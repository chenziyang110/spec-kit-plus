"""Validation helpers for subagent execution results."""

from __future__ import annotations

from .evidence import (
    has_any_evidence,
    has_real_entrypoint_consumer_evidence,
    normalize_evidence_label,
)
from .packet_schema import WorkerTaskPacket
from .packet_validator import PacketValidationError
from .result_schema import WorkerTaskResult


_PLACEHOLDER_OUTPUTS = {
    "",
    "NOT RUN",
    "NOT RUN - REPLACE WITH ACTUAL COMMAND OUTPUT AFTER EXECUTION",
}
_MISSING_UI_FIDELITY_STATUSES = {
    "",
    "none",
    "not_applicable",
    "not_run",
    "unavailable",
}
_FAILED_UI_STATUSES = {
    "failed",
    "fail",
    "failure",
}
_PASSING_UI_FIDELITY_STATUSES = {
    "pass",
    "passed",
    "success",
    "approved",
}
_PENDING_HUMAN_REVIEW_STATUSES = {
    "pending_human_review",
}
_PASSING_VISUAL_COMPARISON_STATUSES = {
    "pass",
    "passed",
    "success",
    "approved",
    "match",
    "matched",
    "matches",
}
_UNAVAILABLE_VISUAL_COMPARISON_STATUSES = {
    "unavailable",
    "not_available",
    "not_applicable",
    "not_run",
    "none",
    "",
}
_HUMAN_UI_REVIEWERS = {
    "human",
    "human_review",
    "human_reviewer",
    "manual",
    "manual_review",
    "manual_reviewer",
}
_UI_REVIEW_ARTIFACT_LABELS = {
    "approval_request",
    "human_approval",
    "human_review",
    "manual_approval",
    "manual_review",
    "pending_human_review",
    "pending_review",
    "review_tracking",
}
_UI_EVIDENCE_REQUIRED_FIDELITY_LEVELS = {
    "approximate",
    "high",
}
_EVIDENCE_LABEL_ALIASES = {
    "real_entrypoint_ui_evidence": "real_entrypoint_evidence",
}


def _normalize_command(value: str) -> str:
    return value.strip()


def _validation_output_is_placeholder(output: str) -> bool:
    normalized = output.strip()
    return normalized.upper() in _PLACEHOLDER_OUTPUTS


def _normalize_required_evidence_label(value: str) -> str:
    normalized = normalize_evidence_label(value)
    return _EVIDENCE_LABEL_ALIASES.get(normalized, normalized)


def _requires_ui_evidence(packet: WorkerTaskPacket, required_evidence: set[str]) -> bool:
    fidelity_level = normalize_evidence_label(packet.ui_contract.fidelity_level)
    if fidelity_level in _UI_EVIDENCE_REQUIRED_FIDELITY_LEVELS:
        return True
    return any(
        "screenshot" in item or "capture" in item or item == "ui_evidence"
        for item in required_evidence
    )


def _has_human_ui_approval(result: WorkerTaskResult) -> bool:
    return normalize_evidence_label(result.ui_verification.reviewer) in _HUMAN_UI_REVIEWERS


def _has_ui_review_artifact(result: WorkerTaskResult) -> bool:
    if has_any_evidence(result.manual_evidence):
        return True
    if not isinstance(result.ui_evidence, list):
        return False
    for item in result.ui_evidence:
        if not isinstance(item, dict):
            continue
        labels = (
            normalize_evidence_label(str(item.get("kind", ""))),
            normalize_evidence_label(str(item.get("type", ""))),
        )
        if any(label in _UI_REVIEW_ARTIFACT_LABELS for label in labels):
            return True
    return False


def _has_manual_ui_approval_artifact(result: WorkerTaskResult) -> bool:
    return has_any_evidence(result.manual_evidence)


