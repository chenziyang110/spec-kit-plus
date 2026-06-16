package query

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"errors"
	"os"
	"sort"
	"strconv"
	"strings"

	rt "github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/runtime"
	"github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/store"
)

const (
	compassMode                             = "compass"
	compassFacetSourceMechanical            = "mechanical_query_facets"
	compassFacetSourceSemanticIntake        = "semantic_intake"
	compassFacetSourceQueryPlan             = "query_plan"
	compassStateUsable                      = "usable"
	compassStateUsableWithReview            = "usable_with_review"
	compassStateNeedsSemanticIntake         = "needs_semantic_intake"
	compassStateNeedsExpansionBeforeFix     = "needs_expansion_before_fix_claim"
	compassStateBlocked                     = "blocked"
	maxCompassLanes                         = 5
	maxCompassReads                         = 15
	maxCompassPathsPerLane                  = 5
	broadFallbackPathThreshold              = 200
	compassRecommendedActionUseReads        = "use_compass_minimal_live_reads"
	compassRecommendedActionExpandBeforeFix = "run_compass_expansion_before_fix"
)

type CompassInput struct {
	Intent         string
	Query          string
	Mode           string
	Plan           Plan
	SemanticIntake SemanticIntake
}

type CompassPayload struct {
	Readiness                string                        `json:"readiness"`
	CompassState             string                        `json:"compass_state"`
	Mode                     string                        `json:"mode"`
	FacetSource              string                        `json:"facet_source"`
	ActiveGenerationID       string                        `json:"active_generation_id,omitempty"`
	CandidateUniverseVersion int                           `json:"candidate_universe_version"`
	QueryFingerprint         string                        `json:"query_fingerprint"`
	Summary                  string                        `json:"summary,omitempty"`
	IntentFacets             []CompassIntentFacet          `json:"intent_facets"`
	EvidenceLanes            []EvidenceLane                `json:"evidence_lanes"`
	MinimalLiveReads         []string                      `json:"minimal_live_reads"`
	CoverageDiagnostics      []CoverageDiagnostic          `json:"coverage_diagnostics"`
	ExpansionRef             ExpansionRef                  `json:"expansion_ref,omitempty"`
	AgentNormalization       *AgentNormalizationDiagnostic `json:"agent_normalization,omitempty"`
	Warnings                 []string                      `json:"warnings,omitempty"`
	RepairHints              []string                      `json:"repair_hints,omitempty"`
	RecommendedNextAction    string                        `json:"recommended_next_action"`
	BaselineKind             string                        `json:"baseline_kind,omitempty"`
}

type CompassIntentFacet struct {
	Facet        string   `json:"facet"`
	Covered      bool     `json:"covered"`
	CoveredBy    []string `json:"covered_by,omitempty"`
	NeedsReview  bool     `json:"needs_review,omitempty"`
	MatchedTerms []string `json:"matched_terms,omitempty"`
}

type EvidenceLane struct {
	ConceptID         string          `json:"concept_id"`
	NodeID            string          `json:"node_id"`
	Title             string          `json:"title"`
	NodeType          string          `json:"node_type,omitempty"`
	Confidence        string          `json:"confidence,omitempty"`
	Score             int             `json:"score,omitempty"`
	MatchedTerms      []string        `json:"matched_terms,omitempty"`
	BaselineKind      string          `json:"baseline_kind,omitempty"`
	FirstPassPaths    []FirstPassPath `json:"first_pass_paths"`
	VerificationHints []string        `json:"verification_hints,omitempty"`
	FollowupSurfaces  []string        `json:"followup_surfaces,omitempty"`
	BeforeFixClaim    []string        `json:"before_fix_claim,omitempty"`
}

type FirstPassPath struct {
	Path       string `json:"path"`
	Reason     string `json:"reason,omitempty"`
	Confidence string `json:"confidence,omitempty"`
}

