# Memory Taxonomy

Use this reference when the task needs actual classification logic instead of only the high-level skill description.

## Design Goal

The memory model should behave like a skill:

- light discovery at the top level
- deeper details only when needed
- stable structure for repeated use
- graph expansion instead of flat scanning by default

Use a hybrid model:

- daily files for raw capture
- metadata for classification
- graph-backed memory packages for browsing
- links and tags for cross-cutting retrieval

## Source Of Truth

Keep these files as the canonical raw inbox:

- `.zero-memory/daily/learning.YYYY-MM-DD.md`

Do not move entries out of the inbox just because they were classified.

## Classification Dimensions

Each entry should keep its original fields and may add the following metadata.

### Component

What subsystem the memory belongs to.

Examples:

- `agent`
- `docs`
- `workflow`
- `tooling`
- `runtime`
- `application`
- `multi-component`

### Kind

What type of knowledge this is semantically.

Examples:

- `incident`
- `bug-pattern`
- `knowledge-gap`
- `best-practice`
- `reflection`
- `feature-gap`
- `automation-opportunity`

### Stage

Where in the work lifecycle the memory applies.

Examples:

- `clarification`
- `design`
- `implementation`
- `testing`
- `review`
- `release`
- `operations`

### Scope

How broadly the memory applies.

Examples:

- `task`
- `project`
- `cross-project`

### Actionability

What the agent should do with the memory.

Examples:

- `reference-only`
- `must-apply`
- `candidate-rule`
- `candidate-skill`
- `needs-human-decision`

### Layer

How the memory participates in graph traversal.

Examples:

- `init`
- `abstract`
- `detailed`
- `leaf`

### Lifecycle Status

Whether the memory is live by default or only preserved for history.

Examples:

- `active`
- `superseded`
- `subsumed`
- `incorrect`
- `tombstone`

### Freshness Metadata

Tracks when the memory was last materially updated or explicitly revalidated.

Examples:

- `last_updated_at`
- `freshness_profile`

If `freshness_profile` is absent, the loader may infer a best-effort default from existing metadata such as `component`, `stage`, and `related_files`, but explicit frontmatter is preferred for important memories.

### Graph Relationship Type

How one memory links to another.

Examples:

- `load_next` -> canonical expansion for BFS discovery
- `related` -> lateral navigation that does not replace `load_next`

### Lookup Metadata

Structured fields that make correction lookup cheap before any semantic comparison.

Examples:

- `pattern_key`
- `related_files`
- `related_symbols`
- `supersedes`
- `superseded_by`
- `abstracts`
- `subsumed_by`
- `recurrence_count`

## Mapping Rules

Use these defaults unless the entry clearly needs something else.

### By daily-learning type

- `incident` -> default `Kind: incident`
- `knowledge-gap` -> default `Kind: knowledge-gap`
- `best-practice` -> default `Kind: best-practice`
- `reflection` -> default `Kind: reflection`
- `feature-gap` -> default `Kind: feature-gap`

### By recurrence

- If the same pattern repeats, reuse the same `Pattern-Key`
- If recurrence reaches a stable threshold, raise `Actionability`
- Typical path:
  - first occurrence -> `reference-only`
  - repeated and useful -> `candidate-rule`
  - repeated and procedural -> `candidate-skill`

### By impact

- Local one-off fix -> `Scope: task`
- Reusable team knowledge -> `Scope: project`
- Portable operating pattern -> `Scope: cross-project`

### By graph role

- Broad routing memory -> `Layer: init` or `abstract`
- Reusable focused rule -> `Layer: detailed`
- Terminal, highly specific memory -> `Layer: leaf`
- `init` / `abstract` nodes should summarize scope, boundary, and navigation; `detailed` / `leaf` nodes should carry most concrete technical facts

## Memory Package Layout

Reusable memory should be promoted into packages under `.zero-memory/memory/`.

Recommended layout:

```text
.zero-memory/
  memory/
    init-memory-set.yml
    registry.yml
    <memory-slug>/
      MEMORY.md
      references/
      examples/
```

Recommended package naming:

- `agent-lazy-loading`
- `workflow-requirements-before-search`
- `testing-regression-patterns`

`MEMORY.md` is the package entrypoint. It should be cheap to inspect first and rich enough to support deeper loading later.

Recommended internal structure:

```markdown
---
id: workflow.requirements.before-search
name: workflow-requirements-before-search
description: Search code only after the requirements-clarification workflow decides the scope is clear.
tags:
  - workflow
  - requirements
pattern_key: workflow.requirements-before-search
status: active
last_updated_at: 2026-04-02T10:15:00Z
freshness_profile: workflow
layer: abstract
source_daily_learning_ids:
  - DL-20260401-173000.123Z-a1b2c3d4
recurrence_count: 1
recent_confirmation_ids:
  - DL-20260401-173000.123Z-a1b2c3d4
load_next:
  - workflow.requirements.before-search.examples
related:
  - workflow.agent.boundaries
related_files:
  - skills/zero-memory-curator/SKILL.md
---

# Workflow Requirements Before Search

## Description
Short summary for discovery and routing.

## Details
Longer explanation, decision rules, and trade-offs.
```

