# Native Subagent Contract

Apply this contract only after the owning workflow selects bounded delegation.

- Discover the active integration's real dispatch and join operations before
  recording a capability blocker. Do not require an operation that the active
  runtime does not expose.
- Dispatch only validated lanes with explicit read/write scope, authoritative
  inputs, acceptance, and verification obligations.
- Prefer `parallel-subagents` only for non-overlapping write scopes. Shared or
  overlapping write scopes default to serial `one-subagent` (resume or
  re-dispatch). A parallel write-conflict error is not permission for the
  Leader to implement that work without a recorded workflow-allowed fallback.
- Launch a safe parallel wave only after isolation is confirmed; otherwise wait
  on serial joins through the owning workflow's start/accept gates.
- An accepted terminal result completes its native lane without a separate
  cleanup operation. Interrupt or cancel only unfinished work that must stop,
  and only through an operation the active runtime exposes.
- Use the result channel owned by the active workflow. Feature lanes such as
  Clarify, Plan, Tasks, Deep Research, and Review use their feature-scoped
  `result submit` route; Quick and PRD Scan use their workspace-scoped route;
  Debug uses its session-scoped route; Implement workers return their result
  inline for the Leader's `implement result-merge`. If a workflow defines no
  runtime result route, return the bounded result inline to the Leader.
- Never redirect an ordinary native lane to `sp-teams` because an unrelated
  lifecycle operation or result path is absent. `sp-teams` is only for an
  explicitly selected durable-team workflow whose state must outlive one
  in-session subagent burst.

The Leader owns joins, synthesis, conflicts, state transitions, and final
claims. A worker result is evidence for those decisions, not permission to
advance or close the owning workflow.
