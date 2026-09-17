package context

// Resolver copies explicit runtime inputs; it neither discovers facts nor grants authority.
type Resolver struct{}

type ResolveInput struct {
	TaskID, Workflow, Goal                string
	Scope                                 []string
	Artifacts                             []Artifact
	Acceptance, Constraints, Skills       []string
	ForbiddenActions                      []string
	StateRef, StateDigest, SourceRevision string
}

// Artifact retains the reason and exact content identity selected by the runtime.
// A digest supplied here must be rechecked by the owner against live bytes.
type Artifact struct {
	Path   string `json:"path"`
	Reason string `json:"reason"`
	Digest string `json:"digest,omitempty"`
}

type ResolvedContext struct {
	TaskID, Workflow, Goal                string
	Scope                                 []string
	Artifacts                             []Artifact
	Acceptance, Constraints, Skills       []string
	ForbiddenActions                      []string
	StateRef, StateDigest, SourceRevision string
}

func (Resolver) Resolve(in ResolveInput) ResolvedContext {
	return ResolvedContext{
		TaskID: in.TaskID, Workflow: in.Workflow, Goal: in.Goal,
		Scope: clone(in.Scope), Artifacts: append([]Artifact(nil), in.Artifacts...),
		Acceptance: clone(in.Acceptance), Constraints: clone(in.Constraints),
		Skills: clone(in.Skills), ForbiddenActions: clone(in.ForbiddenActions),
		StateRef: in.StateRef, StateDigest: in.StateDigest, SourceRevision: in.SourceRevision,
	}
}

func clone(values []string) []string { return append([]string(nil), values...) }
