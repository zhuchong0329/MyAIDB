---
name: zero-memory-curator
description: Classify reusable daily learning into `.zero-memory/memory/` packages with description-first graph loading, layered expansion, BFS validation from a small init set, and missed-recall improvement advice under `.zero-memory/reflection/`.
---

# Zero Memory Curator

Use this skill to turn raw `.zero-memory/daily/` entries into structured memory packages under `.zero-memory/memory/` without losing provenance, and to capture missed-recall improvement advice under `.zero-memory/reflection/`.

Workspace-root rule: every `.zero-memory/...` path in this skill is relative to the current workspace root. If you are editing code in another repository from this workspace, keep the zero-memory data in the workspace, not that repository.

Use this skill proactively when the current task may benefit from prior project experience, recurring lessons, previously curated memory, or when the agent is trying to solve a problem and wants to check for similar historical cases.

## Quick Start

1. Use the current workspace root as the storage root for `.zero-memory/daily/` and `.zero-memory/memory/`.
2. Treat `.zero-memory/daily/learning.YYYY-MM-DD.md` as the raw-learning inbox.
3. Promote durable knowledge into graph-backed memory packages under `.zero-memory/memory/<memory-slug>/`.
4. Store lightweight discovery content in `.zero-memory/memory/<memory-slug>/MEMORY.md`.
5. Store optional deeper material in sibling folders such as `references/` and `examples/`.
6. When memory insert/update/delete/recall work shows that packaging a reusable workflow as a stable skill would materially help future feature work, extract or refresh that workflow skill under `.zero-memory/skills/<skill-name>/`; do not auto-move an active `skills/<skill-name>/` entry just because the workflow looks stable.
7. In each `MEMORY.md`, keep explicit graph and lifecycle metadata in frontmatter: `id`, `layer`, `status`, `last_updated_at`, optional `freshness_profile`, direct-local `source_daily_learning_ids`, `load_next`, `related`, and optional fields such as `recurrence_count`, `last_confirmed_at`, `recent_confirmation_ids`, `supersedes`, `superseded_by`, `abstracts`, `subsumed_by`, `related_files`, and `related_symbols`.
8. Use `load_memory_graph.py` to load description-first summaries from the init set or a chosen memory ID.
9. Use `validate_memory_graph.py` after creating or updating memories; if validation fails, repair what is safe to repair and rerun validation before treating the result as final.
10. Treat `.zero-memory/memory/index/` as generated lookup artifacts, not hand-edited source-of-truth files; use `query_memory_index.py` when you need reverse-parent, pattern-key, related-file, or related-symbol lookup without rescanning every `MEMORY.md`.
11. Treat `.zero-memory/observability/events/`, tracked shared reports under `.zero-memory/observability/reports/latest/`, and explicit audit snapshots under `.zero-memory/observability/reports/history/` as observability artifacts; do not hand-edit these or treat them as curated memory source.
12. Treat `.zero-memory/reflection/` as durable missed-recall improvement advice for `zero-memory-reflection`, not as a replacement for daily learning or curated memory updates.

## Default Model

- Keep raw daily capture append-first as the evidence log.
- Keep packaged memory graph-based instead of flat-only.
- Keep curated memory editable as current best knowledge rather than a second append-only diary.
- Keep discovery description-first.
- Keep full details lazily loaded.
- Keep the init memory set intentionally small.
- Keep direct local provenance on each memory node and compute descendant support on demand instead of rolling it up into every parent.
- Keep default recall focused on `status: active` memories unless inactive history is explicitly requested.
- Keep generated reverse and lookup indexes synchronized from live package metadata instead of hand-maintaining duplicate backlinks.
- Keep `init` and `abstract` nodes focused on routing, scope, and boundary guidance; keep most concrete technical facts on the relevant `load_next` children.
- Keep each active memory's `## Description` plus `## Details` to at most 100 non-empty lines; when it grows larger, split it into two graph-linked memories and update `load_next`, parent routing, `related`, `registry.yml`, and provenance metadata instead of keeping one oversized package.
- Keep selected-memory oversize warnings self-healing: when the current task selected, edited, or materially relied on an active memory and validation reports that memory is oversized, split it in the same curation pass when a clear semantic boundary exists.
- Keep `.zero-memory/skills/<skill-name>/` as an optional extracted-skill home chosen deliberately during memory work, not as an automatic retirement destination for active `skills/` entries.

