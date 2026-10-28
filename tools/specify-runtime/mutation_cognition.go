package main

import (
	"encoding/json"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strings"

	rt "github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/runtime"
	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/workflowregistry"
)

const (
	mutationCognitionReceiptFileName = "cognition-closeout.json"
	mutationCognitionReceiptVersion  = 1
)

// Terminal states that allow a mutation workflow to claim completion.
var mutationCognitionAllowedStates = map[string]bool{
	"ready":       true,
	"no_op":       true,
	"scope_ready": true,
	"mark-dirty":  true,
	"partial":     true,
}

// Feature stages that must leave a project-cognition mutation receipt before complete-stage.
var mutationCognitionFeatureStages = map[string]string{
	"implement": "sp-implement",
	"review":    "sp-review",
}

type mutationCognitionReceipt struct {
	Version       int                 `json:"version"`
	Workflow      string              `json:"workflow"`
	Scope         string              `json:"scope,omitempty"` // feature rel, quick workspace, or project
	ResultState   string              `json:"result_state"`
	Reason        string              `json:"reason,omitempty"`
	Evidence      []string            `json:"evidence,omitempty"`
	ChangedPaths  []string            `json:"changed_paths,omitempty"`
	IntentID      string              `json:"intent_id,omitempty"`
	IntentRef     string              `json:"intent_ref,omitempty"`
	IntentDigest  string              `json:"intent_digest,omitempty"`
	UpdateID      string              `json:"update_id,omitempty"`
	RecordedAt    string              `json:"recorded_at"`
	DoBinding     *DoCognitionBinding `json:"do_binding,omitempty"`
	StrongBinding *closeoutBinding    `json:"strong_binding,omitempty"`
}

func normalizeMutationCognitionState(raw string) string {
	state := strings.ToLower(strings.TrimSpace(raw))
	switch state {
	case "partial_refresh":
		return "partial"
	case "dirty", "mark_dirty":
		return "mark-dirty"
	case "noop", "no-op":
		return "no_op"
	default:
		return state
	}
}

func normalizeMutationWorkflowID(raw string) (string, error) {
	canonical, err := workflowregistry.CanonicalCloseoutWorkflow(raw)
	if err != nil {
		// Accept already-canonical sp-* mutation IDs and short names that map.
		name := strings.ToLower(strings.TrimSpace(raw))
		name = strings.TrimPrefix(name, "/")
		name = strings.ReplaceAll(name, ".", "-")
		if !strings.HasPrefix(name, "sp-") {
			name = "sp-" + strings.TrimPrefix(name, "sp-")
		}
		switch name {
		case "sp-implement", "sp-implement-teams":
			return "sp-implement", nil
		case "sp-quick", "sp-fast", "sp-debug", "sp-review", "sp-map-update":
			return name, nil
		default:
			return "", fmt.Errorf("workflow %q does not own project cognition mutation closeout", raw)
		}
	}
	return canonical, nil
}

func mutationCognitionReceiptPath(scopeDir string) string {
	return filepath.Join(scopeDir, mutationCognitionReceiptFileName)
}

func writeMutationCognitionReceipt(scopeDir string, receipt mutationCognitionReceipt) (string, error) {
	if err := os.MkdirAll(scopeDir, 0o755); err != nil {
		return "", err
	}
	if receipt.Evidence == nil {
		receipt.Evidence = []string{}
	}
	raw, err := json.MarshalIndent(receipt, "", "  ")
	if err != nil {
		return "", err
	}
	path := mutationCognitionReceiptPath(scopeDir)
	if err := writeScriptTextFile(path, string(raw)+"\n"); err != nil {
		return "", err
	}
	return path, nil
}

func loadMutationCognitionReceipt(scopeDir string) (*mutationCognitionReceipt, error) {
	path := mutationCognitionReceiptPath(scopeDir)
	raw, err := os.ReadFile(path)
	if os.IsNotExist(err) {
		return nil, nil
	}
	if err != nil {
		return nil, err
	}
	var receipt mutationCognitionReceipt
	if err := json.Unmarshal(raw, &receipt); err != nil {
		return nil, fmt.Errorf("%s is invalid: %w", mutationCognitionReceiptFileName, err)
	}
	return &receipt, nil
}

func recordMutationCognitionReceipt(scopeDir, workflow, scopeLabel, resultState, reason, updateID string, evidence []string) (map[string]any, error) {
	return recordMutationCognitionReceiptWithPaths(scopeDir, workflow, scopeLabel, resultState, reason, updateID, evidence, nil)
}

