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

CONFIG_PATH="$REPO_ROOT/.specify/config.json"

usage() {
    echo "Usage: $(basename "$0") [repo_root] {check|status|record-refresh|complete-refresh|mark-dirty|clear-dirty|refresh-topics} [reason] [origin_command] [origin_feature_dir] [origin_lane_id] [dirty_scope_paths_json]" >&2
}

python_cmd() {
    if command -v python3 >/dev/null 2>&1; then
        command -v python3
        return 0
    fi
    if command -v python >/dev/null 2>&1; then
        command -v python
        return 0
    fi
    return 1
}

normalize_launcher_executable() {
    local executable="$1"
    if [[ "$executable" =~ ^[A-Za-z]:[\\/] ]]; then
        if command -v wslpath >/dev/null 2>&1; then
            wslpath -u "$executable"
            return 0
        fi
        if command -v cygpath >/dev/null 2>&1; then
            cygpath -u "$executable"
            return 0
        fi
        local drive rest drive_lower
        drive="${executable:0:1}"
        rest="${executable:3}"
        rest="${rest//\\//}"
        drive_lower="$(printf '%s' "$drive" | tr '[:upper:]' '[:lower:]')"
        if [[ -d "/mnt/$drive_lower" ]]; then
            printf '/mnt/%s/%s\n' "$drive_lower" "$rest"
        else
            printf '%s\n' "${executable//\\//}"
        fi
        return 0
    fi
    printf '%s\n' "$executable"
}

normalize_path_for_shell() {
    local path="$1"
    if [[ "$path" =~ ^[A-Za-z]:[\\/] ]]; then
        if command -v wslpath >/dev/null 2>&1; then
            wslpath -u "$path"
            return 0
        fi
        if command -v cygpath >/dev/null 2>&1; then
            cygpath -u "$path"
            return 0
        fi
        local drive rest drive_lower
        drive="${path:0:1}"
        rest="${path:3}"
        rest="${rest//\\//}"
        drive_lower="$(printf '%s' "$drive" | tr '[:upper:]' '[:lower:]')"
        if [[ -d "/mnt/$drive_lower" ]]; then
            printf '/mnt/%s/%s\n' "$drive_lower" "$rest"
        else
            printf '%s\n' "${path//\\//}"
        fi
        return 0
    fi
    printf '%s\n' "$path"
}

normalize_pythonpath_for_shell() {
    [[ -n "${PYTHONPATH:-}" ]] || return 0
    local IFS=';'
    local -a raw_parts=($PYTHONPATH)
    local -a normalized_parts=()
    local part
    for part in "${raw_parts[@]}"; do
        [[ -n "$part" ]] || continue
        normalized_parts+=("$(normalize_path_for_shell "$part")")
    done
    if [[ ${#normalized_parts[@]} -gt 0 ]]; then
        local joined
        joined="$(IFS=:; printf '%s' "${normalized_parts[*]}")"
        export PYTHONPATH="$joined"
    fi
}

launcher_argv_json() {
    local py
    py="$(python_cmd)" || return 1
    if [[ -f "$CONFIG_PATH" ]]; then
        CONFIG_PATH="$CONFIG_PATH" "$py" - <<'PY'
import json
import os
import sys

try:
    with open(os.environ["CONFIG_PATH"], "r", encoding="utf-8-sig") as fh:
        payload = json.load(fh)
except Exception:
    sys.exit(1)

launcher = payload.get("specify_launcher")
if not isinstance(launcher, dict):
    sys.exit(1)
argv = launcher.get("argv")
if not isinstance(argv, list) or not argv or not all(isinstance(item, str) and item for item in argv):
    sys.exit(1)
print(json.dumps(argv))
PY
        return $?
    fi
    return 1
}

run_project_cognition() {
    local -a launcher=()
    local argv_json=""
    local py=""

    if argv_json="$(launcher_argv_json 2>/dev/null)"; then
        if py="$(python_cmd)"; then
            while IFS= read -r item; do
                launcher+=("$item")
            done < <(ARGV_JSON="$argv_json" "$py" - <<'PY'
import json
import os

for item in json.loads(os.environ["ARGV_JSON"]):
    print(item)
PY
)
        fi
    fi

    if [[ ${#launcher[@]} -gt 0 ]]; then
        launcher[0]="$(normalize_launcher_executable "${launcher[0]}")"
        if [[ "${launcher[1]:-}" == "-m" && "${launcher[2]:-}" == "specify_cli" && ! -x "${launcher[0]}" ]]; then
            if py="$(python_cmd)"; then
                launcher[0]="$py"
            fi
        elif [[ "${launcher[1]:-}" == "-m" && "${launcher[2]:-}" == "specify_cli" && "${launcher[0]}" =~ ^/mnt/[A-Za-z]/ ]]; then
            if py="$(python_cmd)"; then
                launcher[0]="$py"
            fi
        fi
    fi

    if [[ ${#launcher[@]} -eq 0 ]]; then
        if command -v specify >/dev/null 2>&1; then
            launcher=(specify)
        else
            echo "Cannot run project-cognition: no specify launcher is configured in .specify/config.json and PATH specify is unavailable." >&2
            return 127
        fi
    fi

    normalize_pythonpath_for_shell
    (cd "$REPO_ROOT" && "${launcher[@]}" project-cognition "$@")
}

mark_dirty_args() {
    local -a args=("mark-dirty")
    if [[ -n "$REASON" ]]; then
        args+=("--reason" "$REASON")
    fi
    if [[ -n "$ORIGIN_COMMAND" ]]; then
        args+=("--origin-command" "$ORIGIN_COMMAND")
    fi
    if [[ -n "$ORIGIN_FEATURE_DIR" ]]; then
        args+=("--origin-feature-dir" "$ORIGIN_FEATURE_DIR")
    fi
    if [[ -n "$ORIGIN_LANE_ID" ]]; then
        args+=("--origin-lane-id" "$ORIGIN_LANE_ID")
    fi
    args+=("--format" "json")
    printf '%s\n' "${args[@]}"
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
        readarray -t _mark_dirty_args < <(mark_dirty_args)
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
