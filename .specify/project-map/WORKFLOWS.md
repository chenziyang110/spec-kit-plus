# Workflows

**Last Updated:** 2026-04-27
**Coverage Scope:** repository-wide user and maintainer workflow paths
**Primary Evidence:** src/specify_cli/__init__.py, src/specify_cli/orchestration/policy.py, src/specify_cli/execution/packet_compiler.py, src/specify_cli/hooks/engine.py, README.md, docs/quickstart.md, tests
**Update When:** command entrypoints, handoffs, state files, or neighboring workflow risks change

## Core User Flows

- **Initialize a project**: operator runs `specify init` -> CLI resolves integration and options -> shared templates/scripts are copied -> context/memory files are bootstrapped -> manifests are recorded -> next-step guidance is printed.
- **Mainline planning flow**: generated project runs `specify -> plan -> tasks -> analyze -> implement`; brownfield repos insert `map-codebase` before planning if atlas freshness is insufficient.
- **Atlas refresh flow**: operator runs `map-codebase` -> handbook/project-map docs are regenerated -> `project-map complete-refresh` records the baseline -> later brownfield workflows inspect freshness before trusting the atlas.

## Core Maintainer Flows

- **Add or change an integration**: update `src/specify_cli/integrations/<name>/`, register it, adjust shared help text if needed, then update integration inventory and context tests.
- **Change a workflow template**: edit `templates/commands/` or `templates/command-partials/`, then update template-guidance tests and cross-integration generation tests.
- **Evolve Codex runtime**: modify `src/specify_cli/codex_team/` and, if needed, `extensions/agent-teams/engine/`, then validate upgrade path, runtime state, and contract tests.

## Capability Flows

- **Integration install flow**: `IntegrationBase.setup()` -> copy command templates -> install integration scripts -> shared infra install -> context bootstrapping -> manifest save.
- **Hook flow**: runtime or CLI event -> `run_quality_hook()` -> event-specific validator -> structured `HookResult` -> caller blocks, warns, or resumes.
- **Learning hook flow**: `sp-*` friction signal -> `workflow.learning.signal` pain score -> terminal `workflow.learning.review` gate -> optional `workflow.learning.capture` candidate write -> `workflow.learning.inject` prevention target.
- **Delegated execution flow**: plan/tasks/context -> `compile_worker_task_packet()` -> validate packet -> dispatch worker/runtime -> submit normalized result -> join-point validation.

## Runtime Data and Event Flows

- CLI subcommands dispatch through Typer in `src/specify_cli/__init__.py`.
- Brownfield freshness decisions flow from `project_map_status.py` into `project-map` commands and hook preflight gates.
- Hook events are normalized into canonical event names in `src/specify_cli/hooks/events.py`, then dispatched by `hooks/engine.py`.
- Learning hook events reuse the same dispatcher and write through `learnings.py` so every `sp-*` workflow has one closeout-learning enforcement path.
- Codex runtime events flow through `specify team` commands, state JSON files under `.specify/codex-team/`, and result handoff utilities.

## Key Business Lifecycles

- **Init lifecycle**: requested integration -> files created -> manifests recorded -> optional git init -> user follows generated workflow surfaces.
- **Atlas lifecycle**: missing/stale coverage -> map-codebase regeneration -> status baseline -> later staleness detection after code or contract drift.
- **Codex team lifecycle**: install assets -> runtime doctor/probe -> dispatch -> watch/await -> shutdown/cleanup.

## State and Entity Lifecycles

- `ProjectMapStatus`: `missing` -> `fresh` baseline at `complete-refresh` -> later derived `possibly_stale` or `stale` based on changed files or dirty reasons.
- `WorkerTaskPacket`: compiled from plan/tasks -> validated -> dispatched -> paired with result envelope -> archived as completion evidence.
- Quick/debug workflow state files in downstream projects remain leader-owned truth surfaces; generated templates describe their lifecycle.
- Codex team task lifecycle follows `pending -> in_progress -> completed|failed`, with worker heartbeats and mailbox messages tracked in state JSON.

## Failure and Recovery Flows

- **Atlas stale/missing**: brownfield workflow must route through `map-codebase`, then reload docs.
- **Hook or packet validation failure**: do not proceed to execution; fix missing artifacts, forbidden drift, or invalid references first.
- **Learning review missing**: terminal `resolved` or `blocked` reporting should stop until the workflow either captures a reusable learning or records `review-learning --decision none` with a rationale.
- **Codex runtime backend missing**: `doctor`/`live-probe` explain missing prerequisites; operator repairs environment before dispatch.
- **Upgrade/config merge drift**: restore paths or re-run installer helpers rather than editing manifest-owned state by hand.

## Entry Points, Contracts, and Handoffs

- Main CLI entry: `src/specify_cli/__init__.py`
- Packet contract: `src/specify_cli/execution/packet_schema.py`
- Hook contract: `src/specify_cli/hooks/types.py`
- Learning hook contract: `src/specify_cli/hooks/learning.py`, `src/specify_cli/learnings.py`
- Runtime asset handoff: `.specify/codex-team/runtime.json`, `.specify/config.json`, `.codex/config.toml`
- Generated downstream handoffs: workflow templates, context files, manifests, status JSON

## State Transitions and Compatibility Notes

- `single-lane` is a topology label, not implicit leader-local execution permission.
- `reported_status` must survive normalization when worker-local vocabulary differs from canonical orchestration state.
- Partial project-map refreshes and dirty reasons change how downstream workflows decide whether to trust atlas coverage.
- Generated command naming and folder placement are compatibility-sensitive across integrations.

## Implicit Dependencies and Feature-Flag Gates

- Shared template wording and README/quickstart wording are implicitly coupled through tests.
- Optional `mcp` installation gates whether Codex runtime can advertise MCP wiring.
- Runtime capability detection gates `native-multi-agent` vs `sidecar-runtime` decisions.
- Extension-engine buildability depends on local Node/Cargo toolchains even though the core Python CLI does not.

## Adjacent Workflow Risks

- A template-only change can silently break help text, integration inventories, and workflow assertions in many test files.
- A project-map freshness rule change can force or suppress brownfield routing unexpectedly.
- Codex team installer changes can spill into docs, tests, config merge behavior, and runtime startup assumptions together.

## Entry Commands and Handoffs

- Human CLI: `specify`, `specify team`, `specify project-map`, `specify hook`, `specify result`, `specify learning`
- Local dev: `python -m src.specify_cli --help`, `uv build`, `pytest -q`
- Extension engine: `npm --prefix extensions/agent-teams/engine run build`
