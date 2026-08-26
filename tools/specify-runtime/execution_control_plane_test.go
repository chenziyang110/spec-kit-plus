package main

import (
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestExecutionAnnounceMakesFastVisibleBeforeClaim(t *testing.T) {
	root := initRunCLIRepository(t)
	announced := announceExecutionCLI(t, root, "activity-fast-visible", "fast", "copy-fix", "", []string{"src/copy"}, []map[string]any{{
		"type": "capability", "key": "copy-rendering", "mode": "exclusive", "confidence": "candidate",
	}})
	if announced["phase"] != "announced" || announced["work_id"] != "activity-fast-visible" {
		t.Fatalf("announced activity = %#v", announced)
	}

	code, payload := invokeRunCLI(t,
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
	root := initRunCLIRepository(t)
	announced := announceExecutionCLI(t, root, "activity-audited", "fast", "audited", "", []string{"src/allowed"}, []map[string]any{{
		"type": "feature", "key": "audited", "mode": "exclusive", "confidence": "candidate",
	}})
	overview := executionOverviewCLI(t, root, "activity-audited")
	guarded := guardExecutionCLI(t, root, announced, overview, []string{"src/allowed"}, []map[string]any{{
		"type": "feature", "key": "audited", "mode": "exclusive", "confidence": "confirmed",
	}})
	if guarded["schema"] != "execution-guard-v1" || guarded["phase"] != "executing" {
		t.Fatalf("guard receipt = %#v", guarded)
	}

	mustWriteScriptDomainTest(t, filepath.Join(root, "src", "outside.go"), "package outside\n")
	code, blocked := invokeRunCLI(t,
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

	if err := os.Remove(filepath.Join(root, "src", "outside.go")); err != nil {
		t.Fatal(err)
	}
	mustWriteScriptDomainTest(t, filepath.Join(root, "src", "allowed", "main.go"), "package allowed\n")
	code, completedPayload := invokeRunCLI(t,
		"execution", "complete", "activity-audited",
		"--project-root", root,
		"--expected-revision", executionJSONNumberString(guarded["work_revision"]),
		"--fence", executionJSONNumberString(guarded["fence"]),
		"--validation-json", `[{"command":"go test ./...","result":"passed"}]`,
		"--reason", "verified execution",
		"--format", "json",
	)
	if code != 0 || completedPayload["status"] != "ok" {
		t.Fatalf("execution complete = code %d envelope %#v", code, completedPayload)
	}
	completed := requireObject(t, requireObject(t, completedPayload, "data"), "execution_completion")
	if completed["schema"] != "execution-completion-v1" || completed["phase"] != "completed" || completed["work_status"] != "completed" {
		t.Fatalf("completion receipt = %#v", completed)
	}
	if strings.Join(anyStringSlice(completed["actual_changed_paths"]), ",") != "src/allowed/main.go" || len(stringValue(completed["completion_sha256"])) != 64 {
		t.Fatalf("audited completion = %#v", completed)
	}

	code, shownPayload := invokeRunCLI(t, "execution", "show", "activity-audited", "--project-root", root, "--format", "json")
	if code != 0 || shownPayload["status"] != "ok" {
		t.Fatalf("execution show = code %d envelope %#v", code, shownPayload)
	}
	shown := requireObject(t, requireObject(t, shownPayload, "data"), "execution_activity")
	if shown["phase"] != "completed" || shown["work_status"] != "completed" {
		t.Fatalf("shown completion = %#v", shown)
	}
}

func TestExecutionGuardRejectsOverviewChangedAfterObservation(t *testing.T) {
	root := initRunCLIRepository(t)
	announced := announceExecutionCLI(t, root, "activity-stale-cli", "debug", "stale-cli", "", []string{"src/stale"}, nil)
	overview := executionOverviewCLI(t, root, "activity-stale-cli")
	_ = announceExecutionCLI(t, root, "activity-racer-cli", "fast", "racer-cli", "", []string{"src/racer"}, nil)

	code, payload := invokeRunCLI(t,
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
	root := initRunCLIRepository(t)
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
	code, payload := invokeRunCLI(t,
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
	root := initRunCLIRepository(t)
	initial := executionOverviewCLI(t, root, "")
	_ = announceExecutionCLI(t, root, "activity-change-feed", "fast", "change-feed", "", []string{"src/change"}, nil)

	code, payload := invokeRunCLI(t,
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
	code, payload := invokeRunCLI(t, args...)
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
	code, payload := invokeRunCLI(t, args...)
	if code != 0 || payload["status"] != "ok" {
		t.Fatalf("execution overview = code %d envelope %#v", code, payload)
	}
	return requireObject(t, payload, "data")
}

func guardExecutionCLI(t *testing.T, root string, announced, overview map[string]any, scope []string, resources []map[string]any) map[string]any {
	t.Helper()
	code, payload := invokeRunCLI(t,
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
