# Daily Learning - 2026-06-30

## DL-20260630-092841.280Z-rust-path-refresh

Summary: Windows Rust bootstrap can install Rustup successfully while the current PowerShell or Codex session still cannot resolve `cargo`.

Durable details: `winget install --id Rustlang.Rustup -e` needs non-interactive agreement flags when run from automation: `--accept-package-agreements --accept-source-agreements`. After Rustup installation, the active process may need `%USERPROFILE%\.cargo\bin` prepended to `PATH`; even then, already-running parent shells may still require a restart before plain `cargo`, `rustc`, or `rustup` commands resolve. Absolute paths under `%USERPROFILE%\.cargo\bin` can verify the installation immediately.

Why reusable: Future Windows setup or CI-like bootstrap work may fail with a misleading "cargo not found" after a successful Rustup install. The fix is to refresh PATH in the script and document that the user may need to restart the shell.

Suggested memory targets: workspace.environment.rust, workflow.bootstrap.windows

Source Slug: default
Source Context: `.zero-memory/context/default/context.md`
Source Sections: Rust Environment
Related Files: `scripts/bootstrap.ps1`, `README.md`, `rust-toolchain.toml`

## DL-20260630-100004.638Z-windows-rust-msvc-linker

Summary: Windows Rust MSVC builds require more than Rustup; `cargo test` needs Visual Studio Build Tools C++ workload and Windows SDK.

Durable details: After installing Rust stable, `cargo test` failed with `link.exe not found`. Trying Rust's `rust-lld.exe` linker also failed because Windows SDK import libraries such as `kernel32.lib`, `ntdll.lib`, `userenv.lib`, `ws2_32.lib`, and `dbghelp.lib` were missing. Installing `Microsoft.VisualStudio.2022.BuildTools` through `winget` with `Microsoft.VisualStudio.Workload.VCTools --includeRecommended` resolved linking, even though the installer reported that a reboot may be required.

Why reusable: Future Windows machines may appear to have a valid Rust toolchain while still failing every test/build at link time. Bootstrap and documentation should treat the platform linker toolchain as a first-class dependency.

Suggested memory targets: workspace.environment.rust, workflow.bootstrap.windows

Source Slug: feature-0-rust-skeleton
Source Context: `.zero-memory/context/feature-0-rust-skeleton/context.md`
Source Sections: Loop End
Related Files: `README.md`, `scripts/bootstrap.ps1`, `scripts/bootstrap.sh`

## DL-20260630-114505.227Z-vector-owned-readonly-api

Summary: MyAIDB Feature 1 uses `Value::Vector(Vec<f32>)` internally but exposes vectors through read-only slice APIs.

Durable details: `Vec<f32>` keeps early construction, testing, and debugging simple, which fits the teaching-oriented project goal. The public accessor `as_vector() -> Option<&[f32]>` avoids promising caller-side append/growth semantics. This keeps the API compatible with a future internal switch to `Box<[f32]>` or another compact vector storage representation.

Why reusable: Future vector storage, schema validation, and index loops should continue to expose read-only vector views unless mutation semantics are deliberately introduced.

Suggested memory targets: core.value.vector-representation, workspace.api.design

Source Slug: feature-1-value-type
Source Context: `.zero-memory/context/feature-1-value-type/context.md`
Source Sections: Design, Loop End
Related Files: `src/core/value.rs`

## DL-20260630-115938.344Z-schema-exact-names-before-sql-identifiers

Summary: Feature 2 keeps schema column-name lookup exact and case-sensitive because SQL identifier normalization is not implemented yet.

Durable details: `Schema::column_index` compares column names exactly. This avoids quietly importing SQLite/PostgreSQL identifier rules before the parser/binder layers exist. Duplicate column detection also uses exact names. A future SQL parser/binder loop should decide whether identifiers are case-insensitive, quoted, normalized, or preserved.

Why reusable: Table, insert, parser, and binder loops must not assume SQL-style identifier normalization already exists in `Schema`.

Suggested memory targets: core.schema.identifier-rules, sql.parser.future-semantics

Source Slug: feature-2-row-schema
Source Context: `.zero-memory/context/feature-2-row-schema/context.md`
Source Sections: Design, Loop End
Related Files: `src/core/schema.rs`
