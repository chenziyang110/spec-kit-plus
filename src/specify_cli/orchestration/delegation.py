"""Shared helpers for describing per-command subagent dispatch."""

from __future__ import annotations

from dataclasses import dataclass
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
    native_dispatch_hint: str
    native_join_hint: str
    managed_team_hint: str
    result_contract_hint: str
    result_handoff_hint: str
    structured_results_expected: bool
    leader_local_fallback_allowed: bool = True


def _command_intent(command_name: str) -> DelegationIntent:
    normalized = command_name.strip().lower()
    return "evidence" if normalized in {"debug", "test-scan"} else "implementation"

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

    native_dispatch_hint = "No subagent dispatch path for this session."
    native_join_hint = (
        "Stay on the leader path and keep the current lane explicit."
        if normalized_command == "implement"
        else "Stay on the leader path or use the managed team workflow."
    )

    if snapshot.native_worker_surface == "spawn_agent":
        native_dispatch_hint = "Dispatch bounded subagents through `spawn_agent`."
        native_join_hint = "Rejoin with `wait_agent`, integrate, then `close_agent`."
    elif snapshot.native_worker_surface == "native-cli":
        native_dispatch_hint = (
            "Dispatch subagents through the integration's native subagent support using the shared prompt contract."
        )
        native_join_hint = (
            "Use the integration-native join point, then integrate results back on the leader path."
        )

    if normalized_command == "implement":
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
