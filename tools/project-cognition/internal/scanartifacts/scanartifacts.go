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
	AcceptedGaps  map[string]bool
	Identities    IdentitySet
}

type Boundary struct {
	SchemaVersion         int
	LegacyRows            bool
	CandidatePaths        map[string]string
	IncludedPaths         map[string]bool
	ExcludedPaths         map[string]bool
	AmbiguousPaths        map[string]bool
	Dispositions          map[string]string
	ClassificationReasons map[string]string
	DecisionSource        map[string]string
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
			if rel == ".specify/project-cognition/status.json" {
				if err := validateJSONObjectFile(full, filepath.Base(rel)); err != nil {
					result.Errors = append(result.Errors, err.Error())
				}
				continue
			}
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
	pkg.AcceptedGaps = acceptedGapPaths(paths)
	boundary := loadBoundary(paths, &result)
	validateBoundaryCoverage(boundary, pkg, &result)
	result.Errors = append(result.Errors, validateCoverageLedger(paths, "scan")...)
	buildIdentities(&pkg)
	if len(result.Errors) > 0 {
		result.Status = "blocked"
		result.Readiness = "blocked"
	}
	result.Details["required_artifacts"] = result.CheckedPaths
	result.Details["boundary"] = map[string]any{
		"candidate_count": len(boundary.CandidatePaths),
		"included_count":  len(boundary.IncludedPaths),
		"excluded_count":  len(boundary.ExcludedPaths),
		"ambiguous_count": len(boundary.AmbiguousPaths),
	}
	return pkg, result
}

func validateCoverageLedger(paths rt.Paths, owner string) []string {
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
			if reason == "subagent_blocked" || status == "blocked" {
				errors = append(errors, "subagent_blocked coverage gap must be resolved before project cognition acceptance")
			}
		}
	}
	return errors
}

