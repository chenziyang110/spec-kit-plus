package query

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"sort"
	"strconv"
	"strings"

	rt "github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/runtime"
	"github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/runtimegate"
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
	compassRecommendedActionReconcileClaims = "reconcile_claims_with_minimal_live_reads"
)

type CompassInput struct {
	Intent          string
	Query           string
	Plan            Plan
	PlanDiagnostics PlanDiagnostics
	InputMode       string
}

type CompassPayload struct {
	EpistemicContract             EpistemicContract             `json:"epistemic_contract"`
	ClaimRetrievalContractVersion int                           `json:"claim_retrieval_contract_version"`
	Readiness                     string                        `json:"readiness"`
	CompassState                  string                        `json:"compass_state"`
	Mode                          string                        `json:"mode"`
	FacetSource                   string                        `json:"facet_source"`
	ActiveGenerationID            string                        `json:"active_generation_id,omitempty"`
	CandidateUniverseVersion      int                           `json:"candidate_universe_version"`
	QueryFingerprint              string                        `json:"query_fingerprint"`
	Summary                       string                        `json:"summary"`
	IntentFacets                  []CompassIntentFacet          `json:"intent_facets"`
	EvidenceLanes                 []EvidenceLane                `json:"evidence_lanes"`
	MinimalLiveReads              []string                      `json:"minimal_live_reads"`
	CoverageDiagnostics           []CoverageDiagnostic          `json:"coverage_diagnostics"`
	ExpansionRef                  *ExpansionRef                 `json:"expansion_ref,omitempty"`
	AgentNormalization            *AgentNormalizationDiagnostic `json:"agent_normalization,omitempty"`
	Warnings                      []string                      `json:"warnings,omitempty"`
	RepairHints                   []string                      `json:"repair_hints,omitempty"`
	Errors                        []string                      `json:"errors"`
	RecommendedNextAction         string                        `json:"recommended_next_action"`
	RecoveryAction                string                        `json:"recovery_action,omitempty"`
	BaselineKind                  string                        `json:"baseline_kind,omitempty"`
}

type CompassIntentFacet struct {
	Name     string `json:"name"`
	Coverage string `json:"coverage"`
	Risk     string `json:"risk,omitempty"`
}

type EvidenceLane struct {
	ID                string               `json:"id"`
	Title             string               `json:"title"`
	Coverage          string               `json:"coverage"`
	Confidence        string               `json:"confidence"`
	FirstPassPaths    []FirstPassPath      `json:"first_pass_paths"`
	VerificationHints []string             `json:"verification_hints"`
	FollowupSurfaces  []string             `json:"followup_surfaces"`
	BeforeFixClaim    []string             `json:"before_fix_claim"`
	ClaimRefs         []ClaimRef           `json:"claim_refs,omitempty"`
	ClaimRanking      *ClaimRankingSummary `json:"claim_ranking,omitempty"`
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
	ID                            string                          `json:"id,omitempty"`
	ClaimRetrievalContractVersion int                             `json:"claim_retrieval_contract_version"`
	ActiveGenerationID            string                          `json:"active_generation_id,omitempty"`
	CandidateUniverseVersion      int                             `json:"candidate_universe_version"`
	QueryFingerprint              string                          `json:"query_fingerprint,omitempty"`
	AvailableSections             map[string]ExpansionSectionMeta `json:"available_sections,omitempty"`
	StaleBehavior                 string                          `json:"stale_behavior,omitempty"`
}

type ExpansionSectionMeta struct {
	State          string `json:"state"`
	EstimatedItems int    `json:"estimated_items"`
}

type compassCandidate struct {
	ranked       rankedConceptCandidate
	conceptID    string
	matchScore   int
	claimRanking ClaimRankingSummary
	suppressed   bool
	reason       string
}

