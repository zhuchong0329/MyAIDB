#!/usr/bin/env bash
set -euo pipefail

echo "==> MyAIDB environment bootstrap (macOS/Linux)"

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

echo "==> Installing or updating the pinned Rust toolchain"
rustup toolchain install stable --component rustfmt --component clippy
rustup component add rustfmt clippy --toolchain stable

echo "==> Active versions"
rustc --version
cargo --version
rustup --version

echo "==> Bootstrap complete"
