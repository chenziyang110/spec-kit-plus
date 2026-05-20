from pathlib import Path

from specify_cli.hooks.project_map import (
    MISSING_BASELINE_FALLBACK_GUIDANCE,
    NON_STALE_FALLBACK_GUIDANCE,
    PATH_INDEX_STALE_FALLBACK_GUIDANCE,
    STALE_FALLBACK_GUIDANCE,
    SUPPORT_DRIFT_FALLBACK_GUIDANCE,
    project_cognition_freshness_result,
    project_map_freshness_result,
)
from specify_cli.project_map_status import (
    MISSING_COGNITION_BASELINE_GUIDANCE,
    STALE_COGNITION_BASELINE_GUIDANCE,
)

from .template_utils import read_template


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _read(rel_path: str) -> str:
    return read_template(rel_path)


TARGETS = [
    "templates/commands/fast.md",
    "templates/commands/quick.md",
    "templates/commands/debug.md",
    "templates/commands/specify.md",
    "templates/commands/plan.md",
    "templates/commands/tasks.md",
    "templates/commands/implement.md",
]


def test_ordinary_sp_workflows_use_shared_project_cognition_advisory() -> None:
    shared_gate = _read("templates/command-partials/common/context-loading-gradient.md")
    lowered_gate = shared_gate.lower()

    assert "project cognition advisory" in lowered_gate
    assert "launcher-backed project cognition query planning flow" in lowered_gate
    assert "lexicon" in lowered_gate
    assert "concept_candidates" in shared_gate
    assert "selected_concepts" in shared_gate
    assert "rejected_concepts" in shared_gate
    assert "selection_reason" in shared_gate
    assert "query_plan" in shared_gate
    assert "route_pack" in shared_gate
    assert "concept selection" in lowered_gate
    assert "raw" in lowered_gate
    assert "graph json artifacts as obsolete runtime surfaces" in lowered_gate
    assert "if cognition freshness is `missing`, continue with live repository evidence" in shared_gate
    assert "if cognition freshness is `stale`, treat map output as advisory" in shared_gate
    assert "Do not treat handbook-first or layered project-map files as evidence" in shared_gate

    navigation_shim = _read("templates/command-partials/common/navigation-check.md")
    lowered_shim = navigation_shim.lower()
    assert "compatibility shim" in lowered_shim
    assert "context-loading-gradient.md" in navigation_shim
    assert "project cognition runtime" in lowered_shim
    assert "concept selection" in lowered_shim
    assert "route_pack" in navigation_shim
    assert "{{invoke:map-update}}" in navigation_shim
    assert "PROJECT-HANDBOOK.md" not in navigation_shim
    assert ".specify/project-map/index/" not in navigation_shim

    debug_content = _read("templates/commands/debug.md").lower()
    assert '{{specify-subcmd:project-cognition lexicon --intent debug --query="$arguments" --format json}}' in debug_content
    assert '{{specify-subcmd:project-cognition query --intent debug --query-plan "<query_plan_json>" --format json}}' in debug_content
    assert "minimal_live_reads" in debug_content
    assert "debug-handbook.md" not in debug_content
    assert "debug-workflow-contract" not in debug_content

    for rel_path in [path for path in TARGETS if path != "templates/commands/debug.md"]:
        content = _read(rel_path).lower()
        assert "project-cognition query" in content, f"{rel_path} missing cognition query gate"
        assert "minimal_live_reads" in content, f"{rel_path} missing minimal live read guidance"
        assert "build-handbook.md" not in content, f"{rel_path} should not keep BUILD-HANDBOOK gate"
        assert "build-workflow-contract" not in content, f"{rel_path} should not keep BUILD-WORKFLOW-CONTRACT gate"


def test_project_cognition_freshness_guidance_prefers_map_update_for_stale_runtime() -> None:
    missing = MISSING_COGNITION_BASELINE_GUIDANCE.lower()
    stale = STALE_COGNITION_BASELINE_GUIDANCE.lower()

    assert "initial project cognition baseline" in missing
    assert "/sp-map-scan" in MISSING_COGNITION_BASELINE_GUIDANCE
    assert "/sp-map-build" in MISSING_COGNITION_BASELINE_GUIDANCE
    assert "project cognition runtime" in stale
    assert stale.index("/sp-map-update") < stale.index("rebuild")
    assert "baseline is missing, unusable, schema-incompatible" in stale


