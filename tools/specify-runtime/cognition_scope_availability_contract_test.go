package main

import (
	"bytes"
	"context"
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"

	rt "github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/runtime"
	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/store"
)

func TestCognitionScopeAvailabilityAPIAndSchemaAreUsable(t *testing.T) {
	var stdout, stderr bytes.Buffer
	for _, args := range [][]string{{"api", "ensure", "--capabilities", "cognition.scope-availability.v2", "--format", "json"}, {"api", "show", "cognition.scope-availability.v2", "--format", "json"}, {"api", "schema", "cognition-scope-availability-input", "--format", "json"}, {"api", "pack", "--capabilities", "cognition.scope-availability.v2", "--include-schema", "--format", "json"}} {
		stdout.Reset()
		stderr.Reset()
		if code := Run(args, &stdout, &stderr, "test"); code != 0 {
			t.Fatalf("%v code=%d out=%s err=%s", args, code, stdout.String(), stderr.String())
		}
		var env map[string]any
		if err := json.Unmarshal(stdout.Bytes(), &env); err != nil || env["status"] != "ok" {
			t.Fatalf("%v out=%s err=%v", args, stdout.String(), err)
		}
	}
	stdout.Reset()
	_ = Run([]string{"api", "show", "cognition.scope-availability.v2", "--format", "json"}, &stdout, &stderr, "test")
	capability := requireObject(t, requireObject(t, decodeJSONObject(t, stdout.Bytes()), "data"), "capability")
	if capability["side_effect"] != "read-only" || capability["input_schema"] != "cognition-scope-availability-input" || !strings.Contains(anyString(capability["usage"]), "--task-packet") {
		t.Fatalf("unusable descriptor=%#v", capability)
	}
}

