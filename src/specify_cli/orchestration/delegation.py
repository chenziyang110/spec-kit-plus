"""Shared helpers for describing per-command delegation surfaces."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from specify_cli.execution import describe_result_handoff_template

from .models import CapabilitySnapshot


DelegationIntent = Literal["implementation", "evidence"]


@dataclass(slots=True, frozen=True)
class DelegationSurfaceDescriptor:
    """Normalized description of how the current session should delegate work."""

    integration_key: str
    command_name: str
    intent: DelegationIntent
    native_surface: str
    native_dispatch_hint: str
    native_join_hint: str
    sidecar_surface_hint: str
    result_contract_hint: str
    result_handoff_hint: str
    structured_results_expected: bool
    leader_local_fallback_allowed: bool = True


def _command_intent(command_name: str) -> DelegationIntent:
    normalized = command_name.strip().lower()
    return "evidence" if normalized == "debug" else "implementation"

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

    native_dispatch_hint = "No native delegated worker surface for this session."
    native_join_hint = (
        "Stay on the leader path and keep the current lane explicit."
        if normalized_command == "implement"
        else "Stay on the leader path or use the coordinated runtime surface."
    )

    if snapshot.native_worker_surface == "spawn_agent":
        native_dispatch_hint = "Dispatch bounded lanes through `spawn_agent`."
        native_join_hint = "Rejoin with `wait_agent`, integrate, then `close_agent`."
    elif snapshot.native_worker_surface == "native-cli":
        native_dispatch_hint = (
            "Dispatch through the integration's native delegated worker surface using the shared worker prompt contract."
        )
        native_join_hint = (
            "Use the integration-native join point, then integrate results back on the leader path."
        )

    if normalized_command == "implement":
        sidecar_surface_hint = (
            "No in-command runtime fallback for `sp-implement`; if native delegation cannot proceed safely, stay on the leader path and record why."
        )
    else:
        sidecar_surface_hint = (
            "Escalate through the coordinated runtime surface when native delegation is unavailable, low-confidence, or unsuitable."
            if snapshot.sidecar_runtime_supported
            else "No coordinated runtime surface is currently available; use leader-local fallback only when delegation cannot proceed safely."
        )

    return DelegationSurfaceDescriptor(
        integration_key=snapshot.integration_key,
        command_name=command_name,
        intent=intent,
        native_surface=snapshot.native_worker_surface,
        native_dispatch_hint=native_dispatch_hint,
        native_join_hint=native_join_hint,
        sidecar_surface_hint=sidecar_surface_hint,
        result_contract_hint=result_contract_hint,
        result_handoff_hint=describe_result_handoff_template(
            command_name=command_name,
            integration_key=snapshot.integration_key,
        ),
        structured_results_expected=structured_results_expected,
    )
