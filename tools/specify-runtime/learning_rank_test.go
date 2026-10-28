package main

import "testing"

func TestLearningApplicabilityRankingCannotOverrideNegativeEvidence(t *testing.T) {
	cards := []map[string]any{
		{"ref": "high-recurrence-conflict", "status": "confirmed", "signal": "high", "occurrences": 1000, "applicability": map[string]any{"state": "rejected"}, "context_match": map[string]any{"exact_operation_owner": true, "matched_dimensions": 7}},
		{"ref": "unknown-legacy", "status": "confirmed", "signal": "high", "occurrences": 20, "applicability": map[string]any{"state": "degraded"}},
		{"ref": "current-candidate", "status": "candidate", "signal": "medium", "occurrences": 1, "applicability": map[string]any{"state": "applicable"}},
	}
	sortLearningCards(cards)
	if cards[0]["ref"] != "current-candidate" || cards[1]["ref"] != "unknown-legacy" || cards[2]["ref"] != "high-recurrence-conflict" {
		t.Fatalf("positive ranking facets overrode applicability: %#v", cards)
	}
}
