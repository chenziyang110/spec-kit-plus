# Consequence gate

Read this only when work changes shared state, lifecycle, concurrency,
destructive behavior, security, public/protocol contracts, generated consumers,
or recovery semantics.

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
