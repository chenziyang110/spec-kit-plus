package query

import (
	"encoding/json"
	"fmt"
	"strings"
)

const semanticAuditArtifactType = "semantic_routing_audit"

type SemanticAuditRequest struct {
	Version               int                                `json:"version"`
	WorkContract          SemanticAuditWorkContract          `json:"work_contract"`
	SemanticIntakeInput   SemanticIntakeRequest              `json:"semantic_intake_input"`
	SemanticIntakeOutput  SemanticIntakePayload              `json:"semantic_intake_output"`
	RouteDecision         SemanticAuditRouteDecisionInput    `json:"route_decision"`
	PermissionDecision    SemanticAuditPermissionInput       `json:"permission_decision"`
	LiveEvidenceCapture   []SemanticAuditCapturedEvidence    `json:"live_evidence_capture,omitempty"`
	VerificationResults   []SemanticAuditVerificationResult  `json:"verification_results,omitempty"`
	WorkflowAuthorization SemanticAuditWorkflowAuthorization `json:"workflow_authorization,omitempty"`
	ActionLog             []SemanticAuditAction              `json:"action_log,omitempty"`
	RouteCorrections      []SemanticAuditRouteCorrection     `json:"route_corrections,omitempty"`
}

type SemanticAuditWorkContract struct {
	ID                 string                              `json:"id,omitempty"`
	RawRequest         string                              `json:"raw_request"`
	NormalizedGoal     string                              `json:"normalized_goal,omitempty"`
	WorkflowIntent     string                              `json:"workflow_intent,omitempty"`
	ExtractedFacets    []string                            `json:"extracted_facets,omitempty"`
	SemanticIntakeRef  string                              `json:"semantic_intake_ref,omitempty"`
	SelectedConceptIDs []string                            `json:"selected_concept_ids,omitempty"`
	RejectedConceptIDs []string                            `json:"rejected_concept_ids,omitempty"`
	EvidencePlan       []SemanticAuditEvidencePlanStep     `json:"evidence_plan,omitempty"`
	PermissionDecision SemanticAuditWorkContractPermission `json:"permission_decision"`
	LearningContract   SemanticAuditWorkContractLearning   `json:"learning_contract"`
}

type SemanticAuditEvidencePlanStep struct {
	EvidenceNeed    string `json:"evidence_need"`
	SuggestedAction string `json:"suggested_action,omitempty"`
	OwnerRef        string `json:"owner_ref,omitempty"`
}

type SemanticAuditWorkContractPermission struct {
	CurrentLevel               string   `json:"current_level,omitempty"`
	MaximumWithoutLiveEvidence string   `json:"maximum_without_live_evidence,omitempty"`
	BlockedActions             []string `json:"blocked_actions,omitempty"`
}

type SemanticAuditWorkContractLearning struct {
	MemoryLevel       string   `json:"memory_level,omitempty"`
	PromotionRequires []string `json:"promotion_requires,omitempty"`
}

type SemanticAuditRouteDecisionInput struct {
	SelectedCandidateIDs []string `json:"selected_candidate_ids,omitempty"`
	ContrastCandidateIDs []string `json:"contrast_candidate_ids,omitempty"`
	RejectedCandidateIDs []string `json:"rejected_candidate_ids,omitempty"`
	SelectionReason      string   `json:"selection_reason,omitempty"`
}

type SemanticAuditPermissionInput struct {
	RequestedLevel    string   `json:"requested_level,omitempty"`
	EvidenceLevel     string   `json:"evidence_level,omitempty"`
	RequestedActions  []string `json:"requested_actions,omitempty"`
	UpgradeReasons    []string `json:"upgrade_reasons,omitempty"`
	DowngradeReasons  []string `json:"downgrade_reasons,omitempty"`
	VerificationOwner string   `json:"verification_owner,omitempty"`
}

type SemanticAuditArtifact struct {
	Version                    int                                     `json:"version"`
	ArtifactType               string                                  `json:"artifact_type"`
	WorkContract               SemanticAuditWorkContract               `json:"work_contract"`
	SemanticIntakeSnapshot     SemanticAuditIntakeSnapshot             `json:"semantic_intake_snapshot"`
	RouteDecision              SemanticAuditRouteDecision              `json:"route_decision"`
	PermissionDecision         SemanticAuditPermissionDecision         `json:"permission_decision"`
	InspectionPlan             SemanticAuditInspectionPlan             `json:"inspection_plan"`
	OwnerBundleConfidence      SemanticAuditOwnerBundleConfidence      `json:"owner_bundle_confidence"`
	OwnerMissExpansion         SemanticAuditOwnerMissExpansion         `json:"owner_miss_expansion"`
	VerificationOwnerDiscovery SemanticAuditVerificationOwnerDiscovery `json:"verification_owner_discovery"`
	LiveEvidenceCapture        []SemanticAuditCapturedEvidence         `json:"live_evidence_capture"`
	VerificationResults        []SemanticAuditVerificationResult       `json:"verification_results"`
	WorkflowAuthorization      SemanticAuditWorkflowAuthorization      `json:"workflow_authorization"`
	RerankAssessment           SemanticAuditRerankAssessment           `json:"rerank_assessment"`
	ClaimReadiness             SemanticAuditClaimReadiness             `json:"claim_readiness"`
	ActionLog                  []SemanticAuditAction                   `json:"action_log"`
	RouteCorrections           []SemanticAuditRouteCorrection          `json:"route_corrections"`
	Replay                     SemanticAuditReplay                     `json:"replay"`
	LearningBoundary           SemanticAuditLearningBoundary           `json:"learning_boundary"`
}

type SemanticAuditIntakeSnapshot struct {
	Input  SemanticIntakeRequest `json:"input"`
	Output SemanticIntakePayload `json:"output"`
}

type SemanticAuditRouteDecision struct {
	SelectedCandidateIDs []string                          `json:"selected_candidate_ids"`
	ContrastCandidateIDs []string                          `json:"contrast_candidate_ids"`
	RejectedCandidateIDs []string                          `json:"rejected_candidate_ids"`
	SelectedCandidates   []SemanticIntakeCandidate         `json:"selected_candidates"`
	ContrastCandidates   []SemanticIntakeCandidate         `json:"contrast_candidates"`
	RejectedCandidates   []SemanticIntakeRejectedCandidate `json:"rejected_candidates"`
	SelectionReason      string                            `json:"selection_reason,omitempty"`
}

type SemanticAuditPermissionDecision struct {
	RequestedLevel    string   `json:"requested_level,omitempty"`
	AllowedLevel      string   `json:"allowed_level"`
	EvidenceLevel     string   `json:"evidence_level"`
	RequestedActions  []string `json:"requested_actions"`
	BlockedActions    []string `json:"blocked_actions"`
	UpgradeReasons    []string `json:"upgrade_reasons,omitempty"`
	DowngradeReasons  []string `json:"downgrade_reasons"`
	VerificationOwner string   `json:"verification_owner,omitempty"`
}

type SemanticAuditInspectionPlan struct {
	Readiness           string                           `json:"readiness"`
	MaxPermission       string                           `json:"max_permission"`
	Steps               []SemanticAuditInspectionStep    `json:"steps"`
	LiveEvidenceCapture SemanticAuditLiveEvidenceCapture `json:"live_evidence_capture"`
	RerankAfterInspect  SemanticAuditRerankAfterInspect  `json:"rerank_after_inspect"`
	StaleIndexDowngrade SemanticAuditStaleIndexDowngrade `json:"stale_index_downgrade"`
	BlockedActions      []string                         `json:"blocked_actions"`
}

type SemanticAuditInspectionStep struct {
	ID              string `json:"id"`
	CandidateID     string `json:"candidate_id,omitempty"`
	EvidenceNeed    string `json:"evidence_need"`
	TargetPath      string `json:"target_path,omitempty"`
	TargetID        string `json:"target_id,omitempty"`
	SuggestedAction string `json:"suggested_action,omitempty"`
	AllowedAction   string `json:"allowed_action"`
	PermissionLevel string `json:"permission_level"`
	ExpectedSignal  string `json:"expected_signal,omitempty"`
	OnContradiction string `json:"on_contradiction"`
}

type SemanticAuditLiveEvidenceCapture struct {
	RequiredFields []string `json:"required_fields"`
	Boundary       string   `json:"boundary"`
}

type SemanticAuditRerankAfterInspect struct {
	RequiredWhen               []string `json:"required_when"`
	Inputs                     []string `json:"inputs"`
	BlockedClaimsUntilRerank   []string `json:"blocked_claims_until_rerank"`
	PermissionPromotionBlocked bool     `json:"permission_promotion_blocked"`
}

type SemanticAuditStaleIndexDowngrade struct {
	Conditions  []string `json:"conditions"`
	DowngradeTo string   `json:"downgrade_to"`
	Reason      string   `json:"reason"`
}

type SemanticAuditOwnerBundleConfidence struct {
	Summary    string                              `json:"summary"`
	Candidates []SemanticAuditOwnerBundleCandidate `json:"candidates"`
}

type SemanticAuditOwnerBundleCandidate struct {
	CandidateID       string   `json:"candidate_id"`
	PrimaryPaths      []string `json:"primary_paths"`
	SupportingPaths   []string `json:"supporting_paths"`
	TruthPaths        []string `json:"truth_paths"`
	VerificationPaths []string `json:"verification_paths"`
	Confidence        string   `json:"confidence"`
	ConfidenceReasons []string `json:"confidence_reasons"`
	CoveredOwnerRoles []string `json:"covered_owner_roles"`
	MissingOwnerRoles []string `json:"missing_owner_roles"`
}

type SemanticAuditOwnerMissExpansion struct {
	MaxRadius        int      `json:"max_radius"`
	AllowedTargetIDs []string `json:"allowed_target_ids"`
	BlockedReason    string   `json:"blocked_reason,omitempty"`
	OnMiss           string   `json:"on_miss"`
	BlockedActions   []string `json:"blocked_actions"`
}

type SemanticAuditVerificationOwnerDiscovery struct {
	Summary          string                                    `json:"summary"`
	RequiredOwners   []SemanticAuditVerificationOwnerCandidate `json:"required_owners"`
	BlockedClaims    []string                                  `json:"blocked_claims"`
	PromotionBlocked bool                                      `json:"promotion_blocked"`
	Reason           string                                    `json:"reason,omitempty"`
}

