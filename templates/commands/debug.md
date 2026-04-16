---
description: Systematic and resumable bug investigation and fixing.
scripts:
  sh: scripts/bash/check-prerequisites.sh --json
  ps: scripts/powershell/check-prerequisites.ps1 -Json
---

## User Input

```text
$ARGUMENTS
```

## Role
You are the debug session leader. Investigate a bug using a persistent, resumable workflow that favors evidence over guesswork.

- The user is the reporter. They describe symptoms and confirm whether the final behavior is fixed.
- The leader owns the session file, the current hypothesis, all state transitions, the final fix, and the verification checkpoint.
- Any delegated helpers are evidence collectors. They do not own the investigation and must not decide that the bug is resolved.

## Operating Principles

- **Evidence before fixes**: Do not change production behavior until you can explain the failure mechanism.
- **Find truth ownership before chasing symptoms**: Identify which layer owns the critical truth and which layers only reflect, cache, or project it.
- **One active hypothesis at a time**: Parallel evidence gathering is allowed; parallel root-cause theories are not.
- **Observability before speculation**: Read existing logs and outputs first. If they are too weak to explain the failure, improve logging or tracing before attempting a fix.
- **Control state is not observation state**: Keep scheduling, admission, allocation, and ownership state separate from UI, logs, event streams, caches, and snapshots.
- **Persistence is memory**: The debug session file in `.planning/debug/[slug].md` is the source of truth. Update it before each action.
- **Leader-led investigation**: The leader integrates evidence and decides what happens next. Delegated helpers only gather bounded facts.
- **Debug the loop, not just the point**: Validate the path from input event to control decision to resource allocation to state transition to external observation.
- **Escalate diagnostics when the loop is still ambiguous**: If two investigation rounds do not converge, stop layering plausible small fixes and add decisive instrumentation.

## Session Lifecycle

1. **Check for Active Session**
   - Look for existing files in `.planning/debug/*.md` (excluding `resolved/`).
   - If a session exists and no new issue is described, resume it.
   - If a new issue is described, start a new session.

2. **Initialize or Resume**
   - Create or read the session file in `.planning/debug/[slug].md`.
   - Announce the current status, current hypothesis, and immediate next action.

3. **Run the Investigation Protocol**
   - Move through the investigation stages below.
   - Update the debug file before each action.
   - Append every confirmed finding to `Evidence`.
   - Append every disproven theory to `Eliminated`.

4. **Fix and Verify**
   - Apply the smallest fix that addresses the confirmed root cause.
   - Verify with the reproduction steps and relevant tests.

5. **Human Verification**
   - Once the fix is verified by the agent, request a human confirmation checkpoint.

6. **Archive and Commit**
   - After human confirmation, move the session file to `resolved/`.
   - Commit the fix and the debug documentation.

## Investigation Protocol

### Required Context Inputs
- Read `.planning/debug/[slug].md` before each resumed action; treat it as the investigation source of truth.
- Read `.specify/memory/constitution.md` if present before forming or validating a fix so the investigation honors project-level MUST/SHOULD constraints.
- Read the active feature's `spec.md`, `plan.md`, and `tasks.md` when available to recover intended behavior, locked planning decisions, and implementation boundaries relevant to the bug.
- If `context.md` exists for the active feature, read it before proposing a fix so locked decisions, canonical references, and user-signaled constraints are not bypassed during debugging.

### Stage 1: Symptom Intake
- Capture expected behavior, actual behavior, reproduction steps, and observed errors.
- Do not ask the user for the fix. Ask only for symptom detail or missing reproduction information.

### Stage 2: Reproduction Gate
- Confirm that the bug is reproducible through a command, script, or explicit manual sequence.
- If reproduction is not yet verified, stop and gather what is missing before theorizing.

### Stage 3: Log Review
- Inspect existing logs, error output, and test output before changing code.
- Identify whether the current observability already shows:
  - where the failure occurs,
  - which inputs or branches matter,
  - what external dependencies returned,
  - and what state changed immediately before failure.

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

### Stage 4: Observability Assessment
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

### Stage 5: Hypothesis Formation
- Form one specific, falsifiable hypothesis from the evidence.
- Record the hypothesis, the test to run, and the expected result in `Current Focus`.
- State why the hypothesis targets the owning layer or control state rather than a downstream projection.

### Stage 6: Experiment Loop
- Run one experiment for the active hypothesis.
- Append the observed result to `Evidence`.
- If the result disproves the hypothesis, append it to `Eliminated` and return to Stage 5.
- If the result confirms the failure mechanism, record the root cause and continue to fixing.
- Record any **rejected surface fixes** that improved symptoms without restoring the control loop, so future resumes do not mistake symptom relief for root-cause resolution.

### Stage 7: Root Cause Confirmation
- Before entering fixing, be able to explain:
  - what failed,
  - why it failed,
  - why the active hypothesis is stronger than the eliminated alternatives,
  - which layer owned the broken truth,
  - which decisive signals ruled out the competing explanations,
  - whether the issue was in control state, observation state, or the boundary between them,
  - and what behavior change should resolve the full loop instead of only a local inconsistency.
- Record the root cause in structured form:
  - `summary`
  - `owning_layer`
  - `broken_control_state`
  - `failure_mechanism`
  - `loop_break`
  - `decisive_signal`

## Capability-Aware Investigation

- During `investigating`, decide whether the current investigation should stay `single-agent` or switch to delegated evidence collection before running multiple independent evidence-gathering actions sequentially.
- Use the shared policy function with the current capability snapshot: `choose_execution_strategy(command_name="debug", snapshot, workload_shape)`.
- Strategy names are canonical and must be used exactly: `single-agent`, `native-multi-agent`, `sidecar-runtime`.
- Debug routing decision order:
  - If there are fewer than 2 independent evidence-gathering lanes, or the planned evidence work would share mutable state -> `single-agent` (`no-safe-batch`)
  - Else if `snapshot.native_multi_agent` -> `native-multi-agent` (`native-supported`)
  - Else if `snapshot.sidecar_runtime_supported` -> `sidecar-runtime` (`native-missing`)
  - Else -> `single-agent` (`fallback`)
- `single-agent` means the leader continues investigating alone.
- `native-multi-agent` means the leader delegates bounded evidence-gathering lanes through the integration's native delegation surface.
- `sidecar-runtime` means the leader escalates the evidence-gathering lanes through the integration's coordinated runtime surface when native delegation is unavailable.
- Suitable delegated tasks include:
  - running targeted tests or repro commands,
  - collecting logs and exit codes,
  - searching for error text,
  - tracing isolated code paths,
  - comparing independent modules or configurations,
  - assessing whether existing logs are sufficient,
  - and gathering output after temporary or durable diagnostic logging has been added.
- Keep the debug session leader-led: delegated helpers return facts, command results, and observations for the current hypothesis.
- Delegated helpers must not mutate the debug session state, declare the root cause final, or archive the session.
- Before dispatching delegated investigation work, update the debug file to reflect the exact current focus and what evidence is being gathered next.

## Debug File Protocol

- **Location**: `.planning/debug/[slug].md`
- **Current Focus**: OVERWRITE on every update. Reflects exactly what the leader is doing now.
- **Evidence**: APPEND confirmed findings only.
- **Eliminated**: APPEND disproven theories only.
- **Update Rule**: Update the file before taking an action.

The session file must always make it clear:
- what the active hypothesis is,
- what experiment is being run,
- why the current logs are sufficient or insufficient,
- which layer owns the relevant truth,
- which state is control state versus observation state,
- where the closed loop is currently believed to break,
- and what the next action is if the session resumes later.

## Fix and Verify Protocol

- Enter `fixing` only after the root cause is confirmed.
- Apply the minimum code change needed to address that root cause.
- Fix the owning control-plane failure first. Do not treat a UI/status smoothing change as sufficient unless the closed loop is proven healthy end-to-end.
- After changing code, rerun:
  - the reproduction path,
  - the most relevant tests,
  - and any logging-enhanced repro flow needed to prove the mechanism changed.
- Verify the full control loop, not only one function or field:
  - triggering input,
  - control decision,
  - resource allocation,
  - resulting state transition,
  - and external observation.
- If verification fails, return to `investigating` with updated evidence. Do not keep layering fixes without updating the hypothesis.

## Checkpoint Protocol

Return a `## CHECKPOINT REACHED` block when user action or confirmation is required.

- **Type**: `human-verify`, `human-action`, or `decision`
- **Progress**: concise summary of the root cause, key evidence, and eliminated hypotheses
- **Awaiting**: exactly what the user must do next

Use `human-verify` after the agent has verified the fix and needs the user to confirm the bug is resolved in their environment.

To begin the debug session:
`EXECUTE_COMMAND: debug`
