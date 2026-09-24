package main

import (
	"encoding/json"
	"reflect"
	"testing"
)

func TestQuickCompactPreservesExistingBindingConflicts(t *testing.T) {
	for _, key := range []string{"response_schema", "confirmation_ref", "confirmation_state", "confirmation_digest"} {
		t.Run(key, func(t *testing.T) {
			data := map[string]any{"confirmation": map[string]any{"keep": true}, "pulse": "keep", key: "different-contract"}
			before, _ := json.Marshal(data)
			out := compactQuickExecutionData(data, "confirmation.json", "confirmed", "digest")
			after, _ := json.Marshal(out)
			if string(before) != string(after) {
				t.Fatal("presentation overwrote an existing binding instead of retaining full context")
			}
		})
	}
}

func TestQuickCompactRejectsBlankOrNullReplacement(t *testing.T) {
	for _, tc := range []struct{ ref, state, digest string }{
		{" \t", "confirmed", "digest"}, {"confirmation.json", "\n", "digest"}, {"confirmation.json", "confirmed", " "},
	} {
		data := map[string]any{"confirmation": map[string]any{"keep": true}, "pulse": "keep"}
		if got := compactQuickExecutionData(data, tc.ref, tc.state, tc.digest); !reflect.DeepEqual(got, data) {
			t.Fatal("blank binding discarded context")
		}
	}
	data := map[string]any{"confirmation": nil, "pulse": "keep"}
	if got := compactQuickExecutionData(data, "confirmation.json", "confirmed", "digest"); !reflect.DeepEqual(got, data) {
		t.Fatal("null confirmation acquired a compact binding")
	}
}

func TestQuickCompactMatchingBindingsAndIdempotence(t *testing.T) {
	data := map[string]any{
		"confirmation": map[string]any{"keep": true}, "pulse": "duplicate",
		"confirmation_ref": "confirmation.json", "confirmation_state": "confirmed", "confirmation_digest": "digest",
		"response_schema": "quick-execution-compact-v1", "requires_worker": false, "blockers": []any{},
	}
	out := compactQuickExecutionData(data, "confirmation.json", "confirmed", "digest")
	if _, ok := out["confirmation"]; ok {
		t.Fatal("compatible bindings prevented compaction")
	}
	if got := compactQuickExecutionData(out, "confirmation.json", "confirmed", "digest"); !reflect.DeepEqual(got, out) {
		t.Fatal("projection is not idempotent")
	}
	if _, ok := data["confirmation"]; !ok {
		t.Fatal("projection mutated canonical input")
	}
}

func FuzzQuickCompactRetainsNonduplicateFields(f *testing.F) {
	for _, seed := range []string{
		`{"confirmation":{},"pulse":{},"requires_worker":false,"blockers":[]}`,
		`{"confirmation":{},"confirmation_digest":"conflict","future_gate":{"denied":true}}`,
		`{"confirmation":null,"pulse":"retain"}`,
		`{"confirmation":{},"response_schema":{"unexpected":"shape"}}`,
	} {
		f.Add(seed)
	}
	f.Fuzz(func(t *testing.T, text string) {
		var data map[string]any
		if err := json.Unmarshal([]byte(text), &data); err != nil || data == nil {
			return
		}
		before, err := json.Marshal(data)
		if err != nil {
			t.Fatal(err)
		}
		out := compactQuickExecutionData(data, "confirmation.json", "confirmed", "digest")
		for key, value := range data {
			if key == "confirmation" || key == "pulse" {
				continue
			}
			got, exists := out[key]
			if !exists || !reflect.DeepEqual(got, value) {
				t.Fatalf("presentation changed nonduplicate field %s", key)
			}
		}
		after, _ := json.Marshal(data)
		if string(before) != string(after) {
			t.Fatal("presentation mutated its input")
		}
	})
}
