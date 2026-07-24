#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(CDPATH="" cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=common.sh
source "$SCRIPT_DIR/common.sh"

REPO_ROOT="${1:-$(get_repo_root)}"
COMMAND="${2:-check}"
REASON="${3:-}"
ORIGIN_COMMAND="${4:-}"
ORIGIN_FEATURE_DIR="${5:-}"
ORIGIN_LANE_ID="${6:-}"
DIRTY_SCOPE_PATHS_JSON="${7:-[]}"

usage() {
    echo "Usage: $(basename "$0") [repo_root] {check|status|record-refresh|complete-refresh|mark-dirty|clear-dirty|refresh-topics} [reason] [origin_command] [origin_feature_dir] [origin_lane_id] [dirty_scope_paths_json]" >&2
}

normalize_configured_path() {
    local configured="$1"
    configured="${configured//\\//}"
    configured="${configured#./}"
    [[ "$configured" == .specify/bin/* ]] || return 1
    local executable_name="${configured#.specify/bin/}"
    [[ -n "$executable_name" && "$executable_name" != */* && "$executable_name" != "." && "$executable_name" != ".." ]] || return 1
    printf '%s\n' "$REPO_ROOT/$configured"
}

specify_runtime_config_value() {
    local config_path="$1"
    local candidate
    for candidate in python3 python; do
        if command -v "$candidate" >/dev/null 2>&1; then
            "$candidate" - "$config_path" <<'PY' 2>/dev/null
import json
import pathlib
import sys

try:
    payload = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
    argv = payload.get("runtime_launcher", {}).get("argv", [])
    if isinstance(argv, list) and argv and isinstance(argv[0], str):
        print(argv[0])
except (OSError, ValueError, TypeError):
    pass
PY
            return 0
        fi
    done

    if command -v node >/dev/null 2>&1; then
        node -e '
const fs = require("fs");
try {
  const payload = JSON.parse(fs.readFileSync(process.argv[1], "utf8"));
  const argv = payload?.runtime_launcher?.argv;
  if (Array.isArray(argv) && typeof argv[0] === "string") process.stdout.write(argv[0]);
} catch (_) {}
' "$config_path" 2>/dev/null
        return 0
    fi

    if command -v jq >/dev/null 2>&1; then
        jq -r '.runtime_launcher.argv[0] // empty' "$config_path" 2>/dev/null
        return 0
    fi

    # Last-resort parser for the deterministic pretty-printed config shape.
    # It intentionally extracts only the first argv string from the named object.
    awk '
        /"runtime_launcher"[[:space:]]*:/ { in_launcher = 1; next }
        in_launcher && /"argv"[[:space:]]*:/ { in_argv = 1; next }
        in_argv && match($0, /"([^"\\]|\\.)*"/) {
            value = substr($0, RSTART + 1, RLENGTH - 2)
            print value
            exit
        }
        in_launcher && /^[[:space:]]*}/ { exit }
    ' "$config_path" 2>/dev/null | sed -e 's#\\\\#\\#g' -e 's#\\/#/#g' -e 's#\\"#"#g'
}

specify_runtime_config_bin() {
    local config_path="$REPO_ROOT/.specify/config.json"
    [[ -f "$config_path" ]] || return 1

    local configured
    configured="$(specify_runtime_config_value "$config_path")"
    [[ -n "$configured" ]] || return 1
    configured="$(normalize_configured_path "$configured")" || return 1
    [[ -f "$configured" ]] || return 1
    printf '%s\n' "$configured"
}

specify_runtime_bin() {
    local configured
    if configured="$(specify_runtime_config_bin)"; then
        printf '%s\n' "$configured"
        return 0
    fi
    local project_runtime
    for project_runtime in \
        "$REPO_ROOT/.specify/bin/specify-runtime" \
        "$REPO_ROOT/.specify/bin/specify-runtime.exe"; do
        if [[ -f "$project_runtime" ]]; then
            printf '%s\n' "$project_runtime"
            return 0
        fi
    done
    echo "Cannot run project cognition: the project-local .specify/bin/specify-runtime binding is unavailable." >&2
    echo "A human must rerun the trusted Specify bootstrap/upgrade flow; agent helpers do not fall back to SPECIFY_RUNTIME_BIN or PATH." >&2
    return 127
}

run_project_cognition() {
    local bin
    bin="$(specify_runtime_bin)" || return $?
    (cd "$REPO_ROOT" && "$bin" cognition "$@")
}

