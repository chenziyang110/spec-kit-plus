package main

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"time"

	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/delta"
	rt "github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/runtime"
	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/update"
)

const closeoutIntentVersion = 1

type closeoutIntent struct {
	Version              int                           `json:"version"`
	ID                   string                        `json:"id"`
	State                string                        `json:"state"`
	Workflow             string                        `json:"workflow"`
	Scope                string                        `json:"scope"`
	Reason               string                        `json:"reason"`
	PayloadJSON          string                        `json:"payload_json,omitempty"`
	DeltaSessionID       string                        `json:"delta_session_id,omitempty"`
	DeltaDigest          string                        `json:"delta_digest,omitempty"`
	CommitRange          string                        `json:"commit_range,omitempty"`
	InputDigest          string                        `json:"input_digest"`
	ChangedPaths         []string                      `json:"changed_paths"`
	UpdateID             string                        `json:"update_id,omitempty"`
	UpdateOutcome        string                        `json:"update_outcome,omitempty"`
	ActiveGenerationID   string                        `json:"active_generation_id,omitempty"`
	ChangedBasis         []string                      `json:"changed_basis,omitempty"`
	RecordedAt           string                        `json:"recorded_at"`
	VerificationOverride []update.VerificationEvidence `json:"verification_override,omitempty"`
	RepairsIntentID      string                        `json:"repairs_intent_id,omitempty"`
	DoBinding            *DoCognitionBinding           `json:"do_binding,omitempty"`
}

func ensureCloseoutIntent(paths rt.Paths, workflow string, scope string, reason string, payloadJSON string, deltaSession string, commitRange string, changedPaths []string, expectedDeltaDigest ...string) (closeoutIntent, string, bool, error) {
	return ensureCloseoutIntentWithDoBinding(paths, workflow, scope, reason, payloadJSON, deltaSession, commitRange, changedPaths, nil, expectedDeltaDigest...)
}

func ensureCloseoutIntentWithDoBinding(paths rt.Paths, workflow string, scope string, reason string, payloadJSON string, deltaSession string, commitRange string, changedPaths []string, binding *DoCognitionBinding, expectedDeltaDigest ...string) (closeoutIntent, string, bool, error) {
	deltaDigest, err := closeoutDeltaDigest(paths, deltaSession)
	if err != nil {
		return closeoutIntent{}, "", false, err
	}
	if len(expectedDeltaDigest) > 0 && deltaDigest != expectedDeltaDigest[0] {
		return closeoutIntent{}, "", false, fmt.Errorf("delta session digest changed after closeout preflight; rerun preflight before creating an intent")
	}
	intent := closeoutIntent{
		Version:        closeoutIntentVersion,
		State:          "pending_update",
		Workflow:       workflow,
		Scope:          scope,
		Reason:         reason,
		PayloadJSON:    payloadJSON,
		DeltaSessionID: deltaSession,
		DeltaDigest:    deltaDigest,
		CommitRange:    commitRange,
		ChangedPaths:   normalizedCloseoutPaths(changedPaths),
		RecordedAt:     time.Now().UTC().Format(time.RFC3339Nano),
		DoBinding:      binding,
	}
	digest := storedCloseoutIntentDigest(intent)
	intent.ID, intent.InputDigest = "intent-"+digest[:24], digest
	path := closeoutIntentPath(paths, intent.ID)
	if raw, err := os.ReadFile(path); err == nil {
		var existing closeoutIntent
		if err := json.Unmarshal(raw, &existing); err != nil {
			return closeoutIntent{}, "", false, fmt.Errorf("parse closeout intent %s: %w", filepath.ToSlash(path), err)
		}
		if err := validateCloseoutIntent(paths, existing); err != nil || existing.InputDigest != digest || existing.Workflow != workflow || existing.Scope != scope {
			return closeoutIntent{}, "", false, fmt.Errorf("closeout intent identity mismatch for %s", filepath.ToSlash(path))
		}
		return existing, closeoutIntentRef(paths, path), true, nil
	} else if !os.IsNotExist(err) {
		return closeoutIntent{}, "", false, fmt.Errorf("read closeout intent %s: %w", filepath.ToSlash(path), err)
	}
	if err := writeCloseoutIntent(path, intent); err != nil {
		return closeoutIntent{}, "", false, err
	}
	return intent, closeoutIntentRef(paths, path), false, nil
}

