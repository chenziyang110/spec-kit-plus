package main

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"regexp"
	"strings"

	rt "github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/runtime"
	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/store"
)

const quickCognitionCloseoutFileName = "cognition-closeout.json"
const quickCognitionCloseoutVersion = 1

// Terminal result_state values that satisfy the quick close gate for source-changing work.
var quickCognitionCloseoutAllowedStates = map[string]bool{
	"ready":       true,
	"no_op":       true,
	"scope_ready": true,
	"mark-dirty":  true,
	"partial":     true,
}

type quickCognitionCloseoutReceipt = mutationCognitionReceipt

func (service quickService) recordCognitionCloseout(workspacePath, resultState, reason, updateID string, evidence []string, bindingID string) (map[string]any, error) {
	var payload map[string]any
	var err error
	if bindingID != "" {
		payload, err = recordBoundFallbackCognitionReceipt(workspacePath, "sp-quick", resultState, reason, updateID, evidence, bindingID)
	} else {
		payload, err = recordMutationCognitionReceipt(workspacePath, "sp-quick", filepath.Base(workspacePath), resultState, reason, updateID, evidence)
	}
	if err != nil {
		return nil, err
	}
	state := fmt.Sprint(payload["result_state"])
	if err := service.patchStatusProjectCognitionRefresh(workspacePath, state, fmt.Sprint(payload["reason"]), evidence); err != nil {
		return nil, err
	}
	payload["status_synced"] = true
	gate := service.cognitionCloseoutStatus(workspacePath)
	payload["allowed_close"] = gate["allowed_close"]
	if blockedReason, ok := gate["blocked_reason"]; ok {
		payload["blocked_reason"] = blockedReason
	}
	if payload["allowed_close"] == true {
		payload["next_action"] = "Run specify-runtime quick close <id> resolved after validation and SUMMARY are ready."
	}
	return payload, nil
}

func recordBoundFallbackCognitionReceipt(scopeDir, workflow, resultState, reason, updateID string, evidence []string, bindingID string) (map[string]any, error) {
	canonical, err := normalizeMutationWorkflowID(workflow)
	if err != nil {
		return nil, err
	}
	if canonical != "sp-quick" || normalizeMutationCognitionState(resultState) != "mark-dirty" || strings.TrimSpace(updateID) != "" {
		return nil, fmt.Errorf("--binding-id fallback requires workflow sp-quick, result-state mark-dirty and no update-id")
	}
	if strings.TrimSpace(reason) == "" {
		return nil, fmt.Errorf("bound mark-dirty fallback requires an explicit --reason")
	}
	paths, err := rt.ResolvePaths(scopeDir)
	if err != nil {
		return nil, err
	}
	scope, err := filepath.Rel(paths.Root, scopeDir)
	if err != nil {
		return nil, err
	}
	scope = filepath.ToSlash(scope)
	release, err := rt.AcquireUpdateLock(paths)
	if err != nil {
		return nil, err
	}
	defer release()
	intent, err := pendingMutationCloseoutIntent(scopeDir, canonical)
	if err != nil {
		return nil, fmt.Errorf("cannot establish absence of a durable closeout intent: %w", err)
	}
	if intent != nil {
		return nil, fmt.Errorf("bound fallback cannot replace durable intent %s; %s", intent.ID, mutationCognitionRecoveryText(scopeDir, canonical, nil))
	}
	proof, err := requireStrongCloseoutBinding(paths.Root, canonical, scope, bindingID, "")
	if err != nil {
		return nil, err
	}
	if proof.ItemID != "" {
		return nil, fmt.Errorf("bound fallback requires the joined Quick Work owner, not one item's binding")
	}
	debt, err := missingOrIncompatibleCognitionDebt(paths)
	if err != nil {
		return nil, err
	}
	receipt := mutationCognitionReceipt{
		Version: mutationCognitionReceiptVersion, Workflow: canonical, Scope: scope,
		ResultState: "mark-dirty", Reason: strings.TrimSpace(reason), Evidence: evidence,
		ChangedPaths: normalizedCloseoutPaths(proof.OwnedDelta), RecordedAt: nowUTCString(),
		StrongBinding: proof, GraphDebt: debt,
	}
	return publishMutationCognitionReceipt(scopeDir, receipt)
}

