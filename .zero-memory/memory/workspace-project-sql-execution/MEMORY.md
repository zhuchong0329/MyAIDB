---
id: workspace.project.sql-execution
name: workspace-project-sql-execution
description: Routes MyAIDB SQL parser/executor and CLI memories, including CREATE TABLE, INSERT, SELECT, and REPL loops.
tags:
  - workspace
  - sql
  - execution
pattern_key: workspace.project.sql-execution
component: application
kind: best-practice
stage: implementation
scope: project
actionability: reference-only
layer: init
status: active
last_updated_at: 2026-07-01T04:00:47Z
freshness_profile: code-env
source_daily_learning_ids:
  - DL-20260701-031034.000Z-insert-execution-literal-to-row
  - DL-20260701-033112.000Z-select-basic-owned-results
  - DL-20260701-040047.000Z-cli-repl-wraps-executor
recurrence_count: 3
last_confirmed_at: 2026-07-01T04:00:47Z
recent_confirmation_ids:
  - DL-20260701-031034.000Z-insert-execution-literal-to-row
  - DL-20260701-033112.000Z-select-basic-owned-results
  - DL-20260701-040047.000Z-cli-repl-wraps-executor
load_next:
  - cli.repl.executor-wrapper
  - sql.executor.insert-execution
  - sql.executor.select-basic
related: []
related_files:
  - src/sql/executor.rs
  - src/sql/parser.rs
  - src/cli.rs
related_symbols:
  - execute_sql
  - Statement
  - ExecuteResult
  - ExecuteError
  - run_repl
---

# Workspace Project SQL Execution

## Description

Start here for MyAIDB SQL execution loop knowledge. This routes memories about how parsed SQL AST nodes connect to the in-memory core model.

## Details

Follow `sql.executor.insert-execution` for the concrete Loop 7 behavior: converting SQL `Literal` values to runtime `Value` values and inserting through `Catalog::table_mut` plus `Table::insert`.

Follow `sql.executor.select-basic` for the concrete Loop 8 behavior: returning owned result columns/rows from a read-only `Catalog::table` query path.

Follow `cli.repl.executor-wrapper` for the concrete Loop 9 behavior: interactive session handling, show-tables meta commands, and formatting around `execute_sql`.

Future SQL loops should keep this node as the routing surface and put concrete behavior on focused child memories.

## Source Extraction

This routing node was created from the Loop 7 completion learning and refreshed with Loop 8 SELECT execution plus Loop 9 CLI learning in `.zero-memory/daily/learning.2026-07-01.md`. It preserves only graph navigation and stable lookup terms.

