from specify_cli.orchestration import CapabilitySnapshot, describe_delegation_surface


def test_describe_delegation_surface_for_codex_implement_prefers_spawn_agent_contract() -> None:
    descriptor = describe_delegation_surface(
        command_name="implement",
        snapshot=CapabilitySnapshot(
            integration_key="codex",
            native_multi_agent=True,
            sidecar_runtime_supported=True,
            structured_results=False,
            native_worker_surface="spawn_agent",
            delegation_confidence="high",
        ),
    )

    assert descriptor.intent == "implementation"
    assert descriptor.native_surface == "spawn_agent"
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
            native_multi_agent=True,
            sidecar_runtime_supported=True,
            structured_results=True,
            native_worker_surface="native-cli",
            delegation_confidence="medium",
        ),
    )

    assert descriptor.intent == "evidence"
    assert descriptor.native_surface == "native-cli"
    assert "native delegated worker surface" in descriptor.native_dispatch_hint.lower()
    assert "evidence payload" in descriptor.result_contract_hint.lower()
    assert ".planning/debug/results/<session-slug>/<lane-id>.json" in descriptor.result_handoff_hint
    assert descriptor.structured_results_expected is True


def test_describe_delegation_surface_for_gemini_explains_no_native_surface() -> None:
    descriptor = describe_delegation_surface(
        command_name="quick",
        snapshot=CapabilitySnapshot(
            integration_key="gemini",
            native_multi_agent=False,
            sidecar_runtime_supported=False,
            structured_results=True,
            native_worker_surface="none",
            delegation_confidence="low",
        ),
    )

    assert descriptor.native_surface == "none"
    assert "no native delegated worker surface" in descriptor.native_dispatch_hint.lower()
    assert "no coordinated runtime surface" in descriptor.sidecar_surface_hint.lower()
    assert ".planning/quick/<id>-<slug>/worker-results/<lane-id>.json" in descriptor.result_handoff_hint
