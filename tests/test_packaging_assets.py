import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent


def test_wheel_force_include_bundles_passive_skills() -> None:
    pyproject = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")

    assert '"templates/passive-skills" = "specify_cli/core_pack/passive-skills"' in pyproject


def test_wheel_force_include_bundles_command_partials_and_testing_templates() -> None:
    pyproject = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")

    assert '"templates/command-partials" = "specify_cli/core_pack/command-partials"' in pyproject
    assert '"templates/prd" = "specify_cli/core_pack/templates/prd"' in pyproject
    assert '"templates/testing" = "specify_cli/core_pack/templates/testing"' in pyproject


def test_wheel_force_include_covers_deep_research_planning_handoff_contract() -> None:
    pyproject = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    deep_research = (REPO_ROOT / "templates" / "commands" / "deep-research.md").read_text(encoding="utf-8")
    plan = (REPO_ROOT / "templates" / "commands" / "plan.md").read_text(encoding="utf-8")
    shell_partial = (
        REPO_ROOT / "templates" / "command-partials" / "deep-research" / "shell.md"
    ).read_text(encoding="utf-8")

    assert '"templates/commands" = "specify_cli/core_pack/commands"' in pyproject
    assert '"templates/command-partials" = "specify_cli/core_pack/command-partials"' in pyproject
    assert "Traceability and Evidence Quality Contract" in deep_research
    assert "Planning Handoff" in deep_research
    assert "PH-001" in deep_research
    assert "CAP-001" in deep_research
    assert "Deep Research Traceability Matrix" in plan
    assert "research finding or spike supports each design decision" in shell_partial


def test_deep_research_golden_examples_are_bundled_with_templates() -> None:
    pyproject = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    examples_dir = REPO_ROOT / "templates" / "examples" / "deep-research"

    assert '"templates/examples" = "specify_cli/core_pack/templates/examples"' in pyproject
    assert (examples_dir / "not-needed.md").exists()
    assert (examples_dir / "docs-only-evidence.md").exists()
    assert (examples_dir / "spike-required.md").exists()

    not_needed = (examples_dir / "not-needed.md").read_text(encoding="utf-8")
    docs_only = (examples_dir / "docs-only-evidence.md").read_text(encoding="utf-8")
    spike_required = (examples_dir / "spike-required.md").read_text(encoding="utf-8")

    assert "**Status**: Not needed" in not_needed
    assert "EVD-001" in docs_only
    assert "PH-001" in docs_only
    assert "SPK-001" in spike_required
    assert "research-spikes/" in spike_required


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


def test_wheel_force_include_bundles_shared_hook_launcher_assets() -> None:
    pyproject = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")

    assert '"src/specify_cli/shared_hooks" = "specify_cli/core_pack/shared_hooks"' in pyproject


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
    (core_pack / "templates" / "examples" / "deep-research").mkdir(parents=True)
    (core_pack / "templates" / "examples" / "deep-research" / "not-needed.md").write_text(
        "# Not needed\n",
        encoding="utf-8",
    )
    (core_pack / "templates" / "prd").mkdir(parents=True)
    (core_pack / "templates" / "prd" / "master-pack-template.md").write_text(
        "# PRD Master Pack\n",
        encoding="utf-8",
    )
    (core_pack / "command-partials" / "test").mkdir(parents=True)
    (core_pack / "command-partials" / "test" / "shell.md").write_text("shell\n", encoding="utf-8")
    (core_pack / "passive-skills" / "python-testing").mkdir(parents=True)
    (core_pack / "passive-skills" / "python-testing" / "SKILL.md").write_text("---\nname: python-testing\n---\n", encoding="utf-8")
    (core_pack / "project-map" / "root").mkdir(parents=True)
    (core_pack / "project-map" / "root" / "ARCHITECTURE.md").write_text("# Architecture\n", encoding="utf-8")
    (core_pack / "project-map" / "QUICK-NAV.md").write_text("# Quick Navigation\n", encoding="utf-8")
    (core_pack / "worker-prompts").mkdir(parents=True)
    (core_pack / "worker-prompts" / "implementer.md").write_text("# Implementer\n", encoding="utf-8")
    (core_pack / "shared_hooks").mkdir(parents=True)
    (core_pack / "shared_hooks" / "specify-hook").write_text("#!/usr/bin/env sh\n", encoding="utf-8")
    (core_pack / "shared_hooks" / "specify-hook.cmd").write_text("@echo off\n", encoding="utf-8")
    (core_pack / "shared_hooks" / "specify-hook.py").write_text("print('hook')\n", encoding="utf-8")
    (core_pack / "scripts" / "powershell").mkdir(parents=True)
    (core_pack / "scripts" / "powershell" / "common.ps1").write_text("# common\n", encoding="utf-8")

    monkeypatch.setattr("specify_cli._locate_core_pack", lambda: core_pack)

    project_root = tmp_path / "project"
    project_root.mkdir()

    assert _install_shared_infra(project_root, "ps") is True
    assert (project_root / ".specify" / "templates" / "testing" / "testing-contract-template.md").exists()
    assert (project_root / ".specify" / "templates" / "examples" / "deep-research" / "not-needed.md").exists()
    assert (project_root / ".specify" / "templates" / "prd" / "master-pack-template.md").exists()
    assert (project_root / ".specify" / "templates" / "command-partials" / "test" / "shell.md").exists()
    assert (project_root / ".specify" / "templates" / "passive-skills" / "python-testing" / "SKILL.md").exists()
    assert (project_root / ".specify" / "templates" / "project-map" / "QUICK-NAV.md").exists()
    assert (project_root / ".specify" / "templates" / "project-map" / "root" / "ARCHITECTURE.md").exists()
    assert (project_root / ".specify" / "templates" / "worker-prompts" / "implementer.md").exists()
    assert not (project_root / ".specify" / "bin" / "specify-hook.py").exists()
