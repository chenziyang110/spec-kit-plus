package main

import (
	"encoding/json"
	"fmt"
	"reflect"
	"strings"
)

// Quick checks must be lossless before the shared, compatibility-oriented
// normalizer runs. Other result channels retain their existing behavior.
func normalizeSubmittedTaskResult(command string, raw []byte) (map[string]any, error) {
	if strings.EqualFold(strings.TrimSpace(command), "quick") {
		if err := validateQuickResultValidationInput(raw); err != nil {
			return nil, err
		}
	}
	return normalizeWorkerTaskResult(raw)
}

// Validate every supplied check, including aliases the normalizer would ignore.
// Omitted/null/empty lists remain compatible with legacy worker results; the
// leader-direct acceptance gate separately requires non-empty passing checks.
// This validates reported data, not actual execution, coverage, or authority.
func validateQuickResultValidationInput(raw []byte) error {
	var payload map[string]any
	if err := json.Unmarshal(raw, &payload); err != nil || payload == nil {
		return fmt.Errorf("quick result validation input must be a JSON object")
	}
	var previous []map[string]string
	seen := false
	for _, field := range []string{"validation_results", "validationResults"} {
		value, present := payload[field]
		if !present {
			continue
		}
		var rows []any
		if value != nil {
			var ok bool
			rows, ok = value.([]any)
			if !ok {
				return fmt.Errorf("quick result %s must be an array or null", field)
			}
		}
		for index, value := range rows {
			row, ok := value.(map[string]any)
			if !ok || row == nil {
				return fmt.Errorf("quick result %s[%d] must be an object", field, index)
			}
			if err := validateQuickCheckAliases(row, "command", "cmd", false); err != nil {
				return fmt.Errorf("quick result %s[%d]: %w", field, index, err)
			}
			if err := validateQuickCheckAliases(row, "status", "result", true); err != nil {
				return fmt.Errorf("quick result %s[%d]: %w", field, index, err)
			}
		}
		checks := normalizeValidationResults(map[string]any{"validation_results": rows})
		if seen && !reflect.DeepEqual(previous, checks) {
			return fmt.Errorf("quick result validation_results and validationResults conflict; supply one complete check list")
		}
		previous, seen = checks, true
	}
	return nil
}

func validateQuickCheckAliases(row map[string]any, primary, alias string, statusField bool) error {
	seen := false
	previous := ""
	for _, field := range []string{primary, alias} {
		value, present := row[field]
		if !present {
			continue
		}
		text, ok := value.(string)
		if !ok || strings.TrimSpace(text) == "" {
			return fmt.Errorf("%s must be a non-empty string", field)
		}
		text = strings.TrimSpace(text)
		if statusField {
			// Match the shared normalizer: unknown statuses remain failed, never
			// passed. Existing pass/fail/skip aliases stay compatible.
			text = resultValidationStatusAliases[strings.ToLower(text)]
			if text == "" {
				text = "failed"
			}
		}
		if seen && previous != text {
			return fmt.Errorf("%s and %s conflict", primary, alias)
		}
		previous, seen = text, true
	}
	if !seen {
		return fmt.Errorf("%s or %s is required", primary, alias)
	}
	return nil
}