def test_project_map_hook_fallback_wording_names_project_cognition_runtime(monkeypatch) -> None:
    def stale_without_reason(_project_root: Path) -> dict[str, object]:
        return {
            "freshness": "stale",
            "state": "runtime_stale",
            "readiness": "blocked",
            "recommended_next_action": "run_map_update",
            "reasons": [],
        }

    def missing_without_reason(_project_root: Path) -> dict[str, object]:
        return {"freshness": "missing", "state": "missing_baseline", "readiness": "blocked", "reasons": []}

    def unknown_without_reason(_project_root: Path) -> dict[str, object]:
        return {"freshness": "", "reasons": []}

    def support_drift_without_reason(_project_root: Path) -> dict[str, object]:
        return {
            "freshness": "support_drift",
            "state": "support_drift",
            "readiness": "blocked",
            "recommended_next_action": "commit_or_ignore_support_files",
            "reasons": [],
        }

    monkeypatch.setattr("specify_cli.hooks.project_cognition.inspect_project_cognition_freshness", stale_without_reason)
    blocked = project_map_freshness_result(PROJECT_ROOT, command_name="implement")
    assert blocked.status == "blocked"
    assert blocked.errors == [STALE_FALLBACK_GUIDANCE]
    assert "project cognition runtime freshness" in blocked.errors[0]
    assert "/sp-map-update" in blocked.errors[0]
    assert "/sp-map-scan -> /sp-map-build" in blocked.errors[0]

    monkeypatch.setattr("specify_cli.hooks.project_cognition.inspect_project_cognition_freshness", missing_without_reason)
    blocked_missing = project_map_freshness_result(PROJECT_ROOT, command_name="debug")
    assert blocked_missing.status == "blocked"
    assert blocked_missing.errors == [MISSING_BASELINE_FALLBACK_GUIDANCE]
    assert "/sp-map-scan -> /sp-map-build" in blocked_missing.errors[0]
    assert "/sp-map-update" not in blocked_missing.errors[0]

    monkeypatch.setattr("specify_cli.hooks.project_cognition.inspect_project_cognition_freshness", support_drift_without_reason)
    support = project_map_freshness_result(PROJECT_ROOT, command_name="implement")
    assert support.status == "blocked"
    assert support.errors == [SUPPORT_DRIFT_FALLBACK_GUIDANCE]
    assert "support" in support.errors[0].lower()
    assert "/sp-map-update" not in support.errors[0]

    monkeypatch.setattr("specify_cli.hooks.project_cognition.inspect_project_cognition_freshness", unknown_without_reason)
    unknown = project_map_freshness_result(PROJECT_ROOT, command_name="debug")
    assert unknown.status == "warn"
    assert unknown.warnings == [NON_STALE_FALLBACK_GUIDANCE.format(state="unknown")]
    assert "project cognition runtime freshness" in unknown.warnings[0]
    assert "/sp-map-scan -> /sp-map-build" in unknown.warnings[0]
    assert "/sp-map-update" in unknown.warnings[0]


def test_project_map_hook_blocks_path_index_stale_runtime_with_map_update_guidance(monkeypatch) -> None:
    def path_index_stale(_project_root: Path) -> dict[str, object]:
        return {
            "freshness": "stale",
            "state": "runtime_stale",
            "readiness": "blocked",
            "recommended_next_action": "run_map_update",
            "reasons": ["58 changed paths missing from project cognition path_index"],
        }

    monkeypatch.setattr("specify_cli.hooks.project_cognition.inspect_project_cognition_freshness", path_index_stale)

    blocked = project_map_freshness_result(PROJECT_ROOT, command_name="debug")

    assert blocked.status == "blocked"
    assert blocked.errors == [PATH_INDEX_STALE_FALLBACK_GUIDANCE]
    assert "path_index" in blocked.errors[0]
    assert "/sp-map-update" in blocked.errors[0]
    assert "ordinary gaps can receive provisional coverage" in blocked.errors[0]
    assert "explicit_rebuild_requested" in blocked.errors[0]
    assert "baseline_identity_invalid" in blocked.errors[0]
    assert "only when the path-index gap is unadoptable" not in blocked.errors[0]


