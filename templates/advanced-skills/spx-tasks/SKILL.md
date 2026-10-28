---
name: spx-tasks
description: Dependency-aware task-generation workflow for advanced coding models. Use when a validated plan exists and execution needs concrete outcomes, guardrails, write scopes, batches, and join points.
---

# SPX Tasks

Read `references/project-learning.md` and apply its consume-capture policy.
Read `references/native-subagents.md` when task-generation lanes are delegated.
Read `references/workflow-runtime.md` and let its CLI own phase state.
Read `references/execution-bootstrap.md`.
Read `references/project-cognition.md`, using cognition intent `plan`,
`references/task-graph-contract.md`, and `references/consequence-gate.md` only
when the plan carries triggered obligations. Resolve the active feature with the
installed `.specify/scripts/bash/check-prerequisites.sh --json` or PowerShell
equivalent; resolve task-generation inputs and keep implementation blocked.
Resume the selected feature's task-generation state in the current worktree.
Register only its allowed task-artifact scope on Work Board; preserve planning
inputs, task-index ownership, and readiness gates. Do not create another branch
or worktree or implement product source.
Transition from the validated `plan` stage into `tasks` through the
workflow runtime before creating task artifacts.
Read `references/ui-quality-gate.md` when the plan carries a UI design contract.

Query `plan-contract.json` first through `specify-runtime artifact show` and verify named owners, paths, and verification
entry points against cognition-selected live evidence. Read
`test_design_gate.decision` as exactly `not_selected`, `selected`, or
`required`. For selected/required input, require the producer-built Tasks
projection and verify it first with
`{{specify-subcmd:specify-runtime test-design projection-verify --feature-dir <feature-dir> --projection-ref <project-relative-ref> --expected-sha256 <sha256> --format json}}`.
Consume the canonical typed pointer-only projection read-only; never create,
patch, replace, weaken, or copy its publication, projection, cases, data,
coverage, gaps, or audit. If the independent `$spx-test-design` producer also
emitted the compatibility `handoff-to-tasks.json`, query it through the artifact
runtime, require its source fingerprint and claim status to be current, and
treat its refs as authoritative input for task shaping rather than
reconstructing test intent from prose. Route no-root, active, blocked,
unpublished, stale, tampered, foreign, or requested missing selected/required
input to `$spx-test-design`; `not_selected` with no root is the legal optional
skip. If planning truth is missing or stale,
stop and route to `$spx-specify`, `$spx-plan`, or `$spx-deep-research`; do not
hide design work inside a task.

The pointer-only **test-design handoff** remains the Tasks CLI compatibility
contract alongside the verified Tasks projection; neither is model-authored.
The Plan binding may be all-null pending or Plan-only and never authorizes
Tasks. Tasks verifies its separate feature projection for read-only
decomposition; the fresh feature handoff plus runtime-owned task-index binding
provides final authorization and all-and-only ref enforcement.

If an existing package becomes stale after a verified Test Design refresh or
adopted Plan UI contract, read `references/rebind.md` before ordinary Tasks
mutations or readiness checks. Use guarded `specify-runtime tasks rebind`;
preserve accepted/deferred history and never delete/rebuild the package or edit
its binding fields. Missing capability routes to runtime repair/upgrade.

Run
`{{specify-subcmd:specify-runtime hook validate-state --command tasks --feature-dir <feature-dir> --autofix --format json}}`
and withhold dependent writes if it remains invalid. Diagnose and repair
current-owner state through supported runtime routes, then rerun this gate in
the same invocation; never hand-edit state or bypass validation. A proven
upstream truth gap still returns to its owner. Require the plan's ready transition to
`sp-tasks`, locked target boundary, current revision, and zero unresolved
planning blockers.

Build the semantic task package through
`{{specify-subcmd:specify-runtime tasks build --feature-dir <feature-dir> --definition-json '<inline-json|@path|->' --format json}}`,
refine it only with `tasks upsert --task-json '<object|@path|->'`,
`tasks set-root --patch-json '<object|@path|->'` (never CLI-owned `transition`),
or `tasks remove`, finish with `tasks finalize`, and create the implementation
transition with `tasks handoff --feature-dir <feature-dir> --target implement --format json`.
Prefer `@path` on Windows for large packages. The CLI expands the canonical
template and atomically renders `task-index.json` plus `tasks.md`; never create,
patch, replace, or delete either projection directly. Every task needs a stable
ID, complete outcome (`objective`/`title`), dependencies, write scope,
acceptance (`acceptance`/`done_condition`), verification, and must-preserve
obligations. Mark parallel only when inputs are stable and writes do not
overlap; name the join and combined check. Write-overlapping task-generation
lanes use serial `one-subagent` (or leader-inline only under adaptive light /
recorded standard degradation)—never unrecorded leader synthesis after a
parallel conflict.
When present, `test_case_refs` and `test_data_refs` are task-local authoritative
inputs copied from that test-design handoff and preserved into the canonical
task graph for later JIT packet compilation. `$spx-test-design` is the public
Advanced producer; its handoff remains pointer-only and the canonical runtime
next stage remains `/sp.tasks`.
`tasks build` binds the handoff ref/SHA-256, source fingerprint, state revision,
and artifact digests into runtime-owned task-index fields. Never author or
patch those fields. Every task ref must be a handoff member; before finalize,
the task-wide unions must consume all and only the handoff case/data arrays.
Finalize and handoff recompute all bindings and reject stale, tampered, forged,
foreign, missing, or partial consumption.
Treat `expected_write_scope` as explicit write authority for dispatch. Each
entry must be an exact future file, an exact directory path, or a bounded
subtree ending with `/**`; filename globs such as `*_test.go`, `?`, `[]`,
`/*`, or middle `**` are invalid. If a task may create or change companion
tests, migrations, fixtures, generated files, or other companion artifacts,
include them explicitly in `expected_write_scope`. When the exact filename is
unknown, use the narrowest containing directory or bounded subtree ending with
`/**`. Verification commands, validation routes, and `pytest tests/...`
strings are evidence only and never grant write authority.

