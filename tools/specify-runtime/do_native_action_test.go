package main

import (
	"bytes"
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"
)

func doNativeFixture(t *testing.T, kind string) (string, DoSession) {
	t.Helper()
	root, input := doFixture(t)
	target := "resource:fixture"
	if kind == "file" {
		target = "out/native.json"
	}
	input.Definition.Steps = []PlaybookStep{{ID: "run", Purpose: "test adapter writes a value", Required: true, ExpectedResult: "value written", SideEffect: "local_write", NativeAction: &PlaybookNativeAction{Kind: kind, Tool: "test.adapter.write", Target: target, Arguments: json.RawMessage(`{"value":1}`)}}}
	input.Definition.Checks = []PlaybookCheck{{ID: "inspect", Purpose: "independently read the actual value", DependsOn: []string{"run"}, Required: true, ExpectedResult: "value is one", Kind: "observation", JSONPointer: "/value", ExpectedJSON: json.RawMessage(`1`), NativeAction: &PlaybookNativeAction{Kind: kind, Tool: "test.adapter.read", Target: target, Arguments: json.RawMessage(`{}`)}}}
	session, err := doStart(root, input)
	if err != nil {
		t.Fatal(err)
	}
	return root, session
}

func doNativeEvent(session DoSession, target, kind, attempt, call, status, outcome, result string) doRecordEvent {
	action, _ := doFindAction(session, kind, target)
	return doRecordEvent{AttemptID: attempt, TargetID: target, Kind: kind, Event: "completed", Status: status, EvidenceOrigin: "agent_tool_observation", ToolCallID: call, StartedAt: doNow(), FinishedAt: doNow(), NativeAction: normalizePlaybookNativeAction(action.nativeAction), NativeObservation: &DoNativeObservation{Outcome: outcome, Result: json.RawMessage(result)}}
}

func doNativeRunProducer(t *testing.T, root string, session DoSession) DoSession {
	t.Helper()
	session = doRecordFixture(t, root, session, "start-native", doRecordEvent{AttemptID: "native-run", TargetID: "run", Kind: "step", Event: "started"})
	started := doNow()
	if err := os.MkdirAll(filepath.Join(root, "out"), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(root, "out", "native.json"), []byte(`{"value":1}`), 0o644); err != nil {
		t.Fatal(err)
	}
	event := doNativeEvent(session, "run", "step", "native-run", "actual-test-write", "passed", "succeeded", `{"written":true}`)
	event.StartedAt = started
	return doRecordFixture(t, root, session, "complete-native", event)
}

func doNativeRunCheck(t *testing.T, root string, session DoSession) DoSession {
	t.Helper()
	session = doRecordFixture(t, root, session, "start-inspect", doRecordEvent{AttemptID: "native-inspect", TargetID: "inspect", Kind: "check", Event: "started"})
	started := doNow()
	raw, err := os.ReadFile(filepath.Join(root, "out", "native.json"))
	if err != nil {
		t.Fatal(err)
	}
	event := doNativeEvent(session, "inspect", "check", "native-inspect", "actual-test-read", "passed", "succeeded", string(raw))
	event.StartedAt = started
	return doRecordFixture(t, root, session, "complete-inspect", event)
}

// The test adapter performs actual local file IO. Kind values exercise protocol
// binding only; these tests do not claim to operate a real browser or connector.
func TestDoNativeKindsKeepIndependentAsOfEffectEvidence(t *testing.T) {
	for _, kind := range []string{"file", "browser", "desktop", "connector"} {
		t.Run(kind, func(t *testing.T) {
			root, session := doNativeFixture(t, kind)
			session = doNativeRunProducer(t, root, session)
			if doValidate(root, session, false).Status == "passed" {
				t.Fatal("producer response replaced independent effect check")
			}
			session = doNativeRunCheck(t, root, session)
			if validation := doValidate(root, session, false); validation.Status != "passed" {
				t.Fatal(validation)
			}
			attempt := session.Attempts[1]
			observation, err := doReadNativeObservation(root, session, attempt)
			if err != nil || string(observation.Result) != `{"value":1}` || attempt.ExitCode != nil || len(attempt.Argv) != 0 || attempt.Cwd != "" {
				t.Fatalf("invalid nonprocess observation: %+v %v", attempt, err)
			}
			var snapshot doNativeSnapshot
			raw, _ := os.ReadFile(filepath.Join(root, filepath.FromSlash(attempt.NativeObservationRef)))
			if err := json.Unmarshal(raw, &snapshot); err != nil || snapshot.VerifiedAsOf != attempt.FinishedAt {
				t.Fatalf("missing as-of observation: %s %v", raw, err)
			}
		})
	}
}

