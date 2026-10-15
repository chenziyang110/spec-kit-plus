"""Check the worker handoff where agents actually consume installed profiles."""

from pathlib import Path

import pytest

from specify_cli.integrations import get_integration
from specify_cli.integrations.manifest import IntegrationManifest


@pytest.mark.parametrize("integration_key", ["codex", "claude"])
@pytest.mark.parametrize("profile", ["classic", "advanced"])
def test_installed_worker_and_e2e_contracts_keep_versioned_runtime_handoff(
    tmp_path: Path, integration_key: str, profile: str,
):
    integration = get_integration(integration_key)
    project = tmp_path / integration_key / profile
    manifest = IntegrationManifest(integration_key, project)
    integration.setup(project, manifest, parsed_options={"workflow_profile": profile}, script_type="ps")
    skills = integration.skills_dest(project)
    if profile == "classic":
        contract = skills / "sp-implement/references/subagent-worker-contract.md"
        packet = skills / "sp-tasks/references/task-packet-schema.md"
        e2e = skills / "sp-e2e/SKILL.md"
        assert "cognition_delta_contract" in packet.read_text(encoding="utf-8")
    else:
        contract = skills / "spx-implement/references/worker-contract.md"
        e2e = skills / "spx-e2e/SKILL.md"
        quick = (skills / "spx-quick/references/worker-contract.md").read_text(encoding="utf-8")
        assert "cognition.worker-delta.v1" in quick
        assert "cognition_result_binding" in quick
        assert not (skills / "spec-kit-project-cognition-gate").exists()
    text = contract.read_text(encoding="utf-8")
    for field in ("spec-kit-cognition-delta-v1", "cognition_delta_contract", "submission_history", "cognition_result_binding", "cognition.worker-delta.v1"):
        assert field in text
    assert "last-writer" in text or "never overwritten with the last worker summary" in text
    assert "{{specify-subcmd:" not in text
    e2e_text = e2e.read_text(encoding="utf-8")
    assert "cognition.worker-delta.v1" in e2e_text
    assert "spec-kit-cognition-delta-v1" in e2e_text
    assert "passing prerequisite" in e2e_text or "nonpassing" in e2e_text
    assert "{{specify-subcmd:" not in e2e_text
