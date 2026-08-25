---
name: spx-debug
description: Lean evidence-driven debugging workflow for advanced coding models. Use for a bug, regression, failed verification, or unexpected runtime behavior whose root cause is not yet proven.
---

# SPX Debug

## Hard preflight stop

The invoking request is not a branch selection, even when it says to fix the
problem. Before committing to any action, classify context sufficiency. If it
is sufficient, render the evidence summary and exact two-option menu, then stop
and wait for a new user reply. Do not infer consent from the recommendation.
If it is insufficient, state that the full workflow will perform its normal
intake and continue into that intake.
Do not say "I'll change", "I'll fix", or "I'll reproduce" before the selected
branch's gates allow that action.

Before opening any reference or calling any tool, assess only evidence already
present in the active conversation. Context-direct is eligible only when it
contains a reproduced failure signal, a proven failure mechanism or root cause,
no competing hypothesis, explicit fix authority, exact owner/current patch
anchors, bounded consumers and risks, and a regression check. Unknown, stale,
conflicting, multi-owner, consequence-bearing, or investigation-dependent work
is insufficient.

The pre-intake routing result is strict:

- **Insufficient: never show a branch menu.** Enter the full Debug branch and
  perform its normal intake. Do not announce discovery, reproduction, or edits
  before the full branch's own confirmation and execution gates.
- **Sufficient:** show the exact scope, evidence, and fallback trigger, then ask
  exactly **Direct fix (Recommended)** or **Continue full sp-debug**.
  Do not paraphrase these labels or add a third option.

After the user's choice, read `references/context-sufficiency-choice.md` only
for a selected context-direct branch. Execute only that branch, defer
`references/project-cognition.md` until exact-path mutation closeout, and do not
consume Project Learning. For the full branch, continue below without asking
again. The remaining skill text owns the full Debug branch.

Read `references/project-learning.md` and apply its consume-capture policy.
Read `references/native-subagents.md` when evidence lanes are delegated.
Read `references/project-cognition.md`, using cognition intent `debug`.
Read `references/run-bootstrap.md`.
Read `references/autonomous-blocker-recovery.md` before treating any
investigation, harness, or verification failure as terminal.
Read `references/human-confirmation.md`, then
`references/investigation-contract.md`. Read
`references/investigator-worker.md` only for delegated evidence. Create an
absent `.planning/debug/<slug>.md` only with `specify-runtime artifact scaffold
--kind debug-session`, or resume it through targeted `artifact show`; mutate it
only through fresh leased `artifact patch` calls. The shared runtime scaffold is
the durable source of truth for every debug invocation.
Read `references/consequence-gate.md` when the suspected cause or fix touches
lifecycle, shared state, destructive behavior, compatibility, migration,
security, concurrency, retry, recovery, or generated consumers.
Read `references/ui-quality-gate.md` when the symptom is visual, responsive,
interaction, focus, accessibility, TUI, or CLI presentation behavior. For those
UI symptoms, enter **UI Debug Mode**: classify visual/layout, UX/interaction
(pointer/mouse, touch, hover, focus, keyboard, loading, empty, populated,
partial, error, permission, offline, retry, undo, recovery), resize/reflow
(stretch, compression, overflow, lost focus/selection/scroll/overlay/unsaved
input), and/or taste/generic-look; record
issue, reason, and design-aware fix direction before coding.

The full `$spx-debug` branch always starts a new run. Record that new run with
`specify-runtime run create`, then execute only through `specify-runtime run
supervise`; do not resume another workflow's run. The explicit user-selected
context-direct branch is the sole exception and creates no run or debug
session.

Create or resume the session in its unconfirmed intake state. Render the Debug
checkpoint from `references/human-confirmation.md` as readable headings and
bullets; for an applicable UI symptom, fold its independent target-baseline
state into the same checkpoint as `界面方向` without proposing a repair, then ask
once for both decisions. Wait for user confirmation before reproduction, log review,
source or test reads, evidence collection, delegation, instrumentation, code
edits, or validation. Persist the main and UI confirmations separately and keep
hypotheses in the agent investigation plan. After confirmation, reproduce the symptom or establish
the strongest available failure signal before changing behavior. Use cognition
to locate likely owners, boundaries, and verification surfaces, then confirm
claims against logs, configuration, tests, runtime output, and live source.

Maintain a small set of ranked hypotheses and choose evidence that separates
them. Distinguish the visible symptom from the failure mechanism. Once evidence
supports a root cause, apply the minimum coherent fix only after the automated
RED gate in the investigation contract. When logs are insufficient, add bounded
instrumentation or request a precise user-log packet instead of guessing.

Preserve the debug session if repair requires a harness, launcher, dependency,
runner, generated tool, or other supporting control-plane change beyond the
first fix scope. Expand the smallest registered causal scope and repair it
inside the active Debug recovery lane; do not invoke another user-invoked
workflow automatically. Then resume the original reproduction and verification
path in the same invocation. Scope growth, unfamiliar technology, or unavailable
delegation alone cannot close the session as blocked.

Re-run the original reproduction and relevant surrounding verification.
For a UI regression, reproduce and recapture the same real entry point,
input event, data condition, viewport/continuous resize path, and state after
the fix; source inspection or component tests cannot
prove a visual symptom resolved.
Delegate only independent evidence lanes or an independent review that improves
confidence. Never reconstruct a debug-session template or create the state file
directly.

After agent verification and related-risk review, move to
`awaiting_human_verify`; do not resolve or archive until explicit human
confirmation. Only after the lifecycle rules in the investigation contract are
satisfied, run
`{{specify-subcmd:specify-runtime cognition closeout-plan --workflow sp-debug --scope-dir <feature-or-scope> --scope-mode explicit --intent debug --format json}}`
with explicit workflow-owned paths, fill returned agent-owned fields, and execute
structured `apply_argv` before claiming the fix complete. Shared apply owns
update, validation, eligible finalization, and receipt; only an update failure
uses mark-dirty plus a standalone dirty receipt. Apply the gate in
`references/project-cognition.md` before any clean claim. Finish
truthfully, citing root-cause evidence, changes, verification, and uncertainty.

## Professional UI contract continuity

For a UI defect, identify the violated exact row/object in `surface_catalog`,
`scenario_matrix`, `interaction_matrix`, `editing_matrix`, `data_state_matrix`,
`accessibility_matrix`, `navigation_matrix`, `content_matrix`,
`motion_contract`, or `usability_validation`; preserve component governance and
approved truth.
Reproduce risk-based scenarios rather than an unbounded Cartesian product, and
never substitute screenshots for required target-user review.
