package validation

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strings"

	rt "github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/runtime"
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
	required := []string{
		".specify/project-cognition/evidence",
		".specify/project-cognition/status.json",
		".specify/project-cognition/provisional/nodes.json",
		".specify/project-cognition/provisional/edges.json",
		".specify/project-cognition/provisional/observations.json",
		".specify/project-cognition/coverage.json",
		".specify/project-cognition/workbench/map-scan.md",
		".specify/project-cognition/workbench/coverage-ledger.md",
		".specify/project-cognition/workbench/coverage-ledger.json",
		".specify/project-cognition/workbench/scan-packets",
		".specify/project-cognition/workbench/map-state.md",
		".specify/project-cognition/workbench/repository-universe.json",
	}
	payload := GatePayload{
		Status:       "ok",
		Gate:         "scan_acceptance",
		Readiness:    "scan_ready",
		Errors:       []string{},
		Warnings:     []string{},
		CheckedPaths: required,
		Details:      map[string]any{},
	}
	for _, rel := range required {
		full := filepath.Join(paths.Root, filepath.FromSlash(rel))
		info, err := os.Stat(full)
		if err != nil {
			payload.Errors = append(payload.Errors, "missing "+rel)
			continue
		}
		if !info.IsDir() && filepath.Ext(full) == ".json" {
			if err := validateJSONFile(full); err != nil {
				payload.Errors = append(payload.Errors, rel+": "+err.Error())
			}
		}
	}
	payload.Errors = append(payload.Errors, validateScanEvidence(paths)...)
	if _, readErrors := readJSONObject(filepath.Join(paths.RuntimeDir, "status.json"), "status.json"); readErrors != nil {
		payload.Errors = append(payload.Errors, readErrors...)
	}
	payload.Errors = append(payload.Errors, validateCoverageRows(paths)...)
	payload.Errors = append(payload.Errors, validateCoverageLedger(paths, "scan")...)
	if len(payload.Errors) > 0 {
		payload.Status = "blocked"
		payload.Readiness = "blocked"
	}
	payload.Details["required_artifacts"] = required
	return payload
}

func validateJSONFile(path string) error {
	data, err := os.ReadFile(path)
	if err != nil {
		return err
	}
	var raw any
	return json.Unmarshal(data, &raw)
}

func readJSONObject(path string, label string) (map[string]any, []string) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, []string{fmt.Sprintf("%s: %v", label, err)}
	}
	var raw any
	if err := json.Unmarshal(data, &raw); err != nil {
		return nil, []string{fmt.Sprintf("%s: %v", label, err)}
	}
	obj, ok := raw.(map[string]any)
	if !ok {
		return nil, []string{label + " must contain a top-level JSON object"}
	}
	return obj, nil
}

func validateScanEvidence(paths rt.Paths) []string {
	errors := []string{}
	coveragePath := filepath.Join(paths.RuntimeDir, "coverage.json")
	if payload, readErrors := readJSONObject(coveragePath, "coverage.json"); readErrors != nil {
		errors = append(errors, readErrors...)
	} else {
		rows, ok := payload["rows"].([]any)
		if !ok {
			errors = append(errors, "coverage.json must define a top-level rows array")
		} else {
			for _, row := range rows {
				obj, ok := row.(map[string]any)
				if !ok {
					continue
				}
				path := normalizedString(obj["path"])
				if strings.HasPrefix(path, ".specify/") {
					errors = append(errors, ".specify/** must not enter project cognition graph evidence")
					break
				}
			}
		}
	}
	evidenceDir := filepath.Join(paths.RuntimeDir, "evidence")
	_ = filepath.WalkDir(evidenceDir, func(path string, entry os.DirEntry, err error) error {
		if err != nil || entry.IsDir() || filepath.Ext(path) != ".json" {
			return nil
		}
		payload, readErrors := readJSONObject(path, filepath.ToSlash(path))
		if readErrors != nil {
			errors = append(errors, readErrors...)
			return nil
		}
		sourcePath := normalizedString(payload["source_path"])
		if strings.HasPrefix(sourcePath, ".specify/") {
			errors = append(errors, ".specify/** must not enter project cognition graph evidence")
			return filepath.SkipAll
		}
		return nil
	})
	return errors
}

func validateCoverageRows(paths rt.Paths) []string {
	coveragePath := filepath.Join(paths.RuntimeDir, "coverage.json")
	payload, readErrors := readJSONObject(coveragePath, "coverage.json")
	if readErrors != nil {
		return readErrors
	}
	rows, ok := payload["rows"].([]any)
	if !ok {
		return []string{"coverage.json must define a top-level rows array"}
	}
	errors := []string{}
	for i, row := range rows {
		obj, ok := row.(map[string]any)
		if !ok {
			errors = append(errors, fmt.Sprintf("coverage.json rows[%d] must be an object", i))
			continue
		}
		if normalizedString(obj["path"]) == "" {
			errors = append(errors, fmt.Sprintf("coverage.json rows[%d] is missing path", i))
		}
	}
	return errors
}

func validateCoverageLedger(paths rt.Paths, owner string) []string {
	ledgerPath := filepath.Join(paths.RuntimeDir, "workbench", "coverage-ledger.json")
	payload, readErrors := readJSONObject(ledgerPath, "coverage-ledger.json")
	if readErrors != nil {
		return readErrors
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
