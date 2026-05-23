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
	agreement.Status = "ok"
	agreement.Readiness = status.Readiness
	agreement.RecommendedNextAction = status.RecommendedNextAction
	return agreement
}

func CheckExisting(paths rt.Paths) (Agreement, bool) {
	if _, err := os.Stat(paths.StatusPath); err != nil {
		return Agreement{}, false
	}
	if _, err := os.Stat(paths.DatabasePath); err != nil {
		return Agreement{}, false
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
