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
observer_mode: full | compressed
observer_framing_completed: [true only after observer framing and transition memo are both written and the observer gate passes]
framing_gate_passed: [true only after candidate count, diversity, contrarian candidate, and transition memo requirements pass]
skip_observer_reason: [required when observer framing was compressed]
waiting_on_child_human_followup: [true when a parent session is blocked on a derived child issue]
atlas_read_completed: [true only after the atlas gate is complete]
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

## Atlas Read Evidence

atlas_paths_read:
  - [atlas artifact actually read before source-level work]
atlas_root_topics_read:
  - [root topic file actually read]
atlas_module_docs_read:
  - [module overview or module-local doc actually read]
atlas_status_basis: [fresh | missing | stale | possibly_stale plus the decision taken]
atlas_blocked_reason: [why atlas gating blocked work, if it did]

## Observer Framing
<!-- OVERWRITE/REFINE before evidence investigation - outsider view only -->

summary: [high-level outsider summary of the issue]
primary_suspected_loop: [most likely workflow/control loop break from the map view]
suspected_owning_layer: [layer most likely to own the truth]
suspected_truth_owner: [module/system area most likely defining the broken truth]
recommended_first_probe: [best first evidence action for the investigator view]
contrarian_candidate: [strongest materially different alternative candidate]
missing_questions:
  - [question that would materially narrow the issue]
alternative_cause_candidates:
  - candidate: [candidate cause]
    failure_shape: [truth_owner_logic | control_observation_drift | projection_render | cache_snapshot | boundary_contract | config_flag_env | ordering_concurrency]
    why_it_fits: [why it fits the symptom]
    map_evidence: [which handbook/project-map evidence supports it]
    would_rule_out: [what missing information or evidence would eliminate it]
    recommended_first_probe: [best first probe for this specific candidate]

## Transition Memo
<!-- OVERWRITE/REFINE between observer framing and evidence investigation -->

first_candidate_to_test: [which observer candidate the investigator should test first]
why_first: [why this candidate is the best first probe]
evidence_unlock:
  - reproduction
  - logs
  - code
  - tests
  - instrumentation
carry_forward_notes:
  - [what the investigator must preserve from observer framing]

## Suggested Evidence Lanes
<!-- OVERWRITE/REFINE - recommended fan-out lanes for delegated or manual evidence collection -->

- name: [queue-snapshot / source-truth-trace / control-state-trace]
  focus: [what this lane examines]
  evidence_to_collect:
    - [specific evidence item]
  join_goal: [what decision this lane should help make at the join point]

## Candidate Resolutions
<!-- APPEND/REFINE - every high-priority framing candidate must eventually land somewhere -->

- candidate: [candidate text]
  disposition: confirmed | ruled_out | still_open_but_deprioritized
  notes: [why it landed there]

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
alternative_hypotheses_considered:
  - [plausible cause that was actively considered]
alternative_hypotheses_ruled_out:
  - [alternative cause explicitly eliminated]
root_cause_confidence: tentative | supported | confirmed
fix: [empty until applied]
fix_scope: truth-owner | control-boundary | observation-boundary | surface-only
verification: [empty until verified]
agent_fail_count: [automatic verification failures only]
human_reopen_count: [human verification reopen count only]
human_verification_outcome: pending | passed | same_issue | derived_issue | unrelated_issue | insufficient_feedback
validation_results:
  - command: [verification command]
    status: passed | failed | skipped
    output: [summary or command output]
files_changed: []
decisive_signals:
  - [signals that directly adjudicated the key hypothesis]
rejected_surface_fixes:
  - [local fixes that improved symptoms but did not fix the control-plane truth]
loop_restoration_proof:
  - [evidence that the full loop is healthy end-to-end]
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

**Observer Framing:**
- OVERWRITE/REFINE before evidence investigation begins
- Must be built from the user report plus handbook/project-map context only
- Do not use code files, test files, logs, or direct repro results here
- Capture an outsider analysis, not a final root-cause verdict
- This section is incomplete until `summary`, `primary_suspected_loop`, `suspected_owning_layer`, `suspected_truth_owner`, `recommended_first_probe`, and at least one `alternative_cause_candidate` are filled
- Compressed framing still requires the full Observer Framing section; compression only changes why the phase was shortened

**Transition Memo:**
- OVERWRITE/REFINE after observer framing
- Converts the outsider analysis into the first investigator-facing probe order
- Records which evidence surfaces are now unlocked and what the investigator must carry forward
- This section is incomplete until `first_candidate_to_test`, `why_first`, and at least one `evidence_unlock` entry are filled

**Observer Gate:**
- Set `observer_framing_completed: true` only after both `Observer Framing` and `Transition Memo` are complete
- If `observer_mode` is `compressed`, `skip_observer_reason` must be non-empty
- No source-code reads, test reads, log reads, or repro commands are allowed while `observer_framing_completed` is not `true`

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

The session file must always make it clear:
- what the observer framing concluded,
- what the active hypothesis is,
- what experiment is being run,
- why the current logs are sufficient or insufficient,
- which layer owns the relevant truth,
- which state is control state versus observation state,
- where the closed loop is currently believed to break,
- and what the next action is if the session resumes later.

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
- `alternative_hypotheses_considered` should show genuine causal spread before fixing begins.
- `alternative_hypotheses_ruled_out` should show which plausible competitors were actively eliminated.
- `root_cause_confidence` should reach `confirmed` before the session can move into fixing.
- `fix_scope` should classify whether the change repairs the truth owner, a boundary, an observation boundary, or only the surface symptom.
- `surface-only` fixes cannot satisfy the session on their own; they must either be replaced or explicitly reclassified when the real owning-layer failure is understood.
- `loop_restoration_proof` must explain why the full closed loop is healthy after verification instead of only showing a local green test.
- Fields: root_cause(summary, owning_layer, broken_control_state, failure_mechanism, loop_break, decisive_signal), alternative_hypotheses_considered, alternative_hypotheses_ruled_out, root_cause_confidence, fix, fix_scope, verification, files_changed, decisive_signals, rejected_surface_fixes, loop_restoration_proof

</section_rules>