func TestCognitionScopeAvailabilityConsumesActualNativeCompiledPacket(t *testing.T) {
	root, feature, featureRef := newImplementedTaskRecoveryFixture(t)
	index := readImplementJSONFile(t, filepath.Join(feature, "task-index.json"))
	task := index["tasks"].([]any)[1].(map[string]any)
	task["read_scope"] = []any{"src/dependency.go"}
	writeTaskRuntimeFixture(t, filepath.Join(feature, "task-index.json"), index)
	if err := os.MkdirAll(filepath.Join(root, ".specify", "templates"), 0755); err != nil {
		t.Fatal(err)
	}
	writeTaskRuntimeFixture(t, filepath.Join(root, ".specify", "templates", "task-packet-template.json"), map[string]any{"ui_contract": map[string]any{"fidelity_level": "none"}})
	paths := workerPlannerFixture(t, root, []string{"src/t002.go", "src/dependency.go", "src/unrelated.go"})
	owner, err := store.OpenExisting(paths)
	if err != nil {
		t.Fatal(err)
	}
	for _, path := range []string{"src/t002.go", "src/dependency.go", "src/unrelated.go"} {
		data, err := os.ReadFile(filepath.Join(root, filepath.FromSlash(path)))
		if err != nil {
			owner.Close()
			t.Fatal(err)
		}
		if _, err := owner.DB().ExecContext(context.Background(), `UPDATE evidence SET content_hash=? WHERE source_path=?`, "sha256:"+fileContentSHA256(data), path); err != nil {
			owner.Close()
			t.Fatal(err)
		}
	}
	owner.Close()
	status, err := rt.ReadStatus(paths)
	if err != nil {
		t.Fatal(err)
	}
	status.DirtyDebts = []rt.DebtRecord{{ID: "debt-unrelated", Kind: "mark_dirty", Paths: []string{"src/unrelated.go"}, Reason: "unrelated owner review pending"}}
	status.Freshness = rt.StaleFreshness
	status.Readiness = rt.ReviewReadiness
	if err := rt.WriteStatus(paths, status); err != nil {
		t.Fatal(err)
	}
	compiled := assertTaskRuntimeCommandOK(t, []string{"implement", "packet-compile", "--feature-dir", featureRef, "--task-id", "T002", "--format", "json"})
	packetRef := compiled["path"].(string)
	var prior map[string]any
	for _, command := range []string{"check", "status", "doctor"} {
		var stdout, stderr bytes.Buffer
		code := Run([]string{"cognition", command, "--task-packet", packetRef, "--format", "json"}, &stdout, &stderr, "test")
		env := decodeJSONObject(t, stdout.Bytes())
		data := requireObject(t, env, "data")
		if code != 0 || data["scope_ready"] != true || data["claim_ready"] != false || data["source_changes_authorized"] != false {
			t.Fatalf("%s actual native packet unusable: code=%d out=%s err=%s", command, code, stdout.String(), stderr.String())
		}
		global := requireObject(t, data, "global_status")
		if global["freshness"] == rt.ReadyFreshness || global["dirty"] != true {
			t.Fatalf("scope changed global truth: %#v", global)
		}
		scope := requireObject(t, data, "scope")
		reads := scope["read_scope"].([]any)
		if len(reads) != 1 || reads[0] != "src/dependency.go" {
			t.Fatalf("actual native read scope omitted: %#v", scope)
		}
		if prior != nil {
			a, _ := json.Marshal(prior)
			b, _ := json.Marshal(data)
			if !bytes.Equal(a, b) {
				t.Fatal("actual entrypoints disagree")
			}
		}
		prior = data
		t.Logf("actual-native-%s-output=%s", command, stdout.String())
	}
	binding, _ := json.Marshal(prior["binding"])
	if err := os.WriteFile(filepath.Join(root, "src/dependency.go"), []byte("changed exact read dependency\n"), 0644); err != nil {
		t.Fatal(err)
	}
	var stdout, stderr bytes.Buffer
	code := Run([]string{"cognition", "check", "--task-packet", packetRef, "--availability-json", string(binding), "--format", "json"}, &stdout, &stderr, "test")
	data := requireObject(t, decodeJSONObject(t, stdout.Bytes()), "data")
	if code == 0 || data["scope_ready"] != false || !strings.Contains(stdout.String(), "stale_scope_availability") {
		t.Fatalf("actual native stale dependency reused: code=%d out=%s", code, stdout.String())
	}
	t.Logf("actual-native-stale-dependency-output=%s", stdout.String())
}

func TestCognitionScopeAvailabilityPublicEntrypointsDoNotGrantWriteOrAcceptance(t *testing.T) {
	root := t.TempDir()
	if err := os.MkdirAll(filepath.Join(root, ".specify"), 0755); err != nil {
		t.Fatal(err)
	}
	old, err := os.Getwd()
	if err != nil {
		t.Fatal(err)
	}
	if err := os.Chdir(root); err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { _ = os.Chdir(old) })
	if err := os.WriteFile(filepath.Join(root, "packet.json"), []byte(`{"version":2,"feature_id":"scope-feature","task_id":"T01","read_scope":["src/a.go"],"write_scope":["src/a.go"]}`), 0644); err != nil {
		t.Fatal(err)
	}
	for _, command := range []string{"check", "status", "doctor"} {
		var stdout, stderr bytes.Buffer
		code := Run([]string{"cognition", command, "--task-packet", "packet.json", "--format", "json"}, &stdout, &stderr, "test")
		env := decodeJSONObject(t, stdout.Bytes())
		data := requireObject(t, env, "data")
		if code == 0 || env["status"] != "blocked" || data["scope_ready"] != false || data["claim_ready"] != false || data["source_changes_authorized"] != false || data["review_required"] != true || data["human_accept_required"] != true {
			t.Fatalf("%s code=%d out=%s err=%s", command, code, stdout.String(), stderr.String())
		}
		if _, err := os.Stat(filepath.Join(root, ".specify", "project-cognition", "status.json")); !os.IsNotExist(err) {
			t.Fatalf("read created runtime state: %v", err)
		}
	}
}
