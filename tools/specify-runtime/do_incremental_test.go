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

func doIncrementalFixture(t *testing.T) (string, DoSession) {
	t.Helper()
	root, session := doStartFixture(t)
	session = doRecordFixture(t, root, session, "inc-start", doRecordEvent{AttemptID: "build-1", TargetID: "run", Kind: "step", Event: "started"})
	started := doNow()
	command := exec.Command("git", "--version")
	command.Dir = root
	output, err := command.Output()
	if err != nil {
		t.Fatal(err)
	}
	if err := os.MkdirAll(filepath.Join(root, "out"), 0755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(root, "out/build.txt"), output, 0644); err != nil {
		t.Fatal(err)
	}
	zero := 0
	session = doRecordFixture(t, root, session, "inc-complete", doRecordEvent{AttemptID: "build-1", TargetID: "run", Kind: "step", Event: "completed", Status: "passed", EvidenceOrigin: "agent_tool_observation", ToolCallID: "actual-git-build", Argv: []string{"git", "--version"}, Cwd: ".", StartedAt: started, FinishedAt: doNow(), ExitCode: &zero, ResultRefs: []DoResultRef{{Path: "out/build.txt", Kind: "file"}}})
	session = doRecordFixture(t, root, session, "inc-report-start", doRecordEvent{AttemptID: "report-1", TargetID: "report", Kind: "check", Event: "started"})
	started = doNow()
	if err := os.WriteFile(filepath.Join(root, "out/report.json"), []byte(`{"ok":true}`), 0644); err != nil {
		t.Fatal(err)
	}
	session = doRecordFixture(t, root, session, "inc-report-complete", doRecordEvent{AttemptID: "report-1", TargetID: "report", Kind: "check", Event: "completed", Status: "passed", EvidenceOrigin: "agent_tool_observation", ToolCallID: "actual-report-read", Cwd: ".", StartedAt: started, FinishedAt: doNow(), ResultRefs: []DoResultRef{{Path: "out/report.json", Kind: "json"}}})
	return root, session
}

func doIncrementalInput(session DoSession) doResumeInput {
	definition := playbookNormalizeDefinition(session.Definition)
	check := definition.Checks[0]
	check.ID = "confirm"
	definition.Checks = append(definition.Checks, check)
	return doResumeInput{ExpectedRevision: session.Revision, Replan: &doReplanInput{RequestID: "incremental", Mode: "unstarted", RetainVerified: true, Definition: definition}}
}

func TestDoIncrementalUnstartedRetainsFreshOriginalEvidence(t *testing.T) {
	root, session := doIncrementalFixture(t)
	original := append([]DoAttempt{}, session.Attempts...)
	input := doIncrementalInput(session)
	// Public JSON deliberately omits fabricated failed-attempt/recovery fields.
	raw, _ := json.Marshal(map[string]any{"expected_revision": session.Revision, "replan": input.Replan})
	var out bytes.Buffer
	if code := runDo([]string{"resume", session.ID, "--project-root", root, "--input-json", string(raw), "--format", "json"}, &out); code != 0 {
		t.Fatalf("%d %s", code, out.String())
	}
	session, _, _ = loadDoSession(root, session.ID)
	if len(session.DefinitionHistory[1].RetainedAttempts) != 2 || len(doLatestAttempts(session)) != 2 || doDigest(original) != doDigest(session.Attempts) {
		t.Fatalf("original evidence rewritten or lost: %+v", session)
	}
	if doValidate(root, session, true).Status == "passed" {
		t.Fatal("new required check was skipped")
	}
	session = doRecordFixture(t, root, session, "confirm-start", doRecordEvent{AttemptID: "confirm-2", TargetID: "confirm", Kind: "check", Event: "started"})
	started := doNow()
	if _, err := os.ReadFile(filepath.Join(root, "out/report.json")); err != nil {
		t.Fatal(err)
	}
	session = doRecordFixture(t, root, session, "confirm-end", doRecordEvent{AttemptID: "confirm-2", TargetID: "confirm", Kind: "check", Event: "completed", Status: "passed", EvidenceOrigin: "agent_tool_observation", ToolCallID: "actual-confirm-read", Cwd: ".", StartedAt: started, FinishedAt: doNow(), ResultRefs: []DoResultRef{{Path: "out/report.json", Kind: "json"}}})
	if result := doValidate(root, session, true); result.Status != "passed" {
		t.Fatalf("fresh carried prerequisite unusable: %+v", result)
	}
	// Rerunning an upstream action changes its identity, invalidating descendants.
	session = doRecordFixture(t, root, session, "rerun-upstream", doRecordEvent{AttemptID: "build-2", TargetID: "run", Kind: "step", Event: "started"})
	if doValidate(root, session, true).Status == "passed" {
		t.Fatal("upstream rerun left descendants accepted")
	}
}

