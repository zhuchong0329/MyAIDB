#!/usr/bin/env python3
"""Aggregate zero-memory observability events into human-readable reports."""

import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone

from memory_graph_common import (
    build_package_map,
    load_memory_packages,
    parse_utc_timestamp,
    resolve_freshness_profile,
)
from memory_observability import (
    dedupe,
    load_events_bundle,
    resolve_writer_id,
    write_report_set,
)


SCRIPT_PATH = "skills/zero-memory-curator/scripts/report_memory_observability.py"
FRESHNESS_TTL_HOURS = {"code-env": 24, "workflow": 24 * 7, "conceptual": None}


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Aggregate zero-memory observability events into hot-memory, routing-friction, "
            "reflection-priority, and stale-but-hot reports."
        )
    )
    parser.add_argument(
        "--root",
        default=".zero-memory/memory",
        help="Memory root directory. Defaults to .zero-memory/memory.",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=30,
        help="Rolling event window in days. Defaults to 30.",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=20,
        help="Maximum entries to emit per report. Defaults to 20.",
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
            "Compatibility alias for --write-latest. Writes tracked latest JSON and "
            "Markdown reports under .zero-memory/observability/reports/latest/."
        ),
    )
    parser.add_argument(
        "--write-latest",
        action="store_true",
        help=(
            "Write tracked latest JSON and Markdown reports under "
            ".zero-memory/observability/reports/latest/."
        ),
    )
    parser.add_argument(
        "--write-history",
        action="store_true",
        help=(
            "Write explicit audit/history snapshots under "
            ".zero-memory/observability/reports/history/YYYY-MM-DD/."
        ),
    )
    parser.add_argument(
        "--writer-scope",
        default="all",
        help=(
            "Event read scope. Defaults to `all`. Use `current` or a comma-separated "
            "list of writer IDs only for focused debugging."
        ),
    )
    return parser.parse_args()


def empty_metric():
    return {
        "recall_count": 0,
        "selected_count": 0,
        "helpful_count": 0,
        "used_in_final_answer_count": 0,
        "stale_hit_count": 0,
        "false_positive_count": 0,
        "missed_recall_count": 0,
        "selected_depths": [],
        "helpful_depths": [],
        "candidate_counts": [],
        "routes": Counter(),
        "last_used_at": "",
    }


def metric_for(metrics, memory_id):
    return metrics[memory_id]


def update_last_used(metric, timestamp):
    if timestamp and (not metric["last_used_at"] or timestamp > metric["last_used_at"]):
        metric["last_used_at"] = timestamp


def route_values(event):
    return dedupe(event.get("routes", []))


def record_depth(metric, key, value):
    if value is None:
        return
    try:
        metric[key].append(int(value))
    except (TypeError, ValueError):
        return


def average(values):
    if not values:
        return None
    return round(sum(values) / float(len(values)), 2)


def freshness_state(package, now):
    profile, _ = resolve_freshness_profile(package)
    ttl_hours = FRESHNESS_TTL_HOURS.get(profile)
    last_updated_at = package.get("last_updated_at", "")
    updated_at = parse_utc_timestamp(last_updated_at)
    if ttl_hours is None or updated_at is None:
        return profile, False
    age_hours = (now - updated_at).total_seconds() / 3600.0
    return profile, age_hours > ttl_hours


def candidate_problem_type(package, entry):
    if entry["missed_recall_count"] > 0 and not (
        package.get("pattern_key") or package.get("related_files") or package.get("related_symbols")
    ):
        return "metadata gap"
    if entry["avg_depth_to_helpful"] is not None and entry["avg_depth_to_helpful"] >= 2.0:
        return "routing gap"
    if entry["missed_recall_count"] > 0 and len(package.get("description", "")) < 120:
        return "description gap"
    if entry["stale_hit_count"] > 0:
        return "staleness gap"
    return "review needed"


def recommended_stale_action(entry):
    if entry["missed_recall_count"] > 0:
        return "refresh"
    if entry["false_positive_count"] > entry["helpful_count"] and entry["helpful_count"] > 0:
        return "split"
    if entry["stale_hit_count"] > 0:
        return "verify only"
    return "refresh"


def common_route_list(route_counter):
    return [
        {"route": route, "count": count}
        for route, count in route_counter.most_common(3)
    ]


