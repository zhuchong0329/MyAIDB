# Memory Routing Workflow

Use this reference when the task needs the full operating procedure for classifying or promoting memory.

## Workflow

1. Read the new or changed entry in `.zero-memory/daily/learning.YYYY-MM-DD.md`.
2. Preserve the original daily-learning entry as raw history.
3. Infer missing metadata from the summary, details, provenance, and surrounding task context.
4. Search for an existing matching `Pattern-Key`.
5. If a match exists, decide whether the new entry confirms the active memory, refines it in place, or materially replaces it with a new active node.
6. If the pattern deserves promotion, create or update a memory package under `.zero-memory/memory/<memory-slug>/`.
7. If the entry came from a user correction or agent self-diagnosis about a missed reusable workflow, missed recall, or missed promotion, do not stop at the daily note; in the same turn make the durable rule reachable through an active memory node and update routing or workflow docs when that was the real gap.
8. In `MEMORY.md`, keep the summary lightweight but add a `Source Extraction` section that explains how facts were distilled from `.zero-memory/daily/*`; keep the canonical direct-local source ID list in frontmatter `source_daily_learning_ids` instead of repeating it verbatim in the body unless a subset-to-fact mapping matters, choose `freshness_profile` when the memory is time-sensitive, and refresh `last_updated_at` whenever the memory is created, materially edited, or explicitly revalidated.
9. If the node is `layer: init` or `layer: abstract`, make the body explain scope, entry conditions, boundary, and when to follow important `load_next` branches; do not copy the full technical content of every child into the parent unless the parent adds real cross-child synthesis.
10. If an active memory's `## Description` plus `## Details` would exceed 100 non-empty lines, split it into two graph-linked memories: keep the original node as a concise summary or router, move one coherent subtopic into a new active child, update the parent's `load_next`, update any previous parent routing that should now target the child, preserve useful `related` links, and keep provenance on both nodes.
11. When a new memory replaces an older one, put the correction narrative on the new active memory and leave only a lightweight inactive redirect or tombstone on the old memory.
12. Put optional deeper material in `references/` or `examples/` when the entrypoint would otherwise become too large.
13. Maintain the graph and lifecycle metadata:
   - keep `registry.yml` aligned and keep its canonical package paths workspace-relative rather than checkout-specific absolute paths
   - keep `init-memory-set.yml` intentionally small
   - add `load_next` edges for canonical active discovery
   - add `related` links for lateral navigation
   - keep `freshness_profile` aligned with drift risk: `code-env`, `workflow`, or `conceptual`
   - keep `last_updated_at` current on new, edited, or revalidated memories
   - keep `status`, `supersedes`, and `superseded_by` aligned when replacement occurs
   - keep `status`, `abstracts`, and `subsumed_by` aligned when approved abstraction absorbs a lower-value memory without declaring it wrong
   - prefer confirmation metadata such as `recurrence_count`, `last_confirmed_at`, and capped `recent_confirmation_ids` over endlessly appending repeated confirmations
14. Run `validate_memory_graph.py`; if it fails, repair safe metadata drift first, rerun validation, and only then decide whether anything blocking remains.
15. Decide whether the entry should stay as reference-only, become a memory package, become a rule candidate, or become a skill candidate.
16. When recalled memories materially affect the task, record the outcome through `record_memory_outcome.py`; when humans or later agents need visibility into hot memories or routing friction, generate reports through `report_memory_observability.py`.

## Deterministic Confirm / Refine / Replace Flow

Use this order when a new daily-learning entry may update older memory:

1. Candidate generation
   - exact `Pattern-Key` match first
   - explicit memory IDs from `Suggested Memory Targets` or known correction links
   - `query_memory_index.py --related-file ...`
   - `query_memory_index.py --related-symbol ...`
   - reverse-parent and graph-neighbor follow-up only after one strong candidate exists
   - if the structured signals still miss a likely same-meaning memory, run `python3 skills/zero-memory-curator/scripts/shortlist_similar_memories.py --root .zero-memory/memory --description "<new description>"` or `--memory-id <new-memory-id>` as a suggestion-only semantic fallback
   - when a candidate memory is selected and you only need a compact semantic edit surface, run `python3 skills/zero-memory-curator/scripts/load_memory_edit_surface.py --root .zero-memory/memory --memory-id <memory-id>` instead of opening the full `MEMORY.md`; narrow further with `--section` or `--frontmatter-key` as needed
