Trigger: when forming, testing, confirming, or rejecting root-cause hypotheses.

Purpose: preserve one-active-hypothesis discipline, candidate queue, causal spread, root-cause confidence, and capability-aware investigation.

Preserved Contract: root cause must be falsifiable, evidence-backed, and recorded before fix work.

## Hypothesis And Root Cause

`Stage 1A Causal Map -> Stage 1B Investigation Contract + Log Investigation Plan -> Evidence Investigation -> Fixing -> Verifying -> Human Verify`
- `Stage 1A: Causal Map`
- `causal_map_completed: true`
  - primary map-backed candidate,
  - materially different contrarian candidate,
  - candidate-separating signals,
- Set `causal_map_completed: true`, `investigation_contract_completed: true`, `log_investigation_plan_completed: true`, and `observer_framing_completed: true` from this package only when the map clearly names an owner, boundary, or minimal read path.
### Stage 1A: Causal Map (Think Subagent)
- This stage is **fallback/deep mode**, not the normal map-backed path. The graph engine (GatheringNode) will return an `await_input` containing a `think_subagent_prompt` when `causal_map_completed` is not yet `true`.
  4. Parse the YAML block after `---` and populate `causal_map`, including `dimension_scan` and `candidate_board`.
  5. Set `causal_map_completed: true`.
- The think subagent produces a causal map based on the user report plus the current system map. It does NOT read source code, logs, or run commands.
- The causal map must include:
  - `candidates`
  - `candidate_board`
- The causal map candidates are the widened alternative cause candidates for the observer-framing phase.
- Produce at least 3 candidates.
- Produce at least 3 alternative cause candidates.
- The contract planner does not widen the hypothesis space. It converts the causal map into:
  - `primary_candidate`
  - `contrarian_candidate`
  - `candidate_queue`
  - `top_candidates`
- The contract planner must preserve candidate-board ordering and runtime-log intent instead of collapsing them into a generic probe note.
- Stage 1B must still leave the session with a clear `contrarian candidate`, a `recommended first probe`, and a transition memo that can automatically continue into evidence investigation.
- **Leader's responsibility**: After parsing the contract-planner result, populate `transition_memo` fields: `first_candidate_to_test`, `why_first`, `evidence_unlock`, and `carry_forward_notes`.
  - `causal_map_completed: true`
  - `Causal Map` contains `dimension_scan`, `candidate_board`, family coverage, and falsifiers
  - `Transition Memo` contains `first_candidate_to_test`, `why_first`, and at least one `evidence_unlock` entry
  - `Investigation Contract` contains `primary_candidate_id`, `candidate_queue`, and related-risk targets
  - `Log Investigation Plan` contains existing log targets, candidate signal mapping, and observability escalation guidance
- Treat logs as evidence, not background noise: if a log line materially changes the hypothesis space, record it in the session `Evidence` section with its source path/command.
  - which candidate-specific signals should appear there,
### Required Framing Before Hypothesis
- Before committing to a root-cause theory, write a **Truth Ownership Map** in the debug session:
- For runtime bug investigations where the leader cannot access the needed logs directly, produce a concrete user log request packet before fixing. Include the time window, target system, identifiers or correlation keys, exact log sources, and the expected candidate-separating signals.
- If two hypothesis/experiment cycles fail to converge, escalate observability explicitly. Add instrumentation that can directly falsify the remaining competing explanations instead of applying another surface-level fix.
### Stage 6: Hypothesis Formation
- Form one specific, falsifiable hypothesis from the evidence.
- Record the hypothesis, the test to run, and the expected result in `Current Focus`.
- State how the hypothesis relates back to the observer framing board: does it confirm, refine, or eliminate one of the observer candidates?
- State why the hypothesis targets the owning layer or control state rather than a downstream projection.
- Run one experiment for the active hypothesis.
- If the result disproves the hypothesis, append it to `Eliminated` and return to Stage 5.
- If the result confirms the failure mechanism, record the root cause and continue to fixing.
- Before leaving this stage, record which plausible causes were considered and which were ruled out so the session shows real causal spread instead of a single-path guess.
- Record any **rejected surface fixes** that improved symptoms without restoring the control loop, so future resumes do not mistake symptom relief for root-cause resolution.
### Stage 8: Root Cause Confirmation
  - why the active hypothesis is stronger than the eliminated alternatives,
- Record explicit causal coverage before fixing:
- Record the root cause in structured form:

## Capability-Aware Investigation

