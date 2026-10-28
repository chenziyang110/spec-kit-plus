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
  perform its normal intake and bounded evidence investigation. Diagnosis may
  begin after intake; repair waits for the evidence-backed repair confirmation
  and execution gates.
- **Sufficient:** show the exact scope, evidence, and fallback trigger, then ask
  exactly **Direct fix (Recommended)** or **Continue full sp-debug**.
  Explain the discovered defect, proven mechanism, decisive evidence, concrete
  repair, affected boundary, risks, and verification before the choice. Choosing
  Direct fix approves that concrete repair; no second checkpoint is needed.
  Do not paraphrase these labels or add a third option.

After the user's choice, read `references/context-sufficiency-choice.md` only
for a selected context-direct branch. Execute only that branch, defer
`references/project-cognition.md` until exact-path mutation closeout, and do not
consume Project Learning. For the full branch, continue below without asking
again. The remaining skill text owns the full Debug branch.

Read `references/project-learning.md` and apply its consume-capture policy.
Read `references/native-subagents.md` when evidence lanes are delegated.
Read `references/project-cognition.md`, using cognition intent `debug`.
Read `references/execution-bootstrap.md`.
Read `references/autonomous-blocker-recovery.md` before treating any
investigation, harness, or verification failure as terminal.
Read `references/human-confirmation.md`, then
`references/investigation-contract.md`. Read
`references/investigator-worker.md` only for delegated evidence. Apply the
session selection, earliest-unsatisfied-gate resume, evidence join, and final
revision checks in the investigation contract. The leader schedules the loop;
do not wait for an assumed graph-engine callback or invoke a Python workflow.
The shared runtime scaffold remains the durable source of truth.
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

Create an absent full Debug session with `specify-runtime artifact scaffold
--kind debug-session`, or resume its existing state through targeted
`specify-runtime artifact show` calls in the current worktree with task
identity `debug:<session-slug>`. The explicit user-selected context-direct
branch creates no debug session; both routes use the shared execution bootstrap.
Once the complete repair scope is proven, announce it, checkpoint selection,
refresh the overview, and require the all-or-none
`specify-runtime execution guard` before the first source write. Context-direct
uses that same guarded Work/Activity lifecycle before its bounded fix; skipping
Debug state does not skip write coordination. Checkpoint validation and call
`specify-runtime execution complete` only after fresh passing validation and
terminal workflow state.

Create or resume without clearing still-valid confirmations or completed framing.
After confirmation and accepted framing, repair only within the exact approved
scope. For a `diagnose only` request, use Diagnosis-Only Delivery in
`references/investigation-contract.md`; deliver the diagnosis without claiming the
defect `resolved` or requesting verification of a nonexistent fix. Resume the
earliest unsatisfied technical gate and check Write Authorization and Guard
Scope before any source, test, harness, configuration, or instrumentation write.

Start new or materially changed intake with `understanding_confirmed: false`;
on resume, validate and reuse an unchanged exact repair approval without
another confirmation, as the investigation contract requires. Understand the reported symptom, expected behavior,
conditions, and investigation boundary;
ask for missing facts only when they block the next safe evidence step. Complete
the intake flags in `references/investigation-contract.md`, then inspect
existing logs, configuration, source, and tests, run a low-risk existing
reproduction, and delegate bounded read-only evidence lanes without an early
approval checkpoint. Use cognition to narrow owners and verify its claims
against live evidence. External effects and destructive actions retain their
own authority gates. Before confirmation, do not change product or test files,
repair a harness, add persistent instrumentation, or dispatch a fix worker.

Maintain a small set of ranked hypotheses and choose evidence that separates
them. Distinguish the visible symptom from the failure mechanism. Once evidence
supports a root cause and a bounded repair, render the Debug Understanding
Checkpoint from `references/human-confirmation.md` as readable headings and
bullets. Explain the discovered defect and decisive evidence, concrete repair,
affected boundary, expected result, risks, and verification. The user approves
that repair, not the technical hypothesis. For UI symptoms, investigate against
a provisional existing/source-backed target, then include the repair's formal
target baseline as `界面方向` in this same checkpoint. Wait for the user's repair
confirmation, persist the exact decision payload,
`checkpoint.confirmation_purpose: evidence-backed-repair`,
`confirmation_digest`, and separate UI state, then pass the automated RED gate
before the minimum coherent fix.
Old or generic intake confirmation is not repair authority on resume. When
evidence cannot be obtained without changing a harness or adding persistent
instrumentation, use the bounded `diagnostic-enablement` confirmation in the
investigation contract; after that diagnostic work, investigate again and
obtain `evidence-backed-repair` approval before repairing the product. Do not
guess a cause or treat diagnostic authority as repair authority.

Preserve the debug session if authorized repair requires a harness, launcher, dependency,
runner, generated tool, or other supporting control-plane change beyond the
first fix scope. If it materially changes the approved repair, obtain the
bounded amendment before writes. Expand the smallest registered causal scope
and repair it inside the active Debug recovery lane; do not invoke another user-invoked
workflow automatically. Then resume the original reproduction and verification
path in the same invocation. Scope growth, unfamiliar technology, or unavailable
delegation alone cannot close the session as blocked.

Before final verification of repaired source, first call
`{{specify-subcmd:specify-runtime cognition closeout-plan --workflow sp-debug --scope-dir <feature-or-scope> --scope-mode explicit --intent debug --format json}}`
with explicit workflow-owned paths, then use its inputs to begin the native work/source binding
from `references/project-cognition.md`. Re-run the original reproduction and
relevant surrounding verification, then seal that exact binding with fresh tool
observations. Human verification and lifecycle approval remain required; neither
the source binding nor a passing test resolves the Debug session by itself.
For a UI regression, reproduce and recapture the same real entry point,
input event, data condition, viewport/continuous resize path, and state after
the fix; source inspection or component tests cannot
prove a visual symptom resolved.
Delegate only independent evidence lanes or an independent review that improves
confidence. Join revision-bound results before causal decisions, recover failed
lanes, and continue independent dependency-ready work. Never reconstruct a
debug-session template or create the state file directly.

After agent verification of an authorized fix and related-risk review, move to
`awaiting_human_verify`; do not resolve or archive until explicit human
confirmation. Only after the lifecycle rules in the investigation contract are
satisfied, use the plan already obtained, fill returned agent-owned fields, and execute
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
