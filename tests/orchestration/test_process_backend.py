"""Tests for the portable process backend."""

from specify_cli.orchestration.backends.process_backend import ProcessBackend


def test_process_backend_describe():
    descriptor = ProcessBackend().describe()

    assert descriptor.name == "process"
    assert descriptor.available is True


def test_process_backend_launch_returns_metadata(monkeypatch, tmp_path):
    captured: dict[str, object] = {}

    class _FakePopen:
        def __init__(self):
            self.pid = 12345

    def _fake_popen(command, *, cwd=None, env=None):
        captured["command"] = command
        captured["cwd"] = cwd
        captured["env"] = env
        return _FakePopen()

    monkeypatch.setattr("specify_cli.orchestration.backends.process_backend.subprocess.Popen", _fake_popen)
    monkeypatch.setenv("PATH", "SYSTEM_PATH")
    monkeypatch.setenv("EXISTING_ENV", "existing")

    backend = ProcessBackend()
    handle = backend.launch(
        command=["python", "-V"],
        cwd=tmp_path,
        env={"TEAM_SESSION": "abc123", "EXISTING_ENV": "override"},
    )

    assert handle.pid == 12345
    assert handle.command == ["python", "-V"]
    assert captured["command"] == ["python", "-V"]
    assert captured["cwd"] == tmp_path
    merged_env = captured["env"]
    assert isinstance(merged_env, dict)
    assert merged_env["PATH"] == "SYSTEM_PATH"
    assert merged_env["TEAM_SESSION"] == "abc123"
    assert merged_env["EXISTING_ENV"] == "override"
