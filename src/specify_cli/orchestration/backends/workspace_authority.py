"""Durable run-control validation and one-shot process launch claims."""

from __future__ import annotations

import hashlib
import json
import re
import secrets
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, Sequence


RUN_CONTROL_SCHEMA_VERSION = "4"
_PRIVATE_REF_PATTERN = re.compile(r"refs/heads/specify/runs/[a-z0-9-]+/g[1-9][0-9]*\Z")
_LIVE_LAUNCH_STATUSES = ("prepared", "executing", "succeeded", "outcome_unknown")
_AUTHORITY_QUERY = """
    SELECT
        r.run_id, r.status, r.current_fence, r.owner_epoch, r.revision,
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
"""


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


@dataclass(slots=True, frozen=True)
class RunControlLaunchClaim:
    """One durable attempt.launch operation held by a process launcher."""

    operation_id: str
    request_sha256: str


@dataclass(slots=True, frozen=True)
class _AuthoritySnapshot:
    owner_epoch: str
    run_revision: int


def valid_private_ref(value: str) -> bool:
    """Return whether *value* is a canonical runtime-owned Run branch ref."""

    return bool(_PRIVATE_REF_PATTERN.fullmatch(value))


def claim_run_control_launch(
    binding: LaunchBinding,
    command: Sequence[str],
) -> RunControlLaunchClaim:
    """Atomically claim the only live attempt.launch operation for an Attempt."""

    database_path = _database_path(binding)
    operation_id = f"attempt_launch_{time.time_ns():020d}_{secrets.token_hex(8)}"
    request_sha256 = _launch_request_sha256(binding, command)
    now_ms = int(time.time() * 1000)
    connection = _open_database_writable(database_path)
    try:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("BEGIN IMMEDIATE")
        _require_schema_version(connection)
        authority = _validate_authority_row(
            connection.execute(_AUTHORITY_QUERY, (binding.attempt_id,)).fetchone(),
            binding,
        )
        live = connection.execute(
            """
            SELECT operation_id
            FROM operations
            WHERE attempt_id = ? AND kind = 'attempt.launch'
              AND status IN (?, ?, ?, ?)
            LIMIT 1
            """,
            (binding.attempt_id, *_LIVE_LAUNCH_STATUSES),
        ).fetchone()
        if live is not None:
            raise RunControlAuthorityError(
                f"attempt launch authority is already claimed by {live[0]}"
            )
        connection.execute(
            """
            INSERT INTO operations (
                operation_id, kind, aggregate_type, aggregate_id,
                run_id, attempt_id, activity_id, workspace_id,
                owner_epoch, fence, run_revision,
                idempotency_key, request_sha256, status, revision,
                created_at_ms, updated_at_ms
            ) VALUES (?, 'attempt.launch', 'workspace', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'executing', 1, ?, ?)
            """,
            (
                operation_id,
                binding.workspace_id,
                binding.run_id,
                binding.attempt_id,
                binding.activity_id,
                binding.workspace_id,
                authority.owner_epoch,
                binding.fence,
                authority.run_revision,
                f"attempt-launch:{operation_id}",
                request_sha256,
                now_ms,
                now_ms,
            ),
        )
        connection.commit()
    except sqlite3.IntegrityError as exc:
        _rollback_quietly(connection)
        raise RunControlAuthorityError("attempt launch authority is already claimed") from exc
    except RunControlAuthorityError:
        _rollback_quietly(connection)
        raise
    except sqlite3.Error as exc:
        _rollback_quietly(connection)
        raise RunControlAuthorityError(f"cannot claim run-control launch authority: {exc}") from exc
    finally:
        connection.close()
    return RunControlLaunchClaim(
        operation_id=operation_id,
        request_sha256=request_sha256,
    )


