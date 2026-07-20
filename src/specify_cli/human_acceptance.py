"""Durable, context-restoring human acceptance state for completed features."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping

import pathspec

from .atomic_io import (
    atomic_write_bytes,
    atomic_write_text,
    interprocess_lock,
    read_local_state_bytes,
    read_local_state_text,
)
from .launcher import render_command


ACCEPTANCE_FILENAME = "human-acceptance.json"
IMPLEMENTATION_SUMMARY_FILENAME = "implementation-summary.md"
IMPLEMENTATION_HANDOFF_FILENAME = "implementation-handoff.json"
REVIEW_STATE_FILENAME = "review-state.json"
ACCEPTANCE_REPAIR_JOURNAL_FILENAME = ".human-acceptance-repair.json"
ACCEPTANCE_REPAIR_BACKUP_FILENAME = ".human-acceptance-repair-backup.json"
ACCEPTANCE_SCHEMA_REF = ".specify/templates/human-acceptance-state-schema.json"
ACCEPTANCE_COMMAND = "sp-accept (Classic) or spx-accept (Advanced)"
ACCEPTANCE_STATUSES = {
    "draft",
    "ready",
    "in_progress",
    "accepted",
    "rejected",
    "blocked",
    "stale",
}
STEP_RESULTS = {"pending", "pass", "fail", "blocked", "not_run"}
SCENARIO_VERDICTS = {"pending", "pass", "fail", "blocked", "not_run"}
OVERALL_VERDICTS = {"pending", "pass", "fail", "blocked"}
FINDING_CLASSIFICATIONS = {
    "observed-mismatch",
    "environment-or-access",
    "unable-to-observe",
}
FINDING_ROUTES = {
    "sp-review",
    "spx-review",
    "human-action",
}
ACCEPTANCE_REPAIR_TARGETS = {
    "sp-review": "review",
    "spx-review": "review",
}
ACCEPTANCE_REPAIR_OWNERS = {
    "sp-review": "sp-review",
    "spx-review": "spx-review",
}
RUNTIME_TARGET_MODES = {"source", "build", "deployment", "device"}
RUNTIME_TARGET_STATUSES = {"pending", "ready", "blocked"}
HUMAN_DECISIONS = {"pending", "accept", "reject"}
HUMAN_EVIDENCE_SOURCES = {
    "human-reply",
    "interactive-input",
    "attached-evidence",
}


def new_human_acceptance_state() -> dict[str, Any]:
    """Return the stable empty state materialized from approved Review output."""

    return {
        "version": 2,
        "schema_ref": ACCEPTANCE_SCHEMA_REF,
        "status": "draft",
        "source": {
            "implementation_summary": IMPLEMENTATION_SUMMARY_FILENAME,
            "implementation_summary_sha256": "",
            "implementation_handoff": IMPLEMENTATION_HANDOFF_FILENAME,
            "implementation_handoff_sha256": "",
            "review_state": REVIEW_STATE_FILENAME,
            "review_state_sha256": "",
            "reviewed_snapshot_sha256": "",
            "acceptance_universe_sha256": "",
            "runtime_targets_sha256": "",
            "prepared_from_sha256": "",
            "current_sha256": "",
        },
        "orientation": {
            "outcome": "",
            "why_it_matters": "",
            "user_visible_changes": [],
            "not_in_scope": [],
            "prerequisites": [],
            "start_here": "",
        },
        "acceptance_universe": {
            "obligations": [],
            "uncovered_obligation_ids": [],
            "verdict": "pending",
        },
        "runtime_targets": [],
        "scenarios": [],
        "cursor": {"scenario_id": None, "step_id": None},
        "findings": [],
        "repair_resume": None,
        "repair_history": [],
        "overall": {
            "verdict": "pending",
            "summary": "",
            "next_command": ACCEPTANCE_COMMAND,
            "human_decision": "pending",
            "decision_confirmation_id": "",
            "decision_evidence": [],
        },
    }


def _canonical_json_sha256(value: object) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _acceptance_contract_sha256(
    obligations: list[dict[str, Any]], scenarios: list[dict[str, Any]]
) -> str:
    return _canonical_json_sha256(
        {
            "human_acceptance_obligations": obligations,
            "human_acceptance_scenarios": scenarios,
        }
    )


def _human_confirmation_id(contract_sha256: str, *parts: object) -> str:
    return (
        "HC-"
        + _canonical_json_sha256(
            {"contract_sha256": contract_sha256, "parts": [str(item) for item in parts]}
        )[:24]
    )


def _acceptance_finding_sha256(value: Mapping[str, Any]) -> str:
    return _canonical_json_sha256(
        {
            key: deepcopy(value.get(key))
            for key in (
                "id",
                "scenario_id",
                "step_id",
                "classification",
                "expected",
                "observed",
                "evidence",
                "route",
            )
        }
    )


def _obligation_contract(value: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: deepcopy(value.get(key))
        for key in (
            "id",
            "source_ref",
            "change_kind",
            "user_outcome",
            "required",
            "scenario_ids",
        )
    }


def _scenario_contract(value: Mapping[str, Any]) -> dict[str, Any]:
    steps = value.get("steps")
    normalized_steps = []
    if isinstance(steps, list):
        normalized_steps = [
            {
                key: deepcopy(step.get(key))
                for key in (
                    "id",
                    "action",
                    "expected_result",
                    "evidence_requirement",
                    "risk",
                )
            }
            for step in steps
            if isinstance(step, Mapping)
        ]
    return {
        **{
            key: deepcopy(value.get(key))
            for key in (
                "id",
                "title",
                "user_value",
                "actor",
                "required",
                "obligation_ids",
                "entrypoint_id",
                "review_scenario_ids",
                "start_state",
            )
        },
        "steps": normalized_steps,
    }


def _materialize_acceptance_scenario(value: Mapping[str, Any]) -> dict[str, Any]:
    canonical = _scenario_contract(value)
    steps: list[dict[str, Any]] = []
    for step in canonical["steps"]:
        steps.append(
            {
                **step,
                "if_failed": (
                    "Stop safely and return the visible result, screenshot, or "
                    "sanitized error; do not retry a destructive action."
                ),
                "response_prompt": (
                    "Reply `seen` if the expected result is visible; otherwise "
                    "return what you observed (without secrets)."
                ),
                "result": "pending",
                "observed_result": None,
                "confirmation_id": "",
                "evidence": [],
            }
        )
    return {
        **{key: value for key, value in canonical.items() if key != "steps"},
        "preconditions": list(value.get("preconditions") or []),
        "runtime_target_id": None,
        "steps": steps,
        "verdict": "pending",
        "notes": None,
    }


def _materialize_runtime_target(value: Mapping[str, Any]) -> dict[str, Any]:
    return {
        **deepcopy(dict(value)),
        "acceptance_status": "pending",
        "acceptance_ready_evidence": [],
        "agent_actions": [],
    }


def _runtime_target_id_for_scenario(
    scenario: Mapping[str, Any],
    targets: list[Mapping[str, Any]],
) -> str | None:
    required_review_ids = set(scenario.get("review_scenario_ids") or [])
    matching = [
        str(target.get("id") or "")
        for target in targets
        if target.get("entrypoint_id") == scenario.get("entrypoint_id")
        and required_review_ids.issubset(set(target.get("review_scenario_ids") or []))
    ]
    return matching[0] if len(matching) == 1 and matching[0] else None


def _review_runtime_target_contract(value: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: deepcopy(value.get(key))
        for key in (
            "id",
            "mode",
            "status",
            "entrypoint_id",
            "environment_ref",
            "instance_ref",
            "configuration_ref",
            "reviewed_snapshot_sha256",
            "artifact_ref",
            "artifact_sha256",
            "deployment_id",
            "observed_version",
            "test_data_refs",
            "ready_evidence_refs",
            "review_scenario_ids",
            "identity_evidence_ref",
            "identity_evidence_sha256",
        )
    }


def _approved_review_acceptance_contract(
    root: Path, feature_dir: Path
) -> dict[str, Any]:
    """Load the immutable human-acceptance contract from a fresh approved Review."""

    from .review_runtime import (
        _review_runtime_target_contract,
        _review_runtime_targets_sha256,
        validate_review,
    )

    validation = validate_review(root, feature_dir)
    state = validation.get("state")
    if not validation.get("valid") or not isinstance(state, dict):
        detail = "; ".join(str(item) for item in validation.get("errors") or [])
        raise ValueError(
            "human acceptance requires a fresh valid Review"
            + (f": {detail}" if detail else "")
        )
    if state.get("status") != "approved":
        raise ValueError("human acceptance requires review-state.json status=approved")

    handoff_path = feature_dir / IMPLEMENTATION_HANDOFF_FILENAME
    review_path = feature_dir / REVIEW_STATE_FILENAME
    handoff = _read_state(handoff_path)
    if handoff.get("human_acceptance_contract_origin") != "task-index-v2":
        raise ValueError(
            "human acceptance requires a task-index-v2 Human Acceptance Universe; "
            "regenerate Tasks instead of accepting a legacy Review-derived fallback"
        )
    obligations = handoff.get("human_acceptance_obligations")
    scenarios = handoff.get("human_acceptance_scenarios")
    if not isinstance(obligations, list) or not obligations:
        raise ValueError(
            "implementation-handoff.json has no frozen human_acceptance_obligations"
        )
    if not isinstance(scenarios, list) or not scenarios:
        raise ValueError(
            "implementation-handoff.json has no frozen human_acceptance_scenarios"
        )
    canonical_obligations = [
        _obligation_contract(item) for item in obligations if isinstance(item, Mapping)
    ]
    canonical_scenarios = [
        _scenario_contract(item) for item in scenarios if isinstance(item, Mapping)
    ]
    if len(canonical_obligations) != len(obligations) or len(
        canonical_scenarios
    ) != len(scenarios):
        raise ValueError(
            "the frozen human acceptance contract contains invalid entries"
        )
    contract_digest = _acceptance_contract_sha256(
        canonical_obligations, canonical_scenarios
    )
    recorded_contract_digest = str(
        handoff.get("human_acceptance_contract_sha256") or ""
    )
    if recorded_contract_digest != contract_digest:
        raise ValueError(
            "implementation-handoff.json human acceptance contract digest is invalid"
        )
    if state.get("human_acceptance_obligations") != obligations:
        raise ValueError("review-state.json human acceptance obligations drifted")
    if state.get("human_acceptance_scenarios") != scenarios:
        raise ValueError("review-state.json human acceptance scenarios drifted")
    final = state.get("final")
    reviewed_snapshot = (
        str(final.get("reviewed_snapshot_sha256") or "")
        if isinstance(final, Mapping)
        else ""
    )
    if not re.fullmatch(r"[0-9a-f]{64}", reviewed_snapshot):
        raise ValueError("approved Review is missing final reviewed snapshot identity")
    raw_entrypoints = state.get("entrypoints")
    entrypoints = raw_entrypoints if isinstance(raw_entrypoints, list) else []
    entrypoint_ids = {
        str(item.get("id"))
        for item in entrypoints
        if isinstance(item, Mapping) and str(item.get("id") or "").strip()
    }
    raw_runtime_targets = state.get("reviewed_runtime_targets")
    if not isinstance(raw_runtime_targets, list) or not raw_runtime_targets:
        raise ValueError("approved Review has no reviewed runtime targets")
    runtime_targets = [
        _review_runtime_target_contract(item)
        for item in raw_runtime_targets
        if isinstance(item, Mapping)
    ]
    if len(runtime_targets) != len(raw_runtime_targets):
        raise ValueError("approved Review runtime target contract is invalid")
    runtime_targets_sha256 = _review_runtime_targets_sha256(runtime_targets)
    final_runtime_targets_sha256 = (
        str(final.get("runtime_targets_sha256") or "")
        if isinstance(final, Mapping)
        else ""
    )
    if final_runtime_targets_sha256 != runtime_targets_sha256:
        raise ValueError("approved Review runtime target digest is invalid")
    return {
        "handoff": handoff,
        "review_state": state,
        "implementation_handoff_sha256": _sha256(handoff_path),
        "review_state_sha256": _sha256(review_path),
        "reviewed_snapshot_sha256": reviewed_snapshot,
        "acceptance_universe_sha256": contract_digest,
        "runtime_targets_sha256": runtime_targets_sha256,
        "obligations": canonical_obligations,
        "scenarios": canonical_scenarios,
        "entrypoint_ids": entrypoint_ids,
        "runtime_targets": runtime_targets,
    }


def _required_obligation_ids(obligations: list[dict[str, Any]]) -> list[str]:
    return sorted(
        str(item.get("id"))
        for item in obligations
        if item.get("required") is True and str(item.get("id") or "").strip()
    )


def _uncovered_obligation_ids(
    obligations: list[dict[str, Any]], scenarios: list[dict[str, Any]]
) -> list[str]:
    passed = {
        str(obligation_id)
        for scenario in scenarios
        if scenario.get("verdict") == "pass"
        for obligation_id in (scenario.get("obligation_ids") or [])
    }
    return sorted(
        str(item.get("id"))
        for item in obligations
        if item.get("required") is True and str(item.get("id")) not in passed
    )


def prepare_human_acceptance(project_root: Path, feature_dir: Path) -> dict[str, Any]:
    """Create or freshness-check the post-implementation acceptance state."""

    root = project_root.resolve()
    resolved_feature_dir = _resolve_feature_dir(root, feature_dir)
    state_path = resolved_feature_dir / ACCEPTANCE_FILENAME
    with interprocess_lock(state_path.parent / ".human-acceptance.lock"):
        return _prepare_human_acceptance_locked(root, resolved_feature_dir)


def _acceptance_repair_paths(feature_dir: Path) -> tuple[Path, Path]:
    return (
        feature_dir / ACCEPTANCE_REPAIR_JOURNAL_FILENAME,
        feature_dir / ACCEPTANCE_REPAIR_BACKUP_FILENAME,
    )


def _decorate_acceptance_repair_payload(
    payload: dict[str, Any],
    *,
    root: Path,
    feature_dir: Path,
    route: str,
) -> dict[str, Any]:
    data = payload.setdefault("data", {})
    data["acceptance_state_path"] = _display_path(
        feature_dir / ACCEPTANCE_FILENAME,
        root,
    )
    data["acceptance_status"] = "draft"
    data["repair_handoff_command"] = route
    data["owning_stage_command"] = ACCEPTANCE_REPAIR_OWNERS[route]
    data["acceptance_return_argv"] = [
        "specify",
        "accept",
        "prepare",
        "--feature-dir",
        str(feature_dir),
        "--format",
        "json",
    ]
    return payload


def _write_acceptance_repair_journal(path: Path, payload: dict[str, Any]) -> None:
    atomic_write_text(
        path,
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
    )


def _clear_acceptance_repair_transaction(journal_path: Path, backup_path: Path) -> None:
    journal_path.unlink(missing_ok=True)
    try:
        backup_path.unlink(missing_ok=True)
    except OSError:
        # The journal is the transaction marker.  A leftover backup is inert and
        # the next route attempt will clean or replace it before any mutation.
        pass


def _validated_acceptance_repair_backup(
    *,
    backup_path: Path,
    expected_sha256: str,
    finding_id: str,
    route: str,
) -> bytes:
    backup_bytes = read_local_state_bytes(backup_path, root=backup_path.parent)
    actual_sha256 = hashlib.sha256(backup_bytes).hexdigest()
    if (
        not re.fullmatch(r"[0-9a-f]{64}", expected_sha256)
        or actual_sha256 != expected_sha256
    ):
        raise ValueError(
            f"backup digest mismatch: expected {expected_sha256 or 'missing'}, "
            f"found {actual_sha256}"
        )
    payload = json.loads(backup_bytes.decode("utf-8"))
    if not isinstance(payload, dict) or payload.get("status") not in {
        "rejected",
        "blocked",
    }:
        raise ValueError("backup must contain a rejected or blocked acceptance object")
    findings = payload.get("findings")
    if not isinstance(findings, list) or not any(
        isinstance(item, dict)
        and item.get("id") == finding_id
        and item.get("route") == route
        and item.get("status") == "open"
        for item in findings
    ):
        raise ValueError("backup does not preserve the named open finding and route")
    if not isinstance(payload.get("source"), dict) or not isinstance(
        payload.get("overall"), dict
    ):
        raise ValueError("backup is missing acceptance source or verdict metadata")
    return backup_bytes


def _acceptance_repair_recovery_error(
    *,
    root: Path,
    feature_dir: Path,
    reason: str,
    evidence: list[str],
    route: str,
    finding_id: str,
    expected_revision: int,
) -> Exception:
    from .workflow_runtime import WorkflowRuntimeError

    journal_path, backup_path = _acceptance_repair_paths(feature_dir)
    resume_argv = [
        "specify",
        "accept",
        "route-repair",
        "--feature-dir",
        str(feature_dir),
        "--finding-id",
        finding_id,
        "--route",
        route,
        "--expected-revision",
        str(expected_revision),
        "--evidence",
        "<sanitized-evidence>",
        "--format",
        "json",
    ]
    blocker = _acceptance_blocker(
        blocker_id="ACCEPTANCE-REPAIR-RECOVERY",
        category="artifact-or-state",
        owner="maintainer",
        summary=reason,
        evidence=[
            *evidence,
            f"journal: {_display_path(journal_path, root)}",
            f"backup: {_display_path(backup_path, root)}",
        ],
        exact_next_action=(
            "Inspect the journal, backup, workflow-runtime.json, rich workflow-state.md, "
            "and human-acceptance.json; restore the backup only when the phase runtime "
            "still names the journal's "
            "original accept revision, otherwise preserve all files for maintainer review."
        ),
        unblock_criteria=(
            "The acceptance file and workflow state match one journal phase, and a "
            "read-only retry reports no pending repair transaction."
        ),
        resume_argv=resume_argv,
        human_action_required=True,
    )
    blocker["human_action_guide"] = {
        "goal": "Recover one interrupted acceptance repair without losing either state file.",
        "why_human": (
            "The deterministic states no longer match a safe automatic recovery case; "
            "choosing which durable record to preserve requires maintainer authority."
        ),
        "prerequisites": [
            f"Access to the project at {root}",
            f"The journal at {_display_path(journal_path, root)}",
            f"The backup at {_display_path(backup_path, root)}",
            "The current workflow-runtime.json, workflow-state.md, and human-acceptance.json files",
        ],
        "safety_notes": [
            "Do not delete the journal or backup before copying both to a safe location.",
            "Do not edit revision numbers or invent a missing acceptance verdict.",
            "Do not paste secrets or unredacted private acceptance evidence into chat.",
        ],
        "steps": [
            {
                "order": 1,
                "title": "Preserve the recovery packet",
                "action": "Copy the journal, backup, workflow state, and acceptance state before editing anything.",
                "command": None,
                "expected_result": "Four unchanged recovery files are available for comparison.",
                "if_failed": "Stop without editing and report the inaccessible path and sanitized OS error.",
            },
            {
                "order": 2,
                "title": "Match the recorded phase",
                "action": "Compare the journal expected revision/target with the current workflow stage and acceptance status.",
                "command": None,
                "expected_result": "The state matches either the original accept phase or the completed repair handoff.",
                "if_failed": "Preserve all files and return their stage, status, and revision values; do not guess.",
            },
            {
                "order": 3,
                "title": "Restore only the proven side",
                "action": "If workflow is still at the original accept revision, restore the backup acceptance file; if the repair handoff is fully committed, keep the draft acceptance file and remove only the journal and backup.",
                "command": None,
                "expected_result": "Both durable files describe the same repair phase.",
                "if_failed": "Stop and return the smallest sanitized filesystem error; do not broaden permissions or delete evidence.",
            },
            {
                "order": 4,
                "title": "Verify through the CLI",
                "action": "Rerun the exact route-repair command with real sanitized evidence and inspect its JSON result.",
                "command": render_command(tuple(resume_argv)),
                "expected_result": "The command either completes once or returns a new typed blocker without changing both states inconsistently.",
                "if_failed": "Return the complete blocker JSON and keep the recovery copies.",
            },
        ],
        "verification": [
            "No pending journal remains after a successful recovery",
            "Workflow stage/revision and acceptance status describe one consistent phase",
            "The named open finding and its evidence are preserved",
        ],
        "evidence_to_return": [
            "Current workflow stage, status, and revision",
            "Current acceptance status, finding ID, and route",
            "Sanitized CLI recovery result or OS error",
        ],
        "resume_instruction": (
            "After the files are consistent, replace <sanitized-evidence> and run: "
            f"{render_command(tuple(resume_argv))}"
        ),
    }
    return WorkflowRuntimeError(
        reason,
        code="acceptance-repair-recovery-required",
        data={
            "journal_path": _display_path(journal_path, root),
            "backup_path": _display_path(backup_path, root),
            "finding_id": finding_id,
            "repair_route": route,
        },
        blocker=blocker,
    )


def _recover_acceptance_repair_transaction(
    *,
    root: Path,
    feature_dir: Path,
) -> dict[str, Any] | None:
    journal_path, backup_path = _acceptance_repair_paths(feature_dir)
    if not journal_path.exists():
        return None
    try:
        journal = json.loads(read_local_state_text(journal_path, root=feature_dir))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise _acceptance_repair_recovery_error(
            root=root,
            feature_dir=feature_dir,
            reason="Acceptance repair journal is unreadable.",
            evidence=[f"read failure: {type(exc).__name__}: {exc}"],
            route="sp-review",
            finding_id="unknown",
            expected_revision=0,
        ) from exc
    if not isinstance(journal, dict):
        raise _acceptance_repair_recovery_error(
            root=root,
            feature_dir=feature_dir,
            reason="Acceptance repair journal is not a JSON object.",
            evidence=["journal shape: non-object"],
            route="sp-review",
            finding_id="unknown",
            expected_revision=0,
        )
    route = str(journal.get("route") or "")
    finding_id = str(journal.get("finding_id") or "")
    target_stage = str(journal.get("target_stage") or "")
    expected_revision = journal.get("expected_revision")
    backup_sha256 = str(journal.get("backup_sha256") or "")
    invalidated_sha256 = str(journal.get("invalidated_acceptance_sha256") or "")
    if (
        route not in ACCEPTANCE_REPAIR_TARGETS
        or target_stage != ACCEPTANCE_REPAIR_TARGETS.get(route)
        or not finding_id
        or isinstance(expected_revision, bool)
        or not isinstance(expected_revision, int)
        or not re.fullmatch(r"[0-9a-f]{64}", backup_sha256)
        or not re.fullmatch(r"[0-9a-f]{64}", invalidated_sha256)
    ):
        raise _acceptance_repair_recovery_error(
            root=root,
            feature_dir=feature_dir,
            reason="Acceptance repair journal metadata is invalid.",
            evidence=[
                "journal route, target, finding, revision, or state digest failed validation"
            ],
            route=route or "sp-review",
            finding_id=finding_id or "unknown",
            expected_revision=(
                expected_revision if isinstance(expected_revision, int) else 0
            ),
        )

    from .agent_api import envelope
    from .workflow_runtime import show_workflow

    shown = show_workflow(feature_dir)
    workflow = shown["data"]
    acceptance_path = feature_dir / ACCEPTANCE_FILENAME
    acceptance_text = read_local_state_text(acceptance_path, root=feature_dir)
    acceptance_sha256 = hashlib.sha256(acceptance_text.encode("utf-8")).hexdigest()
    try:
        acceptance = json.loads(acceptance_text)
    except json.JSONDecodeError as exc:
        raise _acceptance_repair_recovery_error(
            root=root,
            feature_dir=feature_dir,
            reason="Current acceptance state is invalid JSON during recovery.",
            evidence=[
                f"current acceptance digest: {acceptance_sha256}",
                f"JSON error: {exc.msg}",
            ],
            route=route,
            finding_id=finding_id,
            expected_revision=expected_revision,
        ) from exc
    if not isinstance(acceptance, dict):
        raise _acceptance_repair_recovery_error(
            root=root,
            feature_dir=feature_dir,
            reason="Current acceptance state is not a JSON object during recovery.",
            evidence=[f"current acceptance digest: {acceptance_sha256}"],
            route=route,
            finding_id=finding_id,
            expected_revision=expected_revision,
        )
    finding_preserved = any(
        isinstance(item, dict)
        and item.get("id") == finding_id
        and item.get("route") == route
        and item.get("status") == "open"
        for item in acceptance.get("findings", [])
    )
    if (
        workflow.get("stage") == target_stage
        and workflow.get("status") == "active"
        and workflow.get("revision") == expected_revision + 1
        and acceptance_sha256 == invalidated_sha256
        and acceptance.get("status") == "draft"
        and acceptance.get("overall", {}).get("next_command") == route
        and finding_preserved
    ):
        _clear_acceptance_repair_transaction(journal_path, backup_path)
        recovered = envelope(
            "ok",
            f"Recovered completed acceptance repair route {route}.",
            data={
                **workflow,
                "reopened_from": "accept",
                "repair_route": route,
                "finding_id": finding_id,
                "repair_handoff_command": route,
                "owning_stage_command": ACCEPTANCE_REPAIR_OWNERS[route],
                "acceptance_state_path": _display_path(acceptance_path, root),
                "acceptance_status": "draft",
            },
            show_argv=shown["show_argv"],
        )
        return _decorate_acceptance_repair_payload(
            recovered,
            root=root,
            feature_dir=feature_dir,
            route=route,
        )
    if (
        workflow.get("stage") == "accept"
        and workflow.get("status") in {"active", "blocked"}
        and workflow.get("revision") == expected_revision
    ):
        if acceptance_sha256 == backup_sha256:
            _clear_acceptance_repair_transaction(journal_path, backup_path)
            return None
        if acceptance_sha256 != invalidated_sha256 or not finding_preserved:
            raise _acceptance_repair_recovery_error(
                root=root,
                feature_dir=feature_dir,
                reason="Current acceptance draft changed after the repair journal was written.",
                evidence=[
                    f"expected invalidated digest: {invalidated_sha256}",
                    f"current acceptance digest: {acceptance_sha256}",
                    f"named finding preserved: {finding_preserved}",
                ],
                route=route,
                finding_id=finding_id,
                expected_revision=expected_revision,
            )
        try:
            backup_bytes = _validated_acceptance_repair_backup(
                backup_path=backup_path,
                expected_sha256=backup_sha256,
                finding_id=finding_id,
                route=route,
            )
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            raise _acceptance_repair_recovery_error(
                root=root,
                feature_dir=feature_dir,
                reason="Acceptance repair backup is unavailable for rollback.",
                evidence=[f"backup read failure: {type(exc).__name__}: {exc}"],
                route=route,
                finding_id=finding_id,
                expected_revision=expected_revision,
            ) from exc
        atomic_write_bytes(acceptance_path, backup_bytes)
        _clear_acceptance_repair_transaction(journal_path, backup_path)
        return None
    raise _acceptance_repair_recovery_error(
        root=root,
        feature_dir=feature_dir,
        reason="Interrupted acceptance repair does not match a safe automatic recovery phase.",
        evidence=[
            f"workflow stage/status/revision: {workflow.get('stage')}/{workflow.get('status')}/{workflow.get('revision')}",
            f"acceptance status: {acceptance.get('status')}",
            f"journal phase: {journal.get('phase')}",
        ],
        route=route,
        finding_id=finding_id,
        expected_revision=expected_revision,
    )


def route_human_acceptance_repair(
    project_root: Path,
    feature_dir: Path,
    *,
    route: str,
    finding_id: str,
    expected_revision: int,
    evidence: list[str],
) -> dict[str, Any]:
    """Invalidate a failed verdict and atomically guard its workflow handoff."""

    root = project_root.resolve()
    resolved_feature_dir = _resolve_feature_dir(root, feature_dir)
    normalized_route = str(route or "").strip()
    target_stage = ACCEPTANCE_REPAIR_TARGETS.get(normalized_route)
    if target_stage is None:
        allowed = ", ".join(sorted(ACCEPTANCE_REPAIR_TARGETS))
        raise ValueError(f"route must be one of: {allowed}")
    normalized_finding = str(finding_id or "").strip()
    if not normalized_finding:
        raise ValueError("finding_id is required")
    normalized_evidence = [str(item).strip() for item in evidence if str(item).strip()]
    if not normalized_evidence:
        raise ValueError("at least one sanitized evidence item is required")

    state_path = resolved_feature_dir / ACCEPTANCE_FILENAME
    with interprocess_lock(state_path.parent / ".human-acceptance.lock"):
        recovered = _recover_acceptance_repair_transaction(
            root=root,
            feature_dir=resolved_feature_dir,
        )
        if recovered is not None:
            return recovered
        from .workflow_runtime import (
            reopen_acceptance_workflow,
            show_workflow,
        )

        workflow = show_workflow(resolved_feature_dir)
        workflow_data = workflow["data"]
        if (
            workflow_data.get("stage") != "accept"
            or workflow_data.get("status") != "active"
            or workflow_data.get("revision") != expected_revision
        ):
            # Reuse the runtime's typed source/revision blocker before touching
            # acceptance bytes. This keeps rejected repairs byte-identical and
            # preserves any existing human blocker/tutorial.
            return reopen_acceptance_workflow(
                resolved_feature_dir,
                target_stage=target_stage,
                repair_route=normalized_route,
                finding_id=normalized_finding,
                expected_revision=expected_revision,
                evidence=normalized_evidence,
            )
        if not state_path.is_file():
            raise ValueError(f"missing {ACCEPTANCE_FILENAME}")
        original_state_bytes = read_local_state_bytes(
            state_path,
            root=resolved_feature_dir,
        )
        state = _read_state(state_path)
        validation = validate_human_acceptance(root, resolved_feature_dir)
        if not validation["valid"]:
            errors = "; ".join(validation["errors"])
            raise ValueError(
                f"human-acceptance state must be valid before repair routing: {errors}"
            )
        if state.get("status") not in {"rejected", "blocked"}:
            raise ValueError(
                "acceptance repair requires human-acceptance status rejected or blocked"
            )
        findings = state.get("findings")
        if not isinstance(findings, list):
            raise ValueError("human-acceptance findings must be an array")
        finding = next(
            (
                item
                for item in findings
                if isinstance(item, dict) and item.get("id") == normalized_finding
            ),
            None,
        )
        if finding is None:
            raise ValueError(f"acceptance finding '{normalized_finding}' was not found")
        if finding.get("status") != "open":
            raise ValueError(f"acceptance finding '{normalized_finding}' is not open")
        if finding.get("route") != normalized_route:
            raise ValueError(
                f"acceptance finding '{normalized_finding}' routes to "
                f"{finding.get('route') or 'missing'}, not {normalized_route}"
            )

        finding_evidence = finding.get("evidence")
        if not isinstance(finding_evidence, list):
            finding_evidence = []
        finding["evidence"] = list(
            dict.fromkeys([*map(str, finding_evidence), *normalized_evidence])
        )
        finding_contract_sha256 = _acceptance_finding_sha256(finding)
        affected_obligation_ids = {
            str(item.get("id") or "")
            for item in (
                state.get("acceptance_universe", {}).get("obligations", [])
                if isinstance(state.get("acceptance_universe"), dict)
                else []
            )
            if isinstance(item, dict) and str(item.get("id") or "").strip()
        }
        affected_scenario_ids: list[str] = []
        for scenario in state.get("scenarios", []):
            if not isinstance(scenario, dict):
                continue
            scenario_id = str(scenario.get("id") or "")
            scenario["runtime_target_id"] = None
            affected_scenario_ids.append(scenario_id)
            scenario["verdict"] = "pending"
            for step in scenario.get("steps", []):
                if not isinstance(step, dict):
                    continue
                step["result"] = "pending"
                step["observed_result"] = None
                step["evidence"] = []
        state["runtime_targets"] = []
        state["status"] = "draft"
        source = state.get("source")
        if isinstance(source, dict):
            source["prepared_from_sha256"] = ""
            source["current_sha256"] = ""
        universe = state.get("acceptance_universe")
        if isinstance(universe, dict):
            obligations = universe.get("obligations")
            scenarios = state.get("scenarios")
            if isinstance(obligations, list) and isinstance(scenarios, list):
                universe["uncovered_obligation_ids"] = _uncovered_obligation_ids(
                    obligations, scenarios
                )
            universe["verdict"] = "pending"
        state["cursor"] = {
            "scenario_id": finding.get("scenario_id"),
            "step_id": finding.get("step_id"),
        }
        state["repair_resume"] = {
            "finding_id": normalized_finding,
            "finding_contract_sha256": finding_contract_sha256,
            "previous_review_state_sha256": (
                str(source.get("review_state_sha256") or "")
                if isinstance(source, dict)
                else ""
            ),
            "new_review_state_sha256": "",
            "review_cycle_id": "",
            "affected_obligation_ids": sorted(affected_obligation_ids),
            "affected_scenario_ids": affected_scenario_ids,
            "preserved_scenario_ids": [],
            "scenario_id": finding.get("scenario_id"),
            "step_id": finding.get("step_id"),
        }
        prior_overall = state.get("overall")
        decision_confirmation_id = (
            str(prior_overall.get("decision_confirmation_id") or "")
            if isinstance(prior_overall, dict)
            else ""
        )
        state["overall"] = {
            "verdict": "pending",
            "summary": (
                f"Acceptance finding {normalized_finding} is being repaired through "
                f"{normalized_route}; the prior verdict is no longer valid."
            ),
            "next_command": normalized_route,
            "human_decision": "pending",
            "decision_confirmation_id": decision_confirmation_id,
            "decision_evidence": [],
        }
        journal_path, backup_path = _acceptance_repair_paths(resolved_feature_dir)
        backup_path.unlink(missing_ok=True)
        atomic_write_bytes(backup_path, original_state_bytes)
        journal = {
            "version": 1,
            "phase": "prepared",
            "finding_id": normalized_finding,
            "route": normalized_route,
            "target_stage": target_stage,
            "owning_stage_command": ACCEPTANCE_REPAIR_OWNERS[normalized_route],
            "expected_revision": expected_revision,
            "backup_sha256": hashlib.sha256(original_state_bytes).hexdigest(),
            "invalidated_acceptance_sha256": hashlib.sha256(
                (json.dumps(state, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
            ).hexdigest(),
            "acceptance_file": ACCEPTANCE_FILENAME,
            "backup_file": ACCEPTANCE_REPAIR_BACKUP_FILENAME,
        }
        try:
            _write_acceptance_repair_journal(journal_path, journal)
        except OSError:
            backup_path.unlink(missing_ok=True)
            raise
        try:
            _write_state(state_path, state)
        except OSError:
            if (
                read_local_state_bytes(state_path, root=resolved_feature_dir)
                == original_state_bytes
            ):
                _clear_acceptance_repair_transaction(journal_path, backup_path)
            raise
        journal["phase"] = "acceptance-invalidated"
        _write_acceptance_repair_journal(journal_path, journal)

        try:
            routed = reopen_acceptance_workflow(
                resolved_feature_dir,
                target_stage=target_stage,
                repair_route=normalized_route,
                finding_id=normalized_finding,
                expected_revision=expected_revision,
                evidence=normalized_evidence,
            )
        except Exception:
            # The runtime mutation may have committed before its caller observed
            # a transport/filesystem exception. Re-read both durable states via
            # the journal recovery state machine: it returns the committed
            # payload, rolls back only at the original accept revision, and
            # preserves recovery evidence for every ambiguous phase.
            recovered_after_error = _recover_acceptance_repair_transaction(
                root=root,
                feature_dir=resolved_feature_dir,
            )
            if recovered_after_error is not None:
                return recovered_after_error
            raise

        journal["phase"] = "workflow-reopened"
        _write_acceptance_repair_journal(journal_path, journal)
        _clear_acceptance_repair_transaction(journal_path, backup_path)

    return _decorate_acceptance_repair_payload(
        routed,
        root=root,
        feature_dir=resolved_feature_dir,
        route=normalized_route,
    )


def _prepare_human_acceptance_locked(
    root: Path, resolved_feature_dir: Path
) -> dict[str, Any]:
    from .workflow_runtime import (
        MissingWorkflowState,
        WorkflowRuntimeError,
        show_workflow,
    )

    try:
        workflow = show_workflow(resolved_feature_dir)
    except MissingWorkflowState:
        workflow = None
    except WorkflowRuntimeError as exc:
        return {
            "status": "blocked",
            "error_code": "workflow-runtime-validation-blocked",
            "required_action_owner": "agent",
            "state_path": _display_path(
                resolved_feature_dir / ACCEPTANCE_FILENAME, root
            ),
            "errors": [str(exc)],
            "runtime_error": exc.to_envelope(),
            "next_command": "Repair terminal workflow evidence before any acceptance write.",
        }
    if (
        workflow is not None
        and workflow["data"].get("stage") == "accept"
        and workflow["data"].get("status") == "completed"
    ):
        return {
            "status": "blocked",
            "error_code": "terminal-feature-immutable",
            "required_action_owner": "agent",
            "state_path": _display_path(
                resolved_feature_dir / ACCEPTANCE_FILENAME, root
            ),
            "errors": [
                "The feature workflow is already terminal; its accepted evidence is immutable."
            ],
            "workflow": workflow["data"],
            "next_command": (
                "Preserve this feature and start a new sp-specify or spx-specify "
                "workflow for changed implementation scope."
            ),
        }

    summary_path = resolved_feature_dir / IMPLEMENTATION_SUMMARY_FILENAME
    state_path = resolved_feature_dir / ACCEPTANCE_FILENAME
    if not summary_path.is_file():
        return {
            "status": "blocked",
            "state_path": _display_path(state_path, root),
            "errors": [f"missing implementation summary: {summary_path}"],
            "next_command": "sp-review or spx-review",
        }

    try:
        review_contract = _approved_review_acceptance_contract(
            root, resolved_feature_dir
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        if state_path.is_file():
            try:
                existing = _read_state(state_path)
            except (OSError, ValueError, json.JSONDecodeError):
                existing = None
            if isinstance(existing, dict) and existing.get("version") == 2:
                current_summary_digest = _sha256(summary_path)
                current_evidence_digest = _implementation_snapshot_sha256(
                    root, resolved_feature_dir, current_summary_digest
                )
                source = existing.get("source")
                if isinstance(source, dict):
                    source["current_sha256"] = current_evidence_digest
                existing["status"] = "stale"
                overall = existing.get("overall")
                if isinstance(overall, dict):
                    overall.update(
                        {
                            "verdict": "pending",
                            "summary": (
                                "Approved Review is missing or stale. Review must "
                                "revalidate the current product before acceptance resumes."
                            ),
                            "next_command": "sp-review or spx-review",
                            "human_decision": "pending",
                            "decision_evidence": [],
                        }
                    )
                _write_state(state_path, existing)
                return {
                    "status": "stale",
                    "error_code": "approved-review-stale",
                    "required_action_owner": "agent",
                    "state_path": _display_path(state_path, root),
                    "prepared_from_sha256": str(
                        (source or {}).get("prepared_from_sha256") or ""
                    ),
                    "current_sha256": current_evidence_digest,
                    "errors": [str(exc)],
                    "next_command": "sp-review or spx-review",
                }
        return {
            "status": "blocked",
            "error_code": "approved-review-required",
            "required_action_owner": "agent",
            "state_path": _display_path(state_path, root),
            "errors": [str(exc)],
            "next_command": "sp-review or spx-review",
        }

    summary_digest = _sha256(summary_path)
    current_digest = _implementation_snapshot_sha256(
        root, resolved_feature_dir, summary_digest
    )
    canonical_obligations = review_contract["obligations"]
    canonical_scenarios = review_contract["scenarios"]
    source_values = {
        "implementation_summary": IMPLEMENTATION_SUMMARY_FILENAME,
        "implementation_summary_sha256": summary_digest,
        "implementation_handoff": IMPLEMENTATION_HANDOFF_FILENAME,
        "implementation_handoff_sha256": review_contract[
            "implementation_handoff_sha256"
        ],
        "review_state": REVIEW_STATE_FILENAME,
        "review_state_sha256": review_contract["review_state_sha256"],
        "reviewed_snapshot_sha256": review_contract["reviewed_snapshot_sha256"],
        "acceptance_universe_sha256": review_contract["acceptance_universe_sha256"],
        "runtime_targets_sha256": review_contract["runtime_targets_sha256"],
        "prepared_from_sha256": current_digest,
        "current_sha256": current_digest,
    }
    if state_path.exists():
        try:
            state = _read_state(state_path)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            return {
                "status": "conflict",
                "state_path": _display_path(state_path, root),
                "errors": [
                    f"existing acceptance state is unreadable and was preserved: {exc}"
                ],
                "next_command": ACCEPTANCE_COMMAND,
            }
        if state.get("version") != 2:
            return {
                "status": "conflict",
                "error_code": "acceptance-state-migration-required",
                "required_action_owner": "agent",
                "state_path": _display_path(state_path, root),
                "errors": [
                    "legacy human acceptance evidence was preserved; rebuild a v2 "
                    "guide from the frozen Human Acceptance Universe"
                ],
                "next_command": ACCEPTANCE_COMMAND,
            }
        source = state.get("source")
        if not isinstance(source, dict):
            return {
                "status": "conflict",
                "state_path": _display_path(state_path, root),
                "errors": [
                    "existing acceptance state is missing source metadata and was preserved"
                ],
                "next_command": ACCEPTANCE_COMMAND,
            }

        universe = state.get("acceptance_universe")
        actual_obligations = (
            universe.get("obligations") if isinstance(universe, dict) else None
        )
        actual_scenarios = state.get("scenarios")
        contract_drift = actual_obligations != canonical_obligations
        if isinstance(actual_scenarios, list):
            actual_contract_scenarios = [
                _scenario_contract(item)
                for item in actual_scenarios
                if isinstance(item, Mapping)
            ]
            contract_drift = contract_drift or (
                len(actual_contract_scenarios) != len(actual_scenarios)
                or actual_contract_scenarios != canonical_scenarios
            )
        else:
            contract_drift = True
        if contract_drift:
            return {
                "status": "conflict",
                "error_code": "human-acceptance-universe-drift",
                "required_action_owner": "agent",
                "state_path": _display_path(state_path, root),
                "errors": [
                    "human acceptance obligations or canonical scenarios were "
                    "deleted, downgraded, or rewritten; preserve evidence and rebuild "
                    "from the approved Review handoff"
                ],
                "next_command": ACCEPTANCE_COMMAND,
            }

        prepared_digest = str(source.get("prepared_from_sha256") or "")
        source["current_sha256"] = current_digest
        source_drift = any(
            str(source.get(key) or "") != str(source_values[key])
            for key in (
                "implementation_summary_sha256",
                "implementation_handoff_sha256",
                "review_state_sha256",
                "reviewed_snapshot_sha256",
                "acceptance_universe_sha256",
                "runtime_targets_sha256",
            )
        )
        repair_resume = state.get("repair_resume")
        if source_drift and isinstance(repair_resume, dict):
            previous_review_digest = str(
                repair_resume.get("previous_review_state_sha256") or ""
            )
            if (
                not previous_review_digest
                or previous_review_digest == review_contract["review_state_sha256"]
            ):
                return {
                    "status": "blocked",
                    "error_code": "fresh-review-required-after-acceptance-failure",
                    "required_action_owner": "agent",
                    "state_path": _display_path(state_path, root),
                    "errors": [
                        "the failed acceptance scenario requires a new approved Review "
                        "before human acceptance can resume"
                    ],
                    "next_command": "sp-review or spx-review",
                }
            review_source = review_contract["review_state"].get("source")
            expected_finding_id = str(repair_resume.get("finding_id") or "")
            expected_finding_sha256 = str(
                repair_resume.get("finding_contract_sha256") or ""
            )
            current_finding = next(
                (
                    item
                    for item in state.get("findings", [])
                    if isinstance(item, Mapping)
                    and item.get("id") == expected_finding_id
                ),
                None,
            )
            if (
                not isinstance(review_source, Mapping)
                or review_source.get("acceptance_finding_id") != expected_finding_id
                or review_source.get("acceptance_finding_sha256")
                != expected_finding_sha256
                or review_source.get("previous_review_state_sha256")
                != previous_review_digest
                or not isinstance(current_finding, Mapping)
                or _acceptance_finding_sha256(current_finding)
                != expected_finding_sha256
                or not re.fullmatch(
                    r"[0-9a-f]{64}",
                    str(review_source.get("review_cycle_id") or ""),
                )
            ):
                return {
                    "status": "blocked",
                    "error_code": "fresh-review-cycle-mismatch",
                    "required_action_owner": "agent",
                    "state_path": _display_path(state_path, root),
                    "errors": [
                        "the approved Review is not the fresh cycle created for "
                        f"acceptance finding {expected_finding_id or 'unknown'}"
                    ],
                    "next_command": "sp-review or spx-review",
                }
            source.update(source_values)
            repair_resume["new_review_state_sha256"] = review_contract[
                "review_state_sha256"
            ]
            repair_resume["review_cycle_id"] = str(
                review_source.get("review_cycle_id") or ""
            )
            repair_history = state.get("repair_history")
            if not isinstance(repair_history, list):
                return {
                    "status": "conflict",
                    "error_code": "human-acceptance-repair-history-invalid",
                    "required_action_owner": "agent",
                    "state_path": _display_path(state_path, root),
                    "errors": [
                        "human acceptance repair history is missing or invalid; "
                        "preserve the evidence and rebuild from the approved Review"
                    ],
                    "next_command": "sp-review or spx-review",
                }
            completed_repair = deepcopy(repair_resume)
            if any(
                isinstance(item, Mapping)
                and item.get("finding_id") == expected_finding_id
                for item in repair_history
            ):
                return {
                    "status": "conflict",
                    "error_code": "human-acceptance-repair-history-duplicate",
                    "required_action_owner": "agent",
                    "state_path": _display_path(state_path, root),
                    "errors": [
                        f"acceptance finding {expected_finding_id} already has a "
                        "completed Review repair record"
                    ],
                    "next_command": "sp-review or spx-review",
                }
            repair_history.append(completed_repair)
            state["runtime_targets"] = [
                _materialize_runtime_target(item)
                for item in review_contract["runtime_targets"]
            ]
            for scenario in state.get("scenarios", []):
                if isinstance(scenario, dict):
                    scenario["runtime_target_id"] = _runtime_target_id_for_scenario(
                        scenario,
                        state["runtime_targets"],
                    )
                    scenario["verdict"] = "pending"
                    for step in scenario.get("steps", []):
                        if isinstance(step, dict):
                            step["result"] = "pending"
                            step["observed_result"] = None
                            step["evidence"] = []
                            step["confirmation_id"] = _human_confirmation_id(
                                review_contract["acceptance_universe_sha256"],
                                scenario.get("id"),
                                step.get("id"),
                            )
            for finding in state.get("findings", []):
                if (
                    isinstance(finding, dict)
                    and finding.get("id") == expected_finding_id
                ):
                    finding["status"] = "resolved"
            state["status"] = "draft"
            state["overall"] = {
                "verdict": "pending",
                "summary": (
                    "A fresh Review approved the repair. Resume from the preserved "
                    "acceptance cursor on the newly verified runtime instance."
                ),
                "next_command": ACCEPTANCE_COMMAND,
                "human_decision": "pending",
                "decision_confirmation_id": _human_confirmation_id(
                    review_contract["acceptance_universe_sha256"],
                    "overall-decision",
                ),
                "decision_evidence": [],
            }
            _write_state(state_path, state)
            return {
                "status": "draft",
                "state_path": _display_path(state_path, root),
                "prepared_from_sha256": current_digest,
                "current_sha256": current_digest,
                "required_obligations": sum(
                    item.get("required") is True for item in canonical_obligations
                ),
                "required_scenarios": sum(
                    item.get("required") is True for item in canonical_scenarios
                ),
                "resume_cursor": state.get("cursor"),
                "next_command": ACCEPTANCE_COMMAND,
            }

        if source_drift or (prepared_digest and prepared_digest != current_digest):
            state["status"] = "stale"
            overall = state.get("overall")
            if isinstance(overall, dict):
                overall["verdict"] = "pending"
                overall["summary"] = (
                    "Approved Review, implementation, or acceptance-universe evidence "
                    "changed after this guide was prepared. Re-run Review before continuing."
                )
                overall["next_command"] = ACCEPTANCE_COMMAND
                overall["human_decision"] = "pending"
                overall["decision_evidence"] = []
            _write_state(state_path, state)
            return {
                "status": "stale",
                "state_path": _display_path(state_path, root),
                "prepared_from_sha256": prepared_digest,
                "current_sha256": current_digest,
                "next_command": ACCEPTANCE_COMMAND,
            }
        if not prepared_digest:
            source["prepared_from_sha256"] = current_digest
        _write_state(state_path, state)
        return {
            "status": str(state.get("status") or "draft"),
            "state_path": _display_path(state_path, root),
            "prepared_from_sha256": str(source.get("prepared_from_sha256") or ""),
            "current_sha256": current_digest,
            "required_obligations": sum(
                item.get("required") is True for item in canonical_obligations
            ),
            "required_scenarios": sum(
                item.get("required") is True for item in canonical_scenarios
            ),
            "next_command": ACCEPTANCE_COMMAND,
        }

    state = deepcopy(new_human_acceptance_state())
    state["source"] = source_values
    state["acceptance_universe"] = {
        "obligations": canonical_obligations,
        "uncovered_obligation_ids": _required_obligation_ids(canonical_obligations),
        "verdict": "pending",
    }
    state["scenarios"] = [
        _materialize_acceptance_scenario(item) for item in canonical_scenarios
    ]
    state["runtime_targets"] = [
        _materialize_runtime_target(item) for item in review_contract["runtime_targets"]
    ]
    contract_sha256 = review_contract["acceptance_universe_sha256"]
    for scenario in state["scenarios"]:
        scenario["runtime_target_id"] = _runtime_target_id_for_scenario(
            scenario,
            state["runtime_targets"],
        )
        for step in scenario["steps"]:
            step["confirmation_id"] = _human_confirmation_id(
                contract_sha256, scenario["id"], step["id"]
            )
    state["overall"]["decision_confirmation_id"] = _human_confirmation_id(
        contract_sha256, "overall-decision"
    )
    if state["scenarios"]:
        state["cursor"] = {
            "scenario_id": state["scenarios"][0]["id"],
            "step_id": state["scenarios"][0]["steps"][0]["id"],
        }
    _write_state(state_path, state)
    return {
        "status": "draft",
        "state_path": _display_path(state_path, root),
        "prepared_from_sha256": current_digest,
        "current_sha256": current_digest,
        "required_obligations": sum(
            item.get("required") is True for item in canonical_obligations
        ),
        "required_scenarios": sum(
            item.get("required") is True for item in canonical_scenarios
        ),
        "next_command": ACCEPTANCE_COMMAND,
    }


def validate_human_acceptance(
    project_root: Path,
    feature_dir: Path,
    *,
    require_accepted: bool = False,
) -> dict[str, Any]:
    """Validate canonical scope, reviewed runtime identity, human evidence, and verdict."""

    root = project_root.resolve()
    resolved_feature_dir = _resolve_feature_dir(root, feature_dir)
    state_path = resolved_feature_dir / ACCEPTANCE_FILENAME
    summary_path = resolved_feature_dir / IMPLEMENTATION_SUMMARY_FILENAME
    handoff_path = resolved_feature_dir / IMPLEMENTATION_HANDOFF_FILENAME
    review_path = resolved_feature_dir / REVIEW_STATE_FILENAME
    errors: list[str] = []
    if not state_path.is_file():
        errors.append(f"missing {ACCEPTANCE_FILENAME}")
        return _validation_payload(root, state_path, None, errors, stale=False)
    try:
        state = _read_state(state_path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        errors.append(f"invalid {ACCEPTANCE_FILENAME}: {exc}")
        return _validation_payload(root, state_path, None, errors, stale=False)

    status = str(state.get("status") or "")
    if state.get("version") != 2:
        errors.append(
            "version must equal 2; preserve legacy evidence and rebuild from approved Review"
        )
    if state.get("schema_ref") != ACCEPTANCE_SCHEMA_REF:
        errors.append(f"schema_ref must equal {ACCEPTANCE_SCHEMA_REF}")
    if status not in ACCEPTANCE_STATUSES:
        errors.append(f"unsupported acceptance status: {status or 'missing'}")

    review_contract: dict[str, Any] | None = None
    try:
        review_contract = _approved_review_acceptance_contract(
            root, resolved_feature_dir
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        errors.append(str(exc))

    source = _object(state, "source", errors)
    for key, filename in (
        ("implementation_summary", IMPLEMENTATION_SUMMARY_FILENAME),
        ("implementation_handoff", IMPLEMENTATION_HANDOFF_FILENAME),
        ("review_state", REVIEW_STATE_FILENAME),
    ):
        if source.get(key) != filename:
            errors.append(f"source.{key} must equal {filename}")
    digest_fields = (
        "implementation_summary_sha256",
        "implementation_handoff_sha256",
        "review_state_sha256",
        "reviewed_snapshot_sha256",
        "acceptance_universe_sha256",
        "runtime_targets_sha256",
        "prepared_from_sha256",
        "current_sha256",
    )
    recorded = {
        key: _required_string(source, key, "source", errors) for key in digest_fields
    }
    for key, value in recorded.items():
        if value and not re.fullmatch(r"[0-9a-f]{64}", value):
            errors.append(f"source.{key} must be a sha256 digest")

    actual_summary_digest = _sha256(summary_path) if summary_path.is_file() else ""
    actual_handoff_digest = _sha256(handoff_path) if handoff_path.is_file() else ""
    actual_review_digest = _sha256(review_path) if review_path.is_file() else ""
    if not actual_summary_digest:
        errors.append(f"missing {IMPLEMENTATION_SUMMARY_FILENAME}")
    if not actual_handoff_digest:
        errors.append(f"missing {IMPLEMENTATION_HANDOFF_FILENAME}")
    if not actual_review_digest:
        errors.append(f"missing {REVIEW_STATE_FILENAME}")
    actual_digest = (
        _implementation_snapshot_sha256(
            root, resolved_feature_dir, actual_summary_digest
        )
        if actual_summary_digest
        else ""
    )
    freshness_mismatches: list[str] = []
    for key, actual in (
        ("implementation_summary_sha256", actual_summary_digest),
        ("implementation_handoff_sha256", actual_handoff_digest),
        ("review_state_sha256", actual_review_digest),
        ("current_sha256", actual_digest),
    ):
        if actual and recorded.get(key) != actual:
            freshness_mismatches.append(key)
            errors.append(f"source.{key} does not match current evidence")
    if actual_digest and recorded.get("prepared_from_sha256") != actual_digest:
        freshness_mismatches.append("prepared_from_sha256")
        errors.append("implementation evidence changed after acceptance preparation")
    if review_contract is not None:
        for key in (
            "implementation_handoff_sha256",
            "review_state_sha256",
            "reviewed_snapshot_sha256",
            "acceptance_universe_sha256",
            "runtime_targets_sha256",
        ):
            if recorded.get(key) != str(review_contract.get(key) or ""):
                freshness_mismatches.append(key)
                errors.append(f"source.{key} no longer matches approved Review")
    stale = bool(freshness_mismatches or review_contract is None)
    if stale and status != "stale":
        errors.append(
            "Review or implementation evidence changed; status must be stale until Review is rerun"
        )
    if status == "stale" and not stale:
        errors.append("status is stale but all approved Review source identities match")

    orientation = _object(state, "orientation", errors)
    universe = _object(state, "acceptance_universe", errors)
    obligations = universe.get("obligations")
    if not isinstance(obligations, list):
        errors.append("acceptance_universe.obligations must be an array")
        obligations = []
    uncovered_recorded = universe.get("uncovered_obligation_ids")
    if not isinstance(uncovered_recorded, list) or any(
        not isinstance(item, str) or not item.strip()
        for item in (uncovered_recorded if isinstance(uncovered_recorded, list) else [])
    ):
        errors.append(
            "acceptance_universe.uncovered_obligation_ids must be a string array"
        )
        uncovered_recorded = []
    coverage_verdict = str(universe.get("verdict") or "")
    if coverage_verdict not in {"pending", "pass", "fail"}:
        errors.append("acceptance_universe.verdict must be pending, pass, or fail")

    scenarios = state.get("scenarios")
    if not isinstance(scenarios, list):
        errors.append("scenarios must be an array")
        scenarios = []
    if review_contract is not None:
        canonical_obligations = review_contract["obligations"]
        canonical_scenarios = review_contract["scenarios"]
        if obligations != canonical_obligations:
            errors.append(
                "canonical Human Acceptance Universe obligation contract drift"
            )
        actual_scenario_contracts = [
            _scenario_contract(item) for item in scenarios if isinstance(item, Mapping)
        ]
        if (
            len(actual_scenario_contracts) != len(scenarios)
            or actual_scenario_contracts != canonical_scenarios
        ):
            errors.append("canonical Human Acceptance Universe scenario contract drift")
        entrypoint_ids = set(review_contract["entrypoint_ids"])
    else:
        entrypoint_ids = set()

    runtime_targets = state.get("runtime_targets")
    if not isinstance(runtime_targets, list):
        errors.append("runtime_targets must be an array")
        runtime_targets = []
    if review_contract is not None:
        actual_runtime_contracts = [
            _review_runtime_target_contract(item)
            for item in runtime_targets
            if isinstance(item, Mapping)
        ]
        if (
            len(actual_runtime_contracts) != len(runtime_targets)
            or actual_runtime_contracts != review_contract["runtime_targets"]
        ):
            errors.append(
                "runtime_targets must exactly preserve the approved Review runtime target contract"
            )
    runtime_target_by_id: dict[str, dict[str, Any]] = {}
    for index, raw_target in enumerate(runtime_targets):
        prefix = f"runtime_targets[{index}]"
        if not isinstance(raw_target, dict):
            errors.append(f"{prefix} must be an object")
            continue
        target_id = _required_string(raw_target, "id", prefix, errors)
        if target_id in runtime_target_by_id:
            errors.append(f"duplicate runtime target id: {target_id}")
        runtime_target_by_id[target_id] = raw_target
        mode = str(raw_target.get("mode") or "")
        target_status = str(raw_target.get("status") or "")
        acceptance_status = str(raw_target.get("acceptance_status") or "")
        if mode not in RUNTIME_TARGET_MODES:
            errors.append(f"{prefix}.mode is invalid")
        if target_status != "ready":
            errors.append(f"{prefix}.status must preserve Review status=ready")
        if acceptance_status not in RUNTIME_TARGET_STATUSES:
            errors.append(f"{prefix}.acceptance_status is invalid")
        entrypoint_id = _required_string(raw_target, "entrypoint_id", prefix, errors)
        if entrypoint_ids and entrypoint_id not in entrypoint_ids:
            errors.append(f"{prefix}.entrypoint_id is not an official entrypoint")
        for key in (
            "environment_ref",
            "instance_ref",
            "configuration_ref",
            "reviewed_snapshot_sha256",
            "identity_evidence_ref",
            "identity_evidence_sha256",
        ):
            _required_string(raw_target, key, prefix, errors)
        identity_digest = str(raw_target.get("identity_evidence_sha256") or "")
        if identity_digest and not re.fullmatch(r"[0-9a-f]{64}", identity_digest):
            errors.append(f"{prefix}.identity_evidence_sha256 must be a sha256 digest")
        if (
            recorded.get("reviewed_snapshot_sha256")
            and raw_target.get("reviewed_snapshot_sha256")
            != recorded["reviewed_snapshot_sha256"]
        ):
            errors.append(
                f"{prefix}.reviewed_snapshot_sha256 must match approved Review"
            )
        for key in (
            "test_data_refs",
            "ready_evidence_refs",
            "review_scenario_ids",
            "acceptance_ready_evidence",
            "agent_actions",
        ):
            values = raw_target.get(key)
            if not isinstance(values, list) or any(
                not isinstance(item, str) or not item.strip()
                for item in (values if isinstance(values, list) else [])
            ):
                errors.append(f"{prefix}.{key} must be a string array")
        if acceptance_status == "ready":
            _nonempty_string_list(
                raw_target, "acceptance_ready_evidence", prefix, errors
            )
            _nonempty_string_list(raw_target, "agent_actions", prefix, errors)
        if mode in {"build", "deployment"}:
            _required_string(raw_target, "artifact_ref", prefix, errors)
            artifact_digest = _required_string(
                raw_target, "artifact_sha256", prefix, errors
            )
            if artifact_digest and not re.fullmatch(r"[0-9a-f]{64}", artifact_digest):
                errors.append(f"{prefix}.artifact_sha256 must be a sha256 digest")
        if mode == "deployment":
            _required_string(raw_target, "deployment_id", prefix, errors)
            _required_string(raw_target, "observed_version", prefix, errors)

    findings = state.get("findings")
    if not isinstance(findings, list):
        errors.append("findings must be an array")
        findings = []
    cursor = _object(state, "cursor", errors)
    overall = _object(state, "overall", errors)
    overall_verdict = str(overall.get("verdict") or "")
    if overall_verdict not in OVERALL_VERDICTS:
        errors.append("overall.verdict must be pending, pass, fail, or blocked")
    human_decision = str(overall.get("human_decision") or "")
    if human_decision not in HUMAN_DECISIONS:
        errors.append("overall.human_decision must be pending, accept, or reject")
    decision_evidence = overall.get("decision_evidence")
    if not isinstance(decision_evidence, list):
        errors.append("overall.decision_evidence must be an array")
        decision_evidence = []
    decision_confirmation_id = _required_string(
        overall, "decision_confirmation_id", "overall", errors
    )

    if status not in {"draft", "stale"}:
        for key in ("outcome", "why_it_matters", "start_here"):
            _required_string(orientation, key, "orientation", errors)
        _nonempty_string_list(
            orientation, "user_visible_changes", "orientation", errors
        )
        if not scenarios:
            errors.append("the frozen Human Acceptance Universe has no scenarios")

    scenario_ids: set[str] = set()
    step_ids: set[str] = set()
    required_verdicts: list[str] = []
    any_failed = False
    any_blocked = False
    for index, raw_scenario in enumerate(scenarios):
        prefix = f"scenarios[{index}]"
        if not isinstance(raw_scenario, dict):
            errors.append(f"{prefix} must be an object")
            continue
        scenario_id = _required_string(raw_scenario, "id", prefix, errors)
        if scenario_id in scenario_ids:
            errors.append(f"duplicate scenario id: {scenario_id}")
        scenario_ids.add(scenario_id)
        for key in ("title", "user_value", "entrypoint_id", "start_state"):
            _required_string(raw_scenario, key, prefix, errors)
        obligation_ids = raw_scenario.get("obligation_ids")
        if not isinstance(obligation_ids, list) or not obligation_ids:
            errors.append(f"{prefix}.obligation_ids must be a non-empty array")
        required = raw_scenario.get("required")
        if not isinstance(required, bool):
            errors.append(f"{prefix}.required must be a boolean")
            required = False
        verdict = str(raw_scenario.get("verdict") or "")
        if verdict not in SCENARIO_VERDICTS:
            errors.append(f"{prefix}.verdict is invalid")
        if required:
            required_verdicts.append(verdict)
        any_failed = any_failed or verdict == "fail"
        any_blocked = any_blocked or verdict == "blocked"
        runtime_target_id = raw_scenario.get("runtime_target_id")
        target = (
            runtime_target_by_id.get(str(runtime_target_id))
            if runtime_target_id is not None
            else None
        )
        if verdict == "pass" or status in {"ready", "in_progress", "accepted"}:
            if target is None or target.get("acceptance_status") != "ready":
                errors.append(
                    f"{prefix} requires a ready runtime target bound to approved Review"
                )
            elif target.get("entrypoint_id") != raw_scenario.get("entrypoint_id"):
                errors.append(
                    f"{prefix}.runtime_target_id must use the scenario official entrypoint"
                )
            elif not set(raw_scenario.get("review_scenario_ids") or []).issubset(
                set(target.get("review_scenario_ids") or [])
            ):
                errors.append(
                    f"{prefix}.runtime_target_id must cover the scenario linked Review evidence"
                )
        steps = raw_scenario.get("steps")
        if not isinstance(steps, list) or not steps:
            errors.append(f"{prefix}.steps must contain at least one step")
            continue
        scenario_step_results: list[str] = []
        for step_index, raw_step in enumerate(steps):
            step_prefix = f"{prefix}.steps[{step_index}]"
            if not isinstance(raw_step, dict):
                errors.append(f"{step_prefix} must be an object")
                continue
            step_id = _required_string(raw_step, "id", step_prefix, errors)
            if step_id in step_ids:
                errors.append(f"duplicate step id: {step_id}")
            step_ids.add(step_id)
            for key in (
                "action",
                "expected_result",
                "evidence_requirement",
                "risk",
                "if_failed",
                "response_prompt",
            ):
                _required_string(raw_step, key, step_prefix, errors)
            result = str(raw_step.get("result") or "")
            scenario_step_results.append(result)
            if result not in STEP_RESULTS:
                errors.append(f"{step_prefix}.result is invalid")
            any_failed = any_failed or result == "fail"
            any_blocked = any_blocked or result == "blocked"
            evidence = raw_step.get("evidence")
            if not isinstance(evidence, list):
                errors.append(f"{step_prefix}.evidence must be an array")
                evidence = []
            confirmation_id = _required_string(
                raw_step, "confirmation_id", step_prefix, errors
            )
            if result == "pass":
                _required_string(raw_step, "observed_result", step_prefix, errors)
                if not _has_human_evidence(
                    evidence,
                    confirmation_id=confirmation_id,
                    runtime_target_id=str(runtime_target_id or ""),
                    reviewed_snapshot_sha256=recorded.get(
                        "reviewed_snapshot_sha256", ""
                    ),
                ):
                    errors.append(
                        f"{step_prefix}.result=pass requires a structured human confirmation; "
                        "agent or automated evidence cannot substitute"
                    )
        if verdict == "pass" and any(
            result != "pass" for result in scenario_step_results
        ):
            errors.append(f"{prefix}.verdict=pass requires every step to pass")

    actual_uncovered = _uncovered_obligation_ids(obligations, scenarios)
    if sorted(uncovered_recorded) != actual_uncovered:
        errors.append(
            "acceptance_universe.uncovered_obligation_ids must exactly match "
            "required obligation coverage"
        )
    if status == "accepted":
        if actual_uncovered:
            errors.append(
                "accepted status requires zero uncovered Human Acceptance obligations"
            )
        if coverage_verdict != "pass":
            errors.append("accepted status requires acceptance_universe.verdict=pass")

    open_finding_ids: list[str] = []
    for index, raw_finding in enumerate(findings):
        prefix = f"findings[{index}]"
        if not isinstance(raw_finding, dict):
            errors.append(f"{prefix} must be an object")
            continue
        finding_id = _required_string(raw_finding, "id", prefix, errors)
        for key in ("scenario_id", "step_id", "expected", "observed"):
            _required_string(raw_finding, key, prefix, errors)
        if raw_finding.get("scenario_id") not in scenario_ids:
            errors.append(f"{prefix}.scenario_id must reference an existing scenario")
        if raw_finding.get("step_id") not in step_ids:
            errors.append(f"{prefix}.step_id must reference an existing step")
        classification = raw_finding.get("classification")
        route = raw_finding.get("route")
        if classification not in FINDING_CLASSIFICATIONS:
            errors.append(f"{prefix}.classification is invalid")
        if route not in FINDING_ROUTES:
            errors.append(f"{prefix}.route is invalid")
        if route == "human-action" and classification != "environment-or-access":
            errors.append(
                f"{prefix}.route=human-action is only valid for environment-or-access"
            )
        if route != "human-action" and route not in {"sp-review", "spx-review"}:
            errors.append(f"{prefix} must route every failed observation to Review")
        finding_status = raw_finding.get("status")
        if finding_status not in {"open", "resolved"}:
            errors.append(f"{prefix}.status must be open or resolved")
        elif finding_status == "open":
            open_finding_ids.append(finding_id or prefix)
        evidence = raw_finding.get("evidence")
        if not isinstance(evidence, list) or not evidence:
            errors.append(f"{prefix}.evidence must be a non-empty array")

    cursor_scenario = cursor.get("scenario_id")
    cursor_step = cursor.get("step_id")
    if status == "in_progress":
        if cursor_scenario not in scenario_ids:
            errors.append(
                "in_progress state requires cursor.scenario_id to name a scenario"
            )
        if cursor_step not in step_ids:
            errors.append("in_progress state requires cursor.step_id to name a step")
    elif cursor_scenario is not None or cursor_step is not None:
        if cursor_scenario not in scenario_ids or cursor_step not in step_ids:
            errors.append(
                "cursor must be null or reference an existing scenario and step"
            )

    repair_resume = state.get("repair_resume")
    if repair_resume is not None and not isinstance(repair_resume, dict):
        errors.append("repair_resume must be null or an object")
    elif isinstance(repair_resume, dict):
        finding_id = _required_string(
            repair_resume, "finding_id", "repair_resume", errors
        )
        finding_contract_sha256 = _required_string(
            repair_resume,
            "finding_contract_sha256",
            "repair_resume",
            errors,
        )
        if finding_contract_sha256 and not re.fullmatch(
            r"[0-9a-f]{64}", finding_contract_sha256
        ):
            errors.append(
                "repair_resume.finding_contract_sha256 must be a sha256 digest"
            )
        previous_review_sha256 = _required_string(
            repair_resume,
            "previous_review_state_sha256",
            "repair_resume",
            errors,
        )
        new_review_sha256 = str(repair_resume.get("new_review_state_sha256") or "")
        review_cycle_id = str(repair_resume.get("review_cycle_id") or "")
        if previous_review_sha256 and not re.fullmatch(
            r"[0-9a-f]{64}", previous_review_sha256
        ):
            errors.append(
                "repair_resume.previous_review_state_sha256 must be a sha256 digest"
            )
        for key in (
            "affected_obligation_ids",
            "affected_scenario_ids",
            "preserved_scenario_ids",
        ):
            values = repair_resume.get(key)
            if not isinstance(values, list) or any(
                not isinstance(item, str) or not item.strip()
                for item in (values if isinstance(values, list) else [])
            ):
                errors.append(f"repair_resume.{key} must be a string array")
        expected_obligation_ids = sorted(
            str(item.get("id") or "")
            for item in obligations
            if isinstance(item, Mapping) and str(item.get("id") or "").strip()
        )
        if sorted(repair_resume.get("affected_obligation_ids") or []) != (
            expected_obligation_ids
        ):
            errors.append(
                "repair_resume must conservatively retest every human acceptance obligation"
            )
        if (
            sorted(repair_resume.get("affected_scenario_ids") or [])
            != sorted(scenario_ids)
            or repair_resume.get("preserved_scenario_ids") != []
        ):
            errors.append(
                "repair_resume must retest every human scenario and preserve no stale PASS"
            )
        if repair_resume.get("scenario_id") not in scenario_ids:
            errors.append("repair_resume.scenario_id must name the failed scenario")
        if repair_resume.get("step_id") not in step_ids:
            errors.append("repair_resume.step_id must name the failed step")
        repair_finding = next(
            (
                item
                for item in findings
                if isinstance(item, Mapping) and item.get("id") == finding_id
            ),
            None,
        )
        if not isinstance(repair_finding, Mapping):
            errors.append(
                "repair_resume.finding_id must reference an acceptance finding"
            )
        elif _acceptance_finding_sha256(repair_finding) != finding_contract_sha256:
            errors.append(
                "repair_resume.finding_contract_sha256 must bind the routed acceptance finding"
            )
        if new_review_sha256:
            if new_review_sha256 != recorded.get("review_state_sha256"):
                errors.append(
                    "repair_resume.new_review_state_sha256 must match the approved Review"
                )
            if not re.fullmatch(r"[0-9a-f]{64}", review_cycle_id):
                errors.append(
                    "repair_resume.review_cycle_id must bind the approved repair Review"
                )
        elif review_cycle_id:
            errors.append(
                "repair_resume.review_cycle_id requires new_review_state_sha256"
            )

    repair_history = state.get("repair_history")
    if not isinstance(repair_history, list):
        errors.append("repair_history must be an array")
        repair_history = []
    completed_repair_by_finding: dict[str, list[Mapping[str, Any]]] = {}
    prior_completed_review_sha256 = ""
    for index, raw_repair in enumerate(repair_history):
        prefix = f"repair_history[{index}]"
        if not isinstance(raw_repair, Mapping):
            errors.append(f"{prefix} must be an object")
            continue
        history_finding_id = _required_string(raw_repair, "finding_id", prefix, errors)
        history_finding_sha256 = _required_string(
            raw_repair, "finding_contract_sha256", prefix, errors
        )
        previous_review_sha256 = _required_string(
            raw_repair, "previous_review_state_sha256", prefix, errors
        )
        completed_review_sha256 = _required_string(
            raw_repair, "new_review_state_sha256", prefix, errors
        )
        completed_cycle_id = _required_string(
            raw_repair, "review_cycle_id", prefix, errors
        )
        for key, value in (
            ("finding_contract_sha256", history_finding_sha256),
            ("previous_review_state_sha256", previous_review_sha256),
            ("new_review_state_sha256", completed_review_sha256),
            ("review_cycle_id", completed_cycle_id),
        ):
            if value and not re.fullmatch(r"[0-9a-f]{64}", value):
                errors.append(f"{prefix}.{key} must be a sha256 digest")
        for key in (
            "affected_obligation_ids",
            "affected_scenario_ids",
            "preserved_scenario_ids",
        ):
            values = raw_repair.get(key)
            if not isinstance(values, list) or any(
                not isinstance(item, str) or not item.strip()
                for item in (values if isinstance(values, list) else [])
            ):
                errors.append(f"{prefix}.{key} must be a string array")
        expected_obligation_ids = sorted(
            str(item.get("id") or "")
            for item in obligations
            if isinstance(item, Mapping) and str(item.get("id") or "").strip()
        )
        if sorted(raw_repair.get("affected_obligation_ids") or []) != (
            expected_obligation_ids
        ):
            errors.append(f"{prefix} must record every human acceptance obligation")
        if (
            sorted(raw_repair.get("affected_scenario_ids") or [])
            != sorted(scenario_ids)
            or raw_repair.get("preserved_scenario_ids") != []
        ):
            errors.append(
                f"{prefix} must retest every human scenario and preserve no stale PASS"
            )
        if raw_repair.get("scenario_id") not in scenario_ids:
            errors.append(f"{prefix}.scenario_id must name the failed scenario")
        if raw_repair.get("step_id") not in step_ids:
            errors.append(f"{prefix}.step_id must name the failed step")
        history_finding = next(
            (
                item
                for item in findings
                if isinstance(item, Mapping) and item.get("id") == history_finding_id
            ),
            None,
        )
        if not isinstance(history_finding, Mapping):
            errors.append(f"{prefix}.finding_id must reference an acceptance finding")
        else:
            if history_finding.get("route") not in {"sp-review", "spx-review"}:
                errors.append(f"{prefix} may record only a Review-routed finding")
            if history_finding.get("status") != "resolved":
                errors.append(f"{prefix} requires its finding status to be resolved")
            if _acceptance_finding_sha256(history_finding) != history_finding_sha256:
                errors.append(
                    f"{prefix}.finding_contract_sha256 must bind the routed finding"
                )
        if index and previous_review_sha256 != prior_completed_review_sha256:
            errors.append(
                f"{prefix}.previous_review_state_sha256 must continue the repair history chain"
            )
        prior_completed_review_sha256 = completed_review_sha256
        if history_finding_id:
            completed_repair_by_finding.setdefault(history_finding_id, []).append(
                raw_repair
            )

    review_routed_resolved = [
        item
        for item in findings
        if isinstance(item, Mapping)
        and item.get("route") in {"sp-review", "spx-review"}
        and item.get("status") == "resolved"
    ]
    for finding in review_routed_resolved:
        finding_id = str(finding.get("id") or "")
        matching_repairs = completed_repair_by_finding.get(finding_id, [])
        if len(matching_repairs) != 1:
            errors.append(
                "resolved Review finding requires a completed route-repair cycle: "
                f"{finding_id or 'missing-finding'}"
            )

    if repair_history:
        last_repair = repair_history[-1]
        if isinstance(last_repair, Mapping):
            if recorded.get("review_state_sha256") and last_repair.get(
                "new_review_state_sha256"
            ) != recorded.get("review_state_sha256"):
                errors.append(
                    "the latest repair history entry must bind the current approved Review"
                )
            if review_contract is not None:
                review_state = review_contract.get("review_state")
                review_source = (
                    review_state.get("source")
                    if isinstance(review_state, Mapping)
                    else None
                )
                if not isinstance(review_source, Mapping) or any(
                    last_repair.get(history_key) != review_source.get(review_key)
                    for history_key, review_key in (
                        ("finding_id", "acceptance_finding_id"),
                        (
                            "finding_contract_sha256",
                            "acceptance_finding_sha256",
                        ),
                        (
                            "previous_review_state_sha256",
                            "previous_review_state_sha256",
                        ),
                        ("review_cycle_id", "review_cycle_id"),
                    )
                ):
                    errors.append(
                        "the latest repair history entry must match the current "
                        "Review repair source"
                    )
        if (
            isinstance(repair_resume, Mapping)
            and repair_resume.get("new_review_state_sha256")
            and repair_resume != repair_history[-1]
        ):
            errors.append(
                "completed repair_resume must equal the latest repair_history entry"
            )
    elif isinstance(repair_resume, Mapping) and repair_resume.get(
        "new_review_state_sha256"
    ):
        errors.append("completed repair_resume requires a repair_history entry")

    if status in {"draft", "ready", "in_progress"} and overall_verdict != "pending":
        errors.append(f"{status} status requires overall.verdict=pending")
    if status == "accepted":
        if not required_verdicts or any(
            verdict != "pass" for verdict in required_verdicts
        ):
            errors.append("accepted status requires every required scenario to pass")
        if overall_verdict != "pass":
            errors.append("accepted status requires overall.verdict=pass")
        if human_decision != "accept" or not _has_human_evidence(
            decision_evidence,
            confirmation_id=decision_confirmation_id,
            runtime_target_id="all-reviewed-targets",
            reviewed_snapshot_sha256=recorded.get("reviewed_snapshot_sha256", ""),
        ):
            errors.append(
                "accepted status requires an explicit human acceptance decision and evidence"
            )
        if open_finding_ids:
            errors.append(
                "accepted status requires every finding to be resolved; "
                f"open findings: {', '.join(open_finding_ids)}"
            )
    if status == "rejected" and not any_failed:
        errors.append("rejected status requires a failed step or scenario")
    if status == "rejected" and overall_verdict != "fail":
        errors.append("rejected status requires overall.verdict=fail")
    if status == "rejected" and not findings:
        errors.append("rejected status requires a routed acceptance finding")
    if status == "blocked" and not any_blocked and not findings:
        errors.append("blocked status requires a blocked step/scenario or a finding")
    if status == "blocked" and overall_verdict != "blocked":
        errors.append("blocked status requires overall.verdict=blocked")
    if status == "blocked" and not findings:
        errors.append("blocked status requires a routed acceptance finding")
    contract_valid = not errors
    if require_accepted and status != "accepted":
        errors.append("human acceptance closeout requires status=accepted")

    return _validation_payload(
        root,
        state_path,
        state,
        errors,
        stale=stale,
        contract_valid=contract_valid,
    )


def acceptance_closeout_blockers(
    feature_dir: Path,
    *,
    acceptance: Mapping[str, Any] | None = None,
    hook_errors: list[str] | None = None,
    runtime: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Build canonical blockers for prepare/validate/closeout CLI stops."""

    blockers: list[dict[str, Any]] = []
    context = dict(acceptance or {})
    closeout_argv = [
        "specify",
        "accept",
        "closeout",
        "--feature-dir",
        str(feature_dir),
        "--format",
        "json",
    ]
    prepare_argv = [
        "specify",
        "accept",
        "prepare",
        "--feature-dir",
        str(feature_dir),
        "--format",
        "json",
    ]
    show_argv = [
        "specify",
        "workflow",
        "show",
        "--feature-dir",
        str(feature_dir),
        "--format",
        "json",
    ]
    errors = [
        str(item).strip() for item in (context.get("errors") or []) if str(item).strip()
    ]
    runtime_error = context.get("runtime_error")
    if context.get(
        "error_code"
    ) == "workflow-runtime-validation-blocked" and isinstance(runtime_error, Mapping):
        runtime_blockers = runtime_error.get("blockers")
        if isinstance(runtime_blockers, list) and runtime_blockers:
            blockers.extend(
                dict(item) for item in runtime_blockers if isinstance(item, Mapping)
            )
            errors = []
    if errors:
        status = str(context.get("status") or "missing").strip().lower()
        contract_valid = context.get("contract_valid") is True
        routes = [
            dict(item)
            for item in (context.get("finding_routes") or [])
            if isinstance(item, Mapping) and item.get("status") == "open"
        ]
        routed = routes[0] if routes else {}
        route = str(routed.get("route") or "")
        needs_human = (
            context.get("required_action_owner") == "user"
            or route == "human-action"
            or (contract_valid and status in {"draft", "ready", "in_progress"})
        )
        if needs_human:
            category = "human-review"
            owner = "user"
            summary = "Human product acceptance has not reached an accepted verdict."
            exact_next_action = (
                "Run sp-accept or spx-accept and guide the human through every "
                "required real-product scenario before retrying closeout."
            )
            resume_argv = closeout_argv
        elif route in ACCEPTANCE_REPAIR_TARGETS:
            category = "artifact-or-state"
            owner = "agent"
            summary = "A rejected or blocked acceptance finding requires agent-owned repair routing."
            exact_next_action = (
                f"Run accept route-repair for finding {routed.get('id') or 'unknown'} "
                f"through {route}, using sanitized evidence already recorded by the "
                "human, then resume the owning stage."
            )
            resume_argv = show_argv
        elif context.get("error_code") == "terminal-feature-immutable":
            category = "conflict-or-drift"
            owner = "agent"
            summary = "The terminal feature and its accepted evidence are immutable."
            exact_next_action = str(
                context.get("next_command")
                or "Preserve this feature and start a new specification workflow for changed scope."
            )
            resume_argv = show_argv
        else:
            category = "artifact-or-state"
            owner = "agent"
            summary = "The human acceptance artifact is missing, stale, unreadable, or invalid."
            exact_next_action = (
                "Preserve any recoverable human evidence, then use accept prepare and "
                "the owning SP/SPX acceptance workflow to deterministically rebuild or "
                "repair human-acceptance.json before asking the human to continue."
            )
            resume_argv = prepare_argv
        blockers.append(
            _acceptance_blocker(
                blocker_id="ACCEPTANCE-NOT-CLOSED",
                category=category,
                owner=owner,
                summary=summary,
                evidence=errors,
                exact_next_action=exact_next_action,
                unblock_criteria=(
                    "human-acceptance.json is fresh and schema-valid, every required "
                    "obligation is covered, every required scenario has explicit human "
                    "PASS evidence against a ready reviewed runtime target, no finding "
                    "is open, and the human decision is accept."
                ),
                resume_argv=resume_argv,
                human_action_required=needs_human,
            )
        )
    if runtime is not None:
        runtime_data = runtime.get("data")
        runtime_data = dict(runtime_data) if isinstance(runtime_data, Mapping) else {}
        stage = str(runtime_data.get("stage") or "missing")
        status = str(runtime_data.get("status") or "missing")
        runtime_next = runtime.get("next_argv")
        runtime_show = runtime.get("show_argv")
        resume_argv = (
            [str(item) for item in runtime_next]
            if isinstance(runtime_next, list) and runtime_next
            else (
                [str(item) for item in runtime_show]
                if isinstance(runtime_show, list) and runtime_show
                else show_argv
            )
        )
        blockers.append(
            _acceptance_blocker(
                blocker_id="ACCEPTANCE-RUNTIME-OWNER",
                category="workflow-validation",
                owner="agent",
                summary=(
                    "Acceptance is valid, but the phase runtime is not active at accept."
                ),
                evidence=[
                    f"workflow stage/status: {stage}/{status}",
                    "required workflow stage/status: accept/active",
                ],
                exact_next_action=(
                    "Follow the phase runtime's exact next_argv until accept is active; "
                    "do not reconstruct or skip a stage."
                ),
                unblock_criteria="The workflow runtime is active at accept at its current revision.",
                resume_argv=resume_argv,
                human_action_required=False,
            )
        )
    hook_evidence = [
        str(item).strip() for item in (hook_errors or []) if str(item).strip()
    ]
    if hook_evidence:
        blockers.append(
            _acceptance_blocker(
                blocker_id="ACCEPTANCE-WORKFLOW-STATE",
                category="artifact-or-state",
                owner="agent",
                summary="Acceptance workflow state is not valid for closeout.",
                evidence=hook_evidence,
                exact_next_action="Repair the acceptance workflow state and rerun its deterministic validator.",
                unblock_criteria="The acceptance artifact and workflow-state validators both pass.",
                resume_argv=closeout_argv,
                human_action_required=False,
            )
        )
    return blockers


