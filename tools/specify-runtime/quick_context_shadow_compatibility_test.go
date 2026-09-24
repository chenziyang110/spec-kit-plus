package main

import (
	"bytes"
	"encoding/json"
	"io"
	"reflect"
	"strings"
	"testing"
)

// These tests use the production Run entrypoint and existing Quick owners.
// Describing a modifying capability must never perform that modification.
func decodeShadowCompatibilityEnvelope(t *testing.T, raw []byte) Envelope {
	t.Helper()
	decoder := json.NewDecoder(bytes.NewReader(raw))
	decoder.UseNumber()
	var env Envelope
	if err := decoder.Decode(&env); err != nil {
		t.Fatal("invalid compatibility envelope", err)
	}
	if err := decoder.Decode(new(any)); err != io.EOF {
		t.Fatal("more than one compatibility response", err)
	}
	return env
}

func TestQuickShadowCompatibilityPreservesWholeLegacyHelp(t *testing.T) {
	for _, flag := range []string{"--help", "-h"} {
		t.Run(flag, func(t *testing.T) {
			var legacy, current, stderr bytes.Buffer
			args := []string{flag}
			if runQuick(args, &legacy) != 0 || Run(append([]string{"quick"}, args...), &current, &stderr, "test") != 0 {
				t.Fatal("help command failed", stderr.String())
			}
			want := decodeShadowCompatibilityEnvelope(t, legacy.Bytes())
			got := decodeShadowCompatibilityEnvelope(t, current.Bytes())
			shadow, ok := got.Data["context_shadow"].(map[string]any)
			if !ok || shadow["usage"] != quickShadowCommandUsage {
				t.Fatal("missing additive diagnostic help")
			}
			delete(got.Data, "context_shadow")
			commands, ok := got.Data["commands"].([]any)
			if !ok {
				t.Fatal("commands are not an array")
			}
			var retained []any
			added := 0
			for _, command := range commands {
				if command == "context-shadow" {
					added++
				} else {
					retained = append(retained, command)
				}
			}
			if added != 1 {
				t.Fatalf("expected one new command, got %d", added)
			}
			got.Data["commands"] = retained
			if !reflect.DeepEqual(got, want) {
				t.Fatal("adding diagnostic help changed an existing envelope field or contract")
			}
		})
	}
}

func TestQuickShadowCompatibilityMixedPackRetainsEveryOwnerContract(t *testing.T) {
	ids := []string{"api.ensure", "quick.item-start", "quick.item-accept"}
	for position := 0; position <= len(ids); position++ {
		selection := append([]string{}, ids[:position]...)
		selection = append(selection, quickShadowCapability)
		selection = append(selection, ids[position:]...)
		_, packed := runQuickShadowEntry(t, "api", "pack", "--capabilities", strings.Join(selection, ","), "--format", "json")
		if packed.Status != "ok" || len(packed.Items) != len(selection) || len(packed.NextArgv) != 0 {
			t.Fatal("mixed capability request failed or advertised work", packed)
		}
		for index, id := range selection {
			_, shown := runQuickShadowEntry(t, "api", "show", id, "--format", "json")
			owner := shown.Data["capability"].(map[string]any)
			item := packed.Items[index].(map[string]any)
			if item["id"] != id {
				t.Fatal("capability selection order changed")
			}
			for _, field := range []string{"id", "summary", "command", "usage", "side_effect", "input_contract", "output_contract", "execution_contract"} {
				value, present := owner[field]
				actual, included := item[field]
				if present != included || !reflect.DeepEqual(value, actual) {
					t.Fatalf("capability %s lost or gained field %s in compact discovery", id, field)
				}
			}
			if id == "quick.item-start" {
				contract := item["execution_contract"].(map[string]any)
				if contract["default"] != "worker" || contract["result_submit_required"] != true || contract["independent_review_not_waived"] != true {
					t.Fatal("diagnostic discovery weakened the modifying executor contract")
				}
			}
		}
	}
}

func TestQuickShadowCompatibilityDiscoveryDoesNotChangeOwnerFiles(t *testing.T) {
	service, doc := shadowTestRepo(t)
	before := shadowTestFiles(t, service.projectRoot)
	commands := [][]string{
		{"quick", "--help", "--project-root", service.projectRoot},
		{"api", "ensure", "--capabilities", "quick.item-start," + quickShadowCapability, "--project-root", service.projectRoot},
		{"api", "pack", "--capabilities", quickShadowCapability + ",quick.item-start", "--project-root", service.projectRoot},
		{"api", "show", "quick.item-start"},
		{"quick", "context-shadow", "--workspace", doc.Workspace, "--item", "Q1", "--project-root", service.projectRoot},
	}
	for _, args := range commands {
		code, env := runQuickShadowEntry(t, args...)
		if code != 0 || len(env.NextArgv) != 0 {
			t.Fatal("read-only inspection failed or requested execution", args, env)
		}
		if !reflect.DeepEqual(before, shadowTestFiles(t, service.projectRoot)) {
			t.Fatal("inspection changed project/Git files", args)
		}
	}
}
