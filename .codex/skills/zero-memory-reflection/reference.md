# Zero Memory Reflection Reference

Use this reference when the main skill file is not enough and you need the deeper checklists behind each workflow.

## Mode A: Local Reflection Reference

Use this section when the work is centered on a known recall miss, a known `.zero-memory/reflection/` advice note, a known memory pair, or a local neighborhood that needs cleanup.

Start from the advice note's visible evidence boundary. If the note does not yet explain the miss from visible evidence, update it before changing memory or skill descriptions.

### Diagnostic Matrix

#### 1. Discovery Metadata Gap

Signals:

- `Pattern-Key` mismatch or missing reuse
- missing `Suggested Memory Targets`
- empty or weak `related_files`
- empty or weak `related_symbols`

Typical fixes:

- normalize or reuse the stronger `pattern_key`
- add missing lookup metadata to both the old and new nodes
- add the affected file or symbol to the reflection entry and curated memory
- add the affected file, symbol, route, or trigger term to the `.zero-memory/reflection/` advice note when it explains why recall missed

#### 2. Node Description Or Boundary Gap

Signals:

- the existing memory technically matches but its `## Description` does not expose the likely search terms
- nearby memories overlap semantically without clearly saying what each one covers
- the correct node exists but the new node looked clearer than the older one

Typical fixes:

- add likely trigger terms to `## Description`
- state the nearest boundary with similar memories
- explain when to stay on this node and when to follow `load_next`
- add a short comparison note in `## Details`

#### 3. Graph Layering Or Routing Gap

Signals:

- several sibling memories overlap without an abstract parent
- `related` is doing work that should be done by `load_next`
- one memory is overloaded and repeatedly spawns near-duplicate children
- the right memory is reachable only through an unintuitive route

Typical fixes:

- add a missing abstract parent
- split an over-broad node
- re-parent the node through stronger `load_next` edges
- keep `related` as lateral navigation only

#### 4. Workflow Guidance Gap

Signals:

- the author followed the existing `zero-memory-curator` workflow but still modeled the node poorly
- the template did not prompt for trigger terms, boundaries, or layer choice
- repeated reflections point to the same authoring mistake

Typical fixes:

- update `skills/zero-memory-curator/SKILL.md`
- update `references/workflow.md` or `references/taxonomy.md`
- update `assets/MEMORY-TEMPLATE.md`
- add a curated memory for the new durable rule

#### 5. Tooling Or Index Gap

Signals:

- the right metadata exists but targeted lookup still feels awkward
- reverse-parent or related-file lookup is too indirect
- validator feedback does not expose the unhealthy graph shape early enough

Typical fixes:

- improve query examples and docs
- refine generated index content
- improve validator warnings or repair behavior
- improve loader output for side-by-side candidate comparison

#### 6. Observability Signal Gap

Signals:

- a memory is frequently helpful but rarely selected
- a memory is repeatedly selected only after deep graph traversal
- stale memories are still used often without a clear refresh path
- repeated missed-recall reflections concentrate around the same node or cluster

Typical fixes:

- review generated observability reports before changing graph shape
- prefer the tracked shared reduced view under `.zero-memory/observability/reports/latest/`, and regenerate it from all visible writer shards when the latest view is missing or stale
- improve trigger terms, lookup metadata, or parent routing for hot memories
- refresh stale-but-hot workflow memories deliberately
- use hotness and missed-recall concentration to prioritize whole-graph audit review order

## Mode B: Full-Graph Audit Reference

Use this section when the user wants conceptual simplification across the graph, even if no current reflection entry exists yet.

Goal:

- detect clusters of memories that look different on the surface but likely encode one deeper reusable principle
- propose a higher-level abstract memory
- decide which child memories should stay active examples and which low-value children should become inactive `subsumed` nodes under the chosen abstraction

Primary command:

```bash
python3 skills/zero-memory-reflection/scripts/audit_memory_graph.py --root .zero-memory/memory
```

Useful flags:

