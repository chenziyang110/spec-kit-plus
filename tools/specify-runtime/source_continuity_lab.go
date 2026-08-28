package main

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"reflect"
	"regexp"
	"sort"
	"strings"
)

const (
	sourceContinuityLabManifestSchema  = "spec-kit-source-continuity-lab-manifest-v1"
	sourceContinuityLabResultSchema    = "spec-kit-source-continuity-lab-result-v1"
	sourceContinuityLabReportSchema    = "spec-kit-source-continuity-lab-report-v1"
	sourceContinuityAdapterProtocol    = "spec-kit-source-continuity-adapter-v1"
	sourceContinuityAdapterInputSchema = "spec-kit-source-continuity-adapter-plan-input-v1"
	sourceContinuityAdapterPlanSchema  = "spec-kit-source-continuity-adapter-plan-v1"
)

var sourceContinuityAdapterIDPattern = regexp.MustCompile(`^[a-z][a-z0-9]*(?:[.-][a-z0-9]+)*$`)
var sourceContinuityAdapterToolRefPattern = regexp.MustCompile(`^[a-z][a-z0-9+.-]*://[^\s]+$`)

var sourceContinuityAdapterActions = map[string]bool{
	"enumerate-surfaces":         true,
	"enumerate-actions":          true,
	"enumerate-assets":           true,
	"activate-action":            true,
	"observe-side-effects":       true,
	"capture-structure":          true,
	"capture-visual":             true,
	"capture-runtime":            true,
	"prepare-isolated-test-data": true,
}

var sourceContinuityAdapterCapabilityActions = map[string][]string{
	"surface-enumeration":     {"enumerate-surfaces", "capture-structure"},
	"action-execution":        {"enumerate-actions", "activate-action", "capture-runtime"},
	"side-effect-observation": {"observe-side-effects", "capture-runtime"},
	"asset-inspection":        {"enumerate-assets", "capture-visual"},
	"visual-capture":          {"capture-visual"},
}

var sourceContinuityAdapterCapabilityEvidence = map[string]string{
	"surface-enumeration":     "structure_snapshot",
	"action-execution":        "runtime_diagnostics",
	"side-effect-observation": "runtime_diagnostics",
	"asset-inspection":        "visual_capture",
	"visual-capture":          "visual_capture",
}

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
	"adapter_plan_ref": true, "adapter_plan_sha256": true,
	"adapter_execution_ref": true, "adapter_execution_sha256": true,
}

func (service evidenceService) sourceContinuityManifest(args []string) Envelope {
	if quickID := strings.TrimSpace(optionValue(args, "--quick-id", "")); quickID != "" {
		return service.sourceContinuityQuickManifest(args, quickID)
	}
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
	manifest, err := buildSourceContinuityLabManifest(root, feature, taskID, indexPath, task, continuity)
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
	if quickID := strings.TrimSpace(optionValue(args, "--quick-id", "")); quickID != "" {
		return service.sourceContinuityQuickValidate(args, quickID, raw)
	}
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
	diagnostics = append(diagnostics, validateSourceContinuityLabEvidenceRecords(root, raw["evidence_refs"])...)
	source, sourceOK := manifest["source"].(map[string]any)
	indexPath := filepath.Join(feature, "task-index.json")
	index, indexErr := readImplementJSONMap(indexPath)
	_, currentTask, taskErr := findImplementTask(index, taskID)
	currentUI, _ := currentTask["ui_contract"].(map[string]any)
	currentContinuity, _ := currentUI["source_continuity"].(map[string]any)
	targetSnapshot, snapshotErr := sourceContinuityLabTargetSnapshot(root, sourceContinuityLabTaskWriteScope(currentTask))
	if !sourceOK || indexErr != nil || taskErr != nil || snapshotErr != nil || strings.TrimSpace(anyString(source["task_index_sha256"])) != optionalFileSHA256(indexPath) || strings.TrimSpace(anyString(source["target_snapshot_sha256"])) != targetSnapshot || !reflect.DeepEqual(manifest["source_continuity"], currentContinuity) || anyString(manifest["source_continuity_sha256"]) != sourceContinuityLabContractSHA(currentContinuity) {
		diagnostics = append(diagnostics, "stale-manifest")
	}
	adapterPlanRef := filepath.ToSlash(strings.TrimSpace(optionValue(args, "--adapter-plan", "")))
	adapterPlanSHA := strings.TrimSpace(anyString(raw["adapter_plan_sha256"]))
	var adapterPlan map[string]any
	if adapterPlanRef == "" || anyString(raw["adapter_plan_ref"]) == "" || adapterPlanSHA == "" {
		diagnostics = append(diagnostics, "missing-adapter-plan")
	} else {
		adapterPlan, err = loadSourceContinuityAdapterPlan(feature, taskID, adapterPlanRef, adapterPlanSHA, manifestRef, optionalFileSHA256(manifestPath), false)
		if err != nil {
			diagnostics = append(diagnostics, "stale-adapter-plan")
		} else {
			diagnostics = append(diagnostics, validateSourceContinuityAdapterObservation(adapterPlan, adapterPlanRef, adapterPlanSHA, raw)...)
		}
	}
	adapterExecutionRef := filepath.ToSlash(strings.TrimSpace(optionValue(args, "--adapter-execution", "")))
	adapterExecutionSHA := strings.TrimSpace(anyString(raw["adapter_execution_sha256"]))
	var adapterExecution map[string]any
	if adapterExecutionRef == "" || anyString(raw["adapter_execution_ref"]) == "" || adapterExecutionSHA == "" {
		diagnostics = append(diagnostics, "missing-adapter-execution")
	} else if adapterPlan != nil {
		adapterExecution, err = loadSourceContinuityAdapterExecution(feature, taskID, adapterExecutionRef, adapterExecutionSHA, manifestRef, optionalFileSHA256(manifestPath), adapterPlanRef, adapterPlanSHA, false)
		if err != nil {
			diagnostics = append(diagnostics, "stale-adapter-execution")
		} else {
			diagnostics = append(diagnostics, validateSourceContinuityAdapterExecutionObservation(adapterExecution, adapterExecutionRef, adapterExecutionSHA, raw)...)
		}
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
		"source": map[string]any{"result_schema": sourceContinuityLabResultSchema, "task_index_sha256": anyString(source["task_index_sha256"]), "target_snapshot_sha256": targetSnapshot},
	}
	if adapterPlan != nil {
		report["adapter_plan_ref"] = adapterPlanRef
		report["adapter_plan_sha256"] = adapterPlanSHA
	}
	if adapterExecution != nil {
		report["adapter_execution_ref"] = adapterExecutionRef
		report["adapter_execution_sha256"] = adapterExecutionSHA
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
			"source_continuity_lab_report_ref":           reportRef,
			"source_continuity_lab_report_sha256":        reportSHA,
			"source_continuity_adapter_plan_ref":         adapterPlanRef,
			"source_continuity_adapter_plan_sha256":      adapterPlanSHA,
			"source_continuity_adapter_execution_ref":    adapterExecutionRef,
			"source_continuity_adapter_execution_sha256": adapterExecutionSHA,
			"covered_source_continuity_surface_ids":      cloneJSONValue(coverageMap["surface_ids"]),
			"covered_source_continuity_interaction_ids":  cloneJSONValue(coverageMap["interaction_ids"]),
			"covered_source_continuity_component_ids":    cloneJSONValue(coverageMap["component_ids"]),
		},
	}
	env.ShowArgv = []string{"specify-runtime", "artifact", "show", "--path", canonicalPath, "--view", "summary", "--format", "json"}
	return env
}

func (service evidenceService) sourceContinuityAdapterPlan(args []string, raw map[string]any) Envelope {
	if quickID := strings.TrimSpace(optionValue(args, "--quick-id", "")); quickID != "" {
		context, err := service.sourceContinuityQuickContext(args, quickID)
		if err != nil {
			return evidenceUsageError(err.Error())
		}
		manifestRef := filepath.ToSlash(strings.TrimSpace(optionValue(args, "--manifest", "")))
		if manifestRef != sourceContinuityLabQuickManifestRef(context.itemID) {
			return evidenceUsageError("quick adapter plan must bind the canonical item manifest")
		}
		manifestPath, err := secureFeatureRelativePath(context.workspacePath, manifestRef)
		if err != nil {
			return evidenceUsageError("quick source continuity manifest path is unsafe")
		}
		manifest, err := readImplementJSONMap(manifestPath)
		if err != nil {
			return evidenceBlockedError("quick source continuity manifest is unavailable", err)
		}
		if err := validateCurrentQuickSourceContinuityManifest(context, manifest); err != nil {
			return evidenceBlockedError("quick source continuity manifest is stale", err)
		}
		return service.materializeSourceContinuityAdapterPlan(
			context.root,
			context.workspacePath,
			context.itemID,
			"quick",
			manifestRef,
			manifestPath,
			manifest,
			raw,
			true,
		)
	}

	root, feature, err := taskControlFeature(args)
	if err != nil {
		return evidenceUsageError(err.Error())
	}
	taskID, err := normalizeTaskControlID(optionValue(args, "--task-id", ""))
	if err != nil {
		return evidenceUsageError(err.Error())
	}
	manifestRef := filepath.ToSlash(strings.TrimSpace(optionValue(args, "--manifest", "")))
	if manifestRef != sourceContinuityLabManifestRef(taskID) {
		return evidenceUsageError("adapter plan must bind the canonical task manifest")
	}
	manifestPath, err := secureFeatureRelativePath(feature, manifestRef)
	if err != nil {
		return evidenceUsageError("source continuity manifest path is unsafe")
	}
	manifest, err := readImplementJSONMap(manifestPath)
	if err != nil {
		return evidenceBlockedError("source continuity manifest is unavailable", err)
	}
	if err := validateCurrentFeatureSourceContinuityManifest(root, feature, taskID, manifest); err != nil {
		return evidenceBlockedError("source continuity manifest is stale", err)
	}
	return service.materializeSourceContinuityAdapterPlan(
		root,
		feature,
		taskID,
		"formal",
		manifestRef,
		manifestPath,
		manifest,
		raw,
		false,
	)
}