func recordMutationCognitionReceiptWithPaths(scopeDir, workflow, scopeLabel, resultState, reason, updateID string, evidence []string, changedPaths []string) (map[string]any, error) {
	canonical, err := normalizeMutationWorkflowID(workflow)
	if err != nil {
		return nil, err
	}
	paths, err := rt.ResolvePaths(scopeDir)
	if err != nil {
		return nil, err
	}
	// Keep Do's operation lock before cognition's update lock. Bound apply
	// already holds both and bypasses this standalone compatibility wrapper.
	if canonical == "sp-do" {
		id, err := doCognitionScope(paths.Root, scopeLabel)
		if err != nil {
			return nil, err
		}
		release, err := doSessionLock(paths.Root, id)
		if err != nil {
			return nil, err
		}
		defer release()
	}
	release, err := rt.AcquireUpdateLock(paths)
	if err != nil {
		return nil, err
	}
	defer release()
	intent, err := pendingMutationCloseoutIntent(scopeDir, canonical)
	if err != nil {
		return nil, fmt.Errorf("standalone cognition receipt cannot establish absence of a durable intent: %w; %s", err, mutationCognitionRecoveryText(scopeDir, canonical, changedPaths))
	}
	if intent != nil {
		return nil, fmt.Errorf("standalone cognition receipt cannot replace durable intent %s; %s", intent.ID, mutationCognitionRecoveryText(scopeDir, canonical, changedPaths))
	}
	return recordMutationCognitionReceiptBound(scopeDir, canonical, scopeLabel, resultState, reason, updateID, evidence, changedPaths, "", "", "")
}

func recordMutationCognitionReceiptBound(scopeDir, workflow, scopeLabel, resultState, reason, updateID string, evidence []string, changedPaths []string, intentID string, intentRef string, intentDigest string, doBindings ...*DoCognitionBinding) (map[string]any, error) {
	canonical, err := normalizeMutationWorkflowID(workflow)
	if err != nil {
		return nil, err
	}
	state := normalizeMutationCognitionState(resultState)
	if !mutationCognitionAllowedStates[state] && state != "needs_rebuild" && state != "blocked" {
		return nil, fmt.Errorf("--result-state must be ready|no_op|scope_ready|mark-dirty|partial|needs_rebuild|blocked (got %q)", resultState)
	}
	if (state == "mark-dirty" || state == "partial" || state == "scope_ready" || state == "needs_rebuild" || state == "blocked" || state == "no_op") && strings.TrimSpace(reason) == "" {
		return nil, fmt.Errorf("result_state=%s requires --reason (greenfield/empty graph, no_op, or dirty fallback must be explicit so project cognition keeps improving)", state)
	}
	receipt := mutationCognitionReceipt{
		Version:      mutationCognitionReceiptVersion,
		Workflow:     canonical,
		Scope:        scopeLabel,
		ResultState:  state,
		Reason:       strings.TrimSpace(reason),
		Evidence:     evidence,
		ChangedPaths: normalizedCloseoutPaths(changedPaths),
		IntentID:     strings.TrimSpace(intentID),
		IntentRef:    strings.TrimSpace(intentRef),
		IntentDigest: strings.TrimSpace(intentDigest),
		UpdateID:     strings.TrimSpace(updateID),
		RecordedAt:   nowUTCString(),
	}
	if err := doPrepareCognitionReceipt(scopeDir, &receipt, doBindings); err != nil {
		return nil, err
	}
	if intentID != "" {
		paths, err := rt.ResolvePaths(scopeDir)
		if err != nil {
			return nil, err
		}
		intent, err := loadCloseoutIntent(paths, intentID)
		if err != nil {
			return nil, err
		}
		receipt.StrongBinding = intent.StrongBinding
	}
	path, err := writeMutationCognitionReceipt(scopeDir, receipt)
	if err != nil {
		return nil, err
	}
	payload := map[string]any{
		"receipt_path":  filepath.ToSlash(path),
		"workflow":      canonical,
		"scope":         scopeLabel,
		"result_state":  state,
		"reason":        receipt.Reason,
		"evidence":      receipt.Evidence,
		"changed_paths": receipt.ChangedPaths,
		"intent_id":     receipt.IntentID,
		"intent_ref":    receipt.IntentRef,
		"intent_digest": receipt.IntentDigest,
		"update_id":     receipt.UpdateID,
		"recorded_at":   receipt.RecordedAt,
		"allowed_close": mutationCognitionReceiptAllowedClose(scopeDir, &receipt),
		"strong_proof":  receipt.StrongBinding != nil || receipt.Workflow == "sp-do" && receipt.DoBinding != nil,
		"policy":        "Every source-changing mutation workflow must refresh project cognition so a greenfield project continuously gains path_index, routes, and claims. Prefer result_state=ready after update+validate-build+complete-refresh; use mark-dirty/no_op only with an explicit reason.",
	}
	if allowed, reason := mutationCognitionReceiptGateReason(scopeDir, &receipt); !allowed && reason != "" {
		payload["blocked_reason"] = reason
	}
	if state == "mark-dirty" {
		payload["warning"] = "mark-dirty is a temporary unclean closeout; the next source-changing workflow must attempt a real cognition update so the graph keeps growing."
	}
	return payload, nil
}

