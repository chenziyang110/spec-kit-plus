"""Direct project-scoped launches preserve caller-owned execution contracts."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from specify_cli.orchestration.backends.workspace_process_backend import (
    WorkspaceBindingError,
    WorkspaceProcessBackend,
)


def test_launch_uses_explicit_project_without_discovering_parent_git_root(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    project = tmp_path / "parent-repository" / "nested-project"
    project.mkdir(parents=True)
    (project / ".specify").mkdir()
    legacy_files = {
        project.parent / ".git" / "HEAD": b"ref: refs/heads/main\n",
        project.parent / ".git" / "specify-runtime" / "run-control.sqlite": b"existing storage",
        project.parent / ".worktrees" / "legacy-run" / "owned.txt": b"existing worktree",
    }
    for path, content in legacy_files.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    captured: dict[str, object] = {}

    def fake_popen(command, **kwargs):
        captured.update(command=command, **kwargs)
        return SimpleNamespace(pid=23456)

    monkeypatch.setattr(subprocess, "Popen", fake_popen)
    monkeypatch.setattr(
        subprocess, "run", lambda *_a, **_k: pytest.fail("launch must not discover or mutate Git state")
    )
    handle = WorkspaceProcessBackend().launch(
        ["agent-cli", "exec", "--task", "a; $(must-stay-an-argument)"],
        project_root=project,
    )

    assert handle.pid == 23456
    assert handle.cwd == project.resolve()
    assert tuple(captured["command"]) == handle.command
    assert captured["cwd"] == project.resolve()
    assert captured["shell"] is False
    assert not (project / ".git").exists()
    assert not (project / ".specify" / "runs").exists()
    for path, content in legacy_files.items():
        assert path.read_bytes() == content


def test_launch_drops_retired_environment_but_preserves_board_fences_and_packet(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    captured: dict[str, object] = {}
    monkeypatch.setenv("SPECIFY_RUN_ID", "old-run")
    monkeypatch.setenv("SPECIFY_RUN_MANAGED", "1")
    monkeypatch.setenv("SPECIFY_RUN_WORKSPACE", str(tmp_path.parent))
    monkeypatch.setenv("SPECIFY_ATTEMPT_FENCE", "999")
    monkeypatch.setenv("SPECIFY_PRIVATE_REF", "refs/heads/specify/runs/old/g1")
    monkeypatch.setenv("PATH", "SYSTEM_PATH")
    monkeypatch.setenv(
        "WSLENV",
        "SPECIFY_RUN_WORKSPACE/p:SPECIFY_RUN_ID:SPECIFY_PRIVATE_REF:"
        "SPECIFY_WORK_ID:SPECIFY_WORK_FENCE:SPECIFY_FEATURE_BRANCH_POLICY:CALLER_PATH/p",
    )
    board_env = {
        "SPECIFY_WORK_ID": "work-1",
        "SPECIFY_WORK_FENCE": "7",
        "SPECIFY_WORK_REVISION": "3",
        "SPECIFY_WORK_PACKET_FILE": str(tmp_path / "worker-packet.json"),
        "SPECIFY_WORK_PACKET_SHA256": "a" * 64,
        "SPECIFY_EXECUTION_ACTIVITY_ID": "activity-1",
        "SPECIFY_FEATURE_BRANCH_POLICY": "keep-current",
        "CALLER_VALUE": "preserved",
    }

    def fake_popen(command, **kwargs):
        captured.update(command=command, **kwargs)
        return SimpleNamespace(pid=23456)

    monkeypatch.setattr(subprocess, "Popen", fake_popen)
    WorkspaceProcessBackend().launch(
        ["agent-cli"],
        project_root=tmp_path,
        env={
            **board_env,
            "SPECIFY_RUN_WORKSPACE": "ignored",
            "specify_run_attempt_id": "ignored",
            "SPECIFY_WORKSPACE_ROOT": "ignored",
        },
    )

    child_env = captured["env"]
    assert isinstance(child_env, dict)
    assert child_env["PATH"] == "SYSTEM_PATH"
    for key, value in board_env.items():
        assert child_env[key] == value
    assert not any(key.upper().startswith("SPECIFY_RUN_") for key in child_env)
    assert "SPECIFY_ATTEMPT_FENCE" not in child_env
    assert "SPECIFY_PRIVATE_REF" not in child_env
    assert "SPECIFY_WORKSPACE_ROOT" not in child_env
    assert child_env["WSLENV"] == (
        "SPECIFY_WORK_ID:SPECIFY_WORK_FENCE:SPECIFY_FEATURE_BRANCH_POLICY:CALLER_PATH/p"
    )
    # Filtering a child environment must not mutate the caller's active context.
    assert os.environ["SPECIFY_RUN_ID"] == "old-run"


@pytest.mark.parametrize("command", ["agent-cli exec", b"agent-cli", [], [""], [1], ["bad\x00arg"]])
def test_launch_rejects_non_tokenized_commands(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, command
) -> None:
    monkeypatch.setattr(
        subprocess, "Popen", lambda *_a, **_k: pytest.fail("invalid argv must not spawn")
    )
    with pytest.raises(TypeError, match="tokenized argv"):
        WorkspaceProcessBackend().launch(command, project_root=tmp_path)


def test_launch_requires_an_explicit_existing_absolute_directory(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        subprocess, "Popen", lambda *_a, **_k: pytest.fail("invalid root must not spawn")
    )
    backend = WorkspaceProcessBackend()
    with pytest.raises(TypeError, match="project_root"):
        backend.launch(["agent-cli"])
    with pytest.raises(WorkspaceBindingError, match="absolute"):
        backend.launch(["agent-cli"], project_root=Path("."))
    with pytest.raises(WorkspaceBindingError, match="directory"):
        backend.launch(["agent-cli"], project_root=tmp_path / "missing")
    file_path = tmp_path / "file"
    file_path.write_text("not a directory", encoding="utf-8")
    with pytest.raises(WorkspaceBindingError, match="directory"):
        backend.launch(["agent-cli"], project_root=file_path)


def test_spawn_failure_is_reported_without_claiming_or_rewriting_work(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    attempts = 0

    def fake_popen(*_args, **_kwargs):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise OSError("spawn failed")
        return SimpleNamespace(pid=45678)

    monkeypatch.setattr(subprocess, "Popen", fake_popen)
    backend = WorkspaceProcessBackend()
    with pytest.raises(OSError, match="spawn failed"):
        backend.launch(["agent-cli"], project_root=tmp_path)
    assert backend.launch(["agent-cli"], project_root=tmp_path).pid == 45678
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("returncode", [0, 23])
def test_direct_child_runs_in_project_and_reports_exit_without_workflow_acceptance(
    tmp_path: Path, returncode: int
) -> None:
    project = tmp_path / "nested project"
    project.mkdir()
    handle = WorkspaceProcessBackend().launch(
        [
            sys.executable, "-c",
            "import os, sys; from pathlib import Path; "
            "assert Path.cwd() == Path(sys.argv[1]); "
            "assert os.environ['SPECIFY_WORK_FENCE'] == '7'; "
            "sys.exit(int(sys.argv[2]))",
            str(project.resolve()), str(returncode),
        ],
        project_root=project,
        env={"SPECIFY_WORK_FENCE": "7"},
    )
    assert handle.wait(timeout=15) == returncode
    assert handle.poll() == returncode
    assert list(project.iterdir()) == []


def test_cancel_reaps_the_direct_child(tmp_path: Path) -> None:
    handle = WorkspaceProcessBackend().launch(
        [sys.executable, "-c", "import time; time.sleep(30)"],
        project_root=tmp_path,
    )
    try:
        assert handle.poll() is None
        assert handle.cancel() != 0
        assert handle.poll() is not None
    finally:
        if handle.poll() is None:
            handle.cancel()


def test_cancel_escalates_a_child_that_does_not_exit(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    calls = []

    class FakeProcess:
        pid = 56789

        def poll(self):
            return None

        def terminate(self):
            calls.append("terminate")

        def kill(self):
            calls.append("kill")

        def wait(self, *, timeout):
            calls.append(("wait", timeout))
            if "kill" not in calls:
                raise subprocess.TimeoutExpired("agent-cli", timeout)
            return -9

    monkeypatch.setattr(subprocess, "Popen", lambda *_a, **_k: FakeProcess())
    handle = WorkspaceProcessBackend().launch(["agent-cli"], project_root=tmp_path)
    assert handle.cancel() == -9
    assert calls == ["terminate", ("wait", 5), "kill", ("wait", 5)]
