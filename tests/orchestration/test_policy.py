"""Tests for orchestration strategy selection policy."""

from specify_cli.orchestration.models import CapabilitySnapshot
from specify_cli.orchestration.policy import (
    choose_evidence_lane_dispatch,
    choose_subagent_dispatch,
    choose_ui_reference_lane_dispatch,
    classify_batch_execution_policy,
    classify_review_gate_policy,
)


def test_plan_lightweight_safe_routes_to_leader_inline() -> None:
    snapshot = CapabilitySnapshot(integration_key="codex", native_subagents=True)

    decision = choose_subagent_dispatch(
        command_name="plan",
        snapshot=snapshot,
        workload_shape={
            "safe_subagent_lanes": 1,
            "packet_ready": False,
            "lightweight_safe": True,
        },
    )

    assert decision.command_name == "plan"
    assert decision.dispatch_shape == "leader-inline"
    assert decision.reason == "adaptive-light-leader-inline"
    assert decision.execution_surface == "leader-inline"
    assert decision.execution_model == "adaptive"
    assert decision.execution_mode == "light"
    assert decision.workflow_status == "ready"
    assert decision.capability_degraded is False


def test_tasks_standard_native_available_routes_to_parallel_subagents() -> None:
    snapshot = CapabilitySnapshot(integration_key="claude", native_subagents=True)

    decision = choose_subagent_dispatch(
        command_name="tasks",
        snapshot=snapshot,
        workload_shape={
            "safe_subagent_lanes": 2,
            "packet_ready": True,
            "lightweight_safe": False,
        },
    )

    assert decision.command_name == "tasks"
    assert decision.dispatch_shape == "parallel-subagents"
    assert decision.reason == "adaptive-standard-parallel-subagents"
    assert decision.execution_surface == "native-subagents"
    assert decision.execution_model == "adaptive"
    assert decision.execution_mode == "standard"
    assert decision.workflow_status == "ready"


def test_tasks_standard_without_native_subagents_degrades_to_leader_inline() -> None:
    snapshot = CapabilitySnapshot(integration_key="generic", native_subagents=False)

    decision = choose_subagent_dispatch(
        command_name="tasks",
        snapshot=snapshot,
        workload_shape={
            "safe_subagent_lanes": 1,
            "packet_ready": True,
            "lightweight_safe": False,
            "high_risk": False,
        },
    )

    assert decision.dispatch_shape == "leader-inline"
    assert decision.reason == "adaptive-standard-native-unavailable-leader-inline"
    assert decision.execution_surface == "leader-inline"
    assert decision.execution_model == "adaptive"
    assert decision.execution_mode == "standard"
    assert decision.capability_degraded is True


def test_plan_heavy_without_native_subagents_blocks() -> None:
    snapshot = CapabilitySnapshot(integration_key="generic", native_subagents=False)

    decision = choose_subagent_dispatch(
        command_name="plan",
        snapshot=snapshot,
        workload_shape={
            "safe_subagent_lanes": 1,
            "packet_ready": True,
            "touches_schema_or_migration": True,
        },
    )

    assert decision.dispatch_shape == "subagent-blocked"
    assert decision.reason == "adaptive-heavy-subagent-blocked"
    assert decision.execution_surface == "none"
    assert decision.execution_model == "adaptive"
    assert decision.execution_mode == "heavy"
    assert decision.workflow_status == "blocked"
    assert decision.blocked_reason == "heavy or safety-critical plan work requires native subagents"


def test_tasks_heavy_without_native_subagents_uses_task_generation_blocked_reason() -> None:
    snapshot = CapabilitySnapshot(integration_key="generic", native_subagents=False)

    decision = choose_subagent_dispatch(
        command_name="tasks",
        snapshot=snapshot,
        workload_shape={
            "safe_subagent_lanes": 1,
            "packet_ready": True,
            "touches_security_sensitive_surface": True,
        },
    )

    assert decision.execution_model == "adaptive"
    assert decision.execution_mode == "heavy"
    assert decision.workflow_status == "blocked"
    assert decision.dispatch_shape == "subagent-blocked"
    assert decision.execution_surface == "none"
    assert decision.blocked_reason == "heavy or safety-critical task generation requires native subagents"


