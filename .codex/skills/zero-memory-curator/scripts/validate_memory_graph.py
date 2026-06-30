#!/usr/bin/env python3
"""Validate the zero-memory graph and optionally repair safe metadata drift."""

import argparse
import json
import re
import sys

from memory_graph_common import (
    VALID_FRESHNESS_PROFILES,
    VALID_MEMORY_STATUSES,
    bfs_levels,
    build_package_map,
    canonical_registry_path,
    check_memory_index_drift,
    find_load_next_cycles,
    format_cycle,
    is_active_memory,
    load_init_memory_set,
    load_memory_packages,
    load_registry,
    make_registry_entries,
    parse_utc_timestamp,
    sync_memory_indexes,
    update_memory_frontmatter,
    write_init_memory_set,
    write_registry,
)


TIMESTAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$")
MAX_DESCRIPTION_DETAILS_LINES = 100


def parse_args():
    parser = argparse.ArgumentParser(
        description="Validate reachability and metadata consistency for .zero-memory/memory."
    )
    parser.add_argument(
        "--root",
        default=".zero-memory/memory",
        help="Memory root directory. Defaults to .zero-memory/memory.",
    )
    parser.add_argument(
        "--repair",
        action="store_true",
        help="Attempt safe repairs for registry drift and missing init-set metadata.",
    )
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format. Defaults to text.",
    )
    return parser.parse_args()


def _active_child_ids(package_map, package):
    return [
        child_id
        for child_id in package["load_next"]
        if child_id in package_map and is_active_memory(package_map[child_id])
    ]


def _non_empty_line_count(text):
    return len([line for line in (text or "").splitlines() if line.strip()])


def _description_details_line_count(package):
    sections = package["sections"]
    description_lines = _non_empty_line_count(sections.get("Description", ""))
    if not description_lines and package["description"]:
        description_lines = 1
    return description_lines + _non_empty_line_count(sections.get("Details", ""))


