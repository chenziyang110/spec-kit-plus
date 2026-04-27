# Structure

**Last Updated:** 2026-04-27
**Coverage Scope:** repository-wide code and asset layout
**Primary Evidence:** src/, templates/, scripts/, tests/, extensions/, docs/, presets/, pyproject.toml
**Update When:** directory ownership, key file locations, shared write surfaces, or extension/runtime boundaries change

## Directory Layout

- `src/specify_cli/`: Python product code for CLI commands, integrations, runtime helpers, atlas freshness, testing inventory, and verification.
- `templates/`: bundled workflow, atlas, passive-skill, testing, constitution, and worker-prompt assets copied into initialized projects.
- `scripts/`: shared Bash and PowerShell helper scripts installed into downstream repos.
- `tests/`: contract, integration, orchestration, hook, execution, Codex runtime, and docs guidance tests.
- `extensions/`: extension packaging area; `agent-teams/engine/` holds the bundled Node/TypeScript plus Rust runtime.
- `docs/`: user/operator docs and internal `docs/superpowers/{specs,plans}` design history.
- `presets/`: preset packaging and preset scaffold assets.

## Directory Responsibilities

- `src/specify_cli/__init__.py`: command registration, init flow, operator-facing CLI UX.
- `src/specify_cli/integrations/`: agent-specific install logic and output formatting.
- `src/specify_cli/orchestration/`: strategy, review, and delegation policy helpers.
- `src/specify_cli/execution/`: worker packet and result contract logic.
- `src/specify_cli/hooks/`: first-party workflow quality hooks.
- `src/specify_cli/codex_team/`: Codex runtime installation, runtime bridge, watch/status surfaces.
- `extensions/agent-teams/engine/`: runtime engine build/runtime source.

## Critical File Families

- `templates/commands/*.md`: explicit workflow surface.
- `templates/command-partials/*.md`: shared command fragments used across commands.
- `templates/passive-skills/**/SKILL.md`: automatic routing/guardrail layer installed with skills-based integrations.
- `scripts/bash/*.sh` and `scripts/powershell/*.ps1`: installed helper layer consumed by generated projects.
- `tests/integrations/test_integration_*.py`: generated surface truth for specific agent integrations.

## Key File Locations

- CLI root: `src/specify_cli/__init__.py`
- Integration base contract: `src/specify_cli/integrations/base.py`
- Integration registry: `src/specify_cli/integrations/__init__.py`
- Atlas freshness engine: `src/specify_cli/project_map_status.py`
- Testing inventory: `src/specify_cli/testing_inventory.py`
- Worker packet compiler: `src/specify_cli/execution/packet_compiler.py`
- Hook dispatcher: `src/specify_cli/hooks/engine.py`
- Codex runtime installer: `src/specify_cli/codex_team/installer.py`
- Agent-teams engine package manifest: `extensions/agent-teams/engine/package.json`

## Key Components by Area

- **CLI composition**: `__init__.py`, `agents.py`, `extensions.py`, `presets.py`
- **Runtime safety**: `hooks/`, `execution/`, `verification.py`, `project_map_status.py`
- **Learning/state surfaces**: `learnings.py`, `learning_aggregate.py`
- **Codex runtime**: `codex_team/`, `mcp/teams_server.py`, extension engine
- **Docs-as-product assets**: `templates/`, `scripts/`, `docs/quickstart.md`, `README.md`

## Shared Coordination Files

- `pyproject.toml`: Python package metadata, pytest config, wheel force-include asset list.
- `README.md` and `docs/quickstart.md`: user-facing workflow truth that must match generated guidance.
- `.specify/project-map/status.json` when present in initialized projects: brownfield freshness baseline.
- Integration manifests under `.specify/integrations/*.manifest.json` in generated repos: generated file ownership tracking.

## Consumer and Entry Surfaces

- Human entry: `specify` CLI and generated agent command/skill files in initialized projects.
- Agent entry: generated `sp-*` commands/skills, optional `specify-teams-mcp`, and CLI subcommands under `team`, `hook`, `result`, `learning`, `project-map`.
- Build consumer surfaces: `uv build`, extension-engine `npm` / `cargo` builds.

## Common Extension Paths

- Add a new agent integration under `src/specify_cli/integrations/<name>/` and its corresponding tests in `tests/integrations/`.
- Add a new shared workflow or atlas contract in `templates/`, then update template and integration tests together.
- Add a new hook event in `src/specify_cli/hooks/` and expose it via CLI in `src/specify_cli/__init__.py`.
- Add Codex runtime behavior in `src/specify_cli/codex_team/` first; only touch the extension engine when the Python surface requires runtime support.

## Change Surface Matrix

- `src/specify_cli/__init__.py`
  - Affects: CLI help, command registration, init flow, runtime surfaces, many docs and tests
  - Review with: `README.md`, `docs/quickstart.md`, `tests/integrations/test_cli.py`
- `templates/commands/` or `templates/command-partials/`
  - Affects: generated surfaces for all integrations
  - Review with: `tests/test_alignment_templates.py`, `tests/test_extension_skills.py`, integration generation tests
- `src/specify_cli/integrations/base.py`
  - Affects: almost every integration install path and inventory assertion
  - Review with: `tests/integrations/test_integration_base_*`
- `src/specify_cli/project_map_status.py`
  - Affects: brownfield preflight, atlas status semantics, hook flows
  - Review with: `tests/test_project_map_status.py`, `tests/hooks/test_project_map_hooks.py`
- `src/specify_cli/codex_team/` or `extensions/agent-teams/engine/`
  - Affects: `specify team`, runtime assets, upgrade path, Codex-only docs
  - Review with: `tests/codex_team/*`, `tests/contract/test_codex_team_*`

## Where To Add New Code

- Add new CLI-adjacent Python behavior under `src/specify_cli/` in the narrowest subsystem that already owns that concern.
- Add shared downstream assets under `templates/` or `scripts/`, not ad hoc under docs.
- Add user-facing docs under `README.md` / `docs/` only after the product contract exists in code/templates/tests.
- Do not add new agent-specific branching into unrelated files when the per-integration module can own it.
- Do not add new runtime semantics only to tests or docs; wire them through the canonical product surface first.
