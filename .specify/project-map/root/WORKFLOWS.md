# Workflows

**Last Updated:** 2026-04-30
**Coverage Scope:** User workflows, maintainer flows, state transitions, runtime data flows, and failure/recovery paths.
**Primary Evidence:** `worker-results/docs-planning-operations.json`, `integrations-generated-surfaces.json`, `hooks-execution-orchestration.json`, `project-map-atlas-state.json`.
**Update When:** `sp-*` workflow contracts, state files, command routing, testing workflows, map workflows, or orchestration behavior change.

## User Workflow Mainline

The generated workflow mainline remains:

```text
specify -> plan
```

Common full path:

```text
constitution -> specify -> plan -> tasks -> analyze -> implement
```

Optional feasibility path:

```text
specify -> deep-research -> plan
```

## Brownfield Context Gate

Existing-code work must start with reliable atlas context. If `PROJECT-HANDBOOK.md` or `.specify/project-map/**` is missing, stale, too broad, or insufficient:

```text
sp-map-scan -> sp-map-build
```

`sp-map-scan` writes only the scan package:

- `.specify/project-map/map-scan.md`
- `.specify/project-map/coverage-ledger.md`
- `.specify/project-map/coverage-ledger.json`
- `.specify/project-map/scan-packets/*.md`
- `.specify/project-map/map-state.md`

`sp-map-build` validates that package, executes the packets against live repository paths, writes worker-result evidence, synthesizes atlas docs, validates reverse coverage, and completes freshness.

## Testing Workflow

`sp-test` is a compatibility router:

- Route to `sp-test-scan` when testing evidence, risk lanes, or build-ready lanes are missing.
- Route to `sp-test-build` when scan-approved lanes exist.

Durable testing artifacts live under `.specify/testing/` when generated:

- `TEST_SCAN.md`
- `TEST_BUILD_PLAN.md`
- `TEST_BUILD_PLAN.json`
- `UNIT_TEST_SYSTEM_REQUEST.md`
- `TESTING_CONTRACT.md`
- `TESTING_PLAYBOOK.md`
- `testing-state.md`

## Quick/Fast/Debug/Implement Flow

- `sp-fast`: trivial local fixes only; escalate when the work expands, touches shared surfaces, or needs tests/research.
- `sp-quick`: bounded non-trivial work with `.planning/quick/<id>-<slug>/STATUS.md`.
- `sp-debug`: investigation-first flow for unknown root cause; must prove reproduction and fix path before changing behavior.
- `sp-implement`: leader + subagents execution path over generated tasks and milestone state; uses shared subagents-first dispatch vocabulary and worker packet/result contracts.

## Entry Points, Contracts, and Handoffs

- `specify init`: scaffolds project, generated agent surfaces, memory, scripts, templates, and optional Codex team assets.
- `specify project-map check|mark-dirty|clear-dirty|record-refresh|complete-refresh|refresh-topics|status`: project-map state lifecycle.
- `specify hook *`: first-party helper/validation surface.
- `specify learning *`: passive project learning lifecycle.
- `specify testing inventory`: source-aware test inventory helper.
- `sp-teams`: Codex-only team/runtime surface.
- `specify-teams-mcp`: optional agent-facing MCP facade.

## Runtime Data and Event Flows

- Project-map: status and scan/build state flow through `.specify/project-map/index/status.json`, `.specify/project-map/map-state.md`, and `.specify/project-map/worker-results/*.json`.
- Learning: command start/review/capture flows through `.specify/memory/*` and `.planning/learnings/*`.
- Orchestration: sessions, batches, lanes, tasks, decisions, milestone state, and event logs flow through `.specify/orchestration/`.
- Codex team: sessions, dispatches, results, batches, reviews, workers, mailboxes, phases, events, shutdown, claims, config, monitor, and executor state flow through `.specify/teams/state/`.

## State Transitions and Compatibility Notes

- Project-map status can be `missing`, `fresh`, `possibly_stale`, or `stale`.
- Dirty status overrides git-diff-based freshness and maps reasons to affected topics.
- Uncommitted canonical atlas file changes are still considered changed by freshness inspection until committed, even after a complete-refresh writes fresh status metadata.
- Execution-oriented workflows record `execution_model: subagents-first`.
- Dispatch shape is `one-subagent`, `parallel-subagents`, or `leader-inline-fallback`.
- Execution surface is `native-subagents`, `managed-team`, or `leader-inline`.
- `managed-team` is reserved for durable team state, explicit join-point tracking, result files, or lifecycle control beyond one in-session subagent burst.
- `leader-inline-fallback` requires a recorded reason before local execution.

## Failure and Recovery Flows

- Incomplete scan package: `sp-map-build` must refuse atlas writing and route back to `sp-map-scan`.
- Structural-only atlas refresh: failed build; worker results must include `paths_read`.
- Stale global `specify` executable: use `PYTHONPATH=src; python -m specify_cli ...` or editable install.
- Codex team missing runtime backend: install tmux/psmux and required toolchain.
- Hook/packet validation failure: fix the packet/result or workflow state before claiming completion.

## Key Business Lifecycles

1. Initialize a project with one integration.
2. Generate specs/plans/tasks through shared workflow contracts.
3. Implement through leader + subagents by default, with `leader-inline-fallback` only when delegation is unavailable, unsafe, or not packetized.
4. Keep atlas/testing/learning state fresh as repository truth changes.
5. Verify generated surfaces and packaging before release.

## Known Workflow Unknowns

- Native subagent support differs by runtime; generated prompts describe desired behavior but external runtime availability must be detected.
- Historical `.planning/**` files are not an active roadmap unless `.planning/STATE.md` says so.
