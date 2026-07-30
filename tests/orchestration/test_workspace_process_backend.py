"""Tests for run-bound process launch inside an authoritative Git workspace."""

from __future__ import annotations

import subprocess
import sqlite3
import time
from contextlib import closing
from dataclasses import replace
from pathlib import Path

import pytest

from specify_cli.orchestration.backends.workspace_process_backend import (
    WorkspaceBindingError,
    WorkspaceLaunchBinding,
    WorkspaceProcessBackend,
)


def _git(cwd: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        check=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return completed.stdout.strip()


def _workspace_binding(tmp_path: Path) -> WorkspaceLaunchBinding:
    root = tmp_path / "workspace"
    root.mkdir()
    _git(root, "init", "-q")
    _git(root, "config", "user.name", "Workspace Launcher Test")
    _git(root, "config", "user.email", "workspace-launcher@example.invalid")
    _git(root, "config", "commit.gpgsign", "false")
    _git(root, "commit", "--allow-empty", "-q", "-m", "initial")
    _git(root, "checkout", "-q", "-b", "specify/runs/test/g1")
    common_dir = Path(_git(root, "rev-parse", "--git-common-dir"))
    if not common_dir.is_absolute():
        common_dir = root / common_dir
    binding = WorkspaceLaunchBinding(
        run_id="run_test",
        activity_id="activity_test",
        attempt_id="attempt_test",
        workspace_id="workspace_test",
        workspace_generation=1,
        fence=7,
        workspace_root=root.resolve(),
        repo_common_dir=common_dir.resolve(),
        private_ref="refs/heads/specify/runs/test/g1",
    )
    _write_run_control_binding(binding)
    return binding


def _write_run_control_binding(binding: WorkspaceLaunchBinding) -> Path:
    database_path = binding.repo_common_dir / "specify-runtime" / "run-control.sqlite"
    database_path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(database_path)) as database:
        database.executescript(
            """
            CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE runs (
                run_id TEXT PRIMARY KEY, status TEXT NOT NULL, current_fence INTEGER NOT NULL,
                owner_epoch TEXT NOT NULL
            );
            CREATE TABLE activities (
                activity_id TEXT PRIMARY KEY, run_id TEXT NOT NULL, status TEXT NOT NULL
            );
            CREATE TABLE workspaces (
                workspace_id TEXT PRIMARY KEY, run_id TEXT NOT NULL, generation INTEGER NOT NULL,
                root_path TEXT NOT NULL, repo_common_dir TEXT NOT NULL, private_ref TEXT NOT NULL,
                status TEXT NOT NULL
            );
            CREATE TABLE attempts (
                attempt_id TEXT PRIMARY KEY, run_id TEXT NOT NULL, activity_id TEXT NOT NULL,
                workspace_id TEXT NOT NULL, workspace_generation INTEGER NOT NULL,
                status TEXT NOT NULL, owner_epoch TEXT NOT NULL, fence INTEGER NOT NULL,
                lease_until_ms INTEGER NOT NULL
            );
            """
        )
        database.execute("INSERT INTO metadata VALUES ('schema_version', '4')")
        database.execute(
            "INSERT INTO runs VALUES (?, 'ready', ?, 'owner-test')",
            (binding.run_id, binding.fence),
        )
        database.execute(
            "INSERT INTO activities VALUES (?, ?, 'ready')",
            (binding.activity_id, binding.run_id),
        )
        database.execute(
            "INSERT INTO workspaces VALUES (?, ?, ?, ?, ?, ?, 'ready')",
            (
                binding.workspace_id,
                binding.run_id,
                binding.workspace_generation,
                str(binding.workspace_root),
                str(binding.repo_common_dir),
                binding.private_ref,
            ),
        )
        database.execute(
            "INSERT INTO attempts VALUES (?, ?, ?, ?, ?, 'issued', 'owner-test', ?, ?)",
            (
                binding.attempt_id,
                binding.run_id,
                binding.activity_id,
                binding.workspace_id,
                binding.workspace_generation,
                binding.fence,
                int(time.time() * 1000) + 60_000,
            ),
        )
        database.commit()
    return database_path


