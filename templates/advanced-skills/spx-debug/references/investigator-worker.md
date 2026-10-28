# Investigator worker contract

Use a worker for a bounded evidence lane, not for ownership of the diagnosis.
Provide one hypothesis or evidence question, concrete allowed paths/commands,
forbidden writes, and the observation that would support or weaken it.
Read-only evidence workers may run during unconfirmed diagnosis after the
leader completes the intake flags; they require no early repair approval. For
UI evidence, provide the provisional existing/source-backed target before
repair confirmation, or the confirmed UI repair target afterward, plus original
references and intents, real entry point, viewport/window, and state. Label the
target's approval status. The worker must not propose a redesign or use either
target as authority for a speculative fix.

The worker returns facts only:

- hypothesis tested;
- files, logs, tests, or runtime surfaces inspected;
- commands and exact observations;
- evidence for and against;
- confidence, unknowns, and blocker.

The worker does not edit product or test files, repair a harness, add persistent
instrumentation, select the final root cause, or declare the bug fixed. Return
an evidence gap if such diagnostic work is needed; the leader obtains bounded
diagnostic-enablement authority before a separate mutation lane. The leader
compares all evidence, owns the causal claim, presents the concrete
evidence-backed-repair checkpoint, and obtains user approval before performing
the guarded fix or dispatching a fix worker. Verify integrated behavior afterward.
