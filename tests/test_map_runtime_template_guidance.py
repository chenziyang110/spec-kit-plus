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
