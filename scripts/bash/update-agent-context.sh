#!/usr/bin/env bash

# Update agent context files with information from plan.md
#
# This script maintains AI agent context files by parsing feature specifications 
# and updating agent-specific configuration files with project information.
#
# MAIN FUNCTIONS:
# 1. Environment Validation
#    - Verifies git repository structure and branch information
#    - Checks for required plan.md files and templates
#    - Validates file permissions and accessibility
#
# 2. Plan Data Extraction
#    - Parses plan.md files to extract project metadata
#    - Identifies language/version, frameworks, databases, and project types
#    - Handles missing or incomplete specification data gracefully
#
# 3. Agent File Management
#    - Creates new agent context files from templates when needed
#    - Updates existing agent files with new project information
#    - Preserves manual additions and custom configurations
#    - Supports multiple AI agent formats and directory structures
#
# 4. Content Generation
#    - Generates language-specific build/test commands
#    - Creates appropriate project directory structures
#    - Updates technology stacks and recent changes sections
#    - Maintains consistent formatting and timestamps
#
# 5. Multi-Agent Support
#    - Handles agent-specific file paths and naming conventions
#    - Supports: Claude, Gemini, Copilot, Cursor, Qwen, opencode, Codex, Windsurf, Junie, Kilo Code, Auggie CLI, Roo Code, CodeBuddy CLI, Qoder CLI, Amp, SHAI, Tabnine CLI, Kiro CLI, Mistral Vibe, Kimi Code, Pi Coding Agent, iFlow CLI, Forge, Antigravity or Generic
#    - Can update single agents or all existing agent files
#    - Creates default Claude file if no agent files exist
#
# Usage: ./update-agent-context.sh [agent_type]
# Agent types: claude|gemini|copilot|cursor-agent|qwen|opencode|codex|windsurf|junie|kilocode|auggie|roo|codebuddy|amp|shai|tabnine|kiro-cli|agy|bob|vibe|qodercli|kimi|trae|pi|iflow|forge|generic
# Leave empty to update all existing agent files

set -e

# Enable strict error handling
set -u
set -o pipefail

#==============================================================================
# Configuration and Global Variables
#==============================================================================

# Get script directory and load common functions
SCRIPT_DIR="$(CDPATH="" cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/common.sh"

# Get all paths and variables from common functions
_paths_output=$(get_feature_paths) || { echo "ERROR: Failed to resolve feature paths" >&2; exit 1; }
eval "$_paths_output"
unset _paths_output

NEW_PLAN="$IMPL_PLAN"  # Alias for compatibility with existing code
AGENT_TYPE="${1:-}"

# Agent-specific file paths  
CLAUDE_FILE="$REPO_ROOT/CLAUDE.md"
GEMINI_FILE="$REPO_ROOT/GEMINI.md"
COPILOT_FILE="$REPO_ROOT/.github/copilot-instructions.md"
CURSOR_FILE="$REPO_ROOT/.cursor/rules/specify-rules.mdc"
QWEN_FILE="$REPO_ROOT/QWEN.md"
AGENTS_FILE="$REPO_ROOT/AGENTS.md"
WINDSURF_FILE="$REPO_ROOT/.windsurf/rules/specify-rules.md"
JUNIE_FILE="$REPO_ROOT/.junie/AGENTS.md"
KILOCODE_FILE="$REPO_ROOT/.kilocode/rules/specify-rules.md"
AUGGIE_FILE="$REPO_ROOT/.augment/rules/specify-rules.md"
ROO_FILE="$REPO_ROOT/.roo/rules/specify-rules.md"
CODEBUDDY_FILE="$REPO_ROOT/CODEBUDDY.md"
QODER_FILE="$REPO_ROOT/QODER.md"
# Amp, Kiro CLI, IBM Bob, Pi, and Forge all share AGENTS.md — use AGENTS_FILE to avoid
# updating the same file multiple times.
AMP_FILE="$AGENTS_FILE"
SHAI_FILE="$REPO_ROOT/SHAI.md"
TABNINE_FILE="$REPO_ROOT/TABNINE.md"
KIRO_FILE="$AGENTS_FILE"
AGY_FILE="$AGENTS_FILE"
BOB_FILE="$AGENTS_FILE"
VIBE_FILE="$REPO_ROOT/.vibe/agents/specify-agents.md"
KIMI_FILE="$REPO_ROOT/KIMI.md"
TRAE_FILE="$REPO_ROOT/.trae/rules/AGENTS.md"
IFLOW_FILE="$REPO_ROOT/IFLOW.md"
FORGE_FILE="$AGENTS_FILE"

# Template file
TEMPLATE_FILE="$REPO_ROOT/.specify/templates/agent-file-template.md"

# Global variables for parsed plan data
NEW_LANG=""
NEW_FRAMEWORK=""
NEW_DB=""
NEW_PROJECT_TYPE=""
SPEC_KIT_BLOCK_START="<!-- SPEC-KIT:BEGIN -->"
SPEC_KIT_BLOCK_END="<!-- SPEC-KIT:END -->"

#==============================================================================
# Utility Functions
#==============================================================================

log_info() {
    echo "INFO: $1"
}

log_success() {
    echo "✓ $1"
}

log_error() {
    echo "ERROR: $1" >&2
}

log_warning() {
    echo "WARNING: $1" >&2
}

# Cleanup function for temporary files
cleanup() {
    local exit_code=$?
    # Disarm traps to prevent re-entrant loop
    trap - EXIT INT TERM
    rm -f /tmp/agent_update_*_$$
    rm -f /tmp/manual_additions_$$
    exit $exit_code
}

