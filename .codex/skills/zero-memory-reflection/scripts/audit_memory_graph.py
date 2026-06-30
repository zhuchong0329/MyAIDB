#!/usr/bin/env python3
"""Audit the full zero-memory graph and propose reviewable simplification plans."""

import argparse
import hashlib
import json
import math
import sys
from collections import Counter, defaultdict, deque
from itertools import combinations
from pathlib import Path


CURATOR_SCRIPTS_DIR = Path(__file__).resolve().parents[2] / "zero-memory-curator" / "scripts"
if str(CURATOR_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(CURATOR_SCRIPTS_DIR))

from memory_graph_common import (  # noqa: E402
    build_package_map,
    build_reverse_load_next,
    is_active_memory,
    load_memory_packages,
)
from shortlist_similar_memories import (  # noqa: E402
    build_surface,
    dedupe,
    score_candidate,
    tokenize_text,
)
from memory_observability import latest_report_index, write_jsonl_event  # noqa: E402


SCRIPT_PATH = "skills/zero-memory-reflection/scripts/audit_memory_graph.py"


GENERIC_SUMMARY_TOKENS = {
    "active",
    "abstract",
    "daily",
    "entry",
    "example",
    "group",
    "memory",
    "node",
    "note",
    "one",
    "point",
    "shar",
    "shared",
    "system",
    "workflow",
    "zero",
}


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Traverse the full memory graph, cluster likely same-essence memories, "
            "and produce a reviewable simplification plan."
        )
    )
    parser.add_argument(
        "--root",
        default=".zero-memory/memory",
        help="Memory root directory. Defaults to .zero-memory/memory.",
    )
    parser.add_argument(
        "--format",
        choices=("markdown", "json"),
        default="markdown",
        help="Output format. Defaults to markdown.",
    )
    parser.add_argument(
        "--include-inactive",
        action="store_true",
        help="Include inactive memories in the audit candidate set.",
    )
    parser.add_argument(
        "--include-init",
        action="store_true",
        help="Include `layer: init` memories in the audit candidate set.",
    )
    parser.add_argument(
        "--include-routing",
        action="store_true",
        help=(
            "Include memories that already have active children. By default the audit "
            "focuses on compressible non-routing memories first."
        ),
    )
    parser.add_argument(
        "--min-pair-score",
        type=float,
        default=0.26,
        help="Minimum similarity score for a clustering edge. Defaults to 0.26.",
    )
    parser.add_argument(
        "--min-cluster-size",
        type=int,
        default=2,
        help="Minimum cluster size to report. Defaults to 2.",
    )
    parser.add_argument(
        "--top-clusters",
        type=int,
        default=8,
        help="Maximum number of clusters to report. Defaults to 8.",
    )
    return parser.parse_args()


def pair_key(left_id, right_id):
    return tuple(sorted((left_id, right_id)))


def cluster_identifier(component):
    joined = "||".join(sorted(component))
    digest = hashlib.sha1(joined.encode("utf-8")).hexdigest()[:12]
    return "cluster-" + digest


def build_audit_surfaces(packages, package_map, reverse_map):
    surfaces = {}
    for package in packages:
        surfaces[package["id"]] = build_surface(
            memory_id=package["id"],
            name=package["name"],
            description=package["description"],
            details=package["details"],
            pattern_key=package["pattern_key"],
            component=package["component"],
            kind=package["kind"],
            layer=package["layer"],
            related_files=package["related_files"],
            related_symbols=package["related_symbols"],
            tags=package["tags"],
            parents=reverse_map.get(package["id"], []),
            path=package["path"],
            status=package["status"],
        )
    return surfaces


def has_active_children(package, package_map):
    for child_id in package["load_next"]:
        child = package_map.get(child_id)
        if child and is_active_memory(child):
            return True
    return False


def audit_candidates(packages, package_map, include_inactive, include_init, include_routing):
    result = []
    for package in packages:
        if not include_inactive and not is_active_memory(package):
            continue
        if not include_init and package["layer"] == "init":
            continue
        if not include_routing and has_active_children(package, package_map):
            continue
        result.append(package)
    return result


