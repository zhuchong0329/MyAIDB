#!/usr/bin/env python3
"""Load zero-memory descriptions through explicit graph traversal."""

import argparse
import json
import sys
from datetime import datetime, timezone

from memory_graph_common import (
    bfs_levels,
    build_package_map,
    collect_descendant_provenance,
    is_active_memory,
    load_init_memory_set,
    load_memory_packages,
    parse_utc_timestamp,
    resolve_freshness_profile,
)
from memory_observability import write_jsonl_event


SCRIPT_PATH = "skills/zero-memory-curator/scripts/load_memory_graph.py"

FRESHNESS_PROFILE_RULES = {
    "code-env": {
        "ttl_hours": 24,
        "window_label": "24h",
        "fresh_trust_level": "high",
        "fresh_use_posture": "normal",
        "fresh_guidance": (
            "fresh `code-env` memory; use it normally and correct it if current "
            "code, runtime, or environment evidence disagrees"
        ),
        "fresh_validation_advice": "re-check only on contradiction, unusual risk, or a very cheap spot-check",
        "missing_trust_level": "low",
        "missing_use_posture": "skeptical",
        "missing_guidance": (
            "missing `last_updated_at` for `code-env`; use it as a low-confidence "
            "hypothesis and correct it if current code, runtime, or environment "
            "evidence disagrees"
        ),
        "missing_validation_advice": (
            "spot-check before destructive, external, or high-risk use, or when the "
            "check is cheap"
        ),
        "stale_trust_level": "low",
        "stale_use_posture": "skeptical",
        "stale_guidance": (
            "older than 24 hours; use it as a low-confidence hypothesis and correct "
            "it if current code, runtime, or environment evidence disagrees"
        ),
        "stale_validation_advice": (
            "spot-check before destructive, external, or high-risk use, or when the "
            "check is cheap"
        ),
    },
    "workflow": {
        "ttl_hours": 24 * 7,
        "window_label": "7d",
        "fresh_trust_level": "high",
        "fresh_use_posture": "normal",
        "fresh_guidance": (
            "fresh `workflow` memory; use it normally and correct it if the current "
            "workflow or tools disagree"
        ),
        "fresh_validation_advice": "re-check only on contradiction, unusual risk, or a very cheap spot-check",
        "missing_trust_level": "medium",
        "missing_use_posture": "skeptical",
        "missing_guidance": (
            "missing `last_updated_at` for `workflow`; use it with some skepticism "
            "and correct it if current skills, commands, or workflow steps disagree"
        ),
        "missing_validation_advice": (
            "spot-check when the memory is central to the task, externally visible, "
            "or cheap to verify"
        ),
        "stale_trust_level": "medium",
        "stale_use_posture": "skeptical",
        "stale_guidance": (
            "older than 7 days; use it with some skepticism and correct it if the "
            "current workflow or tools disagree"
        ),
        "stale_validation_advice": (
            "spot-check when the memory is central to the task, externally visible, "
            "or cheap to verify"
        ),
    },
    "conceptual": {
        "ttl_hours": None,
        "window_label": "on-suspicion",
        "fresh_trust_level": "high",
        "fresh_use_posture": "normal",
        "fresh_guidance": (
            "fresh `conceptual` memory; use it normally and correct it only if the "
            "current task reveals a contradiction"
        ),
        "fresh_validation_advice": "re-check only on contradiction, unusually high stakes, or a very cheap spot-check",
        "missing_trust_level": "medium",
        "missing_use_posture": "normal",
        "missing_guidance": (
            "missing `last_updated_at` for `conceptual`; age alone does not reduce "
            "trust much, but refresh the metadata when you explicitly revalidate or "
            "materially edit the memory"
        ),
        "missing_validation_advice": "re-check only on contradiction, unusually high stakes, or a very cheap spot-check",
        "contextual_trust_level": "high",
        "contextual_use_posture": "normal",
        "contextual_guidance": (
            "`conceptual` memories do not expire by age alone; use them normally and "
            "correct them only if the current task reveals a contradiction"
        ),
        "contextual_validation_advice": "re-check only on contradiction, unusually high stakes, or a very cheap spot-check",
    },
}


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Load zero-memory descriptions from the init set or a chosen start memory ID."
        )
    )
    parser.add_argument(
        "--root",
        default=".zero-memory/memory",
        help="Memory root directory. Defaults to .zero-memory/memory.",
    )
    parser.add_argument(
        "--start",
        action="append",
        default=[],
        help="Start traversal from this memory ID. May be repeated.",
    )
    parser.add_argument(
        "--depth",
        type=int,
        default=0,
        help="BFS depth to expand. Defaults to 0 (entrypoint descriptions only).",
    )
    parser.add_argument(
        "--format",
        choices=("markdown", "json"),
        default="markdown",
        help="Output format. Defaults to markdown.",
    )
    parser.add_argument(
        "--include-details",
        action="store_true",
        help="Include the Details section for the selected memories.",
    )
    parser.add_argument(
        "--include-provenance",
        action="store_true",
        help="Include direct provenance fields such as source daily-learning IDs.",
    )
    parser.add_argument(
        "--include-derived-provenance",
        action="store_true",
        help="Include derived descendant provenance computed from reachable child memories.",
    )
    parser.add_argument(
        "--include-inactive",
        action="store_true",
        help="Include superseded, incorrect, or tombstoned memories in traversal output.",
    )
    return parser.parse_args()


