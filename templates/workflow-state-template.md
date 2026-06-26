# Workflow State: [FEATURE NAME]

## Current Command

- active_command: [sp-specify | sp-plan | sp-tasks | sp-implement | sp-debug | sp-analyze | sp-deep-research | sp-clarify | sp-constitution | sp-prd | sp-prd-scan | sp-prd-build]
- status: [active | completed | blocked]

## Phase Mode

- phase_mode: [planning-only | design-only | task-generation-only | execution-only | analysis-only | research-only]
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
- source_files_read: [none | discussion source files read | repo context read]
- source_signal_disposition_status: [not-applicable | incomplete | complete]

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

## Embedded Implement Review

- review_gate:
  - mode: [embedded]
  - status: [pending | cleared | repaired | blocked]
  - scope: [pre-implement | join-point-drift | sequential-window]
  - auto_repair_tasks: [true | false]
  - last_reviewed_batch: [batch id or none]
  - latest_review_id: [review id or none]
  - latest_repair_id: [repair id or none]
- review_window_policy:
  - max_completed_tasks_before_review: [5]
  - max_unreviewed_changed_paths: [8]
  - max_unreviewed_validation_failures: [0]
- implementation_review:
  - reviews: [implementation-review/reviews.ndjson]
  - repairs: [implementation-review/repairs.ndjson]
  - snapshots: [implementation-review/snapshots/]
- workflow_state_write_allowlist:
  - review_gate
  - review_window_policy
  - implementation_review
  - next_action
  - blocker_reason
  - blocked_reason
  - next_command
- workflow_state_protected_fields: [all upstream truth, artifact ownership, evidence, transition, gate, and reopen fields outside the review allowlist]

## Handoff Files

- handoff_to_specify: [path or none]
- handoff_to_plan: [path or none]
- handoff_to_tasks: [path or none]
- handoff_to_implement: [path or none]

## Allowed Artifact Writes

- [Artifacts this workflow pass may write, e.g. spec.md]

## Forbidden Actions

- [Actions this workflow pass must not take, e.g. edit source code]

## Authoritative Files

- [Files that are currently treated as the source of truth, e.g. spec.md]

## Next Command

- [`/sp.plan` | `/sp.clarify` | `/sp.deep-research` | other canonical next workflow token]
