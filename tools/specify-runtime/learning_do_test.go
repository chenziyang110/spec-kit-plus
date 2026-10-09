package main

import (
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestDoLearningRecallsLegacyGlobalDefaultsWithoutBroadeningNarrowPreferences(t *testing.T) {
	root := t.TempDir()
	mustMkdirLearningTest(t, filepath.Join(root, ".specify"))
	legacy := []string{}
	for _, command := range knownLearningCommands {
		if command != "sp-do" {
			legacy = append(legacy, command)
		}
	}
	for _, item := range []struct {
		key     string
		applies []string
	}{
		{"project.supported-toolchain", legacy},
		{"debug.narrow-preference", []string{"sp-debug"}},
	} {
		args := []string{"capture", "--project-root", root, "--command", "sp-debug", "--type", "project_constraint", "--summary", "Use the repository-pinned toolchain when reproducing this operation", "--evidence", "The committed configuration declares the supported toolchain; a different major version produced incompatible outputs.", "--recurrence-key", item.key, "--signal", "high", "--format", "json"}
		for _, command := range item.applies {
			args = append(args, "--applies-to", command)
		}
		capture := runLearningEnvelopeTest(t, args)
		if capture.Status != "ok" {
			t.Fatalf("capture: %#v", capture)
		}
	}
	index := filepath.Join(root, ".specify/memory/learnings/INDEX.md")
	before, err := os.ReadFile(index)
	if err != nil {
		t.Fatal(err)
	}
	start := runLearningEnvelopeTest(t, []string{"start", "--project-root", root, "--command", "spx-do", "--format", "json"})
	if start.Status != "ok" || start.Data["command"] != "sp-do" || start.Data["read_only"] != true {
		t.Fatalf("start: %#v", start)
	}
	raw, _ := json.Marshal(start.Data["items"])
	if !strings.Contains(string(raw), "project.supported-toolchain") || strings.Contains(string(raw), "debug.narrow-preference") {
		t.Fatalf("legacy recall widened or missed applicability: %s", raw)
	}
	after, err := os.ReadFile(index)
	if err != nil || string(before) != string(after) {
		t.Fatal("read-only compatibility recall rewrote the stored command list")
	}
}

func TestDoLearningNormalSuccessIsNoOpAndRequiresExactSession(t *testing.T) {
	root, session := doStartFixture(t)
	session = doRunFixture(t, root, session)
	result := runLearningEnvelopeTest(t, []string{"capture-auto", "--project-root", root, "--command", "sp-do", "--session-id", session.ID, "--format", "json"})
	if result.Status != "ok" || result.Data["status"] != "no-op" || len(result.Data["captured"].([]any)) != 0 {
		t.Fatalf("ordinary pass became a lesson: %#v", result)
	}
	for _, args := range [][]string{
		{"capture-auto", "--project-root", root, "--command", "sp-do"},
		{"capture-auto", "--project-root", root, "--command", "sp-do", "--session-id", "../fixture"},
	} {
		if got := runLearningEnvelopeTest(t, args); got.Status == "ok" {
			t.Fatalf("accepted ambiguous/unsafe Do source: %#v", got)
		}
	}
}

func TestDoLearningOnlyCapturesVerifiedRecoveryWithScopedFacets(t *testing.T) {
	root, session := doStartFixture(t)
	session = doRecordFixture(t, root, session, "failed-start", doRecordEvent{AttemptID: "failed-run", TargetID: "run", Kind: "step", Event: "started"})
	one := 1
	stamp := doNow()
	session = doRecordFixture(t, root, session, "failed-completion", doRecordEvent{AttemptID: "failed-run", TargetID: "run", Kind: "step", Event: "completed", Status: "failed", EvidenceOrigin: "agent_tool_observation", ToolCallID: "test-observed-failure", Argv: []string{"git", "--version"}, Cwd: ".", StartedAt: stamp, FinishedAt: stamp, ExitCode: &one, Summary: "Toolchain unavailable until the pinned executable was restored"})
	before := runLearningEnvelopeTest(t, []string{"capture-auto", "--project-root", root, "--command", "sp-do", "--session-id", session.ID})
	if before.Status != "ok" || before.Data["status"] != "no-op" {
		t.Fatalf("unverified recovery generated guidance: %#v", before)
	}
	mustWriteLearningTest(t, filepath.Join(root, "out/recovery.txt"), "The prior native process ended and the intended toolchain is available; output paths were inspected before retry.")
	_, digest, err := loadDoSession(root, session.ID)
	if err != nil {
		t.Fatal(err)
	}
	session, err = doResume(root, session, digest, doResumeInput{ExpectedRevision: session.Revision, AttemptID: "failed-run", Recovery: DoRecovery{Reason: "inspected failed process and restored pinned executable", EvidenceRef: "out/recovery.txt", ProcessesStopped: true, SideEffectsInspected: true}})
	if err != nil {
		t.Fatal(err)
	}
	session = doRunFixture(t, root, session)
	args := []string{"capture-auto", "--project-root", root, "--command", "sp-do", "--session-id", session.ID}
	_, digest, err = loadDoSession(root, session.ID)
	if err != nil {
		t.Fatal(err)
	}
	session, err = doFinish(root, session, digest, doFinishInput{ExpectedRevision: session.Revision, KnowledgeStatus: "pending"})
	if err != nil {
		t.Fatal(err)
	}
	first := runLearningEnvelopeTest(t, args)
	if first.Status != "ok" {
		t.Fatalf("capture: %#v", first)
	}
	encoded, _ := json.Marshal(first.Data)
	if !strings.Contains(string(encoded), "do.recovered-operation.") || !strings.Contains(string(encoded), "operation_owners") {
		t.Fatalf("missing operation-bound recovery and facets: %s", encoded)
	}
	second := runLearningEnvelopeTest(t, args)
	if second.Status != "ok" || second.Data["status"] != "duplicate-snapshot" {
		t.Fatalf("capture replay changed the occurrence count: %#v", second)
	}
	metrics := runLearningEnvelopeTest(t, []string{"metrics", "--project-root", root, "--command", "sp-do"})
	if metrics.Status != "ok" {
		t.Fatalf("Do metrics unrecognized: %#v", metrics)
	}
	session, digest, err = loadDoSession(root, session.ID)
	if err != nil {
		t.Fatal(err)
	}
	if validation := doValidate(root, session, true); validation.Status != "passed" || len(validation.ChangedSourcePaths) != 0 {
		t.Fatalf("Learning metadata was mistaken for product mutation: %+v", validation)
	}
	if _, err := doFinish(root, session, digest, doFinishInput{ExpectedRevision: session.Revision, KnowledgeStatus: "not_applicable"}); err != nil {
		t.Fatalf("Learning prevents Do closeout: %v", err)
	}
}

func TestDoLearningDoesNotMistakeStaleOrNarratedSuccessForRecovery(t *testing.T) {
	session := DoSession{Definition: PlaybookDefinition{Operation: "test", Target: "runtime", Owner: "tooling", Variant: "default"}, Attempts: []DoAttempt{
		{ID: "a", Kind: "step", TargetID: "test", Status: "failed"},
		{ID: "b", Kind: "step", TargetID: "test", Status: "passed", EvidenceOrigin: "human_assertion", ToolCallID: "narration"},
	}}
	if len(doLearningSuggestions(session, DoValidation{Status: "passed"})) != 0 {
		t.Fatal("unproven observation became an automatic recovery lesson")
	}
	session.Attempts[1].EvidenceOrigin = "agent_tool_observation"
	if len(doLearningSuggestions(session, DoValidation{Status: "blocked"})) != 0 {
		t.Fatal("stale current validation became an automatic recovery lesson")
	}
	session.DefinitionEpoch = 2
	if len(doLearningSuggestions(session, DoValidation{Status: "passed"})) != 0 {
		t.Fatal("a retired epoch's passed observation became a current recovery lesson")
	}
	session.Attempts[1].DefinitionEpoch = 2
	if len(doLearningSuggestions(session, DoValidation{Status: "passed"})) != 1 {
		t.Fatal("replanning lost the observed failure once the current epoch actually recovered")
	}
}
