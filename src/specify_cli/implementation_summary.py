"""User-facing closeout summaries for reviewed implementations."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from specify_cli.agent_api import validate_workflow_blocker_payload
from specify_cli.atomic_io import atomic_write_text
from specify_cli.execution.implementation_review import (
    branch_review_path,
    ledger_path,
    task_review_path,
)
from specify_cli.implement_audit import _parse_tasks
from specify_cli.launcher import render_command


SUMMARY_FILENAME = "implementation-summary.md"
COMPARISON_COMMANDS = [
    "git status --short",
    "git diff --stat HEAD",
    "git diff --name-status HEAD",
]


def _resolve_project_feature_dir(project_root: Path, feature_dir: Path) -> Path:
    root = project_root.resolve(strict=False)
    resolved = (
        feature_dir.resolve(strict=False)
        if feature_dir.is_absolute()
        else (root / feature_dir).resolve(strict=False)
    )
    try:
        relative = resolved.relative_to(root)
    except ValueError as exc:
        raise ValueError("feature_dir must stay inside the current project") from exc
    if not relative.parts:
        raise ValueError("feature_dir must identify a directory below the project root")
    return resolved


def build_implementation_summary(
    project_root: Path,
    feature_dir: Path,
    *,
    write_report: bool = True,
) -> dict[str, Any]:
    """Build and optionally write a stable user-facing implementation summary."""

    root = project_root.resolve()
    resolved_feature_dir = _resolve_project_feature_dir(root, feature_dir)
    report_path = resolved_feature_dir / SUMMARY_FILENAME
    worker_results = _load_worker_results(resolved_feature_dir)
    tasks = _parse_tasks(resolved_feature_dir / "tasks.md")

    completed_work = _completed_work(tasks, worker_results, root, resolved_feature_dir)
    changed_from_results = _changed_paths_from_results(worker_results)
    verification_evidence = _verification_evidence(worker_results)
    git_comparison = _git_comparison(
        root,
        excluded_paths={
            _display_path(report_path, root),
            _display_path(resolved_feature_dir / "human-acceptance.json", root),
        },
    )
    behavior_surfaces = _behavior_surfaces(changed_from_results)
    review_artifacts = _review_artifacts(resolved_feature_dir, tasks, root)
    system_review = _system_review_summary(resolved_feature_dir, root)
    blockers = _implementation_blockers(resolved_feature_dir)
    human_needed_checks = [
        str(item["summary"])
        for item in blockers
        if item.get("human_action_required") is True
    ]

    payload: dict[str, Any] = {
        "status": "blocked" if blockers else "ok",
        "feature_dir": _display_path(resolved_feature_dir, root),
        "report_path": _display_path(report_path, root),
        "completed_work": completed_work,
        "changed_paths": {
            "from_worker_results": changed_from_results,
            "from_git_working_tree": git_comparison["changed_paths"],
        },
        "changed_behavior_surfaces": behavior_surfaces,
        "review_artifacts": review_artifacts,
        "system_review": system_review,
        "verification_evidence": verification_evidence,
        "baseline_comparison": {
            "method": "working_tree_vs_head",
            "baseline": "HEAD",
            "commands": COMPARISON_COMMANDS,
            "git_available": git_comparison["git_available"],
            "status_short": git_comparison["status_short"],
            "name_status": git_comparison["name_status"],
        },
        "human_needed_checks": human_needed_checks,
        "blockers": blockers,
        "unresolved_gaps": [str(item["summary"]) for item in blockers],
        "human_acceptance": {
            "state_path": _display_path(
                resolved_feature_dir / "human-acceptance.json", root
            ),
            "next_command": "sp-accept (Classic) or spx-accept (Advanced)",
            "boundary": (
                "System review has independently exercised the implementation from real "
                "entrypoints; human product acceptance remains a separate workflow."
            ),
        },
    }
    if write_report:
        atomic_write_text(report_path, _render_markdown(payload))
    return payload


def _implementation_resume_argv(feature_dir: Path) -> list[str]:
    return [
        "specify",
        "implement",
        "resume-audit",
        "--feature-dir",
        str(feature_dir),
        "--format",
        "json",
    ]


def implementation_closeout_blockers(
    feature_dir: Path,
    *,
    resume_audit: dict[str, Any] | None = None,
    hook_errors: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Return canonical blockers for an implementation closeout stop."""

    blockers = _implementation_blockers(feature_dir)
    resume_argv = _implementation_resume_argv(feature_dir)
    if hook_errors:
        evidence = [str(item).strip() for item in hook_errors if str(item).strip()]
        blockers.append(
            _implementation_gate_blocker(
                blocker_id="IMPLEMENT-SESSION-STATE",
                category="artifact-or-state",
                summary="Implementation session state is not valid for closeout.",
                evidence=evidence
                or ["workflow.session_state.validate returned blocked"],
                exact_next_action="Repair the recorded implementation session state, then rerun the resume audit.",
                unblock_criteria="The session-state hook passes and the implementation resume audit trusts a terminal state.",
                resume_argv=resume_argv,
            )
        )
    if resume_audit is not None and (
        resume_audit.get("status") in {"fail", "conflict"}
        or not resume_audit.get("trusted_terminal_state", False)
    ):
        evidence = [
            str(item).strip()
            for item in resume_audit.get("open_gaps", [])
            if str(item).strip()
        ]
        exact_next_action = str(
            resume_audit.get("recommended_next_action")
            or "Resume implementation and close every recorded evidence gap."
        )
        blockers.append(
            _implementation_gate_blocker(
                blocker_id="IMPLEMENT-RESUME-AUDIT",
                category=(
                    "conflict-or-drift"
                    if resume_audit.get("status") == "conflict"
                    else "workflow-validation"
                ),
                summary="Implementation closeout evidence is incomplete or non-terminal.",
                evidence=evidence
                or ["resume audit does not trust a terminal implementation state"],
                exact_next_action=exact_next_action,
                unblock_criteria="The resume audit returns status=pass with trusted_terminal_state=true and no open gaps.",
                resume_argv=resume_argv,
            )
        )
    return blockers