def collect_issues(root):
    packages, duplicate_ids = load_memory_packages(root)
    package_map = build_package_map(packages)
    registry_entries = load_registry(root)
    init_ids = load_init_memory_set(root)

    errors = []
    warnings = []
    registry_by_id = {}
    registry_duplicate_ids = {}
    superseded_by_candidates = {}
    abstracted_by_candidates = {}

    if not packages:
        warnings.append("No memory packages found under `{0}`.".format(root))
        return {
            "packages": packages,
            "package_map": package_map,
            "registry_entries": registry_entries,
            "registry_by_id": registry_by_id,
            "init_ids": init_ids,
            "errors": errors,
            "warnings": warnings,
            "duplicate_ids": duplicate_ids,
            "cycles": [],
            "reachable_levels": {},
            "superseded_by_candidates": superseded_by_candidates,
            "abstracted_by_candidates": abstracted_by_candidates,
        }

    if duplicate_ids:
        for memory_id in sorted(duplicate_ids):
            errors.append(
                "duplicate package id `{0}` in {1}".format(
                    memory_id, ", ".join(sorted(duplicate_ids[memory_id]))
                )
            )

    for entry in registry_entries:
        memory_id = entry.get("id", "")
        if not memory_id:
            errors.append("registry entry missing `id`")
            continue
        registry_duplicate_ids.setdefault(memory_id, []).append(entry)
        if memory_id not in registry_by_id:
            registry_by_id[memory_id] = entry

    for memory_id, entries in sorted(registry_duplicate_ids.items()):
        if len(entries) > 1:
            errors.append("duplicate registry id `{0}`".format(memory_id))

    if not init_ids:
        errors.append("init-memory-set.yml is empty")

    for package in packages:
        if not package["declared_id"]:
            errors.append("missing frontmatter `id` in `{0}`".format(package["path"]))

        if package["declared_status"] and package["status"] not in VALID_MEMORY_STATUSES:
            errors.append(
                "invalid `status` value `{0}` in `{1}`".format(
                    package["declared_status"], package["path"]
                )
            )

        if (
            package["declared_freshness_profile"]
            and package["freshness_profile"] not in VALID_FRESHNESS_PROFILES
        ):
            errors.append(
                "invalid `freshness_profile` value `{0}` in `{1}`".format(
                    package["declared_freshness_profile"], package["path"]
                )
            )

        registry_entry = registry_by_id.get(package["id"])
        if registry_entry is None:
            errors.append("missing registry entry for `{0}`".format(package["id"]))
        else:
            expected_path = canonical_registry_path(root, package["path"])
            if registry_entry.get("slug") != package["slug"]:
                errors.append(
                    "registry slug drift for `{0}`: `{1}` != `{2}`".format(
                        package["id"], registry_entry.get("slug", ""), package["slug"]
                    )
                )
            if registry_entry.get("path") != expected_path:
                errors.append(
                    "registry path drift for `{0}`: `{1}` != `{2}`".format(
                        package["id"], registry_entry.get("path", ""), expected_path
                    )
                )

        for field_name in ("load_next", "related", "supersedes", "abstracts"):
            for target_id in package[field_name]:
                if target_id not in package_map:
                    errors.append(
                        "missing `{0}` reference `{1}` from `{2}`".format(
                            field_name, target_id, package["id"]
                        )
                    )
                    continue
                if (
                    field_name == "load_next"
                    and is_active_memory(package)
                    and not is_active_memory(package_map[target_id])
                ):
                    errors.append(
                        "active `load_next` edge from `{0}` points to inactive memory `{1}`".format(
                            package["id"], target_id
                        )
                    )

        if package["recurrence_count_raw"] and package["recurrence_count"] is None:
            errors.append(
                "malformed `recurrence_count` in `{0}`".format(package["path"])
            )
        elif package["recurrence_count"] is not None and package["recurrence_count"] < 0:
            errors.append(
                "negative `recurrence_count` in `{0}`".format(package["path"])
            )

        if package["last_confirmed_at"] and not TIMESTAMP_RE.match(
            package["last_confirmed_at"]
        ):
            errors.append(
                "invalid `last_confirmed_at` timestamp in `{0}`".format(package["path"])
            )

        if package["last_updated_at"]:
            if not TIMESTAMP_RE.match(package["last_updated_at"]):
                errors.append(
                    "invalid `last_updated_at` timestamp in `{0}`".format(package["path"])
                )
            elif parse_utc_timestamp(package["last_updated_at"]) is None:
                errors.append(
                    "unparseable `last_updated_at` timestamp in `{0}`".format(
                        package["path"]
                    )
                )
        elif (
            package["declared_freshness_profile"]
            and package["freshness_profile"] in ("code-env", "workflow")
        ):
            warnings.append(
                "`{0}` declares `freshness_profile: {1}` but has no `last_updated_at`".format(
                    package["id"], package["freshness_profile"]
                )
            )

        if package["recent_confirmation_ids"]:
            if len(package["recent_confirmation_ids"]) != len(
                set(package["recent_confirmation_ids"])
            ):
                warnings.append(
                    "duplicate `recent_confirmation_ids` in `{0}`".format(package["id"])
                )
            if package["recurrence_count"] is None:
                warnings.append(
                    "`{0}` has `recent_confirmation_ids` but no `recurrence_count`".format(
                        package["id"]
                    )
                )
            elif package["recurrence_count"] < len(package["recent_confirmation_ids"]):
                warnings.append(
                    "`{0}` has `recurrence_count` smaller than `recent_confirmation_ids`".format(
                        package["id"]
                    )
                )

        active_child_ids = _active_child_ids(package_map, package)
        description_details_lines = _description_details_line_count(package)
        if (
            is_active_memory(package)
            and description_details_lines > MAX_DESCRIPTION_DETAILS_LINES
        ):
            warnings.append(
                "active memory `{0}` has {1} non-empty `Description` + `Details` lines; split it into graph-linked memories and update `load_next` / parent routing".format(
                    package["id"], description_details_lines
                )
            )

        if not package["source_daily_learning_ids"]:
            if is_active_memory(package) and package["layer"] in ("detailed", "leaf"):
                errors.append(
                    "active `{0}` memory `{1}` has no direct daily-learning provenance".format(
                        package["layer"], package["id"]
                    )
                )
            elif is_active_memory(package) and not active_child_ids and not package["abstracts"]:
                warnings.append(
                    "active routing memory `{0}` has no direct daily-learning provenance and no active children".format(
                        package["id"]
                    )
                )

        if package["superseded_by"]:
            if package["superseded_by"] not in package_map:
                errors.append(
                    "missing `superseded_by` reference `{0}` from `{1}`".format(
                        package["superseded_by"], package["id"]
                    )
                )
            elif is_active_memory(package):
                errors.append(
                    "memory `{0}` has `superseded_by` but is still `active`".format(
                        package["id"]
                    )
                )
            elif package["id"] not in package_map[package["superseded_by"]]["supersedes"]:
                errors.append(
                    "missing reciprocal `supersedes` link from `{0}` back to `{1}`".format(
                        package["superseded_by"], package["id"]
                    )
                )

        if package["subsumed_by"]:
            if package["subsumed_by"] not in package_map:
                errors.append(
                    "missing `subsumed_by` reference `{0}` from `{1}`".format(
                        package["subsumed_by"], package["id"]
                    )
                )
            elif package["status"] != "subsumed":
                errors.append(
                    "memory `{0}` has `subsumed_by` but status is `{1}` instead of `subsumed`".format(
                        package["id"], package["status"]
                    )
                )
            elif not is_active_memory(package_map[package["subsumed_by"]]):
                errors.append(
                    "memory `{0}` is subsumed by inactive memory `{1}`".format(
                        package["id"], package["subsumed_by"]
                    )
                )
            elif package["id"] not in package_map[package["subsumed_by"]]["abstracts"]:
                errors.append(
                    "missing reciprocal `abstracts` link from `{0}` back to `{1}`".format(
                        package["subsumed_by"], package["id"]
                    )
                )

        if package["status"] == "subsumed" and not package["subsumed_by"]:
            errors.append(
                "memory `{0}` is `subsumed` but missing `subsumed_by`".format(
                    package["id"]
                )
            )

        if package["subsumed_by"] and (
            package["superseded_by"] or package["supersedes"]
        ):
            errors.append(
                "memory `{0}` mixes subsumption and supersession metadata".format(
                    package["id"]
                )
            )

        for superseded_id in package["supersedes"]:
            superseded_by_candidates.setdefault(superseded_id, []).append(package["id"])

        for abstracted_id in package["abstracts"]:
            abstracted_by_candidates.setdefault(abstracted_id, []).append(package["id"])

        if package["supersedes"] and "Correction" not in package["sections"]:
            warnings.append(
                "replacement memory `{0}` has `supersedes` but no `## Correction` section".format(
                    package["id"]
                )
            )

        if package["abstracts"] and not is_active_memory(package):
            errors.append(
                "memory `{0}` has `abstracts` but is not `active`".format(package["id"])
            )

        if package["status"] == "subsumed" and active_child_ids:
            errors.append(
                "memory `{0}` is `subsumed` but still has active children: {1}".format(
                    package["id"], ", ".join(active_child_ids)
                )
            )

    for old_id, new_ids in sorted(superseded_by_candidates.items()):
        if len(new_ids) > 1:
            errors.append(
                "memory `{0}` is superseded by multiple memories: {1}".format(
                    old_id, ", ".join(sorted(new_ids))
                )
            )
            continue
        new_id = new_ids[0]
        old_package = package_map.get(old_id)
        if old_package is None:
            continue
        if old_package["superseded_by"] and old_package["superseded_by"] != new_id:
            errors.append(
                "memory `{0}` has conflicting `superseded_by`: `{1}` != `{2}`".format(
                    old_id, old_package["superseded_by"], new_id
                )
            )
        elif not old_package["superseded_by"]:
            errors.append(
                "memory `{0}` is missing reciprocal `superseded_by: {1}`".format(
                    old_id, new_id
                )
            )
        if is_active_memory(old_package):
            errors.append(
                "memory `{0}` is superseded by `{1}` but is still `active`".format(
                    old_id, new_id
                )
            )

    for child_id, summary_ids in sorted(abstracted_by_candidates.items()):
        if len(summary_ids) > 1:
            errors.append(
                "memory `{0}` is abstracted by multiple memories: {1}".format(
                    child_id, ", ".join(sorted(summary_ids))
                )
            )
            continue
        summary_id = summary_ids[0]
        child_package = package_map.get(child_id)
        if child_package is None:
            continue
        if child_package["subsumed_by"] and child_package["subsumed_by"] != summary_id:
            errors.append(
                "memory `{0}` has conflicting `subsumed_by`: `{1}` != `{2}`".format(
                    child_id, child_package["subsumed_by"], summary_id
                )
            )
        elif not child_package["subsumed_by"]:
            errors.append(
                "memory `{0}` is missing reciprocal `subsumed_by: {1}`".format(
                    child_id, summary_id
                )
            )
        if child_package["status"] != "subsumed":
            errors.append(
                "memory `{0}` is abstracted by `{1}` but status is `{2}` instead of `subsumed`".format(
                    child_id, summary_id, child_package["status"]
                )
            )
        if _active_child_ids(package_map, child_package):
            errors.append(
                "memory `{0}` is abstracted by `{1}` but still has active children".format(
                    child_id, summary_id
                )
            )
        summary_package = package_map.get(summary_id)
        if summary_package is not None and not is_active_memory(summary_package):
            errors.append(
                "memory `{0}` abstracts `{1}` but is not `active`".format(
                    summary_id, child_id
                )
            )

    for memory_id, entry in sorted(registry_by_id.items()):
        if memory_id not in package_map:
            errors.append(
                "registry entry `{0}` points to missing package `{1}`".format(
                    memory_id, entry.get("path", "")
                )
            )

    missing_init_ids = [memory_id for memory_id in init_ids if memory_id not in package_map]
    for memory_id in missing_init_ids:
        errors.append("init memory `{0}` is missing on disk".format(memory_id))

    inactive_init_ids = [
        memory_id
        for memory_id in init_ids
        if memory_id in package_map and not is_active_memory(package_map[memory_id])
    ]
    for memory_id in inactive_init_ids:
        errors.append("init memory `{0}` is inactive".format(memory_id))

    reachable_levels = bfs_levels(package_map, init_ids, depth=None, include_inactive=False)
    for package in sorted(packages, key=lambda item: item["id"]):
        if is_active_memory(package) and package["id"] not in reachable_levels:
            errors.append("unreachable active memory `{0}`".format(package["id"]))

    cycles = find_load_next_cycles(package_map)
    for cycle in cycles:
        warnings.append("load_next cycle: {0}".format(format_cycle(cycle)))

    if len(init_ids) > 8:
        warnings.append(
            "init-memory-set.yml has {0} entries; keep it intentionally small".format(
                len(init_ids)
            )
        )

    warnings.extend(check_memory_index_drift(root, package_map))

    return {
        "packages": packages,
        "package_map": package_map,
        "registry_entries": registry_entries,
        "registry_by_id": registry_by_id,
        "init_ids": init_ids,
        "errors": sorted(set(errors)),
        "warnings": sorted(set(warnings)),
        "duplicate_ids": duplicate_ids,
        "cycles": cycles,
        "reachable_levels": reachable_levels,
        "superseded_by_candidates": superseded_by_candidates,
        "abstracted_by_candidates": abstracted_by_candidates,
    }


