package query

import (
	"context"
	"encoding/json"
	"fmt"
	"reflect"
	"strconv"
	"testing"

	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/claim"
	rt "github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/runtime"
	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/store"
)

func seedClaimPageGraph(t *testing.T, paths rt.Paths, counts []int) {
	t.Helper()
	input := store.ImportInput{GenerationID: "GEN-claim-page", Kind: "full", SourceCommit: "abc123"}
	for lane, count := range counts {
		id, evidenceID := fmt.Sprintf("N-%d", lane), fmt.Sprintf("E-%d", lane)
		path := fmt.Sprintf("src/lane%d.go", lane)
		title := "needle"
		if lane == 1 {
			title = "needle specialized exact"
		}
		input.Evidence = append(input.Evidence, store.EvidenceImport{ID: evidenceID, SourceKind: "source", SourcePath: path, Span: "1:1-1:20", CommitSHA: "abc123", Extractor: "test", ContentHash: "hash-" + id})
		input.Nodes = append(input.Nodes, store.NodeImport{ID: id, Type: "capability", Title: title, Confidence: "verified", EvidenceIDs: []string{evidenceID}})
		input.PathIndex = append(input.PathIndex, store.PathIndexImport{ID: "P-" + id, Path: path, NodeID: id, Relation: "owns", Confidence: "verified", EvidenceID: evidenceID})
		for n := 0; n < count; n++ {
			state, freshness := claim.StateSupported, claim.FreshnessFresh
			if n == count-1 {
				state, freshness = claim.StateStale, claim.FreshnessStale
			}
			input.Claims = append(input.Claims, store.ClaimImport{ID: fmt.Sprintf("claim:%d-%02d", lane, n), NodeID: id, GraphClaimType: "runtime_owner", Summary: "needle owner", State: state, Freshness: freshness, StateReason: "fixture", SupportingEvidenceIDs: []string{evidenceID}})
		}
	}
	seedReadyGraph(t, paths, input)
}

func TestCompassClaimPageDoesNotStarveTopLane(t *testing.T) {
	paths := queryTestPaths(t)
	seedClaimPageGraph(t, paths, []int{26, 1})
	result, err := Compass(paths, CompassInput{Intent: "debug", Query: "needle specialized exact"})
	if err != nil {
		t.Fatal(err)
	}
	if len(result.EvidenceLanes) == 0 || result.ExpansionRef == nil {
		t.Fatalf("missing lanes: %#v", result)
	}
	top := result.EvidenceLanes[0]
	if top.NodeID != "N-1" || (len(top.ClaimRefs) != 1 || top.ClaimRefs[0].ID != "claim:1-00") || top.ClaimCount != 1 || top.ClaimRefsTruncated || top.ClaimRanking == nil || top.ClaimRanking.State != "stale" || !top.ClaimRanking.ReconciliationRequired {
		t.Fatalf("top lane lost evidence/risk: %#v", top)
	}
	page, err := Expand(paths, ExpandInput{ID: result.ExpansionRef.ID, Section: "claim_evidence"})
	if err != nil {
		t.Fatal(err)
	}
	if page.Status != "ok" || page.TotalCount != 27 || page.ReturnedCount != 25 || !page.HasMore || page.EpistemicContract.GraphOnlyClaimsAllowed {
		t.Fatalf("page/epistemic contract: %#v", page)
	}
	rows := page.Data.([]any)
	if rows[0].(map[string]any)["node_id"] != "N-1" {
		t.Fatalf("top lane absent from first quota: %#v", rows[0])
	}
}

