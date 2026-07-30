"""Tests for run-bound process launch inside an authoritative Git workspace."""

from __future__ import annotations

import subprocess
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
    return WorkspaceLaunchBinding(
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
