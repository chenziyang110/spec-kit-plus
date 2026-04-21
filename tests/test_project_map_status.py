from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import subprocess
import sys


PROJECT_ROOT = Path(__file__).resolve().parent.parent
MODULE_PATH = PROJECT_ROOT / "src" / "specify_cli" / "project_map_status.py"


def _load_module():
    spec = spec_from_file_location("project_map_status", MODULE_PATH)
    assert spec and spec.loader
    module = module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_project_map_status_round_trip(tmp_path):
    mod = _load_module()

    status = mod.ProjectMapStatus(
        last_mapped_commit="abc123",
        last_mapped_at="2026-04-21T00:00:00Z",
        last_mapped_branch="main",
        freshness="fresh",
        last_refresh_reason="manual",
        dirty=False,
        dirty_reasons=[],
    )

    written = mod.write_project_map_status(tmp_path, status)
    loaded = mod.read_project_map_status(tmp_path)

    assert written == tmp_path / ".specify" / "project-map" / "status.json"
    assert loaded.last_mapped_commit == "abc123"
    assert loaded.last_mapped_branch == "main"
    assert loaded.freshness == "fresh"
    assert loaded.dirty is False


def test_missing_canonical_project_map_paths_lists_required_outputs(tmp_path):
    mod = _load_module()

    missing = mod.missing_canonical_project_map_paths(tmp_path)

    normalized = [str(path).replace("\\", "/") for path in missing]
    assert normalized == [
        f"{tmp_path.as_posix()}/PROJECT-HANDBOOK.md",
        f"{tmp_path.as_posix()}/.specify/project-map/ARCHITECTURE.md",
        f"{tmp_path.as_posix()}/.specify/project-map/STRUCTURE.md",
        f"{tmp_path.as_posix()}/.specify/project-map/CONVENTIONS.md",
        f"{tmp_path.as_posix()}/.specify/project-map/INTEGRATIONS.md",
        f"{tmp_path.as_posix()}/.specify/project-map/WORKFLOWS.md",
        f"{tmp_path.as_posix()}/.specify/project-map/TESTING.md",
        f"{tmp_path.as_posix()}/.specify/project-map/OPERATIONS.md",
    ]


def test_mark_project_map_dirty_appends_reason_once(tmp_path):
    mod = _load_module()

    mod.mark_project_map_refreshed(
        tmp_path,
        head_commit="abc123",
        branch="main",
        reason="manual",
        mapped_at="2026-04-21T00:00:00Z",
    )
    first = mod.mark_project_map_dirty(tmp_path, "shared_surface_changed")
    second = mod.mark_project_map_dirty(tmp_path, "shared_surface_changed")

    assert first.dirty is True
    assert first.freshness == "stale"
    assert first.dirty_reasons == ["shared_surface_changed"]
    assert second.dirty_reasons == ["shared_surface_changed"]


def test_assess_project_map_freshness_reports_missing_status(tmp_path):
    mod = _load_module()

    result = mod.assess_project_map_freshness(
        tmp_path,
        head_commit="abc123",
        changed_files=[],
        has_git=True,
    )

    assert result["freshness"] == "missing"
    assert result["reasons"] == ["project-map status missing"]


def test_complete_project_map_refresh_uses_map_codebase_reason(tmp_path):
    mod = _load_module()
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=tmp_path, check=True)
    (tmp_path / "seed.txt").write_text("seed\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "init", "-q"], cwd=tmp_path, check=True)

    status = mod.complete_project_map_refresh(tmp_path)

    assert status.last_refresh_reason == "map-codebase"
    assert status.freshness == "fresh"


def test_assess_project_map_freshness_classifies_changed_files(tmp_path):
    mod = _load_module()

    mod.mark_project_map_refreshed(
        tmp_path,
        head_commit="base123",
        branch="main",
        reason="manual",
        mapped_at="2026-04-21T00:00:00Z",
    )

    stale = mod.assess_project_map_freshness(
        tmp_path,
        head_commit="head456",
        changed_files=["src/router/index.ts"],
        has_git=True,
    )
    maybe = mod.assess_project_map_freshness(
        tmp_path,
        head_commit="head456",
        changed_files=["src/feature/local_fix.py"],
        has_git=True,
    )
    fresh = mod.assess_project_map_freshness(
        tmp_path,
        head_commit="head456",
        changed_files=["notes/todo.txt"],
        has_git=True,
    )

    assert stale["freshness"] == "stale"
    assert stale["reasons"] == ["high-impact project-map change: src/router/index.ts"]
    assert maybe["freshness"] == "possibly_stale"
    assert maybe["reasons"] == ["codebase surface changed since last map: src/feature/local_fix.py"]
    assert fresh["freshness"] == "fresh"
    assert fresh["reasons"] == []


def test_classify_changed_path_matches_shell_contract():
    mod = _load_module()

    assert mod.classify_changed_path("PROJECT-HANDBOOK.md") == "stale"
    assert mod.classify_changed_path(".specify/project-map/ARCHITECTURE.md") == "stale"
    assert mod.classify_changed_path(".specify/project-map/status.json") == "ignore"
    assert mod.classify_changed_path("src/routes/api.ts") == "stale"
    assert mod.classify_changed_path("src/components/button.tsx") == "possibly_stale"
    assert mod.classify_changed_path("notes/changelog.txt") == "ignore"


def test_inspect_project_map_freshness_reads_git_worktree(tmp_path):
    mod = _load_module()

    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=tmp_path, check=True)

    tracked = tmp_path / "src" / "router.ts"
    tracked.parent.mkdir(parents=True, exist_ok=True)
    tracked.write_text("export const route = true;\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "init", "-q"], cwd=tmp_path, check=True)

    mod.mark_project_map_refreshed(
        tmp_path,
        head_commit=mod.git_head_commit(tmp_path),
        branch=mod.git_branch_name(tmp_path),
        reason="manual",
        mapped_at="2026-04-21T00:00:00Z",
    )

    changed = tmp_path / "src" / "api" / "routes.ts"
    changed.parent.mkdir(parents=True, exist_ok=True)
    changed.write_text("export const routes = [];\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)

    result = mod.inspect_project_map_freshness(tmp_path)

    assert result["freshness"] == "stale"
    assert "src/api/routes.ts" in result["changed_files"]
    assert any("high-impact project-map change: src/api/routes.ts" == reason for reason in result["reasons"])
