Trigger: when gathering evidence, reproducing failure, reading logs/tests/source, or building the investigation contract.

Purpose: preserve investigation protocol, mandatory intake contract, reproduction-before-fix, observer framing, evidence plan, and related-risk review.

Preserved Contract: debug must prove reproduction and evidence before forming or acting on root cause.

## Investigation Protocol

### Intake Inputs
- Read `.planning/debug/[slug].md` before each resumed action; treat it as the investigation source of truth.
- Query project cognition with `{{specify-subcmd:project-cognition compass --intent debug --query="$ARGUMENTS" --format json}}`. Read top-level `minimal_live_reads` first, then use lane-level `first_pass_paths` reasons, `verification_hints`, `followup_surfaces`, and `before_fix_claim`. Do not treat first-pass reads as the final edit scope. Use `project-cognition expand` only when the packet's coverage state or live evidence requires it. Use the advanced `lexicon -> semantic_intake -> query` flow only when `compass_state`, coverage diagnostics, localization, or live evidence requires explicit concept decisions. In that escalation, run `project-cognition query --query-plan "<query_plan_json>"` with `query_plan`, `semantic_intake`, `concept_decisions`, and facet coverage
- If the session records `understanding_confirmed: false`, repair or confirm the Debug Understanding Checkpoint before reproduction, log review, source/test reads, evidence collection, subagent dispatch, instrumentation, code edits, or validation.
- If truth ownership, competing truths, stale assumptions, or contradiction signals remain ambiguous, perform only the returned `minimal_live_reads` before continuing.
- [AGENT] If cognition freshness is `missing`, continue with live repository evidence when workflow policy allows degraded advisory navigation; recommend `{{invoke:map-scan}}`, then `{{invoke:map-build}}` only as follow-up brownfield first-baseline maintenance unless the user explicitly requested cognition repair or root-cause analysis truly cannot proceed without a usable baseline.
- [AGENT] If cognition freshness is `stale`, treat map output as advisory, continue with live repository evidence when workflow policy allows, and recommend `{{invoke:map-update}}` as follow-up maintenance only when the user requested cognition repair or stale coverage blocks the investigation.
- [AGENT] If cognition freshness is `support_drift`, continue with live repository evidence when workflow policy allows and record the support-surface drift; do not reflexively route to `{{invoke:map-update}}`.
- [AGENT] If cognition freshness is `partial_refresh`, record that refresh data was recorded but readiness did not pass; follow `recommended_next_action` as advisory unless the workflow truly cannot proceed.
- [AGENT] If cognition freshness is `possibly_stale`, inspect the changed paths, reasons, and affected graph coverage. Use `{{invoke:map-update}}` with the changed paths. Use map-update for ordinary existing-baseline gaps. Use map-scan -> map-build only for first/missing/unusable baseline, schema failure, schema v1 or old broad-schema rebuild-required readiness, zero active-generation path_index rows, missing or invalid alias_index, explicit_rebuild_requested, or baseline_identity_invalid.
- Treat task-relevant cognition coverage as insufficient when the failing area is named only vaguely, lacks ownership or placement guidance, or lacks workflow, constraint, integration, or regression-sensitive testing guidance.
- [AGENT] If task-relevant cognition coverage is insufficient for the failing area, continue with live repository evidence when workflow policy allows and record whether follow-up `{{invoke:map-update}}` with changed paths or affected surfaces is needed. Use map-update for ordinary existing-baseline gaps. Use map-scan -> map-build only for first/missing/unusable baseline, schema failure, schema v1 or old broad-schema rebuild-required readiness, zero active-generation path_index rows, missing or invalid alias_index, explicit_rebuild_requested, or baseline_identity_invalid; block only when the user requested cognition repair or the investigation truly cannot proceed without refreshed coverage.
- Use the debug cognition slice to identify likely truth-owning layers, adjacent workflows, and observability entry points before forming a hypothesis.
- When `ui_confirmation.applicable` is true, use the confirmed UI target
  baseline only as the observation standard: preserve its original references
  and intents, reproduce the real entry point at the confirmed viewport/window
  and state, and capture pre-fix structure, visual, and runtime evidence. Do not
  turn that baseline into a repair design before causal evidence supports one.
