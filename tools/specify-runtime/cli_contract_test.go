package main

import (
	"bytes"
	"encoding/json"
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
	for _, capability := range []string{"api.handshake", "api.list", "validate.spec"} {
		if !containsString(capabilities, capability) {
			t.Fatalf("handshake capability_ids = %#v, want %q", capabilities, capability)
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
		seen[id] = true
	}
	for _, capability := range []string{"api.handshake", "api.list", "validate.spec"} {
		if !seen[capability] {
			t.Fatalf("api list ids = %#v, want %q", seen, capability)
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
