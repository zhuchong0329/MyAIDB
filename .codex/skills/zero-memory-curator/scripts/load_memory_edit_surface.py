#!/usr/bin/env python3
"""Load a token-light edit surface for selected memory packages."""

import argparse
import json
import sys
from pathlib import Path

from memory_graph_common import (
    build_package_map,
    load_memory_package,
    load_memory_packages,
    render_frontmatter,
)
from memory_observability import write_jsonl_event


SCRIPT_PATH = "skills/zero-memory-curator/scripts/load_memory_edit_surface.py"


DEFAULT_FRONTMATTER_KEYS = [
    "id",
    "name",
    "description",
    "pattern_key",
    "component",
    "kind",
    "stage",
    "scope",
    "actionability",
    "layer",
    "status",
    "last_updated_at",
    "freshness_profile",
    "supersedes",
    "superseded_by",
    "abstracts",
    "subsumed_by",
    "load_next",
    "related",
    "related_files",
    "related_symbols",
]

DEFAULT_SECTIONS = ["Description", "Details"]
CANONICAL_PACKAGE_FIELDS = {
    "id",
    "name",
    "description",
    "pattern_key",
    "component",
    "kind",
    "stage",
    "scope",
    "actionability",
    "layer",
    "status",
    "last_updated_at",
    "freshness_profile",
    "supersedes",
    "superseded_by",
    "abstracts",
    "subsumed_by",
    "load_next",
    "related",
    "related_files",
    "related_symbols",
}


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Load only the frontmatter edit surface plus selected markdown sections for "
            "chosen memory packages."
        )
    )
    parser.add_argument(
        "--root",
        default=".zero-memory/memory",
        help="Memory root directory. Defaults to .zero-memory/memory.",
    )
    parser.add_argument(
        "--memory-id",
        action="append",
        default=[],
        help="Memory ID to inspect. May be repeated.",
    )
    parser.add_argument(
        "--slug",
        action="append",
        default=[],
        help="Memory slug to inspect. May be repeated.",
    )
    parser.add_argument(
        "--path",
        action="append",
        default=[],
        help="Explicit MEMORY.md path to inspect. May be repeated.",
    )
    parser.add_argument(
        "--section",
        action="append",
        default=[],
        help=(
            "Markdown section title to include. May be repeated. Defaults to "
            "`Description` and `Details`."
        ),
    )
    parser.add_argument(
        "--frontmatter-key",
        action="append",
        default=[],
        help=(
            "Frontmatter key to include. May be repeated. Defaults to a compact "
            "edit-surface subset."
        ),
    )
    parser.add_argument(
        "--all-frontmatter",
        action="store_true",
        help="Include all frontmatter fields instead of the compact default subset.",
    )
    parser.add_argument(
        "--format",
        choices=("markdown", "json"),
        default="markdown",
        help="Output format. Defaults to markdown.",
    )
    return parser.parse_args()


def unique(values):
    result = []
    seen = set()
    for value in values:
        item = str(value).strip()
        if not item or item in seen:
            continue
        result.append(item)
        seen.add(item)
    return result


def canonical_field_value(package, key):
    if key in package:
        return package[key]
    if key == "name":
        return package.get("name")
    return None


def build_frontmatter_surface(package, keys, include_all_frontmatter):
    if include_all_frontmatter:
        surface = dict(package.get("frontmatter", {}))
        for key in CANONICAL_PACKAGE_FIELDS:
            if key not in surface:
                value = canonical_field_value(package, key)
                if value not in (None, "", []):
                    surface[key] = value
        return surface

    surface = {}
    frontmatter = package.get("frontmatter", {})
    for key in keys:
        value = frontmatter.get(key)
        if value in (None, "", []):
            value = canonical_field_value(package, key)
        if value in (None, "", []):
            continue
        surface[key] = value
    return surface


def build_entry(package, sections, frontmatter_keys, include_all_frontmatter):
    return {
        "id": package["id"],
        "slug": package["slug"],
        "path": package["path"],
        "frontmatter": build_frontmatter_surface(
            package,
            frontmatter_keys,
            include_all_frontmatter=include_all_frontmatter,
        ),
        "sections": dict(
            (section_name, package.get("sections", {}).get(section_name, ""))
            for section_name in sections
        ),
    }