func TestDoNativeObservationRejectsIdentityAndFabricatedProcessFields(t *testing.T) {
	root, session := doNativeFixture(t, "connector")
	session = doRecordFixture(t, root, session, "start-native", doRecordEvent{AttemptID: "native-run", TargetID: "run", Kind: "step", Event: "started"})
	for _, test := range []struct {
		name string
		edit func(*doRecordEvent)
	}{
		{"target", func(event *doRecordEvent) { event.NativeAction.Target = "another-resource" }},
		{"tool", func(event *doRecordEvent) { event.NativeAction.Tool = "another-tool" }},
		{"kind", func(event *doRecordEvent) { event.NativeAction.Kind = "desktop" }},
		{"arguments", func(event *doRecordEvent) { event.NativeAction.Arguments = json.RawMessage(`{"value":2}`) }},
		{"exit", func(event *doRecordEvent) { zero := 0; event.ExitCode = &zero }},
		{"cwd", func(event *doRecordEvent) { event.Cwd = "." }},
		{"argv", func(event *doRecordEvent) { event.Argv = []string{"fake"} }},
		{"unknown-pass", func(event *doRecordEvent) { event.NativeObservation.Outcome = "unknown" }},
		{"failed-pass", func(event *doRecordEvent) { event.NativeObservation.Outcome = "failed" }},
		{"missing-result", func(event *doRecordEvent) { event.NativeObservation.Result = nil }},
		{"duplicate-result", func(event *doRecordEvent) { event.NativeObservation.Result = json.RawMessage(`{"ok":false,"ok":true}`) }},
		{"sensitive-result", func(event *doRecordEvent) {
			event.NativeObservation.Result = json.RawMessage(`{"token":"real-credential-value"}`)
		}},
		{"successful-failure", func(event *doRecordEvent) { event.Status = "failed" }},
	} {
		t.Run(test.name, func(t *testing.T) {
			event := doNativeEvent(session, "run", "step", "native-run", "native-call", "passed", "succeeded", `{"ok":true}`)
			test.edit(&event)
			current, digest, err := loadDoSession(root, session.ID)
			if err != nil {
				t.Fatal(err)
			}
			if _, err := doRecord(root, current, digest, doRecordInput{ExpectedRevision: current.Revision, RequestID: "reject-" + test.name, Events: []doRecordEvent{event}}); err == nil {
				t.Fatal("accepted mismatched or fabricated observation")
			}
			if _, err := os.Stat(filepath.Join(root, filepath.FromSlash(doNativeObservationRef(session, "native-run")))); !os.IsNotExist(err) {
				t.Fatal("rejected record wrote a snapshot")
			}
		})
	}
}

func TestDoNativeEffectCheckRejectsReuseEarlyReadAndWrongValue(t *testing.T) {
	root, session := doNativeFixture(t, "browser")
	session = doNativeRunProducer(t, root, session)
	session = doRecordFixture(t, root, session, "start-inspect", doRecordEvent{AttemptID: "native-inspect", TargetID: "inspect", Kind: "check", Event: "started"})
	for _, test := range []struct {
		name string
		edit func(*doRecordEvent)
	}{
		{"same-call", func(event *doRecordEvent) { event.ToolCallID = session.Attempts[0].ToolCallID }},
		{"early-read", func(event *doRecordEvent) {
			ended, _ := time.Parse(time.RFC3339Nano, session.Attempts[0].FinishedAt)
			event.StartedAt = ended.Add(-time.Millisecond).Format(time.RFC3339Nano)
		}},
		{"wrong-value", func(event *doRecordEvent) { event.NativeObservation.Result = json.RawMessage(`{"value":2}`) }},
	} {
		t.Run(test.name, func(t *testing.T) {
			event := doNativeEvent(session, "inspect", "check", "native-inspect", "actual-test-read", "passed", "succeeded", `{"value":1}`)
			test.edit(&event)
			current, digest, err := loadDoSession(root, session.ID)
			if err != nil {
				t.Fatal(err)
			}
			if _, err := doRecord(root, current, digest, doRecordInput{ExpectedRevision: current.Revision, RequestID: "reject-" + test.name, Events: []doRecordEvent{event}}); err == nil {
				t.Fatal("accepted invalid independent effect check")
			}
		})
	}
}

