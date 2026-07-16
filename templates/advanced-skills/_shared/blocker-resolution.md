# Blocked exit

Read this reference only when the active SPX invocation cannot safely continue
after permitted self-recovery.

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
preserves the prior blocker audit.

For protected CI, identify the repository, branch, pipeline/manual job,
authorization boundary, expected terminal state, safe logs to collect, and the
pipeline URL/ID to return. For visual review, identify the real entry point,
viewport/state matrix, approved reference, acceptance criteria, capture, and
resume action. For a product decision, give concrete options and downstream
effects rather than an open-ended request.