def render_markdown(root, sections, frontmatter_keys, include_all_frontmatter, entries):
    lines = [
        "# Memory Edit Surface",
        "",
        "- Root: `{0}`".format(root),
        "- Sections: {0}".format(
            ", ".join("`{0}`".format(item) for item in sections)
        ),
    ]
    if include_all_frontmatter:
        lines.append("- Frontmatter: `all`")
    else:
        lines.append(
            "- Frontmatter Keys: {0}".format(
                ", ".join("`{0}`".format(item) for item in frontmatter_keys)
            )
        )
    lines.append("")

    if not entries:
        lines.extend(["No matching memories found.", ""])
        return "\n".join(lines)

    for entry in entries:
        lines.append("## {0}".format(entry["id"]))
        lines.append("")
        lines.append("- Slug: `{0}`".format(entry["slug"]))
        lines.append("- Path: `{0}`".format(entry["path"]))
        lines.append("")
        lines.append("### Frontmatter")
        lines.append("")
        lines.append("```yaml")
        rendered_frontmatter = render_frontmatter(entry["frontmatter"])
        lines.append(rendered_frontmatter or "# No selected frontmatter fields found.")
        lines.append("```")
        lines.append("")

        for section_name in sections:
            lines.append("### {0}".format(section_name))
            lines.append("")
            lines.append(entry["sections"].get(section_name) or "(missing)")
            lines.append("")
    return "\n".join(lines)


def build_indexes(packages):
    package_map = build_package_map(packages)
    slug_map = {}
    path_map = {}
    for package in packages:
        if package["slug"] not in slug_map:
            slug_map[package["slug"]] = package
        path_map[str(Path(package["path"]))] = package
    return package_map, slug_map, path_map


def main():
    args = parse_args()
    if not (args.memory_id or args.slug or args.path):
        print(
            "At least one `--memory-id`, `--slug`, or `--path` target is required.",
            file=sys.stderr,
        )
        return 1

    packages, duplicate_ids = load_memory_packages(args.root)
    if duplicate_ids:
        print(
            "Duplicate memory IDs exist; resolve them before using this helper.",
            file=sys.stderr,
        )
        return 1

    package_map, slug_map, path_map = build_indexes(packages)
    sections = unique(args.section or DEFAULT_SECTIONS)
    frontmatter_keys = unique(args.frontmatter_key or DEFAULT_FRONTMATTER_KEYS)
    entries = []
    missing_targets = []
    seen_ids = set()

    for memory_id in unique(args.memory_id):
        package = package_map.get(memory_id)
        if package is None:
            missing_targets.append("memory-id:{0}".format(memory_id))
            continue
        if package["id"] in seen_ids:
            continue
        entries.append(
            build_entry(
                package,
                sections,
                frontmatter_keys,
                include_all_frontmatter=args.all_frontmatter,
            )
        )
        seen_ids.add(package["id"])

    for slug in unique(args.slug):
        package = slug_map.get(slug)
        if package is None:
            missing_targets.append("slug:{0}".format(slug))
            continue
        if package["id"] in seen_ids:
            continue
        entries.append(
            build_entry(
                package,
                sections,
                frontmatter_keys,
                include_all_frontmatter=args.all_frontmatter,
            )
        )
        seen_ids.add(package["id"])

    for raw_path in unique(args.path):
        path = str(Path(raw_path))
        package = path_map.get(path)
        if package is None:
            file_path = Path(raw_path)
            if not file_path.exists():
                missing_targets.append("path:{0}".format(raw_path))
                continue
            package = load_memory_package(file_path)
        if package["id"] in seen_ids:
            continue
        entries.append(
            build_entry(
                package,
                sections,
                frontmatter_keys,
                include_all_frontmatter=args.all_frontmatter,
            )
        )
        seen_ids.add(package["id"])

    if missing_targets:
        print(
            "Missing targets: {0}".format(", ".join(missing_targets)),
            file=sys.stderr,
        )
        return 1

    write_jsonl_event(
        args.root,
        "recall.edit-surface",
        skill="zero-memory-curator",
        script=SCRIPT_PATH,
        memory_ids=[entry["id"] for entry in entries],
        extra={
            "selected_memory_ids": [entry["id"] for entry in entries],
            "sections": sections,
            "frontmatter_keys": [] if args.all_frontmatter else frontmatter_keys,
            "include_all_frontmatter": args.all_frontmatter,
            "entry_count": len(entries),
        },
    )

    if args.format == "json":
        payload = {
            "root": args.root,
            "sections": sections,
            "frontmatter_keys": None if args.all_frontmatter else frontmatter_keys,
            "include_all_frontmatter": args.all_frontmatter,
            "count": len(entries),
            "entries": entries,
        }
        print(json.dumps(payload, indent=2, ensure_ascii=True))
        return 0

    print(
        render_markdown(
            args.root,
            sections,
            frontmatter_keys,
            args.all_frontmatter,
            entries,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
