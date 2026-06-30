#!/usr/bin/env python3
"""Compact an oversized task context into summary-first form plus references."""

import argparse
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n?", re.DOTALL)
SECTION_RE = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)

REFERENCE_BUCKET_ORDER = (
    "analysis",
    "decisions",
    "verification",
    "history",
    "artifacts",
)
REFERENCE_BUCKET_TITLES = {
    "analysis": "Analysis",
    "decisions": "Decisions",
    "verification": "Verification",
    "history": "History",
    "artifacts": "Artifacts",
}
REFERENCE_BUCKET_NOTES = {
    "analysis": "Durable task analysis split out of the main context summary.",
    "decisions": "Decision and rationale detail preserved from the larger context.",
    "verification": "Verification detail preserved from the larger context.",
    "history": "Progress, completion, and resume chronology preserved from the larger context.",
    "artifacts": "Paths, scripts, and supporting artifact references preserved from the larger context.",
}


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Compact a large context.md into a short restart-safe summary plus reference files."
        )
    )
    parser.add_argument(
        "--context-path",
        help=(
            "Explicit context.md path. Defaults to the active path in "
            ".zero-memory/tmp/current-context.txt when set."
        ),
    )
    parser.add_argument(
        "--max-lines",
        type=int,
        default=200,
        help="Hard line cap for context.md. Defaults to 200.",
    )
    parser.add_argument(
        "--max-bytes",
        type=int,
        default=20000,
        help="Hard byte cap for context.md. Defaults to 20000.",
    )
    parser.add_argument(
        "--target-lines",
        type=int,
        default=120,
        help="Soft target line budget for the rewritten context.md. Defaults to 120.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Compact even when the current file is not over the hard size limits.",
    )
    parser.add_argument(
        "--no-snapshot",
        action="store_true",
        help="Skip writing a raw snapshot under references/snapshots/.",
    )
    return parser.parse_args()


def resolve_context_path(explicit_path):
    if explicit_path:
        return explicit_path
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
            return active_path
    default_path = str(
        Path(workspace_root) / ".zero-memory" / "context" / "default" / "context.md"
    )
    for candidate in active_files:
        try:
            candidate.parent.mkdir(parents=True, exist_ok=True)
            candidate.write_text(default_path + "\n", encoding="utf-8")
            break
        except OSError:
            continue
    return default_path


def parse_frontmatter(raw_text):
    match = FRONTMATTER_RE.match(raw_text)
    if not match:
        return "", raw_text
    return match.group(1).strip(), raw_text[match.end() :]


def parse_sections(text):
    matches = list(SECTION_RE.finditer(text))
    sections = {}
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        sections[match.group(1).strip()] = text[start:end].strip()
    return sections


def clean_lines(text):
    return [line.rstrip() for line in text.splitlines() if line.strip()]


def compact_text(text, limit):
    joined = " ".join(
        line.strip().lstrip("-").strip()
        for line in text.splitlines()
        if line.strip()
    )
    if len(joined) <= limit:
        return joined
    truncated = joined[:limit].rsplit(" ", 1)[0].rstrip()
    return truncated + "..."


def classify_section(title):
    normalized = title.strip().lower()
    if any(term in normalized for term in ("decision",)):
        return "decisions"
    if any(term in normalized for term in ("verification",)):
        return "verification"
    if any(term in normalized for term in ("progress", "completion", "resume", "history")):
        return "history"
    if any(
        term in normalized
        for term in ("goal", "understanding", "assumption", "analysis")
    ):
        return "analysis"
    if any(
        term in normalized
        for term in ("touched", "file", "system", "script", "artifact", "reference", "context path")
    ):
        return "artifacts"
    return "history"


def build_reference_contents(sections):
    buckets = {bucket: [] for bucket in REFERENCE_BUCKET_ORDER}
    for title, body in sections.items():
        bucket = classify_section(title)
        buckets[bucket].append((title, body))
    return buckets


def render_reference_file(bucket, entries):
    lines = [
        "# {0}".format(REFERENCE_BUCKET_TITLES[bucket]),
        "",
        REFERENCE_BUCKET_NOTES[bucket],
        "",
    ]
    for title, body in entries:
        lines.append("## {0}".format(title))
        lines.append("")
        if body:
            lines.append(body.rstrip())
        else:
            lines.append("(empty)")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def render_status_section(sections):
    status_lines = clean_lines(sections.get("Status", ""))
    if status_lines:
        return status_lines[:12]
    return ["- active"]


def render_current_summary_section(sections):
    if sections.get("Current Summary"):
        existing = clean_lines(sections["Current Summary"])
        return existing[:18]

    summary_lines = []
    if sections.get("Goal"):
        summary_lines.append("- Goal: {0}".format(compact_text(sections["Goal"], 240)))
    if sections.get("Current Understanding"):
        summary_lines.append(
            "- Current understanding: {0}".format(
                compact_text(sections["Current Understanding"], 320)
            )
        )
    if sections.get("Decisions"):
        summary_lines.append(
            "- Key decisions: {0}".format(compact_text(sections["Decisions"], 240))
        )
    if sections.get("Verification"):
        summary_lines.append(
            "- Verification: {0}".format(compact_text(sections["Verification"], 220))
        )
    if sections.get("Assumptions To Verify"):
        summary_lines.append(
            "- Assumptions to verify: {0}".format(
                compact_text(sections["Assumptions To Verify"], 200)
            )
        )
    if not summary_lines:
        summary_lines.append("- See the reference files for the full preserved task detail.")
    return summary_lines[:18]