def build_similarity_graph(candidates, surfaces, min_pair_score):
    adjacency = defaultdict(set)
    pair_metrics = {}
    ids = [package["id"] for package in candidates]
    for memory_id in ids:
        adjacency[memory_id]
    for left_id, right_id in combinations(ids, 2):
        metrics = score_candidate(surfaces[left_id], surfaces[right_id])
        pair_metrics[pair_key(left_id, right_id)] = metrics
        if metrics["score"] >= min_pair_score:
            adjacency[left_id].add(right_id)
            adjacency[right_id].add(left_id)
    return adjacency, pair_metrics


def connected_components(nodes, adjacency):
    remaining = set(nodes)
    components = []
    while remaining:
        root = sorted(remaining)[0]
        queue = deque([root])
        component = []
        remaining.remove(root)
        while queue:
            current = queue.popleft()
            component.append(current)
            for neighbor in sorted(adjacency.get(current, [])):
                if neighbor in remaining:
                    remaining.remove(neighbor)
                    queue.append(neighbor)
        components.append(sorted(component))
    return components


def cluster_parent_hints(component, package_map, reverse_map):
    cluster_set = set(component)
    external_parent_map = {}
    common_parent_ids = None
    union_parent_ids = []
    for memory_id in component:
        parent_ids = [
            parent_id
            for parent_id in reverse_map.get(memory_id, [])
            if parent_id not in cluster_set
            and parent_id in package_map
            and is_active_memory(package_map[parent_id])
        ]
        parent_ids = dedupe(parent_ids)
        external_parent_map[memory_id] = parent_ids
        parent_set = set(parent_ids)
        common_parent_ids = (
            parent_set if common_parent_ids is None else common_parent_ids.intersection(parent_set)
        )
        union_parent_ids.extend(parent_ids)
    return {
        "by_member": external_parent_map,
        "union_parent_ids": dedupe(union_parent_ids),
        "common_parent_ids": sorted(common_parent_ids or []),
    }


def component_pair_metrics(component, pair_metrics):
    scores = []
    by_member = defaultdict(list)
    for left_id, right_id in combinations(component, 2):
        metrics = pair_metrics[pair_key(left_id, right_id)]
        scores.append(metrics["score"])
        by_member[left_id].append(metrics["score"])
        by_member[right_id].append(metrics["score"])
    averages = {}
    for memory_id in component:
        values = by_member.get(memory_id, [])
        averages[memory_id] = sum(values) / len(values) if values else 0.0
    return scores, averages


def common_cluster_terms(component, surfaces):
    min_frequency = max(2, int(math.ceil(len(component) / 2.0)))
    counts = Counter()
    for memory_id in component:
        tokens = set(tokenize_text(surfaces[memory_id]["description"]))
        for token in tokens:
            if token in GENERIC_SUMMARY_TOKENS:
                continue
            counts[token] += 1
    terms = [
        token
        for token, count in counts.most_common()
        if count >= min_frequency and token not in GENERIC_SUMMARY_TOKENS
    ]
    return terms[:6]


def summary_slug_from_terms(component, terms):
    if terms:
        return "-".join(terms[:4]) + "-summary"
    anchor = component[0].replace(".", "-")
    return anchor + "-summary"


def readable_title(component_name, terms):
    pieces = []
    if component_name and component_name != "multi-component":
        pieces.append(component_name.replace("-", " ").title())
    if terms:
        pieces.extend(token.replace("-", " ") for token in terms[:4])
    pieces.append("Summary")
    return " ".join(piece.title() for piece in pieces if piece).strip()


def select_existing_summary_candidate(component, package_map, averages):
    candidates = []
    for memory_id in component:
        package = package_map[memory_id]
        if package["layer"] == "leaf" and not package["load_next"]:
            continue
        weight = (
            averages.get(memory_id, 0.0),
            len(package["load_next"]),
            len(package["related"]),
            -len(package["description"]),
        )
        candidates.append((weight, memory_id))
    if not candidates:
        return None
    return max(candidates)[1]


