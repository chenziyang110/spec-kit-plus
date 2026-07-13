package query

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strings"

	rt "github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/runtime"
	"github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/runtimegate"
	"github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/store"
)

const (
	CandidateUniverseVersion      = 1
	ClaimRetrievalContractVersion = 1
)

type conceptRef struct {
	GenerationID   string
	NodeID         string
	FallbackNodeID string
}

type ConceptDecision struct {
	ConceptID       string   `json:"concept_id"`
	Decision        string   `json:"decision"`
	SelectionReason string   `json:"selection_reason,omitempty"`
	CoveredFacets   []string `json:"covered_facets,omitempty"`
	MissingFacets   []string `json:"missing_facets,omitempty"`
	MatchSources    []string `json:"match_sources,omitempty"`
	Confidence      string   `json:"confidence,omitempty"`
	Paths           []string `json:"paths,omitempty"`
	Risk            string   `json:"risk,omitempty"`
}

type AliasInterpretation struct {
	Alias      string `json:"alias"`
	Meaning    string `json:"meaning"`
	Confidence string `json:"confidence,omitempty"`
}

type SemanticIntake struct {
	WorkflowIntent        string                `json:"workflow_intent,omitempty"`
	NormalizedQuery       string                `json:"normalized_query,omitempty"`
	IntentFacets          []string              `json:"intent_facets,omitempty"`
	NegativeConstraints   []string              `json:"negative_constraints,omitempty"`
	AliasInterpretations  []AliasInterpretation `json:"alias_interpretations,omitempty"`
	OpenSemanticQuestions []string              `json:"open_semantic_questions,omitempty"`
}

type Plan struct {
	RawQuery              string                `json:"raw_query,omitempty"`
	SemanticIntake        SemanticIntake        `json:"semantic_intake,omitempty"`
	WorkflowIntent        string                `json:"workflow_intent,omitempty"`
	NormalizedQuery       string                `json:"normalized_query,omitempty"`
	IntentFacets          []string              `json:"intent_facets,omitempty"`
	NegativeConstraints   []string              `json:"negative_constraints,omitempty"`
	AliasInterpretations  []AliasInterpretation `json:"alias_interpretations,omitempty"`
	OpenSemanticQuestions []string              `json:"open_semantic_questions,omitempty"`
	ExpandedQueries       []string              `json:"expanded_queries,omitempty"`
	RepositorySearchTerms []string              `json:"repository_search_terms,omitempty"`
	Paths                 []string              `json:"paths,omitempty"`
	PathHints             []string              `json:"path_hints,omitempty"`
	SelectedConcepts      []string              `json:"selected_concepts,omitempty"`
	RejectedConcepts      []string              `json:"rejected_concepts,omitempty"`
	ConceptDecisions      []ConceptDecision     `json:"concept_decisions,omitempty"`
	LexiconGenerationID   string                `json:"lexicon_generation_id,omitempty"`
	SelectionReason       string                `json:"selection_reason,omitempty"`
	Reason                string                `json:"reason,omitempty"`
}

type QueryInput struct {
	Intent          string
	Query           string
	ExpandedQuery   string
	Paths           []string
	Plan            Plan
	PlanDiagnostics PlanDiagnostics
}

type QueryPayload struct {
	EpistemicContract             EpistemicContract `json:"epistemic_contract"`
	ClaimRetrievalContractVersion int               `json:"claim_retrieval_contract_version"`
	BaselineHealth                map[string]any    `json:"baseline_health"`
	QueryCoverage                 map[string]any    `json:"query_coverage"`
	WorkflowRequirement           string            `json:"workflow_requirement"`
	PathAdoption                  map[string]any    `json:"path_adoption"`
	Readiness                     string            `json:"readiness"`
	RecommendedNextAction         string            `json:"recommended_next_action"`
	BaselineKind                  string            `json:"baseline_kind,omitempty"`
	Intent                        string            `json:"intent"`
	Query                         string            `json:"query"`
	QueryPlan                     Plan              `json:"query_plan"`
	SelectedConcepts              []string          `json:"selected_concepts"`
	RejectedConcepts              []string          `json:"rejected_concepts"`
	SelectionReason               string            `json:"selection_reason"`
	CapabilityCandidates          []map[string]any  `json:"capability_candidates"`
	SymptomCandidates             []map[string]any  `json:"symptom_candidates"`
	AffectedNodes                 []map[string]any  `json:"affected_nodes"`
	MinimalLiveReads              []string          `json:"minimal_live_reads"`
	MissingCoverage               []string          `json:"missing_coverage"`
	RoutePack                     map[string]any    `json:"route_pack"`
	Subgraph                      map[string]any    `json:"subgraph"`
	ClaimSignals                  []ClaimSignal     `json:"claim_signals,omitempty"`
	Warnings                      []string          `json:"warnings,omitempty"`
	RepairHints                   []string          `json:"repair_hints,omitempty"`
}

type PlanDiagnostics struct {
	Warnings      []string       `json:"warnings,omitempty"`
	RepairHints   []string       `json:"repair_hints,omitempty"`
	ExpectedShape map[string]any `json:"expected_shape,omitempty"`
}

type PlanParseError struct {
	Errors        []string
	Warnings      []string
	RepairHints   []string
	ExpectedShape map[string]any
}

func (err *PlanParseError) Error() string {
	if err == nil || len(err.Errors) == 0 {
		return "parse query plan"
	}
	return "parse query plan: " + strings.Join(err.Errors, "; ")
}

func ParsePlan(value, file string) (Plan, error) {
	plan, _, err := ParsePlanWithDiagnostics(value, file)
	return plan, err
}

