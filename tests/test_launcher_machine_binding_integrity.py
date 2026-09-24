"""Exercise generated machine bindings with real children, not full CLI acceptance.

The child package has the production launcher/IO owners and a deliberately tiny
CLI that records execution. Its identity is supplied through the existing package
identity helper; no probe/subprocess result or generated script is stubbed.
"""
from __future__ import annotations

import hashlib
import importlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import venv

import pytest


@pytest.fixture
def binding_environment(tmp_path, monkeypatch):
    launcher = importlib.import_module("specify_cli.launcher")
    root = tmp_path.resolve()
    package = root / "source package 中文" / "specify_cli"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text('''import json, os, pathlib, sys

def main():
    marker = os.environ.get("SPECIFY_TEST_BINDING_EXECUTION")
    if marker:
        with pathlib.Path(marker).open("a", encoding="utf-8") as stream:
            stream.write(json.dumps({"argv": sys.argv[1:], "cwd": os.getcwd()}) + "\\n")
    mode = os.environ.get("SPECIFY_TEST_BINDING_RESPONSE", "normal")
    if mode == "invalid-utf8":
        os.write(1, b"\\xff")
    elif mode == "wrong-identity":
        print("not-the-bound-runtime")
    elif mode == "failure":
        print("chenziyang110/spec-kit-plus")
        raise SystemExit(7)
    elif sys.argv[1:] == ["--runtime-id"]:
        print("chenziyang110/spec-kit-plus")
    else:
        print(json.dumps({"argv": sys.argv[1:], "cwd": os.getcwd()}, ensure_ascii=False))
''', encoding="utf-8")
    for name in ("launcher.py", "atomic_io.py", "hook_artifacts.py"):
        shutil.copyfile(Path(launcher.__file__).parent / name, package / name)
    identity = (
        package.parent,
        hashlib.sha256((package / "__init__.py").read_bytes()).hexdigest(),
        hashlib.sha256((package / "launcher.py").read_bytes()).hexdigest(),
    )
    monkeypatch.setattr(launcher, "_binding_package_identity", lambda: identity)
    monkeypatch.setenv(launcher.SPECIFY_LOCAL_BINDING_ENV, str(root / "state 中文"))
    monkeypatch.setenv("PYTHONDONTWRITEBYTECODE", "1")
    trace = root / "executions.jsonl"
    monkeypatch.setenv("SPECIFY_TEST_BINDING_EXECUTION", str(trace))
    monkeypatch.delenv("SPECIFY_TEST_BINDING_RESPONSE", raising=False)
    return launcher, package, trace


def write_binding(launcher, binding_id="a" * 32, interpreter=None):
    interpreter = str(interpreter or sys.executable)
    argv = (interpreter, "-m", "specify_cli")
    spec = launcher.SpecifyLauncherSpec(
        command=launcher.render_command(argv), argv=argv,
        source="local_environment", kind="local_environment",
        runtime_id=launcher.SPECIFY_RUNTIME_ID,
    )
    launcher._write_project_launcher_binding(binding_id, spec)
    return binding_id


def state_snapshot(launcher):
    root = launcher._project_launcher_state_root()
    return {p.relative_to(root).as_posix(): (p.read_bytes(), p.stat().st_mtime_ns)
            for p in root.rglob("*") if p.is_file()}


def test_other_environment_removal_does_not_disable_healthy_binding(binding_environment, tmp_path):
    launcher, _, trace = binding_environment
    interpreters = []
    for name in ("environment-a", "environment-b"):
        root = tmp_path / name
        venv.EnvBuilder(with_pip=False, symlinks=os.name != "nt").create(root)
        interpreters.append(root / ("Scripts/python.exe" if os.name == "nt" else "bin/python"))
    a = write_binding(launcher, "a" * 32, interpreters[0])
    b = write_binding(launcher, "b" * 32, interpreters[1])
    assert launcher._machine_binding_probe(a)
    assert launcher._machine_binding_probe(b)
    shutil.rmtree(tmp_path / "environment-b")
    before = state_snapshot(launcher)
    trace.unlink()
    assert launcher._machine_binding_probe(a), "B's stale repair hint cannot invalidate A's live interpreter"
    assert not launcher._machine_binding_probe(b), "the selected binding still needs its own interpreter"
    assert len(trace.read_text().splitlines()) == 1
    assert state_snapshot(launcher) == before


