package main

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"sort"
	"strings"

	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/delta"
	rt "github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/runtime"
	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/store"
	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/update"
	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/validation"
)

const closeoutStateScopeReady = "scope_ready"

var (
	closeoutApplyAfterIntentPersistHook        func(string) error
	closeoutApplyAfterUpdateHook               func(string) error
	closeoutApplyAfterScopeReceiptHook         func(string) error
	closeoutApplyBeforeCurrentUpdateHook       func(string) error
	closeoutApplyAfterReplayedScopeReceiptHook func(string) error
	closeoutApplyAfterPreflightHook            func() error
)

// Recheck inside the shared cognition lock at each consumption boundary. A
// source mutation racing verification also leaves native freshness debt; an
// already computed graph update must never publish an apparently fresh proof.
func requireCurrentCloseoutBindingLocked(runtime *update.LockedRuntime, paths rt.Paths, intent closeoutIntent) error {
	if err := requireCloseoutIntentCurrentBinding(paths, intent); err != nil {
		if intent.StrongBinding != nil {
			_, debtErr := runtime.MarkDirty(update.DirtyInput{Reason: "closeout-source-binding-changed", OriginCommand: intent.Workflow, OriginFeatureDir: intent.Scope, ScopePaths: intent.ChangedPaths})
			if debtErr != nil {
				return fmt.Errorf("%w; source freshness debt could not be recorded: %v", err, debtErr)
			}
		}
		return err
	}
	return nil
}

type closeoutIntentPendingError struct {
	intent    closeoutIntent
	intentRef string
	err       error
}

func (err *closeoutIntentPendingError) Error() string {
	return err.err.Error()
}

type closeoutStageError struct {
	category string
	detail   string
}

func (err *closeoutStageError) Error() string {
	return err.category + ": " + err.detail
}

func runCognitionCloseoutApplyCLI(args []string, stdout io.Writer) int {
	return runCognitionCloseoutApplyCLIWithInput(args, os.Stdin, stdout)
}

