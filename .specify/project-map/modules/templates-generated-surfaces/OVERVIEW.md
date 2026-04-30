# Templates And Generated Surfaces Overview

**Module ID:** `templates-generated-surfaces`
**Owned Roots:** `templates/`, `scripts/`, `src/specify_cli/integrations/*/scripts/`
**Related Root Topics:** `WORKFLOWS.md`, `CONVENTIONS.md`, `INTEGRATIONS.md`, `TESTING.md`, `OPERATIONS.md`
**Primary Evidence:** `worker-results/integrations-generated-surfaces.json`, `project-map-atlas-state.json`, `docs-planning-operations.json`
**Update When:** workflow templates, command partials, passive skills, generated scripts, project-map/testing templates, or worker prompts change.

## Purpose

This module owns the source artifacts that become downstream agent workflows, skills, prompts, project-map templates, testing artifacts, worker prompts, and helper scripts. It is the repository's generated-behavior layer.

## Why This Module Exists

Generated files are a primary product surface. A wording or path change in `templates/` can alter behavior across many agent integrations even when no Python code changes. This module keeps those assets visible as code-level contracts.

## Shared Surfaces

- `templates/commands/*.md`: canonical workflow command contracts.
- `templates/command-partials/*/shell.md`: reusable objective/context inserts.
- `templates/passive-skills/*/SKILL.md`: passive skills installed into skills-based integrations.
- `templates/project-map/**`: handbook, index, root, and module atlas templates.
- `templates/testing/**`: test-scan/test-build durable artifact templates.
- `templates/worker-prompts/*.md`: role prompts for delegated work.
- `scripts/bash/**` and `scripts/powershell/**`: helper scripts copied to generated projects.

## Risky Coordination Points

- `map-scan.md` and `map-build.md` define the brownfield gate and must stay aligned with project-map status helpers.
- Passive skills can change routing behavior for skills-based integrations.
- Scripts must stay compatible across Bash and PowerShell variants.
- Adapter-specific script directories under `src/specify_cli/integrations/*/scripts/` are product assets and packaging inputs.

## Where To Read Next

- `ARCHITECTURE.md` for the template-to-integration propagation model.
- `STRUCTURE.md` for asset families and placement rules.
- `WORKFLOWS.md` for generated command behavior.
- `TESTING.md` for template and packaging verification.
- Root `CONVENTIONS.md` for naming, state, and compatibility rules.
