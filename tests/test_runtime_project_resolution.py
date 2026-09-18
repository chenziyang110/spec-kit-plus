"""Project-pinned resolution and explicit bootstrap boundaries, using real files."""
from __future__ import annotations

import importlib
import json
import os
from pathlib import Path
import shutil
import subprocess

import pytest


@pytest.fixture
def owners(tmp_path, monkeypatch):
    launcher = importlib.import_module("specify_cli.launcher")
    runtime = importlib.import_module("specify_cli.specify_runtime")
    monkeypatch.setenv(runtime.RUNTIME_CACHE_ENV, str(tmp_path / "cache"))
    monkeypatch.delenv(runtime.RUNTIME_ENV, raising=False)
    monkeypatch.delenv(runtime.RUNTIME_TIMEOUT_ENV, raising=False)
    return launcher, runtime


def pin(owners, root, source=None):
    launcher, runtime = owners
    if source is None:
        source = root.parent / (root.name + "-source")
        source.write_bytes(b"nonexecuted-runtime-fixture")
    config = launcher.write_runtime_launcher_config(root, source)
    assert config is not None
    return config, runtime.project_runtime_entrypoint_path(root)


def snapshot(root):
    return {p.relative_to(root).as_posix(): p.read_bytes()
            for p in root.rglob("*") if p.is_file() and not p.is_symlink()}


@pytest.mark.parametrize("damage", [
    "changed-binary", "missing-binary", "bad-digest", "malformed-json",
    "duplicate-key", "missing-config", "launcher-only", "binding-only",
    "null-launcher", "wrong-entrypoint",
])
def test_broken_pin_never_resolves_environment_or_path(owners, tmp_path, monkeypatch, damage):
    launcher, runtime = owners
    root = tmp_path / "project"
    config, binary = pin(owners, root)
    payload = json.loads(config.read_text())
    if damage == "changed-binary":
        binary.write_bytes(b"changed-after-binding")
    elif damage == "missing-binary":
        binary.unlink()
    elif damage == "malformed-json":
        config.write_text("{")
    elif damage == "duplicate-key":
        config.write_text('{"runtime_launcher":null,"runtime_launcher":{}}')
    elif damage == "missing-config":
        config.unlink()
    else:
        if damage == "bad-digest":
            payload["runtime_launcher_binding"]["runtime_binary_sha256"] = "0" * 64
        elif damage == "launcher-only":
            del payload["runtime_launcher_binding"]
        elif damage == "binding-only":
            del payload["runtime_launcher"]
        elif damage == "null-launcher":
            payload["runtime_launcher"] = None
        else:
            payload["runtime_launcher"]["argv"] = [str(tmp_path / "foreign-runtime")]
        config.write_text(json.dumps(payload))
    monkeypatch.setenv(runtime.RUNTIME_ENV, str(tmp_path / "foreign-runtime"))
    monkeypatch.setattr(runtime.shutil, "which", lambda name: str(tmp_path / "path-runtime"))
    before = snapshot(root)
    with pytest.raises(runtime.SpecifyRuntimeError, match="binding|pinned"):
        runtime.resolve_specify_runtime_binary(root)
    assert snapshot(root) == before
    assert launcher.load_runtime_launcher(root) is None


@pytest.mark.parametrize("check", [True, False])
def test_install_if_missing_cannot_repair_or_bypass_broken_pin(owners, tmp_path, monkeypatch, check):
    _, runtime = owners
    root = tmp_path / "project"
    _, binary = pin(owners, root)
    binary.unlink()
    calls = []
    monkeypatch.setattr(runtime.shutil, "which", lambda name: None)
    def install():
        calls.append("install")
        raise AssertionError("a broken binding is not a missing bootstrap runtime")
    monkeypatch.setattr(runtime, "ensure_binary", install)
    with pytest.raises(runtime.SpecifyRuntimeError, match="binding|pinned"):
        runtime.run_specify_runtime(["quick", "status"], cwd=root,
                                    install_if_missing=True, check=check)
    assert calls == []