# Set up cleanup trap
trap cleanup EXIT INT TERM

is_managed_agents_file() {
    local target_file="$1"
    [[ "$target_file" == "$AGENTS_FILE" ]]
}

render_speckit_managed_block() {
    cat <<'EOF'
<!-- SPEC-KIT:BEGIN -->
## Spec Kit Plus Managed Rules

- `[AGENT]` marks an action the AI must explicitly execute.
- `[AGENT]` is independent from `[P]`.

## Workflow Mainline

- Treat `specify -> plan` as the default path.
- Use `clarify` only when an existing spec needs deeper analysis before planning.
- Use `deep-research` only when requirements are clear but feasibility or the implementation chain must be proven before planning; its findings, demo evidence, and Planning Handoff become inputs to `plan`.
- Use `prd-scan -> prd-build` as the canonical existing-project reverse-PRD lane when the user needs repository-first current-state product documentation. Treat `prd` as deprecated compatibility-only routing into that pair.

## Workflow Activation Discipline

- If there is even a 1% chance an `sp-*` workflow or passive skill applies, route before any response or action, including a clarifying question, file read, shell command, repository inspection, code edit, test run, or summary.
- Do not inspect first outside the workflow; repository inspection belongs inside the selected workflow.
- Name the selected workflow or passive skill in one concise line, then continue under that contract.
- Treat `sp-*` names as canonical workflow identities. Actual invocation syntax depends on the integration and should be taken from generated integration-specific surfaces rather than assumed from this managed block.

## Brownfield Context Gate

- `PROJECT-HANDBOOK.md` is the root navigation artifact.
- Deep project knowledge lives under `.specify/project-map/`.
- Before planning, debugging, or implementing against existing code, read `PROJECT-HANDBOOK.md` and the smallest relevant `.specify/project-map/*.md` files.
- Read atlas content by role:
  - `PROJECT-HANDBOOK.md`: choose the smallest relevant topic set before broad source reads.
  - `root/ARCHITECTURE.md`: architecture boundaries, truth ownership, change propagation, and core seams.
  - `root/STRUCTURE.md`: directory ownership, shared write surfaces, and file-placement rules.
  - `root/WORKFLOWS.md`: workflow paths, handoffs, state lifecycles, and recovery semantics.
  - `root/TESTING.md`: smallest meaningful checks, regression-sensitive areas, and verification expectations.
- If handbook/project-map coverage is missing, stale, or too broad, run `sp-map-scan` followed by `sp-map-build` before continuing.
- Treat git-baseline freshness in `.specify/project-map/index/status.json` as the truth source. If the atlas is not trustworthy, either complete a refresh and use `project-map complete-refresh` as the successful-refresh finalizer, or mark it dirty with `project-map mark-dirty` and route the next brownfield workflow through `sp-map-scan -> sp-map-build`. Do not continue under known-stale atlas state without choosing one of those paths.

## Project Memory

- Passive project memory lives under `.specify/memory/project-rules.md` and `.specify/memory/project-learnings.md`.
- Treat the learning layer as workflow-execution infrastructure, not as optional notes.
- `.specify/memory/constitution.md` is the principle-level source of truth when present.
- `.specify/memory/project-rules.md` holds stable defaults and reusable constraints.
- `.specify/memory/project-learnings.md` holds confirmed reusable lessons.
- `.planning/learnings/candidates.md` is a lower-confidence candidate layer and should influence work only when relevant to the touched area.
- Shared project memory is always available to later work in this repository, not just when a `sp-*` workflow is active.
- Prefer generated project-local Spec Kit workflows, skills, and commands over ad-hoc execution when they fit the task.

## Workflow Routing

- Use `sp-fast` only for trivial, low-risk local changes that do not need planning artifacts.
- Use `sp-quick` for bounded tasks that need lightweight tracking but not the full `specify -> plan -> tasks -> implement` flow.
- Use `sp-auto` when repository state already records the recommended next step and the user wants one continue entrypoint instead of naming the exact workflow manually.
- Use `sp-specify` when scope, behavior, constraints, or acceptance criteria need explicit alignment before planning.
- Use `sp-map-scan` when repository-current-state atlas evidence must be gathered before deeper brownfield work.
- Use `sp-map-build` when refreshed handbook/project-map outputs must be compiled from scan inputs.
- Use `sp-prd-scan` when an existing repository needs the heavy read-only current-state reconstruction scan before final PRD synthesis, and `sp-prd-build` once that scan package is ready to compile.
- Use `sp-deep-research` when a clear requirement still lacks a proven implementation chain and needs coordinated research, optional multi-agent evidence gathering, or a disposable demo before planning.
- Use `sp-debug` when diagnosis or root-cause analysis is still required before a fix path is trustworthy.
- Use `sp-test-scan` for project-level testing evidence and build planning, and `sp-test-build` for leader-managed testing-system construction.

## Command Surface Rules

- Treat the live `specify --help` output as the only authoritative CLI command surface.
- Before suggesting or running a `specify <subcommand>` invocation, verify that `specify --help` or `specify <subcommand> --help` exposes it.
- Do not invent, paraphrase, or "normalize" unsupported CLI names such as `specify create-feature`.
- Feature creation must follow `sp-specify` plus the generated create-feature script, not a separate imagined branch-creation command family.

## Delegated Execution Defaults

- Dispatch native subagents by default for independent, bounded lanes when parallel work materially improves speed, quality, or verification confidence.
- Use a validated `WorkerTaskPacket` or equivalent execution contract before subagent work begins.
- Do not dispatch from raw task text alone.
- Wait for each subagent's structured handoff, result file, or runtime-managed result before integrating or marking work complete. Idle state or a chat summary is not completion evidence.
- Use the integration's durable team/runtime surface only when durable team state, explicit join-point tracking, result files, or lifecycle control beyond one in-session subagent burst is required. For integrations that expose `sp-teams`, use `sp-teams` only in those cases.

## Lane Recovery Rules

- Concurrent feature work is lane-first, not branch-first.
- Do not assume the current branch name is the canonical feature directory slug.
- For resumable `sp-*` commands, resolve the active feature through durable lane state or an explicit `feature_dir` before guessing from branch-only context.
- If a workflow command can accept an explicit `feature_dir`, prefer that override over current-branch inference.
- If lane resolution returns one safe candidate and a materialized worktree, continue from that isolated worktree context instead of the leader workspace.
- Treat canonical workflow-state tokens such as `/sp.plan`, `/sp.tasks`, `/sp.deep-research`, and `/sp.implement` as normalized command identities during resume logic; never compare them as raw strings against bare command names.
- Prefer `.specify/features/<feature>/` as the canonical generated-project feature root. Support legacy feature roots such as `specs/<feature>/` and `.specify/specs/<feature>/` during recovery and repair paths when durable lane state or prefix matching points there.
- Do not fail a resumable workflow only because the current branch is not a feature branch when explicit `feature_dir` or unique lane recovery already identifies the target feature safely.

## Artifact Priority

- `workflow-state.md` under the active feature directory is the stage/status source of truth for resumable workflow progress. Read it before resume, next-step routing, or workflow closeout; do not continue from branch name or chat memory alone when it exists.
- `alignment.md` and `context.md` under the active feature directory carry locked decisions from `sp-specify` into planning.
- `deep-research.md`, its traceable `Planning Handoff`, and `research-spikes/` under the active feature directory carry feasibility evidence, recommended approach, constraints, rejected options, and demo results from `sp-deep-research` into planning.
- `plan.md` under the active feature directory is the implementation design source of truth once planning begins.
- `tasks.md` under the active feature directory is the execution breakdown source of truth once task generation begins.
- `.specify/prd-runs/<run-id>/`, including its workflow state and scan/build artifacts, is the current-state PRD reconstruction truth surface. Treat it as documentation output unless later work explicitly adopts it as planning input.
- `.specify/testing/testing-state.md` is the recovery and next-step truth for `sp-test-*`.
- Treat testing artifacts by role:
  - `TEST_SCAN.md`: scan evidence and module risk findings, not the executable build contract.
  - `TEST_BUILD_PLAN.md` / `.json`: build-ready testing-system lanes and validation commands; primary `sp-test-build` inputs.
  - `UNIT_TEST_SYSTEM_REQUEST.md`: brownfield testing-program input for later scoped spec/planning work.
  - `TESTING_CONTRACT.md`: durable downstream testing obligations that later workflows should honor automatically.
  - `TESTING_PLAYBOOK.md`: operator and maintainer runbook for test execution.
  - `COVERAGE_BASELINE.json`: observed baseline data, not acceptance proof by itself.

## Execution and Closeout Rules

- Do not substitute chat narration for workflow execution. If a workflow requires an artifact write, helper/hook execution, validation run, or state update, perform it explicitly rather than describing it as though it happened.
- For resume, next-step routing, and closeout, read the relevant durable state surface first (`workflow-state.md`, `.specify/testing/testing-state.md`, quick-task `STATUS.md`, or project-map freshness state) before deciding what happens next.
- If the active workflow has a truth-owning artifact set, do not claim completion until those artifacts exist and any required validation or closeout mechanism has run truthfully.
- `.specify/project-map/index/status.json` determines whether handbook/project-map coverage can be trusted as fresh and records git-baseline freshness as the truth source.

## Map Maintenance

- If a change alters architecture boundaries, ownership, workflow names, integration contracts, or verification entry points, refresh `PROJECT-HANDBOOK.md` and the affected `.specify/project-map/*.md` files.
- If a full refresh can be completed now, run `sp-map-scan` followed by `sp-map-build`, then use `project-map complete-refresh` as the successful-refresh finalizer.
- Otherwise use `project-map mark-dirty` as the manual override/fallback and explicitly route the next brownfield workflow through `sp-map-scan` followed by `sp-map-build`.
- Do not treat consumed handbook/project-map context as self-maintaining; the agent changing map-level truth is responsible for keeping the atlas-style handbook system current.

- Preserve content outside this managed block.
<!-- SPEC-KIT:END -->
EOF
}

