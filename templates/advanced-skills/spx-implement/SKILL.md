---
name: spx-implement
description: Lean implementation workflow for advanced coding models. Use for ready tasks, adaptive direct or native-subagent execution, and evidence-backed feature completion.
---

# SPX Implement

Read `references/project-learning.md` and apply its consume-capture policy.
Read `references/native-subagents.md` when implementation lanes are delegated.
Read `references/workflow-runtime.md` and let its CLI own phase state.
Read `references/execution-bootstrap.md`.
Read `references/autonomous-blocker-recovery.md` before treating any task,
tooling, or validation failure as terminal.
Read `references/project-cognition.md`, using cognition intent `implement`.
Read `references/execution-contract.md`. Read `references/worker-contract.md`
only when delegating. Read `references/consequence-gate.md` only on its triggers.
Read `references/ui-quality-gate.md` when any ready task is UI-bearing.

Resume the feature's durable execution state in the current worktree through
its runtime owner.

Leader work uses task identity `implement:<feature-id>`; packet workers use the
runtime-derived `<feature-id>#<Txx>`. Announce complete planned scope, checkpoint
selection, refresh the overview, and require `specify-runtime execution guard`
before source writes or dispatch. `implement task-start` requires that fenced Work identity,
claims the task's complete `expected_write_scope` all-or-none, and returns
`work_claim` before changing lifecycle state to `in_progress`. A legacy
scope-empty task reuses the current Work's confirmed scope; a genuinely
no-write task returns `claim_state: not_required` and must not later report
changed files. The receipt must match the guarded identity and scope. Checkpoint
validation and call `specify-runtime execution complete` only after fresh passing
validation and terminal workflow state.

The shared `specify-runtime execution overview` is coordination context only:
it may reveal that other Implement tasks exist, but it is not
task selection authority or feature selection authority. Do not choose,
resume, or bind a feature from an overview activity row. Resolve the owning feature through the
provenance gate below, then use the matching overview row only to sequence work
and verify Work/Activity ownership.

Resolve the task-bearing feature with the installed
`.specify/scripts/bash/check-prerequisites.sh --json --require-tasks
--include-tasks` or PowerShell equivalent. Inspect the current diff, project
rules, ready tasks, and cognition-selected live paths before editing.
Transition from the validated `tasks` stage into `implement` through the
workflow runtime before any source or test edit.

Apply the Feature Context Provenance Gate before task intake. Accept
`<feature-dir>` only from the setup command, an explicit user selection, or the
validated durable workflow binding in the current worktree. If feature context is missing or ambiguous, stop
before `task-next`; never enumerate `.specify/features/**`, `tasks.md`, or
`task-index.json`, and never choose a feature from name, slug, title, topic, or
keyword similarity. An active or unconsumed discussion is not implementation
authority: resume its Discussion contract, and after handoff readiness let only
its selected `spx-quick` or `spx-specify` consumer create and bind downstream
state. Discussion never hands off directly to `spx-implement`.

For Test Design, consume **only the task packet subset** of canonical
test-design input compiled from the
validated canonical task-index task entry: task-local `test_case_refs`,
`test_data_refs`, and `test_design_handoff_ref`,
`test_design_handoff_sha256`, `test_design_source_fingerprint`,
`test_design_state_revision`, and `test_design_artifact_digests`. These are
read-only expected-behavior, oracle, and material inputs. Implement must not
independently consume a global Test Design publication or projection and must
never mutate canonical Test Design cases, data, coverage, gaps, audit,
publication, projection, or handoff. JIT packet compilation revalidates the
binding; missing, partial, stale, tampered, or foreign refs block before edits
and route through Tasks/Test Design. Before the first `task-start`, this includes
the live Test Design source fingerprint. Once execution starts, expected
product-source edits may advance while the exact handoff, state, canonical Test
Design artifacts, audit, refs, and digests remain mandatory and tamper-checked.
Never merge refs from a noncanonical Markdown task projection
or a separately discovered projection.