parse_dirty_scope_paths() {
    local payload="$1"
    local candidate

    for candidate in python3 python; do
        if command -v "$candidate" >/dev/null 2>&1; then
            "$candidate" - "$payload" <<'PY'
import json
import sys

try:
    payload = json.loads(sys.argv[1])
except (TypeError, ValueError) as exc:
    print(f"Dirty scope paths JSON is invalid: {exc}", file=sys.stderr)
    raise SystemExit(2)

if not isinstance(payload, list) or any(
    not isinstance(item, str) or not item.strip() or "\n" in item or "\r" in item
    for item in payload
):
    print("Dirty scope paths JSON must be an array of non-empty single-line strings.", file=sys.stderr)
    raise SystemExit(2)

for item in payload:
    print(item)
PY
            return $?
        fi
    done

    if command -v node >/dev/null 2>&1; then
        node -e '
let payload;
try {
  payload = JSON.parse(process.argv[1]);
} catch (error) {
  process.stderr.write(`Dirty scope paths JSON is invalid: ${error.message}\n`);
  process.exit(2);
}
if (!Array.isArray(payload) || payload.some((item) => typeof item !== "string" || !item.trim() || /[\r\n]/.test(item))) {
  process.stderr.write("Dirty scope paths JSON must be an array of non-empty single-line strings.\n");
  process.exit(2);
}
for (const item of payload) process.stdout.write(`${item}\n`);
' "$payload"
        return $?
    fi

    if command -v jq >/dev/null 2>&1; then
        jq -r '
            if type != "array" then
                error("Dirty scope paths JSON must be an array of non-empty single-line strings.")
            elif any(.[]; type != "string" or test("^[[:space:]]*$") or test("[\\r\\n]")) then
                error("Dirty scope paths JSON must be an array of non-empty single-line strings.")
            else
                .[]
            end
        ' <<< "$payload"
        return $?
    fi

    echo "Cannot parse dirty scope paths JSON: install Python, Node.js, or jq." >&2
    return 2
}

build_mark_dirty_args() {
    _mark_dirty_args=("mark-dirty")
    if [[ -n "$REASON" ]]; then
        _mark_dirty_args+=("--reason" "$REASON")
    fi
    if [[ -n "$ORIGIN_COMMAND" ]]; then
        _mark_dirty_args+=("--origin-command" "$ORIGIN_COMMAND")
    fi
    if [[ -n "$ORIGIN_FEATURE_DIR" ]]; then
        _mark_dirty_args+=("--origin-feature-dir" "$ORIGIN_FEATURE_DIR")
    fi
    if [[ -n "$ORIGIN_LANE_ID" ]]; then
        _mark_dirty_args+=("--origin-lane-id" "$ORIGIN_LANE_ID")
    fi

    local scope_output
    scope_output="$(parse_dirty_scope_paths "$DIRTY_SCOPE_PATHS_JSON")" || return $?
    if [[ -n "$scope_output" ]]; then
        local scope_path
        while IFS= read -r scope_path; do
            _mark_dirty_args+=("--scope" "$scope_path")
        done <<< "$scope_output"
    fi
    _mark_dirty_args+=("--format" "json")
}

case "$COMMAND" in
    check)
        run_project_cognition check --format json
        ;;
    status)
        run_project_cognition status --format json
        ;;
    record-refresh)
        run_project_cognition record-refresh --reason "${REASON:-manual}" --format json
        ;;
    complete-refresh)
        run_project_cognition complete-refresh --format json
        ;;
    mark-dirty)
        if [[ -z "$REASON" ]]; then
            echo "mark-dirty requires a reason." >&2
            usage
            exit 1
        fi
        build_mark_dirty_args || exit $?
        run_project_cognition "${_mark_dirty_args[@]}"
        ;;
    clear-dirty)
        run_project_cognition clear-dirty --format json
        ;;
    refresh-topics)
        if [[ -z "$REASON" ]]; then
            echo "refresh-topics requires topic arguments after the command." >&2
            usage
            exit 1
        fi
        # Keep the legacy helper's positional contract lightweight: pass the third
        # field as a comma-separated topic list when callers use this wrapper.
        IFS=',' read -r -a _topics <<< "$REASON"
        run_project_cognition refresh-topics "${_topics[@]}" --format json
        ;;
    *)
        usage
        exit 1
        ;;
esac
