---
name: zero-memory-reflection
description: Analyze `.zero-memory/reflection/` advice notes, missed-recall cases, whole-graph abstraction opportunities, and approved graph refactor plans; use only when the user explicitly asks to optimize the memory system or approves the recommendation. This skill is opt-in only and must not be auto-used.
---

# Zero Memory Reflection

Use this opt-in skill when the user explicitly wants to improve the memory system.

This doc is organized into three workflows:

- Mode A: Local Reflection
- Mode B: Full-Graph Audit
- Apply Flow: Approved Graph Refactor

Do not auto-apply this skill.

- The agent may recommend it when repeated missed-recall reflections suggest system-level design debt.
- The skill may run only when the user explicitly requests the optimization or explicitly approves the recommendation.

## Script Path Convention

When this skill says to run a bundled helper, resolve it from the referenced skill's `scripts/` directory instead of hardcoding a workspace-specific skill path. In examples below, `${reflection_scripts}` means the resolved `scripts/` directory for the active `zero-memory-reflection` skill, and `${curator_scripts}` means the resolved `scripts/` directory for the active `zero-memory-curator` skill.

## Mode A: Local Reflection

Use this mode when the problem is centered on a known memory pair, a known reflection entry, or a local recall miss.

Typical triggers:

- a new memory should have matched an older active memory
- an existing memory was found late, or the user asks why it was not recalled earlier
- a reflection entry already exists and needs follow-up
- the issue looks like local wording, metadata, or routing debt around a known neighborhood

Workflow:

1. Start from `.zero-memory/reflection/` advice notes, daily reflection entries, and affected memory IDs, not from a blind full-corpus rewrite.
2. Load the memory graph description-first with `load_memory_graph.py`.
3. Query targeted neighbors with `query_memory_index.py` and only then read selected `MEMORY.md` details.
4. If `.zero-memory/observability/reports/latest/` exists, consult the hot-memory, routing-friction, stale-but-hot, and reflection-priority reports to understand whether the local miss is isolated or part of a broader repeated pattern. If that shared reduced view does not exist yet and the signal would help, generate it with `report_memory_observability.py`; default report reads aggregate all visible writer shards.
5. If structured lookup did not find a strong candidate, run `python3 "${curator_scripts}/shortlist_similar_memories.py" --root .zero-memory/memory --memory-id <new-memory-id>` or `--description "<new description>"` to get a suggestion-only shortlist of same-meaning memories.
6. Diagnose whether the miss came from metadata, wording, graph shape, `zero-memory-curator` guidance, skill descriptions, or tooling.
7. Apply the smallest refactor that materially improves future recall.
8. Revalidate the graph and record the optimization result in zero-memory.

If the reflection note has not been captured yet, scaffold it first with `python3 "${curator_scripts}/scaffold_missed_recall_reflection.py" --root .zero-memory/memory --daily-root .zero-memory/daily --reflection-root .zero-memory/reflection --new-memory-id <new-memory-id> --existing-memory-id <existing-memory-id> --discovery-source graph-traversal --trigger late-duplicate-discovery --miss-reason "<visible reason>" --improvement-advice "<specific recall-surface fix>" --write`, changing `--discovery-source`, `--trigger`, and the advice fields when the case came from semantic shortlist, validator output, manual review, or user correction.

If there is no new duplicate memory and the issue is that an already-existing memory was not recalled, scaffold with `--missed-memory-id <memory-id>` instead of the new/existing pair and capture the visible evidence that explains the miss.

## Mode B: Full-Graph Audit

Use this mode when the user explicitly wants whole-graph simplification, abstraction, or clustering across many memories.

Typical triggers:

- no current reflection entry exists, but the user wants conceptual cleanup
- multiple memories may share one deeper reusable rule
- the goal is synthesis across the graph rather than local duplicate repair

Workflow:

