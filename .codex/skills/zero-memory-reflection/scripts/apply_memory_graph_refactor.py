#!/usr/bin/env python3
"""Apply an approved full-graph audit plan to the zero-memory graph."""

import argparse
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


CURATOR_SCRIPTS_DIR = Path(__file__).resolve().parents[2] / "zero-memory-curator" / "scripts"
if str(CURATOR_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(CURATOR_SCRIPTS_DIR))

from memory_graph_common import (  # noqa: E402
    build_package_map,
    build_reverse_load_next,
    is_active_memory,
    load_init_memory_set,
    load_memory_packages,
    render_frontmatter,
    update_memory_frontmatter,
    write_init_memory_set,
)
from memory_observability import build_observability_snapshot, write_jsonl_event  # noqa: E402


SCRIPT_PATH = "skills/zero-memory-reflection/scripts/apply_memory_graph_refactor.py"

GENERIC_SCOPE_TOKENS = {
    "abstract",
    "active",
    "detail",
    "details",
    "entry",
    "example",
    "examples",
    "flow",
    "flows",
    "group",
    "init",
    "memory",
    "node",
    "path",
    "route",
    "routing",
    "summary",
    "workflow",
    "workflows",
    "workspace",
}


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Apply an approved `zero-memory-reflection` audit cluster by creating or reusing "
            "a summary memory, subsuming selected children, and validating afterward."
        )
    )
    parser.add_argument(
        "--root",
        default=".zero-memory/memory",
        help="Memory root directory. Defaults to .zero-memory/memory.",
    )
    parser.add_argument(
        "--plan",
        required=True,
        help="Path to the saved JSON output from audit_memory_graph.py --format json.",
    )
    cluster_group = parser.add_mutually_exclusive_group(required=True)
    cluster_group.add_argument(
        "--cluster-id",
        help="Stable cluster ID from the audit JSON when available.",
    )
    cluster_group.add_argument(
        "--cluster-index",
        type=int,
        help="1-based cluster index inside the saved audit JSON.",
    )
    parser.add_argument(
        "--summary-id",
        help=(
            "Optional override for the summary memory ID. Use an existing ID to reuse that "
            "summary, or a new ID to create a fresh summary memory."
        ),
    )
    parser.add_argument(
        "--summary-slug",
        help="Optional slug override when creating a new summary memory.",
    )
    parser.add_argument(
        "--summary-name",
        help="Optional frontmatter `name` override when creating a new summary memory.",
    )
    parser.add_argument(
        "--summary-title",
        help="Optional markdown title override when creating a new summary memory.",
    )
    parser.add_argument(
        "--summary-description",
        help="Optional frontmatter/body description override for the summary memory.",
    )
    parser.add_argument(
        "--summary-layer",
        choices=("abstract", "detailed"),
        default="abstract",
        help="Layer to use for a newly created summary. Defaults to abstract.",
    )
    parser.add_argument(
        "--parent-id",
        action="append",
        default=[],
        help=(
            "Explicit active parent memory ID that should gain the summary in `load_next`. "
            "Repeat as needed."
        ),
    )
    parser.add_argument(
        "--add-to-init",
        action="store_true",
        help="Also add the summary memory to init-memory-set.yml.",
    )
    parser.add_argument(
        "--subsume",
        action="append",
        default=[],
        help=(
            "Cluster member ID to mark as `status: subsumed`. Repeat as needed. "
            "Defaults to audit members with action `candidate_subsume`."
        ),
    )
    parser.add_argument(
        "--format",
        choices=("markdown", "json"),
        default="markdown",
        help="Output format. Defaults to markdown.",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Apply the plan. Without this flag the script prints a preview only.",
    )
    parser.add_argument(
        "--change-journal-path",
        help=(
            "Optional JSON path for a structured apply journal. In --write mode the script "
            "will otherwise default to a sibling `history/zero-memory-reflection/` directory "
            "under the chosen memory root parent."
        ),
    )
    return parser.parse_args()


def dedupe(values):
    result = []
    seen = set()
    for value in values:
        item = str(value).strip()
        if not item or item in seen:
            continue
        result.append(item)
        seen.add(item)
    return result


def slugify(value):
    cleaned = []
    previous_dash = False
    for char in str(value).strip().lower():
        keep = char if char.isalnum() else "-"
        if keep == "-":
            if previous_dash:
                continue
            previous_dash = True
        else:
            previous_dash = False
        cleaned.append(keep)
    slug = "".join(cleaned).strip("-")
    return slug or "memory-summary"


def title_from_slug(value):
    pieces = [piece for piece in str(value).replace("_", "-").split("-") if piece]
    if not pieces:
        return "Memory Summary"
    return " ".join(piece.capitalize() for piece in pieces)


