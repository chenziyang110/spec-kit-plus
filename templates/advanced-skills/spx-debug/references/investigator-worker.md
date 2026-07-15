# Investigator worker contract

Use a worker for a bounded evidence lane, not for ownership of the diagnosis.
Provide one hypothesis or evidence question, concrete allowed paths/commands,
forbidden writes, and the observation that would support or weaken it.
For UI evidence, also provide the confirmed UI target baseline, original
references and intents, real entry point, viewport/window, and state. The worker
must not propose a redesign or use the baseline as authority for a speculative
fix.

The worker returns facts only:

- hypothesis tested;
- files, logs, tests, or runtime surfaces inspected;
- commands and exact observations;
- evidence for and against;
- confidence, unknowns, and blocker.

The worker does not edit production files, select the final root cause, or
declare the bug fixed. The leader compares all evidence, owns the causal claim,
performs the fix, and verifies the integrated behavior.