func TestDoIncrementalRefusesStaleAndWeakenedEvidence(t *testing.T) {
	for _, kind := range []string{"changed-output", "changed-source", "tampered-attempt", "attempted-edit", "weakened-check", "source-writer", "external"} {
		t.Run(kind, func(t *testing.T) {
			root, session := doIncrementalFixture(t)
			input := doIncrementalInput(session)
			switch kind {
			case "changed-output":
				_ = os.WriteFile(filepath.Join(root, "out/build.txt"), []byte("different"), 0644)
			case "changed-source":
				_ = os.WriteFile(filepath.Join(root, "source.txt"), []byte("different"), 0644)
			case "tampered-attempt":
				session.Attempts[0].Summary = "forged"
			case "attempted-edit":
				input.Replan.Definition.Steps[0].Argv = []string{"git", "status"}
			case "weakened-check":
				input.Replan.Definition.Checks[0].Required = false
			case "source-writer":
				session.Definition.Steps[0].SourceWrites = []string{"source.txt"}
			case "external":
				session.Definition.Steps[0].SideEffect = "external_mutation"
			}
			if kind == "source-writer" || kind == "external" {
				if len(doPlanRetained(root, session, session.Definition, session.Attempts[0].SourceFingerprint)) != 0 {
					t.Fatal("unsafe mutation carried")
				}
				return
			}
			_, digest, _ := loadDoSession(root, session.ID)
			next, err := doResume(root, session, digest, input)
			if kind == "attempted-edit" || kind == "weakened-check" {
				if err == nil {
					t.Fatal("unsafe adjustment accepted")
				}
				return
			}
			if kind == "tampered-attempt" { // Optimistic session binding rejects our changed in-memory payload.
				if err == nil && len(next.DefinitionHistory[1].RetainedAttempts) > 0 {
					t.Fatal("forged evidence carried")
				}
				return
			}
			if err != nil {
				t.Fatal(err)
			}
			if len(next.DefinitionHistory[1].RetainedAttempts) != 0 {
				t.Fatal("stale result carried")
			}
		})
	}
}

func TestDoIncrementalCarryReceiptTamperAndVerifiedChain(t *testing.T) {
	root, session := doIncrementalFixture(t)
	_, digest, _ := loadDoSession(root, session.ID)
	session, err := doResume(root, session, digest, doIncrementalInput(session))
	if err != nil {
		t.Fatal(err)
	}
	session.Attempts[0].ToolCallID = "different-tool"
	if err := doValidateRetainedBindings(session); err == nil {
		t.Fatal("tampered original accepted")
	}
	session, _, _ = loadDoSession(root, session.ID)
	input := doIncrementalInput(session)
	input.Replan.RequestID = "second"
	input.Replan.Definition = playbookNormalizeDefinition(session.Definition)
	input.Replan.Definition.Title = "same method, refined title"
	_, digest, _ = loadDoSession(root, session.ID)
	session, err = doResume(root, session, digest, input)
	if err != nil {
		t.Fatal(err)
	}
	if len(doLatestAttempts(session)) != 2 || len(session.DefinitionHistory[2].RetainedAttempts) != 2 {
		t.Fatal("verified original evidence was lost at the second replan")
	}
	for _, retained := range session.DefinitionHistory[2].RetainedAttempts {
		if retained.FromEpoch != 1 || retained.AttemptDigest != doDigest(doLatestAttempts(session)[retained.TargetID]) {
			t.Fatal("retention changed the original observation identity")
		}
	}
	if err := doValidateDefinitionHistory(root, session); err != nil {
		t.Fatal(err)
	}
	if err := doDependencyReady(root, session, doLatestAttempts(session), "report", session.Attempts[0].SourceFingerprint); err != nil {
		t.Fatalf("third-epoch consumer lost the actual build prerequisite: %v", err)
	}
	if len(session.Attempts) != 2 || session.Attempts[0].DefinitionEpoch != 1 || session.Attempts[1].DefinitionEpoch != 1 {
		t.Fatal("carrying evidence copied or replayed original attempts")
	}
	// Inputs refuse forged empty recovery and runtime-owned receipts.
	raw, _ := json.Marshal(map[string]any{"expected_revision": session.Revision, "recovery": map[string]any{}, "replan": input.Replan})
	var decoded doResumeInput
	if err := doReadInput(string(raw), &decoded); err == nil || !strings.Contains(err.Error(), "fabricate") {
		t.Fatalf("%v", err)
	}
}