def render_next_step_section(sections):
    if sections.get("Next Step"):
        return clean_lines(sections["Next Step"])[:8]

    resume_lines = clean_lines(sections.get("Resume From Here", ""))
    for line in resume_lines:
        if "next step:" in line.lower():
            return [line]
    if resume_lines:
        return resume_lines[:6]

    verification_lines = clean_lines(sections.get("Verification", ""))
    pending = [line for line in verification_lines if "pending:" in line.lower()]
    if pending:
        return pending[:4]
    return ["- Review the reference files and continue from the latest preserved milestone."]


def write_snapshot(context_dir, raw_text):
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    snapshot_dir = context_dir / "references" / "snapshots"
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    snapshot_path = snapshot_dir / ("context-{0}.md".format(timestamp))
    snapshot_path.write_text(raw_text, encoding="utf-8")
    return snapshot_path


def render_compacted_context(frontmatter_text, sections, written_references, context_dir):
    lines = ["---"]
    if frontmatter_text:
        lines.extend(frontmatter_text.splitlines())
    lines.extend(
        [
            "---",
            "",
            "## Status",
            "",
        ]
    )
    lines.extend(render_status_section(sections))
    lines.extend(
        [
            "",
            "## Current Summary",
            "",
        ]
    )
    lines.extend(render_current_summary_section(sections))
    lines.extend(
        [
            "",
            "## Next Step",
            "",
        ]
    )
    lines.extend(render_next_step_section(sections))
    lines.extend(
        [
            "",
            "## References",
            "",
        ]
    )
    for bucket, reference_path in written_references:
        rel_path = reference_path.relative_to(context_dir)
        lines.append(
            "- `{0}` - {1}".format(rel_path.as_posix(), REFERENCE_BUCKET_NOTES[bucket])
        )

    lines.append("")
    return "\n".join(lines)


def main():
    args = parse_args()
    context_path = resolve_context_path(args.context_path)
    if not context_path:
        print(
            "No context path selected. Pass --context-path or create .zero-memory/context/default/context.md.",
            file=sys.stderr,
        )
        return 1

    path = Path(context_path)
    if not path.exists():
        print("Context path does not exist: {0}".format(path), file=sys.stderr)
        return 1

    raw_text = path.read_text(encoding="utf-8")
    original_line_count = len(raw_text.splitlines())
    original_byte_count = len(raw_text.encode("utf-8"))
    if (
        original_line_count <= args.max_lines
        and original_byte_count <= args.max_bytes
        and not args.force
    ):
        print(
            "Context is already within the hard limits ({0} lines <= {1}, {2} bytes <= {3}); no compaction needed.".format(
                original_line_count, args.max_lines
                , original_byte_count, args.max_bytes
            )
        )
        return 0

    frontmatter_text, body = parse_frontmatter(raw_text)
    sections = parse_sections(body)
    context_dir = path.parent
    references_dir = context_dir / "references"
    references_dir.mkdir(parents=True, exist_ok=True)

    written_references = []
    buckets = build_reference_contents(sections)
    for bucket in REFERENCE_BUCKET_ORDER:
        entries = buckets[bucket]
        if not entries:
            continue
        reference_path = references_dir / ("{0}.md".format(bucket))
        reference_path.write_text(
            render_reference_file(bucket, entries),
            encoding="utf-8",
        )
        written_references.append((bucket, reference_path))

    if not args.no_snapshot:
        snapshot_path = write_snapshot(context_dir, raw_text)
        written_references.append(("history", snapshot_path))

    rewritten = render_compacted_context(
        frontmatter_text,
        sections,
        written_references,
        context_dir,
    )
    rewritten_line_count = len(rewritten.splitlines())
    rewritten_byte_count = len(rewritten.encode("utf-8"))
    if rewritten_line_count > args.max_lines:
        print(
            "Compaction failed: rewritten context is still above the hard line limit ({0} > {1}).".format(
                rewritten_line_count, args.max_lines
            ),
            file=sys.stderr,
        )
        return 1
    if rewritten_byte_count > args.max_bytes:
        print(
            "Compaction failed: rewritten context is still above the hard byte limit ({0} > {1}).".format(
                rewritten_byte_count, args.max_bytes
            ),
            file=sys.stderr,
        )
        return 1
    if rewritten_line_count > args.target_lines:
        print(
            "Compaction warning: rewritten context is above the target budget ({0} > {1}) but still within the hard limit.".format(
                rewritten_line_count, args.target_lines
            ),
            file=sys.stderr,
        )

    path.write_text(rewritten, encoding="utf-8")
    print(
        "Compacted `{0}` from {1} lines / {2} bytes to {3} lines / {4} bytes and wrote {5} reference file(s).".format(
            path,
            original_line_count,
            original_byte_count,
            rewritten_line_count,
            rewritten_byte_count,
            len(written_references),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
