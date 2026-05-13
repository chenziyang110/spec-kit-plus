"""Canonical filesystem layout for the project cognition runtime."""

from __future__ import annotations

from pathlib import Path


def cognition_dir(project_root: Path) -> Path:
    return project_root / ".specify" / "project-cognition"


def cognition_status_path(project_root: Path) -> Path:
    return cognition_dir(project_root) / "status.json"


def cognition_db_path(project_root: Path) -> Path:
    return cognition_dir(project_root) / "project-cognition.db"


def graph_dir(project_root: Path) -> Path:
    return cognition_dir(project_root) / "graph"


def graph_nodes_path(project_root: Path) -> Path:
    return graph_dir(project_root) / "nodes.json"


def graph_edges_path(project_root: Path) -> Path:
    return graph_dir(project_root) / "edges.json"


def graph_claims_path(project_root: Path) -> Path:
    return graph_dir(project_root) / "claims.json"


def graph_conflicts_path(project_root: Path) -> Path:
    return graph_dir(project_root) / "conflicts.json"


def graph_updates_path(project_root: Path) -> Path:
    return graph_dir(project_root) / "updates.json"


def evidence_dir(project_root: Path) -> Path:
    return cognition_dir(project_root) / "evidence"


def provisional_dir(project_root: Path) -> Path:
    return cognition_dir(project_root) / "provisional"


def provisional_nodes_path(project_root: Path) -> Path:
    return provisional_dir(project_root) / "nodes.json"


def provisional_edges_path(project_root: Path) -> Path:
    return provisional_dir(project_root) / "edges.json"


def provisional_observations_path(project_root: Path) -> Path:
    return provisional_dir(project_root) / "observations.json"


def coverage_path(project_root: Path) -> Path:
    return cognition_dir(project_root) / "coverage.json"


def graph_slices_dir(project_root: Path) -> Path:
    return cognition_dir(project_root) / "slices"