- `--min-pair-score <float>` to tighten or loosen clustering
- `--min-cluster-size <int>` to ignore tiny clusters
- `--top-clusters <int>` to limit review size
- `--include-inactive` when historical nodes matter for the audit
- `--include-init` when you also want to review init-routing nodes
- `--include-routing` when you also want to review existing summary/routing nodes; by default the audit focuses on compressible non-routing memories first

Exploratory rerun rule:

- if the default threshold reports no clusters but the user still wants review candidates, run one lower-threshold pass such as `--min-pair-score 0.18`
- treat that lower-threshold output as exploratory shortlist material, not as a same-confidence substitute for the default audit
- only move from exploratory clusters toward apply after manual review confirms the overlap is conceptual rather than just token-level

Audit outputs worth reviewing before approval:

- `cluster_id`
- `existing_summary_id`
- `proposed_abstract_memory`
- `default_subsume_ids`
- `recommended_parent_ids`
- `apply_preview_command`

### Audit Heuristics

The audit should combine both semantic and structural signals:

- weighted token overlap in `description` and `details`
- overlapping description phrases
- text-sequence similarity
- `pattern_key`
- `related_files`
- `related_symbols`
- reverse parents and graph neighborhood
- `component`, `kind`, and `layer`
- optional observability reports to prioritize which candidate clusters deserve human review first
- default report generation should aggregate all visible writer shards rather than only the current writer

The goal is not to prove equality. The goal is to produce a reviewable shortlist of clusters worth human or deeper agent review.

Observability rule:

- usage telemetry may change which clusters are reviewed first
- it must not replace semantic or structural evidence when deciding whether memories should be grouped

### Cluster Outcomes

#### 1. Reuse Existing Summary

Choose this when one current memory already acts like the best abstraction anchor.

Typical action:

- keep the summary node active
- re-parent or simplify the children beneath it
- mark low-value absorbed children `subsumed` only when they add little unique operational value and no longer deserve active routing

#### 2. Create New Summary

Choose this when several similar memories exist but no current node cleanly captures their common essence.

Typical action:

- propose a new abstract memory
- attach the existing memories under it
- decide which children should remain active examples versus which should become `subsumed`

#### 3. Keep Separate

Choose this when the cluster is a false friend: similar wording, but not the same real rule.

Typical action:

- keep the nodes separate
- improve boundary wording so later audits do not re-cluster them

### Child Action Guidance

When the audit proposes child actions:

- `keep_as_summary`: this node is the best current abstraction anchor
- `keep_active_child`: this node still routes to sub-memories or carries distinct structure
- `keep_active_example`: this node still teaches a valuable concrete manifestation
- `candidate_subsume`: this node should become inactive under a better abstraction once the audit plan is explicitly approved and applied

Important:

- `candidate_subsume` is not the same as `superseded`
- use it only for "absorbed into a better abstraction", not for "was wrong"
- the applied lifecycle is `status: subsumed` on the child, with `subsumed_by` pointing at the active summary and the summary listing the child in `abstracts`

## Apply Flow Reference

Use this section only after a full-graph audit cluster is explicitly approved.

### Recommended Sequence

1. Save the audit JSON:

```bash
python3 skills/zero-memory-reflection/scripts/audit_memory_graph.py --root .zero-memory/memory --format json > <audit-plan.json>
```

2. Preview the approved cluster without writing:

```bash
python3 skills/zero-memory-reflection/scripts/apply_memory_graph_refactor.py --root .zero-memory/memory --plan <audit-plan.json> --cluster-id <cluster-id>
```

3. Apply it explicitly:

```bash
python3 skills/zero-memory-reflection/scripts/apply_memory_graph_refactor.py --root .zero-memory/memory --plan <audit-plan.json> --cluster-id <cluster-id> --write
```

4. Re-run validation and then re-audit or reload the affected neighborhood.
5. If the apply step reused an existing summary anchor and changed its child scope, treat prose reconciliation as part of the same change, not as an optional follow-up.
6. Persist a structured apply journal outside the memory body by default under `.zero-memory/history/zero-memory-reflection/`, or pass `--change-journal-path <path>` explicitly when this task needs a custom location.
7. When generated observability reports exist, capture the before-change usage context in the apply journal so later review can tell whether the refactor improved hot-memory routing or missed-recall behavior.

