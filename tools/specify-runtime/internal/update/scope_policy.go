package update

import "github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/store"

// ScopePolicy classifies the actual owner/propagation result. It is navigation
// policy, never a mutation permission or a substitute for no-op verification.
type ScopePolicy struct {
	Classification string `json:"classification"`
	Basis          string `json:"basis"`
}

func ClassifyScopePolicy(baselineUsable bool, changed []string, owners map[string]string, closure store.AffectedClosure) ScopePolicy {
	if !baselineUsable || closure.Truncated {
		return ScopePolicy{"baseline-unavailable", "baseline_or_complete_closure_unavailable"}
	}
	if len(changed) == 0 {
		return ScopePolicy{"read-only/no-change", "no_source_mutation_paths"}
	}
	direct := map[string]bool{}
	for _, path := range changed {
		if owners[path] == "" {
			return ScopePolicy{"baseline-unavailable", "source_path_owner_unknown"}
		}
		direct[owners[path]] = true
	}
	for _, node := range closure.NodeIDs {
		if !direct[node] {
			return ScopePolicy{"propagated", "typed_owner_dependency_closure"}
		}
	}
	return ScopePolicy{"local", "complete_closure_stays_with_direct_owners"}
}
