"""Typed schema objects for the project cognition runtime."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class EvidenceRecord:
    evidence_id: str
    source_kind: str
    source_path: str
    commit_sha: str = ""
    commit_range: str = ""
    span: str = ""
    extractor: str = ""
    captured_at: str = ""
    content_hash: str = ""
    project_internal: bool = True


@dataclass(slots=True)
class ObservationRecord:
    observation_id: str
    observation_type: str
    summary: str
    backing_evidence_ids: list[str] = field(default_factory=list)
    attributes: dict[str, object] = field(default_factory=dict)


@dataclass(slots=True)
class GraphNode:
    node_id: str
    node_type: str
    title: str
    backing_evidence_ids: list[str] = field(default_factory=list)
    attributes: dict[str, object] = field(default_factory=dict)


@dataclass(slots=True)
class GraphEdge:
    edge_id: str
    edge_type: str
    source_node_id: str
    target_node_id: str
    backing_evidence_ids: list[str] = field(default_factory=list)
    attributes: dict[str, object] = field(default_factory=dict)


@dataclass(slots=True)
class ClaimRecord:
    claim_id: str
    subject_ref: str
    predicate: str
    object_value: str = ""
    object_ref: str = ""
    truth_layer: str = "inferred_synthesis"
    confidence: str = "weak"
    backing_evidence_ids: list[str] = field(default_factory=list)
    falsification_reads: list[str] = field(default_factory=list)
    last_validated_at: str = ""


@dataclass(slots=True)
class ConflictRecord:
    conflict_id: str
    subject_ref: str
    competing_claim_ids: list[str] = field(default_factory=list)
    conflict_type: str = ""
    impact_scope: str = ""
    agent_behavior_rule: str = ""
    resolution_status: str = "open"


@dataclass(slots=True)
class UpdateEventRecord:
    update_id: str
    kind: str
    trigger: str
    changed_paths: list[str] = field(default_factory=list)
    affected_nodes: list[str] = field(default_factory=list)
    affected_claims: list[str] = field(default_factory=list)
    created_conflicts: list[str] = field(default_factory=list)
    invalidated_claims: list[str] = field(default_factory=list)
    rebuild_scope: str = ""
    completed_at: str = ""


@dataclass(slots=True)
class SliceRecord:
    slice_id: str
    slice_type: str
    relevant_nodes: list[str] = field(default_factory=list)
    relevant_edges: list[str] = field(default_factory=list)
    key_claims: list[str] = field(default_factory=list)
    active_conflicts: list[str] = field(default_factory=list)
    confidence_summary: dict[str, int] = field(default_factory=dict)
    must_verify_live: list[str] = field(default_factory=list)
    minimal_read_set: list[str] = field(default_factory=list)