def propose_abstract_memory(component, package_map, surfaces, averages):
    component_values = {
        package_map[memory_id]["component"]
        for memory_id in component
        if package_map[memory_id]["component"]
    }
    component_name = (
        component_values.pop() if len(component_values) == 1 else "multi-component"
    )
    common_terms = common_cluster_terms(component, surfaces)
    slug = summary_slug_from_terms(component, common_terms)
    memory_id = "{0}.{1}".format(component_name or "memory", slug.replace("-", "."))
    title = readable_title(component_name, common_terms)
    central_id = max(component, key=lambda item: (averages.get(item, 0.0), item))
    anchor_description = surfaces[central_id]["description"]
    description = (
        "Proposed abstract memory that groups {0} around shared themes: {1}."
    ).format(
        ", ".join("`{0}`".format(item) for item in component[:4])
        + ("..." if len(component) > 4 else ""),
        ", ".join("`{0}`".format(term) for term in common_terms[:4])
        if common_terms
        else "central description overlap anchored by `{0}`".format(central_id),
    )
    return {
        "id": memory_id,
        "slug": slug,
        "title": title,
        "description": description,
        "component": component_name or "multi-component",
        "common_terms": common_terms,
        "anchor_memory_id": central_id,
        "anchor_description": anchor_description,
    }


def member_action(memory_id, component, package_map, surfaces, averages, summary_mode, summary_id):
    package = package_map[memory_id]
    if summary_id and memory_id == summary_id:
        return {
            "action": "keep_as_summary",
            "reason": "chosen as the current summary anchor for this cluster",
        }

    other_ids = [item for item in component if item != memory_id]
    other_files = set()
    other_symbols = set()
    for other_id in other_ids:
        other_files.update(package_map[other_id]["related_files"])
        other_symbols.update(package_map[other_id]["related_symbols"])
    unique_files = sorted(set(package["related_files"]) - other_files)
    unique_symbols = sorted(set(package["related_symbols"]) - other_symbols)

    if package["load_next"]:
        return {
            "action": "keep_active_child",
            "reason": "already routes to child memories and should not be inactivated as a trivial node",
        }

    if unique_files or unique_symbols:
        details = []
        if unique_files:
            details.append(
                "unique `related_files`: {0}".format(
                    ", ".join("`{0}`".format(item) for item in unique_files[:4])
                )
            )
        if unique_symbols:
            details.append(
                "unique `related_symbols`: {0}".format(
                    ", ".join("`{0}`".format(item) for item in unique_symbols[:4])
                )
            )
        return {
            "action": "keep_active_example",
            "reason": "; ".join(details),
        }

    average_score = averages.get(memory_id, 0.0)
    if package["layer"] in ("leaf", "detailed") and average_score >= 0.30:
        reason = (
            "high cluster overlap with no unique file/symbol evidence; candidate for a future "
            "`subsumed`-style inactive state under the higher-level summary"
        )
        if summary_mode == "reuse-existing-summary":
            reason += " `{0}`".format(summary_id)
        return {
            "action": "candidate_subsume",
            "reason": reason,
        }

    return {
        "action": "keep_active_example",
        "reason": "still useful as a concrete manifestation even though the cluster suggests a higher-level summary",
    }