def test_subdirectory_uses_ancestor_pin_not_environment(owners, tmp_path, monkeypatch):
    _, runtime = owners
    root = tmp_path / "project with spaces 中文"
    _, binary = pin(owners, root)
    child = root / "src" / "nested"
    child.mkdir(parents=True)
    monkeypatch.setenv(runtime.RUNTIME_ENV, str(tmp_path / "foreign-runtime"))
    before = snapshot(root)
    assert runtime.resolve_specify_runtime_binary(child) == [str(binary)]
    assert snapshot(root) == before


def test_nearest_project_owns_resolution(owners, tmp_path, monkeypatch):
    _, runtime = owners
    parent = tmp_path / "parent"
    pin(owners, parent)
    nested = parent / "nested"
    _, binary = pin(owners, nested)
    child = nested / "src"
    child.mkdir()
    monkeypatch.setenv(runtime.RUNTIME_ENV, str(tmp_path / "foreign"))
    assert runtime.resolve_specify_runtime_binary(child) == [str(binary)]
    binary.unlink()
    with pytest.raises(runtime.SpecifyRuntimeError):
        runtime.resolve_specify_runtime_binary(child)


@pytest.mark.parametrize("config", [None, {}, {"user": "unbound project"}])
def test_unbound_nested_project_does_not_inherit_parent_pin(owners, tmp_path, monkeypatch, config):
    _, runtime = owners
    parent = tmp_path / "parent"
    pin(owners, parent)
    nested = parent / "nested"
    state = nested / ".specify"
    state.mkdir(parents=True)
    if config is not None:
        (state / "config.json").write_text(json.dumps(config))
    child = nested / "src"
    child.mkdir()
    bootstrap = str(tmp_path / "bootstrap")
    monkeypatch.setenv(runtime.RUNTIME_ENV, bootstrap)
    assert runtime.resolve_specify_runtime_binary(child) == [bootstrap]


@pytest.mark.parametrize("kind", ["config", "project-marker", "dangling-config"])
def test_unsafe_project_state_cannot_trigger_fallback(owners, tmp_path, monkeypatch, kind):
    _, runtime = owners
    root = tmp_path / "project"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    target = outside / "config.json"
    target.write_text("{}")
    if kind == "project-marker":
        alias, destination = root / ".specify", outside
    else:
        (root / ".specify").mkdir()
        alias = root / ".specify/config.json"
        destination = target if kind == "config" else outside / "missing"
    try:
        alias.symlink_to(destination, target_is_directory=kind == "project-marker")
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"symlinks unavailable: {exc}")
    monkeypatch.setenv(runtime.RUNTIME_ENV, str(tmp_path / "foreign"))
    before = snapshot(outside)
    with pytest.raises(runtime.SpecifyRuntimeError):
        runtime.resolve_specify_runtime_binary(root)
    assert snapshot(outside) == before


def test_partial_project_marker_is_not_an_unconfigured_directory(owners, tmp_path, monkeypatch):
    _, runtime = owners
    root = tmp_path / "project"
    root.mkdir()
    (root / ".specify").write_text("unexpected-file")
    monkeypatch.setenv(runtime.RUNTIME_ENV, str(tmp_path / "foreign"))
    with pytest.raises(runtime.SpecifyRuntimeError):
        runtime.resolve_specify_runtime_binary(root)


@pytest.mark.skipif(os.name == "nt", reason="POSIX executable permission bits")
def test_nonexecutable_pin_does_not_fall_back(owners, tmp_path, monkeypatch):
    _, runtime = owners
    root = tmp_path / "project"
    _, binary = pin(owners, root)
    binary.chmod(0o600)
    monkeypatch.setenv(runtime.RUNTIME_ENV, str(tmp_path / "foreign"))
    with pytest.raises(runtime.SpecifyRuntimeError):
        runtime.resolve_specify_runtime_binary(root)


