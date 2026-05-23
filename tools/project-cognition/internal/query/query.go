package query

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strings"

	rt "github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/runtime"
	"github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/runtimegate"
	"github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/store"
)

type Plan struct {
	RawQuery         string   `json:"raw_query,omitempty"`
	ExpandedQueries  []string `json:"expanded_queries,omitempty"`
	Paths            []string `json:"paths,omitempty"`
	PathHints        []string `json:"path_hints,omitempty"`
	SelectedConcepts []string `json:"selected_concepts,omitempty"`
	RejectedConcepts []string `json:"rejected_concepts,omitempty"`
	SelectionReason  string   `json:"selection_reason,omitempty"`
	Reason           string   `json:"reason,omitempty"`
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
	st, err := store.Open(paths)
	if err != nil {
		return QueryPayload{}, err
	}
	defer st.Close()
	nodes, err := st.NodesForPaths(context.Background(), plan.Paths)
	if err != nil {
		return QueryPayload{}, err
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
