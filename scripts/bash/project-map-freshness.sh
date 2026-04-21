#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(CDPATH="" cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=common.sh
source "$SCRIPT_DIR/common.sh"

REPO_ROOT="${1:-$(get_repo_root)}"
COMMAND="${2:-check}"
REASON="${3:-}"

PROJECT_MAP_DIR="$(project_map_dir "$REPO_ROOT")"
STATUS_PATH="$(project_map_status_path "$REPO_ROOT")"
CANONICAL_MAP_FILES=(
    "$REPO_ROOT/PROJECT-HANDBOOK.md"
    "$REPO_ROOT/.specify/project-map/ARCHITECTURE.md"
    "$REPO_ROOT/.specify/project-map/STRUCTURE.md"
    "$REPO_ROOT/.specify/project-map/CONVENTIONS.md"
    "$REPO_ROOT/.specify/project-map/INTEGRATIONS.md"
    "$REPO_ROOT/.specify/project-map/WORKFLOWS.md"
    "$REPO_ROOT/.specify/project-map/TESTING.md"
    "$REPO_ROOT/.specify/project-map/OPERATIONS.md"
)

mkdir -p "$PROJECT_MAP_DIR"

ensure_canonical_map_files() {
    local missing=()
    local path
    for path in "${CANONICAL_MAP_FILES[@]}"; do
        if [[ ! -f "$path" ]]; then
            missing+=("$path")
        fi
    done

    if [[ "${#missing[@]}" -eq 0 ]]; then
        return 0
    fi

    echo "Cannot record a fresh project-map baseline because canonical map files are missing:" >&2
    printf ' - %s\n' "${missing[@]}" >&2
    echo "Run map-codebase first so PROJECT-HANDBOOK.md and .specify/project-map/*.md exist." >&2
    return 1
}

iso_now() {
    date -u +"%Y-%m-%dT%H:%M:%SZ"
}

git_head_commit() {
    if has_git; then
        git -C "$REPO_ROOT" rev-parse HEAD 2>/dev/null || true
    fi
}

git_branch_name() {
    if has_git; then
        git -C "$REPO_ROOT" rev-parse --abbrev-ref HEAD 2>/dev/null || true
    fi
}

read_status_field() {
    local field="$1"
    if [[ ! -f "$STATUS_PATH" ]]; then
        return 0
    fi

    if command -v python3 >/dev/null 2>&1; then
        STATUS_PATH="$STATUS_PATH" FIELD="$field" python3 - <<'PY'
import json, os, sys
path = os.environ["STATUS_PATH"]
field = os.environ["FIELD"]
try:
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
except Exception:
    sys.exit(0)
value = data.get(field, "")
if isinstance(value, bool):
    print("true" if value else "false")
elif isinstance(value, (list, dict)):
    print(json.dumps(value, ensure_ascii=False))
elif value is None:
    print("")
else:
    print(str(value))
PY
        return 0
    fi

    grep -o "\"$field\"[[:space:]]*:[[:space:]]*\"[^\"]*\"" "$STATUS_PATH" 2>/dev/null | sed -E "s/.*:[[:space:]]*\"(.*)\"/\1/" | head -n1 || true
}

read_status_array() {
    local field="$1"
    if [[ ! -f "$STATUS_PATH" ]]; then
        echo "[]"
        return 0
    fi

    if command -v python3 >/dev/null 2>&1; then
        STATUS_PATH="$STATUS_PATH" FIELD="$field" python3 - <<'PY'
import json, os, sys
path = os.environ["STATUS_PATH"]
field = os.environ["FIELD"]
try:
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
except Exception:
    print("[]")
    sys.exit(0)
value = data.get(field, [])
if not isinstance(value, list):
    value = []
print(json.dumps(value, ensure_ascii=False))
PY
        return 0
    fi

    echo "[]"
}

write_status() {
    local last_mapped_commit="$1"
    local last_mapped_at="$2"
    local last_mapped_branch="$3"
    local freshness="$4"
    local last_refresh_reason="$5"
    local dirty="$6"
    local dirty_reasons_json="$7"

    cat > "$STATUS_PATH" <<EOF
{
  "version": 1,
  "last_mapped_commit": "$(json_escape "$last_mapped_commit")",
  "last_mapped_at": "$(json_escape "$last_mapped_at")",
  "last_mapped_branch": "$(json_escape "$last_mapped_branch")",
  "freshness": "$(json_escape "$freshness")",
  "last_refresh_reason": "$(json_escape "$last_refresh_reason")",
  "dirty": $dirty,
  "dirty_reasons": $dirty_reasons_json
}
EOF
}

