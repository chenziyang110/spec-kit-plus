<!-- AUTONOMY DIRECTIVE - DO NOT REMOVE -->
YOU ARE AN AUTONOMOUS CODING AGENT. EXECUTE CLEAR, LOW-RISK TASKS TO COMPLETION WITHOUT ASKING FOR ROUTINE PERMISSION.
DO NOT PAUSE FOR "SHOULD I PROCEED?" WHEN THE NEXT STEP IS OBVIOUS, REVERSIBLE, AND WITHIN THE ACTIVE REQUEST.
FOR ANY SUPPORTED AI CLI IN THIS REPOSITORY, DISPATCH SUBAGENTS FOR INDEPENDENT, BOUNDED PARALLEL SUBTASKS WHEN THAT IMPROVES THROUGHPUT, QUALITY, OR VERIFICATION CONFIDENCE.
FOR CODEX, USE `sp-teams` ONLY WHEN THE WORK NEEDS DURABLE TEAM STATE BEYOND AN IN-SESSION SUBAGENT BURST.
<!-- END AUTONOMY DIRECTIVE -->

## Execution Defaults

For AI CLI workflows in this repository:

- Prefer direct execution for trivial or tightly coupled work.
- Dispatch subagents by default for independent, bounded subtasks when parallel work materially improves speed, quality, or verification confidence.
- Use `sp-teams` for Codex only when execution needs durable team state, explicit join-point tracking, or lifecycle control beyond one in-session subagent burst.
- Choose the lightest path that preserves correctness: direct execution for trivial/tightly coupled work, subagents for bounded parallel work, and `sp-teams` for durable team execution.

## Project Memory

- Passive project memory lives under `.specify/memory/project-rules.md` and `.specify/memory/project-learnings.md`.
- Shared project memory is always available to later work in this repository, not just when a `sp-*` workflow is active.

## Cross-CLI Improvement Policy

- Treat workflow and product improvements as cross-CLI changes by default, not single-integration tweaks.
- If a request mentions one supported CLI as an example, evaluate whether the same improvement should apply to all supported AI CLI integrations.
- Default to shared-template or shared-runtime improvements whenever that preserves correctness.
- Only keep an optimization integration-specific when the capability depends on that CLI's native surface, release scope is intentionally limited, or no equivalent behavior exists for other supported CLIs yet.
- When an improvement ships as integration-specific, document why it is not shared yet and whether other supported CLIs should receive a follow-up adaptation.

# AGENTS.md

## About Spec Kit and Specify

**GitHub Spec Kit** is a comprehensive toolkit for implementing Spec-Driven Development (SDD) - a methodology that emphasizes creating clear specifications before implementation. The toolkit includes templates, scripts, and workflows that guide development teams through a structured approach to building software.

**Specify CLI** is the command-line interface that bootstraps projects with the Spec Kit framework. It sets up the necessary directory structures, templates, and AI agent integrations to support the Spec-Driven Development workflow.

The toolkit supports multiple AI coding assistants, allowing teams to use their preferred tools while maintaining consistent project structure and development practices.

### Current Workflow Guidance

When describing the generated user workflow, teach the current mainline as:

```text
specify -> plan
```

Treat `CLARIFY` as the optional enhancement path when an existing spec needs deeper analysis before planning.
Treat `sp-deep-research` as the optional feasibility and planning handoff gate when the requirements are clear but one or more capabilities still need coordinated research, external evidence, an implementation chain proof, or a disposable demo before planning. Its findings and demo evidence must become explicit inputs to `sp-plan`; do not require it for minor adjustments to existing, already-proven capabilities.
Treat `sp-test` as the compatibility router for project-level testing-system work. Use `sp-test-scan` for read-only evidence, risk tiering, and build-ready lane planning; use `sp-test-build` for leader/subagent construction of the unit testing system from scan-approved lanes. Brownfield coverage programs start from `.specify/testing/UNIT_TEST_SYSTEM_REQUEST.md` emitted by `sp-test-scan`, while preserving the mainline `specify -> plan` guidance.

---

## Adding New Agent Support

This section explains how to add support for new AI agents/assistants to the Specify CLI. Use this guide as a reference when integrating new AI tools into the Spec-Driven Development workflow.

### Overview

