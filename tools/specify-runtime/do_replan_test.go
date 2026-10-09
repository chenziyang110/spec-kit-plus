package main

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"reflect"
	"strings"
	"testing"

	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/runcontrol"
)

func doReplanCopyDefinition(t *testing.T, definition PlaybookDefinition) PlaybookDefinition {
	t.Helper()
	raw, err := json.Marshal(definition)
	if err != nil {
		t.Fatal(err)
	}
	var result PlaybookDefinition
	if err := json.Unmarshal(raw, &result); err != nil {
		t.Fatal(err)
	}
	return result
}

func doReplanObservedFailure(t *testing.T, root string, session DoSession, target, attemptID string) (DoSession, DoRecovery) {
	t.Helper()
	action, err := doFindAction(session, "step", target)
	if err != nil {
		t.Fatal(err)
	}
	session = doRecordFixture(t, root, session, "start-"+attemptID, doRecordEvent{AttemptID: attemptID, TargetID: target, Kind: "step", Event: "started"})
	started := doNow()
	command := exec.Command(action.argv[0], action.argv[1:]...)
	command.Dir = filepath.Join(root, action.cwd)
	output, err := command.CombinedOutput()
	finished := doNow()
	if err == nil || command.ProcessState == nil || command.ProcessState.ExitCode() == 0 {
		t.Fatalf("fixture must execute a real failed command: %s %v", output, err)
	}
	exit := command.ProcessState.ExitCode()
	session = doRecordFixture(t, root, session, "complete-"+attemptID, doRecordEvent{AttemptID: attemptID, TargetID: target, Kind: "step", Event: "completed", Status: "failed", EvidenceOrigin: "agent_tool_observation", ToolCallID: "native-" + attemptID, Argv: action.argv, Cwd: action.cwd, StartedAt: started, FinishedAt: finished, ExitCode: &exit, Summary: strings.TrimSpace(string(output))})
	statusCommand := exec.Command("git", "status", "--porcelain=v1")
	statusCommand.Dir = root
	status, err := statusCommand.CombinedOutput()
	if err != nil {
		t.Fatal(err)
	}
	if err := os.MkdirAll(filepath.Join(root, "out"), 0o755); err != nil {
		t.Fatal(err)
	}
	ref := "out/recovery-" + attemptID + ".txt"
	raw := []byte(fmt.Sprintf("native process exited=%t exit_code=%d\ncommand_output=%s\nactual_workspace_status=%s\n", command.ProcessState.Exited(), exit, output, status))
	if err := os.WriteFile(filepath.Join(root, ref), raw, 0o600); err != nil {
		t.Fatal(err)
	}
	return session, DoRecovery{Reason: "inspected the completed native process and actual workspace status before correcting the command", EvidenceRef: ref, ProcessesStopped: true, SideEffectsInspected: true}
}

func doReplanFailureFixture(t *testing.T) (string, DoSession, doResumeInput) {
	t.Helper()
	root, input := doFixture(t)
	input.Definition.Steps[0].Argv = []string{"git", "spec-kit-no-such-command"}
	session, err := doStart(root, input)
	if err != nil {
		t.Fatal(err)
	}
	session, recovery := doReplanObservedFailure(t, root, session, "run", "failed-command")
	fixed := doReplanCopyDefinition(t, session.Definition)
	fixed.Steps[0].Argv = []string{"git", "--version"}
	return root, session, doResumeInput{ExpectedRevision: session.Revision, AttemptID: "failed-command", Recovery: recovery, Replan: &doReplanInput{RequestID: "correct-command", Definition: fixed}}
}

func doReplanApplyFixture(t *testing.T, root string, session DoSession, input doResumeInput) DoSession {
	t.Helper()
	_, digest, err := loadDoSession(root, session.ID)
	if err != nil {
		t.Fatal(err)
	}
	result, err := doReplan(root, session, digest, input)
	if err != nil {
		t.Fatal(err)
	}
	return result
}