- Read `.specify/memory/constitution.md` if present before forming or validating a fix so the investigation honors project-level MUST/SHOULD constraints.
- Consume project rules and Learning through `learning start --command debug`; expand only selected records whose triggers match the failing area.
- The causal map is produced by a **think subagent** (dispatched automatically by the graph engine at Stage 1A). The constraints below apply to that subagent, not to the leader.
- During observer framing, the think subagent must not read source files, test files, log files, or feature-specific planning artifacts such as `spec.md`, `plan.md`, `tasks.md`, or `context.md`.
- The think subagent must not read test files or test outputs; save those for the investigator phase.
- The think subagent must not inspect logs or runtime output; keep the analysis at the system-map level.
- The think subagent must not run reproduction commands, test commands, or instrumentation.
- The think subagent uses only the user report plus the current system map to reason about likely owning layers, truth owners, workflow boundaries, and possible failure loops.
- If critical information is still missing during observer framing, ask at most one concise missing-information question before moving on.

{{spec-kit-include: ../../command-partials/common/pre-analysis-protocol.md}}

## Mandatory Intake Contract

All new `sp-debug` sessions follow this default intake path:

`Project Cognition Compass -> Map-Backed Minimum Intake -> Evidence Investigation -> Fixing -> Verifying -> Human Verify`

Deep fallback path:

`Stage 1A Causal Map -> Stage 1B Investigation Contract + Log Investigation Plan -> Evidence Investigation -> Fixing -> Verifying -> Human Verify`

Canonical stage map:

- `Default Intake: Map-Backed Minimum Intake`
- `Stage 1A: Causal Map`
- `Stage 1B: Investigation Contract + Log Investigation Plan`
- `Stage 2: Evidence Investigation`
- `Stage 3: Fix`
- `Stage 4: Verify`

Do not enter reproduction, log review, test inspection, source-code reads, evidence collection, or fixing until the session records all of the following:

- `understanding_confirmed: true`
- `causal_map_completed: true`
- `investigation_contract_completed: true`
- `log_investigation_plan_completed: true`
- `observer_framing_completed: true`

Repeated failure does not reopen observer-shape choices. It upgrades downstream investigation strength only, including `root_cause` mode and stronger instrumentation requirements.

### Default Intake: Map-Backed Minimum Intake

- Use the returned project cognition compass packet as the default intake source when readiness is `query_ready` or `review`.
- Write the selected capability/symptom, route pack, returned `minimal_live_reads`, competing truths, and coverage gaps into the debug session before source-level work.
- Generate the smallest sufficient intake package:
  - primary map-backed candidate,
  - materially different contrarian candidate,
  - first probe,
  - existing logs or command output to inspect,
  - candidate-separating signals,
  - nearest-neighbor related-risk target.
- Set `causal_map_completed: true`, `investigation_contract_completed: true`, `log_investigation_plan_completed: true`, and `observer_framing_completed: true` from this package only when the map clearly names an owner, boundary, or minimal read path.
- Record `skip_observer_reason: map-backed-minimum-intake` when the deep Stage 1A/1B subagents are not needed.
- Do not use broad repository reads to compensate for a vague map. If the query bundle lacks ownership, placement, constraints, regression-sensitive tests, or minimal reads, route to `{{invoke:map-update}}` or use the deep fallback below.

### Deep Fallback Intake

### Stage 1A: Causal Map (Think Subagent)