def _acceptance_blocker(
    *,
    blocker_id: str,
    category: str,
    owner: str,
    summary: str,
    evidence: list[str],
    exact_next_action: str,
    unblock_criteria: str,
    resume_argv: list[str],
    human_action_required: bool,
) -> dict[str, Any]:
    resume_command = render_command(tuple(resume_argv))
    blocker: dict[str, Any] = {
        "version": 1,
        "blocker_id": blocker_id,
        "code": "human-acceptance-blocked",
        "workflow": "sp-accept|spx-accept",
        "stage": "human acceptance closeout",
        "category": category,
        "owner": owner,
        "summary": summary,
        "details": "The feature cannot close until a fresh, explicit human product verdict satisfies the acceptance contract.",
        "evidence": evidence,
        "attempted_recovery": [
            {
                "action": "Validate the acceptance artifact and workflow state.",
                "result": "One or more closeout requirements remain unsatisfied.",
            }
        ],
        "exact_next_action": exact_next_action,
        "unblock_criteria": unblock_criteria,
        "affected_scope": ["human product acceptance", "feature closeout"],
        "can_continue": False,
        "human_action_required": human_action_required,
        "human_action_guide": None,
        "resume": {
            "instruction": f"After the acceptance state is repaired, run: {resume_command}",
            "command": resume_command,
            "argv": resume_argv,
        },
    }
    if human_action_required:
        blocker["human_action_guide"] = {
            "goal": "Decide whether the implemented feature works for a real user and explicitly accept or reject it.",
            "why_human": "Automated checks can prove technical conditions, but only a human can make the required product-acceptance judgment.",
            "prerequisites": [
                "Ask the agent to run sp-accept or spx-accept for this feature.",
                "Access to the real application entry point and any test account or data named by the guide.",
                "The generated implementation-summary.md and human-acceptance.json.",
            ],
            "safety_notes": [
                "Do not paste passwords, tokens, cookies, private keys, or unredacted personal data into chat.",
                "Do not approve from automated test output alone; observe each required user-facing result.",
                "If the app, account, environment, or expected behavior is unclear, record blocked instead of guessing.",
            ],
            "steps": [
                {
                    "order": 1,
                    "title": "Let the agent restore context",
                    "action": "Run sp-accept or spx-accept and read the short explanation of what changed, why it matters, and where to start.",
                    "command": None,
                    "expected_result": "You understand the feature outcome, prerequisites, and first real entry point without rereading the implementation history.",
                    "if_failed": "Ask the agent to repair the acceptance guide; do not continue with an unclear target.",
                },
                {
                    "order": 2,
                    "title": "Follow one observable step at a time",
                    "action": "For each required scenario, perform exactly the action the agent presents and report what you actually observe.",
                    "command": None,
                    "expected_result": "Every step receives pass, fail, or blocked plus evidence when requested.",
                    "if_failed": "Describe the observed result and let the agent record and route the finding; do not silently retry or reinterpret it.",
                },
                {
                    "order": 3,
                    "title": "Review the final verdict",
                    "action": "Accept only when every required obligation is covered and every required scenario passes against the reviewed runtime; otherwise reject or block and confirm the routed findings.",
                    "command": None,
                    "expected_result": "human-acceptance.json records one explicit, evidence-backed overall verdict.",
                    "if_failed": "Leave the verdict pending and name the unresolved scenario or decision.",
                },
                {
                    "order": 4,
                    "title": "Close the feature",
                    "action": f"After an accepted verdict, ask the agent to run `{resume_command}`.",
                    "command": resume_command,
                    "expected_result": "The closeout command succeeds without an acceptance or workflow-state blocker.",
                    "if_failed": "Return the complete blocker JSON to the agent and follow its exact resume instructions.",
                },
            ],
            "verification": [
                "Every required obligation is covered and every required scenario and step passed",
                "Every pass is a human observation against a ready runtime target bound to the reviewed snapshot",
                "The human decision is accept, the overall verdict is pass, and status is accepted",
                "No open acceptance finding remains unresolved",
            ],
            "evidence_to_return": [
                "PASS, REJECT, or BLOCKED for each required scenario",
                "Any requested screenshots, output, or IDs with secrets redacted",
                "The final overall acceptance decision",
            ],
            "resume_instruction": f"Return the verdict and evidence to the agent, then resume with `{resume_command}`.",
        }
    return blocker