upsert_speckit_managed_block() {
    local target_file="$1"
    local rendered_block
    local python_cmd=""
    rendered_block="$(render_speckit_managed_block)"

    if command -v python3 >/dev/null 2>&1; then
        python_cmd="python3"
    elif command -v python >/dev/null 2>&1; then
        python_cmd="python"
    else
        log_error "Python is required to update the managed Spec Kit block"
        return 1
    fi

    if ! "$python_cmd" - "$target_file" "$SPEC_KIT_BLOCK_START" "$SPEC_KIT_BLOCK_END" "$rendered_block" <<'PY'
from pathlib import Path
import sys
import os
import re
import tempfile

path = Path(sys.argv[1])
start = sys.argv[2]
end = sys.argv[3]
block = sys.argv[4]

content = path.read_text(encoding="utf-8") if path.exists() else ""

def choose_newline(text: str) -> str:
    if "\r\n" in text:
        return "\r\n"
    if "\n" in text:
        return "\n"
    if "\r" in text:
        return "\r"
    return "\n"

def render_block(template: str, newline: str) -> str:
    normalized = template.replace("\r\n", "\n").replace("\r", "\n")
    return normalized.replace("\n", newline)

def count_markers(text: str, marker: str) -> int:
    return text.count(marker)

def find_complete_blocks(text: str, start_marker: str, end_marker: str):
    pattern = re.escape(start_marker) + r".*?" + re.escape(end_marker)
    return list(re.finditer(pattern, text, flags=re.S))

raw_start_count = count_markers(content, start)
raw_end_count = count_markers(content, end)
complete_blocks = find_complete_blocks(content, start, end)

if raw_start_count == 1 and raw_end_count == 1 and len(complete_blocks) == 1:
    match = complete_blocks[0]
    newline = choose_newline(match.group(0) or content)
    updated = content[:match.start()] + render_block(block, newline) + content[match.end():]
elif content:
    newline = choose_newline(content)
    rendered = render_block(block, newline)
    if rendered in content:
        updated = content
    else:
        if content.endswith(newline + newline):
            separator = ""
        elif content.endswith(newline):
            separator = newline
        else:
            separator = newline + newline
        updated = content + separator + rendered
else:
    updated = render_block(block, "\n")

target_dir = path.parent if path.parent != Path("") else Path(".")
fd, temp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=target_dir)
os.close(fd)
temp_path = Path(temp_name)
try:
    temp_path.write_text(updated, encoding="utf-8")
    if path.exists():
        os.chmod(temp_path, path.stat().st_mode)
    os.replace(temp_path, path)