Set root `validation_policy` to `mode: feature_epochs`, `max_epochs: 3`,
`budget_scope: implement-review`,
`budget_ref: implementation-review/validation-runs.json`, and
`heavy_gate_owner: leader`. Keep full-suite, build, integration, E2E, and
visual commands as shared verification gates. Put only cheap changed-scope
checks safe for one Txx in `task_checks`; only those checks compile into a
worker packet. The three epochs are logical `baseline`, `convergence`, and
`delivery` gates. Retries, timeout recovery, and deterministic shards remain
attempts inside their gate and do not consume another epoch.

At the task-index root, require `acceptance_refs` to be the complete unique
ordered copy of `plan-contract.acceptance_refs` values (typically
`spec-contract.json#/acceptance_criteria/0..N-1`; pointer form
`plan-contract.json#/acceptance_refs/N` is rewritten); a ready version-2
index may not omit the file or carry copied spec refs or a selected subset.
Compile every official entrypoint record in
`official_entrypoints` as **objects** (not bare strings), e.g.
`{"id":"EP-00","path":"/login","kind":"web","label":"/login"}` or
`{"id":"EP-1","command":"npm run dev","ready_signal":"..."}`. The runtime
normalizes legacy string arrays on build/set-root/finalize/closeout, but new
packages should author objects. Keep `review_obligations` and the smallest
complete `system_review_scenarios` matrix as object arrays that prove startup,
every changed user-observable journey, and affected shared regressions. Each
scenario names its entrypoint, preconditions, actions, observable results, and
required evidence. Shape-only `tasks set-root` repairs on an already-`ready`
package keep `ready` when validation still passes (no forced draft→finalize). Compile obligations from every entrypoint, acceptance/capability,
must-preserve, consequence, fidelity, consumer-surface, wiring, and required UI
state source; map every required obligation to one or more scenario ids so
`$spx-review` can enforce zero uncovered scope instead of reconstructing
acceptance from prose. Give every `acceptance_ref` at least one dedicated
required system-review scenario whose required acceptance-source set is
exactly that ref. A broad regression scenario may be additional evidence only;
it cannot serve as a ref's dedicated witness.

Separately freeze a non-empty Human Acceptance Universe in
`human_acceptance_obligations` and `human_acceptance_scenarios`. Cover every
new or changed requirement that a human can perform end to end, retaining its
canonical task-index acceptance ref as the obligation source, a non-empty human
actor, official entrypoint, starting state, human action, observable terminal
outcome, required/optional status, Review-scenario linkage, and obligation
mapping. Every required human scenario links at least one dedicated required
Review scenario for its own `acceptance_ref`. Require zero uncovered required
human obligations. Human
performs these requirement journeys later in `$spx-accept`; do not repeat
System Review by copying its startup, wiring, diagnostics, or broad regression
matrix into human acceptance.

Validate requirement/plan coverage, dependency cycles, write-set safety,
acceptance, and real-entrypoint verification. Generate worker packets later in
`$spx-implement`, from current repository state, rather than pre-authoring a
large packet per task.

When isolated task-generation lanes are delegated, create an absent
`task-generation/lane-manifest.json` with `artifact scaffold --kind task-generation-lane-manifest --path <feature-dir>/task-generation/lane-manifest.json` and query it on resume. Each
lane submits one compact result inline through `result submit --command tasks`;
the runtime alone writes its handoff. At material joins, replace the bounded
`/lanes` array as a whole through a fresh leased JSON-pointer patch and patch
`/status` separately at closeout. Never emulate array append, submit the
manifest wholesale, or duplicate lane events.

For every UI-bearing task, supply only the meaningful non-default semantic fields
described by `assets/ui-task.md` and `assets/ui-task-index-entry.json` to the task
CLI. The CLI expands the stable current `ui_contract` shape; the agent does not
re-emit empty defaults or boilerplate. Use that expanded object as the only UI packet contract. Do not rely on a
global UI coverage table: the just-in-time packet compiler must receive design
sources, the exact `design_change_id`, `design_change_ref`,
`design_change_sha256`, sibling `design_contract_ref`, approved
reference/digests, exact `style_authority`, an applicable `DS-*` decision subset,
component/color-mode/responsive/motion contracts, viewport/state acceptance
rows, comparison tolerance, the unchanged accepted-deviation ledger,
task-specific visual constraints, states, and evidence without re-inferring
them. Across UI tasks, require exact coverage of the plan's design decision and
acceptance rows.
Treat `inherit-existing` as a hard worker guard; never broaden a page-authorized
style delta into global shell or shared-component work.
Never resolve “latest” from `.specify/design/index.json` and never substitute an
unregistered root design document for a registered task binding.

Before handoff, run
`{{specify-subcmd:specify-runtime hook validate-artifacts --command tasks --feature-dir <feature-dir> --format json}}`
and repair the task graph or reopen its owning upstream phase on failure.

Do not implement or edit production source/tests. This invocation authorizes
only this workflow stage. Stop after reporting the executable graph and
recommend `$spx-implement`; do not invoke `$spx-implement` in this run. A
handoff is not authorization to execute it. Use `$spx-analyze` only when an
independent consistency gate is requested or existing state requires it.
