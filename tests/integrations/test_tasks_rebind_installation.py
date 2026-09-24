"""Keep the guarded recovery route reachable in installed Windows profiles."""

import re

import pytest

from specify_cli.integrations import get_integration
from specify_cli.integrations.manifest import IntegrationManifest


@pytest.mark.parametrize("integration_key", ["codex", "cursor-agent"])
@pytest.mark.parametrize("workflow_profile", ["classic", "advanced"])
def test_tasks_rebind_contract_survives_profile_installation(
    tmp_path, integration_key, workflow_profile
):
    integration = get_integration(integration_key)
    manifest = IntegrationManifest(integration_key, tmp_path)
    integration.setup(
        tmp_path,
        manifest,
        parsed_options={"workflow_profile": workflow_profile},
        script_type="ps",
    )
    prefix = "spx" if workflow_profile == "advanced" else "sp"
    skill_dir = integration.skills_dest(tmp_path) / f"{prefix}-tasks"
    entry = skill_dir / "SKILL.md"
    recovery = skill_dir / "references" / "rebind.md"
    entry_text = entry.read_text(encoding="utf-8")
    recovery_text = recovery.read_text(encoding="utf-8")
    normalized = re.sub(r"\s+", " ", recovery_text)

    assert "references/rebind.md" in entry_text
    for required in (
        "tasks.rebind",
        "tasks rebind",
        "--expected-task-index-sha256",
        "--expected-workflow-revision",
        "--expected-test-design-handoff-sha256",
        "tasks-rebind-updates-input",
        "accepted/deferred",
        "all-and-only",
        "history_sha256",
        "workflow complete-stage",
    ):
        assert required in normalized, required
    for text in (entry_text, recovery_text):
        assert "{{specify-subcmd:" not in text
        assert "{{spec-kit-include:" not in text
        assert "{{invoke:" not in text
    assert entry.relative_to(tmp_path).as_posix() in manifest.files
    assert recovery.relative_to(tmp_path).as_posix() in manifest.files
    assert manifest.check_modified() == []
