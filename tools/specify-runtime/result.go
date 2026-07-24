package main

import (
	"encoding/json"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"sort"
	"strings"
)

var resultStatusAliases = map[string]string{
	"pending":            "pending",
	"success":            "success",
	"done":               "success",
	"completed":          "success",
	"done_with_concerns": "success",
	"blocked":            "blocked",
	"needs_context":      "blocked",
	"failed":             "failed",
	"error":              "failed",
}

var resultValidationStatusAliases = map[string]string{
	"passed":  "passed",
	"pass":    "passed",
	"success": "passed",
	"failed":  "failed",
	"fail":    "failed",
	"error":   "failed",
	"skipped": "skipped",
	"skip":    "skipped",
}

var obsoleteUIResultFields = map[string]bool{
	"ui_fidelity_evidence": true,
	"uiFidelityEvidence":   true,
	"uiEvidence":           true,
	"uiVerification":       true,
}

var currentUIEvidenceKinds = map[string]bool{
	"structure_snapshot":  true,
	"visual_capture":      true,
	"runtime_diagnostics": true,
}

var currentUIVerificationFields = map[string]bool{
	"contract_check":              true,
	"runtime_evidence":            true,
	"visual_comparison":           true,
	"fidelity_status":             true,
	"reviewer":                    true,
	"approved_visual_ref":         true,
	"approved_preview_sha256":     true,
	"approved_manifest_sha256":    true,
	"comparison_report_ref":       true,
	"comparison_report_sha256":    true,
	"implementation_capture_refs": true,
	"covered_decision_ids":        true,
	"structural_differences":      true,
	"visual_differences":          true,
	"comparison_tolerance":        true,
	"accepted_deviations":         true,
}

func runResult(args []string, stdout io.Writer) int {
	if len(args) == 0 {
		return writeResultError(stdout, "usage-error", "missing result subcommand")
	}
	switch args[0] {
	case "path":
		return runResultPath(args[1:], stdout)
	case "submit":
		return runResultSubmit(args[1:], stdout)
	default:
		return writeResultError(stdout, "usage-error", fmt.Sprintf("unknown result subcommand %q", args[0]))
	}
}

func runResultPath(args []string, stdout io.Writer) int {
	projectRoot, err := os.Getwd()
	if err != nil {
		return writeResultError(stdout, "error", fmt.Sprintf("resolve project root: %v", err))
	}
	integration, err := resultIntegrationKey(projectRoot)
	if err != nil {
		return writeResultError(stdout, "usage-error", err.Error())
	}
	commandName := strings.TrimSpace(optionValue(args, "--command", ""))
	target, err := buildResultHandoffPath(projectRoot, resultPathRequest{
		CommandName:      commandName,
		IntegrationKey:   integration,
		RequestID:        optionValue(args, "--request-id", ""),
		FeatureDir:       optionValue(args, "--feature-dir", ""),
		TaskID:           optionValue(args, "--task-id", ""),
		Workspace:        optionValue(args, "--workspace", ""),
		DebugSessionSlug: optionValue(args, "--session-slug", ""),
		LaneID:           optionValue(args, "--lane-id", ""),
	})
	if err != nil {
		return writeResultError(stdout, "usage-error", err.Error())
	}
	env := NewEnvelope("ok", "result handoff path resolved")
	env.Data["command"] = commandName
	env.Data["integration"] = integration
	env.Data["path"] = target
	return writeEnvelope(stdout, env)
}

