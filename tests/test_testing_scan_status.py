from pathlib import Path

from specify_cli.scan_freshness import ScanFreshnessStatus, read_scan_status, write_scan_status
from specify_cli.testing_scan_status import (
    classify_testing_changed_files,
    classify_testing_changed_path,
    testing_status_path,
)


def test_testing_status_path_uses_project_testing_status_json(tmp_path: Path) -> None:
    assert testing_status_path(tmp_path) == tmp_path / ".specify" / "testing" / "status.json"


def test_testing_status_round_trip_uses_testing_family(tmp_path: Path) -> None:
    status = ScanFreshnessStatus(
        status_family="testing",
        freshness="fresh",
        last_refresh_commit="abc123",
        last_refresh_branch="main",
        last_refresh_at="2026-05-04T00:00:00Z",
        last_refresh_scope="full",
        last_refresh_basis="test-scan",
        last_refresh_changed_files_basis=["src/app.py", "tests/test_app.py"],
    )

    written = write_scan_status(testing_status_path(tmp_path), status)
    loaded = read_scan_status(written, status_family="testing")

    assert written == tmp_path / ".specify" / "testing" / "status.json"
    assert loaded.status_family == "testing"
    assert loaded.freshness == "fresh"
    assert loaded.last_refresh_basis == "test-scan"
    assert loaded.last_refresh_changed_files_basis == ["src/app.py", "tests/test_app.py"]


def test_testing_classifier_marks_global_test_surfaces_full_stale() -> None:
    full_stale_paths = [
        "pyproject.toml",
        "package.json",
        "go.mod",
        "Cargo.toml",
        "Cargo.lock",
        "uv.lock",
        ".github/workflows/ci.yml",
        "tox.ini",
        "noxfile.py",
        "setup.cfg",
        "pytest.ini",
        ".coveragerc",
        "jest.config.js",
    ]

    for path in full_stale_paths:
        assert classify_testing_changed_path(path) == "full-stale"


def test_testing_classifier_marks_module_local_code_and_tests_targeted_stale() -> None:
    assert classify_testing_changed_path("src/specify_cli/testing_inventory.py") == "targeted-stale"
    assert classify_testing_changed_path("tests/test_testing_inventory.py") == "targeted-stale"


def test_testing_classifier_normalizes_mixed_case_paths_before_matching() -> None:
    assert classify_testing_changed_path("PYPROJECT.TOML") == "full-stale"
    assert classify_testing_changed_path(".GITHUB/WORKFLOWS/CI.YML") == "full-stale"
    assert classify_testing_changed_path("SRC/Specify_Cli/App.py") == "targeted-stale"
    assert classify_testing_changed_path("Tests/Test_App.py") == "targeted-stale"


def test_testing_classifier_ignores_irrelevant_paths_and_empty_relevant_set_is_fresh() -> None:
    assert classify_testing_changed_path("README.md") == "ignore"

    result = classify_testing_changed_files(["README.md", "docs/notes.md"])

    assert result["freshness"] == "fresh"
    assert result["relevant_changed_files"] == []
    assert result["full_stale_files"] == []
    assert result["targeted_stale_files"] == []


def test_testing_classifier_prefers_full_stale_over_targeted_stale() -> None:
    result = classify_testing_changed_files(["src/app.py", "pyproject.toml"])

    assert result["freshness"] == "full-stale"
    assert result["full_stale_files"] == ["pyproject.toml"]
    assert result["targeted_stale_files"] == ["src/app.py"]
