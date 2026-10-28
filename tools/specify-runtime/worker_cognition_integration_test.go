package main

import (
	"context"
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/closeout"
	rt "github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/runtime"
	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/store"
	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/workerdelta"
)

// Only isolated fixtures are initialized through the native store owner. These
// tests never inspect the workspace's cognition database or publish graph facts.
func workerPlannerFixture(t *testing.T, root string, paths []string) rt.Paths {
	t.Helper()
	gitRun(t, root, "init")
	gitRun(t, root, "config", "user.email", "fixture@example.test")
	gitRun(t, root, "config", "user.name", "Fixture")
	gitRun(t, root, "config", "core.longpaths", "true")
	if err := os.MkdirAll(filepath.Join(root, ".specify"), 0755); err != nil {
		t.Fatal(err)
	}
	for _, p := range paths {
		target := filepath.Join(root, filepath.FromSlash(p))
		if err := os.MkdirAll(filepath.Dir(target), 0755); err != nil {
			t.Fatal(err)
		}
		if _, err := os.Stat(target); os.IsNotExist(err) {
			if err := os.WriteFile(target, []byte("fixture retained source\n"), 0644); err != nil {
				t.Fatal(err)
			}
		}
	}
	gitRun(t, root, "add", ".")
	gitRun(t, root, "commit", "-m", "worker submission fixture")
	resolved, err := rt.ResolvePaths(root)
	if err != nil {
		t.Fatal(err)
	}
	owner, err := store.Open(resolved)
	if err != nil {
		t.Fatal(err)
	}
	defer owner.Close()
	input := store.ImportInput{GenerationID: "GEN-worker-delta", Kind: "full", SourceCommit: strings.TrimSpace(gitRun(t, root, "rev-parse", "HEAD"))}
	for _, p := range paths {
		id := p
		input.Evidence = append(input.Evidence, store.EvidenceImport{ID: "E-" + id, SourceKind: "file", SourcePath: p, CommitSHA: input.SourceCommit, Extractor: "fixture", ContentHash: "fixture"})
		input.Nodes = append(input.Nodes, store.NodeImport{ID: "N-" + id, Type: "capability", Title: p, Confidence: "verified", EvidenceIDs: []string{"E-" + id}})
		input.PathIndex = append(input.PathIndex, store.PathIndexImport{ID: "P-" + id, Path: p, NodeID: "N-" + id, Relation: "owns", Confidence: "verified", EvidenceID: "E-" + id})
	}
	if _, err := owner.ImportGeneration(context.Background(), input); err != nil {
		t.Fatal(err)
	}
	if _, _, err := owner.PublishRuntimeMetadata(context.Background(), input.GenerationID, rt.BaselineKindBrownfieldFull); err != nil {
		t.Fatal(err)
	}
	status := rt.DefaultStatus(resolved)
	status.Status = "ok"
	status.Readiness = rt.ReadyReadiness
	status.Freshness = rt.ReadyFreshness
	status.GraphReady = true
	status.ActiveGenerationID = input.GenerationID
	status.BaselineKind = rt.BaselineKindBrownfieldFull
	status.LastRefreshGitCommit = input.SourceCommit
	status.LastRefreshGitBranch = strings.TrimSpace(gitRun(t, root, "branch", "--show-current"))
	status.LastRefreshBasis = "fixture"
	if err := rt.WriteStatus(resolved, status); err != nil {
		t.Fatal(err)
	}
	return resolved
}

func workerPlanner(t *testing.T, root, workflow, scope string, paths []string) closeout.Payload {
	t.Helper()
	resolved := workerPlannerFixture(t, root, paths)
	payload, err := closeout.Run(resolved, closeout.Input{Workflow: workflow, ScopeDir: scope, ExplicitPaths: paths, ScopeMode: "explicit"})
	if err != nil {
		t.Fatal(err)
	}
	if payload.Status != "ok" || payload.PayloadDraft == nil || payload.WorkerCognition == nil {
		t.Fatalf("planner: %#v", payload)
	}
	recordWorkerOwnerEvidence(t, root, scope, payload)
	return payload
}

