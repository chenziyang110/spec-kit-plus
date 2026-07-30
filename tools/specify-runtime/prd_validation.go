package main

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"time"
)

type prdStatusDocument struct {
	Version                      int    `json:"version"`
	StatusFamily                 string `json:"status_family"`
	Freshness                    string `json:"freshness"`
	LastRefreshCommit            string `json:"last_refresh_commit"`
	LastRefreshBranch            string `json:"last_refresh_branch"`
	LastRefreshAt                string `json:"last_refresh_at"`
	LastRefreshScope             string `json:"last_refresh_scope"`
	LastRefreshBasis             string `json:"last_refresh_basis"`
	LastRefreshChangedFilesBasis []any  `json:"last_refresh_changed_files_basis"`
	ManualForceStale             bool   `json:"manual_force_stale"`
	ManualForceStaleReasons      []any  `json:"manual_force_stale_reasons"`
	LatestRun                    string `json:"latest_run"`
}

type prdWorkflowDocument struct {
	frontmatter map[string]string
	fields      map[string]string
	lists       map[string][]string
}

var prdValidationScanDirectorySurfaces = map[string]string{"workspace": ".", "evidence": "evidence", "scan_packets": "scan-packets", "worker_results": "worker-results", "master": "master", "exports": "exports"}
var prdValidationScanFileSurfaces = map[string]string{"workflow_state": "workflow-state.md", "prd_scan": "prd-scan.md", "coverage_ledger": "coverage-ledger.md"}
var prdValidationScanJSONSurfaces = map[string]string{
	"coverage_ledger_json":          "coverage-ledger.json",
	"capability_ledger_json":        "capability-ledger.json",
	"artifact_contracts_json":       "artifact-contracts.json",
	"reconstruction_checklist_json": "reconstruction-checklist.json",
	"entrypoint_ledger_json":        "entrypoint-ledger.json",
	"config_contracts_json":         "config-contracts.json",
	"protocol_contracts_json":       "protocol-contracts.json",
	"state_machines_json":           "state-machines.json",
	"error_semantics_json":          "error-semantics.json",
	"verification_surfaces_json":    "verification-surfaces.json",
}
var prdValidationBuildSurfaces = map[string]string{
	"master_pack":             "master/master-pack.md",
	"package_readme":          "exports/README.md",
	"prd_export":              "exports/prd.md",
	"reconstruction_appendix": "exports/reconstruction-appendix.md",
	"data_model":              "exports/data-model.md",
	"integration_contracts":   "exports/integration-contracts.md",
	"runtime_behaviors":       "exports/runtime-behaviors.md",
	"config_contracts":        "exports/config-contracts.md",
	"protocol_contracts":      "exports/protocol-contracts.md",
	"state_machines":          "exports/state-machines.md",
	"error_semantics":         "exports/error-semantics.md",
	"verification_surface":    "exports/verification-surface.md",
	"reconstruction_risks":    "exports/reconstruction-risks.md",
}
var prdValidationScanSurfaceKeys = []string{"workspace", "evidence", "scan_packets", "worker_results", "master", "exports", "workflow_state", "prd_scan", "coverage_ledger", "coverage_ledger_json", "capability_ledger_json", "artifact_contracts_json", "reconstruction_checklist_json", "entrypoint_ledger_json", "config_contracts_json", "protocol_contracts_json", "state_machines_json", "error_semantics_json", "verification_surfaces_json"}
var prdValidationBuildSurfaceKeys = []string{"master_pack", "package_readme", "prd_export", "reconstruction_appendix", "data_model", "integration_contracts", "runtime_behaviors", "config_contracts", "protocol_contracts", "state_machines", "error_semantics", "verification_surface", "reconstruction_risks"}

func validatePRDStageArtifacts(projectRoot, featurePath, command string) error {
	stage := strings.ToLower(strings.TrimSpace(command))
	if stage != "prd-scan" && stage != "prd-build-ready" && stage != "prd-build" && stage != "prd" {
		return fmt.Errorf("unsupported prd validation command %q", command)
	}

	runDir, runID, err := resolvePRDValidationRunDir(projectRoot, featurePath)
	if err != nil {
		return err
	}

	statusPath, err := secureProjectPath(projectRoot, ".specify/prd/status.json")
	if err != nil {
		return err
	}
	status, statusRaw, err := loadPRDStatusDocument(statusPath)
	if err != nil {
		return err
	}
	if err := validatePRDStatusDocument(status, statusRaw, runID); err != nil {
		return err
	}
	liveFreshness, changedFiles, err := evaluatePRDFreshness(projectRoot, status)
	if err != nil {
		return fmt.Errorf("evaluate live PRD freshness: %w", err)
	}
	if liveFreshness != "fresh" {
		return fmt.Errorf(
			".specify/prd/status.json is %s against the current project state (changed_files=%d); rerun prd-scan and finalize the run",
			liveFreshness,
			len(changedFiles),
		)
	}
	return validatePRDRunArtifacts(runDir, stage)
}