func TestDoNativeSnapshotTamperingAndProducerRetryInvalidateAcceptance(t *testing.T) {
	root, session := doNativeFixture(t, "desktop")
	session = doNativeRunCheck(t, root, doNativeRunProducer(t, root, session))
	ref := filepath.Join(root, filepath.FromSlash(session.Attempts[1].NativeObservationRef))
	original, err := os.ReadFile(ref)
	if err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(ref, []byte(`{"tampered":true}`), 0o600); err != nil {
		t.Fatal(err)
	}
	if doValidate(root, session, false).Status == "passed" {
		t.Fatal("accepted tampered native snapshot")
	}
	if err := os.WriteFile(ref, original, 0o600); err != nil {
		t.Fatal(err)
	}
	session = doRecordFixture(t, root, session, "retry-producer", doRecordEvent{AttemptID: "native-run-2", TargetID: "run", Kind: "step", Event: "started"})
	event := doNativeEvent(session, "run", "step", "native-run-2", "actual-test-write-2", "passed", "succeeded", `{"written":true}`)
	session = doRecordFixture(t, root, session, "retry-completed", event)
	if doValidate(root, session, false).Status == "passed" {
		t.Fatal("producer rerun retained obsolete effect check")
	}
}

func TestDoNativeFailureAndInterruptionUseTypedRecovery(t *testing.T) {
	for _, outcome := range []string{"failed", "unknown"} {
		t.Run(outcome, func(t *testing.T) {
			root, session := doNativeFixture(t, "connector")
			session = doRecordFixture(t, root, session, "start-native", doRecordEvent{AttemptID: "native-run", TargetID: "run", Kind: "step", Event: "started"})
			status := "failed"
			if outcome == "unknown" {
				status = "interrupted"
			}
			session = doRecordFixture(t, root, session, "complete-native", doNativeEvent(session, "run", "step", "native-run", "native-actual-failure", status, outcome, `{"error":"adapter operation unavailable"}`))
			if outcome == "failed" {
				if err := doVerifyNativeFailure(root, session, session.Attempts[0]); err != nil {
					t.Fatal(err)
				}
			}
			input := doResumeInput{ExpectedRevision: session.Revision, AttemptID: "native-run", Recovery: DoRecovery{Reason: "Actual native operation and effects inspected", EvidenceText: "The test adapter operation ended and its resource state was read independently.", SideEffectsInspected: true}}
			if _, _, err := doPrepareRecovery(root, session, input); err == nil {
				t.Fatal("native recovery omitted settlement")
			}
			input.Recovery.NativeActionSettled = true
			recovery, updates, err := doPrepareRecovery(root, session, input)
			if err != nil || len(updates) != 1 || recovery.ProcessesStopped {
				t.Fatalf("native recovery invented process verification: %+v %v", recovery, err)
			}
			if err := doRecoveryMatchesAttempt(DoAttempt{}, recovery); err == nil {
				t.Fatal("native settlement bypassed process recovery")
			}
			current, digest, err := loadDoSession(root, session.ID)
			if err != nil {
				t.Fatal(err)
			}
			recovered, err := doResume(root, current, digest, input)
			if err != nil || recovered.Attempts[0].Recovery == nil {
				t.Fatalf("native recovery did not persist: %+v %v", recovered, err)
			}
			if err := doVerifyRecoveryEvidence(root, *recovered.Attempts[0].Recovery); err != nil {
				t.Fatal(err)
			}
		})
	}
}

