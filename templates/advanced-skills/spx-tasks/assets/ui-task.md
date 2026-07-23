## {{task_id}}: {{ui_outcome}}

### Scope Boundaries

| Field | Value |
| --- | --- |
| write_scope | [{{write_paths}}] |
| read_scope | [DESIGN.md, {{feature_dir}}/ui-brief.md] |

### UI Implementation Contract

| Field | Value |
| --- | --- |
| ui_work_type | {{ui_work_type}} |
| surface_type | {{surface_type}} |
| platforms | [{{platforms}}] |
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
| design_decision_ids | [{{task_applicable_design_decision_ids}}] |
| design_sources | [DESIGN.md, {{approved_visual_ref}}, {{feature_dir}}/ui-brief.md] |
| reference_notes | {{reference_notes_or_none}} |
| visual_target | {{visual_target_or_none}} |
| reference_intents | [{{task_reference_ref_and_intent}}] |
| real_content_plan | [{{task_content_source_and_states}}] |
| image_plan | [{{task_image_ref_role_and_behavior_or_none}}] |
| color_modes | [{{task_applicable_color_modes}}] |
| component_contracts | [{{component_anatomy_states_and_decision_ids}}] |
| responsive_matrix | [{{viewport_and_adaptation_rows}}] |
| motion_contract | [{{purpose_and_reduced_motion_equivalent}}] |
| visual_acceptance_matrix | [{{viewport_state_and_evidence_rows}}] |
| comparison_tolerance | {{comparison_tolerance}} |
| accepted_deviations | [{{approved_deviations_or_none}}] |
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
