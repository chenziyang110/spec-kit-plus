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
LEGACY_STATUS_PATH="$(legacy_project_map_status_path "$REPO_ROOT")"
CANONICAL_MAP_FILES=(
    "$REPO_ROOT/PROJECT-HANDBOOK.md"
    "$REPO_ROOT/.specify/project-map/index/atlas-index.json"
    "$REPO_ROOT/.specify/project-map/index/modules.json"
    "$REPO_ROOT/.specify/project-map/index/relations.json"
    "$REPO_ROOT/.specify/project-map/root/ARCHITECTURE.md"
    "$REPO_ROOT/.specify/project-map/root/STRUCTURE.md"
    "$REPO_ROOT/.specify/project-map/root/CONVENTIONS.md"
    "$REPO_ROOT/.specify/project-map/root/INTEGRATIONS.md"
    "$REPO_ROOT/.specify/project-map/root/WORKFLOWS.md"
    "$REPO_ROOT/.specify/project-map/root/TESTING.md"
    "$REPO_ROOT/.specify/project-map/root/OPERATIONS.md"
)

mkdir -p "$PROJECT_MAP_DIR"
mkdir -p "$(dirname "$STATUS_PATH")"

status_read_path() {
    if [[ -f "$STATUS_PATH" ]]; then
        echo "$STATUS_PATH"
        return 0
    fi
    if [[ -f "$LEGACY_STATUS_PATH" ]]; then
        echo "$LEGACY_STATUS_PATH"
        return 0
    fi
    echo "$STATUS_PATH"
}

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
    echo "Run /sp-map-scan, then /sp-map-build first so PROJECT-HANDBOOK.md and .specify/project-map/*.md exist." >&2
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
    local read_path
    read_path="$(status_read_path)"
    if [[ ! -f "$read_path" ]]; then
        return 0
    fi

    if command -v python3 >/dev/null 2>&1; then
        STATUS_READ_PATH="$read_path" FIELD="$field" python3 - <<'PY'
import json, os, sys
path = os.environ["STATUS_READ_PATH"]
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

    grep -o "\"$field\"[[:space:]]*:[[:space:]]*\"[^\"]*\"" "$read_path" 2>/dev/null | sed -E "s/.*:[[:space:]]*\"(.*)\"/\1/" | head -n1 || true
}

read_status_array() {
    local field="$1"
    local read_path
    read_path="$(status_read_path)"
    if [[ ! -f "$read_path" ]]; then
        echo "[]"
        return 0
    fi

    if command -v python3 >/dev/null 2>&1; then
        STATUS_READ_PATH="$read_path" FIELD="$field" python3 - <<'PY'
import json, os, sys
path = os.environ["STATUS_READ_PATH"]
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
    local last_refresh_topics_json="$6"
    local last_refresh_scope="$7"
    local last_refresh_basis="$8"
    local last_refresh_changed_files_basis_json="$9"
    local dirty="${10}"
    local dirty_reasons_json="${11}"

    local payload
    payload="$(cat <<EOF
{
  "version": 1,
  "last_mapped_commit": "$(json_escape "$last_mapped_commit")",
  "last_mapped_at": "$(json_escape "$last_mapped_at")",
  "last_mapped_branch": "$(json_escape "$last_mapped_branch")",
  "freshness": "$(json_escape "$freshness")",
  "last_refresh_reason": "$(json_escape "$last_refresh_reason")",
  "last_refresh_topics": $last_refresh_topics_json,
  "last_refresh_scope": "$(json_escape "$last_refresh_scope")",
  "last_refresh_basis": "$(json_escape "$last_refresh_basis")",
  "last_refresh_changed_files_basis": $last_refresh_changed_files_basis_json,
  "dirty": $dirty,
  "dirty_reasons": $dirty_reasons_json
}
EOF
)"
    printf '%s\n' "$payload" > "$STATUS_PATH"
    if [[ "$LEGACY_STATUS_PATH" != "$STATUS_PATH" ]]; then
        mkdir -p "$(dirname "$LEGACY_STATUS_PATH")"
        printf '%s\n' "$payload" > "$LEGACY_STATUS_PATH"
    fi
}

