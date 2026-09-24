package context

import (
	"encoding/json"
	"os"
	"reflect"
	"strings"
	"testing"
)

func boundFixture() CompileRequest {
	state := (StateResolver{}).Resolve(StateInput{
		TaskID: "Q001", Workflow: "quick", StateRef: "runtime://task/Q001",
		StateDigest: strings.Repeat("a", 64), SourceRevision: strings.Repeat("b", 40),
	})
	artifacts := (ArtifactResolver{}).Resolve([]ArtifactInput{
		{Path: "src/login.go", Reason: "implementation scope", Digest: strings.Repeat("c", 64)},
	})
	return (Resolver{}).Resolve(ResolveInput{
		TaskID: state.TaskID, Workflow: state.Workflow, Goal: "repair login",
		Scope: []string{"src/"}, Artifacts: artifacts, Acceptance: []string{"login tests pass"},
		Constraints: []string{"preserve existing UI"}, Skills: []string{"backend"},
		ForbiddenActions: []string{"no deployment"}, StateRef: state.StateRef,
		StateDigest: state.StateDigest, SourceRevision: state.SourceRevision,
	}).ToCompileRequest()
}

func TestBoundContextPreservesEveryInput(t *testing.T) {
	in := boundFixture()
	packet, err := (Compiler{}).CompileBound(in)
	if err != nil {
		t.Fatal(err)
	}
	if err := packet.VerifyAgainst(in); err != nil {
		t.Fatal(err)
	}
	if packet.TaskID != in.TaskID || packet.Workflow != in.Workflow ||
		!reflect.DeepEqual(packet.Scope, in.Scope) ||
		!reflect.DeepEqual(packet.ArtifactDetails, in.Artifacts) ||
		!reflect.DeepEqual(packet.ForbiddenActions, in.ForbiddenActions) ||
		!reflect.DeepEqual(packet.Acceptance, in.Acceptance) ||
		!reflect.DeepEqual(packet.Constraints, in.Constraints) ||
		!reflect.DeepEqual(packet.RequiredSkills, in.Skills) {
		t.Fatal("runtime input lost during resolution/compilation")
	}
	data, _ := json.Marshal(packet)
	var restored Packet
	if err := json.Unmarshal(data, &restored); err != nil {
		t.Fatal(err)
	}
	if err := restored.VerifyAgainst(in); err != nil {
		t.Fatal(err)
	}
}

func TestBoundContextDetectsEveryChangedBinding(t *testing.T) {
	mutations := map[string]func(*CompileRequest){
		"task":        func(r *CompileRequest) { r.TaskID = "Q002" },
		"workflow":    func(r *CompileRequest) { r.Workflow = "plan" },
		"goal":        func(r *CompileRequest) { r.Goal = "different" },
		"scope":       func(r *CompileRequest) { r.Scope[0] = "other/" },
		"state":       func(r *CompileRequest) { r.StateDigest = strings.Repeat("d", 64) },
		"source":      func(r *CompileRequest) { r.SourceRevision = strings.Repeat("d", 40) },
		"state-ref":   func(r *CompileRequest) { r.StateRef = "runtime://other" },
		"artifact":    func(r *CompileRequest) { r.Artifacts[0].Digest = strings.Repeat("d", 64) },
		"reason":      func(r *CompileRequest) { r.Artifacts[0].Reason = "new reason" },
		"acceptance":  func(r *CompileRequest) { r.Acceptance[0] = "new check" },
		"constraints": func(r *CompileRequest) { r.Constraints = nil },
		"forbidden":   func(r *CompileRequest) { r.ForbiddenActions = nil },
		"skills":      func(r *CompileRequest) { r.Skills = nil },
	}
	for name, mutate := range mutations {
		t.Run(name, func(t *testing.T) {
			packet, err := (Compiler{}).CompileBound(boundFixture())
			if err != nil {
				t.Fatal(err)
			}
			changed := boundFixture()
			mutate(&changed)
			if packet.VerifyAgainst(changed) == nil {
				t.Fatal("stale packet accepted")
			}
		})
	}
}

