package main

import (
	"bytes"
	"context"
	"crypto/sha256"
	"encoding/json"
	"fmt"
	"os"
	"os/exec"
	"path"
	"path/filepath"
	"reflect"
	"strings"
	"testing"
	"time"

	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/runcontrol"
)

func doReadonlyFailureFixture(t *testing.T) (string, DoSession, doResumeInput) {
	t.Helper()
	root := initCoordinationCLIRepository(t)
	if err := os.WriteFile(filepath.Join(root, "source.txt"), []byte("read-only capability inspection\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	gitRun(t, root, "add", "source.txt")
	gitRun(t, root, "-c", "user.name=Do Test", "-c", "user.email=do@example.test", "commit", "-m", "read-only fixture")
	definition := PlaybookDefinition{
		Operation: "check", Target: "git-capability", Owner: "runtime", Variant: "default",
		Title: "Inspect local Git capability", Goal: "Inspect the installed Git tool without product writes",
		SourceFiles: []string{"source.txt"},
		Steps:       []PlaybookStep{{ID: "run", Purpose: "inspect the actual Git executable", Cwd: ".", Argv: []string{"git", "spec-kit-no-such-command"}, Required: true, ExpectedResult: "the requested Git operation exits zero", SideEffect: "read"}},
		Checks:      []PlaybookCheck{{ID: "exit", Purpose: "independently verify that Git remains available", Cwd: ".", Argv: []string{"git", "--version"}, DependsOn: []string{"run"}, Required: true, ExpectedResult: "exit zero", Kind: "exit_code"}},
	}
	session, err := doStart(root, doStartInput{SessionID: "readonly-recovery", Definition: definition, WriteScope: []string{}, OutputScope: []string{}, AgentID: "do-test", AdapterID: "test"})
	if err != nil {
		t.Fatal(err)
	}
	session, inspection := doReadonlyRunNative(t, root, session, "step", "run", "failed-git", false)
	return root, session, doResumeInput{ExpectedRevision: session.Revision, AttemptID: "failed-git", Recovery: DoRecovery{Reason: "inspected the completed native process and actual Git workspace status", EvidenceText: inspection, ProcessesStopped: true, SideEffectsInspected: true}}
}

func doReadonlyRunNative(t *testing.T, root string, session DoSession, kind, target, attempt string, wantPass bool) (DoSession, string) {
	t.Helper()
	action, err := doFindAction(session, kind, target)
	if err != nil {
		t.Fatal(err)
	}
	session = doRecordFixture(t, root, session, "start-"+attempt, doRecordEvent{AttemptID: attempt, TargetID: target, Kind: kind, Event: "started"})
	started := doNow()
	command := exec.Command(action.argv[0], action.argv[1:]...)
	command.Dir = filepath.Join(root, action.cwd)
	output, commandErr := command.CombinedOutput()
	finished := doNow()
	if command.ProcessState == nil || !command.ProcessState.Exited() {
		t.Fatalf("native command did not finish: %v %s", commandErr, output)
	}
	exit := command.ProcessState.ExitCode()
	if (exit == 0) != wantPass {
		t.Fatalf("unexpected native exit %d (want pass=%t): %v %s", exit, wantPass, commandErr, output)
	}
	status := "failed"
	if exit == 0 {
		status = "passed"
	}
	session = doRecordFixture(t, root, session, "complete-"+attempt, doRecordEvent{AttemptID: attempt, TargetID: target, Kind: kind, Event: "completed", Status: status, EvidenceOrigin: "agent_tool_observation", ToolCallID: "native-" + attempt, Argv: action.argv, Cwd: action.cwd, StartedAt: started, FinishedAt: finished, ExitCode: &exit, Summary: strings.TrimSpace(string(output))})
	inspection := exec.Command("git", "status", "--porcelain=v1", "--untracked-files=all")
	inspection.Dir = root
	workspaceStatus, err := inspection.CombinedOutput()
	if err != nil {
		t.Fatalf("actual side-effect inspection failed: %v %s", err, workspaceStatus)
	}
	return session, fmt.Sprintf("native_process_exited=%t\nnative_exit_code=%d\nnative_argv=%q\nnative_output=%s\nactual_git_status=%s\n", command.ProcessState.Exited(), exit, action.argv, output, workspaceStatus)
}

func doReadonlyResumePublic(t *testing.T, root string, session DoSession, input doResumeInput) DoSession {
	t.Helper()
	raw, err := json.Marshal(input)
	if err != nil {
		t.Fatal(err)
	}
	var output bytes.Buffer
	if code := runDo([]string{"resume", session.ID, "--project-root", root, "--input-json", string(raw), "--format", "json"}, &output); code != 0 {
		t.Fatalf("public recovery failed: %d %s", code, output.String())
	}
	current, _, err := loadDoSession(root, session.ID)
	if err != nil {
		t.Fatal(err)
	}
	return current
}

func doReadonlySnapshotRef(t *testing.T, session DoSession, input doResumeInput) string {
	t.Helper()
	raw, err := json.Marshal(input)
	if err != nil {
		t.Fatal(err)
	}
	return path.Join(".specify/do/sessions", session.ID, "evidence", fmt.Sprintf("recovery-%x.txt", sha256.Sum256(raw)))
}

func doReadonlyAssertSnapshot(t *testing.T, root string, session DoSession, input doResumeInput) {
	t.Helper()
	ref := doReadonlySnapshotRef(t, session, input)
	raw, err := os.ReadFile(filepath.Join(root, filepath.FromSlash(ref)))
	if err != nil || string(raw) != input.Recovery.EvidenceText {
		t.Fatalf("immutable recovery snapshot does not contain the actual inspection: %v", err)
	}
	recovery := session.Attempts[0].Recovery
	if recovery == nil || recovery.EvidenceRef != ref || recovery.EvidenceSHA256 != fmt.Sprintf("%x", sha256.Sum256(raw)) || recovery.EvidenceText != "" {
		t.Fatalf("recovery did not persist only its bound snapshot reference and digest: %+v", recovery)
	}
	if len(session.WriteScope) != 0 || len(session.OutputScope) != 0 {
		t.Fatalf("inline recovery expanded product/output scope: %v %v", session.WriteScope, session.OutputScope)
	}
	metadata := []string{doSessionRef(session.ID)}
	for _, epoch := range session.DefinitionHistory {
		if session.DefinitionEpoch > 1 {
			metadata = append(metadata, doDefinitionEpochRef(session.ID, epoch.Epoch))
		}
	}
	for _, name := range metadata {
		content, err := os.ReadFile(filepath.Join(root, filepath.FromSlash(name)))
		if err != nil {
			t.Fatal(err)
		}
		if bytes.Contains(content, []byte(`"evidence_text"`)) || bytes.Contains(content, []byte("native_process_exited=")) {
			t.Fatalf("inspection body was duplicated in %s", name)
		}
	}
}

func doReadonlyAddReplan(t *testing.T, session DoSession, input doResumeInput) doResumeInput {
	t.Helper()
	definition := doReplanCopyDefinition(t, session.Definition)
	definition.Steps[0].Argv = []string{"git", "--version"}
	input.ExpectedRevision = session.Revision
	input.Replan = &doReplanInput{RequestID: "repair-readonly-command", Definition: definition}
	return input
}

func TestDoReadonlyRecoveryCanResumeReplanVerifyAndSaveWithoutOutputScope(t *testing.T) {
	root, session, resume := doReadonlyFailureFixture(t)
	// Compare durable observations on both sides of the recovery, including
	// JSON's existing omission of empty optional result/change slices.
	session, _, err := loadDoSession(root, session.ID)
	if err != nil {
		t.Fatal(err)
	}
	original := session.Attempts[0]
	originalDefinition := session.DefinitionDigest
	methodID := playbookID(session.Definition)
	session = doReadonlyResumePublic(t, root, session, resume)
	doReadonlyAssertSnapshot(t, root, session, resume)
	_, beforeReplay, _ := loadDoSession(root, session.ID)
	session = doReadonlyResumePublic(t, root, session, resume)
	if _, afterReplay, err := loadDoSession(root, session.ID); err != nil || beforeReplay != afterReplay {
		t.Fatalf("ordinary recovery replay mutated its checkpoint: %v", err)
	}
	replan := doReadonlyAddReplan(t, session, resume)
	session = doReadonlyResumePublic(t, root, session, replan)
	doReadonlyAssertSnapshot(t, root, session, replan)
	if session.DefinitionEpoch != 2 || len(session.DefinitionHistory) != 2 || len(session.Attempts) != 1 || session.DefinitionHistory[0].DefinitionDigest != originalDefinition {
		t.Fatal("recovery lost the original definition or failure history")
	}
	preserved := session.Attempts[0]
	preserved.Recovery = nil
	if !reflect.DeepEqual(preserved, original) {
		beforeFields, afterFields := reflect.ValueOf(original), reflect.ValueOf(preserved)
		for i := 0; i < beforeFields.NumField(); i++ {
			before, after := beforeFields.Field(i).Interface(), afterFields.Field(i).Interface()
			if !reflect.DeepEqual(before, after) {
				t.Logf("observation field %s: original=%#v, persisted=%#v", beforeFields.Type().Field(i).Name, before, after)
			}
		}
		t.Fatal("replanning relabelled the actual failed observation")
	}
	_, beforeReplay, _ = loadDoSession(root, session.ID)
	session = doReadonlyResumePublic(t, root, session, replan)
	if _, afterReplay, err := loadDoSession(root, session.ID); err != nil || beforeReplay != afterReplay {
		t.Fatalf("replan replay mutated its checkpoint: %v", err)
	}
	snapshots, err := filepath.Glob(filepath.Join(root, ".specify/do/sessions", session.ID, "evidence/recovery-*.txt"))
	if err != nil || len(snapshots) != 2 {
		t.Fatalf("exact replays duplicated recovery snapshots: %v %v", err, snapshots)
	}
	store, err := runcontrol.OpenForRepository(context.Background(), root)
	if err != nil {
		t.Fatal(err)
	}
	_, intents, err := store.GetWork(context.Background(), session.WorkID)
	_ = store.Close()
	if err != nil || len(intents) != 1 || intents[0].Path != path.Dir(doSessionRef(session.ID)) {
		t.Fatalf("recovery needed an additional Work write claim: %v %+v", err, intents)
	}
	if validation := doValidate(root, session, true); validation.Status == "passed" {
		t.Fatal("replan passed before current-epoch native execution")
	}
	session, _ = doReadonlyRunNative(t, root, session, "step", "run", "repaired-git", true)
	session, _ = doReadonlyRunNative(t, root, session, "check", "exit", "fresh-exit-check", true)
	validation := doValidate(root, session, true)
	if validation.Status != "passed" || validation.RequiredSteps != 1 || validation.RequiredChecks != 1 || validation.CognitionCloseout != "not_applicable" {
		t.Fatalf("actual read-only operation did not validate: %+v", validation)
	}
	for _, attempt := range session.Attempts[1:] {
		if attempt.DefinitionEpoch != 2 || attempt.Status != "passed" || attempt.ExitCode == nil || *attempt.ExitCode != 0 || len(attempt.Results) != 0 {
			t.Fatalf("current-epoch exit observation was not preserved: %+v", attempt)
		}
	}
	_, digest, err := loadDoSession(root, session.ID)
	if err != nil {
		t.Fatal(err)
	}
	session, err = doFinish(root, session, digest, doFinishInput{ExpectedRevision: session.Revision, KnowledgeStatus: "pending"})
	if err != nil {
		t.Fatal(err)
	}
	publication := playbookPublishFixture(t, root, session, "")
	if publication["id"] != methodID {
		t.Fatal("read-only recovery changed the reusable method identity")
	}
	playbookFinishFixture(t, root, session.ID, publication)
	session, _, err = loadDoSession(root, session.ID)
	if err != nil || session.ExecutionOutcome != "passed" || session.KnowledgeStatus != "saved" || len(session.Attempts) != 3 || len(session.WriteScope) != 0 || len(session.OutputScope) != 0 {
		t.Fatalf("read-only operation did not close with its original scopes/history: %v %+v", err, session)
	}
}

func TestDoReadonlyRecoveryReplayRejectsMissingAndChangedSnapshots(t *testing.T) {
	for _, replan := range []bool{false, true} {
		for _, missing := range []bool{false, true} {
			t.Run(fmt.Sprintf("replan=%t/missing=%t", replan, missing), func(t *testing.T) {
				root, session, input := doReadonlyFailureFixture(t)
				if replan {
					input = doReadonlyAddReplan(t, session, input)
				}
				session = doReadonlyResumePublic(t, root, session, input)
				_, digest, _ := loadDoSession(root, session.ID)
				ref := filepath.Join(root, filepath.FromSlash(doReadonlySnapshotRef(t, session, input)))
				var err error
				if missing {
					err = os.Remove(ref)
				} else {
					err = os.WriteFile(ref, []byte("changed recovery evidence\n"), 0o600)
				}
				if err != nil {
					t.Fatal(err)
				}
				if _, err := doResume(root, session, digest, input); err == nil || !strings.Contains(err.Error(), "missing or changed") {
					t.Fatalf("replay accepted untrusted recovery evidence: %v", err)
				}
				if _, after, err := loadDoSession(root, session.ID); err != nil || after != digest {
					t.Fatalf("rejected replay changed its checkpoint: %v", err)
				}
				if missing {
					if _, err := os.Stat(ref); !os.IsNotExist(err) {
						t.Fatal("replay silently recreated missing evidence")
					}
				}
			})
		}
	}
}

func TestDoReadonlyRecoveryRejectedCASAndFenceLeaveNoSnapshot(t *testing.T) {
	for _, replan := range []bool{false, true} {
		for _, conflict := range []string{"cas", "stale-fence"} {
			t.Run(fmt.Sprintf("replan=%t/%s", replan, conflict), func(t *testing.T) {
				root, before, input := doReadonlyFailureFixture(t)
				_, oldDigest, _ := loadDoSession(root, before.ID)
				if replan {
					input = doReadonlyAddReplan(t, before, input)
				}
				if conflict == "cas" {
					winner := input
					winner.Replan = nil
					winner.Recovery.Reason = "first writer inspected and saved the completed process"
					doReadonlyResumePublic(t, root, before, winner)
				} else {
					store, err := runcontrol.OpenForRepository(context.Background(), root)
					if err != nil {
						t.Fatal(err)
					}
					defer store.Close()
					work, _, err := store.GetWork(context.Background(), before.WorkID)
					if err != nil {
						t.Fatal(err)
					}
					work, err = store.InterruptWork(context.Background(), runcontrol.InterruptWorkParams{WorkID: work.WorkID, Fence: work.Fence, ExpectedRevision: work.Revision, Reason: "recover ownership after the native command has stopped", ObservedPaths: []string{doSessionRef(before.ID)}})
					if err != nil {
						t.Fatal(err)
					}
					if _, err := store.ResumeWork(context.Background(), runcontrol.ResumeWorkParams{WorkID: work.WorkID, ExpectedRevision: work.Revision, AgentID: "recovered-owner", AdapterID: "test", WorkspaceRoot: root, LeaseUntil: time.Now().UTC().Add(time.Hour)}); err != nil {
						t.Fatal(err)
					}
					input.WorkFence = before.WorkFence
				}
				_, currentDigest, _ := loadDoSession(root, before.ID)
				if _, err := doResume(root, before, oldDigest, input); err == nil {
					t.Fatal("stale recovery writer was accepted")
				}
				if _, after, err := loadDoSession(root, before.ID); err != nil || after != currentDigest {
					t.Fatalf("rejected recovery changed the current checkpoint: %v", err)
				}
				if _, err := os.Stat(filepath.Join(root, filepath.FromSlash(doReadonlySnapshotRef(t, before, input)))); !os.IsNotExist(err) {
					t.Fatalf("rejected recovery left a snapshot: %v", err)
				}
			})
		}
	}
}

func TestDoReadonlyRecoveryRejectsInvalidOrUnownedEvidence(t *testing.T) {
	tests := []struct {
		name   string
		change func(*DoRecovery)
	}{
		{"no-source", func(r *DoRecovery) { r.EvidenceText = "" }},
		{"whitespace", func(r *DoRecovery) { r.EvidenceText = " \t\n" }},
		{"oversized", func(r *DoRecovery) { r.EvidenceText = strings.Repeat("x", 64*1024+1) }},
		{"utf8-byte-limit", func(r *DoRecovery) { r.EvidenceText = strings.Repeat("检", 21846) }},
		{"invalid-utf8", func(r *DoRecovery) { r.EvidenceText = string([]byte{0xff}) }},
		{"dual-source", func(r *DoRecovery) { r.EvidenceRef = "source.txt" }},
		{"outside-original-scope", func(r *DoRecovery) { r.EvidenceText = ""; r.EvidenceRef = "source.txt" }},
	}
	for _, test := range tests {
		t.Run(test.name, func(t *testing.T) {
			root, session, input := doReadonlyFailureFixture(t)
			_, digest, _ := loadDoSession(root, session.ID)
			test.change(&input.Recovery)
			if _, err := doResume(root, session, digest, input); err == nil {
				t.Fatal("invalid recovery evidence was accepted")
			}
			if _, after, err := loadDoSession(root, session.ID); err != nil || after != digest {
				t.Fatalf("rejected evidence mutated its checkpoint: %v", err)
			}
			snapshots, err := filepath.Glob(filepath.Join(root, ".specify/do/sessions", session.ID, "evidence/recovery-*.txt"))
			if err != nil || len(snapshots) != 0 {
				t.Fatalf("rejected evidence left a snapshot: %v %v", err, snapshots)
			}
		})
	}
	t.Run("exact-byte-limit", func(t *testing.T) {
		root, session, input := doReadonlyFailureFixture(t)
		input.Recovery.EvidenceText += strings.Repeat(" ", 64*1024-len(input.Recovery.EvidenceText))
		session = doReadonlyResumePublic(t, root, session, input)
		doReadonlyAssertSnapshot(t, root, session, input)
	})
}

func TestDoReadonlyRecoveryInputPresenceIsExclusive(t *testing.T) {
	tests := []struct {
		name, fields string
		valid        bool
	}{
		{"text-only", `"evidence_text":"native inspection"`, true},
		{"ref-only", `"evidence_ref":"out/recovery.txt"`, true},
		{"empty-ref-with-text", `"evidence_ref":"","evidence_text":"native inspection"`, false},
		{"null-ref-with-text", `"evidence_ref":null,"evidence_text":"native inspection"`, false},
		{"ref-with-empty-text", `"evidence_ref":"out/recovery.txt","evidence_text":""`, false},
		{"ref-with-null-text", `"evidence_ref":"out/recovery.txt","evidence_text":null`, false},
		{"empty-ref", `"evidence_ref":""`, false},
		{"null-ref", `"evidence_ref":null`, false},
		{"empty-text", `"evidence_text":""`, false},
		{"null-text", `"evidence_text":null`, false},
		{"both-populated", `"evidence_ref":"out/recovery.txt","evidence_text":"native inspection"`, false},
	}
	for _, test := range tests {
		t.Run(test.name, func(t *testing.T) {
			raw := fmt.Sprintf(`{"expected_revision":1,"attempt_id":"failed-git","recovery":{"reason":"inspected native effects","processes_stopped":true,"side_effects_inspected":true,%s}}`, test.fields)
			var input doResumeInput
			err := doReadInput(raw, &input)
			if (err == nil) != test.valid {
				t.Fatalf("wrong public input presence decision: %v", err)
			}
			if test.valid && (input.Recovery.EvidenceRef == "") == (input.Recovery.EvidenceText == "") {
				t.Fatal("public decoder lost its selected evidence source")
			}
		})
	}
}
