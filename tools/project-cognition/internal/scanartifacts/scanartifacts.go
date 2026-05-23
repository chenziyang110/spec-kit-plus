package scanartifacts

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strings"

	rt "github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/runtime"
)

type ValidateOptions struct {
	RequireStatusJSON bool
}

type Result struct {
	Status       string         `json:"status"`
	Gate         string         `json:"gate"`
	Readiness    string         `json:"readiness"`
	Errors       []string       `json:"errors"`
	Warnings     []string       `json:"warnings"`
	CheckedPaths []string       `json:"checked_paths"`
	Details      map[string]any `json:"details"`
}

type Package struct {
	Evidence      []EvidenceRow
	Nodes         []NodeRow
	Edges         []EdgeRow
	Observations  []ObservationRow
	CoveragePaths []string
	Identities    IdentitySet
}

type IdentitySet struct {
	Evidence      map[string]bool `json:"evidence"`
	Nodes         map[string]bool `json:"nodes"`
	Edges         map[string]bool `json:"edges"`
	Observations  map[string]bool `json:"observations"`
	CoveragePaths map[string]bool `json:"coverage_paths"`
}

type EvidenceRow struct {
	ID          string
	SourceKind  string
	SourcePath  string
	CommitSHA   string
	Span        string
	Extractor   string
	ContentHash string
	Attrs       map[string]any
}

type NodeRow struct {
	ID          string
	Type        string
	Title       string
	Confidence  string
	Paths       []string
	EvidenceIDs []string
	Attrs       map[string]any
}

type EdgeRow struct {
	ID          string
	Type        string
	SourceID    string
	TargetID    string
	Confidence  string
	EvidenceIDs []string
	Attrs       map[string]any
}

type ObservationRow struct {
	ID              string
	ObservationType string
	Summary         string
	EvidenceIDs     []string
	Attrs           map[string]any
}

func Validate(paths rt.Paths, opts ValidateOptions) Result {
	_, result := Load(paths, opts)
	return result
}

func ValidateJSONFile(path string, label string) error {
	_, err := readJSONFile(path, label)
	return err
}

func Load(paths rt.Paths, opts ValidateOptions) (Package, Result) {
	result := newResult(requiredArtifactPaths(opts))
	pkg := Package{Identities: newIdentitySet()}
	for _, rel := range result.CheckedPaths {
		full := filepath.Join(paths.Root, filepath.FromSlash(rel))
		info, err := os.Stat(full)
		if err != nil {
			result.Errors = append(result.Errors, "missing "+rel)
			continue
		}
		if !info.IsDir() && filepath.Ext(full) == ".json" {
			if _, err := readJSONFile(full, filepath.Base(rel)); err != nil {
				result.Errors = append(result.Errors, err.Error())
			}
		}
	}
	loadOptionalWorkbenchJSON(paths, &result, "capability-ledger.json")
	loadOptionalWorkbenchJSON(paths, &result, "control-ledger.json")
	loadEvidence(paths, &pkg, &result)
	loadNodes(paths, &pkg, &result)
	loadEdges(paths, &pkg, &result)
	loadObservations(paths, &pkg, &result)
	loadCoverage(paths, &pkg, &result)
	result.Errors = append(result.Errors, ValidateCoverageLedger(paths, "scan")...)
	buildIdentities(&pkg)
	if len(result.Errors) > 0 {
		result.Status = "blocked"
		result.Readiness = "blocked"
	}
	result.Details["required_artifacts"] = result.CheckedPaths
	return pkg, result
}