def analyze_component(component, package_map, surfaces, pair_metrics, reverse_map):
    scores, averages = component_pair_metrics(component, pair_metrics)
    average_pair_score = sum(scores) / len(scores) if scores else 0.0
    max_pair_score = max(scores) if scores else 0.0
    min_pair_score = min(scores) if scores else 0.0
    existing_summary_id = select_existing_summary_candidate(component, package_map, averages)
    summary_mode = "reuse-existing-summary" if existing_summary_id else "create-new-summary"
    proposed_abstract = propose_abstract_memory(component, package_map, surfaces, averages)
    parent_hints = cluster_parent_hints(component, package_map, reverse_map)

    member_plans = []
    for memory_id in component:
        action_plan = member_action(
            memory_id,
            component,
            package_map,
            surfaces,
            averages,
            summary_mode,
            existing_summary_id,
        )
        member_plans.append(
            {
                "id": memory_id,
                "layer": package_map[memory_id]["layer"],
                "status": package_map[memory_id]["status"],
                "description": package_map[memory_id]["description"],
                "average_similarity": round(averages.get(memory_id, 0.0), 4),
                "action": action_plan["action"],
                "reason": action_plan["reason"],
            }
        )

    default_subsume_ids = [
        member["id"] for member in member_plans if member["action"] == "candidate_subsume"
    ]
    default_summary_id = existing_summary_id or proposed_abstract["id"]
    apply_preview = (
        "python3 skills/zero-memory-reflection/scripts/apply_memory_graph_refactor.py "
        "--root .zero-memory/memory --plan <audit-plan.json> --cluster-id {0} --write"
    ).format(cluster_identifier(component))
    priority_score = average_pair_score * max(2, len(component))
    return {
        "cluster_id": cluster_identifier(component),
        "memory_ids": component,
        "cluster_size": len(component),
        "average_pair_score": round(average_pair_score, 4),
        "max_pair_score": round(max_pair_score, 4),
        "min_pair_score": round(min_pair_score, 4),
        "priority_score": round(priority_score, 4),
        "summary_mode": summary_mode,
        "existing_summary_id": existing_summary_id,
        "proposed_abstract_memory": proposed_abstract,
        "default_subsume_ids": default_subsume_ids,
        "recommended_parent_ids": parent_hints["union_parent_ids"],
        "common_parent_ids": parent_hints["common_parent_ids"],
        "external_parent_ids_by_member": parent_hints["by_member"],
        "default_summary_id": default_summary_id,
        "apply_preview_command": apply_preview,
        "member_plans": member_plans,
        "lifecycle_note": (
            "`candidate_subsume` can now be applied explicitly as `status: subsumed` with "
            "reciprocal `subsumed_by` / `abstracts` metadata through "
            "`apply_memory_graph_refactor.py`, but the audit itself still stays non-mutating."
        ),
    }


def average(values):
    if not values:
        return None
    return round(sum(values) / float(len(values)), 2)


def load_observability_indexes(root):
    hot_payload, hot_index = latest_report_index(root, "hot-memories")
    routing_payload, routing_index = latest_report_index(root, "routing-friction")
    reflection_payload, reflection_index = latest_report_index(root, "reflection-priority")
    return {
        "available_reports": {
            "hot-memories": hot_payload is not None,
            "routing-friction": routing_payload is not None,
            "reflection-priority": reflection_payload is not None,
        },
        "hot": hot_index,
        "routing": routing_index,
        "reflection": reflection_index,
    }


def enrich_cluster_with_observability(cluster, observability_indexes):
    available_reports = observability_indexes["available_reports"]
    if not any(available_reports.values()):
        cluster["observability"] = {
            "available": False,
            "available_reports": available_reports,
            "priority_boost": 0.0,
            "cluster_hotness_score": 0.0,
            "cluster_helpful_count": 0,
            "cluster_missed_recall_count": 0,
            "cluster_stale_hit_count": 0,
            "cluster_avg_depth_to_helpful": None,
            "member_metrics": [],
        }
        return cluster

    member_metrics = []
    hotness_total = 0.0
    helpful_total = 0
    missed_total = 0
    stale_total = 0
    depth_values = []

    for memory_id in cluster["memory_ids"]:
        hot_entry = observability_indexes["hot"].get(memory_id, {})
        routing_entry = observability_indexes["routing"].get(memory_id, {})
        reflection_entry = observability_indexes["reflection"].get(memory_id, {})
        hotness_score = float(hot_entry.get("hotness_score", 0.0) or 0.0)
        helpful_count = int(hot_entry.get("helpful_count", 0) or 0)
        stale_hit_count = int(hot_entry.get("stale_hit_count", 0) or 0)
        missed_recall_count = int(
            reflection_entry.get("missed_recall_count", 0)
            or routing_entry.get("missed_recall_count", 0)
            or 0
        )
        avg_depth = routing_entry.get("avg_depth_to_helpful")
        try:
            avg_depth = float(avg_depth) if avg_depth is not None else None
        except (TypeError, ValueError):
            avg_depth = None
        if avg_depth is not None:
            depth_values.append(avg_depth)

        hotness_total += hotness_score
        helpful_total += helpful_count
        missed_total += missed_recall_count
        stale_total += stale_hit_count
        if hotness_score or helpful_count or missed_recall_count or stale_hit_count or avg_depth is not None:
            member_metrics.append(
                {
                    "memory_id": memory_id,
                    "hotness_score": round(hotness_score, 2),
                    "helpful_count": helpful_count,
                    "missed_recall_count": missed_recall_count,
                    "stale_hit_count": stale_hit_count,
                    "avg_depth_to_helpful": avg_depth,
                }
            )

    avg_depth = average(depth_values)
    priority_boost = round(
        0.10 * hotness_total
        + 1.50 * helpful_total
        + 2.00 * missed_total
        + 1.00 * stale_total
        + 0.50 * (avg_depth or 0.0),
        4,
    )
    cluster["priority_score"] = round(cluster["priority_score"] + priority_boost, 4)
    cluster["observability"] = {
        "available": True,
        "available_reports": available_reports,
        "priority_boost": priority_boost,
        "cluster_hotness_score": round(hotness_total, 2),
        "cluster_helpful_count": helpful_total,
        "cluster_missed_recall_count": missed_total,
        "cluster_stale_hit_count": stale_total,
        "cluster_avg_depth_to_helpful": avg_depth,
        "member_metrics": member_metrics,
    }
    return cluster