def _implementation_gate_blocker(
    *,
    blocker_id: str,
    category: str,
    summary: str,
    evidence: list[str],
    exact_next_action: str,
    unblock_criteria: str,
    resume_argv: list[str],
) -> dict[str, Any]:
    resume_command = render_command(tuple(resume_argv))
    return {
        "version": 1,
        "blocker_id": blocker_id,
        "code": "implementation-closeout-blocked",
        "workflow": "sp-implement|spx-implement",
        "stage": "implementation closeout",
        "category": category,
        "owner": "agent",
        "summary": summary,
        "details": "The deterministic closeout gate cannot claim implementation completion from the current recorded evidence.",
        "evidence": evidence,
        "attempted_recovery": [
            {
                "action": "Run the implementation session-state and resume-audit checks.",
                "result": "The closeout prerequisites remain unsatisfied.",
            }
        ],
        "exact_next_action": exact_next_action,
        "unblock_criteria": unblock_criteria,
        "affected_scope": ["implementation closeout", "human acceptance handoff"],
        "can_continue": True,
        "human_action_required": False,
        "human_action_guide": None,
        "resume": {
            "instruction": f"Run the exact resume audit command: {resume_command}",
            "command": resume_command,
            "argv": resume_argv,
        },
    }


def _load_worker_results(feature_dir: Path) -> list[dict[str, Any]]:
    result_dir = feature_dir / "worker-results"
    if not result_dir.exists():
        return []
    results: list[dict[str, Any]] = []
    for result_path in sorted(result_dir.glob("*.json")):
        try:
            payload = json.loads(result_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            results.append(
                {
                    "task_id": result_path.stem.upper(),
                    "status": "invalid-json",
                    "summary": "Worker result JSON could not be parsed.",
                    "path": result_path,
                    "validation_results": [],
                    "changed_files": [],
                }
            )
            continue
        if isinstance(payload, dict):
            payload["path"] = result_path
            results.append(payload)
    return results


def _implementation_blockers(feature_dir: Path) -> list[dict[str, Any]]:
    lifecycle_dir = feature_dir / "implementation-review" / "tasks"
    if not lifecycle_dir.is_dir():
        return []
    blockers: list[dict[str, Any]] = []
    for lifecycle_path in sorted(lifecycle_dir.glob("*.json")):
        try:
            payload = json.loads(lifecycle_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(payload, dict):
            continue
        task_id = str(payload.get("task_id") or lifecycle_path.stem).upper()
        for index, raw_blocker in enumerate(payload.get("blockers") or [], start=1):
            if isinstance(raw_blocker, dict):
                source_errors = _lifecycle_blocker_source_errors(raw_blocker)
                if source_errors:
                    blockers.append(
                        _invalid_lifecycle_blocker_detail(
                            feature_dir,
                            task_id,
                            index,
                            source_errors,
                        )
                    )
                    continue
                detail = _lifecycle_blocker_detail(
                    feature_dir, task_id, index, raw_blocker
                )
                output_errors = validate_workflow_blocker_payload(detail)
                blockers.append(
                    detail
                    if not output_errors
                    else _invalid_lifecycle_blocker_detail(
                        feature_dir,
                        task_id,
                        index,
                        [f"rendered blocker: {error}" for error in output_errors],
                    )
                )

        verification = payload.get("ui_verification")
        if isinstance(verification, dict) and verification.get("applicable") is True:
            fidelity_status = (
                str(verification.get("fidelity_status") or "").lower().replace("_", "-")
            )
            visual_status = (
                str(verification.get("visual_comparison") or "")
                .lower()
                .replace("_", "-")
            )
            if fidelity_status == "pending-human-review" or visual_status in {
                "needs-human-review",
                "pending-human-review",
            }:
                review_ref = str(verification.get("human_review_ref") or "not recorded")
                blockers.append(
                    _ui_human_blocker(feature_dir, task_id, review_ref)
                )
    return blockers


def _lifecycle_blocker_source_errors(blocker: dict[str, Any]) -> list[str]:
    required_fields = (
        "classification",
        "owner",
        "evidence",
        "exact_next_action",
        "approval_question",
        "unblock_criteria",
        "implementation_can_continue",
        "completion_impact",
    )
    errors = [
        f"missing required field: {field}"
        for field in required_fields
        if field not in blocker
    ]
    classification = str(blocker.get("classification") or "").strip()
    if classification not in {
        "technical",
        "external",
        "human-action",
        "verification_policy",
        "project_cognition_readiness",
        "baseline_timeout",
    }:
        errors.append(f"invalid classification: {classification or 'empty'}")
    owner = str(blocker.get("owner") or "").strip()
    if owner not in {"agent", "user", "maintainer", "external-system"}:
        errors.append(f"invalid owner: {owner or 'empty'}")
    completion_impact = str(blocker.get("completion_impact") or "").strip()
    if completion_impact not in {
        "mandatory_for_completion",
        "optional_cleanup",
        "external_baseline_maintenance",
        "follow_up_risk",
    }:
        errors.append(f"invalid completion_impact: {completion_impact or 'empty'}")
    evidence = blocker.get("evidence")
    if isinstance(evidence, str):
        evidence_valid = bool(evidence.strip())
    elif isinstance(evidence, list):
        evidence_valid = bool(evidence) and all(
            isinstance(item, str) and bool(item.strip()) for item in evidence
        )
    else:
        evidence_valid = False
    if not evidence_valid:
        errors.append("evidence must be a non-empty string or string list")
    for field in ("exact_next_action", "unblock_criteria"):
        if not isinstance(blocker.get(field), str) or not str(blocker[field]).strip():
            errors.append(f"{field} must be a non-empty string")
    if not isinstance(blocker.get("implementation_can_continue"), bool):
        errors.append("implementation_can_continue must be a boolean")
    approval_question = blocker.get("approval_question")
    if approval_question is not None and not isinstance(approval_question, str):
        errors.append("approval_question must be a string or null")
    if owner in {"user", "maintainer"} and not str(approval_question or "").strip():
        errors.append(f"approval_question is required for owner {owner}")
    return errors


def _invalid_lifecycle_blocker_detail(
    feature_dir: Path,
    task_id: str,
    index: int,
    errors: list[str],
) -> dict[str, Any]:
    resume_argv = _implementation_resume_argv(feature_dir)
    resume_command = render_command(tuple(resume_argv))
    return {
        "version": 1,
        "blocker_id": f"{task_id}-B{index:02d}",
        "code": "invalid-task-lifecycle-blocker",
        "workflow": "sp-implement|spx-implement",
        "stage": f"task {task_id}",
        "category": "artifact-or-state",
        "owner": "agent",
        "summary": f"{task_id}: task lifecycle blocker state is invalid.",
        "details": (
            "The lifecycle record cannot be trusted or forwarded until its blocker "
            "entry satisfies the deterministic contract."
        ),
        "evidence": [f"blocker {index}: {error}" for error in errors]
        or [f"blocker {index}: lifecycle blocker validation failed"],
        "attempted_recovery": [
            {
                "action": "Validate the task lifecycle blocker before closeout.",
                "result": "The recorded blocker failed its required field contract.",
            }
        ],
        "exact_next_action": (
            f"Repair blocker {index} in the {task_id} task lifecycle record, then "
            "rerun the implementation resume audit."
        ),
        "approval_question": None,
        "unblock_criteria": (
            "Every task lifecycle blocker has a supported classification and owner, "
            "non-empty evidence and recovery fields, and valid typed values."
        ),
        "affected_scope": [task_id, "implementation closeout"],
        "can_continue": True,
        "human_action_required": False,
        "human_action_guide": None,
        "resume": {
            "instruction": f"Run the exact resume audit command: {resume_command}",
            "command": resume_command,
            "argv": resume_argv,
        },
    }


def _lifecycle_blocker_detail(
    feature_dir: Path,
    task_id: str,
    index: int,
    blocker: dict[str, Any],
) -> dict[str, Any]:
    classification = str(blocker.get("classification") or "technical")
    owner = str(blocker.get("owner") or "agent")
    evidence_value = blocker.get("evidence")
    evidence = (
        [str(item) for item in evidence_value if str(item).strip()]
        if isinstance(evidence_value, list)
        else [str(evidence_value or "No evidence recorded")]
    )
    next_action = str(
        blocker.get("exact_next_action") or "Resolve the recorded task blocker"
    )
    unblock_criteria = str(blocker.get("unblock_criteria") or "Task validation passes")
    human_required = owner in {"user", "maintainer"} or classification == "human-action"
    category = {
        "technical": "technical-failure",
        "external": "external-system",
        "human-action": "human-review",
        "verification_policy": "workflow-validation",
        "project_cognition_readiness": "project-cognition",
        "baseline_timeout": "timeout",
    }.get(classification, "workflow-validation")
    combined = " ".join(
        [classification, next_action, unblock_criteria, *evidence]
    ).lower()
    protected_ci = any(
        term in combined
        for term in (
            "pipeline",
            "protected ci",
            "ci job",
            "github actions",
            "gitlab ci",
        )
    )
    if human_required and protected_ci:
        category = "external-system"
    resume_argv = _implementation_resume_argv(feature_dir)
    resume_command = render_command(tuple(resume_argv))
    detail: dict[str, Any] = {
        "version": 1,
        "blocker_id": f"{task_id}-B{index:02d}",
        "workflow": "sp-implement|spx-implement",
        "stage": f"task {task_id}",
        "category": category,
        "owner": owner,
        "summary": f"{task_id}: {next_action}",
        "details": f"Task lifecycle classification is {classification}.",
        "evidence": evidence,
        "attempted_recovery": [],
        "exact_next_action": next_action,
        "approval_question": blocker.get("approval_question"),
        "unblock_criteria": unblock_criteria,
        "affected_scope": [task_id, "implementation closeout"],
        "can_continue": bool(blocker.get("implementation_can_continue")),
        "human_action_required": human_required,
        "human_action_guide": None,
        "resume": {
            "instruction": (
                f"After returning the requested evidence for {task_id}, run the "
                f"exact implementation resume audit: {resume_command}"
            ),
            "command": resume_command,
            "argv": resume_argv,
        },
    }
    if human_required:
        detail["human_action_guide"] = _human_action_guide(
            task_id,
            next_action,
            unblock_criteria,
            evidence,
            protected_ci=category == "external-system" and protected_ci,
        )
    return detail


def _human_action_guide(
    task_id: str,
    next_action: str,
    unblock_criteria: str,
    evidence: list[str],
    *,
    protected_ci: bool,
) -> dict[str, Any]:
    if protected_ci:
        return {
            "goal": f"Obtain the protected CI result required to unblock {task_id}.",
            "why_human": "The pipeline or protected job requires repository authority or an external UI the agent does not control.",
            "prerequisites": [
                "An account with access to the repository pipeline page",
                "The exact repository, branch, and commit SHA named by the blocker evidence",
                "Explicit approval before any push, pipeline trigger, deployment, or manual job",
            ],
            "safety_notes": [
                "Do not paste tokens, cookies, private keys, or credential screenshots into chat.",
                "Do not run release, deploy, destructive, or unrelated manual jobs.",
                "If the repository, branch, commit, or required job is ambiguous, stop and return that ambiguity.",
            ],
            "steps": [
                {
                    "order": 1,
                    "title": "Confirm the exact revision",
                    "action": "In the repository checkout, record the current branch and commit SHA; compare them with the blocker evidence before opening CI.",
                    "command": "git branch --show-current; git rev-parse HEAD; git status --short",
                    "expected_result": "The intended branch and commit are unambiguous and no unexpected local changes will be sent.",
                    "if_failed": "Do not commit or push. Return the command output with secrets and private paths redacted.",
                },
                {
                    "order": 2,
                    "title": "Open the matching pipeline",
                    "action": "Open the repository's CI/Pipelines page and select the pipeline whose branch and commit SHA exactly match step 1. Trigger or push only when the recorded approval explicitly authorizes it.",
                    "command": None,
                    "expected_result": "The pipeline page shows the same repository, branch, and commit SHA.",
                    "if_failed": "Do not use a similar branch or a different repository. Return `matching pipeline not found` plus the sanitized repository/branch/SHA shown.",
                },
                {
                    "order": 3,
                    "title": "Run only the required protected check",
                    "action": next_action,
                    "command": None,
                    "expected_result": f"The named check reaches a terminal state satisfying: {unblock_criteria}",
                    "if_failed": "Do not retry blindly. Capture the failed job name, terminal status, and the smallest relevant sanitized log excerpt.",
                },
                {
                    "order": 4,
                    "title": "Verify and return the result",
                    "action": "Refresh the pipeline once and confirm its commit SHA and required-job terminal status have not changed.",
                    "command": None,
                    "expected_result": "The pipeline URL/ID, commit SHA, and required job status form one consistent evidence set.",
                    "if_failed": "Return the inconsistency instead of declaring success.",
                },
            ],
            "verification": [unblock_criteria],
            "evidence_to_return": [
                "Pipeline URL or ID",
                "Repository, branch, and commit SHA",
                "Required job names and terminal statuses",
                "For failure only: a short sanitized error excerpt",
            ],
            "resume_instruction": f"Return the evidence and resume {task_id} with sp-implement or spx-implement; do not start a new feature workflow.",
        }

    return {
        "goal": next_action,
        "why_human": "The task lifecycle assigns this action to a user or maintainer boundary.",
        "prerequisites": [
            "Access to the target named in the blocker evidence",
            *evidence,
        ],
        "safety_notes": [
            "Do not share credentials or secrets; stop if the target or requested authority is ambiguous."
        ],
        "steps": [
            {
                "order": 1,
                "title": "Confirm the target",
                "action": "Match the repository, artifact, environment, or decision target against the blocker evidence.",
                "command": None,
                "expected_result": "There is exactly one matching target.",
                "if_failed": "Return the conflicting target names and do not make a change.",
            },
            {
                "order": 2,
                "title": "Perform the requested action",
                "action": next_action,
                "command": None,
                "expected_result": unblock_criteria,
                "if_failed": "Capture the visible status and a sanitized error; do not broaden the action.",
            },
            {
                "order": 3,
                "title": "Verify",
                "action": f"Recheck the target independently and confirm: {unblock_criteria}",
                "command": None,
                "expected_result": unblock_criteria,
                "if_failed": "Return the observed result instead of approving completion.",
            },
        ],
        "verification": [unblock_criteria],
        "evidence_to_return": [
            "The decision or terminal status",
            "A sanitized URL/ID, screenshot, or output proving it",
        ],
        "resume_instruction": f"Return the evidence and resume {task_id} with sp-implement or spx-implement.",
    }


def _ui_human_blocker(
    feature_dir: Path,
    task_id: str,
    review_ref: str,
) -> dict[str, Any]:
    summary = f"{task_id}: UI visual approval is pending; review target: {review_ref}"
    resume_argv = _implementation_resume_argv(feature_dir)
    resume_command = render_command(tuple(resume_argv))
    return {
        "version": 1,
        "blocker_id": f"{task_id}-UI-REVIEW",
        "workflow": "sp-implement|spx-implement",
        "stage": f"task {task_id} UI acceptance",
        "category": "human-review",
        "owner": "user",
        "summary": summary,
        "details": "Automated visual comparison could not close the required UI acceptance gate.",
        "evidence": [review_ref],
        "attempted_recovery": [],
        "exact_next_action": f"Review the real UI against the approved design evidence in {review_ref}.",
        "approval_question": f"Does {task_id} meet the approved visual and interaction contract for every required viewport and state?",
        "unblock_criteria": "A human pass/reject decision and review evidence are returned for every required viewport and state.",
        "affected_scope": [task_id, "UI acceptance", "implementation closeout"],
        "can_continue": False,
        "human_action_required": True,
        "human_action_guide": {
            "goal": f"Accept or reject the visual and interaction fidelity of {task_id}.",
            "why_human": "The required comparison is subjective or the agent cannot inspect the real rendered surface in this environment.",
            "prerequisites": [
                f"Review packet: {review_ref}",
                "Access to the real application entry point named by that packet",
                "The approved design/reference inputs",
            ],
            "safety_notes": [
                "Review the real entry point, not an isolated mock.",
                "Do not approve a missing viewport/state or substitute passing tests for visual acceptance.",
            ],
            "steps": [
                {
                    "order": 1,
                    "title": "Open the review packet",
                    "action": f"Open {review_ref} and identify the real entry point, approved reference, viewport/state matrix, and must-preserve rules.",
                    "command": None,
                    "expected_result": "Every required viewport and state has a named target and comparison source.",
                    "if_failed": "Return `review packet incomplete` and list the missing entry point, reference, viewport, or state.",
                },
                {
                    "order": 2,
                    "title": "Run the real surface",
                    "action": "Use the run command in the review packet or implementation summary, open the real entry point, and reproduce each required state at its recorded viewport.",
                    "command": None,
                    "expected_result": "The real UI loads and each required state can be inspected.",
                    "if_failed": "Return the failing run command, viewport/state, and sanitized runtime error; do not approve from static files alone.",
                },
                {
                    "order": 3,
                    "title": "Compare and capture",
                    "action": "Compare layout, content, interaction, responsive behavior, and must-preserve details against the approved reference; capture one image per required viewport/state.",
                    "command": None,
                    "expected_result": "Each matrix entry has a pass or a concrete mismatch and a corresponding capture.",
                    "if_failed": "Record the exact mismatch and reject that matrix entry rather than averaging it into an overall pass.",
                },
                {
                    "order": 4,
                    "title": "Return the decision",
                    "action": "State PASS only if every required matrix entry passes; otherwise state REJECT and list each repair needed.",
                    "command": None,
                    "expected_result": "A clear PASS or REJECT decision is tied to the captured evidence.",
                    "if_failed": "Return `decision pending` and name the unresolved matrix entries.",
                },
            ],
            "verification": [
                "Every required viewport/state has a decision and capture",
                "PASS contains no unresolved must-preserve mismatch",
            ],
            "evidence_to_return": [
                "PASS or REJECT",
                "Viewport/state result list",
                "Capture paths or sanitized attachments",
                "Repair notes for every rejection",
            ],
            "resume_instruction": f"Return the review evidence and resume {task_id} with sp-implement or spx-implement.",
        },
        "resume": {
            "instruction": (
                f"After the human decision for {task_id} is returned, run the exact "
                f"implementation resume audit: {resume_command}"
            ),
            "command": resume_command,
            "argv": resume_argv,
        },
    }


def _completed_work(
    tasks: list[dict[str, Any]],
    worker_results: list[dict[str, Any]],
    project_root: Path,
    feature_dir: Path,
) -> list[dict[str, Any]]:
    by_task_id = {
        str(result.get("task_id") or "").upper(): result
        for result in worker_results
        if str(result.get("task_id") or "").strip()
    }
    completed: list[dict[str, Any]] = []
    for task in tasks:
        if not task.get("checked"):
            continue
        task_id = str(task.get("task_id") or "").upper()
        result = by_task_id.get(task_id, {})
        changed_files = _normalize_paths(
            result.get("changed_files") or result.get("changedFiles") or []
        )
        result_path = result.get("path")
        review_path = task_review_path(feature_dir, task_id)
        completed.append(
            {
                "task_id": task_id,
                "task": str(task.get("body") or "").strip(),
                "summary": str(result.get("summary") or task.get("body") or "").strip(),
                "result_status": str(result.get("status") or "missing-worker-result"),
                "result_path": _display_path(result_path, project_root)
                if isinstance(result_path, Path)
                else "",
                "review_artifacts": {
                    "task_review": _display_path(review_path, project_root)
                    if review_path.is_file()
                    else "",
                },
                "changed_files": changed_files,
            }
        )
    return completed


def _review_artifacts(
    feature_dir: Path,
    tasks: list[dict[str, Any]],
    project_root: Path,
) -> dict[str, Any]:
    review_ledger_path = ledger_path(feature_dir)
    review_branch_path = branch_review_path(feature_dir)
    task_reviews: dict[str, str] = {}
    for task in tasks:
        task_id = str(task.get("task_id") or "").upper()
        if not task_id:
            continue
        try:
            review_path = task_review_path(feature_dir, task_id)
        except ValueError:
            continue
        if review_path.is_file():
            task_reviews[task_id] = _display_path(review_path, project_root)
    system_review_path = feature_dir / "review-state.json"
    return {
        "ledger": _display_path(review_ledger_path, project_root)
        if review_ledger_path.is_file()
        else "",
        "branch_review": _display_path(review_branch_path, project_root)
        if review_branch_path.is_file()
        else "",
        "task_reviews": task_reviews,
        "system_review": _display_path(system_review_path, project_root)
        if system_review_path.is_file()
        else "",
        "system_review_evidence": _display_path(
            feature_dir / "review-evidence", project_root
        )
        if (feature_dir / "review-evidence").is_dir()
        else "",
    }


def _system_review_summary(feature_dir: Path, project_root: Path) -> dict[str, Any]:
    state_path = feature_dir / "review-state.json"
    if not state_path.is_file():
        return {"status": "missing", "state_path": "", "scenarios": [], "findings": []}
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {
            "status": "invalid",
            "state_path": _display_path(state_path, project_root),
            "scenarios": [],
            "findings": [],
        }
    scenarios = state.get("scenarios") if isinstance(state, dict) else []
    findings = state.get("findings") if isinstance(state, dict) else []
    return {
        "status": str(state.get("status") or "unknown") if isinstance(state, dict) else "invalid",
        "state_path": _display_path(state_path, project_root),
        "scenarios": [
            {
                "id": str(item.get("id") or ""),
                "title": str(item.get("title") or ""),
                "result": str(item.get("result") or ""),
            }
            for item in scenarios or []
            if isinstance(item, dict)
        ],
        "findings": [
            {
                "id": str(item.get("id") or ""),
                "summary": str(item.get("summary") or ""),
                "status": str(item.get("status") or ""),
            }
            for item in findings or []
            if isinstance(item, dict)
        ],
    }


def _changed_paths_from_results(worker_results: list[dict[str, Any]]) -> list[str]:
    paths: list[str] = []
    for result in worker_results:
        paths.extend(
            _normalize_paths(
                result.get("changed_files") or result.get("changedFiles") or []
            )
        )
    return sorted(set(paths))


def _verification_evidence(
    worker_results: list[dict[str, Any]],
) -> list[dict[str, str]]:
    evidence: list[dict[str, str]] = []
    seen: set[tuple[str, str, str]] = set()
    for result in worker_results:
        task_id = str(result.get("task_id") or "").upper()
        validations = (
            result.get("validation_results") or result.get("validationResults") or []
        )
        if not isinstance(validations, list):
            continue
        for item in validations:
            if isinstance(item, dict):
                command = str(item.get("command") or "").strip()
                status = str(item.get("status") or "").strip()
                output = str(item.get("output") or item.get("summary") or "").strip()
            else:
                command = str(item).strip()
                status = ""
                output = ""
            if not command and not output:
                continue
            key = (task_id, command, status)
            if key in seen:
                continue
            seen.add(key)
            evidence.append(
                {
                    "task_id": task_id,
                    "command": command,
                    "status": status,
                    "output": _single_line(output),
                }
            )
    return evidence


def _git_comparison(
    project_root: Path, *, excluded_paths: set[str] | None = None
) -> dict[str, Any]:
    status = _run_git(project_root, ["status", "--short"])
    name_status = _run_git(project_root, ["diff", "--name-status", "HEAD"])
    excluded = {path.replace("\\", "/") for path in (excluded_paths or set())}
    if excluded:
        status = _filter_git_output(status, excluded, short_status=True)
        name_status = _filter_git_output(name_status, excluded, short_status=False)
    changed_paths = _paths_from_git_status(status) if status is not None else []
    return {
        "git_available": status is not None and name_status is not None,
        "status_short": status.splitlines() if status else [],
        "name_status": name_status.splitlines() if name_status else [],
        "changed_paths": changed_paths,
    }


def _filter_git_output(
    output: str | None, excluded_paths: set[str], *, short_status: bool
) -> str | None:
    if output is None:
        return None
    kept: list[str] = []
    for line in output.splitlines():
        if short_status:
            path = line[3:].strip() if len(line) >= 4 else ""
        else:
            parts = line.split("\t")
            path = parts[-1].strip() if len(parts) >= 2 else ""
        if " -> " in path:
            path = path.split(" -> ", 1)[1].strip()
        if path.replace("\\", "/") not in excluded_paths:
            kept.append(line)
    return "\n".join(kept)


def _run_git(project_root: Path, args: list[str]) -> str | None:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=project_root,
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            check=False,
        )
    except (OSError, ValueError):
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def _paths_from_git_status(status_output: str | None) -> list[str]:
    paths: list[str] = []
    for raw in (status_output or "").splitlines():
        line = raw.rstrip()
        if len(line) < 4:
            continue
        path_part = line[3:].strip()
        if " -> " in path_part:
            path_part = path_part.split(" -> ", 1)[1].strip()
        if path_part:
            paths.append(path_part.replace("\\", "/"))
    return sorted(set(paths))


def _behavior_surfaces(paths: list[str]) -> list[dict[str, str]]:
    surfaces: list[dict[str, str]] = []
    for path in paths:
        surfaces.append({"path": path, "surface": _surface_for_path(path)})
    return surfaces


def _surface_for_path(path: str) -> str:
    lowered = path.lower()
    if (
        lowered.startswith("tests/")
        or "/tests/" in lowered
        or lowered.endswith("_test.py")
    ):
        return "tests"
    if lowered.startswith("templates/"):
        return "generated-workflow-template"
    if lowered.startswith("docs/") or lowered.endswith(".md"):
        return "docs"
    if lowered.endswith((".toml", ".json", ".yaml", ".yml", ".ini")):
        return "config-or-state"
    if "/api/" in lowered or lowered.endswith(("route.ts", "route.py")):
        return "api-or-route"
    if "cli" in lowered or lowered.endswith("__init__.py"):
        return "cli-or-command"
    return "source"


def _normalize_paths(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    paths: list[str] = []
    for item in value:
        if not isinstance(item, str):
            continue
        normalized = item.strip().replace("\\", "/")
        if normalized:
            paths.append(normalized)
    return paths


def _display_path(path: Path, project_root: Path) -> str:
    try:
        return path.resolve().relative_to(project_root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _single_line(text: str, *, limit: int = 180) -> str:
    compact = " ".join(text.split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3].rstrip() + "..."


def _render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Implementation Summary",
        "",
        f"- Feature dir: `{payload['feature_dir']}`",
        f"- Closeout status: `{payload['status']}`",
        "",
        "## What Changed",
        "",
    ]
    completed_work = payload.get("completed_work") or []
    if completed_work:
        for item in completed_work:
            lines.append(f"- `{item['task_id']}`: {item['summary'] or item['task']}")
            changed_files = item.get("changed_files") or []
            if changed_files:
                lines.append(
                    f"  - Files: {', '.join(f'`{path}`' for path in changed_files)}"
                )
            if item.get("result_path"):
                lines.append(f"  - Worker result: `{item['result_path']}`")
            review_artifacts = item.get("review_artifacts") or {}
            if review_artifacts.get("task_review"):
                lines.append(f"  - Task review: `{review_artifacts['task_review']}`")
    else:
        lines.append("- No checked tasks were found in `tasks.md`.")

    lines.extend(
        [
            "",
            "## Changed Paths",
            "",
            "### From Worker Results",
            "",
        ]
    )
    changed_paths = payload.get("changed_paths", {})
    worker_paths = changed_paths.get("from_worker_results") or []
    lines.extend(_path_lines(worker_paths))
    lines.extend(["", "### From Git Working Tree", ""])
    git_paths = changed_paths.get("from_git_working_tree") or []
    lines.extend(_path_lines(git_paths))

    lines.extend(["", "## Changed Behavior Surfaces", ""])
    surfaces = payload.get("changed_behavior_surfaces") or []
    if surfaces:
        for item in surfaces:
            lines.append(f"- `{item['path']}` -> {item['surface']}")
    else:
        lines.append("- No behavior surfaces were inferred from worker changed files.")

    lines.extend(["", "## Review Artifacts", ""])
    review_artifacts = payload.get("review_artifacts") or {}
    ledger = review_artifacts.get("ledger") or ""
    branch_review = review_artifacts.get("branch_review") or ""
    task_reviews = review_artifacts.get("task_reviews") or {}
    lines.append(f"- Ledger: `{ledger}`" if ledger else "- Ledger: None recorded.")
    lines.append(
        f"- Branch review: `{branch_review}`"
        if branch_review
        else "- Branch review: None recorded."
    )
    if task_reviews:
        for task_id, path in sorted(task_reviews.items()):
            lines.append(f"- `{task_id}` task review: `{path}`")
    else:
        lines.append("- Task reviews: None recorded.")
    if review_artifacts.get("system_review"):
        lines.append(f"- System review: `{review_artifacts['system_review']}`")
    if review_artifacts.get("system_review_evidence"):
        lines.append(
            f"- Integrated review evidence: `{review_artifacts['system_review_evidence']}`"
        )

    lines.extend(["", "## System Review", ""])
    system_review = payload.get("system_review") or {}
    lines.append(f"- Status: `{system_review.get('status', 'missing')}`")
    scenarios = system_review.get("scenarios") or []
    if scenarios:
        for scenario in scenarios:
            lines.append(
                f"- `{scenario.get('id', '')}`: {scenario.get('result', 'pending')} — "
                f"{scenario.get('title', '')}"
            )
    else:
        lines.append("- Required scenarios: None recorded.")
    findings = system_review.get("findings") or []
    if findings:
        for finding in findings:
            lines.append(
                f"- Finding `{finding.get('id', '')}`: {finding.get('status', 'open')} — "
                f"{finding.get('summary', '')}"
            )
    else:
        lines.append("- Blocking findings: None recorded.")

    lines.extend(["", "## How To Verify", ""])
    evidence = payload.get("verification_evidence") or []
    if evidence:
        for item in evidence:
            command = (
                item.get("command") or item.get("output") or "verification evidence"
            )
            status = item.get("status") or "recorded"
            task = item.get("task_id") or "task"
            lines.append(f"- `{command}` -> {status} ({task})")
    else:
        lines.append("- No worker validation evidence was recorded.")

    comparison = payload.get("baseline_comparison") or {}
    lines.extend(
        [
            "",
            "## Version Comparison",
            "",
            f"- Baseline: `{comparison.get('baseline', 'HEAD')}`",
            "- Run these commands to inspect the current implementation diff:",
        ]
    )
    for command in comparison.get("commands") or COMPARISON_COMMANDS:
        lines.append(f"  - `{command}`")
    status_lines = comparison.get("status_short") or []
    if status_lines:
        lines.extend(["", "Current `git status --short` snapshot:", "", "```text"])
        lines.extend(status_lines)
        lines.append("```")
    else:
        lines.append(
            "- No git working-tree changes were detected when this summary was generated."
        )

    lines.extend(["", "## Blockers", ""])
    blockers = [
        blocker
        for blocker in (payload.get("blockers") or [])
        if isinstance(blocker, dict)
    ]
    if blockers:
        for blocker in blockers:
            lines.extend(_render_blocker_detail(blocker))
    else:
        lines.append("- None recorded.")

    lines.extend(["", "## Human Checks Needed", ""])
    human_blockers = [
        blocker
        for blocker in (payload.get("blockers") or [])
        if isinstance(blocker, dict) and blocker.get("human_action_required") is True
    ]
    if human_blockers:
        for blocker in human_blockers:
            lines.extend(_render_human_blocker(blocker))
    else:
        lines.append("- None recorded.")

    acceptance = payload.get("human_acceptance") or {}
    lines.extend(
        [
            "",
            "## Human Product Acceptance",
            "",
            f"- State: `{acceptance.get('state_path', 'human-acceptance.json')}`",
            f"- Next workflow: `{acceptance.get('next_command', 'sp-accept or spx-accept')}`",
            f"- Boundary: {acceptance.get('boundary', 'Human acceptance is separate from technical closeout.')}",
            "- The acceptance agent will restore context and guide the human one observable step at a time.",
        ]
    )

    lines.extend(["", "## Remaining Gaps", ""])
    gaps = payload.get("unresolved_gaps") or []
    if gaps:
        lines.extend(f"- {gap}" for gap in gaps)
    else:
        lines.append("- None recorded.")

    return "\n".join(lines) + "\n"


def _render_blocker_detail(blocker: dict[str, Any]) -> list[str]:
    attempted = blocker.get("attempted_recovery") or []
    attempted_text = (
        "; ".join(
            f"{item.get('action', 'action')} -> {item.get('result', 'result not recorded')}"
            for item in attempted
            if isinstance(item, dict)
        )
        or "None recorded; no safe automatic recovery was claimed."
    )
    resume = blocker.get("resume") or {}
    return [
        f"### {blocker.get('blocker_id', 'BLOCKER')}: {blocker.get('summary', 'Workflow blocked')}",
        "",
        f"- Workflow / stage: `{blocker.get('workflow', 'unknown')}` / `{blocker.get('stage', 'unknown')}`",
        f"- Category / owner: `{blocker.get('category', 'workflow-validation')}` / `{blocker.get('owner', 'agent')}`",
        f"- Why blocked: {blocker.get('details', 'Not recorded')}",
        f"- Evidence: {'; '.join(str(item) for item in blocker.get('evidence') or [])}",
        f"- Automatic recovery attempted: {attempted_text}",
        f"- Affected scope: {'; '.join(str(item) for item in blocker.get('affected_scope') or [])}",
        f"- Safe independent work can continue: {'yes' if blocker.get('can_continue') else 'no'}",
        f"- Exact next action: {blocker.get('exact_next_action', 'Not recorded')}",
        f"- Unblock criteria: {blocker.get('unblock_criteria', 'Not recorded')}",
        f"- Resume: {resume.get('command') or resume.get('instruction') or 'Not recorded'}",
        "",
    ]


def _render_human_blocker(blocker: dict[str, Any]) -> list[str]:
    guide = blocker.get("human_action_guide") or {}
    rendered = [
        f"### {blocker.get('blocker_id', 'BLOCKER')}: {blocker.get('summary', 'Human action required')}",
        "",
        f"- Why blocked: {blocker.get('details', 'Not recorded')}",
        f"- Owner: `{blocker.get('owner', 'user')}`",
        f"- Evidence: {'; '.join(str(item) for item in blocker.get('evidence') or [])}",
        f"- Unblock criteria: {blocker.get('unblock_criteria', 'Not recorded')}",
        f"- Goal: {guide.get('goal', blocker.get('exact_next_action', 'Resolve the blocker'))}",
        f"- Why a human is required: {guide.get('why_human', 'Human authority is required.')}",
        "",
        "Before you start:",
    ]
    rendered.extend(
        f"- {item}"
        for item in guide.get("prerequisites")
        or ["Confirm the target and required authority."]
    )
    rendered.extend(["", "Safety:"])
    rendered.extend(
        f"- {item}" for item in guide.get("safety_notes") or ["Do not share secrets."]
    )
    rendered.extend(["", "Steps:", ""])
    for step in guide.get("steps") or []:
        rendered.append(
            f"{step.get('order', 1)}. **{step.get('title', 'Action')}** — {step.get('action', '')}"
        )
        if step.get("command"):
            rendered.append(f"   - Command: `{step['command']}`")
        rendered.append(
            f"   - Expected: {step.get('expected_result', 'The requested state is visible.')}"
        )
        rendered.append(
            f"   - If it fails: {step.get('if_failed', 'Return the observed error without retrying blindly.')}"
        )
    rendered.extend(["", "Return to the agent:"])
    rendered.extend(
        f"- {item}"
        for item in guide.get("evidence_to_return") or ["Sanitized proof of the result"]
    )
    rendered.extend(
        [
            "",
            f"Resume: {guide.get('resume_instruction', (blocker.get('resume') or {}).get('instruction', 'Resume the workflow.'))}",
            "",
        ]
    )
    return rendered


def _path_lines(paths: list[str]) -> list[str]:
    if not paths:
        return ["- None recorded."]
    return [f"- `{path}`" for path in paths]