def _memory_freshness(package, now):
    profile, profile_source = resolve_freshness_profile(package)
    if profile_source == "invalid":
        return {
            "profile": "",
            "profile_source": "invalid",
            "window_label": "invalid",
            "status": "invalid",
            "trust_level": "low",
            "use_posture": "skeptical",
            "guidance": (
                "invalid `freshness_profile`; use the memory carefully and repair the "
                "metadata when convenient"
            ),
            "validation_advice": (
                "spot-check if the memory is central to the task, high-risk, or cheap "
                "to verify"
            ),
        }

    rules = FRESHNESS_PROFILE_RULES[profile]
    last_updated_at = package["last_updated_at"]
    if not last_updated_at:
        return {
            "status": "unknown",
            "profile": profile,
            "profile_source": profile_source,
            "window_label": rules["window_label"],
            "trust_level": rules["missing_trust_level"],
            "use_posture": rules["missing_use_posture"],
            "guidance": rules["missing_guidance"],
            "validation_advice": rules["missing_validation_advice"],
        }

    updated_at = parse_utc_timestamp(last_updated_at)
    if updated_at is None:
        return {
            "status": "invalid",
            "profile": profile,
            "profile_source": profile_source,
            "window_label": rules["window_label"],
            "trust_level": "low",
            "use_posture": "skeptical",
            "guidance": (
                "invalid `last_updated_at`; use the memory carefully and repair the "
                "timestamp when convenient"
            ),
            "validation_advice": (
                "spot-check if the memory is central to the task, high-risk, or cheap "
                "to verify"
            ),
        }

    age_seconds = max(0.0, (now - updated_at).total_seconds())
    age_hours = round(age_seconds / 3600.0, 1)
    if rules["ttl_hours"] is None:
        return {
            "status": "contextual",
            "profile": profile,
            "profile_source": profile_source,
            "window_label": rules["window_label"],
            "trust_level": rules["contextual_trust_level"],
            "use_posture": rules["contextual_use_posture"],
            "guidance": rules["contextual_guidance"],
            "validation_advice": rules["contextual_validation_advice"],
            "age_hours_since_update": age_hours,
        }

    if age_seconds > rules["ttl_hours"] * 3600:
        return {
            "status": "stale",
            "profile": profile,
            "profile_source": profile_source,
            "window_label": rules["window_label"],
            "trust_level": rules["stale_trust_level"],
            "use_posture": rules["stale_use_posture"],
            "guidance": rules["stale_guidance"],
            "validation_advice": rules["stale_validation_advice"],
            "age_hours_since_update": age_hours,
        }

    return {
        "status": "fresh",
        "profile": profile,
        "profile_source": profile_source,
        "window_label": rules["window_label"],
        "trust_level": rules["fresh_trust_level"],
        "use_posture": rules["fresh_use_posture"],
        "guidance": rules["fresh_guidance"],
        "validation_advice": rules["fresh_validation_advice"],
        "age_hours_since_update": age_hours,
    }