def _read_state(path: Path) -> dict[str, Any]:
    payload = json.loads(read_local_state_text(path, root=path.parent))
    if not isinstance(payload, dict):
        raise ValueError("top-level JSON must be an object")
    return payload


def _write_state(path: Path, state: dict[str, Any]) -> None:
    atomic_write_text(
        path,
        json.dumps(state, ensure_ascii=False, indent=2) + "\n",
    )


def _resolve_feature_dir(project_root: Path, feature_dir: Path) -> Path:
    resolved = (
        feature_dir.resolve(strict=False)
        if feature_dir.is_absolute()
        else (project_root / feature_dir).resolve(strict=False)
    )
    try:
        relative = resolved.relative_to(project_root.resolve(strict=False))
    except ValueError as exc:
        raise ValueError("feature_dir must stay inside the current project") from exc
    if not relative.parts:
        raise ValueError("feature_dir must identify a directory below the project root")
    return resolved


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _implementation_snapshot_sha256(
    project_root: Path, feature_dir: Path, summary_digest: str
) -> str:
    """Bind acceptance to summary plus current implementation working-tree evidence."""

    digest = hashlib.sha256()
    digest.update(f"summary:{summary_digest}\n".encode("utf-8"))
    try:
        feature_relative = feature_dir.resolve().relative_to(project_root.resolve())
        feature_pathspec = feature_relative.as_posix().rstrip("/") + "/**"
    except ValueError:
        feature_relative = None
        feature_pathspec = ""
    exclusions = [
        ":(exclude).specify/runtime/**",
        ":(exclude).planning/**",
    ]
    if feature_pathspec:
        exclusions.append(f":(exclude){feature_pathspec}")

    head = _run_git_bytes(project_root, ["rev-parse", "HEAD"])
    if head is None:
        _update_no_git_snapshot(digest, project_root, feature_relative)
        return digest.hexdigest()
    digest.update(b"head:")
    digest.update(head.strip())
    digest.update(b"\n")

    diff = _run_git_bytes(
        project_root, ["diff", "--binary", "HEAD", "--", ".", *exclusions]
    )
    if diff is not None:
        digest.update(b"diff:\n")
        digest.update(diff)

    untracked = _run_git_bytes(
        project_root,
        [
            "ls-files",
            "--others",
            "--exclude-standard",
            "-z",
            "--",
            ".",
            *exclusions,
        ],
    )
    if untracked:
        for raw_path in sorted(path for path in untracked.split(b"\0") if path):
            relative = raw_path.decode("utf-8", errors="surrogateescape")
            digest.update(b"untracked:")
            digest.update(raw_path)
            digest.update(b"\0")
            target = project_root / relative
            if target.is_file():
                digest.update(target.read_bytes())
            digest.update(b"\0")
    return digest.hexdigest()


