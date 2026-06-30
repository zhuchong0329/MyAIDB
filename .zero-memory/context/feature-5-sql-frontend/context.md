---
name: feature-5-sql-frontend
description: Feature 5 loop for implementing the SQL tokenizer and minimal parser boundary.
---

# Feature 5: SQL Frontend Boundary

## Loop Start

Feature: SQL tokenizer and minimal parser boundary.

Goal: Implement the first SQL frontend layer so MyAIDB can parse a tiny SQL subset into AST without executing it.

Scope:

- Add `src/sql/mod.rs`.
- Add SQL tokenizer / lexer.
- Add `Token` and `TokenKind`.
- Add parser error type.
- Add AST types.
- Parse `CREATE TABLE table_name (...)`.
- Parse `INSERT INTO table_name VALUES (...)`.
- Support type names: `integer`, `real`, `text`, `blob`, `null`, `vector`.
- Support literals: integer, real, single-quoted string, and `null`.
- Treat SQL keywords as case-insensitive.
- Preserve identifier spelling exactly.
- Use existing `ValueType` in `CREATE TABLE` column definitions.
- Use new SQL `Literal` for `INSERT` values instead of converting directly to runtime `Value`.
- Add tokenizer and parser unit tests.

Out of Scope:

- Do not execute SQL.
- Do not mutate `Catalog`.
- Do not create `Table`.
- Do not insert `Row`.
- Do not implement `SELECT`.
- Do not implement `WHERE`, `ORDER BY`, projection, or expression evaluation.
- Do not implement autoEmbed.
- Do not implement vector literals.
- Do not implement SQL comments.
- Do not implement quoted identifiers.
- Do not implement complex error recovery.
- Do not implement SQL identifier normalization beyond keyword recognition.

Design:

- `sql` is a frontend module separate from `core`.
- `Statement` is the top-level AST.
- `CreateTable` column definitions reuse `ValueType` because type names map directly to MyAIDB's current minimal type system.
- `Insert` stores SQL `Literal` values because SQL literals and runtime `Value` may diverge later through binding, casts, parameters, or nullability rules.
- Keyword matching is case-insensitive, but identifiers are stored exactly as written.
- Semicolon is accepted as optional statement terminator.

Verification:

- `%USERPROFILE%\.cargo\bin\cargo.exe fmt --check`
- `%USERPROFILE%\.cargo\bin\cargo.exe test`
- `%USERPROFILE%\.cargo\bin\cargo.exe clippy --all-targets --all-features -- -D warnings`

Expected Artifacts:

- `src/sql/mod.rs`
- `src/sql/token.rs`
- `src/sql/lexer.rs`
- `src/sql/ast.rs`
- `src/sql/parser.rs`
- Updated `src/lib.rs`
- SQL tokenizer and parser unit tests
- Updated `.zero-memory/context/feature-5-sql-frontend/context.md`

Done Definition:

- Tokenizer recognizes the in-scope SQL tokens.
- Parser creates AST for in-scope `CREATE TABLE` and `INSERT INTO ... VALUES`.
- Keywords are case-insensitive.
- Identifiers preserve exact spelling.
- `CREATE TABLE` columns use `ValueType`.
- `INSERT` values use SQL `Literal`.
- No SQL execution, catalog mutation, table creation, row insertion, SELECT, expression evaluation, autoEmbed, vector literal, comments, or quoted identifiers are introduced.
- Format, tests, and Clippy all pass.
- Loop result and reusable learning are persisted to `.zero-memory`.

## Current Status

- Loop start persisted before implementation.
- User approved no `SELECT` in Loop 5.
- User approved case-insensitive keywords and exact identifier preservation.
- User approved `CREATE TABLE` using `ValueType` and `INSERT` using separate SQL `Literal`.
- Loop completed.

## Loop End

Completed:

- Added `src/sql/mod.rs`, `src/sql/token.rs`, `src/sql/lexer.rs`, `src/sql/ast.rs`, and `src/sql/parser.rs`.
- Exposed the SQL frontend through `src/lib.rs`.
- Added `Token`, `TokenKind`, `LexError`, `ParseError`, `Statement`, `ColumnDef`, and SQL `Literal`.
- Implemented lexing for identifiers, integer literals, real literals, single-quoted text literals, commas, parentheses, and semicolons.
- Implemented parsing for `CREATE TABLE name (...)` and `INSERT INTO name VALUES (...)`.
- `CREATE TABLE` maps supported type names to core `ValueType`.
- `INSERT` preserves SQL literals as `Literal` instead of converting directly to runtime `Value`.
- Keywords are matched case-insensitively.
- Identifier spelling is preserved exactly.
- Optional trailing semicolon is accepted; extra tokens are rejected.

Out-of-scope items intentionally not implemented:

- SQL execution.
- Catalog mutation.
- Table creation.
- Row insertion.
- `SELECT`.
- `WHERE`, `ORDER BY`, projection, or expression evaluation.
- autoEmbed.
- Vector literals.
- SQL comments.
- Quoted identifiers.
- Complex error recovery.

Verification Results:

- `%USERPROFILE%\.cargo\bin\cargo.exe fmt --check` passed.
- `%USERPROFILE%\.cargo\bin\cargo.exe test` passed: 43 tests passed.
- `%USERPROFILE%\.cargo\bin\cargo.exe clippy --all-targets --all-features -- -D warnings` passed.

Failure Notes:

- Initial `fmt --check` failed only because rustfmt wanted to reflow long lines and import ordering.
- Ran `cargo fmt`, then `fmt --check` passed.

Reusable Learning:

- Logged as `DL-20260630-205900.000Z-sql-ast-before-execution`.

Next Loop Candidate:

- Feature 6 should likely introduce a binder/execution boundary that turns parsed `Statement` values into validated core actions, while preserving the current separation between SQL syntax, core storage, and actual mutation.
