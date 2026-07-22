package query

import (
	"context"
	"encoding/json"
	"fmt"
	"sort"
	"strings"
	"unicode"

	rt "github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/runtime"
	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/store"
)

const (
	semanticIntakeReadinessQueryReady          = "query_ready"
	semanticIntakeReadinessInsufficientIndex   = "insufficient_index"
	semanticIntakeReadinessRuntimeUnavailable  = "runtime_unavailable"
	semanticIntakeReadinessInvalidInput        = "invalid_input"
	semanticIntakeBehaviorRuntimeException     = "runtime_exception"
	semanticIntakeBehaviorRuntimeConfiguration = "runtime_configuration"
)

type SemanticIntakeRequest struct {
	Version             int                    `json:"version"`
	RawRequest          string                 `json:"raw_request"`
	ConversationContext map[string]any         `json:"conversation_context,omitempty"`
	AgentFacets         SemanticIntakeFacetSet `json:"agent_facets"`
	Options             SemanticIntakeOptions  `json:"options,omitempty"`
}

type SemanticIntakeFacetSet struct {
	Goal       SemanticIntakeFacetGroup `json:"goal"`
	Surface    SemanticIntakeFacetGroup `json:"surface"`
	Behavior   SemanticIntakeFacetGroup `json:"behavior"`
	Context    SemanticIntakeFacetGroup `json:"context"`
	Constraint SemanticIntakeFacetGroup `json:"constraint"`
}

type SemanticIntakeFacetGroup struct {
	Required   []string `json:"required"`
	Supporting []string `json:"supporting,omitempty"`
	Optional   []string `json:"optional,omitempty"`
}

type SemanticIntakeOptions struct {
	PayloadSize               string `json:"payload_size,omitempty"`
	MaxCandidates             int    `json:"max_candidates,omitempty"`
	IncludeContrast           bool   `json:"include_contrast,omitempty"`
	IncludeRejected           bool   `json:"include_rejected,omitempty"`
	IncludeOwnerHints         bool   `json:"include_owner_hints,omitempty"`
	IncludeVerificationPriors bool   `json:"include_verification_priors,omitempty"`
}

type SemanticIntakePayload struct {
	Version           int                       `json:"version"`
	Readiness         string                    `json:"readiness"`
	ReadinessReason   []string                  `json:"readiness_reason,omitempty"`
	SemanticIntake    *SemanticIntake           `json:"semantic_intake,omitempty"`
	IntakeSummary     SemanticIntakeSummary     `json:"intake_summary"`
	CandidateUniverse SemanticIntakeUniverse    `json:"candidate_universe"`
	ExpansionTargets  []SemanticIntakeExpansion `json:"expansion_targets,omitempty"`
	MissingEvidence   []SemanticIntakeMissing   `json:"missing_evidence,omitempty"`
	PermissionHint    SemanticIntakePermission  `json:"permission_hint"`
	LearningCandidate SemanticIntakeLearning    `json:"learning_candidate"`
	SuggestedRecovery []string                  `json:"suggested_recovery,omitempty"`
}

type SemanticIntakeSummary struct {
	InterpretedSurfaceType  string   `json:"interpreted_surface_type,omitempty"`
	InterpretedBehaviorType string   `json:"interpreted_behavior_type,omitempty"`
	Ambiguities             []string `json:"ambiguities,omitempty"`
}

type SemanticIntakeUniverse struct {
	PrimaryCandidates  []SemanticIntakeCandidate         `json:"primary_candidates"`
	ContrastCandidates []SemanticIntakeCandidate         `json:"contrast_candidates"`
	RejectedCandidates []SemanticIntakeRejectedCandidate `json:"rejected_candidates"`
}

type SemanticIntakeCandidate struct {
	ID             string                      `json:"id"`
	Labels         []string                    `json:"labels,omitempty"`
	SurfaceType    string                      `json:"surface_type"`
	Score          float64                     `json:"score"`
	EvidenceRank   string                      `json:"evidence_rank"`
	FacetCoverage  SemanticIntakeFacetCoverage `json:"facet_coverage"`
	OwnerHints     SemanticIntakeOwnerHints    `json:"owner_hints,omitempty"`
	Basis          []string                    `json:"basis,omitempty"`
	ContrastReason string                      `json:"contrast_reason,omitempty"`
}

