import json
import shutil
import subprocess
import tomllib
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent


def _read(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def _read_command_surface(command_name: str) -> str:
    parts = [_read(f"templates/commands/{command_name}.md")]
    references_dir = REPO_ROOT / "templates" / "command-references" / command_name
    if references_dir.is_dir():
        parts.extend(
            path.read_text(encoding="utf-8")
            for path in sorted(references_dir.glob("*.md"))
        )
    return "\n\n".join(parts)


def test_wheel_force_include_bundles_passive_skills() -> None:
    pyproject = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")

    assert '"templates/passive-skills" = "specify_cli/core_pack/passive-skills"' in pyproject


def test_design_assets_are_packaged() -> None:
    pyproject = _read("pyproject.toml")

    assert '"templates/design-template.md" = "specify_cli/core_pack/templates/design-template.md"' in pyproject
    assert '"templates/design-library" = "specify_cli/core_pack/templates/design-library"' in pyproject


def test_cli_dependency_metadata_pins_pydantic_graph_base_node_api() -> None:
    pyproject = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    dependencies = pyproject["project"]["dependencies"]

    assert "pydantic-graph<2" in dependencies


def test_wheel_force_include_bundles_command_partials_and_prd_templates() -> None:
    pyproject = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")

    assert '"templates/command-partials" = "specify_cli/core_pack/command-partials"' in pyproject
    assert '"templates/command-references" = "specify_cli/core_pack/command-references"' in pyproject
    assert '"templates/prd" = "specify_cli/core_pack/templates/prd"' in pyproject
    assert '"templates/testing" = "specify_cli/core_pack/templates/testing"' not in pyproject


def test_wheel_force_include_covers_deep_research_planning_handoff_contract() -> None:
    pyproject = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    deep_research = (REPO_ROOT / "templates" / "commands" / "deep-research.md").read_text(encoding="utf-8")
    plan = _read_command_surface("plan")
    shell_partial = (
        REPO_ROOT / "templates" / "command-partials" / "deep-research" / "shell.md"
    ).read_text(encoding="utf-8")

    assert '"templates/commands" = "specify_cli/core_pack/commands"' in pyproject
    assert '"templates/command-partials" = "specify_cli/core_pack/command-partials"' in pyproject
    assert "Traceability and Evidence Quality Contract" in deep_research
    assert "Planning Handoff" in deep_research
    assert "PH-001" in deep_research
    assert "CAP-001" in deep_research
    assert "deep-research `PH-###` traceability" in plan
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


def test_semantic_audit_resume_examples_are_bundled_with_templates() -> None:
    pyproject = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    examples_dir = REPO_ROOT / "templates" / "examples" / "semantic-audit-resume"
    scenarios = examples_dir / "scenarios.md"
    resume_validation = examples_dir / "resume-validation.json"
    route_changed_validation = examples_dir / "resume-validation-route-changed.json"
    active_claim_validation = examples_dir / "resume-validation-active-claim-changed.json"
    missing_file_validation = examples_dir / "resume-validation-missing-file.json"
    claim_ref_validation = examples_dir / "resume-validation-claim-ref-mismatch.json"
    verification_ref_validation = examples_dir / "resume-validation-verification-ref-mismatch.json"
    audit_input = examples_dir / "semantic-audit-input.json"
    audit_output = examples_dir / "semantic-audit-output.json"

    assert '"templates/examples" = "specify_cli/core_pack/templates/examples"' in pyproject
    assert scenarios.exists()
    assert resume_validation.exists()
    assert route_changed_validation.exists()
    assert active_claim_validation.exists()
    assert missing_file_validation.exists()
    assert claim_ref_validation.exists()
    assert verification_ref_validation.exists()
    assert audit_input.exists()
    assert audit_output.exists()

    content = scenarios.read_text(encoding="utf-8")
    assert "Semantic Audit Resume Examples" in content
    assert "fresh" in content
    assert "missing-file" in content
    assert "route-changed" in content
    assert "active-claim-changed" in content
    assert "claim-ref-mismatch" in content
    assert "verification-ref-mismatch" in content
    assert "resume-validation.json" in content
    assert "resume-validation-route-changed.json" in content
    assert "resume-validation-active-claim-changed.json" in content
    assert "resume-validation-missing-file.json" in content
    assert "resume-validation-claim-ref-mismatch.json" in content
    assert "resume-validation-verification-ref-mismatch.json" in content

    payload = json.loads(resume_validation.read_text(encoding="utf-8"))
    state = payload["workflow_state"]
    assert state["semantic_audit_input_path"] == "semantic-audit-input.json"
    assert state["semantic_audit_output_path"] == "semantic-audit-output.json"
    assert state["semantic_audit_route_fingerprint"] == "semantic-audit-route:v1:bab591a662cd55d2"
    assert state["active_claim_type"] == "root_cause_claim"
    assert state["selected_candidate_ids"] == ["environment-settings-page"]
    assert state["claim_authorization_refs"] == ["workflow:debug#root-cause-reviewed"]
    assert state["claim_verification_refs"] == ["test:EnvironmentSettings.test.tsx#passed"]


def test_semantic_audit_resume_validator_examples_execute_when_go_is_available() -> None:
    if shutil.which("go") is None:
        pytest.skip("Go toolchain unavailable")

    examples_dir = REPO_ROOT / "templates" / "examples" / "semantic-audit-resume"
    runtime_dir = REPO_ROOT / "tools" / "project-cognition"

    fresh = subprocess.run(
        ["go", "run", ".", "semantic-audit-resume", "--input", str(examples_dir / "resume-validation.json"), "--format", "json"],
        cwd=runtime_dir,
        capture_output=True,
        check=False,
        encoding="utf-8",
        errors="replace",
        text=True,
        timeout=60,
    )
    assert fresh.returncode == 0, fresh.stderr
    fresh_payload = json.loads(fresh.stdout)
    assert fresh_payload["semantic_audit_generated_resume_smoke"] == "passed"
    assert fresh_payload["semantic_audit_resume_status"] == "fresh"
    assert fresh_payload["can_reuse_persisted_claim_readiness"] is True
    assert fresh_payload["grants_permission"] is False

    route_changed = subprocess.run(
        [
            "go",
            "run",
            ".",
            "semantic-audit-resume",
            "--input",
            str(examples_dir / "resume-validation-route-changed.json"),
            "--format",
            "json",
        ],
        cwd=runtime_dir,
        capture_output=True,
        check=False,
        encoding="utf-8",
        errors="replace",
        text=True,
        timeout=60,
    )
    assert route_changed.returncode == 0, route_changed.stderr
    route_changed_payload = json.loads(route_changed.stdout)
    assert route_changed_payload["semantic_audit_generated_resume_smoke"] == "failed"
    assert route_changed_payload["semantic_audit_resume_status"] == "needs-rerun"
    assert route_changed_payload["semantic_audit_stale_reasons"] == ["route-changed"]
    assert route_changed_payload["can_reuse_persisted_claim_readiness"] is False
    assert route_changed_payload["grants_permission"] is False

    stale_fixtures = {
        "resume-validation-active-claim-changed.json": [
            "active-claim-changed",
            "route-changed",
        ],
        "resume-validation-missing-file.json": [
            "missing-file",
        ],
        "resume-validation-claim-ref-mismatch.json": [
            "claim-ref-mismatch",
        ],
        "resume-validation-verification-ref-mismatch.json": [
            "verification-ref-mismatch",
        ],
    }
    for fixture, expected_reasons in stale_fixtures.items():
        result = subprocess.run(
            [
                "go",
                "run",
                ".",
                "semantic-audit-resume",
                "--input",
                str(examples_dir / fixture),
                "--format",
                "json",
            ],
            cwd=runtime_dir,
            capture_output=True,
            check=False,
            encoding="utf-8",
            errors="replace",
            text=True,
            timeout=60,
        )
        assert result.returncode == 0, result.stderr
        payload = json.loads(result.stdout)
        assert payload["semantic_audit_generated_resume_smoke"] == "failed"
        assert payload["semantic_audit_resume_status"] == "needs-rerun"
        assert payload["semantic_audit_stale_reasons"] == expected_reasons
        assert payload["can_reuse_persisted_claim_readiness"] is False
        assert payload["grants_permission"] is False


def test_wheel_force_include_bundles_workflow_state_template() -> None:
    pyproject = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")

    assert (
        '"templates/workflow-state-template.md" = '
        '"specify_cli/core_pack/templates/workflow-state-template.md"'
    ) in pyproject


def test_wheel_force_include_bundles_structured_workflow_contract_templates() -> None:
    pyproject = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")

    for template in (
        "plan-contract-template.json",
        "task-index-template.json",
        "task-packet-template.json",
    ):
        assert (
            f'"templates/{template}" = '
            f'"specify_cli/core_pack/templates/{template}"'
        ) in pyproject


def test_wheel_force_include_bundles_artifact_scaffold_templates() -> None:
    pyproject = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")

    assert '"templates/artifacts" = "specify_cli/core_pack/templates/artifacts"' in pyproject
    assert (REPO_ROOT / "templates" / "artifacts" / "quick-status.md").exists()


def test_ui_reference_artifact_templates_are_packaged() -> None:
    pyproject = _read("pyproject.toml")

    assert '"templates/ui-reference-notes-template.md" = "specify_cli/core_pack/templates/ui-reference-notes-template.md"' in pyproject
    assert '"templates/ui-brief-template.md" = "specify_cli/core_pack/templates/ui-brief-template.md"' in pyproject
    assert '"templates/ui-target-template.html" = "specify_cli/core_pack/templates/ui-target-template.html"' in pyproject


def test_lossless_specify_state_templates_are_force_included() -> None:
    pyproject = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    for template in (
        "templates/brainstorming-stage-manifest-template.json",
        "templates/brainstorming-domains-template.json",
        "templates/brainstorming-evidence-index-template.json",
        "templates/brainstorming-evidence-record-template.json",
    ):
        assert f'"{template}" = ' in pyproject


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


def test_wheel_force_include_bundles_shared_prd_state_helper() -> None:
    pyproject = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")

    assert '"scripts/shared" = "specify_cli/core_pack/scripts/shared"' in pyproject


def test_wheel_force_include_bundles_project_cognition_source() -> None:
    pyproject = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")

    assert (
        '"tools/project-cognition" = '
        '"specify_cli/core_pack/tools/project-cognition"'
    ) in pyproject


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
    (core_pack / "templates" / "artifacts").mkdir(parents=True)
    (core_pack / "templates" / "artifacts" / "quick-status.md").write_text(
        "# Quick Status\n",
        encoding="utf-8",
    )
    (core_pack / "templates" / "design-template.md").write_text("# Design\n", encoding="utf-8")
    (core_pack / "templates" / "ui-reference-notes-template.md").write_text("# UI Reference Notes\n", encoding="utf-8")
    (core_pack / "templates" / "ui-brief-template.md").write_text("# UI Brief\n", encoding="utf-8")
    (core_pack / "templates" / "ui-target-template.html").write_text("<!doctype html>\n", encoding="utf-8")
    (core_pack / "templates" / "design-library").mkdir(parents=True)
    (core_pack / "templates" / "design-library" / "workbench-precision.md").write_text(
        "# Workbench Precision\n",
        encoding="utf-8",
    )
    (core_pack / "command-partials" / "test").mkdir(parents=True)
    (core_pack / "command-partials" / "test" / "shell.md").write_text("shell\n", encoding="utf-8")
    (core_pack / "command-references" / "plan").mkdir(parents=True)
    (core_pack / "command-references" / "plan" / "INDEX.md").write_text("# Plan References\n", encoding="utf-8")
    (core_pack / "passive-skills" / "python-testing").mkdir(parents=True)
    (core_pack / "passive-skills" / "python-testing" / "SKILL.md").write_text("---\nname: python-testing\n---\n", encoding="utf-8")
    (core_pack / "project-map" / "root").mkdir(parents=True)
    (core_pack / "project-map" / "root" / "ARCHITECTURE.md").write_text("# Architecture\n", encoding="utf-8")
    (core_pack / "project-map" / "QUICK-NAV.md").write_text("# Quick Navigation\n", encoding="utf-8")
    (core_pack / "worker-prompts").mkdir(parents=True)
    (core_pack / "worker-prompts" / "implementer.md").write_text("# Implementer\n", encoding="utf-8")
    (core_pack / "worker-prompts" / "task-reviewer.md").write_text("# Task Reviewer\n", encoding="utf-8")
    (core_pack / "shared_hooks").mkdir(parents=True)
    (core_pack / "shared_hooks" / "specify-hook").write_text("#!/usr/bin/env sh\n", encoding="utf-8")
    (core_pack / "shared_hooks" / "specify-hook.cmd").write_text("@echo off\n", encoding="utf-8")
    (core_pack / "shared_hooks" / "specify-hook.mjs").write_text("console.log('hook')\n", encoding="utf-8")
    (core_pack / "shared_hooks" / "specify-hook.py").write_text("print('hook')\n", encoding="utf-8")
    (core_pack / "scripts" / "powershell").mkdir(parents=True)
    (core_pack / "scripts" / "powershell" / "common.ps1").write_text("# common\n", encoding="utf-8")
    (core_pack / "scripts" / "shared").mkdir(parents=True)
    (core_pack / "scripts" / "shared" / "prd-state.py").write_text("print('prd')\n", encoding="utf-8")

    monkeypatch.setattr("specify_cli._locate_core_pack", lambda: core_pack)

    project_root = tmp_path / "project"
    project_root.mkdir()

    assert _install_shared_infra(project_root, "ps") is True
    assert (project_root / ".specify" / "templates" / "testing" / "testing-contract-template.md").exists()
    assert (project_root / ".specify" / "templates" / "examples" / "deep-research" / "not-needed.md").exists()
    assert (project_root / ".specify" / "templates" / "prd" / "master-pack-template.md").exists()
    assert (project_root / ".specify" / "templates" / "artifacts" / "quick-status.md").exists()
    assert (project_root / ".specify" / "templates" / "design-template.md").exists()
    assert (project_root / ".specify" / "templates" / "ui-reference-notes-template.md").exists()
    assert (project_root / ".specify" / "templates" / "ui-brief-template.md").exists()
    assert (project_root / ".specify" / "templates" / "ui-target-template.html").exists()
    assert (
        project_root
        / ".specify"
        / "templates"
        / "design-library"
        / "workbench-precision.md"
    ).exists()
    assert (project_root / "DESIGN.md").exists()
    assert (project_root / "DESIGN.md").read_text(encoding="utf-8") == "# Design\n"
    assert (project_root / ".specify" / "templates" / "command-partials" / "test" / "shell.md").exists()
    assert (project_root / ".specify" / "templates" / "command-references" / "plan" / "INDEX.md").exists()
    assert (project_root / ".specify" / "templates" / "passive-skills" / "python-testing" / "SKILL.md").exists()
    assert not (project_root / ".specify" / "templates" / "project-map" / "QUICK-NAV.md").exists()
    assert not (project_root / ".specify" / "templates" / "project-map" / "root" / "ARCHITECTURE.md").exists()
    assert (project_root / ".specify" / "templates" / "worker-prompts" / "implementer.md").exists()
    assert (project_root / ".specify" / "templates" / "worker-prompts" / "task-reviewer.md").exists()
    assert (project_root / ".specify" / "scripts" / "shared" / "prd-state.py").exists()
    assert not (project_root / ".specify" / "bin" / "specify-hook.mjs").exists()
    assert not (project_root / ".specify" / "bin" / "specify-hook.py").exists()


def test_install_shared_infra_preserves_existing_design_md(tmp_path, monkeypatch) -> None:
    from specify_cli import _install_shared_infra

    core_pack = tmp_path / "core_pack"
    (core_pack / "templates").mkdir(parents=True)
    (core_pack / "templates" / "design-template.md").write_text("# New Design\n", encoding="utf-8")
    (core_pack / "scripts" / "powershell").mkdir(parents=True)

    monkeypatch.setattr("specify_cli._locate_core_pack", lambda: core_pack)

    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / "DESIGN.md").write_text("# Existing Design\n", encoding="utf-8")

    assert _install_shared_infra(project_root, "ps") is True
    assert (project_root / "DESIGN.md").read_text(encoding="utf-8") == "# Existing Design\n"
