package main

import (
	"bytes"
	"crypto/sha256"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"reflect"
	"strings"
	"testing"
)

func TestImplementTaskReopenRecoversUIOnlyFailureAfterResultMerge(t *testing.T) {
	for _, test := range []struct {
		name         string
		verification map[string]any
		wantError    string
	}{
		{
			name:      "missing_ui_verification",
			wantError: "human usability validation requires ui_verification",
		},
		{
			name: "agent_only_review",
			verification: map[string]any{
				"applicable": true, "contract_check": "passed", "runtime_evidence": "passed",
				"reviewer": "agent", "human_review_ref": "evidence/prior-agent-review.md",
			},
			wantError: "human usability validation requires a human reviewer",
		},
	} {
		t.Run(test.name, func(t *testing.T) {
			root, feature, featureRef := newUIReopenTaskFixture(t)
			bindImplementTestWork(t, root, featureRef, []string{"src/t002.go"})
			readFile := func(ref string) []byte {
				t.Helper()
				raw, err := os.ReadFile(filepath.Join(feature, filepath.FromSlash(ref)))
				if os.IsNotExist(err) {
					return nil
				}
				if err != nil {
					t.Fatal(err)
				}
				return raw
			}
			mergeResult := func(result map[string]any) map[string]any {
				t.Helper()
				raw, err := json.Marshal(result)
				if err != nil {
					t.Fatal(err)
				}
				return assertTaskRuntimeCommandOK(t, []string{
					"implement", "result-merge", "--feature-dir", featureRef, "--task-id", "T002",
					"--result-json", string(raw), "--format", "json",
				})
			}
			assertTaskRuntimeCommandOK(t, []string{
				"implement", "task-start", "--feature-dir", featureRef, "--task-id", "T002", "--format", "json",
			})
			result := map[string]any{
				"task_id": "T002", "status": "success", "changed_files": []any{"src/t002.go"},
				"validation_results": []any{map[string]any{"command": "required check", "status": "passed"}},
				"blockers":           []any{}, "suggested_recovery_actions": []any{},
			}
			if test.verification != nil {
				result["ui_verification"] = test.verification
			}
			merged := mergeResult(result)
			if merged["worker_status"] != "success" || merged["task_status"] != "implemented" {
				t.Fatalf("passing ordinary checks did not produce an implemented task: %#v", merged)
			}

			// The defect starts with a real successful merge. No lifecycle or result
			// artifact is edited to recover it after this point.
			lifecycleRef := "implementation-review/tasks/T002.json"
			resultRef := "worker-results/T002.json"
			beforeLifecycle := readImplementJSONFile(t, filepath.Join(feature, lifecycleRef))
			beforeResult := readImplementJSONFile(t, filepath.Join(feature, resultRef))
			beforeResultBytes := readFile(resultRef)
			taskRevision := intFromAny(beforeLifecycle["revision"])
			workflowRevision := intFromAny(readImplementJSONFile(t, filepath.Join(feature, "workflow.json"))["revision"])
			historyRef := fmt.Sprintf("implementation-review/task-reopen-history/T002/revision-%d.json", taskRevision)
			stateRefs := []string{
				"task-index.json", "tasks.md", "implement-tracker.md", "workflow.json",
				"implementation-review/execution-state.json", lifecycleRef, resultRef, historyRef,
			}
			snapshot := func(refs []string) map[string][]byte {
				t.Helper()
				values := make(map[string][]byte, len(refs))
				for _, ref := range refs {
					values[ref] = readFile(ref)
				}
				return values
			}
			assertSnapshot := func(label string, expected map[string][]byte) {
				t.Helper()
				for ref, raw := range expected {
					if actual := readFile(ref); !bytes.Equal(actual, raw) || (actual == nil) != (raw == nil) {
						t.Fatalf("%s changed %s", label, ref)
					}
				}
			}
			beforeState := snapshot(stateRefs)
			siblingFiles := snapshot([]string{
				"implementation-review/tasks/T001.json", "implementation-review/tasks/T003.json",
				"implementation-review/tasks/T004.json", "implementation-review/tasks/T006.json",
			})
			siblingTasks := map[string]any{}
			for _, raw := range readImplementJSONFile(t, filepath.Join(feature, "task-index.json"))["tasks"].([]any) {
				task := raw.(map[string]any)
				if task["id"] != "T002" {
					siblingTasks[anyString(task["id"])] = task
				}
			}
			assertSiblings := func() {
				t.Helper()
				assertSnapshot("UI recovery", siblingFiles)
				index := readImplementJSONFile(t, filepath.Join(feature, "task-index.json"))
				for id, expected := range siblingTasks {
					_, actual, err := findImplementTask(index, id)
					if err != nil || !reflect.DeepEqual(actual, expected) {
						t.Fatalf("UI recovery changed sibling %s: got %#v, want %#v, err %v", id, actual, expected, err)
					}
				}
			}
			exit, rejected := runTaskRuntimeCommand(t, []string{
				"implement", "task-accept", "--feature-dir", featureRef, "--task-id", "T002", "--format", "json",
			})
			if exit == 0 || !strings.Contains(rejected.Summary, test.wantError) {
				t.Fatalf("expected UI-only acceptance failure %q: exit=%d env=%#v", test.wantError, exit, rejected)
			}
			assertSnapshot("rejected UI acceptance", beforeState)
			for command, field := range map[string]string{"task-next": "reason_code", "resume-audit": "resume_classification"} {
				exit, blocked := runTaskRuntimeCommand(t, []string{"implement", command, "--feature-dir", featureRef, "--format", "json"})
				want := "task-reopen-required"
				if command == "resume-audit" {
					want = "task-recovery-required"
				}
				if exit == 0 || blocked.Status != "blocked" || blocked.Data[field] != want {
					t.Fatalf("%s did not route UI-only failure to reopen: exit=%d env=%#v", command, exit, blocked)
				}
			}
			reopenArgs := func(taskRev, workflowRev int) []string {
				return []string{
					"implement", "task-reopen", "--feature-dir", featureRef, "--task-id", "T002",
					"--expected-task-revision", fmt.Sprint(taskRev), "--expected-workflow-revision", fmt.Sprint(workflowRev),
					"--reason", "Complete missing human UI verification.", "--evidence", test.wantError, "--format", "json",
				}
			}
			for _, stale := range []struct {
				taskRev, workflowRev int
				wantError            string
			}{
				{taskRevision - 1, workflowRevision, "task revision is stale"},
				{taskRevision, workflowRevision - 1, "workflow revision is stale"},
			} {
				exit, rejected := runTaskRuntimeCommand(t, reopenArgs(stale.taskRev, stale.workflowRev))
				if exit == 0 || !strings.Contains(rejected.Summary, stale.wantError) {
					t.Fatalf("stale reopen should block: exit=%d env=%#v", exit, rejected)
				}
				assertSnapshot("stale reopen", beforeState)
			}

			reopened := assertTaskRuntimeCommandOK(t, reopenArgs(taskRevision, workflowRevision))
			if reopened["task_status"] != "ready" || intFromAny(reopened["revision"]) != taskRevision+1 || reopened["history_ref"] != historyRef {
				t.Fatalf("UI-only failure did not reopen: %#v", reopened)
			}
			historyBytes := readFile(historyRef)
			history := readImplementJSONFile(t, filepath.Join(feature, filepath.FromSlash(historyRef)))
			previous := history["previous"].(map[string]any)
			if !reflect.DeepEqual(previous["worker_result"], beforeResult) || previous["result_sha256"] != fmt.Sprintf("%x", sha256.Sum256(beforeResultBytes)) {
				t.Fatalf("reopen did not preserve the prior merged worker result and digest: %#v", previous)
			}
			for _, field := range []string{"validation", "ui_verification", "changed_paths", "blockers", "obligation_evidence"} {
				if !reflect.DeepEqual(previous[field], beforeLifecycle[field]) {
					t.Fatalf("reopen did not archive lifecycle %s: got %#v, want %#v", field, previous[field], beforeLifecycle[field])
				}
			}
			marker := readImplementJSONFile(t, filepath.Join(feature, resultRef))
			if marker["status"] != "superseded" || marker["history_ref"] != historyRef || marker["history_sha256"] != fmt.Sprintf("%x", sha256.Sum256(historyBytes)) || marker["history_sha256"] != reopened["history_sha256"] {
				t.Fatalf("superseded result does not bind the preserved history: %#v", marker)
			}
			assertSiblings()
			next := assertTaskRuntimeCommandOK(t, []string{"implement", "task-next", "--feature-dir", featureRef, "--format", "json"})
			if next["task"].(map[string]any)["task_id"] != "T002" {
				t.Fatalf("reopened task was not selected for retry: %#v", next)
			}
			assertTaskRuntimeCommandOK(t, []string{
				"implement", "task-start", "--feature-dir", featureRef, "--task-id", "T002", "--format", "json",
			})
			// This fixture stands for the human review artifact submitted on retry.
			reviewRef := "evidence/usability-review.md"
			if err := os.WriteFile(filepath.Join(feature, reviewRef), []byte("# Human usability review\n\nPASS: the settings task met the approved success criteria.\n"), 0o644); err != nil {
				t.Fatal(err)
			}
			result["ui_verification"] = map[string]any{
				"applicable": true, "contract_check": "passed", "runtime_evidence": "passed",
				"reviewer": "human", "human_review_ref": reviewRef,
			}
			corrected := mergeResult(result)
			correctedHistoryRef := fmt.Sprintf("implementation-review/task-reopen-history/T002/revision-%d.json", intFromAny(corrected["revision"]))
			readyState := snapshot(append(stateRefs, correctedHistoryRef))
			exit, rejected = runTaskRuntimeCommand(t, reopenArgs(intFromAny(corrected["revision"]), workflowRevision))
			if exit == 0 || !strings.Contains(rejected.Summary, "is acceptance-ready") {
				t.Fatalf("acceptance-ready UI task should reject unnecessary reopen: exit=%d env=%#v", exit, rejected)
			}
			assertSnapshot("acceptance-ready reopen rejection", readyState)
			accepted := assertTaskRuntimeCommandOK(t, []string{
				"implement", "task-accept", "--feature-dir", featureRef, "--task-id", "T002", "--format", "json",
			})
			if accepted["task_status"] != "accepted" || accepted["next_task_id"] != "T003" {
				t.Fatalf("corrected UI proof did not complete recovery and unlock the dependent task: %#v", accepted)
			}
			assertSiblings()
			assertSnapshot("successful UI retry", map[string][]byte{historyRef: historyBytes})
		})
	}
}

