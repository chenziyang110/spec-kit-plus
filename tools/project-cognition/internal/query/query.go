package query

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"strings"

	rt "github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/runtime"
	"github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/runtimegate"
	"github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/store"
)

const CandidateUniverseVersion = 1

type ConceptDecision struct {
	ConceptID       string   `json:"concept_id"`
	Decision        string   `json:"decision"`
	SelectionReason string   `json:"selection_reason,omitempty"`
	Confidence      string   `json:"confidence,omitempty"`
	Paths           []string `json:"paths,omitempty"`
	Risk            string   `json:"risk,omitempty"`
}

type Plan struct {
	RawQuery            string            `json:"raw_query,omitempty"`
	ExpandedQueries     []string          `json:"expanded_queries,omitempty"`
	Paths               []string          `json:"paths,omitempty"`
	PathHints           []string          `json:"path_hints,omitempty"`
	SelectedConcepts    []string          `json:"selected_concepts,omitempty"`
	RejectedConcepts    []string          `json:"rejected_concepts,omitempty"`
	ConceptDecisions    []ConceptDecision `json:"concept_decisions,omitempty"`
	LexiconGenerationID string            `json:"lexicon_generation_id,omitempty"`
	SelectionReason     string            `json:"selection_reason,omitempty"`
	Reason              string            `json:"reason,omitempty"`
}

type QueryInput struct {
	Intent        string
	Query         string
	ExpandedQuery string
	Paths         []string
	Plan          Plan
}

type QueryPayload struct {
	BaselineHealth        map[string]any   `json:"baseline_health"`
	QueryCoverage         map[string]any   `json:"query_coverage"`
	WorkflowRequirement   string           `json:"workflow_requirement"`
	PathAdoption          map[string]any   `json:"path_adoption"`
	Readiness             string           `json:"readiness"`
	RecommendedNextAction string           `json:"recommended_next_action"`
	Intent                string           `json:"intent"`
	Query                 string           `json:"query"`
	QueryPlan             Plan             `json:"query_plan"`
	SelectedConcepts      []string         `json:"selected_concepts"`
	RejectedConcepts      []string         `json:"rejected_concepts"`
	SelectionReason       string           `json:"selection_reason"`
	CapabilityCandidates  []map[string]any `json:"capability_candidates"`
	SymptomCandidates     []map[string]any `json:"symptom_candidates"`
	AffectedNodes         []map[string]any `json:"affected_nodes"`
	MinimalLiveReads      []string         `json:"minimal_live_reads"`
	MissingCoverage       []string         `json:"missing_coverage"`
	RoutePack             map[string]any   `json:"route_pack"`
	Subgraph              map[string]any   `json:"subgraph"`
}

func ParsePlan(value, file string) (Plan, error) {
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
			return Plan{}, fmt.Errorf("read query plan file: %w", err)
		}
	case value != "":
		data = []byte(value)
	default:
		return Plan{}, nil
	}
	var plan Plan
	if err := json.Unmarshal(data, &plan); err != nil {
		return Plan{}, fmt.Errorf("parse query plan: %w", err)
	}
	return NormalizePlan(plan), nil
}

func NormalizePlan(plan Plan) Plan {
	if len(plan.Paths) == 0 && len(plan.PathHints) > 0 {
		plan.Paths = append([]string{}, plan.PathHints...)
	}
	if plan.SelectionReason == "" && plan.Reason != "" {
		plan.SelectionReason = plan.Reason
	}
	plan.Paths = normalizePaths(plan.Paths)
	plan.PathHints = normalizePaths(plan.PathHints)
	plan.SelectedConcepts = normalizeStrings(plan.SelectedConcepts)
	plan.RejectedConcepts = normalizeStrings(plan.RejectedConcepts)
	plan.ConceptDecisions = normalizeConceptDecisions(plan.ConceptDecisions, plan.SelectedConcepts, plan.RejectedConcepts, plan.SelectionReason)
	return plan
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
	nodes := []map[string]any{}
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
		nodes, err = st.NodesForPaths(context.Background(), plan.Paths)
		if err != nil {
			return QueryPayload{}, err
		}
	}
	reads := plan.Paths
	if len(reads) == 0 {
		reads = []string{".specify/project-cognition/status.json", ".specify/project-cognition/project-cognition.db"}
	}
	routePack := map[string]any{
		"items":              nodes,
		"routes":             plan.Paths,
		"minimal_live_reads": reads,
		"why_these_reads":    "Selected from query plan paths and active project cognition graph metadata.",
	}
	subgraph := map[string]any{
		"nodes":     nodes,
		"edges":     []map[string]any{},
		"claims":    []map[string]any{},
		"conflicts": []map[string]any{},
	}
	return QueryPayload{
		BaselineHealth: map[string]any{
			"freshness": status.Freshness,
			"readiness": status.Readiness,
			"dirty":     status.Dirty,
		},
		QueryCoverage: map[string]any{
			"paths": plan.Paths,
			"nodes": len(nodes),
		},
		WorkflowRequirement:   "use_project_cognition_then_minimal_live_reads",
		PathAdoption:          map[string]any{"paths": plan.Paths},
		Readiness:             status.Readiness,
		RecommendedNextAction: status.RecommendedNextAction,
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
		MissingCoverage:       []string{},
		RoutePack:             routePack,
		Subgraph:              subgraph,
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

func normalizeConceptDecisions(decisions []ConceptDecision, selectedConcepts, rejectedConcepts []string, selectionReason string) []ConceptDecision {
	if len(decisions) == 0 {
		decisions = make([]ConceptDecision, 0, len(selectedConcepts)+len(rejectedConcepts))
		for _, conceptID := range selectedConcepts {
			decisions = append(decisions, ConceptDecision{
				ConceptID:       conceptID,
				Decision:        "selected",
				SelectionReason: selectionReason,
			})
		}
		for _, conceptID := range rejectedConcepts {
			decisions = append(decisions, ConceptDecision{
				ConceptID:       conceptID,
				Decision:        "rejected",
				SelectionReason: selectionReason,
			})
		}
	}

	seen := map[string]bool{}
	out := make([]ConceptDecision, 0, len(decisions))
	for _, decision := range decisions {
		decision.ConceptID = strings.TrimSpace(decision.ConceptID)
		decision.Decision = strings.TrimSpace(decision.Decision)
		decision.SelectionReason = strings.TrimSpace(decision.SelectionReason)
		decision.Confidence = strings.TrimSpace(decision.Confidence)
		decision.Risk = strings.TrimSpace(decision.Risk)
		decision.Paths = normalizePaths(decision.Paths)
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
	return out
}
