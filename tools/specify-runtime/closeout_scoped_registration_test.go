package main

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"

	changemodel "github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/changes/model"
	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/claim"
	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/delta"
	rt "github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/runtime"
	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/scopedregistration"
)

func TestR4CloseoutApplyScopedRegistrationMergesIntoParentUpdateAndPublicQueries(t *testing.T) {
	root, session, payload := r4CloseoutScopedFixture(t)
	beforeUpdates := r4CloseoutUpdateCount(t, root)

	code, envelope := r4RunCloseoutApply(t, root, session, payload)
	if code != 0 || envelope.Status != "ok" {
		t.Fatalf("closeout apply with scoped registration failed: code=%d envelope=%+v", code, envelope)
	}
	updateID := stringValue(envelope.Data["update_id"])
	if updateID == "" {
		t.Fatalf("closeout apply did not expose parent update id: %+v", envelope.Data)
	}
	if got := r4CloseoutUpdateCount(t, root); got != beforeUpdates+1 {
		t.Fatalf("closeout apply wrote %d update rows, want exactly one parent update row after %d", got, beforeUpdates)
	}

	attrs := r4CloseoutUpdateAttrs(t, root, updateID)
	if stringValue(attrs["closeout_intent_id"]) == "" {
		t.Fatalf("parent update attrs missing closeout intent binding: %#v", attrs)
	}
	scoped := r4MapValue(t, attrs["scoped_registration"])
	if scoped["receipt"] == nil || scoped["scoped_registration_result"] == nil {
		t.Fatalf("parent update did not carry scoped registration receipt/result: %#v", scoped)
	}
	beforeReplayAttrsJSON := r4CloseoutUpdateAttrsJSON(t, root, updateID)
	nativeProof := r4MapValue(t, scoped["native_proof"])
	if stringValue(nativeProof["kind"]) != "do_native" || stringValue(nativeProof["parent_update_id"]) != updateID || stringValue(nativeProof["parent_intent_id"]) != stringValue(attrs["closeout_intent_id"]) {
		t.Fatalf("scoped native proof did not bind parent journal identity: %#v parent_attrs=%#v", nativeProof, attrs)
	}
	registered := mapStringSlices(t, r4MapValue(t, scoped["receipt"])["registered"])
	if !containsAll(registered["nodes"], []string{r4CloseoutScopedID("N", "report-owner")}) || !containsAll(registered["claims"], []string{r4CloseoutScopedID("C", "report-current")}) {
		t.Fatalf("scoped receipt missing registered owner/claim rows: %#v", registered)
	}

	st := r4OpenStore(t, root)
	mapped, err := st.NodeIDsForExactPaths(context.Background(), []string{"generated/report.json", "source.txt"})
	st.Close()
	if err != nil {
		t.Fatal(err)
	}
	if mapped["generated/report.json"] != r4CloseoutScopedID("N", "report-owner") || mapped["source.txt"] != "N-source" {
		t.Fatalf("store path query did not consume parent scoped rows while preserving source owner: %#v", mapped)
	}
	r4AssertPublicNavigationConsumesNode(t, root, "generated/report.json", r4CloseoutScopedID("N", "report-owner"), "R4 Do Generated Report")

	replayCode, replay := r4RunCloseoutApply(t, root, session, payload)
	if replayCode == 0 {
		if replay.Status != "ok" || replay.Data["replayed_completed"] != true || stringValue(replay.Data["update_id"]) != updateID {
			t.Fatalf("completed apply replay success must be truthful idempotent replay of the same parent receipt: code=%d envelope=%+v", replayCode, replay)
		}
	} else if replay.Status != "blocked" || !strings.Contains(fmt.Sprint(replay.Data["error"]), "completed closeout intent requires exact replay") {
		t.Fatalf("completed apply replay should either reuse the same receipt or refuse rewriting it: code=%d envelope=%+v", replayCode, replay)
	}
	if got := r4CloseoutUpdateCount(t, root); got != beforeUpdates+1 {
		t.Fatalf("completed replay inserted duplicate parent updates: got %d want %d", got, beforeUpdates+1)
	}
	if afterReplayAttrsJSON := r4CloseoutUpdateAttrsJSON(t, root, updateID); afterReplayAttrsJSON != beforeReplayAttrsJSON {
		t.Fatalf("completed replay rewrote canonical parent receipt attrs:\nbefore=%s\nafter=%s", beforeReplayAttrsJSON, afterReplayAttrsJSON)
	}
}

