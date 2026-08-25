package main

import (
	"encoding/json"
	"fmt"
	"path/filepath"
	"testing"
)

func TestQuickPreflightCombinesUnfinishedTasksAndLiveWork(t *testing.T) {
	root := initRunCLIRepository(t)
	writeQuickCoordinationFixture(t, root, "260825-current", "Current upload work", "executing", []string{"src/upload"})
	writeQuickCoordinationFixture(t, root, "260825-other", "Node workbench", "planned", []string{"src/nodes"})

	beginQuickCoordinationWork(t, root, "work-current", "quick:260825-current", "Current upload work", "src/upload")
	beginQuickCoordinationWork(t, root, "work-board-only", "feature:260825-reporting", "Reporting feature", "src/reporting")

	code, payload := invokeRunCLI(t,
		"quick", "preflight", "260825-current",
		"--project-root", root,
		"--current-work-id", "work-current",
		"--format", "json",
	)
	if code != 0 || payload["status"] != "ok" {
		t.Fatalf("quick preflight = code %d envelope %#v", code, payload)
	}
	data := requireObject(t, payload, "data")
	if data["snapshot_kind"] != "quick-coordination-v1" || data["coordination_state"] != "attention" {
		t.Fatalf("coordination summary = %#v", data)
	}
	if data["unfinished_quick_count"] != float64(2) || data["other_unfinished_quick_count"] != float64(1) {
		t.Fatalf("quick counts = %#v", data)
	}
	if data["live_work_count"] != float64(2) || data["concurrent_work_count"] != float64(1) {
		t.Fatalf("work counts = %#v", data)
	}
	if data["untracked_quick_count"] != float64(1) || data["board_only_work_count"] != float64(1) {
		t.Fatalf("coverage counts = %#v", data)
	}
	if data["conflict_count"] != float64(0) || data["recommended_action"] != "review_concurrent_work_then_proceed" {
		t.Fatalf("coordination decision = %#v", data)
	}

	quickTasks := requireObjectSlice(t, data, "quick_tasks")
	current := quickCoordinationObjectByField(t, quickTasks, "id", "260825-current")
	other := quickCoordinationObjectByField(t, quickTasks, "id", "260825-other")
	if current["current"] != true || current["board_tracking"] != "tracked" {
		t.Fatalf("current quick projection = %#v", current)
	}
	if other["current"] != false || other["board_tracking"] != "untracked" {
		t.Fatalf("other quick projection = %#v", other)
	}
	if fmt.Sprint(other["planned_write_scope"]) != "[src/nodes]" {
		t.Fatalf("other quick scope = %#v", other["planned_write_scope"])
	}

	signals := requireObjectSlice(t, data, "signals")
	_ = quickCoordinationObjectByField(t, signals, "code", "unfinished_quick_untracked")
	_ = quickCoordinationObjectByField(t, signals, "code", "board_only_work")
}

func TestQuickPreflightBlocksOnlyOnConfirmedBoardOverlap(t *testing.T) {
	root := initRunCLIRepository(t)
	writeQuickCoordinationFixture(t, root, "260825-current", "Current upload work", "planned", []string{"src/shared/upload.go"})
	beginQuickCoordinationWork(t, root, "work-owner", "quick:260825-other", "Other shared work", "src/shared")

	code, payload := invokeRunCLI(t,
		"quick", "preflight", "260825-current",
		"--project-root", root,
		"--format", "json",
	)
	if code != ExitCodeForStatus("blocked") || payload["status"] != "blocked" {
		t.Fatalf("quick preflight = code %d envelope %#v", code, payload)
	}
	data := requireObject(t, payload, "data")
	if data["coordination_state"] != "blocked" || data["recommended_action"] != "resolve_write_overlap" {
		t.Fatalf("coordination decision = %#v", data)
	}
	if data["conflict_count"] != float64(1) {
		t.Fatalf("conflict count = %#v", data)
	}
	conflicts := requireObjectSlice(t, data, "conflicts")
	conflict := conflicts[0]
	if conflict["requested_path"] != "src/shared/upload.go" || conflict["owner_path"] != "src/shared" || conflict["owner_work_id"] != "work-owner" {
		t.Fatalf("conflict projection = %#v", conflict)
	}
	signal := quickCoordinationObjectByField(t, requireObjectSlice(t, data, "signals"), "code", "write_overlap")
	if signal["level"] != "block" {
		t.Fatalf("write overlap signal = %#v", signal)
	}
	blocker := quickCoordinationObjectByField(t, requireObjectSlice(t, payload, "blockers"), "code", "write_overlap")
	if blocker["owner_work_id"] != "work-owner" {
		t.Fatalf("write overlap blocker = %#v", blocker)
	}
}

func TestQuickPreflightDoesNotTreatAnEmptyBoardAsAnEmptyRepository(t *testing.T) {
	root := initRunCLIRepository(t)
	writeQuickCoordinationFixture(t, root, "260825-untracked", "Untracked quick", "blocked", nil)

	code, payload := invokeRunCLI(t, "quick", "preflight", "--project-root", root, "--format", "json")
	if code != 0 || payload["status"] != "ok" {
		t.Fatalf("quick preflight = code %d envelope %#v", code, payload)
	}
	data := requireObject(t, payload, "data")
	if data["live_work_count"] != float64(0) || data["unfinished_quick_count"] != float64(1) {
		t.Fatalf("combined snapshot = %#v", data)
	}
	if data["coordination_state"] != "attention" || data["untracked_quick_count"] != float64(1) {
		t.Fatalf("empty-board interpretation = %#v", data)
	}
}