def test_explicit_unscoped_resolution_keeps_environment_precedence(owners, tmp_path, monkeypatch):
    _, runtime = owners
    monkeypatch.setenv(runtime.RUNTIME_ENV, str(tmp_path / "bootstrap"))
    assert runtime.resolve_specify_runtime_binary() == [str(tmp_path / "bootstrap")]


def test_plain_unconfigured_directory_keeps_path_bootstrap(owners, tmp_path, monkeypatch):
    _, runtime = owners
    root = tmp_path / "unconfigured"
    root.mkdir()
    monkeypatch.setattr(runtime.shutil, "which", lambda name: str(tmp_path / "bootstrap"))
    assert runtime.resolve_specify_runtime_binary(root) == [str(tmp_path / "bootstrap")]
    assert list(root.iterdir()) == []


@pytest.fixture(scope="module")
def native_probe(tmp_path_factory):
    # Build a stdlib-only executable fixture, not a Specify runtime release.
    if not shutil.which("go"):
        pytest.skip("local Go toolchain required for the process-resolution fixture")
    root = tmp_path_factory.mktemp("resolution-native")
    program = root / "main.go"
    program.write_text('''package main
import("encoding/json";"os")
func main(){
 if p:=os.Getenv("SPECIFY_TEST_EXEC_LOG"); p!="" {
  f,e:=os.OpenFile(p,os.O_CREATE|os.O_WRONLY|os.O_APPEND,0600);if e!=nil{os.Exit(1)}
  _,e=f.WriteString(os.Args[0]+"\\n");f.Close();if e!=nil{os.Exit(1)}
 }
 cwd,e:=os.Getwd();if e!=nil{os.Exit(1)}
 if json.NewEncoder(os.Stdout).Encode(map[string]any{"executable":os.Args[0],"cwd":cwd,"args":os.Args[1:]})!=nil{os.Exit(1)}
}
''')
    binary = root / ("probe.exe" if os.name == "nt" else "probe")
    env = os.environ.copy()
    env.update(GOWORK="off", GOTOOLCHAIN="local", GOPROXY="off", GOFLAGS="")
    result = subprocess.run(["go", "build", "-o", str(binary), str(program)],
                            capture_output=True, text=True, env=env, timeout=90)
    assert result.returncode == 0, result.stderr
    return binary


def test_real_child_from_subdirectory_keeps_cwd_and_argv(owners, tmp_path, monkeypatch, native_probe):
    _, runtime = owners
    root = tmp_path / "project with spaces 中文"
    _, binary = pin(owners, root, native_probe)
    child = root / "nested"
    child.mkdir()
    call_log = tmp_path / "executed.txt"
    monkeypatch.setenv("SPECIFY_TEST_EXEC_LOG", str(call_log))
    monkeypatch.setenv(runtime.RUNTIME_ENV, str(native_probe))
    args = ["quick", "status", "--note", "含空格 value"]
    payload = runtime.run_specify_runtime(args, cwd=child)
    assert Path(payload["executable"]) == binary
    assert Path(payload["cwd"]) == child
    assert payload["args"] == args
    assert call_log.read_text().splitlines() == [str(binary)]


@pytest.mark.parametrize("fallback", ["environment", "path"])
def test_real_foreign_executable_is_never_run_for_damaged_pin(owners, tmp_path, monkeypatch, native_probe, fallback):
    _, runtime = owners
    root = tmp_path / "project"
    _, binary = pin(owners, root, native_probe)
    binary.write_bytes(b"damaged")
    call_log = tmp_path / "executed.txt"
    monkeypatch.setenv("SPECIFY_TEST_EXEC_LOG", str(call_log))
    if fallback == "environment":
        monkeypatch.setenv(runtime.RUNTIME_ENV, str(native_probe))
    else:
        monkeypatch.setattr(runtime.shutil, "which", lambda name: str(native_probe))
    with pytest.raises(runtime.SpecifyRuntimeError):
        runtime.run_specify_runtime(["quick", "status"], cwd=root, install_if_missing=True)
    assert not call_log.exists()