def test_plan_unpacketized_heavy_native_subagents_blocks() -> None:
    snapshot = CapabilitySnapshot(integration_key="codex", native_subagents=True)

    decision = choose_subagent_dispatch(
        command_name="plan",
        snapshot=snapshot,
        workload_shape={
            "safe_subagent_lanes": 0,
            "packet_ready": False,
            "touches_security_sensitive_surface": True,
        },
    )

    assert decision.dispatch_shape == "subagent-blocked"
    assert decision.workflow_status == "blocked"
    assert decision.blocked_reason == "heavy or safety-critical plan work cannot be packetized safely"


def test_high_risk_classifier_checks_all_present_risk_keys() -> None:
    snapshot = CapabilitySnapshot(integration_key="codex", native_subagents=True)

    decision = choose_subagent_dispatch(
        command_name="plan",
        snapshot=snapshot,
        workload_shape={
            "safe_subagent_lanes": 1,
            "packet_ready": False,
            "high_risk": False,
            "touches_schema": True,
        },
    )

    assert decision.dispatch_shape == "subagent-blocked"
    assert decision.execution_model == "adaptive"
    assert decision.execution_mode == "heavy"
    assert decision.workflow_status == "blocked"
    assert decision.blocked_reason == "heavy or safety-critical plan work cannot be packetized safely"


def test_standard_native_available_blocks_when_no_safe_lanes() -> None:
    snapshot = CapabilitySnapshot(integration_key="codex", native_subagents=True)

    decision = choose_subagent_dispatch(
        command_name="tasks",
        snapshot=snapshot,
        workload_shape={
            "safe_subagent_lanes": 0,
            "packet_ready": True,
            "lightweight_safe": False,
        },
    )

    assert decision.dispatch_shape == "subagent-blocked"
    assert decision.reason == "adaptive-standard-subagent-blocked"
    assert decision.execution_model == "adaptive"
    assert decision.execution_mode == "standard"
    assert decision.workflow_status == "blocked"
    assert decision.blocked_reason == "standard adaptive task generation cannot be packetized safely"


def test_standard_native_available_blocks_when_packet_not_ready() -> None:
    snapshot = CapabilitySnapshot(integration_key="codex", native_subagents=True)

    decision = choose_subagent_dispatch(
        command_name="tasks",
        snapshot=snapshot,
        workload_shape={
            "safe_subagent_lanes": 1,
            "packet_ready": False,
            "lightweight_safe": False,
        },
    )

    assert decision.dispatch_shape == "subagent-blocked"
    assert decision.reason == "adaptive-standard-subagent-blocked"
    assert decision.execution_model == "adaptive"
    assert decision.execution_mode == "standard"
    assert decision.workflow_status == "blocked"
    assert decision.blocked_reason == "standard adaptive task generation cannot be packetized safely"


def test_non_adaptive_ordinary_commands_remain_mandatory_subagent() -> None:
    snapshot = CapabilitySnapshot(integration_key="claude", native_subagents=True)

    for command_name in (
        "specify",
        "implement",
        "debug",
        "quick",
        "map-scan",
        "map-build",
        "map-update",
    ):
        decision = choose_subagent_dispatch(
            command_name=command_name,
            snapshot=snapshot,
            workload_shape={
                "safe_subagent_lanes": 1,
                "packet_ready": True,
                "overlapping_write_sets": False,
            },
        )

        assert decision.dispatch_shape == "one-subagent"
        assert decision.reason == "mandatory-one-subagent"
        assert decision.execution_surface == "native-subagents"
        assert decision.execution_model == "subagent-mandatory"


