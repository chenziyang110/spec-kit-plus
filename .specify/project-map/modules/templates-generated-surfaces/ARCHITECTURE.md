# Templates And Generated Surfaces Architecture

**Last Updated:** 2026-04-30
**Coverage Scope:** generated-surface architecture, transformation chain, and ownership boundaries.
**Primary Evidence:** `worker-results/integrations-generated-surfaces.json`, `project-map-atlas-state.json`
**Update When:** template transformation, generated command contracts, passive skills, scripts, or atlas/testing templates change.

## Pattern Overview

Shared templates define canonical workflow behavior, and integration adapters transform them into agent-specific command, skill, prompt, workflow, rule, or TOML surfaces. This module is source-of-truth for generated behavior; `specify-cli-core` owns how the assets are installed.

## Internal Boundaries

- Workflow templates: `templates/commands/`
- Shared command fragments: `templates/command-partials/`
- Passive skills: `templates/passive-skills/`
- Atlas templates: `templates/project-map/`
- Testing templates: `templates/testing/`
- Worker prompts: `templates/worker-prompts/`
- Generated helper scripts: `scripts/` and integration-specific script folders

## Key Components and Responsibilities

| Component | Responsibility |
| --- | --- |
| `templates/commands/map-scan.md` | scan package contract for brownfield atlas refresh |
| `templates/commands/map-build.md` | packet execution, worker-result, atlas synthesis, and reverse coverage contract |
| `templates/passive-skills/spec-kit-project-map-gate/SKILL.md` | passive routing gate for stale/missing atlas context |
| `templates/passive-skills/subagent-driven-development/SKILL.md` | generated guidance for packeted delegation where supported |
| `templates/project-map/**` | canonical atlas layer templates |
| `templates/testing/**` | durable test-system scan/build artifacts |
| `scripts/*/project-map-freshness.*` | generated freshness helper parity scripts |
| `scripts/*/update-agent-context.*` | generated agent-context update scripts |

## Change Propagation Paths

- Command template change -> generated agent commands/skills -> integration tests -> user workflow docs.
- Passive skill change -> skills-based integrations -> routing behavior -> generated workflow expectations.
- Project-map template change -> map-build output contract -> handbook/layered contract tests.
- Script change -> downstream initialized projects -> script parity tests and packaging assets.
- Worker prompt change -> delegated execution behavior -> packet/result handoff expectations.

## Truth Ownership and Boundaries

- The exact workflow text lives in `templates/commands/`.
- Agent-specific formatting lives in `specify-cli-core` integration adapters.
- Atlas template structure lives in `templates/project-map/`; actual repo atlas content lives under `.specify/project-map/`.
- Testing workflow artifact structure lives in `templates/testing/`; actual generated test planning state lives under `.specify/testing/`.

## Known Module Unknowns

- External agent runtimes may interpret generated prompts differently.
- Some generated scripts depend on local shell behavior and should be checked in both Bash and PowerShell tests when changed.