func TestDoNativeFileObservationKeepsCurrentTypedReportVerification(t *testing.T) {
	root, input := doFixture(t)
	input.Definition.Steps[0] = PlaybookStep{ID: "run", Purpose: "write report with native file tool", Required: true, ExpectedResult: "report exists", SideEffect: "local_write", NativeAction: &PlaybookNativeAction{Kind: "file", Tool: "test.adapter.write", Target: "out/native.json", Arguments: json.RawMessage(`{"value":1}`)}}
	input.Definition.Checks[0].NativeAction = &PlaybookNativeAction{Kind: "file", Tool: "test.adapter.read", Target: "out/native.json", Arguments: json.RawMessage(`{}`)}
	input.Definition.Checks[0].Cwd = ""
	input.Definition.Checks[0].ResultPath = "out/native.json"
	input.Definition.Checks[0].JSONPointer = "/value"
	input.Definition.Checks[0].ExpectedJSON = json.RawMessage(`1`)
	session, err := doStart(root, input)
	if err != nil {
		t.Fatal(err)
	}
	session = doNativeRunProducer(t, root, session)
	session = doRecordFixture(t, root, session, "start-report", doRecordEvent{AttemptID: "native-report", TargetID: "report", Kind: "check", Event: "started"})
	event := doNativeEvent(session, "report", "check", "native-report", "test-file-read", "passed", "succeeded", `null`)
	event.ResultRefs = []DoResultRef{{Path: "out/native.json", Kind: "json"}}
	session = doRecordFixture(t, root, session, "complete-report", event)
	if validation := doValidate(root, session, false); validation.Status != "passed" {
		t.Fatal(validation)
	}
	if err := os.WriteFile(filepath.Join(root, "out/native.json"), []byte(`{"value":2}`), 0o644); err != nil {
		t.Fatal(err)
	}
	if validation := doValidate(root, session, false); validation.Status == "passed" {
		t.Fatal("native observation displaced current file rehash")
	}
}

func TestDoNativeSourceWriteCannotBypassDeclaredScope(t *testing.T) {
	root, session := doNativeFixture(t, "file")
	session = doRecordFixture(t, root, session, "start-native", doRecordEvent{AttemptID: "native-run", TargetID: "run", Kind: "step", Event: "started"})
	if err := os.WriteFile(filepath.Join(root, "source.txt"), []byte("unowned modification"), 0o644); err != nil {
		t.Fatal(err)
	}
	event := doNativeEvent(session, "run", "step", "native-run", "actual-native-write", "passed", "succeeded", `{"written":true}`)
	current, digest, err := loadDoSession(root, session.ID)
	if err != nil {
		t.Fatal(err)
	}
	if _, err := doRecord(root, current, digest, doRecordInput{ExpectedRevision: current.Revision, RequestID: "complete-unowned", Events: []doRecordEvent{event}}); err == nil || !strings.Contains(err.Error(), "source changed") {
		t.Fatalf("native action bypassed source ownership: %v", err)
	}
}

func TestDoNativeArgumentsCanonicalizeAndRejectUnsafeJSON(t *testing.T) {
	root, _ := doFixture(t)
	a := &PlaybookNativeAction{Kind: "connector", Tool: "test.read", Target: "resource:fixture", Arguments: json.RawMessage(`{"second":2,"first":1}`)}
	b := &PlaybookNativeAction{Kind: "connector", Tool: "test.read", Target: "resource:fixture", Arguments: json.RawMessage(`{ "first": 1, "second": 2 }`)}
	if !doNativeActionsEqual(a, b) {
		t.Fatal("JSON object order changed native action identity")
	}
	for _, raw := range []string{`[]`, `{"first":1,"first":2}`, `{"password":"persisted-password"}`, `{"oversized":"` + strings.Repeat("x", doNativeJSONLimit) + `"}`, strings.Repeat(`{"nested":`, 34) + `{}` + strings.Repeat(`}`, 34)} {
		bad := *a
		bad.Arguments = json.RawMessage(raw)
		if err := validatePlaybookNativeAction(root, &bad, nil, "", ""); err == nil {
			t.Fatal("accepted invalid native arguments")
		}
	}
}

