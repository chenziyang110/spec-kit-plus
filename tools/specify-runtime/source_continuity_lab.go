package main

import (
	"errors"
	"path/filepath"
	"reflect"
	"sort"
	"strings"
)

const (
	sourceContinuityLabManifestSchema = "spec-kit-source-continuity-lab-manifest-v1"
	sourceContinuityLabResultSchema   = "spec-kit-source-continuity-lab-result-v1"
	sourceContinuityLabReportSchema   = "spec-kit-source-continuity-lab-report-v1"
)

var sourceContinuityLabCapabilities = []string{
	"surface-enumeration",
	"action-execution",
	"side-effect-observation",
	"asset-inspection",
	"visual-capture",
}

var sourceContinuityLabEvidenceKinds = []string{
	"structure_snapshot",
	"visual_capture",
	"runtime_diagnostics",
}

var sourceContinuityLabInputFields = map[string]bool{
	"schema": true, "manifest_sha256": true, "source_revision": true,
	"target_revision": true, "adapter": true, "evidence_refs": true,
	"discovery": true, "surface_results": true, "action_results": true,
	"asset_results": true, "verdict": true, "reviewer": true,
}

func (service evidenceService) sourceContinuityManifest(args []string) Envelope {
	root, feature, err := taskControlFeature(args)
	if err != nil {
		return evidenceUsageError(err.Error())
	}
	taskID, err := normalizeTaskControlID(optionValue(args, "--task-id", ""))
	if err != nil {
		return evidenceUsageError(err.Error())
	}
	indexPath := filepath.Join(feature, "task-index.json")
	index, err := readImplementJSONMap(indexPath)
	if err != nil || intFromAny(index["version"]) != 2 || index["status"] != "ready" {
		return evidenceBlockedError("source continuity manifest requires a ready CLI-owned task index", firstVisualComparisonError(err, "task-index.json must use version 2 with status ready"))
	}
	_, task, err := findImplementTask(index, taskID)
	if err != nil {
		return evidenceUsageError(err.Error())
	}
	ui, ok := task["ui_contract"].(map[string]any)
	if !ok {
		return sourceContinuityLabNotApplicable(taskID, "task has no UI contract")
	}
	continuity, ok := ui["source_continuity"].(map[string]any)
	if !ok || strings.TrimSpace(anyString(continuity["applicability"])) != "required" {
		return sourceContinuityLabNotApplicable(taskID, "task has no required source continuity contract")
	}
	if err := validateDesignSourceContinuity(continuity, "ui_contract.source_continuity", true); err != nil {
		return evidenceUsageError(err.Error())
	}
	manifest, err := buildSourceContinuityLabManifest(root, feature, taskID, indexPath, continuity)
	if err != nil {
		return evidenceUsageError(err.Error())
	}
	rendered, err := marshalReviewAcceptJSON(manifest)
	if err != nil {
		return evidenceBlockedError("source continuity manifest cannot be rendered", err)
	}
	manifestRef := sourceContinuityLabManifestRef(taskID)
	canonicalPath := sourceContinuityLabCanonicalPath(root, feature, manifestRef)
	if err := validateSourceContinuityLabArtifactOwner(canonicalPath); err != nil {
		return evidenceBlockedError("source continuity manifest path is not owned by its specialized CLI", err)
	}
	manifestPath := filepath.Join(feature, filepath.FromSlash(manifestRef))
	receipt, err := applyFileTransaction(root, "source-continuity-manifest", []fileTransactionUpdate{{Path: manifestPath, Content: rendered, Perm: 0o644}})
	if err != nil {
		return evidenceBlockedError("source continuity manifest could not be written atomically", err)
	}
	env := NewEnvelope("ok", "source continuity lab manifest materialized")
	env.Data = map[string]any{
		"task_id": taskID, "applicable": true, "status": "ready",
		"manifest_ref": manifestRef, "manifest_sha256": fileContentSHA256(rendered),
		"transaction_receipt_ref": receipt.ReceiptRef,
	}
	env.ShowArgv = []string{"specify-runtime", "artifact", "show", "--path", canonicalPath, "--view", "summary", "--format", "json"}
	return env
}