func runCognitionCloseoutApplyCLIWithInput(args []string, stdin io.Reader, stdout io.Writer) int {
	if hasFlag(args, "--help") || hasFlag(args, "-h") {
		env := NewEnvelope("ok", "project cognition mutation closeout apply usage")
		env.Data = map[string]any{
			"usage": "specify-runtime cognition closeout apply --workflow <sp-*> --scope-dir <path> (--payload-json <inline-json|@path|-> | --delta-session <id> [--registration-json <draft-json|@path|->]) [--project-root <path>] --format json",
		}
		return writeEnvelope(stdout, env)
	}
	verbose := hasFlag(args, "--verbose")
	workflowRaw := firstNonEmpty(optionValue(args, "--workflow", ""), optionValue(args, "--command", ""))
	workflow, err := normalizeMutationWorkflowID(workflowRaw)
	if err != nil {
		return writeEnvelope(stdout, scriptDomainError("cognition", err))
	}
	projectRoot := optionValue(args, "--project-root", ".")
	absRoot, err := filepath.Abs(projectRoot)
	if err != nil {
		return writeEnvelope(stdout, scriptDomainError("cognition", err))
	}
	paths, err := rt.ResolvePaths(absRoot)
	if err != nil {
		return writeEnvelope(stdout, scriptDomainError("cognition", err))
	}
	absRoot = paths.Root

	scopeDir := firstNonEmpty(optionValue(args, "--scope-dir", ""), optionValue(args, "--feature-dir", ""), optionValue(args, "--workspace", ""))
	absScope, relScope, err := resolveCloseoutApplyScope(absRoot, scopeDir)
	if err != nil {
		return writeEnvelope(stdout, scriptDomainError("cognition", err))
	}
	payloadSource := optionValue(args, "--payload-json", "")
	deltaSession := optionValue(args, "--delta-session", "")
	hasPayload := hasFlag(args, "--payload-json")
	hasDelta := strings.TrimSpace(deltaSession) != ""
	registrationSource := optionValue(args, "--registration-json", "")
	hasRegistration := hasFlag(args, "--registration-json")
	if hasPayload == hasDelta {
		return writeEnvelope(stdout, scriptDomainError("cognition", fmt.Errorf("closeout apply requires exactly one of --payload-json or --delta-session")))
	}
	if hasRegistration && hasPayload {
		return closeoutApplyInputRejected(stdout, workflow, relScope, fmt.Errorf("--registration-json requires delta mode; inline mode carries scoped_registration in its single payload JSON"))
	}
	payloadJSON := ""
	if hasPayload {
		raw, err := resolveJSONInputBytesFrom(payloadSource, absRoot, "closeout apply", "--payload-json", stdin)
		if err != nil {
			return closeoutApplyInputRejected(stdout, workflow, relScope, err)
		}
		if len(raw) == 0 {
			return closeoutApplyInputRejected(stdout, workflow, relScope, fmt.Errorf("closeout apply --payload-json must not be empty"))
		}
		payloadJSON = string(raw)
	}
	registrationPayloadJSON := payloadJSON
	if hasRegistration {
		raw, err := resolveJSONInputBytesFrom(registrationSource, absRoot, "closeout apply", "--registration-json", stdin)
		if err != nil {
			return closeoutApplyInputRejected(stdout, workflow, relScope, err)
		}
		if text := strings.TrimSpace(string(raw)); text == "" || text == "null" {
			return closeoutApplyInputRejected(stdout, workflow, relScope, fmt.Errorf("closeout apply --registration-json must not be empty"))
		}
		carrier, err := json.Marshal(map[string]json.RawMessage{"scoped_registration": raw})
		if err != nil {
			return closeoutApplyInputRejected(stdout, workflow, relScope, err)
		}
		registrationPayloadJSON = string(carrier)
	}

	prepared, err := prepareCloseoutInput(paths, workflow, payloadJSON, deltaSession, nil, optionValue(args, "--commit-range", ""))
	if err != nil {
		return closeoutApplyInputRejected(stdout, workflow, relScope, err)
	}
	missingAgentFields := prepared.Missing
	if len(missingAgentFields) > 0 {
		env := NewEnvelope("blocked", "project cognition closeout needs agent-owned evidence before mutation")
		env.Data = map[string]any{
			"closeout_status":         "needs_agent_input",
			"workflow":                workflow,
			"scope":                   relScope,
			"missing_agent_fields":    missingAgentFields,
			"mutation_performed":      false,
			"recommended_next_action": "fill_agent_fields_and_retry_closeout_apply",
		}
		env.Blockers = []any{map[string]any{
			"category": "agent_evidence_incomplete",
			"fields":   missingAgentFields,
		}}
		return writeEnvelope(stdout, env)
	}

	reason := strings.TrimSpace(optionValue(args, "--reason", "workflow-finalize"))
	input := update.UpdateInput{Workflow: workflow, Reason: reason}
	if strings.TrimSpace(payloadJSON) != "" {
		input.PayloadJSON = payloadJSON
	} else {
		input.DeltaSessionID = strings.TrimSpace(deltaSession)
		input.CommitRange = strings.TrimSpace(optionValue(args, "--commit-range", ""))
	}
	changedPaths := prepared.ChangedPaths
	doBinding, releaseDo, err := doBeginCognitionCloseout(paths, workflow, relScope, reason, payloadJSON, deltaSession, input.CommitRange, changedPaths, prepared.DeltaDigest)
	if err != nil {
		return closeoutApplyInputRejected(stdout, workflow, relScope, err)
	}
	defer releaseDo()
	var strongBinding *closeoutBinding
	if bindingID := strings.TrimSpace(optionValue(args, "--binding-id", "")); bindingID != "" {
		strongBinding, err = requireStrongCloseoutBinding(paths.Root, workflow, relScope, bindingID, "")
		if err != nil {
			return closeoutApplyInputRejected(stdout, workflow, relScope, err)
		}
		if !equalCloseoutPaths(strongBinding.OwnedDelta, changedPaths) {
			return closeoutApplyInputRejected(stdout, workflow, relScope, fmt.Errorf("payload paths differ from runtime-bound actual owned delta"))
		}
	}
	if closeoutApplyAfterPreflightHook != nil {
		if err := closeoutApplyAfterPreflightHook(); err != nil {
			return closeoutApplyInputRejected(stdout, workflow, relScope, err)
		}
	}
	registrationJSON, err := prepareCloseoutRegistration(paths, workflow, relScope, registrationPayloadJSON, strongBinding, doBinding, changedPaths)
	if err != nil {
		return closeoutApplyInputRejected(stdout, workflow, relScope, err)
	}
	var (
		updatePayload    update.UpdatePayload
		gate             validation.GatePayload
		finalized        rt.Status
		receipt          map[string]any
		closeoutState    string
		intent           closeoutIntent
		intentRef        string
		resumed          bool
		replayedIntents  []string
		completedReceipt *mutationCognitionReceipt
		completedStatus  rt.Status
	)
	replayedIntents = []string{}
	lockedErr := update.WithLockedRuntime(paths, func(runtime *update.LockedRuntime) error {
		var err error
		if strongBinding != nil {
			if err := requireCurrentCloseoutBindingLocked(runtime, paths, closeoutIntent{Workflow: workflow, Scope: relScope, ChangedPaths: changedPaths, StrongBinding: strongBinding}); err != nil {
				return err
			}
		}
		if err := reconcileCloseoutRepairsLocked(paths); err != nil {
			return err
		}
		intent, intentRef, resumed, err = ensureCloseoutIntentWithRegistration(paths, workflow, relScope, reason, payloadJSON, deltaSession, input.CommitRange, changedPaths, doBinding, strongBinding, registrationJSON, prepared.DeltaDigest)
		if err != nil {
			return err
		}
		if intent.State == "scope_receipt_recorded" {
			if intent.ScopedRegistrationJSON != "" {
				if err := requireCurrentCloseoutBindingLocked(runtime, paths, intent); err != nil {
					return err
				}
				if workflow == "sp-do" {
					if err := doCheckCognitionBinding(paths.Root, relScope, intent.DoBinding); err != nil {
						return err
					}
				}
				stored, err := loadMutationCognitionReceipt(absScope)
				if err != nil || stored == nil {
					return fmt.Errorf("completed closeout receipt is unavailable: %v", err)
				}
				if stored.IntentID != intent.ID || stored.IntentDigest != intent.InputDigest || stored.UpdateID != intent.UpdateID || stored.IntentRef != intentRef || stored.Workflow != workflow || stored.Scope != relScope || !equalCloseoutPaths(stored.ChangedPaths, intent.ChangedPaths) {
					return fmt.Errorf("completed closeout receipt differs from the exact input")
				}
				if allowed, reason := mutationCognitionReceiptGateReason(absScope, stored); !allowed {
					return fmt.Errorf("completed closeout is no longer closeable: %s", reason)
				}
				committed, err := closeoutCommittedUpdate(paths, intent.ID)
				if err != nil || committed == "" || committed != stored.UpdateID {
					return fmt.Errorf("completed closeout journal binding is unavailable or differs: %v", err)
				}
				if err := requireCompletedCloseoutRegistration(paths, intent); err != nil {
					return err
				}
				completedStatus, err = rt.ReadStatus(paths)
				if err != nil || completedStatus.LastUpdateID != intent.UpdateID {
					return fmt.Errorf("completed closeout parent is no longer the current update: %v", err)
				}
				pruned, err := pruneCompletedCloseoutIntent(paths, intent)
				if err != nil || !pruned {
					return fmt.Errorf("completed closeout cannot be guardedly pruned: %v", err)
				}
				completedReceipt = stored
				return nil
			}
			// Publication is already complete. Exact replay must prove that this
			// owner can be pruned; apply must not rewrite its completed scope proof.
			return &closeoutReplayError{IntentID: intent.ID, Err: fmt.Errorf("completed closeout intent requires exact replay for guarded pruning; use closeout inspect")}
		}
		if closeoutApplyAfterIntentPersistHook != nil {
			if err := closeoutApplyAfterIntentPersistHook(intent.ID); err != nil {
				return &closeoutIntentPendingError{intent: intent, intentRef: intentRef, err: err}
			}
		}
		pendingIntents, err := listCloseoutIntents(paths)
		if err != nil {
			return err
		}
		for _, pending := range pendingIntents {
			if pending.ID == intent.ID {
				continue
			}
			updateID, err := replayStoredCloseoutIntentLocked(runtime, paths, pending, doBinding)
			if err != nil {
				return &closeoutReplayError{IntentID: pending.ID, Err: err}
			}
			replayedIntents = append(replayedIntents, updateID)
		}
		if closeoutApplyBeforeCurrentUpdateHook != nil {
			if err := closeoutApplyBeforeCurrentUpdateHook(intent.ID); err != nil {
				return err
			}
		}
		input.CloseoutIntentID = intent.ID
		input.ExpectedDeltaDigest = intent.DeltaDigest
		if err := requireCurrentCloseoutBindingLocked(runtime, paths, intent); err != nil {
			return err
		}
		updatePayload, err = runtime.RunUpdate(input)
		if err != nil {
			return err
		}
		updatePayload.ResumedFromIntent = resumed
		intent.State = "pending_validation"
		intent.UpdateID = updatePayload.UpdateID
		intent.UpdateOutcome = updatePayload.ResultState
		intent.ChangedBasis = append([]string{}, updatePayload.LastRefreshChangedBasis...)
		if status, statusErr := rt.ReadStatus(paths); statusErr == nil {
			intent.ActiveGenerationID = status.ActiveGenerationID
		}
		if err := updateCloseoutIntent(paths, intent); err != nil {
			return err
		}
		if closeoutApplyAfterUpdateHook != nil {
			if err := closeoutApplyAfterUpdateHook(updatePayload.UpdateID); err != nil {
				return err
			}
		}
		if err := requireCurrentCloseoutBindingLocked(runtime, paths, intent); err != nil {
			return &closeoutStageError{category: "source_binding_changed_after_update", detail: err.Error()}
		}
		if _, err := applyCloseoutRegistrationLocked(runtime, paths, intent, updatePayload); err != nil {
			return &closeoutStageError{category: "scoped_registration_incomplete", detail: err.Error()}
		}
		if intent.StrongBinding != nil && (updatePayload.ResultState == update.ResultNoOp || updatePayload.ResultState == update.ResultReady) {
			if err := runtime.ResolveSourceBindingDebt(workflow, relScope, updatePayload.ChangedPaths); err != nil {
				return err
			}
		}

		switch updatePayload.ResultState {
		case update.ResultReady, update.ResultNoOp:
			gate = validation.ValidateBuild(paths)
			if err := runtime.RecordValidateBuildReceipt(gate.Status, gate.Gate, gate.Readiness); err != nil {
				return &closeoutStageError{category: "validate_build_receipt_failed", detail: err.Error()}
			}
			if gate.Status != "ok" || gate.Readiness != rt.ReadyReadiness || !gate.CompletionAllowed {
				return &closeoutStageError{category: "validate_build_blocked", detail: strings.Join(gate.Errors, "; ")}
			}
			intent.State = "receipt_recorded"
			if err := updateCloseoutIntent(paths, intent); err != nil {
				return err
			}
			if workflow == "sp-do" {
				if err := doCheckCognitionBinding(paths.Root, relScope, intent.DoBinding); err != nil {
					return &closeoutStageError{category: "do_source_changed_before_finalize", detail: err.Error()}
				}
			}
			if err := requireCurrentCloseoutBindingLocked(runtime, paths, intent); err != nil {
				return &closeoutStageError{category: "source_binding_changed_before_finalize", detail: err.Error()}
			}
			finalized, err = runtime.CompleteRefresh("workflow-closeout")
			if err != nil {
				return &closeoutStageError{category: "complete_refresh_failed", detail: err.Error()}
			}
			closeoutState = normalizeMutationCognitionState(updatePayload.ResultState)
			if err := requireCurrentCloseoutBindingLocked(runtime, paths, intent); err != nil {
				return err
			}
			receipt, err = recordMutationCognitionReceiptBound(absScope, workflow, relScope, closeoutState, closeoutApplyReceiptReason(closeoutState, updatePayload), updatePayload.UpdateID, closeoutApplyEvidence(updatePayload), updatePayload.ChangedPaths, intent.ID, intentRef, intent.InputDigest, intent.DoBinding)
			if err != nil {
				return err
			}
			if receipt["allowed_close"] != true {
				return &closeoutStageError{category: "mutation_receipt_not_closeable", detail: fmt.Sprint(receipt["blocked_reason"])}
			}
		case update.ResultPartialRefresh:
			if err := requireCurrentCloseoutBindingLocked(runtime, paths, intent); err != nil {
				return err
			}
			closeoutState = "partial"
			if updatePayload.ScopeResultState == update.ResultReady || updatePayload.ScopeResultState == update.ResultNoOp {
				closeoutState = closeoutStateScopeReady
			}
			receipt, err = recordMutationCognitionReceiptBound(absScope, workflow, relScope, closeoutState, closeoutApplyReceiptReason(closeoutState, updatePayload), updatePayload.UpdateID, closeoutApplyEvidence(updatePayload), updatePayload.ChangedPaths, intent.ID, intentRef, intent.InputDigest, intent.DoBinding)
			if err != nil {
				return err
			}
			if receipt["allowed_close"] != true {
				return &closeoutStageError{category: "partial_closeout_not_closeable", detail: fmt.Sprint(receipt["blocked_reason"])}
			}
		default:
			return &closeoutStageError{category: "non_closeable_update_result", detail: updatePayload.ResultState}
		}
		intent.State = "scope_receipt_recorded"
		if err := updateCloseoutIntent(paths, intent); err != nil {
			return err
		}
		if closeoutApplyAfterScopeReceiptHook != nil {
			if err := closeoutApplyAfterScopeReceiptHook(intent.ID); err != nil {
				return err
			}
		}
		if err := requireCurrentCloseoutBindingLocked(runtime, paths, intent); err != nil {
			return err
		}
		return removeCloseoutIntent(paths, intent)
	})

	if lockedErr != nil {
		var replayErr *closeoutReplayError
		if errors.As(lockedErr, &replayErr) {
			env := NewEnvelope("blocked", "an older closeout intent requires exact recovery")
			env.Data = map[string]any{"closeout_status": "intent_recovery_blocked", "workflow": workflow, "scope": relScope, "intent_id": intent.ID, "intent_ref": intentRef, "blocked_intent_id": replayErr.IntentID, "error": replayErr.Error(), "recommended_next_action": "inspect_closeout_intent", "recovery_argv": closeoutRecoveryArgv(paths, "inspect", replayErr.IntentID, "")}
			return writeEnvelope(stdout, env)
		}
		var pendingErr *closeoutIntentPendingError
		if errors.As(lockedErr, &pendingErr) {
			env := NewEnvelope("blocked", "project cognition closeout intent is durable and pending replay")
			env.Data = map[string]any{
				"closeout_status":         "closeout_intent_pending",
				"workflow":                workflow,
				"scope":                   relScope,
				"intent_ref":              pendingErr.intentRef,
				"intent_id":               pendingErr.intent.ID,
				"changed_paths":           pendingErr.intent.ChangedPaths,
				"recommended_next_action": "rerun_same_closeout",
			}
			return writeEnvelope(stdout, env)
		}
		var recoveryErr *update.PredecessorRecoveryError
		if errors.As(lockedErr, &recoveryErr) {
			return closeoutApplyPredecessorRecoveryBlocked(stdout, absScope, workflow, relScope, recoveryErr, intent, intentRef)
		}
		var stageErr *closeoutStageError
		if errors.As(lockedErr, &stageErr) && updatePayload.UpdateID != "" {
			result := closeoutApplyResult(workflow, relScope, updatePayload, resumed, intentRef, verbose)
			if verbose {
				result["validation"] = gate
			} else {
				result["validation_status"] = gate.Status
				result["validation_readiness"] = gate.Readiness
			}
			return closeoutApplyBlockedAfterUpdate(stdout, absScope, workflow, relScope, updatePayload, result, stageErr.category, stageErr.detail, intent, intentRef)
		}
		if intent.State == "scope_receipt_recorded" && intent.ScopedRegistrationJSON != "" {
			env := NewEnvelope("blocked", "completed project cognition closeout no longer proves the current work")
			env.Data = map[string]any{"closeout_status": "completed_receipt_revalidation_blocked", "workflow": workflow, "scope": relScope, "update_id": intent.UpdateID, "intent_id": intent.ID, "error": lockedErr.Error(), "allowed_close": false, "recommended_next_action": "verify_current_workflow_source_and_closeout"}
			return writeEnvelope(stdout, env)
		}
		env := NewEnvelope("blocked", "project cognition closeout update failed")
		if intent.ID == "" {
			return closeoutApplyInputRejected(stdout, workflow, relScope, lockedErr)
		}
		env.Data = map[string]any{
			"closeout_status":         "update_failed",
			"workflow":                workflow,
			"scope":                   relScope,
			"error":                   lockedErr.Error(),
			"intent_ref":              intentRef,
			"intent_id":               intent.ID,
			"recommended_next_action": "inspect_closeout_intent",
			"recovery_argv":           closeoutRecoveryArgv(paths, "inspect", intent.ID, ""),
		}
		return writeEnvelope(stdout, env)
	}

	if completedReceipt != nil {
		partialReasons, globalDebtReasons, scopePartialReasons := update.CloseoutReplayReasons(completedStatus)
		env := NewEnvelope("ok", "project cognition closeout was already recorded and remains current")
		env.Data = map[string]any{"closeout_status": "recorded", "replayed_completed": true, "workflow": workflow, "scope": relScope, "update_id": completedReceipt.UpdateID, "result_state": completedStatus.LastUpdateOutcome, "scope_result_state": completedStatus.LastUpdateScopeOutcome, "global_freshness": completedStatus.Freshness, "global_readiness": completedStatus.Readiness, "global_debt_reasons": globalDebtReasons, "scope_partial_reasons": scopePartialReasons, "partial_refresh_reasons": partialReasons, "closeout_state": completedReceipt.ResultState, "intent_id": intent.ID, "intent_ref": intentRef, "receipt": completedReceipt, "allowed_close": true, "resumed_from_intent": true, "changed_path_count": len(completedReceipt.ChangedPaths), "changed_paths": completedReceipt.ChangedPaths, "replayed_intents": replayedIntents}
		return writeEnvelope(stdout, env)
	}
	result := closeoutApplyResult(workflow, relScope, updatePayload, resumed, intentRef, verbose)
	result["replayed_intents"] = replayedIntents
	result["receipt"] = receipt
	result["closeout_state"] = closeoutState
	result["allowed_close"] = receipt["allowed_close"]
	if gate.Gate != "" && verbose {
		result["validation"] = gate
		result["finalization"] = finalized
	} else if gate.Gate != "" {
		result["validation_status"] = gate.Status
		result["validation_readiness"] = gate.Readiness
		result["finalized_update_id"] = finalized.LastFinalizedUpdateID
	}
	summary := "project cognition closeout updated and recorded"
	if updatePayload.ResultState == update.ResultReady || updatePayload.ResultState == update.ResultNoOp {
		summary = "project cognition closeout updated, validated, finalized, and recorded"
	}
	env := NewEnvelope("ok", summary)
	env.Data = result
	return writeEnvelope(stdout, env)
}

