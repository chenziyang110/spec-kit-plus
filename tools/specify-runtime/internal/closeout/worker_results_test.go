package closeout

import (
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/workerdelta"
)

func writeWorkerOwner(t *testing.T, root, ref string, value any) {
	t.Helper()
	raw, err := json.Marshal(value)
	if err != nil {
		t.Fatal(err)
	}
	writeCloseoutFile(t, root, ref, string(raw))
}

func TestWorkerCollectorRejectsMalformedCanonicalTaskCollections(t *testing.T) {
	for _, workflow := range []string{"sp-implement", "sp-e2e", "sp-quick"} {
		t.Run(workflow, func(t *testing.T) {
			root := t.TempDir()
			scope := ".specify/features/test"
			ref := scope + "/task-index.json"
			value := map[string]any{"tasks": map[string]any{}}
			if workflow == "sp-e2e" {
				scope = ".planning/e2e/run"
				ref = scope + "/state.json"
			}
			if workflow == "sp-quick" {
				scope = ".planning/quick/run"
				ref = scope + "/confirmation.json"
				value = map[string]any{"execution": map[string]any{"work_item_status": map[string]any{}}}
			}
			writeWorkerOwner(t, root, ref, value)
			if _, err := collectWorkerResults(root, workflow, scope); err == nil {
				t.Fatal("damaged owner silently consumed as empty history")
			}
			if workflow != "sp-quick" {
				writeWorkerOwner(t, root, ref, map[string]any{"tasks": []any{map[string]any{}}})
				if _, err := collectWorkerResults(root, workflow, scope); err == nil {
					t.Fatal("missing task identity silently skipped")
				}
			}
		})
	}
}

func TestWorkerCollectorRetainsRenameBoundaryAndRejectsTamperedHistory(t *testing.T) {
	root, paths := initCloseoutFixture(t)
	scope := ".specify/features/001-worker"
	ref := scope + "/worker-results/T1.json"
	lifeRef := scope + "/implementation-review/tasks/T1.json"
	candidate := map[string]any{"task_id": "T1", "status": "success", "validation_results": []any{}, "blockers": []any{}, "cognition_delta": map[string]any{"schema": workerdelta.Schema, "version": 1, "changed_paths": []any{"src/old.go", "src/app.go"}, "path_changes": []any{map[string]any{"kind": "renamed", "old_path": "src/old.go", "new_path": "src/app.go"}}, "behavior_surfaces": []any{"save"}}}
	stored, err := workerdelta.Append(nil, candidate, nil, "success", "", ref, "runtime-attempt", 1)
	if err != nil {
		t.Fatal(err)
	}
	if err := workerdelta.Accept(stored, lifeRef, 2); err != nil {
		t.Fatal(err)
	}
	writeWorkerOwner(t, root, ref, stored)
	writeWorkerOwner(t, root, scope+"/task-index.json", map[string]any{"tasks": []any{map[string]any{"id": "T1", "status": "accepted"}}})
	writeWorkerOwner(t, root, lifeRef, map[string]any{"revision": 2, "status": "accepted", "result_ref": "worker-results/T1.json", "validation": []any{}, "blockers": []any{}})
	before, err := os.ReadFile(filepath.Join(root, filepath.FromSlash(ref)))
	if err != nil {
		t.Fatal(err)
	}
	payload, err := Run(paths, Input{Workflow: "implement", ScopeDir: scope, ExplicitPaths: []string{"src/app.go"}})
	if err != nil {
		t.Fatal(err)
	}
	if payload.Status != "blocked" || len(payload.ApplyArgv) != 0 || payload.WorkerCognition == nil || len(payload.WorkerCognition.ChangedPaths) != 2 || len(payload.WorkerCognition.AcceptedDeltas) != 1 {
		t.Fatalf("rename denominator/authority lost %#v", payload)
	}
	if !workerdelta.Same(payload.PayloadDraft.Boundary.WorkflowOwnedPaths, []string{"src/app.go"}) {
		t.Fatal("reported path expanded Work boundary")
	}
	after, _ := os.ReadFile(filepath.Join(root, filepath.FromSlash(ref)))
	if string(before) != string(after) {
		t.Fatal("read-only planner changed result history")
	}
	stored["submission_history"].([]any)[0].(map[string]any)["result_json"] = "{}"
	writeWorkerOwner(t, root, ref, stored)
	payload, err = Run(paths, Input{Workflow: "implement", ScopeDir: scope, ExplicitPaths: []string{"src/app.go", "src/old.go"}})
	if err != nil {
		t.Fatal(err)
	}
	if payload.Status != "blocked" || len(payload.ApplyArgv) != 0 || !strings.Contains(strings.Join(payload.Errors, " "), "digest mismatch") {
		t.Fatalf("tampered history consumed %#v", payload)
	}
}
