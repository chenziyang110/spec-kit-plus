"""Background worker runtime used by `sp-teams` auto-dispatch."""

from __future__ import annotations

import argparse
import json
import socket
from pathlib import Path

from specify_cli.codex_team.packet_executor import execute_packet, load_packet, write_result_file
from specify_cli.codex_team.state_paths import codex_team_state_root, dispatch_record_path
from specify_cli.codex_team.worker_ops import (
    bootstrap_worker_identity,
    write_worker_heartbeat,
)


LEGACY_HEARTBEAT_EXECUTOR = "legacy-heartbeat-runtime"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Codex team background worker runtime")
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--session-id", required=True)
    parser.add_argument("--worker-id", required=True)
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--request-id", required=False, default="")
    parser.add_argument("--worktree", required=True)
    parser.add_argument("--result-path", required=False, default="")
    parser.add_argument("--heartbeat-interval", type=float, default=5.0)
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    project_root = Path(args.project_root)

    bootstrap_worker_identity(
        project_root,
        worker_id=args.worker_id,
        hostname=socket.gethostname(),
        metadata={
            "session_id": args.session_id,
            "task_id": args.task_id,
            "request_id": args.request_id,
            "worktree": args.worktree,
            "result_path": args.result_path,
        },
    )

    packet_path = _resolve_packet_path(project_root, request_id=args.request_id)
    if packet_path is None:
        write_worker_heartbeat(
            project_root,
            worker_id=args.worker_id,
            status="failed",
            details={
                "session_id": args.session_id,
                "task_id": args.task_id,
                "request_id": args.request_id,
                "worktree": args.worktree,
                "result_path": args.result_path,
                "reason": "worker runtime could not resolve a packet path for this request",
            },
        )
        return 1

    result_path = (
        Path(args.result_path)
        if args.result_path
        else codex_team_state_root(project_root) / "results" / f"{args.request_id or args.task_id}.json"
    )
    packet = load_packet(packet_path)

    write_worker_heartbeat(
        project_root,
        worker_id=args.worker_id,
        status="starting",
        details={
            "session_id": args.session_id,
            "task_id": args.task_id,
            "request_id": args.request_id,
            "packet_path": str(packet_path),
            "worktree": args.worktree,
            "result_path": str(result_path),
        },
    )
    outcome = execute_packet(
        packet,
        project_root=project_root,
        session_id=args.session_id,
        request_id=args.request_id,
        worker_id=args.worker_id,
        worktree=Path(args.worktree),
    )
    write_worker_heartbeat(
        project_root,
        worker_id=args.worker_id,
        status="executing",
        details={
            "session_id": args.session_id,
            "task_id": args.task_id,
            "request_id": args.request_id,
            "packet_path": str(packet_path),
            "worktree": args.worktree,
            "result_path": str(result_path),
            "executor_command": outcome.executor_command,
        },
    )
    write_result_file(result_path, outcome.result)
    write_worker_heartbeat(
        project_root,
        worker_id=args.worker_id,
        status="result_written",
        details={
            "session_id": args.session_id,
            "task_id": args.task_id,
            "request_id": args.request_id,
            "packet_path": str(packet_path),
            "worktree": args.worktree,
            "result_path": str(result_path),
            "executor_command": outcome.executor_command,
        },
    )
    write_worker_heartbeat(
        project_root,
        worker_id=args.worker_id,
        status=_terminal_worker_status(outcome.result.status),
        details={
            "session_id": args.session_id,
            "task_id": args.task_id,
            "request_id": args.request_id,
            "packet_path": str(packet_path),
            "worktree": args.worktree,
            "result_path": str(result_path),
            "executor_command": outcome.executor_command,
            "reason": outcome.reason,
            "result_status": outcome.result.status,
        },
    )
    return 0


def _resolve_packet_path(project_root: Path, *, request_id: str) -> Path | None:
    if request_id:
        dispatch_path = dispatch_record_path(project_root, request_id)
        if dispatch_path.exists():
            try:
                payload = json.loads(dispatch_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                payload = {}
            packet_path = str(payload.get("packet_path", "")).strip()
            if packet_path:
                candidate = Path(packet_path)
                if candidate.exists():
                    return candidate

        candidate = codex_team_state_root(project_root) / "packets" / f"{request_id}.json"
        if candidate.exists():
            return candidate
    return None


def _terminal_worker_status(result_status: str) -> str:
    if result_status == "success":
        return "completed"
    if result_status == "blocked":
        return "blocked"
    return "failed"


if __name__ == "__main__":
    raise SystemExit(main())
