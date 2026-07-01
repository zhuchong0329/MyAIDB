---
id: sql.executor.select-basic
name: sql-executor-select-basic
description: Execute SELECT by reading table rows without mutation, applying query stages, and returning owned projected columns and rows.
tags:
  - sql
  - executor
  - select
pattern_key: sql.executor.select-owned-results
component: application
kind: best-practice
stage: implementation
scope: project
actionability: reference-only
layer: detailed
status: active
last_updated_at: 2026-07-01T07:04:22Z
freshness_profile: code-env
source_daily_learning_ids:
  - DL-20260701-033112.000Z-select-basic-owned-results
  - DL-20260701-070422.000Z-select-where-order-limit
recurrence_count: 2
last_confirmed_at: 2026-07-01T07:04:22Z
recent_confirmation_ids:
  - DL-20260701-033112.000Z-select-basic-owned-results
  - DL-20260701-070422.000Z-select-where-order-limit
load_next: []
related:
  - workspace.project.sql-execution
  - sql.executor.insert-execution
related_files:
  - src/sql/token.rs
  - src/sql/lexer.rs
  - src/sql/ast.rs
  - src/sql/parser.rs
  - src/sql/executor.rs
related_symbols:
  - TokenKind::Asterisk
  - Statement::Select
  - SelectProjection
  - SelectPredicate
  - SelectOrder
  - ComparisonOperator
  - SortDirection
  - ExecuteResult::Select
  - execute_select
  - evaluate_predicate
  - sort_rows
  - project_row
---

# SQL Executor Select Basic

## Description

Use this memory when extending or reviewing MyAIDB's basic `SELECT` read path.

Loop 8 introduced `SELECT * FROM table`, explicit projection, and optional `LIMIT <integer>`. Loop 11 extends the same path with `WHERE column op literal` and `ORDER BY column [ASC|DESC]`. The executor returns owned `Column` and `Row` values so callers do not borrow from `Catalog`.

## Details

The read path should be side-effect-free: use `Catalog::table` and never `table_mut` for SELECT. Missing tables remain `ExecuteError::Catalog(CatalogError::TableNotFound)`.

Projection, filtering, and ordering should reuse `Schema::column_index` so exact column-name behavior stays centralized. Missing projection, filter, or ordering columns surface as `ExecuteError::Schema(SchemaError::ColumnNotFound)`. Explicit projection returns columns and values in the requested order.

SELECT query stages should run in this executor order: `WHERE` filter, `ORDER BY`, `LIMIT`, then projection. This keeps filtering and ordering columns usable even when they are not part of the final projection.

Predicate type mismatches should surface as schema type mismatches. Unsupported comparisons or ordering for values such as null inequality ordering and blob/vector ordering should produce explicit executor errors rather than silently falling back to insertion order.

Future boolean expressions, aliases, qualified names, joins, aggregates, indexes, planner/binder work, and SQL-standard null logic should extend this boundary deliberately instead of bypassing the read-only owned-result model.

## Source Extraction

Stable facts came from Loop 8 and Loop 11 implementation and verification recorded in `.zero-memory/daily/learning.2026-07-01.md`. The preserved rule is the owned result model and read-only SELECT pipeline boundary.
