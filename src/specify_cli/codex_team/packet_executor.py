"""Packet execution helpers for background Codex team workers."""

from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

from specify_cli.execution import (
    RuleAcknowledgement,
    ValidationResult,
    WorkerTaskPacket,
    WorkerTaskResult,
    normalize_worker_task_result_payload,
    validate_worker_task_result,
    worker_task_packet_from_json,
    worker_task_packet_payload,
    worker_task_result_payload,
)


PACKET_EXECUTOR_ENV = "SPECIFY_CODEX_TEAM_PACKET_EXECUTOR"


@dataclass(slots=True)
class PacketExecutionOutcome:
    result: WorkerTaskResult
    stdout: str = ""
    stderr: str = ""
    reason: str = ""
    executor_command: list[str] = field(default_factory=list)


def load_packet(packet_path: Path) -> WorkerTaskPacket:
    return worker_task_packet_from_json(packet_path.read_text(encoding="utf-8"))


def build_result_template(packet: WorkerTaskPacket) -> dict[str, object]:
    result = WorkerTaskResult(
        task_id=packet.task_id,
        status="pending",
        changed_files=list(packet.scope.write_scope),
        validation_results=[
            ValidationResult(
                command=gate,
                status="skipped",
                output="NOT RUN - replace with actual command output after execution",
            )
            for gate in packet.validation_gates
        ],
        summary=packet.objective,
        rule_acknowledgement=RuleAcknowledgement(
            required_references_read=False,
            forbidden_drift_respected=False,
            context_bundle_read=False,
            paths_read=[],
            critical_notes=[
                "Replace the pending placeholder with the real RED/GREEN or validation evidence before returning success.",
            ],
        ),
    )
    return worker_task_result_payload(result)


def _blocked_result(packet: WorkerTaskPacket, *, reason: str) -> WorkerTaskResult:
    return WorkerTaskResult(
        task_id=packet.task_id,
        status="blocked",
        changed_files=[],
        validation_results=[
            ValidationResult(command=gate, status="skipped", output="packet executor did not run")
            for gate in packet.validation_gates
        ],
        summary=f"Packet execution blocked for {packet.task_id}",
        concerns=[reason],
        blockers=[reason],
        failed_assumptions=["A runnable packet executor was available for this worker."],
        suggested_recovery_actions=[
            f"Set {PACKET_EXECUTOR_ENV} to a runnable packet executor command.",
            "Switch this batch to agent-teams-runtime when a runtime-cli-backed executor is available.",
        ],
        rule_acknowledgement=RuleAcknowledgement(
            required_references_read=True,
            forbidden_drift_respected=True,
            context_bundle_read=bool(packet.context_bundle),
            paths_read=[item.path for item in packet.context_bundle if item.must_read],
        ),
    )


def resolve_packet_executor_command() -> list[str] | None:
    raw = os.environ.get(PACKET_EXECUTOR_ENV, "").strip()
    if not raw:
        return None

    candidate = Path(raw)
    if candidate.is_file():
        if candidate.suffix.lower() == ".py":
            return [sys.executable, str(candidate)]
        return [str(candidate)]

    split = shlex.split(raw, posix=os.name != "nt")
    if not split:
        return None
    if len(split) == 1:
        token = Path(split[0])
        if token.is_file() and token.suffix.lower() == ".py":
            return [sys.executable, str(token)]
    return split


def execute_packet(
    packet: WorkerTaskPacket,
    *,
    project_root: Path,
    session_id: str,
    request_id: str,
    worker_id: str,
    worktree: Path,
) -> PacketExecutionOutcome:
    command = resolve_packet_executor_command()
    if command is None:
        reason = (
            "No packet executor command is configured. "
            f"Set {PACKET_EXECUTOR_ENV} to run delegated packet work."
        )
        return PacketExecutionOutcome(
            result=_blocked_result(packet, reason=reason),
            reason=reason,
        )

    payload = {
        "session_id": session_id,
        "request_id": request_id,
        "worker_id": worker_id,
        "project_root": str(project_root),
        "worktree": str(worktree),
        "packet": worker_task_packet_payload(packet),
        "result_template": build_result_template(packet),
    }
    completed = subprocess.run(
        command,
        cwd=str(project_root),
        input=json.dumps(payload, ensure_ascii=False),
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    )
    stdout = completed.stdout.strip()
    stderr = completed.stderr.strip()
    if completed.returncode != 0:
        reason = stderr or stdout or f"packet executor exited with code {completed.returncode}"
        return PacketExecutionOutcome(
            result=_blocked_result(packet, reason=reason),
            stdout=stdout,
            stderr=stderr,
            reason=reason,
            executor_command=command,
        )

    if not stdout:
        reason = "packet executor returned no structured worker result"
        return PacketExecutionOutcome(
            result=_blocked_result(packet, reason=reason),
            stdout=stdout,
            stderr=stderr,
            reason=reason,
            executor_command=command,
        )

    try:
        normalized = normalize_worker_task_result_payload(stdout)
        validated = validate_worker_task_result(normalized, packet)
    except Exception as exc:
        reason = f"packet executor returned invalid structured worker result: {exc}"
        return PacketExecutionOutcome(
            result=_blocked_result(packet, reason=reason),
            stdout=stdout,
            stderr=stderr,
            reason=reason,
            executor_command=command,
        )

    if validated.status == "pending":
        reason = "packet executor returned a pending result instead of a terminal worker result"
        return PacketExecutionOutcome(
            result=_blocked_result(packet, reason=reason),
            stdout=stdout,
            stderr=stderr,
            reason=reason,
            executor_command=command,
        )

    return PacketExecutionOutcome(
        result=validated,
        stdout=stdout,
        stderr=stderr,
        executor_command=command,
    )


def write_result_file(result_path: Path, result: WorkerTaskResult) -> Path:
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(
        json.dumps(worker_task_result_payload(result), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return result_path