def test_workspace_process_backend_forces_cwd_and_authority_environment(monkeypatch, tmp_path: Path):
    binding = _workspace_binding(tmp_path)
    captured: dict[str, object] = {}

    class _FakePopen:
        pid = 23456

    def _fake_popen(command, *, cwd, env, shell):
        captured.update(command=command, cwd=cwd, env=env, shell=shell)
        return _FakePopen()

    monkeypatch.setattr(
        "specify_cli.orchestration.backends.workspace_process_backend.subprocess.Popen",
        _fake_popen,
    )
    monkeypatch.setenv("PATH", "SYSTEM_PATH")

    handle = WorkspaceProcessBackend().launch(
        ["agent-cli", "run", "task"],
        binding=binding,
        env={"CALLER_VALUE": "preserved"},
    )

    assert handle.pid == 23456
    assert handle.cwd == binding.workspace_root
    assert captured["command"] == ["agent-cli", "run", "task"]
    assert captured["cwd"] == binding.workspace_root
    assert captured["shell"] is False
    merged_env = captured["env"]
    assert isinstance(merged_env, dict)
    assert merged_env["PATH"] == "SYSTEM_PATH"
    assert merged_env["CALLER_VALUE"] == "preserved"
    assert merged_env["SPECIFY_RUN_ID"] == binding.run_id
    assert merged_env["SPECIFY_ACTIVITY_ID"] == binding.activity_id
    assert merged_env["SPECIFY_ATTEMPT_ID"] == binding.attempt_id
    assert merged_env["SPECIFY_ATTEMPT_FENCE"] == str(binding.fence)
    assert merged_env["SPECIFY_WORKSPACE_ID"] == binding.workspace_id
    assert merged_env["SPECIFY_WORKSPACE_GENERATION"] == str(binding.workspace_generation)
    assert merged_env["SPECIFY_WORKSPACE_ROOT"] == str(binding.workspace_root)
    assert merged_env["SPECIFY_REPO_COMMON_DIR"] == str(binding.repo_common_dir)
    assert merged_env["SPECIFY_PRIVATE_REF"] == binding.private_ref


def test_workspace_process_backend_rejects_shell_text_and_reserved_env(tmp_path: Path):
    binding = _workspace_binding(tmp_path)
    backend = WorkspaceProcessBackend()

    with pytest.raises(TypeError, match="tokenized argv"):
        backend.launch("agent-cli run task", binding=binding)

    with pytest.raises(WorkspaceBindingError, match="reserved"):
        backend.launch(
            ["agent-cli", "run", "task"],
            binding=binding,
            env={"SPECIFY_WORKSPACE_ROOT": str(tmp_path / "other")},
        )

    with pytest.raises(WorkspaceBindingError, match="private ref"):
        backend.launch(
            ["agent-cli"],
            binding=replace(binding, private_ref="refs/heads/specify/runs/../../outside/g1"),
        )


def test_workspace_process_backend_rejects_wrong_root_or_private_ref(monkeypatch, tmp_path: Path):
    binding = _workspace_binding(tmp_path)
    backend = WorkspaceProcessBackend()
    monkeypatch.setattr(
        "specify_cli.orchestration.backends.workspace_process_backend.subprocess.Popen",
        lambda *args, **kwargs: pytest.fail("invalid binding must not start a process"),
    )

    other = tmp_path / "other"
    other.mkdir()
    with pytest.raises(WorkspaceBindingError, match="Git worktree"):
        backend.launch(["agent-cli"], binding=replace(binding, workspace_root=other.resolve()))

    with pytest.raises(WorkspaceBindingError, match="private ref"):
        backend.launch(
            ["agent-cli"],
            binding=replace(binding, private_ref="refs/heads/specify/runs/other/g1"),
        )


def test_workspace_process_backend_rejects_stale_database_authority(monkeypatch, tmp_path: Path):
    binding = _workspace_binding(tmp_path)
    database_path = binding.repo_common_dir / "specify-runtime" / "run-control.sqlite"
    monkeypatch.setattr(
        "specify_cli.orchestration.backends.workspace_process_backend.subprocess.Popen",
        lambda *args, **kwargs: pytest.fail("stale authority must not start a process"),
    )

    with closing(sqlite3.connect(database_path)) as database:
        database.execute("UPDATE runs SET current_fence = current_fence + 1")
        database.commit()
    with pytest.raises(WorkspaceBindingError, match="authority"):
        WorkspaceProcessBackend().launch(["agent-cli"], binding=binding)

    with closing(sqlite3.connect(database_path)) as database:
        database.execute("UPDATE runs SET current_fence = ?", (binding.fence,))
        database.execute("UPDATE workspaces SET status = 'quarantined'")
        database.commit()
    with pytest.raises(WorkspaceBindingError, match="authority"):
        WorkspaceProcessBackend().launch(["agent-cli"], binding=binding)


def test_workspace_process_backend_requires_read_only_run_control_database(monkeypatch, tmp_path: Path):
    binding = _workspace_binding(tmp_path)
    database_path = binding.repo_common_dir / "specify-runtime" / "run-control.sqlite"
    database_path.unlink()
    monkeypatch.setattr(
        "specify_cli.orchestration.backends.workspace_process_backend.subprocess.Popen",
        lambda *args, **kwargs: pytest.fail("missing authority database must not start a process"),
    )

    with pytest.raises(WorkspaceBindingError, match="run-control database"):
        WorkspaceProcessBackend().launch(["agent-cli"], binding=binding)
    assert not database_path.exists()
