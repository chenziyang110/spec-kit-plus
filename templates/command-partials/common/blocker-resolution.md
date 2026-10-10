## Blocked Exit Contract

All `sp-*` workflows must recover before exiting. Invoking the command
preauthorizes necessary diagnosis, safe repair, verification, and continuation
within the current goal, available permissions, and allowed side effects.
An error, unknown root cause, failed first attempt, or supporting file outside
the initial packet is not a reason to transfer agent-capable work to the user.

At a failed prerequisite, tool call, validation, or proposed blocked exit, read
and apply the Recovery Decision in
`.specify/templates/workflow-blocker-template.md` before choosing to stop.
Preserve the parent workflow and failed gate; diagnose, repair through the
canonical owner, reverify, and resume the exact interrupted gate in the same
invocation. Continue independent dependency-ready work and then the original
workflow's full completion criteria, not just the repair.

Local stop/halt/fail-closed instructions, including exit `10`, stop the invalid
operation; they do not prohibit safe diagnosis or authorized recovery. Keep
read-only and stage boundaries, artifact leases, explicit approvals, and
independent acceptance intact. Do not invoke another user-invoked workflow
automatically or rewrite another owner's artifacts. Never weaken acceptance
criteria, skip mandatory checks, fabricate evidence, or overwrite unrelated
user changes. No unchanged deterministic retries or indefinite polling.

Use the terminal view and `.specify/templates/workflow-blocker-schema.json`
only when no safe authorized recovery or independent work remains. Never return
only an error or “ask a human”; preserve state and keep agent-capable repair
agent-owned. Set `human_action_required: true` only when a specific action needs
human authority, credentials, protected-system access, a decision/review,
physical access, or destructive-action approval. An external outage or missing
capability alone does not imply human action. Tailor the evidence, attempted
recovery, exact next action, unblock criteria, and resume point to the real
boundary. Never claim completion with required work unresolved.

For a feature runtime blocker, do not invent `resume_argv` or overwrite an
existing blocker. The CLI returns a read-only `show_argv` and structured
`resolution_action`; `next_argv` stays empty while evidence is missing. After
the criteria are proven, attach sanitized evidence using the action's declared
input and execute its base argv. It restores the same owner and keeps the full
blocker audit. When an already validated strict backward reopen targets an
earlier stage, the blocked `workflow reopen` response also returns
`pending_reopen_action`. This does not replace the blocker: after the same real
resolution evidence exists, its base argv atomically records resolution and
reopens that earlier stage instead of restoring the same owner first. Use the
pending action exactly; never reconstruct a separate reopen.

When current evidence proves only some named blocker subcauses are resolved,
expand `workflow.reconcile-blocker` through `specify-runtime api show`, then
submit its revision-bound input with the resolved subcauses and a complete
remaining cause/evidence/scope/recovery contract. The runtime keeps the same
owner/category and blocked state, removes stale current text, and appends the
reconciliation audit. Do not use it when no cause remains; satisfy the original
criteria and use `workflow.resolve` instead.