func (service evidenceService) materializeSourceContinuityAdapterPlan(
	root, container, subjectID, mode, manifestRef, manifestPath string,
	manifest, raw map[string]any,
	quick bool,
) Envelope {
	artifact, diagnostics, err := buildSourceContinuityAdapterPlanArtifact(
		root, container, subjectID, mode, manifestRef, manifestPath, manifest, raw,
		explicitSourceContinuityAdapterSelection(), quick,
	)
	if len(diagnostics) > 0 {
		env := NewEnvelope("error", strings.Join(diagnostics, "; "))
		env.Data = map[string]any{"subject_id": subjectID, "diagnostics": stringsToAny(diagnostics)}
		return env
	}
	if err != nil {
		return evidenceBlockedError("adapter plan cannot be materialized", err)
	}
	receipt, err := applyFileTransaction(root, "source-continuity-adapter-plan", []fileTransactionUpdate{{Path: artifact.path, Content: artifact.rendered, Perm: 0o644}})
	if err != nil {
		return evidenceBlockedError("adapter plan could not be written atomically", err)
	}
	return sourceContinuityAdapterPlanEnvelope(artifact, receipt.ReceiptRef)
}

type sourceContinuityAdapterPlanArtifact struct {
	plan          map[string]any
	rendered      []byte
	ref           string
	path          string
	canonicalPath string
	sha256        string
	planID        string
}

func buildSourceContinuityAdapterPlanArtifact(
	root, container, subjectID, mode, manifestRef, manifestPath string,
	manifest, raw, selection map[string]any,
	quick bool,
) (*sourceContinuityAdapterPlanArtifact, []string, error) {
	adapters, assignments, diagnostics := validateSourceContinuityAdapterPlanInput(raw)
	diagnostics = append(diagnostics, validateSourceContinuityAdapterSelection(selection)...)
	if len(diagnostics) > 0 {
		return nil, uniqueSourceContinuityLabDiagnostics(diagnostics), nil
	}
	manifestSHA := optionalFileSHA256(manifestPath)
	seedRaw, err := marshalReviewAcceptJSON(map[string]any{
		"manifest_sha256": manifestSHA,
		"adapters":        adapters,
		"assignments":     assignments,
		"selection":       selection,
	})
	if err != nil {
		return nil, nil, fmt.Errorf("adapter plan identity cannot be derived: %w", err)
	}
	seed := sha256.Sum256(seedRaw)
	planID := "SCAP-" + hex.EncodeToString(seed[:])[:12]
	binding := sourceContinuityAdapterManifestBinding(subjectID, mode, manifestRef, manifestSHA, manifest)
	plan := map[string]any{
		"schema":           sourceContinuityAdapterPlanSchema,
		"adapter_protocol": sourceContinuityAdapterProtocol,
		"plan_id":          planID,
		"subject_id":       subjectID,
		"status":           "ready",
		"binding":          binding,
		"selection":        cloneJSONValue(selection),
		"required_lanes":   stringsToAny(sourceContinuityAdapterRequiredLanes()),
		"adapters":         cloneJSONValue(adapters),
		"assignments":      cloneJSONValue(assignments),
		"unresolved_gaps":  []any{},
	}
	rendered, err := marshalReviewAcceptJSON(plan)
	if err != nil {
		return nil, nil, fmt.Errorf("adapter plan cannot be rendered: %w", err)
	}
	planRef := sourceContinuityAdapterPlanRef(subjectID)
	if quick {
		planRef = sourceContinuityAdapterQuickPlanRef(subjectID)
	}
	canonicalPath := sourceContinuityLabCanonicalPath(root, container, planRef)
	if quick {
		err = validateQuickSourceContinuityLabArtifactOwner(canonicalPath)
	} else {
		err = validateSourceContinuityLabArtifactOwner(canonicalPath)
	}
	if err != nil {
		return nil, nil, fmt.Errorf("adapter plan path is not owned by its specialized CLI: %w", err)
	}
	planPath := filepath.Join(container, filepath.FromSlash(planRef))
	planSHA := fileContentSHA256(rendered)
	return &sourceContinuityAdapterPlanArtifact{
		plan: plan, rendered: rendered, ref: planRef, path: planPath,
		canonicalPath: canonicalPath, sha256: planSHA, planID: planID,
	}, nil, nil
}

func sourceContinuityAdapterManifestBinding(subjectID, mode, manifestRef, manifestSHA string, manifest map[string]any) map[string]any {
	manifestSource, _ := manifest["source"].(map[string]any)
	binding := map[string]any{
		"mode":                     mode,
		"subject_id":               subjectID,
		"manifest_ref":             manifestRef,
		"manifest_sha256":          manifestSHA,
		"source_continuity_sha256": anyString(manifest["source_continuity_sha256"]),
		"target_snapshot_sha256":   anyString(manifestSource["target_snapshot_sha256"]),
	}
	if mode == "quick" {
		binding["confirmation_digest"] = anyString(manifestSource["confirmation_digest"])
	} else {
		binding["task_index_sha256"] = anyString(manifestSource["task_index_sha256"])
	}
	return binding
}

func sourceContinuityAdapterPlanEnvelope(artifact *sourceContinuityAdapterPlanArtifact, receiptRef string) Envelope {
	env := NewEnvelope("ok", "source continuity adapter plan materialized")
	env.Data = map[string]any{
		"subject_id":              anyString(artifact.plan["subject_id"]),
		"adapter_plan_ref":        artifact.ref,
		"adapter_plan_sha256":     artifact.sha256,
		"plan_id":                 artifact.planID,
		"required_lanes":          stringsToAny(sourceContinuityAdapterRequiredLanes()),
		"transaction_receipt_ref": receiptRef,
		"adapter_binding": map[string]any{
			"adapter_plan_ref":    artifact.ref,
			"adapter_plan_sha256": artifact.sha256,
			"adapter": map[string]any{
				"id":           "adapter-plan:" + artifact.sha256[:12],
				"version":      "1",
				"capabilities": stringsToAny(sourceContinuityLabCapabilities),
			},
		},
	}
	env.ShowArgv = []string{"specify-runtime", "artifact", "show", "--path", artifact.canonicalPath, "--view", "summary", "--format", "json"}
	return env
}

func explicitSourceContinuityAdapterSelection() map[string]any {
	return map[string]any{
		"mode": "explicit", "registry_schema": "", "registry_sha256": "",
		"probe_ref": "", "probe_sha256": "", "inventory_sha256": "",
	}
}

func validateSourceContinuityAdapterSelection(value map[string]any) []string {
	if exactVisualComparisonFields(value, map[string]bool{
		"mode": true, "registry_schema": true, "registry_sha256": true,
		"probe_ref": true, "probe_sha256": true, "inventory_sha256": true,
	}, "source continuity adapter selection") != nil {
		return []string{"invalid-adapter-selection"}
	}
	mode := strings.TrimSpace(anyString(value["mode"]))
	switch mode {
	case "explicit":
		for _, field := range []string{"registry_schema", "registry_sha256", "probe_ref", "probe_sha256", "inventory_sha256"} {
			if strings.TrimSpace(anyString(value[field])) != "" {
				return []string{"invalid-explicit-adapter-selection"}
			}
		}
	case "registry-probe":
		if value["registry_schema"] != sourceContinuityAdapterRegistrySchema ||
			!reviewSHA256RE.MatchString(strings.TrimSpace(anyString(value["registry_sha256"]))) ||
			strings.TrimSpace(anyString(value["probe_ref"])) == "" ||
			!reviewSHA256RE.MatchString(strings.TrimSpace(anyString(value["probe_sha256"]))) ||
			!reviewSHA256RE.MatchString(strings.TrimSpace(anyString(value["inventory_sha256"]))) {
			return []string{"invalid-registry-adapter-selection"}
		}
	default:
		return []string{"invalid-adapter-selection-mode"}
	}
	return nil
}

