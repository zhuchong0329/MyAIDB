<!-- BEGIN zero-memory AGENTS.md -->
<INSTRUCTIONS>

## Zero Context Persistence
- Force rule: for task-local continuation state that lets a restarted agent resume work from the saved context, the agent must use the `zero-context-persistence` skill; treat `.zero-memory/tmp/current-context.txt` as the authoritative active context-path handoff, keep that exact path updated during the task, and do not switch to another context path arbitrarily.
- **TIMING RULE — NEVER SKIP**: When the agent is using an active `context.md` and is about to present results or next steps to the user, it MUST update `context.md` FIRST, THEN respond in chat. The correct context-persistence order is always: (1) persist context -> (2) chat response. If the agent realizes it forgot to update `context.md` before responding, it must update it immediately in the same turn, not wait for the user to ask.
- If the active context path is unknown, first load it from `.zero-memory/tmp/current-context.txt` by running `cat .zero-memory/tmp/current-context.txt`. If that file is empty, use `default` as the context name, resolve it to `.zero-memory/context/default/context.md`, update `.zero-memory/tmp/current-context.txt` to that resolved path, and continue from that context.
- Do not change the active context path arbitrarily during a task. Only use another context path when the user or workflow explicitly provides that exact path and intentionally replaces the current one.
- If the context path is known, use `zero-context-persistence` to read or create `context.md`; the file must start with YAML frontmatter containing at least `name:` and `description:`, then keep it updated with concise, restart-safe notes during the task.
- Log the information a restarted agent needs to continue, audit, or debug the task: goal, current understanding, key decisions and rationale, important raw evidence or links to preserved raw detail, assumptions to verify, touched files, verification status, blockers, and next steps.
- When a new or reconciled context item is reusable beyond the task, extract it into `.zero-memory/daily/learning.YYYY-MM-DD.md` and hand the new daily-learning ID to `zero-memory-curator`.
- On task completion, reconcile the latest understanding with `context.md`: append durable findings, mark the current status, and explicitly correct earlier misunderstandings instead of leaving stale guidance behind.
- Keep task context concise and durable; do not dump raw command output or disposable logs into `context.md`.
- Keep `context.md` under `20,000` bytes and `200` lines; while it stays manageable, keep deeper analysis there, and when it grows too large, split durable detail into `.zero-memory/context/<task_slug>/references/` and use the `compact_context.py` helper from `zero-context-persistence`.
- Before using `zero-context-compact` or `compact_context.py`, analyze the current `context.md` first. Extract reusable knowledge into `.zero-memory/daily/` and `zero-memory-curator` before or during the rewrite; when original detail is too large or too raw for memory, summarize the reusable part and record stable `rg`/`grep` search keywords that can locate the preserved source in `context.md`, `references/`, or snapshots.
- When compaction rewrites or moves durable context detail, evaluate whether any reusable knowledge would now be easy to miss from the shorter summary, including corrections, workflow rules, debugging methods, code-structure or call-path analysis, behavior notes, design decisions, or other durable technical insight; if so, log it to `.zero-memory/daily/learning.YYYY-MM-DD.md` and hand the new ID to `zero-memory-curator` in the same turn.
- When detail is split out, add a `## References` section to `context.md` that lists each reference file with a short description of what it contains.
- If a reference file preserves detail moved out of an older, larger `context.md`, say that clearly in the reference description so a restarted agent knows it contains the earlier detail.

## Zero Memory Workflow
- Force rule: use `zero-context-persistence` as the primary capture workflow plus `zero-memory-curator` as the default workflow reminder, log non-trivial reusable learnings into `.zero-memory/daily/`, and use `.zero-memory/memory/` for curated recall.
- Use the `zero-memory-curator` skill whenever prior experience or a blocker may matter.
- Treat this guidance as the default reminder mechanism instead of relying on the deprecated legacy skill.
- Log non-trivial reusable events to `.zero-memory/daily/learning.YYYY-MM-DD.md` with globally unique IDs in the format `DL-YYYYMMDD-HHMMSS.mmmZ-<random-suffix>`.
- For each entry, include summary, durable details, why the item is reusable, suggested memory targets, and provenance such as `Source Slug`, `Source Context`, `Source Sections`, `Related Files`, and optional `See Also`.
- Use `Pattern-Key` and `Recurrence-Count` when a pattern repeats, and update existing memory instead of duplicating noise.
- Force rule: when a user correction or agent self-diagnosis reveals a missed reusable workflow choice, missed recall, or missed memory-promotion step, the agent MUST NOT stop at `.zero-memory/daily/`; in the same turn it MUST use the `zero-memory-curator` skill to update an existing reachable memory or create a new reachable memory node and repair routing or workflow-doc surfaces when needed.
- Do not log trivial noise such as obvious typo fixes unless it is likely to recur or affect workflow quality.
- `.zero-memory/daily/` is the only active raw-learning write target; treat legacy raw-learning files as migration input only.
- Force rule for memory recall:
 - When the agent believes prior experience may matter for the current task, it MUST use the `zero-memory-curator` skill.
 - When the agent encounters a problem, failure, blocker, confusing behavior, or repeated debugging loop, it MUST also use the `zero-memory-curator` skill to check whether prior experience may help solve it.
 - First run the `load_memory_graph.py` helper from `zero-memory-curator` with `--root .zero-memory/memory --depth 0` to load description-first summaries from the init set; if the task already has a strong anchor, use `--start <memory-id>` instead of opening memory files directly.
 - Use returned `load_next` IDs to expand selectively; for example run the `load_memory_graph.py` helper from `zero-memory-curator` with `--root .zero-memory/memory --start workspace.agent.workflows --depth 1`, then follow a relevant child such as `memory.curator.workflow` by running the same helper with `--root .zero-memory/memory --start memory.curator.workflow --depth 0`.
 - Only after the script identifies a relevant memory may the agent read that package's full `MEMORY.md`, `references/`, or `examples/`.
 - Do not read all memory details up front, and do not skip the description-loader script and jump straight to full-file reads.

</INSTRUCTIONS>
<!-- END zero-memory AGENTS.md -->
