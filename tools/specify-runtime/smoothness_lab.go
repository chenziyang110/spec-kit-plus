package main

import (
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"reflect"
	"strings"
)

const (
	smoothnessManifestSchema = "spec-kit-smoothness-lab-manifest-v1"
	smoothnessResultSchema   = "spec-kit-smoothness-lab-result-v1"
	smoothnessReportSchema   = "spec-kit-smoothness-lab-report-v1"
)

var smoothnessDefaultBudgets = map[string]any{
	"inp_ms": 200, "long_task_ms": 50, "cls": 0.1,
	"animation_dropped_frame_pct": 5,
	"bundle_delta_kb":             0,
}

var smoothnessScenarioFailureCodes = map[string]string{
	"focus-continuity":            "focus-continuity-failed",
	"scroll-continuity":           "scroll-continuity-failed",
	"selection-scroll-continuity": "selection-scroll-continuity-failed",
	"pending-cancel-feedback":     "pending-cancel-feedback-failed",
	"duplicate-activation":        "duplicate-activation-failed",
	"reduced-motion":              "reduced-motion-failed",
	"large-data-performance":      "large-data-performance-failed",
	"editing-input-continuity":    "editing-input-continuity-failed",
	"interruption-safe-motion":    "interruption-safe-motion-failed",
}

func (service evidenceService) smoothnessManifest(args []string) Envelope {
	root, feature, err := taskControlFeature(args)
	if err != nil {
		return evidenceUsageError(err.Error())
	}
	taskID, err := normalizeTaskControlID(optionValue(args, "--task-id", ""))
	if err != nil {
		return evidenceUsageError(err.Error())
	}
	index, err := readImplementJSONMap(filepath.Join(feature, "task-index.json"))
	if err != nil || intFromAny(index["version"]) != 2 || index["status"] != "ready" {
		return evidenceBlockedError("smoothness manifest requires a ready CLI-owned task index", firstVisualComparisonError(err, "task-index.json must use version 2 with status ready"))
	}
	_, task, err := findImplementTask(index, taskID)
	if err != nil {
		return evidenceUsageError(err.Error())
	}
	ids, err := smoothnessTaskIDs(task)
	if err != nil {
		return evidenceUsageError(err.Error())
	}
	if len(ids) == 0 {
		env := NewEnvelope("ok", "smoothness lab not applicable")
		env.Data = map[string]any{"task_id": taskID, "applicable": false, "status": "not-applicable", "smoothness_acceptance_ids": []any{}}
		return env
	}
	manifest, err := buildSmoothnessManifest(root, feature, taskID, index, task, ids)
	if err != nil {
		return evidenceUsageError(err.Error())
	}
	rendered, err := marshalReviewAcceptJSON(manifest)
	if err != nil {
		return evidenceBlockedError("smoothness manifest cannot be rendered", err)
	}
	manifestRef := smoothnessManifestRef(taskID)
	manifestPath := filepath.Join(feature, filepath.FromSlash(manifestRef))
	receipt, err := applyFileTransaction(root, "smoothness-manifest", []fileTransactionUpdate{{Path: manifestPath, Content: rendered, Perm: 0o644}})
	if err != nil {
		return evidenceBlockedError("smoothness manifest could not be written atomically", err)
	}
	env := NewEnvelope("ok", "smoothness manifest materialized")
	env.Data = map[string]any{
		"task_id": taskID, "applicable": true, "status": "ready",
		"manifest_ref": manifestRef, "manifest_sha256": fileContentSHA256(rendered),
		"smoothness_acceptance_ids": stringsToAny(ids),
		"transaction_receipt_ref":   receipt.ReceiptRef,
	}
	env.ShowArgv = []string{"specify-runtime", "artifact", "show", "--path", smoothnessCanonicalPath(root, feature, manifestRef), "--view", "summary", "--format", "json"}
	return env
}