func ValidateCoverageLedger(paths rt.Paths, owner string) []string {
	ledgerPath := filepath.Join(paths.RuntimeDir, "workbench", "coverage-ledger.json")
	payload, err := readJSONFile(ledgerPath, "coverage-ledger.json")
	if err != nil {
		return []string{err.Error()}
	}
	obj, ok := payload.(map[string]any)
	if !ok {
		return []string{"coverage-ledger.json must contain a top-level JSON object"}
	}
	if _, ok := obj["rows"].([]any); !ok {
		return []string{"coverage-ledger.json must define a top-level rows array"}
	}
	errors := []string{}
	if gaps, ok := obj["open_gaps"].([]any); ok {
		for _, gap := range gaps {
			gapObj, ok := gap.(map[string]any)
			if !ok {
				continue
			}
			reason := normalizedString(gapObj["reason"])
			status := normalizedString(gapObj["status"])
			gapOwner := normalizedString(gapObj["owner"])
			if reason == "subagent_blocked" || status == "blocked" {
				if owner == "" || gapOwner == "" || gapOwner == owner {
					errors = append(errors, "subagent_blocked coverage gap must be resolved before project cognition acceptance")
				}
			}
		}
	}
	return errors
}

func newResult(checked []string) Result {
	return Result{
		Status:       "ok",
		Gate:         "scan_acceptance",
		Readiness:    "scan_ready",
		Errors:       []string{},
		Warnings:     []string{},
		CheckedPaths: checked,
		Details:      map[string]any{},
	}
}

