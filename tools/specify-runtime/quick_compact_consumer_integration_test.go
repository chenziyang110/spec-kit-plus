package main

import (
	"bytes"
	"fmt"
	"os"
	"path/filepath"
	"reflect"
	"strings"
	"testing"
)

// Full-package regression: real Work/Quick/result-submit, synthetic result
// observations. This is not an installed-agent or product-validation benchmark.
func TestQuickCompactConsumerLifecycle(t *testing.T) {
	for _, direct := range []bool{false, true} {
		for _, compact := range []bool{false, true} {
			t.Run(fmt.Sprintf("direct=%t/compact=%t", direct, compact), func(t *testing.T) {
				id := "260915-compact-consumer"
				root, workspace := stageConfirmedQuickExecutionTestWorkspace(t, id, quickExecutionSingleItemPayload("src/a.go"))
				previous, err := os.Getwd()
				if err != nil {
					t.Fatal(err)
				}
				if err := os.Chdir(root); err != nil {
					t.Fatal(err)
				}
				t.Cleanup(func() {
					if err := os.Chdir(previous); err != nil {
						t.Error(err)
					}
				})
				if err := os.WriteFile(filepath.Join(root, ".specify", "integration.json"), []byte(`{"integration":"codex"}`), 0o600); err != nil {
					t.Fatal(err)
				}
				call := func(mode string, extra ...string) Envelope {
					args := append([]string{"--project-root", root, mode, id, "--item", "Q1"}, extra...)
					if compact {
						args = append(args, "--compact")
					}
					return runScriptDomainEnvelope(t, runQuick, args)
				}
				// Read complete intake before the one and only start in this run.
				intake := runScriptDomainEnvelope(t, runQuick, []string{"--project-root", root, "item-status", id})
				if intake.Status != "ok" || intake.Data["confirmation"] == nil {
					t.Fatal(intake)
				}
				var flags []string
				if direct {
					flags = []string{"--leader-direct"}
				}
				started := call("item-start", flags...)
				if started.Status != "ok" || started.Data["packet"] == nil || started.Data["work_claim"] == nil || started.Data["requires_worker"] != !direct {
					t.Fatal(started)
				}
				if compact {
					if started.Data["response_schema"] != quickExecutionCompactSchema || started.Data["confirmation"] != nil || started.Data["pulse"] != nil {
						t.Fatal("compact start lost its presentation contract")
					}
					decision := intake.Data["confirmation"].(map[string]any)
					if started.Data["confirmation_digest"] != decision["confirmation_digest"] || started.Data["confirmation_state"] != decision["confirmation_state"] {
						t.Fatal("start changed the intake decision binding")
					}
				} else if started.Data["confirmation"] == nil || started.Data["pulse"] == nil {
					t.Fatal("default start is no longer full")
				}
				quickCompactConsumerCompareReads(t, root, id, workspace)
				if rejected := call("item-accept", "--evidence", "no submitted result"); rejected.Status == "ok" {
					t.Fatal("presentation waived required result proof")
				}
				raw := `{"task_id":"Q1","status":"success","changed_files":["src/a.go"],"validation_results":[{"command":"synthetic transport fixture","status":"passed"}],"blockers":[]}`
				submitted := runScriptDomainEnvelope(t, runResult, []string{"submit", "--command", "quick", "--workspace", workspace, "--lane-id", "Q1", "--result-json", raw})
				if submitted.Status != "ok" {
					t.Fatal(submitted)
				}
				accepted := call("item-accept", "--evidence", "synthetic transport fixture only")
				if accepted.Status != "ok" || accepted.Data["all_accepted"] != true || accepted.Data["worker_proof"] == nil {
					t.Fatal(accepted)
				}
				quickCompactConsumerCompareReads(t, root, id, workspace)
				// No replayed start/accept to expand presentation; no closeout claim.
			})
		}
	}
}

func quickCompactConsumerCompareReads(t *testing.T, root, id, workspace string) {
	t.Helper()
	before := map[string][]byte{}
	for _, name := range []string{"confirmation.json", "STATUS.md"} {
		raw, err := os.ReadFile(filepath.Join(workspace, name))
		if err != nil {
			t.Fatal(err)
		}
		before[name] = raw
	}
	args := []string{"--project-root", root, "item-status", id}
	full := runScriptDomainEnvelope(t, runQuick, args)
	compact := runScriptDomainEnvelope(t, runQuick, append(args, "--compact"))
	if full.Status != "ok" || compact.Status != "ok" {
		t.Fatalf("status refresh failed: %#v %#v", full, compact)
	}
	doc := full.Data["confirmation"].(map[string]any)
	expected := map[string]any{}
	for key, value := range full.Data {
		if key != "confirmation" && key != "pulse" {
			expected[key] = value
		}
	}
	ref, err := filepath.Rel(root, filepath.Join(workspace, "confirmation.json"))
	if err != nil {
		t.Fatal(err)
	}
	expected["response_schema"] = quickExecutionCompactSchema
	expected["confirmation_ref"] = filepath.ToSlash(ref)
	expected["confirmation_digest"] = doc["confirmation_digest"]
	expected["confirmation_state"] = doc["confirmation_state"]
	if !reflect.DeepEqual(expected, compact.Data) {
		t.Fatalf("compact changed non-omitted state: expected %#v, got %#v", expected, compact.Data)
	}
	for name, raw := range before {
		after, err := os.ReadFile(filepath.Join(workspace, name))
		if err != nil || !bytes.Equal(raw, after) {
			t.Fatalf("status refresh mutated %s: %v", name, err)
		}
	}
	if strings.Contains(fmt.Sprint(compact.Blockers), "worker_result_required") {
		t.Fatal("read-only refresh unexpectedly attempted acceptance")
	}
}