func TestDoReplanFailedCommandCanVerifyAndPublishTheSameMethod(t *testing.T) {
	root, session, input := doReplanFailureFixture(t)
	oldDefinition := session.DefinitionDigest
	oldBaseline := session.BaselineJSON
	oldSources := doDigest(session.InitialSources)
	id := playbookID(session.Definition)
	requestJSON, _ := json.Marshal(input)
	var output bytes.Buffer
	if code := runDo([]string{"resume", session.ID, "--project-root", root, "--input-json", string(requestJSON), "--format", "json"}, &output); code != 0 {
		t.Fatalf("advertised resume replan failed: %d %s", code, output.String())
	}
	session, _, _ = loadDoSession(root, session.ID)
	if session.DefinitionEpoch != 2 || len(session.DefinitionHistory) != 2 || len(session.Attempts) != 1 || session.Attempts[0].Recovery == nil || session.Attempts[0].DefinitionDigest != oldDefinition || session.BaselineJSON != oldBaseline || doDigest(session.InitialSources) != oldSources {
		t.Fatalf("replan discarded or relabelled earlier execution: %+v", session)
	}
	if validation := doValidate(root, session, true); validation.Status == "passed" {
		t.Fatal("replacement definition passed before any current-epoch execution")
	}
	output.Reset()
	if code := runDo([]string{"show", session.ID, "--section", "definitions", "--project-root", root, "--format", "json"}, &output); code != 0 {
		t.Fatal(output.String())
	}
	var cards struct {
		Data struct {
			Definitions []map[string]any `json:"definitions"`
		} `json:"data"`
	}
	if err := json.Unmarshal(output.Bytes(), &cards); err != nil || len(cards.Data.Definitions) != 2 || cards.Data.Definitions[0]["definition"] != nil || cards.Data.Definitions[0]["show_argv"] == nil {
		t.Fatalf("history was not progressively disclosed: %v %s", err, output.String())
	}
	output.Reset()
	if code := runDo([]string{"show", session.ID, "--section", "definition:1", "--project-root", root, "--format", "json"}, &output); code != 0 || !bytes.Contains(output.Bytes(), []byte(`"definition_snapshot"`)) || !bytes.Contains(output.Bytes(), []byte("spec-kit-no-such-command")) {
		t.Fatalf("selected old definition was not retained: %d %s", code, output.String())
	}
	revision := session.Revision
	if replay, err := doReplan(root, session, "", input); err != nil || replay.Revision != revision || replay.DefinitionEpoch != 2 {
		t.Fatalf("exact replan replay was not idempotent: %v", err)
	}
	session = doRunFixture(t, root, session)
	for _, attempt := range session.Attempts[1:] {
		if attempt.DefinitionEpoch != 2 || !doAttemptInCurrentDefinition(session, attempt) {
			t.Fatal("new observation was not bound to its runtime epoch")
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
	if publication["id"] != id || publication["status"] != "created" {
		t.Fatal(publication)
	}
	playbookFinishFixture(t, root, session.ID, publication)
	doc, err := loadPlaybookDocument(root, id)
	definitionDigest, digestErr := playbookDefinitionDigest(doc.Definition)
	if err != nil || digestErr != nil || definitionDigest != session.DefinitionDigest || definitionDigest == oldDefinition {
		t.Fatalf("published the previous failed definition: %v %+v", err, doc)
	}
}

func TestDoReplanEpochPreventsAThenBThenAFromRevivingPassedAttempts(t *testing.T) {
	root, start := doFixture(t)
	start.Definition.Steps = append(start.Definition.Steps, PlaybookStep{ID: "probe", Purpose: "inspect an optional unavailable Git operation", Cwd: ".", Argv: []string{"git", "spec-kit-no-such-command"}, Required: false, ExpectedResult: "actual capability discovery", SideEffect: "read"})
	session, err := doStart(root, start)
	if err != nil {
		t.Fatal(err)
	}
	original := doReplanCopyDefinition(t, session.Definition)
	session = doRunFixture(t, root, session)
	session, firstRecovery := doReplanObservedFailure(t, root, session, "probe", "probe-a")
	changed := doReplanCopyDefinition(t, session.Definition)
	changed.Steps[0].Argv = []string{"git", "version", "--build-options"}
	first := doResumeInput{ExpectedRevision: session.Revision, AttemptID: "probe-a", Recovery: firstRecovery, Replan: &doReplanInput{RequestID: "method-b", Definition: changed}}
	session = doReplanApplyFixture(t, root, session, first)
	_, digest, _ := loadDoSession(root, session.ID)
	if _, err := doRecord(root, session, digest, doRecordInput{ExpectedRevision: session.Revision, RequestID: "reuse-old-producer", Events: []doRecordEvent{{AttemptID: "report-b", TargetID: "report", Kind: "check", Event: "started"}}}); err == nil {
		t.Fatal("new epoch accepted an old passed producer dependency")
	}
	session, secondRecovery := doReplanObservedFailure(t, root, session, "probe", "probe-b")
	second := doResumeInput{ExpectedRevision: session.Revision, AttemptID: "probe-b", Recovery: secondRecovery, Replan: &doReplanInput{RequestID: "method-a-again", Definition: original}}
	session = doReplanApplyFixture(t, root, session, second)
	if session.DefinitionEpoch != 3 || session.DefinitionDigest != session.DefinitionHistory[0].DefinitionDigest || len(session.Attempts) != 4 || len(doLatestAttempts(session)) != 0 {
		t.Fatal("returning to definition A revived its epoch-one observations")
	}
	if validation := doValidate(root, session, true); validation.Status == "passed" {
		t.Fatal("A→B→A reused old passing checks")
	}
	if err := doValidateDefinitionHistory(root, session); err != nil {
		t.Fatal(err)
	}
}

func TestDoReplanRejectsUnknownEffectsAndUnverifiedChanges(t *testing.T) {
	tests := []struct {
		name   string
		change func(*DoSession, *doResumeInput)
		want   string
	}{
		{"unchanged", func(s *DoSession, i *doResumeInput) { i.Replan.Definition = s.Definition }, "ordinary resume"},
		{"identity", func(s *DoSession, i *doResumeInput) { i.Replan.Definition.Target = "another-target" }, "identity"},
		{"goal", func(s *DoSession, i *doResumeInput) { i.Replan.Definition.Goal = "another task" }, "goal"},
		{"revision", func(s *DoSession, i *doResumeInput) { i.ExpectedRevision-- }, "revision conflict"},
		{"running", func(s *DoSession, i *doResumeInput) { s.Attempts[0].Status = "running" }, "unknown effects"},
		{"interrupted", func(s *DoSession, i *doResumeInput) { s.Attempts[0].Status = "interrupted" }, "unknown effects"},
		{"uninspected", func(s *DoSession, i *doResumeInput) { i.Recovery.SideEffectsInspected = false }, "inspected"},
		{"invented-failure", func(s *DoSession, i *doResumeInput) { zero := 0; s.Attempts[0].ExitCode = &zero }, "nonzero"},
		{"shrinking-output", func(s *DoSession, i *doResumeInput) { i.Replan.OutputScope = []string{} }, "shrink"},
		{"runtime-scope", func(s *DoSession, i *doResumeInput) { i.Replan.WriteScope = []string{".specify/project-cognition"} }, "runtime/workflow"},
		{"escaping-scope", func(s *DoSession, i *doResumeInput) { i.Replan.WriteScope = []string{"../outside"} }, "project-relative"},
		{"source-output-overlap", func(s *DoSession, i *doResumeInput) { i.Replan.WriteScope = []string{"out"} }, "overlap"},
	}
	for _, test := range tests {
		t.Run(test.name, func(t *testing.T) {
			root, session, input := doReplanFailureFixture(t)
			_, digest, err := loadDoSession(root, session.ID)
			if err != nil {
				t.Fatal(err)
			}
			test.change(&session, &input)
			if _, err := doReplan(root, session, digest, input); err == nil || !strings.Contains(err.Error(), test.want) {
				t.Fatalf("invalid replan accepted or wrong boundary: %v", err)
			}
			if _, after, err := loadDoSession(root, session.ID); err != nil || after != digest {
				t.Fatalf("rejected replan mutated the last checkpoint: %v", err)
			}
		})
	}
}

func TestDoReplanClaimsExpandedScopeBeforeMutationAndPreservesBaseline(t *testing.T) {
	root, session, input := doReplanFailureFixture(t)
	baseline := session.BaselineJSON
	input.Replan.WriteScope = []string{"scripts"}
	input.Replan.OutputScope = []string{"out", "reports"}
	session = doReplanApplyFixture(t, root, session, input)
	if session.BaselineJSON != baseline || !reflect.DeepEqual(session.WriteScope, []string{"scripts"}) || !reflect.DeepEqual(session.OutputScope, []string{"out", "reports"}) {
		t.Fatal("scope expansion replaced the original mutation baseline")
	}
	view, err := runcontrol.OpenViewForRepository(context.Background(), root)
	if err != nil {
		t.Fatal(err)
	}
	owners, err := view.FindWorkOwners(context.Background(), "scripts/helper.sh")
	_ = view.Close()
	if err != nil || len(owners) != 1 || owners[0].Work.WorkID != session.WorkID {
		t.Fatalf("new helper scope was not claimed before writes: %v %+v", err, owners)
	}
	if err := os.MkdirAll(filepath.Join(root, "scripts"), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(root, "scripts/helper.sh"), []byte("#!/bin/sh\ngit --version\n"), 0o755); err != nil {
		t.Fatal(err)
	}
	changes, err := runcontrol.InspectWorkspaceDelta(context.Background(), root, session.BaselineJSON)
	if err != nil || !doScopeContains(changes, "scripts/helper.sh") {
		t.Fatalf("new helper disappeared from the initial source mutation basis: %v %v", err, changes)
	}
	if got := doValidate(root, session, true); got.Status == "passed" || got.CognitionCloseout == "not_applicable" {
		t.Fatal("new helper skipped fresh execution or cognition closeout")
	}
}

func TestDoReplanCannotRetroactivelyClaimFilesOrLoseConcurrentReceipts(t *testing.T) {
	t.Run("retroactive", func(t *testing.T) {
		root, session, input := doReplanFailureFixture(t)
		if err := os.WriteFile(filepath.Join(root, "unclaimed.sh"), []byte("git --version\n"), 0o600); err != nil {
			t.Fatal(err)
		}
		input.Replan.WriteScope = []string{"unclaimed.sh"}
		_, digest, _ := loadDoSession(root, session.ID)
		if _, err := doReplan(root, session, digest, input); err == nil || !strings.Contains(err.Error(), "retroactively") {
			t.Fatalf("previously unclaimed mutation was laundered: %v", err)
		}
	})
	t.Run("cas-and-replay", func(t *testing.T) {
		root, before, first := doReplanFailureFixture(t)
		_, originalDigest, _ := loadDoSession(root, before.ID)
		current := doReplanApplyFixture(t, root, before, first)
		second := first
		copyReplan := *first.Replan
		copyReplan.RequestID = "parallel-replan"
		second.Replan = &copyReplan
		if _, err := doReplan(root, before, originalDigest, second); err == nil || !strings.Contains(err.Error(), "revision conflict") {
			t.Fatalf("stale concurrent replan was accepted: %v", err)
		}
		loaded, _, err := loadDoSession(root, before.ID)
		if err != nil || loaded.Revision != current.Revision || len(loaded.ReplanReceipts) != 1 || loaded.ReplanReceipts[first.Replan.RequestID].DefinitionEpoch != 2 {
			t.Fatalf("CAS conflict lost the committed replan receipt: %v", err)
		}
		changedPayload := first
		changedPayload.Recovery.Reason = "different recovery"
		if _, err := doReplan(root, loaded, "", changedPayload); err == nil || !strings.Contains(err.Error(), "reused") {
			t.Fatalf("request key accepted a changed payload: %v", err)
		}
		emptyScope := *first.Replan
		emptyScope.OutputScope = []string{}
		changedPayload = first
		changedPayload.Replan = &emptyScope
		if _, err := doReplan(root, loaded, "", changedPayload); err == nil || !strings.Contains(err.Error(), "reused") {
			t.Fatalf("explicit empty scope was confused with omitted inherited scope: %v", err)
		}
	})
}

func TestDoReplanInputKeepsExplicitScopeAndRuntimeFieldsStrict(t *testing.T) {
	_, _, input := doReplanFailureFixture(t)
	raw, err := json.Marshal(input)
	if err != nil {
		t.Fatal(err)
	}
	var decoded doResumeInput
	if err := doReadInput(string(raw), &decoded); err != nil || decoded.Replan.WriteScope != nil {
		t.Fatalf("omitted scope did not remain inherited: %v", err)
	}
	var document map[string]any
	if err := json.Unmarshal(raw, &document); err != nil {
		t.Fatal(err)
	}
	for _, field := range []string{"write_scope", "output_scope", "definition_epoch"} {
		replan := document["replan"].(map[string]any)
		replan[field] = nil
		bad, _ := json.Marshal(document)
		if err := doReadInput(string(bad), &decoded); err == nil {
			t.Fatalf("accepted null scope or runtime-owned field %s", field)
		}
		delete(replan, field)
	}
}

func TestDoReplanHistoryAndRecoveryRemainBoundOnReplay(t *testing.T) {
	root, session, input := doReplanFailureFixture(t)
	session = doReplanApplyFixture(t, root, session, input)
	ref := filepath.Join(root, doDefinitionEpochRef(session.ID, 1))
	original, err := os.ReadFile(ref)
	if err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(ref, append(append([]byte{}, original...), ' '), 0o600); err != nil {
		t.Fatal(err)
	}
	if _, err := doReplan(root, session, "", input); err == nil || !strings.Contains(err.Error(), "immutable") {
		t.Fatalf("altered history was silently repaired: %v", err)
	}
	if err := os.WriteFile(ref, original, 0o600); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(root, input.Recovery.EvidenceRef), []byte("changed recovery report"), 0o600); err != nil {
		t.Fatal(err)
	}
	if _, err := doReplan(root, session, "", input); err == nil || !strings.Contains(err.Error(), "recovery evidence") {
		t.Fatalf("replayed changed recovery evidence: %v", err)
	}
	if raw, err := os.ReadFile(ref); err != nil || !bytes.Equal(raw, original) {
		t.Fatal("recovery failure rewrote an immutable definition")
	}
}

func TestDoReplanCannotUseAnEarlierFailureAlreadyReplacedByAPass(t *testing.T) {
	root, start := doFixture(t)
	start.Definition.Steps[0].Argv = []string{"git", "config", "--file", "out/probe.ini", "--get", "probe.enabled"}
	session, err := doStart(root, start)
	if err != nil {
		t.Fatal(err)
	}
	session, recovery := doReplanObservedFailure(t, root, session, "run", "missing-config")
	_, digest, _ := loadDoSession(root, session.ID)
	session, err = doResume(root, session, digest, doResumeInput{ExpectedRevision: session.Revision, AttemptID: "missing-config", Recovery: recovery})
	if err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(root, "out/probe.ini"), []byte("[probe]\n\tenabled = true\n"), 0o600); err != nil {
		t.Fatal(err)
	}
	session = doRecordFixture(t, root, session, "start-now-present", doRecordEvent{AttemptID: "config-present", TargetID: "run", Kind: "step", Event: "started"})
	action, _ := doFindAction(session, "step", "run")
	started := doNow()
	command := exec.Command(action.argv[0], action.argv[1:]...)
	command.Dir = root
	out, err := command.CombinedOutput()
	if err != nil {
		t.Fatalf("real config check did not recover: %s %v", out, err)
	}
	zero := 0
	session = doRecordFixture(t, root, session, "complete-now-present", doRecordEvent{AttemptID: "config-present", TargetID: "run", Kind: "step", Event: "completed", Status: "passed", EvidenceOrigin: "agent_tool_observation", ToolCallID: "native-config-now-present", Argv: action.argv, Cwd: ".", StartedAt: started, FinishedAt: doNow(), ExitCode: &zero})
	definition := doReplanCopyDefinition(t, session.Definition)
	definition.Steps[0].Argv = []string{"git", "--version"}
	_, digest, _ = loadDoSession(root, session.ID)
	input := doResumeInput{ExpectedRevision: session.Revision, AttemptID: "missing-config", Recovery: recovery, Replan: &doReplanInput{RequestID: "unnecessary-replan", Definition: definition}}
	if _, err := doReplan(root, session, digest, input); err == nil || !strings.Contains(err.Error(), "latest unresolved") {
		t.Fatalf("an already recovered failure was reused as replan authority: %v", err)
	}
}

