package main

import (
	"bytes"
	"encoding/json"
	"path/filepath"
	"testing"

	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/workerdelta"
)

func TestCognitionPublicPlannerPreservesAcceptedWorkerNumbers(t *testing.T) {
	root, workspace, id := newQuickOptimizationFixture(t)
	t.Chdir(root)
	writeTaskRuntimeFixture(t, filepath.Join(root, ".specify", "integration.json"), map[string]any{"integration": "codex"})
	run := func(args ...string) map[string]any {
		t.Helper()
		var out, errOut bytes.Buffer
		if code := Run(args, &out, &errOut, "test"); code != 0 {
			t.Fatalf("native command %v: exit%d %s %s", args, code, out.String(), errOut.String())
		}
		result, err := workerdelta.Decode(out.Bytes())
		if err != nil {
			t.Fatal(err)
		}
		return result
	}
	run("quick", "--project-root", root, "item-start", id, "--item", "Q1", "--format", "json")
	const counter = "9007199254740993123456789"
	delta := workerDeltaFixture("Q1", "verified <>&中文", []string{"src/a.go"})
	delta["verification_evidence"] = []any{map[string]any{"observed": map[string]any{"count": json.Number(counter)}}}
	input := marshalJSONForCLI(t, map[string]any{
		"task_id": "Q1", "status": "success", "cognition_delta": delta,
		"validation_results": []any{map[string]any{"command": "required check", "status": "passed"}},
	})
	run("result", "submit", "--command", "quick", "--workspace", workspace, "--lane-id", "Q1", "--result-json", input, "--format", "json")
	run("quick", "--project-root", root, "item-accept", id, "--item", "Q1", "--evidence", "independent readback", "--format", "json")
	stored := readWorkerStored(t, filepath.Join(workspace, "worker-results", "Q1.json"))
	storedBytes, err := json.Marshal(stored)
	if err != nil || !bytes.Contains(storedBytes, []byte(counter)) {
		t.Fatalf("canonical owner lost original number: %s %v", storedBytes, err)
	}
	workerPlannerFixture(t, root, []string{"src/a.go"})
	result := run("cognition", "closeout-plan", "--workflow", "sp-quick", "--scope-dir", projectRelativeSlash(root, workspace), "--scope-mode", "explicit", "--changed-path", "src/a.go", "--format", "json")
	data := result["data"].(map[string]any)
	draft := data["payload_draft"].(map[string]any)
	if !workerdelta.Same(draft["behavior_surfaces"], []any{"verified <>&中文"}) {
		t.Fatalf("accepted semantic text changed: %#v", draft)
	}
	draftBytes, err := json.Marshal(draft)
	if err != nil || !bytes.Contains(draftBytes, []byte(counter)) {
		t.Fatalf("public planner rounded accepted worker number: %s %v", draftBytes, err)
	}
}
