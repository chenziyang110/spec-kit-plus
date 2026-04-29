"""Adapter protocol for per-integration multi-agent capability detection."""

from __future__ import annotations

import os
from typing import Protocol, runtime_checkable

from .backends.detect import detect_available_backends
from .models import CapabilitySnapshot

FIRST_RELEASE_WORKFLOW_COMMANDS = frozenset(
    {
        "specify",
        "clarify",
        "explain",
        "debug",
        "deep-research",
        "research",
        "plan",
        "tasks",
        "test",
        "test-scan",
        "test-build",
        "implement",
        "analyze",
        "constitution",
        "checklist",
        "map-codebase",
        "taskstoissues",
    }
)
COMMAND_ALIASES = {
    "research": "deep-research",
}

_MODEL_ENV_KEYS: dict[str, tuple[str, ...]] = {
    "claude": ("CLAUDE_CODE_SUBAGENT_MODEL", "ANTHROPIC_MODEL"),
    "codex": ("OPENAI_MODEL", "CODEX_MODEL"),
    "gemini": ("GEMINI_MODEL",),
    "copilot": ("COPILOT_MODEL", "GITHUB_COPILOT_MODEL"),
}
_LOW_CONFIDENCE_MODEL_MARKERS = ("mini", "haiku", "flash", "nano")
_HIGH_CONFIDENCE_MODEL_MARKERS = ("opus", "sonnet", "gpt-5", "gpt-4", "o3", "o4", "pro")


def normalize_command_name(command_name: str) -> str:
    """Normalize workflow command names for adapter support checks."""
    normalized = command_name.strip().lower()
    while normalized.startswith("/"):
        normalized = normalized[1:]
    if normalized.startswith("sp-"):
        normalized = normalized[3:]
    elif normalized.startswith("sp."):
        normalized = normalized[3:]
    return COMMAND_ALIASES.get(normalized, normalized)


def supports_workflow_command(
    command_name: str,
    supported_commands: frozenset[str] = FIRST_RELEASE_WORKFLOW_COMMANDS,
) -> bool:
    """Return ``True`` when a normalized command is in the allowed set."""
    return normalize_command_name(command_name) in supported_commands


def _read_model_hint(integration_key: str) -> str | None:
    env_keys = list(_MODEL_ENV_KEYS.get(integration_key, ()))
    env_keys.extend(("SPECIFY_MODEL", "MODEL"))
    for key in env_keys:
        value = os.environ.get(key, "").strip()
        if value:
            return value
    return None


def _infer_delegation_confidence(
    *,
    native_worker_surface: str,
    model_hint: str | None,
    default_confidence: str,
) -> str:
    if native_worker_surface in {"none", "unknown"}:
        return "low"
    if not model_hint:
        return default_confidence

    lowered = model_hint.lower()
    if any(marker in lowered for marker in _LOW_CONFIDENCE_MODEL_MARKERS):
        return "low"
    if any(marker in lowered for marker in _HIGH_CONFIDENCE_MODEL_MARKERS):
        return "high" if default_confidence == "high" else "medium"
    return default_confidence


def build_capability_snapshot(
    *,
    integration_key: str,
    native_multi_agent: bool,
    sidecar_runtime_supported: bool,
    structured_results: bool,
    durable_coordination: bool,
    native_worker_surface: str,
    delegation_confidence: str,
    model_family: str | None = None,
    notes: list[str] | None = None,
) -> CapabilitySnapshot:
    """Build a capability snapshot with lightweight runtime/model probing."""

    resolved_notes = list(notes or [])
    runtime_probe_succeeded = False

    try:
        backends = detect_available_backends()
        available_backends = sorted(name for name, descriptor in backends.items() if descriptor.available)
        runtime_probe_succeeded = True
        if available_backends:
            resolved_notes.append(
                f"Runtime probe backends available: {', '.join(available_backends)}."
            )
        elif sidecar_runtime_supported:
            sidecar_runtime_supported = False
            resolved_notes.append(
                "Runtime probe found no available orchestration backends; disabling sidecar runtime support for this session."
            )
    except Exception as exc:  # pragma: no cover - defensive path
        resolved_notes.append(f"Runtime probe failed: {exc}")

    probed_model = _read_model_hint(integration_key)
    resolved_model = probed_model or model_family
    if probed_model:
        resolved_notes.append(f"Model probe selected: {probed_model}.")

    resolved_confidence = _infer_delegation_confidence(
        native_worker_surface=native_worker_surface,
        model_hint=resolved_model,
        default_confidence=delegation_confidence,
    )

    return CapabilitySnapshot(
        integration_key=integration_key,
        native_multi_agent=native_multi_agent,
        sidecar_runtime_supported=sidecar_runtime_supported,
        structured_results=structured_results,
        durable_coordination=durable_coordination,
        native_worker_surface=native_worker_surface,
        delegation_confidence=resolved_confidence,
        model_family=resolved_model,
        runtime_probe_succeeded=runtime_probe_succeeded,
        notes=resolved_notes,
    )


@runtime_checkable
class MultiAgentAdapter(Protocol):
    """Contract implemented by integration-specific multi-agent adapters."""

    def detect_capabilities(self) -> CapabilitySnapshot:
        """Return the current capability snapshot for this integration."""

    def supports_command(self, command_name: str) -> bool:
        """Return ``True`` when the command is supported by the adapter."""
