"""Real child-process checks of Python runtime consumption; not release evidence."""
from __future__ import annotations

import base64
import importlib
import json
import os
import sys

import pytest


@pytest.fixture
def runtime(monkeypatch):
    module = importlib.import_module("specify_cli.specify_runtime")
    monkeypatch.delenv(module.RUNTIME_TIMEOUT_ENV, raising=False)
    def no_install(*args, **kwargs):
        raise AssertionError("response validation must not install or retry a runtime")
    monkeypatch.setattr(module, "ensure_binary", no_install)
    return module


def envelope(status="blocked"):
    return {
        "status": status, "summary": "controlled runtime response",
        "data": {"status": status, "error_code": "fixture", "exact_integer": 9007199254740993},
        "items": [], "blockers": ["original blocker"],
        "show_argv": [], "next_argv": [],
    }


def handshake(runtime, **changes):
    data = {
        "protocol_version": runtime.EXPECTED_RUNTIME_PROTOCOL,
        "capability_ids": list(runtime.REQUIRED_CAPABILITIES),
        "dirty": False, "cli_version": "v1.2.3", "source_revision": "a" * 40,
    }
    data.update(changes)
    return {"status": "ok", "data": data}


def child(tmp_path, responses):
    """Use the installed Python as a portable real child, with durable call counts."""
    script = tmp_path / "runtime_fixture.py"
    script.write_text(
        "import base64,json,os,pathlib,signal,sys\n"
        "root=pathlib.Path(sys.argv[1])\n"
        "counter=root/'calls.txt'\n"
        "n=int(counter.read_text()) if counter.exists() else 0\n"
        "rows=json.loads((root/'responses.json').read_text())\n"
        "row=rows[min(n,len(rows)-1)]\n"
        "counter.write_text(str(n+1))\n"
        "os.write(1,base64.b64decode(row['stdout']))\n"
        "os.write(2,base64.b64decode(row.get('stderr','')))\n"
        "if row.get('signal'): os.kill(os.getpid(),signal.SIGTERM)\n"
        "sys.exit(row['code'])\n",
        encoding="utf-8",
    )
    rows = []
    for payload, code, *options in responses:
        raw = payload if isinstance(payload, bytes) else json.dumps(payload).encode("utf-8")
        row = {"stdout": base64.b64encode(raw).decode("ascii"), "code": code}
        if options:
            row.update(options[0])
        rows.append(row)
    (tmp_path / "responses.json").write_text(json.dumps(rows), encoding="utf-8")
    return [sys.executable, "-I", "-S", str(script), str(tmp_path)], tmp_path / "calls.txt"


@pytest.mark.parametrize("status", ["blocked", "repairable-block"])
@pytest.mark.parametrize("code", [0, 1, 2, 17])
def test_blocking_envelope_requires_the_blocked_exit_code(runtime, monkeypatch, tmp_path, status, code):
    argv, count = child(tmp_path, [(envelope(status), code)])
    monkeypatch.setattr(runtime, "resolve_specify_runtime_binary", lambda root: argv)
    with pytest.raises(runtime.SpecifyRuntimeError):
        runtime.run_specify_runtime(["quick", "status"], cwd=tmp_path)
    assert count.read_text() == "1"


@pytest.mark.parametrize("status", ["blocked", "repairable-block"])
@pytest.mark.parametrize("command", ["quick", "cognition"])
def test_valid_blockers_keep_legacy_consumer_shape(runtime, monkeypatch, tmp_path, status, command):
    payload = envelope(status)
    argv, count = child(tmp_path, [(payload, 10)])
    monkeypatch.setattr(runtime, "resolve_specify_runtime_binary", lambda root: argv)
    result = runtime.run_specify_runtime([command, "status"], cwd=tmp_path)
    assert result == (payload["data"] if command == "cognition" else payload)
    assert count.read_text() == "1"


def test_cognition_cannot_unwrap_a_delivery_failure(runtime, monkeypatch, tmp_path):
    argv, count = child(tmp_path, [(envelope(), 1)])
    monkeypatch.setattr(runtime, "resolve_specify_runtime_binary", lambda root: argv)
    with pytest.raises(runtime.SpecifyRuntimeError):
        runtime.run_specify_runtime(["cognition", "status"], cwd=tmp_path)
    assert count.read_text() == "1"


