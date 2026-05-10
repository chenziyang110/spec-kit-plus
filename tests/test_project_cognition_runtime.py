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


def _reference_runtime():
    try:
        return import_module("specify_cli.cognition.reference")
    except ModuleNotFoundError as exc:
        if exc.name not in {"specify_cli.cognition.reference"}:
            raise
        pytest.fail(f"cross-project cognition reference helpers are missing: {exc}")


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


def test_reference_discovery_requires_explicit_nested_project_roots(tmp_path: Path) -> None:
    runtime = _reference_runtime()
    primary = tmp_path / "primary"
    nested_reference = primary / "vendor" / "reference-app"
    project_map_only = primary / "vendor" / "project-map-only"

    _write_cognition_runtime(primary)
    _write_cognition_runtime(nested_reference)
    (project_map_only / ".specify" / "project-map" / "index").mkdir(parents=True)
    (project_map_only / ".specify" / "project-map" / "index" / "status.json").write_text(
        '{"freshness": "fresh"}\n',
        encoding="utf-8",
    )

    implicit = runtime.discover_reference_projects(primary, explicit_roots=[])
    assert implicit == []

    discovered = runtime.discover_reference_projects(primary, explicit_roots=[nested_reference, project_map_only])

    assert [item.project_root for item in discovered] == [nested_reference]
    assert discovered[0].status_path == nested_reference / ".specify" / "project-cognition" / "status.json"
    assert discovered[0].role == "supplemental"
    assert discovered[0].truth_surface == ".specify/project-cognition"


def test_reference_read_plan_admits_only_fresh_supplemental_cognition_and_keeps_minimal_order(
    tmp_path: Path,
) -> None:
    runtime = _reference_runtime()
    primary = tmp_path / "primary"
    fresh_reference = tmp_path / "fresh-reference"
    stale_reference = tmp_path / "stale-reference"

    _write_cognition_runtime(primary)
    _write_cognition_runtime(fresh_reference, baseline_state="fresh")
    _write_cognition_runtime(stale_reference, baseline_state="stale")

    plan = runtime.build_reference_read_plan(
        primary,
        explicit_roots=[fresh_reference, stale_reference],
        workflow="change",
    )

    assert [item.project_root for item in plan.admitted] == [fresh_reference]
    assert [(item.project_root, item.reason) for item in plan.rejected] == [
        (stale_reference, "cognition-not-fresh")
    ]
    assert plan.primary_project_root == primary
    assert plan.reference_mode == "supplemental-only"
    assert plan.minimal_read_order == [
        fresh_reference / ".specify" / "project-cognition" / "status.json",
        fresh_reference / ".specify" / "project-cognition" / "slices" / "change.json",
        fresh_reference / ".specify" / "project-cognition" / "graph" / "claims.json",
        fresh_reference / ".specify" / "project-cognition" / "graph" / "conflicts.json",
    ]
    assert all(".specify/project-map/" not in path.as_posix() for path in plan.minimal_read_order)
