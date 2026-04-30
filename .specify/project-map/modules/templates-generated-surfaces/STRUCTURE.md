# Templates And Generated Surfaces Structure

**Last Updated:** 2026-04-30
**Coverage Scope:** generated asset placement, directory responsibilities, and shared write surfaces.
**Primary Evidence:** `worker-results/integrations-generated-surfaces.json`, `packaging-release-config.json`
**Update When:** template directories, scripts, passive skills, generated artifact locations, or packaging force-includes change.

## Owned Roots

- `templates/`
- `scripts/`
- `src/specify_cli/integrations/*/scripts/`

## Directory Responsibilities

| Path | Responsibility |
| --- | --- |
| `templates/commands/` | shared workflow command contracts |
| `templates/command-partials/` | reusable command sections inserted into generated workflows |
| `templates/passive-skills/` | passive skills bundled into skills-based integrations |
| `templates/project-map/` | handbook, index, root, module, and deep-detail atlas templates |
| `templates/testing/` | test-scan/test-build planning and contract artifacts |
| `templates/worker-prompts/` | worker role prompts for delegated execution |
| `scripts/bash/` | Bash helper scripts copied downstream |
| `scripts/powershell/` | PowerShell helper scripts copied downstream |
| `src/specify_cli/integrations/*/scripts/` | adapter-specific helper scripts |

## Key File Families

- `templates/commands/<workflow>.md`
- `templates/command-partials/<workflow>/shell.md`
- `templates/passive-skills/<skill>/SKILL.md`
- `templates/project-map/root/*.md`
- `templates/project-map/modules/*.md`
- `templates/testing/*.md`
- `scripts/bash/*.sh`
- `scripts/powershell/*.ps1`

## Shared Write Surfaces

- Downstream agent directories such as `.codex/skills/`, `.claude/commands/`, `.github/agents/`, `.windsurf/workflows/`, and other integration-specific paths.
- Downstream `.specify/project-map/**`, `.specify/testing/**`, and `.specify/memory/**` templates.
- Wheel contents controlled by `pyproject.toml` force-includes.

## Where To Extend This Module

- New workflow: add a command template, optional partial, generated-surface tests, and integration expectations.
- New passive skill: add `templates/passive-skills/<name>/SKILL.md`, then ensure skills-based integrations copy it.
- New atlas layer: update `templates/project-map/**`, project-map tests, and map-build guidance.
- New helper script: add Bash/PowerShell parity where relevant and include packaging tests.
