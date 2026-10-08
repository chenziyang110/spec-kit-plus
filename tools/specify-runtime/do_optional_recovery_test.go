package main

import (
	"bufio"
	"context"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"testing"
	"time"

	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/runcontrol"
)

func TestDoWaitChild(t *testing.T) {
	if os.Getenv("SPECIFY_DO_OPTIONAL_RECOVERY_HELPER") != "1" {
		return
	}
	fmt.Println("optional operation started")
	time.Sleep(30 * time.Second)
}

func doOptionalTimeoutFixture(t *testing.T, requiredDependency bool) (string, DoSession, DoRecovery) {
	t.Helper()
	root, input := doFixture(t)
	executable, err := filepath.Abs(os.Args[0])
	if err != nil {
		t.Fatal(err)
	}
	t.Setenv("PATH", filepath.Dir(executable)+string(os.PathListSeparator)+os.Getenv("PATH"))
	argv := []string{filepath.Base(executable), "-test.run", "^TestDoWaitChild$"}
	input.Definition.Steps = append(input.Definition.Steps, PlaybookStep{ID: "optional", Purpose: "inspect an optional slow local operation", Cwd: ".", Argv: argv, Required: false, ExpectedResult: "the bounded probe completes", SideEffect: "read"})
	if requiredDependency {
		input.Definition.Checks[0].DependsOn = append(input.Definition.Checks[0].DependsOn, "optional")
	}
	session, err := doStart(root, input)
	if err != nil {
		t.Fatal(err)
	}
	if !requiredDependency {
		session = doRunFixture(t, root, session)
	}
	session = doRecordFixture(t, root, session, "start-optional", doRecordEvent{AttemptID: "optional-timeout", TargetID: "optional", Kind: "step", Event: "started"})
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	command := exec.CommandContext(ctx, argv[0], argv[1:]...)
	command.Dir = root
	command.Env = append(os.Environ(), "SPECIFY_DO_OPTIONAL_RECOVERY_HELPER=1")
	stdout, err := command.StdoutPipe()
	if err != nil {
		t.Fatal(err)
	}
	started := doNow()
	if err := command.Start(); err != nil {
		t.Fatal(err)
	}
	waited := false
	defer func() {
		if !waited {
			cancel()
			_ = command.Wait()
		}
	}()
	line, err := bufio.NewReader(stdout).ReadString('\n')
	if err != nil || line != "optional operation started\n" {
		t.Fatalf("native helper did not reach its real operation: %q %v", line, err)
	}
	// Start the execution deadline only after the actual child acknowledges
	// startup, so slow process creation is not mistaken for executed work.
	timer := time.AfterFunc(25*time.Millisecond, cancel)
	err = command.Wait()
	waited = true
	timer.Stop()
	if err == nil || ctx.Err() != context.Canceled || command.ProcessState == nil {
		t.Fatalf("expected a real timed-out and reaped native process: %v %v", err, ctx.Err())
	}
	finished := doNow()
	session = doRecordFixture(t, root, session, "complete-optional", doRecordEvent{AttemptID: "optional-timeout", TargetID: "optional", Kind: "step", Event: "completed", Status: "interrupted", TimedOut: true, EvidenceOrigin: "agent_tool_observation", ToolCallID: "test-native-optional-timeout", Argv: argv, Cwd: ".", StartedAt: started, FinishedAt: finished, Summary: "The native optional process reached its deadline; inspect its effects before closeout"})
	if err := os.MkdirAll(filepath.Join(root, "out"), 0o755); err != nil {
		t.Fatal(err)
	}
	ref := "out/optional-recovery.txt"
	report := fmt.Sprintf("native stdout: %s\nnative wait returned: %v\nprocess state: %s\nNo descendant processes were started and this helper writes no source or outputs.\n", line, err, command.ProcessState.String())
	if err := os.WriteFile(filepath.Join(root, ref), []byte(report), 0o600); err != nil {
		t.Fatal(err)
	}
	return root, session, DoRecovery{Reason: "inspected the reaped native process and its bounded read-only effects", EvidenceRef: ref, ProcessesStopped: true, SideEffectsInspected: true}
}