func (service evidenceService) sourceContinuityValidate(args []string, raw map[string]any) Envelope {
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
		return evidenceUsageError("source continuity validation requires --manifest")
	}
	if manifestRef != sourceContinuityLabManifestRef(taskID) {
		return evidenceUsageError("source continuity manifest must be the canonical task-bound manifest")
	}
	manifestPath, err := secureFeatureRelativePath(feature, manifestRef)
	if err != nil {
		return evidenceUsageError("source continuity manifest path is unsafe")
	}
	manifest, err := readImplementJSONMap(manifestPath)
	if err != nil {
		return evidenceBlockedError("source continuity manifest is unavailable", err)
	}
	diagnostics, metrics := validateSourceContinuityLabResult(taskID, manifest, optionalFileSHA256(manifestPath), raw)
	source, sourceOK := manifest["source"].(map[string]any)
	if !sourceOK || strings.TrimSpace(anyString(source["task_index_sha256"])) != optionalFileSHA256(filepath.Join(feature, "task-index.json")) {
		diagnostics = append(diagnostics, "stale-manifest")
	}
	diagnostics = uniqueSourceContinuityLabDiagnostics(diagnostics)
	if len(diagnostics) > 0 {
		env := NewEnvelope("error", strings.Join(diagnostics, "; "))
		env.Data = map[string]any{"task_id": taskID, "diagnostics": stringsToAny(diagnostics), "metrics": metrics}
		return env
	}
	report := map[string]any{
		"schema": sourceContinuityLabReportSchema, "task_id": taskID, "verdict": "passed",
		"manifest_ref": manifestRef, "manifest_sha256": optionalFileSHA256(manifestPath),
		"source_revision": anyString(raw["source_revision"]), "target_revision": anyString(raw["target_revision"]),
		"adapter": cloneJSONValue(raw["adapter"]), "evidence_refs": cloneJSONValue(raw["evidence_refs"]),
		"discovery": cloneJSONValue(raw["discovery"]), "surface_results": cloneJSONValue(raw["surface_results"]),
		"action_results": cloneJSONValue(raw["action_results"]), "asset_results": cloneJSONValue(raw["asset_results"]),
		"coverage": cloneJSONValue(requireSourceContinuityLabObject(manifest, "source_continuity")["coverage"]),
		"metrics":  metrics, "reviewer": anyString(raw["reviewer"]),
		"source": map[string]any{"result_schema": sourceContinuityLabResultSchema, "task_index_sha256": anyString(source["task_index_sha256"])},
	}
	rendered, err := marshalReviewAcceptJSON(report)
	if err != nil {
		return evidenceBlockedError("source continuity lab report cannot be rendered", err)
	}
	reportRef := sourceContinuityLabReportRef(taskID)
	canonicalPath := sourceContinuityLabCanonicalPath(root, feature, reportRef)
	if err := validateSourceContinuityLabArtifactOwner(canonicalPath); err != nil {
		return evidenceBlockedError("source continuity report path is not owned by its specialized CLI", err)
	}
	reportPath := filepath.Join(feature, filepath.FromSlash(reportRef))
	receipt, err := applyFileTransaction(root, "source-continuity-lab", []fileTransactionUpdate{{Path: reportPath, Content: rendered, Perm: 0o644}})
	if err != nil {
		return evidenceBlockedError("source continuity lab report could not be written atomically", err)
	}
	reportSHA := fileContentSHA256(rendered)
	coverage := requireSourceContinuityLabObject(manifest, "source_continuity")["coverage"]
	coverageMap, _ := coverage.(map[string]any)
	env := NewEnvelope("ok", "source continuity lab report materialized")
	env.Data = map[string]any{
		"task_id": taskID, "report_ref": reportRef, "report_sha256": reportSHA,
		"metrics": metrics, "transaction_receipt_ref": receipt.ReceiptRef,
		"ui_verification_patch": map[string]any{
			"source_continuity_lab_report_ref":          reportRef,
			"source_continuity_lab_report_sha256":       reportSHA,
			"covered_source_continuity_surface_ids":     cloneJSONValue(coverageMap["surface_ids"]),
			"covered_source_continuity_interaction_ids": cloneJSONValue(coverageMap["interaction_ids"]),
			"covered_source_continuity_component_ids":   cloneJSONValue(coverageMap["component_ids"]),
		},
	}
	env.ShowArgv = []string{"specify-runtime", "artifact", "show", "--path", canonicalPath, "--view", "summary", "--format", "json"}
	return env
}

