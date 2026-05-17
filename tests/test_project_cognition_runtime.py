from importlib import import_module
import json
from pathlib import Path

import pytest


def _write_cognition_runtime(
    project_root: Path,
    *,
    baseline_state: str = "fresh",
    slice_name: str = "change.json",
    graph_ready: bool = True,
    include_db: bool = False,
) -> None:
    cognition_dir = project_root / ".specify" / "project-cognition"
    (cognition_dir / "slices").mkdir(parents=True, exist_ok=True)
    (cognition_dir / "graph").mkdir(parents=True, exist_ok=True)
    (cognition_dir / "status.json").write_text(
        json.dumps(
            {
                "version": 1,
                "baseline_state": baseline_state,
                "baseline_commit": "abc123",
                "baseline_branch": "main",
                "baseline_built_at": "2026-05-10T00:00:00Z",
                "graph_ready": graph_ready,
                "freshness": baseline_state,
            }
        ),
        encoding="utf-8",
    )
    if include_db:
        (cognition_dir / "project-cognition.db").write_bytes(b"not-opened-by-reference-read")
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


def test_reference_discovery_recurses_from_explicit_root_to_nested_project_cognition_candidates(
    tmp_path: Path,
) -> None:
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


def test_reference_discovery_reports_specify_candidates_and_cognition_completeness(
    tmp_path: Path,
) -> None:
    runtime = _discovery_runtime()
    reference_root = tmp_path / "reference-corpus"
    ready_reference = reference_root / "examples" / "ready-reference"
    stale_reference = reference_root / "vendor" / "stale-reference"
    specify_only_reference = reference_root / "vendor" / "specify-only"

    _write_cognition_runtime(ready_reference, baseline_state="fresh", include_db=True)
    _write_cognition_runtime(stale_reference, baseline_state="stale")
    (specify_only_reference / ".specify").mkdir(parents=True)

    payload = runtime.discover_reference_projects(reference_root)

    candidate_roots = {Path(candidate["root"]) for candidate in payload["specify_candidates"]}
    assert candidate_roots == {ready_reference, stale_reference, specify_only_reference}

    projects_by_root = {Path(project["root"]): project for project in payload["projects"]}
    assert set(projects_by_root) == {ready_reference, stale_reference}
    assert projects_by_root[ready_reference]["has_specify_dir"] is True
    assert projects_by_root[ready_reference]["has_project_cognition_status"] is True
    assert projects_by_root[ready_reference]["has_project_cognition_db"] is True
    assert projects_by_root[ready_reference]["freshness"] == "fresh"
    assert projects_by_root[ready_reference]["graph_ready"] is True
    assert projects_by_root[ready_reference]["reference_readiness"] == "ready"
    assert projects_by_root[ready_reference]["blockers"] == []

    assert projects_by_root[stale_reference]["reference_readiness"] == "blocked"
    assert "freshness is stale" in projects_by_root[stale_reference]["blockers"]
    assert (
        ".specify/project-cognition/project-cognition.db is missing"
        in projects_by_root[stale_reference]["blockers"]
    )

    candidates_by_root = {Path(candidate["root"]): candidate for candidate in payload["specify_candidates"]}
    assert candidates_by_root[specify_only_reference]["has_project_cognition_status"] is False
    assert candidates_by_root[specify_only_reference]["reference_readiness"] == "blocked"
    assert (
        ".specify/project-cognition/status.json is missing"
        in candidates_by_root[specify_only_reference]["blockers"]
    )


def test_reference_read_returns_admission_slice_graph_and_provenance_for_fresh_cognition(
    tmp_path: Path,
) -> None:
    runtime = _reference_read_runtime()
    fresh_reference = tmp_path / "fresh-reference"
    stale_reference = tmp_path / "stale-reference"

    _write_cognition_runtime(fresh_reference, baseline_state="fresh", include_db=True)
    _write_cognition_runtime(stale_reference, baseline_state="stale", include_db=True)

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
    assert result["minimal_read_order"] == [
        ".specify/project-cognition/status.json",
        ".specify/project-cognition/slices/change.json",
        ".specify/project-cognition/graph/claims.json",
        ".specify/project-cognition/graph/conflicts.json",
    ]
    assert ".specify/project-map/" not in json.dumps(result)

    with pytest.raises(runtime.ReferenceProjectReadError, match="fresh-only"):
        runtime.read_reference_project_cognition(stale_reference, slice_name="change")


def test_reference_read_rejects_incomplete_reference_cognition_runtime(tmp_path: Path) -> None:
    runtime = _reference_read_runtime()
    no_db_reference = tmp_path / "no-db-reference"
    graph_not_ready_reference = tmp_path / "graph-not-ready-reference"

    _write_cognition_runtime(no_db_reference, baseline_state="fresh")
    _write_cognition_runtime(
        graph_not_ready_reference,
        baseline_state="fresh",
        graph_ready=False,
        include_db=True,
    )

    with pytest.raises(runtime.ReferenceProjectReadError, match="project-cognition.db"):
        runtime.read_reference_project_cognition(no_db_reference, slice_name="change")

    with pytest.raises(runtime.ReferenceProjectReadError, match="graph_ready"):
        runtime.read_reference_project_cognition(graph_not_ready_reference, slice_name="change")


def test_reference_read_raises_controlled_error_for_missing_slice_or_malformed_json(
    tmp_path: Path,
) -> None:
    runtime = _reference_read_runtime()
    project_root = tmp_path / "reference-project"

    _write_cognition_runtime(project_root, baseline_state="fresh", include_db=True)
    (project_root / ".specify" / "project-cognition" / "slices" / "change.json").unlink()

    with pytest.raises(runtime.ReferenceProjectReadError, match="slice artifact is missing"):
        runtime.read_reference_project_cognition(project_root, slice_name="change")

    _write_cognition_runtime(project_root, baseline_state="fresh", include_db=True)
    (project_root / ".specify" / "project-cognition" / "status.json").write_text(
        "{not-json}\n",
        encoding="utf-8",
    )

    with pytest.raises(runtime.ReferenceProjectReadError, match="status artifact is malformed"):
        runtime.read_reference_project_cognition(project_root, slice_name="change")
