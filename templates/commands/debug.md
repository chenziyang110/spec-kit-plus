---
description: Use when a bug, regression, failed verification, or unexpected runtime behavior needs a resumable investigation and fix workflow.
workflow_contract:
  when_to_use: A defect or failed verification needs structured root-cause investigation instead of ad hoc fixes.
  primary_objective: Build a resumable debug session that gathers evidence, identifies root cause, applies a fix, and verifies the result.
  primary_outputs: Debug-session state, evidence, verified fix artifacts when justified, and an honest blocked/resolved status.
  default_handoff: Stay inside the debug session until resolved or blocked; route back to execution only after the defect contract is satisfied.
scripts:
  sh: scripts/bash/check-prerequisites.sh --json
  ps: scripts/powershell/check-prerequisites.ps1 -Json
---

{{spec-kit-include: ../command-partials/debug/shell.md}}

## Mandatory Subagent Execution

All substantive tasks in ordinary `sp-*` workflows default to and must use subagents.

The leader orchestrates: route, split tasks, prepare task contracts, dispatch subagents, wait for structured handoffs, integrate results, verify, and update state.

Before dispatch, every subagent lane needs a task contract with objective, authoritative inputs, allowed read/write scope, forbidden paths, acceptance checks, verification evidence, and structured handoff format.

Use `execution_model: subagent-mandatory`.
Use `dispatch_shape: one-subagent | parallel-subagents`.
Use `execution_surface: native-subagents`.


## Role
You are the debug session leader. Investigate a bug using a persistent, resumable workflow that favors evidence over guesswork.

- The user is the reporter. They describe symptoms and confirm whether the final behavior is fixed.
- You are the workflow leader and orchestrator.
- You own routing, task splitting, task contracts, dispatch, join points, integration, verification, and state updates.
- Subagents own the substantive task lanes assigned through task contracts.
- The leader owns the session file, the current hypothesis, all state transitions, the final fix decision, and the verification checkpoint.
- Evidence-collection subagents do not own the investigation and must not decide that the bug is resolved.
- You are not the default evidence worker for every lane; substantive evidence work belongs on subagent lanes after observer framing and task contracts are ready.
- When the investigation splits into safe bounded lanes, route, integrate, and decide rather than manually performing every lane sequentially.

## Operating Principles

- **Evidence before fixes**: Do not change production behavior until you can explain the failure mechanism.
- **Find truth ownership before chasing symptoms**: Identify which layer owns the critical truth and which layers only reflect, cache, or project it.
- **One active hypothesis at a time**: Parallel evidence gathering is allowed; parallel root-cause theories are not.
- **Observability before speculation**: Read existing logs and outputs first. If they are too weak to explain the failure, improve logging or tracing before attempting a fix.
- **Logs are a first-class evidence source**: When existing logs, stderr/stdout, test output, or trace files materially narrow the issue, append it to `Evidence` with `source_type: log` (or the closest concrete source type) and a concrete `source_ref`.
- **Control state is not observation state**: Keep scheduling, admission, allocation, and ownership state separate from UI, logs, event streams, caches, and snapshots.
- **Persistence is memory**: The debug session file in `.planning/debug/[slug].md` is the source of truth. Update it before each action.
- **Leader-led investigation**: The leader integrates evidence and decides what happens next. Delegated helpers only gather bounded facts.
- **Begin as an observer**: Start by acting like a knowledgeable outsider who only has the user report plus the current system map. Do not rush into code-level detail just because implementation files exist.
- **Stage 1A: Causal Map**: The first subagent builds a family-spanning causal map before contract generation begins.
- **Stage 1B: Investigation Contract**: The second subagent converts the causal map into the minimum contract the investigator must consume.
- **The second stage must consume the candidate queue**: Investigation cannot skip the Stage 1B contract and jump straight to freeform fixes.
- **Family coverage is the quality bar**: Observer framing is not complete until the causal map spans enough failure families and each family includes a falsifier.
- **Observer framing remains the bridge artifact**: Stage 1B still records `primary suspected loop`, `recommended first probe`, and a `contrarian candidate` before evidence collection begins.
- **Debug the loop, not just the point**: Validate the path from input event to control decision to resource allocation to state transition to external observation.
- **Escalate diagnostics when the loop is still ambiguous**: If two investigation rounds do not converge, stop layering plausible small fixes and add decisive instrumentation.
- **Root-cause mode is mandatory after repeated failure**: After two automated verification failures, stop adding point fixes and switch the session into `root-cause mode`.
- **Related-risk review is part of closeout**: Do not close the session until nearest-neighbor related risk targets have been reviewed.
- **Execution intent stays explicit**: Record the current verification outcome, active constraints, and required success evidence in the session file before and during verification so resume decisions do not depend on chat memory.

