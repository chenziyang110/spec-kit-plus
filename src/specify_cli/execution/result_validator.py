"""Validation helpers for subagent execution results."""

from __future__ import annotations

from .evidence import has_real_entrypoint_consumer_evidence, normalize_evidence_label
from .packet_schema import WorkerTaskPacket
from .packet_validator import PacketValidationError
from .result_schema import WorkerTaskResult


_PLACEHOLDER_OUTPUTS = {
    "",
    "NOT RUN",
    "NOT RUN - REPLACE WITH ACTUAL COMMAND OUTPUT AFTER EXECUTION",
}
_UI_FIDELITY_PAYLOAD_FIELDS = {
    "artifact",
    "screenshot",
    "diff",
    "comparison",
    "evidence",
    "path",
    "url",
}
_UI_FIDELITY_PLACEHOLDER_VALUES = {
    "",
    "todo",
    "tbd",
    "n_a",
    "none",
    "not_run",
}


def _normalize_command(value: str) -> str:
    return value.strip()


def _validation_output_is_placeholder(output: str) -> bool:
    normalized = output.strip()
    return normalized.upper() in _PLACEHOLDER_OUTPUTS


def _has_meaningful_ui_fidelity_payload(item: dict[str, str]) -> bool:
    for field in _UI_FIDELITY_PAYLOAD_FIELDS:
        value = str(item.get(field, "")).strip()
        if value and normalize_evidence_label(value) not in _UI_FIDELITY_PLACEHOLDER_VALUES:
            return True
    return False


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
            normalize_evidence_label(item)
            for item in packet.required_evidence
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
        if packet.ui_fidelity_requirements.applicable:
            if not result.ui_fidelity_evidence:
                raise PacketValidationError("DP3", "worker result is missing ui fidelity evidence")
            ui_required_evidence = {
                normalize_evidence_label(item)
                for item in packet.ui_fidelity_requirements.required_evidence
                if item.strip()
            }
            if "visual_comparison_evidence" in ui_required_evidence:
                has_visual_comparison = any(
                    normalize_evidence_label(str(item.get("kind", ""))) == "visual_comparison"
                    and _has_meaningful_ui_fidelity_payload(item)
                    for item in result.ui_fidelity_evidence
                    if isinstance(item, dict)
                )
                if not has_visual_comparison:
                    raise PacketValidationError(
                        "DP3",
                        "worker result is missing visual comparison ui fidelity evidence",
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