func TestR4CloseoutApplyScopedRegistrationInterruptedAfterUpdateRecoversSameParent(t *testing.T) {
	root, session, payload := r4CloseoutScopedFixture(t)
	var interruptedUpdateID string
	closeoutApplyAfterUpdateHook = func(updateID string) error {
		interruptedUpdateID = updateID
		return fmt.Errorf("r4 test interruption after parent update before scoped registration")
	}
	code, interrupted := r4RunCloseoutApply(t, root, session, payload)
	closeoutApplyAfterUpdateHook = nil
	if code == 0 || interrupted.Status != "blocked" || interruptedUpdateID == "" {
		t.Fatalf("after-update interruption did not leave a durable parent update: code=%d envelope=%+v update=%q", code, interrupted, interruptedUpdateID)
	}
	if got := r4CloseoutScopedReceiptForUpdate(t, root, interruptedUpdateID); got != nil {
		t.Fatalf("interrupted run published scoped registration before recovery: %#v", got)
	}
	beforeUpdates := r4CloseoutUpdateCount(t, root)

	code, recovered := r4RunCloseoutApply(t, root, session, payload)
	if code != 0 || recovered.Status != "ok" {
		t.Fatalf("same-source replay did not recover interrupted scoped registration: code=%d envelope=%+v", code, recovered)
	}
	if stringValue(recovered.Data["update_id"]) != interruptedUpdateID || recovered.Data["resumed_from_intent"] != true {
		t.Fatalf("recovery did not resume the same parent update: interrupted=%s envelope=%+v", interruptedUpdateID, recovered.Data)
	}
	if got := r4CloseoutUpdateCount(t, root); got != beforeUpdates {
		t.Fatalf("recovery inserted duplicate parent update rows: got %d want %d", got, beforeUpdates)
	}
	scoped := r4CloseoutScopedReceiptForUpdate(t, root, interruptedUpdateID)
	if scoped == nil {
		t.Fatal("recovery did not publish scoped registration onto the interrupted parent update")
	}
	nativeProof := r4MapValue(t, scoped["native_proof"])
	if stringValue(nativeProof["parent_update_id"]) != interruptedUpdateID {
		t.Fatalf("recovered scoped registration lost parent update binding: %#v", nativeProof)
	}
}

