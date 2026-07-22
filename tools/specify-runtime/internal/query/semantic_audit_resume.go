package query

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"sort"
	"strings"
)

type SemanticAuditResumeRequest struct {
	Version             int                      `json:"version"`
	SemanticAuditInput  SemanticAuditRequest     `json:"semantic_audit_input"`
	SemanticAuditOutput SemanticAuditArtifact    `json:"semantic_audit_output"`
	SemanticAuditState  SemanticAuditResumeState `json:"semantic_audit_state"`
	WorkflowState       SemanticAuditResumeState `json:"workflow_state,omitempty"`
}

type SemanticAuditResumeState struct {
	SemanticAuditStatus               string   `json:"semantic_audit_status,omitempty"`
	SemanticAuditInputPath            string   `json:"semantic_audit_input_path,omitempty"`
	SemanticAuditOutputPath           string   `json:"semantic_audit_output_path,omitempty"`
	SemanticAuditResumeStatus         string   `json:"semantic_audit_resume_status,omitempty"`
	SemanticAuditResumeValidation     string   `json:"semantic_audit_resume_validation,omitempty"`
	SemanticAuditRouteFingerprint     string   `json:"semantic_audit_route_fingerprint,omitempty"`
	SemanticAuditGeneratedResumeSmoke string   `json:"semantic_audit_generated_resume_smoke,omitempty"`
	SemanticAuditStaleReasons         []string `json:"semantic_audit_stale_reasons,omitempty"`
	ActiveClaimType                   string   `json:"active_claim_type,omitempty"`
	SelectedCandidateIDs              []string `json:"selected_candidate_ids,omitempty"`
	ClaimReadinessStatus              string   `json:"claim_readiness_status,omitempty"`
	ClaimAuthorizationRefs            []string `json:"claim_authorization_refs,omitempty"`
	ClaimVerificationRefs             []string `json:"claim_verification_refs,omitempty"`
}

type SemanticAuditResumeValidation struct {
	Version                               int                             `json:"version"`
	Validator                             string                          `json:"validator"`
	SemanticAuditGeneratedResumeSmoke     string                          `json:"semantic_audit_generated_resume_smoke"`
	SemanticAuditResumeStatus             string                          `json:"semantic_audit_resume_status"`
	SemanticAuditResumeValidation         string                          `json:"semantic_audit_resume_validation"`
	SemanticAuditRouteFingerprint         string                          `json:"semantic_audit_route_fingerprint"`
	ExpectedSemanticAuditRouteFingerprint string                          `json:"expected_semantic_audit_route_fingerprint"`
	SemanticAuditStaleReasons             []string                        `json:"semantic_audit_stale_reasons"`
	Comparisons                           []SemanticAuditResumeComparison `json:"comparisons"`
	CanReusePersistedClaimReadiness       bool                            `json:"can_reuse_persisted_claim_readiness"`
	ClaimReadyAllowed                     bool                            `json:"claim_ready_allowed"`
	PermissionPromotionGranted            bool                            `json:"permission_promotion_granted"`
	GrantsPermission                      bool                            `json:"grants_permission"`
	Boundary                              string                          `json:"boundary"`
	RequiredAction                        string                          `json:"required_action"`
	Reason                                string                          `json:"reason,omitempty"`
}

type SemanticAuditResumeComparison struct {
	Field    string   `json:"field"`
	Status   string   `json:"status"`
	Expected []string `json:"expected"`
	Actual   []string `json:"actual"`
	Reason   string   `json:"reason,omitempty"`
}

func ParseSemanticAuditResumeRequest(data []byte) (SemanticAuditResumeRequest, error) {
	var request SemanticAuditResumeRequest
	if err := json.Unmarshal(data, &request); err != nil {
		return SemanticAuditResumeRequest{}, fmt.Errorf("parse semantic-audit-resume request: %w", err)
	}
	if request.SemanticAuditInput.WorkContract.RawRequest == "" && request.SemanticAuditOutput.ArtifactType == "" {
		var wrapped struct {
			SemanticAuditResumeInput SemanticAuditResumeRequest `json:"semantic_audit_resume_input"`
		}
		if err := json.Unmarshal(data, &wrapped); err != nil {
			return SemanticAuditResumeRequest{}, fmt.Errorf("parse semantic-audit-resume request: %w", err)
		}
		if wrapped.SemanticAuditResumeInput.SemanticAuditInput.WorkContract.RawRequest != "" || wrapped.SemanticAuditResumeInput.SemanticAuditOutput.ArtifactType != "" {
			request = wrapped.SemanticAuditResumeInput
		}
	}
	if semanticAuditResumeStateEmpty(request.SemanticAuditState) && !semanticAuditResumeStateEmpty(request.WorkflowState) {
		request.SemanticAuditState = request.WorkflowState
	}
	request = normalizeSemanticAuditResumeRequest(request)
	if reasons := validateSemanticAuditResumeRequest(request); len(reasons) > 0 {
		return SemanticAuditResumeRequest{}, fmt.Errorf("invalid semantic-audit-resume request: %s", strings.Join(reasons, "; "))
	}
	return request, nil
}