func sourceContinuityLabNotApplicable(taskID, reason string) Envelope {
	env := NewEnvelope("ok", "source continuity lab not applicable")
	env.Data = map[string]any{"task_id": taskID, "applicable": false, "status": "not-applicable", "reason": reason}
	return env
}

func buildSourceContinuityLabManifest(root, feature, taskID, indexPath string, continuity map[string]any) (map[string]any, error) {
	contractRaw, err := marshalReviewAcceptJSON(continuity)
	if err != nil {
		return nil, errors.New("source continuity contract cannot be canonicalized")
	}
	projectRelativeFeature, err := filepath.Rel(root, feature)
	if err != nil {
		return nil, errors.New("source continuity feature path is invalid")
	}
	return map[string]any{
		"schema": sourceContinuityLabManifestSchema, "task_id": taskID,
		"source_continuity_schema":      anyString(continuity["schema"]),
		"source_continuity_sha256":      fileContentSHA256(contractRaw),
		"source_continuity":             cloneJSONValue(continuity),
		"required_adapter_capabilities": stringsToAny(sourceContinuityLabCapabilities),
		"required_evidence":             stringsToAny(sourceContinuityLabEvidenceKinds),
		"source": map[string]any{
			"task_index_ref": "task-index.json", "task_index_sha256": optionalFileSHA256(indexPath),
			"feature_ref": filepath.ToSlash(projectRelativeFeature),
		},
	}, nil
}

