package main

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"os"
	"path/filepath"
	"reflect"
	"sort"
	"strings"
)

const sourceContinuityAdapterExecutionSchema = "spec-kit-source-continuity-adapter-execution-v1"

func (service evidenceService) sourceContinuityAdapterExecution(args []string) Envelope {
	context, err := service.resolveSourceContinuityAdapterProbeContext(args)
	if err != nil {
		return evidenceUsageError(err.Error())
	}
	planRef := filepath.ToSlash(strings.TrimSpace(optionValue(args, "--adapter-plan", "")))
	planSHA := strings.TrimSpace(optionValue(args, "--adapter-plan-sha256", ""))
	if planRef == "" || !reviewSHA256RE.MatchString(planSHA) {
		return evidenceUsageError("adapter execution requires --adapter-plan and --adapter-plan-sha256")
	}
	plan, err := loadSourceContinuityAdapterPlan(context.container, context.subjectID, planRef, planSHA, context.manifestRef, optionalFileSHA256(context.manifestPath), context.quick)
	if err != nil {
		return evidenceBlockedError("adapter execution requires a current validated plan", err)
	}
	execution, diagnostics := buildSourceContinuityAdapterExecution(context, planRef, planSHA, plan)
	if len(diagnostics) > 0 {
		env := NewEnvelope("error", strings.Join(diagnostics, "; "))
		env.Data = map[string]any{"subject_id": context.subjectID, "diagnostics": stringsToAny(diagnostics)}
		return env
	}
	rendered, err := marshalReviewAcceptJSON(execution)
	if err != nil {
		return evidenceBlockedError("adapter execution manifest cannot be rendered", err)
	}
	ref := sourceContinuityAdapterExecutionRef(context.subjectID, context.quick)
	path := filepath.Join(context.container, filepath.FromSlash(ref))
	canonicalPath := sourceContinuityLabCanonicalPath(context.root, context.container, ref)
	if context.quick {
		err = validateQuickSourceContinuityLabArtifactOwner(canonicalPath)
	} else {
		err = validateSourceContinuityLabArtifactOwner(canonicalPath)
	}
	if err != nil {
		return evidenceBlockedError("adapter execution path is not owned by its specialized CLI", err)
	}
	receipt, err := applyFileTransaction(context.root, "source-continuity-adapter-execution", []fileTransactionUpdate{{Path: path, Content: rendered, Perm: 0o644}})
	if err != nil {
		return evidenceBlockedError("adapter execution manifest could not be written atomically", err)
	}
	packetIDs := []string{}
	for _, value := range listValue(execution["packets"]) {
		packet, _ := value.(map[string]any)
		packetIDs = append(packetIDs, anyString(packet["id"]))
	}
	env := NewEnvelope("ok", "source continuity adapter execution manifest materialized")
	env.Data = map[string]any{
		"subject_id": context.subjectID, "adapter_execution_ref": ref,
		"adapter_execution_sha256": fileContentSHA256(rendered),
		"packet_ids":               stringsToAny(packetIDs), "transaction_receipt_ref": receipt.ReceiptRef,
	}
	env.ShowArgv = []string{"specify-runtime", "artifact", "show", "--path", canonicalPath, "--view", "summary", "--format", "json"}
	return env
}

func buildSourceContinuityAdapterExecution(context *sourceContinuityAdapterProbeContext, planRef, planSHA string, plan map[string]any) (map[string]any, []string) {
	diagnostics := []string{}
	adapterByID := map[string]map[string]any{}
	for _, value := range listValue(plan["adapters"]) {
		adapter, ok := value.(map[string]any)
		if !ok {
			diagnostics = append(diagnostics, "invalid-adapter-execution-adapter")
			continue
		}
		adapterByID[anyString(adapter["id"])] = adapter
	}
	assignmentsByAdapter := map[string][]map[string]any{}
	for _, value := range listValue(plan["assignments"]) {
		assignment, ok := value.(map[string]any)
		if !ok {
			diagnostics = append(diagnostics, "invalid-adapter-execution-assignment")
			continue
		}
		adapterID := anyString(assignment["adapter_id"])
		assignmentsByAdapter[adapterID] = append(assignmentsByAdapter[adapterID], assignment)
	}
	continuity, _ := context.manifest["source_continuity"].(map[string]any)
	packets := []any{}
	adapterIDs := make([]string, 0, len(assignmentsByAdapter))
	for adapterID := range assignmentsByAdapter {
		adapterIDs = append(adapterIDs, adapterID)
	}
	sort.Strings(adapterIDs)
	for _, adapterID := range adapterIDs {
		adapter := adapterByID[adapterID]
		if adapter == nil {
			diagnostics = append(diagnostics, "adapter-execution-assignment-missing-adapter:"+adapterID)
			continue
		}
		packet := sourceContinuityAdapterExecutionPacket(planSHA, adapter, assignmentsByAdapter[adapterID], continuity)
		packets = append(packets, packet)
	}
	binding := sourceContinuityAdapterManifestBinding(context.subjectID, context.mode, context.manifestRef, optionalFileSHA256(context.manifestPath), context.manifest)
	binding["adapter_plan_ref"] = planRef
	binding["adapter_plan_sha256"] = planSHA
	binding["adapter_selection"] = cloneJSONValue(plan["selection"])
	execution := map[string]any{
		"schema": sourceContinuityAdapterExecutionSchema, "subject_id": context.subjectID,
		"status": "ready", "binding": binding, "packets": packets, "unresolved_gaps": []any{},
	}
	if len(packets) == 0 {
		diagnostics = append(diagnostics, "adapter-execution-requires-packets")
	}
	return execution, uniqueSourceContinuityLabDiagnostics(diagnostics)
}

