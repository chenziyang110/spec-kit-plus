"""Journaled multi-file updates for CLI-owned workflow state."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import shutil
import uuid

from .atomic_io import (
    atomic_write_bytes,
    atomic_write_text,
    interprocess_lock,
    read_local_state_bytes,
    safe_local_state_path,
)


class WorkflowTransactionError(RuntimeError):
    """Raised when a workflow-state transaction cannot commit or roll back."""


@dataclass(frozen=True, slots=True)
class WorkflowTransactionReceipt:
    transaction_id: str
    kind: str
    changed_paths: tuple[str, ...]
    receipt_ref: str

    def to_dict(self) -> dict[str, object]:
        return {
            "transaction_id": self.transaction_id,
            "kind": self.kind,
            "changed_paths": list(self.changed_paths),
            "receipt_ref": self.receipt_ref,
        }


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _relative_target(root: Path, target: Path) -> tuple[Path, str]:
    secured = safe_local_state_path(target, root=root)
    relative = secured.relative_to(root).as_posix()
    if relative.startswith(".git/") or relative == ".git":
        raise WorkflowTransactionError("workflow transactions cannot mutate .git")
    return secured, relative


def apply_workflow_transaction(
    project_root: Path,
    *,
    kind: str,
    updates: Mapping[Path, bytes],
    expected_before: Mapping[Path, bytes | None] | None = None,
    transaction_id: str | None = None,
) -> WorkflowTransactionReceipt:
    """Validate, journal, commit, and receipt one bounded multi-file update."""

    root = safe_local_state_path(project_root)
    normalized_kind = kind.strip()
    if not normalized_kind:
        raise WorkflowTransactionError("transaction kind is required")
    if not updates:
        raise WorkflowTransactionError("transaction requires at least one update")

    normalized: list[tuple[Path, str, bytes]] = []
    seen: set[str] = set()
    for raw_target, raw_content in updates.items():
        target, relative = _relative_target(root, Path(raw_target))
        if relative in seen:
            raise WorkflowTransactionError(
                f"transaction contains duplicate target: {relative}"
            )
        seen.add(relative)
        normalized.append((target, relative, bytes(raw_content)))
    normalized.sort(key=lambda item: item[1])

    normalized_preconditions: list[tuple[Path, str, bytes | None]] = []
    seen_preconditions: set[str] = set()
    for raw_target, expected in (expected_before or {}).items():
        target, relative = _relative_target(root, Path(raw_target))
        if relative in seen_preconditions:
            raise WorkflowTransactionError(
                f"transaction contains duplicate precondition: {relative}"
            )
        seen_preconditions.add(relative)
        normalized_preconditions.append(
            (target, relative, None if expected is None else bytes(expected))
        )
    normalized_preconditions.sort(key=lambda item: item[1])

    tx_id = transaction_id or f"TX-{uuid.uuid4().hex[:20]}"
    if not tx_id.startswith("TX-") or any(
        character not in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-"
        for character in tx_id
    ):
        raise WorkflowTransactionError("transaction id is invalid")

    runtime_root = root / ".specify" / "runtime"
    transaction_root = runtime_root / "transactions" / tx_id
    backup_root = transaction_root / "backup"
    stage_root = transaction_root / "stage"
    journal_path = transaction_root / "journal.json"
    receipt_path = runtime_root / "receipts" / f"{tx_id}.json"
    lock_path = runtime_root / "locks" / "workflow-transactions.lock"

    with interprocess_lock(lock_path):
        for target, relative, expected in normalized_preconditions:
            try:
                current = read_local_state_bytes(target, root=root)
            except FileNotFoundError:
                current = None
            if current != expected:
                expected_label = "absence" if expected is None else _sha256(expected)
                current_label = "absence" if current is None else _sha256(current)
                raise WorkflowTransactionError(
                    "transaction precondition failed for "
                    f"{relative}: expected {expected_label}, found {current_label}"
                )
        if transaction_root.exists():
            raise WorkflowTransactionError(
                f"transaction already exists and requires recovery: {tx_id}"
            )
        transaction_root.mkdir(parents=True)
        entries: list[dict[str, object]] = []
        original_content: dict[str, bytes | None] = {}
        try:
            for target, relative, content in normalized:
                previous: bytes | None
                try:
                    previous = read_local_state_bytes(target, root=root)
                except FileNotFoundError:
                    previous = None
                original_content[relative] = previous
                stage_path = stage_root / Path(relative)
                atomic_write_bytes(stage_path, content)
                backup_ref: str | None = None
                if previous is not None:
                    backup_path = backup_root / Path(relative)
                    atomic_write_bytes(backup_path, previous)
                    backup_ref = backup_path.relative_to(transaction_root).as_posix()
                entries.append(
                    {
                        "path": relative,
                        "existed": previous is not None,
                        "before_sha256": _sha256(previous) if previous is not None else None,
                        "after_sha256": _sha256(content),
                        "stage_ref": stage_path.relative_to(transaction_root).as_posix(),
                        "backup_ref": backup_ref,
                        "applied": False,
                    }
                )
            journal: dict[str, object] = {
                "version": 1,
                "transaction_id": tx_id,
                "kind": normalized_kind,
                "phase": "prepared",
                "entries": entries,
            }
            atomic_write_text(
                journal_path,
                json.dumps(journal, ensure_ascii=False, indent=2) + "\n",
            )

            for index, (target, _relative, content) in enumerate(normalized):
                atomic_write_bytes(target, content)
                entries[index]["applied"] = True
                journal["phase"] = "applying"
                atomic_write_text(
                    journal_path,
                    json.dumps(journal, ensure_ascii=False, indent=2) + "\n",
                )

            journal["phase"] = "committed"
            atomic_write_text(
                journal_path,
                json.dumps(journal, ensure_ascii=False, indent=2) + "\n",
            )
            receipt_payload = {
                "version": 1,
                "transaction_id": tx_id,
                "kind": normalized_kind,
                "status": "committed",
                "changed_paths": [relative for _target, relative, _content in normalized],
                "after_sha256": {
                    relative: _sha256(content)
                    for _target, relative, content in normalized
                },
            }
            atomic_write_text(
                receipt_path,
                json.dumps(receipt_payload, ensure_ascii=False, indent=2) + "\n",
            )
        except Exception as exc:
            rollback_errors: list[str] = []
            for target, relative, _content in reversed(normalized):
                previous = original_content.get(relative)
                try:
                    if previous is None:
                        target.unlink(missing_ok=True)
                    else:
                        atomic_write_bytes(target, previous)
                except Exception as rollback_exc:  # pragma: no cover - storage failure
                    rollback_errors.append(f"{relative}: {rollback_exc}")
            if rollback_errors:
                raise WorkflowTransactionError(
                    f"{normalized_kind} failed: {exc}; rollback incomplete: "
                    + "; ".join(rollback_errors)
                ) from exc
            shutil.rmtree(transaction_root, ignore_errors=True)
            raise WorkflowTransactionError(
                f"{normalized_kind} failed and was rolled back: {exc}"
            ) from exc

        shutil.rmtree(transaction_root, ignore_errors=True)

    return WorkflowTransactionReceipt(
        transaction_id=tx_id,
        kind=normalized_kind,
        changed_paths=tuple(relative for _target, relative, _content in normalized),
        receipt_ref=receipt_path.relative_to(root).as_posix(),
    )


__all__ = [
    "WorkflowTransactionError",
    "WorkflowTransactionReceipt",
    "apply_workflow_transaction",
]
