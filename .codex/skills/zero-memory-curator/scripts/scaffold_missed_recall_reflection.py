#!/usr/bin/env python3
"""Scaffold missed-recall reflection notes for late duplicate or missed memory recall."""

import argparse
import json
import os
import re
import secrets
from datetime import datetime, timezone
from pathlib import Path

from memory_graph_common import (
    build_package_map,
    build_reverse_load_next,
    compact_text,
    load_memory_packages,
)
from memory_observability import write_jsonl_event


DEFAULT_PATTERN_KEY = "memory.curator.missed-recall-reflection-loop"
DEFAULT_SOURCE_SECTIONS = ["Current Understanding", "Decisions"]
DEFAULT_MEMORY_TARGETS = [
    "memory.curator.workflow",
    "memory.curator.missed.recall.reflection",
]
DEFAULT_REFLECTION_ROOT = ".zero-memory/reflection"
SCRIPT_PATH = "skills/zero-memory-curator/scripts/scaffold_missed_recall_reflection.py"


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Scaffold `.zero-memory/daily/` and `.zero-memory/reflection/` notes "
            "when memory recall misses an existing memory or creates a late duplicate."
        )
    )
    parser.add_argument(
        "--root",
        default=".zero-memory/memory",
        help="Memory root directory. Defaults to .zero-memory/memory.",
    )
    parser.add_argument(
        "--daily-root",
        default=".zero-memory/daily",
        help="Daily-learning root directory. Defaults to .zero-memory/daily.",
    )
    parser.add_argument(
        "--reflection-root",
        default=DEFAULT_REFLECTION_ROOT,
        help="Reflection-advice root directory. Defaults to .zero-memory/reflection.",
    )
    parser.add_argument(
        "--new-memory-id",
        help="Pair mode: the newer memory ID that was created before the older similar memory was found.",
    )
    parser.add_argument(
        "--existing-memory-id",
        help="Pair mode: the older or already-existing similar memory ID.",
    )
    parser.add_argument(
        "--missed-memory-id",
        help="Single-miss mode: the existing memory ID that should have been recalled earlier.",
    )
    parser.add_argument(
        "--source-context",
        help=(
            "Source context path for the reflection. Defaults to the active path "
            "from .zero-memory/tmp/current-context.txt when available; otherwise uses "
            "`manual-zero-memory-reflection`."
        ),
    )
    parser.add_argument(
        "--source-slug",
        help="Optional source slug override. Defaults to the source-context parent directory name.",
    )
    parser.add_argument(
        "--discovery-source",
        default="graph-traversal",
        help=(
            "How the similar memory pair was discovered. Examples: graph-traversal, "
            "semantic-shortlist, validator, manual-review. Defaults to graph-traversal."
        ),
    )
    parser.add_argument(
        "--discovery-note",
        help="Optional extra note about how the similar memory was noticed.",
    )
    parser.add_argument(
        "--trigger",
        default="late-duplicate-discovery",
        help=(
            "What triggered the reflection. Examples: late-duplicate-discovery, "
            "user-asked-why-not-recalled, agent-self-diagnosis."
        ),
    )
    parser.add_argument(
        "--visible-evidence",
        action="append",
        default=[],
        help=(
            "Visible evidence used to explain the miss. Repeat as needed; do not "
            "include hidden assumptions or unobserved corpus state."
        ),
    )
    parser.add_argument(
        "--miss-reason",
        action="append",
        default=[],
        help="Concrete suspected reason recall failed, based on visible evidence. Repeat as needed.",
    )
    parser.add_argument(
        "--improvement-advice",
        action="append",
        default=[],
        help="Concrete advice for improving recall surfaces. Repeat as needed.",
    )
    parser.add_argument(
        "--replay-check",
        action="append",
        default=[],
        help="Suggested validation or replay check for zero-memory-reflection. Repeat as needed.",
    )
    parser.add_argument(
        "--source-section",
        action="append",
        default=[],
        help="Source section name to record. Repeat as needed. Defaults to Current Understanding and Decisions.",
    )
    parser.add_argument(
        "--suggested-memory-target",
        action="append",
        default=[],
        help="Additional suggested memory target. Repeat as needed.",
    )
    parser.add_argument(
        "--related-file",
        action="append",
        default=[],
        help="Additional related file to record. Repeat as needed.",
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
        help=(
            "Write the scaffolded daily-learning entry and the dedicated "
            ".zero-memory/reflection/ improvement-advice note."
        ),
    )
    return parser.parse_args()


