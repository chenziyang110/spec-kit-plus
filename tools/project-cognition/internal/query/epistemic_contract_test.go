package query

import (
	"encoding/json"
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
