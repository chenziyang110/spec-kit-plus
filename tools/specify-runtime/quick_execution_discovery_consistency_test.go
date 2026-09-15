package main

import (
	"os"
	"reflect"
	"strings"
	"testing"
)

// Full-package tests: execute the actual Run/help/show/pack routes. Do not
// report these as passed after running only the dependency-free helper suite.
func TestQuickOutputDiscoveryConsistency(t *testing.T) {
	root := t.TempDir()
	code, help := quickPackedOutputCLI(t, "quick", "--help", "--project-root", root, "--format", "json")
	contracts, ok := help.Data["output_contracts"].(map[string]any)
	if code != 0 || help.Status != "ok" || !ok || len(contracts) != 4 {
		t.Fatalf("help lacks discovery: code=%d env=%#v", code, help)
	}
	ids := []string{"quick.item-start", "quick.allow-inline", "quick.item-accept", "quick.item-status"}
	for _, includeSchema := range []bool{false, true} {
		args := []string{"api", "pack", "--capabilities", strings.Join(ids, ","), "--project-root", root, "--format", "json"}
		if includeSchema {
			args = append(args, "--include-schema")
		}
		code, pack := quickPackedOutputCLI(t, args...)
		if code != 0 || pack.Status != "ok" || len(pack.Items) != len(ids) {
			t.Fatalf("pack failed: %#v", pack)
		}
		for index, id := range ids {
			code, show := quickPackedOutputCLI(t, "api", "show", id, "--format", "json")
			if code != 0 || show.Status != "ok" {
				t.Fatalf("show %s failed: %#v", id, show)
			}
			descriptor := show.Data["capability"].(map[string]any)
			item := pack.Items[index].(map[string]any)
			if !reflect.DeepEqual(contracts[id], descriptor["output_contract"]) || !reflect.DeepEqual(contracts[id], item["output_contract"]) {
				t.Errorf("help/show/pack differ for %s", id)
			}
			for _, key := range []string{"usage", "input_contract", "side_effect"} {
				if !reflect.DeepEqual(item[key], descriptor[key]) {
					t.Errorf("existing field %s differs for %s", key, id)
				}
			}
		}
	}
	for _, args := range [][]string{{"quick", "-h"}, {"quick", "item-start", "--help"}} {
		code, other := quickPackedOutputCLI(t, append(args, "--project-root", root)...)
		if code != 0 || !reflect.DeepEqual(help.Data, other.Data) {
			t.Fatal("help aliases differ")
		}
	}
	for _, id := range []string{"quick.packet-compile", "quick.preflight", "quick.close", "discussion.checkpoint"} {
		code, show := quickPackedOutputCLI(t, "api", "show", id, "--format", "json")
		if code != 0 {
			t.Fatalf("unsupported-mode descriptor failed: %s", id)
		}
		if _, exists := show.Data["capability"].(map[string]any)["output_contract"]; exists {
			t.Errorf("unexpected compact support: %s", id)
		}
	}
	if entries, err := os.ReadDir(root); err != nil || len(entries) != 0 {
		t.Fatalf("discovery wrote project files: %v %v", entries, err)
	}
}
