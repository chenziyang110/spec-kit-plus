package main

import (
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strings"
)

type prdBuildScaffoldSurface struct {
	Path         string
	TemplatePath string
}

var prdBuildScaffoldCatalog = []prdBuildScaffoldSurface{
	{Path: "master/master-pack.md", TemplatePath: "prd/master-pack-template.md"},
	{Path: "exports/README.md", TemplatePath: "prd/export-readme-template.md"},
	{Path: "exports/prd.md", TemplatePath: "prd/export-prd-template.md"},
	{Path: "exports/reconstruction-appendix.md", TemplatePath: "prd/export-reconstruction-appendix-template.md"},
	{Path: "exports/data-model.md", TemplatePath: "prd/export-data-rules-template.md"},
	{Path: "exports/integration-contracts.md", TemplatePath: "prd/export-integration-contracts-template.md"},
	{Path: "exports/runtime-behaviors.md", TemplatePath: "prd/export-runtime-behaviors-template.md"},
	{Path: "exports/config-contracts.md", TemplatePath: "prd/export-config-contracts-template.md"},
	{Path: "exports/protocol-contracts.md", TemplatePath: "prd/export-protocol-contracts-template.md"},
	{Path: "exports/state-machines.md", TemplatePath: "prd/export-state-machines-template.md"},
	{Path: "exports/error-semantics.md", TemplatePath: "prd/export-error-semantics-template.md"},
	{Path: "exports/verification-surface.md", TemplatePath: "prd/export-verification-surface-template.md"},
	{Path: "exports/reconstruction-risks.md", TemplatePath: "prd/export-reconstruction-risks-template.md"},
}

func (service prdService) scaffoldBuild(runID string) (map[string]any, error) {
	runDir, err := service.resolveRunDir(runID)
	if err != nil {
		return nil, err
	}
	if err := validatePRDStageArtifacts(service.projectRoot, runDir, "prd-build-ready"); err != nil {
		return nil, fmt.Errorf("PRD build scaffold requires a sealed reconstruction-ready scan: %w", err)
	}
	workflow, err := loadPRDWorkflowDocument(filepath.Join(runDir, "workflow-state.md"))
	if err != nil {
		return nil, err
	}
	classification := strings.ToLower(strings.TrimSpace(workflow.fields["classification"]))
	if classification != "ui" && classification != "service" && classification != "mixed" {
		return nil, fmt.Errorf("workflow-state.md classification must be ui, service, or mixed before PRD build scaffold")
	}
	root, err := filepath.Abs(service.projectRoot)
	if err != nil {
		return nil, err
	}
	projectName := filepath.Base(root)
	if projectName == "." || strings.TrimSpace(projectName) == "" {
		projectName = "project"
	}

	updates := []fileTransactionUpdate{}
	created := []string{}
	existing := []string{}
	totalTemplateBytes := 0
	for _, surface := range prdBuildScaffoldCatalog {
		templatePath, err := secureProjectPath(root, filepath.ToSlash(filepath.Join(".specify", "templates", filepath.FromSlash(surface.TemplatePath))))
		if err != nil {
			return nil, err
		}
		templateRaw, err := os.ReadFile(templatePath)
		if err != nil {
			return nil, fmt.Errorf("read installed PRD template %s: %w", surface.TemplatePath, err)
		}
		if len(strings.TrimSpace(string(templateRaw))) == 0 {
			return nil, fmt.Errorf("installed PRD template %s is empty", surface.TemplatePath)
		}
		rendered := renderPRDBuildScaffold(string(templateRaw), projectName, filepath.Base(runDir), classification)
		totalTemplateBytes += len(rendered)
		target := filepath.Join(runDir, filepath.FromSlash(surface.Path))
		if info, statErr := os.Stat(target); statErr == nil {
			if info.IsDir() {
				return nil, fmt.Errorf("PRD build output path is a directory: %s", surface.Path)
			}
			existing = append(existing, prdBuildArtifactRef(filepath.Base(runDir), surface.Path))
			continue
		} else if !os.IsNotExist(statErr) {
			return nil, statErr
		}
		updates = append(updates, fileTransactionUpdate{Path: target, Content: []byte(rendered), Perm: 0o644})
		created = append(created, prdBuildArtifactRef(filepath.Base(runDir), surface.Path))
	}
	sort.Strings(created)
	sort.Strings(existing)
	var transaction any
	if len(updates) > 0 {
		receipt, err := applyFileTransaction(root, "prd-build-scaffold", updates)
		if err != nil {
			return nil, err
		}
		transaction = receipt
	}
	return map[string]any{
		"run_id":                  filepath.Base(runDir),
		"classification":          classification,
		"created_refs":            stringSliceToAny(created),
		"existing_refs":           stringSliceToAny(existing),
		"created_count":           len(created),
		"existing_count":          len(existing),
		"estimated_token_savings": totalTemplateBytes / 4,
		"transaction":             transaction,
		"next_action":             "fill only semantic Markdown sections through leased artifact patch calls",
	}, nil
}

func renderPRDBuildScaffold(template, projectName, runID, classification string) string {
	rendered := strings.ReplaceAll(template, "[PROJECT]", projectName)
	rendered = strings.ReplaceAll(rendered, "[RUN_ID]", runID)
	rendered = strings.ReplaceAll(rendered, "[ui | service | mixed]", classification)
	rendered = strings.ReplaceAll(rendered, "[REPOSITORY_OR_SCOPE]", ".")
	if !strings.HasSuffix(rendered, "\n") {
		rendered += "\n"
	}
	return rendered
}

func prdBuildArtifactRef(runID, relative string) string {
	return filepath.ToSlash(filepath.Join(".specify", "prd-runs", runID, filepath.FromSlash(relative)))
}

func isPRDBuildDocumentPath(path string) bool {
	if !strings.HasPrefix(path, ".specify/prd-runs/") {
		return false
	}
	parts := strings.Split(path, "/")
	if len(parts) < 4 {
		return false
	}
	relative := strings.Join(parts[3:], "/")
	for _, surface := range prdBuildScaffoldCatalog {
		if relative == surface.Path {
			return true
		}
	}
	return false
}
