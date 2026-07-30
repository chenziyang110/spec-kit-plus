## Fixed Workflow Artifact Boundary

Read canonical workflow artifacts only with `specify-runtime artifact show`. When the worker packet authorizes an artifact mutation, use the specialized owner named by the artifact registry or packet. Generic `artifact prepare` plus `artifact submit` is valid only when prepare explicitly grants submit for that type; fixed-shape artifacts use scaffold plus targeted patch, and result/evidence artifacts use their namespaces. Never overwrite the canonical path directly. Source and test files in the packet's write scope remain normal repository edits.

# Debug Investigator Worker Prompt

Use this template when the debug leader dispatches an evidence-gathering lane for `sp-debug`.

## Controller Requirements

- Provide the current hypothesis and the exact evidence question this worker must answer.
- Provide the repro command, failing check, or focused code path to inspect.
- State which files or logs are in scope.
- For UI-related evidence, provide the confirmed UI target baseline, original references and intents, real entry point, viewport/window, and state to observe. The worker must not propose a redesign.

## Worker Contract

- Gather facts only for the current hypothesis.
- Prefer evidence that can rule the current hypothesis in or out against the strongest nearby alternatives.
- Return command results, observations, and file-level evidence.
- Do not declare the root cause final.
- Do not update the debug file.
- Do not mutate the investigation state machine.
- Use the confirmed UI target baseline only to classify observed drift. Do not infer or approve a repair design before the leader proves the failure mechanism.

## Minimum Return Payload

- Hypothesis tested
- Evidence gathered
- Commands run
- Files inspected
- Confidence
- Blocker, if any
- If the current runtime supports structured results, return the same facts in a stable evidence payload rather than freeform narration.
- When the leader provides a runtime result channel, execute the complete runtime-owned argv prefix from the packet, append `--result-json '<inline-json>'`, and submit the normalized envelope (or use the integration's runtime-managed team channel). The debug command also needs its runtime-supplied session slug and lane ID, so never reconstruct an incomplete command or create/overwrite a result file.
- The worker must not enter `idle` before the required inline handoff is submitted or returned.
- If the handoff channel fails, return that failure explicitly instead of idling silently.

## Guardrails

- Stay on the current hypothesis.
- Prefer decisive signals over broad narration.
- If instrumentation is required, say so explicitly instead of guessing.
- The worker must not update the debug file; the leader remains the only owner of session state.

## Inline Project Cognition Handoff

When you changed project-related files, include `changed_paths`, `behavior_surfaces`, `generated_surfaces`, `state_contracts`, `verification`, `known_unknowns`, and `confidence_notes` in the worker result so the parent workflow can build the inline project cognition update payload. Use `known_unknowns` only for blockers that make the update unsafe to trust; put non-blocking scope notes such as excluded unrelated dirty workspace paths in `confidence_notes`.