def cluster_identifier(cluster):
    explicit = str(cluster.get("cluster_id", "")).strip()
    if explicit:
        return explicit
    joined = "||".join(sorted(cluster.get("memory_ids", [])))
    digest = hashlib.sha1(joined.encode("utf-8")).hexdigest()[:12]
    return "cluster-" + digest


def load_plan(path):
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit("Audit plan JSON must be an object.")
    clusters = payload.get("clusters")
    if not isinstance(clusters, list):
        raise SystemExit("Audit plan JSON is missing a `clusters` list.")
    return payload


def select_cluster(plan, cluster_id, cluster_index):
    clusters = plan.get("clusters", [])
    if cluster_id:
        for cluster in clusters:
            if cluster_identifier(cluster) == cluster_id:
                return cluster
        raise SystemExit("Unknown --cluster-id `{0}`.".format(cluster_id))
    index = int(cluster_index or 0)
    if index <= 0 or index > len(clusters):
        raise SystemExit(
            "--cluster-index must be between 1 and {0}.".format(len(clusters))
        )
    return clusters[index - 1]


def dominant_value(packages, field_name, fallback):
    values = [package.get(field_name, "") for package in packages if package.get(field_name, "")]
    distinct = sorted(set(values))
    if len(distinct) == 1:
        return distinct[0]
    return fallback


def union_values(packages, field_name, limit=None):
    values = []
    for package in packages:
        values.extend(package.get(field_name, []))
    values = dedupe(values)
    if limit is not None:
        values = values[:limit]
    return values


def recommended_parent_ids(cluster_member_ids, package_map, reverse_map, excluded_ids):
    cluster_set = set(cluster_member_ids)
    excluded_ids = set(excluded_ids)
    parent_ids = []
    for member_id in cluster_member_ids:
        for parent_id in reverse_map.get(member_id, []):
            if parent_id in cluster_set or parent_id in excluded_ids:
                continue
            parent = package_map.get(parent_id)
            if parent is None or not is_active_memory(parent):
                continue
            parent_ids.append(parent_id)
    return dedupe(parent_ids)


def default_subsume_ids(cluster):
    result = []
    for member in cluster.get("member_plans", []):
        if member.get("action") == "candidate_subsume":
            result.append(member.get("id", ""))
    return dedupe(result)


def quoted(values):
    values = dedupe(values)
    if not values:
        return "_none_"
    return ", ".join("`{0}`".format(value) for value in values)


def utc_now():
    return datetime.now(timezone.utc)


def format_utc_timestamp(value):
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def journal_timestamp_fragment(value):
    return value.astimezone(timezone.utc).strftime("%Y%m%d-%H%M%S")


def token_forms(token):
    token = str(token).strip().lower()
    if not token:
        return set()
    forms = {token}
    if token.endswith("ies") and len(token) > 4:
        forms.add(token[:-3] + "y")
    if token.endswith("s") and len(token) > 4:
        forms.add(token[:-1])
    return forms


def tokenize_text(value):
    tokens = []
    for raw in re.findall(r"[A-Za-z0-9]+", str(value or "").lower()):
        tokens.extend(sorted(token_forms(raw)))
    return dedupe(tokens)


def common_prefix_length(left_parts, right_parts):
    length = 0
    for left_item, right_item in zip(left_parts, right_parts):
        if left_item != right_item:
            break
        length += 1
    return length


def child_scope_terms(summary_id, child_id):
    summary_parts = [item for item in str(summary_id).split(".") if item]
    child_parts = [item for item in str(child_id).split(".") if item]
    prefix_length = common_prefix_length(summary_parts, child_parts)
    tail_parts = child_parts[prefix_length:] or child_parts[-2:]
    tokens = []
    for part in tail_parts:
        tokens.extend(tokenize_text(part))
    return [
        token
        for token in dedupe(tokens)
        if token not in GENERIC_SCOPE_TOKENS and len(token) > 2
    ]


def summary_text_tokens(summary_package, summary_description_override=None):
    summary_text = []
    if summary_description_override:
        summary_text.append(summary_description_override)
    elif summary_package:
        summary_text.append(summary_package.get("description", ""))
    if summary_package:
        summary_text.append(summary_package.get("details", ""))
    return set(tokenize_text(" ".join(summary_text)))