## Routing Heuristics

When deciding how a memory should be packaged:

1. Route by `Pattern-Key` first.
2. If the task may correct older knowledge, use exact memory IDs, `related_files`, and `related_symbols` to shortlist the likely existing package before doing any semantic contradiction check.
3. Use `Component` and `Stage` to choose package naming and tags.
4. Keep one package per reusable topic.
5. Use `Layer` to decide whether the memory is an entrypoint, an abstract grouping, or a terminal detail.
6. Use `Actionability` to decide whether the package should stay as memory, become a rule, or become a skill.
7. If a similar memory is discovered only after a new node was already created, classify that incident itself as `Kind: reflection` and capture which lookup surface failed before deciding how to reshape the graph.
8. If a selected memory is time-sensitive, use `freshness_profile` to decide whether it needs validation before you rely on it:
   - `code-env` -> after 24 hours, lower trust and proactively check only for high-risk or cheap-to-check cases
   - `workflow` -> after 7 days, lower trust slightly and spot-check only when central or cheap to verify
   - `conceptual` -> validate on suspicion instead of age alone

One package can still be linked from many places, but the package remains the main promoted unit.

## Reflection Heuristics

When a late duplicate or missed recall is being recorded, the reflection should usually capture:

- which memory IDs were involved
- which discovery signal failed first: `Pattern-Key`, memory-target hint, `related_files`, `related_symbols`, graph parentage, or description wording
- whether the real problem was node wording, node boundary, graph layering, or workflow guidance
- whether the durable outcome is a local memory fix, a graph refactor, or an opt-in skill-improvement candidate

Use these defaults:

- one-off local recall miss -> `Actionability: reference-only` or `must-apply`
- repeated recall misses across several memories -> `Actionability: candidate-skill`
- repeated misses caused by the same graph shape -> `Scope: project` and usually `Layer: detailed` or `abstract`

## Graph Rules

- Every curated memory must be reachable from the init set by following `load_next`.
- `related` is for lateral navigation only; do not rely on it as the only access path.
- Cycles in `load_next` are allowed, but they should be deliberate and visible in validator warnings.
- One detailed memory may have multiple abstract parents.
- `init` and `abstract` nodes should behave like routing summaries: they may name the important branches and cross-child boundaries, but they should not restate every child node's full detail unless the abstraction itself adds genuine synthesis.
- Default recall should traverse only `status: active` nodes.
- Default recall should treat `last_updated_at` plus `freshness_profile` as freshness metadata that adjusts trust, not as an automatic stop-the-world validation requirement.
- Parent links are derived by reverse lookup from `load_next`; do not hand-maintain duplicate `parents` metadata unless the schema later changes.
- Use `status: subsumed` only when a memory is absorbed into a better abstraction without being wrong; pair it with `subsumed_by` on the child and `abstracts` on the active summary.

## Pattern-Key Guidance

`Pattern-Key` should be stable, short, and semantic.

Good examples:

- `agent.skill.lazy-loading`
- `workflow.requirements-before-search`
- `testing.add-regression-test`

Avoid:

- timestamps
- task-specific IDs
- full sentences

## Promotion Rules

Promote to `AGENTS.md` when:

- the memory changes agent workflow
- the rule should be applied broadly

Promote to `MEMORY.md` when:

- the memory is a durable project fact or convention

Promote to a skill when:

- the pattern is reusable
- the steps are procedural
- deeper detail is helpful and the workflow is procedural

Promote to `.zero-memory/memory/<memory-slug>/` when:

- the pattern is reusable
- the knowledge is worth keeping but does not yet need a global workflow rule
- the LLM should be able to load a short description before reading the deeper detail

When replacing an existing memory:

- keep the new node `active`
- mark the old node `superseded`, `incorrect`, or `tombstone`
- put the main correction explanation on the new node
- keep `source_daily_learning_ids` focused on direct local evidence rather than rolling up every descendant or repeated confirmation

When abstracting over existing memories:

- keep the summary node `active`
- use `abstracts` on the summary to record absorbed children
- mark absorbed children `subsumed` with `subsumed_by`
- do not use `superseded` when the older child memory was still correct but just too low-value to stay on the active route
- keep the summary text focused on "what category this groups and when to follow which branch" rather than duplicating the absorbed or child node details line-by-line

## Minimal Metadata Example

```markdown
### Metadata
- Source: user_feedback
- Related Files: .zero-memory/memory/agent-lazy-loading/MEMORY.md
- Tags: memory, taxonomy, promotion
- Pattern-Key: agent.zero-memory-curator.hybrid-taxonomy
- Status: active
- Last Updated At: 2026-04-02T10:15:00Z
- Freshness Profile: workflow
- Component: agent
- Kind: best-practice
- Stage: design
- Scope: project
- Actionability: candidate-skill
- Layer: abstract
- Related Files: skills/zero-memory-curator/SKILL.md
```