type CoverageDiagnostic struct {
	Kind      string   `json:"kind"`
	ConceptID string   `json:"concept_id,omitempty"`
	Title     string   `json:"title,omitempty"`
	Reason    string   `json:"reason,omitempty"`
	Facets    []string `json:"facets,omitempty"`
}

type ExpansionRef struct {
	ID                string                 `json:"id,omitempty"`
	AvailableSections []ExpansionSectionMeta `json:"available_sections,omitempty"`
}

type ExpansionSectionMeta struct {
	ID      string `json:"id,omitempty"`
	Title   string `json:"title,omitempty"`
	Summary string `json:"summary,omitempty"`
}

type compassCandidate struct {
	ranked     rankedConceptCandidate
	conceptID  string
	suppressed bool
	reason     string
}

func Compass(paths rt.Paths, input CompassInput) (CompassPayload, error) {
	if err := blockSplitBrainBaseline(paths); err != nil {
		return CompassPayload{}, err
	}
	status, err := rt.ReadStatus(paths)
	if err != nil {
		return CompassPayload{}, err
	}

	terms := termsFrom(strings.Join([]string{input.Intent, input.Query}, " "), 30)
	facets, facetSource := compassFacets(input, terms)
	payload := CompassPayload{
		Readiness:                status.Readiness,
		CompassState:             compassStateBlocked,
		Mode:                     compassMode,
		FacetSource:              facetSource,
		ActiveGenerationID:       status.ActiveGenerationID,
		CandidateUniverseVersion: CandidateUniverseVersion,
		QueryFingerprint:         compassFingerprint(input),
		IntentFacets:             []CompassIntentFacet{},
		EvidenceLanes:            []EvidenceLane{},
		MinimalLiveReads:         []string{},
		CoverageDiagnostics:      []CoverageDiagnostic{},
		RecommendedNextAction:    status.RecommendedNextAction,
		BaselineKind:             status.BaselineKind,
	}

	if compassReadinessBlocked(status.Readiness) {
		payload.IntentFacets = coverageForFacets(facets, nil, payload.CoverageDiagnostics, true)
		return payload, nil
	}

	st, err := store.OpenExisting(paths)
	if errors.Is(err, os.ErrNotExist) {
		st = nil
		err = nil
	}
	if err != nil {
		return CompassPayload{}, err
	}
	if st != nil {
		defer st.Close()
		rows, err := st.AllActiveConceptCandidateRows(context.Background())
		if err != nil {
			return CompassPayload{}, err
		}
		if len(rows) > 0 && payload.ActiveGenerationID == "" {
			payload.ActiveGenerationID = rows[0].GenerationID
		}
		candidates := compassCandidates(rows, compassCandidateTerms(input, terms, facets))
		for _, candidate := range candidates {
			if candidate.suppressed {
				payload.CoverageDiagnostics = append(payload.CoverageDiagnostics, CoverageDiagnostic{
					Kind:      "broad_fallback_suppressed",
					ConceptID: candidate.conceptID,
					Title:     candidate.ranked.row.Title,
					Reason:    candidate.reason,
				})
			}
		}
		payload.EvidenceLanes = evidenceLanesFromCandidates(candidates, facets)
		payload.MinimalLiveReads = minimalReadsFromLanes(payload.EvidenceLanes)
	}
	payload.IntentFacets = coverageForFacets(facets, payload.EvidenceLanes, payload.CoverageDiagnostics, true)
	payload.AgentNormalization = compassAgentNormalization(status, payload.EvidenceLanes, payload.CoverageDiagnostics, input.Query)
	payload.CompassState = compassState(status, input, payload)
	payload.RecommendedNextAction = compassRecommendedNextAction(status, payload.CompassState)
	payload.Summary = compassSummary(payload)
	return payload, nil
}