type SemanticAuditVerificationOwnerCandidate struct {
	CandidateID                   string   `json:"candidate_id"`
	Status                        string   `json:"status"`
	VerificationPaths             []string `json:"verification_paths"`
	VerificationCommandCandidates []string `json:"verification_command_candidates"`
	RequiredSignals               []string `json:"required_signals"`
	RequiredAction                string   `json:"required_action,omitempty"`
	BlockedBy                     []string `json:"blocked_by"`
}

type SemanticAuditCapturedEvidence struct {
	StepID                 string   `json:"step_id,omitempty"`
	ReadPath               string   `json:"read_path,omitempty"`
	EvidenceNeed           string   `json:"evidence_need,omitempty"`
	SourceKind             string   `json:"source_kind,omitempty"`
	SourceRef              string   `json:"source_ref,omitempty"`
	LineRefs               []string `json:"line_refs,omitempty"`
	ObservedSignal         string   `json:"observed_signal,omitempty"`
	SupportsCandidateID    string   `json:"supports_candidate_id,omitempty"`
	SupportsCandidate      bool     `json:"supports_candidate,omitempty"`
	ContradictsCandidateID string   `json:"contradicts_candidate_id,omitempty"`
	ContradictsCandidate   bool     `json:"contradicts_candidate,omitempty"`
	SupportsFacets         []string `json:"supports_facets,omitempty"`
	MissingFacets          []string `json:"missing_facets,omitempty"`
	ContentHash            string   `json:"content_hash,omitempty"`
	CapturedAt             string   `json:"captured_at,omitempty"`
	EvidenceRef            string   `json:"evidence_ref,omitempty"`
	VerificationOwner      string   `json:"verification_owner,omitempty"`
}

type SemanticAuditVerificationResult struct {
	CandidateID      string   `json:"candidate_id,omitempty"`
	VerificationPath string   `json:"verification_path,omitempty"`
	Command          string   `json:"command,omitempty"`
	Status           string   `json:"status,omitempty"`
	ClaimType        string   `json:"claim_type,omitempty"`
	ClaimTypes       []string `json:"claim_types,omitempty"`
	EvidenceRef      string   `json:"evidence_ref,omitempty"`
	CapturedAt       string   `json:"captured_at,omitempty"`
	Summary          string   `json:"summary,omitempty"`
}

type SemanticAuditWorkflowAuthorization struct {
	WorkflowIntent      string                            `json:"workflow_intent,omitempty"`
	Status              string                            `json:"status,omitempty"`
	AuthorizedClaims    []string                          `json:"authorized_claims,omitempty"`
	ActiveClaimType     string                            `json:"active_claim_type,omitempty"`
	AuthorizationRef    string                            `json:"authorization_ref,omitempty"`
	ClaimAuthorizations []SemanticAuditClaimAuthorization `json:"claim_authorizations,omitempty"`
	Reason              string                            `json:"reason,omitempty"`
}

type SemanticAuditClaimAuthorization struct {
	ClaimType                string   `json:"claim_type,omitempty"`
	Status                   string   `json:"status,omitempty"`
	AuthorizationRef         string   `json:"authorization_ref,omitempty"`
	VerificationEvidenceRefs []string `json:"verification_evidence_refs,omitempty"`
	Reason                   string   `json:"reason,omitempty"`
}

type SemanticAuditRerankAssessment struct {
	Status                       string                                    `json:"status"`
	SelectedCandidateID          string                                    `json:"selected_candidate_id,omitempty"`
	SupportingEvidenceRefs       []string                                  `json:"supporting_evidence_refs"`
	ContradictingEvidenceRefs    []string                                  `json:"contradicting_evidence_refs"`
	PermissionPromotionCandidate SemanticAuditPermissionPromotionCandidate `json:"permission_promotion_candidate"`
}

type SemanticAuditPermissionPromotionCandidate struct {
	CurrentAllowedLevel string   `json:"current_allowed_level"`
	CandidateLevel      string   `json:"candidate_level"`
	Status              string   `json:"status"`
	Granted             bool     `json:"granted"`
	BlockedBy           []string `json:"blocked_by"`
	Reason              string   `json:"reason,omitempty"`
}

type SemanticAuditClaimReadiness struct {
	InspectStatus         string   `json:"inspect_status"`
	InspectReady          bool     `json:"inspect_ready"`
	ChangeStatus          string   `json:"change_status"`
	ChangeReady           bool     `json:"change_ready"`
	ClaimStatus           string   `json:"claim_status"`
	ClaimType             string   `json:"claim_type,omitempty"`
	ClaimReady            bool     `json:"claim_ready"`
	VerificationSatisfied bool     `json:"verification_satisfied"`
	PromotionBlocked      bool     `json:"promotion_blocked"`
	BlockedBy             []string `json:"blocked_by"`
	ClaimVerificationRefs []string `json:"claim_verification_refs,omitempty"`
	EvidenceTrail         []string `json:"evidence_trail"`
	Reason                string   `json:"reason,omitempty"`
}

type semanticAuditInspectionNeed struct {
	evidenceNeed    string
	suggestedAction string
	ownerRef        string
}

type SemanticAuditAction struct {
	Step             string `json:"step"`
	InputRef         string `json:"input_ref,omitempty"`
	OutputRef        string `json:"output_ref,omitempty"`
	PermissionBefore string `json:"permission_before,omitempty"`
	PermissionAfter  string `json:"permission_after,omitempty"`
	Summary          string `json:"summary,omitempty"`
}

type SemanticAuditRouteCorrection struct {
	Phrase             string   `json:"phrase"`
	RejectedConceptID  string   `json:"rejected_concept_id"`
	FalseMatchType     string   `json:"false_match_type"`
	CorrectionReason   string   `json:"correction_reason,omitempty"`
	RequiredSignals    []string `json:"required_signals,omitempty"`
	SuppressionSignals []string `json:"suppression_signals,omitempty"`
}

type SemanticAuditReplay struct {
	RequiredFields                          []string `json:"required_fields"`
	BlockedFinalClaims                      []string `json:"blocked_final_claims"`
	MaxPermissionFromSemanticIntake         string   `json:"max_permission_from_semantic_intake"`
	PermissionPromotionRequiresLiveEvidence bool     `json:"permission_promotion_requires_live_evidence"`
}

type SemanticAuditLearningBoundary struct {
	MaxMemoryLevelFromSemanticIntake string   `json:"max_memory_level_from_semantic_intake"`
	PromotionRequires                []string `json:"promotion_requires"`
}

func ParseSemanticAuditRequest(data []byte) (SemanticAuditRequest, error) {
	var request SemanticAuditRequest
	if err := json.Unmarshal(data, &request); err != nil {
		return SemanticAuditRequest{}, fmt.Errorf("parse semantic-audit request: %w", err)
	}
	if request.WorkContract.RawRequest == "" && request.SemanticIntakeInput.RawRequest == "" {
		var wrapped struct {
			SemanticAuditInput SemanticAuditRequest `json:"semantic_audit_input"`
		}
		if err := json.Unmarshal(data, &wrapped); err != nil {
			return SemanticAuditRequest{}, fmt.Errorf("parse semantic-audit request: %w", err)
		}
		if wrapped.SemanticAuditInput.WorkContract.RawRequest != "" || wrapped.SemanticAuditInput.SemanticIntakeInput.RawRequest != "" {
			request = wrapped.SemanticAuditInput
		}
	}
	request = normalizeSemanticAuditRequest(request)
	if reasons := validateSemanticAuditRequest(request); len(reasons) > 0 {
		return SemanticAuditRequest{}, fmt.Errorf("invalid semantic-audit request: %s", strings.Join(reasons, "; "))
	}
	return request, nil
}

func BuildSemanticAudit(request SemanticAuditRequest) (SemanticAuditArtifact, error) {
	request = normalizeSemanticAuditRequest(request)
	if reasons := validateSemanticAuditRequest(request); len(reasons) > 0 {
		return SemanticAuditArtifact{}, fmt.Errorf("invalid semantic-audit request: %s", strings.Join(reasons, "; "))
	}

	routeDecision, err := semanticAuditRouteDecision(request)
	if err != nil {
		return SemanticAuditArtifact{}, err
	}
	permissionDecision := semanticAuditPermissionDecision(request)
	corrections := semanticAuditCorrections(request)
	liveEvidence := semanticAuditCapturedEvidence(request.LiveEvidenceCapture)
	verificationResults := semanticAuditVerificationResults(request.VerificationResults)
	workflowAuthorization := semanticAuditWorkflowAuthorization(request.WorkflowAuthorization, request.WorkContract.WorkflowIntent)
	inspectionPlanForRerank := semanticAuditInspectionPlan(request, routeDecision, permissionDecision)
	rerankAssessment := semanticAuditRerankAssessment(routeDecision, permissionDecision, inspectionPlanForRerank, liveEvidence)
	permissionDecision = semanticAuditApplyRerankPermission(permissionDecision, rerankAssessment)
	inspectionPlan := semanticAuditInspectionPlan(request, routeDecision, permissionDecision)
	ownerBundleConfidence := semanticAuditOwnerBundleConfidence(routeDecision)
	ownerMissExpansion := semanticAuditOwnerMissExpansion(request, inspectionPlan)
	verificationOwnerDiscovery := semanticAuditVerificationOwnerDiscovery(routeDecision)
	claimReadiness := semanticAuditClaimReadiness(inspectionPlan, routeDecision, rerankAssessment, verificationOwnerDiscovery, liveEvidence, verificationResults, workflowAuthorization)

	return SemanticAuditArtifact{
		Version:      1,
		ArtifactType: semanticAuditArtifactType,
		WorkContract: request.WorkContract,
		SemanticIntakeSnapshot: SemanticAuditIntakeSnapshot{
			Input:  request.SemanticIntakeInput,
			Output: request.SemanticIntakeOutput,
		},
		RouteDecision:              routeDecision,
		PermissionDecision:         permissionDecision,
		InspectionPlan:             inspectionPlan,
		OwnerBundleConfidence:      ownerBundleConfidence,
		OwnerMissExpansion:         ownerMissExpansion,
		VerificationOwnerDiscovery: verificationOwnerDiscovery,
		LiveEvidenceCapture:        liveEvidence,
		VerificationResults:        verificationResults,
		WorkflowAuthorization:      workflowAuthorization,
		RerankAssessment:           rerankAssessment,
		ClaimReadiness:             claimReadiness,
		ActionLog:                  semanticAuditActions(request.ActionLog),
		RouteCorrections:           corrections,
		Replay: SemanticAuditReplay{
			RequiredFields: []string{
				"work_contract",
				"semantic_intake_input",
				"semantic_intake_output",
				"route_decision",
				"permission_decision",
				"action_log",
			},
			BlockedFinalClaims: []string{
				"root_cause_claim",
				"fixed_claim",
				"completed_claim",
				"release_safe",
			},
			MaxPermissionFromSemanticIntake:         "P2",
			PermissionPromotionRequiresLiveEvidence: true,
		},
		LearningBoundary: SemanticAuditLearningBoundary{
			MaxMemoryLevelFromSemanticIntake: "M1",
			PromotionRequires: []string{
				"live_source_evidence",
				"user_confirmation_or_verified_behavior",
				"replayable_audit_artifact",
			},
		},
	}, nil
}