def test_optional_evidence_lane_defaults_to_leader_inline_when_no_safe_lane() -> None:
    snapshot = CapabilitySnapshot(integration_key="codex", native_subagents=True)

    decision = choose_evidence_lane_dispatch(
        command_name="ask",
        snapshot=snapshot,
        workload_shape={"safe_evidence_lanes": 0},
    )

    assert decision.command_name == "ask"
    assert decision.dispatch_shape == "leader-inline"
    assert decision.reason == "read-only-evidence-leader-inline-no-safe-lane"
    assert decision.execution_surface == "leader-inline"
    assert decision.workflow_status == "ready"
    assert decision.lane_mode == "read-only-evidence"


def test_evidence_lane_routes_to_parallel_subagents_when_contract_ready() -> None:
    snapshot = CapabilitySnapshot(integration_key="codex", native_subagents=True)

    decision = choose_evidence_lane_dispatch(
        command_name="discussion",
        snapshot=snapshot,
        workload_shape={
            "read_only_evidence_lanes": 2,
            "evidence_contract_ready": True,
        },
    )

    assert decision.dispatch_shape == "parallel-subagents"
    assert decision.reason == "read-only-evidence-parallel-subagents"
    assert decision.execution_surface == "native-subagents"
    assert decision.workflow_status == "ready"


def test_required_evidence_lane_blocks_when_native_subagents_unavailable() -> None:
    snapshot = CapabilitySnapshot(integration_key="generic", native_subagents=False)

    decision = choose_evidence_lane_dispatch(
        command_name="discussion",
        snapshot=snapshot,
        workload_shape={
            "safe_evidence_lanes": 1,
            "evidence_contract_ready": True,
            "evidence_lane_required": True,
        },
    )

    assert decision.dispatch_shape == "subagent-blocked"
    assert decision.reason == "read-only-evidence-subagent-blocked"
    assert decision.execution_surface == "none"
    assert decision.workflow_status == "blocked"
    assert decision.blocked_reason == "read-only evidence lanes require native subagents"


def test_optional_evidence_lane_degrades_to_leader_inline_without_native_subagents() -> None:
    snapshot = CapabilitySnapshot(integration_key="generic", native_subagents=False)

    decision = choose_evidence_lane_dispatch(
        command_name="ask",
        snapshot=snapshot,
        workload_shape={
            "safe_evidence_lanes": 1,
            "evidence_contract_ready": True,
        },
    )

    assert decision.dispatch_shape == "leader-inline"
    assert decision.reason == "read-only-evidence-native-unavailable-leader-inline"
    assert decision.execution_surface == "leader-inline"
    assert decision.capability_degraded is True


def test_ui_reference_lane_routes_to_one_subagent_when_contract_ready() -> None:
    snapshot = CapabilitySnapshot(integration_key="codex", native_subagents=True)

    decision = choose_ui_reference_lane_dispatch(
        command_name="specify",
        snapshot=snapshot,
        workload_shape={
            "safe_ui_reference_lanes": 1,
            "ui_reference_contract_ready": True,
            "ui_reference_required": True,
            "fidelity_mode": "approximate",
        },
    )

    assert decision.command_name == "specify"
    assert decision.dispatch_shape == "one-subagent"
    assert decision.reason == "ui-reference-artifact-one-subagent"
    assert decision.execution_surface == "native-subagents"
    assert decision.workflow_status == "ready"
    assert decision.lane_mode == "ui-reference-artifact"
    assert decision.structured_result == "ui_reference_artifacts"


def test_ui_reference_lane_blocks_approximate_when_native_subagents_unavailable() -> None:
    snapshot = CapabilitySnapshot(integration_key="generic", native_subagents=False)

    decision = choose_ui_reference_lane_dispatch(
        command_name="specify",
        snapshot=snapshot,
        workload_shape={
            "safe_ui_reference_lanes": 1,
            "ui_reference_contract_ready": True,
            "ui_reference_required": True,
            "fidelity_mode": "approximate",
        },
    )

    assert decision.dispatch_shape == "subagent-blocked"
    assert decision.reason == "ui-reference-artifact-subagent-blocked"
    assert decision.execution_surface == "none"
    assert decision.workflow_status == "blocked"
    assert decision.blocked_reason == "UI reference artifact lane requires native subagents for approximate fidelity"