func compassFingerprint(input CompassInput) string {
	normalized := strings.Join(normalizeStrings([]string{
		strings.ToLower(strings.TrimSpace(input.Intent)),
		strings.ToLower(strings.TrimSpace(input.Mode)),
		strings.ToLower(strings.TrimSpace(input.Query)),
		strings.ToLower(strings.TrimSpace(input.Plan.NormalizedQuery)),
		strings.Join(input.Plan.IntentFacets, "\x00"),
		strings.ToLower(strings.TrimSpace(input.SemanticIntake.NormalizedQuery)),
		strings.Join(input.SemanticIntake.IntentFacets, "\x00"),
	}), "\x00")
	sum := sha256.Sum256([]byte(normalized))
	return hex.EncodeToString(sum[:12])
}

func compassFacets(input CompassInput, terms []string) ([]string, string) {
	mode := strings.TrimSpace(input.Mode)
	plan := NormalizePlan(input.Plan)
	switch {
	case strings.EqualFold(mode, compassFacetSourceQueryPlan) && len(plan.IntentFacets) > 0:
		return normalizeStrings(plan.IntentFacets), compassFacetSourceQueryPlan
	case strings.EqualFold(mode, compassFacetSourceSemanticIntake) && hasSemanticIntake(input.SemanticIntake):
		return normalizeStrings(input.SemanticIntake.IntentFacets), compassFacetSourceSemanticIntake
	case len(plan.IntentFacets) > 0:
		return normalizeStrings(plan.IntentFacets), compassFacetSourceQueryPlan
	case hasSemanticIntake(plan.SemanticIntake):
		return normalizeStrings(plan.SemanticIntake.IntentFacets), compassFacetSourceSemanticIntake
	case hasSemanticIntake(input.SemanticIntake):
		return normalizeStrings(input.SemanticIntake.IntentFacets), compassFacetSourceSemanticIntake
	default:
		return normalizeStrings(compassMechanicalFacets(input.Query, terms)), compassFacetSourceMechanical
	}
}

func compassCandidates(rows []store.ConceptCandidateRow, terms []string) []compassCandidate {
	candidates := make([]compassCandidate, 0, len(rows))
	for _, row := range rows {
		ranked := newRankedConceptCandidate(row)
		ranked.score, ranked.matchedTerms, ranked.colloquialMatches = scoreConceptCandidate(ranked, terms)
		suppressed, reason := isBroadFallbackCandidate(ranked)
		if ranked.score <= 0 {
			continue
		}
		candidates = append(candidates, compassCandidate{
			ranked:     ranked,
			conceptID:  "concept:" + row.GenerationID + ":" + row.NodeID,
			suppressed: suppressed,
			reason:     reason,
		})
	}
	sort.SliceStable(candidates, func(i, j int) bool {
		if candidates[i].suppressed != candidates[j].suppressed {
			return !candidates[i].suppressed
		}
		if candidates[i].ranked.score != candidates[j].ranked.score {
			return candidates[i].ranked.score > candidates[j].ranked.score
		}
		if candidates[i].ranked.row.Title != candidates[j].ranked.row.Title {
			return candidates[i].ranked.row.Title < candidates[j].ranked.row.Title
		}
		return candidates[i].ranked.row.NodeID < candidates[j].ranked.row.NodeID
	})
	return candidates
}

func isBroadFallbackCandidate(candidate rankedConceptCandidate) (bool, string) {
	if strings.EqualFold(candidate.row.NodeType, "coverage_fallback") {
		return true, "node_type_coverage_fallback"
	}
	if provenance := attrString(candidate.attrs, "fallback_provenance"); provenance != "" {
		return true, "fallback_provenance:" + provenance
	}
	if count := attrInt(candidate.attrs, "path_count"); count >= broadFallbackPathThreshold {
		return true, "path_count_exceeds_threshold"
	}
	return false, ""
}

