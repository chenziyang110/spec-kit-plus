from pathlib import Path
import subprocess

from specify_cli.scan_freshness import (
    ScanFreshnessStatus,
    collect_git_changed_files,
    filter_cognition_ignored_paths,
    read_scan_status,
    write_scan_status,
)


def _init_git_repo(tmp_path: Path) -> Path:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=tmp_path, check=True)
    return tmp_path


def test_scan_status_round_trip_uses_shared_refresh_fields(tmp_path: Path) -> None:
    status_path = tmp_path / ".specify" / "testing" / "status.json"
    status = ScanFreshnessStatus(
        status_family="testing",
        version=1,
        freshness="fresh",
        last_refresh_commit="abc123",
        last_refresh_branch="main",
        last_refresh_at="2026-05-04T00:00:00Z",
        last_refresh_scope="full",
        last_refresh_basis="test-scan",
        last_refresh_changed_files_basis=["src/app.py"],
        manual_force_stale=False,
        manual_force_stale_reasons=[],
    )

    write_scan_status(status_path, status)
    loaded = read_scan_status(status_path, status_family="testing")

    assert loaded.status_family == "testing"
    assert loaded.last_refresh_commit == "abc123"
    assert loaded.last_refresh_branch == "main"
    assert loaded.last_refresh_at == "2026-05-04T00:00:00Z"
    assert loaded.last_refresh_scope == "full"
    assert loaded.last_refresh_basis == "test-scan"
    assert loaded.last_refresh_changed_files_basis == ["src/app.py"]
    assert loaded.manual_force_stale is False


def test_collect_git_changed_files_includes_committed_staged_unstaged_and_untracked(tmp_path: Path) -> None:
    repo = _init_git_repo(tmp_path)
    (repo / "seed.txt").write_text("seed\n", encoding="utf-8")
    (repo / "unstaged.txt").write_text("tracked before baseline\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "init", "-q"], cwd=repo, check=True)
    baseline = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    (repo / "committed.txt").write_text("committed\n", encoding="utf-8")
    subprocess.run(["git", "add", "committed.txt"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "committed", "-q"], cwd=repo, check=True)

    (repo / "staged.txt").write_text("staged\n", encoding="utf-8")
    subprocess.run(["git", "add", "staged.txt"], cwd=repo, check=True)

    (repo / "unstaged.txt").write_text("modified after baseline\n", encoding="utf-8")
    (repo / "untracked.txt").write_text("untracked\n", encoding="utf-8")

    changed = collect_git_changed_files(repo, baseline_commit=baseline)

    assert "committed.txt" in changed
    assert "staged.txt" in changed
    assert "unstaged.txt" in changed
    assert "untracked.txt" in changed


def test_cognitionignore_filters_paths_with_gitignore_like_rules(tmp_path: Path) -> None:
    repo = tmp_path
    ignore_file = repo / ".specify" / "project-cognition" / ".cognitionignore"
    ignore_file.parent.mkdir(parents=True)
    ignore_file.write_text(
        """
# generated dependency projects
vendor/
examples/**/*.generated.ts
*.snap
!tests/fixtures/keep.snap
""",
        encoding="utf-8",
    )

    filtered = filter_cognition_ignored_paths(
        repo,
        [
            "src/app.py",
            "vendor/nested/project.py",
            "examples/demo/app.generated.ts",
            "tests/ui/home.snap",
            "tests/fixtures/keep.snap",
        ],
    )

    assert filtered == [
        "src/app.py",
        "tests/fixtures/keep.snap",
    ]


def test_collect_git_changed_files_applies_cognitionignore_when_enabled(tmp_path: Path) -> None:
    repo = _init_git_repo(tmp_path)
    (repo / "seed.txt").write_text("seed\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "init", "-q"], cwd=repo, check=True)
    baseline = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    ignore_file = repo / ".specify" / "project-cognition" / ".cognitionignore"
    ignore_file.parent.mkdir(parents=True)
    ignore_file.write_text("vendor/\n*.snap\n!tests/fixtures/keep.snap\n", encoding="utf-8")

    (repo / "src").mkdir()
    (repo / "src" / "app.py").write_text("print('changed')\n", encoding="utf-8")
    (repo / "vendor").mkdir()
    (repo / "vendor" / "ignored.py").write_text("print('ignored')\n", encoding="utf-8")
    (repo / "tests" / "fixtures").mkdir(parents=True)
    (repo / "tests" / "fixtures" / "keep.snap").write_text("tracked fixture\n", encoding="utf-8")
    (repo / "tests" / "ui.snap").write_text("ignored snapshot\n", encoding="utf-8")

    changed = collect_git_changed_files(repo, baseline_commit=baseline, use_cognitionignore=True)

    assert "src/app.py" in changed
    assert "tests/fixtures/keep.snap" in changed
    assert "vendor/ignored.py" not in changed
    assert "tests/ui.snap" not in changed


def test_read_scan_status_can_migrate_legacy_project_map_fields(tmp_path: Path) -> None:
    status_path = tmp_path / ".specify" / "project-map" / "index" / "status.json"
    status_path.parent.mkdir(parents=True, exist_ok=True)
    status_path.write_text(
        """{
  "version": 1,
  "last_mapped_commit": "abc123",
  "last_mapped_branch": "main",
  "last_mapped_at": "2026-05-04T00:00:00Z",
  "freshness": "fresh",
  "dirty": true,
  "dirty_reasons": ["workflow_contract_changed"]
}
""",
        encoding="utf-8",
    )

    loaded = read_scan_status(status_path, status_family="project-map")

    assert loaded.last_refresh_commit == "abc123"
    assert loaded.last_refresh_branch == "main"
    assert loaded.last_refresh_at == "2026-05-04T00:00:00Z"
    assert loaded.manual_force_stale is True
    assert loaded.manual_force_stale_reasons == ["workflow_contract_changed"]