finally:
    if temp_path.exists():
        temp_path.unlink()
PY
    then
        log_error "Failed to update managed Spec Kit block in $target_file"
        return 1
    fi

    return 0
}

#==============================================================================
# Validation Functions
#==============================================================================

validate_environment() {
    # Check if we have a current branch/feature (git or non-git)
    if [[ -z "$CURRENT_BRANCH" ]]; then
        log_error "Unable to determine current feature"
        if [[ "$HAS_GIT" == "true" ]]; then
            log_info "Make sure you're on a feature branch"
        else
            log_info "Set SPECIFY_FEATURE environment variable or create a feature first"
        fi
        exit 1
    fi
    
    # Check if plan.md exists
    if [[ ! -f "$NEW_PLAN" ]]; then
        log_error "No plan.md found at $NEW_PLAN"
        log_info "Make sure you're working on a feature with a corresponding spec directory"
        if [[ "$HAS_GIT" != "true" ]]; then
            log_info "Use: export SPECIFY_FEATURE=your-feature-name or create a new feature first"
        fi
        exit 1
    fi
    
    # Check if template exists (needed for new files)
    if [[ ! -f "$TEMPLATE_FILE" ]]; then
        log_warning "Template file not found at $TEMPLATE_FILE"
        log_warning "Creating new agent files will fail"
    fi
}

#==============================================================================
# Plan Parsing Functions
#==============================================================================

extract_plan_field() {
    local field_pattern="$1"
    local plan_file="$2"
    
    grep "^\*\*${field_pattern}\*\*: " "$plan_file" 2>/dev/null | \
        head -1 | \
        sed "s|^\*\*${field_pattern}\*\*: ||" | \
        sed 's/^[ \t]*//;s/[ \t]*$//' | \
        grep -v "NEEDS CLARIFICATION" | \
        grep -v "^N/A$" || echo ""
}

parse_plan_data() {
    local plan_file="$1"
    
    if [[ ! -f "$plan_file" ]]; then
        log_error "Plan file not found: $plan_file"
        return 1
    fi
    
    if [[ ! -r "$plan_file" ]]; then
        log_error "Plan file is not readable: $plan_file"
        return 1
    fi
    
    log_info "Parsing plan data from $plan_file"
    
    NEW_LANG=$(extract_plan_field "Language/Version" "$plan_file")
    NEW_FRAMEWORK=$(extract_plan_field "Primary Dependencies" "$plan_file")
    NEW_DB=$(extract_plan_field "Storage" "$plan_file")
    NEW_PROJECT_TYPE=$(extract_plan_field "Project Type" "$plan_file")
    
    # Log what we found
    if [[ -n "$NEW_LANG" ]]; then
        log_info "Found language: $NEW_LANG"
    else
        log_warning "No language information found in plan"
    fi
    
    if [[ -n "$NEW_FRAMEWORK" ]]; then
        log_info "Found framework: $NEW_FRAMEWORK"
    fi
    
    if [[ -n "$NEW_DB" ]] && [[ "$NEW_DB" != "N/A" ]]; then
        log_info "Found database: $NEW_DB"
    fi
    
    if [[ -n "$NEW_PROJECT_TYPE" ]]; then
        log_info "Found project type: $NEW_PROJECT_TYPE"
    fi
}

