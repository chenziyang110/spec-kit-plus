package query

import (
	"encoding/json"
	"strings"
	"testing"
)

func TestSemanticAuditCapturesReplayableRoutingArtifact(t *testing.T) {
	artifact, err := BuildSemanticAudit(sampleSemanticAuditRequest())
	if err != nil {
		t.Fatal(err)
	}

	if artifact.Version != 1 {
		t.Fatalf("Version = %d, want 1", artifact.Version)
	}
	if artifact.ArtifactType != "semantic_routing_audit" {
		t.Fatalf("ArtifactType = %q, want semantic_routing_audit", artifact.ArtifactType)
	}
	if artifact.WorkContract.RawRequest != "H5访问环境变量页面会出错" {
		t.Fatalf("WorkContract.RawRequest = %q", artifact.WorkContract.RawRequest)
	}
	if artifact.SemanticIntakeSnapshot.Input.RawRequest != artifact.WorkContract.RawRequest {
		t.Fatalf("SemanticIntakeSnapshot.Input.RawRequest = %q, want work contract raw request", artifact.SemanticIntakeSnapshot.Input.RawRequest)
	}
	if artifact.SemanticIntakeSnapshot.Output.Readiness != semanticIntakeReadinessQueryReady {
		t.Fatalf("SemanticIntakeSnapshot.Output.Readiness = %q", artifact.SemanticIntakeSnapshot.Output.Readiness)
	}
	if len(artifact.RouteDecision.SelectedCandidates) != 1 {
		t.Fatalf("SelectedCandidates = %#v, want one selected candidate", artifact.RouteDecision.SelectedCandidates)
	}
	selected := artifact.RouteDecision.SelectedCandidates[0]
	if selected.ID != "environment-settings-page" {
		t.Fatalf("SelectedCandidates[0].ID = %q", selected.ID)
	}
	if len(selected.Basis) == 0 {
		t.Fatalf("SelectedCandidates[0].Basis = %#v, want copied candidate basis", selected.Basis)
	}
	if artifact.PermissionDecision.AllowedLevel != "P2" {
		t.Fatalf("AllowedLevel = %q, want semantic-intake-only cap P2", artifact.PermissionDecision.AllowedLevel)
	}
	if !hasString(artifact.PermissionDecision.BlockedActions, "change") {
		t.Fatalf("BlockedActions = %#v, want change blocked", artifact.PermissionDecision.BlockedActions)
	}
	if !hasString(artifact.PermissionDecision.DowngradeReasons, "semantic_intake_only_cannot_raise_above_p2") {
		t.Fatalf("DowngradeReasons = %#v, want semantic intake cap reason", artifact.PermissionDecision.DowngradeReasons)
	}
	if len(artifact.ActionLog) != 1 || artifact.ActionLog[0].Step != "semantic_intake" {
		t.Fatalf("ActionLog = %#v, want semantic_intake step", artifact.ActionLog)
	}
	if len(artifact.RouteCorrections) != 1 || artifact.RouteCorrections[0].FalseMatchType != "config-shadow" {
		t.Fatalf("RouteCorrections = %#v, want config-shadow correction", artifact.RouteCorrections)
	}
	if !hasString(artifact.Replay.BlockedFinalClaims, "fixed_claim") {
		t.Fatalf("Replay.BlockedFinalClaims = %#v, want fixed_claim blocked", artifact.Replay.BlockedFinalClaims)
	}
	if artifact.LearningBoundary.MaxMemoryLevelFromSemanticIntake != "M1" {
		t.Fatalf("LearningBoundary = %#v, want semantic-intake learning capped at M1", artifact.LearningBoundary)
	}
}

func TestParseSemanticAuditRequestRequiresWorkContractAndSnapshots(t *testing.T) {
	if _, err := ParseSemanticAuditRequest([]byte(`{}`)); err == nil {
		t.Fatal("ParseSemanticAuditRequest({}) succeeded, want validation error")
	}
	if _, err := ParseSemanticAuditRequest([]byte(`{"version":2}`)); err == nil {
		t.Fatal("ParseSemanticAuditRequest(version 2) succeeded, want validation error")
	}
}

func TestParseSemanticAuditRequestAcceptsWrappedWorkflowArtifact(t *testing.T) {
	data, err := json.Marshal(map[string]any{
		"semantic_audit_input": sampleSemanticAuditRequest(),
	})
	if err != nil {
		t.Fatal(err)
	}

	request, err := ParseSemanticAuditRequest(data)
	if err != nil {
		t.Fatal(err)
	}

	if request.WorkContract.RawRequest != "H5访问环境变量页面会出错" {
		t.Fatalf("WorkContract.RawRequest = %q", request.WorkContract.RawRequest)
	}
	if request.RouteDecision.SelectedCandidateIDs[0] != "environment-settings-page" {
		t.Fatalf("SelectedCandidateIDs = %#v", request.RouteDecision.SelectedCandidateIDs)
	}
}

func TestSemanticAuditRejectsUnknownSelectedCandidate(t *testing.T) {
	request := sampleSemanticAuditRequest()
	request.RouteDecision.SelectedCandidateIDs = []string{"missing-candidate"}

	if _, err := BuildSemanticAudit(request); err == nil {
		t.Fatal("BuildSemanticAudit succeeded with unknown selected candidate, want validation error")
	}
}

func TestSemanticAuditPreservesWorkflowWrittenWorkContractSchema(t *testing.T) {
	request := sampleSemanticAuditRequest()
	request.WorkContract.NormalizedGoal = "debug H5 environment settings page access exception"
	request.WorkContract.SemanticIntakeRef = "semantic_intake_output"
	request.WorkContract.SelectedConceptIDs = []string{"environment-settings-page"}
	request.WorkContract.RejectedConceptIDs = []string{"env-config"}
	request.WorkContract.EvidencePlan = []SemanticAuditEvidencePlanStep{{
		EvidenceNeed:    "verify route owner",
		SuggestedAction: "read minimal_live_reads before source edits",
		OwnerRef:        "environment-settings-page",
	}}
	request.WorkContract.PermissionDecision = SemanticAuditWorkContractPermission{
		CurrentLevel:               "p2",
		MaximumWithoutLiveEvidence: "p2",
		BlockedActions:             []string{"change", "fixed_claim"},
	}
	request.WorkContract.LearningContract = SemanticAuditWorkContractLearning{
		MemoryLevel:       "m1",
		PromotionRequires: []string{"live_source_evidence", "user_confirmation"},
	}

	artifact, err := BuildSemanticAudit(request)
	if err != nil {
		t.Fatal(err)
	}

	contract := artifact.WorkContract
	if contract.NormalizedGoal != "debug H5 environment settings page access exception" {
		t.Fatalf("NormalizedGoal = %q", contract.NormalizedGoal)
	}
	if contract.SemanticIntakeRef != "semantic_intake_output" {
		t.Fatalf("SemanticIntakeRef = %q", contract.SemanticIntakeRef)
	}
	if !hasString(contract.SelectedConceptIDs, "environment-settings-page") {
		t.Fatalf("SelectedConceptIDs = %#v", contract.SelectedConceptIDs)
	}
	if !hasString(contract.RejectedConceptIDs, "env-config") {
		t.Fatalf("RejectedConceptIDs = %#v", contract.RejectedConceptIDs)
	}
	if len(contract.EvidencePlan) != 1 || contract.EvidencePlan[0].EvidenceNeed != "verify route owner" {
		t.Fatalf("EvidencePlan = %#v", contract.EvidencePlan)
	}
	if contract.PermissionDecision.CurrentLevel != "P2" {
		t.Fatalf("PermissionDecision.CurrentLevel = %q, want P2", contract.PermissionDecision.CurrentLevel)
	}
	if !hasString(contract.PermissionDecision.BlockedActions, "fixed_claim") {
		t.Fatalf("PermissionDecision.BlockedActions = %#v", contract.PermissionDecision.BlockedActions)
	}
	if contract.LearningContract.MemoryLevel != "M1" {
		t.Fatalf("LearningContract.MemoryLevel = %q, want M1", contract.LearningContract.MemoryLevel)
	}
	if !hasString(contract.LearningContract.PromotionRequires, "live_source_evidence") {
		t.Fatalf("LearningContract.PromotionRequires = %#v", contract.LearningContract.PromotionRequires)
	}
}

func TestSemanticAuditRespectsSemanticIntakePermissionHintCap(t *testing.T) {
	request := sampleSemanticAuditRequest()
	request.SemanticIntakeOutput.Readiness = semanticIntakeReadinessInsufficientIndex
	request.SemanticIntakeOutput.CandidateUniverse.PrimaryCandidates = nil
	request.SemanticIntakeOutput.PermissionHint.MaximumWithoutLiveEvidence = "P1"
	request.RouteDecision.SelectedCandidateIDs = nil
	request.PermissionDecision.RequestedLevel = "P3"
	request.PermissionDecision.RequestedActions = []string{"targeted_inspect"}

	artifact, err := BuildSemanticAudit(request)
	if err != nil {
		t.Fatal(err)
	}

	if artifact.PermissionDecision.AllowedLevel != "P1" {
		t.Fatalf("AllowedLevel = %q, want semantic-intake permission hint cap P1", artifact.PermissionDecision.AllowedLevel)
	}
	if !hasString(artifact.PermissionDecision.BlockedActions, "targeted_inspect") {
		t.Fatalf("BlockedActions = %#v, want targeted_inspect blocked below P2", artifact.PermissionDecision.BlockedActions)
	}
	if !hasString(artifact.PermissionDecision.DowngradeReasons, "semantic_intake_permission_hint_caps_allowed_level") {
		t.Fatalf("DowngradeReasons = %#v, want permission hint cap reason", artifact.PermissionDecision.DowngradeReasons)
	}
}

func TestSemanticAuditRejectsInvalidEmbeddedSemanticIntakeInputVersion(t *testing.T) {
	request := sampleSemanticAuditRequest()
	request.SemanticIntakeInput.Version = 2

	if _, err := BuildSemanticAudit(request); err == nil {
		t.Fatal("BuildSemanticAudit succeeded with semantic_intake_input.version=2, want validation error")
	}
}

func TestSemanticAuditNormalizesEmbeddedSemanticIntakeOutputArrays(t *testing.T) {
	request := sampleSemanticAuditRequest()
	request.SemanticIntakeOutput.Readiness = semanticIntakeReadinessInsufficientIndex
	request.SemanticIntakeOutput.CandidateUniverse = SemanticIntakeUniverse{}
	request.SemanticIntakeOutput.PermissionHint.MaximumWithoutLiveEvidence = "P1"
	request.RouteDecision.SelectedCandidateIDs = nil
	request.RouteDecision.ContrastCandidateIDs = nil
	request.RouteDecision.RejectedCandidateIDs = nil

	artifact, err := BuildSemanticAudit(request)
	if err != nil {
		t.Fatal(err)
	}

	universe := artifact.SemanticIntakeSnapshot.Output.CandidateUniverse
	if universe.PrimaryCandidates == nil || universe.ContrastCandidates == nil || universe.RejectedCandidates == nil {
		t.Fatalf("CandidateUniverse = %#v, want non-nil empty slices", universe)
	}
	data, err := json.Marshal(artifact.SemanticIntakeSnapshot.Output)
	if err != nil {
		t.Fatal(err)
	}
	outputJSON := string(data)
	for _, field := range []string{"primary_candidates", "contrast_candidates", "rejected_candidates"} {
		if strings.Contains(outputJSON, `"`+field+`":null`) {
			t.Fatalf("%s serialized as null in %s", field, outputJSON)
		}
	}
}

