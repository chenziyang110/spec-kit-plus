---
name: "sp-debug"
description: "Systematic bug investigation and fixing with persistent session tracking."
compatibility: "Requires spec-kit project structure with .specify/ directory"
metadata:
  author: "github-spec-kit"
  source: "templates/commands/debug.md"
---

# Systematic Debugging Skill

## Role
You are the debug session leader. Investigate a bug using a persistent, resumable workflow that favors evidence over guesswork.

- The user is the reporter. They describe symptoms and confirm whether the final behavior is fixed.
- The leader owns the session file, the current hypothesis, all state transitions, the final fix, and the verification checkpoint.
- Any delegated helpers are evidence collectors. They do not own the investigation and must not decide that the bug is resolved.

## Operating Principles

- **Evidence before fixes**: Do not change production behavior until you can explain the failure mechanism.
- **One active hypothesis at a time**: Parallel evidence gathering is allowed; parallel root-cause theories are not.
- **Observability before speculation**: Read existing logs and outputs first. If they are too weak to explain the failure, improve logging or tracing before attempting a fix.
- **Persistence is memory**: The debug session file in `.planning/debug/[slug].md` is the source of truth. Update it before each action.
- **Leader-led investigation**: The leader integrates evidence and decides what happens next. Delegated helpers only gather bounded facts.

## Codex Leader Gate

When running `sp-debug` in Codex, you are the **leader**, not a freeform debugger.

Before applying fixes or running multiple independent investigation actions yourself:
- Read the current debug session state and identify whether the investigation has two or more independent evidence-gathering lanes.
- If the current stage is `investigating` and there are two or more bounded evidence-gathering lanes, you **MUST** delegate them through `spawn_agent` before continuing with more sequential evidence collection yourself.
- Use `wait_agent` at the investigation join point, integrate the returned facts into `Evidence` or `Eliminated`, and call `close_agent` for completed child agents.
- Do **not** skip delegation just because the evidence tasks look easy; use the lighter `single-agent` path only when the current investigation does not have safe parallel lanes.

**Hard rule:** During `investigating`, the leader must not let child agents mutate the debug file, declare the root cause final, or advance the session state.

## Session Lifecycle

### 1. Check for Active Session
- List `.planning/debug/*.md` (excluding `resolved/`).
- If sessions exist and `$ARGUMENTS` is empty, list them and ask which one to resume.
- If `$ARGUMENTS` is provided, start a new session or resume the most relevant one.

### 2. Initialize or Resume
- **New Session**:
  - Create slug from input (e.g., `api-timeout`).
  - Create `.planning/debug/[slug].md` using the template.
  - Set status to `gathering`.
- **Resume**:
  - Read the existing debug file.
  - Announce status, current hypothesis, and next action.

### 3. Run the Investigation Protocol
- Move through the investigation stages below.
- Update the debug file before each action.
- Append every confirmed finding to `Evidence`.
- Append every disproven theory to `Eliminated`.

### 4. Fix and Verify
- Apply the smallest fix that addresses the confirmed root cause.
- Verify with the reproduction steps and relevant tests.

### 5. Human Verification
- Once the fix is verified by the agent, request a human confirmation checkpoint.

### 6. Resolution and Archiving
- Only after user confirmation:
  - Move the session file to `.planning/debug/resolved/[slug].md`.
  - Commit the code changes and the debug documentation.

## Investigation Protocol

### Required Context Inputs
- Read `.planning/debug/[slug].md` before each resumed action; treat it as the investigation source of truth.
- Read `PROJECT-HANDBOOK.md` before root-cause analysis so the investigation starts from the current system map.
- If the handbook navigation system is missing, analyze the repository and create it before root-cause analysis continues.
- Read whichever of `.specify/project-map/ARCHITECTURE.md`, `.specify/project-map/WORKFLOWS.md`, `.specify/project-map/INTEGRATIONS.md`, `.specify/project-map/TESTING.md`, and `.specify/project-map/OPERATIONS.md` map to the failing area.
- Use the navigation system to identify likely truth-owning layers, adjacent workflows, and observability entry points before forming a hypothesis.
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

### Stage 4: Observability Check
- If the current logs cannot answer those questions, treat observability as insufficient.
- During `investigating`, you may add or refine diagnostic logging, tracing, or instrumentation, then rerun the reproduction or tests to collect stronger evidence.
- Prefer diagnostic logging that clarifies boundaries, inputs, branches, outputs, and state transitions.

