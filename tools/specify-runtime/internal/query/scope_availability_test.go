package query

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"reflect"
	"strings"
	"testing"

	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/claim"
	rt "github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/runtime"
	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/store"
)

func scopeFixture(t *testing.T, connected bool) rt.Paths {
	t.Helper()
	paths := queryTestPaths(t)
	input := store.ImportInput{GenerationID: "GEN-scope", Kind: "full", SourceCommit: "source"}
	for _, id := range []string{"a", "b", "consumer"} {
		path := "src/" + id + ".go"
		data := []byte("package " + id + "\n")
		if err := os.MkdirAll(filepath.Join(paths.Root, "src"), 0755); err != nil {
			t.Fatal(err)
		}
		if err := os.WriteFile(filepath.Join(paths.Root, filepath.FromSlash(path)), data, 0644); err != nil {
			t.Fatal(err)
		}
		input.Evidence = append(input.Evidence, store.EvidenceImport{ID: "E-" + id, SourceKind: "source", SourcePath: path, ContentHash: scopeDigest(data), Span: "L1", Extractor: "test"})
		input.Nodes = append(input.Nodes, store.NodeImport{ID: "N-" + id, Type: "capability", Title: id, Confidence: "high", EvidenceIDs: []string{"E-" + id}})
		input.PathIndex = append(input.PathIndex, store.PathIndexImport{ID: "P-" + id, Path: path, NodeID: "N-" + id, Relation: "owns", Confidence: "high", EvidenceID: "E-" + id})
		input.Claims = append(input.Claims, store.ClaimImport{ID: "claim:" + id, NodeID: "N-" + id, GraphClaimType: "runtime_owner", Summary: id, State: claim.StateSupported, Freshness: claim.FreshnessFresh, SupportingEvidenceIDs: []string{"E-" + id}})
	}
	if connected {
		input.Edges = []store.EdgeImport{{ID: "edge:a-consumer", Type: "consumed_by", SourceID: "N-a", TargetID: "N-consumer", Confidence: "high", EvidenceIDs: []string{"E-a"}}, {ID: "edge:b-consumer", Type: "depends_on", SourceID: "N-b", TargetID: "N-consumer", Confidence: "high", EvidenceIDs: []string{"E-b"}}}
	}
	seedReadyGraph(t, paths, input)
	scopePacket(t, paths, []string{"src/a.go"}, []string{"src/a.go"})
	return paths
}

func scopePacket(t *testing.T, paths rt.Paths, reads, writes []string) {
	t.Helper()
	if reads == nil {
		reads = []string{}
	}
	if writes == nil {
		writes = []string{}
	}
	data, _ := json.Marshal(map[string]any{"version": 2, "feature_id": "scope-feature", "task_id": "T01", "read_scope": reads, "write_scope": writes, "objective": "change a"})
	if err := os.WriteFile(filepath.Join(paths.Root, "packet.json"), data, 0644); err != nil {
		t.Fatal(err)
	}
}

func scopeDebt(t *testing.T, paths rt.Paths, debt rt.DebtRecord) {
	t.Helper()
	status, err := rt.ReadStatus(paths)
	if err != nil {
		t.Fatal(err)
	}
	status.DirtyDebts = []rt.DebtRecord{debt}
	status.Freshness = rt.StaleFreshness
	status.Readiness = rt.ReviewReadiness
	if err := rt.WriteStatus(paths, status); err != nil {
		t.Fatal(err)
	}
}

func TestScopeAvailabilitySeparatesGlobalDebtAndNeverWritesAuthority(t *testing.T) {
	paths := scopeFixture(t, false)
	scopeDebt(t, paths, rt.DebtRecord{ID: "debt-b", Kind: "mark_dirty", Paths: []string{"src/b.go"}, Reason: "b review pending"})
	before, err := os.ReadFile(paths.StatusPath)
	if err != nil {
		t.Fatal(err)
	}
	payload, err := CheckScopeAvailability(paths, "packet.json", nil)
	if err != nil {
		t.Fatal(err)
	}
	if !payload.ScopeReady || payload.Availability != "ready" || len(payload.Debt) != 1 || payload.Debt[0].Relation != "unrelated" || payload.GlobalStatus.Freshness == rt.ReadyFreshness || len(payload.GlobalStatus.DirtyDebts) != 1 {
		t.Fatalf("unrelated debt was lost or blocked scope: %#v", payload)
	}
	if payload.Policy.Classification != "local" || payload.ClaimReady || payload.SourceChangesAuthorized || !payload.ReviewRequired || !payload.HumanAcceptRequired || payload.EpistemicContract.GraphOnlyClaimsAllowed {
		t.Fatalf("invalid authority boundary: %#v", payload)
	}
	after, err := os.ReadFile(paths.StatusPath)
	if err != nil || !reflect.DeepEqual(before, after) {
		t.Fatal("read changed global status")
	}
	if _, err := CheckScopeAvailability(paths, "packet.json", &payload.Binding); err != nil {
		t.Fatal(err)
	}
}

