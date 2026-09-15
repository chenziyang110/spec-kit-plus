package main

import (
	"encoding/json"
	"reflect"
	"strings"
	"testing"
)

func TestQuickOutputPackContractDenominator(t *testing.T) {
	for _, mode := range []string{"item-start", "allow-inline", "item-accept", "item-status", "packet-compile", "close", "preflight", "checkpoint-confirm", "status", "unknown"} {
		t.Run(mode, func(t *testing.T) {
			contract := quickCompactOutputContract("quick." + mode)
			want := mode == "item-start" || mode == "allow-inline" || mode == "item-accept" || mode == "item-status"
			if (contract != nil) != want {
				t.Fatalf("contract=%#v want support=%v", contract, want)
			}
			if !want {
				return
			}
			if contract["default"] != "full" || contract["fallback"] != "full" || contract["requires_full_intake"] != true || contract["mutates_canonical_state"] != false {
				t.Fatalf("lost presentation boundary: %#v", contract)
			}
			if !strings.Contains(contract["compact_usage"].(string), "quick "+mode+" <quick-id>") || !strings.Contains(contract["compact_usage"].(string), "[--compact]") {
				t.Fatal("missing usable mode-specific discovery")
			}
			if strings.Contains(contract["full_context_usage"].(string), "--compact") || !strings.Contains(contract["full_context_usage"].(string), "quick item-status") {
				t.Fatal("context refresh must use the non-mutating full status route")
			}
			projected := compactQuickExecutionData(map[string]any{"confirmation": "fixture"}, "confirmation.json", "confirmed", "decision")
			if contract["response_schema"] != projected["response_schema"] {
				t.Fatal("discovery and producer schema disagree")
			}
		})
	}
	for _, id := range []string{"implement.item-start", "Quick.item-start", "quick.Item-start", "quick.item-status.extra", "item-start", ""} {
		if quickCompactOutputContract(id) != nil {
			t.Errorf("advertised unsupported capability %q", id)
		}
	}
}

func TestQuickOutputPackPreservesOwningDescriptor(t *testing.T) {
	for _, id := range []string{"quick.item-start", "quick.item-status", "quick.close", "workflow.block"} {
		for _, upstream := range []map[string]any{
			{}, {"output_contract": nil}, {"output_contract": "future-contract"},
			{"output_contract": map[string]any{"version": 99}},
		} {
			before, _ := json.Marshal(upstream)
			item := map[string]any{"id": id, "usage": "original usage", "input_contract": "must keep fenced Work", "side_effect": "original side effect"}
			addQuickPackOutputContract(id, upstream, item)
			after, _ := json.Marshal(upstream)
			if string(before) != string(after) {
				t.Fatal("mutated descriptor")
			}
			if contract, exists := upstream["output_contract"]; exists && !reflect.DeepEqual(contract, item["output_contract"]) {
				t.Fatal("overwrote owning output contract")
			}
			if item["usage"] != "original usage" || item["input_contract"] != "must keep fenced Work" || item["side_effect"] != "original side effect" {
				t.Fatal("changed an existing capability field")
			}
			addQuickPackOutputContract(id, map[string]any{"output_contract": "replacement"}, item)
			if item["output_contract"] == "replacement" {
				// Only an item with no original contract may be filled on replay.
				if _, exists := upstream["output_contract"]; exists || quickCompactOutputContract(id) != nil {
					t.Fatal("replay overwrote metadata")
				}
			}
		}
	}
	addQuickPackOutputContract("quick.item-start", nil, nil)
}

func TestQuickOutputContractFreshCollections(t *testing.T) {
	one := quickCompactOutputContract("quick.item-start")
	one["default"] = "changed"
	one["omitted_fields"].([]string)[0] = "work_claim"
	two := quickCompactOutputContract("quick.item-start")
	if two["default"] != "full" || !reflect.DeepEqual(two["omitted_fields"], []string{"confirmation", "pulse"}) {
		t.Fatal("discovery shares mutable state")
	}
}

func TestQuickOutputParseExecutionOption(t *testing.T) {
	cases := []struct {
		name, mode string
		args       []string
		want       bool
		wantError  bool
	}{
		{"default", "item-start", nil, false, false},
		{"standalone", "item-start", []string{"item-start", "id", "--item", "Q1", "--compact"}, true, false},
		{"leading", "item-status", []string{"--compact", "item-status", "id"}, true, false},
		{"normalized-mode", " ITEM-ACCEPT ", []string{"--compact"}, true, false},
		{"duplicate", "item-start", []string{"--compact", "--item", "Q1", "--compact"}, false, true},
		{"equals-false", "item-start", []string{"--compact=false"}, false, true},
		{"equals-true", "item-status", []string{"--compact=true"}, false, true},
		{"equals-empty", "item-status", []string{"--compact="}, false, true},
		{"packet-compatible-full", "packet-compile", []string{"--compact"}, false, false},
		{"packet-invalid", "packet-compile", []string{"--compact=false"}, false, true},
		{"packet-duplicate", "packet-compile", []string{"--compact", "--compact"}, false, true},
		{"internal-unsupported-mode", "close", []string{"--compact"}, false, true},
		{"ordinary-text", "item-accept", []string{"--evidence", "literal --compact in evidence"}, false, false},
		{"literal-plus-flag", "item-accept", []string{"--evidence", "--compact", "--compact"}, true, false},
		{"literal-equals", "allow-inline", []string{"--reason", "--compact=false"}, false, false},
		{"other-required-field-owned-elsewhere", "item-start", []string{"--item"}, false, false},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			before := append([]string(nil), tc.args...)
			got, err := parseQuickExecutionCompactOption(tc.mode, tc.args)
			if got != tc.want || (err != nil) != tc.wantError {
				t.Fatalf("got (%v,%v), want (%v,error=%v)", got, err, tc.want, tc.wantError)
			}
			if !reflect.DeepEqual(before, tc.args) {
				t.Fatal("mutated caller arguments")
			}
		})
	}
	for _, option := range []string{"--project-root", "--format", "--item", "--current-work-id", "--current-work-fence", "--reason", "--evidence", "--input-json", "--digest", "--view", "--status", "--result-state", "--evidence-json", "--update-id", "--slug", "--intent", "--summary", "--phase", "--decision", "--recommendation", "--mode", "--input", "--review-digest", "--expected-state-sha256", "--feature-dir", "--surface", "--record-id", "--expected-sha256", "--limit"} {
		t.Run("literal-value/"+option, func(t *testing.T) {
			got, err := parseQuickExecutionCompactOption("item-status", []string{option, "--compact"})
			if got || err != nil {
				t.Fatalf("option value treated as flag: (%v,%v)", got, err)
			}
		})
	}
}

func FuzzQuickOutputLiteralValues(f *testing.F) {
	for _, value := range []string{"--compact", "--compact=false", "", "证据", "--compact\n--compact"} {
		f.Add(value)
	}
	f.Fuzz(func(t *testing.T, value string) {
		for _, option := range []string{"--evidence", "--reason", "--project-root"} {
			got, err := parseQuickExecutionCompactOption("item-accept", []string{option, value})
			if got || err != nil {
				t.Fatalf("literal value changed presentation: %q (%v,%v)", value, got, err)
			}
			got, err = parseQuickExecutionCompactOption("item-accept", []string{option, value, "--compact"})
			if !got || err != nil {
				t.Fatalf("literal value masked a real flag: %q (%v,%v)", value, got, err)
			}
		}
	})
}
