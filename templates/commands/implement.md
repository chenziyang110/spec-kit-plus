---
description: Use when tasks.md exists and the planned work should be executed through the tracked implementation workflow.
workflow_contract:
  when_to_use: '`tasks.md` is ready and the feature should move from planning into tracked execution batches.'
  primary_objective: Execute the ready batches while preserving tracker state, subagent contracts, verification discipline, and resumability.
  primary_outputs: Verified code, test, and documentation changes plus compact execution state, one task lifecycle record per executed task, conditional drift/repair records, and `implementation-handoff.json` for mandatory system review.
  default_handoff: Continue ready work; preserve Implement state while agent-owned blockers are repaired inside the active Implement recovery lane; after technical closeout hand the integrated product to /sp.review and stop.
scripts:
  sh: scripts/bash/check-prerequisites.sh --json --require-tasks --include-tasks
  ps: scripts/powershell/check-prerequisites.ps1 -Json -RequireTasks -IncludeTasks
---

{{spec-kit-include: ../command-partials/implement/shell.md}}

{{spec-kit-include: ../command-partials/common/senior-consequence-analysis-gate.md}}

{{spec-kit-include: ../command-partials/common/agent-phase-handoff.md}}
{{spec-kit-include: ../command-partials/common/run-bootstrap.md}}
{{spec-kit-include: ../command-partials/common/autonomous-blocker-recovery.md}}

[AGENT] For project-cognition-backed semantic intake, routing, audit, resume, or final-claim gates, read `references/semantic-work-contract.md`.

[AGENT] `sp-implement` continues the same run created for the feature. Confirm the same run with `specify-runtime run show`, then execute implementation work only through `specify-runtime run supervise`.

[AGENT] Leader-owned supervision uses task identity `implement:<feature-id>`;
packet-backed workers use the runtime-derived `<feature-id>#<Txx>`. Every
modifying launch carries confirmed scope. `implement task-start` requires that
same fenced Work identity, claims the task's complete `expected_write_scope`
all-or-none, and returns `work_claim` before changing lifecycle state to
`in_progress`. A legacy scope-empty task reuses the current Work's confirmed
scope; a genuinely no-write task returns `claim_state: not_required` and must
not later report changed files. Do not perform source writes without a claimed
receipt.

The shared `specify-runtime execution overview` is coordination context only:
it may reveal that other Implement tasks exist, but it is not
task selection authority or feature selection authority. Do not choose,
resume, or bind a feature from an overview activity row. Resolve the owning feature through the
provenance gate below, then use the matching overview row only to sequence work
and verify Run/Work ownership.

## Feature Context Provenance Gate

Accept `<feature-dir>` only from `{SCRIPT}`, an explicit user selection, or the
runtime-selected current Run subject. If feature context is missing or ambiguous, stop
before `task-next`; never enumerate `.specify/features/**`, `tasks.md`, or
`task-index.json`, and never choose a feature from name, slug, title, topic, or
keyword similarity. An active or unconsumed discussion is not implementation
authority: resume its Discussion contract, and after handoff readiness let only
its selected `sp-quick` or `sp-specify` consumer create and bind downstream
state. Discussion never hands off directly to `sp-implement`.

## Test Design Task-Packet Boundary

Implement consumes **only the task packet subset** of canonical test-design
input compiled just in time from
the validated canonical task-index entry: task-local `test_case_refs`,
`test_data_refs`, and the Test Design binding fields
`test_design_handoff_ref`, `test_design_handoff_sha256`,
`test_design_source_fingerprint`, `test_design_state_revision`, and
`test_design_artifact_digests`. Treat those refs as read-only expected-behavior,
oracle, and material inputs for this task. Implement must not independently
discover or consume a global Test Design publication or projection, and must
never edit canonical Test Design cases, data, coverage, gaps, audit, publication,
projection, or compatibility handoff. The packet compiler revalidates the
binding immediately before dispatch; missing, partial, stale, tampered, or
foreign refs block before edits and route through Tasks/Test Design ownership.
Before the first `task-start`, that gate includes the live Test Design source
fingerprint. After execution has started, expected product-source edits do not
invalidate the pinned design input; every Implement command still verifies the
exact handoff, state, canonical Test Design artifacts, audit, refs, and digests,
and any change to those protected inputs blocks immediately.
Do not enrich the packet from a noncanonical Markdown task projection or from a separately located
projection.

