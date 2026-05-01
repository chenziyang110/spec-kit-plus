package main

import (
	"flag"
	"fmt"
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
	dir := flag.String("dir", ".", "feature directory path (containing spec.md, alignment.md, etc.)")
	tier := flag.String("tier", "standard", "check tier: light, standard, deep")
	printVersion := flag.Bool("version", false, "print version and exit")
	flag.Parse()

	if *printVersion {
		fmt.Printf("spec-lint %s (commit %s, built %s)\n", version, commit, date)
		os.Exit(0)
	}

	artifacts := loadArtifacts(*dir)
	runner := newRunner(*tier)
	results := runner.run(artifacts)

	printReport(*dir, *tier, results)

	for _, r := range results {
		if r.status == statusFail {
			os.Exit(1)
		}
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
