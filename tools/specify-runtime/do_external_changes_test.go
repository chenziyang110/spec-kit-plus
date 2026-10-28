package main

import (
	"context"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"

	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/runcontrol"
)

func TestDoExternalChangesAudit(t *testing.T) {
	t.Run("unrelated_exact_snapshot_and_evidence_remain_bound", func(t *testing.T) {
		root, session := doStartFixture(t)
		session = doRunFixture(t, root, session)
		write := func(p, text string) {
			t.Helper()
			if err := os.WriteFile(filepath.Join(root, p), []byte(text), 0o600); err != nil {
				t.Fatal(err)
			}
		}
		write("other-arm64.txt", "unrelated concurrent output")
		if v := doValidate(root, session, true); v.Status != "blocked" || !strings.Contains(strings.Join(v.Blockers, ";"), "unclaimed changed path: other-arm64.txt") {
			t.Fatalf("uninspected external delta was accepted: %+v", v)
		}
		input := doResumeInput{ExpectedRevision: session.Revision, ExternalChanges: &DoExternalChangesInput{Paths: []string{"other-arm64.txt"}}, Recovery: DoRecovery{Reason: "Concurrent ARM64 output is outside this read-only operation", EvidenceText: "Inspected native operations, their input and output paths, and the external diff. This operation did not read or write other-arm64.txt.", ProcessesStopped: true, SideEffectsInspected: true}}
		_, digest, err := loadDoSession(root, session.ID)
		if err != nil {
			t.Fatal(err)
		}
		session, err = doResume(root, session, digest, input)
		if err != nil {
			t.Fatal(err)
		}
		if len(session.ExternalChanges) != 1 || session.ExternalChanges[0].Recovery.EvidenceText != "" {
			t.Fatalf("inspection was not runtime-snapshotted: %+v", session.ExternalChanges)
		}
		if v := doValidate(root, session, true); v.Status != "passed" {
			t.Fatalf("unrelated inspected delta blocked fresh results: %+v", v)
		}
		if replay, err := doResume(root, session, "", input); err != nil || replay.Revision != session.Revision {
			t.Fatalf("unchanged replay changed inspection: %v", err)
		}
		write("other-arm64.txt", "external bytes changed after inspection")
		if v := doValidate(root, session, true); v.Status != "blocked" || !strings.Contains(strings.Join(v.Blockers, ";"), "differs from its inspection") {
			t.Fatalf("changed external state retained its exemption: %+v", v)
		}
		if _, err := doResume(root, session, "", input); err == nil {
			t.Fatal("replay accepted changed external bytes")
		}
		write("other-arm64.txt", "unrelated concurrent output")
		audit := session.ExternalChanges[0]
		write(audit.Recovery.EvidenceRef, "changed inspection text")
		if v := doValidate(root, session, true); v.Status != "blocked" || !strings.Contains(strings.Join(v.Blockers, ";"), "inspection evidence") {
			t.Fatalf("mutated inspection evidence was accepted: %+v", v)
		}
		input.ExternalChanges.Paths = []string{"source.txt"}
		write("source.txt", "new shared input")
		if _, err := doResume(root, session, "", input); err == nil || !strings.Contains(err.Error(), "cannot exclude operation source") {
			t.Fatalf("related input was reclassified as external: %v", err)
		}
		input.ExternalChanges.Paths = []string{"out/report.json"}
		if _, err := doResume(root, session, "", input); err == nil || !strings.Contains(err.Error(), "cannot exclude operation source") {
			t.Fatalf("own output was reclassified as external: %v", err)
		}
	})

	t.Run("other_work_does_not_excuse_changed_read_input", func(t *testing.T) {
		root, session := doStartFixture(t)
		session = doRunFixture(t, root, session)
		store, err := runcontrol.OpenForRepository(context.Background(), root)
		if err != nil {
			t.Fatal(err)
		}
		_, _, err = store.BeginWork(context.Background(), runcontrol.BeginWorkParams{WorkID: "concurrent-input-owner", TaskRef: "other:task", Summary: "Independent concurrent changes", AgentID: "other-agent", AdapterID: "test", WorkspaceRoot: root, NextAction: "edit own input", LeaseUntil: time.Now().UTC().Add(time.Hour), WriteIntents: []runcontrol.WriteIntentSpec{{Path: "source.txt", Operation: runcontrol.WriteModify, Confidence: runcontrol.IntentConfirmed, Reason: "separate task"}, {Path: "arm64.txt", Operation: runcontrol.WriteModify, Confidence: runcontrol.IntentConfirmed, Reason: "separate output"}}})
		store.Close()
		if err != nil {
			t.Fatal(err)
		}
		if err := os.WriteFile(filepath.Join(root, "arm64.txt"), []byte("independent"), 0o600); err != nil {
			t.Fatal(err)
		}
		if v := doValidate(root, session, true); v.Status != "passed" {
			t.Fatalf("existing unrelated confirmed Work ownership regressed: %+v", v)
		}
		if err := os.WriteFile(filepath.Join(root, "source.txt"), []byte("changed shared input"), 0o600); err != nil {
			t.Fatal(err)
		}
		if v := doValidate(root, session, true); v.Status != "blocked" || !strings.Contains(strings.Join(v.Blockers, ";"), "stale") {
			t.Fatalf("other Work bypassed stale shared input: %+v", v)
		}
	})
}
