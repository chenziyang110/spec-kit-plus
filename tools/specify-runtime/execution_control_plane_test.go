package main

import (
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"

	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/runcontrol"
)

func TestExecutionAnnounceMakesFastVisibleBeforeClaim(t *testing.T) {
	root := initCoordinationCLIRepository(t)
	announced := announceExecutionCLI(t, root, "activity-fast-visible", "fast", "copy-fix", "", []string{"src/copy"}, []map[string]any{{
		"type": "capability", "key": "copy-rendering", "mode": "exclusive", "confidence": "candidate",
	}})
	if announced["phase"] != "announced" || announced["work_id"] != "activity-fast-visible" {
		t.Fatalf("announced activity = %#v", announced)
	}

	code, payload := invokeCoordinationCLI(t,
		"execution", "overview",
		"--project-root", root,
		"--current-work-id", "activity-fast-visible",
		"--format", "json",
	)
	if code != 0 || payload["status"] != "ok" {
		t.Fatalf("execution overview = code %d envelope %#v", code, payload)
	}
	data := requireObject(t, payload, "data")
	if data["coordination_revision"].(float64) < 1 || len(stringValue(data["snapshot_sha256"])) != 64 {
		t.Fatalf("versioned overview = %#v", data)
	}
	activity := executionOverviewActivity(t, requireObjectSlice(t, data, "activities"), "fast", "copy-fix", "")
	if activity["activity_registered"] != true || activity["lifecycle_phase"] != "announced" {
		t.Fatalf("registered activity = %#v", activity)
	}
	if strings.Join(anyStringSlice(activity["planned_write_scope"]), ",") != "src/copy" {
		t.Fatalf("planned scope = %#v", activity)
	}
	resources := requireObjectSlice(t, activity, "semantic_resources")
	if resources[0]["type"] != "capability" || resources[0]["key"] != "copy-rendering" || resources[0]["confidence"] != "candidate" {
		t.Fatalf("semantic resources = %#v", resources)
	}
}

func TestExecutionGuardAndCompleteEnforceOneAuditedLifecycle(t *testing.T) {
	root, _, _ := seedCloseoutApplyRuntime(t)
	gitRun(t, root, "init")
	r3SeedGraph(t, root, []string{"src/allowed/main.go"})
	ownedScope := []string{"src/allowed", mutationCognitionReceiptFileName, ".specify/project-cognition"}
	announced := announceExecutionCLI(t, root, "activity-audited", "fast", "audited", "", ownedScope, []map[string]any{{
		"type": "feature", "key": "audited", "mode": "exclusive", "confidence": "candidate",
	}})
	overview := executionOverviewCLI(t, root, "activity-audited")
	guarded := guardExecutionCLI(t, root, announced, overview, ownedScope, []map[string]any{{
		"type": "feature", "key": "audited", "mode": "exclusive", "confidence": "confirmed",
	}})
	if guarded["schema"] != "execution-guard-v1" || guarded["phase"] != "executing" {
		t.Fatalf("guard receipt = %#v", guarded)
	}

	mustWriteScriptDomainTest(t, filepath.Join(root, "src", "outside.go"), "package outside\n")
	code, blocked := invokeCoordinationCLI(t,
		"execution", "complete", "activity-audited",
		"--project-root", root,
		"--expected-revision", executionJSONNumberString(guarded["work_revision"]),
		"--fence", executionJSONNumberString(guarded["fence"]),
		"--validation-json", `[{"command":"go test ./...","result":"passed"}]`,
		"--reason", "verify actual paths",
		"--format", "json",
	)
	if code != ExitCodeForStatus("blocked") || blocked["status"] != "blocked" {
		t.Fatalf("out-of-scope completion = code %d envelope %#v", code, blocked)
	}
	blockers := requireObjectSlice(t, blocked, "blockers")
	if blockers[0]["code"] != "unclaimed_changed_paths" || strings.Join(anyStringSlice(blockers[0]["paths"]), ",") != "src/outside.go" {
		t.Fatalf("scope audit blocker = %#v", blockers)
	}
	recovery := requireObject(t, requireObject(t, blocked, "data"), "resolution_action")
	if recovery["owner"] != "agent" || recovery["human_action_required"] != false || recovery["kind"] != "refresh-overview-and-guard-scope" {
		t.Fatalf("scope audit recovery = %#v", recovery)
	}
	if argv := requireStringArray(t, recovery, "overview_argv"); len(argv) < 4 || argv[1] != "execution" || argv[2] != "overview" {
		t.Fatalf("scope audit overview recovery argv = %#v", argv)
	}

	if err := os.Remove(filepath.Join(root, "src", "outside.go")); err != nil {
		t.Fatal(err)
	}
	mustWriteScriptDomainTest(t, filepath.Join(root, "src", "allowed", "main.go"), "package allowed\n")
	proof := r3Seal(t, root, r3Begin(t, root, ".", "fast", stringValue(guarded["work_id"]), nil, nil))
	r3Apply(t, root, proof)
	code, completedPayload := invokeCoordinationCLI(t,
		"execution", "complete", "activity-audited",
		"--project-root", root,
		"--expected-revision", executionJSONNumberString(guarded["work_revision"]),
		"--fence", executionJSONNumberString(guarded["fence"]),
		"--validation-json", `[{"command":"go test ./...","result":"passed"}]`,
		"--reason", "verified execution",
		"--binding-id", proof.ID,
		"--format", "json",
	)
	if code != 0 || completedPayload["status"] != "ok" {
		t.Fatalf("execution complete = code %d envelope %#v", code, completedPayload)
	}
	completed := requireObject(t, requireObject(t, completedPayload, "data"), "execution_completion")
	if completed["schema"] != "execution-completion-v1" || completed["phase"] != "completed" || completed["work_status"] != "completed" {
		t.Fatalf("completion receipt = %#v", completed)
	}
	productPaths := []string{}
	for _, path := range anyStringSlice(completed["actual_changed_paths"]) {
		if closeoutBindingProductPath(path, ".") {
			productPaths = append(productPaths, path)
		}
	}
	if strings.Join(productPaths, ",") != "src/allowed/main.go" || len(stringValue(completed["completion_sha256"])) != 64 {
		t.Fatalf("audited completion = %#v", completed)
	}

	code, shownPayload := invokeCoordinationCLI(t, "execution", "show", "activity-audited", "--project-root", root, "--format", "json")
	if code != 0 || shownPayload["status"] != "ok" {
		t.Fatalf("execution show = code %d envelope %#v", code, shownPayload)
	}
	shown := requireObject(t, requireObject(t, shownPayload, "data"), "execution_activity")
	if shown["phase"] != "completed" || shown["work_status"] != "completed" {
		t.Fatalf("shown completion = %#v", shown)
	}
}

