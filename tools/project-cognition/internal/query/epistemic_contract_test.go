package query

import (
	"encoding/json"
	"strings"
	"testing"
)

func TestCompassPublishesEpistemicContractForEveryReadinessState(t *testing.T) {
	t.Run("ready graph", func(t *testing.T) {
		paths := queryTestPaths(t)
		seedCompassModelSwitchGraph(t, paths)

		payload, err := Compass(paths, CompassInput{Intent: "debug", Query: "runtimeOverride"})
		if err != nil {
			t.Fatal(err)
		}
		assertAdvisoryEpistemicContract(t, payload.EpistemicContract)
		assertSerializedEpistemicContract(t, payload)
	})

	t.Run("missing baseline", func(t *testing.T) {
		payload, err := Compass(queryTestPaths(t), CompassInput{Intent: "debug", Query: "runtimeOverride"})
		if err != nil {
			t.Fatal(err)
		}
		assertAdvisoryEpistemicContract(t, payload.EpistemicContract)
		assertSerializedEpistemicContract(t, payload)
	})
}

func TestQueryPublishesEpistemicContractForEveryBaselineKind(t *testing.T) {
	t.Run("missing baseline", func(t *testing.T) {
		payload, err := Run(queryTestPaths(t), QueryInput{Intent: "ask", Query: "where is login handled"})
		if err != nil {
			t.Fatal(err)
		}
		assertAdvisoryEpistemicContract(t, payload.EpistemicContract)
		assertSerializedEpistemicContract(t, payload)
	})

	t.Run("greenfield empty", func(t *testing.T) {
		paths := queryTestPaths(t)
		seedGreenfieldEmptyRuntime(t, paths)

		payload, err := Run(paths, QueryInput{Intent: "plan", Query: "add login"})
		if err != nil {
			t.Fatal(err)
		}
		assertAdvisoryEpistemicContract(t, payload.EpistemicContract)
		assertSerializedEpistemicContract(t, payload)
	})
}

func TestExpandPublishesEpistemicContractForCandidateDataAndMissingBundles(t *testing.T) {
	paths := queryTestPaths(t)

	missing, err := Expand(paths, ExpandInput{ID: "not-an-expansion", Section: "raw_candidates"})
	if err != nil {
		t.Fatal(err)
	}
	assertAdvisoryEpistemicContract(t, missing.EpistemicContract)
	assertSerializedEpistemicContract(t, missing)

	bundleID := "exp-12345678"
	_, err = writeExpansionBundle(paths, ExpansionBundle{
		ID:                            bundleID,
		ClaimRetrievalContractVersion: ClaimRetrievalContractVersion,
		CandidateUniverseVersion:      CandidateUniverseVersion,
		QueryFingerprint:              "12345678",
		SectionPayloads: map[string]any{
			"raw_candidates": []map[string]any{{"id": "candidate-1"}},
		},
	})
	if err != nil {
		t.Fatal(err)
	}

	ready, err := Expand(paths, ExpandInput{ID: bundleID, Section: "raw_candidates"})
	if err != nil {
		t.Fatal(err)
	}
	assertAdvisoryEpistemicContract(t, ready.EpistemicContract)
	assertSerializedEpistemicContract(t, ready)
}

func TestWriteExpansionBundleRequiresCurrentClaimContract(t *testing.T) {
	paths := queryTestPaths(t)
	for _, version := range []int{0, ClaimRetrievalContractVersion - 1, ClaimRetrievalContractVersion + 1} {
		_, err := writeExpansionBundle(paths, ExpansionBundle{
			ID:                            "exp-12345678",
			ClaimRetrievalContractVersion: version,
			CandidateUniverseVersion:      CandidateUniverseVersion,
			QueryFingerprint:              "12345678",
			SectionPayloads:               map[string]any{"raw_candidates": []map[string]any{}},
		})
		if err == nil || !strings.Contains(err.Error(), "claim retrieval contract version") {
			t.Fatalf("writeExpansionBundle(version=%d) error = %v, want current-contract-only rejection", version, err)
		}
	}
}

func assertAdvisoryEpistemicContract(t *testing.T, contract EpistemicContract) {
	t.Helper()
	if contract.ContractVersion != 1 {
		t.Fatalf("ContractVersion = %d, want 1", contract.ContractVersion)
	}
	if contract.GraphRole != "route_candidate_only" {
		t.Fatalf("GraphRole = %q, want route_candidate_only", contract.GraphRole)
	}
	if contract.FactSourceOfTruth != "live_repository" {
		t.Fatalf("FactSourceOfTruth = %q, want live_repository", contract.FactSourceOfTruth)
	}
	if !contract.LiveVerificationRequired {
		t.Fatal("LiveVerificationRequired = false, want true")
	}
	if contract.GraphOnlyClaimsAllowed {
		t.Fatal("GraphOnlyClaimsAllowed = true, want false")
	}
	if contract.UnverifiedClaimAction != "withhold" {
		t.Fatalf("UnverifiedClaimAction = %q, want withhold", contract.UnverifiedClaimAction)
	}
}

func assertSerializedEpistemicContract(t *testing.T, payload any) {
	t.Helper()
	data, err := json.Marshal(payload)
	if err != nil {
		t.Fatal(err)
	}
	var object map[string]any
	if err := json.Unmarshal(data, &object); err != nil {
		t.Fatal(err)
	}
	if _, ok := object["epistemic_contract"]; !ok {
		t.Fatalf("serialized payload missing epistemic_contract: %s", data)
	}
}