func ValidateSemanticAuditResume(request SemanticAuditResumeRequest) (SemanticAuditResumeValidation, error) {
	request = normalizeSemanticAuditResumeRequest(request)
	if reasons := validateSemanticAuditResumeRequest(request); len(reasons) > 0 {
		return SemanticAuditResumeValidation{}, fmt.Errorf("invalid semantic-audit-resume request: %s", strings.Join(reasons, "; "))
	}

	expectedSelected := normalizeStrings(request.SemanticAuditInput.RouteDecision.SelectedCandidateIDs)
	expectedClaimType := strings.ToLower(strings.TrimSpace(request.SemanticAuditOutput.ClaimReadiness.ClaimType))
	if expectedClaimType == "" {
		expectedClaimType = "none"
	}
	expectedFingerprint := SemanticAuditResumeRouteFingerprint(expectedSelected, expectedClaimType)
	expectedAuthorizationRefs := semanticAuditResumeAuthorizationRefs(request.SemanticAuditOutput.WorkflowAuthorization, expectedClaimType)
	expectedVerificationRefs := normalizeStrings(request.SemanticAuditOutput.ClaimReadiness.ClaimVerificationRefs)

	comparisons := []SemanticAuditResumeComparison{}
	reasons := []string{}

	addComparison := func(field string, expected, actual []string, reason string) {
		status := "passed"
		if !semanticAuditResumeStringSetsEqual(expected, actual) {
			status = "failed"
			reasons = append(reasons, reason)
		}
		comparisons = append(comparisons, SemanticAuditResumeComparison{
			Field:    field,
			Status:   status,
			Expected: normalizeStrings(expected),
			Actual:   normalizeStrings(actual),
			Reason:   reason,
		})
	}

	state := request.SemanticAuditState
	if semanticAuditResumeMissingFile(state.SemanticAuditInputPath) || semanticAuditResumeMissingFile(state.SemanticAuditOutputPath) {
		reasons = append(reasons, "missing-file")
		comparisons = append(comparisons, SemanticAuditResumeComparison{
			Field:    "audit_files",
			Status:   "failed",
			Expected: []string{"semantic-audit-input.json", "semantic-audit-output.json"},
			Actual:   normalizeStrings([]string{state.SemanticAuditInputPath, state.SemanticAuditOutputPath}),
			Reason:   "missing-file",
		})
	}
	addComparison("selected_candidate_ids", expectedSelected, state.SelectedCandidateIDs, "route-changed")
	addComparison("semantic_audit_file_pair_route", expectedSelected, request.SemanticAuditOutput.RouteDecision.SelectedCandidateIDs, "route-changed")
	addComparison("active_claim_type", []string{expectedClaimType}, []string{state.ActiveClaimType}, "active-claim-changed")
	addComparison("semantic_audit_route_fingerprint", []string{expectedFingerprint}, []string{state.SemanticAuditRouteFingerprint}, "route-changed")
	addComparison("claim_authorization_refs", expectedAuthorizationRefs, state.ClaimAuthorizationRefs, "claim-ref-mismatch")
	addComparison("claim_verification_refs", expectedVerificationRefs, state.ClaimVerificationRefs, "verification-ref-mismatch")
	if semanticAuditResumeClaimNeedsClaimAuthorizationCoverage(expectedClaimType) {
		addComparison("claim_authorization_verification_refs", expectedVerificationRefs, semanticAuditResumeClaimAuthorizationVerificationRefs(request.SemanticAuditOutput.WorkflowAuthorization, expectedClaimType), "verification-ref-mismatch")
	}

	reasons = normalizeStrings(reasons)
	validation := SemanticAuditResumeValidation{
		Version:                               1,
		Validator:                             "semantic-audit-resume",
		SemanticAuditRouteFingerprint:         state.SemanticAuditRouteFingerprint,
		ExpectedSemanticAuditRouteFingerprint: expectedFingerprint,
		Comparisons:                           comparisons,
		PermissionPromotionGranted:            false,
		GrantsPermission:                      false,
		Boundary:                              "comparison_only_no_source_edit_or_claim_authorization",
	}
	if len(reasons) == 0 {
		validation.SemanticAuditGeneratedResumeSmoke = "passed"
		validation.SemanticAuditResumeStatus = "fresh"
		validation.SemanticAuditResumeValidation = "fresh"
		validation.SemanticAuditStaleReasons = []string{"none"}
		validation.CanReusePersistedClaimReadiness = true
		validation.ClaimReadyAllowed = request.SemanticAuditOutput.ClaimReadiness.ClaimReady
		if validation.ClaimReadyAllowed {
			validation.RequiredAction = "reuse_persisted_claim_readiness"
		} else {
			validation.RequiredAction = "continue_without_final_claim"
		}
		validation.Reason = "persisted semantic-audit state matches audit input and output"
		return validation, nil
	}
	validation.SemanticAuditGeneratedResumeSmoke = "failed"
	validation.SemanticAuditResumeStatus = "needs-rerun"
	validation.SemanticAuditResumeValidation = "needs-rerun"
	validation.SemanticAuditStaleReasons = reasons
	validation.ClaimReadyAllowed = false
	validation.RequiredAction = "rebuild_semantic_audit_input"
	validation.Reason = "persisted semantic-audit state differs from audit input or output"
	return validation, nil
}

