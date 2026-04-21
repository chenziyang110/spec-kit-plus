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
    for name in (
        "ARCHITECTURE.md",
        "STRUCTURE.md",
        "CONVENTIONS.md",
        "INTEGRATIONS.md",
        "WORKFLOWS.md",
        "TESTING.md",
        "OPERATIONS.md",
    ):
        (project_map_dir / name).write_text(f"# {name}\n", encoding="utf-8")


def _commit_seeded_map(repo: Path) -> None:
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "seed canonical map", "-q"], cwd=repo, check=True)


def test_bash_project_map_freshness_lifecycle(git_repo: Path):
    missing = _run_bash(git_repo, "check")
    assert missing["freshness"] == "missing"

    _seed_canonical_map(git_repo)
    _commit_seeded_map(git_repo)
    refreshed = _run_bash(git_repo, "record-refresh", "manual")
    assert refreshed["freshness"] == "fresh"
    assert refreshed["status_path"].endswith(".specify/project-map/status.json")

    dirty = _run_bash(git_repo, "mark-dirty", "shared_surface_changed")
    assert dirty["freshness"] == "stale"
    assert dirty["dirty"] is True
    assert dirty["dirty_reasons"] == ["shared_surface_changed"]


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


def test_bash_record_refresh_requires_canonical_map_outputs(git_repo: Path):
    result = _run_bash_raw(git_repo, "record-refresh", "manual")

    assert result.returncode != 0
    assert "canonical map files are missing" in result.stderr.lower()


def test_bash_complete_refresh_uses_map_codebase_reason(git_repo: Path):
    _seed_canonical_map(git_repo)
    _commit_seeded_map(git_repo)

    refreshed = _run_bash(git_repo, "complete-refresh")

    assert refreshed["freshness"] == "fresh"
    status_path = git_repo / ".specify" / "project-map" / "status.json"
    payload = json.loads(status_path.read_text(encoding="utf-8"))
    assert payload["last_refresh_reason"] == "map-codebase"
