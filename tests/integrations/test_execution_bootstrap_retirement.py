"""Focused renderer and manifest checks for the shared execution bootstrap."""

from pathlib import Path

import pytest

from specify_cli.integrations import get_integration
from specify_cli.integrations.base import IntegrationBase
from specify_cli.integrations.manifest import IntegrationManifest


PROJECT_ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize(
    "relative",
    (
        "commands/specify.md",
        "command-references/implement/task-intake-and-tracker.md",
    ),
)
def test_classic_includes_resolve_the_renamed_execution_bootstrap(relative: str) -> None:
    templates = PROJECT_ROOT / "templates"
    source = templates / relative
    bootstrap = templates / "command-partials/common/execution-bootstrap.md"
    rendered = IntegrationBase.render_template_content(
        source.read_text(encoding="utf-8"), template_path=source
    )

    assert bootstrap.read_text(encoding="utf-8").strip() in rendered
    assert "{{spec-kit-include:" not in rendered
    assert "run-bootstrap.md" not in rendered
    assert "specify-runtime run " not in rendered
    assert "SPECIFY_RUN_" not in rendered
    assert not (bootstrap.parent / "run-bootstrap.md").exists()


@pytest.mark.parametrize("modified", (False, True))
def test_advanced_upgrade_retires_both_recorded_bootstrap_copies_without_losing_edits(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, modified: bool
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    sources = tmp_path / "advanced"
    shared = sources / "_shared"
    shared.mkdir(parents=True)
    (shared / "execution-bootstrap.md").write_text(
        "Execution uses the selected project and its Work Board guards.\n", encoding="utf-8"
    )
    skill = sources / "spx-implement"
    skill.mkdir()
    (skill / "SKILL.md").write_text(
        "---\nname: spx-implement\ndescription: advanced install fixture\n---\n\n"
        "Read `references/execution-bootstrap.md`.\n", encoding="utf-8"
    )
    integration = get_integration("codex")
    assert integration is not None
    monkeypatch.setattr(integration, "shared_advanced_skills_dir", lambda: sources)
    monkeypatch.setattr(integration, "list_advanced_skill_templates", lambda: [skill])
    manifest = IntegrationManifest("codex", project)
    skills = integration.skills_dest(project)
    previous = [
        skills / "references/run-bootstrap.md",
        skills / "spx-implement/references/run-bootstrap.md",
    ]
    for path in previous:
        manifest.record_file(path.relative_to(project), "previous generated bootstrap\n")
        if modified:
            path.write_text("user-modified reference\n", encoding="utf-8")
    classic = skills / "sp-plan/SKILL.md"
    manifest.record_file(classic.relative_to(project), "classic profile must remain\n")
    personal = skills / "references/personal.md"
    personal.write_text("untracked personal reference\n", encoding="utf-8")

    integration._install_advanced_skills(
        project_root=project, manifest=manifest, script_type="sh", arg_placeholder="$ARGUMENTS"
    )

    for directory in (skills / "references", skills / "spx-implement/references"):
        current = directory / "execution-bootstrap.md"
        assert current.is_file()
        assert current.relative_to(project).as_posix() in manifest.files
    for path in previous:
        assert path.exists() is modified
        assert (path.relative_to(project).as_posix() in manifest.files) is modified
        if modified:
            assert path.read_text(encoding="utf-8") == "user-modified reference\n"
    assert classic.read_text(encoding="utf-8") == "classic profile must remain\n"
    assert personal.read_text(encoding="utf-8") == "untracked personal reference\n"