def _update_no_git_snapshot(
    digest: Any,
    project_root: Path,
    feature_relative: Path | None,
) -> None:
    """Hash a deterministic project tree when Git cannot provide a snapshot."""

    root = project_root.resolve(strict=False)
    ignore_spec = _root_gitignore_spec(root)
    digest.update(b"tree-fallback:v1\n")
    pending = [root]
    while pending:
        directory = pending.pop()
        with os.scandir(directory) as iterator:
            entries = sorted(iterator, key=lambda entry: entry.name)
        child_directories: list[Path] = []
        for entry in entries:
            entry_path = Path(entry.path)
            relative = entry_path.relative_to(root)
            is_junction = getattr(entry_path, "is_junction", None)
            is_link = entry.is_symlink() or (
                callable(is_junction) and bool(is_junction())
            )
            is_directory = not is_link and entry.is_dir(follow_symlinks=False)
            if _no_git_snapshot_excluded(
                relative,
                feature_relative,
                ignore_spec=ignore_spec,
                is_directory=is_directory,
            ):
                continue
            if is_link:
                _update_no_git_snapshot_record(
                    digest,
                    "link",
                    relative,
                    os.readlink(entry_path),
                )
            elif is_directory:
                child_directories.append(entry_path)
            elif entry.is_file(follow_symlinks=False):
                _update_no_git_snapshot_record(
                    digest,
                    "file",
                    relative,
                    _sha256(entry_path),
                )
            else:
                _update_no_git_snapshot_record(digest, "other", relative, "")
        pending.extend(reversed(child_directories))