func updateCloseoutIntent(paths rt.Paths, intent closeoutIntent) error {
	return writeCloseoutIntent(closeoutIntentPath(paths, intent.ID), intent)
}

func removeCloseoutIntent(paths rt.Paths, intent closeoutIntent) error {
	err := os.Remove(closeoutIntentPath(paths, intent.ID))
	if err != nil && !os.IsNotExist(err) {
		return fmt.Errorf("remove closeout intent %s: %w", intent.ID, err)
	}
	return nil
}

func closeoutIntentPath(paths rt.Paths, intentID string) string {
	return filepath.Join(paths.RuntimeDir, "closeout-intents", intentID+".json")
}

func closeoutIntentRef(paths rt.Paths, path string) string {
	if rel, err := filepath.Rel(paths.Root, path); err == nil {
		return filepath.ToSlash(rel)
	}
	return filepath.ToSlash(path)
}

func closeoutIntentDigest(values ...string) string {
	digest := sha256.Sum256([]byte(strings.Join(values, "\x00")))
	return fmt.Sprintf("%x", digest[:])
}

func writeCloseoutIntent(path string, intent closeoutIntent) error {
	intent.ChangedPaths = normalizedCloseoutPaths(intent.ChangedPaths)
	intent.ChangedBasis = normalizedCloseoutPaths(intent.ChangedBasis)
	return writeScriptJSONFile(path, intent)
}

func listCloseoutIntents(paths rt.Paths) ([]closeoutIntent, error) {
	dir := filepath.Join(paths.RuntimeDir, "closeout-intents")
	entries, err := os.ReadDir(dir)
	if os.IsNotExist(err) {
		return []closeoutIntent{}, nil
	}
	if err != nil {
		return nil, err
	}
	intents := []closeoutIntent{}
	for _, entry := range entries {
		if entry.IsDir() || filepath.Ext(entry.Name()) != ".json" {
			continue
		}
		raw, err := os.ReadFile(filepath.Join(dir, entry.Name()))
		if err != nil {
			return nil, err
		}
		var intent closeoutIntent
		if err := json.Unmarshal(raw, &intent); err != nil {
			return nil, &closeoutReplayError{IntentID: strings.TrimSuffix(entry.Name(), ".json"), Err: fmt.Errorf("invalid closeout intent JSON")}
		}
		if entry.Name() != intent.ID+".json" {
			return nil, &closeoutReplayError{IntentID: strings.TrimSuffix(entry.Name(), ".json"), Err: fmt.Errorf("closeout intent filename does not match identity")}
		}
		if err := validateCloseoutIntent(paths, intent); err != nil {
			return nil, &closeoutReplayError{IntentID: intent.ID, Err: err}
		}
		intents = append(intents, intent)
	}
	sort.Slice(intents, func(i, j int) bool {
		if intents[i].RecordedAt == intents[j].RecordedAt {
			return intents[i].ID < intents[j].ID
		}
		return intents[i].RecordedAt < intents[j].RecordedAt
	})
	return intents, nil
}

func validateCloseoutIntent(paths rt.Paths, intent closeoutIntent) error {
	if err := validateCloseoutIntentIdentity(intent); err != nil {
		return err
	}
	deltaDigest, err := closeoutDeltaDigest(paths, intent.DeltaSessionID)
	if err != nil {
		return err
	}
	if deltaDigest != intent.DeltaDigest {
		return fmt.Errorf("delta session digest changed")
	}
	return nil
}

