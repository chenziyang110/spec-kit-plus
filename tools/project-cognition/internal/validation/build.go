package validation

import (
	"context"
	"database/sql"
	"errors"
	"os"
	"path/filepath"
	"strings"

	rt "github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/runtime"
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
	st, err := store.Open(paths)
	if err != nil {
		payload.Errors = append(payload.Errors, err.Error())
	} else {
		defer st.Close()
		meta, err := st.Metadata(context.Background())
		if err != nil {
			payload.Errors = append(payload.Errors, err.Error())
		} else {
			payload.Details["metadata"] = meta
			payload.Details["query_smoke_test"] = "ok"
		}
	}
	payload.Errors = append(payload.Errors, validateGraphStorePaths(paths)...)
	payload.Errors = append(payload.Errors, validateCoverageLedger(paths, "build")...)
	if len(payload.Errors) > 0 {
		payload.Status = "blocked"
		payload.Readiness = "blocked"
	}
	return payload
}

func validateGraphStorePaths(paths rt.Paths) []string {
	db, err := sql.Open("sqlite", paths.DatabasePath)
	if err != nil {
		return []string{err.Error()}
	}
	defer db.Close()
	if _, err := db.Exec("SELECT 1"); err != nil {
		return []string{err.Error()}
	}
	rows, err := db.Query("SELECT name FROM sqlite_master WHERE type='table' AND name IN ('path_index', 'nodes', 'evidence')")
	if err != nil {
		return []string{err.Error()}
	}
	tableNames := map[string]bool{}
	for rows.Next() {
		var name string
		if err := rows.Scan(&name); err != nil {
			_ = rows.Close()
			return []string{err.Error()}
		}
		tableNames[name] = true
	}
	if err := rows.Close(); err != nil {
		return []string{err.Error()}
	}
	checks := []struct {
		table  string
		column string
	}{
		{table: "path_index", column: "path"},
		{table: "nodes", column: "path"},
		{table: "evidence", column: "source_path"},
	}
	for _, check := range checks {
		if !tableNames[check.table] {
			continue
		}
		rows, err := db.Query("SELECT " + check.column + " FROM " + check.table)
		if err != nil {
			return []string{err.Error()}
		}
		for rows.Next() {
			var raw sql.NullString
			if err := rows.Scan(&raw); err != nil {
				_ = rows.Close()
				return []string{err.Error()}
			}
			if raw.Valid && strings.HasPrefix(filepath.ToSlash(strings.TrimSpace(raw.String)), ".specify/") {
				_ = rows.Close()
				return []string{".specify/** must not enter project cognition graph store"}
			}
		}
		if err := rows.Close(); err != nil {
			return []string{err.Error()}
		}
	}
	return nil
}
