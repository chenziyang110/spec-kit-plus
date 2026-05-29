package query

import (
	"context"
	"encoding/json"
	"errors"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"unicode"

	rt "github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/runtime"
	"github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/store"
)

type LexiconPayload struct {
	Readiness                string           `json:"readiness"`
	RecommendedNextAction    string           `json:"recommended_next_action"`
	BaselineKind             string           `json:"baseline_kind,omitempty"`
	Intent                   string           `json:"intent"`
	Query                    string           `json:"query"`
	ActiveGenerationID       string           `json:"active_generation_id,omitempty"`
	LexiconGenerationID      string           `json:"lexicon_generation_id,omitempty"`
	CandidateUniverseVersion int              `json:"candidate_universe_version"`
	Terms                    []string         `json:"terms"`
	AvailableTerms           []string         `json:"available_terms"`
	ConceptCandidates        []map[string]any `json:"concept_candidates"`
	QueryPlanningContract    map[string]any   `json:"query_planning_contract"`
	CandidateUniverse        map[string]any   `json:"candidate_universe"`
	MatchingProfile          map[string]any   `json:"matching_profile"`
	UnmappedIntent           bool             `json:"unmapped_intent"`
	MissingCoverage          []string         `json:"missing_coverage"`
}

func Lexicon(paths rt.Paths, intent, text string, limit int) (LexiconPayload, error) {
	if err := blockSplitBrainBaseline(paths); err != nil {
		return LexiconPayload{}, err
	}
	status, err := rt.ReadStatus(paths)
	if err != nil {
		return LexiconPayload{}, err
	}
	if limit <= 0 {
		limit = 10
	}
	terms := termsFrom(text, limit)
	payload := LexiconPayload{
		Readiness:                status.Readiness,
		RecommendedNextAction:    status.RecommendedNextAction,
		BaselineKind:             status.BaselineKind,
		Intent:                   intent,
		Query:                    text,
		ActiveGenerationID:       status.ActiveGenerationID,
		LexiconGenerationID:      status.ActiveGenerationID,
		CandidateUniverseVersion: CandidateUniverseVersion,
		Terms:                    terms,
		AvailableTerms:           terms,
		ConceptCandidates:        []map[string]any{},
		QueryPlanningContract:    queryPlanningContract(),
		CandidateUniverse: map[string]any{
			"counts":           map[string]any{"nodes": 0, "candidates": 0},
			"truncated":        false,
			"selection_window": 0,
		},
		MatchingProfile: map[string]any{
			"terms": terms,
		},
		MissingCoverage: []string{},
	}

	if status.BaselineKind == rt.BaselineKindGreenfieldEmpty {
		payload.UnmappedIntent = true
		payload.MissingCoverage = []string{"greenfield_empty_no_project_code"}
		if len(terms) == 0 {
			payload.MissingCoverage = append(payload.MissingCoverage, "empty_query_terms")
		}
		payload.CandidateUniverse = map[string]any{
			"counts":           map[string]any{"nodes": 0, "candidates": 0},
			"truncated":        false,
			"selection_window": limit,
		}
		return payload, nil
	}

	if len(terms) == 0 {
		payload.UnmappedIntent = true
		payload.MissingCoverage = []string{"empty_query_terms"}
		payload.CandidateUniverse = map[string]any{
			"counts":           map[string]any{"nodes": 0, "candidates": 0},
			"truncated":        false,
			"selection_window": limit,
		}
		return payload, nil
	}

	st, err := store.OpenExisting(paths)
	if errors.Is(err, os.ErrNotExist) {
		payload.UnmappedIntent = true
		payload.MissingCoverage = []string{"project_cognition_database_missing"}
		return payload, nil
	}
	if err != nil {
		return LexiconPayload{}, err
	}
	defer st.Close()

	rows, err := st.AllActiveConceptCandidateRows(context.Background())
	if err != nil {
		return LexiconPayload{}, err
	}
	if len(rows) > 0 && payload.LexiconGenerationID == "" {
		payload.LexiconGenerationID = rows[0].GenerationID
		payload.ActiveGenerationID = rows[0].GenerationID
	}

	candidates, positiveMatches := rankConceptCandidates(rows, terms, limit)
	outputTruncated := limit > 0 && len(rows) > limit
	payload.ConceptCandidates = candidates
	payload.CandidateUniverse = map[string]any{
		"counts": map[string]any{
			"nodes":      len(rows),
			"candidates": len(candidates),
		},
		"truncated":        outputTruncated,
		"selection_window": limit,
	}
	payload.MatchingProfile["positive_matches"] = positiveMatches

	switch {
	case len(rows) == 0:
		payload.UnmappedIntent = true
		payload.MissingCoverage = []string{"empty_graph_candidate_universe"}
	case positiveMatches == 0:
		payload.UnmappedIntent = true
		payload.MissingCoverage = []string{"no_graph_candidate_matched_query"}
	}

	return payload, nil
}