func (service evidenceService) smoothnessValidate(args []string, raw map[string]any) Envelope {
	root, feature, err := taskControlFeature(args)
	if err != nil {
		return evidenceUsageError(err.Error())
	}
	taskID, err := normalizeTaskControlID(optionValue(args, "--task-id", ""))
	if err != nil {
		return evidenceUsageError(err.Error())
	}
	manifestRef := filepath.ToSlash(strings.TrimSpace(optionValue(args, "--manifest", "")))
	if manifestRef == "" {
		return evidenceUsageError("smoothness validation requires --manifest")
	}
	manifestPath, err := secureFeatureRelativePath(feature, manifestRef)
	if err != nil {
		return evidenceUsageError("smoothness manifest path is unsafe")
	}
	manifest, err := readImplementJSONMap(manifestPath)
	if err != nil {
		return evidenceBlockedError("smoothness manifest is unavailable", err)
	}
	diagnostics := validateSmoothnessResult(taskID, manifest, optionalFileSHA256(manifestPath), raw)
	if source, ok := manifest["source"].(map[string]any); !ok ||
		strings.TrimSpace(anyString(source["task_index_sha256"])) != optionalFileSHA256(filepath.Join(feature, "task-index.json")) {
		diagnostics = append(diagnostics, "stale-manifest")
	}
	diagnostics = uniqueSmoothnessDiagnostics(diagnostics)
	if len(diagnostics) > 0 {
		env := NewEnvelope("error", strings.Join(diagnostics, "; "))
		env.Data = map[string]any{"task_id": taskID, "diagnostics": stringsToAny(diagnostics)}
		return env
	}
	ids := smoothnessStringListFromAny(manifest["smoothness_acceptance_ids"])
	report := map[string]any{
		"schema":                            smoothnessReportSchema,
		"task_id":                           taskID,
		"verdict":                           "passed",
		"manifest_ref":                      manifestRef,
		"manifest_sha256":                   optionalFileSHA256(manifestPath),
		"covered_smoothness_acceptance_ids": stringsToAny(ids),
		"evidence_refs":                     cloneJSONValue(raw["evidence_refs"]),
		"scenario_results":                  cloneJSONValue(raw["scenario_results"]),
		"performance":                       cloneJSONValue(raw["performance"]),
		"source":                            map[string]any{"result_schema": smoothnessResultSchema},
	}
	rendered, err := marshalReviewAcceptJSON(report)
	if err != nil {
		return evidenceBlockedError("smoothness report cannot be rendered", err)
	}
	reportRef := smoothnessReportRef(taskID)
	reportPath := filepath.Join(feature, filepath.FromSlash(reportRef))
	receipt, err := applyFileTransaction(root, "smoothness-lab", []fileTransactionUpdate{{Path: reportPath, Content: rendered, Perm: 0o644}})
	if err != nil {
		return evidenceBlockedError("smoothness report could not be written atomically", err)
	}
	env := NewEnvelope("ok", "smoothness lab report materialized")
	env.Data = map[string]any{
		"task_id": taskID, "report_ref": reportRef, "report_sha256": fileContentSHA256(rendered),
		"covered_smoothness_acceptance_ids": stringsToAny(ids),
		"ui_verification_patch": map[string]any{
			"covered_smoothness_acceptance_ids": stringsToAny(ids),
			"smoothness_lab_report_ref":         reportRef,
			"smoothness_lab_report_sha256":      fileContentSHA256(rendered),
		},
		"transaction_receipt_ref": receipt.ReceiptRef,
	}
	env.ShowArgv = []string{"specify-runtime", "artifact", "show", "--path", smoothnessCanonicalPath(root, feature, reportRef), "--view", "summary", "--format", "json"}
	return env
}

func buildSmoothnessManifest(root, feature, taskID string, index, task map[string]any, ids []string) (map[string]any, error) {
	entrypoint, err := smoothnessEntrypoint(index, task)
	if err != nil {
		return nil, err
	}
	viewports := []any{"desktop", "mobile"}
	budgets := cloneJSONMap(smoothnessDefaultBudgets)
	if ui, ok := task["ui_contract"].(map[string]any); ok {
		if rows, ok := ui["responsive_matrix"].([]any); ok {
			selected := []string{}
			seen := map[string]bool{}
			for _, raw := range rows {
				row, ok := raw.(map[string]any)
				if !ok {
					continue
				}
				label := strings.TrimSpace(anyString(firstImplementTaskValue(row["profile_id"], row["label"], row["viewport"])))
				if label != "" && !seen[label] {
					selected = append(selected, label)
					seen[label] = true
				}
			}
			if len(selected) > 0 {
				viewports = stringsToAny(selected)
			}
		}
		if usability, ok := ui["usability_validation"].(map[string]any); ok {
			if configured, ok := usability["performance_budgets"].(map[string]any); ok {
				for key := range budgets {
					if value, valid := smoothnessNumber(configured[key]); valid && value >= 0 {
						budgets[key] = value
					}
				}
			}
		}
	}
	return map[string]any{
		"schema":                    smoothnessManifestSchema,
		"task_id":                   taskID,
		"smoothness_acceptance_ids": stringsToAny(ids),
		"required_evidence":         []any{"structure_snapshot", "visual_capture", "runtime_diagnostics"},
		"entrypoint":                entrypoint,
		"viewports":                 viewports,
		"performance_budgets":       budgets,
		"source": map[string]any{
			"task_index_ref":    "task-index.json",
			"task_index_sha256": optionalFileSHA256(filepath.Join(feature, "task-index.json")),
			"feature_ref":       smoothnessCanonicalPath(root, feature, ""),
		},
	}, nil
}