def _no_git_snapshot_excluded(
    relative: Path,
    feature_relative: Path | None,
    *,
    ignore_spec: pathspec.GitIgnoreSpec | None,
    is_directory: bool,
) -> bool:
    if feature_relative is not None and (
        relative == feature_relative or feature_relative in relative.parents
    ):
        return True
    parts = relative.parts
    if not parts:
        return False
    if parts[0] in {".git", ".planning"}:
        return True
    if len(parts) >= 2 and parts[:2] == (".specify", "runtime"):
        return True
    if ignore_spec is None:
        return False
    normalized = relative.as_posix() + ("/" if is_directory else "")
    return ignore_spec.match_file(normalized)


def _root_gitignore_spec(project_root: Path) -> pathspec.GitIgnoreSpec | None:
    ignore_path = project_root / ".gitignore"
    try:
        lines = ignore_path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return None
    if not lines:
        return None
    return pathspec.GitIgnoreSpec.from_lines(lines)


def _update_no_git_snapshot_record(
    digest: Any,
    kind: str,
    relative: Path,
    value: str,
) -> None:
    record = json.dumps(
        [kind, relative.as_posix(), value],
        ensure_ascii=False,
        separators=(",", ":"),
    )
    digest.update(record.encode("utf-8", errors="surrogateescape"))
    digest.update(b"\n")


