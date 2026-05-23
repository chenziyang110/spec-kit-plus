package validation

import (
	"path/filepath"

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
	return scanartifacts.ValidateJSONFile(path, filepath.Base(path))
}

func validateCoverageLedger(paths rt.Paths, owner string) []string {
	return scanartifacts.ValidateCoverageLedger(paths, owner)
}
