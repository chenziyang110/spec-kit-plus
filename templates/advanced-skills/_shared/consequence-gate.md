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

Specify persists one `entrypoint_outcome_contract` with separate live-evidence
inventory and product dispositions. Every preserved/adapted outcome maps to
acceptance and `CA-###` refs. Plan and Tasks reuse the existing CA decision,
task, and Review-scenario chain; they do not create a parallel outcome ledger.
