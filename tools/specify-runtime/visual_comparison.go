package main

import (
	"errors"
	"fmt"
	"path/filepath"
	"reflect"
	"strings"
)

const visualComparisonSchema = "spec-kit-visual-comparison-v1"

var visualComparisonInputFields = map[string]bool{
	"entry_point": true, "implementation_revision": true,
	"capture_refs": true, "structure_snapshot_refs": true, "runtime_diagnostic_refs": true,
	"matrix": true, "verdict": true, "reviewer": true,
}

var visualComparisonMatrixFields = map[string]bool{
	"viewport": true, "color_mode": true, "motion_mode": true, "state": true,
	"approved_target": true, "implementation_capture_ref": true,
	"covered_decision_ids": true, "covered_handoff_contract_ids": true,
	"structural_differences": true, "visual_differences": true, "result": true,
}

var passingVisualComparisonStatuses = map[string]bool{
	"pass": true, "passed": true, "success": true, "approved": true,
	"match": true, "matched": true, "matches": true,
}

func (service evidenceService) visualCompare(args []string, raw map[string]any) Envelope {
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
		return evidenceBlockedError("visual comparison requires a ready CLI-owned task index", firstVisualComparisonError(err, "task-index.json must use version 2 with status ready"))
	}
	_, task, err := findImplementTask(index, taskID)
	if err != nil {
		return evidenceUsageError(err.Error())
	}
	uiContract, ok := task["ui_contract"].(map[string]any)
	if !ok || strings.EqualFold(strings.TrimSpace(anyString(uiContract["fidelity_level"])), "none") {
		return evidenceUsageError("visual comparison requires a UI-bearing task contract")
	}
	template, err := readImplementJSONMap(filepath.Join(root, ".specify", "templates", "visual-comparison-template.json"))
	if err != nil {
		return evidenceBlockedError("visual comparison template is unavailable", err)
	}
	if err := validateVisualComparisonTemplate(template); err != nil {
		return evidenceBlockedError("visual comparison template is unsafe", err)
	}
	report, err := buildVisualComparisonReport(taskID, uiContract, template, raw)
	if err != nil {
		return evidenceUsageError(err.Error())
	}
	rendered, err := marshalReviewAcceptJSON(report)
	if err != nil {
		return evidenceBlockedError("visual comparison report cannot be rendered", err)
	}
	featureRef := "visual-comparison-" + taskID + ".json"
	projectRelativeFeature, err := filepath.Rel(root, feature)
	if err != nil {
		return evidenceBlockedError("visual comparison feature path is invalid", err)
	}
	canonicalRef := filepath.ToSlash(filepath.Join(projectRelativeFeature, featureRef))
	metadata, registered := LookupArtifactType(canonicalRef)
	if !registered || metadata.TypeID != "feature-visual-comparison" || metadata.Owner != "specify-runtime evidence visual-compare" {
		return evidenceBlockedError("visual comparison path is not owned by its specialized CLI", errors.New(canonicalRef))
	}
	reportPath, err := secureProjectPath(root, canonicalRef)
	if err != nil {
		return evidenceBlockedError("visual comparison path is unsafe", err)
	}
	receipt, err := applyFileTransaction(root, "visual-comparison", []fileTransactionUpdate{{Path: reportPath, Content: rendered, Perm: 0o644}})
	if err != nil {
		return evidenceBlockedError("visual comparison report could not be written atomically", err)
	}
	env := NewEnvelope("ok", "visual comparison report materialized")
	env.Data = map[string]any{
		"task_id": taskID, "comparison_report_ref": featureRef,
		"comparison_report_sha256": fileContentSHA256(rendered), "canonical_path": canonicalRef,
		"transaction_receipt_ref": receipt.ReceiptRef,
	}
	env.ShowArgv = []string{"specify-runtime", "artifact", "show", "--path", canonicalRef, "--view", "summary", "--format", "json"}
	return env
}

