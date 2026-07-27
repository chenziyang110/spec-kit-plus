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

func TestAPIShowExpandsEveryAdvertisedCapability(t *testing.T) {
	for _, capabilityID := range defaultCapabilities() {
		t.Run(capabilityID, func(t *testing.T) {
			var stdout, stderr bytes.Buffer
			code := Run([]string{"api", "show", capabilityID, "--format", "json"}, &stdout, &stderr, "test")
			if code != 0 {
				t.Fatalf("api show %s exit code = %d; stdout=%s stderr=%s", capabilityID, code, stdout.String(), stderr.String())
			}
			payload := decodeJSONObject(t, stdout.Bytes())
			capability := requireObject(t, requireObject(t, payload, "data"), "capability")
			if capability["id"] != capabilityID {
				t.Fatalf("api show %s capability = %#v", capabilityID, capability)
			}
		})
	}
}

func TestAPIShowArtifactScaffoldPublishesSchemaAndCatalogRoute(t *testing.T) {
	var stdout, stderr bytes.Buffer
	code := Run([]string{"api", "show", "--id", "artifact.scaffold", "--format", "json"}, &stdout, &stderr, "test")
	if code != 0 {
		t.Fatalf("api show artifact.scaffold exit code = %d; stdout=%s stderr=%s", code, stdout.String(), stderr.String())
	}
	payload := decodeJSONObject(t, stdout.Bytes())
	capability := requireObject(t, requireObject(t, payload, "data"), "capability")
	if capability["input_schema"] != "artifact-scaffold-input" {
		t.Fatalf("artifact scaffold capability = %#v", capability)
	}
	if show := requireStringArray(t, payload, "show_argv"); show[3] != "artifact-scaffold-input" {
		t.Fatalf("artifact scaffold show_argv = %#v", show)
	}
	if next := requireStringArray(t, payload, "next_argv"); len(next) < 3 || next[1] != "artifact" || next[2] != "catalog" {
		t.Fatalf("artifact scaffold next_argv = %#v", next)
	}
}

func TestAPISchemaExpandsArtifactScaffoldInputContract(t *testing.T) {
	var stdout, stderr bytes.Buffer
	code := Run([]string{"api", "schema", "--id", "artifact-scaffold-input", "--format", "json"}, &stdout, &stderr, "test")
	if code != 0 {
		t.Fatalf("api schema artifact scaffold exit code = %d; stdout=%s stderr=%s", code, stdout.String(), stderr.String())
	}
	payload := decodeJSONObject(t, stdout.Bytes())
	schema := requireObject(t, requireObject(t, payload, "data"), "schema")
	properties := requireObject(t, schema, "properties")
	if _, ok := properties["path"]; !ok {
		t.Fatalf("artifact scaffold schema properties = %#v", properties)
	}
	if aliases, ok := schema["x-compatibility-aliases"].(map[string]any); !ok || aliases["out"] != "path" {
		t.Fatalf("artifact scaffold compatibility aliases = %#v", schema["x-compatibility-aliases"])
	}
}