## Main Flow

1. Run `{SCRIPT}` to resolve the task-bearing feature context, then call `{{specify-subcmd:specify-runtime implement task-next --feature-dir <feature-dir> --format json}}`. Treat CLI-owned `task-index.json` as the structured execution contract from Tasks, while letting the CLI return only the next ready task and compact execution state; use `specify-runtime artifact show --json-pointer ...` for any additional canonical field. Never parse or rewrite the full task index with ad-hoc scripts. Required refs, protected requirements, user decisions, and task-local `MP-*` must-preserve obligations remain locked; on conflict, park the task and route repair through the owning upstream phase rather than redefining the goal, then resume Implement after the owner validates the repair.
2. Validate the returned task and current ready batch. For delegated work, call `{{specify-subcmd:specify-runtime implement packet-compile --feature-dir <feature-dir> --task-id <Txx> --format json}}`; do not author a packet file. Pass the returned canonical `path` and `sha256` unchanged as `--work-packet-file <path> --work-packet-sha256 <sha256>` when the delegated worker is launched through `run launch` or `run supervise`; Run Control verifies the exact compiled bytes before parsing, then registers the packet's task identity, objective, and confirmed `scope.write_scope` on the shared Work Board before child launch. Do not reconstruct that metadata with manual `--work-task-ref`, `--work-summary`, or `--work-intents-json` flags. When its task packet includes Test Design refs, enforce the task-packet boundary above and stop on any binding failure. Group behavior-changing Txx items into one coherent change-set, establish its RED/baseline through the Leader-owned logical validation-gate contract, and do not claim completion from chat narration.
3. Use `choose_subagent_dispatch(command_name="implement", snapshot, workload_shape)` for safe worker lanes, use the current integration's native subagent lifecycle where available, and keep leader ownership of tracker state.
4. Start with `specify-runtime implement task-start`, execute the current task or ready batch, merge a structured result with `specify-runtime implement result-merge --result-json '<inline-json>'`, and accept it only with `specify-runtime implement task-accept`. These commands atomically own task status, lifecycle, execution state, and compatibility tracker projections. Never edit those workflow files directly and never create a temporary result JSON file under `worker-results/` (runtime owns that path). Expand the authoritative WorkerTaskResult shape with `specify-runtime api schema implement-result-merge-input --format json` or `api show implement.result-merge`. Acceptance-ready `status: success` requires `validation_results: [{command, status: "passed", summary?}, ...]` (field name is `validation_results`, not `validation`); `blockers` must be empty; worker status is `success|blocked|failed` (not `DONE`). Prefer `--result-json @path` or a clean argv JSON dump over shell `ConvertTo-Json`. `evidence register` is optional attachment and does not substitute for `validation_results`. Resolve known blockers through focused repair; for an unknown technical root cause, preserve Implement state, enter a bounded Debug-grade evidence lane inside Implement, repair the proven owner, then resume the task. Do not invoke another user-invoked workflow automatically.
5. Run event-triggered review for repository drift, parallel joins, write-scope drift, validation failure, worker concerns, obligation conflicts, or sequential change-window limits. Let `specify-runtime implement task-start|result-merge|task-accept` maintain the single task lifecycle record; submit a blocked result through `result-merge` rather than inventing a task-block file operation. Report completion only when its changed paths, validation evidence, review status, and mutation closeout are complete.
6. Persist the shared validation ledger only through `specify-runtime implement validation-start|validation-finish`; inspect it with `validation-status`. Its three
   logical gates are optional RED/baseline, Implement convergence, and Review
   delivery; physical retries are attempts inside their gate. Timeout,
   termination, cancellation, harness, or environment loss is `interrupted`,
   not failed, and may retry the same gate/fingerprint. A real assertion or
   verification failure requires repair and a new fingerprint. No agent may
   reset the ledger or open a fourth logical gate. Per-Txx workers run only
   cheap task checks and return test impact; the Leader owns every heavyweight
   test, build, startup, E2E, and real-entrypoint validation attempt. Before
   each allocation, follow `validation-status.attempt_decision`:
   `resume_running_attempt`, `retry_same_gate`, `repair_before_retry`,
   `open_logical_gate`, or `validation_complete`. `remaining_epochs` and
   `remaining_gate_slots` count only unopened logical gates; zero never blocks
   a progress-bound attempt inside an existing gate.
