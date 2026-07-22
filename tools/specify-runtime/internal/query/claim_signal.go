package query

import (
	"strings"

	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/store"
)

const (
	maxQueryClaimSignals        = 8
	maxQueryClaimEvidenceRefs   = 2
	maxExpansionClaimSignals    = 25
	maxExpansionEvidenceRefs    = 6
	maxCompassClaimRefsPerLane  = 3
	claimConfidenceScope        = "route_candidate"
	claimRankingStateNone       = "none"
	claimRankingStateCandidate  = "candidate"
	claimRankingBoost           = 1
	claimRankingStalePenalty    = -1
	claimRankingConflictPenalty = -2
	claimActionRefreshStale     = "refresh_claim_evidence_then_verify_live_repository"
	claimActionReconcile        = "reconcile_contradicted_claim_with_live_repository"
)

// ClaimSignal is a bounded navigation signal. RouteConfidence is inherited
// from the owning graph node and never proves current repository behavior.
type ClaimSignal struct {
	ID                       string             `json:"id"`
	NodeID                   string             `json:"node_id"`
	GraphClaimType           string             `json:"graph_claim_type"`
	Summary                  string             `json:"summary"`
	State                    string             `json:"state"`
	Freshness                string             `json:"freshness"`
	StateReason              string             `json:"state_reason"`
	RouteConfidence          string             `json:"route_confidence"`
	ConfidenceScope          string             `json:"confidence_scope"`
	Stale                    bool               `json:"stale"`
	LiveVerificationRequired bool               `json:"live_verification_required"`
	EvidenceCount            int                `json:"evidence_count"`
	EvidenceRefs             []ClaimEvidenceRef `json:"evidence_refs"`
	EvidenceTruncated        bool               `json:"evidence_truncated,omitempty"`
}

type ClaimEvidenceRef struct {
	ID         string `json:"id"`
	Role       string `json:"role"`
	SourceKind string `json:"source_kind"`
	SourcePath string `json:"source_path"`
	Span       string `json:"span,omitempty"`
	CommitSHA  string `json:"commit_sha,omitempty"`
}

type ClaimRef struct {
	ID                       string `json:"id"`
	GraphClaimType           string `json:"graph_claim_type"`
	Summary                  string `json:"summary"`
	State                    string `json:"state"`
	Freshness                string `json:"freshness"`
	RouteConfidence          string `json:"route_confidence"`
	ConfidenceScope          string `json:"confidence_scope"`
	Stale                    bool   `json:"stale"`
	LiveVerificationRequired bool   `json:"live_verification_required"`
}

type ClaimRankingSummary struct {
	State                    string `json:"state"`
	Adjustment               int    `json:"adjustment"`
	ReconciliationRequired   bool   `json:"reconciliation_required"`
	ReconciliationAction     string `json:"reconciliation_action,omitempty"`
	LiveVerificationRequired bool   `json:"live_verification_required"`
}

func claimSignals(records []store.GraphClaimEvidence, claimLimit, evidenceLimit int) []ClaimSignal {
	if claimLimit <= 0 || claimLimit > len(records) {
		claimLimit = len(records)
	}
	out := make([]ClaimSignal, 0, claimLimit)
	for _, record := range records[:claimLimit] {
		refLimit := evidenceLimit
		if refLimit <= 0 || refLimit > len(record.Evidence) {
			refLimit = len(record.Evidence)
		}
		refs := make([]ClaimEvidenceRef, 0, refLimit)
		for _, evidence := range record.Evidence[:refLimit] {
			refs = append(refs, ClaimEvidenceRef{
				ID: evidence.ID, Role: evidence.Role, SourceKind: evidence.SourceKind,
				SourcePath: evidence.SourcePath, Span: evidence.Span, CommitSHA: evidence.CommitSHA,
			})
		}
		out = append(out, ClaimSignal{
			ID: record.ID, NodeID: record.NodeID, GraphClaimType: record.GraphClaimType, Summary: record.Summary,
			State: record.State, Freshness: record.Freshness, StateReason: record.StateReason,
			RouteConfidence: record.RouteConfidence, ConfidenceScope: claimConfidenceScope,
			Stale: claimSignalIsStale(record), LiveVerificationRequired: true,
			EvidenceCount: len(record.Evidence), EvidenceRefs: refs, EvidenceTruncated: len(record.Evidence) > refLimit,
		})
	}
	return out
}

func claimRefsByNode(records []store.GraphClaimEvidence) map[string][]ClaimRef {
	out := map[string][]ClaimRef{}
	for _, record := range records {
		refs := out[record.NodeID]
		if len(refs) >= maxCompassClaimRefsPerLane {
			continue
		}
		out[record.NodeID] = append(refs, ClaimRef{
			ID: record.ID, GraphClaimType: record.GraphClaimType, Summary: record.Summary,
			State: record.State, Freshness: record.Freshness, RouteConfidence: record.RouteConfidence,
			ConfidenceScope: claimConfidenceScope, Stale: claimSignalIsStale(record), LiveVerificationRequired: true,
		})
	}
	return out
}

func claimRankingByNode(summaries []store.GraphClaimLifecycleSummary) map[string]ClaimRankingSummary {
	out := make(map[string]ClaimRankingSummary, len(summaries))
	for _, summary := range summaries {
		out[summary.NodeID] = claimRankingSummary(summary)
	}
	return out
}

func claimRankingSummary(summary store.GraphClaimLifecycleSummary) ClaimRankingSummary {
	ranking := ClaimRankingSummary{State: claimRankingStateNone}
	if summary.ClaimCount <= 0 {
		return ranking
	}
	ranking.State = claimRankingStateCandidate
	ranking.LiveVerificationRequired = true
	switch {
	case summary.ContradictedCount > 0:
		ranking.State = "contradicted"
		ranking.Adjustment = claimRankingConflictPenalty
		ranking.ReconciliationRequired = true
		ranking.ReconciliationAction = claimActionReconcile
	case summary.StaleCount > 0:
		ranking.State = "stale"
		ranking.Adjustment = claimRankingStalePenalty
		ranking.ReconciliationRequired = true
		ranking.ReconciliationAction = claimActionRefreshStale
	case summary.FreshVerifiedCount > 0:
		ranking.State = "verified_in_graph_generation"
		ranking.Adjustment = claimRankingBoost
	case summary.FreshSupportedCount > 0:
		ranking.State = "supported"
		ranking.Adjustment = claimRankingBoost
	}
	return ranking
}

func compactGraphClaims(records []store.GraphClaimEvidence) []map[string]any {
	out := make([]map[string]any, 0, len(records))
	for _, record := range records {
		out = append(out, map[string]any{
			"id": record.ID, "node_id": record.NodeID, "graph_claim_type": record.GraphClaimType, "summary": record.Summary,
			"state": record.State, "freshness": record.Freshness, "state_reason": record.StateReason,
		})
	}
	return out
}

func claimSignalIsStale(record store.GraphClaimEvidence) bool {
	return strings.EqualFold(record.State, "stale") || strings.EqualFold(record.Freshness, "stale")
}

func nodeIDsFromCompassCandidates(candidates []compassCandidate) []string {
	nodeIDs := make([]string, 0, len(candidates))
	for _, candidate := range candidates {
		nodeIDs = append(nodeIDs, candidate.ranked.row.NodeID)
	}
	return normalizeStrings(nodeIDs)
}
