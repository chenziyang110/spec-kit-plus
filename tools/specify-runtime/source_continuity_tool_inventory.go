package main

import (
	"encoding/json"
	"os"
	"path/filepath"
	"reflect"
	"sort"
	"strings"
)

const (
	sourceContinuityToolInventoryInputSchema = "spec-kit-source-continuity-tool-inventory-input-v1"
	sourceContinuityToolInventorySchema      = "spec-kit-source-continuity-tool-inventory-v1"
)

func (service evidenceService) sourceContinuityAdapterBridge(args []string, raw map[string]any) Envelope {
	context, err := service.resolveSourceContinuityAdapterProbeContext(args)
	if err != nil {
		return evidenceUsageError(err.Error())
	}
	registry, _, registrySHA, err := loadSourceContinuityAdapterRegistry()
	if err != nil {
		return evidenceBlockedError("source continuity adapter registry is invalid", err)
	}
	probeInput, inventory, diagnostics := bridgeSourceContinuityToolInventory(raw, context, registry, registrySHA)
	if len(diagnostics) > 0 {
		env := NewEnvelope("error", strings.Join(diagnostics, "; "))
		env.Data = map[string]any{"subject_id": context.subjectID, "diagnostics": stringsToAny(diagnostics)}
		env.NextArgv = []string{"specify-runtime", "api", "schema", "source-continuity-tool-inventory-input", "--format", "json"}
		return env
	}
	inventoryRendered, err := marshalReviewAcceptJSON(inventory)
	if err != nil {
		return evidenceBlockedError("tool inventory report cannot be rendered", err)
	}
	inventoryRef := sourceContinuityToolInventoryRef(context.subjectID, context.quick)
	inventoryPath := filepath.Join(context.container, filepath.FromSlash(inventoryRef))
	canonicalPath := sourceContinuityLabCanonicalPath(context.root, context.container, inventoryRef)
	if context.quick {
		err = validateQuickSourceContinuityLabArtifactOwner(canonicalPath)
	} else {
		err = validateSourceContinuityLabArtifactOwner(canonicalPath)
	}
	if err != nil {
		return evidenceBlockedError("tool inventory path is not owned by its specialized CLI", err)
	}
	inventorySHA := fileContentSHA256(inventoryRendered)
	route := routeSourceContinuityAdapters(probeInput, registry, registrySHA)
	if len(route.diagnostics) > 0 {
		env := NewEnvelope("error", strings.Join(route.diagnostics, "; "))
		env.Data = map[string]any{"subject_id": context.subjectID, "diagnostics": stringsToAny(route.diagnostics)}
		env.NextArgv = []string{"specify-runtime", "evidence", "source-continuity-adapter-catalog", "--format", "json"}
		return env
	}
	route.inventoryBridge = map[string]any{
		"mode": "tool-inventory", "inventory_schema": sourceContinuityToolInventorySchema,
		"inventory_ref": inventoryRef, "inventory_sha256": inventorySHA,
	}
	return service.materializeSourceContinuityAdapterProbe(
		context,
		route,
		registrySHA,
		[]fileTransactionUpdate{{Path: inventoryPath, Content: inventoryRendered, Perm: 0o644}},
		map[string]any{
			"tool_inventory_ref": inventoryRef, "tool_inventory_sha256": inventorySHA,
			"visual_capabilities": cloneJSONValue(inventory["visual_capabilities"]),
		},
	)
}

