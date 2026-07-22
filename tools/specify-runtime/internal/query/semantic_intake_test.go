package query

import (
	"encoding/json"
	"strings"
	"testing"

	rt "github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/runtime"
	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/store"
)

func TestSemanticIntakeRoutesEnvironmentPageAheadOfEnvConfig(t *testing.T) {
	paths := queryTestPaths(t)
	seedSemanticIntakeEnvironmentGraph(t, paths)

	payload, err := RunSemanticIntake(paths, SemanticIntakeRequest{
		Version:    1,
		RawRequest: "H5访问环境变量页面会出错，和客户端不太一样",
		ConversationContext: map[string]any{
			"project_role":  "downstream",
			"current_focus": "semantic routing precision",
		},
		AgentFacets: SemanticIntakeFacetSet{
			Goal: SemanticIntakeFacetGroup{
				Required:   []string{"investigate runtime exception"},
				Supporting: []string{"compare H5/client behavior"},
			},
			Surface: SemanticIntakeFacetGroup{
				Required:   []string{"H5/web", "environment settings page"},
				Supporting: []string{"settings UI"},
			},
			Behavior: SemanticIntakeFacetGroup{
				Required: []string{"access exception", "client/web difference"},
			},
			Context: SemanticIntakeFacetGroup{
				Required: []string{"downstream project"},
			},
			Constraint: SemanticIntakeFacetGroup{
				Required: []string{"avoid generic weak match"},
			},
		},
		Options: SemanticIntakeOptions{
			PayloadSize:               "M",
			MaxCandidates:             8,
			IncludeContrast:           true,
			IncludeRejected:           true,
			IncludeOwnerHints:         true,
			IncludeVerificationPriors: true,
		},
	})
	if err != nil {
		t.Fatal(err)
	}

	if payload.Version != 1 {
		t.Fatalf("Version = %d, want 1", payload.Version)
	}
	if payload.Readiness != semanticIntakeReadinessQueryReady {
		t.Fatalf("Readiness = %q, want %q", payload.Readiness, semanticIntakeReadinessQueryReady)
	}
	if payload.IntakeSummary.InterpretedSurfaceType != "ui_page" {
		t.Fatalf("InterpretedSurfaceType = %q, want ui_page", payload.IntakeSummary.InterpretedSurfaceType)
	}
	if !semanticIntakeCandidatesContain(payload.CandidateUniverse.PrimaryCandidates, "environment-settings-page", "ui_page") {
		t.Fatalf("PrimaryCandidates = %#v, want environment-settings-page/ui_page", payload.CandidateUniverse.PrimaryCandidates)
	}
	if semanticIntakeCandidatesContain(payload.CandidateUniverse.PrimaryCandidates, "env-config", "config_surface") {
		t.Fatalf("PrimaryCandidates = %#v, want env-config kept out of primary", payload.CandidateUniverse.PrimaryCandidates)
	}
	if !semanticIntakeCandidatesContain(payload.CandidateUniverse.ContrastCandidates, "env-config", "config_surface") {
		t.Fatalf("ContrastCandidates = %#v, want env-config/config_surface", payload.CandidateUniverse.ContrastCandidates)
	}
	if !semanticIntakeRejectedContain(payload.CandidateUniverse.RejectedCandidates, "workflow-environment", "workflow-shadow") {
		t.Fatalf("RejectedCandidates = %#v, want workflow-environment workflow-shadow", payload.CandidateUniverse.RejectedCandidates)
	}
	if payload.PermissionHint.MaximumWithoutLiveEvidence != "P2" {
		t.Fatalf("MaximumWithoutLiveEvidence = %q, want P2", payload.PermissionHint.MaximumWithoutLiveEvidence)
	}
	if !hasString(payload.PermissionHint.BlockedActions, "change") {
		t.Fatalf("BlockedActions = %#v, want change", payload.PermissionHint.BlockedActions)
	}
	if payload.LearningCandidate.MemoryLevel != "M1" {
		t.Fatalf("LearningCandidate.MemoryLevel = %q, want M1", payload.LearningCandidate.MemoryLevel)
	}
	if len(payload.CandidateUniverse.PrimaryCandidates) == 0 || len(payload.CandidateUniverse.PrimaryCandidates[0].Basis) == 0 {
		t.Fatalf("PrimaryCandidates = %#v, want basis", payload.CandidateUniverse.PrimaryCandidates)
	}
}