func TestExecutionCompleteRejectsMissingImplementTaskSource(t *testing.T) {
	root := initCoordinationCLIRepository(t)
	featureID := "feature-missing-task"
	taskID := "T001"
	taskIndexPath := filepath.Join(root, ".specify", "features", featureID, "task-index.json")
	taskIndexScope := filepath.ToSlash(filepath.Join(".specify", "features", featureID, "task-index.json"))
	writeExecutionOverviewImplementFixture(t, root, featureID, taskID, "pending", []string{"src/missing-task", taskIndexScope})

	announced := announceExecutionCLI(
		t, root, "activity-missing-implement-task", "implement", featureID, taskID,
		[]string{"src/missing-task", taskIndexScope}, nil,
	)
	overview := executionOverviewCLI(t, root, "activity-missing-implement-task")
	guarded := guardExecutionCLI(t, root, announced, overview, []string{"src/missing-task", taskIndexScope}, nil)
	mustWriteScriptDomainTest(t, taskIndexPath, `{"version":2,"status":"ready","feature_id":"feature-missing-task","tasks":[]}`+"\n")

	code, payload := invokeCoordinationCLI(t,
		"execution", "complete", "activity-missing-implement-task",
		"--project-root", root,
		"--expected-revision", executionJSONNumberString(guarded["work_revision"]),
		"--fence", executionJSONNumberString(guarded["fence"]),
		"--validation-json", `[{"command":"go test ./...","result":"passed"}]`,
		"--reason", "reject disappeared task source",
		"--format", "json",
	)
	if code != ExitCodeForStatus("blocked") || payload["status"] != "blocked" {
		t.Fatalf("missing task completion = code %d envelope %#v", code, payload)
	}
	blockers := requireObjectSlice(t, payload, "blockers")
	if blockers[0]["code"] != "task_source_missing" || blockers[0]["workflow"] != "implement" {
		t.Fatalf("missing implement task blocker = %#v", blockers)
	}
}

