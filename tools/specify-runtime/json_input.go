package main

import (
	"encoding/json"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strings"
)

const maxAgentJSONInputBytes = 16 * 1024 * 1024

func readAgentJSONInput(args []string, projectRoot, label string) ([]byte, error) {
	if hasFlag(args, "--input") {
		return nil, fmt.Errorf("%s does not accept agent-authored input files via --input; pass bounded semantic JSON with --input-json (inline, @path, or - for stdin)", label)
	}
	if !hasFlag(args, "--input-json") {
		return nil, fmt.Errorf("%s requires --input-json", label)
	}
	raw, err := resolveAgentJSONInputBytes(optionValue(args, "--input-json", ""), projectRoot, label)
	if err != nil {
		return nil, err
	}
	if len(raw) == 0 {
		return nil, fmt.Errorf("%s --input-json must not be empty", label)
	}
	if len(raw) > maxAgentJSONInputBytes {
		return nil, fmt.Errorf("%s --input-json exceeds %d bytes", label, maxAgentJSONInputBytes)
	}
	return raw, nil
}

// resolveAgentJSONInputBytes loads --input-json content from:
//   - inline JSON text
//   - @path (project-relative or absolute file; shell-safe on Windows)
//   - - (stdin)
//
// Content is consumed at invoke time; agents must not treat the source path as
// durable workflow state. Bare --input remains rejected.
func resolveAgentJSONInputBytes(raw, projectRoot, label string) ([]byte, error) {
	trimmed := strings.TrimSpace(raw)
	if trimmed == "" {
		return nil, nil
	}
	if trimmed == "-" {
		limited := io.LimitReader(os.Stdin, int64(maxAgentJSONInputBytes)+1)
		data, err := io.ReadAll(limited)
		if err != nil {
			return nil, fmt.Errorf("%s --input-json - failed to read stdin: %w", label, err)
		}
		if len(data) > maxAgentJSONInputBytes {
			return nil, fmt.Errorf("%s --input-json exceeds %d bytes", label, maxAgentJSONInputBytes)
		}
		return data, nil
	}
	if strings.HasPrefix(trimmed, "@") {
		path := strings.TrimSpace(strings.TrimPrefix(trimmed, "@"))
		if path == "" {
			return nil, fmt.Errorf("%s --input-json @path requires a non-empty path", label)
		}
		if !filepath.IsAbs(path) {
			root := strings.TrimSpace(projectRoot)
			if root == "" {
				root = "."
			}
			path = filepath.Join(root, path)
		}
		data, err := os.ReadFile(path)
		if err != nil {
			return nil, fmt.Errorf("%s --input-json @path could not read %s: %w", label, path, err)
		}
		if len(data) > maxAgentJSONInputBytes {
			return nil, fmt.Errorf("%s --input-json exceeds %d bytes", label, maxAgentJSONInputBytes)
		}
		return data, nil
	}
	return []byte(raw), nil
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
