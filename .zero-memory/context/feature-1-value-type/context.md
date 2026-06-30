---
name: feature-1-value-type
description: Feature 1 loop for implementing Value and the minimal type system.
---

# Feature 1: Value And Minimal Type System

## Loop Start

Feature: `Value` and minimal type system.

Goal: Implement MyAIDB's first runtime value representation so future `Row`, `Schema`, `Table`, and SQL loops share one clear data model.

Scope:

- Add `src/core/mod.rs`.
- Add `src/core/value.rs`.
- Define `Value` variants: `Null`, `Integer(i64)`, `Real(f64)`, `Text(String)`, `Blob(Vec<u8>)`, `Vector(Vec<f32>)`.
- Define `ValueType` variants: `Null`, `Integer`, `Real`, `Text`, `Blob`, `Vector`.
- Implement `Value::value_type()`.
- Implement basic constructors/conversion helpers.
- Implement read-only access helpers, including `as_vector() -> Option<&[f32]>`.
- Implement `Value::vector_dim() -> Option<usize>`.
- Add unit tests for every supported type.

Out of Scope:

- Do not implement `Row`, `Schema`, `Table`, or `Catalog`.
- Do not implement SQL parser, AST, binder, or executor.
- Do not implement implicit or explicit type conversion rules.
- Do not implement vector distance functions.
- Do not implement model registry, embedding provider, autoEmbed, or semantic query syntax.
- Do not implement serialization, persistence, ordering, or SQL three-valued logic.

Design:

- `Value` is the runtime owned value representation.
- `ValueType` is the lightweight type tag future schema and type-checking code will use.
- Use `Vector(Vec<f32>)` for teaching-friendly construction and tests.
- Expose vector contents through read-only slice APIs so later storage changes such as `Box<[f32]>` do not force broad API churn.
- Keep `Null` as its own runtime value and do not infer SQL null comparison semantics in this loop.
- Avoid NaN-specific `Real` behavior in tests and API contracts.

Verification:

- `%USERPROFILE%\.cargo\bin\cargo.exe fmt --check`
- `%USERPROFILE%\.cargo\bin\cargo.exe test`
- `%USERPROFILE%\.cargo\bin\cargo.exe clippy --all-targets --all-features -- -D warnings`

Expected Artifacts:

- `src/core/mod.rs`
- `src/core/value.rs`
- Updated `src/lib.rs`
- Value and ValueType unit tests
- Updated `.zero-memory/context/feature-1-value-type/context.md`

Done Definition:

- Every `Value` variant reports the correct `ValueType`.
- Text, Blob, and Vector hold owned data.
- Vector dimension and read-only vector slice APIs work.
- Null does not report vector dimension or typed accessors.
- No Row, Schema, Table, SQL, vector distance, or autoEmbed behavior is introduced.
- Format, tests, and Clippy all pass.
- Loop result and reusable learning are persisted to `.zero-memory`.

## Current Status

- Loop start persisted before implementation.
- User approved `Vector(Vec<f32>)` for Feature 1.

## Loop End

Feature: `Value` and minimal type system.

Completed:

- Added `src/core/mod.rs`.
- Added `src/core/value.rs`.
- Defined `Value` with `Null`, `Integer(i64)`, `Real(f64)`, `Text(String)`, `Blob(Vec<u8>)`, and `Vector(Vec<f32>)`.
- Defined `ValueType` with the matching minimal type tags.
- Exposed `core`, `Value`, and `ValueType` from `src/lib.rs`.
- Added owned constructors and `From` conversions for the supported primitive/container inputs.
- Added read-only accessors: `as_integer`, `as_real`, `as_text`, `as_blob`, `as_vector`.
- Added `is_null`, `value_type`, and `vector_dim`.
- Added unit tests covering all supported types, owned data, vector dimension, null behavior, and conversions.

Tests:

- Passed: `%USERPROFILE%\.cargo\bin\cargo.exe fmt --check`
- Passed: `%USERPROFILE%\.cargo\bin\cargo.exe test`
- Passed: `%USERPROFILE%\.cargo\bin\cargo.exe clippy --all-targets --all-features -- -D warnings`

Failures:

- Implementation Bug: first `cargo fmt --check` failed due to one long `assert_eq!` line in `src/core/value.rs`.

Fixes:

- Ran `cargo fmt` and re-ran `cargo fmt --check` successfully.

Reusable Learning:

- Logged `DL-20260630-114505.227Z-vector-owned-readonly-api` in `.zero-memory/daily/learning.2026-06-30.md`.

Next Loop:

- Start Feature 2: define `Row` and `Schema` using `Value` and `ValueType`.

## Feature 2 Planning

- User asked to align Loop 2 scope before implementation.
- Proposed direction: implement `Row` and `Schema` as the next kernel foundation layer over `Value` and `ValueType`.
- Boundary to confirm: no table storage, catalog, SQL parser, execution engine, vector distance, or autoEmbed behavior in Loop 2.
