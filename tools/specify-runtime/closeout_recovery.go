package main

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strings"

	rt "github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/runtime"
	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/store"
	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/update"
)

// The immutable repair record is the publication decision. Recovery can finish
// publishing its successor after a crash without guessing which input won.
type closeoutRepairRecord struct {
	Original    closeoutIntent `json:"original"`
	Replacement closeoutIntent `json:"replacement"`
}

type closeoutReplayError struct {
	IntentID string
	Err      error
}

func (err *closeoutReplayError) Error() string {
	return fmt.Sprintf("replay older closeout intent %s: %v", err.IntentID, err.Err)
}
func (err *closeoutReplayError) Unwrap() error { return err.Err }

var (
	closeoutRepairAfterJournalHook         func() error
	closeoutRepairAfterReplacementHook     func() error
	closeoutRepairAfterOriginalRemovalHook func() error
)

func closeoutRecoveryArgv(paths rt.Paths, action, id, digest string) []string {
	argv := []string{"specify-runtime", "cognition", "closeout", action, "--project-root", paths.Root, "--intent-id", id}
	if digest != "" {
		argv = append(argv, "--expected-digest", digest)
	}
	return append(argv, "--format", "json")
}

func closeoutRepairPath(paths rt.Paths, id string) string {
	return filepath.Join(paths.RuntimeDir, "closeout-repairs", id+".json")
}

func closeoutReplacement(original closeoutIntent, verification []update.VerificationEvidence) closeoutIntent {
	next := original
	next.State = "pending_update"
	next.UpdateID, next.UpdateOutcome, next.ActiveGenerationID = "", "", ""
	next.ChangedBasis = nil
	next.VerificationOverride = append([]update.VerificationEvidence{}, verification...)
	next.RepairsIntentID = original.ID
	next.InputDigest = storedCloseoutIntentDigest(next)
	next.ID = "intent-" + next.InputDigest[:24]
	return next
}

func loadCloseoutRepair(paths rt.Paths, id string) (closeoutRepairRecord, error) {
	if !validCloseoutIntentID(id) {
		return closeoutRepairRecord{}, fmt.Errorf("invalid repair intent ID")
	}
	raw, err := os.ReadFile(closeoutRepairPath(paths, id))
	if err != nil {
		return closeoutRepairRecord{}, err
	}
	var record closeoutRepairRecord
	if err := json.Unmarshal(raw, &record); err != nil {
		return record, fmt.Errorf("invalid closeout repair record")
	}
	if record.Original.ID != id {
		return record, fmt.Errorf("repair record does not bind its original intent")
	}
	if err := validateCloseoutIntentIdentity(record.Original); err != nil {
		return record, err
	}
	if err := validateCloseoutIntentIdentity(record.Replacement); err != nil {
		return record, err
	}
	want, _ := json.Marshal(closeoutReplacement(record.Original, record.Replacement.VerificationOverride))
	actual, _ := json.Marshal(record.Replacement)
	if !bytes.Equal(want, actual) {
		return record, fmt.Errorf("repair record changes fields outside verification")
	}
	return record, nil
}

// Query every generation: a crash after the database commit can leave the
// durable intent looking uncommitted, and the active generation can change.
func closeoutCommittedUpdate(paths rt.Paths, id string) (string, error) {
	st, err := store.OpenExisting(paths)
	if err != nil {
		return "", fmt.Errorf("cannot establish whether closeout committed: %w", err)
	}
	defer st.Close()
	rows, err := st.DB().QueryContext(context.Background(), `SELECT id, attrs_json FROM updates WHERE json_extract(attrs_json, '$.closeout_intent_id') = ?`, id)
	if err != nil {
		return "", err
	}
	defer rows.Close()
	found := ""
	for rows.Next() {
		var updateID, attrsJSON string
		if err := rows.Scan(&updateID, &attrsJSON); err != nil {
			return "", err
		}
		var attrs struct {
			IntentID string `json:"closeout_intent_id"`
		}
		if err := json.Unmarshal([]byte(attrsJSON), &attrs); err != nil {
			return "", fmt.Errorf("cannot inspect update binding")
		}
		if attrs.IntentID == id {
			if found != "" {
				return "", fmt.Errorf("intent has multiple committed update bindings")
			}
			found = updateID
		}
	}
	return found, rows.Err()
}