func validatePRDRunArtifacts(runDir, stage string) error {
	stage = strings.ToLower(strings.TrimSpace(stage))
	if stage != "prd-scan" && stage != "prd-build-ready" && stage != "prd-build" && stage != "prd" {
		return fmt.Errorf("unsupported prd validation stage %q", stage)
	}
	runID := filepath.Base(filepath.Clean(runDir))
	workflowPath := filepath.Join(runDir, "workflow-state.md")
	workflow, err := loadPRDWorkflowDocument(workflowPath)
	if err != nil {
		return err
	}
	if err := validatePRDWorkflowDocument(workflow, runID, stage); err != nil {
		return err
	}

	if err := validatePRDSurfaceCompleteness(runDir, stage); err != nil {
		return err
	}
	if err := validatePRDCanonicalJSONContracts(runDir); err != nil {
		return err
	}
	if err := validatePRDWorkerResults(runDir); err != nil {
		return err
	}
	if err := validatePRDBuildInputContracts(runDir); err != nil {
		return err
	}
	if stage == "prd-build" {
		if err := validatePRDBuildOutputs(runDir); err != nil {
			return err
		}
	}
	if err := validatePRDReadyBinding(workflow, stage); err != nil {
		return err
	}
	return nil
}

func resolvePRDValidationRunDir(projectRoot, featurePath string) (string, string, error) {
	if strings.TrimSpace(featurePath) == "" {
		return "", "", fmt.Errorf("feature path is required for prd validation")
	}

	var runDir string
	var err error
	if filepath.IsAbs(featurePath) || filepath.VolumeName(featurePath) != "" {
		root, rootErr := filepath.Abs(projectRoot)
		if rootErr != nil {
			return "", "", rootErr
		}
		root, rootErr = filepath.EvalSymlinks(root)
		if rootErr != nil {
			return "", "", rootErr
		}
		resolved, absErr := filepath.Abs(featurePath)
		if absErr != nil {
			return "", "", absErr
		}
		rel, relErr := filepath.Rel(root, resolved)
		if relErr != nil || rel == ".." || strings.HasPrefix(rel, ".."+string(filepath.Separator)) {
			return "", "", fmt.Errorf("prd validation path must stay inside the project root")
		}
		runDir = resolved
	} else if strings.Contains(featurePath, "/") || strings.Contains(featurePath, "\\") {
		runDir, err = secureProjectPath(projectRoot, filepath.ToSlash(featurePath))
	} else {
		runDir, err = secureProjectPath(projectRoot, filepath.ToSlash(filepath.Join(".specify", "prd-runs", featurePath)))
	}
	if err != nil {
		return "", "", err
	}
	info, err := os.Stat(runDir)
	if err != nil {
		return "", "", fmt.Errorf("prd run workspace is missing: %w", err)
	}
	if !info.IsDir() {
		return "", "", fmt.Errorf("prd run workspace must be a directory")
	}
	return runDir, filepath.Base(runDir), nil
}

func loadPRDStatusDocument(path string) (prdStatusDocument, map[string]any, error) {
	rawBytes, err := os.ReadFile(path)
	if err != nil {
		return prdStatusDocument{}, nil, fmt.Errorf("read .specify/prd/status.json: %w", err)
	}
	var raw map[string]any
	if err := json.Unmarshal(rawBytes, &raw); err != nil {
		return prdStatusDocument{}, nil, fmt.Errorf(".specify/prd/status.json must be valid JSON: %w", err)
	}
	if raw == nil {
		return prdStatusDocument{}, nil, fmt.Errorf(".specify/prd/status.json must contain a JSON object")
	}
	var doc prdStatusDocument
	if err := json.Unmarshal(rawBytes, &doc); err != nil {
		return prdStatusDocument{}, nil, fmt.Errorf(".specify/prd/status.json schema decode failed: %w", err)
	}
	return doc, raw, nil
}