func missingOrIncompatibleCognitionDebt(paths rt.Paths) (*mutationCognitionGraphDebt, error) {
	debt := &mutationCognitionGraphDebt{
		CauseCode: "missing_graph_store", GraphStorePath: ".specify/project-cognition/project-cognition.db",
		RequiredSchema: store.SchemaVersion, RecoveryAction: "run_map_scan_build",
		RecoveryArgv: []string{"specify-runtime", "cognition", "status", "--format", "json"},
	}
	info, err := os.Lstat(paths.DatabasePath)
	if os.IsNotExist(err) {
		return debt, nil
	}
	if err != nil {
		return nil, err
	}
	if !info.Mode().IsRegular() {
		return nil, fmt.Errorf("bound fallback requires a regular graph store or a missing store")
	}
	version, _, err := store.ExistingDatabaseSchemaVersion(paths)
	if err != nil {
		return nil, fmt.Errorf("cannot verify graph incompatibility: %w", err)
	}
	if version == store.SchemaVersion {
		return nil, fmt.Errorf("bound fallback requires a missing or incompatible graph schema; use the shared cognition closeout apply for the current store")
	}
	debt.CauseCode, debt.SchemaVersion, debt.RecoveryAction = "graph_store_incompatible", version, "inspect_incompatible_store"
	debt.RecoveryArgv = []string{"specify-runtime", "cognition", "archive-incompatible-store", "--inspect", "--format", "json"}
	return debt, nil
}

func (service quickService) loadCognitionCloseout(workspacePath string) (*quickCognitionCloseoutReceipt, error) {
	receipt, err := loadMutationCognitionReceipt(workspacePath)
	if err != nil || receipt == nil {
		return nil, err
	}
	return receipt, nil
}

func (service quickService) cognitionCloseoutStatus(workspacePath string) map[string]any {
	needs := service.quickNeedsCognitionCloseout(workspacePath)
	receipt, err := service.loadCognitionCloseout(workspacePath)
	statusFromBody := service.readStatusProjectCognitionRefresh(workspacePath)
	out := map[string]any{
		"required":      needs,
		"status":        "missing",
		"result_state":  "",
		"reason":        "",
		"receipt_path":  "",
		"status_md":     statusFromBody,
		"allowed_close": !needs,
	}
	finish := func() map[string]any {
		if needs && out["allowed_close"] != true {
			out["next_argv"] = mutationCognitionRecoveryArgv(workspacePath, "sp-quick", service.readStatusChangedCodePaths(workspacePath))
			out["recommended_next_action"] = mutationCognitionRecoveryText(workspacePath, "sp-quick", service.readStatusChangedCodePaths(workspacePath))
		}
		return out
	}
	if err != nil {
		out["status"] = "invalid"
		out["error"] = err.Error()
		out["allowed_close"] = false
		return finish()
	}
	if receipt != nil {
		out["status"] = "recorded"
		out["result_state"] = receipt.ResultState
		out["reason"] = receipt.Reason
		out["receipt_path"] = filepath.ToSlash(filepath.Join(workspacePath, quickCognitionCloseoutFileName))
		if receipt.GraphDebt != nil {
			out["graph_debt"] = receipt.GraphDebt
		}
		allowed, reason := mutationCognitionReceiptGateReason(workspacePath, receipt)
		if needs && receipt.StrongBinding == nil {
			allowed, reason = false, "legacy_receipt_missing_strong_binding"
		}
		if needs && receipt.StrongBinding != nil && receipt.StrongBinding.ItemID != "" {
			allowed, reason = false, "terminal_scope_requires_joined_binding"
		}
		out["allowed_close"] = allowed
		if reason != "" {
			out["blocked_reason"] = reason
		}
		if !needs {
			out["allowed_close"] = true
		}
		return finish()
	}
	// Fall back to STATUS.md body when agents only patched prose (still prefer receipt).
	bodyState := strings.ToLower(strings.TrimSpace(fmt.Sprint(statusFromBody["status"])))
	switch bodyState {
	case "ready", "no_op", "mark-dirty", "partial", "not-needed":
		out["status"] = "status-md-only"
		out["result_state"] = bodyState
		out["reason"] = fmt.Sprint(statusFromBody["reason"])
		if needs {
			// Source-changing work requires the durable receipt file, not only STATUS prose.
			out["allowed_close"] = false
			out["status"] = "missing-receipt"
		} else if bodyState == "not-needed" || mutationCognitionAllowedStates[bodyState] {
			out["allowed_close"] = true
		}
	}
	return finish()
}