@pytest.mark.parametrize("target", ["entry", "invoke", "dispatch"])
def test_invalid_utf8_script_is_unavailable_without_execution(binding_environment, target):
    launcher, _, trace = binding_environment
    binding_id = write_binding(launcher)
    paths = {
        "entry": launcher._project_launcher_binding_dir(binding_id) / launcher.SPECIFY_BINDING_ENTRY,
        "invoke": launcher._project_launcher_native_binding_path(binding_id),
        "dispatch": launcher._project_launcher_dispatch_path(),
    }
    paths[target].write_bytes(b"\xff\xfeinvalid-script")
    before = state_snapshot(launcher)
    assert launcher._machine_binding_probe(binding_id) is False
    assert not trace.exists()
    assert state_snapshot(launcher) == before


def test_rehashed_replacement_invoke_cannot_impersonate_verified_entry(binding_environment):
    launcher, _, trace = binding_environment
    binding_id = write_binding(launcher)
    invoke = launcher._project_launcher_native_binding_path(binding_id)
    replacement = (
        "Write-Output 'chenziyang110/spec-kit-plus'\r\nexit 0\r\n"
        if os.name == "nt" else "#!/bin/sh\nprintf 'chenziyang110/spec-kit-plus\\n'\n"
    )
    invoke.write_bytes(replacement.encode("utf-8-sig" if os.name == "nt" else "utf-8"))
    metadata_path = launcher._project_launcher_binding_path(binding_id)
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["invoke_sha256"] = hashlib.sha256(invoke.read_bytes()).hexdigest()
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
    before = state_snapshot(launcher)
    assert launcher._machine_binding_probe(binding_id) is False
    assert not trace.exists()
    assert state_snapshot(launcher) == before


@pytest.mark.parametrize("target", ["entry", "invoke", "dispatch"])
def test_matching_file_through_symlink_is_not_a_valid_owned_script(binding_environment, tmp_path, target):
    launcher, _, trace = binding_environment
    binding_id = write_binding(launcher)
    path = {
        "entry": launcher._project_launcher_binding_dir(binding_id) / launcher.SPECIFY_BINDING_ENTRY,
        "invoke": launcher._project_launcher_native_binding_path(binding_id),
        "dispatch": launcher._project_launcher_dispatch_path(),
    }[target]
    original = path.read_bytes()
    outside = tmp_path / "outside-script"
    shutil.copy2(path, outside)
    path.unlink()
    try:
        path.symlink_to(outside)
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"symlinks unavailable: {exc}")
    assert launcher._machine_binding_probe(binding_id) is False
    assert not trace.exists()
    assert outside.read_bytes() == original


def test_valid_generated_binding_is_probed_once_without_rewriting_state(binding_environment, tmp_path):
    launcher, _, trace = binding_environment
    binding_id = write_binding(launcher)
    before = state_snapshot(launcher)
    assert launcher._machine_binding_probe(binding_id)
    assert [json.loads(row)["argv"] for row in trace.read_text().splitlines()] == [["--runtime-id"]]
    assert state_snapshot(launcher) == before
    # Exercise the generated executable chain beyond the identity-only probe.
    args = ["fixture-command", "中文 with spaces", "literal;$()"]
    result = subprocess.run([*launcher.project_local_specify_launcher_spec(binding_id).argv, *args],
                            cwd=tmp_path, capture_output=True, text=True, encoding="utf-8", timeout=20)
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["argv"] == args
    assert Path(payload["cwd"]).resolve() == tmp_path.resolve()


@pytest.mark.parametrize("mode", ["wrong-identity", "failure", "invalid-utf8"])
def test_probe_rejects_bad_child_response(binding_environment, monkeypatch, mode):
    launcher, _, trace = binding_environment
    binding_id = write_binding(launcher)
    monkeypatch.setenv("SPECIFY_TEST_BINDING_RESPONSE", mode)
    assert launcher._machine_binding_probe(binding_id) is False
    assert len(trace.read_text().splitlines()) == 1