func replayStoredCloseoutIntentLocked(runtime *update.LockedRuntime, paths rt.Paths, intent closeoutIntent, lockedDoBinding *DoCognitionBinding) (string, error) {
	_, ownerScope, err := resolveCloseoutApplyScope(paths.Root, intent.Scope)
	if err != nil {
		return "", err
	}
	if err := doCheckCognitionScopeOwner(ownerScope, intent.Workflow); err != nil {
		return "", err
	}
	if intent.Workflow == "sp-do" {
		// The cognition lock cannot acquire Do in the opposite order. Only the
		// exact Do owner already serialized by apply or selected replay may drain
		// this intent; other workflows retain its recovery record unchanged.
		if lockedDoBinding == nil || intent.DoBinding == nil || lockedDoBinding.SessionID != intent.DoBinding.SessionID {
			return "", fmt.Errorf("pending Do cognition requires exact Do owner replay; use closeout inspect and its digest-bound replay")
		}
		if err := doCheckCognitionBinding(paths.Root, intent.Scope, intent.DoBinding); err != nil {
			return "", err
		}
	}
	if intent.RepairsIntentID != "" {
		record, err := loadCloseoutRepair(paths, intent.RepairsIntentID)
		if err != nil {
			return "", err
		}
		if record.Replacement.InputDigest != intent.InputDigest {
			return "", fmt.Errorf("repair record does not bind replay intent")
		}
		if err := publishCloseoutRepairLocked(paths, record); err != nil {
			return "", err
		}
	}
	pruned, err := pruneCompletedCloseoutIntent(paths, intent)
	if err != nil {
		return "", err
	}
	if pruned {
		return intent.UpdateID, nil
	}
	if intent.State == "scope_receipt_recorded" {
		// A failed completed-proof check is a refusal, not an interrupted update.
		// RunUpdate can reconstruct status from the journal, so allowing it here
		// would erase the very generation/identity/order mismatch being checked.
		return "", fmt.Errorf("completed closeout intent cannot be pruned: current scope receipt, generation, journal binding or completion order does not prove completion")
	}
	if err := requireCurrentCloseoutBindingLocked(runtime, paths, intent); err != nil {
		return "", fmt.Errorf("pending source proof stale; retain intent for audit and begin fresh verification before closeout recovery: %w", err)
	}
	prepared, err := prepareCloseoutInput(paths, intent.Workflow, intent.PayloadJSON, intent.DeltaSessionID, intent.VerificationOverride, intent.CommitRange)
	if err != nil {
		return "", err
	}
	if len(prepared.Missing) > 0 {
		return "", fmt.Errorf("closeout evidence incomplete: %s", strings.Join(prepared.Missing, ", "))
	}
	if prepared.DeltaDigest != intent.DeltaDigest || !equalCloseoutPaths(prepared.ChangedPaths, intent.ChangedPaths) {
		return "", fmt.Errorf("replay input no longer matches its bound scope or delta")
	}
	absScope, relScope, err := resolveCloseoutApplyScope(paths.Root, intent.Scope)
	if err != nil {
		return "", err
	}
	input := update.UpdateInput{
		Workflow:             intent.Workflow,
		Reason:               intent.Reason,
		PayloadJSON:          intent.PayloadJSON,
		DeltaSessionID:       intent.DeltaSessionID,
		CommitRange:          intent.CommitRange,
		CloseoutIntentID:     intent.ID,
		ExpectedDeltaDigest:  intent.DeltaDigest,
		VerificationOverride: intent.VerificationOverride,
	}
	payload, err := runtime.RunUpdate(input)
	if err != nil {
		return "", err
	}
	intent.State = "pending_validation"
	intent.UpdateID = payload.UpdateID
	intent.UpdateOutcome = payload.ResultState
	intent.ChangedBasis = append([]string{}, payload.LastRefreshChangedBasis...)
	if status, statusErr := rt.ReadStatus(paths); statusErr == nil {
		intent.ActiveGenerationID = status.ActiveGenerationID
	}
	if err := updateCloseoutIntent(paths, intent); err != nil {
		return "", err
	}
	if err := requireCurrentCloseoutBindingLocked(runtime, paths, intent); err != nil {
		return "", err
	}
	if _, err := applyCloseoutRegistrationLocked(runtime, paths, intent, payload); err != nil {
		return "", fmt.Errorf("scoped registration recovery incomplete: %w", err)
	}
	if intent.StrongBinding != nil && (payload.ResultState == update.ResultNoOp || payload.ResultState == update.ResultReady) {
		if err := runtime.ResolveSourceBindingDebt(intent.Workflow, intent.Scope, payload.ChangedPaths); err != nil {
			return "", err
		}
	}

	state := "partial"
	switch payload.ResultState {
	case update.ResultReady, update.ResultNoOp:
		gate := validation.ValidateBuild(paths)
		if err := runtime.RecordValidateBuildReceipt(gate.Status, gate.Gate, gate.Readiness); err != nil {
			return "", err
		}
		if gate.Status != "ok" || gate.Readiness != rt.ReadyReadiness || !gate.CompletionAllowed {
			return "", fmt.Errorf("validate-build blocked: %s", strings.Join(gate.Errors, "; "))
		}
		intent.State = "receipt_recorded"
		if err := updateCloseoutIntent(paths, intent); err != nil {
			return "", err
		}
		if intent.Workflow == "sp-do" {
			if err := doCheckCognitionBinding(paths.Root, relScope, intent.DoBinding); err != nil {
				return "", err
			}
		}
		if err := requireCurrentCloseoutBindingLocked(runtime, paths, intent); err != nil {
			return "", err
		}
		if _, err := runtime.CompleteRefresh("workflow-closeout-replay"); err != nil {
			return "", err
		}
		state = normalizeMutationCognitionState(payload.ResultState)
	case update.ResultPartialRefresh:
		if payload.ScopeResultState == update.ResultReady || payload.ScopeResultState == update.ResultNoOp {
			state = closeoutStateScopeReady
		}
	default:
		return "", fmt.Errorf("non-closeable replay result %s", payload.ResultState)
	}
	intentRef := closeoutIntentRef(paths, closeoutIntentPath(paths, intent.ID))
	if err := requireCurrentCloseoutBindingLocked(runtime, paths, intent); err != nil {
		return "", err
	}
	receipt, err := recordMutationCognitionReceiptBound(absScope, intent.Workflow, relScope, state, closeoutApplyReceiptReason(state, payload), payload.UpdateID, closeoutApplyEvidence(payload), payload.ChangedPaths, intent.ID, intentRef, intent.InputDigest, intent.DoBinding)
	if err != nil {
		return "", err
	}
	if receipt["allowed_close"] != true {
		// Another same-scope intent may still require recovery. This replay
		// publishes only its own completed update; the external scope gate and
		// returned allowed_close remain false until every pending owner is done.
		if receipt["blocked_reason"] != "pending_closeout_intent_requires_replay" {
			return "", fmt.Errorf("replayed mutation receipt is not closeable: %v", receipt["blocked_reason"])
		}
		recorded, err := loadMutationCognitionReceipt(absScope)
		if err != nil || recorded == nil || recorded.Workflow != intent.Workflow || !sameFilesystemPath(filepath.FromSlash(recorded.Scope), filepath.FromSlash(relScope)) || recorded.IntentID != intent.ID || recorded.IntentRef != intentRef || recorded.IntentDigest != intent.InputDigest || recorded.UpdateID != payload.UpdateID || normalizeMutationCognitionState(recorded.ResultState) != state {
			return "", fmt.Errorf("replayed mutation receipt does not bind this completed intent: %v", err)
		}
		if allowed, reason := mutationCognitionReceiptResultGateReason(absScope, recorded); !allowed {
			return "", fmt.Errorf("replayed mutation receipt result is not complete: %s", reason)
		}
	}
	intent.State = "scope_receipt_recorded"
	if err := updateCloseoutIntent(paths, intent); err != nil {
		return "", err
	}
	if closeoutApplyAfterReplayedScopeReceiptHook != nil {
		if err := closeoutApplyAfterReplayedScopeReceiptHook(intent.ID); err != nil {
			return "", err
		}
	}
	if err := removeCloseoutIntent(paths, intent); err != nil {
		return "", err
	}
	return payload.UpdateID, nil
}