def aggregate_metrics(events):
    metrics = defaultdict(empty_metric)
    for event in events:
        kind = str(event.get("kind", "")).strip()
        timestamp = str(event.get("timestamp", "")).strip()

        if kind in ("recall.graph-load", "recall.index-query"):
            for memory_id in dedupe(event.get("returned_memory_ids", [])):
                metric = metric_for(metrics, memory_id)
                metric["recall_count"] += 1
                update_last_used(metric, timestamp)
            continue

        if kind == "recall.edit-surface":
            for memory_id in dedupe(event.get("memory_ids", [])):
                metric = metric_for(metrics, memory_id)
                update_last_used(metric, timestamp)
            continue

        if kind == "recall.selected":
            candidate_count = event.get("candidate_count")
            if candidate_count is None:
                candidate_count = len(dedupe(event.get("candidate_memory_ids", [])))
            for memory_id in dedupe(event.get("selected_memory_ids", [])):
                metric = metric_for(metrics, memory_id)
                metric["selected_count"] += 1
                record_depth(metric, "selected_depths", event.get("depth_to_selected"))
                try:
                    metric["candidate_counts"].append(int(candidate_count))
                except (TypeError, ValueError):
                    pass
                for route in route_values(event):
                    metric["routes"][route] += 1
                update_last_used(metric, timestamp)
            continue

        if kind == "recall.outcome":
            for memory_id in dedupe(event.get("helpful_memory_ids", [])):
                metric = metric_for(metrics, memory_id)
                metric["helpful_count"] += 1
                record_depth(metric, "helpful_depths", event.get("depth_to_selected"))
                for route in route_values(event):
                    metric["routes"][route] += 1
                update_last_used(metric, timestamp)
            for memory_id in dedupe(event.get("used_in_final_answer_memory_ids", [])):
                metric = metric_for(metrics, memory_id)
                metric["used_in_final_answer_count"] += 1
                update_last_used(metric, timestamp)
            for memory_id in dedupe(event.get("false_positive_memory_ids", [])):
                metric = metric_for(metrics, memory_id)
                metric["false_positive_count"] += 1
                update_last_used(metric, timestamp)
            for memory_id in dedupe(event.get("stale_memory_ids", [])):
                metric = metric_for(metrics, memory_id)
                metric["stale_hit_count"] += 1
                update_last_used(metric, timestamp)
            for memory_id in dedupe(event.get("missed_memory_ids", [])):
                metric = metric_for(metrics, memory_id)
                metric["missed_recall_count"] += 1
                update_last_used(metric, timestamp)
            continue

        if kind == "reflection.miss-scaffolded":
            for memory_id in dedupe(
                event.get("missed_memory_ids", []) or [event.get("existing_memory_id", "")]
            ):
                metric = metric_for(metrics, memory_id)
                metric["missed_recall_count"] += 1
                update_last_used(metric, timestamp)
            continue
    return metrics


def build_report_entries(root, metrics, package_map, top):
    now = datetime.now(timezone.utc)
    hot_entries = []
    routing_entries = []
    reflection_entries = []
    stale_entries = []

    for memory_id, metric in metrics.items():
        package = package_map.get(memory_id, {})
        hotness_score = round(
            1.0 * metric["selected_count"]
            + 2.0 * metric["helpful_count"]
            + 2.0 * metric["used_in_final_answer_count"]
            + 0.5 * metric["recall_count"],
            2,
        )
        common_routes = common_route_list(metric["routes"])
        avg_depth_selected = average(metric["selected_depths"])
        avg_depth_helpful = average(metric["helpful_depths"])
        avg_candidate_count = average(metric["candidate_counts"])
        profile, is_stale = freshness_state(package, now)

        hot_entry = {
            "memory_id": memory_id,
            "hotness_score": hotness_score,
            "recall_count": metric["recall_count"],
            "selected_count": metric["selected_count"],
            "helpful_count": metric["helpful_count"],
            "used_in_final_answer_count": metric["used_in_final_answer_count"],
            "stale_hit_count": metric["stale_hit_count"],
            "last_used_at": metric["last_used_at"],
            "description": package.get("description", ""),
            "primary_related_files": package.get("related_files", [])[:4],
            "freshness_profile": profile,
            "last_updated_at": package.get("last_updated_at", ""),
        }
        hot_entries.append(hot_entry)

        if (
            avg_depth_selected is not None
            or avg_depth_helpful is not None
            or metric["false_positive_count"] > 0
            or metric["missed_recall_count"] > 0
        ):
            routing_entries.append(
                {
                    "memory_id": memory_id,
                    "avg_depth_to_selected": avg_depth_selected,
                    "avg_depth_to_helpful": avg_depth_helpful,
                    "avg_candidate_count_before_selection": avg_candidate_count,
                    "false_positive_count": metric["false_positive_count"],
                    "missed_recall_count": metric["missed_recall_count"],
                    "common_routes": common_routes,
                    "helpful_count": metric["helpful_count"],
                }
            )

        if (
            metric["missed_recall_count"] > 0
            or metric["helpful_count"] > 0
            or metric["stale_hit_count"] > 0
        ):
            priority_score = round(
                2.0 * metric["missed_recall_count"]
                + 1.5 * metric["helpful_count"]
                + 1.0 * metric["stale_hit_count"]
                + 1.0 * (avg_depth_helpful or 0.0),
                2,
            )
            reflection_entry = {
                "memory_id": memory_id,
                "priority_score": priority_score,
                "missed_recall_count": metric["missed_recall_count"],
                "helpful_count": metric["helpful_count"],
                "stale_hit_count": metric["stale_hit_count"],
                "avg_depth_to_helpful": avg_depth_helpful,
                "candidate_problem_type": candidate_problem_type(package, {
                    "missed_recall_count": metric["missed_recall_count"],
                    "helpful_count": metric["helpful_count"],
                    "stale_hit_count": metric["stale_hit_count"],
                    "avg_depth_to_helpful": avg_depth_helpful,
                }),
            }
            reflection_entries.append(reflection_entry)

        if is_stale and hotness_score > 0:
            stale_entries.append(
                {
                    "memory_id": memory_id,
                    "freshness_profile": profile,
                    "last_updated_at": package.get("last_updated_at", ""),
                    "helpful_count_rolling": metric["helpful_count"],
                    "stale_hit_count_rolling": metric["stale_hit_count"],
                    "hotness_score": hotness_score,
                    "recommended_action": recommended_stale_action(
                        {
                            "missed_recall_count": metric["missed_recall_count"],
                            "false_positive_count": metric["false_positive_count"],
                            "helpful_count": metric["helpful_count"],
                            "stale_hit_count": metric["stale_hit_count"],
                        }
                    ),
                }
            )

    hot_entries.sort(
        key=lambda item: (
            -item["hotness_score"],
            -item["helpful_count"],
            -item["selected_count"],
            item["memory_id"],
        )
    )
    routing_entries.sort(
        key=lambda item: (
            -(item["missed_recall_count"] + item["false_positive_count"]),
            -(item["avg_depth_to_helpful"] or 0.0),
            item["memory_id"],
        )
    )
    reflection_entries.sort(
        key=lambda item: (-item["priority_score"], item["memory_id"])
    )
    stale_entries.sort(
        key=lambda item: (
            -item["stale_hit_count_rolling"],
            -item["helpful_count_rolling"],
            -item["hotness_score"],
            item["memory_id"],
        )
    )

    return {
        "hot-memories": hot_entries[:top],
        "routing-friction": routing_entries[:top],
        "reflection-priority": reflection_entries[:top],
        "stale-but-hot": stale_entries[:top],
    }


