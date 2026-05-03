from specify_cli.orchestration import CapabilitySnapshot, describe_delegation_surface
from specify_cli.orchestration.adapters import normalize_command_name, supports_workflow_command


def test_research_alias_normalizes_to_deep_research_for_orchestration_support() -> None:
    assert normalize_command_name("research") == "deep-research"
    assert normalize_command_name("sp-research") == "deep-research"
    assert normalize_command_name("sp.research") == "deep-research"
    assert normalize_command_name("/sp.plan") == "plan"
    assert supports_workflow_command("sp-research") is True


def test_describe_delegation_surface_for_codex_implement_prefers_spawn_agent_contract() -> None:
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
    assert "wait_agent" in descriptor.native_join_hint
    assert "WorkerTaskResult" in descriptor.result_contract_hint
    assert ".specify/teams/state/results/<request-id>.json" in descriptor.result_handoff_hint
    assert descriptor.structured_results_expected is True


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
    assert "evidence payload" in descriptor.result_contract_hint.lower()
    assert ".planning/debug/results/<session-slug>/<lane-id>.json" in descriptor.result_handoff_hint
    assert descriptor.structured_results_expected is True


def test_describe_delegation_surface_for_gemini_explains_no_native_subagent_surface() -> None:
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
    assert "no managed team workflow" in descriptor.managed_team_hint.lower()
    assert ".planning/quick/<id>-<slug>/worker-results/<lane-id>.json" in descriptor.result_handoff_hint
