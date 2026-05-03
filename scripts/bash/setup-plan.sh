#!/usr/bin/env bash

set -e

# Parse command line arguments
JSON_MODE=false
FEATURE_DIR_OVERRIDE=""
ARGS=()

while [[ $# -gt 0 ]]; do
    arg="$1"
    case "$arg" in
        --json) 
            JSON_MODE=true 
            shift
            ;;
        --feature-dir)
            if [[ $# -lt 2 ]]; then
                echo "ERROR: --feature-dir requires a value" >&2
                exit 1
            fi
            FEATURE_DIR_OVERRIDE="$2"
            shift 2
            ;;
        --help|-h) 
            echo "Usage: $0 [--json]"
            echo "  --json    Output results in JSON format"
            echo "  --feature-dir PATH  Explicit feature directory override"
            echo "  --help    Show this help message"
            exit 0 
            ;;
        *) 
            ARGS+=("$arg") 
            shift
            ;;
    esac
done

# Get script directory and load common functions
SCRIPT_DIR="$(CDPATH="" cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/common.sh"

# Get all paths and variables from common functions
_paths_output=$(get_feature_paths "$FEATURE_DIR_OVERRIDE") || { echo "ERROR: Failed to resolve feature paths" >&2; exit 1; }
eval "$_paths_output"
unset _paths_output

# Check if we're on a proper feature branch (only for git repos)
if [[ -z "$FEATURE_DIR_OVERRIDE" ]]; then
    check_feature_branch "$CURRENT_BRANCH" "$HAS_GIT" || exit 1
fi

# Ensure the feature directory exists
mkdir -p "$FEATURE_DIR"

# Copy plan template if it exists
TEMPLATE=$(resolve_template "plan-template" "$REPO_ROOT") || true
if [[ -n "$TEMPLATE" ]] && [[ -f "$TEMPLATE" ]]; then
    cp "$TEMPLATE" "$IMPL_PLAN"
    if ! $JSON_MODE; then
        echo "Copied plan template to $IMPL_PLAN"
    fi
else
    if ! $JSON_MODE; then
        echo "Warning: Plan template not found"
    fi
    # Create a basic plan file if template doesn't exist
    touch "$IMPL_PLAN"
fi

# Output results
if $JSON_MODE; then
    if has_jq; then
        jq -cn \
            --arg feature_dir "$FEATURE_DIR" \
            --arg feature_spec "$FEATURE_SPEC" \
            --arg context "$CONTEXT" \
            --arg impl_plan "$IMPL_PLAN" \
            --arg specs_dir "$FEATURE_DIR" \
            --arg branch "$CURRENT_BRANCH" \
            --arg has_git "$HAS_GIT" \
            '{FEATURE_DIR:$feature_dir,FEATURE_SPEC:$feature_spec,CONTEXT:$context,IMPL_PLAN:$impl_plan,SPECS_DIR:$specs_dir,BRANCH:$branch,HAS_GIT:$has_git}'
    else
        printf '{"FEATURE_DIR":"%s","FEATURE_SPEC":"%s","CONTEXT":"%s","IMPL_PLAN":"%s","SPECS_DIR":"%s","BRANCH":"%s","HAS_GIT":"%s"}\n' \
            "$(json_escape "$FEATURE_DIR")" "$(json_escape "$FEATURE_SPEC")" "$(json_escape "$CONTEXT")" "$(json_escape "$IMPL_PLAN")" "$(json_escape "$FEATURE_DIR")" "$(json_escape "$CURRENT_BRANCH")" "$(json_escape "$HAS_GIT")"
    fi
else
    echo "FEATURE_DIR: $FEATURE_DIR"
    echo "FEATURE_SPEC: $FEATURE_SPEC"
    echo "CONTEXT: $CONTEXT"
    echo "IMPL_PLAN: $IMPL_PLAN" 
    echo "SPECS_DIR: $FEATURE_DIR"
    echo "BRANCH: $CURRENT_BRANCH"
    echo "HAS_GIT: $HAS_GIT"
fi
