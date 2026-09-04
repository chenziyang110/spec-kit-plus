"""Verify that both installed profiles carry the optional checkpoint contract."""

import re

import pytest

from specify_cli import _render_spec_kit_managed_block
from specify_cli.integrations import get_integration
from specify_cli.integrations.manifest import IntegrationManifest
from specify_cli.launcher import write_runtime_launcher_config
from specify_cli.specify_runtime import project_runtime_launcher_arg
from tests.template_utils import read_skill_with_references


def _assert_prefix_contract(content: str) -> None:
    compact = re.sub(r"\s+", " ", content).lower()
    assert "active discussion turns" in compact
    assert "suppress the reminder" in compact
    assert "handoff assessment or consumer-route selection" in compact
    assert "draft handoff review or exact digest confirmation" in compact
    assert "`handoff-ready` closeout or downstream invocation" in compact
    assert "end every discussion reply" not in compact
    assert "optional leading `checkpoint` prefix" in compact
    assert "no `continue` keyword or extra confirmation is required" in compact
    assert "separate the prefix from the discussion body" in compact
    assert "save prior pending progress first" in compact
    assert "then answer the body normally" in compact
    assert "prompt does not write files by itself" in compact
    assert "after several unsaved" not in compact


@pytest.mark.parametrize("agent", ["codex", "claude"])
@pytest.mark.parametrize("profile", ["classic", "advanced"])
def test_installed_discussion_keeps_prefix_and_body_independent(tmp_path, agent, profile):
    project = tmp_path / f"{agent}-{profile}"
    integration = get_integration(agent)
    manifest = IntegrationManifest(agent, project)
    integration.setup(project, manifest, parsed_options={"workflow_profile": profile})
    name = "sp-discussion" if profile == "classic" else "spx-discussion"
    skill = integration.skills_dest(project) / name / "SKILL.md"
    combined = read_skill_with_references(skill)

    _assert_prefix_contract(combined)
    assert "需要保存讨论进度时，可在下一条回复前加 `checkpoint`。" in combined
    assert "需要保存进度时，可在下一条回复前加 `checkpoint`。" not in combined
    assert "checkpoint，这个方案的成本怎么算？" in combined
    assert "这个方案的成本怎么算？" in combined
    assert "这里的 checkpoint 是什么意思？" in combined
    assert "quoted text, code, or a question about checkpoint" in re.sub(r"\s+", " ", combined).lower()
    # Prompt changes must retain the real write-owner and stale-state protection.
    assert "--expected-state-sha256" in combined
    assert "discussion checkpoint" in combined
    assert "compaction" in combined.lower()


def test_bootstrap_guidance_does_not_turn_reminder_into_a_save_gate(tmp_path):
    block = _render_spec_kit_managed_block(project_root=tmp_path, newline="\n")
    _assert_prefix_contract(block)
    assert "semantic checkpoints, user-triggered checkpoints/saves, compaction risk, or lifecycle transitions" in block


@pytest.mark.parametrize("agent", ["codex", "claude"])
@pytest.mark.parametrize("profile", ["classic", "advanced"])
def test_installed_discussion_checkpoint_uses_exact_launcher_and_typed_recovery(
    tmp_path, agent, profile
):
    project = tmp_path / f"{agent}-{profile}-runtime"
    project.mkdir()
    runtime_source = tmp_path / f"{agent}-{profile}-specify-runtime.exe"
    runtime_source.write_bytes(b"runtime fixture")
    write_runtime_launcher_config(project, runtime_source)

    integration = get_integration(agent)
    manifest = IntegrationManifest(agent, project)
    integration.setup(project, manifest, parsed_options={"workflow_profile": profile})
    name = "sp-discussion" if profile == "classic" else "spx-discussion"
    skill = integration.skills_dest(project) / name / "SKILL.md"
    combined = read_skill_with_references(skill)
    compact = re.sub(r"\s+", " ", combined).lower()
    runtime_command = project_runtime_launcher_arg()

    assert f"{runtime_command} discussion checkpoint <slug>" in combined
    assert "use the exact rendered project-local runtime launcher" in compact
    assert "never prepend or synthesize a drive letter" in compact
    assert "--input-json -" in combined
    assert "do not place a powershell here-string directly after `--input-json`" in compact
    assert "retry the exact rendered launcher from the project root" in compact
    assert "discussion-checkpoint-input" in combined
    assert "standalone `checkpoint` has no discussion body to continue" in compact
    assert "do not dismiss the failure as harmless" in compact
    assert re.search(r"\b[a-z]:\.specify[\\/]", combined, re.IGNORECASE) is None
