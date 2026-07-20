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
    "product-defect",
    "requirement-gap",
    "environment-or-access",
    "unable-to-verify",
}
FINDING_ROUTES = {
    "sp-review",
    "sp-implement",
    "sp-debug",
    "sp-clarify",
    "sp-specify",
    "spx-review",
    "spx-implement",
    "spx-debug",
    "spx-clarify",
    "spx-specify",
    "human-action",
}
ACCEPTANCE_REPAIR_TARGETS = {
    "sp-review": "review",
    "sp-implement": "implement",
    "sp-debug": "implement",
    "sp-clarify": "specify",
    "sp-specify": "specify",
    "spx-review": "review",
    "spx-implement": "implement",
    "spx-debug": "implement",
    "spx-clarify": "specify",
    "spx-specify": "specify",
}
ACCEPTANCE_REPAIR_OWNERS = {
    "sp-review": "sp-review",
    "sp-implement": "sp-implement",
    "sp-debug": "sp-implement",
    "sp-clarify": "sp-specify",
    "sp-specify": "sp-specify",
    "spx-review": "spx-review",
    "spx-implement": "spx-implement",
    "spx-debug": "spx-implement",
    "spx-clarify": "spx-specify",
    "spx-specify": "spx-specify",
}


def new_human_acceptance_state() -> dict[str, Any]:
    """Return the stable empty state copied by implement closeout."""

    return {
        "version": 1,
        "schema_ref": ACCEPTANCE_SCHEMA_REF,
        "status": "draft",
        "source": {
            "implementation_summary": IMPLEMENTATION_SUMMARY_FILENAME,
            "implementation_summary_sha256": "",
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
        "scenarios": [],
        "cursor": {"scenario_id": None, "step_id": None},
        "findings": [],
        "overall": {
            "verdict": "pending",
            "summary": "",
            "next_command": ACCEPTANCE_COMMAND,
        },
    }


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
    if not re.fullmatch(r"[0-9a-f]{64}", expected_sha256) or actual_sha256 != expected_sha256:
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
        journal = json.loads(
            read_local_state_text(journal_path, root=feature_dir)
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise _acceptance_repair_recovery_error(
            root=root,
            feature_dir=feature_dir,
            reason="Acceptance repair journal is unreadable.",
            evidence=[f"read failure: {type(exc).__name__}: {exc}"],
            route="sp-implement",
            finding_id="unknown",
            expected_revision=0,
        ) from exc
    if not isinstance(journal, dict):
        raise _acceptance_repair_recovery_error(
            root=root,
            feature_dir=feature_dir,
            reason="Acceptance repair journal is not a JSON object.",
            evidence=["journal shape: non-object"],
            route="sp-implement",
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
            route=route or "sp-implement",
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
        for scenario in state.get("scenarios", []):
            if not isinstance(scenario, dict):
                continue
            scenario["verdict"] = "pending"
            for step in scenario.get("steps", []):
                if not isinstance(step, dict):
                    continue
                step["result"] = "pending"
                step["observed_result"] = None
                step["evidence"] = []
        state["status"] = "draft"
        source = state.get("source")
        if isinstance(source, dict):
            source["prepared_from_sha256"] = ""
        state["cursor"] = {
            "scenario_id": finding.get("scenario_id"),
            "step_id": finding.get("step_id"),
        }
        state["overall"] = {
            "verdict": "pending",
            "summary": (
                f"Acceptance finding {normalized_finding} is being repaired through "
                f"{normalized_route}; the prior verdict is no longer valid."
            ),
            "next_command": normalized_route,
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
                (json.dumps(state, ensure_ascii=False, indent=2) + "\n").encode(
                    "utf-8"
                )
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

    summary_digest = _sha256(summary_path)
    current_digest = _implementation_snapshot_sha256(
        root, resolved_feature_dir, summary_digest
    )
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
        prepared_digest = str(source.get("prepared_from_sha256") or "")
        source["implementation_summary_sha256"] = summary_digest
        source["current_sha256"] = current_digest
        if prepared_digest and prepared_digest != current_digest:
            state["status"] = "stale"
            overall = state.get("overall")
            if isinstance(overall, dict):
                overall["verdict"] = "pending"
                overall["summary"] = (
                    "Implementation evidence changed after this acceptance guide was prepared. "
                    "Rebuild the guide before continuing."
                )
                overall["next_command"] = ACCEPTANCE_COMMAND
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
            "next_command": ACCEPTANCE_COMMAND,
        }

    state = deepcopy(new_human_acceptance_state())
    state["source"]["implementation_summary_sha256"] = summary_digest
    state["source"]["prepared_from_sha256"] = current_digest
    state["source"]["current_sha256"] = current_digest
    _write_state(state_path, state)
    return {
        "status": "draft",
        "state_path": _display_path(state_path, root),
        "prepared_from_sha256": current_digest,
        "current_sha256": current_digest,
        "next_command": ACCEPTANCE_COMMAND,
    }


def validate_human_acceptance(
    project_root: Path,
    feature_dir: Path,
    *,
    require_accepted: bool = False,
) -> dict[str, Any]:
    """Validate acceptance shape, freshness, progress, and final verdict rules."""

    root = project_root.resolve()
    resolved_feature_dir = _resolve_feature_dir(root, feature_dir)
    state_path = resolved_feature_dir / ACCEPTANCE_FILENAME
    summary_path = resolved_feature_dir / IMPLEMENTATION_SUMMARY_FILENAME
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
    if state.get("version") != 1:
        errors.append("version must equal 1")
    if state.get("schema_ref") != ACCEPTANCE_SCHEMA_REF:
        errors.append(f"schema_ref must equal {ACCEPTANCE_SCHEMA_REF}")
    if status not in ACCEPTANCE_STATUSES:
        errors.append(f"unsupported acceptance status: {status or 'missing'}")

    source = _object(state, "source", errors)
    if source.get("implementation_summary") != IMPLEMENTATION_SUMMARY_FILENAME:
        errors.append(
            f"source.implementation_summary must equal {IMPLEMENTATION_SUMMARY_FILENAME}"
        )
    recorded_summary_digest = _required_string(
        source, "implementation_summary_sha256", "source", errors
    )
    prepared_digest = _required_string(source, "prepared_from_sha256", "source", errors)
    recorded_current = _required_string(source, "current_sha256", "source", errors)
    actual_summary_digest = _sha256(summary_path) if summary_path.is_file() else ""
    if not actual_summary_digest:
        errors.append(f"missing {IMPLEMENTATION_SUMMARY_FILENAME}")
    elif recorded_summary_digest != actual_summary_digest:
        errors.append(
            "source.implementation_summary_sha256 does not match the current implementation summary"
        )
    actual_digest = (
        _implementation_snapshot_sha256(
            root, resolved_feature_dir, actual_summary_digest
        )
        if actual_summary_digest
        else ""
    )
    stale = bool(actual_digest and prepared_digest and prepared_digest != actual_digest)
    if actual_digest and recorded_current != actual_digest:
        errors.append(
            "source.current_sha256 does not match the current implementation evidence snapshot"
        )
    if stale and status != "stale":
        errors.append(
            "implementation summary changed; status must be stale until the guide is rebuilt"
        )
    if status == "stale" and not stale:
        errors.append(
            "status is stale but the prepared and current implementation summary digests match"
        )

    orientation = _object(state, "orientation", errors)
    scenarios = state.get("scenarios")
    if not isinstance(scenarios, list):
        errors.append("scenarios must be an array")
        scenarios = []
    findings = state.get("findings")
    if not isinstance(findings, list):
        errors.append("findings must be an array")
        findings = []
    cursor = _object(state, "cursor", errors)
    overall = _object(state, "overall", errors)
    overall_verdict = str(overall.get("verdict") or "")
    if overall_verdict not in OVERALL_VERDICTS:
        errors.append("overall.verdict must be pending, pass, fail, or blocked")

    if status not in {"draft", "stale"}:
        for key in ("outcome", "why_it_matters", "start_here"):
            _required_string(orientation, key, "orientation", errors)
        _nonempty_string_list(
            orientation, "user_visible_changes", "orientation", errors
        )
        if not scenarios:
            errors.append(
                "at least one acceptance scenario is required outside draft/stale state"
            )

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
        for key in ("title", "user_value", "start_state"):
            _required_string(raw_scenario, key, prefix, errors)
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
            for key in ("action", "expected_result", "if_failed", "response_prompt"):
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
        if verdict == "pass" and any(
            result != "pass" for result in scenario_step_results
        ):
            errors.append(f"{prefix}.verdict=pass requires every step to pass")

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
        if raw_finding.get("classification") not in FINDING_CLASSIFICATIONS:
            errors.append(f"{prefix}.classification is invalid")
        if raw_finding.get("route") not in FINDING_ROUTES:
            errors.append(f"{prefix}.route is invalid")
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

    if status in {"draft", "ready", "in_progress"} and overall_verdict != "pending":
        errors.append(f"{status} status requires overall.verdict=pending")

    if status == "accepted":
        if not required_verdicts or any(
            verdict != "pass" for verdict in required_verdicts
        ):
            errors.append("accepted status requires every required scenario to pass")
        if overall_verdict != "pass":
            errors.append("accepted status requires overall.verdict=pass")
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
        str(item).strip()
        for item in (context.get("errors") or [])
        if str(item).strip()
    ]
    runtime_error = context.get("runtime_error")
    if (
        context.get("error_code") == "workflow-runtime-validation-blocked"
        and isinstance(runtime_error, Mapping)
    ):
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
                unblock_criteria="human-acceptance.json is fresh, schema-valid, and records status=accepted with every required scenario passing.",
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
                    "action": "Accept only when every required scenario passes; otherwise reject or block and confirm the routed findings.",
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
                "Every required scenario and step passed",
                "The overall verdict is pass and status is accepted",
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
    finding_routes = [
        {
            "id": str(item.get("id") or ""),
            "status": str(item.get("status") or ""),
            "route": str(item.get("route") or ""),
            "classification": str(item.get("classification") or ""),
        }
        for item in findings
        if isinstance(findings, list) and isinstance(item, dict)
    ] if isinstance(findings, list) else []
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
