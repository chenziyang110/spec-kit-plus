from pathlib import Path

from specify_cli.integrations import INTEGRATION_REGISTRY, get_integration
from specify_cli.integrations.base import SkillsIntegration
from specify_cli.integrations.manifest import IntegrationManifest


REPO_ROOT = Path(__file__).resolve().parent.parent


def _passive_skill_files() -> list[str]:
    passive_root = REPO_ROOT / "templates" / "passive-skills"
    return sorted(
        path.relative_to(passive_root).as_posix()
        for path in passive_root.rglob("*")
        if path.is_file()
    )


def _skills_integration_keys() -> list[str]:
    return sorted(
        key
        for key, integration in INTEGRATION_REGISTRY.items()
        if isinstance(integration, SkillsIntegration)
    )


def test_repo_contains_expected_passive_skill_templates() -> None:
    passive_files = _passive_skill_files()

    assert passive_files
    assert "spec-kit-workflow-routing/SKILL.md" not in passive_files
    assert "spec-kit-project-cognition-gate/SKILL.md" in passive_files
    assert "spec-kit-discussion-handoff-review/SKILL.md" in passive_files
    assert "spec-kit-project-map-gate/SKILL.md" not in passive_files
    assert "spec-kit-project-learning/SKILL.md" in passive_files
    assert "project-to-prd/SKILL.md" in passive_files
    assert "spec-kit-ui-design/SKILL.md" in passive_files
    assert "tdd-workflow/SKILL.md" in passive_files
    assert "frontend-design/SKILL.md" in passive_files
    assert "python-testing/SKILL.md" in passive_files
    assert "js-testing/SKILL.md" in passive_files
    assert "code-review-skill/reference/react.md" in passive_files


def test_skills_integrations_install_all_passive_skill_files(tmp_path: Path) -> None:
    passive_files = _passive_skill_files()

    for integration_key in _skills_integration_keys():
        integration = get_integration(integration_key)
        assert integration is not None

        manifest = IntegrationManifest(integration_key, tmp_path / integration_key)
        created = integration.setup(tmp_path / integration_key, manifest, script_type="sh")

        installed = {
            path.resolve().relative_to((tmp_path / integration_key).resolve()).as_posix()
            for path in created
        }

        skill_prefix = integration.config["folder"].rstrip("/") + "/" + integration.config.get(
            "commands_subdir", "skills"
        )
        expected_files = {
            f"{skill_prefix}/{relative_file}"
            for relative_file in passive_files
        }

        assert expected_files.issubset(installed), (
            f"{integration_key} did not install all passive skill files: "
            f"{sorted(expected_files - installed)}"
        )
        retired_prefix = f"{skill_prefix}/spec-kit-workflow-routing/"
        assert not any(path.startswith(retired_prefix) for path in installed), (
            f"{integration_key} installed retired passive workflow routing"
        )


def test_skills_integrations_remove_unmodified_retired_workflow_router(
    tmp_path: Path,
) -> None:
    for integration_key in _skills_integration_keys():
        project = tmp_path / integration_key
        integration = get_integration(integration_key)
        assert integration is not None
        manifest = IntegrationManifest(integration_key, project)
        retired = (
            integration.skills_dest(project)
            / "spec-kit-workflow-routing"
            / "SKILL.md"
        )
        retired_rel = retired.relative_to(project)
        manifest.record_file(retired_rel, "managed legacy router\n")

        integration.setup(project, manifest, script_type="sh")

        assert not retired.exists(), integration_key
        assert retired_rel.as_posix() not in manifest.files, integration_key


def test_skills_integration_preserves_modified_retired_workflow_router(
    tmp_path: Path,
) -> None:
    integration = get_integration("codex")
    assert integration is not None
    manifest = IntegrationManifest("codex", tmp_path)
    retired = (
        integration.skills_dest(tmp_path)
        / "spec-kit-workflow-routing"
        / "SKILL.md"
    )
    retired_rel = retired.relative_to(tmp_path)
    manifest.record_file(retired_rel, "managed legacy router\n")
    retired.write_text("user-modified router\n", encoding="utf-8")

    integration.setup(tmp_path, manifest, script_type="sh")

    assert retired.read_text(encoding="utf-8") == "user-modified router\n"
    assert retired_rel.as_posix() in manifest.files