func TestSemanticAuditFixturesCoverV11RoutingScenarios(t *testing.T) {
	tests := []struct {
		name                 string
		request              SemanticAuditRequest
		wantRawRequest       string
		wantSelectedID       string
		wantRejectedID       string
		wantFalseMatchType   string
		wantCorrectionPhrase string
		wantAllowedLevel     string
		wantBlockedAction    string
	}{
		{
			name:                 "localized CJK request",
			request:              sampleSemanticAuditRequest(),
			wantRawRequest:       "H5访问环境变量页面会出错",
			wantSelectedID:       "environment-settings-page",
			wantRejectedID:       "workflow-environment",
			wantFalseMatchType:   "workflow-shadow",
			wantCorrectionPhrase: "环境变量",
			wantAllowedLevel:     "P2",
			wantBlockedAction:    "change",
		},
		{
			name:                 "mixed CJK ASCII request",
			request:              sampleMixedCJKAuditRequest(),
			wantRawRequest:       "H5 EnvironmentSettings页面白屏",
			wantSelectedID:       "environment-settings-page",
			wantRejectedID:       "env-config",
			wantFalseMatchType:   "config-shadow",
			wantCorrectionPhrase: "EnvironmentSettings页面",
			wantAllowedLevel:     "P2",
			wantBlockedAction:    "change",
		},
		{
			name:                 "symptom-first request",
			request:              sampleSymptomFirstAuditRequest(),
			wantRawRequest:       "打开就白屏，像是设置页挂了",
			wantSelectedID:       "environment-settings-page",
			wantRejectedID:       "docs-environment-settings",
			wantFalseMatchType:   "docs-shadow",
			wantCorrectionPhrase: "设置页",
			wantAllowedLevel:     "P2",
			wantBlockedAction:    "fixed_claim",
		},
		{
			name:                 "workflow-shadow false friend",
			request:              sampleWorkflowShadowAuditRequest(),
			wantRawRequest:       "sp-debug 启动的时候环境报错",
			wantSelectedID:       "generated-sp-debug-runtime",
			wantRejectedID:       "environment-settings-page",
			wantFalseMatchType:   "ui-page-shadow",
			wantCorrectionPhrase: "sp-debug 环境",
			wantAllowedLevel:     "P2",
			wantBlockedAction:    "completed_claim",
		},
		{
			name:                 "docs-shadow false friend",
			request:              sampleDocsShadowAuditRequest(),
			wantRawRequest:       "环境变量页面在哪个文档里说明了",
			wantSelectedID:       "environment-settings-docs",
			wantRejectedID:       "environment-settings-page",
			wantFalseMatchType:   "ui-page-shadow",
			wantCorrectionPhrase: "文档里说明",
			wantAllowedLevel:     "P1",
			wantBlockedAction:    "targeted_inspect",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			artifact, err := BuildSemanticAudit(tt.request)
			if err != nil {
				t.Fatal(err)
			}
			if artifact.WorkContract.RawRequest != tt.wantRawRequest {
				t.Fatalf("RawRequest = %q, want %q", artifact.WorkContract.RawRequest, tt.wantRawRequest)
			}
			if artifact.SemanticIntakeSnapshot.Input.RawRequest != tt.wantRawRequest {
				t.Fatalf("SemanticIntakeSnapshot.Input.RawRequest = %q, want %q", artifact.SemanticIntakeSnapshot.Input.RawRequest, tt.wantRawRequest)
			}
			if len(artifact.RouteDecision.SelectedCandidates) != 1 || artifact.RouteDecision.SelectedCandidates[0].ID != tt.wantSelectedID {
				t.Fatalf("SelectedCandidates = %#v, want %q", artifact.RouteDecision.SelectedCandidates, tt.wantSelectedID)
			}
			if len(artifact.RouteDecision.RejectedCandidates) != 1 {
				t.Fatalf("RejectedCandidates = %#v, want one rejected candidate", artifact.RouteDecision.RejectedCandidates)
			}
			rejected := artifact.RouteDecision.RejectedCandidates[0]
			if rejected.ID != tt.wantRejectedID || rejected.FalseMatchType != tt.wantFalseMatchType {
				t.Fatalf("RejectedCandidates[0] = %#v, want id=%q false_match_type=%q", rejected, tt.wantRejectedID, tt.wantFalseMatchType)
			}
			if !hasString(artifact.RouteDecision.SelectedCandidates[0].Basis, "facet coverage preserved for audit replay") {
				t.Fatalf("Selected basis = %#v, want audit replay basis", artifact.RouteDecision.SelectedCandidates[0].Basis)
			}
			if len(artifact.RouteCorrections) == 0 || artifact.RouteCorrections[0].Phrase != tt.wantCorrectionPhrase {
				t.Fatalf("RouteCorrections = %#v, want phrase %q", artifact.RouteCorrections, tt.wantCorrectionPhrase)
			}
			if artifact.PermissionDecision.AllowedLevel != tt.wantAllowedLevel {
				t.Fatalf("AllowedLevel = %q, want %q", artifact.PermissionDecision.AllowedLevel, tt.wantAllowedLevel)
			}
			if !hasString(artifact.PermissionDecision.BlockedActions, tt.wantBlockedAction) {
				t.Fatalf("BlockedActions = %#v, want %q", artifact.PermissionDecision.BlockedActions, tt.wantBlockedAction)
			}
			if len(artifact.ActionLog) == 0 {
				t.Fatalf("ActionLog = %#v, want replayable action log", artifact.ActionLog)
			}
		})
	}
}

func TestSemanticAuditFixtureCoversStaleRuntimeFallback(t *testing.T) {
	request := sampleStaleRuntimeFallbackAuditRequest()

	artifact, err := BuildSemanticAudit(request)
	if err != nil {
		t.Fatal(err)
	}

	if artifact.SemanticIntakeSnapshot.Output.Readiness != semanticIntakeReadinessRuntimeUnavailable {
		t.Fatalf("Readiness = %q, want runtime_unavailable", artifact.SemanticIntakeSnapshot.Output.Readiness)
	}
	if artifact.PermissionDecision.AllowedLevel != "P0" {
		t.Fatalf("AllowedLevel = %q, want P0 runtime fallback cap", artifact.PermissionDecision.AllowedLevel)
	}
	if !hasString(artifact.PermissionDecision.BlockedActions, "inspect_broadly") {
		t.Fatalf("BlockedActions = %#v, want inspect_broadly blocked", artifact.PermissionDecision.BlockedActions)
	}
	if artifact.LearningBoundary.MaxMemoryLevelFromSemanticIntake != "M1" {
		t.Fatalf("LearningBoundary = %#v, want no durable promotion from fallback", artifact.LearningBoundary)
	}
}

func TestSemanticAuditBuildsEvidenceGuidedInspectionPlan(t *testing.T) {
	request := sampleSemanticAuditRequest()
	request.WorkContract.EvidencePlan = []SemanticAuditEvidencePlanStep{{
		EvidenceNeed:    "client/web behavior split",
		SuggestedAction: "compare H5 adapter boundary",
		OwnerRef:        "environment-settings-page",
	}}
	request.SemanticIntakeOutput.MissingEvidence = []SemanticIntakeMissing{
		{Facet: "exact exception source", SuggestedAction: "inspect runtime stack at primary owner"},
		{Facet: "verification path", SuggestedAction: "identify positive and regression verification owner"},
	}
	request.SemanticIntakeOutput.CandidateUniverse.PrimaryCandidates[0].OwnerHints = SemanticIntakeOwnerHints{
		PrimaryPaths:      []string{"desktop/src/pages/EnvironmentSettings.tsx"},
		VerificationPaths: []string{"desktop/src/pages/EnvironmentSettings.test.tsx"},
	}

	artifact, err := BuildSemanticAudit(request)
	if err != nil {
		t.Fatal(err)
	}

	plan := artifact.InspectionPlan
	if plan.Readiness != "inspect_ready" {
		t.Fatalf("InspectionPlan.Readiness = %q, want inspect_ready", plan.Readiness)
	}
	if plan.MaxPermission != "P2" {
		t.Fatalf("InspectionPlan.MaxPermission = %q, want P2", plan.MaxPermission)
	}
	if !hasString(plan.BlockedActions, "change") || !hasString(plan.BlockedActions, "fixed_claim") {
		t.Fatalf("InspectionPlan.BlockedActions = %#v, want change and fixed_claim blocked", plan.BlockedActions)
	}
	if !hasString(plan.LiveEvidenceCapture.RequiredFields, "read_path") {
		t.Fatalf("LiveEvidenceCapture.RequiredFields = %#v, want read_path", plan.LiveEvidenceCapture.RequiredFields)
	}
	if !hasString(plan.RerankAfterInspect.BlockedClaimsUntilRerank, "root_cause_claim") {
		t.Fatalf("RerankAfterInspect = %#v, want root_cause_claim blocked until rerank", plan.RerankAfterInspect)
	}
	assertInspectionStep(t, plan.Steps, "exact exception source", "desktop/src/pages/EnvironmentSettings.tsx", "targeted_read", "P2")
	assertInspectionStep(t, plan.Steps, "verification path", "desktop/src/pages/EnvironmentSettings.test.tsx", "targeted_read", "P2")
	assertInspectionStep(t, plan.Steps, "client/web behavior split", "desktop/src/pages/EnvironmentSettings.tsx", "targeted_read", "P2")
}

func TestSemanticAuditInspectionPlanBlocksBroadReadsWhenRuntimeUnavailable(t *testing.T) {
	artifact, err := BuildSemanticAudit(sampleStaleRuntimeFallbackAuditRequest())
	if err != nil {
		t.Fatal(err)
	}

	plan := artifact.InspectionPlan
	if plan.Readiness != "inspect_blocked" {
		t.Fatalf("InspectionPlan.Readiness = %q, want inspect_blocked", plan.Readiness)
	}
	if plan.MaxPermission != "P0" {
		t.Fatalf("InspectionPlan.MaxPermission = %q, want P0", plan.MaxPermission)
	}
	if len(plan.Steps) != 0 {
		t.Fatalf("InspectionPlan.Steps = %#v, want no live-read steps without a trusted route", plan.Steps)
	}
	if !hasString(plan.BlockedActions, "inspect_broadly") || !hasString(plan.BlockedActions, "change") {
		t.Fatalf("InspectionPlan.BlockedActions = %#v, want broad inspect and change blocked", plan.BlockedActions)
	}
	if !hasString(plan.StaleIndexDowngrade.Conditions, "runtime_unavailable") {
		t.Fatalf("StaleIndexDowngrade.Conditions = %#v, want runtime_unavailable", plan.StaleIndexDowngrade.Conditions)
	}
}

func TestSemanticAuditCapturedLiveEvidenceCreatesPromotionCandidateWithoutRaisingAllowedLevel(t *testing.T) {
	request := sampleSemanticAuditRequest()
	request.SemanticIntakeOutput.CandidateUniverse.PrimaryCandidates[0].OwnerHints = SemanticIntakeOwnerHints{
		PrimaryPaths: []string{"desktop/src/pages/EnvironmentSettings.tsx"},
	}
	request.LiveEvidenceCapture = []SemanticAuditCapturedEvidence{{
		StepID:              "inspect-01",
		ReadPath:            "desktop/src/pages/EnvironmentSettings.tsx",
		EvidenceNeed:        "exact exception source",
		SourceKind:          "source",
		SourceRef:           "desktop/src/pages/EnvironmentSettings.tsx",
		LineRefs:            []string{"L42-L57"},
		ObservedSignal:      "H5 access exception stack enters EnvironmentSettings route guard",
		SupportsCandidateID: "environment-settings-page",
		SupportsCandidate:   true,
		EvidenceRef:         "read:desktop/src/pages/EnvironmentSettings.tsx#route-guard",
	}}

	artifact, err := BuildSemanticAudit(request)
	if err != nil {
		t.Fatal(err)
	}

	if artifact.PermissionDecision.AllowedLevel != "P2" {
		t.Fatalf("AllowedLevel = %q, want live evidence captured but no direct raise above P2", artifact.PermissionDecision.AllowedLevel)
	}
	if len(artifact.LiveEvidenceCapture) != 1 {
		t.Fatalf("LiveEvidenceCapture = %#v, want one captured evidence entry", artifact.LiveEvidenceCapture)
	}
	if artifact.RerankAssessment.Status != "route_supported" {
		t.Fatalf("RerankAssessment.Status = %q, want route_supported", artifact.RerankAssessment.Status)
	}
	promotion := artifact.RerankAssessment.PermissionPromotionCandidate
	if promotion.CandidateLevel != "P3" {
		t.Fatalf("PermissionPromotionCandidate.CandidateLevel = %q, want P3", promotion.CandidateLevel)
	}
	if promotion.Status != "candidate_only" {
		t.Fatalf("PermissionPromotionCandidate.Status = %q, want candidate_only", promotion.Status)
	}
	if promotion.Granted {
		t.Fatalf("PermissionPromotionCandidate.Granted = true, want false before v1.3 verification owner discovery")
	}
	if !hasString(promotion.BlockedBy, "verification_owner_discovery") {
		t.Fatalf("PermissionPromotionCandidate.BlockedBy = %#v, want verification_owner_discovery", promotion.BlockedBy)
	}
	if !hasString(artifact.RerankAssessment.SupportingEvidenceRefs, "read:desktop/src/pages/EnvironmentSettings.tsx#route-guard") {
		t.Fatalf("SupportingEvidenceRefs = %#v, want captured evidence ref", artifact.RerankAssessment.SupportingEvidenceRefs)
	}
}

func TestSemanticAuditContradictingLiveEvidenceDowngradesRoutePermission(t *testing.T) {
	request := sampleSemanticAuditRequest()
	request.SemanticIntakeOutput.CandidateUniverse.PrimaryCandidates[0].OwnerHints = SemanticIntakeOwnerHints{
		PrimaryPaths: []string{"desktop/src/pages/EnvironmentSettings.tsx"},
	}
	request.LiveEvidenceCapture = []SemanticAuditCapturedEvidence{{
		StepID:                 "inspect-01",
		ReadPath:               "desktop/src/pages/EnvironmentSettings.tsx",
		EvidenceNeed:           "exact exception source",
		SourceKind:             "source",
		SourceRef:              "desktop/src/pages/EnvironmentSettings.tsx",
		LineRefs:               []string{"L42-L57"},
		ObservedSignal:         "route owner is not touched; exception source points to startup env config",
		ContradictsCandidateID: "environment-settings-page",
		ContradictsCandidate:   true,
		EvidenceRef:            "read:desktop/src/pages/EnvironmentSettings.tsx#no-match",
	}}

	artifact, err := BuildSemanticAudit(request)
	if err != nil {
		t.Fatal(err)
	}

	if artifact.RerankAssessment.Status != "route_contradicted" {
		t.Fatalf("RerankAssessment.Status = %q, want route_contradicted", artifact.RerankAssessment.Status)
	}
	if artifact.PermissionDecision.AllowedLevel != "P1" {
		t.Fatalf("AllowedLevel = %q, want P1 after selected route is contradicted", artifact.PermissionDecision.AllowedLevel)
	}
	if !hasString(artifact.PermissionDecision.DowngradeReasons, "live_evidence_contradicts_selected_candidate") {
		t.Fatalf("DowngradeReasons = %#v, want live evidence contradiction reason", artifact.PermissionDecision.DowngradeReasons)
	}
	if !hasString(artifact.PermissionDecision.BlockedActions, "targeted_inspect") {
		t.Fatalf("BlockedActions = %#v, want targeted_inspect blocked after route contradiction", artifact.PermissionDecision.BlockedActions)
	}
	promotion := artifact.RerankAssessment.PermissionPromotionCandidate
	if promotion.CandidateLevel != "P1" || promotion.Status != "blocked" {
		t.Fatalf("PermissionPromotionCandidate = %#v, want blocked P1 candidate", promotion)
	}
	if !hasString(promotion.BlockedBy, "live_evidence_contradicts_candidate") {
		t.Fatalf("PermissionPromotionCandidate.BlockedBy = %#v, want contradiction blocker", promotion.BlockedBy)
	}
	if !hasString(artifact.RerankAssessment.ContradictingEvidenceRefs, "read:desktop/src/pages/EnvironmentSettings.tsx#no-match") {
		t.Fatalf("ContradictingEvidenceRefs = %#v, want captured evidence ref", artifact.RerankAssessment.ContradictingEvidenceRefs)
	}
}

