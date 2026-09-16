package context

import "testing"

func TestCompilerKeepsRuntimeBoundary(t *testing.T) {
	packet := (Compiler{}).Compile(Input{
		Goal: "add login endpoint",
		Skills: []string{"api"},
		Artifacts: []string{"auth/service.go"},
		Rules: []string{"do not change schema"},
		Acceptance: []string{"api test passes"},
		StateRef: "state://task-1",
	})

	if packet.Goal != "add login endpoint" {
		t.Fatal("goal missing")
	}
	if packet.RuntimeStateRef != "state://task-1" {
		t.Fatal("state reference missing")
	}
	if len(packet.Acceptance) != 1 {
		t.Fatal("acceptance missing")
	}
}
