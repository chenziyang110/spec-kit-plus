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


def _write_cognition_baseline(project_root: Path, *, graph_ready: bool = True) -> None:
    cognition_dir = project_root / ".specify" / "project-cognition"
    cognition_dir.mkdir(parents=True, exist_ok=True)
    (cognition_dir / "status.json").write_text(
        (
            '{"version": 3, "graph_ready": true, "baseline_state": "ready", '
            '"freshness": "fresh", "graph_store_path": ".specify/project-cognition/project-cognition.db", '
            '"active_generation_id": "GEN-0001", "query_contract_version": 1, "update_contract_version": 1}\n'
            if graph_ready
            else '{"version": 3, "graph_ready": false, "baseline_state": "missing"}\n'
        ),
        encoding="utf-8",
    )
    (cognition_dir / "project-cognition.db").write_bytes(b"SQLite test database marker")


def _write_cognition_status(project_root: Path, payload: str) -> None:
    cognition_dir = project_root / ".specify" / "project-cognition"
    cognition_dir.mkdir(parents=True, exist_ok=True)
    (cognition_dir / "status.json").write_text(payload, encoding="utf-8")


def test_project_map_status_round_trip(tmp_path):
    mod = _load_module()
    _write_cognition_baseline(tmp_path)

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
        f"{tmp_path.as_posix()}/.specify/project-cognition/status.json",
        f"{tmp_path.as_posix()}/.specify/project-cognition/project-cognition.db",
    ]


def test_mark_project_map_dirty_appends_reason_once(tmp_path):
    mod = _load_module()
    _write_cognition_baseline(tmp_path)

    mod.mark_project_map_refreshed(
        tmp_path,
        head_commit="abc123",
        branch="main",
        reason="manual",
        mapped_at="2026-04-21T00:00:00Z",
    )
    first = mod.mark_project_map_dirty(
        tmp_path,
        "shared_surface_changed",
        origin_command="implement",
        origin_feature_dir="specs/001-demo",
        origin_lane_id="lane-001",
    )
    second = mod.mark_project_map_dirty(tmp_path, "shared_surface_changed")

    assert first.dirty is True
    assert first.freshness == "stale"
    assert first.dirty_reasons == ["shared_surface_changed"]
    assert first.dirty_origin_command == "implement"
    assert first.dirty_origin_feature_dir == "specs/001-demo"
    assert first.dirty_origin_lane_id == "lane-001"
    assert second.dirty_reasons == ["shared_surface_changed"]


def test_project_map_status_round_trip_preserves_dirty_origin_metadata(tmp_path):
    mod = _load_module()
    _write_cognition_baseline(tmp_path)

    status = mod.ProjectMapStatus(
        version=2,
        global_freshness="stale",
        global_last_refresh_commit="abc123",
        global_last_refresh_at="2026-04-21T00:00:00Z",
        global_dirty=True,
        global_dirty_reasons=["workflow_contract_changed"],
        global_dirty_origin_command="implement",
        global_dirty_origin_feature_dir="specs/001-demo",
        global_dirty_origin_lane_id="lane-001",
    )

    mod.write_project_map_status(tmp_path, status)
    loaded = mod.read_project_map_status(tmp_path)

    assert loaded.dirty is True
    assert loaded.dirty_reasons == ["workflow_contract_changed"]
    assert loaded.dirty_origin_command == "implement"
    assert loaded.dirty_origin_feature_dir == "specs/001-demo"
    assert loaded.dirty_origin_lane_id == "lane-001"


def test_project_map_status_round_trip_preserves_dirty_scope_paths(tmp_path):
    mod = _load_module()
    _write_cognition_baseline(tmp_path)

    status = mod.ProjectMapStatus(
        version=2,
        global_freshness="stale",
        global_dirty=True,
        global_dirty_reasons=["shared_surface_changed"],
        global_dirty_scope_paths=["src/specify_cli/hooks/preflight.py", "templates/commands/implement.md"],
    )

    mod.write_project_map_status(tmp_path, status)
    loaded = mod.read_project_map_status(tmp_path)

    assert loaded.dirty_scope_paths == [
        "src/specify_cli/hooks/preflight.py",
        "templates/commands/implement.md",
    ]


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
    assert result["reasons"] == ["Run /sp-map-scan, then /sp-map-build to create the initial project cognition baseline."]


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