func recordWorkerOwnerEvidence(t *testing.T, root, scope string, payload closeout.Payload) {
	t.Helper()
	destination := os.Getenv("SPECIFY_WORKER_COGNITION_EVIDENCE")
	if destination == "" {
		return
	}
	if err := os.MkdirAll(destination, 0755); err != nil {
		t.Fatal(err)
	}
	output, err := os.MkdirTemp(destination, t.Name()+"-")
	if err != nil {
		t.Fatal(err)
	}
	manifest := map[string]string{}
	err = filepath.WalkDir(filepath.Join(root, filepath.FromSlash(scope)), func(path string, entry os.DirEntry, walkErr error) error {
		if walkErr != nil {
			return walkErr
		}
		if entry.IsDir() {
			return nil
		}
		if !strings.HasSuffix(path, ".json") {
			return nil
		}
		relative, err := filepath.Rel(root, path)
		if err != nil {
			return err
		}
		raw, err := os.ReadFile(path)
		if err != nil {
			return err
		}
		target := filepath.Join(output, "owners", relative)
		if err := os.MkdirAll(filepath.Dir(target), 0755); err != nil {
			return err
		}
		if err := os.WriteFile(target, raw, 0644); err != nil {
			return err
		}
		manifest[filepath.ToSlash(relative)] = workerdelta.Digest(raw)
		return nil
	})
	if err != nil {
		t.Fatal(err)
	}
	for name, value := range map[string]any{"planner.json": payload, "owner-digests.json": manifest} {
		raw, err := json.MarshalIndent(value, "", "  ")
		if err != nil {
			t.Fatal(err)
		}
		if err := os.WriteFile(filepath.Join(output, name), raw, 0644); err != nil {
			t.Fatal(err)
		}
	}
}

func workerDeltaFixture(task, behavior string, paths []string) map[string]any {
	return map[string]any{"schema": workerdelta.Schema, "version": 1, "identity": map[string]any{"task_id": task}, "changed_paths": stringsToAny(paths), "behavior_surfaces": []any{behavior}, "owner_surfaces": []any{map[string]any{"owner": "writer", "counter": json.Number("900719925474099312345")}}, "consumer_surfaces": []any{"reader"}, "interfaces": []any{map[string]any{"name": "readback", "nested": []any{true, nil}}}, "generated_surfaces": []any{map[string]any{"owner": "generator", "path": paths[0]}}, "state_contracts": []any{map[string]any{"state": "retained"}}, "verification_evidence": []any{map[string]any{"command": "required check", "result": "passed", "artifact": "raw-evidence"}}, "evidence_refs": []any{map[string]any{"claim_ref": "C-shared"}}, "invalidated_claim_refs": []any{"C-shared"}, "known_unknowns": []any{"source reconciliation remains advisory"}, "confidence_notes": []any{"candidate observed"}}
}

func readWorkerStored(t *testing.T, path string) map[string]any {
	t.Helper()
	raw, err := os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}
	value, err := workerdelta.Decode(raw)
	if err != nil {
		t.Fatal(err)
	}
	if err := workerdelta.ValidateStored(value); err != nil {
		t.Fatal(err)
	}
	return value
}

