package query

import (
	"context"
	"encoding/json"
	"fmt"
	"reflect"
	"strings"
	"testing"

	rt "github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/runtime"
	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/store"
)

func TestLexiconCatalogSnapshotContinuationAndFullDenominator(t *testing.T) {
	paths := queryTestPaths(t)
	input := store.ImportInput{GenerationID: "GEN-catalog-pages", Kind: "full", SourceCommit: "abc123"}
	for index := 0; index < 23; index++ {
		id := fmt.Sprintf("N-%03d", index)
		input.Nodes = append(input.Nodes, store.NodeImport{ID: id, Type: "capability", Title: "catalog node", Confidence: "high", Attrs: map[string]any{"aliases": []string{"共同"}}})
	}
	input.Nodes[22].Attrs = map[string]any{"aliases": []string{"needle 最后一项"}}
	seedReadyGraph(t, paths, input)
	request := LexiconInput{Intent: "debug", Mode: "catalog", Limit: 7}
	var ids []string
	for {
		payload, err := LexiconWithOptions(paths, request)
		if err != nil {
			t.Fatal(err)
		}
		page := payload.CatalogPage
		if page == nil || page.Total != 23 || payload.AliasCatalogCount != 23 || payload.CandidateUniverse["counts"].(map[string]any)["nodes"] != 23 || page.ContractVersion != CatalogSnapshotContractVersion {
			t.Fatalf("incomplete catalog denominator: %#v", payload)
		}
		if !page.SnapshotBound || !validNavigationDigest(page.Revision) || !validNavigationDigest(page.NavigationDigest) {
			t.Fatalf("incorrect snapshot binding: %#v", page)
		}
		for _, row := range payload.AliasCatalog {
			ids = append(ids, row["concept_id"].(string))
		}
		if !page.HasMore {
			if len(page.NextArgv) != 0 || page.NextOffset != nil {
				t.Fatal("terminal page advertised a continuation")
			}
			break
		}
		wantArgv := []string{"specify-runtime", "cognition", "lexicon", "--mode", "catalog", "--intent", "debug", "--query", "", "--limit", "7", "--offset", fmt.Sprint(*page.NextOffset), "--catalog-revision", page.Revision, "--format", "json"}
		if !reflect.DeepEqual(page.NextArgv, wantArgv) {
			t.Fatalf("continuation argv mismatch: %#v", page.NextArgv)
		}
		request.Offset = *page.NextOffset
		request.CatalogRevision = page.Revision
	}
	if len(ids) != 23 {
		t.Fatalf("incomplete traversal: %#v", ids)
	}
	for index, id := range ids {
		if id != fmt.Sprintf("concept:GEN-catalog-pages:N-%03d", index) {
			t.Fatalf("unstable, missing, or repeated ID: %#v", ids)
		}
	}
	request.Offset = 23
	end, err := LexiconWithOptions(paths, request)
	if err != nil || end.CatalogPage.Returned != 0 || end.CatalogPage.Total != 23 || end.CatalogPage.HasMore {
		t.Fatalf("invalid terminal offset: %#v %v", end, err)
	}
	encoded, _ := json.Marshal(end.CatalogPage)
	for _, expected := range []string{`"returned":0`, `"total":23`, `"has_more":false`, `"snapshot_bound":true`} {
		if !strings.Contains(string(encoded), expected) {
			t.Fatalf("missing exact terminal field %s: %s", expected, encoded)
		}
	}
	for _, text := range []string{"needle", "最后一项"} {
		payload, err := LexiconWithOptions(paths, LexiconInput{Intent: "debug", Mode: "catalog", Query: text, Limit: 1})
		if err != nil || len(payload.ConceptCandidates) != 1 || payload.ConceptCandidates[0]["node_id"] != "N-022" || payload.AliasCatalog[0]["concept_id"] != "concept:GEN-catalog-pages:N-000" {
			t.Fatalf("page limit truncated global query ranking for %s: %#v %v", text, payload, err)
		}
	}
}

func TestLexiconCatalogRejectsChangedSnapshotAndRequestBindings(t *testing.T) {
	for _, mutation := range []string{"same-generation-claim", "status", "generation", "query", "intent", "limit", "malformed", "wrong-mode"} {
		t.Run(mutation, func(t *testing.T) {
			paths := queryTestPaths(t)
			seedCompassModelSwitchGraph(t, paths)
			request := LexiconInput{Intent: "debug", Mode: "catalog", Limit: 1}
			first, err := LexiconWithOptions(paths, request)
			if err != nil {
				t.Fatal(err)
			}
			request.Offset = 1
			request.CatalogRevision = first.CatalogPage.Revision
			switch mutation {
			case "same-generation-claim":
				st, err := store.OpenExisting(paths)
				if err != nil {
					t.Fatal(err)
				}
				_, err = st.MarkClaimsStale(context.Background(), []string{"claim:provider-runtime-owner"}, "catalog changed", "catalog-stale")
				st.Close()
				if err != nil {
					t.Fatal(err)
				}
			case "status":
				status, err := rt.ReadStatus(paths)
				if err != nil {
					t.Fatal(err)
				}
				status.LastRefreshReason = "new catalog status"
				if err := rt.WriteStatus(paths, status); err != nil {
					t.Fatal(err)
				}
			case "generation":
				seedReadyGraph(t, paths, store.ImportInput{GenerationID: "GEN-new-catalog", Kind: "full", SourceCommit: "def456", Nodes: []store.NodeImport{{ID: "N-new", Type: "capability", Title: "replacement", Confidence: "high"}}})
			case "query":
				request.Query = "runtime"
			case "intent":
				request.Intent = "explain"
			case "limit":
				request.Limit = 2
			case "malformed":
				request.CatalogRevision = "invalid"
			case "wrong-mode":
				request.Mode = ""
			}
			got, err := LexiconWithOptions(paths, request)
			if err == nil || len(got.AliasCatalog) != 0 || got.CatalogPage != nil {
				t.Fatalf("changed/malformed continuation exposed data: %#v %v", got, err)
			}
			request.CatalogRevision = ""
			request.Mode = "catalog"
			fresh, err := LexiconWithOptions(paths, request)
			if err != nil || fresh.CatalogPage == nil || fresh.CatalogPage.SnapshotBound {
				t.Fatalf("legacy unbound offset cannot recover honestly: %#v %v", fresh, err)
			}
		})
	}
}