def validate_worker_task_result(
    result: WorkerTaskResult,
    packet: WorkerTaskPacket,
) -> WorkerTaskResult:
    """Return the result when it satisfies the packet's handoff contract."""

    if result.status == "pending":
        return result

    if packet.dispatch_policy.must_acknowledge_rules:
        if not result.rule_acknowledgement.required_references_read:
            raise PacketValidationError("DP3", "worker did not acknowledge required references")
        if not result.rule_acknowledgement.forbidden_drift_respected:
            raise PacketValidationError("DP3", "worker did not acknowledge forbidden drift")
        required_context_paths = [
            item.path
            for item in packet.context_bundle
            if item.must_read
        ]
        if required_context_paths:
            if not result.rule_acknowledgement.context_bundle_read:
                raise PacketValidationError("DP3", "worker did not acknowledge execution context bundle")
            read_paths = set(result.rule_acknowledgement.paths_read)
            missing_paths = [path for path in required_context_paths if path not in read_paths]
            if missing_paths:
                missing_text = ", ".join(missing_paths)
                raise PacketValidationError(
                    "DP3",
                    f"worker did not acknowledge required context bundle paths: {missing_text}",
                )
    if result.status == "blocked":
        if not result.blockers:
            raise PacketValidationError("DP3", "blocked worker result is missing blocker evidence")
        if not result.failed_assumptions:
            raise PacketValidationError("DP3", "blocked worker result is missing failed assumptions")
        if not result.suggested_recovery_actions:
            raise PacketValidationError("DP3", "blocked worker result is missing recovery guidance")
        return result
    if packet.validation_gates and not result.validation_results:
        raise PacketValidationError("DP3", "worker result is missing validation evidence")
    if result.status == "success":
        results_by_command = {
            _normalize_command(item.command): item
            for item in result.validation_results
            if _normalize_command(item.command)
        }
        expected_commands = [
            _normalize_command(command)
            for command in packet.validation_gates
            if _normalize_command(command)
        ]
        missing_commands = [
            command for command in expected_commands if command not in results_by_command
        ]
        if missing_commands:
            missing_text = ", ".join(missing_commands)
            raise PacketValidationError(
                "DP3",
                f"worker result is missing validation gate coverage for: {missing_text}",
            )

        for command in expected_commands:
            validation = results_by_command[command]
            if validation.status != "passed":
                raise PacketValidationError(
                    "DP3",
                    f"worker result did not pass validation gate: {command}",
                )
            if _validation_output_is_placeholder(validation.output):
                raise PacketValidationError(
                    "DP3",
                    f"worker result is missing validation output for gate: {command}",
                )
        required_evidence = {
            _normalize_required_evidence_label(item)
            for item in [
                *packet.required_evidence,
                *packet.ui_contract.required_evidence,
            ]
            if item.strip()
        }
        if (
            packet.consumer_surfaces
            or "consumer_evidence" in required_evidence
            or "real_entrypoint_evidence" in required_evidence
        ):
            if not result.consumer_evidence:
                raise PacketValidationError("DP3", "worker result is missing consumer evidence")
        if "real_entrypoint_evidence" in required_evidence:
            if not has_real_entrypoint_consumer_evidence(result.consumer_evidence):
                raise PacketValidationError(
                    "DP3",
                    "worker result is missing real-entrypoint consumer evidence",
                )
        if "acceptance_evidence" in required_evidence and not result.acceptance_evidence:
            raise PacketValidationError("DP3", "worker result is missing acceptance evidence")
        if "manual_evidence" in required_evidence and not result.manual_evidence:
            raise PacketValidationError("DP3", "worker result is missing manual evidence")
        requires_ui_evidence = _requires_ui_evidence(packet, required_evidence)
        requires_visual_review = "visual_comparison_or_human_review" in required_evidence
        if requires_visual_review or requires_ui_evidence:
            fidelity_status = normalize_evidence_label(result.ui_verification.fidelity_status)
            visual_comparison = normalize_evidence_label(
                result.ui_verification.visual_comparison
            )
            if fidelity_status in _MISSING_UI_FIDELITY_STATUSES:
                raise PacketValidationError(
                    "DP3",
                    "visual_comparison_or_human_review requires ui_verification fidelity_status",
                )
            if fidelity_status in _FAILED_UI_STATUSES:
                raise PacketValidationError(
                    "DP3",
                    "visual_comparison_or_human_review has failed ui fidelity status",
                )
            if fidelity_status not in (
                _PASSING_UI_FIDELITY_STATUSES | _PENDING_HUMAN_REVIEW_STATUSES
            ):
                raise PacketValidationError(
                    "DP3",
                    "visual_comparison_or_human_review has unknown ui fidelity status",
                )
            if visual_comparison in _FAILED_UI_STATUSES:
                raise PacketValidationError(
                    "DP3",
                    "visual_comparison_or_human_review has failed visual comparison",
                )
            if visual_comparison not in (
                _PASSING_VISUAL_COMPARISON_STATUSES
                | _UNAVAILABLE_VISUAL_COMPARISON_STATUSES
                | _PENDING_HUMAN_REVIEW_STATUSES
            ):
                raise PacketValidationError(
                    "DP3",
                    "visual_comparison_or_human_review has unknown visual comparison status",
                )
            if requires_ui_evidence and not has_any_evidence(result.ui_evidence):
                raise PacketValidationError("DP3", "worker result is missing ui evidence")
            if (
                fidelity_status in _PASSING_UI_FIDELITY_STATUSES
                and visual_comparison in _UNAVAILABLE_VISUAL_COMPARISON_STATUSES
                and not _has_human_ui_approval(result)
            ):
                raise PacketValidationError(
                    "DP3",
                    "visual_comparison_or_human_review cannot claim fidelity pass without visual comparison or human approval",
                )
            if (
                fidelity_status in _PASSING_UI_FIDELITY_STATUSES
                and visual_comparison in _UNAVAILABLE_VISUAL_COMPARISON_STATUSES
                and not _has_manual_ui_approval_artifact(result)
            ):
                raise PacketValidationError(
                    "DP3",
                    "visual_comparison_or_human_review requires manual evidence for human approval",
                )
        if requires_visual_review:
            if (
                fidelity_status in _PENDING_HUMAN_REVIEW_STATUSES
                and not _has_ui_review_artifact(result)
            ):
                raise PacketValidationError(
                    "DP3",
                    "visual_comparison_or_human_review pending human review requires review evidence",
                )
        if packet.must_preserve_obligations or "must_preserve_evidence" in required_evidence:
            if not result.must_preserve_evidence:
                raise PacketValidationError("DP3", "worker result is missing must-preserve evidence")
            evidence_ids = {
                str(item.get("mp_id", "")).strip()
                for item in result.must_preserve_evidence
                if isinstance(item, dict)
            }
            missing_obligations = [
                obligation.id
                for obligation in packet.must_preserve_obligations
                if obligation.id not in evidence_ids
            ]
            if missing_obligations:
                joined = ", ".join(missing_obligations)
                raise PacketValidationError(
                    "DP3",
                    f"worker result is missing must-preserve evidence for: {joined}",
                )
        if packet.consequence_obligations:
            evidence_ids = {
                str(item.get("obligation_id") or "").strip()
                for item in result.consequence_evidence
                if isinstance(item, dict)
            }
            required_ids = {
                obligation.obligation_id
                for obligation in packet.consequence_obligations
                if obligation.obligation_id.strip()
            }
            missing_ids = sorted(required_ids - evidence_ids)
            if missing_ids:
                raise PacketValidationError(
                    "DP3",
                    "worker result is missing consequence evidence for: "
                    + ", ".join(missing_ids),
                )
    return result