def render_markdown(result):
    lines = [
        "# Full Graph Memory Audit",
        "",
        "- Root: `{0}`".format(result["root"]),
        "- Include Inactive: `{0}`".format(
            "yes" if result["include_inactive"] else "no"
        ),
        "- Include Init: `{0}`".format("yes" if result["include_init"] else "no"),
        "- Include Routing: `{0}`".format(
            "yes" if result["include_routing"] else "no"
        ),
        "- Minimum Pair Score: {0:.2f}".format(result["min_pair_score"]),
        "- Minimum Cluster Size: {0}".format(result["min_cluster_size"]),
        "- Candidate Memory Count: {0}".format(result["candidate_memory_count"]),
        "- Reported Cluster Count: {0}".format(result["cluster_count"]),
        "- Observability Reports: {0}".format(
            ", ".join(
                "`{0}`".format(name)
                for name, available in sorted(result["observability_reports"].items())
                if available
            )
            or "_none_"
        ),
        "- Safety: plan-only; review before any merge, abstraction, or inactive-state change.",
        "",
    ]
    if not result["clusters"]:
        lines.extend(["No clusters met the current threshold.", ""])
        return "\n".join(lines)

    for index, cluster in enumerate(result["clusters"], start=1):
        lines.append("## Cluster {0}".format(index))
        lines.append("")
        lines.append("- Cluster ID: `{0}`".format(cluster["cluster_id"]))
        lines.append(
            "- Members: {0}".format(
                ", ".join("`{0}`".format(item) for item in cluster["memory_ids"])
            )
        )
        lines.append("- Cluster Size: {0}".format(cluster["cluster_size"]))
        lines.append(
            "- Pair Score Range: min={0:.3f}, avg={1:.3f}, max={2:.3f}".format(
                cluster["min_pair_score"],
                cluster["average_pair_score"],
                cluster["max_pair_score"],
            )
        )
        observability = cluster.get("observability", {})
        if observability.get("available"):
            lines.append(
                "- Observability Boost: {0:.3f}".format(
                    observability.get("priority_boost", 0.0)
                )
            )
            lines.append(
                "- Observability Summary: hotness={0}, helpful={1}, missed={2}, stale-hits={3}, avg-depth={4}".format(
                    observability.get("cluster_hotness_score"),
                    observability.get("cluster_helpful_count"),
                    observability.get("cluster_missed_recall_count"),
                    observability.get("cluster_stale_hit_count"),
                    observability.get("cluster_avg_depth_to_helpful"),
                )
            )
        lines.append("- Summary Mode: `{0}`".format(cluster["summary_mode"]))
        if cluster["existing_summary_id"]:
            lines.append(
                "- Existing Summary Candidate: `{0}`".format(
                    cluster["existing_summary_id"]
                )
            )
        proposed = cluster["proposed_abstract_memory"]
        lines.append("- Proposed Abstract ID: `{0}`".format(proposed["id"]))
        lines.append("- Proposed Abstract Slug: `{0}`".format(proposed["slug"]))
        lines.append("- Proposed Abstract Title: {0}".format(proposed["title"]))
        lines.append("- Proposed Abstract Description: {0}".format(proposed["description"]))
        if proposed["common_terms"]:
            lines.append(
                "- Common Terms: {0}".format(
                    ", ".join("`{0}`".format(item) for item in proposed["common_terms"])
                )
            )
        lines.append(
            "- Anchor Memory: `{0}`".format(proposed["anchor_memory_id"])
        )
        lines.append(
            "- Default Subsumed IDs: {0}".format(
                ", ".join("`{0}`".format(item) for item in cluster["default_subsume_ids"])
            )
            if cluster["default_subsume_ids"]
            else "- Default Subsumed IDs: _none_"
        )
        if cluster["recommended_parent_ids"]:
            lines.append(
                "- Recommended External Parents: {0}".format(
                    ", ".join("`{0}`".format(item) for item in cluster["recommended_parent_ids"])
                )
            )
        lines.append("")
        lines.append("### Member Plan")
        lines.append("")
        for member in cluster["member_plans"]:
            lines.append("- `{0}` -> `{1}` ({2})".format(member["id"], member["action"], member["reason"]))
        lines.append("")
        lines.append("- Lifecycle Note: {0}".format(cluster["lifecycle_note"]))
        lines.append("- Apply Preview: `{0}`".format(cluster["apply_preview_command"]))
        lines.append("")
    return "\n".join(lines)


