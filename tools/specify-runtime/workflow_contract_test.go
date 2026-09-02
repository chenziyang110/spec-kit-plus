package main

import (
	"crypto/sha256"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"reflect"
	"sort"
	"strings"
	"testing"
)

func TestWorkflowUsesOneCurrentStateAndExactStageOrder(t *testing.T) {
	projectRoot, featureDir, featureRel := newWorkflowFeature(t, "001-runtime")
	service := NewWorkflowService(projectRoot)

	entered := service.Enter(WorkflowEnterRequest{FeatureID: "001-runtime", Command: "specify", ExpectedRevision: 0})
	if entered.Status != "ok" || entered.Data["revision"] != 1 {
		t.Fatalf("enter = %#v, want revision 1", entered)
	}
	statePath := filepath.Join(featureDir, "workflow.json")
	state := readWorkflowStateMap(t, statePath)
	wantKeys := []string{
		"acceptance_sha256", "blocker", "feature_id", "last_blocker_resolution",
		"last_reopen", "last_resolution_evidence", "revision", "schema_version",
		"stage", "status", "summary",
	}
	keys := make([]string, 0, len(state))
	for key := range state {
		keys = append(keys, key)
	}
	sort.Strings(keys)
	if !reflect.DeepEqual(keys, wantKeys) {
		t.Fatalf("workflow state keys = %#v, want %#v", keys, wantKeys)
	}
	if state["schema_version"] != float64(1) || state["feature_id"] != "001-runtime" || state["stage"] != "specify" || state["status"] != "active" {
		t.Fatalf("workflow state = %#v", state)
	}
	for _, forbidden := range []string{"workflow-runtime.json", "workflow-state.md"} {
		if _, err := os.Stat(filepath.Join(featureDir, forbidden)); !os.IsNotExist(err) {
			t.Fatalf("workflow service created %s: %v", forbidden, err)
		}
	}

	shown := service.Show(WorkflowShowRequest{FeatureDir: featureDir})
	if shown.Status != "ok" || shown.Data["stage"] != "specify" {
		t.Fatalf("show = %#v", shown)
	}
	assertRuntimeWorkflowArgv(t, shown.NextArgv, "next", featureRel)

	next := service.Next(WorkflowShowRequest{FeatureDir: featureRel})
	if next.Data["next_stage"] != "plan" {
		t.Fatalf("next = %#v, want plan", next)
	}
	assertRuntimeWorkflowArgv(t, next.NextArgv, "complete-stage", featureRel)
	writeValidSpecifyGateArtifacts(t, projectRoot, featureRel)

	completed := service.CompleteStage(WorkflowCompleteStageRequest{
		FeatureDir:       featureRel,
		ExpectedRevision: 1,
		Summary:          "Specification ready.",
	})
	if completed.Status != "ok" || completed.Data["revision"] != 2 || completed.Data["status"] != "completed" {
		t.Fatalf("complete-stage = %#v", completed)
	}
	assertRuntimeWorkflowArgv(t, completed.NextArgv, "transition", featureRel)

	advanced := service.Transition(WorkflowTransitionRequest{
		FeatureDir:       featureRel,
		To:               "plan",
		ExpectedRevision: 2,
	})
	if advanced.Status != "ok" || advanced.Data["revision"] != 3 || advanced.Data["stage"] != "plan" || advanced.Data["status"] != "active" {
		t.Fatalf("transition = %#v", advanced)
	}
	receipt, receiptRaw, receiptRef, err := readWorkflowMutationReceipt(projectRoot, featureRel)
	if err != nil {
		t.Fatalf("read workflow mutation receipt: %v", err)
	}
	currentWorkflow, err := os.ReadFile(statePath)
	if err != nil {
		t.Fatal(err)
	}
	if receiptRef != workflowMutationReceiptRef(featureRel) || receipt.Operation != "transition" ||
		receipt.PreviousRevision != 2 || receipt.Revision != 3 || receipt.Stage != "plan" || receipt.Status != "active" ||
		receipt.WorkflowSHA256 != fileContentSHA256(currentWorkflow) || fileContentSHA256(receiptRaw) == "" {
		t.Fatalf("workflow mutation receipt = ref %q receipt %#v", receiptRef, receipt)
	}

	skipped := service.Transition(WorkflowTransitionRequest{
		FeatureDir:       featureRel,
		To:               "tasks",
		ExpectedRevision: 3,
	})
	if skipped.Status != "blocked" {
		t.Fatalf("active stage skip = %#v, want blocked", skipped)
	}
	assertRuntimeWorkflowArgv(t, skipped.NextArgv, "complete-stage", featureRel)

	stale := service.CompleteStage(WorkflowCompleteStageRequest{FeatureDir: featureRel, ExpectedRevision: 1})
	if stale.Status != "blocked" {
		t.Fatalf("stale completion = %#v, want blocked", stale)
	}
	assertRuntimeWorkflowArgv(t, stale.ShowArgv, "show", featureRel)
}

func TestWorkflowFeatureDirConfinementAndRelativeArgv(t *testing.T) {
	t.Run("relative", func(t *testing.T) {
		projectRoot, _, featureRel := newWorkflowFeature(t, "001-relative")
		result := NewWorkflowService(projectRoot).Enter(WorkflowEnterRequest{FeatureDir: featureRel, Command: "specify"})
		if result.Status != "ok" {
			t.Fatalf("relative enter = %#v", result)
		}
		assertRuntimeWorkflowArgv(t, result.ShowArgv, "show", featureRel)
	})

	t.Run("absolute", func(t *testing.T) {
		projectRoot, featureDir, featureRel := newWorkflowFeature(t, "002-absolute")
		result := NewWorkflowService(projectRoot).Enter(WorkflowEnterRequest{FeatureDir: featureDir, Command: "discussion"})
		if result.Status != "ok" {
			t.Fatalf("absolute enter = %#v", result)
		}
		assertRuntimeWorkflowArgv(t, result.NextArgv, "complete-stage", featureRel)
	})

	for _, legacyRoot := range []string{filepath.Join(".specify", "specs"), "specs"} {
		legacyRoot := legacyRoot
		t.Run("legacy "+filepath.ToSlash(legacyRoot), func(t *testing.T) {
			projectRoot := t.TempDir()
			if err := os.MkdirAll(filepath.Join(projectRoot, ".specify"), 0o755); err != nil {
				t.Fatal(err)
			}
			featureID := "006-legacy"
			featureRel := filepath.ToSlash(filepath.Join(legacyRoot, featureID))
			featureDir := filepath.Join(projectRoot, filepath.FromSlash(featureRel))
			if err := os.MkdirAll(featureDir, 0o755); err != nil {
				t.Fatal(err)
			}
			result := NewWorkflowService(projectRoot).Enter(WorkflowEnterRequest{FeatureDir: featureRel, Command: "specify"})
			if result.Status != "ok" {
				t.Fatalf("legacy enter %s = %#v", featureRel, result)
			}
			assertRuntimeWorkflowArgv(t, result.ShowArgv, "show", featureRel)
		})
	}

	t.Run("outside", func(t *testing.T) {
		projectRoot, _, _ := newWorkflowFeature(t, "003-inside")
		outside := t.TempDir()
		result := NewWorkflowService(projectRoot).Enter(WorkflowEnterRequest{FeatureDir: outside, Command: "specify"})
		if result.Status != "invalid" {
			t.Fatalf("outside enter = %#v, want invalid", result)
		}
	})

	t.Run("nested", func(t *testing.T) {
		projectRoot, featureDir, _ := newWorkflowFeature(t, "004-parent")
		nested := filepath.Join(featureDir, "nested")
		if err := os.MkdirAll(nested, 0o755); err != nil {
			t.Fatal(err)
		}
		result := NewWorkflowService(projectRoot).Enter(WorkflowEnterRequest{FeatureDir: nested, Command: "specify"})
		if result.Status != "invalid" {
			t.Fatalf("nested enter = %#v, want invalid", result)
		}
	})

	t.Run("symlinked feature", func(t *testing.T) {
		projectRoot := t.TempDir()
		outside := t.TempDir()
		featuresRoot := filepath.Join(projectRoot, ".specify", "features")
		if err := os.MkdirAll(featuresRoot, 0o755); err != nil {
			t.Fatal(err)
		}
		featureLink := filepath.Join(featuresRoot, "005-linked")
		if err := os.Symlink(outside, featureLink); err != nil {
			t.Skipf("symlinks unavailable: %v", err)
		}
		result := NewWorkflowService(projectRoot).Enter(WorkflowEnterRequest{FeatureDir: featureLink, Command: "specify"})
		if result.Status != "invalid" && result.Status != "blocked" {
			t.Fatalf("symlinked feature enter = %#v, want fail closed", result)
		}
		if _, err := os.Stat(filepath.Join(outside, "workflow.json")); !os.IsNotExist(err) {
			t.Fatalf("symlinked feature wrote outside project: %v", err)
		}
	})
}