def repo_relative(path_value):
    if not path_value:
        return ""
    if path_value == "manual-zero-memory-reflection":
        return path_value
    path = Path(path_value)
    if not path.is_absolute():
        return path.as_posix()
    try:
        return path.resolve().relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        return str(path_value)


def derive_source_context(args):
    explicit = (args.source_context or "").strip()
    if explicit:
        return repo_relative(explicit)
    workspace_root = os.environ.get("TASK_CONTEXT_WORKSPACE_ROOT", "").strip()
    if not workspace_root:
        workspace_root = str(Path.cwd())
    active_file = os.environ.get("TASK_CONTEXT_ACTIVE_CONTEXT_FILE", "").strip()
    active_files = []
    if active_file:
        active_files.append(Path(active_file))
    else:
        active_files.append(
            Path(workspace_root) / ".zero-memory" / "tmp" / "current-context.txt"
        )
    for candidate in active_files:
        try:
            active_path = candidate.read_text(encoding="utf-8").splitlines()[0].strip()
        except (IndexError, OSError):
            active_path = ""
        if active_path:
            return repo_relative(active_path)
    return "manual-zero-memory-reflection"


def slugify(value):
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return slug or "manual-zero-memory-reflection"


def derive_source_slug(source_context, explicit_slug):
    if explicit_slug:
        return explicit_slug.strip()
    if source_context and source_context != "manual-zero-memory-reflection":
        path = Path(source_context)
        if path.name == "context.md":
            return path.parent.name or "manual-zero-memory-reflection"
        if path.name:
            return slugify(path.stem)
    return "manual-zero-memory-reflection"


def generate_daily_identity():
    now = datetime.now(timezone.utc)
    daily_id = now.strftime("DL-%Y%m%d-%H%M%S.") + "{0:03d}Z-".format(
        now.microsecond // 1000
    ) + secrets.token_hex(4)
    return now, daily_id


def truncate(text, limit=180):
    text = compact_text(text or "")
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


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


def shared_values(left, right):
    return sorted(set(left).intersection(right))


def relation_notes(new_package, existing_package):
    notes = []
    if existing_package["id"] in new_package["load_next"]:
        notes.append("`{0}` already lists `{1}` in `load_next`".format(new_package["id"], existing_package["id"]))
    if new_package["id"] in existing_package["load_next"]:
        notes.append("`{0}` already lists `{1}` in `load_next`".format(existing_package["id"], new_package["id"]))
    if existing_package["id"] in new_package["related"]:
        notes.append("`{0}` already lists `{1}` in `related`".format(new_package["id"], existing_package["id"]))
    if new_package["id"] in existing_package["related"]:
        notes.append("`{0}` already lists `{1}` in `related`".format(existing_package["id"], new_package["id"]))
    return notes


def validate_mode(args):
    pair_values = [args.new_memory_id, args.existing_memory_id]
    has_pair_value = any(pair_values)
    has_complete_pair = all(pair_values)
    has_missed_memory = bool(args.missed_memory_id)
    if has_missed_memory and has_pair_value:
        raise SystemExit(
            "Use either --missed-memory-id for single-miss mode or "
            "--new-memory-id plus --existing-memory-id for pair mode, not both."
        )
    if has_pair_value and not has_complete_pair:
        raise SystemExit(
            "Pair mode requires both --new-memory-id and --existing-memory-id."
        )
    if not has_missed_memory and not has_complete_pair:
        raise SystemExit(
            "Provide --missed-memory-id, or provide both --new-memory-id and --existing-memory-id."
        )
    if has_complete_pair and args.new_memory_id == args.existing_memory_id:
        raise SystemExit("--new-memory-id and --existing-memory-id must be different.")
    return "single-miss" if has_missed_memory else "late-duplicate"


