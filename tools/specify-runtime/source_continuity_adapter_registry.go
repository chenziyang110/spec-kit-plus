package main

import (
	_ "embed"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"reflect"
	"sort"
	"strings"
)

const (
	sourceContinuityAdapterRegistrySchema   = "spec-kit-source-continuity-adapter-registry-v1"
	sourceContinuityAdapterProbeInputSchema = "spec-kit-source-continuity-adapter-probe-input-v1"
	sourceContinuityAdapterProbeSchema      = "spec-kit-source-continuity-adapter-probe-v1"
)

//go:embed source_continuity_adapter_registry.json
var sourceContinuityAdapterRegistryRaw []byte

type sourceContinuityAdapterProvider struct {
	ID                    string   `json:"id"`
	Version               string   `json:"version"`
	Capabilities          []string `json:"capabilities"`
	Actions               []string `json:"actions"`
	EvidenceKinds         []string `json:"evidence_kinds"`
	AllowedExecutionModes []string `json:"allowed_execution_modes"`
	WritePolicy           string   `json:"write_policy"`
	NetworkPolicy         string   `json:"network_policy"`
}

type sourceContinuityAdapterRegistry struct {
	Schema    string                            `json:"schema"`
	Providers []sourceContinuityAdapterProvider `json:"providers"`
}

type sourceContinuityAdapterProbeContext struct {
	root         string
	container    string
	subjectID    string
	mode         string
	manifestRef  string
	manifestPath string
	manifest     map[string]any
	quick        bool
}

type sourceContinuityAdapterProbeRoute struct {
	adapters            []any
	assignments         []any
	unresolvedGaps      []any
	unavailableBindings []any
	unselectedBindings  []any
	inventorySHA256     string
	diagnostics         []string
}

func (service evidenceService) sourceContinuityAdapterCatalog() Envelope {
	registry, payload, digest, err := loadSourceContinuityAdapterRegistry()
	if err != nil {
		return evidenceBlockedError("source continuity adapter registry is invalid", err)
	}
	env := NewEnvelope("ok", "source continuity adapter provider catalog")
	env.Data = map[string]any{
		"schema":          registry.Schema,
		"registry_sha256": digest,
		"providers":       cloneJSONValue(payload["providers"]),
	}
	env.NextArgv = []string{"specify-runtime", "evidence", "source-continuity-adapter-probe", "--help"}
	return env
}

func (service evidenceService) sourceContinuityAdapterProbe(args []string, raw map[string]any) Envelope {
	context, err := service.resolveSourceContinuityAdapterProbeContext(args)
	if err != nil {
		return evidenceUsageError(err.Error())
	}
	registry, _, registrySHA, err := loadSourceContinuityAdapterRegistry()
	if err != nil {
		return evidenceBlockedError("source continuity adapter registry is invalid", err)
	}
	route := routeSourceContinuityAdapters(raw, registry, registrySHA)
	if len(route.diagnostics) > 0 {
		env := NewEnvelope("error", strings.Join(route.diagnostics, "; "))
		env.Data = map[string]any{"subject_id": context.subjectID, "diagnostics": stringsToAny(route.diagnostics)}
		env.NextArgv = []string{"specify-runtime", "evidence", "source-continuity-adapter-catalog", "--format", "json"}
		return env
	}
	return service.materializeSourceContinuityAdapterProbe(context, raw, route, registrySHA)
}

