package main

import (
	"bytes"
	"path/filepath"
	"reflect"
	"strings"
	"testing"
)

func TestTasksRebindDiscoveryIsCompleteBeforeRepositoryAccess(t *testing.T) {
	missing := filepath.Join(t.TempDir(), "absent", "feature")
	var helpOut, showOut, stderr bytes.Buffer
	if code := Run([]string{"tasks", "rebind", "--feature-dir", missing, "--help"}, &helpOut, &stderr, "test"); code != 0 {
		t.Fatalf("read-only help tried to load the absent feature: exit=%d stdout=%s stderr=%s", code, helpOut.String(), stderr.String())
	}
	if code := Run([]string{"api", "show", "tasks.rebind", "--format", "json"}, &showOut, &stderr, "test"); code != 0 {
		t.Fatalf("API descriptor unavailable: exit=%d stdout=%s", code, showOut.String())
	}
	help := requireObject(t, requireObject(t, decodeJSONObject(t, helpOut.Bytes()), "data"), "capability")
	show := requireObject(t, requireObject(t, decodeJSONObject(t, showOut.Bytes()), "data"), "capability")
	if !reflect.DeepEqual(help, show) {
		t.Fatalf("help and API command contracts differ: help=%#v show=%#v", help, show)
	}
	usage := show["usage"].(string)
	for _, guard := range []string{"--expected-task-index-sha256", "--expected-workflow-revision", "--expected-test-design-handoff-sha256", "--reason", "--task-updates-json"} {
		if !strings.Contains(usage, guard) {
			t.Fatalf("discovered usage omits required recovery surface %q: %s", guard, usage)
		}
	}
	if show["side_effect"] != "rebinds-task-package" || show["input_schema"] != "tasks-rebind-updates-input" {
		t.Fatalf("rebind must expose its mutation boundary and semantic input schema: %#v", show)
	}
	if pathExists(missing) {
		t.Fatal("help created the absent feature")
	}

	var ensureOut bytes.Buffer
	if code := Run([]string{"api", "ensure", "--capabilities", "tasks.rebind", "--format", "json"}, &ensureOut, &stderr, "test"); code != 0 {
		t.Fatalf("conditional recovery capability cannot be negotiated: exit=%d stdout=%s", code, ensureOut.String())
	}
	data := requireObject(t, decodeJSONObject(t, ensureOut.Bytes()), "data")
	if present := requireStringArray(t, data, "present"); len(present) != 1 || present[0] != "tasks.rebind" {
		t.Fatalf("unexpected negotiated capability: %#v", present)
	}
}

func TestTasksRebindPackPublishesRestrictedSemanticDelta(t *testing.T) {
	var packOut, schemaOut, stderr bytes.Buffer
	if code := Run([]string{"api", "pack", "--capabilities", "tasks.rebind", "--include-schema", "--format", "json"}, &packOut, &stderr, "test"); code != 0 {
		t.Fatalf("pack exit=%d stdout=%s stderr=%s", code, packOut.String(), stderr.String())
	}
	payload := decodeJSONObject(t, packOut.Bytes())
	items, ok := payload["items"].([]any)
	if !ok || len(items) != 1 {
		t.Fatalf("pack did not return one bounded descriptor: %#v", payload)
	}
	item, ok := items[0].(map[string]any)
	if !ok || item["schema_ref"] != "tasks-rebind-updates-input" || item["output_contract"] == nil {
		t.Fatalf("recovery packet omits its input or audit result contract: %#v", items)
	}
	if code := Run([]string{"api", "schema", "tasks-rebind-updates-input", "--format", "json"}, &schemaOut, &stderr, "test"); code != 0 {
		t.Fatalf("schema exit=%d stdout=%s", code, schemaOut.String())
	}
	schema := requireObject(t, requireObject(t, decodeJSONObject(t, schemaOut.Bytes()), "data"), "schema")
	if !reflect.DeepEqual(item["schema"], schema) {
		t.Fatal("API pack and standalone schema disagree")
	}
	if schema["additionalProperties"] != false {
		t.Fatal("rebind schema admits task-index root mutations")
	}
	task := requireObject(t, requireObject(t, schema, "patternProperties"), "^T[0-9]+$")
	properties := requireObject(t, task, "properties")
	if task["additionalProperties"] != false || len(properties) != 3 {
		t.Fatalf("rebind schema admits lifecycle or binding field authoring: %#v", task)
	}
	for _, field := range []string{"test_case_refs", "test_data_refs", "ui_contract"} {
		if _, ok := properties[field].(map[string]any); !ok {
			t.Fatalf("missing legal recovery field %q", field)
		}
	}
}