def main():
    args = parse_args()
    packages, duplicate_ids = load_memory_packages(args.root)
    if duplicate_ids:
        raise SystemExit(
            "Memory graph has duplicate IDs; resolve them before running full-graph audit."
        )
    package_map = build_package_map(packages)
    reverse_map = build_reverse_load_next(package_map, include_inactive=True)
    candidates = audit_candidates(
        packages,
        package_map,
        include_inactive=args.include_inactive,
        include_init=args.include_init,
        include_routing=args.include_routing,
    )
    surfaces = build_audit_surfaces(candidates, package_map, reverse_map)
    adjacency, pair_metrics = build_similarity_graph(
        candidates,
        surfaces,
        min_pair_score=args.min_pair_score,
    )
    components = connected_components(
        [package["id"] for package in candidates],
        adjacency,
    )

    clusters = []
    for component in components:
        if len(component) < args.min_cluster_size:
            continue
        clusters.append(
            analyze_component(component, package_map, surfaces, pair_metrics, reverse_map)
        )

    observability_indexes = load_observability_indexes(args.root)
    for cluster in clusters:
        enrich_cluster_with_observability(cluster, observability_indexes)

    clusters.sort(
        key=lambda item: (
            -item["priority_score"],
            -item["average_pair_score"],
            -item["cluster_size"],
            item["memory_ids"][0],
        )
    )
    clusters = clusters[: max(args.top_clusters, 0)]

    result = {
        "root": args.root,
        "include_inactive": args.include_inactive,
        "include_init": args.include_init,
        "include_routing": args.include_routing,
        "min_pair_score": args.min_pair_score,
        "min_cluster_size": args.min_cluster_size,
        "candidate_memory_count": len(candidates),
        "cluster_count": len(clusters),
        "observability_reports": observability_indexes["available_reports"],
        "clusters": clusters,
    }

    write_jsonl_event(
        args.root,
        "reflection.audit-run",
        skill="zero-memory-reflection",
        script=SCRIPT_PATH,
        memory_ids=dedupe(
            [memory_id for cluster in clusters[:3] for memory_id in cluster["memory_ids"]]
        ),
        extra={
            "cluster_count": len(clusters),
            "top_cluster_ids": [cluster["cluster_id"] for cluster in clusters[:3]],
            "top_cluster_memory_ids": [
                cluster["memory_ids"] for cluster in clusters[:3]
            ],
            "observability_reports": observability_indexes["available_reports"],
        },
    )

    if args.format == "json":
        print(json.dumps(result, indent=2, ensure_ascii=True))
    else:
        print(render_markdown(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
