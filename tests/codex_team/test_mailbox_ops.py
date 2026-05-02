import pytest

from specify_cli.codex_team.events import event_log_path, iter_event_log
from specify_cli.codex_team.mailbox_ops import (
    broadcast_mailbox_message,
    list_mailboxes,
    mark_mailbox_delivered,
    mark_mailbox_notified,
    read_mailbox,
    send_direct_mailbox_message,
)
from specify_cli.codex_team.state_paths import mailbox_path


def _iterate_events(project_root):
    return list(iter_event_log(event_log_path(project_root)))


def test_mailbox_direct_message_persists_message_and_event(codex_team_project_root):
    send_direct_mailbox_message(
        codex_team_project_root,
        mailbox_id="worker-a",
        message_id="msg-1",
        payload={"type": "task", "task_id": "task-1"},
    )

    mailbox = read_mailbox(codex_team_project_root, "worker-a")
    assert any(msg["message_id"] == "msg-1" for msg in mailbox.messages)
    messages = mailbox.messages
    assert messages[0]["notified"] is False
    assert messages[0]["delivered"] is False

    path = mailbox_path(codex_team_project_root, "worker-a")
    assert path.exists()

    events = _iterate_events(codex_team_project_root)
    assert events[-1].kind == "mailbox.message.sent"
    assert events[-1].payload["mailbox_id"] == "worker-a"


def test_mailbox_mark_notified_and_delivered_updates_message(codex_team_project_root):
    send_direct_mailbox_message(
        codex_team_project_root,
        mailbox_id="worker-a",
        message_id="msg-2",
        payload={"type": "task", "task_id": "task-2"},
    )

    mark_mailbox_notified(
        codex_team_project_root,
        mailbox_id="worker-a",
        message_id="msg-2",
        notifier="notifier",
    )
    mailbox = read_mailbox(codex_team_project_root, "worker-a")
    message = next(msg for msg in mailbox.messages if msg["message_id"] == "msg-2")
    assert message["notified"] is True

    mark_mailbox_delivered(
        codex_team_project_root,
        mailbox_id="worker-a",
        message_id="msg-2",
        delivered_by="worker-a",
    )
    mailbox = read_mailbox(codex_team_project_root, "worker-a")
    message = next(msg for msg in mailbox.messages if msg["message_id"] == "msg-2")
    assert message["delivered"] is True

    events = _iterate_events(codex_team_project_root)
    assert events[-2].kind == "mailbox.message.notified"
    assert events[-1].kind == "mailbox.message.delivered"


def test_mailbox_broadcast_creates_entries_for_all_recipients(codex_team_project_root):
    broadcast_mailbox_message(
        codex_team_project_root,
        message_id="msg-3",
        payload={"type": "announcement"},
        recipients=["worker-a", "worker-b"],
    )

    for mailbox_id in {"worker-a", "worker-b"}:
        mailbox = read_mailbox(codex_team_project_root, mailbox_id)
        assert any(msg["message_id"] == "msg-3" for msg in mailbox.messages)
        assert mailbox.messages[0]["broadcast"] is True

    events = _iterate_events(codex_team_project_root)
    assert events[-1].kind == "mailbox.message.broadcast"


def test_list_mailboxes_returns_all_ids(codex_team_project_root):
    broadcast_mailbox_message(
        codex_team_project_root,
        message_id="msg-4",
        payload={"type": "announcement"},
        recipients=["worker-a", "worker-b"],
    )

    mailboxes = list_mailboxes(codex_team_project_root)
    ids = {mailbox.mailbox_id for mailbox in mailboxes}
    assert ids == {"worker-a", "worker-b"}


def test_mailbox_notify_and_deliver_marking_is_idempotent(codex_team_project_root):
    send_direct_mailbox_message(
        codex_team_project_root,
        mailbox_id="worker-a",
        message_id="msg-5",
        payload={"type": "task"},
    )

    first_notify = mark_mailbox_notified(
        codex_team_project_root,
        mailbox_id="worker-a",
        message_id="msg-5",
        notifier="notifier-a",
    )
    events_after_notify = _iterate_events(codex_team_project_root)
    second_notify = mark_mailbox_notified(
        codex_team_project_root,
        mailbox_id="worker-a",
        message_id="msg-5",
        notifier="notifier-b",
    )
    assert first_notify["notified"] is True
    assert second_notify["notified_at"] == first_notify["notified_at"]
    assert second_notify["notified_by"] == first_notify["notified_by"]
    assert len(events_after_notify) == len(_iterate_events(codex_team_project_root))

    first_deliver = mark_mailbox_delivered(
        codex_team_project_root,
        mailbox_id="worker-a",
        message_id="msg-5",
        delivered_by="worker-a",
    )
    events_after_deliver = _iterate_events(codex_team_project_root)
    second_deliver = mark_mailbox_delivered(
        codex_team_project_root,
        mailbox_id="worker-a",
        message_id="msg-5",
        delivered_by="worker-b",
    )
    assert first_deliver["delivered"] is True
    assert second_deliver["delivered_at"] == first_deliver["delivered_at"]
    assert second_deliver["delivered_by"] == first_deliver["delivered_by"]
    assert len(events_after_deliver) == len(_iterate_events(codex_team_project_root))


def test_mailbox_direct_message_rejects_duplicate_message_ids(codex_team_project_root):
    send_direct_mailbox_message(
        codex_team_project_root,
        mailbox_id="worker-a",
        message_id="msg-6",
        payload={"type": "task"},
    )

    with pytest.raises(ValueError):
        send_direct_mailbox_message(
            codex_team_project_root,
            mailbox_id="worker-a",
            message_id="msg-6",
            payload={"type": "task"},
        )


def test_mailbox_broadcast_rejects_duplicate_message_ids_for_same_mailbox(codex_team_project_root):
    broadcast_mailbox_message(
        codex_team_project_root,
        message_id="msg-7",
        payload={"type": "announcement"},
        recipients=["worker-a"],
    )

    with pytest.raises(ValueError):
        broadcast_mailbox_message(
            codex_team_project_root,
            message_id="msg-7",
            payload={"type": "announcement"},
            recipients=["worker-a"],
        )
