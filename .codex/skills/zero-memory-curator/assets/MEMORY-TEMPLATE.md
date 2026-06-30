---
id: workflow.memory.kind.name
name: memory-kind-name
description: One-line summary for fast discovery.
tags:
  - area-tag
  - topic-tag
pattern_key: stable.pattern.key
component: agent
kind: best-practice
stage: design
scope: project
actionability: reference-only
layer: detailed
status: active
last_updated_at: 2026-04-04T11:36:25Z
freshness_profile: workflow
source_daily_learning_ids:
  - DL-YYYYMMDD-HHMMSS.mmmZ-randomsuffix
recurrence_count: 1
last_confirmed_at: 2026-04-02T10:15:00Z
recent_confirmation_ids:
  - DL-YYYYMMDD-HHMMSS.mmmZ-randomsuffix
supersedes:
  - workflow.previous.memory
abstracts:
  - workflow.absorbed.memory
# Or, on an absorbed child memory instead of the summary:
# subsumed_by: workflow.abstract.summary
load_next:
  - workflow.memory.kind.name.detail
related:
  - workflow.other.memory
related_files:
  - path/to/file
related_symbols:
  - symbol_name
---

# Memory Kind Name

## Description

Write 1-3 short paragraphs for cheap loading. This section should help the agent decide whether deeper detail is needed.

Make the description easy to find later:

- include the trigger terms a future recall query is likely to use
- say what this memory covers and the nearest boundary with similar memories
- mention when the reader should stay here versus follow `load_next`
- if this is an `init` or `abstract` node, summarize the branch categories it routes to instead of repeating each child's full technical content

## Details

Put the longer explanation here:

- decision rules
- trade-offs
- anti-patterns
- escalation or promotion guidance
- what makes this node different from nearby or previously confused memories
- which missing metadata or graph edge would most likely cause a recall miss

If this is an `init` or `abstract` routing node:

- keep this section focused on entry conditions, branch choice, and cross-child boundary guidance
- prefer loading the relevant `load_next` children for concrete technical specifics
- duplicate child details here only when the parent adds real synthesis that the children do not already provide

If `## Description` plus `## Details` exceeds 100 non-empty lines for an active memory, split the memory instead of keeping one oversized entrypoint. Keep this node as a concise summary or router, move one coherent subtopic into a new active child memory, add that child to `load_next`, update any previous parent routing that should now target the child, and preserve useful `related` links and provenance on both nodes.

## Correction

Use this section only when the current memory materially replaces an older memory.

- Replaces: `workflow.previous.memory`
- Earlier claim: ...
- Why it was wrong or incomplete: ...
- New evidence: ...
- Current rule: ...

## Source Extraction

Document how this memory was distilled from `.zero-memory/daily/*` entries.

- Canonical source IDs live in frontmatter `source_daily_learning_ids`; they should represent direct local provenance only
- Only restate IDs here when mapping a subset to a specific extracted fact
- Original files: `.zero-memory/daily/learning.YYYY-MM-DD.md`
- Extraction rule: describe which parts are treated as stable facts, which parts are only context, and which noise was intentionally dropped
- Fact list: write the normalized facts that future agents should rely on

Prefer extracting:

- verified root cause
- stable prevention rule
- durable workflow constraint
- evidence-backed commands, paths, or conventions

Avoid extracting:

- one-off conversational phrasing
- temporary logs with no lasting value
- speculative diagnosis that was never verified
- every repeated confirmation when a capped confirmation list plus counters would preserve the same signal more compactly

## Related

- Related files: `path/to/file`
- Related memory IDs:
  - `workflow.other.memory`

Use `related_files`, `related_symbols`, and nearby memory IDs to make future similar-node lookup cheaper.

## Lifecycle Notes

- `status: active` means default recall should include this node
- `status: superseded`, `subsumed`, `incorrect`, or `tombstone` means default recall should hide it unless inactive history is explicitly requested
- Refresh `last_updated_at` whenever this memory is materially edited or explicitly revalidated against the current code, workflow, or environment
- Use `freshness_profile` to decide how age should affect trust:
  - `code-env` -> after 24 hours, use as a low-confidence hypothesis and proactively check only for high-risk or cheap-to-check cases
  - `workflow` -> after 7 days, use with some skepticism and spot-check only when central or cheap to verify
  - `conceptual` -> validate on suspicion rather than on age alone
- Keep the main correction story on the active replacement node and leave only a redirect/tombstone on the old node when possible
- Use `superseded` for wrong or replaced knowledge, but use `subsumed` when the memory is still correct and is only being absorbed into a better active abstraction
- Pair `subsumed_by` on the child with `abstracts` on the active summary

## Examples

- Keep short examples here, or move larger examples into `examples/`.
