#!/usr/bin/env python3
"""Shared observability helpers for zero-memory recall, curation, and reflection."""

import json
import os
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path


VALID_STREAMS = {"recall", "curation", "reflection"}
REPORT_NAMES = (
    "hot-memories",
    "routing-friction",
    "reflection-priority",
    "stale-but-hot",
)


def utc_now():
    return datetime.now(timezone.utc)


def format_utc_timestamp(value):
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def timestamp_fragment(value):
    return value.astimezone(timezone.utc).strftime("%Y%m%d-%H%M%S.") + "{0:03d}Z".format(
        value.microsecond // 1000
    )


def generate_event_id(prefix="OBS", now=None):
    current = now or utc_now()
    return "{0}-{1}-{2}".format(
        prefix,
        timestamp_fragment(current),
        secrets.token_hex(4),
    )


def dedupe(values):
    result = []
    seen = set()
    for value in values or []:
        item = str(value).strip()
        if not item or item in seen:
            continue
        result.append(item)
        seen.add(item)
    return result


def resolve_memory_root(root):
    return Path(root).resolve()


def resolve_workspace_root(root):
    memory_root = resolve_memory_root(root)
    for candidate in [memory_root] + list(memory_root.parents):
        if candidate.name == ".zero-memory":
            return candidate.parent
        if candidate.name == "memory" and candidate.parent.name == ".zero-memory":
            return candidate.parent.parent
    return Path.cwd().resolve()


def zero_memory_root(root):
    return resolve_workspace_root(root) / ".zero-memory"


def observability_root(root):
    return zero_memory_root(root) / "observability"


def observability_events_dir(root):
    return observability_root(root) / "events"


def observability_reports_dir(root):
    return observability_root(root) / "reports"


def local_observability_root(root):
    return zero_memory_root(root) / "tmp" / "zero-memory-observability"


def latest_reports_dir(root):
    return observability_reports_dir(root) / "latest"


def legacy_latest_reports_dir(root):
    return local_observability_root(root) / "latest"


def history_reports_dir(root, date_key):
    return observability_reports_dir(root) / "history" / date_key


def writer_id_file(root):
    return local_observability_root(root) / "writer-id"


def event_stream_name(kind):
    stream = str(kind or "").split(".", 1)[0].strip()
    return stream if stream in VALID_STREAMS else "recall"


def sanitize_writer_id(value):
    item = str(value or "").strip().lower()
    cleaned = []
    for ch in item:
        if ch.isalnum() or ch in ("-", "_"):
            cleaned.append(ch)
    result = "".join(cleaned).strip("-_")
    return result or uuid.uuid4().hex