func ParsePlanWithDiagnostics(value, file string) (Plan, PlanDiagnostics, error) {
	if file == "" && strings.HasPrefix(value, "@") {
		file = strings.TrimPrefix(value, "@")
		value = ""
	}
	var data []byte
	var err error
	switch {
	case file != "":
		data, err = os.ReadFile(file)
		if err != nil {
			return Plan{}, PlanDiagnostics{}, fmt.Errorf("read query plan file: %w", err)
		}
	case value != "":
		data = []byte(value)
	default:
		return Plan{}, PlanDiagnostics{}, nil
	}
	normalized, diagnostics, err := normalizePlanJSON(data)
	if err != nil {
		return Plan{}, diagnostics, err
	}
	var plan Plan
	if err := json.Unmarshal(normalized, &plan); err != nil {
		parseErr := planParseError(
			[]string{fmt.Sprintf("query_plan has unsupported field shape: %v", err)},
			diagnostics.Warnings,
			diagnostics.RepairHints,
		)
		return Plan{}, diagnostics, parseErr
	}
	return NormalizePlan(plan), diagnostics, nil
}

func NormalizePlan(plan Plan) Plan {
	if len(plan.Paths) == 0 && len(plan.PathHints) > 0 {
		plan.Paths = append([]string{}, plan.PathHints...)
	}
	if plan.SelectionReason == "" && plan.Reason != "" {
		plan.SelectionReason = plan.Reason
	}
	plan.WorkflowIntent = strings.TrimSpace(plan.WorkflowIntent)
	plan.NormalizedQuery = strings.TrimSpace(plan.NormalizedQuery)
	plan.IntentFacets = normalizeStrings(plan.IntentFacets)
	plan.NegativeConstraints = normalizeStrings(plan.NegativeConstraints)
	plan.AliasInterpretations = normalizeAliasInterpretations(plan.AliasInterpretations)
	plan.OpenSemanticQuestions = normalizeStrings(plan.OpenSemanticQuestions)
	plan.SemanticIntake = normalizeSemanticIntake(mergeSemanticIntakeAliases(plan.SemanticIntake, plan))
	plan.RepositorySearchTerms = normalizeStrings(plan.RepositorySearchTerms)
	plan.Paths = normalizePaths(plan.Paths)
	plan.PathHints = normalizePaths(plan.PathHints)
	plan.SelectedConcepts = normalizeStrings(plan.SelectedConcepts)
	plan.RejectedConcepts = normalizeStrings(plan.RejectedConcepts)
	plan.ConceptDecisions = normalizeConceptDecisions(plan.ConceptDecisions, plan.SelectedConcepts, plan.RejectedConcepts, plan.SelectionReason)
	return plan
}

func normalizePlanJSON(data []byte) ([]byte, PlanDiagnostics, error) {
	var payload map[string]any
	if err := json.Unmarshal(data, &payload); err != nil {
		return nil, PlanDiagnostics{}, planParseError(
			[]string{fmt.Sprintf("query_plan must be a JSON object: %v", err)},
			nil,
			nil,
		)
	}
	diagnostics := PlanDiagnostics{}
	if err := normalizeAliasInterpretationPayload(payload, "alias_interpretations", "coerced_top_level_alias_interpretations", &diagnostics); err != nil {
		return nil, diagnostics, err
	}
	if rawIntake, ok := payload["semantic_intake"]; ok && rawIntake != nil {
		intake, ok := rawIntake.(map[string]any)
		if !ok {
			return nil, diagnostics, planParseError(
				[]string{"semantic_intake must be an object"},
				diagnostics.Warnings,
				diagnostics.RepairHints,
			)
		}
		if err := normalizeAliasInterpretationPayload(intake, "semantic_intake.alias_interpretations", "coerced_semantic_intake_alias_interpretations", &diagnostics); err != nil {
			return nil, diagnostics, err
		}
	}
	if generationID, ok := payload["lexicon_generation_id"].(string); !ok || strings.TrimSpace(generationID) == "" {
		appendDiagnostic(&diagnostics.Warnings, "query_plan_missing_lexicon_generation_id")
		appendDiagnostic(&diagnostics.RepairHints, "Carry lexicon_generation_id from the project-cognition lexicon payload into the query_plan.")
	}
	normalized, err := json.Marshal(payload)
	if err != nil {
		return nil, diagnostics, planParseError(
			[]string{fmt.Sprintf("normalize query_plan: %v", err)},
			diagnostics.Warnings,
			diagnostics.RepairHints,
		)
	}
	return normalized, diagnostics, nil
}

func normalizeAliasInterpretationPayload(container map[string]any, fieldPath string, warning string, diagnostics *PlanDiagnostics) error {
	raw, ok := container["alias_interpretations"]
	if !ok || raw == nil {
		return nil
	}
	items, ok := raw.([]any)
	if !ok {
		return unsupportedAliasInterpretationsError(fieldPath, *diagnostics)
	}
	converted := make([]any, 0, len(items))
	sawString := false
	sawObject := false
	for _, item := range items {
		switch typed := item.(type) {
		case string:
			value := strings.TrimSpace(typed)
			if value == "" {
				continue
			}
			sawString = true
			converted = append(converted, map[string]any{
				"alias":      value,
				"meaning":    value,
				"confidence": "low",
			})
		case map[string]any:
			sawObject = true
			normalized, err := normalizeAliasInterpretationObject(typed, fieldPath, *diagnostics)
			if err != nil {
				return err
			}
			converted = append(converted, normalized)
		default:
			return unsupportedAliasInterpretationsError(fieldPath, *diagnostics)
		}
	}
	if sawString && sawObject {
		return planParseError(
			[]string{fieldPath + " must not mix string aliases with object aliases"},
			diagnostics.Warnings,
			diagnostics.RepairHints,
		)
	}
	if sawString {
		container["alias_interpretations"] = converted
		appendDiagnostic(&diagnostics.Warnings, warning)
		appendDiagnostic(&diagnostics.RepairHints, "Use alias_interpretations as objects with alias, meaning, and optional confidence fields.")
	}
	return nil
}

