# Agent Teams Engine Workflows

**Last Updated:** 2026-04-30
**Coverage Scope:** engine-local runtime flows, state handoffs, and build/test paths.
**Primary Evidence:** `worker-results/codex-team-runtime.json`, `testing-verification.json`
**Update When:** runtime entry points, dispatch behavior, notify hooks, worker bootstrap, or build/test scripts change.

## Entry Points and Handoffs

- Python `sp-teams` commands install and control the runtime.
- Optional `specify-teams-mcp` surfaces expose operations to agents.
- Engine scripts provide runtime and notify-hook behavior.
- Workers read prompts/skills and submit results through shared state contracts.

## Main Flows

### Runtime Install and Launch

1. Python installer writes team runtime metadata and config.
2. Runtime bridge selects psmux on native Windows or tmux elsewhere when available.
3. Engine assets are located from packaged or source paths.
4. Runtime process/session starts and writes state under `.specify/teams/state/`.

### Dispatch and Result

1. Python auto-dispatch materializes tasks and batches.
2. Runtime launches or coordinates workers.
3. Workers produce structured results.
4. Python completion/review reconciles result records.

### Notify Hook

1. Codex notify configuration calls bundled hook script.
2. Hook reads team state/config.
3. Dispatch or status signals are emitted through shared records.

## State Transitions

- Engine unavailable -> doctor/runtime bridge reports missing toolchain.
- Installed -> session initialized -> dispatch active -> worker results submitted -> batch completed.
- Config changed -> runtime metadata regenerated -> next launch uses updated settings.

## Cross-Module Expansion Triggers

- If `.specify/teams/state` shape changes, inspect `specify-cli-core` state readers/writers and MCP facade.
- If packaged asset paths change, inspect `pyproject.toml` and packaging tests.
- If generated Codex team skills change, inspect `templates-generated-surfaces`.

## Failure and Recovery Notes

- Missing Node/npm/cargo/codex/tmux/psmux should be diagnosed through the Python team doctor/runtime bridge before source edits.
- Engine build failures should be handled in the engine module first, then checked against Python packaging assumptions.
- Rust runtime behavior changes need targeted cargo tests, not only Python pytest.
