#!/usr/bin/env python3
"""Load lightweight descriptions from one, multiple, or all task context files."""

import argparse
import json
import os
import re
import sys
from pathlib import Path


FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n?", re.DOTALL)
SECTION_RE = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Load context descriptions from one, multiple, or all "
            "task context files."
        )
    )
    parser.add_argument(
        "targets",
        nargs="*",
        help=(
            "Context names, context directories, or explicit context.md paths. "
            "If omitted, the active context from .zero-memory/tmp/current-context.txt is used "
            "when set; otherwise the default context is used."
        ),
    )
    parser.add_argument(
        "--root",
        default=".zero-memory/context",
        help="Context root directory. Defaults to .zero-memory/context",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Load every <root>/*/context.md file.",
    )
    parser.add_argument(
        "--format",
        choices=("markdown", "json"),
        default="markdown",
        help="Output format. Defaults to markdown.",
    )
    return parser.parse_args()


def parse_frontmatter(text):
    match = FRONTMATTER_RE.match(text)
    if not match:
        return {}, text

    body = text[match.end() :]
    data = {}
    current_key = None

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


def display_path(path):
    absolute_path = os.path.abspath(str(path))
    cwd = os.path.abspath(os.getcwd())

    try:
        relative_path = os.path.relpath(absolute_path, cwd)
    except ValueError:
        return absolute_path

    if relative_path == ".":
        return "."
    if relative_path == ".." or relative_path.startswith(".." + os.sep):
        return absolute_path
    return relative_path


def first_meaningful_line(text):
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("- ") or line.startswith("* "):
            line = line[2:].strip()
        else:
            line = re.sub(r"^\d+\.\s+", "", line)
        return compact_text(line)
    return ""


def summarize_status(text):
    status = first_meaningful_line(text)
    if status.lower().startswith("state:"):
        return status.split(":", 1)[1].strip()
    return status


def resolve_target(target, root):
    candidate = Path(target)
    if target.endswith(".md"):
        return candidate
    if candidate.is_absolute() or "/" in target or os.sep in target:
        return candidate / "context.md"
    return root / target / "context.md"


def resolve_active_context_file(root):
    env_value = os.environ.get("TASK_CONTEXT_ACTIVE_CONTEXT_FILE", "").strip()
    if env_value:
        return [Path(env_value)]
    workspace_root = root.resolve().parent.parent
    return [
        workspace_root / ".zero-memory" / "tmp" / "current-context.txt",
        workspace_root / "tmp" / "current-context.txt",
    ]


def read_active_context_path(root):
    for active_file in resolve_active_context_file(root):
        if not active_file.is_file():
            default_path = root / "default" / "context.md"
            active_file.parent.mkdir(parents=True, exist_ok=True)
            active_file.write_text(str(default_path.resolve()) + "\n", encoding="utf-8")
            return str(default_path)
        try:
            value = active_file.read_text(encoding="utf-8").splitlines()[0].strip()
        except IndexError:
            value = ""
        except OSError:
            value = ""
        if value:
            return value
        default_path = root / "default" / "context.md"
        active_file.write_text(str(default_path.resolve()) + "\n", encoding="utf-8")
        return str(default_path)
    return str(root / "default" / "context.md")


def iter_context_files(root):
    return sorted(root.glob("*/context.md"))


def add_candidate(path, selected, seen, errors):
    key = os.path.abspath(str(path))
    if key in seen:
        return
    seen.add(key)

    if not path.exists():
        errors.append("Context file does not exist: {0}".format(path))
        return
    if not path.is_file():
        errors.append("Context path is not a file: {0}".format(path))
        return

    selected.append(path)


def collect_context_files(args):
    root = Path(args.root)
    selected = []
    seen = set()
    errors = []

    if args.all:
        if not root.exists():
            errors.append("Context root does not exist: {0}".format(root))
        else:
            for path in iter_context_files(root):
                add_candidate(path, selected, seen, errors)

    requested_targets = list(args.targets)
    if not requested_targets and not args.all:
        active_path = read_active_context_path(root)
        if active_path:
            requested_targets.append(active_path)

    for target in requested_targets:
        add_candidate(resolve_target(target, root), selected, seen, errors)

    if not selected and not errors:
        errors.append(
            "No contexts selected. Pass targets, use --all, or create .zero-memory/context/default/context.md."
        )

    return selected, errors


def load_context_file(context_file):
    raw_text = context_file.read_text(encoding="utf-8")
    frontmatter, body = parse_frontmatter(raw_text)
    sections = parse_sections(body)

    name = str(frontmatter.get("name") or context_file.parent.name).strip()
    description = str(frontmatter.get("description") or "").strip()
    if not description:
        description = first_meaningful_line(sections.get("Description", ""))
    if not description:
        description = first_meaningful_line(sections.get("Goal", ""))

    return {
        "name": name or context_file.parent.name,
        "path": display_path(context_file),
        "description": description,
        "status": summarize_status(sections.get("Status", "")),
    }


def render_markdown(entries):
    lines = ["# Context Descriptions", ""]
    if not entries:
        lines.extend(["No context files found.", ""])
        return "\n".join(lines)

    for entry in entries:
        lines.append("## {0}".format(entry["name"]))
        lines.append("")
        lines.append("- Path: `{0}`".format(entry["path"]))
        lines.append(
            "- Description: {0}".format(entry["description"] or "(missing)")
        )
        if entry["status"]:
            lines.append("- Status: {0}".format(entry["status"]))
        lines.append("")
    return "\n".join(lines)


def main():
    args = parse_args()
    context_files, errors = collect_context_files(args)

    if errors:
        for message in errors:
            print(message, file=sys.stderr)
        if not context_files:
            return 1

    entries = [load_context_file(path) for path in context_files]

    if args.format == "json":
        print(json.dumps(entries, indent=2, ensure_ascii=True))
        return 0

    print(render_markdown(entries))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