def attempt_repairs(root, issues):
    notes = []
    packages = issues["packages"]
    if not packages:
        return notes

    if not issues["duplicate_ids"]:
        expected_registry = make_registry_entries(root, packages)
        current_registry = sorted(
            issues["registry_entries"],
            key=lambda item: (
                item.get("id", ""),
                item.get("slug", ""),
                item.get("path", ""),
            ),
        )
        if current_registry != expected_registry:
            write_registry(root, expected_registry)
            notes.append("rewrote registry.yml from current package metadata")

    layer_init_ids = sorted(
        package["id"]
        for package in packages
        if package.get("layer") == "init" and is_active_memory(package)
    )
    current_init_ids = sorted(issues["init_ids"])
    if layer_init_ids and (
        not current_init_ids
        or any(memory_id not in issues["package_map"] for memory_id in issues["init_ids"])
        or any(
            memory_id in issues["package_map"]
            and not is_active_memory(issues["package_map"][memory_id])
            for memory_id in issues["init_ids"]
        )
    ):
        write_init_memory_set(root, layer_init_ids)
        notes.append("rewrote init-memory-set.yml from active packages marked `layer: init`")

    for old_id, new_ids in sorted(issues["superseded_by_candidates"].items()):
        if len(new_ids) != 1:
            continue
        old_package = issues["package_map"].get(old_id)
        if old_package is None:
            continue
        new_id = new_ids[0]
        updates = {}
        if not old_package["superseded_by"]:
            updates["superseded_by"] = new_id
        if old_package["status"] == "active":
            updates["status"] = "superseded"
        if updates:
            update_memory_frontmatter(old_package["path"], updates)
            notes.append(
                "updated `{0}` with supersession metadata from `{1}`".format(
                    old_id, new_id
                )
            )

    for child_id, summary_ids in sorted(issues["abstracted_by_candidates"].items()):
        if len(summary_ids) != 1:
            continue
        child_package = issues["package_map"].get(child_id)
        if child_package is None:
            continue
        summary_id = summary_ids[0]
        updates = {}
        if not child_package["subsumed_by"]:
            updates["subsumed_by"] = summary_id
        if child_package["status"] == "active":
            updates["status"] = "subsumed"
        if updates:
            update_memory_frontmatter(child_package["path"], updates)
            notes.append(
                "updated `{0}` with subsumption metadata from `{1}`".format(
                    child_id, summary_id
                )
            )

    notes.extend(sync_memory_indexes(root, issues["package_map"]))

    return notes