func (service evidenceService) resolveSourceContinuityAdapterProbeContext(args []string) (*sourceContinuityAdapterProbeContext, error) {
	if quickID := strings.TrimSpace(optionValue(args, "--quick-id", "")); quickID != "" {
		context, err := service.sourceContinuityQuickContext(args, quickID)
		if err != nil {
			return nil, err
		}
		manifestRef := filepath.ToSlash(strings.TrimSpace(optionValue(args, "--manifest", "")))
		if manifestRef != sourceContinuityLabQuickManifestRef(context.itemID) {
			return nil, errors.New("quick adapter probe must bind the canonical item manifest")
		}
		manifestPath, err := secureFeatureRelativePath(context.workspacePath, manifestRef)
		if err != nil {
			return nil, errors.New("quick source continuity manifest path is unsafe")
		}
		manifest, err := readImplementJSONMap(manifestPath)
		if err != nil {
			return nil, errors.New("quick source continuity manifest is unavailable")
		}
		if err := validateCurrentQuickSourceContinuityManifest(context, manifest); err != nil {
			return nil, errors.New("quick source continuity manifest is stale")
		}
		return &sourceContinuityAdapterProbeContext{
			root: context.root, container: context.workspacePath, subjectID: context.itemID,
			mode: "quick", manifestRef: manifestRef, manifestPath: manifestPath,
			manifest: manifest, quick: true,
		}, nil
	}

	root, feature, err := taskControlFeature(args)
	if err != nil {
		return nil, err
	}
	taskID, err := normalizeTaskControlID(optionValue(args, "--task-id", ""))
	if err != nil {
		return nil, err
	}
	manifestRef := filepath.ToSlash(strings.TrimSpace(optionValue(args, "--manifest", "")))
	if manifestRef != sourceContinuityLabManifestRef(taskID) {
		return nil, errors.New("adapter probe must bind the canonical task manifest")
	}
	manifestPath, err := secureFeatureRelativePath(feature, manifestRef)
	if err != nil {
		return nil, errors.New("source continuity manifest path is unsafe")
	}
	manifest, err := readImplementJSONMap(manifestPath)
	if err != nil {
		return nil, errors.New("source continuity manifest is unavailable")
	}
	if err := validateCurrentFeatureSourceContinuityManifest(root, feature, taskID, manifest); err != nil {
		return nil, errors.New("source continuity manifest is stale")
	}
	return &sourceContinuityAdapterProbeContext{
		root: root, container: feature, subjectID: taskID, mode: "formal",
		manifestRef: manifestRef, manifestPath: manifestPath, manifest: manifest,
	}, nil
}