func TestManualImplementCompletionRequiresWorkflowRuntimeProvenance(t *testing.T) {
	root := initCoordinationCLIRepository(t)
	featureID := "feature-manual-workflow"
	taskID := "T001"
	featureDir := filepath.Join(root, ".specify", "features", featureID)
	workflowRef := filepath.ToSlash(filepath.Join(".specify", "features", featureID, "workflow.json"))
	taskIndexRef := filepath.ToSlash(filepath.Join(".specify", "features", featureID, "task-index.json"))
	writeExecutionOverviewImplementFixture(t, root, featureID, taskID, "accepted", []string{workflowRef, taskIndexRef})
	writeWorkflowStateFixture(t, featureDir, featureID, 7, "implement", "active", nil)

	announced := announceExecutionCLI(
		t, root, "activity-manual-workflow", "implement", featureID, taskID,
		[]string{workflowRef, taskIndexRef}, nil,
	)
	overview := executionOverviewCLI(t, root, "activity-manual-workflow")
	guarded := guardExecutionCLI(t, root, announced, overview, []string{workflowRef, taskIndexRef}, nil)

	workflowPath := filepath.Join(featureDir, "workflow.json")
	baseline, err := os.ReadFile(workflowPath)
	if err != nil {
		t.Fatal(err)
	}
	manuallyEdited := readWorkflowStateMap(t, workflowPath)
	manuallyEdited["summary"] = "valid-shaped manual edit"
	writeTaskRuntimeFixture(t, workflowPath, manuallyEdited)
	code, blocked := invokeCoordinationCLI(t,
		"execution", "complete", "activity-manual-workflow",
		"--project-root", root,
		"--expected-revision", executionJSONNumberString(guarded["work_revision"]),
		"--fence", executionJSONNumberString(guarded["fence"]),
		"--validation-json", `[{"command":"go test ./...","result":"passed"}]`,
		"--reason", "reject manual workflow mutation",
		"--format", "json",
	)
	if code != ExitCodeForStatus("blocked") || blocked["status"] != "blocked" || requireObject(t, blocked, "data")["error_code"] != "workflow_control_plane_invalid" {
		t.Fatalf("manual implement accepted unproven workflow mutation: code=%d payload=%#v", code, blocked)
	}
	if err := os.WriteFile(workflowPath, baseline, 0o644); err != nil {
		t.Fatal(err)
	}

	workflowService := NewWorkflowService(root)
	blockedWorkflow := workflowService.Block(WorkflowBlockRequest{
		FeatureDir: featureDir, ExpectedRevision: 7, Category: "technical-failure", Owner: "agent",
		Cause: "manual execution needed a local repair", Evidence: []string{"focused reproduction"},
		AttemptedRecovery: []WorkflowRecoveryAttempt{{Action: "repair local state", Result: "repaired"}},
		AffectedScope:     []string{"T001 completion"}, ExactNextAction: "resolve after verification",
		UnblockCriteria: "focused verification passes",
	})
	if blockedWorkflow.Status != "blocked" {
		t.Fatalf("official block = %#v", blockedWorkflow)
	}
	resolvedWorkflow := workflowService.Resolve(WorkflowResolveRequest{
		FeatureDir: featureDir, ExpectedRevision: 8, ResolutionEvidence: []string{"focused verification passed"},
	})
	if resolvedWorkflow.Status != "ok" || resolvedWorkflow.Data["revision"] != 9 {
		t.Fatalf("official resolve = %#v", resolvedWorkflow)
	}

	code, completedPayload := invokeCoordinationCLI(t,
		"execution", "complete", "activity-manual-workflow",
		"--project-root", root,
		"--expected-revision", executionJSONNumberString(guarded["work_revision"]),
		"--fence", executionJSONNumberString(guarded["fence"]),
		"--validation-json", `[{"command":"go test ./...","result":"passed"}]`,
		"--reason", "accept official workflow recovery",
		"--format", "json",
	)
	if code != 0 || completedPayload["status"] != "ok" {
		t.Fatalf("manual implement did not resume after official workflow recovery: code=%d payload=%#v", code, completedPayload)
	}
	completed := requireObject(t, requireObject(t, completedPayload, "data"), "execution_completion")
	if got := anyStringSlice(completed["workflow_control_plane_paths"]); len(got) != 1 || got[0] != workflowRef || completed["workflow_audit_preserved"] != true {
		t.Fatalf("manual workflow completion accounting = %#v", completed)
	}
	if receiptRef := stringValue(completed["workflow_mutation_receipt_ref"]); !strings.HasPrefix(receiptRef, ".specify/runtime/workflow-mutations/") || len(stringValue(completed["workflow_mutation_receipt_sha256"])) != 64 {
		t.Fatalf("manual workflow mutation receipt accounting = %#v", completed)
	}
}