func TestWorkerCognitionImplementNativeSubmitReadPlanner(t *testing.T) {
	root, feature, scope := newImplementedTaskRecoveryFixture(t)
	assertTaskRuntimeCommandOK(t, []string{"implement", "task-reopen", "--feature-dir", scope, "--task-id", "T002", "--expected-task-revision", "2", "--expected-workflow-revision", "7", "--reason", "Replace incomplete evidence", "--evidence", "required check absent", "--format", "json"})
	index := readImplementJSONFile(t, filepath.Join(feature, "task-index.json"))
	task := index["tasks"].([]any)[1].(map[string]any)
	task["expected_write_scope"] = []any{"src/t002.go", "src/old.go", "src/new.go"}
	writeTaskRuntimeFixture(t, filepath.Join(feature, "task-index.json"), index)
	bindImplementTestWork(t, root, scope, []string{"src/t002.go", "src/old.go", "src/new.go"})
	if err := os.MkdirAll(filepath.Join(root, ".specify", "templates"), 0755); err != nil {
		t.Fatal(err)
	}
	writeTaskRuntimeFixture(t, filepath.Join(root, ".specify", "templates", "task-packet-template.json"), map[string]any{"ui_contract": map[string]any{"fidelity_level": "none"}})
	started := assertTaskRuntimeCommandOK(t, []string{"implement", "task-start", "--feature-dir", scope, "--task-id", "T002", "--execution-mode", "leader-direct", "--format", "json"})
	_ = started
	compiled := assertTaskRuntimeCommandOK(t, []string{"implement", "packet-compile", "--feature-dir", scope, "--task-id", "T002", "--format", "json"})
	packet, err := workerdelta.Decode(mustReadWorkerBytes(t, filepath.Join(root, filepath.FromSlash(compiled["path"].(string)))))
	if err != nil {
		t.Fatal(err)
	}
	if !workerdelta.Same(packet["cognition_delta_contract"], workerdelta.Contract("T002")) {
		t.Fatal("packet contract missing")
	}
	merge := func(raw string, want bool) {
		t.Helper()
		code, env := runTaskRuntimeCommand(t, []string{"implement", "result-merge", "--feature-dir", scope, "--task-id", "T002", "--result-json", raw, "--format", "json"})
		if (code == 0) != want {
			t.Fatalf("merge %d %#v", code, env)
		}
	}
	merge("{bad", false)
	failedDelta := workerDeltaFixture("T002", "failed version", []string{"src/old.go", "src/new.go"})
	failedDelta["path_changes"] = []any{map[string]any{"kind": "renamed", "old_path": "src/old.go", "new_path": "src/new.go"}}
	merge(marshalJSONForCLI(t, map[string]any{"task_id": "T002", "status": "failed", "cognition_delta": failedDelta, "validation_results": []any{map[string]any{"command": "required check", "status": "failed"}}, "blockers": []any{"failed readback"}}), true)
	merge(marshalJSONForCLI(t, map[string]any{"task_id": "T002", "status": "blocked", "changed_paths": []any{"src/t002.go"}, "behavior_surfaces": []any{"blocked version"}, "blockers": []any{"missing fixture"}}), true)
	lifeBefore := readImplementJSONFile(t, filepath.Join(feature, "implementation-review", "tasks", "T002.json"))
	merge(`{"task_id":"T002","status":"success","changed_files":["src/rejected-a"],"changed_paths":["src/rejected-b"],"behavior_surfaces":["rejected candidate version"]}`, false)
	lifeAfter := readImplementJSONFile(t, filepath.Join(feature, "implementation-review", "tasks", "T002.json"))
	if lifeBefore["revision"] != lifeAfter["revision"] || lifeAfter["status"] != "blocked" {
		t.Fatal("rejection promoted lifecycle")
	}
	finalDelta := workerDeltaFixture("T002", "accepted version", []string{"src/t002.go"})
	merge(marshalJSONForCLI(t, map[string]any{"task_id": "T002", "status": "success", "cognition_delta": finalDelta, "validation_results": []any{map[string]any{"command": "required check", "status": "passed"}}, "blockers": []any{}}), true)
	assertTaskRuntimeCommandOK(t, []string{"implement", "task-accept", "--feature-dir", scope, "--task-id", "T002", "--format", "json"})
	stored := readWorkerStored(t, filepath.Join(feature, "worker-results", "T002.json"))
	if len(stored["submission_history"].([]any)) != 6 {
		t.Fatalf("history %v", stored["submission_history"])
	}
	payload := workerPlanner(t, root, "implement", scope, []string{"src/t002.go", "src/old.go", "src/new.go", "src/rejected-a", "src/rejected-b"})
	if len(payload.WorkerCognition.AcceptedDeltas) != 1 || len(payload.WorkerCognition.Events) != 7 {
		t.Fatalf("read stored attempts %#v", payload.WorkerCognition)
	}
	if !workerdelta.Same(payload.PayloadDraft.BehaviorSurfaces, []string{"accepted version"}) {
		t.Fatalf("unaccepted semantics promoted %v", payload.PayloadDraft.BehaviorSurfaces)
	}
	retainedCandidate := false
	for _, event := range payload.WorkerCognition.Events {
		if event.Status == "rejected" && workerdelta.Same(event.CandidateInput["behavior_surfaces"], []any{"rejected candidate version"}) {
			retainedCandidate = true
		}
	}
	if !retainedCandidate {
		t.Fatal("rejected semantic candidate discarded from planner")
	}
	raw, _ := json.Marshal(payload.PayloadDraft)
	if !strings.Contains(string(raw), "900719925474099312345") || len(payload.WorkerCognition.Conflicts) < 1 || len(payload.WorkerCognition.KnownUnknowns) < 1 {
		t.Fatal("lost facets/conflicts/unaccounted history")
	}
	lifeAfter = readImplementJSONFile(t, filepath.Join(feature, "implementation-review", "tasks", "T002.json"))
	if len(lifeAfter["changed_paths"].([]any)) != 5 || len(lifeAfter["cognition_pending_submission_sequences"].([]any)) != 1 {
		t.Fatal("lifecycle retained accounting incomplete")
	}
	// A dependent second worker edits the same source serially. Both accepted
	// semantic versions and their shared claim remain separate in the draft.
	index = readImplementJSONFile(t, filepath.Join(feature, "task-index.json"))
	index["tasks"].([]any)[2].(map[string]any)["expected_write_scope"] = []any{"src/t002.go"}
	writeTaskRuntimeFixture(t, filepath.Join(feature, "task-index.json"), index)
	writeTaskRuntimeFixture(t, filepath.Join(root, ".specify", "templates", "task-lifecycle-template.json"), map[string]any{"version": 1, "revision": 0, "status": "pending", "validation": []any{}, "blockers": []any{}, "ui_verification": map[string]any{"applicable": false}})
	assertTaskRuntimeCommandOK(t, []string{"implement", "task-start", "--feature-dir", scope, "--task-id", "T003", "--execution-mode", "leader-direct", "--format", "json"})
	second := map[string]any{"task_id": "T003", "status": "success", "cognition_delta": workerDeltaFixture("T003", "second worker accepted version", []string{"src/t002.go"}), "validation_results": []any{map[string]any{"command": "dependent check", "status": "passed"}}, "blockers": []any{}}
	assertTaskRuntimeCommandOK(t, []string{"implement", "result-merge", "--feature-dir", scope, "--task-id", "T003", "--result-json", marshalJSONForCLI(t, second), "--format", "json"})
	assertTaskRuntimeCommandOK(t, []string{"implement", "task-accept", "--feature-dir", scope, "--task-id", "T003", "--format", "json"})
	resolved, _ := rt.ResolvePaths(root)
	joined, err := closeout.Run(resolved, closeout.Input{Workflow: "implement", ScopeDir: scope, ExplicitPaths: []string{"src/t002.go", "src/old.go", "src/new.go", "src/rejected-a", "src/rejected-b"}})
	if err != nil {
		t.Fatal(err)
	}
	if joined.PayloadDraft == nil || len(joined.WorkerCognition.AcceptedDeltas) != 2 || !workerdelta.Same(joined.PayloadDraft.BehaviorSurfaces, []string{"accepted version", "second worker accepted version"}) {
		t.Fatalf("serial workers overwritten %#v", joined)
	}
	shared := false
	for _, conflict := range joined.WorkerCognition.Conflicts {
		if conflict.Kind == "shared_claim_versions" && conflict.Key == "C-shared" {
			shared = true
		}
	}
	if !shared {
		t.Fatal("shared claim versions lost")
	}
	recordWorkerOwnerEvidence(t, root, scope, joined)
}

