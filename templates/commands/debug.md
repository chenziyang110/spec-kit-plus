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
- **One active hypothesis at a time**: Parallel evidence gathering is allowed; parallel root-cause theories are not.
- **Observability before speculation**: Read existing logs and outputs first. If they are too weak to explain the failure, improve logging or tracing before attempting a fix.
- **Persistence is memory**: The debug session file in `.planning/debug/[slug].md` is the source of truth. Update it before each action.
- **Leader-led investigation**: The leader integrates evidence and decides what happens next. Delegated helpers only gather bounded facts.

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

### Stage 4: Observability Assessment
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

- During `investigating`, if the current runtime supports parallel workers, subagents, or a native delegation surface, you may delegate bounded evidence-gathering tasks to improve throughput.
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
- and what the next action is if the session resumes later.

## Fix and Verify Protocol

- Enter `fixing` only after the root cause is confirmed.
- Apply the minimum code change needed to address that root cause.
- After changing code, rerun:
  - the reproduction path,
  - the most relevant tests,
  - and any logging-enhanced repro flow needed to prove the mechanism changed.
- If verification fails, return to `investigating` with updated evidence. Do not keep layering fixes without updating the hypothesis.

## Checkpoint Protocol

Return a `## CHECKPOINT REACHED` block when user action or confirmation is required.

- **Type**: `human-verify`, `human-action`, or `decision`
- **Progress**: concise summary of the root cause, key evidence, and eliminated hypotheses
- **Awaiting**: exactly what the user must do next

Use `human-verify` after the agent has verified the fix and needs the user to confirm the bug is resolved in their environment.

To begin the debug session:
`EXECUTE_COMMAND: debug`
