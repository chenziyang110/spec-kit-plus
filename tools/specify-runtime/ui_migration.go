package main

import (
	"fmt"
	"math"
	"reflect"
	"strings"
)

// These optional details belong to the existing source-continuity contract.
// Static sources omit them; a bound state/variant/native operation cannot be
// reduced to the surrounding result's aggregate PASS flag.
func migrationFields(row map[string]any, names ...string) bool {
	expected := map[string]bool{}
	for _, name := range names {
		expected[name] = true
	}
	return row != nil && exactVisualComparisonFields(row, expected, "UI migration detail") == nil
}

func migrationText(value any) bool {
	text, ok := value.(string)
	return ok && strings.TrimSpace(text) != ""
}

func migrationExactStrings(value, expected any) bool {
	actual, actualOK := migrationRawStrings(value)
	want, wantOK := migrationRawStrings(expected)
	actualSet, wantSet := map[string]bool{}, map[string]bool{}
	for _, item := range actual {
		actualSet[item] = true
	}
	for _, item := range want {
		wantSet[item] = true
	}
	return actualOK && wantOK && len(actual) == len(actualSet) && len(want) == len(wantSet) && reflect.DeepEqual(actualSet, wantSet)
}

func migrationRawStrings(value any) ([]string, bool) {
	items, ok := value.([]any)
	if !ok {
		stringsValue, stringsOK := value.([]string)
		if !stringsOK {
			return nil, false
		}
		items = make([]any, len(stringsValue))
		for i, item := range stringsValue {
			items[i] = item
		}
	}
	result := make([]string, 0, len(items))
	for _, item := range items {
		text, textOK := item.(string)
		if !textOK || strings.TrimSpace(text) == "" {
			return nil, false
		}
		result = append(result, text)
	}
	return result, true
}

func migrationStringValues(value any) []string {
	values, _ := migrationRawStrings(value)
	return values
}

func migrationVariantDenominatorErrors(continuity, asset map[string]any) []string {
	variants := mapValue(asset["state_variants"])
	if variants == nil {
		return nil
	}
	id := anyString(asset["component_id"])
	sources := map[string]bool{}
	for _, value := range listValue(variants["variants"]) {
		sources[anyString(mapValue(value)["source_ref"])] = true
	}
	inventory := map[string]bool{}
	for _, ref := range migrationStringValues(asset["source_refs"]) {
		inventory[ref] = true
	}
	diagnostics := []string{}
	if len(sources) == 0 || !reflect.DeepEqual(sources, inventory) {
		diagnostics = append(diagnostics, "asset-state-source-coverage-mismatch:"+id)
	}
	for _, value := range listValue(continuity["surface_bindings"]) {
		for _, value := range listValue(mapValue(value)["component_states"]) {
			component := mapValue(value)
			if anyString(component["component_id"]) == id && !migrationExactStrings(variants["required_states"], component["required_states"]) {
				diagnostics = append(diagnostics, "asset-state-component-coverage-mismatch:"+id)
			}
		}
	}
	return diagnostics
}

type migrationScalarValue struct {
	kind  string
	value any
}

func migrationScalar(value any) (migrationScalarValue, bool) {
	switch item := value.(type) {
	case nil:
		return migrationScalarValue{"null", nil}, true
	case bool:
		return migrationScalarValue{"boolean", item}, true
	case string:
		return migrationScalarValue{"string", item}, true
	case int:
		return migrationScalarValue{"number", float64(item)}, true
	case float64:
		return migrationScalarValue{"number", item}, !math.IsNaN(item) && !math.IsInf(item, 0)
	default:
		return migrationScalarValue{}, false
	}
}