func validateJSONObjectFile(path string, label string) error {
	payload, err := readJSONFile(path, label)
	if err != nil {
		return err
	}
	if _, ok := payload.(map[string]any); !ok {
		return fmt.Errorf("%s must contain a top-level JSON object", label)
	}
	return nil
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

func loadBoundary(paths rt.Paths, result *Result) Boundary {
	boundary := Boundary{
		CandidatePaths:        map[string]string{},
		IncludedPaths:         map[string]bool{},
		ExcludedPaths:         map[string]bool{},
		AmbiguousPaths:        map[string]bool{},
		Dispositions:          map[string]string{},
		ClassificationReasons: map[string]string{},
		DecisionSource:        map[string]string{},
	}
	raw, err := readJSONFile(filepath.Join(paths.RuntimeDir, "workbench", "repository-universe.json"), "repository-universe.json")
	if err != nil {
		result.Errors = append(result.Errors, err.Error())
		return boundary
	}
	obj, ok := raw.(map[string]any)
	if !ok {
		result.Errors = append(result.Errors, "repository-universe.json must contain a top-level JSON object")
		return boundary
	}
	if rows, ok := obj["rows"]; ok {
		boundary.LegacyRows = true
		boundary.CandidatePaths = boundaryCandidatePaths(rows)
		for path := range boundary.CandidatePaths {
			boundary.IncludedPaths[path] = true
			boundary.CandidatePaths[path] = "inventory_only"
			boundary.Dispositions[path] = "inventory_only"
		}
		return boundary
	}
	boundary.SchemaVersion = intFromValue(obj["schema_version"])
	boundary.CandidatePaths = boundaryCandidatePaths(obj["candidate_universe"])
	boundary.IncludedPaths = boundaryPathsFromValue(obj["included_paths"])
	boundary.ExcludedPaths = boundaryPathsFromValue(obj["excluded_paths"])
	boundary.AmbiguousPaths = boundaryPathsFromValue(obj["ambiguous_paths"])
	boundary.Dispositions = boundaryDispositionMap(obj["dispositions"])
	boundary.ClassificationReasons = boundaryDispositionMap(obj["classification_reasons"])
	boundary.DecisionSource = boundaryDispositionMap(obj["decision_source"])
	return boundary
}

func boundaryPathsFromValue(value any) map[string]bool {
	paths := map[string]bool{}
	rows, ok := value.([]any)
	if !ok {
		return paths
	}
	for _, row := range rows {
		path := ""
		switch typed := row.(type) {
		case string:
			path = normalizedString(typed)
		case map[string]any:
			path = normalizedString(typed["path"])
		}
		if path != "" {
			paths[path] = true
		}
	}
	return paths
}

func boundaryDispositionMap(value any) map[string]string {
	values := map[string]string{}
	obj, ok := value.(map[string]any)
	if !ok {
		return values
	}
	for rawPath, rawValue := range obj {
		path := normalizedString(rawPath)
		item := normalizedString(rawValue)
		if path != "" && item != "" {
			values[path] = item
		}
	}
	return values
}

func boundaryCandidatePaths(value any) map[string]string {
	paths := map[string]string{}
	rows, ok := value.([]any)
	if !ok {
		return paths
	}
	for _, row := range rows {
		path := ""
		disposition := ""
		switch typed := row.(type) {
		case string:
			path = normalizedString(typed)
		case map[string]any:
			path = normalizedString(typed["path"])
			disposition = normalizedString(typed["disposition"])
		}
		if path != "" {
			paths[path] = disposition
		}
	}
	return paths
}

func validateBoundaryCoverage(boundary Boundary, pkg Package, result *Result) {
	if boundary.LegacyRows {
		return
	}
	coveragePaths := map[string]bool{}
	for _, path := range pkg.CoveragePaths {
		coveragePaths[path] = true
	}
	acceptedGaps := pkg.AcceptedGaps
	if acceptedGaps == nil {
		acceptedGaps = map[string]bool{}
	}
	for path, candidateDisposition := range boundary.CandidatePaths {
		disposition := boundary.Dispositions[path]
		if disposition == "" {
			disposition = candidateDisposition
		}
		if disposition == "" {
			result.Errors = append(result.Errors, fmt.Sprintf("repository-universe candidate path %s has no disposition", path))
			continue
		}
		if !validBoundaryDisposition(disposition) {
			result.Errors = append(result.Errors, fmt.Sprintf("repository-universe candidate path %s has invalid disposition %s", path, disposition))
			continue
		}
	}
	for path := range boundary.IncludedPaths {
		disposition := boundary.Dispositions[path]
		if disposition == "" {
			disposition = boundary.CandidatePaths[path]
		}
		if disposition == "" {
			result.Errors = append(result.Errors, fmt.Sprintf("repository-universe included path %s has no disposition", path))
			continue
		}
		if !validBoundaryDisposition(disposition) {
			result.Errors = append(result.Errors, fmt.Sprintf("repository-universe included path %s has invalid disposition %s", path, disposition))
			continue
		}
		if includedDispositionRequiresCoverage(disposition) && !coveragePaths[path] && !acceptedGaps[path] {
			result.Errors = append(result.Errors, fmt.Sprintf("repository-universe included path %s has no coverage row or accepted gap", path))
		}
	}
	for path := range boundary.ExcludedPaths {
		disposition := boundary.Dispositions[path]
		if disposition == "" {
			disposition = boundary.CandidatePaths[path]
		}
		if disposition == "" {
			result.Errors = append(result.Errors, fmt.Sprintf("repository-universe excluded path %s has no disposition", path))
			continue
		}
		if !validBoundaryDisposition(disposition) {
			result.Errors = append(result.Errors, fmt.Sprintf("repository-universe excluded path %s has invalid disposition %s", path, disposition))
			continue
		}
		if disposition != "excluded" {
			result.Errors = append(result.Errors, fmt.Sprintf("repository-universe excluded path %s must have excluded disposition", path))
			continue
		}
		if coveragePaths[path] {
			result.Errors = append(result.Errors, fmt.Sprintf("excluded path %s must not appear in coverage.json", path))
		}
	}
}

func acceptedGapPaths(paths rt.Paths) map[string]bool {
	accepted := map[string]bool{}
	raw, err := readJSONFile(filepath.Join(paths.RuntimeDir, "workbench", "coverage-ledger.json"), "coverage-ledger.json")
	if err != nil {
		return accepted
	}
	obj, ok := raw.(map[string]any)
	if !ok {
		return accepted
	}
	gaps, ok := obj["open_gaps"].([]any)
	if !ok {
		return accepted
	}
	for _, gap := range gaps {
		gapObj, ok := gap.(map[string]any)
		if !ok {
			continue
		}
		status := normalizedString(gapObj["status"])
		reason := normalizedString(gapObj["reason"])
		if blockedGapStatusOrReason(status) || blockedGapStatusOrReason(reason) {
			continue
		}
		path := normalizedString(gapObj["path"])
		if path != "" {
			accepted[path] = true
		}
		for _, item := range normalizedStringSlice(gapObj["paths"]) {
			accepted[item] = true
		}
	}
	return accepted
}

func includedDispositionRequiresCoverage(disposition string) bool {
	switch disposition {
	case "deep_read", "sampled", "inventory_only":
		return true
	default:
		return false
	}
}

func validBoundaryDisposition(disposition string) bool {
	switch disposition {
	case "deep_read", "sampled", "inventory_only", "excluded", "blocked":
		return true
	default:
		return false
	}
}

func blockedGapStatusOrReason(value string) bool {
	switch value {
	case "blocked", "unknown", "subagent_blocked", "critical_open_gap":
		return true
	default:
		return false
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
	normalized := normalizedEvidenceObject(row)
	contentHash := normalizedString(row["content_hash"])
	if contentHash == "" {
		contentHash = hashNormalizedObject(normalized)
	}
	return EvidenceRow{
		ID:          id,
		SourceKind:  stringFromMap(normalized, "source_kind"),
		SourcePath:  stringFromMap(normalized, "source_path"),
		CommitSHA:   stringFromMap(normalized, "commit_sha"),
		Span:        stringFromMap(normalized, "span"),
		Extractor:   stringFromMap(normalized, "extractor"),
		ContentHash: contentHash,
		Attrs:       objectMap(row["attrs"]),
	}
}

func normalizedEvidenceObject(row map[string]any) map[string]any {
	normalized := make(map[string]any, len(row))
	for key, value := range row {
		normalized[key] = normalizeEvidenceValue(key, value)
	}
	return normalized
}

func normalizeEvidenceValue(key string, value any) any {
	switch typed := value.(type) {
	case string:
		if isEvidenceStringField(key) || isPathField(key) {
			return normalizedString(typed)
		}
		return typed
	case []any:
		values := make([]any, 0, len(typed))
		for _, item := range typed {
			values = append(values, normalizeEvidenceValue(key, item))
		}
		return values
	case map[string]any:
		values := make(map[string]any, len(typed))
		for childKey, item := range typed {
			values[childKey] = normalizeEvidenceValue(childKey, item)
		}
		return values
	default:
		return value
	}
}

func isEvidenceStringField(key string) bool {
	switch key {
	case "source_kind", "source_path", "commit_sha", "span", "extractor":
		return true
	default:
		return false
	}
}

func isPathField(key string) bool {
	return key == "path" || strings.HasSuffix(key, "_path") || strings.HasSuffix(key, "_paths")
}

func stringFromMap(values map[string]any, key string) string {
	text, _ := values[key].(string)
	return text
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

func intFromValue(value any) int {
	switch typed := value.(type) {
	case float64:
		return int(typed)
	case int:
		return typed
	default:
		return 0
	}
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