func termsFrom(text string, limit int) []string {
	if limit <= 0 {
		limit = 10
	}
	seen := map[string]bool{}
	var terms []string
	for _, field := range strings.FieldsFunc(strings.ToLower(text), func(r rune) bool {
		return !(unicode.IsLetter(r) || unicode.IsDigit(r) || r == '_' || r == '-')
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

func queryPlanningContract() map[string]any {
	return map[string]any{
		"accepted_fields": []string{
			"raw_query",
			"expanded_queries",
			"paths",
			"path_hints",
			"selected_concepts",
			"rejected_concepts",
			"concept_decisions",
			"lexicon_generation_id",
			"selection_reason",
			"reason",
		},
		"path_hint_alias": "paths",
		"reason_alias":    "selection_reason",
	}
}

type rankedConceptCandidate struct {
	row               store.ConceptCandidateRow
	attrs             map[string]any
	aliases           []string
	paths             []string
	routeHints        []string
	verificationHints []string
	matchedTerms      []string
	colloquialMatches []string
	score             int
}

func rankConceptCandidates(rows []store.ConceptCandidateRow, terms []string, limit int) ([]map[string]any, int) {
	ranked := make([]rankedConceptCandidate, 0, len(rows))
	positiveMatches := 0
	for _, row := range rows {
		candidate := newRankedConceptCandidate(row)
		candidate.score, candidate.matchedTerms, candidate.colloquialMatches = scoreConceptCandidate(candidate, terms)
		if candidate.score > 0 {
			positiveMatches++
		}
		ranked = append(ranked, candidate)
	}
	sort.SliceStable(ranked, func(i, j int) bool {
		if ranked[i].score != ranked[j].score {
			return ranked[i].score > ranked[j].score
		}
		if ranked[i].row.Title != ranked[j].row.Title {
			return ranked[i].row.Title < ranked[j].row.Title
		}
		return ranked[i].row.NodeID < ranked[j].row.NodeID
	})
	if limit > 0 && len(ranked) > limit {
		ranked = ranked[:limit]
	}

	candidates := make([]map[string]any, 0, len(ranked))
	for i, candidate := range ranked {
		candidates = append(candidates, candidate.toMap(i+1))
	}
	return candidates, positiveMatches
}

func newRankedConceptCandidate(row store.ConceptCandidateRow) rankedConceptCandidate {
	attrs := parseAttrs(row.AttrsJSON)
	paths := uniqueStrings(append(append([]string{}, row.Paths...), row.EvidencePaths...))
	aliases := []string{row.Title, row.NodeID, row.NodeType}
	aliases = append(aliases, attrStrings(attrs, "aliases")...)
	aliases = append(aliases, attrString(attrs, "domain"), attrString(attrs, "owner"), attrString(attrs, "workflow"), attrString(attrs, "route"))
	aliases = append(aliases, attrStrings(attrs, "route_hints")...)
	aliases = append(aliases, attrStrings(attrs, "verification_hints")...)
	aliases = append(aliases, paths...)
	for _, path := range paths {
		aliases = append(aliases, pathMaterial(path)...)
	}
	aliases = append(aliases, row.ObservationSummaries...)
	return rankedConceptCandidate{
		row:               row,
		attrs:             attrs,
		aliases:           uniqueStrings(aliases),
		paths:             paths,
		routeHints:        uniqueStrings(append(attrStrings(attrs, "route_hints"), attrString(attrs, "route"))),
		verificationHints: uniqueStrings(attrStrings(attrs, "verification_hints")),
	}
}

func (candidate rankedConceptCandidate) toMap(rank int) map[string]any {
	conceptID := "concept:" + candidate.row.GenerationID + ":" + candidate.row.NodeID
	return map[string]any{
		"concept_id":          conceptID,
		"node_id":             candidate.row.NodeID,
		"label":               candidate.row.Title,
		"title":               candidate.row.Title,
		"target_type":         "graph_node",
		"node_type":           candidate.row.NodeType,
		"aliases":             candidate.aliases,
		"matched_terms":       candidate.matchedTerms,
		"colloquial_matches":  candidate.colloquialMatches,
		"paths":               candidate.paths,
		"evidence_ids":        candidate.row.EvidenceIDs,
		"confidence":          candidate.row.Confidence,
		"score":               candidate.score,
		"rank":                rank,
		"domain":              attrString(candidate.attrs, "domain"),
		"owner":               attrString(candidate.attrs, "owner"),
		"route_hints":         candidate.routeHints,
		"verification_hints":  candidate.verificationHints,
		"disambiguation_hint": "Select when the query is about " + candidate.row.Title + " or its owned paths.",
		"selection_guidance":  "Use this concept when graph aliases, paths, or evidence match the user's intent; reject it when the overlap is incidental.",
	}
}

func scoreConceptCandidate(candidate rankedConceptCandidate, terms []string) (int, []string, []string) {
	aliasTerms := map[string]bool{}
	loweredAliases := make([]string, 0, len(candidate.aliases))
	for _, alias := range candidate.aliases {
		lowered := strings.ToLower(alias)
		loweredAliases = append(loweredAliases, lowered)
		for _, term := range termsFrom(alias, 100) {
			aliasTerms[term] = true
		}
	}

	score := 0
	matched := []string{}
	colloquial := []string{}
	seenMatched := map[string]bool{}
	seenColloquial := map[string]bool{}
	for _, term := range terms {
		termScore := 0
		if aliasTerms[term] {
			termScore = maxInt(termScore, 10)
		}
		for aliasTerm := range aliasTerms {
			if len(term) >= 3 && strings.HasPrefix(aliasTerm, term) {
				termScore = maxInt(termScore, 6)
			}
		}
		for _, alias := range loweredAliases {
			if len(term) >= 3 && strings.Contains(alias, term) {
				termScore = maxInt(termScore, 3)
				if !seenColloquial[term] {
					colloquial = append(colloquial, term)
					seenColloquial[term] = true
				}
			}
		}
		if termScore > 0 {
			score += termScore
			if !seenMatched[term] {
				matched = append(matched, term)
				seenMatched[term] = true
			}
		}
	}
	return score, matched, colloquial
}

func parseAttrs(raw string) map[string]any {
	if raw == "" {
		return map[string]any{}
	}
	var attrs map[string]any
	if err := json.Unmarshal([]byte(raw), &attrs); err != nil {
		return map[string]any{}
	}
	return attrs
}

func attrString(attrs map[string]any, key string) string {
	value, ok := attrs[key]
	if !ok {
		return ""
	}
	switch typed := value.(type) {
	case string:
		return strings.TrimSpace(typed)
	default:
		return strings.TrimSpace(strings.TrimPrefix(strings.TrimSuffix(strings.TrimSpace(toString(typed)), `"`), `"`))
	}
}

func attrStrings(attrs map[string]any, key string) []string {
	value, ok := attrs[key]
	if !ok {
		return []string{}
	}
	switch typed := value.(type) {
	case []any:
		out := make([]string, 0, len(typed))
		for _, item := range typed {
			out = append(out, toString(item))
		}
		return uniqueStrings(out)
	case []string:
		return uniqueStrings(typed)
	case string:
		return []string{typed}
	default:
		return []string{toString(typed)}
	}
}

func toString(value any) string {
	switch typed := value.(type) {
	case string:
		return strings.TrimSpace(typed)
	default:
		bytes, err := json.Marshal(typed)
		if err != nil {
			return ""
		}
		return strings.TrimSpace(string(bytes))
	}
}

func pathMaterial(path string) []string {
	path = filepath.ToSlash(strings.TrimSpace(path))
	if path == "" {
		return []string{}
	}
	parts := strings.FieldsFunc(path, func(r rune) bool {
		return r == '/' || r == '\\' || r == '.' || r == '_' || r == '-'
	})
	base := filepath.Base(path)
	ext := filepath.Ext(base)
	if ext != "" {
		base = strings.TrimSuffix(base, ext)
	}
	parts = append(parts, base)
	return uniqueStrings(parts)
}

func uniqueStrings(values []string) []string {
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

func maxInt(a, b int) int {
	if a > b {
		return a
	}
	return b
}