func ParseSemanticIntakeFile(path string) (SemanticIntake, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return SemanticIntake{}, fmt.Errorf("read semantic intake file: %w", err)
	}
	var payload map[string]json.RawMessage
	if err := json.Unmarshal(data, &payload); err != nil {
		return SemanticIntake{}, fmt.Errorf("decode semantic intake file: %w", err)
	}
	if len(payload) == 0 {
		return SemanticIntake{}, fmt.Errorf("semantic intake file has unsupported shape: expected semantic intake object or semantic_intake wrapper")
	}
	if raw, ok := payload["semantic_intake"]; ok {
		if !isJSONObject(raw) {
			return SemanticIntake{}, fmt.Errorf("semantic_intake has unsupported shape: expected object")
		}
		var intake SemanticIntake
		if err := json.Unmarshal(raw, &intake); err != nil {
			return SemanticIntake{}, fmt.Errorf("decode semantic_intake: %w", err)
		}
		return normalizeSemanticIntake(intake), nil
	}
	if !looksLikeSemanticIntake(payload) {
		return SemanticIntake{}, fmt.Errorf("semantic intake file has unsupported shape: expected semantic intake object or semantic_intake wrapper")
	}
	var intake SemanticIntake
	if err := json.Unmarshal(data, &intake); err != nil {
		return SemanticIntake{}, fmt.Errorf("decode semantic intake object: %w", err)
	}
	return normalizeSemanticIntake(intake), nil
}

func isJSONObject(raw json.RawMessage) bool {
	return strings.HasPrefix(strings.TrimSpace(string(raw)), "{")
}

func looksLikeSemanticIntake(payload map[string]json.RawMessage) bool {
	for _, key := range []string{
		"workflow_intent",
		"normalized_query",
		"intent_facets",
		"negative_constraints",
		"alias_interpretations",
		"open_semantic_questions",
	} {
		if _, ok := payload[key]; ok {
			return true
		}
	}
	return false
}