def build_summary_reconciliation(
    summary_id,
    summary_exists,
    summary_package,
    current_load_next,
    new_load_next,
    active_child_ids,
    package_map,
    summary_description_override=None,
):
    if not summary_exists:
        return {
            "required": False,
            "reason": "new summary body is generated in the same apply step",
            "newly_attached_active_children": active_child_ids,
            "removed_children": [],
            "missing_scope_mentions": [],
            "warnings": [],
            "recommended_actions": [],
        }

    current_children = dedupe(current_load_next)
    target_children = dedupe(new_load_next)
    added_active_children = [child_id for child_id in active_child_ids if child_id not in current_children]
    removed_children = [child_id for child_id in current_children if child_id not in target_children]
    required = bool(added_active_children or removed_children)
    summary_tokens = summary_text_tokens(
        summary_package,
        summary_description_override=summary_description_override,
    )

    missing_scope_mentions = []
    for child_id in added_active_children:
        if child_id not in package_map:
            continue
        scope_terms = child_scope_terms(summary_id, child_id)
        matched_terms = [
            term for term in scope_terms if any(form in summary_tokens for form in token_forms(term))
        ]
        if matched_terms:
            continue
        missing_scope_mentions.append(
            {
                "memory_id": child_id,
                "summary_scope_terms": scope_terms[:6],
                "child_description": package_map[child_id].get("description", ""),
            }
        )

    warnings = []
    if missing_scope_mentions:
        warnings.append(
            "summary prose may not mention newly attached active children: {0}".format(
                ", ".join(item["memory_id"] for item in missing_scope_mentions)
            )
        )
    if removed_children:
        warnings.append(
            "summary `load_next` removed children; review whether `## Description` or `## Details` still over-claim those branches: {0}".format(
                ", ".join(removed_children)
            )
        )

    recommended_actions = []
    if required:
        recommended_actions.append(
            "compare the summary `## Description` and `## Details` against the new child scope before closing the reflection pass"
        )
    if missing_scope_mentions:
        recommended_actions.append(
            "either explicitly mention the new child categories in the summary prose or tighten the summary boundary so the added children are clearly out of scope"
        )
    if removed_children:
        recommended_actions.append(
            "remove stale prose that still suggests the summary routes through children that were detached or subsumed"
        )

    reason = "summary child scope changed" if required else "summary child scope unchanged"
    return {
        "required": required,
        "reason": reason,
        "newly_attached_active_children": added_active_children,
        "removed_children": removed_children,
        "missing_scope_mentions": missing_scope_mentions,
        "warnings": warnings,
        "recommended_actions": recommended_actions,
    }


def resolve_change_journal_path(explicit_path, root, change_time, cluster_id):
    explicit = str(explicit_path or "").strip()
    if explicit:
        return explicit, None

    history_dir = Path(root).resolve().parent / "history" / "zero-memory-reflection"
    filename = "zero-memory-reflection-apply-{0}-{1}.json".format(
        journal_timestamp_fragment(change_time),
        cluster_id,
    )
    return str(history_dir / filename), None


def build_change_journal(
    timestamp,
    args,
    cluster,
    summary_action,
    summary_id,
    summary_path,
    summary_exists,
    previous_summary_load_next,
    new_summary_load_next,
    previous_summary_abstracts,
    new_summary_abstracts,
    active_child_ids,
    subsume_ids,
    parent_updates,
    package_map,
    child_updates,
    write_notes,
    validator_payload,
    summary_reconciliation,
    observability_snapshot,
):
    parent_entries = []
    for parent_id, new_load_next in sorted(parent_updates.items()):
        parent_entries.append(
            {
                "memory_id": parent_id,
                "action": "rewrite-load-next",
                "reason": "redirect external parents toward the approved cluster summary",
                "before": {"load_next": list(package_map[parent_id]["load_next"])},
                "after": {"load_next": list(new_load_next)},
            }
        )

    child_entries = []
    for item in child_updates:
        package = package_map[item["id"]]
        child_entries.append(
            {
                "memory_id": item["id"],
                "action": "mark-subsumed",
                "reason": "approved cluster absorbed this child into the chosen summary",
                "before": {
                    "status": package["status"],
                    "subsumed_by": package.get("subsumed_by"),
                },
                "after": {
                    "status": item["status"],
                    "subsumed_by": item["subsumed_by"],
                },
            }
        )

    summary_entry = {
        "memory_id": summary_id,
        "action": summary_action,
        "reason": (
            "reuse an existing summary anchor for the approved audit cluster"
            if summary_exists
            else "create a new summary anchor for the approved audit cluster"
        ),
        "before": {
            "path": summary_path,
            "load_next": list(previous_summary_load_next),
            "abstracts": list(previous_summary_abstracts),
        }
        if summary_exists
        else {
            "path": summary_path,
            "state": "missing",
        },
        "after": {
            "path": summary_path,
            "load_next": list(new_summary_load_next),
            "abstracts": list(new_summary_abstracts),
        },
        "summary_reconciliation": summary_reconciliation,
    }

    validator_summary = None
    if validator_payload is not None:
        validator_summary = {
            "status": validator_payload.get("status"),
            "errors": len(validator_payload.get("errors", [])),
            "warnings": len(validator_payload.get("warnings", [])),
            "repairs": len(validator_payload.get("repairs", [])),
        }

    changed_ids = dedupe(
        [summary_id]
        + subsume_ids
        + list(parent_updates.keys())
    )

    return {
        "timestamp": format_utc_timestamp(timestamp),
        "trigger": {
            "type": "zero-memory-reflection-approved-graph-refactor",
            "plan_path": args.plan,
            "cluster_id": cluster.get("cluster_id") or cluster_identifier(cluster),
            "cluster_member_ids": cluster.get("memory_ids", []),
        },
        "summary": {
            "memory_id": summary_id,
            "action": summary_action,
            "path": summary_path,
            "active_child_ids": active_child_ids,
            "subsumed_ids": subsume_ids,
        },
        "observability": observability_snapshot,
        "changed_memory_ids": changed_ids,
        "changes": [summary_entry] + child_entries + parent_entries,
        "write_notes": list(write_notes),
        "validator": validator_summary,
    }


