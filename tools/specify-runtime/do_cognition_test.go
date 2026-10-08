package main

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"os"
	"os/exec"
	"path/filepath"
	"reflect"
	"strings"
	"testing"
	"time"

	changemodel "github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/changes/model"
	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/closeout"
	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/runcontrol"
	rt "github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/runtime"
	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/store"
)

// Import a baseline using real bytes and the fixture's actual Git commit before
// Do starts. Its real operation then changes source and creates another path.
func doSeedCognitionBaseline(t *testing.T, root string) rt.Paths {
	t.Helper()
	paths, err := rt.ResolvePaths(root)
	if err != nil {
		t.Fatal(err)
	}
	command := exec.Command("git", "rev-parse", "HEAD")
	command.Dir = root
	rawCommit, err := command.Output()
	if err != nil {
		t.Fatal(err)
	}
	commit := strings.TrimSpace(string(rawCommit))
	source, err := os.ReadFile(filepath.Join(root, "source.txt"))
	if err != nil {
		t.Fatal(err)
	}
	st, err := store.Open(paths)
	if err != nil {
		t.Fatal(err)
	}
	_, err = st.ImportGeneration(context.Background(), store.ImportInput{
		GenerationID: "GEN-do-closeout", Kind: "full", SourceCommit: commit,
		Evidence:  []store.EvidenceImport{{ID: "E-source", SourceKind: "file", SourcePath: "source.txt", CommitSHA: commit, Extractor: "do-integration-fixture", ContentHash: fileContentSHA256(source)}},
		Nodes:     []store.NodeImport{{ID: "N-source", Type: "capability", Title: "Source generation", Confidence: "verified", EvidenceIDs: []string{"E-source"}}},
		PathIndex: []store.PathIndexImport{{ID: "P-source", Path: "source.txt", NodeID: "N-source", Relation: "owns", Confidence: "verified", EvidenceID: "E-source"}},
		Aliases:   []store.AliasImport{{ID: "A-source", Alias: "Source generation", NormalizedAlias: "source generation", TargetType: "node", TargetID: "N-source", Source: "node_title", Confidence: "verified", EvidenceID: "E-source"}},
	})
	if err == nil {
		_, _, err = st.PublishRuntimeMetadata(context.Background(), "GEN-do-closeout", rt.BaselineKindBrownfieldFull)
	}
	closeErr := st.Close()
	if err != nil || closeErr != nil {
		t.Fatalf("seed cognition: %v %v", err, closeErr)
	}
	status := rt.DefaultStatus(paths)
	status.Status, status.Freshness, status.Readiness = "ok", rt.ReadyFreshness, rt.ReadyReadiness
	status.GraphReady, status.ActiveGenerationID, status.BaselineKind = true, "GEN-do-closeout", rt.BaselineKindBrownfieldFull
	status.RecommendedNextAction = "use_project_cognition"
	if err := rt.WriteStatus(paths, status); err != nil {
		t.Fatal(err)
	}
	for name, body := range map[string]string{
		"capability-ledger.json": "{\"rows\":[]}",
		"control-ledger.json":    "{\"rows\":[]}",
		"coverage-ledger.json":   "{\"rows\":[{\"path\":\"source.txt\",\"status\":\"covered\"}],\"open_gaps\":[]}",
	} {
		file := filepath.Join(paths.RuntimeDir, "workbench", name)
		if err := os.MkdirAll(filepath.Dir(file), 0o755); err != nil {
			t.Fatal(err)
		}
		if err := os.WriteFile(file, []byte(body+"\n"), 0o644); err != nil {
			t.Fatal(err)
		}
	}
	return paths
}