func normalizeSemanticAuditRequest(request SemanticAuditRequest) SemanticAuditRequest {
	if request.Version == 0 {
		request.Version = 1
	}
	request.WorkContract = normalizeSemanticAuditWorkContract(request.WorkContract)
	request.SemanticIntakeInput.RawRequest = strings.TrimSpace(request.SemanticIntakeInput.RawRequest)
	request.SemanticIntakeInput.AgentFacets = normalizeSemanticIntakeFacetSet(request.SemanticIntakeInput.AgentFacets)
	request.SemanticIntakeInput.Options = normalizeSemanticIntakeOptions(request.SemanticIntakeInput.Options)
	request.SemanticIntakeOutput = normalizeSemanticAuditIntakeOutput(request.SemanticIntakeOutput)
	request.RouteDecision.SelectedCandidateIDs = normalizeStrings(request.RouteDecision.SelectedCandidateIDs)
	request.RouteDecision.ContrastCandidateIDs = normalizeStrings(request.RouteDecision.ContrastCandidateIDs)
	request.RouteDecision.RejectedCandidateIDs = normalizeStrings(request.RouteDecision.RejectedCandidateIDs)
	request.RouteDecision.SelectionReason = strings.TrimSpace(request.RouteDecision.SelectionReason)
	request.PermissionDecision.RequestedLevel = strings.ToUpper(strings.TrimSpace(request.PermissionDecision.RequestedLevel))
	request.PermissionDecision.EvidenceLevel = strings.TrimSpace(request.PermissionDecision.EvidenceLevel)
	request.PermissionDecision.RequestedActions = normalizeStrings(request.PermissionDecision.RequestedActions)
	request.PermissionDecision.UpgradeReasons = normalizeStrings(request.PermissionDecision.UpgradeReasons)
	request.PermissionDecision.DowngradeReasons = normalizeStrings(request.PermissionDecision.DowngradeReasons)
	request.PermissionDecision.VerificationOwner = strings.TrimSpace(request.PermissionDecision.VerificationOwner)
	request.LiveEvidenceCapture = semanticAuditCapturedEvidence(request.LiveEvidenceCapture)
	request.VerificationResults = semanticAuditVerificationResults(request.VerificationResults)
	request.WorkflowAuthorization = semanticAuditWorkflowAuthorization(request.WorkflowAuthorization, request.WorkContract.WorkflowIntent)
	return request
}

func normalizeSemanticAuditWorkContract(contract SemanticAuditWorkContract) SemanticAuditWorkContract {
	contract.ID = strings.TrimSpace(contract.ID)
	contract.RawRequest = strings.TrimSpace(contract.RawRequest)
	contract.NormalizedGoal = strings.TrimSpace(contract.NormalizedGoal)
	contract.WorkflowIntent = strings.TrimSpace(contract.WorkflowIntent)
	contract.ExtractedFacets = normalizeStrings(contract.ExtractedFacets)
	contract.SemanticIntakeRef = strings.TrimSpace(contract.SemanticIntakeRef)
	contract.SelectedConceptIDs = normalizeStrings(contract.SelectedConceptIDs)
	contract.RejectedConceptIDs = normalizeStrings(contract.RejectedConceptIDs)
	contract.EvidencePlan = normalizeSemanticAuditEvidencePlan(contract.EvidencePlan)
	contract.PermissionDecision.CurrentLevel = strings.ToUpper(strings.TrimSpace(contract.PermissionDecision.CurrentLevel))
	contract.PermissionDecision.MaximumWithoutLiveEvidence = strings.ToUpper(strings.TrimSpace(contract.PermissionDecision.MaximumWithoutLiveEvidence))
	contract.PermissionDecision.BlockedActions = normalizeStrings(contract.PermissionDecision.BlockedActions)
	contract.LearningContract.MemoryLevel = strings.ToUpper(strings.TrimSpace(contract.LearningContract.MemoryLevel))
	contract.LearningContract.PromotionRequires = normalizeStrings(contract.LearningContract.PromotionRequires)
	return contract
}

func normalizeSemanticAuditEvidencePlan(steps []SemanticAuditEvidencePlanStep) []SemanticAuditEvidencePlanStep {
	result := make([]SemanticAuditEvidencePlanStep, 0, len(steps))
	for _, step := range steps {
		step.EvidenceNeed = strings.TrimSpace(step.EvidenceNeed)
		step.SuggestedAction = strings.TrimSpace(step.SuggestedAction)
		step.OwnerRef = strings.TrimSpace(step.OwnerRef)
		if step.EvidenceNeed != "" {
			result = append(result, step)
		}
	}
	if result == nil {
		return []SemanticAuditEvidencePlanStep{}
	}
	return result
}

func normalizeSemanticAuditIntakeOutput(output SemanticIntakePayload) SemanticIntakePayload {
	output.Readiness = strings.TrimSpace(output.Readiness)
	output.ReadinessReason = normalizeStrings(output.ReadinessReason)
	if output.CandidateUniverse.PrimaryCandidates == nil {
		output.CandidateUniverse.PrimaryCandidates = []SemanticIntakeCandidate{}
	}
	if output.CandidateUniverse.ContrastCandidates == nil {
		output.CandidateUniverse.ContrastCandidates = []SemanticIntakeCandidate{}
	}
	if output.CandidateUniverse.RejectedCandidates == nil {
		output.CandidateUniverse.RejectedCandidates = []SemanticIntakeRejectedCandidate{}
	}
	output.PermissionHint.MaximumWithoutLiveEvidence = strings.ToUpper(strings.TrimSpace(output.PermissionHint.MaximumWithoutLiveEvidence))
	output.PermissionHint.BlockedActions = normalizeStrings(output.PermissionHint.BlockedActions)
	output.SuggestedRecovery = normalizeStrings(output.SuggestedRecovery)
	return output
}

func validateSemanticAuditRequest(request SemanticAuditRequest) []string {
	reasons := []string{}
	if request.Version != 1 {
		reasons = append(reasons, "version must be 1")
	}
	if request.WorkContract.RawRequest == "" {
		reasons = append(reasons, "work_contract.raw_request is required")
	}
	if request.SemanticIntakeInput.RawRequest == "" {
		reasons = append(reasons, "semantic_intake_input.raw_request is required")
	}
	if len(semanticIntakeFacetStrings(request.SemanticIntakeInput.AgentFacets)) == 0 {
		reasons = append(reasons, "semantic_intake_input.agent_facets is required")
	}
	if request.SemanticIntakeInput.Version != 0 && request.SemanticIntakeInput.Version != 1 {
		reasons = append(reasons, "semantic_intake_input.version must be 1")
	}
	if request.SemanticIntakeOutput.Version != 1 {
		reasons = append(reasons, "semantic_intake_output.version must be 1")
	}
	if request.SemanticIntakeOutput.Readiness == "" {
		reasons = append(reasons, "semantic_intake_output.readiness is required")
	}
	if len(request.RouteDecision.SelectedCandidateIDs) == 0 && request.SemanticIntakeOutput.Readiness == semanticIntakeReadinessQueryReady {
		reasons = append(reasons, "route_decision.selected_candidate_ids is required for query_ready semantic intake")
	}
	return reasons
}

func semanticAuditRouteDecision(request SemanticAuditRequest) (SemanticAuditRouteDecision, error) {
	primaryByID := map[string]SemanticIntakeCandidate{}
	for _, candidate := range request.SemanticIntakeOutput.CandidateUniverse.PrimaryCandidates {
		primaryByID[candidate.ID] = candidate
	}
	contrastByID := map[string]SemanticIntakeCandidate{}
	for _, candidate := range request.SemanticIntakeOutput.CandidateUniverse.ContrastCandidates {
		contrastByID[candidate.ID] = candidate
	}
	rejectedByID := map[string]SemanticIntakeRejectedCandidate{}
	for _, candidate := range request.SemanticIntakeOutput.CandidateUniverse.RejectedCandidates {
		rejectedByID[candidate.ID] = candidate
	}

	selectedCandidates := []SemanticIntakeCandidate{}
	for _, id := range request.RouteDecision.SelectedCandidateIDs {
		candidate, ok := primaryByID[id]
		if !ok {
			return SemanticAuditRouteDecision{}, fmt.Errorf("semantic-audit selected candidate %q is not in semantic_intake_output.candidate_universe.primary_candidates", id)
		}
		selectedCandidates = append(selectedCandidates, candidate)
	}
	contrastCandidates := []SemanticIntakeCandidate{}
	for _, id := range request.RouteDecision.ContrastCandidateIDs {
		candidate, ok := contrastByID[id]
		if !ok {
			return SemanticAuditRouteDecision{}, fmt.Errorf("semantic-audit contrast candidate %q is not in semantic_intake_output.candidate_universe.contrast_candidates", id)
		}
		contrastCandidates = append(contrastCandidates, candidate)
	}
	rejectedCandidates := []SemanticIntakeRejectedCandidate{}
	for _, id := range request.RouteDecision.RejectedCandidateIDs {
		candidate, ok := rejectedByID[id]
		if !ok {
			return SemanticAuditRouteDecision{}, fmt.Errorf("semantic-audit rejected candidate %q is not in semantic_intake_output.candidate_universe.rejected_candidates", id)
		}
		rejectedCandidates = append(rejectedCandidates, candidate)
	}

	return SemanticAuditRouteDecision{
		SelectedCandidateIDs: request.RouteDecision.SelectedCandidateIDs,
		ContrastCandidateIDs: request.RouteDecision.ContrastCandidateIDs,
		RejectedCandidateIDs: request.RouteDecision.RejectedCandidateIDs,
		SelectedCandidates:   selectedCandidates,
		ContrastCandidates:   contrastCandidates,
		RejectedCandidates:   rejectedCandidates,
		SelectionReason:      request.RouteDecision.SelectionReason,
	}, nil
}

