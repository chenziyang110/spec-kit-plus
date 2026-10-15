package main

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"

	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/runcontrol"
	rt "github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/runtime"
	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/store"
)

func r3SeedGraph(t *testing.T, root string, refs []string) {
	t.Helper()
	paths, err := rt.ResolvePaths(root)
	if err != nil {
		t.Fatal(err)
	}
	st, err := store.Open(paths)
	if err != nil {
		t.Fatal(err)
	}
	input := store.ImportInput{GenerationID: "GEN-r3", Kind: "full", SourceCommit: "fixture"}
	coverage := []any{}
	for _, ref := range refs {
		id := closeoutIntentDigest(ref)
		input.Evidence = append(input.Evidence, store.EvidenceImport{ID: "E-" + id, SourceKind: "file", SourcePath: ref, CommitSHA: "fixture", Extractor: "test", ContentHash: "fixture"})
		input.Nodes = append(input.Nodes, store.NodeImport{ID: "N-" + id, Type: "capability", Title: ref, Confidence: "verified", EvidenceIDs: []string{"E-" + id}})
		input.PathIndex = append(input.PathIndex, store.PathIndexImport{ID: "P-" + id, Path: ref, NodeID: "N-" + id, Relation: "owns", Confidence: "verified", EvidenceID: "E-" + id})
		input.Aliases = append(input.Aliases, store.AliasImport{ID: "A-" + id, Alias: ref, NormalizedAlias: ref, TargetType: "node", TargetID: "N-" + id, Source: "node_title", Confidence: "verified", EvidenceID: "E-" + id})
		coverage = append(coverage, map[string]any{"path": ref, "status": "covered"})
	}
	if _, err := st.ImportGeneration(context.Background(), input); err != nil {
		st.Close()
		t.Fatal(err)
	}
	if _, _, err := st.PublishRuntimeMetadata(context.Background(), "GEN-r3", rt.BaselineKindBrownfieldFull); err != nil {
		st.Close()
		t.Fatal(err)
	}
	if err := st.Close(); err != nil {
		t.Fatal(err)
	}
	status := rt.DefaultStatus(paths)
	status.Status, status.Freshness, status.Readiness, status.RecommendedNextAction = "ok", rt.ReadyFreshness, rt.ReadyReadiness, "use_project_cognition"
	status.GraphReady, status.ActiveGenerationID, status.BaselineKind = true, "GEN-r3", rt.BaselineKindBrownfieldFull
	if err := rt.WriteStatus(paths, status); err != nil {
		t.Fatal(err)
	}
	for name, value := range map[string]any{"capability-ledger.json": map[string]any{"rows": []any{}}, "control-ledger.json": map[string]any{"rows": []any{}}, "coverage-ledger.json": map[string]any{"rows": coverage, "open_gaps": []any{}}} {
		writeTaskRuntimeFixture(t, filepath.Join(paths.RuntimeDir, "workbench", name), value.(map[string]any))
	}
}

func r3BindingFixture(t *testing.T, workflow string) (string, string, map[string]any) {
	t.Helper()
	root, _, _ := seedCloseoutApplyRuntime(t)
	gitRun(t, root, "init")
	gitRun(t, root, "config", "user.email", "fixture@example.test")
	gitRun(t, root, "config", "user.name", "Fixture")
	for _, ref := range []string{"src/app.go", "src/old.go", "deps/lock.json"} {
		mustWriteScriptDomainTest(t, filepath.Join(root, filepath.FromSlash(ref)), "before source change\n")
	}
	gitRun(t, root, "add", "src", "deps")
	gitRun(t, root, "commit", "-m", "source binding fixture")
	scope := "."
	writeScope := []string{"src", mutationCognitionReceiptFileName, ".specify/project-cognition"}
	announced := announceExecutionCLI(t, root, "binding-"+workflow, workflow, "binding", "", writeScope, nil)
	guarded := guardExecutionCLI(t, root, announced, executionOverviewCLI(t, root, "binding-"+workflow), writeScope, nil)
	mustWriteScriptDomainTest(t, filepath.Join(root, "src", "app.go"), "after source change\n")
	return root, scope, guarded
}

func r3Apply(t *testing.T, root string, binding closeoutBinding) {
	t.Helper()
	payload := map[string]any{"workflow": binding.Workflow, "reason": "workflow-finalize", "changed_paths": binding.OwnedDelta, "scope_paths": binding.OwnedDelta, "boundary": map[string]any{"scope_mode": "explicit", "workflow_owned_paths": binding.OwnedDelta}, "verification": []map[string]string{{"command": "fixture observed check", "result": "passed"}}}
	raw, _ := json.Marshal(payload)
	var out bytes.Buffer
	if code := runCognitionCloseoutApplyCLIWithInput([]string{"--project-root", root, "--workflow", binding.Workflow, "--scope-dir", binding.Scope, "--payload-json", "-", "--binding-id", binding.ID, "--format", "json"}, bytes.NewReader(raw), &out); code != 0 {
		t.Fatalf("apply current proof: %s", out.String())
	}
}

func r3Claim(t *testing.T, root, workID string, refs []string) {
	t.Helper()
	store, err := runcontrol.OpenForRepository(t.Context(), root)
	if err != nil {
		t.Fatal(err)
	}
	defer store.Close()
	work, _, err := store.GetWork(t.Context(), workID)
	if err != nil {
		t.Fatal(err)
	}
	specs := []runcontrol.WriteIntentSpec{}
	for _, ref := range refs {
		specs = append(specs, runcontrol.WriteIntentSpec{Path: ref, Operation: runcontrol.WriteModify, Confidence: runcontrol.IntentConfirmed, Reason: "exact fixture owner"})
	}
	if _, _, err := store.ClaimWorkIntents(t.Context(), runcontrol.ClaimWorkIntentsParams{WorkID: workID, Fence: work.Fence, ExpectedRevision: work.Revision, Specs: specs}); err != nil {
		t.Fatal(err)
	}
}