func migrationEffectSatisfied(before, after, native map[string]any) bool {
	fields, ok := migrationRawStrings(native["effect_fields"])
	mode := anyString(native["effect_requirement"])
	if !ok || len(fields) == 0 || !migrationExactStrings(native["effect_fields"], native["effect_fields"]) || !quickContains([]string{"state-change", "observation"}, mode) {
		return false
	}
	changed := false
	for _, field := range fields {
		left, leftPresent := before[field]
		right, rightPresent := after[field]
		if !leftPresent || !rightPresent {
			return false
		}
		l, leftOK := migrationScalar(left)
		r, rightOK := migrationScalar(right)
		if !leftOK || !rightOK {
			return false
		}
		changed = changed || l != r
	}
	return changed || mode == "observation"
}

func migrationRowIDs(rows []map[string]any, field string) []any {
	ids := make([]any, 0, len(rows))
	for _, row := range rows {
		ids = append(ids, row[field])
	}
	return ids
}

func migrationSize(value any) ([2]float64, bool) {
	var result [2]float64
	values := listValue(value)
	if len(values) != 2 {
		return result, false
	}
	for i, raw := range values {
		var number float64
		switch n := raw.(type) {
		case float64:
			number = n
		case int:
			number = float64(n)
		default:
			return result, false
		}
		if math.IsNaN(number) || math.IsInf(number, 0) || number < 1 || number > 2147483647 || number != math.Trunc(number) {
			return result, false
		}
		result[i] = number
	}
	return result, true
}

func validateMigrationContract(continuity map[string]any, path string) error {
	coverage := mapValue(continuity["coverage"])
	components := migrationStringValues(coverage["component_ids"])
	for _, value := range listValue(continuity["surface_bindings"]) {
		surface := mapValue(value)
		value, present := surface["component_states"]
		if !present {
			continue
		}
		rows, ok := quickContinuityRows(value)
		if !ok || len(rows) == 0 {
			return fmt.Errorf("%s component_states must be a nonempty array", path)
		}
		seen := map[string]bool{}
		for _, component := range rows {
			id := anyString(component["component_id"])
			parts, partsOK := quickContinuityStringList(component["parts"])
			required, requiredOK := quickContinuityStringList(component["required_states"])
			states, statesOK := quickContinuityRows(component["states"])
			if !migrationFields(component, "component_id", "parts", "required_states", "states") || !quickContains(components, id) || seen[id] || !partsOK || len(parts) == 0 || !requiredOK || len(required) == 0 || !statesOK || !migrationExactStrings(migrationRowIDs(states, "state"), component["required_states"]) {
				return fmt.Errorf("%s component_states must bind covered components and exactly cover required_states", path)
			}
			seen[id] = true
			for _, state := range states {
				visuals, visualsOK := quickContinuityRows(state["visuals"])
				if !migrationFields(state, "state", "behavior", "visuals") || !migrationText(state["state"]) || !migrationText(state["behavior"]) || !visualsOK || !migrationExactStrings(migrationRowIDs(visuals, "part"), component["parts"]) {
					return fmt.Errorf("%s component state needs behavior and every visual part", path)
				}
				for _, visual := range visuals {
					if !migrationFields(visual, "part", "expectation") || !migrationText(visual["part"]) || !migrationText(visual["expectation"]) {
						return fmt.Errorf("%s component visual expectation is incomplete", path)
					}
				}
			}
		}
	}
	for _, value := range listValue(continuity["asset_bindings"]) {
		asset := mapValue(value)
		value, present := asset["state_variants"]
		if !present {
			continue
		}
		variants := mapValue(value)
		if diagnostics := migrationVariantDenominatorErrors(continuity, asset); len(diagnostics) > 0 {
			return fmt.Errorf("%s %s", path, strings.Join(diagnostics, "; "))
		}
		required, requiredOK := quickContinuityStringList(variants["required_states"])
		rows, rowsOK := quickContinuityRows(variants["variants"])
		if !migrationFields(variants, "required_states", "variants") || !requiredOK || len(required) == 0 || !rowsOK || !migrationExactStrings(migrationRowIDs(rows, "state"), variants["required_states"]) {
			return fmt.Errorf("%s asset variants must exactly cover required_states", path)
		}
		for _, row := range rows {
			if !migrationFields(row, "state", "source_ref", "target_ref", "source_size", "target_size") || !migrationText(row["state"]) || !migrationText(row["source_ref"]) || !migrationText(row["target_ref"]) {
				return fmt.Errorf("%s asset state variant is incomplete", path)
			}
			if !quickContains(migrationStringValues(asset["source_refs"]), anyString(row["source_ref"])) {
				return fmt.Errorf("%s asset variant source_ref is outside the source inventory", path)
			}
			for _, field := range []string{"source_ref", "target_ref"} {
				ref := anyString(row[field])
				if quickLooksLikeTemporaryPlaceholder(ref) || quickLooksLikeCharacterReference(ref) {
					return fmt.Errorf("%s asset state variants forbid character and placeholder substitution", path)
				}
			}
			source, sourceOK := migrationSize(row["source_size"])
			target, targetOK := migrationSize(row["target_size"])
			if !sourceOK || !targetOK || (asset["target_strategy"] == "preserve" && source != target) {
				return fmt.Errorf("%s preserved asset variant dimensions must match the source", path)
			}
		}
	}
	for _, value := range listValue(continuity["action_bindings"]) {
		action := mapValue(value)
		value, present := action["native_operation"]
		if !present {
			continue
		}
		native := mapValue(value)
		required, requiredOK := native["permission_required"].(bool)
		refs, refsOK := quickContinuityStringList(native["permission_refs"])
		fields, fieldsOK := migrationRawStrings(native["effect_fields"])
		if !migrationFields(native, "api_ref", "permission_required", "permission_refs", "permission_reason", "expected_effect", "effect_requirement", "effect_fields") || !migrationText(native["api_ref"]) || !migrationText(native["permission_reason"]) || !migrationText(native["expected_effect"]) || !requiredOK || !refsOK || required != (len(refs) > 0) || !migrationExactStrings(native["permission_refs"], native["permission_refs"]) || !fieldsOK || len(fields) == 0 || !migrationExactStrings(native["effect_fields"], native["effect_fields"]) || !quickContains([]string{"state-change", "observation"}, anyString(native["effect_requirement"])) {
			return fmt.Errorf("%s native_operation requires its API, permission declaration, and observable effect", path)
		}
		if native["effect_requirement"] == "observation" && len(listValue(action["side_effects"])) > 0 {
			return fmt.Errorf("%s observation mode cannot replace a native action with promised side effects", path)
		}
	}
	return nil
}