func mutationCognitionStatus(scopeDir string) map[string]any {
	out := map[string]any{
		"status":        "missing",
		"result_state":  "",
		"reason":        "",
		"receipt_path":  "",
		"allowed_close": false,
		"workflow":      "",
	}
	receipt, err := loadMutationCognitionReceipt(scopeDir)
	if err != nil {
		out["status"] = "invalid"
		out["error"] = err.Error()
		return out
	}
	if receipt == nil {
		return out
	}
	out["status"] = "recorded"
	out["result_state"] = receipt.ResultState
	out["reason"] = receipt.Reason
	out["workflow"] = receipt.Workflow
	out["receipt_path"] = filepath.ToSlash(mutationCognitionReceiptPath(scopeDir))
	allowed, reason := mutationCognitionReceiptGateReason(scopeDir, receipt)
	out["allowed_close"] = allowed
	if reason != "" {
		out["blocked_reason"] = reason
	}
	return out
}

func mutationCognitionReceiptAllowedClose(scopeDir string, receipt *mutationCognitionReceipt) bool {
	allowed, _ := mutationCognitionReceiptGateReason(scopeDir, receipt)
	return allowed
}

func mutationCognitionReceiptGateReason(scopeDir string, receipt *mutationCognitionReceipt) (bool, string) {
	if receipt == nil {
		return false, "missing_receipt"
	}
	state := normalizeMutationCognitionState(receipt.ResultState)
	if !mutationCognitionAllowedStates[state] {
		return false, "non_terminal_result_state"
	}
	bound, err := matchingMutationCloseoutIntent(scopeDir, receipt)
	if err != nil {
		return false, "closeout_intent_integrity_requires_inspect"
	}
	// A valid bound intent exempts only its own atomic receipt publication.
	// It must not hide another same-scope intent persisted after that receipt.
	intent, committed, err := pendingIntentForCommittedMutationReceipt(scopeDir, receipt)
	if !committed && err == nil {
		if bound {
			intent, err = pendingMutationCloseoutIntent(scopeDir, receipt.Workflow, receipt.IntentID)
		} else {
			intent, err = pendingMutationCloseoutIntent(scopeDir, receipt.Workflow)
		}
	}
	if err != nil {
		return false, "closeout_intent_integrity_requires_inspect"
	}
	if intent != nil {
		return false, "pending_closeout_intent_requires_replay"
	}
	return mutationCognitionReceiptResultGateReason(scopeDir, receipt)
}