func pruneCompletedCloseoutIntent(paths rt.Paths, intent closeoutIntent) (bool, error) {
	if (intent.State != "scope_receipt_recorded" && intent.State != "receipt_recorded") || intent.UpdateID == "" {
		return false, nil
	}
	absScope, _, err := resolveCloseoutApplyScope(paths.Root, intent.Scope)
	if err != nil {
		return false, err
	}
	receipt, err := loadMutationCognitionReceipt(absScope)
	intentRef := closeoutIntentRef(paths, closeoutIntentPath(paths, intent.ID))
	if err != nil || receipt == nil {
		return false, err
	}
	if receipt.UpdateID != intent.UpdateID || receipt.IntentID != intent.ID || receipt.IntentRef != intentRef || receipt.IntentDigest != intent.InputDigest {
		// A later, currently valid receipt can supersede this already published
		// scope receipt. Prove both runtime journal bindings before pruning the
		// old completed intent; never resubmit its no-longer-current update.
		if intent.State != "scope_receipt_recorded" || receipt.Workflow != intent.Workflow || !sameFilesystemPath(filepath.FromSlash(receipt.Scope), filepath.FromSlash(intent.Scope)) || !validCloseoutIntentID(receipt.IntentID) || !isLowerHexSHA256(receipt.IntentDigest) || receipt.IntentID != "intent-"+receipt.IntentDigest[:24] || receipt.IntentRef != closeoutIntentRef(paths, closeoutIntentPath(paths, receipt.IntentID)) {
			return false, nil
		}
		oldCommitted, err := closeoutCommittedUpdate(paths, intent.ID)
		if err != nil {
			return false, err
		}
		newCommitted, err := closeoutCommittedUpdate(paths, receipt.IntentID)
		if err != nil {
			return false, err
		}
		if oldCommitted != intent.UpdateID || newCommitted == "" || newCommitted != receipt.UpdateID || newCommitted == oldCommitted {
			return false, nil
		}
		if allowed, _ := mutationCognitionReceiptResultGateReason(absScope, receipt); !allowed {
			return false, nil
		}
	}
	state := normalizeMutationCognitionState(receipt.ResultState)
	if state != "ready" && state != "no_op" && state != "scope_ready" && state != "partial" {
		return false, nil
	}
	status, err := rt.ReadStatus(paths)
	if err != nil {
		return false, err
	}
	st, err := store.OpenExisting(paths)
	if err != nil {
		return false, err
	}
	defer st.Close()
	generationID, err := st.ActiveGenerationID(context.Background())
	if err != nil {
		return false, err
	}
	comparisonUpdateID := status.LastFinalizedUpdateID
	if state == "scope_ready" || state == "partial" {
		comparisonUpdateID = status.LastUpdateID
	}
	if comparisonUpdateID == "" {
		return false, nil
	}
	var intentCompletedAt, comparisonCompletedAt string
	if err := st.DB().QueryRowContext(context.Background(), `SELECT completed_at FROM updates WHERE generation_id = ? AND id = ?`, generationID, intent.UpdateID).Scan(&intentCompletedAt); err != nil {
		return false, nil
	}
	if err := st.DB().QueryRowContext(context.Background(), `SELECT completed_at FROM updates WHERE generation_id = ? AND id = ?`, generationID, comparisonUpdateID).Scan(&comparisonCompletedAt); err != nil {
		return false, nil
	}
	if comparisonCompletedAt < intentCompletedAt {
		return false, nil
	}
	if err := removeCloseoutIntent(paths, intent); err != nil {
		return false, err
	}
	return true, nil
}