def report_payload(root, report_name, window_days, observability, entries):
    return {
        "root": root,
        "report_name": report_name,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "window_days": window_days,
        "event_count": len(observability["events"]),
        "writer_scope": observability["writer_scope"],
        "source_writer_ids": observability["source_writer_ids"],
        "source_date_keys": observability["source_date_keys"],
        "source_min_timestamp": observability["source_min_timestamp"],
        "source_max_timestamp": observability["source_max_timestamp"],
        "source_event_file_count": observability["source_event_file_count"],
        "deduped_duplicate_event_count": observability["deduped_duplicate_event_count"],
        "generated_by_writer_id": resolve_writer_id(root),
        "entries": entries,
    }


def render_hot_memories(entries):
    lines = ["# Hot Memories", ""]
    if not entries:
        lines.extend(["No hot memories were observed in the selected window.", ""])
        return "\n".join(lines)
    for entry in entries:
        lines.append(
            "- `{0}` hotness={1} helpful={2} selected={3} recalled={4} stale-hits={5}".format(
                entry["memory_id"],
                entry["hotness_score"],
                entry["helpful_count"],
                entry["selected_count"],
                entry["recall_count"],
                entry["stale_hit_count"],
            )
        )
    lines.append("")
    return "\n".join(lines)


def render_routing_friction(entries):
    lines = ["# Routing Friction", ""]
    if not entries:
        lines.extend(["No routing-friction signals were observed in the selected window.", ""])
        return "\n".join(lines)
    for entry in entries:
        lines.append(
            "- `{0}` depth(selected/helpful)={1}/{2} candidates={3} false-positives={4} missed={5}".format(
                entry["memory_id"],
                entry["avg_depth_to_selected"],
                entry["avg_depth_to_helpful"],
                entry["avg_candidate_count_before_selection"],
                entry["false_positive_count"],
                entry["missed_recall_count"],
            )
        )
    lines.append("")
    return "\n".join(lines)


def render_reflection_priority(entries):
    lines = ["# Reflection Priority", ""]
    if not entries:
        lines.extend(["No reflection-priority signals were observed in the selected window.", ""])
        return "\n".join(lines)
    for entry in entries:
        lines.append(
            "- `{0}` priority={1} missed={2} helpful={3} stale-hits={4} problem={5}".format(
                entry["memory_id"],
                entry["priority_score"],
                entry["missed_recall_count"],
                entry["helpful_count"],
                entry["stale_hit_count"],
                entry["candidate_problem_type"],
            )
        )
    lines.append("")
    return "\n".join(lines)