func evidenceLanesFromCandidates(candidates []compassCandidate, facets []string) []EvidenceLane {
	lanes := make([]EvidenceLane, 0, maxCompassLanes)
	for _, candidate := range candidates {
		if candidate.suppressed || candidate.ranked.score <= 0 {
			continue
		}
		paths := firstPassPaths(candidate.ranked)
		if len(paths) == 0 {
			continue
		}
		lanes = append(lanes, EvidenceLane{
			ConceptID:         candidate.conceptID,
			NodeID:            candidate.ranked.row.NodeID,
			Title:             candidate.ranked.row.Title,
			NodeType:          candidate.ranked.row.NodeType,
			Confidence:        candidate.ranked.row.Confidence,
			Score:             candidate.ranked.score,
			MatchedTerms:      candidate.ranked.matchedTerms,
			FirstPassPaths:    paths,
			VerificationHints: candidate.ranked.verificationHints,
			FollowupSurfaces:  attrStrings(candidate.ranked.attrs, "followup_surfaces"),
			BeforeFixClaim:    attrStrings(candidate.ranked.attrs, "before_fix_claim"),
		})
		if len(lanes) >= maxCompassLanes {
			break
		}
	}
	return lanes
}

func minimalReadsFromLanes(lanes []EvidenceLane) []string {
	reads := []string{}
	for _, lane := range lanes {
		for _, path := range lane.FirstPassPaths {
			reads = appendMissingCoverage(reads, path.Path)
			if len(reads) >= maxCompassReads {
				return reads
			}
		}
	}
	return reads
}

func coverageForFacets(facets []string, lanes []EvidenceLane, diagnostics []CoverageDiagnostic, precision bool) []CompassIntentFacet {
	out := make([]CompassIntentFacet, 0, len(facets))
	for _, facet := range facets {
		coveredBy := []string{}
		matchedTerms := []string{}
		for _, lane := range lanes {
			if compassLaneCoversFacet(lane, facet) {
				coveredBy = appendMissingCoverage(coveredBy, lane.ConceptID)
				matchedTerms = appendUniqueStrings(matchedTerms, lane.MatchedTerms...)
			}
		}
		out = append(out, CompassIntentFacet{
			Facet:        facet,
			Covered:      len(coveredBy) > 0,
			CoveredBy:    coveredBy,
			NeedsReview:  precision && len(coveredBy) == 0,
			MatchedTerms: matchedTerms,
		})
	}
	return out
}

func compassCandidateTerms(input CompassInput, terms, facets []string) []string {
	values := append([]string{}, terms...)
	values = append(values, facets...)
	values = append(values, termsFrom(input.Plan.NormalizedQuery, 20)...)
	values = append(values, input.Plan.IntentFacets...)
	values = append(values, input.Plan.RepositorySearchTerms...)
	values = append(values, termsFrom(input.SemanticIntake.NormalizedQuery, 20)...)
	values = append(values, input.SemanticIntake.IntentFacets...)
	return uniqueStrings(values)
}

func compassMechanicalFacets(query string, terms []string) []string {
	facets := append([]string{}, terms...)
	lowered := strings.ToLower(query)
	if strings.Contains(lowered, "方块") {
		facets = append(facets, "square glyphs", "font fallback")
	}
	if strings.Contains(lowered, "屏幕小") || strings.Contains(lowered, "窗口小") {
		facets = append(facets, "small viewport", "window minimum size")
	}
	if strings.Contains(lowered, "切模型") {
		facets = append(facets, "provider model switch")
	}
	return uniqueStrings(facets)
}

func firstPassPaths(candidate rankedConceptCandidate) []FirstPassPath {
	paths := normalizePaths(candidate.paths)
	if len(paths) > maxCompassPathsPerLane {
		paths = paths[:maxCompassPathsPerLane]
	}
	out := make([]FirstPassPath, 0, len(paths))
	for _, path := range paths {
		out = append(out, FirstPassPath{
			Path:       path,
			Reason:     "owned_by_ranked_project_cognition_node",
			Confidence: candidate.row.Confidence,
		})
	}
	return out
}

