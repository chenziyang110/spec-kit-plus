---
name: spx-implement
description: Lean implementation workflow for advanced coding models. Use for ready tasks, adaptive direct or native-subagent execution, and evidence-backed feature completion.
---

# SPX Implement

Read `references/project-learning.md` and apply its consume-capture policy.
Read `references/native-subagents.md` when implementation lanes are delegated.
Read `references/workflow-runtime.md` and let its CLI own phase state.
Read `references/run-bootstrap.md`.
Read `references/project-cognition.md`, using cognition intent `implement`.
Read `references/execution-contract.md`. Read `references/worker-contract.md`
only when delegating. Read `references/consequence-gate.md` only on its triggers.
Read `references/ui-quality-gate.md` when any ready task is UI-bearing.

`$spx-implement` continues the same run created for the feature. Confirm the same run with `specify-runtime run show`, then execute implementation work only through `specify-runtime run supervise`.

Resolve the task-bearing feature with the installed
`.specify/scripts/bash/check-prerequisites.sh --json --require-tasks
--include-tasks` or PowerShell equivalent. Inspect the current diff, project
rules, ready tasks, and cognition-selected live paths before editing.
Transition from the validated `tasks` stage into `implement` through the
workflow runtime before any source or test edit.

Apply the Feature Context Provenance Gate before task intake. Accept
`<feature-dir>` only from the setup command, an explicit user selection, or the
runtime-selected current lane. If feature context is missing or ambiguous, stop
before `task-next`; never enumerate `.specify/features/**`, `tasks.md`, or
`task-index.json`, and never choose a feature from name, slug, title, topic, or
keyword similarity. An active or unconsumed discussion is not implementation
authority: resume its Discussion contract, and after handoff readiness let only
its selected `spx-quick` or `spx-specify` consumer create and bind downstream
state. Discussion never hands off directly to `spx-implement`.

Recover durable execution truth before work: CLI-owned `workflow.json`
is the required phase gate; rich `workflow-state.md` is resume, evidence, and
optional Analyze Gate context. Obtain compact execution state and the next task
with `{{specify-subcmd:specify-runtime implement task-next --feature-dir <feature-dir> --format json}}`, and query extra fields with
`specify-runtime artifact show`; never parse the full task index with an ad-hoc
script. The compact execution state is the implementation source of truth,
`implement-tracker.md` is a compatibility projection, and the CLI alone owns
those files plus task lifecycle acceptance. Start with `task-start`, compile
delegated packets with `packet-compile`, merge inline results with
`result-merge --result-json`, and accept with `task-accept`. Never mutate
lifecycle/tracker/task projections directly and never create
temporary packet/result files.

Honor persisted upstream routing. If `workflow-state.md` requires or is still
running an Analyze Gate, its artifact fingerprints are stale, or task-index
`source_revision` cannot be trusted against the current plan/task graph, hand
off to `$spx-analyze` and stop before editing. A plain `gate_status: not-run`
does not make optional analysis mandatory. Do not run `$spx-analyze` inline or
silently repair cross-phase truth during the same `$spx-implement` invocation.

After every accepted task, completed batch, join point, or implementation
milestone, immediately call `specify-runtime implement task-next` again. When it
returns another ready task, start that task and continue tool-driven execution
in the same invocation. A completed task, batch, migration, type generation, or
validation milestone is partial progress, not a terminal state. Do not emit a
final answer or otherwise end the current agent turn while `task-next` reports
ready work or an agent-capable recovery step can still make safe progress.
Intermediate progress belongs only in progress updates that do not terminate
the invocation; after any such update, continue tool-driven execution in the
same invocation. End the invocation only after successful Implement closeout
and Review handoff, at a contract-defined cross-workflow handoff-and-stop
boundary, or at a genuine blocker or human gate with no dependency-safe ready
work; preserve the exact resume action in every blocked stop.

Execute the confirmed scope completely. Adapt stale implementation details to
the live repository while preserving user intent and recording material plan
drift. Group related behavior-changing Txx items into a coherent change-set;
establish one failing test or credible baseline gate before its production
edits when practical. Delegate only independent, bounded work that benefits
from parallelism, isolation, or review; direct execution needs no ceremony.