def write_change_journal(path, payload):
    target_path = Path(path)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )


def build_new_summary_payload(
    summary_id,
    summary_slug,
    summary_name,
    summary_title,
    summary_description,
    summary_layer,
    summary_last_updated_at,
    cluster_packages,
    cluster_member_ids,
    active_member_ids,
    subsume_ids,
    summary_parent_ids,
):
    component = dominant_value(
        cluster_packages,
        "component",
        cluster_packages[0].get("component") or "workflow",
    )
    kind = dominant_value(cluster_packages, "kind", "best-practice")
    stage = dominant_value(cluster_packages, "stage", "review")
    scope = dominant_value(cluster_packages, "scope", "project")
    actionability = dominant_value(cluster_packages, "actionability", "reference-only")
    freshness_profile = dominant_value(cluster_packages, "freshness_profile", "conceptual")
    tags = union_values(cluster_packages, "tags", limit=8)
    if "abstraction" not in tags:
        tags.append("abstraction")
    frontmatter = {
        "id": summary_id,
        "name": summary_name,
        "description": summary_description,
        "tags": tags,
        "pattern_key": summary_id,
        "component": component,
        "kind": kind,
        "stage": stage,
        "scope": scope,
        "actionability": actionability,
        "layer": summary_layer,
        "status": "active",
        "last_updated_at": summary_last_updated_at,
        "freshness_profile": freshness_profile,
        "load_next": active_member_ids,
        "abstracts": subsume_ids,
        "related_files": union_values(cluster_packages, "related_files", limit=12),
        "related_symbols": union_values(cluster_packages, "related_symbols", limit=12),
    }
    details_lines = [
        "This summary was created from an approved `zero-memory-reflection` full-graph audit cluster.",
        "",
        "- Cluster members: {0}".format(quoted(cluster_member_ids)),
        "- Active children kept on the main route: {0}".format(quoted(active_member_ids)),
        "- Subsumed memories absorbed into this abstraction: {0}".format(quoted(subsume_ids)),
        "- Added parent routes: {0}".format(quoted(summary_parent_ids)),
        "",
        "Use this node as the higher-level abstraction first, then follow `load_next` only when a remaining active child still carries distinct operational detail.",
    ]
    source_paths = [package["path"] for package in cluster_packages]
    source_lines = [
        "- Original files: {0}".format(
            ", ".join("`{0}`".format(path) for path in source_paths[:8])
            + (", ..." if len(source_paths) > 8 else "")
        ),
        "- Extraction rule: synthesize a higher-level abstraction from an approved whole-graph audit cluster over existing curated memories instead of claiming new direct daily-learning provenance for the summary itself.",
        "- Fact list:",
        "  - the listed memories share one reusable higher-level rule",
        "  - active `load_next` children remain only when they still add distinct operational value",
        "  - low-value concrete variants can become `status: subsumed` with `subsumed_by` pointing here",
    ]
    related_lines = []
    related_files = frontmatter.get("related_files", [])
    if related_files:
        related_lines.append(
            "- Related files: {0}".format(
                ", ".join("`{0}`".format(value) for value in related_files)
            )
        )
    related_lines.append("- Related memory IDs:")
    for memory_id in cluster_member_ids:
        related_lines.append("  - `{0}`".format(memory_id))

    body = "\n".join(
        [
            "# {0}".format(summary_title),
            "",
            "## Description",
            "",
            summary_description,
            "",
            "## Details",
            "",
            "\n".join(details_lines),
            "",
            "## Source Extraction",
            "",
            "\n".join(source_lines),
            "",
            "## Related",
            "",
            "\n".join(related_lines),
            "",
        ]
    )
    return {
        "slug": summary_slug,
        "path": str(Path(summary_slug) / "MEMORY.md"),
        "frontmatter": frontmatter,
        "title": summary_title,
        "body": body,
    }


