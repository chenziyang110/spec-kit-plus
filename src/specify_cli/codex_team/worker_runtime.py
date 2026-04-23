"""Background worker runtime used by `specify team` auto-dispatch."""

from __future__ import annotations

import argparse
import json
import socket
import time
from pathlib import Path

from specify_cli.codex_team.state_paths import shutdown_path
from specify_cli.codex_team.worker_ops import (
    bootstrap_worker_identity,
    write_worker_heartbeat,
)
from specify_cli.execution import WorkerTaskResult, worker_task_result_payload


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

    result_path = Path(args.result_path) if args.result_path else None
    if result_path and not result_path.exists():
        result_path.parent.mkdir(parents=True, exist_ok=True)
        placeholder = WorkerTaskResult(
            task_id=args.task_id,
            status="pending",
            summary=f"Pending result placeholder for request {args.request_id or args.task_id}",
        )
        result_path.write_text(
            json.dumps(
                worker_task_result_payload(placeholder),
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

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

    while True:
        write_worker_heartbeat(
            project_root,
            worker_id=args.worker_id,
            status="ready",
            details={
                "session_id": args.session_id,
                "task_id": args.task_id,
                "request_id": args.request_id,
                "worktree": args.worktree,
                "result_path": args.result_path,
            },
        )
        if shutdown_path(project_root, args.session_id).exists():
            write_worker_heartbeat(
                project_root,
                worker_id=args.worker_id,
                status="shutdown_requested",
                details={
                    "session_id": args.session_id,
                    "task_id": args.task_id,
                    "request_id": args.request_id,
                    "result_path": args.result_path,
                },
            )
            return 0
        time.sleep(max(args.heartbeat_interval, 1.0))


if __name__ == "__main__":
    raise SystemExit(main())