Use one validation ledger shared across Implement and Review, bound to source
fingerprints and persisted through the handoff. Its three logical gates are
optional RED/baseline, Implement convergence, and Review delivery; physical
retries are attempts inside their gate. Do not reset it on resume or handoff,
and never open a fourth logical gate. Only the Leader may run heavyweight tests,
builds, startup, E2E, or
real-entrypoint gates. Per-Txx workers run cheap task checks only, return test
impact, and may advance dependency-safe work while feature verification remains
pending. Timeout, runner termination, cancellation, harness, or environment
loss is an interrupted attempt and may retry the same gate/fingerprint. A real
assertion or verification failure requires repair and a new fingerprint.

Before every Leader allocation, read `validation-status.attempt_decision`.
Resume `resume_running_attempt`; use `retry_same_gate` for its returned
progress-bound attempt; satisfy `repair_before_retry` with an actual fingerprint
change; allocate only the named `open_logical_gate`; and create nothing for
`validation_complete`. `remaining_epochs` and `remaining_gate_slots` count
unopened logical gates, not retry permission. Never stop or blindly retry from
the raw count alone; zero still permits an attempt when
`attempt_decision.can_start_attempt` is true.

Run the relevant verification as attempts inside one convergence gate for the
integrated change-set, not once per task. On interruption, repair the runner and
retry the same fingerprint; on a real failure, repair the implementation and
retry after the fingerprint changes. Hand off unknown root causes to
`$spx-debug` and stop. Update task status through the task CLI and run
`specify-runtime implement closeout` to transactionally create the
preliminary `implementation-summary.md` and machine-readable
`implementation-handoff.json` for the later system Review.
Validate that handoff against the live Spec, Plan, and Tasks. Carry the exact
complete `acceptance_refs` denominator, `acceptance_denominator_sha256`, frozen
Human Acceptance Universe (`human_acceptance_obligations`,
`human_acceptance_scenarios`, and `human_acceptance_contract_sha256`) forward
unchanged; never omit an item,
downgrade `required`, or reconstruct the contract from prose. Implement must
not create, infer, or prefill `reviewed_runtime_targets`; only `$spx-review`
creates those immutable targets from final integrated evidence.
When durable Codex team state is explicitly needed,
hand off to `$spx-implement-teams` and stop; do not switch workflows inline.

For UI-bearing work, consume the compiled task `ui_contract`; do not reconstruct
design intent from task prose. Workers preserve design inputs and return changed
surfaces, required states/viewports, and visual risks, but do not run the full
viewport/state capture loop per Txx. In a Leader-owned gate attempt, run the integrated
real surface once per applicable fingerprint and record `structure_snapshot`,
`visual_capture`, and `runtime_diagnostics` with
`evidence_scope: integrated`; visually inspect, repair drift, and recapture in
a new attempt inside the same gate. For a passing comparison, call
`specify-runtime evidence visual-compare --feature-dir <feature-dir> --task-id <Txxx> --input-json '<observed-comparison-json>' --format json` with only the observed entrypoint/revision, typed evidence refs, matrix differences, explicit verdict, and reviewer. The runtime derives the approved preview/manifest/handoff bindings, exact `DS-*`/`DH-*` coverage, tolerance, deviations, canonical report, and byte digest from the task contract. Never read the stable template or author/patch the report. Record behavior checks separately from
visual/interaction acceptance. Missing or bootstrap design sources hand off to
`$spx-design` and stop; unavailable comparison remains `pending-human-review`,
never an implicit pass.

After verified repository changes, call `specify-runtime implement closeout`.
It exclusively and atomically writes `implementation-summary.md` and
`implementation-handoff.json` with the unchanged validation ledger,
logical-gate count, and attempt history; never author, patch, replace, or
generically submit those files. Then run
`{{specify-subcmd:specify-runtime cognition closeout-plan --workflow sp-implement --intent implement --format json}}`
with explicit workflow-owned paths, fill returned agent-owned fields, and execute
structured `update_argv`. Apply the receipt-bound finalizer gate in
`references/project-cognition.md` before any clean claim. Report changed files, checks actually run, failures or skipped
checks, and residual risk. Ensure closeout prepared a trusted implementation
handoff, recommend `$spx-review`, and stop. Do not invoke `$spx-accept`
directly: technical completion is not human product acceptance, and task
completion is not system Review. Never claim completion without fresh evidence.
