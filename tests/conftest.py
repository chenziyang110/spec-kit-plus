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


def install_passing_workflow_gate(project_root: Path) -> None:
    """Install a deterministic passing artifact gate for Go workflow fixtures."""

    specify_dir = project_root / ".specify"
    specify_dir.mkdir(parents=True, exist_ok=True)
    gate = specify_dir / "workflow-gate.py"
    gate.write_text(
        """import json

print(json.dumps({
    "status": "ok",
    "summary": "test artifact gate passed",
    "data": {},
    "items": [],
    "blockers": [],
    "show_argv": [],
    "next_argv": [],
}))
""",
        encoding="utf-8",
    )
    config_path = specify_dir / "config.json"
    try:
        payload = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        payload = {}
    payload["specify_launcher"] = {"argv": [sys.executable, str(gate)]}
    config_path.write_text(json.dumps(payload), encoding="utf-8")


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
