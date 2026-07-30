package main

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"regexp"
	"sort"
	"strings"
)

type prdRecordSurface struct {
	Name    string
	Path    string
	RootKey string
}

var prdRecordIDPattern = regexp.MustCompile(`^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$`)

var prdRecordSurfaceCatalog = []prdRecordSurface{
	{Name: "coverage", Path: "coverage-ledger.json", RootKey: "rows"},
	{Name: "capability", Path: "capability-ledger.json", RootKey: "capabilities"},
	{Name: "artifact", Path: "artifact-contracts.json", RootKey: "artifacts"},
	{Name: "reconstruction-check", Path: "reconstruction-checklist.json", RootKey: "checks"},
	{Name: "entrypoint", Path: "entrypoint-ledger.json", RootKey: "entrypoints"},
	{Name: "config", Path: "config-contracts.json", RootKey: "configs"},
	{Name: "protocol", Path: "protocol-contracts.json", RootKey: "protocols"},
	{Name: "state-machine", Path: "state-machines.json", RootKey: "machines"},
	{Name: "error", Path: "error-semantics.json", RootKey: "errors"},
	{Name: "verification", Path: "verification-surfaces.json", RootKey: "surfaces"},
}

func canonicalPRDRecordSurface(value string) (prdRecordSurface, error) {
	normalized := strings.ToLower(strings.TrimSpace(value))
	normalized = strings.TrimSuffix(normalized, ".json")
	normalized = strings.ReplaceAll(normalized, "_", "-")
	aliases := map[string]string{
		"coverage-ledger":          "coverage",
		"capability-ledger":        "capability",
		"artifact-contracts":       "artifact",
		"reconstruction-checklist": "reconstruction-check",
		"check":                    "reconstruction-check",
		"entrypoint-ledger":        "entrypoint",
		"config-contracts":         "config",
		"protocol-contracts":       "protocol",
		"state-machines":           "state-machine",
		"error-semantics":          "error",
		"verification-surfaces":    "verification",
	}
	if alias := aliases[normalized]; alias != "" {
		normalized = alias
	}
	for _, surface := range prdRecordSurfaceCatalog {
		if surface.Name == normalized {
			return surface, nil
		}
	}
	names := make([]string, 0, len(prdRecordSurfaceCatalog))
	for _, surface := range prdRecordSurfaceCatalog {
		names = append(names, surface.Name)
	}
	return prdRecordSurface{}, fmt.Errorf("unknown PRD record surface %q; choose one of %s", value, strings.Join(names, ", "))
}

func (service prdService) recordDigests(runDir string) (map[string]any, error) {
	digests := map[string]any{}
	for _, surface := range prdRecordSurfaceCatalog {
		raw, err := os.ReadFile(filepath.Join(runDir, surface.Path))
		if err != nil {
			return nil, fmt.Errorf("read %s: %w", surface.Path, err)
		}
		digests[surface.Name] = fileContentSHA256(raw)
	}
	return digests, nil
}

func (service prdService) upsertRecord(runID, surfaceName, expectedSHA string, record map[string]any) (map[string]any, error) {
	surface, runDir, document, records, currentRaw, err := service.loadRecordSurface(runID, surfaceName, true)
	if err != nil {
		return nil, err
	}
	if err := validatePRDExpectedRecordSHA(expectedSHA, currentRaw); err != nil {
		return nil, err
	}
	if _, wrapped := record[surface.RootKey]; wrapped {
		return nil, fmt.Errorf("submit one compact %s record, not a reconstructed %s document", surface.Name, surface.Path)
	}
	recordID, err := requiredPRDRecordID(record)
	if err != nil {
		return nil, err
	}

	action := "created"
	matched := false
	for index, existing := range records {
		object, ok := existing.(map[string]any)
		if !ok {
			return nil, fmt.Errorf("%s %s[%d] must be an object", surface.Path, surface.RootKey, index)
		}
		if strings.TrimSpace(stringField(object, "id")) == recordID {
			if matched {
				return nil, fmt.Errorf("%s contains duplicate record id %q", surface.Path, recordID)
			}
			records[index] = clonePRDRecord(record)
			matched = true
			action = "updated"
		}
	}
	if !matched {
		records = append(records, clonePRDRecord(record))
	}
	sortPRDRecords(records)
	document[surface.RootKey] = records
	content, err := marshalPRDRecordDocument(document)
	if err != nil {
		return nil, err
	}
	return service.commitRecordMutation(runDir, surface, recordID, action, content)
}