func (service evidenceService) materializeSourceContinuityAdapterProbe(
	context *sourceContinuityAdapterProbeContext,
	raw map[string]any,
	route sourceContinuityAdapterProbeRoute,
	registrySHA string,
) Envelope {
	status := "ready"
	if len(route.unresolvedGaps) > 0 {
		status = "blocked"
	}
	manifestSHA := optionalFileSHA256(context.manifestPath)
	probe := map[string]any{
		"schema":               sourceContinuityAdapterProbeSchema,
		"subject_id":           context.subjectID,
		"status":               status,
		"binding":              sourceContinuityAdapterManifestBinding(context.subjectID, context.mode, context.manifestRef, manifestSHA, context.manifest),
		"registry_schema":      sourceContinuityAdapterRegistrySchema,
		"registry_sha256":      registrySHA,
		"inventory_sha256":     route.inventorySHA256,
		"adapters":             cloneJSONValue(route.adapters),
		"assignments":          cloneJSONValue(route.assignments),
		"unavailable_bindings": cloneJSONValue(route.unavailableBindings),
		"unselected_bindings":  cloneJSONValue(route.unselectedBindings),
		"unresolved_gaps":      cloneJSONValue(route.unresolvedGaps),
	}
	probeRendered, err := marshalReviewAcceptJSON(probe)
	if err != nil {
		return evidenceBlockedError("adapter probe cannot be rendered", err)
	}
	probeRef := sourceContinuityAdapterProbeRef(context.subjectID, context.quick)
	probePath := filepath.Join(context.container, filepath.FromSlash(probeRef))
	canonicalProbePath := sourceContinuityLabCanonicalPath(context.root, context.container, probeRef)
	if context.quick {
		err = validateQuickSourceContinuityLabArtifactOwner(canonicalProbePath)
	} else {
		err = validateSourceContinuityLabArtifactOwner(canonicalProbePath)
	}
	if err != nil {
		return evidenceBlockedError("adapter probe path is not owned by its specialized CLI", err)
	}
	probeSHA := fileContentSHA256(probeRendered)
	if status == "blocked" {
		receipt, err := applyFileTransaction(context.root, "source-continuity-adapter-probe", []fileTransactionUpdate{{Path: probePath, Content: probeRendered, Perm: 0o644}})
		if err != nil {
			return evidenceBlockedError("blocked adapter probe could not be written atomically", err)
		}
		diagnostics := sourceContinuityAdapterGapDiagnostics(route.unresolvedGaps)
		env := NewEnvelope("error", strings.Join(diagnostics, "; "))
		env.Data = map[string]any{
			"subject_id": context.subjectID, "adapter_probe_ref": probeRef,
			"adapter_probe_sha256": probeSHA, "registry_sha256": registrySHA,
			"diagnostics": stringsToAny(diagnostics), "transaction_receipt_ref": receipt.ReceiptRef,
		}
		env.NextArgv = []string{"specify-runtime", "evidence", "source-continuity-adapter-catalog", "--format", "json"}
		env.ShowArgv = []string{"specify-runtime", "artifact", "show", "--path", canonicalProbePath, "--view", "summary", "--format", "json"}
		return env
	}

	planInput := map[string]any{
		"schema": sourceContinuityAdapterInputSchema, "adapters": route.adapters,
		"assignments": route.assignments, "unresolved_gaps": []any{},
	}
	selection := map[string]any{
		"mode": "registry-probe", "registry_schema": sourceContinuityAdapterRegistrySchema,
		"registry_sha256": registrySHA, "probe_ref": probeRef, "probe_sha256": probeSHA,
		"inventory_sha256": route.inventorySHA256,
	}
	planArtifact, diagnostics, err := buildSourceContinuityAdapterPlanArtifact(
		context.root, context.container, context.subjectID, context.mode,
		context.manifestRef, context.manifestPath, context.manifest, planInput,
		selection, context.quick,
	)
	if len(diagnostics) > 0 {
		env := NewEnvelope("error", strings.Join(diagnostics, "; "))
		env.Data = map[string]any{"subject_id": context.subjectID, "diagnostics": stringsToAny(diagnostics)}
		return env
	}
	if err != nil {
		return evidenceBlockedError("registry-routed adapter plan cannot be built", err)
	}
	receipt, err := applyFileTransaction(context.root, "source-continuity-adapter-probe", []fileTransactionUpdate{
		{Path: probePath, Content: probeRendered, Perm: 0o644},
		{Path: planArtifact.path, Content: planArtifact.rendered, Perm: 0o644},
	})
	if err != nil {
		return evidenceBlockedError("adapter probe and plan could not be written atomically", err)
	}
	env := sourceContinuityAdapterPlanEnvelope(planArtifact, receipt.ReceiptRef)
	env.Summary = "source continuity adapter probe selected a complete plan"
	env.Data["adapter_probe_ref"] = probeRef
	env.Data["adapter_probe_sha256"] = probeSHA
	env.Data["registry_sha256"] = registrySHA
	env.Data["inventory_sha256"] = route.inventorySHA256
	env.ShowArgv = []string{"specify-runtime", "artifact", "show", "--path", canonicalProbePath, "--view", "summary", "--format", "json"}
	return env
}

func loadSourceContinuityAdapterRegistry() (*sourceContinuityAdapterRegistry, map[string]any, string, error) {
	var registry sourceContinuityAdapterRegistry
	if err := json.Unmarshal(sourceContinuityAdapterRegistryRaw, &registry); err != nil {
		return nil, nil, "", err
	}
	var payload map[string]any
	if err := json.Unmarshal(sourceContinuityAdapterRegistryRaw, &payload); err != nil {
		return nil, nil, "", err
	}
	if err := validateSourceContinuityAdapterRegistry(registry, payload); err != nil {
		return nil, nil, "", err
	}
	canonical, err := marshalReviewAcceptJSON(payload)
	if err != nil {
		return nil, nil, "", err
	}
	return &registry, payload, fileContentSHA256(canonical), nil
}

