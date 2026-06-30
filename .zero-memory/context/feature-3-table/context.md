---
name: feature-3-table
description: Feature 3 loop for implementing the minimal in-memory Table foundation.
---

# Feature 3: In-Memory Table Foundation

## Loop Start

Feature: in-memory `Table` foundation.

Goal: Implement a single-table in-memory data container so future `INSERT`, `SELECT`, `Catalog`, and SQL loops have a stable storage boundary.

Scope:

- Add `Table` with `name: String`, `schema: Schema`, and `rows: Vec<Row>`.
- Add `TableError`.
- Support `Table::new(name, schema)`.
- Support read-only access to table name, schema, row count, emptiness, all rows, and row by index.
- Support `Table::insert(row: Row) -> Result<(), TableError>`.
- `Table::insert` must take owned `Row` and move it into the table after validation.
- Insert must call `schema.validate_row(&row)`.
- Preserve row insertion order.
- Add unit tests for empty table creation, valid insert, invalid row length, invalid row type, row ordering, and row index lookup.

Out of Scope:

- Do not implement `Catalog`.
- Do not implement multi-table management.
- Do not implement SQL `CREATE TABLE`, `INSERT`, or `SELECT`.
- Do not implement query execution.
- Do not implement indexes.
- Do not implement transactions.
- Do not implement persistence.
- Do not implement vector distance functions.
- Do not implement autoEmbed.
- Do not implement concurrency or locking.

Design:

- `Table` owns its `Schema` and `Vec<Row>`.
- `Table::insert(row: Row)` consumes the row to avoid cloning text, blob, and vector payloads.
- `TableError::InvalidRow(SchemaError)` wraps schema validation failures.
- Row index lookup returns `Option<&Row>` instead of an error in this loop, matching `Row::get` and `Schema::column`.
- Table name lookup is exact and does not introduce SQL identifier semantics.

Verification:

- `%USERPROFILE%\.cargo\bin\cargo.exe fmt --check`
- `%USERPROFILE%\.cargo\bin\cargo.exe test`
- `%USERPROFILE%\.cargo\bin\cargo.exe clippy --all-targets --all-features -- -D warnings`

Expected Artifacts:

- `src/core/table.rs`
- Updated `src/core/mod.rs`
- Updated `src/lib.rs`
- Table unit tests
- Updated `.zero-memory/context/feature-3-table/context.md`

Done Definition:

- Table stores rows only after schema validation passes.
- Invalid rows are rejected without changing existing table rows.
- `insert(row: Row)` consumes owned rows and avoids clone-based insertion.
- Row order is preserved.
- No Catalog, SQL, indexes, transactions, persistence, vector distance, concurrency, or autoEmbed behavior is introduced.
- Format, tests, and Clippy all pass.
- Loop result and reusable learning are persisted to `.zero-memory`.

## Current Status

- Loop start persisted before implementation.
- User approved Feature 3 scope and owned `Row` insertion.

## Loop End

Feature: in-memory `Table` foundation.

Completed:

- Added `src/core/table.rs`.
- Added `Table` with `name: String`, `schema: Schema`, and `rows: Vec<Row>`.
- Added `TableError::InvalidRow(SchemaError)`.
- Added `Table::new`, `name`, `schema`, `len`, `is_empty`, `row`, and `rows`.
- Added `Table::insert(row: Row) -> Result<(), TableError>`.
- `insert` validates with `schema.validate_row(&row)` before pushing the owned row.
- Invalid inserts leave existing rows unchanged.
- Updated `src/core/mod.rs` and `src/lib.rs` exports.
- Added unit tests for empty table creation, valid owned-row insert, invalid length, invalid type, row order, row index lookup, and failed insert preservation.

Tests:

- Passed: `%USERPROFILE%\.cargo\bin\cargo.exe fmt --check`
- Passed: `%USERPROFILE%\.cargo\bin\cargo.exe test`
- Passed: `%USERPROFILE%\.cargo\bin\cargo.exe clippy --all-targets --all-features -- -D warnings`

Failures:

- Implementation Bug: first `cargo fmt --check` failed because a few chained test calls needed formatter-approved line wrapping.

Fixes:

- Ran `cargo fmt` and re-ran `cargo fmt --check` successfully.

Reusable Learning:

- Logged `DL-20260630-122051.961Z-table-owned-row-insert` in `.zero-memory/daily/learning.2026-06-30.md`.

Next Loop:

- Start Feature 4: implement `Catalog` for managing multiple in-memory tables by exact table name.

## Feature 4 Planning

- User asked to align Loop 4 scope before implementation.
- Proposed direction: implement a minimal in-memory `Catalog` that owns multiple `Table` values and exposes exact table-name lookup.
- Boundary to confirm: no SQL catalog semantics, no schemas/namespaces, no persistence, no concurrency, no DDL parser, no transactions, no indexes, and no autoEmbed behavior in Loop 4.