## Passive Project Learning Layer

- [AGENT] Run `{{specify-subcmd:learning start --command debug --format json}}` when available so passive learning files exist, the current debug run sees relevant shared project memory, and repeated candidates, including repeated high-signal candidates, can be auto-promoted into shared learnings at start.
- Read `.specify/memory/constitution.md`, `.specify/memory/project-rules.md`, and `.specify/memory/project-learnings.md` in that order before broader command-local context.
- Review `.planning/learnings/candidates.md` only when it still contains debug-relevant candidate learnings after the passive start step, especially repeated pitfalls, recovery paths, or project constraints for the failing area.
- [AGENT] When investigation friction appears, run `{{specify-subcmd:hook signal-learning --command debug ...}}` with retry, hypothesis-change, validation-failure, false-start, or hidden-dependency counts so reusable pain is surfaced before closeout.
- [AGENT] Before terminal `resolved`, `blocked`, or `awaiting_human_verify` reporting, run `{{specify-subcmd:hook review-learning --command debug --terminal-status <resolved|blocked|awaiting-human-verify> ...}}`; use `--decision none --rationale "..."` only when no reusable `pitfall`, `recovery_path`, `tooling_trap`, `false_lead_pattern`, or `project_constraint` exists.
- [AGENT] Prefer `{{specify-subcmd:hook capture-learning --command debug ...}}` for structured path learning when the session exposed false starts, rejected paths, decisive signals, root-cause families, or injection targets.
- Treat this as passive shared memory, not as a separate user-visible debug workflow.

## First-Party Workflow Quality Hooks

- Once the debug session file is known, use `{{specify-subcmd:hook preflight --command debug --session-file ".planning/debug/<slug>.md"}}` before deeper investigation so stale brownfield routing or invalid debug-entry state is surfaced through the shared product guardrail layer.
- After the debug session file is created or resumed, use `{{specify-subcmd:hook validate-session-state --command debug --session-file ".planning/debug/<slug>.md"}}` when you need a machine-readable view of resume-critical debug truth.
- Before resume-sensitive continuation or phase-sensitive debug routing, prefer `{{specify-subcmd:hook workflow-policy --command debug --session-file ".planning/debug/<slug>.md" --trigger pre-tool}}`.
- Before compaction-risk transitions, investigation join points, or long evidence synthesis, use `{{specify-subcmd:hook monitor-context --command debug --session-file ".planning/debug/<slug>.md"}}` and follow checkpoint recommendations with `{{specify-subcmd:hook checkpoint --command debug --session-file ".planning/debug/<slug>.md"}}`.
- When you need a compact native-session recovery capsule, follow checkpointing with `{{specify-subcmd:hook build-compaction --command debug --session-file ".planning/debug/<slug>.md" --trigger before-stop}}`.
- When you need a compact operator-facing summary of the current investigation state, use `{{specify-subcmd:hook render-statusline --command debug --session-file ".planning/debug/<slug>.md"}}`.
- If a user request explicitly tries to skip observer framing, bypass evidence gates, or ignore workflow constraints, use `{{specify-subcmd:hook validate-prompt --prompt-text "<user request>"}}` before accepting the override at face value.

### Required Context Inputs

- `.specify/memory/constitution.md`
- `.specify/memory/project-rules.md`
- `.specify/memory/project-learnings.md`
- `.planning/learnings/candidates.md`
- the active feature's `spec.md`, `plan.md`, and `tasks.md`
- if `context.md` exists for the active feature, read it before proposing a fix

