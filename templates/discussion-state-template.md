# Discussion State: [TOPIC]

> Derived compatibility view. Canonical authority is `discussion-state.json`
> conforming to `discussion-state-schema.json`; the shared discussion runtime
> renders this Markdown and agents must not update it independently.

## Current Command

- active_command: sp-discussion
- state_surface: discussion-state
- status: active | blocked | handoff-ready | completed | abandoned
- lifecycle_phase: explore | ground | decide | prepare | review | ready | consumed | closed
- slug: [normalized-slug]
- updated_at: [ISO-8601 timestamp]
- closed_at: [ISO-8601 timestamp or none]
- archived_at: [ISO-8601 timestamp or none]

## Phase Mode

- phase_mode: discussion-only
- summary: [Short current-state summary for resume context]

## Session Routing

- current_stage: compatibility projection of lifecycle_phase; UI interaction and blocker state are orthogonal, not additional lifecycle phases
- current_topic: [Short topic label]
- frontstage_reply_contract: unified
- visible_reply_mode: short | standard | complex | readiness-summary | review-summary | blocked
- backstage_state_visibility: hidden | summarized | surfaced
- question_pack_mode: single-question | adaptive-pack | none
- decision_advancement_mode: recommendation-first
- primary_question: [One required boundary, product, trade-off, evidence-conflict, or high-impact decision question; use none only when continuing without waiting for user input]
- optional_followups: []
- recommendation_required_for_choices: true
- blocker_reason: none
- readiness_note: [why the discussion is or is not ready for explicit handoff]
- ui_discussion_status: not_applicable | offered | accepted | skipped | completed | deferred

## DiscussionTurnPacket

- user_goal: [what the human is trying to decide or define]
- current_decision_frame: [current decision boundary]
- confirmed_decisions: []
- context_boundary: {}
- open_questions: []
- current_recommendation: [recommended direction]
- allowed_actions: []
- persistence_mode: frontstage-only | durable-checkpoint | evidence-handoff | lifecycle-transition
- next_gate: [next meaningful decision or validation gate]

## Design Carry-Forward

- experience_commitments: []
- design_system_requirements: []
- design_system_status: [unknown | ready | soft-risk | blocked | not-applicable]
- design_risk_level: [none | low | medium | high]

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

- latest_event_checkpoint: [discussion-log.jsonl event timestamp or none]
- last_compaction_checkpoint: [ISO-8601 timestamp or none]
- compact_summary_status: current | stale | missing
- ordinary_turn_write_policy: deferred-checkpoint
- ordinary_turn_persistence_mode: frontstage-only by default; durable-checkpoint, evidence-handoff, and lifecycle-transition only when their trigger fires
- ordinary_turn_write_gate: suppress local writes until save trigger; do not update persisted counters for every user reply or plain acknowledgement
- structured_refresh_policy: semantic-checkpoint-only
- save_trigger_policy: semantic-checkpoint | user-triggered-checkpoint-or-save | evidence-handoff | compaction-risk | durable-lifecycle-transition
- checkpoint_value_policy: suggest a checkpoint only when semantic recovery value or compaction risk justifies it; do not maintain a hidden turn counter
- checkpoint_continue_policy: user-triggered checkpoint writes one compact JSONL event and typed state update first, refreshes only changed optional artifacts, then continues in the same reply
- pending_context_summary: []
- compaction_preserve_items: []
- hook_persistence_policy: hooks may remind on resume or compaction, but must not create per-user-reply discussion writes

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
- close_archive_rule: handoff-ready remains resumable only until consumed or explicitly dropped; after `sp-specify` consumes the handoff, mark consumed/completed before archiving

## Handoff Assessment

- handoff_assessment_status: not-run | ready-for-handoff | continue-discussion
- handoff_assessment_path: handoff-assessment.md | none
- handoff_assessment_decided_at: [ISO-8601 timestamp or none]
- handoff_scope_shape: unified | blocked

## Handoff Review

- handoff_review_status: not-started | draft | self-review-passed | user-confirmed | blocked
- handoff_user_confirmed_at: [ISO-8601 timestamp or none]
- handoff_blocker_reason: none
- handoff_quality_gate: draft | self_review_passed | user_confirmed | blocked
- handoff_consumption_status: not_consumed | consumed
- consumed_at: [ISO-8601 timestamp or none]
- consumed_by_feature_dir: [FEATURE_DIR that consumed this handoff, or none]

## Allowed Artifact Writes

- discussion-state.json through the shared runtime
- discussion-state.md only as a runtime-rendered compatibility view
- discussion-log.jsonl through compact checkpoint events
- requirements.md
- technical-options.md
- project-context.md
- open-questions.md
- handoff-assessment.md only after explicit user request
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
- write pointer-only handoff-to-specify.json
- use current project cognition to prove another project's implementation facts

## Authoritative Files

- discussion-state.json
- discussion-log.jsonl
- requirements.md
- technical-options.md
- project-context.md
- open-questions.md
- handoff-assessment.md when present
- handoff-to-specify.json as the canonical agent-only handoff contract

## Senior Consequence Analysis

- consequence_gate_status: not-triggered | triggered | ready | blocked | stood-down
- trigger_reason: none
- stand_down_reason: none
- active_consequence_obligations: []
- latest_consequence_handoff: none
- coverage_gap_count: 0

## Handoff

- handoff_contract: none
- handoff_kind: discussion_requirement_contract | legacy_specify_handoff | none
- handoff_goal: none
- consumer_eligibility: sp-specify=blocked; sp-quick=blocked
- recommended_consumer: continue-discussion | sp-specify | sp-quick
- quality_gate_status: draft | self_review_passed | user_confirmed | blocked
- handoff_requested_by_user: false
- next_command: none