def validator_result(root):
    command = [
        sys.executable,
        str(CURATOR_SCRIPTS_DIR / "validate_memory_graph.py"),
        "--root",
        root,
        "--repair",
        "--format",
        "json",
    ]
    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
        check=False,
    )
    payload = None
    stdout = result.stdout.strip()
    if stdout:
        payload = json.loads(stdout)
    return result.returncode, payload, result.stderr.strip()


def render_markdown(result):
    lines = [
        "# Memory Graph Refactor Apply",
        "",
        "- Root: `{0}`".format(result["root"]),
        "- Plan: `{0}`".format(result["plan"]),
        "- Cluster: `{0}`".format(result["cluster_id"]),
        "- Write Mode: `{0}`".format("yes" if result["write"] else "no"),
        "- Summary Action: `{0}`".format(result["summary_action"]),
        "- Summary ID: `{0}`".format(result["summary_id"]),
        "- Summary Path: `{0}`".format(result["summary_path"]),
        "- Subsumed IDs: {0}".format(quoted(result["subsume_ids"])),
        "- Active Child IDs: {0}".format(quoted(result["active_child_ids"])),
        "- Added Parent IDs: {0}".format(quoted(result["summary_parent_ids"])),
        "- Added To Init: `{0}`".format("yes" if result["add_to_init"] else "no"),
        "",
        "## Summary Reconciliation",
        "",
        "- Required: `{0}`".format(
            "yes" if result["summary_reconciliation"]["required"] else "no"
        ),
        "- Reason: {0}".format(result["summary_reconciliation"]["reason"]),
        "- Newly Attached Active Children: {0}".format(
            quoted(result["summary_reconciliation"]["newly_attached_active_children"])
        ),
        "- Removed Children: {0}".format(
            quoted(result["summary_reconciliation"]["removed_children"])
        ),
        "",
    ]
    for warning in result["summary_reconciliation"]["warnings"]:
        lines.append("- Warning: {0}".format(warning))
    for item in result["summary_reconciliation"]["missing_scope_mentions"]:
        lines.append(
            "- Missing Scope Mention: `{0}` may need prose coverage for terms {1}".format(
                item["memory_id"],
                quoted(item["summary_scope_terms"]),
            )
        )
    for action in result["summary_reconciliation"]["recommended_actions"]:
        lines.append("- Recommended Action: {0}".format(action))
    observability = result.get("observability_snapshot", {})
    available_reports = observability.get("available_reports", {})
    lines.extend(["", "## Observability", ""])
    lines.append(
        "- Available Reports: {0}".format(
            ", ".join(
                "`{0}`".format(name)
                for name, available in sorted(available_reports.items())
                if available
            )
            or "_none_"
        )
    )
    lines.append(
        "- Memory Metrics Captured: {0}".format(
            len(observability.get("memory_metrics", {}))
        )
    )
    lines.extend(
        [
            "",
            "## Parent Updates",
            "",
        ]
    )
    if not result["parent_updates"]:
        lines.append("No parent `load_next` rewrites were needed.")
        lines.append("")
    else:
        for item in result["parent_updates"]:
            lines.append(
                "- `{0}` -> {1}".format(
                    item["parent_id"],
                    quoted(item["new_load_next"]),
                )
            )
        lines.append("")

    lines.extend(["## Child Updates", ""])
    if not result["child_updates"]:
        lines.append("No child lifecycle updates were needed.")
        lines.append("")
    else:
        for item in result["child_updates"]:
            lines.append(
                "- `{0}` -> `status: {1}` with `subsumed_by: {2}`".format(
                    item["id"],
                    item["status"],
                    item["subsumed_by"],
                )
            )
        lines.append("")

    if result["validator"] is not None:
        validator = result["validator"]
        lines.extend(
            [
                "## Validation",
                "",
                "- Status: `{0}`".format(validator.get("status", "unknown")),
                "- Repairs: {0}".format(len(validator.get("repairs", []))),
                "- Errors: {0}".format(len(validator.get("errors", []))),
                "- Warnings: {0}".format(len(validator.get("warnings", []))),
                "",
            ]
        )
    lines.extend(["## Change Journal", ""])
    if result["change_journal_written"] and result["change_journal_path"]:
        lines.append("- Path: `{0}`".format(result["change_journal_path"]))
        lines.append("- Status: `written`")
        lines.append("")
    elif result["change_journal_warning"]:
        lines.append("- Status: `not-written`")
        lines.append("- Warning: {0}".format(result["change_journal_warning"]))
        lines.append("")
    return "\n".join(lines)


