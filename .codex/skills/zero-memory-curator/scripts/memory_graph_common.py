#!/usr/bin/env python3
"""Common helpers for zero-memory graph loader and validator scripts."""

import json
import re
from collections import defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path


FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n?", re.DOTALL)
SECTION_RE = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)
VALID_MEMORY_STATUSES = ("active", "superseded", "subsumed", "incorrect", "tombstone")
VALID_FRESHNESS_PROFILES = ("code-env", "workflow", "conceptual")
INDEX_FILENAMES = {
    "reverse_load_next": "reverse-load-next.yml",
    "by_pattern_key": "by-pattern-key.yml",
    "by_related_file": "by-related-file.yml",
    "by_related_symbol": "by-related-symbol.yml",
}
LIST_KEYS = {
    "tags",
    "source_daily_learning_ids",
    "recent_confirmation_ids",
    "supersedes",
    "abstracts",
    "load_next",
    "related",
    "related_files",
    "related_symbols",
}
PREFERRED_FRONTMATTER_ORDER = [
    "id",
    "name",
    "description",
    "tags",
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
    "source_daily_learning_ids",
    "recurrence_count",
    "last_confirmed_at",
    "recent_confirmation_ids",
    "supersedes",
    "superseded_by",
    "abstracts",
    "subsumed_by",
    "load_next",
    "related",
    "related_files",
    "related_symbols",
]


def strip_quotes(value):
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        return value[1:-1]
    return value


def ensure_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value if str(item) != ""]
    if value == "":
        return []
    return [str(value)]


def ensure_scalar(value):
    if value is None:
        return ""
    if isinstance(value, list):
        if not value:
            return ""
        return str(value[0])
    return str(value)


def parse_optional_int(value):
    raw = ensure_scalar(value).strip()
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def parse_utc_timestamp(value):
    raw = ensure_scalar(value).strip()
    if not raw:
        return None
    for pattern in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S.%fZ"):
        try:
            return datetime.strptime(raw, pattern).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def normalize_freshness_profile(value):
    return ensure_scalar(value).strip().lower()


def infer_freshness_profile(package):
    memory_id = package.get("id", "").strip().lower()
    component = package.get("component", "").strip().lower()
    stage = package.get("stage", "").strip().lower()
    related_files = package.get("related_files", [])

    if (
        component == "workflow"
        or memory_id.startswith("workspace.")
        or memory_id.startswith("git.")
        or "workflow" in memory_id
        or "workflows" in memory_id
        or any(path.startswith("skills/") for path in related_files)
    ):
        return "workflow"

    code_env_prefixes = ("src/", "lib/", "app/", "pkg/", "tests/", "scripts/")
    if (
        component in ("application", "runtime", "tooling")
        or memory_id.startswith(("application.", "runtime.", "tooling.", "code."))
        or stage in ("implementation", "testing", "release", "operations")
        or any(path.startswith(code_env_prefixes) for path in related_files)
    ):
        return "code-env"

    return "conceptual"


def resolve_freshness_profile(package):
    declared = package.get("freshness_profile", "")
    if declared:
        if declared in VALID_FRESHNESS_PROFILES:
            return declared, "declared"
        return "", "invalid"
    return infer_freshness_profile(package), "inferred"


def normalize_memory_status(value):
    raw = ensure_scalar(value).strip().lower()
    return raw or "active"


def compact_text(text):
    return " ".join(text.split())


def extract_backticked_values(text):
    return re.findall(r"`([^`]+)`", text or "")


def extract_related_values(section_text, label):
    values = []
    needle = label.lower()
    for raw_line in (section_text or "").splitlines():
        if needle not in raw_line.lower():
            continue
        values.extend(extract_backticked_values(raw_line))
    deduped = []
    seen = set()
    for value in values:
        if value not in seen:
            deduped.append(value)
            seen.add(value)
    return deduped