Recover durable execution truth before work: CLI-owned `workflow.json`
is the required phase gate; rich `workflow-state.md` is resume, evidence, and
optional Analyze Gate context. Obtain compact execution state and the next task
with `{{specify-subcmd:specify-runtime implement task-next --feature-dir <feature-dir> --format json}}`, and query extra fields with
`specify-runtime artifact show`; never parse the full task index with an ad-hoc
script. The compact execution state is the implementation source of truth,
`implement-tracker.md` is a compatibility projection, and the CLI alone owns
those files plus task lifecycle acceptance. Compile delegated packets with
`packet-compile` before dispatch, and pass the receipt's canonical `path`
and `sha256` unchanged as
`--work-packet-file <receipt.path> --work-packet-sha256 <receipt.sha256>` on
`specify-runtime execution announce --workflow implement --agent-id <agent-id>
--adapter-id <adapter-id>`. The runtime verifies the canonical packet path,
exact current compiler output digest over its bytes before parsing, and
immutable baseline binding, then derives feature/subject id, item/task id, task identity, objective,
and the full `planned_write_scope` union of product `write_scope` plus separate
compiler-derived `bookkeeping_write_scope`. Product scope and `ui_contract`
stay unchanged. Do not reconstruct or override packet-derived metadata, or
guard only product paths: use the full returned `planned_write_scope`.
Bookkeeping paths remain CLI-owned, never hand-edited; serialize ownership when
shared feature metadata overlaps, without a wildcard or broad `.specify`
exemption. Exact feature `workflow.json` is compiler-owned bookkeeping so
official `specify-runtime workflow` mutations remain separately audited control
plane work; never hand-edit it or add it through product scope amendment.
Announce binds its exact state and latest mutation receipt when present.
Completion accepts a changed state only when it is active Implement and matches
a newer runtime mutation receipt; valid-shaped hand edits, malformed state, and
unresolved blockers remain agent-owned. The same Activity retries after
official resolution and returns the control-plane path plus receipt ref/digest.
Completion holds the workflow mutation lock and rechecks both exact digests in
its transaction before authority release; drift keeps the same Activity active
for agent-owned retry. Feature-local `.workflow.lock` and workflow-mutation
receipt storage are private transport, not packet scope.
Guard cannot widen packet-backed scope silently: planned changes
before dispatch recompile and reannounce the packet. Packet-backed product
scope accepts only exact future files, exact directories, or bounded subtrees
ending with `/**`; filename globs such as `*_test.go`, `?`, `[]`, `/*`, or
middle `**` are rejected before dispatch. If the task may create or modify
companion tests, migrations, fixtures, generated files, or other companion
artifacts, they must already be present in `expected_write_scope`. Validation
commands and `pytest tests/...` references do not grant write authority. When
the exact future filename is unknown, Tasks must use the narrowest containing
directory or bounded subtree ending with `/**`.
Guard cannot widen packet-backed scope silently. Planned scope changes before
dispatch recompile and reannounce the packet. For one causally required
companion path proven later, keep agent-owned recovery in the same invocation:
refresh overview and rerun the existing `execution guard` with the complete
union plus `--scope-amendments-json`; preserve the original packet, let runtime
mark late discovery, obtain an independent passing `scope-drift-review`, and
resume the interrupted task/gate. `work scope-add` cannot bypass this route.
Checkpoint `selected`, refresh the overview, and guard complete file
and semantic scope before `task-start` or native worker dispatch. Merge inline
results with `result-merge --result-json`, and accept with `task-accept`. Never
mutate lifecycle/tracker/task projections directly and never create temporary
packet/result files.

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
Every cross-workflow route is a handoff-and-stop boundary; never invoke or
continue the destination workflow inside the current Implement invocation.

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
retry after the fingerprint changes. For an unknown technical root cause,
preserve the task lifecycle, ledger, and failed fingerprint; enter a bounded
Debug-grade evidence lane inside Implement, repair the proven owner, and resume
the interrupted validation gate in the same invocation. Do not invoke another
user-invoked workflow automatically. Update task status through the task CLI and run
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

