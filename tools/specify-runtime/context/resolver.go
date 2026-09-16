package context

// Resolver converts explicit runtime inputs into resolved context.
// It intentionally does not inspect arbitrary repository state, grant
// permissions, or decide acceptance. Those remain runtime-owned concerns.
type Resolver struct{}

// ResolveInput is the bounded input contract for context compilation.
type ResolveInput struct {
	TaskID       string
	Workflow     string
	Goal         string
	Scope        []string
	Artifacts    []Artifact
	Acceptance   []string
	Constraints  []string
	Skills       []string
	StateRef     string
}

// Artifact is an explicitly supplied context candidate.
type Artifact struct {
	Path   string
	Reason string
}

// ResolvedContext is a compiler-ready semantic view.
type ResolvedContext struct {
	TaskID      string
	Workflow    string
	Goal        string
	Artifacts   []Artifact
	Acceptance  []string
	Constraints []string
	Skills      []string
	StateRef    string
}

func (Resolver) Resolve(input ResolveInput) ResolvedContext {
	return ResolvedContext{
		TaskID: input.TaskID,
		Workflow: input.Workflow,
		Goal: input.Goal,
		Artifacts: append([]Artifact(nil), input.Artifacts...),
		Acceptance: append([]string(nil), input.Acceptance...),
		Constraints: append([]string(nil), input.Constraints...),
		Skills: append([]string(nil), input.Skills...),
		StateRef: input.StateRef,
	}
}
