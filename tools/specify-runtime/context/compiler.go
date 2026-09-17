package context

// Compiler assembles runtime-supplied context. MaxBytes is an output budget:
// a bound compilation fails rather than truncating any required constraint.
type Compiler struct{ MaxBytes int }

type Input struct {
	Goal, TaskID, Workflow                string
	Scope, Skills, Artifacts              []string
	ArtifactDetails                       []Artifact
	Rules, Acceptance, ForbiddenActions   []string
	StateRef, StateDigest, SourceRevision string
}

// Compile preserves the original inspection-only API. Its output is unbound
// and must not be consumed as an executable contract. Use CompileBound and
// VerifyAgainst with fresh owner-resolved inputs at the consumption boundary.
func (Compiler) Compile(in Input) Packet {
	packet := New(in.Goal)
	packet.TaskID, packet.Workflow = in.TaskID, in.Workflow
	packet.Scope, packet.RequiredSkills = clone(in.Scope), clone(in.Skills)
	packet.RelevantArtifacts = clone(in.Artifacts)
	packet.ArtifactDetails = append([]Artifact(nil), in.ArtifactDetails...)
	packet.Constraints, packet.Acceptance = clone(in.Rules), clone(in.Acceptance)
	packet.ForbiddenActions = clone(in.ForbiddenActions)
	packet.RuntimeStateRef, packet.StateDigest = in.StateRef, in.StateDigest
	packet.SourceRevision = in.SourceRevision
	return packet
}
