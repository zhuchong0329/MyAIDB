#!/usr/bin/env python3
"""Load lightweight descriptions from flat memory packages under ./.zero-memory/memory/."""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple


FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n?", re.DOTALL)
SECTION_RE = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Scan ./.zero-memory/memory/*/MEMORY.md and print lightweight memory descriptions."
    )
    parser.add_argument(
        "--root",
        default=".zero-memory/memory",
        help="Memory root directory. Defaults to .zero-memory/memory",
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
        help="Include the Details section in the output.",
    )
    return parser.parse_args()


def parse_frontmatter(text):
    match = FRONTMATTER_RE.match(text)
    if not match:
        return {}, text

    body = text[match.end() :]
    data = {}
    current_key = None  # type: Optional[str]

    for raw_line in match.group(1).splitlines():
        line = raw_line.rstrip()
        if not line.strip():
            continue
        if line.startswith("  - ") and current_key:
            data.setdefault(current_key, [])
            if isinstance(data[current_key], list):
                data[current_key].append(line[4:].strip())
            continue
        if ":" not in line:
            current_key = None
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if not value:
            data[key] = []
        else:
            data[key] = value
        current_key = key

    return data, body


def parse_sections(text):
    matches = list(SECTION_RE.finditer(text))
    sections = {}
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        title = match.group(1).strip()
        sections[title] = text[start:end].strip()
    return sections


def compact_text(text):
    return " ".join(text.split())


def load_memory_package(memory_file):
    raw_text = memory_file.read_text(encoding="utf-8")
    frontmatter, body = parse_frontmatter(raw_text)
    sections = parse_sections(body)

    name = str(frontmatter.get("name") or memory_file.parent.name)
    description = str(frontmatter.get("description") or "").strip()
    if not description:
        description = compact_text(sections.get("Description", ""))
    details = compact_text(sections.get("Details", ""))

    return {
        "name": name,
        "path": str(memory_file),
        "description": description,
        "details": details,
        "tags": frontmatter.get("tags", []),
        "pattern_key": frontmatter.get("pattern_key", ""),
    }


def iter_memory_files(root):
    return sorted(root.glob("*/MEMORY.md"))


def render_markdown(entries, include_details):
    lines = ["# Memory Descriptions", ""]
    if not entries:
        lines.extend(["No memory packages found.", ""])
        return "\n".join(lines)

    for entry in entries:
        lines.append(f"## {entry['name']}")
        lines.append("")
        lines.append(f"- Path: `{entry['path']}`")
        lines.append(f"- Description: {entry['description'] or '(missing)'}")
        if entry["pattern_key"]:
            lines.append(f"- Pattern-Key: `{entry['pattern_key']}`")
        tags = entry.get("tags")
        if isinstance(tags, list) and tags:
            lines.append(f"- Tags: {', '.join(str(tag) for tag in tags)}")
        if include_details and entry["details"]:
            lines.append(f"- Details: {entry['details']}")
        lines.append("")
    return "\n".join(lines)


def main():
    args = parse_args()
    root = Path(args.root)
    if not root.exists():
        print(f"Memory root does not exist: {root}", file=sys.stderr)
        return 1

    entries = [load_memory_package(path) for path in iter_memory_files(root)]

    if args.format == "json":
        if not args.include_details:
            for entry in entries:
                entry.pop("details", None)
        print(json.dumps(entries, indent=2, ensure_ascii=True))
        return 0

    print(render_markdown(entries, args.include_details))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