def _entry_from_package(
    package,
    package_map,
    level,
    now,
    include_details,
    include_provenance,
    include_derived_provenance,
    include_inactive,
):
    freshness = _memory_freshness(package, now)
    entry = {
        "id": package["id"],
        "name": package["name"],
        "slug": package["slug"],
        "layer": package["layer"],
        "status": package["status"],
        "last_updated_at": package["last_updated_at"],
        "freshness_profile": freshness["profile"],
        "freshness_profile_source": freshness["profile_source"],
        "freshness_window": freshness["window_label"],
        "freshness_status": freshness["status"],
        "trust_level": freshness["trust_level"],
        "use_posture": freshness["use_posture"],
        "guidance": freshness["guidance"],
        "validation_advice": freshness["validation_advice"],
        "path": package["path"],
        "description": package["description"],
        "load_next": package["load_next"],
        "related": package["related"],
        "pattern_key": package["pattern_key"],
        "supersedes": package["supersedes"],
        "superseded_by": package["superseded_by"],
        "abstracts": package["abstracts"],
        "subsumed_by": package["subsumed_by"],
        "related_files": package["related_files"],
        "related_symbols": package["related_symbols"],
        "depth": level,
    }
    if "age_hours_since_update" in freshness:
        entry["age_hours_since_update"] = freshness["age_hours_since_update"]
    if include_provenance:
        entry["source_daily_learning_ids"] = package["source_daily_learning_ids"]
    if include_derived_provenance:
        entry["derived_source_daily_learning_ids"] = collect_descendant_provenance(
            package_map,
            package["id"],
            include_inactive=include_inactive,
        )
    if include_details:
        entry["details"] = package["details"]
    return entry


def render_markdown(
    root,
    start_ids,
    depth,
    entries,
    include_details,
    include_provenance,
    include_derived_provenance,
    include_inactive,
):
    lines = [
        "# Memory Graph",
        "",
        "- Root: `{0}`".format(root),
        "- Start IDs: {0}".format(", ".join("`{0}`".format(item) for item in start_ids)),
        "- Depth: {0}".format(depth),
        "- Include Inactive: `{0}`".format("yes" if include_inactive else "no"),
        "",
    ]
    if not entries:
        lines.extend(["No reachable memories found.", ""])
        return "\n".join(lines)

    for entry in entries:
        lines.append("## {0}".format(entry["id"]))
        lines.append("")
        lines.append("- Name: `{0}`".format(entry["name"]))
        lines.append("- Slug: `{0}`".format(entry["slug"]))
        lines.append("- Layer: `{0}`".format(entry["layer"]))
        lines.append("- Status: `{0}`".format(entry["status"]))
        profile_line = "- Freshness Profile: `{0}`".format(entry["freshness_profile"])
        if entry["freshness_profile_source"] != "declared":
            profile_line += " ({0})".format(entry["freshness_profile_source"])
        lines.append(profile_line)
        lines.append("- Freshness Window: `{0}`".format(entry["freshness_window"]))
        lines.append("- Trust Level: `{0}`".format(entry["trust_level"]))
        lines.append("- Use Posture: `{0}`".format(entry["use_posture"]))
        if entry.get("last_updated_at"):
            lines.append("- Last Updated At: `{0}`".format(entry["last_updated_at"]))
        if entry.get("age_hours_since_update") is not None:
            lines.append(
                "- Age Since Update: `{0}h`".format(entry["age_hours_since_update"])
            )
        if entry["freshness_status"] != "fresh":
            lines.append("- Freshness: `{0}`".format(entry["freshness_status"]))
        lines.append("- Use Guidance: {0}".format(entry["guidance"]))
        lines.append("- Validation Advice: {0}".format(entry["validation_advice"]))
        lines.append("- Depth: {0}".format(entry["depth"]))
        lines.append("- Path: `{0}`".format(entry["path"]))
        lines.append("- Description: {0}".format(entry["description"] or "(missing)"))
        if entry["pattern_key"]:
            lines.append("- Pattern Key: `{0}`".format(entry["pattern_key"]))
        if entry["load_next"]:
            lines.append(
                "- Load Next: {0}".format(
                    ", ".join("`{0}`".format(item) for item in entry["load_next"])
                )
            )
        if entry["related"]:
            lines.append(
                "- Related: {0}".format(
                    ", ".join("`{0}`".format(item) for item in entry["related"])
                )
            )
        if entry["supersedes"]:
            lines.append(
                "- Supersedes: {0}".format(
                    ", ".join("`{0}`".format(item) for item in entry["supersedes"])
                )
            )
        if entry["superseded_by"]:
            lines.append("- Superseded By: `{0}`".format(entry["superseded_by"]))
        if entry["abstracts"]:
            lines.append(
                "- Abstracts: {0}".format(
                    ", ".join("`{0}`".format(item) for item in entry["abstracts"])
                )
            )
        if entry["subsumed_by"]:
            lines.append("- Subsumed By: `{0}`".format(entry["subsumed_by"]))
        if entry["related_files"]:
            lines.append(
                "- Related Files: {0}".format(
                    ", ".join("`{0}`".format(item) for item in entry["related_files"])
                )
            )
        if entry["related_symbols"]:
            lines.append(
                "- Related Symbols: {0}".format(
                    ", ".join("`{0}`".format(item) for item in entry["related_symbols"])
                )
            )
        if include_provenance and entry.get("source_daily_learning_ids"):
            lines.append(
                "- Source Daily Learning IDs: {0}".format(
                    ", ".join(
                        "`{0}`".format(item)
                        for item in entry["source_daily_learning_ids"]
                    )
                )
            )
        if include_derived_provenance and entry.get("derived_source_daily_learning_ids"):
            lines.append(
                "- Derived Descendant Provenance: {0}".format(
                    ", ".join(
                        "`{0}`".format(item)
                        for item in entry["derived_source_daily_learning_ids"]
                    )
                )
            )
        if include_details:
            lines.append("- Details: {0}".format(entry.get("details") or "(missing)"))
        lines.append("")
    return "\n".join(lines)


