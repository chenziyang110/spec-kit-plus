# Discussion State: [TOPIC]

## Current Command

- active_command: sp-discussion
- state_surface: discussion-state
- status: active | blocked | handoff-ready | completed | abandoned
- slug: [normalized-slug]
- updated_at: [ISO-8601 timestamp]
- closed_at: [ISO-8601 timestamp or none]
- archived_at: [ISO-8601 timestamp or none]

## Phase Mode

- phase_mode: discussion-only
- summary: [Short current-state summary for resume context]

## Session Routing

- current_stage: context-intake | product-framing | context-grounding | question-loop | technical-options | ui-interaction-discussion | handoff-assessment | handoff-draft | handoff-self-review | handoff-user-review | handoff-ready
- current_topic: [Short topic label]
- question_pack_mode: single-question | adaptive-pack | none
- decision_advancement_mode: recommendation-first
- primary_question: [One required boundary, product, trade-off, evidence-conflict, or high-impact question, or none]
- optional_followups: []
- recommendation_required_for_choices: true
- blocker_reason: none
- readiness_note: [why the discussion is or is not ready for explicit handoff]
- ui_discussion_status: not_applicable | offered | accepted | skipped | completed | deferred

## Advisor Contract

- truth_pass_status: not-needed | needed | in-progress | complete | blocked
- verified_project_facts: []
- open_assumptions: []
- evidence_checked: []
- advice_confidence: high | medium | low | blocked | none
- discussion_compass_status: current | stale | missing
- current_decision_frame: [one-sentence decision-level framing or none]
- confirmed_decisions: []
- changed_recommendations: []
- next_discussion_paths: []

## Lightweight Recovery

- latest_event_checkpoint: [discussion-log.md event timestamp or none]
- last_compaction_checkpoint: [ISO-8601 timestamp or none]
- compact_summary_status: current | stale | missing
- ordinary_turn_write_policy: append compact event only
- structured_refresh_policy: semantic-checkpoint-only

## Context Boundary

- context_boundary_status: not-started | needs-user-input | locked | blocked
- current_project_root: [absolute path or none]
- current_project_roles: []
- target_project_root: [absolute path, external target, or none]
- target_project_roles: []
- reference_sources: []
- external_systems: []
- boundary_blockers: []
- path_status: unknown | user-confirmed | target-read-confirmed | blocked
- boundary_confidence: unknown | low | medium | high

## Evidence Navigation

- latest_cognition_intent: discussion | none
- latest_cognition_readiness: ready | review | ambiguous | needs_update | needs_rebuild | blocked | none
- latest_minimal_live_reads: []
- latest_live_evidence: []
- cognition_authority_rule: project cognition navigates; live repository evidence proves
- truth_pass_authority_rule: verify current-project facts with live evidence before technical advice
- unresolved_evidence_conflicts: []

## Session Selection

- incomplete_statuses: active, blocked, handoff-ready
- resume_rule: resume only when exactly one incomplete discussion is available or the user selected a slug
- collision_rule: append date or short numeric suffix when a generated slug already exists
- close_archive_rule: handoff-ready remains resumable; close as completed or abandoned before archiving

## Handoff Assessment

- handoff_assessment_status: not-run | ready-for-specify | continue-discussion
- handoff_assessment_path: handoff-assessment.md | none
- handoff_assessment_decided_at: [ISO-8601 timestamp or none]
- handoff_scope_shape: unified | blocked

## Handoff Review

- handoff_review_status: not-started | draft | self-review-passed | user-confirmed | blocked
- handoff_user_confirmed_at: [ISO-8601 timestamp or none]
- handoff_blocker_reason: none
- handoff_quality_gate: draft | self_review_passed | user_confirmed | blocked

## Allowed Artifact Writes

- discussion-state.md
- discussion-log.md
- requirements.md
- technical-options.md
- project-context.md
- open-questions.md
- handoff-assessment.md only after explicit user request
- handoff-to-specify.md draft after explicit user request and boundary lock; mark handoff-ready only after self-review pass and user confirmation
- handoff-to-specify.json draft after explicit user request and boundary lock; mark handoff-ready only after self-review pass and user confirmation

## Forbidden Actions

- create feature branch
- create feature directory
- write spec.md
- write plan.md
- write tasks.md
- edit source code
- edit tests
- run implementation-oriented fix loops
- automatically invoke sp-specify
- infer handoff readiness without explicit user instruction
- add, recommend, or route to sp-split
- write separate split planning artifacts
- write candidate-specific handoff Markdown or JSON
- write pointer-only handoff-to-specify.md or handoff-to-specify.json
- use current project cognition to prove another project's implementation facts

## Authoritative Files

- discussion-state.md
- discussion-log.md
- requirements.md
- technical-options.md
- project-context.md
- open-questions.md
- handoff-assessment.md when present
- handoff-to-specify.md when draft or user-confirmed, according to handoff_review_status
- handoff-to-specify.json when draft or user-confirmed, according to handoff_review_status

## Senior Consequence Analysis

- consequence_gate_status: not-triggered | triggered | ready | blocked | stood-down
- trigger_reason: none
- stand_down_reason: none
- active_consequence_obligations: []
- latest_consequence_handoff: none
- coverage_gap_count: 0

## Handoff

- handoff_to_specify: none
- handoff_to_specify_json: none
- handoff_goal: none
- quality_gate_status: draft | self_review_passed | user_confirmed | blocked
- handoff_requested_by_user: false
- next_command: none