def test_missing_bootstrap_can_still_install_once(owners, tmp_path, monkeypatch, native_probe):
    _, runtime = owners
    root = tmp_path / "unconfigured"
    root.mkdir()
    monkeypatch.setattr(runtime.shutil, "which", lambda name: None)
    calls = []
    def install():
        calls.append("install")
        return native_probe
    monkeypatch.setattr(runtime, "ensure_binary", install)
    result = runtime.run_specify_runtime(["version"], cwd=root, install_if_missing=True)
    assert Path(result["executable"]) == native_probe
    assert calls == ["install"]


def test_explicit_repair_restores_original_project_resolution(owners, tmp_path, monkeypatch):
    launcher, runtime = owners
    root = tmp_path / "project"
    config, binary = pin(owners, root)
    original = root.parent / (root.name + "-source")
    binary.write_bytes(b"damaged")
    monkeypatch.setenv(runtime.RUNTIME_ENV, str(tmp_path / "foreign"))
    with pytest.raises(runtime.SpecifyRuntimeError):
        runtime.resolve_specify_runtime_binary(root)
    launcher.write_runtime_launcher_config(root, original)
    assert runtime.resolve_specify_runtime_binary(root) == [str(binary)]
    assert json.loads(config.read_text())["runtime_launcher_binding"]["runtime_binary_sha256"] == runtime._sha256_file(binary)


def test_relative_subdirectory_resolves_to_absolute_pin(owners, tmp_path, monkeypatch):
    _, runtime = owners
    root = tmp_path / "project"
    _, binary = pin(owners, root)
    (root / "src").mkdir()
    monkeypatch.chdir(tmp_path)
    assert runtime.resolve_specify_runtime_binary(Path("project/src")) == [str(binary)]


def test_unreadable_project_marker_does_not_count_as_missing(owners, tmp_path, monkeypatch):
    _, runtime = owners
    root = tmp_path / "project"
    pin(owners, root)
    original_lstat = Path.lstat
    def deny(path, *args, **kwargs):
        if path == root / ".specify":
            raise PermissionError("controlled access failure")
        return original_lstat(path, *args, **kwargs)
    monkeypatch.setattr(Path, "lstat", deny)
    monkeypatch.setenv(runtime.RUNTIME_ENV, str(tmp_path / "foreign"))
    with pytest.raises(runtime.SpecifyRuntimeError):
        runtime.resolve_specify_runtime_binary(root)


def test_failed_config_save_cannot_escape_to_foreign_runtime(owners, tmp_path, monkeypatch, native_probe):
    launcher, runtime = owners
    root = tmp_path / "project"
    config, binary = pin(owners, root)
    before = config.read_bytes()
    original_write = launcher.atomic_write_text
    def fail(path, content, **kwargs):
        if Path(path) == config:
            raise OSError("controlled config save failure")
        return original_write(path, content, **kwargs)
    with monkeypatch.context() as m:
        m.setattr(launcher, "atomic_write_text", fail)
        with pytest.raises(OSError, match="config save"):
            launcher.write_runtime_launcher_config(root, native_probe)
    assert config.read_bytes() == before
    assert binary.read_bytes() == native_probe.read_bytes()
    call_log = tmp_path / "executed.txt"
    monkeypatch.setenv("SPECIFY_TEST_EXEC_LOG", str(call_log))
    monkeypatch.setenv(runtime.RUNTIME_ENV, str(native_probe))
    with pytest.raises(runtime.SpecifyRuntimeError):
        runtime.run_specify_runtime(["version"], cwd=root, install_if_missing=True)
    assert not call_log.exists()
    # Explicitly rerun the normal config writer; resolution itself never repairs.
    launcher.write_runtime_launcher_config(root, native_probe)
    result = runtime.run_specify_runtime(["version"], cwd=root)
    assert Path(result["executable"]) == binary
    assert call_log.read_text().splitlines() == [str(binary)]
