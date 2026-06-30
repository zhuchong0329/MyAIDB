---
name: feature-0-rust-skeleton
description: Feature 0 loop for creating the Rust project skeleton and verification gate.
---

# Feature 0: Rust Project Skeleton And Verification Gate

## Loop Start

Feature: Rust project skeleton and verification gate.

Goal: Initialize the minimal Rust project skeleton for MyAIDB so future feature loops can run consistent format, test, and lint checks.

Scope:

- Create a single Rust package at the project root.
- Add `Cargo.toml`.
- Add `src/lib.rs` as the database core entrypoint.
- Add `src/main.rs` as the executable entrypoint.
- Add a minimal smoke test.
- Keep dependency set empty unless Cargo itself requires metadata.
- Verify formatting, tests, and Clippy.

Out of Scope:

- Do not implement SQL parser, AST, binder, or executor.
- Do not implement `Value`, `Row`, `Schema`, `Table`, or `Catalog`.
- Do not implement `vector` type or vector distance functions.
- Do not implement model registry, embedding provider, autoEmbed, or semantic query syntax.
- Do not add network services, HTTP frameworks, async runtimes, or database persistence.

Design:

- Use a single root crate first, not a workspace, to keep Feature 0 minimal.
- Expose a tiny library API that proves `src/lib.rs` is usable from tests.
- Provide a tiny binary that prints project identity or accepts `--help`.
- Keep all names and behavior boring; this loop builds the rails, not the train.

Verification:

- `cargo fmt --check`
- `cargo test`
- `cargo clippy --all-targets --all-features -- -D warnings`
- If plain `cargo` is not visible in the current Windows session, use `%USERPROFILE%\.cargo\bin\cargo.exe` and record that Tooling Gap.

Expected Artifacts:

- `Cargo.toml`
- `src/lib.rs`
- `src/main.rs`
- `tests/smoke.rs` or equivalent minimal test
- Updated `.zero-memory/context/feature-0-rust-skeleton/context.md`

Done Definition:

- Rust project builds.
- Smoke test passes.
- Format check passes.
- Clippy passes with warnings denied.
- No database semantics are implemented early.
- The next loop can start with `Value` and the minimal type system.
- Verification results and any reusable learning are persisted to `.zero-memory`.

## Current Status

- Loop start persisted before implementation.
- Rust environment bootstrap files already exist: `README.md`, `rust-toolchain.toml`, `scripts/bootstrap.ps1`, `scripts/bootstrap.sh`.
- On this Windows session, Rust is installed but plain `cargo` may require terminal restart; absolute path verification is available under `%USERPROFILE%\.cargo\bin`.

## Loop End

Feature: Rust project skeleton and verification gate.

Completed:

- Created root Rust package `myaidb`.
- Added `Cargo.toml` and generated `Cargo.lock`.
- Added `src/lib.rs` with minimal project identity API.
- Added `src/main.rs` with minimal `--help` and `--version` CLI behavior.
- Added `tests/smoke.rs` to verify library and binary availability.
- Updated `README.md` and bootstrap scripts with platform linker requirements.

Tests:

- Passed: `%USERPROFILE%\.cargo\bin\cargo.exe fmt --check`
- Passed: `%USERPROFILE%\.cargo\bin\cargo.exe test`
- Passed: `%USERPROFILE%\.cargo\bin\cargo.exe clippy --all-targets --all-features -- -D warnings`
- Passed: PowerShell syntax parse for `scripts/bootstrap.ps1`

Failures:

- Tooling Gap: initial `cargo test` failed because Windows MSVC target could not find `link.exe`.
- Tooling Gap: `rust-lld.exe` did not solve the issue because Windows SDK import libraries such as `kernel32.lib` were missing.

Fixes:

- Installed Visual Studio Build Tools 2022 with the C++ workload and Windows SDK through `winget`.
- Updated `README.md` to document Windows and macOS linker requirements.
- Updated `scripts/bootstrap.ps1` to install/check Visual Studio Build Tools when possible.
- Updated `scripts/bootstrap.sh` to check macOS Xcode Command Line Tools and Linux C compiler availability.

Reusable Learning:

- Logged `DL-20260630-100004.638Z-windows-rust-msvc-linker` in `.zero-memory/daily/learning.2026-06-30.md`.

Next Loop:

- Start Feature 1: implement `Value` and the minimal type system.
