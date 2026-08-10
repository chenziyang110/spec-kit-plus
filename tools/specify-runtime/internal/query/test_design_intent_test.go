package query

import (
	"encoding/json"
	"testing"
)

func TestCompassPublishesTestDesignLiveReadProfile(t *testing.T) {
	payload, err := Compass(queryTestPaths(t), CompassInput{
		Intent: "test_design",
		Query:  "Build comprehensive approval tests and the required data pack",
	})
	if err != nil {
		t.Fatal(err)
	}
	raw, err := json.Marshal(payload)
	if err != nil {
		t.Fatal(err)
	}
	var result map[string]any
	if err := json.Unmarshal(raw, &result); err != nil {
		t.Fatal(err)
	}
	if result["intent_profile"] != "test_design" {
		t.Fatalf("intent_profile=%#v, want test_design", result["intent_profile"])
	}
	focus, _ := result["required_live_read_surfaces"].([]any)
	for _, want := range []string{"requirements", "entrypoints", "test-infrastructure", "fixtures", "verification-routes", "risk-history"} {
		if !testDesignAnySliceContains(focus, want) {
			t.Fatalf("required_live_read_surfaces=%#v, missing %q", focus, want)
		}
	}
}

func TestTestDesignIntentAliasesShareFingerprintAndExpandCandidateTerms(t *testing.T) {
	left := CompassInput{Intent: "test-design", Query: "Build the approval data pack"}
	right := CompassInput{Intent: "test_design", Query: "Build the approval data pack"}
	if compassFingerprint(left) != compassFingerprint(right) {
		t.Fatalf("alias fingerprints differ: %q != %q", compassFingerprint(left), compassFingerprint(right))
	}
	terms := compassCandidateTerms(left, termsFrom(left.Intent+" "+left.Query, 30), nil)
	for _, want := range []string{"test", "verification", "fixture", "harness", "ci", "entrypoint", "regression", "security", "performance", "history"} {
		if !testDesignStringSliceContains(terms, want) {
			t.Fatalf("candidate terms=%#v, missing %q", terms, want)
		}
	}
}

func testDesignAnySliceContains(values []any, want string) bool {
	for _, value := range values {
		if value == want {
			return true
		}
	}
	return false
}

func testDesignStringSliceContains(values []string, want string) bool {
	for _, value := range values {
		if value == want {
			return true
		}
	}
	return false
}
