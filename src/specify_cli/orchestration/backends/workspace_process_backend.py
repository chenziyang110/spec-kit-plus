"""Workspace-bound subprocess backend for run-authoritative launches."""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

from .base import BackendDescriptor
from .workspace_authority import (
    RunControlAuthorityError,
    valid_private_ref,
    validate_run_control_authority,
)


class WorkspaceBindingError(ValueError):
    """Raised when a workspace launch binding is invalid or unsafe."""


@dataclass(slots=True, frozen=True)
class WorkspaceLaunchBinding:
    """Authoritative workspace metadata required for a run-bound launch."""

    run_id: str
    activity_id: str
    attempt_id: str
    workspace_id: str
    workspace_generation: int
    fence: int
    workspace_root: Path
    repo_common_dir: Path
    private_ref: str


@dataclass(slots=True, frozen=True)
class WorkspaceProcessHandle:
    """Launch metadata returned by :class:`WorkspaceProcessBackend`."""

    pid: int
    command: Sequence[str]
    cwd: Path
    binding: WorkspaceLaunchBinding


_RESERVED_ENV_KEYS = frozenset(
    {
        "SPECIFY_RUN_ID",
        "SPECIFY_ACTIVITY_ID",
        "SPECIFY_ATTEMPT_ID",
        "SPECIFY_ATTEMPT_FENCE",
        "SPECIFY_WORKSPACE_ID",
        "SPECIFY_WORKSPACE_GENERATION",
        "SPECIFY_WORKSPACE_ROOT",
        "SPECIFY_REPO_COMMON_DIR",
        "SPECIFY_PRIVATE_REF",
    }
)


class WorkspaceProcessBackend:
    """Launch local processes constrained to an authoritative Git workspace."""

    def describe(self) -> BackendDescriptor:
        return BackendDescriptor(
            name="workspace-process",
            available=True,
            interactive=False,
            binary=None,
            reason="workspace-bound subprocess backend",
        )

    def launch(
        self,
        command: Sequence[str],
        *,
        binding: WorkspaceLaunchBinding,
        env: Mapping[str, str] | None = None,
    ) -> WorkspaceProcessHandle:
        argv = _validate_argv(command)
        validated_binding = _validate_binding(binding)
        try:
            validate_run_control_authority(validated_binding)
        except RunControlAuthorityError as exc:
            raise WorkspaceBindingError(str(exc)) from exc
        merged_env = _workspace_environment(validated_binding, env)

        process = subprocess.Popen(
            argv,
            cwd=validated_binding.workspace_root,
            env=merged_env,
            shell=False,
        )
        return WorkspaceProcessHandle(
            pid=process.pid,
            command=argv,
            cwd=validated_binding.workspace_root,
            binding=validated_binding,
        )


def _validate_argv(command: Sequence[str]) -> list[str]:
    if isinstance(command, (str, bytes)):
        raise TypeError("workspace process launch requires tokenized argv")
    argv = list(command)
    if not argv:
        raise TypeError("workspace process launch requires nonempty tokenized argv")
    if any(not isinstance(token, str) or token == "" or "\x00" in token for token in argv):
        raise TypeError("workspace process launch requires tokenized argv strings")
    return argv


def _validate_binding(binding: WorkspaceLaunchBinding) -> WorkspaceLaunchBinding:
    _require_nonempty("run_id", binding.run_id)
    _require_nonempty("activity_id", binding.activity_id)
    _require_nonempty("attempt_id", binding.attempt_id)
    _require_nonempty("workspace_id", binding.workspace_id)
    _require_positive("workspace_generation", binding.workspace_generation)
    _require_positive("fence", binding.fence)
    _require_nonempty("private_ref", binding.private_ref)

    workspace_root = _require_absolute_existing_dir("Git worktree root", binding.workspace_root)
    repo_common_dir = _require_absolute_existing_dir("Git common dir", binding.repo_common_dir)

    git_dir = _resolve_git_dir(workspace_root)
    actual_common_dir = _resolve_common_dir(git_dir)
    if actual_common_dir != repo_common_dir:
        raise WorkspaceBindingError(
            f"Git common dir mismatch: expected {repo_common_dir}, metadata reported {actual_common_dir}"
        )

    if not valid_private_ref(binding.private_ref):
        raise WorkspaceBindingError("private ref must be a specify run branch ref")

    head_ref = _read_head_ref(git_dir)
    if head_ref != binding.private_ref:
        raise WorkspaceBindingError(
            f"private ref mismatch: expected {binding.private_ref}, HEAD is {head_ref or 'detached'}"
        )
    if not _ref_exists(repo_common_dir, binding.private_ref):
        raise WorkspaceBindingError(f"private ref does not exist: {binding.private_ref}")

    return WorkspaceLaunchBinding(
        run_id=binding.run_id,
        activity_id=binding.activity_id,
        attempt_id=binding.attempt_id,
        workspace_id=binding.workspace_id,
        workspace_generation=binding.workspace_generation,
        fence=binding.fence,
        workspace_root=workspace_root,
        repo_common_dir=repo_common_dir,
        private_ref=binding.private_ref,
    )