func TestSemanticAuditRouteVocabularyEvidenceCannotCreatePromotionCandidate(t *testing.T) {
	request := sampleSemanticAuditRequest()
	request.LiveEvidenceCapture = []SemanticAuditCapturedEvidence{{
		StepID:              "inspect-01",
		EvidenceNeed:        "exact exception source",
		SourceKind:          "route_vocabulary",
		SourceRef:           "semantic_intake_snapshot",
		ObservedSignal:      "alias and owner hint point at environment settings page",
		SupportsCandidateID: "environment-settings-page",
		SupportsCandidate:   true,
		EvidenceRef:         "semantic:intake:environment-settings-page",
	}}

	artifact, err := BuildSemanticAudit(request)
	if err != nil {
		t.Fatal(err)
	}

	if artifact.RerankAssessment.Status != "evidence_missing" {
		t.Fatalf("RerankAssessment.Status = %q, want evidence_missing for route vocabulary evidence", artifact.RerankAssessment.Status)
	}
	promotion := artifact.RerankAssessment.PermissionPromotionCandidate
	if promotion.CandidateLevel != "P2" || promotion.Status != "blocked" {
		t.Fatalf("PermissionPromotionCandidate = %#v, want blocked P2 candidate", promotion)
	}
	if !hasString(promotion.BlockedBy, "live_source_evidence_required") {
		t.Fatalf("PermissionPromotionCandidate.BlockedBy = %#v, want live_source_evidence_required", promotion.BlockedBy)
	}
	if len(artifact.RerankAssessment.SupportingEvidenceRefs) != 0 {
		t.Fatalf("SupportingEvidenceRefs = %#v, want route vocabulary excluded from promotion basis", artifact.RerankAssessment.SupportingEvidenceRefs)
	}
}

func TestSemanticAuditUnboundedSourceEvidenceCannotCreatePromotionCandidate(t *testing.T) {
	request := sampleSemanticAuditRequest()
	request.SemanticIntakeOutput.CandidateUniverse.PrimaryCandidates[0].OwnerHints = SemanticIntakeOwnerHints{
		PrimaryPaths: []string{"desktop/src/pages/EnvironmentSettings.tsx"},
	}
	request.LiveEvidenceCapture = []SemanticAuditCapturedEvidence{{
		StepID:              "inspect-01",
		ReadPath:            "desktop/src/unrelated/BroadSearchResult.ts",
		EvidenceNeed:        "exact exception source",
		SourceKind:          "source",
		SourceRef:           "desktop/src/unrelated/BroadSearchResult.ts",
		ObservedSignal:      "broad read mentions EnvironmentSettings",
		SupportsCandidateID: "environment-settings-page",
		SupportsCandidate:   true,
		EvidenceRef:         "read:desktop/src/unrelated/BroadSearchResult.ts#broad-match",
	}}

	artifact, err := BuildSemanticAudit(request)
	if err != nil {
		t.Fatal(err)
	}

	if artifact.RerankAssessment.Status != "evidence_missing" {
		t.Fatalf("RerankAssessment.Status = %q, want evidence_missing for unbounded source evidence", artifact.RerankAssessment.Status)
	}
	promotion := artifact.RerankAssessment.PermissionPromotionCandidate
	if promotion.CandidateLevel != "P2" || promotion.Status != "blocked" {
		t.Fatalf("PermissionPromotionCandidate = %#v, want blocked P2 candidate", promotion)
	}
	if !hasString(promotion.BlockedBy, "bounded_source_evidence_required") {
		t.Fatalf("PermissionPromotionCandidate.BlockedBy = %#v, want bounded_source_evidence_required", promotion.BlockedBy)
	}
	if len(artifact.RerankAssessment.SupportingEvidenceRefs) != 0 {
		t.Fatalf("SupportingEvidenceRefs = %#v, want unbounded source evidence excluded from promotion basis", artifact.RerankAssessment.SupportingEvidenceRefs)
	}
}

func TestSemanticAuditRerankUsesMultipleLiveSourceEvidenceRecords(t *testing.T) {
	request := sampleSemanticAuditRequest()
	request.SemanticIntakeOutput.CandidateUniverse.PrimaryCandidates[0].OwnerHints = SemanticIntakeOwnerHints{
		PrimaryPaths:    []string{"desktop/src/pages/EnvironmentSettings.tsx"},
		SupportingPaths: []string{"desktop/src/routes/settings.ts"},
	}
	request.LiveEvidenceCapture = []SemanticAuditCapturedEvidence{
		{
			StepID:              "inspect-01",
			ReadPath:            "desktop/src/pages/EnvironmentSettings.tsx",
			EvidenceNeed:        "exact exception source",
			SourceKind:          "source",
			SourceRef:           "desktop/src/pages/EnvironmentSettings.tsx",
			ObservedSignal:      "route guard handles H5 access",
			SupportsCandidateID: "environment-settings-page",
			SupportsCandidate:   true,
			EvidenceRef:         "read:desktop/src/pages/EnvironmentSettings.tsx#route-guard",
		},
		{
			StepID:              "inspect-02",
			ReadPath:            "desktop/src/routes/settings.ts",
			EvidenceNeed:        "route binding",
			SourceKind:          "source",
			SourceRef:           "desktop/src/routes/settings.ts",
			ObservedSignal:      "H5 route points to EnvironmentSettings page",
			SupportsCandidateID: "environment-settings-page",
			SupportsCandidate:   true,
			EvidenceRef:         "read:desktop/src/routes/settings.ts#h5-env-route",
		},
		{
			StepID:              "inspect-03",
			EvidenceNeed:        "alias support",
			SourceKind:          "route_vocabulary",
			SourceRef:           "semantic_intake_snapshot",
			ObservedSignal:      "alias points at environment settings page",
			SupportsCandidateID: "environment-settings-page",
			SupportsCandidate:   true,
			EvidenceRef:         "semantic:intake:environment-settings-page",
		},
	}

	artifact, err := BuildSemanticAudit(request)
	if err != nil {
		t.Fatal(err)
	}

	if artifact.RerankAssessment.Status != "route_supported" {
		t.Fatalf("RerankAssessment.Status = %q, want route_supported", artifact.RerankAssessment.Status)
	}
	refs := artifact.RerankAssessment.SupportingEvidenceRefs
	for _, want := range []string{
		"read:desktop/src/pages/EnvironmentSettings.tsx#route-guard",
		"read:desktop/src/routes/settings.ts#h5-env-route",
	} {
		if !hasString(refs, want) {
			t.Fatalf("SupportingEvidenceRefs = %#v, want %q", refs, want)
		}
	}
	if hasString(refs, "semantic:intake:environment-settings-page") {
		t.Fatalf("SupportingEvidenceRefs = %#v, want route vocabulary excluded", refs)
	}
}

func TestSemanticAuditBuildsOwnerBundleConfidenceModel(t *testing.T) {
	request := sampleSemanticAuditRequest()
	request.SemanticIntakeOutput.CandidateUniverse.PrimaryCandidates[0].OwnerHints = SemanticIntakeOwnerHints{
		PrimaryPaths:      []string{"desktop/src/pages/EnvironmentSettings.tsx"},
		SupportingPaths:   []string{"desktop/src/routes/settings.ts"},
		TruthPaths:        []string{"desktop/src/pages/EnvironmentSettings.model.ts"},
		VerificationPaths: []string{"desktop/src/pages/EnvironmentSettings.test.tsx"},
	}

	artifact, err := BuildSemanticAudit(request)
	if err != nil {
		t.Fatal(err)
	}

	confidence := artifact.OwnerBundleConfidence
	if len(confidence.Candidates) != 1 {
		t.Fatalf("OwnerBundleConfidence.Candidates = %#v, want one candidate", confidence.Candidates)
	}
	candidate := confidence.Candidates[0]
	if candidate.CandidateID != "environment-settings-page" {
		t.Fatalf("CandidateID = %q", candidate.CandidateID)
	}
	if candidate.Confidence != "high" {
		t.Fatalf("Confidence = %q, want high", candidate.Confidence)
	}
	for _, role := range []string{"primary", "supporting", "truth", "verification"} {
		if !hasString(candidate.CoveredOwnerRoles, role) {
			t.Fatalf("CoveredOwnerRoles = %#v, want %q", candidate.CoveredOwnerRoles, role)
		}
	}
	if len(candidate.MissingOwnerRoles) != 0 {
		t.Fatalf("MissingOwnerRoles = %#v, want none", candidate.MissingOwnerRoles)
	}
	if confidence.Summary != "owner_bundle_high" {
		t.Fatalf("Summary = %q, want owner_bundle_high", confidence.Summary)
	}
}

func TestSemanticAuditBoundsOwnerMissExpansionRadius(t *testing.T) {
	request := sampleSemanticAuditRequest()
	request.SemanticIntakeOutput.CandidateUniverse.PrimaryCandidates[0].OwnerHints = SemanticIntakeOwnerHints{}
	request.SemanticIntakeOutput.ExpansionTargets = []SemanticIntakeExpansion{{
		ID:          "environment-settings-page:route",
		SurfaceType: "route_navigation",
		Purpose:     "confirm route owner",
	}}

	artifact, err := BuildSemanticAudit(request)
	if err != nil {
		t.Fatal(err)
	}

	if artifact.InspectionPlan.Readiness != "inspect_limited" {
		t.Fatalf("InspectionPlan.Readiness = %q, want inspect_limited", artifact.InspectionPlan.Readiness)
	}
	for _, step := range artifact.InspectionPlan.Steps {
		if step.AllowedAction != "resolve_owner_before_source_read" {
			t.Fatalf("InspectionPlan.Steps = %#v, want owner resolution before source read", artifact.InspectionPlan.Steps)
		}
		if step.PermissionLevel != "P1" {
			t.Fatalf("InspectionPlan step permission = %q, want P1", step.PermissionLevel)
		}
	}
	expansion := artifact.OwnerMissExpansion
	if expansion.MaxRadius != 1 {
		t.Fatalf("OwnerMissExpansion.MaxRadius = %d, want 1", expansion.MaxRadius)
	}
	if !hasString(expansion.AllowedTargetIDs, "environment-settings-page:route") {
		t.Fatalf("OwnerMissExpansion.AllowedTargetIDs = %#v, want route expansion target", expansion.AllowedTargetIDs)
	}
	if expansion.OnMiss != "stop_and_request_map_update_or_user_clarification" {
		t.Fatalf("OwnerMissExpansion.OnMiss = %q", expansion.OnMiss)
	}
	if !hasString(expansion.BlockedActions, "inspect_broadly") || !hasString(expansion.BlockedActions, "change") {
		t.Fatalf("OwnerMissExpansion.BlockedActions = %#v, want broad inspect and change blocked", expansion.BlockedActions)
	}
	if artifact.OwnerBundleConfidence.Summary != "owner_bundle_low" {
		t.Fatalf("OwnerBundleConfidence.Summary = %q, want owner_bundle_low", artifact.OwnerBundleConfidence.Summary)
	}
}

func TestSemanticAuditDiscoversIndexedVerificationOwnerWithoutGrantingPromotion(t *testing.T) {
	request := sampleSemanticAuditRequest()
	request.SemanticIntakeOutput.CandidateUniverse.PrimaryCandidates[0].OwnerHints = SemanticIntakeOwnerHints{
		PrimaryPaths:      []string{"desktop/src/pages/EnvironmentSettings.tsx"},
		VerificationPaths: []string{"desktop/src/pages/EnvironmentSettings.test.tsx"},
	}
	request.LiveEvidenceCapture = []SemanticAuditCapturedEvidence{{
		StepID:              "inspect-01",
		ReadPath:            "desktop/src/pages/EnvironmentSettings.tsx",
		EvidenceNeed:        "exact exception source",
		SourceKind:          "source",
		SourceRef:           "desktop/src/pages/EnvironmentSettings.tsx",
		ObservedSignal:      "H5 access exception stack enters EnvironmentSettings route guard",
		SupportsCandidateID: "environment-settings-page",
		SupportsCandidate:   true,
		EvidenceRef:         "read:desktop/src/pages/EnvironmentSettings.tsx#route-guard",
	}}

	artifact, err := BuildSemanticAudit(request)
	if err != nil {
		t.Fatal(err)
	}

	discovery := artifact.VerificationOwnerDiscovery
	if discovery.Summary != "verification_owner_indexed" {
		t.Fatalf("VerificationOwnerDiscovery.Summary = %q, want verification_owner_indexed", discovery.Summary)
	}
	if len(discovery.RequiredOwners) != 1 {
		t.Fatalf("VerificationOwnerDiscovery.RequiredOwners = %#v, want one owner", discovery.RequiredOwners)
	}
	owner := discovery.RequiredOwners[0]
	if owner.Status != "owner_indexed" {
		t.Fatalf("Verification owner status = %q, want owner_indexed", owner.Status)
	}
	if !hasString(owner.VerificationPaths, "desktop/src/pages/EnvironmentSettings.test.tsx") {
		t.Fatalf("VerificationPaths = %#v, want indexed test path", owner.VerificationPaths)
	}
	if !hasString(owner.VerificationCommandCandidates, "targeted_test:desktop/src/pages/EnvironmentSettings.test.tsx") {
		t.Fatalf("VerificationCommandCandidates = %#v, want targeted test candidate", owner.VerificationCommandCandidates)
	}
	if !discovery.PromotionBlocked || !hasString(discovery.BlockedClaims, "release_safe") {
		t.Fatalf("VerificationOwnerDiscovery = %#v, want promotion and release claims blocked until verification result", discovery)
	}
	if artifact.RerankAssessment.PermissionPromotionCandidate.Granted {
		t.Fatalf("PermissionPromotionCandidate.Granted = true, want false before verification result")
	}
}

func TestSemanticAuditReportsMissingVerificationOwner(t *testing.T) {
	request := sampleSemanticAuditRequest()
	request.SemanticIntakeOutput.CandidateUniverse.PrimaryCandidates[0].OwnerHints = SemanticIntakeOwnerHints{
		PrimaryPaths: []string{"desktop/src/pages/EnvironmentSettings.tsx"},
	}

	artifact, err := BuildSemanticAudit(request)
	if err != nil {
		t.Fatal(err)
	}

	discovery := artifact.VerificationOwnerDiscovery
	if discovery.Summary != "verification_owner_missing" {
		t.Fatalf("VerificationOwnerDiscovery.Summary = %q, want verification_owner_missing", discovery.Summary)
	}
	if len(discovery.RequiredOwners) != 1 {
		t.Fatalf("VerificationOwnerDiscovery.RequiredOwners = %#v, want one missing owner", discovery.RequiredOwners)
	}
	owner := discovery.RequiredOwners[0]
	if owner.Status != "owner_missing" {
		t.Fatalf("Verification owner status = %q, want owner_missing", owner.Status)
	}
	if !hasString(owner.BlockedBy, "verification_owner_missing") {
		t.Fatalf("Verification owner BlockedBy = %#v, want verification_owner_missing", owner.BlockedBy)
	}
	if owner.RequiredAction != "identify positive and regression verification owner" {
		t.Fatalf("RequiredAction = %q", owner.RequiredAction)
	}
	if !hasString(discovery.BlockedClaims, "fixed_claim") {
		t.Fatalf("BlockedClaims = %#v, want fixed_claim", discovery.BlockedClaims)
	}
}

