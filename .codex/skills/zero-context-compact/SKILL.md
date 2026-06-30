---
name: zero-context-compact
description: Refresh an oversized task context by moving the current `context.md` detail into durable `references/` files and snapshots, then rewriting a new summary-first `context.md`. Use when an active context exceeds 20,000 bytes or 200 lines, grows too noisy, or the user asks to compact a context without losing its history.
---

# Zero Context Compact

Use this skill when an existing `.zero-memory/context/<task_slug>/context.md` has become too large or too noisy to remain a good restart entrypoint.

This skill keeps the task history durable by preserving the current context detail under `references/`, then rewriting `context.md` into a short summary with key status, current understanding, next step, and reference pointers.

## Trigger rule

Use this skill when any condition is true:

- the active `context.md` is larger than `20,000` bytes
- the active `context.md` is longer than `200` lines
- the user explicitly asks to compact, summarize, or refresh a context without discarding older detail

Both hard limits are automatic triggers from `zero-context-persistence`.

## Script Path Convention

When this skill says to run a bundled helper, resolve it from the referenced skill's `scripts/` directory instead of hardcoding a workspace-specific skill path. In examples below, `${context_persistence_scripts}` means the resolved `scripts/` directory for the active `zero-context-persistence` skill.

## Workflow

1. Determine the target context path.
   - If the user gave a `context.md` path, use it.
   - Otherwise resolve the active path from `.zero-memory/tmp/current-context.txt`.
2. Analyze the current context before rewriting it.
   - Read the current `context.md` first; do not run the rewrite as a blind size-reduction step.
   - Identify current status, key decisions, corrections, reusable cross-task lessons, and task-local detail that should stay available for restart, audit, or debugging.
   - Identify raw or highly detailed sections that should be preserved in `references/` or snapshots rather than copied verbatim into daily notes or curated memory.
   - Keep task-specific code-structure, call-path, and design rationale in `references/` unless it expresses a reusable rule, lookup cue, or workflow constraint that future tasks can recall through the memory graph.
   - For each detailed section that may need future retrieval, record stable lookup hints such as the source heading, distinctive phrases, file or symbol names, and 3-8 search keywords that can find the original detail later with `rg` or `grep`.
3. Check the current size before rewriting.
   - Example: `wc -lc .zero-memory/context/<task_slug>/context.md`
4. When the file is over `20,000` bytes or `200` lines, run the deterministic compaction script:

```bash
python3 "${context_persistence_scripts}/compact_context.py" \
  --context-path .zero-memory/context/<task_slug>/context.md \
  --max-bytes 20000 \
  --max-lines 200 \
  --target-lines 120
```

5. Review the rewritten `context.md`.
   - Confirm it now reads like a restart-safe summary instead of a log dump.
   - Confirm durable detail moved into `references/` files such as `analysis.md`, `verification.md`, `history.md`, and `artifacts.md`.
   - Confirm a raw snapshot was preserved under `references/snapshots/` unless the run intentionally skipped snapshots.
6. Evaluate whether compaction moved or compressed reusable knowledge that would now be easy to miss from the shorter summary.
   - If a preserved correction, workflow rule, debugging method, reusable behavior note, or durable recall cue is useful beyond the current task, append it to `.zero-memory/daily/learning.YYYY-MM-DD.md`.
   - Do not promote task-local code-structure, call-path, or design-decision detail merely because it is detailed or expensive to rediscover. Preserve that material in `references/` unless the reusable abstraction itself is clear.
   - When the original detail is too large or too raw for a daily note, summarize the reusable part instead of copying the raw text. Include an `Original Detail Lookup` or `Search Keywords` line with enough `rg` or `grep` terms to find the preserved source detail in `context.md`, `references/`, or `references/snapshots/`.
   - When handing the item to `zero-memory-curator`, keep the compact summary and the original-detail lookup hints in the curated memory if they will help future agents find the fuller preserved context.
   - In the same turn, hand the new daily-learning IDs to `zero-memory-curator` so the compacted-away change remains reachable through curated memory instead of living only in archived references.
   - If compaction only moved task-local detail, do not invent a memory entry.
7. If the user explicitly asked for compaction even when the file is smaller than the hard limits, rerun with `--force`.

## Output expectations

- The old detailed context is preserved in `references/` instead of being discarded.
- The new `context.md` becomes a short summary-first entrypoint.
- Any cross-task reusable knowledge made easier to lose during compaction is promoted through `.zero-memory/daily/` and `zero-memory-curator` in the same turn.
- Task-local analysis, code paths, design rationale, and debug chronology stay in `references/` unless they contain a reusable rule or recall cue.
- Oversized raw detail is summarized for daily notes or memory instead of copied wholesale, with search keywords that can retrieve the preserved original detail by `rg` or `grep`.
- The summary should keep:
  - current status
  - key current understanding
  - next recommended step
  - pointers to the preserved reference files

## Notes

- Do not dump raw temporary logs into `references/`; keep scratch output under `.zero-memory/tmp/<context_name>/`.
- If the generated summary is still too large or the buckets need better naming, do a small follow-up edit after the deterministic rewrite instead of hand-rebuilding the whole context from scratch.