type SemanticIntakeRejectedCandidate struct {
	ID              string   `json:"id"`
	Labels          []string `json:"labels,omitempty"`
	SurfaceType     string   `json:"surface_type"`
	FalseMatchType  string   `json:"false_match_type"`
	RejectionReason string   `json:"rejection_reason"`
}

type SemanticIntakeFacetCoverage struct {
	Covered []string `json:"covered,omitempty"`
	Missing []string `json:"missing,omitempty"`
}

type SemanticIntakeOwnerHints struct {
	PrimaryPaths      []string `json:"primary_paths,omitempty"`
	SupportingPaths   []string `json:"supporting_paths,omitempty"`
	TruthPaths        []string `json:"truth_paths,omitempty"`
	VerificationPaths []string `json:"verification_paths,omitempty"`
}

type SemanticIntakeExpansion struct {
	ID          string `json:"id"`
	SurfaceType string `json:"surface_type,omitempty"`
	Purpose     string `json:"purpose"`
}

type SemanticIntakeMissing struct {
	Facet           string `json:"facet"`
	SuggestedAction string `json:"suggested_action,omitempty"`
}

type SemanticIntakePermission struct {
	MaximumWithoutLiveEvidence string   `json:"maximum_without_live_evidence"`
	BlockedActions             []string `json:"blocked_actions"`
}

type SemanticIntakeLearning struct {
	MemoryLevel  string                        `json:"memory_level"`
	Aliases      []SemanticIntakeAliasLearning `json:"aliases,omitempty"`
	FalseMatches []SemanticIntakeFalseMatch    `json:"false_matches,omitempty"`
}

type SemanticIntakeAliasLearning struct {
	Phrase     string                        `json:"phrase"`
	ConceptID  string                        `json:"concept_id"`
	Conditions SemanticIntakeAliasConditions `json:"conditions,omitempty"`
}

type SemanticIntakeAliasConditions struct {
	RequiredSignals []string `json:"required_signals,omitempty"`
	SuppressSignals []string `json:"suppress_signals,omitempty"`
}

type SemanticIntakeFalseMatch struct {
	Phrase            string `json:"phrase"`
	RejectedConceptID string `json:"rejected_concept_id"`
	FalseMatchType    string `json:"false_match_type"`
}

type semanticIntakeScoredCandidate struct {
	candidate      SemanticIntakeCandidate
	falseMatchType string
	rejectReason   string
	surfaceFit     bool
	score          float64
}

func ParseSemanticIntakeRequest(data []byte) (SemanticIntakeRequest, error) {
	var request SemanticIntakeRequest
	if err := json.Unmarshal(data, &request); err != nil {
		return SemanticIntakeRequest{}, fmt.Errorf("parse semantic-intake request: %w", err)
	}
	request.RawRequest = strings.TrimSpace(request.RawRequest)
	request.AgentFacets = normalizeSemanticIntakeFacetSet(request.AgentFacets)
	request.Options = normalizeSemanticIntakeOptions(request.Options)
	if reasons := validateSemanticIntakeRequest(request); len(reasons) > 0 {
		return SemanticIntakeRequest{}, fmt.Errorf("invalid semantic-intake request: %s", strings.Join(reasons, "; "))
	}
	return request, nil
}

