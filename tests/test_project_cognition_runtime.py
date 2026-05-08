from pathlib import Path
from importlib import import_module

import pytest


def test_cognition_runtime_paths_live_under_project_cognition(tmp_path: Path) -> None:
    try:
        paths = import_module("specify_cli.cognition.paths")
    except ModuleNotFoundError as exc:
        if exc.name not in {"specify_cli.cognition", "specify_cli.cognition.paths"}:
            raise
        pytest.fail(f"project cognition runtime path helpers are missing: {exc}")

    cognition_dir = paths.cognition_dir
    cognition_status_path = paths.cognition_status_path
    graph_nodes_path = paths.graph_nodes_path
    graph_edges_path = paths.graph_edges_path
    graph_claims_path = paths.graph_claims_path
    graph_conflicts_path = paths.graph_conflicts_path
    graph_slices_dir = paths.graph_slices_dir

    assert cognition_dir(tmp_path) == tmp_path / ".specify" / "project-cognition"
    assert cognition_status_path(tmp_path) == tmp_path / ".specify" / "project-cognition" / "status.json"
    assert graph_nodes_path(tmp_path) == tmp_path / ".specify" / "project-cognition" / "graph" / "nodes.json"
    assert graph_edges_path(tmp_path) == tmp_path / ".specify" / "project-cognition" / "graph" / "edges.json"
    assert graph_claims_path(tmp_path) == tmp_path / ".specify" / "project-cognition" / "graph" / "claims.json"
    assert graph_conflicts_path(tmp_path) == tmp_path / ".specify" / "project-cognition" / "graph" / "conflicts.json"
    assert graph_slices_dir(tmp_path) == tmp_path / ".specify" / "project-cognition" / "slices"