func TestR3PendingIntentAuditRefusalAndFreshBoundRepair(t *testing.T) {
	root, scope, guard := r3BindingFixture(t, "fast")
	work := stringValue(guard["work_id"])
	first := r3Seal(t, root, r3Begin(t, root, scope, "fast", work, nil, nil))
	closeoutApplyAfterIntentPersistHook = func(string) error { return errors.New("observed fixture interruption") }
	t.Cleanup(func() { closeoutApplyAfterIntentPersistHook = nil })
	payload := map[string]any{"workflow": first.Workflow, "changed_paths": first.OwnedDelta, "scope_paths": first.OwnedDelta, "boundary": map[string]any{"scope_mode": "explicit", "workflow_owned_paths": first.OwnedDelta}, "verification": []map[string]string{{"command": "fixture observed check", "result": "passed"}}}
	raw, _ := json.Marshal(payload)
	var out bytes.Buffer
	if code := runCognitionCloseoutApplyCLIWithInput([]string{"--project-root", root, "--workflow", first.Workflow, "--scope-dir", scope, "--payload-json", "-", "--binding-id", first.ID}, bytes.NewReader(raw), &out); code == 0 {
		t.Fatal("interruption not observed")
	}
	closeoutApplyAfterIntentPersistHook = nil
	paths, _ := rt.ResolvePaths(root)
	intents, err := listCloseoutIntents(paths)
	if err != nil || len(intents) != 1 {
		t.Fatalf("pending intent %v %v", intents, err)
	}
	original := intents[0]
	mustWriteScriptDomainTest(t, filepath.Join(root, "src", "app.go"), "changed after interrupted validation\n")
	if _, err := loadCloseoutIntent(paths, original.ID); err != nil {
		t.Fatalf("stale evidence lost auditability: %v", err)
	}
	out.Reset()
	if code := runCognitionCloseoutReplayCLI([]string{"--project-root", root, "--intent-id", original.ID, "--expected-digest", original.InputDigest}, &out); code == 0 {
		t.Fatal("stale pending proof replayed")
	}
	current := r3Seal(t, root, r3Begin(t, root, scope, "fast", work, nil, nil))
	verification := []map[string]string{{"command": current.Validation[0].Command, "result": current.Validation[0].Result}}
	verifyRaw, _ := json.Marshal(verification)
	out.Reset()
	if code := runCognitionCloseoutRepairCLIWithInput([]string{"--project-root", root, "--intent-id", original.ID, "--expected-digest", original.InputDigest, "--binding-id", current.ID, "--verification-json", "-"}, bytes.NewReader(verifyRaw), &out); code != 0 {
		t.Fatalf("fresh repair: %s", out.String())
	}
	var env Envelope
	_ = json.Unmarshal(out.Bytes(), &env)
	replacement := stringValue(env.Data["replacement_intent_id"])
	digest := stringValue(env.Data["replacement_input_digest"])
	out.Reset()
	if code := runCognitionCloseoutReplayCLI([]string{"--project-root", root, "--intent-id", replacement, "--expected-digest", digest}, &out); code != 0 {
		t.Fatalf("fresh repaired replay: %s", out.String())
	}
	if err := requireMutationCognitionReceipt(root, first.Workflow); err != nil {
		t.Fatal(err)
	}
}

func TestR3QuickActualTerminalAndAcceptedVersion(t *testing.T) {
	root, workspace, id := newQuickOptimizationFixture(t)
	r3SeedGraph(t, root, []string{"src/a.go"})
	writeTaskRuntimeFixture(t, filepath.Join(root, ".specify", "integration.json"), map[string]any{"integration": "codex"})
	env := runScriptDomainEnvelope(t, runQuick, []string{"--project-root", root, "item-start", id, "--item", "Q1"})
	if env.Status != "ok" {
		t.Fatal(env)
	}
	mustWriteScriptDomainTest(t, filepath.Join(root, "src", "a.go"), "retained Quick source\n")
	result := map[string]any{"task_id": "Q1", "status": "success", "summary": "current native result", "cognition_delta": workerDeltaFixture("Q1", "accepted Quick source", []string{"src/a.go"}), "validation_results": []any{map[string]any{"command": "required check", "status": "passed"}}}
	if code, got := runResultInProject(t, root, []string{"submit", "--command", "quick", "--workspace", workspace, "--lane-id", "Q1", "--result-json", marshalJSONForCLI(t, result)}); code != 0 {
		t.Fatal(got)
	}
	env = runScriptDomainEnvelope(t, runQuick, []string{"--project-root", root, "item-accept", id, "--item", "Q1", "--evidence", "current readback"})
	if env.Status != "ok" {
		t.Fatal(env)
	}
	work := os.Getenv("SPECIFY_WORK_ID")
	scope := projectRelativeSlash(root, workspace)
	r3Claim(t, root, work, []string{scope, ".specify/project-cognition"})
	if env := runScriptDomainEnvelope(t, runQuick, []string{"--project-root", root, "close", id, "resolved"}); env.Status == "ok" {
		t.Fatal("Quick source terminal accepted missing binding")
	}
	binding := r3Seal(t, root, r3Begin(t, root, scope, "quick", work, nil, nil))
	r3Apply(t, root, binding)
	loaded, err := (quickService{projectRoot: root}).loadCognitionCloseout(workspace)
	if err != nil || loaded == nil || loaded.StrongBinding == nil || loaded.Scope != scope || loaded.IntentID == "" || !equalCloseoutPaths(loaded.ChangedPaths, binding.OwnedDelta) {
		t.Fatalf("lossy Quick receipt %+v %v", loaded, err)
	}
	if env := runScriptDomainEnvelope(t, runQuick, []string{"--project-root", root, "close", id, "resolved"}); env.Status != "ok" {
		t.Fatalf("actual Quick terminal: %+v", env)
	}
	if code, got := runResultInProject(t, root, []string{"submit", "--command", "quick", "--workspace", workspace, "--lane-id", "Q1", "--result-json", marshalJSONForCLI(t, result)}); code != 0 {
		t.Fatal(got)
	}
	if err := r3Check(root, binding); err == nil {
		t.Fatal("stale accepted Quick version remained strong")
	}
}

