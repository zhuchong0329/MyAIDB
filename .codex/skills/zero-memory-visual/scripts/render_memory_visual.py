#!/usr/bin/env python3
"""Render a zero-memory graph and observability dashboard as local HTML."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import shutil
import sys
import webbrowser
from datetime import datetime, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import quote


SCRIPT_DIR = Path(__file__).resolve().parent
SKILLS_DIR = SCRIPT_DIR.parents[1]
CURATOR_SCRIPTS = SKILLS_DIR / "zero-memory-curator" / "scripts"
if str(CURATOR_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(CURATOR_SCRIPTS))

from memory_graph_common import (  # noqa: E402
    build_package_map,
    build_reverse_load_next,
    load_memory_packages,
    resolve_freshness_profile,
)
from memory_observability import (  # noqa: E402
    dedupe,
    load_events_bundle,
    resolve_workspace_root,
    zero_memory_root,
)
from report_memory_observability import aggregate_metrics  # noqa: E402


SCRIPT_PATH = "skills/zero-memory-visual/scripts/render_memory_visual.py"
CLIENT_APP_TS = SCRIPT_DIR.parent / "assets" / "memory_visual_app.ts"
CLIENT_APP_JS = SCRIPT_DIR.parent / "assets" / "memory_visual_app.js"
LAYER_ORDER = ["init", "abstract", "detailed", "leaf"]
FILE_LINK_DIR = "__workspace_files"
MARKDOWN_SUFFIXES = {".md", ".markdown"}
TEXT_FILE_CONTENT_TYPES = {
    ".c": "text/plain; charset=utf-8",
    ".cc": "text/plain; charset=utf-8",
    ".cpp": "text/plain; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".go": "text/plain; charset=utf-8",
    ".h": "text/plain; charset=utf-8",
    ".hpp": "text/plain; charset=utf-8",
    ".html": "text/html; charset=utf-8",
    ".java": "text/plain; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".md": "text/markdown; charset=utf-8",
    ".py": "text/x-python; charset=utf-8",
    ".rs": "text/plain; charset=utf-8",
    ".sh": "text/x-shellscript; charset=utf-8",
    ".toml": "text/plain; charset=utf-8",
    ".ts": "text/plain; charset=utf-8",
    ".txt": "text/plain; charset=utf-8",
    ".yaml": "text/yaml; charset=utf-8",
    ".yml": "text/yaml; charset=utf-8",
}


class TextFriendlyRequestHandler(SimpleHTTPRequestHandler):
    """Serve source-like files as readable text instead of downloads."""

    def guess_type(self, path: str) -> str:
        if f"{os.sep}{FILE_LINK_DIR}{os.sep}" in path and f"{os.sep}raw{os.sep}" in path:
            return "text/html; charset=utf-8"
        suffix = Path(path).suffix.lower()
        if suffix in TEXT_FILE_CONTENT_TYPES:
            return TEXT_FILE_CONTENT_TYPES[suffix]
        return super().guess_type(path)


def is_markdown_path(path: str | Path) -> bool:
    return Path(path).suffix.lower() in MARKDOWN_SUFFIXES


def url_path(path: Path) -> str:
    return "/".join(quote(part) for part in path.as_posix().split("/"))


def render_inline_markdown(text: str) -> str:
    rendered = html.escape(text)
    rendered = re.sub(
        r"\[([^\]]+)\]\((https?://[^)\s]+)\)",
        r'<a href="\2" target="_blank" rel="noopener noreferrer">\1</a>',
        rendered,
    )
    rendered = re.sub(r"`([^`]+)`", r"<code>\1</code>", rendered)
    rendered = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", rendered)
    rendered = re.sub(r"__([^_]+)__", r"<strong>\1</strong>", rendered)
    rendered = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", rendered)
    return rendered


def render_markdown(text: str) -> str:
    lines = text.replace("\r\n", "\n").split("\n")
    output = []
    code_lines = []
    in_code = False
    list_type = None

    def close_list() -> None:
        nonlocal list_type
        if list_type:
            output.append(f"</{list_type}>")
            list_type = None

    for line in lines:
        if line.startswith("```"):
            if in_code:
                output.append(
                    "<pre><code>{0}</code></pre>".format(
                        html.escape("\n".join(code_lines))
                    )
                )
                code_lines = []
                in_code = False
            else:
                close_list()
                in_code = True
                code_lines = []
            continue

        if in_code:
            code_lines.append(line)
            continue

        stripped = line.strip()
        if not stripped:
            close_list()
            continue

        heading = re.match(r"^(#{1,6})\s+(.+)$", stripped)
        if heading:
            close_list()
            level = len(heading.group(1))
            output.append(
                f"<h{level}>{render_inline_markdown(heading.group(2))}</h{level}>"
            )
            continue

        if re.match(r"^(-{3,}|\*{3,}|_{3,})$", stripped):
            close_list()
            output.append("<hr>")
            continue

        unordered = re.match(r"^[-*]\s+(.+)$", stripped)
        if unordered:
            if list_type != "ul":
                close_list()
                output.append("<ul>")
                list_type = "ul"
            output.append(f"<li>{render_inline_markdown(unordered.group(1))}</li>")
            continue

        ordered = re.match(r"^\d+\.\s+(.+)$", stripped)
        if ordered:
            if list_type != "ol":
                close_list()
                output.append("<ol>")
                list_type = "ol"
            output.append(f"<li>{render_inline_markdown(ordered.group(1))}</li>")
            continue

        quote_match = re.match(r"^>\s?(.+)$", stripped)
        if quote_match:
            close_list()
            output.append(
                f"<blockquote>{render_inline_markdown(quote_match.group(1))}</blockquote>"
            )
            continue

        close_list()
        output.append(f"<p>{render_inline_markdown(stripped)}</p>")

    if in_code:
        output.append(
            "<pre><code>{0}</code></pre>".format(html.escape("\n".join(code_lines)))
        )
    close_list()
    return "\n".join(output)


def render_file_page(
    repo_path: str,
    body: str,
    action_href: str,
    action_label: str,
) -> str:
    title = html.escape(repo_path)
    return """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <style>
    :root {{
      --ink: #18212f;
      --muted: #687386;
      --paper: #fffaf0;
      --line: rgba(24, 33, 47, 0.14);
      --load: #275d8c;
    }}
    body {{
      margin: 0;
      color: var(--ink);
      background: linear-gradient(135deg, #faf3df 0%, #f7f2e8 100%);
      font: 16px/1.62 ui-sans-serif, system-ui, sans-serif;
    }}
    main {{
      max-width: 980px;
      margin: 28px auto;
      padding: 0 20px 48px;
    }}
    header {{
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 20px;
      border: 1px solid var(--line);
      border-radius: 22px 22px 0 0;
      background: rgba(255, 252, 245, 0.92);
      padding: 18px 22px;
    }}
    h1 {{
      margin: 0;
      font: 24px/1.2 ui-serif, Georgia, serif;
      word-break: break-word;
    }}
    a {{
      color: var(--load);
    }}
    .actions {{
      white-space: nowrap;
      font-size: 14px;
    }}
    .content {{
      border: 1px solid var(--line);
      border-top: 0;
      border-radius: 0 0 22px 22px;
      background: rgba(255, 252, 245, 0.92);
      padding: 22px;
    }}
    .markdownBody h1, .markdownBody h2, .markdownBody h3 {{
      font-family: ui-serif, Georgia, serif;
      letter-spacing: -0.03em;
      line-height: 1.18;
    }}
    .markdownBody h1 {{ font-size: 34px; }}
    .markdownBody h2 {{ font-size: 27px; margin-top: 28px; }}
    .markdownBody h3 {{ font-size: 22px; margin-top: 24px; }}
    .markdownBody code {{
      border-radius: 5px;
      background: rgba(24, 33, 47, 0.08);
      padding: 1px 5px;
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
    }}
    pre {{
      overflow: auto;
      border-radius: 14px;
      background: #fff7ea;
      padding: 16px;
      font: 13px/1.55 ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      white-space: pre-wrap;
      word-break: break-word;
    }}
    pre code {{
      background: transparent;
      padding: 0;
    }}
    blockquote {{
      margin: 18px 0;
      padding: 8px 16px;
      border-left: 4px solid rgba(39, 93, 140, 0.42);
      color: var(--muted);
      background: rgba(39, 93, 140, 0.06);
    }}
  </style>
</head>
<body>
  <main>
    <header>
      <h1>{title}</h1>
      <div class="actions"><a href="{action_href}" rel="noopener noreferrer">{action_label}</a></div>
    </header>
    <section class="content">
      {body}
    </section>
  </main>
</body>
</html>
""".format(
        title=title,
        action_href=html.escape(action_href),
        action_label=html.escape(action_label),
        body=body,
    )


def render_file_preview_page(repo_path: str, target: Path, source_href: str) -> str:
    content = target.read_text(encoding="utf-8", errors="replace")
    if is_markdown_path(target):
        body = f'<article class="markdownBody">{render_markdown(content)}</article>'
    else:
        body = f"<pre>{html.escape(content)}</pre>"
    return render_file_page(
        repo_path,
        body,
        source_href,
        "Open source text",
    )


def render_source_text_page(repo_path: str, target: Path, preview_href: str) -> str:
    content = target.read_text(encoding="utf-8", errors="replace")
    return render_file_page(
        repo_path,
        f"<pre>{html.escape(content)}</pre>",
        preview_href,
        "Back to markdown preview" if is_markdown_path(target) else "Back to preview",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build a local HTML dashboard for zero-memory graph structure and "
            "observability recall frequency."
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
        help="Rolling observability window in days. Defaults to 30.",
    )
    parser.add_argument(
        "--writer-scope",
        default="all",
        help=(
            "Event read scope. Defaults to all. Use current or comma-separated "
            "writer IDs only for focused debugging."
        ),
    )
    parser.add_argument(
        "--include-inactive",
        action="store_true",
        help="Include inactive memories in the dashboard.",
    )
    parser.add_argument(
        "--max-graph-nodes",
        type=int,
        default=36,
        help=(
            "Default maximum nodes to draw in the graph. The table still includes "
            "every memory. Defaults to 36 for readability."
        ),
    )
    parser.add_argument(
        "--output",
        help=(
            "Output HTML path. Defaults to .zero-memory/tmp/zero-memory-visual/index.html "
            "under the workspace root."
        ),
    )
    parser.add_argument(
        "--serve",
        action="store_true",
        help="Serve the generated dashboard with a local HTTP server.",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host for --serve. Defaults to 127.0.0.1.",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8765,
        help="Port for --serve. Use 0 to auto-select. Defaults to 8765.",
    )
    parser.add_argument(
        "--open",
        action="store_true",
        help="Open the served dashboard in the default browser.",
    )
    return parser.parse_args()


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def repo_relative(path_value: str, workspace_root: Path) -> str:
    path = Path(path_value)
    if not path.is_absolute():
        return path.as_posix()
    try:
        return path.resolve().relative_to(workspace_root.resolve()).as_posix()
    except ValueError:
        return str(path_value)


def normalized_repo_path(path_value: str, workspace_root: Path) -> str:
    text = str(path_value or "").strip()
    while text.startswith("./"):
        text = text[2:]
    if not text or "://" in text:
        return text
    path = Path(text)
    if path.is_absolute():
        return repo_relative(text, workspace_root)
    return text


def default_output_path(root: str) -> Path:
    return zero_memory_root(root) / "tmp" / "zero-memory-visual" / "index.html"


def average(values):
    if not values:
        return None
    return round(sum(values) / float(len(values)), 2)


def metric_value(metric: dict, key: str, default=0):
    return metric.get(key, default)


def build_memory_metrics(metric: dict) -> dict:
    recall_count = metric_value(metric, "recall_count")
    selected_count = metric_value(metric, "selected_count")
    helpful_count = metric_value(metric, "helpful_count")
    used_count = metric_value(metric, "used_in_final_answer_count")
    stale_count = metric_value(metric, "stale_hit_count")
    false_positive_count = metric_value(metric, "false_positive_count")
    missed_count = metric_value(metric, "missed_recall_count")
    hotness_score = round(
        1.0 * selected_count
        + 2.0 * helpful_count
        + 2.0 * used_count
        + 0.5 * recall_count,
        2,
    )
    routes = metric.get("routes", {})
    if hasattr(routes, "most_common"):
        common_routes = [
            {"route": route, "count": count}
            for route, count in routes.most_common(5)
        ]
    else:
        common_routes = []
    return {
        "recall_count": recall_count,
        "selected_count": selected_count,
        "helpful_count": helpful_count,
        "used_in_final_answer_count": used_count,
        "stale_hit_count": stale_count,
        "false_positive_count": false_positive_count,
        "missed_recall_count": missed_count,
        "hotness_score": hotness_score,
        "avg_depth_to_selected": average(metric.get("selected_depths", [])),
        "avg_depth_to_helpful": average(metric.get("helpful_depths", [])),
        "avg_candidate_count": average(metric.get("candidate_counts", [])),
        "common_routes": common_routes,
        "last_used_at": metric.get("last_used_at", ""),
    }


def graph_score(node: dict) -> float:
    metrics = node["metrics"]
    return max(
        metrics["hotness_score"],
        metrics["recall_count"],
        metrics["selected_count"],
        metrics["helpful_count"],
        metrics["missed_recall_count"],
    )


def build_dashboard_data(args: argparse.Namespace) -> dict:
    packages, duplicate_ids = load_memory_packages(args.root)
    if duplicate_ids:
        raise SystemExit(
            "Duplicate memory IDs exist; resolve them before visualizing zero-memory."
        )

    if not args.include_inactive:
        packages = [package for package in packages if package.get("status") == "active"]

    package_map = build_package_map(packages)
    reverse_load_next = build_reverse_load_next(
        package_map,
        include_inactive=args.include_inactive,
    )
    observability = load_events_bundle(
        args.root,
        days=args.days,
        streams={"recall", "reflection"},
        writer_scope=args.writer_scope,
    )
    metrics_by_id = aggregate_metrics(observability["events"])
    workspace_root = resolve_workspace_root(args.root)

    nodes = []
    for package in sorted(packages, key=lambda item: item["id"]):
        memory_id = package["id"]
        metrics = build_memory_metrics(metrics_by_id.get(memory_id, {}))
        freshness_profile, freshness_source = resolve_freshness_profile(package)
        parents = reverse_load_next.get(memory_id, [])
        node = {
            "id": memory_id,
            "slug": package.get("slug", ""),
            "name": package.get("name", memory_id),
            "path": repo_relative(package.get("path", ""), workspace_root),
            "description": package.get("description", ""),
            "layer": package.get("layer", "detailed") or "detailed",
            "status": package.get("status", "active"),
            "freshness_profile": freshness_profile,
            "freshness_source": freshness_source,
            "last_updated_at": package.get("last_updated_at", ""),
            "pattern_key": package.get("pattern_key", ""),
            "component": package.get("component", ""),
            "kind": package.get("kind", ""),
            "parents": parents,
            "load_next": dedupe(package.get("load_next", [])),
            "related": dedupe(package.get("related", [])),
            "related_files": dedupe(package.get("related_files", [])),
            "related_symbols": dedupe(package.get("related_symbols", [])),
            "tags": dedupe(package.get("tags", [])),
            "metrics": metrics,
        }
        node["graph_score"] = graph_score(node)
        nodes.append(node)

    known_ids = {node["id"] for node in nodes}
    edges = []
    for node in nodes:
        for target_id in node["load_next"]:
            if target_id in known_ids:
                edges.append(
                    {
                        "source": node["id"],
                        "target": target_id,
                        "type": "load_next",
                    }
                )
        for target_id in node["related"]:
            if target_id in known_ids:
                edges.append(
                    {
                        "source": node["id"],
                        "target": target_id,
                        "type": "related",
                    }
                )

    layer_counts = {}
    status_counts = {}
    total_recall = 0
    total_selected = 0
    total_helpful = 0
    total_missed = 0
    for node in nodes:
        layer_counts[node["layer"]] = layer_counts.get(node["layer"], 0) + 1
        status_counts[node["status"]] = status_counts.get(node["status"], 0) + 1
        total_recall += node["metrics"]["recall_count"]
        total_selected += node["metrics"]["selected_count"]
        total_helpful += node["metrics"]["helpful_count"]
        total_missed += node["metrics"]["missed_recall_count"]

    return {
        "metadata": {
            "generated_at": utc_timestamp(),
            "generated_by": SCRIPT_PATH,
            "root": args.root,
            "workspace_root": workspace_root.as_posix(),
            "file_link_base": FILE_LINK_DIR,
            "file_links": {},
            "file_raw_links": {},
            "window_days": args.days,
            "writer_scope": observability["writer_scope"],
            "source_writer_ids": observability["source_writer_ids"],
            "source_date_keys": observability["source_date_keys"],
            "source_min_timestamp": observability["source_min_timestamp"],
            "source_max_timestamp": observability["source_max_timestamp"],
            "source_event_file_count": observability["source_event_file_count"],
            "event_count": len(observability["events"]),
            "deduped_duplicate_event_count": observability[
                "deduped_duplicate_event_count"
            ],
            "memory_count": len(nodes),
            "edge_count": len(edges),
            "max_graph_nodes": args.max_graph_nodes,
            "include_inactive": args.include_inactive,
            "layer_counts": layer_counts,
            "status_counts": status_counts,
            "totals": {
                "recall_count": total_recall,
                "selected_count": total_selected,
                "helpful_count": total_helpful,
                "missed_recall_count": total_missed,
            },
        },
        "nodes": nodes,
        "edges": edges,
    }


def json_for_html(data: dict) -> str:
    return json.dumps(data, ensure_ascii=True).replace("</", "<\\/")


def load_client_app_js() -> str:
    if not CLIENT_APP_JS.exists():
        raise SystemExit(
            "Missing compiled UI asset: {0}. Rebuild it from assets/memory_visual_app.ts.".format(
                CLIENT_APP_JS
            )
        )
    if CLIENT_APP_TS.exists() and CLIENT_APP_TS.stat().st_mtime > CLIENT_APP_JS.stat().st_mtime:
        print(
            "Warning: TypeScript UI source is newer than the compiled JS asset. "
            "Rebuild assets/memory_visual_app.js before publishing.",
            file=sys.stderr,
        )
    return CLIENT_APP_JS.read_text(encoding="utf-8")


def render_html(data: dict) -> str:
    payload = json_for_html(data)
    client_app_js = load_client_app_js()
    html = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>ZeroAgentMemory</title>
  <style>
    :root {{
      --ink: #18212f;
      --muted: #687386;
      --paper: #f7f2e8;
      --panel: rgba(255, 252, 245, 0.9);
      --line: rgba(24, 33, 47, 0.16);
      --load: #275d8c;
      --related: #9a6432;
      --hot: #d24b2a;
      --helpful: #1f8a63;
      --missed: #b33b63;
      --quiet: #9aa3ae;
      --label-bg: rgba(255, 252, 245, 0.88);
      --shadow: 0 18px 50px rgba(37, 30, 20, 0.15);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      color: var(--ink);
      background:
        radial-gradient(circle at 18% 8%, rgba(210, 75, 42, 0.16), transparent 34rem),
        radial-gradient(circle at 82% 14%, rgba(39, 93, 140, 0.16), transparent 30rem),
        radial-gradient(circle at 52% 78%, rgba(31, 138, 99, 0.1), transparent 34rem),
        linear-gradient(135deg, #fbf3df 0%, #efe6d4 45%, #e8efe7 100%);
      font-family: "Iowan Old Style", "Palatino Linotype", Georgia, Cambria, serif;
      min-height: 100vh;
    }}
    header {{
      padding: 32px min(5vw, 64px) 18px;
    }}
    h1 {{
      margin: 0;
      font-size: clamp(34px, 5vw, 70px);
      line-height: 0.95;
      letter-spacing: -0.05em;
      max-width: 900px;
    }}
    .subtitle {{
      margin-top: 14px;
      color: var(--muted);
      font: 15px/1.6 ui-sans-serif, system-ui, sans-serif;
      max-width: 940px;
    }}
    .toolbar {{
      display: grid;
      gap: 12px;
      grid-template-columns: minmax(180px, 1.7fr) repeat(3, minmax(130px, 0.55fr));
      padding: 0 min(5vw, 64px) 18px;
    }}
    input, select {{
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 16px;
      background: rgba(255, 255, 255, 0.7);
      padding: 12px 14px;
      color: var(--ink);
      font: 14px ui-sans-serif, system-ui, sans-serif;
      outline: none;
    }}
    input:focus, select:focus {{ border-color: rgba(39, 93, 140, 0.55); }}
    .stats {{
      display: grid;
      grid-template-columns: repeat(6, minmax(120px, 1fr));
      gap: 12px;
      padding: 0 min(5vw, 64px) 24px;
    }}
    .stat {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 20px;
      padding: 14px 16px;
      box-shadow: var(--shadow);
    }}
    .stat b {{
      display: block;
      font-size: 25px;
      letter-spacing: -0.03em;
    }}
    .stat span {{
      color: var(--muted);
      font: 12px/1.4 ui-sans-serif, system-ui, sans-serif;
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }}
    main {{
      display: grid;
      grid-template-columns: minmax(360px, 1.25fr) minmax(320px, 0.75fr);
      gap: 18px;
      padding: 0 min(5vw, 64px) 36px;
    }}
    .panel {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 26px;
      box-shadow: var(--shadow);
      overflow: hidden;
      backdrop-filter: blur(12px);
    }}
    .panel h2 {{
      margin: 0;
      padding: 18px 20px;
      border-bottom: 1px solid var(--line);
      font-size: 20px;
      letter-spacing: -0.03em;
    }}
    .panelHead {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      padding: 16px 18px;
      border-bottom: 1px solid var(--line);
    }}
    .panelHead h2 {{
      padding: 0;
      border: 0;
    }}
    .graphControls {{
      display: flex;
      align-items: center;
      justify-content: flex-end;
      flex-wrap: wrap;
      gap: 8px;
      color: var(--muted);
      font: 12px ui-sans-serif, system-ui, sans-serif;
    }}
    .graphControls select {{
      width: auto;
      min-width: 150px;
      padding: 8px 10px;
      border-radius: 12px;
      font-size: 12px;
    }}
    .graphControls input[type="range"] {{
      width: 120px;
      padding: 0;
      accent-color: var(--load);
    }}
    .graphControls label {{
      display: inline-flex;
      align-items: center;
      gap: 7px;
      white-space: nowrap;
    }}
    #graphWrap {{
      min-height: 740px;
      position: relative;
      overflow: hidden;
      isolation: isolate;
      background:
        radial-gradient(circle at 12% 54%, rgba(39, 93, 140, 0.13), transparent 26rem),
        radial-gradient(circle at 76% 43%, rgba(31, 138, 99, 0.11), transparent 28rem),
        linear-gradient(180deg, rgba(255, 252, 245, 0.9), rgba(249, 246, 238, 0.68));
    }}
    #graphWrap::before {{
      content: "";
      position: absolute;
      inset: 0;
      z-index: 0;
      opacity: 0.42;
      background-image:
        linear-gradient(rgba(24, 33, 47, 0.045) 1px, transparent 1px),
        linear-gradient(90deg, rgba(24, 33, 47, 0.035) 1px, transparent 1px);
      background-size: 42px 42px;
      mask-image: radial-gradient(circle at 50% 54%, black, transparent 72%);
    }}
    #graph {{
      position: relative;
      z-index: 1;
      width: 100%;
      height: 720px;
      display: block;
    }}
    .graphStatus {{
      position: relative;
      z-index: 2;
      display: inline-block;
      margin: 16px 16px 10px;
      max-width: min(560px, calc(100% - 32px));
      border: 1px solid rgba(24, 33, 47, 0.12);
      border-radius: 999px;
      background: rgba(255, 252, 245, 0.74);
      padding: 8px 13px;
      color: var(--muted);
      font: 12px/1.35 "Avenir Next", "Gill Sans", ui-sans-serif, system-ui, sans-serif;
      box-shadow: 0 12px 30px rgba(24, 33, 47, 0.08);
      backdrop-filter: blur(12px);
    }}
    .legend {{
      position: absolute;
      z-index: 2;
      right: 16px;
      bottom: 14px;
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
      font: 12px ui-sans-serif, system-ui, sans-serif;
      color: var(--muted);
    }}
    .legend i {{
      width: 10px;
      height: 10px;
      border-radius: 50%;
      display: inline-block;
      margin-right: 5px;
    }}
    .tableWrap {{ max-height: 560px; overflow: auto; }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font: 13px ui-sans-serif, system-ui, sans-serif;
    }}
    th {{
      position: sticky;
      top: 0;
      z-index: 1;
      background: #fff8ec;
      text-align: left;
      padding: 10px 12px;
      border-bottom: 1px solid var(--line);
      color: var(--muted);
      cursor: pointer;
      white-space: nowrap;
    }}
    td {{
      padding: 10px 12px;
      border-bottom: 1px solid rgba(24, 33, 47, 0.08);
      vertical-align: top;
    }}
    tr:hover {{ background: rgba(39, 93, 140, 0.07); }}
    tr.selected {{ background: rgba(210, 75, 42, 0.12); }}
    .memoryId {{
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      font-size: 12px;
      word-break: break-word;
    }}
    .pill {{
      display: inline-flex;
      align-items: center;
      border-radius: 999px;
      padding: 3px 8px;
      margin: 2px 4px 2px 0;
      background: rgba(24, 33, 47, 0.08);
      color: var(--muted);
      font: 12px ui-sans-serif, system-ui, sans-serif;
    }}
    button.pill {{
      border: 0;
      cursor: pointer;
    }}
    button.pill:hover {{
      background: rgba(39, 93, 140, 0.16);
      color: var(--ink);
    }}
    a.fileLink {{
      text-decoration: none;
      color: var(--load);
    }}
    a.fileLink:hover {{
      color: var(--hot);
      text-decoration: underline;
      text-decoration-thickness: 2px;
      text-underline-offset: 3px;
    }}
    a.fileLink code {{
      color: inherit;
    }}
    .filePreview {{
      margin-top: 18px;
      border: 1px solid var(--line);
      border-radius: 18px;
      background: rgba(255, 255, 255, 0.58);
      overflow: hidden;
    }}
    .filePreview[hidden] {{
      display: none;
    }}
    .filePreviewHead {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      padding: 10px 12px;
      border-bottom: 1px solid rgba(24, 33, 47, 0.1);
      color: var(--muted);
      font: 12px ui-sans-serif, system-ui, sans-serif;
    }}
    .filePreviewHead strong {{
      color: var(--ink);
      word-break: break-all;
    }}
    .filePreview pre {{
      margin: 0;
      max-height: 520px;
      overflow: auto;
      padding: 14px;
      color: #111827;
      background: rgba(255, 252, 245, 0.78);
      font: 12px/1.55 ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      white-space: pre-wrap;
      word-break: break-word;
    }}
    .markdownPreview {{
      max-height: 620px;
      overflow: auto;
      padding: 16px 18px;
      background: rgba(255, 252, 245, 0.78);
    }}
    .markdownPreview h1, .markdownPreview h2, .markdownPreview h3 {{
      font-family: ui-serif, Georgia, serif;
      letter-spacing: -0.03em;
      line-height: 1.18;
    }}
    .markdownPreview h1 {{ font-size: 29px; }}
    .markdownPreview h2 {{ font-size: 24px; margin-top: 24px; }}
    .markdownPreview h3 {{ font-size: 20px; margin-top: 20px; }}
    .markdownPreview p {{
      margin: 10px 0;
    }}
    .markdownPreview ul, .markdownPreview ol {{
      padding-left: 24px;
    }}
    .markdownPreview code {{
      border-radius: 5px;
      background: rgba(24, 33, 47, 0.08);
      padding: 1px 5px;
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
    }}
    .markdownPreview pre {{
      max-height: none;
      margin: 12px 0;
      border-radius: 12px;
    }}
    .markdownPreview pre code {{
      background: transparent;
      padding: 0;
    }}
    .markdownPreview blockquote {{
      margin: 14px 0;
      padding: 7px 14px;
      border-left: 4px solid rgba(39, 93, 140, 0.42);
      color: var(--muted);
      background: rgba(39, 93, 140, 0.06);
    }}
    .filePreviewAction {{
      border: 0;
      background: transparent;
      color: var(--load);
      cursor: pointer;
      font: inherit;
      text-decoration: none;
      white-space: nowrap;
    }}
    .filePreviewAction:hover {{
      color: var(--hot);
      text-decoration: underline;
      text-underline-offset: 3px;
    }}
    #details {{
      padding: 18px 20px 22px;
      font: 14px/1.55 ui-sans-serif, system-ui, sans-serif;
    }}
    #details h3 {{
      margin: 0 0 8px;
      font: 23px/1.15 ui-serif, Georgia, serif;
      letter-spacing: -0.03em;
      word-break: break-word;
    }}
    #details .desc {{ color: #334155; }}
    #details dl {{
      display: grid;
      grid-template-columns: 150px 1fr;
      gap: 7px 14px;
      margin: 16px 0;
    }}
    #details dt {{ color: var(--muted); }}
    #details dd {{ margin: 0; word-break: break-word; }}
    .routes {{
      margin: 0;
      padding-left: 18px;
    }}
    .node {{
      cursor: pointer;
      filter: drop-shadow(0 9px 15px rgba(24, 33, 47, 0.16));
      transition: opacity 140ms ease, filter 140ms ease, transform 140ms ease;
    }}
    .node:hover {{ opacity: 0.86; filter: drop-shadow(0 13px 22px rgba(24, 33, 47, 0.22)); }}
    .nodeHalo {{
      fill: rgba(24, 33, 47, 0.04);
      stroke: rgba(24, 33, 47, 0.2);
      stroke-width: 1.2;
    }}
    .edge {{
      stroke-opacity: 0.12;
      stroke-linecap: round;
      stroke-linejoin: round;
    }}
    .edge.load_next {{ stroke-opacity: 0.2; }}
    .edge.selected {{ stroke-opacity: 0.48; }}
    .drilldownBand {{
      fill: rgba(255, 252, 245, 0.25);
      stroke: rgba(24, 33, 47, 0.055);
      stroke-width: 1;
      pointer-events: none;
    }}
    .drilldownBand.selected {{ fill: rgba(39, 93, 140, 0.055); }}
    .drilldownBand.load_next {{ fill: rgba(31, 138, 99, 0.05); }}
    .drilldownBand.related {{ fill: rgba(154, 100, 50, 0.045); }}
    .label {{
      font: 650 11px/1 "Avenir Next", "Gill Sans", ui-sans-serif, system-ui, sans-serif;
      fill: rgba(31, 42, 58, 0.88);
      pointer-events: none;
      letter-spacing: 0.005em;
    }}
    .labelBox {{
      fill: rgba(255, 252, 245, 0.68);
      stroke: rgba(24, 33, 47, 0.11);
      pointer-events: none;
      filter: drop-shadow(0 5px 12px rgba(24, 33, 47, 0.07));
    }}
    .featuredLabel {{
      font-weight: 800;
      fill: var(--ink);
    }}
    .featuredLabelBox {{
      fill: rgba(255, 252, 245, 0.92);
      stroke: rgba(24, 33, 47, 0.22);
    }}
    .drilldownHeader {{
      fill: rgba(255, 252, 245, 0.86);
      stroke: rgba(24, 33, 47, 0.11);
    }}
    footer {{
      padding: 0 min(5vw, 64px) 34px;
      color: var(--muted);
      font: 12px/1.5 ui-sans-serif, system-ui, sans-serif;
    }}
    @media (max-width: 980px) {{
      .toolbar, .stats, main {{ grid-template-columns: 1fr; }}
      .panelHead {{ align-items: flex-start; flex-direction: column; }}
      .graphControls {{ justify-content: flex-start; }}
      #graph {{ height: 560px; }}
      #graphWrap {{ min-height: 590px; }}
    }}
  </style>
</head>
<body>
  <header>
    <h1>ZeroAgentMemory</h1>
    <p class="subtitle" id="subtitle"></p>
  </header>

  <section class="toolbar">
    <input id="search" placeholder="Search memory id, description, file, tag, or pattern key">
    <select id="layerFilter"></select>
    <select id="statusFilter"></select>
    <select id="sortKey">
      <option value="hotness_score">Sort by hotness</option>
      <option value="recall_count">Sort by recall frequency</option>
      <option value="helpful_count">Sort by helpful count</option>
      <option value="missed_recall_count">Sort by missed recall</option>
      <option value="last_used_at">Sort by last used</option>
    </select>
  </section>

  <section class="stats" id="stats"></section>

  <main>
    <section class="panel">
      <div class="panelHead">
        <h2>Graph</h2>
        <div class="graphControls">
          <select id="graphMode">
            <option value="init">Init nodes</option>
            <option value="drilldown">Layer drilldown</option>
            <option value="focus">Readable overview</option>
            <option value="all">All matching nodes</option>
          </select>
          <label>Nodes <input id="nodeLimit" type="range" min="12" max="120" step="1"></label>
          <span id="nodeLimitLabel"></span>
        </div>
      </div>
      <div id="graphWrap">
        <div class="graphStatus" id="graphStatus"></div>
        <svg id="graph" role="img" aria-label="Zero-memory graph visualization"></svg>
        <div class="legend">
          <span><i style="background: var(--hot)"></i>hot</span>
          <span><i style="background: var(--helpful)"></i>helpful</span>
          <span><i style="background: var(--missed)"></i>missed</span>
          <span><i style="background: var(--quiet)"></i>quiet</span>
        </div>
      </div>
    </section>

    <section class="panel">
      <h2>Selected Memory</h2>
      <div id="details"></div>
    </section>
  </main>

  <section class="panel" style="margin: 0 min(5vw, 64px) 28px;">
    <h2>Memory Recall Table</h2>
    <div class="tableWrap">
      <table>
        <thead>
          <tr>
            <th data-sort="id">Memory</th>
            <th data-sort="recall_count">Recall</th>
            <th data-sort="selected_count">Selected</th>
            <th data-sort="helpful_count">Helpful</th>
            <th data-sort="missed_recall_count">Missed</th>
            <th data-sort="hotness_score">Hotness</th>
            <th data-sort="layer">Layer</th>
            <th data-sort="status">Status</th>
          </tr>
        </thead>
        <tbody id="memoryRows"></tbody>
      </table>
    </div>
  </section>

  <footer id="footer"></footer>
  <script id="memory-data" type="application/json">__ZERO_MEMORY_DATA__</script>
  <script>
__ZERO_MEMORY_APP_JS__
  </script>
</body>
</html>
"""
    html = html.replace("{{", "{").replace("}}", "}")
    return (
        html.replace("__ZERO_MEMORY_DATA__", payload)
        .replace("__ZERO_MEMORY_APP_JS__", client_app_js)
    )


def iter_file_link_candidates(data: dict) -> list[str]:
    workspace_root = Path(str(data["metadata"].get("workspace_root", ""))).resolve()
    candidates = []
    for node in data.get("nodes", []):
        candidates.append(normalized_repo_path(node.get("path", ""), workspace_root))
        for related_file in node.get("related_files", []):
            candidates.append(normalized_repo_path(related_file, workspace_root))
    return dedupe([candidate for candidate in candidates if candidate])


def prepare_file_links(output: Path, data: dict) -> None:
    workspace_root = Path(str(data["metadata"].get("workspace_root", ""))).resolve()
    link_root = output.parent / FILE_LINK_DIR
    data["metadata"]["file_links"] = {}
    data["metadata"]["file_raw_links"] = {}
    if link_root.exists() or link_root.is_symlink():
        if link_root.is_dir() and not link_root.is_symlink():
            shutil.rmtree(link_root)
        else:
            link_root.unlink()
    link_root.mkdir(parents=True, exist_ok=True)

    for repo_path in iter_file_link_candidates(data):
        if "://" in repo_path:
            continue
        repo_path_obj = Path(repo_path)
        if repo_path_obj.is_absolute() or ".." in repo_path_obj.parts:
            continue
        target = (workspace_root / repo_path).resolve()
        try:
            target.relative_to(workspace_root)
        except ValueError:
            continue
        if not target.is_file():
            continue
        file_id = hashlib.sha256(repo_path.encode("utf-8")).hexdigest()[:16]
        fetch_relative_path = Path(file_id) / "fetch" / target.name
        fetch_path = link_root / fetch_relative_path
        fetch_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            fetch_path.symlink_to(target)
        except FileExistsError:
            pass
        preview_relative_path = Path(file_id) / "index.html"
        preview_path = link_root / preview_relative_path
        source_relative_path = Path(file_id) / "raw" / target.name
        source_path = link_root / source_relative_path
        source_path.parent.mkdir(parents=True, exist_ok=True)
        preview_path.write_text(
            render_file_preview_page(repo_path, target, f"raw/{quote(target.name)}"),
            encoding="utf-8",
        )
        source_path.write_text(
            render_source_text_page(repo_path, target, "../index.html"),
            encoding="utf-8",
        )
        data["metadata"]["file_links"][repo_path] = (
            f"{FILE_LINK_DIR}/{url_path(preview_relative_path)}"
        )
        data["metadata"]["file_raw_links"][repo_path] = (
            f"{FILE_LINK_DIR}/{url_path(fetch_relative_path)}"
        )


def write_html(path: Path, html: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")


def serve(path: Path, host: str, port: int, should_open: bool) -> None:
    os.chdir(path.parent)
    server = ThreadingHTTPServer((host, port), TextFriendlyRequestHandler)
    actual_host, actual_port = server.server_address
    url = f"http://{actual_host}:{actual_port}/{path.name}"
    print(f"Serving zero-memory visual dashboard: {url}", flush=True)
    if should_open:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.", flush=True)


def main() -> int:
    args = parse_args()
    output = Path(args.output).resolve() if args.output else default_output_path(args.root)
    data = build_dashboard_data(args)
    prepare_file_links(output, data)
    html = render_html(data)
    write_html(output, html)
    print("Wrote zero-memory visual dashboard: {0}".format(output))
    print(
        "Memories: {0}; edges: {1}; events: {2}; window_days: {3}; writer_scope: {4}".format(
            data["metadata"]["memory_count"],
            data["metadata"]["edge_count"],
            data["metadata"]["event_count"],
            data["metadata"]["window_days"],
            data["metadata"]["writer_scope"],
        )
    )
    if args.serve:
        serve(output, args.host, args.port, args.open)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
