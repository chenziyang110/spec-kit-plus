#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

find_workspace_root() {
  local current="${SCRIPT_DIR}"
  while [[ "${current}" != "/" ]]; do
    if [[ -f "${current}/extensions/agent-teams/engine/package.json" ]]; then
      printf '%s\n' "${current}"
      return 0
    fi
    if [[ -d "${current}/.specify" || -f "${current}/pyproject.toml" ]]; then
      printf '%s\n' "${current}"
      return 0
    fi
    current="$(dirname "${current}")"
  done
  printf '%s\n' "$(pwd)"
}

REPO_ROOT="$(find_workspace_root)"
ENGINE_DIR="${REPO_ROOT}/extensions/agent-teams/engine"
DIST_CLI="${ENGINE_DIR}/dist/cli/index.js"

print_usage() {
  cat <<'EOF'
Refresh Codex config and managed MCP servers using the OMX setup flow.

Usage:
  scripts/bash/sync-ecc-to-codex.sh [--dry-run] [--scope project|user] [additional omx setup args]

Examples:
  scripts/bash/sync-ecc-to-codex.sh --dry-run
  scripts/bash/sync-ecc-to-codex.sh --scope project
EOF
}

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  print_usage
  exit 0
fi

if command -v omx >/dev/null 2>&1; then
  exec omx setup "$@"
fi

if ! command -v node >/dev/null 2>&1; then
  echo "error: node is required when 'omx' is not installed on PATH." >&2
  echo "hint: install the global omx CLI or install Node.js and rerun this script." >&2
  exit 1
fi

if [[ ! -f "${ENGINE_DIR}/package.json" ]]; then
  echo "error: 'omx' is not installed on PATH and no bundled engine checkout was found near ${REPO_ROOT}." >&2
  echo "hint: install the global omx CLI or run this script from the spec-kit-plus repository root." >&2
  exit 1
fi

if [[ ! -f "${DIST_CLI}" ]]; then
  if ! command -v npm >/dev/null 2>&1; then
    echo "error: bundled OMX CLI is not built and npm is unavailable to build it." >&2
    echo "hint: install npm, run 'npm --prefix extensions/agent-teams/engine run build', then retry." >&2
    exit 1
  fi

  echo "Bundled OMX CLI not built; running npm build first..." >&2
  npm --prefix "${ENGINE_DIR}" run build >/dev/null
fi

exec node "${DIST_CLI}" setup "$@"
