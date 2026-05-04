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


class ObserverExpansionStatus(str, Enum):
    NOT_APPLICABLE = "not_applicable"
    SUGGESTED = "suggested"
    USER_DECLINED = "user_declined"
    ENABLED = "enabled"
    COMPLETED = "completed"


class ProjectRuntimeProfile(str, Enum):
    FRONTEND_WEB_UI = "frontend/web-ui"
    BACKEND_API_SERVICE = "backend/api-service"
    FULL_STACK_WEB_APP = "full-stack/web-app"
    WORKER_QUEUE_CRON = "worker/queue/cron"
    CLI_AUTOMATION = "cli/automation"
    DATA_PIPELINE_INTEGRATION = "data-pipeline/integration"


class SymptomShape(str, Enum):
    EXACT_ERROR = "exact_error"
    PHENOMENON_ONLY = "phenomenon_only"


class LogReadiness(str, Enum):
    UNKNOWN = "unknown"
    SUFFICIENT_EXISTING_LOGS = "sufficient_existing_logs"
    INSUFFICIENT_NEED_INSTRUMENTATION = "insufficient_need_instrumentation"
    USER_MUST_PROVIDE_LOGS = "user_must_provide_logs"

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


class ExpandedObserverLightScores(BaseModel):
    likelihood: Optional[int] = None
    impact_radius: Optional[int] = None
    falsifiability: Optional[int] = None
    log_observability: Optional[int] = None


class ExpandedObserverEngineeringScores(BaseModel):
    cross_layer_span: Optional[int] = None
    indirect_causality_risk: Optional[int] = None
    evidence_gap: Optional[int] = None
    investigation_cost: Optional[int] = None


class ExpandedObserverCandidateBoardEntry(BaseModel):
    candidate_id: str
    dimension_origin: str
    family: str
    candidate: str
    why_it_fits: Optional[str] = None
    indirect_path: Optional[str] = None
    surface_vs_truth_owner_note: Optional[str] = None
    light_scores: ExpandedObserverLightScores = Field(default_factory=ExpandedObserverLightScores)


class ExpandedObserverTopCandidate(BaseModel):
    candidate_id: str
    family: str
    investigation_priority: int
    recommended_log_probe: Optional[str] = None
    engineering_scores: ExpandedObserverEngineeringScores = Field(
        default_factory=ExpandedObserverEngineeringScores
    )


class LogCandidateSignalMapEntry(BaseModel):
    candidate_id: str
    signals: List[str] = Field(default_factory=list)


class UserRequestPacketEntry(BaseModel):
    target_source: str
    time_window: str
    keywords_or_fields: List[str] = Field(default_factory=list)
    why_this_matters: str
    expected_signal_examples: List[str] = Field(default_factory=list)


class LogInvestigationPlanState(BaseModel):
    existing_log_targets: List[str] = Field(default_factory=list)
    candidate_signal_map: List[LogCandidateSignalMapEntry] = Field(default_factory=list)
    log_sufficiency_judgment: Optional[str] = None
    missing_observability: List[str] = Field(default_factory=list)
    instrumentation_targets: List[str] = Field(default_factory=list)
    instrumentation_style: List[str] = Field(default_factory=list)
    user_request_packet: List[UserRequestPacketEntry] = Field(default_factory=list)


class ObserverTopCandidateSummary(BaseModel):
    candidate_id: str
    family: Optional[str] = None
    investigation_priority: Optional[int] = None
    recommended_log_probe: Optional[str] = None
    why_it_fits: Optional[str] = None


class ExpandedObserverDimensionScan(BaseModel):
    symptom_layer: Optional[str] = None
    caller_or_input_layer: Optional[str] = None
    truth_owner_or_business_layer: Optional[str] = None
    storage_or_state_layer: Optional[str] = None
    cache_queue_async_layer: Optional[str] = None
    config_env_deploy_layer: Optional[str] = None
    external_boundary_layer: Optional[str] = None
    observability_layer: Optional[str] = None


