package store

import (
	"context"
	"encoding/json"
	"strings"
	"testing"

	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/claim"
	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/scanartifacts"
)

func TestApplyScopedRegistrationAtomicallyRegistersAndRetiresWithNegativeEvidence(t *testing.T) {
	st := openImportTestStore(t)
	defer st.Close()
	ctx := context.Background()
	input := validImportInput("GEN-scoped-registration")
	input.Aliases = []AliasImport{{ID: "A-old-app", Alias: "old app", NormalizedAlias: "old app", TargetType: "node", TargetID: "N-app", Source: "scoped_registration", Confidence: "verified", EvidenceID: "E-001"}}
	input.Claims = []ClaimImport{{ID: "claim:old-app", NodeID: "N-app", GraphClaimType: "runtime_owner", Summary: "old app claim", State: claim.StateSupported, Freshness: claim.FreshnessFresh, StateReason: "seed", SupportingEvidenceIDs: []string{"E-001"}}}
	if _, err := st.ImportGeneration(ctx, input); err != nil {
		t.Fatal(err)
	}

	result, err := st.ApplyScopedRegistration(ctx, ScopedRegistrationInput{
		RegistrationID:       "scoped-registration:test",
		ExpectedGenerationID: "GEN-scoped-registration",
		PacketSHA256:         "packet-sha",
		ResultState:          "registered",
		Reason:               "r4 scoped test",
		Package: scanartifacts.Package{
			Evidence: []scanartifacts.EvidenceRow{{ID: "E-new", SourceKind: "source", SourcePath: "src/new.go", Extractor: "test", ContentHash: "hash-new"}},
			Nodes:    []scanartifacts.NodeRow{{ID: "N-new", Type: "capability", Title: "New", Confidence: "partial", EvidenceIDs: []string{"E-new"}}},
			Claims:   []scanartifacts.ClaimRow{{ID: "claim:new", NodeID: "N-new", GraphClaimType: "runtime_owner", Summary: "new claim", RequestedState: claim.StateSupported, SupportingEvidenceIDs: []string{"E-new"}}},
		},
		PathIndex:      []PathIndexImport{{Path: "src/new.go", NodeID: "N-new", Relation: "owns", Confidence: "partial", EvidenceID: "E-new"}},
		Aliases:        []AliasImport{{Alias: "new app", NormalizedAlias: "new app", TargetType: "node", TargetID: "N-new", Source: "scoped_registration", Confidence: "partial", EvidenceID: "E-new"}},
		Retirements:    []ScopedRetirement{{Kind: "alias", ID: "A-old-app", Reason: "renamed"}, {Kind: "path", Path: "src/app.go", Reason: "renamed"}},
		ChangedPaths:   []string{"src/app.go", "src/new.go"},
		NewClaimIDs:    []string{"claim:new"},
		NegativeProbes: []ScopedNegativeProbe{{Intent: "negative-path", Query: "src/app.go", Kind: "path"}, {Intent: "negative-alias", Query: "old app", Kind: "alias"}},
		Attrs:          map[string]any{"packet_sha256": "packet-sha"},
	})
	if err != nil {
		t.Fatal(err)
	}
	if result.Registered["nodes"][0] != "N-new" || result.Retired["aliases"][0] != "A-old-app" || result.Retired["paths"][0] != "src/app.go" {
		t.Fatalf("result = %#v, want registered node and retired alias/path", result)
	}
	if len(result.NegativeQueries) != 2 || result.NegativeQueries[0].Status != "absent_current" || result.NegativeQueries[1].Status != "absent_current" {
		t.Fatalf("negative queries = %#v, want actual absent_current evidence", result.NegativeQueries)
	}
	mapped, err := st.NodeIDsForExactPaths(ctx, []string{"src/app.go", "src/new.go"})
	if err != nil {
		t.Fatal(err)
	}
	if mapped["src/app.go"] != "" || mapped["src/new.go"] != "N-new" {
		t.Fatalf("mapped paths = %#v, want old path gone and new path current", mapped)
	}
	var oldAliasCount int
	if err := st.DB().QueryRowContext(ctx, `SELECT COUNT(*) FROM alias_index WHERE generation_id = 'GEN-scoped-registration' AND normalized_alias = 'old app'`).Scan(&oldAliasCount); err != nil {
		t.Fatal(err)
	}
	if oldAliasCount != 0 {
		t.Fatalf("old alias count = %d, want 0", oldAliasCount)
	}
}

