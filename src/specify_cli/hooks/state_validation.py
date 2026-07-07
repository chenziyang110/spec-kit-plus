"""Validation hooks for workflow source-of-truth state files."""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from specify_cli.lanes.state_store import iter_lane_records

from .checkpoint_serializers import (
    normalize_command_name,
    serialize_debug_session,
    serialize_implement_tracker,
    serialize_quick_status,
    serialize_workflow_state,
)
from .events import WORKFLOW_STATE_VALIDATE
from .types import HookResult, QualityHookError


EXPECTED_WORKFLOW_STATE = {
    "constitution": ("sp-constitution", "planning-only"),
    "specify": ("sp-specify", "planning-only"),
    "clarify": ("sp-clarify", "planning-only"),
    "deep-research": ("sp-deep-research", "research-only"),
    "plan": ("sp-plan", "design-only"),
    "tasks": ("sp-tasks", "task-generation-only"),
    "analyze": ("sp-analyze", "analysis-only"),
    "prd-scan": ("sp-prd-scan", "analysis-only"),
    "prd-build": ("sp-prd-build", "analysis-only"),
    "prd": ("sp-prd", "analysis-only"),
}


def validate_state_hook(project_root: Path, payload: dict[str, object]) -> HookResult:
    command_name = normalize_command_name(str(payload.get("command_name") or ""))
    autofix = bool(payload.get("autofix"))

    if command_name in EXPECTED_WORKFLOW_STATE:
        feature_dir = _required_path(project_root, payload, "feature_dir")
        target = feature_dir / "workflow-state.md"
        diagnostics = _validation_diagnostics(project_root, feature_dir, target, command_name)
        if not target.exists():
            return HookResult(
                event=WORKFLOW_STATE_VALIDATE,
                status="blocked",
                severity="critical",
                errors=[f"workflow-state.md is missing at {target}"],
                data={
                    "validated_path": str(target.resolve()),
                    "lane_context": diagnostics,
                    "autofix": _autofix_metadata(feature_dir, command_name, _autofix_sections_for_command(command_name)),
                },
            )
        checkpoint = serialize_workflow_state(target)
        expected_command, expected_phase = EXPECTED_WORKFLOW_STATE[command_name]
        errors: list[str] = []
        if checkpoint["active_command"] != expected_command:
            errors.append(
                f"active_command mismatch: expected {expected_command}, got {checkpoint['active_command'] or 'missing'}"
            )
        if command_name == "specify":
            required_fixed_fields = (
                "current_stage",
                "current_domain",
                "next_action",
                "blocker_reason",
                "final_handoff_decision",
            )
            fixed_lifecycle_markers = (
                "current_stage",
                "current_domain",
                "blocker_reason",
                "final_handoff_decision",
            )
            uses_fixed_lifecycle = any(str(checkpoint.get(field) or "").strip() for field in fixed_lifecycle_markers)
            if uses_fixed_lifecycle:
                for field in required_fixed_fields:
                    if not str(checkpoint.get(field) or "").strip():
                        errors.append(f"workflow-state is missing Fixed Lifecycle State field: {field}")
            elif checkpoint["phase_mode"] != expected_phase:
                errors.append(
                    f"phase_mode mismatch: expected {expected_phase}, got {checkpoint['phase_mode'] or 'missing'}"
                )
        elif checkpoint["phase_mode"] != expected_phase:
            errors.append(
                f"phase_mode mismatch: expected {expected_phase}, got {checkpoint['phase_mode'] or 'missing'}"
            )
        if not checkpoint["allowed_artifact_writes"]:
            errors.append("workflow-state is missing allowed_artifact_writes")
        if not checkpoint["forbidden_actions"]:
            errors.append("workflow-state is missing forbidden_actions")
        if not checkpoint["authoritative_files"]:
            errors.append("workflow-state is missing authoritative_files")
        if not checkpoint["next_command"]:
            errors.append("workflow-state is missing next_command")
        if errors:
            if autofix:
                snippet = _autofix_sections_for_command(command_name)
                content = target.read_text(encoding="utf-8")
                if snippet.strip() not in content:
                    updated = content.rstrip() + "\n\n" + snippet
                    target.write_text(updated.rstrip() + "\n", encoding="utf-8")
                repaired_checkpoint = serialize_workflow_state(target)
                return HookResult(
                    event=WORKFLOW_STATE_VALIDATE,
                    status="repaired",
                    severity="warning",
                    warnings=["workflow-state.md missing required contract sections; autofix appended defaults"],
                    writes={"workflow_state": str(target.resolve())},
                    data={
                        "checkpoint": repaired_checkpoint,
                        "validated_path": str(target.resolve()),
                        "lane_context": diagnostics,
                        "autofix": _autofix_metadata(feature_dir, command_name, snippet),
                    },
                )
            return HookResult(
                event=WORKFLOW_STATE_VALIDATE,
                status="blocked",
                severity="critical",
                errors=errors,
                data={
                    "checkpoint": checkpoint,
                    "validated_path": str(target.resolve()),
                    "lane_context": diagnostics,
                    "autofix": _autofix_metadata(feature_dir, command_name, _autofix_sections_for_command(command_name)),
                },
            )
        return HookResult(
            event=WORKFLOW_STATE_VALIDATE,
            status="ok",
            severity="info",
            data={
                "checkpoint": checkpoint,
                "validated_path": str(target.resolve()),
                "lane_context": diagnostics,
            },
        )

    if command_name == "implement":
        feature_dir = _required_path(project_root, payload, "feature_dir")
        target = feature_dir / "implement-tracker.md"
        if not target.exists():
            return HookResult(
                event=WORKFLOW_STATE_VALIDATE,
                status="blocked",
                severity="critical",
                errors=[f"implement-tracker.md is missing at {target}"],
            )
        checkpoint = serialize_implement_tracker(target)
        errors = []
        if not checkpoint["status"]:
            errors.append("implement-tracker is missing frontmatter status")
        if not checkpoint["next_action"]:
            errors.append("implement-tracker is missing next_action")
        if errors:
            implementation_review = _implementation_review_metadata(feature_dir)
            return HookResult(
                event=WORKFLOW_STATE_VALIDATE,
                status="blocked",
                severity="critical",
                errors=errors,
                data={"checkpoint": checkpoint, "implementation_review": implementation_review},
            )
        implementation_review = _implementation_review_metadata(feature_dir)
        return HookResult(
            event=WORKFLOW_STATE_VALIDATE,
            status="ok",
            severity="info",
            data={"checkpoint": checkpoint, "implementation_review": implementation_review},
        )

    if command_name == "quick":
        workspace = _required_path(project_root, payload, "workspace")
        target = workspace / "STATUS.md"
        if not target.exists():
            return HookResult(
                event=WORKFLOW_STATE_VALIDATE,
                status="blocked",
                severity="critical",
                errors=[f"STATUS.md is missing at {target}"],
            )
        checkpoint = serialize_quick_status(target)
        errors = []
        if not checkpoint["status"]:
            errors.append("quick STATUS.md is missing frontmatter status")
        if not checkpoint["next_action"]:
            errors.append("quick STATUS.md is missing next_action")
        if errors:
            return HookResult(
                event=WORKFLOW_STATE_VALIDATE,
                status="blocked",
                severity="critical",
                errors=errors,
                data={"checkpoint": checkpoint},
            )
        return HookResult(
            event=WORKFLOW_STATE_VALIDATE,
            status="ok",
            severity="info",
            data={"checkpoint": checkpoint},
        )

    if command_name == "debug":
        session_file = _required_path(project_root, payload, "session_file")
        if not session_file.exists():
            return HookResult(
                event=WORKFLOW_STATE_VALIDATE,
                status="blocked",
                severity="critical",
                errors=[f"debug session file is missing at {session_file}"],
            )
        checkpoint = serialize_debug_session(session_file)
        return HookResult(
            event=WORKFLOW_STATE_VALIDATE,
            status="ok",
            severity="info",
            data={"checkpoint": checkpoint},
        )

    raise QualityHookError(f"unsupported command_name '{command_name}' for workflow.state.validate")