func closeoutCommitInActiveGeneration(paths rt.Paths, updateID string) (bool, error) {
	st, err := store.OpenExisting(paths)
	if err != nil {
		return false, err
	}
	defer st.Close()
	active, err := st.ActiveGenerationID(context.Background())
	if err != nil {
		return false, err
	}
	var generation string
	if err := st.DB().QueryRowContext(context.Background(), `SELECT generation_id FROM updates WHERE id = ?`, updateID).Scan(&generation); err != nil {
		return false, err
	}
	return active == generation, nil
}

func publishCloseoutRepairLocked(paths rt.Paths, record closeoutRepairRecord) error {
	if err := validateCloseoutIntent(paths, record.Original); err != nil {
		return err
	}
	if err := validateCloseoutIntent(paths, record.Replacement); err != nil {
		return err
	}
	committed, err := closeoutCommittedUpdate(paths, record.Original.ID)
	if err != nil {
		return err
	}
	if committed != "" {
		return fmt.Errorf("repair is forbidden: original intent already committed")
	}
	prepared, err := prepareCloseoutInput(paths, record.Replacement.Workflow, record.Replacement.PayloadJSON, record.Replacement.DeltaSessionID, record.Replacement.VerificationOverride, record.Replacement.CommitRange)
	if err != nil {
		return err
	}
	if len(prepared.Missing) != 0 || !equalCloseoutPaths(prepared.ChangedPaths, record.Original.ChangedPaths) {
		return fmt.Errorf("repair does not preserve the complete original closeout scope")
	}
	if prepared.DeltaDigest != record.Replacement.DeltaDigest {
		return fmt.Errorf("delta session changed before repair publication")
	}
	original, err := loadCloseoutIntent(paths, record.Original.ID)
	if err == nil {
		want, _ := json.Marshal(record.Original)
		actual, _ := json.Marshal(original)
		if !bytes.Equal(want, actual) {
			return fmt.Errorf("original intent changed after repair was prepared")
		}
	} else if !os.IsNotExist(err) {
		return err
	}
	replacement, err := loadCloseoutIntent(paths, record.Replacement.ID)
	if err == nil {
		if replacement.InputDigest != record.Replacement.InputDigest {
			return fmt.Errorf("replacement intent digest changed")
		}
	} else if os.IsNotExist(err) {
		committed, err := closeoutCommittedUpdate(paths, record.Replacement.ID)
		if err != nil {
			return err
		}
		if committed == "" {
			if err := writeCloseoutIntent(closeoutIntentPath(paths, record.Replacement.ID), record.Replacement); err != nil {
				return err
			}
		}
	} else {
		return err
	}
	if closeoutRepairAfterReplacementHook != nil {
		if err := closeoutRepairAfterReplacementHook(); err != nil {
			return err
		}
	}
	if err := removeCloseoutIntent(paths, record.Original); err != nil {
		return err
	}
	if closeoutRepairAfterOriginalRemovalHook != nil {
		return closeoutRepairAfterOriginalRemovalHook()
	}
	return nil
}

func equalCloseoutPaths(left, right []string) bool {
	left, right = normalizedCloseoutPaths(left), normalizedCloseoutPaths(right)
	if len(left) != len(right) {
		return false
	}
	for i := range left {
		if left[i] != right[i] {
			return false
		}
	}
	return true
}

func reconcileCloseoutRepairsLocked(paths rt.Paths) error {
	entries, err := os.ReadDir(filepath.Join(paths.RuntimeDir, "closeout-intents"))
	if os.IsNotExist(err) {
		return nil
	}
	if err != nil {
		return err
	}
	for _, entry := range entries {
		id := strings.TrimSuffix(entry.Name(), ".json")
		if entry.IsDir() || !strings.HasSuffix(entry.Name(), ".json") || !validCloseoutIntentID(id) {
			continue
		}
		record, err := loadCloseoutRepair(paths, id)
		if os.IsNotExist(err) {
			continue
		}
		if err == nil {
			err = publishCloseoutRepairLocked(paths, record)
		}
		if err != nil {
			return &closeoutReplayError{IntentID: id, Err: err}
		}
	}
	return nil
}

func closeoutRecoveryFailure(stdout io.Writer, paths rt.Paths, id, category string, err error) int {
	env := NewEnvelope("blocked", "project cognition closeout recovery blocked")
	env.Data = map[string]any{"closeout_status": category, "intent_id": id, "error": err.Error(), "recommended_next_action": "inspect_closeout_intent"}
	if validCloseoutIntentID(id) {
		env.Data["recovery_argv"] = closeoutRecoveryArgv(paths, "inspect", id, "")
	}
	env.Blockers = []any{map[string]any{"category": category, "owner": "project_cognition", "detail": err.Error()}}
	return writeEnvelope(stdout, env)
}