func normalizeAliasInterpretationObject(value map[string]any, fieldPath string, diagnostics PlanDiagnostics) (map[string]any, error) {
	out := map[string]any{}
	for _, key := range []string{"alias", "meaning", "confidence"} {
		raw, ok := value[key]
		if !ok || raw == nil {
			continue
		}
		text, ok := raw.(string)
		if !ok {
			return nil, unsupportedAliasInterpretationsError(fieldPath, diagnostics)
		}
		out[key] = strings.TrimSpace(text)
	}
	for key, raw := range value {
		if key == "alias" || key == "meaning" || key == "confidence" {
			continue
		}
		out[key] = raw
	}
	return out, nil
}

func unsupportedAliasInterpretationsError(fieldPath string, diagnostics PlanDiagnostics) *PlanParseError {
	return planParseError(
		[]string{fieldPath + " must be an array of objects with string alias, meaning, and confidence fields"},
		diagnostics.Warnings,
		diagnostics.RepairHints,
	)
}

func planParseError(errors []string, warnings []string, repairHints []string) *PlanParseError {
	hints := append([]string{}, repairHints...)
	appendDiagnostic(&hints, "Use alias_interpretations as objects with alias, meaning, and optional confidence fields.")
	return &PlanParseError{
		Errors:        errors,
		Warnings:      append([]string{}, warnings...),
		RepairHints:   hints,
		ExpectedShape: expectedQueryPlanShape(),
	}
}

func expectedQueryPlanShape() map[string]any {
	return map[string]any{
		"alias_interpretations": []map[string]string{
			{"alias": "<user term>", "meaning": "<project term>", "confidence": "medium"},
		},
		"semantic_intake": map[string]any{
			"alias_interpretations": []map[string]string{
				{"alias": "<user term>", "meaning": "<project term>", "confidence": "medium"},
			},
		},
	}
}

func appendDiagnostic(values *[]string, value string) {
	value = strings.TrimSpace(value)
	if value == "" {
		return
	}
	for _, existing := range *values {
		if existing == value {
			return
		}
	}
	*values = append(*values, value)
}

