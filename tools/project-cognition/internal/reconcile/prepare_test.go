package reconcile

import (
	"context"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"

	"github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/claim"
	rt "github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/runtime"
	"github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/store"
)

func TestParsePrepareRequestAcceptsOnlyCurrentSemanticDecisionContract(t *testing.T) {
	raw := []byte(`{
  "claim_reconciliation_prepare_contract_version": 1,
  "workflow": "sp-implement",
  "items": [{
    "claim_id": "claim:app-owner",
    "reason": "bounded live read and claim-specific test",
    "evidence": [{
      "source_path": "src/./app.go",
      "span": "L1-L20",
      "role": "supporting"
    }],
    "verification": {"result": "passed", "command": "go test ./src/..."}
  }]
}`)
	request, err := ParsePrepareRequest(raw)
	if err != nil {
		t.Fatal(err)
	}
	if request.ContractVersion != CurrentPrepareContractVersion || request.Workflow != "sp-implement" {
		t.Fatalf("request = %#v, want current prepare contract", request)
	}
	if got := request.Items[0].Evidence[0].SourcePath; got != "src/app.go" {
		t.Fatalf("source path = %q, want canonical repository-relative path", got)
	}

	for name, invalid := range map[string]string{
		"legacy version":         strings.Replace(string(raw), `"claim_reconciliation_prepare_contract_version": 1`, `"claim_reconciliation_prepare_contract_version": 0`, 1),
		"agent generation":       strings.Replace(string(raw), `"workflow": "sp-implement",`, `"workflow": "sp-implement", "expected_generation_id": "GEN-current",`, 1),
		"agent observation time": strings.Replace(string(raw), `"workflow": "sp-implement",`, `"workflow": "sp-implement", "observed_at": "2026-07-13T09:00:00Z",`, 1),
		"agent expected state":   strings.Replace(string(raw), `"claim_id": "claim:app-owner",`, `"claim_id": "claim:app-owner", "expected_state": "stale",`, 1),
		"agent target state":     strings.Replace(string(raw), `"claim_id": "claim:app-owner",`, `"claim_id": "claim:app-owner", "requested_state": "verified_in_graph_generation",`, 1),
		"agent content hash":     strings.Replace(string(raw), `"role": "supporting"`, `"role": "supporting", "expected_content_hash": "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"`, 1),
		"agent source kind":      strings.Replace(string(raw), `"source_path": "src/./app.go",`, `"source_kind": "source", "source_path": "src/./app.go",`, 1),
	} {
		t.Run(name, func(t *testing.T) {
			if _, err := ParsePrepareRequest([]byte(invalid)); err == nil {
				t.Fatal("ParsePrepareRequest succeeded, want mechanical-field rejection")
			}
		})
	}
}