def _run_git_bytes(project_root: Path, args: list[str]) -> bytes | None:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=project_root,
            capture_output=True,
            check=False,
        )
    except (OSError, ValueError):
        return None
    if result.returncode != 0:
        return None
    return result.stdout


def _object(payload: dict[str, Any], key: str, errors: list[str]) -> dict[str, Any]:
    value = payload.get(key)
    if not isinstance(value, dict):
        errors.append(f"{key} must be an object")
        return {}
    return value


def _required_string(
    payload: dict[str, Any], key: str, prefix: str, errors: list[str]
) -> str:
    value = str(payload.get(key) or "").strip()
    if not value:
        errors.append(f"{prefix}.{key} must be a non-empty string")
    return value


def _nonempty_string_list(
    payload: dict[str, Any], key: str, prefix: str, errors: list[str]
) -> None:
    value = payload.get(key)
    if (
        not isinstance(value, list)
        or not value
        or any(not isinstance(item, str) or not item.strip() for item in value)
    ):
        errors.append(f"{prefix}.{key} must be a non-empty string array")


def _has_human_evidence(
    values: object,
    *,
    confirmation_id: str,
    runtime_target_id: str,
    reviewed_snapshot_sha256: str,
) -> bool:
    if not isinstance(values, list):
        return False
    return any(
        isinstance(item, Mapping)
        and item.get("actor") == "human"
        and item.get("source") in HUMAN_EVIDENCE_SOURCES
        and str(item.get("statement") or "").strip()
        and item.get("confirmation_id") == confirmation_id
        and item.get("runtime_target_id") == runtime_target_id
        and item.get("reviewed_snapshot_sha256") == reviewed_snapshot_sha256
        for item in values
    )