func Run(paths rt.Paths, input QueryInput) (QueryPayload, error) {
	if err := blockSplitBrainBaseline(paths); err != nil {
		return QueryPayload{}, err
	}
	status, err := rt.ReadStatus(paths)
	if err != nil {
		return QueryPayload{}, err
	}
	plan := NormalizePlan(input.Plan)
	if plan.RawQuery == "" {
		plan.RawQuery = input.Query
	}
	if input.ExpandedQuery != "" && len(plan.ExpandedQueries) == 0 {
		plan.ExpandedQueries = []string{input.ExpandedQuery}
	}
	if len(plan.Paths) == 0 {
		plan.Paths = normalizePaths(input.Paths)
	}
	if status.BaselineKind == rt.BaselineKindGreenfieldEmpty {
		readCandidates := []string{
			".specify/memory/constitution.md",
			".specify/memory/project-rules.md",
			"AGENTS.md",
		}
		readCandidates = append(readCandidates, plan.Paths...)
		readCandidates = append(readCandidates, plan.PathHints...)
		reads := normalizePaths(readCandidates)
		return QueryPayload{
			EpistemicContract:             NewEpistemicContract(),
			ClaimRetrievalContractVersion: ClaimRetrievalContractVersion,
			BaselineHealth: map[string]any{
				"freshness":     status.Freshness,
				"readiness":     status.Readiness,
				"dirty":         status.Dirty,
				"baseline_kind": status.BaselineKind,
			},
			QueryCoverage:         map[string]any{"paths": plan.Paths, "nodes": 0, "baseline_kind": status.BaselineKind},
			WorkflowRequirement:   "use_greenfield_workflow_artifacts_then_live_requirements",
			PathAdoption:          map[string]any{"paths": plan.Paths},
			Readiness:             status.Readiness,
			RecommendedNextAction: status.RecommendedNextAction,
			BaselineKind:          status.BaselineKind,
			Intent:                input.Intent,
			Query:                 input.Query,
			QueryPlan:             plan,
			SelectedConcepts:      plan.SelectedConcepts,
			RejectedConcepts:      plan.RejectedConcepts,
			SelectionReason:       plan.SelectionReason,
			CapabilityCandidates:  []map[string]any{},
			SymptomCandidates:     []map[string]any{},
			AffectedNodes:         []map[string]any{},
			MinimalLiveReads:      reads,
			MissingCoverage:       []string{"greenfield_empty_no_project_code"},
			RoutePack: map[string]any{
				"items":              []map[string]any{},
				"routes":             plan.Paths,
				"minimal_live_reads": reads,
				"why_these_reads":    "Greenfield empty baseline has no project source graph yet; use workflow artifacts and live requirements.",
			},
			Subgraph: map[string]any{
				"nodes":     []map[string]any{},
				"edges":     []map[string]any{},
				"claims":    []map[string]any{},
				"conflicts": []map[string]any{},
			},
			Warnings:    input.PlanDiagnostics.Warnings,
			RepairHints: input.PlanDiagnostics.RepairHints,
		}, nil
	}
	nodes := []map[string]any{}
	missingCoverage := []string{}
	st, err := store.OpenExisting(paths)
	if errors.Is(err, os.ErrNotExist) {
		st = nil
		err = nil
	}
	if err != nil {
		return QueryPayload{}, err
	}
	if st != nil {
		defer st.Close()
		activeGenerationID, err := st.ActiveGenerationID(context.Background())
		if err != nil {
			return QueryPayload{}, err
		}
		if plan.LexiconGenerationID != "" && activeGenerationID != "" && plan.LexiconGenerationID != activeGenerationID {
			return generationMismatchPayload(status, input, plan, activeGenerationID), nil
		}
		if hasSemanticIntake(plan.SemanticIntake) && len(plan.SelectedConcepts) == 0 {
			rows, err := st.AllActiveConceptCandidateRows(context.Background())
			if err != nil {
				return QueryPayload{}, err
			}
			plan, missingCoverage = applySemanticIntakeSelection(plan, rows, activeGenerationID)
		}
		if len(plan.SelectedConcepts) > 0 {
			var nodeIDs []string
			var selectedRefs []selectedConceptRef
			var selectedMissingCoverage []string
			selectedRefs, selectedMissingCoverage = selectedConceptRefs(plan.SelectedConcepts, activeGenerationID)
			missingCoverage = appendUniqueStrings(missingCoverage, selectedMissingCoverage...)
			nodeCandidates := selectedNodeIDCandidates(selectedRefs)
			nodes, err = st.NodesForIDs(context.Background(), nodeCandidates)
			if err != nil {
				return QueryPayload{}, err
			}
			resolvedNodeIDs := nodeIDsFromNodes(nodes)
			nodeIDs, missingConcepts := resolveSelectedNodeIDs(selectedRefs, resolvedNodeIDs)
			for _, conceptID := range missingConcepts {
				missingCoverage = appendMissingCoverage(missingCoverage, "unknown_selected_concept:"+conceptID)
			}
			nodes, err = st.NodesForIDs(context.Background(), nodeIDs)
			if err != nil {
				return QueryPayload{}, err
			}
			if len(plan.Paths) == 0 && len(nodes) > 0 {
				plan.Paths = pathsFromNodes(nodes)
			}
		}
		if len(nodes) == 0 && (len(plan.SelectedConcepts) == 0 || len(plan.Paths) > 0) {
			nodes, err = st.NodesForPaths(context.Background(), plan.Paths)
			if err != nil {
				return QueryPayload{}, err
			}
		}
	}
	reads := normalizePaths(append(append([]string{}, plan.Paths...), pathsFromNodes(nodes)...))
	if len(reads) == 0 {
		reads = []string{".specify/project-cognition/status.json", ".specify/project-cognition/project-cognition.db"}
	}
	readiness := status.Readiness
	recommendedNextAction := status.RecommendedNextAction
	if shouldReviewMissingCoverage(missingCoverage) && status.Readiness == rt.ReadyReadiness {
		readiness = "review"
		recommendedNextAction = "use_minimal_live_reads_and_review_missing_coverage"
	}
	claims := []map[string]any{}
	claimSignalPackets := []ClaimSignal{}
	if st != nil {
		claimRecords, readErr := st.ClaimEvidenceForNodeIDs(context.Background(), nodeIDListFromNodes(nodes))
		err = readErr
		if err != nil {
			return QueryPayload{}, err
		}
		claims = compactGraphClaims(claimRecords)
		claimSignalPackets = claimSignals(claimRecords, maxQueryClaimSignals, maxQueryClaimEvidenceRefs)
	}
	routePack := map[string]any{
		"items":              nodes,
		"routes":             plan.Paths,
		"minimal_live_reads": reads,
		"claims":             claims,
		"why_these_reads":    "Selected from query plan paths and active project cognition graph metadata.",
	}
	subgraph := map[string]any{
		"nodes":     nodes,
		"edges":     []map[string]any{},
		"claims":    claims,
		"conflicts": []map[string]any{},
	}
	return QueryPayload{
		EpistemicContract:             NewEpistemicContract(),
		ClaimRetrievalContractVersion: ClaimRetrievalContractVersion,
		BaselineHealth: map[string]any{
			"freshness":     status.Freshness,
			"readiness":     status.Readiness,
			"dirty":         status.Dirty,
			"baseline_kind": status.BaselineKind,
		},
		QueryCoverage: map[string]any{
			"paths":         plan.Paths,
			"nodes":         len(nodes),
			"baseline_kind": status.BaselineKind,
		},
		WorkflowRequirement:   "use_project_cognition_then_minimal_live_reads",
		PathAdoption:          map[string]any{"paths": plan.Paths},
		Readiness:             readiness,
		RecommendedNextAction: recommendedNextAction,
		BaselineKind:          status.BaselineKind,
		Intent:                input.Intent,
		Query:                 input.Query,
		QueryPlan:             plan,
		SelectedConcepts:      plan.SelectedConcepts,
		RejectedConcepts:      plan.RejectedConcepts,
		SelectionReason:       plan.SelectionReason,
		CapabilityCandidates:  nodes,
		SymptomCandidates:     []map[string]any{},
		AffectedNodes:         nodes,
		MinimalLiveReads:      reads,
		MissingCoverage:       missingCoverage,
		RoutePack:             routePack,
		Subgraph:              subgraph,
		ClaimSignals:          claimSignalPackets,
		Warnings:              input.PlanDiagnostics.Warnings,
		RepairHints:           input.PlanDiagnostics.RepairHints,
	}, nil
}

