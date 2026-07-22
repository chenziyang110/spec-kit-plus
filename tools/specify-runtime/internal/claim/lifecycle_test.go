package claim

import (
	"reflect"
	"testing"
)

func TestCompileDerivesLifecycleFromEvidenceInsteadOfRequestedState(t *testing.T) {
	tests := []struct {
		name      string
		candidate Candidate
		wantState State
		wantFresh Freshness
	}{
		{
			name: "candidate without evidence",
			candidate: Candidate{
				ID:             "claim:candidate",
				RequestedState: StateVerified,
			},
			wantState: StateCandidate,
			wantFresh: FreshnessUnknown,
		},
		{
			name: "supporting evidence",
			candidate: Candidate{
				ID:                    "claim:supported",
				SupportingEvidenceIDs: []string{"evidence:source"},
			},
			wantState: StateSupported,
			wantFresh: FreshnessFresh,
		},
		{
			name: "supporting evidence and passed verification",
			candidate: Candidate{
				ID:                    "claim:verified",
				SupportingEvidenceIDs: []string{"evidence:source"},
				Verifications: []Verification{{
					ID:         "verification:test",
					Result:     VerificationPassed,
					EvidenceID: "evidence:test",
				}},
			},
			wantState: StateVerified,
			wantFresh: FreshnessFresh,
		},
		{
			name: "contradicting evidence overrides support",
			candidate: Candidate{
				ID:                       "claim:contradicted",
				SupportingEvidenceIDs:    []string{"evidence:source"},
				ContradictingEvidenceIDs: []string{"evidence:counterexample"},
			},
			wantState: StateContradicted,
			wantFresh: FreshnessFresh,
		},
		{
			name: "explicit invalidation overrides every positive signal",
			candidate: Candidate{
				ID:                    "claim:stale",
				SupportingEvidenceIDs: []string{"evidence:source"},
				Verifications: []Verification{{
					ID:         "verification:test",
					Result:     VerificationPassed,
					EvidenceID: "evidence:test",
				}},
				StaleReason: "changed_path:src/app.go",
			},
			wantState: StateStale,
			wantFresh: FreshnessStale,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			original := cloneCandidate(tt.candidate)
			got := Compile(tt.candidate)
			if got.State != tt.wantState || got.Freshness != tt.wantFresh {
				t.Fatalf("Compile() = state %q freshness %q, want %q/%q", got.State, got.Freshness, tt.wantState, tt.wantFresh)
			}
			if !reflect.DeepEqual(tt.candidate, original) {
				t.Fatalf("Compile mutated input: got %#v, want %#v", tt.candidate, original)
			}
		})
	}
}

func TestCompileUsesLatestVerificationResultDeterministically(t *testing.T) {
	candidate := Candidate{
		ID:                    "claim:verification-order",
		SupportingEvidenceIDs: []string{"evidence:source"},
		Verifications: []Verification{
			{ID: "verification:new", Result: VerificationPassed, EvidenceID: "evidence:new", ObservedAt: "2026-07-13T10:00:00Z"},
			{ID: "verification:old", Result: VerificationFailed, EvidenceID: "evidence:old", ObservedAt: "2026-07-12T10:00:00Z"},
		},
	}

	forward := Compile(candidate)
	candidate.Verifications[0], candidate.Verifications[1] = candidate.Verifications[1], candidate.Verifications[0]
	reversed := Compile(candidate)
	if forward.State != StateVerified || reversed.State != StateVerified {
		t.Fatalf("state = %q/%q, want deterministic verified state from latest result", forward.State, reversed.State)
	}
	if !reflect.DeepEqual(forward, reversed) {
		t.Fatalf("Compile depends on verification input order:\nforward=%#v\nreversed=%#v", forward, reversed)
	}
}

