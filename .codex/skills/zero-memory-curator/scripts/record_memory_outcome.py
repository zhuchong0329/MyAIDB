#!/usr/bin/env python3
"""Record explicit zero-memory recall selection and outcome signals."""

import argparse
import json

from memory_observability import dedupe, write_jsonl_event


SCRIPT_PATH = "skills/zero-memory-curator/scripts/record_memory_outcome.py"


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Record which recalled memories were selected, helpful, stale, or missed "
            "after a memory-driven task step."
        )
    )
    parser.add_argument(
        "--root",
        default=".zero-memory/memory",
        help="Memory root directory. Defaults to .zero-memory/memory.",
    )
    parser.add_argument(
        "--skill",
        default="zero-memory-curator",
        help="Owning skill name for the outcome event. Defaults to zero-memory-curator.",
    )
    parser.add_argument(
        "--candidate-memory-id",
        action="append",
        default=[],
        help="Candidate memory ID surfaced before selection. May be repeated.",
    )
    parser.add_argument(
        "--selected-memory-id",
        action="append",
        default=[],
        help="Memory ID selected as relevant. May be repeated.",
    )
    parser.add_argument(
        "--helpful-memory-id",
        action="append",
        default=[],
        help="Memory ID that was actually helpful. May be repeated.",
    )
    parser.add_argument(
        "--used-in-final-answer-memory-id",
        action="append",
        default=[],
        help="Helpful memory ID that materially influenced the final answer. May be repeated.",
    )
    parser.add_argument(
        "--false-positive-memory-id",
        action="append",
        default=[],
        help="Memory ID that looked relevant but turned out to be noise. May be repeated.",
    )
    parser.add_argument(
        "--stale-memory-id",
        action="append",
        default=[],
        help="Selected or helpful stale memory ID. May be repeated.",
    )
    parser.add_argument(
        "--missed-memory-id",
        action="append",
        default=[],
        help="Memory ID that should have been recalled earlier. May be repeated.",
    )
    parser.add_argument(
        "--route",
        action="append",
        default=[],
        help="Recall route or trace string such as workspace.agent.workflows -> memory.curator.workflow. May be repeated.",
    )
    parser.add_argument(
        "--selection-reason",
        help="Optional short explanation for why the selected memory was chosen.",
    )
    parser.add_argument(
        "--depth-to-selected",
        type=int,
        help="Optional depth from the start node to the selected memory set.",
    )
    parser.add_argument(
        "--candidate-count",
        type=int,
        help="Optional number of candidate memories considered before selection.",
    )
    parser.add_argument(
        "--note",
        help="Optional short outcome note.",
    )
    parser.add_argument(
        "--format",
        choices=("markdown", "json"),
        default="markdown",
        help="Output format. Defaults to markdown.",
    )
    return parser.parse_args()


def render_markdown(result):
    lines = [
        "# Memory Outcome Recorded",
        "",
        "- Root: `{0}`".format(result["root"]),
        "- Skill: `{0}`".format(result["skill"]),
        "- Selected Event ID: `{0}`".format(result["selected_event_id"] or "_none_"),
        "- Outcome Event ID: `{0}`".format(result["outcome_event_id"] or "_none_"),
        "- Candidate Memory IDs: {0}".format(
            ", ".join("`{0}`".format(item) for item in result["candidate_memory_ids"])
            or "_none_"
        ),
        "- Selected Memory IDs: {0}".format(
            ", ".join("`{0}`".format(item) for item in result["selected_memory_ids"])
            or "_none_"
        ),
        "- Helpful Memory IDs: {0}".format(
            ", ".join("`{0}`".format(item) for item in result["helpful_memory_ids"])
            or "_none_"
        ),
        "- Missed Memory IDs: {0}".format(
            ", ".join("`{0}`".format(item) for item in result["missed_memory_ids"])
            or "_none_"
        ),
        "",
    ]
    return "\n".join(lines)


def main():
    args = parse_args()
    candidate_memory_ids = dedupe(args.candidate_memory_id)
    selected_memory_ids = dedupe(args.selected_memory_id)
    helpful_memory_ids = dedupe(args.helpful_memory_id)
    final_memory_ids = dedupe(args.used_in_final_answer_memory_id)
    false_positive_memory_ids = dedupe(args.false_positive_memory_id)
    stale_memory_ids = dedupe(args.stale_memory_id)
    missed_memory_ids = dedupe(args.missed_memory_id)
    routes = dedupe(args.route)

    if not (
        candidate_memory_ids
        or selected_memory_ids
        or helpful_memory_ids
        or false_positive_memory_ids
        or stale_memory_ids
        or missed_memory_ids
    ):
        raise SystemExit(
            "Provide at least one candidate, selected, helpful, false-positive, stale, or missed memory ID."
        )

    candidate_count = args.candidate_count
    if candidate_count is None and candidate_memory_ids:
        candidate_count = len(candidate_memory_ids)

    selected_event = None
    if candidate_memory_ids or selected_memory_ids:
        selected_event = write_jsonl_event(
            args.root,
            "recall.selected",
            skill=args.skill,
            script=SCRIPT_PATH,
            memory_ids=selected_memory_ids or candidate_memory_ids,
            extra={
                "candidate_memory_ids": candidate_memory_ids,
                "candidate_count": candidate_count,
                "selected_memory_ids": selected_memory_ids,
                "selection_reason": (args.selection_reason or "").strip(),
                "depth_to_selected": args.depth_to_selected,
                "routes": routes,
            },
        )

    outcome_event = write_jsonl_event(
        args.root,
        "recall.outcome",
        skill=args.skill,
        script=SCRIPT_PATH,
        memory_ids=dedupe(
            selected_memory_ids
            + helpful_memory_ids
            + final_memory_ids
            + false_positive_memory_ids
            + stale_memory_ids
            + missed_memory_ids
        ),
        extra={
            "candidate_memory_ids": candidate_memory_ids,
            "candidate_count": candidate_count,
            "selected_memory_ids": selected_memory_ids,
            "helpful_memory_ids": helpful_memory_ids,
            "used_in_final_answer_memory_ids": final_memory_ids,
            "false_positive_memory_ids": false_positive_memory_ids,
            "stale_memory_ids": stale_memory_ids,
            "missed_memory_ids": missed_memory_ids,
            "depth_to_selected": args.depth_to_selected,
            "routes": routes,
            "notes": (args.note or "").strip(),
        },
    )

    result = {
        "root": args.root,
        "skill": args.skill,
        "candidate_memory_ids": candidate_memory_ids,
        "selected_memory_ids": selected_memory_ids,
        "helpful_memory_ids": helpful_memory_ids,
        "missed_memory_ids": missed_memory_ids,
        "selected_event_id": (selected_event or {}).get("event_id", ""),
        "outcome_event_id": (outcome_event or {}).get("event_id", ""),
    }
    if args.format == "json":
        print(json.dumps(result, indent=2, ensure_ascii=True))
    else:
        print(render_markdown(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