func TestDoOptionalTimeoutBlocksCloseoutUntilRecoveredWithoutRerun(t *testing.T) {
	root, session, recovery := doOptionalTimeoutFixture(t, false)
	validation := doValidate(root, session, true)
	if validation.Status == "passed" || !strings.Contains(strings.Join(validation.Blockers, " "), "optional-timeout") {
		t.Fatalf("an unrecovered optional timeout passed validation: %+v", validation)
	}
	_, digest, err := loadDoSession(root, session.ID)
	if err != nil {
		t.Fatal(err)
	}
	for _, disposition := range []string{"pending", "not_applicable"} {
		if _, err := doFinish(root, session, digest, doFinishInput{ExpectedRevision: session.Revision, KnowledgeStatus: disposition}); err == nil {
			t.Fatalf("knowledge=%s closed an unrecovered optional timeout", disposition)
		}
	}
	if _, err := updatePlaybook(root, PlaybookUpdateRequest{Definition: session.Definition, SessionID: session.ID, ChangeSummary: "Capture the operation only after recovery"}); err == nil {
		t.Fatal("Playbook publication bypassed optional timeout recovery")
	}
	if _, err := loadPlaybookDocument(root, playbookID(session.Definition)); !os.IsNotExist(err) {
		t.Fatalf("a method was published before recovery: %v", err)
	}
	attemptCount := len(session.Attempts)
	session, err = doResume(root, session, digest, doResumeInput{ExpectedRevision: session.Revision, AttemptID: "optional-timeout", Recovery: recovery})
	if err != nil {
		t.Fatal(err)
	}
	if len(session.Attempts) != attemptCount || session.Attempts[attemptCount-1].Status != "interrupted" || session.Attempts[attemptCount-1].Recovery == nil {
		t.Fatal("recovery erased the interruption or invented a successful optional retry")
	}
	if validation := doValidate(root, session, true); validation.Status != "passed" {
		t.Fatalf("recovered optional work incorrectly became a new success obligation: %+v", validation)
	}
	_, digest, err = loadDoSession(root, session.ID)
	if err != nil {
		t.Fatal(err)
	}
	session, err = doFinish(root, session, digest, doFinishInput{ExpectedRevision: session.Revision, KnowledgeStatus: "pending"})
	if err != nil {
		t.Fatal(err)
	}
	publication := playbookPublishFixture(t, root, session, "")
	playbookFinishFixture(t, root, session.ID, publication)
	store, err := runcontrol.OpenViewForRepository(context.Background(), root)
	if err != nil {
		t.Fatal(err)
	}
	defer store.Close()
	work, _, err := store.GetWork(context.Background(), session.WorkID)
	if err != nil || work.Status != runcontrol.WorkCompleted {
		t.Fatalf("fully recovered and saved operation did not complete Work: %+v %v", work, err)
	}
}

func TestDoOptionalRecoveryPreservesRequiredDependencyObligation(t *testing.T) {
	root, session, recovery := doOptionalTimeoutFixture(t, true)
	_, digest, err := loadDoSession(root, session.ID)
	if err != nil {
		t.Fatal(err)
	}
	session, err = doResume(root, session, digest, doResumeInput{ExpectedRevision: session.Revision, AttemptID: "optional-timeout", Recovery: recovery})
	if err != nil {
		t.Fatal(err)
	}
	validation := doValidate(root, session, true)
	if validation.Status == "passed" || !strings.Contains(strings.Join(validation.Blockers, " "), "step optional has no current passed attempt") {
		t.Fatalf("recovering an optional dependency erased its required consumer's obligation: %+v", validation)
	}
}
