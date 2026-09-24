"""Real-file/process launcher persistence regressions; not full init/release tests."""
from __future__ import annotations

import hashlib
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import pytest


@pytest.fixture
def owners(tmp_path, monkeypatch):
    launcher = importlib.import_module("specify_cli.launcher")
    runtime = importlib.import_module("specify_cli.specify_runtime")
    monkeypatch.setenv(runtime.RUNTIME_CACHE_ENV, str(tmp_path / "cache"))
    monkeypatch.setenv(launcher.SPECIFY_LOCAL_BINDING_ENV, str(tmp_path / "bindings"))
    return launcher, runtime


def source(tmp_path, name, data):
    path = tmp_path / name
    path.write_bytes(data)
    path.chmod(0o700)
    return path


def initial(owners, tmp_path):
    launcher, runtime = owners
    project = tmp_path / "project"
    old = source(tmp_path, "old-runtime", b"old-runtime-bytes")
    config = launcher.write_runtime_launcher_config(project, old)
    assert config is not None
    payload = json.loads(config.read_text())
    payload["user"] = {"note": "保留😀", "id": 9007199254740993}
    config.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return project, config, runtime.project_runtime_entrypoint_path(project)


@pytest.mark.parametrize("raw", [b"{", b"null", b"[]", b'{"user":1,"user":2}',
                                  b'{"user":NaN}', b'{"user":"\xff"}'])
def test_invalid_config_is_rejected_before_runtime_replacement(owners, tmp_path, raw):
    launcher, runtime = owners
    project, config, pinned = initial(owners, tmp_path)
    config.write_bytes(raw)
    before = pinned.read_bytes()
    new = source(tmp_path, "new-runtime", b"new-runtime-bytes")
    cached = runtime.content_addressed_runtime_path(runtime._sha256_file(new))
    assert launcher.write_runtime_launcher_config(project, new) is None
    assert pinned.read_bytes() == before
    assert config.read_bytes() == raw
    assert not cached.exists()


def test_binding_metadata_failure_precedes_binary_publication(owners, tmp_path, monkeypatch):
    launcher, runtime = owners
    project, config, pinned = initial(owners, tmp_path)
    old_config, old_binary = config.read_bytes(), pinned.read_bytes()
    new = source(tmp_path, "new-runtime", b"new-runtime-bytes")
    def fail():
        raise RuntimeError("injected metadata failure")
    monkeypatch.setattr(runtime, "current_runtime_binding_metadata", fail)
    with pytest.raises(RuntimeError, match="metadata failure"):
        launcher.write_runtime_launcher_config(project, new)
    assert pinned.read_bytes() == old_binary
    assert config.read_bytes() == old_config


def wait_for(path, process, seconds=15):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if path.exists():
            return
        if process.poll() is not None:
            raise AssertionError(f"worker exited early: {process.returncode}")
        time.sleep(0.01)
    raise AssertionError(f"worker did not reach checkpoint {path.name}")