func TestSemanticIntakeRejectsEmptyRequestBeforeRankingCandidates(t *testing.T) {
	paths := queryTestPaths(t)
	seedSemanticIntakeEnvironmentGraph(t, paths)

	payload, err := RunSemanticIntake(paths, SemanticIntakeRequest{})
	if err != nil {
		t.Fatal(err)
	}
	if payload.Readiness != semanticIntakeReadinessInvalidInput {
		t.Fatalf("Readiness = %q, want %q", payload.Readiness, semanticIntakeReadinessInvalidInput)
	}
	if len(payload.CandidateUniverse.PrimaryCandidates) != 0 {
		t.Fatalf("PrimaryCandidates = %#v, want none for invalid input", payload.CandidateUniverse.PrimaryCandidates)
	}
	if payload.PermissionHint.MaximumWithoutLiveEvidence != "P0" {
		t.Fatalf("MaximumWithoutLiveEvidence = %q, want P0", payload.PermissionHint.MaximumWithoutLiveEvidence)
	}
}

func TestParseSemanticIntakeRequestRequiresRawRequestAndFacets(t *testing.T) {
	if _, err := ParseSemanticIntakeRequest([]byte(`{}`)); err == nil {
		t.Fatal("ParseSemanticIntakeRequest({}) succeeded, want validation error")
	}
	if _, err := ParseSemanticIntakeRequest([]byte(`{"raw_request":"H5页面报错"}`)); err == nil {
		t.Fatal("ParseSemanticIntakeRequest without facets succeeded, want validation error")
	}
}

func TestParseSemanticIntakeRequestRejectsUnsupportedVersion(t *testing.T) {
	_, err := ParseSemanticIntakeRequest([]byte(`{
		"version": 2,
		"raw_request": "H5页面报错",
		"agent_facets": {
			"surface": {"required": ["environment settings page"]}
		}
	}`))
	if err == nil {
		t.Fatal("ParseSemanticIntakeRequest with version 2 succeeded, want validation error")
	}
}

func TestSemanticIntakeInvalidInputSerializesEmptyCandidateArrays(t *testing.T) {
	payload, err := RunSemanticIntake(rt.Paths{}, SemanticIntakeRequest{})
	if err != nil {
		t.Fatal(err)
	}

	if got := string(mustJSONMarshal(t, payload)); !containsAll(got,
		`"primary_candidates":[]`,
		`"contrast_candidates":[]`,
		`"rejected_candidates":[]`,
	) {
		t.Fatalf("payload JSON = %s, want empty candidate arrays", got)
	}
}

func TestSemanticIntakeHonorsOutputOptions(t *testing.T) {
	paths := queryTestPaths(t)
	seedSemanticIntakeEnvironmentGraph(t, paths)

	payload, err := RunSemanticIntake(paths, SemanticIntakeRequest{
		Version:    1,
		RawRequest: "H5访问环境变量页面会出错",
		AgentFacets: SemanticIntakeFacetSet{
			Surface:  SemanticIntakeFacetGroup{Required: []string{"environment settings page"}},
			Behavior: SemanticIntakeFacetGroup{Required: []string{"access exception"}},
		},
		Options: SemanticIntakeOptions{
			MaxCandidates:             4,
			IncludeContrast:           false,
			IncludeRejected:           false,
			IncludeOwnerHints:         false,
			IncludeVerificationPriors: false,
		},
	})
	if err != nil {
		t.Fatal(err)
	}
	if len(payload.CandidateUniverse.ContrastCandidates) != 0 {
		t.Fatalf("ContrastCandidates = %#v, want omitted by option", payload.CandidateUniverse.ContrastCandidates)
	}
	if len(payload.CandidateUniverse.RejectedCandidates) != 0 {
		t.Fatalf("RejectedCandidates = %#v, want omitted by option", payload.CandidateUniverse.RejectedCandidates)
	}
	for _, candidate := range payload.CandidateUniverse.PrimaryCandidates {
		if len(candidate.OwnerHints.PrimaryPaths) != 0 {
			t.Fatalf("OwnerHints = %#v, want omitted by option", candidate.OwnerHints)
		}
	}
	if len(payload.MissingEvidence) != 0 || len(payload.ExpansionTargets) != 0 {
		t.Fatalf("MissingEvidence=%#v ExpansionTargets=%#v, want verification priors omitted", payload.MissingEvidence, payload.ExpansionTargets)
	}
}