def _validation_payload(
    project_root: Path,
    state_path: Path,
    state: dict[str, Any] | None,
    errors: list[str],
    *,
    stale: bool,
    contract_valid: bool = False,
) -> dict[str, Any]:
    overall = (state or {}).get("overall")
    next_command_value = (
        overall.get("next_command") if isinstance(overall, dict) else None
    )
    findings = (state or {}).get("findings")
    finding_routes = (
        [
            {
                "id": str(item.get("id") or ""),
                "status": str(item.get("status") or ""),
                "route": str(item.get("route") or ""),
                "classification": str(item.get("classification") or ""),
            }
            for item in findings
            if isinstance(findings, list) and isinstance(item, dict)
        ]
        if isinstance(findings, list)
        else []
    )
    return {
        "status": str((state or {}).get("status") or "missing"),
        "valid": not errors,
        "contract_valid": contract_valid,
        "accepted": not errors and (state or {}).get("status") == "accepted",
        "stale": stale,
        "finding_routes": finding_routes,
        "state_path": _display_path(state_path, project_root),
        "errors": errors,
        "next_command": str(next_command_value).strip()
        if next_command_value
        else ACCEPTANCE_COMMAND,
    }


def _display_path(path: Path, project_root: Path) -> str:
    try:
        return path.resolve().relative_to(project_root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()