func TestSemanticAuditPassedVerificationResultBuildsClaimReadinessEvidenceTrailWithoutGrantingClaim(t *testing.T) {
	request := sampleSemanticAuditRequest()
	request.SemanticIntakeOutput.CandidateUniverse.PrimaryCandidates[0].OwnerHints = SemanticIntakeOwnerHints{
		PrimaryPaths:      []string{"desktop/src/pages/EnvironmentSettings.tsx"},
		VerificationPaths: []string{"desktop/src/pages/EnvironmentSettings.test.tsx"},
	}
	request.LiveEvidenceCapture = []SemanticAuditCapturedEvidence{{
		StepID:              "inspect-01",
		ReadPath:            "desktop/src/pages/EnvironmentSettings.tsx",
		EvidenceNeed:        "exact exception source",
		SourceKind:          "source",
		SourceRef:           "desktop/src/pages/EnvironmentSettings.tsx",
		ObservedSignal:      "H5 access exception stack enters EnvironmentSettings route guard",
		SupportsCandidateID: "environment-settings-page",
		SupportsCandidate:   true,
		EvidenceRef:         "read:desktop/src/pages/EnvironmentSettings.tsx#route-guard",
	}}
	request.VerificationResults = []SemanticAuditVerificationResult{{
		CandidateID:      "environment-settings-page",
		VerificationPath: "desktop/src/pages/EnvironmentSettings.test.tsx",
		Command:          "npm test -- EnvironmentSettings.test.tsx",
		Status:           "passed",
		EvidenceRef:      "test:EnvironmentSettings.test.tsx#passed",
		Summary:          "targeted regression test passed",
	}}

	artifact, err := BuildSemanticAudit(request)
	if err != nil {
		t.Fatal(err)
	}

	if len(artifact.VerificationResults) != 1 {
		t.Fatalf("VerificationResults = %#v, want one normalized result", artifact.VerificationResults)
	}
	readiness := artifact.ClaimReadiness
	if !readiness.VerificationSatisfied {
		t.Fatalf("ClaimReadiness.VerificationSatisfied = false, want true")
	}
	if readiness.ClaimReady {
		t.Fatalf("ClaimReadiness.ClaimReady = true, want false without workflow authorization")
	}
	if readiness.ClaimStatus != "claim_candidate" {
		t.Fatalf("ClaimReadiness.ClaimStatus = %q, want claim_candidate", readiness.ClaimStatus)
	}
	if !hasString(readiness.BlockedBy, "workflow_authorization") {
		t.Fatalf("ClaimReadiness.BlockedBy = %#v, want workflow_authorization", readiness.BlockedBy)
	}
	for _, want := range []string{"read:desktop/src/pages/EnvironmentSettings.tsx#route-guard", "test:EnvironmentSettings.test.tsx#passed"} {
		if !hasString(readiness.EvidenceTrail, want) {
			t.Fatalf("ClaimReadiness.EvidenceTrail = %#v, want %q", readiness.EvidenceTrail, want)
		}
	}
}

func TestSemanticAuditVerificationResultMustMatchIndexedOwnerPath(t *testing.T) {
	request := sampleSemanticAuditRequest()
	request.SemanticIntakeOutput.CandidateUniverse.PrimaryCandidates[0].OwnerHints = SemanticIntakeOwnerHints{
		PrimaryPaths:      []string{"desktop/src/pages/EnvironmentSettings.tsx"},
		VerificationPaths: []string{"desktop/src/pages/EnvironmentSettings.test.tsx"},
	}
	request.LiveEvidenceCapture = []SemanticAuditCapturedEvidence{{
		StepID:              "inspect-01",
		ReadPath:            "desktop/src/pages/EnvironmentSettings.tsx",
		EvidenceNeed:        "exact exception source",
		SourceKind:          "source",
		SourceRef:           "desktop/src/pages/EnvironmentSettings.tsx",
		ObservedSignal:      "H5 access exception stack enters EnvironmentSettings route guard",
		SupportsCandidateID: "environment-settings-page",
		SupportsCandidate:   true,
		EvidenceRef:         "read:desktop/src/pages/EnvironmentSettings.tsx#route-guard",
	}}
	request.VerificationResults = []SemanticAuditVerificationResult{{
		CandidateID:      "environment-settings-page",
		VerificationPath: "desktop/src/pages/Unrelated.test.tsx",
		Command:          "npm test -- Unrelated.test.tsx",
		Status:           "passed",
		EvidenceRef:      "test:Unrelated.test.tsx#passed",
		Summary:          "unrelated test passed",
	}}

	artifact, err := BuildSemanticAudit(request)
	if err != nil {
		t.Fatal(err)
	}

	readiness := artifact.ClaimReadiness
	if readiness.VerificationSatisfied {
		t.Fatalf("ClaimReadiness.VerificationSatisfied = true, want false for unmatched verification path")
	}
	if readiness.ClaimStatus != "claim_blocked" {
		t.Fatalf("ClaimReadiness.ClaimStatus = %q, want claim_blocked", readiness.ClaimStatus)
	}
	if !hasString(readiness.BlockedBy, "verification_owner_match_required") {
		t.Fatalf("ClaimReadiness.BlockedBy = %#v, want verification_owner_match_required", readiness.BlockedBy)
	}
}

func TestSemanticAuditPartialVerificationOwnershipBlocksClaimReadiness(t *testing.T) {
	request := sampleSemanticAuditRequest()
	request.SemanticIntakeOutput.CandidateUniverse.PrimaryCandidates = append(request.SemanticIntakeOutput.CandidateUniverse.PrimaryCandidates, SemanticIntakeCandidate{
		ID:           "h5-client-shell",
		Labels:       []string{"H5 Client Shell"},
		SurfaceType:  "client_surface",
		Score:        8,
		EvidenceRank: "E2",
		FacetCoverage: SemanticIntakeFacetCoverage{
			Covered: []string{"H5 client"},
		},
		OwnerHints: SemanticIntakeOwnerHints{
			PrimaryPaths: []string{"desktop/src/h5/ClientShell.tsx"},
		},
	})
	request.RouteDecision.SelectedCandidateIDs = []string{"environment-settings-page", "h5-client-shell"}
	request.SemanticIntakeOutput.CandidateUniverse.PrimaryCandidates[0].OwnerHints = SemanticIntakeOwnerHints{
		PrimaryPaths:      []string{"desktop/src/pages/EnvironmentSettings.tsx"},
		VerificationPaths: []string{"desktop/src/pages/EnvironmentSettings.test.tsx"},
	}
	request.LiveEvidenceCapture = []SemanticAuditCapturedEvidence{
		{
			StepID:              "inspect-01",
			ReadPath:            "desktop/src/pages/EnvironmentSettings.tsx",
			EvidenceNeed:        "exact exception source",
			SourceKind:          "source",
			SourceRef:           "desktop/src/pages/EnvironmentSettings.tsx",
			ObservedSignal:      "H5 access exception stack enters EnvironmentSettings route guard",
			SupportsCandidateID: "environment-settings-page",
			SupportsCandidate:   true,
			EvidenceRef:         "read:desktop/src/pages/EnvironmentSettings.tsx#route-guard",
		},
	}
	request.VerificationResults = []SemanticAuditVerificationResult{{
		CandidateID:      "environment-settings-page",
		VerificationPath: "desktop/src/pages/EnvironmentSettings.test.tsx",
		Command:          "npm test -- EnvironmentSettings.test.tsx",
		Status:           "passed",
		EvidenceRef:      "test:EnvironmentSettings.test.tsx#passed",
		Summary:          "targeted regression test passed",
	}}

	artifact, err := BuildSemanticAudit(request)
	if err != nil {
		t.Fatal(err)
	}

	if artifact.VerificationOwnerDiscovery.Summary != "verification_owner_partial" {
		t.Fatalf("VerificationOwnerDiscovery.Summary = %q, want verification_owner_partial", artifact.VerificationOwnerDiscovery.Summary)
	}
	readiness := artifact.ClaimReadiness
	if readiness.VerificationSatisfied {
		t.Fatalf("ClaimReadiness.VerificationSatisfied = true, want false with partial verification ownership")
	}
	if readiness.ClaimStatus != "claim_blocked" {
		t.Fatalf("ClaimReadiness.ClaimStatus = %q, want claim_blocked", readiness.ClaimStatus)
	}
	if !hasString(readiness.BlockedBy, "verification_owner_missing") {
		t.Fatalf("ClaimReadiness.BlockedBy = %#v, want verification_owner_missing", readiness.BlockedBy)
	}
}

func TestSemanticAuditLaterPassedVerificationResultCanSatisfyAfterEarlierFailure(t *testing.T) {
	request := sampleSemanticAuditRequest()
	request.SemanticIntakeOutput.CandidateUniverse.PrimaryCandidates[0].OwnerHints = SemanticIntakeOwnerHints{
		PrimaryPaths:      []string{"desktop/src/pages/EnvironmentSettings.tsx"},
		VerificationPaths: []string{"desktop/src/pages/EnvironmentSettings.test.tsx"},
	}
	request.LiveEvidenceCapture = []SemanticAuditCapturedEvidence{{
		StepID:              "inspect-01",
		ReadPath:            "desktop/src/pages/EnvironmentSettings.tsx",
		EvidenceNeed:        "exact exception source",
		SourceKind:          "source",
		SourceRef:           "desktop/src/pages/EnvironmentSettings.tsx",
		ObservedSignal:      "H5 access exception stack enters EnvironmentSettings route guard",
		SupportsCandidateID: "environment-settings-page",
		SupportsCandidate:   true,
		EvidenceRef:         "read:desktop/src/pages/EnvironmentSettings.tsx#route-guard",
	}}
	request.VerificationResults = []SemanticAuditVerificationResult{
		{
			CandidateID:      "environment-settings-page",
			VerificationPath: "desktop/src/pages/EnvironmentSettings.test.tsx",
			Command:          "npm test -- EnvironmentSettings.test.tsx",
			Status:           "failed",
			EvidenceRef:      "test:EnvironmentSettings.test.tsx#failed",
			Summary:          "first targeted test run failed",
		},
		{
			CandidateID:      "environment-settings-page",
			VerificationPath: "desktop/src/pages/EnvironmentSettings.test.tsx",
			Command:          "npm test -- EnvironmentSettings.test.tsx",
			Status:           "passed",
			EvidenceRef:      "test:EnvironmentSettings.test.tsx#passed",
			Summary:          "rerun targeted test passed",
		},
	}

	artifact, err := BuildSemanticAudit(request)
	if err != nil {
		t.Fatal(err)
	}

	readiness := artifact.ClaimReadiness
	if !readiness.VerificationSatisfied {
		t.Fatalf("ClaimReadiness.VerificationSatisfied = false, want true after later passed result")
	}
	if !hasString(readiness.EvidenceTrail, "test:EnvironmentSettings.test.tsx#passed") {
		t.Fatalf("ClaimReadiness.EvidenceTrail = %#v, want passed verification evidence", readiness.EvidenceTrail)
	}
	if hasString(readiness.BlockedBy, "verification_result_pass_required") {
		t.Fatalf("ClaimReadiness.BlockedBy = %#v, did not expect verification_result_pass_required", readiness.BlockedBy)
	}
}

func TestSemanticAuditFailedVerificationResultUsesFailedBlocker(t *testing.T) {
	request := sampleVerifiedSemanticAuditRequest()
	request.VerificationResults = []SemanticAuditVerificationResult{{
		CandidateID:      "environment-settings-page",
		VerificationPath: "desktop/src/pages/EnvironmentSettings.test.tsx",
		Command:          "npm test -- EnvironmentSettings.test.tsx",
		Status:           "failed",
		EvidenceRef:      "test:EnvironmentSettings.test.tsx#failed",
		Summary:          "targeted regression test failed",
	}}

	artifact, err := BuildSemanticAudit(request)
	if err != nil {
		t.Fatal(err)
	}

	readiness := artifact.ClaimReadiness
	if readiness.VerificationSatisfied {
		t.Fatalf("ClaimReadiness.VerificationSatisfied = true, want false with failed verification")
	}
	if readiness.ClaimReady {
		t.Fatalf("ClaimReadiness.ClaimReady = true, want false with failed verification")
	}
	if !hasString(readiness.BlockedBy, "verification_result_failed") {
		t.Fatalf("ClaimReadiness.BlockedBy = %#v, want verification_result_failed", readiness.BlockedBy)
	}
	if hasString(readiness.BlockedBy, "verification_result_pass_required") {
		t.Fatalf("ClaimReadiness.BlockedBy = %#v, did not expect generic pass-required blocker for failed verification", readiness.BlockedBy)
	}
}

func TestSemanticAuditBlockedVerificationResultUsesBlockedBlocker(t *testing.T) {
	request := sampleVerifiedSemanticAuditRequest()
	request.VerificationResults = []SemanticAuditVerificationResult{{
		CandidateID:      "environment-settings-page",
		VerificationPath: "desktop/src/pages/EnvironmentSettings.test.tsx",
		Command:          "npm test -- EnvironmentSettings.test.tsx",
		Status:           "blocked",
		EvidenceRef:      "test:EnvironmentSettings.test.tsx#blocked",
		Summary:          "targeted regression test could not run because the test server was unavailable",
	}}

	artifact, err := BuildSemanticAudit(request)
	if err != nil {
		t.Fatal(err)
	}

	readiness := artifact.ClaimReadiness
	if readiness.VerificationSatisfied {
		t.Fatalf("ClaimReadiness.VerificationSatisfied = true, want false with blocked verification")
	}
	if !hasString(readiness.BlockedBy, "verification_result_blocked") {
		t.Fatalf("ClaimReadiness.BlockedBy = %#v, want verification_result_blocked", readiness.BlockedBy)
	}
}

