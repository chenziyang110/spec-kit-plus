package main

import (
	"regexp"
	"sort"
	"strconv"
	"strings"
)

// Collect independent structural mistakes before live applicability checks.
// Do not repeat execution, open Work, or invent a session in order to diagnose.
func doPrepareDefinitionIssues(root string, definition PlaybookDefinition) error {
	issues := []playbookJSONIssue{}
	add := func(pointer, keyword, message string) {
		if len(issues) < 12 {
			issues = append(issues, playbookJSONIssue{InstancePath: pointer, Keyword: keyword, Message: message})
		}
	}
	names := make([]string, 0, len(definition.Parameters))
	for name := range definition.Parameters {
		names = append(names, name)
	}
	sort.Strings(names)
	for _, name := range names {
		parameter := definition.Parameters[name]
		base := playbookJSONPointer("/definition/parameters", name)
		if parameter.Kind == "string" && parameter.Pattern == "" {
			add(base+"/pattern", "required", "string parameters require a nonempty validation pattern")
		}
		if parameter.Kind == "enum" && len(parameter.AllowedValues) == 0 {
			add(base+"/allowed_values", "minItems", "enum parameters require at least one allowed value")
		}
		if !parameter.Required && parameter.Default == nil {
			add(base+"/default", "required", "optional parameters require a default")
		}
		if parameter.Pattern != "" {
			if _, err := regexp.Compile("^(?:" + parameter.Pattern + ")$"); err != nil {
				add(base+"/pattern", "pattern", "parameter pattern must be a valid regular expression")
			}
		}
	}
	for i, step := range definition.Steps {
		if step.NativeAction == nil && !strings.Contains(step.Cwd, "{{param:") {
			if _, err := playbookSafePath(root, step.Cwd, true); err != nil {
				add(playbookJSONPointer("/definition/steps", strconv.Itoa(i))+"/cwd", "format", "cwd must be '.' or a canonical project-relative directory; absolute paths are not supported")
			}
		}
	}
	for i, check := range definition.Checks {
		if check.NativeAction == nil && !strings.Contains(check.Cwd, "{{param:") {
			if _, err := playbookSafePath(root, check.Cwd, true); err != nil {
				add(playbookJSONPointer("/definition/checks", strconv.Itoa(i))+"/cwd", "format", "cwd must be '.' or a canonical project-relative directory; absolute paths are not supported")
			}
		}
	}
	if len(issues) == 0 {
		return nil
	}
	return &playbookJSONInputError{Issues: issues}
}
