package main

import (
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func migrationFixture(t *testing.T, name string) map[string]any {
	t.Helper()
	raw, err := os.ReadFile(filepath.Join("..", "..", "tests", "fixtures", "source-continuity-lab", name))
	if err != nil {
		t.Fatal(err)
	}
	var value map[string]any
	if err := json.Unmarshal(raw, &value); err != nil {
		t.Fatal(err)
	}
	return value
}

func TestUIMigrationContractAcceptsStateAssetAndNativeRequirements(t *testing.T) {
	contract := migrationFixture(t, "migration-contract.json")
	if err := validateDesignSourceContinuity(contract, "ui_contract.source_continuity", true); err != nil {
		t.Fatalf("complete migration contract rejected: %v", err)
	}
	observation := migrationFixture(t, "migration-observation.json")
	manifest := map[string]any{"schema": sourceContinuityLabManifestSchema, "task_id": "T001", "source_continuity": contract}
	if diagnostics, _ := validateSourceContinuityLabResult("T001", manifest, "runtime-filled", observation); len(diagnostics) != 0 {
		t.Fatalf("complete migration observations rejected: %v", diagnostics)
	}
}

func TestUIMigrationContractRejectsIncompleteRequirements(t *testing.T) {
	for _, damage := range []string{"missing-state", "missing-label", "wrong-size", "character", "missing-permission"} {
		t.Run(damage, func(t *testing.T) {
			contract := migrationFixture(t, "migration-contract.json")
			asset := mapValue(listValue(contract["asset_bindings"])[0])
			variants := mapValue(asset["state_variants"])
			rows := listValue(variants["variants"])
			switch damage {
			case "missing-state":
				variants["variants"] = rows[:len(rows)-1]
			case "missing-label":
				component := mapValue(listValue(mapValue(listValue(contract["surface_bindings"])[0])["component_states"])[0])
				states := listValue(component["states"])
				last := mapValue(states[len(states)-1])
				visuals := listValue(last["visuals"])
				last["visuals"] = visuals[:len(visuals)-1]
			case "wrong-size":
				mapValue(rows[len(rows)-1])["target_size"] = []any{24, 24}
			case "character":
				mapValue(rows[len(rows)-1])["target_ref"] = "text:↻"
			case "missing-permission":
				mapValue(mapValue(listValue(contract["action_bindings"])[0])["native_operation"])["permission_refs"] = []any{}
			}
			if err := validateDesignSourceContinuity(contract, "ui_contract.source_continuity", true); err == nil {
				t.Fatalf("%s requirement unexpectedly accepted", damage)
			}
		})
	}
}

func TestUIMigrationNativeAndAssetTargetsReachAdapters(t *testing.T) {
	contract := migrationFixture(t, "migration-contract.json")
	adapter := map[string]any{"id": "native-runner", "actions": []any{"activate-action"}}
	behavior := sourceContinuityAdapterExecutionPacket("digest", adapter, []map[string]any{{"side": "target", "capability": "action-execution"}}, contract)
	targets := mapValue(behavior["binding_targets"])
	states := listValue(targets["component_states"])
	if len(states) != 4 || anyString(mapValue(states[3])["state"]) != "disabled" || !migrationExactStrings(mapValue(states[3])["checks"], []any{"behavior"}) {
		t.Fatalf("behavior packet lost state targets: %#v", targets)
	}
	if _, exists := targets["asset_variants"]; exists {
		t.Fatal("behavior-only adapter received visual asset work")
	}
	visual := sourceContinuityAdapterExecutionPacket("digest", adapter, []map[string]any{{"side": "target", "capability": "visual-capture"}}, contract)
	variants := listValue(mapValue(visual["binding_targets"])["asset_variants"])
	if len(variants) != 4 || anyString(mapValue(variants[2])["state"]) != "pressed" {
		t.Fatalf("visual adapter lost original variants: %#v", variants)
	}
}

func TestUIMigrationLabPersistsAndRechecksDetailedEvidence(t *testing.T) {
	root, featureRef, feature := sourceContinuityLabProject(t)
	indexPath := filepath.Join(feature, "task-index.json")
	index := readImplementJSONFile(t, indexPath)
	task := mapValue(listValue(index["tasks"])[0])
	mapValue(task["ui_contract"])["source_continuity"] = migrationFixture(t, "migration-contract.json")
	mapValue(task["ui_contract"])["component_contracts"] = []any{map[string]any{"id": "DH-COMP-001", "anatomy": []any{"indicator", "label"}, "required_states": []any{"normal", "hover", "pressed", "disabled"}}}
	writeTaskRuntimeFixture(t, indexPath, index)
	manifestRef, manifestSHA := materializeSourceContinuityLabManifest(t, root, featureRef)
	observation := migrationFixture(t, "migration-observation.json")
	observation["manifest_sha256"] = manifestSHA
	planRef := prepareFeatureSourceContinuityAdapterPlan(t, root, featureRef, manifestRef, observation)
	bindSourceContinuityLabEvidence(t, root, observation)
	refs := map[string]string{}
	for _, value := range listValue(observation["evidence_refs"]) {
		row := mapValue(value)
		refs["evidence://"+anyString(row["side"])+"/"+anyString(row["kind"])] = anyString(row["ref"])
	}
	var bindRefs func(any) any
	bindRefs = func(value any) any {
		switch row := value.(type) {
		case map[string]any:
			for key, item := range row {
				row[key] = bindRefs(item)
			}
		case []any:
			for i, item := range row {
				row[i] = bindRefs(item)
			}
		case string:
			if replacement, ok := refs[row]; ok {
				return replacement
			}
		}
		return value
	}
	bindRefs(observation)
	raw, err := json.Marshal(observation)
	if err != nil {
		t.Fatal(err)
	}
	exit, env := runTaskRuntimeCommand(t, []string{"evidence", "source-continuity-validate", "--project-root", root, "--feature-dir", featureRef, "--task-id", sourceContinuityLabTaskID, "--manifest", manifestRef, "--adapter-plan", planRef, "--adapter-execution", anyString(observation["adapter_execution_ref"]), "--input-json", string(raw), "--format", "json"})
	if exit != 0 || env.Status != "ok" {
		t.Fatalf("complete migration evidence rejected: exit=%d env=%#v", exit, env)
	}
	reportRef := anyString(env.Data["report_ref"])
	verify := func(sha string) error {
		return validatePersistedSourceContinuityLabReport(feature, task, reportRef, sha, planRef, anyString(observation["adapter_plan_sha256"]), anyString(observation["adapter_execution_ref"]), anyString(observation["adapter_execution_sha256"]))
	}
	if err := verify(anyString(env.Data["report_sha256"])); err != nil {
		t.Fatalf("persisted migration report rejected: %v", err)
	}
	reportPath := filepath.Join(feature, filepath.FromSlash(reportRef))
	report := readImplementJSONFile(t, reportPath)
	mapValue(mapValue(listValue(report["action_results"])[0])["native_operation"])["verified_permission_refs"] = []any{}
	writeTaskRuntimeFixture(t, reportPath, report)
	if err := verify(optionalFileSHA256(reportPath)); err == nil || !strings.Contains(err.Error(), "native-operation-permission-mismatch") {
		t.Fatalf("rehashed invalid native evidence passed: %v", err)
	}
}

func TestUIMigrationManifestRejectsDriftedComponentAnatomy(t *testing.T) {
	root, featureRef, feature := sourceContinuityLabProject(t)
	indexPath := filepath.Join(feature, "task-index.json")
	index := readImplementJSONFile(t, indexPath)
	ui := mapValue(mapValue(listValue(index["tasks"])[0])["ui_contract"])
	ui["source_continuity"] = migrationFixture(t, "migration-contract.json")
	ui["component_contracts"] = []any{map[string]any{"id": "DH-COMP-001", "anatomy": []any{"indicator"}, "required_states": []any{"normal", "hover", "pressed", "disabled"}}}
	writeTaskRuntimeFixture(t, indexPath, index)
	exit, env := runTaskRuntimeCommand(t, []string{"evidence", "source-continuity-manifest", "--project-root", root, "--feature-dir", featureRef, "--task-id", sourceContinuityLabTaskID, "--format", "json"})
	if exit == 0 || env.Status == "ok" {
		t.Fatalf("stateful manifest accepted component anatomy that dropped the label: %#v", env)
	}
}

func TestUIMigrationAssetDenominatorCannotShrinkWithObservation(t *testing.T) {
	for _, shrinkInventory := range []bool{false, true} {
		contract := migrationFixture(t, "migration-contract.json")
		asset := mapValue(listValue(contract["asset_bindings"])[0])
		variants := mapValue(asset["state_variants"])
		variants["required_states"] = listValue(variants["required_states"])[:3]
		variants["variants"] = listValue(variants["variants"])[:3]
		if shrinkInventory {
			asset["source_refs"] = listValue(asset["source_refs"])[:3]
		}
		if validateDesignSourceContinuity(contract, "continuity", true) == nil {
			t.Fatal("asset denominator shrank below its source/component states")
		}
		components := []any{map[string]any{"id": "DH-COMP-001", "anatomy": []any{"indicator", "label"}, "required_states": []any{"normal", "hover", "pressed", "disabled"}}}
		if validateMigrationComponentBindings(contract, components) == nil {
			t.Fatal("asset denominator shrank below the component contract")
		}
		observation := migrationFixture(t, "migration-observation.json")
		result := mapValue(listValue(observation["asset_results"])[0])
		result["state_variants"] = listValue(result["state_variants"])[:3]
		refs, _ := validateSourceContinuityLabEvidence(observation["evidence_refs"])
		if len(migrationObservationErrors(contract, observation, refs)) == 0 {
			t.Fatal("shrunken source/result denominator passed")
		}
	}
}

func TestUIMigrationNativeEffectsUseDeclaredScalarFields(t *testing.T) {
	for name, after := range map[string]map[string]any{
		"numeric-spelling": {"x": float64(100), "y": float64(100)},
		"metadata-only":    {"x": float64(100), "y": float64(100), "timestamp": float64(2)},
		"missing-field":    {"x": float64(110)},
	} {
		t.Run(name, func(t *testing.T) {
			contract := migrationFixture(t, "migration-contract.json")
			observation := migrationFixture(t, "migration-observation.json")
			native := mapValue(mapValue(listValue(observation["action_results"])[0])["native_operation"])
			native["before"] = map[string]any{"x": 100, "y": 100, "timestamp": 1}
			native["after"] = after
			refs, _ := validateSourceContinuityLabEvidence(observation["evidence_refs"])
			if !strings.Contains(strings.Join(migrationObservationErrors(contract, observation, refs), "\n"), "native-operation-effect-mismatch") {
				t.Fatal("non-effect change passed")
			}
		})
	}
	contract := migrationFixture(t, "migration-contract.json")
	action := mapValue(listValue(contract["action_bindings"])[0])
	native := mapValue(action["native_operation"])
	native["effect_requirement"] = "observation"
	if validateDesignSourceContinuity(contract, "continuity", true) == nil {
		t.Fatal("side-effecting native action downgraded to observation")
	}
	action["side_effects"] = []any{}
	if err := validateDesignSourceContinuity(contract, "continuity", true); err != nil {
		t.Fatal(err)
	}
	state := map[string]any{"x": float64(100), "y": float64(100)}
	if !migrationEffectSatisfied(state, state, native) {
		t.Fatal("read-only native observation requires an unpromised state change")
	}
}

func TestUIMigrationRejectsFalsePositiveEvidence(t *testing.T) {
	for _, damage := range []string{"active-disabled-label", "enabled-disabled-control", "missing-state", "wrong-size", "character", "missing-permission", "stationary-window", "screenshot-only-native", "malformed-state", "malformed-visual-list", "boolean-size"} {
		t.Run(damage, func(t *testing.T) {
			contract := migrationFixture(t, "migration-contract.json")
			observation := migrationFixture(t, "migration-observation.json")
			surface := mapValue(listValue(observation["surface_results"])[0])
			states := listValue(surface["component_states"])
			disabled := mapValue(states[len(states)-1])
			asset := mapValue(listValue(observation["asset_results"])[0])
			variants := listValue(asset["state_variants"])
			native := mapValue(mapValue(listValue(observation["action_results"])[0])["native_operation"])
			expected := ""
			switch damage {
			case "active-disabled-label":
				visuals := listValue(disabled["visuals"])
				mapValue(visuals[len(visuals)-1])["matches"] = false
				expected = "component-state-visual-mismatch"
			case "enabled-disabled-control":
				disabled["behavior_matches"] = false
				expected = "component-state-behavior-mismatch"
			case "missing-state":
				asset["state_variants"] = variants[:len(variants)-1]
				expected = "asset-state-coverage-mismatch"
			case "wrong-size":
				mapValue(variants[len(variants)-1])["target_size"] = []any{24, 24}
				expected = "asset-state-size-mismatch"
			case "character":
				mapValue(variants[len(variants)-1])["character_substitution"] = true
				expected = "asset-state-character-substitution"
			case "missing-permission":
				native["verified_permission_refs"] = []any{}
				expected = "native-operation-permission-mismatch"
			case "stationary-window":
				native["after"] = cloneJSONValue(native["before"])
				expected = "native-operation-effect-mismatch"
			case "screenshot-only-native":
				native["effect_evidence_ref"] = "evidence://target/visual_capture"
				expected = "native-operation-evidence-kind-mismatch"
			case "malformed-state":
				disabled["state"] = map[string]any{"name": "disabled"}
				expected = "component-state-coverage-mismatch"
			case "malformed-visual-list":
				disabled["visuals"] = append(listValue(disabled["visuals"]), "not an observation")
				expected = "component-state-visual-coverage-mismatch"
			case "boolean-size":
				mapValue(variants[len(variants)-1])["target_size"] = []any{true, 26}
				expected = "asset-state-size-mismatch"
			}
			manifest := map[string]any{"schema": sourceContinuityLabManifestSchema, "task_id": "T001", "source_continuity": contract}
			diagnostics, _ := validateSourceContinuityLabResult("T001", manifest, "runtime-filled", observation)
			if !strings.Contains(strings.Join(diagnostics, "\n"), expected) {
				t.Fatalf("missing %s: %v", expected, diagnostics)
			}
		})
	}
}
