from specify_cli.orchestration.adapters import MultiAgentAdapter
from specify_cli.orchestration.models import CapabilitySnapshot
from specify_cli.integrations.claude import ClaudeMultiAgentAdapter
from specify_cli.integrations.codex import CodexMultiAgentAdapter
from specify_cli.integrations.copilot import CopilotMultiAgentAdapter
from specify_cli.integrations.gemini import GeminiMultiAgentAdapter


def test_multi_agent_adapter_protocol_shape():
    assert isinstance(ClaudeMultiAgentAdapter(), MultiAgentAdapter)
    assert isinstance(CodexMultiAgentAdapter(), MultiAgentAdapter)
    assert isinstance(GeminiMultiAgentAdapter(), MultiAgentAdapter)
    assert isinstance(CopilotMultiAgentAdapter(), MultiAgentAdapter)


def test_claude_adapter_capability_snapshot():
    adapter = ClaudeMultiAgentAdapter()
    snapshot = adapter.detect_capabilities()

    assert isinstance(snapshot, CapabilitySnapshot)
    assert snapshot.integration_key == "claude"
    assert snapshot.native_multi_agent is True


def test_codex_adapter_capability_snapshot():
    adapter = CodexMultiAgentAdapter()
    snapshot = adapter.detect_capabilities()

    assert isinstance(snapshot, CapabilitySnapshot)
    assert snapshot.integration_key == "codex"
    assert snapshot.native_multi_agent is True
    assert snapshot.sidecar_runtime_supported is True


def test_gemini_adapter_capability_snapshot():
    snapshot = GeminiMultiAgentAdapter().detect_capabilities()

    assert snapshot.integration_key == "gemini"
    assert snapshot.native_multi_agent is True
    assert snapshot.sidecar_runtime_supported is True


def test_copilot_adapter_capability_snapshot():
    snapshot = CopilotMultiAgentAdapter().detect_capabilities()

    assert snapshot.integration_key == "copilot"
    assert snapshot.native_multi_agent is False
    assert snapshot.sidecar_runtime_supported is True
    assert snapshot.durable_coordination is False


def test_adapters_support_known_commands_and_reject_unknown_commands():
    for adapter in [ClaudeMultiAgentAdapter(), CodexMultiAgentAdapter(), GeminiMultiAgentAdapter()]:
        assert adapter.supports_command("implement") is True
        assert adapter.supports_command("sp-implement") is True
        assert adapter.supports_command("/plan") is True
        assert adapter.supports_command("definitely-not-a-command") is False

    copilot = CopilotMultiAgentAdapter()
    assert copilot.supports_command("implement") is True
    assert copilot.supports_command("sp-implement") is True
    assert copilot.supports_command("plan") is True
    assert copilot.supports_command("/plan") is True
    assert copilot.supports_command("definitely-not-a-command") is False
