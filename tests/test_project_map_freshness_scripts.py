import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parent.parent
BASH_COMMON = PROJECT_ROOT / "scripts" / "bash" / "common.sh"
BASH_HELPER = PROJECT_ROOT / "scripts" / "bash" / "project-map-freshness.sh"
BASH_COGNITION_HELPER = PROJECT_ROOT / "scripts" / "bash" / "project-cognition-freshness.sh"
PS_COMMON = PROJECT_ROOT / "scripts" / "powershell" / "common.ps1"
PS_HELPER = PROJECT_ROOT / "scripts" / "powershell" / "project-map-freshness.ps1"
PS_COGNITION_HELPER = PROJECT_ROOT / "scripts" / "powershell" / "project-cognition-freshness.ps1"


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


def _run_bash_cognition(repo: Path, *args: str, launcher_argv: list[str] | None = None) -> dict:
    if not shutil.which("bash"):
        pytest.skip("bash not available")
    scripts_dir = repo / "scripts" / "bash"
    scripts_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy(BASH_COMMON, scripts_dir / "common.sh")
    shutil.copy(BASH_COGNITION_HELPER, scripts_dir / "project-cognition-freshness.sh")
    _write_source_launcher_config(repo, launcher_argv=launcher_argv)
    result = subprocess.run(
        ["bash", "scripts/bash/project-cognition-freshness.sh", ".", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return json.loads(result.stdout)


def _write_bash_source_launcher(repo: Path) -> list[str] | None:
    if not shutil.which("bash"):
        return None
    launcher_path = repo / "scripts" / "bash" / "source-specify-launcher.sh"
    launcher_path.parent.mkdir(parents=True, exist_ok=True)
    launcher_path.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        "if [[ \"$1\" != \"project-cognition\" || \"$2\" != \"mark-dirty\" ]]; then\n"
        "  echo \"unexpected launcher args: $*\" >&2\n"
        "  exit 64\n"
        "fi\n"
        "reason=\"\"\n"
        "shift 2\n"
        "while [[ $# -gt 0 ]]; do\n"
        "  case \"$1\" in\n"
        "    --reason) reason=\"$2\"; shift 2 ;;\n"
        "    --format) shift 2 ;;\n"
        "    *) shift ;;\n"
        "  esac\n"
        "done\n"
        "if [[ \"$reason\" != \"workflow contract changed\" ]]; then\n"
        "  echo \"unexpected reason: $reason\" >&2\n"
        "  exit 65\n"
        "fi\n"
        "mkdir -p .specify/project-cognition\n"
        "cat > .specify/project-cognition/status.json <<'JSON'\n"
        "{\"dirty\":true,\"dirty_reasons\":[\"workflow_contract_changed\"],\"status_path\":\".specify/project-cognition/status.json\"}\n"
        "JSON\n"
        "cat .specify/project-cognition/status.json\n",
        encoding="utf-8",
        newline="\n",
    )
    return ["bash", "scripts/bash/source-specify-launcher.sh"]


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


def _run_powershell_cognition(repo: Path, *args: str, launcher_argv: list[str] | None = None) -> dict:
    shell = shutil.which("pwsh") or shutil.which("powershell")
    if not shell:
        pytest.skip("PowerShell not available")
    scripts_dir = repo / "scripts" / "powershell"
    scripts_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy(PS_COMMON, scripts_dir / "common.ps1")
    shutil.copy(PS_COGNITION_HELPER, scripts_dir / "project-cognition-freshness.ps1")
    _write_source_launcher_config(repo, launcher_argv=launcher_argv)
    result = subprocess.run(
        [
            shell,
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            "scripts/powershell/project-cognition-freshness.ps1",
            "-RepoRoot",
            str(repo),
            "-Command",
            *args,
        ],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": str(PROJECT_ROOT / "src")},
    )
    return json.loads(result.stdout)


def _write_source_launcher_config(repo: Path, *, launcher_argv: list[str] | None = None) -> None:
    argv = launcher_argv or [sys.executable, "-m", "specify_cli"]
    config_path = repo / ".specify" / "config.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        json.dumps(
            {
                "specify_launcher": {
                    "command": " ".join(argv),
                    "argv": argv,
                }
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def _write_powershell_fake_launcher(repo: Path) -> list[str] | None:
    shell = shutil.which("pwsh") or shutil.which("powershell")
    if not shell:
        return None
    launcher_path = repo / "scripts" / "powershell" / "source-specify-launcher.ps1"
    launcher_path.parent.mkdir(parents=True, exist_ok=True)
    launcher_path.write_text(
        """
param([Parameter(ValueFromRemainingArguments=$true)][string[]]$Args)
if ($Args.Count -lt 2 -or $Args[0] -ne "project-cognition" -or $Args[1] -ne "mark-dirty") {
    Write-Error "unexpected launcher args: $($Args -join ' ')"
    exit 64
}
$reason = ""
for ($i = 2; $i -lt $Args.Count; $i++) {
    if ($Args[$i] -eq "--reason" -and ($i + 1) -lt $Args.Count) {
        $reason = $Args[$i + 1]
        $i++
    } elseif ($Args[$i] -eq "--format") {
        $i++
    }
}
if ($reason -ne "workflow contract changed") {
    Write-Error "unexpected reason: $reason"
    exit 65
}
New-Item -ItemType Directory -Force -Path ".specify/project-cognition" | Out-Null
$payload = '{"dirty":true,"dirty_reasons":["workflow_contract_changed"],"status_path":".specify/project-cognition/status.json"}'
Set-Content -LiteralPath ".specify/project-cognition/status.json" -Value $payload -Encoding utf8
Write-Output $payload
""".lstrip(),
        encoding="utf-8",
        newline="\n",
    )
    return [shell, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "scripts/powershell/source-specify-launcher.ps1"]


def _project_cognition_status_path(repo: Path) -> Path:
    return repo / ".specify" / "project-cognition" / "status.json"


def _legacy_project_map_status_path(repo: Path) -> Path:
    return repo / ".specify" / "project-map" / "status.json"


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
    status_path = _legacy_project_map_status_path(repo)
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


def _seed_graph_ready_stale_status(repo: Path, reason: str) -> Path:
    status_path = _project_cognition_status_path(repo)
    status_path.parent.mkdir(parents=True, exist_ok=True)
    (status_path.parent / "project-cognition.db").write_bytes(b"SQLite test database marker")
    status_path.write_text(
        json.dumps(
            {
                "version": 3,
                "baseline_state": "ready",
                "baseline_commit": "",
                "baseline_branch": "main",
                "baseline_built_at": "2026-05-17T00:00:00Z",
                "graph_ready": True,
                "graph_store_path": ".specify/project-cognition/project-cognition.db",
                "active_generation_id": "GEN-0001",
                "query_contract_version": 2,
                "update_contract_version": 1,
                "freshness": "stale",
                "dirty": True,
                "dirty_reasons": [reason],
                "manual_force_stale": True,
                "manual_force_stale_reasons": [reason],
                "dirty_origin_command": "sp-map-update",
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
    assert missing["state"] == "missing_baseline"
    assert missing["readiness"] == "blocked"
    assert missing["recommended_next_action"] == "run_map_scan_build"

    _seed_canonical_map(git_repo)
    _commit_seeded_map(git_repo)
    refreshed = _run_bash(git_repo, "record-refresh", "manual")
    assert refreshed["freshness"] == "fresh"
    assert refreshed["state"] == "fresh"
    assert refreshed["readiness"] == "ready"
    assert refreshed["recommended_next_action"] == "retry_current_workflow"
    assert refreshed["status_path"].endswith(".specify/project-cognition/status.json")

    dirty = _run_bash(
        git_repo,
        "mark-dirty",
        "shared_surface_changed",
        "implement",
        "specs/001-demo",
        "lane-001",
    )
    assert dirty["freshness"] == "stale"
    assert dirty["state"] == "runtime_stale"
    assert dirty["readiness"] == "blocked"
    assert dirty["recommended_next_action"] == "run_map_update"
    assert dirty["dirty"] is True
    assert dirty["dirty_reasons"] == ["shared_surface_changed"]
    assert dirty["dirty_origin_command"] == "implement"
    assert dirty["dirty_origin_feature_dir"] == "specs/001-demo"
    assert dirty["dirty_origin_lane_id"] == "lane-001"
    assert dirty["dirty_scope_paths"] == []
    assert dirty["must_refresh_topics"] == ["ARCHITECTURE.md", "STRUCTURE.md"]
    assert dirty["review_topics"] == ["INTEGRATIONS.md", "WORKFLOWS.md", "TESTING.md"]


def test_bash_project_map_freshness_routes_singular_path_gap_to_map_update(git_repo: Path):
    _seed_graph_ready_stale_status(
        git_repo,
        "path not covered by project cognition index: src/auth/missing.ts",
    )

    result = _run_bash(git_repo, "check")

    assert result["freshness"] == "stale"
    assert result["recommended_next_action"] == "run_map_update"


def test_bash_project_map_freshness_routes_unadoptable_path_gap_prose_to_map_update(git_repo: Path):
    _seed_graph_ready_stale_status(
        git_repo,
        "path not safely adoptable by project cognition index: scripts/release/package.ps1",
    )

    result = _run_bash(git_repo, "check")

    assert result["freshness"] == "stale"
    assert result["recommended_next_action"] == "run_map_update"


@pytest.mark.parametrize(
    "reason",
    [
        "58 changed paths missing from project cognition path_index",
        "path not safely adoptable by project cognition index: scripts/release/package.ps1",
    ],
)
def test_bash_mark_dirty_routes_normalized_path_gaps_to_map_update(git_repo: Path, reason: str):
    _seed_canonical_map(git_repo)
    _commit_seeded_map(git_repo)
    _run_bash(git_repo, "record-refresh", "manual")

    result = _run_bash(git_repo, "mark-dirty", reason)

    assert result["freshness"] == "stale"
    assert result["recommended_next_action"] == "run_map_update"


@pytest.mark.parametrize(
    "reason",
    [
        "explicit_rebuild_requested",
        "baseline_identity_invalid",
        "active_generation_has_no_path_index_rows",
        "failed_update_unusable_baseline",
        "path_not_safely_adoptable_by_project_cognition_index: scripts/release/package.ps1",
    ],
)
def test_bash_mark_dirty_routes_scan_build_machine_tokens_to_scan_build(git_repo: Path, reason: str):
    _seed_canonical_map(git_repo)
    _commit_seeded_map(git_repo)
    _run_bash(git_repo, "record-refresh", "manual")

    result = _run_bash(git_repo, "mark-dirty", reason)

    assert result["freshness"] == "stale"
    assert result["recommended_next_action"] == "run_map_scan_build"


@pytest.mark.parametrize(
    "reason",
    [
        "operator note: explicit_rebuild_requested is documented here, not asserted as a machine token",
        "operator note: baseline_identity_invalid appears in guidance, but this is prose",
    ],
)
def test_bash_mark_dirty_ignores_scan_build_token_strings_inside_prose(git_repo: Path, reason: str):
    _seed_canonical_map(git_repo)
    _commit_seeded_map(git_repo)
    _run_bash(git_repo, "record-refresh", "manual")

    result = _run_bash(git_repo, "mark-dirty", reason)

    assert result["freshness"] == "stale"
    assert result["recommended_next_action"] == "run_map_update"


def test_bash_project_cognition_helper_uses_launcher_without_project_map(git_repo: Path):
    launcher = _write_bash_source_launcher(git_repo)
    if launcher is None:
        pytest.skip("bash python not available")

    payload = _run_bash_cognition(
        git_repo,
        "mark-dirty",
        "workflow contract changed",
        launcher_argv=launcher,
    )

    assert payload["dirty"] is True
    assert payload["dirty_reasons"] == ["workflow_contract_changed"]
    assert payload["status_path"].replace("\\", "/").endswith(".specify/project-cognition/status.json")
    assert _project_cognition_status_path(git_repo).exists()
    assert not (git_repo / ".specify" / "project-map").exists()


def test_powershell_project_cognition_helper_uses_launcher_without_project_map(git_repo: Path):
    launcher = _write_powershell_fake_launcher(git_repo)
    if launcher is None:
        pytest.skip("PowerShell not available")

    payload = _run_powershell_cognition(
        git_repo,
        "mark-dirty",
        "workflow contract changed",
        launcher_argv=launcher,
    )

    assert payload["dirty"] is True
    assert payload["dirty_reasons"] == ["workflow_contract_changed"]
    assert payload["status_path"].replace("\\", "/").endswith(".specify/project-cognition/status.json")
    assert _project_cognition_status_path(git_repo).exists()
    assert not (git_repo / ".specify" / "project-map").exists()


def test_bash_check_reads_legacy_project_map_status(git_repo: Path):
    _seed_legacy_status(git_repo)

    result = _run_bash(git_repo, "check")

    assert result["freshness"] == "stale"
    assert result["dirty"] is True
    assert result["dirty_reasons"] == ["workflow_contract_changed"]
    assert result["status_path"].endswith(".specify/project-cognition/status.json")
    assert result["suggested_topics"] == ["ARCHITECTURE.md", "INTEGRATIONS.md", "WORKFLOWS.md", "TESTING.md"]


def test_bash_mark_dirty_migrates_legacy_status_to_canonical_path(git_repo: Path):
    _seed_legacy_status(git_repo, dirty=False)

    result = _run_bash(git_repo, "mark-dirty", "shared_surface_changed")

    assert result["freshness"] == "stale"
    assert _project_cognition_status_path(git_repo).exists()
    assert _legacy_project_map_status_path(git_repo).exists()
    assert not (git_repo / ".specify" / "project-map" / "index" / "status.json").exists()
    payload = json.loads(_project_cognition_status_path(git_repo).read_text(encoding="utf-8"))
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
    assert stale["state"] == "runtime_stale"
    assert stale["readiness"] == "blocked"
    assert stale["recommended_next_action"] == "run_map_update"
    assert any("high-impact compatibility/export change" in reason for reason in stale["reasons"])
    assert stale["must_refresh_topics"] == ["INTEGRATIONS.md", "WORKFLOWS.md"]
    assert stale["review_topics"] == ["ARCHITECTURE.md", "TESTING.md"]
    assert stale["suggested_topics"] == ["ARCHITECTURE.md", "INTEGRATIONS.md", "WORKFLOWS.md", "TESTING.md"]


def test_powershell_project_map_freshness_routes_singular_path_gap_to_map_update(git_repo: Path):
    _seed_graph_ready_stale_status(
        git_repo,
        "path not covered by project cognition index: src/auth/missing.ts",
    )

    result = _run_powershell(git_repo, "check")

    assert result["freshness"] == "stale"
    assert result["recommended_next_action"] == "run_map_update"


def test_powershell_project_map_freshness_routes_unadoptable_path_gap_prose_to_map_update(git_repo: Path):
    _seed_graph_ready_stale_status(
        git_repo,
        "path not safely adoptable by project cognition index: scripts/release/package.ps1",
    )

    result = _run_powershell(git_repo, "check")

    assert result["freshness"] == "stale"
    assert result["recommended_next_action"] == "run_map_update"


@pytest.mark.parametrize(
    "reason",
    [
        "58 changed paths missing from project cognition path_index",
        "path not safely adoptable by project cognition index: scripts/release/package.ps1",
    ],
)
def test_powershell_mark_dirty_routes_normalized_path_gaps_to_map_update(git_repo: Path, reason: str):
    _seed_canonical_map(git_repo)
    _commit_seeded_map(git_repo)
    _run_powershell(git_repo, "record-refresh", "manual")

    result = _run_powershell(git_repo, "mark-dirty", reason)

    assert result["freshness"] == "stale"
    assert result["recommended_next_action"] == "run_map_update"


@pytest.mark.parametrize(
    "reason",
    [
        "explicit_rebuild_requested",
        "baseline_identity_invalid",
        "active_generation_has_no_path_index_rows",
        "failed_update_unusable_baseline",
        "path_not_safely_adoptable_by_project_cognition_index: scripts/release/package.ps1",
    ],
)
def test_powershell_mark_dirty_routes_scan_build_machine_tokens_to_scan_build(git_repo: Path, reason: str):
    _seed_canonical_map(git_repo)
    _commit_seeded_map(git_repo)
    _run_powershell(git_repo, "record-refresh", "manual")

    result = _run_powershell(git_repo, "mark-dirty", reason)

    assert result["freshness"] == "stale"
    assert result["recommended_next_action"] == "run_map_scan_build"


@pytest.mark.parametrize(
    "reason",
    [
        "operator note: explicit_rebuild_requested is documented here, not asserted as a machine token",
        "operator note: baseline_identity_invalid appears in guidance, but this is prose",
    ],
)
def test_powershell_mark_dirty_ignores_scan_build_token_strings_inside_prose(git_repo: Path, reason: str):
    _seed_canonical_map(git_repo)
    _commit_seeded_map(git_repo)
    _run_powershell(git_repo, "record-refresh", "manual")

    result = _run_powershell(git_repo, "mark-dirty", reason)

    assert result["freshness"] == "stale"
    assert result["recommended_next_action"] == "run_map_update"


def test_project_map_freshness_helpers_classify_support_drift_with_next_action(git_repo: Path):
    _seed_canonical_map(git_repo)
    _commit_seeded_map(git_repo)
    _run_bash(git_repo, "record-refresh", "map-build")
    _run_powershell(git_repo, "record-refresh", "map-build")

    changed = git_repo / ".specify" / "templates" / "runtime-config.template.json"
    changed.parent.mkdir(parents=True, exist_ok=True)
    changed.write_text('{"changed": true}\n', encoding="utf-8")
    subprocess.run(["git", "add", ".specify/templates/runtime-config.template.json"], cwd=git_repo, check=True)

    bash_result = _run_bash(git_repo, "check")
    pwsh_result = _run_powershell(git_repo, "check")

    assert bash_result["freshness"] == "support_drift"
    assert bash_result["state"] == "support_drift"
    assert bash_result["readiness"] == "blocked"
    assert bash_result["recommended_next_action"] == "commit_or_ignore_support_files"
    assert bash_result["must_refresh_topics"] == []
    assert bash_result["review_topics"] == []
    assert any("support surface changed" in reason for reason in bash_result["reasons"])

    assert pwsh_result["freshness"] == bash_result["freshness"]
    assert pwsh_result["state"] == bash_result["state"]
    assert pwsh_result["readiness"] == bash_result["readiness"]
    assert pwsh_result["recommended_next_action"] == bash_result["recommended_next_action"]
    assert pwsh_result["must_refresh_topics"] == bash_result["must_refresh_topics"]
    assert pwsh_result["review_topics"] == bash_result["review_topics"]
    assert any("support surface changed" in reason for reason in pwsh_result["reasons"])


def test_project_map_freshness_helpers_report_possibly_stale_state_and_action(git_repo: Path):
    _seed_canonical_map(git_repo)
    _commit_seeded_map(git_repo)
    _run_bash(git_repo, "record-refresh", "map-build")
    _run_powershell(git_repo, "record-refresh", "map-build")

    changed = git_repo / "src" / "feature" / "local_fix.py"
    changed.parent.mkdir(parents=True, exist_ok=True)
    changed.write_text("print('hi')\n", encoding="utf-8")
    subprocess.run(["git", "add", "src/feature/local_fix.py"], cwd=git_repo, check=True)

    bash_result = _run_bash(git_repo, "check")
    pwsh_result = _run_powershell(git_repo, "check")

    assert bash_result["freshness"] == "possibly_stale"
    assert bash_result["state"] == "runtime_stale"
    assert bash_result["readiness"] == "review"
    assert bash_result["recommended_next_action"] == "run_map_update"
    assert pwsh_result["freshness"] == bash_result["freshness"]
    assert pwsh_result["state"] == bash_result["state"]
    assert pwsh_result["readiness"] == bash_result["readiness"]
    assert pwsh_result["recommended_next_action"] == bash_result["recommended_next_action"]


def test_project_map_freshness_helpers_report_partial_refresh_for_stale_runtime_drift_after_partial_refresh(git_repo: Path):
    _seed_canonical_map(git_repo)
    _commit_seeded_map(git_repo)

    status_path = _project_cognition_status_path(git_repo)
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
                "last_refresh_topics": ["INTEGRATIONS.md", "WORKFLOWS.md"],
                "last_refresh_scope": "partial",
                "last_refresh_basis": "topic-refresh",
                "last_refresh_changed_files_basis": ["src/routes/api.ts"],
                "dirty": False,
                "dirty_reasons": [],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    changed = git_repo / "src" / "routes" / "api.ts"
    changed.parent.mkdir(parents=True, exist_ok=True)
    changed.write_text("export const route = true;\n", encoding="utf-8")
    subprocess.run(["git", "add", "src/routes/api.ts"], cwd=git_repo, check=True)

    bash_result = _run_bash(git_repo, "check")
    pwsh_result = _run_powershell(git_repo, "check")

    assert bash_result["freshness"] == "partial_refresh"
    assert bash_result["state"] == "partial_refresh"
    assert bash_result["readiness"] == "blocked"
    assert bash_result["recommended_next_action"] == "run_map_update"
    assert any("partial cognition refresh is recorded" in reason.lower() for reason in bash_result["reasons"])

    assert pwsh_result["freshness"] == bash_result["freshness"]
    assert pwsh_result["state"] == bash_result["state"]
    assert pwsh_result["readiness"] == bash_result["readiness"]
    assert pwsh_result["recommended_next_action"] == bash_result["recommended_next_action"]
    assert any("partial cognition refresh is recorded" in reason.lower() for reason in pwsh_result["reasons"])


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


def test_project_map_freshness_helpers_ignore_reference_only_atlas_changes(git_repo: Path):
    _seed_canonical_map(git_repo)
    _commit_seeded_map(git_repo)
    _run_bash(git_repo, "record-refresh", "map-build")
    _run_powershell(git_repo, "record-refresh", "map-build")

    target = git_repo / ".specify" / "project-map" / "root" / "ARCHITECTURE.md"
    target.write_text("# changed atlas output\n", encoding="utf-8")
    subprocess.run(["git", "add", str(target.relative_to(git_repo))], cwd=git_repo, check=True)

    bash_result = _run_bash(git_repo, "check")
    pwsh_result = _run_powershell(git_repo, "check")

    assert bash_result["freshness"] == "fresh"
    assert bash_result["reasons"] == []
    assert pwsh_result["freshness"] == "fresh"
    assert pwsh_result["reasons"] == []


@pytest.mark.parametrize(
    "path",
    [
        "PROJECT-HANDBOOK.md",
        ".specify/project-map/root/STRUCTURE.md",
        ".specify/prd-runs/001-demo/research.json",
        ".venv/lib/site-packages/pkg.py",
        ".pytest_cache/v/cache/nodeids",
        ".ruff_cache/0.11.0/cache",
        "dist/spec-kit-plus.tar.gz",
        "build/lib/module.py",
    ],
)
def test_project_map_freshness_helpers_ignore_reference_and_excluded_paths(git_repo: Path, path: str):
    _seed_canonical_map(git_repo)
    _commit_seeded_map(git_repo)
    _run_bash(git_repo, "record-refresh", "map-build")
    _run_powershell(git_repo, "record-refresh", "map-build")

    changed = git_repo / path
    changed.parent.mkdir(parents=True, exist_ok=True)
    changed.write_text("changed\n", encoding="utf-8")
    subprocess.run(["git", "add", "-f", path], cwd=git_repo, check=True)

    bash_result = _run_bash(git_repo, "check")
    pwsh_result = _run_powershell(git_repo, "check")

    assert bash_result["freshness"] == "fresh"
    assert bash_result["reasons"] == []
    assert pwsh_result["freshness"] == "fresh"
    assert pwsh_result["reasons"] == []


@pytest.mark.parametrize(
    "path,expected_freshness,expected_reason_prefix",
    [
        (".specify/templates/project-map/ARCHITECTURE.md", "stale", "high-impact compatibility/export change"),
        (".specify/memory/constitution.md", "stale", "high-impact compatibility/export change"),
        (".specify/memory/project-rules.md", "stale", "high-impact compatibility/export change"),
        ("docker-compose.yml", "stale", "high-impact compatibility/export change"),
        ("Dockerfile", "stale", "high-impact compatibility/export change"),
        ("Makefile", "stale", "high-impact compatibility/export change"),
        ("package.json", "stale", "high-impact compatibility/export change"),
        ("pnpm-lock.yaml", "stale", "high-impact compatibility/export change"),
        ("go.mod", "stale", "high-impact compatibility/export change"),
    ],
)
def test_project_map_freshness_helpers_keep_live_runtime_paths_stale_driving(
    git_repo: Path,
    path: str,
    expected_freshness: str,
    expected_reason_prefix: str,
):
    _seed_canonical_map(git_repo)
    _commit_seeded_map(git_repo)
    _run_bash(git_repo, "record-refresh", "map-build")
    _run_powershell(git_repo, "record-refresh", "map-build")

    changed = git_repo / path
    changed.parent.mkdir(parents=True, exist_ok=True)
    changed.write_text("changed\n", encoding="utf-8")
    subprocess.run(["git", "add", path], cwd=git_repo, check=True)

    bash_result = _run_bash(git_repo, "check")
    pwsh_result = _run_powershell(git_repo, "check")

    assert bash_result["freshness"] == expected_freshness
    assert any(reason.startswith(expected_reason_prefix) for reason in bash_result["reasons"])
    assert pwsh_result["freshness"] == expected_freshness
    assert any(reason.startswith(expected_reason_prefix) for reason in pwsh_result["reasons"])


def test_powershell_check_reads_legacy_project_map_status(git_repo: Path):
    _seed_legacy_status(git_repo)

    result = _run_powershell(git_repo, "check")

    assert result["freshness"] == "stale"
    assert result["dirty"] is True
    assert result["dirty_reasons"] == ["workflow_contract_changed"]
    assert result["status_path"].replace("\\", "/").endswith(".specify/project-cognition/status.json")
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
    assert "project-map compatibility/export baseline" in result.stderr.lower()
    assert "project-handbook.md" in result.stderr.lower()
    assert "quick-nav.md" in result.stderr.lower()


def test_project_map_refresh_helpers_frame_outputs_as_compatibility_exports(git_repo: Path):
    result = _run_bash_raw(git_repo, "record-refresh", "manual")
    pwsh = shutil.which("pwsh") or shutil.which("powershell")

    assert "project-handbook.md" in result.stderr.lower()
    assert "layered compatibility/export atlas files exist" in result.stderr.lower()

    if pwsh:
        ps_result = subprocess.run(
            [
                pwsh,
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                "scripts/powershell/project-map-freshness.ps1",
                "-RepoRoot",
                str(git_repo),
                "-Command",
                "record-refresh",
                "-Reason",
                "manual",
            ],
            cwd=git_repo,
            check=False,
            capture_output=True,
            text=True,
        )
        assert ps_result.returncode != 0
        stderr = (ps_result.stderr or "") + (ps_result.stdout or "")
        lowered = stderr.lower()
        assert "project-map compatibility/export baseline" in lowered
        assert "project-handbook.md" in lowered
        assert "layered compatibility/export atlas files exist" in lowered


def test_bash_complete_refresh_uses_map_codebase_reason(git_repo: Path):
    _seed_canonical_map(git_repo)
    _commit_seeded_map(git_repo)

    refreshed = _run_bash(git_repo, "complete-refresh")

    assert refreshed["freshness"] == "fresh"
    status_path = _project_cognition_status_path(git_repo)
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

    payload = json.loads(_project_cognition_status_path(git_repo).read_text(encoding="utf-8"))
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

    status_path = _project_cognition_status_path(git_repo)
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

    status_path = _project_cognition_status_path(git_repo)
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
    status_path = _project_cognition_status_path(git_repo)
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