func bridgeSourceContinuityToolInventory(
	raw map[string]any,
	context *sourceContinuityAdapterProbeContext,
	registry *sourceContinuityAdapterRegistry,
	registrySHA string,
) (map[string]any, map[string]any, []string) {
	diagnostics := []string{}
	if exactVisualComparisonFields(raw, map[string]bool{"schema": true, "source": true, "tools": true, "policy": true}, "source continuity tool inventory") != nil {
		diagnostics = append(diagnostics, "invalid-tool-inventory-fields")
	}
	if raw["schema"] != sourceContinuityToolInventoryInputSchema {
		diagnostics = append(diagnostics, "invalid-tool-inventory-schema")
	}
	source, sourceOK := raw["source"].(map[string]any)
	if !sourceOK || exactVisualComparisonFields(source, map[string]bool{"kind": true, "captured_by": true, "freshness": true}, "tool inventory source") != nil ||
		anyString(source["kind"]) != "live-session" || !quickContains([]string{"agent-observation", "runtime-api", "host-connector"}, anyString(source["captured_by"])) || anyString(source["freshness"]) != "current" {
		diagnostics = append(diagnostics, "invalid-tool-inventory-source")
		source = map[string]any{}
	}
	policy, policyOK := raw["policy"].(map[string]any)
	if !policyOK || exactVisualComparisonFields(policy, map[string]bool{"allow_manual_attested": true, "preferred_tool_ids": true}, "tool inventory policy") != nil {
		diagnostics = append(diagnostics, "invalid-tool-inventory-policy")
		policy = map[string]any{}
	}
	allowManual, manualOK := policy["allow_manual_attested"].(bool)
	preferredToolIDs := sourceContinuityLabStringList(policy["preferred_tool_ids"])
	if !manualOK || len(preferredToolIDs) > 32 || len(preferredToolIDs) != len(sourceContinuityAdapterStringSet(preferredToolIDs)) {
		diagnostics = append(diagnostics, "invalid-tool-inventory-policy")
	}
	allowedSignals := sourceContinuityToolInventorySignals(registry)
	tools, toolsOK := raw["tools"].([]any)
	if !toolsOK || len(tools) == 0 || len(tools) > 32 {
		diagnostics = append(diagnostics, "tool-inventory-requires-tools")
		tools = []any{}
	}
	seenIDs := map[string]bool{}
	normalizedTools := []map[string]any{}
	probeBindings := []map[string]any{}
	availableSignals := map[string]bool{}
	allowedUnavailableReasons := map[string]bool{"tool-missing": true, "permission-denied": true, "source-unavailable": true, "unsupported-mode": true, "manual-attestation-unavailable": true}
	for _, value := range tools {
		tool, ok := value.(map[string]any)
		if !ok || exactVisualComparisonFields(tool, map[string]bool{
			"id": true, "tool_ref": true, "signals": true, "roles": true,
			"execution_mode": true, "available": true, "unavailable_reason": true,
		}, "tool inventory entry") != nil {
			diagnostics = append(diagnostics, "invalid-tool-inventory-entry")
			continue
		}
		id := strings.TrimSpace(anyString(tool["id"]))
		toolRef := strings.TrimSpace(anyString(tool["tool_ref"]))
		signals := sourceContinuityLabStringList(tool["signals"])
		roles := sourceContinuityLabStringList(tool["roles"])
		executionMode := strings.TrimSpace(anyString(tool["execution_mode"]))
		available, availableOK := tool["available"].(bool)
		unavailableReason := strings.TrimSpace(anyString(tool["unavailable_reason"]))
		if !sourceContinuityAdapterIDPattern.MatchString(id) || len(id) > 128 || seenIDs[id] ||
			!sourceContinuityAdapterToolRefPattern.MatchString(toolRef) || len(toolRef) > 512 ||
			len(signals) == 0 || len(signals) > 32 || !sourceContinuityAdapterAllowedValues(signals, allowedSignals) ||
			len(roles) == 0 || !sourceContinuityAdapterAllowedValues(roles, map[string]bool{"source": true, "target": true}) ||
			!quickContains([]string{"runtime-managed", "agent-tool", "app-connector", "external-runner", "manual-attested"}, executionMode) ||
			!availableOK || (available && unavailableReason != "") || (!available && !allowedUnavailableReasons[unavailableReason]) {
			diagnostics = append(diagnostics, "invalid-tool-inventory-entry:"+id)
			continue
		}
		seenIDs[id] = true
		for _, signal := range signals {
			if available {
				availableSignals[signal] = true
			}
		}
		normalized := map[string]any{
			"id": id, "tool_ref": toolRef, "signals": stringsToAny(signals), "roles": stringsToAny(roles),
			"execution_mode": executionMode, "available": available, "unavailable_reason": unavailableReason,
		}
		normalizedTools = append(normalizedTools, normalized)
		providerIDs := sourceContinuityProvidersForSignals(signals, registry)
		if len(providerIDs) > 0 {
			probeBindings = append(probeBindings, map[string]any{
				"id": id, "provider_ids": stringsToAny(providerIDs), "roles": stringsToAny(roles),
				"tool_ref": toolRef, "execution_mode": executionMode,
				"available": available, "unavailable_reason": unavailableReason,
			})
		}
	}
	for _, id := range preferredToolIDs {
		if !seenIDs[id] {
			diagnostics = append(diagnostics, "unknown-preferred-tool:"+id)
		}
	}
	diagnostics = uniqueSourceContinuityLabDiagnostics(diagnostics)
	sort.SliceStable(normalizedTools, func(i, j int) bool { return anyString(normalizedTools[i]["id"]) < anyString(normalizedTools[j]["id"]) })
	sort.SliceStable(probeBindings, func(i, j int) bool { return anyString(probeBindings[i]["id"]) < anyString(probeBindings[j]["id"]) })
	bindingsAny := make([]any, 0, len(probeBindings))
	for _, binding := range probeBindings {
		bindingsAny = append(bindingsAny, binding)
	}
	probeInput := map[string]any{
		"schema":   sourceContinuityAdapterProbeInputSchema,
		"bindings": bindingsAny,
		"policy": map[string]any{
			"allow_manual_attested": allowManual,
			"preferred_binding_ids": stringsToAny(preferredToolIDs),
		},
	}
	probeInputRendered, _ := marshalReviewAcceptJSON(probeInput)
	toolsAny := make([]any, 0, len(normalizedTools))
	for _, tool := range normalizedTools {
		toolsAny = append(toolsAny, tool)
	}
	inventory := map[string]any{
		"schema": sourceContinuityToolInventorySchema, "subject_id": context.subjectID,
		"status": "ready", "binding": sourceContinuityAdapterManifestBinding(context.subjectID, context.mode, context.manifestRef, optionalFileSHA256(context.manifestPath), context.manifest),
		"registry_schema": sourceContinuityAdapterRegistrySchema, "registry_sha256": registrySHA,
		"source": cloneJSONValue(source), "tools": toolsAny, "policy": cloneJSONValue(policy),
		"visual_capabilities": map[string]any{
			"image_generation": sourceContinuityAvailability(availableSignals["image-generation"]),
			"image_inspection": sourceContinuityAvailability(availableSignals["image-inspection"]),
			"image_editing":    sourceContinuityAvailability(availableSignals["image-editing"]),
		},
		"generated_probe_input_sha256": fileContentSHA256(probeInputRendered),
	}
	return probeInput, inventory, diagnostics
}

