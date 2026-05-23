package query

import (
	"strings"

	rt "github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/runtime"
)

type LexiconPayload struct {
	Readiness             string           `json:"readiness"`
	RecommendedNextAction string           `json:"recommended_next_action"`
	Intent                string           `json:"intent"`
	Query                 string           `json:"query"`
	Terms                 []string         `json:"terms"`
	AvailableTerms        []string         `json:"available_terms"`
	ConceptCandidates     []map[string]any `json:"concept_candidates"`
	QueryPlanningContract map[string]any   `json:"query_planning_contract"`
}

func Lexicon(paths rt.Paths, intent, text string, limit int) (LexiconPayload, error) {
	if err := blockSplitBrainBaseline(paths); err != nil {
		return LexiconPayload{}, err
	}
	status, err := rt.ReadStatus(paths)
	if err != nil {
		return LexiconPayload{}, err
	}
	terms := termsFrom(text, limit)
	candidates := make([]map[string]any, 0, len(terms))
	for i, term := range terms {
		candidates = append(candidates, map[string]any{
			"concept_id":          "term:" + term,
			"label":               term,
			"target_type":         "path_or_capability",
			"aliases":             []string{term},
			"matched_terms":       []string{term},
			"query_examples":      []string{text},
			"evidence_ids":        []string{},
			"disambiguation_hint": "Use project paths and capability ledger entries that mention " + term + ".",
			"rank":                i + 1,
		})
	}
	return LexiconPayload{
		Readiness:             status.Readiness,
		RecommendedNextAction: status.RecommendedNextAction,
		Intent:                intent,
		Query:                 text,
		Terms:                 terms,
		AvailableTerms:        terms,
		ConceptCandidates:     candidates,
		QueryPlanningContract: map[string]any{
			"accepted_fields": []string{"raw_query", "expanded_queries", "paths", "path_hints", "selected_concepts", "rejected_concepts", "selection_reason", "reason"},
			"path_hint_alias": "paths",
			"reason_alias":    "selection_reason",
		},
	}, nil
}

func termsFrom(text string, limit int) []string {
	if limit <= 0 {
		limit = 10
	}
	seen := map[string]bool{}
	var terms []string
	for _, field := range strings.FieldsFunc(strings.ToLower(text), func(r rune) bool {
		return !(r >= 'a' && r <= 'z' || r >= '0' && r <= '9' || r == '_' || r == '-')
	}) {
		if field == "" || seen[field] {
			continue
		}
		seen[field] = true
		terms = append(terms, field)
		if len(terms) >= limit {
			break
		}
	}
	return terms
}
