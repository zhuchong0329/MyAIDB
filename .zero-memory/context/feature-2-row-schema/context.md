---
name: feature-2-row-schema
description: Feature 2 loop for implementing Row, Column, Schema, and schema validation.
---

# Feature 2: Row And Schema

## Loop Start

Feature: `Row` and `Schema`.

Goal: Implement MyAIDB's row data structure and schema description so future `Table`, `INSERT`, and `SELECT` loops have a stable data boundary.

Scope:

- Add `Row` as an owned list of `Value`.
- Add `Column` with `name: String` and `value_type: ValueType`.
- Add `Schema` as an owned list of `Column`.
- Add `SchemaError`.
- Support row length and indexed value access.
- Support schema column count and indexed column access.
- Support exact column-name lookup.
- Validate duplicate column names when creating `Schema`.
- Validate row shape against schema:
  - row column count must match schema column count.
  - each `Value::value_type()` must exactly match the column `ValueType`.
  - `Value::Null` only matches `ValueType::Null`.
- Add unit tests for row access, schema lookup, duplicate columns, row length mismatch, type mismatch, and strict null behavior.

Out of Scope:

- Do not implement `Table` or `Catalog`.
- Do not implement `INSERT`.
- Do not implement SQL parser, AST, binder, or executor.
- Do not implement indexes.
- Do not implement vector distance functions.
- Do not implement autoEmbed or semantic query behavior.
- Do not implement nullable columns or SQL three-valued logic.
- Do not implement identifier normalization or SQL case-insensitive name rules.

Design:

- `Row` owns `Vec<Value>`.
- `Schema` owns `Vec<Column>`.
- `Schema::new` returns `Result<Schema, SchemaError>` so invalid schemas fail early.
- Column-name lookup is exact and case-sensitive in this loop because SQL identifier normalization is out of scope.
- Null matching stays strict: `Value::Null` only satisfies `ValueType::Null`.

Verification:

- `%USERPROFILE%\.cargo\bin\cargo.exe fmt --check`
- `%USERPROFILE%\.cargo\bin\cargo.exe test`
- `%USERPROFILE%\.cargo\bin\cargo.exe clippy --all-targets --all-features -- -D warnings`

Expected Artifacts:

- `src/core/row.rs`
- `src/core/schema.rs`
- Updated `src/core/mod.rs`
- Updated `src/lib.rs`
- Row and Schema unit tests
- Updated `.zero-memory/context/feature-2-row-schema/context.md`

Done Definition:

- Row stores and exposes values without implementing table behavior.
- Schema rejects duplicate column names.
- Schema validates row length and value types.
- Null is strict and does not match non-null column types.
- No Table, Catalog, SQL, index, vector distance, nullable-column, or autoEmbed behavior is introduced.
- Format, tests, and Clippy all pass.
- Loop result and reusable learning are persisted to `.zero-memory`.

## Current Status

- Loop start persisted before implementation.
- User approved Feature 2 scope and strict Null matching.

## Loop End

Feature: `Row` and `Schema`.

Completed:

- Added `src/core/row.rs`.
- Added `src/core/schema.rs`.
- Added `Row` as an owned `Vec<Value>` wrapper with read-only accessors and owned extraction.
- Added `Column` with `name: String` and `value_type: ValueType`.
- Added `Schema` as an owned `Vec<Column>` wrapper.
- Added `SchemaError` with `ColumnCountMismatch`, `TypeMismatch`, `DuplicateColumn`, and `ColumnNotFound`.
- Added exact, case-sensitive column-name lookup.
- Added row validation against schema length and exact value types.
- Preserved strict null behavior: `Value::Null` only matches `ValueType::Null`.
- Updated `src/core/mod.rs` and `src/lib.rs` exports.

Tests:

- Passed: `%USERPROFILE%\.cargo\bin\cargo.exe fmt --check`
- Passed: `%USERPROFILE%\.cargo\bin\cargo.exe test`
- Passed: `%USERPROFILE%\.cargo\bin\cargo.exe clippy --all-targets --all-features -- -D warnings`

Failures:

- Implementation Bug: first `cargo fmt --check` failed because a few test assertions needed formatter-approved line wrapping.

Fixes:

- Ran `cargo fmt` and re-ran `cargo fmt --check` successfully.

Reusable Learning:

- Logged `DL-20260630-115938.344Z-schema-exact-names-before-sql-identifiers` in `.zero-memory/daily/learning.2026-06-30.md`.

Next Loop:

- Start Feature 3: define the in-memory `Table` foundation using `Schema` and `Row`.
