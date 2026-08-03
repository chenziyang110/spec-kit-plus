"""Read-only validation of run-control authority before process launch."""

from __future__ import annotations

import re
import sqlite3
import time
from pathlib import Path
from typing import Protocol


RUN_CONTROL_SCHEMA_VERSION = "4"
_PRIVATE_REF_PATTERN = re.compile(r"refs/heads/specify/runs/[a-z0-9-]+/g[1-9][0-9]*\Z")


class LaunchBinding(Protocol):
    run_id: str
    activity_id: str
    attempt_id: str
    workspace_id: str
    workspace_generation: int
    fence: int
    workspace_root: Path
    repo_common_dir: Path
    private_ref: str


class RunControlAuthorityError(ValueError):
    """Raised when persisted run-control state does not authorize a launch."""


def valid_private_ref(value: str) -> bool:
    """Return whether *value* is a canonical runtime-owned Run branch ref."""

    return bool(_PRIVATE_REF_PATTERN.fullmatch(value))


def validate_run_control_authority(binding: LaunchBinding) -> None:
    """Require one exact, live pre-launch binding from the shared SQLite DB."""

    database_path = binding.repo_common_dir / "specify-runtime" / "run-control.sqlite"
    if not database_path.is_file():
        raise RunControlAuthorityError(f"run-control database does not exist: {database_path}")

    try:
        connection = sqlite3.connect(
            database_path.resolve().as_uri() + "?mode=ro",
            uri=True,
            timeout=5.0,
        )
    except sqlite3.Error as exc:
        raise RunControlAuthorityError(f"cannot open run-control database read-only: {exc}") from exc

    try:
        connection.execute("PRAGMA query_only = ON")
        version_row = connection.execute(
            "SELECT value FROM metadata WHERE key = 'schema_version'"
        ).fetchone()
        if version_row is None or str(version_row[0]) != RUN_CONTROL_SCHEMA_VERSION:
            actual = "missing" if version_row is None else str(version_row[0])
            raise RunControlAuthorityError(
                f"run-control schema authority mismatch: expected {RUN_CONTROL_SCHEMA_VERSION}, got {actual}"
            )

        row = connection.execute(
            """
            SELECT
                r.run_id, r.status, r.current_fence, r.owner_epoch,
                a.activity_id, a.status,
                w.workspace_id, w.generation, w.root_path, w.repo_common_dir,
                w.private_ref, w.status,
                p.attempt_id, p.workspace_generation, p.status, p.owner_epoch,
                p.fence, p.lease_until_ms
            FROM attempts AS p
            JOIN runs AS r ON r.run_id = p.run_id
            JOIN activities AS a
              ON a.activity_id = p.activity_id AND a.run_id = p.run_id
            JOIN workspaces AS w
              ON w.workspace_id = p.workspace_id AND w.run_id = p.run_id
            WHERE p.attempt_id = ?
            """,
            (binding.attempt_id,),
        ).fetchone()
    except RunControlAuthorityError:
        raise
    except sqlite3.Error as exc:
        raise RunControlAuthorityError(f"cannot read run-control launch authority: {exc}") from exc
    finally:
        connection.close()

    if row is None:
        raise RunControlAuthorityError("run-control launch authority is missing")

    (
        run_id,
        run_status,
        current_fence,
        run_owner,
        activity_id,
        activity_status,
        workspace_id,
        workspace_generation,
        workspace_root,
        repo_common_dir,
        private_ref,
        workspace_status,
        attempt_id,
        attempt_workspace_generation,
        attempt_status,
        attempt_owner,
        attempt_fence,
        lease_until_ms,
    ) = row

    try:
        exact_identity = (
            run_id == binding.run_id
            and activity_id == binding.activity_id
            and workspace_id == binding.workspace_id
            and attempt_id == binding.attempt_id
            and int(workspace_generation) == binding.workspace_generation
            and int(attempt_workspace_generation) == binding.workspace_generation
            and int(current_fence) == binding.fence
            and int(attempt_fence) == binding.fence
            and Path(str(workspace_root)).resolve() == binding.workspace_root
            and Path(str(repo_common_dir)).resolve() == binding.repo_common_dir
            and private_ref == binding.private_ref
        )
        live_state = (
            run_status == "ready"
            and activity_status == "ready"
            and workspace_status == "ready"
            and attempt_status == "issued"
            and run_owner == attempt_owner
            and int(lease_until_ms) > int(time.time() * 1000)
        )
    except (OSError, TypeError, ValueError) as exc:
        raise RunControlAuthorityError("run-control launch authority is invalid") from exc
    if not exact_identity or not live_state:
        raise RunControlAuthorityError("run-control launch authority is stale or mismatched")