2. Confirm existing memory
   - choose this when the active memory's rule is still correct and the new entry only adds another confirmation, stronger evidence, or another instance of the same pattern
   - update `recurrence_count`, `last_confirmed_at`, and capped `recent_confirmation_ids`
   - refresh `last_updated_at` if the confirmation required an explicit revalidation against current code, workflow, or environment
3. Refine existing memory in place
   - choose this when the active memory is still the right package and the new entry improves explanation, scope, examples, or precision without overturning the rule
   - keep the same memory ID and update the body, direct provenance, and `last_updated_at`
   - if the refined node is `init` or `abstract`, prefer adding better routing/boundary guidance over copying the detailed facts that already belong on the children
4. Replace with a new memory
   - choose this when the older memory is materially wrong, unsafe, or conceptually replaced by a better rule
   - create the new active memory, set its `last_updated_at`, add a `## Correction` section there, set `supersedes`, and mark the old memory `superseded` or `tombstone`
5. Ambiguous case
   - if multiple active candidates remain plausible after metadata-first lookup, do not guess; stop at the shortlist and require deeper semantic review or a human decision

## Recall Freshness Rule

Adjust trust only for the memories actually selected as relevant, not the whole memory set.

Use `freshness_profile` to decide the default posture:

- `code-env`: after 24 hours, treat as a low-confidence hypothesis for code logic, runtime behavior, commands, paths, or environment assumptions
- `workflow`: after 7 days, use with some skepticism for skills, procedures, and tool workflows
- `conceptual`: no time-based expiry; age alone should not lower trust much

Do not treat age alone as a hard blocker. By default, try to use the stale memory carefully and correct it if task execution or current evidence contradicts it.

Reserve proactive validation for:

- destructive, irreversible, or external actions
- production or high-blast-radius changes
- cases where one cheap check can avoid a costly mistake
- memories that are central to a large change or major design decision

If the memory still holds after a contradiction-driven check or a cheap spot-check, refresh `last_updated_at`. If it has drifted, update or supersede the memory before treating it as trusted guidance.

## Whole-Graph Audit Apply Flow

Use this flow only after the user explicitly approves a whole-graph abstraction change.

1. Save the audit output with `python3 skills/zero-memory-reflection/scripts/audit_memory_graph.py --root .zero-memory/memory --format json > <audit-plan.json>`.
2. Pick the approved cluster by `cluster_id` or cluster index.
3. Apply it explicitly with `python3 skills/zero-memory-reflection/scripts/apply_memory_graph_refactor.py --root .zero-memory/memory --plan <audit-plan.json> --cluster-id <cluster-id> --write`.
4. Let the apply step create or reuse the summary memory, redirect parents safely, and mark absorbed children `subsumed`.
5. Re-run the audit or targeted graph loads only after validation passes again.

## Late-Duplicate Reflection Loop

Use this loop when a new memory was created first and only later did review, validation, or a broader search reveal that a similar active memory already existed.

1. Record a reflection entry in `.zero-memory/daily/learning.YYYY-MM-DD.md`.
   - If the new/existing pair is already known, scaffold the entry with `python3 skills/zero-memory-curator/scripts/scaffold_missed_recall_reflection.py --root .zero-memory/memory --daily-root .zero-memory/daily --new-memory-id <new-memory-id> --existing-memory-id <existing-memory-id> --discovery-source graph-traversal --write`, changing `--discovery-source` when the pair came from semantic shortlist, validator output, or manual review instead of graph traversal.
