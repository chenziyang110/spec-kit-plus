# Specify CLI Core Structure

**Last Updated:** 2026-04-30
**Coverage Scope:** module-local file placement, owned directories, and extension points.
**Primary Evidence:** `worker-results/core-cli-architecture.json`, `integrations-generated-surfaces.json`, `testing-verification.json`
**Update When:** owned source roots, command files, helper modules, tests, or packaging ownership changes.

## Owned Roots

- `src/specify_cli/`
- `tests/`
- `pyproject.toml`

## Directory Responsibilities

| Path | Responsibility |
| --- | --- |
| `src/specify_cli/__init__.py` | primary CLI command handlers and subapp wiring |
| `src/specify_cli/integrations/` | integration registry, base classes, adapter packages, manifests |
| `src/specify_cli/execution/` | packet/result contracts, validation, rendering, handoff helpers |
| `src/specify_cli/hooks/` | workflow helper and validation command implementations |
| `src/specify_cli/orchestration/` | subagents-first dispatch and resumable orchestration state |
| `src/specify_cli/codex_team/` | Codex team control-plane commands, state, install, runtime bridge |
| `src/specify_cli/mcp/` | MCP facade for team state and operations |
| `src/specify_cli/project_map_status.py` | atlas freshness model |
| `src/specify_cli/testing_inventory.py` | testable module inventory |
| `src/specify_cli/extensions.py`, `src/specify_cli/presets.py` | extension and preset catalog/install logic |
| `tests/integrations/` | generated adapter behavior |
| `tests/hooks/`, `tests/execution/`, `tests/orchestration/` | workflow contract helpers |
| `tests/codex_team/`, `tests/contract/` | Codex team and API surface contracts |

## Key File Families

- Command router: `__init__.py`, `__main__.py`, `launcher.py`
- Registry and adapters: `integrations/__init__.py`, `integrations/base.py`, `integrations/<agent>/__init__.py`
- State helpers: `project_map_status.py`, `learnings.py`, `testing_inventory.py`, `verification.py`
- Execution contracts: `execution/packet_schema.py`, `execution/result_schema.py`, validators and handoff helpers
- Hook helpers: `hooks/*.py`
- Team runtime: `codex_team/*.py`, `mcp/teams_server.py`

## Shared Write Surfaces

- `.specify/project-map/index/status.json` and `.specify/project-map/status.json`
- `.specify/orchestration/**`
- `.specify/teams/**`
- `.specify/memory/**`
- `.planning/learnings/**`
- Generated project files under agent-specific directories during `specify init`

## Where To Extend This Module

- New CLI command: add to the relevant Typer app in `__init__.py`, then add tests and docs/guidance if user-facing.
- New integration: add `src/specify_cli/integrations/<key>/`, register it in `integrations/__init__.py`, and cover it under `tests/integrations/`.
- New delegated-work contract: extend `execution/` first, then update hooks, generated prompts, and contract tests.
- New freshness behavior: update `project_map_status.py`, freshness scripts, templates, and project-map tests together.
- New Codex team state behavior: update `codex_team/`, MCP facade if exposed, and engine assumptions if runtime assets change.
