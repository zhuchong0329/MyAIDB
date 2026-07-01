---
id: cli.repl.executor-wrapper
name: cli-repl-executor-wrapper
description: Keep the MyAIDB CLI as a testable session, meta-command, and formatting layer over execute_sql.
tags:
  - cli
  - repl
  - sql
pattern_key: cli.repl.wraps-sql-executor
component: application
kind: best-practice
stage: implementation
scope: project
actionability: reference-only
layer: detailed
status: active
last_updated_at: 2026-07-01T04:00:47Z
freshness_profile: code-env
source_daily_learning_ids:
  - DL-20260701-040047.000Z-cli-repl-wraps-executor
recurrence_count: 1
last_confirmed_at: 2026-07-01T04:00:47Z
recent_confirmation_ids:
  - DL-20260701-040047.000Z-cli-repl-wraps-executor
load_next: []
related:
  - workspace.project.sql-execution
  - sql.executor.select-basic
related_files:
  - src/cli.rs
  - src/main.rs
  - tests/smoke.rs
related_symbols:
  - run_repl
  - process_command
  - print_execute_result
  - print_select_result
  - Catalog::table_names
---

# CLI REPL Executor Wrapper

## Description

Use this memory when extending or reviewing MyAIDB's interactive CLI/REPL.

The CLI should remain a thin session and formatting layer. SQL semantics stay in `execute_sql`; CLI-only commands such as `show tables`, `.help`, and `.quit` are handled before SQL dispatch.

## Details

Keep `src/main.rs` focused on argument routing. No args and `repl` start the REPL; `--help` and `--version` stay non-interactive.

Keep `run_repl` generic over `BufRead` and `Write` so unit tests can inject stdin/stdout without spawning a process. Use binary smoke tests only for end-to-end argument/stdin behavior.

The REPL owns one process-local `Catalog` for the session. It should dispatch `CREATE TABLE`, `INSERT`, and `SELECT` to `execute_sql`, print `ExecuteResult` values, and report errors without panicking or exiting the session.

Do not add CLI-only commands to the SQL parser unless they are intended to become SQL language features. `show tables` belongs in the CLI for now and should use `Catalog::table_names`.

## Source Extraction

Stable facts came from Loop 9 implementation and verification recorded in `.zero-memory/daily/learning.2026-07-01.md`. The preserved rule is the separation between CLI/session behavior and SQL execution semantics.