func Compass(paths rt.Paths, input CompassInput) (CompassPayload, error) {
	if agreement, exists := runtimegate.CheckExisting(paths); exists && agreement.Status != "ok" {
		return blockedAgreementCompassPayload(input, agreement), nil
	}
	status, err := rt.ReadStatus(paths)
	if err != nil {
		return CompassPayload{}, err
	}

	terms := termsFrom(strings.Join([]string{input.Intent, input.Query}, " "), 30)
	facets, facetSource := compassFacets(input, terms)
	payload := CompassPayload{
		EpistemicContract:             NewEpistemicContract(),
		ClaimRetrievalContractVersion: ClaimRetrievalContractVersion,
		Readiness:                     status.Readiness,
		CompassState:                  compassStateBlocked,
		Mode:                          compassMode,
		FacetSource:                   facetSource,
		ActiveGenerationID:            status.ActiveGenerationID,
		CandidateUniverseVersion:      CandidateUniverseVersion,
		QueryFingerprint:              compassFingerprint(input),
		Summary:                       "Compass packet is blocked until project cognition readiness is restored.",
		IntentFacets:                  []CompassIntentFacet{},
		EvidenceLanes:                 []EvidenceLane{},
		MinimalLiveReads:              []string{},
		CoverageDiagnostics:           []CoverageDiagnostic{},
		Warnings:                      input.PlanDiagnostics.Warnings,
		RepairHints:                   input.PlanDiagnostics.RepairHints,
		Errors:                        []string{},
		RecommendedNextAction:         status.RecommendedNextAction,
		BaselineKind:                  status.BaselineKind,
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
	claimRecords := []store.GraphClaimEvidence{}
	if st != nil {
		defer st.Close()
		rows, err := st.AllActiveConceptCandidateRows(context.Background())
		if err != nil {
			return CompassPayload{}, err
		}
		if len(rows) > 0 && payload.ActiveGenerationID == "" {
			payload.ActiveGenerationID = rows[0].GenerationID
		}
		candidates = compassCandidates(rows, compassCandidateTerms(input, terms, facets), compassUsesPrecisionInput(input), compassPrecisionConceptFilter(input))
		claimLifecycleSummaries, err := st.ClaimLifecycleSummariesForNodeIDs(context.Background(), nodeIDsFromCompassCandidates(candidates))
		if err != nil {
			return CompassPayload{}, err
		}
		candidates = applyClaimRanking(candidates, claimLifecycleSummaries)
		claimRecords, err = st.ClaimEvidenceForNodeIDs(context.Background(), nodeIDsFromCompassCandidates(candidates))
		if err != nil {
			return CompassPayload{}, err
		}
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
		payload.EvidenceLanes = evidenceLanesFromCandidates(candidates, facets, selectedPaths, claimRefsByNode(claimRecords))
		payload.CoverageDiagnostics = append(payload.CoverageDiagnostics, claimReconciliationDiagnostics(payload.EvidenceLanes, facets)...)
		payload.MinimalLiveReads = minimalReadsFromLanes(payload.EvidenceLanes)
	}
	payload.IntentFacets = coverageForFacets(facets, payload.EvidenceLanes, payload.CoverageDiagnostics, true)
	payload.AgentNormalization = compassAgentNormalization(status, input, payload)
	payload.CompassState = compassState(status, input, payload)
	payload.RecommendedNextAction = compassRecommendedNextAction(status, payload.CompassState, payload.CoverageDiagnostics)
	payload.Summary = compassSummary(payload)
	if len(candidates) > 0 {
		sectionPayloads := map[string]any{
			"related_paths":   payload.MinimalLiveReads,
			"raw_candidates":  candidatesForExpansion(candidates),
			"coverage_gaps":   payload.CoverageDiagnostics,
			"graph_neighbors": []map[string]any{},
			"claim_evidence":  claimSignals(claimRecords, maxExpansionClaimSignals, maxExpansionEvidenceRefs),
		}
		bundle := ExpansionBundle{
			ClaimRetrievalContractVersion: ClaimRetrievalContractVersion,
			ActiveGenerationID:            payload.ActiveGenerationID,
			CandidateUniverseVersion:      payload.CandidateUniverseVersion,
			QueryFingerprint:              payload.QueryFingerprint,
			Sections:                      expansionSectionMeta(sectionPayloads),
			SectionPayloads:               sectionPayloads,
			CreatedAt:                     deterministicExpansionCreatedAt(payload.QueryFingerprint),
		}
		bundle.ID = expansionBundleID(bundle)
		ref, err := writeExpansionBundle(paths, bundle)
		if err != nil {
			payload.Warnings = appendDiagnosticString(payload.Warnings, "expansion_bundle_write_failed:"+err.Error())
		} else {
			payload.ExpansionRef = &ref
		}
	}
	return payload, nil
}

func blockedAgreementCompassPayload(input CompassInput, agreement runtimegate.Agreement) CompassPayload {
	recoveryAction := firstNonEmpty(agreement.RecoveryAction, agreement.RecommendedNextAction)
	recommendedAction := firstNonEmpty(agreement.RecommendedNextAction, recoveryAction)
	readiness := agreement.Readiness
	if compassAgreementNeedsRebuild(agreement, recoveryAction) {
		readiness = rt.NeedsRebuildReadiness
		recoveryAction = "run_map_scan_build"
		recommendedAction = "run_map_scan_build"
	}
	if readiness == "" {
		readiness = rt.BlockedReadiness
	}
	_, facetSource := compassFacets(input, termsFrom(strings.Join([]string{input.Intent, input.Query}, " "), 30))
	return CompassPayload{
		EpistemicContract:             NewEpistemicContract(),
		ClaimRetrievalContractVersion: ClaimRetrievalContractVersion,
		Readiness:                     readiness,
		CompassState:                  compassStateBlocked,
		Mode:                          compassMode,
		FacetSource:                   facetSource,
		ActiveGenerationID:            firstNonEmpty(agreement.StatusGenerationID, agreement.DBActiveGenerationID),
		CandidateUniverseVersion:      CandidateUniverseVersion,
		QueryFingerprint:              compassFingerprint(input),
		Summary:                       "Compass packet is blocked until project cognition baseline is rebuilt.",
		IntentFacets:                  []CompassIntentFacet{},
		EvidenceLanes:                 []EvidenceLane{},
		MinimalLiveReads:              []string{},
		CoverageDiagnostics:           []CoverageDiagnostic{},
		Warnings:                      input.PlanDiagnostics.Warnings,
		RepairHints:                   input.PlanDiagnostics.RepairHints,
		Errors:                        append([]string{}, agreement.Errors...),
		RecommendedNextAction:         recommendedAction,
		RecoveryAction:                recoveryAction,
		BaselineKind:                  firstNonEmpty(agreement.StatusBaselineKind, agreement.DBBaselineKind),
	}
}

func compassAgreementNeedsRebuild(agreement runtimegate.Agreement, recoveryAction string) bool {
	if recoveryAction == "run_map_scan_build" {
		return true
	}
	for _, err := range agreement.Errors {
		if strings.Contains(err, "project-cognition.db metadata schema_version") {
			return true
		}
	}
	return false
}

func firstNonEmpty(values ...string) string {
	for _, value := range values {
		if value != "" {
			return value
		}
	}
	return ""
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

type compassConceptFilter struct {
	selected map[string]bool
	rejected map[string]bool
}

func (filter compassConceptFilter) accepts(conceptID string) bool {
	if filter.rejected[conceptID] {
		return false
	}
	return len(filter.selected) == 0 || filter.selected[conceptID]
}

func compassCandidates(rows []store.ConceptCandidateRow, terms []string, precision bool, filter compassConceptFilter) []compassCandidate {
	candidates := make([]compassCandidate, 0, len(rows))
	for _, row := range rows {
		conceptID := "concept:" + row.GenerationID + ":" + row.NodeID
		if !filter.accepts(conceptID) {
			continue
		}
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
			ranked:       ranked,
			conceptID:    conceptID,
			matchScore:   ranked.score,
			claimRanking: ClaimRankingSummary{State: claimRankingStateNone},
			suppressed:   suppressed,
			reason:       reason,
		})
	}
	sortCompassCandidates(candidates)
	return candidates
}

