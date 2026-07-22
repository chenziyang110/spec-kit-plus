// Package claim defines the deterministic lifecycle for project-cognition graph claims.
// Graph claims are navigation assertions inside one graph generation; they never
// authorize workflow final claims or certify current repository truth.
package claim

import (
	"encoding/json"
	"sort"
	"strings"
)

type State string

const (
	StateCandidate    State = "candidate"
	StateSupported    State = "supported"
	StateVerified     State = "verified_in_graph_generation"
	StateContradicted State = "contradicted"
	StateStale        State = "stale"
)

type Freshness string

const (
	FreshnessUnknown Freshness = "unknown"
	FreshnessFresh   Freshness = "fresh"
	FreshnessStale   Freshness = "stale"
)

type VerificationResult string

const (
	VerificationPassed       VerificationResult = "passed"
	VerificationFailed       VerificationResult = "failed"
	VerificationBlocked      VerificationResult = "blocked"
	VerificationInconclusive VerificationResult = "inconclusive"
	VerificationContradicted VerificationResult = "contradicted"
)

type Verification struct {
	ID         string             `json:"id"`
	Result     VerificationResult `json:"result"`
	Command    string             `json:"command,omitempty"`
	EvidenceID string             `json:"evidence_id,omitempty"`
	ObservedAt string             `json:"observed_at,omitempty"`
	Attrs      map[string]any     `json:"attrs,omitempty"`
}

// ReconciliationSignals are runtime-validated observations. They deliberately
// contain no requested target state: the lifecycle derives that state.
type ReconciliationSignals struct {
	SupportingEvidence    bool
	ContradictingEvidence bool
	VerificationResult    VerificationResult
}

type ReconciliationDecision struct {
	State     State
	Freshness Freshness
}

type Candidate struct {
	ID                       string         `json:"id"`
	NodeID                   string         `json:"node_id"`
	GraphClaimType           string         `json:"graph_claim_type"`
	Summary                  string         `json:"summary"`
	RequestedState           State          `json:"requested_state,omitempty"`
	SupportingEvidenceIDs    []string       `json:"supporting_evidence_ids"`
	ContradictingEvidenceIDs []string       `json:"contradicting_evidence_ids"`
	Verifications            []Verification `json:"verifications"`
	StaleReason              string         `json:"stale_reason,omitempty"`
	Attrs                    map[string]any `json:"attrs,omitempty"`
}

type Compiled struct {
	ID                       string         `json:"id"`
	NodeID                   string         `json:"node_id"`
	GraphClaimType           string         `json:"graph_claim_type"`
	Summary                  string         `json:"summary"`
	State                    State          `json:"state"`
	Freshness                Freshness      `json:"freshness"`
	StateReason              string         `json:"state_reason"`
	SupportingEvidenceIDs    []string       `json:"supporting_evidence_ids"`
	ContradictingEvidenceIDs []string       `json:"contradicting_evidence_ids"`
	Verifications            []Verification `json:"verifications"`
	Attrs                    map[string]any `json:"attrs,omitempty"`
}

func Compile(candidate Candidate) Compiled {
	compiled := Compiled{
		ID:                       strings.TrimSpace(candidate.ID),
		NodeID:                   strings.TrimSpace(candidate.NodeID),
		GraphClaimType:           strings.TrimSpace(candidate.GraphClaimType),
		Summary:                  strings.TrimSpace(candidate.Summary),
		SupportingEvidenceIDs:    uniqueSorted(candidate.SupportingEvidenceIDs),
		ContradictingEvidenceIDs: uniqueSorted(candidate.ContradictingEvidenceIDs),
		Verifications:            cloneAndSortVerifications(candidate.Verifications),
		Attrs:                    cloneMap(candidate.Attrs),
	}

	switch {
	case strings.TrimSpace(candidate.StaleReason) != "":
		compiled.State = StateStale
		compiled.Freshness = FreshnessStale
		compiled.StateReason = strings.TrimSpace(candidate.StaleReason)
	case len(compiled.ContradictingEvidenceIDs) > 0 || latestVerificationContradicts(compiled.Verifications):
		compiled.State = StateContradicted
		compiled.Freshness = FreshnessFresh
		compiled.StateReason = "contradicting_evidence"
	case len(compiled.SupportingEvidenceIDs) > 0 && latestVerificationPassed(compiled.Verifications):
		compiled.State = StateVerified
		compiled.Freshness = FreshnessFresh
		compiled.StateReason = "supporting_evidence_and_current_verification"
	case len(compiled.SupportingEvidenceIDs) > 0:
		compiled.State = StateSupported
		compiled.Freshness = FreshnessFresh
		compiled.StateReason = "supporting_evidence"
	default:
		compiled.State = StateCandidate
		compiled.Freshness = FreshnessUnknown
		compiled.StateReason = "evidence_required"
	}
	return compiled
}