func TestApplyScopedRegistrationRejectsGenerationRaceBeforeMutation(t *testing.T) {
	st := openImportTestStore(t)
	defer st.Close()
	ctx := context.Background()
	if _, err := st.ImportGeneration(ctx, validImportInput("GEN-race")); err != nil {
		t.Fatal(err)
	}
	_, err := st.ApplyScopedRegistration(ctx, ScopedRegistrationInput{RegistrationID: "scoped-registration:race", ExpectedGenerationID: "GEN-other", PacketSHA256: "packet-sha", ResultState: "registered", Reason: "race"})
	if err == nil {
		t.Fatal("ApplyScopedRegistration returned nil error for generation mismatch")
	}
	var updateCount int
	if queryErr := st.DB().QueryRowContext(ctx, `SELECT COUNT(*) FROM updates WHERE id = 'scoped-registration:race'`).Scan(&updateCount); queryErr != nil {
		t.Fatal(queryErr)
	}
	if updateCount != 0 {
		t.Fatalf("update count = %d, want 0", updateCount)
	}
}

func TestApplyScopedRegistrationMergesIntoParentUpdateJournal(t *testing.T) {
	st := openImportTestStore(t)
	defer st.Close()
	ctx := context.Background()
	if _, err := st.ImportGeneration(ctx, validImportInput("GEN-parent-scoped")); err != nil {
		t.Fatal(err)
	}
	if err := st.RecordStructuredUpdate(ctx, UpdateRecord{
		ID:             "upd-parent",
		Trigger:        "workflow-finalize",
		ChangedPaths:   []string{"src/original.go"},
		AffectedNodes:  []string{"N-app"},
		AffectedClaims: []string{"claim:app"},
		ResultState:    "ready",
		Attrs: map[string]any{
			"closeout_intent_id": "intent-parent",
			"scope_result_state": "ready",
			"original":           "preserved",
		},
	}); err != nil {
		t.Fatal(err)
	}
	placeholderAttrs, err := attrsJSONOrEmpty(map[string]any{"update_id": "upd-parent"})
	if err != nil {
		t.Fatal(err)
	}
	if _, err := st.DB().ExecContext(ctx, `INSERT INTO evidence(id, generation_id, source_kind, source_path, commit_sha, span, extractor, content_hash, captured_at, attrs_json) VALUES('E-parent-placeholder', 'GEN-parent-scoped', 'workflow_update', 'generated/report.json', '', '', 'test', '', '2026-08-26T00:00:00Z', ?)`, placeholderAttrs); err != nil {
		t.Fatal(err)
	}
	if _, err := st.DB().ExecContext(ctx, `INSERT INTO path_index(id, generation_id, path, node_id, relation, confidence, evidence_id, updated_at) VALUES('P-parent-placeholder', 'GEN-parent-scoped', 'src/parent.go', 'N-app', 'owns', 'partial', 'E-parent-placeholder', '2026-08-26T00:00:00Z')`); err != nil {
		t.Fatal(err)
	}

	result, err := st.ApplyScopedRegistration(ctx, ScopedRegistrationInput{
		RegistrationID:       "upd-parent",
		ExpectedGenerationID: "GEN-parent-scoped",
		PacketSHA256:         "packet-parent",
		ParentUpdateID:       "upd-parent",
		ParentIntentID:       "intent-parent",
		ResultState:          "registered",
		Reason:               "parent scoped registration",
		Package: scanartifacts.Package{
			Evidence: []scanartifacts.EvidenceRow{{ID: "E-parent", SourceKind: "source", SourcePath: "src/parent.go", Extractor: "test", ContentHash: "hash-parent"}},
			Nodes:    []scanartifacts.NodeRow{{ID: "N-parent", Type: "capability", Title: "Parent", Confidence: "partial", EvidenceIDs: []string{"E-parent"}}},
			Claims:   []scanartifacts.ClaimRow{{ID: "claim:parent", NodeID: "N-parent", GraphClaimType: "runtime_owner", Summary: "parent claim", RequestedState: claim.StateSupported, SupportingEvidenceIDs: []string{"E-parent"}}},
		},
		PathIndex:    []PathIndexImport{{Path: "src/parent.go", NodeID: "N-parent", Relation: "owns", Confidence: "partial", EvidenceID: "E-parent"}},
		ChangedPaths: []string{"src/parent.go"},
		NewClaimIDs:  []string{"claim:parent"},
		Attrs: map[string]any{
			"packet_sha256": "packet-parent",
			"receipt":       map[string]any{"status": "blocked"},
		},
	})
	if err != nil {
		t.Fatal(err)
	}
	if result.ActiveGenerationID != "GEN-parent-scoped" || result.Registered["nodes"][0] != "N-parent" {
		t.Fatalf("result = %#v, want parent scoped registration result", result)
	}
	mapped, err := st.NodeIDsForExactPaths(ctx, []string{"src/parent.go"})
	if err != nil {
		t.Fatal(err)
	}
	if mapped["src/parent.go"] != "N-parent" {
		t.Fatalf("parent scoped path transfer mapped %#v, want N-parent", mapped)
	}

	var updateCount int
	if err := st.DB().QueryRowContext(ctx, `SELECT COUNT(*) FROM updates WHERE id = 'upd-parent'`).Scan(&updateCount); err != nil {
		t.Fatal(err)
	}
	if updateCount != 1 {
		t.Fatalf("update count = %d, want one parent journal row", updateCount)
	}
	var resultState, attrsJSON string
	if err := st.DB().QueryRowContext(ctx, `SELECT result_state, attrs_json FROM updates WHERE id = 'upd-parent'`).Scan(&resultState, &attrsJSON); err != nil {
		t.Fatal(err)
	}
	if resultState != "ready" {
		t.Fatalf("result_state = %q, want original parent state ready", resultState)
	}
	var attrs map[string]any
	decoder := json.NewDecoder(strings.NewReader(attrsJSON))
	decoder.UseNumber()
	if err := decoder.Decode(&attrs); err != nil {
		t.Fatal(err)
	}
	if attrs["closeout_intent_id"] != "intent-parent" || attrs["original"] != "preserved" || attrs["scope_result_state"] != "ready" {
		t.Fatalf("attrs = %#v, want original parent attrs preserved", attrs)
	}
	scoped, ok := attrs["scoped_registration"].(map[string]any)
	if !ok {
		t.Fatalf("attrs = %#v, want scoped_registration nested attrs", attrs)
	}
	if scoped["packet_sha256"] != "packet-parent" {
		t.Fatalf("scoped packet = %#v, want packet-parent", scoped["packet_sha256"])
	}
	if _, ok := scoped["scoped_registration_result"].(map[string]any); !ok {
		t.Fatalf("scoped attrs = %#v, want recoverable scoped_registration_result", scoped)
	}
}

