package context

import (
	"bytes"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"path"
	"strings"
	"unicode/utf8"
)

const QuickShadowSchema = "quick-context-shadow-v1"

// QuickShadowSource is supplied by the Quick runtime owner, never by an Agent
// JSON input. No field here grants permission or proves product acceptance.
type QuickShadowSource struct {
	ProjectIdentity string
	Workspace       string
	ItemID          string
	StatePath       string
	StateDigest     string
	SourceRevision  string
	OwnerPacket     json.RawMessage
}

// QuickShadowReport retains the COMPLETE legacy packet next to the projection.
// The projection alone is not executable. This is an internal diagnostic view,
// not a new persisted workflow artifact, approval, lease, cache or final claim.
type QuickShadowReport struct {
	Schema              string          `json:"schema"`
	Mode                string          `json:"mode"`
	AuthorizesExecution bool            `json:"authorizes_execution"`
	LiveCodeVerified    bool            `json:"live_code_verified"`
	ProjectIdentity     string          `json:"project_identity"`
	Workspace           string          `json:"workspace"`
	ItemID              string          `json:"item_id"`
	SourceFingerprint   string          `json:"source_fingerprint"`
	OwnerFieldCount     int             `json:"owner_field_count"`
	OwnerPacket         json.RawMessage `json:"owner_packet"`
	Projection          Packet          `json:"projection"`
}

// BuildQuickShadow reads the same owner twice and fails on observable drift.
// This is not a transaction or protection against a hostile concurrent writer.
// It neither retries, repairs state, starts work nor substitutes an executor.
func BuildQuickShadow(read func() (QuickShadowSource, error)) (QuickShadowReport, error) {
	if read == nil {
		return QuickShadowReport{}, fmt.Errorf("quick_shadow_owner_missing")
	}
	first, err := read()
	if err != nil {
		return QuickShadowReport{}, err
	}
	report, err := projectQuickShadow(first)
	if err != nil {
		return QuickShadowReport{}, err
	}
	second, err := read()
	if err != nil {
		return QuickShadowReport{}, err
	}
	// The first projection already validated the complete canonical contract.
	// Revalidate identity/wire shape and compare the fresh full fingerprint;
	// identical inputs do not need a second bound compilation/serialization.
	_, _, fingerprint, err := normalizeQuickShadowSource(second)
	if err != nil {
		return QuickShadowReport{}, err
	}
	if report.SourceFingerprint != fingerprint {
		return QuickShadowReport{}, fmt.Errorf("quick_shadow_source_changed: reread the selected owner; no partial report")
	}
	return report, nil
}

// VerifyQuickShadow reopens the actual owner; an old matching packet or state
// digest supplied by a caller cannot replace this fresh read. Still no authority.
func VerifyQuickShadow(report QuickShadowReport, read func() (QuickShadowSource, error)) error {
	// A typed caller can still supply invalid UTF-8. Do not let JSON's lossy
	// replacement turn a modified header into the fresh owner's valid identity.
	for _, value := range []string{report.Schema, report.Mode, report.ProjectIdentity,
		report.Workspace, report.ItemID, report.SourceFingerprint} {
		if !utf8.ValidString(value) {
			return fmt.Errorf("quick_shadow_identity_invalid: report header is not UTF-8")
		}
	}
	if err := report.Projection.validateBound(); err != nil {
		return err
	}
	if _, _, err := canonicalShadowObject(report.OwnerPacket); err != nil {
		return err
	}
	encoded, err := json.Marshal(report)
	if err != nil || len(encoded) > defaultMaxBytes {
		return fmt.Errorf("quick_shadow_budget_exceeded")
	}
	current, err := BuildQuickShadow(read)
	if err != nil {
		return err
	}
	// Only the informational clock differs. Every other returned field is checked.
	report.Projection.GeneratedAt, current.Projection.GeneratedAt = "", ""
	left, _ := json.Marshal(report)
	right, _ := json.Marshal(current)
	if !bytes.Equal(left, right) {
		return fmt.Errorf("quick_shadow_stale_or_modified: rebuild from the current owner")
	}
	return nil
}

// ValidateQuickShadowJSON protects a bounded diagnostic read before the existing
// owner decoder runs. It does not rewrite the object or approve its schema.
// The raw-state digest also binds bytes not projected by that existing owner.
func ValidateQuickShadowJSON(raw []byte) error {
	_, _, err := canonicalShadowObject(raw)
	return err
}

func canonicalShadowObject(raw []byte) (map[string]any, []byte, error) {
	if len(raw) == 0 || len(raw) > defaultMaxBytes || !utf8.Valid(raw) || !json.Valid(raw) {
		return nil, nil, fmt.Errorf("quick_shadow_json_invalid: require a bounded UTF-8 object")
	}
	if err := unicodeEscapes(raw); err != nil {
		return nil, nil, err
	}
	d := json.NewDecoder(bytes.NewReader(raw))
	d.UseNumber() // Preserve integer precision, including future opaque owner fields.
	value, err := uniqueJSONValue(d, 0)
	if err != nil {
		return nil, nil, err
	}
	if _, err := d.Token(); err != io.EOF {
		return nil, nil, fmt.Errorf("quick_shadow_json_invalid: trailing data")
	}
	object, ok := value.(map[string]any)
	if !ok {
		return nil, nil, fmt.Errorf("quick_shadow_json_invalid: expected object")
	}
	canonical, err := json.Marshal(object)
	return object, canonical, err
}

