"""Project config must use safe state reads before diagnosis or provisioning."""
from __future__ import annotations

import json
import os
from pathlib import Path
import stat
import subprocess
import sys

import pytest

from specify_cli import launcher


@pytest.fixture
def config_path(tmp_path: Path) -> Path:
    path = tmp_path.resolve() / "project 中文" / launcher.SPECIFY_CONFIG_FILE
    path.parent.mkdir(parents=True)
    return path


def test_missing_configuration_remains_unbound_without_creating_state(tmp_path: Path):
    path = tmp_path.resolve() / "absent" / launcher.SPECIFY_CONFIG_FILE
    assert launcher._load_config(path) == {}
    assert not path.parent.exists()


@pytest.mark.parametrize("payload", [
    {},
    {"user": {"note": "保留😀", "id": 9007199254740993}, "enabled": True,
     "ratio": 1.25, "optional": None},
])
def test_valid_json_preserves_values_and_does_not_write(config_path: Path, payload):
    raw = json.dumps(payload, ensure_ascii=False, indent=2).replace("\n", "\r\n").encode()
    config_path.write_bytes(raw)
    before = config_path.stat()
    assert launcher._load_config(config_path) == payload
    assert config_path.read_bytes() == raw
    assert config_path.stat().st_mtime_ns == before.st_mtime_ns


@pytest.mark.parametrize("raw", [
    b"{", b"null", b"[]", b'{"x":1,"\\u0078":2}', b'{"x":NaN}',
    b'{"x":Infinity}', b'{"x":1e999}', b'{"x":"\\ud800"}', b"\xff",
])
def test_invalid_json_remains_rejected_without_rewriting(config_path: Path, raw: bytes):
    config_path.write_bytes(raw)
    assert launcher._load_config(config_path) is None
    assert config_path.read_bytes() == raw


@pytest.mark.parametrize("kind", ["file", "dangling", "parent"])
def test_config_links_are_invalid_not_missing_or_trusted(config_path: Path, kind: str):
    target = config_path.parents[2] / "outside"
    target.mkdir()
    victim = target / "config.json"
    if kind != "dangling":
        victim.write_bytes(b'{"external":true}')
    try:
        if kind == "parent":
            config_path.parent.rmdir()
            config_path.parent.symlink_to(target, target_is_directory=True)
        else:
            config_path.symlink_to(victim)
    except (NotImplementedError, OSError) as exc:
        pytest.skip(f"symbolic links unavailable: {exc}")
    assert launcher._load_config(config_path) is None
    if kind != "dangling":
        assert victim.read_bytes() == b'{"external":true}'
    else:
        assert not victim.exists()


@pytest.mark.parametrize("kind", ["directory", "socket"])
def test_special_configuration_is_rejected_without_replacement(
    config_path: Path, kind: str, create_filesystem_socket,
):
    if kind == "directory":
        config_path.mkdir()
    else:
        # Keep the path within the Unix-domain socket length limit.
        config_path = config_path.parents[2] / "sock"
        create_filesystem_socket(config_path)
    before = config_path.lstat()
    assert launcher._load_config(config_path) is None
    assert os.path.samestat(before, config_path.lstat())
    assert config_path.lstat().st_mode == before.st_mode


def test_unreadable_config_is_not_treated_as_empty(config_path: Path, monkeypatch):
    config_path.write_text('{"retain":true}', encoding="utf-8")

    def deny_read(*args, **kwargs):
        raise PermissionError("controlled config access failure")

    monkeypatch.setattr(launcher, "read_local_state_text", deny_read)
    assert launcher._load_config(config_path) is None
    assert config_path.read_bytes() == b'{"retain":true}'


