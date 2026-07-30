# Consequence gate

Read this only when work changes shared state, lifecycle, concurrency,
destructive behavior, security, public/protocol contracts, generated consumers,
or recovery semantics. Also trigger for a new or changed entry point over an
existing operation, a direct/background/headless/system entry point, or a
changed consumer/interaction owner.

For that entry-point trigger, inspect current result/error definitions,
existing consumers, state transitions, tests, and UI/window/request/retry
owners. Reusing an executor does not prove that its new consumer preserves all
terminal, recoverable, partial, cancelled, or user-input-required outcomes.

Identify the affected objects and, for each material one:

- source of truth and mutation owner;
- allowed states and transitions;
- observers and downstream consumers;
- behavior during failure, retry, cancellation, timeout, rollback, and resume;
- evidence required to prove the new contract at a real entry point.

Turn each unresolved consequence into a requirement, design decision, task, or
blocker owned by the current workflow. Do not leave it as generic "consider
edge cases" prose. When no trigger applies, do not create a consequence matrix
or placeholder section.

The owning workflow persists one outcome contract with separate live-evidence
inventory and product dispositions. Specify writes
`entrypoint_outcome_contract` in `spec-contract.json`; Quick writes the same
inventory, dispositions, acceptance mapping, and `CA-###` refs in task-local
`PLAN.md`, with active statuses and the artifact reference in `STATUS.md`.
Plan and Tasks reuse Specify's CA decision, task, and Review-scenario chain;
Quick carries its refs through batches, worker packets, and closeout without
creating a feature spec. Consequence breadth alone never forces Quick to
`spx-specify`.
