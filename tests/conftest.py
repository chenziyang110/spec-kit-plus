"""Shared test helpers for the Spec Kit test suite."""

import atexit
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

_ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")


def _install_safe_windows_tmpdir_root() -> None:
    """Keep pytest temp roots isolated from both the repo and stale temp trees."""

    if os.name != "nt":
        return
    if os.environ.get("PYTEST_DEBUG_TEMPROOT"):
        return

    temp_root = Path(tempfile.gettempdir()) / (
        f"spk-pytest-{os.getpid()}-{uuid.uuid4().hex[:8]}"
    )
    temp_root.mkdir(parents=True, exist_ok=True)
    atexit.register(shutil.rmtree, temp_root, ignore_errors=True)
    os.environ["PYTEST_DEBUG_TEMPROOT"] = str(temp_root)


_install_safe_windows_tmpdir_root()


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
def isolate_runtime_cache_dir(tmp_path_factory: pytest.TempPathFactory):
    """Keep runtime discovery isolated from stale developer caches."""

    name = "SPECIFY_RUNTIME_CACHE_DIR"
    previous = os.environ.get(name)
    cache_dir = tmp_path_factory.mktemp("runtime-cache")
    os.environ[name] = str(cache_dir)
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
    env = os.environ.copy()
    env.setdefault("GOCACHE", str(PROJECT_ROOT / ".codex-gocache-pytest"))
    env.setdefault("GOTMPDIR", str(PROJECT_ROOT / ".codex-tmp"))
    Path(env["GOCACHE"]).mkdir(parents=True, exist_ok=True)
    Path(env["GOTMPDIR"]).mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["go", "build", "-o", str(binary), "."],
        cwd=source,
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )
    return binary


@pytest.fixture
def unified_runtime_env(
    monkeypatch: pytest.MonkeyPatch,
    built_unified_runtime: Path,
) -> None:
    """Route one test through the freshly built unified runtime."""

    monkeypatch.setenv("SPECIFY_RUNTIME_BIN", str(built_unified_runtime))
    # Local go builds from a dirty worktree embed dirty=true; tests still need them.
    monkeypatch.setenv("SPECIFY_RUNTIME_ALLOW_DIRTY", "1")
