import ast
import importlib
import json
import os
from pathlib import Path
import stat
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
        "workflow.enter",
        "workflow.next",
        "workflow.complete-stage",
        "workflow.transition",
        "workflow.reopen",
        "workflow.block",
        "workflow.resolve",
        "workflow.closeout",
    }
    assert "workflow.start" not in runtime.REQUIRED_CAPABILITIES
    assert "workflow.status" not in runtime.REQUIRED_CAPABILITIES


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
    _write_config(
        tmp_path,
        {
            "runtime_launcher": {
                "command": "pwsh -Command SHOULD_NOT_BE_TRUSTED",
                "argv": [project_binary.relative_to(tmp_path).as_posix()],
            },
            "project_cognition_launcher": {
                "command": str(legacy_binary),
                "argv": [str(legacy_binary)],
            },
        },
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
        ["validate", "spec", "--dir", ".", "--format", "json"],
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
        ["validate", "spec", "--dir", "."],
        cwd=tmp_path,
        install_if_missing=True,
    )

    assert payload == {"status": "ok"}
    assert calls == [[str(binary), "validate", "spec", "--dir", "."]]


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
    assert any(prefix[:2] == ("validate", "spec") for prefix in prefixes)
    assert any(prefix[0] == "workflow" for prefix in prefixes)
    assert all(
        prefix[0] in {"cognition", "workflow"}
        or prefix[:2] == ("validate", "spec")
        for prefix in prefixes
    )
