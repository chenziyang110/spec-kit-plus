package context

import "testing"

func TestResolverChainKeepsRuntimeOwnership(t *testing.T) {
	state := (StateResolver{}).Resolve(StateInput{
		TaskID:   "Q001",
		Workflow: "quick",
		StateRef: "runtime://task/Q001",
	})

	artifacts := (ArtifactResolver{}).Resolve([]ArtifactInput{
		{Path: "auth/login.go", Reason: "task scope"},
	})

	resolved := (Resolver{}).Resolve(ResolveInput{
		TaskID:    state.TaskID,
		Workflow:  state.Workflow,
		Artifacts: artifacts,
		StateRef:  state.StateRef,
	})

	if resolved.StateRef != "runtime://task/Q001" {
		t.Fatal("state reference was lost")
	}
	if len(resolved.Artifacts) != 1 || resolved.Artifacts[0].Path != "auth/login.go" {
		t.Fatal("artifact resolution failed")
	}
}

func TestArtifactResolverDoesNotInventArtifacts(t *testing.T) {
	resolved := (ArtifactResolver{}).Resolve(nil)
	if len(resolved) != 0 {
		t.Fatal("resolver invented repository artifacts")
	}
}
