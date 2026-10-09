package main

import (
	"bytes"
	"encoding/json"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"
	"testing"
)

func TestDoCompletedEventMustMatchItsStartedAction(t *testing.T) {
	for _, kind := range []string{"step", "check"} {
		t.Run(kind, func(t *testing.T) {
			root, input := doFixture(t)
			if kind == "step" {
				input.Definition.Steps = append(input.Definition.Steps, PlaybookStep{ID: "other", Purpose: "a separate command", Cwd: ".", Argv: []string{"git", "--version"}, Required: false, ExpectedResult: "exit zero", SideEffect: "read"})
			} else {
				input.Definition.Checks = append(input.Definition.Checks, PlaybookCheck{ID: "other", Purpose: "a separate check", Cwd: ".", Argv: []string{"git", "--version"}, Required: false, ExpectedResult: "exit zero", Kind: "exit_code"})
			}
			session, err := doStart(root, input)
			if err != nil {
				t.Fatal(err)
			}
			session = doRecordFixture(t, root, session, "start-original", doRecordEvent{AttemptID: "original", TargetID: "run", Kind: "step", Event: "started"})
			started := doNow()
			command := exec.Command("git", "--version")
			command.Dir = root
			if output, err := command.CombinedOutput(); err != nil {
				t.Fatalf("native command failed: %v %s", err, output)
			}
			_, digest, err := loadDoSession(root, session.ID)
			if err != nil {
				t.Fatal(err)
			}
			zero := 0
			_, err = doRecord(root, session, digest, doRecordInput{ExpectedRevision: session.Revision, RequestID: "complete-wrong-action", Events: []doRecordEvent{{AttemptID: "original", TargetID: "other", Kind: kind, Event: "completed", Status: "passed", EvidenceOrigin: "agent_tool_observation", ToolCallID: "native-original", Argv: []string{"git", "--version"}, Cwd: ".", StartedAt: started, FinishedAt: doNow(), ExitCode: &zero}}})
			if err == nil {
				t.Fatal("completion was accepted under a different action's contract")
			}
			current, after, err := loadDoSession(root, session.ID)
			if err != nil || after != digest || len(current.Attempts) != 1 || current.Attempts[0].Status != "running" {
				t.Fatalf("rejected completion consumed the original checkpoint: %v %+v", err, current.Attempts)
			}
		})
	}
}

func TestDoInitialOutputScopeCannotAbsorbMaintainedScripts(t *testing.T) {
	for _, kind := range []string{"step", "check"} {
		t.Run(kind, func(t *testing.T) {
			root, input := doFixture(t)
			if err := os.MkdirAll(filepath.Join(root, "out"), 0o755); err != nil {
				t.Fatal(err)
			}
			if err := os.WriteFile(filepath.Join(root, "out/maintained-script.txt"), []byte("maintained source entrypoint\n"), 0o644); err != nil {
				t.Fatal(err)
			}
			if kind == "step" {
				input.Definition.Steps[0].ScriptRef = "out/maintained-script.txt"
			} else {
				input.Definition.Checks[0].ScriptRef = "out/maintained-script.txt"
				input.Definition.Checks[0].Argv = []string{"git", "--version"}
			}
			if _, err := doStart(root, input); err == nil {
				t.Fatal("initial output scope absorbed a maintained source script")
			}
			if _, err := os.Stat(filepath.Join(root, filepath.FromSlash(doSessionRef(input.SessionID)))); !os.IsNotExist(err) {
				t.Fatalf("invalid scope published a session: %v", err)
			}
		})
	}
}