func RunSemanticIntake(paths rt.Paths, request SemanticIntakeRequest) (SemanticIntakePayload, error) {
	request.RawRequest = strings.TrimSpace(request.RawRequest)
	request.AgentFacets = normalizeSemanticIntakeFacetSet(request.AgentFacets)
	request.Options = normalizeSemanticIntakeOptions(request.Options)
	if reasons := validateSemanticIntakeRequest(request); len(reasons) > 0 {
		return semanticIntakeInvalidInputPayload(reasons), nil
	}
	status, err := rt.ReadStatus(paths)
	if err != nil {
		return SemanticIntakePayload{}, err
	}
	if status.Readiness != rt.ReadyReadiness || !status.GraphReady || status.ActiveGenerationID == "" {
		return semanticIntakeUnavailablePayload("runtime is not query-ready"), nil
	}

	st, err := store.Open(paths)
	if err != nil {
		return SemanticIntakePayload{}, err
	}
	defer st.Close()

	rows, err := st.AllActiveConceptCandidateRows(context.Background())
	if err != nil {
		return SemanticIntakePayload{}, err
	}
	if len(rows) == 0 {
		return semanticIntakeInsufficientPayload("active graph has no candidate concepts"), nil
	}

	surfaceType := semanticIntakeSurfaceType(request)
	behaviorType := semanticIntakeBehaviorType(request)
	scored := make([]semanticIntakeScoredCandidate, 0, len(rows))
	for _, row := range rows {
		scored = append(scored, semanticIntakeScoreCandidate(row, request, surfaceType))
	}
	sort.SliceStable(scored, func(i, j int) bool {
		if scored[i].score == scored[j].score {
			return scored[i].candidate.ID < scored[j].candidate.ID
		}
		return scored[i].score > scored[j].score
	})

	payload := SemanticIntakePayload{
		Version:        1,
		Readiness:      semanticIntakeReadinessQueryReady,
		SemanticIntake: semanticIntakeCompassObject(request, nil),
		IntakeSummary: SemanticIntakeSummary{
			InterpretedSurfaceType:  surfaceType,
			InterpretedBehaviorType: behaviorType,
			Ambiguities:             semanticIntakeAmbiguities(request),
		},
		CandidateUniverse: semanticIntakeEmptyUniverse(),
		PermissionHint: SemanticIntakePermission{
			MaximumWithoutLiveEvidence: "P2",
			BlockedActions:             []string{"change", "root_cause_claim", "fixed_claim", "completed_claim", "release_safe"},
		},
		LearningCandidate: SemanticIntakeLearning{MemoryLevel: "M1"},
	}

	for _, item := range scored {
		switch {
		case item.falseMatchType != "":
			if request.Options.IncludeRejected {
				payload.CandidateUniverse.RejectedCandidates = append(payload.CandidateUniverse.RejectedCandidates, SemanticIntakeRejectedCandidate{
					ID:              item.candidate.ID,
					Labels:          item.candidate.Labels,
					SurfaceType:     item.candidate.SurfaceType,
					FalseMatchType:  item.falseMatchType,
					RejectionReason: item.rejectReason,
				})
			}
		case item.score <= 0:
			continue
		case item.surfaceFit && len(payload.CandidateUniverse.PrimaryCandidates) < request.Options.MaxCandidates:
			payload.CandidateUniverse.PrimaryCandidates = append(payload.CandidateUniverse.PrimaryCandidates, semanticIntakeApplyCandidateOptions(item.candidate, request.Options))
		default:
			candidate := item.candidate
			if candidate.ContrastReason == "" {
				candidate.ContrastReason = "matches request wording but does not satisfy the strongest required surface signals"
			}
			if request.Options.IncludeContrast {
				payload.CandidateUniverse.ContrastCandidates = append(payload.CandidateUniverse.ContrastCandidates, semanticIntakeApplyCandidateOptions(candidate, request.Options))
			}
		}
	}

	if len(payload.CandidateUniverse.PrimaryCandidates) == 0 {
		payload.Readiness = semanticIntakeReadinessInsufficientIndex
		payload.ReadinessReason = []string{"no candidate satisfied required surface facets"}
		payload.PermissionHint.MaximumWithoutLiveEvidence = "P1"
		payload.SuggestedRecovery = []string{"run specify-runtime cognition update", "ask one surface clarification question"}
	}
	if request.Options.IncludeVerificationPriors {
		payload.MissingEvidence = semanticIntakeMissingEvidence(request)
		payload.ExpansionTargets = semanticIntakeExpansionTargets(payload.CandidateUniverse.PrimaryCandidates)
	}
	payload.SemanticIntake = semanticIntakeCompassObject(request, payload.CandidateUniverse.PrimaryCandidates)
	payload.LearningCandidate = semanticIntakeLearningCandidate(request, payload.CandidateUniverse.PrimaryCandidates, payload.CandidateUniverse.RejectedCandidates)
	return payload, nil
}

func semanticIntakeInvalidInputPayload(reasons []string) SemanticIntakePayload {
	payload := semanticIntakeUnavailablePayload(strings.Join(reasons, "; "))
	payload.Readiness = semanticIntakeReadinessInvalidInput
	payload.SuggestedRecovery = []string{"provide raw_request and at least one agent facet before semantic intake"}
	return payload
}

