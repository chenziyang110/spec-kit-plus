import json
import hashlib
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

import specify_cli.specify_runtime as runtime
from specify_cli.launcher import load_runtime_launcher, resolve_runtime_launcher_argv


COGNITION_SNAPSHOT_CAPABILITIES = {
    "cognition.expansion.snapshot.v2", "cognition.claim-evidence.page.v1",
    "cognition.catalog.snapshot.v1",
}


RUNTIME_NAME = "specify-runtime.exe" if os.name == "nt" else "specify-runtime"
PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _write_runtime(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("runtime", encoding="utf-8")
    if os.name != "nt":
        path.chmod(0o755)
    return path


def test_standalone_installers_require_the_format_policy_command_chain() -> None:
    for relative_path in (
        "tools/specify-runtime/install.sh",
        "tools/specify-runtime/install.ps1",
    ):
        content = (PROJECT_ROOT / relative_path).read_text(encoding="utf-8")
        for command in (
            "scan-formats",
            "scan-policy-stage",
            "scan-policy-confirm",
            "scan-prepare",
        ):
            assert command in content, (relative_path, command)


@pytest.mark.parametrize(
    "relative_path",
    ("tools/specify-runtime/install.sh", "tools/specify-runtime/install.ps1"),
)
def test_standalone_installers_require_closeout_intent_recovery(
    relative_path: str,
) -> None:
    content = (PROJECT_ROOT / relative_path).read_text(encoding="utf-8")
    handshake_guard = content.split("Downloaded binary failed the specify-runtime API handshake")[0]
    normalized = handshake_guard.replace(r"\.", ".")

    for capability in ("cognition.closeout.inspect", "cognition.closeout.repair"):
        assert f'"{capability}"' in normalized, (relative_path, capability)


@pytest.mark.parametrize(
    "relative_path", ("tools/specify-runtime/install.sh", "tools/specify-runtime/install.ps1"),
)
def test_standalone_installers_refuse_missing_snapshot_contract_before_publication(
    relative_path: str,
) -> None:
    content = (PROJECT_ROOT / relative_path).read_text(encoding="utf-8")
    guard = content.index("Downloaded binary lacks required cognition snapshot capability")
    publish = content.index("mv -f" if relative_path.endswith(".sh") else "Move-Item -LiteralPath $candidate")
    assert guard < publish
    for capability in (
        "cognition.expansion.snapshot.v2", "cognition.claim-evidence.page.v1",
        "cognition.catalog.snapshot.v1",
    ):
        assert f'"{capability}"' in content[:guard]


def _install_native_profile(project: Path, profile: str, binary: Path) -> None:
    from specify_cli.integrations import get_integration
    from specify_cli.integrations.manifest import IntegrationManifest

    project.mkdir()
    runtime.write_project_launcher_config(project, binary)
    integration = get_integration("codex")
    integration.setup(
        project, IntegrationManifest("codex", project),
        parsed_options={"workflow_profile": profile}, script_type="ps",
    )
    (project / "user-custom.txt").write_text("user owned\n", encoding="utf-8")
    prefix = "sp" if profile == "classic" else "spx"
    entry = project / ".codex" / "skills" / f"{prefix}-quick" / "SKILL.md"
    entry.write_text(entry.read_text(encoding="utf-8") + "\nUser custom instruction\n", encoding="utf-8")


@pytest.mark.parametrize("profile", ("classic", "advanced"))
def test_current_native_snapshot_runtime_is_compatible_with_installed_profile(
    profile: str, tmp_path: Path, built_unified_runtime: Path,
) -> None:
    from specify_cli.launcher import runtime_launcher_is_compatible

    project = tmp_path / profile
    _install_native_profile(project, profile, built_unified_runtime)
    before = {str(p.relative_to(project)): p.read_bytes() for p in project.rglob("*") if p.is_file()}
    info = runtime._runtime_handshake([str(runtime.project_runtime_entrypoint_path(project))], cwd=project)
    assert info is not None
    assert COGNITION_SNAPSHOT_CAPABILITIES <= set(info["capability_ids"])
    assert runtime_launcher_is_compatible(project)
    assert before == {str(p.relative_to(project)): p.read_bytes() for p in project.rglob("*") if p.is_file()}


@pytest.mark.parametrize("profile", ("classic", "advanced"))
def test_actual_legacy_native_snapshot_runtime_is_refused_without_fixture_mutation(
    profile: str, tmp_path: Path,
) -> None:
    from specify_cli.launcher import runtime_launcher_is_compatible

    legacy_path = os.environ.get("SPECIFY_COGNITION_LEGACY_RUNTIME")
    legacy_digest = os.environ.get("SPECIFY_COGNITION_LEGACY_RUNTIME_SHA256")
    if not legacy_path or not legacy_digest:
        pytest.skip("an exact observed pre-snapshot native runtime is required")
    binary = Path(legacy_path).resolve()
    assert hashlib.sha256(binary.read_bytes()).hexdigest() == legacy_digest
    project = tmp_path / profile
    _install_native_profile(project, profile, binary)
    before = {str(p.relative_to(project)): p.read_bytes() for p in project.rglob("*") if p.is_file()}
    pinned = runtime.project_runtime_entrypoint_path(project)
    info = runtime._runtime_handshake([str(pinned)], cwd=project)
    assert info is not None
    observed = set(info["capability_ids"])
    assert set(runtime.REQUIRED_CAPABILITIES) - COGNITION_SNAPSHOT_CAPABILITIES <= observed
    assert COGNITION_SNAPSHOT_CAPABILITIES.isdisjoint(observed)
    assert not runtime.launcher_supports_required_commands([str(pinned)], cwd=project)
    assert not runtime_launcher_is_compatible(project)
    assert before == {str(p.relative_to(project)): p.read_bytes() for p in project.rglob("*") if p.is_file()}


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


@pytest.mark.parametrize(
    "missing_capabilities",
    (
        {"cognition.closeout.inspect"},
        {"cognition.closeout.repair"},
        {"cognition.closeout.inspect", "cognition.closeout.repair"},
    ),
)
def test_launcher_support_probe_rejects_runtime_without_closeout_intent_recovery(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    missing_capabilities: set[str],
) -> None:
    legacy_capabilities = sorted(
        set(runtime.REQUIRED_CAPABILITIES) - missing_capabilities
    )
    assert "cognition.closeout.apply" in legacy_capabilities
    assert "cognition.closeout.replay" in legacy_capabilities
    monkeypatch.setattr(
        runtime.subprocess,
        "run",
        lambda *_args, **_kwargs: SimpleNamespace(
            returncode=0,
            stdout=json.dumps(
                {
                    "status": "ok",
                    "data": {
                        "protocol_version": "specify-runtime.v1",
                        "capability_ids": legacy_capabilities,
                    },
                }
            ),
            stderr="",
        ),
    )

    assert not runtime.launcher_supports_required_commands(
        [str(tmp_path / RUNTIME_NAME)]
    )


def test_clean_release_without_closeout_intent_recovery_requires_replacement(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    binary = _write_runtime(tmp_path / "old" / RUNTIME_NAME)
    replacement = _write_runtime(tmp_path / "new" / RUNTIME_NAME)
    missing = {"cognition.closeout.inspect", "cognition.closeout.repair"}
    handshake = {
        "protocol_version": "specify-runtime.v1",
        "capability_ids": sorted(set(runtime.REQUIRED_CAPABILITIES) - missing),
        "cli_version": "v0.6.23",
        "source_revision": "a" * 40,
        "dirty": False,
    }
    monkeypatch.setattr(runtime, "_runtime_handshake", lambda *_args, **_kwargs: handshake)
    monkeypatch.setattr(runtime, "_source_build_marker_matches", lambda _binary: False)
    build_calls: list[tuple[Path, str]] = []

    def build_replacement(candidate: Path, version: str, _reason: str) -> Path:
        build_calls.append((candidate, version))
        return replacement

    monkeypatch.setattr(runtime, "_build_supported_binary_from_source", build_replacement)

    assert not runtime._cached_binary_is_compatible(binary, "v0.6.23")
    assert runtime._ensure_supported_binary(binary, "v0.6.23") == replacement
    assert build_calls == [(binary, "v0.6.23")]


def test_resolve_prefers_env_over_path_when_no_project_launcher(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    # Keep the bootstrap case independent of .specify state in host ancestors.
    config = tmp_path / ".specify" / "config.json"
    config.parent.mkdir(parents=True)
    config.write_text("{}", encoding="utf-8")
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
    runtime_ignore = project / ".specify" / "runtime" / ".gitignore"
    assert runtime_ignore.read_text(encoding="utf-8").splitlines() == ["*", "!.gitignore"]
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