1. Run `python3 "${reflection_scripts}/audit_memory_graph.py" --root .zero-memory/memory`.
2. If the default audit returns no clusters but the user still wants exploratory review, rerun it once with a lower `--min-pair-score` such as `0.18` and treat that second pass as a candidate-discovery surface, not as an approval-ready simplification plan.
3. If `.zero-memory/observability/reports/latest/` exists, let those reports influence which clusters deserve review first, but do not treat telemetry as proof that two memories mean the same thing. If needed, regenerate the shared reduced view first; the default report scope is all visible writer shards, not only the current writer.
4. Review the suggested clusters, summary candidates, and child actions.
5. Pay attention to the audit outputs that drive later approval:
   - `cluster_id`
   - `existing_summary_id`
   - `proposed_abstract_memory`
   - `default_subsume_ids`
   - `recommended_parent_ids`
   - `apply_preview_command`
6. Keep memories active when they still carry independent operational value.
7. Use `candidate_subsume` only as an approval candidate at this stage.
8. By default the audit focuses on non-routing memories first; add `--include-routing` only when you explicitly want existing summary/routing nodes to participate.
9. Treat the audit as non-mutating even though the schema now supports subsumption. Actual writes belong to the Apply Flow.

## Apply Flow: Approved Graph Refactor

Use this flow only after a full-graph audit cluster is explicitly approved.

Workflow:

1. Save the audit output as JSON, for example: `python3 "${reflection_scripts}/audit_memory_graph.py" --root .zero-memory/memory --format json > <audit-plan.json>`.
2. Preview the approved cluster without writing: `python3 "${reflection_scripts}/apply_memory_graph_refactor.py" --root .zero-memory/memory --plan <audit-plan.json> --cluster-id <cluster-id>`.
3. Apply it explicitly with `python3 "${reflection_scripts}/apply_memory_graph_refactor.py" --root .zero-memory/memory --plan <audit-plan.json> --cluster-id <cluster-id> --write` or `--cluster-index <n>`. By default the structured apply journal goes under `.zero-memory/history/zero-memory-reflection/`; pass `--change-journal-path <path>` only when you need a custom location.
4. Treat `summary_reconciliation` output as mandatory follow-up when a reused summary anchor changes scope. If the apply step adds or removes active children, compare the summary's `## Description` and `## Details` against the new `load_next` set in the same pass; do not stop after frontmatter-only rewrites.
5. Let the apply step create or reuse the summary memory, redirect active parents safely, write any approved `subsumed` lifecycle changes, and persist a structured change journal outside the memory body by default under `.zero-memory/history/zero-memory-reflection/`.
6. Use `status: subsumed` plus reciprocal `subsumed_by` / `abstracts` only for memories that are absorbed into a better abstraction without being wrong.
7. Do not mix subsumption with supersession on the same node.

## Shared Investigation Rules

Use these rules across all three workflows:

1. Identify the smallest relevant trigger set first:
   - reflection entries
   - `.zero-memory/reflection/` advice notes
   - known memory IDs
   - nearby parents, children, and lateral neighbors
2. Load the current graph surface with `python3 "${curator_scripts}/load_memory_graph.py" --root .zero-memory/memory --depth 0`, then narrow with `--start <memory-id>` and `--include-details` only for selected targets.
3. Query structured lookup surfaces before broad semantic reading:
   - exact `Pattern-Key`
   - `query_memory_index.py --related-file ...`
   - `query_memory_index.py --related-symbol ...`
   - reverse-parent lookup through the index
4. Read only the relevant `.zero-memory/reflection/` advice notes, daily reflection entries, selected memories, and `skills/zero-memory-curator/**` guidance.
5. Treat stale selected memories as lower-confidence evidence rather than as an automatic blocker, and use `freshness_profile` to decide how much skepticism to apply:
   - `code-env` -> after 24 hours, use skeptically and proactively check only for high-risk or cheap-to-check cases
   - `workflow` -> after 7 days, use with some skepticism and spot-check only when central or cheap to verify
   - `conceptual` -> validate on suspicion instead of age alone