func TestR3ImplementActualTerminalNativeValidationAndAcceptedVersion(t *testing.T) {
	root, feature, scope := newImplementFeatureProject(t)
	writeTaskRuntimeFixture(t, filepath.Join(root, ".specify", "integration.json"), map[string]any{"integration": "codex"})
	r3SeedGraph(t, root, []string{"src/product.txt"})
	withImplementCwd(t, root)
	index := readImplementJSONFile(t, filepath.Join(feature, "task-index.json"))
	task := index["tasks"].([]any)[0].(map[string]any)
	task["objective"], task["status"], task["dependencies"], task["expected_write_scope"], task["task_checks"] = "bounded source repair", "pending", []any{}, []any{"src/product.txt"}, []any{"required check"}
	index["source_revision"] = "r3-source"
	writeImplementJSONFile(t, filepath.Join(feature, "task-index.json"), index)
	writeTaskRuntimeFixture(t, filepath.Join(root, ".specify", "templates", "task-lifecycle-template.json"), map[string]any{"version": 1, "revision": 0, "status": "pending", "validation": []any{}, "blockers": []any{}, "ui_verification": map[string]any{"applicable": false}})
	bindImplementTestWork(t, root, scope, []string{"src/product.txt", scope, ".specify/project-cognition"})
	assertTaskRuntimeCommandOK(t, []string{"implement", "task-start", "--feature-dir", scope, "--task-id", "T001", "--execution-mode", "leader-direct", "--format", "json"})
	mustWriteScriptDomainTest(t, filepath.Join(root, "src", "product.txt"), "retained implementation source\n")
	result := map[string]any{"task_id": "T001", "status": "success", "summary": "current implementation", "cognition_delta": workerDeltaFixture("T001", "accepted implementation", []string{"src/product.txt"}), "validation_results": []any{map[string]any{"command": "required check", "status": "passed"}}, "blockers": []any{}}
	assertTaskRuntimeCommandOK(t, []string{"implement", "result-merge", "--feature-dir", scope, "--task-id", "T001", "--result-json", marshalJSONForCLI(t, result), "--format", "json"})
	assertTaskRuntimeCommandOK(t, []string{"implement", "task-accept", "--feature-dir", scope, "--task-id", "T001", "--format", "json"})
	work := os.Getenv("SPECIFY_WORK_ID")
	binding := r3Begin(t, root, scope, "implement", work, nil, nil)
	now := time.Now().UTC().Format(time.RFC3339Nano)
	if _, err := sealCloseoutBinding(root, binding.Workflow, scope, closeoutBindingInput{BindingID: binding.ID, Validation: []closeoutBindingObservation{{Command: "old convergence", Result: "passed", StartedAt: now, FinishedAt: now}}}); err == nil {
		t.Fatal("old/unbound native convergence became strong")
	}
	var out bytes.Buffer
	if code := runImplement([]string{"validation-start", "--feature-dir", scope, "--stage", "implement", "--purpose", "convergence", "--command", "required check", "--task-id", "T001", "--fingerprint", "agent-invented"}, &out); code == 0 {
		t.Fatal("agent fingerprint became runtime proof")
	}
	out.Reset()
	if code := runImplement([]string{"validation-start", "--feature-dir", scope, "--stage", "implement", "--purpose", "convergence", "--command", "required check", "--task-id", "T001"}, &out); code != 0 {
		t.Fatalf("native convergence begin: %s", out.String())
	}
	out.Reset()
	if code := runImplement([]string{"validation-finish", "--feature-dir", scope, "--run-id", "V1", "--status", "passed", "--evidence-ref", "implementation-review/validation-evidence/V1.txt", "--summary", "fresh current observation"}, &out); code != 0 {
		t.Fatalf("native convergence finish: %s", out.String())
	}
	out.Reset()
	if code := runImplement([]string{"closeout", "--feature-dir", scope}, &out); code == 0 {
		t.Fatal("Implement accepted legacy receipt")
	}
	binding = r3Seal(t, root, binding)
	// A new binding retries the same convergence gate with a new attempt. It
	// never consumes an additional logical gate or reuses the prior pass.
	binding = r3Begin(t, root, scope, "implement", work, nil, nil)
	out.Reset()
	if code := runImplement([]string{"validation-start", "--feature-dir", scope, "--stage", "implement", "--purpose", "convergence", "--command", "required check", "--task-id", "T001"}, &out); code != 0 {
		t.Fatalf("same gate fresh attempt: %s", out.String())
	}
	out.Reset()
	if code := runImplement([]string{"validation-finish", "--feature-dir", scope, "--run-id", "V1", "--status", "passed", "--evidence-ref", "implementation-review/validation-evidence/V1-A2.txt", "--summary", "fresh new binding observation"}, &out); code != 0 {
		t.Fatalf("same gate finish: %s", out.String())
	}
	budget, err := implementValidationBudgetStatus(root, feature)
	if err != nil || intFromAny(budget["used_epochs"]) != 1 || intFromAny(budget["used_attempts"]) != 2 {
		t.Fatalf("new binding changed logical budget: %+v %v", budget, err)
	}
	binding = r3Seal(t, root, binding)
	r3Apply(t, root, binding)
	out.Reset()
	if code := runImplement([]string{"closeout", "--feature-dir", scope}, &out); code != 0 {
		t.Fatalf("actual Implement terminal: %s", out.String())
	}
	if err := r3Check(root, binding); err != nil {
		t.Fatalf("handoff weakened source proof: %v", err)
	}
	out.Reset()
	if code := runImplement([]string{"result-merge", "--feature-dir", scope, "--task-id", "T001", "--result-json", marshalJSONForCLI(t, result)}, &out); code == 0 {
		t.Fatal("current accepted result was replaced without a native new attempt")
	}
	if err := r3Check(root, binding); err != nil {
		t.Fatalf("refused resubmission damaged current evidence: %v", err)
	}
	// Published source artifacts are consistency inputs, not authenticated
	// storage. Replacing the accepted bytes cannot inherit that acceptance.
	writeImplementJSONFile(t, filepath.Join(feature, "worker-results", "T001.json"), result)
	if err := r3Check(root, binding); err == nil {
		t.Fatal("old Implement acceptance accepted a new submission")
	}
}

