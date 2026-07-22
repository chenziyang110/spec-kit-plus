package validation

import (
	"bytes"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strings"

	rt "github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/runtime"
	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/scanartifacts"
)

type GatePayload struct {
	Status       string         `json:"status"`
	Gate         string         `json:"gate"`
	Readiness    string         `json:"readiness"`
	Errors       []string       `json:"errors"`
	Warnings     []string       `json:"warnings"`
	CheckedPaths []string       `json:"checked_paths"`
	Details      map[string]any `json:"details"`
}

func ValidateScan(paths rt.Paths) GatePayload {
	result := scanartifacts.Validate(paths, scanartifacts.ValidateOptions{RequireStatusJSON: true})
	return GatePayload{
		Status:       result.Status,
		Gate:         result.Gate,
		Readiness:    result.Readiness,
		Errors:       result.Errors,
		Warnings:     result.Warnings,
		CheckedPaths: result.CheckedPaths,
		Details:      result.Details,
	}
}

func validateJSONFile(path string) error {
	_, err := readJSONValue(path, filepath.Base(path))
	return err
}

func readJSONValue(path string, label string) (any, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	if bytes.HasPrefix(data, []byte{0xEF, 0xBB, 0xBF}) {
		return nil, fmt.Errorf("%s contains UTF-8 BOM", label)
	}
	var raw any
	if err := json.Unmarshal(data, &raw); err != nil {
		return nil, err
	}
	return raw, nil
}

func validateCoverageLedger(paths rt.Paths, owner string) []string {
	ledgerPath := filepath.Join(paths.RuntimeDir, "workbench", "coverage-ledger.json")
	raw, err := readJSONValue(ledgerPath, "coverage-ledger.json")
	if err != nil {
		return []string{"coverage-ledger.json: " + err.Error()}
	}
	payload, ok := raw.(map[string]any)
	if !ok {
		return []string{"coverage-ledger.json must contain a top-level JSON object"}
	}
	if _, ok := payload["rows"].([]any); !ok {
		return []string{"coverage-ledger.json must define a top-level rows array"}
	}
	errors := []string{}
	if gaps, ok := payload["open_gaps"].([]any); ok {
		for _, gap := range gaps {
			obj, ok := gap.(map[string]any)
			if !ok {
				continue
			}
			reason := normalizedString(obj["reason"])
			status := normalizedString(obj["status"])
			gapOwner := normalizedString(obj["owner"])
			if reason == "subagent_blocked" || status == "blocked" {
				if owner == "" || gapOwner == "" || gapOwner == owner {
					errors = append(errors, "subagent_blocked coverage gap must be resolved before project cognition acceptance")
				}
			}
		}
	}
	return errors
}

func normalizedString(value any) string {
	text, _ := value.(string)
	return filepath.ToSlash(strings.TrimSpace(text))
}
