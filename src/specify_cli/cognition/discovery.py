"""Discovery helpers for cross-project cognition references."""

from __future__ import annotations

from pathlib import Path


def discover_reference_projects(root: Path) -> dict[str, list[dict[str, str]]]:
    """Find nested projects that expose a project-cognition status artifact."""
    projects: list[dict[str, str]] = []
    for status_path in sorted(root.rglob("status.json")):
        if status_path.parts[-3:] != (".specify", "project-cognition", "status.json"):
            continue
        project_root = status_path.parent.parent.parent
        projects.append(
            {
                "root": str(project_root),
                "status_path": str(status_path),
            }
        )
    return {"projects": projects}
