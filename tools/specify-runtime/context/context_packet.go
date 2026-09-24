package context

import "time"

const PacketSchema = "context-packet-v2"

// Packet is a derived view. Bound means structurally bound to explicit inputs,
// not authorized, current, accepted, or ready for a workflow final claim.
type Packet struct {
	SchemaVersion     string     `json:"schema_version"`
	Bound             bool       `json:"bound"`
	TaskID            string     `json:"task_id,omitempty"`
	Workflow          string     `json:"workflow,omitempty"`
	Goal              string     `json:"goal"`
	Scope             []string   `json:"scope,omitempty"`
	Constraints       []string   `json:"constraints,omitempty"`
	RequiredSkills    []string   `json:"required_skills,omitempty"`
	RelevantArtifacts []string   `json:"relevant_artifacts,omitempty"`
	ArtifactDetails   []Artifact `json:"artifact_details,omitempty"`
	Acceptance        []string   `json:"acceptance,omitempty"`
	ForbiddenActions  []string   `json:"forbidden_actions,omitempty"`
	RuntimeStateRef   string     `json:"runtime_state_ref,omitempty"`
	StateDigest       string     `json:"state_digest,omitempty"`
	SourceRevision    string     `json:"source_revision,omitempty"`
	ContentDigest     string     `json:"content_digest,omitempty"`
	GeneratedAt       string     `json:"generated_at"`
}

func New(goal string) Packet {
	return Packet{SchemaVersion: PacketSchema, Goal: goal, GeneratedAt: time.Now().UTC().Format(time.RFC3339)}
}
