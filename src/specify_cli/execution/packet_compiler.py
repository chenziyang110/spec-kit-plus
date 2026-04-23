"""Compile delegated worker packets from planning artifacts."""

from __future__ import annotations

import re
from pathlib import Path

from .packet_schema import DispatchPolicy, PacketReference, PacketScope, WorkerTaskPacket
from .packet_validator import validate_worker_task_packet


SECTION_RE = re.compile(r"(?ms)^#{2,3}\s+(?P<title>.+?)\n(?P<body>.*?)(?=^#{2,3}\s+|\Z)")
BULLET_RE = re.compile(r"(?m)^\s*-\s+`?(?P<value>.+?)`?\s*$")
TASK_RE = re.compile(r"(?m)^\s*-\s\[[ xX]\]\s(?P<task_id>T\d+)(?P<body>.+)$")
PATH_RE = re.compile(r"[\w./-]+/[\w./-]+")
STORY_RE = re.compile(r"\[(US\d+)\]")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def _section_body(text: str, title: str) -> str:
    for match in SECTION_RE.finditer(text):
        if match.group("title").strip().lower() == title.strip().lower():
            return match.group("body").strip()
    return ""


def _bullet_values(text: str) -> list[str]:
    return [match.group("value").strip() for match in BULLET_RE.finditer(text)]


def _story_id_from_task_body(task_body: str) -> str:
    match = STORY_RE.search(task_body)
    return match.group(1) if match else "UNASSIGNED"


def _paths_from_task_body(task_body: str) -> list[str]:
    return PATH_RE.findall(task_body)


def _task_body(tasks_text: str, task_id: str) -> str:
    for match in TASK_RE.finditer(tasks_text):
        if match.group("task_id") == task_id:
            return match.group("body").strip()
    raise ValueError(f"Task {task_id} not found in tasks.md")


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if value and value not in seen:
            ordered.append(value)
            seen.add(value)
    return ordered


def compile_worker_task_packet(
    *,
    project_root: Path,
    feature_dir: Path,
    task_id: str,
) -> WorkerTaskPacket:
    """Compile a delegated execution packet from constitution, plan, and tasks."""

    constitution_text = _read(project_root / ".specify" / "memory" / "constitution.md")
    plan_text = _read(feature_dir / "plan.md")
    tasks_text = _read(feature_dir / "tasks.md")

    task_body = _task_body(tasks_text, task_id)
    objective = task_body

    required_references = [
        PacketReference(
            path=value,
            reason="compiled from Required Implementation References",
        )
        for value in _bullet_values(_section_body(plan_text, "Required Implementation References"))
    ]
    forbidden_drift = _bullet_values(_section_body(plan_text, "Forbidden Implementation Drift"))
    hard_rules = _unique(
        _bullet_values(constitution_text)
        + _bullet_values(_section_body(plan_text, "Task-Level Quality Floor"))
    )
    validation_gates = [
        value
        for value in _bullet_values(_section_body(tasks_text, "Validation Gates"))
        if not value.startswith("[ ]")
    ]
    if not validation_gates:
        validation_gates = [f"pytest -q -k {task_id.lower()}"]

    packet = WorkerTaskPacket(
        feature_id=feature_dir.name,
        task_id=task_id,
        story_id=_story_id_from_task_body(task_body),
        objective=objective,
        scope=PacketScope(
            write_scope=_paths_from_task_body(task_body),
            read_scope=[ref.path for ref in required_references],
        ),
        required_references=required_references,
        hard_rules=hard_rules,
        forbidden_drift=forbidden_drift,
        validation_gates=validation_gates,
        done_criteria=[objective],
        handoff_requirements=[
            "return changed files",
            "return validation results",
            "return blockers",
        ],
        dispatch_policy=DispatchPolicy(mode="hard_fail", must_acknowledge_rules=True),
    )
    return validate_worker_task_packet(packet)