func runCognitionCloseoutInspectCLI(args []string, stdout io.Writer) int {
	if containsHelpFlag(args) {
		env := NewEnvelope("ok", "project cognition closeout inspect usage")
		env.Data["usage"] = "specify-runtime cognition closeout inspect [--intent-id <id>] [--project-root <path>] --format json"
		return writeEnvelope(stdout, env)
	}
	paths, err := rt.ResolvePaths(optionValue(args, "--project-root", "."))
	if err != nil {
		return writeEnvelope(stdout, scriptDomainError("cognition", err))
	}
	id := optionValue(args, "--intent-id", "")
	if id == "" {
		entries, err := os.ReadDir(filepath.Join(paths.RuntimeDir, "closeout-intents"))
		if err != nil && !os.IsNotExist(err) {
			return closeoutRecoveryFailure(stdout, paths, "", "inspect_failed", err)
		}
		items := []any{}
		for _, entry := range entries {
			candidate := strings.TrimSuffix(entry.Name(), ".json")
			if entry.IsDir() || !strings.HasSuffix(entry.Name(), ".json") || !validCloseoutIntentID(candidate) {
				continue
			}
			item := map[string]any{"intent_id": candidate, "inspect_argv": closeoutRecoveryArgv(paths, "inspect", candidate, "")}
			intent, err := loadCloseoutIntent(paths, candidate)
			if err != nil {
				item["state"] = "invalid"
			} else {
				item["state"], item["scope"], item["workflow"] = intent.State, intent.Scope, intent.Workflow
			}
			items = append(items, item)
		}
		env := NewEnvelope("ok", "pending project cognition closeout intents")
		env.Data = map[string]any{"read_only": true, "items": items, "count": len(items)}
		return writeEnvelope(stdout, env)
	}
	if !validCloseoutIntentID(id) {
		return closeoutRecoveryFailure(stdout, paths, id, "invalid_intent_id", fmt.Errorf("an exact intent ID is required"))
	}
	record, recordErr := loadCloseoutRepair(paths, id)
	if recordErr == nil {
		if _, err := os.Stat(closeoutIntentPath(paths, id)); err == nil {
			env := NewEnvelope("ok", "closeout verification repair is durable and pending publication")
			env.Data = map[string]any{"read_only": true, "intent_id": id, "input_digest": record.Original.InputDigest, "scope": record.Original.Scope, "workflow": record.Original.Workflow, "state": record.Original.State, "closeout_status": "repair_pending", "repair_argv": closeoutRecoveryArgv(paths, "repair", id, record.Original.InputDigest), "recommended_next_action": "resume_closeout_repair"}
			return writeEnvelope(stdout, env)
		}
		env := NewEnvelope("ok", "closeout intent has a verification-bound replacement")
		env.Data = closeoutRepairResult(paths, record)
		env.Data["read_only"] = true
		return writeEnvelope(stdout, env)
	}
	if !os.IsNotExist(recordErr) {
		return closeoutRecoveryFailure(stdout, paths, id, "repair_record_invalid", recordErr)
	}
	intent, err := loadCloseoutIntent(paths, id)
	if err != nil {
		env := NewEnvelope("blocked", "closeout intent cannot be safely replayed or repaired")
		env.Data = map[string]any{"read_only": true, "intent_id": id, "closeout_status": "intent_integrity_blocked", "error": err.Error(), "recommended_next_action": "restore_intent_integrity_through_runtime_maintainer"}
		return writeEnvelope(stdout, env)
	}
	if intent.RepairsIntentID != "" {
		record, err := loadCloseoutRepair(paths, intent.RepairsIntentID)
		if err != nil || record.Replacement.InputDigest != intent.InputDigest {
			env := NewEnvelope("blocked", "repaired intent lineage must be restored before replay")
			env.Data = map[string]any{"read_only": true, "intent_id": id, "input_digest": intent.InputDigest, "closeout_status": "repair_lineage_blocked", "recommended_next_action": "restore_repair_record_through_runtime_maintainer"}
			return writeEnvelope(stdout, env)
		}
	}
	committed, err := closeoutCommittedUpdate(paths, id)
	if err != nil {
		return closeoutRecoveryFailure(stdout, paths, id, "commit_state_unknown", err)
	}
	data := map[string]any{"read_only": true, "intent_id": id, "input_digest": intent.InputDigest, "scope": intent.Scope, "workflow": intent.Workflow, "state": intent.State, "changed_paths": intent.ChangedPaths, "committed": committed != ""}
	if committed != "" {
		current, err := closeoutCommitInActiveGeneration(paths, committed)
		if err != nil {
			return closeoutRecoveryFailure(stdout, paths, id, "commit_state_unknown", err)
		}
		if !current {
			data["closeout_status"] = "committed_in_prior_generation"
			data["recommended_next_action"] = "reconcile_committed_intent_through_runtime_maintainer"
			env := NewEnvelope("ok", "intent already committed before the graph generation changed; replay is forbidden")
			env.Data = data
			return writeEnvelope(stdout, env)
		}
	}
	prepared, inputErr := prepareCloseoutInput(paths, intent.Workflow, intent.PayloadJSON, intent.DeltaSessionID, intent.VerificationOverride, intent.CommitRange)
	if inputErr == nil && len(prepared.Missing) == 0 {
		data["recommended_next_action"] = "replay_closeout_intent"
		data["replay_argv"] = closeoutRecoveryArgv(paths, "replay", id, intent.InputDigest)
	} else {
		issues := prepared.Missing
		if inputErr != nil {
			issues = []string{inputErr.Error()}
		}
		data["input_issues"] = issues
		data["recommended_next_action"] = "repair_input_contract_through_runtime_maintainer"
		if committed == "" && closeoutVerificationOnlyIssues(issues) {
			data["recommended_next_action"] = "supply_verified_evidence_and_repair_closeout"
			data["repair_argv"] = append(closeoutRecoveryArgv(paths, "repair", id, intent.InputDigest), "--verification-json", "-")
			data["verification_fields"] = []string{"command", "result", "artifact (optional)"}
		}
	}
	env := NewEnvelope("ok", "project cognition closeout recovery inspection")
	env.Data = data
	return writeEnvelope(stdout, env)
}

