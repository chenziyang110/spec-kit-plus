import json
import shutil
import subprocess
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parent.parent
BASH_COMMON = PROJECT_ROOT / "scripts" / "bash" / "common.sh"
BASH_HELPER = PROJECT_ROOT / "scripts" / "bash" / "project-map-freshness.sh"
PS_COMMON = PROJECT_ROOT / "scripts" / "powershell" / "common.ps1"
PS_HELPER = PROJECT_ROOT / "scripts" / "powershell" / "project-map-freshness.ps1"


@pytest.fixture
def git_repo(tmp_path: Path) -> Path:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=tmp_path, check=True)
    (tmp_path / ".specify").mkdir()

    bash_dir = tmp_path / "scripts" / "bash"
    bash_dir.mkdir(parents=True)
    shutil.copy(BASH_COMMON, bash_dir / "common.sh")
    shutil.copy(BASH_HELPER, bash_dir / "project-map-freshness.sh")

    ps_dir = tmp_path / "scripts" / "powershell"
    ps_dir.mkdir(parents=True)
    shutil.copy(PS_COMMON, ps_dir / "common.ps1")
    shutil.copy(PS_HELPER, ps_dir / "project-map-freshness.ps1")

    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "--allow-empty", "-m", "init", "-q"], cwd=tmp_path, check=True)
    return tmp_path