func validatePRDStatusDocument(doc prdStatusDocument, raw map[string]any, runID string) error {
	requiredKeys := []string{
		"version",
		"status_family",
		"freshness",
		"last_refresh_commit",
		"last_refresh_branch",
		"last_refresh_at",
		"last_refresh_scope",
		"last_refresh_basis",
		"last_refresh_changed_files_basis",
		"manual_force_stale",
		"manual_force_stale_reasons",
		"latest_run",
	}
	for _, key := range requiredKeys {
		if _, ok := raw[key]; !ok {
			return fmt.Errorf(".specify/prd/status.json is missing required field %q", key)
		}
	}
	if doc.Version != 1 {
		return fmt.Errorf(".specify/prd/status.json version must be 1")
	}
	if doc.StatusFamily != "prd" {
		return fmt.Errorf(".specify/prd/status.json status_family must be \"prd\"")
	}
	if doc.Freshness != "fresh" {
		return fmt.Errorf(".specify/prd/status.json freshness must be \"fresh\" for a validated prd run")
	}
	if strings.TrimSpace(doc.LastRefreshAt) == "" {
		return fmt.Errorf(".specify/prd/status.json last_refresh_at must be non-empty")
	}
	if _, err := time.Parse(time.RFC3339, doc.LastRefreshAt); err != nil {
		return fmt.Errorf(".specify/prd/status.json last_refresh_at must be valid RFC3339: %w", err)
	}
	if strings.TrimSpace(doc.LastRefreshCommit) == "" {
		return fmt.Errorf(".specify/prd/status.json last_refresh_commit must be non-empty")
	}
	if strings.TrimSpace(doc.LastRefreshBranch) == "" {
		return fmt.Errorf(".specify/prd/status.json last_refresh_branch must be non-empty")
	}
	if strings.TrimSpace(doc.LastRefreshBasis) == "" {
		return fmt.Errorf(".specify/prd/status.json last_refresh_basis must be non-empty")
	}
	if doc.LastRefreshScope != "full" && doc.LastRefreshScope != "targeted" {
		return fmt.Errorf(".specify/prd/status.json last_refresh_scope must be \"full\" or \"targeted\"")
	}
	if strings.TrimSpace(doc.LatestRun) == "" {
		return fmt.Errorf(".specify/prd/status.json latest_run must be non-empty")
	}
	if doc.LatestRun != runID {
		return fmt.Errorf(".specify/prd/status.json latest_run %q does not match workspace %q", doc.LatestRun, runID)
	}
	if _, ok := raw["last_refresh_changed_files_basis"].([]any); !ok {
		return fmt.Errorf(".specify/prd/status.json last_refresh_changed_files_basis must be an array")
	}
	for index, value := range doc.LastRefreshChangedFilesBasis {
		if text, ok := value.(string); !ok || strings.TrimSpace(text) == "" {
			return fmt.Errorf(".specify/prd/status.json last_refresh_changed_files_basis[%d] must be a non-empty string", index)
		}
	}
	if _, ok := raw["manual_force_stale_reasons"].([]any); !ok {
		return fmt.Errorf(".specify/prd/status.json manual_force_stale_reasons must be an array")
	}
	for index, value := range doc.ManualForceStaleReasons {
		if text, ok := value.(string); !ok || strings.TrimSpace(text) == "" {
			return fmt.Errorf(".specify/prd/status.json manual_force_stale_reasons[%d] must be a non-empty string", index)
		}
	}
	if _, ok := raw["manual_force_stale"].(bool); !ok {
		return fmt.Errorf(".specify/prd/status.json manual_force_stale must be a boolean")
	}
	if doc.ManualForceStale || len(doc.ManualForceStaleReasons) > 0 {
		return fmt.Errorf(".specify/prd/status.json cannot be fresh while manual_force_stale is set")
	}
	return nil
}

func prdAllowedFreshness(value string) bool {
	switch strings.TrimSpace(value) {
	case "fresh", "targeted-stale", "full-stale", "missing":
		return true
	default:
		return false
	}
}

func loadPRDWorkflowDocument(path string) (prdWorkflowDocument, error) {
	raw, err := os.ReadFile(path)
	if err != nil {
		return prdWorkflowDocument{}, fmt.Errorf("read workflow-state.md: %w", err)
	}
	frontmatter, body := prdParseFrontmatter(string(raw))
	fields := prdExtractMarkdownFields(body)
	lists := map[string][]string{
		"allowed_artifact_writes": collectMarkdownSectionBullets(body, "Allowed Artifact Writes"),
		"forbidden_actions":       collectMarkdownSectionBullets(body, "Forbidden Actions"),
		"authoritative_files":     collectMarkdownSectionBullets(body, "Authoritative Files"),
	}
	if fields["next_command"] == "" {
		fields["next_command"] = strings.Trim(strings.TrimSpace(prdExtractSectionFirstValue(body)), "`")
	}
	return prdWorkflowDocument{
		frontmatter: frontmatter,
		fields:      fields,
		lists:       lists,
	}, nil
}

func collectMarkdownSectionBullets(body string, title string) []string {
	lines := strings.Split(body, "\n")
	inSection := false
	items := []string{}
	for _, raw := range lines {
		line := strings.TrimSpace(raw)
		if strings.HasPrefix(line, "## ") {
			inSection = strings.EqualFold(strings.TrimSpace(strings.TrimPrefix(line, "## ")), title)
			continue
		}
		if !inSection || !strings.HasPrefix(line, "- ") {
			continue
		}
		item := strings.TrimSpace(strings.TrimPrefix(line, "- "))
		if strings.Contains(item, ":") {
			continue
		}
		items = append(items, strings.Trim(item, "`"))
	}
	return items
}

