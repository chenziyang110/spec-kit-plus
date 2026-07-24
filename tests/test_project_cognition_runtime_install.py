import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

import specify_cli.specify_runtime as runtime
from specify_cli.launcher import load_runtime_launcher, resolve_runtime_launcher_argv


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
    project = tmp_path / "project"
    project.mkdir()
    binary = _write_runtime(tmp_path / "user-cache" / RUNTIME_NAME)

    config_path = runtime.write_project_launcher_config(project, binary)

    assert config_path == project / ".specify" / "config.json"
    launcher = load_runtime_launcher(project)
    assert launcher is not None
    assert launcher.argv == (runtime.project_runtime_launcher_arg(),)
    project_binary = runtime.project_runtime_entrypoint_path(project)
    assert project_binary.read_bytes() == binary.read_bytes()
    assert resolve_runtime_launcher_argv(project) == (str(project_binary),)
    payload = json.loads(config_path.read_text(encoding="utf-8"))
    assert "runtime_launcher" in payload
    assert "project_cognition_launcher" not in payload
    assert payload["runtime_launcher_binding"]["runtime_binary_sha256"] == runtime._sha256_file(
        project_binary
    )


def test_materialize_project_runtime_uses_content_addressed_cache(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    cache = tmp_path / "cache"
    project = tmp_path / "project"
    source = _write_runtime(tmp_path / "download" / RUNTIME_NAME)
    monkeypatch.setenv("SPECIFY_RUNTIME_CACHE_DIR", str(cache))

    project_binary = runtime.materialize_project_runtime_entrypoint(project, source)
    digest = runtime._sha256_file(source)

    assert project_binary == runtime.project_runtime_entrypoint_path(project)
    assert runtime.content_addressed_runtime_path(digest) == (
        cache / "runtimes" / digest / RUNTIME_NAME
    )
    assert runtime.content_addressed_runtime_path(digest).read_bytes() == source.read_bytes()
    assert project_binary.read_bytes() == source.read_bytes()
    assert source.is_file()
    if os.name != "nt":
        assert os.access(project_binary, os.X_OK)


def test_materialize_project_runtime_rejects_symlinked_project_bin(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    project = tmp_path / "project"
    outside = tmp_path / "outside"
    source = _write_runtime(tmp_path / "download" / RUNTIME_NAME)
    (project / ".specify").mkdir(parents=True)
    outside.mkdir()
    monkeypatch.setenv("SPECIFY_RUNTIME_CACHE_DIR", str(tmp_path / "cache"))
    try:
        os.symlink(outside, project / ".specify" / "bin", target_is_directory=True)
    except (NotImplementedError, OSError) as exc:
        pytest.skip(f"directory symlinks unavailable: {exc}")

    with pytest.raises((ValueError, runtime.SpecifyRuntimeError)):
        runtime.materialize_project_runtime_entrypoint(project, source)

    assert not (outside / RUNTIME_NAME).exists()


def test_materialize_project_runtime_rejects_symlinked_source(
    tmp_path: Path,
) -> None:
    source = _write_runtime(tmp_path / "download" / RUNTIME_NAME)
    linked_source = tmp_path / "linked-runtime"
    try:
        os.symlink(source, linked_source)
    except (NotImplementedError, OSError) as exc:
        pytest.skip(f"file symlinks unavailable: {exc}")

    with pytest.raises(runtime.SpecifyRuntimeError, match="must not be a symbolic link"):
        runtime.materialize_project_runtime_entrypoint(
            tmp_path / "project",
            linked_source,
        )


def test_project_runtime_binding_does_not_persist_env_override(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    env_runtime = _write_runtime(tmp_path / "env" / RUNTIME_NAME)
    monkeypatch.setenv("SPECIFY_RUNTIME_BIN", str(env_runtime))

    runtime.write_project_launcher_config(project, env_runtime)

    payload = json.loads((project / ".specify" / "config.json").read_text(encoding="utf-8"))
    serialized = json.dumps(payload)
    assert str(env_runtime) not in serialized
    assert payload["runtime_launcher"]["argv"] == [runtime.project_runtime_launcher_arg()]