func validateSourceContinuityAdapterRegistry(registry sourceContinuityAdapterRegistry, payload map[string]any) error {
	if registry.Schema != sourceContinuityAdapterRegistrySchema || len(registry.Providers) == 0 || exactVisualComparisonFields(payload, map[string]bool{"schema": true, "providers": true}, "adapter registry") != nil {
		return errors.New("adapter registry identity is invalid")
	}
	seen := map[string]bool{}
	allowedModes := map[string]bool{"runtime-managed": true, "agent-tool": true, "app-connector": true, "external-runner": true, "manual-attested": true}
	for _, provider := range registry.Providers {
		if !sourceContinuityAdapterIDPattern.MatchString(provider.ID) || provider.Version == "" || seen[provider.ID] {
			return fmt.Errorf("adapter provider identity is invalid: %s", provider.ID)
		}
		seen[provider.ID] = true
		if !sourceContinuityAdapterAllowedValues(provider.Capabilities, visualComparisonStringSet(sourceContinuityLabCapabilities)) ||
			!sourceContinuityAdapterAllowedValues(provider.Actions, sourceContinuityAdapterActions) ||
			!sourceContinuityAdapterAllowedValues(provider.EvidenceKinds, visualComparisonStringSet(sourceContinuityLabEvidenceKinds)) ||
			!sourceContinuityAdapterAllowedValues(provider.AllowedExecutionModes, allowedModes) ||
			!quickContains([]string{"read-only", "evidence-store-only", "isolated-test-data"}, provider.WritePolicy) ||
			!quickContains([]string{"denied", "declared-read-only"}, provider.NetworkPolicy) {
			return fmt.Errorf("adapter provider contract is invalid: %s", provider.ID)
		}
		actionSet := sourceContinuityAdapterStringSet(provider.Actions)
		evidenceSet := sourceContinuityAdapterStringSet(provider.EvidenceKinds)
		for _, capability := range provider.Capabilities {
			for _, action := range sourceContinuityAdapterCapabilityActions[capability] {
				if !actionSet[action] {
					return fmt.Errorf("adapter provider %s lacks action %s", provider.ID, action)
				}
			}
			if !evidenceSet[sourceContinuityAdapterCapabilityEvidence[capability]] {
				return fmt.Errorf("adapter provider %s lacks evidence for %s", provider.ID, capability)
			}
		}
	}
	return nil
}