func TestPrepareDerivesSnapshotHashesTimestampAndCanonicalPacket(t *testing.T) {
	root, paths := seedPrepareRepository(t)
	appContent, err := os.ReadFile(filepath.Join(root, "src", "app.go"))
	if err != nil {
		t.Fatal(err)
	}
	testContent, err := os.ReadFile(filepath.Join(root, "src", "app_test.go"))
	if err != nil {
		t.Fatal(err)
	}
	request := PrepareRequest{
		ContractVersion: CurrentPrepareContractVersion,
		Workflow:        " sp-implement ",
		Items: []PrepareItem{
			{
				ClaimID: "claim:z-owner", Reason: " source and test confirm owner ",
				Evidence: []PrepareEvidence{
					{SourcePath: `src\app_test.go`, Span: "L1-L20", Role: "supporting"},
					{SourcePath: "src/./app.go", Span: "L1-L20", Role: "supporting"},
				},
				Verification: &Verification{Result: claim.VerificationPassed, Command: " go test ./src/... "},
			},
			{
				ClaimID: "claim:a-contract", Reason: "live config contradicts the route",
				Evidence: []PrepareEvidence{{SourcePath: "config/runtime.json", Span: "L1", Role: "contradicting"}},
			},
		},
	}
	observedAt := time.Now().UTC()
	prepared, err := prepareAt(paths, request, observedAt)
	if err != nil {
		t.Fatal(err)
	}
	if prepared.Status != "ok" || prepared.ResultState != "prepared" || prepared.ContractVersion != CurrentPrepareContractVersion {
		t.Fatalf("prepared = %#v, want compact current prepare payload", prepared)
	}
	if prepared.PreparedPacketPath == "" || len(prepared.ApplyArgv) != 7 {
		t.Fatalf("prepared = %#v, want runtime packet path and structured apply argv", prepared)
	}
	if strings.Join(prepared.ApplyArgv, " ") != "project-cognition claim-reconcile apply --input "+prepared.PreparedPacketPath+" --format json" {
		t.Fatalf("apply_argv = %#v", prepared.ApplyArgv)
	}
	packetBytes, err := os.ReadFile(filepath.Join(root, filepath.FromSlash(prepared.PreparedPacketPath)))
	if err != nil {
		t.Fatal(err)
	}
	packet, err := ParsePacket(packetBytes)
	if err != nil {
		t.Fatalf("parse runtime-prepared packet: %v", err)
	}
	if packet.ContractVersion != CurrentContractVersion || packet.ExpectedGenerationID != "GEN-current" || packet.Workflow != "sp-implement" {
		t.Fatalf("packet header = %#v, want runtime-derived current packet", packet)
	}
	if packet.ObservedAt != observedAt.Format(time.RFC3339Nano) {
		t.Fatalf("observed_at = %q, want %q", packet.ObservedAt, observedAt.Format(time.RFC3339Nano))
	}
	if len(packet.Items) != 2 || packet.Items[0].ClaimID != "claim:a-contract" || packet.Items[1].ClaimID != "claim:z-owner" {
		t.Fatalf("items = %#v, want canonical claim ordering", packet.Items)
	}
	if packet.Items[0].ExpectedState != claim.StateContradicted || packet.Items[1].ExpectedState != claim.StateStale {
		t.Fatalf("expected states = %q, %q, want active graph snapshot", packet.Items[0].ExpectedState, packet.Items[1].ExpectedState)
	}
	ownerEvidence := packet.Items[1].Evidence
	if len(ownerEvidence) != 2 || ownerEvidence[0].SourcePath != "src/app.go" || ownerEvidence[1].SourcePath != "src/app_test.go" {
		t.Fatalf("owner evidence = %#v, want canonical path ordering", ownerEvidence)
	}
	if ownerEvidence[0].SourceKind != "source" || ownerEvidence[1].SourceKind != "test" || packet.Items[0].Evidence[0].SourceKind != "config" {
		t.Fatalf("derived source kinds = %#v / %#v, want runtime path classification", ownerEvidence, packet.Items[0].Evidence)
	}
	if ownerEvidence[0].ExpectedContentHash != reconcileHash(appContent) || ownerEvidence[1].ExpectedContentHash != reconcileHash(testContent) {
		t.Fatalf("owner hashes = %#v, want runtime-computed file hashes", ownerEvidence)
	}

	payload, err := Run(paths, packet)
	if err != nil {
		t.Fatalf("prepared packet was not directly applicable: %v", err)
	}
	if payload.Status != "ok" || payload.ResultState != "ready" || len(payload.ReconciledClaims) != 2 {
		t.Fatalf("payload = %#v, want direct prepare-to-apply success", payload)
	}
}

