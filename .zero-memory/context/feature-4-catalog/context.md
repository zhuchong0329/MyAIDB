---
name: feature-4-catalog
description: Feature 4 loop for implementing the minimal in-memory Catalog.
---

# Feature 4: In-Memory Catalog

## Loop Start

Feature: in-memory `Catalog`.

Goal: Implement a minimal in-memory table registry so future SQL `CREATE TABLE`, `INSERT`, and `SELECT` loops can find tables by name.

Scope:

- Add `Catalog` that owns multiple `Table` values.
- Add `CatalogError`.
- Support `Catalog::new()`.
- Support `Catalog::len()` and `Catalog::is_empty()`.
- Support `Catalog::create_table(name, schema) -> Result<(), CatalogError>`.
- Support `Catalog::insert_table(table) -> Result<(), CatalogError>`.
- Support read-only lookup: `table(name) -> Result<&Table, CatalogError>`.
- Support mutable lookup: `table_mut(name) -> Result<&mut Table, CatalogError>`.
- Support listing table names.
- Use exact, case-sensitive table-name matching.
- Add tests for empty catalog, table creation, duplicate table rejection, missing table lookup, mutable table lookup plus row insert, and exact case-sensitive names.

Out of Scope:

- Do not implement SQL `CREATE TABLE`, `INSERT`, or `SELECT`.
- Do not implement a DDL parser.
- Do not implement database/schema namespaces.
- Do not implement system tables.
- Do not implement persistence.
- Do not implement transactions.
- Do not implement concurrency or locking.
- Do not implement indexes.
- Do not implement vector distance functions.
- Do not implement autoEmbed.
- Do not implement SQL identifier normalization or case folding.

Design:

- `Catalog` uses `Vec<Table>` first for teaching clarity and observable insertion order.
- `create_table(name, schema)` is the main creation path and internally creates `Table::new(name, schema)`.
- `insert_table(table)` is supported for tests and future internal reuse.
- Duplicate detection uses exact table names.
- `table_names()` returns a read-only iterator over names in insertion order.
- Lookup returns `Result` instead of `Option` because missing tables are semantic errors for future SQL layers.

Verification:

- `%USERPROFILE%\.cargo\bin\cargo.exe fmt --check`
- `%USERPROFILE%\.cargo\bin\cargo.exe test`
- `%USERPROFILE%\.cargo\bin\cargo.exe clippy --all-targets --all-features -- -D warnings`

Expected Artifacts:

- `src/core/catalog.rs`
- Updated `src/core/mod.rs`
- Updated `src/lib.rs`
- Catalog unit tests
- Updated `.zero-memory/context/feature-4-catalog/context.md`

Done Definition:

- Catalog can create and register tables.
- Catalog rejects duplicate exact table names.
- Catalog can perform read-only and mutable lookup by exact name.
- Mutable lookup can insert rows through `Table::insert`.
- Table names preserve insertion order.
- No SQL, DDL parser, namespace, system table, persistence, transaction, concurrency, index, vector distance, identifier normalization, or autoEmbed behavior is introduced.
- Format, tests, and Clippy all pass.
- Loop result and reusable learning are persisted to `.zero-memory`.

## Current Status

- Loop start persisted before implementation.
- User approved exact case-sensitive table names.
- User approved `create_table(name, schema)` as the main path and `insert_table(table)` as a supported secondary path.

## Loop End

Feature: in-memory `Catalog`.

Completed:

- Added `src/core/catalog.rs`.
- Added `Catalog` owning `Vec<Table>`.
- Added `CatalogError` with `DuplicateTable` and `TableNotFound`.
- Added `Catalog::new`, `len`, and `is_empty`.
- Added `create_table(name, schema)` as the main creation path.
- Added `insert_table(table)` for tests and future internal reuse.
- Added `table(name)` and `table_mut(name)` lookups.
- Added `table_names()` preserving insertion order.
- Kept exact, case-sensitive table-name matching.
- Updated `src/core/mod.rs` and `src/lib.rs` exports.
- Added unit tests for empty catalog, table creation, inserting existing table values, duplicate rejection, missing lookup, mutable lookup plus row insert, and exact case-sensitive names.

Tests:

- Passed: `%USERPROFILE%\.cargo\bin\cargo.exe fmt --check`
- Passed: `%USERPROFILE%\.cargo\bin\cargo.exe test`
- Passed: `%USERPROFILE%\.cargo\bin\cargo.exe clippy --all-targets --all-features -- -D warnings`

Failures:

- Implementation Bug: first `cargo fmt --check` failed because several test assertions needed formatter-approved line wrapping.

Fixes:

- Ran `cargo fmt` and re-ran `cargo fmt --check` successfully.

Reusable Learning:

- Logged `DL-20260630-122917.876Z-catalog-vec-exact-name-contract` in `.zero-memory/daily/learning.2026-06-30.md`.

Next Loop:

- Start Feature 5: define the first SQL frontend boundary, likely tokenizer/parser planning before implementation.

## Feature 5 Planning

- User asked to align Loop 5 scope before implementation.
- Proposed direction: start SQL frontend with tokenizer and a minimal parser boundary, not execution.
- Boundary to confirm: no binder, no execution, no catalog mutation, no row insertion, no expression evaluator, no SQL identifier normalization beyond tokenization decisions.
