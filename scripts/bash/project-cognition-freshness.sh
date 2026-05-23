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

project_cognition_bin() {
    if [[ -n "${PROJECT_COGNITION_BIN:-}" ]]; then
        printf '%s\n' "$PROJECT_COGNITION_BIN"
        return 0
    fi
    if command -v project-cognition >/dev/null 2>&1; then
        command -v project-cognition
        return 0
    fi
    echo "Cannot run project-cognition: set PROJECT_COGNITION_BIN or install project-cognition on PATH." >&2
    return 127
}

run_project_cognition() {
    local bin
    bin="$(project_cognition_bin)" || return $?
    (cd "$REPO_ROOT" && "$bin" "$@")
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
