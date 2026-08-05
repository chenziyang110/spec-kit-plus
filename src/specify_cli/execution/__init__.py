"""Shared execution packet helpers for delegated task routing."""

from .packet_compiler import compile_worker_task_packet
from .packet_renderer import render_packet_summary
from .packet_schema import (
    ContextBundleItem,
    DispatchPolicy,
    ExecutionIntent,
    PacketReference,
    PacketScope,
    ValidationPolicy,
    WorkerTaskPacket,
    worker_task_packet_from_json,
    worker_task_packet_payload,
)
from .packet_validator import PacketValidationError, validate_worker_task_packet
from .result_handoff import (
    FEATURE_LANE_RESULT_DIRECTORIES,
    STAGE_OWNED_RESULT_COMMANDS,
    WORKSPACE_LANE_RESULT_COMMANDS,
    build_result_handoff_path,
    describe_result_handoff_template,
    describe_result_submit_template,
    uses_stage_owned_result_channel,
)
from .result_handoff import write_normalized_result_handoff
from .result_normalizer import normalize_worker_task_result_payload
from .result_schema import (
    RuleAcknowledgement,
    ValidationResult,
    WorkerTaskResult,
    worker_task_result_from_json,
    worker_task_result_payload,
)
from .result_validator import validate_worker_task_result
from specify_cli.verification import (
    run_verification_commands,
    summarize_validation_results,
    verification_passed,
)

__all__ = [
    "DispatchPolicy",
    "ExecutionIntent",
    "FEATURE_LANE_RESULT_DIRECTORIES",
    "ContextBundleItem",
    "PacketReference",
    "PacketScope",
    "PacketValidationError",
    "RuleAcknowledgement",
    "STAGE_OWNED_RESULT_COMMANDS",
    "ValidationResult",
    "ValidationPolicy",
    "WorkerTaskPacket",
    "WorkerTaskResult",
    "WORKSPACE_LANE_RESULT_COMMANDS",
    "build_result_handoff_path",
    "compile_worker_task_packet",
    "describe_result_handoff_template",
    "describe_result_submit_template",
    "render_packet_summary",
    "normalize_worker_task_result_payload",
    "run_verification_commands",
    "summarize_validation_results",
    "validate_worker_task_packet",
    "validate_worker_task_result",
    "uses_stage_owned_result_channel",
    "verification_passed",
    "worker_task_packet_from_json",
    "worker_task_packet_payload",
    "worker_task_result_from_json",
    "worker_task_result_payload",
    "write_normalized_result_handoff",
]
