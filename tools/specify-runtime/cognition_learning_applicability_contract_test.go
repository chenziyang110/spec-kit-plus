package main

import (
	"bytes"
	"encoding/json"
	"reflect"
	"strings"
	"testing"
)

func TestLearningApplicabilityPublicCapabilityAndFlagSchema(t *testing.T) {
	run := func(args ...string) map[string]any {
		t.Helper()
		var stdout, stderr bytes.Buffer
		if code := Run(args, &stdout, &stderr, "test"); code != 0 {
			t.Fatalf("%v code=%d out=%s err=%s", args, code, stdout.String(), stderr.String())
		}
		return decodeJSONObject(t, stdout.Bytes())
	}
	run("api", "ensure", "--capabilities", "cognition.scope-availability.v2,learning.applicability.v1,do.prepare,do.complete,e2e.task-submit", "--format", "json")
	show := run("api", "show", "learning.applicability.v1", "--format", "json")
	capability := requireObject(t, requireObject(t, show, "data"), "capability")
	if capability["side_effect"] != "read-only" || capability["input_schema"] != "learning-applicability-input" {
		t.Fatalf("wrong Learning capability: %#v", capability)
	}
	command, ok := capability["command"].([]any)
	if !ok || len(command) != 3 || anyString(command[0]) == "" || !reflect.DeepEqual(command[1:], []any{"learning", "start"}) {
		t.Fatalf("semantic capability invented a new command: %#v", capability["command"])
	}
	if !strings.Contains(anyString(capability["input_contract"]), "promotion remains explicit") || !strings.Contains(anyString(capability["output_contract"]), "Legacy/context-missing records degrade") {
		t.Fatalf("applicability/lifecycle boundaries missing: %#v", capability)
	}
	run("api", "schema", "learning-applicability-input", "--format", "json")
	run("api", "pack", "--capabilities", "learning.applicability.v1", "--include-schema", "--format", "json")
	schema := learningApplicabilityInputSchema()
	if schema["additionalProperties"] != false || !reflect.DeepEqual(schema["required"], []string{"component", "sources", "constraints", "evidence_kind"}) {
		t.Fatalf("capture flag schema is not explicit: %#v", schema)
	}
	properties := schema["properties"].(map[string]any)
	for _, name := range []string{"sources", "constraints"} {
		paths := properties[name].(map[string]any)
		if paths["minItems"] != 1 || paths["maxItems"] != 32 || paths["uniqueItems"] != true {
			t.Fatalf("incomplete source declaration %s: %#v", name, paths)
		}
	}
	if _, acceptsCallerHash := properties["source_sha256"]; acceptsCallerHash {
		t.Fatal("capture flag schema accepts caller-produced mechanical proof")
	}
}

func TestRuntimeArgvBindingPreservesCanonicalUIMap(t *testing.T) {
	for _, test := range []struct {
		name string
		ui   map[string]any
		want string
	}{
		{"absent-approval", nil, `{"ui_confirmation":null}`},
		{"explicit-empty-object", map[string]any{}, `{"ui_confirmation":{}}`},
	} {
		t.Run(test.name, func(t *testing.T) {
			canonical := map[string]any{"ui_confirmation": test.ui}
			before, err := json.Marshal(canonical)
			if err != nil {
				t.Fatal(err)
			}
			after, err := json.Marshal(bindRuntimeArgvValue(canonical, "native.exe"))
			if err != nil {
				t.Fatal(err)
			}
			if string(before) != test.want || string(after) != string(before) {
				t.Fatalf("canonical UI value changed: before=%s after=%s want=%s", before, after, test.want)
			}
		})
	}
	canonical := map[string]any{"next_argv": []string{"specify-runtime", "api", "show"}}
	bound := bindRuntimeArgvValue(canonical, "native.exe").(map[string]any)["next_argv"].([]string)
	if bound[0] != "native.exe" || canonical["next_argv"].([]string)[0] != "specify-runtime" {
		t.Fatalf("argv binding either failed or changed canonical input: %#v", bound)
	}
}
