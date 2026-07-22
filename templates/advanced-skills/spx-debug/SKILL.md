---
name: spx-debug
description: Lean evidence-driven debugging workflow for advanced coding models. Use for a bug, regression, failed verification, or unexpected runtime behavior whose root cause is not yet proven.
---

# SPX Debug

Read `references/project-learning.md` and apply its consume-capture policy.
Read `references/project-cognition.md`, using cognition intent `debug`.
Read `references/human-confirmation.md`, then
`references/investigation-contract.md`. Read
`references/investigator-worker.md` only for delegated evidence. Resolve
`assets/debug-session.md` relative to this Skill and use a created or resumed
session as the durable source of truth for every debug invocation.
Read `references/consequence-gate.md` when the suspected cause or fix touches
lifecycle, shared state, destructive behavior, compatibility, migration,
security, concurrency, retry, recovery, or generated consumers.
Read `references/ui-quality-gate.md` when the symptom is visual, responsive,
interaction, focus, accessibility, TUI, or CLI presentation behavior.

Create or resume the session in its unconfirmed intake state. Render the Debug
card from `references/human-confirmation.md`; for an applicable UI symptom,
append its target-baseline card without proposing a repair, then ask once for
both decisions. Wait for user confirmation before reproduction, log review,
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

Re-run the original reproduction and relevant surrounding verification.
For a UI regression, reproduce and recapture the same real entry point,
viewport, and state after the fix; source inspection or component tests cannot
prove a visual symptom resolved.
Delegate only independent evidence lanes or an independent review that improves
confidence. Create state from the advanced session asset rather than the
classic multi-agent debug template.

After agent verification and related-risk review, move to
`awaiting_human_verify`; do not resolve or archive until explicit human
confirmation. Only after the lifecycle rules in the investigation contract are
satisfied, run
`{{specify-subcmd:specify-runtime cognition closeout-plan --workflow sp-debug --intent debug --format json}}`
with explicit workflow-owned paths, fill returned agent-owned fields, and execute
structured `update_argv`. Apply the receipt-bound finalizer gate in
`references/project-cognition.md` before any clean claim. Finish
truthfully, citing root-cause evidence, changes, verification, and uncertainty.
