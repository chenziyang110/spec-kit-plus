"""Artifact scaffold writer placeholder."""

from __future__ import annotations

from pathlib import Path
from typing import Any


class ArtifactScaffoldError(ValueError):
    """Raised when artifact scaffold generation fails."""


def scaffold_artifact(
    project_root: Path,
    *,
    kind: str,
    out_path: str,
    variables: dict[str, Any] | None = None,
) -> dict[str, Any]:
    raise ArtifactScaffoldError("artifact scaffold writer is not implemented")
