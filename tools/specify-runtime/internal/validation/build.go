package validation

import (
	"context"
	"database/sql"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strings"

	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/buildgate"
	rt "github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/runtime"
	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/runtimegate"
	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/scanartifacts"
	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/store"
)

func ValidateBuild(paths rt.Paths) GatePayload {
	required := []string{
		".specify/project-cognition/workbench/capability-ledger.json",
		".specify/project-cognition/workbench/control-ledger.json",
		".specify/project-cognition/project-cognition.db",
		".specify/project-cognition/status.json",
	}
	payload := GatePayload{
		Status:       "ok",
		Gate:         "build_acceptance",
		Readiness:    "query_ready",
		Errors:       []string{},
		Warnings:     []string{},
		CheckedPaths: required,
		Details:      map[string]any{},
	}
	requiredErrors := []string{}
	for _, rel := range required {
		full := filepath.Join(paths.Root, filepath.FromSlash(rel))
		if _, err := os.Stat(full); err != nil {
			requiredErrors = append(requiredErrors, "missing "+rel)
			continue
		}
		if filepath.Ext(full) == ".json" {
			if err := validateJSONFile(full); err != nil {
				requiredErrors = append(requiredErrors, rel+": "+err.Error())
			}
		}
	}
	status, err := rt.ReadStatus(paths)
	if errors.Is(err, rt.ErrUnsupportedLegacy) {
		payload.Errors = append(payload.Errors, "unsupported legacy runtime")
	} else if err != nil {
		payload.Errors = append(payload.Errors, err.Error())
	} else {
		payload.Details["runtime_format"] = status.RuntimeFormat
		payload.Details["runtime_schema"] = status.RuntimeSchema
		payload.Details["freshness"] = status.Freshness
	}
	greenfieldEmpty := false
	agreement := runtimegate.Check(paths)
	if agreement.Status == "blocked" && agreement.CauseCode != runtimegate.CauseUpdateFinalizationPending {
		payload.Errors = append(payload.Errors, agreement.Errors...)
		if agreement.RecoveryAction != "" {
			payload.Details["recovery_action"] = agreement.RecoveryAction
		}
	} else if agreement.CauseCode == runtimegate.CauseUpdateFinalizationPending {
		payload.Details["runtime_agreement"] = "pending_receipt_bound_finalization"
	}
	st, err := store.OpenExisting(paths)
	if err != nil {
		payload.Errors = append(payload.Errors, err.Error())
	} else {
		defer st.Close()
		meta, err := st.Metadata(context.Background())
		if err != nil {
			payload.Errors = append(payload.Errors, err.Error())
		} else {
			payload.Details["metadata"] = meta
		}
		activeGenerationID, err := activeGenerationID(st.DB())
		if err == nil {
			greenfieldEmpty = isGreenfieldEmptyBaseline(status, st.DB(), activeGenerationID)
		}
	}
	payload.Errors = append(payload.Errors, filterRequiredBuildErrors(requiredErrors, greenfieldEmpty)...)
	reconciliationDetails, reconciliationErrors := validateIdentityReconciliation(paths)
	for key, value := range reconciliationDetails {
		payload.Details[key] = value
	}
	payload.Errors = append(payload.Errors, reconciliationErrors...)
	graphDetails, graphErrors, graphWarnings := validateGraphStore(paths, status, agreement)
	for key, value := range graphDetails {
		payload.Details[key] = value
	}
	payload.Errors = append(payload.Errors, graphErrors...)
	payload.Warnings = append(payload.Warnings, graphWarnings...)
	if !greenfieldEmpty {
		payload.Errors = append(payload.Errors, validateCoverageLedger(paths, "build")...)
	}
	if len(payload.Errors) > 0 {
		payload.Status = "blocked"
		payload.Readiness = "blocked"
	}
	return payload
}

func filterRequiredBuildErrors(errors []string, greenfieldEmpty bool) []string {
	if !greenfieldEmpty {
		return errors
	}
	filtered := []string{}
	for _, err := range errors {
		if err == "missing .specify/project-cognition/workbench/capability-ledger.json" ||
			err == "missing .specify/project-cognition/workbench/control-ledger.json" {
			continue
		}
		filtered = append(filtered, err)
	}
	return filtered
}

