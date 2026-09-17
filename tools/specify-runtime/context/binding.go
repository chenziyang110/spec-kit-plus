package context

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"path"
	"strings"
	"time"
	"unicode/utf8"
)

const defaultMaxBytes = 128 * 1024

// CompileBound refuses incomplete bindings. The owner must obtain all facts
// from trusted runtime APIs; this pure function does not inspect repository IO.
func (c Compiler) CompileBound(in CompileRequest) (Packet, error) {
	if err := validateRequest(in); err != nil {
		return Packet{}, err
	}
	packet := c.Compile(in.ToCompilerInput())
	packet.Bound = true
	packet.ContentDigest = packet.digest()
	limit := c.MaxBytes
	if limit == 0 {
		limit = defaultMaxBytes
	}
	encoded, err := json.Marshal(packet)
	if err != nil {
		return Packet{}, err
	}
	if limit < 0 || limit > defaultMaxBytes || len(encoded) > limit {
		return Packet{}, fmt.Errorf("context_budget_exceeded: need %d bytes, budget %d; narrow owner-selected context, never drop obligations", len(encoded), limit)
	}
	return packet, nil
}

// VerifyAgainst checks both packet integrity and an exact fresh owner snapshot.
// It deliberately does not check permissions or decide acceptance. A matching
// packet must still pass the owning workflow's existing consumption gates.
func (p Packet) VerifyAgainst(in CompileRequest) error {
	if err := p.validateBound(); err != nil {
		return err
	}
	expected, err := (Compiler{}).CompileBound(in)
	if err != nil {
		return err
	}
	if expected.ContentDigest != p.ContentDigest {
		return fmt.Errorf("context_stale: task, scope, state, source, or obligations changed; recompile")
	}
	return nil
}

// validateBound checks a packet's own shape and redundant projections. It does
// not establish freshness; only the owning runtime can resolve current inputs.
func (p Packet) validateBound() error {
	encoded, err := json.Marshal(p)
	if err != nil || len(encoded) > defaultMaxBytes {
		return fmt.Errorf("context_budget_exceeded: encoded packet exceeds the bounded read limit")
	}
	if !p.Bound || p.SchemaVersion != PacketSchema || p.ContentDigest != p.digest() {
		return fmt.Errorf("context_integrity_invalid: unbound or modified packet")
	}
	if _, err := time.Parse(time.RFC3339, p.GeneratedAt); err != nil {
		return fmt.Errorf("context_timestamp_invalid: %w", err)
	}
	expected, err := (Compiler{}).CompileBound(CompileRequest{
		TaskID: p.TaskID, Workflow: p.Workflow, Goal: p.Goal, Scope: p.Scope,
		Artifacts: p.ArtifactDetails, Skills: p.RequiredSkills,
		Constraints: p.Constraints, Acceptance: p.Acceptance,
		ForbiddenActions: p.ForbiddenActions, StateRef: p.RuntimeStateRef,
		StateDigest: p.StateDigest, SourceRevision: p.SourceRevision,
	})
	if err != nil {
		return err
	}
	if expected.ContentDigest != p.ContentDigest {
		return fmt.Errorf("context_projection_invalid: artifact paths do not match their bound details")
	}
	return nil
}

func (p Packet) digest() string {
	// GeneratedAt is informational, not an authorization clock or a cache key.
	p.GeneratedAt, p.ContentDigest = "", ""
	encoded, _ := json.Marshal(p) // Packet contains only serializable concrete types.
	sum := sha256.Sum256(encoded)
	return hex.EncodeToString(sum[:])
}

func digestShape(value string, sizes ...int) bool {
	for _, size := range sizes {
		if len(value) == size && strings.ToLower(value) == value {
			_, err := hex.DecodeString(value)
			return err == nil
		}
	}
	return false
}

func relative(value string) bool {
	trimmed := strings.TrimSuffix(value, "/")
	return utf8.ValidString(value) && trimmed != "" && trimmed != "." && trimmed != ".." &&
		!strings.HasPrefix(trimmed, "../") && !path.IsAbs(trimmed) &&
		!strings.ContainsAny(trimmed, "\\:\x00\r\n") && path.Clean(trimmed) == trimmed
}

func validateRequest(in CompileRequest) error {
	for _, field := range []struct{ name, value string }{
		{"task_id", in.TaskID}, {"workflow", in.Workflow}, {"goal", in.Goal}, {"state_ref", in.StateRef},
	} {
		if !utf8.ValidString(field.value) || strings.TrimSpace(field.value) == "" {
			return fmt.Errorf("context_binding_invalid: %s must be non-empty UTF-8", field.name)
		}
	}
	if !digestShape(in.StateDigest, 64) || !digestShape(in.SourceRevision, 40, 64) {
		return fmt.Errorf("context_binding_invalid: require state SHA-256 and source Git revision")
	}
	if len(in.Scope) == 0 || len(in.Acceptance) == 0 {
		return fmt.Errorf("context_binding_missing: scope and acceptance are required")
	}
	for _, scope := range in.Scope {
		if !relative(scope) {
			return fmt.Errorf("context_scope_invalid: %q", scope)
		}
	}
	seen := map[string]bool{}
	for _, artifact := range in.Artifacts {
		if !relative(artifact.Path) || strings.HasSuffix(artifact.Path, "/") ||
			!utf8.ValidString(artifact.Reason) || strings.TrimSpace(artifact.Reason) == "" || !digestShape(artifact.Digest, 64) {
			return fmt.Errorf("context_artifact_invalid: %q requires canonical path, reason, and SHA-256", artifact.Path)
		}
		if seen[artifact.Path] {
			return fmt.Errorf("context_artifact_duplicate: %q", artifact.Path)
		}
		seen[artifact.Path] = true
	}
	for _, values := range [][]string{in.Acceptance, in.Constraints, in.Skills, in.ForbiddenActions} {
		for _, value := range values {
			if !utf8.ValidString(value) || strings.TrimSpace(value) == "" {
				return fmt.Errorf("context_obligation_invalid: entries must be non-empty UTF-8")
			}
		}
	}
	return nil
}