func TestR3ReviewActualRepairTerminalConsumesWorkProof(t *testing.T) {
	root, feature, scope := newReviewAcceptWorkflowFeature(t, "r3-review")
	r3SeedGraph(t, root, []string{"src/product.txt"})
	writeReviewAcceptWorkflowStateFixture(t, feature, "r3-review", 4, "review", "active", nil)
	mustWriteScriptDomainTest(t, filepath.Join(root, "src", "product.txt"), "retained Review repair\n")
	declareReviewAcceptImplementationPaths(t, feature, "src/product.txt")
	mustWriteReviewAcceptJSON(t, filepath.Join(feature, implementationHandoffFilename), reviewAcceptHandoffFixture(root, feature, 4))
	state := approvedReviewStateFixture(t, root, feature, scope, 4)
	mustWriteReviewAcceptJSON(t, filepath.Join(feature, reviewStateFilename), state)
	authorizeReviewAcceptRepair(t, feature, "src/product.txt")
	state = readReviewAcceptJSON(t, filepath.Join(feature, reviewStateFilename))
	state["status"] = "approved"
	mustWriteReviewAcceptJSON(t, filepath.Join(feature, reviewStateFilename), state)
	gitRun(t, root, "init")
	intents := []map[string]any{{"path": "src/product.txt", "operation": "modify", "confidence": "confirmed"}, {"path": scope, "operation": "modify", "confidence": "confirmed"}, {"path": ".specify/project-cognition", "operation": "modify", "confidence": "confirmed"}}
	code, env := invokeCoordinationCLI(t, "work", "begin", "--project-root", root, "--work-id", "review-work", "--task-ref", "review:r3-review", "--summary", "accepted Review repairs", "--agent-id", "review-leader", "--adapter-id", "test", "--intents-json", marshalWorkBoardCLIJSON(t, intents))
	if code != 0 {
		t.Fatal(env)
	}
	withImplementCwd(t, root)
	t.Setenv("SPECIFY_WORK_ID", "review-work")
	var out bytes.Buffer
	args := []string{"closeout", "--project-root", root, "--feature-dir", scope, "--expected-revision", "4"}
	if code := runReview(args, &out); code == 0 {
		t.Fatal("Review repair accepted missing proof")
	}
	binding := r3Begin(t, root, scope, "review", "review-work", nil, nil)
	if code := runImplement([]string{"validation-start", "--feature-dir", scope, "--stage", "review", "--purpose", "delivery", "--command", "delivery check", "--task-id", "T001"}, &out); code != 0 {
		t.Fatalf("delivery begin: %s", out.String())
	}
	out.Reset()
	if code := runImplement([]string{"validation-finish", "--feature-dir", scope, "--run-id", "V1", "--status", "passed", "--evidence-ref", "implementation-review/validation-evidence/V1.txt", "--summary", "fresh Review observation"}, &out); code != 0 {
		t.Fatalf("delivery finish: %s", out.String())
	}
	binding = r3Seal(t, root, binding)
	r3Apply(t, root, binding)
	out.Reset()
	if code := runReview(args, &out); code != 0 {
		t.Fatalf("actual Review repair terminal: %s", out.String())
	}
	mustWriteScriptDomainTest(t, filepath.Join(root, "src", "product.txt"), "changed after review source proof\n")
	out.Reset()
	if code := runReview(args, &out); code == 0 {
		t.Fatal("Review repair source drift retained terminal claim")
	}
}

func r3Begin(t *testing.T, root, scope, workflow, work string, dependencies, parents []string) closeoutBinding {
	t.Helper()
	binding, err := beginCloseoutBinding(root, "sp-"+workflow, scope, closeoutBindingInput{WorkID: work, DependencyRefs: dependencies, ParentBindingIDs: parents})
	if err != nil {
		t.Fatal(err)
	}
	return binding
}
func r3Seal(t *testing.T, root string, binding closeoutBinding) closeoutBinding {
	t.Helper()
	now := time.Now().UTC().Format(time.RFC3339Nano)
	sealed, err := sealCloseoutBinding(root, binding.Workflow, binding.Scope, closeoutBindingInput{BindingID: binding.ID, Validation: []closeoutBindingObservation{{Command: "fixture observed check", Result: "passed", StartedAt: now, FinishedAt: now}}})
	if err != nil {
		t.Fatal(err)
	}
	return sealed
}
func r3Check(root string, binding closeoutBinding) error {
	_, err := requireStrongCloseoutBinding(root, binding.Workflow, binding.Scope, binding.ID, binding.WorkID)
	return err
}

func TestR3RenameOwnershipRefusesEitherEndpointBeforeBinding(t *testing.T) {
	for _, staged := range []bool{false, true} {
		t.Run(map[bool]string{false: "unstaged", true: "staged"}[staged], func(t *testing.T) {
			root, scope, guard := r3BindingFixture(t, "fast")
			mustMkdir(t, filepath.Join(root, "outside"))
			if err := os.Rename(filepath.Join(root, "src", "old.go"), filepath.Join(root, "outside", "new.go")); err != nil {
				t.Fatal(err)
			}
			if staged {
				gitRun(t, root, "add", "src/old.go", "outside/new.go")
			}
			if _, err := beginCloseoutBinding(root, "sp-fast", scope, closeoutBindingInput{WorkID: stringValue(guard["work_id"])}); err == nil || !strings.Contains(err.Error(), "both endpoints") {
				t.Fatalf("cross-owner rename became bound: %v", err)
			}
			entries, _ := os.ReadDir(closeoutBindingDir(root))
			if len(entries) != 0 {
				t.Fatal("rejected rename wrote a binding")
			}
		})
	}
}