def parse_frontmatter(text):
    match = FRONTMATTER_RE.match(text)
    if not match:
        return {}, text

    body = text[match.end() :]
    data = {}
    current_key = None

    for raw_line in match.group(1).splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped:
            continue
        if line.startswith("  - ") and current_key:
            data.setdefault(current_key, [])
            if isinstance(data[current_key], list):
                data[current_key].append(strip_quotes(line[4:].strip()))
            continue
        if ":" not in line:
            current_key = None
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if value == "[]":
            data[key] = []
        elif not value:
            data[key] = []
        else:
            data[key] = strip_quotes(value)
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


def iter_memory_files(root):
    return sorted(Path(root).glob("*/MEMORY.md"))


def derive_id_from_slug(slug):
    return slug.replace("-", ".")


def load_memory_package(memory_file):
    raw_text = Path(memory_file).read_text(encoding="utf-8")
    frontmatter, body = parse_frontmatter(raw_text)
    sections = parse_sections(body)
    slug = Path(memory_file).parent.name
    declared_id = ensure_scalar(frontmatter.get("id")).strip()
    memory_id = declared_id or derive_id_from_slug(slug)
    description = ensure_scalar(frontmatter.get("description")).strip()
    if not description:
        description = compact_text(sections.get("Description", ""))

    recurrence_count_raw = ensure_scalar(frontmatter.get("recurrence_count")).strip()
    related_files = ensure_list(frontmatter.get("related_files"))
    if not related_files:
        related_files = extract_related_values(sections.get("Related", ""), "Related files")
    related_symbols = ensure_list(frontmatter.get("related_symbols"))
    if not related_symbols:
        related_symbols = extract_related_values(
            sections.get("Related", ""),
            "Related symbols",
        )

    return {
        "id": memory_id,
        "declared_id": declared_id,
        "slug": slug,
        "name": ensure_scalar(frontmatter.get("name")) or slug,
        "path": str(Path(memory_file)),
        "description": description,
        "details": compact_text(sections.get("Details", "")),
        "layer": ensure_scalar(frontmatter.get("layer")) or "detailed",
        "status": normalize_memory_status(frontmatter.get("status")),
        "declared_status": ensure_scalar(frontmatter.get("status")).strip(),
        "last_updated_at": ensure_scalar(frontmatter.get("last_updated_at")).strip(),
        "freshness_profile": normalize_freshness_profile(
            frontmatter.get("freshness_profile")
        ),
        "declared_freshness_profile": ensure_scalar(
            frontmatter.get("freshness_profile")
        ).strip(),
        "load_next": ensure_list(frontmatter.get("load_next")),
        "related": ensure_list(frontmatter.get("related")),
        "source_daily_learning_ids": ensure_list(frontmatter.get("source_daily_learning_ids")),
        "recent_confirmation_ids": ensure_list(frontmatter.get("recent_confirmation_ids")),
        "supersedes": ensure_list(frontmatter.get("supersedes")),
        "abstracts": ensure_list(frontmatter.get("abstracts")),
        "related_files": related_files,
        "related_symbols": related_symbols,
        "tags": ensure_list(frontmatter.get("tags")),
        "pattern_key": ensure_scalar(frontmatter.get("pattern_key")).strip(),
        "component": ensure_scalar(frontmatter.get("component")).strip(),
        "kind": ensure_scalar(frontmatter.get("kind")).strip(),
        "stage": ensure_scalar(frontmatter.get("stage")).strip(),
        "scope": ensure_scalar(frontmatter.get("scope")).strip(),
        "actionability": ensure_scalar(frontmatter.get("actionability")).strip(),
        "recurrence_count": parse_optional_int(frontmatter.get("recurrence_count")),
        "recurrence_count_raw": recurrence_count_raw,
        "last_confirmed_at": ensure_scalar(frontmatter.get("last_confirmed_at")).strip(),
        "superseded_by": ensure_scalar(frontmatter.get("superseded_by")).strip(),
        "subsumed_by": ensure_scalar(frontmatter.get("subsumed_by")).strip(),
        "frontmatter": frontmatter,
        "sections": sections,
    }