@pytest.mark.parametrize("first_kind", ["runtime", "specify"])
def test_concurrent_launcher_writers_preserve_both_bindings(owners, tmp_path, first_kind):
    launcher, runtime = owners
    project, config, pinned = initial(owners, tmp_path)
    a = source(tmp_path, "version-a", b"runtime-A")
    b = source(tmp_path, "version-b", b"runtime-B")
    script = tmp_path / "writer.py"
    script.write_text('''import json, pathlib, sys, time
sys.path.insert(0, sys.argv[1])
from specify_cli import launcher, specify_runtime as runtime
root, control = pathlib.Path(sys.argv[2]), pathlib.Path(sys.argv[3])
role, kind, binary = sys.argv[4:7]
(control / (role + ".started")).touch()
old_write = launcher.atomic_write_text
def controlled_write(path, text, **kwargs):
    if role == "A" and pathlib.Path(path) == root / launcher.SPECIFY_CONFIG_FILE:
        (control / "A.ready").touch()
        limit = time.monotonic() + 20
        while not (control / "release").exists():
            if time.monotonic() > limit: raise RuntimeError("checkpoint timeout")
            time.sleep(0.01)
    return old_write(path, text, **kwargs)
launcher.atomic_write_text = controlled_write
old_copy = runtime.materialize_project_runtime_entrypoint
def observed_copy(*args, **kwargs):
    (control / (role + ".copy")).touch()
    return old_copy(*args, **kwargs)
runtime.materialize_project_runtime_entrypoint = observed_copy
if kind == "specify":
    argv = ("uvx", "--from", launcher.SPECIFY_SOURCE_REPOSITORY + "@" + "a" * 40, "specify")
    spec = launcher.SpecifyLauncherSpec(command=launcher.render_command(argv), argv=argv, source="git", kind="source_bound", runtime_id=launcher.SPECIFY_RUNTIME_ID)
    result = launcher.write_project_specify_launcher_config(root, spec)
else:
    result = launcher.write_runtime_launcher_config(root, binary)
if result is None: raise RuntimeError("writer did not persist configuration")
(control / (role + ".done")).touch()
''', encoding="utf-8")
    control = tmp_path / "control"
    control.mkdir()
    root = str(Path(launcher.__file__).resolve().parent.parent)
    procs, streams = [], []
    crossed = False
    try:
        for role, kind, binary in [("A", first_kind, a), ("B", "runtime", b)]:
            stream = (tmp_path / f"{role}.log").open("wb")
            streams.append(stream)
            proc = subprocess.Popen([sys.executable, str(script), root, str(project), str(control), role, kind, str(binary)],
                                    stdin=subprocess.DEVNULL, stdout=stream, stderr=stream)
            procs.append(proc)
            wait_for(control / ("A.ready" if role == "A" else "B.started"), proc)
        # B is a real launched writer. It must not enter materialization while
        # A is paused immediately before publishing its configuration.
        deadline = time.monotonic() + 1.0
        while time.monotonic() < deadline:
            if (control / "B.copy").exists():
                crossed = True
                break
            if procs[1].poll() is not None:
                raise AssertionError("second writer exited without entering materialization")
            time.sleep(0.01)
    finally:
        (control / "release").touch()
        for proc in procs:
            try:
                proc.wait(timeout=20)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=5)
        for stream in streams:
            stream.close()
    assert not crossed, "second writer changed the binary before the first writer published its binding"
    for role, proc in zip(("A", "B"), procs):
        assert proc.returncode == 0, (tmp_path / f"{role}.log").read_text()
    payload = json.loads(config.read_text())
    assert payload["runtime_launcher_binding"]["runtime_binary_sha256"] == hashlib.sha256(pinned.read_bytes()).hexdigest()
    assert pinned.read_bytes() == b"runtime-B"
    assert payload["user"] == {"note": "保留😀", "id": 9007199254740993}
    if first_kind == "specify":
        assert payload["specify_launcher"]["argv"][2].endswith("@" + "a" * 40)
    assert launcher.load_runtime_launcher(project) is not None


def trusted_source_launcher(launcher):
    argv = ("uvx", "--from", launcher.SPECIFY_SOURCE_REPOSITORY + "@" + "a" * 40, "specify")
    return launcher.SpecifyLauncherSpec(
        command=launcher.render_command(argv), argv=argv,
        source="git", kind="source_bound", runtime_id=launcher.SPECIFY_RUNTIME_ID,
    )


def test_source_and_runtime_bindings_load_and_preserve_user_configuration(owners, tmp_path):
    launcher, runtime = owners
    project, config, pinned = initial(owners, tmp_path)
    spec = trusted_source_launcher(launcher)
    launcher.write_project_specify_launcher_config(project, spec)
    assert launcher.load_project_specify_launcher(project).argv == spec.argv
    assert launcher.resolve_runtime_launcher_argv(project) == (str(pinned),)
    payload = json.loads(config.read_text())
    assert payload["user"] == {"note": "保留😀", "id": 9007199254740993}
    assert payload["runtime_launcher_binding"]["runtime_binary_sha256"] == runtime._sha256_file(pinned)
    before = config.read_bytes(), config.stat().st_mtime_ns
    assert launcher.write_project_specify_launcher_config(project, spec) == config
    assert launcher.write_runtime_launcher_config(project, pinned) == config
    assert (config.read_bytes(), config.stat().st_mtime_ns) == before
    assert (project / ".specify/runtime/launcher-config.lock").is_file()
    assert (project / ".specify/runtime/.gitignore").read_text().splitlines() == ["*", "!.gitignore"]