func TestLegacyImplementCompletionUsesMatchingWorkflowRoot(t *testing.T) {
	root := initCoordinationCLIRepository(t)
	featureID := "feature-legacy-workflow"
	taskID := "T001"
	featureRef := filepath.ToSlash(filepath.Join("specs", featureID))
	featureDir := filepath.Join(root, filepath.FromSlash(featureRef))
	workflowRef := featureRef + "/workflow.json"
	taskIndexRef := featureRef + "/task-index.json"
	writeTaskRuntimeFixture(t, filepath.Join(featureDir, "task-index.json"), map[string]any{
		"version": 2, "status": "ready", "feature_id": featureID,
		"tasks": []any{map[string]any{
			"id": taskID, "objective": "legacy task", "status": "accepted",
			"expected_write_scope": []any{workflowRef, taskIndexRef},
		}},
	})
	writeWorkflowStateFixture(t, featureDir, featureID, 7, "implement", "active", nil)

	code, announcedPayload := invokeCoordinationCLI(t,
		"execution", "announce", "--project-root", root,
		"--activity-id", "activity-legacy-workflow", "--workflow", "implement",
		"--subject-id", featureID, "--item-id", taskID, "--source-ref", taskIndexRef,
		"--summary", "legacy implement", "--agent-id", "legacy-agent", "--adapter-id", "codex",
		"--next-action", "guard legacy execution", "--lease-seconds", "1800",
		"--planned-write-scope-json", marshalWorkBoardCLIJSON(t, []string{workflowRef, taskIndexRef}),
		"--resources-json", "[]", "--format", "json",
	)
	if code != 0 || announcedPayload["status"] != "ok" {
		t.Fatalf("legacy execution announce = code=%d payload=%#v", code, announcedPayload)
	}
	announced := requireObject(t, requireObject(t, announcedPayload, "data"), "execution_activity")
	overview := executionOverviewCLI(t, root, "activity-legacy-workflow")
	guarded := guardExecutionCLI(t, root, announced, overview, []string{workflowRef, taskIndexRef}, nil)

	workflowService := NewWorkflowService(root)
	blockedWorkflow := workflowService.Block(WorkflowBlockRequest{
		FeatureDir: featureRef, ExpectedRevision: 7, Category: "technical-failure", Owner: "agent",
		Cause: "legacy execution needed local recovery", Evidence: []string{"legacy focused reproduction"},
		AttemptedRecovery: []WorkflowRecoveryAttempt{{Action: "repair legacy state", Result: "repaired"}},
		AffectedScope:     []string{"legacy T001 completion"}, ExactNextAction: "resolve after legacy verification",
		UnblockCriteria: "legacy focused verification passes",
	})
	if blockedWorkflow.Status != "blocked" {
		t.Fatalf("legacy workflow block = %#v", blockedWorkflow)
	}
	resolvedWorkflow := workflowService.Resolve(WorkflowResolveRequest{
		FeatureDir: featureRef, ExpectedRevision: 8, ResolutionEvidence: []string{"legacy focused verification passed"},
	})
	if resolvedWorkflow.Status != "ok" {
		t.Fatalf("legacy workflow resolve = %#v", resolvedWorkflow)
	}

	code, completedPayload := invokeCoordinationCLI(t,
		"execution", "complete", "activity-legacy-workflow", "--project-root", root,
		"--expected-revision", executionJSONNumberString(guarded["work_revision"]),
		"--fence", executionJSONNumberString(guarded["fence"]),
		"--validation-json", `[{"command":"go test ./...","result":"passed"}]`,
		"--reason", "complete legacy workflow recovery", "--format", "json",
	)
	if code != 0 || completedPayload["status"] != "ok" {
		t.Fatalf("legacy implement did not resume on its matching root: code=%d payload=%#v", code, completedPayload)
	}
	completed := requireObject(t, requireObject(t, completedPayload, "data"), "execution_completion")
	if got := anyStringSlice(completed["workflow_control_plane_paths"]); len(got) != 1 || got[0] != workflowRef || completed["workflow_audit_preserved"] != true {
		t.Fatalf("legacy workflow completion accounting = %#v", completed)
	}
}

