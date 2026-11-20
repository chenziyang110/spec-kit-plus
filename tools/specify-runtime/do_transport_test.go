package main

import (
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"testing"
	"time"
)

func TestDoJSONInputAcceptsUTF8BOMAndRejectsInvalidEncoding(t *testing.T) {
	const request = `{"goal":"打包测试"}`
	var input doStartInput
	if err := doReadInput("\uFEFF"+request, &input); err != nil || input.Goal != "打包测试" {
		t.Fatalf("UTF-8 BOM changed the request: %q, %v", input.Goal, err)
	}
	for _, bad := range []string{strings.Replace(request, "打", "\xff", 1), "{\x00}\x00"} {
		if err := doReadInput(bad, &input); err == nil || !strings.Contains(err.Error(), "UTF-8 JSON") {
			t.Fatalf("expected an actionable encoding error, got %v", err)
		}
	}
}

func TestDoRecordAcceptsWholeSecondsAndExplainsClockErrors(t *testing.T) {
	root, input := doFixture(t)
	if err := os.MkdirAll(filepath.Join(root, ".specify"), 0o755); err != nil {
		t.Fatal(err)
	}
	session, err := doStart(root, input)
	if err != nil {
		t.Fatal(err)
	}
	session = doRecordFixture(t, root, session, "clock-register", doRecordEvent{
		AttemptID: "clock-1", TargetID: "run", Kind: "step", Event: "started",
	})
	registered, err := time.Parse(time.RFC3339Nano, session.Attempts[0].RegisteredAt)
	if err != nil {
		t.Fatal(err)
	}
	process := exec.Command("git", "--version")
	process.Dir = root
	if err := process.Run(); err != nil {
		t.Fatal(err)
	}
	zero := 0
	event := doRecordEvent{
		AttemptID: "clock-1", TargetID: "run", Kind: "step", Event: "completed",
		Status: "passed", EvidenceOrigin: "agent_tool_observation", ToolCallID: "clock-git",
		Argv: []string{"git", "--version"}, Cwd: ".", ExitCode: &zero,
		StartedAt:  registered.Truncate(time.Second).Format(time.RFC3339),
		FinishedAt: doNow(),
	}
	_, digest, err := loadDoSession(root, session.ID)
	if err != nil {
		t.Fatal(err)
	}
	for _, test := range []struct {
		name, want        string
		started, finished string
	}{
		{"early", "started_at is more than 2s before registered_at", registered.Add(-3 * time.Second).Format(time.RFC3339Nano), event.FinishedAt},
		{"order", "finished_at precedes started_at", event.FinishedAt, registered.Add(-time.Second).Format(time.RFC3339Nano)},
		{"future", "finished_at is more than 2s ahead of the runtime clock", event.StartedAt, time.Now().Add(time.Minute).Format(time.RFC3339Nano)},
	} {
		invalid := event
		invalid.StartedAt, invalid.FinishedAt = test.started, test.finished
		_, err := doRecord(root, session, digest, doRecordInput{
			ExpectedRevision: session.Revision, RequestID: "clock-" + test.name, Events: []doRecordEvent{invalid},
		})
		if err == nil || !strings.Contains(err.Error(), test.want) {
			t.Fatalf("%s: expected %q, got %v", test.name, test.want, err)
		}
	}
	finished := doRecordFixture(t, root, session, "clock-finish", event)
	if finished.Attempts[0].Status != "passed" || finished.Attempts[0].StartedAt != event.StartedAt {
		t.Fatalf("whole-second observation was not preserved: %+v", finished.Attempts[0])
	}
}