func sourceContinuityAdapterExecutionPacket(planSHA string, adapter map[string]any, assignments []map[string]any, continuity map[string]any) map[string]any {
	adapterID := anyString(adapter["id"])
	seed := sha256.Sum256([]byte(planSHA + "\n" + adapterID + "\n"))
	lanes := []string{}
	evidenceSet := map[string]bool{}
	capabilitySet := map[string]bool{}
	for _, assignment := range assignments {
		side := anyString(assignment["side"])
		capability := anyString(assignment["capability"])
		lanes = append(lanes, side+"."+capability)
		capabilitySet[capability] = true
		evidenceSet[side+":"+sourceContinuityAdapterCapabilityEvidence[capability]] = true
	}
	evidenceRequirements := []any{}
	for _, side := range []string{"source", "target"} {
		for _, kind := range sourceContinuityLabEvidenceKinds {
			if evidenceSet[side+":"+kind] {
				evidenceRequirements = append(evidenceRequirements, map[string]any{
					"side": side, "kind": kind, "adapter_id": adapterID,
				})
			}
		}
	}
	targets := map[string]any{
		"surface_binding_ids": []any{}, "action_binding_ids": []any{}, "asset_binding_ids": []any{},
	}
	if capabilitySet["surface-enumeration"] {
		targets["surface_binding_ids"] = stringsToAny(sourceContinuityLabBindingIDs(continuity["surface_bindings"]))
	}
	if capabilitySet["action-execution"] || capabilitySet["side-effect-observation"] {
		targets["action_binding_ids"] = stringsToAny(sourceContinuityLabBindingIDs(continuity["action_bindings"]))
	}
	if capabilitySet["asset-inspection"] || capabilitySet["visual-capture"] {
		targets["asset_binding_ids"] = stringsToAny(sourceContinuityLabBindingIDs(continuity["asset_bindings"]))
	}
	for field, value := range migrationAdapterTargets(capabilitySet, continuity) {
		targets[field] = value
	}
	preconditions := []any{"manifest-current", "adapter-plan-current", "tool-binding-available", "real-entrypoint-or-declared-substitute-ready"}
	if anyString(adapter["write_policy"]) == "isolated-test-data" {
		preconditions = append(preconditions, "isolated-test-data-prepared")
	}
	return map[string]any{
		"id": "SCAE-" + hex.EncodeToString(seed[:])[:12], "adapter_id": adapterID,
		"tool_ref": adapter["tool_ref"], "execution_mode": adapter["execution_mode"],
		"lanes": stringsToAny(lanes), "actions": cloneJSONValue(adapter["actions"]),
		"evidence_requirements": evidenceRequirements, "binding_targets": targets,
		"write_policy": adapter["write_policy"], "network_policy": adapter["network_policy"],
		"preconditions": preconditions,
		"stop_conditions": []any{
			"tool-unavailable", "permission-boundary", "unexpected-destructive-side-effect",
			"unbound-surface-action-or-asset", "runtime-crash-or-unrecoverable-state",
		},
	}
}

func sourceContinuityAdapterExecutionRef(subjectID string, quick bool) string {
	if quick {
		return "source-continuity/source-continuity-adapter-execution-" + subjectID + ".json"
	}
	return "implementation-review/source-continuity/source-continuity-adapter-execution-" + subjectID + ".json"
}