func doCognitionPlannerPayload(t *testing.T, root string, session DoSession) []byte {
	t.Helper()
	validation := doValidate(root, session, false)
	if validation.Status != "passed" || len(validation.ChangedSourcePaths) == 0 {
		t.Fatalf("operation must pass its actual checks before cognition: %+v", validation)
	}
	// The existing planner resolves cwd; unlike closeout apply it does not
	// accept --project-root. Exercise its actual public command contract.
	cwd, err := os.Getwd()
	if err != nil {
		t.Fatal(err)
	}
	if err := os.Chdir(root); err != nil {
		t.Fatal(err)
	}
	defer func() {
		if err := os.Chdir(cwd); err != nil {
			t.Fatal(err)
		}
	}()
	args := []string{"cognition", "closeout-plan", "--workflow", "sp-do", "--scope-dir", ".specify/do/sessions/" + session.ID, "--scope-mode", "explicit", "--format", "json"}
	for _, p := range validation.ChangedSourcePaths {
		args = append(args, "--changed-path", p)
	}
	var stdout, stderr bytes.Buffer
	if code := Run(args, &stdout, &stderr, "test"); code != 0 {
		t.Fatalf("planner %d: %s %s", code, stdout.String(), stderr.String())
	}
	var envelope struct {
		Data closeout.Payload "json:\"data\""
	}
	if err := json.Unmarshal(stdout.Bytes(), &envelope); err != nil || envelope.Data.PayloadDraft == nil {
		t.Fatalf("planner draft missing: %v %s", err, stdout.String())
	}
	draft := envelope.Data.PayloadDraft
	draft.BehaviorSurfaces = []string{"The verified local operation updates the owned source and generated report."}
	draft.GeneratedSurfaceNote = []string{"The required JSON check passed against the actual current report."}
	draft.StateContracts = []string{"Required operation and dependent report checks passed against the final source fingerprint."}
	draft.Verification = []closeout.VerificationRecord{{Command: strings.Join(session.Definition.Steps[0].Argv, " "), Result: "passed", Artifact: doSessionRef(session.ID)}, {Command: "runtime JSON result validation", Result: "passed", Artifact: session.Definition.Checks[0].ResultPath}}
	draft.ConfidenceNotes = []string{"Command exit observations originate from the native tool; runtime independently checks report bytes and source fingerprints."}
	for index := range draft.UnknownPathDispositions {
		disposition := string(changemodel.DispositionAdoptable)
		draft.UnknownPathDispositions[index].AgentDisposition = &disposition
	}
	for index := range draft.PathChanges {
		disposition := changemodel.DispositionAdoptable
		draft.PathChanges[index].Disposition = &disposition
		draft.PathChanges[index].NodeID = "N-source"
		draft.PathChanges[index].EvidenceRefs = []string{draft.PathChanges[index].Path}
	}
	raw, err := json.Marshal(draft)
	if err != nil {
		t.Fatal(err)
	}
	return raw
}

func doApplyCognitionPayload(t *testing.T, root string, session DoSession, payload []byte) (int, Envelope) {
	t.Helper()
	var out bytes.Buffer
	code := runCognitionCloseoutApplyCLIWithInput([]string{"--project-root", root, "--workflow", "sp-do", "--scope-dir", ".specify/do/sessions/" + session.ID, "--payload-json", "-", "--format", "json"}, bytes.NewReader(payload), &out)
	var envelope Envelope
	if err := json.Unmarshal(out.Bytes(), &envelope); err != nil {
		t.Fatalf("decode closeout: %v %s", err, out.String())
	}
	return code, envelope
}