func mustReadWorkerBytes(t *testing.T, path string) []byte {
	t.Helper()
	raw, err := os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}
	return raw
}

func TestWorkerCognitionQuickNativeSubmitReadPlannerAndAcceptanceDrift(t *testing.T) {
	root, workspace, id := newQuickOptimizationFixture(t)
	writeTaskRuntimeFixture(t, filepath.Join(root, ".specify", "integration.json"), map[string]any{"integration": "codex"})
	env := runScriptDomainEnvelope(t, runQuick, []string{"--project-root", root, "item-start", id, "--item", "Q1"})
	if env.Status != "ok" {
		t.Fatalf("start %v", env.Blockers)
	}
	if !workerdelta.Same(env.Data["packet"].(map[string]any)["cognition_delta_contract"], workerdelta.Contract("Q1")) {
		t.Fatal("Quick packet contract missing")
	}
	submit := func(result map[string]any, want bool) {
		t.Helper()
		code, payload := runResultInProject(t, root, []string{"submit", "--command", "quick", "--workspace", workspace, "--lane-id", "Q1", "--result-json", marshalJSONForCLI(t, result)})
		if (code == 0) != want {
			t.Fatalf("submit %d %v", code, payload)
		}
	}
	submit(map[string]any{"task_id": "Q1", "status": "failed", "changed_paths": []any{"src/a.go"}, "behavior_surfaces": []any{"failed quick"}}, true)
	submit(map[string]any{"task_id": "Q1", "status": "success", "changed_files": []any{"src/rejected-a"}, "changed_paths": []any{"src/rejected-b"}}, false)
	result := map[string]any{"task_id": "Q1", "status": "success", "summary": "readback passed", "cognition_delta": workerDeltaFixture("Q1", "accepted quick", []string{"src/a.go"}), "validation_results": []any{map[string]any{"command": "required check", "status": "passed"}}}
	submit(result, true)
	env = runScriptDomainEnvelope(t, runQuick, []string{"--project-root", root, "item-accept", id, "--item", "Q1", "--evidence", "readback verified"})
	if env.Status != "ok" {
		t.Fatalf("accept %v", env.Blockers)
	}
	scope := projectRelativeSlash(root, workspace)
	payload := workerPlanner(t, root, "quick", scope, []string{"src/a.go", "src/rejected-a", "src/rejected-b"})
	if len(payload.WorkerCognition.Events) != 3 || len(payload.WorkerCognition.AcceptedDeltas) != 1 || len(payload.WorkerCognition.Conflicts) == 0 {
		t.Fatalf("Quick stored history %#v", payload.WorkerCognition)
	}
	if !workerdelta.Same(payload.PayloadDraft.BehaviorSurfaces, []string{"accepted quick"}) {
		t.Fatal("Quick candidate promoted")
	}
	submit(result, true)
	resolved, _ := rt.ResolvePaths(root)
	drift, err := closeout.Run(resolved, closeout.Input{Workflow: "quick", ScopeDir: scope, ExplicitPaths: []string{"src/a.go", "src/rejected-a", "src/rejected-b"}})
	if err != nil {
		t.Fatal(err)
	}
	if len(drift.WorkerCognition.AcceptedDeltas) != 0 {
		t.Fatal("old Quick acceptance applied to new submission")
	}
	env = runScriptDomainEnvelope(t, runQuick, []string{"--project-root", root, "item-accept", id, "--item", "Q1", "--evidence", "old proof"})
	if env.Status == "ok" {
		t.Fatal("acceptance drift ignored")
	}
}

