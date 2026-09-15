package main

import (
	"encoding/json"
	"reflect"
	"testing"
)

func TestQuickHelpOutputContracts(t *testing.T) {
	commands := []string{"list", "preflight", "item-start", "allow-inline", "item-accept", "item-status", "packet-compile"}
	data := map[string]any{"commands": commands, "item_start_requires": "existing Work claim gate"}
	addQuickHelpOutputContracts(data)
	contracts, ok := data["output_contracts"].(map[string]any)
	if !ok || len(contracts) != 4 {
		t.Fatalf("unexpected supported operations: %#v", data)
	}
	for _, command := range commands {
		id := "quick." + command
		contract, exists := contracts[id]
		want := quickCompactOutputContract(id)
		if exists != (want != nil) || (exists && !reflect.DeepEqual(contract, want)) {
			t.Errorf("help differs from canonical contract for %s", id)
		}
	}
	if data["item_start_requires"] != "existing Work claim gate" || !reflect.DeepEqual(data["commands"], commands) {
		t.Fatal("changed existing help fields")
	}
	// Editing one response must not affect another response or the producer.
	contracts["quick.item-start"].(map[string]any)["omitted_fields"].([]string)[0] = "work_claim"
	other := map[string]any{"commands": commands}
	addQuickHelpOutputContracts(other)
	if !reflect.DeepEqual(other["output_contracts"].(map[string]any)["quick.item-start"], quickCompactOutputContract("quick.item-start")) {
		t.Fatal("help shares mutable output contracts")
	}
}

func TestQuickHelpOutputPreservesOwnerAndMalformedInput(t *testing.T) {
	for _, data := range []map[string]any{
		nil, {}, {"commands": "item-start"}, {"commands": []string{"packet-compile"}},
		{"commands": []string{"item-start"}, "output_contracts": nil},
		{"commands": []string{"item-start"}, "output_contracts": "owner contract"},
	} {
		before, _ := json.Marshal(data)
		addQuickHelpOutputContracts(data)
		after, _ := json.Marshal(data)
		if string(before) != string(after) {
			t.Errorf("unexpected mutation: before=%s after=%s", before, after)
		}
	}
	data := map[string]any{"commands": []string{"item-status", "item-status", "unknown"}}
	addQuickHelpOutputContracts(data)
	if len(data["output_contracts"].(map[string]any)) != 1 {
		t.Fatal("duplicate or unsupported command advertised")
	}
	before, _ := json.Marshal(data)
	addQuickHelpOutputContracts(data)
	after, _ := json.Marshal(data)
	if string(before) != string(after) {
		t.Fatal("help enrichment is not idempotent")
	}
}

func TestQuickShowOutputSupportsSameMapWithoutOverwrite(t *testing.T) {
	for _, id := range []string{"quick.item-start", "quick.item-status", "quick.packet-compile", "discussion.checkpoint"} {
		for _, existing := range []map[string]any{{}, {"output_contract": nil}, {"output_contract": "owner contract"}} {
			descriptor := map[string]any{"id": id, "usage": "existing usage", "input_contract": "existing input", "side_effect": "existing effect"}
			for key, value := range existing {
				descriptor[key] = value
			}
			addQuickPackOutputContract(id, descriptor, descriptor)
			contract, found := descriptor["output_contract"]
			if owner, exists := existing["output_contract"]; exists {
				if !found || !reflect.DeepEqual(contract, owner) {
					t.Fatal("owner contract overwritten")
				}
			} else if want := quickCompactOutputContract(id); (want != nil) != found || (found && !reflect.DeepEqual(want, contract)) {
				t.Fatalf("show contract mismatch for %s", id)
			}
			if descriptor["usage"] != "existing usage" || descriptor["input_contract"] != "existing input" || descriptor["side_effect"] != "existing effect" {
				t.Fatal("descriptor fields changed")
			}
			packed := map[string]any{"id": id}
			addQuickPackOutputContract(id, descriptor, packed)
			if !reflect.DeepEqual(packed["output_contract"], descriptor["output_contract"]) {
				t.Fatal("pack/show drift")
			}
		}
	}
}
