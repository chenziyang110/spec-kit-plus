from datetime import datetime
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field, model_validator, ConfigDict

class DebugStatus(str, Enum):
    GATHERING = "gathering"
    INVESTIGATING = "investigating"
    FIXING = "fixing"
    VERIFYING = "verifying"
    AWAITING_HUMAN = "awaiting_human_verify"
    RESOLVED = "resolved"

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

class EliminatedEntry(BaseModel):
    hypothesis: str
    evidence: str
    timestamp: datetime = Field(default_factory=datetime.now)

class EvidenceEntry(BaseModel):
    timestamp: datetime = Field(default_factory=datetime.now)
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

class Resolution(BaseModel):
    model_config = ConfigDict(validate_assignment=True)
    root_cause: Optional[RootCause] = None
    fix: Optional[str] = None
    verification: Optional[str] = None
    files_changed: List[str] = Field(default_factory=list)
    fail_count: int = 0
    report: Optional[str] = None
    decisive_signals: List[str] = Field(default_factory=list)
    rejected_surface_fixes: List[str] = Field(default_factory=list)

class FeatureContext(BaseModel):
    feature_id: Optional[str] = None
    feature_name: Optional[str] = None
    feature_phase: Optional[str] = None
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
    diagnostic_profile: Optional[str] = None
    current_node_id: Optional[str] = None
    created: datetime = Field(default_factory=datetime.now)
    updated: datetime = Field(default_factory=datetime.now)
    
    current_focus: Focus = Field(default_factory=Focus)
    symptoms: Symptoms = Field(default_factory=Symptoms)
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