For UI-bearing work, apply Design Intelligence **UI Implementation Rules** before
generating UI: query the task's exact registered design change and UI System
Model (tokens, components, states) through `specify-runtime artifact show`, plus surface-aware
anti-slop and the task `ui_contract`; prefer visual hierarchy and the component
system over generic equal-weight card grids. Consume the compiled task `ui_contract`; do not
reconstruct design intent from task prose. Workers preserve design inputs and
return changed surfaces, required states/viewports, and visual risks, but do not
run the full viewport/state capture loop per Txx. The implementation must
satisfy each task's applicable `interaction_matrix`, `editing_matrix`, and `data_state_matrix`
rows: pointer/mouse, keyboard/focus, touch/shortcut/command paths; empty and
populated data plus each event sequence, immediate feedback, focus, repeat,
cancellation, and pending policy and applicable partial, error, permission, offline, pending,
retry, undo, and recovery; and `stretch_behavior` / `overflow_behavior` during
continuous resize while focus, selection, scrolling, overlays, or unsaved input
is active. Preserve component `interaction_modes` and `data_scenarios`; do not
substitute a populated pointer happy path. In a Leader-owned gate attempt,
run the integrated real surface once per applicable fingerprint and record
`structure_snapshot`, `visual_capture`, and `runtime_diagnostics` with
`evidence_scope: integrated`; visually inspect, repair drift, and recapture in
a new attempt inside the same gate. Record exact
`covered_smoothness_acceptance_ids` in `ui_verification`; missing or extra IDs
block task acceptance without introducing a new evidence kind. Materialize the
CLI-owned manifest with `specify-runtime evidence smoothness-manifest`, run its
exact real-entrypoint matrix through Playwright or the available browser runner,
and submit observations to `evidence smoothness-validate`; bind the returned
`smoothness_lab_report_ref` and `smoothness_lab_report_sha256`. The runtime must
resolve the task surface's exact `entrypoint_id`; missing, unknown, or ambiguous
bindings block the lab. Acceptance revalidates the canonical manifest, current
task-index digest, typed evidence triad, complete scenario set, and performance
budgets, so never handwrite or reduce the report. For a passing comparison, call
`specify-runtime evidence visual-compare --feature-dir <feature-dir> --task-id <Txxx> --input-json '<observed-comparison-json>' --format json` with only the observed entrypoint/revision, typed evidence refs, matrix differences, explicit verdict, and reviewer. The runtime derives the approved preview/manifest/handoff bindings, exact `DS-*`/`DH-*` coverage, tolerance, deviations, canonical report, and byte digest from the task contract. Never read the stable template or author/patch the report. Record behavior checks separately from
visual/interaction acceptance. When `source_continuity.applicability: required`,
run `source-continuity-manifest`, inspect the current tool inventory, then call
`source-continuity-adapter-bridge` with the exact Formal selectors and manifest.
It maps signals through `source-continuity-adapter-catalog` and owns inventory,
Probe, and Plan. `source-continuity-adapter-probe` and
`source-continuity-adapter-plan` remain progressively lower-level fallbacks.
The target snapshot hashes current `expected_write_scope`, using legacy
`write_scope` only as fallback. Runtime-owned workflow roots and Source
Continuity outputs are excluded, keeping repeated manifests byte-stable until
an in-scope product source changes. Do not add `source-continuity` artifacts to
product or execution-guard scope as a workaround; explicit runtime-owned scopes
are invalid.
Compile `source-continuity-adapter-execution` from the returned plan ref/SHA,
then execute only its bounded per-adapter packets, business binding targets,
evidence requirements, permissions, preconditions, and stop conditions. Register
captures with provenance `adapter:<adapter_id>`, bind each evidence row and the
observation to the returned plan, then submit observations through
`specify-runtime evidence
source-continuity-validate --feature-dir <feature-dir> --task-id <Txxx>
--manifest <manifest-ref> --adapter-plan <adapter-plan-ref>
--adapter-execution <adapter-execution-ref> --input-json
'<observed-result-json>'`. Bind the exact three-axis coverage,
`source_continuity_adapter_plan_ref`/SHA-256 and
`source_continuity_adapter_execution_ref`/SHA-256 and
`source_continuity_lab_report_ref`/SHA-256 in
`ui_verification`; unbound discovery candidates, dead actions, outcome drift,
stale manifests, and character-substituted assets block acceptance. Missing or bootstrap design sources hand off to
`$spx-design` and stop; unavailable comparison remains `pending-human-review`,
never an implicit pass.

After verified repository changes, call `specify-runtime implement closeout`.
It exclusively and atomically writes `implementation-summary.md` and
`implementation-handoff.json` with the unchanged validation ledger,
logical-gate count, and attempt history; never author, patch, replace, or
generically submit those files. Then run
`{{specify-subcmd:specify-runtime cognition closeout-plan --workflow sp-implement --scope-dir <feature-dir> --scope-mode explicit --intent implement --format json}}`
with explicit workflow-owned paths, fill returned agent-owned fields, and execute
structured `apply_argv` **before** `implement closeout` / `workflow complete-stage`
(runtime hard gate). Shared apply owns update, validation, eligible finalization,
and receipt; only an update failure uses mark-dirty plus a standalone dirty
receipt. Apply the gate in
`references/project-cognition.md` before any clean claim. Report changed files, checks actually run, failures or skipped
checks, and residual risk. Ensure closeout prepared a trusted implementation
handoff, recommend `$spx-review`, and stop. Do not invoke `$spx-accept`
directly: technical completion is not human product acceptance, and task
completion is not system Review. Never claim completion without fresh evidence.

## Professional UI contract continuity

For UI-bearing tasks, implement the exact `surface_catalog`, `scenario_matrix`,
`interaction_matrix`, `editing_matrix`, `data_state_matrix`, `accessibility_matrix`,
`navigation_matrix`, `content_matrix`, `motion_contract`, and
`usability_validation` subset,
including component governance/iconography. Web tasks exercise every applicable
smoothness acceptance ID and return exact coverage. Exercise risk-based or pairwise
real-entrypoint scenarios, never an unbounded Cartesian product. Automated
tests/screenshots cannot close required target-user human review.