func runResultSubmit(args []string, stdout io.Writer) int {
	projectRoot, err := os.Getwd()
	if err != nil {
		return writeResultError(stdout, "error", fmt.Sprintf("resolve project root: %v", err))
	}
	integration, err := resultIntegrationKey(projectRoot)
	if err != nil {
		return writeResultError(stdout, "usage-error", err.Error())
	}
	commandName := strings.TrimSpace(optionValue(args, "--command", ""))
	if integration == "codex" && strings.ToLower(commandName) != "review" {
		return writeResultError(stdout, "usage-error", "Codex projects must use `sp-teams submit-result` for runtime-managed result channels.")
	}
	resultFile := strings.TrimSpace(optionValue(args, "--result-file", ""))
	if resultFile == "" {
		return writeResultError(stdout, "usage-error", "--result-file is required")
	}
	sourcePath, err := resolveProjectContainedPath(projectRoot, resultFile)
	if err != nil {
		return writeResultError(stdout, "usage-error", fmt.Sprintf("result file path is invalid: %v", err))
	}
	raw, err := os.ReadFile(sourcePath)
	if err != nil {
		return writeResultError(stdout, "blocked", fmt.Sprintf("Result file not found: %s", sourcePath))
	}
	normalized, err := normalizeWorkerTaskResult(raw)
	if err != nil {
		return writeResultError(stdout, "invalid", err.Error())
	}
	if normalized["status"] == "pending" {
		return writeResultError(stdout, "invalid", "Pending result templates cannot be written to the canonical handoff path. Replace the placeholder with a real success, blocked, or failed result first.")
	}
	target, err := buildResultHandoffPath(projectRoot, resultPathRequest{
		CommandName:      commandName,
		IntegrationKey:   integration,
		RequestID:        optionValue(args, "--request-id", ""),
		FeatureDir:       optionValue(args, "--feature-dir", ""),
		TaskID:           optionValue(args, "--task-id", ""),
		Workspace:        optionValue(args, "--workspace", ""),
		DebugSessionSlug: optionValue(args, "--session-slug", ""),
		LaneID:           optionValue(args, "--lane-id", ""),
	})
	if err != nil {
		return writeResultError(stdout, "usage-error", err.Error())
	}
	if err := writeJSONAtomic(target, normalized); err != nil {
		return writeResultError(stdout, "error", fmt.Sprintf("write result handoff: %v", err))
	}
	env := NewEnvelope("ok", "result handoff submitted")
	env.Data["command"] = commandName
	env.Data["integration"] = integration
	env.Data["path"] = target
	env.Data["worker_status"] = normalized["status"]
	env.Data["reported_status"] = normalized["reported_status"]
	return writeEnvelope(stdout, env)
}

type resultPathRequest struct {
	CommandName      string
	IntegrationKey   string
	RequestID        string
	FeatureDir       string
	TaskID           string
	Workspace        string
	DebugSessionSlug string
	LaneID           string
}

func buildResultHandoffPath(projectRoot string, request resultPathRequest) (string, error) {
	commandName := strings.ToLower(strings.TrimSpace(request.CommandName))
	integrationKey := strings.ToLower(strings.TrimSpace(request.IntegrationKey))

	switch {
	case commandName == "review":
		featureDir, err := resolveProjectContainedPath(projectRoot, request.FeatureDir)
		if err != nil || strings.TrimSpace(request.LaneID) == "" {
			return "", fmt.Errorf("--feature-dir and --lane-id are required for review result handoff")
		}
		laneID, err := resultPathSegment(request.LaneID, "lane-id")
		if err != nil {
			return "", err
		}
		return resolveProjectContainedPath(projectRoot, filepath.Join(featureDir, "review-results", laneID+".json"))
	case integrationKey == "codex":
		if strings.TrimSpace(request.RequestID) == "" {
			return "", fmt.Errorf("Codex result handoff paths are runtime-managed; pass --request-id <id> or use `sp-teams submit-result --request-id <id> --result-file <path>`.")
		}
		requestID, err := resultPathSegment(request.RequestID, "request-id")
		if err != nil {
			return "", err
		}
		return resolveProjectContainedPath(projectRoot, filepath.Join(".specify", "teams", "state", "results", requestID+".json"))
	case commandName == "implement":
		featureDir, err := resolveProjectContainedPath(projectRoot, request.FeatureDir)
		if err != nil || strings.TrimSpace(request.TaskID) == "" {
			return "", fmt.Errorf("--feature-dir and --task-id are required for implement result handoff")
		}
		taskID, err := resultPathSegment(request.TaskID, "task-id")
		if err != nil {
			return "", err
		}
		return resolveProjectContainedPath(projectRoot, filepath.Join(featureDir, "worker-results", taskID+".json"))
	case commandName == "quick":
		workspace, err := resolveProjectContainedPath(projectRoot, request.Workspace)
		if err != nil || strings.TrimSpace(request.LaneID) == "" {
			return "", fmt.Errorf("--workspace and --lane-id are required for quick result handoff")
		}
		laneID, err := resultPathSegment(request.LaneID, "lane-id")
		if err != nil {
			return "", err
		}
		return resolveProjectContainedPath(projectRoot, filepath.Join(workspace, "worker-results", laneID+".json"))
	case commandName == "debug":
		if strings.TrimSpace(request.DebugSessionSlug) == "" || strings.TrimSpace(request.LaneID) == "" {
			return "", fmt.Errorf("--session-slug and --lane-id are required for debug result handoff")
		}
		sessionSlug, err := resultPathSegment(request.DebugSessionSlug, "session-slug")
		if err != nil {
			return "", err
		}
		laneID, err := resultPathSegment(request.LaneID, "lane-id")
		if err != nil {
			return "", err
		}
		return resolveProjectContainedPath(projectRoot, filepath.Join(".planning", "debug", "results", sessionSlug, laneID+".json"))
	default:
		return "", fmt.Errorf("Unsupported result command %q.", request.CommandName)
	}
}

