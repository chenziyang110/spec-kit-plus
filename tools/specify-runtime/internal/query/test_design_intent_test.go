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

func testDesignAnySliceContains(values []any, want string) bool {
	for _, value := range values {
		if value == want {
			return true
		}
	}
	return false
}