func TestR3ApplyRacingSourceRefusesBeforeUpdateAndMarksDebt(t *testing.T) {
	for _, phase := range []string{"preflight", "before_update", "after_update"} {
		t.Run(phase, func(t *testing.T) {
			root, scope, guard := r3BindingFixture(t, "fast")
			proof := r3Seal(t, root, r3Begin(t, root, scope, "fast", stringValue(guard["work_id"]), nil, nil))
			paths, _ := rt.ResolvePaths(root)
			before := countCloseoutApplyUpdates(t, paths)
			mutate := func() error {
				path := filepath.Join(root, "src", "app.go")
				info, err := os.Stat(path)
				if err != nil {
					return err
				}
				if err := os.WriteFile(path, []byte("other source change\n"), 0o644); err != nil {
					return err
				}
				return os.Chtimes(path, info.ModTime(), info.ModTime())
			}
			switch phase {
			case "preflight":
				closeoutApplyAfterPreflightHook = mutate
			case "before_update":
				closeoutApplyBeforeCurrentUpdateHook = func(string) error { return mutate() }
			case "after_update":
				closeoutApplyAfterUpdateHook = func(string) error { return mutate() }
			}
			t.Cleanup(func() {
				closeoutApplyAfterPreflightHook = nil
				closeoutApplyBeforeCurrentUpdateHook = nil
				closeoutApplyAfterUpdateHook = nil
			})
			payload := map[string]any{"workflow": proof.Workflow, "changed_paths": proof.OwnedDelta, "scope_paths": proof.OwnedDelta, "boundary": map[string]any{"scope_mode": "explicit", "workflow_owned_paths": proof.OwnedDelta}, "verification": []map[string]string{{"command": "fixture observed check", "result": "passed"}}}
			raw, _ := json.Marshal(payload)
			var out bytes.Buffer
			if code := runCognitionCloseoutApplyCLIWithInput([]string{"--project-root", root, "--workflow", proof.Workflow, "--scope-dir", scope, "--payload-json", "-", "--binding-id", proof.ID}, bytes.NewReader(raw), &out); code == 0 {
				t.Fatalf("raced source published closeout: %s", out.String())
			}
			if phase != "after_update" && countCloseoutApplyUpdates(t, paths) != before {
				t.Fatal("stale source reached update before locked check")
			}
			status, err := rt.ReadStatus(paths)
			if err != nil || !status.Dirty || status.Freshness == rt.ReadyFreshness {
				t.Fatalf("raced source falsely fresh: %+v %v", status, err)
			}
			if err := requireMutationCognitionReceipt(root, proof.Workflow); err == nil {
				t.Fatal("raced source published a closeable receipt")
			}
		})
	}
}

func TestR3CommittedSourceRaceRepairPublishesFreshSuccessor(t *testing.T) {
	root, scope, guard := r3BindingFixture(t, "fast")
	work := stringValue(guard["work_id"])
	first := r3Seal(t, root, r3Begin(t, root, scope, "fast", work, nil, nil))
	closeoutApplyAfterUpdateHook = func(string) error {
		mustWriteScriptDomainTest(t, filepath.Join(root, "src", "app.go"), "source changed after committed update\n")
		return nil
	}
	t.Cleanup(func() { closeoutApplyAfterUpdateHook = nil })
	payload := map[string]any{"workflow": first.Workflow, "changed_paths": first.OwnedDelta, "scope_paths": first.OwnedDelta, "boundary": map[string]any{"scope_mode": "explicit", "workflow_owned_paths": first.OwnedDelta}, "verification": []map[string]string{{"command": "fixture observed check", "result": "passed"}}}
	raw, _ := json.Marshal(payload)
	var out bytes.Buffer
	if code := runCognitionCloseoutApplyCLIWithInput([]string{"--project-root", root, "--workflow", first.Workflow, "--scope-dir", scope, "--payload-json", "-", "--binding-id", first.ID}, bytes.NewReader(raw), &out); code == 0 {
		t.Fatal("post-update stale proof published")
	}
	closeoutApplyAfterUpdateHook = nil
	paths, _ := rt.ResolvePaths(root)
	intents, err := listCloseoutIntents(paths)
	if err != nil || len(intents) != 1 {
		t.Fatalf("race intent %v %v", intents, err)
	}
	original := intents[0]
	oldUpdate, err := closeoutCommittedUpdate(paths, original.ID)
	if err != nil || oldUpdate == "" {
		t.Fatalf("original commit not preserved: %s %v", oldUpdate, err)
	}
	originalBytes := canonicalCloseoutBindingJSON(original)
	out.Reset()
	if code := runCognitionCloseoutInspectCLI([]string{"--project-root", root, "--intent-id", original.ID}, &out); code != 0 {
		t.Fatalf("inspect race: %s", out.String())
	}
	t.Logf("committed stale inspection: %s", out.String())
	fresh := r3Seal(t, root, r3Begin(t, root, scope, "fast", work, nil, nil))
	verification, _ := json.Marshal([]map[string]string{{"command": fresh.Validation[0].Command, "result": fresh.Validation[0].Result}})
	out.Reset()
	if code := runCognitionCloseoutRepairCLIWithInput([]string{"--project-root", root, "--intent-id", original.ID, "--expected-digest", original.InputDigest, "--binding-id", fresh.ID, "--verification-json", "-"}, bytes.NewReader(verification), &out); code != 0 {
		t.Fatalf("committed fresh successor refused: %s", out.String())
	}
	var env Envelope
	_ = json.Unmarshal(out.Bytes(), &env)
	replacement := stringValue(env.Data["replacement_intent_id"])
	digest := stringValue(env.Data["replacement_input_digest"])
	record, err := loadCloseoutRepair(paths, original.ID)
	if err != nil || !bytes.Equal(originalBytes, canonicalCloseoutBindingJSON(record.Original)) {
		t.Fatalf("old committed input was rewritten: %v", err)
	}
	out.Reset()
	if code := runCognitionCloseoutReplayCLI([]string{"--project-root", root, "--intent-id", replacement, "--expected-digest", digest}, &out); code != 0 {
		t.Fatalf("fresh successor publication: %s", out.String())
	}
	if old, err := closeoutCommittedUpdate(paths, original.ID); err != nil || old != oldUpdate {
		t.Fatal("old committed update was discarded or rebound")
	}
	newUpdate, err := closeoutCommittedUpdate(paths, replacement)
	if err != nil || newUpdate == "" || newUpdate == oldUpdate {
		t.Fatal("successor reused the old update")
	}
	if err := requireMutationCognitionReceipt(root, first.Workflow); err != nil {
		t.Fatal(err)
	}
	if err := r3Check(root, first); err == nil {
		t.Fatal("archived stale proof became current")
	}
}