@pytest.mark.parametrize("target", ["init", "launcher"])
def test_changed_pinned_package_is_rejected_before_child_start(binding_environment, target):
    launcher, package, trace = binding_environment
    binding_id = write_binding(launcher)
    path = package / ("__init__.py" if target == "init" else "launcher.py")
    with path.open("ab") as stream:
        stream.write(b"\n# changed source\n")
    assert launcher._machine_binding_probe(binding_id) is False
    assert not trace.exists()


@pytest.mark.parametrize("target", ["binding", "dispatch"])
def test_missing_metadata_never_executes_a_probe(binding_environment, target):
    launcher, _, trace = binding_environment
    binding_id = write_binding(launcher)
    path = (launcher._project_launcher_binding_path(binding_id) if target == "binding"
            else launcher._project_launcher_dispatch_metadata_path())
    path.unlink()
    assert launcher._machine_binding_probe(binding_id) is False
    assert not trace.exists()


def test_dispatch_with_rehashed_modified_source_is_still_rejected(binding_environment):
    launcher, _, trace = binding_environment
    binding_id = write_binding(launcher)
    path = launcher._project_launcher_dispatch_path()
    with path.open("ab") as stream:
        stream.write(b"\n# modified dispatcher\n")
    metadata_path = launcher._project_launcher_dispatch_metadata_path()
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["dispatch_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
    assert launcher._machine_binding_probe(binding_id) is False
    assert not trace.exists()


@pytest.mark.parametrize("target", ["entry", "invoke", "dispatch"])
def test_invalid_recorded_path_is_unavailable_not_a_traceback(binding_environment, target):
    launcher, _, trace = binding_environment
    binding_id = write_binding(launcher)
    path = (launcher._project_launcher_dispatch_metadata_path() if target == "dispatch"
            else launcher._project_launcher_binding_path(binding_id))
    metadata = json.loads(path.read_text(encoding="utf-8"))
    invalid = str(path.parent / "invalid\x00path")
    if target == "entry":
        metadata["entry_argv"][1] = invalid
    else:
        metadata[target + "_path"] = invalid
    path.write_text(json.dumps(metadata), encoding="utf-8")
    assert launcher._machine_binding_probe(binding_id) is False
    assert not trace.exists()


def install_bound_project(binding_environment, tmp_path):
    """Use the real public writer, canonical template, probe and config loader."""
    launcher, _, _ = binding_environment
    project = tmp_path / "project 中文"
    current = launcher.current_environment_specify_launcher_spec()
    config = launcher.write_project_specify_launcher_config(project, current)
    assert config == project / launcher.SPECIFY_CONFIG_FILE
    loaded = launcher.load_project_specify_launcher(project)
    assert loaded is not None and loaded.kind == "machine_binding"
    return project, config, launcher._project_launcher_destination(project), loaded


def test_public_writer_installs_executable_project_wrapper(binding_environment, tmp_path):
    launcher, _, trace = binding_environment
    project, config, wrapper, loaded = install_bound_project(binding_environment, tmp_path)
    assert launcher.project_specify_launcher_is_available(project, loaded)
    nested = project / "nested directory"
    nested.mkdir()
    argv = ([launcher._windows_powershell_executable(), "-NoProfile", "-File", str(wrapper)]
            if os.name == "nt" else [str(wrapper)])
    args = ["fixture-command", "中文 with spaces", "literal;$()"]
    trace.unlink()
    result = subprocess.run([*argv, *args], cwd=nested, capture_output=True, text=True,
                            encoding="utf-8", check=False, timeout=20)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {"argv": args, "cwd": str(nested)}
    assert len(trace.read_text().splitlines()) == 1
    before = config.read_bytes(), config.stat().st_mtime_ns, wrapper.read_bytes(), wrapper.stat().st_mtime_ns
    launcher.write_project_specify_launcher_config(project, launcher.current_environment_specify_launcher_spec())
    assert (config.read_bytes(), config.stat().st_mtime_ns,
            wrapper.read_bytes(), wrapper.stat().st_mtime_ns) == before


@pytest.mark.skipif(os.name == "nt", reason="POSIX executable permission semantics")
def test_project_wrapper_permission_loss_is_unavailable_before_probe(binding_environment, tmp_path):
    launcher, _, trace = binding_environment
    project, _, wrapper, loaded = install_bound_project(binding_environment, tmp_path)
    wrapper.chmod(0o600)
    with pytest.raises(PermissionError):
        subprocess.run([str(wrapper), "--runtime-id"], check=False, timeout=10)
    trace.unlink()
    assert not launcher.project_specify_launcher_is_available(project, loaded)
    assert not trace.exists(), "an unusable project wrapper must not trigger a misleading probe"
    assert wrapper.stat().st_mode & 0o777 == 0o600


@pytest.mark.skipif(os.name == "nt", reason="POSIX executable permission semantics")
def test_normal_repair_restores_only_identical_wrapper_permissions(binding_environment, tmp_path):
    launcher, _, _ = binding_environment
    project, config, wrapper, loaded = install_bound_project(binding_environment, tmp_path)
    before = wrapper.read_bytes(), config.read_bytes()
    wrapper.chmod(0o600)
    launcher.write_project_specify_launcher_config(project, launcher.current_environment_specify_launcher_spec())
    assert os.access(wrapper, os.X_OK), "normal repair must not skip an identical but unlaunchable wrapper"
    assert (wrapper.read_bytes(), config.read_bytes()) == before
    assert launcher.project_specify_launcher_is_available(project, loaded)
    result = subprocess.run([str(wrapper), "--runtime-id"], capture_output=True, text=True,
                            encoding="utf-8", check=False, timeout=10)
    assert result.returncode == 0 and result.stdout.strip() == launcher.SPECIFY_RUNTIME_ID


@pytest.mark.skipif(os.name == "nt", reason="POSIX executable permission semantics")
def test_permission_repair_does_not_chmod_a_hardlinked_external_file(binding_environment, tmp_path):
    launcher, _, _ = binding_environment
    project, _, wrapper, _ = install_bound_project(binding_environment, tmp_path)
    wrapper.chmod(0o600)
    external = tmp_path / "retained-backup"
    try:
        os.link(wrapper, external)
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"hardlinks unavailable: {exc}")
    before = external.read_bytes(), external.stat().st_mode, external.stat().st_mtime_ns
    launcher.write_project_specify_launcher_config(project, launcher.current_environment_specify_launcher_spec())
    assert os.access(wrapper, os.X_OK)
    assert not os.path.samefile(wrapper, external)
    assert (external.read_bytes(), external.stat().st_mode, external.stat().st_mtime_ns) == before