def finish_run_control_launch(
    binding: LaunchBinding,
    claim: RunControlLaunchClaim,
    *,
    succeeded: bool,
) -> None:
    """Record the definite outcome of one claimed local process spawn."""

    database_path = _database_path(binding)
    next_status = "succeeded" if succeeded else "failed"
    now_ms = int(time.time() * 1000)
    connection = _open_database_writable(database_path)
    try:
        connection.execute("BEGIN IMMEDIATE")
        _require_schema_version(connection)
        cursor = connection.execute(
            """
            UPDATE operations
            SET status = ?, revision = revision + 1, updated_at_ms = ?
            WHERE operation_id = ? AND kind = 'attempt.launch'
              AND run_id = ? AND attempt_id = ?
              AND activity_id = ? AND workspace_id = ?
              AND fence = ? AND request_sha256 = ? AND status = 'executing'
            """,
            (
                next_status,
                now_ms,
                claim.operation_id,
                binding.run_id,
                binding.attempt_id,
                binding.activity_id,
                binding.workspace_id,
                binding.fence,
                claim.request_sha256,
            ),
        )
        if cursor.rowcount != 1:
            raise RunControlAuthorityError(
                "attempt launch authority changed before its outcome was recorded"
            )
        connection.commit()
    except RunControlAuthorityError:
        _rollback_quietly(connection)
        raise
    except sqlite3.Error as exc:
        _rollback_quietly(connection)
        raise RunControlAuthorityError(f"cannot finish run-control launch authority: {exc}") from exc
    finally:
        connection.close()


def _database_path(binding: LaunchBinding) -> Path:
    database_path = binding.repo_common_dir / "specify-runtime" / "run-control.sqlite"
    if not database_path.is_file():
        raise RunControlAuthorityError(f"run-control database does not exist: {database_path}")
    return database_path


def _open_database_writable(database_path: Path) -> sqlite3.Connection:
    try:
        return sqlite3.connect(database_path, timeout=5.0, isolation_level=None)
    except sqlite3.Error as exc:
        raise RunControlAuthorityError(f"cannot open run-control database for launch claim: {exc}") from exc


def _require_schema_version(connection: sqlite3.Connection) -> None:
    version_row = connection.execute(
        "SELECT value FROM metadata WHERE key = 'schema_version'"
    ).fetchone()
    if version_row is None or str(version_row[0]) != RUN_CONTROL_SCHEMA_VERSION:
        actual = "missing" if version_row is None else str(version_row[0])
        raise RunControlAuthorityError(
            f"run-control schema authority mismatch: expected {RUN_CONTROL_SCHEMA_VERSION}, got {actual}"
        )


def _validate_authority_row(
    row: tuple[object, ...] | None,
    binding: LaunchBinding,
) -> _AuthoritySnapshot:
    if row is None:
        raise RunControlAuthorityError("run-control launch authority is missing")

    (
        run_id,
        run_status,
        current_fence,
        run_owner,
        run_revision,
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
            and valid_private_ref(binding.private_ref)
        )
        live_state = (
            run_status == "ready"
            and activity_status == "ready"
            and workspace_status == "ready"
            and attempt_status == "issued"
            and run_owner == attempt_owner
            and int(run_revision) > 0
            and int(lease_until_ms) > int(time.time() * 1000)
        )
    except (OSError, TypeError, ValueError) as exc:
        raise RunControlAuthorityError("run-control launch authority is invalid") from exc
    if not exact_identity or not live_state:
        raise RunControlAuthorityError("run-control launch authority is stale or mismatched")
    return _AuthoritySnapshot(
        owner_epoch=str(run_owner),
        run_revision=int(run_revision),
    )


def _launch_request_sha256(binding: LaunchBinding, command: Sequence[str]) -> str:
    payload = {
        "activity_id": binding.activity_id,
        "argv": list(command),
        "attempt_id": binding.attempt_id,
        "fence": binding.fence,
        "private_ref": binding.private_ref,
        "repo_common_dir": str(binding.repo_common_dir),
        "run_id": binding.run_id,
        "workspace_generation": binding.workspace_generation,
        "workspace_id": binding.workspace_id,
        "workspace_root": str(binding.workspace_root),
    }
    encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode()
    return hashlib.sha256(encoded).hexdigest()


def _rollback_quietly(connection: sqlite3.Connection) -> None:
    if connection.in_transaction:
        try:
            connection.rollback()
        except sqlite3.Error:
            pass
