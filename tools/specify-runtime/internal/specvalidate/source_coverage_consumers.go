package specvalidate

import (
	"fmt"
	"reflect"
	"strings"
)

// ValidateSourceCoverageInheritance prevents a downstream phase from dropping
// or reinterpreting the reviewed source-to-spec mappings.
func ValidateSourceCoverageInheritance(upstream, downstream map[string]any) error {
	expected, err := coverageRows(upstream)
	if err != nil {
		return err
	}
	actual, err := coverageRows(downstream)
	if err != nil {
		return err
	}
	if !reflect.DeepEqual(expected, actual) {
		return fmt.Errorf("source_requirement_coverage must exactly preserve the upstream rows and order")
	}
	return nil
}

// HasSourceRequirementCoverage keeps the legacy no-source packet path separate
// from the requirement-bound path, where a missing task assignment is an error.
func HasSourceRequirementCoverage(payload map[string]any) bool {
	rows, err := coverageRows(payload)
	return err != nil || len(rows) != 0
}

// ValidateTaskSourceRequirementCoverage requires actual task assignments, not
// just an intact top-level denominator or generic review-scenario arrays.
func ValidateTaskSourceRequirementCoverage(index map[string]any) error {
	rows, err := coverageRows(index)
	if err != nil {
		return err
	}
	if len(rows) == 0 {
		return nil
	}
	canonicalAcceptance, err := coverageStringSet(index["acceptance_refs"], "task-index acceptance_refs")
	if err != nil {
		return err
	}
	expected := map[string]bool{}
	for _, raw := range rows {
		row, ok := raw.(map[string]any)
		if !ok {
			return fmt.Errorf("source_requirement_coverage entries must be objects")
		}
		if row["disposition"] != "in_scope" {
			continue
		}
		refs, err := coverageStringSet(row["acceptance_refs"], "source requirement acceptance_refs")
		if err != nil || len(refs) == 0 {
			return fmt.Errorf("in_scope source requirement must retain its acceptance_refs")
		}
		for ref := range refs {
			if !canonicalAcceptance[ref] {
				return fmt.Errorf("source requirement acceptance_ref %s is absent from task-index acceptance_refs", ref)
			}
			expected[ref] = true
		}
	}
	tasks, ok := index["tasks"].([]any)
	if !ok {
		return fmt.Errorf("task-index tasks must be an array")
	}
	assigned := map[string]bool{}
	for _, raw := range tasks {
		task, ok := raw.(map[string]any)
		if !ok {
			return fmt.Errorf("task-index tasks must contain objects")
		}
		refs := map[string]bool{}
		if value, exists := task["acceptance_refs"]; exists {
			refs, err = coverageStringSet(value, "task acceptance_refs")
			if err != nil {
				return err
			}
		}
		if len(refs) == 0 {
			continue
		}
		criteria, ok := task["acceptance"].([]any)
		if !ok || len(criteria) == 0 {
			return fmt.Errorf("task %s assigns acceptance refs without concrete task acceptance", coverageText(task["id"]))
		}
		for _, value := range criteria {
			if text, ok := value.(string); !ok || strings.TrimSpace(text) == "" {
				return fmt.Errorf("task %s acceptance must contain non-empty criteria", coverageText(task["id"]))
			}
		}
		for ref := range refs {
			if !canonicalAcceptance[ref] {
				return fmt.Errorf("task %s assigns unknown acceptance_ref %s", coverageText(task["id"]), ref)
			}
			if task["status"] != "deferred" {
				assigned[ref] = true
			}
		}
	}
	if missing := missingCoverageRefs(expected, assigned); len(missing) != 0 {
		return fmt.Errorf("source requirements have no concrete task acceptance assignment: %s", strings.Join(missing, ", "))
	}
	return nil
}

// SourceRequirementRefsForTask derives the exact requirement subset from that
// task's explicit acceptance allocation. Caller validates the complete index.
func SourceRequirementRefsForTask(index, task map[string]any) ([]string, error) {
	rows, err := coverageRows(index)
	if err != nil {
		return nil, err
	}
	refs := map[string]bool{}
	if value, exists := task["acceptance_refs"]; exists {
		refs, err = coverageStringSet(value, "task acceptance_refs")
		if err != nil {
			return nil, err
		}
	}
	result := []string{}
	for _, raw := range rows {
		row, ok := raw.(map[string]any)
		if !ok {
			return nil, fmt.Errorf("source_requirement_coverage entries must be objects")
		}
		if row["disposition"] != "in_scope" {
			continue
		}
		acceptance, err := coverageStringSet(row["acceptance_refs"], "source requirement acceptance_refs")
		if err != nil {
			return nil, err
		}
		for ref := range acceptance {
			if refs[ref] {
				result = append(result, coverageText(row["requirement_id"]))
				break
			}
		}
	}
	return result, nil
}