// Validate the recorded update result independently of whether other intents
// still own this scope. Locked replay uses this proof to publish and prune one
// completed intent without claiming that the entire scope may close.
func mutationCognitionReceiptResultGateReason(scopeDir string, receipt *mutationCognitionReceipt) (bool, string) {
	if receipt == nil {
		return false, "missing_receipt"
	}
	state := normalizeMutationCognitionState(receipt.ResultState)
	if !mutationCognitionAllowedStates[state] {
		return false, "non_terminal_result_state"
	}
	if receipt.StrongBinding != nil {
		paths, err := rt.ResolvePaths(scopeDir)
		if err != nil {
			return false, "strong_binding_root_unavailable"
		}
		physicalScope, err := filepath.Rel(paths.Root, scopeDir)
		if err != nil || filepath.ToSlash(physicalScope) != receipt.Scope {
			return false, "strong_binding_copied_to_wrong_scope"
		}
		if _, err := requireStrongCloseoutBinding(paths.Root, receipt.Workflow, receipt.Scope, receipt.StrongBinding.ID, receipt.StrongBinding.WorkID); err != nil {
			return false, "strong_binding_stale: " + err.Error()
		}
		stored, err := loadCloseoutBinding(paths.Root, receipt.StrongBinding.ID)
		if err != nil || stored.Digest != receipt.StrongBinding.Digest {
			return false, "strong_binding_receipt_version_changed"
		}
	}
	switch state {
	case "ready", "no_op":
		updateID := strings.TrimSpace(receipt.UpdateID)
		if updateID == "" {
			return false, "missing_update_id"
		}
		paths, ok := mutationCognitionProjectRuntimePaths(scopeDir)
		if !ok {
			return false, "missing_project_cognition_status"
		}
		status, err := rt.ReadStatus(paths)
		if err != nil {
			return false, "invalid_project_cognition_status"
		}
		if status.LastUpdateID != updateID || status.LastFinalizedUpdateID != updateID || status.LastUpdateOutcome != state {
			return false, "update_not_finalized"
		}
		if status.Freshness != rt.ReadyFreshness || status.Readiness != rt.ReadyReadiness || status.Dirty {
			return false, "project_cognition_not_fresh"
		}
	case "scope_ready":
		updateID := strings.TrimSpace(receipt.UpdateID)
		if updateID == "" {
			return false, "missing_update_id"
		}
		paths, ok := mutationCognitionProjectRuntimePaths(scopeDir)
		if !ok {
			return false, "missing_project_cognition_status"
		}
		status, err := rt.ReadStatus(paths)
		if err != nil {
			return false, "invalid_project_cognition_status"
		}
		if status.LastUpdateID != updateID || status.LastUpdateOutcome != "partial_refresh" {
			return false, "scope_update_not_current"
		}
		if status.LastUpdateScopeOutcome != "ready" && status.LastUpdateScopeOutcome != "no_op" {
			return false, "workflow_scope_not_ready"
		}
		if status.Freshness == rt.ReadyFreshness || status.Readiness == rt.ReadyReadiness || !status.Dirty {
			return false, "scope_ready_requires_visible_project_debt"
		}
	case "partial":
		if mutationCognitionHasAutoRepairablePartialReason(receipt) {
			return false, "auto_repairable_partial_missing_passing_verification_result"
		}
	}
	return true, ""
}

func mutationCognitionHasAutoRepairablePartialReason(receipt *mutationCognitionReceipt) bool {
	values := []string{receipt.Reason}
	values = append(values, receipt.Evidence...)
	for _, value := range values {
		if strings.Contains(strings.ToLower(value), "missing_passing_verification_result") {
			return true
		}
	}
	return false
}

func mutationCognitionProjectRuntimePaths(scopeDir string) (rt.Paths, bool) {
	abs, err := filepath.Abs(scopeDir)
	if err != nil {
		return rt.Paths{}, false
	}
	abs = filepath.Clean(abs)
	for {
		candidate, err := rt.ResolvePaths(abs)
		if err == nil {
			if _, statErr := os.Stat(candidate.StatusPath); statErr == nil {
				return candidate, true
			}
		}
		parent := filepath.Dir(abs)
		if parent == abs {
			return rt.Paths{}, false
		}
		abs = parent
	}
}

func requireMutationCognitionReceipt(scopeDir, expectedWorkflow string) error {
	gate := mutationCognitionStatus(scopeDir)
	if gate["allowed_close"] == true {
		// Optionally ensure workflow family matches when provided.
		if expected := strings.TrimSpace(expectedWorkflow); expected != "" {
			got := strings.TrimSpace(fmt.Sprint(gate["workflow"]))
			want, err := normalizeMutationWorkflowID(expected)
			if err == nil && got != "" && got != want {
				// implement-teams records as sp-implement; accept family match.
				if !(want == "sp-implement" && got == "sp-implement") {
					return fmt.Errorf("project cognition mutation receipt workflow is %q, expected %q; %s", got, want, mutationCognitionRecoveryText(scopeDir, want, nil))
				}
			}
		}
		receipt, err := loadMutationCognitionReceipt(scopeDir)
		if err != nil {
			return err
		}
		if receipt != nil && receipt.Workflow == "sp-do" && receipt.DoBinding == nil {
			return fmt.Errorf("missing pre-update Do source binding; resume the exact native Do cognition closeout owner")
		}
		needsStrong := receipt != nil && (receipt.Workflow == "sp-implement" || receipt.Workflow == "sp-quick" || receipt.Workflow == "sp-fast" || receipt.Workflow == "sp-debug" || receipt.Workflow == "sp-review" || receipt.Workflow == "sp-e2e" || receipt.Workflow == "sp-do")
		if receipt == nil || needsStrong && receipt.StrongBinding == nil && !(receipt.Workflow == "sp-do" && receipt.DoBinding != nil) {
			return fmt.Errorf("legacy cognition receipt is audit input and lacks cognition.closeout.binding.v1; begin before fresh verification, seal and apply the exact current binding")
		}
		if receipt.StrongBinding != nil && receipt.StrongBinding.ItemID != "" && (receipt.Workflow == "sp-implement" || receipt.Workflow == "sp-quick" || receipt.Workflow == "sp-review" || receipt.Workflow == "sp-e2e") {
			return fmt.Errorf("terminal scope requires the joined native Work owner, not one item's binding")
		}
		return nil
	}
	status := fmt.Sprint(gate["status"])
	next := mutationCognitionRecoveryText(scopeDir, firstNonEmpty(expectedWorkflow, "sp-implement"), nil)
	if status == "missing" {
		return fmt.Errorf("project cognition mutation closeout receipt is missing; %s; standalone mark-dirty fallback is allowed only when no trustworthy intent can be formed", next)
	}
	if status == "invalid" {
		return fmt.Errorf("project cognition mutation closeout receipt is invalid (%v); %s", gate["error"], next)
	}
	if reason := strings.TrimSpace(fmt.Sprint(gate["blocked_reason"])); reason != "" {
		return fmt.Errorf("project cognition mutation closeout result_state=%q is not closeable: %s; re-run %s after repairing the closeout", gate["result_state"], reason, next)
	}
	return fmt.Errorf("project cognition mutation closeout result_state=%q is not terminal (need ready|no_op|scope_ready|mark-dirty|partial); re-run %s", gate["result_state"], next)
}