func TestApplyScopedRegistrationRejectsParentIntentMismatchBeforeMutation(t *testing.T) {
	st := openImportTestStore(t)
	defer st.Close()
	ctx := context.Background()
	if _, err := st.ImportGeneration(ctx, validImportInput("GEN-parent-mismatch")); err != nil {
		t.Fatal(err)
	}
	if err := st.RecordStructuredUpdate(ctx, UpdateRecord{ID: "upd-parent-mismatch", Trigger: "workflow-finalize", ResultState: "ready", Attrs: map[string]any{"closeout_intent_id": "intent-good"}}); err != nil {
		t.Fatal(err)
	}
	_, err := st.ApplyScopedRegistration(ctx, ScopedRegistrationInput{
		RegistrationID:       "upd-parent-mismatch",
		ExpectedGenerationID: "GEN-parent-mismatch",
		PacketSHA256:         "packet-parent",
		ParentUpdateID:       "upd-parent-mismatch",
		ParentIntentID:       "intent-forged",
		ResultState:          "registered",
		Package:              scanartifacts.Package{Evidence: []scanartifacts.EvidenceRow{{ID: "E-should-not-insert", SourceKind: "source", SourcePath: "src/forged.go", Extractor: "test", ContentHash: "hash"}}},
		Attrs:                map[string]any{"packet_sha256": "packet-parent"},
	})
	if err == nil || !strings.Contains(err.Error(), "closeout_intent_id mismatch") {
		t.Fatalf("ApplyScopedRegistration error = %v, want closeout_intent_id mismatch", err)
	}
	var evidenceCount int
	if err := st.DB().QueryRowContext(ctx, `SELECT COUNT(*) FROM evidence WHERE id = 'E-should-not-insert'`).Scan(&evidenceCount); err != nil {
		t.Fatal(err)
	}
	if evidenceCount != 0 {
		t.Fatalf("evidence count = %d, want parent mismatch to fail before mutation", evidenceCount)
	}
	var attrsJSON string
	if err := st.DB().QueryRowContext(ctx, `SELECT attrs_json FROM updates WHERE id = 'upd-parent-mismatch'`).Scan(&attrsJSON); err != nil {
		t.Fatal(err)
	}
	if strings.Contains(attrsJSON, "scoped_registration") {
		t.Fatalf("attrs_json = %s, want no scoped registration merge", attrsJSON)
	}
}