func TestSemanticAuditInconclusiveVerificationResultUsesInconclusiveBlocker(t *testing.T) {
	request := sampleVerifiedSemanticAuditRequest()
	request.VerificationResults = []SemanticAuditVerificationResult{{
		CandidateID:      "environment-settings-page",
		VerificationPath: "desktop/src/pages/EnvironmentSettings.test.tsx",
		Command:          "npm test -- EnvironmentSettings.test.tsx",
		Status:           "skipped",
		EvidenceRef:      "test:EnvironmentSettings.test.tsx#skipped",
		Summary:          "targeted regression test was skipped",
	}}

	artifact, err := BuildSemanticAudit(request)
	if err != nil {
		t.Fatal(err)
	}

	readiness := artifact.ClaimReadiness
	if readiness.VerificationSatisfied {
		t.Fatalf("ClaimReadiness.VerificationSatisfied = true, want false with skipped verification")
	}
	if !hasString(readiness.BlockedBy, "verification_result_inconclusive") {
		t.Fatalf("ClaimReadiness.BlockedBy = %#v, want verification_result_inconclusive", readiness.BlockedBy)
	}
}

func TestSemanticAuditLaterPassedVerificationResultCanSatisfyAfterEarlierBlocked(t *testing.T) {
	request := sampleVerifiedSemanticAuditRequest()
	request.VerificationResults = []SemanticAuditVerificationResult{
		{
			CandidateID:      "environment-settings-page",
			VerificationPath: "desktop/src/pages/EnvironmentSettings.test.tsx",
			Command:          "npm test -- EnvironmentSettings.test.tsx",
			Status:           "blocked",
			EvidenceRef:      "test:EnvironmentSettings.test.tsx#blocked",
			Summary:          "targeted regression test was blocked by unavailable service",
		},
		{
			CandidateID:      "environment-settings-page",
			VerificationPath: "desktop/src/pages/EnvironmentSettings.test.tsx",
			Command:          "npm test -- EnvironmentSettings.test.tsx",
			Status:           "passed",
			EvidenceRef:      "test:EnvironmentSettings.test.tsx#passed",
			Summary:          "rerun targeted regression test passed",
		},
	}

	artifact, err := BuildSemanticAudit(request)
	if err != nil {
		t.Fatal(err)
	}

	readiness := artifact.ClaimReadiness
	if !readiness.VerificationSatisfied {
		t.Fatalf("ClaimReadiness.VerificationSatisfied = false, want true after later passed result")
	}
	if hasString(readiness.BlockedBy, "verification_result_blocked") {
		t.Fatalf("ClaimReadiness.BlockedBy = %#v, did not expect stale blocked result to keep claim blocked", readiness.BlockedBy)
	}
	if !hasString(readiness.EvidenceTrail, "test:EnvironmentSettings.test.tsx#passed") {
		t.Fatalf("ClaimReadiness.EvidenceTrail = %#v, want latest passed verification evidence", readiness.EvidenceTrail)
	}
}

func TestSemanticAuditLaterFailedVerificationResultBlocksAfterEarlierPassed(t *testing.T) {
	request := sampleVerifiedSemanticAuditRequest()
	request.VerificationResults = []SemanticAuditVerificationResult{
		{
			CandidateID:      "environment-settings-page",
			VerificationPath: "desktop/src/pages/EnvironmentSettings.test.tsx",
			Command:          "npm test -- EnvironmentSettings.test.tsx",
			Status:           "passed",
			EvidenceRef:      "test:EnvironmentSettings.test.tsx#passed",
			Summary:          "first targeted regression test passed",
		},
		{
			CandidateID:      "environment-settings-page",
			VerificationPath: "desktop/src/pages/EnvironmentSettings.test.tsx",
			Command:          "npm test -- EnvironmentSettings.test.tsx",
			Status:           "failed",
			EvidenceRef:      "test:EnvironmentSettings.test.tsx#failed",
			Summary:          "later targeted regression test failed",
		},
	}

	artifact, err := BuildSemanticAudit(request)
	if err != nil {
		t.Fatal(err)
	}

	readiness := artifact.ClaimReadiness
	if readiness.VerificationSatisfied {
		t.Fatalf("ClaimReadiness.VerificationSatisfied = true, want false after later failed result")
	}
	if !hasString(readiness.BlockedBy, "verification_result_failed") {
		t.Fatalf("ClaimReadiness.BlockedBy = %#v, want verification_result_failed", readiness.BlockedBy)
	}
}

func TestSemanticAuditVerificationResultCapturedAtCanOverrideArrayOrder(t *testing.T) {
	request := sampleVerifiedSemanticAuditRequest()
	request.VerificationResults = []SemanticAuditVerificationResult{
		{
			CandidateID:      "environment-settings-page",
			VerificationPath: "desktop/src/pages/EnvironmentSettings.test.tsx",
			Command:          "npm test -- EnvironmentSettings.test.tsx",
			Status:           "passed",
			EvidenceRef:      "test:EnvironmentSettings.test.tsx#passed",
			CapturedAt:       "2026-06-25T12:30:00Z",
			Summary:          "newer targeted regression test passed",
		},
		{
			CandidateID:      "environment-settings-page",
			VerificationPath: "desktop/src/pages/EnvironmentSettings.test.tsx",
			Command:          "npm test -- EnvironmentSettings.test.tsx",
			Status:           "failed",
			EvidenceRef:      "test:EnvironmentSettings.test.tsx#failed",
			CapturedAt:       "2026-06-25T12:00:00Z",
			Summary:          "older targeted regression test failed",
		},
	}

	artifact, err := BuildSemanticAudit(request)
	if err != nil {
		t.Fatal(err)
	}

	readiness := artifact.ClaimReadiness
	if !readiness.VerificationSatisfied {
		t.Fatalf("ClaimReadiness.VerificationSatisfied = false, want true when newer captured_at result passed")
	}
	if hasString(readiness.BlockedBy, "verification_result_failed") {
		t.Fatalf("ClaimReadiness.BlockedBy = %#v, did not expect older failed result to keep claim blocked", readiness.BlockedBy)
	}
	if !hasString(readiness.EvidenceTrail, "test:EnvironmentSettings.test.tsx#passed") {
		t.Fatalf("ClaimReadiness.EvidenceTrail = %#v, want newer passed verification evidence", readiness.EvidenceTrail)
	}
}

func TestSemanticAuditWorkflowAuthorizationCanMakeRootCauseClaimReady(t *testing.T) {
	request := sampleVerifiedSemanticAuditRequest()
	request.WorkContract.WorkflowIntent = "debug"
	request.WorkflowAuthorization = SemanticAuditWorkflowAuthorization{
		WorkflowIntent:   "debug",
		Status:           "authorized",
		AuthorizedClaims: []string{"root_cause_claim"},
		AuthorizationRef: "workflow:debug#root-cause-reviewed",
		Reason:           "debug workflow reviewed bounded evidence and matching verification",
	}

	artifact, err := BuildSemanticAudit(request)
	if err != nil {
		t.Fatal(err)
	}

	readiness := artifact.ClaimReadiness
	if !readiness.ClaimReady {
		t.Fatalf("ClaimReadiness.ClaimReady = false, want true with root-cause workflow authorization")
	}
	if readiness.ClaimStatus != "claim_ready" {
		t.Fatalf("ClaimReadiness.ClaimStatus = %q, want claim_ready", readiness.ClaimStatus)
	}
	if readiness.ClaimType != "root_cause_claim" {
		t.Fatalf("ClaimReadiness.ClaimType = %q, want root_cause_claim", readiness.ClaimType)
	}
	if readiness.PromotionBlocked {
		t.Fatalf("ClaimReadiness.PromotionBlocked = true, want false after workflow authorization")
	}
	if hasString(readiness.BlockedBy, "workflow_authorization") {
		t.Fatalf("ClaimReadiness.BlockedBy = %#v, did not expect workflow_authorization", readiness.BlockedBy)
	}
	if !hasString(readiness.EvidenceTrail, "workflow:debug#root-cause-reviewed") {
		t.Fatalf("ClaimReadiness.EvidenceTrail = %#v, want workflow authorization ref", readiness.EvidenceTrail)
	}
	if artifact.RerankAssessment.PermissionPromotionCandidate.Granted {
		t.Fatalf("PermissionPromotionCandidate.Granted = true, want false; workflow authorization affects claim readiness only")
	}
	if artifact.PermissionDecision.AllowedLevel != "P2" {
		t.Fatalf("PermissionDecision.AllowedLevel = %q, want P2", artifact.PermissionDecision.AllowedLevel)
	}
}

func TestSemanticAuditResumeValidationPassesFreshState(t *testing.T) {
	request := sampleRootCauseReadySemanticAuditRequest()
	artifact, err := BuildSemanticAudit(request)
	if err != nil {
		t.Fatal(err)
	}
	resume := SemanticAuditResumeRequest{
		Version:             1,
		SemanticAuditInput:  request,
		SemanticAuditOutput: artifact,
		SemanticAuditState: SemanticAuditResumeState{
			SemanticAuditInputPath:        "<WORKFLOW_STATE_DIR>/semantic-audit-input.json",
			SemanticAuditOutputPath:       "<WORKFLOW_STATE_DIR>/semantic-audit-output.json",
			SemanticAuditRouteFingerprint: SemanticAuditResumeRouteFingerprint(request.RouteDecision.SelectedCandidateIDs, "root_cause_claim"),
			ActiveClaimType:               "root_cause_claim",
			SelectedCandidateIDs:          []string{"environment-settings-page"},
			ClaimAuthorizationRefs:        []string{"workflow:debug#root-cause-reviewed"},
			ClaimVerificationRefs:         []string{"test:EnvironmentSettings.test.tsx#passed"},
		},
	}

	validation, err := ValidateSemanticAuditResume(resume)
	if err != nil {
		t.Fatal(err)
	}

	if validation.SemanticAuditGeneratedResumeSmoke != "passed" {
		t.Fatalf("SemanticAuditGeneratedResumeSmoke = %q, want passed", validation.SemanticAuditGeneratedResumeSmoke)
	}
	if validation.SemanticAuditResumeStatus != "fresh" {
		t.Fatalf("SemanticAuditResumeStatus = %q, want fresh", validation.SemanticAuditResumeStatus)
	}
	if validation.Validator != "semantic-audit-resume" {
		t.Fatalf("Validator = %q, want semantic-audit-resume", validation.Validator)
	}
	if !validation.ClaimReadyAllowed {
		t.Fatalf("ClaimReadyAllowed = false, want true")
	}
	if !validation.CanReusePersistedClaimReadiness {
		t.Fatalf("CanReusePersistedClaimReadiness = false, want true")
	}
	if validation.PermissionPromotionGranted {
		t.Fatalf("PermissionPromotionGranted = true, want false")
	}
	if validation.GrantsPermission {
		t.Fatalf("GrantsPermission = true, want false")
	}
	if validation.Boundary != "comparison_only_no_source_edit_or_claim_authorization" {
		t.Fatalf("Boundary = %q, want comparison_only_no_source_edit_or_claim_authorization", validation.Boundary)
	}
	if !hasString(validation.SemanticAuditStaleReasons, "none") {
		t.Fatalf("SemanticAuditStaleReasons = %#v, want none", validation.SemanticAuditStaleReasons)
	}
}

func TestSemanticAuditResumeValidationBlocksRouteDrift(t *testing.T) {
	request := sampleRootCauseReadySemanticAuditRequest()
	artifact, err := BuildSemanticAudit(request)
	if err != nil {
		t.Fatal(err)
	}
	resume := SemanticAuditResumeRequest{
		Version:             1,
		SemanticAuditInput:  request,
		SemanticAuditOutput: artifact,
		SemanticAuditState: SemanticAuditResumeState{
			SemanticAuditInputPath:        "<WORKFLOW_STATE_DIR>/semantic-audit-input.json",
			SemanticAuditOutputPath:       "<WORKFLOW_STATE_DIR>/semantic-audit-output.json",
			SemanticAuditRouteFingerprint: SemanticAuditResumeRouteFingerprint([]string{"env-config"}, "root_cause_claim"),
			ActiveClaimType:               "root_cause_claim",
			SelectedCandidateIDs:          []string{"env-config"},
			ClaimAuthorizationRefs:        []string{"workflow:debug#root-cause-reviewed"},
			ClaimVerificationRefs:         []string{"test:EnvironmentSettings.test.tsx#passed"},
		},
	}

	validation, err := ValidateSemanticAuditResume(resume)
	if err != nil {
		t.Fatal(err)
	}

	if validation.SemanticAuditGeneratedResumeSmoke != "failed" {
		t.Fatalf("SemanticAuditGeneratedResumeSmoke = %q, want failed", validation.SemanticAuditGeneratedResumeSmoke)
	}
	if validation.SemanticAuditResumeStatus != "needs-rerun" {
		t.Fatalf("SemanticAuditResumeStatus = %q, want needs-rerun", validation.SemanticAuditResumeStatus)
	}
	if validation.ClaimReadyAllowed {
		t.Fatalf("ClaimReadyAllowed = true, want false after route drift")
	}
	if validation.CanReusePersistedClaimReadiness {
		t.Fatalf("CanReusePersistedClaimReadiness = true, want false after route drift")
	}
	if validation.GrantsPermission {
		t.Fatalf("GrantsPermission = true, want false")
	}
	if !hasString(validation.SemanticAuditStaleReasons, "route-changed") {
		t.Fatalf("SemanticAuditStaleReasons = %#v, want route-changed", validation.SemanticAuditStaleReasons)
	}
	if validation.RequiredAction != "rebuild_semantic_audit_input" {
		t.Fatalf("RequiredAction = %q, want rebuild_semantic_audit_input", validation.RequiredAction)
	}
}

