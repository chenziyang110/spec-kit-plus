package main

import (
	"bytes"
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestTeamsStatusAndDoctorRequireCodexProjectAndReadState(t *testing.T) {
	project := newTeamsProject(t)
	withCwd(t, project)
	writeTeamsJSON(t, teamsRuntimeSessionPath(project, "default"), map[string]any{
		"session": map[string]any{"session_id": "default", "status": "running"},
	})
	writeTeamsJSON(t, teamsDispatchRecordPath(project, "req-failed"), map[string]any{
		"request_id": "req-failed", "target_worker": "worker-1", "status": "failed", "reason": "boom",
	})

	var stdout bytes.Buffer
	if exit := runTeams([]string{"status"}, &stdout); exit != 0 {
		t.Fatalf("status exit=%d output=%s", exit, stdout.String())
	}
	status := decodeEnvelope(t, stdout.Bytes()).Data
	if status["available"] != true || status["runtime_state"] == nil {
		t.Fatalf("unexpected status: %#v", status)
	}

	stdout.Reset()
	if exit := runTeams([]string{"doctor"}, &stdout); exit != 0 {
		t.Fatalf("doctor exit=%d output=%s", exit, stdout.String())
	}
	doctor := decodeEnvelope(t, stdout.Bytes()).Data
	if len(doctor["failed_dispatches"].([]any)) != 1 {
		t.Fatalf("expected failed dispatch: %#v", doctor)
	}
}

func TestTeamsExternalDispatchCommandsReturnBlocked(t *testing.T) {
	project := newTeamsProject(t)
	withCwd(t, project)
	feature := filepath.Join(project, "specs", "001-demo")
	if err := os.MkdirAll(feature, 0o755); err != nil {
		t.Fatal(err)
	}
	var stdout bytes.Buffer
	if exit := runTeams([]string{"live-probe"}, &stdout); exit != 10 {
		t.Fatalf("live-probe should block: %d %s", exit, stdout.String())
	}
	stdout.Reset()
	if exit := runTeams([]string{"auto-dispatch", "--feature-dir", "specs/001-demo"}, &stdout); exit != 10 {
		t.Fatalf("auto-dispatch should block: %d %s", exit, stdout.String())
	}
}

func TestTeamsResultTemplateAndSubmitResultUseRuntimeStatePaths(t *testing.T) {
	project := newTeamsProject(t)
	withCwd(t, project)
	seedTeamsDispatch(t, project, "req-template", "T701")

	var stdout bytes.Buffer
	if exit := runTeams([]string{"result-template", "--request-id", "req-template"}, &stdout); exit != 0 {
		t.Fatalf("result-template exit=%d output=%s", exit, stdout.String())
	}
	template := decodeEnvelope(t, stdout.Bytes()).Data
	if template["task_id"] != "T701" || template["status"] != "pending" {
		t.Fatalf("unexpected template: %#v", template)
	}

	resultPath := filepath.Join(project, "result.json")
	writeTeamsJSON(t, resultPath, map[string]any{
		"task_id": "T701", "status": "success", "changed_files": []any{"src/t701.py"},
		"validation_results": []any{map[string]any{"command": "pytest -q", "status": "passed", "output": "PASS"}},
		"summary":            "Implemented T701",
	})
	stdout.Reset()
	if exit := runTeams([]string{"submit-result", "--request-id", "req-template", "--result-file", "result.json"}, &stdout); exit != 0 {
		t.Fatalf("submit-result exit=%d output=%s", exit, stdout.String())
	}
	if _, err := os.Stat(teamsResultRecordPath(project, "req-template")); err != nil {
		t.Fatalf("result record missing: %v", err)
	}

	stdout.Reset()
	if exit := runTeams([]string{"submit-result", "--print-schema"}, &stdout); exit != 0 {
		t.Fatalf("print-schema exit=%d output=%s", exit, stdout.String())
	}
	if !strings.Contains(stdout.String(), "required_fields") {
		t.Fatalf("schema missing required_fields: %s", stdout.String())
	}
}

func TestTeamsCompleteBatchBlocksUntilAllResultsAreSuccessful(t *testing.T) {
	project := newTeamsProject(t)
	withCwd(t, project)
	writeTeamsJSON(t, teamsBatchRecordPath(project, "batch-1"), map[string]any{
		"batch_id": "batch-1", "batch_name": "Batch 1", "request_ids": []any{"req-a", "req-b"}, "status": "dispatched",
	})
	writeTeamsJSON(t, teamsResultRecordPath(project, "req-a"), map[string]any{"request_id": "req-a", "status": "success"})

	var stdout bytes.Buffer
	if exit := runTeams([]string{"complete-batch", "--batch-id", "batch-1"}, &stdout); exit != 10 {
		t.Fatalf("complete-batch should block: %d %s", exit, stdout.String())
	}
	writeTeamsJSON(t, teamsResultRecordPath(project, "req-b"), map[string]any{"request_id": "req-b", "status": "success"})
	stdout.Reset()
	if exit := runTeams([]string{"complete-batch", "--batch-id", "batch-1"}, &stdout); exit != 0 {
		t.Fatalf("complete-batch exit=%d output=%s", exit, stdout.String())
	}
	batch := readTeamsJSON(t, teamsBatchRecordPath(project, "batch-1"))
	if batch["status"] != "completed" {
		t.Fatalf("batch not completed: %#v", batch)
	}
}

func TestTeamsSyncBackPlansCopiesAndProtectsDirtyWorkspace(t *testing.T) {
	project := newTeamsProject(t)
	withCwd(t, project)
	source := filepath.Join(project, ".specify", "teams", "worktrees", "default", "worker-a", "src", "app.py")
	writeTeamsText(t, source, "print('from worker')\n")

	var stdout bytes.Buffer
	if exit := runTeams([]string{"sync-back", "--dry-run"}, &stdout); exit != 0 {
		t.Fatalf("sync-back dry-run exit=%d output=%s", exit, stdout.String())
	}
	plan := decodeEnvelope(t, stdout.Bytes()).Data
	if plan["candidate_count"] != float64(1) {
		t.Fatalf("unexpected plan: %#v", plan)
	}

	stdout.Reset()
	if exit := runTeams([]string{"sync-back"}, &stdout); exit != 10 {
		t.Fatalf("sync-back should protect dirty workspace: exit=%d output=%s", exit, stdout.String())
	}
	stdout.Reset()
	if exit := runTeams([]string{"sync-back", "--allow-dirty"}, &stdout); exit != 0 {
		t.Fatalf("sync-back allow-dirty exit=%d output=%s", exit, stdout.String())
	}
	target := filepath.Join(project, "src", "app.py")
	raw, err := os.ReadFile(target)
	if err != nil || string(raw) != "print('from worker')\n" {
		t.Fatalf("sync-back target mismatch: %v %q", err, raw)
	}
}

func newTeamsProject(t *testing.T) string {
	t.Helper()
	project := t.TempDir()
	if err := os.MkdirAll(filepath.Join(project, ".specify"), 0o755); err != nil {
		t.Fatal(err)
	}
	writeTeamsJSON(t, filepath.Join(project, ".specify", "integration.json"), map[string]any{"integration": "codex"})
	return project
}

func seedTeamsDispatch(t *testing.T, project, requestID, taskID string) {
	t.Helper()
	packetPath := filepath.Join(project, ".specify", "teams", "state", "packets", requestID+".json")
	writeTeamsJSON(t, packetPath, map[string]any{
		"feature_id": "001-feature", "task_id": taskID, "story_id": "US1",
		"objective":        "Implement " + taskID,
		"scope":            map[string]any{"write_scope": []any{"src/t701.py"}, "read_scope": []any{"src/contracts.py"}},
		"validation_gates": []any{"pytest -q"},
		"packet_version":   1,
	})
	writeTeamsJSON(t, teamsDispatchRecordPath(project, requestID), map[string]any{
		"request_id": requestID, "target_worker": "worker-1", "status": "pending", "packet_path": packetPath,
	})
}

func writeTeamsJSON(t *testing.T, path string, payload any) {
	t.Helper()
	raw, err := json.MarshalIndent(payload, "", "  ")
	if err != nil {
		t.Fatal(err)
	}
	writeTeamsText(t, path, string(raw)+"\n")
}

func readTeamsJSON(t *testing.T, path string) map[string]any {
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

func writeTeamsText(t *testing.T, path, content string) {
	t.Helper()
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(path, []byte(content), 0o644); err != nil {
		t.Fatal(err)
	}
}
