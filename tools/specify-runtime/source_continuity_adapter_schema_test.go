package main

import (
	"bytes"
	"strings"
	"testing"
)

func TestAPIPublishesSourceContinuityAdapterPlanCapability(t *testing.T) {
	var stdout, stderr bytes.Buffer
	code := Run([]string{"api", "show", "evidence.source-continuity-adapter-plan", "--format", "json"}, &stdout, &stderr, "test")
	if code != 0 {
		t.Fatalf("api show adapter plan exit=%d stdout=%s stderr=%s", code, stdout.String(), stderr.String())
	}
	capability := requireObject(t, requireObject(t, decodeJSONObject(t, stdout.Bytes()), "data"), "capability")
	for _, field := range []string{"usage", "side_effect", "input_contract", "input_schema"} {
		if value, ok := capability[field].(string); !ok || strings.TrimSpace(value) == "" {
			t.Fatalf("adapter plan capability.%s = %#v", field, capability[field])
		}
	}
	if capability["input_schema"] != "source-continuity-adapter-plan-input" {
		t.Fatalf("adapter plan input schema = %#v", capability["input_schema"])
	}
}

func TestAPISchemaConstrainsSourceContinuityAdapterPlanActionSpace(t *testing.T) {
	var stdout, stderr bytes.Buffer
	code := Run([]string{"api", "schema", "source-continuity-adapter-plan-input", "--format", "json"}, &stdout, &stderr, "test")
	if code != 0 {
		t.Fatalf("api schema adapter plan exit=%d stdout=%s stderr=%s", code, stdout.String(), stderr.String())
	}
	schema := requireObject(t, requireObject(t, decodeJSONObject(t, stdout.Bytes()), "data"), "schema")
	if schema["additionalProperties"] != false {
		t.Fatalf("adapter plan schema must reject undeclared execution fields: %#v", schema)
	}
	properties := requireObject(t, schema, "properties")
	adapters := requireObject(t, properties, "adapters")
	items := requireObject(t, adapters, "items")
	if items["additionalProperties"] != false {
		t.Fatalf("adapter descriptor must reject command/argv/env fields: %#v", items)
	}
	actions := requireObject(t, requireObject(t, items, "properties"), "actions")
	actionItems := requireObject(t, actions, "items")
	actionEnums, ok := actionItems["enum"].([]any)
	if !ok || len(actionEnums) != len(sourceContinuityAdapterActions) {
		t.Fatalf("adapter action enum = %#v", actionItems["enum"])
	}
	for _, forbidden := range []string{"shell-exec", "install", "command", "argv", "env"} {
		for _, value := range actionEnums {
			if value == forbidden {
				t.Fatalf("adapter action schema exposes forbidden action %q", forbidden)
			}
		}
	}
}