func validatePRDWorkflowDocument(doc prdWorkflowDocument, runID string, stage string) error {
	if strings.TrimSpace(doc.frontmatter["id"]) != runID {
		return fmt.Errorf("workflow-state.md frontmatter id %q does not match workspace %q", doc.frontmatter["id"], runID)
	}
	if strings.TrimSpace(doc.frontmatter["slug"]) == "" {
		return fmt.Errorf("workflow-state.md frontmatter slug must be non-empty")
	}
	if doc.fields["phase_mode"] != "analysis-only" {
		return fmt.Errorf("workflow-state.md phase_mode must be analysis-only")
	}
	if len(doc.lists["allowed_artifact_writes"]) == 0 {
		return fmt.Errorf("workflow-state.md allowed_artifact_writes must be non-empty")
	}
	if len(doc.lists["forbidden_actions"]) == 0 {
		return fmt.Errorf("workflow-state.md forbidden_actions must be non-empty")
	}
	if len(doc.lists["authoritative_files"]) == 0 {
		return fmt.Errorf("workflow-state.md authoritative_files must be non-empty")
	}
	if strings.TrimSpace(doc.fields["classification"]) == "" || !prdAllowedClassification(doc.fields["classification"]) {
		return fmt.Errorf("workflow-state.md classification must be ui, service, or mixed")
	}
	if doc.fields["scan_status"] != "complete" {
		return fmt.Errorf("workflow-state.md scan_status must be complete")
	}
	if !prdNoneLike(doc.fields["failed_readiness_checks"]) {
		return fmt.Errorf("workflow-state.md failed_readiness_checks must be empty before validation")
	}

	switch stage {
	case "prd-scan":
		if doc.fields["active_command"] != "sp-prd-scan" {
			return fmt.Errorf("workflow-state.md active_command must be sp-prd-scan")
		}
		if doc.fields["status"] != "ready-for-build" {
			return fmt.Errorf("workflow-state.md status must be ready-for-build for prd-scan")
		}
	case "prd":
		if doc.fields["active_command"] != "sp-prd" {
			return fmt.Errorf("workflow-state.md active_command must be sp-prd")
		}
		if doc.fields["status"] != "ready-for-build" {
			return fmt.Errorf("workflow-state.md status must be ready-for-build for prd compatibility")
		}
	case "prd-build":
		if doc.fields["active_command"] != "sp-prd-build" {
			return fmt.Errorf("workflow-state.md active_command must be sp-prd-build")
		}
		if doc.fields["status"] != "complete" {
			return fmt.Errorf("workflow-state.md status must be complete for prd-build")
		}
		if doc.fields["build_status"] != "complete" {
			return fmt.Errorf("workflow-state.md build_status must be complete for prd-build")
		}
		if !prdNoneLike(doc.fields["failed_reverse_coverage_checks"]) {
			return fmt.Errorf("workflow-state.md failed_reverse_coverage_checks must be empty before build completion")
		}
	case "prd-build-ready":
		switch doc.fields["active_command"] {
		case "sp-prd-scan":
			if doc.fields["status"] != "ready-for-build" {
				return fmt.Errorf("workflow-state.md status must be ready-for-build before prd-build starts")
			}
			if doc.fields["build_status"] != "pending" {
				return fmt.Errorf("workflow-state.md build_status must be pending before prd-build starts")
			}
		case "sp-prd-build":
			if !prdBuildInProgressStatus(doc.fields["status"]) {
				return fmt.Errorf("workflow-state.md status must identify a resumable prd-build stage")
			}
			if doc.fields["build_status"] != "pending" && doc.fields["build_status"] != "executing" {
				return fmt.Errorf("workflow-state.md build_status must be pending or executing while prd-build is resumable")
			}
			if !prdNoneLike(doc.fields["failed_reverse_coverage_checks"]) {
				return fmt.Errorf("workflow-state.md failed_reverse_coverage_checks must be empty while prd-build is resumable")
			}
		default:
			return fmt.Errorf("workflow-state.md active_command must be sp-prd-scan or sp-prd-build for build readiness")
		}
	}
	return nil
}

func prdBuildInProgressStatus(value string) bool {
	switch strings.ToLower(strings.TrimSpace(value)) {
	case "validating", "executing-packets", "synthesizing", "reverse-validating":
		return true
	default:
		return false
	}
}

func prdAllowedClassification(value string) bool {
	switch strings.TrimSpace(value) {
	case "ui", "service", "mixed":
		return true
	default:
		return false
	}
}

func prdNoneLike(value string) bool {
	switch strings.ToLower(strings.Trim(strings.TrimSpace(value), "`")) {
	case "", "none", "[]", "n/a", "null":
		return true
	default:
		return false
	}
}