Specify supports multiple AI agents by generating agent-specific command files and directory structures when initializing projects. Each agent has its own conventions for:

- **Command file formats** (Markdown, TOML, etc.)
- **Directory structures** (`.claude/commands/`, `.windsurf/workflows/`, etc.)
- **Command invocation patterns** (slash commands, CLI tools, etc.)
- **Argument passing conventions** (`$ARGUMENTS`, `{{args}}`, etc.)

### Current Supported Agents

| Agent                      | Directory              | Format   | CLI Tool        | Description                 |
| -------------------------- | ---------------------- | -------- | --------------- | --------------------------- |
| **Claude Code**            | `.claude/commands/`    | Markdown | `claude`        | Anthropic's Claude Code CLI |
| **Gemini CLI**             | `.gemini/commands/`    | TOML     | `gemini`        | Google's Gemini CLI         |
| **GitHub Copilot**         | `.github/agents/`      | Markdown | N/A (IDE-based) | GitHub Copilot in VS Code   |
| **Cursor**                 | `.cursor/commands/`    | Markdown | N/A (IDE-based) | Cursor IDE (`--ai cursor-agent`) |
| **Qwen Code**              | `.qwen/commands/`      | Markdown | `qwen`          | Alibaba's Qwen Code CLI     |
| **opencode**               | `.opencode/command/`   | Markdown | `opencode`      | opencode CLI                |
| **Codex CLI**              | `.codex/skills/`       | Markdown | `codex`         | Codex CLI (`--ai codex --ai-skills`) |
| **Windsurf**               | `.windsurf/workflows/` | Markdown | N/A (IDE-based) | Windsurf IDE workflows      |
| **Junie**                  | `.junie/commands/`     | Markdown | `junie`         | Junie by JetBrains          |
| **Kilo Code**              | `.kilocode/workflows/` | Markdown | N/A (IDE-based) | Kilo Code IDE               |
| **Auggie CLI**             | `.augment/commands/`   | Markdown | `auggie`        | Auggie CLI                  |
| **Roo Code**               | `.roo/commands/`       | Markdown | N/A (IDE-based) | Roo Code IDE                |
| **CodeBuddy CLI**          | `.codebuddy/commands/` | Markdown | `codebuddy`     | CodeBuddy CLI               |
| **Qoder CLI**              | `.qoder/commands/`     | Markdown | `qodercli`      | Qoder CLI                   |
| **Kiro CLI**               | `.kiro/prompts/`       | Markdown | `kiro-cli`      | Kiro CLI                    |
| **Amp**                    | `.agents/commands/`    | Markdown | `amp`           | Amp CLI                     |
| **SHAI**                   | `.shai/commands/`      | Markdown | `shai`          | SHAI CLI                    |
| **Tabnine CLI**            | `.tabnine/agent/commands/` | TOML | `tabnine`       | Tabnine CLI                 |
| **Kimi Code**              | `.kimi/skills/`        | Markdown | `kimi`          | Kimi Code CLI (Moonshot AI) |
| **Pi Coding Agent**        | `.pi/prompts/`         | Markdown | `pi`            | Pi terminal coding agent    |
| **iFlow CLI**              | `.iflow/commands/`     | Markdown | `iflow`         | iFlow CLI (iflow-ai)        |
| **Forge**                  | `.forge/commands/`     | Markdown | `forge`         | Forge CLI (forgecode.dev)   |
| **IBM Bob**                | `.bob/commands/`       | Markdown | N/A (IDE-based) | IBM Bob IDE                 |
| **Trae**                   | `.trae/rules/`         | Markdown | N/A (IDE-based) | Trae IDE                    |
| **Antigravity**            | `.agent/commands/`     | Markdown | N/A (IDE-based) | Antigravity IDE (`--ai agy --ai-skills`) |
| **Mistral Vibe**           | `.vibe/prompts/`       | Markdown | `vibe`          | Mistral Vibe CLI            |
| **Generic**                | User-specified via `--ai-commands-dir` | Markdown | N/A | Bring your own agent        |

### Step-by-Step Integration Guide

Follow these steps to add a new agent (using a hypothetical new agent as an example):

#### 1. Add to AGENT_CONFIG

**IMPORTANT**: Use the actual CLI tool name as the key, not a shortened version.