func validateIdentityReconciliation(paths rt.Paths) (map[string]any, []string) {
	details := map[string]any{
		"identity_reconciliation":          "not_run",
		"scan_artifact_counts":             identityCounts(scanartifacts.IdentitySet{}),
		"db_counts":                        identitySnapshotCounts(store.IdentitySnapshot{}),
		"identity_diffs":                   map[string]identityCategoryDiff{},
		"identity_mismatch_count":          0,
		"identity_mismatch_categories":     []string{},
		"identity_repairability":           "not_applicable",
		"identity_recommended_next_action": "none",
		"rejections":                       []store.RowDecision{},
		"merge_records":                    []store.MergeRecord{},
	}
	errors := []string{}
	pkg, result := scanartifacts.Load(paths, scanartifacts.ValidateOptions{RequireStatusJSON: false})
	details["scan_artifact_counts"] = identityCounts(pkg.Identities)
	presentCount := scanArtifactPresentCount(paths)
	if presentCount == 0 {
		details["identity_reconciliation"] = "skipped_no_scan_package"
		return details, errors
	}
	if result.Status != "ok" {
		details["identity_reconciliation"] = "skipped_invalid_scan_package"
		return details, result.Errors
	}
	st, err := store.OpenExisting(paths)
	if err != nil {
		return details, []string{err.Error()}
	}
	defer st.Close()
	snapshot, err := st.ActiveIdentitySnapshot(context.Background())
	if err != nil {
		return details, []string{err.Error()}
	}
	details["db_counts"] = identitySnapshotCounts(snapshot)
	details["rejections"] = snapshot.Rejections
	details["merge_records"] = snapshot.MergeRecords
	identityDiffs := map[string]identityCategoryDiff{}
	for _, category := range []struct {
		name     string
		expected map[string]bool
		actual   map[string]bool
	}{
		{name: "evidence", expected: pkg.Identities.Evidence, actual: snapshot.Evidence},
		{name: "node", expected: pkg.Identities.Nodes, actual: snapshot.Nodes},
		{name: "edge", expected: pkg.Identities.Edges, actual: snapshot.Edges},
		{name: "observation", expected: pkg.Identities.Observations, actual: snapshot.Observations},
		{name: "coverage_path", expected: pkg.Identities.CoveragePaths, actual: snapshot.CoveragePaths},
	} {
		diff, categoryErrors := compareIdentityCategoryDetailed(category.name, category.expected, category.actual, snapshot)
		identityDiffs[category.name] = diff
		errors = append(errors, categoryErrors...)
	}
	details["identity_diffs"] = identityDiffs
	details["identity_mismatch_count"] = identityMismatchCount(identityDiffs)
	details["identity_mismatch_categories"] = identityMismatchCategories(identityDiffs)
	repairability := classifyIdentityRepairability(identityDiffs)
	details["identity_repairability"] = repairability
	details["identity_recommended_next_action"] = identityRecommendedNextAction(repairability)
	if len(errors) > 0 {
		details["identity_reconciliation"] = "blocked"
	} else {
		details["identity_reconciliation"] = "ok"
	}
	return details, errors
}

func scanArtifactPresentCount(paths rt.Paths) int {
	count := 0
	for _, rel := range scanArtifactAnchorPaths() {
		if _, err := os.Stat(filepath.Join(paths.Root, filepath.FromSlash(rel))); err == nil {
			count++
		}
	}
	return count
}

func scanArtifactAnchorPaths() []string {
	return []string{
		".specify/project-cognition/evidence",
		".specify/project-cognition/provisional/nodes.json",
		".specify/project-cognition/provisional/edges.json",
		".specify/project-cognition/provisional/observations.json",
		".specify/project-cognition/coverage.json",
		".specify/project-cognition/workbench/map-scan.md",
		".specify/project-cognition/workbench/scan-packets",
		".specify/project-cognition/workbench/worker-results",
		".specify/project-cognition/workbench/map-state.md",
		".specify/project-cognition/workbench/repository-universe.json",
	}
}

func identityCounts(identities scanartifacts.IdentitySet) map[string]int {
	return map[string]int{
		"evidence":       len(identities.Evidence),
		"nodes":          len(identities.Nodes),
		"edges":          len(identities.Edges),
		"observations":   len(identities.Observations),
		"coverage_paths": len(identities.CoveragePaths),
	}
}

func identitySnapshotCounts(snapshot store.IdentitySnapshot) map[string]int {
	return map[string]int{
		"evidence":       len(snapshot.Evidence),
		"nodes":          len(snapshot.Nodes),
		"edges":          len(snapshot.Edges),
		"observations":   len(snapshot.Observations),
		"coverage_paths": len(snapshot.CoveragePaths),
	}
}

