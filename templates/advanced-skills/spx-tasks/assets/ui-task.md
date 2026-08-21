## {{task_id}}: {{ui_outcome}}

### Scope Boundaries

| Field | Value |
| --- | --- |
| write_scope | [{{write_paths}}] |
| read_scope | [.specify/design/changes/{{design_change_id}}/DESIGN.md, .specify/design/changes/{{design_change_id}}/design-contract.json, {{feature_dir}}/ui-brief.md] |

### UI Implementation Contract

| Field | Value |
| --- | --- |
| design_change_id | {{design_change_id}} |
| design_change_ref | .specify/design/changes/{{design_change_id}}/DESIGN.md |
| design_change_sha256 | {{registered_design_change_sha256}} |
| design_contract_ref | .specify/design/changes/{{design_change_id}}/design-contract.json |
| ui_work_type | {{ui_work_type}} |
| surface_type | {{surface_type}} |
| platforms | [{{platforms}}] |
| style_authority | {{exact_mode_scope_sources_protected_surfaces_allowed_delta_and_authorization}} |
| subject | {{subject}} |
| audience | {{audience}} |
| single_job | {{single_job}} |
| visual_thesis | {{visual_thesis}} |
| content_thesis | {{content_thesis}} |
| interaction_thesis | {{interaction_thesis}} |
| signature_element | {{signature_element}} |
| approved_visual_ref | {{approved_visual_ref}} |
| approved_preview_sha256 | {{approved_preview_sha256_or_empty_for_live_pattern}} |
| approved_manifest_sha256 | {{approved_manifest_sha256_or_empty_for_live_pattern}} |
| approved_handoff_ref | {{approved_handoff_ref_or_empty_for_live_pattern}} |
| approved_handoff_sha256 | {{approved_handoff_sha256_or_empty_for_live_pattern}} |
| design_decision_ids | [{{task_applicable_design_decision_ids}}] |
| handoff_contract_ids | [{{task_applicable_handoff_contract_ids_or_empty_for_live_pattern}}] |
| design_sources | [.specify/design/changes/{{design_change_id}}/DESIGN.md, .specify/design/changes/{{design_change_id}}/design-contract.json, {{approved_visual_ref}}, {{feature_dir}}/ui-brief.md] |
| reference_notes | {{reference_notes_or_none}} |
| visual_target | {{visual_target_or_none}} |
| reference_intents | [{{task_reference_ref_and_intent}}] |
| real_content_plan | [{{task_content_source_and_states}}] |
| image_plan | [{{task_image_ref_role_and_behavior_or_none}}] |
| surface_catalog | {{exact_selected_surface_rows_with_source_specimen_component_and_decision_refs}} |
| scenario_matrix | {{exact_selected_bounded_risk_scenarios_with_surface_contract_refs_including_editing_ids_interaction_script_start_state_ordered_steps_and_selected_data_state_branches_for_success_failure_timeout_cancel_retry_duplicate_out_of_order_plus_focus_announcement_completion_recovery}} |
| interaction_matrix | [{{task_interaction_surface_input_trigger_event_sequence_immediate_feedback_focus_repeat_cancellation_pending_rows}}] |
| editing_matrix | [{{task_editing_input_methods_composition_paste_autofill_selection_caret_formatting_validation_dirty_persistence_undo_redo_conflict_read_only_disabled_and_submission_rows}}] |
| data_state_matrix | [{{task_state_data_condition_expectation_rows}}] |
| accessibility_matrix | {{exact_selected_accessibility_rows}} |
| navigation_matrix | {{exact_selected_navigation_rows}} |
| content_matrix | {{exact_selected_content_rows}} |
| color_modes | [{{task_applicable_color_modes}}] |
| component_contracts | {{exact_selected_handoff_component_rows_including_ids_with_required_states_interaction_modes_data_scenarios_variants_content_constraints_semantic_token_refs_governance_iconography}} |
| responsive_matrix | {{exact_selected_handoff_responsive_rows_including_state_adaptation_stretch_overflow_and_ids}} |
| motion_contract | {{purpose_transitions_duration_easing_interrupt_reduced_motion_and_feedback_timing}} |
| usability_validation | {{risk_methods_critical_tasks_success_criteria_human_review_required_and_smoothness_acceptance_ids}} |
| visual_acceptance_matrix | {{exact_selected_handoff_visual_acceptance_rows_including_ids}} |
| comparison_tolerance | {{exact_structured_comparison_tolerance_object}} |
| accepted_deviations | {{exact_selected_handoff_deviation_rows_including_ids_or_empty}} |
| fidelity_level | {{approximate_or_high_or_inspiration}} |
| must_preserve | [{{task_specific_constraints}}, {{motion_and_reduced_motion_constraints}}] |
| may_adapt | [{{allowed_choices}}] |
| must_not | [{{forbidden_drift}}] |
| required_states | [{{affected_states}}] |
| required_evidence | [structure_snapshot, visual_capture, runtime_diagnostics, visual_comparison_or_human_review] |

### Acceptance

- Behavior:
- Visual and interaction acceptance:
- Real-entrypoint verification:
- Stop and reopen condition:

Exercise risk-based or pairwise combinations, never an unbounded Cartesian
product. Automated tests and screenshots cannot close required target-user
human review.