func TestClaimEvidenceFairPagesTraverseFullDenominator(t *testing.T) {
	paths := queryTestPaths(t)
	seedClaimPageGraph(t, paths, []int{31, 30, 29})
	result, err := Compass(paths, CompassInput{Intent: "debug", Query: "needle"})
	if err != nil {
		t.Fatal(err)
	}
	if len(result.EvidenceLanes) != 3 {
		t.Fatalf("lanes=%#v", result.EvidenceLanes)
	}
	seen := map[string]bool{}
	offset := 0
	for {
		page, err := Expand(paths, ExpandInput{ID: result.ExpansionRef.ID, Section: "claim_evidence", Offset: offset})
		if err != nil {
			t.Fatal(err)
		}
		if page.Status != "ok" || page.TotalCount != 90 || page.Offset != offset || page.ReturnedCount > 25 || page.EpistemicContract.GraphOnlyClaimsAllowed {
			t.Fatalf("invalid full page: %#v", page)
		}
		rows := page.Data.([]any)
		if page.ReturnedCount != len(rows) {
			t.Fatal("returned denominator differs")
		}
		for n, value := range rows {
			row := value.(map[string]any)
			id := row["id"].(string)
			if seen[id] {
				t.Fatalf("duplicate %s", id)
			}
			seen[id] = true
			if offset == 0 && n < 3 && (row["node_id"] != result.EvidenceLanes[n].NodeID || row["state"] != "stale") {
				t.Fatalf("lane/risk quota %d: %#v", n, row)
			}
		}
		if !page.HasMore {
			if len(page.NextArgv) != 0 {
				t.Fatal("terminal continuation")
			}
			break
		}
		offset += len(rows)
		want := []string{"specify-runtime", "cognition", "expand", "--id", result.ExpansionRef.ID, "--section", "claim_evidence", "--offset", strconv.Itoa(offset), "--format", "json"}
		if !reflect.DeepEqual(page.NextArgv, want) {
			t.Fatalf("continuation=%v want=%v", page.NextArgv, want)
		}
	}
	if len(seen) != 90 {
		t.Fatalf("full denominator=%d", len(seen))
	}
	for _, lane := range result.EvidenceLanes {
		if len(lane.ClaimRefs) != 3 || !lane.ClaimRefsTruncated || lane.ClaimCount < 29 || lane.ClaimRanking == nil || !lane.ClaimRanking.ReconciliationRequired {
			t.Fatalf("lane denominator/risk=%#v", lane)
		}
	}
	if _, err := Expand(paths, ExpandInput{ID: result.ExpansionRef.ID, Section: "claim_evidence", Offset: 91}); err == nil {
		t.Fatal("out of range accepted")
	}
	if _, err := Expand(paths, ExpandInput{ID: result.ExpansionRef.ID, Section: "claim_evidence", Offset: -1}); err == nil {
		t.Fatal("negative offset accepted")
	}
	if _, err := Expand(paths, ExpandInput{ID: result.ExpansionRef.ID, Section: "coverage_diagnostics", Offset: 1}); err == nil {
		t.Fatal("non-claim offset accepted")
	}
}

func TestClaimEvidenceContinuationRejectsSameGenerationMutation(t *testing.T) {
	paths := queryTestPaths(t)
	seedClaimPageGraph(t, paths, []int{30})
	result, err := Compass(paths, CompassInput{Intent: "debug", Query: "needle"})
	if err != nil {
		t.Fatal(err)
	}
	st, err := store.OpenExisting(paths)
	if err != nil {
		t.Fatal(err)
	}
	_, err = st.MarkClaimsStale(context.Background(), []string{"claim:0-00"}, "live mutation", "claim-page-change")
	st.Close()
	if err != nil {
		t.Fatal(err)
	}
	page, err := Expand(paths, ExpandInput{ID: result.ExpansionRef.ID, Section: "claim_evidence", Offset: 25})
	if err != nil {
		t.Fatal(err)
	}
	if page.Status != "stale_expansion" || page.Data != nil || page.NextArgv != nil {
		t.Fatalf("stale page consumed: %#v", page)
	}
}

func TestClaimEvidenceEmptyPageSerializesExactDenominator(t *testing.T) {
	paths := queryTestPaths(t)
	seedClaimPageGraph(t, paths, []int{0})
	result, err := Compass(paths, CompassInput{Intent: "explain", Query: "needle"})
	if err != nil {
		t.Fatal(err)
	}
	page, err := Expand(paths, ExpandInput{ID: result.ExpansionRef.ID, Section: "claim_evidence"})
	if err != nil {
		t.Fatal(err)
	}
	encoded, err := json.Marshal(page)
	if err != nil {
		t.Fatal(err)
	}
	var raw map[string]any
	if err := json.Unmarshal(encoded, &raw); err != nil {
		t.Fatal(err)
	}
	for _, key := range []string{"total_count", "returned_count", "offset"} {
		if value, ok := raw[key]; !ok || value != float64(0) {
			t.Fatalf("missing exact zero %s: %s", key, encoded)
		}
	}
	if raw["has_more"] != false || page.Status != "ok" || page.ReturnedCount != 0 {
		t.Fatalf("empty terminal page: %s", encoded)
	}
}