func routeSourceContinuityAdapters(raw map[string]any, registry *sourceContinuityAdapterRegistry, registrySHA string) sourceContinuityAdapterProbeRoute {
	result := sourceContinuityAdapterProbeRoute{}
	canonical, err := marshalReviewAcceptJSON(raw)
	if err == nil {
		result.inventorySHA256 = fileContentSHA256(canonical)
	}
	if exactVisualComparisonFields(raw, map[string]bool{"schema": true, "bindings": true, "policy": true}, "adapter probe input") != nil {
		result.diagnostics = append(result.diagnostics, "invalid-adapter-probe-fields")
	}
	if raw["schema"] != sourceContinuityAdapterProbeInputSchema {
		result.diagnostics = append(result.diagnostics, "invalid-adapter-probe-schema")
	}
	policy, policyOK := raw["policy"].(map[string]any)
	if !policyOK || exactVisualComparisonFields(policy, map[string]bool{"allow_manual_attested": true, "preferred_binding_ids": true}, "adapter probe policy") != nil {
		result.diagnostics = append(result.diagnostics, "invalid-adapter-probe-policy")
		policy = map[string]any{}
	}
	allowManual, manualOK := policy["allow_manual_attested"].(bool)
	preferred := sourceContinuityLabStringList(policy["preferred_binding_ids"])
	if !manualOK || len(preferred) != len(sourceContinuityAdapterStringSet(preferred)) {
		result.diagnostics = append(result.diagnostics, "invalid-adapter-probe-policy")
	}
	providerByID := map[string]sourceContinuityAdapterProvider{}
	for _, provider := range registry.Providers {
		providerByID[provider.ID] = provider
	}
	bindings, bindingsOK := raw["bindings"].([]any)
	if !bindingsOK || len(bindings) == 0 {
		result.diagnostics = append(result.diagnostics, "adapter-probe-requires-bindings")
		bindings = []any{}
	}
	seenIDs := map[string]bool{}
	allAdapters := map[string]map[string]any{}
	bindingOrder := []string{}
	for _, value := range bindings {
		binding, ok := value.(map[string]any)
		if !ok || exactVisualComparisonFields(binding, map[string]bool{
			"id": true, "provider_ids": true, "roles": true, "tool_ref": true,
			"execution_mode": true, "available": true, "unavailable_reason": true,
		}, "adapter probe binding") != nil {
			result.diagnostics = append(result.diagnostics, "invalid-adapter-probe-binding")
			continue
		}
		id := strings.TrimSpace(anyString(binding["id"]))
		providerIDs := sourceContinuityLabStringList(binding["provider_ids"])
		roles := sourceContinuityLabStringList(binding["roles"])
		toolRef := strings.TrimSpace(anyString(binding["tool_ref"]))
		executionMode := strings.TrimSpace(anyString(binding["execution_mode"]))
		available, availableOK := binding["available"].(bool)
		unavailableReason := strings.TrimSpace(anyString(binding["unavailable_reason"]))
		if !sourceContinuityAdapterIDPattern.MatchString(id) || seenIDs[id] || len(providerIDs) == 0 || len(providerIDs) != len(sourceContinuityAdapterStringSet(providerIDs)) ||
			!sourceContinuityAdapterAllowedValues(roles, map[string]bool{"source": true, "target": true}) || len(roles) == 0 ||
			!sourceContinuityAdapterToolRefPattern.MatchString(toolRef) || !availableOK || (available && unavailableReason != "") || (!available && unavailableReason == "") {
			result.diagnostics = append(result.diagnostics, "invalid-adapter-probe-binding:"+id)
			continue
		}
		seenIDs[id] = true
		bindingOrder = append(bindingOrder, id)
		providers := []sourceContinuityAdapterProvider{}
		providerInvalid := false
		for _, providerID := range providerIDs {
			provider, exists := providerByID[providerID]
			if !exists {
				result.diagnostics = append(result.diagnostics, "unknown-adapter-provider:"+providerID)
				providerInvalid = true
				continue
			}
			if !quickContains(provider.AllowedExecutionModes, executionMode) {
				result.diagnostics = append(result.diagnostics, "adapter-provider-execution-mode-mismatch:"+id+":"+providerID)
				providerInvalid = true
			}
			providers = append(providers, provider)
		}
		if providerInvalid {
			continue
		}
		if !available || (executionMode == "manual-attested" && !allowManual) {
			reason := unavailableReason
			if reason == "" {
				reason = "manual-attested-disabled-by-policy"
			}
			result.unavailableBindings = append(result.unavailableBindings, map[string]any{"id": id, "reason": reason})
			continue
		}
		allAdapters[id] = mergeSourceContinuityAdapterProviders(id, roles, toolRef, executionMode, providers, registrySHA)
	}
	preferredSet := sourceContinuityAdapterStringSet(preferred)
	for id := range preferredSet {
		if !seenIDs[id] {
			result.diagnostics = append(result.diagnostics, "unknown-preferred-adapter-binding:"+id)
		}
	}
	result.diagnostics = uniqueSourceContinuityLabDiagnostics(result.diagnostics)
	if len(result.diagnostics) > 0 {
		return result
	}

	preferredRank := map[string]int{}
	for index, id := range preferred {
		preferredRank[id] = index
	}
	selectedIDs := map[string]bool{}
	for _, lane := range sourceContinuityAdapterRequiredLanes() {
		parts := strings.SplitN(lane, ".", 2)
		side, capability := parts[0], parts[1]
		candidates := []map[string]any{}
		for _, id := range bindingOrder {
			adapter := allAdapters[id]
			if adapter != nil && sourceContinuityAdapterStringSet(sourceContinuityLabStringList(adapter["roles"]))[side] && sourceContinuityAdapterStringSet(sourceContinuityLabStringList(adapter["capabilities"]))[capability] {
				candidates = append(candidates, adapter)
			}
		}
		if len(candidates) == 0 {
			result.unresolvedGaps = append(result.unresolvedGaps, map[string]any{
				"lane": lane, "reason": "no-available-provider-binding",
				"recovery": "bind an available catalog provider for this side and capability, then rerun the probe",
			})
			continue
		}
		sort.SliceStable(candidates, func(i, j int) bool {
			return sourceContinuityAdapterCandidateLess(candidates[i], candidates[j], preferredRank)
		})
		selected := candidates[0]
		selectedID := anyString(selected["id"])
		selectedIDs[selectedID] = true
		reason := "registry-probe:execution-mode-priority"
		if _, preferred := preferredRank[selectedID]; preferred {
			reason = "registry-probe:preferred-binding"
		}
		result.assignments = append(result.assignments, map[string]any{
			"side": side, "capability": capability, "adapter_id": selectedID,
			"selection_reason": reason,
		})
	}
	selectedOrder := make([]string, 0, len(selectedIDs))
	for id := range selectedIDs {
		selectedOrder = append(selectedOrder, id)
	}
	sort.Strings(selectedOrder)
	for _, id := range selectedOrder {
		result.adapters = append(result.adapters, allAdapters[id])
	}
	for _, id := range bindingOrder {
		if allAdapters[id] != nil && !selectedIDs[id] {
			result.unselectedBindings = append(result.unselectedBindings, id)
		}
	}
	return result
}

