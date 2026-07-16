# Debug Template

Template for `.planning/debug/[slug].md` — active debug session tracking.

---

## File Template

```markdown
---
slug: [session slug]
status: gathering | investigating | fixing | verifying | awaiting_human_verify | resolved
trigger: "[verbatim user input]"
understanding_confirmed: [true only after the user confirms the Debug Understanding Checkpoint]
diagnostic_profile: scheduler-admission | cache-snapshot | ui-projection | general
causal_map_completed: [true after map-backed minimum intake or the Stage 1A causal map is written]
investigation_contract_completed: [true after map-backed minimum intake or the Stage 1B contract planner finishes]
log_investigation_plan_completed: [true after map-backed minimum intake or the Stage 1B log plan is written]
observer_framing_completed: [true after the map-backed or deep canonical intake package is complete]
framing_gate_passed: [true only after family coverage, candidate queue, and related-risk gate checks pass]
legacy_session_needs_reintake: [true only when a resumed legacy session cannot satisfy the new intake contract safely]
execution_model: leader-inline | subagent-assisted | blocked
dispatch_shape: leader-inline | one-subagent | parallel-subagents | subagent-blocked
execution_surface: leader-inline | native-subagents | none
dispatch_reason: [why leader-inline, subagent-assisted, or blocked was selected]
blocked_reason: [required when dispatch_shape is subagent-blocked or execution_surface is none]
waiting_on_child_human_followup: [true when a parent session is blocked on a derived child issue]
skip_observer_reason: [map-backed-minimum-intake when deep Stage 1A/1B was not required]
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

## Debug Understanding Checkpoint
<!-- OVERWRITE/REFINE before substantive investigation starts -->

checkpoint:
  issue: [the symptom, regression, or failing signal the reporter confirmed]
  issue_detail: [where it appears, why it matters, and the nearby issue this session is not debugging]
  expected_or_target: [what should happen instead, or the confirmed unknown]
  reproduction_or_failing_signal: [known repro command, manual sequence, failing test, log/error text, or confirmed unknown]
  known_evidence:
    - [project cognition route, existing log, prior verification output, report, or artifact already available]
  in_scope:
    - [area, workflow, command, state loop, or behavior this session will investigate]
  out_of_scope:
    - [nearby issue, enhancement, or unrelated behavior excluded from this session]
  fix_authority: [diagnose only | diagnose and fix after causal evidence]
  assumptions_to_correct:
    - [reporter assumption, uncertain fact, or none]
  reconfirmation_trigger: [material problem, boundary, authority, compatibility, migration, side-effect, or risk change]
  confirmation_digest: [digest of the confirmed user-owned decisions]
  user_corrections:
    - [user correction, ambiguity, or confirmation timestamp]

ui_confirmation:
  applicable: [true for visual, interaction, responsive, accessibility, TUI, or CLI presentation behavior]
  confirmation_purpose: [Debug target baseline]
  user_and_primary_job: [affected user, context, and single job]
  design_basis_and_source_material:
    - [approved design direction, current entry point, or original reference plus intent]
  target_experience: [expected visual, content, and interaction experience]
  structure_and_visible_change: [structure and visible behavior to restore or preserve]
  interaction_states_and_adaptation:
    - [interaction, state, viewport/window, keyboard, or accessibility expectation]
  design_boundaries:
    must_preserve: []
    may_adapt: []
    must_not: []
  acceptance_evidence:
    - [real-entrypoint state/viewport evidence required after a fix]
  confirmation_digest: [digest of the confirmed UI target baseline]

agent_investigation_plan:
  candidate_focus:
    - [primary suspected truth owner, competing explanation, or candidate family to test first without claiming root cause]
  investigation_plan:
    - [session-specific ordered evidence step]
  next_action: [first reproduction, log, source, test, or instrumentation route after confirmation]
  fix_gate: [what must be proven before code changes are allowed]
  done_or_progress_signal:
    - [evidence that proves the session can move to fix, verification, human verification, or blocked state]

## Atlas Read Evidence

atlas_paths_read:
  - [atlas artifact actually read before source-level work]
atlas_root_topics_read:
  - [root topic file actually read]
atlas_module_docs_read:
  - [module overview or module-local doc actually read]
atlas_status_basis: [fresh | missing | stale | possibly_stale plus the decision taken]
atlas_blocked_reason: [why atlas gating blocked work, if it did]

## Senior Consequence Analysis

consequence_gate_status: not-triggered | triggered | ready | blocked | stood-down
trigger_reason: none
stand_down_reason: none
consequence_obligations:
  - id: CA-###
    claim: [stable consequence claim]
    affected_objects:
      - [object or state surface]
    owner_workflow: [discussion | specify | plan | tasks | debug | implement]
    latest_resolve_phase: [discussion | specify | plan | tasks | implementation | verification]
    status: open | resolved | deferred | stood-down
    stop_and_reopen_condition: [condition that reopens upstream workflow]
affected_objects:
dependency_loop:
control_state:
observation_state:
state_behavior_matrix:
dependency_impact:
recovery_and_validation:
coverage_gaps:
adjacent_risk_targets:
surface_only_fixes_rejected:

## Causal Map
<!-- OVERWRITE/REFINE before evidence investigation - map-backed minimum intake or Stage 1A system-map view -->

symptom_anchor: [where the symptom first appears]
closed_loop_path:
  - [input event]
  - [control decision]
  - [truth owner update]
  - [projection refresh]
  - [external observation]
break_edges:
  - [where the loop most likely breaks]
bypass_paths:
  - [cache or projection bypass]
family_coverage:
  - [truth_owner_logic | cache_snapshot | projection_render]
candidates:
  - candidate_id: [stable candidate id]
    family: [failure family]
    candidate: [concise hypothesis]
    falsifier: [key disconfirming signal]
adjacent_risk_targets:
  - target: [nearest-neighbor risk]
    reason: [why it is related]
    family: [failure family]
    scope: [nearest-neighbor | broader-family]
    falsifier: [what would disconfirm the risk]

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
    map_evidence: [which project cognition evidence supports it]
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

## Investigation Contract
<!-- OVERWRITE/REFINE - converts observer framing into runtime investigation constraints -->

primary_candidate_id: [candidate id currently driving the next investigation step]
investigation_mode: normal | root_cause
escalation_reason: [why the session entered root_cause mode, if it did]
candidate_queue:
  - candidate_id: [stable candidate id]
    candidate: [concise one-line hypothesis]
    family: [truth_owner_logic | projection_render | cache_snapshot | boundary_contract | config_flag_env | ordering_concurrency]
    status: pending | active | confirmed | ruled_out | deprioritized
    evidence_needed:
      - [concrete evidence still required]
    evidence_found:
      - [evidence already collected]
    related_targets:
      - [nearest-neighbor target id]
related_risk_targets:
  - target: [adjacent risk area]
    reason: [why this risk is related]
    scope: [nearest-neighbor | broader-family]
    status: pending | checked | cleared | needs_followup
    evidence:
      - [what was reviewed]
causal_coverage_state:
  competing_candidate_ruled_out: [true|false]
  truth_owner_confirmed: [true|false]
  boundary_break_localized: [true|false]
  related_risk_scan_completed: [true|false]
  closeout_ready: [true|false]
top_candidates:
  - candidate_id: [stable candidate id]
    family: [failure family]
    investigation_priority: [numeric priority order]
    recommended_log_probe: [candidate-specific log probe]

## Log Investigation Plan
<!-- OVERWRITE/REFINE - map-backed or Stage 1B plan for existing logs, candidate signals, and observability gaps -->

existing_log_targets:
  - [existing runtime log, stderr/stdout, trace file, browser console, worker output, or prior artifact to inspect first]
candidate_signal_map:
  - candidate_id: [stable candidate id]
    signals:
      - [signal that would support or weaken this candidate]
log_sufficiency_judgment: [whether existing logs are likely sufficient, and what must happen before fixing if not]
missing_observability:
  - [candidate-separating signal not currently observable]
instrumentation_targets:
  - [boundary, transition, or state owner that needs targeted instrumentation]
instrumentation_style:
  - [preferred targeted logging/tracing style]
user_request_packet:
  - target_source: [log source the user must provide if inaccessible]
    time_window: [specific failing window]
    keywords_or_fields:
      - [identifier or field]
    why_this_matters: [candidate-separating reason]
    expected_signal_examples:
      - [example signal and interpretation]

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
  source_type: log
  source_ref: [for example `logs/app.log`, `runtime-test-output.log`, or the exact command that produced the evidence]
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

**Causal Map:**
- OVERWRITE/REFINE during map-backed minimum intake or Stage 1A
- Captures the project cognition/system-map view before evidence investigation begins
- Tracks family coverage, broken edges, likely bypass paths, and nearest-neighbor risks

**Observer Framing:**
- OVERWRITE/REFINE before evidence investigation begins
- Must be built from the user report plus project cognition context only
- Do not use code files, test files, logs, or direct repro results here
- Capture an outsider analysis, not a final root-cause verdict
- This section is incomplete until `summary`, `primary_suspected_loop`, `suspected_owning_layer`, `suspected_truth_owner`, `recommended_first_probe`, and at least one `alternative_cause_candidate` are filled

**Transition Memo:**
- OVERWRITE/REFINE after observer framing
- Converts the outsider analysis into the first investigator-facing probe order
- Records which evidence surfaces are now unlocked and what the investigator must carry forward
- This section is incomplete until `first_candidate_to_test`, `why_first`, and at least one `evidence_unlock` entry are filled

**Investigation Contract:**
- OVERWRITE/REFINE once observer framing is available
- Converts observer framing from advisory prose into runtime investigation constraints
- `primary_candidate_id` must map to an entry in `candidate_queue`
- `investigation_mode` tracks whether the session is still in `normal` mode or has escalated into `root_cause`
- `related_risk_targets` records the nearest-neighbor paths that must be reviewed before closeout
- `causal_coverage_state.related_risk_scan_completed` should stay `false` until the nearest-neighbor review is actually complete

**Log Investigation Plan:**
- OVERWRITE/REFINE after map-backed minimum intake or Stage 1B
- Records existing logs to inspect first, expected candidate-separating signals, sufficiency judgment, missing observability, instrumentation targets, and user log request packet
- This section is incomplete until `existing_log_targets`, `candidate_signal_map`, and `log_sufficiency_judgment` are filled
- Do not read logs while creating this plan; log review begins only after the canonical intake package is complete

**Observer Gate:**
- Set `observer_framing_completed: true` only after map-backed minimum intake or Stage 1A (`Causal Map`) plus Stage 1B (`Observer Framing` + `Transition Memo` + `Investigation Contract` + `Log Investigation Plan`) are complete
- The canonical intake completion fields are `causal_map_completed`, `investigation_contract_completed`, `log_investigation_plan_completed`, and derived `observer_framing_completed`
- If `legacy_session_needs_reintake` is true, re-run map-backed intake or Stage 1A/1B before evidence collection resumes
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
- whether a recorded evidence item came from logs, tests, verification commands, traces, or manual observation,
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
