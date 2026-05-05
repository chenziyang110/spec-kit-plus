#!/usr/bin/env bash
# Common functions and variables for all scripts

# Find repository root by searching upward for .specify directory
# This is the primary marker for spec-kit projects
find_specify_root() {
    local dir="${1:-$(pwd)}"
    # Normalize to absolute path to prevent infinite loop with relative paths
    # Use -- to handle paths starting with - (e.g., -P, -L)
    dir="$(cd -- "$dir" 2>/dev/null && pwd)" || return 1
    local prev_dir=""
    while true; do
        if [ -d "$dir/.specify" ]; then
            echo "$dir"
            return 0
        fi
        # Stop if we've reached filesystem root or dirname stops changing
        if [ "$dir" = "/" ] || [ "$dir" = "$prev_dir" ]; then
            break
        fi
        prev_dir="$dir"
        dir="$(dirname "$dir")"
    done
    return 1
}

# Get repository root, prioritizing .specify directory over git
# This prevents using a parent git repo when spec-kit is initialized in a subdirectory
get_repo_root() {
    # First, look for .specify directory (spec-kit's own marker)
    local specify_root
    if specify_root=$(find_specify_root); then
        echo "$specify_root"
        return
    fi

    # Fallback to git if no .specify found
    if git rev-parse --show-toplevel >/dev/null 2>&1; then
        git rev-parse --show-toplevel
        return
    fi

    # Final fallback to script location for non-git repos
    local script_dir="$(CDPATH="" cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    (cd "$script_dir/../../.." && pwd)
}

# Feature roots are ordered by current preference first, then compatibility fallbacks.
feature_specs_roots() {
    local repo_root="$1"
    printf '%s\n' "$repo_root/.specify/features"
    printf '%s\n' "$repo_root/specs"
    printf '%s\n' "$repo_root/.specify/specs"
}