func BuildSemanticAuditResumeMissingFileValidation(state SemanticAuditResumeState) SemanticAuditResumeValidation {
	state = normalizeSemanticAuditResumeState(state)
	return SemanticAuditResumeValidation{
		Version:                               1,
		Validator:                             "semantic-audit-resume",
		SemanticAuditGeneratedResumeSmoke:     "failed",
		SemanticAuditResumeStatus:             "needs-rerun",
		SemanticAuditResumeValidation:         "needs-rerun",
		SemanticAuditRouteFingerprint:         state.SemanticAuditRouteFingerprint,
		ExpectedSemanticAuditRouteFingerprint: "",
		SemanticAuditStaleReasons:             []string{"missing-file"},
		Comparisons: []SemanticAuditResumeComparison{{
			Field:    "audit_files",
			Status:   "failed",
			Expected: []string{"semantic-audit-input.json", "semantic-audit-output.json"},
			Actual:   normalizeStrings([]string{state.SemanticAuditInputPath, state.SemanticAuditOutputPath}),
			Reason:   "missing-file",
		}},
		CanReusePersistedClaimReadiness: false,
		ClaimReadyAllowed:               false,
		PermissionPromotionGranted:      false,
		GrantsPermission:                false,
		Boundary:                        "comparison_only_no_source_edit_or_claim_authorization",
		RequiredAction:                  "rebuild_semantic_audit_input",
		Reason:                          "persisted semantic-audit files are missing or unreadable",
	}
}

func SemanticAuditResumeRouteFingerprint(selectedCandidateIDs []string, activeClaimType string) string {
	selected := normalizeStrings(selectedCandidateIDs)
	claim := strings.ToLower(strings.TrimSpace(activeClaimType))
	if claim == "" {
		claim = "none"
	}
	base := "selected_candidate_ids=" + strings.Join(selected, ",") + ";active_claim_type=" + claim
	sum := sha256.Sum256([]byte(base))
	return "semantic-audit-route:v1:" + hex.EncodeToString(sum[:8])
}

func normalizeSemanticAuditResumeRequest(request SemanticAuditResumeRequest) SemanticAuditResumeRequest {
	if request.Version == 0 {
		request.Version = 1
	}
	if semanticAuditResumeStateEmpty(request.SemanticAuditState) && !semanticAuditResumeStateEmpty(request.WorkflowState) {
		request.SemanticAuditState = request.WorkflowState
	}
	request.SemanticAuditInput = normalizeSemanticAuditRequest(request.SemanticAuditInput)
	request.SemanticAuditState = normalizeSemanticAuditResumeState(request.SemanticAuditState)
	request.WorkflowState = normalizeSemanticAuditResumeState(request.WorkflowState)
	return request
}

