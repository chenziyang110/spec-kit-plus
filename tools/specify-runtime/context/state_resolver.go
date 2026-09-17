package context

// StateResolver preserves explicit state identity without granting transitions.
type StateResolver struct{}

type StateInput struct {
	TaskID, Workflow, StateRef, StateDigest, SourceRevision string
}

type RuntimeState struct {
	TaskID, Workflow, StateRef, StateDigest, SourceRevision string
}

func (StateResolver) Resolve(in StateInput) RuntimeState {
	return RuntimeState{
		TaskID: in.TaskID, Workflow: in.Workflow, StateRef: in.StateRef,
		StateDigest: in.StateDigest, SourceRevision: in.SourceRevision,
	}
}
