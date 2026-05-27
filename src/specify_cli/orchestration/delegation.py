"""Shared helpers for describing per-command subagent dispatch."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from specify_cli.execution import describe_result_handoff_template

from .models import CapabilitySnapshot


DelegationIntent = Literal["implementation", "evidence"]


@dataclass(slots=True, frozen=True)
class DelegationSurfaceDescriptor:
    """Normalized description of how the current session should dispatch work."""

    integration_key: str
    command_name: str
    intent: DelegationIntent
    native_subagent_surface: str
    native_discovery_hint: str
    native_dispatch_hint: str
    native_join_hint: str
    managed_team_hint: str
    result_contract_hint: str
    result_handoff_hint: str
    structured_results_expected: bool
    leader_local_fallback_allowed: bool = True


def _command_intent(command_name: str) -> DelegationIntent:
    normalized = command_name.strip().lower()
    return "evidence" if normalized in {"debug", "map-scan", "map-build", "map-update"} else "implementation"

def describe_delegation_surface(
    *,
    command_name: str,
    snapshot: CapabilitySnapshot,
) -> DelegationSurfaceDescriptor:
    """Describe how the current integration should dispatch and rejoin work."""

    normalized_command = command_name.strip().lower()
    intent = _command_intent(command_name)
    result_contract_hint = (
        "Fact-only evidence payload: hypothesis tested, commands run, files inspected, observations, confidence, blocker."
        if intent == "evidence"
        else "WorkerTaskResult contract with status, changed files, validation evidence, blockers, failed assumptions, and recovery guidance."
    )
    structured_results_expected = snapshot.structured_results or intent == "implementation"

    integration_key = snapshot.integration_key.strip().lower()
    native_discovery_hint = (
        "Check current runtime/tool discovery for an integration-native subagent or task-dispatch surface first; no known native subagent surface is configured for this integration, so record the unavailable surface explicitly before using a fallback or blocked state."
    )
    native_dispatch_hint = "No subagent dispatch path for this session."
    native_join_hint = (
        "Stay on the leader path and keep the current lane explicit."
        if normalized_command == "implement"
        else "Stay on the leader path and keep the current lane explicit."
    )

    if snapshot.native_worker_surface == "spawn_agent":
        native_discovery_hint = (
            "Before recording `subagent-blocked`, confirm the current runtime exposes `spawn_agent`, `wait_agent`, and `close_agent`; if they are not visible, use the active tool discovery mechanism for multi-agent or subagent tools first."
        )
        native_dispatch_hint = "Dispatch bounded subagents through `spawn_agent`."
        native_join_hint = "Rejoin with `wait_agent`, integrate, then `close_agent`."
    elif snapshot.native_worker_surface == "native-cli":
        if integration_key == "gemini":
            native_discovery_hint = (
                "Before recording `subagent-blocked`, check the active Gemini CLI surface for `@agent-name` or `@generalist` subagent dispatch and record the exact missing surface if unavailable."
            )
            native_dispatch_hint = (
                "Dispatch bounded lanes with `@generalist` or a named `@agent-name` using the shared prompt contract."
            )
            native_join_hint = (
                "Request independent `@generalist` lanes together for parallel work when safe, then integrate results back on the leader path."
            )
        elif integration_key == "copilot":
            native_discovery_hint = (
                "Before recording `subagent-blocked`, check the active Copilot CLI surface for `task`, `read_agent`, and `list_agents`; record the exact missing surface if unavailable."
            )
            native_dispatch_hint = (
                "Dispatch bounded lanes through Copilot CLI `task` with an appropriate agent type using the shared prompt contract."
            )
            native_join_hint = "Rejoin through `read_agent` or `list_agents`, then integrate results back on the leader path."
        else:
            native_discovery_hint = (
                "Before recording `subagent-blocked`, check the active tool surface for the integration-native subagent or task-dispatch entrypoint and record the exact missing surface if unavailable."
            )
            native_dispatch_hint = (
                "Dispatch subagents through the integration's native subagent support using the shared prompt contract."
            )
            native_join_hint = (
                "Use the integration-native join point, then integrate results back on the leader path."
            )

    if normalized_command == "debug":
        managed_team_hint = (
            "No managed-team or leader-inline fallback for `sp-debug`; choose `leader-inline` up front for a small focused investigation, or record `subagent-blocked` with `execution_surface: none` when the next safe step cannot proceed."
        )
    elif normalized_command == "implement":
        managed_team_hint = (
            "No in-command team fallback for `sp-implement`; if subagents cannot proceed safely, stay on the leader path and record why."
        )
    else:
        managed_team_hint = (
            "Use the managed team workflow when subagents are unavailable, low-confidence, or unsuitable."
            if snapshot.managed_team_supported
            else "No managed team workflow is currently available; use leader-inline fallback only when subagents cannot proceed safely."
        )

    return DelegationSurfaceDescriptor(
        integration_key=snapshot.integration_key,
        command_name=command_name,
        intent=intent,
        native_subagent_surface=snapshot.native_worker_surface,
        native_discovery_hint=native_discovery_hint,
        native_dispatch_hint=native_dispatch_hint,
        native_join_hint=native_join_hint,
        managed_team_hint=managed_team_hint,
        result_contract_hint=result_contract_hint,
        result_handoff_hint=describe_result_handoff_template(
            command_name=command_name,
            integration_key=snapshot.integration_key,
        ),
        structured_results_expected=structured_results_expected,
    )


@dataclass(slots=True, frozen=True)
class TaskContractValidation:
    """Result of validating a single task contract before dispatch."""
    task_id: str
    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    auto_corrections: dict[str, str] = field(default_factory=dict)


KNOWN_AGENT_ROLES = frozenset({
    "security-reviewer",
    "test-engineer",
    "style-reviewer",
    "performance-reviewer",
    "quality-reviewer",
    "api-reviewer",
    "debugger",
    "code-simplifier",
    "build-fixer",
    "git-master",
    "executor",
})


def validate_task_contract(
    *,
    task_id: str,
    agent: str,
    write_scope: list[str] | None = None,
    depends_on: list[str] | None = None,
    project_root: str = ".",
) -> TaskContractValidation:
    """Validate a task contract has the minimum fields for safe subagent dispatch."""
    errors: list[str] = []
    warnings: list[str] = []
    corrections: dict[str, str] = {}

    # 1. agent_exists
    resolved_agent = agent.strip().lower() if agent else ""
    if not resolved_agent:
        corrections["agent"] = "executor"
        resolved_agent = "executor"
    elif resolved_agent not in KNOWN_AGENT_ROLES:
        warnings.append(f"agent '{agent}' not in known role pool, using 'executor'")
        corrections["agent"] = "executor"
        resolved_agent = "executor"

    # 2. deps_acyclic — simple self-reference check
    if depends_on:
        for dep in depends_on:
            if dep.strip() == task_id.strip():
                errors.append(f"task {task_id} depends on itself")
                break

    # 3. forbidden_safe — ensure sensitive paths are covered
    write_paths = write_scope or []
    sensitive_patterns = {".env", "credentials", "secrets", "secret", ".key", ".pem"}
    for path in write_paths:
        path_lower = path.lower()
        for pattern in sensitive_patterns:
            if pattern in path_lower:
                warnings.append(
                    f"write_scope includes potentially sensitive path '{path}'"
                )
                break

    valid = len(errors) == 0
    return TaskContractValidation(
        task_id=task_id,
        valid=valid,
        errors=errors,
        warnings=warnings,
        auto_corrections=corrections,
    )


def validate_batch_isolation(
    tasks: list[dict[str, object]],
) -> list[dict[str, object]]:
    """Check a batch of tasks for write-set isolation. Returns list of conflicts."""
    conflicts: list[dict[str, object]] = []
    for i, task_a in enumerate(tasks):
        write_a = set(
            str(p) for p in (task_a.get("write_scope") or [])
        )
        if not write_a:
            continue
        for j in range(i + 1, len(tasks)):
            task_b = tasks[j]
            write_b = set(
                str(p) for p in (task_b.get("write_scope") or [])
            )
            overlap = write_a & write_b
            if overlap:
                conflicts.append({
                    "task_a": str(task_a.get("task_id", i)),
                    "task_b": str(task_b.get("task_id", j)),
                    "overlapping_paths": sorted(overlap),
                })
    return conflicts