func semanticAuditPermissionDecision(request SemanticAuditRequest) SemanticAuditPermissionDecision {
	requested := request.PermissionDecision.RequestedLevel
	if requested == "" {
		requested = request.SemanticIntakeOutput.PermissionHint.MaximumWithoutLiveEvidence
	}
	if requested == "" {
		requested = "P0"
	}
	allowed := requested
	downgradeReasons := append([]string{}, request.PermissionDecision.DowngradeReasons...)
	if semanticAuditPermissionRank(allowed) > semanticAuditPermissionRank("P2") {
		allowed = "P2"
		downgradeReasons = append(downgradeReasons, "semantic_intake_only_cannot_raise_above_p2")
	}
	intakeCap := request.SemanticIntakeOutput.PermissionHint.MaximumWithoutLiveEvidence
	if intakeCap == "" {
		intakeCap = "P0"
	}
	if semanticAuditPermissionRank(allowed) > semanticAuditPermissionRank(intakeCap) {
		allowed = intakeCap
		downgradeReasons = append(downgradeReasons, "semantic_intake_permission_hint_caps_allowed_level")
	}

	blocked := []string{
		"change",
		"root_cause_claim",
		"fixed_claim",
		"completed_claim",
		"release_safe",
	}
	blocked = append(blocked, request.SemanticIntakeOutput.PermissionHint.BlockedActions...)
	for _, action := range request.PermissionDecision.RequestedActions {
		if action == "change" || strings.HasSuffix(action, "_claim") || action == "release_safe" || (semanticAuditPermissionRank(allowed) < semanticAuditPermissionRank("P2") && semanticAuditActionRequiresP2(action)) {
			blocked = append(blocked, action)
		}
	}

	evidenceLevel := request.PermissionDecision.EvidenceLevel
	if evidenceLevel == "" {
		evidenceLevel = "semantic_intake_only"
	}

	return SemanticAuditPermissionDecision{
		RequestedLevel:    requested,
		AllowedLevel:      allowed,
		EvidenceLevel:     evidenceLevel,
		RequestedActions:  request.PermissionDecision.RequestedActions,
		BlockedActions:    normalizeStrings(blocked),
		UpgradeReasons:    request.PermissionDecision.UpgradeReasons,
		DowngradeReasons:  normalizeStrings(downgradeReasons),
		VerificationOwner: request.PermissionDecision.VerificationOwner,
	}
}

func semanticAuditCapturedEvidence(values []SemanticAuditCapturedEvidence) []SemanticAuditCapturedEvidence {
	result := make([]SemanticAuditCapturedEvidence, 0, len(values))
	for _, evidence := range values {
		evidence.StepID = strings.TrimSpace(evidence.StepID)
		evidence.ReadPath = strings.TrimSpace(evidence.ReadPath)
		evidence.EvidenceNeed = strings.TrimSpace(evidence.EvidenceNeed)
		evidence.SourceKind = strings.ToLower(strings.TrimSpace(evidence.SourceKind))
		evidence.SourceRef = strings.TrimSpace(evidence.SourceRef)
		evidence.LineRefs = normalizeStrings(evidence.LineRefs)
		evidence.ObservedSignal = strings.TrimSpace(evidence.ObservedSignal)
		evidence.SupportsCandidateID = strings.TrimSpace(evidence.SupportsCandidateID)
		evidence.ContradictsCandidateID = strings.TrimSpace(evidence.ContradictsCandidateID)
		evidence.SupportsFacets = normalizeStrings(evidence.SupportsFacets)
		evidence.MissingFacets = normalizeStrings(evidence.MissingFacets)
		evidence.ContentHash = strings.TrimSpace(evidence.ContentHash)
		evidence.CapturedAt = strings.TrimSpace(evidence.CapturedAt)
		evidence.EvidenceRef = strings.TrimSpace(evidence.EvidenceRef)
		evidence.VerificationOwner = strings.TrimSpace(evidence.VerificationOwner)
		if evidence.ObservedSignal != "" || evidence.EvidenceRef != "" || evidence.ReadPath != "" || evidence.SourceRef != "" {
			result = append(result, evidence)
		}
	}
	if result == nil {
		return []SemanticAuditCapturedEvidence{}
	}
	return result
}

func semanticAuditVerificationResults(values []SemanticAuditVerificationResult) []SemanticAuditVerificationResult {
	result := make([]SemanticAuditVerificationResult, 0, len(values))
	for _, verification := range values {
		verification.CandidateID = strings.TrimSpace(verification.CandidateID)
		verification.VerificationPath = semanticAuditNormalizePath(verification.VerificationPath)
		verification.Command = strings.TrimSpace(verification.Command)
		verification.Status = strings.ToLower(strings.TrimSpace(verification.Status))
		verification.ClaimType = strings.ToLower(strings.TrimSpace(verification.ClaimType))
		verification.ClaimTypes = semanticAuditNormalizeClaimTypes(append(verification.ClaimTypes, verification.ClaimType))
		verification.EvidenceRef = strings.TrimSpace(verification.EvidenceRef)
		verification.CapturedAt = strings.TrimSpace(verification.CapturedAt)
		verification.Summary = strings.TrimSpace(verification.Summary)
		if verification.VerificationPath != "" || verification.Command != "" || verification.EvidenceRef != "" || verification.Summary != "" {
			result = append(result, verification)
		}
	}
	if result == nil {
		return []SemanticAuditVerificationResult{}
	}
	return result
}

func semanticAuditWorkflowAuthorization(value SemanticAuditWorkflowAuthorization, fallbackIntent string) SemanticAuditWorkflowAuthorization {
	value.WorkflowIntent = strings.ToLower(strings.TrimSpace(value.WorkflowIntent))
	if value.WorkflowIntent == "" {
		value.WorkflowIntent = strings.ToLower(strings.TrimSpace(fallbackIntent))
	}
	value.Status = strings.ToLower(strings.TrimSpace(value.Status))
	value.AuthorizedClaims = normalizeStrings(value.AuthorizedClaims)
	for i, claim := range value.AuthorizedClaims {
		value.AuthorizedClaims[i] = strings.ToLower(strings.TrimSpace(claim))
	}
	value.AuthorizedClaims = normalizeStrings(value.AuthorizedClaims)
	value.ActiveClaimType = strings.ToLower(strings.TrimSpace(value.ActiveClaimType))
	value.AuthorizationRef = strings.TrimSpace(value.AuthorizationRef)
	value.ClaimAuthorizations = semanticAuditClaimAuthorizations(value.ClaimAuthorizations)
	value.Reason = strings.TrimSpace(value.Reason)
	if value.Status == "" {
		value.Status = "blocked"
	}
	return value
}

func semanticAuditClaimAuthorizations(values []SemanticAuditClaimAuthorization) []SemanticAuditClaimAuthorization {
	result := make([]SemanticAuditClaimAuthorization, 0, len(values))
	for _, authorization := range values {
		authorization.ClaimType = strings.ToLower(strings.TrimSpace(authorization.ClaimType))
		authorization.Status = strings.ToLower(strings.TrimSpace(authorization.Status))
		authorization.AuthorizationRef = strings.TrimSpace(authorization.AuthorizationRef)
		authorization.VerificationEvidenceRefs = normalizeStrings(authorization.VerificationEvidenceRefs)
		authorization.Reason = strings.TrimSpace(authorization.Reason)
		if authorization.ClaimType != "" || authorization.Status != "" || authorization.AuthorizationRef != "" || len(authorization.VerificationEvidenceRefs) > 0 || authorization.Reason != "" {
			result = append(result, authorization)
		}
	}
	if result == nil {
		return []SemanticAuditClaimAuthorization{}
	}
	return result
}

func semanticAuditRerankAssessment(route SemanticAuditRouteDecision, permission SemanticAuditPermissionDecision, plan SemanticAuditInspectionPlan, evidence []SemanticAuditCapturedEvidence) SemanticAuditRerankAssessment {
	selectedID := ""
	if len(route.SelectedCandidateIDs) > 0 {
		selectedID = route.SelectedCandidateIDs[0]
	} else if len(route.SelectedCandidates) > 0 {
		selectedID = route.SelectedCandidates[0].ID
	}
	assessment := SemanticAuditRerankAssessment{
		Status:                    "evidence_missing",
		SelectedCandidateID:       selectedID,
		SupportingEvidenceRefs:    []string{},
		ContradictingEvidenceRefs: []string{},
		PermissionPromotionCandidate: SemanticAuditPermissionPromotionCandidate{
			CurrentAllowedLevel: permission.AllowedLevel,
			CandidateLevel:      permission.AllowedLevel,
			Status:              "blocked",
			Granted:             false,
			BlockedBy:           []string{"live_evidence_capture_required", "live_source_evidence_required", "bounded_source_evidence_required"},
			Reason:              "captured bounded live source evidence is required before permission can be considered beyond routing data",
		},
	}
	if selectedID == "" {
		assessment.Status = "no_selected_route"
		assessment.PermissionPromotionCandidate.CandidateLevel = "P0"
		assessment.PermissionPromotionCandidate.BlockedBy = []string{"selected_route_required"}
		return assessment
	}

	for _, item := range evidence {
		ref := semanticAuditCapturedEvidenceRef(item)
		if semanticAuditCapturedEvidenceCanRerank(item, route, plan) && item.ContradictsCandidateID == selectedID && item.ContradictsCandidate {
			assessment.ContradictingEvidenceRefs = append(assessment.ContradictingEvidenceRefs, ref)
			continue
		}
		if semanticAuditCapturedEvidenceCanRerank(item, route, plan) && item.SupportsCandidateID == selectedID && item.SupportsCandidate {
			assessment.SupportingEvidenceRefs = append(assessment.SupportingEvidenceRefs, ref)
		}
	}
	assessment.SupportingEvidenceRefs = normalizeStrings(assessment.SupportingEvidenceRefs)
	assessment.ContradictingEvidenceRefs = normalizeStrings(assessment.ContradictingEvidenceRefs)

	if len(assessment.ContradictingEvidenceRefs) > 0 {
		assessment.Status = "route_contradicted"
		assessment.PermissionPromotionCandidate = SemanticAuditPermissionPromotionCandidate{
			CurrentAllowedLevel: permission.AllowedLevel,
			CandidateLevel:      "P1",
			Status:              "blocked",
			Granted:             false,
			BlockedBy:           []string{"live_evidence_contradicts_candidate", "rerun_semantic_intake"},
			Reason:              "captured live evidence contradicts the selected route",
		}
		return assessment
	}
	if len(assessment.SupportingEvidenceRefs) > 0 {
		assessment.Status = "route_supported"
		assessment.PermissionPromotionCandidate = SemanticAuditPermissionPromotionCandidate{
			CurrentAllowedLevel: permission.AllowedLevel,
			CandidateLevel:      "P3",
			Status:              "candidate_only",
			Granted:             false,
			BlockedBy:           []string{"verification_owner_discovery", "workflow_authorization", "verification_result_required"},
			Reason:              "live evidence supports the route, but v1.2 records only a candidate for later permission promotion",
		}
	}
	return assessment
}

