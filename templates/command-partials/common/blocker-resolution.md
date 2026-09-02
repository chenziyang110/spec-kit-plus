## Blocked Exit Contract

If blocked after safe recovery, read and follow
`.specify/templates/workflow-blocker-template.md` and its JSON schema. Never
return only an error or “ask a human”; preserve state and keep agent-capable
repair agent-owned. Set `human_action_required: true` only for authority,
credentials, protected systems, human decisions/reviews, or physical access.
For Fast, Quick, Implement, and Debug, apply their Autonomous Blocker Recovery
contract first: project-controlled launchers, harnesses, dependencies, tooling,
local services, and supporting scope expansion are not terminal merely because
they sit outside the initial packet.
Tailor steps, expected results, failure paths, evidence, and resume action to
CI, visual review, or product decisions. Never claim completion.

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