func TestWorkerCognitionE2ENativeSubmitReviewAcceptReadPlannerAndReopen(t *testing.T) {
	root := e2eTestInit(t, "execution")
	input := e2eTestPrepareSubmission(t, root, "S1", "pass")
	worker := input["worker_result"].(map[string]any)
	worker["cognition_delta"] = workerDeltaFixture("S1", "accepted E2E v1", []string{"tests/e2e/s1.md"})
	bad := workerdelta.Clone(worker)
	bad["changed_paths"] = []any{"tests/e2e/rejected.md"}
	input["worker_result"] = bad
	code, _ := e2eTestCall(t, root, "task-submit", "--run-id", "run-1", "--expected-revision", e2eTestRevision(t, root), "--task-id", "S1", "--worker-id", "worker-S1", "--result-json", e2eTestJSON(t, input))
	if code == 0 {
		t.Fatal("E2E conflict accepted")
	}
	input["worker_result"] = worker
	packetSHA := input["packet_sha256"]
	input["packet_sha256"] = "wrong-packet"
	wrongPacketJSON := e2eTestJSON(t, input)
	code, _ = e2eTestCall(t, root, "task-submit", "--run-id", "run-1", "--expected-revision", e2eTestRevision(t, root), "--task-id", "S1", "--worker-id", "worker-S1", "--result-json", wrongPacketJSON)
	if code == 0 {
		t.Fatal("E2E wrong packet accepted")
	}
	service := e2eService{projectRoot: root, runID: "run-1", rootRef: ".planning/e2e/run-1", observed: map[string]string{}}
	state, err := service.readState()
	if err != nil {
		t.Fatal(err)
	}
	var rejected map[string]any
	if err := service.readSnapshot(state.Tasks[0].History[len(state.Tasks[0].History)-1], &rejected); err != nil {
		t.Fatal(err)
	}
	if rejected["submission_input_json"] != wrongPacketJSON || rejected["submission_input_sha256"] != workerdelta.Digest([]byte(wrongPacketJSON)) {
		t.Fatal("E2E rejected exact outer submission was lost")
	}
	firstRejectedRef := state.Tasks[0].History[len(state.Tasks[0].History)-1]
	code, _ = e2eTestCall(t, root, "task-submit", "--run-id", "run-1", "--expected-revision", e2eTestRevision(t, root), "--task-id", "S1", "--worker-id", "worker-S1", "--result-json", wrongPacketJSON)
	if code == 0 {
		t.Fatal("repeated E2E wrong packet accepted")
	}
	state, err = service.readState()
	if err != nil {
		t.Fatal(err)
	}
	if state.Tasks[0].History[len(state.Tasks[0].History)-1] == firstRejectedRef {
		t.Fatal("repeated E2E submission version overwritten")
	}
	input["packet_sha256"] = packetSHA
	input["outcome"] = "unrecognized-outcome"
	code, _ = e2eTestCall(t, root, "task-submit", "--run-id", "run-1", "--expected-revision", e2eTestRevision(t, root), "--task-id", "S1", "--worker-id", "worker-S1", "--result-json", e2eTestJSON(t, input))
	if code == 0 {
		t.Fatal("E2E unknown outcome accepted")
	}
	input["outcome"] = "pass"
	e2eTestMutation(t, root, "task-submit", "--task-id", "S1", "--worker-id", "worker-S1", "--result-json", e2eTestJSON(t, input))
	e2eTestReviewAndAccept(t, root, "S1")
	scope := ".planning/e2e/run-1"
	payload := workerPlanner(t, root, "e2e", scope, []string{"tests/e2e/s1.md", "tests/e2e/rejected.md"})
	if len(payload.WorkerCognition.AcceptedDeltas) != 1 || len(payload.WorkerCognition.Events) != 5 || !workerdelta.Same(payload.PayloadDraft.BehaviorSurfaces, []string{"accepted E2E v1"}) {
		t.Fatalf("E2E handoff %#v", payload.WorkerCognition)
	}
	e2eTestFile(t, root, "tests/e2e/reopen-evidence.txt", "v1 behavior requires correction")
	e2eTestMutation(t, root, "reopen", "--task-id", "S1", "--leader-id", "leader", "--reason", "behavior corrected", "--evidence-ref", "tests/e2e/reopen-evidence.txt")
	input = e2eTestPrepareSubmission(t, root, "S1", "pass")
	worker = input["worker_result"].(map[string]any)
	worker["cognition_delta"] = workerDeltaFixture("S1", "accepted E2E v2", []string{"tests/e2e/s1.md"})
	e2eTestMutation(t, root, "task-submit", "--task-id", "S1", "--worker-id", "worker-S1", "--result-json", e2eTestJSON(t, input))
	e2eTestReviewAndAccept(t, root, "S1")
	resolved, _ := rt.ResolvePaths(root)
	payload, err = closeout.Run(resolved, closeout.Input{Workflow: "e2e", ScopeDir: scope, ExplicitPaths: []string{"tests/e2e/s1.md", "tests/e2e/rejected.md"}})
	if err != nil {
		t.Fatal(err)
	}
	if len(payload.WorkerCognition.AcceptedDeltas) != 1 || len(payload.WorkerCognition.Events) != 6 || !workerdelta.Same(payload.PayloadDraft.BehaviorSurfaces, []string{"accepted E2E v2"}) {
		t.Fatalf("E2E attempt overwrite %#v", payload.WorkerCognition)
	}
	recordWorkerOwnerEvidence(t, root, scope, payload)
	outputPath := filepath.Join(root, "tests", "e2e", "s1.md")
	oldOutput := mustReadWorkerBytes(t, outputPath)
	e2eTestFile(t, root, "tests/e2e/s1.md", "post-acceptance source drift")
	drift, err := closeout.Run(resolved, closeout.Input{Workflow: "e2e", ScopeDir: scope, ExplicitPaths: []string{"tests/e2e/s1.md", "tests/e2e/rejected.md"}})
	if err != nil {
		t.Fatal(err)
	}
	if len(drift.WorkerCognition.AcceptedDeltas) != 0 {
		t.Fatal("E2E stale accepted output promoted")
	}
	if err := os.WriteFile(outputPath, oldOutput, 0644); err != nil {
		t.Fatal(err)
	}
}