func blockSplitBrainBaseline(paths rt.Paths) error {
	return runtimegate.BlockIfExisting(paths)
}

func normalizePaths(paths []string) []string {
	seen := map[string]bool{}
	out := make([]string, 0, len(paths))
	for _, path := range paths {
		path = filepath.ToSlash(strings.TrimSpace(strings.TrimPrefix(path, "./")))
		if path == "" || seen[path] {
			continue
		}
		seen[path] = true
		out = append(out, path)
	}
	return out
}

func normalizeStrings(values []string) []string {
	seen := map[string]bool{}
	out := make([]string, 0, len(values))
	for _, value := range values {
		value = strings.TrimSpace(value)
		if value == "" || seen[value] {
			continue
		}
		seen[value] = true
		out = append(out, value)
	}
	return out
}

func normalizeSemanticIntake(intake SemanticIntake) SemanticIntake {
	intake.WorkflowIntent = strings.TrimSpace(intake.WorkflowIntent)
	intake.NormalizedQuery = strings.TrimSpace(intake.NormalizedQuery)
	intake.IntentFacets = normalizeStrings(intake.IntentFacets)
	intake.NegativeConstraints = normalizeStrings(intake.NegativeConstraints)
	intake.OpenSemanticQuestions = normalizeStrings(intake.OpenSemanticQuestions)
	intake.AliasInterpretations = normalizeAliasInterpretations(intake.AliasInterpretations)
	return intake
}

func mergeSemanticIntakeAliases(intake SemanticIntake, plan Plan) SemanticIntake {
	if intake.WorkflowIntent == "" {
		intake.WorkflowIntent = plan.WorkflowIntent
	}
	if intake.NormalizedQuery == "" {
		intake.NormalizedQuery = plan.NormalizedQuery
	}
	if len(intake.IntentFacets) == 0 {
		intake.IntentFacets = append([]string{}, plan.IntentFacets...)
	}
	if len(intake.NegativeConstraints) == 0 {
		intake.NegativeConstraints = append([]string{}, plan.NegativeConstraints...)
	}
	if len(intake.AliasInterpretations) == 0 {
		intake.AliasInterpretations = append([]AliasInterpretation{}, plan.AliasInterpretations...)
	}
	if len(intake.OpenSemanticQuestions) == 0 {
		intake.OpenSemanticQuestions = append([]string{}, plan.OpenSemanticQuestions...)
	}
	return intake
}

func normalizeAliasInterpretations(values []AliasInterpretation) []AliasInterpretation {
	seenAliases := map[string]bool{}
	interpretations := make([]AliasInterpretation, 0, len(values))
	for _, interpretation := range values {
		interpretation.Alias = strings.TrimSpace(interpretation.Alias)
		interpretation.Meaning = strings.TrimSpace(interpretation.Meaning)
		interpretation.Confidence = strings.TrimSpace(interpretation.Confidence)
		if interpretation.Alias == "" && interpretation.Meaning == "" {
			continue
		}
		key := interpretation.Alias + "\x00" + interpretation.Meaning
		if seenAliases[key] {
			continue
		}
		seenAliases[key] = true
		interpretations = append(interpretations, interpretation)
	}
	return interpretations
}

func hasSemanticIntake(intake SemanticIntake) bool {
	return intake.WorkflowIntent != "" ||
		intake.NormalizedQuery != "" ||
		len(intake.IntentFacets) > 0 ||
		len(intake.NegativeConstraints) > 0 ||
		len(intake.AliasInterpretations) > 0 ||
		len(intake.OpenSemanticQuestions) > 0
}

func parseConceptID(value string) (conceptRef, bool) {
	value = strings.TrimSpace(value)
	if !strings.HasPrefix(value, "concept:") {
		return conceptRef{}, false
	}
	generationID, nodeID, ok := strings.Cut(strings.TrimPrefix(value, "concept:"), ":")
	if !ok || generationID == "" || nodeID == "" {
		return conceptRef{}, false
	}
	ref := conceptRef{GenerationID: generationID, NodeID: nodeID}
	if fallbackNodeID, _, ok := strings.Cut(nodeID, ":"); ok {
		ref.FallbackNodeID = fallbackNodeID
	}
	return ref, true
}

type selectedConceptRef struct {
	ConceptID      string
	NodeID         string
	FallbackNodeID string
}

func selectedConceptRefs(selectedConcepts []string, activeGenerationID string) ([]selectedConceptRef, []string) {
	refs := []selectedConceptRef{}
	missingCoverage := []string{}
	seenConceptIDs := map[string]bool{}
	for _, conceptID := range selectedConcepts {
		conceptID = strings.TrimSpace(conceptID)
		if conceptID == "" || seenConceptIDs[conceptID] {
			continue
		}
		seenConceptIDs[conceptID] = true
		ref, ok := parseConceptID(conceptID)
		nodeID := conceptID
		fallbackNodeID := ""
		if ok {
			if activeGenerationID != "" && ref.GenerationID != activeGenerationID {
				missingCoverage = append(missingCoverage, "selected_concept_generation_mismatch:"+conceptID)
				continue
			}
			nodeID = ref.NodeID
			fallbackNodeID = ref.FallbackNodeID
		}
		if nodeID == "" {
			continue
		}
		refs = append(refs, selectedConceptRef{
			ConceptID:      conceptID,
			NodeID:         nodeID,
			FallbackNodeID: fallbackNodeID,
		})
	}
	return refs, missingCoverage
}