func TestSemanticAuditWorkflowAuthorizationRequiresClaimSpecificVerificationForFixedClaim(t *testing.T) {
	request := sampleVerifiedSemanticAuditRequest()
	request.WorkContract.WorkflowIntent = "implement"
	request.WorkflowAuthorization = SemanticAuditWorkflowAuthorization{
		WorkflowIntent:   "implement",
		Status:           "authorized",
		AuthorizedClaims: []string{"fixed_claim"},
		AuthorizationRef: "workflow:implement#verified-task-complete",
		Reason:           "implementation workflow completed required verification",
	}

	artifact, err := BuildSemanticAudit(request)
	if err != nil {
		t.Fatal(err)
	}

	readiness := artifact.ClaimReadiness
	if readiness.ClaimReady {
		t.Fatalf("ClaimReadiness.ClaimReady = true, want false for debug fixed claim")
	}
	if readiness.ClaimStatus != "claim_candidate" {
		t.Fatalf("ClaimReadiness.ClaimStatus = %q, want claim_candidate", readiness.ClaimStatus)
	}
	if !hasString(readiness.BlockedBy, "claim_specific_verification_required") {
		t.Fatalf("ClaimReadiness.BlockedBy = %#v, want claim_specific_verification_required", readiness.BlockedBy)
	}
	if readiness.ClaimType != "fixed_claim" {
		t.Fatalf("ClaimReadiness.ClaimType = %q, want fixed_claim as unsupported attempted claim", readiness.ClaimType)
	}
}

func TestSemanticAuditWorkflowAuthorizationDoesNotReuseFixedVerificationForCompletedClaim(t *testing.T) {
	request := sampleVerifiedSemanticAuditRequest()
	request.WorkContract.WorkflowIntent = "implement"
	request.VerificationResults[0].ClaimTypes = []string{"fixed_claim"}
	request.WorkflowAuthorization = SemanticAuditWorkflowAuthorization{
		WorkflowIntent:   "implement",
		Status:           "authorized",
		AuthorizedClaims: []string{"completed_claim"},
		AuthorizationRef: "workflow:implement#completed-reviewed",
		Reason:           "completed claim must have completed verification",
		ClaimAuthorizations: []SemanticAuditClaimAuthorization{{
			ClaimType:                "completed_claim",
			Status:                   "authorized",
			AuthorizationRef:         "workflow:implement#completed-reviewed",
			VerificationEvidenceRefs: []string{request.VerificationResults[0].EvidenceRef},
		}},
	}

	artifact, err := BuildSemanticAudit(request)
	if err != nil {
		t.Fatal(err)
	}

	readiness := artifact.ClaimReadiness
	if readiness.ClaimReady {
		t.Fatalf("ClaimReadiness.ClaimReady = true, want false when fixed verification is reused for completed claim")
	}
	if readiness.ClaimType != "completed_claim" {
		t.Fatalf("ClaimReadiness.ClaimType = %q, want completed_claim", readiness.ClaimType)
	}
	if !hasString(readiness.BlockedBy, "claim_specific_verification_required") {
		t.Fatalf("ClaimReadiness.BlockedBy = %#v, want claim_specific_verification_required", readiness.BlockedBy)
	}
}

func TestSemanticAuditWorkflowAuthorizationCanMakeClaimTypedFinalClaimsReady(t *testing.T) {
	for _, claimType := range []string{"fixed_claim", "completed_claim", "release_safe"} {
		t.Run(claimType, func(t *testing.T) {
			request := sampleVerifiedSemanticAuditRequest()
			request.WorkContract.WorkflowIntent = "implement"
			request.VerificationResults[0].ClaimTypes = []string{claimType}
			verificationRef := request.VerificationResults[0].EvidenceRef
			request.WorkflowAuthorization = SemanticAuditWorkflowAuthorization{
				WorkflowIntent:   "implement",
				Status:           "authorized",
				AuthorizedClaims: []string{claimType},
				AuthorizationRef: "workflow:implement#" + claimType + "-reviewed",
				Reason:           "workflow reviewed claim-specific verification",
				ClaimAuthorizations: []SemanticAuditClaimAuthorization{{
					ClaimType:                claimType,
					Status:                   "authorized",
					AuthorizationRef:         "workflow:implement#" + claimType + "-reviewed",
					VerificationEvidenceRefs: []string{verificationRef},
					Reason:                   "workflow reviewed claim-specific verification",
				}},
			}

			artifact, err := BuildSemanticAudit(request)
			if err != nil {
				t.Fatal(err)
			}

			readiness := artifact.ClaimReadiness
			if !readiness.ClaimReady {
				t.Fatalf("ClaimReadiness.ClaimReady = false, want true for %s with claim-specific verification", claimType)
			}
			if readiness.ClaimStatus != "claim_ready" {
				t.Fatalf("ClaimReadiness.ClaimStatus = %q, want claim_ready", readiness.ClaimStatus)
			}
			if readiness.ClaimType != claimType {
				t.Fatalf("ClaimReadiness.ClaimType = %q, want %s", readiness.ClaimType, claimType)
			}
			if !hasString(readiness.ClaimVerificationRefs, verificationRef) {
				t.Fatalf("ClaimReadiness.ClaimVerificationRefs = %#v, want %s", readiness.ClaimVerificationRefs, verificationRef)
			}
			if hasString(readiness.BlockedBy, "claim_specific_verification_required") {
				t.Fatalf("ClaimReadiness.BlockedBy = %#v, did not expect claim_specific_verification_required", readiness.BlockedBy)
			}
			if artifact.RerankAssessment.PermissionPromotionCandidate.Granted {
				t.Fatalf("PermissionPromotionCandidate.Granted = true, want false; workflow authorization affects claim readiness only")
			}
			if artifact.PermissionDecision.AllowedLevel != "P2" {
				t.Fatalf("PermissionDecision.AllowedLevel = %q, want P2", artifact.PermissionDecision.AllowedLevel)
			}
		})
	}
}

func TestSemanticAuditWorkflowAuthorizationRequiresActiveClaimForMultipleAuthorizedClaims(t *testing.T) {
	request := sampleVerifiedSemanticAuditRequest()
	request.WorkContract.WorkflowIntent = "implement"
	request.VerificationResults[0].ClaimTypes = []string{"fixed_claim", "completed_claim"}
	verificationRef := request.VerificationResults[0].EvidenceRef
	request.WorkflowAuthorization = SemanticAuditWorkflowAuthorization{
		WorkflowIntent:   "implement",
		Status:           "authorized",
		AuthorizedClaims: []string{"fixed_claim", "completed_claim"},
		Reason:           "workflow authorized multiple claim types but did not choose the active claim",
		ClaimAuthorizations: []SemanticAuditClaimAuthorization{
			{
				ClaimType:                "fixed_claim",
				Status:                   "authorized",
				AuthorizationRef:         "workflow:implement#fixed-reviewed",
				VerificationEvidenceRefs: []string{verificationRef},
			},
			{
				ClaimType:                "completed_claim",
				Status:                   "authorized",
				AuthorizationRef:         "workflow:implement#completed-reviewed",
				VerificationEvidenceRefs: []string{verificationRef},
			},
		},
	}

	artifact, err := BuildSemanticAudit(request)
	if err != nil {
		t.Fatal(err)
	}

	readiness := artifact.ClaimReadiness
	if readiness.ClaimReady {
		t.Fatalf("ClaimReadiness.ClaimReady = true, want false when multiple authorized claims lack active_claim_type")
	}
	if readiness.ClaimType != "" {
		t.Fatalf("ClaimReadiness.ClaimType = %q, want empty claim type without explicit active claim", readiness.ClaimType)
	}
	if !hasString(readiness.BlockedBy, "active_claim_type_required") {
		t.Fatalf("ClaimReadiness.BlockedBy = %#v, want active_claim_type_required", readiness.BlockedBy)
	}
}

func TestSemanticAuditWorkflowAuthorizationUsesExplicitActiveClaim(t *testing.T) {
	request := sampleVerifiedSemanticAuditRequest()
	request.WorkContract.WorkflowIntent = "implement"
	request.VerificationResults[0].ClaimTypes = []string{"fixed_claim", "completed_claim"}
	verificationRef := request.VerificationResults[0].EvidenceRef
	request.WorkflowAuthorization = SemanticAuditWorkflowAuthorization{
		WorkflowIntent:   "implement",
		Status:           "authorized",
		AuthorizedClaims: []string{"fixed_claim", "completed_claim"},
		ActiveClaimType:  "completed_claim",
		Reason:           "workflow selected completed_claim as the active final claim",
		ClaimAuthorizations: []SemanticAuditClaimAuthorization{
			{
				ClaimType:                "fixed_claim",
				Status:                   "authorized",
				AuthorizationRef:         "workflow:implement#fixed-reviewed",
				VerificationEvidenceRefs: []string{verificationRef},
			},
			{
				ClaimType:                "completed_claim",
				Status:                   "authorized",
				AuthorizationRef:         "workflow:implement#completed-reviewed",
				VerificationEvidenceRefs: []string{verificationRef},
			},
		},
	}

	artifact, err := BuildSemanticAudit(request)
	if err != nil {
		t.Fatal(err)
	}

	readiness := artifact.ClaimReadiness
	if !readiness.ClaimReady {
		t.Fatalf("ClaimReadiness.ClaimReady = false, want true with explicit active claim")
	}
	if readiness.ClaimType != "completed_claim" {
		t.Fatalf("ClaimReadiness.ClaimType = %q, want completed_claim", readiness.ClaimType)
	}
	if !hasString(readiness.EvidenceTrail, "workflow:implement#completed-reviewed") {
		t.Fatalf("ClaimReadiness.EvidenceTrail = %#v, want completed authorization ref", readiness.EvidenceTrail)
	}
	if hasString(readiness.EvidenceTrail, "workflow:implement#fixed-reviewed") {
		t.Fatalf("ClaimReadiness.EvidenceTrail = %#v, did not expect inactive fixed authorization ref", readiness.EvidenceTrail)
	}
}

func TestSemanticAuditWorkflowAuthorizationBlocksUnauthorizedActiveClaim(t *testing.T) {
	request := sampleVerifiedSemanticAuditRequest()
	request.WorkContract.WorkflowIntent = "implement"
	request.VerificationResults[0].ClaimTypes = []string{"fixed_claim", "completed_claim"}
	verificationRef := request.VerificationResults[0].EvidenceRef
	request.WorkflowAuthorization = SemanticAuditWorkflowAuthorization{
		WorkflowIntent:   "implement",
		Status:           "authorized",
		AuthorizedClaims: []string{"fixed_claim"},
		ActiveClaimType:  "completed_claim",
		Reason:           "workflow selected a claim that is not authorized",
		ClaimAuthorizations: []SemanticAuditClaimAuthorization{{
			ClaimType:                "completed_claim",
			Status:                   "authorized",
			AuthorizationRef:         "workflow:implement#completed-reviewed",
			VerificationEvidenceRefs: []string{verificationRef},
		}},
	}

	artifact, err := BuildSemanticAudit(request)
	if err != nil {
		t.Fatal(err)
	}

	readiness := artifact.ClaimReadiness
	if readiness.ClaimReady {
		t.Fatalf("ClaimReadiness.ClaimReady = true, want false when active claim is not listed in authorized_claims")
	}
	if readiness.ClaimType != "completed_claim" {
		t.Fatalf("ClaimReadiness.ClaimType = %q, want attempted completed_claim", readiness.ClaimType)
	}
	if !hasString(readiness.BlockedBy, "active_claim_not_authorized") {
		t.Fatalf("ClaimReadiness.BlockedBy = %#v, want active_claim_not_authorized", readiness.BlockedBy)
	}
}

func TestSemanticAuditWorkflowAuthorizationRequiresClaimAuthorizationForFinalClaims(t *testing.T) {
	request := sampleVerifiedSemanticAuditRequest()
	request.WorkContract.WorkflowIntent = "implement"
	request.VerificationResults[0].ClaimTypes = []string{"fixed_claim"}
	request.WorkflowAuthorization = SemanticAuditWorkflowAuthorization{
		WorkflowIntent:   "implement",
		Status:           "authorized",
		AuthorizedClaims: []string{"fixed_claim"},
		AuthorizationRef: "workflow:implement#fixed-reviewed",
		Reason:           "top-level authorization is not enough for fixed claims",
	}

	artifact, err := BuildSemanticAudit(request)
	if err != nil {
		t.Fatal(err)
	}

	readiness := artifact.ClaimReadiness
	if readiness.ClaimReady {
		t.Fatalf("ClaimReadiness.ClaimReady = true, want false without claim_authorizations entry")
	}
	if readiness.ClaimType != "fixed_claim" {
		t.Fatalf("ClaimReadiness.ClaimType = %q, want fixed_claim", readiness.ClaimType)
	}
	if !hasString(readiness.BlockedBy, "claim_authorization_required") {
		t.Fatalf("ClaimReadiness.BlockedBy = %#v, want claim_authorization_required", readiness.BlockedBy)
	}
}

func TestSemanticAuditWorkflowAuthorizationFinalClaimUsesClaimAuthorizationRef(t *testing.T) {
	request := sampleVerifiedSemanticAuditRequest()
	request.WorkContract.WorkflowIntent = "implement"
	request.VerificationResults[0].ClaimTypes = []string{"fixed_claim"}
	request.WorkflowAuthorization = SemanticAuditWorkflowAuthorization{
		WorkflowIntent:   "implement",
		Status:           "authorized",
		AuthorizedClaims: []string{"fixed_claim"},
		Reason:           "claim-specific authorization carries its own ref",
		ClaimAuthorizations: []SemanticAuditClaimAuthorization{{
			ClaimType:                "fixed_claim",
			Status:                   "authorized",
			AuthorizationRef:         "workflow:implement#fixed-reviewed",
			VerificationEvidenceRefs: []string{request.VerificationResults[0].EvidenceRef},
		}},
	}

	artifact, err := BuildSemanticAudit(request)
	if err != nil {
		t.Fatal(err)
	}

	readiness := artifact.ClaimReadiness
	if !readiness.ClaimReady {
		t.Fatalf("ClaimReadiness.ClaimReady = false, want true when claim_authorizations has authorization_ref")
	}
	if !hasString(readiness.EvidenceTrail, "workflow:implement#fixed-reviewed") {
		t.Fatalf("ClaimReadiness.EvidenceTrail = %#v, want claim-specific authorization ref", readiness.EvidenceTrail)
	}
}

