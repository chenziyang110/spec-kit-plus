package context

import "time"

// Packet is the bounded execution context delivered to an agent.
// It is a compiled view, not a new source of truth.
type Packet struct {
	Goal              string   `json:"goal"`
	Constraints       []string `json:"constraints,omitempty"`
	RequiredSkills    []string `json:"required_skills,omitempty"`
	RelevantArtifacts []string `json:"relevant_artifacts,omitempty"`
	Acceptance        []string `json:"acceptance,omitempty"`
	ForbiddenActions  []string `json:"forbidden_actions,omitempty"`
	RuntimeStateRef   string   `json:"runtime_state_ref,omitempty"`
	GeneratedAt       string   `json:"generated_at"`
}

func New(goal string) Packet {
	return Packet{Goal: goal, GeneratedAt: time.Now().UTC().Format(time.RFC3339)}
}
