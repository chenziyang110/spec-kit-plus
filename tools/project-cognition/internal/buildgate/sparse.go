package buildgate

import (
	"context"
	"database/sql"
	"fmt"
	"sort"

	rt "github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/runtime"
	"github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/scanartifacts"
)

type SparseResult struct {
	Errors   []string
	Warnings []string
	Details  map[string]any
}

func ValidateSparsePathIndex(paths rt.Paths, db *sql.DB, generationID string) SparseResult {
	result := SparseResult{
		Errors:   []string{},
		Warnings: []string{},
		Details:  map[string]any{},
	}
	requirements, requirementErrors := scanartifacts.LoadPathIndexRequirements(paths)
	if len(requirementErrors) > 0 {
		result.Errors = append(result.Errors, requirementErrors...)
		return result
	}
	indexedPaths, err := activePathIndexPaths(context.Background(), db, generationID)
	if err != nil {
		result.Errors = append(result.Errors, err.Error())
		return result
	}
	indexedSet := stringSet(indexedPaths)
	indexRequiredSet := stringSet(requirements.IndexRequiredPaths)
	indexedRequiredCount := 0
	for _, path := range indexedPaths {
		if indexRequiredSet[path] {
			indexedRequiredCount++
		}
	}
	ratio := 1.0
	if len(requirements.IndexRequiredPaths) > 0 {
		ratio = float64(indexedRequiredCount) / float64(len(requirements.IndexRequiredPaths))
	}
	result.Details["included_count"] = len(requirements.IncludedPaths)
	result.Details["index_required_count"] = len(requirements.IndexRequiredPaths)
	result.Details["path_index_to_included_ratio"] = fmt.Sprintf("%.2f", ratio)
	result.Details["canonical_node_path_count"] = requirements.CanonicalNodePathCount
	result.Details["compatibility_derived_node_path_count"] = requirements.CompatibilityDerivedPathCount
	result.Details["accepted_nonblocking_gap_paths"] = requirements.AcceptedNonblockingGapPaths

	for _, path := range requirements.CriticalIndexRequiredPaths {
		if !indexedSet[path] {
			result.Errors = append(result.Errors, "critical_missing_path_index: "+path)
		}
	}
	for _, path := range requirements.ImportantIndexRequiredPaths {
		if !indexedSet[path] {
			result.Errors = append(result.Errors, "important_missing_path_index: "+path)
		}
	}
	switch {
	case ratio < 0.70:
		result.Errors = append(result.Errors, fmt.Sprintf("path_index_to_included_ratio %.2f is below hard threshold 0.70", ratio))
	case ratio < 0.90:
		result.Warnings = append(result.Warnings, fmt.Sprintf("path_index_to_included_ratio %.2f is below warning threshold 0.90", ratio))
	}
	sort.Strings(result.Errors)
	sort.Strings(result.Warnings)
	return result
}

func activePathIndexPaths(ctx context.Context, db *sql.DB, generationID string) ([]string, error) {
	rows, err := db.QueryContext(ctx, `SELECT DISTINCT path FROM path_index WHERE generation_id = ?`, generationID)
	if err != nil {
		return nil, fmt.Errorf("read active path_index paths: %w", err)
	}
	defer rows.Close()
	paths := []string{}
	for rows.Next() {
		var path string
		if err := rows.Scan(&path); err != nil {
			return nil, fmt.Errorf("scan active path_index path: %w", err)
		}
		paths = append(paths, path)
	}
	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("read active path_index paths: %w", err)
	}
	sort.Strings(paths)
	return paths, nil
}

func stringSet(values []string) map[string]bool {
	set := map[string]bool{}
	for _, value := range values {
		set[value] = true
	}
	return set
}