func validateSmoothnessResult(taskID string, manifest map[string]any, manifestSHA string, raw map[string]any) []string {
	var diagnostics []string
	if manifest["schema"] != smoothnessManifestSchema || manifest["task_id"] != taskID {
		diagnostics = append(diagnostics, "stale-manifest")
	}
	if raw["schema"] != smoothnessResultSchema {
		diagnostics = append(diagnostics, "invalid-result-schema")
	}
	if strings.TrimSpace(anyString(raw["manifest_sha256"])) != manifestSHA {
		diagnostics = append(diagnostics, "stale-manifest")
	}
	ids := smoothnessStringListFromAny(manifest["smoothness_acceptance_ids"])
	covered := smoothnessStringListFromAny(raw["covered_smoothness_acceptance_ids"])
	if len(ids) != len(smoothnessStringSet(ids)) || len(covered) != len(smoothnessStringSet(covered)) || !reflect.DeepEqual(smoothnessStringSet(ids), smoothnessStringSet(covered)) {
		diagnostics = append(diagnostics, "smoothness-id-mismatch")
	}
	evidenceKinds := smoothnessEvidenceKinds(raw["evidence_refs"])
	for _, required := range []string{"structure_snapshot", "visual_capture", "runtime_diagnostics"} {
		if !evidenceKinds[required] {
			diagnostics = append(diagnostics, "missing-"+strings.ReplaceAll(required, "_", "-"))
		}
	}
	diagnostics = append(diagnostics, smoothnessScenarioDiagnostics(ids, raw["scenario_results"])...)
	diagnostics = append(diagnostics, smoothnessBudgetDiagnostics(manifest["performance_budgets"], raw["performance"])...)
	return uniqueSmoothnessDiagnostics(diagnostics)
}

func smoothnessTaskIDs(task map[string]any) ([]string, error) {
	ui, ok := task["ui_contract"].(map[string]any)
	if !ok {
		return nil, errors.New("smoothness lab requires a UI task contract")
	}
	validation, ok := ui["usability_validation"].(map[string]any)
	if !ok {
		return []string{}, nil
	}
	return anyStringList(validation["smoothness_acceptance_ids"], "ui_contract.usability_validation.smoothness_acceptance_ids", false)
}

func smoothnessEntrypoint(index, task map[string]any) (map[string]any, error) {
	entrypoints, _ := index["official_entrypoints"].([]any)
	entrypointIDs := map[string]bool{}
	if ui, ok := task["ui_contract"].(map[string]any); ok {
		if surfaces, ok := ui["surface_catalog"].([]any); ok {
			for _, raw := range surfaces {
				surface, ok := raw.(map[string]any)
				if !ok {
					return nil, errors.New("smoothness lab requires surface entrypoint bindings")
				}
				entrypointID := strings.TrimSpace(anyString(surface["entrypoint_id"]))
				if entrypointID == "" {
					return nil, errors.New("smoothness lab requires a bound official entrypoint")
				}
				entrypointIDs[entrypointID] = true
			}
		}
	}
	if len(entrypointIDs) != 1 {
		return nil, errors.New("smoothness lab surfaces must bind exactly one official entrypoint")
	}
	entrypointID := ""
	for value := range entrypointIDs {
		entrypointID = value
	}
	for _, value := range entrypoints {
		entry, ok := value.(map[string]any)
		if !ok {
			continue
		}
		if anyString(entry["id"]) == entrypointID {
			return map[string]any{
				"id": anyString(entry["id"]), "kind": anyString(entry["kind"]),
				"route": anyString(entry["route"]), "url": anyString(entry["url"]),
			}, nil
		}
	}
	return nil, errors.New("smoothness lab requires a bound official entrypoint")
}