func mutationWorkflowForFeatureStage(stage string) (string, bool) {
	workflow, ok := mutationCognitionFeatureStages[strings.ToLower(strings.TrimSpace(stage))]
	return workflow, ok
}

func runMutationCognitionReceiptCLI(args []string, stdout io.Writer) int {
	workflow := firstNonEmpty(optionValue(args, "--workflow", ""), optionValue(args, "--command", ""))
	scopeDir := firstNonEmpty(optionValue(args, "--scope-dir", ""), optionValue(args, "--feature-dir", ""), optionValue(args, "--workspace", ""))
	if strings.TrimSpace(workflow) == "" {
		return writeEnvelope(stdout, scriptDomainError("cognition", fmt.Errorf("mutation-receipt requires --workflow sp-implement|sp-quick|sp-fast|sp-debug|sp-do|sp-review|sp-e2e|sp-map-update")))
	}
	if strings.TrimSpace(scopeDir) == "" {
		return writeEnvelope(stdout, scriptDomainError("cognition", fmt.Errorf("mutation-receipt requires --scope-dir or --feature-dir (feature workspace, quick workspace, or project-relative mutation scope)")))
	}
	// Resolve relative scope against project root when provided.
	projectRoot := optionValue(args, "--project-root", ".")
	absRoot, err := filepath.Abs(projectRoot)
	if err != nil {
		return writeEnvelope(stdout, scriptDomainError("cognition", err))
	}
	absScope := scopeDir
	if !filepath.IsAbs(scopeDir) {
		absScope = filepath.Join(absRoot, filepath.FromSlash(scopeDir))
	}
	absScope = filepath.Clean(absScope)
	resultState := firstNonEmpty(optionValue(args, "--result-state", ""), optionValue(args, "--status", ""))
	if strings.TrimSpace(resultState) == "" {
		return writeEnvelope(stdout, scriptDomainError("cognition", fmt.Errorf("mutation-receipt requires --result-state ready|no_op|scope_ready|mark-dirty|partial")))
	}
	reason := optionValue(args, "--reason", "")
	updateID := optionValue(args, "--update-id", "")
	evidence := []string{}
	if raw := strings.TrimSpace(optionValue(args, "--evidence-json", "")); raw != "" {
		if err := json.Unmarshal([]byte(raw), &evidence); err != nil {
			return writeEnvelope(stdout, scriptDomainError("cognition", fmt.Errorf("--evidence-json must be a JSON string array: %w", err)))
		}
	}
	relScope := scopeDir
	if rel, err := filepath.Rel(absRoot, absScope); err == nil {
		relScope = filepath.ToSlash(rel)
	}
	payload, err := recordMutationCognitionReceipt(absScope, workflow, relScope, resultState, reason, updateID, evidence)
	if err != nil {
		return writeEnvelope(stdout, scriptDomainError("cognition", err))
	}
	env := NewEnvelope("ok", "project cognition mutation closeout recorded")
	env.Data = payload
	env.Data["gate"] = mutationCognitionStatus(absScope)
	return writeEnvelope(stdout, env)
}