func sourceContinuityToolInventorySignals(registry *sourceContinuityAdapterRegistry) map[string]bool {
	result := map[string]bool{"image-generation": true, "image-inspection": true, "image-editing": true}
	for _, provider := range registry.Providers {
		for _, signal := range provider.DetectionSignals {
			result[signal] = true
		}
	}
	return result
}

func sourceContinuityToolInventorySignalStrings() []string {
	registry, _, _, err := loadSourceContinuityAdapterRegistry()
	if err != nil {
		return []string{"image-generation", "image-inspection", "image-editing"}
	}
	signals := sourceContinuityToolInventorySignals(registry)
	result := make([]string, 0, len(signals))
	for signal := range signals {
		result = append(result, signal)
	}
	sort.Strings(result)
	return result
}

func sourceContinuityProvidersForSignals(signals []string, registry *sourceContinuityAdapterRegistry) []string {
	signalSet := sourceContinuityAdapterStringSet(signals)
	result := []string{}
	for _, provider := range registry.Providers {
		matched := false
		for _, signal := range provider.DetectionSignals {
			if signalSet[signal] {
				matched = true
				break
			}
		}
		if matched {
			result = append(result, provider.ID)
		}
	}
	return result
}

func sourceContinuityAvailability(available bool) string {
	if available {
		return "available"
	}
	return "unavailable"
}

func directSourceContinuityToolInventoryBridge() map[string]any {
	return map[string]any{
		"mode": "direct", "inventory_schema": "", "inventory_ref": "", "inventory_sha256": "",
	}
}

func sourceContinuityToolInventoryRef(subjectID string, quick bool) string {
	if quick {
		return "source-continuity/source-continuity-tool-inventory-" + subjectID + ".json"
	}
	return "implementation-review/source-continuity/source-continuity-tool-inventory-" + subjectID + ".json"
}

