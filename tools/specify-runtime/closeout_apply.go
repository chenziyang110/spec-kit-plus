package main

import (
	"encoding/json"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"sort"
	"strings"

	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/delta"
	rt "github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/runtime"
	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/update"
	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/validation"
)

const closeoutStateScopeReady = "scope_ready"

func runCognitionCloseoutApplyCLI(args []string, stdout io.Writer) int {
	return runCognitionCloseoutApplyCLIWithInput(args, os.Stdin, stdout)
}

func runCognitionCloseoutApplyCLIWithInput(args []string, stdin io.Reader, stdout io.Writer) int {
	if hasFlag(args, "--help") || hasFlag(args, "-h") {
		env := NewEnvelope("ok", "project cognition mutation closeout apply usage")
		env.Data = map[string]any{
			"usage": "specify-runtime cognition closeout apply --workflow <sp-*> --scope-dir <path> (--payload-json <inline-json> | --payload-json @path | --payload-json - | --delta-session <id>) [--project-root <path>] --format json",
		}
		return writeEnvelope(stdout, env)
	}
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
	if hasPayload == hasDelta {
		return writeEnvelope(stdout, scriptDomainError("cognition", fmt.Errorf("closeout apply requires exactly one of --payload-json or --delta-session")))
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

	missingAgentFields, err := closeoutApplyPreflight(paths, workflow, payloadJSON, deltaSession)
	if err != nil {
		return writeEnvelope(stdout, scriptDomainError("cognition", err))
	}
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
	updatePayload, err := update.RunUpdate(paths, input)
	if err != nil {
		env := NewEnvelope("blocked", "project cognition closeout update failed")
		env.Data = map[string]any{
			"closeout_status":         "update_failed",
			"workflow":                workflow,
			"scope":                   relScope,
			"error":                   err.Error(),
			"recommended_next_action": "repair_update_or_mark_dirty",
		}
		return writeEnvelope(stdout, env)
	}

	result := map[string]any{
		"closeout_status":       "recorded",
		"workflow":              workflow,
		"scope":                 relScope,
		"update_id":             updatePayload.UpdateID,
		"result_state":          updatePayload.ResultState,
		"scope_result_state":    updatePayload.ScopeResultState,
		"global_freshness":      updatePayload.GlobalFreshness,
		"global_readiness":      updatePayload.GlobalReadiness,
		"global_debt_reasons":   updatePayload.GlobalDebtReasons,
		"scope_partial_reasons": updatePayload.ScopePartialReasons,
		"update":                updatePayload,
	}

	switch updatePayload.ResultState {
	case update.ResultReady, update.ResultNoOp:
		gate := validation.ValidateBuild(paths)
		result["validation"] = gate
		if err := update.RecordValidateBuildReceipt(paths, gate.Status, gate.Gate, gate.Readiness); err != nil {
			return closeoutApplyBlockedAfterUpdate(stdout, absScope, workflow, relScope, updatePayload, result, "validate_build_receipt_failed", err.Error())
		}
		if gate.Status != "ok" || gate.Readiness != rt.ReadyReadiness || !gate.CompletionAllowed {
			return closeoutApplyBlockedAfterUpdate(stdout, absScope, workflow, relScope, updatePayload, result, "validate_build_blocked", strings.Join(gate.Errors, "; "))
		}
		finalized, err := update.CompleteRefresh(paths, "workflow-closeout")
		if err != nil {
			return closeoutApplyBlockedAfterUpdate(stdout, absScope, workflow, relScope, updatePayload, result, "complete_refresh_failed", err.Error())
		}
		result["finalization"] = finalized
		state := normalizeMutationCognitionState(updatePayload.ResultState)
		receipt, err := recordMutationCognitionReceipt(absScope, workflow, relScope, state, closeoutApplyReceiptReason(state, updatePayload), updatePayload.UpdateID, closeoutApplyEvidence(updatePayload))
		if err != nil {
			return writeEnvelope(stdout, scriptDomainError("cognition", err))
		}
		result["receipt"] = receipt
		result["closeout_state"] = state
		result["allowed_close"] = receipt["allowed_close"]
		env := NewEnvelope("ok", "project cognition closeout updated, validated, finalized, and recorded")
		env.Data = result
		return writeEnvelope(stdout, env)
	case update.ResultPartialRefresh:
		state := "partial"
		if updatePayload.ScopeResultState == update.ResultReady || updatePayload.ScopeResultState == update.ResultNoOp {
			state = closeoutStateScopeReady
		}
		receipt, err := recordMutationCognitionReceipt(absScope, workflow, relScope, state, closeoutApplyReceiptReason(state, updatePayload), updatePayload.UpdateID, closeoutApplyEvidence(updatePayload))
		if err != nil {
			return writeEnvelope(stdout, scriptDomainError("cognition", err))
		}
		result["receipt"] = receipt
		result["closeout_state"] = state
		result["allowed_close"] = receipt["allowed_close"]
		if receipt["allowed_close"] == true {
			env := NewEnvelope("ok", "workflow-owned cognition scope recorded while project-wide debt remains visible")
			env.Data = result
			return writeEnvelope(stdout, env)
		}
		result["recommended_next_action"] = "repair_closeout_partial_and_retry"
		env := NewEnvelope("blocked", "project cognition partial closeout is not closeable")
		env.Data = result
		return writeEnvelope(stdout, env)
	default:
		return closeoutApplyBlockedAfterUpdate(stdout, absScope, workflow, relScope, updatePayload, result, "non_closeable_update_result", updatePayload.ResultState)
	}
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
	missing := []string{}
	if strings.TrimSpace(payloadJSON) != "" {
		var payload update.PayloadFileInput
		if err := json.Unmarshal([]byte(payloadJSON), &payload); err != nil {
			return nil, fmt.Errorf("--payload-json must be valid project cognition update JSON: %w", err)
		}
		if strings.TrimSpace(payload.Workflow) != "" {
			payloadWorkflow, err := normalizeMutationWorkflowID(payload.Workflow)
			if err != nil {
				return nil, err
			}
			if payloadWorkflow != workflow {
				return nil, fmt.Errorf("closeout apply workflow %s does not match payload workflow %s", workflow, payloadWorkflow)
			}
		}
		owned := normalizedCloseoutPaths(payload.Boundary.WorkflowOwnedPaths)
		if strings.TrimSpace(payload.Boundary.ScopeMode) != "explicit" {
			missing = append(missing, "boundary.scope_mode=explicit")
		}
		if len(owned) == 0 {
			missing = append(missing, "boundary.workflow_owned_paths")
		}
		changed := append([]string{}, payload.ChangedPaths...)
		changed = append(changed, payload.ScopePaths...)
		for _, change := range payload.PathChanges {
			changed = append(changed, change.Path)
			if strings.TrimSpace(change.OldPath) != "" {
				changed = append(changed, change.OldPath)
			}
		}
		changed = normalizedCloseoutPaths(changed)
		if len(changed) == 0 {
			missing = append(missing, "changed_paths")
		}
		if len(owned) > 0 {
			ownedSet := closeoutPathSet(owned)
			for _, path := range changed {
				if !ownedSet[path] {
					return nil, fmt.Errorf("payload path %s is outside boundary.workflow_owned_paths", path)
				}
			}
		}
		verification := append(update.VerificationEvidenceList{}, payload.Verification...)
		verification = append(verification, payload.VerificationEvidence...)
		if !closeoutHasPassingVerification(verification) {
			missing = append(missing, "verification[result=passed]")
		}
		return sortedUniqueCloseoutStrings(missing), nil
	}

	bundle, err := delta.Load(paths.RuntimeDir, strings.TrimSpace(deltaSession))
	if err != nil {
		return nil, err
	}
	if strings.TrimSpace(bundle.Session.OriginCommand) != "" {
		sessionWorkflow, err := normalizeMutationWorkflowID(bundle.Session.OriginCommand)
		if err != nil {
			return nil, fmt.Errorf("invalid delta session origin_command: %w", err)
		}
		if sessionWorkflow != workflow {
			return nil, fmt.Errorf("closeout apply workflow %s does not match delta workflow %s", workflow, sessionWorkflow)
		}
	}
	declaredPaths := []string{}
	pathChangeEndpoints := []string{}
	hasPassing := false
	for _, event := range bundle.Events {
		declaredPaths = append(declaredPaths, event.ChangedPaths...)
		for _, change := range event.PathChanges {
			pathChangeEndpoints = append(pathChangeEndpoints, change.Path)
			if strings.TrimSpace(change.OldPath) != "" {
				pathChangeEndpoints = append(pathChangeEndpoints, change.OldPath)
			}
		}
		for _, raw := range event.Verification {
			var evidence update.VerificationEvidence
			if json.Unmarshal([]byte(strings.TrimSpace(raw)), &evidence) == nil && strings.TrimSpace(evidence.Command) != "" && strings.TrimSpace(evidence.Result) == "passed" {
				hasPassing = true
			}
		}
	}
	declaredPaths = normalizedCloseoutPaths(declaredPaths)
	if len(declaredPaths) == 0 {
		missing = append(missing, "delta.workflow_owned_changed_paths")
	} else {
		declaredSet := closeoutPathSet(declaredPaths)
		for _, endpoint := range normalizedCloseoutPaths(pathChangeEndpoints) {
			if !declaredSet[endpoint] {
				return nil, fmt.Errorf("delta path change endpoint %s is outside declared workflow-owned changed paths", endpoint)
			}
		}
	}
	if !hasPassing {
		missing = append(missing, "delta.verification[result=passed]")
	}
	return sortedUniqueCloseoutStrings(missing), nil
}

func closeoutApplyBlockedAfterUpdate(stdout io.Writer, absScope string, workflow string, relScope string, payload update.UpdatePayload, result map[string]any, category string, detail string) int {
	reason := strings.TrimSpace(category + ": " + detail)
	receipt, receiptErr := recordMutationCognitionReceipt(absScope, workflow, relScope, "blocked", reason, payload.UpdateID, closeoutApplyEvidence(payload))
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
		return strings.Join(payload.PartialRefreshReasons, ", ")
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
	for _, value := range values {
		if strings.TrimSpace(value.Command) != "" && strings.TrimSpace(value.Result) == "passed" {
			return true
		}
	}
	return false
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
