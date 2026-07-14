## {{task_id}}: {{ui_outcome}}

### Scope Boundaries

| Field | Value |
| --- | --- |
| write_scope | [{{write_paths}}] |
| read_scope | [DESIGN.md, {{feature_dir}}/ui-brief.md] |
| ui_fidelity_level | [{{none_or_approximate_or_high}}] |
| design_inputs | [DESIGN.md, {{feature_dir}}/ui-brief.md] |
| ui_required_evidence | [{{real_entry_screenshots_or_output}}, visual_comparison_or_human_review] |

### UI Implementation Contract

| Field | Value |
| --- | --- |
| design_sources | [DESIGN.md, {{feature_dir}}/ui-brief.md] |
| reference_notes | {{reference_notes_or_none}} |
| visual_target | {{visual_target_or_none}} |
| ui_fidelity_mode | {{none_or_approximate_or_high_or_inspiration}} |
| must_preserve | [{{task_specific_constraints}}] |
| may_adapt | [{{allowed_choices}}] |
| must_not | [{{forbidden_drift}}] |
| required_states | [{{affected_states}}] |
| required_evidence | [{{viewport_state_captures}}, {{interaction_checks}}] |

### Acceptance

- Behavior:
- Visual and interaction acceptance:
- Real-entrypoint verification:
- Stop and reopen condition:
