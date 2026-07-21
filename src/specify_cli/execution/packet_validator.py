"""Validation helpers for worker task packets."""

from __future__ import annotations

import re
from dataclasses import dataclass

from .packet_schema import UI_CONTRACT_FIELDS, UIContract, WorkerTaskPacket


MP_ID_RE = re.compile(r"^MP-\d{3}$")
UI_WORK_TYPES = {"existing-pattern", "feature-extension", "reference-implementation"}
UI_SURFACE_TYPES = {
    "landing",
    "product-workspace",
    "hybrid",
    "existing-pattern-maintenance",
}
UI_PLATFORMS = {"web", "mobile", "desktop", "tui", "cli"}
UI_REFERENCE_INTENTS = {
    "exact",
    "preserve-structure",
    "inspiration",
    "extract-tokens",
    "do-not-copy",
}
UI_REQUIRED_EVIDENCE = {
    "structure_snapshot",
    "visual_capture",
    "runtime_diagnostics",
    "visual_comparison_or_human_review",
}
OBSOLETE_UI_EVIDENCE_LABELS = {
    "real_entrypoint_ui_evidence",
    "reference_source_evidence",
    "ui_fidelity_criteria",
    "deviation_log",
    "visual_comparison_evidence",
}
SURFACE_LIMIT_ANTI_GOAL_RE = re.compile(
    r"\b(do not|don't|must not)\b.*\b(add|introduce|modify|change|expand)\b.*\b(public\s+)?(command|commands|api|apis|route|routes|surface|surfaces|lifecycle)\b",
    re.IGNORECASE,
)


@dataclass(slots=True)
class PacketValidationError(ValueError):
    code: str
    message: str

    def __post_init__(self) -> None:
        ValueError.__init__(self, self.message)


def _has_blank_entry(values: list[str]) -> bool:
    return any(not item.strip() for item in values)


def _ui_contract_applies(packet: WorkerTaskPacket) -> bool:
    contract = packet.ui_contract
    return any(
        getattr(contract, field_name)
        for field_name in UI_CONTRACT_FIELDS
        if field_name != "fidelity_level"
    ) or contract.fidelity_level != "none"


def validate_ui_contract(contract: UIContract) -> None:
    """Validate the one current UI contract shape and values."""
    if contract.fidelity_level not in {"approximate", "high", "inspiration"}:
        raise PacketValidationError(
            "DP1",
            "active UI contract fidelity_level must be approximate, high, or inspiration",
        )
    if contract.ui_work_type not in UI_WORK_TYPES:
        raise PacketValidationError(
            "DP1", "UI contract requires a valid ui_work_type"
        )
    if contract.surface_type not in UI_SURFACE_TYPES:
        raise PacketValidationError(
            "DP1", "UI contract requires a valid surface_type"
        )
    if not contract.platforms or any(
        item not in UI_PLATFORMS for item in contract.platforms
    ):
        raise PacketValidationError(
            "DP1", "UI contract requires supported platforms"
        )
    for field_name in (
        "subject",
        "audience",
        "single_job",
        "visual_thesis",
        "content_thesis",
        "interaction_thesis",
        "signature_element",
        "approved_visual_ref",
    ):
        if not str(getattr(contract, field_name)).strip():
            raise PacketValidationError(
                "DP1", f"UI contract requires nonblank {field_name}"
            )
    if not contract.design_sources or _has_blank_entry(contract.design_sources):
        raise PacketValidationError("DP1", "UI contract requires design_sources")
    if not contract.required_states or _has_blank_entry(contract.required_states):
        raise PacketValidationError("DP1", "UI contract requires required_states")
    if not contract.real_content_plan:
        raise PacketValidationError(
            "DP1", "UI contract requires a real_content_plan"
        )
    for item in contract.real_content_plan:
        if not isinstance(item, dict) or not str(item.get("source_ref") or "").strip():
            raise PacketValidationError(
                "DP1", "UI contract real_content_plan entries require source_ref"
            )
    for item in contract.reference_intents:
        if (
            not isinstance(item, dict)
            or not str(item.get("ref") or "").strip()
            or str(item.get("intent") or "").strip() not in UI_REFERENCE_INTENTS
        ):
            raise PacketValidationError(
                "DP1",
                "UI contract reference_intents entries require ref and valid intent",
            )
    for item in contract.image_plan:
        if (
            not isinstance(item, dict)
            or not str(item.get("ref") or "").strip()
            or not str(item.get("role") or "").strip()
        ):
            raise PacketValidationError(
                "DP1", "UI contract image_plan entries require ref and role"
            )
    evidence = {item.strip() for item in contract.required_evidence}
    if evidence != UI_REQUIRED_EVIDENCE:
        raise PacketValidationError(
            "DP1",
            "UI contract required_evidence must be exactly: "
            + ", ".join(sorted(UI_REQUIRED_EVIDENCE)),
        )