func selectedNodeIDCandidates(refs []selectedConceptRef) []string {
	nodeIDs := []string{}
	seenNodeIDs := map[string]bool{}
	for _, ref := range refs {
		for _, nodeID := range []string{ref.NodeID, ref.FallbackNodeID} {
			if nodeID == "" || seenNodeIDs[nodeID] {
				continue
			}
			seenNodeIDs[nodeID] = true
			nodeIDs = append(nodeIDs, nodeID)
		}
	}
	return nodeIDs
}

func resolveSelectedNodeIDs(refs []selectedConceptRef, resolvedNodeIDs map[string]bool) ([]string, []string) {
	nodeIDs := []string{}
	missingConcepts := []string{}
	seenNodeIDs := map[string]bool{}
	for _, ref := range refs {
		nodeID := ref.NodeID
		if !resolvedNodeIDs[nodeID] && ref.FallbackNodeID != "" && resolvedNodeIDs[ref.FallbackNodeID] {
			nodeID = ref.FallbackNodeID
		}
		if !resolvedNodeIDs[nodeID] {
			missingConcepts = append(missingConcepts, ref.ConceptID)
			continue
		}
		if seenNodeIDs[nodeID] {
			continue
		}
		seenNodeIDs[nodeID] = true
		nodeIDs = append(nodeIDs, nodeID)
	}
	return nodeIDs, missingConcepts
}

func pathsFromNodes(nodes []map[string]any) []string {
	paths := make([]string, 0, len(nodes))
	for _, node := range nodes {
		path, ok := node["path"].(string)
		if !ok {
			continue
		}
		paths = append(paths, path)
	}
	return normalizePaths(paths)
}

func nodeIDsFromNodes(nodes []map[string]any) map[string]bool {
	ids := map[string]bool{}
	for _, node := range nodes {
		id, ok := node["id"].(string)
		if !ok {
			continue
		}
		ids[id] = true
	}
	return ids
}

func nodeIDListFromNodes(nodes []map[string]any) []string {
	ids := nodeIDsFromNodes(nodes)
	out := make([]string, 0, len(ids))
	for id := range ids {
		out = append(out, id)
	}
	sort.Strings(out)
	return out
}

func appendMissingCoverage(values []string, value string) []string {
	for _, existing := range values {
		if existing == value {
			return values
		}
	}
	return append(values, value)
}

func appendUniqueStrings(values []string, additions ...string) []string {
	for _, addition := range additions {
		values = appendMissingCoverage(values, addition)
	}
	return values
}

func shouldReviewMissingCoverage(missingCoverage []string) bool {
	for _, value := range missingCoverage {
		if strings.HasPrefix(value, "unknown_selected_concept:") ||
			strings.HasPrefix(value, "selected_concept_generation_mismatch:") ||
			value == "semantic_intake_partial_facet_coverage" ||
			value == "semantic_intake_facets_uncovered" {
			return true
		}
	}
	return false
}

func generationMismatchPayload(status rt.Status, input QueryInput, plan Plan, activeGenerationID string) QueryPayload {
	reads := []string{".specify/project-cognition/status.json", ".specify/project-cognition/project-cognition.db"}
	return QueryPayload{
		EpistemicContract:             NewEpistemicContract(),
		ClaimRetrievalContractVersion: ClaimRetrievalContractVersion,
		BaselineHealth: map[string]any{
			"freshness":             status.Freshness,
			"readiness":             status.Readiness,
			"dirty":                 status.Dirty,
			"baseline_kind":         status.BaselineKind,
			"active_generation_id":  activeGenerationID,
			"lexicon_generation_id": plan.LexiconGenerationID,
		},
		QueryCoverage: map[string]any{
			"paths":                 plan.Paths,
			"nodes":                 0,
			"baseline_kind":         status.BaselineKind,
			"active_generation_id":  activeGenerationID,
			"lexicon_generation_id": plan.LexiconGenerationID,
		},
		WorkflowRequirement:   "use_project_cognition_then_minimal_live_reads",
		PathAdoption:          map[string]any{"paths": plan.Paths},
		Readiness:             rt.ReviewReadiness,
		RecommendedNextAction: "rerun_project_cognition_lexicon",
		BaselineKind:          status.BaselineKind,
		Intent:                input.Intent,
		Query:                 input.Query,
		QueryPlan:             plan,
		SelectedConcepts:      plan.SelectedConcepts,
		RejectedConcepts:      plan.RejectedConcepts,
		SelectionReason:       plan.SelectionReason,
		CapabilityCandidates:  []map[string]any{},
		SymptomCandidates:     []map[string]any{},
		AffectedNodes:         []map[string]any{},
		MinimalLiveReads:      reads,
		MissingCoverage:       []string{"lexicon_generation_mismatch"},
		RoutePack: map[string]any{
			"items":              []map[string]any{},
			"routes":             plan.Paths,
			"minimal_live_reads": reads,
			"why_these_reads":    "Lexicon generation does not match the active project cognition graph; rerun lexicon before interpreting selected concepts.",
		},
		Subgraph: map[string]any{
			"nodes":     []map[string]any{},
			"edges":     []map[string]any{},
			"claims":    []map[string]any{},
			"conflicts": []map[string]any{},
		},
		Warnings:    input.PlanDiagnostics.Warnings,
		RepairHints: input.PlanDiagnostics.RepairHints,
	}
}

type semanticCandidateDecision struct {
	conceptID       string
	paths           []string
	coveredFacets   []string
	missingFacets   []string
	matchSources    []string
	score           int
	negativeOverlap bool
}