def _run_bash(repo: Path, *args: str) -> dict:
    if not shutil.which("bash"):
        pytest.skip("bash not available")
    result = subprocess.run(
        ["bash", "scripts/bash/project-map-freshness.sh", ".", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return json.loads(result.stdout)


def _run_bash_raw(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    if not shutil.which("bash"):
        pytest.skip("bash not available")
    return subprocess.run(
        ["bash", "scripts/bash/project-map-freshness.sh", ".", *args],
        cwd=repo,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def _run_powershell(repo: Path, *args: str) -> dict:
    shell = shutil.which("pwsh") or shutil.which("powershell")
    if not shell:
        pytest.skip("PowerShell not available")
    result = subprocess.run(
        [shell, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "scripts/powershell/project-map-freshness.ps1", "-RepoRoot", str(repo), "-Command", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)


def _seed_canonical_map(repo: Path) -> None:
    (repo / "PROJECT-HANDBOOK.md").write_text("# Handbook\n", encoding="utf-8")
    project_map_dir = repo / ".specify" / "project-map"
    project_map_dir.mkdir(parents=True, exist_ok=True)
    index_dir = project_map_dir / "index"
    root_dir = project_map_dir / "root"
    (project_map_dir / "QUICK-NAV.md").write_text("# Quick Navigation\n", encoding="utf-8")
    index_dir.mkdir(parents=True, exist_ok=True)
    root_dir.mkdir(parents=True, exist_ok=True)
    (index_dir / "atlas-index.json").write_text("{}\n", encoding="utf-8")
    (index_dir / "modules.json").write_text('{"modules":[]}\n', encoding="utf-8")
    (index_dir / "relations.json").write_text('{"relations":[]}\n', encoding="utf-8")
    for name in (
        "ARCHITECTURE.md",
        "STRUCTURE.md",
        "CONVENTIONS.md",
        "INTEGRATIONS.md",
        "WORKFLOWS.md",
        "TESTING.md",
        "OPERATIONS.md",
    ):
        (root_dir / name).write_text(f"# {name}\n", encoding="utf-8")


def _commit_seeded_map(repo: Path) -> None:
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "seed canonical map", "-q"], cwd=repo, check=True)


def _seed_legacy_status(repo: Path, *, dirty: bool = True, dirty_reasons: list[str] | None = None) -> Path:
    reasons = dirty_reasons if dirty_reasons is not None else (["workflow_contract_changed"] if dirty else [])
    status_path = repo / ".specify" / "project-map" / "status.json"
    status_path.parent.mkdir(parents=True, exist_ok=True)
    status_path.write_text(
        json.dumps(
            {
                "version": 1,
                "last_mapped_commit": "",
                "last_mapped_at": "2026-04-21T00:00:00Z",
                "last_mapped_branch": "main",
                "freshness": "stale" if dirty else "fresh",
                "last_refresh_reason": "manual",
                "last_refresh_topics": [],
                "last_refresh_scope": "full",
                "last_refresh_basis": "manual",
                "last_refresh_changed_files_basis": [],
                "dirty": dirty,
                "dirty_reasons": reasons,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return status_path


def test_bash_project_map_freshness_lifecycle(git_repo: Path):
    missing = _run_bash(git_repo, "check")
    assert missing["freshness"] == "missing"

    _seed_canonical_map(git_repo)
    _commit_seeded_map(git_repo)
    refreshed = _run_bash(git_repo, "record-refresh", "manual")
    assert refreshed["freshness"] == "fresh"
    assert refreshed["status_path"].endswith(".specify/project-map/index/status.json")

    dirty = _run_bash(
        git_repo,
        "mark-dirty",
        "shared_surface_changed",
        "implement",
        "specs/001-demo",
        "lane-001",
    )
    assert dirty["freshness"] == "stale"
    assert dirty["dirty"] is True
    assert dirty["dirty_reasons"] == ["shared_surface_changed"]
    assert dirty["dirty_origin_command"] == "implement"
    assert dirty["dirty_origin_feature_dir"] == "specs/001-demo"
    assert dirty["dirty_origin_lane_id"] == "lane-001"
    assert dirty["dirty_scope_paths"] == []
    assert dirty["must_refresh_topics"] == ["ARCHITECTURE.md", "STRUCTURE.md"]
    assert dirty["review_topics"] == ["INTEGRATIONS.md", "WORKFLOWS.md", "TESTING.md"]


def test_bash_check_reads_legacy_project_map_status(git_repo: Path):
    _seed_legacy_status(git_repo)

    result = _run_bash(git_repo, "check")

    assert result["freshness"] == "stale"
    assert result["dirty"] is True
    assert result["dirty_reasons"] == ["workflow_contract_changed"]
    assert result["status_path"].endswith(".specify/project-map/index/status.json")
    assert result["suggested_topics"] == ["ARCHITECTURE.md", "INTEGRATIONS.md", "WORKFLOWS.md", "TESTING.md"]


def test_bash_mark_dirty_migrates_legacy_status_to_canonical_path(git_repo: Path):
    _seed_legacy_status(git_repo, dirty=False)

    result = _run_bash(git_repo, "mark-dirty", "shared_surface_changed")

    assert result["freshness"] == "stale"
    assert (git_repo / ".specify" / "project-map" / "index" / "status.json").exists()
    payload = json.loads((git_repo / ".specify" / "project-map" / "status.json").read_text(encoding="utf-8"))
    assert payload["dirty_reasons"] == ["shared_surface_changed"]


def test_powershell_project_map_freshness_detects_git_changes(git_repo: Path):
    _seed_canonical_map(git_repo)
    _commit_seeded_map(git_repo)
    refreshed = _run_powershell(git_repo, "record-refresh", "manual")
    assert refreshed["freshness"] == "fresh"

    changed = git_repo / "src" / "router.ts"
    changed.parent.mkdir(parents=True, exist_ok=True)
    changed.write_text("export const route = true;\n", encoding="utf-8")
    subprocess.run(["git", "add", "src/router.ts"], cwd=git_repo, check=True)

    stale = _run_powershell(git_repo, "check")
    assert stale["freshness"] == "stale"
    assert any("high-impact project-map change" in reason for reason in stale["reasons"])
    assert stale["must_refresh_topics"] == ["INTEGRATIONS.md", "WORKFLOWS.md"]
    assert stale["review_topics"] == ["ARCHITECTURE.md", "TESTING.md"]
    assert stale["suggested_topics"] == ["ARCHITECTURE.md", "INTEGRATIONS.md", "WORKFLOWS.md", "TESTING.md"]


def test_project_map_runtime_state_changes_do_not_mark_atlas_stale(git_repo: Path):
    _seed_canonical_map(git_repo)
    _commit_seeded_map(git_repo)

    _run_bash(git_repo, "record-refresh", "manual")
    state_file = git_repo / ".specify" / "project-map" / "map-state.md"
    worker_result = git_repo / ".specify" / "project-map" / "worker-results" / "SCAN-core.json"
    worker_result.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text("# state\n", encoding="utf-8")
    worker_result.write_text('{"status":"done"}\n', encoding="utf-8")
    subprocess.run(["git", "add", ".specify/project-map/map-state.md", ".specify/project-map/worker-results/SCAN-core.json"], cwd=git_repo, check=True)

    bash_result = _run_bash(git_repo, "check")
    assert bash_result["freshness"] == "fresh"
    assert bash_result["reasons"] == []

    powershell_result = _run_powershell(git_repo, "check")
    assert powershell_result["freshness"] == "fresh"
    assert powershell_result["reasons"] == []


def test_powershell_check_reads_legacy_project_map_status(git_repo: Path):
    _seed_legacy_status(git_repo)

    result = _run_powershell(git_repo, "check")

    assert result["freshness"] == "stale"
    assert result["dirty"] is True
    assert result["dirty_reasons"] == ["workflow_contract_changed"]
    assert result["status_path"].replace("\\", "/").endswith(".specify/project-map/index/status.json")
    assert result["suggested_topics"] == ["ARCHITECTURE.md", "INTEGRATIONS.md", "WORKFLOWS.md", "TESTING.md"]


def test_dirty_topic_order_is_stable_across_shell_helpers(git_repo: Path):
    _seed_legacy_status(
        git_repo,
        dirty_reasons=["project_map_dirty", "workflow_contract_changed"],
    )

    expected_must = ["ARCHITECTURE.md", "WORKFLOWS.md"]
    expected_review = ["ARCHITECTURE.md", "INTEGRATIONS.md", "TESTING.md"]
    expected_suggested = ["ARCHITECTURE.md", "INTEGRATIONS.md", "WORKFLOWS.md", "TESTING.md"]

    bash_result = _run_bash(git_repo, "check")
    powershell_result = _run_powershell(git_repo, "check")

    assert bash_result["must_refresh_topics"] == expected_must
    assert bash_result["review_topics"] == expected_review
    assert bash_result["suggested_topics"] == expected_suggested
    assert powershell_result["must_refresh_topics"] == expected_must
    assert powershell_result["review_topics"] == expected_review
    assert powershell_result["suggested_topics"] == expected_suggested


def test_bash_record_refresh_requires_canonical_map_outputs(git_repo: Path):
    result = _run_bash_raw(git_repo, "record-refresh", "manual")

    assert result.returncode != 0
    assert "canonical map files are missing" in result.stderr.lower()
    assert "quick-nav.md" in result.stderr.lower()


def test_bash_complete_refresh_uses_map_codebase_reason(git_repo: Path):
    _seed_canonical_map(git_repo)
    _commit_seeded_map(git_repo)

    refreshed = _run_bash(git_repo, "complete-refresh")

    assert refreshed["freshness"] == "fresh"
    status_path = git_repo / ".specify" / "project-map" / "index" / "status.json"
    payload = json.loads(status_path.read_text(encoding="utf-8"))
    assert payload["last_refresh_reason"] == "map-build"
    assert payload["last_refresh_topics"] == ["ARCHITECTURE.md", "STRUCTURE.md", "CONVENTIONS.md", "INTEGRATIONS.md", "OPERATIONS.md", "WORKFLOWS.md", "TESTING.md"]
    assert payload["last_refresh_scope"] == "full"
    assert payload["last_refresh_basis"] == "map-build"
    assert payload["last_refresh_changed_files_basis"] == []


def test_complete_refresh_clears_manual_force_stale_fields_in_shell_helpers(git_repo: Path):
    _seed_canonical_map(git_repo)
    _commit_seeded_map(git_repo)

    _run_bash(git_repo, "record-refresh", "manual")
    bash_dirty = _run_bash(git_repo, "mark-dirty", "workflow_contract_changed", "implement", "specs/001-demo", "lane-001")
    assert bash_dirty["manual_force_stale"] is True
    assert bash_dirty["manual_force_stale_reasons"] == ["workflow_contract_changed"]
    assert bash_dirty["dirty"] is True
    assert bash_dirty["dirty_reasons"] == ["workflow_contract_changed"]
    assert bash_dirty["dirty_origin_command"] == "implement"
    assert bash_dirty["dirty_origin_feature_dir"] == "specs/001-demo"
    assert bash_dirty["dirty_origin_lane_id"] == "lane-001"
    assert bash_dirty["dirty_scope_paths"] == []

    bash_refreshed = _run_bash(git_repo, "complete-refresh")
    assert bash_refreshed["manual_force_stale"] is False
    assert bash_refreshed["manual_force_stale_reasons"] == []
    assert bash_refreshed["dirty"] is False
    assert bash_refreshed["dirty_reasons"] == []
    assert bash_refreshed["dirty_origin_command"] == ""
    assert bash_refreshed["dirty_origin_feature_dir"] == ""
    assert bash_refreshed["dirty_origin_lane_id"] == ""
    assert bash_refreshed["dirty_scope_paths"] == []

    _run_powershell(git_repo, "mark-dirty", "workflow_contract_changed", "implement", "specs/001-demo", "lane-001")
    ps_refreshed = _run_powershell(git_repo, "complete-refresh")
    assert ps_refreshed["manual_force_stale"] is False
    assert ps_refreshed["manual_force_stale_reasons"] == []
    assert ps_refreshed["dirty"] is False
    assert ps_refreshed["dirty_reasons"] == []
    assert ps_refreshed["dirty_origin_command"] == ""
    assert ps_refreshed["dirty_origin_feature_dir"] == ""
    assert ps_refreshed["dirty_origin_lane_id"] == ""
    assert ps_refreshed["dirty_scope_paths"] == []

    payload = json.loads((git_repo / ".specify" / "project-map" / "index" / "status.json").read_text(encoding="utf-8"))
    assert payload["manual_force_stale"] is False
    assert payload["manual_force_stale_reasons"] == []
    assert payload["dirty"] is False
    assert payload["dirty_reasons"] == []
    assert payload["dirty_origin_command"] == ""
    assert payload["dirty_origin_feature_dir"] == ""
    assert payload["dirty_origin_lane_id"] == ""
    assert payload["dirty_scope_paths"] == []


def test_bash_prefers_present_empty_manual_force_stale_reasons_over_legacy_dirty_reasons(git_repo: Path):
    _seed_canonical_map(git_repo)
    _commit_seeded_map(git_repo)

    status_path = git_repo / ".specify" / "project-map" / "index" / "status.json"
    status_path.parent.mkdir(parents=True, exist_ok=True)
    status_path.write_text(
        json.dumps(
            {
                "version": 1,
                "last_mapped_commit": subprocess.run(["git", "rev-parse", "HEAD"], cwd=git_repo, check=True, capture_output=True, text=True).stdout.strip(),
                "last_mapped_at": "2026-04-21T00:00:00Z",
                "last_mapped_branch": "main",
                "freshness": "stale",
                "last_refresh_reason": "manual",
                "last_refresh_topics": [],
                "last_refresh_scope": "full",
                "last_refresh_basis": "manual",
                "last_refresh_changed_files_basis": [],
                "manual_force_stale": False,
                "manual_force_stale_reasons": [],
                "dirty": False,
                "dirty_reasons": ["workflow_contract_changed"],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    result = _run_bash(git_repo, "mark-dirty", "shared_surface_changed")

    assert result["dirty_reasons"] == ["shared_surface_changed"]
    assert result["manual_force_stale_reasons"] == ["shared_surface_changed"]


def test_bash_mark_dirty_normalizes_human_reason(git_repo: Path):
    _seed_canonical_map(git_repo)
    _commit_seeded_map(git_repo)
    _run_bash(git_repo, "record-refresh", "manual")

    dirty = _run_bash(git_repo, "mark-dirty", "workflow contract changed")

    assert dirty["dirty_reasons"] == ["workflow_contract_changed"]
    assert dirty["must_refresh_topics"] == ["WORKFLOWS.md"]
    assert dirty["review_topics"] == ["ARCHITECTURE.md", "INTEGRATIONS.md", "TESTING.md"]


def test_bash_check_downgrades_to_review_only_when_partial_refresh_already_covers_topics(git_repo: Path):
    _seed_canonical_map(git_repo)
    _commit_seeded_map(git_repo)

    status_path = git_repo / ".specify" / "project-map" / "index" / "status.json"
    status_path.parent.mkdir(parents=True, exist_ok=True)
    status_path.write_text(
        json.dumps(
            {
                "version": 1,
                "last_mapped_commit": subprocess.run(["git", "rev-parse", "HEAD"], cwd=git_repo, check=True, capture_output=True, text=True).stdout.strip(),
                "last_mapped_at": "2026-04-21T00:00:00Z",
                "last_mapped_branch": "main",
                "freshness": "fresh",
                "last_refresh_reason": "topic-refresh",
                "last_refresh_topics": ["ARCHITECTURE.md", "STRUCTURE.md", "TESTING.md"],
                "last_refresh_scope": "partial",
                "last_refresh_basis": "topic-refresh",
                "last_refresh_changed_files_basis": ["src/feature/local_fix.py"],
                "dirty": False,
                "dirty_reasons": [],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    changed = git_repo / "src" / "feature" / "local_fix.py"
    changed.parent.mkdir(parents=True, exist_ok=True)
    changed.write_text("print('hi')\n", encoding="utf-8")
    subprocess.run(["git", "add", "src/feature/local_fix.py"], cwd=git_repo, check=True)

    result = _run_bash(git_repo, "check")

    assert result["freshness"] == "possibly_stale"
    assert result["must_refresh_topics"] == []
    assert result["review_topics"] == ["ARCHITECTURE.md", "STRUCTURE.md", "TESTING.md"]
    assert result["reasons"] == ["covered topic changed since last partial map: src/feature/local_fix.py"]


def test_powershell_check_downgrades_to_review_only_when_partial_refresh_already_covers_topics(git_repo: Path):
    status_path = git_repo / ".specify" / "project-map" / "index" / "status.json"
    status_path.parent.mkdir(parents=True, exist_ok=True)
    status_path.write_text(
        json.dumps(
            {
                "version": 1,
                "last_mapped_commit": subprocess.run(["git", "rev-parse", "HEAD"], cwd=git_repo, check=True, capture_output=True, text=True).stdout.strip(),
                "last_mapped_at": "2026-04-21T00:00:00Z",
                "last_mapped_branch": "main",
                "freshness": "fresh",
                "last_refresh_reason": "topic-refresh",
                "last_refresh_topics": ["ARCHITECTURE.md", "STRUCTURE.md", "TESTING.md"],
                "last_refresh_scope": "partial",
                "last_refresh_basis": "topic-refresh",
                "last_refresh_changed_files_basis": ["src/feature/local_fix.py"],
                "dirty": False,
                "dirty_reasons": [],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    changed = git_repo / "src" / "feature" / "local_fix.py"
    changed.parent.mkdir(parents=True, exist_ok=True)
    changed.write_text("print('hi')\n", encoding="utf-8")
    subprocess.run(["git", "add", "src/feature/local_fix.py"], cwd=git_repo, check=True)

    result = _run_powershell(git_repo, "check")

    assert result["freshness"] == "possibly_stale"
    assert result["must_refresh_topics"] == []
    assert result["review_topics"] == ["ARCHITECTURE.md", "STRUCTURE.md", "TESTING.md"]
    assert result["reasons"] == ["covered topic changed since last partial map: src/feature/local_fix.py"]