func applyClaimRanking(candidates []compassCandidate, summaries []store.GraphClaimLifecycleSummary) []compassCandidate {
	rankings := claimRankingByNode(summaries)
	for index := range candidates {
		candidate := &candidates[index]
		candidate.ranked.score = candidate.matchScore
		candidate.claimRanking = ClaimRankingSummary{State: claimRankingStateNone}
		if candidate.matchScore <= 0 {
			continue
		}
		if ranking, ok := rankings[candidate.ranked.row.NodeID]; ok {
			candidate.claimRanking = ranking
			candidate.ranked.score = maxInt(1, candidate.matchScore+ranking.Adjustment)
		}
	}
	sortCompassCandidates(candidates)
	return candidates
}

func sortCompassCandidates(candidates []compassCandidate) {
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

func evidenceLanesFromCandidates(candidates []compassCandidate, facets []string, selectedPaths map[string]bool, claimRefs map[string][]ClaimRef) []EvidenceLane {
	lanes := make([]EvidenceLane, 0, maxCompassLanes)
	readBudget := map[string]bool{}
	for _, candidate := range candidates {
		if candidate.suppressed || candidate.matchScore <= 0 {
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
			ClaimRefs:         append([]ClaimRef{}, claimRefs[candidate.ranked.row.NodeID]...),
			ClaimRanking:      compactClaimRanking(candidate.claimRanking),
			matchedTerms:      candidate.ranked.matchedTerms,
			nodeType:          candidate.ranked.row.NodeType,
		})
		if len(lanes) >= maxCompassLanes {
			break
		}
	}
	return lanes
}

func compactClaimRanking(ranking ClaimRankingSummary) *ClaimRankingSummary {
	if ranking.State == "" || ranking.State == claimRankingStateNone {
		return nil
	}
	copy := ranking
	return &copy
}

