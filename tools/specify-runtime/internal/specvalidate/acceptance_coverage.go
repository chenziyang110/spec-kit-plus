package specvalidate

import (
	"fmt"
	"sort"
	"strings"
)

// ValidateAcceptanceCoverage proves exact requirement/acceptance set closure.
// An acceptance criterion belongs to one requirement; a requirement may have
// multiple criteria. This is shared by the light and detailed runtime gates.
func ValidateAcceptanceCoverage(spec map[string]any) error {
	requirements, err := specRequirementRefs(spec)
	if err != nil {
		return err
	}
	criteria, ok := spec["acceptance_criteria"].([]any)
	if !ok || len(criteria) == 0 {
		return fmt.Errorf("spec-contract.json acceptance_criteria must be a non-empty array")
	}
	acceptance := map[string]bool{}
	for index, criterion := range criteria {
		if text, ok := criterion.(string); !ok || strings.TrimSpace(text) == "" {
			return fmt.Errorf("acceptance_criteria[%d] must be a non-empty string", index)
		}
		acceptance[fmt.Sprintf("spec-contract.json#/acceptance_criteria/%d", index)] = true
	}
	rows, ok := spec["acceptance_coverage"].([]any)
	if !ok || len(rows) == 0 {
		return fmt.Errorf("spec-contract.json acceptance_coverage must be a non-empty array")
	}
	coveredRequirements, coveredAcceptance := map[string]bool{}, map[string]bool{}
	for index, value := range rows {
		row, ok := value.(map[string]any)
		if !ok {
			return fmt.Errorf("acceptance_coverage[%d] must be an object", index)
		}
		requirement, _ := row["requirement_ref"].(string)
		criterion, _ := row["acceptance_ref"].(string)
		if !requirements[requirement] || !acceptance[criterion] {
			return fmt.Errorf("acceptance_coverage[%d] must reference an existing canonical requirement and acceptance criterion", index)
		}
		if coveredAcceptance[criterion] {
			return fmt.Errorf("acceptance_coverage must map every acceptance criterion exactly once to one requirement: %s", criterion)
		}
		coveredRequirements[requirement], coveredAcceptance[criterion] = true, true
	}
	if missing := missingCoverageRefs(requirements, coveredRequirements); len(missing) > 0 {
		return fmt.Errorf("spec requirements are missing acceptance_coverage: %s", strings.Join(missing, ", "))
	}
	if missing := missingCoverageRefs(acceptance, coveredAcceptance); len(missing) > 0 {
		return fmt.Errorf("spec acceptance criteria are missing acceptance_coverage: %s", strings.Join(missing, ", "))
	}
	return nil
}

func specRequirementRefs(spec map[string]any) (map[string]bool, error) {
	scope, ok := spec["scope"].(map[string]any)
	if !ok {
		return nil, fmt.Errorf("spec-contract.json scope must be an object for acceptance_coverage")
	}
	inScope, ok := scope["in"].([]any)
	if !ok {
		return nil, fmt.Errorf("spec-contract.json scope.in must be an array for acceptance_coverage")
	}
	refs := map[string]bool{}
	for index, value := range inScope {
		if text, ok := value.(string); !ok || strings.TrimSpace(text) == "" {
			return nil, fmt.Errorf("scope.in[%d] must identify a non-empty requirement", index)
		}
		refs[fmt.Sprintf("spec-contract.json#/scope/in/%d", index)] = true
	}
	addOperation := func(token string, value any) error {
		valid := false
		switch operation := value.(type) {
		case string:
			valid = strings.TrimSpace(operation) != ""
		case map[string]any:
			valid = len(operation) > 0
		}
		if !valid {
			return fmt.Errorf("capability_operations/%s must describe an existing non-empty operation", token)
		}
		refs["spec-contract.json#/capability_operations/"+token] = true
		return nil
	}
	switch operations := spec["capability_operations"].(type) {
	case []any:
		for index, operation := range operations {
			if err := addOperation(fmt.Sprint(index), operation); err != nil {
				return nil, err
			}
		}
	case map[string]any:
		keys := make([]string, 0, len(operations))
		for key := range operations {
			keys = append(keys, key)
		}
		sort.Strings(keys)
		for _, key := range keys {
			token := strings.ReplaceAll(strings.ReplaceAll(key, "~", "~0"), "/", "~1")
			if err := addOperation(token, operations[key]); err != nil {
				return nil, err
			}
		}
	default:
		return nil, fmt.Errorf("spec-contract.json capability_operations must be an array or object for acceptance_coverage")
	}
	return refs, nil
}

func capabilityOperationCount(value any) (int, bool) {
	switch operations := value.(type) {
	case []any:
		return len(operations), true
	case map[string]any:
		return len(operations), true
	default:
		return 0, false
	}
}

func missingCoverageRefs(expected, actual map[string]bool) []string {
	missing := []string{}
	for ref := range expected {
		if !actual[ref] {
			missing = append(missing, ref)
		}
	}
	sort.Strings(missing)
	return missing
}

func checkAcceptanceCoverage(a artifactSet) checkResult {
	if strings.TrimSpace(a.specContract) == "" {
		return checkResult{status: statusPass}
	}
	spec, result := parseSpecContract(a)
	if result.status != statusPass {
		return result
	}
	if err := ValidateAcceptanceCoverage(spec); err != nil {
		return checkResult{status: statusFail, message: err.Error()}
	}
	return checkResult{status: statusPass}
}