func TestWorkerCognitionCASRefusesLostHistoryAndImplementCrossChannelAcceptance(t *testing.T) {
	root, feature, scope := newImplementedTaskRecoveryFixture(t)
	path := filepath.Join(feature, "worker-results", "T002.json")
	before, err := os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}
	raw := []byte(`{"task_id":"T002","status":"success","changed_paths":["src/t002.go"]}`)
	normalized, err := normalizeWorkerTaskResult(raw)
	if err != nil {
		t.Fatal(err)
	}
	if _, err := persistWorkerResultSubmission(root, path, normalized, raw, "", "", 0, []fileTransactionPrecondition{{Path: filepath.Join(feature, "task-index.json"), ExpectedSHA256: strings.Repeat("0", 64)}}); err == nil {
		t.Fatal("stale owner CAS accepted")
	}
	after, _ := os.ReadFile(path)
	if string(before) != string(after) {
		t.Fatal("CAS failure changed history")
	}
	lifePath := filepath.Join(feature, "implementation-review", "tasks", "T002.json")
	life := readImplementJSONFile(t, lifePath)
	life["validation"] = []any{map[string]any{"command": "required check", "status": "passed"}}
	writeTaskRuntimeFixture(t, lifePath, life)
	if _, err := persistWorkerResultSubmission(root, path, normalized, raw, "", "", 0, nil); err != nil {
		t.Fatal(err)
	}
	code, env := runTaskRuntimeCommand(t, []string{"implement", "task-accept", "--feature-dir", scope, "--task-id", "T002", "--format", "json"})
	if code == 0 || !strings.Contains(env.Summary, "exact current lifecycle") {
		t.Fatalf("cross-channel proof accepted %d %#v", code, env)
	}
}