func validateSourceContinuityToolInventoryBridge(container, subjectID, manifestRef, manifestSHA string, bridge, probe map[string]any, quick bool) []string {
	if exactVisualComparisonFields(bridge, map[string]bool{"mode": true, "inventory_schema": true, "inventory_ref": true, "inventory_sha256": true}, "tool inventory bridge") != nil {
		return []string{"invalid-tool-inventory-bridge"}
	}
	mode := strings.TrimSpace(anyString(bridge["mode"]))
	if mode == "direct" {
		if anyString(bridge["inventory_schema"]) != "" || anyString(bridge["inventory_ref"]) != "" || anyString(bridge["inventory_sha256"]) != "" {
			return []string{"invalid-direct-tool-inventory-bridge"}
		}
		return nil
	}
	if mode != "tool-inventory" || bridge["inventory_schema"] != sourceContinuityToolInventorySchema || !reviewSHA256RE.MatchString(anyString(bridge["inventory_sha256"])) {
		return []string{"invalid-tool-inventory-bridge"}
	}
	expectedRef := sourceContinuityToolInventoryRef(subjectID, quick)
	if filepath.ToSlash(strings.TrimSpace(anyString(bridge["inventory_ref"]))) != expectedRef {
		return []string{"stale-tool-inventory"}
	}
	path, err := secureFeatureRelativePath(container, expectedRef)
	if err != nil {
		return []string{"stale-tool-inventory"}
	}
	raw, err := os.ReadFile(path)
	if err != nil || taskControlSHA256(raw) != anyString(bridge["inventory_sha256"]) {
		return []string{"stale-tool-inventory"}
	}
	var inventory map[string]any
	if err := json.Unmarshal(raw, &inventory); err != nil {
		return []string{"stale-tool-inventory"}
	}
	if exactVisualComparisonFields(inventory, map[string]bool{
		"schema": true, "subject_id": true, "status": true, "binding": true,
		"registry_schema": true, "registry_sha256": true, "source": true, "tools": true, "policy": true,
		"visual_capabilities": true, "generated_probe_input_sha256": true,
	}, "tool inventory report") != nil {
		return []string{"stale-tool-inventory"}
	}
	binding, _ := inventory["binding"].(map[string]any)
	if inventory["schema"] != sourceContinuityToolInventorySchema || inventory["status"] != "ready" || anyString(inventory["subject_id"]) != subjectID ||
		anyString(binding["manifest_ref"]) != manifestRef || anyString(binding["manifest_sha256"]) != manifestSHA ||
		anyString(inventory["registry_schema"]) != anyString(probe["registry_schema"]) || anyString(inventory["registry_sha256"]) != anyString(probe["registry_sha256"]) ||
		anyString(inventory["generated_probe_input_sha256"]) != anyString(probe["inventory_sha256"]) {
		return []string{"stale-tool-inventory"}
	}
	registry, _, registrySHA, err := loadSourceContinuityAdapterRegistry()
	if err != nil || registrySHA != anyString(inventory["registry_sha256"]) {
		return []string{"stale-tool-inventory"}
	}
	manifestPath, err := secureFeatureRelativePath(container, manifestRef)
	if err != nil {
		return []string{"stale-tool-inventory"}
	}
	manifest, err := readImplementJSONMap(manifestPath)
	if err != nil {
		return []string{"stale-tool-inventory"}
	}
	bindingMode := anyString(binding["mode"])
	context := &sourceContinuityAdapterProbeContext{
		container: container, subjectID: subjectID, mode: bindingMode,
		manifestRef: manifestRef, manifestPath: manifestPath, manifest: manifest, quick: quick,
	}
	replayInput := map[string]any{
		"schema": sourceContinuityToolInventoryInputSchema,
		"source": inventory["source"], "tools": inventory["tools"], "policy": inventory["policy"],
	}
	probeInput, expectedInventory, diagnostics := bridgeSourceContinuityToolInventory(replayInput, context, registry, registrySHA)
	if len(diagnostics) > 0 || !reflect.DeepEqual(inventory, expectedInventory) {
		return []string{"stale-tool-inventory"}
	}
	route := routeSourceContinuityAdapters(probeInput, registry, registrySHA)
	if len(route.diagnostics) > 0 || !reflect.DeepEqual(route.adapters, listValue(probe["adapters"])) || !reflect.DeepEqual(route.assignments, listValue(probe["assignments"])) {
		return []string{"stale-tool-inventory"}
	}
	return nil
}