func TestWorkflowStateDecoderRejectsMalformedOrDriftedStateWithoutMutation(t *testing.T) {
	tests := []struct {
		name   string
		mutate func(map[string]any) []byte
	}{
		{name: "malformed json", mutate: func(map[string]any) []byte { return []byte(`{"schema_version":`) }},
		{name: "unknown field", mutate: func(state map[string]any) []byte { state["legacy"] = true; return mustJSONBytes(t, state) }},
		{name: "wrong schema", mutate: func(state map[string]any) []byte { state["schema_version"] = 2; return mustJSONBytes(t, state) }},
		{name: "feature mismatch", mutate: func(state map[string]any) []byte { state["feature_id"] = "other"; return mustJSONBytes(t, state) }},
		{name: "invalid revision", mutate: func(state map[string]any) []byte { state["revision"] = 0; return mustJSONBytes(t, state) }},
		{name: "invalid stage", mutate: func(state map[string]any) []byte { state["stage"] = "deploy"; return mustJSONBytes(t, state) }},
		{name: "invalid status", mutate: func(state map[string]any) []byte { state["status"] = "paused"; return mustJSONBytes(t, state) }},
		{name: "invalid blocker shape", mutate: func(state map[string]any) []byte {
			state["status"] = "blocked"
			state["blocker"] = "broken"
			return mustJSONBytes(t, state)
		}},
	}
	for _, test := range tests {
		t.Run(test.name, func(t *testing.T) {
			projectRoot, featureDir, featureRel := newWorkflowFeature(t, "001-invalid-state")
			writeWorkflowStateFixture(t, featureDir, "001-invalid-state", 3, "plan", "active", nil)
			state := readWorkflowStateMap(t, filepath.Join(featureDir, "workflow.json"))
			raw := test.mutate(state)
			if err := os.WriteFile(filepath.Join(featureDir, "workflow.json"), raw, 0o644); err != nil {
				t.Fatal(err)
			}
			before := append([]byte(nil), raw...)
			service := NewWorkflowService(projectRoot)
			shown := service.Show(WorkflowShowRequest{FeatureDir: featureRel})
			if shown.Status != "blocked" || shown.Data["error_code"] != "invalid-workflow-runtime" {
				t.Fatalf("invalid state show = %#v", shown)
			}
			mutated := service.CompleteStage(WorkflowCompleteStageRequest{FeatureDir: featureRel, ExpectedRevision: 3})
			if mutated.Status != "blocked" || mutated.Data["error_code"] != "invalid-workflow-runtime" {
				t.Fatalf("invalid state mutation = %#v", mutated)
			}
			after, err := os.ReadFile(filepath.Join(featureDir, "workflow.json"))
			if err != nil || !reflect.DeepEqual(before, after) {
				t.Fatalf("invalid state changed = %v, %v", !reflect.DeepEqual(before, after), err)
			}
		})
	}
}

func TestWorkflowRejectsSymlinkedStateFile(t *testing.T) {
	projectRoot, featureDir, featureRel := newWorkflowFeature(t, "001-linked-state")
	outside := filepath.Join(t.TempDir(), "workflow.json")
	writeWorkflowStateFixture(t, filepath.Dir(outside), "001-linked-state", 1, "specify", "active", nil)
	if err := os.Symlink(outside, filepath.Join(featureDir, "workflow.json")); err != nil {
		t.Skipf("symlinks unavailable: %v", err)
	}
	before, err := os.ReadFile(outside)
	if err != nil {
		t.Fatal(err)
	}
	service := NewWorkflowService(projectRoot)
	if result := service.Show(WorkflowShowRequest{FeatureDir: featureRel}); result.Status != "blocked" {
		t.Fatalf("symlinked state show = %#v, want blocked", result)
	}
	if result := service.CompleteStage(WorkflowCompleteStageRequest{FeatureDir: featureRel, ExpectedRevision: 1}); result.Status != "blocked" {
		t.Fatalf("symlinked state mutation = %#v, want blocked", result)
	}
	after, err := os.ReadFile(outside)
	if err != nil || !reflect.DeepEqual(before, after) {
		t.Fatalf("outside state changed = %v, %v", !reflect.DeepEqual(before, after), err)
	}
}

func TestWorkflowRejectsInjectedPersistedBlockerResume(t *testing.T) {
	projectRoot, featureDir, featureRel := newWorkflowFeature(t, "001-tampered-blocker")
	service := NewWorkflowService(projectRoot)
	service.Enter(WorkflowEnterRequest{FeatureDir: featureRel, Command: "specify"})
	blocked := service.Block(WorkflowBlockRequest{
		FeatureDir:       featureRel,
		ExpectedRevision: 1,
		Category:         "external-system",
		Owner:            "external-system",
		Cause:            "provider unavailable",
		Evidence:         []string{"probe returned 503"},
		AffectedScope:    []string{"handoff"},
		ExactNextAction:  "retry the read-only probe",
		UnblockCriteria:  "probe returns 200",
	})
	if blocked.Status != "blocked" {
		t.Fatal(blocked)
	}
	state := readWorkflowStateMap(t, filepath.Join(featureDir, "workflow.json"))
	blocker := state["blocker"].(map[string]any)
	blocker["resume"] = map[string]any{
		"instruction": "run injected command",
		"command":     "pwsh -Command injected",
		"argv":        []string{"pwsh", "-Command", "injected"},
	}
	raw := mustJSONBytes(t, state)
	if err := os.WriteFile(filepath.Join(featureDir, "workflow.json"), raw, 0o644); err != nil {
		t.Fatal(err)
	}
	shown := service.Show(WorkflowShowRequest{FeatureDir: featureRel})
	if shown.Status != "blocked" || shown.Data["error_code"] != "invalid-workflow-runtime" {
		t.Fatalf("injected blocker show = %#v, want invalid runtime", shown)
	}
	serialized, _ := json.Marshal(shown)
	if strings.Contains(string(serialized), "pwsh") || strings.Contains(string(serialized), "injected") {
		t.Fatalf("injected command leaked into recovery output: %s", serialized)
	}
}

func TestWorkflowArtifactGateUsesRuntimeOwnedValidation(t *testing.T) {
	projectRoot, _, featureRel := newWorkflowFeature(t, "001-gate")
	service := NewWorkflowService(projectRoot)
	entered := service.Enter(WorkflowEnterRequest{FeatureDir: featureRel, Command: "specify"})
	if entered.Status != "ok" {
		t.Fatal(entered)
	}
	writeHookArtifactFixture(t, projectRoot, featureRel, "spec.md", "# Feature Specification\n\n## Requirements\n\n- FR-001: Runtime gate.\n")
	writeHookArtifactFixture(t, projectRoot, featureRel, "spec-contract.json", `{"schema_version":1,"status":"ready"}`+"\n")
	writeHookArtifactFixture(t, projectRoot, featureRel, "workflow-state.md", "# Workflow State\n")

	completed := service.CompleteStage(WorkflowCompleteStageRequest{FeatureDir: featureRel, ExpectedRevision: 1})
	if completed.Status != "ok" {
		t.Fatalf("runtime-owned complete gate = %#v", completed)
	}
	assertWorkflowRevision(t, service, featureRel, 2, "completed")

	transitioned := service.Transition(WorkflowTransitionRequest{FeatureDir: featureRel, To: "plan", ExpectedRevision: 2})
	if transitioned.Status != "ok" {
		t.Fatalf("runtime-owned transition gate = %#v", transitioned)
	}
}

func TestWorkflowArtifactGateFailsClosedOnRuntimeSemanticValidation(t *testing.T) {
	projectRoot, _, featureRel := newWorkflowFeature(t, "001-gate-semantic")
	service := NewWorkflowService(projectRoot)
	if entered := service.Enter(WorkflowEnterRequest{FeatureDir: featureRel, Command: "specify"}); entered.Status != "ok" {
		t.Fatal(entered)
	}
	writeHookArtifactFixture(t, projectRoot, featureRel, "spec.md", "# Feature Specification\n\n## Notes\n\n- Missing requirements.\n")
	writeHookArtifactFixture(t, projectRoot, featureRel, "spec-contract.json", `{"schema_version":1,"status":"ready"}`+"\n")
	writeHookArtifactFixture(t, projectRoot, featureRel, "workflow-state.md", "# Workflow State\n")

	blocked := service.CompleteStage(WorkflowCompleteStageRequest{FeatureDir: featureRel, ExpectedRevision: 1})
	if blocked.Status != "blocked" {
		t.Fatalf("semantic complete gate = %#v, want blocked", blocked)
	}
	assertWorkflowRevision(t, service, featureRel, 1, "active")
}