func applySemanticIntakeSelection(plan Plan, rows []store.ConceptCandidateRow, activeGenerationID string) (Plan, []string) {
	if activeGenerationID == "" && len(rows) > 0 {
		activeGenerationID = rows[0].GenerationID
	}
	if plan.LexiconGenerationID == "" {
		plan.LexiconGenerationID = activeGenerationID
	}
	decisions := make([]semanticCandidateDecision, 0, len(rows))
	for _, row := range rows {
		decision := semanticDecisionForRow(row, plan.SemanticIntake)
		if decision.conceptID == "" {
			continue
		}
		decisions = append(decisions, decision)
	}
	missingCoverage := []string{}
	requiredFacets := plan.SemanticIntake.IntentFacets
	selected := selectSemanticCoverageDecisions(decisions, requiredFacets)
	if len(selected) == 0 {
		if len(requiredFacets) > 0 {
			missingCoverage = appendMissingCoverage(missingCoverage, "semantic_intake_facets_uncovered")
		}
		return plan, missingCoverage
	}
	coveredBySelected := []string{}
	for _, selectedDecision := range selected {
		coveredBySelected = appendUniqueStrings(coveredBySelected, selectedDecision.coveredFacets...)
	}
	aggregateMissingFacets := missingFacetValues(requiredFacets, coveredBySelected)
	for _, selectedDecision := range selected {
		plan.SelectedConcepts = appendMissingCoverage(plan.SelectedConcepts, selectedDecision.conceptID)
		plan.Paths = appendUniqueStrings(plan.Paths, selectedDecision.paths...)
		plan.ConceptDecisions = append(plan.ConceptDecisions, ConceptDecision{
			ConceptID:       selectedDecision.conceptID,
			Decision:        "selected",
			SelectionReason: "Selected by semantic_intake runtime fallback for facet coverage over normalized query and project aliases.",
			CoveredFacets:   selectedDecision.coveredFacets,
			MissingFacets:   missingFacetValues(requiredFacets, selectedDecision.coveredFacets),
			MatchSources:    selectedDecision.matchSources,
			Confidence:      confidenceForCoverage(coveredBySelected, requiredFacets),
			Paths:           selectedDecision.paths,
		})
	}
	if len(aggregateMissingFacets) > 0 {
		missingCoverage = appendMissingCoverage(missingCoverage, "semantic_intake_partial_facet_coverage")
	}
	selectedIDs := map[string]bool{}
	for _, selectedDecision := range selected {
		selectedIDs[selectedDecision.conceptID] = true
	}
	for _, decision := range decisions {
		if selectedIDs[decision.conceptID] {
			continue
		}
		if decision.negativeOverlap || len(decision.coveredFacets) > 0 {
			plan.RejectedConcepts = appendMissingCoverage(plan.RejectedConcepts, decision.conceptID)
			risk := "insufficient facet coverage"
			reason := "Rejected because semantic_intake facet coverage is weaker than the selected concept."
			if decision.negativeOverlap {
				risk = "lexical false positive"
				reason = "Matches surface wording or a negative constraint but misses core semantic_intake facets."
			}
			plan.ConceptDecisions = append(plan.ConceptDecisions, ConceptDecision{
				ConceptID:       decision.conceptID,
				Decision:        "rejected",
				SelectionReason: reason,
				CoveredFacets:   decision.coveredFacets,
				MissingFacets:   decision.missingFacets,
				MatchSources:    decision.matchSources,
				Confidence:      "medium",
				Paths:           decision.paths,
				Risk:            risk,
			})
		}
	}
	plan.ConceptDecisions = normalizeConceptDecisions(plan.ConceptDecisions, plan.SelectedConcepts, plan.RejectedConcepts, plan.SelectionReason)
	return plan, missingCoverage
}

func selectSemanticCoverageDecisions(decisions []semanticCandidateDecision, requiredFacets []string) []semanticCandidateDecision {
	remaining := map[string]bool{}
	for _, facet := range requiredFacets {
		remaining[facet] = true
	}
	selected := []semanticCandidateDecision{}
	used := map[string]bool{}
	for {
		bestIndex := -1
		bestNewCoverage := 0
		for i, decision := range decisions {
			if used[decision.conceptID] || decision.negativeOverlap || len(decision.coveredFacets) == 0 {
				continue
			}
			newCoverage := countNewFacetCoverage(decision.coveredFacets, remaining)
			if bestIndex == -1 ||
				newCoverage > bestNewCoverage ||
				(newCoverage == bestNewCoverage && decision.score > decisions[bestIndex].score) {
				bestIndex = i
				bestNewCoverage = newCoverage
			}
		}
		if bestIndex == -1 {
			break
		}
		if len(requiredFacets) > 0 && bestNewCoverage == 0 {
			break
		}
		decision := decisions[bestIndex]
		selected = append(selected, decision)
		used[decision.conceptID] = true
		for _, facet := range decision.coveredFacets {
			delete(remaining, facet)
		}
		if len(remaining) == 0 {
			break
		}
	}
	return selected
}

func countNewFacetCoverage(coveredFacets []string, remaining map[string]bool) int {
	if len(remaining) == 0 {
		return len(coveredFacets)
	}
	count := 0
	for _, facet := range coveredFacets {
		if remaining[facet] {
			count++
		}
	}
	return count
}