func semanticIntakeUnavailablePayload(reason string) SemanticIntakePayload {
	return SemanticIntakePayload{
		Version:           1,
		Readiness:         semanticIntakeReadinessRuntimeUnavailable,
		ReadinessReason:   []string{reason},
		CandidateUniverse: semanticIntakeEmptyUniverse(),
		PermissionHint: SemanticIntakePermission{
			MaximumWithoutLiveEvidence: "P0",
			BlockedActions:             []string{"inspect_broadly", "change", "finalize", "root_cause_claim", "fixed_claim", "completed_claim", "release_safe"},
		},
		LearningCandidate: SemanticIntakeLearning{MemoryLevel: "M0"},
		SuggestedRecovery: []string{"initialize or refresh the specify-runtime cognition store"},
	}
}

func normalizeSemanticIntakeOptions(options SemanticIntakeOptions) SemanticIntakeOptions {
	options.PayloadSize = strings.ToUpper(strings.TrimSpace(options.PayloadSize))
	if options.PayloadSize == "" {
		options.PayloadSize = "M"
	}
	if options.MaxCandidates <= 0 {
		switch options.PayloadSize {
		case "S":
			options.MaxCandidates = 4
		case "L":
			options.MaxCandidates = 12
		default:
			options.MaxCandidates = 8
		}
	}
	return options
}

func validateSemanticIntakeRequest(request SemanticIntakeRequest) []string {
	reasons := []string{}
	if request.Version != 0 && request.Version != 1 {
		reasons = append(reasons, "version must be 1")
	}
	if strings.TrimSpace(request.RawRequest) == "" {
		reasons = append(reasons, "raw_request is required")
	}
	if len(semanticIntakeFacetStrings(request.AgentFacets)) == 0 {
		reasons = append(reasons, "at least one agent facet is required")
	}
	return reasons
}

func semanticIntakeApplyCandidateOptions(candidate SemanticIntakeCandidate, options SemanticIntakeOptions) SemanticIntakeCandidate {
	if !options.IncludeOwnerHints {
		candidate.OwnerHints = SemanticIntakeOwnerHints{}
	}
	return candidate
}

func semanticIntakeEmptyUniverse() SemanticIntakeUniverse {
	return SemanticIntakeUniverse{
		PrimaryCandidates:  []SemanticIntakeCandidate{},
		ContrastCandidates: []SemanticIntakeCandidate{},
		RejectedCandidates: []SemanticIntakeRejectedCandidate{},
	}
}

func semanticIntakeInsufficientPayload(reason string) SemanticIntakePayload {
	payload := semanticIntakeUnavailablePayload(reason)
	payload.Readiness = semanticIntakeReadinessInsufficientIndex
	payload.PermissionHint.MaximumWithoutLiveEvidence = "P1"
	payload.LearningCandidate.MemoryLevel = "M1"
	return payload
}

func semanticIntakeScoreCandidate(row store.ConceptCandidateRow, request SemanticIntakeRequest, desiredSurface string) semanticIntakeScoredCandidate {
	surface := semanticIntakeNormalizeSurface(row.NodeType, row.Title, row.Paths)
	labels := semanticIntakeLabels(row)
	haystack := strings.ToLower(strings.Join(append(append([]string{row.NodeID, row.NodeType, row.Title}, labels...), row.Paths...), " "))
	facets := semanticIntakeFacetStrings(request.AgentFacets)
	rawAndFacets := strings.ToLower(request.RawRequest + " " + strings.Join(facets, " "))

	score := 0.0
	covered := []string{}
	basis := []string{}
	for _, label := range labels {
		if strings.TrimSpace(label) == "" {
			continue
		}
		normalized := strings.ToLower(label)
		if strings.Contains(rawAndFacets, normalized) || semanticIntakeTokenOverlap(normalized, rawAndFacets) {
			score += 2
			covered = append(covered, label)
			basis = append(basis, "matched alias or label: "+label)
			break
		}
	}
	for _, facet := range facets {
		if semanticIntakeTextMatches(haystack, strings.ToLower(facet)) {
			score += 1
			covered = append(covered, facet)
		}
	}
	surfaceFit := surface == desiredSurface || desiredSurface == "generic_surface"
	if surfaceFit {
		score += 5
		basis = append(basis, "surface type "+surface+" satisfies required surface signals")
	} else if semanticIntakeSurfaceFamilyFit(surface, desiredSurface) {
		score += 1.5
		basis = append(basis, "surface type "+surface+" is related to "+desiredSurface)
	}
	if len(row.Paths) > 0 {
		score += 1
		basis = append(basis, "owner path is indexed")
	}

	falseMatchType, rejectReason := semanticIntakeFalseMatch(surface, desiredSurface, rawAndFacets)
	if falseMatchType != "" {
		score -= 3
	}
	candidate := SemanticIntakeCandidate{
		ID:           row.NodeID,
		Labels:       labels,
		SurfaceType:  surface,
		Score:        score,
		EvidenceRank: "E2",
		FacetCoverage: SemanticIntakeFacetCoverage{
			Covered: normalizeStrings(covered),
			Missing: semanticIntakeCandidateMissingFacets(request, surfaceFit),
		},
		OwnerHints: SemanticIntakeOwnerHints{
			PrimaryPaths: normalizePaths(row.Paths),
		},
		Basis: normalizeStrings(basis),
	}
	if !surfaceFit {
		candidate.ContrastReason = "matches request wording but surface type " + surface + " does not satisfy strongest " + desiredSurface + " signals"
	}
	return semanticIntakeScoredCandidate{candidate: candidate, falseMatchType: falseMatchType, rejectReason: rejectReason, surfaceFit: surfaceFit, score: score}
}

