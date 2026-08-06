package main

import (
	"encoding/json"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strings"

	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/workflowregistry"
)

const (
	mutationCognitionReceiptFileName = "cognition-closeout.json"
	mutationCognitionReceiptVersion  = 1
)

// Terminal states that allow a mutation workflow to claim completion.
var mutationCognitionAllowedStates = map[string]bool{
	"ready":      true,
	"no_op":      true,
	"mark-dirty": true,
	"partial":    true,
}

// Feature stages that must leave a project-cognition mutation receipt before complete-stage.
var mutationCognitionFeatureStages = map[string]string{
	"implement": "sp-implement",
	"review":    "sp-review",
}

type mutationCognitionReceipt struct {
	Version     int      `json:"version"`
	Workflow    string   `json:"workflow"`
	Scope       string   `json:"scope,omitempty"` // feature rel, quick workspace, or project
	ResultState string   `json:"result_state"`
	Reason      string   `json:"reason,omitempty"`
	Evidence    []string `json:"evidence,omitempty"`
	UpdateID    string   `json:"update_id,omitempty"`
	RecordedAt  string   `json:"recorded_at"`
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
	canonical, err := normalizeMutationWorkflowID(workflow)
	if err != nil {
		return nil, err
	}
	state := normalizeMutationCognitionState(resultState)
	if !mutationCognitionAllowedStates[state] && state != "needs_rebuild" && state != "blocked" {
		return nil, fmt.Errorf("--result-state must be ready|no_op|mark-dirty|partial|needs_rebuild|blocked (got %q)", resultState)
	}
	if (state == "mark-dirty" || state == "partial" || state == "needs_rebuild" || state == "blocked" || state == "no_op") && strings.TrimSpace(reason) == "" {
		return nil, fmt.Errorf("result_state=%s requires --reason (greenfield/empty graph, no_op, or dirty fallback must be explicit so project cognition keeps improving)", state)
	}
	receipt := mutationCognitionReceipt{
		Version:     mutationCognitionReceiptVersion,
		Workflow:    canonical,
		Scope:       scopeLabel,
		ResultState: state,
		Reason:      strings.TrimSpace(reason),
		Evidence:    evidence,
		UpdateID:    strings.TrimSpace(updateID),
		RecordedAt:  nowUTCString(),
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
		"update_id":     receipt.UpdateID,
		"recorded_at":   receipt.RecordedAt,
		"allowed_close": mutationCognitionAllowedStates[state],
		"policy":        "Every source-changing mutation workflow must refresh project cognition so a greenfield project continuously gains path_index, routes, and claims. Prefer result_state=ready after update+validate-build+complete-refresh; use mark-dirty/no_op only with an explicit reason.",
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
	out["allowed_close"] = mutationCognitionAllowedStates[normalizeMutationCognitionState(receipt.ResultState)]
	return out
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
					return fmt.Errorf("project cognition mutation receipt workflow is %q, expected %q; re-record with cognition mutation-receipt --workflow %s", got, want, want)
				}
			}
		}
		return nil
	}
	status := fmt.Sprint(gate["status"])
	next := fmt.Sprintf("specify-runtime cognition mutation-receipt --workflow %s --scope-dir %q --result-state ready|no_op|mark-dirty|partial --reason <text> --format json", firstNonEmpty(expectedWorkflow, "sp-implement"), scopeDir)
	if status == "missing" {
		return fmt.Errorf("project cognition mutation closeout receipt is missing; after source changes run closeout-plan → update → validate-build/complete-refresh (or mark-dirty), then %s so the project map keeps improving", next)
	}
	if status == "invalid" {
		return fmt.Errorf("project cognition mutation closeout receipt is invalid (%v); re-run %s", gate["error"], next)
	}
	return fmt.Errorf("project cognition mutation closeout result_state=%q is not terminal (need ready|no_op|mark-dirty|partial); re-run %s", gate["result_state"], next)
}

func mutationWorkflowForFeatureStage(stage string) (string, bool) {
	workflow, ok := mutationCognitionFeatureStages[strings.ToLower(strings.TrimSpace(stage))]
	return workflow, ok
}

func runMutationCognitionReceiptCLI(args []string, stdout io.Writer) int {
	workflow := firstNonEmpty(optionValue(args, "--workflow", ""), optionValue(args, "--command", ""))
	scopeDir := firstNonEmpty(optionValue(args, "--scope-dir", ""), optionValue(args, "--feature-dir", ""), optionValue(args, "--workspace", ""))
	if strings.TrimSpace(workflow) == "" {
		return writeEnvelope(stdout, scriptDomainError("cognition", fmt.Errorf("mutation-receipt requires --workflow sp-implement|sp-quick|sp-fast|sp-debug|sp-review|sp-map-update")))
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
		return writeEnvelope(stdout, scriptDomainError("cognition", fmt.Errorf("mutation-receipt requires --result-state ready|no_op|mark-dirty|partial")))
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
