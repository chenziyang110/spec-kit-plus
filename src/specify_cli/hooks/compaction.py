"""Structured workflow compaction artifacts for resumable recovery."""

from __future__ import annotations

import json
from hashlib import sha1
from pathlib import Path
from typing import Any

from .checkpoint import checkpoint_hook
from .checkpoint_serializers import normalize_command_name
from .events import WORKFLOW_COMPACTION_BUILD, WORKFLOW_COMPACTION_READ
from .learning import _recent_signal_for_command
from .types import HookResult


def build_compaction_hook(project_root: Path, payload: dict[str, object]) -> HookResult:
    command_name = normalize_command_name(str(payload.get("command_name") or ""))
    trigger = str(payload.get("trigger") or "manual").strip().lower() or "manual"

    checkpoint_result = checkpoint_hook(project_root, payload)
    if checkpoint_result.status == "blocked":
        return HookResult(
            event=WORKFLOW_COMPACTION_BUILD,
            status="repairable-block",
            severity="warning",
            errors=list(checkpoint_result.errors),
            actions=[
                *checkpoint_result.errors,
                "recreate the resumable workflow source of truth before building compaction output",
            ],
            data={"checkpoint_result": checkpoint_result.to_dict()},
        )

    checkpoint = dict(checkpoint_result.data.get("checkpoint") or {})
    scope_key = _scope_key(command_name, checkpoint, payload)
    artifact_dir = project_root / ".specify" / "runtime" / "compaction" / scope_key
    artifact_dir.mkdir(parents=True, exist_ok=True)

    truth_sources = _truth_sources(project_root, checkpoint, payload)
    recent_signal = _recent_signal_for_command(project_root, command_name=command_name)
    artifact = {
        "identity": {
            "command_name": command_name,
            "scope_key": scope_key,
            "trigger": trigger,
        },
        "truth_sources": truth_sources,
        "phase_state": _phase_state(checkpoint),
        "artifact_digest": _artifact_digest(checkpoint),
        "execution_signal": _execution_signal(checkpoint, recent_signal),
        "resume_cue": _resume_cue(command_name, checkpoint),
    }

    json_path = artifact_dir / "latest.json"
    markdown_path = artifact_dir / "latest.md"
    json_path.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    markdown_path.write_text(_artifact_markdown(artifact), encoding="utf-8")

    return HookResult(
        event=WORKFLOW_COMPACTION_BUILD,
        status="ok",
        severity="info",
        writes={
            "compaction_json": str(json_path.relative_to(project_root)),
            "compaction_markdown": str(markdown_path.relative_to(project_root)),
        },
        data={
            "artifact_path": str(json_path),
            "markdown_path": str(markdown_path),
            "scope_key": scope_key,
            "artifact": artifact,
        },
    )


def read_compaction_hook(project_root: Path, payload: dict[str, object]) -> HookResult:
    command_name = normalize_command_name(str(payload.get("command_name") or ""))
    scope_key = _scope_key(command_name, dict(payload.get("checkpoint") or {}), payload)
    json_path = project_root / ".specify" / "runtime" / "compaction" / scope_key / "latest.json"
    if not json_path.exists():
        return HookResult(
            event=WORKFLOW_COMPACTION_READ,
            status="warn",
            severity="warning",
            warnings=[f"no compaction artifact exists yet at {json_path}"],
            data={"artifact_path": str(json_path), "exists": False},
        )
    artifact = json.loads(json_path.read_text(encoding="utf-8"))
    return HookResult(
        event=WORKFLOW_COMPACTION_READ,
        status="ok",
        severity="info",
        data={"artifact_path": str(json_path), "exists": True, "artifact": artifact},
    )


def _scope_key(command_name: str, checkpoint: dict[str, Any], payload: dict[str, object]) -> str:
    if command_name == "quick":
        workspace = str(payload.get("workspace") or checkpoint.get("path") or "").strip()
        if workspace:
            return f"quick-{Path(workspace).name}"
    if command_name == "debug":
        session_file = str(payload.get("session_file") or checkpoint.get("path") or "").strip()
        if session_file:
            return f"debug-{Path(session_file).stem}"
    feature_dir = str(payload.get("feature_dir") or "").strip()
    if feature_dir:
        return f"{command_name}-{Path(feature_dir).name}"
    checkpoint_path = str(checkpoint.get("path") or "").strip()
    if checkpoint_path:
        return f"{command_name}-{Path(checkpoint_path).parent.name}"
    fingerprint = sha1(command_name.encode("utf-8")).hexdigest()[:8]
    return f"{command_name}-{fingerprint}"


