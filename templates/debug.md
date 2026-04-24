# Debug Template

Template for `.planning/debug/[slug].md` — active debug session tracking.

---

## File Template

```markdown
---
slug: [session slug]
status: gathering | investigating | fixing | verifying | awaiting_human_verify | resolved
trigger: "[verbatim user input]"
diagnostic_profile: scheduler-admission | cache-snapshot | ui-projection | general
current_node_id: [ID of the active graph node]
created: [ISO timestamp]
updated: [ISO timestamp]
---

## Current Focus
<!-- OVERWRITE on each update - always reflects NOW -->

hypothesis: [current theory being tested]
test: [how testing it]
expecting: [what result means if true/false]
next_action: [immediate next step]

## Symptoms
<!-- Written during gathering, then immutable -->

expected: [what should happen]
actual: [what actually happens]
errors: [error messages if any]
reproduction: [how to trigger]
reproduction_command: [command or script if available]
started: [when it broke / always broken]
reproduction_verified: [true once repro confirmed]

## Suggested Evidence Lanes
<!-- OVERWRITE/REFINE - recommended fan-out lanes for delegated or manual evidence collection -->

- name: [queue-snapshot / source-truth-trace / control-state-trace]
  focus: [what this lane examines]
  evidence_to_collect:
    - [specific evidence item]
  join_goal: [what decision this lane should help make at the join point]

## Truth Ownership
<!-- APPEND/REFINE during investigation - identifies who owns system truth -->

- layer: [scheduler / engine / API / UI / cache]
  owns: [what this layer is allowed to define as truth]
  evidence: [why this ownership claim is justified]

## Control State
<!-- OVERWRITE/REFINE - state used for decisions, admission, scheduling, or mutual exclusion -->

- [running set / admitted slots / ownership set / queue counters]

## Observation State
<!-- OVERWRITE/REFINE - state used for display, logs, polling, snapshots, or caches -->

- [UI status / event stream / task table / snapshot cache]

## Closed Loop
<!-- OVERWRITE/REFINE - validate the full control loop, not just one function -->

input_event: [what enters the system]
control_decision: [what layer decides what should happen]
resource_allocation: [how slots/resources/ownership are assigned]
state_transition: [what internal state should change]
external_observation: [what should become visible externally]
break_point: [which link in the loop is currently suspected broken]

## Execution Intent
<!-- OVERWRITE/REFINE - the current verification target and the evidence required to accept it -->

outcome: [what the current fix or verification pass is trying to prove]
constraints:
  - [constraints that must remain true while verifying]
success_signals:
  - [observations or checks required before the session can move to resolved]

## Eliminated
<!-- APPEND only - prevents re-investigating after context reset -->

- hypothesis: [theory that was wrong]
  evidence: [what disproved it]
  timestamp: [when eliminated]

## Evidence
<!-- APPEND only - facts discovered during investigation -->

- timestamp: [when found]
  checked: [what was examined]
  found: [what was observed]
  implication: [what this means]

## Resolution
<!-- OVERWRITE as understanding evolves -->

root_cause:
  summary: [one-sentence explanation of the confirmed root cause]
  owning_layer: [which layer owned the broken truth]
  broken_control_state: [which control state was wrong]
  failure_mechanism: [why that control state became wrong]
  loop_break: [where the end-to-end control loop broke]
  decisive_signal: [single strongest signal that ruled out competing theories]
fix: [empty until applied]
verification: [empty until verified]
validation_results:
  - command: [verification command]
    status: passed | failed | skipped
    output: [summary or command output]
files_changed: []
decisive_signals:
  - [signals that directly adjudicated the key hypothesis]
rejected_surface_fixes:
  - [local fixes that improved symptoms but did not fix the control-plane truth]
```

---

<section_rules>

**Frontmatter (status, trigger, timestamps):**
- `status`: OVERWRITE - reflects current phase
- `trigger`: IMMUTABLE - verbatim user input, never changes
- `diagnostic_profile`: OVERWRITE/REFINE - the current issue classification used to bias diagnostic checklists
- `created`: IMMUTABLE - set once
- `updated`: OVERWRITE - update on every change

**Current Focus:**
- OVERWRITE entirely on each update
- Always reflects what the agent is doing RIGHT NOW
- If the agent reads this after context reset, it knows exactly where to resume
- Fields: hypothesis, test, expecting, next_action

**Symptoms:**
- Written during initial gathering phase
- IMMUTABLE after gathering complete
- Reference point for what we're trying to fix
- Fields: expected, actual, errors, reproduction, reproduction_command, started, reproduction_verified

**Suggested Evidence Lanes:**
- OVERWRITE/REFINE as the diagnostic profile changes
- These lanes are the default fan-out plan for delegated evidence gathering or manual division of work
- Keep them aligned with `diagnostic_profile`

**Truth Ownership:**
- REFINE as evidence improves
- Identify which layer owns each critical truth and which layers only project or cache it
- Prevents debugging the symptom layer as if it were the control plane

**Control State / Observation State:**
- Keep these separate
- `Control State` is used for decisions such as scheduling, admission, allocation, or mutual exclusion
- `Observation State` is for UI, logs, event streams, polling, and snapshots
- Do not drive control decisions from observation-only state without explicit justification

**Closed Loop:**
- OVERWRITE/REFINE as understanding improves
- Tracks the full path: input event -> control decision -> resource allocation -> state transition -> external observation
- Use `break_point` to record which link is currently believed to be broken

**Eliminated:**
- APPEND only - never remove entries
- Prevents re-investigating dead ends after context reset
- Each entry: hypothesis, evidence that disproved it, timestamp

**Evidence:**
- APPEND only - never remove entries
- Facts discovered during investigation
- Each entry: timestamp, what checked, what found, implication
- Builds the case for root cause

**Resolution:**
- OVERWRITE as understanding evolves
- Final state shows confirmed root cause and verified fix
- `root_cause` should be structured, not just a sentence
- Fields: root_cause(summary, owning_layer, broken_control_state, failure_mechanism, loop_break, decisive_signal), fix, verification, files_changed, decisive_signals, rejected_surface_fixes

</section_rules>