func semanticIntakeNormalizeSurface(nodeType string, title string, paths []string) string {
	value := strings.ToLower(strings.TrimSpace(nodeType + " " + title + " " + strings.Join(paths, " ")))
	switch {
	case strings.Contains(value, "workflow") || strings.Contains(value, "command"):
		return "workflow_surface"
	case strings.Contains(value, "config") || strings.Contains(value, ".env"):
		return "config_surface"
	case strings.Contains(value, "build") || strings.Contains(value, "release"):
		return "build_release_surface"
	case strings.Contains(value, "api") || strings.Contains(value, "endpoint"):
		return "api_endpoint"
	case strings.Contains(value, "state") || strings.Contains(value, "store"):
		return "state_store"
	case strings.Contains(value, "docs") || strings.Contains(value, "documentation"):
		return "docs_reference_surface"
	case strings.Contains(value, "adapter") || strings.Contains(value, "client-boundary"):
		return "adapter_boundary"
	case strings.Contains(value, "component"):
		return "ui_component"
	case strings.Contains(value, "page") || strings.Contains(value, "ui"):
		return "ui_page"
	default:
		return strings.TrimSpace(nodeType)
	}
}

func semanticIntakeSurfaceType(request SemanticIntakeRequest) string {
	text := strings.ToLower(request.RawRequest + " " + strings.Join(semanticIntakeFacetStrings(request.AgentFacets), " "))
	switch {
	case strings.Contains(text, "sp-debug") || strings.Contains(text, "workflow") || strings.Contains(text, "launcher") || strings.Contains(text, "command"):
		return "workflow_surface"
	case strings.Contains(text, ".env") || strings.Contains(text, "启动") || strings.Contains(text, "startup") || strings.Contains(text, "config") || strings.Contains(text, "配置"):
		return "config_surface"
	case strings.Contains(text, "打包") || strings.Contains(text, "build") || strings.Contains(text, "release"):
		return "build_release_surface"
	case strings.Contains(text, "接口") || strings.Contains(text, "api") || strings.Contains(text, "后端") || strings.Contains(text, "字段"):
		return "api_endpoint"
	case strings.Contains(text, "状态") || strings.Contains(text, "切页面") || strings.Contains(text, "store"):
		return "state_store"
	case strings.Contains(text, "文档") || strings.Contains(text, "docs") || strings.Contains(text, "说明"):
		return "docs_reference_surface"
	case strings.Contains(text, "客户端正常") || strings.Contains(text, "client/web") || strings.Contains(text, "客户端不") || strings.Contains(text, "h5不"):
		if strings.Contains(text, "页面") || strings.Contains(text, "page") || strings.Contains(text, "访问") {
			return "ui_page"
		}
		return "adapter_boundary"
	case strings.Contains(text, "页面") || strings.Contains(text, "page") || strings.Contains(text, "访问") || strings.Contains(text, "打开") || strings.Contains(text, "h5"):
		return "ui_page"
	default:
		return "generic_surface"
	}
}

func semanticIntakeBehaviorType(request SemanticIntakeRequest) string {
	text := strings.ToLower(request.RawRequest + " " + strings.Join(semanticIntakeFacetStrings(request.AgentFacets), " "))
	switch {
	case strings.Contains(text, "启动") || strings.Contains(text, "startup") || strings.Contains(text, "not applied"):
		return semanticIntakeBehaviorRuntimeConfiguration
	case strings.Contains(text, "exception") || strings.Contains(text, "异常") || strings.Contains(text, "报错") || strings.Contains(text, "出错") || strings.Contains(text, "炸"):
		return semanticIntakeBehaviorRuntimeException
	default:
		return ""
	}
}

