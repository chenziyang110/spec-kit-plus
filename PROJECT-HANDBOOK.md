# Project Handbook

**Last Updated:** 2026-04-20
**Purpose:** Root navigation artifact for `spec-kit-plus`.

## System Summary

`spec-kit-plus` is a Python CLI toolkit for Spec-Driven Development. The main
entrypoint is `src/specify_cli/__init__.py`, which orchestrates project
initialization, agent integration wiring, command surfaces, and supporting
assets. The repository combines:

- CLI and orchestration runtime code under `src/specify_cli/`
- generated workflow assets under `templates/`
- scripts for update/sync tasks under `scripts/bash/` and
  `scripts/powershell/`
- contract and integration verification under `tests/`

## How To Read This Project

1. Start here for orientation and system boundaries.
2. Use `Topic Map` to pick only the topical docs relevant to your touched
   area.
3. Read live code after topical docs when coverage is missing, stale, or too
   broad.

## Shared Surfaces

- `src/specify_cli/__init__.py` (CLI entrypoint, init/install orchestration,
  command registration)
- `templates/commands/` (workflow contract for generated command/skill content)
- `templates/` (shared templates copied into initialized projects)
- `src/specify_cli/integrations/` (agent-specific generation behavior)
- `scripts/bash/` and `scripts/powershell/` (agent-context and project scripts)
- `tests/integrations/` and template/guidance tests under `tests/`

## Risky Coordination Points

- Shared template installation logic in `src/specify_cli/__init__.py`
- Integration inventory/behavior tests in `tests/integrations/`
- Language alignment across `templates/commands/`, README/quickstart, and
  generated surfaces
- Cross-platform script parity between `scripts/bash/` and
  `scripts/powershell/`
- Repo docs and guidance tests coupling (`README.md`, `docs/quickstart.md`,
  `tests/test_specify_guidance_docs.py`)

## Topic Map

- `.specify/project-map/ARCHITECTURE.md` - layers, abstractions, truth
  ownership
- `.specify/project-map/STRUCTURE.md` - where code and assets live
- `.specify/project-map/CONVENTIONS.md` - naming, imports, style, error rules
- `.specify/project-map/INTEGRATIONS.md` - external tooling and runtime
  dependencies
- `.specify/project-map/WORKFLOWS.md` - user/maintainer workflows and handoffs
- `.specify/project-map/TESTING.md` - test layers and minimum checks
- `.specify/project-map/OPERATIONS.md` - operator flows, recovery, and
  troubleshooting

## Update Triggers

- `src/specify_cli/` ownership, layering, or module boundaries change
- `templates/` or generated asset layout/meaning changes
- new agent integration support or integration contract changes
- command/workflow language shifts that impact generated skills/docs
- testing strategy or critical coverage surfaces change
- runtime or operational assumptions change (for example `specify team` scope)

## Recent Structural Changes

- Introduced handbook navigation model: root `PROJECT-HANDBOOK.md` plus topical
  `.specify/project-map/` docs.
- Replaced legacy reliance on `项目技术文档.md` with handbook/project-map as the
  only current navigation truth.
- Added `sp-map-codebase` as the explicit generation and refresh surface for
  brownfield navigation updates.
- Aligned local `.specify/templates/` and `.specify/memory/constitution.md`
  with handbook-first navigation guidance.
