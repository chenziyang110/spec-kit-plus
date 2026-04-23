"""Typed execution packet contract for delegated work."""

from __future__ import annotations

from dataclasses import dataclass, field
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
    dispatch_policy: DispatchPolicy = field(default_factory=DispatchPolicy)
    packet_version: int = 1
