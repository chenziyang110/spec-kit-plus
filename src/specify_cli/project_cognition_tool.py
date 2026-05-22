"""Thin resolver/runner for the external project-cognition binary."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any


class ProjectCognitionToolError(RuntimeError):
    """Raised when the project-cognition binary cannot be resolved or run."""


def resolve_project_cognition_binary() -> list[str]:
    """Return the command vector for project-cognition.

    ``PROJECT_COGNITION_BIN`` may contain either a single executable path or a
    command vector separated with ``os.pathsep``. The latter keeps tests and
    Windows Python-script shims shell-free.
    """

    override = os.environ.get("PROJECT_COGNITION_BIN", "").strip()
    if override:
        parts = [part for part in override.split(os.pathsep) if part]
        if parts:
            return parts
    resolved = shutil.which("project-cognition")
    if resolved:
        return [resolved]
    raise ProjectCognitionToolError(
        "project-cognition binary not found; set PROJECT_COGNITION_BIN or install project-cognition on PATH"
    )


def run_project_cognition(
    args: list[str],
    *,
    cwd: Path,
    check: bool = True,
) -> dict[str, Any]:
    """Run project-cognition and parse its JSON object stdout."""

    command = [*resolve_project_cognition_binary(), *args]
    result = subprocess.run(
        command,
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    output = (result.stdout or "").strip()
    if check and result.returncode != 0:
        detail = (result.stderr or output or "project-cognition failed").strip()
        raise ProjectCognitionToolError(f"project-cognition {' '.join(args)} failed: {detail}")
    if not output:
        if result.returncode != 0:
            detail = (result.stderr or "project-cognition failed").strip()
            raise ProjectCognitionToolError(f"project-cognition {' '.join(args)} failed: {detail}")
        return {}
    try:
        payload = json.loads(output)
    except json.JSONDecodeError as exc:
        raise ProjectCognitionToolError(
            f"project-cognition {' '.join(args)} returned invalid JSON: {exc}"
        ) from exc
    if not isinstance(payload, dict):
        raise ProjectCognitionToolError(f"project-cognition {' '.join(args)} returned non-object JSON")
    if check and result.returncode != 0:
        detail = (result.stderr or output).strip()
        raise ProjectCognitionToolError(f"project-cognition {' '.join(args)} failed: {detail}")
    return payload