## Session Lifecycle

1. **Check for Active Session**
   - Look for existing files in `.planning/debug/*.md` (excluding `resolved/`).
   - If a session exists and no new issue is described, resume it.
   - If a new issue is described, start a new session.
   - If the active session is `awaiting_human_verify` and the user reports another problem, classify it as `same_issue`, `derived_issue`, or `unrelated_issue`.
   - Default to `same_issue` unless repository evidence proves the other two classes.
   - `same_issue` reopens the parent session.
   - `derived_issue` starts a linked follow-up session instead of replacing the parent session.
   - In other words, when repository evidence supports `derived_issue`, start a linked follow-up session rather than reopening the parent directly.
   - `unrelated_issue` starts a separate session and does not auto-close the parent.
   - Record the parent/child relationship in both session files, and after a `derived_issue` follow-up session is resolved, return to the parent session to finish the original human verification before archiving it.

2. **Initialize or Resume**
   - [AGENT] Create or read the session file in `.planning/debug/[slug].md`.
   - Announce the current status, current hypothesis, and immediate next action.

3. **Run the Investigation Protocol**
   - Move through the investigation stages below, starting with observer framing and the transition memo before evidence collection begins.
   - **Hard gate**: Do not enter Stage 3 (`Reproduction Gate`) or perform any code, log, test, or repro action until the observer gate has passed.
   - The observer gate passes only when the debug session records `observer_framing_completed: true`, `observer_mode`, the required `Observer Framing` fields, and the required `Transition Memo` fields.
   - Update the debug file before each action.
   - Append every confirmed finding to `Evidence`.
   - Append every disproven theory to `Eliminated`.

4. **Fix and Verify**
   - Packetize the smallest safe fix that addresses the confirmed root cause and delegate it through a validated subagent lane.
   - If the fix lane cannot be safely packetized or dispatched, record `subagent-blocked` with the escalation or recovery reason instead of making the fix directly.
   - Verify with the reproduction steps and relevant tests.

5. **Human Verification**
   - Once the fix is verified by the agent, move into a formal human verification stage instead of resolving immediately.
   - The session closes only after explicit human confirmation or an evidence-backed classification into `same_issue`, `derived_issue`, or `unrelated_issue`.

6. **Archive and Commit**
   - After human confirmation, move the session file to `resolved/`.
   - Commit the fix and the debug documentation.

## Required Context Inputs

{{spec-kit-include: ../command-partials/common/context-loading-gradient.md}}

**This command tier: light.** Pass the atlas gate before investigation moves
into reproduction, logs, tests, or source-code reads.

## Project-Map Hard Gate

Before observer framing moves into reproduction, logs, tests, or source-code
reads, pass the atlas gate by reading.

You must pass an atlas gate before reproduction, log review, test inspection,
or source-code reads begin.

1. `PROJECT-HANDBOOK.md`
2. `atlas.entry`
3. `atlas.index.status`
4. `atlas.index.atlas`
5. the relevant root topic documents for workflows, testing, and operations
6. at least one relevant module overview document
7. `atlas.index.relations` when Layer 1 names cross-module or shared-surface risk

## Investigation Protocol

