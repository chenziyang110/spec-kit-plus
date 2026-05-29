package runtimegate

import (
	"context"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"strings"

	rt "github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/runtime"
	"github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/store"
)

const (
	graphStorePath      = ".specify/project-cognition/project-cognition.db"
	rebuildAction       = "run_map_scan_build"
	rewriteStatusAction = "rewrite_status_from_db_metadata"
)

type Agreement struct {
	Status                string   `json:"status"`
	Readiness             string   `json:"readiness"`
	Errors                []string `json:"errors"`
	Warnings              []string `json:"warnings"`
	RecoveryAction        string   `json:"recovery_action,omitempty"`
	StatusPath            string   `json:"status_path"`
	GraphStorePath        string   `json:"graph_store_path"`
	StatusGenerationID    string   `json:"status_generation_id,omitempty"`
	DBActiveGenerationID  string   `json:"db_active_generation_id,omitempty"`
	StatusBaselineKind    string   `json:"status_baseline_kind,omitempty"`
	DBBaselineKind        string   `json:"db_baseline_kind,omitempty"`
	DBGenerationKind      string   `json:"db_generation_kind,omitempty"`
	RecommendedNextAction string   `json:"recommended_next_action"`
}

func Check(paths rt.Paths) Agreement {
	agreement := baseAgreement(paths)
	status, err := rt.ReadStatus(paths)
	if errors.Is(err, rt.ErrUnsupportedLegacy) {
		payload := rt.UnsupportedLegacyPayload(paths)
		agreement.Readiness = rt.UnsupportedReadiness
		agreement.RecoveryAction = rebuildAction
		agreement.RecommendedNextAction = rebuildAction
		agreement.Errors = append(agreement.Errors, payload.ErrorCode+": "+payload.Errors[0])
		return agreement
	}
	if err != nil {
		agreement.Errors = append(agreement.Errors, fmt.Sprintf("read status: %v", err))
		return agreement
	}
	agreement.Readiness = status.Readiness
	agreement.GraphStorePath = normalizeGraphStorePath(status.GraphStorePath)
	agreement.StatusGenerationID = status.ActiveGenerationID
	agreement.StatusBaselineKind = status.BaselineKind

	st, err := store.OpenExisting(paths)
	if err != nil {
		agreement.Readiness = rt.BlockedReadiness
		agreement.RecommendedNextAction = rebuildAction
		agreement.Errors = append(agreement.Errors, fmt.Sprintf("open graph store: %v", err))
		return agreement
	}
	defer st.Close()

	activeGenerationID, err := st.ActiveGenerationID(context.Background())
	if err != nil {
		agreement.Readiness = rt.BlockedReadiness
		agreement.Errors = append(agreement.Errors, fmt.Sprintf("read DB active generation: %v", err))
		return agreement
	}
	agreement.DBActiveGenerationID = activeGenerationID
	if activeGenerationID == "" {
		agreement.Readiness = rt.BlockedReadiness
		agreement.RecommendedNextAction = rebuildAction
		agreement.Errors = append(agreement.Errors, "project-cognition.db has no active generation")
		return agreement
	}
	if agreement.GraphStorePath != graphStorePath {
		agreement.Readiness = rt.BlockedReadiness
		agreement.RecoveryAction = rewriteStatusAction
		agreement.Errors = append(agreement.Errors, fmt.Sprintf("graph_store_path mismatch: status.json has %q, expected %q", agreement.GraphStorePath, graphStorePath))
		return agreement
	}
	if status.ActiveGenerationID != activeGenerationID {
		agreement.Readiness = rt.BlockedReadiness
		agreement.RecoveryAction = rewriteStatusAction
		agreement.Errors = append(agreement.Errors, fmt.Sprintf("active_generation_id mismatch: status.json has %q, DB has %q", status.ActiveGenerationID, activeGenerationID))
		return agreement
	}
	if err := verifyDBMetadata(context.Background(), st, activeGenerationID, agreement.GraphStorePath); err != nil {
		agreement.Readiness = rt.BlockedReadiness
		agreement.RecoveryAction = rewriteStatusAction
		agreement.Errors = append(agreement.Errors, err.Error())
		return agreement
	}
	dbBaselineKind, dbGenerationKind, err := baselineKindAgreement(context.Background(), st, status)
	agreement.DBBaselineKind = dbBaselineKind
	agreement.DBGenerationKind = dbGenerationKind
	if err != nil {
		agreement.Readiness = rt.BlockedReadiness
		agreement.RecoveryAction = rewriteStatusAction
		agreement.Errors = append(agreement.Errors, err.Error())
		return agreement
	}
	agreement.Status = "ok"
	agreement.Readiness = status.Readiness
	agreement.RecommendedNextAction = status.RecommendedNextAction
	return agreement
}

func CheckExisting(paths rt.Paths) (Agreement, bool) {
	statusExists, statusErr := pathExists(paths.StatusPath)
	dbExists, dbErr := pathExists(paths.DatabasePath)
	if statusErr != nil || dbErr != nil {
		agreement := baseAgreement(paths)
		if statusErr != nil {
			agreement.Errors = append(agreement.Errors, fmt.Sprintf("stat status.json: %v", statusErr))
		}
		if dbErr != nil {
			agreement.Errors = append(agreement.Errors, fmt.Sprintf("stat project-cognition.db: %v", dbErr))
		}
		return agreement, true
	}
	if !statusExists && !dbExists {
		return Agreement{}, false
	}
	if statusExists != dbExists {
		agreement := baseAgreement(paths)
		agreement.RecoveryAction = rebuildAction
		if statusExists {
			agreement.Errors = append(agreement.Errors, "status.json exists but project-cognition.db is missing")
		} else {
			agreement.Errors = append(agreement.Errors, "project-cognition.db exists but status.json is missing")
		}
		return agreement, true
	}
	return Check(paths), true
}