def load_memory_packages(root):
    packages = []
    duplicate_ids = {}
    for memory_file in iter_memory_files(root):
        package = load_memory_package(memory_file)
        packages.append(package)
        duplicate_ids.setdefault(package["id"], []).append(package["path"])
    return packages, dict(
        (memory_id, paths)
        for memory_id, paths in duplicate_ids.items()
        if len(paths) > 1
    )


def load_init_memory_set(root):
    path = Path(root) / "init-memory-set.yml"
    if not path.exists():
        return []

    ids = []
    in_list = False
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("init_memory_set:"):
            in_list = True
            remainder = stripped.split(":", 1)[1].strip()
            if remainder and remainder != "[]":
                ids.append(strip_quotes(remainder))
            continue
        if in_list and line.startswith("  - "):
            ids.append(strip_quotes(line[4:].strip()))
            continue
        if in_list and not line.startswith("  "):
            break
    return ids


def load_registry(root):
    path = Path(root) / "registry.yml"
    if not path.exists():
        return []

    entries = []
    current = None
    in_list = False
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("memories:"):
            in_list = True
            continue
        if not in_list:
            continue
        if line.startswith("  - "):
            current = {}
            entries.append(current)
            payload = line[4:].strip()
            if payload and ":" in payload:
                key, value = payload.split(":", 1)
                current[key.strip()] = strip_quotes(value.strip())
            continue
        if current is None or not line.startswith("    "):
            continue
        key, value = stripped.split(":", 1)
        current[key.strip()] = strip_quotes(value.strip())
    return entries


def canonical_registry_path(root, memory_file):
    root_path = Path(root).resolve()
    workspace_root = root_path.parent.parent
    memory_path = Path(memory_file).resolve()
    try:
        return memory_path.relative_to(workspace_root).as_posix()
    except ValueError:
        return (Path(".zero-memory") / "memory" / memory_path.parent.name / "MEMORY.md").as_posix()


def make_registry_entries(root, packages):
    entries = []
    for package in sorted(packages, key=lambda item: item["id"]):
        entries.append(
            {
                "id": package["id"],
                "slug": package["slug"],
                "path": canonical_registry_path(root, package["path"]),
            }
        )
    return entries


def write_registry(root, entries):
    path = Path(root) / "registry.yml"
    lines = [
        "# Registry of stable memory IDs, slugs, and workspace-relative canonical package paths.",
        "memories:",
    ]
    for entry in sorted(entries, key=lambda item: item["id"]):
        lines.append("  - id: {0}".format(entry["id"]))
        lines.append("    slug: {0}".format(entry["slug"]))
        lines.append("    path: {0}".format(entry["path"]))
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def write_init_memory_set(root, ids):
    path = Path(root) / "init-memory-set.yml"
    lines = [
        "# Entry-point memory IDs for layered discovery.",
        "# Keep this set intentionally small and route to deeper knowledge via load_next.",
        "init_memory_set:",
    ]
    for memory_id in ids:
        lines.append("  - {0}".format(memory_id))
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def _quote_scalar(value):
    if isinstance(value, int):
        return str(value)
    escaped = str(value).replace("\\", "\\\\").replace("'", "\\'")
    return "'{0}'".format(escaped)


def render_frontmatter(frontmatter):
    keys = []
    for key in PREFERRED_FRONTMATTER_ORDER:
        if key in frontmatter:
            keys.append(key)
    for key in sorted(frontmatter):
        if key not in keys:
            keys.append(key)

    lines = []
    for key in keys:
        value = frontmatter[key]
        if value in (None, "", []):
            continue
        if key in LIST_KEYS:
            items = ensure_list(value)
            if not items:
                continue
            lines.append("{0}:".format(key))
            for item in items:
                lines.append("  - {0}".format(_quote_scalar(item)))
            continue
        if key == "recurrence_count":
            parsed = parse_optional_int(value)
            if parsed is not None:
                lines.append("{0}: {1}".format(key, parsed))
                continue
        lines.append("{0}: {1}".format(key, _quote_scalar(ensure_scalar(value))))
    return "\n".join(lines)