func TestQuickPreflightNormalizesGlobScopeForConfirmedBoardOverlap(t *testing.T) {
	root := initRunCLIRepository(t)
	writeQuickCoordinationFixture(t, root, "260825-current", "Current upload work", "planned", []string{"src/**"})
	beginQuickCoordinationWork(t, root, "work-owner", "feature:upload", "Upload owner", "src/upload.go")

	code, payload := invokeRunCLI(t,
		"quick", "preflight", "260825-current",
		"--project-root", root,
		"--format", "json",
	)
	if code != ExitCodeForStatus("blocked") || payload["status"] != "blocked" {
		t.Fatalf("glob-scope preflight = code %d envelope %#v", code, payload)
	}
	data := requireObject(t, payload, "data")
	conflict := requireObjectSlice(t, data, "conflicts")[0]
	if conflict["requested_path"] != "src" || conflict["owner_path"] != "src/upload.go" {
		t.Fatalf("normalized glob conflict = %#v", conflict)
	}
}

func TestQuickPreflightNormalizesGlobScopeForUnfinishedQuickAdvisory(t *testing.T) {
	root := initRunCLIRepository(t)
	writeQuickCoordinationFixture(t, root, "260825-current", "Current upload work", "planned", []string{"src/*"})
	writeQuickCoordinationFixture(t, root, "260825-other", "Other node work", "executing", []string{"src/nodes"})

	code, payload := invokeRunCLI(t,
		"quick", "preflight", "260825-current",
		"--project-root", root,
		"--format", "json",
	)
	if code != 0 || payload["status"] != "ok" {
		t.Fatalf("glob-scope advisory = code %d envelope %#v", code, payload)
	}
	data := requireObject(t, payload, "data")
	signal := quickCoordinationObjectByField(t, requireObjectSlice(t, data, "signals"), "code", "unfinished_quick_scope_overlap")
	if signal["requested_path"] != "src" || signal["other_quick_path"] != "src/nodes" {
		t.Fatalf("normalized Quick overlap signal = %#v", signal)
	}
}

func writeQuickCoordinationFixture(t *testing.T, root, id, title, status string, writeScope []string) {
	t.Helper()
	workspace := id + "-fixture"
	workspacePath := filepath.Join(root, ".planning", "quick", workspace)
	mustWriteScriptDomainTest(t, filepath.Join(workspacePath, "STATUS.md"), fmt.Sprintf(`---
id: "%s"
title: "%s"
status: "%s"
---
## Current Focus
%s

## Next Action
- Continue %s
`, id, title, status, title, title))
	if writeScope == nil {
		return
	}
	payload := quickConfirmationDoc{
		Schema:            quickConfirmationSchema,
		Workspace:         workspace,
		ConfirmationMode:  "explicit",
		ConfirmationState: "confirmed",
		Decision: quickConfirmationDecision{
			Goal:              title,
			UserVisibleResult: title,
			Scope:             quickConfirmationScope{Include: []string{title}, Exclude: []string{}},
			Items: []quickConfirmationItem{{
				ID: "Q1", Deliverable: title, DependsOn: []string{}, Acceptance: "done", WriteScope: writeScope,
			}},
			ReconfirmationTrigger: "scope changes",
		},
		Delivery: quickConfirmationDelivery{Waves: []quickConfirmationWave{{ID: "W1", ItemIDs: []string{"Q1"}}}},
	}
	raw, err := json.MarshalIndent(payload, "", "  ")
	if err != nil {
		t.Fatal(err)
	}
	mustWriteScriptDomainTest(t, filepath.Join(workspacePath, quickConfirmationFileName), string(raw)+"\n")
}

func beginQuickCoordinationWork(t *testing.T, root, workID, taskRef, summary, path string) {
	t.Helper()
	intents := marshalWorkBoardCLIJSON(t, []map[string]any{{
		"path": path, "operation": "modify", "reason": summary, "confidence": "confirmed",
	}})
	code, payload := invokeRunCLI(t,
		"work", "begin",
		"--project-root", root,
		"--work-id", workID,
		"--task-ref", taskRef,
		"--summary", summary,
		"--agent-id", workID+"-agent",
		"--adapter-id", "codex",
		"--lease-seconds", "1800",
		"--intents-json", intents,
		"--format", "json",
	)
	if code != 0 || payload["status"] != "ok" {
		t.Fatalf("work begin %s = code %d envelope %#v", workID, code, payload)
	}
}

func requireObjectSlice(t *testing.T, object map[string]any, field string) []map[string]any {
	t.Helper()
	raw, ok := object[field].([]any)
	if !ok {
		t.Fatalf("%s = %#v, want array", field, object[field])
	}
	items := make([]map[string]any, 0, len(raw))
	for _, item := range raw {
		items = append(items, requireObjectValue(t, item))
	}
	return items
}

func quickCoordinationObjectByField(t *testing.T, objects []map[string]any, field, value string) map[string]any {
	t.Helper()
	for _, object := range objects {
		if object[field] == value {
			return object
		}
	}
	t.Fatalf("no object with %s=%q in %#v", field, value, objects)
	return nil
}