def test_project_map_hook_ignores_guidance_path_index_when_selecting_fallback(monkeypatch) -> None:
    def stale_changed_file_with_guidance(_project_root: Path) -> dict[str, object]:
        return {
            "freshness": "stale",
            "state": "runtime_stale",
            "readiness": "blocked",
            "recommended_next_action": "run_map_update",
            "reasons": [
                "high-impact project cognition input changed: src/router/index.ts",
                PATH_INDEX_STALE_FALLBACK_GUIDANCE,
            ],
        }

    monkeypatch.setattr(
        "specify_cli.hooks.project_cognition.inspect_project_cognition_freshness",
        stale_changed_file_with_guidance,
    )

    blocked = project_map_freshness_result(PROJECT_ROOT, command_name="debug")

    assert blocked.status == "blocked"
    assert blocked.errors == [
        "high-impact project cognition input changed: src/router/index.ts",
        PATH_INDEX_STALE_FALLBACK_GUIDANCE,
    ]
    assert blocked.errors != [PATH_INDEX_STALE_FALLBACK_GUIDANCE]


def test_project_map_hook_preserves_zero_path_index_rebuild_reason(monkeypatch) -> None:
    def zero_path_index_rebuild(_project_root: Path) -> dict[str, object]:
        return {
            "freshness": "stale",
            "state": "runtime_stale",
            "readiness": "blocked",
            "recommended_next_action": "run_map_scan_build",
            "reasons": ["active_generation_has_no_path_index_rows"],
        }

    monkeypatch.setattr(
        "specify_cli.hooks.project_cognition.inspect_project_cognition_freshness",
        zero_path_index_rebuild,
    )

    blocked = project_map_freshness_result(PROJECT_ROOT, command_name="debug")

    assert blocked.status == "blocked"
    assert blocked.errors == ["active_generation_has_no_path_index_rows"]
    assert blocked.errors != [PATH_INDEX_STALE_FALLBACK_GUIDANCE]


def test_project_map_hook_preserves_unsafe_adoption_rebuild_reason(monkeypatch) -> None:
    def unsafe_adoption_rebuild(_project_root: Path) -> dict[str, object]:
        return {
            "freshness": "stale",
            "state": "runtime_stale",
            "readiness": "blocked",
            "recommended_next_action": "run_map_scan_build",
            "reasons": ["path_not_safely_adoptable_by_project_cognition_index: scripts/release/package.ps1"],
        }

    monkeypatch.setattr(
        "specify_cli.hooks.project_cognition.inspect_project_cognition_freshness",
        unsafe_adoption_rebuild,
    )

    blocked = project_map_freshness_result(PROJECT_ROOT, command_name="debug")

    assert blocked.status == "blocked"
    assert blocked.errors == ["path_not_safely_adoptable_by_project_cognition_index: scripts/release/package.ps1"]
    assert blocked.errors != [PATH_INDEX_STALE_FALLBACK_GUIDANCE]


def test_project_cognition_gate_alias_matches_project_map_gate(monkeypatch) -> None:
    def stale_without_reason(_project_root: Path) -> dict[str, object]:
        return {
            "freshness": "stale",
            "state": "runtime_stale",
            "readiness": "blocked",
            "recommended_next_action": "run_map_update",
            "reasons": [],
        }

    monkeypatch.setattr("specify_cli.hooks.project_cognition.inspect_project_cognition_freshness", stale_without_reason)
    blocked = project_cognition_freshness_result(PROJECT_ROOT, command_name="implement")
    aliased = project_map_freshness_result(PROJECT_ROOT, command_name="implement")

    assert blocked.status == "blocked"
    assert blocked.errors == aliased.errors
