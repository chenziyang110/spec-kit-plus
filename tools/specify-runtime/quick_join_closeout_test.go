package main

import (
	"bytes"
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"

	rt "github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/runtime"
)

func TestQuickJoinRecoversCurrentManualSingleItemCloseout(t *testing.T) {
	root, workspace, id := newUnboundQuickOptimizationFixture(t)
	scope := projectRelativeSlash(root, workspace)
	r3SeedGraph(t, root, []string{"src/a.go"})
	writeTaskRuntimeFixture(t, filepath.Join(root, ".specify", "integration.json"), map[string]any{"integration": "codex"})
	const activityID = "manual-quick-q1"
	claims := []string{"src/a.go", scope, ".planning/quick/index.json", ".specify/project-cognition"}
	code, announced := invokeCoordinationCLI(t,
		"execution", "announce", "--project-root", root, "--activity-id", activityID,
		"--workflow", "quick", "--subject-id", id, "--item-id", "Q1",
		"--summary", "manual fixture", "--agent-id", "leader", "--adapter-id", "codex",
		"--planned-write-scope-json", marshalWorkBoardCLIJSON(t, claims), "--format", "json",
	)
	announcement := requireObject(t, announced, "data")
	if code != 0 || announcement["quick_binding_scope"] != "item" ||
		!strings.Contains(stringValue(announcement["quick_joined_work_usage"]), "--subject-id "+id+" ") ||
		strings.Contains(stringValue(announcement["quick_joined_work_usage"]), "--item-id") {
		t.Fatalf("missing actionable item-scope announcement: %#v", announced)
	}
	registration := requireObject(t, announcement, "execution_activity")
	workID := stringValue(registration["work_id"])
	guarded := guardExecutionCLI(t, root, registration, executionOverviewCLI(t, root, workID), claims, nil)
	t.Setenv("SPECIFY_WORK_ID", workID)
	t.Setenv("SPECIFY_WORK_FENCE", executionJSONNumberString(guarded["fence"]))
	env := runScriptDomainEnvelope(t, runQuick, []string{"--project-root", root, "item-start", id, "--item", "Q1"})
	if env.Status != "ok" {
		t.Fatalf("start item: %#v", env)
	}
	source := filepath.Join(root, "src", "a.go")
	mustWriteScriptDomainTest(t, source, "package fixture\n// current accepted result\n")
	result := map[string]any{
		"task_id": "Q1", "status": "success", "summary": "accepted source",
		"cognition_delta":    workerDeltaFixture("Q1", "accepted source", []string{"src/a.go"}),
		"validation_results": []any{map[string]any{"command": "required check", "status": "passed"}},
	}
	if code, got := runResultInProject(t, root, []string{"submit", "--command", "quick", "--workspace", workspace, "--lane-id", "Q1", "--result-json", marshalJSONForCLI(t, result)}); code != 0 {
		t.Fatal(got)
	}
	env = runScriptDomainEnvelope(t, runQuick, []string{"--project-root", root, "item-accept", id, "--item", "Q1", "--evidence", "read back item changes"})
	if env.Status != "ok" {
		t.Fatalf("accept item: %#v", env)
	}
	draft := r3Begin(t, root, scope, "quick", workID, nil, nil)
	if _, captured := draft.Source[quickDerivedIndexRef]; captured {
		t.Fatal("new native binding treated the derived index as product source")
	}
	// Exercise an existing binding shape from before the fix. It included a
	// snapshot of the index, which Quick status refreshes during recovery.
	indexSnapshot, err := closeoutBindingSnapshot(root, []string{quickDerivedIndexRef})
	if err != nil {
		t.Fatal(err)
	}
	draft.Source[quickDerivedIndexRef] = indexSnapshot[quickDerivedIndexRef]
	draft.WriteScope = normalizedCloseoutPaths(append(draft.WriteScope, quickDerivedIndexRef))
	draft.Digest = closeoutBindingDigest(draft)
	if err := writeScriptJSONFile(filepath.Join(closeoutBindingDir(root), draft.ID+".json"), draft); err != nil {
		t.Fatal(err)
	}
	proof := r3Seal(t, root, draft)
	if proof.ItemID != "Q1" {
		t.Fatalf("fixture requires a native item proof, got %#v", proof)
	}
	raw := marshalJSONForCLI(t, map[string]any{
		"workflow": proof.Workflow, "reason": "finalize item", "changed_paths": proof.OwnedDelta, "scope_paths": proof.OwnedDelta,
		"boundary":     map[string]any{"scope_mode": "explicit", "workflow_owned_paths": proof.OwnedDelta},
		"verification": []map[string]string{{"command": "fixture observed check", "result": "passed"}},
	})
	var out bytes.Buffer
	if code := runCognitionCloseoutApplyCLIWithInput([]string{"--project-root", root, "--workflow", "quick", "--scope-dir", scope, "--payload-json", "-", "--binding-id", proof.ID}, strings.NewReader(raw), &out); code != 0 {
		t.Fatalf("apply item proof: %s", out.String())
	}
	var applied Envelope
	if err := json.Unmarshal(out.Bytes(), &applied); err != nil {
		t.Fatal(err)
	}
	if applied.Data["allowed_close"] != false || applied.Data["binding_scope"] != "item" || len(applied.NextArgv) == 0 {
		t.Fatalf("item receipt incorrectly advertised terminal close: %+v", applied)
	}
	status := runScriptDomainEnvelope(t, runQuick, []string{"--project-root", root, "status", id})
	statusGate, _ := status.Data["cognition_closeout"].(map[string]any)
	if statusGate["blocked_reason"] != "terminal_scope_requires_joined_binding" {
		t.Fatalf("status lost the item-scoped recovery: %+v", status)
	}
	if env := runScriptDomainEnvelope(t, runQuick, []string{"--project-root", root, "close", id, "resolved"}); env.Status == "ok" {
		t.Fatal("unjoined item could close Quick")
	}

	original, err := os.ReadFile(source)
	if err != nil {
		t.Fatal(err)
	}
	paths, err := rt.ResolvePaths(root)
	if err != nil {
		t.Fatal(err)
	}
	graphBefore, err := os.ReadFile(paths.DatabasePath)
	if err != nil {
		t.Fatal(err)
	}
	receiptBefore, err := os.ReadFile(mutationCognitionReceiptPath(workspace))
	if err != nil {
		t.Fatal(err)
	}
	joinArgs := applied.NextArgv[2:]
	badFence := append([]string(nil), joinArgs...)
	for i := range badFence {
		if badFence[i] == "--fence" {
			badFence[i+1] = "99"
		}
	}
	if env := runScriptDomainEnvelope(t, runQuick, badFence); env.Status == "ok" {
		t.Fatal("wrong work fence joined prior evidence")
	}
	mustWriteScriptDomainTest(t, source, "unverified bytes\n")
	if env := runScriptDomainEnvelope(t, runQuick, joinArgs); env.Status == "ok" {
		t.Fatal("stale source joined prior evidence")
	}
	currentReceipt, err := os.ReadFile(mutationCognitionReceiptPath(workspace))
	if err != nil || !bytes.Equal(receiptBefore, currentReceipt) {
		t.Fatal("refused recovery rewrote the receipt")
	}
	if err := os.WriteFile(source, original, 0o644); err != nil {
		t.Fatal(err)
	}
	joined := runScriptDomainEnvelope(t, runQuick, joinArgs)
	gate, _ := joined.Data["cognition_closeout"].(map[string]any)
	if joined.Status != "ok" || gate["allowed_close"] != true || gate["binding_scope"] != "joined" {
		t.Fatalf("join did not retain the current proof: %+v", joined)
	}
	persisted, err := loadMutationCognitionReceipt(workspace)
	if err != nil || persisted.QuickJoinedBinding == nil || persisted.StrongBinding.Digest != proof.Digest {
		t.Fatalf("join did not persist its relation to the original sealed item: %#v %v", persisted, err)
	}
	graphAfter, err := os.ReadFile(paths.DatabasePath)
	if err != nil || !bytes.Equal(graphBefore, graphAfter) {
		t.Fatal("joining evidence rewrote the project graph")
	}
	if env := runScriptDomainEnvelope(t, runQuick, joined.NextArgv[2:]); env.Status != "ok" {
		t.Fatalf("joined proof did not close Quick: %+v", env)
	}
	code, currentWork := invokeCoordinationCLI(t, "execution", "show", activityID, "--project-root", root, "--format", "json")
	if code != 0 {
		t.Fatalf("read current Work: %#v", currentWork)
	}
	registration = requireObject(t, requireObject(t, currentWork, "data"), "execution_activity")
	code, completed := invokeCoordinationCLI(t,
		"execution", "complete", activityID, "--project-root", root,
		"--expected-revision", executionJSONNumberString(registration["work_revision"]),
		"--fence", executionJSONNumberString(registration["fence"]),
		"--validation-json", `[{"command":"fixture observed check","result":"passed"}]`,
		"--reason", "complete joined Quick task", "--format", "json",
	)
	if code != 0 || completed["status"] != "ok" {
		t.Fatalf("manual Work could not complete: %#v", completed)
	}
	archived := runScriptDomainEnvelope(t, runQuick, []string{"--project-root", root, "archive", id})
	if archived.Status != "ok" {
		t.Fatalf("finished Quick could not archive: %+v", archived)
	}
}
