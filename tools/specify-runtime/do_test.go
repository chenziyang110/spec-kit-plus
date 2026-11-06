package main

import (
	"bytes"
	"context"
	"encoding/json"
	"os"
	"os/exec"
	"path/filepath"
	"reflect"
	"runtime"
	"strings"
	"testing"
	"time"

	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/runcontrol"
)

func doFixture(t *testing.T) (string, doStartInput) {
	t.Helper()
	root := initCoordinationCLIRepository(t)
	if err := os.WriteFile(filepath.Join(root, "source.txt"), []byte("source v1\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	gitRun(t, root, "add", "source.txt")
	gitRun(t, root, "-c", "user.name=Do Test", "-c", "user.email=do@example.test", "commit", "-m", "fixture")
	definition := PlaybookDefinition{Operation: "test", Target: "fixture", Owner: "runtime", Variant: "default", Title: "Verify a local operation", Goal: "Run the local verification", SourceFiles: []string{"source.txt"}, Steps: []PlaybookStep{{ID: "run", Purpose: "invoke the actual local Git tool", Cwd: ".", Argv: []string{"git", "--version"}, Required: true, ExpectedResult: "exit zero", SideEffect: "read"}}, Checks: []PlaybookCheck{{ID: "report", Purpose: "verify the generated report", Cwd: ".", Argv: []string{}, DependsOn: []string{"run"}, Required: true, ExpectedResult: "report confirms success", Kind: "json", ResultPath: "out/report.json", JSONPointer: "/ok", ExpectedJSON: json.RawMessage(`true`)}}}
	return root, doStartInput{SessionID: "fixture", Definition: definition, OutputScope: []string{"out"}, AgentID: "do-test", AdapterID: "test"}
}

func doStartFixture(t *testing.T) (string, DoSession) {
	t.Helper()
	root, input := doFixture(t)
	session, err := doStart(root, input)
	if err != nil {
		t.Fatal(err)
	}
	return root, session
}

func doRecordFixture(t *testing.T, root string, session DoSession, request string, events ...doRecordEvent) DoSession {
	t.Helper()
	current, digest, err := loadDoSession(root, session.ID)
	if err != nil {
		t.Fatal(err)
	}
	result, err := doRecord(root, current, digest, doRecordInput{ExpectedRevision: current.Revision, RequestID: request, Events: events})
	if err != nil {
		t.Fatal(err)
	}
	return result
}

func doRunFixture(t *testing.T, root string, session DoSession) DoSession {
	t.Helper()
	session = doRecordFixture(t, root, session, "start-command", doRecordEvent{AttemptID: "run-1", TargetID: "run", Kind: "step", Event: "started"})
	started := doNow()
	command := exec.Command("git", "--version")
	command.Dir = root
	output, err := command.CombinedOutput()
	if err != nil {
		t.Fatalf("actual test command failed: %v %s", err, output)
	}
	finished := doNow()
	zero := 0
	session = doRecordFixture(t, root, session, "complete-command", doRecordEvent{AttemptID: "run-1", TargetID: "run", Kind: "step", Event: "completed", Status: "passed", EvidenceOrigin: "agent_tool_observation", ToolCallID: "test-real-git-call", Argv: []string{"git", "--version"}, Cwd: ".", StartedAt: started, FinishedAt: finished, ExitCode: &zero, Summary: strings.TrimSpace(string(output))})
	session = doRecordFixture(t, root, session, "start-report", doRecordEvent{AttemptID: "report-1", TargetID: "report", Kind: "check", Event: "started"})
	started = doNow()
	if err := os.MkdirAll(filepath.Join(root, "out"), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(root, "out/report.json"), []byte(`{"ok":true}`), 0o644); err != nil {
		t.Fatal(err)
	}
	finished = doNow()
	return doRecordFixture(t, root, session, "complete-report", doRecordEvent{AttemptID: "report-1", TargetID: "report", Kind: "check", Event: "completed", Status: "passed", EvidenceOrigin: "agent_tool_observation", ToolCallID: "test-real-file-read", Argv: []string{}, Cwd: ".", StartedAt: started, FinishedAt: finished, ResultRefs: []DoResultRef{{Path: "out/report.json", Kind: "json"}}})
}

func TestDoCompleteUsesFreshTypedEvidenceWithoutInventingCognition(t *testing.T) {
	root, session := doStartFixture(t)
	session = doRunFixture(t, root, session)
	validation := doValidate(root, session, true)
	if validation.Status != "passed" || validation.RequiredSteps != 1 || validation.RequiredChecks != 1 || validation.CognitionCloseout != "not_applicable" {
		t.Fatalf("unexpected validation: %+v", validation)
	}
	_, digest, err := loadDoSession(root, session.ID)
	if err != nil {
		t.Fatal(err)
	}
	finished, err := doFinish(root, session, digest, doFinishInput{ExpectedRevision: session.Revision, KnowledgeStatus: "not_applicable"})
	if err != nil {
		t.Fatal(err)
	}
	if finished.ExecutionOutcome != "passed" || finished.KnowledgeStatus != "not_applicable" {
		t.Fatal(finished)
	}
	if _, err := os.Stat(filepath.Join(root, ".specify/do/sessions/fixture/cognition-closeout.json")); !os.IsNotExist(err) {
		t.Fatal("read/output-only operation invented cognition receipt")
	}
	var out bytes.Buffer
	if code := runDo([]string{"show", "--active", "--project-root", root, "--format", "json"}, &out); code != 0 {
		t.Fatalf("%d %s", code, out.String())
	}
	if !bytes.Contains(out.Bytes(), []byte(`"active":false`)) {
		t.Fatal(out.String())
	}
}

func TestDoRequiredChecksAndOldEvidenceCannotBeReplacedByPassNarration(t *testing.T) {
	root, session := doStartFixture(t)
	validation := doValidate(root, session, true)
	if validation.Status == "passed" || len(validation.Blockers) < 2 {
		t.Fatal(validation)
	}
	before, digest, err := loadDoSession(root, session.ID)
	if err != nil {
		t.Fatal(err)
	}
	zero := 0
	_, err = doRecord(root, before, digest, doRecordInput{ExpectedRevision: before.Revision, RequestID: "fabricated", Events: []doRecordEvent{{AttemptID: "never-started", TargetID: "run", Kind: "step", Event: "completed", Status: "passed", ExitCode: &zero}}})
	if err == nil {
		t.Fatal("accepted a completion with no started checkpoint")
	}
	session = doRunFixture(t, root, session)
	if err := os.WriteFile(filepath.Join(root, "source.txt"), []byte("source v2\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	validation = doValidate(root, session, true)
	if validation.Status == "passed" || !strings.Contains(strings.Join(validation.Blockers, " "), "stale") {
		t.Fatal(validation)
	}
}

func TestDoBatchRecordIsAtomicAndIdempotent(t *testing.T) {
	root, session := doStartFixture(t)
	_, digest, _ := loadDoSession(root, session.ID)
	input := doRecordInput{ExpectedRevision: session.Revision, RequestID: "batch-one", Events: []doRecordEvent{{AttemptID: "run-1", TargetID: "run", Kind: "step", Event: "started"}, {AttemptID: "unknown", TargetID: "missing", Kind: "step", Event: "started"}}}
	if _, err := doRecord(root, session, digest, input); err == nil {
		t.Fatal("invalid partial batch passed")
	}
	after, newDigest, err := loadDoSession(root, session.ID)
	if err != nil {
		t.Fatal(err)
	}
	if newDigest != digest || len(after.Attempts) != 0 {
		t.Fatal("failed batch wrote partial state")
	}
	input.Events = input.Events[:1]
	after, err = doRecord(root, after, newDigest, input)
	if err != nil {
		t.Fatal(err)
	}
	replayed, err := doRecord(root, after, "", input)
	if err != nil || replayed.Revision != after.Revision {
		t.Fatalf("duplicate changed state: %v", err)
	}
	input.Events[0].AttemptID = "changed"
	if _, err := doRecord(root, after, "", input); err == nil {
		t.Fatal("reused key accepted a changed payload")
	}
}

func TestDoTimeoutRetainsAttemptAndRequiresInspectionBeforeRetry(t *testing.T) {
	root, session := doStartFixture(t)
	session = doRecordFixture(t, root, session, "start", doRecordEvent{AttemptID: "run-1", TargetID: "run", Kind: "step", Event: "started"})
	now := doNow()
	zero := 0
	event := doRecordEvent{AttemptID: "run-1", TargetID: "run", Kind: "step", Event: "completed", Status: "passed", TimedOut: true, EvidenceOrigin: "agent_tool_observation", ToolCallID: "timed-out-call", Argv: []string{"git", "--version"}, Cwd: ".", StartedAt: now, FinishedAt: now, ExitCode: &zero}
	_, digest, _ := loadDoSession(root, session.ID)
	if _, err := doRecord(root, session, digest, doRecordInput{ExpectedRevision: session.Revision, RequestID: "bad-pass", Events: []doRecordEvent{event}}); err == nil {
		t.Fatal("timeout reported as passed")
	}
	event.Status = "interrupted"
	session = doRecordFixture(t, root, session, "timeout", event)
	_, digest, _ = loadDoSession(root, session.ID)
	retry := doRecordInput{ExpectedRevision: session.Revision, RequestID: "retry", Events: []doRecordEvent{{AttemptID: "run-2", TargetID: "run", Kind: "step", Event: "started"}}}
	if _, err := doRecord(root, session, digest, retry); err == nil {
		t.Fatal("blind retry of interrupted effects accepted")
	}
	if err := os.MkdirAll(filepath.Join(root, "out"), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(root, "out/recovery.txt"), []byte("native session ended; no child process or artifact mutation remains"), 0o644); err != nil {
		t.Fatal(err)
	}
	session, err := doResume(root, session, digest, doResumeInput{ExpectedRevision: session.Revision, AttemptID: "run-1", Recovery: DoRecovery{Reason: "checked native tool session and output directory", EvidenceRef: "out/recovery.txt", ProcessesStopped: true, SideEffectsInspected: true}})
	if err != nil {
		t.Fatal(err)
	}
	session = doRecordFixture(t, root, session, "retry-after-inspection", retry.Events...)
	if len(session.Attempts) != 2 || session.Attempts[0].Status != "interrupted" {
		t.Fatal(session.Attempts)
	}
}

func TestDoOutputClaimsPreventConcurrentOverwrite(t *testing.T) {
	root, input := doFixture(t)
	first, err := doStart(root, input)
	if err != nil {
		t.Fatal(err)
	}
	input.SessionID = "second"
	if _, err := doStart(root, input); err == nil {
		t.Fatal("two sessions obtained the same output directory")
	}
	if _, err := os.Stat(filepath.Join(root, filepath.FromSlash(doSessionRef("second")))); !os.IsNotExist(err) {
		t.Fatal("conflict published another session")
	}
	input.OutputScope = []string{"other-out"}
	input.Definition.Checks[0].ResultPath = "other-out/report.json"
	if _, err := doStart(root, input); err != nil {
		t.Fatal(err)
	}
	var out bytes.Buffer
	if code := runDo([]string{"show", "--active", "--project-root", root}, &out); code == 0 || !bytes.Contains(out.Bytes(), []byte(`"ambiguous":true`)) {
		t.Fatalf("multiple sessions guessed latest: %d %s", code, out.String())
	}
	if first.ID != "fixture" {
		t.Fatal(first.ID)
	}
}

func TestDoTypedReportRejectsSkippedEmptyMalformedAndFalseAssertions(t *testing.T) {
	for _, raw := range []string{`<testsuite tests="0"></testsuite>`, `<testsuite><testcase><skipped/></testcase></testsuite>`, `<testsuite failures="1"><testcase/></testsuite>`, `<testsuite><testcase/><error/></testsuite>`, `not xml`} {
		if err := doAuditJUnit([]byte(raw), 1); err == nil {
			t.Fatalf("accepted invalid report: %s", raw)
		}
	}
	if err := doAuditJUnit([]byte(`<testsuites><testsuite failures="0" errors="0" skipped="0"><testcase name="real"/></testsuite></testsuites>`), 1); err != nil {
		t.Fatal(err)
	}
	root, session := doStartFixture(t)
	session = doRunFixture(t, root, session)
	ref := session.Attempts[1].Results[0]
	if err := os.WriteFile(filepath.Join(root, filepath.FromSlash(ref.SnapshotRef)), []byte(`{"ok":false}`), 0o600); err != nil {
		t.Fatal(err)
	}
	if validation := doValidate(root, session, true); validation.Status == "passed" {
		t.Fatal("changed immutable report passed")
	}
}

func TestDoRecordsCannotWidenFrozenCommandOrCaptureOutsideScope(t *testing.T) {
	root, session := doStartFixture(t)
	session = doRecordFixture(t, root, session, "start", doRecordEvent{AttemptID: "run-1", TargetID: "run", Kind: "step", Event: "started"})
	now := doNow()
	zero := 0
	event := doRecordEvent{AttemptID: "run-1", TargetID: "run", Kind: "step", Event: "completed", Status: "passed", EvidenceOrigin: "agent_tool_observation", ToolCallID: "actual-call", Argv: []string{"git", "status"}, Cwd: ".", StartedAt: now, FinishedAt: now, ExitCode: &zero}
	_, digest, _ := loadDoSession(root, session.ID)
	if _, err := doRecord(root, session, digest, doRecordInput{ExpectedRevision: session.Revision, RequestID: "widen", Events: []doRecordEvent{event}}); err == nil {
		t.Fatal("changed argv accepted")
	}
	event.Argv = []string{"git", "--version"}
	event.ResultRefs = []DoResultRef{{Path: "../secret", Kind: "log"}}
	if _, err := doRecord(root, session, digest, doRecordInput{ExpectedRevision: session.Revision, RequestID: "escape", Events: []doRecordEvent{event}}); err == nil {
		t.Fatal("outside evidence accepted")
	}
}

func TestDoReadOnlyShowAndValidateDoNotWriteState(t *testing.T) {
	root, session := doStartFixture(t)
	before, err := os.ReadFile(filepath.Join(root, filepath.FromSlash(doSessionRef(session.ID))))
	if err != nil {
		t.Fatal(err)
	}
	for _, args := range [][]string{{"show", session.ID}, {"resume", session.ID}, {"validate", session.ID}} {
		var out bytes.Buffer
		runDo(append(args, "--project-root", root), &out)
		if out.Len() == 0 {
			t.Fatal("missing structured response")
		}
	}
	after, err := os.ReadFile(filepath.Join(root, filepath.FromSlash(doSessionRef(session.ID))))
	if err != nil {
		t.Fatal(err)
	}
	if !reflect.DeepEqual(before, after) {
		t.Fatal("read-only routes changed state")
	}
	var input doFinishInput
	if err := doReadInput(`{"expected_revision":1,"expected_revision":2}`, &input); err == nil {
		t.Fatal("duplicate input keys accepted")
	}
	if _, err := doPath(root, "out/../../escape", false); err == nil {
		t.Fatal("path escape accepted")
	}
}

func TestDoImmutableReportSurvivesOriginalMetadataChangeButCannotBecomeFreshAgain(t *testing.T) {
	root, session := doStartFixture(t)
	session = doRunFixture(t, root, session)
	// A new run may reuse a method but must not inherit the old output as fresh.
	if err := os.Chtimes(filepath.Join(root, "out/report.json"), time.Now().Add(-time.Hour), time.Now().Add(-time.Hour)); err != nil {
		t.Fatal(err)
	}
	ref := session.Attempts[1].Results[0]
	if ref.SnapshotRef == "" || ref.SHA256 == "" {
		t.Fatal("typed evidence lacks runtime-owned snapshot/digest")
	}
	validation := doValidate(root, session, true)
	if validation.Status != "passed" {
		t.Fatalf("immutable recorded evidence should remain source-bound: %+v", validation)
	}
	session = doRecordFixture(t, root, session, "fresh-check", doRecordEvent{AttemptID: "report-2", TargetID: "report", Kind: "check", Event: "started"})
	_, digest, _ := loadDoSession(root, session.ID)
	now := doNow()
	_, err := doRecord(root, session, digest, doRecordInput{ExpectedRevision: session.Revision, RequestID: "reuse-old-report", Events: []doRecordEvent{{AttemptID: "report-2", TargetID: "report", Kind: "check", Event: "completed", Status: "passed", EvidenceOrigin: "agent_tool_observation", ToolCallID: "real-old-file-read", Cwd: ".", StartedAt: now, FinishedAt: now, ResultRefs: []DoResultRef{{Path: "out/report.json", Kind: "json"}}}}})
	if err == nil || !strings.Contains(err.Error(), "predates") {
		t.Fatalf("old producer output counted as new evidence: %v", err)
	}
}

func TestDoStartAndFinishRetriesDoNotReviseOrRerun(t *testing.T) {
	root, input := doFixture(t)
	session, err := doStart(root, input)
	if err != nil {
		t.Fatal(err)
	}
	again, err := doStart(root, input)
	if err != nil || again.Revision != session.Revision || again.WorkID != session.WorkID {
		t.Fatalf("start retry duplicated state: %v", err)
	}
	input.Definition.Goal = "a different operation"
	if _, err := doStart(root, input); err == nil {
		t.Fatal("start retry silently changed the frozen goal")
	}
	session = doRunFixture(t, root, session)
	_, digest, _ := loadDoSession(root, session.ID)
	finish := doFinishInput{ExpectedRevision: session.Revision, KnowledgeStatus: "not_applicable"}
	session, err = doFinish(root, session, digest, finish)
	if err != nil {
		t.Fatal(err)
	}
	again, err = doFinish(root, session, "old-digest-is-not-used-on-replay", finish)
	if err != nil || again.Revision != session.Revision || len(again.Attempts) != 2 {
		t.Fatalf("finish replay revised or reran: %v", err)
	}
}

func TestDoExternalBlockerAllowsHonestStopAndOnlyFreshResolution(t *testing.T) {
	root, session := doStartFixture(t)
	if err := os.MkdirAll(filepath.Join(root, "out"), 0o755); err != nil {
		t.Fatal(err)
	}
	proof := filepath.Join(root, "out/access.txt")
	if err := os.WriteFile(proof, []byte("external test service reported unavailable"), 0o600); err != nil {
		t.Fatal(err)
	}
	_, digest, _ := loadDoSession(root, session.ID)
	blocker := DoBlocker{Owner: "agent", Category: "dependency", Cause: "test service unavailable", NextAction: "service owner restores test endpoint", UnblockCriteria: "native request reaches the test endpoint", ResumePoint: "run", AttemptedRecovery: []string{"checked configured endpoint and current connection response"}, EvidenceRefs: []string{"out/access.txt"}}
	input := doFinishInput{ExpectedRevision: session.Revision, Blocker: &blocker}
	if _, err := doFinish(root, session, digest, input); err == nil {
		t.Fatal("agent-owned failure became a terminal excuse")
	}
	blocker.Owner = "external"
	session, err := doFinish(root, session, digest, input)
	if err != nil {
		t.Fatal(err)
	}
	replayed, err := doFinish(root, session, "", input)
	if err != nil || replayed.Revision != session.Revision {
		t.Fatalf("blocker retry changed state: %v", err)
	}
	var out bytes.Buffer
	if code := runDo([]string{"show", "--active", "--project-root", root}, &out); code != 0 || !bytes.Contains(out.Bytes(), []byte(`"can_stop":true`)) || !bytes.Contains(out.Bytes(), []byte(`"terminal":false`)) {
		t.Fatalf("blocked Do lost its resume context: %d %s", code, out.String())
	}
	if validation := doValidate(root, session, true); validation.Status == "passed" {
		t.Fatal("external blocker was reported as a passed execution")
	}
	_, digest, _ = loadDoSession(root, session.ID)
	resume := doResumeInput{ExpectedRevision: session.Revision, Recovery: DoRecovery{Reason: "checked restored external dependency and retained outputs", EvidenceRef: "out/access.txt", ProcessesStopped: true, SideEffectsInspected: true}}
	if _, err := doResume(root, session, digest, resume); err == nil {
		t.Fatal("unchanged failure evidence resolved the blocker")
	}
	if err := os.WriteFile(proof, []byte("new native request succeeded; previous attempt stopped; outputs inspected"), 0o600); err != nil {
		t.Fatal(err)
	}
	session, err = doResume(root, session, digest, resume)
	if err != nil || session.Blocker != nil || len(session.BlockerHistory) != 1 {
		t.Fatalf("resolution failed: %v %+v", err, session.Blocker)
	}
	replayed, err = doResume(root, session, "", resume)
	if err != nil || replayed.Revision != session.Revision || len(replayed.BlockerHistory) != 1 {
		t.Fatalf("resolution replay duplicated history: %v", err)
	}
}

func TestDoInterruptedWorkRequiresExplicitRecoveredFence(t *testing.T) {
	root, session := doStartFixture(t)
	session = doRecordFixture(t, root, session, "start-interrupted", doRecordEvent{AttemptID: "run-1", TargetID: "run", Kind: "step", Event: "started"})
	store, err := runcontrol.OpenForRepository(context.Background(), root)
	if err != nil {
		t.Fatal(err)
	}
	defer store.Close()
	work, _, err := store.GetWork(context.Background(), session.WorkID)
	if err != nil {
		t.Fatal(err)
	}
	work, err = store.InterruptWork(context.Background(), runcontrol.InterruptWorkParams{WorkID: work.WorkID, Fence: work.Fence, ExpectedRevision: work.Revision, Reason: "native session interrupted", ObservedPaths: []string{doSessionRef(session.ID)}})
	if err != nil {
		t.Fatal(err)
	}
	work, err = store.ResumeWork(context.Background(), runcontrol.ResumeWorkParams{WorkID: work.WorkID, ExpectedRevision: work.Revision, AgentID: "recovery-agent", AdapterID: "test", WorkspaceRoot: root, LeaseUntil: time.Now().UTC().Add(time.Hour)})
	if err != nil {
		t.Fatal(err)
	}
	if err := os.MkdirAll(filepath.Join(root, "out"), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(root, "out/recovery.txt"), []byte("native process stopped and owned output paths inspected"), 0o600); err != nil {
		t.Fatal(err)
	}
	_, digest, _ := loadDoSession(root, session.ID)
	resume := doResumeInput{ExpectedRevision: session.Revision, AttemptID: "run-1", Recovery: DoRecovery{Reason: "explicit owner recovery followed native process inspection", EvidenceRef: "out/recovery.txt", ProcessesStopped: true, SideEffectsInspected: true}}
	if _, err := doResume(root, session, digest, resume); err == nil {
		t.Fatal("Do silently adopted a newer Work owner")
	}
	resume.WorkFence = work.Fence - 1
	if _, err := doResume(root, session, digest, resume); err == nil {
		t.Fatal("Do accepted a stale recovery fence")
	}
	resume.WorkFence = work.Fence
	session, err = doResume(root, session, digest, resume)
	if err != nil || session.WorkFence != work.Fence || session.Attempts[0].Status != "interrupted" {
		t.Fatalf("explicit recovery failed: %v", err)
	}
	session = doRecordFixture(t, root, session, "fresh-after-work-recovery", doRecordEvent{AttemptID: "run-2", TargetID: "run", Kind: "step", Event: "started"})
	if len(session.Attempts) != 2 {
		t.Fatal("recovery discarded the unknown original attempt")
	}
}

func TestDoOwnedSourceChangesRequireExactFreshCognitionCloseout(t *testing.T) {
	root, input := doFixture(t)
	input.WriteScope = []string{"scripts"}
	session, err := doStart(root, input)
	if err != nil {
		t.Fatal(err)
	}
	if err := os.MkdirAll(filepath.Join(root, "scripts"), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(root, "scripts/check.sh"), []byte("#!/bin/sh\ngit --version\n"), 0o755); err != nil {
		t.Fatal(err)
	}
	session = doRunFixture(t, root, session)
	validation := doValidate(root, session, true)
	if validation.Status == "passed" || !reflect.DeepEqual(validation.ChangedSourcePaths, []string{"scripts/check.sh"}) || validation.CognitionCloseout != "required" {
		t.Fatal(validation)
	}
	scope := filepath.Dir(filepath.Join(root, filepath.FromSlash(doSessionRef(session.ID))))
	if _, err := writeMutationCognitionReceipt(scope, mutationCognitionReceipt{Version: mutationCognitionReceiptVersion, Workflow: "sp-do", Scope: ".specify/do/sessions/wrong", ResultState: "mark-dirty", Reason: "foreign scope fixture", ChangedPaths: []string{"scripts/check.sh"}, RecordedAt: doNow()}); err != nil {
		t.Fatal(err)
	}
	if validation := doValidate(root, session, true); validation.Status == "passed" {
		t.Fatal("foreign scope cognition receipt was accepted")
	}
	if _, err := recordMutationCognitionReceiptWithPaths(scope, "sp-do", ".specify/do/sessions/"+session.ID, "mark-dirty", "project graph requires refresh for the new owned script", "", []string{"scripts/check.sh"}, []string{"scripts/check.sh"}); err != nil {
		t.Fatal(err)
	}
	if validation := doValidate(root, session, true); validation.Status != "passed" || validation.CognitionCloseout != "mark-dirty" {
		t.Fatal(validation)
	}
	if err := os.WriteFile(filepath.Join(root, "scripts/new.sh"), []byte("#!/bin/sh\nexit 1\n"), 0o755); err != nil {
		t.Fatal(err)
	}
	if validation := doValidate(root, session, true); validation.Status == "passed" || !strings.Contains(strings.Join(validation.Blockers, " "), "stale") {
		t.Fatal("a new file inside owned source scope reused earlier pass evidence", validation)
	}
}

func TestDoLargeArtifactUsesSmallReceiptAndMustRemainIntact(t *testing.T) {
	root, session := doStartFixture(t)
	session = doRecordFixture(t, root, session, "artifact-start", doRecordEvent{AttemptID: "run-1", TargetID: "run", Kind: "step", Event: "started"})
	if err := os.MkdirAll(filepath.Join(root, "out"), 0o755); err != nil {
		t.Fatal(err)
	}
	raw := bytes.Repeat([]byte("large package bytes\n"), 180000)
	if err := os.WriteFile(filepath.Join(root, "out/package.bin"), raw, 0o644); err != nil {
		t.Fatal(err)
	}
	zero := 0
	now := doNow()
	session = doRecordFixture(t, root, session, "artifact-complete", doRecordEvent{AttemptID: "run-1", TargetID: "run", Kind: "step", Event: "completed", Status: "passed", EvidenceOrigin: "agent_tool_observation", ToolCallID: "test-package-fixture", Argv: []string{"git", "--version"}, Cwd: ".", StartedAt: now, FinishedAt: now, ExitCode: &zero, ResultRefs: []DoResultRef{{Path: "out/package.bin", Kind: "file"}}})
	ref := session.Attempts[0].Results[0]
	info, err := os.Stat(filepath.Join(root, filepath.FromSlash(ref.SnapshotRef)))
	if err != nil || info.Size() > 4096 || ref.Size != int64(len(raw)) {
		t.Fatalf("large artifact copied into session instead of hashed: %v", err)
	}
	if err := doVerifyArtifactReceipt(root, ref); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(root, "out/package.bin"), []byte("overwritten artifact"), 0o644); err != nil {
		t.Fatal(err)
	}
	if err := doVerifyArtifactReceipt(root, ref); err == nil {
		t.Fatal("changed package artifact remained passed")
	}
}

func TestDoSummaryDisclosesOnlyRequestedDefinitionAndAttemptDetails(t *testing.T) {
	root, session := doStartFixture(t)
	session = doRunFixture(t, root, session)
	var summary bytes.Buffer
	if code := runDo([]string{"show", session.ID, "--project-root", root}, &summary); code != 0 {
		t.Fatal(summary.String())
	}
	for _, hidden := range []string{`"baseline_json"`, `"initial_sources"`, `"requests"`, `"registered_at"`, `"source_files"`} {
		if bytes.Contains(summary.Bytes(), []byte(hidden)) {
			t.Fatalf("summary included internal/full detail %s", hidden)
		}
	}
	for _, section := range []string{"definition", "attempt:run-1"} {
		var detail bytes.Buffer
		if code := runDo([]string{"show", session.ID, "--section", section, "--project-root", root}, &detail); code != 0 {
			t.Fatal(detail.String())
		}
		if section == "definition" && !bytes.Contains(detail.Bytes(), []byte(`"source_files"`)) || section == "attempt:run-1" && !bytes.Contains(detail.Bytes(), []byte(`"registered_at"`)) {
			t.Fatalf("selected detail was not disclosed: %s", detail.String())
		}
	}
}

func TestDoCurrentReportCannotBeReplacedByItsHistoricalSnapshot(t *testing.T) {
	root, session := doStartFixture(t)
	session = doRunFixture(t, root, session)
	if err := os.WriteFile(filepath.Join(root, "out/report.json"), []byte(`{"ok":false}`), 0o644); err != nil {
		t.Fatal(err)
	}
	validation := doValidate(root, session, true)
	if validation.Status == "passed" || !strings.Contains(strings.Join(validation.Blockers, " "), "current result") {
		t.Fatalf("historical snapshot replaced current failed output: %+v", validation)
	}
	if err := os.Remove(filepath.Join(root, "out/report.json")); err != nil {
		t.Fatal(err)
	}
	if validation := doValidate(root, session, true); validation.Status == "passed" {
		t.Fatal("missing current report remained passed")
	}
}

func TestDoRerunningProducerRequiresNewDependentAcceptance(t *testing.T) {
	root, session := doStartFixture(t)
	session = doRunFixture(t, root, session)
	session = doRecordFixture(t, root, session, "producer-rerun-start", doRecordEvent{AttemptID: "run-2", TargetID: "run", Kind: "step", Event: "started"})
	start := doNow()
	command := exec.Command("git", "--version")
	command.Dir = root
	if output, err := command.CombinedOutput(); err != nil {
		t.Fatalf("native command: %v %s", err, output)
	}
	zero := 0
	session = doRecordFixture(t, root, session, "producer-rerun-complete", doRecordEvent{AttemptID: "run-2", TargetID: "run", Kind: "step", Event: "completed", Status: "passed", EvidenceOrigin: "agent_tool_observation", ToolCallID: "test-real-git-rerun", Argv: []string{"git", "--version"}, Cwd: ".", StartedAt: start, FinishedAt: doNow(), ExitCode: &zero})
	if validation := doValidate(root, session, true); validation.Status == "passed" || !strings.Contains(strings.Join(validation.Blockers, " "), "dependency") {
		t.Fatal("old acceptance was applied to a different producer attempt", validation)
	}
	session = doRecordFixture(t, root, session, "new-acceptance-start", doRecordEvent{AttemptID: "report-2", TargetID: "report", Kind: "check", Event: "started"})
	now := doNow()
	session = doRecordFixture(t, root, session, "new-acceptance-complete", doRecordEvent{AttemptID: "report-2", TargetID: "report", Kind: "check", Event: "completed", Status: "passed", EvidenceOrigin: "agent_tool_observation", ToolCallID: "test-current-report-read", Cwd: ".", StartedAt: now, FinishedAt: now, ResultRefs: []DoResultRef{{Path: "out/report.json", Kind: "json"}}})
	if validation := doValidate(root, session, true); validation.Status != "passed" {
		t.Fatal(validation)
	}
}

func TestDoPlatformContextCannotDriftAcrossResume(t *testing.T) {
	root, session := doStartFixture(t)
	session = doRunFixture(t, root, session)
	session.Context["os"] = "different-from-" + runtime.GOOS
	if validation := doValidate(root, session, true); validation.Status == "passed" || !strings.Contains(strings.Join(validation.Blockers, " "), "platform") {
		t.Fatal("foreign runtime platform reused the prior observation", validation)
	}
}

// This fixture uses a real native Git patch application to create one source
// report and modify an existing source. It returns before the cognition gate.
func doSourceMutationFixture(t *testing.T) (string, doStartInput, DoSession) {
	return doSourceMutationFixtureWithSetup(t, nil)
}

func doSourceMutationFixtureWithSetup(t *testing.T, setup func(string)) (string, doStartInput, DoSession) {
	t.Helper()
	root, input := doFixture(t)
	patch := "diff --git a/source.txt b/source.txt\n--- a/source.txt\n+++ b/source.txt\n@@ -1 +1 @@\n-source v1\n+source v2\ndiff --git a/generated/report.json b/generated/report.json\nnew file mode 100644\n--- /dev/null\n+++ b/generated/report.json\n@@ -0,0 +1 @@\n+{\"ok\":true}\n"
	if err := os.WriteFile(filepath.Join(root, "generate.patch"), []byte(patch), 0o644); err != nil {
		t.Fatal(err)
	}
	gitRun(t, root, "add", "generate.patch")
	gitRun(t, root, "-c", "user.name=Do Test", "-c", "user.email=do@example.test", "commit", "-m", "add source mutation fixture")
	input.Definition.Operation = "generate"
	input.Definition.SourceFiles = []string{"source.txt", "generate.patch"}
	input.Definition.Steps[0].Argv = []string{"git", "apply", "generate.patch"}
	input.Definition.Steps[0].SideEffect = "local_write"
	input.Definition.Steps[0].SourceWrites = []string{"source.txt", "generated"}
	input.Definition.Checks[0].ResultPath = "generated/report.json"
	input.WriteScope = []string{"source.txt", "generated"}
	// Runtime setup must bind to this isolated project, never an ancestor's cognition.
	if err := os.MkdirAll(filepath.Join(root, ".specify"), 0o755); err != nil {
		t.Fatal(err)
	}
	if setup != nil {
		setup(root)
	}
	session, err := doStart(root, input)
	if err != nil {
		t.Fatal(err)
	}
	session = doRecordFixture(t, root, session, "source-write-start", doRecordEvent{AttemptID: "run-1", TargetID: "run", Kind: "step", Event: "started"})
	started := doNow()
	command := exec.Command("git", "apply", "generate.patch")
	command.Dir = root
	output, err := command.CombinedOutput()
	if err != nil {
		t.Fatalf("native source mutation failed: %v %s", err, output)
	}
	zero := 0
	session = doRecordFixture(t, root, session, "source-write-complete", doRecordEvent{AttemptID: "run-1", TargetID: "run", Kind: "step", Event: "completed", Status: "passed", EvidenceOrigin: "agent_tool_observation", ToolCallID: "test-real-git-source-patch", Argv: input.Definition.Steps[0].Argv, Cwd: ".", StartedAt: started, FinishedAt: doNow(), ExitCode: &zero})
	session = doRecordFixture(t, root, session, "generated-check-start", doRecordEvent{AttemptID: "report-1", TargetID: "report", Kind: "check", Event: "started"})
	now := doNow()
	session = doRecordFixture(t, root, session, "generated-check-complete", doRecordEvent{AttemptID: "report-1", TargetID: "report", Kind: "check", Event: "completed", Status: "passed", EvidenceOrigin: "agent_tool_observation", ToolCallID: "test-real-generated-json-read", Cwd: ".", StartedAt: now, FinishedAt: now, ResultRefs: []DoResultRef{{Path: "generated/report.json", Kind: "json"}}})
	return root, input, session
}

func TestDoExplicitSourceMutationRequiresFinalChecksAndCognition(t *testing.T) {
	root, _, session := doSourceMutationFixture(t)
	mutation := session.Attempts[0]
	if mutation.SourceFingerprint == mutation.AfterSourceFingerprint || mutation.AfterSourceFingerprint != session.Attempts[1].SourceFingerprint || !reflect.DeepEqual(mutation.SourceChangedPaths, []string{"generated/report.json", "source.txt"}) {
		t.Fatalf("source mutation lost before/after causal proof: %+v", mutation)
	}
	validation := doValidate(root, session, true)
	if validation.Status == "passed" || validation.CognitionCloseout != "required" || len(validation.ChangedSourcePaths) != 2 {
		t.Fatalf("source mutation skipped cognition: %+v", validation)
	}
	scope := filepath.Dir(filepath.Join(root, filepath.FromSlash(doSessionRef(session.ID))))
	if _, err := recordMutationCognitionReceiptWithPaths(scope, "sp-do", ".specify/do/sessions/"+session.ID, "mark-dirty", "new generated source and existing source change remain declared project graph debt", "", validation.ChangedSourcePaths, validation.ChangedSourcePaths); err != nil {
		t.Fatal(err)
	}
	if validation := doValidate(root, session, true); validation.Status != "passed" {
		t.Fatalf("legitimate source-writing operation cannot finish: %+v", validation)
	}
	_, digest, _ := loadDoSession(root, session.ID)
	if _, err := doFinish(root, session, digest, doFinishInput{ExpectedRevision: session.Revision, KnowledgeStatus: "pending"}); err != nil {
		t.Fatal(err)
	}
}

func TestDoSourceMutationPermissionCannotExceedFrozenWorkScope(t *testing.T) {
	root, input := doFixture(t)
	input.Definition.Steps[0].SideEffect = "local_write"
	input.Definition.Steps[0].SourceWrites = []string{"source.txt"}
	if _, err := doStart(root, input); err == nil {
		t.Fatal("source-writing step started without source Work ownership")
	}
	input.WriteScope = []string{"source.txt", "scripts"}
	input.Definition.Steps[0].SourceWrites = []string{"scripts"}
	session, err := doStart(root, input)
	if err != nil {
		t.Fatal(err)
	}
	session = doRecordFixture(t, root, session, "restricted-writer-start", doRecordEvent{AttemptID: "run-1", TargetID: "run", Kind: "step", Event: "started"})
	if err := os.WriteFile(filepath.Join(root, "source.txt"), []byte("changed outside this step's source_writes"), 0o644); err != nil {
		t.Fatal(err)
	}
	_, digest, _ := loadDoSession(root, session.ID)
	now := doNow()
	zero := 0
	_, err = doRecord(root, session, digest, doRecordInput{ExpectedRevision: session.Revision, RequestID: "scope-exceeded", Events: []doRecordEvent{{AttemptID: "run-1", TargetID: "run", Kind: "step", Event: "completed", Status: "passed", EvidenceOrigin: "agent_tool_observation", ToolCallID: "test-observed-restricted-mutation", Argv: input.Definition.Steps[0].Argv, Cwd: ".", StartedAt: now, FinishedAt: now, ExitCode: &zero}}})
	if err == nil || !strings.Contains(err.Error(), "source_writes") {
		t.Fatalf("step used another step's broader Work write scope: %v", err)
	}
}

func TestDoActiveLookupFiltersTheActualWorkAdapter(t *testing.T) {
	root, input := doFixture(t)
	input.AdapterID = "claude"
	if _, err := doStart(root, input); err != nil {
		t.Fatal(err)
	}
	input.SessionID = "gemini-run"
	input.AdapterID = "gemini"
	input.OutputScope = []string{"gemini-out"}
	input.Definition.Checks[0].ResultPath = "gemini-out/report.json"
	if _, err := doStart(root, input); err != nil {
		t.Fatal(err)
	}
	for adapter, id := range map[string]string{"claude": "fixture", "gemini": "gemini-run"} {
		var out bytes.Buffer
		if code := runDo([]string{"show", "--active", "--adapter-id", adapter, "--project-root", root}, &out); code != 0 {
			t.Fatal(out.String())
		}
		if !bytes.Contains(out.Bytes(), []byte(`"session_id":"`+id+`"`)) {
			t.Fatalf("active selection crossed adapters: %s", out.String())
		}
	}
}

func TestDoNoOpSourceWriterRetainsCanonicalEmptyDirtySnapshot(t *testing.T) {
	root, input := doFixture(t)
	input.WriteScope = []string{"source.txt"}
	input.Definition.Steps[0].SideEffect = "local_write"
	input.Definition.Steps[0].SourceWrites = []string{"source.txt"}
	session, err := doStart(root, input)
	if err != nil {
		t.Fatal(err)
	}
	session = doRunFixture(t, root, session)
	session, _, err = loadDoSession(root, session.ID)
	if err != nil {
		t.Fatal(err)
	}
	if validation := doValidate(root, session, true); validation.Status != "passed" || validation.CognitionCloseout != "not_applicable" {
		t.Fatalf("a writer that made no source change lost its valid empty source snapshot: %+v", validation)
	}
}

func TestDoOversizeCheckpointCannotReplaceReadableState(t *testing.T) {
	root, session := doStartFixture(t)
	_, digest, err := loadDoSession(root, session.ID)
	if err != nil {
		t.Fatal(err)
	}
	session.Requests["too-large"] = strings.Repeat("x", doSessionSizeLimit)
	if err := doWriteSession(root, session, digest, nil); err == nil {
		t.Fatal("published a session the reader cannot load")
	}
	if _, after, err := loadDoSession(root, session.ID); err != nil || after != digest {
		t.Fatalf("oversize checkpoint damaged the last readable state: %v", err)
	}
}

func TestDoPublishedInputSchemasMatchRuntime(t *testing.T) {
	for filename, schema := range map[string]map[string]any{"do-start.schema.json": doStartInputSchema(), "do-prepare.schema.json": doPrepareInputSchema(), "do-record.schema.json": doRecordInputSchema(), "do-finish.schema.json": doFinishInputSchema(), "do-complete.schema.json": doCompleteInputSchema(), "do-resume.schema.json": doResumeInputSchema()} {
		raw, err := os.ReadFile(filepath.Join("..", "..", "templates", "artifacts", filename))
		if err != nil {
			t.Fatal(err)
		}
		var actual, expected any
		if err := json.Unmarshal(raw, &actual); err != nil {
			t.Fatal(err)
		}
		encoded, _ := json.Marshal(schema)
		_ = json.Unmarshal(encoded, &expected)
		if !reflect.DeepEqual(actual, expected) {
			t.Fatalf("published %s differs from its live API schema", filename)
		}
	}
}
