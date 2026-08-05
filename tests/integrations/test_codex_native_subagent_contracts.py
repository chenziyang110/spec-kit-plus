"""Regression tests for Codex native subagent lifecycle and handoffs."""

from pathlib import Path

from specify_cli.integrations import get_integration
from specify_cli.integrations.manifest import IntegrationManifest


def _install_codex(project: Path, *, workflow_profile: str = "classic") -> Path:
    integration = get_integration("codex")
    assert integration is not None
    manifest = IntegrationManifest("codex", project)
    integration.setup(
        project,
        manifest,
        parsed_options={"workflow_profile": workflow_profile},
        script_type="sh",
    )
    return integration.skills_dest(project)


def _read_skill_with_references(skill_path: Path) -> str:
    parts = [skill_path.read_text(encoding="utf-8")]
    references_dir = skill_path.parent / "references"
    if references_dir.is_dir():
        parts.extend(
            path.read_text(encoding="utf-8")
            for path in sorted(references_dir.glob("**/*.md"))
        )
    return "\n\n".join(parts)


def test_classic_codex_native_subagent_skills_require_spawn_wait_and_no_close(
    tmp_path: Path,
) -> None:
    skills_dir = _install_codex(tmp_path / "classic-codex-native")
    subagent_skills: list[Path] = []

    for skill_path in sorted(skills_dir.glob("sp-*/SKILL.md")):
        content = _read_skill_with_references(skill_path)
        if "spawn_agent" not in content:
            continue
        subagent_skills.append(skill_path)
        assert "wait_agent" in content, skill_path
        assert "close_agent" not in content, skill_path
        assert "interrupt_agent" in content or "cancel" in content.lower(), skill_path

    assert subagent_skills, (
        "expected at least one Classic Codex sp-* skill to use native subagents"
    )

    for shared_skill_name in (
        "subagent-driven-development",
        "dispatching-parallel-agents",
        "spec-kit-workflow-routing",
    ):
        shared_content = _read_skill_with_references(
            skills_dir / shared_skill_name / "SKILL.md"
        ).lower()
        assert "dispatch and join" in shared_content, shared_skill_name
        assert "accepted terminal result" in shared_content, shared_skill_name
        assert "stage" in shared_content and "result" in shared_content, shared_skill_name


def test_advanced_codex_spx_skills_stay_close_agent_free_and_preserve_stage_result_submit(
    tmp_path: Path,
) -> None:
    skills_dir = _install_codex(
        tmp_path / "advanced-codex-native",
        workflow_profile="advanced",
    )

    generated = {
        skill_path.parent.name: _read_skill_with_references(skill_path)
        for skill_path in sorted(skills_dir.glob("spx-*/SKILL.md"))
    }
    assert generated, "expected Advanced Codex spx-* skills to be generated"

    for skill_name, content in generated.items():
        assert "close_agent" not in content, skill_name

    plan_content = generated["spx-plan"]
    tasks_content = generated["spx-tasks"]
    assert "result submit --command plan" in plan_content
    assert "result submit --command tasks" in tasks_content
    assert "sp-teams submit-result" not in plan_content
    assert "sp-teams submit-result" not in tasks_content

    shared_contract = (
        skills_dir / "spx-plan" / "references" / "native-subagents.md"
    ).read_text(encoding="utf-8")
    assert "dispatch and join operations" in shared_contract
    assert "accepted terminal result completes" in shared_contract
    assert "explicitly selected durable-team workflow" in shared_contract

    delegated_skills = {
        "spx-clarify",
        "spx-debug",
        "spx-deep-research",
        "spx-implement",
        "spx-map-scan",
        "spx-plan",
        "spx-prd-build",
        "spx-prd-scan",
        "spx-quick",
        "spx-review",
        "spx-tasks",
    }
    for skill_name in delegated_skills:
        assert "references/native-subagents.md" in generated[skill_name], skill_name