### Observer Framing Inputs
- Read `.planning/debug/[slug].md` before each resumed action; treat it as the investigation source of truth.
- Check whether `.specify/project-map/index/status.json` exists.
- If it exists, use the project-map freshness helper for the active script variant to assess freshness before trusting the current handbook/project-map set.
- [AGENT] If freshness is `missing` or `stale`, run `/sp-map-scan` followed by `/sp-map-build` before root-cause analysis continues, then reload the generated navigation artifacts.
- [AGENT] If freshness is `possibly_stale`, inspect the reported changed paths and reasons plus `must_refresh_topics` and `review_topics`. If `must_refresh_topics` is non-empty for the failing area, run `/sp-map-scan` followed by `/sp-map-build` before root-cause analysis continues. If only `review_topics` are non-empty, review those topical files before widening the investigation.
- [AGENT] Read `PROJECT-HANDBOOK.md` before root-cause analysis so the investigation starts from the current system map.
- [AGENT] If the handbook navigation system is missing, run `/sp-map-scan` followed by `/sp-map-build` before root-cause analysis continues, then reload the generated navigation artifacts.
- Treat task-relevant coverage as insufficient when the touched area is named only vaguely, lacks ownership or placement guidance, or lacks workflow, constraint, integration, or regression-sensitive testing guidance.
- [AGENT] If task-relevant coverage is insufficient for the failing area, run `/sp-map-scan` followed by `/sp-map-build` before root-cause analysis continues, then reload the generated navigation artifacts.
- Read whichever of `ARCHITECTURE.md`, `WORKFLOWS.md`, `INTEGRATIONS.md`, `TESTING.md`, and `OPERATIONS.md` map to the failing area.
- Read the corresponding `.specify/project-map/root/ARCHITECTURE.md`, `.specify/project-map/root/WORKFLOWS.md`, `.specify/project-map/root/INTEGRATIONS.md`, `.specify/project-map/root/TESTING.md`, and `.specify/project-map/root/OPERATIONS.md` files for the failing area.
- Use the navigation system to identify likely truth-owning layers, adjacent workflows, and observability entry points before forming a hypothesis.
- Read `.specify/memory/constitution.md` if present before forming or validating a fix so the investigation honors project-level MUST/SHOULD constraints.
- Read `.specify/memory/project-rules.md` if present before forming or validating a fix.
- Read `.specify/memory/project-learnings.md` if present before forming or validating a fix.
- If `.planning/learnings/candidates.md` exists, inspect only the entries relevant to the failing area so repeated pitfalls, recovery paths, and project constraints are not rediscovered from scratch.
- Observer framing is performed by a **think subagent** (dispatched automatically by the graph engine at Stage 1). The constraints below apply to that subagent, not to the leader.
- During observer framing, the think subagent must not read source files, test files, log files, or feature-specific planning artifacts such as `spec.md`, `plan.md`, `tasks.md`, or `context.md`.
- The think subagent must not read test files or test outputs; save those for the investigator phase.
- The think subagent must not inspect logs or runtime output; keep the analysis at the system-map level.
- The think subagent must not run reproduction commands, test commands, or instrumentation.
- The think subagent uses only the user report plus the current system map to reason about likely owning layers, truth owners, workflow boundaries, and possible failure loops.
- If the user already supplied strong low-level evidence such as a full stack trace, explicit failing command, explicit failing file, explicit repro command, or precise error text with location, use **compressed observer framing** rather than skipping the observer stage.
- If critical information is still missing during observer framing, ask at most one concise missing-information question before moving on.

{{spec-kit-include: ../command-partials/common/pre-analysis-protocol.md}}

## Fast-Path Gate (before Observer Framing)

Check these three conditions. If ALL are true, you may fast-path past the think subagent:

1. **Exact error location known**: File path + line number or function name
2. **Clear reproduction steps**: User provided or trivially inferable
3. **Impact surface bounded**: Single module, no cross-module IPC or shared state

If fast-path: manually set `observer_framing_completed: true`, fill minimal `observer_framing` fields, record `observer_mode: compressed` with `skip_observer_reason`, then re-enter GatheringNode — the graph engine will skip the think-subagent gate and proceed to Stage 3 (Reproduction Gate).

Record: "Fast-path: error at [location], repro [steps], impact bounded to [module]."
If not: proceed to Stage 1 (Observer Framing).

### Stage 1: Observer Framing

This stage is now split into Stage 1A and Stage 1B, but remains the same top-level observer-framing phase for workflow semantics.

### Stage 1A: Causal Map (Think Subagent)

