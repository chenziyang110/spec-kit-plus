package context

// Compiler builds bounded context packets from runtime-owned facts.
// The initial implementation intentionally accepts explicit inputs only.
// Repository scanning, permission checks and state lookup stay owned by the
// runtime and will be added behind this boundary.
type Compiler struct{}

type Input struct {
	Goal       string
	Skills     []string
	Artifacts  []string
	Rules      []string
	Acceptance []string
	StateRef   string
}

func (Compiler) Compile(in Input) Packet {
	packet := New(in.Goal)
	packet.RequiredSkills = append([]string(nil), in.Skills...)
	packet.RelevantArtifacts = append([]string(nil), in.Artifacts...)
	packet.Constraints = append([]string(nil), in.Rules...)
	packet.Acceptance = append([]string(nil), in.Acceptance...)
	packet.RuntimeStateRef = in.StateRef
	return packet
}
