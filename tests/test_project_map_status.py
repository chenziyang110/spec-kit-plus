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
        version=2,
        global_freshness="fresh",
        global_last_refresh_commit="abc123",
        global_last_refresh_at="2026-04-21T00:00:00Z",
        global_stale_reasons=[],
        global_affected_root_docs=["WORKFLOWS.md"],
        modules={
            "specify-cli-core": {
                "freshness": "fresh",
                "deep_status": "deep_stale",
                "last_refresh_commit": "abc123",
                "coverage_fingerprint": "sha256:test",
                "stale_reasons": [],
                "affected_docs": ["WORKFLOWS.md"],
            }
        },
    )

    written = mod.write_project_map_status(tmp_path, status)
    loaded = mod.read_project_map_status(tmp_path)

    assert written == tmp_path / ".specify" / "project-map" / "index" / "status.json"
    assert loaded.version == 2
    assert loaded.global_last_refresh_commit == "abc123"
    assert loaded.global_freshness == "fresh"
    assert loaded.global_affected_root_docs == ["WORKFLOWS.md"]
    assert loaded.modules["specify-cli-core"]["deep_status"] == "deep_stale"


def test_missing_canonical_project_map_paths_lists_required_outputs(tmp_path):
    mod = _load_module()

    missing = mod.missing_canonical_project_map_paths(tmp_path)

    normalized = [str(path).replace("\\", "/") for path in missing]
    assert normalized == [
        f"{tmp_path.as_posix()}/PROJECT-HANDBOOK.md",
        f"{tmp_path.as_posix()}/.specify/project-map/index/atlas-index.json",
        f"{tmp_path.as_posix()}/.specify/project-map/index/modules.json",
        f"{tmp_path.as_posix()}/.specify/project-map/index/relations.json",
        f"{tmp_path.as_posix()}/.specify/project-map/index/status.json",
        f"{tmp_path.as_posix()}/.specify/project-map/root/ARCHITECTURE.md",
        f"{tmp_path.as_posix()}/.specify/project-map/root/STRUCTURE.md",
        f"{tmp_path.as_posix()}/.specify/project-map/root/CONVENTIONS.md",
        f"{tmp_path.as_posix()}/.specify/project-map/root/INTEGRATIONS.md",
        f"{tmp_path.as_posix()}/.specify/project-map/root/WORKFLOWS.md",
        f"{tmp_path.as_posix()}/.specify/project-map/root/TESTING.md",
        f"{tmp_path.as_posix()}/.specify/project-map/root/OPERATIONS.md",
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


def test_normalize_dirty_reason_maps_human_input_to_canonical_reason():
    mod = _load_module()

    assert mod.normalize_dirty_reason("shared surface changed") == "shared_surface_changed"
    assert mod.normalize_dirty_reason("workflow contract changed") == "workflow_contract_changed"
    assert mod.normalize_dirty_reason("runtime invariant changed") == "runtime_invariant_changed"
    assert mod.normalize_dirty_reason("integration boundary changed") == "integration_boundary_changed"


def test_refresh_plan_for_dirty_reason_maps_to_topics():
    mod = _load_module()

    assert mod.refresh_plan_for_dirty_reason("shared_surface_changed") == {
        "must_refresh_topics": ["ARCHITECTURE.md", "STRUCTURE.md"],
        "review_topics": ["INTEGRATIONS.md", "WORKFLOWS.md", "TESTING.md"],
    }
    assert mod.refresh_plan_for_dirty_reason("workflow_contract_changed") == {
        "must_refresh_topics": ["WORKFLOWS.md"],
        "review_topics": ["ARCHITECTURE.md", "INTEGRATIONS.md", "TESTING.md"],
    }
    assert mod.refresh_plan_for_dirty_reason("runtime_invariant_changed") == {
        "must_refresh_topics": ["OPERATIONS.md"],
        "review_topics": ["INTEGRATIONS.md", "TESTING.md"],
    }


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

    assert status.last_refresh_reason == "map-build"
    assert status.freshness == "fresh"
    assert status.last_refresh_topics == ["ARCHITECTURE.md", "STRUCTURE.md", "CONVENTIONS.md", "INTEGRATIONS.md", "OPERATIONS.md", "WORKFLOWS.md", "TESTING.md"]
    assert status.last_refresh_scope == "full"
    assert status.last_refresh_basis == "map-build"
    assert status.last_refresh_changed_files_basis == []


def test_mark_project_map_refreshed_accepts_partial_topic_scope(tmp_path):
    mod = _load_module()

    status = mod.mark_project_map_refreshed(
        tmp_path,
        head_commit="abc123",
        branch="main",
        reason="manual",
        mapped_at="2026-04-21T00:00:00Z",
        refresh_topics=["INTEGRATIONS.md", "WORKFLOWS.md"],
        refresh_scope="partial",
        refresh_basis="topic-refresh",
        changed_files_basis=["src/routes/api.ts"],
    )

    assert status.last_refresh_topics == ["INTEGRATIONS.md", "WORKFLOWS.md"]
    assert status.last_refresh_scope == "partial"
    assert status.last_refresh_basis == "topic-refresh"
    assert status.last_refresh_changed_files_basis == ["src/routes/api.ts"]


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
    assert stale["must_refresh_topics"] == ["INTEGRATIONS.md", "WORKFLOWS.md"]
    assert stale["review_topics"] == ["ARCHITECTURE.md", "TESTING.md"]
    assert stale["suggested_topics"] == ["ARCHITECTURE.md", "INTEGRATIONS.md", "WORKFLOWS.md", "TESTING.md"]
    assert maybe["freshness"] == "possibly_stale"
    assert maybe["reasons"] == ["codebase surface changed since last map: src/feature/local_fix.py"]
    assert maybe["must_refresh_topics"] == ["STRUCTURE.md"]
    assert maybe["review_topics"] == ["ARCHITECTURE.md", "TESTING.md"]
    assert maybe["suggested_topics"] == ["ARCHITECTURE.md", "STRUCTURE.md", "TESTING.md"]
    assert fresh["freshness"] == "fresh"
    assert fresh["reasons"] == []
    assert fresh["must_refresh_topics"] == []
    assert fresh["review_topics"] == []
    assert fresh["suggested_topics"] == []


def test_assess_project_map_freshness_downgrades_to_review_only_when_partial_refresh_already_covers_topics(tmp_path):
    mod = _load_module()

    mod.mark_project_map_refreshed(
        tmp_path,
        head_commit="base123",
        branch="main",
        reason="topic-refresh",
        mapped_at="2026-04-21T00:00:00Z",
        refresh_topics=["STRUCTURE.md", "ARCHITECTURE.md", "TESTING.md"],
        refresh_scope="partial",
        refresh_basis="topic-refresh",
        changed_files_basis=["src/feature/local_fix.py"],
    )

    result = mod.assess_project_map_freshness(
        tmp_path,
        head_commit="head456",
        changed_files=["src/feature/local_fix.py"],
        has_git=True,
    )

    assert result["freshness"] == "possibly_stale"
    assert result["must_refresh_topics"] == []
    assert result["review_topics"] == ["ARCHITECTURE.md", "STRUCTURE.md", "TESTING.md"]
    assert result["suggested_topics"] == ["ARCHITECTURE.md", "STRUCTURE.md", "TESTING.md"]
    assert result["reasons"] == ["covered topic changed since last partial map: src/feature/local_fix.py"]


def test_classify_changed_path_matches_shell_contract():
    mod = _load_module()

    assert mod.classify_changed_path("PROJECT-HANDBOOK.md") == "stale"
    assert mod.classify_changed_path(".specify/project-map/root/ARCHITECTURE.md") == "stale"
    assert mod.classify_changed_path(".specify/project-map/index/status.json") == "ignore"
    assert mod.classify_changed_path(".specify/project-map/map-state.md") == "ignore"
    assert mod.classify_changed_path(".specify/project-map/worker-results/SCAN-core.json") == "ignore"
    assert mod.classify_changed_path("src/routes/api.ts") == "stale"
    assert mod.classify_changed_path("src/components/button.tsx") == "possibly_stale"
    assert mod.classify_changed_path("notes/changelog.txt") == "ignore"


def test_suggested_topics_for_changed_path_maps_high_value_surfaces():
    mod = _load_module()

    assert mod.suggested_topics_for_changed_path("src/routes/api.ts") == [
        "ARCHITECTURE.md",
        "INTEGRATIONS.md",
        "WORKFLOWS.md",
        "TESTING.md",
    ]
    assert mod.suggested_topics_for_changed_path("src/components/button.tsx") == [
        "ARCHITECTURE.md",
        "STRUCTURE.md",
        "TESTING.md",
    ]
    assert mod.suggested_topics_for_changed_path("docker-compose.yml") == [
        "INTEGRATIONS.md",
        "OPERATIONS.md",
        "TESTING.md",
    ]
    assert mod.suggested_topics_for_changed_path(".specify/project-map/index/status.json") == []
    assert mod.suggested_topics_for_changed_path(".specify/project-map/map-state.md") == []
    assert mod.suggested_topics_for_changed_path(".specify/project-map/worker-results/SCAN-core.json") == []


def test_refresh_plan_for_changed_path_splits_must_refresh_from_review():
    mod = _load_module()

    assert mod.refresh_plan_for_changed_path("src/routes/api.ts") == {
        "must_refresh_topics": ["INTEGRATIONS.md", "WORKFLOWS.md"],
        "review_topics": ["ARCHITECTURE.md", "TESTING.md"],
    }
    assert mod.refresh_plan_for_changed_path("src/components/button.tsx") == {
        "must_refresh_topics": ["STRUCTURE.md"],
        "review_topics": ["ARCHITECTURE.md", "TESTING.md"],
    }
    assert mod.refresh_plan_for_changed_path("docker-compose.yml") == {
        "must_refresh_topics": ["INTEGRATIONS.md", "OPERATIONS.md"],
        "review_topics": ["TESTING.md"],
    }
    assert mod.refresh_plan_for_changed_path(".specify/project-map/index/status.json") == {
        "must_refresh_topics": [],
        "review_topics": [],
    }
    assert mod.refresh_plan_for_changed_path(".specify/project-map/map-state.md") == {
        "must_refresh_topics": [],
        "review_topics": [],
    }


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
    assert result["must_refresh_topics"] == ["INTEGRATIONS.md", "WORKFLOWS.md"]
    assert result["review_topics"] == ["ARCHITECTURE.md", "TESTING.md"]
    assert result["suggested_topics"] == ["ARCHITECTURE.md", "INTEGRATIONS.md", "WORKFLOWS.md", "TESTING.md"]
