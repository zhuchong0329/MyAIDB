---
id: sql.executor.insert-execution
name: sql-executor-insert-execution
description: Execute INSERT by converting SQL literals to runtime values, building a Row, and delegating validation to Table::insert.
tags:
  - sql
  - executor
  - insert
pattern_key: sql.executor.insert-literal-to-row
component: application
kind: best-practice
stage: implementation
scope: project
actionability: reference-only
layer: detailed
status: active
last_updated_at: 2026-07-01T03:10:34Z
freshness_profile: code-env
source_daily_learning_ids:
  - DL-20260701-031034.000Z-insert-execution-literal-to-row
recurrence_count: 1
last_confirmed_at: 2026-07-01T03:10:34Z
recent_confirmation_ids:
  - DL-20260701-031034.000Z-insert-execution-literal-to-row
load_next: []
related:
  - workspace.project.sql-execution
related_files:
  - src/sql/executor.rs
  - src/sql/ast.rs
  - src/core/table.rs
  - src/core/schema.rs
related_symbols:
  - execute_sql
  - ExecuteResult::Insert
  - ExecuteError::Table
  - literal_to_value
  - Table::insert
  - Schema::validate_row
---

# SQL Executor Insert Execution

## Description

Use this memory when extending or reviewing MyAIDB SQL execution for `INSERT INTO table VALUES (...)`.

The executor should keep SQL syntax and runtime storage concerns separate: parse into `Statement::Insert`, convert each SQL `Literal` into a core `Value`, build an owned `Row`, then delegate mutation and validation to the target `Table`.

## Details

Loop 7's execution path is `execute_sql -> parse_statement -> Statement::Insert -> Catalog::table_mut -> Row::new -> Table::insert`.

Keep missing table errors as `ExecuteError::Catalog(CatalogError::TableNotFound)`. Keep row length mismatch, type mismatch, and strict null behavior inside `Table::insert` / `Schema::validate_row`, surfaced through `ExecuteError::Table(TableError::InvalidRow(...))`.

Do not duplicate schema validation in the SQL executor. The core `Table::insert(row)` method already validates before pushing, so failed SQL inserts should not mutate existing rows.

Current supported SQL literals map directly: `Null`, `Integer`, `Real`, and `Text`. Blob/vector literal syntax, implicit casts, column-list inserts, multi-row inserts, defaults, constraints, transactions, and SELECT remain separate future loops.

## Source Extraction

Stable facts came from Loop 7 implementation and verification recorded in `.zero-memory/daily/learning.2026-07-01.md`. Transient command output was dropped; the preserved rule is the executor/core boundary and error-routing contract.