func semanticAuditCapturedEvidenceCanRerank(evidence SemanticAuditCapturedEvidence, route SemanticAuditRouteDecision, plan SemanticAuditInspectionPlan) bool {
	return evidence.SourceKind == "source" &&
		evidence.ReadPath != "" &&
		semanticAuditPathAllowedForRerank(evidence.ReadPath, route, plan)
}

func semanticAuditCapturedEvidenceRef(evidence SemanticAuditCapturedEvidence) string {
	if evidence.EvidenceRef != "" {
		return evidence.EvidenceRef
	}
	if evidence.SourceRef != "" {
		return evidence.SourceRef
	}
	if evidence.ReadPath != "" {
		return evidence.ReadPath
	}
	return evidence.ObservedSignal
}

func semanticAuditPathAllowedForRerank(path string, route SemanticAuditRouteDecision, plan SemanticAuditInspectionPlan) bool {
	normalizedPath := semanticAuditNormalizePath(path)
	if normalizedPath == "" {
		return false
	}
	for _, allowedPath := range semanticAuditAllowedRerankSourcePaths(route, plan) {
		if normalizedPath == semanticAuditNormalizePath(allowedPath) {
			return true
		}
	}
	return false
}

func semanticAuditAllowedRerankSourcePaths(route SemanticAuditRouteDecision, plan SemanticAuditInspectionPlan) []string {
	paths := []string{}
	for _, step := range plan.Steps {
		if step.TargetPath != "" {
			paths = append(paths, step.TargetPath)
		}
	}
	for _, candidate := range route.SelectedCandidates {
		paths = append(paths, candidate.OwnerHints.PrimaryPaths...)
		paths = append(paths, candidate.OwnerHints.SupportingPaths...)
		paths = append(paths, candidate.OwnerHints.TruthPaths...)
		paths = append(paths, candidate.OwnerHints.VerificationPaths...)
	}
	return normalizePaths(paths)
}

func semanticAuditNormalizePath(path string) string {
	paths := normalizePaths([]string{path})
	if len(paths) == 0 {
		return ""
	}
	return paths[0]
}

func semanticAuditApplyRerankPermission(permission SemanticAuditPermissionDecision, assessment SemanticAuditRerankAssessment) SemanticAuditPermissionDecision {
	if assessment.Status != "route_contradicted" {
		return permission
	}
	if semanticAuditPermissionRank(permission.AllowedLevel) > semanticAuditPermissionRank("P1") {
		permission.AllowedLevel = "P1"
	}
	permission.EvidenceLevel = "live_evidence_contradicts_route"
	permission.DowngradeReasons = normalizeStrings(append(permission.DowngradeReasons, "live_evidence_contradicts_selected_candidate"))
	permission.BlockedActions = normalizeStrings(append(permission.BlockedActions,
		"targeted_inspect",
		"change",
		"root_cause_claim",
		"fixed_claim",
		"completed_claim",
		"release_safe",
	))
	return permission
}

func semanticAuditOwnerBundleConfidence(route SemanticAuditRouteDecision) SemanticAuditOwnerBundleConfidence {
	candidates := make([]SemanticAuditOwnerBundleCandidate, 0, len(route.SelectedCandidates))
	summary := "owner_bundle_missing"
	for _, candidate := range route.SelectedCandidates {
		owner := SemanticAuditOwnerBundleCandidate{
			CandidateID:       candidate.ID,
			PrimaryPaths:      normalizePaths(candidate.OwnerHints.PrimaryPaths),
			SupportingPaths:   normalizePaths(candidate.OwnerHints.SupportingPaths),
			TruthPaths:        normalizePaths(candidate.OwnerHints.TruthPaths),
			VerificationPaths: normalizePaths(candidate.OwnerHints.VerificationPaths),
			ConfidenceReasons: []string{},
			CoveredOwnerRoles: []string{},
			MissingOwnerRoles: []string{},
		}
		if len(owner.PrimaryPaths) > 0 {
			owner.CoveredOwnerRoles = append(owner.CoveredOwnerRoles, "primary")
			owner.ConfidenceReasons = append(owner.ConfidenceReasons, "primary owner path is indexed")
		} else {
			owner.MissingOwnerRoles = append(owner.MissingOwnerRoles, "primary")
		}
		if len(owner.SupportingPaths) > 0 {
			owner.CoveredOwnerRoles = append(owner.CoveredOwnerRoles, "supporting")
			owner.ConfidenceReasons = append(owner.ConfidenceReasons, "supporting owner path is indexed")
		} else {
			owner.MissingOwnerRoles = append(owner.MissingOwnerRoles, "supporting")
		}
		if len(owner.TruthPaths) > 0 {
			owner.CoveredOwnerRoles = append(owner.CoveredOwnerRoles, "truth")
			owner.ConfidenceReasons = append(owner.ConfidenceReasons, "truth owner path is indexed")
		} else {
			owner.MissingOwnerRoles = append(owner.MissingOwnerRoles, "truth")
		}
		if len(owner.VerificationPaths) > 0 {
			owner.CoveredOwnerRoles = append(owner.CoveredOwnerRoles, "verification")
			owner.ConfidenceReasons = append(owner.ConfidenceReasons, "verification owner path is indexed")
		} else {
			owner.MissingOwnerRoles = append(owner.MissingOwnerRoles, "verification")
		}
		switch len(owner.CoveredOwnerRoles) {
		case 4:
			owner.Confidence = "high"
		case 2, 3:
			owner.Confidence = "medium"
		default:
			owner.Confidence = "low"
			if len(owner.ConfidenceReasons) == 0 {
				owner.ConfidenceReasons = append(owner.ConfidenceReasons, "no concrete owner paths indexed")
			}
		}
		owner.ConfidenceReasons = normalizeStrings(owner.ConfidenceReasons)
		owner.CoveredOwnerRoles = normalizeStrings(owner.CoveredOwnerRoles)
		owner.MissingOwnerRoles = normalizeStrings(owner.MissingOwnerRoles)
		candidates = append(candidates, owner)
		if summary == "owner_bundle_missing" || semanticAuditOwnerConfidenceRank(owner.Confidence) < semanticAuditOwnerConfidenceRank(summary) {
			summary = "owner_bundle_" + owner.Confidence
		}
	}
	if candidates == nil {
		candidates = []SemanticAuditOwnerBundleCandidate{}
	}
	if len(candidates) == 0 {
		summary = "owner_bundle_missing"
	}
	return SemanticAuditOwnerBundleConfidence{
		Summary:    summary,
		Candidates: candidates,
	}
}

func semanticAuditOwnerConfidenceRank(value string) int {
	switch strings.TrimPrefix(strings.ToLower(strings.TrimSpace(value)), "owner_bundle_") {
	case "high":
		return 3
	case "medium":
		return 2
	case "low":
		return 1
	default:
		return 0
	}
}

func semanticAuditOwnerMissExpansion(request SemanticAuditRequest, plan SemanticAuditInspectionPlan) SemanticAuditOwnerMissExpansion {
	targets := []string{}
	for _, step := range plan.Steps {
		if step.AllowedAction == "resolve_owner_before_source_read" && step.TargetID != "" {
			targets = append(targets, step.TargetID)
		}
	}
	for _, target := range request.SemanticIntakeOutput.ExpansionTargets {
		targets = append(targets, target.ID)
	}
	targets = normalizeStrings(targets)
	expansion := SemanticAuditOwnerMissExpansion{
		MaxRadius:        1,
		AllowedTargetIDs: targets,
		OnMiss:           "stop_and_request_map_update_or_user_clarification",
		BlockedActions:   []string{"inspect_broadly", "change", "root_cause_claim", "fixed_claim", "completed_claim", "release_safe"},
	}
	if len(targets) == 0 {
		expansion.BlockedReason = "no bounded expansion target is available"
	}
	return expansion
}

func semanticAuditVerificationOwnerDiscovery(route SemanticAuditRouteDecision) SemanticAuditVerificationOwnerDiscovery {
	owners := make([]SemanticAuditVerificationOwnerCandidate, 0, len(route.SelectedCandidates))
	missing := false
	indexed := false
	for _, candidate := range route.SelectedCandidates {
		paths := normalizePaths(candidate.OwnerHints.VerificationPaths)
		owner := SemanticAuditVerificationOwnerCandidate{
			CandidateID:                   candidate.ID,
			Status:                        "owner_missing",
			VerificationPaths:             []string{},
			VerificationCommandCandidates: []string{},
			RequiredSignals:               []string{"positive verification covers selected behavior", "regression verification covers rejected or contrast false friends"},
			RequiredAction:                "identify positive and regression verification owner",
			BlockedBy:                     []string{"verification_owner_missing", "verification_result_required"},
		}
		if len(paths) > 0 {
			owner.Status = "owner_indexed"
			owner.VerificationPaths = paths
			owner.VerificationCommandCandidates = semanticAuditVerificationCommandCandidates(paths)
			owner.RequiredAction = "run targeted verification and capture result before claim promotion"
			owner.BlockedBy = []string{"verification_result_required", "workflow_authorization"}
			indexed = true
		} else {
			missing = true
		}
		owners = append(owners, owner)
	}
	if len(owners) == 0 {
		missing = true
	}
	summary := "verification_owner_missing"
	reason := "verification owner is required before P3/P4 claims"
	if indexed && !missing {
		summary = "verification_owner_indexed"
		reason = "verification owner path is indexed, but verification results are still required before claim promotion"
	} else if indexed && missing {
		summary = "verification_owner_partial"
		reason = "some selected candidates have verification owners, but at least one selected route still lacks verification ownership"
	}
	if owners == nil {
		owners = []SemanticAuditVerificationOwnerCandidate{}
	}
	return SemanticAuditVerificationOwnerDiscovery{
		Summary:          summary,
		RequiredOwners:   owners,
		BlockedClaims:    []string{"root_cause_claim", "fixed_claim", "completed_claim", "release_safe"},
		PromotionBlocked: true,
		Reason:           reason,
	}
}