func TestDoWindowsOutputScopeCannotAliasMaintainedScriptCase(t *testing.T) {
	if runtime.GOOS != "windows" {
		t.Skip("this alias requires the native Windows case-insensitive filesystem")
	}
	root, input := doFixture(t)
	if err := os.MkdirAll(filepath.Join(root, "out"), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(root, "out/maintained-script.txt"), []byte("maintained source entrypoint\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	input.Definition.Steps[0].ScriptRef = "out/maintained-script.txt"
	input.Definition.Checks[0].ResultPath = "OUT/report.json"
	input.OutputScope = []string{"OUT"}
	if _, err := doStart(root, input); err == nil {
		t.Fatal("a differently cased Windows output scope absorbed maintained source")
	}
}

func TestDoCompletedNativeObservationRequiresExplicitCwd(t *testing.T) {
	root, session := doStartFixture(t)
	session = doRecordFixture(t, root, session, "start-cwd", doRecordEvent{AttemptID: "run-1", TargetID: "run", Kind: "step", Event: "started"})
	started := doNow()
	command := exec.Command("git", "--version")
	command.Dir = root
	if output, err := command.CombinedOutput(); err != nil {
		t.Fatalf("native command failed: %v %s", err, output)
	}
	_, digest, err := loadDoSession(root, session.ID)
	if err != nil {
		t.Fatal(err)
	}
	zero := 0
	_, err = doRecord(root, session, digest, doRecordInput{ExpectedRevision: session.Revision, RequestID: "complete-without-cwd", Events: []doRecordEvent{{AttemptID: "run-1", TargetID: "run", Kind: "step", Event: "completed", Status: "passed", EvidenceOrigin: "agent_tool_observation", ToolCallID: "native-no-cwd", Argv: []string{"git", "--version"}, StartedAt: started, FinishedAt: doNow(), ExitCode: &zero}}})
	if err == nil {
		t.Fatal("missing observed cwd was fabricated as the project root")
	}
	current, after, err := loadDoSession(root, session.ID)
	if err != nil || after != digest || current.Attempts[0].Status != "running" {
		t.Fatalf("rejected observation changed the checkpoint: %v %+v", err, current.Attempts)
	}
}

func TestDoOptionalRecoveryEvidenceMustRemainBoundAtCloseout(t *testing.T) {
	root, session, recovery := doOptionalTimeoutFixture(t, false)
	_, digest, err := loadDoSession(root, session.ID)
	if err != nil {
		t.Fatal(err)
	}
	session, err = doResume(root, session, digest, doResumeInput{ExpectedRevision: session.Revision, AttemptID: "optional-timeout", Recovery: recovery})
	if err != nil {
		t.Fatal(err)
	}
	_, digest, err = loadDoSession(root, session.ID)
	if err != nil {
		t.Fatal(err)
	}
	session, err = doFinish(root, session, digest, doFinishInput{ExpectedRevision: session.Revision, KnowledgeStatus: "pending"})
	if err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(root, recovery.EvidenceRef), []byte("replaced inspection evidence\n"), 0o600); err != nil {
		t.Fatal(err)
	}
	validation := doValidate(root, session, true)
	if validation.Status == "passed" || !strings.Contains(strings.Join(validation.Blockers, " "), "optional-timeout") {
		t.Fatalf("changed recovery evidence cleared an optional interruption: %+v", validation)
	}
	_, digest, err = loadDoSession(root, session.ID)
	if err != nil {
		t.Fatal(err)
	}
	if _, err := doFinish(root, session, digest, doFinishInput{ExpectedRevision: session.Revision, KnowledgeStatus: "pending"}); err == nil {
		t.Fatal("completion replay ignored changed recovery evidence")
	}
	if _, err := updatePlaybook(root, PlaybookUpdateRequest{Definition: session.Definition, SessionID: session.ID, ChangeSummary: "Preserve the method after current recovery validation"}); err == nil {
		t.Fatal("method publication ignored changed recovery evidence")
	}
}

func TestDoEarlierEpochRecoveryEvidenceMustRemainBound(t *testing.T) {
	root, session, resume := doReadonlyFailureFixture(t)
	resume = doReadonlyAddReplan(t, session, resume)
	session = doReadonlyResumePublic(t, root, session, resume)
	session, _ = doReadonlyRunNative(t, root, session, "step", "run", "repaired-git", true)
	session, _ = doReadonlyRunNative(t, root, session, "check", "exit", "fresh-check", true)
	if validation := doValidate(root, session, true); validation.Status != "passed" {
		t.Fatal(validation)
	}
	ref := session.Attempts[0].Recovery.EvidenceRef
	if err := os.Remove(filepath.Join(root, filepath.FromSlash(ref))); err != nil {
		t.Fatal(err)
	}
	validation := doValidate(root, session, true)
	if validation.Status == "passed" || !strings.Contains(strings.Join(validation.Blockers, " "), "failed-git") {
		t.Fatalf("missing prior-epoch recovery evidence was ignored: %+v", validation)
	}
}

func TestDoPassedExecutionCannotBeReopenedByOldAttemptRecovery(t *testing.T) {
	root, session, recovery := doReadonlyFailureFixture(t)
	replan := doReadonlyAddReplan(t, session, recovery)
	session = doReadonlyResumePublic(t, root, session, replan)
	session, _ = doReadonlyRunNative(t, root, session, "step", "run", "repaired-git", true)
	session, _ = doReadonlyRunNative(t, root, session, "check", "exit", "fresh-check", true)
	_, digest, err := loadDoSession(root, session.ID)
	if err != nil {
		t.Fatal(err)
	}
	session, err = doFinish(root, session, digest, doFinishInput{ExpectedRevision: session.Revision, KnowledgeStatus: "pending"})
	if err != nil {
		t.Fatal(err)
	}
	// Exact replan replay is an existing immutable receipt, even after finish.
	session = doReadonlyResumePublic(t, root, session, replan)
	_, digest, err = loadDoSession(root, session.ID)
	if err != nil {
		t.Fatal(err)
	}
	recovery.ExpectedRevision = session.Revision
	recovery.Recovery.Reason = "fresh inspection while repairing knowledge persistence"
	recovery.Recovery.EvidenceText += "The completed operation remains passed.\n"
	if _, err := doResume(root, session, digest, recovery); err == nil {
		t.Fatal("old failed-attempt recovery reopened a passed operation for native reruns")
	}
	current, after, err := loadDoSession(root, session.ID)
	if err != nil || after != digest || current.ExecutionOutcome != "passed" || current.KnowledgeStatus != "pending" {
		t.Fatalf("rejected recovery changed finished execution: %v %+v", err, current)
	}
}

func TestDoProtectedPathsRejectCaseAliasesAndNestedGit(t *testing.T) {
	root, input := doFixture(t)
	for _, relative := range []string{".GIT/config", "vendor/.git/config", "vendor/.GiT/config"} {
		if _, err := doPath(root, relative, false); err == nil {
			t.Errorf("Do path accepted protected Git alias %s", relative)
		}
	}
	for _, relative := range []string{".SPECIFY/Do", ".PLANNING/e2e"} {
		input.OutputScope = []string{"out", relative}
		if _, err := doStart(root, input); err == nil {
			t.Errorf("Do start accepted runtime-state output alias %s", relative)
		}
		if _, err := doReplanScope(root, nil, []string{relative}); err == nil {
			t.Errorf("Do replan accepted runtime-state output alias %s", relative)
		}
	}
}

func TestDoJUnitCannotCountDisabledOrNonexecutedCasesAsPassing(t *testing.T) {
	for name, report := range map[string]string{
		"disabled-suite": `<testsuite tests="1" disabled="1"><testcase name="disabled"/></testsuite>`,
		"notrun":         `<testsuite tests="1"><testcase name="disabled" status="notrun" result="suppressed"/></testsuite>`,
		"suppressed":     `<testsuite tests="1"><testcase name="disabled" result="suppressed"/></testsuite>`,
		"skipped-result": `<testsuite tests="1"><testcase name="skipped" status="run" result="skipped"/></testsuite>`,
		"failed-status":  `<testsuite tests="1"><testcase name="failed" status="failed"/></testsuite>`,
	} {
		t.Run(name, func(t *testing.T) {
			if err := doAuditJUnit([]byte(report), 1); err == nil {
				t.Fatal("nonpassing or nonexecuted case satisfied the frozen executed denominator")
			}
		})
	}
	// GoogleTest may explicitly execute disabled-named tests using its opt-in
	// flag. The case's actual run/completed result, rather than its name, proves
	// execution. Standard JUnit does not require these optional case attributes.
	for _, report := range []string{
		`<testsuite tests="1" disabled="0"><testcase name="normal" status="run" result="completed"/></testsuite>`,
		`<testsuite tests="1" disabled="1"><testcase name="disabled-but-executed" status="run" result="completed"/></testsuite>`,
		`<testsuite tests="1"><testcase name="normal"/></testsuite>`,
	} {
		if err := doAuditJUnit([]byte(report), 1); err != nil {
			t.Fatalf("genuinely passing report was refused: %v", err)
		}
	}
}

func TestDoJUnitDeclaredCountersMustMatchActualCases(t *testing.T) {
	for name, report := range map[string]string{
		"omitted-disabled-case": `<testsuite tests="2" disabled="1"><testcase status="run" result="completed"/></testsuite>`,
		"too-few":               `<testsuite tests="2"><testcase/></testsuite>`,
		"too-many":              `<testsuite tests="0"><testcase/></testsuite>`,
		"invalid-counter":       `<testsuite tests="unknown"><testcase/></testsuite>`,
		"negative-counter":      `<testsuite tests="-1"><testcase/></testsuite>`,
		"nested-leaf":           `<testsuites tests="1"><testsuite tests="2"><testcase/></testsuite></testsuites>`,
		"nested-aggregate":      `<testsuites tests="3"><testsuite tests="1"><testcase/></testsuite><testsuite tests="1"><testcase/></testsuite></testsuites>`,
	} {
		t.Run(name, func(t *testing.T) {
			if err := doAuditJUnit([]byte(report), 1); err == nil {
				t.Fatal("inconsistent declared denominator hid missing execution cases")
			}
		})
	}
	for _, report := range []string{
		`<testsuites tests="2"><testsuite tests="1"><testcase/></testsuite><testsuite tests="1"><testcase/></testsuite></testsuites>`,
		`<testsuites tests="2"><testsuite tests="2"><testsuite tests="1"><testcase/></testsuite><testsuite tests="1"><testcase/></testsuite></testsuite></testsuites>`,
		`<testsuites><testsuite><testcase/><testcase/></testsuite></testsuites>`,
	} {
		if err := doAuditJUnit([]byte(report), 2); err != nil {
			t.Fatalf("complete nested or counter-free report was refused: %v", err)
		}
	}
}

func TestDoPublicStartReplayCannotHideWorkFromAnotherAdapter(t *testing.T) {
	for _, changed := range []string{"adapter", "agent"} {
		t.Run(changed, func(t *testing.T) {
			root, input := doFixture(t)
			input.AdapterID = "claude"
			input.Definition = playbookNormalizeDefinition(input.Definition)
			raw, err := json.Marshal(input)
			if err != nil {
				t.Fatal(err)
			}
			var output bytes.Buffer
			if code := runDo([]string{"start", "--project-root", root, "--input-json", string(raw), "--format", "json"}, &output); code != 0 {
				t.Fatal(output.String())
			}
			session, digest, err := loadDoSession(root, input.SessionID)
			if err != nil {
				t.Fatal(err)
			}
			if changed == "adapter" {
				input.AdapterID = "gemini"
			} else {
				input.AgentID = "another-agent"
			}
			raw, err = json.Marshal(input)
			if err != nil {
				t.Fatal(err)
			}
			output.Reset()
			code := runDo([]string{"start", "--project-root", root, "--input-json", string(raw), "--format", "json"}, &output)
			var lookup bytes.Buffer
			if showCode := runDo([]string{"show", "--active", "--adapter-id", input.AdapterID, "--project-root", root, "--format", "json"}, &lookup); showCode != 0 {
				t.Fatal(lookup.String())
			}
			if code == 0 {
				t.Fatalf("different %s replay returned an existing owner's session; actual adapter lookup=%s", changed, lookup.String())
			}
			if _, after, err := loadDoSession(root, session.ID); err != nil || after != digest {
				t.Fatalf("caller refusal changed the session: %v", err)
			}
			var ownerLookup bytes.Buffer
			if showCode := runDo([]string{"show", "--active", "--adapter-id", "claude", "--project-root", root, "--format", "json"}, &ownerLookup); showCode != 0 || !bytes.Contains(ownerLookup.Bytes(), []byte(`"session_id":"`+session.ID+`"`)) {
				t.Fatalf("original owner lost active routing: %d %s", showCode, ownerLookup.String())
			}
		})
	}
}

func TestDoPublicSameCallerStartReplayRetainsTerminalCompletion(t *testing.T) {
	root, input := doFixture(t)
	input.Definition = playbookNormalizeDefinition(input.Definition)
	session, err := doStart(root, input)
	if err != nil {
		t.Fatal(err)
	}
	session = doRunFixture(t, root, session)
	_, digest, err := loadDoSession(root, session.ID)
	if err != nil {
		t.Fatal(err)
	}
	session, err = doFinish(root, session, digest, doFinishInput{ExpectedRevision: session.Revision, KnowledgeStatus: "not_applicable"})
	if err != nil {
		t.Fatal(err)
	}
	_, digest, err = loadDoSession(root, session.ID)
	if err != nil {
		t.Fatal(err)
	}
	// Work already canonicalizes these identity strings when it is created.
	input.AgentID = " " + input.AgentID + " "
	input.AdapterID = " " + input.AdapterID + " "
	raw, err := json.Marshal(input)
	if err != nil {
		t.Fatal(err)
	}
	var output bytes.Buffer
	if code := runDo([]string{"start", "--project-root", root, "--input-json", string(raw), "--format", "json"}, &output); code != 0 || !bytes.Contains(output.Bytes(), []byte(`"terminal":true`)) {
		t.Fatalf("same canonical caller could not replay completed creation: %d %s", code, output.String())
	}
	if _, after, err := loadDoSession(root, session.ID); err != nil || after != digest {
		t.Fatalf("terminal creation replay changed the checkpoint: %v", err)
	}
}