func closeoutApplyResult(workflow string, scope string, payload update.UpdatePayload, resumed bool, intentRef string, verbose bool) map[string]any {
	changedPaths := normalizedCloseoutPaths(payload.ChangedPaths)
	compactPaths := changedPaths
	if len(compactPaths) > 20 {
		compactPaths = compactPaths[:20]
	}
	result := map[string]any{
		"closeout_status":       "recorded",
		"workflow":              workflow,
		"scope":                 scope,
		"update_id":             payload.UpdateID,
		"result_state":          payload.ResultState,
		"scope_result_state":    payload.ScopeResultState,
		"global_freshness":      payload.GlobalFreshness,
		"global_readiness":      payload.GlobalReadiness,
		"global_debt_reasons":   payload.GlobalDebtReasons,
		"scope_partial_reasons": payload.ScopePartialReasons,
		"changed_path_count":    len(changedPaths),
		"changed_paths":         compactPaths,
		"resumed_from_intent":   resumed,
		"intent_ref":            intentRef,
	}
	if verbose {
		result["update"] = payload
	}
	if payload.PredecessorRecovery != nil {
		result["predecessor_recovery"] = payload.PredecessorRecovery
	}
	if payload.StatusRecovery != nil {
		result["status_recovery"] = payload.StatusRecovery
	}
	return result
}

