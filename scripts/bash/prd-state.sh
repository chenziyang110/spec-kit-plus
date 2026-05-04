#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SHARED_HELPER="$SCRIPT_DIR/../shared/prd-state.py"
PYTHON_BIN="${SPECIFY_PYTHON:-python}"

if [[ ! -f "$SHARED_HELPER" ]]; then
  echo "shared PRD helper not found: $SHARED_HELPER" >&2
  exit 1
fi

exec "$PYTHON_BIN" "$SHARED_HELPER" "${1:-.}" "${2:-status}" "${3:-}"