def _workspace_environment(
    binding: WorkspaceLaunchBinding,
    env: Mapping[str, str] | None,
) -> dict[str, str]:
    if env:
        reserved = sorted(key for key in env if key in _RESERVED_ENV_KEYS)
        if reserved:
            raise WorkspaceBindingError(
                "caller environment cannot override reserved workspace authority variables: "
                + ", ".join(reserved)
            )

    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    merged_env.update(
        {
            "SPECIFY_RUN_ID": binding.run_id,
            "SPECIFY_ACTIVITY_ID": binding.activity_id,
            "SPECIFY_ATTEMPT_ID": binding.attempt_id,
            "SPECIFY_ATTEMPT_FENCE": str(binding.fence),
            "SPECIFY_WORKSPACE_ID": binding.workspace_id,
            "SPECIFY_WORKSPACE_GENERATION": str(binding.workspace_generation),
            "SPECIFY_WORKSPACE_ROOT": str(binding.workspace_root),
            "SPECIFY_REPO_COMMON_DIR": str(binding.repo_common_dir),
            "SPECIFY_PRIVATE_REF": binding.private_ref,
        }
    )
    return merged_env


def _require_nonempty(name: str, value: str) -> None:
    if not isinstance(value, str) or not value:
        raise WorkspaceBindingError(f"{name} must be a nonempty string")


def _require_positive(name: str, value: int) -> None:
    if not isinstance(value, int) or value <= 0:
        raise WorkspaceBindingError(f"{name} must be a positive integer")


def _require_absolute_existing_dir(label: str, value: Path) -> Path:
    path = Path(value)
    if not path.is_absolute():
        raise WorkspaceBindingError(f"{label} must be absolute: {path}")
    if not path.is_dir():
        raise WorkspaceBindingError(f"{label} must exist and be a directory: {path}")
    return path.resolve()


def _resolve_git_dir(workspace_root: Path) -> Path:
    git_entry = workspace_root / ".git"
    if git_entry.is_dir():
        return git_entry.resolve()
    if git_entry.is_file():
        content = git_entry.read_text(encoding="utf-8", errors="replace").strip()
        prefix = "gitdir:"
        if not content.lower().startswith(prefix):
            raise WorkspaceBindingError(f"Git worktree root has invalid .git file: {workspace_root}")
        git_dir = Path(content[len(prefix) :].strip())
        if not git_dir.is_absolute():
            git_dir = workspace_root / git_dir
        if not git_dir.is_dir():
            raise WorkspaceBindingError(f"Git worktree root points to missing git dir: {git_dir}")
        return git_dir.resolve()
    raise WorkspaceBindingError(f"Git worktree root is not a Git worktree: {workspace_root}")


def _resolve_common_dir(git_dir: Path) -> Path:
    common_dir_file = git_dir / "commondir"
    if not common_dir_file.exists():
        return git_dir.resolve()
    common_dir_text = common_dir_file.read_text(encoding="utf-8", errors="replace").strip()
    common_dir = Path(common_dir_text)
    if not common_dir.is_absolute():
        common_dir = git_dir / common_dir
    if not common_dir.is_dir():
        raise WorkspaceBindingError(f"Git common dir from metadata does not exist: {common_dir}")
    return common_dir.resolve()


def _read_head_ref(git_dir: Path) -> str | None:
    head_file = git_dir / "HEAD"
    if not head_file.is_file():
        raise WorkspaceBindingError(f"Git worktree root is missing HEAD: {git_dir}")
    head = head_file.read_text(encoding="utf-8", errors="replace").strip()
    prefix = "ref:"
    if not head.startswith(prefix):
        return None
    return head[len(prefix) :].strip()


def _ref_exists(repo_common_dir: Path, ref: str) -> bool:
    ref_path = repo_common_dir / Path(ref)
    if ref_path.is_file():
        return True

    packed_refs = repo_common_dir / "packed-refs"
    if not packed_refs.is_file():
        return False
    suffix = f" {ref}"
    with packed_refs.open(encoding="utf-8", errors="replace") as stream:
        return any(line.rstrip("\n").endswith(suffix) for line in stream if line and not line.startswith("#"))