Do not treat a folder tree as the only navigation system. The real discovery path is the curated graph formed by `load_next` and `related`.

## Package Layout

```text
.zero-memory/
  daily/
    learning.YYYY-MM-DD.md
  reflection/
    missed-recall/
      YYYY-MM-DD/
        <reflection-id>.md
  memory/
    init-memory-set.yml
    registry.yml
    <memory-slug>/
      MEMORY.md
      references/
      examples/
  skills/
    <skill-name>/
      SKILL.md
      references/
      scripts/
```

`MEMORY.md` should contain both:

- a short description for cheap loading
- deeper details for on-demand loading

The recommended split inside `MEMORY.md` is:

- frontmatter `description` for a one-line summary
- frontmatter `id` for stable graph references
- frontmatter `layer` for review/debug context
- frontmatter `status` for lifecycle state such as `active`, `superseded`, or `subsumed`
- frontmatter `last_updated_at` for freshness-aware recall and stale-memory revalidation
- frontmatter optional `freshness_profile` to control how stale selected memories should affect trust:
  - `code-env` -> after 24 hours, use as a low-confidence hypothesis and proactively check only for high-risk or cheap-to-check cases
  - `workflow` -> after 7 days, use with some skepticism and spot-check only when the memory is central or cheap to verify
  - `conceptual` -> age alone should not lower trust much; validate mainly on contradiction or unusually high stakes
  - if omitted, the loader infers a best-effort default from existing metadata
- frontmatter `source_daily_learning_ids` for direct local provenance IDs only
- frontmatter confirmation metadata such as `recurrence_count`, `last_confirmed_at`, and capped `recent_confirmation_ids`
- frontmatter supersession metadata such as `supersedes` and `superseded_by`
- frontmatter `load_next` for canonical expansion
- frontmatter `related` for lateral navigation
- frontmatter optional lookup keys such as `related_files` and `related_symbols`
- `## Description` for a compact explanation
- `## Details` for the longer guidance
- `## Correction` when this memory replaces an older one
- `## Source Extraction` for original-file provenance, extraction rules, and normalized facts without restating the same full ID list from frontmatter unless a subset-to-fact mapping matters

For `layer: init` or `layer: abstract` nodes, keep the body focused on:

- what category the node covers
- when the reader should start here
- when to follow each important `load_next` branch
- boundary or synthesis guidance that the children do not already repeat

Do not copy the full technical content of every child memory into the parent unless the parent is adding a real cross-child synthesis that would otherwise be lost.

Use frontmatter as the canonical machine-readable source for provenance, lifecycle, and lookup metadata. The body should add extraction context, correction rationale, and durable facts instead of mirroring the same metadata verbatim.

## When To Read More

- For the classification dimensions and routing rules, read `references/taxonomy.md`.
- For the end-to-end operating workflow, read `references/workflow.md`.
- For a starter package template, read `assets/MEMORY-TEMPLATE.md`.

## Script Path Convention

When this skill says to run a bundled helper, resolve it from this skill's own `scripts/` directory instead of hardcoding a workspace-specific skill path. Before executing a shell example, either set the script-directory variables or substitute the resolved directories directly. In examples below, `${curator_scripts}` means the resolved `scripts/` directory for the active `zero-memory-curator` skill. If an approved step uses `zero-memory-reflection`, `${reflection_scripts}` means that skill's resolved `scripts/` directory.

## Recall Rule

When prior experience may matter:

1. Load description-first summaries by running `python3 "${curator_scripts}/load_memory_graph.py" --root .zero-memory/memory --depth 0` before reading any full `MEMORY.md` file.
2. Start from the init set by default, or from a chosen memory ID when the task already has a strong anchor. Example: `python3 "${curator_scripts}/load_memory_graph.py" --root .zero-memory/memory --start workspace.agent.workflows --depth 0`
3. Expand selectively through `load_next`. Example: run `python3 "${curator_scripts}/load_memory_graph.py" --root .zero-memory/memory --start workspace.agent.workflows --depth 1`, note the returned child IDs such as `memory.curator.workflow`, then continue with `python3 "${curator_scripts}/load_memory_graph.py" --root .zero-memory/memory --start memory.curator.workflow --depth 0` before deciding whether to open the full package files.
4. If the selected memory is an `init` or `abstract` routing node, treat it as branch-selection guidance first. Expand its `load_next` children and read only the relevant child details instead of expecting the parent to duplicate every branch's concrete facts. Before any fallback `rg` search, web lookup, or ad hoc external probing, inspect at least one plausible child, or all plausible children whose descriptions overlap the task terms; do not stop at the router itself.
5. If the selected memories look relevant and you need their `## Details` without opening each full `MEMORY.md`, rerun the same targeted command with `--include-details`. Example: `python3 "${curator_scripts}/load_memory_graph.py" --root .zero-memory/memory --start memory.curator.workflow --depth 0 --include-details`
6. If you need a low-token edit surface for a selected memory before making semantic body edits, run `python3 "${curator_scripts}/load_memory_edit_surface.py" --root .zero-memory/memory --memory-id <memory-id>`. Narrow further with repeatable `--section <title>` or `--frontmatter-key <key>` when you only need part of the edit surface.
7. If you need direct provenance such as `source_daily_learning_ids` for audits, curation, or source tracing, rerun the same targeted command with `--include-provenance`. Example: `python3 "${curator_scripts}/load_memory_graph.py" --root .zero-memory/memory --start memory.curator.workflow --depth 0 --include-provenance`
8. If you need to inspect superseded, incorrect, or tombstoned history, rerun the same targeted command with `--include-inactive`.
9. If you need rolled-up descendant support after a relevant memory has already been selected, rerun the same targeted command with `--include-derived-provenance`.
10. You may combine these flags when the same selected set needs deeper content, lifecycle history, or provenance context.
11. Read deeper `references/`, `examples/`, or full `MEMORY.md` files only for the selected memories after this targeted graph load still leaves unanswered questions.
12. Treat freshness as selection-based and profile-based, not as a full-corpus validation loop. Only adjust trust for the memories actually selected as relevant.
13. Use `freshness_profile` to decide how much skepticism to apply:
   - `code-env`: after 24 hours, treat the memory as a low-confidence hypothesis; proactively check only before destructive, external, or high-risk use, or when the check is cheap
   - `workflow`: after 7 days, use with some skepticism; spot-check only when the memory is central to the task, externally visible, or cheap to verify
   - `conceptual`: do not force time-based validation; use normally and validate mainly when the current task suggests drift, contradiction, or unusually high stakes
14. If task execution or a spot-check confirms the memory is still current, refresh `last_updated_at`; if current evidence contradicts it, update or supersede the memory before treating it as trusted guidance.
15. When a selected memory routes to an existing stable workflow skill under `.zero-memory/skills/<skill-name>/`, open that stored workflow doc only after the graph step identifies it as relevant; do not scan the whole `.zero-memory/skills/` tree by default.
16. If recall or curation makes it clear that future reuse would benefit from extracting or refreshing a stable workflow skill and none exists yet or the current one is stale, create or update `.zero-memory/skills/<skill-name>/` intentionally and then wire it through curated memory; do not auto-move an active `skills/<skill-name>/` entry unless the user explicitly asks for that migration.
17. If graph loading still does not surface a useful memory, use a narrow fallback `rg` search over `.zero-memory/memory/` and, if needed, `.zero-memory/daily/` with concrete terms such as an error code, symbol name, subsystem name, or `Pattern-Key` fragment.
18. When recalled memory materially affects the task, record which memories were selected, helpful, stale, false-positive, or missed with `python3 "${curator_scripts}/record_memory_outcome.py" --root .zero-memory/memory ...`.
19. When humans or later agents need recall telemetry, generate reports with `python3 "${curator_scripts}/report_memory_observability.py" --root .zero-memory/memory`; default reads aggregate all visible writer shards. Use `--write` or `--write-latest` to refresh the tracked shared latest view under `.zero-memory/observability/reports/latest/`, keep that shared latest view on the default `writer_scope=all`, and use `--write-history` only when an explicit audit snapshot under `.zero-memory/observability/reports/history/YYYY-MM-DD/` is intended.

Do not load all memory details by default.
Do not default to `--include-details`, `--include-provenance`, `--include-inactive`, or `--include-derived-provenance`; use them as targeted escalation flags after the description-first pass identifies a relevant memory.
Do not skip the description-loader script and jump straight to full-file reads; the script output must choose the memories that deserve deeper reading.
Do not replace graph loading with broad text scanning; the fallback `rg` search is only a rescue path when the normal graph-based recall path does not find a useful memory.

Use this same flow when:

- a command fails unexpectedly
- debugging starts to loop
- the agent is blocked on an unfamiliar issue
- a similar bug, workflow problem, or environment issue may already have been seen before

## Curation Rule

When curating new information:

1. Read only the new daily-learning entry or explicitly selected raw entries.
2. Reuse an existing `Pattern-Key` when the durable pattern already exists.
3. Decide whether the new entry should:
   - confirm an existing active memory
   - refine an existing active memory in place
   - create a replacement memory that supersedes an older one
   - split an oversized active memory into two graph-linked memories when the combined `## Description` plus `## Details` would exceed 100 non-empty lines
4. Create or update the right memory package under `.zero-memory/memory/<memory-slug>/`.
5. If the trigger was a user correction or agent self-diagnosis about a missed reusable workflow, missed recall, or missed promotion, treat the daily note as insufficient by itself: before ending the turn, make sure the durable rule is reachable through an existing active memory or a newly created reachable memory node, and update routing or workflow docs if the miss came from guidance rather than only one local node.
6. Treat an oversized-memory warning as in-scope curation work without waiting for a separate user request when all of these are true:
   - the warning names a memory that the current task selected, edited, or materially relied on
   - the oversized memory is part of the current task's subject, not merely an unrelated validator warning
   - a coherent subtopic can be moved into a child memory without losing the parent's routing value
   - the split can preserve provenance, parent `load_next`, useful `related` links, `registry.yml`, and validation health
7. Do not split mechanically:
   - if the oversized memory is unrelated to the current task, call it out as a non-blocking follow-up
   - if the semantic boundary is unclear, leave the warning visible and create or update a daily/reflection note instead of guessing
   - if the cleanup requires whole-graph abstraction across many memories, recommend `zero-memory-reflection` and wait for explicit approval
8. Maintain the graph and lifecycle metadata:
   - keep `registry.yml` aligned and store canonical package paths there as workspace-relative paths such as `.zero-memory/memory/<slug>/MEMORY.md`, not checkout-specific absolute paths
   - keep `init-memory-set.yml` intentionally small
   - connect each non-init memory to at least one reachable parent via `load_next`
   - keep `load_next` focused on active expansion paths
   - use `related` only for lateral navigation, not as the only discovery path
   - for `init` or `abstract` parents, keep `## Description` and `## Details` focused on scope, boundary, and navigation; keep most concrete facts on the relevant children
   - choose `freshness_profile` to match drift risk when the memory is time-sensitive
   - set or refresh `last_updated_at` on any new, edited, or explicitly revalidated memory
   - when replacing an older memory, mark the older one inactive and keep the correction narrative on the new active node
   - when an approved higher-level abstraction absorbs low-value memories that are not wrong, mark the absorbed nodes `subsumed`, point them at the active summary with `subsumed_by`, and record the reciprocal `abstracts` list on the summary
   - when splitting an oversized memory, keep the original node as the best summary or router, move one coherent subtopic into a new active child, add the child to the parent's `load_next`, preserve lateral `related` links where useful, and update any previous parent that should now route to the child directly
   - when memory insert/update/delete/recall work shows a reusable workflow would benefit from a stable skill surface, extract or refresh `.zero-memory/skills/<skill-name>/` intentionally and expose it through memory `related_files` plus routing details; do not auto-move an active `skills/` copy unless that migration is explicitly requested
9. Run `validate_memory_graph.py`.
10. If validation fails, attempt safe repair first, rerun validation, and only proceed automatically when blocking errors are gone.
11. If warnings remain, call them out explicitly and explain why they are non-blocking.
12. If the curation pass depended on recalled memories in a way that would help future optimization, record the recall outcome through observability instead of encoding volatile usage counters into `MEMORY.md`.

Use this decision order so the choice is deterministic:

1. Gather active candidate memories in this order:
   - exact `Pattern-Key` match
   - explicit memory IDs from `Suggested Memory Targets` or known correction links
   - `query_memory_index.py --related-file ...`
   - `query_memory_index.py --related-symbol ...`
   - graph neighbors of the strongest candidate