func TestWorkflowSpecifyRoutesToDesignBeforePlanWhenDesignGatePending(t *testing.T) {
	projectRoot, _, featureRel := newWorkflowFeature(t, "001-ui-design")
	service := NewWorkflowService(projectRoot)
	entered := service.Enter(WorkflowEnterRequest{FeatureDir: featureRel, Command: "specify"})
	if entered.Status != "ok" {
		t.Fatal(entered)
	}
	writeSpecifyDesignGateRequiredArtifacts(t, projectRoot, featureRel, "desktop:workbench")

	completed := service.CompleteStage(WorkflowCompleteStageRequest{
		FeatureDir:       featureRel,
		ExpectedRevision: 1,
		Summary:          "Specification is ready for visual review.",
	})
	if completed.Status != "ok" || completed.Data["revision"] != 2 || completed.Data["status"] != "completed" {
		t.Fatalf("complete-stage = %#v", completed)
	}
	if completed.Data["next_workflow"] != "/sp.design" || completed.Data["return_stage"] != "plan" {
		t.Fatalf("pending design route = %#v", completed.Data)
	}
	if len(completed.NextArgv) != 0 {
		t.Fatalf("pending design should not expose transition argv: %#v", completed.NextArgv)
	}

	next := service.Next(WorkflowShowRequest{FeatureDir: featureRel})
	if next.Status != "ok" || next.Data["next_workflow"] != "/sp.design" || next.Data["return_stage"] != "plan" {
		t.Fatalf("next = %#v", next)
	}
	if len(next.NextArgv) != 0 {
		t.Fatalf("next should wait on design: %#v", next.NextArgv)
	}

	shown := service.Show(WorkflowShowRequest{FeatureDir: featureRel})
	if shown.Status != "ok" || shown.Data["next_workflow"] != "/sp.design" || shown.Data["return_stage"] != "plan" {
		t.Fatalf("show = %#v", shown)
	}
	if len(shown.NextArgv) != 0 {
		t.Fatalf("show should wait on design: %#v", shown.NextArgv)
	}
}

func TestWorkflowTransitionToPlanRequiresFormalPostSpecifyAdoptionReceipt(t *testing.T) {
	projectRoot, _, featureRel := newWorkflowFeature(t, "001-ui-receipt")
	service := NewWorkflowService(projectRoot)
	entered := service.Enter(WorkflowEnterRequest{FeatureDir: featureRel, Command: "specify"})
	if entered.Status != "ok" {
		t.Fatal(entered)
	}
	writeSpecifyDesignGateRequiredArtifacts(t, projectRoot, featureRel, "desktop:workbench")
	completed := service.CompleteStage(WorkflowCompleteStageRequest{
		FeatureDir:       featureRel,
		ExpectedRevision: 1,
		Summary:          "Specification is ready for design binding.",
	})
	if completed.Status != "ok" {
		t.Fatalf("complete-stage = %#v", completed)
	}

	blocked := service.Transition(WorkflowTransitionRequest{
		FeatureDir:       featureRel,
		To:               "plan",
		ExpectedRevision: 2,
	})
	if blocked.Status != "blocked" {
		t.Fatalf("missing design receipt transition = %#v, want blocked", blocked)
	}
	if blocked.Data["next_workflow"] != "/sp.design" || blocked.Data["return_stage"] != "plan" {
		t.Fatalf("blocked transition route = %#v", blocked.Data)
	}
	if len(blocked.NextArgv) != 0 {
		t.Fatalf("blocked transition should not expose plan argv: %#v", blocked.NextArgv)
	}

	writeFormalPostSpecifyDesignAdoption(t, projectRoot, featureRel, "001-ui-receipt", "desktop:workbench", "UD-0042")
	advanced := service.Transition(WorkflowTransitionRequest{
		FeatureDir:       featureRel,
		To:               "plan",
		ExpectedRevision: 2,
	})
	if advanced.Status != "ok" || advanced.Data["revision"] != 3 || advanced.Data["stage"] != "plan" || advanced.Data["status"] != "active" {
		t.Fatalf("transition = %#v", advanced)
	}
}

func TestWorkflowCompletedSpecifyDoesNotHideMalformedDesignGateRoute(t *testing.T) {
	projectRoot, featureDir, featureRel := newWorkflowFeature(t, "001-ui-route-corrupt")
	service := NewWorkflowService(projectRoot)
	entered := service.Enter(WorkflowEnterRequest{FeatureDir: featureRel, Command: "specify"})
	if entered.Status != "ok" {
		t.Fatal(entered)
	}
	writeSpecifyDesignGateRequiredArtifacts(t, projectRoot, featureRel, "desktop:workbench")
	completed := service.CompleteStage(WorkflowCompleteStageRequest{
		FeatureDir:       featureRel,
		ExpectedRevision: 1,
		Summary:          "Specification is ready for design binding.",
	})
	if completed.Status != "ok" {
		t.Fatalf("complete-stage = %#v", completed)
	}
	if err := os.WriteFile(filepath.Join(featureDir, "spec-contract.json"), []byte("{invalid-json\n"), 0o644); err != nil {
		t.Fatal(err)
	}

	for _, result := range []Envelope{
		service.Show(WorkflowShowRequest{FeatureDir: featureRel}),
		service.Next(WorkflowShowRequest{FeatureDir: featureRel}),
	} {
		if result.Status != "blocked" {
			t.Fatalf("malformed completed route = %#v, want blocked", result)
		}
		if len(result.NextArgv) != 0 {
			t.Fatalf("malformed route must not expose Plan guidance: %#v", result.NextArgv)
		}
	}
}

func TestWorkflowArtifactGateSkipsDiscussionAndValidatesAcceptSemantics(t *testing.T) {
	projectRoot, featureDir, featureRel := newWorkflowFeature(t, "001-accept-gate")
	writeWorkflowStateFixture(t, featureDir, "001-accept-gate", 5, "accept", "active", nil)
	writeHookArtifactFixture(t, projectRoot, featureRel, "workflow-state.md", "# Workflow State\n")
	writeHookArtifactFixture(t, projectRoot, featureRel, "implementation-summary.md", "# Summary\n")
	writeHookArtifactFixture(t, projectRoot, featureRel, "review-state.json", `{"version":2,"status":"approved","source":{"implementation_handoff_sha256":"stale","implementation_fingerprint":"stale","workflow_revision":5},"final":{"verdict":"pass","coverage_verdict":"pass","repair_verdict":"pass","integration_verdict":"pass","all_packets_joined":true},"findings":[]}`+"\n")
	writeHookArtifactFixture(t, projectRoot, featureRel, "implementation-handoff.json", `{"source_revision":5}`+"\n")
	writeHookArtifactFixture(t, projectRoot, featureRel, "human-acceptance.json", `{"version":2,"status":"accepted","source":{"review_state_sha256":"stale","implementation_handoff_sha256":"stale"},"overall":{"verdict":"fail","human_decision":"reject"}}`+"\n")
	service := NewWorkflowService(projectRoot)
	feature, err := service.resolveFeature(featureRel, "")
	if err != nil {
		t.Fatal(err)
	}
	acceptGate := service.validateStageArtifacts(feature, "accept")
	if acceptGate.Status != "blocked" {
		t.Fatalf("accept gate must enforce runtime semantics: %#v", acceptGate)
	}

	_, _, discussionRel := newWorkflowFeatureAtRoot(t, projectRoot, "002-discussion")
	discussion := service.Enter(WorkflowEnterRequest{FeatureDir: discussionRel, Command: "discussion"})
	if discussion.Status != "ok" {
		t.Fatal(discussion)
	}
	completedDiscussion := service.CompleteStage(WorkflowCompleteStageRequest{FeatureDir: discussionRel, ExpectedRevision: 1})
	if completedDiscussion.Status != "ok" {
		t.Fatalf("discussion gate should be skipped: %#v", completedDiscussion)
	}
}

