---
name: default
description: MyAIDB project default zero-memory context.
---

# Default Context

## Status

- zero-memory has been deployed for this workspace.
- Codex skills were copied into `.codex/skills`.
- Workspace memory data directories were initialized under `.zero-memory/`.
- Installation was completed manually because `bash` is not available in the current PowerShell environment.
- Verification passed: `AGENTS.md`, `.codex/skills`, `.zero-memory/`, and `.zero-memory/tmp/current-context.txt` are present.
- The local zero-memory source checkout under `extra/zero-agent-memory` is intentionally ignored by Git so public history does not expose private source metadata.

## Git Initialization

- Workspace root was initialized as a Git repository on branch `main`.
- zero-memory is not tracked as a submodule in the public repository; copied Codex skills are tracked directly under `.codex/skills`.
- Remote `origin` was set to `git@github.com:zhuchong0329/MyAIDB.git`.
- Public history was sanitized to avoid exposing private source repository metadata before pushing.
- Git author and committer metadata were changed to `zhuchong0329 <zhuchong0329@users.noreply.github.com>` for public-safe commits.
- Push is still pending because GitHub SSH returned `Permission denied (publickey)`.
- Alternative push path: HTTPS remote can be used instead of SSH, but GitHub requires a Personal Access Token or Git Credential Manager/browser login rather than account password.

## Project Anchors

- `PRINCIPLES.md` records the MyAIDB original principles.
- `DEVELOPMENT_PLAN.md` records the first-stage development plan.
- `LOOP_ENGINEERING.md` records the feature-level loop engineering workflow: agent autonomy to test-passing within one feature, verification, failure classification, and `.zero-memory` learning persistence.

## Current Planning

- Candidate first feature loop: create the Rust project skeleton and verification gate before implementing database semantics.
- Rationale: a strict loop engineering workflow needs reproducible commands, tests, formatting, and a minimal executable surface before feature loops such as `Value`, SQL parsing, or autoEmbed can be disciplined.
- Feature 0 completed: root Rust package, minimal lib/bin, smoke tests, and verification gate are in place. Next loop is Feature 1: `Value` and the minimal type system.
- Feature 1 completed: `Value` and `ValueType` are implemented under `src/core`, with `Vector(Vec<f32>)` exposed through read-only slice APIs. Next loop is Feature 2: `Row` and `Schema`.
- Feature 2 completed: `Row`, `Column`, `Schema`, and strict schema validation are implemented under `src/core`. Next loop is Feature 3: in-memory `Table`.
- Feature 3 completed: in-memory `Table` stores owned rows after schema validation, preserving row order and rejecting invalid rows without mutation. Next loop is Feature 4: `Catalog`.
- Feature 4 completed: in-memory `Catalog` owns multiple tables, supports exact-name create/insert/lookup, mutable table access, and insertion-order table-name listing. Next loop should start the SQL frontend boundary.
- Feature 5 completed: SQL frontend boundary parses a tiny SQL subset into AST without execution. It includes lexer/token/parser/AST support for `CREATE TABLE` and `INSERT INTO ... VALUES`, case-insensitive keywords, exact identifier preservation, `ValueType` column types, and SQL `Literal` insert values. Next loop should likely introduce binder/execution boundary decisions.

## Rust Environment

- Added `README.md`, `rust-toolchain.toml`, `scripts/bootstrap.ps1`, and `scripts/bootstrap.sh` for cross-platform Rust environment setup.
- Windows bootstrap installed Rustup through `winget`, then installed Rust stable with `rustfmt` and Clippy.
- Verified installed tools by absolute path under `%USERPROFILE%\.cargo\bin`: `rustc 1.96.0`, `cargo 1.96.0`, `rustup 1.29.0`.
- Current Codex PowerShell session still does not see `cargo` on PATH; restart the terminal/Codex session or reload PATH before using plain `cargo`.
- Reusable learning logged in `.zero-memory/daily/learning.2026-06-30.md` as `DL-20260630-092841.280Z-rust-path-refresh`.
