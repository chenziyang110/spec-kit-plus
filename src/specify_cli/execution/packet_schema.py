"""Typed execution packet contract for delegated work."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field, fields
from typing import Literal


PacketMode = Literal["hard_fail"]


@dataclass(slots=True)
class PacketReference:
    path: str
    reason: str


@dataclass(slots=True)
class PacketScope:
    write_scope: list[str] = field(default_factory=list)
    read_scope: list[str] = field(default_factory=list)


@dataclass(slots=True)
class DispatchPolicy:
    mode: PacketMode = "hard_fail"
    must_acknowledge_rules: bool = True


@dataclass(slots=True)
class ExecutionIntent:
    outcome: str = ""
    constraints: list[str] = field(default_factory=list)
    success_signals: list[str] = field(default_factory=list)


@dataclass(slots=True)
class WorkerTaskPacket:
    feature_id: str
    task_id: str
    story_id: str
    objective: str
    scope: PacketScope
    required_references: list[PacketReference]
    hard_rules: list[str]
    forbidden_drift: list[str]
    validation_gates: list[str]
    done_criteria: list[str]
    handoff_requirements: list[str]
    intent: ExecutionIntent = field(default_factory=ExecutionIntent)
    dispatch_policy: DispatchPolicy = field(default_factory=DispatchPolicy)
    packet_version: int = 2


def _filter_dataclass_payload(cls: type, payload: dict[str, object]) -> dict[str, object]:
    allowed = {item.name for item in fields(cls)}
    return {key: value for key, value in payload.items() if key in allowed}


def worker_task_packet_payload(packet: WorkerTaskPacket) -> dict[str, object]:
    """Return a JSON-serializable payload for a worker packet."""

    return asdict(packet)


def worker_task_packet_from_json(text: str) -> WorkerTaskPacket:
    """Parse a worker packet from JSON text."""

    payload = json.loads(text)
    scope = PacketScope(**_filter_dataclass_payload(PacketScope, payload.get("scope", {})))
    required_references = [
        PacketReference(**_filter_dataclass_payload(PacketReference, item))
        for item in payload.get("required_references", [])
        if isinstance(item, dict)
    ]
    intent = ExecutionIntent(
        **_filter_dataclass_payload(ExecutionIntent, payload.get("intent", {}))
    )
    dispatch_policy = DispatchPolicy(
        **_filter_dataclass_payload(DispatchPolicy, payload.get("dispatch_policy", {}))
    )
    packet_payload = _filter_dataclass_payload(WorkerTaskPacket, payload)
    packet_payload["intent"] = intent
    packet_payload["scope"] = scope
    packet_payload["required_references"] = required_references
    packet_payload["dispatch_policy"] = dispatch_policy
    return WorkerTaskPacket(**packet_payload)