def test_complete_project_map_refresh_clears_manual_override_and_writes_refresh_fields(tmp_path):
    mod = _load_module()
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=tmp_path, check=True)
    (tmp_path / "seed.txt").write_text("seed\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "init", "-q"], cwd=tmp_path, check=True)

    mod.mark_project_map_dirty(tmp_path, "workflow_contract_changed")
    status = mod.complete_project_map_refresh(tmp_path)

    assert status.manual_force_stale is False
    assert status.manual_force_stale_reasons == []
    assert status.last_refresh_commit
    assert status.last_refresh_basis == "map-build"

    cognition_payload = (tmp_path / ".specify" / "project-cognition" / "status.json").read_text(encoding="utf-8")
    assert '"freshness": "fresh"' in cognition_payload
    assert '"manual_force_stale": false' in cognition_payload


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
    _write_cognition_baseline(tmp_path)

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
    assert stale["state"] == "runtime_stale"
    assert stale["reasons"] == [
        "high-impact project cognition input changed: src/router/index.ts",
        "Use /sp-map-update when the project cognition runtime is stale or too weak for the touched area. If no usable baseline remains, rebuild it with /sp-map-scan followed by /sp-map-build.",
    ]
    assert stale["must_refresh_topics"] == ["INTEGRATIONS.md", "WORKFLOWS.md"]
    assert stale["review_topics"] == ["ARCHITECTURE.md", "TESTING.md"]
    assert stale["suggested_topics"] == ["ARCHITECTURE.md", "INTEGRATIONS.md", "WORKFLOWS.md", "TESTING.md"]
    assert maybe["freshness"] == "possibly_stale"
    assert maybe["state"] == "runtime_stale"
    assert maybe["reasons"] == [
        "codebase surface changed since last cognition baseline: src/feature/local_fix.py",
        "Use /sp-map-update when the project cognition runtime is stale or too weak for the touched area. If no usable baseline remains, rebuild it with /sp-map-scan followed by /sp-map-build.",
    ]
    assert maybe["must_refresh_topics"] == ["STRUCTURE.md"]
    assert maybe["review_topics"] == ["ARCHITECTURE.md", "TESTING.md"]
    assert maybe["suggested_topics"] == ["ARCHITECTURE.md", "STRUCTURE.md", "TESTING.md"]
    assert fresh["freshness"] == "fresh"
    assert fresh["state"] == "fresh"
    assert fresh["reasons"] == []
    assert fresh["must_refresh_topics"] == []
    assert fresh["review_topics"] == []
    assert fresh["suggested_topics"] == []


def test_assess_project_map_freshness_classifies_support_drift(tmp_path):
    mod = _load_module()
    _write_cognition_baseline(tmp_path)

    mod.mark_project_map_refreshed(
        tmp_path,
        head_commit="base123",
        branch="main",
        reason="manual",
        mapped_at="2026-04-21T00:00:00Z",
    )

    result = mod.assess_project_map_freshness(
        tmp_path,
        head_commit="head456",
        changed_files=[".specify/templates/runtime-config.template.json"],
        has_git=True,
    )

    assert result["freshness"] == "support_drift"
    assert result["state"] == "support_drift"
    assert result["readiness"] == "blocked"
    assert result["recommended_next_action"] in {
        "commit_or_ignore_support_files",
        "review_policy_configuration",
    }
    assert any("support" in reason.lower() for reason in result["reasons"])


def test_assess_project_map_freshness_reports_partial_refresh_when_recorded_update_remains_blocked(tmp_path):
    mod = _load_module()
    _write_cognition_baseline(tmp_path)

    mod.mark_project_map_refreshed(
        tmp_path,
        head_commit="base123",
        branch="main",
        reason="topic-refresh",
        mapped_at="2026-04-21T00:00:00Z",
        refresh_topics=["STRUCTURE.md"],
        refresh_scope="partial",
        refresh_basis="topic-refresh",
        changed_files_basis=["src/feature/local_fix.py"],
    )

    result = mod.assess_project_map_freshness(
        tmp_path,
        head_commit="head456",
        changed_files=["src/routes/api.ts"],
        has_git=True,
    )

    assert result["freshness"] == "partial_refresh"
    assert result["state"] == "partial_refresh"
    assert result["readiness"] == "blocked"
    assert result["recommended_next_action"] != "retry_current_workflow"
    assert any("partial" in reason.lower() for reason in result["reasons"])


def test_assess_project_map_freshness_ignores_reference_only_project_map_changes(tmp_path):
    mod = _load_module()
    _write_cognition_baseline(tmp_path)

    mod.mark_project_map_refreshed(
        tmp_path,
        head_commit="base123",
        branch="main",
        reason="map-build",
        mapped_at="2026-05-08T00:00:00Z",
    )

    result = mod.assess_project_map_freshness(
        tmp_path,
        head_commit="head456",
        changed_files=[
            ".specify/project-map/index/status.json",
            ".specify/project-map/root/ARCHITECTURE.md",
            ".specify/project-map/worker-results/SCAN-core.json",
        ],
        has_git=True,
    )

    assert result["freshness"] == "fresh"
    assert result["reasons"] == []
    assert result["changed_files"] == [
        ".specify/project-map/index/status.json",
        ".specify/project-map/root/ARCHITECTURE.md",
        ".specify/project-map/worker-results/SCAN-core.json",
    ]


def test_classify_changed_path_treats_project_map_outputs_as_ignore_for_freshness():
    mod = _load_module()

    assert mod.classify_changed_path("PROJECT-HANDBOOK.md") == "ignore"
    assert mod.classify_changed_path(".specify/project-map/root/ARCHITECTURE.md") == "ignore"
    assert mod.classify_changed_path(".specify/project-map/index/capabilities.json") == "ignore"


def test_classify_changed_path_keeps_memory_and_template_truth_surfaces_live():
    mod = _load_module()

    assert mod.classify_changed_path(".specify/memory/constitution.md") == "stale"
    assert mod.classify_changed_path(".specify/templates/project-map/ARCHITECTURE.md") == "stale"


def test_assess_project_map_freshness_downgrades_to_review_only_when_partial_refresh_already_covers_topics(tmp_path):
    mod = _load_module()
    _write_cognition_baseline(tmp_path)

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
    assert result["state"] == "runtime_stale"
    assert result["must_refresh_topics"] == []
    assert result["review_topics"] == ["ARCHITECTURE.md", "STRUCTURE.md", "TESTING.md"]
    assert result["suggested_topics"] == ["ARCHITECTURE.md", "STRUCTURE.md", "TESTING.md"]
    assert result["reasons"] == [
        "covered topic changed since last partial cognition refresh: src/feature/local_fix.py",
        "Use /sp-map-update when the project cognition runtime is stale or too weak for the touched area. If no usable baseline remains, rebuild it with /sp-map-scan followed by /sp-map-build.",
    ]


def test_classify_changed_path_matches_shell_contract():
    mod = _load_module()

    assert mod.classify_changed_path("PROJECT-HANDBOOK.md") == "ignore"
    assert mod.classify_changed_path(".specify/project-map/root/ARCHITECTURE.md") == "ignore"
    assert mod.classify_changed_path(".specify/project-map/index/status.json") == "ignore"
    assert mod.classify_changed_path(".specify/project-map/map-state.md") == "ignore"
    assert mod.classify_changed_path(".specify/project-map/worker-results/SCAN-core.json") == "ignore"
    assert mod.classify_changed_path("docker-compose.yml") == "stale"
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
    assert mod.suggested_topics_for_changed_path("PROJECT-HANDBOOK.md") == []
    assert mod.suggested_topics_for_changed_path(".specify/project-map/root/ARCHITECTURE.md") == []
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
    assert mod.refresh_plan_for_changed_path("PROJECT-HANDBOOK.md") == {
        "must_refresh_topics": [],
        "review_topics": [],
    }
    assert mod.refresh_plan_for_changed_path(".specify/project-map/root/ARCHITECTURE.md") == {
        "must_refresh_topics": [],
        "review_topics": [],
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
    _write_cognition_baseline(tmp_path)

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
    assert any("high-impact project cognition input changed: src/api/routes.ts" == reason for reason in result["reasons"])
    assert result["must_refresh_topics"] == ["INTEGRATIONS.md", "WORKFLOWS.md"]
    assert result["review_topics"] == ["ARCHITECTURE.md", "TESTING.md"]
    assert result["suggested_topics"] == ["ARCHITECTURE.md", "INTEGRATIONS.md", "WORKFLOWS.md", "TESTING.md"]


def test_inspect_project_map_freshness_prefers_cognition_status_metadata_over_stale_compat_status(tmp_path):
    mod = _load_module()
    _write_cognition_baseline(tmp_path)
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=tmp_path, check=True)
    (tmp_path / "seed.txt").write_text("seed\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "init", "-q"], cwd=tmp_path, check=True)

    mod.write_project_map_status(
        tmp_path,
        mod.ProjectMapStatus(
            global_freshness="stale",
            global_last_refresh_commit="legacy123",
            global_last_refresh_at="2026-04-21T00:00:00Z",
            global_last_refresh_branch="main",
            global_dirty=True,
            global_dirty_reasons=["workflow_contract_changed"],
        ),
    )
    _write_cognition_status(
        tmp_path,
        """{
  "version": 2,
  "baseline_state": "ready",
  "baseline_commit": "__HEAD__",
  "baseline_branch": "main",
  "baseline_built_at": "2026-05-11T00:00:00Z",
  "graph_ready": true,
  "freshness": "fresh",
  "last_refresh_reason": "map-update",
  "last_refresh_topics": ["INTEGRATIONS.md"],
  "last_refresh_scope": "partial",
  "last_refresh_basis": "map-update",
  "manual_force_stale": false,
  "manual_force_stale_reasons": [],
  "dirty": false,
  "dirty_reasons": []
}
""",
    )
    head_commit = mod.git_head_commit(tmp_path)
    status_path = tmp_path / ".specify" / "project-cognition" / "status.json"
    status_path.write_text(status_path.read_text(encoding="utf-8").replace("__HEAD__", head_commit), encoding="utf-8")

    result = mod.inspect_project_map_freshness(tmp_path)

    assert result["freshness"] == "fresh"
    assert result["state"] == "fresh"
    assert result["dirty"] is False
    assert result["last_mapped_commit"] == head_commit