func semanticAuditVerificationCommandCandidates(paths []string) []string {
	candidates := make([]string, 0, len(paths))
	for _, path := range normalizePaths(paths) {
		candidates = append(candidates, "targeted_test:"+path)
	}
	if candidates == nil {
		return []string{}
	}
	return candidates
}

func semanticAuditClaimReadiness(plan SemanticAuditInspectionPlan, route SemanticAuditRouteDecision, rerank SemanticAuditRerankAssessment, discovery SemanticAuditVerificationOwnerDiscovery, evidence []SemanticAuditCapturedEvidence, results []SemanticAuditVerificationResult, authorization SemanticAuditWorkflowAuthorization) SemanticAuditClaimReadiness {
	readiness := SemanticAuditClaimReadiness{
		InspectStatus:         plan.Readiness,
		InspectReady:          plan.Readiness == "inspect_ready",
		ChangeStatus:          "change_blocked",
		ChangeReady:           false,
		ClaimStatus:           "claim_blocked",
		ClaimReady:            false,
		VerificationSatisfied: false,
		PromotionBlocked:      true,
		BlockedBy:             []string{},
		EvidenceTrail:         []string{},
		Reason:                "claim promotion requires bounded live evidence, matching verification result, and workflow authorization",
	}
	readiness.EvidenceTrail = append(readiness.EvidenceTrail, rerank.SupportingEvidenceRefs...)

	if rerank.Status != "route_supported" {
		readiness.BlockedBy = append(readiness.BlockedBy, "bounded_live_evidence_required")
		if rerank.Status == "route_contradicted" {
			readiness.BlockedBy = append(readiness.BlockedBy, "route_contradicted")
		}
		return semanticAuditNormalizeClaimReadiness(readiness)
	}
	if !semanticAuditVerificationOwnersFullyIndexed(discovery) {
		readiness.BlockedBy = append(readiness.BlockedBy, "verification_owner_missing")
		return semanticAuditNormalizeClaimReadiness(readiness)
	}

	matches, verificationBlocker, verificationSatisfied := semanticAuditPassedVerificationResultsForAllOwners(discovery, results)
	if !verificationSatisfied {
		readiness.BlockedBy = append(readiness.BlockedBy, verificationBlocker)
		return semanticAuditNormalizeClaimReadiness(readiness)
	}
	for _, match := range matches {
		readiness.EvidenceTrail = append(readiness.EvidenceTrail, semanticAuditVerificationResultRef(match))
	}

	readiness.VerificationSatisfied = true
	readiness.ClaimStatus = "claim_candidate"
	readiness.Reason = "bounded live evidence and matching verification results are present, but workflow authorization is still required before final claims"

	evidenceRefs, evidenceBlocker, evidenceSatisfied := semanticAuditBoundedLiveEvidenceForAllSelectedCandidates(route, plan, evidence)
	readiness.EvidenceTrail = append(readiness.EvidenceTrail, evidenceRefs...)
	if !evidenceSatisfied {
		readiness.BlockedBy = append(readiness.BlockedBy, evidenceBlocker)
		readiness.Reason = "bounded live source evidence is required for every selected candidate before final claims"
		return semanticAuditNormalizeClaimReadiness(readiness)
	}

	if authorization.Status != "authorized" || len(authorization.AuthorizedClaims) == 0 {
		readiness.BlockedBy = append(readiness.BlockedBy, "workflow_authorization")
		return semanticAuditNormalizeClaimReadiness(readiness)
	}
	claimType, claimTypeBlocker, claimTypeSelected := semanticAuditAuthorizedClaimType(authorization)
	readiness.ClaimType = claimType
	if !claimTypeSelected {
		readiness.BlockedBy = append(readiness.BlockedBy, claimTypeBlocker)
		readiness.Reason = "bounded evidence and verification are present, but workflow authorization must select exactly one active claim"
		return semanticAuditNormalizeClaimReadiness(readiness)
	}
	if !semanticAuditClaimTypeSupported(claimType) {
		readiness.BlockedBy = append(readiness.BlockedBy, "claim_type_not_supported")
		readiness.Reason = "bounded evidence and verification are present, but the requested claim type is not supported"
		return semanticAuditNormalizeClaimReadiness(readiness)
	}
	claimMatches, claimVerificationSatisfied := semanticAuditClaimSpecificVerificationResultsForAllOwners(discovery, results, claimType)
	if !claimVerificationSatisfied {
		readiness.BlockedBy = append(readiness.BlockedBy, "claim_specific_verification_required")
		readiness.Reason = "bounded evidence and generic verification are present, but stronger claims require claim-specific passed verification results"
		return semanticAuditNormalizeClaimReadiness(readiness)
	}
	claimAuthorization, claimAuthorizationBlocker, claimAuthorizationSatisfied := semanticAuditClaimAuthorizationForClaim(authorization, claimType, claimMatches)
	if !claimAuthorizationSatisfied {
		readiness.BlockedBy = append(readiness.BlockedBy, claimAuthorizationBlocker)
		readiness.Reason = "bounded evidence and claim-specific verification are present, but workflow claim authorization is missing or incomplete"
		return semanticAuditNormalizeClaimReadiness(readiness)
	}
	for _, match := range claimMatches {
		readiness.EvidenceTrail = append(readiness.EvidenceTrail, semanticAuditVerificationResultRef(match))
	}
	readiness.ClaimVerificationRefs = semanticAuditVerificationResultRefs(claimMatches)
	readiness.ClaimStatus = "claim_ready"
	readiness.ClaimReady = true
	readiness.PromotionBlocked = false
	readiness.EvidenceTrail = append(readiness.EvidenceTrail, claimAuthorization.AuthorizationRef)
	readiness.Reason = "bounded live evidence, claim-specific verification results, and explicit workflow authorization support the requested claim"
	return semanticAuditNormalizeClaimReadiness(readiness)
}

func semanticAuditBoundedLiveEvidenceForAllSelectedCandidates(route SemanticAuditRouteDecision, plan SemanticAuditInspectionPlan, evidence []SemanticAuditCapturedEvidence) ([]string, string, bool) {
	selectedIDs := semanticAuditSelectedCandidateIDs(route)
	if len(selectedIDs) == 0 {
		return nil, "bounded_live_evidence_required", false
	}
	supported := map[string]bool{}
	refs := []string{}
	for _, item := range evidence {
		if !semanticAuditCapturedEvidenceCanRerank(item, route, plan) {
			continue
		}
		for _, id := range selectedIDs {
			if item.ContradictsCandidateID == id && item.ContradictsCandidate {
				return refs, "route_contradicted", false
			}
			if item.SupportsCandidateID == id && item.SupportsCandidate {
				supported[id] = true
				refs = append(refs, semanticAuditCapturedEvidenceRef(item))
			}
		}
	}
	for _, id := range selectedIDs {
		if !supported[id] {
			return refs, "bounded_live_evidence_required", false
		}
	}
	return normalizeStrings(refs), "", true
}

func semanticAuditSelectedCandidateIDs(route SemanticAuditRouteDecision) []string {
	ids := []string{}
	seen := map[string]bool{}
	add := func(id string) {
		id = strings.TrimSpace(id)
		if id == "" || seen[id] {
			return
		}
		seen[id] = true
		ids = append(ids, id)
	}
	for _, id := range route.SelectedCandidateIDs {
		add(id)
	}
	for _, candidate := range route.SelectedCandidates {
		add(candidate.ID)
	}
	return ids
}

func semanticAuditClaimSpecificVerificationResultsForAllOwners(discovery SemanticAuditVerificationOwnerDiscovery, results []SemanticAuditVerificationResult, claimType string) ([]SemanticAuditVerificationResult, bool) {
	if claimType == "root_cause_claim" {
		matches := []SemanticAuditVerificationResult{}
		for _, owner := range discovery.RequiredOwners {
			matched := false
			for _, result := range results {
				if result.Status != "passed" || !semanticAuditVerificationResultMatchesOwner(owner, result) {
					continue
				}
				if len(result.ClaimTypes) > 0 && !semanticAuditHasString(result.ClaimTypes, claimType) {
					continue
				}
				matches = append(matches, result)
				matched = true
				break
			}
			if !matched {
				return matches, false
			}
		}
		return matches, true
	}
	matches := []SemanticAuditVerificationResult{}
	for _, owner := range discovery.RequiredOwners {
		matched := false
		for _, result := range results {
			if result.Status != "passed" || !semanticAuditVerificationResultMatchesOwner(owner, result) {
				continue
			}
			if !semanticAuditHasString(result.ClaimTypes, claimType) {
				continue
			}
			matches = append(matches, result)
			matched = true
			break
		}
		if !matched {
			return matches, false
		}
	}
	return matches, true
}

func semanticAuditClaimAuthorizationForClaim(authorization SemanticAuditWorkflowAuthorization, claimType string, verificationMatches []SemanticAuditVerificationResult) (SemanticAuditClaimAuthorization, string, bool) {
	if claimType == "root_cause_claim" {
		for _, claimAuthorization := range authorization.ClaimAuthorizations {
			if claimAuthorization.ClaimType != claimType || claimAuthorization.Status != "authorized" {
				continue
			}
			if claimAuthorization.AuthorizationRef == "" {
				return claimAuthorization, "claim_authorization_ref_required", false
			}
			if !semanticAuditClaimAuthorizationReferencesVerification(claimAuthorization, verificationMatches) {
				return claimAuthorization, "claim_authorization_verification_ref_required", false
			}
			return claimAuthorization, "", true
		}
		if authorization.AuthorizationRef == "" {
			return SemanticAuditClaimAuthorization{ClaimType: claimType, Status: authorization.Status}, "workflow_authorization_ref_required", false
		}
		return SemanticAuditClaimAuthorization{
			ClaimType:                claimType,
			Status:                   authorization.Status,
			AuthorizationRef:         authorization.AuthorizationRef,
			VerificationEvidenceRefs: semanticAuditVerificationResultRefs(verificationMatches),
			Reason:                   authorization.Reason,
		}, "", true
	}
	for _, claimAuthorization := range authorization.ClaimAuthorizations {
		if claimAuthorization.ClaimType != claimType {
			continue
		}
		if claimAuthorization.Status != "authorized" {
			return claimAuthorization, "claim_authorization_required", false
		}
		if claimAuthorization.AuthorizationRef == "" {
			return claimAuthorization, "claim_authorization_ref_required", false
		}
		if !semanticAuditClaimAuthorizationReferencesVerification(claimAuthorization, verificationMatches) {
			return claimAuthorization, "claim_authorization_verification_ref_required", false
		}
		return claimAuthorization, "", true
	}
	return SemanticAuditClaimAuthorization{}, "claim_authorization_required", false
}