func TestDoIncrementalChainInvalidatesChangesAndMissingHops(t *testing.T) {
	for _, change := range []string{"input", "script", "output", "snapshot", "command", "dependency", "external", "missing-hop", "changed-hop", "superseded"} {
		t.Run(change, func(t *testing.T) {
			root, session := doIncrementalFixture(t)
			_, digest, _ := loadDoSession(root, session.ID)
			var err error
			session, err = doResume(root, session, digest, doIncrementalInput(session))
			if err != nil {
				t.Fatal(err)
			}
			definition := playbookNormalizeDefinition(session.Definition)
			fingerprint := session.Attempts[0].SourceFingerprint
			switch change {
			case "input", "script":
				// Scripts participate in the same declared-input fingerprint.
				if change == "script" {
					definition.Steps[0].ScriptRef = "source.txt"
				}
				if err := os.WriteFile(filepath.Join(root, "source.txt"), []byte("changed input or script"), 0644); err != nil {
					t.Fatal(err)
				}
				_, fingerprint, _, _, err = doCaptureSource(root, definition)
				if err != nil {
					t.Fatal(err)
				}
			case "output":
				if err := os.WriteFile(filepath.Join(root, "out/build.txt"), []byte("changed artifact"), 0644); err != nil {
					t.Fatal(err)
				}
			case "snapshot":
				if err := os.WriteFile(filepath.Join(root, filepath.FromSlash(session.Attempts[0].Results[0].SnapshotRef)), []byte("changed receipt"), 0644); err != nil {
					t.Fatal(err)
				}
			case "command":
				definition.Steps[0].Argv = []string{"git", "status"}
			case "dependency":
				definition.Checks[0].DependsOn = nil
			case "external":
				definition.Steps[0].SideEffect = "external_mutation"
			case "missing-hop":
				session.DefinitionHistory[1].RetainedAttempts = nil
			case "changed-hop":
				session.DefinitionHistory[1].RetainedAttempts[0].AttemptDigest = "changed"
			case "superseded":
				replacement := session.Attempts[0]
				replacement.ID, replacement.Status = "build-2", "failed"
				replacement.DefinitionEpoch, replacement.DefinitionDigest = 2, session.DefinitionDigest
				session.Attempts = append(session.Attempts, replacement)
			}
			retained := doPlanRetained(root, session, definition, fingerprint)
			for _, item := range retained {
				if change != "dependency" || item.TargetID == "report" {
					t.Fatalf("%s preserved invalid evidence: %+v", change, retained)
				}
			}
			if change == "changed-hop" && doValidateRetainedBindings(session) == nil {
				t.Fatal("tampered intermediate receipt was accepted")
			}
		})
	}
}

func TestDoIncrementalPreservesCompleteRequiredClosure(t *testing.T) {
	_, input := doFixture(t)
	previous := playbookNormalizeDefinition(input.Definition)
	previous.Checks[0].Kind = "exit_code"
	previous.Checks[0].Argv = []string{"git", "status", "--porcelain"}
	previous.Checks[0].ResultPath, previous.Checks[0].JSONPointer, previous.Checks[0].ExpectedJSON = "", "", nil
	changed := playbookNormalizeDefinition(previous)
	changed.Checks[0].Argv = []string{"git", "--version"}
	if doIncrementalContract(previous, changed) == nil {
		t.Fatal("exit check identity was weakened")
	}
	previous.Checks[0].NativeAction = &PlaybookNativeAction{Kind: "connector", Tool: "fixture.inspect", Target: "actual-record", Arguments: json.RawMessage(`{}`)}
	changed = playbookNormalizeDefinition(previous)
	changed.Checks[0].NativeAction.Target = "unrelated-record"
	if doIncrementalContract(previous, changed) == nil {
		t.Fatal("observation target replaced")
	}
	previous = playbookNormalizeDefinition(input.Definition)
	prerequisite := previous.Checks[0]
	prerequisite.ID = "optional-prerequisite"
	prerequisite.Required = false
	prerequisite.Kind = "junit"
	prerequisite.ExpectedJSON = nil
	prerequisite.JSONPointer = ""
	prerequisite.MinCases = 10
	previous.Checks = append([]PlaybookCheck{prerequisite}, previous.Checks...)
	previous.Checks[1].DependsOn = []string{"optional-prerequisite"}
	changed = playbookNormalizeDefinition(previous)
	changed.Checks[0].MinCases = 1
	if doIncrementalContract(previous, changed) == nil {
		t.Fatal("optional required prerequisite weakened")
	}
	previous = playbookNormalizeDefinition(input.Definition)
	preflight := previous.Steps[0]
	preflight.ID = "preflight"
	preflight.Required = false
	previous.Steps = append([]PlaybookStep{preflight}, previous.Steps...)
	previous.Steps[1].DependsOn = []string{"preflight"}
	changed = playbookNormalizeDefinition(previous)
	changed.Steps[1].DependsOn = nil
	if doIncrementalContract(previous, changed) == nil {
		t.Fatal("required step prerequisite removed")
	}
}

func TestDoIncrementalRefusesChangedOutputBeforeConsumerStarts(t *testing.T) {
	root, session := doIncrementalFixture(t)
	_, digest, _ := loadDoSession(root, session.ID)
	session, err := doResume(root, session, digest, doIncrementalInput(session))
	if err != nil {
		t.Fatal(err)
	}
	_, before, _ := loadDoSession(root, session.ID)
	if err := os.WriteFile(filepath.Join(root, "out/build.txt"), []byte("tampered after retention"), 0644); err != nil {
		t.Fatal(err)
	}
	_, err = doRecord(root, session, before, doRecordInput{ExpectedRevision: session.Revision, RequestID: "bad-consumer", Events: []doRecordEvent{{AttemptID: "bad-consumer", TargetID: "confirm", Kind: "check", Event: "started"}}})
	if err == nil {
		t.Fatal("consumer was allowed to run using changed retained output")
	}
	_, after, _ := loadDoSession(root, session.ID)
	if before != after {
		t.Fatal("rejected consumer changed session")
	}
}