func TestClaimEvidencePageRejectsInvalidBoundDescriptor(t *testing.T) {
	for _, bad := range []any{json.Number("1.5"), json.Number("-1"), "1", nil} {
		t.Run(fmt.Sprint(bad), func(t *testing.T) {
			paths := queryTestPaths(t)
			seedClaimPageGraph(t, paths, []int{1})
			st, err := store.OpenExisting(paths)
			if err != nil {
				t.Fatal(err)
			}
			read, err := st.BeginNavigationRead(context.Background())
			if err != nil {
				t.Fatal(err)
			}
			snapshot := read.Snapshot
			read.Close()
			st.Close()
			status, err := rt.ReadStatus(paths)
			if err != nil {
				t.Fatal(err)
			}
			bundle := ExpansionBundle{ExpansionContractVersion: ExpansionContractVersion, ClaimRetrievalContractVersion: ClaimRetrievalContractVersion, CandidateUniverseVersion: CandidateUniverseVersion, ActiveGenerationID: status.ActiveGenerationID, NavigationSnapshot: snapshot, StatusDigest: navigationStatusDigest(status), QueryFingerprint: "descriptor-fixture", SectionPayloads: map[string]any{"claim_evidence": []any{}, "claim_evidence_index": map[string]any{"node_ids": []string{"N-0"}, "total_count": bad}}}
			bundle.ID = expansionBundleID(bundle)
			ref, err := writeExpansionBundle(paths, bundle)
			if err != nil {
				t.Fatal(err)
			}
			page, err := Expand(paths, ExpandInput{ID: ref.ID, Section: "claim_evidence"})
			if err != nil {
				t.Fatal(err)
			}
			if page.Status != "invalid_expansion" || page.Data != nil {
				t.Fatalf("malformed descriptor consumed: %#v", page)
			}
		})
	}
}

func TestClaimEvidenceLegacyDescriptorRequiresNewCompass(t *testing.T) {
	for _, index := range []any{nil, []any{}} {
		t.Run(fmt.Sprintf("%T", index), func(t *testing.T) {
			paths := queryTestPaths(t)
			seedClaimPageGraph(t, paths, []int{1})
			st, err := store.OpenExisting(paths)
			if err != nil {
				t.Fatal(err)
			}
			read, err := st.BeginNavigationRead(context.Background())
			if err != nil {
				t.Fatal(err)
			}
			snapshot := read.Snapshot
			read.Close()
			st.Close()
			status, err := rt.ReadStatus(paths)
			if err != nil {
				t.Fatal(err)
			}
			bundle := ExpansionBundle{ExpansionContractVersion: ExpansionContractVersion, ClaimRetrievalContractVersion: ClaimRetrievalContractVersion, CandidateUniverseVersion: CandidateUniverseVersion, ActiveGenerationID: status.ActiveGenerationID, NavigationSnapshot: snapshot, StatusDigest: navigationStatusDigest(status), QueryFingerprint: "legacy-claim-index", SectionPayloads: map[string]any{"related_paths": []string{"src/lane0.go"}, "claim_evidence": []any{map[string]any{"id": "claim:0-00"}}}}
			if index != nil {
				bundle.SectionPayloads["claim_evidence_index"] = index
			}
			bundle.ID = expansionBundleID(bundle)
			ref, err := writeExpansionBundle(paths, bundle)
			if err != nil {
				t.Fatal(err)
			}
			page, err := Expand(paths, ExpandInput{ID: ref.ID, Section: "claim_evidence"})
			if err != nil {
				t.Fatal(err)
			}
			if page.Status != "incompatible_expansion" || page.Data != nil {
				t.Fatalf("incomplete legacy denominator: %#v", page)
			}
			related, err := Expand(paths, ExpandInput{ID: ref.ID, Section: "related_paths"})
			if err != nil {
				t.Fatal(err)
			}
			if related.Status != "ok" {
				t.Fatalf("nonclaim section lost: %#v", related)
			}
			data, err := json.Marshal(related)
			if err != nil {
				t.Fatal(err)
			}
			var fields map[string]any
			if err := json.Unmarshal(data, &fields); err != nil {
				t.Fatal(err)
			}
			if _, ok := fields["total_count"]; ok {
				t.Fatalf("unrelated paging metadata: %s", data)
			}
		})
	}
}
