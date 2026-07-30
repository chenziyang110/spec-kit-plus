package main

import (
	"bytes"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestPRDBuildScaffoldCreatesStableDocumentsAndPreservesResumeContent(t *testing.T) {
	projectRoot := t.TempDir()
	runID := "260729-scaffold"
	installPRDBuildScaffoldTemplates(t, projectRoot, "")
	runDir := seedPRDRunFixture(t, projectRoot, runID, prdFixtureOptions{
		command: "sp-prd-scan", status: "ready-for-build", scanStatus: "complete", buildStatus: "pending",
		classification: "mixed", nextCommand: "/sp.prd-build", freshness: "fresh", latestRun: runID,
	})

	service := prdService{projectRoot: projectRoot}
	result, err := service.scaffoldBuild(runID)
	if err != nil {
		t.Fatalf("scaffold PRD build: %v", err)
	}
	if result["created_count"] != len(prdBuildScaffoldCatalog) || result["transaction"] == nil {
		t.Fatalf("scaffold result = %#v", result)
	}
	if savings, ok := result["estimated_token_savings"].(int); !ok || savings <= 0 {
		t.Fatalf("estimated token savings = %#v", result["estimated_token_savings"])
	}
	masterPath := filepath.Join(runDir, "master", "master-pack.md")
	master, err := os.ReadFile(masterPath)
	if err != nil {
		t.Fatalf("read scaffolded master pack: %v", err)
	}
	if !bytes.Contains(master, []byte(runID)) || bytes.Contains(master, []byte("[PROJECT]")) || !bytes.Contains(master, []byte("## Capability Inventory")) {
		t.Fatalf("master scaffold did not render stable values: %s", master)
	}
	if bytes.Contains(master, []byte(filepath.ToSlash(projectRoot))) || !bytes.Contains(master, []byte("**Source Workspace**: .")) {
		t.Fatalf("master scaffold must use stable project-relative scope: %s", master)
	}
	if err := os.WriteFile(masterPath, append(master, []byte("\nSemantic resume content.\n")...), 0o644); err != nil {
		t.Fatalf("seed resume content: %v", err)
	}
	resumeState := prdWorkflowStateFixture(runID, prdFixtureOptions{
		command: "sp-prd-build", status: "synthesizing", scanStatus: "complete", buildStatus: "executing",
		classification: "mixed", nextCommand: "none",
	})
	if err := os.WriteFile(filepath.Join(runDir, "workflow-state.md"), []byte(resumeState), 0o644); err != nil {
		t.Fatalf("seed resumable PRD build state: %v", err)
	}

	replayed, err := service.scaffoldBuild(runID)
	if err != nil {
		t.Fatalf("resume scaffold: %v", err)
	}
	if replayed["created_count"] != 0 || replayed["existing_count"] != len(prdBuildScaffoldCatalog) || replayed["transaction"] != nil {
		t.Fatalf("resume scaffold result = %#v", replayed)
	}
	master, _ = os.ReadFile(masterPath)
	if !bytes.Contains(master, []byte("Semantic resume content.")) {
		t.Fatalf("resume scaffold overwrote semantic content: %s", master)
	}
}

func TestPRDBuildScaffoldFailsBeforeWritingWhenInstalledTemplateIsMissing(t *testing.T) {
	projectRoot := t.TempDir()
	runID := "260729-missing-template"
	installPRDBuildScaffoldTemplates(t, projectRoot, "prd/export-error-semantics-template.md")
	runDir := seedPRDRunFixture(t, projectRoot, runID, prdFixtureOptions{
		command: "sp-prd-scan", status: "ready-for-build", scanStatus: "complete", buildStatus: "pending",
		classification: "service", nextCommand: "/sp.prd-build", freshness: "fresh", latestRun: runID,
	})

	_, err := (prdService{projectRoot: projectRoot}).scaffoldBuild(runID)
	if err == nil || !strings.Contains(err.Error(), "installed PRD template") {
		t.Fatalf("missing template error = %v", err)
	}
	for _, surface := range prdBuildScaffoldCatalog {
		if _, statErr := os.Stat(filepath.Join(runDir, filepath.FromSlash(surface.Path))); !os.IsNotExist(statErr) {
			t.Fatalf("scaffold wrote %s before validating every template", surface.Path)
		}
	}
}

func TestPRDBuildDocumentsRejectGenericPrepare(t *testing.T) {
	projectRoot := t.TempDir()
	runID := "260729-build-owner"
	seedPRDRunFixture(t, projectRoot, runID, prdFixtureOptions{
		command: "sp-prd-scan", status: "ready-for-build", scanStatus: "complete", buildStatus: "pending",
		classification: "ui", nextCommand: "/sp.prd-build", freshness: "fresh", latestRun: runID,
	})
	path := filepath.ToSlash(filepath.Join(".specify", "prd-runs", runID, "master", "master-pack.md"))
	var stdout, stderr bytes.Buffer
	code := Run([]string{"artifact", "prepare", "--path", path, "--format", "json", "--project-root", projectRoot}, &stdout, &stderr, "test")
	if code != 2 || !strings.Contains(stdout.String(), "prd-build scaffold") {
		t.Fatalf("generic PRD build prepare should be rejected: code=%d stdout=%s stderr=%s", code, stdout.String(), stderr.String())
	}
}

func TestPRDBuildValidationRejectsUnresolvedScaffoldPlaceholders(t *testing.T) {
	if got := firstUnresolvedPRDTemplatePlaceholder("# Export\n\n- [CAPABILITY]\n"); got != "[CAPABILITY]" {
		t.Fatalf("placeholder detection = %q", got)
	}
	if got := firstUnresolvedPRDTemplatePlaceholder("- [x] done\n- [Guide](docs/guide.md)\n- citation [1]\n- inline `[foo, bar]`\n```json\n[\"value\"]\n```\n"); got != "" {
		t.Fatalf("valid markdown marker detected as placeholder: %q", got)
	}
}

func installPRDBuildScaffoldTemplates(t *testing.T, projectRoot, skip string) {
	t.Helper()
	for _, surface := range prdBuildScaffoldCatalog {
		if surface.TemplatePath == skip {
			continue
		}
		source := filepath.Join("..", "..", "templates", filepath.FromSlash(surface.TemplatePath))
		raw, err := os.ReadFile(source)
		if err != nil {
			t.Fatalf("read source PRD template %s: %v", source, err)
		}
		target := filepath.Join(projectRoot, ".specify", "templates", filepath.FromSlash(surface.TemplatePath))
		if err := os.MkdirAll(filepath.Dir(target), 0o755); err != nil {
			t.Fatalf("mkdir installed template dir: %v", err)
		}
		if err := os.WriteFile(target, raw, 0o644); err != nil {
			t.Fatalf("install PRD template %s: %v", target, err)
		}
	}
}