2. Treat the incident as a recall or routing miss, not only as dedupe cleanup.
3. When the trigger is a user correction about a missed reusable workflow or missed promotion, treat that correction as mandatory same-turn memory work: daily learning alone is insufficient, and the durable rule must become reachable through curated memory before the turn ends.
4. Diagnose the miss across these buckets:
   - candidate-generation metadata gap: `Pattern-Key`, `Suggested Memory Targets`, `related_files`, `related_symbols`
   - semantic-surface gap: descriptions mean the same thing even though `pattern_key` and exact metadata do not collide
   - node-surface gap: weak `## Description`, weak boundary wording in `## Details`, missing nearby-memory references
   - graph-shape gap: missing abstract parent, wrong layer, missing `load_next`, or overuse of `related`
   - workflow gap: `zero-memory-curator` docs, examples, or templates did not make the better modeling choice obvious
5. Resolve the knowledge shape:
   - keep the existing memory and fold the new evidence into it
   - supersede the newer duplicate with the older active node
   - create a clearer abstract parent or split an over-broad node
6. Update the discovery surfaces that caused the miss so the next recall can succeed earlier.
7. Treat "noticed during normal graph traversal while trying to merge a new daily note" as a first-class discovery path, not as a special case outside the scripted workflow.
8. If generated observability reports exist, use them to see whether the same miss affects a hot or high-friction memory before deciding whether the fix should stay local.
9. If the same kind of miss repeats or appears to involve broader memory-graph design debt, recommend the opt-in `zero-memory-reflection` skill instead of trying to redesign the whole system implicitly during normal curation.

## Incremental Use With `zero-context-persistence`

When `zero-memory-curator` is called immediately after `zero-context-persistence` appends a new daily-learning entry:

1. Scope the read to the newly added entry only.
2. Use the new daily-learning ID as the primary lookup key.
3. Do not read the full `learning.YYYY-MM-DD.md` file unless the task is explicitly a maintenance or dedupe sweep.
4. Reuse existing `Pattern-Key` knowledge only when needed to update an existing memory package, recurrence count, graph relationship, or supersession link.

This keeps token usage low and avoids reprocessing historical content on every new learning.

## Decision Table

| Situation | Action |
|-----------|--------|
| New one-off incident | Classify and keep in daily learning |
| Repeat of known correct pattern | Reuse `Pattern-Key`, keep the active memory, and update confirmation metadata |
| New evidence corrects an existing memory but stays in the same conceptual package | Update the active memory in place and add a correction note if the old claim was materially wrong |
| New evidence replaces an existing memory with a safer or clearer rule | Create a new active memory, mark the old one superseded or tombstoned, and add a correction section on the new node |
| New memory was created, then a similar active memory was found later | Record a reflection entry, fix the discovery surfaces that caused the miss, then merge, re-parent, or supersede as appropriate |
| Approved whole-graph audit shows one better abstraction and low-value concrete variants | Create or reuse the active summary, mark absorbed variants `subsumed`, and keep reciprocal `abstracts` / `subsumed_by` metadata aligned |
| Active memory `Description` + `Details` exceeds 100 non-empty lines | Split the oversized memory into a concise parent/router plus a new active child, then update `load_next`, prior parent routing, `related`, registry, and provenance |
| Reusable but not yet workflow-critical | Promote to `.zero-memory/memory/<memory-slug>/` |
| Broad workflow lesson | Promote to `AGENTS.md` |
| Stable project convention | Promote to `MEMORY.md` |
| Reusable procedural knowledge | Extract or update a skill |

## How To Infer Metadata

### Component

Look at:

- affected files
- subsystem names
- user request scope
- nearby skills or workflows

### Kind

Infer from the core purpose:

- failure or breakage -> `incident`
- correction of misunderstanding -> `knowledge-gap`
- durable recommendation -> `best-practice`
- user-requested missing capability -> `feature-gap`
- repeated improvement idea -> `automation-opportunity`

### Stage

Infer from where the problem appears:

- before code search -> `clarification`
- during solution shaping -> `design`
- during code changes -> `implementation`
- while validating -> `testing`
- while inspecting diffs -> `review`
- during deploy or run -> `release` or `operations`

## Dedupe Rules

- Prefer one stable pattern with updated recurrence over many near-duplicates.
- If content differs but root cause is the same, keep one `Pattern-Key`.
- If the symptom is similar but the prevention rule is different, use different `Pattern-Key` values.
- If a detailed memory already exists but a broader grouping is now clear, create an abstract parent memory instead of duplicating the detailed content.
- If a duplicate is discovered only after a new memory was already created, capture why the earlier lookup failed and repair the recall surface instead of treating it as a pure cleanup chore.

