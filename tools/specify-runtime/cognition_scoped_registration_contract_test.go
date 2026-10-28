package main

import (
	"bytes"
	"context"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"

	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/claim"
	rt "github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/runtime"
	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/scopedregistration"
	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/store"
)

type r4ScopedFixture struct {
	root      string
	scope     string
	workID    string
	binding   closeoutBinding
	oldAlias  string
	newPath   string
	testPath  string
	oldPath   string
	packetRaw []byte
}

func TestR4ScopedRegisterCLIStdinBindsNativeProofAndRegistersQueryableFacts(t *testing.T) {
	fixture := r4ScopedRegistrationFixture(t)
	request := r4ScopedRegistrationRequest(t, fixture)
	raw := r4ScopedRegistrationJSON(t, request)

	code, envelope := r4RunScopedRegisterWithStdin(t, fixture.root, raw)
	if code != 0 || envelope.Status != "ok" {
		t.Fatalf("scoped-register failed: code=%d envelope=%+v", code, envelope)
	}
	if envelope.Data["claim_ready"] != false {
		t.Fatalf("scoped registration claimed workflow readiness: %+v", envelope.Data)
	}
	if got := stringValue(envelope.Data["source_revision"]); got != fixture.binding.AttemptID {
		t.Errorf("source_revision = %q, want runtime-owned sealed binding attempt %q", got, fixture.binding.AttemptID)
	}
	details := r4MapValue(t, envelope.Data["details"])
	nativeProof := r4MapValue(t, details["native_proof"])
	if got := stringValue(nativeProof["work_id"]); got != fixture.workID {
		t.Fatalf("native proof work_id = %q, want sealed binding work_id %q", got, fixture.workID)
	}
	if got := stringValue(nativeProof["attempt_id"]); got != fixture.binding.AttemptID {
		t.Fatalf("native proof attempt_id = %q, want sealed binding attempt %q", got, fixture.binding.AttemptID)
	}
	if got := stringSliceValue(t, nativeProof["owned_delta"]); !containsAll(got, []string{fixture.oldPath, fixture.newPath, "src/app.go"}) {
		t.Fatalf("native proof owned_delta = %#v, want actual changed source paths", got)
	}
	proofSource := r4MapValue(t, nativeProof["source"])
	if proofSource[fixture.newPath] == nil || proofSource["src/app.go"] == nil {
		t.Fatalf("native proof source basis missing changed source hashes: %#v", proofSource)
	}
	if debt := stringSliceValue(t, envelope.Data["validation_debt"]); len(debt) != 0 {
		t.Fatalf("complete scoped packet carried validation debt: %#v", debt)
	}
	registered := mapStringSlices(t, envelope.Data["registered"])
	if !containsAll(registered["nodes"], []string{"N-r4-new-owner", "N-r4-new-consumer", "N-r4-new-verification"}) ||
		!containsAll(registered["claims"], []string{"C-r4-owner-verified", "C-r4-consumer-supported", "C-r4-provisional"}) ||
		!containsAll(registered["path_index"], []string{"P-r4-new-owner"}) ||
		!containsAll(registered["aliases"], []string{"A-r4-new-owner"}) {
		t.Fatalf("registered rows missing identity/claim/path/alias agreement: %#v", registered)
	}
	retired := mapStringSlices(t, envelope.Data["retired"])
	if !containsAll(retired["aliases"], []string{fixture.oldAlias}) || !containsAll(retired["paths"], []string{fixture.oldPath}) {
		t.Fatalf("retired rows = %#v, want exact old alias/path", retired)
	}
	for _, row := range negativeQueryRows(t, envelope.Data["negative_queries"]) {
		if row["status"] != "absent_current" || row["observed_count"] != "0" {
			t.Fatalf("negative query did not prove zero current rows: %#v", row)
		}
	}

	st := r4OpenStore(t, fixture.root)
	defer st.Close()
	mapped, err := st.NodeIDsForExactPaths(context.Background(), []string{fixture.oldPath, fixture.newPath, "deps/lock.json"})
	if err != nil {
		t.Fatal(err)
	}
	if mapped[fixture.oldPath] != "" || mapped[fixture.newPath] != "N-r4-new-owner" || mapped["deps/lock.json"] == "" {
		t.Fatalf("query readback = %#v, want old path gone, new owner current, unrelated path preserved", mapped)
	}
	claimRows, err := st.ClaimsForNodeIDs(context.Background(), []string{fixture.oldAppNodeID(), fixture.oldPathNodeID(), fixture.unrelatedNodeID()})
	if err != nil {
		t.Fatal(err)
	}
	oldClaims := r4ClaimStates(claimRows)
	if oldClaims["C-r4-old-app-current"].freshness != string(claim.FreshnessStale) || oldClaims["C-r4-old-consumer"].freshness != string(claim.FreshnessStale) {
		t.Fatalf("related old claims were not marked stale: %#v", oldClaims)
	}
	if oldClaims["C-r4-unrelated-deps"].freshness != string(claim.FreshnessFresh) || oldClaims["C-r4-unrelated-deps"].state != string(claim.StateVerified) {
		t.Fatalf("unrelated claim was not preserved fresh/verified: %#v", oldClaims)
	}
	r4AssertFixtureSourceRelationship(t, fixture)
	claims, err := st.ClaimsForNodeIDs(context.Background(), []string{"N-r4-new-owner", "N-r4-new-consumer", "N-r4-new-verification"})
	if err != nil {
		t.Fatal(err)
	}
	seenClaims := map[string]string{}
	for _, row := range claims {
		seenClaims[stringValue(row["id"])] = stringValue(row["state"])
	}
	if seenClaims["C-r4-owner-verified"] != string(claim.StateVerified) ||
		seenClaims["C-r4-consumer-supported"] != string(claim.StateSupported) ||
		seenClaims["C-r4-provisional"] != string(claim.StateCandidate) {
		t.Fatalf("claim lifecycle readback = %#v", seenClaims)
	}
	activeGeneration, err := st.ActiveGenerationID(context.Background())
	if err != nil {
		t.Fatal(err)
	}
	if activeGeneration != "GEN-r3" {
		t.Fatalf("scoped registration replaced the active graph: got %q want GEN-r3", activeGeneration)
	}
	r4AssertPublicNavigationConsumesScopedRows(t, fixture.root, fixture.newPath)
}