Add the new agent to the `AGENT_CONFIG` dictionary in `src/specify_cli/__init__.py`. This is the **single source of truth** for all agent metadata:

```python
AGENT_CONFIG = {
    # ... existing agents ...
    "new-agent-cli": {  # Use the ACTUAL CLI tool name (what users type in terminal)
        "name": "New Agent Display Name",
        "folder": ".newagent/",  # Directory for agent files
        "commands_subdir": "commands",  # Subdirectory name for command files (default: "commands")
        "install_url": "https://example.com/install",  # URL for installation docs (or None if IDE-based)
        "requires_cli": True,  # True if CLI tool required, False for IDE-based agents
    },
}
```

**Key Design Principle**: The dictionary key should match the actual executable name that users install. For example:

- ✅ Use `"cursor-agent"` because the CLI tool is literally called `cursor-agent`
- ❌ Don't use `"cursor"` as a shortcut if the tool is `cursor-agent`

This eliminates the need for special-case mappings throughout the codebase.

**Field Explanations**:

- `name`: Human-readable display name shown to users
- `folder`: Directory where agent-specific files are stored (relative to project root)
- `commands_subdir`: Subdirectory name within the agent folder where command/prompt files are stored (default: `"commands"`)
  - Most agents use `"commands"` (e.g., `.claude/commands/`)
  - Some agents use alternative names: `"agents"` (copilot), `"workflows"` (windsurf, kilocode), `"prompts"` (codex, kiro-cli, pi), `"command"` (opencode - singular)
  - This field enables `--ai-skills` to locate command templates correctly for skill generation
- `install_url`: Installation documentation URL (set to `None` for IDE-based agents)
- `requires_cli`: Whether the agent requires a CLI tool check during initialization

#### 2. Update CLI Help Text

Update the `--ai` parameter help text in the `init()` command to include the new agent:

```python
ai_assistant: str = typer.Option(None, "--ai", help="AI assistant to use: claude, gemini, copilot, cursor-agent, qwen, opencode, codex, windsurf, kilocode, auggie, codebuddy, new-agent-cli, or kiro-cli"),
```

Also update any function docstrings, examples, and error messages that list available agents.

#### 3. Update README Documentation

Update the **Supported AI Agents** section in `README.md` to include the new agent:

- Add the new agent to the table with appropriate support level (Full/Partial)
- Include the agent's official website link
- Add any relevant notes about the agent's implementation
- Ensure the table formatting remains aligned and consistent

#### 4. Update Release Package Script

Modify `.github/workflows/scripts/create-release-packages.sh`:

##### Add to ALL_AGENTS array

```bash
ALL_AGENTS=(claude gemini copilot cursor-agent qwen opencode windsurf kiro-cli)
```

##### Add case statement for directory structure

```bash
case $agent in
  # ... existing cases ...
  windsurf)
    mkdir -p "$base_dir/.windsurf/workflows"
    generate_commands windsurf md "\$ARGUMENTS" "$base_dir/.windsurf/workflows" "$script" ;;
esac
```

#### 4. Update GitHub Release Script

Modify `.github/workflows/scripts/create-github-release.sh` to include the new agent's packages:

```bash
gh release create "$VERSION" \
  # ... existing packages ...
  .genreleases/spec-kit-template-windsurf-sh-"$VERSION".zip \
  .genreleases/spec-kit-template-windsurf-ps-"$VERSION".zip \
  # Add new agent packages here
```

#### 5. Update Agent Context Scripts

##### Bash script (`scripts/bash/update-agent-context.sh`)

Add file variable:

```bash
WINDSURF_FILE="$REPO_ROOT/.windsurf/rules/specify-rules.md"
```

Add to case statement:

```bash
case "$AGENT_TYPE" in
  # ... existing cases ...
  windsurf) update_agent_file "$WINDSURF_FILE" "Windsurf" ;;
  "")
    # ... existing checks ...
    [ -f "$WINDSURF_FILE" ] && update_agent_file "$WINDSURF_FILE" "Windsurf";
    # Update default creation condition
    ;;
esac
```

##### PowerShell script (`scripts/powershell/update-agent-context.ps1`)

Add file variable:

```powershell
$windsurfFile = Join-Path $repoRoot '.windsurf/rules/specify-rules.md'
```

Add to switch statement:

```powershell
switch ($AgentType) {
    # ... existing cases ...
    'windsurf' { Update-AgentFile $windsurfFile 'Windsurf' }
    '' {
        foreach ($pair in @(
            # ... existing pairs ...
            @{file=$windsurfFile; name='Windsurf'}
        )) {
            if (Test-Path $pair.file) { Update-AgentFile $pair.file $pair.name }
        }
        # Update default creation condition
    }
}
```

#### 6. Update CLI Tool Checks (Optional)

For agents that require CLI tools, add checks in the `check()` command and agent validation:

```python
# In check() command
tracker.add("windsurf", "Windsurf IDE (optional)")
windsurf_ok = check_tool_for_tracker("windsurf", "https://windsurf.com/", tracker)

# In init validation (only if CLI tool required)
elif selected_ai == "windsurf":
    if not check_tool("windsurf", "Install from: https://windsurf.com/"):
        console.print("[red]Error:[/red] Windsurf CLI is required for Windsurf projects")
        agent_tool_missing = True
```

**Note**: CLI tool checks are now handled automatically based on the `requires_cli` field in AGENT_CONFIG. No additional code changes needed in the `check()` or `init()` commands - they automatically loop through AGENT_CONFIG and check tools as needed.

## Important Design Decisions

### Using Actual CLI Tool Names as Keys

**CRITICAL**: When adding a new agent to AGENT_CONFIG, always use the **actual executable name** as the dictionary key, not a shortened or convenient version.

**Why this matters:**

- The `check_tool()` function uses `shutil.which(tool)` to find executables in the system PATH
- If the key doesn't match the actual CLI tool name, you'll need special-case mappings throughout the codebase
- This creates unnecessary complexity and maintenance burden

**Example - The Cursor Lesson:**

❌ **Wrong approach** (requires special-case mapping):

```python
AGENT_CONFIG = {
    "cursor": {  # Shorthand that doesn't match the actual tool
        "name": "Cursor",
        # ...
    }
}

# Then you need special cases everywhere:
cli_tool = agent_key
if agent_key == "cursor":
    cli_tool = "cursor-agent"  # Map to the real tool name
```

✅ **Correct approach** (no mapping needed):

```python
AGENT_CONFIG = {
    "cursor-agent": {  # Matches the actual executable name
        "name": "Cursor",
        # ...
    }
}

# No special cases needed - just use agent_key directly!
```

**Benefits of this approach:**

- Eliminates special-case logic scattered throughout the codebase
- Makes the code more maintainable and easier to understand
- Reduces the chance of bugs when adding new agents
- Tool checking "just works" without additional mappings

#### 7. Update Devcontainer files (Optional)

For agents that have VS Code extensions or require CLI installation, update the devcontainer configuration files:

##### VS Code Extension-based Agents

For agents available as VS Code extensions, add them to `.devcontainer/devcontainer.json`:

```json
{
  "customizations": {
    "vscode": {
      "extensions": [
        // ... existing extensions ...
        // [New Agent Name]
        "[New Agent Extension ID]"
      ]
    }
  }
}
```

##### CLI-based Agents

For agents that require CLI tools, add installation commands to `.devcontainer/post-create.sh`:

```bash
#!/bin/bash

# Existing installations...

echo -e "\n🤖 Installing [New Agent Name] CLI..."
# run_command "npm install -g [agent-cli-package]@latest" # Example for node-based CLI
# or other installation instructions (must be non-interactive and compatible with Linux Debian "Trixie" or later)...
echo "✅ Done"

```

**Quick Tips:**

- **Extension-based agents**: Add to the `extensions` array in `devcontainer.json`
- **CLI-based agents**: Add installation scripts to `post-create.sh`
- **Hybrid agents**: May require both extension and CLI installation
- **Test thoroughly**: Ensure installations work in the devcontainer environment

## Agent Categories

### CLI-Based Agents

Require a command-line tool to be installed:

- **Claude Code**: `claude` CLI
- **Gemini CLI**: `gemini` CLI
- **Qwen Code**: `qwen` CLI
- **opencode**: `opencode` CLI
- **Codex CLI**: `codex` CLI (requires `--ai-skills`)
- **Junie**: `junie` CLI
- **Auggie CLI**: `auggie` CLI
- **CodeBuddy CLI**: `codebuddy` CLI
- **Qoder CLI**: `qodercli` CLI
- **Kiro CLI**: `kiro-cli` CLI
- **Amp**: `amp` CLI
- **SHAI**: `shai` CLI
- **Tabnine CLI**: `tabnine` CLI
- **Kimi Code**: `kimi` CLI
- **Mistral Vibe**: `vibe` CLI
- **Pi Coding Agent**: `pi` CLI
- **iFlow CLI**: `iflow` CLI
- **Forge**: `forge` CLI

### IDE-Based Agents

Work within integrated development environments:

- **GitHub Copilot**: Built into VS Code/compatible editors
- **Cursor**: Built into Cursor IDE (`--ai cursor-agent`)
- **Windsurf**: Built into Windsurf IDE
- **Kilo Code**: Built into Kilo Code IDE
- **Roo Code**: Built into Roo Code IDE
- **IBM Bob**: Built into IBM Bob IDE
- **Trae**: Built into Trae IDE
- **Antigravity**: Built into Antigravity IDE (`--ai agy --ai-skills`)

## Command File Formats

### Markdown Format

Used by: Claude, Cursor, GitHub Copilot, opencode, Windsurf, Junie, Kiro CLI, Amp, SHAI, IBM Bob, Kimi Code, Qwen, Pi, Codex, Auggie, CodeBuddy, Qoder, Roo Code, Kilo Code, Trae, Antigravity, Mistral Vibe, iFlow, Forge

**Standard format:**

```markdown
---
description: "Command description"
---

Command content with {SCRIPT} and $ARGUMENTS placeholders.
```

**GitHub Copilot Chat Mode format:**

```markdown
---
description: "Command description"
mode: sp.command-name
---

Command content with {SCRIPT} and $ARGUMENTS placeholders.
```

### TOML Format

Used by: Gemini, Tabnine

```toml
description = "Command description"

prompt = """
Command content with {SCRIPT} and {{args}} placeholders.
"""
```

## Directory Conventions

- **CLI agents**: Usually `.<agent-name>/commands/`
- **Singular command exception**:
  - opencode: `.opencode/command/` (singular `command`, not `commands`)
- **Nested path exception**:
  - Tabnine: `.tabnine/agent/commands/` (extra `agent/` segment)
- **Shared `.agents/` folder**:
  - Amp: `.agents/commands/` (shared folder, not `.amp/`)
- **Codex dedicated folder**:
- Codex: `.codex/skills/` (dedicated Codex folder; requires `--ai-skills`; explicit workflow skills use `$sp-<command>`, passive bundled skills keep their template directory names such as `spec-kit-*`, `tdd-workflow`, or `frontend-design`)
- **Skills-based exceptions**:
- Kimi Code: `.kimi/skills/` (skills; explicit workflow skills use `/skill:sp-<command>`, passive bundled skills keep their template directory names such as `spec-kit-*`, `tdd-workflow`, or `frontend-design`)
- **Shared rule for skills-based integrations**:
- When an integration installs into a `skills/` directory, explicit workflow skills use the `sp-*` namespace and passive bundled skills keep the directory names defined under `templates/passive-skills/`.
- **Prompt-based exceptions**:
  - Kiro CLI: `.kiro/prompts/`
  - Pi: `.pi/prompts/`
  - Mistral Vibe: `.vibe/prompts/`
- **Rules-based exceptions**:
  - Trae: `.trae/rules/`
- **IDE agents**: Follow IDE-specific patterns:
  - Copilot: `.github/agents/`
  - Cursor: `.cursor/commands/`
  - Windsurf: `.windsurf/workflows/`
  - Kilo Code: `.kilocode/workflows/`
  - Roo Code: `.roo/commands/`
  - IBM Bob: `.bob/commands/`
- Antigravity: `.agent/skills/` (`--ai-skills` required; explicit workflow skills use `sp-*`, passive bundled skills keep their template directory names; `.agent/commands/` is deprecated)

## Argument Patterns

Different agents use different argument placeholders:

- **Markdown/prompt-based**: `$ARGUMENTS`
- **TOML-based**: `{{args}}`
- **Forge-specific**: `{{parameters}}` (uses custom parameter syntax)
- **Script placeholders**: `{SCRIPT}` (replaced with actual script path)
- **Agent placeholders**: `__AGENT__` (replaced with agent name)