@pytest.mark.skipif(os.name == "nt", reason="POSIX signal exit semantics")
def test_signal_termination_is_not_a_structured_block(runtime, monkeypatch, tmp_path):
    argv, count = child(tmp_path, [(envelope(), 0, {"signal": True})])
    monkeypatch.setattr(runtime, "resolve_specify_runtime_binary", lambda root: argv)
    with pytest.raises(runtime.SpecifyRuntimeError):
        runtime.run_specify_runtime(["quick", "status"], cwd=tmp_path)
    assert count.read_text() == "1"


def test_check_false_remains_an_explicit_diagnostic_opt_out(runtime, monkeypatch, tmp_path):
    payload = envelope()
    argv, _ = child(tmp_path, [(payload, 1)])
    monkeypatch.setattr(runtime, "resolve_specify_runtime_binary", lambda root: argv)
    assert runtime.run_specify_runtime(["quick", "status"], cwd=tmp_path, check=False) == payload


@pytest.mark.parametrize("command", ["quick", "cognition"])
def test_successful_response_retains_exact_integer_and_shape(runtime, monkeypatch, tmp_path, command):
    payload = envelope("ok")
    argv, _ = child(tmp_path, [(payload, 0)])
    monkeypatch.setattr(runtime, "resolve_specify_runtime_binary", lambda root: argv)
    assert runtime.run_specify_runtime([command, "status"], cwd=tmp_path) == (
        payload["data"] if command == "cognition" else payload
    )


@pytest.mark.parametrize("payload", [{"legacy": True}, {"status": "ok"}, {}])
def test_plain_legacy_objects_still_return(runtime, monkeypatch, tmp_path, payload):
    argv, _ = child(tmp_path, [(payload, 0)])
    monkeypatch.setattr(runtime, "resolve_specify_runtime_binary", lambda root: argv)
    assert runtime.run_specify_runtime(["validate", "spec"], cwd=tmp_path) == payload


@pytest.mark.parametrize("raw", [
    b'{"status":"error","status":"ok"}',
    b'{"status":"error","statu\\u0073":"ok"}',
    b'{"data":{"ready":false,"ready":true}}',
    b'{"value":NaN}', b'{"value":Infinity}', b'{"value":1e999}',
    b'{"value":"\xff"}', b'{"ok":true} {}', b'[]',
])
def test_malformed_or_ambiguous_output_is_never_interpreted(runtime, monkeypatch, tmp_path, raw):
    argv, count = child(tmp_path, [(raw, 0)])
    monkeypatch.setattr(runtime, "resolve_specify_runtime_binary", lambda root: argv)
    # check=False waives command status checks, not JSON integrity.
    for check in (True, False):
        with pytest.raises(runtime.SpecifyRuntimeError):
            runtime.run_specify_runtime(["quick", "status"], cwd=tmp_path, check=check)
    assert count.read_text() == "2"
    assert runtime._runtime_handshake(argv, cwd=tmp_path) is None
    assert count.read_text() == "3"


@pytest.mark.parametrize("kind", ["binary", "release", "latest-clean"])
def test_compatibility_does_not_combine_incompatible_snapshots(runtime, monkeypatch, tmp_path, kind):
    first = handshake(runtime, dirty=True)
    second = handshake(runtime, capability_ids=[])
    argv, count = child(tmp_path, [(first, 0), (second, 0)])
    original = runtime._runtime_handshake
    monkeypatch.setattr(runtime, "_runtime_handshake", lambda *a, **kw: original(argv, cwd=tmp_path))
    binary = tmp_path / "runtime_fixture.py"
    if kind == "binary":
        accepted = runtime._binary_is_compatible(binary)
    elif kind == "release":
        accepted = runtime._release_binary_is_compatible(binary, "v1.2.3")
    else:
        accepted = runtime._clean_release_binary_meets_contract(binary)
    assert accepted is False
    assert count.read_text() == "1"


