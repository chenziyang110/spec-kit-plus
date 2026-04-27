import json
import os


def test_init_defaults_to_product_constitution_profile(tmp_path):
    from typer.testing import CliRunner
    from specify_cli import app

    project = tmp_path / "product-profile-project"
    project.mkdir()
    runner = CliRunner()

    old_cwd = os.getcwd()
    try:
        os.chdir(project)
        result = runner.invoke(
            app,
            [
                "init",
                "--here",
                "--ai",
                "claude",
                "--script",
                "sh",
                "--no-git",
                "--ignore-agent-tools",
            ],
            catch_exceptions=False,
        )
    finally:
        os.chdir(old_cwd)

    assert result.exit_code == 0, result.output
    init_options = json.loads((project / ".specify" / "init-options.json").read_text(encoding="utf-8"))
    constitution = (project / ".specify" / "memory" / "constitution.md").read_text(encoding="utf-8")

    assert init_options["constitution_profile"] == "product"
    assert "### VII. No Unrequested Fallbacks" in constitution
    assert "PROJECT-HANDBOOK.md" in constitution


def test_init_with_library_constitution_profile_materializes_project_template(tmp_path):
    from typer.testing import CliRunner
    from specify_cli import app

    project = tmp_path / "library-profile-project"
    project.mkdir()
    runner = CliRunner()

    old_cwd = os.getcwd()
    try:
        os.chdir(project)
        result = runner.invoke(
            app,
            [
                "init",
                "--here",
                "--ai",
                "claude",
                "--script",
                "sh",
                "--no-git",
                "--ignore-agent-tools",
                "--constitution-profile",
                "library",
            ],
            catch_exceptions=False,
        )
    finally:
        os.chdir(old_cwd)

    assert result.exit_code == 0, result.output

    init_options = json.loads((project / ".specify" / "init-options.json").read_text(encoding="utf-8"))
    template = (project / ".specify" / "templates" / "constitution-template.md").read_text(encoding="utf-8")
    constitution = (project / ".specify" / "memory" / "constitution.md").read_text(encoding="utf-8")
    profile_asset = project / ".specify" / "templates" / "constitution" / "profiles" / "library.yml"
    base_asset = project / ".specify" / "templates" / "constitution" / "base.md"

    assert init_options["constitution_profile"] == "library"
    assert profile_asset.exists()
    assert base_asset.exists()
    assert "Stable Public Surface" in template
    assert "SemVer and Release Discipline" in template
    assert "PROJECT-HANDBOOK.md" not in template
    assert "Stable Public Surface" in constitution
    assert "library constitution profile" in result.output.lower()


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
    from typer.testing import CliRunner
    from specify_cli import app

    project = tmp_path / "default-profile-alias-project"
    project.mkdir()
    runner = CliRunner()

    old_cwd = os.getcwd()
    try:
        os.chdir(project)
        result = runner.invoke(
            app,
            [
                "init",
                "--here",
                "--ai",
                "claude",
                "--script",
                "sh",
                "--no-git",
                "--ignore-agent-tools",
                "--constitution-profile",
                "default",
            ],
            catch_exceptions=False,
        )
    finally:
        os.chdir(old_cwd)

    assert result.exit_code == 0, result.output
    init_options = json.loads((project / ".specify" / "init-options.json").read_text(encoding="utf-8"))
    constitution = (project / ".specify" / "memory" / "constitution.md").read_text(encoding="utf-8")

    assert init_options["constitution_profile"] == "product"
    assert "### VII. No Unrequested Fallbacks" in constitution
