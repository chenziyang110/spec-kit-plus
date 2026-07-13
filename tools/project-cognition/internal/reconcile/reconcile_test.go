package reconcile

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/claim"
	rt "github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/runtime"
	"github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/store"
)

func TestParsePacketAcceptsOnlyCurrentDerivedStateContract(t *testing.T) {
	raw := []byte(`{
  "claim_reconciliation_contract_version": 1,
  "expected_generation_id": "GEN-current",
  "workflow": "sp-implement",
  "observed_at": "2026-07-13T10:00:00Z",
  "items": [{
    "claim_id": "claim:app-owner",
    "expected_state": "stale",
    "reason": "bounded live read and claim-specific test",
    "evidence": [{
      "source_kind": "source",
	      "source_path": "src/./app.go",
      "span": "L1-L20",
      "role": "supporting",
      "expected_content_hash": "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    }],
    "verification": {"result": "passed", "command": "go test ./src/..."}
  }]
}`)
	packet, err := ParsePacket(raw)
	if err != nil {
		t.Fatal(err)
	}
	if packet.ContractVersion != CurrentContractVersion || packet.Items[0].ExpectedState != claim.StateStale {
		t.Fatalf("packet = %#v, want current contract and expected stale state", packet)
	}
	if packet.Items[0].Evidence[0].SourcePath != "src/app.go" {
		t.Fatalf("source path = %q, want canonical repository-relative path", packet.Items[0].Evidence[0].SourcePath)
	}

	for name, invalid := range map[string]string{
		"legacy version":                     strings.Replace(string(raw), `"claim_reconciliation_contract_version": 1`, `"claim_reconciliation_contract_version": 0`, 1),
		"requested target state":             strings.Replace(string(raw), `"expected_state": "stale",`, `"expected_state": "stale", "requested_state": "verified_in_graph_generation",`, 1),
		"passed without supporting evidence": strings.Replace(string(raw), `"role": "supporting"`, `"role": "contradicting"`, 1),
	} {
		t.Run(name, func(t *testing.T) {
			if _, err := ParsePacket([]byte(invalid)); err == nil {
				t.Fatal("ParsePacket succeeded, want current-contract rejection")
			}
		})
	}
}

func TestRunReReadsBoundedEvidenceAndReturnsAdvisoryReconciliation(t *testing.T) {
	root := t.TempDir()
	if err := os.MkdirAll(filepath.Join(root, ".specify"), 0o755); err != nil {
		t.Fatal(err)
	}
	content := []byte("package app\n\nfunc Owner() string { return \"app\" }\n")
	writeReconcileFile(t, root, "src/app.go", content)
	paths, err := rt.ResolvePaths(root)
	if err != nil {
		t.Fatal(err)
	}
	st, err := store.Open(paths)
	if err != nil {
		t.Fatal(err)
	}
	seed := store.ImportInput{
		GenerationID: "GEN-current", Kind: "full", SourceCommit: "abc123",
		Evidence: []store.EvidenceImport{{ID: "E-old", SourceKind: "source", SourcePath: "src/app.go", CommitSHA: "abc123", Extractor: "test", ContentHash: "old"}},
		Nodes:    []store.NodeImport{{ID: "N-app", Type: "capability", Title: "App", Confidence: "verified", EvidenceIDs: []string{"E-old"}}},
		Claims: []store.ClaimImport{{
			ID: "claim:app-owner", NodeID: "N-app", GraphClaimType: "runtime_owner", Summary: "App owns runtime behavior",
			State: claim.StateStale, PriorState: claim.StateSupported, Freshness: claim.FreshnessStale, StateReason: "changed_path", SupportingEvidenceIDs: []string{"E-old"},
		}},
	}
	if _, err := st.ImportGeneration(context.Background(), seed); err != nil {
		t.Fatal(err)
	}
	if err := st.Close(); err != nil {
		t.Fatal(err)
	}

	packet := Packet{
		ContractVersion: CurrentContractVersion, ExpectedGenerationID: "GEN-current", Workflow: "sp-implement", ObservedAt: "2026-07-13T10:00:00Z",
		Items: []Item{{
			ClaimID: "claim:app-owner", ExpectedState: claim.StateStale, Reason: "bounded live evidence confirms owner",
			Evidence:     []Evidence{{SourceKind: "source", SourcePath: "src/app.go", Span: "L1-L3", Role: "supporting", ExpectedContentHash: reconcileHash(content)}},
			Verification: &Verification{Result: claim.VerificationPassed, Command: "go test ./src/..."},
		}},
	}
	payload, err := Run(paths, packet)
	if err != nil {
		t.Fatal(err)
	}
	if payload.Status != "ok" || payload.ResultState != "ready" || payload.ContractVersion != CurrentContractVersion {
		t.Fatalf("payload = %#v, want ready current reconciliation", payload)
	}
	if payload.EpistemicContract.GraphRole != "route_candidate_only" || !payload.EpistemicContract.LiveVerificationRequired || payload.EpistemicContract.GraphOnlyClaimsAllowed {
		t.Fatalf("epistemic contract = %#v, want advisory graph boundary", payload.EpistemicContract)
	}
	if len(payload.ReconciledClaims) != 1 || payload.ReconciledClaims[0].ToState != claim.StateVerified {
		t.Fatalf("claims = %#v, want graph-generation verified", payload.ReconciledClaims)
	}

	replayed, err := Run(paths, packet)
	if err != nil {
		t.Fatal(err)
	}
	if !replayed.Replayed || replayed.ReconciliationID != payload.ReconciliationID {
		t.Fatalf("replay = %#v, want stable idempotent reconciliation", replayed)
	}
}

