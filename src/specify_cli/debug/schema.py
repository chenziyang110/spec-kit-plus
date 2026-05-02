from datetime import datetime
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field, model_validator, ConfigDict
from specify_cli.verification import ValidationStatus

class DebugStatus(str, Enum):
    GATHERING = "gathering"
    INVESTIGATING = "investigating"
    FIXING = "fixing"
    VERIFYING = "verifying"
    AWAITING_HUMAN = "awaiting_human_verify"
    RESOLVED = "resolved"


class CandidateDisposition(str, Enum):
    CONFIRMED = "confirmed"
    RULED_OUT = "ruled_out"
    STILL_OPEN_BUT_DEPRIORITIZED = "still_open_but_deprioritized"


class HumanVerificationOutcome(str, Enum):
    PENDING = "pending"
    PASSED = "passed"
    SAME_ISSUE = "same_issue"
    DERIVED_ISSUE = "derived_issue"
    UNRELATED_ISSUE = "unrelated_issue"
    INSUFFICIENT_FEEDBACK = "insufficient_feedback"


class InvestigationMode(str, Enum):
    NORMAL = "normal"
    ROOT_CAUSE = "root_cause"


class CandidateStatus(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    CONFIRMED = "confirmed"
    RULED_OUT = "ruled_out"
    DEPRIORITIZED = "deprioritized"


class RelatedRiskStatus(str, Enum):
    PENDING = "pending"
    CHECKED = "checked"
    CLEARED = "cleared"
    NEEDS_FOLLOWUP = "needs_followup"

class Focus(BaseModel):
    hypothesis: Optional[str] = None
    test: Optional[str] = None
    expecting: Optional[str] = None
    next_action: Optional[str] = None

class Symptoms(BaseModel):
    expected: Optional[str] = None
    actual: Optional[str] = None
    errors: Optional[str] = None
    reproduction: Optional[str] = None
    reproduction_command: Optional[str] = None
    started: Optional[str] = None
    reproduction_verified: bool = False


class ObserverCauseCandidate(BaseModel):
    candidate: str
    failure_shape: Optional[str] = None
    why_it_fits: Optional[str] = None
    map_evidence: Optional[str] = None
    would_rule_out: Optional[str] = None
    recommended_first_probe: Optional[str] = None


class CandidateResolution(BaseModel):
    candidate: str
    disposition: CandidateDisposition
    notes: Optional[str] = None


class InvestigationCandidate(BaseModel):
    candidate_id: str
    candidate: str
    family: str
    status: CandidateStatus = CandidateStatus.PENDING
    why_it_fits: Optional[str] = None
    map_evidence: Optional[str] = None
    would_rule_out: Optional[str] = None
    recommended_first_probe: Optional[str] = None
    evidence_needed: List[str] = Field(default_factory=list)
    evidence_found: List[str] = Field(default_factory=list)
    related_targets: List[str] = Field(default_factory=list)


class RelatedRiskTarget(BaseModel):
    target: str
    reason: str
    scope: str
    status: RelatedRiskStatus = RelatedRiskStatus.PENDING
    evidence: List[str] = Field(default_factory=list)


class CausalCoverageState(BaseModel):
    competing_candidate_ruled_out: bool = False
    truth_owner_confirmed: bool = False
    boundary_break_localized: bool = False
    related_risk_scan_completed: bool = False
    closeout_ready: bool = False


class InvestigationContractState(BaseModel):
    primary_candidate_id: Optional[str] = None
    candidate_queue: List[InvestigationCandidate] = Field(default_factory=list)
    related_risk_targets: List[RelatedRiskTarget] = Field(default_factory=list)
    investigation_mode: InvestigationMode = InvestigationMode.NORMAL
    escalation_reason: Optional[str] = None
    causal_coverage_state: CausalCoverageState = Field(default_factory=CausalCoverageState)


class ObserverFramingState(BaseModel):
    summary: Optional[str] = None
    primary_suspected_loop: Optional[str] = None
    suspected_owning_layer: Optional[str] = None
    suspected_truth_owner: Optional[str] = None
    recommended_first_probe: Optional[str] = None
    contrarian_candidate: Optional[str] = None
    missing_questions: List[str] = Field(default_factory=list)
    alternative_cause_candidates: List[ObserverCauseCandidate] = Field(default_factory=list)


class TransitionMemoState(BaseModel):
    first_candidate_to_test: Optional[str] = None
    why_first: Optional[str] = None
    evidence_unlock: List[str] = Field(default_factory=list)
    carry_forward_notes: List[str] = Field(default_factory=list)

class EliminatedEntry(BaseModel):
    hypothesis: str
    evidence: str
    timestamp: datetime = Field(default_factory=datetime.now)

class EvidenceEntry(BaseModel):
    timestamp: datetime = Field(default_factory=datetime.now)
    source_type: Optional[str] = None
    source_ref: Optional[str] = None
    checked: str
    found: str
    implication: str


class OwnershipEntry(BaseModel):
    layer: str
    owns: str
    evidence: Optional[str] = None


class ClosedLoop(BaseModel):
    input_event: Optional[str] = None
    control_decision: Optional[str] = None
    resource_allocation: Optional[str] = None
    state_transition: Optional[str] = None
    external_observation: Optional[str] = None
    break_point: Optional[str] = None


class RootCause(BaseModel):
    summary: Optional[str] = None
    owning_layer: Optional[str] = None
    broken_control_state: Optional[str] = None
    failure_mechanism: Optional[str] = None
    loop_break: Optional[str] = None
    decisive_signal: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def coerce_from_string(cls, value):
        if isinstance(value, str):
            return {"summary": value}
        return value

    def display_text(self) -> str:
        return self.summary or "Not confirmed"


class SuggestedEvidenceLane(BaseModel):
    name: str
    focus: str
    evidence_to_collect: List[str] = Field(default_factory=list)
    join_goal: Optional[str] = None


class SuggestedDispatchTask(BaseModel):
    lane_name: str
    agent_role: str
    task_summary: str
    prompt: str


class SuggestedSpawnTask(BaseModel):
    lane_name: str
    agent_type: str
    reasoning_effort: str
    message: str


class ValidationCheck(BaseModel):
    command: str
    status: ValidationStatus
    output: str = ""


class ExecutionIntentState(BaseModel):
    outcome: Optional[str] = None
    constraints: List[str] = Field(default_factory=list)
    success_signals: List[str] = Field(default_factory=list)

class Resolution(BaseModel):
    model_config = ConfigDict(validate_assignment=True)
    root_cause: Optional[RootCause] = None
    alternative_hypotheses_considered: List[str] = Field(default_factory=list)
    alternative_hypotheses_ruled_out: List[str] = Field(default_factory=list)
    root_cause_confidence: Optional[str] = None
    fix: Optional[str] = None
    fix_scope: Optional[str] = None
    verification: Optional[str] = None
    validation_results: List[ValidationCheck] = Field(default_factory=list)
    files_changed: List[str] = Field(default_factory=list)
    fail_count: int = 0
    agent_fail_count: int = 0
    human_reopen_count: int = 0
    human_verification_outcome: HumanVerificationOutcome = HumanVerificationOutcome.PENDING
    report: Optional[str] = None
    decisive_signals: List[str] = Field(default_factory=list)
    rejected_surface_fixes: List[str] = Field(default_factory=list)
    loop_restoration_proof: List[str] = Field(default_factory=list)

class FeatureContext(BaseModel):
    feature_id: Optional[str] = None
    feature_name: Optional[str] = None
    feature_phase: Optional[str] = None
    summary: Optional[str] = None
    description: Optional[str] = None
    project_map_summary: Optional[str] = None
    spec_path: Optional[str] = None
    plan_path: Optional[str] = None
    tasks_path: Optional[str] = None
    constitution_path: Optional[str] = None
    roadmap_path: Optional[str] = None
    modified_files: List[str] = Field(default_factory=list)

class DebugGraphState(BaseModel):
    slug: str
    status: DebugStatus = DebugStatus.GATHERING
    trigger: str
    parent_slug: Optional[str] = None
    child_slugs: List[str] = Field(default_factory=list)
    resume_after_child: bool = False
    waiting_on_child_human_followup: bool = False
    diagnostic_profile: Optional[str] = None
    observer_mode: Optional[str] = None
    observer_framing_completed: bool = False
    framing_gate_passed: bool = False
    skip_observer_reason: Optional[str] = None
    current_node_id: Optional[str] = None
    created: datetime = Field(default_factory=datetime.now)
    updated: datetime = Field(default_factory=datetime.now)
    
    current_focus: Focus = Field(default_factory=Focus)
    symptoms: Symptoms = Field(default_factory=Symptoms)
    observer_framing: ObserverFramingState = Field(default_factory=ObserverFramingState)
    transition_memo: TransitionMemoState = Field(default_factory=TransitionMemoState)
    eliminated: List[EliminatedEntry] = Field(default_factory=list)
    evidence: List[EvidenceEntry] = Field(default_factory=list)
    suggested_evidence_lanes: List[SuggestedEvidenceLane] = Field(default_factory=list)
    truth_ownership: List[OwnershipEntry] = Field(default_factory=list)
    control_state: List[str] = Field(default_factory=list)
    observation_state: List[str] = Field(default_factory=list)
    closed_loop: ClosedLoop = Field(default_factory=ClosedLoop)
    resolution: Resolution = Field(default_factory=Resolution)
    context: FeatureContext = Field(default_factory=FeatureContext)
    recently_modified: List[str] = Field(default_factory=list)
    execution_intent: ExecutionIntentState = Field(default_factory=ExecutionIntentState)
    investigation_contract: InvestigationContractState = Field(default_factory=InvestigationContractState)
    candidate_resolutions: List[CandidateResolution] = Field(default_factory=list)
    think_subagent_prompt: Optional[str] = None