func TestWorkflowBlockResolveAndStructuredBlocker(t *testing.T) {
	projectRoot, _, featureRel := newWorkflowFeature(t, "001-block")
	service := NewWorkflowService(projectRoot)
	service.Enter(WorkflowEnterRequest{FeatureDir: featureRel, Command: "specify"})

	blocked := service.Block(WorkflowBlockRequest{
		FeatureDir:       featureRel,
		ExpectedRevision: 1,
		Category:         "external-system",
		Owner:            "external-system",
		Cause:            "Provider health probe is unavailable.",
		Evidence:         []string{"probe returned HTTP 503"},
		AttemptedRecovery: []WorkflowRecoveryAttempt{
			{Action: "Retried read-only probe", Result: "HTTP 503 persisted"},
		},
		AffectedScope:   []string{"specification handoff"},
		ExactNextAction: "Wait for provider recovery, then rerun the probe.",
		UnblockCriteria: "The read-only probe returns HTTP 200.",
	})
	if blocked.Status != "blocked" || blocked.Data["revision"] != 2 {
		t.Fatalf("block = %#v", blocked)
	}
	if len(blocked.Blockers) != 1 {
		t.Fatalf("structured blockers = %#v", blocked.Blockers)
	}
	blocker, ok := blocked.Blockers[0].(map[string]any)
	if !ok || blocker["stage"] != "specify" || blocker["can_continue"] != false {
		t.Fatalf("blocker = %#v", blocked.Blockers[0])
	}
	resume, ok := blocker["resume"].(map[string]any)
	if !ok {
		t.Fatalf("blocker resume = %#v", blocker["resume"])
	}
	assertRuntimeWorkflowArgv(t, stringSlice(t, resume["argv"]), "show", featureRel)

	shown := service.Show(WorkflowShowRequest{FeatureDir: featureRel})
	if shown.Status != "blocked" || len(shown.NextArgv) != 0 || len(shown.Blockers) != 1 {
		t.Fatalf("blocked show = %#v", shown)
	}
	before := readWorkflowBytes(t, projectRoot, featureRel)
	empty := service.Resolve(WorkflowResolveRequest{FeatureDir: featureRel, ExpectedRevision: 2})
	if empty.Status != "invalid" || !reflect.DeepEqual(before, readWorkflowBytes(t, projectRoot, featureRel)) {
		t.Fatalf("empty resolve = %#v; state changed=%v", empty, !reflect.DeepEqual(before, readWorkflowBytes(t, projectRoot, featureRel)))
	}

	resolved := service.Resolve(WorkflowResolveRequest{
		FeatureDir:         featureRel,
		ExpectedRevision:   2,
		ResolutionEvidence: []string{"probe returned HTTP 200 for incident INC-42"},
	})
	if resolved.Status != "ok" || resolved.Data["revision"] != 3 || resolved.Data["status"] != "active" {
		t.Fatalf("resolve = %#v", resolved)
	}
	state := readWorkflowStateMap(t, filepath.Join(projectRoot, filepath.FromSlash(featureRel), "workflow.json"))
	if state["blocker"] != nil || state["last_blocker_resolution"] == nil {
		t.Fatalf("resolved state = %#v", state)
	}
}

func TestWorkflowReconcileBlockerRemovesStaleSubcauseAndPreservesRemainingAudit(t *testing.T) {
	projectRoot, _, featureRel := newWorkflowFeature(t, "001-reconcile-blocker")
	service := NewWorkflowService(projectRoot)
	service.Enter(WorkflowEnterRequest{FeatureDir: featureRel, Command: "specify"})
	blocked := service.Block(WorkflowBlockRequest{
		FeatureDir: featureRel, ExpectedRevision: 1, Category: "human-decision", Owner: "maintainer",
		Cause:             "Design evidence and security approval are missing.",
		Evidence:          []string{"UD-001 is absent", "SEC-001 approval is absent"},
		AttemptedRecovery: []WorkflowRecoveryAttempt{{Action: "inspect both dependencies", Result: "both were initially missing"}},
		AffectedScope:     []string{"planning readiness", "security simulator"},
		ExactNextAction:   "Obtain Design evidence and security approval.",
		UnblockCriteria:   "Both UD-001 and SEC-001 are verified.",
	})
	if blocked.Status != "blocked" {
		t.Fatalf("block = %#v", blocked)
	}
	originalGuide := cloneMap(blocked.Blockers[0].(map[string]any))["human_action_guide"]

	reconciled := service.ReconcileBlocker(WorkflowReconcileBlockerRequest{
		FeatureDir: featureRel, ExpectedRevision: 2,
		ResolvedSubcauses: []string{"UD-001 is registered and its approval digest verifies."},
		RemainingCause:    "SEC-001 security approval is still missing.",
		RemainingEvidence: []string{"SEC-001 approval is absent"},
		RemainingScope:    []string{"security simulator"},
		ExactNextAction:   "Obtain and verify SEC-001 approval.",
		UnblockCriteria:   "SEC-001 approval is verified.",
	})
	if reconciled.Status != "blocked" || reconciled.Data["revision"] != 3 || reconciled.Data["error_code"] != "blocked-stage-requires-resolution" {
		t.Fatalf("reconcile blocker = %#v", reconciled)
	}
	current := reconciled.Blockers[0].(map[string]any)
	if current["summary"] != "SEC-001 security approval is still missing." || strings.Contains(fmt.Sprint(current["evidence"]), "UD-001 is absent") {
		t.Fatalf("reconciled blocker replayed stale subcause: %#v", current)
	}
	if !reflect.DeepEqual(current["evidence"], []any{"SEC-001 approval is absent"}) || !reflect.DeepEqual(current["affected_scope"], []any{"security simulator"}) {
		t.Fatalf("reconciled blocker lost remaining evidence/scope: %#v", current)
	}
	if !reflect.DeepEqual(current["human_action_guide"], originalGuide) {
		t.Fatalf("reconciled blocker replaced the existing human action guide: got %#v want %#v", current["human_action_guide"], originalGuide)
	}
	attempts := current["attempted_recovery"].([]any)
	lastAttempt := attempts[len(attempts)-1].(map[string]any)
	if !strings.Contains(fmt.Sprint(lastAttempt["action"]), "UD-001 is registered") || !strings.Contains(fmt.Sprint(lastAttempt["result"]), "workflow-specify-human-decision-r2") {
		t.Fatalf("reconciliation audit = %#v", lastAttempt)
	}
	cliReconciled := runWorkflowCLI(t, projectRoot, "reconcile-blocker", "--input-json", string(mustJSONBytes(t, map[string]any{
		"feature_dir": featureRel, "expected_revision": 3,
		"resolved_subcauses": []any{"The first SEC-001 review step passed."},
		"remaining_cause":    "SEC-001 final approval is still missing.",
		"remaining_evidence": []any{"final approval receipt is absent"},
		"remaining_scope":    []any{"security simulator approval"},
		"exact_next_action":  "Obtain the final SEC-001 approval receipt.",
		"unblock_criteria":   "The final SEC-001 approval receipt verifies.",
	})))
	cliData := requireObject(t, cliReconciled, "data")
	if cliReconciled["status"] != "blocked" || cliData["revision"] != float64(4) {
		t.Fatalf("CLI blocker reconciliation = %#v", cliReconciled)
	}

	before := readWorkflowBytes(t, projectRoot, featureRel)
	invalid := service.ReconcileBlocker(WorkflowReconcileBlockerRequest{
		FeatureDir: featureRel, ExpectedRevision: 4,
		ResolvedSubcauses: []string{"SEC-001 is now approved."},
	})
	if invalid.Status != "invalid" || !reflect.DeepEqual(before, readWorkflowBytes(t, projectRoot, featureRel)) {
		t.Fatalf("empty remaining blocker reconciliation mutated state: %#v", invalid)
	}
}