func newUIReopenTaskFixture(t *testing.T) (string, string, string) {
	t.Helper()
	root, feature, featureRef := newImplementedTaskRecoveryFixture(t)
	for _, path := range []string{filepath.Join(root, ".specify", "templates"), filepath.Join(feature, "evidence")} {
		if err := os.MkdirAll(path, 0o755); err != nil {
			t.Fatal(err)
		}
	}
	writeTaskRuntimeFixture(t, filepath.Join(root, ".specify", "templates", "task-packet-template.json"), map[string]any{
		"ui_contract": map[string]any{"fidelity_level": "none", "surface_catalog": []any{}, "usability_validation": map[string]any{}},
	})
	indexPath := filepath.Join(feature, "task-index.json")
	index := readImplementJSONFile(t, indexPath)
	tasks := index["tasks"].([]any)
	task := tasks[1].(map[string]any)
	task["status"], task["result_ref"] = "ready", nil
	index["official_entrypoints"] = []any{map[string]any{
		"id": "EP-WEB-SETTINGS", "kind": "web", "route": "/settings", "url": "http://127.0.0.1:4173/settings",
	}}
	task["ui_contract"] = map[string]any{
		"surface_catalog": []any{map[string]any{"id": "SURF-SETTINGS", "entrypoint_id": "EP-WEB-SETTINGS", "surface": "settings"}},
		"usability_validation": map[string]any{
			"risk_level": "high", "methods": []any{"moderated task-based usability test"},
			"critical_tasks": []any{"Complete the settings task"}, "success_criteria": []any{"Complete without a critical error"},
			"human_review_required": true,
		},
	}
	index["tasks"] = append(tasks, map[string]any{
		"id": "T004", "objective": "deferred sibling", "status": "deferred", "dependencies": []any{},
		"user_confirmed_deferral_refs": []any{"evidence/deferral.md"},
	})
	writeTaskRuntimeFixture(t, indexPath, index)
	writeTaskRuntimeFixture(t, filepath.Join(feature, "implementation-review", "tasks", "T004.json"), map[string]any{
		"version": 1, "revision": 3, "task_id": "T004", "status": "deferred", "user_confirmed_deferral_refs": []any{"evidence/deferral.md"},
	})
	if err := os.WriteFile(filepath.Join(feature, "evidence", "deferral.md"), []byte("# Fixture deferral\n\nThe user deferred T004.\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	lifecyclePath := filepath.Join(feature, "implementation-review", "tasks", "T002.json")
	lifecycle := readImplementJSONFile(t, lifecyclePath)
	lifecycle["status"], lifecycle["revision"], lifecycle["result_ref"], lifecycle["ui_verification"] = "ready", 0, nil, nil
	lifecycle["validation"], lifecycle["changed_paths"] = []any{}, []any{}
	writeTaskRuntimeFixture(t, lifecyclePath, lifecycle)
	if err := os.Remove(filepath.Join(feature, "worker-results", "T002.json")); err != nil {
		t.Fatal(err)
	}
	statePath := filepath.Join(feature, "implementation-review", "execution-state.json")
	state := readImplementJSONFile(t, statePath)
	state["status"], state["current_task"], state["next_action"] = "executing", nil, "Start T002."
	writeTaskRuntimeFixture(t, statePath, state)
	if err := os.WriteFile(filepath.Join(feature, "implement-tracker.md"), renderImplementTaskTracker(feature, state), 0o644); err != nil {
		t.Fatal(err)
	}
	tasksPath := filepath.Join(feature, "tasks.md")
	markdown, err := os.ReadFile(tasksPath)
	if err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(tasksPath, append(markdown, []byte("- [ ] T004 deferred sibling\n")...), 0o644); err != nil {
		t.Fatal(err)
	}
	return root, feature, featureRef
}