def render_stale_but_hot(entries):
    lines = ["# Stale But Hot", ""]
    if not entries:
        lines.extend(["No stale-but-hot memories were observed in the selected window.", ""])
        return "\n".join(lines)
    for entry in entries:
        lines.append(
            "- `{0}` profile={1} helpful={2} stale-hits={3} action={4}".format(
                entry["memory_id"],
                entry["freshness_profile"],
                entry["helpful_count_rolling"],
                entry["stale_hit_count_rolling"],
                entry["recommended_action"],
            )
        )
    lines.append("")
    return "\n".join(lines)


def render_markdown(root, window_days, observability, reports):
    source_date_keys = observability["source_date_keys"]
    if source_date_keys:
        if len(source_date_keys) == 1:
            source_date_summary = source_date_keys[0]
        else:
            source_date_summary = "{0} .. {1} ({2} buckets)".format(
                source_date_keys[0],
                source_date_keys[-1],
                len(source_date_keys),
            )
    else:
        source_date_summary = "(none)"
    lines = [
        "# Memory Observability Reports",
        "",
        "- Root: `{0}`".format(root),
        "- Window Days: {0}".format(window_days),
        "- Event Count: {0}".format(len(observability["events"])),
        "- Writer Scope: `{0}`".format(observability["writer_scope"]),
        "- Source Date Coverage: {0}".format(source_date_summary),
        "- Source Max Timestamp: `{0}`".format(
            observability["source_max_timestamp"] or ""
        ),
        "- Source Writers: {0}".format(
            ", ".join("`{0}`".format(item) for item in observability["source_writer_ids"])
            or "(none)"
        ),
        "- Source Event Files: {0}".format(observability["source_event_file_count"]),
        "- Deduped Duplicate Events: {0}".format(
            observability["deduped_duplicate_event_count"]
        ),
        "- Generated By Writer: `{0}`".format(resolve_writer_id(root)),
        "",
        render_hot_memories(reports["hot-memories"]).rstrip(),
        "",
        render_routing_friction(reports["routing-friction"]).rstrip(),
        "",
        render_reflection_priority(reports["reflection-priority"]).rstrip(),
        "",
        render_stale_but_hot(reports["stale-but-hot"]).rstrip(),
        "",
    ]
    return "\n".join(lines)


def main():
    args = parse_args()
    packages, duplicate_ids = load_memory_packages(args.root)
    if duplicate_ids:
        raise SystemExit(
            "Duplicate memory IDs exist; resolve them before generating observability reports."
        )
    package_map = build_package_map(packages)
    observability = load_events_bundle(
        args.root,
        days=args.days,
        streams={"recall", "reflection"},
        writer_scope=args.writer_scope,
    )
    events = observability["events"]
    metrics = aggregate_metrics(events)
    reports = build_report_entries(args.root, metrics, package_map, args.top)

    json_reports = {}
    markdown_reports = {}
    for report_name, entries in reports.items():
        json_reports[report_name] = report_payload(
            args.root, report_name, args.days, observability, entries
        )
        if report_name == "hot-memories":
            markdown_reports[report_name] = render_hot_memories(entries)
        elif report_name == "routing-friction":
            markdown_reports[report_name] = render_routing_friction(entries)
        elif report_name == "reflection-priority":
            markdown_reports[report_name] = render_reflection_priority(entries)
        else:
            markdown_reports[report_name] = render_stale_but_hot(entries)

    write_latest = args.write or args.write_latest
    if write_latest and str(args.writer_scope or "all").strip() != "all":
        raise SystemExit(
            "Tracked latest reports require `--writer-scope all`; use a filtered run "
            "without `--write` or write an explicit history snapshot instead."
        )
    if write_latest or args.write_history:
        for report_name in reports:
            write_report_set(
                args.root,
                report_name,
                json_reports[report_name],
                markdown_reports[report_name],
                write_latest=write_latest,
                write_history=args.write_history,
            )

    if args.format == "json":
        print(
            json.dumps(
                {
                    "root": args.root,
                    "window_days": args.days,
                    "event_count": len(events),
                    "writer_scope": observability["writer_scope"],
                    "source_writer_ids": observability["source_writer_ids"],
                    "source_date_keys": observability["source_date_keys"],
                    "source_min_timestamp": observability["source_min_timestamp"],
                    "source_max_timestamp": observability["source_max_timestamp"],
                    "source_event_file_count": observability["source_event_file_count"],
                    "deduped_duplicate_event_count": observability[
                        "deduped_duplicate_event_count"
                    ],
                    "generated_by_writer_id": resolve_writer_id(args.root),
                    "reports": json_reports,
                },
                indent=2,
                ensure_ascii=True,
            )
        )
        return 0

    print(render_markdown(args.root, args.days, observability, reports))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