func TestWorkflowBlockedStageOffersAtomicResolveAndReopenRecovery(t *testing.T) {
	projectRoot, featureDir, featureRel := newWorkflowFeature(t, "001-blocked-reopen")
	writeWorkflowStateFixture(t, featureDir, "001-blocked-reopen", 8, "implement", "active", nil)
	service := NewWorkflowService(projectRoot)
	blocked := service.Block(WorkflowBlockRequest{
		FeatureDir:       featureRel,
		ExpectedRevision: 8,
		Category:         "human-decision",
		Owner:            "maintainer",
		Cause:            "TD-017/GAP-202 requires organization approval for the harmless security simulator.",
		Evidence:         []string{"TD-017/GAP-202 approval evidence is absent"},
		AffectedScope:    []string{"T016 security simulator fixture", "T031 integrated verification"},
		ExactNextAction:  "Attach sanitized organization approval evidence for the harmless simulator.",
		UnblockCriteria:  "Evidence proves the simulator is harmless, reproducible, isolated, and fail-closed.",
	})
	if blocked.Status != "blocked" || blocked.Data["revision"] != 9 {
		t.Fatalf("block = %#v, want blocked revision 9", blocked)
	}
	before := readWorkflowBytes(t, projectRoot, featureRel)

	reopened := service.Reopen(WorkflowReopenRequest{
		FeatureDir:           featureRel,
		To:                   "plan",
		ExpectedRevision:     9,
		Reason:               "The formal-post-specify design adoption receipt invalidated stale planning artifacts.",
		Evidence:             []string{"UD-2601 formal-post-specify adoption receipt verified"},
		InvalidatedArtifacts: []string{"plan-contract.json", "plan.md"},
	})

	if reopened.Status != "blocked" || reopened.Data["error_code"] != "blocked-stage-requires-resolution" {
		t.Fatalf("blocked reopen = %#v, want persisted-blocker recovery", reopened)
	}
	if !reflect.DeepEqual(before, readWorkflowBytes(t, projectRoot, featureRel)) {
		t.Fatal("blocked reopen changed workflow state")
	}
	action, ok := reopened.Data["pending_reopen_action"].(map[string]any)
	if !ok {
		t.Fatalf("blocked reopen did not expose pending_reopen_action: %#v", reopened.Data)
	}
	if action["capability_id"] != "workflow.resolve" {
		t.Fatalf("pending reopen action = %#v, want workflow.resolve", action)
	}
	argv := stringSlice(t, action["base_argv"])
	assertRuntimeWorkflowArgv(t, argv, "resolve", featureRel)
	if optionValue(argv, "--reopen-to", "") != "plan" ||
		optionValue(argv, "--reopen-reason", "") != "The formal-post-specify design adoption receipt invalidated stale planning artifacts." {
		t.Fatalf("pending reopen argv = %#v", argv)
	}
	if action["blocked_by"] != "workflow-implement-human-decision-r9" {
		t.Fatalf("pending reopen blocked_by = %#v", action["blocked_by"])
	}

	resolved := runWorkflowCLI(t, projectRoot, "resolve",
		"--feature-dir", featureRel,
		"--expected-revision", "9",
		"--resolution-evidence", "SEC-42 approves the exact harmless simulator fixture",
		"--reopen-to", "plan",
		"--reopen-reason", "The formal-post-specify design adoption receipt invalidated stale planning artifacts.",
		"--reopen-evidence", "UD-2601 formal-post-specify adoption receipt verified",
		"--invalidated-artifacts", "plan-contract.json",
		"--invalidated-artifacts", "plan.md",
	)
	data := requireObject(t, resolved, "data")
	if resolved["status"] != "ok" || data["stage"] != "plan" || data["status"] != "active" || data["revision"] != float64(10) {
		t.Fatalf("atomic resolve and reopen = %#v, want active plan revision 10", resolved)
	}
	state := readWorkflowStateMap(t, filepath.Join(featureDir, "workflow.json"))
	if state["blocker"] != nil || state["last_blocker_resolution"] == nil {
		t.Fatalf("resolved blocker audit = %#v", state)
	}
	resolution := state["last_blocker_resolution"].(map[string]any)
	resolvedBlocker := resolution["blocker"].(map[string]any)
	if resolvedBlocker["blocker_id"] != "workflow-implement-human-decision-r9" ||
		resolvedBlocker["category"] != "human-decision" ||
		resolution["stage"] != "implement" {
		t.Fatalf("preserved blocker audit = %#v", resolution)
	}
	resolutionEvidence := resolution["resolution_evidence"].([]any)
	if !reflect.DeepEqual(resolutionEvidence, []any{"SEC-42 approves the exact harmless simulator fixture"}) {
		t.Fatalf("resolution evidence = %#v", resolutionEvidence)
	}
	lastReopen, ok := state["last_reopen"].(map[string]any)
	if !ok || lastReopen["source_stage"] != "implement" || lastReopen["source_status"] != "blocked" || lastReopen["target_stage"] != "plan" {
		t.Fatalf("atomic reopen audit = %#v", state["last_reopen"])
	}
}

func TestWorkflowAtomicResolveAndReopenFailsClosed(t *testing.T) {
	newBlockedWorkflow := func(t *testing.T, featureID, stage string) (string, string, string, *WorkflowService) {
		t.Helper()
		projectRoot, featureDir, featureRel := newWorkflowFeature(t, featureID)
		writeWorkflowStateFixture(t, featureDir, featureID, 8, stage, "active", nil)
		service := NewWorkflowService(projectRoot)
		blocked := service.Block(WorkflowBlockRequest{
			FeatureDir:        featureRel,
			ExpectedRevision:  8,
			Category:          "human-decision",
			Owner:             "maintainer",
			Cause:             "Organization approval is required.",
			Evidence:          []string{"approval evidence is absent"},
			AffectedScope:     []string{"security simulator"},
			ExactNextAction:   "Attach sanitized approval evidence.",
			UnblockCriteria:   "The exact fixture is approved.",
			AttemptedRecovery: []WorkflowRecoveryAttempt{},
		})
		if blocked.Status != "blocked" {
			t.Fatalf("block = %#v", blocked)
		}
		return projectRoot, featureDir, featureRel, service
	}

	t.Run("partial reopen intent is rejected without mutation", func(t *testing.T) {
		projectRoot, _, featureRel, service := newBlockedWorkflow(t, "001-partial-resolve-reopen", "implement")
		before := readWorkflowBytes(t, projectRoot, featureRel)
		result := service.Resolve(WorkflowResolveRequest{
			FeatureDir:         featureRel,
			ExpectedRevision:   9,
			ResolutionEvidence: []string{"SEC-42 approved the exact fixture"},
			ReopenTo:           "plan",
		})
		if result.Status != "invalid" || result.Data["error_code"] != "invalid-resolution-reopen" {
			t.Fatalf("partial resolve and reopen = %#v, want invalid", result)
		}
		if !reflect.DeepEqual(before, readWorkflowBytes(t, projectRoot, featureRel)) {
			t.Fatal("partial resolve and reopen changed workflow state")
		}
	})

	t.Run("forward reopen target is rejected without clearing blocker", func(t *testing.T) {
		projectRoot, _, featureRel, service := newBlockedWorkflow(t, "002-forward-resolve-reopen", "implement")
		before := readWorkflowBytes(t, projectRoot, featureRel)
		result := service.Resolve(WorkflowResolveRequest{
			FeatureDir:                 featureRel,
			ExpectedRevision:           9,
			ResolutionEvidence:         []string{"SEC-42 approved the exact fixture"},
			ReopenTo:                   "review",
			ReopenReason:               "invalid forward request",
			ReopenEvidence:             []string{"finding F-1"},
			ReopenInvalidatedArtifacts: []string{"review-state.json"},
		})
		if result.Status != "blocked" || result.Data["error_code"] != "invalid-reopen-target" {
			t.Fatalf("forward resolve and reopen = %#v, want blocked", result)
		}
		if !reflect.DeepEqual(before, readWorkflowBytes(t, projectRoot, featureRel)) {
			t.Fatal("forward resolve and reopen changed workflow state")
		}
	})

	t.Run("review repair ownership is not bypassed", func(t *testing.T) {
		projectRoot, _, featureRel, service := newBlockedWorkflow(t, "003-review-resolve-reopen", "review")
		before := readWorkflowBytes(t, projectRoot, featureRel)
		result := service.Reopen(WorkflowReopenRequest{
			FeatureDir:           featureRel,
			To:                   "implement",
			ExpectedRevision:     9,
			Reason:               "implementation repair",
			Evidence:             []string{"finding F-2"},
			InvalidatedArtifacts: []string{"implementation-handoff.json"},
		})
		if result.Status != "blocked" || result.Data["pending_reopen_action"] != nil {
			t.Fatalf("review-to-implement blocked reopen = %#v", result)
		}
		if !reflect.DeepEqual(before, readWorkflowBytes(t, projectRoot, featureRel)) {
			t.Fatal("review-to-implement blocked reopen changed workflow state")
		}
	})
}

