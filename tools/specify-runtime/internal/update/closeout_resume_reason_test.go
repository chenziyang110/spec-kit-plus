package update

import (
	"reflect"
	"testing"
)

func TestCloseoutJournalResumePreservesPartialReasonAndScopeBoundary(t *testing.T) {
	for _, tc := range []struct {
		name          string
		unrelatedDebt bool
		verification  []VerificationEvidence
		wantScope     string
	}{
		{name: "ready scope retains unrelated project debt", unrelatedDebt: true, verification: []VerificationEvidence{{Command: "bounded business check", Result: "passed"}}, wantScope: ResultReady},
		{name: "missing verification remains an open scope obligation", wantScope: ResultPartialRefresh},
	} {
		t.Run(tc.name, func(t *testing.T) {
			paths := testPaths(t)
			seedReadyRuntime(t, paths)
			if tc.unrelatedDebt {
				if _, err := MarkDirty(paths, DirtyInput{Reason: "older unrelated debt", ScopePaths: []string{"src/other.go"}}); err != nil {
					t.Fatal(err)
				}
			}
			input := UpdateInput{ChangedPaths: []string{"src/app.go"}, Reason: "workflow-finalize", Workflow: "sp-quick", Verification: tc.verification, CloseoutIntentID: "intent-0123456789abcdef01234567"}
			first, err := RunUpdate(paths, input)
			if err != nil {
				t.Fatal(err)
			}
			if first.ResultState != ResultPartialRefresh || first.ScopeResultState != tc.wantScope || len(first.PartialRefreshReasons) == 0 {
				t.Fatalf("first update did not expose the expected partial boundary: %#v", first)
			}
			replayed, err := RunUpdate(paths, input)
			if err != nil {
				t.Fatal(err)
			}
			if !replayed.ResumedFromIntent || replayed.UpdateID != first.UpdateID || replayed.ResultState != first.ResultState || replayed.ScopeResultState != first.ScopeResultState {
				t.Fatalf("replay changed the committed outcome: first=%#v replay=%#v", first, replayed)
			}
			if !reflect.DeepEqual(replayed.PartialRefreshReasons, first.PartialRefreshReasons) || !reflect.DeepEqual(replayed.GlobalDebtReasons, first.GlobalDebtReasons) || !reflect.DeepEqual(replayed.ScopePartialReasons, first.ScopePartialReasons) {
				t.Fatalf("replay lost or moved a still-open obligation: first=%#v replay=%#v", first, replayed)
			}
		})
	}
}