def test_ui_reference_lane_allows_inspiration_inline_soft_risk_without_native_subagents() -> None:
    snapshot = CapabilitySnapshot(integration_key="generic", native_subagents=False)

    decision = choose_ui_reference_lane_dispatch(
        command_name="specify",
        snapshot=snapshot,
        workload_shape={
            "safe_ui_reference_lanes": 1,
            "ui_reference_contract_ready": True,
            "ui_reference_required": True,
            "fidelity_mode": "inspiration",
        },
    )

    assert decision.dispatch_shape == "leader-inline"
    assert decision.reason == "ui-reference-artifact-inspiration-inline-soft-risk"
    assert decision.execution_surface == "leader-inline"
    assert decision.workflow_status == "ready"
    assert decision.capability_degraded is True
    assert decision.lane_mode == "ui-reference-artifact"


def test_ui_reference_lane_uses_parallel_subagents_for_multiple_safe_lanes() -> None:
    snapshot = CapabilitySnapshot(integration_key="codex", native_subagents=True)

    decision = choose_ui_reference_lane_dispatch(
        command_name="specify",
        snapshot=snapshot,
        workload_shape={
            "safe_ui_reference_lanes": 3,
            "ui_reference_contract_ready": True,
            "ui_reference_required": True,
            "fidelity_mode": "high",
        },
    )

    assert decision.dispatch_shape == "parallel-subagents"
    assert decision.reason == "ui-reference-artifact-parallel-subagents"
    assert decision.execution_surface == "native-subagents"


def test_lightweight_safe_is_derived_from_risk_keys_when_omitted() -> None:
    snapshot = CapabilitySnapshot(integration_key="codex", native_subagents=True)

    decision = choose_subagent_dispatch(
        command_name="plan",
        snapshot=snapshot,
        workload_shape={
            "safe_subagent_lanes": 1,
            "packet_ready": False,
            "touches_shared_registration_surface": False,
            "cross_project_target": False,
            "reference_fidelity_required": False,
        },
    )

    assert decision.dispatch_shape == "leader-inline"
    assert decision.reason == "adaptive-light-leader-inline"


def test_classify_batch_execution_policy_marks_low_risk_preparation_as_mixed_tolerance() -> None:
    policy = classify_batch_execution_policy(
        workload_shape={
            "parallel_batches": 2,
            "overlapping_write_sets": False,
            "safe_preparation": True,
            "preparation_scope": "scaffolding",
        }
    )

    assert policy.batch_classification == "mixed_tolerance"
    assert policy.safe_preparation_allowed is True
    assert policy.reason == "low_risk_preparation"


def test_classify_batch_execution_policy_keeps_general_parallel_implementation_strict() -> None:
    policy = classify_batch_execution_policy(
        workload_shape={
            "parallel_batches": 2,
            "overlapping_write_sets": False,
            "safe_preparation": False,
        }
    )

    assert policy.batch_classification == "strict"
    assert policy.safe_preparation_allowed is False
    assert policy.reason == "full_success_required"


def test_classify_review_gate_policy_marks_high_risk_shared_surface_batches() -> None:
    policy = classify_review_gate_policy(
        workload_shape={
            "touches_shared_surface": True,
            "review_lane_available": True,
        }
    )

    assert policy.requires_review_gate is True
    assert policy.peer_review_lane_recommended is True
    assert policy.reason == "shared_surface"