func validateSourceContinuityAdapterPlanInput(raw map[string]any) ([]any, []any, []string) {
	diagnostics := []string{}
	if err := exactVisualComparisonFields(raw, map[string]bool{
		"schema": true, "adapters": true, "assignments": true, "unresolved_gaps": true,
	}, "source continuity adapter plan input"); err != nil {
		diagnostics = append(diagnostics, "invalid-adapter-plan-fields")
	}
	if raw["schema"] != sourceContinuityAdapterInputSchema {
		diagnostics = append(diagnostics, "invalid-adapter-plan-schema")
	}
	gaps, gapsOK := raw["unresolved_gaps"].([]any)
	if !gapsOK || len(gaps) > 0 {
		diagnostics = append(diagnostics, "adapter-plan-unresolved-gap")
	}
	adapters, adaptersOK := raw["adapters"].([]any)
	if !adaptersOK || len(adapters) == 0 {
		diagnostics = append(diagnostics, "adapter-plan-requires-adapters")
		adapters = []any{}
	}
	adapterByID := map[string]map[string]any{}
	for _, value := range adapters {
		adapter, ok := value.(map[string]any)
		if !ok || exactVisualComparisonFields(adapter, map[string]bool{
			"id": true, "version": true, "roles": true, "capabilities": true,
			"actions": true, "evidence_kinds": true, "execution_mode": true,
			"tool_ref": true, "write_policy": true, "network_policy": true,
		}, "source continuity adapter") != nil {
			diagnostics = append(diagnostics, "invalid-adapter-fields")
			continue
		}
		id := strings.TrimSpace(anyString(adapter["id"]))
		version := strings.TrimSpace(anyString(adapter["version"]))
		toolRef := strings.TrimSpace(anyString(adapter["tool_ref"]))
		if !sourceContinuityAdapterIDPattern.MatchString(id) || version == "" || !sourceContinuityAdapterToolRefPattern.MatchString(toolRef) {
			diagnostics = append(diagnostics, "invalid-adapter-identity")
		}
		if _, duplicate := adapterByID[id]; duplicate {
			diagnostics = append(diagnostics, "duplicate-adapter-id:"+id)
		}
		adapterByID[id] = adapter
		roles := sourceContinuityLabStringList(adapter["roles"])
		capabilities := sourceContinuityLabStringList(adapter["capabilities"])
		actions := sourceContinuityLabStringList(adapter["actions"])
		evidenceKinds := sourceContinuityLabStringList(adapter["evidence_kinds"])
		if !sourceContinuityAdapterAllowedValues(roles, map[string]bool{"source": true, "target": true}) || len(roles) == 0 {
			diagnostics = append(diagnostics, "invalid-adapter-role:"+id)
		}
		if !sourceContinuityAdapterAllowedValues(capabilities, visualComparisonStringSet(sourceContinuityLabCapabilities)) || len(capabilities) == 0 {
			diagnostics = append(diagnostics, "invalid-adapter-capability:"+id)
		}
		if !sourceContinuityAdapterAllowedValues(actions, sourceContinuityAdapterActions) {
			diagnostics = append(diagnostics, "unsupported-adapter-action:"+id)
		}
		if !sourceContinuityAdapterAllowedValues(evidenceKinds, map[string]bool{"structure_snapshot": true, "visual_capture": true, "runtime_diagnostics": true}) {
			diagnostics = append(diagnostics, "invalid-adapter-evidence-kind:"+id)
		}
		if !quickContains([]string{"runtime-managed", "agent-tool", "app-connector", "external-runner", "manual-attested"}, anyString(adapter["execution_mode"])) {
			diagnostics = append(diagnostics, "invalid-adapter-execution-mode:"+id)
		}
		writePolicy := anyString(adapter["write_policy"])
		if !quickContains([]string{"read-only", "evidence-store-only", "isolated-test-data"}, writePolicy) {
			diagnostics = append(diagnostics, "invalid-adapter-write-policy:"+id)
		}
		if !quickContains([]string{"denied", "declared-read-only"}, anyString(adapter["network_policy"])) {
			diagnostics = append(diagnostics, "invalid-adapter-network-policy:"+id)
		}
		actionSet := sourceContinuityAdapterStringSet(actions)
		evidenceSet := sourceContinuityAdapterStringSet(evidenceKinds)
		for _, capability := range capabilities {
			for _, action := range sourceContinuityAdapterCapabilityActions[capability] {
				if !actionSet[action] {
					diagnostics = append(diagnostics, "adapter-capability-contract-mismatch:"+id+":"+capability)
				}
			}
			if !evidenceSet[sourceContinuityAdapterCapabilityEvidence[capability]] {
				diagnostics = append(diagnostics, "adapter-capability-contract-mismatch:"+id+":"+capability)
			}
		}
	}
	assignments, assignmentsOK := raw["assignments"].([]any)
	if !assignmentsOK {
		diagnostics = append(diagnostics, "adapter-plan-requires-assignments")
		assignments = []any{}
	}
	seenLanes := map[string]bool{}
	for _, value := range assignments {
		assignment, ok := value.(map[string]any)
		if !ok || exactVisualComparisonFields(assignment, map[string]bool{
			"side": true, "capability": true, "adapter_id": true, "selection_reason": true,
		}, "source continuity adapter assignment") != nil {
			diagnostics = append(diagnostics, "invalid-adapter-assignment")
			continue
		}
		side := strings.TrimSpace(anyString(assignment["side"]))
		capability := strings.TrimSpace(anyString(assignment["capability"]))
		adapterID := strings.TrimSpace(anyString(assignment["adapter_id"]))
		lane := side + "." + capability
		if seenLanes[lane] {
			diagnostics = append(diagnostics, "duplicate-adapter-lane:"+lane)
		}
		seenLanes[lane] = true
		adapter := adapterByID[adapterID]
		if adapter == nil || !sourceContinuityAdapterStringSet(sourceContinuityLabStringList(adapter["roles"]))[side] || !sourceContinuityAdapterStringSet(sourceContinuityLabStringList(adapter["capabilities"]))[capability] {
			diagnostics = append(diagnostics, "adapter-assignment-mismatch:"+lane)
		}
		if strings.TrimSpace(anyString(assignment["selection_reason"])) == "" {
			diagnostics = append(diagnostics, "adapter-assignment-reason-missing:"+lane)
		}
	}
	for _, lane := range sourceContinuityAdapterRequiredLanes() {
		if !seenLanes[lane] {
			diagnostics = append(diagnostics, "missing-adapter-lane:"+lane)
		}
	}
	return adapters, assignments, uniqueSourceContinuityLabDiagnostics(diagnostics)
}

func sourceContinuityAdapterRequiredLanes() []string {
	lanes := []string{}
	for _, side := range []string{"source", "target"} {
		for _, capability := range sourceContinuityLabCapabilities {
			lanes = append(lanes, side+"."+capability)
		}
	}
	return lanes
}

func sourceContinuityAdapterAllowedValues(values []string, allowed map[string]bool) bool {
	if len(values) != len(sourceContinuityAdapterStringSet(values)) {
		return false
	}
	for _, value := range values {
		if !allowed[value] {
			return false
		}
	}
	return true
}

func sourceContinuityAdapterStringSet(values []string) map[string]bool {
	result := map[string]bool{}
	for _, value := range values {
		if value = strings.TrimSpace(value); value != "" {
			result[value] = true
		}
	}
	return result
}

func validateCurrentFeatureSourceContinuityManifest(root, feature, taskID string, manifest map[string]any) error {
	indexPath := filepath.Join(feature, "task-index.json")
	index, err := readImplementJSONMap(indexPath)
	if err != nil {
		return err
	}
	_, task, err := findImplementTask(index, taskID)
	if err != nil {
		return err
	}
	ui, _ := task["ui_contract"].(map[string]any)
	continuity, _ := ui["source_continuity"].(map[string]any)
	source, _ := manifest["source"].(map[string]any)
	targetSnapshot, err := sourceContinuityLabTargetSnapshot(root, sourceContinuityLabTaskWriteScope(task))
	if err != nil {
		return err
	}
	if manifest["schema"] != sourceContinuityLabManifestSchema || anyString(manifest["task_id"]) != taskID || !reflect.DeepEqual(manifest["source_continuity"], continuity) || anyString(manifest["source_continuity_sha256"]) != sourceContinuityLabContractSHA(continuity) || anyString(source["task_index_sha256"]) != optionalFileSHA256(indexPath) || anyString(source["target_snapshot_sha256"]) != targetSnapshot {
		return errors.New("source continuity manifest no longer matches the current task contract")
	}
	return nil
}

func validateCurrentQuickSourceContinuityManifest(context *sourceContinuityQuickContext, manifest map[string]any) error {
	source, _ := manifest["source"].(map[string]any)
	targetSnapshot, err := sourceContinuityLabTargetSnapshot(context.root, context.item.WriteScope)
	if err != nil {
		return err
	}
	if manifest["schema"] != sourceContinuityLabManifestSchema || anyString(manifest["task_id"]) != context.itemID || !reflect.DeepEqual(manifest["source_continuity"], context.continuity) || anyString(manifest["source_continuity_sha256"]) != sourceContinuityLabContractSHA(context.continuity) || anyString(source["confirmation_digest"]) != context.doc.ConfirmationDigest || anyString(source["target_snapshot_sha256"]) != targetSnapshot {
		return errors.New("source continuity manifest no longer matches the current quick decision")
	}
	return nil
}