func closeoutApplyPredecessorRecoveryBlocked(stdout io.Writer, absScope string, workflow string, relScope string, recoveryErr *update.PredecessorRecoveryError, intent closeoutIntent, intentRef string) int {
	changedPaths := intent.ChangedPaths
	recovery := recoveryErr.Recovery
	reason := recoveryErr.Error()
	evidence := []string{
		"predecessor_update_id=" + recovery.UpdateID,
		"predecessor_update_outcome=" + recovery.UpdateOutcome,
		"recovery_action=" + recovery.RecommendedNextAction,
	}
	receipt, receiptErr := recordMutationCognitionReceiptBound(absScope, workflow, relScope, "blocked", reason, "", evidence, changedPaths, intent.ID, intentRef, intent.InputDigest, intent.DoBinding)
	data := map[string]any{
		"closeout_status":             "predecessor_recovery_blocked",
		"workflow":                    workflow,
		"scope":                       relScope,
		"closeout_state":              "predecessor_recovery_blocked",
		"predecessor_recovery":        recovery,
		"mutation_performed":          false,
		"current_mutation_accounting": "recorded",
		"changed_paths":               changedPaths,
		"intent_ref":                  intentRef,
		"intent_id":                   intent.ID,
		"recommended_next_action":     recovery.RecommendedNextAction,
	}
	if receiptErr != nil {
		data["current_mutation_accounting"] = "failed"
		data["receipt_error"] = receiptErr.Error()
	} else {
		data["receipt"] = receipt
		data["allowed_close"] = receipt["allowed_close"]
	}
	env := NewEnvelope("blocked", "project cognition predecessor recovery blocked; current mutation scope recorded without finalizing the graph")
	env.Data = data
	env.Blockers = []any{map[string]any{
		"category": "predecessor_recovery_blocked",
		"owner":    "project_cognition",
		"detail":   reason,
	}}
	return writeEnvelope(stdout, env)
}