2. If no active candidate remains after this lookup, but the new description still looks semantically close to known knowledge, run `python3 "${curator_scripts}/shortlist_similar_memories.py" --root .zero-memory/memory --description "<new description>"` or `--memory-id <new-memory-id>` as a suggestion-only fallback before creating or finalizing a new memory.
3. If no active candidate remains after the structured lookup plus semantic shortlist fallback, create a new memory.
4. If one active candidate clearly expresses the same current rule and the new daily entry only adds another confirmation, keep the same memory and update confirmation metadata.
5. If one active candidate is still the right conceptual package but the new entry adds a better explanation, broader scope, or a non-breaking refinement, update that memory in place.
6. If the strongest active candidate is materially wrong, risky, or replaced by a new safer rule, create a new active memory, set `supersedes`, update the old memory to `superseded` or `tombstone`, and remove the old node from active `load_next` expansion paths.
7. If multiple active candidates remain plausible after the semantic shortlist, stop at candidate generation and escalate for human or deeper semantic review instead of guessing.

## Reflection Rule For Missed Recall

When a new memory is created and a similar active memory is discovered later, when an existing memory is found only after it should already have been recalled, or when the user asks why an existing memory was not recalled, treat that event as a recall or routing miss instead of only a duplicate-cleanup task.

1. Do not silently delete, merge, supersede, or move on without recording why the miss happened.
2. Analyze the current visible evidence before explaining the miss. Use only evidence visible in the turn, such as loaded memory descriptions, graph routes, lookup terms, candidate lists, generated observability reports, script output, or the user's correction. Do not invent hidden recall attempts, hidden corpus state, or unstated user intent.
3. If the new/existing memory pair is already known, scaffold the reflection with `python3 "${curator_scripts}/scaffold_missed_recall_reflection.py" --root .zero-memory/memory --daily-root .zero-memory/daily --reflection-root .zero-memory/reflection --new-memory-id <new-memory-id> --existing-memory-id <existing-memory-id> --discovery-source graph-traversal --trigger late-duplicate-discovery --miss-reason "<visible reason>" --improvement-advice "<specific recall-surface fix>" --write`, adjusting `--discovery-source`, `--trigger`, `--miss-reason`, and `--improvement-advice` to match the visible evidence.
4. If there is no new duplicate memory and the miss is about an already-existing memory, scaffold it with `python3 "${curator_scripts}/scaffold_missed_recall_reflection.py" --root .zero-memory/memory --daily-root .zero-memory/daily --reflection-root .zero-memory/reflection --missed-memory-id <memory-id> --discovery-source user-correction --trigger user-asked-why-not-recalled --visible-evidence "<what was visible>" --miss-reason "<visible reason>" --improvement-advice "<specific recall-surface fix>" --write`.
5. Write or update the dedicated missed-recall advice under `.zero-memory/reflection/missed-recall/YYYY-MM-DD/`. That note is the durable input for `zero-memory-reflection`; it must include the trigger, affected memory IDs, visible evidence boundary, suspected miss reasons, concrete improvement advice, and replay or validation checks.
6. Append a reflection entry to `.zero-memory/daily/learning.YYYY-MM-DD.md` unless the same miss is already being captured in the current maintenance pass.
7. Do not finish with a daily note or reflection note alone when the correction is reusable. In the same turn, update an existing reachable memory or create a new reachable memory node, and strengthen the routing or workflow-doc surfaces that made the correction easy to miss.
8. Check why the earlier lookup missed the existing memory:
   - missing or inconsistent `Pattern-Key`
   - missing `Suggested Memory Targets`
   - missing `related_files` or `related_symbols`
   - likely recall or user-correction terms missing from `## Description`
   - weak `## Description` wording that does not expose likely recall terms
   - missing boundary guidance in `## Details`
   - missing `load_next` or `related` edges
   - wrong layer split, such as a missing abstract parent or an over-broad node
   - `zero-memory-curator` docs or template guidance that did not make the better description or layer choice obvious
   - tooling or index output that hid the likely candidate even though useful metadata existed
9. Update the affected memories so the next recall is cheaper:
   - make `## Description` include trigger terms and the distinction from nearby memories
   - make `## Details` explain boundary rules and when to follow `load_next`
   - align `pattern_key`, `related_files`, `related_symbols`, `load_next`, and `related`
   - merge, refine, supersede, or re-parent the nodes when the graph shape is the real problem
