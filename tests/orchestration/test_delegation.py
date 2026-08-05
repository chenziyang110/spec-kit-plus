from specify_cli.orchestration import CapabilitySnapshot, describe_delegation_surface
from specify_cli.orchestration.adapters import (
    normalize_command_name,
    supports_workflow_command,
)


def test_research_alias_normalizes_to_deep_research_for_orchestration_support() -> None:
    assert normalize_command_name("research") == "deep-research"
    assert normalize_command_name("sp-research") == "deep-research"
    assert normalize_command_name("sp.research") == "deep-research"
    assert normalize_command_name("/sp.plan") == "plan"
    assert supports_workflow_command("sp-research") is True


def test_ask_command_is_supported_by_orchestration_adapter() -> None:
    assert normalize_command_name("ask") == "ask"
    assert normalize_command_name("sp-ask") == "ask"
    assert normalize_command_name("/sp.ask") == "ask"
    assert supports_workflow_command("ask") is True
    assert supports_workflow_command("sp-ask") is True
    assert supports_workflow_command("/sp.ask") is True


def test_describe_delegation_surface_for_codex_implement_prefers_spawn_agent_contract() -> (
    None
):
    descriptor = describe_delegation_surface(
        command_name="implement",
        snapshot=CapabilitySnapshot(
            integration_key="codex",
            native_subagents=True,
            managed_team_supported=True,
            structured_results=False,
            native_worker_surface="spawn_agent",
            delegation_confidence="high",
        ),
    )

    assert descriptor.intent == "implementation"
    assert descriptor.native_subagent_surface == "spawn_agent"
    assert "spawn_agent" in descriptor.native_dispatch_hint
    assert "tool discovery" in descriptor.native_discovery_hint.lower()
    assert "subagent-blocked" in descriptor.native_discovery_hint
    assert "close_agent" not in descriptor.native_discovery_hint
    assert "wait_agent" in descriptor.native_join_hint
    assert "close_agent" not in descriptor.native_join_hint
    assert "WorkerTaskResult" in descriptor.result_contract_hint
    assert (
        ".specify/teams/state/results/<request-id>.json"
        in descriptor.result_handoff_hint
    )
    assert "implement result-merge" in descriptor.result_submit_hint
    assert "--result-file" not in descriptor.result_submit_hint
    assert descriptor.structured_results_expected is True


def test_describe_delegation_surface_for_codex_native_lifecycle_has_no_close_step() -> (
    None
):
    descriptor = describe_delegation_surface(
        command_name="plan",
        snapshot=CapabilitySnapshot(
            integration_key="codex",
            native_subagents=True,
            managed_team_supported=True,
            structured_results=True,
            native_worker_surface="spawn_agent",
            delegation_confidence="high",
        ),
    )

    assert "spawn_agent" in descriptor.native_dispatch_hint
    assert "wait_agent" in descriptor.native_join_hint
    assert "close_agent" not in descriptor.native_discovery_hint
    assert "close_agent" not in descriptor.native_dispatch_hint
    assert "close_agent" not in descriptor.native_join_hint


def test_describe_delegation_surface_for_cursor_names_task_lifecycle() -> None:
    descriptor = describe_delegation_surface(
        command_name="implement",
        snapshot=CapabilitySnapshot(
            integration_key="cursor-agent",
            native_subagents=True,
            managed_team_supported=True,
            structured_results=True,
            native_worker_surface="cursor-task",
            delegation_confidence="medium",
        ),
    )

    assert descriptor.intent == "implementation"
    assert descriptor.native_subagent_surface == "cursor-task"
    assert "`Task`" in descriptor.native_discovery_hint
    assert "`description`" in descriptor.native_discovery_hint
    assert "`prompt`" in descriptor.native_discovery_hint
    assert "`subagent_type`" in descriptor.native_discovery_hint
    assert "`run_in_background`" in descriptor.native_discovery_hint
    assert "Task(" in descriptor.native_dispatch_hint
    assert "`generalPurpose`" in descriptor.native_dispatch_hint
    assert "`explore`" in descriptor.native_dispatch_hint
    assert "terminal `Task` result" in descriptor.native_join_hint
    assert "background completion" in descriptor.native_join_hint
    assert "`agent_id`" in descriptor.native_join_hint
    assert "`resume`" in descriptor.native_join_hint
    assert "follow-up" in descriptor.native_join_hint
    assert "close" not in descriptor.native_join_hint.lower()
    assert "spawn_agent" not in descriptor.native_dispatch_hint
    assert "wait_agent" not in descriptor.native_join_hint
    assert descriptor.result_handoff_hint == "FEATURE_DIR/worker-results/<task-id>.json"
    assert "implement result-merge" in descriptor.result_submit_hint
    assert "--result-json" in descriptor.result_submit_hint
    assert "sp-teams" not in descriptor.result_submit_hint
    assert "--result-file" not in descriptor.result_submit_hint


