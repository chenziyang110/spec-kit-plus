"""Filesystem locations for Codex team runtime state."""

from __future__ import annotations

from pathlib import Path

from specify_cli.orchestration.state_store import orchestration_root


def codex_team_state_root(project_root: Path) -> Path:
    """Return the root directory for Codex team runtime state."""
    return orchestration_root(project_root).parent / "teams" / "state"


def runtime_session_path(project_root: Path, session_id: str) -> Path:
    """Return the persisted runtime session path."""
    return codex_team_state_root(project_root) / f"session-{session_id}.json"


def dispatch_record_path(project_root: Path, request_id: str) -> Path:
    """Return the persisted dispatch record path."""
    return codex_team_state_root(project_root) / "dispatch" / f"{request_id}.json"


def result_record_path(project_root: Path, request_id: str) -> Path:
    """Return the persisted worker result path."""
    return codex_team_state_root(project_root) / "results" / f"{request_id}.json"


def batch_record_path(project_root: Path, batch_id: str) -> Path:
    """Return the persisted batch record path."""
    return codex_team_state_root(project_root) / "batches" / f"{batch_id}.json"


def review_record_path(project_root: Path, review_id: str) -> Path:
    """Return the persisted review round record path."""
    return codex_team_state_root(project_root) / "reviews" / f"{review_id}.json"


def task_record_path(project_root: Path, task_id: str) -> Path:
    """Return the persisted task record path."""
    return codex_team_state_root(project_root) / "tasks" / f"{task_id}.json"


def worker_identity_path(project_root: Path, worker_id: str) -> Path:
    """Return the persisted worker identity path."""
    return (
        codex_team_state_root(project_root)
        / "workers"
        / "identity"
        / f"{worker_id}.json"
    )


def worker_heartbeat_path(project_root: Path, worker_id: str) -> Path:
    """Return the persisted worker heartbeat path."""
    return (
        codex_team_state_root(project_root)
        / "workers"
        / "heartbeat"
        / f"{worker_id}.json"
    )


def mailbox_path(project_root: Path, mailbox_id: str) -> Path:
    """Return the persisted mailbox record path."""
    return codex_team_state_root(project_root) / "mailboxes" / f"{mailbox_id}.json"


def phase_path(project_root: Path, phase_name: str) -> Path:
    """Return the persisted phase record path."""
    return codex_team_state_root(project_root) / "phases" / f"{phase_name}.json"


def event_log_path(project_root: Path, session_id: str | None = None) -> Path:
    """Return the append-only event log path."""
    session_suffix = session_id or "default"
    return (
        codex_team_state_root(project_root)
        / "events"
        / f"events-{session_suffix}.log"
    )


def shutdown_path(project_root: Path, session_id: str | None = None) -> Path:
    """Return the persisted shutdown request path."""
    session_suffix = session_id or "request"
    return (
        codex_team_state_root(project_root)
        / "shutdown"
        / f"{session_suffix}.json"
    )


def task_claim_path(project_root: Path, claim_id: str) -> Path:
    """Return the persisted task claim path."""
    return codex_team_state_root(project_root) / "claims" / f"{claim_id}.json"


def team_config_path(project_root: Path) -> Path:
    """Return the persisted team configuration path."""
    return codex_team_state_root(project_root) / "team-config.json"


def monitor_snapshot_path(project_root: Path, snapshot_id: str) -> Path:
    """Return the persisted monitor snapshot path."""
    return codex_team_state_root(project_root) / "monitor" / f"{snapshot_id}.json"


def executor_record_root(project_root: Path) -> Path:
    """Return the directory containing batch executor manifests and transcripts."""
    return codex_team_state_root(project_root) / "executors"