def infer_single_possible_gaps(package, parents):
    hints = []
    if not package["pattern_key"]:
        hints.append("the missed memory is missing `pattern_key`")
    if not package["related_files"]:
        hints.append("the missed memory is missing `related_files`")
    if not parents:
        hints.append("the missed memory has no reverse `load_next` parent route")
    if not package["load_next"] and package["layer"] in {"init", "abstract"}:
        hints.append("the routing memory has no `load_next` expansion paths")
    return dedupe(hints)


def infer_possible_gaps(
    new_package,
    existing_package,
    new_parents,
    existing_parents,
    shared_related_files,
    shared_related_symbols,
    relation_hints,
):
    hints = []
    new_pattern = new_package["pattern_key"]
    existing_pattern = existing_package["pattern_key"]
    if not new_pattern and not existing_pattern:
        hints.append("both memories are missing `pattern_key`")
    elif not new_pattern or not existing_pattern:
        hints.append("one memory is missing `pattern_key`")
    elif new_pattern != existing_pattern:
        hints.append(
            "the memories use different `pattern_key` values (`{0}` vs `{1}`)".format(
                new_pattern, existing_pattern
            )
        )

    if not new_package["related_files"] or not existing_package["related_files"]:
        hints.append("at least one memory is missing `related_files`")
    elif not shared_related_files:
        hints.append("the memories do not share any `related_files`")

    if new_package["related_symbols"] or existing_package["related_symbols"]:
        if not new_package["related_symbols"] or not existing_package["related_symbols"]:
            hints.append("only one side has `related_symbols`")
        elif not shared_related_symbols:
            hints.append("the memories do not share any `related_symbols`")

    if not new_parents or not existing_parents:
        hints.append("one side has no reverse `load_next` parent route")
    elif not set(new_parents).intersection(existing_parents):
        hints.append("the memories do not share a reverse `load_next` parent")

    if new_package["layer"] != existing_package["layer"]:
        hints.append(
            "the memories use different layers (`{0}` vs `{1}`)".format(
                new_package["layer"], existing_package["layer"]
            )
        )

    if new_package["component"] and existing_package["component"]:
        if new_package["component"] != existing_package["component"]:
            hints.append(
                "the memories use different `component` values (`{0}` vs `{1}`)".format(
                    new_package["component"], existing_package["component"]
                )
            )

    if new_package["kind"] and existing_package["kind"]:
        if new_package["kind"] != existing_package["kind"]:
            hints.append(
                "the memories use different `kind` values (`{0}` vs `{1}`)".format(
                    new_package["kind"], existing_package["kind"]
                )
            )

    if not relation_hints:
        hints.append("no direct `load_next` or `related` link currently connects the pair")

    return dedupe(hints)


def list_or_none(values):
    values = dedupe(values)
    if not values:
        return "_none_"
    return ", ".join("`{0}`".format(value) for value in values)


def text_list_or_none(values):
    values = dedupe(values)
    if not values:
        return "_none_"
    return "; ".join(values)


def plain_list_or_none(values):
    values = dedupe(values)
    if not values:
        return "_none_"
    return ", ".join(values)