def update_memory_frontmatter(memory_file, field_updates):
    path = Path(memory_file)
    raw_text = path.read_text(encoding="utf-8")
    frontmatter, body = parse_frontmatter(raw_text)
    for key, value in field_updates.items():
        if value in (None, "", []):
            frontmatter.pop(key, None)
        else:
            frontmatter[key] = value
    rendered = "---\n{0}\n---\n{1}".format(
        render_frontmatter(frontmatter),
        body,
    )
    path.write_text(rendered, encoding="utf-8")


def memory_index_root(root):
    return Path(root) / "index"


def build_package_map(packages):
    package_map = {}
    for package in packages:
        if package["id"] not in package_map:
            package_map[package["id"]] = package
    return package_map


def is_active_memory(package):
    return package.get("status", "active") == "active"


def build_reverse_load_next(package_map, include_inactive=True):
    reverse_map = defaultdict(list)
    for memory_id, package in sorted(package_map.items()):
        if not include_inactive and not is_active_memory(package):
            continue
        for child_id in package["load_next"]:
            child = package_map.get(child_id)
            if child is None:
                continue
            if not include_inactive and not is_active_memory(child):
                continue
            reverse_map[child_id].append(memory_id)
    return {
        memory_id: sorted(parent_ids)
        for memory_id, parent_ids in sorted(reverse_map.items())
    }


def _build_lookup_map(package_map, value_getter, include_inactive=True):
    lookup = defaultdict(list)
    for memory_id, package in sorted(package_map.items()):
        if not include_inactive and not is_active_memory(package):
            continue
        for raw_value in value_getter(package):
            value = str(raw_value).strip()
            if value:
                lookup[value].append(memory_id)
    return {
        key: sorted(set(memory_ids))
        for key, memory_ids in sorted(lookup.items())
    }


def build_pattern_key_index(package_map, include_inactive=True):
    return _build_lookup_map(
        package_map,
        lambda package: [package.get("pattern_key", "")],
        include_inactive=include_inactive,
    )


def build_related_file_index(package_map, include_inactive=True):
    return _build_lookup_map(
        package_map,
        lambda package: package.get("related_files", []),
        include_inactive=include_inactive,
    )


def build_related_symbol_index(package_map, include_inactive=True):
    return _build_lookup_map(
        package_map,
        lambda package: package.get("related_symbols", []),
        include_inactive=include_inactive,
    )


def build_memory_index_payloads(package_map):
    return {
        INDEX_FILENAMES["reverse_load_next"]: {
            "version": 1,
            "kind": "reverse-load-next",
            "all": build_reverse_load_next(package_map, include_inactive=True),
            "active": build_reverse_load_next(package_map, include_inactive=False),
        },
        INDEX_FILENAMES["by_pattern_key"]: {
            "version": 1,
            "kind": "by-pattern-key",
            "all": build_pattern_key_index(package_map, include_inactive=True),
            "active": build_pattern_key_index(package_map, include_inactive=False),
        },
        INDEX_FILENAMES["by_related_file"]: {
            "version": 1,
            "kind": "by-related-file",
            "all": build_related_file_index(package_map, include_inactive=True),
            "active": build_related_file_index(package_map, include_inactive=False),
        },
        INDEX_FILENAMES["by_related_symbol"]: {
            "version": 1,
            "kind": "by-related-symbol",
            "all": build_related_symbol_index(package_map, include_inactive=True),
            "active": build_related_symbol_index(package_map, include_inactive=False),
        },
    }


