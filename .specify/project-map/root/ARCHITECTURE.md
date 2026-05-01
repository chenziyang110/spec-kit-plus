# Architecture

**Last Updated:** 2026-04-30
**Coverage Scope:** Cross-module architecture, ownership, contracts, and dependency graph.
**Primary Evidence:** `worker-results/core-cli-architecture.json`, `integrations-generated-surfaces.json`, `hooks-execution-orchestration.json`, `codex-team-runtime.json`.
**Update When:** CLI command registration, integration generation, packet/result schemas, hooks, orchestration policy, Codex team runtime, or packaging boundaries change.

## System Shape

The repo is a Python CLI monolith with bundled generated assets and an optional Node/TypeScript/Rust runtime. `src/specify_cli/__init__.py` is the Typer app and command router. The main subsystems are:

- integration generation: `src/specify_cli/integrations/`
- workflow assets: `templates/` and `scripts/`
- quality and delegated execution contracts: `src/specify_cli/execution/`, `src/specify_cli/hooks/`, `src/specify_cli/orchestration/`
- atlas/testing/learning helpers: `project_map_status.py`, `testing_inventory.py`, `learnings.py`, `verification.py`
- Codex team control plane: `src/specify_cli/codex_team/` and `src/specify_cli/mcp/`
- bundled engine: `extensions/agent-teams/engine/`

## Key Components and Responsibilities

- `src/specify_cli/__init__.py`: registers the CLI, owns user-facing commands, calls integration setup, renders status panels, and exposes hook/learning/project-map/team/test/eval helper commands.
- `src/specify_cli/integrations/base.py`: owns template discovery, placeholder processing, generated project-map gates, delegation/result addenda, skill rendering, passive skill copying, and manifest recording.
- `src/specify_cli/project_map_status.py`: owns canonical and legacy status paths, dirty/fresh state, changed-path classification, topic refresh plans, and complete-refresh metadata.
- `src/specify_cli/execution/packet_schema.py` and `result_schema.py`: own worker packet and worker result data contracts.
- `src/specify_cli/hooks/`: owns first-party validation helpers for preflight, state, artifacts, delegation, learning, project-map, read/prompt guards, boundaries, checkpoints, and commit checks.
- `src/specify_cli/orchestration/`: owns the subagents-first dispatch vocabulary, capability snapshots, state files, event logs, scheduler decisions, and review-loop helpers.
- `src/specify_cli/codex_team/`: owns Codex-only team runtime state, dispatch, result submission, installer, sync-back, watcher, doctor, and API facade.

## Internal Boundaries and Critical Seams

- Templates are product code. Changing `templates/commands` or passive skills changes generated downstream behavior even when no Python source changes.
- Integration adapters are the boundary between shared workflow contracts and agent-specific file formats.
- Project-map freshness is a workflow gate, not just documentation metadata.
- Packet/result contracts are shared between workflow prompts, hooks, Codex team runtime, and contract tests.
- Codex team runtime has a Python control plane and a bundled engine; they share state and packaged assets but are not the same runtime layer.

## Dependency Graph and Coupling Hotspots

```text
pyproject.toml
  -> bundles templates/scripts/engine assets

src/specify_cli/__init__.py
  -> integrations registry
  -> project_map_status / learnings / testing_inventory / verification
  -> codex_team runtime helpers
  -> hooks and execution validators

src/specify_cli/integrations/base.py
  -> templates/commands
  -> templates/passive-skills
  -> scripts and integration-specific scripts

templates/commands
  -> tests/test_*template*
  -> generated agent skills/commands/workflows

src/specify_cli/codex_team
  -> extensions/agent-teams/engine
  -> tests/codex_team and tests/contract
```

## High-Value Capabilities

### specify-cli-core
- **Entry**: `src/specify_cli/__init__.py` — Typer app, command registration
- **Truth**: `src/specify_cli/integrations/base.py` — integration registry
- **Key deps**: templates, scripts, tests, pyproject.toml
- **Extension point**: `src/specify_cli/integrations/` — add adapter
- **Do not touch**: upstream agent CLI behavior, external MCP servers
- **Test**: `uv run --extra test pytest -q -n auto`
- **Full docs**: → `modules/specify-cli-core/OVERVIEW.md`

### templates-generated-surfaces
- **Entry**: `templates/commands/` — workflow command templates
- **Truth**: `templates/command-partials/` — shared partials
- **Key deps**: scripts, passive-skills, worker-prompts
- **Extension point**: add new command template + partials
- **Do not touch**: generated output in downstream projects directly
- **Test**: `pytest tests/integrations -q`
- **Full docs**: → `modules/templates-generated-surfaces/OVERVIEW.md`

### agent-teams-engine
- **Entry**: `extensions/agent-teams/engine/src/` — Node/TypeScript
- **Truth**: `extensions/agent-teams/engine/package.json`
- **Key deps**: Rust crates, tmux/psmux, native hooks
- **Extension point**: `extensions/agent-teams/engine/skills/worker/SKILL.md`
- **Do not touch**: Rust crates without running targeted scan packet
- **Test**: `npm --prefix extensions/agent-teams/engine run build`
- **Full docs**: → `modules/agent-teams-engine/OVERVIEW.md`

## Ownership and Truth Map

| Surface | Owner | Truth Files | Consumers |
| --- | --- | --- | --- |
| CLI commands | specify-cli-core | `src/specify_cli/__init__.py` | users, tests, generated docs |
| Integrations | specify-cli-core | `src/specify_cli/integrations/` | generated agent projects |
| Workflow assets | templates-generated-surfaces | `templates/commands`, `templates/passive-skills` | all integrations |
| Freshness | specify-cli-core | `project_map_status.py`, scripts | brownfield gates |
| Execution contracts | specify-cli-core | `execution/`, `hooks/`, `orchestration/` | workflows and team runtime |
| Engine runtime | agent-teams-engine | `extensions/agent-teams/engine/` | Codex team runtime |

## Known Architectural Unknowns

- Rust engine crates need deeper packeted tracing before behavior-level changes.
- External agent CLI semantics are outside repo ownership.
- Local global `specify` installs may not match source checkout behavior.

## Change Propagation Paths

- Template change -> generated agent files -> integration tests -> README/docs guidance.
- Integration base change -> all integrations -> packaging assets -> generated project manifests.
- Packet schema change -> hooks -> Codex team runtime -> generated prompts -> execution tests.
- Project-map status change -> Python helper -> Bash/PowerShell helper -> AGENTS/brownfield gates.