func semanticIntakeFalseMatch(surface string, desiredSurface string, text string) (string, string) {
	if surface == desiredSurface {
		return "", ""
	}
	if surface == "workflow_surface" && desiredSurface != "workflow_surface" {
		return "workflow-shadow", "workflow runtime does not match the requested product surface"
	}
	if surface == "docs_reference_surface" && !strings.Contains(text, "docs") && !strings.Contains(text, "文档") {
		return "docs-shadow", "documentation surface does not match runtime behavior request"
	}
	return "", ""
}

func semanticIntakeSurfaceFamilyFit(surface string, desiredSurface string) bool {
	if desiredSurface == "ui_page" && (surface == "ui_component" || surface == "route_navigation" || surface == "adapter_boundary") {
		return true
	}
	if desiredSurface == "config_surface" && surface == "build_release_surface" {
		return true
	}
	return false
}

func semanticIntakeLabels(row store.ConceptCandidateRow) []string {
	labels := []string{row.Title}
	for _, alias := range row.Aliases {
		labels = append(labels, alias.Alias)
	}
	return normalizeStrings(labels)
}

func semanticIntakeFacetStrings(facets SemanticIntakeFacetSet) []string {
	values := []string{}
	groups := []SemanticIntakeFacetGroup{facets.Goal, facets.Surface, facets.Behavior, facets.Context, facets.Constraint}
	for _, group := range groups {
		values = append(values, group.Required...)
		values = append(values, group.Supporting...)
		values = append(values, group.Optional...)
	}
	return normalizeStrings(values)
}

func semanticIntakeCandidateMissingFacets(request SemanticIntakeRequest, surfaceFit bool) []string {
	missing := []string{}
	if !surfaceFit {
		missing = append(missing, "required surface fit")
	}
	if semanticIntakeBehaviorType(request) == semanticIntakeBehaviorRuntimeException {
		missing = append(missing, "exact exception source")
	}
	missing = append(missing, "verification path")
	return normalizeStrings(missing)
}

func semanticIntakeMissingEvidence(request SemanticIntakeRequest) []SemanticIntakeMissing {
	missing := []SemanticIntakeMissing{{Facet: "verification path", SuggestedAction: "identify a positive and regression verification owner"}}
	if semanticIntakeBehaviorType(request) == semanticIntakeBehaviorRuntimeException {
		missing = append([]SemanticIntakeMissing{{Facet: "exact exception source", SuggestedAction: "inspect primary owner and runtime stack"}}, missing...)
	}
	return missing
}

func semanticIntakeExpansionTargets(primary []SemanticIntakeCandidate) []SemanticIntakeExpansion {
	if len(primary) == 0 {
		return nil
	}
	targets := []SemanticIntakeExpansion{}
	for _, candidate := range primary {
		switch candidate.SurfaceType {
		case "ui_page":
			targets = append(targets, SemanticIntakeExpansion{ID: candidate.ID + ":route", SurfaceType: "route_navigation", Purpose: "confirm route owner"})
			targets = append(targets, SemanticIntakeExpansion{ID: candidate.ID + ":adapter", SurfaceType: "adapter_boundary", Purpose: "check client/web behavior split"})
		case "config_surface":
			targets = append(targets, SemanticIntakeExpansion{ID: candidate.ID + ":startup", SurfaceType: "config_surface", Purpose: "confirm runtime config load path"})
		}
	}
	return targets
}

func semanticIntakeLearningCandidate(request SemanticIntakeRequest, primary []SemanticIntakeCandidate, rejected []SemanticIntakeRejectedCandidate) SemanticIntakeLearning {
	learning := SemanticIntakeLearning{MemoryLevel: "M1"}
	text := request.RawRequest + " " + strings.Join(semanticIntakeFacetStrings(request.AgentFacets), " ")
	if strings.Contains(text, "环境变量页面") {
		for _, candidate := range primary {
			if candidate.SurfaceType == "ui_page" {
				learning.Aliases = append(learning.Aliases, SemanticIntakeAliasLearning{
					Phrase:    "环境变量页面",
					ConceptID: candidate.ID,
					Conditions: SemanticIntakeAliasConditions{
						RequiredSignals: []string{"页面", "访问"},
						SuppressSignals: []string{".env", "CI", "shell", "build"},
					},
				})
				break
			}
		}
	}
	falseMatchPhrase := semanticIntakeLearningPhrase(request)
	for _, candidate := range rejected {
		learning.FalseMatches = append(learning.FalseMatches, SemanticIntakeFalseMatch{
			Phrase:            falseMatchPhrase,
			RejectedConceptID: candidate.ID,
			FalseMatchType:    candidate.FalseMatchType,
		})
	}
	return learning
}

