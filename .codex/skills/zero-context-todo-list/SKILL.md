---
name: zero-context-todo-list
description: Capture user-requested todo items into the active task context by creating or updating `references/todo-list.md` and linking it from the current `context.md`. Use when the user asks to create, add to, reorganize, reprioritize, or review a todo list, task list, backlog, or action-item list for the current context. This skill treats the todo list as user-controlled planning only, never as permission to execute listed work automatically, and adds restart-safe detail for investigation-style items when that detail is already known.
---

# Zero Context Todo List

Use this skill to maintain a durable todo list inside the active task context.

The todo list is a context reference file, not an execution queue.

## Hard Rules

- The todo list is **user-controlled planning only**.
- Adding an item to the list does **not** authorize the agent to execute it.
- The agent may create, add, remove, regroup, reprioritize, or rewrite todo items **only when the user explicitly asks** for that list-management action.
- The agent may execute a listed item **only after a separate explicit user request** to do that work.
- Do not silently start work just because the todo list contains actionable items.
- Do not silently mark items `in_progress`, `done`, or `cancelled` unless the user explicitly asks for that status change or the current request clearly includes it.
- Do not invent scope. Normalize the user's wording into concise tasks, but stay grounded in the user's actual request.
- Do not invent diagnostic detail. Add richer context only when it is directly provided by the user or already established in the active context or related reference files.

## Resolve The Active Context

1. Read `.zero-memory/tmp/current-context.txt`.
2. If it contains a non-empty path, use that as the active `context.md`.
3. If the file is missing or empty, use `.zero-memory/context/default/context.md` as the active `context.md`, create `.zero-memory/tmp/` if needed, and write that path to `.zero-memory/tmp/current-context.txt`.
4. If the target `context.md` does not exist, create it with minimal YAML frontmatter:
   - `name: default`
   - `description: Default zero-memory task context.`
5. Do not choose a new task-specific context silently. Use another context only when the user explicitly asks for it or the current workflow explicitly requires it.

Once the active context is known:

- Treat the parent directory of `context.md` as the task context directory.
- Use `<context_dir>/references/todo-list.md` as the todo-list file.
- If `references/` does not exist yet, create it.

## File Ownership And Source Of Truth

- The durable markdown file in the active context is the source of truth.
- Do not use only transient task-tracking state as a substitute for the file.
- Keep the list restart-safe, concise, and easy to edit later.

## When The User Asks To Create Or Add Items

1. Read the user's message carefully.
2. Split compound requests into distinct todo items when that improves clarity.
3. Preserve important constraints:
   - dependencies
   - ordering hints
   - blocked conditions
   - scope limits
   - explicit "do not do X" instructions
4. When the item is an investigation, debugging, regression, reproduction, or root-cause task, capture restart-safe problem detail when available. Prefer short bullet lines under the item such as:
   - `Current evidence`
   - `Reproduction target`
   - `Related files`, `Related tests`, or `Related draft testcase`
   - `Success criteria`
5. Only include detail that is directly grounded in the user's request or in current active-context notes you already verified. Do not add speculative causes or made-up reproduction steps.
6. Default newly captured items to `pending`.
7. If the user input is too ambiguous to turn into stable tasks, ask a clarification question instead of guessing.

## When The User Asks To Reorganize The List

Allowed only when the user explicitly asks.

Examples:

- reorder by priority
- group by topic
- merge duplicates
- split a large item into smaller ones
- mark user-confirmed items as `done` or `cancelled`

When reorganizing:

- preserve the original meaning
- keep stable item IDs when practical
- do not treat reordering as permission to execute anything

## Todo File Template

Create or maintain `references/todo-list.md` with this structure:

```markdown
# Todo List

## Policy
- This file is a user-controlled planning artifact for the current context.
- Adding an item here does not authorize the agent to execute it.
- The agent may update this list only when the user explicitly asks to create, add, remove, reorganize, reprioritize, or revise todo items.
- The agent may execute a listed item only after a separate explicit user request for that work.

## Metadata
- Context: `context.md`
- Last Updated: <YYYY-MM-DD>

## Items
- `TODO-001` [pending] <short task summary>
  - Details: <constraints, dependencies, or important user wording>
  - Current evidence: <symptom or observation, when useful>
  - Reproduction target: <how to reproduce or validate, when useful>
  - Related files/tests: <optional anchors for later resumption>
  - Success criteria: <definition of done, when useful>
```

Guidelines:

- Use stable IDs like `TODO-001`, `TODO-002`, and increment them.
- Keep summaries short and actionable.
- Put essential nuance in `Details`, not in the title.
- For simple items, `Details` alone is often enough.
- For investigation-style items, add only the extra bullets that materially help a later agent resume the problem without re-deriving the symptom or target.
- If there are no items yet, keep the policy and metadata sections and leave `## Items` empty.

## Update The Current Context

After creating or updating the todo file:

1. Re-read the active `context.md`.
2. Ensure there is a `## References` section.
3. Add or update an entry for `references/todo-list.md`.
4. The reference description must explicitly say that:
   - the file is the todo list for the current context
   - it is user-controlled planning only
   - listed items may be reorganized or executed only when the user explicitly requests it

Recommended reference text:

- `references/todo-list.md` - User-controlled todo list for this context. It is a planning artifact only; items may be added, reorganized, or executed only when the user explicitly requests those actions.

## Response Back To The User

After updating the files:

- summarize what was added or changed in the todo list
- mention the todo-list path
- do **not** imply that work has started
- do **not** volunteer to execute the list unless the user asks