func compassLaneCoversFacet(lane EvidenceLane, facet string) bool {
	material := strings.ToLower(strings.Join(append([]string{lane.Title, lane.NodeType}, lane.MatchedTerms...), " "))
	if semanticMaterialMatches(material, facet) {
		return true
	}
	for _, path := range lane.FirstPassPaths {
		if semanticMaterialMatches(strings.ToLower(path.Path), facet) {
			return true
		}
	}
	return false
}

func compassReadinessBlocked(readiness string) bool {
	return readiness == rt.NeedsRebuildReadiness || readiness == rt.BlockedReadiness || readiness == rt.UnsupportedReadiness
}

func compassState(status rt.Status, input CompassInput, payload CompassPayload) string {
	if compassReadinessBlocked(status.Readiness) {
		return compassStateBlocked
	}
	if payload.AgentNormalization != nil && payload.AgentNormalization.Required {
		return compassStateNeedsSemanticIntake
	}
	hasUncovered := compassHasUncoveredFacet(payload.IntentFacets)
	if len(payload.EvidenceLanes) == 0 && hasUncovered {
		return compassStateNeedsExpansionBeforeFix
	}
	mode := strings.TrimSpace(input.Mode)
	if status.Readiness == rt.ReadyReadiness && (strings.EqualFold(mode, compassFacetSourceQueryPlan) || strings.EqualFold(mode, compassFacetSourceSemanticIntake)) && !hasUncovered {
		return compassStateUsable
	}
	if status.Readiness == rt.ReadyReadiness && len(payload.EvidenceLanes) > 0 {
		return compassStateUsableWithReview
	}
	return compassStateNeedsExpansionBeforeFix
}

func compassHasUncoveredFacet(facets []CompassIntentFacet) bool {
	for _, facet := range facets {
		if !facet.Covered {
			return true
		}
	}
	return len(facets) == 0
}

func compassRecommendedNextAction(status rt.Status, state string) string {
	switch state {
	case compassStateUsable, compassStateUsableWithReview:
		return compassRecommendedActionUseReads
	case compassStateNeedsExpansionBeforeFix:
		return compassRecommendedActionExpandBeforeFix
	case compassStateNeedsSemanticIntake:
		return "write_semantic_intake_from_alias_catalog"
	default:
		return status.RecommendedNextAction
	}
}

func compassAgentNormalization(status rt.Status, lanes []EvidenceLane, diagnostics []CoverageDiagnostic, query string) *AgentNormalizationDiagnostic {
	if len(lanes) > 0 || !agentNormalizationCatalogUsable(status) {
		return nil
	}
	triggers := []string{}
	if queryHasCJKOrMixedCJKASCII(query) {
		triggers = append(triggers, "cjk_or_mixed_language_query")
	}
	for _, diagnostic := range diagnostics {
		if diagnostic.Kind == "broad_fallback_suppressed" {
			triggers = appendMissingCoverage(triggers, "only_broad_fallback_matched")
		}
	}
	if len(triggers) == 0 {
		return nil
	}
	return &AgentNormalizationDiagnostic{
		Required: true,
		Reason:   "raw_terms_need_project_vocabulary_normalization",
		Triggers: triggers,
		Action:   "write_semantic_intake_from_alias_catalog",
		Reminder: "Translate user language into project vocabulary before fixing when compact evidence lanes are absent.",
	}
}

func compassSummary(payload CompassPayload) string {
	if len(payload.EvidenceLanes) == 0 {
		return "No compact evidence lane matched the query."
	}
	return "Compact compass packet selected minimal live reads from ranked project cognition evidence lanes."
}

func attrInt(attrs map[string]any, key string) int {
	value, ok := attrs[key]
	if !ok {
		return 0
	}
	switch typed := value.(type) {
	case int:
		return typed
	case int64:
		return int(typed)
	case float64:
		return int(typed)
	case string:
		out, _ := strconv.Atoi(strings.TrimSpace(typed))
		return out
	default:
		return 0
	}
}