func closeoutApplyInputPaths(paths rt.Paths, payloadJSON string, deltaSession string) ([]string, error) {
	values := []string{}
	if strings.TrimSpace(payloadJSON) != "" {
		var payload update.PayloadFileInput
		if err := json.Unmarshal([]byte(payloadJSON), &payload); err != nil {
			return nil, fmt.Errorf("parse current closeout payload for mutation accounting: %w", err)
		}
		values = append(values, payload.ChangedPaths...)
		values = append(values, payload.ScopePaths...)
		for _, change := range payload.PathChanges {
			values = append(values, change.Path, change.OldPath)
		}
		return normalizedCloseoutPaths(values), nil
	}
	bundle, err := delta.Load(paths.RuntimeDir, strings.TrimSpace(deltaSession))
	if err != nil {
		return nil, err
	}
	for _, event := range bundle.Events {
		values = append(values, event.ChangedPaths...)
		for _, change := range event.PathChanges {
			values = append(values, change.Path, change.OldPath)
		}
	}
	return normalizedCloseoutPaths(values), nil
}

func closeoutApplyInputRejected(stdout io.Writer, workflow string, scope string, err error) int {
	env := NewEnvelope("blocked", "project cognition closeout input rejected before mutation")
	env.Data = map[string]any{
		"closeout_status":         "input_rejected",
		"workflow":                workflow,
		"scope":                   scope,
		"error":                   err.Error(),
		"mutation_performed":      false,
		"recommended_next_action": "provide_bounded_closeout_input",
	}
	env.Blockers = []any{map[string]any{
		"category": "invalid_or_oversized_closeout_input",
		"detail":   err.Error(),
	}}
	return writeEnvelope(stdout, env)
}