func validateSourceContinuityLabResult(taskID string, manifest map[string]any, manifestSHA string, raw map[string]any) ([]string, map[string]any) {
	diagnostics := []string{}
	if manifest["schema"] != sourceContinuityLabManifestSchema || anyString(manifest["task_id"]) != taskID {
		diagnostics = append(diagnostics, "stale-manifest")
	}
	for field := range raw {
		if !sourceContinuityLabInputFields[field] {
			diagnostics = append(diagnostics, "unsupported-result-field")
		}
	}
	if raw["schema"] != sourceContinuityLabResultSchema {
		diagnostics = append(diagnostics, "invalid-result-schema")
	}
	if strings.TrimSpace(anyString(raw["manifest_sha256"])) != manifestSHA {
		diagnostics = append(diagnostics, "stale-manifest")
	}
	for _, field := range []string{"source_revision", "target_revision", "reviewer"} {
		if strings.TrimSpace(anyString(raw[field])) == "" {
			diagnostics = append(diagnostics, "missing-"+strings.ReplaceAll(field, "_", "-"))
		}
	}
	if !sourceContinuityLabPassing(raw["verdict"]) {
		diagnostics = append(diagnostics, "overall-verdict-failed")
	}
	diagnostics = append(diagnostics, validateSourceContinuityLabAdapter(raw["adapter"])...)
	evidenceRefs, evidenceDiagnostics := validateSourceContinuityLabEvidence(raw["evidence_refs"])
	diagnostics = append(diagnostics, evidenceDiagnostics...)

	continuity := requireSourceContinuityLabObject(manifest, "source_continuity")
	coverage := requireSourceContinuityLabObject(continuity, "coverage")
	expectedSurfaces := sourceContinuityLabStringList(coverage["surface_ids"])
	expectedActions := sourceContinuityLabStringList(coverage["interaction_ids"])
	expectedAssets := sourceContinuityLabStringList(coverage["component_ids"])
	expectedSurfaceBindings := sourceContinuityLabBindingIDs(continuity["surface_bindings"])
	expectedActionBindings := sourceContinuityLabBindingIDs(continuity["action_bindings"])
	expectedAssetBindings := sourceContinuityLabBindingIDs(continuity["asset_bindings"])

	discovery, discoveryDiagnostics := validateSourceContinuityLabDiscovery(raw["discovery"], expectedSurfaceBindings, expectedActionBindings, expectedAssetBindings)
	diagnostics = append(diagnostics, discoveryDiagnostics...)
	surfacePassed, surfaceDiagnostics := validateSourceContinuityLabSurfaces(raw["surface_results"], expectedSurfaces)
	diagnostics = append(diagnostics, surfaceDiagnostics...)
	actionPassed, actionOutcomePassed, actionDiagnostics := validateSourceContinuityLabActions(raw["action_results"], expectedActions, continuity["action_bindings"], evidenceRefs)
	diagnostics = append(diagnostics, actionDiagnostics...)
	assetPassed, assetDiagnostics := validateSourceContinuityLabAssets(raw["asset_results"], expectedAssets, continuity["asset_bindings"], evidenceRefs)
	diagnostics = append(diagnostics, assetDiagnostics...)

	metrics := map[string]any{
		"source_discovery_coverage":   sourceContinuityLabRatio(discovery, len(expectedSurfaceBindings)+len(expectedActionBindings)+len(expectedAssetBindings)),
		"target_surface_reachability": sourceContinuityLabRatio(surfacePassed, len(expectedSurfaces)),
		"action_operability":          sourceContinuityLabRatio(actionPassed, len(expectedActions)),
		"business_outcome_parity":     sourceContinuityLabRatio(actionOutcomePassed, len(expectedActions)),
		"asset_fidelity":              sourceContinuityLabRatio(assetPassed, len(expectedAssets)),
	}
	return uniqueSourceContinuityLabDiagnostics(diagnostics), metrics
}

func validateSourceContinuityLabAdapter(value any) []string {
	adapter, ok := value.(map[string]any)
	if !ok {
		return []string{"invalid-adapter"}
	}
	if err := exactVisualComparisonFields(adapter, map[string]bool{"id": true, "version": true, "capabilities": true}, "source continuity adapter"); err != nil {
		return []string{"invalid-adapter"}
	}
	if strings.TrimSpace(anyString(adapter["id"])) == "" || strings.TrimSpace(anyString(adapter["version"])) == "" {
		return []string{"invalid-adapter"}
	}
	capabilities := sourceContinuityLabStringSet(sourceContinuityLabStringList(adapter["capabilities"]))
	missing := []string{}
	for _, capability := range sourceContinuityLabCapabilities {
		if !capabilities[capability] {
			missing = append(missing, "missing-adapter-capability:"+capability)
		}
	}
	return missing
}

func validateSourceContinuityLabEvidence(value any) (map[string]bool, []string) {
	rows, ok := value.([]any)
	if !ok {
		return map[string]bool{}, []string{"invalid-evidence-refs"}
	}
	refs := map[string]bool{}
	covered := map[string]bool{}
	diagnostics := []string{}
	for _, value := range rows {
		row, ok := value.(map[string]any)
		if !ok || exactVisualComparisonFields(row, map[string]bool{"side": true, "kind": true, "ref": true}, "source continuity evidence") != nil {
			diagnostics = append(diagnostics, "invalid-evidence-ref")
			continue
		}
		side := strings.TrimSpace(anyString(row["side"]))
		kind := strings.TrimSpace(anyString(row["kind"]))
		ref := strings.TrimSpace(anyString(row["ref"]))
		if (side != "source" && side != "target") || ref == "" {
			diagnostics = append(diagnostics, "invalid-evidence-ref")
			continue
		}
		refs[ref] = true
		covered[side+":"+kind] = true
	}
	for _, side := range []string{"source", "target"} {
		for _, kind := range sourceContinuityLabEvidenceKinds {
			if !covered[side+":"+kind] {
				diagnostics = append(diagnostics, "missing-"+side+"-"+strings.ReplaceAll(kind, "_", "-"))
			}
		}
	}
	return refs, diagnostics
}