7. For UI work, apply Design Intelligence **UI Implementation Rules** before
   generating UI: query the task's exact registered design change, UI System
   Model (tokens, components, states), surface-aware anti-slop policy, and the task
   `ui_contract` through `specify-runtime artifact show`. Prefer visual hierarchy
   and the component system over generic equal-weight card grids. Execute the
   declared pointer/mouse, keyboard/focus, touch, and command paths; verify
   each interaction row's event sequence, immediate feedback, focus, repeat,
   cancellation, and pending behavior plus component `interaction_modes`,
   `data_scenarios`, `editing_matrix`, and
   resize/stretch/overflow behavior instead of checking only the populated
   happy path. Preserve states and changed surfaces
   through `specify-runtime implement`, and capture requirements, but do not run
   the full viewport/state capture loop per Txx. Group the matrix by integrated
   surface and capture typed `structure_snapshot`, `visual_capture`, and
   `runtime_diagnostics` evidence through `specify-runtime evidence
   register|import` with `evidence_scope: integrated`. Bind shared refs and the
   task's structured `ui_verification` into each task lifecycle only through
   `specify-runtime implement result-merge|task-accept`; include the required
   evidence, difference inventory, accepted deviations, and
   exact `covered_smoothness_acceptance_ids`, plus the objective-comparison or
   `pending-human-review` result. For every passing
   visual comparison, submit only the observed entrypoint/revision, typed
   evidence refs, matrix differences, explicit verdict, and reviewer through
   `specify-runtime evidence visual-compare --feature-dir <feature-dir>
   --task-id <Txxx> --input-json '<observed-comparison-json>' --format json`.
   The runtime derives and atomically writes the registered report from the
   task's approved preview/manifest/handoff bindings, exact `DS-*`/`DH-*`
   coverage, comparison tolerance, and accepted deviations; use its returned
   report ref and byte digest in `ui_verification`. Never read or reconstruct
   `visual-comparison-template.json`, and never generically submit or patch the
   report. When `smoothness_acceptance_ids` is non-empty, first call
   `specify-runtime evidence smoothness-manifest --feature-dir <feature-dir>
   --task-id <Txxx> --format json`; execute its exact real-entrypoint viewport,
   interaction, reduced-motion, interruption, and performance matrix with
   Playwright or the available browser runner; then submit only observations to
   `specify-runtime evidence smoothness-validate --feature-dir <feature-dir>
   --task-id <Txxx> --manifest <manifest-ref> --input-json
   '<observed-result-json>' --format json`. Merge the returned exact coverage,
   `smoothness_lab_report_ref`, and `smoothness_lab_report_sha256` into the
   lifecycle. The report augments the existing evidence triad; it is not a new
   evidence kind. The runtime must resolve the task surface's exact
   `entrypoint_id`; missing, unknown, or ambiguous entrypoint bindings block
   the lab. Task acceptance revalidates the canonical manifest, current
   task-index digest, typed evidence triad, full scenario set, and performance
   budgets, so a handwritten or minimal report cannot pass. Query the packet's must-read immutable handoff through
   `specify-runtime artifact show` before UI work and resolve selected rows and
   implementation bindings from it; a missing file, digest mismatch, unknown ID,
   or copied-row mismatch blocks implementation rather than authorizing
   reconstruction. This is evidence reuse, not permission to recapture or rerun
   the matrix per task. Unavailable objective comparison remains
   `pending-human-review`, never an implicit pass. Route an invalid, bootstrap,
   or missing design source to `sp-design` instead of inventing one.