func TestScopeAvailabilityRelatedAndUnknownDebtRequireLiveFallback(t *testing.T) {
	for _, test := range []struct {
		name      string
		connected bool
		paths     []string
		relation  string
	}{{"direct-read", false, []string{"src/a.go"}, "related"}, {"propagated", true, []string{"src/b.go"}, "related"}, {"empty", false, nil, "unknown"}, {"unindexed", false, []string{"src/unknown.go"}, "unknown"}} {
		t.Run(test.name, func(t *testing.T) {
			paths := scopeFixture(t, test.connected)
			scopeDebt(t, paths, rt.DebtRecord{ID: "debt", Kind: "mark_dirty", Paths: test.paths, Reason: "pending"})
			p, err := CheckScopeAvailability(paths, "packet.json", nil)
			if err != nil {
				t.Fatal(err)
			}
			if p.ScopeReady || p.Availability != "degraded" || len(p.MinimalLiveReads) == 0 || p.Debt[0].Relation != test.relation {
				t.Fatalf("unsafe debt assessment: %#v", p)
			}
			if test.connected && p.Policy.Classification != "propagated" {
				t.Fatalf("closure classification=%#v", p.Policy)
			}
		})
	}
}

func TestScopeAvailabilityReadDependencyIsNotIgnored(t *testing.T) {
	paths := scopeFixture(t, false)
	scopePacket(t, paths, []string{"src/b.go"}, []string{"src/a.go"})
	scopeDebt(t, paths, rt.DebtRecord{ID: "read-debt", Kind: "mark_dirty", Paths: []string{"src/b.go"}, Reason: "pending read"})
	p, err := CheckScopeAvailability(paths, "packet.json", nil)
	if err != nil {
		t.Fatal(err)
	}
	if p.ScopeReady || p.Debt[0].Relation != "related" {
		t.Fatalf("read dependency omitted: %#v", p)
	}
	if p.Policy.Classification != "local" {
		t.Fatalf("independent read dependency fabricated write propagation: %#v", p.Policy)
	}
}

func TestScopeAvailabilitySameGenerationCapsuleInvalidation(t *testing.T) {
	for _, kind := range []string{"source-bytes", "packet-scope", "claim-revision", "dependency-edge", "status-debt", "claim-state", "claim-evidence-dependency"} {
		t.Run(kind, func(t *testing.T) {
			paths := scopeFixture(t, false)
			before, err := CheckScopeAvailability(paths, "packet.json", nil)
			if err != nil || !before.ScopeReady {
				t.Fatalf("before=%#v err=%v", before, err)
			}
			switch kind {
			case "source-bytes":
				path := filepath.Join(paths.Root, "src/a.go")
				info, _ := os.Stat(path)
				if err := os.WriteFile(path, []byte("package z\n"), 0644); err != nil {
					t.Fatal(err)
				}
				_ = os.Chtimes(path, info.ModTime(), info.ModTime())
			case "packet-scope":
				scopePacket(t, paths, []string{"src/a.go", "src/b.go"}, []string{"src/a.go"})
			case "status-debt":
				scopeDebt(t, paths, rt.DebtRecord{ID: "new-debt", Kind: "mark_dirty", Paths: []string{"src/b.go"}, Reason: "pending"})
			default:
				st, err := store.OpenExisting(paths)
				if err != nil {
					t.Fatal(err)
				}
				statement := map[string]string{"claim-revision": `UPDATE claims SET revision=revision+1 WHERE id='claim:a'`, "dependency-edge": `INSERT INTO edges(id,generation_id,type,source_id,target_id,confidence,attrs_json,created_at,updated_at) VALUES('new-edge','GEN-scope','depends_on','N-a','N-b','high','{}','','')`, "claim-state": `UPDATE claims SET state='stale',freshness='stale' WHERE id='claim:a'`, "claim-evidence-dependency": `INSERT INTO claim_evidence(claim_id,evidence_id,role) VALUES('claim:a','E-b','supporting')`}[kind]
				if _, err = st.DB().ExecContext(context.Background(), statement); err != nil {
					st.Close()
					t.Fatal(err)
				}
				st.Close()
			}
			after, err := CheckScopeAvailability(paths, "packet.json", &before.Binding)
			if err != nil {
				t.Fatal(err)
			}
			if after.ScopeReady || !scopeIntersect(after.Reasons, []string{"stale_scope_availability"}) || after.Binding.NavigationSnapshot.GenerationID != before.Binding.NavigationSnapshot.GenerationID {
				t.Fatalf("same-generation change reused: %#v", after)
			}
		})
	}
}

