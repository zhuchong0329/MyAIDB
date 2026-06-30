# MyAIDB

MyAIDB is a learning-oriented single-node SQL database project for exploring autoEmbed-style semantic indexing, query execution, and loop engineering.

The project principles live in `PRINCIPLES.md`, the first-stage development plan lives in `DEVELOPMENT_PLAN.md`, and the feature-loop workflow lives in `LOOP_ENGINEERING.md`.

## Environment

MyAIDB uses Rust as the core implementation language.

Required tools:

- Rust toolchain managed by `rustup`
- Cargo
- `rustfmt`
- Clippy
- Git
- Platform linker toolchain:
  - Windows: Visual Studio Build Tools with the C++ workload and Windows SDK
  - macOS: Xcode Command Line Tools

The pinned Rust channel and required Rust components are declared in `rust-toolchain.toml`.

## Bootstrap

Run the bootstrap script for your platform from the project root.

Windows PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/bootstrap.ps1
```

macOS or Linux:

```bash
chmod +x scripts/bootstrap.sh
./scripts/bootstrap.sh
```

The bootstrap script will:

- Check whether `rustup` is installed.
- Check or install the platform linker toolchain when the script can do so safely.
- Install Rust through the standard platform path when possible.
- Install or update the pinned Rust toolchain.
- Install `rustfmt` and Clippy.
- Print the active Rust and Cargo versions.

After installing Rust for the first time, restart your terminal if `cargo` is still not found.

On Windows, `winget` may update the user PATH after the current terminal session has already started. If the bootstrap script succeeds but a new command still cannot find `cargo`, restart PowerShell, Windows Terminal, or the Codex session. The binaries are normally installed under `%USERPROFILE%\.cargo\bin`.

Windows Rust uses the MSVC target by default. If `cargo test` fails with `link.exe not found` or missing libraries such as `kernel32.lib`, install Visual Studio Build Tools with the C++ workload and Windows SDK. The Windows bootstrap script attempts this through `winget`, but the installer may take several minutes and may request a reboot.

On macOS, install Xcode Command Line Tools if the bootstrap script reports that they are missing:

```bash
xcode-select --install
```

## Daily Commands

Format check:

```bash
cargo fmt --check
```

Run tests:

```bash
cargo test
```

Run Clippy:

```bash
cargo clippy --all-targets --all-features -- -D warnings
```

When the Rust project skeleton exists, every feature loop should run at least the relevant tests plus the project-level quick checks above.

## Cross-Platform Notes

- Use `rustup` instead of OS package managers for the active Rust toolchain.
- Keep platform-specific setup inside `scripts/bootstrap.ps1` and `scripts/bootstrap.sh`.
- Do not commit local build output such as `target/`.
- Prefer deterministic local tests over network, GPU, or external model dependencies.
- Real embedding models should run behind a provider boundary and should not be required for core database tests.