@pytest.mark.parametrize("kind", ["binary", "release", "latest-clean"])
def test_compatible_snapshot_is_probed_once(runtime, monkeypatch, tmp_path, kind):
    argv, count = child(tmp_path, [(handshake(runtime), 0)])
    original = runtime._runtime_handshake
    monkeypatch.setattr(runtime, "_runtime_handshake", lambda *a, **kw: original(argv, cwd=tmp_path))
    binary = tmp_path / "runtime_fixture.py"
    if kind == "binary":
        assert runtime._binary_is_compatible(binary)
    elif kind == "release":
        assert runtime._release_binary_is_compatible(binary, "v1.2.3")
    else:
        assert runtime._clean_release_binary_meets_contract(binary)
    assert count.read_text() == "1"


@pytest.mark.parametrize("status", ["blocked", "repairable-block", "error", "usage-error", None, True])
def test_failed_handshake_status_cannot_advertise_compatibility(runtime, tmp_path, status):
    payload = handshake(runtime)
    payload["status"] = status
    argv, count = child(tmp_path, [(payload, 0)])
    assert runtime._runtime_handshake(argv, cwd=tmp_path) is None
    assert count.read_text() == "1"


@pytest.mark.parametrize("shape", ["flat", "wrapped", "aliases"])
def test_handshake_legacy_shapes_remain_supported(runtime, tmp_path, shape):
    payload = handshake(runtime)
    if shape == "flat":
        payload = payload["data"]
    elif shape == "aliases":
        data = payload["data"]
        data["runtime_protocol"] = data.pop("protocol_version")
        data["capabilities"] = data.pop("capability_ids")
    argv, count = child(tmp_path, [(payload, 0)])
    assert runtime.launcher_supports_required_commands(argv, cwd=tmp_path)
    assert count.read_text() == "1"


@pytest.mark.parametrize("value", [None, [], "invalid"])
def test_handshake_invalid_data_does_not_fall_back_to_top_level(runtime, tmp_path, value):
    payload = handshake(runtime)["data"]
    payload["data"] = value
    argv, _ = child(tmp_path, [(payload, 0)])
    assert runtime._runtime_handshake(argv, cwd=tmp_path) is None


@pytest.mark.parametrize("extra", [None, 7, {}, "", " api.show"])
def test_noncanonical_capability_members_are_rejected(runtime, tmp_path, extra):
    payload = handshake(runtime)
    payload["data"]["capability_ids"].append(extra)
    argv, _ = child(tmp_path, [(payload, 0)])
    assert runtime.launcher_supports_required_commands(argv, cwd=tmp_path) is False


def test_optional_shadow_stays_optional_and_retired_commands_stay_rejected(runtime, tmp_path):
    assert "quick.context-shadow" not in runtime.REQUIRED_CAPABILITIES
    first = handshake(runtime)
    second = handshake(runtime)
    second["data"]["capability_ids"].append("quick.context-shadow")
    third = handshake(runtime)
    third["data"]["capability_ids"].append("run.begin")
    argv, count = child(tmp_path, [(first, 0), (second, 0), (third, 0)])
    assert runtime.launcher_supports_required_commands(argv, cwd=tmp_path)
    assert runtime.launcher_supports_required_commands(argv, cwd=tmp_path)
    assert runtime.launcher_supports_required_commands(argv, cwd=tmp_path) is False
    assert count.read_text() == "3"


def test_explicit_dirty_override_and_release_pin_are_not_weakened(runtime, monkeypatch, tmp_path):
    argv, _ = child(tmp_path, [(handshake(runtime, dirty=True), 0)])
    original = runtime._runtime_handshake
    monkeypatch.setattr(runtime, "_runtime_handshake", lambda *a, **kw: original(argv, cwd=tmp_path))
    binary = tmp_path / "runtime_fixture.py"
    assert runtime._binary_is_compatible(binary, allow_dirty=True)
    assert not runtime._release_binary_is_compatible(binary, "v1.2.3")
    assert not runtime._clean_release_binary_meets_contract(binary)
    (tmp_path / "responses.json").write_text(json.dumps([
        {"stdout": base64.b64encode(json.dumps(handshake(runtime)).encode()).decode(), "code": 0}
    ]))
    assert not runtime._release_binary_is_compatible(binary, "v9.9.9")
    assert runtime._release_binary_is_compatible(binary, "latest")