func validateSourceContinuityLabDiscovery(value any, expectedSurfaces, expectedActions, expectedAssets []string) (int, []string) {
	discovery, ok := value.(map[string]any)
	if !ok || exactVisualComparisonFields(discovery, map[string]bool{
		"surface_binding_ids": true, "action_binding_ids": true, "asset_binding_ids": true, "unexpected_candidates": true,
	}, "source continuity discovery") != nil {
		return 0, []string{"invalid-discovery"}
	}
	diagnostics := []string{}
	covered := 0
	for _, item := range []struct {
		field string
		want  []string
	}{
		{"surface_binding_ids", expectedSurfaces},
		{"action_binding_ids", expectedActions},
		{"asset_binding_ids", expectedAssets},
	} {
		got := sourceContinuityLabStringList(discovery[item.field])
		if !sourceContinuityLabExactIDs(got, item.want) {
			diagnostics = append(diagnostics, strings.ReplaceAll(item.field, "_binding_ids", "")+"-discovery-coverage-mismatch")
		}
		covered += sourceContinuityLabIntersectionCount(got, item.want)
	}
	unexpected, ok := discovery["unexpected_candidates"].([]any)
	if !ok {
		diagnostics = append(diagnostics, "invalid-unexpected-candidates")
	} else if len(unexpected) > 0 {
		for _, value := range unexpected {
			row, valid := value.(map[string]any)
			if !valid || exactVisualComparisonFields(row, map[string]bool{"id": true, "kind": true, "source_ref": true, "reason": true}, "unexpected source candidate") != nil {
				diagnostics = append(diagnostics, "invalid-unexpected-candidate")
				continue
			}
			diagnostics = append(diagnostics, "unbound-source-candidate:"+strings.TrimSpace(anyString(row["id"])))
		}
	}
	return covered, diagnostics
}

func validateSourceContinuityLabSurfaces(value any, expected []string) (int, []string) {
	rows, ok := value.([]any)
	if !ok {
		return 0, []string{"invalid-surface-results"}
	}
	ids := []string{}
	passed := 0
	diagnostics := []string{}
	for _, value := range rows {
		row, ok := value.(map[string]any)
		if !ok || exactVisualComparisonFields(row, map[string]bool{
			"surface_id": true, "source_reachable": true, "target_reachable": true, "disposition_verified": true, "verdict": true,
		}, "source continuity surface result") != nil {
			diagnostics = append(diagnostics, "invalid-surface-result")
			continue
		}
		id := strings.TrimSpace(anyString(row["surface_id"]))
		ids = append(ids, id)
		okResult := boolValue(row["source_reachable"]) && boolValue(row["target_reachable"]) && boolValue(row["disposition_verified"]) && sourceContinuityLabPassing(row["verdict"])
		if okResult {
			passed++
		} else {
			if !boolValue(row["target_reachable"]) {
				diagnostics = append(diagnostics, "target-surface-unreachable:"+id)
			}
			if !boolValue(row["disposition_verified"]) {
				diagnostics = append(diagnostics, "surface-disposition-mismatch:"+id)
			}
		}
	}
	if !sourceContinuityLabExactIDs(ids, expected) {
		diagnostics = append(diagnostics, "surface-coverage-mismatch")
	}
	return passed, diagnostics
}