func TestApplyScopedRegistrationReplacesOnlyPriorScopedStableRows(t *testing.T) {
	st := openImportTestStore(t)
	defer st.Close()
	ctx := context.Background()
	if _, err := st.ImportGeneration(ctx, validImportInput("GEN-scoped-stable-replace")); err != nil {
		t.Fatal(err)
	}
	first := ScopedRegistrationInput{
		RegistrationID:       "scoped-registration:first",
		ExpectedGenerationID: "GEN-scoped-stable-replace",
		PacketSHA256:         "packet-first",
		ResultState:          "registered",
		Reason:               "first scoped registration",
		Package: scanartifacts.Package{
			Evidence: []scanartifacts.EvidenceRow{{ID: "E-stable", SourceKind: "file", SourcePath: "src/stable.go", Extractor: "test", ContentHash: "hash-first"}},
			Nodes:    []scanartifacts.NodeRow{{ID: "N-stable", Type: "capability", Title: "Stable first", Confidence: "supported", EvidenceIDs: []string{"E-stable"}}},
			Claims:   []scanartifacts.ClaimRow{{ID: "claim:stable", NodeID: "N-stable", GraphClaimType: "runtime_owner", Summary: "first claim", RequestedState: claim.StateSupported, SupportingEvidenceIDs: []string{"E-stable"}}},
		},
		PathIndex:    []PathIndexImport{{ID: "P-stable", Path: "src/stable.go", NodeID: "N-stable", Relation: "owns", Confidence: "supported", EvidenceID: "E-stable"}},
		Aliases:      []AliasImport{{ID: "A-stable", Alias: "Stable first", NormalizedAlias: "stable first", TargetType: "node", TargetID: "N-stable", Source: "scoped_registration", Confidence: "supported", EvidenceID: "E-stable"}},
		ChangedPaths: []string{"src/stable.go"},
		NewClaimIDs:  []string{"claim:stable"},
		Attrs:        map[string]any{"packet_sha256": "packet-first", "native_proof": map[string]any{"kind": "strong", "binding_id": "owner-one", "workflow": "sp-do", "scope": ".specify/do/sessions/fixture"}},
	}
	if _, err := st.ApplyScopedRegistration(ctx, first); err != nil {
		t.Fatal(err)
	}
	second := first
	second.RegistrationID = "scoped-registration:second"
	second.PacketSHA256 = "packet-second"
	second.Reason = "second scoped registration"
	second.Package.Evidence[0].ContentHash = "hash-second"
	second.Package.Nodes[0].Title = "Stable second"
	second.Package.Claims[0].Summary = "second claim"
	second.Aliases[0].Alias = "Stable second"
	second.Aliases[0].NormalizedAlias = "stable second"
	second.Attrs = map[string]any{"packet_sha256": "packet-second", "native_proof": map[string]any{"kind": "strong", "binding_id": "owner-one", "workflow": "sp-do", "scope": ".specify/do/sessions/fixture"}}
	if _, err := st.ApplyScopedRegistration(ctx, second); err != nil {
		t.Fatal(err)
	}
	var nodeTitle, evidenceHash, claimSummary string
	if err := st.DB().QueryRowContext(ctx, `SELECT title FROM nodes WHERE id = 'N-stable'`).Scan(&nodeTitle); err != nil {
		t.Fatal(err)
	}
	if err := st.DB().QueryRowContext(ctx, `SELECT content_hash FROM evidence WHERE id = 'E-stable'`).Scan(&evidenceHash); err != nil {
		t.Fatal(err)
	}
	if err := st.DB().QueryRowContext(ctx, `SELECT summary FROM claims WHERE id = 'claim:stable'`).Scan(&claimSummary); err != nil {
		t.Fatal(err)
	}
	if nodeTitle != "Stable second" || evidenceHash != "hash-second" || claimSummary != "second claim" {
		t.Fatalf("stable successor did not replace scoped rows: title=%q hash=%q claim=%q", nodeTitle, evidenceHash, claimSummary)
	}
	var staleTransitions int
	if err := st.DB().QueryRowContext(ctx, `SELECT COUNT(*) FROM claim_transitions WHERE claim_id = 'claim:stable' AND to_state = 'stale'`).Scan(&staleTransitions); err != nil {
		t.Fatal(err)
	}
	if staleTransitions != 1 {
		t.Fatalf("stale predecessor transitions = %d, want 1", staleTransitions)
	}
	conflict := first
	conflict.RegistrationID = "scoped-registration:conflict"
	conflict.PacketSHA256 = "packet-conflict"
	conflict.Attrs = map[string]any{"packet_sha256": "packet-conflict", "native_proof": map[string]any{"kind": "strong", "binding_id": "owner-two", "workflow": "sp-do", "scope": ".specify/do/sessions/other"}}
	conflict.Package.Nodes = []scanartifacts.NodeRow{{ID: "N-stable", Type: "capability", Title: "Foreign conflict", Confidence: "supported", EvidenceIDs: []string{"E-stable"}}}
	conflict.Package.Claims = nil
	conflict.PathIndex = nil
	conflict.Aliases = nil
	conflict.NewClaimIDs = nil
	_, err := st.ApplyScopedRegistration(ctx, conflict)
	if err == nil || !strings.Contains(err.Error(), "different scoped registration owner") {
		t.Fatalf("ApplyScopedRegistration conflict error = %v, want different scoped owner refusal", err)
	}
	if err := st.DB().QueryRowContext(ctx, `SELECT title FROM nodes WHERE id = 'N-stable'`).Scan(&nodeTitle); err != nil {
		t.Fatal(err)
	}
	if nodeTitle != "Stable second" {
		t.Fatalf("foreign owner changed prior scoped row title to %q", nodeTitle)
	}
}