func TestR4CloseoutApplyScopedRegistrationInterruptedSourceDriftRefusesRecovery(t *testing.T) {
	root, session, payload := r4CloseoutScopedFixture(t)
	var interruptedUpdateID string
	closeoutApplyAfterUpdateHook = func(updateID string) error {
		interruptedUpdateID = updateID
		return fmt.Errorf("r4 test interruption before scoped registration")
	}
	code, interrupted := r4RunCloseoutApply(t, root, session, payload)
	closeoutApplyAfterUpdateHook = nil
	if code == 0 || interruptedUpdateID == "" {
		t.Fatalf("interruption setup failed: code=%d envelope=%+v", code, interrupted)
	}
	if err := os.WriteFile(filepath.Join(root, "generated", "report.json"), []byte("{\"ok\":false,\"drift\":true}\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	beforeUpdates := r4CloseoutUpdateCount(t, root)

	code, drift := r4RunCloseoutApply(t, root, session, payload)
	if code == 0 || drift.Status != "blocked" {
		t.Fatalf("source drift after parent update recovered as success: code=%d envelope=%+v", code, drift)
	}
	joined := fmt.Sprint(drift.Data) + " " + r4JoinedBlockers(drift)
	if !strings.Contains(joined, "source") && !strings.Contains(joined, "binding") {
		t.Fatalf("drift refusal did not explain stale source/binding: %+v", drift)
	}
	if got := r4CloseoutUpdateCount(t, root); got != beforeUpdates {
		t.Fatalf("drift retry inserted duplicate update rows: got %d want %d", got, beforeUpdates)
	}
	if scoped := r4CloseoutScopedReceiptForUpdate(t, root, interruptedUpdateID); scoped != nil {
		t.Fatalf("drift retry published scoped registration despite changed source: %#v", scoped)
	}
}

func TestR4CloseoutApplyScopedRegistrationDraftRejectsCallerProofFieldsAndLosslessAttrs(t *testing.T) {
	root, session, payload := r4CloseoutScopedFixture(t)
	var raw map[string]any
	decoder := json.NewDecoder(bytes.NewReader(payload))
	decoder.UseNumber()
	if err := decoder.Decode(&raw); err != nil {
		t.Fatal(err)
	}
	draft := r4MapValue(t, raw["scoped_registration"])
	draft["proof"] = map[string]any{"kind": "caller_fabricated", "source_revision": "fake"}
	draft["work"] = map[string]any{"work_id": "fake"}
	draft["source"] = map[string]any{"source_revision": "fake"}
	mutated, err := json.Marshal(raw)
	if err != nil {
		t.Fatal(err)
	}
	code, envelope := r4RunCloseoutApply(t, root, session, mutated)
	if code == 0 || envelope.Status != "blocked" || !strings.Contains(fmt.Sprint(envelope.Data["error"]), "unknown field") {
		t.Fatalf("draft accepted caller-owned proof/work/source fields: code=%d envelope=%+v", code, envelope)
	}

	root, session, payload = r4CloseoutScopedFixture(t)
	payload = r4CloseoutPayloadWithBigAttr(t, payload)
	code, envelope = r4RunCloseoutApply(t, root, session, payload)
	if code != 0 || envelope.Status != "ok" {
		t.Fatalf("lossless attr payload failed: code=%d envelope=%+v", code, envelope)
	}
	updateID := stringValue(envelope.Data["update_id"])
	attrs := r4CloseoutUpdateAttrs(t, root, updateID)
	scoped := r4MapValue(t, attrs["scoped_registration"])
	if digest := stringValue(scoped["packet_sha256"]); digest == "" {
		t.Fatalf("scoped registration attrs missing canonical request digest: %#v", scoped)
	}
	receipt := r4MapValue(t, scoped["receipt"])
	if status := stringValue(receipt["status"]); status == "" {
		t.Fatalf("scoped registration attrs missing compact receipt status: %#v", receipt)
	}

	bigNumber := []byte("9007199254740993123456789")
	r4AssertStoredScopedAttrContains(t, root, "evidence", r4CloseoutScopedID("E", "report-source"), bigNumber)
	r4AssertStoredScopedAttrContains(t, root, "nodes", r4CloseoutScopedID("N", "report-owner"), bigNumber)
	r4AssertPublicScopedAttrRoutesPreserveBigNumber(t, root, "generated/report.json", r4CloseoutScopedID("N", "report-owner"), "R4 Do Generated Report", bigNumber)

	beforeReplayCount := r4CloseoutUpdateCount(t, root)
	beforeReplayAttrsJSON := r4CloseoutUpdateAttrsJSON(t, root, updateID)
	code, replay := r4RunCloseoutApply(t, root, session, payload)
	if code != 0 || replay.Status != "ok" || replay.Data["replayed_completed"] != true || stringValue(replay.Data["update_id"]) != updateID {
		t.Fatalf("lossless attr replay did not reuse the same parent update: code=%d envelope=%+v", code, replay)
	}
	if got := r4CloseoutUpdateCount(t, root); got != beforeReplayCount {
		t.Fatalf("lossless attr replay inserted duplicate updates: got %d want %d", got, beforeReplayCount)
	}
	if afterReplayAttrsJSON := r4CloseoutUpdateAttrsJSON(t, root, updateID); afterReplayAttrsJSON != beforeReplayAttrsJSON {
		t.Fatalf("lossless attr replay rewrote canonical parent receipt attrs:\nbefore=%s\nafter=%s", beforeReplayAttrsJSON, afterReplayAttrsJSON)
	}
	replayAttrs := r4CloseoutUpdateAttrs(t, root, stringValue(replay.Data["update_id"]))
	replayScoped := r4MapValue(t, replayAttrs["scoped_registration"])
	if !r4SameJSONValue(scoped["packet_sha256"], replayScoped["packet_sha256"]) {
		t.Fatalf("lossless attr replay changed canonical registration identity: original=%+v replay=%+v", envelope.Data, replay.Data)
	}
}

func TestR4CloseoutApplyDeltaSessionRegistrationJSONMergesAndReplays(t *testing.T) {
	root, session, deltaSession, draft := r4CloseoutScopedDeltaFixture(t)
	beforeUpdates := r4CloseoutUpdateCount(t, root)

	code, envelope := r4RunCloseoutApplyDeltaRegistration(t, root, session, deltaSession, draft)
	if code != 0 || envelope.Status != "ok" {
		t.Fatalf("delta closeout scoped registration failed: code=%d envelope=%+v", code, envelope)
	}
	updateID := stringValue(envelope.Data["update_id"])
	if updateID == "" {
		t.Fatalf("delta closeout did not expose update id: %+v", envelope.Data)
	}
	if got := r4CloseoutUpdateCount(t, root); got != beforeUpdates+1 {
		t.Fatalf("delta closeout wrote %d update rows, want one parent row after %d", got, beforeUpdates)
	}
	attrs := r4CloseoutUpdateAttrs(t, root, updateID)
	scoped := r4MapValue(t, attrs["scoped_registration"])
	nativeProof := r4MapValue(t, scoped["native_proof"])
	if stringValue(nativeProof["parent_update_id"]) != updateID || stringValue(nativeProof["parent_intent_id"]) != stringValue(attrs["closeout_intent_id"]) {
		t.Fatalf("delta scoped registration did not bind parent update/intent: native=%#v attrs=%#v", nativeProof, attrs)
	}
	registered := mapStringSlices(t, r4MapValue(t, scoped["receipt"])["registered"])
	if !containsAll(registered["nodes"], []string{r4CloseoutScopedID("N", "report-owner")}) {
		t.Fatalf("delta scoped registration missing report owner row: %#v", registered)
	}
	r4AssertPublicNavigationConsumesNode(t, root, "generated/report.json", r4CloseoutScopedID("N", "report-owner"), "R4 Do Generated Report")

	beforeReplayAttrsJSON := r4CloseoutUpdateAttrsJSON(t, root, updateID)
	replayCode, replay := r4RunCloseoutApplyDeltaRegistration(t, root, session, deltaSession, draft)
	if replayCode == 0 {
		if replay.Status != "ok" || replay.Data["replayed_completed"] != true || stringValue(replay.Data["update_id"]) != updateID {
			t.Fatalf("delta replay success must be truthful idempotent replay of the same parent receipt: code=%d envelope=%+v", replayCode, replay)
		}
	} else if replay.Status != "blocked" || !strings.Contains(fmt.Sprint(replay.Data["error"]), "completed closeout intent requires exact replay") {
		t.Fatalf("delta replay should either reuse the same receipt or refuse rewriting it: code=%d envelope=%+v", replayCode, replay)
	}
	if got := r4CloseoutUpdateCount(t, root); got != beforeUpdates+1 {
		t.Fatalf("delta replay inserted duplicate updates: got %d want %d", got, beforeUpdates+1)
	}
	if afterReplayAttrsJSON := r4CloseoutUpdateAttrsJSON(t, root, updateID); afterReplayAttrsJSON != beforeReplayAttrsJSON {
		t.Fatalf("delta replay rewrote canonical parent receipt attrs:\nbefore=%s\nafter=%s", beforeReplayAttrsJSON, afterReplayAttrsJSON)
	}
}

func TestR4CloseoutApplyRegistrationJSONStdinConflictRefusesBeforeMutation(t *testing.T) {
	root, session, _, draft := r4CloseoutScopedDeltaFixture(t)
	beforeUpdates := r4CloseoutUpdateCount(t, root)
	beforeIntents := r4CloseoutIntentCount(t, root)
	reader := &r4FailingReader{}
	var out bytes.Buffer
	code := runCognitionCloseoutApplyCLIWithInput([]string{"--project-root", root, "--workflow", "sp-do", "--scope-dir", ".specify/do/sessions/" + session.ID, "--payload-json", "-", "--registration-json", "-", "--format", "json"}, reader, &out)
	_ = draft
	var envelope Envelope
	if err := json.Unmarshal(out.Bytes(), &envelope); err != nil {
		t.Fatalf("decode stdin conflict output: %v\n%s", err, out.String())
	}
	if reader.reads != 0 {
		t.Fatalf("dual stdin conflict read stdin %d times before refusing", reader.reads)
	}
	if code == 0 || envelope.Status != "blocked" || !strings.Contains(fmt.Sprint(envelope.Data["error"]), "requires delta mode") {
		t.Fatalf("dual stdin payload/registration was not explicitly refused before read: code=%d envelope=%+v", code, envelope)
	}
	if got := r4CloseoutUpdateCount(t, root); got != beforeUpdates {
		t.Fatalf("stdin conflict mutated updates: got %d want %d", got, beforeUpdates)
	}
	if got := r4CloseoutIntentCount(t, root); got != beforeIntents {
		t.Fatalf("stdin conflict persisted intents: got %d want %d", got, beforeIntents)
	}
}

func TestR4CloseoutApplyRegistrationJSONMalformedDraftRefusesBeforeIntent(t *testing.T) {
	root, session, deltaSession, _ := r4CloseoutScopedDeltaFixture(t)
	beforeUpdates := r4CloseoutUpdateCount(t, root)
	beforeIntents := r4CloseoutIntentCount(t, root)
	badDraft := []byte(`{"schema":"unsupported-scoped-registration-draft.v9","delta":{},"result":{"state":"registered"}}`)
	code, envelope := r4RunCloseoutApplyDeltaRegistration(t, root, session, deltaSession, badDraft)
	if code == 0 || envelope.Status != "blocked" || !strings.Contains(fmt.Sprint(envelope.Data["error"]), "scoped_registration schema") {
		t.Fatalf("unsupported registration draft was not refused before intent: code=%d envelope=%+v", code, envelope)
	}
	if got := r4CloseoutUpdateCount(t, root); got != beforeUpdates {
		t.Fatalf("unsupported registration draft mutated updates: got %d want %d", got, beforeUpdates)
	}
	if got := r4CloseoutIntentCount(t, root); got != beforeIntents {
		t.Fatalf("unsupported registration draft persisted intents: got %d want %d", got, beforeIntents)
	}
}

func TestR4CloseoutApplyRegistrationJSONRejectsCallerProofFieldsBeforeIntent(t *testing.T) {
	root, session, deltaSession, draft := r4CloseoutScopedDeltaFixture(t)
	beforeUpdates := r4CloseoutUpdateCount(t, root)
	beforeIntents := r4CloseoutIntentCount(t, root)
	var raw map[string]any
	decoder := json.NewDecoder(bytes.NewReader(draft))
	decoder.UseNumber()
	if err := decoder.Decode(&raw); err != nil {
		t.Fatal(err)
	}
	raw["proof"] = map[string]any{"kind": "caller_fabricated", "source_revision": "fake"}
	raw["work"] = map[string]any{"work_id": "fake"}
	raw["source"] = map[string]any{"source_revision": "fake"}
	mutated, err := json.Marshal(raw)
	if err != nil {
		t.Fatal(err)
	}
	code, envelope := r4RunCloseoutApplyDeltaRegistration(t, root, session, deltaSession, mutated)
	if code == 0 || envelope.Status != "blocked" || !strings.Contains(fmt.Sprint(envelope.Data["error"]), "unknown field") {
		t.Fatalf("registration-json draft accepted caller proof/work/source fields: code=%d envelope=%+v", code, envelope)
	}
	if got := r4CloseoutUpdateCount(t, root); got != beforeUpdates {
		t.Fatalf("caller proof draft mutated updates: got %d want %d", got, beforeUpdates)
	}
	if got := r4CloseoutIntentCount(t, root); got != beforeIntents {
		t.Fatalf("caller proof draft persisted intents: got %d want %d", got, beforeIntents)
	}
}

func TestR4CloseoutPlanDeltaRegistrationApplyArgvCarriesBindingPlaceholder(t *testing.T) {
	root, scope, _ := r3BindingFixture(t, "fast")
	paths, err := rt.ResolvePaths(root)
	if err != nil {
		t.Fatal(err)
	}
	deltaSession, err := delta.Begin(delta.BeginInput{Root: root, RuntimeDir: paths.RuntimeDir, OriginCommand: "sp-fast", OriginFeatureDir: scope})
	if err != nil {
		t.Fatal(err)
	}
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
	var stdout, stderr bytes.Buffer
	code := Run([]string{"cognition", "closeout-plan", "--workflow", "sp-fast", "--scope-dir", scope, "--scope-mode", "explicit", "--changed-path", "src/app.go", "--delta-session", deltaSession.SessionID, "--format", "json"}, &stdout, &stderr, "test")
	if code != 0 {
		t.Fatalf("closeout-plan failed: code=%d stderr=%s stdout=%s", code, stderr.String(), stdout.String())
	}
	var envelope Envelope
	if err := json.Unmarshal(stdout.Bytes(), &envelope); err != nil {
		t.Fatalf("decode closeout-plan: %v\n%s", err, stdout.String())
	}
	argv := stringSliceValue(t, envelope.Data["registration_apply_argv"])
	if !containsAll(argv, []string{"--delta-session", deltaSession.SessionID, "--registration-json", "-", "--binding-id", "<binding_id returned by seal>"}) {
		t.Fatalf("registration_apply_argv did not preserve delta registration and sealed binding placeholder: %#v", argv)
	}
	applyArgv := stringSliceValue(t, envelope.Data["apply_argv"])
	if !containsAll(applyArgv, []string{"--binding-id", "<binding_id returned by seal>"}) {
		t.Fatalf("apply_argv lost sealed binding placeholder while registration apply carried it: %#v", applyArgv)
	}
}

func r4CloseoutScopedFixture(t *testing.T) (string, DoSession, []byte) {
	t.Helper()
	var pathsRoot string
	root, _, session := doSourceMutationFixtureWithSetup(t, func(root string) { _ = doSeedCognitionBaseline(t, root); pathsRoot = root })
	if pathsRoot == "" {
		t.Fatal("baseline fixture did not run")
	}
	payload := doCognitionPlannerPayload(t, root, session)
	return root, session, r4CloseoutAddScopedRegistration(t, root, session, payload, r4CloseoutScopedDraft(t, root, session))
}

func r4CloseoutScopedDraft(t *testing.T, root string, session DoSession) closeoutRegistrationDraft {
	t.Helper()
	now := time.Now().UTC().Format(time.RFC3339Nano)
	reportHash := r4FileSHA256(t, root, "generated/report.json")
	sourceHash := r4FileSHA256(t, root, "source.txt")
	sessionHash := r4SHA256Hex([]byte(session.ID + ":" + session.Attempts[0].AfterSourceFingerprint))
	return closeoutRegistrationDraft{
		Schema: closeoutRegistrationDraftSchema,
		Result: scopedregistration.ResultIntent{State: "registered", Reason: "R4 shared closeout scoped registration join test"},
		Delta: scopedregistration.Delta{
			ChangedPaths: []scopedregistration.PathChange{
				{Operation: "modify", Path: "source.txt", NodeID: "N-source", EvidenceRefs: []string{"source-after"}},
				{Operation: "create", Path: "generated/report.json", NodeID: "report-owner", EvidenceRefs: []string{"report-source"}},
			},
			Evidence: []scopedregistration.Evidence{
				{ID: "source-after", SourceKind: "file", SourcePath: "source.txt", CommitSHA: "fixture", Extractor: "r4-closeout-scoped-test", ContentHash: sourceHash},
				{ID: "report-source", SourceKind: "file", SourcePath: "generated/report.json", CommitSHA: "fixture", Extractor: "r4-closeout-scoped-test", ContentHash: reportHash, Attrs: map[string]any{"observed_generation": json.Number("9007199254740993123456789")}},
				{ID: "session-proof", SourceKind: "command_result", SourcePath: doSessionRef(session.ID), CommitSHA: "fixture", Extractor: "r4-closeout-scoped-test", ContentHash: sessionHash, Attrs: map[string]any{"runtime_source_path": doSessionRef(session.ID)}},
			},
			Nodes: []scopedregistration.Node{
				{ID: "report-owner", Type: "generated_output", Title: "R4 Do Generated Report", Confidence: "supported", EvidenceIDs: []string{"report-source", "session-proof"}},
			},
			Edges: []scopedregistration.Edge{
				{ID: "source-produces-report", Type: "produces", SourceID: "N-source", TargetID: "report-owner", Confidence: "supported", EvidenceIDs: []string{"source-after", "report-source"}},
			},
			Claims: []scopedregistration.Claim{
				{ID: "report-current", NodeID: "report-owner", GraphClaimType: "verification", Summary: "The Do source mutation produced generated/report.json and the JSON check passed.", RequestedState: claim.StateVerified, SupportingEvidenceIDs: []string{"report-source", "session-proof"}, Verifications: []claim.Verification{{ID: "report-json-check", Result: claim.VerificationPassed, Command: "Do runtime JSON result validation", EvidenceID: "session-proof", ObservedAt: now}}},
			},
			Aliases:   []scopedregistration.Alias{{ID: "report-alias", Alias: "R4 Do Generated Report", NormalizedAlias: "r4 do generated report", TargetType: "node", TargetID: "report-owner", Source: "closeout_scoped_registration_test", Confidence: "supported", EvidenceID: "report-source"}},
			PathIndex: []scopedregistration.PathIndex{{ID: "report-path", Path: "generated/report.json", NodeID: "report-owner", Relation: "owns", Confidence: "supported", EvidenceID: "report-source"}},
			Obligations: scopedregistration.ObligationSummary{
				Owners:              []string{"generated/report.json"},
				Consumers:           []string{"source.txt produces generated/report.json through the recorded Do operation"},
				Interfaces:          []string{"generated/report.json JSON contract"},
				StateContracts:      []string{"parent update remains the only closeout journal row for this scoped registration"},
				GeneratedChain:      []string{"git apply generate.patch -> generated/report.json"},
				VerificationEntries: []string{"generated/report.json"},
			},
		},
	}
}

func r4CloseoutAddScopedRegistration(t *testing.T, root string, session DoSession, payload []byte, draft closeoutRegistrationDraft) []byte {
	t.Helper()
	var raw map[string]any
	decoder := json.NewDecoder(bytes.NewReader(payload))
	decoder.UseNumber()
	if err := decoder.Decode(&raw); err != nil {
		t.Fatalf("decode planner payload: %v\n%s", err, payload)
	}
	raw["scoped_registration"] = draft
	out, err := json.Marshal(raw)
	if err != nil {
		t.Fatal(err)
	}
	if !bytes.Contains(out, []byte(closeoutRegistrationDraftSchema)) || !bytes.Contains(out, []byte(session.ID)) {
		t.Fatalf("scoped closeout payload lost draft/session binding: %s", out)
	}
	return out
}

func r4AlignCloseoutPayloadPathChangeToScopedOwner(t *testing.T, raw map[string]any) {
	t.Helper()
	items, ok := raw["path_changes"].([]any)
	if !ok {
		t.Fatalf("closeout payload missing path_changes: %#v", raw)
	}
	aligned := false
	for _, item := range items {
		row := r4MapValue(t, item)
		if stringValue(row["path"]) != "generated/report.json" {
			continue
		}
		delete(row, "node_id")
		row["disposition"] = string(changemodel.DispositionReviewOnly)
		row["evidence_refs"] = []any{"report-source"}
		aligned = true
	}
	if dispositions, ok := raw["unknown_path_dispositions"].([]any); ok {
		for _, item := range dispositions {
			row := r4MapValue(t, item)
			if stringValue(row["path"]) == "generated/report.json" {
				row["agent_disposition"] = string(changemodel.DispositionReviewOnly)
			}
		}
	}
	if !aligned {
		t.Fatalf("closeout payload did not contain generated/report.json path change: %#v", raw["path_changes"])
	}
}

func r4AssertStoredScopedAttrContains(t *testing.T, root, table, id string, want []byte) {
	t.Helper()
	if table != "evidence" && table != "nodes" {
		t.Fatalf("unsupported scoped attr table %q", table)
	}
	st := r4OpenStore(t, root)
	defer st.Close()
	var attrsJSON string
	query := fmt.Sprintf("SELECT attrs_json FROM %s WHERE id = ?", table)
	if err := st.DB().QueryRowContext(context.Background(), query, id).Scan(&attrsJSON); err != nil {
		t.Fatalf("read %s attrs for %s: %v", table, id, err)
	}
	if !strings.Contains(attrsJSON, string(want)) {
		t.Fatalf("stored %s attrs for %s lost exact large number precision: %s", table, id, attrsJSON)
	}
}

func r4AssertPublicScopedAttrRoutesPreserveBigNumber(t *testing.T, root, pathValue, nodeID, aliasQuery string, want []byte) {
	t.Helper()
	st := r4OpenStore(t, root)
	generationID, err := st.ActiveGenerationID(context.Background())
	st.Close()
	if err != nil {
		t.Fatal(err)
	}
	conceptID := "concept:" + generationID + ":" + nodeID
	plan := marshalJSONForCLI(t, map[string]any{
		"candidate_universe_version": 2,
		"lexicon_generation_id":      generationID,
		"paths":                      []string{pathValue},
		"selected_concepts":          []string{conceptID},
		"concept_decisions": []map[string]any{{
			"concept_id":       conceptID,
			"decision":         "selected",
			"selection_reason": "R4 closeout scoped registration attr precision must survive public navigation.",
			"confidence":       "high",
			"paths":            []string{pathValue},
		}},
	})
	code, rawQuery := r4RunCognitionRawInRoot(t, root, []string{"cognition", "query", "--intent", "owner", "--query-plan", plan, "--format", "json"})
	if code != 0 {
		t.Fatalf("public query failed for scoped attr route: code=%d output=%s", code, string(rawQuery))
	}
	r4AssertOutputDoesNotLoseBigNumberWhenAttrExposed(t, "public query", rawQuery, want)

	code, compassPayload := r4RunCognitionInRoot(t, root, []string{"cognition", "compass", "--query-plan", plan, "--format", "json"})
	if code != 0 {
		t.Fatalf("public compass failed for scoped attr route: code=%d payload=%#v", code, compassPayload)
	}
	rawCompass, err := json.Marshal(compassPayload)
	if err != nil {
		t.Fatal(err)
	}
	r4AssertOutputDoesNotLoseBigNumberWhenAttrExposed(t, "public compass", rawCompass, want)
	if ref := r4MapValue(t, compassPayload["expansion_ref"]); stringValue(ref["id"]) != "" {
		code, rawExpand := r4RunCognitionRawInRoot(t, root, []string{"cognition", "expand", "--id", stringValue(ref["id"]), "--section", "related_paths", "--format", "json"})
		if code != 0 {
			t.Fatalf("public expand failed for scoped attr route: code=%d output=%s", code, string(rawExpand))
		}
		r4AssertOutputDoesNotLoseBigNumberWhenAttrExposed(t, "public expand", rawExpand, want)
	}

	code, rawAlias := r4RunCognitionRawInRoot(t, root, []string{"cognition", "lexicon", "--intent", "debug", "--mode", "catalog", "--query", aliasQuery, "--limit", "10", "--format", "json"})
	if code != 0 {
		t.Fatalf("public lexicon failed for scoped attr route: code=%d output=%s", code, string(rawAlias))
	}
	r4AssertOutputDoesNotLoseBigNumberWhenAttrExposed(t, "public lexicon", rawAlias, want)
}

func r4AssertOutputDoesNotLoseBigNumberWhenAttrExposed(t *testing.T, route string, raw, want []byte) {
	t.Helper()
	if bytes.Contains(raw, []byte("big_counter")) && !bytes.Contains(raw, want) {
		t.Fatalf("%s exposed scoped attrs but lost exact large number precision: %s", route, string(raw))
	}
}

func r4CloseoutPayloadWithBigAttr(t *testing.T, payload []byte) []byte {
	t.Helper()
	var raw map[string]any
	decoder := json.NewDecoder(bytes.NewReader(payload))
	decoder.UseNumber()
	if err := decoder.Decode(&raw); err != nil {
		t.Fatal(err)
	}
	draft := r4MapValue(t, raw["scoped_registration"])
	delta := r4MapValue(t, draft["delta"])
	evidence, ok := delta["evidence"].([]any)
	if !ok || len(evidence) == 0 {
		t.Fatalf("draft evidence missing: %#v", draft)
	}
	evidenceRow := r4MapValue(t, evidence[0])
	evidenceRow["attrs"] = map[string]any{"big_counter": json.Number("9007199254740993123456789")}
	nodes, ok := delta["nodes"].([]any)
	if !ok || len(nodes) == 0 {
		t.Fatalf("draft nodes missing: %#v", draft)
	}
	nodeRow := r4MapValue(t, nodes[0])
	nodeRow["attrs"] = map[string]any{"big_counter": json.Number("9007199254740993123456789")}
	out, err := json.Marshal(raw)
	if err != nil {
		t.Fatal(err)
	}
	if !bytes.Contains(out, []byte("9007199254740993123456789")) {
		t.Fatalf("raw big number missing before runtime: %s", out)
	}
	return out
}

func r4RunCloseoutApply(t *testing.T, root string, session DoSession, payload []byte) (int, Envelope) {
	t.Helper()
	var out bytes.Buffer
	code := runCognitionCloseoutApplyCLIWithInput([]string{"--project-root", root, "--workflow", "sp-do", "--scope-dir", ".specify/do/sessions/" + session.ID, "--payload-json", "-", "--format", "json", "--verbose"}, bytes.NewReader(payload), &out)
	var envelope Envelope
	if err := json.Unmarshal(out.Bytes(), &envelope); err != nil {
		t.Fatalf("decode closeout apply output: %v\n%s", err, out.String())
	}
	return code, envelope
}

func r4CloseoutUpdateCount(t *testing.T, root string) int {
	t.Helper()
	st := r4OpenStore(t, root)
	defer st.Close()
	return countRows(t, st, "updates")
}

func r4CloseoutUpdateAttrsJSON(t *testing.T, root, updateID string) string {
	t.Helper()
	st := r4OpenStore(t, root)
	defer st.Close()
	var raw string
	if err := st.DB().QueryRowContext(context.Background(), `SELECT attrs_json FROM updates WHERE id = ?`, updateID).Scan(&raw); err != nil {
		t.Fatal(err)
	}
	return raw
}

func r4CloseoutUpdateAttrs(t *testing.T, root, updateID string) map[string]any {
	t.Helper()
	raw := r4CloseoutUpdateAttrsJSON(t, root, updateID)
	var attrs map[string]any
	decoder := json.NewDecoder(strings.NewReader(raw))
	decoder.UseNumber()
	if err := decoder.Decode(&attrs); err != nil {
		t.Fatalf("decode update attrs: %v\n%s", err, raw)
	}
	return attrs
}

func r4CloseoutScopedReceiptForUpdate(t *testing.T, root, updateID string) map[string]any {
	t.Helper()
	attrs := r4CloseoutUpdateAttrs(t, root, updateID)
	if scoped, ok := attrs["scoped_registration"].(map[string]any); ok {
		return scoped
	}
	return nil
}

func r4CloseoutScopedID(kind, local string) string {
	return kind + "-scoped-" + closeoutIntentDigest(closeoutRegistrationDraftSchema, kind, local)[:24]
}

func r4CloseoutScopedDeltaFixture(t *testing.T) (string, DoSession, string, []byte) {
	t.Helper()
	root, session, _ := r4CloseoutScopedFixture(t)
	paths, err := rt.ResolvePaths(root)
	if err != nil {
		t.Fatal(err)
	}
	deltaSession, err := delta.Begin(delta.BeginInput{Root: root, RuntimeDir: paths.RuntimeDir, OriginCommand: "sp-do", OriginFeatureDir: ".specify/do/sessions/" + session.ID})
	if err != nil {
		t.Fatal(err)
	}
	sourceDisposition := changemodel.DispositionAdoptable
	reportDisposition := changemodel.DispositionAdoptable
	if _, err := delta.Append(delta.AppendInput{
		RuntimeDir:   paths.RuntimeDir,
		SessionID:    deltaSession.SessionID,
		EventType:    "workflow_closeout",
		ChangedPaths: []string{"source.txt", "generated/report.json"},
		PathChanges: []changemodel.PathChange{
			{Operation: changemodel.OperationModify, Path: "source.txt", NodeID: "N-source", Disposition: &sourceDisposition, EvidenceRefs: []string{"source.txt"}},
			{Operation: changemodel.OperationAdd, Path: "generated/report.json", Disposition: &reportDisposition, EvidenceRefs: []string{"report-source"}},
		},
		BehaviorSurfaces: []string{"The Do source mutation updates source.txt and creates generated/report.json."},
		OwnerConsumers:   []string{"generated/report.json is consumed through R4 scoped public query/navigation."},
		Verification:     []string{`{"command":"Do runtime JSON result validation","result":"passed","artifact":"generated/report.json"}`},
		Confidence:       "high",
	}); err != nil {
		t.Fatal(err)
	}
	draft, err := json.Marshal(r4CloseoutScopedDraft(t, root, session))
	if err != nil {
		t.Fatal(err)
	}
	if !bytes.Contains(draft, []byte(closeoutRegistrationDraftSchema)) || bytes.Contains(draft, []byte(`"scoped_registration"`)) {
		t.Fatalf("registration-json draft shape must be raw schema/delta/result only: %s", draft)
	}
	return root, session, deltaSession.SessionID, draft
}

func r4RunCloseoutApplyDeltaRegistration(t *testing.T, root string, session DoSession, deltaSession string, draft []byte) (int, Envelope) {
	t.Helper()
	var out bytes.Buffer
	code := runCognitionCloseoutApplyCLIWithInput([]string{"--project-root", root, "--workflow", "sp-do", "--scope-dir", ".specify/do/sessions/" + session.ID, "--delta-session", deltaSession, "--registration-json", "-", "--format", "json", "--verbose"}, bytes.NewReader(draft), &out)
	var envelope Envelope
	if err := json.Unmarshal(out.Bytes(), &envelope); err != nil {
		t.Fatalf("decode delta registration closeout output: %v\n%s", err, out.String())
	}
	return code, envelope
}

func r4CloseoutIntentCount(t *testing.T, root string) int {
	t.Helper()
	paths, err := rt.ResolvePaths(root)
	if err != nil {
		t.Fatal(err)
	}
	entries, err := os.ReadDir(filepath.Join(paths.RuntimeDir, "closeout-intents"))
	if os.IsNotExist(err) {
		return 0
	}
	if err != nil {
		t.Fatal(err)
	}
	count := 0
	for _, entry := range entries {
		if !entry.IsDir() && filepath.Ext(entry.Name()) == ".json" {
			count++
		}
	}
	return count
}

type r4FailingReader struct{ reads int }

func (reader *r4FailingReader) Read(_ []byte) (int, error) {
	reader.reads++
	return 0, fmt.Errorf("stdin must not be read for rejected closeout apply argument combinations")
}
