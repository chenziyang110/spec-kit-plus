package main

import (
	"crypto/sha256"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"time"

	rt "github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/runtime"
)

const closeoutIntentVersion = 1

type closeoutIntent struct {
	Version            int      `json:"version"`
	ID                 string   `json:"id"`
	State              string   `json:"state"`
	Workflow           string   `json:"workflow"`
	Scope              string   `json:"scope"`
	Reason             string   `json:"reason"`
	PayloadJSON        string   `json:"payload_json,omitempty"`
	DeltaSessionID     string   `json:"delta_session_id,omitempty"`
	CommitRange        string   `json:"commit_range,omitempty"`
	InputDigest        string   `json:"input_digest"`
	ChangedPaths       []string `json:"changed_paths"`
	UpdateID           string   `json:"update_id,omitempty"`
	UpdateOutcome      string   `json:"update_outcome,omitempty"`
	ActiveGenerationID string   `json:"active_generation_id,omitempty"`
	ChangedBasis       []string `json:"changed_basis,omitempty"`
	RecordedAt         string   `json:"recorded_at"`
}

func ensureCloseoutIntent(paths rt.Paths, workflow string, scope string, reason string, payloadJSON string, deltaSession string, commitRange string, changedPaths []string) (closeoutIntent, string, bool, error) {
	digest := closeoutIntentDigest(workflow, scope, reason, payloadJSON, deltaSession, commitRange)
	intent := closeoutIntent{
		Version:        closeoutIntentVersion,
		ID:             "intent-" + digest[:24],
		State:          "pending_update",
		Workflow:       workflow,
		Scope:          scope,
		Reason:         reason,
		PayloadJSON:    payloadJSON,
		DeltaSessionID: deltaSession,
		CommitRange:    commitRange,
		InputDigest:    digest,
		ChangedPaths:   normalizedCloseoutPaths(changedPaths),
		RecordedAt:     time.Now().UTC().Format(time.RFC3339Nano),
	}
	path := closeoutIntentPath(paths, intent.ID)
	if raw, err := os.ReadFile(path); err == nil {
		var existing closeoutIntent
		if err := json.Unmarshal(raw, &existing); err != nil {
			return closeoutIntent{}, "", false, fmt.Errorf("parse closeout intent %s: %w", filepath.ToSlash(path), err)
		}
		if existing.Version != closeoutIntentVersion || existing.InputDigest != digest || existing.Workflow != workflow || existing.Scope != scope {
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
			return nil, err
		}
		if err := validateCloseoutIntent(intent); err != nil {
			return nil, fmt.Errorf("invalid closeout intent %s: %w", entry.Name(), err)
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

func validateCloseoutIntent(intent closeoutIntent) error {
	if intent.Version != closeoutIntentVersion || strings.TrimSpace(intent.ID) == "" {
		return fmt.Errorf("unsupported or missing intent identity")
	}
	digest := closeoutIntentDigest(intent.Workflow, intent.Scope, intent.Reason, intent.PayloadJSON, intent.DeltaSessionID, intent.CommitRange)
	if intent.InputDigest != digest || intent.ID != "intent-"+digest[:24] {
		return fmt.Errorf("intent digest mismatch")
	}
	return nil
}

func runCognitionCloseoutReplayCLI(args []string, stdout io.Writer) int {
	projectRoot := optionValue(args, "--project-root", ".")
	paths, err := rt.ResolvePaths(projectRoot)
	if err != nil {
		return writeEnvelope(stdout, scriptDomainError("cognition", err))
	}
	scopeDir := firstNonEmpty(optionValue(args, "--scope-dir", ""), optionValue(args, "--feature-dir", ""), optionValue(args, "--workspace", ""))
	absScope, relScope, err := resolveCloseoutApplyScope(paths.Root, scopeDir)
	if err != nil {
		return writeEnvelope(stdout, scriptDomainError("cognition", err))
	}
	receipt, err := loadMutationCognitionReceipt(absScope)
	if err != nil {
		return writeEnvelope(stdout, scriptDomainError("cognition", err))
	}
	if receipt == nil || normalizeMutationCognitionState(receipt.ResultState) != "blocked" {
		return writeEnvelope(stdout, scriptDomainError("cognition", fmt.Errorf("closeout replay requires a blocked cognition-closeout.json for %s", relScope)))
	}
	intents, err := listCloseoutIntents(paths)
	if err != nil {
		return writeEnvelope(stdout, scriptDomainError("cognition", err))
	}
	matches := []closeoutIntent{}
	for _, intent := range intents {
		if intent.Scope == relScope {
			matches = append(matches, intent)
		}
	}
	if len(matches) != 1 {
		return writeEnvelope(stdout, scriptDomainError("cognition", fmt.Errorf("closeout replay found %d intents for %s; expected exactly one", len(matches), relScope)))
	}
	intent := matches[0]
	intentRef := closeoutIntentRef(paths, closeoutIntentPath(paths, intent.ID))
	if receipt.IntentID != intent.ID || receipt.IntentRef != intentRef || receipt.IntentDigest != intent.InputDigest {
		return writeEnvelope(stdout, scriptDomainError("cognition", fmt.Errorf("blocked closeout receipt does not bind the selected replay intent")))
	}
	replayArgs := []string{
		"--project-root", paths.Root,
		"--workflow", intent.Workflow,
		"--scope-dir", intent.Scope,
		"--reason", intent.Reason,
		"--format", "json",
	}
	if intent.PayloadJSON != "" {
		replayArgs = append(replayArgs, "--payload-json", "-")
		return runCognitionCloseoutApplyCLIWithInput(replayArgs, strings.NewReader(intent.PayloadJSON), stdout)
	}
	replayArgs = append(replayArgs, "--delta-session", intent.DeltaSessionID)
	if intent.CommitRange != "" {
		replayArgs = append(replayArgs, "--commit-range", intent.CommitRange)
	}
	return runCognitionCloseoutApplyCLIWithInput(replayArgs, strings.NewReader(""), stdout)
}
