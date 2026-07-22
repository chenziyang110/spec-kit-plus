"""Thin Python adapter for the unified Go workflow runtime.

``specify-runtime workflow`` is the sole reader, writer, validator, and CAS
owner of ``workflow.json``.  This module preserves Python call signatures and
typed exceptions for internal callers without parsing or mutating phase state.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
import json
from pathlib import Path
import tempfile
from typing import Any

from .agent_api import envelope
from .specify_runtime import SpecifyRuntimeError, run_specify_runtime


TERMINAL_ACCEPTANCE_SNAPSHOT_FILENAME = ".human-acceptance-terminal.json"
WORKFLOW_STAGES = (
    "discussion",
    "specify",
    "plan",
    "tasks",
    "implement",
    "review",
    "accept",
)


def terminal_acceptance_snapshot_path(feature_dir: Path | str) -> Path:
    """Return the immutable acceptance evidence consumed by Go closeout."""

    return Path(feature_dir) / TERMINAL_ACCEPTANCE_SNAPSHOT_FILENAME


def workflow_runtime_path(feature_dir: Path | str) -> Path:
    """Return Go's compact phase-state path without reading or writing it."""

    return Path(feature_dir) / "workflow.json"


def workflow_state_path(feature_dir: Path | str) -> Path:
    """Return the rich workflow evidence path without reading or writing it."""

    return Path(feature_dir) / "workflow-state.md"


def _resume_argv(blocker: Mapping[str, Any]) -> list[str]:
    resume = blocker.get("resume")
    if not isinstance(resume, Mapping):
        return []
    argv = resume.get("argv")
    if not isinstance(argv, list) or not all(isinstance(item, str) for item in argv):
        return []
    return list(argv)


