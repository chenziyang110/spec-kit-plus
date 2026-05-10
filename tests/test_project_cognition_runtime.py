from importlib import import_module
import json
from pathlib import Path

import pytest


def _write_cognition_runtime(
    project_root: Path,
    *,
    baseline_state: str = "fresh",
    slice_name: str = "change.json",
) -> None:
    cognition_dir = project_root / ".specify" / "project-cognition"
    (cognition_dir / "slices").mkdir(parents=True)
    (cognition_dir / "graph").mkdir(parents=True)
    (cognition_dir / "status.json").write_text(
        json.dumps(
            {
                "version": 1,
                "baseline_state": baseline_state,
                "baseline_commit": "abc123",
                "baseline_branch": "main",
                "baseline_built_at": "2026-05-10T00:00:00Z",
                "graph_ready": True,
                "freshness": baseline_state,
            }
        ),
        encoding="utf-8",
    )
    (cognition_dir / "slices" / slice_name).write_text(
        json.dumps(
            {
                "slice": {
                    "slice_id": slice_name.removesuffix(".json"),
                    "slice_type": slice_name.removesuffix(".json"),
                    "minimal_read_set": [
                        ".specify/project-cognition/status.json",
                        f".specify/project-cognition/slices/{slice_name}",
                    ],
                }
            }
        ),
        encoding="utf-8",
    )
    (cognition_dir / "graph" / "claims.json").write_text('{"claims": []}\n', encoding="utf-8")
    (cognition_dir / "graph" / "conflicts.json").write_text('{"conflicts": []}\n', encoding="utf-8")


def _discovery_runtime():
    try:
        return import_module("specify_cli.cognition.discovery")
    except ModuleNotFoundError as exc:
        if exc.name not in {"specify_cli.cognition.discovery"}:
            raise
        pytest.fail(f"cross-project cognition discovery helpers are missing: {exc}")


def _reference_read_runtime():
    try:
        return import_module("specify_cli.cognition.reference_read")
    except ModuleNotFoundError as exc:
        if exc.name not in {"specify_cli.cognition.reference_read"}:
            raise
        pytest.fail(f"cross-project cognition reference-read helpers are missing: {exc}")


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


def test_reference_discovery_recurses_from_explicit_root_to_nested_project_cognition(tmp_path: Path) -> None:
    runtime = _discovery_runtime()
    reference_root = tmp_path / "reference-corpus"
    nested_reference = reference_root / "vendor" / "reference-app"
    sibling_reference = reference_root / "examples" / "another-app"
    project_map_only = reference_root / "vendor" / "project-map-only"

    _write_cognition_runtime(nested_reference)
    _write_cognition_runtime(sibling_reference)
    (project_map_only / ".specify" / "project-map" / "index").mkdir(parents=True)
    (project_map_only / ".specify" / "project-map" / "index" / "status.json").write_text(
        '{"freshness": "fresh"}\n',
        encoding="utf-8",
    )

    payload = runtime.discover_reference_projects(reference_root)

    project_roots = {Path(project["root"]) for project in payload["projects"]}
    assert project_roots == {sibling_reference, nested_reference}
    assert {
        Path(project["status_path"]) for project in payload["projects"]
    } == {
        sibling_reference / ".specify" / "project-cognition" / "status.json",
        nested_reference / ".specify" / "project-cognition" / "status.json",
    }
    assert all(".specify/project-map/" not in json.dumps(project) for project in payload["projects"])


def test_reference_read_returns_admission_slice_graph_and_provenance_for_fresh_cognition(
    tmp_path: Path,
) -> None:
    runtime = _reference_read_runtime()
    fresh_reference = tmp_path / "fresh-reference"
    stale_reference = tmp_path / "stale-reference"

    _write_cognition_runtime(fresh_reference, baseline_state="fresh")
    _write_cognition_runtime(stale_reference, baseline_state="stale")

    result = runtime.read_reference_project_cognition(
        fresh_reference,
        slice_name="change",
        include_graph=["claims", "conflicts"],
    )

    assert result["admission"]["freshness"] == "fresh"
    assert result["slice"]["slice_id"] == "change"
    assert "claims" in result["graph"]
    assert "conflicts" in result["graph"]
    assert result["provenance"]["project_root"] == str(fresh_reference)
    assert ".specify/project-map/" not in json.dumps(result)

    with pytest.raises(runtime.ReferenceProjectReadError, match="fresh-only"):
        runtime.read_reference_project_cognition(stale_reference, slice_name="change")