func TestScopeAvailabilityOldCapsuleAndScopePathsRefuse(t *testing.T) {
	if _, err := ParseScopeBinding([]byte(`{"contract_version":0}`)); err == nil {
		t.Fatal("old capsule accepted")
	}
	for _, path := range []string{"../outside", "src/*.go", "C:/private", ".specify/project-cognition/project-cognition.db", "src/../a.go"} {
		if _, err := scopePath(path); err == nil {
			t.Fatalf("unsafe concrete scope %s accepted", path)
		}
	}
	paths := scopeFixture(t, false)
	scopePacket(t, paths, []string{"../outside"}, nil)
	if _, err := CheckScopeAvailability(paths, "packet.json", nil); err == nil {
		t.Fatal("unsafe packet accepted")
	}
}

func TestScopeAvailabilityUnavailableBaselineAndCoverageRecover(t *testing.T) {
	paths := scopeFixture(t, false)
	status, _ := rt.ReadStatus(paths)
	status.ActiveGenerationID = "wrong"
	_ = rt.WriteStatus(paths, status)
	p, err := CheckScopeAvailability(paths, "packet.json", nil)
	if err != nil || p.ScopeReady || p.Availability != "unavailable" || p.Policy.Classification != "baseline-unavailable" {
		t.Fatalf("invalid baseline=%#v err=%v", p, err)
	}
	status.ActiveGenerationID = "GEN-scope"
	status.Readiness = rt.NeedsRebuildReadiness
	_ = rt.WriteStatus(paths, status)
	p, err = CheckScopeAvailability(paths, "packet.json", nil)
	if err != nil || p.ScopeReady || p.Availability != "unavailable" {
		t.Fatalf("mandatory rebuild readiness bypassed: %#v err=%v", p, err)
	}
	status.Readiness = rt.ReadyReadiness
	_ = rt.WriteStatus(paths, status)
	scopePacket(t, paths, []string{"src/a.go"}, nil)
	p, err = CheckScopeAvailability(paths, "packet.json", nil)
	if err != nil || !p.ScopeReady || p.Policy.Classification != "read-only/no-change" {
		t.Fatalf("recovery=%#v err=%v", p, err)
	}
	if err := os.WriteFile(filepath.Join(paths.Root, "src/a.go"), []byte("changed source\n"), 0644); err != nil {
		t.Fatal(err)
	}
	p, err = CheckScopeAvailability(paths, "packet.json", nil)
	if err != nil || p.ScopeReady || !strings.Contains(strings.Join(p.Reasons, ","), "coverage_unknown") {
		t.Fatalf("live source mismatch accepted: %#v err=%v", p, err)
	}
}

