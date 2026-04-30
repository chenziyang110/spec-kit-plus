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

### Capability: Project Initialization And Integration Install

- Owner: `specify-cli-core`
- Truth lives: `src/specify_cli/__init__.py`, `src/specify_cli/integrations/`, `templates/`, `scripts/`
- Entry points: `specify init`, `--ai`, `--integration`, `--constitution-profile`, `--preset`
- Downstream consumers: generated projects, agent CLIs/IDEs, integration tests
- Extend here: add adapter classes under `src/specify_cli/integrations/<agent>/` and register in `INTEGRATION_REGISTRY`
- Do not extend here: do not special-case agent generation in random CLI branches when a base integration hook can own it
- Key contracts: real CLI executable names are integration keys; generated destinations must stay inside project root; manifest records generated files
- Change propagation: CLI help, README, integration tests, template packaging, update-context scripts
- Minimum verification: `pytest tests/integrations tests/test_agent_config_consistency.py -q`
- Failure modes: wrong generated path, stale help text, unsupported external CLI assumption, manifest drift
- Confidence: Verified

### Capability: Brownfield Atlas Lifecycle

- Owner: `specify-cli-core`
- Truth lives: `templates/commands/map-scan.md`, `templates/commands/map-build.md`, `src/specify_cli/project_map_status.py`, `.specify/project-map/`
- Entry points: `sp-map-scan`, `sp-map-build`, `specify project-map *`, `specify hook complete-refresh`
- Downstream consumers: every brownfield planning/debug/implementation workflow
- Extend here: update map templates, status helpers, freshness scripts, project-map tests
- Do not extend here: do not hide map refresh inside unrelated workflow commands
- Key contracts: scan writes scan package only; build executes packets and writes atlas; complete-refresh uses reason `map-build`
- Change propagation: AGENTS managed block, generated workflow guidance, hook helpers, freshness scripts
- Minimum verification: `pytest tests/test_map_scan_build_template_guidance.py tests/test_project_map_status.py tests/test_project_map_freshness_scripts.py -q`
- Failure modes: structural-only refresh, missing packets, stale status, uncommitted atlas files causing freshness check to report stale
- Confidence: Verified

### Capability: Delegated Execution And Quality Hooks

- Owner: `specify-cli-core`
- Truth lives: `src/specify_cli/execution/`, `src/specify_cli/hooks/`, `src/specify_cli/orchestration/`
- Entry points: `specify hook *`, generated workflow prompts, Codex team dispatch/result surfaces
- Downstream consumers: `sp-implement`, `sp-debug`, `sp-quick`, `sp-test-*`, `sp-map-*`, Codex team runtime
- Extend here: packet schema, result schema, hook implementations, subagent dispatch policy, state store
- Do not extend here: do not invent command-local packet shapes that bypass shared schemas
- Key contracts: `WorkerTaskPacket`, `WorkerTaskResult`, `choose_subagent_dispatch`, hook JSON payloads
- Change propagation: generated prompts, tests/execution, tests/hooks, tests/orchestration, contract tests
- Minimum verification: `pytest tests/execution tests/hooks tests/orchestration -q`
- Failure modes: packet/result mismatch, hook false positives, dispatch policy overclaiming runtime capability
- Confidence: Verified

### Capability: Codex Team Runtime

- Owner: `specify-cli-core` for Python control plane; `agent-teams-engine` for bundled engine
- Truth lives: `src/specify_cli/codex_team/`, `src/specify_cli/mcp/teams_server.py`, `extensions/agent-teams/engine/`
- Entry points: `sp-teams`, `specify-teams-mcp`, generated Codex skills, engine runtime CLI
- Downstream consumers: Codex projects, workers, result handoff validation, team watcher
- Extend here: Python command/API/state files for CLI behavior; engine `src/team` or `src/scripts/notify-hook` for runtime internals
- Do not extend here: do not make non-Codex integrations depend on Codex-only runtime assets
- Key contracts: `.specify/teams/state/*`, dispatch/result/batch records, notify hook config, MCP facade tools
- Change propagation: pyproject force-includes, tests/codex_team, engine build, Codex integration generation
- Minimum verification: `pytest tests/codex_team tests/contract/test_codex_team_cli_surface.py tests/test_teams_mcp_server.py -q`; `npm --prefix extensions/agent-teams/engine run build`
- Failure modes: missing tmux/psmux, stale engine dist, missing toolchain, result schema mismatch
- Confidence: Inferred for Rust internals; Verified for Python control plane

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