- This stage is **mandatory**. The graph engine (GatheringNode) will return an `await_input` containing a `think_subagent_prompt` when `causal_map_completed` is not yet `true`.
- **Leader's responsibility**: When you receive the `think_subagent_prompt`:
  1. Dispatch a think subagent with the exact prompt text (use your runtime's subagent dispatch mechanism).
  2. Wait for the subagent's structured result.
  3. The result is hybrid: free-text analysis followed by `---` and a YAML block.
  4. Parse the YAML block after `---` and populate the `causal_map` fields plus `observer_mode`.
  5. Set `observer_mode: full` (unless the subagent output indicates `compressed` with a `skip_observer_reason`).
- The think subagent produces a causal map based on the user report plus the current system map. It does NOT read source code, logs, or run commands.
- The causal map must include:
  - `symptom_anchor`
  - `closed_loop_path`
  - `break_edges`
  - `family_coverage`
  - `candidates`
  - `adjacent_risk_targets`
- The causal map candidates are the widened alternative cause candidates for the observer-framing phase.
- Full framing: cover at least 3 failure families.
- Compressed framing: cover at least 2 failure families.
- Full framing: at least 3 candidates.
- Compressed framing: at least 2 candidates.
- Full framing: at least 3 alternative cause candidates.
- Compressed framing: at least 2 for compressed framing.
- Each family must include a falsifier, not just a plausible guess.

### Stage 1B: Investigation Contract

- After Stage 1A completes, Gathering returns an `await_input` containing `contract_subagent_prompt`.
- **Leader's responsibility**: When you receive `contract_subagent_prompt`:
  1. Dispatch a contract-planner subagent with the exact prompt text.
  2. Wait for the structured result.
  3. Parse the YAML block after `---` and populate `observer_framing`, `transition_memo`, and `investigation_contract`.
  4. Set `contract_generation_completed: true`.
- The contract planner does not widen the hypothesis space. It converts the causal map into:
  - `primary suspected loop`
  - `primary_candidate`
  - `contrarian_candidate`
  - `candidate_queue`
  - `related_risk_targets`
  - `transition_memo`
- Stage 1B must still leave the session with a clear `contrarian candidate`, a `recommended first probe`, and a transition memo that can automatically continue into evidence investigation.
- Compressed framing still requires the full observer framing section; compression lowers certainty expectations, not delivery requirements.

### Stage 2: Transition Memo

- The transition memo is produced by the think subagent as part of its YAML output (included in the `---` block).
- **Leader's responsibility**: After parsing the subagent result, populate `transition_memo` fields: `first_candidate_to_test`, `why_first`, `evidence_unlock`, and `carry_forward_notes`.
- Record whether this pass used `full observer framing` or `compressed observer framing`, and why.
- After writing the transition memo, automatically continue into evidence investigation. Do not stop for confirmation unless human action is required.
- Treat the transition memo as the bridge between the outsider view and the investigator view. The later evidence phase must carry the observer framing forward instead of discarding it.
- After the transition memo is written, build or refresh the runtime investigation contract so the second stage has an explicit candidate queue, primary candidate, and related risk targets.
- If `observer_mode` is `compressed`, fill `skip_observer_reason` with the decisive low-level evidence that justified compression.

### Observer Gate
- Before Stage 3 begins, verify all of the following in the debug session:
  - `observer_framing_completed: true`
  - `observer_mode` is set to `full` or `compressed`
  - `skip_observer_reason` is filled when `observer_mode` is `compressed`
  - `Observer Framing` contains the required outsider-analysis fields
  - `Transition Memo` contains `first_candidate_to_test`, `why_first`, and at least one `evidence_unlock` entry
- If any observer-gate item is missing, return to Stage 1 or Stage 2 instead of reading code, logs, tests, or running reproduction.
- No source-code reads, test reads, log reads, or repro commands are allowed while `observer_framing_completed` is not `true`.

### Stage 3: Reproduction Gate
- Capture expected behavior, actual behavior, reproduction steps, and observed errors in the session file before running the first repro.
- Confirm that the bug is reproducible through a command, script, or explicit manual sequence.
- If reproduction is not yet verified, stop and gather what is missing before theorizing.

### Stage 4: Log Review
- Inspect existing logs, error output, and test output before changing code.
- Treat logs as evidence, not background noise: if a log line materially changes the hypothesis space, record it in the session `Evidence` section with its source path/command.
- Identify whether the current observability already shows:
  - where the failure occurs,
  - which inputs or branches matter,
  - what external dependencies returned,
  - and what state changed immediately before failure.
- Read the active feature's `spec.md`, `plan.md`, and `tasks.md` when available to recover intended behavior, locked planning decisions, and implementation boundaries relevant to the bug.
- If `context.md` exists for the active feature, read it before proposing a fix so locked decisions, canonical references, and user-signaled constraints are not bypassed during debugging.
- Read `.specify/testing/TESTING_CONTRACT.md` if present before validating a fix so bug-resolution expectations include any project-wide regression-test requirements.
- Read `.specify/testing/TESTING_PLAYBOOK.md` if present before final verification so the canonical debug-side test commands come from the repository playbook.

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

## Capability-Aware Investigation

- During `investigating`, the current candidate queue is the execution contract for the stage. The leader should not drift into unrelated freeform probing while the active primary candidate is still unresolved.
- Candidate queue entries must be consumed explicitly: confirm them, rule them out, or deprioritize them with evidence. Do not let high-priority candidates silently disappear from the session.

- During `investigating`, decide whether the current investigation can use subagent evidence collection before running multiple independent evidence-gathering actions sequentially.
- [AGENT] Use the shared policy function with the current capability snapshot: `choose_subagent_dispatch(command_name="debug", snapshot, workload_shape)`.
- Persist the decision fields exactly: `execution_model: subagent-mandatory`, `dispatch_shape: one-subagent | parallel-subagents`, `execution_surface: native-subagents`.
- Treat `snapshot.delegation_confidence` as a runtime/model reliability signal. If confidence is `low`, prefer native-subagents or subagent-blocked status over brittle native fan-out.
- Debug routing decision order:
  - One safe validated evidence lane -> `one-subagent` on `native-subagents` when available.
  - Two or more independent evidence lanes -> `parallel-subagents` on `native-subagents` when available.  - No safe lane, shared mutable state, missing contract, low confidence, or unavailable delegation -> `subagent-blocked` with a recorded reason.
- Dispatch that single subagent only when the leader has already recorded enough context, probe intent, and evidence expectations to preserve quality.
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
- If the current integration exposes a runtime-managed result channel, use that channel. Otherwise write the normalized evidence/result envelope to `.planning/debug/results/<session-slug>/<lane-id>.json`
- When the local CLI is available and no runtime-managed result channel exists, prefer `{{specify-subcmd:result path}}` to compute the canonical handoff target and `{{specify-subcmd:result submit}}` to normalize and write the evidence/result envelope.
- Preserve `reported_status` when normalizing subagent language such as `DONE_WITH_CONCERNS` or `NEEDS_CONTEXT` into canonical orchestration state.
- Idle subagent is not an accepted result.
- [AGENT] The leader must wait for and consume the structured handoff before closing the join point, declaring completion, requesting shutdown, or interrupting subagent execution.

## Debug File Protocol

- **Location**: `.planning/debug/[slug].md`
- **observer_framing_completed**: `false` until Observer Framing and Transition Memo are both written and the observer gate is satisfied.
- **observer_mode**: must be set to `full` or `compressed` before Stage 3.
- **skip_observer_reason**: required whenever `observer_mode` is `compressed`.
- **Current Focus**: OVERWRITE on every update. Reflects exactly what the leader is doing now.
- **Evidence**: APPEND confirmed findings only.
- **Eliminated**: APPEND disproven theories only.
- **Update Rule**: Update the file before taking an action.
- No source-code reads, test reads, log reads, or repro commands are allowed while `observer_framing_completed` is not `true`.

The session file must always make it clear:
- what the observer framing concluded,
- what the active hypothesis is,
- what experiment is being run,
- why the current logs are sufficient or insufficient,
- which layer owns the relevant truth,
- which state is control state versus observation state,
- where the closed loop is currently believed to break,
- and what the next action is if the session resumes later.

## Fix and Verify Protocol

- Enter `fixing` only after the root cause is confirmed.
- Write a failing automated repro test before changing production code.
- Do not modify production behavior until the RED state is proven.
- If no reliable automated test surface exists for the failing behavior, add the missing harness first or route through `/sp-test-scan` before code changes.
- Apply the minimum code change needed to address that root cause.
- Fix the owning control-plane failure first. Do not treat a UI/status smoothing change as sufficient unless the closed loop is proven healthy end-to-end.
- Classify the fix before verification:
  - write the classification to `fix_scope`
  - `truth-owner`
  - `control-boundary`
  - `observation-boundary`
  - `surface-only`
- `surface-only` means the change smooths or hides the symptom without repairing the owning truth or the broken handoff. A `surface-only` fix cannot satisfy the debug contract.
- After changing code, rerun:
  - the reproduction path,
  - the most relevant tests,
  - and any logging-enhanced repro flow needed to prove the mechanism changed.
- If `.specify/testing/TESTING_CONTRACT.md` exists and the bug touches a covered module, add or update a regression test before considering the session resolved.
- If `.specify/testing/TESTING_PLAYBOOK.md` defines command-tier expectations for `fast smoke`, `focused`, and `full`, use the fast smoke tier for the cheapest repro check, run the focused tier before accepting the fix, and use the full tier when regression risk remains.
- Verify the full control loop, not only one function or field:
  - triggering input,
  - control decision,
  - resource allocation,
  - resulting state transition,
  - and external observation.
- Record `loop_restoration_proof` before moving to `resolved`. This loop restoration proof should show why the full loop is healthy now, not merely why one surface looks better.
- If verification fails, return to `investigating` with updated evidence. Do not keep layering fixes without updating the hypothesis.
- If automated verification or human verification fails repeatedly without producing a stronger causal explanation, stop the local fix loop and create or refresh `.planning/debug/[slug].research.md` before another code change.
- Use that debug-local research checkpoint to record the missing contract facts, environment assumptions, external references, or repository evidence needed to break the loop.
- If the fix changed truth-owning surfaces, shared surfaces, command/route/contract boundaries, verification entry points, runtime assumptions, or other map-level coverage facts, and verification is truthfully green and no explicit blocker prevents completion, run `/sp-map-scan` followed by `/sp-map-build` before moving to `awaiting_human_verify` or `resolved` so `PROJECT-HANDBOOK.md`, `.specify/project-map/*.md`, and `.specify/project-map/index/status.json` are refreshed in the same pass.
- If you cannot complete that refresh in the current pass, mark `.specify/project-map/index/status.json` dirty through the project-map freshness helper and recommend `/sp-map-scan` followed by `/sp-map-build` before later brownfield work proceeds.
- [AGENT] Resolved debug sessions should auto-capture learning candidates from the persisted debug session state.
- [AGENT] If you are finalizing outside the normal debug CLI closeout path, run `{{specify-subcmd:learning capture-auto --command debug --session-file .planning/debug/[slug].md --format json}}`.
- [AGENT] If the auto-capture pass returns no candidates but you still discovered a reusable `pitfall`, `recovery_path`, or `project_constraint`, fall back to `{{specify-subcmd:learning capture --command debug ...}}`.
- [AGENT] Before leaving the debug session in a terminal state, run `{{specify-subcmd:hook review-learning --command debug --terminal-status <resolved|blocked|awaiting-human-verify> --decision <captured|none|deferred> --rationale "<why>"}}` so the learning closeout gate cannot be skipped.
- Keep lower-signal items as candidates and use `{{specify-subcmd:learning promote --target learning ...}}` only after explicit confirmation or proven recurrence.
- Only ask for confirmation when a new learning is highest-signal, such as an explicit user default, clear cross-stage reuse, or repeated recurrence that should become shared project memory.

## Checkpoint Protocol

Return a `## CHECKPOINT REACHED` block when user action or confirmation is required.

- **Type**: `human-verify`, `human-action`, or `decision`
- **Progress**: concise summary of the root cause, key evidence, and eliminated hypotheses
- **Awaiting**: exactly what the user must do next

Use `human-verify` after the agent has verified the fix and needs the user to confirm the bug is resolved in their environment.

To begin the debug session:
`EXECUTE_COMMAND: debug`