type identityCategoryDiff struct {
	MissingScan   []string `json:"missing_scan"`
	UnexpectedDB  []string `json:"unexpected_db"`
	MismatchCount int      `json:"mismatch_count"`
}

func compareIdentityCategory(category string, expected map[string]bool, actual map[string]bool, snapshot store.IdentitySnapshot) []string {
	_, errors := compareIdentityCategoryDetailed(category, expected, actual, snapshot)
	return errors
}

func compareIdentityCategoryDetailed(category string, expected map[string]bool, actual map[string]bool, snapshot store.IdentitySnapshot) (identityCategoryDiff, []string) {
	missing := []string{}
	unexpected := []string{}
	for identity := range expected {
		if !actual[identity] && !identityCoveredByDecision(category, identity, snapshot) {
			missing = append(missing, identity)
		}
	}
	for identity := range actual {
		if !expected[identity] && !identityAllowedAsWorkflowUpdate(category, identity, snapshot) {
			unexpected = append(unexpected, identity)
		}
	}
	sort.Strings(missing)
	sort.Strings(unexpected)
	errors := []string{}
	if len(missing) > 0 {
		errors = append(errors, "missing scan "+identityErrorNoun(category)+" identities: "+strings.Join(missing, ", "))
	}
	if len(unexpected) > 0 {
		errors = append(errors, "unexpected DB "+identityErrorNoun(category)+" identities: "+strings.Join(unexpected, ", "))
	}
	return identityCategoryDiff{
		MissingScan:   missing,
		UnexpectedDB:  unexpected,
		MismatchCount: len(missing) + len(unexpected),
	}, errors
}

func identityMismatchCount(diffs map[string]identityCategoryDiff) int {
	total := 0
	for _, diff := range diffs {
		total += diff.MismatchCount
	}
	return total
}

func identityMismatchCategories(diffs map[string]identityCategoryDiff) []string {
	categories := []string{}
	for category, diff := range diffs {
		if diff.MismatchCount > 0 {
			categories = append(categories, category)
		}
	}
	sort.Strings(categories)
	return categories
}

func classifyIdentityRepairability(diffs map[string]identityCategoryDiff) string {
	total := identityMismatchCount(diffs)
	if total == 0 {
		return "not_needed"
	}
	categories := identityMismatchCategories(diffs)
	if total <= 10 && len(categories) == 1 && categories[0] == "coverage_path" {
		return "bounded_path_repair"
	}
	if total <= 10 && identityCategoriesArePathLed(categories) {
		return "bounded_path_identity_review"
	}
	return "manual_identity_review"
}

func identityCategoriesArePathLed(categories []string) bool {
	for _, category := range categories {
		if category != "coverage_path" && category != "evidence" {
			return false
		}
	}
	return len(categories) > 0
}

func identityRecommendedNextAction(repairability string) string {
	switch repairability {
	case "not_needed":
		return "none"
	case "bounded_path_repair", "bounded_path_identity_review":
		return "repair_identity_reconciliation"
	default:
		return "review_project_cognition_update"
	}
}

func identityAllowedAsWorkflowUpdate(category string, identity string, snapshot store.IdentitySnapshot) bool {
	switch category {
	case "evidence":
		return snapshot.WorkflowUpdateEvidence[identity]
	case "node":
		return snapshot.WorkflowUpdateNodes[identity]
	case "coverage_path":
		return snapshot.WorkflowUpdateCoveragePaths[identity]
	default:
		return false
	}
}

func identityCoveredByDecision(category string, identity string, snapshot store.IdentitySnapshot) bool {
	for _, rejection := range snapshot.Rejections {
		if sameIdentityCategory(rejection.Category, category) && rejection.Identity == identity {
			return true
		}
	}
	for _, record := range snapshot.MergeRecords {
		if sameIdentityCategory(record.Category, category) && record.SourceIdentity == identity {
			return true
		}
	}
	return false
}

func sameIdentityCategory(actual string, expected string) bool {
	return canonicalIdentityCategory(actual) == canonicalIdentityCategory(expected)
}

func canonicalIdentityCategory(category string) string {
	switch strings.TrimSuffix(strings.TrimSpace(category), "s") {
	case "coverage", "coverage_path":
		return "coverage_path"
	default:
		return strings.TrimSuffix(strings.TrimSpace(category), "s")
	}
}

func identityErrorNoun(category string) string {
	switch category {
	case "coverage_path":
		return "coverage path"
	default:
		return category
	}
}

