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

type conceptRef struct {
	GenerationID   string
	NodeID         string
	FallbackNodeID string
}

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
	BaselineKind          string           `json:"baseline_kind,omitempty"`
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
		}, nil
	}
	nodes := []map[string]any{}
	missingCoverage := []string{}
	selectedConceptsMissingNodes := false
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
		if len(plan.SelectedConcepts) > 0 {
			var nodeIDs []string
			var selectedRefs []selectedConceptRef
			selectedRefs, missingCoverage = selectedConceptRefs(plan.SelectedConcepts, activeGenerationID)
			if len(missingCoverage) > 0 {
				selectedConceptsMissingNodes = true
			}
			nodeCandidates := selectedNodeIDCandidates(selectedRefs)
			nodes, err = st.NodesForIDs(context.Background(), nodeCandidates)
			if err != nil {
				return QueryPayload{}, err
			}
			resolvedNodeIDs := nodeIDsFromNodes(nodes)
			nodeIDs, missingConcepts := resolveSelectedNodeIDs(selectedRefs, resolvedNodeIDs)
			for _, conceptID := range missingConcepts {
				selectedConceptsMissingNodes = true
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
	if selectedConceptsMissingNodes && status.Readiness == rt.ReadyReadiness {
		readiness = "review"
		recommendedNextAction = "use_minimal_live_reads_and_review_missing_coverage"
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

func appendMissingCoverage(values []string, value string) []string {
	for _, existing := range values {
		if existing == value {
			return values
		}
	}
	return append(values, value)
}

func generationMismatchPayload(status rt.Status, input QueryInput, plan Plan, activeGenerationID string) QueryPayload {
	reads := []string{".specify/project-cognition/status.json", ".specify/project-cognition/project-cognition.db"}
	return QueryPayload{
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
		Readiness:             "ambiguous",
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