func closeoutVerificationOnlyIssues(issues []string) bool {
	if len(issues) == 0 {
		return false
	}
	for _, issue := range issues {
		if !strings.Contains(issue, "verification") {
			return false
		}
	}
	return true
}

func runCognitionCloseoutRepairCLI(args []string, stdout io.Writer) int {
	return runCognitionCloseoutRepairCLIWithInput(args, os.Stdin, stdout)
}

func runCognitionCloseoutRepairCLIWithInput(args []string, stdin io.Reader, stdout io.Writer) int {
	if containsHelpFlag(args) {
		env := NewEnvelope("ok", "project cognition closeout repair usage")
		env.Data["usage"] = "specify-runtime cognition closeout repair --intent-id <id> --expected-digest <sha256> [--verification-json -|<json>|@path] [--project-root <path>] --format json"
		return writeEnvelope(stdout, env)
	}
	paths, err := rt.ResolvePaths(optionValue(args, "--project-root", "."))
	if err != nil {
		return writeEnvelope(stdout, scriptDomainError("cognition", err))
	}
	id, expected := optionValue(args, "--intent-id", ""), optionValue(args, "--expected-digest", "")
	if !validCloseoutIntentID(id) || len(expected) != 64 {
		return closeoutRecoveryFailure(stdout, paths, id, "invalid_repair_binding", fmt.Errorf("exact --intent-id and --expected-digest are required"))
	}
	for _, forbidden := range []string{"--payload-json", "--delta-session", "--workflow", "--scope-dir", "--feature-dir", "--workspace", "--reason"} {
		if hasFlag(args, forbidden) {
			return closeoutRecoveryFailure(stdout, paths, id, "invalid_repair_input", fmt.Errorf("repair may replace verification only"))
		}
	}
	var verification update.VerificationEvidenceList
	if hasFlag(args, "--verification-json") {
		raw, err := resolveJSONInputBytesFrom(optionValue(args, "--verification-json", ""), paths.Root, "closeout repair", "--verification-json", stdin)
		if err != nil {
			return closeoutRecoveryFailure(stdout, paths, id, "invalid_repair_input", err)
		}
		var structured []update.VerificationEvidence
		if err := json.Unmarshal(raw, &structured); err != nil {
			return closeoutRecoveryFailure(stdout, paths, id, "invalid_repair_input", fmt.Errorf("verification repair requires an array of structured evidence"))
		}
		if err := update.ValidateVerificationEvidence(structured); err != nil {
			return closeoutRecoveryFailure(stdout, paths, id, "invalid_repair_input", err)
		}
		for i := range structured {
			structured[i].Command = strings.TrimSpace(structured[i].Command)
			structured[i].Result = strings.TrimSpace(structured[i].Result)
			structured[i].Artifact = strings.TrimSpace(structured[i].Artifact)
		}
		verification = structured
		if !closeoutHasPassingVerification(verification) {
			return closeoutRecoveryFailure(stdout, paths, id, "invalid_repair_input", fmt.Errorf("repair requires at least one actual passed verification result"))
		}
	}
	var record closeoutRepairRecord
	err = update.WithLockedRuntime(paths, func(_ *update.LockedRuntime) error {
		var err error
		record, err = loadCloseoutRepair(paths, id)
		if err == nil {
			if record.Original.InputDigest != expected {
				return fmt.Errorf("repair expected digest does not match original intent")
			}
			if verification != nil {
				a, _ := json.Marshal(record.Replacement.VerificationOverride)
				b, _ := json.Marshal(verification)
				if !bytes.Equal(a, b) {
					return fmt.Errorf("a different verification repair is already bound to this original intent")
				}
			}
			return publishCloseoutRepairLocked(paths, record)
		}
		if !os.IsNotExist(err) {
			return err
		}
		original, err := loadCloseoutIntent(paths, id)
		if err != nil {
			return err
		}
		if original.InputDigest != expected {
			return fmt.Errorf("repair expected digest does not match original intent")
		}
		if original.State != "pending_update" || original.UpdateID != "" || original.RepairsIntentID != "" {
			return fmt.Errorf("only an uncommitted original input may be repaired")
		}
		if verification == nil {
			return fmt.Errorf("--verification-json is required for a new repair; inspect then supply actual verification")
		}
		committed, err := closeoutCommittedUpdate(paths, id)
		if err != nil {
			return err
		}
		if committed != "" {
			return fmt.Errorf("repair is forbidden: original intent already committed")
		}
		before, beforeErr := prepareCloseoutInput(paths, original.Workflow, original.PayloadJSON, original.DeltaSessionID, nil, original.CommitRange)
		issues := before.Missing
		if beforeErr != nil {
			issues = []string{beforeErr.Error()}
		}
		if !closeoutVerificationOnlyIssues(issues) {
			return fmt.Errorf("intent does not have a verification-only defect; use its inspected recovery route")
		}
		replacement := closeoutReplacement(original, verification)
		prepared, err := prepareCloseoutInput(paths, replacement.Workflow, replacement.PayloadJSON, replacement.DeltaSessionID, verification, replacement.CommitRange)
		if err != nil {
			return err
		}
		if len(prepared.Missing) > 0 || !equalCloseoutPaths(prepared.ChangedPaths, original.ChangedPaths) {
			return fmt.Errorf("verification repair cannot change or omit the original scope")
		}
		if prepared.DeltaDigest != original.DeltaDigest {
			return fmt.Errorf("delta session changed during verification repair")
		}
		record = closeoutRepairRecord{Original: original, Replacement: replacement}
		if err := writeScriptJSONFile(closeoutRepairPath(paths, id), record); err != nil {
			return err
		}
		if closeoutRepairAfterJournalHook != nil {
			if err := closeoutRepairAfterJournalHook(); err != nil {
				return err
			}
		}
		return publishCloseoutRepairLocked(paths, record)
	})
	if err != nil {
		return closeoutRecoveryFailure(stdout, paths, id, "repair_blocked", err)
	}
	env := NewEnvelope("ok", "closeout verification repaired without changing project facts")
	env.Data = closeoutRepairResult(paths, record)
	return writeEnvelope(stdout, env)
}