func TestSemanticAuditWorkflowAuthorizationRequiresClaimAuthorizationRefForFinalClaims(t *testing.T) {
	request := sampleVerifiedSemanticAuditRequest()
	request.WorkContract.WorkflowIntent = "implement"
	request.VerificationResults[0].ClaimTypes = []string{"completed_claim"}
	request.WorkflowAuthorization = SemanticAuditWorkflowAuthorization{
		WorkflowIntent:   "implement",
		Status:           "authorized",
		AuthorizedClaims: []string{"completed_claim"},
		AuthorizationRef: "workflow:implement#completed-reviewed",
		Reason:           "claim-specific authorization ref is required",
		ClaimAuthorizations: []SemanticAuditClaimAuthorization{{
			ClaimType:                "completed_claim",
			Status:                   "authorized",
			VerificationEvidenceRefs: []string{request.VerificationResults[0].EvidenceRef},
		}},
	}

	artifact, err := BuildSemanticAudit(request)
	if err != nil {
		t.Fatal(err)
	}

	readiness := artifact.ClaimReadiness
	if readiness.ClaimReady {
		t.Fatalf("ClaimReadiness.ClaimReady = true, want false without claim-specific authorization_ref")
	}
	if !hasString(readiness.BlockedBy, "claim_authorization_ref_required") {
		t.Fatalf("ClaimReadiness.BlockedBy = %#v, want claim_authorization_ref_required", readiness.BlockedBy)
	}
}

func TestSemanticAuditWorkflowAuthorizationRequiresClaimAuthorizationVerificationRefsForFinalClaims(t *testing.T) {
	request := sampleVerifiedSemanticAuditRequest()
	request.WorkContract.WorkflowIntent = "implement"
	request.VerificationResults[0].ClaimTypes = []string{"release_safe"}
	request.WorkflowAuthorization = SemanticAuditWorkflowAuthorization{
		WorkflowIntent:   "implement",
		Status:           "authorized",
		AuthorizedClaims: []string{"release_safe"},
		AuthorizationRef: "workflow:implement#release-safe-reviewed",
		Reason:           "claim-specific authorization must reference matched verification evidence",
		ClaimAuthorizations: []SemanticAuditClaimAuthorization{{
			ClaimType:                "release_safe",
			Status:                   "authorized",
			AuthorizationRef:         "workflow:implement#release-safe-reviewed",
			VerificationEvidenceRefs: []string{"test:unrelated#passed"},
		}},
	}

	artifact, err := BuildSemanticAudit(request)
	if err != nil {
		t.Fatal(err)
	}

	readiness := artifact.ClaimReadiness
	if readiness.ClaimReady {
		t.Fatalf("ClaimReadiness.ClaimReady = true, want false when claim authorization references unrelated verification evidence")
	}
	if !hasString(readiness.BlockedBy, "claim_authorization_verification_ref_required") {
		t.Fatalf("ClaimReadiness.BlockedBy = %#v, want claim_authorization_verification_ref_required", readiness.BlockedBy)
	}
}

func TestSemanticAuditWorkflowAuthorizationBlocksUnknownClaimType(t *testing.T) {
	request := sampleVerifiedSemanticAuditRequest()
	request.WorkflowAuthorization = SemanticAuditWorkflowAuthorization{
		WorkflowIntent:   "implement",
		Status:           "authorized",
		AuthorizedClaims: []string{"deploy_claim"},
		AuthorizationRef: "workflow:implement#deploy-reviewed",
		Reason:           "unknown claim type must not be accepted",
	}

	artifact, err := BuildSemanticAudit(request)
	if err != nil {
		t.Fatal(err)
	}

	readiness := artifact.ClaimReadiness
	if readiness.ClaimReady {
		t.Fatalf("ClaimReadiness.ClaimReady = true, want false for unknown claim type")
	}
	if readiness.ClaimType != "deploy_claim" {
		t.Fatalf("ClaimReadiness.ClaimType = %q, want deploy_claim", readiness.ClaimType)
	}
	if !hasString(readiness.BlockedBy, "claim_type_not_supported") {
		t.Fatalf("ClaimReadiness.BlockedBy = %#v, want claim_type_not_supported", readiness.BlockedBy)
	}
}

func TestSemanticAuditWorkflowAuthorizationRequiresAuthorizationRef(t *testing.T) {
	request := sampleVerifiedSemanticAuditRequest()
	request.WorkflowAuthorization = SemanticAuditWorkflowAuthorization{
		WorkflowIntent:   "debug",
		Status:           "authorized",
		AuthorizedClaims: []string{"root_cause_claim"},
		Reason:           "debug workflow reviewed bounded evidence and matching verification",
	}

	artifact, err := BuildSemanticAudit(request)
	if err != nil {
		t.Fatal(err)
	}

	readiness := artifact.ClaimReadiness
	if readiness.ClaimReady {
		t.Fatalf("ClaimReadiness.ClaimReady = true, want false without authorization_ref")
	}
	if readiness.ClaimStatus != "claim_candidate" {
		t.Fatalf("ClaimReadiness.ClaimStatus = %q, want claim_candidate", readiness.ClaimStatus)
	}
	if readiness.ClaimType != "root_cause_claim" {
		t.Fatalf("ClaimReadiness.ClaimType = %q, want root_cause_claim", readiness.ClaimType)
	}
	if !hasString(readiness.BlockedBy, "workflow_authorization_ref_required") {
		t.Fatalf("ClaimReadiness.BlockedBy = %#v, want workflow_authorization_ref_required", readiness.BlockedBy)
	}
}

func TestSemanticAuditWorkflowAuthorizationRequiresEverySelectedCandidateLiveEvidence(t *testing.T) {
	request := sampleVerifiedSemanticAuditRequest()
	request.SemanticIntakeOutput.CandidateUniverse.PrimaryCandidates = append(
		request.SemanticIntakeOutput.CandidateUniverse.PrimaryCandidates,
		SemanticIntakeCandidate{
			ID:           "h5-client-shell",
			Labels:       []string{"H5 Client Shell"},
			SurfaceType:  "ui_shell",
			Score:        8,
			EvidenceRank: "E2",
			FacetCoverage: SemanticIntakeFacetCoverage{
				Covered: []string{"H5"},
				Missing: []string{"verification path"},
			},
			OwnerHints: SemanticIntakeOwnerHints{
				PrimaryPaths:      []string{"desktop/src/h5/ClientShell.tsx"},
				VerificationPaths: []string{"desktop/src/h5/ClientShell.test.tsx"},
			},
		},
	)
	request.RouteDecision.SelectedCandidateIDs = []string{"environment-settings-page", "h5-client-shell"}
	request.VerificationResults = append(request.VerificationResults, SemanticAuditVerificationResult{
		CandidateID:      "h5-client-shell",
		VerificationPath: "desktop/src/h5/ClientShell.test.tsx",
		Command:          "npm test -- ClientShell.test.tsx",
		Status:           "passed",
		EvidenceRef:      "test:ClientShell.test.tsx#passed",
		Summary:          "H5 shell regression test passed",
	})
	request.WorkflowAuthorization = SemanticAuditWorkflowAuthorization{
		WorkflowIntent:   "debug",
		Status:           "authorized",
		AuthorizedClaims: []string{"root_cause_claim"},
		AuthorizationRef: "workflow:debug#root-cause-reviewed",
		Reason:           "debug workflow reviewed bounded evidence and matching verification",
	}

	artifact, err := BuildSemanticAudit(request)
	if err != nil {
		t.Fatal(err)
	}

	readiness := artifact.ClaimReadiness
	if !readiness.VerificationSatisfied {
		t.Fatalf("ClaimReadiness.VerificationSatisfied = false, want true with passed verification for every selected candidate")
	}
	if readiness.ClaimReady {
		t.Fatalf("ClaimReadiness.ClaimReady = true, want false until every selected candidate has bounded source evidence")
	}
	if !hasString(readiness.BlockedBy, "bounded_live_evidence_required") {
		t.Fatalf("ClaimReadiness.BlockedBy = %#v, want bounded_live_evidence_required", readiness.BlockedBy)
	}
}

func TestSemanticAuditWorkflowAuthorizationRequiresEverySelectedCandidateVerification(t *testing.T) {
	request := sampleVerifiedSemanticAuditRequest()
	request.SemanticIntakeOutput.CandidateUniverse.PrimaryCandidates = append(
		request.SemanticIntakeOutput.CandidateUniverse.PrimaryCandidates,
		SemanticIntakeCandidate{
			ID:           "h5-client-shell",
			Labels:       []string{"H5 Client Shell"},
			SurfaceType:  "ui_shell",
			Score:        8,
			EvidenceRank: "E2",
			FacetCoverage: SemanticIntakeFacetCoverage{
				Covered: []string{"H5"},
				Missing: []string{"verification path"},
			},
			OwnerHints: SemanticIntakeOwnerHints{
				PrimaryPaths:      []string{"desktop/src/h5/ClientShell.tsx"},
				VerificationPaths: []string{"desktop/src/h5/ClientShell.test.tsx"},
			},
		},
	)
	request.RouteDecision.SelectedCandidateIDs = []string{"environment-settings-page", "h5-client-shell"}
	request.LiveEvidenceCapture = append(request.LiveEvidenceCapture, SemanticAuditCapturedEvidence{
		StepID:              "inspect-02",
		ReadPath:            "desktop/src/h5/ClientShell.tsx",
		EvidenceNeed:        "H5 host route evidence",
		SourceKind:          "source",
		SourceRef:           "desktop/src/h5/ClientShell.tsx",
		ObservedSignal:      "H5 shell hosts the environment settings route",
		SupportsCandidateID: "h5-client-shell",
		SupportsCandidate:   true,
		EvidenceRef:         "read:desktop/src/h5/ClientShell.tsx#route-host",
	})
	request.WorkflowAuthorization = SemanticAuditWorkflowAuthorization{
		WorkflowIntent:   "debug",
		Status:           "authorized",
		AuthorizedClaims: []string{"root_cause_claim"},
		AuthorizationRef: "workflow:debug#root-cause-reviewed",
		Reason:           "debug workflow reviewed bounded evidence and matching verification",
	}

	artifact, err := BuildSemanticAudit(request)
	if err != nil {
		t.Fatal(err)
	}

	readiness := artifact.ClaimReadiness
	if readiness.VerificationSatisfied {
		t.Fatalf("ClaimReadiness.VerificationSatisfied = true, want false until every selected candidate has a passed verification result")
	}
	if readiness.ClaimReady {
		t.Fatalf("ClaimReadiness.ClaimReady = true, want false with one selected candidate missing verification result")
	}
	if !hasString(readiness.BlockedBy, "verification_result_required") {
		t.Fatalf("ClaimReadiness.BlockedBy = %#v, want verification_result_required", readiness.BlockedBy)
	}
}

func sampleVerifiedSemanticAuditRequest() SemanticAuditRequest {
	request := sampleSemanticAuditRequest()
	request.SemanticIntakeOutput.CandidateUniverse.PrimaryCandidates[0].OwnerHints = SemanticIntakeOwnerHints{
		PrimaryPaths:      []string{"desktop/src/pages/EnvironmentSettings.tsx"},
		VerificationPaths: []string{"desktop/src/pages/EnvironmentSettings.test.tsx"},
	}
	request.LiveEvidenceCapture = []SemanticAuditCapturedEvidence{{
		StepID:              "inspect-01",
		ReadPath:            "desktop/src/pages/EnvironmentSettings.tsx",
		EvidenceNeed:        "exact exception source",
		SourceKind:          "source",
		SourceRef:           "desktop/src/pages/EnvironmentSettings.tsx",
		ObservedSignal:      "H5 access exception stack enters EnvironmentSettings route guard",
		SupportsCandidateID: "environment-settings-page",
		SupportsCandidate:   true,
		EvidenceRef:         "read:desktop/src/pages/EnvironmentSettings.tsx#route-guard",
	}}
	request.VerificationResults = []SemanticAuditVerificationResult{{
		CandidateID:      "environment-settings-page",
		VerificationPath: "desktop/src/pages/EnvironmentSettings.test.tsx",
		Command:          "npm test -- EnvironmentSettings.test.tsx",
		Status:           "passed",
		EvidenceRef:      "test:EnvironmentSettings.test.tsx#passed",
		Summary:          "targeted regression test passed",
	}}
	return request
}

func sampleRootCauseReadySemanticAuditRequest() SemanticAuditRequest {
	request := sampleVerifiedSemanticAuditRequest()
	request.WorkContract.WorkflowIntent = "debug"
	request.WorkflowAuthorization = SemanticAuditWorkflowAuthorization{
		WorkflowIntent:   "debug",
		Status:           "authorized",
		AuthorizedClaims: []string{"root_cause_claim"},
		AuthorizationRef: "workflow:debug#root-cause-reviewed",
		Reason:           "debug workflow reviewed bounded evidence and matching verification",
	}
	return request
}

