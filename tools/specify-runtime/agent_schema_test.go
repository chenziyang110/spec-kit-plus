package main

import (
	"bytes"
	"testing"
)

func TestAPISchemaExpandsWorkflowBlockInputContract(t *testing.T) {
	var stdout, stderr bytes.Buffer
	code := Run(
		[]string{"api", "schema", "workflow-block-input", "--format", "json"},
		&stdout,
		&stderr,
		"test",
	)
	if code != 0 {
		t.Fatalf("api schema exit code = %d; stdout=%s stderr=%s", code, stdout.String(), stderr.String())
	}
	payload := decodeJSONObject(t, stdout.Bytes())
	data := requireObject(t, payload, "data")
	schema := requireObject(t, data, "schema")
	properties := requireObject(t, schema, "properties")
	humanActionRequired := requireObject(t, properties, "human_action_required")
	types, ok := humanActionRequired["type"].([]any)
	if !ok || len(types) != 2 || types[0] != "boolean" || types[1] != "null" {
		t.Fatalf("human_action_required type = %#v, want [boolean null]", humanActionRequired["type"])
	}
	required, ok := schema["required"].([]any)
	if !ok || len(required) != 10 {
		t.Fatalf("workflow block required fields = %#v, want 10 fields", schema["required"])
	}
	if show := requireStringArray(t, payload, "show_argv"); len(show) < 4 || show[1] != "api" || show[2] != "show" {
		t.Fatalf("schema show_argv = %#v, want runtime capability expansion", show)
	}
}

func TestAPISchemaRejectsUnknownSchema(t *testing.T) {
	var stdout, stderr bytes.Buffer
	code := Run([]string{"api", "schema", "missing", "--format", "json"}, &stdout, &stderr, "test")
	if code != 2 {
		t.Fatalf("unknown api schema exit code = %d, want 2; stdout=%s", code, stdout.String())
	}
	payload := decodeJSONObject(t, stdout.Bytes())
	if payload["status"] != "usage-error" {
		t.Fatalf("unknown api schema status = %#v, want usage-error", payload["status"])
	}
}
