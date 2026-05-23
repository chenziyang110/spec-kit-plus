package runtime

import (
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	gort "runtime"
	"time"
)

const (
	RuntimeFormat         = "project-cognition-go"
	RuntimeSchema         = 1
	ErrLegacyCode         = "unsupported_legacy_runtime"
	MissingFreshness      = "missing"
	ReadyFreshness        = "fresh"
	StaleFreshness        = "stale"
	ReadyReadiness        = "query_ready"
	BlockedReadiness      = "blocked"
	NeedsRebuildReadiness = "needs_rebuild"
	UnsupportedReadiness  = "unsupported_runtime"
)

var ErrUnsupportedLegacy = errors.New("unsupported legacy project cognition runtime")

type Status struct {
	RuntimeFormat                string   `json:"runtime_format"`
	RuntimeSchema                int      `json:"runtime_schema"`
	Status                       string   `json:"status"`
	Freshness                    string   `json:"freshness"`
	Readiness                    string   `json:"readiness"`
	RecommendedNextAction        string   `json:"recommended_next_action"`
	StatusPath                   string   `json:"status_path"`
	GraphStorePath               string   `json:"graph_store_path"`
	GraphReady                   bool     `json:"graph_ready"`
	ActiveGenerationID           string   `json:"active_generation_id,omitempty"`
	QueryContractVersion         int      `json:"query_contract_version,omitempty"`
	UpdateContractVersion        int      `json:"update_contract_version,omitempty"`
	Dirty                        bool     `json:"dirty"`
	DirtyReasons                 []string `json:"dirty_reasons"`
	DirtyOriginCommand           string   `json:"dirty_origin_command"`
	DirtyOriginFeatureDir        string   `json:"dirty_origin_feature_dir"`
	DirtyOriginLaneID            string   `json:"dirty_origin_lane_id"`
	DirtyScopePaths              []string `json:"dirty_scope_paths"`
	StalePaths                   []string `json:"stale_paths"`
	StaleReasons                 []string `json:"stale_reasons"`
	LastRefreshReason            string   `json:"last_refresh_reason"`
	LastRefreshBasis             string   `json:"last_refresh_basis"`
	LastRefreshChangedFilesBasis []string `json:"last_refresh_changed_files_basis"`
	LastUpdateID                 string   `json:"last_update_id"`
	LastDeltaSessionID           string   `json:"last_delta_session_id"`
	LastUpdateOutcome            string   `json:"last_update_outcome"`
	LastUpdateBoundary           string   `json:"last_update_boundary"`
	UpdatedAt                    string   `json:"updated_at"`
}

type ErrorPayload struct {
	Status                string   `json:"status"`
	Readiness             string   `json:"readiness"`
	ErrorCode             string   `json:"error_code"`
	RecommendedNextAction string   `json:"recommended_next_action"`
	Errors                []string `json:"errors"`
	StatusPath            string   `json:"status_path,omitempty"`
}

func DefaultStatus(paths Paths) Status {
	return Status{
		RuntimeFormat:                RuntimeFormat,
		RuntimeSchema:                RuntimeSchema,
		Status:                       "missing",
		Freshness:                    MissingFreshness,
		Readiness:                    NeedsRebuildReadiness,
		RecommendedNextAction:        "run_map_scan_build",
		StatusPath:                   slash(paths.StatusPath),
		GraphStorePath:               ".specify/project-cognition/project-cognition.db",
		DirtyReasons:                 []string{},
		DirtyScopePaths:              []string{},
		StalePaths:                   []string{},
		StaleReasons:                 []string{},
		LastRefreshChangedFilesBasis: []string{},
		UpdatedAt:                    time.Now().UTC().Format(time.RFC3339),
	}
}

func ReadStatus(paths Paths) (Status, error) {
	data, err := os.ReadFile(paths.StatusPath)
	if errors.Is(err, os.ErrNotExist) {
		return DefaultStatus(paths), nil
	}
	if err != nil {
		return Status{}, fmt.Errorf("read status: %w", err)
	}
	var raw map[string]any
	if err := json.Unmarshal(data, &raw); err != nil {
		return Status{}, fmt.Errorf("parse status: %w", err)
	}
	if raw["runtime_format"] != RuntimeFormat {
		return Status{}, ErrUnsupportedLegacy
	}
	var status Status
	if err := json.Unmarshal(data, &status); err != nil {
		return Status{}, fmt.Errorf("decode status: %w", err)
	}
	status.StatusPath = slash(paths.StatusPath)
	if status.GraphStorePath == "" {
		status.GraphStorePath = ".specify/project-cognition/project-cognition.db"
	}
	normalizeStatusSlices(&status)
	return status, nil
}

func WriteStatus(paths Paths, status Status) error {
	status.RuntimeFormat = RuntimeFormat
	status.RuntimeSchema = RuntimeSchema
	status.StatusPath = slash(paths.StatusPath)
	status.GraphStorePath = ".specify/project-cognition/project-cognition.db"
	status.UpdatedAt = time.Now().UTC().Format(time.RFC3339)
	normalizeStatusSlices(&status)
	if err := os.MkdirAll(paths.RuntimeDir, 0o755); err != nil {
		return fmt.Errorf("create runtime dir: %w", err)
	}
	data, err := json.MarshalIndent(status, "", "  ")
	if err != nil {
		return fmt.Errorf("encode status: %w", err)
	}
	tmpPath := paths.StatusPath + ".tmp"
	if err := os.WriteFile(tmpPath, append(data, '\n'), 0o644); err != nil {
		return fmt.Errorf("write temp status: %w", err)
	}
	if err := replaceStatusFile(tmpPath, paths.StatusPath); err != nil {
		_ = os.Remove(tmpPath)
		return err
	}
	return nil
}

func replaceStatusFile(tmpPath, statusPath string) error {
	if err := os.Rename(tmpPath, statusPath); err == nil {
		return nil
	} else if gort.GOOS != "windows" || !errors.Is(err, os.ErrExist) {
		return fmt.Errorf("replace status: %w", err)
	}
	if err := os.Remove(statusPath); err != nil {
		return fmt.Errorf("remove existing status before replace: %w", err)
	}
	if err := os.Rename(tmpPath, statusPath); err != nil {
		return fmt.Errorf("replace status after removing existing file: %w", err)
	}
	return nil
}

func UnsupportedLegacyPayload(paths Paths) ErrorPayload {
	return ErrorPayload{
		Status:                "blocked",
		Readiness:             UnsupportedReadiness,
		ErrorCode:             ErrLegacyCode,
		RecommendedNextAction: "run_map_scan_build",
		Errors:                []string{"existing .specify/project-cognition runtime is not a Go project-cognition runtime; remove or archive it and run sp-map-scan followed by sp-map-build"},
		StatusPath:            slash(paths.StatusPath),
	}
}

func RelativeRuntimePath(paths Paths, abs string) string {
	if rel, err := filepath.Rel(paths.Root, abs); err == nil {
		return slash(rel)
	}
	return slash(abs)
}

func slash(path string) string {
	return filepath.ToSlash(path)
}

func normalizeStatusSlices(status *Status) {
	if status.DirtyReasons == nil {
		status.DirtyReasons = []string{}
	}
	if status.DirtyScopePaths == nil {
		status.DirtyScopePaths = []string{}
	}
	if status.StalePaths == nil {
		status.StalePaths = []string{}
	}
	if status.StaleReasons == nil {
		status.StaleReasons = []string{}
	}
	if status.LastRefreshChangedFilesBasis == nil {
		status.LastRefreshChangedFilesBasis = []string{}
	}
}