func validateMigrationComponentBindings(continuity map[string]any, componentValue any) error {
	components := map[string]map[string]any{}
	for _, value := range listValue(componentValue) {
		row := mapValue(value)
		components[anyString(row["id"])] = row
	}
	for _, value := range listValue(continuity["surface_bindings"]) {
		for _, detail := range listValue(mapValue(value)["component_states"]) {
			state := mapValue(detail)
			component := components[anyString(state["component_id"])]
			if !migrationExactStrings(state["parts"], component["anatomy"]) || !migrationExactStrings(state["required_states"], component["required_states"]) {
				return fmt.Errorf("source component states must exactly match component anatomy and required_states")
			}
		}
	}
	for _, value := range listValue(continuity["asset_bindings"]) {
		asset := mapValue(value)
		if variants := mapValue(asset["state_variants"]); variants != nil && !migrationExactStrings(variants["required_states"], components[anyString(asset["component_id"])]["required_states"]) {
			return fmt.Errorf("source asset states must exactly match component required_states")
		}
	}
	return nil
}

func migrationResultByID(value any, field string) map[string]map[string]any {
	result := map[string]map[string]any{}
	for _, raw := range listValue(value) {
		row := mapValue(raw)
		result[anyString(row[field])] = row
	}
	return result
}

func migrationAdapterTargets(capabilities map[string]bool, continuity map[string]any) map[string]any {
	checks := []any{}
	if capabilities["surface-enumeration"] {
		checks = append(checks, "inventory")
	}
	if capabilities["action-execution"] || capabilities["side-effect-observation"] {
		checks = append(checks, "behavior")
	}
	if capabilities["asset-inspection"] || capabilities["visual-capture"] {
		checks = append(checks, "visual")
	}
	result := map[string]any{}
	states := []any{}
	for _, value := range listValue(continuity["surface_bindings"]) {
		surface := mapValue(value)
		for _, detail := range listValue(surface["component_states"]) {
			component := mapValue(detail)
			for _, state := range migrationStringValues(component["required_states"]) {
				states = append(states, map[string]any{"surface_binding_id": surface["id"], "component_id": component["component_id"], "state": state, "parts": cloneJSONValue(component["parts"]), "checks": checks})
			}
		}
	}
	if len(states) > 0 && len(checks) > 0 {
		result["component_states"] = states
	}
	if capabilities["asset-inspection"] || capabilities["visual-capture"] {
		variants := []any{}
		for _, value := range listValue(continuity["asset_bindings"]) {
			asset := mapValue(value)
			for _, state := range migrationStringValues(mapValue(asset["state_variants"])["required_states"]) {
				variants = append(variants, map[string]any{"asset_binding_id": asset["id"], "state": state})
			}
		}
		if len(variants) > 0 {
			result["asset_variants"] = variants
		}
	}
	return result
}