func TestCanTransitionRejectsUnsupportedPromotionAndStaleRecovery(t *testing.T) {
	allowed := [][2]State{
		{StateCandidate, StateSupported},
		{StateSupported, StateVerified},
		{StateVerified, StateContradicted},
		{StateSupported, StateStale},
	}
	for _, transition := range allowed {
		if !CanTransition(transition[0], transition[1]) {
			t.Errorf("CanTransition(%q, %q) = false, want true", transition[0], transition[1])
		}
	}

	rejected := [][2]State{
		{StateCandidate, StateVerified},
		{StateStale, StateSupported},
		{StateContradicted, StateVerified},
	}
	for _, transition := range rejected {
		if CanTransition(transition[0], transition[1]) {
			t.Errorf("CanTransition(%q, %q) = true, want false", transition[0], transition[1])
		}
	}
}

func TestDeriveReconciliationUsesValidatedSignalsAndKeepsGenericFailuresNonAuthoritative(t *testing.T) {
	tests := []struct {
		name      string
		from      State
		freshness Freshness
		signals   ReconciliationSignals
		wantState State
		wantFresh Freshness
	}{
		{
			name: "passed claim-specific evidence restores stale claim",
			from: StateStale, freshness: FreshnessStale,
			signals:   ReconciliationSignals{SupportingEvidence: true, VerificationResult: VerificationPassed},
			wantState: StateVerified, wantFresh: FreshnessFresh,
		},
		{
			name: "new current basis can replace a contradicted basis",
			from: StateContradicted, freshness: FreshnessFresh,
			signals:   ReconciliationSignals{SupportingEvidence: true, VerificationResult: VerificationPassed},
			wantState: StateVerified, wantFresh: FreshnessFresh,
		},
		{
			name: "supporting evidence without verification is supported",
			from: StateCandidate, freshness: FreshnessUnknown,
			signals:   ReconciliationSignals{SupportingEvidence: true},
			wantState: StateSupported, wantFresh: FreshnessFresh,
		},
		{
			name: "contradicting evidence has precedence",
			from: StateVerified, freshness: FreshnessFresh,
			signals:   ReconciliationSignals{SupportingEvidence: true, ContradictingEvidence: true, VerificationResult: VerificationPassed},
			wantState: StateContradicted, wantFresh: FreshnessFresh,
		},
		{
			name: "generic failed command does not contradict a stale claim",
			from: StateStale, freshness: FreshnessStale,
			signals:   ReconciliationSignals{SupportingEvidence: true, VerificationResult: VerificationFailed},
			wantState: StateStale, wantFresh: FreshnessStale,
		},
		{
			name: "blocked verification cannot promote",
			from: StateStale, freshness: FreshnessStale,
			signals:   ReconciliationSignals{SupportingEvidence: true, VerificationResult: VerificationBlocked},
			wantState: StateStale, wantFresh: FreshnessStale,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got := DeriveReconciliation(tt.from, tt.freshness, tt.signals)
			if got.State != tt.wantState || got.Freshness != tt.wantFresh {
				t.Fatalf("DeriveReconciliation() = %q/%q, want %q/%q", got.State, got.Freshness, tt.wantState, tt.wantFresh)
			}
		})
	}
}

func TestCanReconcileTransitionDoesNotRelaxNormalLifecycle(t *testing.T) {
	for _, transition := range [][2]State{
		{StateStale, StateVerified},
		{StateContradicted, StateVerified},
		{StateVerified, StateSupported},
	} {
		if !CanReconcileTransition(transition[0], transition[1]) {
			t.Errorf("CanReconcileTransition(%q, %q) = false, want true", transition[0], transition[1])
		}
		if CanTransition(transition[0], transition[1]) {
			t.Errorf("CanTransition(%q, %q) = true, dedicated reconciliation must not relax normal lifecycle", transition[0], transition[1])
		}
	}
}

func cloneCandidate(candidate Candidate) Candidate {
	candidate.SupportingEvidenceIDs = append([]string(nil), candidate.SupportingEvidenceIDs...)
	candidate.ContradictingEvidenceIDs = append([]string(nil), candidate.ContradictingEvidenceIDs...)
	candidate.Verifications = append([]Verification(nil), candidate.Verifications...)
	return candidate
}