8. After successful technical closeout, call `{{specify-subcmd:specify-runtime implement closeout --feature-dir <feature-dir> --format json}}`. That command exclusively derives and atomically writes the preliminary `implementation-summary.md` and deterministic `implementation-handoff.json`, including the unchanged validation ledger, logical-gate count, and attempt history. It revalidates the live Spec, Plan, and Tasks and preserves their exact complete `acceptance_refs` denominator, `acceptance_denominator_sha256`, and frozen Human Acceptance Universe (`human_acceptance_obligations`, `human_acceptance_scenarios`, and `human_acceptance_contract_sha256`) unchanged. Never author, patch, submit, or stage either artifact yourself or through the generic artifact channel. Implement must not create, infer, or prefill `reviewed_runtime_targets`; only Review creates them from final integrated evidence. Complete only the `implement` stage, recommend `{{invoke:review}}`, and stop. The embedded event-triggered task review remains part of implementation, while `sp-review` owns the reserved delivery gate and may retry attempts inside it to prove startup, user journeys, interaction, and integrated wiring from real entrypoints. Do not invoke Review inline or claim that task completion equals a usable reviewed product.

## Non-Terminal Progress Guard

When technical recovery crosses the first task packet, preserve the task
lifecycle, validation ledger, source fingerprint, and failed attempt through
`specify-runtime implement`. Expand the registered causal write scope and repair
the affected supporting control plane inside Implement, using Debug-grade
evidence discipline without invoking another user-invoked workflow. After
verified repair, resume the interrupted validation gate in the same invocation.
Contradictory requirement, design, Plan, Tasks, or Test Design truth remains an
explicit owning-phase handoff-and-stop boundary; do not silently redefine it.

After every accepted task, completed batch, join point, or implementation
milestone, immediately call `specify-runtime implement task-next` again. When it
returns another ready task, start that task and continue tool-driven execution
in the same invocation. A completed task, batch, migration, type generation, or
validation milestone is partial progress, not a terminal state.

Do not emit a final answer or otherwise end the current agent turn while
`task-next` reports ready work or an agent-capable recovery step can still make
safe progress. Intermediate progress belongs only in progress updates that do
not terminate the invocation; after any such update, continue tool-driven
execution in the same invocation. The invocation may end only after successful
Implement closeout and Review handoff, at a contract-defined cross-workflow
handoff-and-stop boundary, or at a genuine blocker or human gate with no
dependency-safe ready work; preserve the exact resume action in every blocked
stop.

{{spec-kit-include: ../command-partials/common/inline-project-cognition-update.md}}
Before `implement closeout` or `workflow complete-stage`, execute the shared
planner-returned `apply_argv`; it writes the runtime-bound receipt after update,
validation, and eligible finalization. Runtime blocks closeout without that
receipt so every implement pass grows project cognition.

## Detailed References

Read [Reference index](references/INDEX.md) before applying detailed contracts.

- [task intake and tracker](references/task-intake-and-tracker.md)
- [red first and validation](references/red-first-and-validation.md)
- [subagent worker contract](references/subagent-worker-contract.md)
- [join point review](references/join-point-review.md)
- [safe repair loop](references/safe-repair-loop.md)
- [final reconciliation and closeout](references/branch-review-and-closeout.md)

## Professional UI Contract Continuity

Implement each task's exact `surface_catalog`, `scenario_matrix`,
`interaction_matrix`, `editing_matrix`, `data_state_matrix`, `accessibility_matrix`,
`navigation_matrix`, `content_matrix`, `motion_contract`, and
`usability_validation` subset, including component
governance, adoption permissions, and iconography. Web tasks must exercise every applicable
`smoothness_acceptance_id` and return exact coverage plus the bound Smoothness
Lab report through the existing UI evidence kinds. Exercise risk-based or pairwise combinations at
real entry points, never an unbounded Cartesian product. Do not claim required
target-user human review from automated tests or screenshots.
