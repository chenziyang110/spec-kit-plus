"""Exercise the real skill installer and repair owner, not a substitute renderer."""

import re

import pytest

from specify_cli.integrations import get_integration
from specify_cli.integrations.manifest import IntegrationManifest


HOST_SHELLS = [
    pytest.param(host, shell, id=f"{host}-{shell}")
    for host in ("codex", "cursor-agent")
    for shell in ("sh", "ps")
]


def normalized(path):
    return re.sub(r"\s+", " ", path.read_text(encoding="utf-8").lower())


@pytest.mark.parametrize(("integration_key", "script_type"), HOST_SHELLS)
def test_advanced_quick_policy_survives_install(tmp_path, integration_key, script_type):
    integration = get_integration(integration_key)
    manifest = IntegrationManifest(integration_key, tmp_path)
    integration.setup(
        tmp_path, manifest,
        parsed_options={"workflow_profile": "advanced"}, script_type=script_type,
    )
    skills = integration.skills_dest(tmp_path)
    entry = skills / "spx-quick" / "SKILL.md"
    reference = entry.parent / "references" / "task-contract.md"
    skill, policy = normalized(entry), normalized(reference)

    assert "references/task-contract.md" in skill
    assert "--leader-direct" in skill
    assert "quick-item-dispatch-v1" in skill
    for anchor in (
        "quick-execution-compact-v1", "standalone_boolean", "response_presentation_only",
        "requires_full_intake", "decision_digest_not_file_hash", "omitted_fields",
        "quick.item-start,quick.allow-inline,quick.item-accept,quick.item-status",
        "compact output never authorizes leader-direct",
        "unknown response or ambiguous mutation outcome",
        "never reuse those merely because the digest matches",
        "do not fetch a full pulse after every compact response",
    ):
        assert anchor in policy, anchor
    for text in (skill, policy):
        assert "{{specify-subcmd:" not in text
        assert "{{spec-kit-include:" not in text
    for path in (entry, reference):
        assert path.relative_to(tmp_path).as_posix() in manifest.files
    assert not (skills / "sp-quick").exists()
    assert manifest.check_modified() == []


@pytest.mark.parametrize("integration_key", ["codex", "cursor-agent"])
def test_classic_quick_keeps_worker_default(tmp_path, integration_key):
    integration = get_integration(integration_key)
    manifest = IntegrationManifest(integration_key, tmp_path)
    integration.setup(
        tmp_path, manifest,
        parsed_options={"workflow_profile": "classic"}, script_type="sh",
    )
    skills = integration.skills_dest(tmp_path)
    entry = skills / "sp-quick" / "SKILL.md"
    text = normalized(entry)
    assert "subagent-mandatory" in text
    assert "--leader-direct" not in text
    assert not (skills / "spx-quick").exists()
    assert manifest.check_modified() == []


def test_quick_policy_repair_preserves_user_changes(tmp_path):
    integration = get_integration("codex")
    manifest = IntegrationManifest("codex", tmp_path)
    integration.setup(
        tmp_path, manifest,
        parsed_options={"workflow_profile": "advanced"}, script_type="sh",
    )
    policy = integration.skills_dest(tmp_path) / "spx-quick" / "references" / "task-contract.md"
    original = policy.read_bytes()
    policy.unlink()
    manifest.save()
    manifest = IntegrationManifest.load("codex", tmp_path)
    restored = integration.repair_missing_advanced_skill_files(tmp_path, manifest, script_type="sh")
    assert policy in restored
    assert policy.read_bytes() == original
    assert manifest.check_modified() == []

    custom = original + b"\nLocal policy: preserve operator-owned additions.\n"
    policy.write_bytes(custom)
    restored = integration.repair_missing_advanced_skill_files(tmp_path, manifest, script_type="sh")
    assert policy not in restored
    assert policy.read_bytes() == custom
    assert policy.relative_to(tmp_path).as_posix() in manifest.check_modified()
