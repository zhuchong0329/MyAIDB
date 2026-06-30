---
name: zero-memory-visual
description: Build and optionally serve a local TypeScript-backed web UI that visualizes `.zero-memory/memory/` graph structure together with recall frequency, selection, helpfulness, missed-recall, staleness, and hotness metrics from `.zero-memory/observability/` events.
---

# Zero Memory Visual

Use this skill when a user wants a browser-based view of the zero-memory graph, wants to inspect memory recall frequency, or wants to combine curated memory structure with observability telemetry.

## Path Convention

When this skill says to run a bundled helper or compile a bundled asset, resolve it from this skill's own directory instead of hardcoding a workspace-specific skill path. In examples below, `${visual_scripts}` means the resolved `scripts/` directory for the active `zero-memory-visual` skill, and `${visual_assets}` means its resolved `assets/` directory.

## Quick Start

From the workspace root, generate a standalone HTML dashboard:

```bash
python3 "${visual_scripts}/render_memory_visual.py" \
  --root .zero-memory/memory
```

Generate and serve the dashboard locally:

```bash
python3 "${visual_scripts}/render_memory_visual.py" \
  --root .zero-memory/memory \
  --serve \
  --port 8765
```

The default output is `.zero-memory/tmp/zero-memory-visual/index.html`. Pass `--output <path>` when the workspace has stricter scratch-output placement rules.

Freshness rule: every invocation of this skill must regenerate the dashboard from the current `--root` memory graph before serving, opening, or reporting an existing URL. Do not rely on an older generated `index.html` or a long-running server as evidence that the graph is current; rerun the renderer first, then verify the served page when applicable.

## What The UI Shows

- An init-node entry view that shows the graph's starting memories first.
- A layer-by-layer drilldown graph centered on the clicked memory node.
- Readability controls for init nodes, drilldown, focused overview, or full matching-node graph modes.
- A sortable table with every memory and its recall metrics.
- Per-memory details: description, status, layer, parents, children, related memories, related files, and common recall routes.
- Generated, source-event, and last-used timestamps displayed in the viewer's local timezone, while raw UTC values remain available for audit where useful.
- Recall frequency from observability events:
  - `recall_count`: how often a memory appeared in graph-load or index-query results.
  - `selected_count`: how often an agent selected it as relevant.
  - `helpful_count`: how often it was recorded as helpful.
  - `used_in_final_answer_count`: how often it influenced final output.
  - `missed_recall_count`: how often it was recorded as missed or found late.
  - `stale_hit_count` and `false_positive_count`: review-quality signals.

## Workflow

1. Run the renderer from the workspace root or pass an explicit `--root` so the output is rebuilt from the current memory graph.
2. If a dashboard server is already running, treat it only as a reusable transport: overwrite the generated output first, then verify that the served page responds from the refreshed file. Restart the server if it cannot serve the refreshed output.
3. Use `--days <n>` to choose the rolling observability window; default is `30`.
4. Keep `--writer-scope all` for normal visualization so the dashboard aggregates all visible writer shards.
5. Use the default `Init nodes` graph for first inspection; it shows only the memory graph's entry points.
6. Click an init node to enter layer drilldown, which centers that memory and lays out upstream parents, `load_next` children, related peers, and other correlated nodes in separate columns.
7. Keep clicking graph nodes or table rows to make that memory the drilldown center and continue walking deeper through the graph.
8. Use the UI graph-mode selector for focused overview or full matching-node audit views.
9. Use `--max-graph-nodes <n>` to adjust the drilldown or overview graph size when needed.
10. If the user wants to inspect it immediately, use `--serve`; otherwise provide the generated HTML path.

## TypeScript UI Source

- Browser UI source lives in `assets/memory_visual_app.ts`.
- The renderer embeds the compiled snapshot `assets/memory_visual_app.js`, so normal dashboard generation does not require TypeScript tooling.
- After editing the TypeScript source, refresh the compiled snapshot with:

```bash
npx --yes --package typescript tsc \
  --target ES2020 \
  --lib DOM,ES2020 \
  --module preserve \
  --strict false \
  --noImplicitAny false \
  --strictNullChecks false \
  "${visual_assets}/memory_visual_app.ts"
```

- Regenerate the dashboard after refreshing the snapshot.

## Notes

- The script reads memory packages and observability events but does not mutate memory, reports, or events.
- If latest observability reports are missing or stale, the script still computes metrics directly from events.
- For public examples, use neutral zero-memory terms only. Do not include workspace-specific project names, hostnames, issue IDs, or local paths in this skill.
