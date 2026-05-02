from pathlib import Path

from specify_cli.hooks.engine import run_quality_hook


def _create_project(tmp_path: Path) -> Path:
    project = tmp_path / "prd-hook-project"
    project.mkdir()
    (project / ".specify").mkdir()
    return project


def _write_prd_workflow_state(run_dir: Path) -> None:
    (run_dir / "workflow-state.md").write_text(
        "\n".join(
            [
                "# Workflow State: PRD Demo",
                "",
                "## Current Command",
                "",
                "- active_command: `sp-prd`",
                "- status: `active`",
                "",
                "## Phase Mode",
                "",
                "- phase_mode: `analysis-only`",
                "- summary: reverse PRD extraction only",
                "",
                "## Next Action",
                "",
                "- finish export completeness checks",
                "",
                "## Next Command",
                "",
                "- `/sp.prd`",
                "",
            ]
        ),
        encoding="utf-8",
    )


def _write_complete_prd_artifacts(run_dir: Path) -> None:
    _write_prd_workflow_state(run_dir)
    (run_dir / "coverage-matrix.md").write_text(
        "\n".join(
            [
                "# Coverage Matrix",
                "",
                "| Capability | Tier | Evidence Status | Depth Status | Export Destinations | Overall Status |",
                "|------------|------|-----------------|--------------|---------------------|----------------|",
                "| Config Management | critical | Evidence | depth-qualified | prd.md | depth-qualified |",
            ]
        ),
        encoding="utf-8",
    )
    master_dir = run_dir / "master"
    master_dir.mkdir()
    (master_dir / "master-pack.md").write_text(
        "\n".join(
            [
                "# Master Pack",
                "",
                "## Capability Inventory",
                "",
                "## Critical Capability Dossiers",
                "",
                "### CAP-001 Config Management",
                "",
                "#### Implementation Mechanisms",
                "",
                "#### Source Traceability",
                "",
                "## Coverage and Export Map",
            ]
        ),
        encoding="utf-8",
    )
    exports_dir = run_dir / "exports"
    exports_dir.mkdir()
    (exports_dir / "prd.md").write_text(
        "\n".join(
            [
                "# PRD",
                "",
                "**Derived From**: `master/master-pack.md`",
                "",
                "## Capability Overview",
                "",
                "## Critical Capability Notes",
                "",
                "## Unknowns and Evidence Confidence",
            ]
        ),
        encoding="utf-8",
    )
    (master_dir / "exports").mkdir()


def test_prd_state_validation_accepts_analysis_only_workflow_state(tmp_path: Path):
    project = _create_project(tmp_path)
    run_dir = project / ".specify" / "prd-runs" / "260502-demo-prd"
    run_dir.mkdir(parents=True, exist_ok=True)
    _write_prd_workflow_state(run_dir)

    result = run_quality_hook(
        project,
        "workflow.state.validate",
        {"command_name": "prd", "feature_dir": str(run_dir)},
    )

    assert result.status == "ok"
    assert result.errors == []
    assert result.data["checkpoint"]["active_command"] == "sp-prd"
    assert result.data["checkpoint"]["phase_mode"] == "analysis-only"


def test_prd_state_validation_blocks_wrong_phase_mode(tmp_path: Path):
    project = _create_project(tmp_path)
    run_dir = project / ".specify" / "prd-runs" / "260502-demo-prd"
    run_dir.mkdir(parents=True, exist_ok=True)
    _write_prd_workflow_state(run_dir)
    content = (run_dir / "workflow-state.md").read_text(encoding="utf-8")
    (run_dir / "workflow-state.md").write_text(
        content.replace("analysis-only", "planning-only"),
        encoding="utf-8",
    )

    result = run_quality_hook(
        project,
        "workflow.state.validate",
        {"command_name": "prd", "feature_dir": str(run_dir)},
    )

    assert result.status == "blocked"
    assert any("phase_mode" in message for message in result.errors)


def test_prd_artifact_validation_blocks_missing_prd_suite_artifacts(tmp_path: Path):
    project = _create_project(tmp_path)
    run_dir = project / ".specify" / "prd-runs" / "260502-demo-prd"
    run_dir.mkdir(parents=True, exist_ok=True)
    _write_prd_workflow_state(run_dir)

    result = run_quality_hook(
        project,
        "workflow.artifacts.validate",
        {"command_name": "prd", "feature_dir": str(run_dir)},
    )

    assert result.status == "blocked"
    assert any("coverage-matrix.md" in message for message in result.errors)
    assert any("master/master-pack.md" in message for message in result.errors)
    assert any("exports/prd.md" in message for message in result.errors)
    assert any("master/exports" in message for message in result.errors)


def test_prd_artifact_validation_requires_master_exports_directory(tmp_path: Path):
    project = _create_project(tmp_path)
    run_dir = project / ".specify" / "prd-runs" / "260502-demo-prd"
    run_dir.mkdir(parents=True, exist_ok=True)
    _write_complete_prd_artifacts(run_dir)
    master_exports_dir = run_dir / "master" / "exports"
    master_exports_dir.rmdir()
    master_exports_dir.write_text("not a directory\n", encoding="utf-8")

    result = run_quality_hook(
        project,
        "workflow.artifacts.validate",
        {"command_name": "prd", "feature_dir": str(run_dir)},
    )

    assert result.status == "blocked"
    assert any("master/exports must be a directory" in message for message in result.errors)


def test_prd_artifact_validation_accepts_complete_prd_suite(tmp_path: Path):
    project = _create_project(tmp_path)
    run_dir = project / ".specify" / "prd-runs" / "260502-demo-prd"
    run_dir.mkdir(parents=True, exist_ok=True)
    _write_complete_prd_artifacts(run_dir)

    result = run_quality_hook(
        project,
        "workflow.artifacts.validate",
        {"command_name": "prd", "feature_dir": str(run_dir)},
    )

    assert result.status == "ok"
    assert result.errors == []


def test_prd_artifact_validation_blocks_missing_depth_aware_sections(tmp_path: Path):
    project = _create_project(tmp_path)
    run_dir = project / ".specify" / "prd-runs" / "260503-depth-gap-prd"
    run_dir.mkdir(parents=True, exist_ok=True)
    _write_prd_workflow_state(run_dir)
    (run_dir / "coverage-matrix.md").write_text("# Coverage Matrix\n", encoding="utf-8")
    master_dir = run_dir / "master"
    master_dir.mkdir()
    (master_dir / "master-pack.md").write_text("# Master Pack\n", encoding="utf-8")
    (master_dir / "exports").mkdir()
    exports_dir = run_dir / "exports"
    exports_dir.mkdir()
    (exports_dir / "prd.md").write_text("# PRD\n", encoding="utf-8")

    result = run_quality_hook(
        project,
        "workflow.artifacts.validate",
        {"command_name": "prd", "feature_dir": str(run_dir)},
    )

    assert result.status == "blocked"
    assert any("coverage-matrix.md is missing depth-aware columns" in message for message in result.errors)
    assert any("master/master-pack.md is missing required section" in message for message in result.errors)
    assert any("exports/prd.md is missing required section" in message for message in result.errors)