func TestLegacyManualExecutionBaselineFallbackUsesPersistedSourceRef(t *testing.T) {
	for _, featureRoot := range []string{filepath.ToSlash(filepath.Join(".specify", "specs")), "specs"} {
		featureID := "feature-upgrade-legacy"
		featureRef := filepath.ToSlash(filepath.Join(filepath.FromSlash(featureRoot), featureID))
		registration := runcontrol.ExecutionRegistration{Activity: runcontrol.ExecutionActivity{
			Workflow: runcontrol.ExecutionWorkflowImplement, SubjectID: featureID,
			SourceRef:    featureRef + "/task-index.json",
			BaselineJSON: `{"head_commit":"legacy","dirty_paths":[],"path_digests":{}}`,
		}}
		binding, captured, ok := executionWorkflowControlPlaneBaseline(registration)
		if !ok || captured || binding.FeatureRef != featureRef || binding.WorkflowRef != featureRef+"/workflow.json" {
			t.Fatalf("legacy baseline fallback for %s = binding %#v captured=%v ok=%v", featureRoot, binding, captured, ok)
		}
	}
}

func TestExecutionCompleteRejectsMissingQuickTaskSource(t *testing.T) {
	root := initCoordinationCLIRepository(t)
	quickID := "260826-missing-task"
	writeQuickCoordinationFixture(t, root, quickID, "Missing Quick task", "planned", []string{"src/missing-quick"})
	statusScope := filepath.ToSlash(filepath.Join(".planning", "quick", quickID+"-fixture", "STATUS.md"))

	announced := announceExecutionCLI(
		t, root, "activity-missing-quick-task", "quick", quickID, "",
		[]string{"src/missing-quick", statusScope}, nil,
	)
	overview := executionOverviewCLI(t, root, "activity-missing-quick-task")
	guarded := guardExecutionCLI(t, root, announced, overview, []string{"src/missing-quick", statusScope}, nil)
	if err := os.Remove(filepath.Join(root, filepath.FromSlash(statusScope))); err != nil {
		t.Fatal(err)
	}

	code, payload := invokeCoordinationCLI(t,
		"execution", "complete", "activity-missing-quick-task",
		"--project-root", root,
		"--expected-revision", executionJSONNumberString(guarded["work_revision"]),
		"--fence", executionJSONNumberString(guarded["fence"]),
		"--validation-json", `[{"command":"go test ./...","result":"passed"}]`,
		"--reason", "reject disappeared Quick task",
		"--format", "json",
	)
	if code != ExitCodeForStatus("blocked") || payload["status"] != "blocked" {
		t.Fatalf("missing Quick completion = code %d envelope %#v", code, payload)
	}
	blockers := requireObjectSlice(t, payload, "blockers")
	if blockers[0]["code"] != "task_source_missing" || blockers[0]["workflow"] != "quick" {
		t.Fatalf("missing Quick task blocker = %#v", blockers)
	}
}

func TestExecutionGuardRejectsOverviewChangedAfterObservation(t *testing.T) {
	root := initCoordinationCLIRepository(t)
	announced := announceExecutionCLI(t, root, "activity-stale-cli", "debug", "stale-cli", "", []string{"src/stale"}, nil)
	overview := executionOverviewCLI(t, root, "activity-stale-cli")
	_ = announceExecutionCLI(t, root, "activity-racer-cli", "fast", "racer-cli", "", []string{"src/racer"}, nil)

	code, payload := invokeCoordinationCLI(t,
		"execution", "guard", "activity-stale-cli",
		"--project-root", root,
		"--expected-revision", executionJSONNumberString(announced["work_revision"]),
		"--fence", executionJSONNumberString(announced["fence"]),
		"--expected-overview-revision", executionJSONNumberString(overview["coordination_revision"]),
		"--expected-overview-sha256", stringValue(overview["snapshot_sha256"]),
		"--write-scope-json", `["src/stale"]`,
		"--resources-json", `[]`,
		"--reason", "stale guard",
		"--format", "json",
	)
	if code != ExitCodeForStatus("blocked") || payload["status"] != "blocked" {
		t.Fatalf("stale guard = code %d envelope %#v", code, payload)
	}
	blockers := requireObjectSlice(t, payload, "blockers")
	if blockers[0]["code"] != "overview_stale" {
		t.Fatalf("stale blocker = %#v", blockers)
	}
}