func TestDoNativeFailedToolCanReplanThroughPublicCLI(t *testing.T) {
	root, session := doNativeFixture(t, "file")
	session = doRecordFixture(t, root, session, "start-failed", doRecordEvent{AttemptID: "failed-native", TargetID: "run", Kind: "step", Event: "started"})
	started := doNow()
	if err := os.WriteFile(filepath.Join(root, "out/native.json"), []byte(`{"value":1}`), 0o644); err == nil {
		t.Fatal("fixture must observe a real failed file write without its parent directory")
	}
	event := doNativeEvent(session, "run", "step", "failed-native", "actual-failed-file-write", "failed", "failed", `{"error":"parent-directory-missing"}`)
	event.StartedAt = started
	session = doRecordFixture(t, root, session, "complete-failed", event)
	fixed := doReplanCopyDefinition(t, session.Definition)
	fixed.Steps[0].NativeAction.Arguments = json.RawMessage(`{"value":1,"create_parent":true}`)
	input := doResumeInput{ExpectedRevision: session.Revision, AttemptID: "failed-native", Recovery: DoRecovery{Reason: "Inspected failed native file write and its absent parent directory", EvidenceText: "The local write returned an error because its output directory did not exist. No file was created. The file operation has completed and no asynchronous operation remains.", NativeActionSettled: true, SideEffectsInspected: true}, Replan: &doReplanInput{RequestID: "create-output-directory", Definition: fixed}}
	raw, err := json.Marshal(input)
	if err != nil {
		t.Fatal(err)
	}
	var output bytes.Buffer
	if code := runDo([]string{"resume", session.ID, "--project-root", root, "--input-json", string(raw), "--format", "json"}, &output); code != 0 {
		t.Fatalf("native public replan failed: %d %s", code, output.String())
	}
	session, _, err = loadDoSession(root, session.ID)
	if err != nil || session.DefinitionEpoch != 2 || len(session.Attempts) != 1 || session.Attempts[0].Recovery == nil {
		t.Fatalf("native replan lost failure/recovery history: %+v %v", session, err)
	}
	if _, err := doReadNativeObservation(root, session, session.Attempts[0]); err != nil {
		t.Fatal("native replan changed immutable failed observation", err)
	}
	session = doNativeRunCheck(t, root, doNativeRunProducer(t, root, session))
	if validation := doValidate(root, session, false); validation.Status != "passed" {
		t.Fatal(validation)
	}
}

func TestDoNativeMutationRequiresMandatoryDependentEffectCoverage(t *testing.T) {
	root, session := doNativeFixture(t, "connector")
	exitCheck := PlaybookCheck{ID: "unrelated", Purpose: "inspect a local tool version", Cwd: ".", Argv: []string{"git", "--version"}, Required: true, ExpectedResult: "exit zero", Kind: "exit_code"}
	for _, test := range []struct {
		name string
		edit func(*PlaybookDefinition)
	}{
		{"unrelated-exit-only", func(definition *PlaybookDefinition) { definition.Checks = []PlaybookCheck{exitCheck} }},
		{"dependent-exit-only", func(definition *PlaybookDefinition) {
			check := exitCheck
			check.DependsOn = []string{"run"}
			definition.Checks = []PlaybookCheck{check}
		}},
		{"optional-only-effect", func(definition *PlaybookDefinition) {
			definition.Checks[0].Required = false
			definition.Checks = append(definition.Checks, exitCheck)
		}},
		{"unrelated-typed-file", func(definition *PlaybookDefinition) {
			definition.Checks = []PlaybookCheck{{ID: "artifact", Purpose: "read unrelated artifact", Cwd: ".", Required: true, ExpectedResult: "file exists", Kind: "file", ResultPath: "out/another.bin"}}
		}},
		{"optional-mutation-in-required-closure", func(definition *PlaybookDefinition) {
			definition.Steps[0].Required = false
			definition.Steps = append(definition.Steps, PlaybookStep{ID: "consumer", Purpose: "read after mutation", Cwd: ".", Argv: []string{"git", "--version"}, DependsOn: []string{"run"}, Required: true, SideEffect: "read", ExpectedResult: "read completes"})
			definition.Checks = []PlaybookCheck{exitCheck}
		}},
	} {
		t.Run(test.name, func(t *testing.T) {
			definition := doReplanCopyDefinition(t, session.Definition)
			test.edit(&definition)
			if err := validatePlaybookDefinition(root, definition); err == nil || !strings.Contains(err.Error(), "effect check") {
				t.Fatalf("native mutation accepted without dependent mandatory effect coverage: %v", err)
			}
		})
	}
	for _, kind := range []string{"file", "json", "junit"} {
		t.Run("valid-"+kind, func(t *testing.T) {
			definition := doReplanCopyDefinition(t, session.Definition)
			check := PlaybookCheck{ID: "artifact", Purpose: "read actual mutation result", Cwd: ".", DependsOn: []string{"run"}, Required: true, ExpectedResult: "result verified", Kind: kind, ResultPath: "out/result.bin"}
			if kind == "json" {
				check.ExpectedJSON = json.RawMessage(`true`)
			}
			if kind == "junit" {
				check.MinCases = 1
			}
			definition.Checks = []PlaybookCheck{check}
			if err := validatePlaybookDefinition(root, definition); err != nil {
				t.Fatal(err)
			}
		})
	}
	definition := doReplanCopyDefinition(t, session.Definition)
	definition.Steps[0].Required = false
	definition.Steps = append(definition.Steps, PlaybookStep{ID: "consumer", Purpose: "read after mutation", Cwd: ".", Argv: []string{"git", "--version"}, DependsOn: []string{"run"}, Required: true, SideEffect: "read", ExpectedResult: "read completes"})
	definition.Checks[0].DependsOn = []string{"consumer"}
	if err := validatePlaybookDefinition(root, definition); err != nil {
		t.Fatal("valid transitive native coverage rejected", err)
	}
}

