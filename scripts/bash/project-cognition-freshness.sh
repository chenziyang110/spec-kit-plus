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
    if [[ "$configured" =~ ^[A-Za-z]:[\\/] ]]; then
        if command -v cygpath >/dev/null 2>&1; then
            configured="$(cygpath -u "$configured")"
        elif command -v wslpath >/dev/null 2>&1; then
            configured="$(wslpath -u "$configured")"
        else
            return 1
        fi
    elif [[ "$configured" != /* ]]; then
        configured="$REPO_ROOT/$configured"
    fi
    printf '%s\n' "$configured"
}

project_cognition_config_value() {
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
    argv = payload.get("project_cognition_launcher", {}).get("argv", [])
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
  const argv = payload?.project_cognition_launcher?.argv;
  if (Array.isArray(argv) && typeof argv[0] === "string") process.stdout.write(argv[0]);
} catch (_) {}
' "$config_path" 2>/dev/null
        return 0
    fi

    if command -v jq >/dev/null 2>&1; then
        jq -r '.project_cognition_launcher.argv[0] // empty' "$config_path" 2>/dev/null
        return 0
    fi

    # Last-resort parser for the deterministic pretty-printed config shape.
    # It intentionally extracts only the first argv string from the named object.
    awk '
        /"project_cognition_launcher"[[:space:]]*:/ { in_launcher = 1; next }
        in_launcher && /"argv"[[:space:]]*:/ { in_argv = 1; next }
        in_argv && match($0, /"([^"\\]|\\.)*"/) {
            value = substr($0, RSTART + 1, RLENGTH - 2)
            print value
            exit
        }
        in_launcher && /^[[:space:]]*}/ { exit }
    ' "$config_path" 2>/dev/null | sed -e 's#\\\\#\\#g' -e 's#\\/#/#g' -e 's#\\"#"#g'
}

project_cognition_config_bin() {
    local config_path="$REPO_ROOT/.specify/config.json"
    [[ -f "$config_path" ]] || return 1

    local configured
    configured="$(project_cognition_config_value "$config_path")"
    [[ -n "$configured" ]] || return 1
    configured="$(normalize_configured_path "$configured")" || return 1
    [[ -f "$configured" ]] || return 1
    printf '%s\n' "$configured"
}

project_cognition_bin() {
    if [[ -n "${PROJECT_COGNITION_BIN:-}" ]]; then
        printf '%s\n' "$PROJECT_COGNITION_BIN"
        return 0
    fi
    local configured
    if configured="$(project_cognition_config_bin)"; then
        printf '%s\n' "$configured"
        return 0
    fi
    if command -v project-cognition >/dev/null 2>&1; then
        command -v project-cognition
        return 0
    fi
    echo "Cannot run project-cognition: no usable project_cognition_launcher is pinned in .specify/config.json." >&2
    echo "Run the project-pinned Specify launcher with 'check', then 'integration repair'. Do not probe 'specify cognition' or 'specify project-cognition'." >&2
    return 127
}

run_project_cognition() {
    local bin
    bin="$(project_cognition_bin)" || return $?
    (cd "$REPO_ROOT" && "$bin" "$@")
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
