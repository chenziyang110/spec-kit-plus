from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

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

class Resolution(BaseModel):
    root_cause: Optional[str] = None
    fix: Optional[str] = None
    verification: Optional[str] = None
    files_changed: List[str] = Field(default_factory=list)
    fail_count: int = 0
    report: Optional[str] = None

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
    current_node_id: Optional[str] = None
    created: datetime = Field(default_factory=datetime.now)
    updated: datetime = Field(default_factory=datetime.now)
    
    current_focus: Focus = Field(default_factory=Focus)
    symptoms: Symptoms = Field(default_factory=Symptoms)
    eliminated: List[EliminatedEntry] = Field(default_factory=list)
    evidence: List[EvidenceEntry] = Field(default_factory=list)
    resolution: Resolution = Field(default_factory=Resolution)
    context: FeatureContext = Field(default_factory=FeatureContext)
    recently_modified: List[str] = Field(default_factory=list)