def build_details(new_package, existing_package, analysis, discovery_source, discovery_note):
    lines = [
        "Scaffolded missed-recall comparison between `{0}` and `{1}`.".format(
            new_package["id"], existing_package["id"]
        ),
        "",
        "Discovery context:",
        "- Similar pair noticed through `{0}`.".format(discovery_source),
    ]
    if discovery_note:
        lines.append("- Discovery note: {0}".format(discovery_note))
    lines.extend(
        [
            "",
        "Compared memory surfaces:",
        "- New memory description: {0}".format(analysis["new_description"]),
        "- Existing memory description: {0}".format(analysis["existing_description"]),
        "- New memory status/layer: `{0}` / `{1}`".format(
            new_package["status"], new_package["layer"]
        ),
        "- Existing memory status/layer: `{0}` / `{1}`".format(
            existing_package["status"], existing_package["layer"]
        ),
        "- New memory `pattern_key`: {0}".format(
            "`{0}`".format(new_package["pattern_key"]) if new_package["pattern_key"] else "_missing_"
        ),
        "- Existing memory `pattern_key`: {0}".format(
            "`{0}`".format(existing_package["pattern_key"])
            if existing_package["pattern_key"]
            else "_missing_"
        ),
        "- New memory parents: {0}".format(list_or_none(analysis["new_parents"])),
        "- Existing memory parents: {0}".format(list_or_none(analysis["existing_parents"])),
        "- Shared parents: {0}".format(list_or_none(analysis["shared_parents"])),
        "- Shared `related_files`: {0}".format(list_or_none(analysis["shared_related_files"])),
        "- Shared `related_symbols`: {0}".format(list_or_none(analysis["shared_related_symbols"])),
        "- Existing cross-links: {0}".format(text_list_or_none(analysis["relation_hints"])),
        "",
        "Possible recall-miss surfaces to review:",
        ]
    )
    if analysis["possible_gaps"]:
        for hint in analysis["possible_gaps"]:
            lines.append("- {0}".format(hint))
    else:
        lines.append(
            "- No obvious structured metadata gap was detected; the miss may depend on description wording or semantic boundary definition."
        )
    lines.extend(
        [
            "",
            "Next decisions to make:",
            "- Explain why the earlier lookup missed the existing memory.",
            "- Decide whether to merge, refine, re-parent, or supersede.",
            "- Update descriptions, boundary wording, lookup metadata, and graph edges before closing the duplicate.",
        ]
    )
    return "\n".join(lines).strip()


def build_single_miss_details(package, analysis, discovery_source, discovery_note, trigger):
    lines = [
        "Scaffolded missed-recall analysis for existing memory `{0}`.".format(
            package["id"]
        ),
        "",
        "Discovery context:",
        "- Trigger: `{0}`.".format(trigger),
        "- Missed memory noticed through `{0}`.".format(discovery_source),
    ]
    if discovery_note:
        lines.append("- Discovery note: {0}".format(discovery_note))
    lines.extend(
        [
            "",
            "Visible memory surface:",
            "- Memory description: {0}".format(analysis["missed_description"]),
            "- Memory status/layer: `{0}` / `{1}`".format(
                package["status"], package["layer"]
            ),
            "- Memory `pattern_key`: {0}".format(
                "`{0}`".format(package["pattern_key"])
                if package["pattern_key"]
                else "_missing_"
            ),
            "- Memory parents: {0}".format(list_or_none(analysis["parents"])),
            "- Memory `related_files`: {0}".format(
                list_or_none(package["related_files"])
            ),
            "- Memory `related_symbols`: {0}".format(
                list_or_none(package["related_symbols"])
            ),
            "",
            "Possible recall-miss surfaces to review:",
        ]
    )
    if analysis["possible_gaps"]:
        for hint in analysis["possible_gaps"]:
            lines.append("- {0}".format(hint))
    else:
        lines.append(
            "- No obvious structured metadata gap was detected; review the earlier recall terms, route choice, and memory wording."
        )
    lines.extend(
        [
            "",
            "Next decisions to make:",
            "- Explain why the visible recall path did not surface this existing memory earlier.",
            "- Decide whether description wording, lookup metadata, graph routing, skill guidance, or tooling should change.",
            "- Re-run the intended graph-first lookup path after the fix.",
        ]
    )
    return "\n".join(lines).strip()


def build_related_files(new_package, existing_package, shared_related_files, extra_related_files):
    values = [
        repo_relative(new_package["path"]),
        repo_relative(existing_package["path"]),
        SCRIPT_PATH,
    ]
    values.extend(shared_related_files)
    values.extend(extra_related_files)
    return dedupe(values)


