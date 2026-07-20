"""Cross-integration rendering contract for the post-implementation review workflow."""

import tomllib

from specify_cli.integrations import get_integration
from specify_cli.integrations.manifest import IntegrationManifest


def _install(integration_key, project, *, workflow_profile="classic"):
    integration = get_integration(integration_key)
    assert integration is not None
    manifest = IntegrationManifest(integration_key, project)
    integration.setup(
        project,
        manifest,
        parsed_options={"workflow_profile": workflow_profile},
        script_type="sh",
    )
    return integration, manifest


def test_classic_skills_profile_renders_and_tracks_sp_review(tmp_path):
    project = tmp_path / "codex-classic-review"

    integration, manifest = _install("codex", project)

    review_skill = integration.skills_dest(project) / "sp-review" / "SKILL.md"
    relative = review_skill.relative_to(project).as_posix()
    assert review_skill.is_file()
    assert relative in manifest.files

    content = review_skill.read_text(encoding="utf-8")
    assert 'name: "sp-review"' in content
    assert "templates/commands/review.md" in content


def test_classic_markdown_integration_renders_and_tracks_sp_review(tmp_path):
    project = tmp_path / "qwen-classic-review"

    integration, manifest = _install("qwen", project)

    review_command = integration.commands_dest(project) / "sp.review.md"
    relative = review_command.relative_to(project).as_posix()
    assert review_command.is_file()
    assert relative in manifest.files
    assert "sp-review" in review_command.read_text(encoding="utf-8").lower()


def test_classic_toml_integration_renders_parseable_and_tracked_sp_review(tmp_path):
    project = tmp_path / "gemini-classic-review"

    integration, manifest = _install("gemini", project)

    review_command = integration.commands_dest(project) / "sp.review.toml"
    relative = review_command.relative_to(project).as_posix()
    assert review_command.is_file()
    assert relative in manifest.files

    rendered = tomllib.loads(review_command.read_text(encoding="utf-8"))
    assert rendered["description"]
    assert "sp-review" in rendered["prompt"].lower()


def test_advanced_skills_profile_renders_and_tracks_spx_review(tmp_path):
    project = tmp_path / "codex-advanced-review"

    integration, manifest = _install(
        "codex",
        project,
        workflow_profile="advanced",
    )

    review_dir = integration.skills_dest(project) / "spx-review"
    review_skill = review_dir / "SKILL.md"
    assert review_skill.is_file()
    assert not (integration.skills_dest(project) / "sp-review" / "SKILL.md").exists()

    installed_files = [path for path in review_dir.rglob("*") if path.is_file()]
    assert installed_files
    for installed_file in installed_files:
        relative = installed_file.relative_to(project).as_posix()
        assert relative in manifest.files

    content = review_skill.read_text(encoding="utf-8")
    assert 'name: "spx-review"' in content
    assert "templates/advanced-skills/spx-review/SKILL.md" in content