func validatePRDSurfaceCompleteness(runDir string, stage string) error {
	required := append([]string{}, prdValidationScanSurfaceKeys...)
	if stage == "prd-build" {
		required = append(required, prdValidationBuildSurfaceKeys...)
	}
	for _, key := range required {
		if err := validatePRDSurface(runDir, key); err != nil {
			return err
		}
	}
	if err := requireDirectoryEntries(filepath.Join(runDir, "evidence"), ".json"); err != nil {
		return fmt.Errorf("evidence directory must contain canonical evidence packets: %w", err)
	}
	if err := requireDirectoryEntries(filepath.Join(runDir, "scan-packets"), ".md"); err != nil {
		return fmt.Errorf("scan-packets directory must contain scan packets: %w", err)
	}
	if err := requireDirectoryEntries(filepath.Join(runDir, "worker-results"), ".json"); err != nil {
		return fmt.Errorf("worker-results directory must contain worker results: %w", err)
	}
	if stage == "prd-build" {
		for _, relative := range []string{
			"master/master-pack.md",
			"exports/README.md",
			"exports/prd.md",
			"exports/reconstruction-appendix.md",
			"exports/data-model.md",
			"exports/integration-contracts.md",
			"exports/runtime-behaviors.md",
			"exports/config-contracts.md",
			"exports/protocol-contracts.md",
			"exports/state-machines.md",
			"exports/error-semantics.md",
			"exports/verification-surface.md",
			"exports/reconstruction-risks.md",
		} {
			if err := requireNonEmptyFile(filepath.Join(runDir, filepath.FromSlash(relative))); err != nil {
				return fmt.Errorf("%s: %w", relative, err)
			}
		}
	}
	return nil
}

func validatePRDSurface(runDir string, key string) error {
	relative := prdValidationExpectedSurfaces()[key]
	if relative == "" {
		return fmt.Errorf("unknown prd surface key %q", key)
	}
	path := runDir
	if relative != "." {
		path = filepath.Join(runDir, filepath.FromSlash(relative))
	}
	info, err := os.Stat(path)
	if err != nil {
		return fmt.Errorf("required surface %s is missing", relative)
	}
	if relative == "." {
		if !info.IsDir() {
			return fmt.Errorf("required surface %s must be a directory", relative)
		}
		return nil
	}
	if filepath.Ext(relative) != "" {
		if info.IsDir() {
			return fmt.Errorf("required surface %s must be a file", relative)
		}
		return nil
	}
	if !info.IsDir() {
		return fmt.Errorf("required surface %s must be a directory", relative)
	}
	return nil
}

func prdValidationExpectedSurfaces() map[string]string {
	surfaces := map[string]string{}
	for key, value := range prdValidationScanDirectorySurfaces {
		surfaces[key] = value
	}
	for key, value := range prdValidationScanFileSurfaces {
		surfaces[key] = value
	}
	for key, value := range prdValidationScanJSONSurfaces {
		surfaces[key] = value
	}
	for key, value := range prdValidationBuildSurfaces {
		surfaces[key] = value
	}
	return surfaces
}

func requireDirectoryEntries(path string, suffix string) error {
	entries, err := os.ReadDir(path)
	if err != nil {
		return err
	}
	for _, entry := range entries {
		if entry.IsDir() {
			continue
		}
		if suffix == "" || strings.HasSuffix(strings.ToLower(entry.Name()), strings.ToLower(suffix)) {
			return nil
		}
	}
	return fmt.Errorf("no %s files found", suffix)
}

func requireNonEmptyFile(path string) error {
	info, err := os.Stat(path)
	if err != nil {
		return err
	}
	if info.IsDir() {
		return fmt.Errorf("must be a file")
	}
	if info.Size() == 0 {
		return fmt.Errorf("must not be empty")
	}
	return nil
}

func validatePRDCanonicalJSONContracts(runDir string) error {
	for _, spec := range []struct {
		path string
		key  string
	}{
		{path: "coverage-ledger.json", key: "rows"},
		{path: "capability-ledger.json", key: "capabilities"},
		{path: "artifact-contracts.json", key: "artifacts"},
		{path: "reconstruction-checklist.json", key: "checks"},
		{path: "entrypoint-ledger.json", key: "entrypoints"},
		{path: "config-contracts.json", key: "configs"},
		{path: "protocol-contracts.json", key: "protocols"},
		{path: "state-machines.json", key: "machines"},
		{path: "error-semantics.json", key: "errors"},
		{path: "verification-surfaces.json", key: "surfaces"},
	} {
		if err := validatePRDJSONArrayContract(filepath.Join(runDir, filepath.FromSlash(spec.path)), spec.path, spec.key); err != nil {
			return err
		}
	}
	return nil
}

func validatePRDJSONArrayContract(path string, label string, key string) error {
	rawBytes, err := os.ReadFile(path)
	if err != nil {
		return fmt.Errorf("%s: %w", label, err)
	}
	var raw map[string]any
	if err := json.Unmarshal(rawBytes, &raw); err != nil {
		return fmt.Errorf("%s must be valid JSON: %w", label, err)
	}
	if raw == nil {
		return fmt.Errorf("%s must contain a top-level object", label)
	}
	value, ok := raw[key]
	if !ok {
		return fmt.Errorf("%s must define top-level %q", label, key)
	}
	if _, ok := value.([]any); !ok {
		return fmt.Errorf("%s field %q must be an array", label, key)
	}
	if label == "coverage-ledger.json" {
		version, ok := raw["version"]
		if !ok {
			return fmt.Errorf("coverage-ledger.json must define top-level %q", "version")
		}
		if number, ok := version.(float64); !ok || int(number) != 1 {
			return fmt.Errorf("coverage-ledger.json version must be 1")
		}
	}
	return nil
}

