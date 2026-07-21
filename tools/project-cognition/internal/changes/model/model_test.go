package model

import "testing"

func TestResolvePathDispositionsAppliesAgentDecision(t *testing.T) {
	changes := []PathChange{{Path: "src/new.go", Operation: OperationAdd}}
	disposition := DispositionAdoptable

	resolved, err := ResolvePathDispositions(changes, []PathDispositionDecision{{
		Path:             "src/new.go",
		AgentDisposition: &disposition,
	}})
	if err != nil {
		t.Fatal(err)
	}
	if resolved[0].Disposition == nil || *resolved[0].Disposition != DispositionAdoptable {
		t.Fatalf("Disposition = %#v, want adoptable", resolved[0].Disposition)
	}
}

func TestResolvePathDispositionsRejectsConflictAndUnknownDecision(t *testing.T) {
	adoptable := DispositionAdoptable
	reviewOnly := DispositionReviewOnly
	for _, tc := range []struct {
		name      string
		changes   []PathChange
		decisions []PathDispositionDecision
	}{
		{
			name:      "conflict",
			changes:   []PathChange{{Path: "src/new.go", Operation: OperationAdd, Disposition: &adoptable}},
			decisions: []PathDispositionDecision{{Path: "src/new.go", AgentDisposition: &reviewOnly}},
		},
		{
			name:      "unknown path",
			changes:   []PathChange{{Path: "src/new.go", Operation: OperationAdd}},
			decisions: []PathDispositionDecision{{Path: "src/other.go", AgentDisposition: &reviewOnly}},
		},
	} {
		t.Run(tc.name, func(t *testing.T) {
			if _, err := ResolvePathDispositions(tc.changes, tc.decisions); err == nil {
				t.Fatal("expected disposition reconciliation error")
			}
		})
	}
}
