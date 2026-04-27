"""Delegation integrity hooks built on shared packet/result validators."""

from __future__ import annotations

from pathlib import Path

from specify_cli.execution import (
    PacketValidationError,
    validate_worker_task_packet,
    validate_worker_task_result,
    worker_task_packet_from_json,
    worker_task_packet_payload,
    worker_task_result_from_json,
    worker_task_result_payload,
)

from .events import DELEGATION_JOIN_VALIDATE, DELEGATION_PACKET_VALIDATE
from .types import HookResult, QualityHookError


def validate_packet_hook(_project_root: Path, payload: dict[str, object]) -> HookResult:
    packet_path = _required_path(payload, "packet_file")
    try:
        packet = validate_worker_task_packet(
            worker_task_packet_from_json(packet_path.read_text(encoding="utf-8"))
        )
    except PacketValidationError as exc:
        return HookResult(
            event=DELEGATION_PACKET_VALIDATE,
            status="blocked",
            severity="critical",
            errors=[f"{exc.code}: {exc.message}"],
        )

    return HookResult(
        event=DELEGATION_PACKET_VALIDATE,
        status="ok",
        severity="info",
        data={"packet": worker_task_packet_payload(packet)},
    )


def validate_join_hook(_project_root: Path, payload: dict[str, object]) -> HookResult:
    packet_path = _required_path(payload, "packet_file")
    result_path = _required_path(payload, "result_file")

    try:
        packet = validate_worker_task_packet(
            worker_task_packet_from_json(packet_path.read_text(encoding="utf-8"))
        )
        result = validate_worker_task_result(
            worker_task_result_from_json(result_path.read_text(encoding="utf-8")),
            packet,
        )
    except PacketValidationError as exc:
        return HookResult(
            event=DELEGATION_JOIN_VALIDATE,
            status="blocked",
            severity="critical",
            errors=[f"{exc.code}: {exc.message}"],
        )

    return HookResult(
        event=DELEGATION_JOIN_VALIDATE,
        status="ok",
        severity="info",
        data={
            "packet": worker_task_packet_payload(packet),
            "result": worker_task_result_payload(result),
        },
    )


def _required_path(payload: dict[str, object], key: str) -> Path:
    raw = str(payload.get(key) or "").strip()
    if not raw:
        raise QualityHookError(f"{key} is required")
    path = Path(raw)
    if not path.exists():
        raise QualityHookError(f"{key} does not exist: {path}")
    return path