func TestDoSourceMutationFullCognitionRefreshThenPlaybookSaved(t *testing.T) {
	var paths rt.Paths
	root, _, session := doSourceMutationFixtureWithSetup(t, func(root string) { paths = doSeedCognitionBaseline(t, root) })
	payload := doCognitionPlannerPayload(t, root, session)
	code, envelope := doApplyCognitionPayload(t, root, session, payload)
	if code != 0 || envelope.Data["allowed_close"] != true || envelope.Data["closeout_state"] != "ready" || envelope.Data["validation_readiness"] != rt.ReadyReadiness {
		t.Fatalf("full cognition refresh failed: %d %+v", code, envelope)
	}
	status, err := rt.ReadStatus(paths)
	if err != nil || status.LastFinalizedUpdateID == "" || status.LastFinalizedUpdateID != status.LastUpdateID || status.Readiness != rt.ReadyReadiness {
		t.Fatalf("refresh did not finalize: %+v %v", status, err)
	}
	session, digest, err := loadDoSession(root, session.ID)
	if err != nil {
		t.Fatal(err)
	}
	validation := doValidate(root, session, true)
	if validation.Status != "passed" || validation.CognitionCloseout != "ready" {
		t.Fatalf("owner cognition writes invalidated its Do operation: %+v", validation)
	}
	receipt, err := loadMutationCognitionReceipt(filepath.Join(root, ".specify/do/sessions", session.ID))
	if err != nil || receipt.DoBinding == nil || receipt.DoBinding.SourceFingerprint != validation.SourceFingerprint || receipt.IntentDigest == "" {
		t.Fatalf("receipt did not preserve its pre-update source basis: %+v %v", receipt, err)
	}
	workStore, err := runcontrol.OpenForRepository(context.Background(), root)
	if err != nil {
		t.Fatal(err)
	}
	_, intents, err := workStore.GetWork(context.Background(), session.WorkID)
	_ = workStore.Close()
	if err != nil {
		t.Fatal(err)
	}
	claimed := map[string]bool{}
	for _, intent := range intents {
		claimed[intent.Path] = true
	}
	for _, p := range []string{".specify/project-cognition/project-cognition.db", ".specify/project-cognition/status.json", ".specify/project-cognition/validate-build-receipt.json"} {
		if !claimed[p] {
			t.Fatalf("cognition wrote without an exact Work claim: %s", p)
		}
	}
	if claimed[".specify/project-cognition"] || claimed[".specify"] {
		t.Fatal("cognition claimed a whole metadata tree")
	}
	unexpected := filepath.Join(paths.RuntimeDir, "unclaimed.json")
	if err := os.WriteFile(unexpected, []byte("{\"must\":\"not be ignored\"}"), 0o644); err != nil {
		t.Fatal(err)
	}
	if validation := doValidate(root, session, true); validation.Status == "passed" || !strings.Contains(strings.Join(validation.Blockers, " "), "unclaimed.json") {
		t.Fatal("unregistered cognition metadata was silently hidden", validation)
	}
	if err := os.Remove(unexpected); err != nil {
		t.Fatal(err)
	}
	session, err = doFinish(root, session, digest, doFinishInput{ExpectedRevision: session.Revision, KnowledgeStatus: "pending"})
	if err != nil {
		t.Fatal(err)
	}
	published := playbookPublishFixture(t, root, session, "")
	playbookFinishFixture(t, root, session.ID, published)
	finished, _, err := loadDoSession(root, session.ID)
	if err != nil || finished.KnowledgeStatus != "saved" || doValidate(root, finished, true).Status != "passed" {
		t.Fatalf("full source-mutation path failed to save: %+v %v", finished, err)
	}
}