def _truth_sources(project_root: Path, checkpoint: dict[str, Any], payload: dict[str, object]) -> list[dict[str, Any]]:
    candidates = [
        str(payload.get("feature_dir") or "").strip(),
        str(payload.get("workspace") or "").strip(),
        str(payload.get("session_file") or "").strip(),
        str(checkpoint.get("path") or "").strip(),
    ]
    seen: set[str] = set()
    sources: list[dict[str, Any]] = []
    for raw in candidates:
        if not raw:
            continue
        path = Path(raw)
        if not path.is_absolute():
            path = (project_root / path).resolve()
        key = str(path)
        if key in seen:
            continue
        seen.add(key)
        exists = path.exists()
        sources.append(
            {
                "path": key,
                "exists": exists,
                "mtime_ms": (path.stat().st_mtime_ns / 1_000_000) if exists else None,
            }
        )
    return sources


def _phase_state(checkpoint: dict[str, Any]) -> dict[str, Any]:
    return {
        "state_kind": checkpoint.get("state_kind", ""),
        "status": checkpoint.get("status", ""),
        "active_command": checkpoint.get("active_command", ""),
        "phase_mode": checkpoint.get("phase_mode", ""),
        "next_command": checkpoint.get("next_command", ""),
        "next_action": checkpoint.get("next_action", ""),
        "resume_decision": checkpoint.get("resume_decision", ""),
        "blocked_reason": checkpoint.get("blocked_reason", ""),
    }


def _artifact_digest(checkpoint: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "authoritative_files",
        "exit_criteria",
        "current_batch",
        "goal",
        "active_lane",
        "observer_summary",
        "lane_id",
        "lane_recovery_state",
    )
    return {key: checkpoint[key] for key in keys if key in checkpoint and checkpoint[key]}


def _execution_signal(checkpoint: dict[str, Any], recent_signal: dict[str, object] | None) -> dict[str, Any]:
    signal = {
        "retry_attempts": checkpoint.get("retry_attempts", ""),
    }
    if recent_signal:
        signal["pain_score"] = recent_signal.get("pain_score")
        signal["factors"] = recent_signal.get("factors", {})
        signal["false_starts"] = recent_signal.get("false_starts", [])
        signal["hidden_dependencies"] = recent_signal.get("hidden_dependencies", [])
    return signal


def _resume_cue(command_name: str, checkpoint: dict[str, Any]) -> list[str]:
    cues = [f"You are resuming `{command_name}`."]
    next_action = str(checkpoint.get("next_action") or "").strip()
    if next_action:
        cues.append(f"Next action: {next_action}.")
    next_command = str(checkpoint.get("next_command") or "").strip()
    if next_command:
        cues.append(f"Next command: {next_command}.")
    checkpoint_path = str(checkpoint.get("path") or "").strip()
    if checkpoint_path:
        cues.append(f"Re-read {checkpoint_path} before changing course.")
    return cues


def _artifact_markdown(artifact: dict[str, Any]) -> str:
    identity = artifact["identity"]
    phase_state = artifact["phase_state"]
    resume_cue = artifact["resume_cue"]
    truth_sources = artifact["truth_sources"]
    lines = [
        "# Workflow Compaction",
        "",
        f"- command_name: `{identity['command_name']}`",
        f"- scope_key: `{identity['scope_key']}`",
        f"- trigger: `{identity['trigger']}`",
        "",
        "## Phase State",
        "",
        f"- status: `{phase_state.get('status', '')}`",
        f"- next_action: `{phase_state.get('next_action', '')}`",
        f"- next_command: `{phase_state.get('next_command', '')}`",
        "",
        "## Truth Sources",
        "",
    ]
    for source in truth_sources:
        lines.append(f"- `{source['path']}`")
    lines.extend(["", "## Resume Cue", ""])
    for cue in resume_cue:
        lines.append(f"- {cue}")
    lines.append("")
    return "\n".join(lines)
