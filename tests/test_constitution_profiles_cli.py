import json
import os


def _compact(text):
    return " ".join(text.split())


def _run_init_for_constitution_profile(tmp_path, project_name, profile=None):
    from typer.testing import CliRunner
    from specify_cli import app

    project = tmp_path / project_name
    project.mkdir()
    runner = CliRunner()
    args = [
        "init",
        "--here",
        "--ai",
        "claude",
        "--script",
        "sh",
        "--no-git",
        "--ignore-agent-tools",
    ]
    if profile is not None:
        args.extend(["--constitution-profile", profile])

    old_cwd = os.getcwd()
    try:
        os.chdir(project)
        result = runner.invoke(app, args, catch_exceptions=False)
    finally:
        os.chdir(old_cwd)

    assert result.exit_code == 0, result.output
    init_options = json.loads((project / ".specify" / "init-options.json").read_text(encoding="utf-8"))
    constitution = (project / ".specify" / "memory" / "constitution.md").read_text(encoding="utf-8")
    return project, result, init_options, constitution


def test_init_defaults_to_product_constitution_profile(tmp_path):
    _, _, init_options, constitution = _run_init_for_constitution_profile(
        tmp_path,
        "product-profile-project",
    )

    assert init_options["constitution_profile"] == "product"
    assert "### VII. No Unrequested Fallbacks" in constitution
    assert ".specify/project-cognition/status.json" in constitution
    assert "default brownfield runtime truth surface" in constitution
    assert "Project Cognition Before Existing-System Judgment" in constitution
    assert "agents MUST query project cognition before broad source inspection" in _compact(constitution)
    assert "map-update" in constitution


def test_init_with_library_constitution_profile_materializes_project_template(tmp_path):
    project, result, init_options, constitution = _run_init_for_constitution_profile(
        tmp_path,
        "library-profile-project",
        profile="library",
    )

    template = (project / ".specify" / "templates" / "constitution-template.md").read_text(encoding="utf-8")
    profile_asset = project / ".specify" / "templates" / "constitution" / "profiles" / "library.yml"
    base_asset = project / ".specify" / "templates" / "constitution" / "base.md"

    assert init_options["constitution_profile"] == "library"
    assert profile_asset.exists()
    assert base_asset.exists()
    assert "Stable Public Surface" in template
    assert "SemVer and Release Discipline" in template
    assert "Project Cognition Before Existing-System Judgment" in template
    assert ".specify/project-cognition/status.json" not in template
    assert "Stable Public Surface" in constitution
    assert "Project Cognition Before Existing-System Judgment" in constitution
    assert "library constitution profile" in result.output.lower()


def test_init_with_minimal_constitution_profile_materializes_project_constitution(tmp_path):
    _, result, init_options, constitution = _run_init_for_constitution_profile(
        tmp_path,
        "minimal-profile-project",
        profile="minimal",
    )

    assert init_options["constitution_profile"] == "minimal"
    assert "Project Cognition Before Existing-System Judgment" in constitution
    assert "scope boundaries" in constitution
    assert ".specify/project-cognition/status.json" not in constitution
    assert "minimal constitution profile" in result.output.lower()


def test_init_with_regulated_constitution_profile_materializes_project_constitution(tmp_path):
    _, result, init_options, constitution = _run_init_for_constitution_profile(
        tmp_path,
        "regulated-profile-project",
        profile="regulated",
    )

    assert init_options["constitution_profile"] == "regulated"
    assert "Project Cognition Before Existing-System Judgment" in constitution
    assert "trust boundaries" in constitution
    assert "control impact" in constitution
    assert ".specify/project-cognition/status.json" not in constitution
    assert "regulated constitution profile" in result.output.lower()


def test_init_rejects_unknown_constitution_profile(tmp_path):
    from typer.testing import CliRunner
    from specify_cli import app

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "init",
            str(tmp_path / "invalid-profile-project"),
            "--ai",
            "claude",
            "--script",
            "sh",
            "--no-git",
            "--ignore-agent-tools",
            "--constitution-profile",
            "unknown",
        ],
    )

    assert result.exit_code != 0
    assert "Invalid --constitution-profile value" in result.output


def test_init_accepts_default_constitution_profile_alias(tmp_path):
    _, _, init_options, constitution = _run_init_for_constitution_profile(
        tmp_path,
        "default-profile-alias-project",
        profile="default",
    )

    assert init_options["constitution_profile"] == "product"
    assert "### VII. No Unrequested Fallbacks" in constitution