func sampleSemanticAuditRequest() SemanticAuditRequest {
	intakeInput := SemanticIntakeRequest{
		Version:    1,
		RawRequest: "H5访问环境变量页面会出错",
		AgentFacets: SemanticIntakeFacetSet{
			Surface:  SemanticIntakeFacetGroup{Required: []string{"H5", "environment settings page"}},
			Behavior: SemanticIntakeFacetGroup{Required: []string{"access exception"}},
		},
	}
	intakeOutput := SemanticIntakePayload{
		Version:   1,
		Readiness: semanticIntakeReadinessQueryReady,
		CandidateUniverse: SemanticIntakeUniverse{
			PrimaryCandidates: []SemanticIntakeCandidate{{
				ID:           "environment-settings-page",
				Labels:       []string{"Environment Settings Page", "环境变量页面"},
				SurfaceType:  "ui_page",
				Score:        9,
				EvidenceRank: "E2",
				FacetCoverage: SemanticIntakeFacetCoverage{
					Covered: []string{"H5", "environment settings page"},
					Missing: []string{"verification path"},
				},
				Basis: []string{"facet coverage preserved for audit replay", "surface type ui_page satisfies required surface signals"},
			}},
			ContrastCandidates: []SemanticIntakeCandidate{{
				ID:             "env-config",
				Labels:         []string{".env", "environment variables"},
				SurfaceType:    "config_surface",
				Score:          4,
				EvidenceRank:   "E2",
				ContrastReason: "matches environment wording but not page surface",
			}},
			RejectedCandidates: []SemanticIntakeRejectedCandidate{{
				ID:              "workflow-environment",
				Labels:          []string{"workflow environment"},
				SurfaceType:     "workflow_surface",
				FalseMatchType:  "workflow-shadow",
				RejectionReason: "workflow surface is not requested",
			}},
		},
		PermissionHint: SemanticIntakePermission{
			MaximumWithoutLiveEvidence: "P2",
			BlockedActions:             []string{"change", "fixed_claim"},
		},
		LearningCandidate: SemanticIntakeLearning{
			MemoryLevel: "M1",
			FalseMatches: []SemanticIntakeFalseMatch{{
				Phrase:            "环境变量",
				RejectedConceptID: "env-config",
				FalseMatchType:    "config-shadow",
			}},
		},
	}
	return SemanticAuditRequest{
		Version: 1,
		WorkContract: SemanticAuditWorkContract{
			ID:             "wc-h5-env-page",
			RawRequest:     "H5访问环境变量页面会出错",
			WorkflowIntent: "debug",
			ExtractedFacets: []string{
				"H5",
				"environment settings page",
				"access exception",
			},
		},
		SemanticIntakeInput:  intakeInput,
		SemanticIntakeOutput: intakeOutput,
		RouteDecision: SemanticAuditRouteDecisionInput{
			SelectedCandidateIDs: []string{"environment-settings-page"},
			ContrastCandidateIDs: []string{"env-config"},
			RejectedCandidateIDs: []string{"workflow-environment"},
			SelectionReason:      "H5 page surface dominates environment config wording",
		},
		PermissionDecision: SemanticAuditPermissionInput{
			RequestedLevel:    "P3",
			EvidenceLevel:     "semantic_intake_only",
			RequestedActions:  []string{"targeted_inspect", "change"},
			UpgradeReasons:    []string{"primary candidate selected"},
			DowngradeReasons:  []string{"verification path missing"},
			VerificationOwner: "",
		},
		ActionLog: []SemanticAuditAction{{
			Step:             "semantic_intake",
			InputRef:         "semantic_intake_input",
			OutputRef:        "semantic_intake_output",
			PermissionBefore: "P0",
			PermissionAfter:  "P2",
			Summary:          "ranked page surface ahead of config false friend",
		}},
		RouteCorrections: []SemanticAuditRouteCorrection{{
			Phrase:             "环境变量",
			RejectedConceptID:  "env-config",
			FalseMatchType:     "config-shadow",
			CorrectionReason:   "page/access facets dominate config wording",
			RequiredSignals:    []string{"页面", "访问"},
			SuppressionSignals: []string{".env", "shell", "build"},
		}},
	}
}

func sampleMixedCJKAuditRequest() SemanticAuditRequest {
	request := sampleSemanticAuditRequest()
	request.WorkContract.RawRequest = "H5 EnvironmentSettings页面白屏"
	request.WorkContract.NormalizedGoal = "debug H5 environment settings page blank screen"
	request.WorkContract.ExtractedFacets = []string{"H5", "EnvironmentSettings页面", "blank screen"}
	request.SemanticIntakeInput.RawRequest = request.WorkContract.RawRequest
	request.SemanticIntakeInput.AgentFacets.Surface.Required = []string{"H5", "EnvironmentSettings页面"}
	request.SemanticIntakeInput.AgentFacets.Behavior.Required = []string{"blank screen"}
	request.SemanticIntakeOutput.CandidateUniverse.PrimaryCandidates[0].Basis = []string{"facet coverage preserved for audit replay", "mixed CJK/ASCII surface term maps to UI page"}
	request.SemanticIntakeOutput.CandidateUniverse.RejectedCandidates = []SemanticIntakeRejectedCandidate{{
		ID:              "env-config",
		Labels:          []string{".env", "environment variables"},
		SurfaceType:     "config_surface",
		FalseMatchType:  "config-shadow",
		RejectionReason: "config wording lacks page and blank-screen facets",
	}}
	request.SemanticIntakeOutput.LearningCandidate.FalseMatches = []SemanticIntakeFalseMatch{{
		Phrase:            "EnvironmentSettings页面",
		RejectedConceptID: "env-config",
		FalseMatchType:    "config-shadow",
	}}
	request.RouteDecision.RejectedCandidateIDs = []string{"env-config"}
	request.RouteCorrections = []SemanticAuditRouteCorrection{{
		Phrase:             "EnvironmentSettings页面",
		RejectedConceptID:  "env-config",
		FalseMatchType:     "config-shadow",
		RequiredSignals:    []string{"页面", "H5"},
		SuppressionSignals: []string{".env", "shell"},
	}}
	return request
}

func sampleSymptomFirstAuditRequest() SemanticAuditRequest {
	request := sampleSemanticAuditRequest()
	request.WorkContract.RawRequest = "打开就白屏，像是设置页挂了"
	request.WorkContract.NormalizedGoal = "debug settings page blank screen"
	request.WorkContract.ExtractedFacets = []string{"blank screen", "settings page", "symptom-first"}
	request.SemanticIntakeInput.RawRequest = request.WorkContract.RawRequest
	request.SemanticIntakeInput.AgentFacets.Surface.Required = []string{"settings page"}
	request.SemanticIntakeInput.AgentFacets.Behavior.Required = []string{"blank screen"}
	request.SemanticIntakeOutput.CandidateUniverse.PrimaryCandidates[0].Basis = []string{"facet coverage preserved for audit replay", "symptom-first behavior still preserves page surface"}
	request.SemanticIntakeOutput.CandidateUniverse.RejectedCandidates = []SemanticIntakeRejectedCandidate{{
		ID:              "docs-environment-settings",
		Labels:          []string{"Environment settings docs"},
		SurfaceType:     "docs_reference_surface",
		FalseMatchType:  "docs-shadow",
		RejectionReason: "symptom requires runtime page, not documentation",
	}}
	request.SemanticIntakeOutput.LearningCandidate.FalseMatches = []SemanticIntakeFalseMatch{{
		Phrase:            "设置页",
		RejectedConceptID: "docs-environment-settings",
		FalseMatchType:    "docs-shadow",
	}}
	request.RouteDecision.RejectedCandidateIDs = []string{"docs-environment-settings"}
	request.PermissionDecision.RequestedActions = []string{"targeted_inspect", "fixed_claim"}
	request.RouteCorrections = []SemanticAuditRouteCorrection{{
		Phrase:            "设置页",
		RejectedConceptID: "docs-environment-settings",
		FalseMatchType:    "docs-shadow",
		RequiredSignals:   []string{"白屏", "挂了"},
	}}
	return request
}

func sampleWorkflowShadowAuditRequest() SemanticAuditRequest {
	request := sampleSemanticAuditRequest()
	request.WorkContract.RawRequest = "sp-debug 启动的时候环境报错"
	request.WorkContract.NormalizedGoal = "debug generated sp-debug runtime environment error"
	request.WorkContract.WorkflowIntent = "debug"
	request.WorkContract.ExtractedFacets = []string{"sp-debug", "workflow runtime", "environment error"}
	request.SemanticIntakeInput.RawRequest = request.WorkContract.RawRequest
	request.SemanticIntakeInput.AgentFacets.Surface.Required = []string{"sp-debug", "workflow runtime"}
	request.SemanticIntakeInput.AgentFacets.Behavior.Required = []string{"environment error"}
	request.SemanticIntakeOutput.CandidateUniverse.PrimaryCandidates = []SemanticIntakeCandidate{{
		ID:           "generated-sp-debug-runtime",
		Labels:       []string{"sp-debug runtime"},
		SurfaceType:  "workflow_surface",
		Score:        9,
		EvidenceRank: "E2",
		FacetCoverage: SemanticIntakeFacetCoverage{
			Covered: []string{"sp-debug", "workflow runtime"},
			Missing: []string{"live launcher evidence"},
		},
		Basis: []string{"facet coverage preserved for audit replay", "workflow facet dominates environment wording"},
	}}
	request.SemanticIntakeOutput.CandidateUniverse.RejectedCandidates = []SemanticIntakeRejectedCandidate{{
		ID:              "environment-settings-page",
		Labels:          []string{"环境变量页面"},
		SurfaceType:     "ui_page",
		FalseMatchType:  "ui-page-shadow",
		RejectionReason: "workflow runtime is not a user-facing settings page",
	}}
	request.SemanticIntakeOutput.LearningCandidate.FalseMatches = []SemanticIntakeFalseMatch{{
		Phrase:            "sp-debug 环境",
		RejectedConceptID: "environment-settings-page",
		FalseMatchType:    "ui-page-shadow",
	}}
	request.RouteDecision.SelectedCandidateIDs = []string{"generated-sp-debug-runtime"}
	request.RouteDecision.RejectedCandidateIDs = []string{"environment-settings-page"}
	request.PermissionDecision.RequestedActions = []string{"targeted_inspect", "completed_claim"}
	request.RouteCorrections = []SemanticAuditRouteCorrection{{
		Phrase:            "sp-debug 环境",
		RejectedConceptID: "environment-settings-page",
		FalseMatchType:    "ui-page-shadow",
		RequiredSignals:   []string{"sp-debug", "启动"},
	}}
	return request
}

func sampleDocsShadowAuditRequest() SemanticAuditRequest {
	request := sampleSemanticAuditRequest()
	request.WorkContract.RawRequest = "环境变量页面在哪个文档里说明了"
	request.WorkContract.NormalizedGoal = "find documentation for environment settings page"
	request.WorkContract.WorkflowIntent = "research"
	request.WorkContract.ExtractedFacets = []string{"documentation", "environment settings page"}
	request.SemanticIntakeInput.RawRequest = request.WorkContract.RawRequest
	request.SemanticIntakeInput.AgentFacets.Surface.Required = []string{"documentation", "environment settings page"}
	request.SemanticIntakeInput.AgentFacets.Behavior.Required = nil
	request.SemanticIntakeOutput.CandidateUniverse.PrimaryCandidates = []SemanticIntakeCandidate{{
		ID:           "environment-settings-docs",
		Labels:       []string{"Environment settings docs"},
		SurfaceType:  "docs_reference_surface",
		Score:        8,
		EvidenceRank: "E2",
		FacetCoverage: SemanticIntakeFacetCoverage{
			Covered: []string{"documentation", "environment settings page"},
			Missing: []string{"doc path evidence"},
		},
		Basis: []string{"facet coverage preserved for audit replay", "docs facet dominates UI page wording"},
	}}
	request.SemanticIntakeOutput.CandidateUniverse.RejectedCandidates = []SemanticIntakeRejectedCandidate{{
		ID:              "environment-settings-page",
		Labels:          []string{"环境变量页面"},
		SurfaceType:     "ui_page",
		FalseMatchType:  "ui-page-shadow",
		RejectionReason: "request asks for docs, not the page implementation",
	}}
	request.SemanticIntakeOutput.PermissionHint.MaximumWithoutLiveEvidence = "P1"
	request.SemanticIntakeOutput.LearningCandidate.FalseMatches = []SemanticIntakeFalseMatch{{
		Phrase:            "文档里说明",
		RejectedConceptID: "environment-settings-page",
		FalseMatchType:    "ui-page-shadow",
	}}
	request.RouteDecision.SelectedCandidateIDs = []string{"environment-settings-docs"}
	request.RouteDecision.RejectedCandidateIDs = []string{"environment-settings-page"}
	request.PermissionDecision.RequestedLevel = "P2"
	request.PermissionDecision.RequestedActions = []string{"targeted_inspect"}
	request.RouteCorrections = []SemanticAuditRouteCorrection{{
		Phrase:            "文档里说明",
		RejectedConceptID: "environment-settings-page",
		FalseMatchType:    "ui-page-shadow",
		RequiredSignals:   []string{"文档", "说明"},
	}}
	return request
}

func sampleStaleRuntimeFallbackAuditRequest() SemanticAuditRequest {
	request := sampleSemanticAuditRequest()
	request.WorkContract.RawRequest = "项目认知运行时不可用时先别乱匹配"
	request.WorkContract.NormalizedGoal = "record fallback audit without trusting stale runtime"
	request.SemanticIntakeInput.RawRequest = request.WorkContract.RawRequest
	request.SemanticIntakeOutput = semanticIntakeUnavailablePayload("project-cognition runtime unavailable")
	request.RouteDecision = SemanticAuditRouteDecisionInput{
		SelectionReason: "runtime unavailable; no selected concept",
	}
	request.PermissionDecision = SemanticAuditPermissionInput{
		RequestedLevel:   "P2",
		EvidenceLevel:    "semantic_intake_only",
		RequestedActions: []string{"inspect_broadly", "change"},
	}
	request.ActionLog = []SemanticAuditAction{{
		Step:             "fallback_audit",
		OutputRef:        "manual semantic-audit-input.json",
		PermissionBefore: "P0",
		PermissionAfter:  "P0",
		Summary:          "runtime unavailable fallback preserves fields without route trust",
	}}
	request.RouteCorrections = nil
	return request
}

func assertInspectionStep(t *testing.T, steps []SemanticAuditInspectionStep, evidenceNeed string, targetPath string, allowedAction string, permissionLevel string) {
	t.Helper()
	for _, step := range steps {
		if step.EvidenceNeed != evidenceNeed {
			continue
		}
		if step.TargetPath != targetPath {
			t.Fatalf("inspection step %q target_path = %q, want %q", evidenceNeed, step.TargetPath, targetPath)
		}
		if step.AllowedAction != allowedAction {
			t.Fatalf("inspection step %q allowed_action = %q, want %q", evidenceNeed, step.AllowedAction, allowedAction)
		}
		if step.PermissionLevel != permissionLevel {
			t.Fatalf("inspection step %q permission_level = %q, want %q", evidenceNeed, step.PermissionLevel, permissionLevel)
		}
		if step.OnContradiction == "" {
			t.Fatalf("inspection step %q missing on_contradiction", evidenceNeed)
		}
		return
	}
	t.Fatalf("missing inspection step for evidence_need %q in %#v", evidenceNeed, steps)
}