func claimReconciliationDiagnostics(lanes []EvidenceLane, facets []string) []CoverageDiagnostic {
	diagnostics := []CoverageDiagnostic{}
	for _, lane := range lanes {
		if lane.ClaimRanking == nil || !lane.ClaimRanking.ReconciliationRequired {
			continue
		}
		kind := "stale_claim_signal"
		message := "Selected route " + lane.Title + " has stale project cognition claims and requires live refresh."
		if lane.ClaimRanking.State == "contradicted" {
			kind = "contradicted_claim_signal"
			message = "Selected route " + lane.Title + " has contradicted project cognition claims and requires live reconciliation."
		}
		diagnostics = append(diagnostics, CoverageDiagnostic{
			Kind:              kind,
			Severity:          "warning",
			Message:           message,
			AffectedFacets:    append([]string{}, facets...),
			RecommendedAction: lane.ClaimRanking.ReconciliationAction,
		})
	}
	return diagnostics
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
			"match_score":        candidate.matchScore,
			"confidence":         candidate.ranked.row.Confidence,
			"matched_terms":      append([]string{}, candidate.ranked.matchedTerms...),
			"paths":              append([]string{}, candidate.ranked.paths...),
			"evidence_ids":       append([]string{}, candidate.ranked.row.EvidenceIDs...),
			"suppressed":         candidate.suppressed,
			"suppression_reason": candidate.reason,
		}
		if ranking := compactClaimRanking(candidate.claimRanking); ranking != nil {
			item["claim_ranking"] = ranking
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

func compassPrecisionConceptFilter(input CompassInput) compassConceptFilter {
	if normalizedCompassInputMode(input.InputMode) != compassInputModeQueryPlan {
		return compassConceptFilter{}
	}
	plan := NormalizePlan(input.Plan)
	filter := compassConceptFilter{
		selected: map[string]bool{},
		rejected: map[string]bool{},
	}
	for _, conceptID := range plan.SelectedConcepts {
		filter.selected[conceptID] = true
	}
	for _, conceptID := range plan.RejectedConcepts {
		filter.rejected[conceptID] = true
	}
	for _, decision := range plan.ConceptDecisions {
		switch strings.ToLower(strings.TrimSpace(decision.Decision)) {
		case "selected":
			filter.selected[decision.ConceptID] = true
		case "rejected":
			filter.rejected[decision.ConceptID] = true
		}
	}
	return filter
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
	if status.Readiness == rt.ReadyReadiness && (mode == compassInputModeQueryPlan || mode == compassInputModeSemanticIntake) && !hasUncovered && !compassHasClaimReconciliationDiagnostic(payload.CoverageDiagnostics) {
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

func compassRecommendedNextAction(status rt.Status, state string, diagnostics []CoverageDiagnostic) string {
	if state == compassStateUsableWithReview && compassHasClaimReconciliationDiagnostic(diagnostics) {
		return compassRecommendedActionReconcileClaims
	}
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

func compassHasClaimReconciliationDiagnostic(diagnostics []CoverageDiagnostic) bool {
	for _, diagnostic := range diagnostics {
		if diagnostic.Kind == "stale_claim_signal" || diagnostic.Kind == "contradicted_claim_signal" {
			return true
		}
	}
	return false
}

func compassAgentNormalization(status rt.Status, input CompassInput, payload CompassPayload) *AgentNormalizationDiagnostic {
	if !agentNormalizationCatalogUsable(status) {
		return nil
	}
	triggers := []string{}
	mode := normalizedCompassInputMode(input.InputMode)
	if mode == compassInputModeQuery && payload.FacetSource == compassFacetSourceMechanical && queryHasCJKOrMixedCJKASCII(input.Query) {
		if len(payload.EvidenceLanes) == 0 || compassMechanicalFacetsNeedSemanticIntake(payload.IntentFacets) {
			triggers = append(triggers, "cjk_or_mixed_language_query")
		}
		if compassMechanicalFacetsNeedSemanticIntake(payload.IntentFacets) {
			triggers = appendMissingCoverage(triggers, "partial_cjk_mechanical_facets")
		}
	}
	if mode == compassInputModeQuery && len(payload.EvidenceLanes) == 0 {
		for _, diagnostic := range payload.CoverageDiagnostics {
			if diagnostic.Kind == "broad_fallback_suppressed" {
				triggers = appendMissingCoverage(triggers, "only_broad_fallback_matched")
			}
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
		Reminder: "Translate user language into project vocabulary before fixing when compact evidence lanes are absent or mechanical CJK facets remain weak.",
	}
}

func compassMechanicalFacetsNeedSemanticIntake(facets []CompassIntentFacet) bool {
	for _, facet := range facets {
		if facet.Coverage == "covered_for_first_pass" {
			continue
		}
		if queryHasCJKOrMixedCJKASCII(facet.Name) && len([]rune(facet.Name)) >= 4 {
			return true
		}
	}
	return false
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