func smoothnessScenarioDiagnostics(expectedIDs []string, value any) []string {
	var diagnostics []string
	rows, _ := value.([]any)
	verdicts := map[string][]string{}
	expected := smoothnessStringSet(expectedIDs)
	for _, value := range rows {
		row, ok := value.(map[string]any)
		if !ok {
			continue
		}
		id := strings.TrimSpace(anyString(row["smoothness_acceptance_id"]))
		verdict := strings.ToLower(strings.TrimSpace(anyString(row["verdict"])))
		if !expected[id] {
			diagnostics = append(diagnostics, "smoothness-id-mismatch")
		}
		verdicts[id] = append(verdicts[id], verdict)
		if verdict != "pass" && verdict != "passed" && verdict != "success" && verdict != "approved" {
			if code := smoothnessScenarioFailureCodes[id]; code != "" {
				diagnostics = append(diagnostics, code)
			} else if id != "" {
				diagnostics = append(diagnostics, id+"-failed")
			}
		}
	}
	for _, id := range expectedIDs {
		if len(verdicts[id]) != 1 {
			if code := smoothnessScenarioFailureCodes[id]; code != "" {
				diagnostics = append(diagnostics, code)
			} else {
				diagnostics = append(diagnostics, id+"-failed")
			}
		}
	}
	return diagnostics
}

func smoothnessBudgetDiagnostics(budgetValue, performanceValue any) []string {
	budgets, _ := budgetValue.(map[string]any)
	performance, _ := performanceValue.(map[string]any)
	checks := []struct {
		key  string
		code string
	}{
		{"inp_ms", "inp-budget-exceeded"},
		{"long_task_ms", "long-task-budget-exceeded"},
		{"cls", "cls-budget-exceeded"},
		{"animation_dropped_frame_pct", "animation-budget-exceeded"},
		{"bundle_delta_kb", "bundle-delta-budget-exceeded"},
	}
	var diagnostics []string
	for _, check := range checks {
		observed, observedOK := smoothnessNumber(performance[check.key])
		budget, budgetOK := smoothnessNumber(budgets[check.key])
		if !observedOK || !budgetOK {
			diagnostics = append(diagnostics, "missing-"+strings.ReplaceAll(check.key, "_", "-"))
			continue
		}
		if observed > budget {
			diagnostics = append(diagnostics, check.code)
		}
	}
	return diagnostics
}

func smoothnessEvidenceKinds(value any) map[string]bool {
	kinds := map[string]bool{}
	rows, _ := value.([]any)
	for _, value := range rows {
		row, ok := value.(map[string]any)
		if !ok {
			continue
		}
		kind := strings.TrimSpace(anyString(row["kind"]))
		ref := strings.TrimSpace(anyString(row["ref"]))
		if kind != "" && ref != "" {
			kinds[kind] = true
		}
	}
	return kinds
}

