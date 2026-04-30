# Specify CLI Core Overview

**Module ID:** `specify-cli-core`
**Owned Roots:** `src/specify_cli/`, `tests/`, `pyproject.toml`
**Related Root Topics:** `ARCHITECTURE.md`, `WORKFLOWS.md`, `INTEGRATIONS.md`, `TESTING.md`, `OPERATIONS.md`
**Primary Evidence:** `worker-results/core-cli-architecture.json`, `hooks-execution-orchestration.json`, `integrations-generated-surfaces.json`, `codex-team-runtime.json`
**Update When:** CLI commands, integration registry, project-map freshness, hooks, execution contracts, orchestration policy, testing inventory, or Codex team Python control plane changes.

## Purpose

This module is the Python product surface for Spec Kit Plus. It owns the `specify` CLI, the integration registry used by `specify init`, generated project metadata, project-map freshness, learning/testing/eval helper commands, execution packet/result contracts, workflow hooks, orchestration helpers, and the Python control plane for Codex team runtime.

## Why This Module Exists

Without this module boundary, CLI behavior, generated integration setup, delegated execution contracts, and runtime helper state would be spread across templates and docs with no stable owner. Treat this module as the code authority for what commands exist, how local state is validated, and how generated surfaces are produced.

## Shared Surfaces

- `src/specify_cli/__init__.py`: Typer app, command registration, `init`, project-map, hook, learning, testing, eval, and team commands.
- `src/specify_cli/integrations/`: adapter registry and generated file behavior for supported agents.
- `src/specify_cli/execution/`: `WorkerTaskPacket` and `WorkerTaskResult` schemas plus validators.
- `src/specify_cli/hooks/`: first-party validation/helper commands used by generated workflows.
- `src/specify_cli/orchestration/`: execution strategy, state, scheduler, and review-loop helpers.
- `src/specify_cli/codex_team/` and `src/specify_cli/mcp/`: Codex team control plane and optional MCP facade.
- `pyproject.toml`: package metadata, console scripts, dependency set, pytest config, and forced bundled assets.

## Risky Coordination Points

- `src/specify_cli/__init__.py` is a broad command router; small edits can change help text, command availability, init behavior, and tests across the repo.
- `integrations/base.py` affects nearly every generated agent surface.
- `project_map_status.py` must stay aligned with Bash/PowerShell freshness scripts and map workflow templates.
- Packet/result schema changes must propagate to hooks, generated workflow prompts, Codex team runtime, and tests.
- Codex team Python code shares contracts with the bundled engine but remains a separate control plane.

## Where To Read Next

- `ARCHITECTURE.md` for boundaries, components, propagation paths, and truth ownership.
- `STRUCTURE.md` for file placement and extension paths inside `src/specify_cli/`.
- `WORKFLOWS.md` for command flows, state transitions, and handoffs.
- `TESTING.md` for focused verification routes.
- Root `INTEGRATIONS.md` before changing supported agents or external runtime assumptions.
