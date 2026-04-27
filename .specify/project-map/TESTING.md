# Testing

**Last Updated:** 2026-04-27
**Coverage Scope:** repository-wide verification and regression strategy
**Primary Evidence:** tests/, pyproject.toml, README.md, docs/local-development.md, extensions/agent-teams/engine/package.json
**Update When:** test layering, minimum checks, regression-sensitive areas, or runtime verification commands change

## Test Layers

- **Root contract and guidance tests**: validate template wording, docs, CLI help, packaging assets, and route guidance.
- **Integration tests**: validate generated output trees and context files for supported agents.
- **Codex runtime tests**: validate runtime bridge, installer, upgrade path, state lifecycle, and CLI surfaces.
- **Hook/execution/orchestration tests**: validate packet schemas, hook event dispatch, strategy policy, and result handling.

## Test Pyramid and Quality Gates

- The repo is test-heavy at the contract/integration level rather than UI/E2E heavy.
- Primary quality gate is `pytest -q`.
- Secondary gates depend on the touched surface:
  - `uv build` for packaging and bundled asset inclusion
  - `npm --prefix extensions/agent-teams/engine run build` for agent-teams engine changes

## Key Test Directories

- `tests/(root)`: 47 repo-wide contract/doc/template tests
- `tests/codex_team`: 37 Codex runtime and installer tests
- `tests/integrations`: 35 integration-specific and shared inventory tests
- `tests/hooks`: workflow quality hook tests, including learning signal/review/capture/inject hooks
- `tests/orchestration`: 9 execution-strategy and state-store tests
- `tests/execution`: 7 packet/result schema tests
- `tests/contract`: 6 CLI surface contract tests

## Smallest Meaningful Checks

- Atlas/template contract only: `pytest tests/test_project_handbook_templates.py tests/test_alignment_templates.py tests/test_specify_guidance_docs.py -q`
- Integration generation only: `pytest tests/integrations/test_cli.py tests/integrations/test_integration_codex.py -q`
- Codex runtime only: `pytest tests/codex_team -q`
- Packaging sanity: `uv build`

## Capability Verification Map

- Init/scaffolding changes: `tests/integrations/test_cli.py`, `tests/integrations/test_integration_*`
- Template/guidance changes: `tests/test_alignment_templates.py`, `tests/test_extension_skills.py`, `tests/test_specify_guidance_docs.py`
- Atlas freshness changes: `tests/test_project_map_status.py`, `tests/test_project_map_freshness_scripts.py`, `tests/hooks/test_project_map_hooks.py`
- Hook changes: `tests/hooks/`, plus `tests/contract/test_hook_cli_surface.py` when the CLI surface changes
- Packet/result contract changes: `tests/execution/`
- Codex runtime changes: `tests/codex_team/`, `tests/contract/test_codex_team_*`

## Contract Verification Surfaces

- README/quickstart wording is asserted directly in tests.
- Inventory tests assert exact generated file sets for multiple integrations.
- Manifest tests ensure created files are tracked and removable as expected.
- CLI contract tests pin subcommand behavior and structured output.

## Verification Entry Points

- Full regression: `pytest -q`
- Local dev smoke: `python -m src.specify_cli --help`
- Build/package: `uv build`
- Extension engine build: `npm --prefix extensions/agent-teams/engine run build`

## Build, Runtime, and Recovery Verification

- Runtime/backend changes should rerun targeted Codex team tests plus at least one CLI surface contract.
- Atlas contract changes should rerun template-guidance and docs tests, not just integration generation.
- Packaging or force-include asset changes should rerun `tests/test_packaging_assets.py` and `uv build`.

## Change-Impact Verification Matrix

- `src/specify_cli/__init__.py`
  - Run: `pytest tests/integrations/test_cli.py tests/test_specify_guidance_docs.py -q`
- `templates/commands/` or `templates/project-map/`
  - Run: `pytest tests/test_alignment_templates.py tests/test_project_handbook_templates.py tests/test_extension_skills.py -q`
- `src/specify_cli/integrations/base.py` or per-integration modules
  - Run: relevant `tests/integrations/test_integration_*.py`
- `src/specify_cli/project_map_status.py`
  - Run: `pytest tests/test_project_map_status.py tests/test_project_map_freshness_scripts.py tests/hooks/test_project_map_hooks.py -q`
- `src/specify_cli/codex_team/` or `extensions/agent-teams/engine/`
  - Run: `pytest tests/codex_team tests/contract/test_codex_team_* -q`

## Regression-Sensitive Areas

- Exact generated file inventories per integration
- Help text and README/quickstart workflow descriptions
- Atlas freshness/stale classification logic
- Packet/result schema normalization and delegated execution language
- `.codex/config.toml` merge behavior and Codex runtime upgrade path

## When To Expand Verification

- Expand to full `pytest -q` whenever a change touches shared templates, integration base classes, project-map freshness, hook dispatch, or Codex runtime installation.
- Expand to extension-engine build/test commands whenever touching `extensions/agent-teams/engine/`.
