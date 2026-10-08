"""DO and Playbook are pinned Go namespaces, including bootstrap compatibility."""

from pathlib import Path

import pytest

from specify_cli import specify_runtime
from specify_cli.launcher import (
    load_runtime_launcher,
    render_project_launcher_placeholders,
    write_runtime_launcher_config,
)
from specify_cli.workflow_artifact_lint import (
    load_workflow_artifact_registry,
    scan_workflow_artifact_instructions,
)


ROOT = Path(__file__).resolve().parents[1]
DO_CAPABILITIES = (
    "do.start", "do.record", "do.validate", "do.finish", "do.resume", "do.show",
    "playbook.find", "playbook.show", "playbook.update", "playbook.validate",
)


@pytest.mark.parametrize("command", ["do show --active", "playbook find --query build"])
def test_do_commands_bind_to_project_go_runtime(tmp_path, command):
    project = tmp_path / "project with spaces"
    binary = tmp_path / "specify-runtime"
    binary.write_bytes(b"renderer fixture\n")
    write_runtime_launcher_config(project, binary)
    launcher = load_runtime_launcher(project)
    assert launcher is not None
    content = "{{specify-subcmd:specify-runtime " + command + " --format json}}"
    rendered = render_project_launcher_placeholders(project, content)
    assert rendered == f"{launcher.command} {command} --format json"
    assert "uvx" not in rendered
    assert "specify specify-runtime" not in rendered


@pytest.mark.parametrize("missing", DO_CAPABILITIES)
def test_bootstrap_rejects_each_missing_do_capability(missing):
    capabilities = list(specify_runtime.REQUIRED_CAPABILITIES)
    assert missing in capabilities
    handshake = {
        "protocol_version": specify_runtime.EXPECTED_RUNTIME_PROTOCOL,
        "capability_ids": capabilities,
    }
    assert specify_runtime._runtime_supports_required_commands(handshake)
    handshake["capability_ids"] = [cap for cap in capabilities if cap != missing]
    assert not specify_runtime._runtime_supports_required_commands(handshake)


@pytest.mark.parametrize("name", ["install.sh", "install.ps1"])
def test_standalone_installers_reject_old_runtime_without_do(name):
    content = (ROOT / "tools/specify-runtime" / name).read_text(encoding="utf-8")
    for capability in DO_CAPABILITIES:
        assert f'"{capability}"' in content


@pytest.mark.parametrize("command", [
    "specify do start", "specify playbook update", "python -m specify_cli do record",
    "python -m specify_cli playbook show",
])
def test_do_cannot_fall_back_to_python_in_agent_prompts(tmp_path, command):
    prompt = tmp_path / "templates/commands/do.md"
    prompt.parent.mkdir(parents=True)
    prompt.write_text(f"Run `{command}`.\n", encoding="utf-8")
    registry = load_workflow_artifact_registry(ROOT / "templates/workflow-artifact-registry.json")
    report = scan_workflow_artifact_instructions([prompt], registry)
    assert ("legacy_python_runtime", "invoke") in {
        (item.artifact_id, item.operation) for item in report.violations
    }