func TestScopeAvailabilityParsesActualPacketScopesWithoutGenericPathHarvest(t *testing.T) {
	p, err := parseTaskScope([]byte(`{"packet_version":2,"feature_id":"scope-feature","task_id":"T01","scope":{"read_scope":["src/b.go"],"write_scope":["src/a.go"]},"context_bundle":[{"path":"ignored-prose.go"}]}`))
	if err != nil || !reflect.DeepEqual(p.ReadScope, []string{"src/b.go"}) || !reflect.DeepEqual(p.WriteScope, []string{"src/a.go"}) {
		t.Fatalf("Python PacketScope=%#v err=%v", p, err)
	}
	quick, err := parseTaskScope([]byte(`{"schema":"quick-worker-packet-v1","work_item_id":"Q01","write_scope":["src/a.go"],"scope":{"include":["prose"]},"current_state_evidence":["descriptive evidence"]}`))
	if err != nil || quick.ReadDependenciesComplete || len(quick.ReadScope) != 0 {
		t.Fatalf("Quick read completeness fabricated: %#v err=%v", quick, err)
	}
	paths := scopeFixture(t, false)
	if err := os.WriteFile(filepath.Join(paths.Root, "packet.json"), []byte(`{"schema":"quick-worker-packet-v1","work_item_id":"Q01","write_scope":["src/a.go"]}`), 0644); err != nil {
		t.Fatal(err)
	}
	payload, err := CheckScopeAvailability(paths, "packet.json", nil)
	if err != nil || payload.ScopeReady || !scopeIntersect(payload.Reasons, []string{"packet_read_dependencies_unknown"}) {
		t.Fatalf("Quick missing reads accepted: %#v err=%v", payload, err)
	}
}

func TestScopeAvailabilityMalformedPacketArraysCannotAssertCompleteness(t *testing.T) {
	for _, packet := range []string{
		`{"version":2,"feature_id":"f","task_id":"T01","read_scope":null,"write_scope":["src/a.go"]}`,
		`{"version":2,"feature_id":"f","task_id":"T01","write_scope":["src/a.go"]}`,
		`{"version":2,"feature_id":"f","task_id":"T01","read_scope":["src/a.go"]}`,
		`{"version":2,"feature_id":"f","task_id":"T01","read_scope":["src/a.go"],"write_scope":null}`,
		`{"version":2,"task_id":"T01","read_scope":["src/a.go"],"write_scope":[]}`,
		`{"version":2,"feature_id":"f","read_scope":["src/a.go"],"write_scope":[]}`,
		`{"version":2,"feature_id":"f","task_id":"T01","read_scope":"src/a.go","write_scope":[]}`,
		`{"packet_version":2,"feature_id":"f","task_id":"T01","scope":{"read_scope":null,"write_scope":["src/a.go"]}}`,
		`{"packet_version":2,"feature_id":"f","task_id":"T01","scope":{"write_scope":["src/a.go"]}}`,
		`{"packet_version":2,"feature_id":"f","task_id":"T01","scope":{"read_scope":["src/a.go"],"write_scope":null}}`,
		`{"schema":"quick-worker-packet-v1","work_item_id":"Q01","write_scope":["src/a.go"],"read_scope":null}`,
		`{"schema":"quick-worker-packet-v1","write_scope":["src/a.go"]}`,
	} {
		if scope, err := parseTaskScope([]byte(packet)); err == nil {
			t.Fatalf("malformed packet asserted completeness: scope=%#v packet=%s", scope, packet)
		}
	}
	for _, packet := range []string{`{"version":2,"feature_id":"f","task_id":"T01","read_scope":[],"write_scope":["src/a.go"]}`, `{"packet_version":2,"feature_id":"f","task_id":"T01","scope":{"read_scope":["src/a.go"],"write_scope":[]}}`, `{"schema":"quick-worker-packet-v1","work_item_id":"Q01","write_scope":["src/a.go"],"read_scope":[]}`} {
		if scope, err := parseTaskScope([]byte(packet)); err != nil || !scope.ReadDependenciesComplete {
			t.Fatalf("explicit valid array failed: scope=%#v err=%v", scope, err)
		}
	}
}

func scopeProofSQL(t *testing.T, paths rt.Paths, statements ...string) {
	t.Helper()
	st, err := store.OpenExisting(paths)
	if err != nil {
		t.Fatal(err)
	}
	defer st.Close()
	for _, statement := range statements {
		if _, err := st.DB().ExecContext(context.Background(), statement); err != nil {
			t.Fatal(err)
		}
	}
}

func TestScopeAvailabilityDebtEvidenceProofIsTransitive(t *testing.T) {
	paths := scopeFixture(t, false)
	scopeProofSQL(t, paths, `INSERT INTO claim_evidence(claim_id,evidence_id,role) VALUES('claim:b','E-consumer','supporting')`, `INSERT INTO claim_evidence(claim_id,evidence_id,role) VALUES('claim:consumer','E-a','supporting')`)
	scopeDebt(t, paths, rt.DebtRecord{ID: "b-debt", Kind: "mark_dirty", Paths: []string{"src/b.go"}, Reason: "pending"})
	p, err := CheckScopeAvailability(paths, "packet.json", nil)
	if err != nil {
		t.Fatal(err)
	}
	if p.ScopeReady || p.Debt[0].Relation != "related" || !scopeIntersect(p.ProofPaths, []string{"src/consumer.go"}) {
		t.Fatalf("transitive supporting source omitted: %#v", p)
	}
}