func closeoutApplyPreflight(paths rt.Paths, workflow string, payloadJSON string, deltaSession string) ([]string, error) {
	prepared, err := prepareCloseoutInput(paths, workflow, payloadJSON, deltaSession, nil)
	return prepared.Missing, err
}

func closeoutApplyBlockedAfterUpdate(stdout io.Writer, absScope string, workflow string, relScope string, payload update.UpdatePayload, result map[string]any, category string, detail string, intent closeoutIntent, intentRef string) int {
	reason := strings.TrimSpace(category + ": " + detail)
	receipt, receiptErr := recordMutationCognitionReceiptBound(absScope, workflow, relScope, "blocked", reason, payload.UpdateID, closeoutApplyEvidence(payload), intent.ChangedPaths, intent.ID, intentRef, intent.InputDigest, intent.DoBinding)
	if receiptErr == nil {
		result["receipt"] = receipt
	}
	result["closeout_state"] = "blocked"
	result["allowed_close"] = false
	result["blocker_category"] = category
	result["blocker_detail"] = strings.TrimSpace(detail)
	result["recommended_next_action"] = "repair_closeout_and_retry"
	env := NewEnvelope("blocked", "project cognition closeout stopped after recording truthful update state")
	env.Data = result
	return writeEnvelope(stdout, env)
}

func closeoutApplyReceiptReason(state string, payload update.UpdatePayload) string {
	switch state {
	case "ready":
		return "workflow-owned project cognition scope updated and receipt-bound finalization completed"
	case "no_op":
		return "workflow-owned project cognition scope produced no graph mutation and receipt-bound finalization completed"
	case closeoutStateScopeReady:
		reasons := payload.GlobalDebtReasons
		if len(reasons) == 0 {
			reasons = payload.PartialRefreshReasons
		}
		return "workflow scope ready; project-wide cognition debt remains: " + strings.Join(reasons, ", ")
	default:
		if reason := strings.Join(payload.PartialRefreshReasons, ", "); strings.TrimSpace(reason) != "" {
			return reason
		}
		return fmt.Sprintf("workflow cognition remains incomplete: result_state=%s, scope_result_state=%s; no detailed reason was recorded", payload.ResultState, payload.ScopeResultState)
	}
}

func closeoutApplyEvidence(payload update.UpdatePayload) []string {
	values := []string{
		"scope_result_state=" + payload.ScopeResultState,
		"global_result_state=" + payload.ResultState,
		"global_freshness=" + payload.GlobalFreshness,
	}
	for _, reason := range payload.PartialRefreshReasons {
		values = append(values, "partial_refresh_reason="+reason)
	}
	return sortedUniqueCloseoutStrings(values)
}

func closeoutHasPassingVerification(values update.VerificationEvidenceList) bool {
	passed := false
	for _, value := range values {
		if strings.TrimSpace(value.Result) == "failed" {
			return false
		}
		if strings.TrimSpace(value.Command) != "" && strings.TrimSpace(value.Result) == "passed" {
			passed = true
		}
	}
	return passed
}

func resolveCloseoutApplyScope(root string, scopeDir string) (string, string, error) {
	if strings.TrimSpace(scopeDir) == "" {
		return "", "", fmt.Errorf("closeout apply requires --scope-dir or --feature-dir")
	}
	absScope := scopeDir
	if !filepath.IsAbs(absScope) {
		absScope = filepath.Join(root, filepath.FromSlash(absScope))
	}
	absScope = filepath.Clean(absScope)
	rel, err := filepath.Rel(root, absScope)
	if err != nil {
		return "", "", err
	}
	relSlash := filepath.ToSlash(rel)
	if relSlash == ".." || strings.HasPrefix(relSlash, "../") {
		return "", "", fmt.Errorf("closeout scope must stay within project root")
	}
	return absScope, relSlash, nil
}

func normalizedCloseoutPaths(values []string) []string {
	out := []string{}
	seen := map[string]bool{}
	for _, value := range values {
		value = filepath.ToSlash(strings.TrimSpace(value))
		for strings.HasPrefix(value, "./") {
			value = strings.TrimPrefix(value, "./")
		}
		if value == "" || seen[value] {
			continue
		}
		seen[value] = true
		out = append(out, value)
	}
	sort.Strings(out)
	return out
}

func closeoutPathSet(values []string) map[string]bool {
	out := make(map[string]bool, len(values))
	for _, value := range values {
		out[value] = true
	}
	return out
}

func sortedUniqueCloseoutStrings(values []string) []string {
	out := []string{}
	seen := map[string]bool{}
	for _, value := range values {
		value = strings.TrimSpace(value)
		if value == "" || seen[value] {
			continue
		}
		seen[value] = true
		out = append(out, value)
	}
	sort.Strings(out)
	return out
}