classify_path() {
    local path="$1"
    local lower
    lower="$(printf '%s' "$path" | tr '[:upper:]' '[:lower:]')"

    case "$lower" in
        .specify/project-map/status.json)
            echo "ignore"
            return 0
            ;;
        project-handbook.md|\
        .specify/project-map/*|\
        .specify/templates/project-map/*|\
        .specify/templates/project-handbook-template.md|\
        .specify/memory/constitution.md|\
        .specify/extensions.yml|\
        .github/workflows/*|\
        package.json|package-lock.json|pnpm-lock.yaml|yarn.lock|\
        pyproject.toml|poetry.lock|go.mod|go.sum|cargo.toml|cargo.lock|\
        composer.json|composer.lock|gemfile|gemfile.lock|\
        dockerfile|docker-compose.yml|docker-compose.yaml|makefile)
            echo "stale"
            return 0
            ;;
    esac

    if [[ "$lower" =~ (^|/)(route|routes|router|routing|url|urls|endpoint|endpoints|api|schema|schemas|contract|contracts|type|types|interface|interfaces|registry|registries|manifest|manifests|config|configs|settings|workflow|workflows|command|commands|integration|integrations|adapter|adapters|middleware|export|exports|index)(/|\.|$) ]]; then
        echo "stale"
        return 0
    fi

    if [[ "$lower" =~ (^|/)(src|app|apps|server|client|web|ui|frontend|backend|lib|libs|scripts|tests|docs|specs)(/|$) ]]; then
        echo "possibly_stale"
        return 0
    fi

    echo "ignore"
}

json_array_from_lines() {
    if command -v python3 >/dev/null 2>&1; then
        python3 - <<'PY'
import json, sys
lines = [line.rstrip("\n") for line in sys.stdin if line.rstrip("\n")]
print(json.dumps(lines, ensure_ascii=False))
PY
        return 0
    fi

    local first=true
    printf '['
    while IFS= read -r line; do
        [[ -n "$line" ]] || continue
        if [[ "$first" == true ]]; then
            first=false
        else
            printf ', '
        fi
        printf '"%s"' "$(json_escape "$line")"
    done
    printf ']'
}

append_reason_json() {
    local existing_json="$1"
    local new_reason="$2"
    if command -v python3 >/dev/null 2>&1; then
        EXISTING_JSON="$existing_json" NEW_REASON="$new_reason" python3 - <<'PY'
import json, os
existing = os.environ["EXISTING_JSON"]
reason = os.environ["NEW_REASON"]
try:
    data = json.loads(existing) if existing else []
except Exception:
    data = []
if reason and reason not in data:
    data.append(reason)
print(json.dumps(data, ensure_ascii=False))
PY
        return 0
    fi

    printf '["%s"]' "$(json_escape "$new_reason")"
}

emit_check_json() {
    local freshness="$1"
    local head_commit="$2"
    local last_mapped_commit="$3"
    local dirty="$4"
    local dirty_reasons_json="$5"
    local reasons_json="$6"
    local changed_files_json="$7"

    cat <<EOF
{
  "status_path": "$(json_escape "$STATUS_PATH")",
  "freshness": "$(json_escape "$freshness")",
  "head_commit": "$(json_escape "$head_commit")",
  "last_mapped_commit": "$(json_escape "$last_mapped_commit")",
  "dirty": $dirty,
  "dirty_reasons": $dirty_reasons_json,
  "reasons": $reasons_json,
  "changed_files": $changed_files_json
}
EOF
}

run_check() {
    local head_commit last_mapped_commit dirty dirty_reasons_json
    head_commit="$(git_head_commit)"

    if [[ ! -f "$STATUS_PATH" ]]; then
        emit_check_json "missing" "$head_commit" "" "false" "[]" '["project-map status missing"]' "[]"
        return 0
    fi

    last_mapped_commit="$(read_status_field "last_mapped_commit")"
    dirty="$(read_status_field "dirty")"
    dirty_reasons_json="$(read_status_array "dirty_reasons")"
    [[ -n "$dirty" ]] || dirty="false"

    if [[ "$dirty" == "true" ]]; then
        emit_check_json "stale" "$head_commit" "$last_mapped_commit" "true" "$dirty_reasons_json" "$dirty_reasons_json" "[]"
        return 0
    fi

    if [[ -z "$last_mapped_commit" || -z "$head_commit" ]]; then
        emit_check_json "possibly_stale" "$head_commit" "$last_mapped_commit" "false" "$dirty_reasons_json" '["git baseline unavailable for project-map freshness"]' "[]"
        return 0
    fi

    if ! has_git; then
        emit_check_json "possibly_stale" "$head_commit" "$last_mapped_commit" "false" "$dirty_reasons_json" '["git baseline unavailable for project-map freshness"]' "[]"
        return 0
    fi

    local diff_output
    diff_output="$(
        {
            git -C "$REPO_ROOT" diff --name-status --find-renames "$last_mapped_commit..$head_commit" 2>/dev/null || true
            git -C "$REPO_ROOT" diff --name-status --find-renames --cached 2>/dev/null || true
            git -C "$REPO_ROOT" diff --name-status --find-renames 2>/dev/null || true
            git -C "$REPO_ROOT" ls-files --others --exclude-standard 2>/dev/null | sed 's/^/??\t/' || true
        } | awk '!seen[$0]++'
    )"
    if [[ -z "$diff_output" ]]; then
        emit_check_json "fresh" "$head_commit" "$last_mapped_commit" "false" "$dirty_reasons_json" "[]" "[]"
        return 0
    fi

    local worst="fresh"
    local reasons=()
    local changed_files=()

    while IFS=$'\t' read -r status path1 path2; do
        [[ -n "$status" ]] || continue
        local candidate_path="$path1"
        if [[ "$status" == R* && -n "${path2:-}" ]]; then
            candidate_path="$path2"
        fi

        changed_files+=("$candidate_path")
        local classification
        classification="$(classify_path "$candidate_path")"

        if [[ "$classification" == "stale" ]]; then
            worst="stale"
            reasons+=("high-impact project-map change: $candidate_path")
        elif [[ "$classification" == "possibly_stale" && "$worst" != "stale" ]]; then
            worst="possibly_stale"
            reasons+=("codebase surface changed since last map: $candidate_path")
        fi
    done <<< "$diff_output"

    local reasons_json changed_files_json
    reasons_json="$(printf '%s\n' "${reasons[@]}" | json_array_from_lines)"
    changed_files_json="$(printf '%s\n' "${changed_files[@]}" | json_array_from_lines)"

    if [[ "$changed_files_json" == "[]" && "$reasons_json" == "[]" ]]; then
        worst="fresh"
    fi

    if [[ "$worst" == "fresh" ]]; then
        reasons_json="[]"
    fi

    emit_check_json "$worst" "$head_commit" "$last_mapped_commit" "false" "$dirty_reasons_json" "$reasons_json" "$changed_files_json"
}

record_refresh() {
    local reason="${REASON:-manual}"
    ensure_canonical_map_files
    local head_commit branch now
    head_commit="$(git_head_commit)"
    branch="$(git_branch_name)"
    now="$(iso_now)"
    write_status "$head_commit" "$now" "$branch" "fresh" "$reason" "false" "[]"
    run_check
}

mark_dirty() {
    local reason="${REASON:-project-map-dirty}"
    local last_mapped_commit last_mapped_at last_mapped_branch last_refresh_reason dirty_reasons_json
    last_mapped_commit="$(read_status_field "last_mapped_commit")"
    last_mapped_at="$(read_status_field "last_mapped_at")"
    last_mapped_branch="$(read_status_field "last_mapped_branch")"
    last_refresh_reason="$(read_status_field "last_refresh_reason")"
    dirty_reasons_json="$(append_reason_json "$(read_status_array "dirty_reasons")" "$reason")"

    if [[ -z "$last_mapped_at" ]]; then
        last_mapped_at="$(iso_now)"
    fi
    if [[ -z "$last_refresh_reason" ]]; then
        last_refresh_reason="manual"
    fi

    write_status "$last_mapped_commit" "$last_mapped_at" "$last_mapped_branch" "stale" "$last_refresh_reason" "true" "$dirty_reasons_json"
    run_check
}

clear_dirty() {
    local last_mapped_commit last_mapped_at last_mapped_branch last_refresh_reason
    last_mapped_commit="$(read_status_field "last_mapped_commit")"
    last_mapped_at="$(read_status_field "last_mapped_at")"
    last_mapped_branch="$(read_status_field "last_mapped_branch")"
    last_refresh_reason="$(read_status_field "last_refresh_reason")"
    write_status "$last_mapped_commit" "$last_mapped_at" "$last_mapped_branch" "fresh" "$last_refresh_reason" "false" "[]"
    run_check
}

case "$COMMAND" in
    check)
        run_check
        ;;
    record-refresh|complete-refresh)
        if [[ "$COMMAND" == "complete-refresh" && -z "$REASON" ]]; then
            REASON="map-codebase"
        fi
        record_refresh
        ;;
    mark-dirty)
        mark_dirty
        ;;
    clear-dirty)
        clear_dirty
        ;;
    *)
        echo "Usage: project-map-freshness.sh [repo_root] {check|record-refresh|complete-refresh|mark-dirty|clear-dirty} [reason]" >&2
        exit 1
        ;;
esac
