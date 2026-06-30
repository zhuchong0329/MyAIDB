#!/usr/bin/env python3
"""Query generated zero-memory lookup indexes without rescanning MEMORY.md files."""

import argparse
import json
import sys

from memory_graph_common import INDEX_FILENAMES, load_memory_index, memory_index_root
from memory_observability import write_jsonl_event


SCRIPT_PATH = "skills/zero-memory-curator/scripts/query_memory_index.py"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Query generated zero-memory indexes under .zero-memory/memory/index/."
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
        help="Query the `all` view instead of the default active-only view.",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--parent-of",
        help="Return parent memory IDs whose `load_next` contains this child memory ID.",
    )
    group.add_argument(
        "--pattern-key",
        help="Return memory IDs indexed by this exact pattern key.",
    )
    group.add_argument(
        "--related-file",
        help="Return memory IDs indexed by this exact related file path.",
    )
    group.add_argument(
        "--related-symbol",
        help="Return memory IDs indexed by this exact related symbol.",
    )
    return parser.parse_args()


def resolve_query(args):
    if args.parent_of:
        return ("reverse_load_next", args.parent_of, "parent-of")
    if args.pattern_key:
        return ("by_pattern_key", args.pattern_key, "pattern-key")
    if args.related_file:
        return ("by_related_file", args.related_file, "related-file")
    return ("by_related_symbol", args.related_symbol, "related-symbol")


def render_markdown(root, filename, query_kind, query_value, include_inactive, matches):
    lines = [
        "# Memory Index Query",
        "",
        "- Root: `{0}`".format(root),
        "- Index File: `{0}`".format(memory_index_root(root) / filename),
        "- Query Kind: `{0}`".format(query_kind),
        "- Query Value: `{0}`".format(query_value),
        "- Include Inactive: `{0}`".format("yes" if include_inactive else "no"),
        "- Match Count: {0}".format(len(matches)),
        "",
    ]
    if not matches:
        lines.extend(["No matches found.", ""])
        return "\n".join(lines)
    lines.append("## Matches")
    lines.append("")
    for memory_id in matches:
        lines.append("- `{0}`".format(memory_id))
    lines.append("")
    return "\n".join(lines)


def main():
    args = parse_args()
    index_key, query_value, query_kind = resolve_query(args)
    filename = INDEX_FILENAMES[index_key]
    payload = load_memory_index(args.root, filename)
    if payload is None:
        print(
            "Generated index `{0}` is missing under `{1}`. Run `python3 skills/zero-memory-curator/scripts/validate_memory_graph.py --root {2} --repair` first.".format(
                filename,
                memory_index_root(args.root),
                args.root,
            ),
            file=sys.stderr,
        )
        return 1

    scope = "all" if args.include_inactive else "active"
    matches = payload.get(scope, {}).get(query_value, [])
    write_jsonl_event(
        args.root,
        "recall.index-query",
        skill="zero-memory-curator",
        script=SCRIPT_PATH,
        memory_ids=matches,
        extra={
            "query_kind": query_kind,
            "query_value": query_value,
            "include_inactive": args.include_inactive,
            "returned_memory_ids": matches,
            "returned_count": len(matches),
        },
    )
    if args.format == "json":
        print(
            json.dumps(
                {
                    "root": args.root,
                    "index_file": str(memory_index_root(args.root) / filename),
                    "query_kind": query_kind,
                    "query_value": query_value,
                    "include_inactive": args.include_inactive,
                    "count": len(matches),
                    "matches": matches,
                },
                indent=2,
                ensure_ascii=True,
            )
        )
        return 0

    print(
        render_markdown(
            args.root,
            filename,
            query_kind,
            query_value,
            args.include_inactive,
            matches,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