def resolve_writer_id(root):
    path = writer_id_file(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        try:
            current = sanitize_writer_id(path.read_text(encoding="utf-8").strip())
            if current:
                return current
        except OSError:
            pass
    value = uuid.uuid4().hex
    path.write_text(value + "\n", encoding="utf-8")
    return value


def repo_relative_path(path_value, workspace_root):
    if not path_value:
        return ""
    path = Path(path_value)
    if not path.is_absolute():
        return path.as_posix()
    try:
        return path.resolve().relative_to(Path(workspace_root).resolve()).as_posix()
    except ValueError:
        return str(path_value)


def resolve_active_context_path(root):
    workspace_root = resolve_workspace_root(root)
    active_files = [
        workspace_root / ".zero-memory" / "tmp" / "current-context.txt",
        workspace_root / "tmp" / "current-context.txt",
    ]
    for active_file in active_files:
        try:
            raw = active_file.read_text(encoding="utf-8").splitlines()[0].strip()
        except (IndexError, OSError):
            raw = ""
        if not raw:
            continue
        candidate = Path(raw)
        if not candidate.is_absolute():
            candidate = workspace_root / candidate
        return repo_relative_path(candidate, workspace_root)
    return ""


def context_name_from_path(path_value):
    value = str(path_value or "").strip()
    if not value:
        return ""
    path = Path(value)
    if path.name == "context.md":
        return path.parent.name
    return path.stem


def resolve_session_id(context_name):
    explicit = os.environ.get("ZERO_MEMORY_OBSERVABILITY_SESSION_ID", "").strip()
    if explicit:
        return explicit
    if context_name:
        return "context:{0}".format(context_name)
    return "workspace-local"


def write_jsonl_event(root, kind, skill, script, memory_ids=None, extra=None, status="ok"):
    try:
        now = utc_now()
        workspace_root = resolve_workspace_root(root)
        context_path = resolve_active_context_path(root)
        context_name = context_name_from_path(context_path)
        writer_id = resolve_writer_id(root)
        payload = {
            "event_id": generate_event_id(now=now),
            "timestamp": format_utc_timestamp(now),
            "kind": str(kind).strip(),
            "skill": str(skill).strip(),
            "script": str(script).strip(),
            "session_id": resolve_session_id(context_name),
            "task_context": context_path,
            "context_name": context_name,
            "writer_id": writer_id,
            "workspace_root_hint": repo_relative_path(workspace_root, workspace_root) or ".",
            "memory_ids": dedupe(memory_ids),
            "status": str(status or "ok").strip() or "ok",
        }
        for key, value in dict(extra or {}).items():
            if value in (None, "", []):
                continue
            payload[key] = value

        events_dir = observability_events_dir(root)
        date_dir = events_dir / now.strftime("%Y-%m-%d")
        date_dir.mkdir(parents=True, exist_ok=True)
        stream_path = date_dir / "{0}.{1}.jsonl".format(
            writer_id,
            event_stream_name(kind),
        )
        with stream_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=True) + "\n")
        return payload
    except Exception:
        return None


def parse_event_file_info(path):
    name = path.name
    parts = name.split(".")
    if len(parts) == 3 and parts[2] == "jsonl":
        if parts[1] in VALID_STREAMS:
            return sanitize_writer_id(parts[0]), parts[1]
        if parts[0] in VALID_STREAMS:
            return "", parts[0]
    return "", ""


def normalize_writer_scope(root, writer_scope=None):
    scope = str(writer_scope or "all").strip()
    if not scope or scope == "all":
        return None
    if scope == "current":
        return {resolve_writer_id(root)}
    return {sanitize_writer_id(item) for item in scope.split(",") if item.strip()}


def iter_event_files(root, streams=None, writer_scope=None):
    events_dir = observability_events_dir(root)
    if not events_dir.exists():
        return []
    allowed = set(streams or [])
    allowed_writers = normalize_writer_scope(root, writer_scope)
    files = []
    for path in sorted(events_dir.glob("*.jsonl")):
        writer_id, stream = parse_event_file_info(path)
        if allowed and stream not in allowed:
            continue
        if allowed_writers is not None and (
            not writer_id or writer_id not in allowed_writers
        ):
            continue
        files.append(path)
    for path in sorted(events_dir.glob("*/*.jsonl")):
        writer_id, stream = parse_event_file_info(path)
        if allowed and stream not in allowed:
            continue
        if allowed_writers is not None and (
            not writer_id or writer_id not in allowed_writers
        ):
            continue
        files.append(path)
    return sorted(files)


