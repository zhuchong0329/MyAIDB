---
id: workspace.project.sql-execution
name: workspace-project-sql-execution
description: Routes MyAIDB SQL parser/executor memories, including CREATE TABLE, INSERT, and SELECT execution loops.
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
last_updated_at: 2026-07-01T03:31:12Z
freshness_profile: code-env
source_daily_learning_ids:
  - DL-20260701-031034.000Z-insert-execution-literal-to-row
  - DL-20260701-033112.000Z-select-basic-owned-results
recurrence_count: 2
last_confirmed_at: 2026-07-01T03:31:12Z
recent_confirmation_ids:
  - DL-20260701-031034.000Z-insert-execution-literal-to-row
  - DL-20260701-033112.000Z-select-basic-owned-results
load_next:
  - sql.executor.insert-execution
  - sql.executor.select-basic
related: []
related_files:
  - src/sql/executor.rs
  - src/sql/parser.rs
related_symbols:
  - execute_sql
  - Statement
  - ExecuteResult
  - ExecuteError
---

# Workspace Project SQL Execution

## Description

Start here for MyAIDB SQL execution loop knowledge. This routes memories about how parsed SQL AST nodes connect to the in-memory core model.

## Details

Follow `sql.executor.insert-execution` for the concrete Loop 7 behavior: converting SQL `Literal` values to runtime `Value` values and inserting through `Catalog::table_mut` plus `Table::insert`.

Follow `sql.executor.select-basic` for the concrete Loop 8 behavior: returning owned result columns/rows from a read-only `Catalog::table` query path.

Future SQL loops should keep this node as the routing surface and put concrete behavior on focused child memories.

## Source Extraction

This routing node was created from the Loop 7 completion learning and refreshed with Loop 8 SELECT execution learning in `.zero-memory/daily/learning.2026-07-01.md`. It preserves only graph navigation and stable lookup terms.