@pytest.mark.parametrize("preserve", [False, True])
def test_permission_repair_never_replaces_user_modified_wrapper(binding_environment, tmp_path, preserve):
    launcher, _, _ = binding_environment
    project, config, wrapper, _ = install_bound_project(binding_environment, tmp_path)
    with wrapper.open("ab") as stream:
        stream.write(b"\n# user modification\n")
    if os.name != "nt":
        wrapper.chmod(0o600)
    before = wrapper.read_bytes(), wrapper.stat().st_mode, config.read_bytes()
    current = launcher.current_environment_specify_launcher_spec()
    if preserve:
        assert launcher.write_project_specify_launcher_config(
            project, current, preserve_conflicting_wrapper=True) == config
    else:
        with pytest.raises(RuntimeError, match="conflict"):
            launcher.write_project_specify_launcher_config(project, current)
    assert (wrapper.read_bytes(), wrapper.stat().st_mode, config.read_bytes()) == before


@pytest.mark.skipif(os.name == "nt", reason="POSIX executable permission semantics")
def test_permission_repair_write_failure_is_not_reported_as_success(binding_environment, tmp_path, monkeypatch):
    launcher, _, _ = binding_environment
    project, config, wrapper, loaded = install_bound_project(binding_environment, tmp_path)
    wrapper.chmod(0o600)
    before = wrapper.read_bytes(), config.read_bytes()
    original = launcher.atomic_write_text
    def fail_wrapper(path, text, **kwargs):
        if Path(path) == wrapper:
            raise OSError("controlled wrapper repair failure")
        return original(path, text, **kwargs)
    monkeypatch.setattr(launcher, "atomic_write_text", fail_wrapper)
    with pytest.raises(OSError, match="wrapper repair failure"):
        launcher.write_project_specify_launcher_config(project, launcher.current_environment_specify_launcher_spec())
    assert (wrapper.read_bytes(), config.read_bytes()) == before
    assert not launcher.project_specify_launcher_is_available(project, loaded)