class ExpandedObserverState(BaseModel):
    dimension_scan: ExpandedObserverDimensionScan = Field(default_factory=ExpandedObserverDimensionScan)
    candidate_board: List[ExpandedObserverCandidateBoardEntry] = Field(default_factory=list)
    top_candidates: List[ExpandedObserverTopCandidate] = Field(default_factory=list)
    log_investigation_plan: LogInvestigationPlanState = Field(default_factory=LogInvestigationPlanState)


class InvestigationContractState(BaseModel):
    primary_candidate_id: Optional[str] = None
    candidate_queue: List[InvestigationCandidate] = Field(default_factory=list)
    related_risk_targets: List[RelatedRiskTarget] = Field(default_factory=list)
    investigation_mode: InvestigationMode = InvestigationMode.NORMAL
    escalation_reason: Optional[str] = None
    causal_coverage_state: CausalCoverageState = Field(default_factory=CausalCoverageState)
    top_candidates: List[ExpandedObserverTopCandidate] = Field(default_factory=list)
    log_investigation_plan: LogInvestigationPlanState = Field(default_factory=LogInvestigationPlanState)


class CausalMapCandidate(BaseModel):
    candidate_id: str
    family: str
    candidate: str
    why_it_fits: Optional[str] = None
    map_evidence: Optional[str] = None
    falsifier: Optional[str] = None
    break_edge: Optional[str] = None
    bypass_path: Optional[str] = None
    recommended_first_probe: Optional[str] = None


class CausalMapRiskTarget(BaseModel):
    target: str
    reason: str
    family: str
    scope: str = "nearest-neighbor"
    falsifier: Optional[str] = None


class CausalMapState(BaseModel):
    symptom_anchor: Optional[str] = None
    closed_loop_path: List[str] = Field(default_factory=list)
    break_edges: List[str] = Field(default_factory=list)
    bypass_paths: List[str] = Field(default_factory=list)
    family_coverage: List[str] = Field(default_factory=list)
    candidates: List[CausalMapCandidate] = Field(default_factory=list)
    adjacent_risk_targets: List[CausalMapRiskTarget] = Field(default_factory=list)


class ObserverFramingState(BaseModel):
    summary: Optional[str] = None
    primary_suspected_loop: Optional[str] = None
    suspected_owning_layer: Optional[str] = None
    suspected_truth_owner: Optional[str] = None
    recommended_first_probe: Optional[str] = None
    contrarian_candidate: Optional[str] = None
    project_runtime_profile: Optional[ProjectRuntimeProfile] = None
    symptom_shape: Optional[SymptomShape] = None
    log_readiness: Optional[LogReadiness] = None
    top_candidate_summary: Optional[ObserverTopCandidateSummary] = None
    surface_truth_owner_distinction: Optional[str] = None
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
    causal_map_completed: bool = False
    contract_generation_completed: bool = False
    observer_mode: Optional[str] = None
    observer_expansion_status: Optional[ObserverExpansionStatus] = None
    observer_expansion_reason: Optional[str] = None
    project_runtime_profile: Optional[ProjectRuntimeProfile] = None
    symptom_shape: Optional[SymptomShape] = None
    log_readiness: Optional[LogReadiness] = None
    observer_framing_completed: bool = False
    framing_gate_passed: bool = False
    skip_observer_reason: Optional[str] = None
    current_node_id: Optional[str] = None
    created: datetime = Field(default_factory=datetime.now)
    updated: datetime = Field(default_factory=datetime.now)
    
    current_focus: Focus = Field(default_factory=Focus)
    symptoms: Symptoms = Field(default_factory=Symptoms)
    causal_map: CausalMapState = Field(default_factory=CausalMapState)
    observer_framing: ObserverFramingState = Field(default_factory=ObserverFramingState)
    expanded_observer: ExpandedObserverState = Field(default_factory=ExpandedObserverState)
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
    contract_subagent_prompt: Optional[str] = None