## Special Processing Requirements

Some agents require custom processing beyond the standard template transformations:

### Copilot Integration

GitHub Copilot has unique requirements:
- Commands use `.agent.md` extension (not `.md`)
- Each command gets a companion `.prompt.md` file in `.github/prompts/`
- Installs `.vscode/settings.json` with prompt file recommendations
- Context file lives at `.github/copilot-instructions.md`

Implementation: Extends `IntegrationBase` with custom `setup()` method that:
1. Processes templates with `process_template()`
2. Generates companion `.prompt.md` files
3. Merges VS Code settings

### Forge Integration

Forge has special frontmatter and argument requirements:
- Uses `{{parameters}}` instead of `$ARGUMENTS`
- Strips `handoffs` frontmatter key (Forge-specific collaboration feature)
- Injects `name` field into frontmatter when missing

Implementation: Extends `MarkdownIntegration` with custom `setup()` method that:
1. Inherits standard template processing from `MarkdownIntegration`
2. Adds extra `$ARGUMENTS` → `{{parameters}}` replacement after template processing
3. Applies Forge-specific transformations via `_apply_forge_transformations()`
4. Strips `handoffs` frontmatter key
5. Injects missing `name` fields
6. Ensures the shared `update-agent-context.*` scripts include a `forge` case that maps context updates to `AGENTS.md` (similar to `opencode`/`codex`/`pi`) and lists `forge` in their usage/help text

### Standard Markdown Agents

Most agents (Bob, Claude, Windsurf, etc.) use `MarkdownIntegration`:
- Simple subclass with just `key`, `config`, `registrar_config` set
- Inherits standard processing from `MarkdownIntegration.setup()`
- No custom processing needed

## Testing New Agent Integration

1. **Build test**: Run package creation script locally
2. **CLI test**: Test `specify init --ai <agent>` command
3. **File generation**: Verify correct directory structure and files
4. **Command validation**: Ensure generated commands work with the agent
5. **Context update**: Test agent context update scripts

## Common Pitfalls

1. **Using shorthand keys instead of actual CLI tool names**: Always use the actual executable name as the AGENT_CONFIG key (e.g., `"cursor-agent"` not `"cursor"`). This prevents the need for special-case mappings throughout the codebase.
2. **Forgetting update scripts**: Both bash and PowerShell scripts must be updated when adding new agents.
3. **Incorrect `requires_cli` value**: Set to `True` only for agents that actually have CLI tools to check; set to `False` for IDE-based agents.
4. **Wrong argument format**: Use correct placeholder format for each agent type (`$ARGUMENTS` for Markdown, `{{args}}` for TOML).
5. **Directory naming**: Follow agent-specific conventions exactly (check existing agents for patterns).
6. **Help text inconsistency**: Update all user-facing text consistently (help strings, docstrings, README, error messages).

## Future Considerations

When adding new agents:

- Consider the agent's native command/workflow patterns
- Ensure compatibility with the Spec-Driven Development process
- Document any special requirements or limitations
- Update this guide with lessons learned
- Verify the actual CLI tool name before adding to AGENT_CONFIG

---

*This documentation should be updated whenever new agents are added to maintain accuracy and completeness.*

<!-- SPEC-KIT:BEGIN -->
## Spec Kit Plus Managed Rules

- `[AGENT]` marks an action the AI must explicitly execute.
- `[AGENT]` is independent from `[P]`.

## Workflow Mainline

- Treat `specify -> plan` as the default path.
- Use `clarify` only when an existing spec needs deeper analysis before planning.
- Use `deep-research` only when requirements are clear but feasibility or the implementation chain must be proven before planning; its research findings, demo evidence, and Planning Handoff become inputs to `plan`.

## Workflow Activation Discipline

- If there is even a 1% chance an `sp-*` workflow or passive skill applies, route before any response or action, including a clarifying question, file read, shell command, repository inspection, code edit, test run, or summary.
- Do not inspect first outside the workflow; repository inspection belongs inside the selected workflow.
- Name the selected workflow or passive skill in one concise line, then continue under that contract.

## Brownfield Context Gate

