"""Shared test helpers for the Spec Kit test suite."""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

_ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")


def strip_ansi(text: str) -> str:
    """Remove ANSI escape codes from Rich-formatted CLI output."""
    return _ANSI_ESCAPE_RE.sub("", text)


def seed_existing_workflow_state(
    feature_dir: Path,
    *,
    stage: str,
    revision: int,
    status: str = "active",
) -> None:
    """Create a pre-existing workflow fixture without installing a gate bypass."""

    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "workflow.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "feature_id": feature_dir.name,
                "revision": revision,
                "stage": stage,
                "status": status,
                "summary": "existing workflow fixture",
                "blocker": None,
                "last_resolution_evidence": [],
                "last_reopen": None,
                "last_blocker_resolution": None,
                "acceptance_sha256": None,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


@pytest.fixture(scope="session", autouse=True)
def isolate_project_launcher_bindings(tmp_path_factory):
    """Keep generated machine-local launcher bindings out of the developer home."""

    name = "SPECIFY_PROJECT_LAUNCHER_STATE_DIR"
    previous = os.environ.get(name)
    os.environ[name] = str(tmp_path_factory.mktemp("project-launcher-bindings"))
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop(name, None)
        else:
            os.environ[name] = previous


@pytest.fixture(scope="session", autouse=True)
def isolate_claude_config_dir(tmp_path_factory: pytest.TempPathFactory):
    """Keep personal Claude skills from changing project compatibility tests."""

    name = "CLAUDE_CONFIG_DIR"
    previous = os.environ.get(name)
    os.environ[name] = str(tmp_path_factory.mktemp("claude-config"))
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop(name, None)
        else:
            os.environ[name] = previous


@pytest.fixture(scope="session")
def built_unified_runtime(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Build the shared Go runtime once for Python-to-Go integration tests."""

    source = PROJECT_ROOT / "tools" / "specify-runtime"
    suffix = ".exe" if os.name == "nt" else ""
    binary = tmp_path_factory.mktemp("unified-runtime") / f"specify-runtime{suffix}"
    subprocess.run(
        ["go", "build", "-o", str(binary), "."],
        cwd=source,
        check=True,
        capture_output=True,
        text=True,
    )
    return binary


@pytest.fixture
def unified_runtime_env(
    monkeypatch: pytest.MonkeyPatch,
    built_unified_runtime: Path,
) -> None:
    """Route one test through the freshly built unified runtime."""

    monkeypatch.setenv("SPECIFY_RUNTIME_BIN", str(built_unified_runtime))
