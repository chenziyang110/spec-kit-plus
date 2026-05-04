from pathlib import Path

from specify_cli.prd_scan_status import (
    classify_prd_changed_files,
    classify_prd_changed_path,
    prd_status_path,
)
from specify_cli.scan_freshness import ScanFreshnessStatus, read_scan_status, write_scan_status


def test_prd_status_path_uses_project_prd_status_json(tmp_path: Path) -> None:
    assert prd_status_path(tmp_path) == tmp_path / ".specify" / "prd" / "status.json"


def test_prd_status_round_trip_uses_prd_family(tmp_path: Path) -> None:
    status = ScanFreshnessStatus(
        status_family="prd",
        freshness="fresh",
        last_refresh_commit="abc123",
        last_refresh_branch="main",
        last_refresh_at="2026-05-04T00:00:00Z",
        last_refresh_scope="full",
        last_refresh_basis="prd-scan",
        last_refresh_changed_files_basis=["src/app.py", "README.md"],
    )

    written = write_scan_status(prd_status_path(tmp_path), status)
    loaded = read_scan_status(written, status_family="prd")

    assert written == tmp_path / ".specify" / "prd" / "status.json"
    assert loaded.status_family == "prd"
    assert loaded.freshness == "fresh"
    assert loaded.last_refresh_basis == "prd-scan"
    assert loaded.last_refresh_changed_files_basis == ["src/app.py", "README.md"]


def test_prd_classifier_marks_global_workflow_surfaces_full_stale() -> None:
    full_stale_paths = [
        "templates/commands/prd-scan.md",
        "templates/command-partials/prd/shell.md",
        "src/specify_cli/__init__.py",
        "src/specify_cli/agents.py",
        "src/specify_cli/launcher.py",
        "src/specify_cli/workflow_markers.py",
        "src/specify_cli/integrations/codex/__init__.py",
        "src/specify_cli/hooks/artifact_validation.py",
        "src/specify_cli/orchestration/policy.py",
        "scripts/bash/prd-state.sh",
        "scripts/powershell/update-agent-context.ps1",
        ".github/workflows/release.yml",
        "pyproject.toml",
        "package.json",
        "uv.lock",
        "AGENTS.md",
        "PROJECT-HANDBOOK.md",
    ]

    for path in full_stale_paths:
        assert classify_prd_changed_path(path) == "full-stale"


def test_prd_classifier_marks_bounded_source_test_and_doc_changes_targeted_stale() -> None:
    assert classify_prd_changed_path("src/specify_cli/prd_scan_status.py") == "targeted-stale"
    assert classify_prd_changed_path("tests/test_prd_scan_status.py") == "targeted-stale"
    assert classify_prd_changed_path("README.md") == "targeted-stale"
    assert classify_prd_changed_path("docs/operators/prd.md") == "targeted-stale"
    assert classify_prd_changed_path("templates/project-handbook-template.md") == "targeted-stale"


def test_prd_classifier_normalizes_mixed_case_paths_before_matching() -> None:
    assert classify_prd_changed_path("TEMPLATES/COMMANDS/PRD-SCAN.MD") == "full-stale"
    assert classify_prd_changed_path(".GITHUB/WORKFLOWS/CI.YML") == "full-stale"
    assert classify_prd_changed_path("SRC/Specify_Cli/App.py") == "targeted-stale"
    assert classify_prd_changed_path("Tests/Test_PRD.py") == "targeted-stale"
    assert classify_prd_changed_path("Docs/PRD/Notes.MD") == "targeted-stale"


def test_prd_classifier_ignores_irrelevant_paths_and_empty_relevant_set_is_fresh() -> None:
    assert classify_prd_changed_path("newsletters/issue.md") == "ignore"

    result = classify_prd_changed_files(["newsletters/issue.md", "plans/local-note.md"])

    assert result["freshness"] == "fresh"
    assert result["relevant_changed_files"] == []
    assert result["full_stale_files"] == []
    assert result["targeted_stale_files"] == []


def test_prd_classifier_prefers_full_stale_over_targeted_stale() -> None:
    result = classify_prd_changed_files(["src/app.py", "templates/commands/prd-scan.md"])

    assert result["freshness"] == "full-stale"
    assert result["full_stale_files"] == ["templates/commands/prd-scan.md"]
    assert result["targeted_stale_files"] == ["src/app.py"]