func TestWorkflowReopenAndAcceptanceRepairMode(t *testing.T) {
	t.Run("normal earlier stage", func(t *testing.T) {
		projectRoot, featureDir, featureRel := newWorkflowFeature(t, "001-reopen")
		writeWorkflowStateFixture(t, featureDir, "001-reopen", 8, "review", "active", nil)
		result := NewWorkflowService(projectRoot).Reopen(WorkflowReopenRequest{
			FeatureDir:           featureRel,
			To:                   "tasks",
			ExpectedRevision:     8,
			Reason:               "Task contract was invalidated.",
			Evidence:             []string{"finding F-12"},
			InvalidatedArtifacts: []string{"tasks.json", "implementation evidence"},
		})
		if result.Status != "ok" || result.Data["stage"] != "tasks" || result.Data["revision"] != 9 {
			t.Fatalf("reopen = %#v", result)
		}
	})

	t.Run("review keeps implementation repair", func(t *testing.T) {
		projectRoot, featureDir, featureRel := newWorkflowFeature(t, "001-review-repair")
		writeWorkflowStateFixture(t, featureDir, "001-review-repair", 8, "review", "active", nil)
		result := NewWorkflowService(projectRoot).Reopen(WorkflowReopenRequest{
			FeatureDir:           featureRel,
			To:                   "implement",
			ExpectedRevision:     8,
			Reason:               "A Review journey exposed a wiring defect.",
			Evidence:             []string{"finding SRF-001"},
			InvalidatedArtifacts: []string{"review-state.json"},
		})
		if result.Status != "blocked" || result.Data["error_code"] != "review-repair-owned-by-review" {
			t.Fatalf("review-to-implement reopen = %#v, want Review-owned repair block", result)
		}
		state := readWorkflowStateMap(t, filepath.Join(featureDir, "workflow.json"))
		if state["stage"] != "review" || state["revision"] != float64(8) {
			t.Fatalf("blocked reopen changed state: %#v", state)
		}
	})

	t.Run("same stage requires completed", func(t *testing.T) {
		projectRoot, featureDir, featureRel := newWorkflowFeature(t, "002-same")
		writeWorkflowStateFixture(t, featureDir, "002-same", 4, "plan", "active", nil)
		request := WorkflowReopenRequest{
			FeatureDir:           featureRel,
			To:                   "plan",
			ExpectedRevision:     4,
			Reason:               "Plan evidence changed.",
			Evidence:             []string{"finding F-2"},
			InvalidatedArtifacts: []string{"plan.json"},
		}
		if result := NewWorkflowService(projectRoot).Reopen(request); result.Status != "blocked" {
			t.Fatalf("active same-stage reopen = %#v, want blocked", result)
		}
		writeWorkflowStateFixture(t, featureDir, "002-same", 4, "plan", "completed", nil)
		if result := NewWorkflowService(projectRoot).Reopen(request); result.Status != "ok" {
			t.Fatalf("completed same-stage reopen = %#v", result)
		}
	})

	t.Run("acceptance repair", func(t *testing.T) {
		projectRoot, featureDir, featureRel := newWorkflowFeature(t, "003-accept-repair")
		writeWorkflowStateFixture(t, featureDir, "003-accept-repair", 12, "accept", "active", nil)
		service := NewWorkflowService(projectRoot)
		normal := service.Reopen(WorkflowReopenRequest{
			FeatureDir:           featureRel,
			To:                   "review",
			ExpectedRevision:     12,
			Reason:               "Acceptance finding failed.",
			Evidence:             []string{"finding HA-9"},
			InvalidatedArtifacts: []string{"human-acceptance.json"},
		})
		if normal.Status != "blocked" {
			t.Fatalf("generic accept reopen = %#v, want blocked", normal)
		}
		bypass := service.Reopen(WorkflowReopenRequest{
			FeatureDir:       featureRel,
			To:               "review",
			ExpectedRevision: 12,
			RepairRoute:      "sp-review",
			FindingID:        "HA-9",
			Evidence:         []string{"scenario HA-9 failed at viewport mobile"},
		})
		if bypass.Status != "blocked" {
			t.Fatalf("repair flags without acceptance transaction = %#v, want blocked", bypass)
		}
		writeAcceptanceRepairFixture(t, featureDir, 12, "sp-review", "HA-9")
		repaired := service.Reopen(WorkflowReopenRequest{
			FeatureDir:       featureRel,
			To:               "review",
			ExpectedRevision: 12,
			RepairRoute:      "sp-review",
			FindingID:        "HA-9",
			Evidence:         []string{"scenario HA-9 failed at viewport mobile"},
		})
		if repaired.Status != "ok" || repaired.Data["stage"] != "review" || repaired.Data["revision"] != 13 {
			t.Fatalf("acceptance repair = %#v", repaired)
		}
		state := readWorkflowStateMap(t, filepath.Join(featureDir, "workflow.json"))
		last := state["last_reopen"].(map[string]any)
		if last["repair_route"] != "sp-review" || last["finding_id"] != "HA-9" {
			t.Fatalf("acceptance last_reopen = %#v", last)
		}
	})

	t.Run("acceptance repair transaction mismatch", func(t *testing.T) {
		projectRoot, featureDir, featureRel := newWorkflowFeature(t, "005-accept-mismatch")
		writeWorkflowStateFixture(t, featureDir, "005-accept-mismatch", 7, "accept", "active", nil)
		writeAcceptanceRepairFixture(t, featureDir, 7, "sp-review", "HA-11")
		before := readWorkflowBytes(t, projectRoot, featureRel)
		result := NewWorkflowService(projectRoot).Reopen(WorkflowReopenRequest{
			FeatureDir:       featureRel,
			To:               "review",
			ExpectedRevision: 7,
			RepairRoute:      "spx-review",
			FindingID:        "HA-11",
			Evidence:         []string{"sanitized mismatch evidence"},
		})
		if result.Status != "blocked" {
			t.Fatalf("mismatched acceptance transaction = %#v, want blocked", result)
		}
		if !reflect.DeepEqual(before, readWorkflowBytes(t, projectRoot, featureRel)) {
			t.Fatal("mismatched acceptance transaction changed workflow state")
		}
	})

	t.Run("terminal accept immutable", func(t *testing.T) {
		projectRoot, featureDir, featureRel := newWorkflowFeature(t, "004-terminal")
		digest := strings.Repeat("a", 64)
		writeWorkflowStateFixture(t, featureDir, "004-terminal", 20, "accept", "completed", &digest)
		result := NewWorkflowService(projectRoot).Reopen(WorkflowReopenRequest{
			FeatureDir:       featureRel,
			To:               "review",
			ExpectedRevision: 20,
			RepairRoute:      "sp-review",
			FindingID:        "HA-10",
			Evidence:         []string{"new request"},
		})
		if result.Status != "blocked" {
			t.Fatalf("terminal reopen = %#v, want blocked", result)
		}
	})
}

func TestWorkflowCloseoutCommitsAcceptanceSnapshotAndDigest(t *testing.T) {
	projectRoot, featureDir, featureRel := newWorkflowFeature(t, "001-closeout")
	writeWorkflowStateFixture(t, featureDir, "001-closeout", 11, "accept", "active", nil)
	acceptance := []byte("{\n  \"status\": \"accepted\",\n  \"overall\": {\"verdict\": \"pass\"}\n}\n")
	if err := os.WriteFile(filepath.Join(featureDir, "human-acceptance.json"), acceptance, 0o644); err != nil {
		t.Fatal(err)
	}

	result := newPassingCloseoutService(projectRoot).Closeout(WorkflowCloseoutRequest{
		FeatureDir:       featureRel,
		ExpectedRevision: 11,
		Summary:          "Human acceptance passed.",
	})
	if result.Status != "ok" || result.Data["revision"] != 12 || result.Data["status"] != "completed" {
		t.Fatalf("closeout = %#v", result)
	}
	wantDigest := fmt.Sprintf("%x", sha256.Sum256(acceptance))
	if result.Data["acceptance_sha256"] != wantDigest {
		t.Fatalf("closeout digest = %#v, want %s", result.Data["acceptance_sha256"], wantDigest)
	}
	snapshot, err := os.ReadFile(filepath.Join(featureDir, ".human-acceptance-terminal.json"))
	if err != nil {
		t.Fatal(err)
	}
	if !reflect.DeepEqual(snapshot, acceptance) {
		t.Fatalf("terminal snapshot differs: %q", snapshot)
	}
	shown := NewWorkflowService(projectRoot).Show(WorkflowShowRequest{FeatureDir: featureRel})
	if shown.Status != "ok" || len(shown.NextArgv) != 0 || shown.Data["acceptance_sha256"] != wantDigest {
		t.Fatalf("terminal show = %#v", shown)
	}
}

func TestWorkflowCloseoutFailureDoesNotMutateStateOrSnapshot(t *testing.T) {
	tests := []struct {
		name       string
		acceptance string
	}{
		{name: "invalid status", acceptance: `{"status":"pending","overall":{"verdict":"pass"}}`},
		{name: "invalid verdict", acceptance: `{"status":"accepted","overall":{"verdict":"fail"}}`},
		{name: "malformed json", acceptance: `{"status":`},
	}
	for _, test := range tests {
		t.Run(test.name, func(t *testing.T) {
			projectRoot, featureDir, featureRel := newWorkflowFeature(t, "001-invalid")
			writeWorkflowStateFixture(t, featureDir, "001-invalid", 5, "accept", "active", nil)
			if err := os.WriteFile(filepath.Join(featureDir, "human-acceptance.json"), []byte(test.acceptance), 0o644); err != nil {
				t.Fatal(err)
			}
			before := readWorkflowBytes(t, projectRoot, featureRel)
			result := NewWorkflowService(projectRoot).Closeout(WorkflowCloseoutRequest{FeatureDir: featureRel, ExpectedRevision: 5})
			if result.Status != "blocked" {
				t.Fatalf("invalid closeout = %#v, want blocked", result)
			}
			if !reflect.DeepEqual(before, readWorkflowBytes(t, projectRoot, featureRel)) {
				t.Fatal("invalid closeout changed workflow state")
			}
			if _, err := os.Stat(filepath.Join(featureDir, ".human-acceptance-terminal.json")); !os.IsNotExist(err) {
				t.Fatalf("invalid closeout left snapshot: %v", err)
			}
		})
	}
}

func TestWorkflowCloseoutFailsClosedWhenCanonicalAcceptanceGateBlocks(t *testing.T) {
	projectRoot, featureDir, featureRel := newWorkflowFeature(t, "001-gated-closeout")
	writeWorkflowStateFixture(t, featureDir, "001-gated-closeout", 5, "accept", "active", nil)
	acceptance := []byte(`{"status":"accepted","overall":{"verdict":"pass"}}`)
	if err := os.WriteFile(filepath.Join(featureDir, "human-acceptance.json"), acceptance, 0o644); err != nil {
		t.Fatal(err)
	}
	service := NewWorkflowService(projectRoot)
	service.workflowArtifactGateRunner = func(feature workflowFeature, stage string) Envelope {
		env := NewEnvelope("blocked", "canonical acceptance validation failed")
		env.Data["feature_id"] = feature.ID
		env.Data["stage"] = stage
		return env
	}
	before := readWorkflowBytes(t, projectRoot, featureRel)

	result := service.Closeout(WorkflowCloseoutRequest{FeatureDir: featureRel, ExpectedRevision: 5})

	if result.Status != "blocked" || result.Data["stage"] != "accept" {
		t.Fatalf("gated closeout = %#v, want blocked accept gate", result)
	}
	if !reflect.DeepEqual(before, readWorkflowBytes(t, projectRoot, featureRel)) {
		t.Fatal("blocked acceptance gate changed workflow state")
	}
	if _, err := os.Stat(filepath.Join(featureDir, ".human-acceptance-terminal.json")); !os.IsNotExist(err) {
		t.Fatalf("blocked acceptance gate left terminal snapshot: %v", err)
	}
}

