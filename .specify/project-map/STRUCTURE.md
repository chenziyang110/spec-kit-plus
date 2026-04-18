# Structure

**Last Updated:** 2026-04-19
**Coverage Scope:** repository-wide code and asset layout
**Primary Evidence:** src/, templates/, tests/, .specify/
**Update When:** directory ownership, key file locations, or shared write surfaces change

## Directory Layout

- `src/specify_cli/` - CLI implementation and runtime/integration modules.
- `templates/` - shared generated-project templates and command templates.
- `.agents/skills/` - checked-in skill mirrors for major workflows.
- `scripts/` - bash and PowerShell automation scripts.
- `tests/` - unit/contract/integration tests.
- `.specify/` - repo-local template/memory/project-map artifacts for this repo's
  own workflow guidance.
- `docs/` - user and maintainer documentation (`quickstart`, install, upgrade).

## Directory Responsibilities

- `src/specify_cli/__init__.py`: entrypoint, command routing, init logic, agent
  registration bridge.
- `src/specify_cli/integrations/base.py`: integration installation primitives.
- `src/specify_cli/integrations/<agent>/`: agent-specific folder/format behavior.
- `templates/commands/`: workflow behavior contracts consumed by integrations.
- `templates/project-handbook-template.md` and `templates/project-map/`: handbook
  navigation scaffolding for generated projects.
- `tests/integrations/`: generated project and integration installation checks.

## Key File Locations

- CLI core: `src/specify_cli/__init__.py`
- Integration registry/base: `src/specify_cli/integrations/__init__.py`,
  `src/specify_cli/integrations/base.py`
- Root docs: `README.md`, `docs/quickstart.md`, `CHANGELOG.md`
- Live handbook: `PROJECT-HANDBOOK.md`
- Live topical map: `.specify/project-map/*.md`

## Shared Coordination Files

- `AGENTS.md` defines repository execution and agent instructions.
- `templates/constitution-template.md` plus `.specify/templates/constitution-template.md`
  govern constitution defaults and local mirror consistency.
- `.specify/memory/constitution.md` is this repo's active constitution state.
- `tests/test_specify_guidance_docs.py` enforces README/quickstart guidance.

## Where To Add New Code

- New CLI command behavior: `src/specify_cli/__init__.py` or dedicated module
  under `src/specify_cli/` if scoped.
- New integration: add module under `src/specify_cli/integrations/<tool>/` and
  register in central config.
- New shared generation asset: `templates/` and matching tests under `tests/`.
- Repository guidance/navigation updates: `PROJECT-HANDBOOK.md`,
  `.specify/project-map/`, README/quickstart/changelog, and coupled tests.