func validatePersistedSmoothnessReport(feature string, task map[string]any, expectedIDs []string, reportRef, reportSHA256 string) error {
	taskID := strings.ToUpper(strings.TrimSpace(anyString(task["id"])))
	if reportRef != smoothnessReportRef(taskID) {
		return fmt.Errorf("smoothness lab report must use the runtime-owned canonical task path")
	}
	reportPath, err := secureFeatureRelativePath(feature, reportRef)
	if err != nil {
		return fmt.Errorf("smoothness lab report path is unsafe")
	}
	reportRaw, err := os.ReadFile(reportPath)
	if err != nil || taskControlSHA256(reportRaw) != reportSHA256 {
		return fmt.Errorf("smoothness lab report SHA-256 must bind the report")
	}
	var report map[string]any
	if err := json.Unmarshal(reportRaw, &report); err != nil {
		return fmt.Errorf("smoothness lab report must contain a JSON object")
	}
	if report["schema"] != smoothnessReportSchema || strings.ToUpper(strings.TrimSpace(anyString(report["task_id"]))) != taskID || strings.ToLower(strings.TrimSpace(anyString(report["verdict"]))) != "passed" {
		return fmt.Errorf("smoothness lab report identity or verdict is invalid")
	}
	manifestRef := filepath.ToSlash(strings.TrimSpace(anyString(report["manifest_ref"])))
	if manifestRef != smoothnessManifestRef(taskID) {
		return fmt.Errorf("smoothness lab report must bind the runtime-owned task manifest")
	}
	manifestPath, err := secureFeatureRelativePath(feature, manifestRef)
	if err != nil {
		return fmt.Errorf("smoothness lab manifest path is unsafe")
	}
	manifestRaw, err := os.ReadFile(manifestPath)
	if err != nil || taskControlSHA256(manifestRaw) != strings.TrimSpace(anyString(report["manifest_sha256"])) {
		return fmt.Errorf("smoothness lab report manifest SHA-256 must bind the manifest")
	}
	var manifest map[string]any
	if err := json.Unmarshal(manifestRaw, &manifest); err != nil {
		return fmt.Errorf("smoothness lab manifest must contain a JSON object")
	}
	indexPath := filepath.Join(feature, "task-index.json")
	index, err := readImplementJSONMap(indexPath)
	if err != nil {
		return fmt.Errorf("smoothness lab report requires the current task index")
	}
	_, currentTask, err := findImplementTask(index, taskID)
	if err != nil {
		return fmt.Errorf("smoothness lab report requires the current task contract")
	}
	expectedEntrypoint, err := smoothnessEntrypoint(index, currentTask)
	if err != nil {
		return err
	}
	if !reflect.DeepEqual(manifest["entrypoint"], expectedEntrypoint) {
		return fmt.Errorf("smoothness lab manifest entrypoint binding is stale")
	}
	reportSource, _ := report["source"].(map[string]any)
	validationInput := map[string]any{
		"schema":                            reportSource["result_schema"],
		"manifest_sha256":                   report["manifest_sha256"],
		"covered_smoothness_acceptance_ids": report["covered_smoothness_acceptance_ids"],
		"evidence_refs":                     report["evidence_refs"],
		"scenario_results":                  report["scenario_results"],
		"performance":                       report["performance"],
	}
	diagnostics := validateSmoothnessResult(taskID, manifest, taskControlSHA256(manifestRaw), validationInput)
	manifestIDs := smoothnessStringListFromAny(manifest["smoothness_acceptance_ids"])
	if len(expectedIDs) != len(smoothnessStringSet(expectedIDs)) || !reflect.DeepEqual(smoothnessStringSet(expectedIDs), smoothnessStringSet(manifestIDs)) {
		diagnostics = append(diagnostics, "smoothness-id-mismatch")
	}
	if source, ok := manifest["source"].(map[string]any); !ok || strings.TrimSpace(anyString(source["task_index_ref"])) != "task-index.json" || strings.TrimSpace(anyString(source["task_index_sha256"])) != optionalFileSHA256(indexPath) {
		diagnostics = append(diagnostics, "stale-manifest")
	}
	diagnostics = uniqueSmoothnessDiagnostics(diagnostics)
	if len(diagnostics) > 0 {
		return fmt.Errorf("smoothness lab report is invalid: %s", strings.Join(diagnostics, ", "))
	}
	return nil
}

func smoothnessStringListFromAny(value any) []string {
	values, _ := anyStringList(value, "smoothness list", false)
	return values
}

func smoothnessStringSet(values []string) map[string]bool {
	set := map[string]bool{}
	for _, value := range values {
		set[value] = true
	}
	return set
}

func uniqueSmoothnessDiagnostics(values []string) []string {
	seen := map[string]bool{}
	out := []string{}
	for _, value := range values {
		if value == "" || seen[value] {
			continue
		}
		seen[value] = true
		out = append(out, value)
	}
	return out
}

func smoothnessFloat(value any) float64 {
	number, _ := smoothnessNumber(value)
	return number
}

func smoothnessNumber(value any) (float64, bool) {
	switch typed := value.(type) {
	case float64:
		return typed, true
	case float32:
		return float64(typed), true
	case int:
		return float64(typed), true
	case int64:
		return float64(typed), true
	default:
		return 0, false
	}
}

func smoothnessManifestRef(taskID string) string {
	return "implementation-review/smoothness/smoothness-manifest-" + taskID + ".json"
}

func smoothnessReportRef(taskID string) string {
	return "implementation-review/smoothness/smoothness-lab-" + taskID + ".json"
}

func smoothnessCanonicalPath(root, feature, ref string) string {
	relative, err := filepath.Rel(root, filepath.Join(feature, filepath.FromSlash(ref)))
	if err != nil {
		return filepath.ToSlash(ref)
	}
	return filepath.ToSlash(relative)
}

func secureFeatureRelativePath(feature, ref string) (string, error) {
	if filepath.IsAbs(ref) || strings.Contains(ref, "\\") || strings.Contains(ref, "..") {
		return "", fmt.Errorf("unsafe path")
	}
	return filepath.Join(feature, filepath.FromSlash(ref)), nil
}
