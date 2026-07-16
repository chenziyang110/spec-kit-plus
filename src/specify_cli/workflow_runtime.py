"""Deterministic workflow state transitions for Classic and Advanced agents.

The runtime owns the mandatory high-level phase order.  It writes the existing
``workflow-state.md`` contract so current serializers and validators continue to
observe one source of truth, while keeping mutation behind optimistic revision
guards and atomic replacement.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
import re
import subprocess
from typing import Any

import yaml

from .agent_api import envelope
from .atomic_io import atomic_write_text, interprocess_lock
from .hooks.checkpoint_serializers import parse_frontmatter, serialize_workflow_state
from .hooks.state_validation import EXPECTED_WORKFLOW_STATE


WORKFLOW_STATE_SCHEMA_VERSION = 1
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
_PHASE_MODE = {
    "discussion": "planning-only",
    "specify": "planning-only",
    "plan": "design-only",
    "tasks": "task-generation-only",
    "implement": "execution-only",
    "accept": "acceptance-only",
}
_ARTIFACT_CONTRACT = {
    "discussion": {
        "allowed": [".specify/discussions/", "workflow-state.md"],
        "forbidden": ["write feature implementation", "skip specify"],
        "authoritative": ["discussion record", "workflow-state.md"],
    },
    "specify": {
        "allowed": ["spec.md", "spec-contract.json", "workflow-state.md"],
        "forbidden": ["write plan.md", "write tasks.md", "edit source code"],
        "authoritative": ["spec.md", "spec-contract.json", "workflow-state.md"],
    },
    "plan": {
        "allowed": ["plan.md", "plan-contract.json", "workflow-state.md"],
        "forbidden": ["write tasks.md", "edit source code"],
        "authoritative": [
            "spec-contract.json",
            "plan-contract.json",
            "workflow-state.md",
        ],
    },
    "tasks": {
        "allowed": ["tasks.md", "task-index.json", "workflow-state.md"],
        "forbidden": ["edit source code", "start implementation"],
        "authoritative": ["plan-contract.json", "task-index.json", "workflow-state.md"],
    },
    "implement": {
        "allowed": [
            "source and test files named by task-index.json",
            "implementation lifecycle records",
            "workflow-state.md",
        ],
        "forbidden": ["skip task validation", "declare human acceptance"],
        "authoritative": [
            "task-index.json",
            "implementation lifecycle records",
            "workflow-state.md",
        ],
    },
    "accept": {
        "allowed": ["human-acceptance.json", "workflow-state.md"],
        "forbidden": [
            "silently repair implementation",
            "perform unapproved external writes",
        ],
        "authoritative": [
            "implementation-summary.md",
            "human-acceptance.json",
            "workflow-state.md",
        ],
    },
}
_BLOCKER_CATEGORIES = frozenset(
    {
        "workflow-validation",
        "artifact-or-state",
        "technical-failure",
        "dependency-or-service",
        "delegation",
        "project-cognition",
        "credentials-or-permission",
        "external-system",
        "external-write-authorization",
        "human-decision",
        "human-review",
        "timeout",
        "conflict-or-drift",
    }
)
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
    """Return the canonical high-level workflow state path for a feature."""

    return Path(feature_dir) / "workflow-state.md"


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-") or "workflow"


def _resume_command(argv: Sequence[str]) -> str:
    return subprocess.list2cmdline([str(item) for item in argv])


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
) -> dict[str, Any]:
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
        guide = _validate_human_action_guide(guide)
    return {
        "version": 1,
        "blocker_id": f"workflow-{_slug(stage)}-{_slug(category)}",
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
        return envelope(
            self.status,
            str(self),
            data={"error_code": self.code, **self.data},
            blockers=[blocker] if blocker else [],
            next_argv=_blocker_resume_argv(blocker),
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


def _clean_line(value: object) -> str:
    return " ".join(str(value or "").replace("`", "'").split())


def _command_for_stage(stage: str) -> str:
    return f"sp-{stage}"


def _next_command_token(stage: str, status: str) -> str:
    if status == "completed":
        return "none"
    next_stage = _NEXT_STAGE.get(stage)
    return f"/sp.{next_stage}" if next_stage else "/sp.accept"


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


def _render_list(items: Sequence[str]) -> str:
    return "\n".join(f"- {item}" for item in items)


def _render_state(state: Mapping[str, Any]) -> str:
    stage = str(state["stage"])
    status = str(state["status"])
    contract = _ARTIFACT_CONTRACT[stage]
    blocker = state.get("blocker")
    blocker_reason = (
        str(blocker.get("summary") or "None")
        if isinstance(blocker, Mapping)
        else "None"
    )
    next_stage = _NEXT_STAGE.get(stage)
    next_action = (
        "Workflow complete."
        if status == "completed"
        else (
            f"Resolve blocker, then continue {stage}."
            if status == "blocked"
            else f"Complete {stage}, then transition to {next_stage or 'closeout'}."
        )
    )
    frontmatter = {
        "workflow_runtime_version": WORKFLOW_STATE_SCHEMA_VERSION,
        "revision": int(state["revision"]),
        "stage": stage,
        "active_command": _command_for_stage(stage),
        "status": status,
        "phase_mode": _PHASE_MODE[stage],
        "summary": str(state.get("summary") or ""),
        "current_stage": stage,
        "next_action": next_action,
        "blocker_reason": blocker_reason,
        "blocker": blocker,
        "last_resolution_evidence": list(state.get("last_resolution_evidence") or []),
    }
    yaml_frontmatter = yaml.safe_dump(
        frontmatter,
        allow_unicode=True,
        sort_keys=False,
        default_flow_style=False,
    ).rstrip()
    next_command = _next_command_token(stage, status)
    return (
        f"---\n{yaml_frontmatter}\n---\n\n"
        f"# Workflow State: {stage}\n\n"
        "## Current Command\n\n"
        f"- active_command: `{_command_for_stage(stage)}`\n"
        f"- status: `{status}`\n\n"
        "## Phase Mode\n\n"
        f"- phase_mode: `{_PHASE_MODE[stage]}`\n"
        f"- summary: `{_clean_line(state.get('summary'))}`\n\n"
        "## Stage State\n\n"
        f"- current_stage: `{stage}`\n"
        "- current_domain: `none`\n"
        f"- next_action: `{_clean_line(next_action)}`\n"
        f"- blocker_reason: `{_clean_line(blocker_reason)}`\n"
        f"- final_handoff_decision: `{next_command}`\n\n"
        "## Allowed Artifact Writes\n\n"
        f"{_render_list(contract['allowed'])}\n\n"
        "## Forbidden Actions\n\n"
        f"{_render_list(contract['forbidden'])}\n\n"
        "## Authoritative Files\n\n"
        f"{_render_list(contract['authoritative'])}\n\n"
        "## Next Command\n\n"
        f"- `{next_command}`\n"
    )


def _actual_revision(path: Path) -> int:
    if not path.is_file():
        return 0
    try:
        frontmatter, _ = parse_frontmatter(path.read_text(encoding="utf-8"))
        revision = frontmatter.get("revision")
        if isinstance(revision, bool) or not isinstance(revision, int) or revision < 1:
            raise ValueError
        return revision
    except (OSError, ValueError, yaml.YAMLError) as exc:
        raise WorkflowRuntimeError(
            f"workflow state at {path} has no valid runtime revision",
            code="invalid-workflow-state",
            data={"path": str(path)},
            status="error",
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
        evidence=[f"workflow-state.md current revision is {actual_revision}"],
        attempted_recovery=[],
        affected_scope=["workflow-state.md"],
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
            "path": str(workflow_state_path(feature_dir)),
        },
        blocker=blocker,
    )


def _atomic_guarded_write(
    feature_dir: Path,
    state: Mapping[str, Any],
    *,
    expected_revision: int,
) -> Path:
    path = workflow_state_path(feature_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.parent / ".workflow-state.lock"
    with interprocess_lock(lock_path):
        actual_revision = _actual_revision(path)
        if actual_revision != expected_revision:
            raise _revision_conflict(
                feature_dir,
                expected_revision=expected_revision,
                actual_revision=actual_revision,
            )
        atomic_write_text(path, _render_state(state))
    return path


def _read_state(feature_dir: Path) -> dict[str, Any]:
    path = workflow_state_path(feature_dir)
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
            cause=f"workflow-state.md is missing at {path}",
            evidence=[str(path)],
            attempted_recovery=[],
            affected_scope=["workflow entry"],
            exact_next_action="Enter the workflow at specify, or at optional discussion.",
            unblock_criteria="workflow-state.md exists at revision 1.",
            resume_argv=enter_argv,
        )
        raise MissingWorkflowState(
            f"workflow-state.md is missing at {path}",
            code="missing-workflow-state",
            data={"path": str(path)},
            blocker=blocker,
        )

    frontmatter, _ = parse_frontmatter(path.read_text(encoding="utf-8"))
    revision = frontmatter.get("revision")
    stage = str(frontmatter.get("stage") or "").strip().lower()
    status = str(frontmatter.get("status") or "").strip().lower()
    if isinstance(revision, bool) or not isinstance(revision, int) or revision < 1:
        raise WorkflowRuntimeError(
            "workflow state revision must be a positive integer",
            code="invalid-workflow-state",
            data={"path": str(path)},
            status="error",
        )
    if stage not in WORKFLOW_STAGES:
        raise WorkflowRuntimeError(
            f"workflow state has unsupported stage '{stage or 'missing'}'",
            code="invalid-workflow-state",
            data={"path": str(path)},
            status="error",
        )
    if status not in {"active", "blocked", "completed"}:
        raise WorkflowRuntimeError(
            f"workflow state has unsupported status '{status or 'missing'}'",
            code="invalid-workflow-state",
            data={"path": str(path)},
            status="error",
        )

    checkpoint = serialize_workflow_state(path)
    expected_command = _command_for_stage(stage)
    expected_phase = _PHASE_MODE[stage]
    validator_contract = EXPECTED_WORKFLOW_STATE.get(stage)
    if validator_contract is not None:
        expected_command, expected_phase = validator_contract
    errors: list[str] = []
    if checkpoint["active_command"] != expected_command:
        errors.append(
            f"active_command expected {expected_command}, got {checkpoint['active_command'] or 'missing'}"
        )
    if checkpoint["phase_mode"] != expected_phase:
        errors.append(
            f"phase_mode expected {expected_phase}, got {checkpoint['phase_mode'] or 'missing'}"
        )
    if checkpoint["current_stage"] != stage:
        errors.append(
            f"current_stage expected {stage}, got {checkpoint['current_stage'] or 'missing'}"
        )
    for key in ("allowed_artifact_writes", "forbidden_actions", "authoritative_files"):
        if not checkpoint[key]:
            errors.append(f"{key} is missing")
    if not checkpoint["next_command"]:
        errors.append("next_command is missing")
    if errors:
        raise WorkflowRuntimeError(
            "workflow state failed the existing serializer/validator contract: "
            + "; ".join(errors),
            code="invalid-workflow-state",
            data={"path": str(path), "errors": errors},
            status="error",
        )

    blocker = frontmatter.get("blocker")
    if blocker is not None and not isinstance(blocker, dict):
        raise WorkflowRuntimeError(
            "workflow state blocker must be an object or null",
            code="invalid-workflow-state",
            data={"path": str(path)},
            status="error",
        )
    return {
        "schema_version": WORKFLOW_STATE_SCHEMA_VERSION,
        "path": str(path),
        "revision": revision,
        "stage": stage,
        "status": status,
        "summary": str(frontmatter.get("summary") or ""),
        "blocker": blocker,
        "last_resolution_evidence": list(
            frontmatter.get("last_resolution_evidence") or []
        ),
    }


def _state_data(state: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": WORKFLOW_STATE_SCHEMA_VERSION,
        "path": str(state["path"]),
        "revision": int(state["revision"]),
        "stage": str(state["stage"]),
        "status": str(state["status"]),
        "summary": str(state.get("summary") or ""),
        "next_stage": (
            _NEXT_STAGE.get(str(state["stage"]))
            if state["status"] != "completed"
            else None
        ),
    }


def show_workflow(feature_dir: Path | str) -> dict[str, Any]:
    """Read the compact runtime state; detailed Markdown remains on disk."""

    feature = Path(feature_dir)
    state = _read_state(feature)
    blocker = state.get("blocker")
    if state["status"] == "blocked" and isinstance(blocker, dict):
        return envelope(
            "blocked",
            f"Workflow is blocked at {state['stage']}.",
            data=_state_data(state),
            blockers=[blocker],
            next_argv=_blocker_resume_argv(blocker),
        )
    return envelope(
        "ok",
        f"Workflow is {state['status']} at {state['stage']}.",
        data=_state_data(state),
        next_argv=_next_argv(feature) if state["status"] != "completed" else [],
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
            actual_revision=_actual_revision(workflow_state_path(feature)),
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
    }
    _atomic_guarded_write(feature, state, expected_revision=0)
    persisted = _read_state(feature)
    next_stage = _NEXT_STAGE[normalized_stage]
    return envelope(
        "ok",
        f"Workflow entered at {normalized_stage}.",
        data=_state_data(persisted),
        show_argv=_show_argv(feature),
        next_argv=_transition_argv(feature, next_stage, 1),
    )


def next_workflow(feature_dir: Path | str) -> dict[str, Any]:
    """Resolve the only legal next stage without mutating state."""

    feature = Path(feature_dir)
    state = _read_state(feature)
    next_stage = (
        _NEXT_STAGE.get(state["stage"]) if state["status"] != "completed" else None
    )
    data = {**_state_data(state), "next_stage": next_stage}
    blocker = state.get("blocker")
    if state["status"] == "blocked" and isinstance(blocker, dict):
        return envelope(
            "blocked",
            f"Resolve the blocker before leaving {state['stage']}.",
            data=data,
            blockers=[blocker],
            next_argv=_blocker_resume_argv(blocker),
        )
    next_argv = (
        _transition_argv(feature, next_stage, state["revision"])
        if next_stage is not None
        else []
    )
    return envelope(
        "ok",
        (
            f"The next required stage is {next_stage}."
            if next_stage
            else "The workflow has no remaining stage."
        ),
        data=data,
        show_argv=_show_argv(feature),
        next_argv=next_argv,
    )


def _invalid_transition(
    feature: Path,
    *,
    stage: str,
    target_stage: str,
    expected_stage: str | None,
    revision: int,
) -> InvalidTransition:
    expected_label = expected_stage or "closeout"
    cause = (
        f"invalid transition from {stage} to {target_stage}; expected {expected_label}"
    )
    resume_argv = (
        _transition_argv(feature, expected_stage, revision)
        if expected_stage is not None
        else _show_argv(feature)
    )
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
        unblock_criteria=f"The requested target is exactly {expected_label} at revision {revision}.",
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
        },
        blocker=blocker,
    )


def transition_workflow(
    feature_dir: Path | str,
    *,
    target_stage: str,
    expected_revision: int,
    summary: str = "",
    resolution_evidence: Sequence[str] | None = None,
) -> dict[str, Any]:
    """Advance exactly one stage; a blocked state requires resolution evidence."""

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
    if state["status"] == "completed" or normalized_target != expected_stage:
        raise _invalid_transition(
            feature,
            stage=state["stage"],
            target_stage=normalized_target or "missing",
            expected_stage=expected_stage,
            revision=state["revision"],
        )
    resolution = [
        str(item).strip() for item in (resolution_evidence or []) if str(item).strip()
    ]
    if state["status"] == "blocked" and not resolution:
        blocker = dict(state.get("blocker") or {})
        resume = _blocker_resume_argv(blocker) or _show_argv(feature)
        cause = "blocked workflow transition requires resolution_evidence"
        raise InvalidTransition(
            cause,
            code="missing-resolution-evidence",
            data={"stage": state["stage"], "revision": state["revision"]},
            blocker={
                **blocker,
                "summary": cause,
                "exact_next_action": (
                    "Return sanitized evidence satisfying the recorded unblock criteria, "
                    "then rerun the exact resume argv."
                ),
                "resume": _resume_record(resume),
            },
        )
    new_revision = state["revision"] + 1
    new_state = {
        "revision": new_revision,
        "stage": normalized_target,
        "status": "active",
        "summary": str(summary or f"{normalized_target} is active."),
        "blocker": None,
        "last_resolution_evidence": resolution,
    }
    _atomic_guarded_write(feature, new_state, expected_revision=expected_revision)
    persisted = _read_state(feature)
    data = _state_data(persisted)
    if resolution:
        data["resolution_evidence"] = resolution
    next_stage = _NEXT_STAGE.get(normalized_target)
    return envelope(
        "ok",
        f"Workflow advanced to {normalized_target}.",
        data=data,
        show_argv=_show_argv(feature),
        next_argv=(
            _transition_argv(feature, next_stage, new_revision)
            if next_stage is not None
            else [
                "specify",
                "workflow",
                "closeout",
                "--feature-dir",
                str(feature),
                "--expected-revision",
                str(new_revision),
                "--format",
                "json",
            ]
        ),
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
    resume_argv: Sequence[object],
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
    if state["status"] == "completed":
        raise InvalidTransition(
            "completed workflow cannot be blocked",
            code="workflow-already-completed",
            data=_state_data(state),
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
    normalized_resume = _required_string_list(resume_argv, "resume_argv")
    normalized_attempts = _normalize_attempts(attempted_recovery)
    normalized_action = _required_text(exact_next_action, "exact_next_action")
    normalized_criteria = _required_text(unblock_criteria, "unblock_criteria")
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
    )
    new_state = {
        "revision": state["revision"] + 1,
        "stage": state["stage"],
        "status": "blocked",
        "summary": normalized_cause,
        "blocker": blocker,
        "last_resolution_evidence": state.get("last_resolution_evidence") or [],
    }
    _atomic_guarded_write(feature, new_state, expected_revision=expected_revision)
    persisted = _read_state(feature)
    return envelope(
        "blocked",
        normalized_cause,
        data=_state_data(persisted),
        blockers=[blocker],
        show_argv=_show_argv(feature),
        next_argv=normalized_resume,
    )


def closeout_workflow(
    feature_dir: Path | str,
    *,
    expected_revision: int,
    summary: str = "",
) -> dict[str, Any]:
    """Mark an active acceptance stage complete; no earlier stage may close."""

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
    new_state = {
        "revision": state["revision"] + 1,
        "stage": "accept",
        "status": "completed",
        "summary": str(summary or "Human acceptance completed."),
        "blocker": None,
        "last_resolution_evidence": state.get("last_resolution_evidence") or [],
    }
    _atomic_guarded_write(feature, new_state, expected_revision=expected_revision)
    persisted = _read_state(feature)
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
    "WORKFLOW_STATE_SCHEMA_VERSION",
    "WorkflowRuntimeError",
    "block_workflow",
    "closeout_workflow",
    "enter_workflow",
    "next_workflow",
    "show_workflow",
    "transition_workflow",
    "workflow_state_path",
]