func TestDoCognitionPendingIntentRetainsPreUpdateSourceBinding(t *testing.T) {
	root, _, session := doSourceMutationFixtureWithSetup(t, func(root string) { doSeedCognitionBaseline(t, root) })
	payload := doCognitionPlannerPayload(t, root, session)
	closeoutApplyAfterIntentPersistHook = func(string) error { return errors.New("fixture interruption before graph update") }
	t.Cleanup(func() { closeoutApplyAfterIntentPersistHook = nil })
	code, envelope := doApplyCognitionPayload(t, root, session, payload)
	if code == 0 || envelope.Data["closeout_status"] != "closeout_intent_pending" {
		t.Fatalf("expected a durable pending intent: %+v", envelope)
	}
	paths, _ := rt.ResolvePaths(root)
	intents, err := listCloseoutIntents(paths)
	if err != nil || len(intents) != 1 || intents[0].DoBinding == nil {
		t.Fatalf("intent omitted its pre-update Do binding: %+v %v", intents, err)
	}
	intent := intents[0]
	copy := intent
	copy.DoBinding = nil
	if storedCloseoutIntentDigest(copy) == intent.InputDigest {
		t.Fatal("source basis is absent from the durable intent digest")
	}
	status, _ := rt.ReadStatus(paths)
	if status.LastUpdateID != "" {
		t.Fatal("interrupted pre-update intent unexpectedly changed the graph")
	}
	closeoutApplyAfterIntentPersistHook = nil
	var replay, stderr bytes.Buffer
	code = Run([]string{"cognition", "closeout", "replay", "--project-root", root, "--intent-id", intent.ID, "--expected-digest", intent.InputDigest, "--format", "json"}, &replay, &stderr, "test")
	if err := json.Unmarshal(replay.Bytes(), &envelope); err != nil || code != 0 || envelope.Data["allowed_close"] != true {
		t.Fatalf("same-boundary selected replay did not complete: %v %+v %s", err, envelope, stderr.String())
	}
	receipt, err := loadMutationCognitionReceipt(filepath.Join(root, ".specify/do/sessions", session.ID))
	if err != nil || !reflect.DeepEqual(receipt.DoBinding, intent.DoBinding) || receipt.IntentID != intent.ID {
		t.Fatalf("recovery replaced its historical binding: %+v %v", receipt, err)
	}
}

