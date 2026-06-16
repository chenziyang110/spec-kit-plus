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
	compassFacetSourceSemanticIntake        = "semantic_intake.intent_facets"
	compassFacetSourceQueryPlan             = "query_plan.intent_facets"
	compassInputModeQuery                   = "query"
	compassInputModeSemanticIntake          = "semantic_intake"
	compassInputModeQueryPlan               = "query_plan"
	compassStateUsable                      = "usable"
	compassStateUsableWithReview            = "usable_with_review"
	compassStateNeedsSemanticIntake         = "needs_semantic_intake"
	compassStateNeedsExpansionBeforeFix     = "needs_expansion_before_fix_claim"
	compassStateBlocked                     = "blocked"
	maxCompassLanes                         = 3
	maxCompassReads                         = 15
	maxCompassPathsPerLane                  = 6
	broadFallbackPathThreshold              = 50
	compassRecommendedActionUseReads        = "use_compass_minimal_live_reads"
	compassRecommendedActionExpandBeforeFix = "run_compass_expansion_before_fix"
)

type CompassInput struct {
	Intent          string
	Query           string
	Plan            Plan
	PlanDiagnostics PlanDiagnostics
	InputMode       string
}

type CompassPayload struct {
	Readiness                string                        `json:"readiness"`
	CompassState             string                        `json:"compass_state"`
	Mode                     string                        `json:"mode"`
	FacetSource              string                        `json:"facet_source"`
	ActiveGenerationID       string                        `json:"active_generation_id,omitempty"`
	CandidateUniverseVersion int                           `json:"candidate_universe_version"`
	QueryFingerprint         string                        `json:"query_fingerprint"`
	Summary                  string                        `json:"summary"`
	IntentFacets             []CompassIntentFacet          `json:"intent_facets"`
	EvidenceLanes            []EvidenceLane                `json:"evidence_lanes"`
	MinimalLiveReads         []string                      `json:"minimal_live_reads"`
	CoverageDiagnostics      []CoverageDiagnostic          `json:"coverage_diagnostics"`
	ExpansionRef             *ExpansionRef                 `json:"expansion_ref,omitempty"`
	AgentNormalization       *AgentNormalizationDiagnostic `json:"agent_normalization,omitempty"`
	Warnings                 []string                      `json:"warnings,omitempty"`
	RepairHints              []string                      `json:"repair_hints,omitempty"`
	RecommendedNextAction    string                        `json:"recommended_next_action"`
	BaselineKind             string                        `json:"baseline_kind,omitempty"`
}

type CompassIntentFacet struct {
	Name     string `json:"name"`
	Coverage string `json:"coverage"`
	Risk     string `json:"risk,omitempty"`
}

type EvidenceLane struct {
	ID                string          `json:"id"`
	Title             string          `json:"title"`
	Coverage          string          `json:"coverage"`
	Confidence        string          `json:"confidence"`
	FirstPassPaths    []FirstPassPath `json:"first_pass_paths"`
	VerificationHints []string        `json:"verification_hints"`
	FollowupSurfaces  []string        `json:"followup_surfaces"`
	BeforeFixClaim    []string        `json:"before_fix_claim"`
	matchedTerms      []string
	nodeType          string
}

type FirstPassPath struct {
	Path         string `json:"path"`
	Reason       string `json:"reason"`
	EvidenceHint string `json:"evidence_hint,omitempty"`
}

type CoverageDiagnostic struct {
	Kind              string   `json:"kind"`
	Severity          string   `json:"severity"`
	Message           string   `json:"message"`
	AffectedFacets    []string `json:"affected_facets,omitempty"`
	RecommendedAction string   `json:"recommended_action"`
}

type ExpansionRef struct {
	ID                       string                          `json:"id,omitempty"`
	ActiveGenerationID       string                          `json:"active_generation_id,omitempty"`
	CandidateUniverseVersion int                             `json:"candidate_universe_version,omitempty"`
	QueryFingerprint         string                          `json:"query_fingerprint,omitempty"`
	AvailableSections        map[string]ExpansionSectionMeta `json:"available_sections,omitempty"`
	StaleBehavior            string                          `json:"stale_behavior,omitempty"`
}

