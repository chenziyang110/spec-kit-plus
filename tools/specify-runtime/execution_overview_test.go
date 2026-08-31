package main

import (
	"encoding/json"
	"fmt"
	"path/filepath"
	"strings"
	"testing"
)

func TestExecutionOverviewJoinsFastDebugImplementAndQuickActivity(t *testing.T) {
	root := initCoordinationCLIRepository(t)
	writeQuickCoordinationFixture(t, root, "260826-upload", "Upload recognition", "executing", []string{"src/upload"})
	writeQuickCoordinationFixture(t, root, "260826-nodes", "Node workbench", "planned", []string{"src/nodes"})
	writeExecutionOverviewImplementFixture(t, root, "feature-ledger", "T001", "in_progress", []string{"src/ledger"})

	beginExecutionOverviewWork(t, root, "work-quick", "quick:260826-upload", "Upload recognition", "src/upload")
	beginExecutionOverviewWork(t, root, "work-debug", "debug:overlay-dismiss", "Overlay dismissal", "src/overlay")
	beginExecutionOverviewWork(t, root, "work-fast", "fast:small-copy-fix", "Small copy fix", "src/copy")
	beginExecutionOverviewWork(t, root, "work-implement", "implement:feature-ledger", "Ledger implementation", "src/ledger")

	code, payload := invokeCoordinationCLI(t,
		"execution", "overview",
		"--project-root", root,
		"--current-work-id", "work-quick",
		"--format", "json",
	)
	if code != 0 || payload["status"] != "ok" {
		t.Fatalf("execution overview = code %d envelope %#v", code, payload)
	}
	data := requireObject(t, payload, "data")
	if data["snapshot_kind"] != "execution-overview-v1" || data["coordination_state"] != "clear" {
		t.Fatalf("overview state = %#v", data)
	}
	if data["workflow_count"] != float64(4) || data["execution_count"] != float64(5) {
		t.Fatalf("overview counts = %#v", data)
	}
	if data["open_task_count"] != float64(3) || data["live_work_count"] != float64(4) {
		t.Fatalf("source counts = %#v", data)
	}
	if data["untracked_open_task_count"] != float64(1) {
		t.Fatalf("untracked task count = %#v", data)
	}

	activities := requireObjectSlice(t, data, "activities")
	quick := executionOverviewActivity(t, activities, "quick", "260826-upload", "")
	if quick["tracking_state"] != "work_tracked" || quick["current"] != true {
		t.Fatalf("quick activity = %#v", quick)
	}
	if strings.Join(anyStringSlice(quick["work_ids"]), ",") != "work-quick" {
		t.Fatalf("quick correlation = %#v", quick)
	}
	_ = executionOverviewActivity(t, activities, "fast", "small-copy-fix", "")
	debug := executionOverviewActivity(t, activities, "debug", "overlay-dismiss", "")
	if debug["tracking_state"] != "work_only" {
		t.Fatalf("debug activity = %#v", debug)
	}
	implementation := executionOverviewActivity(t, activities, "implement", "feature-ledger", "T001")
	if implementation["tracking_state"] != "work_tracked" || implementation["task_status"] != "in_progress" {
		t.Fatalf("implement activity = %#v", implementation)
	}
	backlog := executionOverviewActivity(t, activities, "quick", "260826-nodes", "")
	if backlog["tracking_state"] != "task_only" {
		t.Fatalf("untracked Quick activity = %#v", backlog)
	}

	signals := requireObjectSlice(t, data, "signals")
	openTaskSignal := quickCoordinationObjectByField(t, signals, "code", "open_task_untracked")
	if openTaskSignal["level"] != "info" || openTaskSignal["workflow"] != "quick" {
		t.Fatalf("open task signal = %#v", openTaskSignal)
	}
}

