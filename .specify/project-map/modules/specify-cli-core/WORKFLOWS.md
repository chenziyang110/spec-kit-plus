# Specify CLI Core Workflows

**Last Updated:** 2026-04-30
**Coverage Scope:** module-local command flows, state transitions, and handoffs.
**Primary Evidence:** `worker-results/core-cli-architecture.json`, `hooks-execution-orchestration.json`, `codex-team-runtime.json`
**Update When:** command entry points, project state, handoff fields, hook behavior, or team runtime flows change.

## Entry Points and Handoffs

- `specify init`: resolves integration, scaffolds templates/scripts/state, and records generated files.
- `specify project-map *`: checks, marks, clears, records, completes, and reports atlas freshness.
- `specify hook *`: exposes validation and helper commands for generated workflows.
- `specify learning *`: manages passive learning capture and review.
- `specify testing inventory`: reports testable modules from local source manifests.
- `sp-teams`: Codex-only team runtime entry point.
- `specify-teams-mcp`: optional MCP facade over team operations.

## Main Flows

### Init and Integration Generation

1. User calls `specify init` with `--ai` or `--integration`.
2. CLI resolves aliases and integration registry metadata.
3. Integration setup transforms shared templates and copies scripts/passive skills.
4. Manifest and config state are written for generated files.
5. Tests assert expected paths, arguments, and adapter-specific transforms.

### Project-Map Freshness

1. Workflows inspect `PROJECT-HANDBOOK.md` and `.specify/project-map/index/status.json`.
2. If stale or missing, `sp-map-scan` creates scan package and packet contracts.
3. `sp-map-build` executes packets, writes worker results and atlas docs, validates reverse coverage.
4. `complete-refresh` records `map-build` as the refresh reason after canonical files exist.

### Delegated Execution

1. A workflow decides execution strategy using shared policy and runtime capability.
2. Worker packets use `WorkerTaskPacket`.
3. Workers return `WorkerTaskResult`.
4. Hook/result validators confirm changed files, validation results, blockers, concerns, and rule acknowledgement.

### Codex Team Runtime

1. Install/runtime commands create `.specify/teams/runtime.json`, `.specify/config.json`, and state directories.
2. Dispatch creates batches/tasks and launches workers or runtime executor paths.
3. Workers submit structured results.
4. Completion and review commands reconcile results back into state.

## State Transitions

- Project map: `missing` -> `stale` or `possibly_stale` -> scan ready -> build complete -> fresh metadata.
- Learning: command start -> candidate capture -> review -> accepted memory or discarded candidate.
- Orchestration: session -> batch -> lane/task -> result -> review/complete.
- Codex team: install -> session -> dispatch -> worker status/result -> batch complete -> sync/review.

## Cross-Module Expansion Triggers

- Template wording changes require reading `templates-generated-surfaces`.
- Engine runtime changes require reading `agent-teams-engine`.
- Packaging changes require reading root `OPERATIONS.md` and `pyproject.toml`.
- Integration changes require reading root `INTEGRATIONS.md` and relevant generated-surface tests.

## Failure and Recovery Notes

- If `specify` from PATH lacks a current command, rerun with `$env:PYTHONPATH='src'; python -m specify_cli ...`.
- If project-map build has no packet evidence, reject it as structural-only.
- If generated integration tests fail after a base adapter change, inspect adapter-specific exceptions before broad refactors.
- If Codex team state is inconsistent, inspect `.specify/teams/state/` records and run the team doctor surface before editing state by hand.
