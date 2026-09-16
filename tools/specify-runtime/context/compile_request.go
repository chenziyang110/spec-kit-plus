package context

// CompileRequest is the runtime-owned input boundary for producing a context
// packet. It intentionally contains facts already resolved by runtime layers.
// It is not a permission grant and it does not prove acceptance.
type CompileRequest struct {
	TaskID      string
	Workflow    string
	Goal        string
	Artifacts   []Artifact
	Skills      []string
	Constraints []string
	Acceptance  []string
	StateRef    string
}

func (r CompileRequest) ToCompilerInput() Input {
	artifactPaths := make([]string, 0, len(r.Artifacts))
	for _, artifact := range r.Artifacts {
		artifactPaths = append(artifactPaths, artifact.Path)
	}

	return Input{
		Goal:       r.Goal,
		Skills:     append([]string(nil), r.Skills...),
		Artifacts:  artifactPaths,
		Rules:      append([]string(nil), r.Constraints...),
		Acceptance: append([]string(nil), r.Acceptance...),
		StateRef:   r.StateRef,
	}
}