func TestExecutionOverviewBlocksDuplicateLiveOwnersOfSameTask(t *testing.T) {
	root := initCoordinationCLIRepository(t)
	writeQuickCoordinationFixture(t, root, "260826-shared", "Shared task", "executing", []string{"src/shared-a", "src/shared-b"})
	beginExecutionOverviewWork(t, root, "work-owner-a", "quick:260826-shared", "Shared task A", "src/shared-a")
	beginExecutionOverviewWork(t, root, "work-owner-b", "quick:260826-shared", "Shared task B", "src/shared-b")

	code, payload := invokeCoordinationCLI(t, "execution", "overview", "--project-root", root, "--format", "json")
	if code != ExitCodeForStatus("blocked") || payload["status"] != "blocked" {
		t.Fatalf("execution overview = code %d envelope %#v", code, payload)
	}
	data := requireObject(t, payload, "data")
	if data["coordination_state"] != "blocked" || data["blocker_count"] != float64(1) {
		t.Fatalf("blocked overview = %#v", data)
	}
	signals := requireObjectSlice(t, data, "signals")
	duplicate := quickCoordinationObjectByField(t, signals, "code", "duplicate_task_owner")
	if duplicate["task_ref"] != "quick:260826-shared" {
		t.Fatalf("duplicate owner signal = %#v", duplicate)
	}
}

func TestExecutionOverviewWarnsWhenExecutingTaskHasNoWorkAuthority(t *testing.T) {
	root := initCoordinationCLIRepository(t)
	writeExecutionOverviewImplementFixture(t, root, "feature-untracked", "T009", "in_progress", []string{"src/untracked"})

	code, payload := invokeCoordinationCLI(t, "execution", "overview", "--project-root", root, "--format", "json")
	if code != 0 || payload["status"] != "ok" {
		t.Fatalf("execution overview = code %d envelope %#v", code, payload)
	}
	data := requireObject(t, payload, "data")
	if data["coordination_state"] != "attention" || data["warning_count"] != float64(1) {
		t.Fatalf("attention overview = %#v", data)
	}
	signals := requireObjectSlice(t, data, "signals")
	untracked := quickCoordinationObjectByField(t, signals, "code", "executing_task_untracked")
	if untracked["workflow"] != "implement" || untracked["subject_id"] != "feature-untracked" || untracked["item_id"] != "T009" {
		t.Fatalf("untracked execution signal = %#v", untracked)
	}
}

func TestExecutionOverviewBlocksUnknownCurrentWorkIdentity(t *testing.T) {
	root := initCoordinationCLIRepository(t)

	code, payload := invokeCoordinationCLI(t,
		"execution", "overview",
		"--project-root", root,
		"--current-work-id", "missing-work",
		"--format", "json",
	)
	if code != ExitCodeForStatus("blocked") || payload["status"] != "blocked" {
		t.Fatalf("execution overview = code %d envelope %#v", code, payload)
	}
	data := requireObject(t, payload, "data")
	signals := requireObjectSlice(t, data, "signals")
	identity := quickCoordinationObjectByField(t, signals, "code", "current_work_identity_invalid")
	if identity["work_id"] != "missing-work" {
		t.Fatalf("identity signal = %#v", identity)
	}
}

func TestExecutionOverviewIsPublishedAsOneSharedRuntimeCapability(t *testing.T) {
	code, payload := invokeCoordinationCLI(t, "api", "show", "execution.overview", "--format", "json")
	if code != 0 || payload["status"] != "ok" {
		t.Fatalf("api show execution.overview = code %d envelope %#v", code, payload)
	}
	data := requireObject(t, payload, "data")
	capability := requireObject(t, data, "capability")
	if capability["id"] != "execution.overview" || capability["side_effect"] != "reconciles-work-board" {
		t.Fatalf("execution overview capability = %#v", capability)
	}
	usage := stringValue(capability["usage"])
	if !strings.Contains(usage, "specify-runtime execution overview") {
		t.Fatalf("execution overview usage = %q", usage)
	}
}

func TestExecutionOverviewWarnsAcrossWorkflowPlannedScopeOverlap(t *testing.T) {
	root := initCoordinationCLIRepository(t)
	writeQuickCoordinationFixture(t, root, "260826-shared-plan", "Shared Quick plan", "planned", []string{"src/shared"})
	writeExecutionOverviewImplementFixture(t, root, "feature-shared-plan", "T010", "pending", []string{"src/shared/worker.go"})

	code, payload := invokeCoordinationCLI(t, "execution", "overview", "--project-root", root, "--format", "json")
	if code != 0 || payload["status"] != "ok" {
		t.Fatalf("execution overview = code %d envelope %#v", code, payload)
	}
	data := requireObject(t, payload, "data")
	if data["coordination_state"] != "attention" || data["warning_count"] != float64(1) {
		t.Fatalf("planned overlap overview = %#v", data)
	}
	signals := requireObjectSlice(t, data, "signals")
	overlap := quickCoordinationObjectByField(t, signals, "code", "planned_scope_overlap")
	if overlap["left_activity_id"] != "implement:feature-shared-plan#T010" || overlap["right_activity_id"] != "quick:260826-shared-plan" {
		t.Fatalf("planned overlap signal = %#v", overlap)
	}
	if overlap["left_path"] != "src/shared/worker.go" || overlap["right_path"] != "src/shared" {
		t.Fatalf("planned overlap paths = %#v", overlap)
	}
}