func mergeSourceContinuityAdapterProviders(id string, roles []string, toolRef, executionMode string, providers []sourceContinuityAdapterProvider, registrySHA string) map[string]any {
	capabilities := map[string]bool{}
	actions := map[string]bool{}
	evidenceKinds := map[string]bool{}
	writePolicy := "read-only"
	networkPolicy := "denied"
	for _, provider := range providers {
		for _, value := range provider.Capabilities {
			capabilities[value] = true
		}
		for _, value := range provider.Actions {
			actions[value] = true
		}
		for _, value := range provider.EvidenceKinds {
			evidenceKinds[value] = true
		}
		if sourceContinuityAdapterWritePolicyRank(provider.WritePolicy) > sourceContinuityAdapterWritePolicyRank(writePolicy) {
			writePolicy = provider.WritePolicy
		}
		if provider.NetworkPolicy == "declared-read-only" {
			networkPolicy = provider.NetworkPolicy
		}
	}
	return map[string]any{
		"id": id, "version": "registry:" + registrySHA[:12], "roles": stringsToAny(roles),
		"capabilities": stringsToAny(sourceContinuityAdapterOrderedSet(sourceContinuityLabCapabilities, capabilities)),
		"actions": stringsToAny(sourceContinuityAdapterOrderedSet([]string{
			"enumerate-surfaces", "enumerate-actions", "enumerate-assets", "activate-action",
			"observe-side-effects", "capture-structure", "capture-visual", "capture-runtime",
			"prepare-isolated-test-data",
		}, actions)),
		"evidence_kinds": stringsToAny(sourceContinuityAdapterOrderedSet(sourceContinuityLabEvidenceKinds, evidenceKinds)),
		"execution_mode": executionMode, "tool_ref": toolRef,
		"write_policy": writePolicy, "network_policy": networkPolicy,
	}
}

func sourceContinuityAdapterCandidateLess(left, right map[string]any, preferredRank map[string]int) bool {
	leftID, rightID := anyString(left["id"]), anyString(right["id"])
	leftPreferred, leftOK := preferredRank[leftID]
	rightPreferred, rightOK := preferredRank[rightID]
	if leftOK != rightOK {
		return leftOK
	}
	if leftOK && leftPreferred != rightPreferred {
		return leftPreferred < rightPreferred
	}
	modeRank := map[string]int{"runtime-managed": 0, "agent-tool": 1, "app-connector": 2, "external-runner": 3, "manual-attested": 4}
	leftMode, rightMode := modeRank[anyString(left["execution_mode"])], modeRank[anyString(right["execution_mode"])]
	if leftMode != rightMode {
		return leftMode < rightMode
	}
	return leftID < rightID
}