func validateVisualComparisonTemplate(template map[string]any) error {
	expectedTop := map[string]bool{
		"schema": true, "task_id": true, "entry_point": true, "approved": true,
		"implementation": true, "matrix": true, "comparison_tolerance": true,
		"accepted_deviations": true, "decision_coverage": true, "verdict": true, "reviewer": true,
	}
	if err := exactVisualComparisonFields(template, expectedTop, "visual comparison template"); err != nil {
		return err
	}
	if template["schema"] != visualComparisonSchema || template["task_id"] != nil || template["entry_point"] != nil || template["verdict"] != "pending-human-review" || template["reviewer"] != nil {
		return errors.New("template must preserve canonical blocked readiness defaults")
	}
	approved, ok := template["approved"].(map[string]any)
	if !ok || exactVisualComparisonFields(approved, map[string]bool{
		"visual_ref": true, "preview_sha256": true, "manifest_sha256": true,
		"handoff_ref": true, "handoff_sha256": true, "direction_id": true,
		"decision_ids": true, "handoff_contract_ids": true,
	}, "visual comparison template approved") != nil {
		return errors.New("template approved projection is invalid")
	}
	implementation, ok := template["implementation"].(map[string]any)
	if !ok || exactVisualComparisonFields(implementation, map[string]bool{
		"revision": true, "capture_refs": true, "structure_snapshot_refs": true, "runtime_diagnostic_refs": true,
	}, "visual comparison template implementation") != nil {
		return errors.New("template implementation projection is invalid")
	}
	matrix, ok := template["matrix"].([]any)
	if !ok || len(matrix) != 1 {
		return errors.New("template matrix must contain one pending row")
	}
	row, ok := matrix[0].(map[string]any)
	if !ok || exactVisualComparisonFields(row, visualComparisonMatrixFields, "visual comparison template matrix row") != nil || row["result"] != "pending" {
		return errors.New("template matrix row is invalid")
	}
	return nil
}

func buildVisualComparisonReport(taskID string, uiContract, template, raw map[string]any) (map[string]any, error) {
	for field := range raw {
		if !visualComparisonInputFields[field] {
			return nil, fmt.Errorf("visual comparison input contains runtime-owned or unsupported field %q", field)
		}
	}
	entryPoint := strings.TrimSpace(anyString(raw["entry_point"]))
	revision := strings.TrimSpace(anyString(raw["implementation_revision"]))
	reviewer := strings.TrimSpace(anyString(raw["reviewer"]))
	verdict := normalizeVisualComparisonStatus(raw["verdict"])
	if entryPoint == "" || revision == "" || reviewer == "" {
		return nil, errors.New("entry_point, implementation_revision, and reviewer are required")
	}
	if !passingVisualComparisonStatuses[verdict] {
		return nil, errors.New("verdict must explicitly record a passing visual comparison")
	}
	captureRefs, err := anyStringList(raw["capture_refs"], "capture_refs", true)
	if err != nil {
		return nil, err
	}
	structureRefs, err := anyStringList(raw["structure_snapshot_refs"], "structure_snapshot_refs", true)
	if err != nil {
		return nil, err
	}
	runtimeRefs, err := anyStringList(raw["runtime_diagnostic_refs"], "runtime_diagnostic_refs", true)
	if err != nil {
		return nil, err
	}
	decisionIDs, err := anyStringList(uiContract["design_decision_ids"], "ui_contract.design_decision_ids", true)
	if err != nil {
		return nil, err
	}
	handoffIDs, err := anyStringList(uiContract["handoff_contract_ids"], "ui_contract.handoff_contract_ids", false)
	if err != nil {
		return nil, err
	}
	approvedVisualRef, err := requiredVisualComparisonContractText(uiContract, "approved_visual_ref")
	if err != nil {
		return nil, err
	}
	approvedPreviewSHA, err := requiredVisualComparisonDigest(uiContract, "approved_preview_sha256")
	if err != nil {
		return nil, err
	}
	approvedManifestSHA, err := requiredVisualComparisonDigest(uiContract, "approved_manifest_sha256")
	if err != nil {
		return nil, err
	}
	approvedHandoffRef, err := requiredVisualComparisonContractText(uiContract, "approved_handoff_ref")
	if err != nil {
		return nil, err
	}
	approvedHandoffSHA, err := requiredVisualComparisonDigest(uiContract, "approved_handoff_sha256")
	if err != nil {
		return nil, err
	}
	tolerance, ok := uiContract["comparison_tolerance"].(map[string]any)
	if !ok || len(tolerance) == 0 {
		return nil, errors.New("ui_contract.comparison_tolerance must be a non-empty object")
	}
	acceptedDeviations, ok := uiContract["accepted_deviations"].([]any)
	if !ok {
		return nil, errors.New("ui_contract.accepted_deviations must be an array")
	}
	matrix, err := normalizeVisualComparisonMatrix(raw["matrix"], approvedVisualRef, captureRefs, decisionIDs, handoffIDs)
	if err != nil {
		return nil, err
	}
	directionID := ""
	if _, fragment, found := strings.Cut(approvedVisualRef, "#"); found {
		directionID = strings.TrimSpace(fragment)
	}
	report := cloneJSONMap(template)
	report["schema"] = visualComparisonSchema
	report["task_id"] = taskID
	report["entry_point"] = entryPoint
	report["approved"] = map[string]any{
		"visual_ref": approvedVisualRef, "preview_sha256": approvedPreviewSHA,
		"manifest_sha256": approvedManifestSHA, "handoff_ref": approvedHandoffRef,
		"handoff_sha256": approvedHandoffSHA, "direction_id": directionID,
		"decision_ids": stringsToAny(decisionIDs), "handoff_contract_ids": stringsToAny(handoffIDs),
	}
	report["implementation"] = map[string]any{
		"revision": revision, "capture_refs": stringsToAny(captureRefs),
		"structure_snapshot_refs": stringsToAny(structureRefs), "runtime_diagnostic_refs": stringsToAny(runtimeRefs),
	}
	report["matrix"] = matrix
	report["comparison_tolerance"] = cloneJSONValue(tolerance)
	report["accepted_deviations"] = cloneJSONValue(acceptedDeviations)
	report["decision_coverage"] = stringsToAny(decisionIDs)
	report["verdict"] = "passed"
	report["reviewer"] = reviewer
	return report, nil
}