func validateGraphStore(paths rt.Paths, status rt.Status, agreement runtimegate.Agreement) (map[string]any, []string, []string) {
	details := map[string]any{}
	errors := []string{}
	warnings := []string{}
	info, err := os.Stat(paths.DatabasePath)
	if err != nil {
		return details, []string{"missing .specify/project-cognition/project-cognition.db"}, warnings
	}
	if info.Size() == 0 {
		return details, []string{"project-cognition.db must not be empty"}, warnings
	}
	db, err := sql.Open("sqlite", paths.DatabasePath)
	if err != nil {
		return details, []string{err.Error()}, warnings
	}
	defer db.Close()
	if _, err := db.Exec("SELECT 1"); err != nil {
		return details, []string{fmt.Sprintf("project-cognition.db is not query ready: %v", err)}, warnings
	}

	tableNames, err := sqliteTableNames(db)
	if err != nil {
		return details, []string{err.Error()}, warnings
	}
	missing := []string{}
	for _, table := range store.RequiredTables() {
		if !tableNames[table] {
			missing = append(missing, table)
		}
	}
	if len(missing) > 0 {
		errors = append(errors, "project-cognition.db missing required query tables: "+strings.Join(missing, ", "))
		return details, errors, warnings
	}
	missingColumns, err := missingRequiredColumns(db)
	if err != nil {
		errors = append(errors, err.Error())
		return details, errors, warnings
	}
	if len(missingColumns) > 0 {
		errors = append(errors, "project-cognition.db missing required query columns: "+strings.Join(missingColumns, ", "))
		return details, errors, warnings
	}

	schemaVersion, err := metadataScalar(db, "schema_version")
	if err != nil {
		errors = append(errors, err.Error())
	} else {
		details["schema_version"] = schemaVersion
		if schemaVersion != fmt.Sprint(store.SchemaVersion) {
			errors = append(errors, fmt.Sprintf("project-cognition.db schema_version %s is not supported; expected %d", schemaVersion, store.SchemaVersion))
		}
	}

	activeGenerationID, err := activeGenerationID(db)
	if err != nil {
		errors = append(errors, err.Error())
	} else if activeGenerationID == "" {
		errors = append(errors, "project-cognition.db has no active generation")
	} else {
		details["active_generation_id"] = activeGenerationID
		if shouldReportGraphGenerationMismatch(status, activeGenerationID, agreement) {
			errors = append(errors, fmt.Sprintf("status.json active_generation_id %s does not match DB active generation %s", status.ActiveGenerationID, activeGenerationID))
		}
		nodeCount, err := countGenerationRows(db, "nodes", activeGenerationID)
		if err != nil {
			errors = append(errors, err.Error())
		}
		pathCount, err := countGenerationRows(db, "path_index", activeGenerationID)
		if err != nil {
			errors = append(errors, err.Error())
		}
		evidenceCount, err := countGenerationRows(db, "evidence", activeGenerationID)
		if err != nil {
			errors = append(errors, err.Error())
		}
		details["node_count"] = nodeCount
		details["path_index_count"] = pathCount
		details["evidence_count"] = evidenceCount
		greenfieldEmpty := isGreenfieldEmptyBaseline(status, db, activeGenerationID)
		details["baseline_kind"] = status.BaselineKind
		aliasDetails, aliasErrors, err := validateAliasIndex(db, activeGenerationID, greenfieldEmpty)
		if err != nil {
			errors = append(errors, err.Error())
		}
		for key, value := range aliasDetails {
			details[key] = value
		}
		errors = append(errors, aliasErrors...)
		if nodeCount == 0 && !greenfieldEmpty {
			errors = append(errors, "active generation has no nodes")
		}
		if pathCount == 0 && !greenfieldEmpty {
			errors = append(errors, "active_generation_has_no_path_index_rows")
		}
		if pathCount > 0 && sparsePathIndexGateAvailable(paths) {
			sparse := buildgate.ValidateSparsePathIndex(paths, db, activeGenerationID)
			for key, value := range sparse.Details {
				details[key] = value
			}
			errors = append(errors, sparse.Errors...)
			warnings = append(warnings, sparse.Warnings...)
		}
		if evidenceCount == 0 && !greenfieldEmpty {
			errors = append(errors, "active generation has no evidence rows")
		}
		if len(errors) == 0 {
			details["query_smoke_test"] = "ok"
		}
	}

	excludedPaths := excludedBoundaryPaths(paths)
	for _, check := range graphPathTableChecks() {
		rows, err := db.Query("SELECT " + check.column + " FROM " + check.table)
		if err != nil {
			errors = append(errors, err.Error())
			continue
		}
		for rows.Next() {
			var raw sql.NullString
			if err := rows.Scan(&raw); err != nil {
				_ = rows.Close()
				errors = append(errors, err.Error())
				break
			}
			if raw.Valid {
				normalized := canonicalGraphPath(raw.String)
				if strings.HasPrefix(normalized, ".specify/") {
					_ = rows.Close()
					errors = append(errors, ".specify/** must not enter project cognition graph store")
					break
				}
				if excludedPaths[normalized] {
					_ = rows.Close()
					errors = append(errors, fmt.Sprintf("excluded boundary path %s must not enter project cognition graph store", normalized))
					break
				}
			}
		}
		if err := rows.Close(); err != nil {
			errors = append(errors, err.Error())
		}
	}
	return details, errors, warnings
}

