package cli

import (
	"bytes"
	"encoding/json"
	"os"
	"path/filepath"
	"reflect"
	"testing"
)

func TestScopedStatusCheckDoctorUseSameNativeOwnerAndPreserveGlobalRead(t *testing.T) {
	root := initEmptyCLIRuntime(t)
	if err := os.WriteFile(filepath.Join(root, "packet.json"), []byte(`{"version":2,"feature_id":"scope-feature","task_id":"T01","read_scope":["src/new.go"],"write_scope":["src/new.go"]}`), 0644); err != nil {
		t.Fatal(err)
	}
	var first map[string]any
	for _, command := range []string{"status", "check", "doctor"} {
		var stdout, stderr bytes.Buffer
		code := Run([]string{command, "--task-packet", "packet.json", "--format", "json"}, &stdout, &stderr, "test")
		var payload map[string]any
		if err := json.Unmarshal(stdout.Bytes(), &payload); err != nil {
			t.Fatalf("%s output=%s err=%v", command, stdout.String(), err)
		}
		if code != exitCodeBlocked || payload["scope_ready"] != false || payload["global_status"] == nil {
			t.Fatalf("%s code=%d out=%s stderr=%s", command, code, stdout.String(), stderr.String())
		}
		if first != nil && !reflect.DeepEqual(first, payload) {
			t.Fatalf("entrypoint outcomes disagree: %s", command)
		}
		first = payload
	}
	var stdout, stderr bytes.Buffer
	if code := Run([]string{"status", "--format", "json"}, &stdout, &stderr, "test"); code != 0 {
		t.Fatalf("global status code=%d", code)
	}
	var global map[string]any
	_ = json.Unmarshal(stdout.Bytes(), &global)
	if global["scope_ready"] != nil || global["freshness"] == nil {
		t.Fatalf("global contract replaced: %s", stdout.String())
	}
}

func TestScopedStatusRefusesOldBindingAndDocumentsExactFlags(t *testing.T) {
	_ = initEmptyCLIRuntime(t)
	var stdout, stderr bytes.Buffer
	code := Run([]string{"check", "--task-packet", "packet.json", "--availability-json", `{"contract_version":0}`}, &stdout, &stderr, "test")
	if code != exitCodeBlocked || !bytes.Contains(stdout.Bytes(), []byte("incompatible_scope_availability")) {
		t.Fatalf("code=%d out=%s err=%s", code, stdout.String(), stderr.String())
	}
	stdout.Reset()
	stderr.Reset()
	_ = Run([]string{"check", "--help"}, &stdout, &stderr, "test")
	if !bytes.Contains(stderr.Bytes(), []byte("task-packet")) || !bytes.Contains(stderr.Bytes(), []byte("availability-json")) {
		t.Fatalf("scope flags missing help: %s", stderr.String())
	}
}