func TestDoNativeMutationLegacyEffectCheckNeedsIndependentFreshCall(t *testing.T) {
	root, input := doFixture(t)
	input.Definition.Steps[0] = PlaybookStep{ID: "run", Purpose: "write report with native file tool", Required: true, ExpectedResult: "report exists", SideEffect: "local_write", NativeAction: &PlaybookNativeAction{Kind: "file", Tool: "test.adapter.write", Target: "out/native.json", Arguments: json.RawMessage(`{"value":1}`)}}
	input.Definition.Checks[0].ResultPath = "out/native.json"
	input.Definition.Checks[0].JSONPointer = "/value"
	input.Definition.Checks[0].ExpectedJSON = json.RawMessage(`1`)
	session, err := doStart(root, input)
	if err != nil {
		t.Fatal(err)
	}
	session = doNativeRunProducer(t, root, session)
	session = doRecordFixture(t, root, session, "start-report", doRecordEvent{AttemptID: "report-1", TargetID: "report", Kind: "check", Event: "started"})
	makeEvent := func() doRecordEvent {
		return doRecordEvent{AttemptID: "report-1", TargetID: "report", Kind: "check", Event: "completed", Status: "passed", EvidenceOrigin: "agent_tool_observation", ToolCallID: "independent-file-check", Cwd: ".", StartedAt: doNow(), FinishedAt: doNow(), ResultRefs: []DoResultRef{{Path: "out/native.json", Kind: "json"}}}
	}
	for _, sameCall := range []bool{true, false} {
		event := makeEvent()
		if sameCall {
			event.ToolCallID = session.Attempts[0].ToolCallID
		} else {
			finished, _ := time.Parse(time.RFC3339Nano, session.Attempts[0].FinishedAt)
			event.StartedAt = finished.Add(-time.Millisecond).Format(time.RFC3339Nano)
		}
		current, digest, err := loadDoSession(root, session.ID)
		if err != nil {
			t.Fatal(err)
		}
		if _, err := doRecord(root, current, digest, doRecordInput{ExpectedRevision: current.Revision, RequestID: "reject-invalid-legacy-effect", Events: []doRecordEvent{event}}); err == nil {
			t.Fatal("legacy report inspection bypassed native effect independence")
		}
	}
	session = doRecordFixture(t, root, session, "complete-report", makeEvent())
	if validation := doValidate(root, session, false); validation.Status != "passed" {
		t.Fatal("valid independent local effect check failed", validation)
	}
}