func TestDoCognitionSameSecondChangedSourceRejectsPriorRefresh(t *testing.T) {
	root, input := doFixture(t)
	doSeedCognitionBaseline(t, root)
	input.WriteScope = []string{"source.txt"}
	session, err := doStart(root, input)
	if err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(root, "source.txt"), []byte("source v2\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	session = doRunFixture(t, root, session)
	payload := doCognitionPlannerPayload(t, root, session)
	code, envelope := doApplyCognitionPayload(t, root, session, payload)
	if code != 0 || envelope.Data["allowed_close"] != true {
		t.Fatalf("first refresh failed: %+v", envelope)
	}
	scope := filepath.Join(root, ".specify/do/sessions", session.ID)
	receipt, err := loadMutationCognitionReceipt(scope)
	if err != nil {
		t.Fatal(err)
	}
	old := *receipt
	old.DoBinding = nil
	if _, err := writeMutationCognitionReceipt(scope, old); err != nil {
		t.Fatal(err)
	}
	session, _, _ = loadDoSession(root, session.ID)
	if validation := doValidate(root, session, true); validation.Status == "passed" || !strings.Contains(strings.Join(validation.Blockers, " "), "pre-update Do source binding") {
		t.Fatal("legacy unbound receipt passed", validation)
	}
	if _, err := recordMutationCognitionReceiptWithPaths(scope, "sp-do", ".specify/do/sessions/"+session.ID, "ready", "attempt to relabel a previous update", receipt.UpdateID, receipt.Evidence, receipt.ChangedPaths); err == nil {
		t.Fatal("manual receipt late-bound an old update to current source")
	}
	if _, err := writeMutationCognitionReceipt(scope, *receipt); err != nil {
		t.Fatal(err)
	}
	stamp, err := time.Parse(time.RFC3339, receipt.RecordedAt)
	if err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(root, "source.txt"), []byte("source v3\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	if err := os.Chtimes(filepath.Join(root, "source.txt"), stamp, stamp); err != nil {
		t.Fatal(err)
	}
	session = doRecordFixture(t, root, session, "new-source-start", doRecordEvent{AttemptID: "run-2", TargetID: "run", Kind: "step", Event: "started"})
	started := doNow()
	command := exec.Command("git", "--version")
	command.Dir = root
	if _, err := command.Output(); err != nil {
		t.Fatal(err)
	}
	zero := 0
	session = doRecordFixture(t, root, session, "new-source-complete", doRecordEvent{AttemptID: "run-2", TargetID: "run", Kind: "step", Event: "completed", Status: "passed", EvidenceOrigin: "agent_tool_observation", ToolCallID: "real-git-after-source-change", Argv: []string{"git", "--version"}, Cwd: ".", StartedAt: started, FinishedAt: doNow(), ExitCode: &zero})
	session = doRecordFixture(t, root, session, "new-source-check-start", doRecordEvent{AttemptID: "report-2", TargetID: "report", Kind: "check", Event: "started"})
	now := doNow()
	session = doRecordFixture(t, root, session, "new-source-check-complete", doRecordEvent{AttemptID: "report-2", TargetID: "report", Kind: "check", Event: "completed", Status: "passed", EvidenceOrigin: "agent_tool_observation", ToolCallID: "real-current-report-read", Cwd: ".", StartedAt: now, FinishedAt: now, ResultRefs: []DoResultRef{{Path: "out/report.json", Kind: "json"}}})
	if validation := doValidate(root, session, false); validation.Status != "passed" {
		t.Fatalf("fresh operation/check evidence must be valid for the new source: %+v", validation)
	}
	if validation := doValidate(root, session, true); validation.Status == "passed" || !strings.Contains(strings.Join(validation.Blockers, " "), "pre-update Do source binding") {
		t.Fatal("same-second changed source reused an old graph refresh", validation)
	}
	code, envelope = doApplyCognitionPayload(t, root, session, doCognitionPlannerPayload(t, root, session))
	if code != 0 || envelope.Data["allowed_close"] != true {
		t.Fatalf("fresh new-source refresh failed: %+v", envelope)
	}
	session, _, _ = loadDoSession(root, session.ID)
	if validation := doValidate(root, session, true); validation.Status != "passed" {
		t.Fatalf("new bound refresh did not recover: %+v", validation)
	}
}

func TestDoCognitionRefusesChangedSourceBeforeFinalization(t *testing.T) {
	root, _, session := doSourceMutationFixtureWithSetup(t, func(root string) { doSeedCognitionBaseline(t, root) })
	payload := doCognitionPlannerPayload(t, root, session)
	closeoutApplyAfterUpdateHook = func(string) error {
		return os.WriteFile(filepath.Join(root, "source.txt"), []byte("changed while cognition was refreshing\n"), 0o644)
	}
	t.Cleanup(func() { closeoutApplyAfterUpdateHook = nil })
	code, envelope := doApplyCognitionPayload(t, root, session, payload)
	if code == 0 || envelope.Data["allowed_close"] == true {
		t.Fatalf("source changed during graph mutation but closeout claimed success: %+v", envelope)
	}
	paths, _ := rt.ResolvePaths(root)
	status, err := rt.ReadStatus(paths)
	if err != nil || status.LastFinalizedUpdateID != "" {
		t.Fatalf("changed source was published as a finalized refresh: %+v %v", status, err)
	}
	closeoutApplyAfterUpdateHook = nil
	if err := os.WriteFile(filepath.Join(root, "source.txt"), []byte("source v2\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	code, envelope = doApplyCognitionPayload(t, root, session, payload)
	if code != 0 || envelope.Data["allowed_close"] != true {
		t.Fatalf("restore original validated source could not recover the exact intent: %+v", envelope)
	}
}

func TestDoCognitionWorkConflictBlocksBeforeGraphMutation(t *testing.T) {
	root, _, session := doSourceMutationFixtureWithSetup(t, func(root string) { doSeedCognitionBaseline(t, root) })
	payload := doCognitionPlannerPayload(t, root, session)
	workStore, err := runcontrol.OpenForRepository(context.Background(), root)
	if err != nil {
		t.Fatal(err)
	}
	_, _, err = workStore.BeginWork(context.Background(), runcontrol.BeginWorkParams{
		WorkID: "work-other-cognition", TaskRef: "fixture:cognition-owner", Summary: "another real cognition owner", AgentID: "other-agent", AdapterID: "test", WorkspaceRoot: root, NextAction: "refresh owned graph", LeaseUntil: time.Now().UTC().Add(time.Minute),
		WriteIntents: []runcontrol.WriteIntentSpec{{Path: ".specify/project-cognition/project-cognition.db", Operation: runcontrol.WriteModify, Reason: "another graph writer", Confidence: runcontrol.IntentConfirmed}},
	})
	_ = workStore.Close()
	if err != nil {
		t.Fatal(err)
	}
	code, envelope := doApplyCognitionPayload(t, root, session, payload)
	if code == 0 || envelope.Data["mutation_performed"] != false {
		t.Fatalf("conflicting Work was ignored: %+v", envelope)
	}
	paths, _ := rt.ResolvePaths(root)
	status, err := rt.ReadStatus(paths)
	if err != nil || status.LastUpdateID != "" {
		t.Fatalf("graph mutated before acquiring its exact Work ownership: %+v %v", status, err)
	}
	intents, err := listCloseoutIntents(paths)
	if err != nil || len(intents) != 0 {
		t.Fatalf("ownership rejection left a mutation intent: %+v %v", intents, err)
	}
}

func TestDoCognitionReceiptCrashMustReplayBeforeWorkRelease(t *testing.T) {
	root, _, session := doSourceMutationFixtureWithSetup(t, func(root string) { doSeedCognitionBaseline(t, root) })
	payload := doCognitionPlannerPayload(t, root, session)
	closeoutApplyAfterScopeReceiptHook = func(string) error {
		return errors.New("fixture crash after ready receipt but before intent cleanup")
	}
	t.Cleanup(func() { closeoutApplyAfterScopeReceiptHook = nil })
	code, envelope := doApplyCognitionPayload(t, root, session, payload)
	if code == 0 {
		t.Fatalf("expected receipt-before-cleanup interruption: %+v", envelope)
	}
	scope := filepath.Join(root, ".specify/do/sessions", session.ID)
	if gate := mutationCognitionStatus(scope); gate["allowed_close"] != true || gate["result_state"] != "ready" {
		t.Fatalf("fixture did not hit the durable-ready-receipt window: %+v", gate)
	}
	session, digest, err := loadDoSession(root, session.ID)
	if err != nil {
		t.Fatal(err)
	}
	if _, err := doFinish(root, session, digest, doFinishInput{ExpectedRevision: session.Revision, KnowledgeStatus: "pending"}); err == nil || !strings.Contains(err.Error(), "remains pending") {
		t.Fatalf("Do finished before its exact cognition recovery record was cleaned: %v", err)
	}
	paths, _ := rt.ResolvePaths(root)
	intents, err := listCloseoutIntents(paths)
	if err != nil || len(intents) != 1 {
		t.Fatalf("exact pending recovery intent disappeared: %+v %v", intents, err)
	}
	intent := intents[0]
	validation := doValidate(root, session, false)
	if _, err := recordMutationCognitionReceiptWithPaths(scope, "sp-do", ".specify/do/sessions/"+session.ID, "mark-dirty", "explicit debt must not hide pending owner recovery", "", validation.ChangedSourcePaths, validation.ChangedSourcePaths); err != nil {
		t.Fatal(err)
	}
	if validation := doValidate(root, session, true); validation.Status == "passed" || !strings.Contains(strings.Join(validation.Blockers, " "), "remains pending") {
		t.Fatalf("replacing the receipt hid the pending cognition intent: %+v", validation)
	}
	closeoutApplyAfterScopeReceiptHook = nil
	var replay, stderr bytes.Buffer
	code = Run([]string{"cognition", "closeout", "replay", "--project-root", root, "--intent-id", intent.ID, "--expected-digest", intent.InputDigest, "--format", "json"}, &replay, &stderr, "test")
	if err := json.Unmarshal(replay.Bytes(), &envelope); err != nil || code != 0 || envelope.Data["allowed_close"] != true {
		t.Fatalf("exact recovery could not retain its active Work and finish: %v %+v %s", err, envelope, stderr.String())
	}
	session, digest, err = loadDoSession(root, session.ID)
	if err != nil {
		t.Fatal(err)
	}
	session, err = doFinish(root, session, digest, doFinishInput{ExpectedRevision: session.Revision, KnowledgeStatus: "pending"})
	if err != nil {
		t.Fatal(err)
	}
	published := playbookPublishFixture(t, root, session, "")
	playbookFinishFixture(t, root, session.ID, published)
}

func TestDoCognitionPendingIntentBlocksAfterSourceReturnsToBaseline(t *testing.T) {
	root, input := doFixture(t)
	doSeedCognitionBaseline(t, root)
	input.WriteScope = []string{"source.txt"}
	session, err := doStart(root, input)
	if err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(root, "source.txt"), []byte("source v2\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	session = doRunFixture(t, root, session)
	payload := doCognitionPlannerPayload(t, root, session)
	closeoutApplyAfterScopeReceiptHook = func(string) error { return errors.New("fixture crash before intent cleanup") }
	t.Cleanup(func() { closeoutApplyAfterScopeReceiptHook = nil })
	if code, envelope := doApplyCognitionPayload(t, root, session, payload); code == 0 {
		t.Fatalf("expected the pending receipt window: %+v", envelope)
	}
	closeoutApplyAfterScopeReceiptHook = nil
	if err := os.WriteFile(filepath.Join(root, "source.txt"), []byte("source v1\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	session, _, err = loadDoSession(root, session.ID)
	if err != nil {
		t.Fatal(err)
	}
	session = doRecordFixture(t, root, session, "restored-source-start", doRecordEvent{AttemptID: "run-restored", TargetID: "run", Kind: "step", Event: "started"})
	started := doNow()
	command := exec.Command("git", "--version")
	command.Dir = root
	if _, err := command.Output(); err != nil {
		t.Fatal(err)
	}
	zero := 0
	session = doRecordFixture(t, root, session, "restored-source-complete", doRecordEvent{AttemptID: "run-restored", TargetID: "run", Kind: "step", Event: "completed", Status: "passed", EvidenceOrigin: "agent_tool_observation", ToolCallID: "real-git-restored-baseline", Argv: []string{"git", "--version"}, Cwd: ".", StartedAt: started, FinishedAt: doNow(), ExitCode: &zero})
	session = doRecordFixture(t, root, session, "restored-source-check-start", doRecordEvent{AttemptID: "report-restored", TargetID: "report", Kind: "check", Event: "started"})
	now := doNow()
	session = doRecordFixture(t, root, session, "restored-source-check-complete", doRecordEvent{AttemptID: "report-restored", TargetID: "report", Kind: "check", Event: "completed", Status: "passed", EvidenceOrigin: "agent_tool_observation", ToolCallID: "real-report-restored-baseline", Cwd: ".", StartedAt: now, FinishedAt: now, ResultRefs: []DoResultRef{{Path: "out/report.json", Kind: "json"}}})
	if validation := doValidate(root, session, false); validation.Status != "passed" || len(validation.ChangedSourcePaths) != 0 {
		t.Fatalf("fixture must have fresh passed execution with zero net source changes: %+v", validation)
	}
	_, digest, err := loadDoSession(root, session.ID)
	if err != nil {
		t.Fatal(err)
	}
	if _, err := doFinish(root, session, digest, doFinishInput{ExpectedRevision: session.Revision, KnowledgeStatus: "not_applicable"}); err == nil || !strings.Contains(err.Error(), "remains pending") {
		t.Fatalf("returning source to baseline released Work with a pending cognition intent: %v", err)
	}
}

func TestDoReadOnlyOperationDoesNotAcquireUnrelatedCognitionRecovery(t *testing.T) {
	root, input := doFixture(t)
	dir := filepath.Join(root, ".specify/project-cognition/closeout-intents")
	if err := os.MkdirAll(dir, 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(dir, "intent-000000000000000000000000.json"), []byte("{\"foreign\":\"pre-existing invalid intent\"}"), 0o644); err != nil {
		t.Fatal(err)
	}
	session, err := doStart(root, input)
	if err != nil {
		t.Fatal(err)
	}
	session = doRunFixture(t, root, session)
	if validation := doValidate(root, session, true); validation.Status != "passed" || validation.CognitionCloseout != "not_applicable" {
		t.Fatalf("an unrelated cognition recovery was imposed on a read/output-only operation: %+v", validation)
	}
}
