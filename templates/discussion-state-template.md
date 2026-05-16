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

- current_stage: session-intake | idea-framing | context-grounding | question-loop | technical-options | requirements-synthesis | handoff-on-request
- current_topic: [Short topic label]
- next_question: [One high-impact question or none]
- blocker_reason: none
- readiness_note: [why the discussion is or is not ready for explicit handoff]

## Session Selection

- incomplete_statuses: active, blocked, handoff-ready
- resume_rule: resume only when exactly one incomplete discussion is available or the user selected a slug
- collision_rule: append date or short numeric suffix when a generated slug already exists

## Allowed Artifact Writes

- discussion-state.md
- discussion-log.md
- requirements.md
- technical-options.md
- project-context.md
- open-questions.md
- handoff-to-specify.md only after explicit user request

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

## Authoritative Files

- discussion-state.md
- discussion-log.md
- requirements.md
- technical-options.md
- project-context.md
- open-questions.md

## Senior Consequence Analysis

- consequence_gate_status: not-triggered | triggered | ready | blocked | stood-down
- trigger_reason: none
- stand_down_reason: none
- active_consequence_obligations: []
- latest_consequence_handoff: none
- coverage_gap_count: 0

## Handoff

- handoff_to_specify: none
- handoff_requested_by_user: false
- next_command: none