## Promotion Thresholds

Promotion should usually happen when at least one is true:

- the same pattern recurs multiple times
- the memory prevents an expensive mistake
- the memory changes how the agent should operate in future tasks
- the knowledge benefits from lazy-loaded long-form guidance
- the knowledge should route to multiple detailed memories through `load_next`

## Memory Package Guidelines

Packages should be concise at the top and deeper only when needed.

Recommended entry format:

```markdown
---
id: workflow.agent.lazy-loading
name: agent-lazy-loading
description: Load memory summaries first and read details only on demand.
tags:
  - agent
  - memory
pattern_key: agent.zero-memory-curator.hybrid-taxonomy
status: active
last_updated_at: 2026-04-04T11:36:25Z
freshness_profile: workflow
layer: abstract
source_daily_learning_ids:
  - DL-20260401-173000.123Z-a1b2c3d4
recurrence_count: 1
recent_confirmation_ids:
  - DL-20260401-173000.123Z-a1b2c3d4
load_next:
  - workflow.agent.lazy-loading.examples
related:
  - workflow.task.context.persistence
related_files:
  - skills/zero-memory-curator/SKILL.md
---

# Agent Lazy Loading

## Description
Use light memory descriptions for discovery and load full details only on demand.

## Details
Store the decision rules, examples, and promotion guidance here or in `references/`.

## Source Extraction
Use frontmatter `source_daily_learning_ids` as the canonical direct-local ID list, then explain which parts were promoted as durable facts and which parts were intentionally left behind as task-specific noise.
```

Do not dump every original incident into `MEMORY.md`. Keep the entrypoint compact.

Do not let one active memory's `## Description` plus `## Details` grow beyond 100 non-empty lines. Split the memory into a concise parent or router plus a focused child memory, then update the graph relation so normal recall can still discover the deeper detail through `load_next`.

Do not copy every child node's concrete detail into an `init` or `abstract` parent. Use the parent to explain scope, branch choice, and boundary, then let `load_next` plus selective `--include-details` loading surface the concrete child facts.

Do not skip provenance. A memory package should explain how its stable facts were extracted from the original daily-learning records.

Do not duplicate the same full source ID list in both frontmatter and `## Source Extraction` unless the body is mapping a specific subset of IDs to specific facts.

Use `load_memory_graph.py` when only the description layer is needed.

Use `load_memory_edit_surface.py` when a selected memory needs semantic cleanup review but full-file reading would add unnecessary token cost.

## Extraction Rules

When extracting original facts from `.zero-memory/daily/*`:

1. Start from frontmatter `source_daily_learning_ids` and the original file path.
2. Pull out only verified facts from `Summary`, `Details`, `Why Reusable`, and later resolution notes.
3. Rewrite them into durable statements that can survive outside the original task.
4. Drop transient logs, negotiation text, and unresolved speculation.
5. When the new evidence corrects an older memory, record the correction rationale on the active memory instead of leaving the contradiction implicit.
6. Record the extraction rule in `MEMORY.md` so future agents know how this package was formed.

## Anti-Patterns

- Do not replace the raw inbox with a folder tree.
- Do not create orphan memories that are unreachable from the init set.
- Do not let `related` become the only path to a memory that should really be in `load_next`.
- Do not grow the init set until it becomes a flat dump of every memory.
- Do not promote one-off trivia into permanent rules.
- Do not keep superseded or incorrect memories on active `load_next` paths.
- Do not keep `subsumed` memories on active `load_next` paths either; route through the active summary instead.
- Do not use `source_daily_learning_ids` as an unbounded dump of every repeated confirmation or every child memory's provenance.

## Recommended Collaboration

Use the two skills in this order:

1. `zero-context-persistence` writes the reusable observation into `.zero-memory/daily/`.
2. `zero-memory-curator` classifies it and promotes reusable topics into `.zero-memory/memory/`.
3. Use `load_memory_graph.py` when the agent only needs discovery-level memory.
4. Promotion updates flow back into `AGENTS.md`, `MEMORY.md`, or a new skill when justified.
