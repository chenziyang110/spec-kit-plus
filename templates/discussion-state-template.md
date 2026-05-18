# Discussion State: [TOPIC]

## Current Command

- active_command: sp-discussion
- state_surface: discussion-state
- status: active | blocked | handoff-ready | completed | abandoned
- slug: [normalized-slug]
- updated_at: [ISO-8601 timestamp]

## Phase Mode

- phase_mode: discussion-only
- summary: [Short current-state summary for resume context]

## Session Routing

- current_stage: context-intake | product-framing | context-grounding | question-loop | technical-options | handoff-assessment | handoff-draft | handoff-self-review | handoff-user-review | handoff-ready
- current_topic: [Short topic label]
- next_question: [One boundary or high-impact question, or none]
- blocker_reason: none
- readiness_note: [why the discussion is or is not ready for explicit handoff]

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

## Session Selection

- incomplete_statuses: active, blocked, handoff-ready
- resume_rule: resume only when exactly one incomplete discussion is available or the user selected a slug
- collision_rule: append date or short numeric suffix when a generated slug already exists

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
- handoff-to-specify.md only after explicit user request, boundary lock, self-review pass, and user confirmation
- handoff-to-specify.json only after explicit user request, boundary lock, self-review pass, and user confirmation

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
- handoff-to-specify.md when user-confirmed
- handoff-to-specify.json when user-confirmed

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