func loadSourceContinuityAdapterPlan(container, subjectID, ref, sha, manifestRef, manifestSHA string, quick bool) (map[string]any, error) {
	expectedRef := sourceContinuityAdapterPlanRef(subjectID)
	if quick {
		expectedRef = sourceContinuityAdapterQuickPlanRef(subjectID)
	}
	if filepath.ToSlash(strings.TrimSpace(ref)) != expectedRef || !reviewSHA256RE.MatchString(strings.TrimSpace(sha)) {
		return nil, errors.New("adapter plan ref and SHA-256 must use the canonical subject binding")
	}
	path, err := secureFeatureRelativePath(container, expectedRef)
	if err != nil {
		return nil, errors.New("adapter plan path is unsafe")
	}
	raw, err := os.ReadFile(path)
	if err != nil || taskControlSHA256(raw) != sha {
		return nil, errors.New("adapter plan SHA-256 must bind the canonical plan")
	}
	var plan map[string]any
	if err := json.Unmarshal(raw, &plan); err != nil {
		return nil, errors.New("adapter plan must contain a JSON object")
	}
	if exactVisualComparisonFields(plan, map[string]bool{
		"schema": true, "adapter_protocol": true, "plan_id": true, "subject_id": true,
		"status": true, "binding": true, "selection": true, "required_lanes": true,
		"adapters": true, "assignments": true, "unresolved_gaps": true,
	}, "source continuity adapter plan") != nil {
		return nil, errors.New("adapter plan contains unsupported fields")
	}
	binding, _ := plan["binding"].(map[string]any)
	selection, selectionOK := plan["selection"].(map[string]any)
	input := map[string]any{
		"schema":          sourceContinuityAdapterInputSchema,
		"adapters":        plan["adapters"],
		"assignments":     plan["assignments"],
		"unresolved_gaps": plan["unresolved_gaps"],
	}
	_, _, diagnostics := validateSourceContinuityAdapterPlanInput(input)
	if !selectionOK {
		diagnostics = append(diagnostics, "invalid-adapter-selection")
	} else {
		diagnostics = append(diagnostics, validateSourceContinuityAdapterSelection(selection)...)
		if anyString(selection["mode"]) == "registry-probe" {
			diagnostics = append(diagnostics, validateSourceContinuityAdapterProbeSelection(container, subjectID, manifestRef, manifestSHA, selection, plan, quick)...)
		}
	}
	lanes := sourceContinuityLabStringList(plan["required_lanes"])
	if plan["schema"] != sourceContinuityAdapterPlanSchema || plan["adapter_protocol"] != sourceContinuityAdapterProtocol || plan["status"] != "ready" || anyString(plan["subject_id"]) != subjectID || !sourceContinuityLabExactIDs(lanes, sourceContinuityAdapterRequiredLanes()) || anyString(binding["manifest_ref"]) != manifestRef || anyString(binding["manifest_sha256"]) != manifestSHA {
		diagnostics = append(diagnostics, "stale-adapter-plan")
	}
	if len(diagnostics) > 0 {
		return nil, fmt.Errorf("adapter plan is invalid: %s", strings.Join(uniqueSourceContinuityLabDiagnostics(diagnostics), ", "))
	}
	return plan, nil
}

func validateSourceContinuityAdapterObservation(plan map[string]any, planRef, planSHA string, raw map[string]any) []string {
	diagnostics := []string{}
	if anyString(raw["adapter_plan_ref"]) != planRef || anyString(raw["adapter_plan_sha256"]) != planSHA {
		diagnostics = append(diagnostics, "stale-adapter-plan")
	}
	expectedComposite := map[string]any{
		"id":           "adapter-plan:" + planSHA[:12],
		"version":      "1",
		"capabilities": stringsToAny(sourceContinuityLabCapabilities),
	}
	if !reflect.DeepEqual(raw["adapter"], expectedComposite) {
		diagnostics = append(diagnostics, "adapter-plan-composite-mismatch")
	}
	adapterByID := map[string]map[string]any{}
	for _, value := range listValue(plan["adapters"]) {
		adapter, ok := value.(map[string]any)
		if ok {
			adapterByID[anyString(adapter["id"])] = adapter
		}
	}
	observed := map[string]bool{}
	for _, value := range listValue(raw["evidence_refs"]) {
		row, ok := value.(map[string]any)
		if !ok {
			continue
		}
		adapterID := strings.TrimSpace(anyString(row["adapter_id"]))
		side := strings.TrimSpace(anyString(row["side"]))
		kind := strings.TrimSpace(anyString(row["kind"]))
		adapter := adapterByID[adapterID]
		if adapterID == "" || adapter == nil || !sourceContinuityAdapterStringSet(sourceContinuityLabStringList(adapter["roles"]))[side] || !sourceContinuityAdapterStringSet(sourceContinuityLabStringList(adapter["evidence_kinds"]))[kind] {
			diagnostics = append(diagnostics, "evidence-adapter-assignment-mismatch:"+side+":"+kind)
			continue
		}
		observed[adapterID+"|"+side+"|"+kind] = true
	}
	for _, value := range listValue(plan["assignments"]) {
		assignment, ok := value.(map[string]any)
		if !ok {
			continue
		}
		adapterID := anyString(assignment["adapter_id"])
		side := anyString(assignment["side"])
		capability := anyString(assignment["capability"])
		kind := sourceContinuityAdapterCapabilityEvidence[capability]
		if !observed[adapterID+"|"+side+"|"+kind] {
			diagnostics = append(diagnostics, "evidence-adapter-assignment-mismatch:"+side+"."+capability)
		}
	}
	return uniqueSourceContinuityLabDiagnostics(diagnostics)
}

func sourceContinuityLabNotApplicable(taskID, reason string) Envelope {
	env := NewEnvelope("ok", "source continuity lab not applicable")
	env.Data = map[string]any{"task_id": taskID, "applicable": false, "status": "not-applicable", "reason": reason}
	return env
}

type sourceContinuityQuickContext struct {
	root             string
	workspace        string
	workspacePath    string
	itemID           string
	confirmationPath string
	doc              *quickConfirmationDoc
	continuity       map[string]any
	item             quickConfirmationItem
}

func (service evidenceService) sourceContinuityQuickContext(args []string, quickID string) (*sourceContinuityQuickContext, error) {
	root, err := filepath.Abs(service.projectRoot)
	if err != nil {
		return nil, errors.New("source continuity quick project root is invalid")
	}
	quick := quickService{projectRoot: root}
	quickRoot, err := quick.root()
	if err != nil {
		return nil, err
	}
	tasks, err := quick.scan(quickRoot)
	if err != nil {
		return nil, err
	}
	task, err := matchQuickTask(tasks, quickID)
	if err != nil {
		return nil, err
	}
	workspacePath := strings.TrimSpace(anyString(task["workspace_path"]))
	workspace := strings.TrimSpace(anyString(task["workspace"]))
	doc, err := quick.loadConfirmation(workspacePath)
	if err != nil {
		return nil, err
	}
	if err := requireQuickCheckpointExecutable(doc); err != nil {
		return nil, err
	}
	itemID := strings.TrimSpace(firstNonEmpty(optionValue(args, "--item-id", ""), optionValue(args, "--item", "")))
	if itemID == "" {
		return nil, errors.New("source continuity quick lab requires --item-id Qn")
	}
	item, ok := findQuickItem(doc, itemID)
	if !ok {
		return nil, fmt.Errorf("unknown quick work item %s", itemID)
	}
	if strings.ToLower(strings.TrimSpace(quickStatusMap(doc)[itemID].Status)) != "in_progress" {
		return nil, fmt.Errorf("quick work item %s must be in_progress before source continuity evidence is generated", itemID)
	}
	continuity, ok := doc.Decision.UIConfirmation["source_continuity"].(map[string]any)
	if !ok || strings.TrimSpace(anyString(continuity["applicability"])) != "required" {
		return nil, errors.New("quick work item has no required source continuity contract")
	}
	if err := validateDesignSourceContinuity(continuity, "ui_confirmation.source_continuity", true); err != nil {
		return nil, err
	}
	return &sourceContinuityQuickContext{
		root: root, workspace: workspace, workspacePath: workspacePath, itemID: itemID,
		confirmationPath: filepath.Join(workspacePath, quickConfirmationFileName), doc: doc,
		continuity: continuity, item: item,
	}, nil
}