func TestRunRejectsHashMismatchAndUnsafeOrIgnoredPathsBeforeWriting(t *testing.T) {
	root := t.TempDir()
	if err := os.MkdirAll(filepath.Join(root, ".specify"), 0o755); err != nil {
		t.Fatal(err)
	}
	writeReconcileFile(t, root, "src/app.go", []byte("current"))
	paths, err := rt.ResolvePaths(root)
	if err != nil {
		t.Fatal(err)
	}

	base := Packet{
		ContractVersion: CurrentContractVersion, ExpectedGenerationID: "GEN-current", Workflow: "sp-plan", ObservedAt: "2026-07-13T10:00:00Z",
		Items: []Item{{
			ClaimID: "claim:app-owner", ExpectedState: claim.StateStale, Reason: "bounded read",
			Evidence:     []Evidence{{SourceKind: "source", SourcePath: "src/app.go", Span: "L1", Role: "supporting", ExpectedContentHash: "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"}},
			Verification: &Verification{Result: claim.VerificationPassed, Command: "go test ./..."},
		}},
	}
	for name, mutate := range map[string]func(*Packet){
		"hash mismatch":  func(*Packet) {},
		"path traversal": func(packet *Packet) { packet.Items[0].Evidence[0].SourcePath = "../outside.go" },
		"ignored runtime path": func(packet *Packet) {
			packet.Items[0].Evidence[0].SourcePath = ".specify/project-cognition/status.json"
		},
	} {
		t.Run(name, func(t *testing.T) {
			packet := base
			packet.Items = append([]Item(nil), base.Items...)
			packet.Items[0].Evidence = append([]Evidence(nil), base.Items[0].Evidence...)
			mutate(&packet)
			if _, err := Run(paths, packet); err == nil {
				t.Fatal("Run succeeded, want evidence preflight rejection")
			}
			if _, err := os.Stat(paths.DatabasePath); !os.IsNotExist(err) {
				t.Fatalf("database stat error = %v, want no store write before evidence passes", err)
			}
		})
	}
}

func writeReconcileFile(t *testing.T, root, relative string, data []byte) {
	t.Helper()
	path := filepath.Join(root, filepath.FromSlash(relative))
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(path, data, 0o644); err != nil {
		t.Fatal(err)
	}
}

func reconcileHash(data []byte) string {
	digest := sha256.Sum256(data)
	return "sha256:" + hex.EncodeToString(digest[:])
}

