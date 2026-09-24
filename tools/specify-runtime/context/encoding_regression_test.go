package context

import (
	"strings"
	"testing"
)

func TestBindingRejectsLossyUnicodeInputs(t *testing.T) {
	changes := map[string]func(*CompileRequest){
		"task":            func(r *CompileRequest) { r.TaskID += "\xff" },
		"workflow":        func(r *CompileRequest) { r.Workflow += "\xff" },
		"goal":            func(r *CompileRequest) { r.Goal += "\xff" },
		"state-ref":       func(r *CompileRequest) { r.StateRef += "\xff" },
		"scope":           func(r *CompileRequest) { r.Scope[0] += "\xff" },
		"artifact-path":   func(r *CompileRequest) { r.Artifacts[0].Path += "\xff" },
		"artifact-reason": func(r *CompileRequest) { r.Artifacts[0].Reason += "\xff" },
		"constraint":      func(r *CompileRequest) { r.Constraints[0] += "\xff" },
		"acceptance":      func(r *CompileRequest) { r.Acceptance[0] += "\xff" },
		"skill":           func(r *CompileRequest) { r.Skills[0] += "\xff" },
		"forbidden":       func(r *CompileRequest) { r.ForbiddenActions[0] += "\xff" },
	}
	for name, change := range changes {
		t.Run(name, func(t *testing.T) {
			in := boundFixture()
			change(&in)
			p, err := (Compiler{}).CompileBound(in)
			if err == nil || p.Bound {
				t.Fatal("lossy Unicode input was bound")
			}
		})
	}
}

func TestDistinctInvalidBytesCannotShareAnAcceptedBinding(t *testing.T) {
	first, second := boundFixture(), boundFixture()
	first.Goal, second.Goal = "repair\xfe", "repair\xff"
	p, err := (Compiler{}).CompileBound(first)
	if err == nil && p.VerifyAgainst(second) == nil {
		t.Fatal("different invalid byte sequences were accepted as the same input")
	}
}

func TestVerificationEnforcesActualPacketBudget(t *testing.T) {
	in := boundFixture()
	p, err := (Compiler{}).CompileBound(in)
	if err != nil {
		t.Fatal(err)
	}
	p.GeneratedAt = "2026-09-17T00:00:00." + strings.Repeat("1", defaultMaxBytes) + "Z"
	if p.VerifyAgainst(in) == nil {
		t.Fatal("oversized timestamp escaped the packet budget")
	}
}