func closeoutRepairResult(paths rt.Paths, record closeoutRepairRecord) map[string]any {
	data := map[string]any{"closeout_status": "intent_repaired", "intent_id": record.Original.ID, "replacement_intent_id": record.Replacement.ID, "replacement_input_digest": record.Replacement.InputDigest, "repair_record_ref": closeoutIntentRef(paths, closeoutRepairPath(paths, record.Original.ID)), "graph_mutation_performed": false, "recommended_next_action": "replay_closeout_intent"}
	if _, err := os.Stat(closeoutIntentPath(paths, record.Replacement.ID)); err == nil {
		committed, err := closeoutCommittedUpdate(paths, record.Replacement.ID)
		if err != nil {
			data["recommended_next_action"] = "inspect_commit_state_through_runtime_maintainer"
		} else if committed != "" {
			current, err := closeoutCommitInActiveGeneration(paths, committed)
			if err != nil || !current {
				data["recommended_next_action"] = "reconcile_committed_intent_through_runtime_maintainer"
			} else {
				data["replay_argv"] = closeoutRecoveryArgv(paths, "replay", record.Replacement.ID, record.Replacement.InputDigest)
			}
		} else {
			data["replay_argv"] = closeoutRecoveryArgv(paths, "replay", record.Replacement.ID, record.Replacement.InputDigest)
		}
	} else {
		data["recommended_next_action"] = "resume_owning_workflow"
	}
	return data
}