- During `investigating`, the current candidate queue is the execution contract for the stage. The leader should not drift into unrelated freeform probing while the active primary candidate is still unresolved.
- Candidate queue entries must be consumed explicitly: confirm them, rule them out, or deprioritize them with evidence. Do not let high-priority candidates silently disappear from the session.

- During `investigating`, determine whether the current investigation has one or more safe evidence-collection lanes before running multiple independent evidence-gathering actions sequentially.
- [AGENT] Use the shared policy function with the current capability snapshot when the investigation has safe delegated lanes: `choose_subagent_dispatch(command_name="debug", snapshot, workload_shape)`.
- Persist the decision fields exactly: `execution_model: leader-inline | subagent-assisted | blocked`, `dispatch_shape: leader-inline | one-subagent | parallel-subagents | subagent-blocked`, `execution_surface: leader-inline | native-subagents | none`, `dispatch_reason`, and `blocked_reason` when blocked.
- Treat runtime safety as a dispatch-blocking decision. If the next step is unsafe, unavailable, or unpacketizable, use `subagent-blocked`, record `execution_surface: none`, and stop instead of widening brittle native fan-out.
- Debug routing decision order:
  - Small focused investigation with one short evidence chain -> `leader-inline`.
  - One safe validated evidence lane where isolation improves quality -> `one-subagent` on `native-subagents` when available.
  - Two or more independent evidence lanes -> `parallel-subagents` on `native-subagents` when available.
  - No safe lane, shared mutable state, missing contract, incomplete packet, unavailable delegation, or unsafe next step -> `subagent-blocked` with `execution_surface: none` and a recorded reason.
- Dispatch a subagent only when the evidence-lane contract is complete: probe intent, required evidence, authoritative inputs, and validation targets must all be recorded before dispatch.
- If that subagent-readiness bar is not met, compile the missing evidence-lane contract before dispatch; if the lane cannot be made safe, record `subagent-blocked` and stop for escalation or recovery.
- `parallel-subagents` means the leader dispatches bounded evidence-gathering subagents and rejoins at an explicit join point.
- `native-subagents` means the leader uses the current runtime native subagent surface for dispatched evidence lanes.
- The durable team workflow remains separate from ordinary debug dispatch and is not the execution surface for this command.
- Suitable subagent tasks include:
  - running targeted tests or repro commands,
  - collecting logs and exit codes,
  - searching for error text,
  - tracing isolated code paths,
  - comparing independent modules or configurations,
  - assessing whether existing logs are sufficient,
  - and gathering output after temporary or durable diagnostic logging has been added.
- Keep the debug session leader-led: subagents return facts, command results, and observations for the current hypothesis.
- Subagents must not redo observer framing from scratch; they inherit the observer framing and transition memo as the current outsider model.
- Subagents must not mutate the debug session state, declare the root cause final, or archive the session.
- Before dispatching subagent investigation work, update the debug file to reflect the exact current focus and what evidence is being gathered next.
- Use `.specify/templates/worker-prompts/debug-investigator.md` as the default evidence-collector contract whenever the current integration can dispatch a debug subagent.
- If the current runtime supports structured subagent results, prefer a stable evidence payload over freeform summaries so the leader can merge findings without reinterpretation.
- If the current integration exposes a runtime-managed result channel, use that channel. For Codex runtime-managed handoffs, the canonical path requires the runtime dispatch request id and is computed with `{{specify-subcmd:result path --command debug --request-id <request-id>}}`; final completion must be reported through the active runtime-managed result channel for that request id.
- Without a runtime-managed result channel, write the normalized evidence/result envelope to `.planning/debug/results/<session-slug>/<lane-id>.json`
- When the local CLI is available and no runtime-managed result channel exists, prefer `{{specify-subcmd:result path --command debug --session-slug <session-slug> --lane-id <lane-id>}}` to compute the canonical handoff target and `{{specify-subcmd:result submit --command debug --session-slug <session-slug> --lane-id <lane-id> --result-file <path>}}` to normalize and write the evidence/result envelope. `result path` emits JSON and does not accept `--format`; do not append `--format`.
- Preserve `reported_status` when normalizing subagent language such as `DONE_WITH_CONCERNS` or `NEEDS_CONTEXT` into canonical orchestration state.
- Idle subagent is not an accepted result.
- [AGENT] The leader must wait for and consume the structured handoff before closing the join point, declaring completion, requesting shutdown, or interrupting subagent execution.
