package main

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strings"

	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/specvalidate"
)

type SpecValidationRequest struct {
	FeatureDir string
	Tier       string
	ShowPasses bool
}

func ValidateSpec(request SpecValidationRequest) Envelope {
	tier := request.Tier
	if tier == "" {
		tier = "light"
	}
	env := NewEnvelope("ok", "spec artifacts validated")
	env.Data["tier"] = tier
	env.Data["feature_dir"] = request.FeatureDir
	if !specvalidate.ValidTier(tier) {
		env.Status = "usage-error"
		env.Summary = "spec validation tier is invalid"
		env.Blockers = append(env.Blockers, fmt.Sprintf("invalid tier %q; expected one of: light, standard, deep", tier))
		return env
	}

	if tier != "light" {
		report, err := specvalidate.Validate(request.FeatureDir, tier, request.ShowPasses)
		if err != nil {
			env.Status = "error"
			env.Summary = "spec validation failed to run"
			env.Blockers = append(env.Blockers, err.Error())
			return env
		}
		env.Data["summary"] = report.Summary
		env.Data["failures"] = report.Failures
		env.Data["warnings"] = report.Warnings
		if request.ShowPasses {
			env.Data["passes"] = report.Passes
		}
		if report.Summary.Failed > 0 {
			env.Status = "blocked"
			env.Summary = "spec validation found blocking contract failures"
			env.Blockers = append(env.Blockers, fmt.Sprintf("%d contract checks failed; inspect data.failures", report.Summary.Failed))
			env.NextArgv = []string{"specify-runtime", "validate", "spec", "--dir", request.FeatureDir, "--tier", tier}
		} else if report.Summary.Warnings > 0 {
			env.Status = "warn"
			env.Summary = "spec validation completed with warnings"
		}
		return env
	}

	required := []string{"spec.md", "spec-contract.json"}
	for _, relative := range required {
		path := filepath.Join(request.FeatureDir, relative)
		if _, err := os.Stat(path); err != nil {
			env.Status = "blocked"
			env.Summary = "spec validation is blocked"
			env.Blockers = append(env.Blockers, relative+" is missing")
		}
	}
	specPath := filepath.Join(request.FeatureDir, "spec.md")
	if raw, err := os.ReadFile(specPath); err == nil && !containsSpecRequirementsSection(string(raw)) {
		env.Status = "blocked"
		env.Summary = "spec validation is blocked"
		env.Blockers = append(env.Blockers, "spec.md must include a Requirements section")
	}
	contractPath := filepath.Join(request.FeatureDir, "spec-contract.json")
	if raw, err := os.ReadFile(contractPath); err == nil && !json.Valid(raw) {
		env.Status = "blocked"
		env.Summary = "spec validation is blocked"
		env.Blockers = append(env.Blockers, "spec-contract.json is not valid JSON")
	}
	if env.Status == "blocked" {
		env.NextArgv = []string{"specify-runtime", "validate", "spec", "--dir", request.FeatureDir, "--tier", tier}
	}
	return env
}

func containsSpecRequirementsSection(content string) bool {
	return strings.Contains(content, "## Requirements") || strings.Contains(content, "# Requirements")
}