func TestPrepareRejectsMissingClaimsAndUnsafeIgnoredOrDuplicateEvidenceWithoutMutation(t *testing.T) {
	root, paths := seedPrepareRepository(t)
	outside := filepath.Join(filepath.Dir(root), "outside.go")
	if err := os.WriteFile(outside, []byte("outside"), 0o644); err != nil {
		t.Fatal(err)
	}
	defer os.Remove(outside)

	base := PrepareRequest{
		ContractVersion: CurrentPrepareContractVersion,
		Workflow:        "sp-plan",
		Items: []PrepareItem{{
			ClaimID: "claim:z-owner", Reason: "bounded evidence",
			Evidence: []PrepareEvidence{{SourcePath: "src/app.go", Span: "L1", Role: "supporting"}},
		}},
	}
	for name, mutate := range map[string]func(*PrepareRequest){
		"missing claim": func(request *PrepareRequest) { request.Items[0].ClaimID = "claim:missing" },
		"path traversal": func(request *PrepareRequest) {
			request.Items[0].Evidence[0].SourcePath = "../outside.go"
		},
		"ignored runtime path": func(request *PrepareRequest) {
			request.Items[0].Evidence[0].SourcePath = ".specify/project-cognition/status.json"
		},
		"duplicate evidence": func(request *PrepareRequest) {
			request.Items[0].Evidence = append(request.Items[0].Evidence, request.Items[0].Evidence[0])
		},
	} {
		t.Run(name, func(t *testing.T) {
			request := clonePrepareRequest(base)
			mutate(&request)
			if _, err := prepareAt(paths, request, time.Now().UTC()); err == nil {
				t.Fatal("prepareAt succeeded, want preflight rejection")
			}
			st, err := store.Open(paths)
			if err != nil {
				t.Fatal(err)
			}
			defer st.Close()
			var count int
			if err := st.DB().QueryRow(`SELECT COUNT(*) FROM claim_reconciliations`).Scan(&count); err != nil {
				t.Fatal(err)
			}
			if count != 0 {
				t.Fatalf("claim_reconciliations = %d, want prepare to remain read-only", count)
			}
		})
	}
}

func TestParsePrepareRequestRejectsMalformedTrailingAndIncompleteInput(t *testing.T) {
	for name, raw := range map[string]string{
		"multiple values": `{}` + " " + `{}`,
		"malformed":       `{"claim_reconciliation_prepare_contract_version":`,
		"empty":           `{"claim_reconciliation_prepare_contract_version":1,"workflow":"sp-plan","items":[]}`,
	} {
		t.Run(name, func(t *testing.T) {
			if _, err := ParsePrepareRequest([]byte(raw)); err == nil {
				t.Fatal("ParsePrepareRequest succeeded, want rejection")
			}
		})
	}
}

func seedPrepareRepository(t *testing.T) (string, rt.Paths) {
	t.Helper()
	root := t.TempDir()
	if err := os.MkdirAll(filepath.Join(root, ".specify"), 0o755); err != nil {
		t.Fatal(err)
	}
	writeReconcileFile(t, root, "src/app.go", []byte("package app\n\nfunc Owner() string { return \"app\" }\n"))
	writeReconcileFile(t, root, "src/app_test.go", []byte("package app\n\nfunc TestOwner() {}\n"))
	writeReconcileFile(t, root, "config/runtime.json", []byte("{\"owner\":\"other\"}\n"))
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
		Nodes: []store.NodeImport{
			{ID: "N-app", Type: "capability", Title: "App", Confidence: "verified", EvidenceIDs: []string{"E-old"}},
			{ID: "N-contract", Type: "contract", Title: "Contract", Confidence: "verified", EvidenceIDs: []string{"E-old"}},
		},
		Claims: []store.ClaimImport{
			{ID: "claim:z-owner", NodeID: "N-app", GraphClaimType: "runtime_owner", Summary: "App owns runtime behavior", State: claim.StateStale, PriorState: claim.StateSupported, Freshness: claim.FreshnessStale, StateReason: "changed_path", SupportingEvidenceIDs: []string{"E-old"}},
			{ID: "claim:a-contract", NodeID: "N-contract", GraphClaimType: "contract", Summary: "Contract route is current", State: claim.StateContradicted, PriorState: claim.StateSupported, Freshness: claim.FreshnessFresh, StateReason: "counterexample", SupportingEvidenceIDs: []string{"E-old"}},
		},
	}
	if _, err := st.ImportGeneration(context.Background(), seed); err != nil {
		t.Fatal(err)
	}
	if err := st.Close(); err != nil {
		t.Fatal(err)
	}
	return root, paths
}