func semanticDecisionForRow(row store.ConceptCandidateRow, intake SemanticIntake) semanticCandidateDecision {
	candidate := newRankedConceptCandidate(row)
	conceptID := "concept:" + row.GenerationID + ":" + row.NodeID
	searchMaterial := strings.ToLower(strings.Join(uniqueStrings(append(append([]string{
		row.NodeID,
		row.NodeType,
		row.Title,
		attrString(candidate.attrs, "domain"),
		attrString(candidate.attrs, "owner"),
	}, candidate.aliases...), candidate.paths...)), " "))
	coveredFacets := []string{}
	matchSources := []string{}
	for _, facet := range intake.IntentFacets {
		if semanticMaterialMatches(searchMaterial, facet) {
			coveredFacets = appendMissingCoverage(coveredFacets, facet)
			matchSources = appendMissingCoverage(matchSources, "intent_facets")
		}
	}
	if semanticMaterialMatches(searchMaterial, intake.NormalizedQuery) {
		matchSources = appendMissingCoverage(matchSources, "semantic_intake")
	}
	for _, interpretation := range intake.AliasInterpretations {
		if semanticMaterialMatches(searchMaterial, interpretation.Alias) || semanticMaterialMatches(searchMaterial, interpretation.Meaning) {
			matchSources = appendMissingCoverage(matchSources, "alias")
			if interpretation.Meaning != "" {
				for _, facet := range intake.IntentFacets {
					if semanticMaterialMatches(strings.ToLower(interpretation.Meaning), facet) {
						coveredFacets = appendMissingCoverage(coveredFacets, facet)
					}
				}
			}
		}
	}
	if len(candidate.paths) > 0 {
		for _, facet := range coveredFacets {
			for _, path := range candidate.paths {
				if semanticMaterialMatches(strings.ToLower(path), facet) {
					matchSources = appendMissingCoverage(matchSources, "path")
					break
				}
			}
		}
	}
	missingFacets := missingFacetValues(intake.IntentFacets, coveredFacets)
	negativeOverlap := false
	for _, constraint := range intake.NegativeConstraints {
		if semanticMaterialMatches(searchMaterial, constraint) {
			negativeOverlap = true
			matchSources = appendMissingCoverage(matchSources, "negative_constraints")
		}
	}
	score := len(coveredFacets)*10 + len(matchSources)
	if negativeOverlap {
		score -= 25
	}
	return semanticCandidateDecision{
		conceptID:       conceptID,
		paths:           candidate.paths,
		coveredFacets:   coveredFacets,
		missingFacets:   missingFacets,
		matchSources:    matchSources,
		score:           score,
		negativeOverlap: negativeOverlap,
	}
}

func semanticMaterialMatches(material, phrase string) bool {
	material = strings.ToLower(strings.TrimSpace(material))
	phrase = strings.ToLower(strings.TrimSpace(phrase))
	if material == "" || phrase == "" {
		return false
	}
	if strings.Contains(material, phrase) {
		return true
	}
	terms := termsFrom(phrase, 20)
	if len(terms) == 0 {
		return false
	}
	matched := 0
	for _, term := range terms {
		if len(term) < 3 {
			continue
		}
		if strings.Contains(material, term) {
			matched++
		}
	}
	if matched == 0 {
		return false
	}
	return matched == len(terms) || matched >= 2
}

func missingFacetValues(required, covered []string) []string {
	coveredSet := map[string]bool{}
	for _, value := range covered {
		coveredSet[value] = true
	}
	missing := []string{}
	for _, value := range required {
		if !coveredSet[value] {
			missing = appendMissingCoverage(missing, value)
		}
	}
	return missing
}

func confidenceForCoverage(covered, required []string) string {
	switch {
	case len(required) == 0:
		return "medium"
	case len(covered) >= len(required):
		return "high"
	case len(covered) >= 2:
		return "medium"
	default:
		return "low"
	}
}

func normalizeConceptDecisions(decisions []ConceptDecision, selectedConcepts, rejectedConcepts []string, selectionReason string) []ConceptDecision {
	seen := map[string]bool{}
	out := make([]ConceptDecision, 0, len(decisions)+len(selectedConcepts)+len(rejectedConcepts))
	for _, decision := range decisions {
		decision.ConceptID = strings.TrimSpace(decision.ConceptID)
		decision.Decision = strings.TrimSpace(decision.Decision)
		decision.SelectionReason = strings.TrimSpace(decision.SelectionReason)
		decision.Confidence = strings.TrimSpace(decision.Confidence)
		decision.Risk = strings.TrimSpace(decision.Risk)
		decision.Paths = normalizePaths(decision.Paths)
		decision.CoveredFacets = normalizeStrings(decision.CoveredFacets)
		decision.MissingFacets = normalizeStrings(decision.MissingFacets)
		decision.MatchSources = normalizeStrings(decision.MatchSources)
		if decision.ConceptID == "" || decision.Decision == "" {
			continue
		}
		key := decision.ConceptID + "\x00" + decision.Decision
		if seen[key] {
			continue
		}
		seen[key] = true
		out = append(out, decision)
	}
	for _, conceptID := range selectedConcepts {
		out = appendMissingConceptDecision(out, seen, conceptID, "selected", selectionReason)
	}
	for _, conceptID := range rejectedConcepts {
		out = appendMissingConceptDecision(out, seen, conceptID, "rejected", selectionReason)
	}
	return out
}

func appendMissingConceptDecision(out []ConceptDecision, seen map[string]bool, conceptID, decision, selectionReason string) []ConceptDecision {
	conceptID = strings.TrimSpace(conceptID)
	decision = strings.TrimSpace(decision)
	if conceptID == "" || decision == "" {
		return out
	}
	key := conceptID + "\x00" + decision
	if seen[key] {
		return out
	}
	seen[key] = true
	return append(out, ConceptDecision{
		ConceptID:       conceptID,
		Decision:        decision,
		SelectionReason: strings.TrimSpace(selectionReason),
	})
}