func CanTransition(from, to State) bool {
	if from == to {
		return true
	}
	switch from {
	case StateCandidate:
		return to == StateSupported || to == StateContradicted || to == StateStale
	case StateSupported:
		return to == StateVerified || to == StateContradicted || to == StateStale
	case StateVerified:
		return to == StateContradicted || to == StateStale
	case StateContradicted:
		return to == StateStale
	default:
		return false
	}
}

// CanReconcileTransition is intentionally separate from CanTransition. Only
// the evidence-validating reconciliation path may replace a stale or
// contradicted basis and recover a graph claim within the active generation.
func CanReconcileTransition(from, to State) bool {
	if from == to {
		return true
	}
	switch from {
	case StateCandidate:
		return to == StateSupported || to == StateVerified || to == StateContradicted || to == StateStale
	case StateSupported:
		return to == StateVerified || to == StateContradicted || to == StateStale
	case StateVerified:
		return to == StateSupported || to == StateContradicted || to == StateStale
	case StateContradicted, StateStale:
		return to == StateSupported || to == StateVerified || to == StateContradicted || to == StateStale
	default:
		return false
	}
}

// DeriveReconciliation computes the head state from a new, bounded evidence
// basis. A failed or blocked command is not itself falsifying evidence.
func DeriveReconciliation(from State, currentFreshness Freshness, signals ReconciliationSignals) ReconciliationDecision {
	decision := ReconciliationDecision{State: from, Freshness: currentFreshness}
	if signals.ContradictingEvidence || signals.VerificationResult == VerificationContradicted {
		return ReconciliationDecision{State: StateContradicted, Freshness: FreshnessFresh}
	}
	switch signals.VerificationResult {
	case VerificationFailed, VerificationBlocked, VerificationInconclusive:
		return decision
	case VerificationPassed:
		if signals.SupportingEvidence {
			return ReconciliationDecision{State: StateVerified, Freshness: FreshnessFresh}
		}
		return decision
	case "":
		if signals.SupportingEvidence {
			return ReconciliationDecision{State: StateSupported, Freshness: FreshnessFresh}
		}
		return decision
	default:
		return decision
	}
}

func latestVerificationPassed(rows []Verification) bool {
	if len(rows) == 0 {
		return false
	}
	latest := rows[len(rows)-1]
	return latest.Result == VerificationPassed && strings.TrimSpace(latest.EvidenceID) != ""
}

func latestVerificationContradicts(rows []Verification) bool {
	if len(rows) == 0 {
		return false
	}
	result := rows[len(rows)-1].Result
	return result == VerificationFailed || result == VerificationContradicted
}

func cloneAndSortVerifications(rows []Verification) []Verification {
	out := make([]Verification, len(rows))
	for i, row := range rows {
		row.ID = strings.TrimSpace(row.ID)
		row.EvidenceID = strings.TrimSpace(row.EvidenceID)
		row.Command = strings.TrimSpace(row.Command)
		row.ObservedAt = strings.TrimSpace(row.ObservedAt)
		row.Attrs = cloneMap(row.Attrs)
		out[i] = row
	}
	sort.Slice(out, func(i, j int) bool {
		if out[i].ObservedAt != out[j].ObservedAt {
			return out[i].ObservedAt < out[j].ObservedAt
		}
		if out[i].ID != out[j].ID {
			return out[i].ID < out[j].ID
		}
		return verificationSortKey(out[i]) < verificationSortKey(out[j])
	})
	return out
}

func verificationSortKey(value Verification) string {
	encoded, _ := json.Marshal(value)
	return string(encoded)
}

func uniqueSorted(values []string) []string {
	seen := make(map[string]bool, len(values))
	for _, value := range values {
		if value = strings.TrimSpace(value); value != "" {
			seen[value] = true
		}
	}
	out := make([]string, 0, len(seen))
	for value := range seen {
		out = append(out, value)
	}
	sort.Strings(out)
	return out
}

func cloneMap(input map[string]any) map[string]any {
	if input == nil {
		return nil
	}
	out := make(map[string]any, len(input))
	for key, value := range input {
		out[key] = value
	}
	return out
}