- `PROJECT-HANDBOOK.md` is the root navigation artifact.
- Deep project knowledge lives under `.specify/project-map/`.
- Before planning, debugging, or implementing against existing code, read `PROJECT-HANDBOOK.md` and the smallest relevant `.specify/project-map/*.md` files.
- If handbook/project-map coverage is missing, stale, or too broad, run the runtime's `map-scan` workflow entrypoint followed by `map-build` before continuing.

## Project Memory

- Passive project memory lives under `.specify/memory/project-rules.md` and `.specify/memory/project-learnings.md`.
- Shared project memory is always available to later work in this repository, not just when a `sp-*` workflow is active.
- Prefer generated project-local Spec Kit workflows, skills, and commands over ad-hoc execution when they fit the task.

## Workflow Routing

- Use `sp-fast` only for trivial, low-risk local changes that do not need planning artifacts.
- Use `sp-quick` for bounded tasks that need lightweight tracking but not the full `specify -> plan -> tasks -> implement` flow.
- Use `sp-specify` when scope, behavior, constraints, or acceptance criteria need explicit alignment before planning.
- Use `sp-deep-research` when a clear requirement still lacks a proven implementation chain and needs coordinated research, optional multi-agent evidence gathering, or a disposable demo before planning.
- Use `sp-debug` when diagnosis or root-cause analysis is still required before a fix path is trustworthy.
- Use `sp-test` as the compatibility router for project-level testing work.
- Use `sp-test-scan` when testing-system coverage needs read-only evidence, risk tiering, module-by-module gap analysis, or build-ready lanes.
- Use `sp-test-build` when scan-approved lanes should construct or refresh the unit testing system through leader/subagent execution.
- Use `sp-tasks` to produce enriched task contracts with agent assignment, context navigation, scope boundaries, and verify commands — enabling subagents to execute without asking the leader for clarification.

## Delegated Execution Defaults

- Use subagents-first execution for independent, bounded work when delegation preserves quality.
- Dispatch one subagent for one safe delegated lane; dispatch parallel subagents for independent safe lanes.
- Use a validated `WorkerTaskPacket` or equivalent execution contract before subagent work begins.
- Do not dispatch from raw task text alone.
- Wait for each subagent's structured handoff before integrating or marking work complete; idle status is not completion evidence.
- Use leader-inline fallback only after recording why delegation is unavailable, unsafe, or not packetized.
- Use `sp-teams` only when durable team state, explicit join-point tracking, result files, or lifecycle control are needed beyond one in-session subagent burst.

## Artifact Priority

- `.specify/memory/constitution.md` is the principle-level source of truth when present.
- `workflow-state.md` under the active feature directory is the stage/status source of truth for resumable workflow progress.
- `alignment.md` and `context.md` under the active feature directory carry locked decisions from `sp-specify` into planning.
- `deep-research.md`, its traceable `Planning Handoff`, and `research-spikes/` under the active feature directory carry feasibility evidence IDs, recommended approach, constraints, rejected options, and demo results from `sp-deep-research` into planning.
- `plan.md` under the active feature directory is the implementation design source of truth once planning begins.
- `tasks.md` under the active feature directory is the execution breakdown source of truth once task generation begins.
- `.specify/testing/TEST_SCAN.md`, `.specify/testing/TEST_BUILD_PLAN.md`, `.specify/testing/TEST_BUILD_PLAN.json`, `.specify/testing/TESTING_CONTRACT.md`, `.specify/testing/TESTING_PLAYBOOK.md`, and `.specify/testing/testing-state.md` constrain testing-system construction, implementation, and debugging when present.
- `.specify/project-map/index/status.json` determines whether handbook/project-map coverage can be trusted as fresh.

## Map Maintenance

- If a change alters architecture boundaries, ownership, workflow names, integration contracts, or verification entry points, refresh `PROJECT-HANDBOOK.md` and the affected `.specify/project-map/*.md` files.
- If that refresh cannot happen in the current pass, mark `.specify/project-map/index/status.json` dirty and explicitly route the next brownfield workflow through `sp-map-scan` followed by `sp-map-build`.
- Do not treat consumed handbook/project-map context as self-maintaining; the agent changing map-level truth is responsible for keeping the atlas-style handbook system current.

- Preserve content outside this managed block.
<!-- SPEC-KIT:END -->