func semanticAuditClaimAuthorizationReferencesVerification(claimAuthorization SemanticAuditClaimAuthorization, verificationMatches []SemanticAuditVerificationResult) bool {
	if len(claimAuthorization.VerificationEvidenceRefs) == 0 {
		return false
	}
	for _, match := range verificationMatches {
		if !semanticAuditHasString(claimAuthorization.VerificationEvidenceRefs, semanticAuditVerificationResultRef(match)) {
			return false
		}
	}
	return true
}

func semanticAuditVerificationResultRefs(results []SemanticAuditVerificationResult) []string {
	refs := make([]string, 0, len(results))
	for _, result := range results {
		refs = append(refs, semanticAuditVerificationResultRef(result))
	}
	return normalizeStrings(refs)
}

func semanticAuditVerificationOwnersFullyIndexed(discovery SemanticAuditVerificationOwnerDiscovery) bool {
	if len(discovery.RequiredOwners) == 0 {
		return false
	}
	for _, owner := range discovery.RequiredOwners {
		if owner.Status != "owner_indexed" || len(owner.VerificationPaths) == 0 {
			return false
		}
	}
	return true
}

func semanticAuditPassedVerificationResultsForAllOwners(discovery SemanticAuditVerificationOwnerDiscovery, results []SemanticAuditVerificationResult) ([]SemanticAuditVerificationResult, string, bool) {
	if len(results) == 0 {
		return nil, "verification_result_required", false
	}
	passedResults := []SemanticAuditVerificationResult{}
	ownerMatchCount := 0
	ownerPassCount := 0
	latestBlockingResult := ""
	for _, owner := range discovery.RequiredOwners {
		result, matched := semanticAuditLatestVerificationResultForOwner(owner, results)
		if !matched {
			continue
		}
		ownerMatchCount++
		if result.Status == "passed" {
			passedResults = append(passedResults, result)
			ownerPassCount++
			continue
		}
		if latestBlockingResult == "" {
			latestBlockingResult = semanticAuditVerificationResultStatusBlocker(result.Status)
		}
	}
	if ownerMatchCount == 0 {
		return passedResults, "verification_owner_match_required", false
	}
	if ownerMatchCount < len(discovery.RequiredOwners) {
		return passedResults, "verification_result_required", false
	}
	if ownerPassCount < len(discovery.RequiredOwners) {
		if latestBlockingResult != "" {
			return passedResults, latestBlockingResult, false
		}
		return passedResults, "verification_result_pass_required", false
	}
	return passedResults, "", true
}

func semanticAuditLatestVerificationResultForOwner(owner SemanticAuditVerificationOwnerCandidate, results []SemanticAuditVerificationResult) (SemanticAuditVerificationResult, bool) {
	var latest SemanticAuditVerificationResult
	latestIndex := -1
	for index, result := range results {
		if !semanticAuditVerificationResultMatchesOwner(owner, result) {
			continue
		}
		if latestIndex == -1 || semanticAuditVerificationResultNewer(result, latest, index, latestIndex) {
			latest = result
			latestIndex = index
		}
	}
	return latest, latestIndex != -1
}

func semanticAuditVerificationResultNewer(current SemanticAuditVerificationResult, previous SemanticAuditVerificationResult, currentIndex int, previousIndex int) bool {
	if current.CapturedAt != "" && previous.CapturedAt != "" && current.CapturedAt != previous.CapturedAt {
		return current.CapturedAt > previous.CapturedAt
	}
	return currentIndex > previousIndex
}

func semanticAuditVerificationResultStatusBlocker(status string) string {
	switch status {
	case "failed":
		return "verification_result_failed"
	case "blocked":
		return "verification_result_blocked"
	case "passed":
		return ""
	default:
		return "verification_result_inconclusive"
	}
}

func semanticAuditVerificationResultMatchesDiscovery(discovery SemanticAuditVerificationOwnerDiscovery, result SemanticAuditVerificationResult) bool {
	for _, owner := range discovery.RequiredOwners {
		if semanticAuditVerificationResultMatchesOwner(owner, result) {
			return true
		}
	}
	return false
}

func semanticAuditVerificationResultMatchesOwner(owner SemanticAuditVerificationOwnerCandidate, result SemanticAuditVerificationResult) bool {
	resultPath := semanticAuditNormalizePath(result.VerificationPath)
	if resultPath == "" {
		return false
	}
	if result.CandidateID != "" && owner.CandidateID != "" && result.CandidateID != owner.CandidateID {
		return false
	}
	for _, path := range owner.VerificationPaths {
		if resultPath == semanticAuditNormalizePath(path) {
			return true
		}
	}
	return false
}

func semanticAuditAuthorizedClaimType(authorization SemanticAuditWorkflowAuthorization) (string, string, bool) {
	if authorization.ActiveClaimType != "" {
		if !semanticAuditHasString(authorization.AuthorizedClaims, authorization.ActiveClaimType) {
			return authorization.ActiveClaimType, "active_claim_not_authorized", false
		}
		return authorization.ActiveClaimType, "", true
	}
	if len(authorization.AuthorizedClaims) == 1 {
		return authorization.AuthorizedClaims[0], "", true
	}
	if len(authorization.AuthorizedClaims) > 1 {
		return "", "active_claim_type_required", false
	}
	return "", "workflow_authorization", false
}

func semanticAuditClaimTypeSupported(claimType string) bool {
	switch claimType {
	case "root_cause_claim", "fixed_claim", "completed_claim", "release_safe":
		return true
	default:
		return false
	}
}

func semanticAuditNormalizeClaimTypes(claimTypes []string) []string {
	result := normalizeStrings(claimTypes)
	for i, claimType := range result {
		result[i] = strings.ToLower(strings.TrimSpace(claimType))
	}
	result = normalizeStrings(result)
	if result == nil {
		return []string{}
	}
	return result
}

func semanticAuditHasString(values []string, target string) bool {
	for _, value := range values {
		if value == target {
			return true
		}
	}
	return false
}

func semanticAuditVerificationResultRef(result SemanticAuditVerificationResult) string {
	if result.EvidenceRef != "" {
		return result.EvidenceRef
	}
	if result.Command != "" {
		return result.Command
	}
	if result.VerificationPath != "" {
		return result.VerificationPath
	}
	return result.Summary
}

func semanticAuditNormalizeClaimReadiness(readiness SemanticAuditClaimReadiness) SemanticAuditClaimReadiness {
	readiness.BlockedBy = normalizeStrings(readiness.BlockedBy)
	readiness.ClaimVerificationRefs = normalizeStrings(readiness.ClaimVerificationRefs)
	readiness.EvidenceTrail = normalizeStrings(readiness.EvidenceTrail)
	if readiness.InspectStatus == "" {
		readiness.InspectStatus = "inspect_blocked"
	}
	if readiness.ChangeStatus == "" {
		readiness.ChangeStatus = "change_blocked"
	}
	if readiness.ClaimStatus == "" {
		readiness.ClaimStatus = "claim_blocked"
	}
	return readiness
}

func semanticAuditInspectionPlan(request SemanticAuditRequest, route SemanticAuditRouteDecision, permission SemanticAuditPermissionDecision) SemanticAuditInspectionPlan {
	maxPermission := strings.ToUpper(strings.TrimSpace(permission.AllowedLevel))
	if maxPermission == "" {
		maxPermission = "P0"
	}
	if semanticAuditPermissionRank(maxPermission) > semanticAuditPermissionRank("P2") {
		maxPermission = "P2"
	}

	plan := SemanticAuditInspectionPlan{
		Readiness:     "inspect_blocked",
		MaxPermission: maxPermission,
		Steps:         []SemanticAuditInspectionStep{},
		LiveEvidenceCapture: SemanticAuditLiveEvidenceCapture{
			RequiredFields: []string{
				"source_kind",
				"read_path",
				"evidence_need",
				"observed_signal",
				"supports_candidate",
				"contradicts_candidate",
				"evidence_ref",
			},
			Boundary: "Agent records live evidence after bounded reads; only source_kind=source with a bounded read_path can support rerank. semantic-audit does not read source, run tests, edit files, or authorize final claims.",
		},
		RerankAfterInspect: SemanticAuditRerankAfterInspect{
			RequiredWhen: []string{
				"live_evidence_contradicts_selected_candidate",
				"required_facet_remains_missing",
				"selected_owner_path_missing",
			},
			Inputs: []string{
				"inspection_plan.steps",
				"live_evidence_capture",
				"semantic_intake_snapshot",
			},
			BlockedClaimsUntilRerank: []string{
				"root_cause_claim",
				"fixed_claim",
				"completed_claim",
				"release_safe",
			},
			PermissionPromotionBlocked: true,
		},
		StaleIndexDowngrade: SemanticAuditStaleIndexDowngrade{
			Conditions: []string{
				"runtime_unavailable",
				"stale_index",
				"selected_owner_missing",
				"live_evidence_contradicts_candidate",
			},
			DowngradeTo: "P1",
			Reason:      "live evidence or runtime freshness must win over indexed routing",
		},
		BlockedActions: normalizeStrings(append([]string{
			"change",
			"root_cause_claim",
			"fixed_claim",
			"completed_claim",
			"release_safe",
		}, permission.BlockedActions...)),
	}
	if semanticAuditPermissionRank(maxPermission) < semanticAuditPermissionRank("P2") {
		if maxPermission == "P0" {
			plan.StaleIndexDowngrade.DowngradeTo = "P0"
		}
		return plan
	}
	if request.SemanticIntakeOutput.Readiness != semanticIntakeReadinessQueryReady {
		return plan
	}
	if len(route.SelectedCandidates) == 0 {
		return plan
	}

	needs := semanticAuditInspectionNeeds(request, route)
	if len(needs) == 0 {
		needs = []semanticAuditInspectionNeed{{
			evidenceNeed:    "verify selected route with live evidence",
			suggestedAction: "perform a bounded read of the selected owner before making route claims",
		}}
	}

	limited := false
	ready := false
	for _, need := range needs {
		candidate := semanticAuditInspectionCandidate(route.SelectedCandidates, need.ownerRef)
		step := SemanticAuditInspectionStep{
			ID:              fmt.Sprintf("inspect-%02d", len(plan.Steps)+1),
			CandidateID:     candidate.ID,
			EvidenceNeed:    need.evidenceNeed,
			SuggestedAction: need.suggestedAction,
			OnContradiction: "downgrade_route_and_rerun_semantic_intake",
			ExpectedSignal:  semanticAuditExpectedInspectionSignal(need.evidenceNeed),
		}
		targetPath := semanticAuditInspectionTargetPath(candidate, need.evidenceNeed)
		if targetPath != "" {
			step.TargetPath = targetPath
			step.AllowedAction = "targeted_read"
			step.PermissionLevel = "P2"
			ready = true
		} else {
			step.TargetID = semanticAuditInspectionTargetID(request, candidate, need.evidenceNeed)
			step.AllowedAction = "resolve_owner_before_source_read"
			step.PermissionLevel = "P1"
			limited = true
		}
		plan.Steps = append(plan.Steps, step)
	}
	switch {
	case ready && !limited:
		plan.Readiness = "inspect_ready"
	case len(plan.Steps) > 0:
		plan.Readiness = "inspect_limited"
	default:
		plan.Readiness = "inspect_blocked"
	}
	return plan
}