def _required_path(project_root: Path, payload: dict[str, object], key: str) -> Path:
    raw = str(payload.get(key) or "").strip()
    if not raw:
        raise QualityHookError(f"{key} is required")
    path = Path(raw)
    if not path.is_absolute():
        path = (project_root / path).resolve()
    return path


def _implementation_review_metadata(feature_dir: Path) -> dict[str, str]:
    review_dir = feature_dir / "implementation-review"
    return {
        "ledger": str((review_dir / "ledger.json").resolve()),
        "branch_review": str((review_dir / "branch-review.md").resolve()),
    }


def _autofix_sections_for_command(command_name: str) -> str:
    defaults: dict[str, dict[str, object]] = {
        "specify": {
            "allowed": [
                "spec.md",
                "alignment.md",
                "context.md",
                "references.md",
                "specify-draft.md",
                "workflow-state.md",
                "checklists/requirements.md",
            ],
            "forbidden": [
                "edit source code",
                "edit tests",
                "fix build/tooling",
                "implement behavior",
                "run implementation-oriented fix loops",
            ],
            "authoritative": [
                "spec.md",
                "alignment.md",
                "context.md",
                "references.md",
                "specify-draft.md",
            ],
            "next_command": "/sp.plan",
        },
        "clarify": {
            "allowed": [
                "spec.md",
                "alignment.md",
                "context.md",
                "references.md",
                "clarification/handoffs/*.json",
                "clarification/evidence-index.json",
                "clarification/checkpoints.ndjson",
                "workflow-state.md",
            ],
            "forbidden": [
                "edit source code",
                "edit tests",
                "fix build/tooling",
                "implement behavior",
                "run implementation-oriented fix loops",
            ],
            "authoritative": [
                "spec.md",
                "alignment.md",
                "context.md",
                "references.md",
                "clarification/handoffs/*.json",
                "clarification/evidence-index.json",
            ],
            "next_command": "/sp.plan",
        },
        "deep-research": {
            "allowed": ["deep-research.md", "research-spikes/", "alignment.md", "context.md", "references.md", "workflow-state.md"],
            "forbidden": [
                "edit production source code",
                "edit tests",
                "fix build/tooling",
                "implement behavior",
                "commit prototype code as production",
            ],
            "authoritative": ["spec.md", "alignment.md", "context.md", "references.md", "deep-research.md"],
            "next_command": "/sp.plan",
        },
        "plan": {
            "allowed": [
                "plan.md",
                "research.md",
                "data-model.md",
                "contracts/",
                "quickstart.md",
                "plan-contract.json",
                "planning/handoffs/*.json",
                "planning/evidence-index.json",
                "planning/checkpoints.ndjson",
                "workflow-state.md",
            ],
            "forbidden": ["edit source code", "edit tests", "implement behavior", "start execution from plan artifacts"],
            "authoritative": [
                "spec.md",
                "alignment.md",
                "context.md",
                "plan.md",
                "research.md",
                "plan-contract.json",
                "planning/handoffs/*.json",
                "planning/evidence-index.json",
            ],
            "next_command": "/sp.tasks",
        },
        "tasks": {
            "allowed": [
                "tasks.md",
                "handoff-to-tasks.json",
                "task-index.json",
                "task-packets/*.json",
                "task-generation/handoffs/*.json",
                "task-generation/evidence-index.json",
                "task-generation/checkpoints.ndjson",
                "workflow-state.md",
            ],
            "forbidden": ["edit source code", "edit tests", "implement behavior", "start execution from task-generation artifacts"],
            "authoritative": [
                "spec.md",
                "alignment.md",
                "context.md",
                "plan.md",
                "tasks.md",
                "handoff-to-tasks.json",
                "task-index.json",
                "task-packets/*.json",
                "task-generation/handoffs/*.json",
                "task-generation/evidence-index.json",
            ],
            "next_command": "/sp.implement",
        },
        "analyze": {
            "allowed": ["workflow-state.md"],
            "forbidden": ["edit source code", "edit tests", "edit planning artifacts", "start implementation before the gate is cleared"],
            "authoritative": ["spec.md", "plan.md", "tasks.md", "workflow-state.md"],
            "next_command": "/sp.implement",
        },
        "constitution": {
            "allowed": ["workflow-state.md"],
            "forbidden": ["edit source code"],
            "authoritative": ["workflow-state.md"],
            "next_command": "/sp.specify",
        },
        "prd": {
            "allowed": ["workflow-state.md"],
            "forbidden": ["edit source code"],
            "authoritative": ["workflow-state.md"],
            "next_command": "/sp.prd",
        },
        "prd-scan": {
            "allowed": ["workflow-state.md"],
            "forbidden": ["edit source code"],
            "authoritative": ["workflow-state.md"],
            "next_command": "/sp.prd-build",
        },
        "prd-build": {
            "allowed": ["workflow-state.md"],
            "forbidden": ["edit source code"],
            "authoritative": ["workflow-state.md"],
            "next_command": "/sp.prd-build",
        },
    }
    config = defaults[command_name]
    allowed = "\n".join(f"- {item}" for item in config["allowed"])
    forbidden = "\n".join(f"- {item}" for item in config["forbidden"])
    authoritative = "\n".join(f"- {item}" for item in config["authoritative"])
    next_command = str(config["next_command"])
    clean_tasks_handoff = ""
    if command_name == "tasks":
        clean_tasks_handoff = (
            "## Fixed Lifecycle State\n\n"
            "- current_stage: `task-generation`\n"
            "- current_domain: `none`\n"
            "- next_action: `hand off to implement`\n"
            "- blocker_reason: `None`\n"
            "- final_handoff_decision: `/sp.implement`\n\n"
            "## Analyze Gate\n\n"
            "- gate_status: `cleared`\n"
            "- gate_cycle: `0`\n"
            "- highest_invalid_stage: `none`\n"
            "- blocker_bundle:\n"
            "  - none\n"
            "- blocker_attribution_values: `none`\n\n"
            "## Reopen Contract\n\n"
            "- reopen_source: `none`\n"
            "- reopen_target: `none`\n"
            "- reopen_reason: `none`\n\n"
            "## Handoff Files\n\n"
            "- handoff_to_implement: `handoff-to-implement.json`\n\n"
        )
    return (
        f"{clean_tasks_handoff}"
        "## Allowed Artifact Writes\n\n"
        f"{allowed}\n\n"
        "## Forbidden Actions\n\n"
        f"{forbidden}\n\n"
        "## Authoritative Files\n\n"
        f"{authoritative}\n\n"
        "## Next Command\n\n"
        f"- `{next_command}`\n"
    )


def _autofix_metadata(feature_dir: Path, command_name: str, snippet: str) -> dict[str, object]:
    return {
        "available": True,
        "command": f'specify hook validate-state --command {command_name} --feature-dir "{feature_dir}" --autofix',
        "snippet": snippet,
    }


def _validation_diagnostics(project_root: Path, feature_dir: Path, target: Path, command_name: str) -> dict[str, object]:
    lane = next(
        (
            record
            for record in iter_lane_records(project_root)
            if (project_root / record.feature_dir).resolve() == feature_dir.resolve()
        ),
        None,
    )
    if lane is None:
        return {
            "resolved_from": "feature_dir",
            "command_name": command_name,
        }
    worktree_relative = Path(lane.worktree_path) / Path(lane.feature_dir) / "workflow-state.md"
    return {
        "resolved_from": "feature_dir+lane-record",
        "command_name": command_name,
        "lane_id": lane.lane_id,
        "feature_dir": lane.feature_dir,
        "worktree_path": lane.worktree_path,
        "worktree_state_path": str((project_root / worktree_relative).resolve()).replace("\\", "/"),
        "lane_record": asdict(lane),
        "validated_path": str(target.resolve()),
    }
