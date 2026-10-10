# Blocked exit

Every `spx-*` workflow must read and follow
`references/autonomous-blocker-recovery.md` before deciding that a failure is
terminal, including intake, prerequisite, tool, artifact, and validation errors.
Do not wait for the user to request recovery. Preserve the parent workflow,
resume the exact interrupted gate in the same invocation after repair, and
continue the original completion criteria. A local stop/halt/fail-closed rule
stops the invalid operation, not safe diagnosis or authorized recovery; all
read-only, stage, approval, and independent-validation boundaries remain intact.

Use the installed `.specify/templates/workflow-blocker-schema.json` and compact
human view in `.specify/templates/workflow-blocker-template.md`. Preserve any
owning workflow/task blocker record; this is the user-facing resolution view,
not a parallel state machine.

Report the workflow/stage, blocker category and owner, exact cause, sanitized
evidence, recovery attempted and result, affected scope, smallest next action,
observable unblock criteria, and exact resume point. An error list or “ask a
human” is not sufficient. Continue independent safe lanes when possible and do
not claim completion while a mandatory blocker remains.

Keep ordinary repository repair, available fallbacks, local validation, and
agent-capable diagnosis agent-owned. Set `human_action_required: true` only for
credentials/permissions the agent cannot access, protected external systems,
an external write or approval not authorized, subjective product/visual
decisions, physical-device action, or an organization-controlled service the
agent cannot operate.

Project-controlled launchers, harnesses, dependencies, tooling, local services,
and supporting scope growth cannot become terminal only because they were
outside the first packet. Use this terminal view only after no safe authorized
recovery or independent work remains. An unavailable capability or external
outage alone does not imply human action: keep the real owner and
`human_action_required: false` unless a specific human action is necessary.
Never weaken acceptance criteria, skip mandatory checks, fabricate evidence,
or overwrite unrelated user changes to turn a blocker into a passing result.

When human action is truly required, provide a self-contained tutorial:

1. State the goal and why the agent cannot perform it.
2. List prerequisites and safety warnings; never ask for secrets, cookies,
   private keys, or full tokens.
3. Give numbered exact UI navigation or commands, explain placeholders, and
   state the expected visible result plus a safe failure branch for every step.
4. Give an independent verification step.
5. Name the sanitized status, output, URL/ID, screenshot, or decision to return.
6. Give the exact SPX command or message that resumes from the preserved state.

For a feature runtime blocker, do not author `resume_argv` or replace the
persisted blocker. Use the runtime-returned read-only `show_argv` and structured
`resolution_action`; an empty `next_argv` means evidence is still required.
After the criteria are proven, attach sanitized evidence through the action's
declared input and execute its base argv. It reactivates the same owner and
preserves the prior blocker audit. When a validated strict backward reopen
targets an earlier stage, the blocked `workflow reopen` response also returns
`pending_reopen_action`. It does not replace the blocker. Once the same real
resolution evidence exists, execute that base argv exactly so the runtime
atomically records resolution and reopens the earlier stage instead of
reactivating the same owner first; never reconstruct a separate reopen.

When current evidence proves only some named blocker subcauses are resolved,
expand `workflow.reconcile-blocker` through `specify-runtime api show`, then
submit its revision-bound input with the resolved subcauses and a complete
remaining cause/evidence/scope/recovery contract. The runtime keeps the same
owner/category and blocked state, removes stale current text, and appends the
reconciliation audit. Do not use it when no cause remains; satisfy the original
criteria and use `workflow.resolve` instead.

For protected CI, identify the repository, branch, pipeline/manual job,
authorization boundary, expected terminal state, safe logs to collect, and the
pipeline URL/ID to return. For visual review, identify the real entry point,
viewport/state matrix, approved reference, acceptance criteria, capture, and
resume action. For a product decision, give concrete options and downstream
effects rather than an open-ended request.