@pytest.mark.parametrize("raw", [b"{", b"[]", b'{"x":1,"x":2}', b"\xff"])
def test_invalid_config_diagnostic_precedes_other_probes(config_path: Path, monkeypatch, raw: bytes):
    config_path.write_bytes(raw)

    def forbidden(*args, **kwargs):
        pytest.fail("invalid project config must stop before other scans/probes")

    for name in ("diagnose_claude_personal_skill_shadows", "load_project_specify_launcher",
                 "runtime_launcher_is_compatible", "resolve_specify_launcher_spec"):
        monkeypatch.setattr(launcher, name, forbidden)
    issues = launcher.diagnose_project_runtime_compatibility(config_path.parents[1])
    assert len(issues) == 1
    assert issues[0]["code"] == "invalid-project-config"
    assert issues[0]["severity"] == "repairable-block"
    assert ".specify/config.json" in issues[0]["summary"]
    assert "stored digests" in issues[0]["repair"]
    assert config_path.read_bytes() == raw
    assert not (config_path.parent / "runtime").exists()


@pytest.mark.parametrize("present", [True, False])
def test_genuinely_unbound_project_keeps_existing_diagnostics(config_path: Path, present: bool):
    if present:
        config_path.write_bytes(b"{}")
    issues = launcher.diagnose_project_runtime_compatibility(config_path.parents[1])
    codes = {issue["code"] for issue in issues}
    assert "invalid-project-config" not in codes
    assert "missing-specify-runtime-launcher" in codes
    assert "missing-learning-index" in codes
    assert not (config_path.parent / "runtime").exists()


@pytest.mark.parametrize("operation", [
    "load", "load-specify", "load-runtime", "diagnose", "write-specify", "write-runtime",
])
def test_fifo_config_cannot_hang_public_consumers(config_path: Path, operation: str):
    if not hasattr(os, "mkfifo"):
        pytest.skip("named-pipe fixture requires POSIX")
    os.mkfifo(config_path)
    before = config_path.lstat()
    root = config_path.parents[2]
    script = root / "config-consumer.py"
    script.write_text('''import json, os, pathlib, sys, types
# Load complete production owners without the heavy CLI package initializer.
pkg = types.ModuleType("specify_cli")
pkg.__path__ = [sys.argv[1]]
sys.modules["specify_cli"] = pkg
from specify_cli import launcher
project, op = pathlib.Path(sys.argv[2]), sys.argv[3]
os.environ[launcher.SPECIFY_LOCAL_BINDING_ENV] = str(project.parent / "bindings")
os.environ["SPECIFY_RUNTIME_CACHE_DIR"] = str(project.parent / "cache")
path = project / launcher.SPECIFY_CONFIG_FILE
if op == "load": result = launcher._load_config(path) is None
elif op == "load-specify": result = launcher.load_project_specify_launcher(project) is None
elif op == "load-runtime": result = launcher.load_runtime_launcher(project) is None
elif op == "diagnose":
    issues = launcher.diagnose_project_runtime_compatibility(project)
    result = len(issues) == 1 and issues[0]["code"] == "invalid-project-config"
elif op == "write-specify":
    result = launcher.write_project_specify_launcher_config(
        project, launcher.current_environment_specify_launcher_spec()) is None
elif op == "write-runtime":
    result = launcher.write_runtime_launcher_config(project, project.parent / "no-runtime") is None
else: raise AssertionError(op)
print(json.dumps({"rejected": result}))
''', encoding="utf-8")
    try:
        result = subprocess.run(
            [sys.executable, "-I", "-B", str(script), str(Path(launcher.__file__).parent),
             str(config_path.parents[1]), operation],
            stdin=subprocess.DEVNULL, capture_output=True, text=True, encoding="utf-8", timeout=3,
        )
    except subprocess.TimeoutExpired:
        pytest.fail(f"{operation} blocked while reading FIFO project configuration")
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {"rejected": True}
    assert os.path.samestat(before, config_path.lstat())
    assert stat.S_ISFIFO(config_path.lstat().st_mode)
    assert config_path.lstat().st_mtime_ns == before.st_mtime_ns
    assert not (config_path.parent / "runtime").exists()
    assert not (root / "bindings").exists()
    assert not (root / "cache").exists()