func (service prdService) removeRecord(runID, surfaceName, recordID, expectedSHA string) (map[string]any, error) {
	surface, runDir, document, records, currentRaw, err := service.loadRecordSurface(runID, surfaceName, true)
	if err != nil {
		return nil, err
	}
	if err := validatePRDExpectedRecordSHA(expectedSHA, currentRaw); err != nil {
		return nil, err
	}
	recordID = strings.TrimSpace(recordID)
	if !prdRecordIDPattern.MatchString(recordID) {
		return nil, fmt.Errorf("--record-id must be a stable 1-128 character identifier")
	}
	filtered := make([]any, 0, len(records))
	removed := 0
	for index, existing := range records {
		object, ok := existing.(map[string]any)
		if !ok {
			return nil, fmt.Errorf("%s %s[%d] must be an object", surface.Path, surface.RootKey, index)
		}
		if strings.TrimSpace(stringField(object, "id")) == recordID {
			removed++
			continue
		}
		filtered = append(filtered, existing)
	}
	if removed == 0 {
		return nil, fmt.Errorf("%s has no record %q", surface.Path, recordID)
	}
	if removed > 1 {
		return nil, fmt.Errorf("%s contains duplicate record id %q", surface.Path, recordID)
	}
	sortPRDRecords(filtered)
	document[surface.RootKey] = filtered
	content, err := marshalPRDRecordDocument(document)
	if err != nil {
		return nil, err
	}
	return service.commitRecordMutation(runDir, surface, recordID, "removed", content)
}

func (service prdService) showRecord(runID, surfaceName, recordID string) (map[string]any, error) {
	surface, runDir, _, records, raw, err := service.loadRecordSurface(runID, surfaceName, false)
	if err != nil {
		return nil, err
	}
	recordID = strings.TrimSpace(recordID)
	if !prdRecordIDPattern.MatchString(recordID) {
		return nil, fmt.Errorf("--record-id must be a stable 1-128 character identifier")
	}
	var selected map[string]any
	for _, existing := range records {
		object, ok := existing.(map[string]any)
		if ok && strings.TrimSpace(stringField(object, "id")) == recordID {
			if selected != nil {
				return nil, fmt.Errorf("%s contains duplicate record id %q", surface.Path, recordID)
			}
			selected = object
		}
	}
	if selected == nil {
		return nil, fmt.Errorf("%s has no record %q", surface.Path, recordID)
	}
	return map[string]any{
		"run_id":       filepath.Base(runDir),
		"surface":      surface.Name,
		"artifact_ref": prdRecordArtifactRef(filepath.Base(runDir), surface),
		"file_sha256":  fileContentSHA256(raw),
		"record_id":    recordID,
		"record":       selected,
		"record_count": len(records),
	}, nil
}

func (service prdService) listRecords(runID, surfaceName string, limit int) (map[string]any, error) {
	surface, runDir, _, records, raw, err := service.loadRecordSurface(runID, surfaceName, false)
	if err != nil {
		return nil, err
	}
	if limit <= 0 {
		limit = 100
	}
	summaries := make([]any, 0, min(limit, len(records)))
	for index, existing := range records {
		if len(summaries) >= limit {
			break
		}
		object, ok := existing.(map[string]any)
		if !ok {
			return nil, fmt.Errorf("%s %s[%d] must be an object", surface.Path, surface.RootKey, index)
		}
		summary := map[string]any{"id": stringField(object, "id")}
		for _, field := range []string{"status", "tier", "name", "kind", "surface", "path", "capability_id"} {
			if value, exists := object[field]; exists && value != nil && strings.TrimSpace(fmt.Sprint(value)) != "" {
				summary[field] = value
			}
		}
		summaries = append(summaries, summary)
	}
	return map[string]any{
		"run_id":         filepath.Base(runDir),
		"surface":        surface.Name,
		"artifact_ref":   prdRecordArtifactRef(filepath.Base(runDir), surface),
		"file_sha256":    fileContentSHA256(raw),
		"record_count":   len(records),
		"returned_count": len(summaries),
		"truncated":      len(summaries) < len(records),
		"records":        summaries,
	}, nil
}

func (service prdService) loadRecordSurface(runID, surfaceName string, mutation bool) (prdRecordSurface, string, map[string]any, []any, []byte, error) {
	surface, err := canonicalPRDRecordSurface(surfaceName)
	if err != nil {
		return prdRecordSurface{}, "", nil, nil, nil, err
	}
	runDir, err := service.resolveRunDir(runID)
	if err != nil {
		return prdRecordSurface{}, "", nil, nil, nil, err
	}
	if mutation {
		if err := service.requirePRDScanRecordMutation(runDir); err != nil {
			return prdRecordSurface{}, "", nil, nil, nil, err
		}
	}
	path := filepath.Join(runDir, surface.Path)
	raw, err := os.ReadFile(path)
	if err != nil {
		return prdRecordSurface{}, "", nil, nil, nil, fmt.Errorf("read %s: %w", surface.Path, err)
	}
	var document map[string]any
	if err := json.Unmarshal(raw, &document); err != nil || document == nil {
		if err == nil {
			err = fmt.Errorf("top-level value is not an object")
		}
		return prdRecordSurface{}, "", nil, nil, nil, fmt.Errorf("parse %s: %w", surface.Path, err)
	}
	records, ok := document[surface.RootKey].([]any)
	if !ok {
		return prdRecordSurface{}, "", nil, nil, nil, fmt.Errorf("%s must contain top-level array %q", surface.Path, surface.RootKey)
	}
	return surface, runDir, document, records, raw, nil
}