func (service quickService) validateCognitionCloseoutForClose(workspacePath, statusValue string) error {
	if statusValue != "resolved" {
		return nil
	}
	gate := service.cognitionCloseoutStatus(workspacePath)
	if gate["allowed_close"] == true {
		return nil
	}
	needs := gate["required"] == true
	if !needs {
		return nil
	}
	state := strings.TrimSpace(fmt.Sprint(gate["result_state"]))
	status := strings.TrimSpace(fmt.Sprint(gate["status"]))
	next := mutationCognitionRecoveryText(workspacePath, "sp-quick", service.readStatusChangedCodePaths(workspacePath))
	switch status {
	case "missing", "missing-receipt":
		return fmt.Errorf("cannot close as resolved: project cognition closeout receipt is missing for source-changing quick work; %s; greenfield/empty graph still needs no_op from shared apply or an explicit dirty fallback when no trustworthy intent can be formed", next)
	case "invalid":
		return fmt.Errorf("cannot close as resolved: cognition-closeout receipt is invalid (%v); %s", gate["error"], next)
	default:
		if reason := strings.TrimSpace(fmt.Sprint(gate["blocked_reason"])); reason != "" {
			return fmt.Errorf("cannot close as resolved: cognition closeout result_state=%q is not closeable: %s; re-run %s after repairing the closeout", state, reason, next)
		}
		return fmt.Errorf("cannot close as resolved: cognition closeout result_state=%q is not terminal for close (need ready|no_op|scope_ready|mark-dirty|partial); re-run %s", state, next)
	}
}

func (service quickService) quickNeedsCognitionCloseout(workspacePath string) bool {
	if paths := service.readStatusChangedCodePaths(workspacePath); len(paths) > 0 {
		for _, path := range paths {
			if quickPathImpliesProjectCognition(path) {
				return true
			}
		}
	}
	doc, err := service.loadConfirmation(workspacePath)
	if err != nil || doc == nil {
		return false
	}
	for _, item := range doc.Decision.Items {
		for _, path := range item.WriteScope {
			if quickPathImpliesProjectCognition(path) {
				return true
			}
		}
	}
	return false
}

func quickPathImpliesProjectCognition(path string) bool {
	rel := filepath.ToSlash(strings.TrimSpace(path))
	if rel == "" || rel == "." {
		return false
	}
	lower := strings.ToLower(rel)
	// Quick workspace and pure planning prose do not require project cognition update.
	if strings.HasPrefix(lower, ".planning/") {
		return false
	}
	if strings.HasPrefix(lower, ".specify/features/") || strings.HasPrefix(lower, "specs/") {
		// Feature planning artifacts alone are not product-graph mutations.
		if strings.HasSuffix(lower, ".md") || strings.HasSuffix(lower, ".json") {
			return false
		}
	}
	// Docs-only under docs/ still can affect navigation; treat as cognition-relevant
	// only when not pure changelog/readme under quick scope — default true for product paths.
	return true
}

var quickProjectCognitionStatusRE = regexp.MustCompile(`(?m)^project_cognition_refresh:\s*\n(?:[ \t]+.+\n)*?[ \t]+status:\s*(\S+)`)

