#!/usr/bin/env bash
set -euo pipefail

echo "==> MyAIDB environment bootstrap (macOS/Linux)"

TOOLCHAIN_CHANNEL="$(sed -n 's/^[[:space:]]*channel[[:space:]]*=[[:space:]]*"\([^"]*\)".*/\1/p' rust-toolchain.toml | head -n 1)"

if [ -z "$TOOLCHAIN_CHANNEL" ]; then
  echo "Could not read the Rust toolchain channel from rust-toolchain.toml."
  exit 1
fi

case "$(uname -s)" in
  Darwin)
    if ! xcode-select -p >/dev/null 2>&1; then
      echo "Xcode Command Line Tools are required for the macOS linker."
      echo "Run: xcode-select --install"
      xcode-select --install || true
      exit 1
    fi
    ;;
  Linux)
    if ! command -v cc >/dev/null 2>&1; then
      echo "A C compiler/linker is required. Install your distro build tools, for example:"
      echo "  Debian/Ubuntu: sudo apt install build-essential"
      echo "  Fedora: sudo dnf groupinstall 'Development Tools'"
      exit 1
    fi
    ;;
esac

if ! command -v rustup >/dev/null 2>&1 && [ -f "$HOME/.cargo/env" ]; then
  # shellcheck disable=SC1090
  source "$HOME/.cargo/env"
fi

if ! command -v rustup >/dev/null 2>&1; then
  echo "==> rustup not found; installing Rustup"
  curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
  # shellcheck disable=SC1090
  source "$HOME/.cargo/env"
fi

if ! command -v rustup >/dev/null 2>&1; then
  echo "rustup is still not available in PATH."
  echo "Restart the terminal after installation, then rerun this script."
  exit 1
fi

echo "==> Installing or updating Rust toolchain: $TOOLCHAIN_CHANNEL"
rustup toolchain install "$TOOLCHAIN_CHANNEL" --component rustfmt --component clippy
rustup component add rustfmt clippy --toolchain "$TOOLCHAIN_CHANNEL"

echo "==> Active versions"
rustc --version
cargo --version
rustup --version

echo "==> Bootstrap complete"
