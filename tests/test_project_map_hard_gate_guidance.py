from pathlib import Path

from specify_cli.hooks.project_map import (
    NON_STALE_FALLBACK_GUIDANCE,
    STALE_FALLBACK_GUIDANCE,
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


def test_ordinary_sp_workflows_use_shared_project_cognition_gate() -> None:
    shared_gate = _read("templates/command-partials/common/context-loading-gradient.md")
    lowered_gate = shared_gate.lower()

    assert "project cognition runtime" in lowered_gate
    assert ".specify/project-cognition/status.json" in shared_gate
    assert ".specify/project-cognition/graph/nodes.json" in shared_gate
    assert ".specify/project-cognition/graph/edges.json" in shared_gate
    assert ".specify/project-cognition/graph/claims.json" in shared_gate
    assert ".specify/project-cognition/graph/conflicts.json" in shared_gate
    assert "`missing` -> block and refresh through `sp-map-scan -> sp-map-build`" in shared_gate
    assert "`stale` -> block and refresh through `sp-map-update`" in shared_gate
    assert "Do not treat handbook-first or layered project-map files as the primary runtime read surfaces" in shared_gate

    navigation_shim = _read("templates/command-partials/common/navigation-check.md")
    lowered_shim = navigation_shim.lower()
    assert "compatibility shim" in lowered_shim
    assert "context-loading-gradient.md" in navigation_shim
    assert "project cognition runtime" in lowered_shim
    assert ".specify/project-cognition/status.json" in navigation_shim
    assert "{{invoke:map-update}}" in navigation_shim
    assert "PROJECT-HANDBOOK.md" not in navigation_shim
    assert ".specify/project-map/index/" not in navigation_shim

    debug_content = _read("templates/commands/debug.md").lower()
    assert "debug-handbook.md" in debug_content
    assert "debug-workflow-contract" in debug_content

    for rel_path in [path for path in TARGETS if path != "templates/commands/debug.md"]:
        content = _read(rel_path).lower()
        assert "build-handbook.md" in content, f"{rel_path} missing BUILD-HANDBOOK gate"
        assert "build-workflow-contract" in content, f"{rel_path} missing BUILD-WORKFLOW-CONTRACT gate"


def test_project_cognition_freshness_guidance_prefers_map_update_for_stale_runtime() -> None:
    missing = MISSING_COGNITION_BASELINE_GUIDANCE.lower()
    stale = STALE_COGNITION_BASELINE_GUIDANCE.lower()

    assert "initial project cognition baseline" in missing
    assert "/sp-map-scan" in MISSING_COGNITION_BASELINE_GUIDANCE
    assert "/sp-map-build" in MISSING_COGNITION_BASELINE_GUIDANCE
    assert "project cognition runtime" in stale
    assert stale.index("/sp-map-update") < stale.index("rebuild")
    assert "no usable baseline remains" in stale


def test_project_map_hook_fallback_wording_names_project_cognition_runtime(monkeypatch) -> None:
    def stale_without_reason(_project_root: Path) -> dict[str, object]:
        return {"freshness": "stale", "reasons": []}

    def missing_without_reason(_project_root: Path) -> dict[str, object]:
        return {"freshness": "missing", "reasons": []}

    def unknown_without_reason(_project_root: Path) -> dict[str, object]:
        return {"freshness": "", "reasons": []}

    monkeypatch.setattr("specify_cli.hooks.project_map.inspect_project_map_freshness", stale_without_reason)
    blocked = project_map_freshness_result(PROJECT_ROOT, command_name="implement")
    assert blocked.status == "blocked"
    assert blocked.errors == [STALE_FALLBACK_GUIDANCE]
    assert "project cognition runtime freshness" in blocked.errors[0]
    assert "/sp-map-update" in blocked.errors[0]
    assert "/sp-map-scan -> /sp-map-build" in blocked.errors[0]

    monkeypatch.setattr("specify_cli.hooks.project_map.inspect_project_map_freshness", missing_without_reason)
    warned = project_map_freshness_result(PROJECT_ROOT, command_name="debug")
    assert warned.status == "warn"
    assert warned.warnings == [NON_STALE_FALLBACK_GUIDANCE.format(state="missing")]
    assert "project cognition runtime freshness" in warned.warnings[0]
    assert "/sp-map-scan -> /sp-map-build" in warned.warnings[0]
    assert "/sp-map-update" in warned.warnings[0]

    monkeypatch.setattr("specify_cli.hooks.project_map.inspect_project_map_freshness", unknown_without_reason)
    unknown = project_map_freshness_result(PROJECT_ROOT, command_name="debug")
    assert unknown.status == "warn"
    assert unknown.warnings == [NON_STALE_FALLBACK_GUIDANCE.format(state="unknown")]
    assert "project cognition runtime freshness" in unknown.warnings[0]
    assert "/sp-map-scan -> /sp-map-build" in unknown.warnings[0]
    assert "/sp-map-update" in unknown.warnings[0]
