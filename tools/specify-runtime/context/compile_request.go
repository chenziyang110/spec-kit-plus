package context

// CompileRequest contains facts resolved by the owning runtime. It is not a
// permission grant, and caller-supplied hashes alone do not prove live facts.
type CompileRequest struct {
	TaskID, Workflow, Goal                string
	Scope                                 []string
	Artifacts                             []Artifact
	Skills, Constraints, Acceptance       []string
	ForbiddenActions                      []string
	StateRef, StateDigest, SourceRevision string
}

func (r ResolvedContext) ToCompileRequest() CompileRequest {
	return CompileRequest{
		TaskID: r.TaskID, Workflow: r.Workflow, Goal: r.Goal,
		Scope: clone(r.Scope), Artifacts: append([]Artifact(nil), r.Artifacts...),
		Skills: clone(r.Skills), Constraints: clone(r.Constraints),
		Acceptance: clone(r.Acceptance), ForbiddenActions: clone(r.ForbiddenActions),
		StateRef: r.StateRef, StateDigest: r.StateDigest, SourceRevision: r.SourceRevision,
	}
}

func (r CompileRequest) ToCompilerInput() Input {
	paths := make([]string, 0, len(r.Artifacts))
	for _, artifact := range r.Artifacts {
		paths = append(paths, artifact.Path)
	}
	return Input{
		TaskID: r.TaskID, Workflow: r.Workflow, Goal: r.Goal, Scope: clone(r.Scope),
		Skills: clone(r.Skills), Artifacts: paths,
		ArtifactDetails: append([]Artifact(nil), r.Artifacts...), Rules: clone(r.Constraints),
		Acceptance: clone(r.Acceptance), ForbiddenActions: clone(r.ForbiddenActions),
		StateRef: r.StateRef, StateDigest: r.StateDigest, SourceRevision: r.SourceRevision,
	}
}