func TestScopeAvailabilityCompleteDisjointTransitiveProofStaysReady(t *testing.T) {
	paths := scopeFixture(t, false)
	scopeProofSQL(t, paths, `INSERT INTO claim_evidence(claim_id,evidence_id,role) VALUES('claim:b','E-consumer','supporting')`)
	scopeDebt(t, paths, rt.DebtRecord{ID: "b-debt", Kind: "mark_dirty", Paths: []string{"src/b.go"}, Reason: "pending"})
	p, err := CheckScopeAvailability(paths, "packet.json", nil)
	if err != nil {
		t.Fatal(err)
	}
	if !p.ScopeReady || p.Debt[0].Relation != "unrelated" || !scopeIntersect(p.ProofPaths, []string{"src/consumer.go"}) || p.GlobalStatus.Freshness == rt.ReadyFreshness {
		t.Fatalf("complete disjoint proof blocked or lost: %#v", p)
	}
}

func TestScopeAvailabilityLateClaimEvidenceBeyond25CannotProveDisjointness(t *testing.T) {
	paths := scopeFixture(t, false)
	st, err := store.OpenExisting(paths)
	if err != nil {
		t.Fatal(err)
	}
	for i := 0; i < 30; i++ {
		id := fmt.Sprintf("claim:late-%02d", i)
		if _, err := st.DB().Exec(`INSERT INTO claims(id,generation_id,node_id,graph_claim_type,summary,state,prior_state,freshness,state_reason,attrs_json,revision,created_at,updated_at) VALUES(?,'GEN-scope','N-b','runtime_owner','late','supported','','fresh','','{}',1,'','')`, id); err != nil {
			st.Close()
			t.Fatal(err)
		}
		evidence := "E-b"
		if i == 29 {
			evidence = "E-a"
		}
		if _, err := st.DB().Exec(`INSERT INTO claim_evidence(claim_id,evidence_id,role) VALUES(?,?,'supporting')`, id, evidence); err != nil {
			st.Close()
			t.Fatal(err)
		}
	}
	st.Close()
	scopeDebt(t, paths, rt.DebtRecord{ID: "b-debt", Kind: "mark_dirty", Paths: []string{"src/b.go"}, Reason: "pending"})
	p, err := CheckScopeAvailability(paths, "packet.json", nil)
	if err != nil {
		t.Fatal(err)
	}
	if p.ScopeReady || p.Debt[0].Relation != "related" {
		t.Fatalf("31st claim source was omitted: %#v", p)
	}
}

func TestScopeAvailabilityRealTypedClosureTruncationRemainsDegraded(t *testing.T) {
	paths := scopeFixture(t, false)
	st, err := store.OpenExisting(paths)
	if err != nil {
		t.Fatal(err)
	}
	tx, err := st.DB().Begin()
	if err != nil {
		st.Close()
		t.Fatal(err)
	}
	for i := 0; i < 1001; i++ {
		id := fmt.Sprintf("N-many-%04d", i)
		if _, err := tx.Exec(`INSERT INTO nodes(id,generation_id,type,title,confidence,attrs_json,created_at,updated_at) VALUES(?,'GEN-scope','capability','many','high','{}','','')`, id); err != nil {
			tx.Rollback()
			st.Close()
			t.Fatal(err)
		}
		if _, err := tx.Exec(`INSERT INTO node_evidence(node_id,evidence_id) VALUES(?,'E-a')`, id); err != nil {
			tx.Rollback()
			st.Close()
			t.Fatal(err)
		}
		if _, err := tx.Exec(`INSERT INTO path_index(id,generation_id,path,node_id,relation,confidence,evidence_id,updated_at) VALUES(?,'GEN-scope','src/a.go',?,'owns','high','E-a','')`, "P-"+id, id); err != nil {
			tx.Rollback()
			st.Close()
			t.Fatal(err)
		}
	}
	if err := tx.Commit(); err != nil {
		st.Close()
		t.Fatal(err)
	}
	st.Close()
	p, err := CheckScopeAvailability(paths, "packet.json", nil)
	if err != nil {
		t.Fatal(err)
	}
	if p.ScopeReady || p.Availability != "degraded" || !scopeIntersect(p.Reasons, []string{"source_closure_incomplete"}) || p.Policy.Classification != "baseline-unavailable" {
		t.Fatalf("real truncated closure granted readiness: %#v", p)
	}
}

