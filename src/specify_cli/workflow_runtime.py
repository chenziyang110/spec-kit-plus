"""Deterministic workflow state transitions for Classic and Advanced agents.

The runtime owns only the mandatory high-level phase order in the compact
``workflow-runtime.json`` file. Rich command resume/evidence state remains in
``workflow-state.md`` so transitions cannot erase Learning, analysis, research,
or profile-specific data. Runtime mutation uses optimistic revision guards and
atomic replacement.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import hashlib
import json
from pathlib import Path
import re
from typing import Any

from .agent_api import (
    WORKFLOW_BLOCKER_CATEGORIES,
    envelope,
    validate_workflow_blocker_payload,
)
from .atomic_io import (
    atomic_write_text,
    interprocess_lock,
    read_local_state_bytes,
    read_local_state_text,
)
from .launcher import render_command


WORKFLOW_STATE_SCHEMA_VERSION = 1
WORKFLOW_RUNTIME_SCHEMA_VERSION = WORKFLOW_STATE_SCHEMA_VERSION
TERMINAL_ACCEPTANCE_SNAPSHOT_FILENAME = ".human-acceptance-terminal.json"
WORKFLOW_STAGES = (
    "discussion",
    "specify",
    "plan",
    "tasks",
    "implement",
    "accept",
)
_ENTRY_STAGES = frozenset({"discussion", "specify"})
_NEXT_STAGE = {
    current: WORKFLOW_STAGES[index + 1]
    for index, current in enumerate(WORKFLOW_STAGES[:-1])
}
_STAGE_INDEX = {stage: index for index, stage in enumerate(WORKFLOW_STAGES)}
_BLOCKER_CATEGORIES = frozenset(WORKFLOW_BLOCKER_CATEGORIES)
_BLOCKER_OWNERS = frozenset({"agent", "user", "maintainer", "external-system"})
_HUMAN_ACTION_FIELDS = frozenset(
    {
        "goal",
        "why_human",
        "prerequisites",
        "safety_notes",
        "steps",
        "verification",
        "evidence_to_return",
        "resume_instruction",
    }
)
_HUMAN_ACTION_STEP_FIELDS = frozenset(
    {"order", "title", "action", "command", "expected_result", "if_failed"}
)


def workflow_state_path(feature_dir: Path | str) -> Path:
    """Return the rich workflow-owned resume and evidence state path."""

    return Path(feature_dir) / "workflow-state.md"


def workflow_runtime_path(feature_dir: Path | str) -> Path:
    """Return the compact CLI-owned phase-order state path for a feature."""

    return Path(feature_dir) / "workflow-runtime.json"


def terminal_acceptance_snapshot_path(feature_dir: Path | str) -> Path:
    """Return the immutable acceptance evidence bound to terminal runtime state."""

    return Path(feature_dir) / TERMINAL_ACCEPTANCE_SNAPSHOT_FILENAME


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-") or "workflow"


def _resume_command(argv: Sequence[str]) -> str:
    return render_command(tuple(str(item) for item in argv))


def _resume_record(argv: Sequence[str]) -> dict[str, Any]:
    normalized = [str(item) for item in argv]
    command = _resume_command(normalized)
    return {
        "instruction": f"Run the exact resume command: {command}",
        "command": command,
        "argv": normalized,
    }


def _blocker_resume_argv(blocker: Mapping[str, Any]) -> list[str]:
    resume = blocker.get("resume")
    if not isinstance(resume, Mapping):
        return []
    argv = resume.get("argv")
    if isinstance(argv, (str, bytes)) or not isinstance(argv, Sequence):
        return []
    return [str(item) for item in argv if str(item)]


def _novice_human_action(
    *,
    owner: str,
    evidence: list[str],
    exact_next_action: str,
    unblock_criteria: str,
    resume_argv: list[str],
) -> dict[str, Any]:
    return {
        "goal": exact_next_action,
        "why_human": (
            f"This boundary is owned by {owner}; the agent cannot safely exercise "
            "that authority or substitute its own decision."
        ),
        "prerequisites": [
            "Access to the exact repository, environment, artifact, or decision named in the evidence.",
            "The authority required for the requested action.",
            *evidence,
        ],
        "safety_notes": [
            "Do not paste tokens, passwords, cookies, private keys, or unredacted private logs into chat.",
            "Do not broaden the action to a different repository, branch, environment, job, or setting.",
            "Stop and return the ambiguity if the target cannot be matched exactly to the evidence.",
        ],
        "steps": [
            {
                "order": 1,
                "title": "Confirm the exact target",
                "action": (
                    "Read the blocker cause and evidence, then match the named repository, "
                    "environment, artifact, setting, or decision before changing anything."
                ),
                "expected_result": "Exactly one target matches the sanitized evidence.",
                "if_failed": "Make no change; return the conflicting target names or missing identifier.",
            },
            {
                "order": 2,
                "title": "Perform only the requested action",
                "action": exact_next_action,
                "expected_result": unblock_criteria,
                "if_failed": (
                    "Do not retry blindly or expand scope; record the visible terminal status "
                    "and the smallest sanitized error evidence."
                ),
            },
            {
                "order": 3,
                "title": "Verify independently",
                "action": (
                    "Refresh or rerun a read-only check against the same exact target and "
                    f"confirm: {unblock_criteria}"
                ),
                "expected_result": unblock_criteria,
                "if_failed": "Return the observed mismatch instead of claiming the blocker is resolved.",
            },
        ],
        "verification": [unblock_criteria],
        "evidence_to_return": [
            "The exact target identifier and terminal result.",
            "A sanitized URL, job ID, screenshot, or command output that independently proves the result.",
            "For failure only, the smallest relevant sanitized error excerpt.",
        ],
        "resume_instruction": f"Return the evidence, then run: {_resume_command(resume_argv)}",
    }


def _validate_human_action_guide(guide: Mapping[str, Any]) -> dict[str, Any]:
    unknown = sorted(set(guide) - _HUMAN_ACTION_FIELDS)
    if unknown:
        raise ValueError(f"human_action contains unknown field(s): {', '.join(unknown)}")
    normalized = dict(guide)
    for field in ("goal", "why_human", "resume_instruction"):
        normalized[field] = _required_text(normalized.get(field), f"human_action.{field}")
    for field in (
        "prerequisites",
        "safety_notes",
        "verification",
        "evidence_to_return",
    ):
        normalized[field] = _required_string_list(
            normalized.get(field), f"human_action.{field}"
        )
    raw_steps = normalized.get("steps")
    if isinstance(raw_steps, (str, bytes)) or not isinstance(raw_steps, Sequence):
        raise ValueError("human_action.steps must be a list")
    steps: list[dict[str, Any]] = []
    for index, raw_step in enumerate(raw_steps):
        if not isinstance(raw_step, Mapping):
            raise ValueError(f"human_action.steps[{index}] must be an object")
        unknown_step = sorted(set(raw_step) - _HUMAN_ACTION_STEP_FIELDS)
        if unknown_step:
            raise ValueError(
                f"human_action.steps[{index}] contains unknown field(s): "
                + ", ".join(unknown_step)
            )
        order = raw_step.get("order")
        if isinstance(order, bool) or not isinstance(order, int) or order < 1:
            raise ValueError(f"human_action.steps[{index}].order must be a positive integer")
        command = raw_step.get("command")
        if command is not None and not isinstance(command, str):
            raise ValueError(f"human_action.steps[{index}].command must be a string or null")
        steps.append(
            {
                "order": order,
                "title": _required_text(
                    raw_step.get("title"), f"human_action.steps[{index}].title"
                ),
                "action": _required_text(
                    raw_step.get("action"), f"human_action.steps[{index}].action"
                ),
                "command": command,
                "expected_result": _required_text(
                    raw_step.get("expected_result"),
                    f"human_action.steps[{index}].expected_result",
                ),
                "if_failed": _required_text(
                    raw_step.get("if_failed"),
                    f"human_action.steps[{index}].if_failed",
                ),
            }
        )
    if not steps:
        raise ValueError("human_action.steps must contain at least one step")
    normalized["steps"] = steps
    return normalized


def _runtime_blocker(
    *,
    stage: str,
    category: str,
    owner: str,
    cause: str,
    evidence: list[str],
    attempted_recovery: list[dict[str, str]],
    affected_scope: list[str],
    exact_next_action: str,
    unblock_criteria: str,
    resume_argv: list[str],
    human_action: Mapping[str, Any] | None = None,
    human_action_required: bool | None = None,
    blocker_id: str | None = None,
    resolution_action: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if human_action is not None and "resume_instruction" in human_action:
        raise ValueError(
            "human_action.resume_instruction is runtime-owned; omit it from input"
        )
    if human_action is not None and human_action_required is False:
        raise ValueError(
            "human_action cannot be supplied when human_action_required is false"
        )
    if owner in {"user", "maintainer"} and human_action_required is False:
        raise ValueError(
            f"human_action_required cannot be false for blocker owner {owner}"
        )
    human_required = (
        human_action_required
        if human_action_required is not None
        else owner in {"user", "maintainer"} or human_action is not None
    )
    guide: dict[str, Any] | None = None
    if human_required:
        guide = _novice_human_action(
            owner=owner,
            evidence=evidence,
            exact_next_action=exact_next_action,
            unblock_criteria=unblock_criteria,
            resume_argv=resume_argv,
        )
        if human_action is not None:
            guide.update(dict(human_action))
        if resolution_action is not None:
            guide["resume_instruction"] = (
                "Return sanitized evidence to the agent. The agent must apply the "
                "structured data.resolution_action returned by workflow show with "
                "that evidence; rerunning "
                "workflow show only refreshes state and does not resolve the blocker."
            )
        guide = _validate_human_action_guide(guide)
    payload = {
        "version": 1,
        "blocker_id": str(
            blocker_id or f"workflow-{_slug(stage)}-{_slug(category)}"
        ),
        "code": "workflow-blocked",
        "workflow": "sp|spx",
        "stage": stage,
        "category": category,
        "owner": owner,
        "summary": cause,
        "details": cause,
        "evidence": evidence,
        "attempted_recovery": attempted_recovery,
        "exact_next_action": exact_next_action,
        "unblock_criteria": unblock_criteria,
        "affected_scope": affected_scope,
        "can_continue": False,
        "human_action_required": human_required,
        "human_action_guide": guide,
        "resume": _resume_record(resume_argv),
    }
    return payload


class WorkflowRuntimeError(ValueError):
    """Base class for deterministic workflow failures exposed to CLI adapters."""

    def __init__(
        self,
        message: str,
        *,
        code: str,
        data: Mapping[str, Any] | None = None,
        blocker: Mapping[str, Any] | None = None,
        status: str = "blocked",
    ) -> None:
        super().__init__(message)
        self.code = code
        self.data = dict(data or {})
        self.blocker = dict(blocker or {})
        self.status = status

    def to_envelope(self) -> dict[str, Any]:
        blocker = {**self.blocker, "code": self.code} if self.blocker else {}
        data = {"error_code": self.code, **self.data}
        resolution_action = data.get("resolution_action")
        return envelope(
            self.status,
            str(self),
            data=data,
            blockers=[blocker] if blocker else [],
            next_argv=(
                []
                if isinstance(resolution_action, Mapping)
                else _blocker_resume_argv(blocker)
            ),
        )


class RevisionConflict(WorkflowRuntimeError):
    """Raised when an optimistic workflow revision guard fails."""


class InvalidTransition(WorkflowRuntimeError):
    """Raised when a command tries to skip or reverse a workflow stage."""


class MissingWorkflowState(WorkflowRuntimeError):
    """Raised when a read or mutation targets a workflow that was not entered."""


def _required_text(value: object, field: str) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        raise ValueError(f"{field} is required")
    return normalized


def _required_string_list(value: Sequence[object], field: str) -> list[str]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise ValueError(f"{field} must be a list")
    normalized = [str(item).strip() for item in value if str(item).strip()]
    if not normalized:
        raise ValueError(f"{field} must contain at least one value")
    return normalized


def _normalize_attempts(value: Sequence[Mapping[str, object]]) -> list[dict[str, str]]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise ValueError("attempted_recovery must be a list")
    attempts: list[dict[str, str]] = []
    for index, raw in enumerate(value):
        if not isinstance(raw, Mapping):
            raise ValueError(f"attempted_recovery[{index}] must be an object")
        attempts.append(
            {
                "action": _required_text(
                    raw.get("action"), f"attempted_recovery[{index}].action"
                ),
                "result": _required_text(
                    raw.get("result"), f"attempted_recovery[{index}].result"
                ),
            }
        )
    return attempts


def _is_terminal_state(stage: str, status: str) -> bool:
    return stage == "accept" and status == "completed"


def _transition_argv(feature_dir: Path, target_stage: str, revision: int) -> list[str]:
    return [
        "specify",
        "workflow",
        "transition",
        "--feature-dir",
        str(feature_dir),
        "--to",
        target_stage,
        "--expected-revision",
        str(revision),
        "--format",
        "json",
    ]


def _show_argv(feature_dir: Path) -> list[str]:
    return [
        "specify",
        "workflow",
        "show",
        "--feature-dir",
        str(feature_dir),
        "--format",
        "json",
    ]


def _next_argv(feature_dir: Path) -> list[str]:
    return [
        "specify",
        "workflow",
        "next",
        "--feature-dir",
        str(feature_dir),
        "--format",
        "json",
    ]


def _resolution_action(feature_dir: Path, revision: int) -> dict[str, Any]:
    return {
        "capability_id": "workflow.resolve",
        "base_argv": [
            "specify",
            "workflow",
            "resolve",
            "--feature-dir",
            str(feature_dir),
            "--expected-revision",
            str(revision),
            "--format",
            "json",
        ],
        "required_inputs": [
            {
                "field": "resolution_evidence",
                "flag": "--resolution-evidence",
                "repeatable": True,
                "min_items": 1,
                "source": "sanitized evidence satisfying unblock_criteria",
            }
        ],
    }


def _blocked_runtime_view(
    _feature_dir: Path,
    state: Mapping[str, Any],
) -> dict[str, Any]:
    return dict(state.get("blocker") or {})


def _closeout_argv(feature_dir: Path, revision: int) -> list[str]:
    return [
        "specify",
        "workflow",
        "closeout",
        "--feature-dir",
        str(feature_dir),
        "--expected-revision",
        str(revision),
        "--format",
        "json",
    ]


def _complete_stage_argv(
    feature_dir: Path,
    revision: int,
) -> list[str]:
    argv = [
        "specify",
        "workflow",
        "complete-stage",
        "--feature-dir",
        str(feature_dir),
        "--expected-revision",
        str(revision),
        "--format",
        "json",
    ]
    return argv


def _render_state(state: Mapping[str, Any]) -> str:
    payload = {
        "workflow_runtime_version": WORKFLOW_RUNTIME_SCHEMA_VERSION,
        "revision": int(state["revision"]),
        "stage": str(state["stage"]),
        "status": str(state["status"]),
        "summary": str(state.get("summary") or ""),
        "blocker": state.get("blocker"),
        "last_resolution_evidence": list(state.get("last_resolution_evidence") or []),
        "last_reopen": state.get("last_reopen"),
        "last_blocker_resolution": state.get("last_blocker_resolution"),
        "acceptance_sha256": state.get("acceptance_sha256"),
    }
    return json.dumps(
        payload,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    )


def _invalid_runtime_state(
    feature_dir: Path,
    *,
    cause: str,
    evidence: Sequence[str],
    attempted_recovery: Sequence[Mapping[str, object]] | None = None,
) -> WorkflowRuntimeError:
    path = workflow_runtime_path(feature_dir)
    resume_argv = _show_argv(feature_dir)
    blocker = _runtime_blocker(
        stage="phase-runtime",
        category="artifact-or-state",
        owner="maintainer",
        cause=cause,
        evidence=[str(item) for item in evidence],
        attempted_recovery=_normalize_attempts(list(attempted_recovery or [])),
        affected_scope=["required workflow phase order", str(path)],
        exact_next_action=(
            "Back up workflow-runtime.json, identify the last trusted required stage "
            "from validated artifacts, then restore a schema-valid runtime file or "
            "remove it and re-enter at specify. Do not edit workflow-state.md as a repair."
        ),
        unblock_criteria=(
            "specify workflow show returns exit 0 for this feature and reports the "
            "trusted stage, status, and revision."
        ),
        resume_argv=resume_argv,
    )
    return WorkflowRuntimeError(
        cause,
        code="invalid-workflow-runtime",
        data={"path": str(path)},
        blocker=blocker,
    )


def _terminal_acceptance_evidence_error(
    feature_dir: Path,
    *,
    acceptance_sha256: str,
    evidence: Sequence[str],
) -> WorkflowRuntimeError:
    snapshot_path = terminal_acceptance_snapshot_path(feature_dir)
    acceptance_path = feature_dir / "human-acceptance.json"
    resume_argv = _show_argv(feature_dir)
    cause = "terminal acceptance evidence drifted from its immutable snapshot"
    blocker = _runtime_blocker(
        stage="accept",
        category="conflict-or-drift",
        owner="maintainer",
        cause=cause,
        evidence=[str(item) for item in evidence],
        attempted_recovery=[
            {
                "action": "Compared terminal acceptance evidence digests",
                "result": "The current artifact or immutable snapshot is missing or mismatched.",
            }
        ],
        affected_scope=[
            str(acceptance_path),
            str(snapshot_path),
            str(workflow_runtime_path(feature_dir)),
        ],
        exact_next_action=(
            "Do not edit the terminal snapshot or workflow-runtime.json. Back up the "
            "current human-acceptance.json. Verify the snapshot digest equals the "
            "recorded acceptance_sha256; if it does, restore human-acceptance.json "
            "byte-for-byte from that snapshot. If the snapshot is missing or its "
            "digest differs, preserve all files and escalate instead of re-entering "
            "or rewriting the completed workflow."
        ),
        unblock_criteria=(
            "The immutable snapshot and current human-acceptance.json both have digest "
            f"{acceptance_sha256}, and workflow show reports completed accept."
        ),
        resume_argv=resume_argv,
    )
    return WorkflowRuntimeError(
        cause,
        code="terminal-acceptance-evidence-drift",
        data={
            "acceptance_sha256": acceptance_sha256,
            "acceptance_path": str(acceptance_path),
            "acceptance_snapshot_path": str(snapshot_path),
        },
        blocker=blocker,
    )


def _acceptance_evidence_digest(
    path: Path,
    *,
    label: str,
) -> tuple[str, str | None]:
    """Read one acceptance artifact without leaking filesystem races."""

    try:
        content = read_local_state_bytes(path, root=path.parent)
    except ValueError:
        return (
            "unsafe-link",
            f"{label} uses a symlink, junction, or unsafe local-state path: {path}",
        )
    except FileNotFoundError:
        return (
            "missing",
            f"{label} is missing or was replaced during read: {path}",
        )
    except OSError as exc:
        return (
            "unreadable",
            f"{label} is unreadable: {path} ({type(exc).__name__})",
        )
    return hashlib.sha256(content).hexdigest(), None


def _actual_revision(feature_dir: Path) -> int:
    path = workflow_runtime_path(feature_dir)
    if not path.is_file():
        return 0
    try:
        payload = json.loads(read_local_state_text(path, root=feature_dir))
        if not isinstance(payload, dict):
            raise ValueError("top-level value is not an object")
        revision = payload.get("revision")
        if isinstance(revision, bool) or not isinstance(revision, int) or revision < 1:
            raise ValueError("revision is not a positive integer")
        return int(revision)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise _invalid_runtime_state(
            feature_dir,
            cause=f"workflow runtime at {path} has no valid revision",
            evidence=[
                f"read-only parse failed: {type(exc).__name__}: {exc}"
            ],
            attempted_recovery=[
                {"action": "Read and parse workflow-runtime.json", "result": "The runtime state is invalid."}
            ],
        ) from exc


def _revision_conflict(
    feature_dir: Path, *, expected_revision: int, actual_revision: int
) -> RevisionConflict:
    resume_argv = _show_argv(feature_dir)
    blocker = _runtime_blocker(
        stage="revision-guard",
        category="conflict-or-drift",
        owner="agent",
        cause=f"expected revision {expected_revision}, found {actual_revision}",
        evidence=[f"workflow-runtime.json current revision is {actual_revision}"],
        attempted_recovery=[],
        affected_scope=["workflow-runtime.json"],
        exact_next_action="Read the current workflow state and recompute the intended mutation.",
        unblock_criteria="The next mutation names the current revision and preserves newer state.",
        resume_argv=resume_argv,
    )
    return RevisionConflict(
        f"expected revision {expected_revision}, found {actual_revision}",
        code="revision-conflict",
        data={
            "expected_revision": expected_revision,
            "actual_revision": actual_revision,
            "path": str(workflow_runtime_path(feature_dir)),
        },
        blocker=blocker,
    )


def _atomic_guarded_write(
    feature_dir: Path,
    state: Mapping[str, Any],
    *,
    expected_revision: int,
) -> dict[str, Any]:
    path = workflow_runtime_path(feature_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.parent / ".workflow-state.lock"
    with interprocess_lock(lock_path):
        actual_revision = _actual_revision(feature_dir)
        if actual_revision != expected_revision:
            raise _revision_conflict(
                feature_dir,
                expected_revision=expected_revision,
                actual_revision=actual_revision,
            )
        atomic_write_text(path, _render_state(state) + "\n")
        committed = _read_state(feature_dir)
    return committed


def _read_state(feature_dir: Path) -> dict[str, Any]:
    path = workflow_runtime_path(feature_dir)
    if not path.is_file():
        enter_argv = [
            "specify",
            "workflow",
            "enter",
            "--feature-dir",
            str(feature_dir),
            "--expected-revision",
            "0",
            "--format",
            "json",
        ]
        blocker = _runtime_blocker(
            stage="workflow-entry",
            category="artifact-or-state",
            owner="agent",
            cause=f"workflow-runtime.json is missing at {path}",
            evidence=[str(path)],
            attempted_recovery=[],
            affected_scope=["workflow entry", "workflow-runtime.json"],
            exact_next_action="Enter the workflow at specify, or at optional discussion.",
            unblock_criteria="workflow-runtime.json exists at revision 1.",
            resume_argv=enter_argv,
        )
        raise MissingWorkflowState(
            f"workflow-runtime.json is missing at {path}",
            code="missing-workflow-state",
            data={"path": str(path)},
            blocker=blocker,
        )

    try:
        payload = json.loads(read_local_state_text(path, root=feature_dir))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise _invalid_runtime_state(
            feature_dir,
            cause=f"workflow runtime at {path} is unreadable or invalid JSON",
            evidence=[
                f"read-only parse failed: {type(exc).__name__}: {exc}"
            ],
            attempted_recovery=[
                {"action": "Read and parse workflow-runtime.json", "result": "The runtime state is invalid."}
            ],
        ) from exc
    if not isinstance(payload, dict):
        raise _invalid_runtime_state(
            feature_dir,
            cause="workflow runtime must be a JSON object",
            evidence=["workflow-runtime.json top-level value is not an object"],
        )
    version = payload.get("workflow_runtime_version")
    revision = payload.get("revision")
    stage = str(payload.get("stage") or "").strip().lower()
    status = str(payload.get("status") or "").strip().lower()
    errors: list[str] = []
    if version != WORKFLOW_RUNTIME_SCHEMA_VERSION:
        errors.append(
            f"workflow_runtime_version must equal {WORKFLOW_RUNTIME_SCHEMA_VERSION}"
        )
    if isinstance(revision, bool) or not isinstance(revision, int) or revision < 1:
        errors.append("revision must be a positive integer")
    if stage not in WORKFLOW_STAGES:
        errors.append(f"unsupported stage '{stage or 'missing'}'")
    if status not in {"active", "blocked", "completed"}:
        errors.append(f"unsupported status '{status or 'missing'}'")
    summary = payload.get("summary")
    if not isinstance(summary, str):
        errors.append("summary must be a string")
    resolution_evidence = payload.get("last_resolution_evidence")
    if not isinstance(resolution_evidence, list) or any(
        not isinstance(item, str) for item in resolution_evidence
    ):
        errors.append("last_resolution_evidence must be an array of strings")
    last_reopen = payload.get("last_reopen")
    if last_reopen is not None and not isinstance(last_reopen, dict):
        errors.append("last_reopen must be an object or null")
    last_blocker_resolution = payload.get("last_blocker_resolution")
    if last_blocker_resolution is not None and not isinstance(
        last_blocker_resolution, dict
    ):
        errors.append("last_blocker_resolution must be an object or null")
    acceptance_sha256 = payload.get("acceptance_sha256")
    if acceptance_sha256 is not None and (
        not isinstance(acceptance_sha256, str)
        or re.fullmatch(r"[0-9a-f]{64}", acceptance_sha256) is None
    ):
        errors.append("acceptance_sha256 must be a lowercase SHA-256 digest or null")
    if stage == "accept" and status == "completed" and acceptance_sha256 is None:
        errors.append("completed accept requires an acceptance_sha256 snapshot")
    terminal_evidence_errors: list[str] = []
    if (
        not errors
        and stage == "accept"
        and status == "completed"
        and isinstance(acceptance_sha256, str)
        and re.fullmatch(r"[0-9a-f]{64}", acceptance_sha256)
    ):
        snapshot_path = terminal_acceptance_snapshot_path(feature_dir)
        acceptance_path = feature_dir / "human-acceptance.json"
        for label, evidence_path in (
            ("terminal acceptance snapshot", snapshot_path),
            ("current human acceptance", acceptance_path),
        ):
            actual_digest, read_error = _acceptance_evidence_digest(
                evidence_path,
                label=label,
            )
            if read_error is not None:
                terminal_evidence_errors.append(read_error)
                continue
            if actual_digest != acceptance_sha256:
                terminal_evidence_errors.append(
                    f"{label} digest {actual_digest} does not match "
                    f"acceptance_sha256 {acceptance_sha256}"
                )
    if terminal_evidence_errors:
        raise _terminal_acceptance_evidence_error(
            feature_dir,
            acceptance_sha256=str(acceptance_sha256),
            evidence=terminal_evidence_errors,
        )
    if errors:
        raise _invalid_runtime_state(
            feature_dir,
            cause="workflow runtime failed its schema contract: " + "; ".join(errors),
            evidence=[f"schema error: {error}" for error in errors],
            attempted_recovery=[
                {"action": "Validate workflow-runtime.json", "result": "Schema validation failed."}
            ],
        )

    blocker = payload.get("blocker")
    if blocker is not None and not isinstance(blocker, dict):
        raise _invalid_runtime_state(
            feature_dir,
            cause="workflow runtime blocker must be an object or null",
            evidence=["schema error: blocker is neither an object nor null"],
        )
    if status == "blocked" and blocker is None:
        raise _invalid_runtime_state(
            feature_dir,
            cause="blocked workflow runtime must contain a complete blocker",
            evidence=["schema error: status is blocked but blocker is null"],
        )
    if status != "blocked" and blocker is not None:
        raise _invalid_runtime_state(
            feature_dir,
            cause="nonblocked workflow runtime must not retain a blocker",
            evidence=[f"schema error: status is {status} but blocker is present"],
        )
    if isinstance(blocker, dict):
        blocker_errors = validate_workflow_blocker_payload(blocker)
        if blocker_errors:
            raise _invalid_runtime_state(
                feature_dir,
                cause="persisted workflow blocker failed its schema contract",
                evidence=[f"blocker schema error: {error}" for error in blocker_errors],
                attempted_recovery=[
                    {
                        "action": "Validate the persisted blocker against workflow-blocker v1",
                        "result": "Schema validation failed.",
                    }
                ],
            )
        # Command-bearing blocker fields are runtime-owned. Rebuild them from the
        # live feature path and current revision so moved/tampered state cannot
        # inject argv, stale revisions, or ambiguous blocker identities.
        blocker = dict(blocker)
        blocker.pop("resolution_action", None)
        blocker["blocker_id"] = (
            f"workflow-{_slug(stage)}-{_slug(str(blocker['category']))}-r{revision}"
        )
        blocker["resume"] = _resume_record(_show_argv(feature_dir))
        guide = blocker.get("human_action_guide")
        if isinstance(guide, dict):
            guide = dict(guide)
            guide["resume_instruction"] = (
                "Return sanitized evidence to the agent. The agent must apply the "
                "structured resolution_action returned by workflow show; rerunning "
                "show alone does not resolve the blocker."
            )
            blocker["human_action_guide"] = guide
    if isinstance(last_blocker_resolution, dict):
        prior_blocker = last_blocker_resolution.get("blocker")
        resolved_evidence = last_blocker_resolution.get("resolution_evidence")
        resolved_revision = last_blocker_resolution.get("resolved_revision")
        resolved_stage = last_blocker_resolution.get("stage")
        resolved_summary = last_blocker_resolution.get("summary")
        resolution_errors: list[str] = []
        if not isinstance(prior_blocker, dict):
            resolution_errors.append("blocker must be an object")
        else:
            resolution_errors.extend(
                f"blocker: {error}"
                for error in validate_workflow_blocker_payload(prior_blocker)
            )
        if not isinstance(resolved_evidence, list) or not resolved_evidence or any(
            not isinstance(item, str) or not item.strip() for item in resolved_evidence
        ):
            resolution_errors.append(
                "resolution_evidence must be a non-empty array of strings"
            )
        if (
            isinstance(resolved_revision, bool)
            or not isinstance(resolved_revision, int)
            or resolved_revision < 1
        ):
            resolution_errors.append("resolved_revision must be a positive integer")
        if resolved_stage not in WORKFLOW_STAGES:
            resolution_errors.append("stage must be a supported workflow stage")
        if not isinstance(resolved_summary, str) or not resolved_summary.strip():
            resolution_errors.append("summary must be a non-empty string")
        if resolution_errors:
            raise _invalid_runtime_state(
                feature_dir,
                cause="last blocker resolution failed its schema contract",
                evidence=[
                    f"last_blocker_resolution schema error: {error}"
                    for error in resolution_errors
                ],
            )
    return {
        "schema_version": WORKFLOW_RUNTIME_SCHEMA_VERSION,
        "path": str(path),
        "revision": revision,
        "stage": stage,
        "status": status,
        "summary": summary,
        "blocker": blocker,
        "last_resolution_evidence": list(resolution_evidence),
        "last_reopen": last_reopen,
        "last_blocker_resolution": last_blocker_resolution,
        "acceptance_sha256": acceptance_sha256,
    }


def _state_data(state: Mapping[str, Any]) -> dict[str, Any]:
    stage = str(state["stage"])
    status = str(state["status"])
    data = {
        "schema_version": WORKFLOW_STATE_SCHEMA_VERSION,
        "path": str(state["path"]),
        "revision": int(state["revision"]),
        "stage": stage,
        "status": status,
        "summary": str(state.get("summary") or ""),
        "next_stage": None if _is_terminal_state(stage, status) else _NEXT_STAGE.get(stage),
    }
    if state.get("last_reopen") is not None:
        data["last_reopen"] = dict(state["last_reopen"])
    resolution = state.get("last_blocker_resolution")
    if isinstance(resolution, Mapping):
        prior = resolution.get("blocker")
        data["last_blocker_resolution"] = {
            "blocker_id": (
                str(prior.get("blocker_id") or "")
                if isinstance(prior, Mapping)
                else ""
            ),
            "owner": (
                str(prior.get("owner") or "") if isinstance(prior, Mapping) else ""
            ),
            "stage": str(resolution.get("stage") or ""),
            "summary": str(resolution.get("summary") or ""),
            "resolved_revision": resolution.get("resolved_revision"),
            "resolution_evidence": list(resolution.get("resolution_evidence") or []),
        }
    if state.get("acceptance_sha256") is not None:
        data["acceptance_sha256"] = str(state["acceptance_sha256"])
        data["acceptance_snapshot_path"] = str(
            terminal_acceptance_snapshot_path(Path(str(state["path"])).parent)
        )
    return data


def show_workflow(feature_dir: Path | str) -> dict[str, Any]:
    """Read the compact runtime state; detailed Markdown remains on disk."""

    feature = Path(feature_dir)
    state = _read_state(feature)
    blocker = state.get("blocker")
    if state["status"] == "blocked" and isinstance(blocker, dict):
        blocker = _blocked_runtime_view(feature, state)
        resolution_action = _resolution_action(feature, int(state["revision"]))
        return envelope(
            "blocked",
            f"Workflow is blocked at {state['stage']}.",
            data={
                **_state_data(state),
                "resolution_action": (
                    dict(resolution_action)
                    if isinstance(resolution_action, Mapping)
                    else None
                ),
            },
            blockers=[blocker],
            show_argv=_show_argv(feature),
            next_argv=[],
        )
    return envelope(
        "ok",
        f"Workflow is {state['status']} at {state['stage']}.",
        data=_state_data(state),
        next_argv=(
            []
            if _is_terminal_state(state["stage"], state["status"])
            else _next_argv(feature)
        ),
    )


def enter_workflow(
    feature_dir: Path | str,
    *,
    stage: str = "specify",
    expected_revision: int = 0,
    summary: str = "",
) -> dict[str, Any]:
    """Create the workflow at optional discussion or mandatory specify."""

    feature = Path(feature_dir)
    normalized_stage = str(stage or "").strip().lower()
    if normalized_stage not in _ENTRY_STAGES:
        resume_argv = [
            "specify",
            "workflow",
            "enter",
            "--feature-dir",
            str(feature),
            "--command",
            "specify",
            "--expected-revision",
            "0",
            "--format",
            "json",
        ]
        blocker = _runtime_blocker(
            stage=normalized_stage or "workflow-entry",
            category="workflow-validation",
            owner="agent",
            cause=(
                "workflow may only enter at discussion or specify; "
                f"got {normalized_stage or 'missing'}"
            ),
            evidence=[
                "required order: discussion(optional) -> specify -> plan -> tasks -> implement -> accept"
            ],
            attempted_recovery=[],
            affected_scope=["workflow entry"],
            exact_next_action="Enter at specify, or enter at discussion when discovery is needed.",
            unblock_criteria="The first persisted stage is discussion or specify.",
            resume_argv=resume_argv,
        )
        raise InvalidTransition(
            blocker["summary"],
            code="invalid-entry-stage",
            data={"requested_stage": normalized_stage},
            blocker=blocker,
        )
    if isinstance(expected_revision, bool) or expected_revision != 0:
        raise _revision_conflict(
            feature,
            expected_revision=int(expected_revision),
            actual_revision=_actual_revision(feature),
        )
    if not feature.is_dir():
        raise WorkflowRuntimeError(
            f"feature directory does not exist: {feature}",
            code="missing-feature-dir",
            data={"feature_dir": str(feature)},
            status="invalid",
        )
    state = {
        "revision": 1,
        "stage": normalized_stage,
        "status": "active",
        "summary": str(summary or f"{normalized_stage} is active."),
        "blocker": None,
        "last_resolution_evidence": [],
        "last_reopen": None,
        "last_blocker_resolution": None,
        "acceptance_sha256": None,
    }
    persisted = _atomic_guarded_write(feature, state, expected_revision=0)
    return envelope(
        "ok",
        f"Workflow entered at {normalized_stage}.",
        data=_state_data(persisted),
        show_argv=_show_argv(feature),
        next_argv=_complete_stage_argv(feature, 1),
    )


def next_workflow(feature_dir: Path | str) -> dict[str, Any]:
    """Resolve the only legal next stage without mutating state."""

    feature = Path(feature_dir)
    state = _read_state(feature)
    next_stage = (
        None
        if _is_terminal_state(state["stage"], state["status"])
        else _NEXT_STAGE.get(state["stage"])
    )
    data = {**_state_data(state), "next_stage": next_stage}
    blocker = state.get("blocker")
    if state["status"] == "blocked" and isinstance(blocker, dict):
        blocker = _blocked_runtime_view(feature, state)
        resolution_action = _resolution_action(feature, int(state["revision"]))
        return envelope(
            "blocked",
            f"Resolve the blocker before leaving {state['stage']}.",
            data={
                **data,
                "resolution_action": (
                    dict(resolution_action)
                    if isinstance(resolution_action, Mapping)
                    else None
                ),
            },
            blockers=[blocker],
            show_argv=_show_argv(feature),
            next_argv=[],
        )
    next_argv: list[str] = []
    if state["stage"] == "accept" and state["status"] == "active":
        next_argv = _closeout_argv(feature, state["revision"])
    elif next_stage is not None:
        next_argv = (
            _transition_argv(feature, next_stage, state["revision"])
            if state["status"] == "completed"
            else _complete_stage_argv(feature, state["revision"])
        )
    return envelope(
        "ok",
        (
            "Complete explicit human acceptance, then run the guarded closeout."
            if state["stage"] == "accept" and state["status"] == "active"
            else (
                f"The next required stage is {next_stage}."
                if next_stage
                else "The workflow has no remaining stage."
            )
        ),
        data=data,
        show_argv=_show_argv(feature),
        next_argv=next_argv,
    )


def _invalid_transition(
    feature: Path,
    *,
    state: Mapping[str, Any],
    target_stage: str,
    expected_stage: str | None,
) -> InvalidTransition:
    stage = str(state["stage"])
    status = str(state["status"])
    revision = int(state["revision"])
    expected_label = expected_stage or "closeout"
    cause = (
        f"invalid transition from {stage} to {target_stage}; expected {expected_label}"
    )
    if expected_stage is None:
        resume_argv = _show_argv(feature)
    elif status == "completed":
        resume_argv = _transition_argv(feature, expected_stage, revision)
    else:
        resume_argv = _complete_stage_argv(feature, revision)
    recorded = state.get("blocker")
    if status == "blocked" and isinstance(recorded, Mapping):
        blocker = _blocked_runtime_view(feature, state)
    else:
        blocker = _runtime_blocker(
            stage=target_stage,
            category="workflow-validation",
            owner="agent",
            cause=cause,
            evidence=[
                "required order: discussion(optional) -> specify -> plan -> tasks -> implement -> accept"
            ],
            attempted_recovery=[],
            affected_scope=[stage, target_stage],
            exact_next_action=f"Complete {stage}, then transition to {expected_label}.",
            unblock_criteria=(
                f"The {stage} stage is completed and the requested target is exactly "
                f"{expected_label} at the current revision."
            ),
            resume_argv=resume_argv,
        )
    return InvalidTransition(
        cause,
        code="invalid-transition",
        data={
            "stage": stage,
            "target_stage": target_stage,
            "expected_stage": expected_stage,
            "revision": revision,
            **(
                {"resolution_action": _resolution_action(feature, revision)}
                if status == "blocked" and isinstance(recorded, Mapping)
                else {}
            ),
        },
        blocker=blocker,
    )


def _stage_not_completed(
    feature: Path,
    *,
    state: Mapping[str, Any],
    target_stage: str,
) -> InvalidTransition:
    status = str(state["status"])
    stage = str(state["stage"])
    cause = (
        f"cannot transition from {stage} to {target_stage} while the source "
        f"stage status is {status}; complete the source stage first"
    )
    resume_argv = _complete_stage_argv(feature, int(state["revision"]))
    recorded = state.get("blocker")
    if status == "blocked" and isinstance(recorded, Mapping):
        blocker = _blocked_runtime_view(feature, state)
    else:
        blocker = _runtime_blocker(
            stage=stage,
            category="workflow-validation",
            owner="agent",
            cause=cause,
            evidence=[
                f"current stage: {stage}",
                f"current status: {status}",
                f"requested target: {target_stage}",
            ],
            attempted_recovery=[],
            affected_scope=[stage, target_stage],
            exact_next_action=(
                "Finish the current stage artifacts, then run the exact "
                "complete-stage argv."
            ),
            unblock_criteria=(
                f"The persisted {stage} stage has status completed at the current revision."
            ),
            resume_argv=resume_argv,
        )
    return InvalidTransition(
        cause,
        code="source-stage-not-completed",
        data={
            "stage": stage,
            "status": status,
            "target_stage": target_stage,
            "revision": int(state["revision"]),
            **(
                {
                    "resolution_action": _resolution_action(
                        feature, int(state["revision"])
                    )
                }
                if status == "blocked" and isinstance(recorded, Mapping)
                else {}
            ),
        },
        blocker=blocker,
    )


def transition_workflow(
    feature_dir: Path | str,
    *,
    target_stage: str,
    expected_revision: int,
    summary: str = "",
) -> dict[str, Any]:
    """Advance exactly one completed stage."""

    feature = Path(feature_dir)
    state = _read_state(feature)
    if isinstance(expected_revision, bool) or not isinstance(expected_revision, int):
        raise ValueError("expected_revision must be an integer")
    if state["revision"] != expected_revision:
        raise _revision_conflict(
            feature,
            expected_revision=expected_revision,
            actual_revision=state["revision"],
        )
    normalized_target = str(target_stage or "").strip().lower()
    expected_stage = _NEXT_STAGE.get(state["stage"])
    if (
        _is_terminal_state(state["stage"], state["status"])
        or normalized_target != expected_stage
    ):
        raise _invalid_transition(
            feature,
            state=state,
            target_stage=normalized_target or "missing",
            expected_stage=expected_stage,
        )
    if state["status"] != "completed":
        raise _stage_not_completed(
            feature,
            state=state,
            target_stage=normalized_target,
        )
    new_revision = state["revision"] + 1
    new_state = {
        "revision": new_revision,
        "stage": normalized_target,
        "status": "active",
        "summary": str(summary or f"{normalized_target} is active."),
        "blocker": None,
        "last_resolution_evidence": [
            *list(state.get("last_resolution_evidence") or []),
        ],
        "last_reopen": state.get("last_reopen"),
        "last_blocker_resolution": state.get("last_blocker_resolution"),
    }
    persisted = _atomic_guarded_write(
        feature, new_state, expected_revision=expected_revision
    )
    data = _state_data(persisted)
    next_stage = _NEXT_STAGE.get(normalized_target)
    return envelope(
        "ok",
        f"Workflow advanced to {normalized_target}.",
        data=data,
        show_argv=_show_argv(feature),
        next_argv=(
            _complete_stage_argv(feature, new_revision)
            if next_stage is not None
            else _closeout_argv(feature, new_revision)
        ),
    )


def complete_workflow_stage(
    feature_dir: Path | str,
    *,
    expected_revision: int,
    summary: str = "",
) -> dict[str, Any]:
    """Mark one non-terminal stage complete without entering its successor."""

    feature = Path(feature_dir)
    state = _read_state(feature)
    if isinstance(expected_revision, bool) or not isinstance(expected_revision, int):
        raise ValueError("expected_revision must be an integer")
    if state["revision"] != expected_revision:
        raise _revision_conflict(
            feature,
            expected_revision=expected_revision,
            actual_revision=state["revision"],
        )
    if state["status"] == "blocked":
        cause = "blocked stage completion requires workflow resolve first"
        blocker = _blocked_runtime_view(feature, state)
        raise InvalidTransition(
            cause,
            code="blocked-stage-requires-resolution",
            data={
                **_state_data(state),
                "resolution_action": _resolution_action(
                    feature, int(state["revision"])
                ),
            },
            blocker=blocker,
        )
    next_stage = _NEXT_STAGE.get(state["stage"])
    if next_stage is None:
        cause = "accept is terminal and must close through workflow closeout"
        raise InvalidTransition(
            cause,
            code="terminal-stage-requires-closeout",
            data=_state_data(state),
            blocker=_runtime_blocker(
                stage=state["stage"],
                category="workflow-validation",
                owner="agent",
                cause=cause,
                evidence=["required terminal action: workflow closeout"],
                attempted_recovery=[],
                affected_scope=["human acceptance", "workflow closeout"],
                exact_next_action=(
                    "Finish explicit human acceptance, validate it, then run workflow closeout."
                ),
                unblock_criteria=(
                    "The workflow is active at accept and human-acceptance.json is accepted."
                ),
                resume_argv=_show_argv(feature),
            ),
        )
    if state["status"] == "completed":
        return envelope(
            "ok",
            f"Workflow stage {state['stage']} is already complete.",
            data=_state_data(state),
            show_argv=_show_argv(feature),
            next_argv=_transition_argv(feature, next_stage, state["revision"]),
        )

    new_revision = state["revision"] + 1
    new_state = {
        "revision": new_revision,
        "stage": state["stage"],
        "status": "completed",
        "summary": str(summary or f"{state['stage']} stage completed."),
        "blocker": None,
        "last_resolution_evidence": [
            *list(state.get("last_resolution_evidence") or []),
        ],
        "last_reopen": state.get("last_reopen"),
        "last_blocker_resolution": state.get("last_blocker_resolution"),
    }
    persisted = _atomic_guarded_write(
        feature, new_state, expected_revision=expected_revision
    )
    return envelope(
        "ok",
        f"Workflow stage {state['stage']} completed.",
        data=_state_data(persisted),
        show_argv=_show_argv(feature),
        next_argv=_transition_argv(feature, next_stage, new_revision),
    )


def reopen_workflow(
    feature_dir: Path | str,
    *,
    target_stage: str,
    expected_revision: int,
    reason: str,
    evidence: Sequence[object],
    invalidated_artifacts: Sequence[object],
) -> dict[str, Any]:
    """Reopen one invalidated earlier or completed required stage."""

    feature = Path(feature_dir)
    state = _read_state(feature)
    if isinstance(expected_revision, bool) or not isinstance(expected_revision, int):
        raise ValueError("expected_revision must be an integer")
    if state["revision"] != expected_revision:
        raise _revision_conflict(
            feature,
            expected_revision=expected_revision,
            actual_revision=state["revision"],
        )
    normalized_target = _required_text(target_stage, "target_stage").lower()
    normalized_reason = _required_text(reason, "reason")
    normalized_evidence = _required_string_list(evidence, "evidence")
    normalized_invalidated = _required_string_list(
        invalidated_artifacts,
        "invalidated_artifacts",
    )
    source_stage = str(state["stage"])
    source_status = str(state["status"])
    target_is_reopenable = normalized_target in {
        "specify",
        "plan",
        "tasks",
        "implement",
    }
    target_is_earlier = target_is_reopenable and (
        _STAGE_INDEX[normalized_target] < _STAGE_INDEX[source_stage]
    )
    target_is_completed_source = (
        target_is_reopenable
        and normalized_target == source_stage
        and source_status == "completed"
    )
    if source_stage == "accept" and source_status == "completed":
        cause = (
            "a completed acceptance is terminal and immutable; new or changed scope "
            "must start a new feature workflow"
        )
        blocker = _runtime_blocker(
            stage="accept",
            category="workflow-validation",
            owner="agent",
            cause=cause,
            evidence=[
                f"current runtime: {source_stage}/{source_status}/revision {state['revision']}",
                f"requested target: {normalized_target}",
                "terminal acceptance evidence remains authoritative for this feature",
            ],
            attempted_recovery=[],
            affected_scope=["completed workflow", normalized_target],
            exact_next_action=(
                "Preserve this terminal feature and start a new specification workflow "
                "for the changed requirement in a new feature directory."
            ),
            unblock_criteria=(
                "A distinct feature workflow exists for the new scope; this completed "
                "workflow remains unchanged."
            ),
            resume_argv=_show_argv(feature),
        )
        raise InvalidTransition(
            cause,
            code="terminal-workflow-immutable",
            data=_state_data(state),
            blocker=blocker,
        )
    if source_status == "blocked":
        cause = (
            "a blocked workflow cannot be reopened until its recorded blocker is "
            "resolved with evidence"
        )
        raise InvalidTransition(
            cause,
            code="blocked-reopen-requires-resolution",
            data={
                **_state_data(state),
                "requested_target": normalized_target,
                "resolution_action": _resolution_action(
                    feature, int(state["revision"])
                ),
                "recovery": (
                    "Follow the persisted blocker's exact next action and resume argv. "
                    "After its unblock criteria are proven, run workflow resolve with "
                    "the current revision and sanitized resolution evidence; retry "
                    "reopen only if the upstream invalidation still applies."
                ),
            },
            blocker=_blocked_runtime_view(feature, state),
        )
    if source_stage == "accept":
        cause = (
            "generic workflow reopen cannot leave accept; route the recorded human "
            "acceptance finding through accept route-repair"
        )
        blocker = _runtime_blocker(
            stage="accept",
            category="workflow-validation",
            owner="agent",
            cause=cause,
            evidence=[
                f"current runtime: {source_stage}/{source_status}/revision {state['revision']}",
                f"requested target: {normalized_target}",
            ],
            attempted_recovery=[],
            affected_scope=["human acceptance", normalized_target],
            exact_next_action=(
                "Record the failed acceptance finding and use accept route-repair "
                "with its exact route, finding ID, revision, and sanitized evidence."
            ),
            unblock_criteria=(
                "accept route-repair atomically invalidates the verdict and returns "
                "the owning repair handoff."
            ),
            resume_argv=_show_argv(feature),
        )
        raise InvalidTransition(
            cause,
            code="acceptance-repair-required",
            data=_state_data(state),
            blocker=blocker,
        )
    if not (target_is_earlier or target_is_completed_source):
        cause = (
            f"cannot reopen {source_stage} to {normalized_target}; target must be "
            "an earlier required stage, or the same completed stage, among specify, "
            "plan, tasks, or implement"
        )
        blocker = _runtime_blocker(
            stage=source_stage,
            category="workflow-validation",
            owner="agent",
            cause=cause,
            evidence=[
                f"current runtime: {source_stage}/{source_status}/revision {state['revision']}",
                f"requested target: {normalized_target}",
                "allowed action: evidence-backed backward invalidation or completed-stage reactivation",
            ],
            attempted_recovery=[],
            affected_scope=[source_stage, normalized_target],
            exact_next_action=(
                "Choose the highest earlier required stage actually invalidated; a "
                "same-stage target is valid only when that source stage is completed."
            ),
            unblock_criteria=(
                "The target is earlier than the current non-accept stage, or is that "
                "same completed stage, and the request names evidence plus every "
                "invalidated downstream artifact."
            ),
            resume_argv=_show_argv(feature),
        )
        raise InvalidTransition(
            cause,
            code="invalid-reopen-target",
            data={
                **_state_data(state),
                "requested_target": normalized_target,
            },
            blocker=blocker,
        )

    last_reopen = {
        "source_stage": source_stage,
        "source_status": source_status,
        "target_stage": normalized_target,
        "reason": normalized_reason,
        "evidence": normalized_evidence,
        "invalidated_artifacts": normalized_invalidated,
    }
    new_revision = state["revision"] + 1
    new_state = {
        "revision": new_revision,
        "stage": normalized_target,
        "status": "active",
        "summary": normalized_reason,
        "blocker": None,
        "last_resolution_evidence": [
            *list(state.get("last_resolution_evidence") or []),
            f"reopened {source_stage} to {normalized_target}: {normalized_reason}",
            *normalized_evidence,
        ],
        "last_reopen": last_reopen,
        "last_blocker_resolution": state.get("last_blocker_resolution"),
    }
    persisted = _atomic_guarded_write(
        feature, new_state, expected_revision=expected_revision
    )
    return envelope(
        "ok",
        f"Reopened invalidated workflow stage {normalized_target} from {source_stage}.",
        data=_state_data(persisted),
        show_argv=_show_argv(feature),
        next_argv=_complete_stage_argv(feature, new_revision),
    )


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
    """Return a failed acceptance to an earlier owning stage exactly once."""

    feature = Path(feature_dir)
    state = _read_state(feature)
    if isinstance(expected_revision, bool) or not isinstance(expected_revision, int):
        raise ValueError("expected_revision must be an integer")
    if state["revision"] != expected_revision:
        raise _revision_conflict(
            feature,
            expected_revision=expected_revision,
            actual_revision=state["revision"],
        )
    normalized_target = _required_text(target_stage, "target_stage").lower()
    if normalized_target not in {"specify", "implement"}:
        raise ValueError("acceptance repair target_stage must be specify or implement")
    normalized_route = _required_text(repair_route, "repair_route")
    normalized_finding = _required_text(finding_id, "finding_id")
    normalized_evidence = _required_string_list(evidence, "evidence")
    if state["stage"] == "accept" and state["status"] == "blocked":
        cause = (
            "acceptance repair cannot supersede a persisted blocker; resolve the "
            "recorded blocker with evidence before routing the acceptance finding"
        )
        raise InvalidTransition(
            cause,
            code="blocked-reopen-requires-resolution",
            data={
                **_state_data(state),
                "requested_target": normalized_target,
                "resolution_action": _resolution_action(
                    feature, int(state["revision"])
                ),
                "recovery": (
                    "Follow the persisted blocker's exact next action and resume argv, "
                    "then run workflow resolve with sanitized evidence."
                ),
            },
            blocker=_blocked_runtime_view(feature, state),
        )
    if state["stage"] != "accept" or state["status"] != "active":
        cause = (
            "acceptance repair may only reopen active accept; "
            f"found {state['stage']} with {state['status']} status"
        )
        raise InvalidTransition(
            cause,
            code="invalid-acceptance-repair-stage",
            data=_state_data(state),
            blocker=_runtime_blocker(
                stage=state["stage"],
                category="workflow-validation",
                owner="agent",
                cause=cause,
                evidence=[
                    "required source state: active accept",
                    f"requested repair route: {normalized_route}",
                    f"acceptance finding: {normalized_finding}",
                ],
                attempted_recovery=[],
                affected_scope=["human acceptance", normalized_target],
                exact_next_action=(
                    "Read the current workflow and acceptance state; route repair only "
                    "from the unresolved accept phase."
                ),
                unblock_criteria=(
                    "The workflow is active at accept and the named open "
                    "finding still selects this repair route."
                ),
                resume_argv=_show_argv(feature),
            ),
        )

    new_revision = state["revision"] + 1
    reopening_evidence = [
        *list(state.get("last_resolution_evidence") or []),
        f"acceptance finding {normalized_finding} routed to {normalized_route}",
        *normalized_evidence,
    ]
    new_state = {
        "revision": new_revision,
        "stage": normalized_target,
        "status": "active",
        "summary": str(
            summary
            or f"Acceptance finding {normalized_finding} reopened {normalized_target}."
        ),
        "blocker": None,
        "last_resolution_evidence": reopening_evidence,
        "last_reopen": {
            "source_stage": "accept",
            "source_status": state["status"],
            "target_stage": normalized_target,
            "reason": f"Acceptance finding {normalized_finding} routed to {normalized_route}",
            "evidence": normalized_evidence,
            "invalidated_artifacts": [
                "human-acceptance.json verdict",
                f"{normalized_target} and downstream artifacts",
            ],
        },
        "last_blocker_resolution": state.get("last_blocker_resolution"),
    }
    persisted = _atomic_guarded_write(
        feature, new_state, expected_revision=expected_revision
    )
    return envelope(
        "ok",
        f"Acceptance repair routed to {normalized_route}.",
        data={
            **_state_data(persisted),
            "reopened_from": "accept",
            "repair_route": normalized_route,
            "finding_id": normalized_finding,
            "handoff_command": normalized_route,
        },
        show_argv=_show_argv(feature),
    )


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
    """Persist a detailed blocker and, at a human boundary, a novice guide."""

    feature = Path(feature_dir)
    state = _read_state(feature)
    if isinstance(expected_revision, bool) or not isinstance(expected_revision, int):
        raise ValueError("expected_revision must be an integer")
    if state["revision"] != expected_revision:
        raise _revision_conflict(
            feature,
            expected_revision=expected_revision,
            actual_revision=state["revision"],
        )
    if _is_terminal_state(state["stage"], state["status"]):
        raise InvalidTransition(
            "completed workflow cannot be blocked",
            code="workflow-already-completed",
            data=_state_data(state),
        )
    if state["status"] == "blocked":
        cause = "an unresolved workflow blocker cannot be replaced by another blocker"
        raise InvalidTransition(
            cause,
            code="blocker-already-recorded",
            data={
                **_state_data(state),
                "resolution_action": _resolution_action(
                    feature, int(state["revision"])
                ),
                "recovery": (
                    "Honor the persisted blocker. Resolve it with fresh evidence before "
                    "recording any later independent blocker."
                ),
            },
            blocker=_blocked_runtime_view(feature, state),
        )
    normalized_category = _required_text(category, "category").lower()
    if normalized_category not in _BLOCKER_CATEGORIES:
        raise ValueError(f"unsupported blocker category '{category}'")
    normalized_owner = _required_text(owner, "owner").lower()
    if normalized_owner not in _BLOCKER_OWNERS:
        raise ValueError(f"unsupported blocker owner '{owner}'")
    normalized_cause = _required_text(cause, "cause")
    normalized_evidence = _required_string_list(evidence, "evidence")
    normalized_scope = _required_string_list(affected_scope, "affected_scope")
    normalized_resume = _show_argv(feature)
    normalized_attempts = _normalize_attempts(attempted_recovery)
    normalized_action = _required_text(exact_next_action, "exact_next_action")
    normalized_criteria = _required_text(unblock_criteria, "unblock_criteria")
    blocked_revision = state["revision"] + 1
    resolution_action = _resolution_action(feature, blocked_revision)
    blocker = _runtime_blocker(
        stage=state["stage"],
        category=normalized_category,
        owner=normalized_owner,
        cause=normalized_cause,
        evidence=normalized_evidence,
        attempted_recovery=normalized_attempts,
        affected_scope=normalized_scope,
        exact_next_action=normalized_action,
        unblock_criteria=normalized_criteria,
        resume_argv=normalized_resume,
        human_action=human_action,
        human_action_required=human_action_required,
        blocker_id=(
            f"workflow-{_slug(state['stage'])}-{_slug(normalized_category)}-"
            f"r{blocked_revision}"
        ),
        resolution_action=resolution_action,
    )
    new_state = {
        "revision": blocked_revision,
        "stage": state["stage"],
        "status": "blocked",
        "summary": normalized_cause,
        "blocker": blocker,
        "last_resolution_evidence": state.get("last_resolution_evidence") or [],
        "last_reopen": state.get("last_reopen"),
        "last_blocker_resolution": state.get("last_blocker_resolution"),
    }
    persisted = _atomic_guarded_write(
        feature, new_state, expected_revision=expected_revision
    )
    output_blocker = _blocked_runtime_view(feature, persisted)
    return envelope(
        "blocked",
        normalized_cause,
        data={**_state_data(persisted), "resolution_action": resolution_action},
        blockers=[output_blocker],
        show_argv=_show_argv(feature),
        next_argv=[],
    )


def resolve_workflow_blocker(
    feature_dir: Path | str,
    *,
    expected_revision: int,
    resolution_evidence: Sequence[object],
    summary: str = "",
) -> dict[str, Any]:
    """Resolve one persisted blocker and reactivate its owning stage."""

    feature = Path(feature_dir)
    state = _read_state(feature)
    if isinstance(expected_revision, bool) or not isinstance(expected_revision, int):
        raise ValueError("expected_revision must be an integer")
    if state["revision"] != expected_revision:
        raise _revision_conflict(
            feature,
            expected_revision=expected_revision,
            actual_revision=state["revision"],
        )
    blocker = state.get("blocker")
    if state["status"] != "blocked" or not isinstance(blocker, dict):
        cause = (
            "workflow resolve requires a persisted blocked state; "
            f"found {state['stage']} with {state['status']} status"
        )
        raise InvalidTransition(
            cause,
            code="no-blocker-to-resolve",
            data=_state_data(state),
            blocker=_runtime_blocker(
                stage=state["stage"],
                category="workflow-validation",
                owner="agent",
                cause=cause,
                evidence=["required source status: blocked"],
                attempted_recovery=[],
                affected_scope=[state["stage"], "workflow blocker resolution"],
                exact_next_action="Read the current workflow and continue its active owner.",
                unblock_criteria="A persisted blocker exists at the current revision.",
                resume_argv=_show_argv(feature),
            ),
        )
    normalized_evidence = _required_string_list(
        resolution_evidence, "resolution_evidence"
    )
    resolution_summary = str(summary or "").strip() or (
        f"Resolved blocker {blocker.get('blocker_id', 'workflow-blocker')}."
    )
    new_revision = state["revision"] + 1
    new_state = {
        "revision": new_revision,
        "stage": state["stage"],
        "status": "active",
        "summary": resolution_summary,
        "blocker": None,
        "last_resolution_evidence": [
            *list(state.get("last_resolution_evidence") or []),
            *normalized_evidence,
        ],
        "last_reopen": state.get("last_reopen"),
        "last_blocker_resolution": {
            "blocker": blocker,
            "stage": state["stage"],
            "summary": resolution_summary,
            "resolved_revision": new_revision,
            "resolution_evidence": normalized_evidence,
        },
    }
    persisted = _atomic_guarded_write(
        feature, new_state, expected_revision=expected_revision
    )
    next_argv = (
        _closeout_argv(feature, new_revision)
        if state["stage"] == "accept"
        else _complete_stage_argv(feature, new_revision)
    )
    return envelope(
        "ok",
        f"Resolved the workflow blocker at {state['stage']}; the stage is active again.",
        data=_state_data(persisted),
        show_argv=_show_argv(feature),
        next_argv=next_argv,
    )


def closeout_workflow(
    feature_dir: Path | str,
    *,
    expected_revision: int,
    acceptance_sha256: str,
    summary: str = "",
) -> dict[str, Any]:
    """Commit an active acceptance stage with its validated artifact snapshot."""

    feature = Path(feature_dir)
    state = _read_state(feature)
    if isinstance(expected_revision, bool) or not isinstance(expected_revision, int):
        raise ValueError("expected_revision must be an integer")
    if state["revision"] != expected_revision:
        raise _revision_conflict(
            feature,
            expected_revision=expected_revision,
            actual_revision=state["revision"],
        )
    if state["stage"] != "accept" or state["status"] != "active":
        resume_argv = _show_argv(feature)
        cause = (
            "workflow may only close out from accept with active status; "
            f"found {state['stage']} with {state['status']} status"
        )
        blocker = _runtime_blocker(
            stage=state["stage"],
            category="workflow-validation",
            owner="agent",
            cause=cause,
            evidence=["required final stage: active accept"],
            attempted_recovery=[],
            affected_scope=["workflow closeout"],
            exact_next_action=(
                "Complete every remaining stage in order and resolve any blocker before closeout."
            ),
            unblock_criteria="The current state is active accept at the current revision.",
            resume_argv=resume_argv,
        )
        raise InvalidTransition(
            cause,
            code="invalid-closeout-stage",
            data=_state_data(state),
            blocker=blocker,
        )
    normalized_acceptance_sha256 = str(acceptance_sha256 or "").strip()
    if re.fullmatch(r"[0-9a-f]{64}", normalized_acceptance_sha256) is None:
        raise ValueError("acceptance_sha256 must be a lowercase SHA-256 digest")
    acceptance_path = feature / "human-acceptance.json"
    snapshot_path = terminal_acceptance_snapshot_path(feature)
    actual_acceptance_sha256, acceptance_read_error = _acceptance_evidence_digest(
        acceptance_path,
        label="current human acceptance",
    )
    actual_snapshot_sha256, snapshot_read_error = _acceptance_evidence_digest(
        snapshot_path,
        label="terminal acceptance snapshot",
    )
    if (
        actual_acceptance_sha256 != normalized_acceptance_sha256
        or actual_snapshot_sha256 != normalized_acceptance_sha256
    ):
        cause = "human acceptance changed before terminal workflow commit"
        raise InvalidTransition(
            cause,
            code="acceptance-snapshot-conflict",
            data={
                **_state_data(state),
                "expected_acceptance_sha256": normalized_acceptance_sha256,
                "actual_acceptance_sha256": actual_acceptance_sha256,
                "actual_snapshot_sha256": actual_snapshot_sha256,
            },
            blocker=_runtime_blocker(
                stage="accept",
                category="conflict-or-drift",
                owner=(
                    "maintainer"
                    if acceptance_read_error is not None
                    or snapshot_read_error is not None
                    else "agent"
                ),
                cause=cause,
                evidence=[
                    f"expected acceptance digest: {normalized_acceptance_sha256}",
                    f"actual acceptance digest: {actual_acceptance_sha256}",
                    f"terminal snapshot digest: {actual_snapshot_sha256}",
                    *(
                        [acceptance_read_error]
                        if acceptance_read_error is not None
                        else []
                    ),
                    *(
                        [snapshot_read_error]
                        if snapshot_read_error is not None
                        else []
                    ),
                ],
                attempted_recovery=[],
                affected_scope=["human-acceptance.json", "workflow closeout"],
                exact_next_action=(
                    "Revalidate the current human acceptance artifact and retry "
                    "closeout with its fresh revision-bound snapshot."
                ),
                unblock_criteria=(
                    "human-acceptance.json remains accepted and unchanged through "
                    "the terminal runtime commit."
                ),
                resume_argv=_show_argv(feature),
            ),
        )
    new_state = {
        "revision": state["revision"] + 1,
        "stage": "accept",
        "status": "completed",
        "summary": str(summary or "Human acceptance completed."),
        "blocker": None,
        "last_resolution_evidence": state.get("last_resolution_evidence") or [],
        "last_reopen": state.get("last_reopen"),
        "last_blocker_resolution": state.get("last_blocker_resolution"),
        "acceptance_sha256": normalized_acceptance_sha256,
    }
    persisted = _atomic_guarded_write(
        feature, new_state, expected_revision=expected_revision
    )
    return envelope(
        "ok",
        "Workflow closeout completed.",
        data=_state_data(persisted),
        show_argv=_show_argv(feature),
    )


__all__ = [
    "InvalidTransition",
    "MissingWorkflowState",
    "RevisionConflict",
    "WORKFLOW_STAGES",
    "TERMINAL_ACCEPTANCE_SNAPSHOT_FILENAME",
    "WORKFLOW_RUNTIME_SCHEMA_VERSION",
    "WORKFLOW_STATE_SCHEMA_VERSION",
    "WorkflowRuntimeError",
    "block_workflow",
    "closeout_workflow",
    "complete_workflow_stage",
    "enter_workflow",
    "next_workflow",
    "reopen_workflow",
    "reopen_acceptance_workflow",
    "resolve_workflow_blocker",
    "show_workflow",
    "transition_workflow",
    "terminal_acceptance_snapshot_path",
    "workflow_runtime_path",
    "workflow_state_path",
]