def validate_ui_context_nav(context_nav: list[dict[str, str]]) -> None:
    """Validate packet-only compact navigation derived for UI execution."""

    context_kinds = {
        str(item.get("kind") or "").strip()
        for item in context_nav
        if isinstance(item, dict)
    }
    missing_context = {"ui_entrypoint", "design_source"} - context_kinds
    if missing_context:
        raise PacketValidationError(
            "DP2",
            "UI contract is missing compact context_nav kinds: "
            + ", ".join(sorted(missing_context)),
        )


def validate_worker_task_packet(packet: WorkerTaskPacket) -> WorkerTaskPacket:
    """Return the packet when its hard-fail execution contract is complete."""

    if (
        not packet.intent.outcome
        or not packet.intent.constraints
        or not packet.intent.success_signals
    ):
        raise PacketValidationError(
            "DP1", "execution intent contract must be present in the packet"
        )
    if not packet.scope.write_scope:
        raise PacketValidationError(
            "DP1", "write_scope is required for delegated execution"
        )
    if not packet.context_bundle:
        raise PacketValidationError(
            "DP2", "context_bundle must be compiled into the packet"
        )
    if not packet.required_references:
        raise PacketValidationError(
            "DP2", "required_references must be compiled into the packet"
        )
    if not packet.hard_rules:
        raise PacketValidationError("DP1", "hard_rules must be present in the packet")
    policy = packet.validation_policy
    if policy.mode not in {"task", "feature_epochs"}:
        raise PacketValidationError("DP1", "validation_policy mode is invalid")
    if policy.mode == "feature_epochs":
        if (
            isinstance(policy.max_epochs, bool)
            or not isinstance(policy.max_epochs, int)
            or not 1 <= policy.max_epochs <= 3
        ):
            raise PacketValidationError(
                "DP1", "feature_epochs validation_policy max_epochs must be 1..3"
            )
        if policy.budget_scope != "implement-review":
            raise PacketValidationError(
                "DP1",
                "feature_epochs validation_policy budget_scope must be implement-review",
            )
        if not policy.budget_ref.strip():
            raise PacketValidationError(
                "DP1", "feature_epochs validation_policy requires budget_ref"
            )
        if policy.heavy_gate_owner != "leader":
            raise PacketValidationError(
                "DP1",
                "feature_epochs validation_policy heavy_gate_owner must be leader",
            )
    elif not packet.validation_gates:
        raise PacketValidationError(
            "DP1", "validation_gates must be present in the packet"
        )
    if not packet.done_criteria:
        raise PacketValidationError(
            "DP1", "done_criteria must be present in the packet"
        )
    if not packet.handoff_requirements:
        raise PacketValidationError(
            "DP1", "handoff_requirements must be present in the packet"
        )
    if not packet.platform_guardrails:
        raise PacketValidationError(
            "DP2", "platform_guardrails must be compiled into the packet"
        )
    if any(SURFACE_LIMIT_ANTI_GOAL_RE.search(goal) for goal in packet.anti_goals):
        if not packet.does_not_remove:
            raise PacketValidationError(
                "DP1",
                "surface-limiting anti-goals require a does-not-remove guard",
            )
    obsolete_evidence = sorted(
        {
            item.strip().lower().replace("-", "_").replace(" ", "_")
            for item in packet.required_evidence
        }
        & OBSOLETE_UI_EVIDENCE_LABELS
    )
    if obsolete_evidence:
        raise PacketValidationError(
            "DP1",
            "worker packet contains obsolete UI evidence labels: "
            + ", ".join(obsolete_evidence),
        )
    if packet.ui_contract.fidelity_level not in {
        "none",
        "approximate",
        "high",
        "inspiration",
    }:
        raise PacketValidationError(
            "DP1",
            "UI contract fidelity_level must be none, approximate, high, or inspiration",
        )
    if _ui_contract_applies(packet):
        validate_ui_contract(packet.ui_contract)
        validate_ui_context_nav(packet.context_nav)
    if _has_blank_entry(packet.controller_checks_required):
        raise PacketValidationError(
            "DP1", "controller checks required cannot contain blank entries"
        )
    for obligation in packet.must_preserve_obligations:
        if not MP_ID_RE.match(obligation.id):
            raise PacketValidationError(
                "DP1", "must-preserve obligation id must use MP-### format"
            )
        if (
            not obligation.type
            or not obligation.claim
            or not obligation.source
            or not obligation.downstream_requirement
        ):
            raise PacketValidationError(
                "DP1", "must-preserve obligation is missing required fields"
            )
    for obligation in packet.consequence_obligations:
        if not obligation.obligation_id.strip():
            raise PacketValidationError(
                "DP2", "consequence obligation is missing obligation_id"
            )
        if not obligation.claim.strip():
            raise PacketValidationError(
                "DP2",
                f"consequence obligation {obligation.obligation_id} is missing claim",
            )
        if not obligation.affected_objects:
            raise PacketValidationError(
                "DP2",
                f"consequence obligation {obligation.obligation_id} is missing affected_objects",
            )
        if not obligation.stop_and_reopen_condition.strip():
            raise PacketValidationError(
                "DP2",
                f"consequence obligation {obligation.obligation_id} is missing stop_and_reopen_condition",
            )
    return packet