func validateCloseoutIntentIdentity(intent closeoutIntent) error {
	if intent.Version != closeoutIntentVersion || !validCloseoutIntentID(intent.ID) {
		return fmt.Errorf("unsupported or missing intent identity")
	}
	if (intent.PayloadJSON == "") == (intent.DeltaSessionID == "") {
		return fmt.Errorf("intent must bind exactly one payload or delta session")
	}
	if _, err := normalizeMutationWorkflowID(intent.Workflow); err != nil {
		return err
	}
	switch intent.State {
	case "pending_update", "pending_validation", "receipt_recorded", "scope_receipt_recorded":
	default:
		return fmt.Errorf("invalid closeout intent state")
	}
	if intent.VerificationOverride != nil || intent.RepairsIntentID != "" {
		if !validCloseoutIntentID(intent.RepairsIntentID) || len(intent.VerificationOverride) == 0 {
			return fmt.Errorf("invalid repaired intent binding")
		}
		if err := update.ValidateVerificationEvidence(intent.VerificationOverride); err != nil {
			return err
		}
	}
	digest := storedCloseoutIntentDigest(intent)
	if intent.InputDigest != digest || intent.ID != "intent-"+digest[:24] {
		return fmt.Errorf("intent digest mismatch")
	}
	return nil
}

func storedCloseoutIntentDigest(intent closeoutIntent) string {
	values := []string{intent.Workflow, intent.Scope, intent.Reason, intent.PayloadJSON, intent.DeltaSessionID, intent.CommitRange, intent.DeltaDigest}
	if intent.DoBinding != nil {
		raw, _ := json.Marshal(intent.DoBinding)
		values = append(values, "do-source-basis", string(raw))
	}
	if intent.VerificationOverride != nil || intent.RepairsIntentID != "" {
		raw, _ := json.Marshal(intent.VerificationOverride)
		values = append(values, "verification-repair", intent.RepairsIntentID, string(raw))
	}
	return closeoutIntentDigest(values...)
}

func validCloseoutIntentID(value string) bool {
	if !strings.HasPrefix(value, "intent-") || len(value) != len("intent-")+24 {
		return false
	}
	_, err := hex.DecodeString(strings.TrimPrefix(value, "intent-"))
	return err == nil && strings.ToLower(value) == value
}

func loadCloseoutIntent(paths rt.Paths, id string) (closeoutIntent, error) {
	if !validCloseoutIntentID(id) {
		return closeoutIntent{}, fmt.Errorf("--intent-id must be an exact intent ID")
	}
	raw, err := os.ReadFile(closeoutIntentPath(paths, id))
	if err != nil {
		return closeoutIntent{}, err
	}
	var intent closeoutIntent
	if err := json.Unmarshal(raw, &intent); err != nil {
		return closeoutIntent{}, fmt.Errorf("invalid closeout intent JSON")
	}
	if intent.ID != id {
		return closeoutIntent{}, fmt.Errorf("closeout intent filename does not match identity")
	}
	if err := validateCloseoutIntent(paths, intent); err != nil {
		return closeoutIntent{}, err
	}
	return intent, nil
}

func closeoutDeltaDigest(paths rt.Paths, sessionID string) (string, error) {
	sessionID = strings.TrimSpace(sessionID)
	if sessionID == "" {
		return "", nil
	}
	bundle, err := delta.Load(paths.RuntimeDir, sessionID)
	if err != nil {
		return "", err
	}
	return delta.Digest(bundle)
}

func runCognitionCloseoutReplayCLI(args []string, stdout io.Writer) int {
	if containsHelpFlag(args) {
		env := NewEnvelope("ok", "project cognition closeout replay usage")
		env.Data["usage"] = "specify-runtime cognition closeout replay (--intent-id <id> --expected-digest <sha256> | --scope-dir <scope>) [--project-root <path>] --format json"
		return writeEnvelope(stdout, env)
	}
	projectRoot := optionValue(args, "--project-root", ".")
	paths, err := rt.ResolvePaths(projectRoot)
	if err != nil {
		return writeEnvelope(stdout, scriptDomainError("cognition", err))
	}
	return replaySelectedCloseoutIntent(paths, args, stdout)
}