func requiredArtifactPaths(opts ValidateOptions) []string {
	required := []string{
		".specify/project-cognition/evidence",
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
	if opts.RequireStatusJSON {
		required = append(required, ".specify/project-cognition/status.json")
	}
	return required
}

func newIdentitySet() IdentitySet {
	return IdentitySet{
		Evidence:      map[string]bool{},
		Nodes:         map[string]bool{},
		Edges:         map[string]bool{},
		Observations:  map[string]bool{},
		CoveragePaths: map[string]bool{},
	}
}

func loadOptionalWorkbenchJSON(paths rt.Paths, result *Result, name string) {
	path := filepath.Join(paths.RuntimeDir, "workbench", name)
	if _, err := os.Stat(path); err != nil {
		return
	}
	if _, err := readJSONFile(path, name); err != nil {
		result.Errors = append(result.Errors, err.Error())
	}
}

func loadEvidence(paths rt.Paths, pkg *Package, result *Result) {
	evidenceDir := filepath.Join(paths.RuntimeDir, "evidence")
	entries, err := os.ReadDir(evidenceDir)
	if err != nil {
		return
	}
	sort.Slice(entries, func(i, j int) bool { return entries[i].Name() < entries[j].Name() })
	for _, entry := range entries {
		if entry.IsDir() || filepath.Ext(entry.Name()) != ".json" {
			continue
		}
		path := filepath.Join(evidenceDir, entry.Name())
		raw, err := readJSONFile(path, filepath.ToSlash(path))
		if err != nil {
			result.Errors = append(result.Errors, err.Error())
			continue
		}
		rows, err := evidenceRows(raw)
		if err != nil {
			result.Errors = append(result.Errors, filepath.ToSlash(path)+": "+err.Error())
			continue
		}
		stem := strings.TrimSuffix(entry.Name(), filepath.Ext(entry.Name()))
		for i, row := range rows {
			item := evidenceFromObject(row, stem, i)
			if strings.HasPrefix(item.SourcePath, ".specify/") {
				result.Errors = append(result.Errors, ".specify/** must not enter project cognition graph evidence")
			}
			pkg.Evidence = append(pkg.Evidence, item)
		}
	}
}

func loadNodes(paths rt.Paths, pkg *Package, result *Result) {
	raw, err := readJSONFile(filepath.Join(paths.RuntimeDir, "provisional", "nodes.json"), "nodes.json")
	if err != nil {
		result.Errors = append(result.Errors, err.Error())
		return
	}
	rows, err := arrayRows(raw, "nodes")
	if err != nil {
		result.Errors = append(result.Errors, "nodes.json: "+err.Error())
		return
	}
	for i, row := range rows {
		item := NodeRow{
			ID:          normalizedString(row["id"]),
			Type:        normalizedString(row["type"]),
			Title:       normalizedString(row["title"]),
			Confidence:  normalizedString(row["confidence"]),
			Paths:       normalizedStringSlice(row["paths"]),
			EvidenceIDs: normalizedStringSlice(row["evidence_ids"]),
			Attrs:       objectMap(row["attrs"]),
		}
		if item.ID == "" {
			result.Errors = append(result.Errors, fmt.Sprintf("nodes.json rows[%d] is missing id", i))
		}
		pkg.Nodes = append(pkg.Nodes, item)
	}
}

func loadEdges(paths rt.Paths, pkg *Package, result *Result) {
	raw, err := readJSONFile(filepath.Join(paths.RuntimeDir, "provisional", "edges.json"), "edges.json")
	if err != nil {
		result.Errors = append(result.Errors, err.Error())
		return
	}
	rows, err := arrayRows(raw, "edges")
	if err != nil {
		result.Errors = append(result.Errors, "edges.json: "+err.Error())
		return
	}
	for i, row := range rows {
		item := EdgeRow{
			ID:          normalizedString(row["id"]),
			Type:        normalizedString(row["type"]),
			SourceID:    normalizedString(row["source_id"]),
			TargetID:    normalizedString(row["target_id"]),
			Confidence:  normalizedString(row["confidence"]),
			EvidenceIDs: normalizedStringSlice(row["evidence_ids"]),
			Attrs:       objectMap(row["attrs"]),
		}
		if item.ID == "" {
			result.Errors = append(result.Errors, fmt.Sprintf("edges.json rows[%d] is missing id", i))
		}
		pkg.Edges = append(pkg.Edges, item)
	}
}

func loadObservations(paths rt.Paths, pkg *Package, result *Result) {
	raw, err := readJSONFile(filepath.Join(paths.RuntimeDir, "provisional", "observations.json"), "observations.json")
	if err != nil {
		result.Errors = append(result.Errors, err.Error())
		return
	}
	rows, err := arrayRows(raw, "observations")
	if err != nil {
		result.Errors = append(result.Errors, "observations.json: "+err.Error())
		return
	}
	for i, row := range rows {
		item := ObservationRow{
			ID:              normalizedString(row["id"]),
			ObservationType: normalizedString(row["observation_type"]),
			Summary:         normalizedString(row["summary"]),
			EvidenceIDs:     normalizedStringSlice(row["evidence_ids"]),
			Attrs:           objectMap(row["attrs"]),
		}
		if item.ID == "" {
			result.Errors = append(result.Errors, fmt.Sprintf("observations.json rows[%d] is missing id", i))
		}
		pkg.Observations = append(pkg.Observations, item)
	}
}

func loadCoverage(paths rt.Paths, pkg *Package, result *Result) {
	raw, err := readJSONFile(filepath.Join(paths.RuntimeDir, "coverage.json"), "coverage.json")
	if err != nil {
		result.Errors = append(result.Errors, err.Error())
		return
	}
	rows, err := arrayRows(raw, "rows")
	if err != nil {
		result.Errors = append(result.Errors, "coverage.json must define a top-level rows array")
		return
	}
	for i, row := range rows {
		path := normalizedString(row["path"])
		if path == "" {
			result.Errors = append(result.Errors, fmt.Sprintf("coverage.json rows[%d] is missing path", i))
			continue
		}
		if strings.HasPrefix(path, ".specify/") {
			result.Errors = append(result.Errors, ".specify/** must not enter project cognition graph evidence")
			continue
		}
		pkg.CoveragePaths = append(pkg.CoveragePaths, path)
	}
}

func buildIdentities(pkg *Package) {
	for _, row := range pkg.Evidence {
		pkg.Identities.Evidence[row.ID+"|"+row.SourcePath+"|"+row.ContentHash] = true
	}
	for _, row := range pkg.Nodes {
		pkg.Identities.Nodes[row.ID] = true
	}
	for _, row := range pkg.Edges {
		pkg.Identities.Edges[row.ID+"|"+row.SourceID+"|"+row.TargetID+"|"+row.Type] = true
	}
	for _, row := range pkg.Observations {
		pkg.Identities.Observations[row.ID] = true
	}
	for _, path := range pkg.CoveragePaths {
		pkg.Identities.CoveragePaths[path] = true
	}
}

func readJSONFile(path string, label string) (any, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, fmt.Errorf("%s: %w", label, err)
	}
	if len(data) >= 3 && data[0] == 0xEF && data[1] == 0xBB && data[2] == 0xBF {
		return nil, fmt.Errorf("%s contains UTF-8 BOM", label)
	}
	var raw any
	if err := json.Unmarshal(data, &raw); err != nil {
		return nil, fmt.Errorf("%s: %w", label, err)
	}
	return raw, nil
}