func TestR3E2ERetainedTestAssetActualTerminal(t *testing.T) {
	root := e2eTestInit(t, "execution")
	mustMkdir(t, filepath.Join(root, ".specify"))
	gitRun(t, root, "init")
	r3SeedGraph(t, root, []string{"tests/e2e/s1.md"})
	for stage := 1; stage <= 7; stage++ {
		id := "S" + fmt.Sprint(stage)
		input := e2eTestPrepareSubmission(t, root, id, "pass")
		if stage == 1 {
			input["worker_result"].(map[string]any)["cognition_delta"] = workerDeltaFixture(id, "retained E2E test asset", []string{"tests/e2e/s1.md"})
		}
		e2eTestMutation(t, root, "task-submit", "--task-id", id, "--worker-id", "worker-"+id, "--result-json", e2eTestJSON(t, input))
		e2eTestReviewAndAccept(t, root, id)
	}
	if code, _ := e2eTestCall(t, root, "close", "--run-id", "run-1", "--leader-id", "leader", "--outcome", "pass", "--expected-revision", e2eTestRevision(t, root)); code == 0 {
		t.Fatal("retained asset closed without strong receipt")
	}
	scope := ".planning/e2e/run-1"
	intents := []map[string]any{{"path": "tests/e2e/s1.md", "operation": "modify", "confidence": "confirmed"}, {"path": scope, "operation": "modify", "confidence": "confirmed"}, {"path": ".specify/project-cognition", "operation": "modify", "confidence": "confirmed"}}
	if code, env := invokeCoordinationCLI(t, "work", "begin", "--project-root", root, "--work-id", "e2e-work", "--task-ref", "e2e:run-1", "--summary", "joined retained E2E asset", "--agent-id", "leader", "--adapter-id", "test", "--intents-json", marshalWorkBoardCLIJSON(t, intents)); code != 0 {
		t.Fatal(env)
	}
	proof := r3Seal(t, root, r3Begin(t, root, scope, "e2e", "e2e-work", nil, nil))
	if len(proof.RequiredDependencyRefs) < 8 {
		t.Fatal("native E2E dependency closure was omitted")
	}
	r3Apply(t, root, proof)
	closed := e2eTestMutation(t, root, "close", "--leader-id", "leader", "--outcome", "pass")
	if closed["product_pass"] != true {
		t.Fatal(closed)
	}
	e2eTestFile(t, root, "request.md", "changed input after source validation\n")
	if err := r3Check(root, proof); err == nil {
		t.Fatal("native E2E required dependency changed but source proof survived")
	}
}

func TestR3E2ETraceAndTemporaryOnlyTerminalDoesNotInventUpdate(t *testing.T) {
	root := e2eTestInit(t, "execution")
	refs := []string{"test-results/e2e/run-1/trace.json", ".specify/tmp/e2e/scratch.json", ".codex-tmp/e2e/raw.log"}
	for stage := 1; stage <= 7; stage++ {
		id := "S" + fmt.Sprint(stage)
		input := e2eTestPrepareSubmission(t, root, id, "pass")
		if stage == 1 {
			for _, ref := range refs {
				e2eTestFile(t, root, ref, "observed disposable run output\n")
			}
			input["worker_result"].(map[string]any)["cognition_delta"] = workerDeltaFixture(id, "execution trace only", refs)
		}
		e2eTestMutation(t, root, "task-submit", "--task-id", id, "--worker-id", "worker-"+id, "--result-json", e2eTestJSON(t, input))
		e2eTestReviewAndAccept(t, root, id)
	}
	if result := e2eTestMutation(t, root, "close", "--leader-id", "leader", "--outcome", "pass"); result["product_pass"] != true {
		t.Fatal(result)
	}
	for _, ref := range []string{".planning/e2e/run-1/cognition-closeout.json", ".specify/project-cognition/status.json"} {
		if _, err := os.Stat(filepath.Join(root, filepath.FromSlash(ref))); !os.IsNotExist(err) {
			t.Fatalf("trace-only execution fabricated %s: %v", ref, err)
		}
	}
}