def main():
    args = parse_args()
    packages, duplicate_ids = load_memory_packages(args.root)
    if duplicate_ids:
        for memory_id in sorted(duplicate_ids):
            print(
                "Duplicate memory ID `{0}` in: {1}".format(
                    memory_id, ", ".join(duplicate_ids[memory_id])
                ),
                file=sys.stderr,
            )
        return 1

    package_map = build_package_map(packages)
    start_ids = args.start or load_init_memory_set(args.root)
    if not start_ids:
        print(
            "No start IDs were provided and init-memory-set.yml is empty.",
            file=sys.stderr,
        )
        return 1

    missing_start_ids = [memory_id for memory_id in start_ids if memory_id not in package_map]
    if missing_start_ids:
        print(
            "Unknown start memory IDs: {0}".format(", ".join(missing_start_ids)),
            file=sys.stderr,
        )
        return 1

    if not args.include_inactive:
        inactive_start_ids = [
            memory_id
            for memory_id in start_ids
            if not is_active_memory(package_map[memory_id])
        ]
        if inactive_start_ids:
            print(
                "Inactive start memory IDs require `--include-inactive`: {0}".format(
                    ", ".join(inactive_start_ids)
                ),
                file=sys.stderr,
            )
            return 1

    levels = bfs_levels(
        package_map,
        start_ids,
        depth=args.depth,
        include_inactive=args.include_inactive,
    )
    now = datetime.now(timezone.utc)
    ordered_entries = []
    for memory_id, level in sorted(levels.items(), key=lambda item: (item[1], item[0])):
        ordered_entries.append(
            _entry_from_package(
                package_map[memory_id],
                package_map,
                level,
                now,
                args.include_details,
                args.include_provenance,
                args.include_derived_provenance,
                args.include_inactive,
            )
        )

    write_jsonl_event(
        args.root,
        "recall.graph-load",
        skill="zero-memory-curator",
        script=SCRIPT_PATH,
        memory_ids=[entry["id"] for entry in ordered_entries],
        extra={
            "start_ids": start_ids,
            "requested_depth": args.depth,
            "include_details": args.include_details,
            "include_provenance": args.include_provenance,
            "include_derived_provenance": args.include_derived_provenance,
            "include_inactive": args.include_inactive,
            "returned_memory_ids": [entry["id"] for entry in ordered_entries],
            "returned_count": len(ordered_entries),
            "returned_depth_by_memory_id": dict(
                (entry["id"], entry["depth"]) for entry in ordered_entries
            ),
            "returned_stale_memory_ids": [
                entry["id"]
                for entry in ordered_entries
                if entry.get("freshness_status") == "stale"
            ],
        },
    )

    if args.format == "json":
        payload = {
            "root": args.root,
            "start_ids": start_ids,
            "depth": args.depth,
            "include_inactive": args.include_inactive,
            "count": len(ordered_entries),
            "entries": ordered_entries,
        }
        print(json.dumps(payload, indent=2, ensure_ascii=True))
        return 0

    print(
        render_markdown(
            args.root,
            start_ids,
            args.depth,
            ordered_entries,
            args.include_details,
            args.include_provenance,
            args.include_derived_provenance,
            args.include_inactive,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