classify_path() {
    local path="$1"
    local lower
    lower="$(printf '%s' "$path" | tr '[:upper:]' '[:lower:]')"

    case "$lower" in
        .specify/project-map/status.json|\
        .specify/project-map/index/status.json|\
        .specify/project-map/map-state.md|\
        .specify/project-map/worker-results/*)
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

refresh_plan_for_path() {
    local path="$1"
    local lower
    lower="$(printf '%s' "$path" | tr '[:upper:]' '[:lower:]' | tr '\\' '/')"
    local must_refresh=()
    local review=()
    local specific_boundary_hit=false
    local classification
    classification="$(classify_path "$path")"
    [[ "$classification" == "ignore" ]] && {
        printf '{"must_refresh_topics":[],"review_topics":[]}\n'
        return 0
    }

    add_topic() {
        local target_name="$1"
        shift
        local topic
        for topic in "$@"; do
            local -n target_ref="$target_name"
            local existing
            for existing in "${target_ref[@]:-}"; do
                [[ "$existing" == "$topic" ]] && continue 2
            done
            target_ref+=("$topic")
        done
    }

    ordered_json_array() {
        local -n source_ref="$1"
        local ordered=(
            "ARCHITECTURE.md"
            "STRUCTURE.md"
            "CONVENTIONS.md"
            "INTEGRATIONS.md"
            "OPERATIONS.md"
            "WORKFLOWS.md"
            "TESTING.md"
        )
        local out=()
        local topic="$1"
        local item
        for topic in "${ordered[@]}"; do
            for item in "${source_ref[@]:-}"; do
                if [[ "$item" == "$topic" ]]; then
                    out+=("$topic")
                fi
            done
        done
        printf '%s\n' "${out[@]}" | json_array_from_lines
    }

    case "$lower" in
        project-handbook.md|.specify/project-map/root/architecture.md|.specify/project-map/architecture.md) add_topic must_refresh "ARCHITECTURE.md" ;;
        .specify/project-map/root/structure.md|.specify/project-map/structure.md) add_topic must_refresh "STRUCTURE.md" ;;
        .specify/project-map/root/conventions.md|.specify/project-map/conventions.md) add_topic must_refresh "CONVENTIONS.md" ;;
        .specify/project-map/root/integrations.md|.specify/project-map/integrations.md) add_topic must_refresh "INTEGRATIONS.md" ;;
        .specify/project-map/root/workflows.md|.specify/project-map/workflows.md) add_topic must_refresh "WORKFLOWS.md" ;;
        .specify/project-map/root/testing.md|.specify/project-map/testing.md) add_topic must_refresh "TESTING.md" ;;
        .specify/project-map/root/operations.md|.specify/project-map/operations.md) add_topic must_refresh "OPERATIONS.md" ;;
    esac

    if [[ "$lower" =~ (^|/)(route|routes|router|routing|api|endpoint|endpoints|workflow|workflows|command|commands)(/|\.|$) ]]; then
        specific_boundary_hit=true
        add_topic must_refresh "INTEGRATIONS.md" "WORKFLOWS.md"
        add_topic review "ARCHITECTURE.md" "TESTING.md"
    fi
    if [[ "$lower" =~ (^|/)(schema|schemas|contract|contracts|type|types|interface|interfaces|manifest|manifests|adapter|adapters|middleware|export|exports)(/|\.|$) ]]; then
        specific_boundary_hit=true
        add_topic must_refresh "INTEGRATIONS.md"
        add_topic review "ARCHITECTURE.md" "TESTING.md"
    fi
    if [[ "$lower" =~ (^|/)(config|configs|settings)(/|\.|$) || "$lower" =~ (^|/)(package\.json|package-lock\.json|pnpm-lock\.yaml|yarn\.lock|pyproject\.toml|poetry\.lock|go\.mod|go\.sum|cargo\.toml|cargo\.lock|composer\.json|composer\.lock|gemfile|gemfile\.lock)$ ]]; then
        add_topic must_refresh "CONVENTIONS.md" "INTEGRATIONS.md" "OPERATIONS.md"
        add_topic review "TESTING.md"
    fi
    if [[ "$lower" =~ (^|/)(dockerfile|docker-compose\.yml|docker-compose\.yaml|makefile)$ ]]; then
        add_topic must_refresh "INTEGRATIONS.md" "OPERATIONS.md"
        add_topic review "TESTING.md"
    fi
    if [[ "$specific_boundary_hit" == false && "$lower" =~ (^|/)(src|app|apps|server|client|web|ui|frontend|backend|lib|libs)(/|$) ]]; then
        add_topic must_refresh "STRUCTURE.md"
        add_topic review "ARCHITECTURE.md" "TESTING.md"
    fi
    if [[ "$lower" =~ (^|/)scripts(/|$) ]]; then
        add_topic must_refresh "OPERATIONS.md"
        add_topic review "STRUCTURE.md" "TESTING.md"
    fi
    if [[ "$lower" =~ (^|/)tests(/|$) ]]; then
        add_topic must_refresh "TESTING.md"
        add_topic review "ARCHITECTURE.md"
    fi
    if [[ "$lower" =~ (^|/)(docs|specs)(/|$) ]]; then
        add_topic must_refresh "WORKFLOWS.md"
        add_topic review "ARCHITECTURE.md"
    fi

    if [[ "${#must_refresh[@]}" -eq 0 && "${#review[@]}" -eq 0 ]]; then
        if [[ "$classification" == "stale" ]]; then
            add_topic must_refresh "ARCHITECTURE.md"
            add_topic review "TESTING.md"
        elif [[ "$classification" == "possibly_stale" ]]; then
            add_topic must_refresh "STRUCTURE.md"
            add_topic review "ARCHITECTURE.md" "TESTING.md"
        fi
    fi

    local must_json review_json
    must_json="$(ordered_json_array must_refresh)"
    review_json="$(ordered_json_array review)"
    printf '{"must_refresh_topics":%s,"review_topics":%s}\n' "$must_json" "$review_json"
}

suggested_topics_for_path() {
    local path="$1"
    local plan_json
    plan_json="$(refresh_plan_for_path "$path")"
    if command -v python3 >/dev/null 2>&1; then
        PLAN_JSON="$plan_json" python3 - <<'PY'
import json, os
data = json.loads(os.environ["PLAN_JSON"])
topics = data.get("must_refresh_topics", []) + data.get("review_topics", [])
seen = []
for topic in topics:
    if topic not in seen:
        seen.append(topic)
print("\n".join(seen))
PY
        return 0
    fi
}

json_array_from_lines() {
    if command -v python3 >/dev/null 2>&1; then
        python3 -c 'import json,sys; print(json.dumps([line.rstrip("\n") for line in sys.stdin if line.rstrip("\n")], ensure_ascii=False))'
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

canonicalize_topics() {
    local -n source_ref="$1"
    local ordered=(
        "ARCHITECTURE.md"
        "STRUCTURE.md"
        "CONVENTIONS.md"
        "INTEGRATIONS.md"
        "OPERATIONS.md"
        "WORKFLOWS.md"
        "TESTING.md"
    )
    local topic item out=()
    for topic in "${ordered[@]}"; do
        for item in "${source_ref[@]:-}"; do
            if [[ "$item" == "$topic" ]]; then
                out+=("$topic")
            fi
        done
    done
    printf '%s\n' "${out[@]}"
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

normalize_dirty_reason() {
    local reason="$1"
    local normalized
    normalized="$(printf '%s' "$reason" | tr '[:upper:]' '[:lower:]' | tr '_-' '  ' | xargs)"
    case "$normalized" in
        "") echo "project_map_dirty" ;;
        "shared surface changed") echo "shared_surface_changed" ;;
        "architecture surface changed") echo "architecture_surface_changed" ;;
        "integration boundary changed") echo "integration_boundary_changed" ;;
        "workflow contract changed") echo "workflow_contract_changed" ;;
        "verification surface changed") echo "verification_surface_changed" ;;
        "runtime invariant changed") echo "runtime_invariant_changed" ;;
        *) echo "${normalized// /_}" ;;
    esac
}

refresh_plan_for_dirty_reason() {
    local canonical
    canonical="$(normalize_dirty_reason "$1")"
    case "$canonical" in
        shared_surface_changed)
            printf '{"must_refresh_topics":["ARCHITECTURE.md","STRUCTURE.md"],"review_topics":["INTEGRATIONS.md","WORKFLOWS.md","TESTING.md"]}\n'
            ;;
        architecture_surface_changed)
            printf '{"must_refresh_topics":["ARCHITECTURE.md"],"review_topics":["STRUCTURE.md","WORKFLOWS.md","TESTING.md"]}\n'
            ;;
        integration_boundary_changed)
            printf '{"must_refresh_topics":["INTEGRATIONS.md"],"review_topics":["ARCHITECTURE.md","OPERATIONS.md","TESTING.md"]}\n'
            ;;
        workflow_contract_changed)
            printf '{"must_refresh_topics":["WORKFLOWS.md"],"review_topics":["ARCHITECTURE.md","INTEGRATIONS.md","TESTING.md"]}\n'
            ;;
        verification_surface_changed)
            printf '{"must_refresh_topics":["TESTING.md"],"review_topics":["ARCHITECTURE.md","WORKFLOWS.md"]}\n'
            ;;
        runtime_invariant_changed)
            printf '{"must_refresh_topics":["OPERATIONS.md"],"review_topics":["INTEGRATIONS.md","TESTING.md"]}\n'
            ;;
        *)
            printf '{"must_refresh_topics":["ARCHITECTURE.md"],"review_topics":["TESTING.md"]}\n'
            ;;
    esac
}

emit_check_json() {
    local freshness="$1"
    local head_commit="$2"
    local last_mapped_commit="$3"
    local dirty="$4"
    local dirty_reasons_json="$5"
    local reasons_json="$6"
    local changed_files_json="$7"
    local suggested_topics_json="$8"
    local must_refresh_json="$9"
    local review_json="${10}"

    cat <<EOF
{
  "status_path": "$(json_escape "$STATUS_PATH")",
  "freshness": "$(json_escape "$freshness")",
  "head_commit": "$(json_escape "$head_commit")",
  "last_mapped_commit": "$(json_escape "$last_mapped_commit")",
  "dirty": $dirty,
  "dirty_reasons": $dirty_reasons_json,
  "reasons": $reasons_json,
  "changed_files": $changed_files_json,
  "suggested_topics": $suggested_topics_json,
  "must_refresh_topics": $must_refresh_json,
  "review_topics": $review_json
}
EOF
}

run_check() {
    local head_commit last_mapped_commit dirty dirty_reasons_json
    head_commit="$(git_head_commit)"

    if [[ ! -f "$(status_read_path)" ]]; then
        emit_check_json "missing" "$head_commit" "" "false" "[]" '["project-map status missing"]' "[]" "[]" "[]" "[]"
        return 0
    fi

    last_mapped_commit="$(read_status_field "last_mapped_commit")"
    dirty="$(read_status_field "dirty")"
    dirty_reasons_json="$(read_status_array "dirty_reasons")"
    [[ -n "$dirty" ]] || dirty="false"

    if [[ "$dirty" == "true" ]]; then
        local must_refresh_json review_json suggested_topics_json
        if command -v python3 >/dev/null 2>&1; then
            readarray -t _dirty_plan < <(DIRTY_REASONS_JSON="$dirty_reasons_json" python3 - <<'PY'
import json, os
reasons = json.loads(os.environ["DIRTY_REASONS_JSON"])
mapping = {
    "shared_surface_changed": (["ARCHITECTURE.md", "STRUCTURE.md"], ["INTEGRATIONS.md", "WORKFLOWS.md", "TESTING.md"]),
    "architecture_surface_changed": (["ARCHITECTURE.md"], ["STRUCTURE.md", "WORKFLOWS.md", "TESTING.md"]),
    "integration_boundary_changed": (["INTEGRATIONS.md"], ["ARCHITECTURE.md", "OPERATIONS.md", "TESTING.md"]),
    "workflow_contract_changed": (["WORKFLOWS.md"], ["ARCHITECTURE.md", "INTEGRATIONS.md", "TESTING.md"]),
    "verification_surface_changed": (["TESTING.md"], ["ARCHITECTURE.md", "WORKFLOWS.md"]),
    "runtime_invariant_changed": (["OPERATIONS.md"], ["INTEGRATIONS.md", "TESTING.md"]),
}
order = ["ARCHITECTURE.md","STRUCTURE.md","CONVENTIONS.md","INTEGRATIONS.md","OPERATIONS.md","WORKFLOWS.md","TESTING.md"]
must, review = [], []
for reason in reasons:
    m, r = mapping.get(reason, (["ARCHITECTURE.md"], ["TESTING.md"]))
    for topic in m:
        if topic not in must:
            must.append(topic)
    for topic in r:
        if topic not in review:
            review.append(topic)
must = [t for t in order if t in must]
review = [t for t in order if t in review]
suggested = [topic for topic in order if topic in set(must + review)]
print(json.dumps(must, ensure_ascii=False))
print(json.dumps(review, ensure_ascii=False))
print(json.dumps(suggested, ensure_ascii=False))
PY
)
            must_refresh_json="${_dirty_plan[0]:-[]}"
            review_json="${_dirty_plan[1]:-[]}"
            suggested_topics_json="${_dirty_plan[2]:-[]}"
        else
            must_refresh_json="[]"
            review_json="[]"
            suggested_topics_json="[]"
        fi
        emit_check_json "stale" "$head_commit" "$last_mapped_commit" "true" "$dirty_reasons_json" "$dirty_reasons_json" "[]" "$suggested_topics_json" "$must_refresh_json" "$review_json"
        return 0
    fi

    if [[ -z "$last_mapped_commit" || -z "$head_commit" ]]; then
        emit_check_json "possibly_stale" "$head_commit" "$last_mapped_commit" "false" "$dirty_reasons_json" '["git baseline unavailable for project-map freshness"]' "[]" "[]" "[]" "[]"
        return 0
    fi

    if ! has_git; then
        emit_check_json "possibly_stale" "$head_commit" "$last_mapped_commit" "false" "$dirty_reasons_json" '["git baseline unavailable for project-map freshness"]' "[]" "[]" "[]" "[]"
        return 0
    fi

    local diff_output
    diff_output="$(
        {
            git -C "$REPO_ROOT" diff --ignore-cr-at-eol --name-status --find-renames "$last_mapped_commit..$head_commit" 2>/dev/null || true
            git -C "$REPO_ROOT" diff --ignore-cr-at-eol --name-status --find-renames --cached 2>/dev/null || true
            git -C "$REPO_ROOT" diff --ignore-cr-at-eol --name-status --find-renames 2>/dev/null || true
            git -C "$REPO_ROOT" ls-files --others --exclude-standard 2>/dev/null | sed 's/^/??\t/' || true
        } | awk '!seen[$0]++'
    )"
    if [[ -z "$diff_output" ]]; then
        emit_check_json "fresh" "$head_commit" "$last_mapped_commit" "false" "$dirty_reasons_json" "[]" "[]" "[]" "[]" "[]"
        return 0
    fi

    local worst="fresh"
    local reasons=()
    local changed_files=()
    local suggested_topics=()
    local must_refresh_topics=()
    local review_topics=()
    local last_refresh_scope last_refresh_topics_json
    last_refresh_scope="$(read_status_field "last_refresh_scope")"
    last_refresh_topics_json="$(read_status_array "last_refresh_topics")"

    while IFS=$'\t' read -r status path1 path2; do
        [[ -n "$status" ]] || continue
        local candidate_path="$path1"
        if [[ "$status" == R* && -n "${path2:-}" ]]; then
            candidate_path="$path2"
        fi
        local candidate_lower
        candidate_lower="$(printf '%s' "$candidate_path" | tr '[:upper:]' '[:lower:]' | tr '\\' '/')"
        if [[ "$head_commit" == "$last_mapped_commit" ]]; then
            case "$candidate_lower" in
                project-handbook.md|.specify/project-map/*)
                    continue
                    ;;
            esac
        fi

        changed_files+=("$candidate_path")
        local classification
        classification="$(classify_path "$candidate_path")"
        local plan_json
        plan_json="$(refresh_plan_for_path "$candidate_path")"
        local covered_by_last_refresh=false
        if [[ "$last_refresh_scope" == "partial" ]] && command -v python3 >/dev/null 2>&1; then
            if LAST_REFRESH_TOPICS_JSON="$last_refresh_topics_json" PLAN_JSON="$plan_json" python3 - <<'PY'
import json, os, sys
last_topics = set(json.loads(os.environ["LAST_REFRESH_TOPICS_JSON"]))
plan = json.loads(os.environ["PLAN_JSON"])
needed = set(plan.get("must_refresh_topics", []) + plan.get("review_topics", []))
sys.exit(0 if needed.issubset(last_topics) else 1)
PY
            then
                covered_by_last_refresh=true
                plan_json="$(PLAN_JSON="$plan_json" python3 - <<'PY'
import json, os
plan = json.loads(os.environ["PLAN_JSON"])
topics = []
for topic in plan.get("must_refresh_topics", []) + plan.get("review_topics", []):
    if topic not in topics:
        topics.append(topic)
print(json.dumps({"must_refresh_topics": [], "review_topics": topics}, ensure_ascii=False))
PY
)"
            fi
        fi
        if command -v python3 >/dev/null 2>&1; then
            while IFS= read -r topic; do
                [[ -n "$topic" ]] || continue
                local already=false existing
                for existing in "${must_refresh_topics[@]}"; do
                    [[ "$existing" == "$topic" ]] && already=true && break
                done
                [[ "$already" == true ]] || must_refresh_topics+=("$topic")
            done < <(PLAN_JSON="$plan_json" python3 - <<'PY'
import json, os
for item in json.loads(os.environ["PLAN_JSON"]).get("must_refresh_topics", []):
    print(item)
PY
)
            while IFS= read -r topic; do
                [[ -n "$topic" ]] || continue
                local already=false existing
                for existing in "${review_topics[@]}"; do
                    [[ "$existing" == "$topic" ]] && already=true && break
                done
                [[ "$already" == true ]] || review_topics+=("$topic")
            done < <(PLAN_JSON="$plan_json" python3 - <<'PY'
import json, os
for item in json.loads(os.environ["PLAN_JSON"]).get("review_topics", []):
    print(item)
PY
)
        fi
        while IFS= read -r topic; do
            [[ -n "$topic" ]] || continue
            local already=false
            local existing
            for existing in "${suggested_topics[@]}"; do
                if [[ "$existing" == "$topic" ]]; then
                    already=true
                    break
                fi
            done
            [[ "$already" == true ]] || suggested_topics+=("$topic")
        done < <(suggested_topics_for_path "$candidate_path")

        if [[ "$classification" == "stale" ]]; then
            worst="stale"
            reasons+=("high-impact project-map change: $candidate_path")
        elif [[ "$classification" == "possibly_stale" && "$worst" != "stale" ]]; then
            worst="possibly_stale"
            if [[ "$covered_by_last_refresh" == true ]]; then
                reasons+=("covered topic changed since last partial map: $candidate_path")
            else
                reasons+=("codebase surface changed since last map: $candidate_path")
            fi
        fi
    done <<< "$diff_output"

    local reasons_json changed_files_json suggested_topics_json must_refresh_json review_json
    local deduped_reasons=()
    local reason existing seen
    for reason in "${reasons[@]}"; do
        seen=false
        for existing in "${deduped_reasons[@]:-}"; do
            if [[ "$existing" == "$reason" ]]; then
                seen=true
                break
            fi
        done
        [[ "$seen" == true ]] || deduped_reasons+=("$reason")
    done
    reasons_json="$(printf '%s\n' "${deduped_reasons[@]}" | json_array_from_lines)"
    changed_files_json="$(printf '%s\n' "${changed_files[@]}" | json_array_from_lines)"
    suggested_topics_json="$(canonicalize_topics suggested_topics | json_array_from_lines)"
    must_refresh_json="$(canonicalize_topics must_refresh_topics | json_array_from_lines)"
    review_json="$(canonicalize_topics review_topics | json_array_from_lines)"

    if [[ "$changed_files_json" == "[]" && "$reasons_json" == "[]" ]]; then
        worst="fresh"
    fi

    if [[ "$worst" == "fresh" ]]; then
        reasons_json="[]"
    fi

    emit_check_json "$worst" "$head_commit" "$last_mapped_commit" "false" "$dirty_reasons_json" "$reasons_json" "$changed_files_json" "$suggested_topics_json" "$must_refresh_json" "$review_json"
}

record_refresh() {
    local reason="${REASON:-manual}"
    ensure_canonical_map_files
    local head_commit branch now
    head_commit="$(git_head_commit)"
    branch="$(git_branch_name)"
    now="$(iso_now)"
    local topics_json
    if command -v python3 >/dev/null 2>&1; then
        topics_json="$(python3 - <<'PY'
import json
print(json.dumps(["ARCHITECTURE.md","STRUCTURE.md","CONVENTIONS.md","INTEGRATIONS.md","OPERATIONS.md","WORKFLOWS.md","TESTING.md"], ensure_ascii=False))
PY
)"
    else
        topics_json='["ARCHITECTURE.md","STRUCTURE.md","CONVENTIONS.md","INTEGRATIONS.md","OPERATIONS.md","WORKFLOWS.md","TESTING.md"]'
    fi
    write_status "$head_commit" "$now" "$branch" "fresh" "$reason" "$topics_json" "full" "$reason" "[]" "false" "[]"
    emit_check_json "fresh" "$head_commit" "$head_commit" "false" "[]" "[]" "[]" "$topics_json" "$topics_json" "[]"
}

mark_dirty() {
    local reason="${REASON:-project-map-dirty}"
    local last_mapped_commit last_mapped_at last_mapped_branch last_refresh_reason dirty_reasons_json
    last_mapped_commit="$(read_status_field "last_mapped_commit")"
    last_mapped_at="$(read_status_field "last_mapped_at")"
    last_mapped_branch="$(read_status_field "last_mapped_branch")"
    last_refresh_reason="$(read_status_field "last_refresh_reason")"
    local canonical_reason
    canonical_reason="$(normalize_dirty_reason "$reason")"
    dirty_reasons_json="$(append_reason_json "$(read_status_array "dirty_reasons")" "$canonical_reason")"

    if [[ -z "$last_mapped_at" ]]; then
        last_mapped_at="$(iso_now)"
    fi
    if [[ -z "$last_refresh_reason" ]]; then
        last_refresh_reason="manual"
    fi

    local last_refresh_topics_json last_refresh_scope last_refresh_basis last_refresh_changed_files_basis_json
    last_refresh_topics_json="$(read_status_array "last_refresh_topics")"
    last_refresh_scope="$(read_status_field "last_refresh_scope")"
    last_refresh_basis="$(read_status_field "last_refresh_basis")"
    last_refresh_changed_files_basis_json="$(read_status_array "last_refresh_changed_files_basis")"
    [[ -n "$last_refresh_scope" ]] || last_refresh_scope="full"
    [[ -n "$last_refresh_basis" ]] || last_refresh_basis="$last_refresh_reason"
    write_status "$last_mapped_commit" "$last_mapped_at" "$last_mapped_branch" "stale" "$last_refresh_reason" "$last_refresh_topics_json" "$last_refresh_scope" "$last_refresh_basis" "$last_refresh_changed_files_basis_json" "true" "$dirty_reasons_json"
    run_check
}

clear_dirty() {
    local last_mapped_commit last_mapped_at last_mapped_branch last_refresh_reason
    last_mapped_commit="$(read_status_field "last_mapped_commit")"
    last_mapped_at="$(read_status_field "last_mapped_at")"
    last_mapped_branch="$(read_status_field "last_mapped_branch")"
    last_refresh_reason="$(read_status_field "last_refresh_reason")"
    local last_refresh_topics_json last_refresh_scope last_refresh_basis last_refresh_changed_files_basis_json
    last_refresh_topics_json="$(read_status_array "last_refresh_topics")"
    last_refresh_scope="$(read_status_field "last_refresh_scope")"
    last_refresh_basis="$(read_status_field "last_refresh_basis")"
    last_refresh_changed_files_basis_json="$(read_status_array "last_refresh_changed_files_basis")"
    [[ -n "$last_refresh_scope" ]] || last_refresh_scope="full"
    [[ -n "$last_refresh_basis" ]] || last_refresh_basis="$last_refresh_reason"
    write_status "$last_mapped_commit" "$last_mapped_at" "$last_mapped_branch" "fresh" "$last_refresh_reason" "$last_refresh_topics_json" "$last_refresh_scope" "$last_refresh_basis" "$last_refresh_changed_files_basis_json" "false" "[]"
    run_check
}

case "$COMMAND" in
    check)
        run_check
        ;;
    record-refresh|complete-refresh)
        if [[ "$COMMAND" == "complete-refresh" && -z "$REASON" ]]; then
            REASON="map-build"
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