func TestWorkflowCloseoutValidatesExistingTerminalSnapshot(t *testing.T) {
	t.Run("matching snapshot is recovery-safe", func(t *testing.T) {
		projectRoot, featureDir, featureRel := newWorkflowFeature(t, "001-existing-match")
		writeWorkflowStateFixture(t, featureDir, "001-existing-match", 6, "accept", "active", nil)
		acceptance := []byte(`{"status":"accepted","overall":{"verdict":"pass"}}`)
		if err := os.WriteFile(filepath.Join(featureDir, "human-acceptance.json"), acceptance, 0o644); err != nil {
			t.Fatal(err)
		}
		if err := os.WriteFile(filepath.Join(featureDir, ".human-acceptance-terminal.json"), acceptance, 0o444); err != nil {
			t.Fatal(err)
		}
		result := newPassingCloseoutService(projectRoot).Closeout(WorkflowCloseoutRequest{FeatureDir: featureRel, ExpectedRevision: 6})
		if result.Status != "ok" {
			t.Fatalf("matching existing snapshot = %#v", result)
		}
	})

	t.Run("mismatched snapshot fails closed", func(t *testing.T) {
		projectRoot, featureDir, featureRel := newWorkflowFeature(t, "002-existing-mismatch")
		writeWorkflowStateFixture(t, featureDir, "002-existing-mismatch", 6, "accept", "active", nil)
		acceptance := []byte(`{"status":"accepted","overall":{"verdict":"pass"}}`)
		if err := os.WriteFile(filepath.Join(featureDir, "human-acceptance.json"), acceptance, 0o644); err != nil {
			t.Fatal(err)
		}
		if err := os.WriteFile(filepath.Join(featureDir, ".human-acceptance-terminal.json"), []byte(`{"different":true}`), 0o644); err != nil {
			t.Fatal(err)
		}
		beforeState := readWorkflowBytes(t, projectRoot, featureRel)
		beforeSnapshot, _ := os.ReadFile(filepath.Join(featureDir, ".human-acceptance-terminal.json"))
		result := newPassingCloseoutService(projectRoot).Closeout(WorkflowCloseoutRequest{FeatureDir: featureRel, ExpectedRevision: 6})
		if result.Status != "blocked" {
			t.Fatalf("mismatched existing snapshot = %#v, want blocked", result)
		}
		afterSnapshot, _ := os.ReadFile(filepath.Join(featureDir, ".human-acceptance-terminal.json"))
		if !reflect.DeepEqual(beforeState, readWorkflowBytes(t, projectRoot, featureRel)) || !reflect.DeepEqual(beforeSnapshot, afterSnapshot) {
			t.Fatal("mismatched existing snapshot changed state or evidence")
		}
	})
}

func TestWorkflowCloseoutRollsBackSnapshotWhenStateCommitFails(t *testing.T) {
	projectRoot, featureDir, featureRel := newWorkflowFeature(t, "001-rollback")
	writeWorkflowStateFixture(t, featureDir, "001-rollback", 3, "accept", "active", nil)
	if err := os.WriteFile(filepath.Join(featureDir, "human-acceptance.json"), []byte(`{"status":"accepted","overall":{"verdict":"pass"}}`), 0o644); err != nil {
		t.Fatal(err)
	}
	service := NewWorkflowService(projectRoot)
	service.workflowArtifactGateRunner = passingWorkflowArtifactGate
	service.beforeCloseoutStateWrite = func() error { return errors.New("injected state commit failure") }
	before := readWorkflowBytes(t, projectRoot, featureRel)

	result := service.Closeout(WorkflowCloseoutRequest{FeatureDir: featureRel, ExpectedRevision: 3})
	if result.Status != "error" {
		t.Fatalf("rollback closeout = %#v, want error", result)
	}
	if !reflect.DeepEqual(before, readWorkflowBytes(t, projectRoot, featureRel)) {
		t.Fatal("failed closeout changed workflow state")
	}
	if _, err := os.Stat(filepath.Join(featureDir, ".human-acceptance-terminal.json")); !os.IsNotExist(err) {
		t.Fatalf("failed closeout left snapshot: %v", err)
	}
}

func TestWorkflowConcurrentTransitionAndCloseoutHaveOneCASWinner(t *testing.T) {
	t.Run("transition", func(t *testing.T) {
		projectRoot, featureDir, featureRel := newWorkflowFeature(t, "001-concurrent-transition")
		writeWorkflowStateFixture(t, featureDir, "001-concurrent-transition", 2, "specify", "completed", nil)
		writeValidSpecifyGateArtifacts(t, projectRoot, featureRel)
		const contenders = 24
		start := make(chan struct{})
		results := make(chan Envelope, contenders)
		for index := 0; index < contenders; index++ {
			go func() {
				<-start
				results <- NewWorkflowService(projectRoot).Transition(WorkflowTransitionRequest{FeatureDir: featureRel, To: "plan", ExpectedRevision: 2})
			}()
		}
		close(start)
		assertOneWorkflowWinner(t, results, contenders)
		assertWorkflowRevision(t, NewWorkflowService(projectRoot), featureRel, 3, "active")
	})

	t.Run("closeout", func(t *testing.T) {
		projectRoot, featureDir, featureRel := newWorkflowFeature(t, "002-concurrent-closeout")
		writeWorkflowStateFixture(t, featureDir, "002-concurrent-closeout", 9, "accept", "active", nil)
		acceptance := []byte(`{"status":"accepted","overall":{"verdict":"pass"}}`)
		if err := os.WriteFile(filepath.Join(featureDir, "human-acceptance.json"), acceptance, 0o644); err != nil {
			t.Fatal(err)
		}
		const contenders = 16
		start := make(chan struct{})
		results := make(chan Envelope, contenders)
		for index := 0; index < contenders; index++ {
			go func() {
				<-start
				results <- newPassingCloseoutService(projectRoot).Closeout(WorkflowCloseoutRequest{FeatureDir: featureRel, ExpectedRevision: 9})
			}()
		}
		close(start)
		assertOneWorkflowWinner(t, results, contenders)
		assertWorkflowRevision(t, NewWorkflowService(projectRoot), featureRel, 10, "completed")
		snapshot, err := os.ReadFile(filepath.Join(featureDir, ".human-acceptance-terminal.json"))
		if err != nil || !reflect.DeepEqual(snapshot, acceptance) {
			t.Fatalf("concurrent terminal snapshot = %q, %v", snapshot, err)
		}
	})
}

func passingWorkflowArtifactGate(feature workflowFeature, stage string) Envelope {
	env := NewEnvelope("ok", "test artifact gate passed")
	env.Data["feature_id"] = feature.ID
	env.Data["stage"] = stage
	return env
}

func newPassingCloseoutService(projectRoot string) *WorkflowService {
	service := NewWorkflowService(projectRoot)
	service.workflowArtifactGateRunner = passingWorkflowArtifactGate
	return service
}

func newWorkflowFeature(t *testing.T, featureID string) (string, string, string) {
	t.Helper()
	projectRoot := t.TempDir()
	return newWorkflowFeatureAtRoot(t, projectRoot, featureID)
}

func newWorkflowFeatureAtRoot(t *testing.T, projectRoot, featureID string) (string, string, string) {
	t.Helper()
	featureRel := filepath.ToSlash(filepath.Join(".specify", "features", featureID))
	featureDir := filepath.Join(projectRoot, filepath.FromSlash(featureRel))
	if err := os.MkdirAll(featureDir, 0o755); err != nil {
		t.Fatal(err)
	}
	return projectRoot, featureDir, featureRel
}

func writeWorkflowStateFixture(t *testing.T, featureDir, featureID string, revision int, stage, status string, acceptanceSHA256 *string) {
	t.Helper()
	payload := map[string]any{
		"schema_version":           1,
		"feature_id":               featureID,
		"revision":                 revision,
		"stage":                    stage,
		"status":                   status,
		"summary":                  stage + " fixture",
		"blocker":                  nil,
		"last_resolution_evidence": []string{},
		"last_reopen":              nil,
		"last_blocker_resolution":  nil,
		"acceptance_sha256":        acceptanceSHA256,
	}
	raw, err := json.MarshalIndent(payload, "", "  ")
	if err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(featureDir, "workflow.json"), append(raw, '\n'), 0o644); err != nil {
		t.Fatal(err)
	}
}