func normalizeVisualComparisonMatrix(value any, approvedVisualRef string, captureRefs, decisionIDs, handoffIDs []string) ([]any, error) {
	rawRows, ok := value.([]any)
	if !ok || len(rawRows) == 0 {
		return nil, errors.New("matrix must be a non-empty array")
	}
	allowedCaptures := visualComparisonStringSet(captureRefs)
	allowedDecisions := visualComparisonStringSet(decisionIDs)
	allowedHandoffs := visualComparisonStringSet(handoffIDs)
	coveredDecisions := map[string]bool{}
	coveredHandoffs := map[string]bool{}
	rows := make([]any, 0, len(rawRows))
	for index, value := range rawRows {
		raw, ok := value.(map[string]any)
		if !ok {
			return nil, fmt.Errorf("matrix[%d] must be an object", index)
		}
		if err := exactVisualComparisonFieldsAllowed(raw, visualComparisonMatrixFields, fmt.Sprintf("matrix[%d]", index)); err != nil {
			return nil, err
		}
		viewport := strings.TrimSpace(anyString(raw["viewport"]))
		state := strings.TrimSpace(anyString(raw["state"]))
		capture := strings.TrimSpace(anyString(raw["implementation_capture_ref"]))
		if viewport == "" || state == "" || capture == "" {
			return nil, fmt.Errorf("matrix[%d] requires viewport, state, and implementation_capture_ref", index)
		}
		if !allowedCaptures[capture] {
			return nil, fmt.Errorf("matrix[%d] references a capture outside capture_refs", index)
		}
		rowDecisionIDs, err := anyStringList(raw["covered_decision_ids"], fmt.Sprintf("matrix[%d].covered_decision_ids", index), false)
		if err != nil {
			return nil, err
		}
		rowHandoffIDs, err := anyStringList(raw["covered_handoff_contract_ids"], fmt.Sprintf("matrix[%d].covered_handoff_contract_ids", index), false)
		if err != nil {
			return nil, err
		}
		for _, id := range rowDecisionIDs {
			if !allowedDecisions[id] {
				return nil, fmt.Errorf("matrix[%d] references unknown design decision %s", index, id)
			}
			coveredDecisions[id] = true
		}
		for _, id := range rowHandoffIDs {
			if !allowedHandoffs[id] {
				return nil, fmt.Errorf("matrix[%d] references unknown handoff contract %s", index, id)
			}
			coveredHandoffs[id] = true
		}
		if !passingVisualComparisonStatuses[normalizeVisualComparisonStatus(raw["result"])] {
			return nil, fmt.Errorf("matrix[%d].result must explicitly pass", index)
		}
		structural, err := visualComparisonArray(raw, "structural_differences")
		if err != nil {
			return nil, fmt.Errorf("matrix[%d]: %w", index, err)
		}
		visual, err := visualComparisonArray(raw, "visual_differences")
		if err != nil {
			return nil, fmt.Errorf("matrix[%d]: %w", index, err)
		}
		rows = append(rows, map[string]any{
			"viewport": viewport, "color_mode": visualComparisonNullableText(raw["color_mode"]),
			"motion_mode": visualComparisonNullableText(raw["motion_mode"]), "state": state,
			"approved_target":            visualComparisonTextOr(raw["approved_target"], approvedVisualRef),
			"implementation_capture_ref": capture, "covered_decision_ids": stringsToAny(rowDecisionIDs),
			"covered_handoff_contract_ids": stringsToAny(rowHandoffIDs),
			"structural_differences":       cloneJSONValue(structural), "visual_differences": cloneJSONValue(visual),
			"result": "passed",
		})
	}
	if !reflect.DeepEqual(coveredDecisions, allowedDecisions) {
		return nil, errors.New("matrix must exactly cover ui_contract.design_decision_ids")
	}
	if !reflect.DeepEqual(coveredHandoffs, allowedHandoffs) {
		return nil, errors.New("matrix must exactly cover ui_contract.handoff_contract_ids")
	}
	return rows, nil
}

