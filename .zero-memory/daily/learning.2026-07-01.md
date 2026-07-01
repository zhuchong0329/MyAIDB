# Daily Learning - 2026-07-01

## DL-20260701-005000.000Z-create-table-execution-before-insert

Summary: MyAIDB Feature 6 executes only `CREATE TABLE` SQL and keeps `INSERT` execution for a separate loop.

Durable details: `execute_sql(catalog, sql)` parses SQL into a `Statement`, then dispatches only `Statement::CreateTable`. Column definitions are converted into core `Column` values, then into `Schema`, then applied through `Catalog::create_table`. `INSERT` returns `ExecuteError::UnsupportedStatement` so unsupported execution is visible rather than silently ignored.

Why reusable: Future SQL execution loops should keep syntax parsing, schema construction, catalog mutation, and unsupported statement handling explicit. Feature 7 should convert SQL `Literal` values to runtime `Value` values against the target table schema, preserving `Table::insert(row)` validate-before-mutate semantics.

Suggested memory targets: sql.executor.create-table, sql.executor.future-insert

Source Slug: feature-6-create-table-execution
Source Context: `.zero-memory/context/feature-6-create-table-execution/context.md`
Source Sections: Design, Loop End
Related Files: `src/sql/executor.rs`, `src/sql/mod.rs`, `src/lib.rs`

## DL-20260701-024823.000Z-macos-bootstrap-rust-toolchain

- Timestamp: 2026-07-01T02:48:23Z
- Source Slug: feature-6-create-table-execution
- Source Context: `.zero-memory/context/feature-6-create-table-execution/context.md`
- Type: best-practice
- Pattern-Key: tooling.bootstrap.rust-toolchain-script
- Summary: MyAIDB macOS/Linux bootstrap should be executable and derive the Rust channel from `rust-toolchain.toml`.
- Details: Running `./scripts/bootstrap.sh` initially failed on macOS with `permission denied` because the script lacked executable mode. After adding execute permission, the script reached rustup setup. The script was also hardened to read `channel` from `rust-toolchain.toml` instead of hardcoding `stable`, and to source `$HOME/.cargo/env` when rustup exists but is not currently on PATH.
- Why Reusable: Future environment setup or README/bootstrap maintenance should keep README commands runnable directly and avoid drift between `rust-toolchain.toml` and installation scripts.
- Suggested Memory Targets:
  - tooling.bootstrap.rust-toolchain
- Related Files:
  - `README.md`
  - `rust-toolchain.toml`
  - `scripts/bootstrap.sh`
  - `.zero-memory/context/feature-6-create-table-execution/context.md`
- Source Sections:
  - 2026-07-01 macOS Environment Bootstrap
- Status: new

## DL-20260701-031034.000Z-insert-execution-literal-to-row

- Timestamp: 2026-07-01T03:10:34Z
- Source Slug: feature-6-create-table-execution
- Source Context: `.zero-memory/context/feature-6-create-table-execution/context.md`
- Type: best-practice
- Pattern-Key: sql.executor.insert-literal-to-row
- Summary: MyAIDB Loop 7 executes `INSERT INTO table VALUES (...)` by converting SQL literals to runtime values and delegating validation/mutation to `Table::insert`.
- Details: `Statement::Insert` now creates a `Row` from converted `Literal` values, looks up the target table through `Catalog::table_mut`, and calls `Table::insert(row)`. The executor exposes `ExecuteResult::Insert { table, rows_inserted: 1 }` and wraps insertion failures with `ExecuteError::Table(TableError)`. Missing tables remain catalog errors. Row length mismatch, type mismatch, and strict null behavior stay owned by `Schema::validate_row` through `Table::insert`, preserving validate-before-mutate behavior.
- Why Reusable: Future SQL execution loops should keep parser literals separate from runtime values, route catalog lookup errors separately from table/schema validation errors, and reuse core mutation boundaries instead of duplicating validation in the SQL executor.
- Suggested Memory Targets:
  - sql.executor.insert-execution
  - sql.executor.future-select
- Related Files:
  - `src/sql/executor.rs`
  - `src/sql/ast.rs`
  - `src/core/table.rs`
  - `src/core/schema.rs`
- Related Symbols:
  - `execute_sql`
  - `ExecuteResult::Insert`
  - `ExecuteError::Table`
  - `literal_to_value`
  - `Table::insert`
- Source Sections:
  - 2026-07-01 Loop 7 Start
  - 2026-07-01 Loop 7 End
- Status: new

## DL-20260701-033112.000Z-select-basic-owned-results

- Timestamp: 2026-07-01T03:31:12Z
- Source Slug: feature-6-create-table-execution
- Source Context: `.zero-memory/context/feature-6-create-table-execution/context.md`
- Type: best-practice
- Pattern-Key: sql.executor.select-owned-results
- Summary: MyAIDB Loop 8 implements the first SELECT read path with owned result columns and rows.
- Details: `SELECT` is implemented end-to-end across token, lexer, AST, parser, and executor. The supported subset is `SELECT * FROM table`, `SELECT col1, col2 FROM table`, and optional `LIMIT <integer>`. Execution reads through `Catalog::table` and returns `ExecuteResult::Select { columns: Vec<Column>, rows: Vec<Row> }`, avoiding borrowed result lifetimes. Projection uses `Schema::column_index` for exact column matching and requested ordering; missing tables surface as catalog errors and missing columns as schema errors. LIMIT truncates rows while preserving insertion order, and SELECT does not mutate the table.
- Why Reusable: Future query features should preserve the read-only executor boundary, keep result ownership explicit, and extend projection/filtering behavior without borrowing from `Catalog` or duplicating schema lookup semantics.
- Suggested Memory Targets:
  - sql.executor.select-basic
  - sql.executor.future-where-order-limit
- Related Files:
  - `src/sql/token.rs`
  - `src/sql/lexer.rs`
  - `src/sql/ast.rs`
  - `src/sql/parser.rs`
  - `src/sql/executor.rs`
- Related Symbols:
  - `TokenKind::Asterisk`
  - `Statement::Select`
  - `SelectProjection`
  - `ExecuteResult::Select`
  - `execute_select`
  - `project_row`
- Source Sections:
  - Loop 8 Start
  - Loop 8 End
- Status: new
