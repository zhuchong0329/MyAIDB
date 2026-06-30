# Task Context Template

Use or adapt this structure for `.zero-memory/context/<task_slug>/`.

## Recommended Layout

```text
.zero-memory/context/<task_slug>/
  context.md
  references/
    original-context-analysis.md
    debug-notes.md
  scripts/
    helper.py
```

- `context.md` is the summary entrypoint a restarted agent should read first.
- `references/` stores durable deeper detail that is useful but too large or too noisy for `context.md`.
- `scripts/` stores useful task-local helpers that support reproduction, parsing, or verification.
- Prefer repo-local paths inside `context.md`; avoid absolute repo/worktree paths unless the task specifically depends on them.

## Summary `context.md` Template

```markdown
---
name: <task_slug_or_short_task_name>
description: <one-line summary of the goal and current state>
---

# <Task Title>

## Context Path
- `.zero-memory/context/<task_slug>/context.md`

## Status
- active | blocked | completed

## Goal
- Short statement of the task outcome.

## Current Understanding
- Key facts that are currently believed to be true.

## Decisions
- Decision: <what was chosen>
- Why: <brief rationale>

## Assumptions To Verify
- <assumption still needing confirmation>

## Touched Files / Systems
- `<path-or-symbol>`

## Verification
- Done: <checks already completed>
- Pending: <checks still needed>

## References
- `references/original-context-analysis.md` - Detailed analysis split out from the original full `context.md` during summarization.
- `references/debug-notes.md` - Curated debugging details and reproduction notes that are too detailed for the summary.

## Task Scripts
- `scripts/helper.py` - Optional task-local helper for reproduction, parsing, or verification.

## Progress Log
- <timestamp or milestone>: <high-signal update>

## Resume From Here
- Next step: <the first thing a restarted agent should do>
- Watchouts: <pitfalls or stale assumptions to avoid>

## Completion Notes
- Final result: <what changed>
- Follow-up: <remaining work, if any>
- Corrections: <earlier misunderstanding corrected here>
```

## Daily-Learning Handoff Template

When a new or reconciled context item is reusable beyond the current task, extract it into `.zero-memory/daily/learning.YYYY-MM-DD.md`.

Before deciding not to extract, ask:

- did useful work or problem-solving uncover a non-obvious solution through investigation?
- did the task require a workaround for unexpected behavior?
- did it reveal a project-specific pattern worth reusing?
- did an error require debugging to resolve?

```markdown
## DL-20260401-173000.123Z-a1b2c3d4
- Timestamp: 2026-04-01T17:30:00Z
- Source Slug: <task-slug>
- Source Context: .zero-memory/context/<task-slug>/context.md
- Type: best-practice | knowledge-gap | feature-gap | incident
- Summary: <concise reusable lesson>
- Details: <durable detail only>
- Why Reusable: <why this matters beyond the task>
- Suggested Memory Targets:
  - <memory-id>
- Source Sections:
  - Decisions
  - Completion Notes
- Status: new
```

Notes:

- Use the globally unique ID format `DL-YYYYMMDD-HHMMSS.mmmZ-<random-suffix>`.
- Keep timestamps in UTC and include the `Z` suffix explicitly.
- Preserve provenance back to the task context and source sections.
- If the answer to any of the four questions above is yes, strongly consider extraction unless the content is still task-local, raw-log-heavy, or unverified.
- Do not copy raw logs or negotiation text into daily learning.

## When Summarizing an Existing `context.md`

If the user asks for a summary or the file has become too large:

1. If `context.md` exceeds `20,000` bytes or `200` lines, use `zero-context-compact` instead of ad-hoc trimming.
2. Split the original detailed content into multiple files under `references/`.
3. Keep the new `context.md` short and current.
4. Add `## References` entries that explain which parts of the original context were moved into which files.
5. Prefer descriptive filenames over generic chunk names when possible.
6. If compaction moved or compressed cross-task reusable knowledge that would now be easy to miss, including a rule, correction, debugging method, reusable behavior note, or durable recall cue, append a daily-learning entry and hand it to `zero-memory-curator` in the same turn. Keep task-local code-structure, call-path, design rationale, and debug chronology in `references/` unless the reusable abstraction itself is clear.
7. Keep `context.md` under `20,000` bytes and `200` lines; use `python3 skills/zero-context-persistence/scripts/compact_context.py --max-bytes 20000 --max-lines 200` when a deterministic rewrite is needed.

Example split:

- `references/original-context-current-understanding.md` - Current-understanding and analysis sections copied from the original large `context.md`.
- `references/original-context-progress-log.md` - Older milestone history moved out of the summary during context compaction.

## Writing Guidance

- Always start `context.md` with YAML frontmatter containing at least `name` and `description`.
- Keep `name` stable for the same task so resumed sessions recognize the file as the same context.
- Keep `description` short and update it when the task focus or status meaningfully changes.
- Prefer concise summaries over raw logs.
- Prefer repo-local references such as `./`, `.zero-memory/context/...`, and relative file paths over `Active repo: /abs/path` notes.
- Do not add absolute repo/worktree paths to normal task notes unless the exact path is itself part of the issue being tracked.
- Put durable debug detail in `references/`; put disposable raw logs and build output under workspace-root `.zero-memory/tmp/<context_name>/` when an active context exists.
- Use `zero-context-compact` before `context.md` grows beyond `20,000` bytes or `200` lines when the file needs a deterministic summary-plus-references rewrite.
- When compaction materially shortens the summary entrypoint, evaluate whether any cross-task reusable change now needs promotion through `.zero-memory/daily/` and `zero-memory-curator` so it remains recallable outside the task-local references, including reusable code-structure cues or other durable lookup paths.
- Do not promote task-local analysis just because it was moved into `references/`; promote only the reusable abstraction, correction, workflow rule, or lookup cue.
- When a script matters for continuation, mention it in `context.md` with its purpose and assumptions.
- Keep the latest truth easy to spot.
- When an earlier assumption becomes wrong, leave a visible correction instead of silently letting stale notes stand.
- If the task spans multiple repos, keep the context directory in the current workspace root unless the user explicitly requests another location.