func (service evidenceService) sourceContinuityQuickManifest(args []string, quickID string) Envelope {
	context, err := service.sourceContinuityQuickContext(args, quickID)
	if err != nil {
		return evidenceUsageError(err.Error())
	}
	contractRaw, err := marshalReviewAcceptJSON(context.continuity)
	if err != nil {
		return evidenceBlockedError("source continuity contract cannot be canonicalized", err)
	}
	confirmationRef, err := filepath.Rel(context.root, context.confirmationPath)
	if err != nil {
		return evidenceBlockedError("quick confirmation path is invalid", err)
	}
	targetSnapshot, err := sourceContinuityLabTargetSnapshot(context.root, context.item.WriteScope)
	if err != nil {
		return evidenceBlockedError("quick source continuity target snapshot is unavailable", err)
	}
	manifest := map[string]any{
		"schema": sourceContinuityLabManifestSchema, "task_id": context.itemID,
		"source_continuity_schema":      anyString(context.continuity["schema"]),
		"source_continuity_sha256":      fileContentSHA256(contractRaw),
		"source_continuity":             cloneJSONValue(context.continuity),
		"required_adapter_capabilities": stringsToAny(sourceContinuityLabCapabilities),
		"required_evidence":             stringsToAny(sourceContinuityLabEvidenceKinds),
		"source": map[string]any{
			"confirmation_ref":       filepath.ToSlash(confirmationRef),
			"confirmation_digest":    context.doc.ConfirmationDigest,
			"target_snapshot_sha256": targetSnapshot,
			"quick_id":               quickID, "item_id": context.itemID,
		},
	}
	rendered, err := marshalReviewAcceptJSON(manifest)
	if err != nil {
		return evidenceBlockedError("source continuity manifest cannot be rendered", err)
	}
	manifestRef := sourceContinuityLabQuickManifestRef(context.itemID)
	canonicalPath := sourceContinuityLabCanonicalPath(context.root, context.workspacePath, manifestRef)
	if err := validateQuickSourceContinuityLabArtifactOwner(canonicalPath); err != nil {
		return evidenceBlockedError("quick source continuity manifest path is not owned by its specialized CLI", err)
	}
	manifestPath := filepath.Join(context.workspacePath, filepath.FromSlash(manifestRef))
	receipt, err := applyFileTransaction(context.root, "quick-source-continuity-manifest", []fileTransactionUpdate{{Path: manifestPath, Content: rendered, Perm: 0o644}})
	if err != nil {
		return evidenceBlockedError("quick source continuity manifest could not be written atomically", err)
	}
	env := NewEnvelope("ok", "quick source continuity lab manifest materialized")
	env.Data = map[string]any{
		"quick_id": quickID, "item_id": context.itemID, "applicable": true, "status": "ready",
		"manifest_ref": manifestRef, "manifest_sha256": fileContentSHA256(rendered),
		"transaction_receipt_ref": receipt.ReceiptRef,
	}
	env.ShowArgv = []string{"specify-runtime", "artifact", "show", "--path", canonicalPath, "--view", "summary", "--format", "json"}
	return env
}

func (service evidenceService) sourceContinuityQuickValidate(args []string, quickID string, raw map[string]any) Envelope {
	context, err := service.sourceContinuityQuickContext(args, quickID)
	if err != nil {
		return evidenceUsageError(err.Error())
	}
	manifestRef := filepath.ToSlash(strings.TrimSpace(optionValue(args, "--manifest", "")))
	if manifestRef != sourceContinuityLabQuickManifestRef(context.itemID) {
		return evidenceUsageError("quick source continuity manifest must be the canonical item-bound manifest")
	}
	manifestPath, err := secureFeatureRelativePath(context.workspacePath, manifestRef)
	if err != nil {
		return evidenceUsageError("quick source continuity manifest path is unsafe")
	}
	manifest, err := readImplementJSONMap(manifestPath)
	if err != nil {
		return evidenceBlockedError("quick source continuity manifest is unavailable", err)
	}
	diagnostics, metrics := validateSourceContinuityLabResult(context.itemID, manifest, optionalFileSHA256(manifestPath), raw)
	diagnostics = append(diagnostics, validateSourceContinuityLabEvidenceRecords(context.root, raw["evidence_refs"])...)
	source, sourceOK := manifest["source"].(map[string]any)
	targetSnapshot, snapshotErr := sourceContinuityLabTargetSnapshot(context.root, context.item.WriteScope)
	if !sourceOK || snapshotErr != nil || strings.TrimSpace(anyString(source["confirmation_digest"])) != context.doc.ConfirmationDigest || strings.TrimSpace(anyString(source["target_snapshot_sha256"])) != targetSnapshot || !reflect.DeepEqual(manifest["source_continuity"], context.continuity) || anyString(manifest["source_continuity_sha256"]) != sourceContinuityLabContractSHA(context.continuity) {
		diagnostics = append(diagnostics, "stale-manifest")
	}
	adapterPlanRef := filepath.ToSlash(strings.TrimSpace(optionValue(args, "--adapter-plan", "")))
	adapterPlanSHA := strings.TrimSpace(anyString(raw["adapter_plan_sha256"]))
	var adapterPlan map[string]any
	if adapterPlanRef == "" || anyString(raw["adapter_plan_ref"]) == "" || adapterPlanSHA == "" {
		diagnostics = append(diagnostics, "missing-adapter-plan")
	} else {
		adapterPlan, err = loadSourceContinuityAdapterPlan(context.workspacePath, context.itemID, adapterPlanRef, adapterPlanSHA, manifestRef, optionalFileSHA256(manifestPath), true)
		if err != nil {
			diagnostics = append(diagnostics, "stale-adapter-plan")
		} else {
			diagnostics = append(diagnostics, validateSourceContinuityAdapterObservation(adapterPlan, adapterPlanRef, adapterPlanSHA, raw)...)
		}
	}
	adapterExecutionRef := filepath.ToSlash(strings.TrimSpace(optionValue(args, "--adapter-execution", "")))
	adapterExecutionSHA := strings.TrimSpace(anyString(raw["adapter_execution_sha256"]))
	var adapterExecution map[string]any
	if adapterExecutionRef == "" || anyString(raw["adapter_execution_ref"]) == "" || adapterExecutionSHA == "" {
		diagnostics = append(diagnostics, "missing-adapter-execution")
	} else if adapterPlan != nil {
		adapterExecution, err = loadSourceContinuityAdapterExecution(context.workspacePath, context.itemID, adapterExecutionRef, adapterExecutionSHA, manifestRef, optionalFileSHA256(manifestPath), adapterPlanRef, adapterPlanSHA, true)
		if err != nil {
			diagnostics = append(diagnostics, "stale-adapter-execution")
		} else {
			diagnostics = append(diagnostics, validateSourceContinuityAdapterExecutionObservation(adapterExecution, adapterExecutionRef, adapterExecutionSHA, raw)...)
		}
	}
	diagnostics = uniqueSourceContinuityLabDiagnostics(diagnostics)
	if len(diagnostics) > 0 {
		env := NewEnvelope("error", strings.Join(diagnostics, "; "))
		env.Data = map[string]any{"quick_id": quickID, "item_id": context.itemID, "diagnostics": stringsToAny(diagnostics), "metrics": metrics}
		return env
	}
	report := map[string]any{
		"schema": sourceContinuityLabReportSchema, "task_id": context.itemID, "verdict": "passed",
		"manifest_ref": manifestRef, "manifest_sha256": optionalFileSHA256(manifestPath),
		"source_revision": anyString(raw["source_revision"]), "target_revision": anyString(raw["target_revision"]),
		"adapter": cloneJSONValue(raw["adapter"]), "evidence_refs": cloneJSONValue(raw["evidence_refs"]),
		"discovery": cloneJSONValue(raw["discovery"]), "surface_results": cloneJSONValue(raw["surface_results"]),
		"action_results": cloneJSONValue(raw["action_results"]), "asset_results": cloneJSONValue(raw["asset_results"]),
		"coverage": cloneJSONValue(context.continuity["coverage"]), "metrics": metrics, "reviewer": anyString(raw["reviewer"]),
		"source": map[string]any{
			"result_schema":          sourceContinuityLabResultSchema,
			"confirmation_digest":    context.doc.ConfirmationDigest,
			"target_snapshot_sha256": targetSnapshot,
			"quick_id":               quickID, "item_id": context.itemID,
		},
	}
	if adapterPlan != nil {
		report["adapter_plan_ref"] = adapterPlanRef
		report["adapter_plan_sha256"] = adapterPlanSHA
	}
	if adapterExecution != nil {
		report["adapter_execution_ref"] = adapterExecutionRef
		report["adapter_execution_sha256"] = adapterExecutionSHA
	}
	rendered, err := marshalReviewAcceptJSON(report)
	if err != nil {
		return evidenceBlockedError("quick source continuity lab report cannot be rendered", err)
	}
	reportRef := sourceContinuityLabQuickReportRef(context.itemID)
	canonicalPath := sourceContinuityLabCanonicalPath(context.root, context.workspacePath, reportRef)
	if err := validateQuickSourceContinuityLabArtifactOwner(canonicalPath); err != nil {
		return evidenceBlockedError("quick source continuity report path is not owned by its specialized CLI", err)
	}
	reportPath := filepath.Join(context.workspacePath, filepath.FromSlash(reportRef))
	receipt, err := applyFileTransaction(context.root, "quick-source-continuity-lab", []fileTransactionUpdate{{Path: reportPath, Content: rendered, Perm: 0o644}})
	if err != nil {
		return evidenceBlockedError("quick source continuity lab report could not be written atomically", err)
	}
	reportSHA := fileContentSHA256(rendered)
	coverage, _ := context.continuity["coverage"].(map[string]any)
	env := NewEnvelope("ok", "quick source continuity lab report materialized")
	env.Data = map[string]any{
		"quick_id": quickID, "item_id": context.itemID, "report_ref": reportRef, "report_sha256": reportSHA,
		"metrics": metrics, "transaction_receipt_ref": receipt.ReceiptRef,
		"ui_verification_patch": map[string]any{
			"source_continuity_lab_report_ref": reportRef, "source_continuity_lab_report_sha256": reportSHA,
			"source_continuity_adapter_plan_ref": adapterPlanRef, "source_continuity_adapter_plan_sha256": adapterPlanSHA,
			"source_continuity_adapter_execution_ref": adapterExecutionRef, "source_continuity_adapter_execution_sha256": adapterExecutionSHA,
			"covered_source_continuity_surface_ids":     cloneJSONValue(coverage["surface_ids"]),
			"covered_source_continuity_interaction_ids": cloneJSONValue(coverage["interaction_ids"]),
			"covered_source_continuity_component_ids":   cloneJSONValue(coverage["component_ids"]),
		},
	}
	env.ShowArgv = []string{"specify-runtime", "artifact", "show", "--path", canonicalPath, "--view", "summary", "--format", "json"}
	return env
}