def build_single_related_files(package, extra_related_files):
    values = [
        repo_relative(package["path"]),
        SCRIPT_PATH,
    ]
    values.extend(package["related_files"])
    values.extend(extra_related_files)
    return dedupe(values)


def generated_pair_evidence(new_package, existing_package, analysis):
    values = [
        "New memory `{0}` description: {1}".format(
            new_package["id"], analysis["new_description"]
        ),
        "Existing memory `{0}` description: {1}".format(
            existing_package["id"], analysis["existing_description"]
        ),
        "New memory parents: {0}".format(plain_list_or_none(analysis["new_parents"])),
        "Existing memory parents: {0}".format(
            plain_list_or_none(analysis["existing_parents"])
        ),
        "Shared parents: {0}".format(plain_list_or_none(analysis["shared_parents"])),
        "Shared related files: {0}".format(
            plain_list_or_none(analysis["shared_related_files"])
        ),
        "Existing direct cross-links: {0}".format(
            text_list_or_none(analysis["relation_hints"])
        ),
    ]
    return dedupe(values)


def generated_single_evidence(package, analysis):
    return dedupe(
        [
            "Missed memory `{0}` description: {1}".format(
                package["id"], analysis["missed_description"]
            ),
            "Missed memory parents: {0}".format(
                plain_list_or_none(analysis["parents"])
            ),
            "Missed memory related files: {0}".format(
                plain_list_or_none(package["related_files"])
            ),
            "Missed memory related symbols: {0}".format(
                plain_list_or_none(package["related_symbols"])
            ),
        ]
    )


def render_section_list(lines, title, values):
    lines.append("## {0}".format(title))
    values = dedupe(values)
    if values:
        for value in values:
            lines.append("- {0}".format(value))
    else:
        lines.append("- _none recorded_")
    lines.append("")


def render_reflection_advice(note):
    lines = [
        "# Missed Recall Improvement Advice",
        "",
        "- Reflection ID: `{0}`".format(note["reflection_id"]),
        "- Timestamp: {0}".format(note["timestamp"]),
        "- Status: new",
        "- Trigger: `{0}`".format(note["trigger"]),
        "- Mode: `{0}`".format(note["mode"]),
        "- Discovery Source: `{0}`".format(note["discovery_source"]),
        "- Source Context: `{0}`".format(note["source_context"]),
        "- Daily Learning ID: `{0}`".format(note["daily_id"]),
        "",
        "## Affected Memories",
    ]
    for memory_id in note["affected_memory_ids"]:
        lines.append("- `{0}`".format(memory_id))
    lines.extend(
        [
            "",
            "## Evidence Boundary",
            "- Explain the miss only from visible evidence in the current turn, such as loaded memory descriptions, graph routes, lookup terms, candidate lists, generated observability reports, or the user's correction.",
            "- Do not invent hidden recall attempts, hidden corpus state, or unstated user intent.",
            "",
        ]
    )
    render_section_list(lines, "Visible Evidence", note["visible_evidence"])
    render_section_list(lines, "Suspected Miss Reasons", note["miss_reasons"])
    render_section_list(lines, "Improvement Advice", note["improvement_advice"])
    render_section_list(lines, "Replay Or Validation Checks", note["replay_checks"])
    lines.extend(
        [
            "## Handoff To zero-memory-reflection",
            "- Use this note as opt-in input when the user asks to optimize memory recall, skill descriptions, or graph routing.",
            "- Prefer the smallest local fix first; escalate to whole-graph audit only when repeated notes show system-level design debt.",
            "",
        ]
    )
    return "\n".join(lines)


def write_reflection_note(reflection_file, note_text):
    reflection_file.parent.mkdir(parents=True, exist_ok=True)
    reflection_file.write_text(note_text.rstrip() + "\n", encoding="utf-8")


def emit_multiline_field(lines, key, value):
    value = (value or "").strip()
    if not value:
        lines.append("- {0}:".format(key))
        return
    parts = value.splitlines()
    lines.append("- {0}: {1}".format(key, parts[0]))
    for part in parts[1:]:
        lines.append("  {0}".format(part))