func TestR3BindingFreshSourceAndDependencyBytes(t *testing.T) {
	for _, phase := range []string{"before_seal", "after_seal"} {
		for _, kind := range []string{"same_size_same_mtime", "rename_both_ends", "dependency"} {
			t.Run(phase+"_"+kind, func(t *testing.T) {
				root, scope, guard := r3BindingFixture(t, "fast")
				binding := r3Begin(t, root, scope, "fast", stringValue(guard["work_id"]), []string{"deps/lock.json"}, nil)
				if phase == "after_seal" {
					binding = r3Seal(t, root, binding)
					if err := r3Check(root, binding); err != nil {
						t.Fatal(err)
					}
				}
				path := filepath.Join(root, "src", "app.go")
				switch kind {
				case "same_size_same_mtime":
					info, err := os.Stat(path)
					if err != nil {
						t.Fatal(err)
					}
					data, err := os.ReadFile(path)
					if err != nil {
						t.Fatal(err)
					}
					data[0] ^= 1
					if err := os.WriteFile(path, data, 0o644); err != nil {
						t.Fatal(err)
					}
					if err := os.Chtimes(path, info.ModTime(), info.ModTime()); err != nil {
						t.Fatal(err)
					}
				case "rename_both_ends":
					if err := os.Rename(filepath.Join(root, "src", "old.go"), filepath.Join(root, "src", "new.go")); err != nil {
						t.Fatal(err)
					}
				case "dependency":
					mustWriteScriptDomainTest(t, filepath.Join(root, "deps", "lock.json"), "different dependency\n")
				}
				if phase == "after_seal" {
					if err := r3Check(root, binding); err == nil {
						t.Fatal("changed bytes retained strong proof")
					}
				} else {
					now := nowUTCString()
					_, err := sealCloseoutBinding(root, binding.Workflow, scope, closeoutBindingInput{BindingID: binding.ID, Validation: []closeoutBindingObservation{{Command: "old check", Result: "passed", StartedAt: now, FinishedAt: now}}})
					if err == nil {
						t.Fatal("changed source was rebound to old verification")
					}
				}
			})
		}
	}
}

func TestR3BindingExactAttemptScopeWorkAndTransitiveParents(t *testing.T) {
	root, scope, guard := r3BindingFixture(t, "fast")
	work := stringValue(guard["work_id"])
	first := r3Seal(t, root, r3Begin(t, root, scope, "fast", work, []string{"deps/lock.json"}, nil))
	if _, err := requireStrongCloseoutBinding(root, "sp-debug", scope, first.ID, work); err == nil {
		t.Fatal("wrong workflow accepted")
	}
	if _, err := requireStrongCloseoutBinding(root, first.Workflow, scope+"-other", first.ID, work); err == nil {
		t.Fatal("wrong scope accepted")
	}
	if _, err := requireStrongCloseoutBinding(root, first.Workflow, scope, first.ID, "another-work"); err == nil {
		t.Fatal("cross-task Work accepted")
	}
	second := r3Begin(t, root, scope, "fast", work, nil, nil)
	if err := r3Check(root, first); err == nil {
		t.Fatal("superseded attempt accepted")
	}
	second = r3Seal(t, root, second)
	// Independent work has its own exact path; its unchanged proof must survive.
	announced := announceExecutionCLI(t, root, "binding-debug", "debug", "independent", "", []string{"other"}, nil)
	other := guardExecutionCLI(t, root, announced, executionOverviewCLI(t, root, "binding-debug"), []string{"other"}, nil)
	mustWriteScriptDomainTest(t, filepath.Join(root, "other", "file"), "independent source\n")
	otherScope := "."
	unaffected := r3Seal(t, root, r3Begin(t, root, otherScope, "debug", stringValue(other["work_id"]), nil, nil))
	childAnnounced := announceExecutionCLI(t, root, "binding-child", "debug", "child", "", []string{"child"}, nil)
	childWork := guardExecutionCLI(t, root, childAnnounced, executionOverviewCLI(t, root, "binding-child"), []string{"child"}, nil)
	mustWriteScriptDomainTest(t, filepath.Join(root, "child", "file"), "child source\n")
	child := r3Seal(t, root, r3Begin(t, root, ".", "debug", stringValue(childWork["work_id"]), nil, []string{second.ID}))
	if err := r3Check(root, child); err != nil {
		t.Fatal(err)
	}
	mustWriteScriptDomainTest(t, filepath.Join(root, "src", "app.go"), "parent changed\n")
	if err := r3Check(root, child); err == nil {
		t.Fatal("affected descendant retained proof")
	}
	if err := r3Check(root, unaffected); err != nil {
		t.Fatalf("unaffected evidence lost: %v", err)
	}
}

func TestR3BindingRefusesMechanicalInputLegacyAndOldObservations(t *testing.T) {
	root, scope, guard := r3BindingFixture(t, "fast")
	for _, field := range []string{"source", "sha256", "attempt_id", "started_at", "write_scope", "accepted_output_refs"} {
		input := map[string]any{"work_id": stringValue(guard["work_id"]), field: "forged"}
		raw, _ := json.Marshal(input)
		var out bytes.Buffer
		code := runCognitionCloseoutBindingCLIWithInput([]string{"begin", "--workflow", "sp-fast", "--scope-dir", scope, "--project-root", root, "--input-json", "-"}, bytes.NewReader(raw), &out)
		if code == 0 {
			t.Fatalf("mechanical field %s accepted: %s", field, out.String())
		}
	}
	old := time.Now().Add(-time.Hour).UTC().Format(time.RFC3339Nano)
	artifact := filepath.Join(root, "old-check.log")
	mustWriteScriptDomainTest(t, artifact, "old passing result\n")
	oldTime := time.Now().Add(-time.Hour)
	if err := os.Chtimes(artifact, oldTime, oldTime); err != nil {
		t.Fatal(err)
	}
	binding := r3Begin(t, root, scope, "fast", stringValue(guard["work_id"]), nil, nil)
	if _, err := sealCloseoutBinding(root, binding.Workflow, scope, closeoutBindingInput{BindingID: binding.ID, Validation: []closeoutBindingObservation{{Command: "old observation", Result: "passed", StartedAt: old, FinishedAt: old}}}); err == nil {
		t.Fatal("old observation sealed")
	}
	now := time.Now().UTC().Format(time.RFC3339Nano)
	if _, err := sealCloseoutBinding(root, binding.Workflow, scope, closeoutBindingInput{BindingID: binding.ID, Validation: []closeoutBindingObservation{{Command: "retimestamped old log", Result: "passed", Artifact: "old-check.log", StartedAt: now, FinishedAt: now}}}); err == nil {
		t.Fatal("old artifact relabelled")
	}
	if _, err := recordMutationCognitionReceipt(filepath.Join(root, filepath.FromSlash(scope)), "sp-fast", scope, "mark-dirty", "explicit legacy audit", "", nil); err != nil {
		t.Fatal(err)
	}
	if err := requireMutationCognitionReceipt(filepath.Join(root, filepath.FromSlash(scope)), "sp-fast"); err == nil {
		t.Fatal("legacy receipt became strong terminal proof")
	}
}