format_technology_stack() {
    local lang="$1"
    local framework="$2"
    local parts=()
    
    # Add non-empty parts
    [[ -n "$lang" && "$lang" != "NEEDS CLARIFICATION" ]] && parts+=("$lang")
    [[ -n "$framework" && "$framework" != "NEEDS CLARIFICATION" && "$framework" != "N/A" ]] && parts+=("$framework")
    
    # Join with proper formatting
    if [[ ${#parts[@]} -eq 0 ]]; then
        echo ""
    elif [[ ${#parts[@]} -eq 1 ]]; then
        echo "${parts[0]}"
    else
        # Join multiple parts with " + "
        local result="${parts[0]}"
        for ((i=1; i<${#parts[@]}; i++)); do
            result="$result + ${parts[i]}"
        done
        echo "$result"
    fi
}

#==============================================================================
# Template and Content Generation Functions
#==============================================================================

get_project_structure() {
    local project_type="$1"
    
    if [[ "$project_type" == *"web"* ]]; then
        echo "backend/\\nfrontend/\\ntests/"
    else
        echo "src/\\ntests/"
    fi
}

get_commands_for_language() {
    local lang="$1"
    
    case "$lang" in
        *"Python"*)
            echo "cd src && pytest && ruff check ."
            ;;
        *"Rust"*)
            echo "cargo test && cargo clippy"
            ;;
        *"JavaScript"*|*"TypeScript"*)
            echo "npm test \\&\\& npm run lint"
            ;;
        *)
            echo "# Add commands for $lang"
            ;;
    esac
}

get_language_conventions() {
    local lang="$1"
    echo "$lang: Follow standard conventions"
}

create_new_agent_file() {
    local target_file="$1"
    local temp_file="$2"
    local project_name="$3"
    local current_date="$4"
    
    if [[ ! -f "$TEMPLATE_FILE" ]]; then
        log_error "Template not found at $TEMPLATE_FILE"
        return 1
    fi
    
    if [[ ! -r "$TEMPLATE_FILE" ]]; then
        log_error "Template file is not readable: $TEMPLATE_FILE"
        return 1
    fi
    
    log_info "Creating new agent context file from template..."
    
    if ! cp "$TEMPLATE_FILE" "$temp_file"; then
        log_error "Failed to copy template file"
        return 1
    fi
    
    # Replace template placeholders
    local project_structure
    project_structure=$(get_project_structure "$NEW_PROJECT_TYPE")
    
    local commands
    commands=$(get_commands_for_language "$NEW_LANG")
    
    local language_conventions
    language_conventions=$(get_language_conventions "$NEW_LANG")
    
    # Perform substitutions with error checking using safer approach
    # Escape special characters for sed by using a different delimiter or escaping
    local escaped_lang=$(printf '%s\n' "$NEW_LANG" | sed 's/[\[\.*^$()+{}|]/\\&/g')
    local escaped_framework=$(printf '%s\n' "$NEW_FRAMEWORK" | sed 's/[\[\.*^$()+{}|]/\\&/g')
    local escaped_branch=$(printf '%s\n' "$CURRENT_BRANCH" | sed 's/[\[\.*^$()+{}|]/\\&/g')
    
    # Build technology stack and recent change strings conditionally
    local tech_stack
    if [[ -n "$escaped_lang" && -n "$escaped_framework" ]]; then
        tech_stack="- $escaped_lang + $escaped_framework ($escaped_branch)"
    elif [[ -n "$escaped_lang" ]]; then
        tech_stack="- $escaped_lang ($escaped_branch)"
    elif [[ -n "$escaped_framework" ]]; then
        tech_stack="- $escaped_framework ($escaped_branch)"
    else
        tech_stack="- ($escaped_branch)"
    fi

    local recent_change
    if [[ -n "$escaped_lang" && -n "$escaped_framework" ]]; then
        recent_change="- $escaped_branch: Added $escaped_lang + $escaped_framework"
    elif [[ -n "$escaped_lang" ]]; then
        recent_change="- $escaped_branch: Added $escaped_lang"
    elif [[ -n "$escaped_framework" ]]; then
        recent_change="- $escaped_branch: Added $escaped_framework"
    else
        recent_change="- $escaped_branch: Added"
    fi

    local substitutions=(
        "s|\[PROJECT NAME\]|$project_name|"
        "s|\[DATE\]|$current_date|"
        "s|\[EXTRACTED FROM ALL PLAN.MD FILES\]|$tech_stack|"
        "s|\[ACTUAL STRUCTURE FROM PLANS\]|$project_structure|g"
        "s|\[ONLY COMMANDS FOR ACTIVE TECHNOLOGIES\]|$commands|"
        "s|\[LANGUAGE-SPECIFIC, ONLY FOR LANGUAGES IN USE\]|$language_conventions|"
        "s|\[LAST 3 FEATURES AND WHAT THEY ADDED\]|$recent_change|"
    )
    
    for substitution in "${substitutions[@]}"; do
        if ! sed -i.bak -e "$substitution" "$temp_file"; then
            log_error "Failed to perform substitution: $substitution"
            rm -f "$temp_file" "$temp_file.bak"
            return 1
        fi
    done
    
    # Convert \n sequences to actual newlines
    newline=$(printf '\n')
    sed -i.bak2 "s/\\\\n/${newline}/g" "$temp_file"

    # Clean up backup files
    rm -f "$temp_file.bak" "$temp_file.bak2"

    # Prepend Cursor frontmatter for .mdc files so rules are auto-included
    if [[ "$target_file" == *.mdc ]]; then
        local frontmatter_file
        frontmatter_file=$(mktemp) || return 1
        printf '%s\n' "---" "description: Project Development Guidelines" "globs: [\"**/*\"]" "alwaysApply: true" "---" "" > "$frontmatter_file"
        cat "$temp_file" >> "$frontmatter_file"
        mv "$frontmatter_file" "$temp_file"
    fi

    return 0
}




update_existing_agent_file() {
    local target_file="$1"
    local current_date="$2"
    
    log_info "Updating existing agent context file..."
    
    # Use a single temporary file for atomic update
    local temp_file
    temp_file=$(mktemp) || {
        log_error "Failed to create temporary file"
        return 1
    }
    
    # Process the file in one pass
    local tech_stack=$(format_technology_stack "$NEW_LANG" "$NEW_FRAMEWORK")
    local new_tech_entries=()
    local new_change_entry=""
    
    # Prepare new technology entries
    if [[ -n "$tech_stack" ]] && ! grep -Fq -- "$tech_stack" "$target_file"; then
        new_tech_entries+=("- $tech_stack ($CURRENT_BRANCH)")
    fi
    
    if [[ -n "$NEW_DB" ]] && [[ "$NEW_DB" != "N/A" ]] && [[ "$NEW_DB" != "NEEDS CLARIFICATION" ]] && ! grep -Fq -- "$NEW_DB" "$target_file"; then
        new_tech_entries+=("- $NEW_DB ($CURRENT_BRANCH)")
    fi
    
    # Prepare new change entry
    if [[ -n "$tech_stack" ]]; then
        new_change_entry="- $CURRENT_BRANCH: Added $tech_stack"
    elif [[ -n "$NEW_DB" ]] && [[ "$NEW_DB" != "N/A" ]] && [[ "$NEW_DB" != "NEEDS CLARIFICATION" ]]; then
        new_change_entry="- $CURRENT_BRANCH: Added $NEW_DB"
    fi
    
    # Check if sections exist in the file
    local has_active_technologies=0
    local has_recent_changes=0
    
    if grep -q "^## Active Technologies" "$target_file" 2>/dev/null; then
        has_active_technologies=1
    fi
    
    if grep -q "^## Recent Changes" "$target_file" 2>/dev/null; then
        has_recent_changes=1
    fi
    
    # Process file line by line
    local in_tech_section=false
    local in_changes_section=false
    local tech_entries_added=false
    local changes_entries_added=false
    local existing_changes_count=0
    local file_ended=false
    
    while IFS= read -r line || [[ -n "$line" ]]; do
        # Handle Active Technologies section
        if [[ "$line" == "## Active Technologies" ]]; then
            echo "$line" >> "$temp_file"
            in_tech_section=true
            continue
        elif [[ $in_tech_section == true ]] && [[ "$line" =~ ^##[[:space:]] ]]; then
            # Add new tech entries before closing the section
            if [[ $tech_entries_added == false ]] && [[ ${#new_tech_entries[@]} -gt 0 ]]; then
                printf '%s\n' "${new_tech_entries[@]}" >> "$temp_file"
                tech_entries_added=true
            fi
            echo "$line" >> "$temp_file"
            in_tech_section=false
            continue
        elif [[ $in_tech_section == true ]] && [[ -z "$line" ]]; then
            # Add new tech entries before empty line in tech section
            if [[ $tech_entries_added == false ]] && [[ ${#new_tech_entries[@]} -gt 0 ]]; then
                printf '%s\n' "${new_tech_entries[@]}" >> "$temp_file"
                tech_entries_added=true
            fi
            echo "$line" >> "$temp_file"
            continue
        fi
        
        # Handle Recent Changes section
        if [[ "$line" == "## Recent Changes" ]]; then
            echo "$line" >> "$temp_file"
            # Add new change entry right after the heading
            if [[ -n "$new_change_entry" ]]; then
                echo "$new_change_entry" >> "$temp_file"
            fi
            in_changes_section=true
            changes_entries_added=true
            continue
        elif [[ $in_changes_section == true ]] && [[ "$line" =~ ^##[[:space:]] ]]; then
            echo "$line" >> "$temp_file"
            in_changes_section=false
            continue
        elif [[ $in_changes_section == true ]] && [[ "$line" == "- "* ]]; then
            # Keep only first 2 existing changes
            if [[ $existing_changes_count -lt 2 ]]; then
                echo "$line" >> "$temp_file"
                ((existing_changes_count++))
            fi
            continue
        fi
        
        # Update timestamp
        if [[ "$line" =~ (\*\*)?Last\ updated(\*\*)?:.*[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9] ]]; then
            echo "$line" | sed "s/[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]/$current_date/" >> "$temp_file"
        else
            echo "$line" >> "$temp_file"
        fi
    done < "$target_file"
    
    # Post-loop check: if we're still in the Active Technologies section and haven't added new entries
    if [[ $in_tech_section == true ]] && [[ $tech_entries_added == false ]] && [[ ${#new_tech_entries[@]} -gt 0 ]]; then
        printf '%s\n' "${new_tech_entries[@]}" >> "$temp_file"
        tech_entries_added=true
    fi
    
    # If sections don't exist, add them at the end of the file
    if [[ $has_active_technologies -eq 0 ]] && [[ ${#new_tech_entries[@]} -gt 0 ]]; then
        echo "" >> "$temp_file"
        echo "## Active Technologies" >> "$temp_file"
        printf '%s\n' "${new_tech_entries[@]}" >> "$temp_file"
        tech_entries_added=true
    fi
    
    if [[ $has_recent_changes -eq 0 ]] && [[ -n "$new_change_entry" ]]; then
        echo "" >> "$temp_file"
        echo "## Recent Changes" >> "$temp_file"
        echo "$new_change_entry" >> "$temp_file"
        changes_entries_added=true
    fi
    
    # Ensure Cursor .mdc files have YAML frontmatter for auto-inclusion
    if [[ "$target_file" == *.mdc ]]; then
        if ! head -1 "$temp_file" | grep -q '^---'; then
            local frontmatter_file
            frontmatter_file=$(mktemp) || { rm -f "$temp_file"; return 1; }
            printf '%s\n' "---" "description: Project Development Guidelines" "globs: [\"**/*\"]" "alwaysApply: true" "---" "" > "$frontmatter_file"
            cat "$temp_file" >> "$frontmatter_file"
            mv "$frontmatter_file" "$temp_file"
        fi
    fi

    # Move temp file to target atomically
    if ! mv "$temp_file" "$target_file"; then
        log_error "Failed to update target file"
        rm -f "$temp_file"
        return 1
    fi

    return 0
}
#==============================================================================
# Main Agent File Update Function
#==============================================================================

update_agent_file() {
    local target_file="$1"
    local agent_name="$2"
    
    if [[ -z "$target_file" ]] || [[ -z "$agent_name" ]]; then
        log_error "update_agent_file requires target_file and agent_name parameters"
        return 1
    fi
    
    log_info "Updating $agent_name context file: $target_file"
    
    local project_name
    project_name=$(basename "$REPO_ROOT")
    local current_date
    current_date=$(date +%Y-%m-%d)
    
    # Create directory if it doesn't exist
    local target_dir
    target_dir=$(dirname "$target_file")
    if [[ ! -d "$target_dir" ]]; then
        if ! mkdir -p "$target_dir"; then
            log_error "Failed to create directory: $target_dir"
            return 1
        fi
    fi

    local file_exists=false
    if [[ -f "$target_file" ]]; then
        file_exists=true
        if [[ ! -r "$target_file" ]]; then
            log_error "Cannot read existing file: $target_file"
            return 1
        fi
        if [[ ! -w "$target_file" ]]; then
            log_error "Cannot write to existing file: $target_file"
            return 1
        fi
    fi

    if [[ ! -f "$target_file" ]]; then
        # Create new file from template
        local temp_file
        temp_file=$(mktemp) || {
            log_error "Failed to create temporary file"
            return 1
        }
        
        if create_new_agent_file "$target_file" "$temp_file" "$project_name" "$current_date"; then
            if mv "$temp_file" "$target_file"; then
                :
            else
                log_error "Failed to move temporary file to $target_file"
                rm -f "$temp_file"
                return 1
            fi
        else
            log_error "Failed to create new agent file"
            rm -f "$temp_file"
            return 1
        fi
    elif ! is_managed_agents_file "$target_file"; then
        # Update existing file
        if update_existing_agent_file "$target_file" "$current_date"; then
            :
        else
            log_error "Failed to update existing agent file"
            return 1
        fi
    fi

    if ! upsert_speckit_managed_block "$target_file"; then
        log_error "Failed to update managed Spec Kit block"
        return 1
    fi

    if [[ "$file_exists" == true ]]; then
        log_success "Updated existing $agent_name context file"
    else
        log_success "Created new $agent_name context file"
    fi

    return 0
}

#==============================================================================
# Agent Selection and Processing
#==============================================================================

update_specific_agent() {
    local agent_type="$1"
    
    case "$agent_type" in
        claude)
            update_agent_file "$CLAUDE_FILE" "Claude Code" || return 1
            ;;
        gemini)
            update_agent_file "$GEMINI_FILE" "Gemini CLI" || return 1
            ;;
        copilot)
            update_agent_file "$COPILOT_FILE" "GitHub Copilot" || return 1
            ;;
        cursor-agent)
            update_agent_file "$CURSOR_FILE" "Cursor IDE" || return 1
            ;;
        qwen)
            update_agent_file "$QWEN_FILE" "Qwen Code" || return 1
            ;;
        opencode)
            update_agent_file "$AGENTS_FILE" "opencode" || return 1
            ;;
        codex)
            update_agent_file "$AGENTS_FILE" "Codex CLI" || return 1
            log_info "Codex team/runtime uses the specify-owned surface: sp-teams"
            ;;
        windsurf)
            update_agent_file "$WINDSURF_FILE" "Windsurf" || return 1
            ;;
        junie)
            update_agent_file "$JUNIE_FILE" "Junie" || return 1
            ;;
        kilocode)
            update_agent_file "$KILOCODE_FILE" "Kilo Code" || return 1
            ;;
        auggie)
            update_agent_file "$AUGGIE_FILE" "Auggie CLI" || return 1
            ;;
        roo)
            update_agent_file "$ROO_FILE" "Roo Code" || return 1
            ;;
        codebuddy)
            update_agent_file "$CODEBUDDY_FILE" "CodeBuddy CLI" || return 1
            ;;
        qodercli)
            update_agent_file "$QODER_FILE" "Qoder CLI" || return 1
            ;;
        amp)
            update_agent_file "$AMP_FILE" "Amp" || return 1
            ;;
        shai)
            update_agent_file "$SHAI_FILE" "SHAI" || return 1
            ;;
        tabnine)
            update_agent_file "$TABNINE_FILE" "Tabnine CLI" || return 1
            ;;
        kiro-cli)
            update_agent_file "$KIRO_FILE" "Kiro CLI" || return 1
            ;;
        agy)
            update_agent_file "$AGY_FILE" "Antigravity" || return 1
            ;;
        bob)
            update_agent_file "$BOB_FILE" "IBM Bob" || return 1
            ;;
        vibe)
            update_agent_file "$VIBE_FILE" "Mistral Vibe" || return 1
            ;;
        kimi)
            update_agent_file "$KIMI_FILE" "Kimi Code" || return 1
            ;;
        trae)
            update_agent_file "$TRAE_FILE" "Trae" || return 1
            ;;
        pi)
            update_agent_file "$AGENTS_FILE" "Pi Coding Agent" || return 1
            ;;
        iflow)
            update_agent_file "$IFLOW_FILE" "iFlow CLI" || return 1
            ;;
        forge)
            update_agent_file "$AGENTS_FILE" "Forge" || return 1
            ;;
        generic)
            log_info "Generic agent: no predefined context file. Use the agent-specific update script for your agent."
            ;;
        *)
            log_error "Unknown agent type '$agent_type'"
            log_error "Expected: claude|gemini|copilot|cursor-agent|qwen|opencode|codex|windsurf|junie|kilocode|auggie|roo|codebuddy|amp|shai|tabnine|kiro-cli|agy|bob|vibe|qodercli|kimi|trae|pi|iflow|forge|generic"
            exit 1
            ;;
    esac
}

