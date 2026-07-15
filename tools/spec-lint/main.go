package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"os"
	"path/filepath"
)

// Set at build time with -ldflags.
var (
	version = "dev"
	commit  = "unknown"
	date    = "unknown"
)

func main() {
	dir := flag.String("dir", ".", "feature directory path (containing spec-contract.json and spec.md, or a legacy spec package)")
	tier := flag.String("tier", "standard", "check tier: light, standard, deep")
	format := flag.String("format", "text", "output format: text, json")
	showPasses := flag.Bool("show-passes", false, "include passing check names in JSON output")
	printVersion := flag.Bool("version", false, "print version and exit")
	flag.Parse()

	if *printVersion {
		fmt.Printf("spec-lint %s (commit %s, built %s)\n", version, commit, date)
		os.Exit(0)
	}
	if !validTier(*tier) {
		fmt.Fprintf(os.Stderr, "spec-lint: invalid tier %q; expected one of: light, standard, deep\n", *tier)
		os.Exit(2)
	}
	if !validFormat(*format) {
		fmt.Fprintf(os.Stderr, "spec-lint: invalid format %q; expected one of: text, json\n", *format)
		os.Exit(2)
	}

	artifacts := loadArtifacts(*dir)
	runner := newRunner(*tier)
	results := runner.run(artifacts)

	if *format == "json" {
		if err := printJSONReport(os.Stdout, *tier, results, *showPasses); err != nil {
			fmt.Fprintf(os.Stderr, "spec-lint: encode JSON report: %v\n", err)
			os.Exit(1)
		}
	} else {
		printReport(*dir, *tier, results)
	}

	for _, r := range results {
		if r.status == statusFail {
			os.Exit(1)
		}
	}
}

func validFormat(format string) bool {
	switch format {
	case "text", "json":
		return true
	default:
		return false
	}
}

func validTier(tier string) bool {
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

func printReport(dir, tier string, results []checkResult) {
	fmt.Printf("spec-lint %s\n", version)
	fmt.Printf("  directory: %s\n", dir)
	fmt.Printf("  tier:      %s\n\n", tier)

	passN, failN, warnN := 0, 0, 0
	for _, r := range results {
		switch r.status {
		case statusPass:
			fmt.Printf("  [PASS] %s\n", r.name)
			passN++
		case statusFail:
			fmt.Printf("  [FAIL] %s — %s\n", r.name, r.message)
			failN++
		case statusWarn:
			fmt.Printf("  [WARN] %s — %s\n", r.name, r.message)
			warnN++
		}
	}

	fmt.Printf("\n  %d passed, %d failed, %d warnings\n", passN, failN, warnN)
}

type reportSummary struct {
	Passed   int `json:"passed"`
	Failed   int `json:"failed"`
	Warnings int `json:"warnings"`
}

type reportDiagnostic struct {
	Name    string `json:"name"`
	Message string `json:"message"`
}

type agentReport struct {
	Status   string             `json:"status"`
	Tier     string             `json:"tier"`
	Summary  reportSummary      `json:"summary"`
	Failures []reportDiagnostic `json:"failures"`
	Warnings []reportDiagnostic `json:"warnings"`
	Passes   *[]string          `json:"passes,omitempty"`
}

func printJSONReport(w io.Writer, tier string, results []checkResult, showPasses bool) error {
	report := agentReport{
		Status:   "ok",
		Tier:     tier,
		Failures: []reportDiagnostic{},
		Warnings: []reportDiagnostic{},
	}
	passes := []string{}
	for _, result := range results {
		switch result.status {
		case statusPass:
			report.Summary.Passed++
			passes = append(passes, result.name)
		case statusFail:
			report.Summary.Failed++
			report.Failures = append(report.Failures, reportDiagnostic{Name: result.name, Message: result.message})
		case statusWarn:
			report.Summary.Warnings++
			report.Warnings = append(report.Warnings, reportDiagnostic{Name: result.name, Message: result.message})
		}
	}
	if report.Summary.Failed > 0 {
		report.Status = "failed"
	}
	if showPasses {
		report.Passes = &passes
	}
	return json.NewEncoder(w).Encode(report)
}