type ExpansionSectionMeta struct {
	State          string `json:"state"`
	EstimatedItems int    `json:"estimated_items"`
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
		Summary:                  "Compass packet is blocked until project cognition readiness is restored.",
		IntentFacets:             []CompassIntentFacet{},
		EvidenceLanes:            []EvidenceLane{},
		MinimalLiveReads:         []string{},
		CoverageDiagnostics:      []CoverageDiagnostic{},
		Warnings:                 input.PlanDiagnostics.Warnings,
		RepairHints:              input.PlanDiagnostics.RepairHints,
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
	candidates := []compassCandidate{}
	candidatesComputed := false
	if st != nil {
		defer st.Close()
		rows, err := st.AllActiveConceptCandidateRows(context.Background())
		if err != nil {
			return CompassPayload{}, err
		}
		if len(rows) > 0 && payload.ActiveGenerationID == "" {
			payload.ActiveGenerationID = rows[0].GenerationID
		}
		candidates = compassCandidates(rows, compassCandidateTerms(input, terms, facets), compassUsesPrecisionInput(input))
		candidatesComputed = true
		selectedPaths := compassSelectedPrecisionPaths(input)
		for _, candidate := range candidates {
			if candidate.suppressed {
				payload.CoverageDiagnostics = append(payload.CoverageDiagnostics, CoverageDiagnostic{
					Kind:              "broad_fallback_suppressed",
					Severity:          "info",
					Message:           "Suppressed broad fallback candidate " + candidate.ranked.row.Title + ": " + candidate.reason,
					AffectedFacets:    facets,
					RecommendedAction: "use_specific_evidence_lanes_before_broad_fallbacks",
				})
			}
		}
		payload.EvidenceLanes = evidenceLanesFromCandidates(candidates, facets, selectedPaths)
		payload.MinimalLiveReads = minimalReadsFromLanes(payload.EvidenceLanes)
	}
	payload.IntentFacets = coverageForFacets(facets, payload.EvidenceLanes, payload.CoverageDiagnostics, true)
	payload.AgentNormalization = compassAgentNormalization(status, payload.EvidenceLanes, payload.CoverageDiagnostics, input.Query)
	payload.CompassState = compassState(status, input, payload)
	payload.RecommendedNextAction = compassRecommendedNextAction(status, payload.CompassState)
	payload.Summary = compassSummary(payload)
	if candidatesComputed {
		ref, err := writeExpansionBundle(paths, ExpansionBundle{
			ID:                       "exp-" + payload.QueryFingerprint,
			ActiveGenerationID:       payload.ActiveGenerationID,
			CandidateUniverseVersion: payload.CandidateUniverseVersion,
			QueryFingerprint:         payload.QueryFingerprint,
			Sections:                 []string{"related_paths", "raw_candidates", "coverage_gaps", "graph_neighbors"},
			SectionPayloads: map[string]any{
				"related_paths":   payload.MinimalLiveReads,
				"raw_candidates":  candidatesForExpansion(candidates),
				"coverage_gaps":   payload.CoverageDiagnostics,
				"graph_neighbors": []map[string]any{},
			},
		})
		if err != nil {
			payload.Warnings = appendDiagnosticString(payload.Warnings, "expansion_bundle_write_failed:"+err.Error())
		} else {
			payload.ExpansionRef = &ref
		}
	}
	return payload, nil
}