func TestR3SharedApplyAndActualFastDebugCompletionConsumeBinding(t *testing.T) {
	for _, workflow := range []string{"fast", "debug"} {
		t.Run(workflow, func(t *testing.T) {
			root, scope, guard := r3BindingFixture(t, workflow)
			work := stringValue(guard["work_id"])
			args := []string{"execution", "complete", work, "--project-root", root, "--expected-revision", executionJSONNumberString(guard["work_revision"]), "--fence", executionJSONNumberString(guard["fence"]), "--validation-json", `[{"command":"fresh check","result":"passed"}]`, "--reason", "observed validated completion", "--format", "json"}
			code, _ := invokeCoordinationCLI(t, args...)
			if code == 0 {
				t.Fatal("actual source-changing terminal accepted missing binding")
			}
			binding := r3Seal(t, root, r3Begin(t, root, scope, workflow, work, nil, nil))
			payload := map[string]any{"workflow": "sp-" + workflow, "reason": "workflow-finalize", "changed_paths": binding.OwnedDelta, "scope_paths": binding.OwnedDelta, "boundary": map[string]any{"scope_mode": "explicit", "workflow_owned_paths": binding.OwnedDelta}, "verification": []map[string]string{{"command": "fixture observed check", "result": "passed"}}}
			raw, _ := json.Marshal(payload)
			var out bytes.Buffer
			code = runCognitionCloseoutApplyCLIWithInput([]string{"--project-root", root, "--workflow", "sp-" + workflow, "--scope-dir", scope, "--payload-json", "-", "--binding-id", binding.ID, "--format", "json"}, bytes.NewReader(raw), &out)
			if code != 0 {
				t.Fatalf("shared apply refused current proof: %s", out.String())
			}
			receipt, err := loadMutationCognitionReceipt(filepath.Join(root, filepath.FromSlash(scope)))
			if err != nil || receipt.StrongBinding == nil {
				t.Fatalf("lost shared receipt binding: %#v %v", receipt, err)
			}
			if err := requireMutationCognitionReceipt(filepath.Join(root, filepath.FromSlash(scope)), binding.Workflow); err != nil {
				t.Fatal(err)
			}
			// A byte-identical receipt copied into another task cannot close that task.
			copyScope := filepath.Join(root, ".planning", "copy")
			if _, err := writeMutationCognitionReceipt(copyScope, *receipt); err != nil {
				t.Fatal(err)
			}
			if err := requireMutationCognitionReceipt(copyScope, binding.Workflow); err == nil {
				t.Fatal("copied receipt accepted")
			}
			if err := os.Remove(mutationCognitionReceiptPath(copyScope)); err != nil {
				t.Fatal(err)
			}
			args = append(args, "--binding-id", binding.ID)
			code, env := invokeCoordinationCLI(t, args...)
			if code != 0 {
				t.Fatalf("actual terminal failed current proof: %#v", env)
			}
			if err := r3Check(root, binding); err != nil {
				t.Fatalf("completion changed source basis: %v", err)
			}
		})
	}
}

func TestR3APIDeclaresBindingAndReadOnlyCheckDoesNotMutateWork(t *testing.T) {
	for _, args := range [][]string{{"cognition", "--help"}, {"cognition", "closeout", "--help"}, {"cognition", "closeout", "binding", "--help"}} {
		var out bytes.Buffer
		if code := Run(args, &out, &bytes.Buffer{}, "test"); code != 0 || !strings.Contains(out.String(), "binding") || !strings.Contains(out.String(), "seal") {
			t.Fatalf("public binding help missing: %v code=%d output=%s", args, code, out.String())
		}
	}
	root, scope, guard := r3BindingFixture(t, "fast")
	binding := r3Seal(t, root, r3Begin(t, root, scope, "fast", stringValue(guard["work_id"]), nil, nil))
	view, err := runcontrol.OpenViewForRepository(t.Context(), root)
	if err != nil {
		t.Fatal(err)
	}
	before, _, err := view.GetWork(t.Context(), binding.WorkID)
	if err != nil {
		t.Fatal(err)
	}
	_ = view.Close()
	input, _ := json.Marshal(map[string]string{"binding_id": binding.ID})
	var out bytes.Buffer
	code := runCognitionCloseoutBindingCLIWithInput([]string{"check", "--workflow", binding.Workflow, "--scope-dir", scope, "--project-root", root, "--input-json", "-"}, bytes.NewReader(input), &out)
	if code != 0 {
		t.Fatalf("read-only check: %s", out.String())
	}
	view, err = runcontrol.OpenViewForRepository(t.Context(), root)
	if err != nil {
		t.Fatal(err)
	}
	defer view.Close()
	after, _, err := view.GetWork(t.Context(), binding.WorkID)
	if err != nil {
		t.Fatal(err)
	}
	if !sameCloseoutBindingJSON(before, after) {
		t.Fatal("read-only binding check mutated native Work")
	}
	for _, id := range []string{"cognition.closeout.binding.v1", "cognition.closeout.binding.begin", "cognition.closeout.binding.seal", "cognition.closeout.binding.check"} {
		if !containsCapability(defaultCapabilities(), id) {
			t.Fatal("missing capability", id)
		}
	}
	if !strings.Contains(capabilitySummary("cognition.closeout.binding.v1"), "source bytes") {
		t.Fatal("missing capability contract")
	}
}
