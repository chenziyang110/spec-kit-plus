"""Worker bootstrap instruction generation for Codex team workers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from specify_cli.codex_team.tmux_backend import WorkerPaneSpec


@dataclass(slots=True, frozen=True)
class WorkerBootstrapPayload:
    instructions: str
    role_overlay: dict[str, str]
    metadata: dict[str, str]


def build_worker_bootstrap_payload(
    pane_spec: WorkerPaneSpec,
    *,
    role: str,
    instructions_prefix: str | None = None,
    additional_metadata: Mapping[str, str] | None = None,
) -> WorkerBootstrapPayload:
    overlay = {
        "role": role,
        "session_id": pane_spec.session,
        "worker_id": pane_spec.worker_id,
        "worktree_path": pane_spec.worktree,
    }

    metadata: dict[str, str] = {
        "backend": pane_spec.backend or "",
        "binary": pane_spec.binary or "",
        "pane_title": pane_spec.pane_title,
        "launch_command": pane_spec.launch_command,
    }
    if additional_metadata:
        metadata.update(additional_metadata)

    env_lines = "\n".join(
        f"  {key}={value}" for key, value in sorted(pane_spec.env.items())
    ) or "  (none)"

    prefix = instructions_prefix or "Worker bootstrap instructions:"
    instructions_parts = [
        prefix,
        f"role: {role}",
        f"session: {pane_spec.session}",
        f"worker_id: {pane_spec.worker_id}",
        f"worktree: {pane_spec.worktree}",
        f"launch_command: {pane_spec.launch_command}",
        "env:",
        env_lines,
    ]
    if additional_metadata:
        packet_summary = additional_metadata.get("packet_summary", "")
        required_refs = additional_metadata.get("required_references", "")
        forbidden_drift = additional_metadata.get("forbidden_drift", "")
        validation_gates = additional_metadata.get("validation_gates", "")
        instructions_parts.extend(
            [
                f"packet_summary: {packet_summary}",
                f"required_references: {required_refs}",
                f"forbidden_drift: {forbidden_drift}",
                f"validation_gates: {validation_gates}",
                "hard rule: do not execute from raw task text alone",
            ]
        )
    instructions = "\n".join(instructions_parts)

    return WorkerBootstrapPayload(
        instructions=instructions,
        role_overlay=overlay,
        metadata=metadata,
    )


__all__ = ["WorkerBootstrapPayload", "build_worker_bootstrap_payload"]
