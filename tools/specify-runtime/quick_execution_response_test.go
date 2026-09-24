package main

import (
	"encoding/json"
	"fmt"
	"reflect"
	"strings"
	"testing"
)

const quickCompactTestRef = ".planning/quick/260914-001-optimize/confirmation.json"

// Synthetic execution data for a reproducible payload-size experiment, not a
// model trace, a canonical workflow fixture, or a claim about billed tokens.
func quickCompactTestData(items int) map[string]any {
	rows := make([]any, 0, items)
	ready := make([]string, 0, items)
	for i := 1; i <= items; i++ {
		id := fmt.Sprintf("Q%03d", i)
		rows = append(rows, map[string]any{
			"id": id, "deliverable": "implement the bounded outcome without changing public behavior",
			"acceptance":  "targeted checks pass and required evidence is preserved",
			"write_scope": []string{fmt.Sprintf("src/module%d.go", i)},
			"depends_on":  []string{},
		})
		ready = append(ready, id)
	}
	return map[string]any{
		"task":         map[string]any{"id": "260914-001", "workspace": "260914-001-optimize"},
		"work_item_id": "Q001",
		"confirmation": map[string]any{
			"confirmation_state": "confirmed", "confirmation_digest": strings.Repeat("a", 64),
			"decision": map[string]any{"goal": "deliver confirmed scope", "items": rows},
		},
		"pulse":       map[string]any{"items": rows},
		"packet":      map[string]any{"work_item_id": "Q001", "write_scope": []string{"src/module1.go"}},
		"packet_path": ".planning/quick/260914-001-optimize/packets/Q001.json",
		"work_claim":  map[string]any{"work_id": "W1", "fence": 3, "claim_state": "claimed"},
		"ready_item_ids": ready, "blocked_item_ids": []string{"Q999"}, "active_item_ids": []string{"Q001"},
		"requires_worker": true, "all_accepted": false,
		"worker_proof":       map[string]any{"mode": "worker", "result_path": "worker-results/Q001.json"},
		"blockers":           []string{"required upstream evidence pending"},
		"next_action":        "submit the worker result before accepting the item",
		"future_safety_gate": map[string]any{"permission": "do-not-widen"},
	}
}

func TestQuickCompactPreservesNonduplicateFields(t *testing.T) {
	data := quickCompactTestData(10)
	before, err := json.Marshal(data)
	if err != nil {
		t.Fatal(err)
	}
	out := compactQuickExecutionData(data, quickCompactTestRef, "confirmed", strings.Repeat("a", 64))
	for key, want := range data {
		if key == "confirmation" || key == "pulse" {
			if _, ok := out[key]; ok {
				t.Fatalf("duplicate context retained: %s", key)
			}
			continue
		}
		if !reflect.DeepEqual(out[key], want) {
			t.Errorf("changed required field %s", key)
		}
	}
	if out["response_schema"] != "quick-execution-compact-v1" ||
		out["confirmation_ref"] != quickCompactTestRef ||
		out["confirmation_state"] != "confirmed" ||
		out["confirmation_digest"] != strings.Repeat("a", 64) {
		t.Fatalf("missing decision binding: %#v", out)
	}
	after, err := json.Marshal(data)
	if err != nil {
		t.Fatal(err)
	}
	if string(before) != string(after) {
		t.Fatal("projection modified its input")
	}
	out["requires_worker"] = false
	if data["requires_worker"] != true {
		t.Fatal("projection aliases the input map")
	}
}

func TestQuickCompactFailsOpenToFullContextWhenBindingMissing(t *testing.T) {
	for _, tc := range []struct{ name, ref, state, digest string }{
		{"missing ref", "", "confirmed", "digest"},
		{"missing state", quickCompactTestRef, "", "digest"},
		{"missing digest", quickCompactTestRef, "confirmed", ""},
	} {
		t.Run(tc.name, func(t *testing.T) {
			data := quickCompactTestData(1)
			if got := compactQuickExecutionData(data, tc.ref, tc.state, tc.digest); !reflect.DeepEqual(got, data) {
				t.Fatal("discarded context without a replacement binding")
			}
		})
	}
	for _, data := range []map[string]any{nil, {"packet": "keep-full", "ready": false}} {
		if got := compactQuickExecutionData(data, quickCompactTestRef, "confirmed", "digest"); !reflect.DeepEqual(got, data) {
			t.Fatal("changed response without confirmation context")
		}
	}
}

func TestQuickCompactRetainsFalseAndBlockedValues(t *testing.T) {
	data := quickCompactTestData(1)
	data["requires_worker"] = false
	data["ready"] = false
	data["inline_reason"] = "spawn_failed: actual dispatch unavailable"
	out := compactQuickExecutionData(data, quickCompactTestRef, "inherited", "digest")
	for _, key := range []string{"requires_worker", "ready", "all_accepted", "inline_reason", "blockers", "blocked_item_ids"} {
		if got, ok := out[key]; !ok || !reflect.DeepEqual(got, data[key]) {
			t.Fatalf("lost %s", key)
		}
	}
}

func TestQuickCompactResponseSize(t *testing.T) {
	for _, count := range []int{1, 10, 100} {
		t.Run(fmt.Sprintf("items_%d", count), func(t *testing.T) {
			data := quickCompactTestData(count)
			full, err := json.Marshal(data)
			if err != nil {
				t.Fatal(err)
			}
			compact, err := json.Marshal(compactQuickExecutionData(data, quickCompactTestRef, "confirmed", strings.Repeat("a", 64)))
			if err != nil {
				t.Fatal(err)
			}
			if len(compact) >= len(full) {
				t.Fatalf("response grew: %d >= %d", len(compact), len(full))
			}
			t.Logf("synthetic data only: full_bytes=%d compact_bytes=%d reduction=%.2f%%", len(full), len(compact), 100*(1-float64(len(compact))/float64(len(full))))
		})
	}
}

func BenchmarkQuickExecutionResponse(b *testing.B) {
	for _, count := range []int{1, 10, 100} {
		data := quickCompactTestData(count)
		for _, compact := range []bool{false, true} {
			b.Run(fmt.Sprintf("items_%d/compact_%t", count, compact), func(b *testing.B) {
				var encoded []byte
				var err error
				b.ReportAllocs()
				for i := 0; i < b.N; i++ {
					out := data
					if compact {
						out = compactQuickExecutionData(data, quickCompactTestRef, "confirmed", strings.Repeat("a", 64))
					}
					encoded, err = json.Marshal(out)
					if err != nil {
						b.Fatal(err)
					}
				}
				b.ReportMetric(float64(len(encoded)), "response-bytes/op")
			})
		}
	}
}