func validatePRDWorkerResults(runDir string) error {
	resultsDir := filepath.Join(runDir, "worker-results")
	entries, err := os.ReadDir(resultsDir)
	if err != nil {
		return fmt.Errorf("worker-results: %w", err)
	}
	validated := 0
	for _, entry := range entries {
		if entry.IsDir() || !strings.EqualFold(filepath.Ext(entry.Name()), ".json") {
			continue
		}
		validated++
		label := filepath.ToSlash(filepath.Join("worker-results", entry.Name()))
		payload, err := loadPRDJSONObject(filepath.Join(resultsDir, entry.Name()), label)
		if err != nil {
			return err
		}
		for _, field := range []string{"lane_id", "reported_status", "confidence", "result_handoff_path"} {
			if strings.TrimSpace(prdAnyString(payload[field])) == "" {
				return fmt.Errorf("%s %s must be a non-empty string", label, field)
			}
		}
		status := strings.ToLower(strings.TrimSpace(prdAnyString(payload["reported_status"])))
		switch status {
		case "done", "done_with_concerns", "blocked", "needs_context":
		default:
			return fmt.Errorf("%s reported_status must be done, done_with_concerns, blocked, or needs_context", label)
		}
		for _, field := range []string{"paths_read", "key_facts", "evidence_refs", "recommended_contract_updates", "unknowns", "minimum_verification"} {
			values, ok := payload[field].([]any)
			if !ok {
				return fmt.Errorf("%s %s must be an array", label, field)
			}
			if field == "paths_read" {
				if len(values) == 0 {
					return fmt.Errorf("%s paths_read must be non-empty", label)
				}
				for index, value := range values {
					if strings.TrimSpace(prdAnyString(value)) == "" {
						return fmt.Errorf("%s paths_read[%d] must be a non-empty string", label, index)
					}
				}
			}
		}
	}
	if validated == 0 {
		return fmt.Errorf("worker-results must contain at least one JSON result file")
	}
	return nil
}

func validatePRDBuildInputContracts(runDir string) error {
	coverage, err := loadPRDJSONArray(runDir, "coverage-ledger.json", "rows")
	if err != nil {
		return err
	}
	if len(coverage) == 0 {
		return fmt.Errorf("coverage-ledger.json must include at least one substantive coverage row")
	}
	for index, value := range coverage {
		row, ok := value.(map[string]any)
		if !ok {
			return fmt.Errorf("coverage-ledger.json row %d must be an object", index+1)
		}
		subject := ""
		for _, key := range []string{"id", "surface", "path", "capability_id", "capability_ref"} {
			if subject = strings.TrimSpace(prdAnyString(row[key])); subject != "" {
				break
			}
		}
		if subject == "" {
			return fmt.Errorf("coverage-ledger.json row %d must identify a surface, path, or capability", index+1)
		}
		status := strings.TrimSpace(prdAnyString(row["status"]))
		if status == "" {
			status = strings.TrimSpace(prdAnyString(row["coverage_state"]))
		}
		if status == "" {
			return fmt.Errorf("coverage-ledger.json row %d must record status or coverage_state", index+1)
		}
		reason := strings.TrimSpace(prdAnyString(row["reason"]))
		if reason == "" {
			reason = strings.TrimSpace(prdAnyString(row["notes"]))
		}
		normalizedStatus := strings.ToLower(strings.ReplaceAll(status, "_", "-"))
		if normalizedStatus == "n/a" || normalizedStatus == "na" || normalizedStatus == "not-applicable" {
			if reason == "" && !prdHasEvidence(row["evidence"]) {
				return fmt.Errorf("coverage-ledger.json row %d not-applicable status requires evidence or a reason", index+1)
			}
		} else if !prdHasEvidence(row["evidence"]) {
			return fmt.Errorf("coverage-ledger.json row %d must record non-empty evidence", index+1)
		}
	}

	capabilities, err := loadPRDJSONArray(runDir, "capability-ledger.json", "capabilities")
	if err != nil {
		return err
	}
	critical := 0
	for index, value := range capabilities {
		capability, ok := value.(map[string]any)
		if !ok {
			return fmt.Errorf("capability-ledger.json capability %d must be an object", index+1)
		}
		if strings.EqualFold(strings.TrimSpace(prdAnyString(capability["tier"])), "critical") {
			critical++
			status := strings.ToLower(strings.TrimSpace(prdAnyString(capability["status"])))
			if status != "reconstruction-ready" && status != "l4 reconstruction-ready" {
				return fmt.Errorf("capability-ledger.json critical capability %d must be reconstruction-ready", index+1)
			}
		}
	}
	if critical == 0 {
		return fmt.Errorf("capability-ledger.json must include at least one critical capability")
	}

	for _, contract := range []struct {
		path string
		key  string
		name string
	}{
		{path: "artifact-contracts.json", key: "artifacts", name: "artifact"},
		{path: "reconstruction-checklist.json", key: "checks", name: "check"},
	} {
		items, err := loadPRDJSONArray(runDir, contract.path, contract.key)
		if err != nil {
			return err
		}
		if len(items) == 0 {
			return fmt.Errorf("%s must include at least one %s", contract.path, contract.name)
		}
		for index, value := range items {
			item, ok := value.(map[string]any)
			if !ok {
				return fmt.Errorf("%s %s %d must be an object", contract.path, contract.name, index+1)
			}
			for _, field := range []string{"id", "status"} {
				if strings.TrimSpace(prdAnyString(item[field])) == "" {
					return fmt.Errorf("%s %s %d must define non-empty %s", contract.path, contract.name, index+1, field)
				}
			}
		}
	}

	for _, required := range []struct {
		path   string
		suffix string
	}{
		{path: "scan-packets", suffix: ".md"},
		{path: "evidence", suffix: ".json"},
	} {
		if err := requirePRDSubstantiveEntry(filepath.Join(runDir, required.path), required.suffix); err != nil {
			return fmt.Errorf("%s must contain substantive %s evidence: %w", required.path, required.suffix, err)
		}
	}
	return nil
}