func buildSourceContinuityLabManifest(root, feature, taskID, indexPath string, task, continuity map[string]any) (map[string]any, error) {
	contractRaw, err := marshalReviewAcceptJSON(continuity)
	if err != nil {
		return nil, errors.New("source continuity contract cannot be canonicalized")
	}
	projectRelativeFeature, err := filepath.Rel(root, feature)
	if err != nil {
		return nil, errors.New("source continuity feature path is invalid")
	}
	targetSnapshot, err := sourceContinuityLabTargetSnapshot(root, sourceContinuityLabTaskWriteScope(task))
	if err != nil {
		return nil, errors.New("source continuity target snapshot is unavailable")
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
			"feature_ref": filepath.ToSlash(projectRelativeFeature), "target_snapshot_sha256": targetSnapshot,
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

type sourceContinuityLabEvidenceBinding struct {
	Side      string
	Kind      string
	AdapterID string
}

func validateSourceContinuityLabEvidence(value any) (map[string]sourceContinuityLabEvidenceBinding, []string) {
	rows, ok := value.([]any)
	if !ok {
		return map[string]sourceContinuityLabEvidenceBinding{}, []string{"invalid-evidence-refs"}
	}
	refs := map[string]sourceContinuityLabEvidenceBinding{}
	covered := map[string]bool{}
	diagnostics := []string{}
	for _, value := range rows {
		row, ok := value.(map[string]any)
		expectedFields := map[string]bool{"side": true, "kind": true, "ref": true, "adapter_id": true}
		if !ok || exactVisualComparisonFields(row, expectedFields, "source continuity evidence") != nil {
			diagnostics = append(diagnostics, "invalid-evidence-ref")
			continue
		}
		side := strings.TrimSpace(anyString(row["side"]))
		kind := strings.TrimSpace(anyString(row["kind"]))
		ref := strings.TrimSpace(anyString(row["ref"]))
		adapterID := strings.TrimSpace(anyString(row["adapter_id"]))
		if (side != "source" && side != "target") || !quickContains(sourceContinuityLabEvidenceKinds, kind) || ref == "" || adapterID == "" {
			diagnostics = append(diagnostics, "invalid-evidence-ref")
			continue
		}
		binding := sourceContinuityLabEvidenceBinding{Side: side, Kind: kind, AdapterID: adapterID}
		if existing, exists := refs[ref]; exists && existing != binding {
			if existing.Side != side {
				diagnostics = append(diagnostics, "evidence-ref-side-conflict")
			} else {
				diagnostics = append(diagnostics, "evidence-ref-binding-conflict")
			}
		} else {
			refs[ref] = binding
		}
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

func validateSourceContinuityLabEvidenceRecords(root string, value any) []string {
	rows, ok := value.([]any)
	if !ok {
		return []string{"invalid-evidence-refs"}
	}
	service := evidenceService{projectRoot: root}
	diagnostics := []string{}
	for _, value := range rows {
		row, ok := value.(map[string]any)
		if !ok {
			continue
		}
		ref := filepath.ToSlash(strings.TrimSpace(anyString(row["ref"])))
		adapterID := strings.TrimSpace(anyString(row["adapter_id"]))
		if ref == "" || !strings.HasPrefix(ref, ".specify/evidence/records/") {
			diagnostics = append(diagnostics, "unverified-evidence-ref:"+ref)
			continue
		}
		env := service.verify(ref)
		record, err := service.readRecord(ref)
		provenanceValid := strings.TrimSpace(record.Provenance) != ""
		if adapterID != "" {
			provenanceValid = record.Provenance == "adapter:"+adapterID
		}
		if err != nil || env.Status != "ok" || record.SchemaVersion != evidenceSchemaVersion || filepath.ToSlash(record.RecordRef) != ref || record.Status != "ready" || record.SHA256 == "" || record.ObjectRef == "" || strings.TrimSpace(record.Source) == "" || !provenanceValid {
			diagnostics = append(diagnostics, "unverified-evidence-ref:"+ref)
		}
	}
	return diagnostics
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

func validateSourceContinuityLabActions(value any, expected []string, bindingValue any, evidenceRefs map[string]sourceContinuityLabEvidenceBinding) (int, int, []string) {
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
		sourceEvidence := evidenceRefs[strings.TrimSpace(anyString(row["source_evidence_ref"]))]
		targetEvidence := evidenceRefs[strings.TrimSpace(anyString(row["target_evidence_ref"]))]
		if sourceEvidence.Side != "source" || targetEvidence.Side != "target" {
			diagnostics = append(diagnostics, "action-evidence-unbound:"+id)
		} else if sourceEvidence.Kind != "runtime_diagnostics" || targetEvidence.Kind != "runtime_diagnostics" {
			diagnostics = append(diagnostics, "action-evidence-kind-mismatch:"+id)
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

func validateSourceContinuityLabAssets(value any, expected []string, bindingValue any, evidenceRefs map[string]sourceContinuityLabEvidenceBinding) (int, []string) {
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
		sourceEvidence := evidenceRefs[strings.TrimSpace(anyString(row["source_evidence_ref"]))]
		targetEvidence := evidenceRefs[strings.TrimSpace(anyString(row["target_evidence_ref"]))]
		if sourceEvidence.Side != "source" || targetEvidence.Side != "target" {
			diagnostics = append(diagnostics, "asset-evidence-unbound:"+id)
		} else if sourceEvidence.Kind != "visual_capture" || targetEvidence.Kind != "visual_capture" {
			diagnostics = append(diagnostics, "asset-evidence-kind-mismatch:"+id)
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

func sourceContinuityAdapterPlanRef(taskID string) string {
	return "implementation-review/source-continuity/source-continuity-adapter-plan-" + taskID + ".json"
}

func sourceContinuityLabQuickManifestRef(itemID string) string {
	return "source-continuity/source-continuity-manifest-" + itemID + ".json"
}

func sourceContinuityLabQuickReportRef(itemID string) string {
	return "source-continuity/source-continuity-lab-" + itemID + ".json"
}

func sourceContinuityAdapterQuickPlanRef(itemID string) string {
	return "source-continuity/source-continuity-adapter-plan-" + itemID + ".json"
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
	wantOwner := "specify-runtime evidence source-continuity-manifest / source-continuity-adapter-probe / source-continuity-adapter-plan / source-continuity-validate"
	if !ok || metadata.TypeID != "feature-source-continuity-lab" || metadata.Owner != wantOwner {
		return errors.New(canonicalPath)
	}
	return nil
}

func validateQuickSourceContinuityLabArtifactOwner(canonicalPath string) error {
	metadata, ok := LookupArtifactType(canonicalPath)
	wantOwner := "specify-runtime evidence source-continuity-manifest / source-continuity-adapter-probe / source-continuity-adapter-plan / source-continuity-validate"
	if !ok || metadata.TypeID != "quick-source-continuity-lab" || metadata.Owner != wantOwner {
		return errors.New(canonicalPath)
	}
	return nil
}

func validatePersistedQuickSourceContinuityLabReport(workspacePath string, doc *quickConfirmationDoc, itemID, reportRef, reportSHA256, expectedAdapterPlanRef, expectedAdapterPlanSHA, expectedAdapterExecutionRef, expectedAdapterExecutionSHA string) error {
	if reportRef != sourceContinuityLabQuickReportRef(itemID) {
		return errors.New("source continuity lab report must use the runtime-owned canonical quick item path")
	}
	reportPath, err := secureFeatureRelativePath(workspacePath, reportRef)
	if err != nil {
		return errors.New("source continuity lab report path is unsafe")
	}
	reportRaw, err := os.ReadFile(reportPath)
	if err != nil || taskControlSHA256(reportRaw) != reportSHA256 {
		return errors.New("source continuity lab report SHA-256 must bind the report")
	}
	var report map[string]any
	if err := json.Unmarshal(reportRaw, &report); err != nil {
		return errors.New("source continuity lab report must contain a JSON object")
	}
	if report["schema"] != sourceContinuityLabReportSchema || anyString(report["task_id"]) != itemID || strings.ToLower(strings.TrimSpace(anyString(report["verdict"]))) != "passed" {
		return errors.New("source continuity lab report identity or verdict is invalid")
	}
	manifestRef := filepath.ToSlash(strings.TrimSpace(anyString(report["manifest_ref"])))
	if manifestRef != sourceContinuityLabQuickManifestRef(itemID) {
		return errors.New("source continuity lab report must bind the runtime-owned quick manifest")
	}
	manifestPath, err := secureFeatureRelativePath(workspacePath, manifestRef)
	if err != nil {
		return errors.New("source continuity lab manifest path is unsafe")
	}
	manifestRaw, err := os.ReadFile(manifestPath)
	if err != nil || taskControlSHA256(manifestRaw) != anyString(report["manifest_sha256"]) {
		return errors.New("source continuity lab report manifest SHA-256 must bind the manifest")
	}
	var manifest map[string]any
	if err := json.Unmarshal(manifestRaw, &manifest); err != nil {
		return errors.New("source continuity lab manifest must contain a JSON object")
	}
	continuity, _ := doc.Decision.UIConfirmation["source_continuity"].(map[string]any)
	if !reflect.DeepEqual(manifest["source_continuity"], continuity) || anyString(manifest["source_continuity_sha256"]) != sourceContinuityLabContractSHA(continuity) {
		return errors.New("source continuity lab manifest contract binding is stale")
	}
	item, ok := findQuickItem(doc, itemID)
	if !ok {
		return errors.New("source continuity lab report requires the current quick item")
	}
	projectRoot, rootErr := sourceContinuityLabProjectRoot(workspacePath)
	targetSnapshot, snapshotErr := sourceContinuityLabTargetSnapshot(projectRoot, item.WriteScope)
	manifestSource, _ := manifest["source"].(map[string]any)
	reportSource, _ := report["source"].(map[string]any)
	adapterPlanRef := filepath.ToSlash(strings.TrimSpace(anyString(report["adapter_plan_ref"])))
	adapterPlanSHA := strings.TrimSpace(anyString(report["adapter_plan_sha256"]))
	if adapterPlanRef != expectedAdapterPlanRef || adapterPlanSHA != expectedAdapterPlanSHA {
		return errors.New("source continuity adapter plan verification binding is stale")
	}
	adapterPlan, adapterPlanErr := loadSourceContinuityAdapterPlan(workspacePath, itemID, adapterPlanRef, adapterPlanSHA, manifestRef, taskControlSHA256(manifestRaw), true)
	adapterExecutionRef := filepath.ToSlash(strings.TrimSpace(anyString(report["adapter_execution_ref"])))
	adapterExecutionSHA := strings.TrimSpace(anyString(report["adapter_execution_sha256"]))
	if adapterExecutionRef != expectedAdapterExecutionRef || adapterExecutionSHA != expectedAdapterExecutionSHA {
		return errors.New("source continuity adapter execution verification binding is stale")
	}
	adapterExecution, adapterExecutionErr := loadSourceContinuityAdapterExecution(workspacePath, itemID, adapterExecutionRef, adapterExecutionSHA, manifestRef, taskControlSHA256(manifestRaw), adapterPlanRef, adapterPlanSHA, true)
	validationInput := map[string]any{
		"schema": reportSource["result_schema"], "manifest_sha256": report["manifest_sha256"],
		"source_revision": report["source_revision"], "target_revision": report["target_revision"],
		"adapter": report["adapter"], "evidence_refs": report["evidence_refs"], "discovery": report["discovery"],
		"surface_results": report["surface_results"], "action_results": report["action_results"], "asset_results": report["asset_results"],
		"verdict": report["verdict"], "reviewer": report["reviewer"],
	}
	diagnostics, metrics := validateSourceContinuityLabResult(itemID, manifest, taskControlSHA256(manifestRaw), validationInput)
	if adapterPlanErr != nil {
		diagnostics = append(diagnostics, "stale-adapter-plan")
	} else {
		validationInput["adapter_plan_ref"] = adapterPlanRef
		validationInput["adapter_plan_sha256"] = adapterPlanSHA
		diagnostics = append(diagnostics, validateSourceContinuityAdapterObservation(adapterPlan, adapterPlanRef, adapterPlanSHA, validationInput)...)
	}
	if adapterExecutionErr != nil {
		diagnostics = append(diagnostics, "stale-adapter-execution")
	} else {
		validationInput["adapter_execution_ref"] = adapterExecutionRef
		validationInput["adapter_execution_sha256"] = adapterExecutionSHA
		diagnostics = append(diagnostics, validateSourceContinuityAdapterExecutionObservation(adapterExecution, adapterExecutionRef, adapterExecutionSHA, validationInput)...)
	}
	if rootErr == nil {
		diagnostics = append(diagnostics, validateSourceContinuityLabEvidenceRecords(projectRoot, report["evidence_refs"])...)
	}
	if rootErr != nil || snapshotErr != nil {
		return errors.New("source continuity lab target snapshot is unavailable")
	}
	if anyString(manifestSource["target_snapshot_sha256"]) != targetSnapshot || anyString(reportSource["target_snapshot_sha256"]) != targetSnapshot {
		return errors.New("source continuity lab target snapshot changed after the report was generated")
	}
	if anyString(manifestSource["confirmation_digest"]) != doc.ConfirmationDigest || anyString(reportSource["confirmation_digest"]) != doc.ConfirmationDigest {
		diagnostics = append(diagnostics, "stale-manifest")
	}
	if !reflect.DeepEqual(report["metrics"], metrics) {
		diagnostics = append(diagnostics, "metrics-mismatch")
	}
	if !reflect.DeepEqual(report["coverage"], continuity["coverage"]) {
		diagnostics = append(diagnostics, "coverage-mismatch")
	}
	diagnostics = uniqueSourceContinuityLabDiagnostics(diagnostics)
	if len(diagnostics) > 0 {
		return fmt.Errorf("source continuity lab report is invalid: %s", strings.Join(diagnostics, ", "))
	}
	return nil
}

func validatePersistedSourceContinuityLabReport(feature string, task map[string]any, reportRef, reportSHA256, expectedAdapterPlanRef, expectedAdapterPlanSHA, expectedAdapterExecutionRef, expectedAdapterExecutionSHA string) error {
	taskID := strings.ToUpper(strings.TrimSpace(anyString(task["id"])))
	if reportRef != sourceContinuityLabReportRef(taskID) {
		return errors.New("source continuity lab report must use the runtime-owned canonical task path")
	}
	reportPath, err := secureFeatureRelativePath(feature, reportRef)
	if err != nil {
		return errors.New("source continuity lab report path is unsafe")
	}
	reportRaw, err := os.ReadFile(reportPath)
	if err != nil || taskControlSHA256(reportRaw) != reportSHA256 {
		return errors.New("source continuity lab report SHA-256 must bind the report")
	}
	var report map[string]any
	if err := json.Unmarshal(reportRaw, &report); err != nil {
		return errors.New("source continuity lab report must contain a JSON object")
	}
	if report["schema"] != sourceContinuityLabReportSchema || strings.ToUpper(strings.TrimSpace(anyString(report["task_id"]))) != taskID || strings.ToLower(strings.TrimSpace(anyString(report["verdict"]))) != "passed" {
		return errors.New("source continuity lab report identity or verdict is invalid")
	}
	manifestRef := filepath.ToSlash(strings.TrimSpace(anyString(report["manifest_ref"])))
	if manifestRef != sourceContinuityLabManifestRef(taskID) {
		return errors.New("source continuity lab report must bind the runtime-owned task manifest")
	}
	manifestPath, err := secureFeatureRelativePath(feature, manifestRef)
	if err != nil {
		return errors.New("source continuity lab manifest path is unsafe")
	}
	manifestRaw, err := os.ReadFile(manifestPath)
	if err != nil || taskControlSHA256(manifestRaw) != strings.TrimSpace(anyString(report["manifest_sha256"])) {
		return errors.New("source continuity lab report manifest SHA-256 must bind the manifest")
	}
	var manifest map[string]any
	if err := json.Unmarshal(manifestRaw, &manifest); err != nil {
		return errors.New("source continuity lab manifest must contain a JSON object")
	}
	indexPath := filepath.Join(feature, "task-index.json")
	index, err := readImplementJSONMap(indexPath)
	if err != nil {
		return errors.New("source continuity lab report requires the current task index")
	}
	_, currentTask, err := findImplementTask(index, taskID)
	if err != nil {
		return errors.New("source continuity lab report requires the current task contract")
	}
	currentUI, _ := currentTask["ui_contract"].(map[string]any)
	currentContinuity, _ := currentUI["source_continuity"].(map[string]any)
	if !reflect.DeepEqual(manifest["source_continuity"], currentContinuity) || anyString(manifest["source_continuity_sha256"]) != sourceContinuityLabContractSHA(currentContinuity) {
		return errors.New("source continuity lab manifest contract binding is stale")
	}
	reportSource, _ := report["source"].(map[string]any)
	adapterPlanRef := filepath.ToSlash(strings.TrimSpace(anyString(report["adapter_plan_ref"])))
	adapterPlanSHA := strings.TrimSpace(anyString(report["adapter_plan_sha256"]))
	if adapterPlanRef != expectedAdapterPlanRef || adapterPlanSHA != expectedAdapterPlanSHA {
		return errors.New("source continuity adapter plan verification binding is stale")
	}
	adapterPlan, adapterPlanErr := loadSourceContinuityAdapterPlan(feature, taskID, adapterPlanRef, adapterPlanSHA, manifestRef, taskControlSHA256(manifestRaw), false)
	adapterExecutionRef := filepath.ToSlash(strings.TrimSpace(anyString(report["adapter_execution_ref"])))
	adapterExecutionSHA := strings.TrimSpace(anyString(report["adapter_execution_sha256"]))
	if adapterExecutionRef != expectedAdapterExecutionRef || adapterExecutionSHA != expectedAdapterExecutionSHA {
		return errors.New("source continuity adapter execution verification binding is stale")
	}
	adapterExecution, adapterExecutionErr := loadSourceContinuityAdapterExecution(feature, taskID, adapterExecutionRef, adapterExecutionSHA, manifestRef, taskControlSHA256(manifestRaw), adapterPlanRef, adapterPlanSHA, false)
	validationInput := map[string]any{
		"schema": reportSource["result_schema"], "manifest_sha256": report["manifest_sha256"],
		"source_revision": report["source_revision"], "target_revision": report["target_revision"],
		"adapter": report["adapter"], "evidence_refs": report["evidence_refs"], "discovery": report["discovery"],
		"surface_results": report["surface_results"], "action_results": report["action_results"], "asset_results": report["asset_results"],
		"verdict": report["verdict"], "reviewer": report["reviewer"],
	}
	diagnostics, metrics := validateSourceContinuityLabResult(taskID, manifest, taskControlSHA256(manifestRaw), validationInput)
	if adapterPlanErr != nil {
		diagnostics = append(diagnostics, "stale-adapter-plan")
	} else {
		validationInput["adapter_plan_ref"] = adapterPlanRef
		validationInput["adapter_plan_sha256"] = adapterPlanSHA
		diagnostics = append(diagnostics, validateSourceContinuityAdapterObservation(adapterPlan, adapterPlanRef, adapterPlanSHA, validationInput)...)
	}
	if adapterExecutionErr != nil {
		diagnostics = append(diagnostics, "stale-adapter-execution")
	} else {
		validationInput["adapter_execution_ref"] = adapterExecutionRef
		validationInput["adapter_execution_sha256"] = adapterExecutionSHA
		diagnostics = append(diagnostics, validateSourceContinuityAdapterExecutionObservation(adapterExecution, adapterExecutionRef, adapterExecutionSHA, validationInput)...)
	}
	manifestSource, _ := manifest["source"].(map[string]any)
	currentIndexSHA := optionalFileSHA256(indexPath)
	projectRoot, rootErr := sourceContinuityLabProjectRoot(feature)
	targetSnapshot, snapshotErr := sourceContinuityLabTargetSnapshot(projectRoot, sourceContinuityLabTaskWriteScope(currentTask))
	if rootErr == nil {
		diagnostics = append(diagnostics, validateSourceContinuityLabEvidenceRecords(projectRoot, report["evidence_refs"])...)
	}
	if rootErr != nil || snapshotErr != nil || strings.TrimSpace(anyString(manifestSource["task_index_ref"])) != "task-index.json" || strings.TrimSpace(anyString(manifestSource["task_index_sha256"])) != currentIndexSHA || strings.TrimSpace(anyString(reportSource["task_index_sha256"])) != currentIndexSHA || strings.TrimSpace(anyString(manifestSource["target_snapshot_sha256"])) != targetSnapshot || strings.TrimSpace(anyString(reportSource["target_snapshot_sha256"])) != targetSnapshot {
		diagnostics = append(diagnostics, "stale-manifest")
	}
	if !reflect.DeepEqual(report["metrics"], metrics) {
		diagnostics = append(diagnostics, "metrics-mismatch")
	}
	if !reflect.DeepEqual(report["coverage"], currentContinuity["coverage"]) {
		diagnostics = append(diagnostics, "coverage-mismatch")
	}
	diagnostics = uniqueSourceContinuityLabDiagnostics(diagnostics)
	if len(diagnostics) > 0 {
		return fmt.Errorf("source continuity lab report is invalid: %s", strings.Join(diagnostics, ", "))
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

func sourceContinuityLabContractSHA(continuity map[string]any) string {
	raw, err := marshalReviewAcceptJSON(continuity)
	if err != nil {
		return ""
	}
	return fileContentSHA256(raw)
}

func sourceContinuityLabTaskWriteScope(task map[string]any) []string {
	values := anyStringSlice(task["write_scope"])
	if scope, ok := task["scope"].(map[string]any); ok {
		values = append(values, anyStringSlice(scope["write_scope"])...)
	}
	seen := map[string]bool{}
	result := []string{}
	for _, value := range values {
		value = strings.TrimSpace(value)
		if value != "" && !seen[value] {
			seen[value] = true
			result = append(result, value)
		}
	}
	return result
}

func sourceContinuityLabProjectRoot(path string) (string, error) {
	current, err := filepath.Abs(path)
	if err != nil {
		return "", err
	}
	for {
		base := strings.ToLower(filepath.Base(current))
		if base == ".specify" || base == ".planning" || base == "specs" {
			return filepath.Dir(current), nil
		}
		parent := filepath.Dir(current)
		if parent == current {
			return "", errors.New("source continuity project root is not discoverable")
		}
		current = parent
	}
}

func sourceContinuityLabTargetSnapshot(root string, declared []string) (string, error) {
	rootAbs, err := filepath.Abs(root)
	if err != nil {
		return "", err
	}
	paths := []string{}
	seen := map[string]bool{}
	addFile := func(path string) error {
		rel, err := filepath.Rel(rootAbs, path)
		if err != nil || rel == ".." || strings.HasPrefix(rel, ".."+string(filepath.Separator)) {
			return errors.New("source continuity snapshot path escapes project root")
		}
		rel = filepath.ToSlash(rel)
		if !seen[rel] {
			seen[rel] = true
			paths = append(paths, rel)
		}
		return nil
	}
	walk := func(start string, _ bool) error {
		return filepath.WalkDir(start, func(path string, entry os.DirEntry, walkErr error) error {
			if walkErr != nil {
				return walkErr
			}
			if entry.IsDir() {
				if path != start && sourceContinuityLabIgnoredSnapshotDir(entry.Name()) {
					return filepath.SkipDir
				}
				return nil
			}
			info, err := entry.Info()
			if err != nil || !info.Mode().IsRegular() {
				return err
			}
			return addFile(path)
		})
	}
	if len(declared) > 0 {
		for _, raw := range declared {
			normalized := filepath.ToSlash(strings.TrimSpace(raw))
			if strings.HasSuffix(normalized, "/**") {
				normalized = strings.TrimSuffix(normalized, "/**")
			} else if strings.HasSuffix(normalized, "/*") {
				normalized = strings.TrimSuffix(normalized, "/*")
			}
			normalized = strings.TrimSuffix(normalized, "/")
			firstSegment := strings.ToLower(strings.Split(strings.TrimPrefix(normalized, "./"), "/")[0])
			if firstSegment == ".specify" || firstSegment == ".planning" {
				return "", errors.New("source continuity target scope cannot be runtime-owned")
			}
			path, err := secureProjectPath(rootAbs, normalized)
			if err != nil {
				return "", err
			}
			info, err := os.Stat(path)
			if os.IsNotExist(err) {
				if err := addFile(path); err != nil {
					return "", err
				}
				continue
			}
			if err != nil {
				return "", err
			}
			if info.IsDir() {
				if err := walk(path, true); err != nil {
					return "", err
				}
			} else if err := addFile(path); err != nil {
				return "", err
			}
		}
	} else if err := walk(rootAbs, false); err != nil {
		return "", err
	}
	sort.Strings(paths)
	digest := sha256.New()
	digest.Write([]byte("source-continuity-target-snapshot-v1\n"))
	for _, rel := range paths {
		digest.Write([]byte("PATH\n" + rel + "\n"))
		raw, err := os.ReadFile(filepath.Join(rootAbs, filepath.FromSlash(rel)))
		if os.IsNotExist(err) {
			digest.Write([]byte("MISSING\n"))
			continue
		}
		if err != nil {
			return "", err
		}
		digest.Write(raw)
		digest.Write([]byte("\n"))
	}
	return hex.EncodeToString(digest.Sum(nil)), nil
}

func sourceContinuityLabIgnoredSnapshotDir(name string) bool {
	normalized := strings.ToLower(strings.TrimSpace(name))
	if normalized == ".git" || normalized == ".specify" || normalized == ".planning" || normalized == ".venv" || normalized == "node_modules" || normalized == "__pycache__" || normalized == ".pytest_cache" || normalized == ".ruff_cache" || normalized == ".mypy_cache" {
		return true
	}
	return strings.HasPrefix(normalized, ".codex-") || strings.HasPrefix(normalized, "pytest-") || strings.HasPrefix(normalized, "test-tmp") || strings.HasPrefix(normalized, "test-run-")
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