func validateAliasIndex(db *sql.DB, generationID string, greenfieldEmpty bool) (map[string]any, []string, error) {
	details := map[string]any{}
	errors := []string{}
	aliasCount, err := countGenerationRows(db, "alias_index", generationID)
	if err != nil {
		return details, errors, err
	}
	details["alias_index_count"] = aliasCount
	if greenfieldEmpty {
		return details, errors, nil
	}
	if aliasCount == 0 {
		errors = append(errors, "active_generation_has_no_alias_rows")
	}

	missingAliasNodeIDs, err := stringColumnRows(db, `
SELECT n.id FROM nodes n WHERE n.generation_id = ? AND NOT EXISTS (
  SELECT 1 FROM alias_index a
  WHERE a.generation_id = n.generation_id
    AND a.target_type = 'node'
    AND a.target_id = n.id
    AND TRIM(a.normalized_alias) <> ''
) ORDER BY n.id`, generationID)
	if err != nil {
		return details, errors, err
	}
	for _, nodeID := range missingAliasNodeIDs {
		errors = append(errors, "active_generation_node_missing_aliases:"+nodeID)
	}

	orphanTargetIDs, err := stringColumnRows(db, `
SELECT DISTINCT a.target_id
FROM alias_index a
LEFT JOIN nodes n ON n.generation_id = a.generation_id AND n.id = a.target_id
WHERE a.generation_id = ? AND a.target_type = 'node' AND n.id IS NULL
ORDER BY a.target_id`, generationID)
	if err != nil {
		return details, errors, err
	}
	for _, targetID := range orphanTargetIDs {
		errors = append(errors, "alias_index_orphan_target_id:"+targetID)
	}

	missingEvidenceIDs, err := stringColumnRows(db, `
SELECT DISTINCT a.evidence_id
FROM alias_index a
LEFT JOIN evidence e ON e.generation_id = a.generation_id AND e.id = a.evidence_id
WHERE a.generation_id = ? AND TRIM(a.evidence_id) <> '' AND e.id IS NULL
ORDER BY a.evidence_id`, generationID)
	if err != nil {
		return details, errors, err
	}
	for _, evidenceID := range missingEvidenceIDs {
		errors = append(errors, "alias_index_missing_evidence_id:"+evidenceID)
	}
	return details, errors, nil
}

func isGreenfieldEmptyBaseline(status rt.Status, db *sql.DB, activeGenerationID string) bool {
	if status.BaselineKind != rt.BaselineKindGreenfieldEmpty {
		return false
	}
	metaKind, err := metadataScalar(db, "baseline_kind")
	if err != nil || metaKind != rt.BaselineKindGreenfieldEmpty {
		return false
	}
	var generationKind string
	err = db.QueryRow("SELECT kind FROM generations WHERE id = ?", activeGenerationID).Scan(&generationKind)
	return err == nil && generationKind == rt.BaselineKindGreenfieldEmpty
}

func sparsePathIndexGateAvailable(paths rt.Paths) bool {
	_, err := os.Stat(filepath.Join(paths.RuntimeDir, "workbench", "repository-universe.json"))
	return err == nil
}