func resultPathSegment(value, label string) (string, error) {
	value = strings.TrimSpace(value)
	if value == "" {
		return "", fmt.Errorf("--%s is required", label)
	}
	if strings.ContainsAny(value, `/\`) || value == "." || value == ".." {
		return "", fmt.Errorf("--%s must be a single path segment", label)
	}
	return value, nil
}

func resultIntegrationKey(projectRoot string) (string, error) {
	configPath := filepath.Join(projectRoot, ".specify", "integration.json")
	raw, err := os.ReadFile(configPath)
	if err != nil {
		return "", fmt.Errorf(".specify/integration.json is required for result handoff commands")
	}
	var payload map[string]any
	if err := json.Unmarshal(raw, &payload); err != nil {
		return "", fmt.Errorf(".specify/integration.json is invalid JSON")
	}
	integration := strings.ToLower(strings.TrimSpace(asString(payload["integration"])))
	if integration == "" {
		integration = strings.ToLower(strings.TrimSpace(asString(payload["ai"])))
	}
	if integration == "" {
		return "", fmt.Errorf(".specify/integration.json does not declare integration")
	}
	return integration, nil
}

func normalizeWorkerTaskResult(raw []byte) (map[string]any, error) {
	var payload map[string]any
	if err := json.Unmarshal(raw, &payload); err != nil {
		return nil, fmt.Errorf("worker result payload must be JSON object: %w", err)
	}
	if payload == nil {
		return nil, fmt.Errorf("worker result payload must be JSON object")
	}
	unsupported := []string{}
	for key := range payload {
		if obsoleteUIResultFields[key] {
			unsupported = append(unsupported, key)
		}
	}
	if len(unsupported) > 0 {
		sort.Strings(unsupported)
		return nil, fmt.Errorf("obsolete UI result fields are not supported; use ui_evidence: %s", strings.Join(unsupported, ", "))
	}

	rawStatus := strings.ToLower(strings.TrimSpace(asString(pick(payload, "status", "reported_status", "result_status"))))
	canonicalStatus := resultStatusAliases[rawStatus]
	if canonicalStatus == "" {
		canonicalStatus = "failed"
	}
	summary := asString(pick(payload, "summary", "message", "output_summary"))
	blockers := asStringList(pick(payload, "blockers", "blocking_reasons", "blocker"))
	failedAssumptions := asStringList(pick(payload, "failed_assumptions", "failedAssumptions", "missing_context", "assumptions"))
	recoveryActions := asStringList(pick(payload, "suggested_recovery_actions", "recovery_actions", "recoveryActions", "next_steps"))
	concerns := asStringList(pick(payload, "concerns", "issues", "notes"))

	if rawStatus == "done_with_concerns" && len(concerns) == 0 {
		concerns = []string{"worker reported follow-up concerns"}
	}
	if rawStatus == "needs_context" {
		if len(blockers) == 0 && strings.TrimSpace(summary) != "" {
			blockers = []string{strings.TrimSpace(summary)}
		}
		if len(failedAssumptions) == 0 {
			failedAssumptions = asStringList(payload["missing_context"])
			if len(failedAssumptions) == 0 {
				failedAssumptions = []string{"required execution context was not available"}
			}
		}
		if len(recoveryActions) == 0 {
			recoveryActions = []string{"provide the missing context and resubmit the delegated task"}
		}
	}
	if canonicalStatus == "blocked" {
		if len(blockers) == 0 && strings.TrimSpace(summary) != "" {
			blockers = []string{strings.TrimSpace(summary)}
		}
		if len(failedAssumptions) == 0 {
			failedAssumptions = []string{"worker could not proceed with the available assumptions"}
		}
		if len(recoveryActions) == 0 {
			recoveryActions = []string{"inspect the blocker details and resubmit the delegated task"}
		}
	}

	uiEvidence, err := normalizeUIEvidence(payload["ui_evidence"])
	if err != nil {
		return nil, err
	}
	uiVerification, err := normalizeUIVerification(payload["ui_verification"])
	if err != nil {
		return nil, err
	}

	reportedStatus := rawStatus
	if reportedStatus == "" {
		reportedStatus = canonicalStatus
	}
	return map[string]any{
		"task_id":                    strings.TrimSpace(asString(pick(payload, "task_id", "taskId"))),
		"status":                     canonicalStatus,
		"wave":                       strings.TrimSpace(asString(payload["wave"])),
		"packet_id":                  strings.TrimSpace(asString(pick(payload, "packet_id", "packetId"))),
		"obligation_ids":             asStringList(pick(payload, "obligation_ids", "obligationIds")),
		"observations":               normalizeObjectList(payload["observations"]),
		"findings":                   normalizeObjectList(payload["findings"]),
		"changed_files":              asStringList(pick(payload, "changed_files", "changedFiles", "files_changed")),
		"validation_results":         normalizeValidationResults(payload),
		"summary":                    summary,
		"concerns":                   concerns,
		"reported_status":            reportedStatus,
		"blockers":                   blockers,
		"failed_assumptions":         failedAssumptions,
		"suggested_recovery_actions": recoveryActions,
		"rule_acknowledgement":       normalizeRuleAcknowledgement(payload),
		"acceptance_evidence":        normalizeEvidenceItems(pick(payload, "acceptance_evidence", "acceptanceEvidence")),
		"consumer_evidence":          normalizeEvidenceItems(pick(payload, "consumer_evidence", "consumerEvidence")),
		"manual_evidence":            normalizeEvidenceItems(pick(payload, "manual_evidence", "manualEvidence")),
		"must_preserve_evidence":     normalizeEvidenceItems(pick(payload, "must_preserve_evidence", "mustPreserveEvidence")),
		"consequence_evidence":       normalizeEvidenceItems(pick(payload, "consequence_evidence", "consequenceEvidence")),
		"ui_evidence":                uiEvidence,
		"ui_verification":            uiVerification,
	}, nil
}

func normalizeValidationResults(payload map[string]any) []map[string]string {
	raw, ok := pick(payload, "validation_results", "validationResults").([]any)
	if !ok {
		return []map[string]string{}
	}
	results := []map[string]string{}
	for _, item := range raw {
		record, ok := item.(map[string]any)
		if !ok {
			continue
		}
		command := strings.TrimSpace(asString(pick(record, "command", "cmd")))
		if command == "" {
			continue
		}
		rawStatus := strings.ToLower(strings.TrimSpace(asString(pick(record, "status", "result"))))
		status := resultValidationStatusAliases[rawStatus]
		if status == "" {
			status = "failed"
		}
		results = append(results, map[string]string{
			"command": command,
			"status":  status,
			"output":  asString(pick(record, "output", "details", "message")),
		})
	}
	return results
}

func normalizeRuleAcknowledgement(payload map[string]any) map[string]any {
	raw, ok := pick(payload, "rule_acknowledgement", "ruleAcknowledgement").(map[string]any)
	if !ok {
		return defaultRuleAcknowledgement()
	}
	return map[string]any{
		"required_references_read":  boolValue(pick(raw, "required_references_read", "requiredReferencesRead")),
		"forbidden_drift_respected": boolValue(pick(raw, "forbidden_drift_respected", "forbiddenDriftRespected")),
		"context_bundle_read":       boolValue(pick(raw, "context_bundle_read", "contextBundleRead")),
		"paths_read":                asStringList(pick(raw, "paths_read", "pathsRead")),
		"critical_notes":            asStringList(pick(raw, "critical_notes", "criticalNotes")),
	}
}

func defaultRuleAcknowledgement() map[string]any {
	return map[string]any{
		"required_references_read":  false,
		"forbidden_drift_respected": false,
		"context_bundle_read":       false,
		"paths_read":                []string{},
		"critical_notes":            []string{},
	}
}

func normalizeUIVerification(value any) (map[string]any, error) {
	if value == nil {
		return defaultUIVerification(), nil
	}
	raw, ok := value.(map[string]any)
	if !ok {
		return nil, fmt.Errorf("ui_verification must be an object")
	}
	unsupported := []string{}
	for key := range raw {
		if !currentUIVerificationFields[key] {
			unsupported = append(unsupported, key)
		}
	}
	if len(unsupported) > 0 {
		sort.Strings(unsupported)
		return nil, fmt.Errorf("ui_verification contains unsupported fields: %s", strings.Join(unsupported, ", "))
	}
	result := defaultUIVerification()
	for _, key := range []string{
		"contract_check", "runtime_evidence", "visual_comparison", "fidelity_status",
		"reviewer", "approved_visual_ref", "approved_preview_sha256",
		"approved_manifest_sha256", "comparison_report_ref",
		"comparison_report_sha256", "comparison_tolerance",
	} {
		if rawValue, exists := raw[key]; exists {
			result[key] = asString(rawValue)
		}
	}
	for _, key := range []string{"implementation_capture_refs", "covered_decision_ids", "structural_differences", "visual_differences"} {
		if rawValue, exists := raw[key]; exists {
			result[key] = asStringList(rawValue)
		}
	}
	if rawValue, exists := raw["accepted_deviations"]; exists {
		result["accepted_deviations"] = normalizeEvidenceItems(rawValue)
	}
	return result, nil
}

func defaultUIVerification() map[string]any {
	return map[string]any{
		"contract_check":              "not-run",
		"runtime_evidence":            "not-run",
		"visual_comparison":           "unavailable",
		"fidelity_status":             "not-applicable",
		"reviewer":                    "agent",
		"approved_visual_ref":         "",
		"approved_preview_sha256":     "",
		"approved_manifest_sha256":    "",
		"comparison_report_ref":       "",
		"comparison_report_sha256":    "",
		"implementation_capture_refs": []string{},
		"covered_decision_ids":        []string{},
		"structural_differences":      []string{},
		"visual_differences":          []string{},
		"comparison_tolerance":        "",
		"accepted_deviations":         []map[string]string{},
	}
}

func normalizeUIEvidence(value any) ([]map[string]string, error) {
	if value == nil {
		return []map[string]string{}, nil
	}
	raw, ok := value.([]any)
	if !ok {
		return nil, fmt.Errorf("ui_evidence must be a list")
	}
	normalized := []map[string]string{}
	for index, item := range raw {
		record, ok := item.(map[string]any)
		if !ok {
			return nil, fmt.Errorf("ui_evidence entries must be objects")
		}
		evidence := stringifyObject(record)
		kind := evidence["kind"]
		ref := evidence["ref"]
		if !currentUIEvidenceKinds[kind] {
			if kind == "" {
				kind = "<blank>"
			}
			return nil, fmt.Errorf("ui_evidence[%d] uses unsupported kind: %s", index, kind)
		}
		if ref == "" {
			return nil, fmt.Errorf("ui_evidence[%d] requires ref", index)
		}
		normalized = append(normalized, evidence)
	}
	return normalized, nil
}

func normalizeEvidenceItems(value any) []map[string]string {
	raw, ok := value.([]any)
	if !ok {
		return []map[string]string{}
	}
	normalized := []map[string]string{}
	for _, item := range raw {
		record, ok := item.(map[string]any)
		if !ok {
			continue
		}
		evidence := stringifyObject(record)
		if len(evidence) > 0 {
			normalized = append(normalized, evidence)
		}
	}
	return normalized
}

func normalizeObjectList(value any) []map[string]any {
	raw, ok := value.([]any)
	if !ok {
		return []map[string]any{}
	}
	normalized := []map[string]any{}
	for _, item := range raw {
		record, ok := item.(map[string]any)
		if ok {
			normalized = append(normalized, record)
		}
	}
	return normalized
}

func stringifyObject(record map[string]any) map[string]string {
	normalized := map[string]string{}
	for key, rawValue := range record {
		key = strings.TrimSpace(key)
		value := strings.TrimSpace(asString(rawValue))
		if key != "" && value != "" {
			normalized[key] = value
		}
	}
	return normalized
}

func asStringList(value any) []string {
	switch typed := value.(type) {
	case nil:
		return []string{}
	case string:
		stripped := strings.TrimSpace(typed)
		if stripped == "" {
			return []string{}
		}
		return []string{stripped}
	case []any:
		values := []string{}
		for _, item := range typed {
			text := strings.TrimSpace(asString(item))
			if text != "" {
				values = append(values, text)
			}
		}
		return values
	default:
		text := strings.TrimSpace(asString(value))
		if text == "" {
			return []string{}
		}
		return []string{text}
	}
}

func pick(payload map[string]any, keys ...string) any {
	for _, key := range keys {
		if value, exists := payload[key]; exists {
			return value
		}
	}
	return nil
}

func asString(value any) string {
	switch typed := value.(type) {
	case nil:
		return ""
	case string:
		return typed
	default:
		return fmt.Sprint(typed)
	}
}

func boolValue(value any) bool {
	typed, ok := value.(bool)
	return ok && typed
}

func resolveProjectContainedPath(projectRoot, value string) (string, error) {
	value = strings.TrimSpace(value)
	if value == "" {
		return "", fmt.Errorf("path is required")
	}
	root, err := filepath.Abs(projectRoot)
	if err != nil {
		return "", err
	}
	var absolute string
	if filepath.IsAbs(value) {
		absolute = value
	} else {
		absolute = filepath.Join(root, filepath.FromSlash(value))
	}
	absolute, err = filepath.Abs(absolute)
	if err != nil {
		return "", err
	}
	relative, err := filepath.Rel(root, absolute)
	if err != nil || relative == ".." || strings.HasPrefix(relative, ".."+string(filepath.Separator)) {
		return "", fmt.Errorf("path must stay inside the project root")
	}
	secured, err := secureProjectPath(root, filepath.ToSlash(relative))
	if err != nil {
		return "", err
	}
	return secured, nil
}

func writeJSONAtomic(path string, payload map[string]any) error {
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		return err
	}
	raw, err := json.MarshalIndent(payload, "", "  ")
	if err != nil {
		return err
	}
	raw = append(raw, '\n')
	temp, err := os.CreateTemp(filepath.Dir(path), "."+filepath.Base(path)+".*.tmp")
	if err != nil {
		return err
	}
	tempPath := temp.Name()
	defer os.Remove(tempPath)
	if _, err := temp.Write(raw); err != nil {
		_ = temp.Close()
		return err
	}
	if err := temp.Sync(); err != nil {
		_ = temp.Close()
		return err
	}
	if err := temp.Close(); err != nil {
		return err
	}
	return replaceFile(tempPath, path)
}

func writeResultError(stdout io.Writer, status, summary string) int {
	env := NewEnvelope(status, summary)
	env.Blockers = append(env.Blockers, summary)
	return writeEnvelope(stdout, env)
}