- This stage is **fallback/deep mode**, not the normal map-backed path. The graph engine (GatheringNode) will return an `await_input` containing a `think_subagent_prompt` when `causal_map_completed` is not yet `true`.
- **Leader's responsibility**: When you receive the `think_subagent_prompt`:
  1. Dispatch a think subagent with the exact prompt text (use your runtime's subagent dispatch mechanism).
  2. Wait for the subagent's structured result.
  3. The result is hybrid: free-text analysis followed by `---` and a YAML block.
  4. Parse the YAML block after `---` and populate `causal_map`, including `dimension_scan` and `candidate_board`.
  5. Set `causal_map_completed: true`.
- The think subagent produces a causal map based on the user report plus the current system map. It does NOT read source code, logs, or run commands.
- The causal map must include:
  - `symptom_anchor`
  - `closed_loop_path`
  - `break_edges`
  - `bypass_paths`
  - `family_coverage`
  - `candidates`
  - `adjacent_risk_targets`
  - `dimension_scan`
  - `candidate_board`
- The causal map candidates are the widened alternative cause candidates for the observer-framing phase.
- Cover at least 3 failure families.
- Produce at least 3 candidates.
- Produce at least 3 alternative cause candidates.
- Each family must include a falsifier, not just a plausible guess.
- Stage 1A is still intake-only fallback work: no source-code reads, test reads, log reads, or repro commands are allowed while `observer_framing_completed` is not `true`.

### Stage 1B: Investigation Contract + Log Investigation Plan

- After Stage 1A completes in fallback/deep mode, Gathering returns an `await_input` containing `contract_subagent_prompt`.
- **Leader's responsibility**: When you receive `contract_subagent_prompt`:
  1. Dispatch a contract-planner subagent with the exact prompt text.
  2. Wait for the structured result.
  3. Parse the YAML block after `---` and populate `observer_framing`, `transition_memo`, `investigation_contract`, and top-level `log_investigation_plan`.
  4. Set `investigation_contract_completed: true` and `log_investigation_plan_completed: true`.
  5. Set `observer_framing_completed: true` only after Stage 1A and Stage 1B artifacts are present.
- The contract planner does not widen the hypothesis space. It converts the causal map into:
  - `primary suspected loop`
  - `primary_candidate`
  - `contrarian_candidate`
  - `candidate_queue`
  - `related_risk_targets`
  - `transition_memo`
  - `top_candidates`
  - `log_investigation_plan`
- The contract planner must preserve candidate-board ordering and runtime-log intent instead of collapsing them into a generic probe note.
- Stage 1B must still leave the session with a clear `contrarian candidate`, a `recommended first probe`, and a transition memo that can automatically continue into evidence investigation.

### Stage 2: Evidence Investigation

- The transition memo is produced by the contract-planner subagent as part of its YAML output (included in the `---` block).
- **Leader's responsibility**: After parsing the contract-planner result, populate `transition_memo` fields: `first_candidate_to_test`, `why_first`, `evidence_unlock`, and `carry_forward_notes`.
- After writing the Stage 1B package, automatically continue into evidence investigation. Do not stop for confirmation unless human action is required.
- Treat the transition memo as the bridge between the outsider view and the investigator view. The later evidence phase must carry the observer framing forward instead of discarding it.

### Observer Gate
- Before evidence investigation begins, verify all of the following in the debug session:
  - `causal_map_completed: true`
  - `investigation_contract_completed: true`
  - `log_investigation_plan_completed: true`
  - `observer_framing_completed: true`
  - `Causal Map` contains `dimension_scan`, `candidate_board`, family coverage, and falsifiers
  - `Observer Framing` contains the required outsider-analysis fields
  - `Transition Memo` contains `first_candidate_to_test`, `why_first`, and at least one `evidence_unlock` entry
  - `Investigation Contract` contains `primary_candidate_id`, `candidate_queue`, and related-risk targets
  - `Log Investigation Plan` contains existing log targets, candidate signal mapping, and observability escalation guidance
- If any observer-gate item is missing, return to Stage 1 or Stage 2 instead of reading code, logs, tests, or running reproduction.
- No source-code reads, test reads, log reads, or repro commands are allowed while `observer_framing_completed` is not `true`.

### Stage 3: Reproduction Gate
- Capture expected behavior, actual behavior, reproduction steps, and observed errors in the session file before running the first repro.
- Confirm that the bug is reproducible through a command, script, or explicit manual sequence.
- If reproduction is not yet verified, stop and gather what is missing before theorizing.

### Stage 4: Log Review
- Inspect existing logs, error output, and test output before changing code.
- Logs are a first-class evidence source and existing logs come first.
- Treat logs as evidence, not background noise: if a log line materially changes the hypothesis space, record it in the session `Evidence` section with its source path/command.
- Identify whether the current observability already shows:
  - where the failure occurs,
  - which inputs or branches matter,
  - what external dependencies returned,
  - and what state changed immediately before failure.
- Read the active feature's `spec.md`, `plan.md`, and `tasks.md` when available to recover intended behavior, locked planning decisions, and implementation boundaries relevant to the bug.
- If `context.md` exists for the active feature, read it before proposing a fix so locked decisions, canonical references, and user-signaled constraints are not bypassed during debugging.
- For runtime bugs, use the investigation contract's `log_investigation_plan` log investigation plan to decide:
  - which existing log targets to inspect first,
  - which candidate-specific signals should appear there,
  - whether logs are sufficient,
  - and whether instrumentation or a user log request must happen before fixing.

### Required Framing Before Hypothesis
- Before committing to a root-cause theory, write a **Truth Ownership Map** in the debug session:
  - which layer owns the decision truth,
  - which layers only reflect or cache it,
  - and what evidence supports that ownership claim.
- Split state into **Control State** and **Observation State**:
  - `Control State` covers counters, queues, admission sets, scheduler slots, ownership sets, and other values used to make decisions.
  - `Observation State` covers UI status, logs, task tables, snapshots, event streams, and other externally visible projections.
- Write the expected **Closed Loop** in the session file:
  - input event -> control decision -> resource allocation -> state transition -> external observation
- Prefer hypotheses that explain the control-plane truth, not just the visible symptom layer.

### Stage 5: Observability Assessment
- If the current logs cannot answer those questions, treat observability as insufficient.
- During `investigating`, you may add or refine diagnostic logging, tracing, or instrumentation, then rerun the reproduction or tests to collect stronger evidence.
- If logs are insufficient during a runtime bug investigation, you cannot directly enter fixing until the work either extracts decisive signals from existing logs or records an instrumentation / user log request escalation.
- Prefer diagnostic logging that clarifies boundaries, inputs, branches, outputs, and state transitions.
- Prefer **decisive signals** over broad debug noise:
  - queue contents,
  - ownership sets,
  - running/admitted collections,
  - resource counters,
  - and the exact handoff points between decision layers.
- Bias your instrumentation to the active problem profile when one is apparent:
  - **scheduler/admission**: queues, running/admitted sets, slot counters, promotion handoffs
  - **cache/snapshot drift**: authoritative state versus cached state, invalidation timing, refresh paths
  - **UI projection**: source-of-truth state, publish boundary, transformed view-model state, render/polling output
- For runtime bug investigations where the leader cannot access the needed logs directly, produce a concrete user log request packet before fixing. Include the time window, target system, identifiers or correlation keys, exact log sources, and the expected candidate-separating signals.
- If two hypothesis/experiment cycles fail to converge, escalate observability explicitly. Add instrumentation that can directly falsify the remaining competing explanations instead of applying another surface-level fix.

### Stage 6: Hypothesis Formation
- Form one specific, falsifiable hypothesis from the evidence.
- Record the hypothesis, the test to run, and the expected result in `Current Focus`.
- State how the hypothesis relates back to the observer framing board: does it confirm, refine, or eliminate one of the observer candidates?
- State why the hypothesis targets the owning layer or control state rather than a downstream projection.

### Stage 7: Experiment Loop
- Run one experiment for the active hypothesis.
- Append the observed result to `Evidence`.
- If the result disproves the hypothesis, append it to `Eliminated` and return to Stage 5.
- If the result confirms the failure mechanism, record the root cause and continue to fixing.
- Before leaving this stage, record which plausible causes were considered and which were ruled out so the session shows real causal spread instead of a single-path guess.
- Record any **rejected surface fixes** that improved symptoms without restoring the control loop, so future resumes do not mistake symptom relief for root-cause resolution.

### Stage 8: Root Cause Confirmation
- Before entering fixing, be able to explain:
  - what failed,
  - why it failed,
  - why the active hypothesis is stronger than the eliminated alternatives,
  - which layer owned the broken truth,
  - which decisive signals ruled out the competing explanations,
  - whether the issue was in control state, observation state, or the boundary between them,
  - and what behavior change should resolve the full loop instead of only a local inconsistency.
- Record explicit causal coverage before fixing:
  - `alternative_hypotheses_considered`
  - `alternative_hypotheses_ruled_out`
  - `root_cause_confidence`
- Use `root_cause_confidence: confirmed` only when the current explanation is stronger than the ruled-out alternatives and the decisive signals directly support it.
- Record the root cause in structured form:
  - `summary`
  - `owning_layer`
  - `broken_control_state`
  - `failure_mechanism`
  - `loop_break`
  - `decisive_signal`