func TestContextRejectsTamperingAndUnboundViews(t *testing.T) {
	in := boundFixture()
	packet := (Compiler{}).Compile(in.ToCompilerInput())
	if packet.VerifyAgainst(in) == nil {
		t.Fatal("unbound view accepted")
	}
	packet, _ = (Compiler{}).CompileBound(in)
	packet.ForbiddenActions = nil
	if packet.VerifyAgainst(in) == nil {
		t.Fatal("tampering accepted")
	}
}

func TestContextRefusesMissingBindings(t *testing.T) {
	mutations := []func(*CompileRequest){
		func(r *CompileRequest) { r.TaskID = "" }, func(r *CompileRequest) { r.Workflow = "" },
		func(r *CompileRequest) { r.Goal = " " }, func(r *CompileRequest) { r.StateRef = "" },
		func(r *CompileRequest) { r.StateDigest = "invalid" }, func(r *CompileRequest) { r.SourceRevision = "" },
		func(r *CompileRequest) { r.Scope = nil }, func(r *CompileRequest) { r.Acceptance = nil },
		func(r *CompileRequest) { r.Artifacts[0].Reason = "" }, func(r *CompileRequest) { r.Artifacts[0].Digest = "" },
		func(r *CompileRequest) { r.Artifacts = append(r.Artifacts, r.Artifacts[0]) },
		func(r *CompileRequest) { r.Acceptance = []string{" "} },
	}
	for i, mutate := range mutations {
		in := boundFixture()
		mutate(&in)
		if _, err := (Compiler{}).CompileBound(in); err == nil {
			t.Errorf("case %d accepted", i)
		}
	}
}

func TestContextRejectsPortablePathEscapes(t *testing.T) {
	for _, value := range []string{"../secret", "/etc/passwd", "C:/secret", "..\\secret", "src/../secret", "src//file", ".", ""} {
		t.Run(value, func(t *testing.T) {
			in := boundFixture()
			in.Artifacts[0].Path = value
			if _, err := (Compiler{}).CompileBound(in); err == nil {
				t.Fatal("unsafe artifact path")
			}
			in = boundFixture()
			in.Scope = []string{value}
			if _, err := (Compiler{}).CompileBound(in); err == nil {
				t.Fatal("unsafe scope")
			}
		})
	}
}

func TestContextBudgetNeverTruncates(t *testing.T) {
	for _, limit := range []int{16, -1, defaultMaxBytes + 1} {
		packet, err := (Compiler{MaxBytes: limit}).CompileBound(boundFixture())
		if err == nil || packet.Bound || packet.ContentDigest != "" {
			t.Fatal("partial or over-budget context returned")
		}
	}
}

func TestContextCopiesMutableInputs(t *testing.T) {
	in := boundFixture()
	packet, _ := (Compiler{}).CompileBound(in)
	in.Scope[0] = "other/"
	in.Artifacts[0].Reason = "changed"
	in.ForbiddenActions[0] = "changed"
	if err := packet.VerifyAgainst(boundFixture()); err != nil {
		t.Fatal("input aliases packet", err)
	}
}

func TestContextDigestDoesNotDependOnClock(t *testing.T) {
	in := boundFixture()
	first, _ := (Compiler{}).CompileBound(in)
	second, _ := (Compiler{}).CompileBound(in)
	second.GeneratedAt = "2000-01-01T00:00:00Z"
	if first.ContentDigest != second.ContentDigest || second.VerifyAgainst(in) != nil {
		t.Fatal("clock is not an authority binding")
	}
}

func TestBoundPacketMatchesSchemaSurface(t *testing.T) {
	data, err := os.ReadFile("../../../schemas/context-packet.schema.json")
	if err != nil {
		t.Fatal(err)
	}
	var schema struct {
		Required   []string
		Properties map[string]json.RawMessage
	}
	if err := json.Unmarshal(data, &schema); err != nil {
		t.Fatal(err)
	}
	packet, _ := (Compiler{}).CompileBound(boundFixture())
	data, _ = json.Marshal(packet)
	var fields map[string]any
	_ = json.Unmarshal(data, &fields)
	for _, key := range schema.Required {
		if _, ok := fields[key]; !ok {
			t.Errorf("missing required field %s", key)
		}
	}
	for key := range fields {
		if _, ok := schema.Properties[key]; !ok {
			t.Errorf("schema missing property %s", key)
		}
	}
}
