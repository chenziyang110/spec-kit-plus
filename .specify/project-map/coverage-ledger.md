# Coverage Ledger

## Summary

- generated_by: sp-map-scan
- generated_at: 2026-04-30
- row_count: 16
- critical: 10
- important: 4
- low-risk: 2
- unknown: 0

## Rows

| Row | Category | Depth | Criticality | Scope | Packet | Atlas Targets |
| --- | --- | --- | --- | --- | --- | --- |
| L001 | config, packaging-release | deep-read | critical | `pyproject.toml`, `uv.lock`, root metadata | `core-cli-architecture`, `packaging-release-config` | `root/OPERATIONS.md`, `root/STRUCTURE.md`, `root/INTEGRATIONS.md` |
| L002 | source | deep-read | critical | `src/specify_cli/__init__.py`, CLI command registration | `core-cli-architecture` | `root/ARCHITECTURE.md`, `root/WORKFLOWS.md`, `modules/specify-cli-core/*` |
| L003 | source, state-artifact | deep-read | critical | project-map freshness, learning, testing, verification helpers | `core-cli-architecture`, `hooks-execution-orchestration`, `project-map-atlas-state` | `root/WORKFLOWS.md`, `root/OPERATIONS.md`, `modules/specify-cli-core/*` |
| L004 | integration | deep-read | critical | `src/specify_cli/integrations/**` | `integrations-generated-surfaces` | `root/INTEGRATIONS.md`, `modules/specify-cli-core/ARCHITECTURE.md` |
| L005 | template-generated-surface | deep-read | critical | `templates/commands`, `templates/command-partials`, `templates/passive-skills`, `templates/project-map`, `templates/testing`, worker prompts | `integrations-generated-surfaces`, `project-map-atlas-state` | `root/WORKFLOWS.md`, `root/CONVENTIONS.md`, `modules/templates-generated-surfaces/*` |
| L006 | script | sampled | important | `scripts/bash`, `scripts/powershell`, integration update scripts | `integrations-generated-surfaces`, `packaging-release-config` | `root/OPERATIONS.md`, `root/INTEGRATIONS.md`, `modules/templates-generated-surfaces/STRUCTURE.md` |
| L007 | source | deep-read | critical | `src/specify_cli/execution/**`, result and packet contracts | `hooks-execution-orchestration` | `root/ARCHITECTURE.md`, `root/WORKFLOWS.md`, `modules/specify-cli-core/ARCHITECTURE.md` |
| L008 | source | deep-read | critical | `src/specify_cli/hooks/**`, `src/specify_cli/orchestration/**` | `hooks-execution-orchestration` | `root/ARCHITECTURE.md`, `root/WORKFLOWS.md`, `root/OPERATIONS.md`, `modules/specify-cli-core/WORKFLOWS.md` |
| L009 | runtime | deep-read | critical | `src/specify_cli/codex_team/**`, `src/specify_cli/mcp/**` | `codex-team-runtime` | `root/ARCHITECTURE.md`, `root/INTEGRATIONS.md`, `modules/specify-cli-core/WORKFLOWS.md` |
| L010 | runtime | sampled | important | `extensions/agent-teams/engine/**` TypeScript/Rust runtime | `codex-team-runtime` | `root/INTEGRATIONS.md`, `root/OPERATIONS.md`, `modules/agent-teams-engine/*` |
| L011 | test | sampled | critical | `tests/**` Python test matrix | `testing-verification` | `root/TESTING.md`, module `TESTING.md` files |
| L012 | test | sampled | important | engine Node/Rust tests under `extensions/agent-teams/engine/**/__tests__` and `crates/**/tests` | `testing-verification` | `root/TESTING.md`, `modules/agent-teams-engine/TESTING.md` |
| L013 | documentation | sampled | important | `README.md`, `docs/**`, `.planning/**`, `plans/**`, `newsletters/**` | `docs-planning-operations`, `project-map-atlas-state` | `PROJECT-HANDBOOK.md`, `root/WORKFLOWS.md`, `root/OPERATIONS.md` |
| L014 | state-artifact | deep-read | critical | `AGENTS.md`, `.specify/**`, `PROJECT-HANDBOOK.md`, project-map status/templates | `core-cli-architecture`, `project-map-atlas-state` | `PROJECT-HANDBOOK.md`, `root/CONVENTIONS.md`, `root/OPERATIONS.md` |
| L015 | packaging-release | sampled | important | `.github/**`, `.devcontainer/**`, `extensions/**` catalogs, `presets/**` | `docs-planning-operations`, `packaging-release-config` | `root/INTEGRATIONS.md`, `root/OPERATIONS.md`, `root/STRUCTURE.md` |
| L016 | vendor-cache-build-output | inventory | low-risk | `.git`, `.venv`, caches, `dist`, `.tmp-*`, `.worktrees`, runtime logs | `testing-verification` | `root/STRUCTURE.md`, `root/OPERATIONS.md` |

## Excluded Buckets

- `.git/`: excluded_from_deep_read; Git object database. Revisit for history, blame, or release provenance.
- `.venv/`: excluded_from_deep_read; local virtualenv. Revisit only for environment reproduction.
- `.pytest_cache/`, `.ruff_cache/`: excluded_from_deep_read; tool caches. Revisit only for cache-specific defects.
- `dist/`, `.tmp-dist/`, `.tmp-agent-teams-smoke/`, `runtime-test-output.log`: excluded_from_deep_read; generated outputs. Revisit for packaging/smoke failures.
- `.worktrees/`: excluded_from_deep_read; generated worktrees. Revisit only for worktree-specific runtime issues.

## Reverse Index

- `root/ARCHITECTURE.md`: L002, L007, L008, L009
- `root/STRUCTURE.md`: L001, L006, L014, L015, L016
- `root/CONVENTIONS.md`: L004, L005, L014
- `root/INTEGRATIONS.md`: L001, L004, L006, L009, L010, L015
- `root/WORKFLOWS.md`: L002, L003, L005, L007, L008, L013
- `root/TESTING.md`: L001, L011, L012
- `root/OPERATIONS.md`: L001, L003, L006, L008, L010, L013, L014, L015, L016
- `modules/specify-cli-core/*`: L002, L003, L004, L007, L008, L009, L011
- `modules/agent-teams-engine/*`: L010, L012
- `modules/templates-generated-surfaces/*`: L005, L006