func TestSemanticIntakeQueryReadySerializesEmptyCandidateArrays(t *testing.T) {
	paths := queryTestPaths(t)
	seedSemanticIntakeEnvironmentGraph(t, paths)

	payload, err := RunSemanticIntake(paths, SemanticIntakeRequest{
		Version:    1,
		RawRequest: "H5访问环境变量页面会出错",
		AgentFacets: SemanticIntakeFacetSet{
			Surface:  SemanticIntakeFacetGroup{Required: []string{"environment settings page"}},
			Behavior: SemanticIntakeFacetGroup{Required: []string{"access exception"}},
		},
		Options: SemanticIntakeOptions{
			IncludeContrast: false,
			IncludeRejected: false,
		},
	})
	if err != nil {
		t.Fatal(err)
	}

	if got := string(mustJSONMarshal(t, payload)); !containsAll(got,
		`"contrast_candidates":[]`,
		`"rejected_candidates":[]`,
	) {
		t.Fatalf("payload JSON = %s, want empty candidate arrays", got)
	}
}

func TestSemanticIntakeFalseMatchLearningPhraseComesFromRequest(t *testing.T) {
	paths := queryTestPaths(t)
	seedSemanticIntakeEnvironmentGraph(t, paths)

	payload, err := RunSemanticIntake(paths, SemanticIntakeRequest{
		Version:    1,
		RawRequest: "打开订单页面报错",
		AgentFacets: SemanticIntakeFacetSet{
			Surface:  SemanticIntakeFacetGroup{Required: []string{"订单页面"}},
			Behavior: SemanticIntakeFacetGroup{Required: []string{"页面报错"}},
		},
		Options: SemanticIntakeOptions{IncludeRejected: true},
	})
	if err != nil {
		t.Fatal(err)
	}
	if len(payload.LearningCandidate.FalseMatches) == 0 {
		t.Fatalf("LearningCandidate = %#v, want false match record", payload.LearningCandidate)
	}
	if payload.LearningCandidate.FalseMatches[0].Phrase != "订单页面" {
		t.Fatalf("FalseMatches[0].Phrase = %q, want request-derived phrase", payload.LearningCandidate.FalseMatches[0].Phrase)
	}
}

func seedSemanticIntakeEnvironmentGraph(t *testing.T, paths rt.Paths) {
	t.Helper()
	seedReadyGraph(t, paths, store.ImportInput{
		GenerationID: "GEN-semantic-intake-env",
		Kind:         "full",
		SourceCommit: "abc123",
		Evidence: []store.EvidenceImport{{
			ID:          "E-page",
			SourceKind:  "source",
			SourcePath:  "desktop/src/pages/EnvironmentSettings.tsx",
			CommitSHA:   "abc123",
			Extractor:   "test",
			ContentHash: "hash-page",
		}, {
			ID:          "E-env",
			SourceKind:  "source",
			SourcePath:  ".env.example",
			CommitSHA:   "abc123",
			Extractor:   "test",
			ContentHash: "hash-env",
		}, {
			ID:          "E-workflow",
			SourceKind:  "source",
			SourcePath:  "templates/commands/sp-debug.md",
			CommitSHA:   "abc123",
			Extractor:   "test",
			ContentHash: "hash-workflow",
		}},
		Nodes: []store.NodeImport{{
			ID:          "environment-settings-page",
			Type:        "ui_page",
			Title:       "Environment Settings Page",
			Confidence:  "verified",
			EvidenceIDs: []string{"E-page"},
			Attrs: map[string]any{
				"aliases": []any{"环境变量页面", "environment settings page", "H5 environment settings page"},
			},
		}, {
			ID:          "env-config",
			Type:        "config_surface",
			Title:       "Environment Variable Config",
			Confidence:  "verified",
			EvidenceIDs: []string{"E-env"},
			Attrs: map[string]any{
				"aliases": []any{".env", "environment variables", "环境变量"},
			},
		}, {
			ID:          "workflow-environment",
			Type:        "workflow_surface",
			Title:       "Workflow Environment",
			Confidence:  "verified",
			EvidenceIDs: []string{"E-workflow"},
			Attrs: map[string]any{
				"aliases": []any{"workflow environment", "sp-debug environment", "工作流环境"},
			},
		}},
		PathIndex: []store.PathIndexImport{{
			ID:         "P-page",
			Path:       "desktop/src/pages/EnvironmentSettings.tsx",
			NodeID:     "environment-settings-page",
			Relation:   "owns",
			Confidence: "verified",
			EvidenceID: "E-page",
		}, {
			ID:         "P-env",
			Path:       ".env.example",
			NodeID:     "env-config",
			Relation:   "owns",
			Confidence: "verified",
			EvidenceID: "E-env",
		}, {
			ID:         "P-workflow",
			Path:       "templates/commands/sp-debug.md",
			NodeID:     "workflow-environment",
			Relation:   "owns",
			Confidence: "verified",
			EvidenceID: "E-workflow",
		}},
	})
}

