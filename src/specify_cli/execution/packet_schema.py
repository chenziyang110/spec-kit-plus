"""Typed execution packet contract for subagent work."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field, fields
from typing import Literal


PacketMode = Literal["hard_fail"]
ValidationMode = Literal["task", "feature_epochs"]
HeavyGateOwner = Literal["worker", "leader"]
ContextKind = Literal[
    "coverage_baseline",
    "handbook",
    "project_cognition",
    "testing_contract",
    "testing_playbook",
    "task_reference",
]

LEGACY_CONTEXT_KIND_ALIASES: dict[str, ContextKind] = {
    "project_map": "project_cognition",
}


@dataclass(slots=True)
class PacketReference:
    path: str
    reason: str


@dataclass(slots=True)
class MustPreserveObligation:
    id: str
    type: str
    claim: str
    source: str
    downstream_requirement: str
    mapped_to: list[str] = field(default_factory=list)
    stop_and_reopen_condition: str = ""


@dataclass(slots=True)
class PacketScope:
    write_scope: list[str] = field(default_factory=list)
    read_scope: list[str] = field(default_factory=list)


@dataclass(slots=True)
class PacketInterfaces:
    consumes: list[str] = field(default_factory=list)
    produces: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ContextBundleItem:
    path: str
    kind: ContextKind = "task_reference"
    purpose: str = ""
    required_for: list[str] = field(default_factory=list)
    read_order: int = 0
    must_read: bool = True
    selection_reason: str = ""

    def __post_init__(self) -> None:
        if isinstance(self.kind, str):
            self.kind = LEGACY_CONTEXT_KIND_ALIASES.get(self.kind, self.kind)


@dataclass(slots=True)
class DispatchPolicy:
    mode: PacketMode = "hard_fail"
    must_acknowledge_rules: bool = True


@dataclass(slots=True)
class ValidationPolicy:
    """Describe where validation runs and which shared budget owns it."""

    mode: ValidationMode = "task"
    max_epochs: int = 0
    budget_scope: str = "task"
    budget_ref: str = ""
    heavy_gate_owner: HeavyGateOwner = "worker"


@dataclass(slots=True)
class ExecutionIntent:
    outcome: str = ""
    constraints: list[str] = field(default_factory=list)
    success_signals: list[str] = field(default_factory=list)


UIFidelityLevel = Literal["none", "approximate", "high", "inspiration"]


@dataclass(slots=True)
class UIContract:
    ui_work_type: str = ""
    surface_type: str = ""
    platforms: list[str] = field(default_factory=list)
    subject: str = ""
    audience: str = ""
    single_job: str = ""
    visual_thesis: str = ""
    content_thesis: str = ""
    interaction_thesis: str = ""
    signature_element: str = ""
    approved_visual_ref: str = ""
    approved_preview_sha256: str = ""
    approved_manifest_sha256: str = ""
    design_decision_ids: list[str] = field(default_factory=list)
    design_sources: list[str] = field(default_factory=list)
    reference_notes: str = ""
    visual_target: str = ""
    reference_intents: list[dict[str, str]] = field(default_factory=list)
    real_content_plan: list[dict[str, object]] = field(default_factory=list)
    image_plan: list[dict[str, str]] = field(default_factory=list)
    color_modes: list[str] = field(default_factory=list)
    component_contracts: list[dict[str, object]] = field(default_factory=list)
    responsive_matrix: list[dict[str, object]] = field(default_factory=list)
    motion_contract: dict[str, object] = field(default_factory=dict)
    visual_acceptance_matrix: list[dict[str, object]] = field(default_factory=list)
    comparison_tolerance: str = ""
    accepted_deviations: list[dict[str, object]] = field(default_factory=list)
    fidelity_level: UIFidelityLevel = "none"
    must_preserve: list[str] = field(default_factory=list)
    may_adapt: list[str] = field(default_factory=list)
    must_not: list[str] = field(default_factory=list)
    required_states: list[str] = field(default_factory=list)
    required_evidence: list[str] = field(default_factory=list)


UI_CONTRACT_FIELDS = frozenset(item.name for item in fields(UIContract))


@dataclass(slots=True)
class ConsequenceObligation:
    obligation_id: str
    claim: str = ""
    affected_objects: list[str] = field(default_factory=list)
    state_behavior_refs: list[str] = field(default_factory=list)
    dependency_refs: list[str] = field(default_factory=list)
    recovery_validation_refs: list[str] = field(default_factory=list)
    owner: str = ""
    latest_resolve_phase: str = ""
    status: str = "open"
    stop_and_reopen_condition: str = ""


@dataclass(slots=True)
class WorkerTaskPacket:
    feature_id: str
    task_id: str
    story_id: str
    objective: str
    scope: PacketScope
    context_bundle: list[ContextBundleItem]
    required_references: list[PacketReference]
    hard_rules: list[str]
    forbidden_drift: list[str]
    validation_gates: list[str]
    done_criteria: list[str]
    handoff_requirements: list[str]
    platform_guardrails: list[str] = field(default_factory=list)
    user_confirmed_deferral_refs: list[str] = field(default_factory=list)
    intent: ExecutionIntent = field(default_factory=ExecutionIntent)
    dispatch_policy: DispatchPolicy = field(default_factory=DispatchPolicy)
    validation_policy: ValidationPolicy = field(default_factory=ValidationPolicy)
    # Subagent-ready task contract fields (optional — populated when tasks.md is enriched)
    agent_role: str = ""
    context_nav: list[dict[str, str]] = field(default_factory=list)
    anti_goals: list[str] = field(default_factory=list)
    does_not_remove: list[str] = field(default_factory=list)
    capability_operations: list[str] = field(default_factory=list)
    task_checks: list[str] = field(default_factory=list)
    verify_commands: list[str] = field(default_factory=list)
    acceptance_criteria: list[str] = field(default_factory=list)
    consumer_surfaces: list[str] = field(default_factory=list)
    required_evidence: list[str] = field(default_factory=list)
    global_constraints: list[str] = field(default_factory=list)
    interfaces: PacketInterfaces = field(default_factory=PacketInterfaces)
    review_inputs: list[str] = field(default_factory=list)
    review_risks: list[str] = field(default_factory=list)
    controller_checks_required: list[str] = field(default_factory=list)
    ui_contract: UIContract = field(default_factory=UIContract)
    must_preserve_obligations: list[MustPreserveObligation] = field(
        default_factory=list
    )
    consequence_obligations: list[ConsequenceObligation] = field(default_factory=list)
    escalation_role: str = "debugger"
    retry_max: int = 2
    packet_version: int = 2


def _filter_dataclass_payload(
    cls: type, payload: dict[str, object]
) -> dict[str, object]:
    allowed = {item.name for item in fields(cls)}
    return {key: value for key, value in payload.items() if key in allowed}


def _normalize_context_bundle_item_payload(
    payload: dict[str, object],
) -> dict[str, object]:
    item_payload = _filter_dataclass_payload(ContextBundleItem, payload)
    kind = item_payload.get("kind")
    if isinstance(kind, str):
        item_payload["kind"] = LEGACY_CONTEXT_KIND_ALIASES.get(kind, kind)
    return item_payload


def worker_task_packet_payload(packet: WorkerTaskPacket) -> dict[str, object]:
    """Return a JSON-serializable payload for a worker packet."""

    return asdict(packet)


def worker_task_packet_from_json(text: str) -> WorkerTaskPacket:
    """Parse a worker packet from JSON text."""

    payload = json.loads(text)
    if "ui_fidelity_requirements" in payload:
        raise ValueError(
            "ui_fidelity_requirements is not part of the current UI contract"
        )
    raw_ui_contract = payload.get("ui_contract", {})
    if not isinstance(raw_ui_contract, dict):
        raise ValueError("ui_contract must be an object")
    unknown_ui_fields = set(raw_ui_contract) - UI_CONTRACT_FIELDS
    if unknown_ui_fields:
        raise ValueError(
            "ui_contract contains unsupported fields: "
            + ", ".join(sorted(unknown_ui_fields))
        )
    missing_ui_fields = UI_CONTRACT_FIELDS - set(raw_ui_contract)
    if raw_ui_contract and missing_ui_fields:
        raise ValueError(
            "ui_contract is missing current fields: "
            + ", ".join(sorted(missing_ui_fields))
        )
    scope = PacketScope(
        **_filter_dataclass_payload(PacketScope, payload.get("scope", {}))
    )
    required_references = [
        PacketReference(**_filter_dataclass_payload(PacketReference, item))
        for item in payload.get("required_references", [])
        if isinstance(item, dict)
    ]
    must_preserve_obligations = [
        MustPreserveObligation(
            **_filter_dataclass_payload(MustPreserveObligation, item)
        )
        for item in payload.get("must_preserve_obligations", [])
        if isinstance(item, dict)
    ]
    context_bundle = [
        ContextBundleItem(**_normalize_context_bundle_item_payload(item))
        for item in payload.get("context_bundle", [])
        if isinstance(item, dict)
    ]
    consequence_obligations = [
        ConsequenceObligation(**_filter_dataclass_payload(ConsequenceObligation, item))
        for item in payload.get("consequence_obligations", [])
        if isinstance(item, dict)
    ]
    intent = ExecutionIntent(
        **_filter_dataclass_payload(ExecutionIntent, payload.get("intent", {}))
    )
    interfaces = PacketInterfaces(
        **_filter_dataclass_payload(PacketInterfaces, payload.get("interfaces", {}))
    )
    dispatch_policy = DispatchPolicy(
        **_filter_dataclass_payload(DispatchPolicy, payload.get("dispatch_policy", {}))
    )
    raw_validation_policy = payload.get("validation_policy", {})
    if not isinstance(raw_validation_policy, dict):
        raise ValueError("validation_policy must be an object")
    validation_policy = ValidationPolicy(
        **_filter_dataclass_payload(ValidationPolicy, raw_validation_policy)
    )
    ui_contract = UIContract(**_filter_dataclass_payload(UIContract, raw_ui_contract))
    packet_payload = _filter_dataclass_payload(WorkerTaskPacket, payload)
    packet_payload["intent"] = intent
    packet_payload["interfaces"] = interfaces
    packet_payload["scope"] = scope
    packet_payload["context_bundle"] = context_bundle
    packet_payload["required_references"] = required_references
    packet_payload["must_preserve_obligations"] = must_preserve_obligations
    packet_payload["consequence_obligations"] = consequence_obligations
    packet_payload["dispatch_policy"] = dispatch_policy
    packet_payload["validation_policy"] = validation_policy
    packet_payload["ui_contract"] = ui_contract
    return WorkerTaskPacket(**packet_payload)