def test_describe_delegation_surface_for_claude_debug_uses_evidence_contract() -> None:
    descriptor = describe_delegation_surface(
        command_name="debug",
        snapshot=CapabilitySnapshot(
            integration_key="claude",
            native_subagents=True,
            managed_team_supported=True,
            structured_results=True,
            native_worker_surface="native-cli",
            delegation_confidence="medium",
        ),
    )

    assert descriptor.intent == "evidence"
    assert descriptor.native_subagent_surface == "native-cli"
    assert "native subagent support" in descriptor.native_dispatch_hint.lower()
    assert "active tool surface" in descriptor.native_discovery_hint.lower()
    assert "subagent-blocked" in descriptor.native_discovery_hint
    assert (
        "no managed-team or leader-inline fallback"
        in descriptor.managed_team_hint.lower()
    )
    assert "execution_surface: none" in descriptor.managed_team_hint.lower()
    assert "evidence payload" in descriptor.result_contract_hint.lower()
    assert (
        ".planning/debug/results/<session-slug>/<lane-id>.json"
        in descriptor.result_handoff_hint
    )
    assert "result submit --command debug" in descriptor.result_submit_hint
    assert descriptor.structured_results_expected is True


def test_describe_delegation_surface_for_review_exposes_three_wave_contract() -> None:
    descriptor = describe_delegation_surface(
        command_name="review",
        snapshot=CapabilitySnapshot(
            integration_key="codex",
            native_subagents=True,
            managed_team_supported=True,
            structured_results=True,
            native_worker_surface="spawn_agent",
            delegation_confidence="high",
        ),
    )

    assert descriptor.intent == "hybrid"
    assert "read-only review" in descriptor.result_contract_hint.lower()
    assert "fix" in descriptor.result_contract_hint.lower()
    assert "independent revalidation" in descriptor.result_contract_hint.lower()
    assert "leader" in descriptor.native_join_hint.lower()
    assert "review-results/<lane-id>.json" in descriptor.result_handoff_hint
    assert "result submit --command review" in descriptor.result_submit_hint


def test_describe_delegation_surface_for_gemini_explains_no_native_subagent_surface() -> (
    None
):
    descriptor = describe_delegation_surface(
        command_name="quick",
        snapshot=CapabilitySnapshot(
            integration_key="gemini",
            native_subagents=False,
            managed_team_supported=False,
            structured_results=True,
            native_worker_surface="none",
            delegation_confidence="low",
        ),
    )

    assert descriptor.native_subagent_surface == "none"
    assert "no subagent dispatch path" in descriptor.native_dispatch_hint.lower()
    assert (
        "no known native subagent surface" in descriptor.native_discovery_hint.lower()
    )
    assert "no managed team workflow" in descriptor.managed_team_hint.lower()
    assert (
        ".planning/quick/<id>-<slug>/worker-results/<lane-id>.json"
        in descriptor.result_handoff_hint
    )
    assert "result submit --command quick" in descriptor.result_submit_hint


def test_describe_delegation_surface_for_gemini_native_cli_names_agent_syntax() -> None:
    descriptor = describe_delegation_surface(
        command_name="map-scan",
        snapshot=CapabilitySnapshot(
            integration_key="gemini",
            native_subagents=True,
            managed_team_supported=False,
            structured_results=True,
            native_worker_surface="native-cli",
            delegation_confidence="medium",
        ),
    )

    assert descriptor.intent == "evidence"
    assert "@generalist" in descriptor.native_dispatch_hint
    assert "@agent" in descriptor.native_discovery_hint
    assert "subagent-blocked" in descriptor.native_discovery_hint
