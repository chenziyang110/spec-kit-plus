# Architecture

**Last Updated:** 2026-04-19
**Coverage Scope:** repository-wide conceptual architecture
**Primary Evidence:** src/, templates/, tests/, README.md
**Update When:** layers, abstractions, boundaries, or truth ownership change

## Pattern Overview

`spec-kit-plus` follows a template-driven CLI architecture. The CLI core loads
integration metadata, installs generated assets into target projects, and
enforces workflow contracts through templates plus tests. The system is
contract-heavy: docs/templates/skills and tests are treated as coupled
interfaces.

## Layers

- CLI layer: `src/specify_cli/__init__.py`, command groups, option parsing,
  init/check/help surfaces.
- Integration layer: `src/specify_cli/integrations/` with base classes and
  per-agent modules (codex, claude, gemini, cursor-agent, forge, etc.).
- Template/scaffold layer: `templates/` shared assets copied into projects
  (`templates/commands/`, `templates/project-map/`, handbook/constitution/spec
  templates).
- Runtime/orchestration layer: `src/specify_cli/orchestration/`, debug/quick
  modules, and Codex-specific runtime helpers under `src/specify_cli/codex_team/`.
- Verification layer: `tests/` contract tests, integration tests, and targeted
  guidance-doc assertions.

## Core Abstractions

- `AGENT_CONFIG` in `src/specify_cli/__init__.py` is the agent metadata source
  of truth.
- Integration base classes define installation and template processing behavior
  by format (markdown, toml, skills).
- Template artifacts in `templates/` are treated as product contract surfaces.
- `.agents/skills/` is a checked-in mirror used to keep generated skill wording
  aligned with templates.

## Main Flows

- Project init flow: `specify init` -> select integration -> install templates,
  scripts, and guidance -> write manifests/context files.
- Workflow authoring flow: edit `templates/commands/*` and related templates ->
  sync mirrors/tests -> validate with pytest.
- Runtime flow (Codex scope): `specify team` commands interact with
  `.specify/codex-team/` state and runtime orchestration boundaries.

## Truth Ownership and Boundaries

- Root orientation truth: `PROJECT-HANDBOOK.md`.
- Topical truth: `.specify/project-map/*.md`.
- Canonical shared templates for generated projects: `templates/`.
- Repo-local mirror for this repository's own operations: `.specify/templates/`.
- Contract verification truth: `tests/` (especially template/guidance/integration
  suites).

## Cross-Cutting Concerns

- Cross-CLI consistency: all integration additions should prefer shared logic
  and shared templates unless capability is integration-specific.
- Backward compatibility: docs and tests must reflect deprecations and bridges.
- Cross-platform operation: bash and PowerShell scripts remain parallel surfaces.
- Drift prevention: README/quickstart/template wording is validated by tests.