def _render_index_payload(payload):
    return json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n"


def sync_memory_indexes(root, package_map):
    index_root = memory_index_root(root)
    index_root.mkdir(parents=True, exist_ok=True)
    notes = []
    for filename, payload in build_memory_index_payloads(package_map).items():
        path = index_root / filename
        expected_text = _render_index_payload(payload)
        current_text = path.read_text(encoding="utf-8") if path.exists() else None
        if current_text != expected_text:
            path.write_text(expected_text, encoding="utf-8")
            notes.append("rewrote {0}".format(path))
    return notes


def check_memory_index_drift(root, package_map):
    warnings = []
    index_root = memory_index_root(root)
    for filename, payload in build_memory_index_payloads(package_map).items():
        path = index_root / filename
        expected_text = _render_index_payload(payload)
        if not path.exists():
            warnings.append("generated memory index missing `{0}`".format(path))
            continue
        current_text = path.read_text(encoding="utf-8")
        if current_text != expected_text:
            warnings.append("generated memory index stale `{0}`".format(path))
    return warnings


def load_memory_index(root, filename):
    path = memory_index_root(root) / filename
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def bfs_levels(package_map, start_ids, depth=None, include_inactive=True):
    levels = {}
    queue = deque()
    for memory_id in start_ids:
        package = package_map.get(memory_id)
        if package is None:
            continue
        if not include_inactive and not is_active_memory(package):
            continue
        if memory_id not in levels:
            queue.append((memory_id, 0))

    while queue:
        memory_id, level = queue.popleft()
        if memory_id in levels:
            continue
        levels[memory_id] = level
        if depth is not None and level >= depth:
            continue
        for child_id in package_map[memory_id]["load_next"]:
            child = package_map.get(child_id)
            if child is None:
                continue
            if not include_inactive and not is_active_memory(child):
                continue
            if child_id not in levels:
                queue.append((child_id, level + 1))
    return levels


def collect_descendant_provenance(package_map, start_id, include_inactive=True):
    if start_id not in package_map:
        return []

    seen = {start_id}
    queue = deque()
    for child_id in package_map[start_id]["load_next"]:
        child = package_map.get(child_id)
        if child is None:
            continue
        if not include_inactive and not is_active_memory(child):
            continue
        queue.append(child_id)

    derived_ids = set()
    while queue:
        memory_id = queue.popleft()
        if memory_id in seen:
            continue
        seen.add(memory_id)
        package = package_map[memory_id]
        derived_ids.update(package["source_daily_learning_ids"])
        for child_id in package["load_next"]:
            child = package_map.get(child_id)
            if child is None:
                continue
            if not include_inactive and not is_active_memory(child):
                continue
            queue.append(child_id)
    return sorted(derived_ids)


def _canonical_cycle(cycle):
    core = cycle[:-1]
    if not core:
        return tuple()
    best = None
    for index in range(len(core)):
        rotated = core[index:] + core[:index]
        candidate = tuple(rotated)
        if best is None or candidate < best:
            best = candidate
    return best


def find_load_next_cycles(package_map):
    state = {}
    stack = []
    cycles = {}

    def walk(memory_id):
        state[memory_id] = 1
        stack.append(memory_id)
        for child_id in package_map[memory_id]["load_next"]:
            if child_id not in package_map:
                continue
            child_state = state.get(child_id, 0)
            if child_state == 0:
                walk(child_id)
            elif child_state == 1:
                cycle_start = stack.index(child_id)
                cycle = stack[cycle_start:] + [child_id]
                cycles[_canonical_cycle(cycle)] = cycle
        stack.pop()
        state[memory_id] = 2

    for memory_id in sorted(package_map):
        if state.get(memory_id, 0) == 0:
            walk(memory_id)
    return sorted(cycles.values(), key=lambda item: item[0] if item else "")


def format_cycle(cycle):
    return " -> ".join(cycle)
