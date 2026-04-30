# Structure

**Last Updated:** 2026-04-30
**Coverage Scope:** Repository directories, file-family ownership, placement rules, and generated/cache boundaries.
**Primary Evidence:** `worker-results/testing-verification.json`, `packaging-release-config.json`, `integrations-generated-surfaces.json`.
**Update When:** Major directories, generated asset locations, packaging force-includes, test layout, or state locations change.

## Top-Level Layout

| Path | Responsibility | Add Here When |
| --- | --- | --- |
| `src/specify_cli/` | Python CLI product code | Adding CLI behavior, integrations, hooks, orchestration, project-map/testing/learning helpers |
| `templates/` | Generated downstream artifacts | Changing workflow prompts, passive skills, project-map/testing templates, worker prompts |
| `scripts/` | Shared shell/PowerShell helpers copied downstream | Updating generated helper behavior or project-map freshness scripts |
| `tests/` | Python regression, contract, integration, hook, execution, orchestration, Codex-team tests | Adding tests for Python CLI and generated surfaces |
| `extensions/` | Extension system docs/catalogs and bundled agent-teams engine | Changing extension catalogs or optional engine runtime |
| `presets/` | Preset catalogs, docs, and self-test/scaffold presets | Adding or validating reusable preset packages |
| `docs/` | User/developer docs and historical superpowers specs/plans | Updating docs, quickstart, installation, design history |
| `.planning/` | Product planning state and historical milestone artifacts | Updating project roadmap/state outside current atlas |
| `.specify/` | Runtime state, memory, project-map atlas, generated workflow state | Managing atlas/memory/runtime state |
| `.github/`, `.devcontainer/` | CI, release, issue templates, devcontainer setup | Updating GitHub/dev environment behavior |

## Critical File Families

- CLI command surface: `src/specify_cli/__init__.py`
- Integration adapters: `src/specify_cli/integrations/**`
- Hook and execution contracts: `src/specify_cli/hooks/**`, `src/specify_cli/execution/**`, `src/specify_cli/orchestration/**`
- Project-map freshness: `src/specify_cli/project_map_status.py`, `scripts/*/project-map-freshness.*`
- Codex team Python runtime: `src/specify_cli/codex_team/**`, `src/specify_cli/mcp/**`
- Bundled engine: `extensions/agent-teams/engine/**`
- Generated workflow source: `templates/commands/**`, `templates/command-partials/**`, `templates/passive-skills/**`
- Atlas templates: `templates/project-map/**`
- Testing workflow templates: `templates/testing/**`

## Key Components by Area

### Python CLI

- `__init__.py`: central command registry and command handlers.
- `integrations/`: adapter registry and file generation.
- `codex_team/`: team runtime state, dispatch, result handling, installer, watcher, doctor.
- `execution/`: packet/result schemas and validators.
- `hooks/`: first-party workflow quality hook implementations.
- `orchestration/`: strategy decisions, state store, scheduler, review loop.
- `extensions.py`, `presets.py`: extension/preset manifest validation and installation.

### Generated Surfaces

- `templates/commands/*.md`: shared workflow command contracts.
- `templates/command-partials/*/shell.md`: shared objective/context inserts.
- `templates/passive-skills/*/SKILL.md`: passive skills installed for skills-based integrations.
- `templates/project-map/**`: root/module atlas templates and index templates.
- `templates/testing/**`: test-scan/test-build durable artifacts.
- `templates/worker-prompts/*.md`: role prompts for delegated work.

### Bundled Runtime

- `extensions/agent-teams/engine/package.json`: Node package and build/test scripts.
- `extensions/agent-teams/engine/src/team/**`: team runtime, state, tmux/session orchestration, worker bootstrap.
- `extensions/agent-teams/engine/src/scripts/notify-hook/**`: native hook notification and dispatch support.
- `extensions/agent-teams/engine/crates/**`: Rust workspace crates.

## Common Extension Paths

- New supported AI agent: add an integration package under `src/specify_cli/integrations/<agent>/`, register in `integrations/__init__.py`, add tests under `tests/integrations/`, update docs when user-facing.
- New workflow command: add `templates/commands/<name>.md`, optional partial under `templates/command-partials/<name>/`, update generated-surface tests and integration expectations.
- New project-map behavior: update map templates, `project_map_status.py`, scripts, and project-map tests.
- New engine runtime behavior: update `extensions/agent-teams/engine/src/**` and Python packaging/installer/tests if assets or state contracts change.

## Consumer and Entry Surfaces

- Users enter through `specify`, `specify-teams-mcp`, generated `sp-*` skills/commands, and optional extension/preset commands.
- Tests consume root and module artifacts through pytest.
- Generated projects consume `templates/`, `scripts/`, and integration scripts.
- Codex team runtime consumes `.specify/teams/state/*` and generated runtime assets.

## Change Surface Matrix

| Change | Review | Minimum Verification |
| --- | --- | --- |
| CLI command or init behavior | `src/specify_cli/__init__.py`, README, integration tests | `pytest tests/integrations/test_cli.py -q` |
| Integration generation | `integrations/base.py`, specific adapter, scripts | `pytest tests/integrations -q` |
| Workflow templates | `templates/commands`, passive skills, docs | `pytest tests/test_*template* tests/test_passive_skill_guidance.py -q` |
| Project-map freshness | Python helper and shell helpers | `pytest tests/test_project_map_status.py tests/test_project_map_freshness_scripts.py -q` |
| Codex team runtime | Python runtime, engine, contracts | `pytest tests/codex_team tests/contract -q`; engine build |
| Packaging assets | `pyproject.toml`, templates, engine | `pytest tests/test_packaging_assets.py -q`; `uv build` |

## Excluded and Generated Buckets

- `.git/`, `.venv/`, `.pytest_cache/`, `.ruff_cache/`, `dist/`, `.tmp-*`, `.worktrees/`, and `runtime-test-output.log` are inventory-only by default.
- Revisit those buckets only when diagnosing environment, cache, packaging output, worktree, or smoke-test failures.
