"""Tests for GrokIntegration."""

from pathlib import Path

from specify_cli.integrations import get_integration
from specify_cli.integrations.grok import GrokMultiAgentAdapter
from specify_cli.integrations.manifest import IntegrationManifest
from specify_cli.orchestration import describe_delegation_surface


def test_grok_skills_init_installs_command_and_passive_skills(tmp_path):
    from typer.testing import CliRunner
    from specify_cli import app

    runner = CliRunner()
    target = tmp_path / "grok-skills-runtime"

    result = runner.invoke(
        app,
        [
            "init",
            str(target),
            "--ai",
            "grok",
            "--no-git",
            "--ignore-agent-tools",
            "--script",
            "sh",
        ],
    )

    assert result.exit_code == 0, f"init --ai grok failed: {result.output}"
    plan_skill = target / ".grok" / "skills" / "sp-plan" / "SKILL.md"
    assert plan_skill.exists()
    assert (target / ".grok" / "skills" / "dispatching-parallel-agents" / "SKILL.md").exists()
    content = plan_skill.read_text(encoding="utf-8")
    assert "user-invocable: true" in content
    assert "/sp-plan" in content or "sp-plan" in content


def test_grok_invoke_placeholder_projects_slash_skill_surface():
    from specify_cli.integrations.base import IntegrationBase

    rendered = IntegrationBase.process_template(
        "---\n---\nRun {{invoke:plan}} next.",
        "grok",
        "sh",
    )

    assert rendered.endswith("Run /sp-plan next.")


def test_grok_multi_agent_adapter_declares_spawn_subagent_surface():
    snapshot = GrokMultiAgentAdapter().detect_capabilities()

    assert snapshot.integration_key == "grok"
    assert snapshot.native_subagents is True
    assert snapshot.native_worker_surface == "spawn_subagent"
    assert snapshot.structured_results is True
    assert snapshot.managed_team_supported is False
    assert snapshot.delegation_confidence in {"medium", "high"}

    descriptor = describe_delegation_surface(
        command_name="plan",
        snapshot=snapshot,
    )
    assert "spawn_subagent" in descriptor.native_discovery_hint
    assert "spawn_subagent" in descriptor.native_dispatch_hint
    assert "get_command_or_subagent_output" in descriptor.native_join_hint
    assert "result submit" in descriptor.native_join_hint.lower() or "result submit" in descriptor.result_submit_hint
    assert "No subagent dispatch path for this session." not in descriptor.native_dispatch_hint
    assert "no known native subagent surface is configured" not in descriptor.native_discovery_hint


def _install_grok(project: Path, *, workflow_profile: str = "classic") -> Path:
    integration = get_integration("grok")
    assert integration is not None
    manifest = IntegrationManifest("grok", project)
    integration.setup(
        project,
        manifest,
        parsed_options={"workflow_profile": workflow_profile},
        script_type="sh",
    )
    return integration.skills_dest(project)


def test_classic_grok_plan_and_tasks_wire_spawn_subagent_and_result_submit(tmp_path: Path):
    skills_dir = _install_grok(tmp_path / "classic-grok-native")

    plan = (skills_dir / "sp-plan" / "SKILL.md").read_text(encoding="utf-8")
    tasks = (skills_dir / "sp-tasks" / "SKILL.md").read_text(encoding="utf-8")
    implement = (skills_dir / "sp-implement" / "SKILL.md").read_text(encoding="utf-8")

    for content, label in ((plan, "plan"), (tasks, "tasks"), (implement, "implement")):
        assert "spawn_subagent" in content, label
        assert "get_command_or_subagent_output" in content, label
        assert "no known native subagent surface is configured" not in content.lower(), label
        assert "No subagent dispatch path for this session." not in content, label

    assert "Grok Subagent Capability Discovery" in plan
    assert "Grok Subagent Capability Discovery" in tasks
    assert "result submit --command plan" in plan
    assert "result submit --command tasks" in tasks
    assert "Grok Adaptive Dispatch" in plan
    assert "Grok Adaptive Dispatch" in tasks
    assert "Grok Adaptive Dispatch" in implement


def test_advanced_grok_native_subagent_reference_binds_spawn_subagent(tmp_path: Path):
    skills_dir = _install_grok(
        tmp_path / "advanced-grok-native",
        workflow_profile="advanced",
    )

    shared = (
        skills_dir / "spx-plan" / "references" / "native-subagents.md"
    ).read_text(encoding="utf-8")
    assert "spawn_subagent" in shared
    assert "get_command_or_subagent_output" in shared
    assert "Grok Native Subagent Surface" in shared

    plan = (skills_dir / "spx-plan" / "SKILL.md").read_text(encoding="utf-8")
    tasks = (skills_dir / "spx-tasks" / "SKILL.md").read_text(encoding="utf-8")
    assert "references/native-subagents.md" in plan
    assert "references/native-subagents.md" in tasks