def emit_list_field(lines, key, values, quote_backticks=False):
    values = dedupe(values)
    if not values:
        lines.append("- {0}:".format(key))
        return
    lines.append("- {0}:".format(key))
    for value in values:
        rendered = "`{0}`".format(value) if quote_backticks else value
        lines.append("  - {0}".format(rendered))


def render_daily_entry(entry):
    lines = [
        "## {0}".format(entry["daily_id"]),
        "- Timestamp: {0}".format(entry["timestamp"]),
        "- Source Slug: {0}".format(entry["source_slug"]),
        "- Source Context: `{0}`".format(entry["source_context"]),
        "- Type: reflection",
        "- Pattern-Key: {0}".format(entry["pattern_key"]),
    ]
    emit_multiline_field(lines, "Summary", entry["summary"])
    emit_multiline_field(lines, "Details", entry["details"])
    emit_multiline_field(lines, "Why Reusable", entry["why_reusable"])
    emit_list_field(
        lines,
        "Suggested Memory Targets",
        entry["suggested_memory_targets"],
        quote_backticks=True,
    )
    emit_list_field(lines, "Source Sections", entry["source_sections"])
    emit_list_field(lines, "Related Files", entry["related_files"], quote_backticks=True)
    lines.append("- Status: new")
    lines.append("")
    return "\n".join(lines)


def append_entry(daily_file, entry_text):
    daily_file.parent.mkdir(parents=True, exist_ok=True)
    existing = daily_file.read_text(encoding="utf-8") if daily_file.exists() else ""
    if existing.strip():
        combined = existing.rstrip() + "\n\n" + entry_text.rstrip() + "\n"
    else:
        combined = entry_text.rstrip() + "\n"
    daily_file.write_text(combined, encoding="utf-8")


def render_markdown_result(result):
    lines = [
        "# Missed Recall Reflection Scaffold",
        "",
        "- Root: `{0}`".format(result["root"]),
        "- Daily Root: `{0}`".format(result["daily_root"]),
        "- Reflection Root: `{0}`".format(result["reflection_root"]),
        "- Mode: `{0}`".format(result["mode"]),
        "- Affected Memories: {0}".format(list_or_none(result["affected_memory_ids"])),
        "- Missed Memories: {0}".format(list_or_none(result["missed_memory_ids"])),
        "- Late Duplicate Memories: {0}".format(
            list_or_none(result["late_duplicate_memory_ids"])
        ),
        "- Daily Output File: `{0}`".format(result["daily_output_file"]),
        "- Reflection Output File: `{0}`".format(result["reflection_output_file"]),
        "- Daily ID: `{0}`".format(result["daily_id"]),
        "- Discovery Source: `{0}`".format(result["discovery_source"]),
        "- Write Mode: `{0}`".format("yes" if result["write"] else "no"),
        "",
        "## Daily Entry",
        "",
        result["entry_markdown"].rstrip(),
        "",
        "## Reflection Advice",
        "",
        result["reflection_markdown"].rstrip(),
        "",
    ]
    return "\n".join(lines)