func exactVisualComparisonFields(value map[string]any, expected map[string]bool, label string) error {
	if len(value) != len(expected) {
		return fmt.Errorf("%s fields do not match the canonical template", label)
	}
	return exactVisualComparisonFieldsAllowed(value, expected, label)
}

func exactVisualComparisonFieldsAllowed(value map[string]any, allowed map[string]bool, label string) error {
	for field := range value {
		if !allowed[field] {
			return fmt.Errorf("%s contains unsupported field %q", label, field)
		}
	}
	return nil
}

func visualComparisonArray(value map[string]any, field string) ([]any, error) {
	raw, exists := value[field]
	if !exists {
		return []any{}, nil
	}
	list, ok := raw.([]any)
	if !ok {
		return nil, fmt.Errorf("%s must be an array", field)
	}
	return list, nil
}

func requiredVisualComparisonContractText(contract map[string]any, field string) (string, error) {
	value := strings.TrimSpace(anyString(contract[field]))
	if value == "" {
		return "", fmt.Errorf("ui_contract.%s is required", field)
	}
	return value, nil
}

func requiredVisualComparisonDigest(contract map[string]any, field string) (string, error) {
	value, err := requiredVisualComparisonContractText(contract, field)
	if err != nil {
		return "", err
	}
	if !reviewSHA256RE.MatchString(value) {
		return "", fmt.Errorf("ui_contract.%s must be a sha256 digest", field)
	}
	return value, nil
}

func normalizeVisualComparisonStatus(value any) string {
	return strings.ReplaceAll(strings.ToLower(strings.TrimSpace(anyString(value))), "_", "-")
}

func visualComparisonStringSet(values []string) map[string]bool {
	result := map[string]bool{}
	for _, value := range values {
		result[value] = true
	}
	return result
}

func visualComparisonNullableText(value any) any {
	text := strings.TrimSpace(anyString(value))
	if text == "" {
		return nil
	}
	return text
}

func visualComparisonTextOr(value any, fallback string) string {
	if text := strings.TrimSpace(anyString(value)); text != "" {
		return text
	}
	return fallback
}

func firstVisualComparisonError(err error, fallback string) error {
	if err != nil {
		return err
	}
	return errors.New(fallback)
}