func TestUpdateScopedRegistrationReceiptPreservesParentJournalAttrs(t *testing.T) {
	st := openImportTestStore(t)
	defer st.Close()
	ctx := context.Background()
	if _, err := st.ImportGeneration(ctx, validImportInput("GEN-parent-receipt")); err != nil {
		t.Fatal(err)
	}
	if err := st.RecordStructuredUpdate(ctx, UpdateRecord{ID: "upd-parent-receipt", Trigger: "workflow-finalize", ResultState: "ready", Attrs: map[string]any{"closeout_intent_id": "intent-parent", "original": "preserved"}}); err != nil {
		t.Fatal(err)
	}
	if _, err := st.ApplyScopedRegistration(ctx, ScopedRegistrationInput{
		RegistrationID:       "upd-parent-receipt",
		ExpectedGenerationID: "GEN-parent-receipt",
		PacketSHA256:         "packet-parent-receipt",
		ParentUpdateID:       "upd-parent-receipt",
		ParentIntentID:       "intent-parent",
		ResultState:          "registered",
		Attrs:                map[string]any{"packet_sha256": "packet-parent-receipt", "receipt": map[string]any{"status": "blocked"}},
	}); err != nil {
		t.Fatal(err)
	}
	if err := st.UpdateScopedRegistrationReceipt(ctx, "GEN-parent-receipt", "upd-parent-receipt", "packet-parent-receipt", map[string]any{
		"packet_sha256": "packet-parent-receipt",
		"receipt":       map[string]any{"status": "ok"},
	}); err != nil {
		t.Fatal(err)
	}
	var attrsJSON string
	if err := st.DB().QueryRowContext(ctx, `SELECT attrs_json FROM updates WHERE id = 'upd-parent-receipt'`).Scan(&attrsJSON); err != nil {
		t.Fatal(err)
	}
	var attrs map[string]any
	decoder := json.NewDecoder(strings.NewReader(attrsJSON))
	decoder.UseNumber()
	if err := decoder.Decode(&attrs); err != nil {
		t.Fatal(err)
	}
	if attrs["original"] != "preserved" || attrs["closeout_intent_id"] != "intent-parent" {
		t.Fatalf("attrs = %#v, want parent attrs preserved after receipt", attrs)
	}
	scoped := attrs["scoped_registration"].(map[string]any)
	receipt := scoped["receipt"].(map[string]any)
	if receipt["status"] != "ok" {
		t.Fatalf("receipt = %#v, want finalized ok receipt nested under scoped_registration", receipt)
	}
}
