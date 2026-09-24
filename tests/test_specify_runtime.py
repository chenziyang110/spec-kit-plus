import ast
import importlib
import json
import os
import re
import stat
import subprocess
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = PROJECT_ROOT / "src" / "specify_cli"
RUNTIME_BINARY_NAME = "specify-runtime.exe" if os.name == "nt" else "specify-runtime"
LEGACY_BINARY_NAME = "project-cognition.exe" if os.name == "nt" else "project-cognition"


def _load_runtime() -> ModuleType:
    return importlib.import_module("specify_cli.specify_runtime")


def _write_executable(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("runtime", encoding="utf-8")
    if os.name != "nt":
        path.chmod(path.stat().st_mode | stat.S_IXUSR)
    return path


def _write_config(project_root: Path, payload: dict[str, object]) -> None:
    config_path = project_root / ".specify" / "config.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps(payload), encoding="utf-8")


def test_required_runtime_contract_uses_the_current_workflow_surface() -> None:
    runtime = _load_runtime()

    workflow_capabilities = {
        capability
        for capability in runtime.REQUIRED_CAPABILITIES
        if capability.startswith("workflow.")
    }
    assert workflow_capabilities == {
        "workflow.show",
        "workflow.ensure",
        "workflow.enter",
        "workflow.next",
        "workflow.complete-stage",
        "workflow.transition",
        "workflow.reopen",
        "workflow.block",
        "workflow.reconcile-blocker",
        "workflow.resolve",
        "workflow.closeout",
    }
    assert "workflow.start" not in runtime.REQUIRED_CAPABILITIES
    assert "workflow.status" not in runtime.REQUIRED_CAPABILITIES


def test_required_runtime_contract_matches_the_shipped_agent_surface() -> None:
    runtime = _load_runtime()
    source = (PROJECT_ROOT / "tools" / "specify-runtime" / "main.go").read_text(
        encoding="utf-8"
    )
    start = source.index("func defaultCapabilities() []string")
    end = source.index("func defaultCapabilityCards()", start)
    shipped = set(
        re.findall(
            r'"([a-z][a-z0-9-]*(?:\.[a-z][a-z0-9-]*)+)"',
            source[start:end],
        )
    )

    # Recovery is negotiated when needed; existing installations need not
    # support it to keep running unrelated workflows.
    assert set(runtime.REQUIRED_CAPABILITIES) | {"tasks.rebind"} == shipped


def test_tasks_rebind_is_discoverable_without_raising_installation_minimum(
    built_unified_runtime: Path,
) -> None:
    runtime = _load_runtime()
    assert "tasks.rebind" not in runtime.REQUIRED_CAPABILITIES

    result = subprocess.run(
        [
            str(built_unified_runtime), "api", "ensure",
            "--capabilities", "tasks.rebind", "--format", "json",
        ],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    assert payload["status"] == "ok"
    assert payload["data"]["present"] == ["tasks.rebind"]
    assert payload["data"]["missing"] == []


def test_required_runtime_contract_retires_run_without_retiring_shared_execution() -> None:
    capabilities = set(_load_runtime().REQUIRED_CAPABILITIES)
    assert not any(
        capability.startswith(("run.", "candidate.", "cas.", "sync."))
        for capability in capabilities
    )
    assert {cap for cap in capabilities if cap.startswith("result.")} == {
        "result.path", "result.submit"
    }
    assert {cap for cap in capabilities if cap.startswith("accept.")} == {
        "accept.prepare", "accept.validate", "accept.route-repair", "accept.closeout"
    }
    assert {
        "work.claim", "work.checkpoint", "work.finish", "work.interrupt",
        "board.show", "board.branch-policy", "board.feature-bootstrap",
        "execution.announce", "execution.guard", "execution.checkpoint",
        "execution.complete", "review.prepare", "review.validate", "review.closeout",
    } <= capabilities


@pytest.mark.parametrize(
    "missing",
    (None, "execution.guard", "work.claim", "board.branch-policy", "result.submit", "review.closeout", "accept.validate"),
)
def test_runtime_handshake_accepts_retirement_but_requires_shared_guards(
    monkeypatch: pytest.MonkeyPatch, missing: str | None
) -> None:
    runtime = _load_runtime()
    retired = {
        "result.list", "result.show", "result.reopen", "result.depend", "accept.receipt"
    }
    capabilities = [
        cap for cap in runtime.REQUIRED_CAPABILITIES
        if not cap.startswith(("run.", "candidate.", "cas.", "sync."))
        and cap not in retired and cap != missing
    ]
    monkeypatch.setattr(
        runtime,
        "_runtime_handshake",
        lambda *_a, **_k: {
            "protocol_version": runtime.EXPECTED_RUNTIME_PROTOCOL,
            "capability_ids": capabilities,
        },
    )
    assert runtime.launcher_supports_required_commands(["specify-runtime"]) is (missing is None)


@pytest.mark.parametrize(
    "retired",
    (
        "run.launch", "run.supervise", "run.integrate", "candidate.build",
        "candidate.review", "candidate.show", "result.list", "result.show",
        "result.reopen", "result.depend", "accept.receipt", "cas.publish", "sync.safe",
    ),
)
def test_runtime_handshake_rejects_cached_binary_with_retired_surface(
    monkeypatch: pytest.MonkeyPatch, retired: str
) -> None:
    runtime = _load_runtime()
    monkeypatch.setattr(
        runtime, "_runtime_handshake",
        lambda *_a, **_k: {
            "protocol_version": runtime.EXPECTED_RUNTIME_PROTOCOL,
            "capability_ids": [*runtime.REQUIRED_CAPABILITIES, retired],
        },
    )
    assert not runtime.launcher_supports_required_commands(["specify-runtime"])


def test_runtime_handshake_allows_unrelated_additive_capabilities(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime = _load_runtime()
    monkeypatch.setattr(
        runtime, "_runtime_handshake",
        lambda *_a, **_k: {
            "protocol_version": runtime.EXPECTED_RUNTIME_PROTOCOL,
            "capability_ids": [*runtime.REQUIRED_CAPABILITIES, "example.extra"],
        },
    )
    assert runtime.launcher_supports_required_commands(["specify-runtime"])


@pytest.mark.parametrize(
    "capability",
    ("cognition.closeout.inspect", "cognition.closeout.repair"),
)
def test_required_runtime_contract_includes_closeout_intent_recovery(
    capability: str,
) -> None:
    runtime = _load_runtime()

    assert capability in runtime.REQUIRED_CAPABILITIES


@pytest.mark.parametrize(
    "capability",
    (
        "evidence.smoothness-manifest",
        "evidence.smoothness-validate",
    ),
)
def test_required_runtime_contract_includes_smoothness_evidence(
    capability: str,
) -> None:
    runtime = _load_runtime()

    assert capability in runtime.REQUIRED_CAPABILITIES


@pytest.mark.parametrize(
    "capability",
    (
        "evidence.source-continuity-manifest",
        "evidence.source-continuity-adapter-catalog",
        "evidence.source-continuity-adapter-bridge",
        "evidence.source-continuity-adapter-probe",
        "evidence.source-continuity-adapter-plan",
        "evidence.source-continuity-adapter-execution",
        "evidence.source-continuity-validate",
    ),
)
def test_required_runtime_contract_includes_source_continuity_lab(
    capability: str,
) -> None:
    runtime = _load_runtime()

    assert capability in runtime.REQUIRED_CAPABILITIES


def test_runtime_resolver_prefers_project_fixed_launcher(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runtime = _load_runtime()
    project_binary = _write_executable(
        tmp_path / ".specify" / "bin" / RUNTIME_BINARY_NAME
    )
    env_binary = _write_executable(tmp_path / "env" / RUNTIME_BINARY_NAME)
    path_binary = _write_executable(tmp_path / "path" / RUNTIME_BINARY_NAME)
    legacy_binary = _write_executable(tmp_path / "legacy" / LEGACY_BINARY_NAME)
    runtime.write_project_launcher_config(tmp_path, project_binary)
    config_path = tmp_path / ".specify" / "config.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    config["runtime_launcher"]["command"] = "pwsh -Command SHOULD_NOT_BE_TRUSTED"
    config["project_cognition_launcher"] = {
        "command": str(legacy_binary),
        "argv": [str(legacy_binary)],
    }
    _write_config(
        tmp_path,
        config,
    )
    monkeypatch.setenv("SPECIFY_RUNTIME_BIN", str(env_binary))
    monkeypatch.setenv("PROJECT_COGNITION_BIN", str(legacy_binary))
    monkeypatch.setattr(runtime.shutil, "which", lambda _name: str(path_binary))

    resolved = runtime.resolve_specify_runtime_binary(tmp_path)

    assert resolved == [str(project_binary)]


def test_runtime_resolver_uses_new_env_and_ignores_legacy_config_and_env(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runtime = _load_runtime()
    env_binary = _write_executable(tmp_path / "env" / RUNTIME_BINARY_NAME)
    legacy_binary = _write_executable(tmp_path / "legacy" / LEGACY_BINARY_NAME)
    path_binary = _write_executable(tmp_path / "path" / RUNTIME_BINARY_NAME)
    _write_config(
        tmp_path,
        {
            "project_cognition_launcher": {
                "command": str(legacy_binary),
                "argv": [str(legacy_binary)],
            }
        },
    )
    monkeypatch.setenv("SPECIFY_RUNTIME_BIN", str(env_binary))
    monkeypatch.setenv("PROJECT_COGNITION_BIN", str(legacy_binary))
    monkeypatch.setattr(runtime.shutil, "which", lambda _name: str(path_binary))

    resolved = runtime.resolve_specify_runtime_binary(tmp_path)

    assert resolved == [str(env_binary)]


def test_runtime_env_is_one_executable_path_not_an_argv_vector(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = _load_runtime()
    configured = f"runtime{os.pathsep}with-separator"
    monkeypatch.setenv("SPECIFY_RUNTIME_BIN", configured)

    assert runtime._env_argv() == [configured]


def test_source_bound_runtime_binding_metadata_requires_matching_source_fingerprint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = _load_runtime()
    launcher = SimpleNamespace(
        kind="source_bound",
        argv=(
            "uvx",
            "--from",
            "git+https://github.com/chenziyang110/spec-kit-plus.git@" + ("a" * 40),
            "specify",
        ),
    )
    monkeypatch.setattr(
        "specify_cli.launcher.resolve_specify_launcher_spec",
        lambda: launcher,
    )
    monkeypatch.setattr(
        runtime,
        "_bundled_runtime_source",
        lambda: PROJECT_ROOT / "tools" / "specify-runtime",
    )

    metadata = runtime.current_runtime_binding_metadata()

    assert metadata["binding_version"] == runtime.RUNTIME_LAUNCHER_BINDING_VERSION
    assert metadata["specify_launcher_kind"] == "source_bound"
    assert metadata["specify_launcher_argv"] == list(launcher.argv)
    assert metadata["source_build_required"] is True
    assert metadata["runtime_source_sha256"] == runtime._source_fingerprint(
        PROJECT_ROOT / "tools" / "specify-runtime"
    )
    drifted = dict(metadata)
    drifted["runtime_source_sha256"] = "stale"
    assert runtime.runtime_binding_metadata_matches(metadata, metadata) is True
    assert runtime.runtime_binding_metadata_matches(drifted, metadata) is False


def test_local_checkout_runtime_binding_requires_matching_source_fingerprint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = _load_runtime()
    launcher = SimpleNamespace(kind="local_environment", argv=("specify",))
    source_dir = PROJECT_ROOT / "tools" / "specify-runtime"
    monkeypatch.setattr(
        "specify_cli.launcher.resolve_specify_launcher_spec",
        lambda: launcher,
    )
    monkeypatch.setattr(runtime, "_local_runtime_source_checkout", lambda: source_dir)
    monkeypatch.setattr(runtime, "_bundled_runtime_source", lambda: source_dir)

    metadata = runtime.current_runtime_binding_metadata()

    assert metadata["specify_launcher_kind"] == "local_environment"
    assert "specify_launcher_argv" not in metadata
    assert metadata["source_build_required"] is True
    assert metadata["runtime_source_sha256"] == runtime._source_fingerprint(source_dir)
    drifted = dict(metadata)
    drifted["runtime_source_sha256"] = "stale"
    assert runtime.runtime_binding_metadata_matches(metadata, metadata) is True
    assert runtime.runtime_binding_metadata_matches(drifted, metadata) is False


def test_runtime_resolver_falls_back_only_to_specify_runtime_on_path(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runtime = _load_runtime()
    path_binary = _write_executable(tmp_path / "path" / RUNTIME_BINARY_NAME)
    legacy_binary = _write_executable(tmp_path / "legacy" / LEGACY_BINARY_NAME)
    requested: list[str] = []

    monkeypatch.delenv("SPECIFY_RUNTIME_BIN", raising=False)
    monkeypatch.setenv("PROJECT_COGNITION_BIN", str(legacy_binary))

    def fake_which(name: str) -> str | None:
        requested.append(name)
        return str(path_binary) if name == "specify-runtime" else str(legacy_binary)

    monkeypatch.setattr(runtime.shutil, "which", fake_which)

    resolved = runtime.resolve_specify_runtime_binary(tmp_path)

    assert resolved == [str(path_binary)]
    assert requested == ["specify-runtime"]


@pytest.mark.parametrize(
    "args",
    [
        ["cognition", "check", "--format", "json"],
        ["validate", "spec", "--feature-dir", ".", "--format", "json"],
    ],
)
def test_runtime_runner_uses_unified_namespaced_argv(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    args: list[str],
) -> None:
    runtime = _load_runtime()
    binary = _write_executable(tmp_path / RUNTIME_BINARY_NAME)
    calls: list[tuple[list[str], dict[str, object]]] = []

    monkeypatch.setattr(
        runtime,
        "resolve_specify_runtime_binary",
        lambda project_root=None: [str(binary)],
    )

    def fake_run(command: list[str], **kwargs: object) -> SimpleNamespace:
        calls.append((command, kwargs))
        return SimpleNamespace(returncode=0, stdout='{"ok":true}', stderr="")

    monkeypatch.setattr(runtime.subprocess, "run", fake_run)

    result = runtime.run_specify_runtime(args, cwd=tmp_path)

    assert result == {"ok": True}
    assert calls[0][0] == [str(binary), *args]
    assert "project-cognition" not in calls[0][0]
    assert "spec-lint" not in calls[0][0]


@pytest.mark.parametrize(
    ("args", "expected_timeout"),
    [
        (["quick", "status", "Q-123", "--format", "json"], 35.0),
        (
            ["artifact", "show", "--path", "spec.md", "--format", "json"],
            35.0,
        ),
        (
            ["artifact", "show-many", "--input-json", '{"queries":[]}', "--format", "json"],
            35.0,
        ),
        (["validate", "spec", "--feature-dir", ".", "--format", "json"], 305.0),
        (
            ["execution", "announce", "--workflow", "implement", "--format", "json"],
            305.0,
        ),
    ],
)
def test_runtime_runner_applies_a_bounded_timeout_to_every_command(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    args: list[str],
    expected_timeout: float,
) -> None:
    runtime = _load_runtime()
    binary = _write_executable(tmp_path / RUNTIME_BINARY_NAME)
    calls: list[dict[str, object]] = []
    monkeypatch.delenv("SPECIFY_RUNTIME_TIMEOUT_SECONDS", raising=False)
    monkeypatch.setattr(
        runtime,
        "resolve_specify_runtime_binary",
        lambda project_root=None: [str(binary)],
    )

    def fake_run(_command: list[str], **kwargs: object) -> SimpleNamespace:
        calls.append(kwargs)
        return SimpleNamespace(returncode=0, stdout='{"status":"ok"}', stderr="")

    monkeypatch.setattr(runtime.subprocess, "run", fake_run)

    runtime.run_specify_runtime(args, cwd=tmp_path)

    assert calls[0]["timeout"] == expected_timeout


def test_runtime_runner_converts_timeout_into_a_diagnostic_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runtime = _load_runtime()
    binary = _write_executable(tmp_path / RUNTIME_BINARY_NAME)
    monkeypatch.delenv("SPECIFY_RUNTIME_TIMEOUT_SECONDS", raising=False)
    monkeypatch.setattr(
        runtime,
        "resolve_specify_runtime_binary",
        lambda project_root=None: [str(binary)],
    )

    def fake_run(command: list[str], **kwargs: object) -> SimpleNamespace:
        raise runtime.subprocess.TimeoutExpired(command, kwargs["timeout"])

    monkeypatch.setattr(runtime.subprocess, "run", fake_run)

    with pytest.raises(
        runtime.SpecifyRuntimeError,
        match=r"specify-runtime quick status timed out after 35 seconds",
    ):
        runtime.run_specify_runtime(
            ["quick", "status", "Q-123", "--format", "json"],
            cwd=tmp_path,
        )


@pytest.mark.parametrize("value", ["0", "-1", "forever"])
def test_runtime_runner_rejects_unbounded_or_invalid_timeout_configuration(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    value: str,
) -> None:
    runtime = _load_runtime()
    binary = _write_executable(tmp_path / RUNTIME_BINARY_NAME)
    monkeypatch.setenv("SPECIFY_RUNTIME_TIMEOUT_SECONDS", value)
    monkeypatch.setattr(
        runtime,
        "resolve_specify_runtime_binary",
        lambda project_root=None: [str(binary)],
    )
    monkeypatch.setattr(
        runtime.subprocess,
        "run",
        lambda *_args, **_kwargs: SimpleNamespace(
            returncode=0,
            stdout='{"status":"ok"}',
            stderr="",
        ),
    )

    with pytest.raises(
        runtime.SpecifyRuntimeError,
        match="SPECIFY_RUNTIME_TIMEOUT_SECONDS must be a positive number of seconds",
    ):
        runtime.run_specify_runtime(["api", "list", "--format", "json"], cwd=tmp_path)


def test_runtime_runner_unwraps_cognition_envelope_for_existing_python_consumers(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runtime = _load_runtime()
    binary = _write_executable(tmp_path / RUNTIME_BINARY_NAME)
    monkeypatch.setattr(
        runtime,
        "resolve_specify_runtime_binary",
        lambda project_root=None: [str(binary)],
    )

    def fake_run(command: list[str], **kwargs: object) -> SimpleNamespace:
        return SimpleNamespace(
            returncode=0,
            stdout=json.dumps(
                {
                    "status": "ok",
                    "summary": "cognition completed",
                    "data": {"freshness": "fresh", "readiness": "query_ready"},
                    "items": [],
                    "blockers": [],
                    "show_argv": [],
                    "next_argv": [],
                }
            ),
            stderr="",
        )

    monkeypatch.setattr(runtime.subprocess, "run", fake_run)

    result = runtime.run_specify_runtime(
        ["cognition", "check", "--format", "json"], cwd=tmp_path
    )

    assert result == {"freshness": "fresh", "readiness": "query_ready"}


@pytest.mark.parametrize("status", ["blocked", "repairable-block"])
def test_runtime_runner_returns_structured_cognition_blockers(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    status: str,
) -> None:
    runtime = _load_runtime()
    binary = _write_executable(tmp_path / RUNTIME_BINARY_NAME)
    monkeypatch.setattr(
        runtime,
        "resolve_specify_runtime_binary",
        lambda project_root=None: [str(binary)],
    )
    blocker = {
        "status": status,
        "readiness": "blocked",
        "error_code": "unsupported_legacy_runtime",
        "recommended_next_action": "run_map_scan_build",
    }

    def fake_run(command: list[str], **kwargs: object) -> SimpleNamespace:
        return SimpleNamespace(
            returncode=10,
            stdout=json.dumps(
                {
                    "status": status,
                    "summary": "project cognition command did not complete",
                    "data": blocker,
                    "items": [],
                    "blockers": [],
                    "show_argv": [],
                    "next_argv": [],
                }
            ),
            stderr="",
        )

    monkeypatch.setattr(runtime.subprocess, "run", fake_run)

    result = runtime.run_specify_runtime(
        ["cognition", "check", "--format", "json"], cwd=tmp_path
    )

    assert result == blocker


@pytest.mark.parametrize("status", ["blocked", "repairable-block"])
def test_runtime_runner_preserves_structured_non_cognition_blockers(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    status: str,
) -> None:
    runtime = _load_runtime()
    binary = _write_executable(tmp_path / RUNTIME_BINARY_NAME)
    monkeypatch.setattr(
        runtime,
        "resolve_specify_runtime_binary",
        lambda project_root=None: [str(binary)],
    )
    envelope = {
        "status": status,
        "summary": "Work Board storage needs agent-owned recovery",
        "data": {
            "error_code": "run_control_store_unavailable",
            "recovery_owner": "agent",
        },
        "items": [],
        "blockers": [{"code": "run_control_store_unavailable"}],
        "show_argv": ["specify-runtime", "board", "show", "--format", "json"],
        "next_argv": [],
    }

    monkeypatch.setattr(
        runtime.subprocess,
        "run",
        lambda *_args, **_kwargs: SimpleNamespace(
            returncode=10, stdout=json.dumps(envelope), stderr=""
        ),
    )

    assert runtime.run_specify_runtime(
        ["board", "reconcile", "--format", "json"], cwd=tmp_path
    ) == envelope


def test_runtime_runner_still_raises_for_cognition_usage_errors(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runtime = _load_runtime()
    binary = _write_executable(tmp_path / RUNTIME_BINARY_NAME)
    monkeypatch.setattr(
        runtime,
        "resolve_specify_runtime_binary",
        lambda project_root=None: [str(binary)],
    )

    def fake_run(command: list[str], **kwargs: object) -> SimpleNamespace:
        return SimpleNamespace(
            returncode=2,
            stdout=json.dumps(
                {
                    "status": "usage-error",
                    "summary": "invalid cognition arguments",
                    "data": {"error": "missing input"},
                    "items": [],
                    "blockers": [],
                    "show_argv": [],
                    "next_argv": [],
                }
            ),
            stderr="",
        )

    monkeypatch.setattr(runtime.subprocess, "run", fake_run)

    with pytest.raises(runtime.SpecifyRuntimeError, match="invalid cognition arguments"):
        runtime.run_specify_runtime(
            ["cognition", "query", "--format", "json"], cwd=tmp_path
        )


def test_runtime_runner_can_install_when_missing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runtime = _load_runtime()
    binary = _write_executable(tmp_path / RUNTIME_BINARY_NAME)
    calls: list[list[str]] = []

    def missing_runtime(_project_root: Path | None = None) -> list[str]:
        raise runtime.SpecifyRuntimeError("runtime missing")

    monkeypatch.setattr(runtime, "resolve_specify_runtime_binary", missing_runtime)
    monkeypatch.setattr(runtime, "ensure_binary", lambda: binary)

    def fake_run(command: list[str], **_kwargs: object) -> SimpleNamespace:
        calls.append(command)
        return SimpleNamespace(returncode=0, stdout='{"status":"ok"}', stderr="")

    monkeypatch.setattr(runtime.subprocess, "run", fake_run)

    payload = runtime.run_specify_runtime(
        ["validate", "spec", "--feature-dir", "."],
        cwd=tmp_path,
        install_if_missing=True,
    )

    assert payload == {"status": "ok"}
    assert calls == [[str(binary), "validate", "spec", "--feature-dir", "."]]


def test_download_urls_default_to_official_source_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = _load_runtime()
    monkeypatch.delenv("SPECIFY_RUNTIME_DOWNLOAD_MIRRORS", raising=False)
    monkeypatch.setattr(runtime, "binary_filename", lambda: "specify-runtime-linux-amd64")

    urls = runtime.download_urls("v0.6.9")

    assert urls == [(
        "https://github.com/chenziyang110/spec-kit-plus-releases/releases/download/"
        "v0.6.9/specify-runtime-linux-amd64"
    )]


def test_download_urls_honor_custom_mirror_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = _load_runtime()
    monkeypatch.setenv(
        "SPECIFY_RUNTIME_DOWNLOAD_MIRRORS",
        "{github_url},https://example.invalid/cdn/{filename}",
    )
    monkeypatch.setattr(runtime, "binary_filename", lambda: "specify-runtime-linux-amd64")

    urls = runtime.download_urls("v1.2.3")

    assert urls == [
        "https://github.com/chenziyang110/spec-kit-plus-releases/releases/download/"
        "v1.2.3/specify-runtime-linux-amd64",
        "https://example.invalid/cdn/specify-runtime-linux-amd64",
    ]


def test_download_tries_next_mirror_when_first_source_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runtime = _load_runtime()
    dest = tmp_path / "runtime.bin"
    attempted: list[str] = []

    monkeypatch.setattr(
        runtime,
        "download_urls",
        lambda _version: [
            "https://primary.example/fail",
            "https://mirror.example/ok",
        ],
    )
    monkeypatch.setattr(runtime, "cache_dir", lambda: tmp_path)
    monkeypatch.setattr(runtime, "binary_filename", lambda: "specify-runtime-linux-amd64")
    monkeypatch.setattr(runtime, "_download_timeout_seconds", lambda: 5.0)

    def fake_download(url: str, destination: Path, *, timeout: float) -> None:
        attempted.append(url)
        if "fail" in url:
            raise runtime.SpecifyRuntimeError("primary unavailable")
        destination.write_bytes(b"x" * 2048)

    monkeypatch.setattr(runtime, "_download_from_url", fake_download)

    result = runtime.download("v0.6.9", dest)

    assert result == dest
    assert attempted == [
        "https://primary.example/fail",
        "https://mirror.example/ok",
    ]
    assert dest.stat().st_size >= 1024


def test_download_uses_authenticated_github_cli_before_mirrors(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runtime = _load_runtime()
    dest = tmp_path / "runtime.bin"
    filename = "specify-runtime-windows-amd64.exe"
    official = (
        "https://github.com/chenziyang110/spec-kit-plus-releases/releases/latest/download/"
        f"{filename}"
    )
    mirror = f"https://mirror.example/{official}"
    http_attempts: list[str] = []
    github_cli_attempts: list[str] = []

    monkeypatch.setattr(runtime, "download_urls", lambda _version: [official, mirror])
    monkeypatch.setattr(runtime, "cache_dir", lambda: tmp_path)
    monkeypatch.setattr(runtime, "binary_filename", lambda: filename)
    monkeypatch.setattr(runtime, "_download_timeout_seconds", lambda: 5.0)

    def fake_download(url: str, _destination: Path, *, timeout: float) -> None:
        assert timeout == 5.0
        http_attempts.append(url)
        if url == official:
            raise runtime.SpecifyRuntimeError("HTTP 404")
        raise AssertionError("mirror must not run after authenticated download succeeds")

    def fake_github_cli(version: str, destination: Path) -> Path:
        github_cli_attempts.append(version)
        destination.write_bytes(b"x" * 2048)
        return destination

    monkeypatch.setattr(runtime, "_download_from_url", fake_download)
    monkeypatch.setattr(
        runtime,
        "_download_with_github_cli",
        fake_github_cli,
        raising=False,
    )

    result = runtime.download("latest", dest)

    assert result == dest
    assert http_attempts == [official]
    assert github_cli_attempts == ["latest"]


def test_download_continues_to_mirror_when_authenticated_github_cli_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runtime = _load_runtime()
    dest = tmp_path / "runtime.bin"
    filename = "specify-runtime-windows-amd64.exe"
    official = (
        "https://github.com/chenziyang110/spec-kit-plus-releases/releases/latest/download/"
        f"{filename}"
    )
    mirror = f"https://mirror.example/{filename}"
    http_attempts: list[str] = []

    monkeypatch.setattr(runtime, "download_urls", lambda _version: [official, mirror])
    monkeypatch.setattr(runtime, "cache_dir", lambda: tmp_path)
    monkeypatch.setattr(runtime, "binary_filename", lambda: filename)
    monkeypatch.setattr(runtime, "_download_timeout_seconds", lambda: 5.0)

    def fake_download(url: str, destination: Path, *, timeout: float) -> None:
        assert timeout == 5.0
        http_attempts.append(url)
        if url == official:
            raise runtime.SpecifyRuntimeError("HTTP 404")
        destination.write_bytes(b"x" * 2048)

    def fail_github_cli(_version: str, _destination: Path) -> Path:
        raise runtime.SpecifyRuntimeError("gh auth unavailable")

    monkeypatch.setattr(runtime, "_download_from_url", fake_download)
    monkeypatch.setattr(runtime, "_download_with_github_cli", fail_github_cli)
    monkeypatch.setattr(runtime, "_download_with_github_api", fail_github_cli, raising=False)

    result = runtime.download("latest", dest)

    assert result == dest
    assert http_attempts == [official, mirror]


@pytest.mark.parametrize(
    ("version", "tag_args"),
    (("latest", []), ("v0.6.22", ["v0.6.22"])),
)
def test_authenticated_github_cli_download_uses_local_credential_store(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    version: str,
    tag_args: list[str],
) -> None:
    runtime = _load_runtime()
    destination = tmp_path / "runtime.bin"
    filename = "specify-runtime-windows-amd64.exe"
    github_cli = r"C:\tools\gh.exe"
    commands: list[list[str]] = []

    monkeypatch.setattr(
        runtime.shutil,
        "which",
        lambda command: github_cli if command == "gh" else None,
    )
    monkeypatch.setattr(runtime, "binary_filename", lambda: filename)

    def fake_run(command: list[str], **kwargs: object) -> SimpleNamespace:
        commands.append(command)
        assert kwargs["capture_output"] is True
        assert kwargs["text"] is True
        destination.write_bytes(b"x" * 2048)
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(runtime.subprocess, "run", fake_run)

    result = runtime._download_with_github_cli(version, destination)

    assert result == destination
    assert commands == [
        [
            github_cli,
            "release",
            "download",
            *tag_args,
            "--repo",
            runtime.REPO,
            "--pattern",
            filename,
            "--output",
            str(destination),
        ]
    ]


def test_authenticated_github_cli_failure_does_not_echo_subprocess_output(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runtime = _load_runtime()
    destination = tmp_path / "runtime.bin"
    leaked_value = "credential-that-must-not-appear"

    monkeypatch.setattr(runtime.shutil, "which", lambda _command: r"C:\tools\gh.exe")
    monkeypatch.setattr(
        runtime.subprocess,
        "run",
        lambda *_args, **_kwargs: SimpleNamespace(
            returncode=1,
            stdout="",
            stderr=leaked_value,
        ),
    )

    with pytest.raises(runtime.SpecifyRuntimeError) as exc_info:
        runtime._download_with_github_cli("latest", destination)

    assert leaked_value not in str(exc_info.value)
    assert not destination.exists()


def test_ensure_binary_prefers_release_download_even_when_source_build_flagged(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """uvx --from git sets source_build_required; release download must still win."""
    runtime = _load_runtime()
    cache = tmp_path / "cache"
    cache.mkdir()
    downloaded = tmp_path / "downloaded-runtime"
    build_calls: list[str] = []
    download_calls: list[str] = []

    monkeypatch.delenv("SPECIFY_RUNTIME_BIN", raising=False)
    monkeypatch.setattr(runtime, "cache_dir", lambda: cache)
    monkeypatch.setattr(
        runtime,
        "cached_executable",
        lambda: cache / RUNTIME_BINARY_NAME,
    )
    monkeypatch.setattr(
        runtime,
        "current_runtime_binding_metadata",
        lambda: {
            "source_build_required": True,
            "specify_launcher_kind": "source_bound",
        },
    )
    monkeypatch.setattr(runtime, "_cached_binary_is_compatible", lambda *_a, **_k: False)

    def fake_download(version: str, destination: Path | None = None) -> Path:
        download_calls.append(version)
        dest = destination or downloaded
        _write_executable(Path(dest))
        return Path(dest)

    def fake_build(*_args: object, **_kwargs: object) -> Path:
        build_calls.append("built")
        raise AssertionError("source build must not run when release download succeeds")

    monkeypatch.setattr(runtime, "download", fake_download)
    monkeypatch.setattr(runtime, "_build_supported_binary_from_source", fake_build)
    monkeypatch.setattr(runtime, "_ensure_supported_binary", lambda binary, _version: binary)
    monkeypatch.setattr(runtime, "interprocess_lock", lambda _path: _NullLock())

    result = runtime.ensure_binary("v0.6.9")

    assert result == cache / RUNTIME_BINARY_NAME
    assert result.is_file()
    assert download_calls == ["v0.6.9"]
    assert build_calls == []


def test_ensure_binary_tries_latest_when_pinned_release_missing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runtime = _load_runtime()
    cache = tmp_path / "cache"
    cache.mkdir()
    download_calls: list[str] = []
    build_calls: list[str] = []

    monkeypatch.delenv("SPECIFY_RUNTIME_BIN", raising=False)
    monkeypatch.setattr(runtime, "cache_dir", lambda: cache)
    monkeypatch.setattr(
        runtime,
        "cached_executable",
        lambda: cache / RUNTIME_BINARY_NAME,
    )
    monkeypatch.setattr(runtime, "_cached_binary_is_compatible", lambda *_a, **_k: False)
    monkeypatch.setattr(runtime, "interprocess_lock", lambda _path: _NullLock())

    def fake_download(version: str, destination: Path | None = None) -> Path:
        download_calls.append(version)
        if version == "v0.6.16":
            raise runtime.SpecifyRuntimeError("HTTP 404")
        dest = Path(destination or (tmp_path / "latest-runtime"))
        _write_executable(dest)
        return dest

    def fake_build(*_args: object, **_kwargs: object) -> Path:
        build_calls.append("built")
        raise AssertionError("source build must not run when latest download succeeds")

    monkeypatch.setattr(runtime, "download", fake_download)
    monkeypatch.setattr(runtime, "_build_supported_binary_from_source", fake_build)
    monkeypatch.setattr(
        runtime,
        "_ensure_supported_binary",
        lambda binary, _version: binary,
    )

    result = runtime.ensure_binary("v0.6.16")

    assert result == cache / RUNTIME_BINARY_NAME
    assert result.is_file()
    assert download_calls == ["v0.6.16", "latest"]
    assert build_calls == []


def test_ensure_supported_binary_does_not_rebuild_source_build(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runtime = _load_runtime()
    binary = _write_executable(tmp_path / RUNTIME_BINARY_NAME)
    build_calls: list[str] = []

    monkeypatch.setattr(runtime, "_release_binary_is_compatible", lambda *_a, **_k: False)
    monkeypatch.setattr(runtime, "_source_build_marker_matches", lambda _binary: True)
    monkeypatch.setattr(
        runtime,
        "_binary_is_compatible",
        lambda _binary, allow_dirty=False: allow_dirty is True,
    )
    monkeypatch.setattr(
        runtime,
        "_clean_release_binary_meets_contract",
        lambda _binary: False,
    )

    def fake_build(*_args: object, **_kwargs: object) -> Path:
        build_calls.append("built")
        raise AssertionError("already-built source binary must not rebuild")

    monkeypatch.setattr(runtime, "_build_supported_binary_from_source", fake_build)

    result = runtime._ensure_supported_binary(binary, "v0.6.16")

    assert result == binary
    assert build_calls == []


def test_ensure_supported_binary_accepts_clean_release_fallback(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runtime = _load_runtime()
    binary = _write_executable(tmp_path / RUNTIME_BINARY_NAME)
    build_calls: list[str] = []
    marker_versions: list[str] = []

    monkeypatch.setattr(runtime, "_release_binary_is_compatible", lambda *_a, **_k: False)
    monkeypatch.setattr(runtime, "_source_build_marker_matches", lambda _binary: False)
    monkeypatch.setattr(runtime, "_clean_release_binary_meets_contract", lambda _binary: True)
    monkeypatch.setattr(
        runtime,
        "_write_fallback_release_marker",
        lambda _binary, requested: marker_versions.append(requested),
    )

    def fake_build(*_args: object, **_kwargs: object) -> Path:
        build_calls.append("built")
        raise AssertionError("clean release fallback must not force source build")

    monkeypatch.setattr(runtime, "_build_supported_binary_from_source", fake_build)

    result = runtime._ensure_supported_binary(binary, "v0.6.16")

    assert result == binary
    assert marker_versions == ["v0.6.16"]
    assert build_calls == []


def test_cached_binary_accepts_fallback_release_marker(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runtime = _load_runtime()
    binary = _write_executable(tmp_path / RUNTIME_BINARY_NAME)

    monkeypatch.setattr(runtime, "_source_build_marker_matches", lambda _binary: False)
    monkeypatch.setattr(runtime, "_release_binary_is_compatible", lambda *_a, **_k: False)
    monkeypatch.setattr(
        runtime,
        "_fallback_release_marker_matches",
        lambda _binary, requested: requested == "v0.6.16",
    )
    monkeypatch.setattr(runtime, "_clean_release_binary_meets_contract", lambda _binary: True)

    assert runtime._cached_binary_is_compatible(binary, "v0.6.16") is True
    assert runtime._cached_binary_is_compatible(binary, "v0.6.17") is False


def test_fallback_release_marker_round_trip(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runtime = _load_runtime()
    binary = _write_executable(tmp_path / RUNTIME_BINARY_NAME)
    monkeypatch.setattr(runtime, "_runtime_contract_fingerprint", lambda: "contract-fp")

    runtime._write_fallback_release_marker(binary, "v0.6.16")

    assert runtime._fallback_release_marker_matches(binary, "v0.6.16") is True
    assert runtime._fallback_release_marker_matches(binary, "v0.6.15") is False
    assert not runtime._source_build_marker(binary).is_file()


class _NullLock:
    def __enter__(self) -> "_NullLock":
        return self

    def __exit__(self, *_exc: object) -> None:
        return None


def test_default_runtime_version_pins_stable_packages_and_tracks_dev_latest(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = _load_runtime()

    monkeypatch.setattr(runtime.importlib.metadata, "version", lambda _name: "1.2.3")
    assert runtime.default_runtime_version() == "v1.2.3"

    monkeypatch.setattr(
        runtime.importlib.metadata,
        "version",
        lambda _name: "1.2.4.dev0",
    )
    assert runtime.default_runtime_version() == "latest"


@pytest.mark.parametrize(
    ("info", "expected_version", "accepted"),
    [
        (
            {
                "cli_version": "v0.6.6",
                "source_revision": "a" * 40,
                "dirty": False,
            },
            "v0.6.6",
            True,
        ),
        (
            {
                "cli_version": "v0.6.6",
                "source_revision": "a" * 40,
                "dirty": False,
            },
            "latest",
            True,
        ),
        (
            {"cli_version": "dev", "source_revision": "a" * 40, "dirty": False},
            "latest",
            False,
        ),
        (
            {
                "cli_version": "v0.6.5",
                "source_revision": "a" * 40,
                "dirty": False,
            },
            "v0.6.6",
            False,
        ),
        (
            {
                "cli_version": "v0.6.6",
                "source_revision": "unknown",
                "dirty": False,
            },
            "v0.6.6",
            False,
        ),
        (
            {
                "cli_version": "v0.6.6",
                "source_revision": "a" * 40,
                "dirty": True,
            },
            "v0.6.6",
            False,
        ),
    ],
)
def test_release_identity_requires_exact_clean_provenance(
    info: dict[str, object], expected_version: str, accepted: bool
) -> None:
    runtime = _load_runtime()

    assert (
        runtime._release_identity_is_compatible(
            info,
            expected_version=expected_version,
        )
        is accepted
    )


def test_runtime_identity_rejects_missing_dirty_provenance() -> None:
    runtime = _load_runtime()

    assert runtime._runtime_identity_is_compatible({}, allow_dirty=True) is False
    assert (
        runtime._runtime_identity_is_compatible(
            {"dirty": True}, allow_dirty=False
        )
        is False
    )
    assert (
        runtime._runtime_identity_is_compatible({"dirty": True}, allow_dirty=True)
        is True
    )


def test_python_runtime_surface_removes_legacy_installers_and_launchers() -> None:
    legacy_modules = [
        PACKAGE_ROOT / "project_cognition_runtime.py",
        PACKAGE_ROOT / "project_cognition_tool.py",
        PACKAGE_ROOT / "lint.py",
    ]
    assert [path.name for path in legacy_modules if path.exists()] == []

    forbidden_tokens = (
        "project_cognition_launcher",
        "PROJECT_COGNITION_BIN",
        "project_cognition_runtime",
        "project_cognition_tool",
        "from specify_cli.lint import",
    )
    offenders: dict[str, list[str]] = {}
    for path in PACKAGE_ROOT.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        hits = [token for token in forbidden_tokens if token in text]
        if hits:
            offenders[path.relative_to(PROJECT_ROOT).as_posix()] = hits

    assert offenders == {}


def test_python_callers_use_only_unified_runtime_namespaces() -> None:
    prefixes: list[tuple[str, ...]] = []
    unresolved: list[str] = []

    for path in PACKAGE_ROOT.rglob("*.py"):
        if path.name == "specify_runtime.py":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            name = (
                node.func.id
                if isinstance(node.func, ast.Name)
                else node.func.attr
                if isinstance(node.func, ast.Attribute)
                else ""
            )
            if name != "run_specify_runtime":
                continue
            relative = path.relative_to(PROJECT_ROOT).as_posix()
            if not node.args or not isinstance(node.args[0], (ast.List, ast.Tuple)):
                unresolved.append(f"{relative}:{node.lineno}")
                continue
            prefix: list[str] = []
            for element in node.args[0].elts:
                if isinstance(element, ast.Constant) and isinstance(element.value, str):
                    prefix.append(element.value)
                else:
                    break
            if not prefix:
                unresolved.append(f"{relative}:{node.lineno}")
                continue
            prefixes.append(tuple(prefix))

    assert unresolved == []
    assert any(prefix[0] == "cognition" for prefix in prefixes)
    assert any(prefix[0] == "deep-research" for prefix in prefixes)
    assert any(prefix[0] == "prd-build" for prefix in prefixes)
    assert any(prefix[0] == "prd-scan" for prefix in prefixes)
    assert any(prefix[:2] == ("validate", "spec") for prefix in prefixes)
    assert any(prefix[0] == "workflow" for prefix in prefixes)
    assert all(
        prefix[0] in {"cognition", "deep-research", "prd-build", "prd-scan", "workflow"}
        or prefix[:2] == ("validate", "spec")
        for prefix in prefixes
    )