def test_classify_review_gate_policy_marks_boundary_batches_without_peer_lane() -> None:
    policy = classify_review_gate_policy(
        workload_shape={
            "touches_protocol_boundary": True,
            "review_lane_available": False,
        }
    )

    assert policy.requires_review_gate is True
    assert policy.peer_review_lane_recommended is False
    assert policy.reason == "boundary_contract"


def test_classify_review_gate_policy_checks_all_schema_aliases() -> None:
    policy = classify_review_gate_policy(
        workload_shape={
            "touches_schema": False,
            "touches_migration": True,
        }
    )

    assert policy.requires_review_gate is True
    assert policy.reason == "schema_change"


def test_classify_review_gate_policy_covers_schema_or_migration_alias() -> None:
    policy = classify_review_gate_policy(
        workload_shape={
            "touches_schema_or_migration": True,
        }
    )

    assert policy.requires_review_gate is True
    assert policy.reason == "schema_change"


def test_classify_review_gate_policy_checks_all_shared_surface_aliases() -> None:
    policy = classify_review_gate_policy(
        workload_shape={
            "touches_shared_registration_surface": False,
            "touches_shared_surface": True,
        }
    )

    assert policy.requires_review_gate is True
    assert policy.reason == "shared_surface"


def test_classify_review_gate_policy_checks_all_boundary_aliases() -> None:
    policy = classify_review_gate_policy(
        workload_shape={
            "touches_protocol_boundary": False,
            "touches_native_bridge": True,
        }
    )

    assert policy.requires_review_gate is True
    assert policy.reason == "boundary_contract"


def test_classify_review_gate_policy_covers_protocol_generated_and_plugin_aliases() -> None:
    policy = classify_review_gate_policy(
        workload_shape={
            "touches_protocol_or_generated_api": False,
            "touches_native_or_plugin_bridge": False,
            "touches_plugin_bridge": True,
        }
    )

    assert policy.requires_review_gate is True
    assert policy.reason == "boundary_contract"


def test_classify_review_gate_policy_marks_security_sensitive_surface() -> None:
    policy = classify_review_gate_policy(
        workload_shape={
            "touches_security_sensitive_surface": True,
        }
    )

    assert policy.requires_review_gate is True
    assert policy.reason == "security_sensitive"


def test_classify_review_gate_policy_marks_general_high_risk() -> None:
    policy = classify_review_gate_policy(
        workload_shape={
            "high_risk": True,
        }
    )

    assert policy.requires_review_gate is True
    assert policy.reason == "general_high_risk"


def test_classify_review_gate_policy_marks_cross_project_targets() -> None:
    policy = classify_review_gate_policy(
        workload_shape={
            "cross_project_target": True,
        }
    )

    assert policy.requires_review_gate is True
    assert policy.reason == "cross_project"


def test_classify_review_gate_policy_marks_reference_fidelity_required() -> None:
    policy = classify_review_gate_policy(
        workload_shape={
            "reference_fidelity_required": True,
        }
    )

    assert policy.requires_review_gate is True
    assert policy.reason == "reference_fidelity"


def test_classify_review_gate_policy_marks_deep_research_handoff_required() -> None:
    policy = classify_review_gate_policy(
        workload_shape={
            "deep_research_handoff_required": True,
        }
    )

    assert policy.requires_review_gate is True
    assert policy.reason == "deep_research_handoff"


def test_classify_review_gate_policy_marks_independent_synthesis_required() -> None:
    policy = classify_review_gate_policy(
        workload_shape={
            "consequence_obligations_require_independent_synthesis": True,
        }
    )

    assert policy.requires_review_gate is True
    assert policy.reason == "independent_synthesis_required"


def test_classify_review_gate_policy_skips_low_risk_batches() -> None:
    policy = classify_review_gate_policy(
        workload_shape={
            "touches_shared_surface": False,
            "touches_schema": False,
            "touches_protocol_boundary": False,
        }
    )

    assert policy.requires_review_gate is False
    assert policy.peer_review_lane_recommended is False
    assert policy.reason == "low_risk_batch"