func TestScopeAvailabilityDebtProofIncompleteSupportStaysUnknown(t *testing.T) {
	for _, test := range []struct {
		name string
		sql  []string
	}{
		{"ownerless", []string{`INSERT INTO edges(id,generation_id,type,source_id,target_id,confidence,attrs_json,created_at,updated_at) VALUES('b-consumer','GEN-scope','depends_on','N-b','N-consumer','high','{}','','')`, `DELETE FROM path_index WHERE node_id='N-consumer'`}},
		{"support-hash", []string{`INSERT INTO evidence(id,generation_id,source_kind,source_path,commit_sha,span,extractor,content_hash,captured_at,attrs_json) VALUES('E-b-bad','GEN-scope','source','src/b.go','','','test','sha256:unknown','','{}')`, `INSERT INTO claim_evidence(claim_id,evidence_id,role) VALUES('claim:b','E-b-bad','supporting')`}},
		{"contradicting", []string{`UPDATE claim_evidence SET role='contradicting' WHERE claim_id='claim:b'`}},
		{"missing-node-support", []string{`DELETE FROM node_evidence WHERE node_id='N-b'`}},
		{"weak-node-support", []string{`UPDATE nodes SET confidence='weak' WHERE id='N-b'`}},
		{"missing-edge-support", []string{`INSERT INTO edges(id,generation_id,type,source_id,target_id,confidence,attrs_json,created_at,updated_at) VALUES('b-consumer','GEN-scope','depends_on','N-b','N-consumer','high','{}','','')`}},
	} {
		t.Run(test.name, func(t *testing.T) {
			paths := scopeFixture(t, false)
			scopeProofSQL(t, paths, test.sql...)
			scopeDebt(t, paths, rt.DebtRecord{ID: "b-debt", Kind: "mark_dirty", Paths: []string{"src/b.go"}, Reason: "pending"})
			p, err := CheckScopeAvailability(paths, "packet.json", nil)
			if err != nil {
				t.Fatal(err)
			}
			if p.ScopeReady || p.Debt[0].Relation != "unknown" {
				t.Fatalf("incomplete debt support classified disjoint: %#v", p)
			}
		})
	}
}

func TestScopeAvailabilityDebtBytesAreBoundAndRereadBeforeReady(t *testing.T) {
	paths := scopeFixture(t, false)
	scopeProofSQL(t, paths, `INSERT INTO claim_evidence(claim_id,evidence_id,role) VALUES('claim:b','E-consumer','supporting')`)
	scopeDebt(t, paths, rt.DebtRecord{ID: "b-debt", Kind: "mark_dirty", Paths: []string{"src/b.go"}, Reason: "pending"})
	p, err := CheckScopeAvailability(paths, "packet.json", nil)
	if err != nil || !p.ScopeReady {
		t.Fatalf("before=%#v err=%v", p, err)
	}
	_, before, err := scopeSourceBasis(paths.Root, p.ProofPaths)
	if err != nil {
		t.Fatal(err)
	}
	if scopeObjectDigest(before) != p.Binding.SourceDigest {
		t.Fatal("binding omitted proof bytes")
	}
	file := filepath.Join(paths.Root, "src/consumer.go")
	info, err := os.Stat(file)
	if err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(file, []byte("package consuMer\n"), 0644); err != nil {
		t.Fatal(err)
	}
	_ = os.Chtimes(file, info.ModTime(), info.ModTime())
	// Execute the actual final-read owner after changing a byte proof already
	// observed above. This is deterministic phase verification, not a claimed
	// injected concurrent race within CheckScopeAvailability.
	if err := recheckScopeSourceBasis(paths.Root, p.ProofPaths, before); err == nil {
		t.Fatal("final reread omitted disjoint debt supporting source")
	}
	_, after, err := scopeSourceBasis(paths.Root, p.ProofPaths)
	if err != nil {
		t.Fatal(err)
	}
	if err := mergeScopeSourceBasis(before, after); err == nil {
		t.Fatal("two observations of changed proof bytes were silently merged")
	}
	current, err := CheckScopeAvailability(paths, "packet.json", &p.Binding)
	if err != nil {
		t.Fatal(err)
	}
	if current.ScopeReady || current.Binding.SourceDigest == p.Binding.SourceDigest || !scopeIntersect(current.Reasons, []string{"stale_scope_availability"}) {
		t.Fatalf("debt supporting-source drift reused capsule: %#v", current)
	}
}