func normalizeSemanticAuditResumeState(state SemanticAuditResumeState) SemanticAuditResumeState {
	state.SemanticAuditStatus = strings.TrimSpace(state.SemanticAuditStatus)
	state.SemanticAuditInputPath = strings.TrimSpace(state.SemanticAuditInputPath)
	state.SemanticAuditOutputPath = strings.TrimSpace(state.SemanticAuditOutputPath)
	state.SemanticAuditResumeStatus = strings.TrimSpace(state.SemanticAuditResumeStatus)
	state.SemanticAuditResumeValidation = strings.TrimSpace(state.SemanticAuditResumeValidation)
	state.SemanticAuditRouteFingerprint = strings.TrimSpace(state.SemanticAuditRouteFingerprint)
	state.SemanticAuditGeneratedResumeSmoke = strings.TrimSpace(state.SemanticAuditGeneratedResumeSmoke)
	state.SemanticAuditStaleReasons = normalizeStrings(state.SemanticAuditStaleReasons)
	state.ActiveClaimType = strings.ToLower(strings.TrimSpace(state.ActiveClaimType))
	if state.ActiveClaimType == "" {
		state.ActiveClaimType = "none"
	}
	state.SelectedCandidateIDs = normalizeStrings(state.SelectedCandidateIDs)
	state.ClaimReadinessStatus = strings.TrimSpace(state.ClaimReadinessStatus)
	state.ClaimAuthorizationRefs = normalizeStrings(state.ClaimAuthorizationRefs)
	state.ClaimVerificationRefs = normalizeStrings(state.ClaimVerificationRefs)
	return state
}

func validateSemanticAuditResumeRequest(request SemanticAuditResumeRequest) []string {
	reasons := []string{}
	if request.Version != 1 {
		reasons = append(reasons, "version must be 1")
	}
	if request.SemanticAuditInput.WorkContract.RawRequest == "" {
		reasons = append(reasons, "semantic_audit_input.work_contract.raw_request is required")
	}
	if request.SemanticAuditOutput.ArtifactType == "" {
		reasons = append(reasons, "semantic_audit_output.artifact_type is required")
	}
	return reasons
}

func semanticAuditResumeAuthorizationRefs(value SemanticAuditWorkflowAuthorization, activeClaimType string) []string {
	activeClaimType = strings.ToLower(strings.TrimSpace(activeClaimType))
	claimRefs := []string{}
	for _, authorization := range value.ClaimAuthorizations {
		if authorization.ClaimType == activeClaimType && authorization.AuthorizationRef != "" {
			claimRefs = append(claimRefs, authorization.AuthorizationRef)
		}
	}
	if len(claimRefs) > 0 {
		return normalizeStrings(claimRefs)
	}
	if value.AuthorizationRef != "" {
		return normalizeStrings([]string{value.AuthorizationRef})
	}
	return []string{}
}

func semanticAuditResumeClaimAuthorizationVerificationRefs(value SemanticAuditWorkflowAuthorization, activeClaimType string) []string {
	activeClaimType = strings.ToLower(strings.TrimSpace(activeClaimType))
	refs := []string{}
	for _, authorization := range value.ClaimAuthorizations {
		if authorization.ClaimType == activeClaimType {
			refs = append(refs, authorization.VerificationEvidenceRefs...)
		}
	}
	return normalizeStrings(refs)
}

func semanticAuditResumeClaimNeedsClaimAuthorizationCoverage(claimType string) bool {
	switch strings.ToLower(strings.TrimSpace(claimType)) {
	case "fixed_claim", "completed_claim", "release_safe":
		return true
	default:
		return false
	}
}

func semanticAuditResumeStateEmpty(state SemanticAuditResumeState) bool {
	return strings.TrimSpace(state.SemanticAuditInputPath) == "" &&
		strings.TrimSpace(state.SemanticAuditOutputPath) == "" &&
		strings.TrimSpace(state.SemanticAuditRouteFingerprint) == "" &&
		strings.TrimSpace(state.ActiveClaimType) == "" &&
		len(state.SelectedCandidateIDs) == 0 &&
		len(state.ClaimAuthorizationRefs) == 0 &&
		len(state.ClaimVerificationRefs) == 0
}

func semanticAuditResumeMissingFile(path string) bool {
	path = strings.TrimSpace(path)
	return path == "" || strings.EqualFold(path, "none")
}

func semanticAuditResumeStringSetsEqual(left []string, right []string) bool {
	left = normalizeStrings(left)
	right = normalizeStrings(right)
	if len(left) != len(right) {
		return false
	}
	sort.Strings(left)
	sort.Strings(right)
	for i := range left {
		if left[i] != right[i] {
			return false
		}
	}
	return true
}
