---
name: myaidb-sql-database-loops
description: Long-running MyAIDB SQL database implementation loops, including parser, executor, CLI, and query semantics.
---

## Status

- active; Loop 11 implementation complete and verified.

## Current Summary

- Loop 6 completed `CREATE TABLE` execution through `execute_sql`, `Schema::new`, and `Catalog::create_table`.
- Loop 7 completed `INSERT INTO table VALUES (...)` execution through `Catalog::table_mut`, `literal_to_value`, `Row::new`, and `Table::insert`.
- Loop 8 completed basic `SELECT` execution with owned result columns/rows for `SELECT *`, explicit projection, and optional `LIMIT`.
- Loop 9 completed an interactive CLI/REPL for manual create/insert/select/show-tables workflows.
- Loop 9.5 completed TTY line editing through `rustyline` while preserving the generic `BufRead` runner for piped stdin and tests.
- Loop 10 completed CLI-only schema introspection with `.schema`, `schema`, and `describe <table>`, reusing `Catalog`, `Table`, and `Schema` APIs without changing SQL parser semantics.
- Current active task: Loop 11 query semantics expansion completed; next step is summarize, commit, or align Loop 12.

## Loop 11 Scope Draft

- Recommended feature: expand SELECT query semantics with simple filtering and sorting end-to-end.
- User accepted the scope and asked to start Loop 11.
- Proposed in scope:
  - Add lexer tokens for comparison operators: `=`, `!=`, `<`, `<=`, `>`, `>=`.
  - Add AST types for simple predicates and ordering.
  - Parse `SELECT ... FROM table WHERE column op literal`.
  - Parse optional `ORDER BY column [ASC|DESC]`.
  - Keep existing `LIMIT`; define execution order as `WHERE`, `ORDER BY`, `LIMIT`, then projection.
  - Execute predicates for supported scalar values: null equality, integer, real, and text comparisons.
  - Preserve exact column matching through schema lookup and keep SELECT read-only.
  - Add lexer/parser/executor tests and CLI smoke coverage using create/insert/select with where/order/limit.
- Proposed out of scope: boolean `AND`/`OR`/`NOT`, parentheses, expressions on both sides, column-to-column comparison, functions, aliases, joins, aggregates, indexes, query planner, vector search, collations, full SQL NULL three-valued logic, multi-column order, and parser-level `DESCRIBE`.

## Loop 11 Start

- Goal: implement `WHERE column op literal` and `ORDER BY column [ASC|DESC]` for SELECT while preserving the existing read-only SELECT boundary and owned result model.
- Planned touched surfaces: `src/sql/token.rs`, `src/sql/lexer.rs`, `src/sql/ast.rs`, `src/sql/parser.rs`, `src/sql/executor.rs`, CLI smoke tests, and focused unit tests.
- Verification plan: `cargo fmt`, `cargo test`, `cargo build`, `cargo fmt --check`, `cargo clippy --all-targets --all-features -- -D warnings`, and `git diff --check`.

## Loop 11 End

- Added comparison tokens for `=`, `!=`, `<`, `<=`, `>`, and `>=`.
- Extended SELECT AST with `SelectPredicate`, `ComparisonOperator`, `SelectOrder`, and `SortDirection`; exported the new query types through `src/sql/mod.rs` and `src/lib.rs`.
- Parser now supports `WHERE column op literal`, `ORDER BY column [ASC|DESC]`, and existing `LIMIT` after those clauses.
- Executor now applies SELECT stages as `WHERE`, `ORDER BY`, `LIMIT`, then projection.
- Predicate/order/projection column lookup all reuse `Schema::column_index`, preserving exact column semantics.
- Predicate type mismatches surface as `SchemaError::TypeMismatch`; missing WHERE/ORDER columns surface as `SchemaError::ColumnNotFound`.
- Unsupported null ordering comparisons and vector/blob ordering produce explicit executor errors.
- Added lexer/parser/executor tests plus binary smoke coverage for filtered and ordered SELECT through stdin.
- Verification passed: `cargo fmt`, `cargo test` (85 library tests, 4 smoke tests), `cargo build`, `cargo fmt --check`, `cargo clippy --all-targets --all-features -- -D warnings`, and `git diff --check`.
- Reusable learning logged as `DL-20260701-070422.000Z-select-where-order-limit` and curated into `sql.executor.select-basic`; memory graph validation passed with only generated-index warnings.

## Important Current Worktree Notes

- Loop 10 code and tests are implemented and verified but not yet committed in this context handoff.
- Verification already passed for Loop 10: `cargo fmt`, `cargo test` (72 library tests, 3 smoke tests), `cargo build`, `cargo fmt --check`, `cargo clippy --all-targets --all-features -- -D warnings`, and `git diff --check`.
- Current uncommitted task files may include `src/cli.rs`, `tests/smoke.rs`, zero-memory daily/memory/context updates, and observability outcome events.

## Context Migration

- Previous active context path: `.zero-memory/context/feature-6-create-table-execution/context.md`.
- Reason for migration: that path was created for Loop 6 but became the active handoff for later loops; the user approved a clearer long-running context name.
- Keep the previous context as historical detail. Do not delete it; use it as a reference for Loop 6 through Loop 10 chronology and earlier compaction artifacts.
- New active pointer should be `.zero-memory/context/myaidb-sql-database-loops/context.md`.

## 2026-07-01 Migration Completion

- Created this broader active context and updated `.zero-memory/tmp/current-context.txt` to point here.
- Marked `.zero-memory/context/feature-6-create-table-execution/context.md` as migrated historical detail.
- Cleaned a generated `.zero-memory/tmp/zero-memory-observability/writer-id` scratch file.
- Verified both context files are under the 200-line guideline: this context has 51 lines at creation time; the old context has 96 lines after marking migration.

## References

- `.zero-memory/context/feature-6-create-table-execution/context.md` - Historical context and detailed recent notes from Loop 6 through Loop 11 scope alignment before migration.
- `.zero-memory/context/feature-6-create-table-execution/references/history.md` - Preserved detailed chronology from the older context compaction.
- `.zero-memory/context/feature-6-create-table-execution/references/artifacts.md` - Preserved paths, scripts, and supporting artifact references from the older context compaction.
