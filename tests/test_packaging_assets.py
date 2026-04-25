import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent


def test_wheel_force_include_bundles_passive_skills() -> None:
    pyproject = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")

    assert '"templates/passive-skills" = "specify_cli/core_pack/passive-skills"' in pyproject


def test_wheel_force_include_bundles_command_partials_and_testing_templates() -> None:
    pyproject = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")

    assert '"templates/command-partials" = "specify_cli/core_pack/command-partials"' in pyproject
    assert '"templates/testing" = "specify_cli/core_pack/templates/testing"' in pyproject


def test_wheel_force_include_bundles_workflow_state_template() -> None:
    pyproject = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")

    assert (
        '"templates/workflow-state-template.md" = '
        '"specify_cli/core_pack/templates/workflow-state-template.md"'
    ) in pyproject


def test_wheel_force_include_bundles_internal_codex_team_runtime_assets() -> None:
    pyproject = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")

    expected_entries = [
        '"extensions/agent-teams/engine/package.json" = "specify_cli/core_pack/extensions/agent-teams/engine/package.json"',
        '"extensions/agent-teams/engine/src" = "specify_cli/core_pack/extensions/agent-teams/engine/src"',
        '"extensions/agent-teams/engine/crates" = "specify_cli/core_pack/extensions/agent-teams/engine/crates"',
        '"extensions/agent-teams/engine/prompts" = "specify_cli/core_pack/extensions/agent-teams/engine/prompts"',
        '"extensions/agent-teams/engine/skills" = "specify_cli/core_pack/extensions/agent-teams/engine/skills"',
    ]

    for entry in expected_entries:
        assert entry in pyproject


def test_internal_codex_team_runtime_cargo_lock_is_tracked_for_force_include() -> None:
    tracked = subprocess.run(
        ["git", "ls-files", "extensions/agent-teams/engine/Cargo.lock"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()

    assert tracked == "extensions/agent-teams/engine/Cargo.lock"


def test_install_shared_infra_copies_split_core_pack_template_dirs(tmp_path, monkeypatch) -> None:
    from specify_cli import _install_shared_infra

    core_pack = tmp_path / "core_pack"
    (core_pack / "templates").mkdir(parents=True)
    (core_pack / "templates" / "project-handbook-template.md").write_text("# Handbook\n", encoding="utf-8")
    (core_pack / "templates" / "testing").mkdir(parents=True)
    (core_pack / "templates" / "testing" / "testing-contract-template.md").write_text(
        "# Testing Contract\n",
        encoding="utf-8",
    )
    (core_pack / "command-partials" / "test").mkdir(parents=True)
    (core_pack / "command-partials" / "test" / "shell.md").write_text("shell\n", encoding="utf-8")
    (core_pack / "passive-skills" / "python-testing").mkdir(parents=True)
    (core_pack / "passive-skills" / "python-testing" / "SKILL.md").write_text("---\nname: python-testing\n---\n", encoding="utf-8")
    (core_pack / "project-map").mkdir(parents=True)
    (core_pack / "project-map" / "ARCHITECTURE.md").write_text("# Architecture\n", encoding="utf-8")
    (core_pack / "worker-prompts").mkdir(parents=True)
    (core_pack / "worker-prompts" / "implementer.md").write_text("# Implementer\n", encoding="utf-8")
    (core_pack / "scripts" / "powershell").mkdir(parents=True)
    (core_pack / "scripts" / "powershell" / "common.ps1").write_text("# common\n", encoding="utf-8")

    monkeypatch.setattr("specify_cli._locate_core_pack", lambda: core_pack)

    project_root = tmp_path / "project"
    project_root.mkdir()

    assert _install_shared_infra(project_root, "ps") is True
    assert (project_root / ".specify" / "templates" / "testing" / "testing-contract-template.md").exists()
    assert (project_root / ".specify" / "templates" / "command-partials" / "test" / "shell.md").exists()
    assert (project_root / ".specify" / "templates" / "passive-skills" / "python-testing" / "SKILL.md").exists()
    assert (project_root / ".specify" / "templates" / "project-map" / "ARCHITECTURE.md").exists()
    assert (project_root / ".specify" / "templates" / "worker-prompts" / "implementer.md").exists()