def main():
    args = parse_args()
    plan = load_plan(args.plan)
    cluster = select_cluster(plan, args.cluster_id, args.cluster_index)
    cluster_id = cluster_identifier(cluster)
    change_time = utc_now()
    change_timestamp = format_utc_timestamp(change_time)

    packages, duplicate_ids = load_memory_packages(args.root)
    if duplicate_ids:
        raise SystemExit(
            "Memory graph has duplicate IDs; resolve them before applying an audit plan."
        )
    package_map = build_package_map(packages)
    reverse_map = build_reverse_load_next(package_map, include_inactive=True)

    cluster_member_ids = dedupe(cluster.get("memory_ids", []))
    if not cluster_member_ids:
        raise SystemExit("Selected cluster has no `memory_ids`.")
    unknown_ids = [memory_id for memory_id in cluster_member_ids if memory_id not in package_map]
    if unknown_ids:
        raise SystemExit(
            "Selected cluster references unknown memory IDs: {0}".format(
                ", ".join(unknown_ids)
            )
        )

    cluster_packages = [package_map[memory_id] for memory_id in cluster_member_ids]
    default_summary_id = (
        (cluster.get("existing_summary_id") or "").strip()
        or (cluster.get("proposed_abstract_memory") or {}).get("id", "").strip()
    )
    summary_id = (args.summary_id or default_summary_id).strip()
    if not summary_id:
        raise SystemExit("Could not determine a summary memory ID for the selected cluster.")

    summary_exists = summary_id in package_map
    summary_package = package_map.get(summary_id)
    previous_summary_load_next = list(summary_package["load_next"]) if summary_exists else []
    previous_summary_abstracts = list(summary_package["abstracts"]) if summary_exists else []
    if summary_exists and not is_active_memory(summary_package):
        raise SystemExit("Summary memory `{0}` exists but is not active.".format(summary_id))

    default_subsume = default_subsume_ids(cluster)
    subsume_ids = dedupe(args.subsume or default_subsume)
    invalid_subsume = [memory_id for memory_id in subsume_ids if memory_id not in cluster_member_ids]
    if invalid_subsume:
        raise SystemExit(
            "`--subsume` IDs must be cluster members: {0}".format(
                ", ".join(invalid_subsume)
            )
        )
    if summary_id in subsume_ids:
        raise SystemExit("The chosen summary memory cannot also be subsumed.")

    for memory_id in cluster_member_ids:
        package = package_map[memory_id]
        if not is_active_memory(package):
            raise SystemExit(
                "Apply workflow currently expects active cluster members only; `{0}` is `{1}`.".format(
                    memory_id, package["status"]
                )
            )

    for memory_id in subsume_ids:
        package = package_map[memory_id]
        if package["layer"] == "init":
            raise SystemExit("Init memory `{0}` cannot be subsumed.".format(memory_id))
        active_children = [
            child_id
            for child_id in package["load_next"]
            if child_id in package_map and is_active_memory(package_map[child_id])
        ]
        if active_children:
            raise SystemExit(
                "Memory `{0}` cannot be subsumed because it still has active children: {1}".format(
                    memory_id, ", ".join(active_children)
                )
            )

    cluster_set = set(cluster_member_ids)
    if args.parent_id:
        summary_parent_ids = dedupe(args.parent_id)
    elif summary_exists:
        summary_parent_ids = []
    else:
        summary_parent_ids = recommended_parent_ids(
            cluster_member_ids,
            package_map,
            reverse_map,
            excluded_ids=subsume_ids,
        )

    for parent_id in summary_parent_ids:
        if parent_id not in package_map:
            raise SystemExit("Unknown --parent-id `{0}`.".format(parent_id))
        if parent_id in cluster_set:
            raise SystemExit(
                "Parent `{0}` is inside the cluster; use an external parent or `--add-to-init`.".format(
                    parent_id
                )
            )
        if parent_id == summary_id:
            raise SystemExit("Summary memory cannot parent itself.")
        if not is_active_memory(package_map[parent_id]):
            raise SystemExit("Parent `{0}` must be active.".format(parent_id))

    if not summary_exists and not summary_parent_ids and not args.add_to_init:
        raise SystemExit(
            "A new summary would be unreachable; add at least one `--parent-id` or use `--add-to-init`."
        )

    active_child_ids = [
        memory_id
        for memory_id in cluster_member_ids
        if memory_id not in subsume_ids and memory_id != summary_id
    ]

    parent_updates = {}
    parent_notes = []

    for parent_id in summary_parent_ids:
        current_children = list(package_map[parent_id]["load_next"])
        new_children = [child_id for child_id in current_children if child_id not in subsume_ids]
        if summary_id not in new_children:
            new_children.append(summary_id)
        new_children = dedupe(new_children)
        if new_children != current_children:
            parent_updates[parent_id] = new_children
            parent_notes.append(
                "attached summary `{0}` under parent `{1}`".format(summary_id, parent_id)
            )

    for child_id in subsume_ids:
        for parent_id in reverse_map.get(child_id, []):
            parent_package = package_map.get(parent_id)
            if parent_package is None or not is_active_memory(parent_package):
                continue
            if parent_id in subsume_ids:
                continue
            current_children = list(
                parent_updates.get(parent_id, parent_package["load_next"])
            )
            new_children = [item for item in current_children if item != child_id]
            if parent_id != summary_id and parent_id not in cluster_set:
                if summary_id not in new_children:
                    new_children.append(summary_id)
            new_children = dedupe(new_children)
            if new_children != current_children:
                parent_updates[parent_id] = new_children
                parent_notes.append(
                    "redirected parent `{0}` from subsumed child `{1}` to summary `{2}`".format(
                        parent_id, child_id, summary_id
                    )
                )

    summary_action = "update-existing-summary" if summary_exists else "create-new-summary"
    summary_payload = None
    summary_frontmatter_updates = None
    summary_path = (
        summary_package["path"]
        if summary_exists
        else str(Path(args.root) / (args.summary_slug or (cluster.get("proposed_abstract_memory") or {}).get("slug", "") or slugify(summary_id)) / "MEMORY.md")
    )
    new_summary_load_next = []
    new_summary_abstracts = []

    if summary_exists:
        new_summary_load_next = dedupe(
            [
                child_id
                for child_id in summary_package["load_next"]
                if child_id not in subsume_ids
            ]
            + active_child_ids
        )
        new_summary_abstracts = dedupe(summary_package["abstracts"] + subsume_ids)
        summary_frontmatter_updates = {}
        if new_summary_load_next != previous_summary_load_next:
            summary_frontmatter_updates["load_next"] = new_summary_load_next
        if new_summary_abstracts != previous_summary_abstracts:
            summary_frontmatter_updates["abstracts"] = new_summary_abstracts
        if args.summary_description and args.summary_description != summary_package["description"]:
            summary_frontmatter_updates["description"] = args.summary_description
        if summary_frontmatter_updates:
            summary_frontmatter_updates["last_updated_at"] = change_timestamp
        else:
            summary_frontmatter_updates = None
        summary_path = summary_package["path"]
    else:
        proposed = cluster.get("proposed_abstract_memory") or {}
        summary_slug = args.summary_slug or proposed.get("slug") or slugify(summary_id)
        summary_name = args.summary_name or summary_slug
        summary_title = (
            args.summary_title
            or proposed.get("title")
            or title_from_slug(summary_slug)
        )
        summary_description = (
            args.summary_description
            or proposed.get("description")
            or "Higher-level summary synthesized from an approved zero-memory-reflection audit cluster."
        )
        summary_path = str(Path(args.root) / summary_slug / "MEMORY.md")
        if Path(summary_path).exists():
            raise SystemExit(
                "Cannot create summary `{0}` because `{1}` already exists.".format(
                    summary_id, summary_path
                )
            )
        summary_payload = build_new_summary_payload(
            summary_id=summary_id,
            summary_slug=summary_slug,
            summary_name=summary_name,
            summary_title=summary_title,
            summary_description=summary_description,
            summary_layer=args.summary_layer,
            summary_last_updated_at=change_timestamp,
            cluster_packages=cluster_packages,
            cluster_member_ids=cluster_member_ids,
            active_member_ids=active_child_ids,
            subsume_ids=subsume_ids,
            summary_parent_ids=summary_parent_ids,
        )
        new_summary_load_next = list(summary_payload["frontmatter"]["load_next"])
        new_summary_abstracts = list(summary_payload["frontmatter"]["abstracts"])

    summary_reconciliation = build_summary_reconciliation(
        summary_id=summary_id,
        summary_exists=summary_exists,
        summary_package=summary_package,
        current_load_next=previous_summary_load_next,
        new_load_next=new_summary_load_next,
        active_child_ids=active_child_ids,
        package_map=package_map,
        summary_description_override=args.summary_description if summary_exists else None,
    )
    observability_snapshot = build_observability_snapshot(
        args.root,
        dedupe(cluster_member_ids + [summary_id] + list(parent_updates.keys())),
    )

    child_updates = [
        {
            "id": memory_id,
            "status": "subsumed",
            "subsumed_by": summary_id,
            "path": package_map[memory_id]["path"],
        }
        for memory_id in subsume_ids
    ]

    init_update = None
    if args.add_to_init:
        current_init_ids = load_init_memory_set(args.root)
        new_init_ids = dedupe(current_init_ids + [summary_id])
        if new_init_ids != current_init_ids:
            init_update = new_init_ids

    validator_payload = None
    validator_stderr = ""
    validator_code = 0
    write_notes = []
    change_journal_path = None
    change_journal_written = False
    change_journal_warning = None
    change_journal_payload = None

    if args.write:
        if summary_payload is not None:
            summary_file = Path(summary_path)
            summary_file.parent.mkdir(parents=True, exist_ok=True)
            rendered = "---\n{0}\n---\n\n{1}".format(
                render_frontmatter(summary_payload["frontmatter"]),
                summary_payload["body"].rstrip() + "\n",
            )
            summary_file.write_text(rendered, encoding="utf-8")
            write_notes.append("created summary `{0}`".format(summary_id))
        elif summary_frontmatter_updates:
            update_memory_frontmatter(summary_path, summary_frontmatter_updates)
            write_notes.append("updated summary `{0}`".format(summary_id))

        for item in child_updates:
            update_memory_frontmatter(
                item["path"],
                {
                    "status": item["status"],
                    "subsumed_by": item["subsumed_by"],
                    "last_updated_at": change_timestamp,
                },
            )
        if child_updates:
            write_notes.append(
                "updated {0} child memories to `status: subsumed`".format(
                    len(child_updates)
                )
            )

        for parent_id, new_load_next in sorted(parent_updates.items()):
            update_memory_frontmatter(
                package_map[parent_id]["path"],
                {
                    "load_next": new_load_next,
                    "last_updated_at": change_timestamp,
                },
            )
        if parent_updates:
            write_notes.append(
                "rewrote `load_next` for {0} parent memories".format(len(parent_updates))
            )

        if init_update is not None:
            write_init_memory_set(args.root, init_update)
            write_notes.append("updated init-memory-set.yml")

        validator_code, validator_payload, validator_stderr = validator_result(args.root)
        change_journal_path, change_journal_warning = resolve_change_journal_path(
            args.change_journal_path,
            args.root,
            change_time,
            cluster_id,
        )
        change_journal_payload = build_change_journal(
            timestamp=change_time,
            args=args,
            cluster=cluster,
            summary_action=summary_action,
            summary_id=summary_id,
            summary_path=summary_path,
            summary_exists=summary_exists,
            previous_summary_load_next=previous_summary_load_next,
            new_summary_load_next=new_summary_load_next,
            previous_summary_abstracts=previous_summary_abstracts,
            new_summary_abstracts=new_summary_abstracts,
            active_child_ids=active_child_ids,
            subsume_ids=subsume_ids,
            parent_updates=parent_updates,
            package_map=package_map,
            child_updates=child_updates,
            write_notes=write_notes,
            validator_payload=validator_payload,
            summary_reconciliation=summary_reconciliation,
            observability_snapshot=observability_snapshot,
        )
        if change_journal_path:
            write_change_journal(change_journal_path, change_journal_payload)
            change_journal_written = True

    result = {
        "root": args.root,
        "plan": args.plan,
        "cluster_id": cluster_id,
        "write": args.write,
        "summary_action": summary_action,
        "summary_id": summary_id,
        "summary_path": summary_path,
        "subsume_ids": subsume_ids,
        "active_child_ids": active_child_ids,
        "summary_parent_ids": summary_parent_ids,
        "add_to_init": args.add_to_init,
        "parent_updates": [
            {"parent_id": parent_id, "new_load_next": value}
            for parent_id, value in sorted(parent_updates.items())
        ],
        "child_updates": child_updates,
        "write_notes": write_notes,
        "parent_notes": parent_notes,
        "summary_reconciliation": summary_reconciliation,
        "change_journal_path": change_journal_path,
        "change_journal_written": change_journal_written,
        "change_journal_warning": change_journal_warning,
        "observability_snapshot": observability_snapshot,
        "validator": validator_payload,
        "validator_stderr": validator_stderr,
    }

    write_jsonl_event(
        args.root,
        "reflection.{0}".format("apply-write" if args.write else "apply-preview"),
        skill="zero-memory-reflection",
        script=SCRIPT_PATH,
        memory_ids=dedupe([summary_id] + cluster_member_ids + list(parent_updates.keys())),
        extra={
            "cluster_id": cluster_id,
            "summary_id": summary_id,
            "changed_memory_ids": dedupe(
                [summary_id] + subsume_ids + list(parent_updates.keys())
            ),
            "subsumed_ids": subsume_ids,
            "rewired_parent_ids": sorted(parent_updates.keys()),
            "observability_reports": observability_snapshot.get("available_reports", {}),
            "validator_status": (validator_payload or {}).get("status", ""),
        },
        status=(validator_payload or {}).get("status", "ok"),
    )

    if args.format == "json":
        print(json.dumps(result, indent=2, ensure_ascii=True))
    else:
        print(render_markdown(result))
    return validator_code


if __name__ == "__main__":
    raise SystemExit(main())