func validateSourceContinuityLabActions(value any, expected []string, bindingValue any, evidenceRefs map[string]bool) (int, int, []string) {
	rows, ok := value.([]any)
	if !ok {
		return 0, 0, []string{"invalid-action-results"}
	}
	expectedEffects := map[string][]string{}
	for _, value := range listValue(bindingValue) {
		row, _ := value.(map[string]any)
		expectedEffects[strings.TrimSpace(anyString(row["interaction_id"]))] = sourceContinuityLabStringList(row["side_effects"])
	}
	ids := []string{}
	passed := 0
	outcomes := 0
	diagnostics := []string{}
	for _, value := range rows {
		row, ok := value.(map[string]any)
		if !ok || exactVisualComparisonFields(row, map[string]bool{
			"interaction_id": true, "source_reachable": true, "target_reachable": true,
			"source_evidence_ref": true, "target_evidence_ref": true, "observed_side_effects": true,
			"business_outcome_verified": true, "final_state_verified": true, "verdict": true,
		}, "source continuity action result") != nil {
			diagnostics = append(diagnostics, "invalid-action-result")
			continue
		}
		id := strings.TrimSpace(anyString(row["interaction_id"]))
		ids = append(ids, id)
		if !evidenceRefs[strings.TrimSpace(anyString(row["source_evidence_ref"]))] || !evidenceRefs[strings.TrimSpace(anyString(row["target_evidence_ref"]))] {
			diagnostics = append(diagnostics, "action-evidence-unbound:"+id)
		}
		if !sourceContinuityLabExactIDs(sourceContinuityLabStringList(row["observed_side_effects"]), expectedEffects[id]) {
			diagnostics = append(diagnostics, "side-effect-mismatch:"+id)
		}
		operable := boolValue(row["source_reachable"]) && boolValue(row["target_reachable"]) && sourceContinuityLabPassing(row["verdict"])
		outcome := boolValue(row["business_outcome_verified"]) && boolValue(row["final_state_verified"])
		if operable {
			passed++
		} else if !boolValue(row["target_reachable"]) {
			diagnostics = append(diagnostics, "target-action-unreachable:"+id)
		}
		if outcome {
			outcomes++
		} else {
			if !boolValue(row["business_outcome_verified"]) {
				diagnostics = append(diagnostics, "business-outcome-mismatch:"+id)
			}
			if !boolValue(row["final_state_verified"]) {
				diagnostics = append(diagnostics, "final-state-mismatch:"+id)
			}
		}
	}
	if !sourceContinuityLabExactIDs(ids, expected) {
		diagnostics = append(diagnostics, "action-coverage-mismatch")
	}
	return passed, outcomes, diagnostics
}

func validateSourceContinuityLabAssets(value any, expected []string, bindingValue any, evidenceRefs map[string]bool) (int, []string) {
	rows, ok := value.([]any)
	if !ok {
		return 0, []string{"invalid-asset-results"}
	}
	policies := map[string]string{}
	for _, value := range listValue(bindingValue) {
		row, _ := value.(map[string]any)
		policies[strings.TrimSpace(anyString(row["component_id"]))] = strings.TrimSpace(anyString(row["placeholder_policy"]))
	}
	ids := []string{}
	passed := 0
	diagnostics := []string{}
	for _, value := range rows {
		row, ok := value.(map[string]any)
		if !ok || exactVisualComparisonFields(row, map[string]bool{
			"component_id": true, "source_evidence_ref": true, "target_evidence_ref": true,
			"semantic_match": true, "provenance_match": true, "render_match": true,
			"character_substitution": true, "verdict": true,
		}, "source continuity asset result") != nil {
			diagnostics = append(diagnostics, "invalid-asset-result")
			continue
		}
		id := strings.TrimSpace(anyString(row["component_id"]))
		ids = append(ids, id)
		if !evidenceRefs[strings.TrimSpace(anyString(row["source_evidence_ref"]))] || !evidenceRefs[strings.TrimSpace(anyString(row["target_evidence_ref"]))] {
			diagnostics = append(diagnostics, "asset-evidence-unbound:"+id)
		}
		characterViolation := boolValue(row["character_substitution"]) && policies[id] == "forbid-character-substitution"
		if characterViolation {
			diagnostics = append(diagnostics, "asset-character-substitution:"+id)
		}
		fidelity := boolValue(row["semantic_match"]) && boolValue(row["provenance_match"]) && boolValue(row["render_match"])
		if !fidelity {
			diagnostics = append(diagnostics, "asset-fidelity-mismatch:"+id)
		}
		if fidelity && !characterViolation && sourceContinuityLabPassing(row["verdict"]) {
			passed++
		}
	}
	if !sourceContinuityLabExactIDs(ids, expected) {
		diagnostics = append(diagnostics, "asset-coverage-mismatch")
	}
	return passed, diagnostics
}