def test_existing_pin_still_wins_over_environment_and_path(owners, tmp_path, monkeypatch):
    launcher, runtime = owners
    project, _, pinned = initial(owners, tmp_path)
    monkeypatch.setenv(runtime.RUNTIME_ENV, str(tmp_path / "wrong-runtime"))
    def forbidden(*args, **kwargs):
        raise AssertionError("valid project binding must win before PATH lookup")
    monkeypatch.setattr(runtime.shutil, "which", forbidden)
    assert runtime.resolve_specify_runtime_binary(project) == [str(pinned)]
    assert launcher.load_runtime_launcher(project) is not None


def test_explicit_direct_noop_does_not_create_state(owners, tmp_path):
    launcher, _ = owners
    project = tmp_path / "absent"
    assert launcher.write_project_specify_launcher_config(project, launcher.default_specify_launcher_spec()) is None
    assert not project.exists()


def test_implicit_foreign_launcher_is_not_overwritten(owners, tmp_path, monkeypatch):
    launcher, _ = owners
    project = tmp_path / "project"
    config = project / launcher.SPECIFY_CONFIG_FILE
    config.parent.mkdir(parents=True)
    original = {"specify_launcher": {"argv": ["foreign"], "runtime_id": "not-ours"}, "user": True}
    config.write_text(json.dumps(original))
    before = config.read_bytes()
    monkeypatch.setattr(launcher, "resolve_specify_launcher_spec", lambda: trusted_source_launcher(launcher))
    assert launcher.write_project_specify_launcher_config(project) == config
    assert config.read_bytes() == before


@pytest.mark.parametrize("raw", [b'{"outer":{"a":1,"a":2}}', b'{"user":1,"us\\u0065r":2}',
                                  b'{"user":Infinity}', b'{"user":1e999}', b'{"user":"\\ud800"}'])
def test_source_writer_also_rejects_unrepresentable_configuration(owners, tmp_path, raw):
    launcher, _ = owners
    project = tmp_path / "project"
    config = project / launcher.SPECIFY_CONFIG_FILE
    config.parent.mkdir(parents=True)
    config.write_bytes(raw)
    assert launcher.write_project_specify_launcher_config(project, trusted_source_launcher(launcher)) is None
    assert config.read_bytes() == raw
    assert sorted(p.name for p in config.parent.iterdir()) == ["config.json"]


@pytest.mark.parametrize("invalid", [None, [], "invalid", 1, float("nan"), {"surrogate": "\ud800"}, {"unsupported": object()}])
def test_invalid_binding_metadata_does_not_replace_pin(owners, tmp_path, monkeypatch, invalid):
    launcher, runtime = owners
    project, config, pinned = initial(owners, tmp_path)
    before = pinned.read_bytes(), config.read_bytes()
    new = source(tmp_path, "new-runtime", b"new-runtime-bytes")
    monkeypatch.setattr(runtime, "current_runtime_binding_metadata", lambda: invalid)
    with pytest.raises((ValueError, TypeError)):
        launcher.write_runtime_launcher_config(project, new)
    assert (pinned.read_bytes(), config.read_bytes()) == before