func sourceContinuityAdapterWritePolicyRank(value string) int {
	switch value {
	case "isolated-test-data":
		return 2
	case "evidence-store-only":
		return 1
	default:
		return 0
	}
}

func sourceContinuityAdapterOrderedSet(order []string, values map[string]bool) []string {
	result := []string{}
	for _, value := range order {
		if values[value] {
			result = append(result, value)
		}
	}
	return result
}

func sourceContinuityAdapterGapDiagnostics(gaps []any) []string {
	diagnostics := []string{}
	for _, value := range gaps {
		gap, _ := value.(map[string]any)
		lane := strings.TrimSpace(anyString(gap["lane"]))
		if lane != "" {
			diagnostics = append(diagnostics, "missing-adapter-lane:"+lane)
		}
	}
	return uniqueSourceContinuityLabDiagnostics(diagnostics)
}

func sourceContinuityAdapterProbeRef(subjectID string, quick bool) string {
	if quick {
		return "source-continuity/source-continuity-adapter-probe-" + subjectID + ".json"
	}
	return "implementation-review/source-continuity/source-continuity-adapter-probe-" + subjectID + ".json"
}

func validateSourceContinuityAdapterProbeSelection(container, subjectID, manifestRef, manifestSHA string, selection, plan map[string]any, quick bool) []string {
	registry, _, registrySHA, err := loadSourceContinuityAdapterRegistry()
	if err != nil || registry.Schema != anyString(selection["registry_schema"]) || registrySHA != anyString(selection["registry_sha256"]) {
		return []string{"stale-adapter-registry"}
	}
	expectedRef := sourceContinuityAdapterProbeRef(subjectID, quick)
	if filepath.ToSlash(strings.TrimSpace(anyString(selection["probe_ref"]))) != expectedRef {
		return []string{"stale-adapter-probe"}
	}
	path, err := secureFeatureRelativePath(container, expectedRef)
	if err != nil {
		return []string{"stale-adapter-probe"}
	}
	raw, err := os.ReadFile(path)
	if err != nil || taskControlSHA256(raw) != anyString(selection["probe_sha256"]) {
		return []string{"stale-adapter-probe"}
	}
	var probe map[string]any
	if err := json.Unmarshal(raw, &probe); err != nil {
		return []string{"stale-adapter-probe"}
	}
	if exactVisualComparisonFields(probe, map[string]bool{
		"schema": true, "subject_id": true, "status": true, "binding": true,
		"registry_schema": true, "registry_sha256": true, "inventory_sha256": true,
		"adapters": true, "assignments": true, "unavailable_bindings": true,
		"unselected_bindings": true, "unresolved_gaps": true,
	}, "source continuity adapter probe") != nil {
		return []string{"stale-adapter-probe"}
	}
	binding, _ := probe["binding"].(map[string]any)
	if probe["schema"] != sourceContinuityAdapterProbeSchema || probe["status"] != "ready" || anyString(probe["subject_id"]) != subjectID ||
		anyString(probe["registry_schema"]) != sourceContinuityAdapterRegistrySchema || anyString(probe["registry_sha256"]) != registrySHA ||
		anyString(probe["inventory_sha256"]) != anyString(selection["inventory_sha256"]) ||
		anyString(binding["manifest_ref"]) != manifestRef || anyString(binding["manifest_sha256"]) != manifestSHA ||
		!reflect.DeepEqual(probe["adapters"], plan["adapters"]) || !reflect.DeepEqual(probe["assignments"], plan["assignments"]) ||
		len(listValue(probe["unresolved_gaps"])) != 0 {
		return []string{"stale-adapter-probe"}
	}
	return nil
}
