package update

import (
	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/store"
	"testing"
)

func TestScopePolicyUsesActualOwnerAndClosure(t *testing.T) {
	for _, test := range []struct {
		name     string
		baseline bool
		changed  []string
		owners   map[string]string
		closure  store.AffectedClosure
		want     string
	}{
		{"no-change", true, nil, nil, store.AffectedClosure{}, "read-only/no-change"},
		{"local", true, []string{"src/a.go"}, map[string]string{"src/a.go": "N-a"}, store.AffectedClosure{NodeIDs: []string{"N-a"}}, "local"},
		{"propagated", true, []string{"src/a.go"}, map[string]string{"src/a.go": "N-a"}, store.AffectedClosure{NodeIDs: []string{"N-a", "N-consumer"}}, "propagated"},
		{"missing-baseline", false, nil, nil, store.AffectedClosure{}, "baseline-unavailable"},
		{"unknown-owner", true, []string{"src/a.go"}, nil, store.AffectedClosure{}, "baseline-unavailable"},
		{"truncated", true, []string{"src/a.go"}, map[string]string{"src/a.go": "N-a"}, store.AffectedClosure{Truncated: true}, "baseline-unavailable"},
	} {
		t.Run(test.name, func(t *testing.T) {
			p := ClassifyScopePolicy(test.baseline, test.changed, test.owners, test.closure)
			if p.Classification != test.want || p.Basis == "" {
				t.Fatalf("policy=%#v want %s", p, test.want)
			}
		})
	}
}