func (service prdService) requirePRDScanRecordMutation(runDir string) error {
	document, err := loadPRDWorkflowDocument(filepath.Join(runDir, "workflow-state.md"))
	if err != nil {
		return err
	}
	active := strings.ToLower(strings.TrimSpace(document.fields["active_command"]))
	if active != "sp-prd-scan" && active != "sp-prd" {
		return fmt.Errorf("PRD scan contracts are immutable while active_command is %q", active)
	}
	return nil
}

func validatePRDExpectedRecordSHA(expected string, currentRaw []byte) error {
	expected = strings.ToLower(strings.TrimSpace(expected))
	if !validArtifactSHA256(expected) {
		return fmt.Errorf("--expected-sha256 is required and must be a 64-character SHA-256 from prd-scan init, status, record-list, record-show, or the previous mutation")
	}
	current := fileContentSHA256(currentRaw)
	if expected != current {
		return fmt.Errorf("PRD record artifact changed since inspection: expected %s, current %s", expected, current)
	}
	return nil
}

func requiredPRDRecordID(record map[string]any) (string, error) {
	recordID := strings.TrimSpace(stringField(record, "id"))
	if !prdRecordIDPattern.MatchString(recordID) {
		return "", fmt.Errorf("record.id must be a stable 1-128 character identifier")
	}
	return recordID, nil
}

func clonePRDRecord(record map[string]any) map[string]any {
	raw, _ := json.Marshal(record)
	var cloned map[string]any
	_ = json.Unmarshal(raw, &cloned)
	return cloned
}

func sortPRDRecords(records []any) {
	sort.SliceStable(records, func(left, right int) bool {
		leftObject, _ := records[left].(map[string]any)
		rightObject, _ := records[right].(map[string]any)
		leftID := strings.TrimSpace(stringField(leftObject, "id"))
		rightID := strings.TrimSpace(stringField(rightObject, "id"))
		if leftID == "" {
			return false
		}
		if rightID == "" {
			return true
		}
		return leftID < rightID
	})
}

func marshalPRDRecordDocument(document map[string]any) ([]byte, error) {
	raw, err := json.MarshalIndent(document, "", "  ")
	if err != nil {
		return nil, fmt.Errorf("render PRD record artifact: %w", err)
	}
	return append(raw, '\n'), nil
}

func (service prdService) commitRecordMutation(runDir string, surface prdRecordSurface, recordID, action string, content []byte) (map[string]any, error) {
	updates := []fileTransactionUpdate{{Path: filepath.Join(runDir, surface.Path), Content: content, Perm: 0o644}}
	statusInvalidated := false
	statusPath, err := service.statusPath()
	if err != nil {
		return nil, err
	}
	status, err := readJSONObject(statusPath)
	if err != nil {
		return nil, fmt.Errorf("read PRD status before record mutation: %w", err)
	}
	if stringField(status, "freshness") == "fresh" && stringField(status, "latest_run") == filepath.Base(runDir) {
		status["freshness"] = "full-stale"
		status["last_refresh_at"] = nowUTCString()
		status["last_refresh_basis"] = "prd-record-mutated"
		status["last_refresh_scope"] = "full"
		statusRaw, err := marshalPRDRecordDocument(status)
		if err != nil {
			return nil, err
		}
		updates = append(updates, fileTransactionUpdate{Path: statusPath, Content: statusRaw, Perm: 0o644})
		statusInvalidated = true
	}
	receipt, err := applyFileTransaction(service.projectRoot, "prd-record-"+action, updates)
	if err != nil {
		return nil, err
	}
	document, err := readJSONObject(filepath.Join(runDir, surface.Path))
	if err != nil {
		return nil, err
	}
	records, _ := document[surface.RootKey].([]any)
	return map[string]any{
		"run_id":             filepath.Base(runDir),
		"surface":            surface.Name,
		"artifact_ref":       prdRecordArtifactRef(filepath.Base(runDir), surface),
		"file_sha256":        fileContentSHA256(content),
		"record_id":          recordID,
		"record_action":      action,
		"record_count":       len(records),
		"status_invalidated": statusInvalidated,
		"transaction":        receipt,
	}, nil
}

func prdRecordArtifactRef(runID string, surface prdRecordSurface) string {
	return filepath.ToSlash(filepath.Join(".specify", "prd-runs", runID, surface.Path))
}