func validatePRDBuildOutputs(runDir string) error {
	for _, relative := range prdValidationBuildSurfaces {
		path := filepath.Join(runDir, filepath.FromSlash(relative))
		raw, err := os.ReadFile(path)
		if err != nil {
			return fmt.Errorf("%s: %w", relative, err)
		}
		if !prdHasSubstantiveMarkdown(string(raw)) {
			return fmt.Errorf("required build output must contain substantive content beyond headings: %s", relative)
		}
		if placeholder := firstUnresolvedPRDTemplatePlaceholder(string(raw)); placeholder != "" {
			return fmt.Errorf("%s contains unresolved PRD template placeholder %s", relative, placeholder)
		}
	}
	prdRaw, err := os.ReadFile(filepath.Join(runDir, "exports", "prd.md"))
	if err != nil {
		return err
	}
	content := string(prdRaw)
	for _, heading := range []string{"## Capability Overview", "## Critical Capability Notes", "## Unknowns and Evidence Confidence"} {
		if !strings.Contains(content, heading) {
			return fmt.Errorf("exports/prd.md is missing required section %s", heading)
		}
	}
	return nil
}

func loadPRDJSONArray(runDir, relative, key string) ([]any, error) {
	payload, err := loadPRDJSONObject(filepath.Join(runDir, filepath.FromSlash(relative)), relative)
	if err != nil {
		return nil, err
	}
	values, ok := payload[key].([]any)
	if !ok {
		return nil, fmt.Errorf("%s field %q must be an array", relative, key)
	}
	return values, nil
}

func loadPRDJSONObject(path, label string) (map[string]any, error) {
	raw, err := os.ReadFile(path)
	if err != nil {
		return nil, fmt.Errorf("%s: %w", label, err)
	}
	var payload map[string]any
	if err := json.Unmarshal(raw, &payload); err != nil {
		return nil, fmt.Errorf("%s must be valid JSON: %w", label, err)
	}
	if payload == nil {
		return nil, fmt.Errorf("%s must contain a top-level object", label)
	}
	return payload, nil
}

func prdAnyString(value any) string {
	text, _ := value.(string)
	return text
}

func prdHasEvidence(value any) bool {
	switch typed := value.(type) {
	case string:
		return strings.TrimSpace(typed) != ""
	case []any:
		if len(typed) == 0 {
			return false
		}
		for _, item := range typed {
			if strings.TrimSpace(prdAnyString(item)) == "" {
				return false
			}
		}
		return true
	default:
		return false
	}
}

func requirePRDSubstantiveEntry(root, suffix string) error {
	found := false
	err := filepath.WalkDir(root, func(path string, entry os.DirEntry, walkErr error) error {
		if walkErr != nil {
			return walkErr
		}
		if entry.IsDir() || !strings.EqualFold(filepath.Ext(entry.Name()), suffix) {
			return nil
		}
		info, err := entry.Info()
		if err != nil {
			return err
		}
		if info.Size() > 0 {
			found = true
		}
		return nil
	})
	if err != nil {
		return err
	}
	if !found {
		return fmt.Errorf("no non-empty %s files found", suffix)
	}
	return nil
}

func prdHasSubstantiveMarkdown(content string) bool {
	for _, raw := range strings.Split(content, "\n") {
		line := strings.TrimSpace(raw)
		if line == "" || strings.HasPrefix(line, "#") || strings.HasPrefix(line, "<!--") {
			continue
		}
		return true
	}
	return false
}