func TestExecutionGuardBlocksSemanticConflictAcrossDifferentFiles(t *testing.T) {
	root := initCoordinationCLIRepository(t)
	first := announceExecutionCLI(t, root, "activity-api-first", "quick", "api-first", "", []string{"src/first"}, nil)
	firstOverview := executionOverviewCLI(t, root, "activity-api-first")
	_ = guardExecutionCLI(t, root, first, firstOverview, []string{"src/first"}, []map[string]any{{
		"type": "api", "key": "/v1/nodes", "mode": "exclusive", "confidence": "confirmed",
	}})

	second := announceExecutionCLI(t, root, "activity-api-second", "implement", "feature-api", "T002", []string{"src/second"}, nil)
	secondOverview := executionOverviewCLI(t, root, "activity-api-second")
	resources := marshalWorkBoardCLIJSON(t, []map[string]any{{
		"type": "api", "key": "/v1/nodes", "mode": "exclusive", "confidence": "confirmed",
	}})
	code, payload := invokeCoordinationCLI(t,
		"execution", "guard", "activity-api-second",
		"--project-root", root,
		"--expected-revision", executionJSONNumberString(second["work_revision"]),
		"--fence", executionJSONNumberString(second["fence"]),
		"--expected-overview-revision", executionJSONNumberString(secondOverview["coordination_revision"]),
		"--expected-overview-sha256", stringValue(secondOverview["snapshot_sha256"]),
		"--write-scope-json", `["src/second"]`,
		"--resources-json", resources,
		"--reason", "claim shared API",
		"--format", "json",
	)
	if code != ExitCodeForStatus("blocked") || payload["status"] != "blocked" {
		t.Fatalf("semantic conflict = code %d envelope %#v", code, payload)
	}
	blockers := requireObjectSlice(t, payload, "blockers")
	if blockers[0]["code"] != "semantic_resource_conflict" || blockers[0]["resource_type"] != "api" || blockers[0]["resource_key"] != "/v1/nodes" {
		t.Fatalf("semantic blocker = %#v", blockers)
	}
}

func TestExecutionOverviewReturnsChangesSinceRevision(t *testing.T) {
	root := initCoordinationCLIRepository(t)
	initial := executionOverviewCLI(t, root, "")
	_ = announceExecutionCLI(t, root, "activity-change-feed", "fast", "change-feed", "", []string{"src/change"}, nil)

	code, payload := invokeCoordinationCLI(t,
		"execution", "overview",
		"--project-root", root,
		"--since-revision", executionJSONNumberString(initial["coordination_revision"]),
		"--format", "json",
	)
	if code != 0 || payload["status"] != "ok" {
		t.Fatalf("changed overview = code %d envelope %#v", code, payload)
	}
	data := requireObject(t, payload, "data")
	changes := requireObjectSlice(t, data, "changes")
	if len(changes) == 0 || data["changed_since_revision"] != true {
		t.Fatalf("change feed = %#v", data)
	}
}

func TestExecutionCheckpointAdvancesSelectedAndValidatingPhases(t *testing.T) {
	root := initCoordinationCLIRepository(t)
	announced := announceExecutionCLI(t, root, "activity-checkpoint", "debug", "checkpoint", "", []string{"src/checkpoint"}, nil)
	code, selectedPayload := invokeCoordinationCLI(t,
		"execution", "checkpoint", "activity-checkpoint",
		"--project-root", root,
		"--expected-revision", executionJSONNumberString(announced["work_revision"]),
		"--fence", executionJSONNumberString(announced["fence"]),
		"--phase", "selected",
		"--next-action", "claim selected task",
		"--lease-seconds", "1900",
		"--format", "json",
	)
	if code != 0 || selectedPayload["status"] != "ok" {
		t.Fatalf("execution checkpoint selected = code %d envelope %#v", code, selectedPayload)
	}
	selected := requireObject(t, requireObject(t, selectedPayload, "data"), "execution_activity")
	if selected["phase"] != "selected" {
		t.Fatalf("selected activity = %#v", selected)
	}
	overview := executionOverviewCLI(t, root, "activity-checkpoint")
	guarded := guardExecutionCLI(t, root, selected, overview, []string{"src/checkpoint"}, nil)
	code, validatingPayload := invokeCoordinationCLI(t,
		"execution", "checkpoint", "activity-checkpoint",
		"--project-root", root,
		"--expected-revision", executionJSONNumberString(guarded["work_revision"]),
		"--fence", executionJSONNumberString(guarded["fence"]),
		"--phase", "validating",
		"--next-action", "run integrated verification",
		"--lease-seconds", "2000",
		"--format", "json",
	)
	if code != 0 || validatingPayload["status"] != "ok" {
		t.Fatalf("execution checkpoint validating = code %d envelope %#v", code, validatingPayload)
	}
	validating := requireObject(t, requireObject(t, validatingPayload, "data"), "execution_activity")
	if validating["phase"] != "validating" || validating["next_action"] != "run integrated verification" {
		t.Fatalf("validating activity = %#v", validating)
	}
}

