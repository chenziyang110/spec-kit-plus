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
    assert "spec-kit-workflow-routing/SKILL.md" in passive_files
    assert "spec-kit-project-map-gate/SKILL.md" in passive_files
    assert "spec-kit-project-learning/SKILL.md" in passive_files
    assert "project-to-prd/SKILL.md" in passive_files
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