func loadSourceContinuityAdapterExecution(container, subjectID, ref, sha, manifestRef, manifestSHA, planRef, planSHA string, quick bool) (map[string]any, error) {
	expectedRef := sourceContinuityAdapterExecutionRef(subjectID, quick)
	if filepath.ToSlash(strings.TrimSpace(ref)) != expectedRef || !reviewSHA256RE.MatchString(strings.TrimSpace(sha)) {
		return nil, errors.New("adapter execution ref and SHA-256 must use the canonical subject binding")
	}
	path, err := secureFeatureRelativePath(container, expectedRef)
	if err != nil {
		return nil, errors.New("adapter execution path is unsafe")
	}
	raw, err := os.ReadFile(path)
	if err != nil || taskControlSHA256(raw) != sha {
		return nil, errors.New("adapter execution SHA-256 must bind the canonical manifest")
	}
	var execution map[string]any
	if err := json.Unmarshal(raw, &execution); err != nil {
		return nil, errors.New("adapter execution must contain a JSON object")
	}
	if exactVisualComparisonFields(execution, map[string]bool{
		"schema": true, "subject_id": true, "status": true, "binding": true,
		"packets": true, "unresolved_gaps": true,
	}, "adapter execution manifest") != nil {
		return nil, errors.New("adapter execution contains unsupported fields")
	}
	binding, _ := execution["binding"].(map[string]any)
	if execution["schema"] != sourceContinuityAdapterExecutionSchema || execution["status"] != "ready" || anyString(execution["subject_id"]) != subjectID ||
		anyString(binding["manifest_ref"]) != manifestRef || anyString(binding["manifest_sha256"]) != manifestSHA ||
		anyString(binding["adapter_plan_ref"]) != planRef || anyString(binding["adapter_plan_sha256"]) != planSHA ||
		len(listValue(execution["packets"])) == 0 || len(listValue(execution["unresolved_gaps"])) != 0 {
		return nil, errors.New("adapter execution binding is stale")
	}
	plan, err := loadSourceContinuityAdapterPlan(container, subjectID, planRef, planSHA, manifestRef, manifestSHA, quick)
	if err != nil {
		return nil, err
	}
	context := &sourceContinuityAdapterProbeContext{container: container, subjectID: subjectID, mode: anyString(binding["mode"]), manifestRef: manifestRef}
	manifestPath, err := secureFeatureRelativePath(container, manifestRef)
	if err != nil {
		return nil, err
	}
	context.manifestPath = manifestPath
	context.manifest, err = readImplementJSONMap(manifestPath)
	if err != nil {
		return nil, err
	}
	expected, diagnostics := buildSourceContinuityAdapterExecution(context, planRef, planSHA, plan)
	if len(diagnostics) > 0 || !reflect.DeepEqual(execution, expected) {
		return nil, errors.New("adapter execution manifest is not the deterministic projection of the current plan")
	}
	return execution, nil
}

func validateSourceContinuityAdapterExecutionObservation(execution map[string]any, executionRef, executionSHA string, raw map[string]any) []string {
	diagnostics := []string{}
	if anyString(raw["adapter_execution_ref"]) != executionRef || anyString(raw["adapter_execution_sha256"]) != executionSHA {
		diagnostics = append(diagnostics, "stale-adapter-execution")
	}
	observed := map[string]bool{}
	for _, value := range listValue(raw["evidence_refs"]) {
		row, ok := value.(map[string]any)
		if !ok {
			continue
		}
		key := anyString(row["adapter_id"]) + "|" + anyString(row["side"]) + "|" + anyString(row["kind"])
		observed[key] = true
	}
	for _, value := range listValue(execution["packets"]) {
		packet, ok := value.(map[string]any)
		if !ok {
			diagnostics = append(diagnostics, "invalid-adapter-execution-packet")
			continue
		}
		for _, requirementValue := range listValue(packet["evidence_requirements"]) {
			requirement, ok := requirementValue.(map[string]any)
			if !ok {
				diagnostics = append(diagnostics, "invalid-adapter-execution-evidence-requirement")
				continue
			}
			key := anyString(requirement["adapter_id"]) + "|" + anyString(requirement["side"]) + "|" + anyString(requirement["kind"])
			if !observed[key] {
				diagnostics = append(diagnostics, "adapter-execution-evidence-missing:"+anyString(packet["id"])+":"+anyString(requirement["side"])+":"+anyString(requirement["kind"]))
			}
		}
	}
	return uniqueSourceContinuityLabDiagnostics(diagnostics)
}