def main():
    args = parse_args()
    mode = validate_mode(args)

    packages, duplicate_ids = load_memory_packages(args.root)
    if duplicate_ids:
        raise SystemExit(
            "Memory graph has duplicate IDs; resolve them before scaffolding reflection notes."
        )
    package_map = build_package_map(packages)
    reverse_map = build_reverse_load_next(package_map, include_inactive=True)

    source_context = derive_source_context(args)
    source_slug = derive_source_slug(source_context, args.source_slug)
    source_sections = dedupe(args.source_section or DEFAULT_SOURCE_SECTIONS)
    suggested_memory_targets = dedupe(
        DEFAULT_MEMORY_TARGETS + list(args.suggested_memory_target or [])
    )
    discovery_source = args.discovery_source.strip() or "graph-traversal"
    discovery_note = (args.discovery_note or "").strip()
    trigger = (args.trigger or "").strip() or "late-duplicate-discovery"

    now, daily_id = generate_daily_identity()
    date_key = now.strftime("%Y-%m-%d")
    timestamp = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    daily_file = Path(args.daily_root) / "learning.{0}.md".format(date_key)
    reflection_file = (
        Path(args.reflection_root) / "missed-recall" / date_key / "{0}.md".format(daily_id)
    )

    if mode == "late-duplicate":
        new_package = package_map.get(args.new_memory_id)
        existing_package = package_map.get(args.existing_memory_id)
        if new_package is None:
            raise SystemExit("Unknown --new-memory-id `{0}`.".format(args.new_memory_id))
        if existing_package is None:
            raise SystemExit(
                "Unknown --existing-memory-id `{0}`.".format(args.existing_memory_id)
            )

        new_parents = reverse_map.get(new_package["id"], [])
        existing_parents = reverse_map.get(existing_package["id"], [])
        shared_related_files = shared_values(
            new_package["related_files"], existing_package["related_files"]
        )
        shared_related_symbols = shared_values(
            new_package["related_symbols"], existing_package["related_symbols"]
        )
        relation_hints = relation_notes(new_package, existing_package)
        possible_gaps = infer_possible_gaps(
            new_package,
            existing_package,
            new_parents,
            existing_parents,
            shared_related_files,
            shared_related_symbols,
            relation_hints,
        )
        analysis = {
            "new_description": truncate(new_package["description"]),
            "existing_description": truncate(existing_package["description"]),
            "new_parents": new_parents,
            "existing_parents": existing_parents,
            "shared_parents": shared_values(new_parents, existing_parents),
            "shared_related_files": shared_related_files,
            "shared_related_symbols": shared_related_symbols,
            "relation_hints": relation_hints,
            "possible_gaps": possible_gaps,
        }
        details = build_details(
            new_package,
            existing_package,
            analysis,
            discovery_source,
            discovery_note,
        )
        summary = (
            "New memory `{0}` was created before the existing similar memory `{1}` "
            "was found, so this late duplicate should be treated as a missed-recall reflection."
        ).format(new_package["id"], existing_package["id"])
        affected_memory_ids = [new_package["id"], existing_package["id"]]
        missed_memory_ids = [existing_package["id"]]
        late_duplicate_memory_ids = [new_package["id"]]
        related_files = build_related_files(
            new_package,
            existing_package,
            shared_related_files,
            [repo_relative(path) for path in args.related_file],
        )
        generated_evidence = generated_pair_evidence(
            new_package, existing_package, analysis
        )
        comparison = {
            "new_description": analysis["new_description"],
            "existing_description": analysis["existing_description"],
            "new_parents": analysis["new_parents"],
            "existing_parents": analysis["existing_parents"],
            "shared_parents": analysis["shared_parents"],
            "shared_related_files": analysis["shared_related_files"],
            "shared_related_symbols": analysis["shared_related_symbols"],
            "relation_hints": analysis["relation_hints"],
            "possible_gaps": analysis["possible_gaps"],
        }
    else:
        missed_package = package_map.get(args.missed_memory_id)
        if missed_package is None:
            raise SystemExit(
                "Unknown --missed-memory-id `{0}`.".format(args.missed_memory_id)
            )
        parents = reverse_map.get(missed_package["id"], [])
        possible_gaps = infer_single_possible_gaps(missed_package, parents)
        analysis = {
            "missed_description": truncate(missed_package["description"]),
            "parents": parents,
            "possible_gaps": possible_gaps,
        }
        details = build_single_miss_details(
            missed_package,
            analysis,
            discovery_source,
            discovery_note,
            trigger,
        )
        summary = (
            "Existing memory `{0}` was found only after it should already have been "
            "recalled, so this should be treated as a missed-recall reflection."
        ).format(missed_package["id"])
        affected_memory_ids = [missed_package["id"]]
        missed_memory_ids = [missed_package["id"]]
        late_duplicate_memory_ids = []
        related_files = build_single_related_files(
            missed_package,
            [repo_relative(path) for path in args.related_file],
        )
        generated_evidence = generated_single_evidence(missed_package, analysis)
        comparison = {
            "missed_description": analysis["missed_description"],
            "parents": analysis["parents"],
            "possible_gaps": analysis["possible_gaps"],
        }

    miss_reasons = dedupe(list(args.miss_reason or []) + list(possible_gaps))
    if not miss_reasons:
        miss_reasons = [
            "No concrete structured-metadata cause was confirmed yet; replay the earlier recall path and inspect wording, route choice, and lookup terms before changing the graph."
        ]
    improvement_advice = dedupe(args.improvement_advice or [])
    if not improvement_advice:
        improvement_advice = [
            "Improve the smallest discovery surface that explains the miss: memory description wording, lookup metadata, graph routing, skill guidance, or tooling output."
        ]
    replay_checks = dedupe(args.replay_check or [])
    if not replay_checks:
        replay_checks = [
            "Re-run the intended graph-first lookup path and confirm the missed memory is discoverable without broad text search.",
            "If the miss looks repeated or systemic, hand this note to zero-memory-reflection for opt-in optimization.",
        ]
    visible_evidence = dedupe(list(args.visible_evidence or []) + generated_evidence)

    entry = {
        "daily_id": daily_id,
        "timestamp": timestamp,
        "source_slug": source_slug,
        "source_context": source_context,
        "pattern_key": DEFAULT_PATTERN_KEY,
        "summary": summary,
        "details": details,
        "why_reusable": (
            "A scaffolded reflection note lowers the cost of capturing why recall missed "
            "and makes it easier to improve descriptions, metadata, graph routing, "
            "skill guidance, or tooling before cleanup hides the root cause."
        ),
        "suggested_memory_targets": suggested_memory_targets,
        "source_sections": source_sections,
        "related_files": dedupe(related_files + [repo_relative(str(reflection_file))]),
    }
    entry_markdown = render_daily_entry(entry)

    reflection_note = {
        "reflection_id": daily_id,
        "timestamp": timestamp,
        "trigger": trigger,
        "mode": mode,
        "discovery_source": discovery_source,
        "source_context": source_context,
        "daily_id": daily_id,
        "affected_memory_ids": affected_memory_ids,
        "visible_evidence": visible_evidence,
        "miss_reasons": miss_reasons,
        "improvement_advice": improvement_advice,
        "replay_checks": replay_checks,
    }
    reflection_markdown = render_reflection_advice(reflection_note)

    if args.write:
        append_entry(daily_file, entry_markdown)
        write_reflection_note(reflection_file, reflection_markdown)

    result = {
        "root": args.root,
        "daily_root": args.daily_root,
        "reflection_root": args.reflection_root,
        "mode": mode,
        "affected_memory_ids": affected_memory_ids,
        "missed_memory_ids": missed_memory_ids,
        "late_duplicate_memory_ids": late_duplicate_memory_ids,
        "daily_output_file": repo_relative(str(daily_file)),
        "reflection_output_file": repo_relative(str(reflection_file)),
        "daily_id": daily_id,
        "discovery_source": discovery_source,
        "write": args.write,
        "comparison": comparison,
        "entry": entry,
        "entry_markdown": entry_markdown,
        "reflection": reflection_note,
        "reflection_markdown": reflection_markdown,
    }

    write_jsonl_event(
        args.root,
        "reflection.miss-scaffolded",
        skill="zero-memory-curator",
        script=SCRIPT_PATH,
        memory_ids=affected_memory_ids,
        extra={
            "mode": mode,
            "missed_memory_ids": missed_memory_ids,
            "late_duplicate_memory_ids": late_duplicate_memory_ids,
            "discovery_source": discovery_source,
            "daily_id": daily_id,
            "daily_output_file": repo_relative(str(daily_file)),
            "reflection_output_file": repo_relative(str(reflection_file)),
            "write": args.write,
        },
    )

    if args.format == "json":
        print(json.dumps(result, indent=2, ensure_ascii=True))
    else:
        print(render_markdown_result(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