func compassFingerprint(input CompassInput) string {
	mode := normalizedCompassInputMode(input.InputMode)
	components := []string{
		strings.ToLower(strings.TrimSpace(input.Intent)),
		mode,
		strings.ToLower(strings.TrimSpace(input.Query)),
	}
	if mode == compassInputModeQueryPlan || mode == compassInputModeSemanticIntake {
		plan := NormalizePlan(input.Plan)
		components = append(components,
			strings.ToLower(strings.TrimSpace(plan.NormalizedQuery)),
			strings.Join(plan.IntentFacets, "\x00"),
			strings.Join(plan.RepositorySearchTerms, "\x00"),
			strings.Join(plan.Paths, "\x00"),
			strings.Join(plan.PathHints, "\x00"),
			strings.Join(plan.SelectedConcepts, "\x00"),
			strings.ToLower(strings.TrimSpace(plan.SemanticIntake.NormalizedQuery)),
			strings.Join(plan.SemanticIntake.IntentFacets, "\x00"),
		)
		for _, decision := range compassSelectedConceptDecisions(plan) {
			components = append(components,
				decision.ConceptID,
				strings.ToLower(strings.TrimSpace(decision.Decision)),
				strings.Join(decision.CoveredFacets, "\x00"),
				strings.Join(decision.MatchSources, "\x00"),
				strings.Join(decision.Paths, "\x00"),
			)
		}
	}
	normalized := strings.Join(normalizeStrings(components), "\x00")
	sum := sha256.Sum256([]byte(normalized))
	return hex.EncodeToString(sum[:12])
}

func compassFacets(input CompassInput, terms []string) ([]string, string) {
	mode := normalizedCompassInputMode(input.InputMode)
	plan := NormalizePlan(input.Plan)
	switch {
	case mode == compassInputModeQueryPlan && len(plan.SemanticIntake.IntentFacets) > 0:
		return normalizeStrings(plan.SemanticIntake.IntentFacets), compassFacetSourceQueryPlan
	case mode == compassInputModeQueryPlan && len(plan.IntentFacets) > 0:
		return normalizeStrings(plan.IntentFacets), compassFacetSourceQueryPlan
	case mode == compassInputModeSemanticIntake && hasSemanticIntake(plan.SemanticIntake):
		return normalizeStrings(plan.SemanticIntake.IntentFacets), compassFacetSourceSemanticIntake
	default:
		return normalizeStrings(compassMechanicalFacets(input.Query, terms)), compassFacetSourceMechanical
	}
}

