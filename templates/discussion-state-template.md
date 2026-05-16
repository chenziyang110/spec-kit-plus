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

- current_stage: session-intake | idea-framing | context-grounding | question-loop | technical-options | requirements-synthesis | handoff-assessment | split-mode | candidate-selection | handoff-on-request
- current_topic: [Short topic label]
- next_question: [One high-impact question or none]
- blocker_reason: none
- readiness_note: [why the discussion is or is not ready for explicit handoff]

## Session Selection

- incomplete_statuses: active, blocked, handoff-ready
- resume_rule: resume only when exactly one incomplete discussion is available or the user selected a slug
- collision_rule: append date or short numeric suffix when a generated slug already exists

## Handoff Assessment

- handoff_assessment_status: not-run | ready-for-specify | split-required | continue-discussion
- handoff_assessment_path: handoff-assessment.md | none
- handoff_assessment_decided_at: [ISO-8601 timestamp or none]

## Split Plan

- split_plan_status: none | active | partially-handed-off | completed | blocked
- split_plan_path: split-plan.md | none
- active_candidate: CAND-xxx | none
- next_recommended_candidate: CAND-xxx | none
- backlog_completion_rule: discussion remains incomplete until every candidate is completed, deferred, or explicitly abandoned

## Allowed Artifact Writes

- discussion-state.md
- discussion-log.md
- requirements.md
- technical-options.md
- project-context.md
- open-questions.md
- handoff-to-specify.md only after explicit user request and bounded handoff selection
- handoff-assessment.md only after explicit user request
- split-plan.md only when handoff assessment returns split-required
- handoffs/*.md only after candidate selection
- handoffs/*.json only after candidate selection
- handoff-to-specify.json only after explicit user request and bounded handoff selection

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
- mark discussion completed while split-plan.md has unfinished candidates
- write pointer-only handoff-to-specify.md or handoff-to-specify.json

## Authoritative Files

- discussion-state.md
- discussion-log.md
- requirements.md
- technical-options.md
- project-context.md
- open-questions.md
- handoff-assessment.md when present
- split-plan.md when present
- handoffs/CAND-xxx-handoff-to-specify.md when present
- handoffs/CAND-xxx-handoff-to-specify.json when present

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
- active_candidate_handoff: none
- active_candidate_handoff_json: none
- handoff_requested_by_user: false
- next_command: none