func TestExecutionOverviewBlocksExecutingTaskWhoseScopeWasNotClaimed(t *testing.T) {
	root := initCoordinationCLIRepository(t)
	writeQuickCoordinationFixture(t, root, "260826-unclaimed", "Unclaimed Quick", "executing", []string{"src/unclaimed"})
	beginExecutionOverviewWorkWithConfidence(t, root, "work-unclaimed", "quick:260826-unclaimed", "Unclaimed Quick", "src/unclaimed", "candidate")

	code, payload := invokeCoordinationCLI(t,
		"execution", "overview",
		"--project-root", root,
		"--current-work-id", "work-unclaimed",
		"--format", "json",
	)
	if code != ExitCodeForStatus("blocked") || payload["status"] != "blocked" {
		t.Fatalf("execution overview = code %d envelope %#v", code, payload)
	}
	data := requireObject(t, payload, "data")
	signals := requireObjectSlice(t, data, "signals")
	unclaimed := quickCoordinationObjectByField(t, signals, "code", "executing_task_scope_unclaimed")
	if unclaimed["activity_id"] != "quick:260826-unclaimed" || fmt.Sprint(unclaimed["missing_paths"]) != "[src/unclaimed]" {
		t.Fatalf("unclaimed scope signal = %#v", unclaimed)
	}
}

func beginExecutionOverviewWork(t *testing.T, root, workID, taskRef, summary, path string) {
	t.Helper()
	beginExecutionOverviewWorkWithConfidence(t, root, workID, taskRef, summary, path, "confirmed")
}

func beginExecutionOverviewWorkWithConfidence(t *testing.T, root, workID, taskRef, summary, path, confidence string) {
	t.Helper()
	intents := marshalWorkBoardCLIJSON(t, []map[string]any{{
		"path": path, "operation": "modify", "reason": summary, "confidence": confidence,
	}})
	args := []string{
		"work", "begin",
		"--project-root", root,
		"--work-id", workID,
		"--task-ref", taskRef,
		"--summary", summary,
		"--agent-id", workID + "-agent",
		"--adapter-id", "codex",
		"--lease-seconds", "1800",
		"--intents-json", intents,
		"--format", "json",
	}
	code, payload := invokeCoordinationCLI(t, args...)
	if code != 0 || payload["status"] != "ok" {
		t.Fatalf("work begin %s = code %d envelope %#v", workID, code, payload)
	}
}

func writeExecutionOverviewImplementFixture(t *testing.T, root, featureID, taskID, status string, writeScope []string) {
	t.Helper()
	featureDir := filepath.Join(root, ".specify", "features", featureID)
	payload := map[string]any{
		"version":    2,
		"status":     "ready",
		"feature_id": featureID,
		"tasks": []any{map[string]any{
			"id":                   taskID,
			"objective":            "Implement " + featureID,
			"status":               status,
			"expected_write_scope": stringsToAny(writeScope),
		}},
	}
	raw, err := json.MarshalIndent(payload, "", "  ")
	if err != nil {
		t.Fatal(err)
	}
	mustWriteScriptDomainTest(t, filepath.Join(featureDir, "task-index.json"), string(raw)+"\n")
}

func executionOverviewActivity(t *testing.T, activities []map[string]any, workflow, subjectID, itemID string) map[string]any {
	t.Helper()
	for _, activity := range activities {
		if activity["workflow"] == workflow && activity["subject_id"] == subjectID && activity["item_id"] == itemID {
			return activity
		}
	}
	t.Fatalf("no activity workflow=%q subject_id=%q item_id=%q in %#v", workflow, subjectID, itemID, activities)
	return nil
}