func compassCandidates(rows []store.ConceptCandidateRow, terms []string, precision bool) []compassCandidate {
	candidates := make([]compassCandidate, 0, len(rows))
	for _, row := range rows {
		ranked := newRankedConceptCandidate(row)
		ranked.score, ranked.matchedTerms, ranked.colloquialMatches = scoreConceptCandidate(ranked, terms)
		if precision {
			score, matched := scoreCompassPrecisionCandidate(ranked, terms)
			ranked.score += score
			ranked.matchedTerms = uniqueStrings(append(ranked.matchedTerms, matched...))
		}
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
	if attrBool(candidate.attrs, "coverage_fallback") {
		return true, "attrs_coverage_fallback"
	}
	if provenance := attrString(candidate.attrs, "fallback_provenance"); provenance != "" {
		return true, "fallback_provenance:" + provenance
	}
	if count := attrInt(candidate.attrs, "path_count"); count >= broadFallbackPathThreshold {
		return true, "path_count_exceeds_threshold"
	}
	return false, ""
}

func evidenceLanesFromCandidates(candidates []compassCandidate, facets []string, selectedPaths map[string]bool) []EvidenceLane {
	lanes := make([]EvidenceLane, 0, maxCompassLanes)
	readBudget := map[string]bool{}
	for _, candidate := range candidates {
		if candidate.suppressed || candidate.ranked.score <= 0 {
			continue
		}
		paths := firstPassPaths(candidate.ranked, readBudget, selectedPaths)
		if len(paths) == 0 {
			continue
		}
		lanes = append(lanes, EvidenceLane{
			ID:                candidate.conceptID,
			Title:             candidate.ranked.row.Title,
			Coverage:          "covered_for_first_pass",
			Confidence:        candidate.ranked.row.Confidence,
			FirstPassPaths:    paths,
			VerificationHints: candidate.ranked.verificationHints,
			FollowupSurfaces:  attrStrings(candidate.ranked.attrs, "followup_surfaces"),
			BeforeFixClaim:    attrStrings(candidate.ranked.attrs, "before_fix_claim"),
			matchedTerms:      candidate.ranked.matchedTerms,
			nodeType:          candidate.ranked.row.NodeType,
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

func candidatesForExpansion(candidates []compassCandidate) []map[string]any {
	out := make([]map[string]any, 0, len(candidates))
	for _, candidate := range candidates {
		item := map[string]any{
			"id":                 candidate.conceptID,
			"title":              candidate.ranked.row.Title,
			"node_type":          candidate.ranked.row.NodeType,
			"score":              candidate.ranked.score,
			"confidence":         candidate.ranked.row.Confidence,
			"matched_terms":      append([]string{}, candidate.ranked.matchedTerms...),
			"paths":              append([]string{}, candidate.ranked.paths...),
			"evidence_ids":       append([]string{}, candidate.ranked.row.EvidenceIDs...),
			"suppressed":         candidate.suppressed,
			"suppression_reason": candidate.reason,
		}
		if owner := attrString(candidate.ranked.attrs, "owner"); owner != "" {
			item["owner"] = owner
		}
		if domain := attrString(candidate.ranked.attrs, "domain"); domain != "" {
			item["domain"] = domain
		}
		out = append(out, item)
	}
	return out
}

func appendDiagnosticString(values []string, value string) []string {
	value = strings.TrimSpace(value)
	if value == "" {
		return values
	}
	for _, existing := range values {
		if existing == value {
			return values
		}
	}
	return append(values, value)
}

func coverageForFacets(facets []string, lanes []EvidenceLane, diagnostics []CoverageDiagnostic, precision bool) []CompassIntentFacet {
	out := make([]CompassIntentFacet, 0, len(facets))
	for _, facet := range facets {
		coveredBy := []string{}
		for _, lane := range lanes {
			if compassLaneCoversFacet(lane, facet) {
				coveredBy = appendMissingCoverage(coveredBy, lane.ID)
			}
		}
		coverage := "missing"
		risk := "needs_review"
		if len(coveredBy) > 0 {
			coverage = "covered_for_first_pass"
			risk = "first evidence path, not final edit scope"
		} else if len(lanes) > 0 {
			coverage = "partial"
		} else if precision {
			coverage = "needs_expansion_before_fix_claim"
		}
		out = append(out, CompassIntentFacet{
			Name:     facet,
			Coverage: coverage,
			Risk:     risk,
		})
	}
	return out
}

func compassCandidateTerms(input CompassInput, terms, facets []string) []string {
	values := append([]string{}, terms...)
	values = append(values, facets...)
	if !compassUsesPrecisionInput(input) {
		return uniqueStrings(values)
	}
	plan := NormalizePlan(input.Plan)
	values = append(values, termsFrom(plan.NormalizedQuery, 20)...)
	values = append(values, plan.IntentFacets...)
	values = append(values, plan.RepositorySearchTerms...)
	values = append(values, termsFrom(plan.SemanticIntake.NormalizedQuery, 20)...)
	values = append(values, plan.SemanticIntake.IntentFacets...)
	values = append(values, compassPathTerms(plan.Paths)...)
	for _, decision := range compassSelectedConceptDecisions(plan) {
		values = append(values, decision.CoveredFacets...)
		values = append(values, decision.MatchSources...)
		values = append(values, compassPathTerms(decision.Paths)...)
	}
	return uniqueStrings(values)
}

func compassSelectedPrecisionPaths(input CompassInput) map[string]bool {
	if !compassUsesPrecisionInput(input) {
		return nil
	}
	plan := NormalizePlan(input.Plan)
	paths := append([]string{}, plan.Paths...)
	for _, decision := range compassSelectedConceptDecisions(plan) {
		paths = append(paths, decision.Paths...)
	}
	selected := map[string]bool{}
	for _, path := range normalizePaths(paths) {
		selected[path] = true
	}
	return selected
}

func compassSelectedConceptDecisions(plan Plan) []ConceptDecision {
	out := []ConceptDecision{}
	for _, decision := range plan.ConceptDecisions {
		if strings.EqualFold(decision.Decision, "selected") {
			out = append(out, decision)
		}
	}
	return out
}

func scoreCompassPrecisionCandidate(candidate rankedConceptCandidate, terms []string) (int, []string) {
	material := strings.ToLower(strings.Join(uniqueStrings(append(append([]string{
		candidate.row.NodeID,
		candidate.row.NodeType,
		candidate.row.Title,
		attrString(candidate.attrs, "domain"),
		attrString(candidate.attrs, "owner"),
	}, candidate.aliases...), candidate.paths...)), " "))
	score := 0
	matched := []string{}
	for _, term := range terms {
		if !compassPrecisionTermMatches(material, term) {
			continue
		}
		score += 4
		matched = appendMissingCoverage(matched, term)
	}
	return score, matched
}

func compassPrecisionTermMatches(material, term string) bool {
	term = strings.ToLower(strings.TrimSpace(term))
	if term == "" {
		return false
	}
	if compassLooksLikePathTerm(term) {
		return strings.Contains(material, term)
	}
	return semanticMaterialMatches(material, term)
}

func compassLooksLikePathTerm(term string) bool {
	return strings.Contains(term, "/") || strings.Contains(term, "\\")
}

func compassPathTerms(paths []string) []string {
	values := []string{}
	for _, path := range paths {
		values = append(values, path)
	}
	return values
}

func compassUsesPrecisionInput(input CompassInput) bool {
	mode := normalizedCompassInputMode(input.InputMode)
	return mode == compassInputModeQueryPlan || mode == compassInputModeSemanticIntake
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

func firstPassPaths(candidate rankedConceptCandidate, readBudget map[string]bool, selectedPaths map[string]bool) []FirstPassPath {
	paths := prioritizeCompassSelectedPaths(normalizePaths(candidate.paths), selectedPaths)
	out := make([]FirstPassPath, 0, len(paths))
	for _, path := range paths {
		if readBudget[path] {
			continue
		}
		if len(readBudget) >= maxCompassReads {
			break
		}
		out = append(out, FirstPassPath{
			Path:         path,
			Reason:       "owned_by_ranked_project_cognition_node",
			EvidenceHint: strings.Join(candidate.row.EvidenceIDs, ","),
		})
		readBudget[path] = true
		if len(out) >= maxCompassPathsPerLane {
			break
		}
	}
	return out
}

func prioritizeCompassSelectedPaths(paths []string, selectedPaths map[string]bool) []string {
	if len(selectedPaths) == 0 || len(paths) == 0 {
		return paths
	}
	prioritized := make([]string, 0, len(paths))
	for _, path := range paths {
		if selectedPaths[path] {
			prioritized = append(prioritized, path)
		}
	}
	for _, path := range paths {
		if !selectedPaths[path] {
			prioritized = append(prioritized, path)
		}
	}
	return prioritized
}

func compassLaneCoversFacet(lane EvidenceLane, facet string) bool {
	material := strings.ToLower(strings.Join(append([]string{lane.Title, lane.nodeType}, lane.matchedTerms...), " "))
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
	mode := normalizedCompassInputMode(input.InputMode)
	if status.Readiness == rt.ReadyReadiness && (mode == compassInputModeQueryPlan || mode == compassInputModeSemanticIntake) && !hasUncovered {
		return compassStateUsable
	}
	if (status.Readiness == rt.ReadyReadiness || status.Readiness == rt.ReviewReadiness) && len(payload.EvidenceLanes) > 0 {
		return compassStateUsableWithReview
	}
	return compassStateNeedsExpansionBeforeFix
}

func normalizedCompassInputMode(mode string) string {
	mode = strings.TrimSpace(mode)
	if mode == "" {
		return compassInputModeQuery
	}
	switch {
	case strings.EqualFold(mode, compassInputModeQueryPlan):
		return compassInputModeQueryPlan
	case strings.EqualFold(mode, compassInputModeSemanticIntake):
		return compassInputModeSemanticIntake
	default:
		return compassInputModeQuery
	}
}

func compassHasUncoveredFacet(facets []CompassIntentFacet) bool {
	for _, facet := range facets {
		if facet.Coverage != "covered_for_first_pass" {
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

func attrBool(attrs map[string]any, key string) bool {
	value, ok := attrs[key]
	if !ok {
		return false
	}
	switch typed := value.(type) {
	case bool:
		return typed
	case string:
		return strings.EqualFold(strings.TrimSpace(typed), "true")
	default:
		return false
	}
}