func TestLegacyWorkFinishCannotBypassExecutionCompletionAudit(t *testing.T) {
	root := initCoordinationCLIRepository(t)
	announced := announceExecutionCLI(t, root, "activity-no-bypass", "fast", "no-bypass", "", []string{"src/no-bypass"}, nil)
	code, payload := invokeCoordinationCLI(t,
		"work", "finish", "activity-no-bypass",
		"--project-root", root,
		"--expected-revision", executionJSONNumberString(announced["work_revision"]),
		"--fence", executionJSONNumberString(announced["fence"]),
		"--reason", "skip execution audit",
		"--format", "json",
	)
	if code != ExitCodeForStatus("blocked") || payload["status"] != "blocked" {
		t.Fatalf("legacy finish bypass = code %d envelope %#v", code, payload)
	}
	data := requireObject(t, payload, "data")
	if data["error_code"] != "execution_completion_required" {
		t.Fatalf("legacy finish blocker = %#v", payload)
	}
}

func TestExecutionOverviewWarnsCandidateSemanticResourceOverlap(t *testing.T) {
	root := initCoordinationCLIRepository(t)
	resource := []map[string]any{{
		"type": "api", "key": "/v1/shared", "mode": "exclusive", "confidence": "candidate",
	}}
	_ = announceExecutionCLI(t, root, "activity-plan-a", "fast", "plan-a", "", []string{"src/a"}, resource)
	_ = announceExecutionCLI(t, root, "activity-plan-b", "debug", "plan-b", "", []string{"src/b"}, resource)

	code, payload := invokeCoordinationCLI(t, "execution", "overview", "--project-root", root, "--format", "json")
	if code != 0 || payload["status"] != "ok" {
		t.Fatalf("semantic planned overview = code %d envelope %#v", code, payload)
	}
	data := requireObject(t, payload, "data")
	if data["coordination_state"] != "attention" {
		t.Fatalf("semantic planned state = %#v", data)
	}
	signal := quickCoordinationObjectByField(t, requireObjectSlice(t, data, "signals"), "code", "planned_resource_overlap")
	if signal["resource_type"] != "api" || signal["resource_key"] != "/v1/shared" {
		t.Fatalf("semantic planned overlap = %#v", signal)
	}
}

func TestExecutionRecoverySignalCarriesActionableState(t *testing.T) {
	root := initCoordinationCLIRepository(t)
	code, announcedPayload := invokeCoordinationCLI(t,
		"execution", "announce",
		"--project-root", root,
		"--activity-id", "activity-recovery",
		"--workflow", "fast",
		"--subject-id", "recovery",
		"--summary", "recovery activity",
		"--agent-id", "recovery-agent",
		"--adapter-id", "codex",
		"--lease-seconds", "1",
		"--planned-write-scope-json", `["src/recovery"]`,
		"--resources-json", `[{"type":"feature","key":"recovery","mode":"exclusive","confidence":"candidate"}]`,
		"--format", "json",
	)
	if code != 0 || announcedPayload["status"] != "ok" {
		t.Fatalf("announce recovery activity = code %d envelope %#v", code, announcedPayload)
	}
	mustWriteScriptDomainTest(t, filepath.Join(root, "src", "recovery", "main.go"), "package recovery\n")
	time.Sleep(1200 * time.Millisecond)

	code, payload := invokeCoordinationCLI(t, "execution", "overview", "--project-root", root, "--format", "json")
	if code != 0 || payload["status"] != "ok" {
		t.Fatalf("recovery overview = code %d envelope %#v", code, payload)
	}
	data := requireObject(t, payload, "data")
	signal := quickCoordinationObjectByField(t, requireObjectSlice(t, data, "signals"), "code", "work_recovery_hold")
	if signal["recovery_action"] != "resume_or_abandon_after_inspection" || len(stringValue(signal["recovery_sha256"])) != 64 {
		t.Fatalf("recovery signal = %#v", signal)
	}
	if strings.Join(anyStringSlice(signal["observed_paths"]), ",") != "src/recovery/main.go" || executionInt64(signal["last_heartbeat_at_ms"]) < 1 {
		t.Fatalf("recovery evidence = %#v", signal)
	}
	activity := executionOverviewActivity(t, requireObjectSlice(t, data, "activities"), "fast", "recovery", "")
	if activity["lifecycle_phase"] != "interrupted" {
		t.Fatalf("interrupted lifecycle = %#v", activity)
	}
}