func BlockIfExisting(paths rt.Paths) error {
	agreement, ok := CheckExisting(paths)
	if !ok || agreement.Status == "ok" {
		return nil
	}
	return fmt.Errorf("project cognition agreement blocked: %s: %s", agreementAction(agreement), strings.Join(agreement.Errors, "; "))
}

func BlockedPayload(paths rt.Paths, agreement Agreement) map[string]any {
	if agreement.StatusPath == "" {
		agreement.StatusPath = rt.RelativeRuntimePath(paths, paths.StatusPath)
	}
	if agreement.GraphStorePath == "" {
		agreement.GraphStorePath = graphStorePath
	}
	return map[string]any{
		"status":                  agreement.Status,
		"readiness":               agreement.Readiness,
		"errors":                  agreement.Errors,
		"warnings":                agreement.Warnings,
		"recovery_action":         agreement.RecoveryAction,
		"recommended_next_action": agreement.RecommendedNextAction,
		"status_path":             agreement.StatusPath,
		"graph_store_path":        agreement.GraphStorePath,
		"status_generation_id":    agreement.StatusGenerationID,
		"db_active_generation_id": agreement.DBActiveGenerationID,
		"status_baseline_kind":    agreement.StatusBaselineKind,
		"db_baseline_kind":        agreement.DBBaselineKind,
		"db_generation_kind":      agreement.DBGenerationKind,
	}
}

func agreementAction(agreement Agreement) string {
	if agreement.RecoveryAction != "" {
		return agreement.RecoveryAction
	}
	return agreement.RecommendedNextAction
}

func baseAgreement(paths rt.Paths) Agreement {
	return Agreement{
		Status:                "blocked",
		Readiness:             rt.BlockedReadiness,
		Errors:                []string{},
		Warnings:              []string{},
		RecommendedNextAction: rebuildAction,
		StatusPath:            rt.RelativeRuntimePath(paths, paths.StatusPath),
		GraphStorePath:        graphStorePath,
	}
}

func normalizeGraphStorePath(path string) string {
	if path == "" {
		return graphStorePath
	}
	cleaned := filepath.ToSlash(filepath.Clean(strings.ReplaceAll(path, `\`, `/`)))
	if cleaned == "." {
		return graphStorePath
	}
	return strings.TrimPrefix(cleaned, "./")
}

func pathExists(path string) (bool, error) {
	_, err := os.Stat(path)
	if err == nil {
		return true, nil
	}
	if errors.Is(err, os.ErrNotExist) {
		return false, nil
	}
	return false, err
}

func verifyDBMetadata(ctx context.Context, st *store.Store, activeGenerationID string, statusGraphStorePath string) error {
	meta, err := st.Metadata(ctx)
	if err != nil {
		return fmt.Errorf("read DB metadata: %w", err)
	}
	required := map[string]string{
		"runtime_format":          rt.RuntimeFormat,
		"runtime_schema":          fmt.Sprint(rt.RuntimeSchema),
		"schema_version":          fmt.Sprint(store.SchemaVersion),
		"active_generation_id":    activeGenerationID,
		"graph_store_path":        graphStorePath,
		"graph_ready":             "true",
		"baseline_state":          "fresh",
		"baseline_kind":           rt.BaselineKindBrownfieldFull,
		"query_contract_version":  "1",
		"update_contract_version": "1",
	}
	for key, want := range required {
		got, ok := meta[key]
		if !ok {
			return fmt.Errorf("project-cognition.db metadata missing %s", key)
		}
		if key == "graph_store_path" {
			got = normalizeGraphStorePath(got)
			want = normalizeGraphStorePath(want)
		}
		if key == "baseline_kind" {
			if got != rt.BaselineKindBrownfieldFull && got != rt.BaselineKindGreenfieldEmpty {
				return fmt.Errorf("project-cognition.db metadata baseline_kind has %q, expected %q or %q", got, rt.BaselineKindBrownfieldFull, rt.BaselineKindGreenfieldEmpty)
			}
			continue
		}
		if got != want {
			return fmt.Errorf("project-cognition.db metadata %s has %q, expected %q", key, got, want)
		}
	}
	if normalizeGraphStorePath(statusGraphStorePath) != normalizeGraphStorePath(meta["graph_store_path"]) {
		return fmt.Errorf("graph_store_path mismatch: status.json has %q, DB metadata has %q", statusGraphStorePath, meta["graph_store_path"])
	}
	return nil
}

func baselineKindAgreement(ctx context.Context, st *store.Store, status rt.Status) (dbKind string, generationKind string, err error) {
	meta, err := st.Metadata(ctx)
	if err != nil {
		return "", "", fmt.Errorf("read DB metadata: %w", err)
	}
	dbKind = strings.TrimSpace(meta["baseline_kind"])
	generationKind, err = st.ActiveGenerationKind(ctx)
	if err != nil {
		return "", "", err
	}
	if strings.TrimSpace(status.BaselineKind) != "" && dbKind != status.BaselineKind {
		return dbKind, generationKind, fmt.Errorf("baseline_kind mismatch: status.json has %q, DB metadata has %q", status.BaselineKind, dbKind)
	}
	if status.BaselineKind == rt.BaselineKindGreenfieldEmpty && generationKind != rt.BaselineKindGreenfieldEmpty {
		return dbKind, generationKind, fmt.Errorf("greenfield_empty status requires active generation kind %q, got %q", rt.BaselineKindGreenfieldEmpty, generationKind)
	}
	return dbKind, generationKind, nil
}
