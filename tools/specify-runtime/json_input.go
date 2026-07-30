package main

import (
	"encoding/json"
	"fmt"
)

const maxAgentJSONInputBytes = 16 * 1024 * 1024

func readAgentJSONInput(args []string, projectRoot, label string) ([]byte, error) {
	_ = projectRoot
	if hasFlag(args, "--input") {
		return nil, fmt.Errorf("%s does not accept agent-authored input files; pass bounded semantic JSON inline with --input-json", label)
	}
	if !hasFlag(args, "--input-json") {
		return nil, fmt.Errorf("%s requires --input-json", label)
	}
	raw := []byte(optionValue(args, "--input-json", ""))
	if len(raw) == 0 {
		return nil, fmt.Errorf("%s --input-json must not be empty", label)
	}
	if len(raw) > maxAgentJSONInputBytes {
		return nil, fmt.Errorf("%s --input-json exceeds %d bytes", label, maxAgentJSONInputBytes)
	}
	return raw, nil
}

func readAgentJSONObject(args []string, projectRoot, label string) (map[string]any, error) {
	raw, err := readAgentJSONInput(args, projectRoot, label)
	if err != nil {
		return nil, err
	}
	var value map[string]any
	if err := json.Unmarshal(raw, &value); err != nil {
		return nil, fmt.Errorf("%s input must be a JSON object: %w", label, err)
	}
	if value == nil {
		return nil, fmt.Errorf("%s input must be a JSON object", label)
	}
	return value, nil
}
