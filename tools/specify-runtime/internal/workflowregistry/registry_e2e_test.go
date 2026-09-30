package workflowregistry

import "testing"

func TestE2ECloseoutAliases(t *testing.T) {
	for _, input := range []string{"e2e", "sp-e2e", "/sp.e2e", "sp_e2e", " E2E "} {
		t.Run(input, func(t *testing.T) {
			got, err := CanonicalCloseoutWorkflow(input)
			if err != nil || got != "sp-e2e" {
				t.Fatalf("CanonicalCloseoutWorkflow(%q) = %q, %v", input, got, err)
			}
		})
	}
}

func TestE2EPolicyAndAdjacentOwnership(t *testing.T) {
	policies := Policies()
	policy, ok := policies["e2e"]
	if !ok || policy.Mode != ModeMutationCloseout || policy.CanonicalWorkflow != "sp-e2e" {
		t.Fatalf("missing E2E test-asset closeout policy: %#v", policy)
	}
	for _, name := range []string{"test-design", "accept", "plan", "tasks"} {
		if policies[name].Mode != ModeNoCloseout {
			t.Fatalf("E2E must not change %q ownership", name)
		}
	}
	delete(policies, "e2e")
	if _, ok := Policies()["e2e"]; !ok {
		t.Fatal("callers must not mutate the canonical registry through Policies()")
	}
}
