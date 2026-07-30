#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="${1:-.}"
MODE="${2:-status}"
RUN_SLUG="${3:-}"

RUNTIME_BIN="${SPECIFY_RUNTIME_BIN:-$PROJECT_ROOT/.specify/bin/specify-runtime}"
if [[ -z "${SPECIFY_RUNTIME_BIN:-}" && ! -x "$RUNTIME_BIN" && -x "$RUNTIME_BIN.exe" ]]; then
  RUNTIME_BIN="$RUNTIME_BIN.exe"
elif [[ ! -x "$RUNTIME_BIN" ]]; then
  RUNTIME_BIN="$(command -v specify-runtime || true)"
fi

if [[ -z "$RUNTIME_BIN" ]]; then
  echo "specify-runtime not found; install the project-local runtime first" >&2
  exit 1
fi

case "$MODE" in
  status-build)
    exec "$RUNTIME_BIN" prd-build status-build "$RUN_SLUG" --project-root "$PROJECT_ROOT" --format json
    ;;
  init|status|init-scan|status-scan|finalize|finalize-scan)
    exec "$RUNTIME_BIN" prd-scan "$MODE" "$RUN_SLUG" --project-root "$PROJECT_ROOT" --format json
    ;;
  *)
    echo "unsupported PRD mode: $MODE" >&2
    exit 2
    ;;
esac