class WorkflowRuntimeError(ValueError):
    """Typed Python view of one rejected unified-runtime operation."""

    def __init__(
        self,
        message: str,
        *,
        code: str,
        data: Mapping[str, Any] | None = None,
        blocker: Mapping[str, Any] | None = None,
        status: str = "blocked",
        payload: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.data = dict(data or {})
        self.blocker = dict(blocker or {})
        self.status = status
        self._payload = deepcopy(dict(payload)) if payload is not None else None

    def to_envelope(self) -> dict[str, Any]:
        if self._payload is not None:
            return deepcopy(self._payload)
        blocker = {**self.blocker, "code": self.code} if self.blocker else {}
        return envelope(
            self.status,
            str(self),
            data={"error_code": self.code, **self.data},
            blockers=[blocker] if blocker else [],
            next_argv=_resume_argv(blocker),
        )


class RevisionConflict(WorkflowRuntimeError):
    """Raised when the Go runtime rejects an optimistic revision guard."""


class InvalidTransition(WorkflowRuntimeError):
    """Raised when the Go runtime rejects a phase transition or mutation."""


class MissingWorkflowState(WorkflowRuntimeError):
    """Raised when a workflow operation targets a feature without phase state."""


def _project_context(feature_dir: Path | str) -> tuple[Path, Path]:
    feature = Path(feature_dir).expanduser().resolve(strict=False)
    features_dir = feature.parent
    if features_dir.name == "features" and features_dir.parent.name == ".specify":
        return features_dir.parent.parent, feature
    raise ValueError(
        "feature_dir must be one direct child of a project's .specify/features directory"
    )


def _runtime_error(
    payload: Mapping[str, Any],
) -> WorkflowRuntimeError:
    data = payload.get("data")
    normalized_data = dict(data) if isinstance(data, Mapping) else {}
    blockers = payload.get("blockers")
    first_blocker = (
        dict(blockers[0])
        if isinstance(blockers, list) and blockers and isinstance(blockers[0], Mapping)
        else {}
    )
    code = str(
        normalized_data.get("error_code")
        or first_blocker.get("code")
        or "workflow-runtime-rejected"
    )
    message = str(payload.get("summary") or "workflow runtime rejected the operation")
    status = str(payload.get("status") or "blocked")
    lowered = code.casefold()
    error_type: type[WorkflowRuntimeError]
    if code == "missing-workflow-state" or "missing-workflow" in lowered:
        error_type = MissingWorkflowState
    elif code == "revision-conflict" or (
        "revision" in lowered and ("conflict" in lowered or "stale" in lowered)
    ):
        error_type = RevisionConflict
    elif any(
        marker in lowered
        for marker in (
            "transition",
            "reopen",
            "closeout",
            "source-stage",
            "terminal-workflow",
            "blocker-already",
            "no-blocker",
            "workflow-already-completed",
        )
    ):
        error_type = InvalidTransition
    else:
        error_type = WorkflowRuntimeError
    return error_type(
        message,
        code=code,
        data=normalized_data,
        blocker=first_blocker,
        status=status,
        payload=payload,
    )


def _validated_envelope(payload: object) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise WorkflowRuntimeError(
            "specify-runtime workflow returned a non-object response",
            code="invalid-workflow-runtime-response",
            status="error",
        )
    required_types = {
        "status": str,
        "summary": str,
        "data": dict,
        "items": list,
        "blockers": list,
        "show_argv": list,
        "next_argv": list,
    }
    invalid = [
        key
        for key, expected_type in required_types.items()
        if not isinstance(payload.get(key), expected_type)
    ]
    if invalid:
        raise WorkflowRuntimeError(
            "specify-runtime workflow returned an invalid envelope",
            code="invalid-workflow-runtime-response",
            data={"invalid_fields": invalid},
            status="error",
        )
    return payload


def _persisted_blocked_state(payload: Mapping[str, Any]) -> bool:
    data = payload.get("data")
    return (
        isinstance(data, Mapping)
        and data.get("status") == "blocked"
        and isinstance(data.get("revision"), int)
        and isinstance(data.get("stage"), str)
        and bool(data.get("stage"))
    )


def _invoke_workflow(
    feature_dir: Path | str,
    subcommand: str,
    args: Sequence[str] = (),
    *,
    allow_persisted_blocked: bool = False,
) -> dict[str, Any]:
    project_root, feature = _project_context(feature_dir)
    try:
        raw = run_specify_runtime(
            [
                "workflow",
                subcommand,
                "--feature-dir",
                str(feature),
                *[str(item) for item in args],
                "--project-root",
                str(project_root),
                "--format",
                "json",
            ],
            cwd=project_root,
            check=False,
            install_if_missing=True,
        )
    except SpecifyRuntimeError as exc:
        raise WorkflowRuntimeError(
            str(exc),
            code="workflow-runtime-unavailable",
            data={"operation": subcommand},
            status="error",
        ) from exc
    payload = _validated_envelope(raw)
    status = payload["status"]
    if status in {"ok", "warn", "repaired"}:
        return payload
    if (
        status == "blocked"
        and allow_persisted_blocked
        and _persisted_blocked_state(payload)
    ):
        return payload
    raise _runtime_error(payload)


def _optional_flag(args: list[str], name: str, value: object) -> None:
    normalized = str(value or "").strip()
    if normalized:
        args.extend([name, normalized])


def _repeated_flag(args: list[str], name: str, values: Sequence[object]) -> None:
    for value in values:
        normalized = str(value or "").strip()
        if normalized:
            args.extend([name, normalized])


def show_workflow(feature_dir: Path | str) -> dict[str, Any]:
    """Read workflow state through ``specify-runtime workflow show``."""

    return _invoke_workflow(feature_dir, "show", allow_persisted_blocked=True)


def enter_workflow(
    feature_dir: Path | str,
    *,
    stage: str = "specify",
    expected_revision: int = 0,
    summary: str = "",
) -> dict[str, Any]:
    args = [
        "--command",
        str(stage),
        "--expected-revision",
        str(expected_revision),
    ]
    _optional_flag(args, "--summary", summary)
    return _invoke_workflow(feature_dir, "enter", args)


def next_workflow(feature_dir: Path | str) -> dict[str, Any]:
    """Resolve the next action through the unified runtime without mutation."""

    return _invoke_workflow(feature_dir, "next", allow_persisted_blocked=True)


def complete_workflow_stage(
    feature_dir: Path | str,
    *,
    expected_revision: int,
    summary: str = "",
) -> dict[str, Any]:
    args = ["--expected-revision", str(expected_revision)]
    _optional_flag(args, "--summary", summary)
    return _invoke_workflow(feature_dir, "complete-stage", args)


def transition_workflow(
    feature_dir: Path | str,
    *,
    target_stage: str,
    expected_revision: int,
    summary: str = "",
) -> dict[str, Any]:
    args = [
        "--to",
        str(target_stage),
        "--expected-revision",
        str(expected_revision),
    ]
    _optional_flag(args, "--summary", summary)
    return _invoke_workflow(feature_dir, "transition", args)


def reopen_workflow(
    feature_dir: Path | str,
    *,
    target_stage: str,
    expected_revision: int,
    reason: str,
    evidence: Sequence[object],
    invalidated_artifacts: Sequence[object],
) -> dict[str, Any]:
    args = [
        "--to",
        str(target_stage),
        "--expected-revision",
        str(expected_revision),
    ]
    _optional_flag(args, "--reason", reason)
    _repeated_flag(args, "--evidence", evidence)
    _repeated_flag(args, "--invalidated-artifacts", invalidated_artifacts)
    return _invoke_workflow(feature_dir, "reopen", args)


def reopen_acceptance_workflow(
    feature_dir: Path | str,
    *,
    target_stage: str,
    repair_route: str,
    finding_id: str,
    expected_revision: int,
    evidence: Sequence[object],
    summary: str = "",
) -> dict[str, Any]:
    """Delegate acceptance repair phase mutation to Go's guarded reopen route."""

    args = [
        "--to",
        str(target_stage),
        "--expected-revision",
        str(expected_revision),
        "--repair-route",
        str(repair_route),
        "--finding-id",
        str(finding_id),
    ]
    _repeated_flag(args, "--evidence", evidence)
    _optional_flag(args, "--summary", summary)
    return _invoke_workflow(feature_dir, "reopen", args)


def block_workflow(
    feature_dir: Path | str,
    *,
    expected_revision: int,
    category: str,
    owner: str,
    cause: str,
    evidence: Sequence[object],
    attempted_recovery: Sequence[Mapping[str, object]],
    affected_scope: Sequence[object],
    exact_next_action: str,
    unblock_criteria: str,
    human_action: Mapping[str, Any] | None = None,
    human_action_required: bool | None = None,
) -> dict[str, Any]:
    project_root, feature = _project_context(feature_dir)
    payload: dict[str, Any] = {
        "feature_dir": feature.relative_to(project_root).as_posix(),
        "expected_revision": expected_revision,
        "category": category,
        "owner": owner,
        "cause": cause,
        "evidence": list(evidence),
        "attempted_recovery": [dict(item) for item in attempted_recovery],
        "affected_scope": list(affected_scope),
        "exact_next_action": exact_next_action,
        "unblock_criteria": unblock_criteria,
    }
    if human_action is not None:
        payload["human_action"] = dict(human_action)
    if human_action_required is not None:
        payload["human_action_required"] = human_action_required

    temp_dir = project_root / ".specify"
    temp_dir.mkdir(parents=True, exist_ok=True)
    input_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            prefix=".workflow-block-",
            suffix=".json",
            dir=temp_dir,
            delete=False,
        ) as handle:
            json.dump(payload, handle, ensure_ascii=False, separators=(",", ":"))
            handle.write("\n")
            input_path = Path(handle.name)
        return _invoke_workflow(
            feature,
            "block",
            ("--input", str(input_path)),
            allow_persisted_blocked=True,
        )
    finally:
        if input_path is not None:
            input_path.unlink(missing_ok=True)


