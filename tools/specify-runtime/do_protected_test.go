package main

import (
	"bytes"
	"encoding/json"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"testing"
)

const doProtectedTestEnvironment = "SPECIFY_DO_TEST_OFFICIAL_CONFIG"
const doProtectedTestContent = "fixture-private-config-do-not-persist"

func doProtectedFixture(t *testing.T) (string, string, doStartInput) {
	t.Helper()
	root, input := doCommandFixture(t)
	file := filepath.Join(t.TempDir(), "private-config-fixture.h")
	if err := os.WriteFile(file, []byte(doProtectedTestContent), 0o600); err != nil {
		t.Fatal(err)
	}
	t.Setenv(doProtectedTestEnvironment, file)
	input.Command.ExternalInputs = map[string]PlaybookExternalInput{"official_config": {Environment: doProtectedTestEnvironment}}
	input.Command.Argv = append(input.Command.Argv, "-Config", "{{external:official_config}}")
	return root, file, input
}

func doProtectedNoLeak(t *testing.T, file string, value any) {
	t.Helper()
	raw, err := json.Marshal(value)
	if err != nil {
		t.Fatal(err)
	}
	for _, needle := range []string{file, strings.ReplaceAll(file, `\`, "/"), filepath.Base(file), doProtectedTestContent} {
		encoded, _ := json.Marshal(needle)
		if bytes.Contains(raw, encoded[1:len(encoded)-1]) {
			t.Fatal("protected value escaped into persisted or returned data")
		}
	}
}

func TestDoProtectedMissingBindingHasActionableReadOnlyDiagnostic(t *testing.T) {
	root, file, input := doProtectedFixture(t)
	t.Setenv(doProtectedTestEnvironment, "")
	before := doFastTree(t, root)
	raw, _ := json.Marshal(input)
	var request map[string]any
	_ = json.Unmarshal(raw, &request)
	delete(request, "definition") // Compact API input omits the unused definition.
	raw, _ = json.Marshal(request)
	var output bytes.Buffer
	if runDo([]string{"prepare", "--input-json", string(raw), "--project-root", root, "--format", "json"}, &output) == 0 {
		t.Fatal("missing binding passed")
	}
	var envelope Envelope
	if err := json.Unmarshal(output.Bytes(), &envelope); err != nil {
		t.Fatal(err)
	}
	issues := envelope.Data["validation_errors"].([]any)
	if len(envelope.ShowArgv) != 0 || len(issues) != 1 || issues[0].(map[string]any)["instance_path"] != "/command/external_inputs/official_config/environment" || !strings.Contains(issues[0].(map[string]any)["message"].(string), doProtectedTestEnvironment) {
		t.Fatal("missing binding diagnostic is not actionable")
	}
	doProtectedNoLeak(t, file, envelope)
	doPrepareValidationUnchanged(t, root, before)
}

func TestDoProtectedNativeExecutionPersistsOnlySymbolicEvidence(t *testing.T) {
	python, err := exec.LookPath("python")
	if err != nil {
		t.Skip("Python native process helper unavailable")
	}
	root, file, input := doProtectedFixture(t)
	script := "import pathlib,sys\np=pathlib.Path(sys.argv[1])\ndata=p.read_bytes()\nassert data\nprint(str(p)); print(data.decode()); print(data.decode(),file=sys.stderr)\npathlib.Path('out').mkdir(exist_ok=True)\npathlib.Path('out/installer.exe').write_bytes(b'built')\n"
	if err := os.WriteFile(filepath.Join(root, "operation.py"), []byte(script), 0o600); err != nil {
		t.Fatal(err)
	}
	input.Command.Argv = []string{"python", "operation.py", "{{external:official_config}}"}
	prepared, err := doPrepare(root, input)
	if err != nil {
		t.Fatal(err)
	}
	doProtectedNoLeak(t, file, prepared)
	canonical := prepared["start_input"].(doStartInput)
	canonical.Definition.SourceFiles = []string{"source.txt"} // Actual scripts must still be source-bound automatically.
	session, err := doStart(root, canonical)
	if err != nil {
		t.Fatal(err)
	}
	next, err := doNext(root, session)
	if err != nil {
		t.Fatal(err)
	}
	ready := next["ready"].([]map[string]any)[0]
	start := ready["started_input"].(doRecordInput)
	session = doRecordFixture(t, root, session, start.RequestID, start.Events...)
	next, err = doNext(root, session)
	if err != nil {
		t.Fatal(err)
	}
	running := next["running"].([]map[string]any)[0]
	packet := running["protected_execution"].(map[string]any)
	if packet["source_files"].(map[string]string)["operation.py"] == "" {
		t.Fatal("actual script is absent from protected prelaunch hashes")
	}
	doProtectedNoLeak(t, file, packet)
	helper, err := filepath.Abs(filepath.Join("..", "..", "scripts", "shared", "do_protected_process.py"))
	if err != nil {
		t.Fatal(err)
	}
	command := exec.Command(python, helper, "--input-json", "-")
	command.Dir = root
	raw, _ := json.Marshal(packet)
	command.Stdin = bytes.NewReader(raw)
	started := doNow()
	output, err := command.CombinedOutput()
	finished := doNow()
	if err != nil {
		t.Fatalf("native helper failed: %v", err)
	}
	var receipt struct {
		Outcome  string `json:"outcome"`
		ExitCode int    `json:"exit_code"`
	}
	if json.Unmarshal(output, &receipt) != nil || receipt.Outcome != "passed" || receipt.ExitCode != 0 {
		t.Fatal("no passing safe helper receipt")
	}
	doProtectedNoLeak(t, file, string(output))
	event := running["completion_event"].(doRecordEvent)
	event.Status, event.ToolCallID, event.StartedAt, event.FinishedAt, event.ExitCode = "passed", "native-protected-build", started, finished, &receipt.ExitCode
	session = doRecordFixture(t, root, session, "complete-protected-build", event)
	session = doRecordFixture(t, root, session, "start-protected-check", doRecordEvent{AttemptID: "check-1", TargetID: "check-1", Kind: "check", Event: "started"})
	now := doNow()
	session = doRecordFixture(t, root, session, "complete-protected-check", doRecordEvent{AttemptID: "check-1", TargetID: "check-1", Kind: "check", Event: "completed", Status: "passed", EvidenceOrigin: "agent_tool_observation", ToolCallID: "native-file-check", Cwd: ".", Argv: []string{}, StartedAt: now, FinishedAt: now, ResultRefs: []DoResultRef{{Path: "out/installer.exe", Kind: "file"}}})
	session, err = doComplete(root, session.ID, doCompleteInput{ExpectedRevision: session.Revision, ChangeSummary: "Verified package script with protected configuration binding"})
	if err != nil {
		t.Fatal(err)
	}
	if session.KnowledgeStatus != "saved" {
		t.Fatal("verified symbolic method was not retained")
	}
	doProtectedNoLeak(t, file, session)
	if err := filepath.WalkDir(root, func(name string, entry os.DirEntry, walkErr error) error {
		if walkErr != nil {
			return walkErr
		}
		if entry.IsDir() {
			return nil
		}
		raw, err := os.ReadFile(name)
		if err != nil {
			return err
		}
		doProtectedNoLeak(t, file, string(raw))
		return nil
	}); err != nil {
		t.Fatal(err)
	}
	if raw, err := os.ReadFile(file); err != nil || string(raw) != doProtectedTestContent {
		t.Fatal("external configuration changed")
	}
}

func TestDoProtectedSourceWriterCannotMaskExternalDriftOrPersistLogs(t *testing.T) {
	root, file, input := doProtectedFixture(t)
	input.Command.SourceWrites, input.WriteScope = []string{"source.txt"}, []string{"source.txt"}
	prepared, err := doPrepare(root, input)
	if err != nil {
		t.Fatal(err)
	}
	session, err := doStart(root, prepared["start_input"].(doStartInput))
	if err != nil {
		t.Fatal(err)
	}
	session = doRecordFixture(t, root, session, "begin-protected-write", doRecordEvent{AttemptID: "run-1", TargetID: "run", Kind: "step", Event: "started"})
	current, digest, err := loadDoSession(root, session.ID)
	if err != nil {
		t.Fatal(err)
	}
	zero, now := 0, doNow()
	event := doRecordEvent{AttemptID: "run-1", TargetID: "run", Kind: "step", Event: "completed", Status: "passed", EvidenceOrigin: "agent_tool_observation", ToolCallID: "native-protected-write", Argv: session.Definition.Steps[0].Argv, Cwd: ".", StartedAt: now, FinishedAt: now, ExitCode: &zero}
	for _, mode := range []string{"summary", "log", "expanded-argv", "metadata"} {
		candidate := event
		switch mode {
		case "summary":
			candidate.Summary = file
		case "log":
			candidate.ResultRefs = []DoResultRef{{Path: "out/build.log", Kind: "log"}}
		case "expanded-argv":
			candidate.Argv = append([]string{}, event.Argv...)
			candidate.Argv[len(candidate.Argv)-1] = file
		case "metadata":
			candidate.ToolCallID = file
		}
		if _, err := doRecord(root, current, digest, doRecordInput{ExpectedRevision: current.Revision, RequestID: mode, Events: []doRecordEvent{candidate}}); err == nil {
			t.Fatal("unsafe observation was accepted")
		} else {
			doProtectedNoLeak(t, file, err.Error())
		}
	}
	if err := os.WriteFile(filepath.Join(root, "source.txt"), []byte("source v2\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(file, []byte("different-protected-configuration"), 0o600); err != nil {
		t.Fatal(err)
	}
	if _, err := doRecord(root, current, digest, doRecordInput{ExpectedRevision: current.Revision, RequestID: "external-drift", Events: []doRecordEvent{event}}); err == nil || !strings.Contains(err.Error(), "protected_input_changed_during_attempt") {
		t.Fatal("source write permission masked external drift")
	}
	if err := os.WriteFile(file, []byte(doProtectedTestContent), 0o600); err != nil {
		t.Fatal(err)
	}
	session = doRecordFixture(t, root, current, "unchanged-protected-config", event)
	if err := doValidateMutationLineage(session, session.Attempts[0], doLatestAttempts(session), doAttemptResultFingerprint(session.Attempts[0])); err != nil {
		t.Fatal(err)
	}
	for _, value := range []any{file, doProtectedTestContent} {
		if err := doProtectedPrivatePayload(session.Definition, value); err == nil {
			t.Fatal("pasted private metadata accepted")
		}
	}
}