func semanticIntakeCandidatesContain(candidates []SemanticIntakeCandidate, id string, surfaceType string) bool {
	for _, candidate := range candidates {
		if candidate.ID == id && candidate.SurfaceType == surfaceType {
			return true
		}
	}
	return false
}

func mustJSONMarshal(t *testing.T, value any) []byte {
	t.Helper()
	data, err := json.Marshal(value)
	if err != nil {
		t.Fatal(err)
	}
	return data
}

func containsAll(value string, substrings ...string) bool {
	for _, substring := range substrings {
		if !strings.Contains(value, substring) {
			return false
		}
	}
	return true
}

func semanticIntakeRejectedContain(candidates []SemanticIntakeRejectedCandidate, id string, falseMatchType string) bool {
	for _, candidate := range candidates {
		if candidate.ID == id && candidate.FalseMatchType == falseMatchType {
			return true
		}
	}
	return false
}

func TestSemanticIntakeMissingRuntimeReturnsStructuredFallback(t *testing.T) {
	paths := queryTestPaths(t)

	payload, err := RunSemanticIntake(paths, SemanticIntakeRequest{
		Version:    1,
		RawRequest: "环境变量不对",
		AgentFacets: SemanticIntakeFacetSet{
			Surface: SemanticIntakeFacetGroup{Required: []string{"environment"}},
		},
	})
	if err != nil {
		t.Fatal(err)
	}
	if payload.Readiness == semanticIntakeReadinessQueryReady {
		t.Fatalf("Readiness = %q, want non-ready fallback for missing runtime", payload.Readiness)
	}
	if payload.PermissionHint.MaximumWithoutLiveEvidence == "" {
		t.Fatalf("PermissionHint = %#v, want permission cap", payload.PermissionHint)
	}
	if payload.PermissionHint.MaximumWithoutLiveEvidence != "P0" {
		t.Fatalf("MaximumWithoutLiveEvidence = %q, want P0", payload.PermissionHint.MaximumWithoutLiveEvidence)
	}
	for _, action := range []string{"inspect_broadly", "change", "root_cause_claim", "fixed_claim", "completed_claim", "release_safe"} {
		if !hasString(payload.PermissionHint.BlockedActions, action) {
			t.Fatalf("BlockedActions = %#v, want %q blocked", payload.PermissionHint.BlockedActions, action)
		}
	}
}

func TestSemanticIntakeRoutesEnvConfigWhenStartupConfigSignalsDominate(t *testing.T) {
	paths := queryTestPaths(t)
	seedSemanticIntakeEnvironmentGraph(t, paths)

	payload, err := RunSemanticIntake(paths, SemanticIntakeRequest{
		Version:    1,
		RawRequest: "环境变量配了，但是启动后没生效",
		AgentFacets: SemanticIntakeFacetSet{
			Goal:       SemanticIntakeFacetGroup{Required: []string{"investigate configuration not applied"}},
			Surface:    SemanticIntakeFacetGroup{Required: []string{"environment config"}},
			Behavior:   SemanticIntakeFacetGroup{Required: []string{"configured value not applied after startup"}},
			Context:    SemanticIntakeFacetGroup{Required: []string{"runtime startup"}},
			Constraint: SemanticIntakeFacetGroup{Required: []string{"avoid page surface mismatch"}},
		},
		Options: SemanticIntakeOptions{IncludeContrast: true, IncludeRejected: true},
	})
	if err != nil {
		t.Fatal(err)
	}
	if payload.IntakeSummary.InterpretedSurfaceType != "config_surface" {
		t.Fatalf("InterpretedSurfaceType = %q, want config_surface", payload.IntakeSummary.InterpretedSurfaceType)
	}
	if !semanticIntakeCandidatesContain(payload.CandidateUniverse.PrimaryCandidates, "env-config", "config_surface") {
		t.Fatalf("PrimaryCandidates = %#v, want env-config/config_surface", payload.CandidateUniverse.PrimaryCandidates)
	}
	if semanticIntakeCandidatesContain(payload.CandidateUniverse.PrimaryCandidates, "environment-settings-page", "ui_page") {
		t.Fatalf("PrimaryCandidates = %#v, want page out of primary for config startup request", payload.CandidateUniverse.PrimaryCandidates)
	}
}
