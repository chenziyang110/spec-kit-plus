from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _read(relative_path: str) -> str:
    return (PROJECT_ROOT / relative_path).read_text(encoding="utf-8")


def test_map_build_runtime_outputs_are_project_cognition_graph_artifacts() -> None:
    content = _read("templates/commands/map-build.md")

    assert ".specify/project-cognition/status.json" in content
    assert ".specify/project-cognition/graph/nodes.json" in content
    assert ".specify/project-cognition/graph/edges.json" in content
    assert ".specify/project-cognition/graph/claims.json" in content
    assert ".specify/project-cognition/graph/conflicts.json" in content
    assert ".specify/project-cognition/slices/" in content
    assert "build or refresh `DEBUG-HANDBOOK.md` and `BUILD-HANDBOOK.md`" not in content
    assert "runtime handbook output contract" not in content.lower()


def test_context_loading_gradient_uses_cognition_runtime_gate() -> None:
    content = _read("templates/command-partials/common/context-loading-gradient.md")
    lowered = content.lower()

    assert ".specify/project-cognition/status.json" in content
    assert ".specify/project-cognition/graph/nodes.json" in content
    assert ".specify/project-cognition/graph/edges.json" in content
    assert ".specify/project-cognition/graph/claims.json" in content
    assert ".specify/project-cognition/graph/conflicts.json" in content
    assert "graph-native" in lowered
    assert "runtime handbook gate" not in lowered
    assert "workflow handbooks as the mandatory pre-source knowledge base" not in lowered
    assert "PROJECT-HANDBOOK.md" not in content
    assert "atlas.entry" not in content
    assert "root topic document" not in lowered
    assert "module overview document" not in lowered