10. If raw evidence is too detailed for a concise note, summarize the useful lesson and record search keywords or memory IDs that can recover the original visible source with `rg` or graph lookup.
11. If the structured candidate lookup missed because two descriptions mean the same thing without sharing a `pattern_key`, run `python3 "${curator_scripts}/shortlist_similar_memories.py" --root .zero-memory/memory --memory-id <new-memory-id>` to shortlist same-meaning candidates before choosing one for reflection scaffolding, or go straight to the scaffold command if the agent already noticed the similar memory during normal graph traversal.
12. If the user explicitly approves a whole-graph simplification, use `zero-memory-reflection` audit output plus `python3 "${reflection_scripts}/apply_memory_graph_refactor.py" --root .zero-memory/memory --plan <audit-plan.json> --cluster-id <cluster-id> --write` to create or reuse the higher-level summary and write any resulting `subsumed` lifecycle updates.
13. If generated observability reports exist under `.zero-memory/observability/reports/latest/`, use them to see whether the miss is isolated or part of a hotter recurring routing problem before deciding how broad the fix should be. If they do not exist and the signal would help, generate them; the report reader aggregates all visible writer shards by default.
14. If the miss points to broader design debt in `zero-memory-curator`, the memory graph, the lookup indexes, or skill descriptions, advise the user that the opt-in `zero-memory-reflection` skill may help. Do not invoke it automatically; use it only when the user explicitly asks or approves the optimization.

## Output Expectations

When using this skill:

- Prefer updating metadata over rewriting the whole entry.
- Prefer dedupe by `Pattern-Key` over creating near-duplicate entries.
- Prefer one package per reusable topic over many generated indexes.
- Record promotion targets explicitly when an entry becomes a rule or skill.
- Load package descriptions first and read deeper files only when needed.
- Preserve provenance from daily learning into curated memory.
- Prefer direct local provenance IDs in frontmatter over repeating the same ID list in `## Source Extraction`.
- Prefer confirmation metadata over unbounded frontmatter growth when a memory is repeatedly re-confirmed.
- Prefer splitting active memories whose `## Description` plus `## Details` exceed 100 non-empty lines; keep the parent concise and route deeper detail through a new `load_next` child instead of making one large entrypoint.
- Prefer splitting an oversized selected or materially used memory during the current curation pass when the split is semantically clear; do not leave it as a warning merely because the user did not separately ask for cleanup.
- Prefer leaving unrelated oversized-memory warnings as explicit follow-up instead of folding unrelated graph maintenance into the current task.
- Prefer `freshness_profile` as a cheap trust-adjustment hint instead of turning stale memories into hard validation gates.
- Prefer refreshing `last_updated_at` whenever a memory is materially edited or explicitly revalidated against current code or environment.
- Prefer the replacement node to explain what changed and why; keep superseded nodes lightweight and inactive by default.
- Keep every curated memory reachable from the init set through `load_next`.
- Prefer repairing discovery surfaces on both the old and new nodes when a late duplicate reveals a recall miss.
- Prefer the semantic shortlist helper only as a suggestion-only fallback after structured lookup, not as an auto-merge mechanism.
- Prefer `.zero-memory/reflection/` missed-recall advice notes whenever an existing memory was found late, the user asks why it was not recalled, or a duplicate was created before discovering the older memory.
- Prefer visible-evidence reasoning in reflection advice; do not claim causes that were not observable from loaded memory surfaces, lookup output, observability reports, script output, or user correction text.
- Prefer `init` and `abstract` parents that summarize scope, boundary, and routing; keep child-level technical specifics on the selected `load_next` nodes unless the parent adds real cross-child synthesis.
- Prefer `related_files` that point to the concrete helper skill or script an agent should open next, not only to a higher-level wrapper memory or umbrella skill.
- Prefer `load_memory_edit_surface.py` over opening a full `MEMORY.md` when semantic cleanup only needs compact frontmatter plus `## Description` / `## Details`.
- Prefer `.zero-memory/skills/<skill-name>/` as an optional extracted-skill home when memory work shows a reusable workflow deserves a stable skill surface.
- Prefer append-only journals under `.zero-memory/observability/events/` plus the tracked shared reduced view under `.zero-memory/observability/reports/latest/` for usage analysis instead of storing volatile counters in curated memory frontmatter or body text.

## Related Skills

- `zero-context-persistence` should hand new reusable daily-learning IDs directly to this skill.
- `zero-memory-reflection` can analyze `.zero-memory/reflection/` advice notes, repeated recall misses, or duplicate-creation reflections, but it is opt-in only and must not be auto-invoked.
- `zero-memory-reflection` can also run an opt-in whole-graph audit when the user explicitly wants higher-level abstraction or graph simplification across many memories.