def load_events_bundle(root, days=None, streams=None, writer_scope=None):
    cutoff = None
    if days is not None and int(days) > 0:
        cutoff = utc_now() - timedelta(days=int(days))

    events = []
    event_files = iter_event_files(root, streams=streams, writer_scope=writer_scope)
    seen_event_ids = set()
    source_writer_ids = set()
    source_date_keys = set()
    source_min_timestamp = ""
    source_max_timestamp = ""
    duplicate_event_count = 0
    for event_file in event_files:
        file_writer_id, _ = parse_event_file_info(event_file)
        for raw_line in event_file.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            timestamp = payload.get("timestamp", "")
            try:
                event_time = datetime.strptime(
                    timestamp, "%Y-%m-%dT%H:%M:%SZ"
                ).replace(tzinfo=timezone.utc)
            except ValueError:
                event_time = None
            if cutoff is not None and event_time is not None and event_time < cutoff:
                continue
            if event_time is not None:
                iso_timestamp = format_utc_timestamp(event_time)
                date_key = event_time.strftime("%Y-%m-%d")
                source_date_keys.add(date_key)
                if not source_min_timestamp or iso_timestamp < source_min_timestamp:
                    source_min_timestamp = iso_timestamp
                if not source_max_timestamp or iso_timestamp > source_max_timestamp:
                    source_max_timestamp = iso_timestamp
            event_id = str(payload.get("event_id", "")).strip()
            if event_id:
                if event_id in seen_event_ids:
                    duplicate_event_count += 1
                    continue
                seen_event_ids.add(event_id)
            payload_writer_id = str(payload.get("writer_id", "")).strip()
            if not payload_writer_id and file_writer_id:
                payload["writer_id"] = file_writer_id
                payload_writer_id = file_writer_id
            if payload_writer_id:
                source_writer_ids.add(sanitize_writer_id(payload_writer_id))
            events.append(payload)
    return {
        "events": events,
        "writer_scope": str(writer_scope or "all").strip() or "all",
        "source_writer_ids": sorted(source_writer_ids),
        "source_date_keys": sorted(source_date_keys),
        "source_min_timestamp": source_min_timestamp,
        "source_max_timestamp": source_max_timestamp,
        "source_event_file_count": len(event_files),
        "deduped_duplicate_event_count": duplicate_event_count,
    }


def load_events(root, days=None, streams=None, writer_scope=None):
    return load_events_bundle(
        root, days=days, streams=streams, writer_scope=writer_scope
    )["events"]


def latest_report_json_path(root, report_name):
    return latest_reports_dir(root) / "{0}.json".format(report_name)


def latest_report_markdown_path(root, report_name):
    return latest_reports_dir(root) / "{0}.md".format(report_name)


def load_latest_report(root, report_name):
    if report_name not in REPORT_NAMES:
        return None
    path = latest_report_json_path(root, report_name)
    if not path.exists():
        legacy = legacy_latest_reports_dir(root) / "{0}.json".format(report_name)
        path = legacy
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def latest_report_index(root, report_name):
    payload = load_latest_report(root, report_name)
    entries = []
    if payload is not None:
        entries = payload.get("entries", []) or []
    index = {}
    for entry in entries:
        memory_id = str(entry.get("memory_id", "")).strip()
        if memory_id:
            index[memory_id] = entry
    return payload, index


def build_observability_snapshot(root, memory_ids):
    snapshot = {"available_reports": {}, "memory_metrics": {}}
    for report_name in REPORT_NAMES:
        payload, index = latest_report_index(root, report_name)
        snapshot["available_reports"][report_name] = payload is not None
        for memory_id in dedupe(memory_ids):
            entry = index.get(memory_id)
            if entry is None:
                continue
            snapshot["memory_metrics"].setdefault(memory_id, {})[report_name] = entry
    return snapshot


def history_snapshot_stem(root, report_name):
    now = utc_now()
    return "{0}.{1}.{2}".format(
        now.strftime("%Y%m%dT%H%M%SZ"),
        resolve_writer_id(root),
        report_name,
    )


def write_report_set(root, report_name, json_payload, markdown_text, write_latest=False, write_history=False):
    if report_name not in REPORT_NAMES:
        raise ValueError("Unknown report name `{0}`.".format(report_name))

    json_text = json.dumps(json_payload, indent=2, ensure_ascii=True) + "\n"
    markdown_body = markdown_text.rstrip() + "\n"

    if write_latest:
        latest_dir = latest_reports_dir(root)
        latest_dir.mkdir(parents=True, exist_ok=True)
        latest_report_json_path(root, report_name).write_text(json_text, encoding="utf-8")
        latest_report_markdown_path(root, report_name).write_text(
            markdown_body, encoding="utf-8"
        )

    if write_history:
        date_key = utc_now().strftime("%Y-%m-%d")
        history_dir = history_reports_dir(root, date_key)
        history_dir.mkdir(parents=True, exist_ok=True)
        stem = history_snapshot_stem(root, report_name)
        (history_dir / "{0}.json".format(stem)).write_text(
            json_text, encoding="utf-8"
        )
        (history_dir / "{0}.md".format(stem)).write_text(
            markdown_body, encoding="utf-8"
        )