func semanticIntakeCompassObject(request SemanticIntakeRequest, primary []SemanticIntakeCandidate) *SemanticIntake {
	intake := SemanticIntake{
		NormalizedQuery:     request.RawRequest,
		IntentFacets:        semanticIntakeFacetStrings(request.AgentFacets),
		NegativeConstraints: append([]string{}, request.AgentFacets.Constraint.Required...),
	}
	if workflowIntent, ok := request.ConversationContext["workflow_intent"].(string); ok {
		intake.WorkflowIntent = strings.TrimSpace(workflowIntent)
	}
	for _, candidate := range primary {
		if len(candidate.Labels) == 0 {
			continue
		}
		intake.AliasInterpretations = append(intake.AliasInterpretations, AliasInterpretation{
			Alias:      candidate.Labels[0],
			Meaning:    candidate.ID,
			Confidence: "medium",
		})
	}
	normalized := normalizeSemanticIntake(intake)
	return &normalized
}

func semanticIntakeLearningPhrase(request SemanticIntakeRequest) string {
	groups := []SemanticIntakeFacetGroup{
		request.AgentFacets.Surface,
		request.AgentFacets.Goal,
		request.AgentFacets.Behavior,
		request.AgentFacets.Context,
		request.AgentFacets.Constraint,
	}
	for _, group := range groups {
		for _, value := range append(append([]string{}, group.Required...), group.Supporting...) {
			value = strings.TrimSpace(value)
			if value != "" {
				return value
			}
		}
	}
	return strings.TrimSpace(request.RawRequest)
}

func semanticIntakeAmbiguities(request SemanticIntakeRequest) []string {
	text := strings.ToLower(request.RawRequest + " " + strings.Join(semanticIntakeFacetStrings(request.AgentFacets), " "))
	if strings.Contains(text, "h5") {
		return []string{"H5 may mean mobile web or browser-hosted web surface"}
	}
	return nil
}

func normalizeSemanticIntakeFacetSet(facets SemanticIntakeFacetSet) SemanticIntakeFacetSet {
	facets.Goal = normalizeSemanticIntakeFacetGroup(facets.Goal)
	facets.Surface = normalizeSemanticIntakeFacetGroup(facets.Surface)
	facets.Behavior = normalizeSemanticIntakeFacetGroup(facets.Behavior)
	facets.Context = normalizeSemanticIntakeFacetGroup(facets.Context)
	facets.Constraint = normalizeSemanticIntakeFacetGroup(facets.Constraint)
	return facets
}

func normalizeSemanticIntakeFacetGroup(group SemanticIntakeFacetGroup) SemanticIntakeFacetGroup {
	group.Required = normalizeStrings(group.Required)
	group.Supporting = normalizeStrings(group.Supporting)
	group.Optional = normalizeStrings(group.Optional)
	return group
}

func semanticIntakeTextMatches(haystack string, needle string) bool {
	needle = strings.TrimSpace(needle)
	if needle == "" {
		return false
	}
	if strings.Contains(haystack, needle) {
		return true
	}
	return semanticIntakeTokenOverlap(needle, haystack)
}

func semanticIntakeTokenOverlap(needle string, haystack string) bool {
	tokens := semanticIntakeTokens(needle)
	if len(tokens) == 0 {
		return false
	}
	matches := 0
	for _, token := range tokens {
		if len([]rune(token)) < 2 {
			continue
		}
		if strings.Contains(haystack, token) {
			matches++
		}
	}
	return matches > 0 && matches*2 >= len(tokens)
}

func semanticIntakeTokens(value string) []string {
	return strings.FieldsFunc(strings.ToLower(value), func(r rune) bool {
		return !(unicode.IsLetter(r) || unicode.IsDigit(r) || r == '.' || r == '-' || r == '_')
	})
}