### Stage 5: Hypothesis Formation
- Form one specific, falsifiable hypothesis from the evidence.
- Record the hypothesis, the test to run, and the expected result in `Current Focus`.

### Stage 6: Experiment Loop
- Run one experiment for the active hypothesis.
- Append the observed result to `Evidence`.
- If the result disproves the hypothesis, append it to `Eliminated` and return to Stage 5.
- If the result confirms the failure mechanism, record the root cause and continue to fixing.

### Stage 7: Root Cause Confirmation
- Before entering fixing, be able to explain:
  - what failed,
  - why it failed,
  - why the active hypothesis is stronger than the eliminated alternatives,
  - and what behavior change should resolve it.

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
- Keep the debug session leader-led: the leader owns the debug file, the current hypothesis, state transitions, fixes, verification, and human checkpoints.
- Delegated helpers must return facts, command results, and observations for the current hypothesis. They must not mutate the debug session state, declare the root cause final, or archive the session.
- Before dispatching any delegated investigation work, update the debug file to reflect the exact current focus and what evidence is being gathered next.

## Debug File Protocol (Mandatory)
- **Location**: `.planning/debug/[slug].md`
- **Current Focus**: OVERWRITE on every update. Reflects exactly what the leader is doing NOW.
- **Evidence**: APPEND confirmed findings.
- **Eliminated**: APPEND disproven theories.
- **Update Rule**: Update the file BEFORE taking an action.

The session file must always make it clear:
- what the active hypothesis is,
- what experiment is being run,
- why the current logs are sufficient or insufficient,
- and what the next action is if the session resumes later.

## Fix and Verify Protocol
- Enter `fixing` only after the root cause is confirmed.
- Apply the minimal change needed. Update `Resolution.fix`.
- Verify by rerunning the reproduction path, the most relevant tests, and any logging-enhanced repro flow needed to prove the mechanism changed.
- If verification fails, return to `investigating` with updated evidence. Do not keep layering fixes without updating the hypothesis.
- If verification succeeds, transition to `awaiting_human_verify`.

## Checkpoint Protocol
When you reach a point where user action or verification is needed, return a `## CHECKPOINT REACHED` block with:
- **Type**: human-verify, human-action, or decision.
- **Progress**: summary of root cause, evidence, and eliminated hypotheses.
- **Awaiting**: what exactly you need from the user.

Use `human-verify` after the agent has verified the fix and needs the user to confirm the bug is resolved in their environment.

## Codex Native Multi-Agent Investigation

When running `sp-debug` in Codex, treat the `investigating` stage as a leader-led routing decision between `single-agent` and native delegated evidence collection.
- If there are two or more independent evidence-gathering lanes, prefer native delegation through `spawn_agent` over manual sequential investigation.
- Suitable child tasks include running targeted tests or repro commands, collecting logs and exit codes, searching for error text, tracing isolated code paths, comparing independent modules or configurations, judging whether existing logs are detailed enough, and gathering evidence after diagnostic logging has been added.
- Read `diagnostic_profile` from the debug session before choosing child lanes. Treat it as the default evidence-routing hint unless fresh evidence clearly invalidates it.
- If `suggested_evidence_lanes` is populated, use it as the default fan-out plan for child-agent evidence collection and join-point planning.
- Prefer child tasks that gather decisive control-plane signals such as ownership sets, queue contents, resource counters, running collections, and decision-boundary traces.
- Bias delegated evidence collection by profile when possible:
  - `scheduler-admission`: gather queue contents, running/admitted sets, slot counters, and promotion handoff traces in parallel.
  - `cache-snapshot`: gather authoritative control state, cached or snapshot state, invalidation timing, and refresh-path traces in parallel.
  - `ui-projection`: gather source-of-truth state, publish-boundary state, transformed view-model state, and rendered or polled output in parallel.
  - `general`: gather the owning decision-layer state, the observable projection state, and the boundary trace between them.
- The leader **MUST** update the debug file's `Current Focus` before delegating and treat child work as evidence gathering for the current hypothesis, not as parallel hypothesis formation.
- Child agents must return facts, command results, and observations; they must not update the debug file, declare the root cause final, transition the session state, or archive the session.
- Use `wait_agent` only after the current investigation fan-out reaches its join point, then integrate the returned evidence into `Evidence` or `Eliminated` yourself.
- Use `close_agent` after integrating finished child results.
- Keep fixing, verification, `awaiting_human_verify`, and final session resolution on the leader path unless a single explicitly scoped repair task is delegated after the root cause is already established.