func TestR4ScopedRegisterReplayRequiresCurrentProofAndDoesNotReplaceGeneration(t *testing.T) {
	fixture := r4ScopedRegistrationFixture(t)
	raw := r4ScopedRegistrationJSON(t, r4ScopedRegistrationRequest(t, fixture))
	code, envelope := r4RunScopedRegisterWithStdin(t, fixture.root, raw)
	if code != 0 || envelope.Status != "ok" {
		t.Fatalf("initial scoped-register failed: %d %+v", code, envelope)
	}
	registrationID := stringValue(envelope.Data["registration_id"])
	st := r4OpenStore(t, fixture.root)
	beforeUpdates := countRowsWhere(t, st, "updates", "id = ?", registrationID)
	beforeNodes := countRows(t, st, "nodes")
	st.Close()

	code, replay := r4RunScopedRegisterWithStdin(t, fixture.root, raw)
	if code != 0 || replay.Status != "ok" || replay.Data["replayed"] != true {
		t.Fatalf("identical replay failed: %d %+v", code, replay)
	}
	if !r4SameJSONValue(envelope.Data["registered"], replay.Data["registered"]) ||
		!r4SameJSONValue(envelope.Data["retired"], replay.Data["retired"]) ||
		!r4SameJSONValue(envelope.Data["negative_queries"], replay.Data["negative_queries"]) ||
		!r4SameJSONValue(envelope.Data["validation_debt"], replay.Data["validation_debt"]) ||
		!r4SameJSONValue(envelope.Data["claim_ready"], replay.Data["claim_ready"]) {
		t.Fatalf("replay receipt drifted from original: original=%+v replay=%+v", envelope.Data, replay.Data)
	}
	st = r4OpenStore(t, fixture.root)
	if got := countRowsWhere(t, st, "updates", "id = ?", registrationID); got != beforeUpdates {
		t.Fatalf("replay inserted duplicate update rows: got %d want %d", got, beforeUpdates)
	}
	if got := countRows(t, st, "nodes"); got != beforeNodes {
		t.Fatalf("replay inserted duplicate node rows: got %d want %d", got, beforeNodes)
	}
	st.Close()

	if err := os.WriteFile(filepath.Join(fixture.root, "src", "app.go"), []byte("source drift after scoped registration\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	code, drift := r4RunScopedRegisterWithStdin(t, fixture.root, raw)
	if code == 0 || drift.Status == "ok" || !strings.Contains(r4JoinedBlockers(drift), "changed after validation began") {
		t.Fatalf("stale proof replay was accepted: code=%d envelope=%+v", code, drift)
	}
}

func TestR4ScopedRegisterRejectsGenerationAndProofDriftBeforeMutation(t *testing.T) {
	t.Run("generation-mismatch", func(t *testing.T) {
		fixture := r4ScopedRegistrationFixture(t)
		request := r4ScopedRegistrationRequest(t, fixture)
		request.Source.ActiveGenerationID = "GEN-r4-other"
		raw := r4ScopedRegistrationJSON(t, request)
		st := r4OpenStore(t, fixture.root)
		before := countRows(t, st, "updates")
		st.Close()
		code, envelope := r4RunScopedRegisterWithStdin(t, fixture.root, raw)
		if code == 0 || envelope.Status == "ok" || !strings.Contains(r4JoinedBlockers(envelope), "active generation mismatch") {
			t.Fatalf("generation mismatch accepted: %d %+v", code, envelope)
		}
		st = r4OpenStore(t, fixture.root)
		if got := countRows(t, st, "updates"); got != before {
			t.Fatalf("generation mismatch mutated updates: got %d want %d", got, before)
		}
		st.Close()
	})
	t.Run("source-drift", func(t *testing.T) {
		fixture := r4ScopedRegistrationFixture(t)
		raw := r4ScopedRegistrationJSON(t, r4ScopedRegistrationRequest(t, fixture))
		if err := os.WriteFile(filepath.Join(fixture.root, "src", "app.go"), []byte("drift before scoped registration\n"), 0o644); err != nil {
			t.Fatal(err)
		}
		st := r4OpenStore(t, fixture.root)
		before := countRows(t, st, "updates")
		st.Close()
		code, envelope := r4RunScopedRegisterWithStdin(t, fixture.root, raw)
		if code == 0 || envelope.Status == "ok" || !strings.Contains(r4JoinedBlockers(envelope), "changed after validation began") {
			t.Fatalf("source drift accepted: %d %+v", code, envelope)
		}
		st = r4OpenStore(t, fixture.root)
		if got := countRows(t, st, "updates"); got != before {
			t.Fatalf("source drift mutated updates: got %d want %d", got, before)
		}
		st.Close()
	})
	t.Run("compiler-conflict", func(t *testing.T) {
		fixture := r4ScopedRegistrationFixture(t)
		request := r4ScopedRegistrationRequest(t, fixture)
		request.Delta.Nodes = append(request.Delta.Nodes, request.Delta.Nodes[0])
		raw := r4ScopedRegistrationJSON(t, request)
		st := r4OpenStore(t, fixture.root)
		before := countRows(t, st, "updates")
		st.Close()
		code, envelope := r4RunScopedRegisterWithStdin(t, fixture.root, raw)
		if code == 0 || envelope.Status == "ok" {
			t.Fatalf("conflicting scoped package accepted: %d %+v", code, envelope)
		}
		st = r4OpenStore(t, fixture.root)
		if got := countRows(t, st, "updates"); got != before {
			t.Fatalf("compiler conflict mutated updates: got %d want %d", got, before)
		}
		st.Close()
	})
	t.Run("source-evidence-hash-mismatch", func(t *testing.T) {
		fixture := r4ScopedRegistrationFixture(t)
		request := r4ScopedRegistrationRequest(t, fixture)
		request.Delta.Evidence[0].ContentHash = strings.Repeat("0", 64)
		raw := r4ScopedRegistrationJSON(t, request)
		st := r4OpenStore(t, fixture.root)
		before := countRows(t, st, "updates")
		st.Close()
		code, envelope := r4RunScopedRegisterWithStdin(t, fixture.root, raw)
		if code == 0 || envelope.Status == "ok" || !strings.Contains(r4JoinedBlockers(envelope), "content_hash_mismatch") {
			t.Fatalf("false source evidence hash accepted: %d %+v", code, envelope)
		}
		st = r4OpenStore(t, fixture.root)
		if got := countRows(t, st, "updates"); got != before {
			t.Fatalf("false source evidence hash mutated updates: got %d want %d", got, before)
		}
		st.Close()
	})
	t.Run("caller-attempt-and-accepted-output-drift", func(t *testing.T) {
		fixture := r4ScopedRegistrationFixture(t)
		request := r4ScopedRegistrationRequest(t, fixture)
		request.Work.AttemptID = "caller-fabricated-attempt"
		request.Work.AcceptedOutputRefs = []scopedregistration.AcceptedRef{{Path: ".specify/runtime/receipts/cognition-bindings/" + fixture.binding.ID + ".json", SHA256: strings.Repeat("1", 64)}}
		raw := r4ScopedRegistrationJSON(t, request)
		st := r4OpenStore(t, fixture.root)
		before := countRows(t, st, "updates")
		st.Close()
		code, envelope := r4RunScopedRegisterWithStdin(t, fixture.root, raw)
		if code == 0 || envelope.Status == "ok" {
			t.Fatalf("caller-fabricated attempt/accepted output drift accepted: %d %+v", code, envelope)
		}
		st = r4OpenStore(t, fixture.root)
		if got := countRows(t, st, "updates"); got != before {
			t.Fatalf("attempt/accepted-output drift mutated updates: got %d want %d", got, before)
		}
		st.Close()
	})
	t.Run("caller-source-revision-drift", func(t *testing.T) {
		fixture := r4ScopedRegistrationFixture(t)
		request := r4ScopedRegistrationRequest(t, fixture)
		request.Source.SourceRevision = "caller-fabricated-revision"
		raw := r4ScopedRegistrationJSON(t, request)
		st := r4OpenStore(t, fixture.root)
		before := countRows(t, st, "updates")
		st.Close()
		code, envelope := r4RunScopedRegisterWithStdin(t, fixture.root, raw)
		if code == 0 || envelope.Status == "ok" || !strings.Contains(r4JoinedBlockers(envelope), "source_revision contradicts native proof") {
			t.Fatalf("caller-fabricated source_revision accepted: %d %+v", code, envelope)
		}
		st = r4OpenStore(t, fixture.root)
		if got := countRows(t, st, "updates"); got != before {
			t.Fatalf("source revision drift mutated updates: got %d want %d", got, before)
		}
		st.Close()
	})
	t.Run("uncovered-verified-source-evidence", func(t *testing.T) {
		fixture := r4ScopedRegistrationFixture(t)
		uncoveredPath := "src/uncovered.go"
		if err := os.WriteFile(filepath.Join(fixture.root, filepath.FromSlash(uncoveredPath)), []byte("uncovered evidence source\n"), 0o644); err != nil {
			t.Fatal(err)
		}
		request := r4ScopedRegistrationRequest(t, fixture)
		request.Delta.Evidence = append(request.Delta.Evidence, scopedregistration.Evidence{ID: "E-r4-uncovered", SourceKind: "file", SourcePath: uncoveredPath, CommitSHA: "fixture", Extractor: "r4-native-contract-test", ContentHash: r4FileSHA256(t, fixture.root, uncoveredPath)})
		request.Delta.Nodes = append(request.Delta.Nodes, scopedregistration.Node{ID: "N-r4-uncovered", Type: "component", Title: "R4 uncovered evidence", Confidence: "supported", EvidenceIDs: []string{"E-r4-uncovered"}})
		request.Delta.Claims = append(request.Delta.Claims, scopedregistration.Claim{ID: "C-r4-uncovered-verified", NodeID: "N-r4-uncovered", GraphClaimType: "owner", Summary: "Verified source evidence must be covered by the runtime proof.", RequestedState: claim.StateVerified, SupportingEvidenceIDs: []string{"E-r4-uncovered"}, Verifications: []claim.Verification{{ID: "V-r4-uncovered", Result: claim.VerificationPassed, Command: "R4 uncovered source proof check", EvidenceID: "E-r4-verification", ObservedAt: time.Now().UTC().Format(time.RFC3339Nano)}}})
		parsed, canonical, err := scopedregistration.Parse(r4ScopedRegistrationJSON(t, request))
		if err != nil {
			t.Fatal(err)
		}
		paths, err := rt.ResolvePaths(fixture.root)
		if err != nil {
			t.Fatal(err)
		}
		st := r4OpenStore(t, fixture.root)
		before := countRows(t, st, "updates")
		st.Close()
		basis := scopedregistration.ProofBasis{Kind: "closeout_binding", BindingID: fixture.binding.ID, Workflow: fixture.binding.Workflow, Scope: fixture.binding.Scope, WorkID: fixture.binding.WorkID, AttemptID: fixture.binding.AttemptID, SourceRevision: fixture.binding.AttemptID, Source: fixture.binding.Source, OwnedDelta: append(append([]string{}, fixture.binding.OwnedDelta...), uncoveredPath), Digest: fixture.binding.Digest}
		_, err = scopedregistration.ApplyWithProofBasis(context.Background(), paths, parsed, canonical, basis, nil)
		if err == nil || !strings.Contains(err.Error(), "native_source_uncovered") {
			t.Fatalf("uncovered verified source evidence accepted: %v", err)
		}
		st = r4OpenStore(t, fixture.root)
		if got := countRows(t, st, "updates"); got != before {
			t.Fatalf("uncovered evidence drift mutated updates: got %d want %d", got, before)
		}
		st.Close()
	})
	t.Run("native-owner-basis-attempt-and-accepted-output-drift", func(t *testing.T) {
		fixture := r4ScopedRegistrationFixture(t)
		request := r4ScopedRegistrationRequest(t, fixture)
		parsed, canonical, err := scopedregistration.Parse(r4ScopedRegistrationJSON(t, request))
		if err != nil {
			t.Fatal(err)
		}
		paths, err := rt.ResolvePaths(fixture.root)
		if err != nil {
			t.Fatal(err)
		}
		st := r4OpenStore(t, fixture.root)
		before := countRows(t, st, "updates")
		st.Close()
		basis := scopedregistration.ProofBasis{Kind: "closeout_binding", BindingID: fixture.binding.ID, Workflow: fixture.binding.Workflow, Scope: fixture.binding.Scope, WorkID: fixture.binding.WorkID, AttemptID: "native-owner-attempt-v2", SourceRevision: "native-owner-attempt-v2", Source: fixture.binding.Source, OwnedDelta: fixture.binding.OwnedDelta, Digest: fixture.binding.Digest, AcceptedOutputSHA256: strings.Repeat("2", 64)}
		_, err = scopedregistration.ApplyWithProofBasis(context.Background(), paths, parsed, canonical, basis, nil)
		if err == nil || !strings.Contains(err.Error(), "attempt_id contradicts native proof") {
			t.Fatalf("native owner attempt drift accepted: %v", err)
		}
		st = r4OpenStore(t, fixture.root)
		if got := countRows(t, st, "updates"); got != before {
			t.Fatalf("native owner attempt drift mutated updates: got %d want %d", got, before)
		}
		st.Close()
	})
	t.Run("dependency-drift", func(t *testing.T) {
		fixture := r4ScopedRegistrationFixtureWithDependencies(t)
		raw := r4ScopedRegistrationJSON(t, r4ScopedRegistrationRequest(t, fixture))
		if err := os.WriteFile(filepath.Join(fixture.root, "deps", "lock.json"), []byte("dependency drift before scoped registration\n"), 0o644); err != nil {
			t.Fatal(err)
		}
		st := r4OpenStore(t, fixture.root)
		before := countRows(t, st, "updates")
		st.Close()
		code, envelope := r4RunScopedRegisterWithStdin(t, fixture.root, raw)
		if code == 0 || envelope.Status == "ok" || !strings.Contains(r4JoinedBlockers(envelope), "dependency bytes changed") {
			t.Fatalf("dependency drift accepted: %d %+v", code, envelope)
		}
		st = r4OpenStore(t, fixture.root)
		if got := countRows(t, st, "updates"); got != before {
			t.Fatalf("dependency drift mutated updates: got %d want %d", got, before)
		}
		st.Close()
	})
}

func TestR4ScopedRegisterRejectsSupportedUncoveredFileEvidenceAsCurrent(t *testing.T) {
	fixture := r4ScopedRegistrationFixture(t)
	request := r4ScopedRegistrationRequest(t, fixture)
	r4AppendSupportedUncoveredFileEvidence(&request)
	raw := r4ScopedRegistrationJSON(t, request)
	st := r4OpenStore(t, fixture.root)
	beforeUpdates := countRows(t, st, "updates")
	beforeEvidence := countRows(t, st, "evidence")
	st.Close()
	code, envelope := r4RunScopedRegisterWithStdin(t, fixture.root, raw)
	if code == 0 || envelope.Status == "ok" || !strings.Contains(r4JoinedBlockers(envelope), "native_source_uncovered") {
		t.Fatalf("supported uncovered file evidence published as current: code=%d envelope=%+v", code, envelope)
	}
	st = r4OpenStore(t, fixture.root)
	if got := countRows(t, st, "updates"); got != beforeUpdates {
		t.Fatalf("supported uncovered evidence inserted update rows: got %d want %d", got, beforeUpdates)
	}
	if got := countRows(t, st, "evidence"); got != beforeEvidence {
		t.Fatalf("supported uncovered evidence inserted current evidence rows: got %d want %d", got, beforeEvidence)
	}
	st.Close()
}

func TestR4ScopedRegisterPartialSupportedUncoveredEvidenceStaysCandidateDebt(t *testing.T) {
	fixture := r4ScopedRegistrationFixture(t)
	request := r4ScopedRegistrationRequest(t, fixture)
	request.Result.State = "partial"
	r4AppendSupportedUncoveredFileEvidence(&request)
	code, envelope := r4RunScopedRegisterWithStdin(t, fixture.root, r4ScopedRegistrationJSON(t, request))
	if code != 0 || stringValue(envelope.Data["status"]) != "partial" {
		t.Fatalf("partial supported uncovered evidence did not publish as explicit debt: code=%d envelope=%+v", code, envelope)
	}
	debt := stringSliceValue(t, envelope.Data["validation_debt"])
	if !r4StringSliceContainsPrefix(debt, "evidence:E-r4-supported-uncovered-file:native_source_uncovered:") ||
		!r4StringSliceContainsPrefix(debt, "claim:C-r4-supported-uncovered-file:unverified_source_evidence:E-r4-supported-uncovered-file:") {
		t.Fatalf("partial supported uncovered evidence did not preserve typed debt: %#v", debt)
	}
	registered := mapStringSlices(t, envelope.Data["registered"])
	if !containsAll(registered["claims"], []string{"C-r4-supported-uncovered-file"}) ||
		!containsAll(registered["nodes"], []string{"N-r4-supported-uncovered-file"}) ||
		!containsAll(registered["edges"], []string{"EDGE-r4-supported-uncovered-file"}) {
		t.Fatalf("partial supported uncovered package did not register auditable candidate rows: %#v", registered)
	}
	st := r4OpenStore(t, fixture.root)
	defer st.Close()
	claims, err := st.ClaimsForNodeIDs(context.Background(), []string{"N-r4-supported-uncovered-file"})
	if err != nil {
		t.Fatal(err)
	}
	states := r4ClaimStates(claims)
	if states["C-r4-supported-uncovered-file"].state != string(claim.StateCandidate) {
		t.Fatalf("uncovered supported claim became current semantic trust instead of candidate: %#v", states)
	}
	if got := r4SingleStringQuery(t, st, `SELECT confidence FROM nodes WHERE id = ?`, "N-r4-supported-uncovered-file"); got != "partial" {
		t.Fatalf("uncovered supported node confidence = %q, want partial", got)
	}
	if got := r4SingleStringQuery(t, st, `SELECT confidence FROM edges WHERE id = ?`, "EDGE-r4-supported-uncovered-file"); got != "partial" {
		t.Fatalf("uncovered supported edge confidence = %q, want partial", got)
	}
}

func TestR4ScopedRegisterRejectsMissingRetirementRowsAndIncompleteObligations(t *testing.T) {
	t.Run("missing-retirement-row", func(t *testing.T) {
		fixture := r4ScopedRegistrationFixture(t)
		request := r4ScopedRegistrationRequest(t, fixture)
		request.Delta.Retirements = append(request.Delta.Retirements, scopedregistration.Retirement{Kind: "alias", ID: "A-r4-missing", Reason: "must prove exact zero-row retirements"})
		raw := r4ScopedRegistrationJSON(t, request)
		st := r4OpenStore(t, fixture.root)
		before := countRows(t, st, "updates")
		st.Close()
		code, envelope := r4RunScopedRegisterWithStdin(t, fixture.root, raw)
		if code == 0 || envelope.Status == "ok" {
			t.Fatalf("missing alias retirement row accepted: %d %+v", code, envelope)
		}
		st = r4OpenStore(t, fixture.root)
		if got := countRows(t, st, "updates"); got != before {
			t.Fatalf("missing retirement mutated updates: got %d want %d", got, before)
		}
		st.Close()
	})
	t.Run("unknown-obligation-cannot-register-semantic-pass", func(t *testing.T) {
		fixture := r4ScopedRegistrationFixture(t)
		request := r4ScopedRegistrationRequest(t, fixture)
		request.Delta.Obligations.Consumers = nil
		request.Delta.Obligations.VerificationEntries = nil
		request.Delta.Obligations.Unknowns = []string{"truncated-full-delta-denominator"}
		raw := r4ScopedRegistrationJSON(t, request)
		code, envelope := r4RunScopedRegisterWithStdin(t, fixture.root, raw)
		if code == 0 || envelope.Status == "ok" {
			t.Fatalf("incomplete obligation packet registered as semantic pass: %d %+v", code, envelope)
		}
	})
	t.Run("whitespace-registered-cannot-bypass-debt", func(t *testing.T) {
		fixture := r4ScopedRegistrationFixture(t)
		request := r4ScopedRegistrationRequest(t, fixture)
		request.Result.State = " registered "
		request.Delta.Obligations.Consumers = nil
		raw := r4ScopedRegistrationJSON(t, request)
		st := r4OpenStore(t, fixture.root)
		before := countRows(t, st, "updates")
		st.Close()
		code, envelope := r4RunScopedRegisterWithStdin(t, fixture.root, raw)
		if code == 0 || envelope.Status == "ok" || !strings.Contains(r4JoinedBlockers(envelope), "consumer_obligations_not_declared") {
			t.Fatalf("whitespace registered bypassed validation debt: %d %+v", code, envelope)
		}
		st = r4OpenStore(t, fixture.root)
		if got := countRows(t, st, "updates"); got != before {
			t.Fatalf("whitespace registered debt mutated updates: got %d want %d", got, before)
		}
		st.Close()
	})
}

func TestR4ScopedRegisterPartialPublicationIsExplicitDebtOnly(t *testing.T) {
	fixture := r4ScopedRegistrationFixture(t)
	request := r4ScopedRegistrationRequest(t, fixture)
	request.Result.State = "partial"
	request.Delta.Obligations.Consumers = nil
	request.Delta.Obligations.VerificationEntries = nil
	request.Delta.Obligations.Unknowns = []string{"pending-independent-consumer-review"}
	raw := r4ScopedRegistrationJSON(t, request)
	code, envelope := r4RunScopedRegisterWithStdin(t, fixture.root, raw)
	if code != 0 || stringValue(envelope.Data["status"]) != "partial" {
		t.Fatalf("explicit partial scoped registration with debt should remain publishable as provisional debt: %d %+v", code, envelope)
	}
	if envelope.Data["claim_ready"] != false {
		t.Fatalf("partial scoped registration claimed semantic success: %+v", envelope.Data)
	}
	debt := stringSliceValue(t, envelope.Data["validation_debt"])
	if !containsAll(debt, []string{"consumer_obligations_not_declared", "verification_entries_not_declared", "pending-independent-consumer-review", "result_state_partial"}) {
		t.Fatalf("partial scoped registration did not preserve pending debt: %#v", debt)
	}
	st := r4OpenStore(t, fixture.root)
	defer st.Close()
	if got := countRowsWhere(t, st, "updates", "result_state = ?", "partial"); got != 1 {
		t.Fatalf("partial publication did not remain explicitly partial: got %d update rows", got)
	}
}

func TestR4ScopedRegisterPublicationRaceRollsBackAndMarksDebt(t *testing.T) {
	fixture := r4ScopedRegistrationFixture(t)
	request := r4ScopedRegistrationRequest(t, fixture)
	raw := r4ScopedRegistrationJSON(t, request)
	parsed, canonical, err := scopedregistration.Parse(raw)
	if err != nil {
		t.Fatal(err)
	}
	paths, err := rt.ResolvePaths(fixture.root)
	if err != nil {
		t.Fatal(err)
	}
	st := r4OpenStore(t, fixture.root)
	beforeUpdates := countRows(t, st, "updates")
	beforeNodes := countRows(t, st, "nodes")
	st.Close()
	_, err = scopedregistration.ApplyWithGuards(context.Background(), paths, parsed, canonical, &scopedregistration.Guards{
		BeforeCommit: func() error {
			if writeErr := os.WriteFile(filepath.Join(fixture.root, "src", "app.go"), []byte("source drift during scoped publication\n"), 0o644); writeErr != nil {
				return writeErr
			}
			return verifyScopedRegistrationNativeProof(fixture.root, parsed)
		},
	})
	if err == nil || !strings.Contains(err.Error(), "before-commit guard") {
		t.Fatalf("publication race was not rejected by guard: %v", err)
	}
	st = r4OpenStore(t, fixture.root)
	if got := countRows(t, st, "updates"); got != beforeUpdates {
		t.Fatalf("publication race committed update rows: got %d want %d", got, beforeUpdates)
	}
	if got := countRows(t, st, "nodes"); got != beforeNodes {
		t.Fatalf("publication race committed scoped node rows: got %d want %d", got, beforeNodes)
	}
	st.Close()
}

func TestR4ScopedRegisterDoNativeProofUsesRuntimeOwnerAndPublicRoutes(t *testing.T) {
	root, _, session := doSourceMutationFixtureWithSetup(t, func(root string) { doSeedCognitionBaseline(t, root) })
	validation := doValidate(root, session, false)
	if validation.Status != "passed" || !containsAll(validation.ChangedSourcePaths, []string{"generated/report.json", "source.txt"}) {
		t.Fatalf("Do fixture did not produce a completed source-bound owner proof: %+v", validation)
	}
	now := time.Now().UTC().Format(time.RFC3339Nano)
	request := scopedregistration.Request{
		Schema: scopedregistration.Schema,
		Proof:  scopedregistration.ProofBinding{Kind: "do_native", DoRef: ".specify/do/sessions/" + session.ID},
		Source: scopedregistration.SourceBinding{ActiveGenerationID: "GEN-do-closeout"},
		Result: scopedregistration.ResultIntent{State: "registered", Reason: "R4 Do-native scoped registration contract test"},
		Delta: scopedregistration.Delta{
			ChangedPaths: []scopedregistration.PathChange{
				{Operation: "modify", Path: "source.txt", NodeID: "N-r4-do-source", EvidenceRefs: []string{"E-r4-do-source"}},
				{Operation: "create", Path: "generated/report.json", NodeID: "N-r4-do-report", EvidenceRefs: []string{"E-r4-do-report"}},
			},
			Evidence: []scopedregistration.Evidence{
				{ID: "E-r4-do-source", SourceKind: "file", SourcePath: "source.txt", CommitSHA: "fixture", Extractor: "r4-native-contract-test", ContentHash: r4FileSHA256(t, root, "source.txt")},
				{ID: "E-r4-do-report", SourceKind: "command_result", SourcePath: "generated/report.json", CommitSHA: "fixture", Extractor: "r4-native-contract-test", ContentHash: r4FileSHA256(t, root, "generated/report.json")},
			},
			Nodes: []scopedregistration.Node{
				{ID: "N-r4-do-source", Type: "component", Title: "R4 Do Source", Confidence: "supported", EvidenceIDs: []string{"E-r4-do-source"}},
				{ID: "N-r4-do-report", Type: "verification", Title: "R4 Do Report", Confidence: "supported", EvidenceIDs: []string{"E-r4-do-report"}},
			},
			Edges: []scopedregistration.Edge{{ID: "EDGE-r4-do-report-verifies", Type: "verifies", SourceID: "N-r4-do-report", TargetID: "N-r4-do-source", Confidence: "supported", EvidenceIDs: []string{"E-r4-do-report"}}},
			Claims: []scopedregistration.Claim{
				{ID: "C-r4-do-supported", NodeID: "N-r4-do-source", GraphClaimType: "owner", Summary: "Do native source mutation is registered through runtime owner proof.", RequestedState: claim.StateSupported, SupportingEvidenceIDs: []string{"E-r4-do-source"}},
				{ID: "C-r4-do-report", NodeID: "N-r4-do-report", GraphClaimType: "verification", Summary: "Do native report remains a supported verification artifact.", RequestedState: claim.StateSupported, SupportingEvidenceIDs: []string{"E-r4-do-report"}},
			},
			Aliases:     []scopedregistration.Alias{{ID: "A-r4-do-source", Alias: "R4 Do Source", NormalizedAlias: "r4 do source", TargetType: "node", TargetID: "N-r4-do-source", Source: "scoped_registration", Confidence: "supported", EvidenceID: "E-r4-do-source"}},
			PathIndex:   []scopedregistration.PathIndex{{ID: "P-r4-do-source", Path: "source.txt", NodeID: "N-r4-do-source", Relation: "owns", Confidence: "supported", EvidenceID: "E-r4-do-source"}, {ID: "P-r4-do-report", Path: "generated/report.json", NodeID: "N-r4-do-report", Relation: "verifies", Confidence: "supported", EvidenceID: "E-r4-do-report"}},
			Obligations: scopedregistration.ObligationSummary{Owners: []string{"source.txt"}, Consumers: []string{"generated/report.json"}, Interfaces: []string{"R4 Do Source"}, StateContracts: []string{"GEN-do-closeout remains active"}, GeneratedChain: []string{"Do session " + session.ID}, VerificationEntries: []string{"Do validation " + now}},
		},
	}
	code, envelope := r4RunScopedRegisterWithStdin(t, root, r4ScopedRegistrationJSON(t, request))
	if code != 0 || envelope.Status != "ok" {
		t.Fatalf("do_native scoped-register failed: code=%d envelope=%+v", code, envelope)
	}
	details := r4MapValue(t, envelope.Data["details"])
	nativeProof := r4MapValue(t, details["native_proof"])
	if stringValue(nativeProof["kind"]) != "do_native" || stringValue(nativeProof["source_revision"]) != validation.SourceFingerprint {
		t.Fatalf("do_native proof did not come from runtime owner binding: proof=%#v validation=%+v", nativeProof, validation)
	}
	if got := stringSliceValue(t, nativeProof["owned_delta"]); !containsAll(got, validation.ChangedSourcePaths) {
		t.Fatalf("do_native owned_delta = %#v, want actual changed source paths %#v", got, validation.ChangedSourcePaths)
	}
	st := r4OpenStore(t, root)
	mapped, err := st.NodeIDsForExactPaths(context.Background(), []string{"source.txt", "generated/report.json"})
	st.Close()
	if err != nil {
		t.Fatal(err)
	}
	if mapped["source.txt"] != "N-r4-do-source" || mapped["generated/report.json"] != "N-r4-do-report" {
		t.Fatalf("do_native path query readback = %#v", mapped)
	}
	r4AssertPublicNavigationConsumesNode(t, root, "source.txt", "N-r4-do-source", "R4 Do Source")
	reloaded, _, err := loadDoSession(root, session.ID)
	if err != nil {
		t.Fatal(err)
	}
	after := doValidate(root, reloaded, true)
	if after.Status != "passed" {
		t.Fatalf("do_native scoped registration did not leave original Do closeout consumable: %+v", after)
	}
}

func TestR4ScopedRegisterClosureTruncationCannotMasqueradeAsSemanticPass(t *testing.T) {
	fixture := r4ScopedRegistrationFixture(t)
	request := r4ScopedRegistrationRequest(t, fixture)
	for index := 0; index < 205; index++ {
		nodeID := fmt.Sprintf("N-r4-wide-%03d", index)
		claimID := fmt.Sprintf("C-r4-wide-%03d", index)
		request.Delta.Nodes = append(request.Delta.Nodes, scopedregistration.Node{ID: nodeID, Type: "consumer", Title: nodeID, Confidence: "supported", EvidenceIDs: []string{"E-r4-source"}})
		request.Delta.Edges = append(request.Delta.Edges, scopedregistration.Edge{ID: fmt.Sprintf("EDGE-r4-wide-%03d", index), Type: "consumes", SourceID: nodeID, TargetID: "N-r4-new-owner", Confidence: "supported", EvidenceIDs: []string{"E-r4-source"}})
		request.Delta.Claims = append(request.Delta.Claims, scopedregistration.Claim{ID: claimID, NodeID: nodeID, GraphClaimType: "consumer", Summary: "wide closure consumer", RequestedState: claim.StateSupported, SupportingEvidenceIDs: []string{"E-r4-source"}})
	}
	code, envelope := r4RunScopedRegisterWithStdin(t, fixture.root, r4ScopedRegistrationJSON(t, request))
	if code != 0 {
		t.Fatalf("wide closure scoped-register failed before closure debt could be assessed: %d %+v", code, envelope)
	}
	closure := r4MapValue(t, envelope.Data["affected_closure"])
	if !r4BoolField(closure, "truncated", "Truncated") || r4StringField(closure, "truncation_reason", "TruncationReason") != "node_budget_exhausted" {
		t.Fatalf("wide closure did not report explicit truncation: %+v", envelope.Data)
	}
	if envelope.Status == "ok" || !containsAll(stringSliceValue(t, envelope.Data["validation_debt"]), []string{"affected_closure_truncated"}) || envelope.Data["claim_ready"] != false {
		t.Fatalf("truncated closure masqueraded as semantic success: %+v", envelope.Data)
	}
}

func TestR4ScopedRegisterPreservesLargeNumericAttrsThroughStdinStoreAndReplay(t *testing.T) {
	fixture := r4ScopedRegistrationFixture(t)
	request := r4ScopedRegistrationRequest(t, fixture)
	request.Delta.Nodes[0].Attrs = map[string]any{"placeholder": "replaced-with-raw-big-number"}
	raw := r4ScopedRegistrationJSON(t, request)
	bigNumber := []byte("9007199254740993123456789")
	raw = bytes.Replace(raw, []byte(`"replaced-with-raw-big-number"`), bigNumber, 1)
	if !bytes.Contains(raw, []byte(`"placeholder":9007199254740993123456789`)) {
		t.Fatalf("fixture did not contain raw unquoted large JSON number: %s", string(raw))
	}
	code, envelope := r4RunScopedRegisterWithStdin(t, fixture.root, raw)
	if code != 0 || envelope.Status != "ok" {
		t.Fatalf("large numeric attrs scoped-register failed: %d %+v", code, envelope)
	}
	st := r4OpenStore(t, fixture.root)
	var attrsJSON string
	if err := st.DB().QueryRowContext(context.Background(), `SELECT attrs_json FROM nodes WHERE id = ?`, "N-r4-new-owner").Scan(&attrsJSON); err != nil {
		st.Close()
		t.Fatal(err)
	}
	st.Close()
	if !strings.Contains(attrsJSON, string(bigNumber)) {
		t.Fatalf("stored attrs lost exact large number precision: %s", attrsJSON)
	}
	code, replay := r4RunScopedRegisterWithStdin(t, fixture.root, raw)
	if code != 0 || replay.Status != "ok" || replay.Data["replayed"] != true {
		t.Fatalf("large numeric attrs replay failed: %d %+v", code, replay)
	}
	if !r4SameJSONValue(envelope.Data["registered"], replay.Data["registered"]) {
		t.Fatalf("large numeric attrs replay changed registration rows: original=%+v replay=%+v", envelope.Data, replay.Data)
	}
	if code, rawQuery := r4RunCognitionRawInRoot(t, fixture.root, []string{"cognition", "query", "--intent", "owner", "--query", "N-r4-new-owner", "--format", "json"}); code == 0 && bytes.Contains(rawQuery, []byte("placeholder")) && !bytes.Contains(rawQuery, bigNumber) {
		t.Fatalf("public query exposed attrs but lost exact large number precision: %s", string(rawQuery))
	}
}

func r4ScopedRegistrationFixture(t *testing.T) r4ScopedFixture {
	t.Helper()
	return r4ScopedRegistrationFixtureWithOptions(t, nil)
}

func r4ScopedRegistrationFixtureWithDependencies(t *testing.T) r4ScopedFixture {
	t.Helper()
	return r4ScopedRegistrationFixtureWithOptions(t, []string{"deps/lock.json"})
}

func r4ScopedRegistrationFixtureWithOptions(t *testing.T, dependencies []string) r4ScopedFixture {
	t.Helper()
	root, scope, guard := r3BindingFixture(t, "fast")
	refs := []string{"src/app.go", "src/old.go", "deps/lock.json"}
	if err := os.WriteFile(filepath.Join(root, "src", "app.go"), []byte("package app\n\nfunc UseNewOwner() string {\n\treturn NewOwner()\n}\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(root, "src", "old.go"), []byte("package app\n\nfunc OldComponent() string {\n\treturn \"old\"\n}\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	r4SeedGraphWithClaims(t, root, refs)
	newPath := "src/new-owner.go"
	testPath := "src/new_owner_test.go"
	oldPath := "src/old.go"
	if err := os.WriteFile(filepath.Join(root, filepath.FromSlash(newPath)), []byte("package app\n\nfunc NewOwner() string {\n\treturn \"r4-new-owner\"\n}\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(root, filepath.FromSlash(testPath)), []byte("package app\n\nimport \"testing\"\n\nfunc TestUseNewOwner(t *testing.T) {\n\tif got := UseNewOwner(); got != \"r4-new-owner\" {\n\t\tt.Fatalf(\"UseNewOwner() = %q\", got)\n\t}\n}\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	if err := os.Remove(filepath.Join(root, filepath.FromSlash(oldPath))); err != nil {
		t.Fatal(err)
	}
	workID := stringValue(guard["work_id"])
	binding := r3Seal(t, root, r3Begin(t, root, scope, "fast", workID, dependencies, nil))
	if !containsAll(binding.OwnedDelta, []string{"src/app.go", oldPath, newPath, testPath}) {
		t.Fatalf("fixture binding owned_delta = %#v, want app modify, old delete, new owner and test create", binding.OwnedDelta)
	}
	return r4ScopedFixture{
		root:     root,
		scope:    scope,
		workID:   workID,
		binding:  binding,
		oldAlias: "A-" + closeoutIntentDigest(oldPath),
		newPath:  newPath,
		testPath: testPath,
		oldPath:  oldPath,
	}
}

func (fixture r4ScopedFixture) oldAppNodeID() string {
	return "N-" + closeoutIntentDigest("src/app.go")
}

func (fixture r4ScopedFixture) oldPathNodeID() string {
	return "N-" + closeoutIntentDigest(fixture.oldPath)
}

func (fixture r4ScopedFixture) unrelatedNodeID() string {
	return "N-" + closeoutIntentDigest("deps/lock.json")
}

func r4SeedGraphWithClaims(t *testing.T, root string, refs []string) {
	t.Helper()
	paths, err := rt.ResolvePaths(root)
	if err != nil {
		t.Fatal(err)
	}
	st, err := store.Open(paths)
	if err != nil {
		t.Fatal(err)
	}
	input := store.ImportInput{GenerationID: "GEN-r3", Kind: "full", SourceCommit: "fixture"}
	coverage := []any{}
	for _, ref := range refs {
		id := closeoutIntentDigest(ref)
		evidenceID := "E-" + id
		nodeID := "N-" + id
		input.Evidence = append(input.Evidence, store.EvidenceImport{ID: evidenceID, SourceKind: "file", SourcePath: ref, CommitSHA: "fixture", Extractor: "test", ContentHash: "fixture"})
		input.Nodes = append(input.Nodes, store.NodeImport{ID: nodeID, Type: "capability", Title: ref, Confidence: "verified", EvidenceIDs: []string{evidenceID}})
		input.PathIndex = append(input.PathIndex, store.PathIndexImport{ID: "P-" + id, Path: ref, NodeID: nodeID, Relation: "owns", Confidence: "verified", EvidenceID: evidenceID})
		input.Aliases = append(input.Aliases, store.AliasImport{ID: "A-" + id, Alias: ref, NormalizedAlias: ref, TargetType: "node", TargetID: nodeID, Source: "node_title", Confidence: "verified", EvidenceID: evidenceID})
		coverage = append(coverage, map[string]any{"path": ref, "status": "covered"})
	}
	appEvidence := "E-" + closeoutIntentDigest("src/app.go")
	oldEvidence := "E-" + closeoutIntentDigest("src/old.go")
	depsEvidence := "E-" + closeoutIntentDigest("deps/lock.json")
	appNode := "N-" + closeoutIntentDigest("src/app.go")
	oldNode := "N-" + closeoutIntentDigest("src/old.go")
	depsNode := "N-" + closeoutIntentDigest("deps/lock.json")
	input.Aliases = append(input.Aliases, store.AliasImport{ID: "A-r4-old-consumer-alias", Alias: "R4 old consumer", NormalizedAlias: "r4 old consumer", TargetType: "node", TargetID: oldNode, Source: "r4-native-contract-test", Confidence: "verified", EvidenceID: oldEvidence})
	input.Claims = append(input.Claims,
		store.ClaimImport{ID: "C-r4-old-app-current", NodeID: appNode, GraphClaimType: "consumer", Summary: "src/app.go had a fresh claim before the scoped update.", State: claim.StateVerified, Freshness: claim.FreshnessFresh, StateReason: "fixture-current-app", SupportingEvidenceIDs: []string{appEvidence}, Verifications: []store.ClaimVerificationImport{{ID: "V-r4-old-app-current", Result: claim.VerificationPassed, Command: "fixture old app verification", EvidenceID: appEvidence, ObservedAt: time.Now().UTC().Format(time.RFC3339Nano)}}},
		store.ClaimImport{ID: "C-r4-old-consumer", NodeID: oldNode, GraphClaimType: "consumer", Summary: "src/old.go was an old consumer before removal.", State: claim.StateVerified, Freshness: claim.FreshnessFresh, StateReason: "fixture-old-consumer", SupportingEvidenceIDs: []string{oldEvidence}, Verifications: []store.ClaimVerificationImport{{ID: "V-r4-old-consumer", Result: claim.VerificationPassed, Command: "fixture old consumer verification", EvidenceID: oldEvidence, ObservedAt: time.Now().UTC().Format(time.RFC3339Nano)}}},
		store.ClaimImport{ID: "C-r4-unrelated-deps", NodeID: depsNode, GraphClaimType: "dependency", Summary: "deps/lock.json must remain fresh when unrelated to the scoped source update.", State: claim.StateVerified, Freshness: claim.FreshnessFresh, StateReason: "fixture-unrelated-preserved", SupportingEvidenceIDs: []string{depsEvidence}, Verifications: []store.ClaimVerificationImport{{ID: "V-r4-unrelated-deps", Result: claim.VerificationPassed, Command: "fixture unrelated dependency verification", EvidenceID: depsEvidence, ObservedAt: time.Now().UTC().Format(time.RFC3339Nano)}}},
	)
	if _, err := st.ImportGeneration(context.Background(), input); err != nil {
		st.Close()
		t.Fatal(err)
	}
	if _, _, err := st.PublishRuntimeMetadata(context.Background(), "GEN-r3", rt.BaselineKindBrownfieldFull); err != nil {
		st.Close()
		t.Fatal(err)
	}
	if err := st.Close(); err != nil {
		t.Fatal(err)
	}
	status := rt.DefaultStatus(paths)
	status.Status, status.Freshness, status.Readiness, status.RecommendedNextAction = "ok", rt.ReadyFreshness, rt.ReadyReadiness, "use_project_cognition"
	status.GraphReady, status.ActiveGenerationID, status.BaselineKind = true, "GEN-r3", rt.BaselineKindBrownfieldFull
	if err := rt.WriteStatus(paths, status); err != nil {
		t.Fatal(err)
	}
	for name, value := range map[string]any{"capability-ledger.json": map[string]any{"rows": []any{}}, "control-ledger.json": map[string]any{"rows": []any{}}, "coverage-ledger.json": map[string]any{"rows": coverage, "open_gaps": []any{}}} {
		writeTaskRuntimeFixture(t, filepath.Join(paths.RuntimeDir, "workbench", name), value.(map[string]any))
	}
}

func r4ScopedRegistrationRequest(t *testing.T, fixture r4ScopedFixture) scopedregistration.Request {
	t.Helper()
	now := time.Now().UTC().Format(time.RFC3339Nano)
	sourceHash := r4FileSHA256(t, fixture.root, fixture.newPath)
	consumerHash := r4FileSHA256(t, fixture.root, "src/app.go")
	testHash := r4FileSHA256(t, fixture.root, fixture.testPath)
	verificationHash := r4SHA256Hex([]byte("native verification observed"))
	return scopedregistration.Request{
		Schema: scopedregistration.Schema,
		Proof:  scopedregistration.ProofBinding{Kind: "closeout_binding", BindingID: fixture.binding.ID, Workflow: fixture.binding.Workflow, Scope: fixture.binding.Scope},
		Work: scopedregistration.WorkBinding{
			WorkID:    fixture.binding.WorkID,
			AttemptID: fixture.binding.AttemptID,
			AcceptedOutputRefs: []scopedregistration.AcceptedRef{{
				Path:   ".specify/runtime/receipts/cognition-bindings/" + fixture.binding.ID + ".json",
				SHA256: fixture.binding.Digest,
			}},
		},
		Source: scopedregistration.SourceBinding{
			ActiveGenerationID: "GEN-r3",
			SourceRevision:     fixture.binding.AttemptID,
			SourceHashes:       []scopedregistration.SourceHash{{Path: fixture.newPath, SHA256: sourceHash}, {Path: "src/app.go", SHA256: consumerHash}, {Path: fixture.testPath, SHA256: testHash}},
		},
		Result: scopedregistration.ResultIntent{State: "registered", Reason: "R4 native scoped registration contract test"},
		Delta: scopedregistration.Delta{
			ChangedPaths: []scopedregistration.PathChange{
				{Operation: "modify", Path: "src/app.go", NodeID: "N-r4-new-consumer", EvidenceRefs: []string{"E-r4-consumer-source"}},
				{Operation: "delete", Path: fixture.oldPath, EvidenceRefs: []string{"E-r4-source"}},
				{Operation: "create", Path: fixture.newPath, NodeID: "N-r4-new-owner", EvidenceRefs: []string{"E-r4-source"}},
				{Operation: "create", Path: fixture.testPath, NodeID: "N-r4-new-verification", EvidenceRefs: []string{"E-r4-test-source"}},
			},
			Evidence: []scopedregistration.Evidence{
				{ID: "E-r4-source", SourceKind: "file", SourcePath: fixture.newPath, CommitSHA: "fixture", Extractor: "r4-native-contract-test", ContentHash: sourceHash},
				{ID: "E-r4-consumer-source", SourceKind: "file", SourcePath: "src/app.go", CommitSHA: "fixture", Extractor: "r4-native-contract-test", ContentHash: consumerHash},
				{ID: "E-r4-test-source", SourceKind: "file", SourcePath: fixture.testPath, CommitSHA: "fixture", Extractor: "r4-native-contract-test", ContentHash: testHash},
				{ID: "E-r4-verification", SourceKind: "command_result", SourcePath: ".codex-tmp/cognition-loop-implementation/r4-native-contract-test-author-v2/verification.json", CommitSHA: "fixture", Extractor: "r4-native-contract-test", ContentHash: verificationHash},
			},
			Nodes: []scopedregistration.Node{
				{ID: "N-r4-new-owner", Type: "component", Title: "R4 new owner", Confidence: "supported", EvidenceIDs: []string{"E-r4-source"}},
				{ID: "N-r4-new-consumer", Type: "consumer", Title: "R4 new consumer", Confidence: "supported", EvidenceIDs: []string{"E-r4-consumer-source"}},
				{ID: "N-r4-new-verification", Type: "verification", Title: "R4 new verification", Confidence: "supported", EvidenceIDs: []string{"E-r4-test-source", "E-r4-verification"}},
			},
			Edges: []scopedregistration.Edge{
				{ID: "EDGE-r4-consumes", Type: "consumes", SourceID: "N-r4-new-consumer", TargetID: "N-r4-new-owner", Confidence: "supported", EvidenceIDs: []string{"E-r4-consumer-source"}},
				{ID: "EDGE-r4-verifies", Type: "verifies", SourceID: "N-r4-new-verification", TargetID: "N-r4-new-owner", Confidence: "supported", EvidenceIDs: []string{"E-r4-test-source", "E-r4-verification"}},
			},
			Claims: []scopedregistration.Claim{
				{ID: "C-r4-owner-verified", NodeID: "N-r4-new-owner", GraphClaimType: "owner", Summary: "src/new-owner.go owns the new R4 component.", RequestedState: claim.StateVerified, SupportingEvidenceIDs: []string{"E-r4-source"}, Verifications: []claim.Verification{{ID: "V-r4-owner", Result: claim.VerificationPassed, Command: "R4 native scoped contract verification", EvidenceID: "E-r4-verification", ObservedAt: now}}},
				{ID: "C-r4-consumer-supported", NodeID: "N-r4-new-consumer", GraphClaimType: "consumer", Summary: "src/app.go calls NewOwner through UseNewOwner.", RequestedState: claim.StateSupported, SupportingEvidenceIDs: []string{"E-r4-consumer-source"}},
				{ID: "C-r4-provisional", NodeID: "N-r4-new-verification", GraphClaimType: "verification", Summary: "A future independent consumer still has to accept the full R4 denominator.", RequestedState: claim.StateVerified},
			},
			Aliases:   []scopedregistration.Alias{{ID: "A-r4-new-owner", Alias: "R4 New Owner", NormalizedAlias: "r4 new owner", TargetType: "node", TargetID: "N-r4-new-owner", Source: "scoped_registration", Confidence: "supported", EvidenceID: "E-r4-source"}},
			PathIndex: []scopedregistration.PathIndex{{ID: "P-r4-new-owner", Path: fixture.newPath, NodeID: "N-r4-new-owner", Relation: "owns", Confidence: "supported", EvidenceID: "E-r4-source"}, {ID: "P-r4-new-test", Path: fixture.testPath, NodeID: "N-r4-new-verification", Relation: "verifies", Confidence: "supported", EvidenceID: "E-r4-test-source"}},
			Retirements: []scopedregistration.Retirement{
				{Kind: "alias", ID: fixture.oldAlias, Reason: "src/old.go removed by bounded R4 scoped registration"},
				{Kind: "alias", ID: "A-r4-old-consumer-alias", Reason: "old consumer alias removed by bounded R4 scoped registration"},
				{Kind: "path", Path: fixture.oldPath, Reason: "src/old.go removed by bounded R4 scoped registration"},
				{Kind: "claim", ID: "C-r4-old-consumer", Reason: "src/old.go consumer claim retired by bounded R4 scoped registration"},
			},
			Obligations: scopedregistration.ObligationSummary{
				Owners:              []string{fixture.newPath},
				Consumers:           []string{"src/app.go"},
				Interfaces:          []string{"R4 New Owner"},
				StateContracts:      []string{"active generation GEN-r3 remains active"},
				GeneratedChain:      []string{"no generated chain for this bounded native contract test"},
				VerificationEntries: []string{fixture.testPath},
				InvalidatedAliases:  []string{"src/old.go", "R4 old consumer"},
			},
		},
	}
}

func r4ScopedRegistrationJSON(t *testing.T, request scopedregistration.Request) []byte {
	t.Helper()
	raw, err := json.Marshal(request)
	if err != nil {
		t.Fatal(err)
	}
	return raw
}

func r4AppendSupportedUncoveredFileEvidence(request *scopedregistration.Request) {
	request.Delta.Evidence = append(request.Delta.Evidence, scopedregistration.Evidence{ID: "E-r4-supported-uncovered-file", SourceKind: "file", SourcePath: "src/unowned-supported.go", CommitSHA: "fixture", Extractor: "r4-native-contract-test", ContentHash: strings.Repeat("b", 64)})
	request.Delta.Nodes = append(request.Delta.Nodes, scopedregistration.Node{ID: "N-r4-supported-uncovered-file", Type: "component", Title: "R4 supported uncovered file", Confidence: "supported", EvidenceIDs: []string{"E-r4-supported-uncovered-file"}})
	request.Delta.Edges = append(request.Delta.Edges, scopedregistration.Edge{ID: "EDGE-r4-supported-uncovered-file", Type: "consumes", SourceID: "N-r4-supported-uncovered-file", TargetID: "N-r4-new-owner", Confidence: "supported", EvidenceIDs: []string{"E-r4-supported-uncovered-file"}})
	request.Delta.Claims = append(request.Delta.Claims, scopedregistration.Claim{ID: "C-r4-supported-uncovered-file", NodeID: "N-r4-supported-uncovered-file", GraphClaimType: "owner", Summary: "Supported claims backed by unowned file evidence must not become current trust.", RequestedState: claim.StateSupported, SupportingEvidenceIDs: []string{"E-r4-supported-uncovered-file"}})
}

func r4RunScopedRegisterWithStdin(t *testing.T, root string, raw []byte) (int, Envelope) {
	t.Helper()
	input := filepath.Join(t.TempDir(), "stdin.json")
	if err := os.WriteFile(input, append(raw, '\n'), 0o644); err != nil {
		t.Fatal(err)
	}
	file, err := os.Open(input)
	if err != nil {
		t.Fatal(err)
	}
	defer file.Close()
	previous := os.Stdin
	os.Stdin = file
	defer func() { os.Stdin = previous }()
	var stdout, stderr bytes.Buffer
	code := Run([]string{"cognition", "scoped-register", "--project-root", root, "--input-json", "-", "--format", "json"}, &stdout, &stderr, "test")
	if stderr.Len() != 0 {
		t.Fatalf("unexpected stderr: %s", stderr.String())
	}
	var envelope Envelope
	if err := json.Unmarshal(stdout.Bytes(), &envelope); err != nil {
		t.Fatalf("decode scoped-register output: %v\n%s", err, stdout.String())
	}
	return code, envelope
}

func r4RunCognitionInRoot(t *testing.T, root string, args []string) (int, map[string]any) {
	t.Helper()
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
	code := Run(args, &stdout, &stderr, "test")
	if stderr.Len() != 0 && code == 0 {
		t.Fatalf("unexpected stderr for %v: %s", args, stderr.String())
	}
	var payload map[string]any
	if err := json.Unmarshal(stdout.Bytes(), &payload); err != nil {
		return code, map[string]any{"decode_error": err.Error(), "stdout": stdout.String(), "stderr": stderr.String()}
	}
	return code, payload
}

func r4RunCognitionRawInRoot(t *testing.T, root string, args []string) (int, []byte) {
	t.Helper()
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
	code := Run(args, &stdout, &stderr, "test")
	if stderr.Len() != 0 && code == 0 {
		t.Fatalf("unexpected stderr for %v: %s", args, stderr.String())
	}
	return code, stdout.Bytes()
}

func r4AssertPublicNavigationConsumesScopedRows(t *testing.T, root, newPath string) {
	t.Helper()
	r4AssertPublicNavigationConsumesNode(t, root, newPath, "N-r4-new-owner", "R4 New Owner")
}

func r4AssertPublicNavigationConsumesNode(t *testing.T, root, pathValue, nodeID, aliasQuery string) {
	t.Helper()
	st := r4OpenStore(t, root)
	generationID, err := st.ActiveGenerationID(context.Background())
	st.Close()
	if err != nil {
		t.Fatal(err)
	}
	plan := marshalJSONForCLI(t, map[string]any{
		"candidate_universe_version": 2,
		"lexicon_generation_id":      generationID,
		"paths":                      []string{pathValue},
		"selected_concepts":          []string{"concept:" + generationID + ":" + nodeID},
		"concept_decisions": []map[string]any{{
			"concept_id":       "concept:" + generationID + ":" + nodeID,
			"decision":         "selected",
			"selection_reason": "R4 scoped registration must be queryable through the public navigation surface.",
			"confidence":       "high",
			"paths":            []string{pathValue},
		}},
	})
	code, queryPayload := r4RunCognitionInRoot(t, root, []string{"cognition", "query", "--intent", "debug", "--query-plan", plan, "--format", "json"})
	if code != 0 || queryPayload["resolution_state"] != "resolved_exact" || !r4JSONStringSliceContains(queryPayload["minimal_live_reads"], pathValue) {
		t.Errorf("public query did not consume scoped owner row: code=%d payload=%#v", code, queryPayload)
	}
	code, compassPayload := r4RunCognitionInRoot(t, root, []string{"cognition", "compass", "--query-plan", plan, "--format", "json"})
	if code != 0 || !r4JSONStringSliceContains(compassPayload["minimal_live_reads"], pathValue) {
		t.Errorf("public compass did not consume scoped owner row: code=%d payload=%#v", code, compassPayload)
	}
	code, lexiconPayload := r4RunCognitionInRoot(t, root, []string{"cognition", "lexicon", "--intent", "debug", "--mode", "catalog", "--query", aliasQuery, "--limit", "10", "--format", "json"})
	if code != 0 || !r4AliasCatalogContainsNode(lexiconPayload["alias_catalog"], nodeID) {
		t.Errorf("public alias catalog did not expose scoped identity: code=%d payload=%#v", code, lexiconPayload)
	}
	if code, payload := r4RunCognitionInRoot(t, root, []string{"cognition", "validate-build", "--format", "json"}); code != 0 {
		t.Errorf("validate-build did not consume scoped graph: code=%d payload=%#v", code, payload)
	}
}

func r4OpenStore(t *testing.T, root string) *store.Store {
	t.Helper()
	paths, err := rt.ResolvePaths(root)
	if err != nil {
		t.Fatal(err)
	}
	st, err := store.OpenExisting(paths)
	if err != nil {
		t.Fatal(err)
	}
	return st
}

func countRows(t *testing.T, st *store.Store, table string) int {
	t.Helper()
	var count int
	if err := st.DB().QueryRowContext(context.Background(), "SELECT COUNT(*) FROM "+table).Scan(&count); err != nil {
		t.Fatal(err)
	}
	return count
}

func countRowsWhere(t *testing.T, st *store.Store, table, where string, args ...any) int {
	t.Helper()
	var count int
	if err := st.DB().QueryRowContext(context.Background(), "SELECT COUNT(*) FROM "+table+" WHERE "+where, args...).Scan(&count); err != nil {
		t.Fatal(err)
	}
	return count
}

func r4FileSHA256(t *testing.T, root, ref string) string {
	t.Helper()
	data, err := os.ReadFile(filepath.Join(root, filepath.FromSlash(ref)))
	if err != nil {
		t.Fatal(err)
	}
	return r4SHA256Hex(data)
}

func r4SHA256Hex(data []byte) string {
	sum := sha256.Sum256(data)
	return hex.EncodeToString(sum[:])
}

func r4MapValue(t *testing.T, value any) map[string]any {
	t.Helper()
	out, ok := value.(map[string]any)
	if !ok {
		t.Fatalf("value is %T, want map[string]any: %#v", value, value)
	}
	return out
}

func mapStringSlices(t *testing.T, value any) map[string][]string {
	t.Helper()
	raw := r4MapValue(t, value)
	out := map[string][]string{}
	for key, item := range raw {
		out[key] = stringSliceValue(t, item)
	}
	return out
}

func stringSliceValue(t *testing.T, value any) []string {
	t.Helper()
	items, ok := value.([]any)
	if !ok {
		t.Fatalf("value is %T, want []any: %#v", value, value)
	}
	out := make([]string, 0, len(items))
	for _, item := range items {
		out = append(out, stringValue(item))
	}
	return out
}

func negativeQueryRows(t *testing.T, value any) []map[string]string {
	t.Helper()
	items, ok := value.([]any)
	if !ok {
		t.Fatalf("negative queries value is %T: %#v", value, value)
	}
	out := make([]map[string]string, 0, len(items))
	for _, item := range items {
		row := r4MapValue(t, item)
		converted := map[string]string{}
		for key, raw := range row {
			converted[key] = stringValue(raw)
		}
		out = append(out, converted)
	}
	return out
}

func r4JoinedBlockers(envelope Envelope) string {
	parts := make([]string, 0, len(envelope.Blockers))
	for _, blocker := range envelope.Blockers {
		parts = append(parts, stringValue(blocker))
	}
	return strings.Join(parts, " ")
}

func r4AliasCatalogContainsNode(value any, nodeID string) bool {
	items, ok := value.([]any)
	if !ok {
		return false
	}
	for _, item := range items {
		row, ok := item.(map[string]any)
		if !ok {
			continue
		}
		if stringValue(row["node_id"]) == nodeID {
			return true
		}
		if strings.HasSuffix(stringValue(row["concept_id"]), ":"+nodeID) {
			return true
		}
	}
	return false
}

func r4JSONStringSliceContains(value any, want string) bool {
	items, ok := value.([]any)
	if !ok {
		return false
	}
	for _, item := range items {
		if stringValue(item) == want {
			return true
		}
	}
	return false
}

type r4ClaimState struct {
	state     string
	freshness string
}

func r4ClaimStates(rows []map[string]any) map[string]r4ClaimState {
	out := map[string]r4ClaimState{}
	for _, row := range rows {
		out[stringValue(row["id"])] = r4ClaimState{state: stringValue(row["state"]), freshness: stringValue(row["freshness"])}
	}
	return out
}

func r4AssertFixtureSourceRelationship(t *testing.T, fixture r4ScopedFixture) {
	t.Helper()
	owner, err := os.ReadFile(filepath.Join(fixture.root, filepath.FromSlash(fixture.newPath)))
	if err != nil {
		t.Fatal(err)
	}
	consumer, err := os.ReadFile(filepath.Join(fixture.root, "src", "app.go"))
	if err != nil {
		t.Fatal(err)
	}
	verification, err := os.ReadFile(filepath.Join(fixture.root, filepath.FromSlash(fixture.testPath)))
	if err != nil {
		t.Fatal(err)
	}
	if !strings.Contains(string(owner), "func NewOwner() string") ||
		!strings.Contains(string(consumer), "return NewOwner()") ||
		!strings.Contains(string(verification), "TestUseNewOwner") ||
		!strings.Contains(string(verification), "UseNewOwner()") {
		t.Fatalf("semantic fixture source relationship missing owner/consumer/test proof:\nowner=%s\nconsumer=%s\nverification=%s", owner, consumer, verification)
	}
}

func r4SameJSONValue(left, right any) bool {
	leftRaw, leftErr := json.Marshal(left)
	rightRaw, rightErr := json.Marshal(right)
	return leftErr == nil && rightErr == nil && bytes.Equal(leftRaw, rightRaw)
}

func r4BoolField(row map[string]any, keys ...string) bool {
	for _, key := range keys {
		if value, ok := row[key].(bool); ok {
			return value
		}
	}
	return false
}

func r4StringField(row map[string]any, keys ...string) string {
	for _, key := range keys {
		if value := stringValue(row[key]); value != "" {
			return value
		}
	}
	return ""
}

func r4StringSliceContainsPrefix(values []string, prefix string) bool {
	for _, value := range values {
		if strings.HasPrefix(value, prefix) {
			return true
		}
	}
	return false
}

func r4SingleStringQuery(t *testing.T, st *store.Store, query string, args ...any) string {
	t.Helper()
	var out string
	if err := st.DB().QueryRowContext(context.Background(), query, args...).Scan(&out); err != nil {
		t.Fatal(err)
	}
	return out
}

func containsAll(values, required []string) bool {
	seen := map[string]bool{}
	for _, value := range values {
		seen[value] = true
	}
	for _, value := range required {
		if !seen[value] {
			return false
		}
	}
	return true
}