func sourceContinuityLabManifestRef(taskID string) string {
	return "implementation-review/source-continuity/source-continuity-manifest-" + taskID + ".json"
}

func sourceContinuityLabReportRef(taskID string) string {
	return "implementation-review/source-continuity/source-continuity-lab-" + taskID + ".json"
}

func sourceContinuityLabCanonicalPath(root, feature, ref string) string {
	relative, err := filepath.Rel(root, filepath.Join(feature, filepath.FromSlash(ref)))
	if err != nil {
		return filepath.ToSlash(ref)
	}
	return filepath.ToSlash(relative)
}

func validateSourceContinuityLabArtifactOwner(canonicalPath string) error {
	metadata, ok := LookupArtifactType(canonicalPath)
	wantOwner := "specify-runtime evidence source-continuity-manifest / source-continuity-validate"
	if !ok || metadata.TypeID != "feature-source-continuity-lab" || metadata.Owner != wantOwner {
		return errors.New(canonicalPath)
	}
	return nil
}

func sourceContinuityLabBindingIDs(value any) []string {
	ids := []string{}
	for _, value := range listValue(value) {
		row, ok := value.(map[string]any)
		if ok {
			ids = append(ids, strings.TrimSpace(anyString(row["id"])))
		}
	}
	return ids
}

func sourceContinuityLabStringList(value any) []string {
	values, err := anyStringList(value, "source continuity lab list", false)
	if err != nil {
		return []string{}
	}
	return values
}

func sourceContinuityLabExactIDs(got, want []string) bool {
	gotSet := sourceContinuityLabStringSet(got)
	wantSet := sourceContinuityLabStringSet(want)
	return len(got) == len(gotSet) && len(want) == len(wantSet) && reflect.DeepEqual(gotSet, wantSet)
}

func sourceContinuityLabStringSet(values []string) map[string]bool {
	result := map[string]bool{}
	for _, value := range values {
		if trimmed := strings.TrimSpace(value); trimmed != "" {
			result[trimmed] = true
		}
	}
	return result
}

func sourceContinuityLabIntersectionCount(got, want []string) int {
	wantSet := sourceContinuityLabStringSet(want)
	seen := map[string]bool{}
	count := 0
	for _, value := range got {
		value = strings.TrimSpace(value)
		if wantSet[value] && !seen[value] {
			count++
			seen[value] = true
		}
	}
	return count
}

func sourceContinuityLabRatio(passed, total int) float64 {
	if total <= 0 {
		return 1
	}
	return float64(passed) / float64(total)
}

func sourceContinuityLabPassing(value any) bool {
	normalized := strings.ToLower(strings.TrimSpace(anyString(value)))
	return normalized == "pass" || normalized == "passed" || normalized == "success" || normalized == "matched" || normalized == "approved"
}

func requireSourceContinuityLabObject(value map[string]any, field string) map[string]any {
	result, _ := value[field].(map[string]any)
	if result == nil {
		return map[string]any{}
	}
	return result
}

func uniqueSourceContinuityLabDiagnostics(values []string) []string {
	seen := map[string]bool{}
	result := []string{}
	for _, value := range values {
		value = strings.TrimSpace(value)
		if value != "" && !seen[value] {
			seen[value] = true
			result = append(result, value)
		}
	}
	sort.Strings(result)
	return result
}
