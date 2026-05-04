"""Testing-system scan freshness helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Literal, TypedDict


TestingFreshness = Literal["fresh", "targeted-stale", "full-stale"]
TestingPathClassification = Literal["ignore", "targeted-stale", "full-stale"]


class TestingScanFreshnessResult(TypedDict):
    freshness: TestingFreshness
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

TEST_CONFIG_NAMES = {
    ".coveragerc",
    "coverage.xml",
    "jest.config.cjs",
    "jest.config.js",
    "jest.config.mjs",
    "jest.config.ts",
    "playwright.config.ts",
    "pytest.ini",
    "vitest.config.js",
    "vitest.config.mjs",
    "vitest.config.ts",
}

FULL_STALE_ROOT_FILES = {
    "cargo.toml",
    "go.mod",
    "noxfile.py",
    "package.json",
    "pyproject.toml",
    "setup.cfg",
    "tox.ini",
    *LOCKFILE_NAMES,
    *TEST_CONFIG_NAMES,
}


def testing_status_path(project_root: Path) -> Path:
    return project_root / ".specify" / "testing" / "status.json"


def classify_testing_changed_path(path: str) -> TestingPathClassification:
    normalized = path.replace("\\", "/").strip("/").lower()
    name = normalized.rsplit("/", 1)[-1]

    if normalized in FULL_STALE_ROOT_FILES or name in LOCKFILE_NAMES:
        return "full-stale"
    if normalized.startswith(".github/workflows/") or normalized.startswith(".gitlab/"):
        return "full-stale"
    if name in TEST_CONFIG_NAMES or _is_coverage_config(normalized):
        return "full-stale"
    if normalized.startswith("src/") or normalized.startswith("tests/"):
        return "targeted-stale"
    return "ignore"


def classify_testing_changed_files(changed_files: list[str]) -> TestingScanFreshnessResult:
    full_stale_files: list[str] = []
    targeted_stale_files: list[str] = []

    for path in changed_files:
        classification = classify_testing_changed_path(path)
        if classification == "full-stale":
            full_stale_files.append(path)
        elif classification == "targeted-stale":
            targeted_stale_files.append(path)

    freshness: TestingFreshness
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


def _is_coverage_config(path: str) -> bool:
    name = path.rsplit("/", 1)[-1]
    return name.startswith("coverage.") or name.startswith(".coverage")