6. Classify the issue into one or more buckets:
  - discovery metadata gap
  - node description or boundary gap
  - graph layering or routing gap
  - workflow/doc/template gap
  - tooling/index gap
7. If observability reports exist, use them to prioritize which hot, stale, or high-friction memories deserve attention first, but keep semantic truth grounded in the actual memories and graph structure rather than in raw frequency alone. Prefer the tracked shared reduced view under `.zero-memory/observability/reports/latest/`, and remember that default report generation reads all visible writer shards.

## Shared Refactor Rules

- Prefer local fixes first: better `## Description`, better boundary wording, better `pattern_key`, and better lookup metadata.
- When wording is not enough, repair the graph: add an abstract parent, split an over-broad node, or strengthen `load_next`.
- Update both sides of a late duplicate when needed; do not leave the older node easy to miss and only clean up the newer node.
- Keep historical correction value, but do not preserve duplicate active nodes when one current rule is enough.
- If the reflection reveals a durable operating rule, update or create a curated memory for it.
- If the reflection reveals a recurring procedural workflow, update `zero-memory-curator` docs or create/refine a skill instead of burying the fix only in one `MEMORY.md`.
- For whole-graph work, keep the sequence explicit: analyze -> approve -> apply.
- When multiple low-value memories share one deeper essence, prefer a higher-level abstract memory instead of only pairwise dedupe.
- Do not misuse `superseded` for memories that are not wrong but are merely absorbed into a better abstraction; use `status: subsumed` with `subsumed_by` / `abstracts` for that case.
- When a refactor reuses an existing summary anchor and changes its active child scope, reconcile the summary prose in the same pass instead of assuming the old `## Description` and `## Details` still describe the broader graph shape.
- Treat the apply script's `summary_reconciliation` warnings as a semantic warning layer, not as optional noise. Either update the summary prose or explicitly justify why the added children are intentionally out of scope for that node's text.
- Keep historical backtracking outside the memory body by default: write a structured apply journal that records changed memory IDs, actions, reasons, and before/after routing or lifecycle state.

## Validation

### After Mode A

1. Run `python3 "${curator_scripts}/validate_memory_graph.py" --root .zero-memory/memory --repair`.
2. Re-run the targeted `load_memory_graph.py` or `query_memory_index.py` commands that previously missed the memory.
3. Confirm the improved route is now discoverable without a broad text search.
4. Call out any remaining warnings and why they are non-blocking.

### After Apply Flow

1. Re-run `audit_memory_graph.py` after any apply step to see whether the cluster became simpler.
2. Re-run `validate_memory_graph.py --repair`.
3. Review the apply script's `summary_reconciliation` output and update any reused summary prose before treating the refactor as complete.
4. Confirm that the simplification did not hide any independently useful operational memory.
5. Confirm that every `subsumed` memory now points at an active summary through `subsumed_by`, and that the summary records the reciprocal `abstracts` list.
6. Confirm that a structured apply journal was written outside the memory body, normally under `.zero-memory/history/zero-memory-reflection/` unless this task intentionally used `--change-journal-path`.

## Record The Outcome

- Append or update a reflection entry in `.zero-memory/daily/learning.YYYY-MM-DD.md`.
- Create or update the relevant `.zero-memory/reflection/` advice note when the optimization changes the diagnosis, replay check, or recommended memory/skill improvement.
- Update or create curated memory only when the reflection yields a durable rule.
- Refresh `last_updated_at` on any memory you edit or explicitly revalidate during reflection work.
- If an approved apply step changed graph shape, keep the per-apply change journal outside the memory body by default and summarize only the durable rule in daily learning or curated memory.
- Keep the resulting explanation concise enough that later agents can reuse it without replaying the full investigation.

## Read More

- For the deeper diagnostic matrix, audit heuristics, and apply guidance, read [reference.md](reference.md).