func TestPayloadRemainsCompactAndMachineReadable(t *testing.T) {
	payload := Payload{Status: "ok", ResultState: "ready", ContractVersion: CurrentContractVersion, ReconciledClaims: []store.ClaimReconciliationRecord{}}
	data, err := json.Marshal(payload)
	if err != nil {
		t.Fatal(err)
	}
	if strings.Contains(string(data), "claim_ready") || strings.Contains(string(data), "workflow_authorization") {
		t.Fatalf("payload leaks semantic-audit authorization namespace: %s", data)
	}
}

func TestBlockedPayloadUsesCurrentMachineReadableContract(t *testing.T) {
	payload := BlockedPayload(os.ErrPermission)
	if payload.Status != "error" || payload.ResultState != "blocked" || payload.ContractVersion != CurrentContractVersion {
		t.Fatalf("payload = %#v, want blocked current contract", payload)
	}
	if payload.ErrorCode != "invalid_claim_reconciliation" || len(payload.Errors) != 1 || !strings.Contains(payload.Errors[0], "permission") {
		t.Fatalf("payload errors = %#v, want normalized permission error", payload)
	}
}

func TestPacketValidationRejectsAmbiguousOrIncompleteInputs(t *testing.T) {
	validEvidence := Evidence{
		SourceKind: "source", SourcePath: "src/app.go", Span: "L1", Role: "supporting",
		ExpectedContentHash: "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
	}
	valid := Packet{
		ContractVersion: CurrentContractVersion, ExpectedGenerationID: "GEN-current", Workflow: "sp-plan", ObservedAt: "2026-07-13T10:00:00Z",
		Items: []Item{{
			ClaimID: "claim:app", ExpectedState: claim.StateStale, Reason: "bounded read", Evidence: []Evidence{validEvidence},
			Verification: &Verification{Result: claim.VerificationPassed, Command: "go test ./..."},
		}},
	}
	tests := map[string]func(*Packet){
		"missing generation":        func(packet *Packet) { packet.ExpectedGenerationID = "" },
		"invalid observed time":     func(packet *Packet) { packet.ObservedAt = "yesterday" },
		"future observed time":      func(packet *Packet) { packet.ObservedAt = "2099-01-01T00:00:00Z" },
		"missing items":             func(packet *Packet) { packet.Items = nil },
		"invalid expected state":    func(packet *Packet) { packet.Items[0].ExpectedState = "verified" },
		"duplicate claim":           func(packet *Packet) { packet.Items = append(packet.Items, packet.Items[0]) },
		"missing evidence":          func(packet *Packet) { packet.Items[0].Evidence = nil; packet.Items[0].Verification = nil },
		"invalid source kind":       func(packet *Packet) { packet.Items[0].Evidence[0].SourceKind = "agent_memory" },
		"invalid content hash":      func(packet *Packet) { packet.Items[0].Evidence[0].ExpectedContentHash = "hash" },
		"invalid evidence role":     func(packet *Packet) { packet.Items[0].Evidence[0].Role = "authoritative" },
		"missing command":           func(packet *Packet) { packet.Items[0].Verification.Command = "" },
		"invalid verification":      func(packet *Packet) { packet.Items[0].Verification.Result = "unknown" },
		"contradiction without ref": func(packet *Packet) { packet.Items[0].Verification.Result = claim.VerificationContradicted },
	}
	for name, mutate := range tests {
		t.Run(name, func(t *testing.T) {
			packet := clonePacket(valid)
			mutate(&packet)
			if _, err := normalizeAndValidatePacket(packet); err == nil {
				t.Fatal("normalizeAndValidatePacket succeeded, want rejection")
			}
		})
	}
}

func TestParsePacketRejectsTrailingJSONValues(t *testing.T) {
	if _, err := ParsePacket([]byte(`{} {}`)); err == nil {
		t.Fatal("ParsePacket accepted multiple JSON values")
	}
	if _, err := ParsePacket([]byte(`{"claim_reconciliation_contract_version":`)); err == nil {
		t.Fatal("ParsePacket accepted malformed JSON")
	}
}