def render_text(root, issues, repair_notes, repaired_issues):
    effective = repaired_issues or issues
    status = "PASS" if not effective["errors"] else "FAIL"
    lines = [
        "Memory graph validation: {0}".format(status),
        "Root: {0}".format(root),
    ]
    if repair_notes:
        lines.append("Repairs:")
        for note in repair_notes:
            lines.append("- {0}".format(note))
    if effective["errors"]:
        lines.append("Errors:")
        for item in effective["errors"]:
            lines.append("- {0}".format(item))
    if effective["warnings"]:
        lines.append("Warnings:")
        for item in effective["warnings"]:
            lines.append("- {0}".format(item))
    if not effective["errors"] and not effective["warnings"]:
        lines.append("No errors or warnings.")
    return "\n".join(lines)


def render_json(root, issues, repair_notes, repaired_issues):
    effective = repaired_issues or issues
    payload = {
        "root": root,
        "status": "pass" if not effective["errors"] else "fail",
        "repairs": repair_notes,
        "errors": effective["errors"],
        "warnings": effective["warnings"],
        "init_ids": effective["init_ids"],
        "reachable_count": len(effective["reachable_levels"]),
        "package_count": len(effective["packages"]),
        "active_reachable_count": len(effective["reachable_levels"]),
    }
    return json.dumps(payload, indent=2, ensure_ascii=True)


def main():
    args = parse_args()
    initial_issues = collect_issues(args.root)
    repair_notes = []
    repaired_issues = None

    if args.repair:
        repair_notes = attempt_repairs(args.root, initial_issues)
        if repair_notes:
            repaired_issues = collect_issues(args.root)

    output = (
        render_json(args.root, initial_issues, repair_notes, repaired_issues)
        if args.format == "json"
        else render_text(args.root, initial_issues, repair_notes, repaired_issues)
    )
    print(output)

    effective = repaired_issues or initial_issues
    return 0 if not effective["errors"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