func (service quickService) readStatusChangedCodePaths(workspacePath string) []string {
	raw, err := os.ReadFile(filepath.Join(workspacePath, "STATUS.md"))
	if err != nil {
		return nil
	}
	text := string(raw)
	// YAML list form under changed_code_paths:
	lines := strings.Split(text, "\n")
	inSection := false
	paths := []string{}
	for _, line := range lines {
		trimmed := strings.TrimSpace(line)
		if strings.HasPrefix(trimmed, "changed_code_paths:") {
			inSection = true
			rest := strings.TrimSpace(strings.TrimPrefix(trimmed, "changed_code_paths:"))
			if rest == "[]" || rest == "" {
				continue
			}
			if strings.HasPrefix(rest, "[") && strings.HasSuffix(rest, "]") {
				inner := strings.Trim(rest, "[]")
				for _, part := range strings.Split(inner, ",") {
					part = strings.Trim(strings.TrimSpace(part), `"'`)
					if part != "" {
						paths = append(paths, part)
					}
				}
			}
			continue
		}
		if inSection {
			if strings.HasPrefix(line, "  - ") || strings.HasPrefix(line, "- ") {
				item := strings.TrimSpace(strings.TrimPrefix(strings.TrimSpace(line), "-"))
				item = strings.Trim(item, `"'`)
				if item != "" && item != "[]" {
					paths = append(paths, item)
				}
				continue
			}
			if trimmed != "" && !strings.HasPrefix(line, " ") && !strings.HasPrefix(line, "\t") {
				inSection = false
			}
		}
	}
	return paths
}

func (service quickService) readStatusProjectCognitionRefresh(workspacePath string) map[string]any {
	raw, err := os.ReadFile(filepath.Join(workspacePath, "STATUS.md"))
	if err != nil {
		return map[string]any{}
	}
	text := string(raw)
	out := map[string]any{"status": "", "reason": "", "evidence": []string{}}
	if m := quickProjectCognitionStatusRE.FindStringSubmatch(text); len(m) == 2 {
		out["status"] = strings.Trim(m[1], `"'`)
	}
	// Optional reason line under the block.
	reasonRE := regexp.MustCompile(`(?m)^project_cognition_refresh:\s*\n(?:[ \t]+.+\n)*?[ \t]+reason:\s*(.+)$`)
	if m := reasonRE.FindStringSubmatch(text); len(m) == 2 {
		out["reason"] = strings.Trim(strings.TrimSpace(m[1]), `"'`)
	}
	return out
}

func (service quickService) patchStatusProjectCognitionRefresh(workspacePath, resultState, reason string, evidence []string) error {
	statusPath := filepath.Join(workspacePath, "STATUS.md")
	raw, err := os.ReadFile(statusPath)
	if err != nil {
		return err
	}
	evidenceJSON, _ := json.Marshal(evidence)
	if evidenceJSON == nil {
		evidenceJSON = []byte("[]")
	}
	block := "project_cognition_refresh:\n" +
		"  status: " + resultState + "\n" +
		"  reason: " + strconvQuoteIfNeeded(reason) + "\n" +
		"  evidence: " + string(evidenceJSON) + "\n"
	text := string(raw)
	sectionRE := regexp.MustCompile(`(?ms)^project_cognition_refresh:\n(?:[ \t].*\n)*`)
	if sectionRE.MatchString(text) {
		text = sectionRE.ReplaceAllString(text, block)
	} else {
		// Append under Summary Pointer when present.
		anchor := "## Summary Pointer"
		if idx := strings.Index(text, anchor); idx >= 0 {
			// Find end of Summary Pointer section (next ##) or EOF.
			rest := text[idx:]
			next := strings.Index(rest[len(anchor):], "\n## ")
			insertAt := len(text)
			if next >= 0 {
				insertAt = idx + len(anchor) + next + 1
			}
			text = text[:insertAt] + "\n" + block + text[insertAt:]
		} else {
			text = strings.TrimRight(text, "\n") + "\n\n" + block
		}
	}
	return writeScriptTextFile(statusPath, text)
}

func strconvQuoteIfNeeded(value string) string {
	value = strings.TrimSpace(value)
	if value == "" {
		return `""`
	}
	if strings.ContainsAny(value, ":#\n\"'") || strings.Contains(value, " ") {
		b, _ := json.Marshal(value)
		return string(b)
	}
	return value
}
