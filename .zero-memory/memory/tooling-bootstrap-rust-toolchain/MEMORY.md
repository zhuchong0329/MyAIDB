---
id: tooling.bootstrap.rust-toolchain
name: tooling-bootstrap-rust-toolchain
description: Keep MyAIDB Rust bootstrap scripts executable, rustup-based, and synchronized with rust-toolchain.toml.
tags:
  - tooling
  - rust
  - bootstrap
pattern_key: tooling.bootstrap.rust-toolchain-script
component: tooling
kind: best-practice
stage: implementation
scope: project
actionability: reference-only
layer: detailed
status: active
last_updated_at: 2026-07-01T02:48:23Z
freshness_profile: code-env
source_daily_learning_ids:
  - DL-20260701-024823.000Z-macos-bootstrap-rust-toolchain
recurrence_count: 1
last_confirmed_at: 2026-07-01T02:48:23Z
recent_confirmation_ids:
  - DL-20260701-024823.000Z-macos-bootstrap-rust-toolchain
load_next: []
related:
  - workspace.project.tooling
related_files:
  - README.md
  - rust-toolchain.toml
  - scripts/bootstrap.sh
related_symbols:
  - rustup
  - rustfmt
  - clippy
---

# Tooling Bootstrap Rust Toolchain

## Description

Use this memory when working on MyAIDB local environment setup, `scripts/bootstrap.sh`, README bootstrap instructions, or Rust toolchain installation behavior on macOS/Linux.

The concrete rule is that the shell bootstrap should be directly runnable from the README path, should install through `rustup`, and should derive the channel from `rust-toolchain.toml` so the script and project pin do not drift.

## Details

Verified on macOS: `./scripts/bootstrap.sh` failed with `permission denied` when the script lacked executable mode. Keep the executable bit set so the README command works after clone.

The script should source `$HOME/.cargo/env` before deciding rustup is missing. This handles terminals where rustup is already installed under `~/.cargo/bin` but PATH has not loaded it.

The script should parse `rust-toolchain.toml` for the channel instead of hardcoding `stable`. After that, use `rustup toolchain install "$TOOLCHAIN_CHANNEL" --component rustfmt --component clippy` and `rustup component add rustfmt clippy --toolchain "$TOOLCHAIN_CHANNEL"`.

## Source Extraction

Stable facts came from the 2026-07-01 macOS bootstrap task. Dropped details include transient rustup download progress and sandbox-specific permission output, except for the durable observation that real local setup writes to `~/.rustup` and `~/.cargo`.
