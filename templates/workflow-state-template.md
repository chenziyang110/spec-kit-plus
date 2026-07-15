# Workflow State: [FEATURE NAME]

## Current Command

- active_command: [sp-specify | sp-plan | sp-tasks | sp-implement | sp-accept | sp-debug | sp-analyze | sp-deep-research | sp-clarify | sp-constitution | sp-prd | sp-prd-scan | sp-prd-build]
- status: [active | completed | blocked]

## Phase Mode

- phase_mode: [planning-only | design-only | task-generation-only | execution-only | acceptance-only | analysis-only | research-only]
- summary: [Short current-state summary for resume and hook context]

## Stage State

- current_stage: [context-intake | clarification | approach-comparison | section-approval | artifact-writing | artifact-review | user-review | plan-design | task-generation | analysis | implementation | research]
- current_domain: [scope | acceptance | integration | compatibility | security | data-shape | external-dependency | none]
- next_action: [Smallest next workflow action to take]
- blocker_reason: [None | Why progress is blocked]
- approach_comparison_status: [not-needed | pending | awaiting-user-confirmation | selected | auto-accepted-recommended]
- section_approval_status: [not-needed | pending | awaiting-user-confirmation | approved | auto-approved-recommended]
- final_handoff_decision: [/sp.plan | /sp.clarify | /sp.deep-research | undecided]

## Review State

- last_user_reviewed_artifact_state: [not-requested | requested | changes-requested | approved]
- canonical_contract_ref: [handoff-to-specify.json | spec-contract.json | plan-contract.json | task-index.json | none]
- canonical_contract_revision: [revision or none]
- semantic_delta: [none | compact changed decision ids]

## Semantic Audit State

- semantic_audit_status: [not-needed | input-draft | audit-recorded | claim-candidate | claim-ready | blocked]
- semantic_audit_input_path: [<WORKFLOW_STATE_DIR>/semantic-audit-input.json | none]
- semantic_audit_output_path: [<WORKFLOW_STATE_DIR>/semantic-audit-output.json | none]
- semantic_audit_resume_status: [fresh | missing | stale | needs-rerun]
- semantic_audit_resume_validation: [not-run | fresh | missing-file | route-changed | active-claim-changed | claim-ref-mismatch | verification-ref-mismatch | needs-rerun]
- semantic_audit_route_fingerprint: [stable fingerprint of selected_candidate_ids plus active_claim_type | none]
- semantic_audit_generated_resume_smoke: [not-run | passed | failed | not-applicable]
- semantic_audit_stale_reasons: [none | missing-file | route-changed | active-claim-changed | claim-ref-mismatch | verification-ref-mismatch]
- active_claim_type: [none | root_cause_claim | fixed_claim | completed_claim | release_safe]
- selected_candidate_ids: [none | selected candidate ids from route_decision]
- claim_readiness_status: [not-evaluated | claim_blocked | claim_candidate | claim_ready]
- claim_authorization_refs: [none | workflow authorization refs recorded in workflow_authorization or claim_authorizations]
- claim_verification_refs: [none | verification evidence refs recorded in claim_readiness.claim_verification_refs]

## Unknown Handling

- hard_unknown_count: [0]
- soft_unknown_count: [0]
- next_unknown_to_resolve: [field or none]
- design-system carry-forward: [status and risk fields below]
- design_system_status: [not-applicable | ready | soft-risk | blocked]
- design_risk_level: [none | low | medium | high]

## UI Reference Processing

- ui_reference_processing_status: [not-applicable | subagent-dispatched | completed | blocked | inline-fallback-approved]
- ui_reference_lane_mode: [none | ui-reference-artifact]
- ui_fidelity_mode: [none | approximate | high | inspiration]
- ui_reference_notes: [path or none]
- ui_brief: [path or none]
- ui_target: [path or none]
- ui_reference_ownership: [user-owned | project-owned | third-party | unknown | mixed | none]
- visual_verification_requirement: [none | agent-visual-comparison | visual-comparison-or-human-review | pending-human-review]
- required_evidence: [none | reference source evidence, fidelity criteria, verification entry points, difference inventory, accepted deviations]

## Reopen Contract

- reopen_source: [none | specify | plan | tasks | implement]
- reopen_target: [none | specify | plan | tasks]
- reopen_reason: [why a prior artifact must be reopened]

## Analyze Gate

- gate_status: [not-run | cleared | blocked]
- gate_cycle: [0]
- highest_invalid_stage: [none | clarify | deep-research | plan | tasks | execution-only]
- blocker_bundle:
  - [finding-id | invalid-stage | open | attribution | compact summary | remediation requirement]
- blocker_attribution_values: [none | missed_by_previous_analyze | introduced_by_remediation | upstream_artifact_changed | detector_scope_changed]
- artifact_fingerprint_basis:
  - spec.md: [summary or hash when available]
  - context.md: [summary or hash when available]
  - plan.md: [summary or hash when available]
  - tasks.md: [summary or hash when available]

## Learning Signals

- route_reason: none
- blocked_reason: none

## Learning Triggers

<!-- Add one bullet per reusable signal. Use `kind: compact evidence`, where kind is user_correction, repeated_attempt, route_change, blocker_recovery, false_lead, decisive_signal, hidden_dependency, validation_gap, tooling_trap, state_loss, cognition_gap, reusable_constraint, or near_miss. Leave this section empty when no signal exists. -->

## False Starts

<!-- Add rejected routes, hypotheses, or implementation paths. Leave empty when none exist. -->

## Hidden Dependencies

<!-- Add dependencies discovered during this workflow. Leave empty when none exist. -->

## Reusable Constraints

<!-- Add stable constraints that later workflows must honor. Leave empty when none exist. -->

## Embedded Implement Review

- current_task_id: [task id or none]
- current_task_lifecycle_ref: [task lifecycle path or none]
- review_status: [not-triggered | pending | cleared | repaired | blocked]
- review_trigger: [none | repository-drift | parallel-join | write-scope-drift | validation-failure | worker-concern | obligation-conflict | real-entrypoint-gap | review-window]
- latest_review_or_repair_ref: [event path or none; write only when multiple tasks are affected]
- workflow_state_write_allowlist:
  - current_task_id
  - current_task_lifecycle_ref
  - review_status
  - review_trigger
  - latest_review_or_repair_ref
  - next_action
  - blocker_reason
  - blocked_reason
  - next_command
- workflow_state_protected_fields: [all upstream truth, artifact ownership, evidence, transition, gate, and reopen fields outside the review allowlist]

## Canonical Phase Contract

- contract_ref: [handoff-to-specify.json | spec-contract.json | plan-contract.json | task-index.json | none]
- contract_revision: [revision or none]
- transition_status: [ready | blocked | complete | none]

## Allowed Artifact Writes

- [Artifacts this workflow pass may write, e.g. spec.md]

## Forbidden Actions

- [Actions this workflow pass must not take, e.g. edit source code]

## Authoritative Files

- [Files that are currently treated as the source of truth, e.g. spec.md]

## Next Command

- [`/sp.plan` | `/sp.clarify` | `/sp.deep-research` | other canonical next workflow token]