func migrationObservationErrors(continuity, observation map[string]any, evidence map[string]sourceContinuityLabEvidenceBinding) []string {
	diagnostics := []string{}
	bound := func(value any, side, kind string) bool {
		row, ok := evidence[anyString(value)]
		return ok && row.Side == side && row.Kind == kind
	}
	surfaces := migrationResultByID(observation["surface_results"], "surface_id")
	for _, value := range listValue(continuity["surface_bindings"]) {
		surface := mapValue(value)
		if _, exists := surface["component_states"]; !exists {
			continue
		}
		id := anyString(surface["surface_id"])
		rows, _ := quickContinuityRows(surfaces[id]["component_states"])
		expected := []any{}
		parts := map[string]any{}
		for _, value := range listValue(surface["component_states"]) {
			component := mapValue(value)
			componentID := anyString(component["component_id"])
			parts[componentID] = component["parts"]
			for _, state := range migrationStringValues(component["required_states"]) {
				expected = append(expected, componentID+":"+state)
			}
		}
		actual := []any{}
		for _, row := range rows {
			key := anyString(row["component_id"]) + ":" + anyString(row["state"])
			actual = append(actual, key)
			if !migrationFields(row, "component_id", "state", "behavior_matches", "behavior_observation", "behavior_evidence_ref", "visuals") || !migrationText(row["component_id"]) || !migrationText(row["state"]) {
				diagnostics = append(diagnostics, "component-state-result-invalid:"+key)
			}
			if row["behavior_matches"] != true || !migrationText(row["behavior_observation"]) {
				diagnostics = append(diagnostics, "component-state-behavior-mismatch:"+key)
			}
			if !bound(row["behavior_evidence_ref"], "target", "runtime_diagnostics") {
				diagnostics = append(diagnostics, "component-state-evidence-kind-mismatch:"+key)
			}
			visuals, _ := quickContinuityRows(row["visuals"])
			if !migrationExactStrings(migrationRowIDs(visuals, "part"), parts[anyString(row["component_id"])]) {
				diagnostics = append(diagnostics, "component-state-visual-coverage-mismatch:"+key)
			}
			for _, visual := range visuals {
				if !migrationFields(visual, "part", "matches", "observation", "source_evidence_ref", "target_evidence_ref") || visual["matches"] != true || !migrationText(visual["observation"]) {
					diagnostics = append(diagnostics, "component-state-visual-mismatch:"+key+":"+anyString(visual["part"]))
				}
				if !bound(visual["source_evidence_ref"], "source", "visual_capture") || !bound(visual["target_evidence_ref"], "target", "visual_capture") {
					diagnostics = append(diagnostics, "component-state-evidence-kind-mismatch:"+key)
				}
			}
		}
		if !migrationExactStrings(actual, expected) {
			diagnostics = append(diagnostics, "component-state-coverage-mismatch:"+id)
		}
	}
	assets := migrationResultByID(observation["asset_results"], "component_id")
	for _, value := range listValue(continuity["asset_bindings"]) {
		asset := mapValue(value)
		variants := mapValue(asset["state_variants"])
		if variants == nil {
			continue
		}
		diagnostics = append(diagnostics, migrationVariantDenominatorErrors(continuity, asset)...)
		id := anyString(asset["component_id"])
		rows, _ := quickContinuityRows(assets[id]["state_variants"])
		if !migrationExactStrings(migrationRowIDs(rows, "state"), variants["required_states"]) {
			diagnostics = append(diagnostics, "asset-state-coverage-mismatch:"+id)
		}
		expected := migrationResultByID(variants["variants"], "state")
		for _, row := range rows {
			key := id + ":" + anyString(row["state"])
			target := expected[anyString(row["state"])]
			if !migrationFields(row, "state", "source_ref", "target_ref", "source_size", "target_size", "source_evidence_ref", "target_evidence_ref", "render_match", "character_substitution") {
				diagnostics = append(diagnostics, "asset-state-result-invalid:"+key)
			}
			if row["source_ref"] != target["source_ref"] || row["target_ref"] != target["target_ref"] {
				diagnostics = append(diagnostics, "asset-state-reference-mismatch:"+key)
			}
			for _, field := range []string{"source_size", "target_size"} {
				actual, actualOK := migrationSize(row[field])
				want, wantOK := migrationSize(target[field])
				if !actualOK || !wantOK || actual != want {
					diagnostics = append(diagnostics, "asset-state-size-mismatch:"+key)
				}
			}
			if row["character_substitution"] != false {
				diagnostics = append(diagnostics, "asset-state-character-substitution:"+key)
			}
			if row["render_match"] != true {
				diagnostics = append(diagnostics, "asset-state-render-mismatch:"+key)
			}
			if !bound(row["source_evidence_ref"], "source", "visual_capture") || !bound(row["target_evidence_ref"], "target", "visual_capture") {
				diagnostics = append(diagnostics, "asset-state-evidence-kind-mismatch:"+key)
			}
		}
	}
	actions := migrationResultByID(observation["action_results"], "interaction_id")
	for _, value := range listValue(continuity["action_bindings"]) {
		action := mapValue(value)
		native := mapValue(action["native_operation"])
		if native == nil {
			continue
		}
		id := anyString(action["interaction_id"])
		if native["effect_requirement"] == "observation" && len(listValue(action["side_effects"])) > 0 {
			diagnostics = append(diagnostics, "native-operation-mode-mismatch:"+id)
		}
		result := mapValue(actions[id]["native_operation"])
		if result == nil {
			diagnostics = append(diagnostics, "native-operation-result-missing:"+id)
			continue
		}
		if !migrationFields(result, "api_ref", "verified_permission_refs", "permission_evidence_ref", "effect_evidence_ref", "before", "after", "effect_matches") || result["api_ref"] != native["api_ref"] {
			diagnostics = append(diagnostics, "native-operation-api-mismatch:"+id)
		}
		if !migrationExactStrings(result["verified_permission_refs"], native["permission_refs"]) {
			diagnostics = append(diagnostics, "native-operation-permission-mismatch:"+id)
		}
		if !bound(result["permission_evidence_ref"], "target", "runtime_diagnostics") || !bound(result["effect_evidence_ref"], "target", "runtime_diagnostics") {
			diagnostics = append(diagnostics, "native-operation-evidence-kind-mismatch:"+id)
		}
		before, after := mapValue(result["before"]), mapValue(result["after"])
		if !migrationEffectSatisfied(before, after, native) || result["effect_matches"] != true {
			diagnostics = append(diagnostics, "native-operation-effect-mismatch:"+id)
		}
	}
	return uniqueSourceContinuityLabDiagnostics(diagnostics)
}