def resolve_workflow_blocker(
    feature_dir: Path | str,
    *,
    expected_revision: int,
    resolution_evidence: Sequence[object],
    summary: str = "",
) -> dict[str, Any]:
    args = ["--expected-revision", str(expected_revision)]
    _repeated_flag(args, "--resolution-evidence", resolution_evidence)
    _optional_flag(args, "--summary", summary)
    return _invoke_workflow(feature_dir, "resolve", args)


def closeout_workflow(
    feature_dir: Path | str,
    *,
    expected_revision: int,
    summary: str = "",
) -> dict[str, Any]:
    args = ["--expected-revision", str(expected_revision)]
    _optional_flag(args, "--summary", summary)
    return _invoke_workflow(feature_dir, "closeout", args)


__all__ = [
    "InvalidTransition",
    "MissingWorkflowState",
    "RevisionConflict",
    "TERMINAL_ACCEPTANCE_SNAPSHOT_FILENAME",
    "WORKFLOW_STAGES",
    "WorkflowRuntimeError",
    "block_workflow",
    "closeout_workflow",
    "complete_workflow_stage",
    "enter_workflow",
    "next_workflow",
    "reopen_acceptance_workflow",
    "reopen_workflow",
    "resolve_workflow_blocker",
    "show_workflow",
    "terminal_acceptance_snapshot_path",
    "transition_workflow",
    "workflow_runtime_path",
    "workflow_state_path",
]
