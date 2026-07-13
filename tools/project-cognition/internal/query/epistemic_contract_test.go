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
	if contract.Version != 1 {
		t.Fatalf("Version = %d, want 1", contract.Version)
	}
	if contract.GraphRole != "advisory_navigation" {
		t.Fatalf("GraphRole = %q, want advisory_navigation", contract.GraphRole)
	}
	if contract.FactAuthority != "live_repository_evidence" {
		t.Fatalf("FactAuthority = %q, want live_repository_evidence", contract.FactAuthority)
	}
	if contract.ReturnedContentStatus != "route_candidates" {
		t.Fatalf("ReturnedContentStatus = %q, want route_candidates", contract.ReturnedContentStatus)
	}
	if !contract.LiveEvidenceRequired {
		t.Fatal("LiveEvidenceRequired = false, want true")
	}
	wantProhibited := []string{
		"current_behavior_claim",
		"root_cause_claim",
		"fixed_claim",
		"completed_claim",
		"release_safe",
	}
	if !equalStrings(contract.ProhibitedClaims, wantProhibited) {
		t.Fatalf("ProhibitedClaims = %#v, want %#v", contract.ProhibitedClaims, wantProhibited)
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
