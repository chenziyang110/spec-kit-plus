package main

import (
	"bytes"
	"encoding/json"
	"os"
	"path/filepath"
	"reflect"
	"sort"
	"testing"
)

var unifiedEnvelopeKeys = []string{
	"blockers",
	"data",
	"items",
	"next_argv",
	"show_argv",
	"status",
	"summary",
}

func TestVersionJSONUsesUnifiedEnvelope(t *testing.T) {
	var stdout, stderr bytes.Buffer

	code := Run([]string{"version", "--format", "json"}, &stdout, &stderr, "v9.9.9")

	if code != 0 {
		t.Fatalf("version exit code = %d, want 0; stderr=%q stdout=%q", code, stderr.String(), stdout.String())
	}
	if stderr.Len() != 0 {
		t.Fatalf("version stderr = %q, want empty", stderr.String())
	}
	payload := decodeJSONObject(t, stdout.Bytes())
	requireUnifiedEnvelope(t, payload)
	if payload["status"] != "ok" {
		t.Fatalf("version status = %#v, want ok", payload["status"])
	}
	data := requireObject(t, payload, "data")
	if data["cli_version"] != "v9.9.9" {
		t.Fatalf("version data.cli_version = %#v, want v9.9.9", data["cli_version"])
	}
	if protocol, ok := data["protocol_version"].(string); !ok || protocol == "" {
		t.Fatalf("version data.protocol_version = %#v, want non-empty string", data["protocol_version"])
	}
}

func TestAPIHandshakePublishesProtocolVersionAndCapabilities(t *testing.T) {
	var stdout, stderr bytes.Buffer

	code := Run([]string{"api", "handshake", "--format", "json"}, &stdout, &stderr, "v9.9.9")

	if code != 0 {
		t.Fatalf("api handshake exit code = %d, want 0; stderr=%q stdout=%q", code, stderr.String(), stdout.String())
	}
	payload := decodeJSONObject(t, stdout.Bytes())
	requireUnifiedEnvelope(t, payload)
	data := requireObject(t, payload, "data")
	if data["cli_version"] != "v9.9.9" {
		t.Fatalf("handshake data.cli_version = %#v, want v9.9.9", data["cli_version"])
	}
	if protocol, ok := data["protocol_version"].(string); !ok || protocol == "" {
		t.Fatalf("handshake data.protocol_version = %#v, want non-empty string", data["protocol_version"])
	}
	capabilities := requireStringArray(t, data, "capability_ids")
	seenCapabilities := map[string]bool{}
	for _, capability := range capabilities {
		if seenCapabilities[capability] {
			t.Fatalf("handshake capability_ids contains duplicate %q: %#v", capability, capabilities)
		}
		seenCapabilities[capability] = true
	}
	for _, capability := range []string{
		"api.handshake", "api.list", "artifact.catalog", "artifact.scaffold", "cognition.run", "validate.spec",
		"workflow.show", "workflow.enter", "workflow.next", "workflow.complete-stage", "workflow.transition",
		"workflow.reopen", "workflow.block", "workflow.resolve", "workflow.closeout",
	} {
		if !containsString(capabilities, capability) {
			t.Fatalf("handshake capability_ids = %#v, want %q", capabilities, capability)
		}
	}
	for _, retired := range []string{"workflow.start", "workflow.status"} {
		if containsString(capabilities, retired) {
			t.Fatalf("handshake capability_ids retained retired capability %q: %#v", retired, capabilities)
		}
	}
}

func TestAPIListReturnsCompactCapabilityCards(t *testing.T) {
	var stdout, stderr bytes.Buffer

	code := Run([]string{"api", "list", "--format", "json"}, &stdout, &stderr, "v9.9.9")

	if code != 0 {
		t.Fatalf("api list exit code = %d, want 0; stderr=%q stdout=%q", code, stderr.String(), stdout.String())
	}
	payload := decodeJSONObject(t, stdout.Bytes())
	requireUnifiedEnvelope(t, payload)
	items, ok := payload["items"].([]any)
	if !ok || len(items) == 0 {
		t.Fatalf("api list items = %#v, want non-empty array", payload["items"])
	}
	seen := map[string]bool{}
	for index, raw := range items {
		item, ok := raw.(map[string]any)
		if !ok {
			t.Fatalf("api list items[%d] = %#v, want object", index, raw)
		}
		id, idOK := item["id"].(string)
		summary, summaryOK := item["summary"].(string)
		if !idOK || id == "" || !summaryOK || summary == "" {
			t.Fatalf("api list items[%d] = %#v, want non-empty id and summary", index, item)
		}
		if seen[id] {
			t.Fatalf("api list contains duplicate capability %q", id)
		}
		seen[id] = true
	}
	if len(seen) != len(items) {
		t.Fatalf("api list contains duplicate capability cards: %d unique of %d", len(seen), len(items))
	}
	for _, capability := range []string{
		"api.handshake", "api.list", "artifact.catalog", "artifact.scaffold", "validate.spec",
		"workflow.show", "workflow.enter", "workflow.next", "workflow.complete-stage", "workflow.transition",
		"workflow.reopen", "workflow.block", "workflow.resolve", "workflow.closeout",
	} {
		if !seen[capability] {
			t.Fatalf("api list ids = %#v, want %q", seen, capability)
		}
	}
}

