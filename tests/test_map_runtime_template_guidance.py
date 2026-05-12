from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _read(path: str) -> str:
    return (PROJECT_ROOT / path).read_text(encoding="utf-8")


def test_map_scan_template_targets_graph_native_runtime() -> None:
    content = _read("templates/commands/map-scan.md")

    assert ".specify/project-cognition/" in content
    assert "evidence" in content.lower()
    assert "provisional nodes" in content.lower()
    assert "candidate edges" in content.lower()
    assert "must not publish final cognition truth" in content.lower()


def test_map_build_template_targets_graph_reconstruction() -> None:
    content = _read("templates/commands/map-build.md")

    assert ".specify/project-cognition/graph/nodes.json" in content
    assert ".specify/project-cognition/graph/claims.json" in content
    assert ".specify/project-cognition/slices/" in content
    assert "conflict" in content.lower()
    assert "claim" in content.lower()


def test_map_update_template_exists_and_is_incremental() -> None:
    template_path = PROJECT_ROOT / "templates/commands/map-update.md"
    assert template_path.exists(), "map-update command template must exist for incremental cognition runtime maintenance"
    content = _read("templates/commands/map-update.md")

    assert "map-update" in content
    assert "diff" in content.lower()
    assert "user supplement" in content.lower()
    assert "incremental" in content.lower()
    assert "after recording updates, re-evaluate runtime readiness through the shared freshness contract" in content.lower()
    assert "do not report refresh completion when the runtime remains blocked" in content.lower()
    assert "partial_refresh" in content.lower()
    assert "user-supplied scope is authoritative for the touched area unless repository evidence disproves it" in content.lower()
    assert "prefer the smallest update that can truthfully restore readiness" in content.lower()
    assert "do not re-read or rewrite the full graph when status.json, graph/updates.json, and one or two affected slices are sufficient" in content.lower()
    assert "do not split small localized updates into parallel scan-style lanes just because subagents are available" in content.lower()
    assert "escalate to `sp-map-scan`, then `sp-map-build` only when the current baseline is unusable or the affected closure cannot be bounded safely" in content.lower()