func replaySelectedCloseoutIntent(paths rt.Paths, args []string, stdout io.Writer) int {
	id := optionValue(args, "--intent-id", "")
	expected := optionValue(args, "--expected-digest", "")
	scopeDir := firstNonEmpty(optionValue(args, "--scope-dir", ""), optionValue(args, "--feature-dir", ""), optionValue(args, "--workspace", ""))
	if id != "" && (!validCloseoutIntentID(id) || len(expected) != 64) {
		return closeoutRecoveryFailure(stdout, paths, id, "invalid_replay_binding", fmt.Errorf("exact --intent-id and --expected-digest are required"))
	}
	releaseDo, err := doBeginCognitionReplay(paths, id, expected, scopeDir)
	if err != nil {
		return closeoutRecoveryFailure(stdout, paths, id, "replay_blocked", err)
	}
	defer releaseDo()
	var intent closeoutIntent
	var receipt *mutationCognitionReceipt
	var updateID string
	err = update.WithLockedRuntime(paths, func(runtime *update.LockedRuntime) error {
		var err error
		if id == "" {
			absScope, relScope, err := resolveCloseoutApplyScope(paths.Root, scopeDir)
			if err != nil {
				return err
			}
			receipt, err = loadMutationCognitionReceipt(absScope)
			if err != nil {
				return err
			}
			if receipt == nil || normalizeMutationCognitionState(receipt.ResultState) != "blocked" {
				return fmt.Errorf("closeout replay requires a blocked cognition-closeout.json for %s; use closeout inspect for exact intent recovery", relScope)
			}
			id, expected = receipt.IntentID, receipt.IntentDigest
			if !validCloseoutIntentID(id) {
				return fmt.Errorf("blocked closeout receipt does not bind a replay intent; use closeout inspect")
			}
		}
		intent, err = loadCloseoutIntent(paths, id)
		if err != nil {
			return err
		}
		if intent.InputDigest != expected {
			return fmt.Errorf("replay expected digest does not match selected intent")
		}
		absScope, relScope, err := resolveCloseoutApplyScope(paths.Root, intent.Scope)
		if err != nil {
			return err
		}
		if scopeDir != "" {
			_, requestedScope, err := resolveCloseoutApplyScope(paths.Root, scopeDir)
			if err != nil || requestedScope != relScope {
				return fmt.Errorf("replay scope does not match selected intent")
			}
		}
		if receipt != nil && (receipt.IntentRef != closeoutIntentRef(paths, closeoutIntentPath(paths, id)) || receipt.Scope != relScope) {
			return fmt.Errorf("blocked closeout receipt does not bind the selected replay intent")
		}
		if _, err := os.Stat(closeoutRepairPath(paths, id)); err == nil {
			return fmt.Errorf("original intent has a durable repair; inspect it and resume the replacement")
		}
		updateID, err = replayStoredCloseoutIntentLocked(runtime, paths, intent)
		if err != nil {
			return err
		}
		receipt, err = loadMutationCognitionReceipt(absScope)
		return err
	})
	if err != nil {
		return closeoutRecoveryFailure(stdout, paths, id, "replay_blocked", err)
	}
	if receipt == nil {
		return closeoutRecoveryFailure(stdout, paths, id, "replay_receipt_missing", errors.New("replay did not record a scope receipt"))
	}
	absScope, _, _ := resolveCloseoutApplyScope(paths.Root, intent.Scope)
	env := NewEnvelope("ok", "selected project cognition closeout replayed")
	env.Data = map[string]any{"closeout_status": "recorded", "intent_id": id, "workflow": intent.Workflow, "scope": intent.Scope, "update_id": updateID, "resumed_from_intent": true, "closeout_state": receipt.ResultState, "allowed_close": mutationCognitionReceiptAllowedClose(absScope, receipt)}
	return writeEnvelope(stdout, env)
}
