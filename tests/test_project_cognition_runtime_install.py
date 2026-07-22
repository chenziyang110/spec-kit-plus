import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

import specify_cli.specify_runtime as runtime
from specify_cli.launcher import load_runtime_launcher


RUNTIME_NAME = "specify-runtime.exe" if os.name == "nt" else "specify-runtime"


def _write_runtime(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("runtime", encoding="utf-8")
    if os.name != "nt":
        path.chmod(0o755)
    return path


def test_binary_filename_uses_unified_runtime_name(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(runtime, "get_platform", lambda: ("linux", "amd64"))

    assert runtime.binary_filename() == "specify-runtime-linux-amd64"


def test_cache_and_env_use_unified_names(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("SPECIFY_RUNTIME_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setattr(runtime.platform, "system", lambda: "Windows")

    assert runtime.cache_dir() == tmp_path / "cache"
    assert runtime.cached_executable() == tmp_path / "cache" / "specify-runtime.exe"


def test_launcher_support_probe_uses_api_handshake(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    calls: list[list[str]] = []

    def fake_run(command: list[str], **_kwargs: object) -> SimpleNamespace:
        calls.append(command)
        return SimpleNamespace(
            returncode=0,
            stdout=json.dumps(
                {
                    "status": "ok",
                    "data": {
                        "protocol_version": "specify-runtime.v1",
                        "capability_ids": list(runtime.REQUIRED_CAPABILITIES),
                    },
                }
            ),
            stderr="",
        )

    monkeypatch.setattr(runtime.subprocess, "run", fake_run)

    assert runtime.launcher_supports_required_commands([str(tmp_path / RUNTIME_NAME)])
    assert calls == [[str(tmp_path / RUNTIME_NAME), "api", "handshake", "--format", "json"]]


def test_launcher_support_probe_rejects_runtime_without_artifact_data_plane(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    def fake_run(command: list[str], **_kwargs: object) -> SimpleNamespace:
        return SimpleNamespace(
            returncode=0,
            stdout=json.dumps(
                {
                    "status": "ok",
                    "data": {
                        "protocol_version": "specify-runtime.v1",
                        "capability_ids": [
                            "api.handshake",
                            "api.list",
                            "validate.spec",
                        ],
                    },
                }
            ),
            stderr="",
        )

    monkeypatch.setattr(runtime.subprocess, "run", fake_run)

    assert not runtime.launcher_supports_required_commands(
        [str(tmp_path / RUNTIME_NAME)]
    )


def test_resolve_prefers_env_over_path_when_no_project_launcher(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    env_runtime = _write_runtime(tmp_path / "env" / RUNTIME_NAME)
    path_runtime = _write_runtime(tmp_path / "path" / RUNTIME_NAME)
    monkeypatch.setenv("SPECIFY_RUNTIME_BIN", str(env_runtime))
    monkeypatch.setattr(runtime.shutil, "which", lambda _name: str(path_runtime))

    assert runtime.resolve_specify_runtime_binary(tmp_path) == [str(env_runtime)]


def test_run_specify_runtime_parses_json(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    binary = _write_runtime(tmp_path / RUNTIME_NAME)
    monkeypatch.setattr(runtime, "resolve_specify_runtime_binary", lambda _root=None: [str(binary)])

    def fake_run(command: list[str], **kwargs: object) -> SimpleNamespace:
        assert command == [str(binary), "validate", "spec", "--format", "json"]
        assert kwargs["cwd"] == tmp_path
        return SimpleNamespace(returncode=0, stdout='{"status":"ok"}', stderr="")

    monkeypatch.setattr(runtime.subprocess, "run", fake_run)

    assert runtime.run_specify_runtime(["validate", "spec", "--format", "json"], cwd=tmp_path) == {
        "status": "ok"
    }


def test_write_project_launcher_config_records_runtime_launcher(tmp_path: Path) -> None:
    binary = _write_runtime(tmp_path / ".specify" / "bin" / RUNTIME_NAME)

    config_path = runtime.write_project_launcher_config(tmp_path, binary)

    assert config_path == tmp_path / ".specify" / "config.json"
    launcher = load_runtime_launcher(tmp_path)
    assert launcher is not None
    assert launcher.argv == (str(binary),)
    payload = json.loads(config_path.read_text(encoding="utf-8"))
    assert "runtime_launcher" in payload
    assert "project_cognition_launcher" not in payload