func TestExecutionGuardUsesRegisteredWorkIdentityWhenIDsDiffer(t *testing.T) {
	root := initCoordinationCLIRepository(t)
	code, payload := invokeCoordinationCLI(t,
		"execution", "announce",
		"--project-root", root,
		"--activity-id", "activity-distinct-id",
		"--work-id", "work-distinct-id",
		"--workflow", "debug",
		"--subject-id", "distinct-id",
		"--summary", "distinct execution and Work ids",
		"--agent-id", "distinct-agent",
		"--adapter-id", "codex",
		"--planned-write-scope-json", `["src/distinct"]`,
		"--format", "json",
	)
	if code != 0 || payload["status"] != "ok" {
		t.Fatalf("announce distinct ids = code %d envelope %#v", code, payload)
	}
	announced := requireObject(t, requireObject(t, payload, "data"), "execution_activity")
	overview := executionOverviewCLI(t, root, "work-distinct-id")
	guarded := guardExecutionCLI(t, root, announced, overview, []string{"src/distinct"}, nil)
	if guarded["work_id"] != "work-distinct-id" || guarded["activity_id"] != "activity-distinct-id" {
		t.Fatalf("guarded distinct ids = %#v", guarded)
	}
}

func announceExecutionCLI(
	t *testing.T,
	root string,
	activityID string,
	workflow string,
	subjectID string,
	itemID string,
	plannedScope []string,
	resources []map[string]any,
) map[string]any {
	t.Helper()
	if resources == nil {
		resources = []map[string]any{}
	}
	args := []string{
		"execution", "announce",
		"--project-root", root,
		"--activity-id", activityID,
		"--workflow", workflow,
		"--subject-id", subjectID,
		"--summary", workflow + " " + subjectID,
		"--agent-id", activityID + "-agent",
		"--adapter-id", "codex",
		"--next-action", "await execution guard",
		"--lease-seconds", "1800",
		"--planned-write-scope-json", marshalWorkBoardCLIJSON(t, plannedScope),
		"--resources-json", marshalWorkBoardCLIJSON(t, resources),
		"--format", "json",
	}
	if itemID != "" {
		args = append(args[:8], append([]string{"--item-id", itemID}, args[8:]...)...)
	}
	code, payload := invokeCoordinationCLI(t, args...)
	if code != 0 || payload["status"] != "ok" {
		t.Fatalf("execution announce %s = code %d envelope %#v", activityID, code, payload)
	}
	return requireObject(t, requireObject(t, payload, "data"), "execution_activity")
}

func executionOverviewCLI(t *testing.T, root, currentActivityID string) map[string]any {
	t.Helper()
	args := []string{"execution", "overview", "--project-root", root, "--format", "json"}
	if currentActivityID != "" {
		args = append(args[:4], append([]string{"--current-work-id", currentActivityID}, args[4:]...)...)
	}
	code, payload := invokeCoordinationCLI(t, args...)
	if code != 0 || payload["status"] != "ok" {
		t.Fatalf("execution overview = code %d envelope %#v", code, payload)
	}
	return requireObject(t, payload, "data")
}

func guardExecutionCLI(t *testing.T, root string, announced, overview map[string]any, scope []string, resources []map[string]any) map[string]any {
	t.Helper()
	code, payload := invokeCoordinationCLI(t,
		"execution", "guard", stringValue(announced["activity_id"]),
		"--project-root", root,
		"--expected-revision", executionJSONNumberString(announced["work_revision"]),
		"--fence", executionJSONNumberString(announced["fence"]),
		"--expected-overview-revision", executionJSONNumberString(overview["coordination_revision"]),
		"--expected-overview-sha256", stringValue(overview["snapshot_sha256"]),
		"--write-scope-json", marshalWorkBoardCLIJSON(t, scope),
		"--resources-json", marshalWorkBoardCLIJSON(t, resources),
		"--reason", "start guarded execution",
		"--format", "json",
	)
	if code != 0 || payload["status"] != "ok" {
		t.Fatalf("execution guard = code %d envelope %#v", code, payload)
	}
	return requireObject(t, requireObject(t, payload, "data"), "execution_guard")
}

func executionJSONNumberString(value any) string {
	if number, ok := value.(json.Number); ok {
		return number.String()
	}
	return strings.TrimSuffix(strings.TrimSuffix(stringValue(value), ".0"), ".")
}