# Helper: skip non-existent files and files already updated (dedup by
# realpath so that variables pointing to the same file — e.g. AMP_FILE,
# KIRO_FILE, BOB_FILE all resolving to AGENTS_FILE — are only written once).
# Uses a linear array instead of associative array for bash 3.2 compatibility.
# Note: defined at top level because bash 3.2 does not support true
# nested/local functions. _updated_paths, _found_agent, and _all_ok are
# initialised exclusively inside update_all_existing_agents so that
# sourcing this script has no side effects on the caller's environment.

_update_if_new() {
    local file="$1" name="$2"
    [[ -f "$file" ]] || return 0
    local real_path
    real_path=$(realpath "$file" 2>/dev/null || echo "$file")
    local p
    if [[ ${#_updated_paths[@]} -gt 0 ]]; then
        for p in "${_updated_paths[@]}"; do
            [[ "$p" == "$real_path" ]] && return 0
        done
    fi
    # Record the file as seen before attempting the update so that:
    # (a) aliases pointing to the same path are not retried on failure
    # (b) _found_agent reflects file existence, not update success
    _updated_paths+=("$real_path")
    _found_agent=true
    update_agent_file "$file" "$name"
}

update_all_existing_agents() {
    _found_agent=false
    _updated_paths=()
    local _all_ok=true

    _update_if_new "$CLAUDE_FILE" "Claude Code"           || _all_ok=false
    _update_if_new "$GEMINI_FILE" "Gemini CLI"             || _all_ok=false
    _update_if_new "$COPILOT_FILE" "GitHub Copilot"        || _all_ok=false
    _update_if_new "$CURSOR_FILE" "Cursor IDE"             || _all_ok=false
    _update_if_new "$QWEN_FILE" "Qwen Code"                || _all_ok=false
    _update_if_new "$AGENTS_FILE" "Codex/opencode/Amp/Kiro/Bob/Pi/Forge" || _all_ok=false
    _update_if_new "$WINDSURF_FILE" "Windsurf"             || _all_ok=false
    _update_if_new "$JUNIE_FILE" "Junie"                || _all_ok=false
    _update_if_new "$KILOCODE_FILE" "Kilo Code"            || _all_ok=false
    _update_if_new "$AUGGIE_FILE" "Auggie CLI"             || _all_ok=false
    _update_if_new "$ROO_FILE" "Roo Code"                  || _all_ok=false
    _update_if_new "$CODEBUDDY_FILE" "CodeBuddy CLI"       || _all_ok=false
    _update_if_new "$SHAI_FILE" "SHAI"                     || _all_ok=false
    _update_if_new "$TABNINE_FILE" "Tabnine CLI"           || _all_ok=false
    _update_if_new "$QODER_FILE" "Qoder CLI"               || _all_ok=false
    _update_if_new "$AGY_FILE" "Antigravity"               || _all_ok=false
    _update_if_new "$VIBE_FILE" "Mistral Vibe"             || _all_ok=false
    _update_if_new "$KIMI_FILE" "Kimi Code"                || _all_ok=false
    _update_if_new "$TRAE_FILE" "Trae"                     || _all_ok=false
    _update_if_new "$IFLOW_FILE" "iFlow CLI"               || _all_ok=false

    # If no agent files exist, create a default Claude file
    if [[ "$_found_agent" == false ]]; then
        log_info "No existing agent files found, creating default Claude file..."
        update_agent_file "$CLAUDE_FILE" "Claude Code" || return 1
    fi

    [[ "$_all_ok" == true ]]
}
print_summary() {
    echo
    log_info "Summary of changes:"
    
    if [[ -n "$NEW_LANG" ]]; then
        echo "  - Added language: $NEW_LANG"
    fi
    
    if [[ -n "$NEW_FRAMEWORK" ]]; then
        echo "  - Added framework: $NEW_FRAMEWORK"
    fi
    
    if [[ -n "$NEW_DB" ]] && [[ "$NEW_DB" != "N/A" ]]; then
        echo "  - Added database: $NEW_DB"
    fi
    
    echo
    log_info "Usage: $0 [claude|gemini|copilot|cursor-agent|qwen|opencode|codex|windsurf|junie|kilocode|auggie|roo|codebuddy|amp|shai|tabnine|kiro-cli|agy|bob|vibe|qodercli|kimi|trae|pi|iflow|forge|generic]"
}

#==============================================================================
# Main Execution
#==============================================================================

main() {
    # Validate environment before proceeding
    validate_environment
    
    log_info "=== Updating agent context files for feature $CURRENT_BRANCH ==="
    
    # Parse the plan file to extract project information
    if ! parse_plan_data "$NEW_PLAN"; then
        log_error "Failed to parse plan data"
        exit 1
    fi
    
    # Process based on agent type argument
    local success=true
    
    if [[ -z "$AGENT_TYPE" ]]; then
        # No specific agent provided - update all existing agent files
        log_info "No agent specified, updating all existing agent files..."
        if ! update_all_existing_agents; then
            success=false
        fi
    else
        # Specific agent provided - update only that agent
        log_info "Updating specific agent: $AGENT_TYPE"
        if ! update_specific_agent "$AGENT_TYPE"; then
            success=false
        fi
    fi
    
    # Print summary
    print_summary
    
    if [[ "$success" == true ]]; then
        log_success "Agent context update completed successfully"
        exit 0
    else
        log_error "Agent context update completed with errors"
        exit 1
    fi
}

# Execute main function if script is run directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
