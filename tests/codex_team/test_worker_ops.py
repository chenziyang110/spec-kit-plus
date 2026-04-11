from specify_cli.codex_team.events import event_log_path, iter_event_log
from specify_cli.codex_team.state_paths import worker_heartbeat_path, worker_identity_path
from specify_cli.codex_team.worker_ops import (
    bootstrap_worker_identity,
    list_worker_identities,
    read_worker_heartbeat,
    worker_status_snapshot,
    write_worker_heartbeat,
)


def _iterate_events(project_root):
    return list(iter_event_log(event_log_path(project_root)))


def test_worker_identity_bootstrap_creates_record_and_event(codex_team_project_root):
    identity = bootstrap_worker_identity(
        codex_team_project_root,
        worker_id="worker-a",
        hostname="host.local",
    )

    assert identity.worker_id == "worker-a"
    path = worker_identity_path(codex_team_project_root, "worker-a")
    assert path.exists()

    events = _iterate_events(codex_team_project_root)
    assert events[-1].kind == "worker.identity.created"
    assert events[-1].payload["worker_id"] == "worker-a"


def test_worker_identity_bootstrap_is_idempotent(codex_team_project_root):
    first = bootstrap_worker_identity(
        codex_team_project_root,
        worker_id="worker-a",
        hostname="host.local",
    )
    events_after_first = _iterate_events(codex_team_project_root)

    second = bootstrap_worker_identity(
        codex_team_project_root,
        worker_id="worker-a",
        hostname="host.local",
    )
    events_after_second = _iterate_events(codex_team_project_root)

    assert second.created_at == first.created_at
    assert len(events_after_second) == len(events_after_first)


def test_worker_heartbeat_round_trips_and_events(codex_team_project_root):
    write_worker_heartbeat(
        codex_team_project_root,
        worker_id="worker-a",
        status="ready",
    )

    heartbeat = read_worker_heartbeat(codex_team_project_root, "worker-a")
    assert heartbeat.status == "ready"
    path = worker_heartbeat_path(codex_team_project_root, "worker-a")
    assert path.exists()

    events = _iterate_events(codex_team_project_root)
    assert events[-1].kind == "worker.heartbeat.updated"
    assert events[-1].payload["status"] == "ready"


def test_worker_status_snapshot_summarizes_heartbeats(codex_team_project_root):
    write_worker_heartbeat(
        codex_team_project_root,
        worker_id="worker-a",
        status="ready",
    )
    write_worker_heartbeat(
        codex_team_project_root,
        worker_id="worker-b",
        status="busy",
    )

    snapshot = worker_status_snapshot(
        codex_team_project_root,
        snapshot_id="snapshot-1",
        task_count=5,
    )

    assert snapshot.worker_count == 2
    assert snapshot.task_count == 5
    assert snapshot.status_breakdown == {"ready": 1, "busy": 1}
    events = _iterate_events(codex_team_project_root)
    assert events[-1].kind == "worker.snapshot"
    assert events[-1].payload["snapshot_id"] == "snapshot-1"


def test_list_worker_identities_returns_all_registered_workers(codex_team_project_root):
    bootstrap_worker_identity(
        codex_team_project_root,
        worker_id="worker-a",
        hostname="host.local",
    )
    bootstrap_worker_identity(
        codex_team_project_root,
        worker_id="worker-b",
        hostname="host.remote",
    )

    identities = list_worker_identities(codex_team_project_root)
    ids = {identity.worker_id for identity in identities}

    assert ids == {"worker-a", "worker-b"}
