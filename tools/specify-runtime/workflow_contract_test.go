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
	installWorkflowGateLauncher(t, projectRoot)
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

func TestWorkflowArtifactGateIsFailClosedForCompleteAndTransition(t *testing.T) {
	projectRoot, _, featureRel := newWorkflowFeature(t, "001-gate")
	service := NewWorkflowService(projectRoot)
	entered := service.Enter(WorkflowEnterRequest{FeatureDir: featureRel, Command: "specify"})
	if entered.Status != "ok" {
		t.Fatal(entered)
	}

	missingLauncher := service.CompleteStage(WorkflowCompleteStageRequest{FeatureDir: featureRel, ExpectedRevision: 1})
	if missingLauncher.Status != "blocked" {
		t.Fatalf("missing launcher gate = %#v, want blocked", missingLauncher)
	}
	assertWorkflowRevision(t, service, featureRel, 1, "active")

	installWorkflowGateLauncher(t, projectRoot)
	setWorkflowGateStatus(t, projectRoot, "blocked")
	blocked := service.CompleteStage(WorkflowCompleteStageRequest{FeatureDir: featureRel, ExpectedRevision: 1})
	if blocked.Status != "blocked" {
		t.Fatalf("blocked complete gate = %#v", blocked)
	}
	assertWorkflowRevision(t, service, featureRel, 1, "active")

	setWorkflowGateStatus(t, projectRoot, "ok")
	completed := service.CompleteStage(WorkflowCompleteStageRequest{FeatureDir: featureRel, ExpectedRevision: 1})
	if completed.Status != "ok" {
		t.Fatalf("passing complete gate = %#v", completed)
	}

	setWorkflowGateStatus(t, projectRoot, "blocked")
	transitionBlocked := service.Transition(WorkflowTransitionRequest{FeatureDir: featureRel, To: "plan", ExpectedRevision: 2})
	if transitionBlocked.Status != "blocked" {
		t.Fatalf("blocked transition gate = %#v", transitionBlocked)
	}
	assertWorkflowRevision(t, service, featureRel, 2, "completed")

	setWorkflowGateStatus(t, projectRoot, "ok")
	transitioned := service.Transition(WorkflowTransitionRequest{FeatureDir: featureRel, To: "plan", ExpectedRevision: 2})
	if transitioned.Status != "ok" {
		t.Fatalf("passing transition gate = %#v", transitioned)
	}

	_, _, discussionRel := newWorkflowFeatureAtRoot(t, projectRoot, "002-discussion")
	discussion := service.Enter(WorkflowEnterRequest{FeatureDir: discussionRel, Command: "discussion"})
	if discussion.Status != "ok" {
		t.Fatal(discussion)
	}
	setWorkflowGateStatus(t, projectRoot, "blocked")
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

	result := NewWorkflowService(projectRoot).Closeout(WorkflowCloseoutRequest{
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
		result := NewWorkflowService(projectRoot).Closeout(WorkflowCloseoutRequest{FeatureDir: featureRel, ExpectedRevision: 6})
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
		result := NewWorkflowService(projectRoot).Closeout(WorkflowCloseoutRequest{FeatureDir: featureRel, ExpectedRevision: 6})
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
		installWorkflowGateLauncher(t, projectRoot)
		writeWorkflowStateFixture(t, featureDir, "001-concurrent-transition", 2, "specify", "completed", nil)
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
				results <- NewWorkflowService(projectRoot).Closeout(WorkflowCloseoutRequest{FeatureDir: featureRel, ExpectedRevision: 9})
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

func TestWorkflowArtifactGateHelper(t *testing.T) {
	if os.Getenv("SPECIFY_RUNTIME_WORKFLOW_GATE") != "1" {
		return
	}
	args := os.Args
	separator := -1
	for index, arg := range args {
		if arg == "--" {
			separator = index
			break
		}
	}
	valid := separator >= 0 && len(args[separator+1:]) >= 8
	gateArgs := []string{}
	if separator >= 0 {
		gateArgs = args[separator+1:]
	}
	valid = valid && gateArgs[0] == "hook" && gateArgs[1] == "validate-artifacts" && optionValue(gateArgs, "--command", "") != "" && optionValue(gateArgs, "--feature-dir", "") != "" && optionValue(gateArgs, "--format", "") == "json"
	status := "ok"
	if raw, err := os.ReadFile(filepath.Join(".specify", "test-workflow-gate-status")); err == nil {
		status = strings.TrimSpace(string(raw))
	}
	if !valid {
		status = "invalid"
	}
	payload := map[string]any{
		"status":   status,
		"summary":  "test artifact gate",
		"blockers": []any{},
	}
	if status != "ok" && status != "warn" && status != "repaired" {
		payload["blockers"] = []any{map[string]any{"code": "test-artifact-gate", "stage": optionValue(gateArgs, "--command", "unknown")}}
	}
	_ = json.NewEncoder(os.Stdout).Encode(payload)
	if status == "blocked" || status == "repairable-block" {
		os.Exit(10)
	}
	if status != "ok" && status != "warn" && status != "repaired" {
		os.Exit(2)
	}
	os.Exit(0)
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

func installWorkflowGateLauncher(t *testing.T, projectRoot string) {
	t.Helper()
	payload := map[string]any{
		"specify_launcher": map[string]any{
			"argv": []string{os.Args[0], "-test.run=^TestWorkflowArtifactGateHelper$", "--"},
		},
	}
	raw, err := json.Marshal(payload)
	if err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(projectRoot, ".specify", "config.json"), raw, 0o644); err != nil {
		t.Fatal(err)
	}
	setWorkflowGateStatus(t, projectRoot, "ok")
}

func setWorkflowGateStatus(t *testing.T, projectRoot, status string) {
	t.Helper()
	if err := os.WriteFile(filepath.Join(projectRoot, ".specify", "test-workflow-gate-status"), []byte(status), 0o644); err != nil {
		t.Fatal(err)
	}
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
