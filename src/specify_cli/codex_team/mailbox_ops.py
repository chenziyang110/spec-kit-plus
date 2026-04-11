"""Mailbox persistence helpers for Codex team runtime."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from specify_cli.codex_team.events import append_event, event_log_path
from specify_cli.codex_team.state_paths import codex_team_state_root, mailbox_path


@dataclass(slots=True)
class Mailbox:
    mailbox_id: str
    messages: list[dict[str, Any]]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _log_mailbox_event(project_root: Path, *, kind: str, payload: dict[str, Any]) -> None:
    log_path = event_log_path(project_root, session_id=None)
    append_event(
        log_path,
        event_id=f"mailbox-{kind}-{uuid.uuid4().hex}",
        kind=kind,
        payload=payload,
    )


def _save_mailbox(project_root: Path, mailbox: Mailbox) -> Path:
    path = mailbox_path(project_root, mailbox.mailbox_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "mailbox_id": mailbox.mailbox_id,
        "messages": mailbox.messages,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path


def read_mailbox(project_root: Path, mailbox_id: str) -> Mailbox:
    path = mailbox_path(project_root, mailbox_id)
    if not path.exists():
        return Mailbox(mailbox_id=mailbox_id, messages=[])
    payload = json.loads(path.read_text(encoding="utf-8"))
    return Mailbox(
        mailbox_id=payload.get("mailbox_id", mailbox_id),
        messages=payload.get("messages", []),
    )


def _build_message(
    *,
    message_id: str,
    payload: dict[str, Any],
    broadcast: bool,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    message: dict[str, Any] = {
        "message_id": message_id,
        "payload": payload,
        "created_at": _utc_now(),
        "broadcast": broadcast,
        "notified": False,
        "notified_at": "",
        "notified_by": "",
        "delivered": False,
        "delivered_at": "",
        "delivered_by": "",
    }
    if metadata:
        message["metadata"] = metadata
    return message


def _enqueue_message(
    project_root: Path,
    *,
    mailbox_id: str,
    message_id: str,
    payload: dict[str, Any],
    metadata: dict[str, Any] | None = None,
    broadcast: bool,
    event_kind: str | None = None,
) -> dict[str, Any]:
    mailbox = read_mailbox(project_root, mailbox_id)
    if any(msg.get("message_id") == message_id for msg in mailbox.messages):
        raise ValueError(f"message {message_id} already exists in mailbox {mailbox_id}")
    message = _build_message(
        message_id=message_id,
        payload=payload,
        broadcast=broadcast,
        metadata=metadata,
    )
    mailbox.messages.append(message)
    _save_mailbox(project_root, mailbox)
    if event_kind:
        _log_mailbox_event(
            project_root,
            kind=event_kind,
            payload={
                "mailbox_id": mailbox_id,
                "message_id": message_id,
                "broadcast": broadcast,
            },
        )
    return message


def send_direct_mailbox_message(
    project_root: Path,
    *,
    mailbox_id: str,
    message_id: str,
    payload: dict[str, Any],
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return _enqueue_message(
        project_root,
        mailbox_id=mailbox_id,
        message_id=message_id,
        payload=payload,
        metadata=metadata,
        broadcast=False,
        event_kind="mailbox.message.sent",
    )


def broadcast_mailbox_message(
    project_root: Path,
    *,
    recipients: list[str],
    message_id: str,
    payload: dict[str, Any],
    metadata: dict[str, Any] | None = None,
) -> None:
    for mailbox_id in recipients:
        _enqueue_message(
            project_root,
            mailbox_id=mailbox_id,
            message_id=message_id,
            payload=payload,
            metadata=metadata,
            broadcast=True,
            event_kind=None,
        )
    _log_mailbox_event(
        project_root,
        kind="mailbox.message.broadcast",
        payload={
            "message_id": message_id,
            "recipients": recipients,
        },
    )


def list_mailboxes(project_root: Path) -> list[Mailbox]:
    base = codex_team_state_root(project_root) / "mailboxes"
    if not base.exists():
        return []
    mailboxes: list[Mailbox] = []
    for file in sorted(base.glob("*.json")):
        payload = json.loads(file.read_text(encoding="utf-8"))
        mailboxes.append(
            Mailbox(
                mailbox_id=payload.get("mailbox_id", file.stem),
                messages=payload.get("messages", []),
            )
        )
    return mailboxes


def _locate_message(mailbox: Mailbox, message_id: str) -> dict[str, Any]:
    for message in mailbox.messages:
        if message.get("message_id") == message_id:
            return message
    raise KeyError(f"message {message_id} not found")


def mark_mailbox_notified(
    project_root: Path,
    *,
    mailbox_id: str,
    message_id: str,
    notifier: str,
) -> dict[str, Any]:
    mailbox = read_mailbox(project_root, mailbox_id)
    message = _locate_message(mailbox, message_id)
    if message.get("notified"):
        return message
    message["notified"] = True
    message["notified_at"] = _utc_now()
    message["notified_by"] = notifier
    _save_mailbox(project_root, mailbox)
    _log_mailbox_event(
        project_root,
        kind="mailbox.message.notified",
        payload={
            "mailbox_id": mailbox_id,
            "message_id": message_id,
            "notifier": notifier,
        },
    )
    return message


def mark_mailbox_delivered(
    project_root: Path,
    *,
    mailbox_id: str,
    message_id: str,
    delivered_by: str,
) -> dict[str, Any]:
    mailbox = read_mailbox(project_root, mailbox_id)
    message = _locate_message(mailbox, message_id)
    if message.get("delivered"):
        return message
    message["delivered"] = True
    message["delivered_at"] = _utc_now()
    message["delivered_by"] = delivered_by
    _save_mailbox(project_root, mailbox)
    _log_mailbox_event(
        project_root,
        kind="mailbox.message.delivered",
        payload={
            "mailbox_id": mailbox_id,
            "message_id": message_id,
            "delivered_by": delivered_by,
        },
    )
    return message
