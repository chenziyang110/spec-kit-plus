package specvalidate

import (
	"fmt"
	"os"
	"path/filepath"
)

// Summary contains the compact aggregate result for a spec validation run.
type Summary struct {
	Passed   int `json:"passed"`
	Failed   int `json:"failed"`
	Warnings int `json:"warnings"`
}

// Diagnostic identifies one failed or warning-level contract check.
type Diagnostic struct {
	Name    string `json:"name"`
	Message string `json:"message"`
}

// Report is the structured result consumed by the unified runtime envelope.
type Report struct {
	Tier     string       `json:"tier"`
	Summary  Summary      `json:"summary"`
	Failures []Diagnostic `json:"failures"`
	Warnings []Diagnostic `json:"warnings"`
	Passes   []string     `json:"passes,omitempty"`
}

// Validate runs the selected validation tier against a feature directory.
func Validate(dir, tier string, includePasses bool) (Report, error) {
	if !ValidTier(tier) {
		return Report{}, fmt.Errorf("invalid tier %q; expected one of: light, standard, deep", tier)
	}

	results := newRunner(tier).run(loadArtifacts(dir))
	report := Report{
		Tier:     tier,
		Failures: []Diagnostic{},
		Warnings: []Diagnostic{},
	}
	for _, result := range results {
		switch result.status {
		case statusPass:
			report.Summary.Passed++
			if includePasses {
				report.Passes = append(report.Passes, result.name)
			}
		case statusFail:
			report.Summary.Failed++
			report.Failures = append(report.Failures, Diagnostic{Name: result.name, Message: result.message})
		case statusWarn:
			report.Summary.Warnings++
			report.Warnings = append(report.Warnings, Diagnostic{Name: result.name, Message: result.message})
		}
	}
	return report, nil
}

// ValidTier reports whether tier names a supported validation depth.
func ValidTier(tier string) bool {
	switch tier {
	case "light", "standard", "deep":
		return true
	default:
		return false
	}
}

func loadArtifacts(dir string) artifactSet {
	read := func(name string) string {
		data, err := os.ReadFile(filepath.Join(dir, name))
		if err != nil {
			return ""
		}
		return string(data)
	}

	return artifactSet{
		dir:           dir,
		spec:          read("spec.md"),
		alignment:     read("alignment.md"),
		context:       read("context.md"),
		references:    read("references.md"),
		workflowState: read("workflow-state.md"),
		requirements:  read(filepath.Join("checklists", "requirements.md")),
		handoff:       read(filepath.Join("brainstorming", "handoff-to-specify.json")),
		specContract:  read("spec-contract.json"),
	}
}