@pytest.mark.parametrize("kind", ["config", "runtime-directory", "lock"])
def test_launcher_write_refuses_linked_configuration_or_lock(owners, tmp_path, kind):
    launcher, runtime = owners
    project = tmp_path / "project"
    config = project / launcher.SPECIFY_CONFIG_FILE
    config.parent.mkdir(parents=True)
    outside = tmp_path / "outside"
    outside.mkdir()
    target = outside / "state"
    target.write_text("{}")
    if kind == "config":
        alias, destination = config, target
    elif kind == "runtime-directory":
        alias, destination = project / ".specify/runtime", outside
        config.write_text("{}")
    else:
        alias, destination = project / ".specify/runtime/launcher-config.lock", target
        alias.parent.mkdir()
        config.write_text("{}")
    try:
        alias.symlink_to(destination, target_is_directory=kind == "runtime-directory")
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"symlinks unavailable: {exc}")
    new = source(tmp_path, "new-runtime", b"new-runtime-bytes")
    with pytest.raises(ValueError):
        launcher.write_runtime_launcher_config(project, new)
    assert target.read_text() == "{}"
    assert sorted(p.name for p in outside.iterdir()) == ["state"]
    assert not runtime.content_addressed_runtime_path(runtime._sha256_file(new)).exists()


def test_config_write_error_is_reported_and_lock_released(owners, tmp_path, monkeypatch):
    launcher, runtime = owners
    project, config, pinned = initial(owners, tmp_path)
    before = config.read_bytes()
    lock = project / ".specify/runtime/launcher-config.lock"
    lock_info = lock.stat()
    new = source(tmp_path, "new-runtime", b"new-runtime-bytes")
    write = launcher.atomic_write_text
    def fail_config(path, text, **kwargs):
        if Path(path) == config:
            raise OSError("injected config save failure")
        return write(path, text, **kwargs)
    with monkeypatch.context() as m:
        m.setattr(launcher, "atomic_write_text", fail_config)
        with pytest.raises(OSError, match="config save failure"):
            launcher.write_runtime_launcher_config(project, new)
    assert config.read_bytes() == before
    # A lock is NOT a multi-file rollback. Existing readers reject this mismatch.
    assert pinned.read_bytes() == b"new-runtime-bytes"
    assert launcher.load_runtime_launcher(project) is None
    assert os.path.samestat(lock_info, lock.stat())
    assert launcher.write_runtime_launcher_config(project, new) == config
    assert launcher.load_runtime_launcher(project) is not None


def lock_holder(launcher, tmp_path, project):
    script = tmp_path / "hold-lock.py"
    marker = tmp_path / "lock-held"
    script.write_text('''import pathlib,sys,time
sys.path.insert(0,sys.argv[1])
from specify_cli import launcher
with launcher._locked_project_launcher_config(pathlib.Path(sys.argv[2])):
    pathlib.Path(sys.argv[3]).touch()
    time.sleep(60)
''', encoding="utf-8")
    stream = (tmp_path / "lock-holder.log").open("wb")
    process = subprocess.Popen(
        [sys.executable, str(script), str(Path(launcher.__file__).resolve().parent.parent), str(project), str(marker)],
        stdin=subprocess.DEVNULL, stdout=stream, stderr=stream,
    )
    try:
        wait_for(marker, process)
    except BaseException:
        process.kill()
        process.wait(timeout=5)
        stream.close()
        raise
    return process, stream


def test_killed_writer_releases_os_lock_without_removing_lock_file(owners, tmp_path):
    launcher, _ = owners
    project, config, _ = initial(owners, tmp_path)
    holder, stream = lock_holder(launcher, tmp_path, project)
    lock = project / ".specify/runtime/launcher-config.lock"
    info = lock.stat()
    holder.kill()
    holder.wait(timeout=5)
    stream.close()
    assert os.path.samestat(info, lock.stat())
    assert launcher.write_project_specify_launcher_config(project, trusted_source_launcher(launcher)) == config


def test_lock_is_scoped_to_one_project(owners, tmp_path):
    launcher, _ = owners
    project, _, _ = initial(owners, tmp_path)
    holder, stream = lock_holder(launcher, tmp_path, project)
    try:
        other = tmp_path / "other-project"
        assert launcher.write_project_specify_launcher_config(other, trusted_source_launcher(launcher)) == other / launcher.SPECIFY_CONFIG_FILE
        assert holder.poll() is None
    finally:
        holder.kill()
        holder.wait(timeout=5)
        stream.close()
