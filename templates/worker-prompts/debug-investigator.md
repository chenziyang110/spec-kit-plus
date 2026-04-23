# Debug Investigator Worker Prompt

Use this template when the debug leader dispatches an evidence-gathering lane for `sp-debug`.

## Controller Requirements

- Provide the current hypothesis and the exact evidence question this worker must answer.
- Provide the repro command, failing check, or focused code path to inspect.
- State which files or logs are in scope.

## Worker Contract

- Gather facts only for the current hypothesis.
- Return command results, observations, and file-level evidence.
- Do not declare the root cause final.
- Do not update the debug file.
- Do not mutate the investigation state machine.

## Minimum Return Payload

- Hypothesis tested
- Evidence gathered
- Commands run
- Files inspected
- Confidence
- Blocker, if any
- If the current runtime supports structured results, return the same facts in a stable evidence payload rather than freeform narration.
- When the leader provides a delegated result handoff path, write the normalized evidence/result envelope there instead of replying with freeform prose only.

## Guardrails

- Stay on the current hypothesis.
- Prefer decisive signals over broad narration.
- If instrumentation is required, say so explicitly instead of guessing.
- The worker must not update the debug file; the leader remains the only owner of session state.
