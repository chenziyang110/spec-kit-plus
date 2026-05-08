"""JSON persistence helpers for the project cognition runtime."""

from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path
from typing import Any

from .paths import (
    cognition_dir,
    coverage_path,
    evidence_dir,
    graph_claims_path,
    graph_conflicts_path,
    graph_dir,
    graph_edges_path,
    graph_nodes_path,
    graph_slices_dir,
    graph_updates_path,
    provisional_dir,
)
from .schema import ClaimRecord, ConflictRecord, GraphEdge, GraphNode, SliceRecord, UpdateEventRecord


def ensure_cognition_runtime_dirs(project_root: Path) -> None:
    for directory in (
        cognition_dir(project_root),
        graph_dir(project_root),
        graph_slices_dir(project_root),
        evidence_dir(project_root),
        provisional_dir(project_root),
    ):
        directory.mkdir(parents=True, exist_ok=True)


def write_json_artifact(path: Path, payload: dict[str, object]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def read_json_artifact(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_graph_nodes(project_root: Path, nodes: list[GraphNode]) -> Path:
    ensure_cognition_runtime_dirs(project_root)
    return write_json_artifact(
        graph_nodes_path(project_root),
        {"nodes": [asdict(node) for node in nodes]},
    )


def write_graph_edges(project_root: Path, edges: list[GraphEdge]) -> Path:
    ensure_cognition_runtime_dirs(project_root)
    return write_json_artifact(
        graph_edges_path(project_root),
        {"edges": [asdict(edge) for edge in edges]},
    )


def write_graph_claims(project_root: Path, claims: list[ClaimRecord]) -> Path:
    ensure_cognition_runtime_dirs(project_root)
    return write_json_artifact(
        graph_claims_path(project_root),
        {"claims": [asdict(claim) for claim in claims]},
    )


def write_graph_conflicts(project_root: Path, conflicts: list[ConflictRecord]) -> Path:
    ensure_cognition_runtime_dirs(project_root)
    return write_json_artifact(
        graph_conflicts_path(project_root),
        {"conflicts": [asdict(conflict) for conflict in conflicts]},
    )


def write_graph_updates(project_root: Path, updates: list[UpdateEventRecord]) -> Path:
    ensure_cognition_runtime_dirs(project_root)
    return write_json_artifact(
        graph_updates_path(project_root),
        {"updates": [asdict(update) for update in updates]},
    )


def write_slice(project_root: Path, relative_name: str, slice_record: SliceRecord) -> Path:
    ensure_cognition_runtime_dirs(project_root)
    relative_path = Path(relative_name)
    if relative_path.is_absolute():
        raise ValueError("slice path must be relative to the slices directory")
    if relative_path.suffix != ".json":
        raise ValueError("slice path must end with .json")
    if any(part == ".." for part in relative_path.parts):
        raise ValueError("slice path must not escape the slices directory")
    target_path = (graph_slices_dir(project_root) / relative_path).resolve(strict=False)
    slices_root = graph_slices_dir(project_root).resolve(strict=False)
    try:
        target_path.relative_to(slices_root)
    except ValueError as exc:
        raise ValueError("slice path must stay within the slices directory") from exc
    return write_json_artifact(
        target_path,
        {"slice": asdict(slice_record)},
    )


def write_coverage(project_root: Path, payload: dict[str, object]) -> Path:
    ensure_cognition_runtime_dirs(project_root)
    return write_json_artifact(coverage_path(project_root), payload)
