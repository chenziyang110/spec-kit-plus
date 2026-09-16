package context

import "testing"

func TestResolverKeepsRuntimeBoundaries(t *testing.T) {
	resolved := (Resolver{}).Resolve(ResolveInput{
		TaskID: "Q001",
		Workflow: "quick",
		Goal: "add login endpoint",
		Artifacts: []Artifact{{Path: "auth/login.go", Reason: "scope"}},
		Acceptance: []string{"unit tests pass"},
		Constraints: []string{"do not change database schema"},
		Skills: []string{"backend"},
		StateRef: "runtime://task/Q001",
	})

	if resolved.TaskID != "Q001" || resolved.StateRef == "" {
		t.Fatal("runtime identity was lost")
	}
	if len(resolved.Artifacts) != 1 {
		t.Fatal("artifacts were not preserved")
	}
}

func TestResolverDoesNotCreateAuthority(t *testing.T) {
	resolved := (Resolver{}).Resolve(ResolveInput{Goal: "change code"})
	if len(resolved.Acceptance) != 0 {
		t.Fatal("unexpected acceptance authority")
	}
}