func excludedBoundaryPaths(paths rt.Paths) map[string]bool {
	boundaryPath := filepath.Join(paths.RuntimeDir, "workbench", "repository-universe.json")
	raw, err := os.ReadFile(boundaryPath)
	if err != nil {
		return map[string]bool{}
	}
	var obj map[string]any
	if err := json.Unmarshal(raw, &obj); err != nil {
		return map[string]bool{}
	}
	rawExcluded, ok := obj["excluded_paths"].([]any)
	if !ok {
		return map[string]bool{}
	}
	excluded := map[string]bool{}
	for _, entry := range rawExcluded {
		path := ""
		switch value := entry.(type) {
		case string:
			path = value
		case map[string]any:
			if rawPath, ok := value["path"].(string); ok {
				path = rawPath
			}
		}
		normalized := canonicalGraphPath(path)
		if normalized != "" {
			excluded[normalized] = true
		}
	}
	return excluded
}

func canonicalGraphPath(path string) string {
	normalized := filepath.ToSlash(strings.TrimSpace(path))
	for strings.HasPrefix(normalized, "./") {
		normalized = strings.TrimPrefix(normalized, "./")
	}
	return normalized
}

func graphPathTableChecks() []struct {
	table  string
	column string
} {
	return []struct {
		table  string
		column string
	}{
		{table: "path_index", column: "path"},
		{table: "evidence", column: "source_path"},
	}
}

func shouldReportGraphGenerationMismatch(status rt.Status, activeGenerationID string, agreement runtimegate.Agreement) bool {
	if status.ActiveGenerationID == "" || status.ActiveGenerationID == activeGenerationID {
		return false
	}
	return agreement.Status != "blocked" || agreement.StatusGenerationID != status.ActiveGenerationID || agreement.DBActiveGenerationID != activeGenerationID
}

func sqliteTableNames(db *sql.DB) (map[string]bool, error) {
	rows, err := db.Query("SELECT name FROM sqlite_master WHERE type='table'")
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	tableNames := map[string]bool{}
	for rows.Next() {
		var name string
		if err := rows.Scan(&name); err != nil {
			return nil, err
		}
		tableNames[name] = true
	}
	return tableNames, rows.Err()
}

func missingRequiredColumns(db *sql.DB) ([]string, error) {
	missing := []string{}
	for table, requiredColumns := range store.RequiredTableColumns() {
		columns, err := sqliteTableColumns(db, table)
		if err != nil {
			return nil, err
		}
		for _, column := range requiredColumns {
			if !columns[column] {
				missing = append(missing, table+"."+column)
			}
		}
	}
	sort.Strings(missing)
	return missing, nil
}

func sqliteTableColumns(db *sql.DB, table string) (map[string]bool, error) {
	rows, err := db.Query("PRAGMA table_info(" + table + ")")
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	columns := map[string]bool{}
	for rows.Next() {
		var cid int
		var name, typ string
		var notNull int
		var defaultValue sql.NullString
		var pk int
		if err := rows.Scan(&cid, &name, &typ, &notNull, &defaultValue, &pk); err != nil {
			return nil, err
		}
		columns[name] = true
	}
	return columns, rows.Err()
}

func metadataScalar(db *sql.DB, key string) (string, error) {
	var raw string
	err := db.QueryRow("SELECT value_json FROM metadata WHERE key = ?", key).Scan(&raw)
	if errors.Is(err, sql.ErrNoRows) {
		return "", fmt.Errorf("project-cognition.db metadata.%s is missing", key)
	}
	if err != nil {
		return "", fmt.Errorf("read project-cognition.db metadata.%s: %w", key, err)
	}
	return strings.Trim(strings.TrimSpace(raw), `"`), nil
}

func activeGenerationID(db *sql.DB) (string, error) {
	var id string
	err := db.QueryRow("SELECT id FROM generations WHERE state = 'active' ORDER BY sequence DESC, id DESC LIMIT 1").Scan(&id)
	if errors.Is(err, sql.ErrNoRows) {
		return "", nil
	}
	if err != nil {
		return "", fmt.Errorf("read active generation: %w", err)
	}
	return id, nil
}

func countGenerationRows(db *sql.DB, table string, generationID string) (int, error) {
	var count int
	err := db.QueryRow("SELECT COUNT(*) FROM "+table+" WHERE generation_id = ?", generationID).Scan(&count)
	if err != nil {
		return 0, fmt.Errorf("count %s rows: %w", table, err)
	}
	return count, nil
}

func stringColumnRows(db *sql.DB, query string, args ...any) ([]string, error) {
	rows, err := db.Query(query, args...)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	values := []string{}
	for rows.Next() {
		var value string
		if err := rows.Scan(&value); err != nil {
			return nil, err
		}
		values = append(values, value)
	}
	return values, rows.Err()
}