func TestDoReplanRequiresAnActualTypedAssertionFailure(t *testing.T) {
	for _, fails := range []bool{false, true} {
		t.Run(fmt.Sprint(fails), func(t *testing.T) {
			root, session := doStartFixture(t)
			session = doRunFixture(t, root, session)
			session = doRecordFixture(t, root, session, "start-inspection-failure", doRecordEvent{AttemptID: "inspection-failure", TargetID: "report", Kind: "check", Event: "started"})
			started := doNow()
			report := []byte(`{"ok":true}`)
			if fails {
				report = []byte(`{"ok":false}`)
			}
			if err := os.WriteFile(filepath.Join(root, "out/report.json"), report, 0o600); err != nil {
				t.Fatal(err)
			}
			session = doRecordFixture(t, root, session, "complete-inspection-failure", doRecordEvent{AttemptID: "inspection-failure", TargetID: "report", Kind: "check", Event: "completed", Status: "failed", EvidenceOrigin: "agent_tool_observation", ToolCallID: "native-read-json-report", Argv: []string{}, Cwd: ".", StartedAt: started, FinishedAt: doNow(), ResultRefs: []DoResultRef{{Path: "out/report.json", Kind: "json"}}})
			recoveryRef := "out/recovery-inspection.txt"
			if err := os.WriteFile(filepath.Join(root, recoveryRef), append([]byte("inspected actual assertion report; no native process remains: "), report...), 0o600); err != nil {
				t.Fatal(err)
			}
			definition := doReplanCopyDefinition(t, session.Definition)
			definition.Checks[0].JSONPointer = ""
			definition.Checks[0].ExpectedJSON = json.RawMessage(`{"ok":true}`)
			input := doResumeInput{ExpectedRevision: session.Revision, AttemptID: "inspection-failure", Recovery: DoRecovery{Reason: "inspected report and tightened the complete JSON assertion", EvidenceRef: recoveryRef, ProcessesStopped: true, SideEffectsInspected: true}, Replan: &doReplanInput{RequestID: "inspect-replan", Definition: definition}}
			_, digest, _ := loadDoSession(root, session.ID)
			_, err := doReplan(root, session, digest, input)
			if fails && err != nil {
				t.Fatalf("real typed failure could not be replanned: %v", err)
			}
			if !fails && (err == nil || !strings.Contains(err.Error(), "actually satisfies")) {
				t.Fatalf("a passing report relabelled failed authorized a replan: %v", err)
			}
		})
	}
}
