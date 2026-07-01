---
id: cli.repl.executor-wrapper
name: cli-repl-executor-wrapper
description: Keep the MyAIDB CLI as a testable session, meta-command, input-frontend, and formatting layer over execute_sql.
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
last_updated_at: 2026-07-01T07:22:08Z
freshness_profile: code-env
source_daily_learning_ids:
  - DL-20260701-040047.000Z-cli-repl-wraps-executor
  - DL-20260701-054159.000Z-repl-tty-line-editor
  - DL-20260701-061713.000Z-cli-schema-introspection
  - DL-20260701-072208.000Z-seeded-dev-repl
recurrence_count: 4
last_confirmed_at: 2026-07-01T07:22:08Z
recent_confirmation_ids:
  - DL-20260701-040047.000Z-cli-repl-wraps-executor
  - DL-20260701-054159.000Z-repl-tty-line-editor
  - DL-20260701-061713.000Z-cli-schema-introspection
  - DL-20260701-072208.000Z-seeded-dev-repl
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
  - run_interactive_repl
  - std::io::IsTerminal
  - parse_schema_command
  - print_schema_command
  - Catalog::table
  - Table::schema
  - Schema::columns
  - run_repl_with_catalog
  - run_interactive_repl_with_catalog
  - run_seed_script
  - run_seeded_repl
---

# CLI REPL Executor Wrapper

## Description

Use this memory when extending or reviewing MyAIDB's interactive CLI/REPL.

The CLI should remain a thin input/session/formatting layer. SQL semantics stay in `execute_sql`; CLI-only commands such as `show tables`, `.help`, and `.quit` are handled before SQL dispatch.

## Details

Keep `src/main.rs` focused on argument routing. No args and `repl` start the REPL; `--help` and `--version` stay non-interactive.

Keep `run_repl` generic over `BufRead` and `Write` so unit tests can inject stdin/stdout without spawning a process. Use binary smoke tests only for end-to-end argument/stdin behavior.

For manual terminal sessions, use `run_interactive_repl` with `rustyline` so left/right arrows, backspace/delete, and up/down in-session history work. Gate this through `std::io::IsTerminal` in `main.rs`; piped stdin should keep using the generic `BufRead` runner so automation and smoke tests stay deterministic.

The REPL owns one process-local `Catalog` for the session. It should dispatch `CREATE TABLE`, `INSERT`, and `SELECT` to `execute_sql`, print `ExecuteResult` values, and report errors without panicking or exiting the session.

Do not add CLI-only commands to the SQL parser unless they are intended to become SQL language features. `show tables` belongs in the CLI for now and should use `Catalog::table_names`.

Schema inspection is also a CLI shell feature for now. Commands such as `.schema`, `schema`, and `describe <table>` should be parsed before SQL dispatch, then rendered from core read APIs: `Catalog::table_names` for all tables, and `Catalog::table` plus `Table::schema().columns()` for one table. Reuse the CLI table formatting helpers and report missing tables without exiting the session.

For seeded manual testing, avoid piping seed SQL directly into the REPL when the user should keep interactive terminal editing. Instead, load seed commands into a shared `Catalog` first, then enter `run_repl_with_catalog` or `run_interactive_repl_with_catalog` with that same catalog. Seed loading should be strict: SQL errors in the seed file should fail startup instead of being rendered as ordinary REPL errors and ignored.

## Source Extraction

Stable facts came from Loop 9, Loop 9.5, Loop 10, and seeded dev REPL implementation and verification recorded in `.zero-memory/daily/learning.2026-07-01.md`. The preserved rule is the separation between CLI input/session/inspection behavior and SQL execution semantics while preserving interactive TTY ergonomics.
