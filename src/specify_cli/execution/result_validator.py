"""Validation helpers for subagent execution results."""

from __future__ import annotations

from .packet_schema import WorkerTaskPacket
from .packet_validator import PacketValidationError
from .result_schema import WorkerTaskResult


_PLACEHOLDER_OUTPUTS = {
    "",
    "NOT RUN",
    "NOT RUN - REPLACE WITH ACTUAL COMMAND OUTPUT AFTER EXECUTION",
}


def _normalize_command(value: str) -> str:
    return value.strip()


def _validation_output_is_placeholder(output: str) -> bool:
    normalized = output.strip()
    return normalized.upper() in _PLACEHOLDER_OUTPUTS


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
    return result