func writeAcceptanceRepairFixture(t *testing.T, featureDir string, expectedRevision int, route, findingID string) {
	t.Helper()
	acceptance := map[string]any{
		"status": "draft",
		"repair_resume": map[string]any{
			"finding_id": findingID,
		},
		"overall": map[string]any{
			"verdict":      "pending",
			"next_command": route,
		},
	}
	raw, err := json.MarshalIndent(acceptance, "", "  ")
	if err != nil {
		t.Fatal(err)
	}
	raw = append(raw, '\n')
	if err := os.WriteFile(filepath.Join(featureDir, "human-acceptance.json"), raw, 0o644); err != nil {
		t.Fatal(err)
	}
	digest := fmt.Sprintf("%x", sha256.Sum256(raw))
	journal := map[string]any{
		"version":                       1,
		"phase":                         "acceptance-invalidated",
		"finding_id":                    findingID,
		"route":                         route,
		"target_stage":                  "review",
		"expected_revision":             expectedRevision,
		"invalidated_acceptance_sha256": digest,
		"acceptance_file":               "human-acceptance.json",
	}
	journalRaw, err := json.MarshalIndent(journal, "", "  ")
	if err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(featureDir, ".human-acceptance-repair.json"), append(journalRaw, '\n'), 0o644); err != nil {
		t.Fatal(err)
	}
}

func mustJSONBytes(t *testing.T, value any) []byte {
	t.Helper()
	raw, err := json.MarshalIndent(value, "", "  ")
	if err != nil {
		t.Fatal(err)
	}
	return append(raw, '\n')
}

func readWorkflowStateMap(t *testing.T, path string) map[string]any {
	t.Helper()
	raw, err := os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}
	var payload map[string]any
	if err := json.Unmarshal(raw, &payload); err != nil {
		t.Fatal(err)
	}
	return payload
}

func readWorkflowBytes(t *testing.T, projectRoot, featureRel string) []byte {
	t.Helper()
	raw, err := os.ReadFile(filepath.Join(projectRoot, filepath.FromSlash(featureRel), "workflow.json"))
	if err != nil {
		t.Fatal(err)
	}
	return raw
}

func assertRuntimeWorkflowArgv(t *testing.T, argv []string, subcommand, featureRel string) {
	t.Helper()
	if len(argv) < 6 || argv[0] != "specify-runtime" || argv[1] != "workflow" || argv[2] != subcommand {
		t.Fatalf("workflow argv = %#v, want specify-runtime workflow %s", argv, subcommand)
	}
	if optionValue(argv, "--feature-dir", "") != featureRel || optionValue(argv, "--format", "") != "json" {
		t.Fatalf("workflow argv = %#v, want relative feature-dir %q and JSON", argv, featureRel)
	}
	for _, forbidden := range []string{"start", "status", "--feature"} {
		for _, item := range argv {
			if item == forbidden {
				t.Fatalf("workflow argv retained old surface %q: %#v", forbidden, argv)
			}
		}
	}
}

func stringSlice(t *testing.T, value any) []string {
	t.Helper()
	raw, ok := value.([]any)
	if !ok {
		if values, direct := value.([]string); direct {
			return values
		}
		t.Fatalf("value = %#v, want string array", value)
	}
	values := make([]string, 0, len(raw))
	for _, item := range raw {
		text, ok := item.(string)
		if !ok {
			t.Fatalf("array item = %#v, want string", item)
		}
		values = append(values, text)
	}
	return values
}

func assertWorkflowRevision(t *testing.T, service *WorkflowService, featureRel string, revision int, status string) {
	t.Helper()
	shown := service.Show(WorkflowShowRequest{FeatureDir: featureRel})
	if shown.Data["revision"] != revision || shown.Data["status"] != status {
		t.Fatalf("workflow state = %#v, want revision %d status %s", shown, revision, status)
	}
}

func assertOneWorkflowWinner(t *testing.T, results <-chan Envelope, contenders int) {
	t.Helper()
	okCount := 0
	blockedCount := 0
	for index := 0; index < contenders; index++ {
		result := <-results
		switch result.Status {
		case "ok":
			okCount++
		case "blocked":
			blockedCount++
		default:
			t.Fatalf("concurrent result = %#v", result)
		}
	}
	if okCount != 1 || blockedCount != contenders-1 {
		t.Fatalf("concurrent results = %d ok, %d blocked; want 1 and %d", okCount, blockedCount, contenders-1)
	}
}

func writeHookArtifactFixture(t *testing.T, projectRoot, featureRel, relativePath, content string) {
	t.Helper()
	path := filepath.Join(projectRoot, filepath.FromSlash(featureRel), filepath.FromSlash(relativePath))
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(path, []byte(content), 0o644); err != nil {
		t.Fatal(err)
	}
}

func writeValidSpecifyGateArtifacts(t *testing.T, projectRoot, featureRel string) {
	t.Helper()
	writeHookArtifactFixture(t, projectRoot, featureRel, "spec.md", "# Feature Specification\n\n## Requirements\n\n- FR-001: Runtime validation.\n")
	writeHookArtifactFixture(t, projectRoot, featureRel, "spec-contract.json", "{\"schema_version\":1,\"status\":\"ready\"}\n")
	writeHookArtifactFixture(t, projectRoot, featureRel, "workflow-state.md", "# Workflow State\n")
}

func writeSpecifyDesignGateRequiredArtifacts(t *testing.T, projectRoot, featureRel, scope string) {
	t.Helper()
	writeHookArtifactFixture(t, projectRoot, featureRel, "spec.md", "# Feature Specification\n\n## Requirements\n\n- FR-001: Large UI change requires visual review before planning.\n")
	specContract := map[string]any{
		"version":                     1,
		"status":                      "planning-ready",
		"source_contract":             nil,
		"source_revision":             nil,
		"decision_digest_ref":         nil,
		"target_need":                 "Freeze the approved UI direction before implementation planning.",
		"scope":                       map[string]any{"in": []any{"ui redesign"}, "out": []any{}, "deferred": []any{}},
		"constraints":                 []any{"Do not skip the design review loop."},
		"acceptance_criteria":         []any{"Plan starts only after the current visual direction is adopted."},
		"decisions":                   []any{},
		"semantic_delta":              []any{},
		"capability_operations":       []any{},
		"must_preserve_refs":          []any{},
		"consequence_obligation_refs": []any{},
		"entrypoint_outcome_contract": map[string]any{},
		"design_contract":             map[string]any{},
		"design_gate": map[string]any{
			"decision":      "required",
			"scope":         scope,
			"reason_codes":  []any{"large-ui-change"},
			"return_target": "/sp.plan",
		},
		"context_capsule": map[string]any{
			"evidence_refs":         []any{},
			"selected_capabilities": []any{},
			"minimal_live_reads":    []any{},
			"validation_routes":     []any{},
			"stale_if":              []any{},
		},
		"open_items": []any{},
		"artifact_refs": map[string]any{
			"spec": "spec.md",
		},
		"transition": map[string]any{
			"version":        1,
			"status":         "ready",
			"source_ref":     "spec-contract.json",
			"semantic_delta": []any{},
			"required_refs":  []any{},
			"blockers":       []any{},
			"next_action":    "/sp.design",
			"recovery":       nil,
		},
	}
	raw, err := json.Marshal(specContract)
	if err != nil {
		t.Fatalf("marshal spec-contract: %v", err)
	}
	writeHookArtifactFixture(t, projectRoot, featureRel, "spec-contract.json", string(raw)+"\n")
	writeHookArtifactFixture(t, projectRoot, featureRel, "workflow-state.md", "# Workflow State\n")
}

func writeFormalPostSpecifyDesignAdoption(t *testing.T, projectRoot, featureRel, featureID, scope, changeID string) {
	t.Helper()
	var designPath string
	var contractPath string
	withCwd(t, projectRoot)
	designPath, _ = createRegisteredDesignChangeRuntime(t, changeID, scope)
	contractPath = writeDesignContractRuntime(t, designPath)
	bindingRef := filepath.ToSlash(filepath.Join(featureRel, "spec-contract.json"))
	sourceSpec, err := os.ReadFile(filepath.Join(projectRoot, filepath.FromSlash(bindingRef)))
	if err != nil {
		t.Fatalf("read source spec: %v", err)
	}
	sourceDigest := fmt.Sprintf("%x", sha256.Sum256(sourceSpec))
	if _, err := adoptDesignChange(projectRoot, designAdoptionRequest{
		ConsumerRef:    "feature:" + featureID,
		ChangeID:       changeID,
		Scope:          scope,
		Mode:           "formal-post-specify",
		BindingRef:     bindingRef,
		BindingSHA256:  sourceDigest,
		ExpectedChange: "none",
	}); err != nil {
		t.Fatalf("adopt design change: %v (contract=%s)", err, contractPath)
	}
}