func TestEnvelopeBindsTopLevelAndNestedRuntimeArgvToCurrentExecutable(t *testing.T) {
	env := NewEnvelope("blocked", "binding contract")
	env.ShowArgv = []string{"specify-runtime", "workflow", "show"}
	env.NextArgv = []string{"specify-runtime", "workflow", "next"}
	env.Data["resolution_action"] = map[string]any{
		"base_argv": []any{"specify-runtime", "workflow", "resolve"},
	}
	env.Blockers = append(env.Blockers, map[string]any{
		"resume": map[string]any{"argv": []string{"specify-runtime", "workflow", "show"}},
	})
	var stdout bytes.Buffer
	writeEnvelope(&stdout, env)
	payload := decodeJSONObject(t, stdout.Bytes())
	executable, err := os.Executable()
	if err != nil {
		t.Fatal(err)
	}
	executable, err = filepath.Abs(executable)
	if err != nil {
		t.Fatal(err)
	}
	for label, argv := range map[string][]string{
		"show":       requireStringArray(t, payload, "show_argv"),
		"next":       requireStringArray(t, payload, "next_argv"),
		"resolution": requireStringArray(t, requireObject(t, requireObject(t, payload, "data"), "resolution_action"), "base_argv"),
		"blocker":    requireStringArray(t, requireObject(t, requireObjectValue(t, payload["blockers"].([]any)[0]), "resume"), "argv"),
	} {
		if argv[0] != executable {
			t.Fatalf("%s argv[0] = %q, want %q", label, argv[0], executable)
		}
	}
}

func decodeJSONObject(t *testing.T, raw []byte) map[string]any {
	t.Helper()
	var payload map[string]any
	if err := json.Unmarshal(raw, &payload); err != nil {
		t.Fatalf("decode JSON object: %v; output=%q", err, string(raw))
	}
	return payload
}

func decodeJSONValue(t *testing.T, value any) map[string]any {
	t.Helper()
	raw, err := json.Marshal(value)
	if err != nil {
		t.Fatalf("encode result as JSON: %v", err)
	}
	return decodeJSONObject(t, raw)
}

func requireUnifiedEnvelope(t *testing.T, payload map[string]any) {
	t.Helper()
	keys := make([]string, 0, len(payload))
	for key := range payload {
		keys = append(keys, key)
	}
	sort.Strings(keys)
	if !reflect.DeepEqual(keys, unifiedEnvelopeKeys) {
		t.Fatalf("envelope keys = %#v, want %#v", keys, unifiedEnvelopeKeys)
	}
	if summary, ok := payload["summary"].(string); !ok || summary == "" {
		t.Fatalf("envelope summary = %#v, want non-empty string", payload["summary"])
	}
	for _, key := range []string{"items", "blockers", "show_argv", "next_argv"} {
		if _, ok := payload[key].([]any); !ok {
			t.Fatalf("envelope %s = %#v, want array", key, payload[key])
		}
	}
}

func requireObject(t *testing.T, payload map[string]any, key string) map[string]any {
	t.Helper()
	value, ok := payload[key].(map[string]any)
	if !ok {
		t.Fatalf("%s = %#v, want object", key, payload[key])
	}
	return value
}

func requireObjectValue(t *testing.T, value any) map[string]any {
	t.Helper()
	result, ok := value.(map[string]any)
	if !ok {
		t.Fatalf("value = %#v, want object", value)
	}
	return result
}

func requireStringArray(t *testing.T, payload map[string]any, key string) []string {
	t.Helper()
	raw, ok := payload[key].([]any)
	if !ok {
		t.Fatalf("%s = %#v, want array", key, payload[key])
	}
	values := make([]string, 0, len(raw))
	for index, item := range raw {
		value, ok := item.(string)
		if !ok || value == "" {
			t.Fatalf("%s[%d] = %#v, want non-empty string", key, index, item)
		}
		values = append(values, value)
	}
	return values
}

func containsString(values []string, want string) bool {
	for _, value := range values {
		if value == want {
			return true
		}
	}
	return false
}