func semanticAuditInspectionNeeds(request SemanticAuditRequest, route SemanticAuditRouteDecision) []semanticAuditInspectionNeed {
	needs := []semanticAuditInspectionNeed{}
	indexByNeed := map[string]int{}
	add := func(need semanticAuditInspectionNeed) {
		need.evidenceNeed = strings.TrimSpace(need.evidenceNeed)
		need.suggestedAction = strings.TrimSpace(need.suggestedAction)
		need.ownerRef = strings.TrimSpace(need.ownerRef)
		if need.evidenceNeed == "" {
			return
		}
		key := strings.ToLower(need.evidenceNeed)
		if existing, ok := indexByNeed[key]; ok {
			if needs[existing].suggestedAction == "" {
				needs[existing].suggestedAction = need.suggestedAction
			}
			if needs[existing].ownerRef == "" {
				needs[existing].ownerRef = need.ownerRef
			}
			return
		}
		indexByNeed[key] = len(needs)
		needs = append(needs, need)
	}
	for _, step := range request.WorkContract.EvidencePlan {
		add(semanticAuditInspectionNeed{
			evidenceNeed:    step.EvidenceNeed,
			suggestedAction: step.SuggestedAction,
			ownerRef:        step.OwnerRef,
		})
	}
	for _, missing := range request.SemanticIntakeOutput.MissingEvidence {
		add(semanticAuditInspectionNeed{
			evidenceNeed:    missing.Facet,
			suggestedAction: missing.SuggestedAction,
		})
	}
	for _, candidate := range route.SelectedCandidates {
		for _, missing := range candidate.FacetCoverage.Missing {
			add(semanticAuditInspectionNeed{
				evidenceNeed:    missing,
				suggestedAction: semanticAuditSuggestedInspectionAction(missing),
				ownerRef:        candidate.ID,
			})
		}
	}
	return needs
}

func semanticAuditInspectionCandidate(candidates []SemanticIntakeCandidate, ownerRef string) SemanticIntakeCandidate {
	ownerRef = strings.TrimSpace(ownerRef)
	if ownerRef != "" {
		for _, candidate := range candidates {
			if candidate.ID == ownerRef {
				return candidate
			}
		}
	}
	return candidates[0]
}

func semanticAuditInspectionTargetPath(candidate SemanticIntakeCandidate, evidenceNeed string) string {
	lower := strings.ToLower(strings.TrimSpace(evidenceNeed))
	if strings.Contains(lower, "verification") || strings.Contains(lower, "regression") || strings.Contains(lower, "test") {
		if path := firstString(candidate.OwnerHints.VerificationPaths); path != "" {
			return path
		}
	}
	if strings.Contains(lower, "truth") || strings.Contains(lower, "root cause") {
		if path := firstString(candidate.OwnerHints.TruthPaths); path != "" {
			return path
		}
	}
	for _, values := range [][]string{
		candidate.OwnerHints.PrimaryPaths,
		candidate.OwnerHints.SupportingPaths,
		candidate.OwnerHints.TruthPaths,
		candidate.OwnerHints.VerificationPaths,
	} {
		if path := firstString(values); path != "" {
			return path
		}
	}
	return ""
}

func semanticAuditInspectionTargetID(request SemanticAuditRequest, candidate SemanticIntakeCandidate, evidenceNeed string) string {
	need := strings.ToLower(strings.TrimSpace(evidenceNeed))
	for _, target := range request.SemanticIntakeOutput.ExpansionTargets {
		if strings.HasPrefix(target.ID, candidate.ID) {
			if strings.Contains(need, "verification") && strings.Contains(strings.ToLower(target.Purpose+" "+target.SurfaceType), "verification") {
				return target.ID
			}
			if strings.Contains(need, "adapter") && strings.Contains(strings.ToLower(target.Purpose+" "+target.SurfaceType), "adapter") {
				return target.ID
			}
			if strings.Contains(need, "route") && strings.Contains(strings.ToLower(target.Purpose+" "+target.SurfaceType), "route") {
				return target.ID
			}
		}
	}
	if candidate.ID != "" {
		return candidate.ID
	}
	return "unresolved_owner"
}

func semanticAuditSuggestedInspectionAction(evidenceNeed string) string {
	lower := strings.ToLower(strings.TrimSpace(evidenceNeed))
	switch {
	case strings.Contains(lower, "verification"):
		return "identify positive and regression verification owner"
	case strings.Contains(lower, "exception"):
		return "inspect primary owner and runtime stack"
	default:
		return "collect bounded live evidence for the missing facet"
	}
}

func semanticAuditExpectedInspectionSignal(evidenceNeed string) string {
	lower := strings.ToLower(strings.TrimSpace(evidenceNeed))
	switch {
	case strings.Contains(lower, "verification"):
		return "positive and regression verification path exists"
	case strings.Contains(lower, "exception"):
		return "runtime stack or failing behavior maps to the selected owner"
	case strings.Contains(lower, "client") || strings.Contains(lower, "web") || strings.Contains(lower, "h5"):
		return "client/web boundary evidence explains the behavior split"
	default:
		return "live evidence covers the missing facet without contradicting the selected route"
	}
}

func firstString(values []string) string {
	for _, value := range values {
		value = strings.TrimSpace(value)
		if value != "" {
			return value
		}
	}
	return ""
}

func semanticAuditPermissionRank(level string) int {
	switch strings.ToUpper(strings.TrimSpace(level)) {
	case "P4":
		return 4
	case "P3":
		return 3
	case "P2":
		return 2
	case "P1":
		return 1
	default:
		return 0
	}
}

func semanticAuditActionRequiresP2(action string) bool {
	action = strings.TrimSpace(action)
	if action == "" {
		return false
	}
	return action == "targeted_inspect" ||
		strings.HasPrefix(action, "inspect") ||
		strings.Contains(action, "live_read") ||
		strings.Contains(action, "source_read")
}

func semanticAuditActions(actions []SemanticAuditAction) []SemanticAuditAction {
	result := make([]SemanticAuditAction, 0, len(actions))
	for _, action := range actions {
		action.Step = strings.TrimSpace(action.Step)
		action.InputRef = strings.TrimSpace(action.InputRef)
		action.OutputRef = strings.TrimSpace(action.OutputRef)
		action.PermissionBefore = strings.ToUpper(strings.TrimSpace(action.PermissionBefore))
		action.PermissionAfter = strings.ToUpper(strings.TrimSpace(action.PermissionAfter))
		action.Summary = strings.TrimSpace(action.Summary)
		if action.Step != "" {
			result = append(result, action)
		}
	}
	if result == nil {
		return []SemanticAuditAction{}
	}
	return result
}

func semanticAuditCorrections(request SemanticAuditRequest) []SemanticAuditRouteCorrection {
	corrections := append([]SemanticAuditRouteCorrection{}, request.RouteCorrections...)
	for _, falseMatch := range request.SemanticIntakeOutput.LearningCandidate.FalseMatches {
		if falseMatch.Phrase == "" || falseMatch.RejectedConceptID == "" || falseMatch.FalseMatchType == "" {
			continue
		}
		corrections = append(corrections, SemanticAuditRouteCorrection{
			Phrase:            falseMatch.Phrase,
			RejectedConceptID: falseMatch.RejectedConceptID,
			FalseMatchType:    falseMatch.FalseMatchType,
			CorrectionReason:  "semantic-intake false match candidate; promote only with live evidence and confirmation",
		})
	}
	normalized := make([]SemanticAuditRouteCorrection, 0, len(corrections))
	seen := map[string]bool{}
	for _, correction := range corrections {
		correction.Phrase = strings.TrimSpace(correction.Phrase)
		correction.RejectedConceptID = strings.TrimSpace(correction.RejectedConceptID)
		correction.FalseMatchType = strings.TrimSpace(correction.FalseMatchType)
		correction.CorrectionReason = strings.TrimSpace(correction.CorrectionReason)
		correction.RequiredSignals = normalizeStrings(correction.RequiredSignals)
		correction.SuppressionSignals = normalizeStrings(correction.SuppressionSignals)
		if correction.Phrase == "" || correction.RejectedConceptID == "" || correction.FalseMatchType == "" {
			continue
		}
		key := correction.Phrase + "\x00" + correction.RejectedConceptID + "\x00" + correction.FalseMatchType
		if seen[key] {
			continue
		}
		seen[key] = true
		normalized = append(normalized, correction)
	}
	if normalized == nil {
		return []SemanticAuditRouteCorrection{}
	}
	return normalized
}
