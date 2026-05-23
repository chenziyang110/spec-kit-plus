package validation

import (
	"encoding/json"
	"os"
	"strings"

	rt "github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/runtime"
	"github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/scanartifacts"
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
	data, err := os.ReadFile(path)
	if err != nil {
		return err
	}
	var raw any
	return json.Unmarshal(data, &raw)
}

func validateCoverageLedger(paths rt.Paths, owner string) []string {
	result := scanartifacts.Validate(paths, scanartifacts.ValidateOptions{RequireStatusJSON: false})
	errors := []string{}
	for _, err := range result.Errors {
		if strings.Contains(err, "coverage-ledger.json") ||
			err == "subagent_blocked coverage gap must be resolved before project cognition acceptance" {
			errors = append(errors, err)
		}
	}
	return errors
}