# Get current branch, with fallback for non-git repositories
get_current_branch() {
    # First check if SPECIFY_FEATURE environment variable is set
    if [[ -n "${SPECIFY_FEATURE:-}" ]]; then
        echo "$SPECIFY_FEATURE"
        return
    fi

    # Then check git if available at the spec-kit root (not parent)
    local repo_root=$(get_repo_root)
    if has_git; then
        git -C "$repo_root" rev-parse --abbrev-ref HEAD
        return
    fi

    # For non-git repos, try to find the latest feature directory.
    local latest_feature=""
    local highest=0
    local latest_timestamp=""
    local specs_dir=""
    while IFS= read -r specs_dir; do
        [[ -d "$specs_dir" ]] || continue
        for dir in "$specs_dir"/*; do
            if [[ -d "$dir" ]]; then
                local dirname=$(basename "$dir")
                if [[ "$dirname" =~ ^([0-9]{8}-[0-9]{6})- ]]; then
                    # Timestamp-based branch: compare lexicographically
                    local ts="${BASH_REMATCH[1]}"
                    if [[ "$ts" > "$latest_timestamp" ]]; then
                        latest_timestamp="$ts"
                        latest_feature=$dirname
                    fi
                elif [[ "$dirname" =~ ^([0-9]{3,})- ]]; then
                    local number=${BASH_REMATCH[1]}
                    number=$((10#$number))
                    if [[ "$number" -gt "$highest" ]]; then
                        highest=$number
                        # Only update if no timestamp branch found yet
                        if [[ -z "$latest_timestamp" ]]; then
                            latest_feature=$dirname
                        fi
                    fi
                fi
            fi
        done
    done < <(feature_specs_roots "$repo_root")

    if [[ -n "$latest_feature" ]]; then
        echo "$latest_feature"
        return
    fi

    echo "main"  # Final fallback
}

# Check if we have git available at the spec-kit root level
# Returns true only if git is installed and the repo root is inside a git work tree
# Handles both regular repos (.git directory) and worktrees/submodules (.git file)
has_git() {
    # First check if git command is available (before calling get_repo_root which may use git)
    command -v git >/dev/null 2>&1 || return 1
    local repo_root=$(get_repo_root)
    # Check if .git exists (directory or file for worktrees/submodules)
    [ -e "$repo_root/.git" ] || return 1
    # Verify it's actually a valid git work tree
    git -C "$repo_root" rev-parse --is-inside-work-tree >/dev/null 2>&1
}

check_feature_branch() {
    local branch="$1"
    local has_git_repo="$2"

    # For non-git repos, we can't enforce branch naming but still provide output
    if [[ "$has_git_repo" != "true" ]]; then
        echo "[specify] Warning: Git repository not detected; skipped branch validation" >&2
        return 0
    fi

    # Accept sequential prefix (3+ digits) but exclude malformed timestamps
    # Malformed: 7-or-8 digit date + 6-digit time with no trailing slug (e.g. "2026031-143022" or "20260319-143022")
    local is_sequential=false
    if [[ "$branch" =~ ^[0-9]{3,}- ]] && [[ ! "$branch" =~ ^[0-9]{7}-[0-9]{6}- ]] && [[ ! "$branch" =~ ^[0-9]{7,8}-[0-9]{6}$ ]]; then
        is_sequential=true
    fi
    if [[ "$is_sequential" != "true" ]] && [[ ! "$branch" =~ ^[0-9]{8}-[0-9]{6}- ]]; then
        echo "ERROR: Not on a feature branch. Current branch: $branch" >&2
        echo "Feature branches should be named like: 001-feature-name, 1234-feature-name, or 20260319-143022-feature-name" >&2
        return 1
    fi

    return 0
}

get_feature_dir() { echo "$1/.specify/features/$2"; }

# Find feature directory from durable lane state before falling back to branch-prefix guessing.
# This lets resumed workflows recover the canonical feature dir even when the
# current branch name and feature directory suffix no longer match exactly.
find_feature_dir_from_lane_state() {
    local repo_root="$1"
    local branch_name="$2"
    local lanes_root="$repo_root/.specify/lanes"

    [ -d "$lanes_root" ] || return 1

    local matches=()
    local lane_file feature_dir
    for lane_file in "$lanes_root"/*/lane.json; do
        [ -f "$lane_file" ] || continue
        if grep -Eq "\"branch_name\"[[:space:]]*:[[:space:]]*\"$branch_name\"" "$lane_file" \
            || grep -Eq "\"lane_id\"[[:space:]]*:[[:space:]]*\"$branch_name\"" "$lane_file"; then
            feature_dir=$(sed -n 's/.*"feature_dir"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "$lane_file" | head -n1)
            [ -n "$feature_dir" ] || continue
            if [[ "$feature_dir" != /* ]]; then
                feature_dir="$repo_root/$feature_dir"
            fi
            matches+=("$feature_dir")
        fi
    done

    if [[ ${#matches[@]} -eq 0 ]]; then
        return 1
    fi

    local unique_matches=()
    local candidate seen=false
    for candidate in "${matches[@]}"; do
        seen=false
        for existing in "${unique_matches[@]}"; do
            if [[ "$existing" == "$candidate" ]]; then
                seen=true
                break
            fi
        done
        if [[ "$seen" == false ]]; then
            unique_matches+=("$candidate")
        fi
    done

    if [[ ${#unique_matches[@]} -eq 1 ]]; then
        echo "${unique_matches[0]}"
        return 0
    fi

    echo "ERROR: Multiple lane records map branch '$branch_name' to feature directories: ${unique_matches[*]}" >&2
    echo "Please resolve the lane state before continuing." >&2
    return 1
}

# Find feature directory by numeric prefix instead of exact branch match
# This allows multiple branches to work on the same spec (e.g., 004-fix-bug, 004-add-feature)
find_feature_dir_by_prefix() {
    local repo_root="$1"
    local branch_name="$2"

    # Extract prefix from branch (e.g., "004" from "004-whatever" or "20260319-143022" from timestamp branches)
    local prefix=""
    if [[ "$branch_name" =~ ^([0-9]{8}-[0-9]{6})- ]]; then
        prefix="${BASH_REMATCH[1]}"
    elif [[ "$branch_name" =~ ^([0-9]{3,})- ]]; then
        prefix="${BASH_REMATCH[1]}"
    else
        # If branch doesn't have a recognized prefix, fall back to the preferred root.
        echo "$repo_root/.specify/features/$branch_name"
        return
    fi

    # Search known feature roots in preference order and return the first match set.
    local specs_dir
    while IFS= read -r specs_dir; do
        [[ -d "$specs_dir" ]] || continue
        local root_matches=()
        for dir in "$specs_dir"/"$prefix"-*; do
            if [[ -d "$dir" ]]; then
                root_matches+=("$dir")
            fi
        done
        if [[ ${#root_matches[@]} -eq 1 ]]; then
            echo "${root_matches[0]}"
            return
        fi
        if [[ ${#root_matches[@]} -gt 1 ]]; then
            echo "ERROR: Multiple spec directories found with prefix '$prefix' under '$specs_dir': ${root_matches[*]}" >&2
            echo "Please ensure only one spec directory exists per prefix in the active feature root." >&2
            return 1
        fi
    done < <(feature_specs_roots "$repo_root")

    # No match found - return the preferred root path (will fail later with clear error)
    echo "$repo_root/.specify/features/$branch_name"
}

get_feature_paths() {
    local explicit_feature_dir="${1:-}"
    local repo_root=$(get_repo_root)
    local current_branch=$(get_current_branch)
    local has_git_repo="false"

    if has_git; then
        has_git_repo="true"
    fi

    local feature_dir
    if [[ -n "$explicit_feature_dir" ]]; then
        if [[ "$explicit_feature_dir" = /* ]]; then
            feature_dir="$explicit_feature_dir"
        else
            feature_dir="$repo_root/$explicit_feature_dir"
        fi
    else
        # Use prefix-based lookup to support multiple branches per spec
        if ! feature_dir=$(find_feature_dir_from_lane_state "$repo_root" "$current_branch"); then
            if ! feature_dir=$(find_feature_dir_by_prefix "$repo_root" "$current_branch"); then
                echo "ERROR: Failed to resolve feature directory" >&2
                return 1
            fi
        fi
    fi

    # Use printf '%q' to safely quote values, preventing shell injection
    # via crafted branch names or paths containing special characters
    printf 'REPO_ROOT=%q\n' "$repo_root"
    printf 'CURRENT_BRANCH=%q\n' "$current_branch"
    printf 'HAS_GIT=%q\n' "$has_git_repo"
    printf 'FEATURE_DIR=%q\n' "$feature_dir"
    printf 'FEATURE_SPEC=%q\n' "$feature_dir/spec.md"
    printf 'CONTEXT=%q\n' "$feature_dir/context.md"
    printf 'SPECIFY_DRAFT=%q\n' "$feature_dir/specify-draft.md"
    printf 'IMPL_PLAN=%q\n' "$feature_dir/plan.md"
    printf 'TASKS=%q\n' "$feature_dir/tasks.md"
    printf 'RESEARCH=%q\n' "$feature_dir/research.md"
    printf 'DATA_MODEL=%q\n' "$feature_dir/data-model.md"
    printf 'QUICKSTART=%q\n' "$feature_dir/quickstart.md"
    printf 'CONTRACTS_DIR=%q\n' "$feature_dir/contracts"
}

# Check if jq is available for safe JSON construction
has_jq() {
    command -v jq >/dev/null 2>&1
}

# Escape a string for safe embedding in a JSON value (fallback when jq is unavailable).
# Handles backslash, double-quote, and JSON-required control character escapes (RFC 8259).
json_escape() {
    local s="$1"
    s="${s//\\/\\\\}"
    s="${s//\"/\\\"}"
    s="${s//$'\n'/\\n}"
    s="${s//$'\t'/\\t}"
    s="${s//$'\r'/\\r}"
    s="${s//$'\b'/\\b}"
    s="${s//$'\f'/\\f}"
    # Escape any remaining U+0001-U+001F control characters as \uXXXX.
    # (U+0000/NUL cannot appear in bash strings and is excluded.)
    # LC_ALL=C ensures ${#s} counts bytes and ${s:$i:1} yields single bytes,
    # so multi-byte UTF-8 sequences (first byte >= 0xC0) pass through intact.
    local LC_ALL=C
    local i char code
    for (( i=0; i<${#s}; i++ )); do
        char="${s:$i:1}"
        printf -v code '%d' "'$char" 2>/dev/null || code=256
        if (( code >= 1 && code <= 31 )); then
            printf '\\u%04x' "$code"
        else
            printf '%s' "$char"
        fi
    done
}

check_file() { [[ -f "$1" ]] && echo "  ✓ $2" || echo "  ✗ $2"; }
check_dir() { [[ -d "$1" && -n $(ls -A "$1" 2>/dev/null) ]] && echo "  ✓ $2" || echo "  ✗ $2"; }

# Resolve a template name to a file path using the priority stack:
#   1. .specify/templates/overrides/
#   2. .specify/presets/<preset-id>/templates/ (sorted by priority from .registry)
#   3. .specify/extensions/<ext-id>/templates/
#   4. .specify/templates/ (core)
resolve_template() {
    local template_name="$1"
    local repo_root="$2"
    local base="$repo_root/.specify/templates"

    # Priority 1: Project overrides
    local override="$base/overrides/${template_name}.md"
    [ -f "$override" ] && echo "$override" && return 0

    # Priority 2: Installed presets (sorted by priority from .registry)
    local presets_dir="$repo_root/.specify/presets"
    if [ -d "$presets_dir" ]; then
        local registry_file="$presets_dir/.registry"
        if [ -f "$registry_file" ] && command -v python3 >/dev/null 2>&1; then
            # Read preset IDs sorted by priority (lower number = higher precedence).
            # The python3 call is wrapped in an if-condition so that set -e does not
            # abort the function when python3 exits non-zero (e.g. invalid JSON).
            local sorted_presets=""
            if sorted_presets=$(SPECKIT_REGISTRY="$registry_file" python3 -c "
import json, sys, os
try:
    with open(os.environ['SPECKIT_REGISTRY']) as f:
        data = json.load(f)
    presets = data.get('presets', {})
    for pid, meta in sorted(presets.items(), key=lambda x: x[1].get('priority', 10)):
        print(pid)
except Exception:
    sys.exit(1)
" 2>/dev/null); then
                if [ -n "$sorted_presets" ]; then
                    # python3 succeeded and returned preset IDs — search in priority order
                    while IFS= read -r preset_id; do
                        local candidate="$presets_dir/$preset_id/templates/${template_name}.md"
                        [ -f "$candidate" ] && echo "$candidate" && return 0
                    done <<< "$sorted_presets"
                fi
                # python3 succeeded but registry has no presets — nothing to search
            else
                # python3 failed (missing, or registry parse error) — fall back to unordered directory scan
                for preset in "$presets_dir"/*/; do
                    [ -d "$preset" ] || continue
                    local candidate="$preset/templates/${template_name}.md"
                    [ -f "$candidate" ] && echo "$candidate" && return 0
                done
            fi
        else
            # Fallback: alphabetical directory order (no python3 available)
            for preset in "$presets_dir"/*/; do
                [ -d "$preset" ] || continue
                local candidate="$preset/templates/${template_name}.md"
                [ -f "$candidate" ] && echo "$candidate" && return 0
            done
        fi
    fi

    # Priority 3: Extension-provided templates
    local ext_dir="$repo_root/.specify/extensions"
    if [ -d "$ext_dir" ]; then
        for ext in "$ext_dir"/*/; do
            [ -d "$ext" ] || continue
            # Skip hidden directories (e.g. .backup, .cache)
            case "$(basename "$ext")" in .*) continue;; esac
            local candidate="$ext/templates/${template_name}.md"
            [ -f "$candidate" ] && echo "$candidate" && return 0
        done
    fi

    # Priority 4: Core templates
    local core="$base/${template_name}.md"
    [ -f "$core" ] && echo "$core" && return 0

    # Template not found in any location.
    # Return 1 so callers can distinguish "not found" from "found".
    # Callers running under set -e should use: TEMPLATE=$(resolve_template ...) || true
    return 1
}

project_map_dir() {
    local repo_root="${1:-$(get_repo_root)}"
    echo "$repo_root/.specify/project-map"
}

project_map_status_path() {
    local repo_root="${1:-$(get_repo_root)}"
    echo "$(project_map_dir "$repo_root")/index/status.json"
}

legacy_project_map_status_path() {
    local repo_root="${1:-$(get_repo_root)}"
    echo "$(project_map_dir "$repo_root")/status.json"
}

testing_dir() {
    local repo_root="${1:-$(get_repo_root)}"
    echo "$repo_root/.specify/testing"
}

testing_status_path() {
    local repo_root="${1:-$(get_repo_root)}"
    echo "$(testing_dir "$repo_root")/status.json"
}
