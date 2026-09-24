package main

import (
	"encoding/json"
	"reflect"
	"strings"
	"testing"
)

func TestQuickLazyResponseMatchesEagerProjection(t *testing.T) {
	for _, compact := range []bool{false, true} {
		for _, state := range []string{"confirmed", "inherited", ""} {
			for _, conflict := range []bool{false, true} {
				data := map[string]any{
					"confirmation":   map[string]any{"decision": "unchanged"},
					"packet":         map[string]any{"requires_worker": true},
					"work_claim":     map[string]any{"fence": 4},
					"ready_item_ids": []string{}, "all_accepted": false,
					"future_gate": map[string]any{"blocked": true},
				}
				if conflict {
					data["confirmation_digest"] = "different-existing-binding"
				}
				before, _ := json.Marshal(data)
				pulse := "complete pulse"
				eager := make(map[string]any, len(data)+1)
				for k, v := range data {
					eager[k] = v
				}
				eager["pulse"] = pulse
				if compact {
					eager = compactQuickExecutionData(eager, "confirmation.json", state, "digest")
				}
				calls := 0
				got := quickExecutionResponseData(data, "confirmation.json", state, "digest", compact, func() any {
					calls++
					return pulse
				})
				if !reflect.DeepEqual(got, eager) {
					t.Fatalf("lazy differs from eager: compact=%v state=%q conflict=%v", compact, state, conflict)
				}
				wantCalls := 1
				if compact && state != "" && !conflict {
					wantCalls = 0
				}
				if calls != wantCalls {
					t.Fatalf("pulse calls=%d want=%d", calls, wantCalls)
				}
				after, _ := json.Marshal(data)
				if string(before) != string(after) {
					t.Fatal("presentation mutated its input")
				}
			}
		}
	}
}

func TestQuickLazyPacketOnlyNeverBuildsPulse(t *testing.T) {
	for _, compact := range []bool{false, true} {
		data := map[string]any{"packet": "complete packet", "ready": false}
		got := quickExecutionResponseData(data, "confirmation.json", "confirmed", "digest", compact, func() any {
			t.Fatal("packet-only response must not render a pulse")
			return nil
		})
		if !reflect.DeepEqual(got, data) {
			t.Fatal("packet-only shape changed")
		}
	}
}

func TestQuickLazyFallbackKeepsNullAndExistingPulse(t *testing.T) {
	for _, data := range []map[string]any{
		{"confirmation": nil},
		{"confirmation": map[string]any{}, "response_schema": "future-schema"},
		{"confirmation": map[string]any{}, "confirmation_ref": false},
	} {
		calls := 0
		out := quickExecutionResponseData(data, "confirmation.json", "confirmed", "digest", true, func() any {
			calls++
			return "full pulse"
		})
		if calls != 1 || out["pulse"] != "full pulse" {
			t.Fatal("fallback dropped full context")
		}
	}
	data := map[string]any{"confirmation": map[string]any{}, "pulse": false}
	out := quickExecutionResponseData(data, "confirmation.json", "confirmed", "digest", false, func() any {
		t.Fatal("existing pulse must not be overwritten")
		return nil
	})
	if out["pulse"] != false {
		t.Fatal("lost explicit false pulse")
	}
}

func BenchmarkQuickLazyPulse(b *testing.B) {
	data := map[string]any{"confirmation": map[string]any{"decision": "frozen"}, "requires_worker": true}
	for _, lazy := range []bool{false, true} {
		name := "eager"
		if lazy {
			name = "lazy"
		}
		b.Run(name, func(b *testing.B) {
			// Synthetic pulse cost, not a real workflow or model billing benchmark.
			calls := 0
			build := func() any {
				calls++
				return strings.Repeat("Q item: pending; acceptance unchanged\n", 100)
			}
			b.ReportAllocs()
			for i := 0; i < b.N; i++ {
				var out map[string]any
				if lazy {
					out = quickExecutionResponseData(data, "confirmation.json", "confirmed", "digest", true, build)
				} else {
					full := map[string]any{"confirmation": data["confirmation"], "requires_worker": true, "pulse": build()}
					out = compactQuickExecutionData(full, "confirmation.json", "confirmed", "digest")
				}
				if out["requires_worker"] != true {
					b.Fatal("lost worker gate")
				}
			}
			b.ReportMetric(float64(calls)/float64(b.N), "pulse-builds/op")
		})
	}
}