func evidenceRows(raw any) ([]map[string]any, error) {
	if arr, ok := raw.([]any); ok {
		return objectRows(arr)
	}
	obj, ok := raw.(map[string]any)
	if !ok {
		return nil, fmt.Errorf("must contain a top-level JSON object or array")
	}
	for _, key := range []string{"rows", "evidence"} {
		if arr, ok := obj[key].([]any); ok {
			return objectRows(arr)
		}
	}
	return []map[string]any{obj}, nil
}

func arrayRows(raw any, key string) ([]map[string]any, error) {
	if arr, ok := raw.([]any); ok {
		return objectRows(arr)
	}
	obj, ok := raw.(map[string]any)
	if !ok {
		return nil, fmt.Errorf("must contain a top-level JSON object or array")
	}
	for _, candidate := range []string{key, "rows"} {
		if arr, ok := obj[candidate].([]any); ok {
			return objectRows(arr)
		}
	}
	return nil, fmt.Errorf("must define a top-level %s array", key)
}

func objectRows(rows []any) ([]map[string]any, error) {
	objects := make([]map[string]any, 0, len(rows))
	for i, row := range rows {
		obj, ok := row.(map[string]any)
		if !ok {
			return nil, fmt.Errorf("rows[%d] must be an object", i)
		}
		objects = append(objects, obj)
	}
	return objects, nil
}

func evidenceFromObject(row map[string]any, fileStem string, index int) EvidenceRow {
	id := normalizedString(row["id"])
	if id == "" {
		id = fmt.Sprintf("%s-%d", fileStem, index)
	}
	contentHash := normalizedString(row["content_hash"])
	if contentHash == "" {
		contentHash = hashNormalizedObject(row)
	}
	return EvidenceRow{
		ID:          id,
		SourceKind:  normalizedString(row["source_kind"]),
		SourcePath:  normalizedString(row["source_path"]),
		CommitSHA:   normalizedString(row["commit_sha"]),
		Span:        normalizedString(row["span"]),
		Extractor:   normalizedString(row["extractor"]),
		ContentHash: contentHash,
		Attrs:       objectMap(row["attrs"]),
	}
}

func hashNormalizedObject(obj map[string]any) string {
	data, err := json.Marshal(obj)
	if err != nil {
		return ""
	}
	sum := sha256.Sum256(data)
	return hex.EncodeToString(sum[:])
}

func objectMap(value any) map[string]any {
	obj, ok := value.(map[string]any)
	if !ok {
		return map[string]any{}
	}
	return obj
}

func normalizedStringSlice(value any) []string {
	raw, ok := value.([]any)
	if !ok {
		return []string{}
	}
	values := []string{}
	for _, item := range raw {
		text := normalizedString(item)
		if text != "" {
			values = append(values, text)
		}
	}
	return values
}

func normalizedString(value any) string {
	text, _ := value.(string)
	text = filepath.ToSlash(strings.TrimSpace(text))
	return strings.TrimPrefix(text, "./")
}
