package context

// StateResolver extracts runtime-owned state references into context inputs.
// It does not grant permissions or decide lifecycle transitions.
type StateResolver struct{}

type StateInput struct {
	TaskID   string
	Workflow string
	StateRef string
}

type RuntimeState struct {
	TaskID   string
	Workflow string
	StateRef string
}

func (StateResolver) Resolve(input StateInput) RuntimeState {
	return RuntimeState{
		TaskID:   input.TaskID,
		Workflow: input.Workflow,
		StateRef: input.StateRef,
	}
}
