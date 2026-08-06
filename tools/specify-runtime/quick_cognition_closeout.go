package main

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"regexp"
	"strings"
)

const quickCognitionCloseoutFileName = "cognition-closeout.json"
const quickCognitionCloseoutVersion = 1

// Terminal result_state values that satisfy the quick close gate for source-changing work.
var quickCognitionCloseoutAllowedStates = map[string]bool{
	"ready":      true,
	"no_op":      true,
	"mark-dirty": true,
	"partial":    true,
}

type quickCognitionCloseoutReceipt struct {
	Version     int      `json:"version"`
	Workflow    string   `json:"workflow"`
	ResultState string   `json:"result_state"`
	Reason      string   `json:"reason,omitempty"`
	Evidence    []string `json:"evidence,omitempty"`
	UpdateID    string   `json:"update_id,omitempty"`
	RecordedAt  string   `json:"recorded_at"`
}

func (service quickService) recordCognitionCloseout(workspacePath, resultState, reason, updateID string, evidence []string) (map[string]any, error) {
	payload, err := recordMutationCognitionReceipt(workspacePath, "sp-quick", filepath.Base(workspacePath), resultState, reason, updateID, evidence)
	if err != nil {
		return nil, err
	}
	state := fmt.Sprint(payload["result_state"])
	if err := service.patchStatusProjectCognitionRefresh(workspacePath, state, fmt.Sprint(payload["reason"]), evidence); err != nil {
		return nil, err
	}
	payload["status_synced"] = true
	payload["next_action"] = "Run specify-runtime quick close <id> resolved after validation and SUMMARY are ready."
	return payload, nil
}

func (service quickService) loadCognitionCloseout(workspacePath string) (*quickCognitionCloseoutReceipt, error) {
	receipt, err := loadMutationCognitionReceipt(workspacePath)
	if err != nil || receipt == nil {
		return nil, err
	}
	return &quickCognitionCloseoutReceipt{
		Version:     receipt.Version,
		Workflow:    receipt.Workflow,
		ResultState: receipt.ResultState,
		Reason:      receipt.Reason,
		Evidence:    receipt.Evidence,
		UpdateID:    receipt.UpdateID,
		RecordedAt:  receipt.RecordedAt,
	}, nil
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
	if err != nil {
		out["status"] = "invalid"
		out["error"] = err.Error()
		out["allowed_close"] = false
		return out
	}
	if receipt != nil {
		out["status"] = "recorded"
		out["result_state"] = receipt.ResultState
		out["reason"] = receipt.Reason
		out["receipt_path"] = filepath.ToSlash(filepath.Join(workspacePath, quickCognitionCloseoutFileName))
		out["allowed_close"] = mutationCognitionAllowedStates[normalizeMutationCognitionState(receipt.ResultState)]
		if !needs {
			out["allowed_close"] = true
		}
		return out
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
	return out
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
	next := "specify-runtime quick cognition-closeout <id> --result-state ready|no_op|mark-dirty|partial --reason <text> --format json"
	switch status {
	case "missing", "missing-receipt":
		return fmt.Errorf("cannot close as resolved: project cognition closeout receipt is missing for source-changing quick work; run planner-first cognition closeout (closeout-plan → update → validate-build/complete-refresh or mark-dirty), then %s; greenfield/empty graph must still record no_op or mark-dirty with --reason", next)
	case "invalid":
		return fmt.Errorf("cannot close as resolved: cognition-closeout receipt is invalid (%v); re-run %s", gate["error"], next)
	default:
		return fmt.Errorf("cannot close as resolved: cognition closeout result_state=%q is not terminal for close (need ready|no_op|mark-dirty|partial); re-run %s", state, next)
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