func firstUnresolvedPRDTemplatePlaceholder(content string) string {
	for offset := 0; offset < len(content); {
		start := strings.IndexByte(content[offset:], '[')
		if start < 0 {
			return ""
		}
		start += offset
		endRelative := strings.IndexByte(content[start+1:], ']')
		if endRelative < 0 {
			return ""
		}
		end := start + 1 + endRelative
		inner := strings.TrimSpace(content[start+1 : end])
		offset = end + 1
		if inner == "" || strings.EqualFold(inner, "x") || allDecimalDigits(inner) {
			continue
		}
		if insidePRDMarkdownCode(content, start) || (start > 0 && content[start-1] == '\\') {
			continue
		}
		if offset < len(content) && content[offset] == '(' {
			continue
		}
		return content[start:offset]
	}
	return ""
}

func insidePRDMarkdownCode(content string, offset int) bool {
	if strings.Count(content[:offset], "```")%2 == 1 {
		return true
	}
	lineStart := strings.LastIndexByte(content[:offset], '\n') + 1
	return strings.Count(content[lineStart:offset], "`")%2 == 1
}

func allDecimalDigits(value string) bool {
	if value == "" {
		return false
	}
	for _, r := range value {
		if r < '0' || r > '9' {
			return false
		}
	}
	return true
}

func validatePRDReadyBinding(doc prdWorkflowDocument, stage string) error {
	nextCommand := strings.TrimSpace(doc.fields["next_command"])
	switch stage {
	case "prd-scan", "prd":
		if nextCommand == "" || !strings.Contains(strings.ToLower(nextCommand), "prd-build") {
			return fmt.Errorf("workflow-state.md next_command must hand off to prd-build")
		}
		if !prdNoneLike(doc.fields["build_status"]) && doc.fields["build_status"] != "pending" {
			return fmt.Errorf("workflow-state.md build_status must remain pending before prd-build")
		}
	case "prd-build":
		if !prdNoneLike(nextCommand) && strings.Contains(strings.ToLower(nextCommand), "prd-scan") {
			return fmt.Errorf("workflow-state.md next_command must not route back to prd-scan after build completion")
		}
	case "prd-build-ready":
		if doc.fields["active_command"] == "sp-prd-scan" {
			if nextCommand == "" || !strings.Contains(strings.ToLower(nextCommand), "prd-build") {
				return fmt.Errorf("workflow-state.md next_command must hand off to prd-build")
			}
		} else if strings.Contains(strings.ToLower(nextCommand), "prd-scan") {
			return fmt.Errorf("workflow-state.md next_command must not route back to prd-scan while prd-build is resumable")
		}
	}
	return nil
}

func prdParseFrontmatter(text string) (map[string]string, string) {
	if !strings.HasPrefix(text, "---\n") && !strings.HasPrefix(text, "---\r\n") {
		return map[string]string{}, text
	}
	lines := strings.Split(text, "\n")
	end := -1
	for i := 1; i < len(lines); i++ {
		if strings.TrimSpace(strings.TrimSuffix(lines[i], "\r")) == "---" {
			end = i
			break
		}
	}
	if end < 0 {
		return map[string]string{}, text
	}
	frontmatter := map[string]string{}
	for _, raw := range lines[1:end] {
		line := strings.TrimSpace(raw)
		if line == "" || !strings.Contains(line, ":") {
			continue
		}
		parts := strings.SplitN(line, ":", 2)
		frontmatter[strings.TrimSpace(parts[0])] = strings.Trim(strings.TrimSpace(parts[1]), `"'`)
	}
	return frontmatter, strings.Join(lines[end+1:], "\n")
}

func prdExtractMarkdownFields(text string) map[string]string {
	result := map[string]string{}
	for _, raw := range strings.Split(text, "\n") {
		line := strings.TrimSpace(raw)
		if !strings.HasPrefix(line, "- ") || !strings.Contains(line, ":") {
			continue
		}
		parts := strings.SplitN(strings.TrimSpace(strings.TrimPrefix(line, "- ")), ":", 2)
		result[strings.ToLower(strings.TrimSpace(parts[0]))] = strings.Trim(strings.TrimSpace(parts[1]), `"'`+"`")
	}
	return result
}

func prdExtractSectionFirstValue(body string) string {
	lines := strings.Split(body, "\n")
	inSection := false
	for _, raw := range lines {
		line := strings.TrimSpace(raw)
		if strings.HasPrefix(line, "## ") {
			inSection = strings.EqualFold(strings.TrimSpace(strings.TrimPrefix(line, "## ")), "Next Command")
			continue
		}
		if !inSection || !strings.HasPrefix(line, "- ") {
			continue
		}
		return strings.TrimSpace(strings.TrimPrefix(line, "- "))
	}
	return ""
}