### Abstraction Lifecycle

Use these fields when a memory is absorbed into a better abstraction but is not wrong:

- child memory:
  - `status: subsumed`
  - `subsumed_by: <active-summary-id>`
- active summary memory:
  - `abstracts:`
    - `<subsumed-child-id>`

Rules:

- do not keep `subsumed` memories on active `load_next` paths
- do not mix `subsumed_by` with `superseded_by` on the same child
- do not use `superseded` when the old memory is still correct and is only being absorbed into a better abstraction
- prefer leaving the audit non-mutating and using `apply_memory_graph_refactor.py` as the explicit write step

### Apply Safety Rules

- prefer reusing an existing summary when it already expresses the common rule clearly
- create a new summary only when the current graph lacks a clean abstraction anchor
- do not subsume nodes that still route to active children
- keep active examples when they still carry distinct operational value
- let the apply step redirect parents safely instead of editing several nodes by hand first
- when a reused summary gains or loses active children, compare its prose with the new `load_next` set before you consider the refactor complete
- treat `summary_reconciliation` warnings as evidence that the graph changed faster than the summary text did
- record changed memory IDs, actions, reasons, and before/after graph state in a structured apply journal outside the memory body

### Summary Reconciliation Checklist

Use this checklist after `apply_memory_graph_refactor.py` previews or writes a reused summary:

1. Review `newly_attached_active_children` and `removed_children`.
2. Read the reused summary's current `## Description` and `## Details`.
3. Ask whether the prose still matches the node's real scope after the new `load_next` edges.
4. If the script reports `missing_scope_mentions`, either:
   - expand the prose to name the new child categories, or
   - tighten the summary wording so those children are clearly outside the prose contract
5. Remove stale claims that still describe children that were detached or subsumed.
6. Only close the reflection pass once the node's text and graph shape agree.

### Structured Apply Journal

The apply journal should stay outside the memory body by default and should record:

- trigger type and cluster ID
- changed memory IDs
- per-memory action such as `create-new-summary`, `update-existing-summary`, `rewrite-load-next`, or `mark-subsumed`
- why each memory changed
- before/after routing or lifecycle state
- `summary_reconciliation` output, including warnings and recommended actions
- validator status after the write

## Shared Refactor Checklist

Before making changes:

- identify the old memory, the new memory or missed memory, and the `.zero-memory/reflection/` advice note when working in Mode A
- identify the approved cluster, summary choice, and absorbed children when working in Mode B / Apply Flow
- write down the exact lookup path that failed or the exact graph shape that should improve
- if an affected memory is time-sensitive, use `freshness_profile` to decide how much skepticism to apply before you treat it as authoritative:
  - `code-env` -> after 24 hours, use skeptically and proactively check only for high-risk or cheap-to-check cases
  - `workflow` -> after 7 days, use with some skepticism and spot-check only when central or cheap to verify
  - `conceptual` -> validate on suspicion
- decide whether the smallest useful fix is local or structural

When editing memories:

- update the older node if it was too hard to find
- update the newer node if it captured a clearer wording worth keeping
- avoid leaving both nodes active when they express the same current rule
- preserve correction history when the older rule was materially wrong
- refresh `last_updated_at` on memories that were edited or explicitly revalidated during the reflection pass
- if a reused summary anchor changed graph scope, update its body text in the same pass instead of leaving the change journal as the only evidence of the broader meaning

When editing `zero-memory-curator` guidance:

- add only the guidance that future agents would likely miss without help
- prefer checklists and short examples over long prose
- keep the skill opt-in boundary explicit when a deeper reflection workflow is involved

## Exit Criteria

The optimization is complete when:

1. the missed memory becomes discoverable through the intended graph-first path
2. the affected nodes explain their boundaries more clearly
3. the graph still validates cleanly
4. the reflection result is captured in zero-memory, including an updated `.zero-memory/reflection/` advice note when the diagnosis or recommended fix changed
5. the skill did not silently turn a one-off fix into an unapproved system-wide rewrite
