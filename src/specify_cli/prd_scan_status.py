"""PRD scan freshness helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Literal, TypedDict


PrdFreshness = Literal["fresh", "targeted-stale", "full-stale"]
PrdPathClassification = Literal["ignore", "targeted-stale", "full-stale"]


class PrdScanFreshnessResult(TypedDict):
    freshness: PrdFreshness
    relevant_changed_files: list[str]
    full_stale_files: list[str]
    targeted_stale_files: list[str]


LOCKFILE_NAMES = {
    "bun.lock",
    "bun.lockb",
    "cargo.lock",
    "composer.lock",
    "go.sum",
    "package-lock.json",
    "pnpm-lock.yaml",
    "poetry.lock",
    "uv.lock",
    "yarn.lock",
}

FULL_STALE_ROOT_FILES = {
    "agents.md",
    "project-handbook.md",
    "cargo.toml",
    "go.mod",
    "package.json",
    "pyproject.toml",
    "setup.cfg",
    *LOCKFILE_NAMES,
}

FULL_STALE_EXACT_FILES = {
    "src/specify_cli/__init__.py",
    "src/specify_cli/agents.py",
    "src/specify_cli/launcher.py",
    "src/specify_cli/workflow_markers.py",
}

FULL_STALE_PREFIXES = (
    ".github/workflows/",
    "scripts/bash/",
    "scripts/powershell/",
    "src/specify_cli/execution/",
    "src/specify_cli/hooks/",
    "src/specify_cli/integrations/",
    "src/specify_cli/orchestration/",
    "src/specify_cli/shared_hooks/",
    "templates/commands/",
    "templates/command-partials/",
    "templates/passive-skills/",
    "templates/project-map/",
    "templates/testing/",
    "templates/worker-prompts/",
)

TARGETED_STALE_PREFIXES = (
    "docs/",
    "src/",
    "templates/",
    "tests/",
)

TARGETED_STALE_ROOT_FILES = {
    "readme.md",
}


def prd_status_path(project_root: Path) -> Path:
    return project_root / ".specify" / "prd" / "status.json"


def classify_prd_changed_path(path: str) -> PrdPathClassification:
    normalized = path.replace("\\", "/").strip("/").lower()
    name = normalized.rsplit("/", 1)[-1]

    if normalized in FULL_STALE_ROOT_FILES or normalized in FULL_STALE_EXACT_FILES or name in LOCKFILE_NAMES:
        return "full-stale"
    if normalized.startswith(FULL_STALE_PREFIXES):
        return "full-stale"
    if normalized in TARGETED_STALE_ROOT_FILES or normalized.startswith(TARGETED_STALE_PREFIXES):
        return "targeted-stale"
    return "ignore"


def classify_prd_changed_files(changed_files: list[str]) -> PrdScanFreshnessResult:
    full_stale_files: list[str] = []
    targeted_stale_files: list[str] = []

    for path in changed_files:
        classification = classify_prd_changed_path(path)
        if classification == "full-stale":
            full_stale_files.append(path)
        elif classification == "targeted-stale":
            targeted_stale_files.append(path)

    freshness: PrdFreshness
    if full_stale_files:
        freshness = "full-stale"
    elif targeted_stale_files:
        freshness = "targeted-stale"
    else:
        freshness = "fresh"

    return {
        "freshness": freshness,
        "relevant_changed_files": [*full_stale_files, *targeted_stale_files],
        "full_stale_files": full_stale_files,
        "targeted_stale_files": targeted_stale_files,
    }
