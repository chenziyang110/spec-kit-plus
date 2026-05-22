package cli

import (
	"bytes"
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestVersionPrintsBinaryName(t *testing.T) {
	var stdout, stderr bytes.Buffer
	code := Run([]string{"--version"}, &stdout, &stderr, "v1.2.3")
	if code != 0 {
		t.Fatalf("code = %d stderr=%s", code, stderr.String())
	}
	if strings.TrimSpace(stdout.String()) != "project-cognition v1.2.3" {
		t.Fatalf("stdout = %q", stdout.String())
	}
}

func TestStatusReturnsUnsupportedLegacyJSON(t *testing.T) {
	root := t.TempDir()
	dir := filepath.Join(root, ".specify", "project-cognition")
	if err := os.MkdirAll(dir, 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(dir, "status.json"), []byte(`{"freshness":"fresh"}`), 0o644); err != nil {
		t.Fatal(err)
	}
	old, _ := os.Getwd()
	if err := os.Chdir(root); err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { _ = os.Chdir(old) })

	var stdout, stderr bytes.Buffer
	code := Run([]string{"status", "--format", "json"}, &stdout, &stderr, "test")
	if code != 0 {
		t.Fatalf("code = %d stderr=%s", code, stderr.String())
	}
	var payload map[string]any
	if err := json.Unmarshal(stdout.Bytes(), &payload); err != nil {
		t.Fatal(err)
	}
	if payload["error_code"] != "unsupported_legacy_runtime" {
		t.Fatalf("payload = %#v", payload)
	}
}

func TestDeltaBeginCommandCreatesSession(t *testing.T) {
	root := t.TempDir()
	if err := os.Mkdir(filepath.Join(root, ".specify"), 0o755); err != nil {
		t.Fatal(err)
	}
	old, _ := os.Getwd()
	if err := os.Chdir(root); err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { _ = os.Chdir(old) })

	var stdout, stderr bytes.Buffer
	code := Run([]string{"delta", "begin", "--origin-command", "quick", "--format", "json"}, &stdout, &stderr, "test")
	if code != 0 {
		t.Fatalf("code = %d stderr=%s", code, stderr.String())
	}
	var payload map[string]any
	if err := json.Unmarshal(stdout.Bytes(), &payload); err != nil {
		t.Fatal(err)
	}
	if payload["session_id"] == "" {
		t.Fatalf("payload = %#v", payload)
	}
}

func TestDeltaAppendCommandWritesEvent(t *testing.T) {
	root := t.TempDir()
	if err := os.Mkdir(filepath.Join(root, ".specify"), 0o755); err != nil {
		t.Fatal(err)
	}
	old, _ := os.Getwd()
	if err := os.Chdir(root); err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { _ = os.Chdir(old) })

	sessionID := beginDeltaSession(t)
	var stdout, stderr bytes.Buffer
	code := Run([]string{
		"delta", "append",
		"--session", sessionID,
		"--event-type", "worker_result",
		"--changed-path", "src/a.go",
		"--verification", "go test ./... PASS",
		"--format", "json",
	}, &stdout, &stderr, "test")
	if code != 0 {
		t.Fatalf("code = %d stderr=%s", code, stderr.String())
	}
	var payload map[string]any
	if err := json.Unmarshal(stdout.Bytes(), &payload); err != nil {
		t.Fatal(err)
	}
	if payload["event_id"] == "" {
		t.Fatalf("payload = %#v", payload)
	}
}

func TestDeltaAppendCommandAcceptsPacketFile(t *testing.T) {
	root := t.TempDir()
	if err := os.Mkdir(filepath.Join(root, ".specify"), 0o755); err != nil {
		t.Fatal(err)
	}
	old, _ := os.Getwd()
	if err := os.Chdir(root); err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { _ = os.Chdir(old) })

	sessionID := beginDeltaSession(t)
	packet := filepath.Join(root, "packet.json")
	data := []byte(`{"event_type":"worker_result","changed_paths":["src/a.go"],"verification_evidence":["go test ./... PASS"]}`)
	if err := os.WriteFile(packet, data, 0o644); err != nil {
		t.Fatal(err)
	}

	var stdout, stderr bytes.Buffer
	code := Run([]string{
		"delta", "append",
		"--session", sessionID,
		"--packet-file", packet,
		"--format", "json",
	}, &stdout, &stderr, "test")
	if code != 0 {
		t.Fatalf("code = %d stderr=%s", code, stderr.String())
	}
	var payload map[string]any
	if err := json.Unmarshal(stdout.Bytes(), &payload); err != nil {
		t.Fatal(err)
	}
	if payload["event_type"] != "worker_result" {
		t.Fatalf("payload = %#v", payload)
	}
}

func beginDeltaSession(t *testing.T) string {
	t.Helper()
	var stdout, stderr bytes.Buffer
	code := Run([]string{"delta", "begin", "--origin-command", "quick", "--format", "json"}, &stdout, &stderr, "test")
	if code != 0 {
		t.Fatalf("begin code = %d stderr=%s", code, stderr.String())
	}
	var payload map[string]any
	if err := json.Unmarshal(stdout.Bytes(), &payload); err != nil {
		t.Fatal(err)
	}
	sessionID, ok := payload["session_id"].(string)
	if !ok || sessionID == "" {
		t.Fatalf("payload = %#v", payload)
	}
	return sessionID
}
