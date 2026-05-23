package validation

import (
	"context"
	"database/sql"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strings"

	rt "github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/runtime"
	"github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/runtimegate"
	"github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/scanartifacts"
	"github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/store"
)

func ValidateBuild(paths rt.Paths) GatePayload {
	required := []string{
		".specify/project-cognition/workbench/capability-ledger.json",
		".specify/project-cognition/workbench/control-ledger.json",
		".specify/project-cognition/workbench/worker-results",
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
	for _, rel := range required {
		full := filepath.Join(paths.Root, filepath.FromSlash(rel))
		if _, err := os.Stat(full); err != nil {
			payload.Errors = append(payload.Errors, "missing "+rel)
			continue
		}
		if filepath.Ext(full) == ".json" {
			if err := validateJSONFile(full); err != nil {
				payload.Errors = append(payload.Errors, rel+": "+err.Error())
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
	agreement := runtimegate.Check(paths)
	if agreement.Status == "blocked" {
		payload.Errors = append(payload.Errors, agreement.Errors...)
		if agreement.RecoveryAction != "" {
			payload.Details["recovery_action"] = agreement.RecoveryAction
		}
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
	}
	reconciliationDetails, reconciliationErrors := validateIdentityReconciliation(paths)
	for key, value := range reconciliationDetails {
		payload.Details[key] = value
	}
	payload.Errors = append(payload.Errors, reconciliationErrors...)
	graphDetails, graphErrors := validateGraphStore(paths, status, agreement)
	for key, value := range graphDetails {
		payload.Details[key] = value
	}
	payload.Errors = append(payload.Errors, graphErrors...)
	payload.Errors = append(payload.Errors, validateCoverageLedger(paths, "build")...)
	if len(payload.Errors) > 0 {
		payload.Status = "blocked"
		payload.Readiness = "blocked"
	}
	return payload
}

func validateIdentityReconciliation(paths rt.Paths) (map[string]any, []string) {
	details := map[string]any{
		"identity_reconciliation": "not_run",
		"scan_artifact_counts":    identityCounts(scanartifacts.IdentitySet{}),
		"db_counts":               identitySnapshotCounts(store.IdentitySnapshot{}),
		"rejections":              []store.RowDecision{},
		"merge_records":           []store.MergeRecord{},
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
	errors = append(errors, compareIdentityCategory("evidence", pkg.Identities.Evidence, snapshot.Evidence, snapshot)...)
	errors = append(errors, compareIdentityCategory("node", pkg.Identities.Nodes, snapshot.Nodes, snapshot)...)
	errors = append(errors, compareIdentityCategory("edge", pkg.Identities.Edges, snapshot.Edges, snapshot)...)
	errors = append(errors, compareIdentityCategory("observation", pkg.Identities.Observations, snapshot.Observations, snapshot)...)
	errors = append(errors, compareIdentityCategory("coverage_path", pkg.Identities.CoveragePaths, snapshot.CoveragePaths, snapshot)...)
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

func compareIdentityCategory(category string, expected map[string]bool, actual map[string]bool, snapshot store.IdentitySnapshot) []string {
	missing := []string{}
	unexpected := []string{}
	for identity := range expected {
		if !actual[identity] && !identityCoveredByDecision(category, identity, snapshot) {
			missing = append(missing, identity)
		}
	}
	for identity := range actual {
		if !expected[identity] {
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
	return errors
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

func validateGraphStore(paths rt.Paths, status rt.Status, agreement runtimegate.Agreement) (map[string]any, []string) {
	details := map[string]any{}
	errors := []string{}
	info, err := os.Stat(paths.DatabasePath)
	if err != nil {
		return details, []string{"missing .specify/project-cognition/project-cognition.db"}
	}
	if info.Size() == 0 {
		return details, []string{"project-cognition.db must not be empty"}
	}
	db, err := sql.Open("sqlite", paths.DatabasePath)
	if err != nil {
		return details, []string{err.Error()}
	}
	defer db.Close()
	if _, err := db.Exec("SELECT 1"); err != nil {
		return details, []string{fmt.Sprintf("project-cognition.db is not query ready: %v", err)}
	}

	tableNames, err := sqliteTableNames(db)
	if err != nil {
		return details, []string{err.Error()}
	}
	missing := []string{}
	for _, table := range store.RequiredTables() {
		if !tableNames[table] {
			missing = append(missing, table)
		}
	}
	if len(missing) > 0 {
		errors = append(errors, "project-cognition.db missing required query tables: "+strings.Join(missing, ", "))
		return details, errors
	}
	missingColumns, err := missingRequiredColumns(db)
	if err != nil {
		errors = append(errors, err.Error())
		return details, errors
	}
	if len(missingColumns) > 0 {
		errors = append(errors, "project-cognition.db missing required query columns: "+strings.Join(missingColumns, ", "))
		return details, errors
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
		if nodeCount == 0 {
			errors = append(errors, "active generation has no nodes")
		}
		if pathCount == 0 {
			errors = append(errors, "active_generation_has_no_path_index_rows")
		}
		if evidenceCount == 0 {
			errors = append(errors, "active generation has no evidence rows")
		}
		if len(errors) == 0 {
			details["query_smoke_test"] = "ok"
		}
	}

	checks := []struct {
		table  string
		column string
	}{
		{table: "path_index", column: "path"},
		{table: "evidence", column: "source_path"},
		{table: "symbol_index", column: "path"},
		{table: "entrypoint_index", column: "path"},
		{table: "test_index", column: "test_path"},
	}
	for _, check := range checks {
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
			if raw.Valid && strings.HasPrefix(filepath.ToSlash(strings.TrimSpace(raw.String)), ".specify/") {
				_ = rows.Close()
				errors = append(errors, ".specify/** must not enter project cognition graph store")
				break
			}
		}
		if err := rows.Close(); err != nil {
			errors = append(errors, err.Error())
		}
	}
	return details, errors
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