// Normalize only identity and wire representation; this is not an execution
// gate. The first projection performs the full admission checks. Matching this
// digest on a second read means all those exact inputs remained unchanged.
func normalizeQuickShadowSource(source QuickShadowSource) (QuickShadowSource, map[string]any, string, error) {
	if !digestShape(source.ProjectIdentity, 64) || !relative(source.Workspace) ||
		strings.TrimSpace(source.Workspace) != source.Workspace ||
		strings.Contains(source.Workspace, "/") || !quickShadowItemID(source.ItemID) ||
		!digestShape(source.StateDigest, 64) || !digestShape(source.SourceRevision, 40, 64) {
		return QuickShadowSource{}, nil, "", fmt.Errorf("quick_shadow_identity_invalid")
	}
	statePath := path.Join(".planning/quick", source.Workspace, "confirmation.json")
	if source.StatePath != statePath {
		return QuickShadowSource{}, nil, "", fmt.Errorf("quick_shadow_state_scope_invalid")
	}
	owner, canonical, err := canonicalShadowObject(source.OwnerPacket)
	if err != nil {
		return QuickShadowSource{}, nil, "", err
	}
	source.OwnerPacket = canonical
	identity, err := json.Marshal(source)
	if err != nil {
		return QuickShadowSource{}, nil, "", err
	}
	return source, owner, shadowSHA256(identity), nil
}

func projectQuickShadow(source QuickShadowSource) (QuickShadowReport, error) {
	source, owner, fingerprint, err := normalizeQuickShadowSource(source)
	if err != nil {
		return QuickShadowReport{}, err
	}
	state, _ := owner["confirmation_state"].(string)
	blockers, blockersOK := owner["blockers"].([]any)
	if owner["schema"] != "quick-worker-packet-v1" || owner["work_item_id"] != source.ItemID ||
		owner["ready"] != true || !blockersOK || len(blockers) != 0 ||
		(state != "confirmed" && state != "inherited") {
		return QuickShadowReport{}, fmt.Errorf("quick_shadow_owner_not_ready")
	}
	goal, _ := owner["goal"].(string)
	acceptance, _ := owner["acceptance"].(string)
	if acceptance == "" || owner["required_acceptance"] != acceptance {
		return QuickShadowReport{}, fmt.Errorf("quick_shadow_acceptance_mismatch")
	}
	rawScope, ok := owner["write_scope"].([]any)
	if !ok || len(rawScope) == 0 {
		return QuickShadowReport{}, fmt.Errorf("quick_shadow_scope_unprojectable: no nonempty file scope; keep the legacy path")
	}
	scope := make([]string, 0, len(rawScope))
	for _, entry := range rawScope {
		value, ok := entry.(string)
		if !ok {
			return QuickShadowReport{}, fmt.Errorf("quick_shadow_scope_invalid")
		}
		scope = append(scope, value)
	}
	// Bind the complete owner contract AND the local lineage. A decision-only
	// digest cannot stand in for raw confirmation bytes or execution state.
	statePath := source.StatePath
	projection, err := (Compiler{}).CompileBound(CompileRequest{
		TaskID: "quick:" + source.Workspace + "#" + source.ItemID, Workflow: "quick",
		Goal: goal, Scope: scope, Acceptance: []string{acceptance},
		Constraints: []string{"shadow-only: the complete owner_packet remains required; this projection is not executable",
			"quick-owner-snapshot-sha256:" + fingerprint},
		Artifacts: []Artifact{{Path: statePath, Reason: "Quick runtime-owned confirmation bytes", Digest: source.StateDigest}},
		StateRef:  statePath, StateDigest: source.StateDigest, SourceRevision: source.SourceRevision,
	})
	if err != nil {
		return QuickShadowReport{}, err
	}
	report := QuickShadowReport{
		Schema: QuickShadowSchema, Mode: "shadow-only", ProjectIdentity: source.ProjectIdentity,
		Workspace: source.Workspace, ItemID: source.ItemID, SourceFingerprint: fingerprint,
		OwnerFieldCount: len(owner), OwnerPacket: append(json.RawMessage(nil), source.OwnerPacket...), Projection: projection,
	}
	encoded, err := json.Marshal(report)
	if err != nil || len(encoded) > defaultMaxBytes {
		return QuickShadowReport{}, fmt.Errorf("quick_shadow_budget_exceeded: narrow inputs; never truncate the owner contract")
	}
	return report, nil
}

func quickShadowItemID(value string) bool {
	if len(value) < 2 || value[0] != 'Q' || value[1] < '1' || value[1] > '9' {
		return false
	}
	for _, char := range value[2:] {
		if char < '0' || char > '9' {
			return false
		}
	}
	return true
}

func shadowSHA256(data []byte) string {
	sum := sha256.Sum256(data)
	return hex.EncodeToString(sum[:])
}
