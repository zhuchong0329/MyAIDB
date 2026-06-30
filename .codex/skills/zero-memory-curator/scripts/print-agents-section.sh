#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: print-agents-section.sh [--agents-file PATH] <section-title>

Print one `## <section-title>` section from an AGENTS.md file.
When --agents-file is omitted, the script searches upward from the current
directory and then falls back to this repository's AGENTS.md.
EOF
}

agents_file=""
if [[ "${1:-}" == "--agents-file" ]]; then
  agents_file="${2:-}"
  shift 2
fi

section="${1:-}"
if [[ -z "$section" ]]; then
  usage >&2
  exit 64
fi

if [[ -z "$agents_file" ]]; then
  search_dir="$PWD"
  while [[ "$search_dir" != "/" ]]; do
    if [[ -f "$search_dir/AGENTS.md" ]]; then
      agents_file="$search_dir/AGENTS.md"
      break
    fi
    search_dir="$(dirname "$search_dir")"
  done
fi

if [[ -z "$agents_file" ]]; then
  script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  repo_agents="$(cd "$script_dir/../../.." && pwd)/AGENTS.md"
  if [[ -f "$repo_agents" ]]; then
    agents_file="$repo_agents"
  fi
fi

if [[ -z "$agents_file" || ! -f "$agents_file" ]]; then
  echo "AGENTS.md not found" >&2
  exit 66
fi

awk -v wanted="$section" '
  $0 == "## " wanted {
    in_section = 1
    found = 1
  }
  in_section && /^## / && $0 != "## " wanted {
    exit
  }
  in_section {
    print
  }
  END {
    if (!found) {
      exit 2
    }
  }
' "$agents_file"