func TestScopeAvailabilityVersion1BindingsAndWhitespaceQuickIdentityRefuse(t *testing.T) {
	paths := scopeFixture(t, false)
	p, err := CheckScopeAvailability(paths, "packet.json", nil)
	if err != nil {
		t.Fatal(err)
	}
	old := p.Binding
	old.ContractVersion = 1
	data, _ := json.Marshal(old)
	if _, err := ParseScopeBinding(data); err == nil {
		t.Fatal("version1 proof binding accepted")
	}
	for _, id := range []string{" ", " Q01", "Q01 "} {
		packet, _ := json.Marshal(map[string]any{"schema": "quick-worker-packet-v1", "work_item_id": id, "read_scope": []string{}, "write_scope": []string{"src/a.go"}})
		if _, err := parseTaskScope(packet); err == nil {
			t.Fatalf("whitespace Quick identity accepted: %q", id)
		}
	}
}

func TestScopeAvailabilityUnknownGlobalReasonAndUnrelatedByteDriftStayConservative(t *testing.T) {
	paths := scopeFixture(t, false)
	scopeDebt(t, paths, rt.DebtRecord{ID: "b-debt", Kind: "mark_dirty", Paths: []string{"src/b.go"}, Reason: "pending"})
	if err := os.WriteFile(filepath.Join(paths.Root, "src/b.go"), []byte("new unknown dependency\n"), 0644); err != nil {
		t.Fatal(err)
	}
	p, err := CheckScopeAvailability(paths, "packet.json", nil)
	if err != nil || p.ScopeReady || p.Debt[0].Relation != "unknown" {
		t.Fatalf("unproven unrelated source accepted: %#v err=%v", p, err)
	}
}

func TestScopeAvailabilityClaimEvidenceDependencyMakesDebtRelated(t *testing.T) {
	paths := scopeFixture(t, false)
	st, err := store.OpenExisting(paths)
	if err != nil {
		t.Fatal(err)
	}
	if _, err := st.DB().ExecContext(context.Background(), `INSERT INTO claim_evidence(claim_id,evidence_id,role) VALUES('claim:a','E-b','supporting')`); err != nil {
		st.Close()
		t.Fatal(err)
	}
	st.Close()
	scopeDebt(t, paths, rt.DebtRecord{ID: "dependency-debt", Kind: "mark_dirty", Paths: []string{"src/b.go"}, Reason: "pending"})
	p, err := CheckScopeAvailability(paths, "packet.json", nil)
	if err != nil || p.ScopeReady || p.Debt[0].Relation != "related" {
		t.Fatalf("claim source dependency ignored: %#v err=%v", p, err)
	}
}

func TestScopeAvailabilityDebtConsumerClosureMustHaveCurrentSourceEvidence(t *testing.T) {
	paths := scopeFixture(t, false)
	st, err := store.OpenExisting(paths)
	if err != nil {
		t.Fatal(err)
	}
	if _, err := st.DB().ExecContext(context.Background(), `INSERT INTO edges(id,generation_id,type,source_id,target_id,confidence,attrs_json,created_at,updated_at) VALUES('b-consumer','GEN-scope','consumed_by','N-b','N-consumer','high','{}','','')`); err != nil {
		st.Close()
		t.Fatal(err)
	}
	st.Close()
	scopeDebt(t, paths, rt.DebtRecord{ID: "b-debt", Kind: "mark_dirty", Paths: []string{"src/b.go"}, Reason: "pending"})
	if err := os.WriteFile(filepath.Join(paths.Root, "src/consumer.go"), []byte("new consumer dependency\n"), 0644); err != nil {
		t.Fatal(err)
	}
	p, err := CheckScopeAvailability(paths, "packet.json", nil)
	if err != nil || p.ScopeReady || p.Debt[0].Relation != "unknown" {
		t.Fatalf("unproved consumer closure treated unrelated: %#v err=%v", p, err)
	}
}
