package runtime

import (
	"crypto/sha256"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"time"
)

const (
	RuntimeFormat                          = "project-cognition-go"
	RuntimeSchema                          = 1
	ErrLegacyCode                          = "unsupported_legacy_runtime"
	MissingFreshness                       = "missing"
	ReadyFreshness                         = "fresh"
	PartialRefreshFreshness                = "partial_refresh"
	PendingFinalizationStatus              = "pending_finalization"
	StaleFreshness                         = "stale"
	ReadyReadiness                         = "query_ready"
	ReviewReadiness                        = "review"
	BlockedReadiness                       = "blocked"
	NeedsRebuildReadiness                  = "needs_rebuild"
	UnsupportedReadiness                   = "unsupported_runtime"
	BaselineKindBrownfieldFull             = "brownfield_full"
	BaselineKindGreenfieldEmpty            = "greenfield_empty"
	GreenfieldBaselineHasProjectCodeReason = "greenfield_baseline_has_project_code"
)

var ErrUnsupportedLegacy = errors.New("unsupported legacy project cognition runtime")

type Status struct {
	RuntimeFormat                string       `json:"runtime_format"`
	RuntimeSchema                int          `json:"runtime_schema"`
	Status                       string       `json:"status"`
	Freshness                    string       `json:"freshness"`
	Readiness                    string       `json:"readiness"`
	RecommendedNextAction        string       `json:"recommended_next_action"`
	StatusPath                   string       `json:"status_path"`
	GraphStorePath               string       `json:"graph_store_path"`
	GraphReady                   bool         `json:"graph_ready"`
	ActiveGenerationID           string       `json:"active_generation_id,omitempty"`
	BaselineKind                 string       `json:"baseline_kind,omitempty"`
	QueryContractVersion         int          `json:"query_contract_version,omitempty"`
	UpdateContractVersion        int          `json:"update_contract_version,omitempty"`
	Dirty                        bool         `json:"dirty"`
	DirtyReasons                 []string     `json:"dirty_reasons"`
	DirtyOriginCommand           string       `json:"dirty_origin_command"`
	DirtyOriginFeatureDir        string       `json:"dirty_origin_feature_dir"`
	DirtyOriginLaneID            string       `json:"dirty_origin_lane_id"`
	DirtyScopePaths              []string     `json:"dirty_scope_paths"`
	DirtyDebts                   []DebtRecord `json:"dirty_debts,omitempty"`
	StalePaths                   []string     `json:"stale_paths"`
	StaleReasons                 []string     `json:"stale_reasons"`
	LastRefreshReason            string       `json:"last_refresh_reason"`
	LastRefreshBasis             string       `json:"last_refresh_basis"`
	LastRefreshGitCommit         string       `json:"last_refresh_git_commit,omitempty"`
	LastRefreshGitBranch         string       `json:"last_refresh_git_branch,omitempty"`
	LastRefreshChangedFilesBasis []string     `json:"last_refresh_changed_files_basis"`
	LastUpdateID                 string       `json:"last_update_id"`
	LastFinalizedUpdateID        string       `json:"last_finalized_update_id,omitempty"`
	LastDeltaSessionID           string       `json:"last_delta_session_id"`
	LastUpdateOutcome            string       `json:"last_update_outcome"`
	LastUpdateScopeOutcome       string       `json:"last_update_scope_outcome,omitempty"`
	LastUpdatePartialReasons     []string     `json:"last_update_partial_reasons,omitempty"`
	LastUpdateBoundary           string       `json:"last_update_boundary"`
	UpdatedAt                    string       `json:"updated_at"`
}

type DebtRecord struct {
	ID               string   `json:"id"`
	Kind             string   `json:"kind"`
	Paths            []string `json:"paths,omitempty"`
	Reason           string   `json:"reason,omitempty"`
	UpdateID         string   `json:"update_id,omitempty"`
	OriginCommand    string   `json:"origin_command,omitempty"`
	OriginFeatureDir string   `json:"origin_feature_dir,omitempty"`
	OriginLaneID     string   `json:"origin_lane_id,omitempty"`
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
		DirtyDebts:                   []DebtRecord{},
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
	if status.RuntimeSchema != RuntimeSchema {
		return Status{}, ErrUnsupportedLegacy
	}
	if status.GraphStorePath == "" {
		return Status{}, ErrUnsupportedLegacy
	}
	status.StatusPath = slash(paths.StatusPath)
	normalizeStatusSlices(&status)
	normalizeDerivedStatus(&status)
	return status, nil
}

func WriteStatus(paths Paths, status Status) error {
	status.RuntimeFormat = RuntimeFormat
	status.RuntimeSchema = RuntimeSchema
	status.StatusPath = slash(paths.StatusPath)
	status.GraphStorePath = ".specify/project-cognition/project-cognition.db"
	status.UpdatedAt = time.Now().UTC().Format(time.RFC3339)
	normalizeStatusSlices(&status)
	normalizeDerivedStatus(&status)
	if err := os.MkdirAll(paths.RuntimeDir, 0o755); err != nil {
		return fmt.Errorf("create runtime dir: %w", err)
	}
	data, err := json.MarshalIndent(status, "", "  ")
	if err != nil {
		return fmt.Errorf("encode status: %w", err)
	}
	tmpFile, err := os.CreateTemp(paths.RuntimeDir, ".status-*.tmp")
	if err != nil {
		return fmt.Errorf("create temp status: %w", err)
	}
	tmpPath := tmpFile.Name()
	if _, err := tmpFile.Write(append(data, '\n')); err != nil {
		_ = tmpFile.Close()
		_ = os.Remove(tmpPath)
		return fmt.Errorf("write temp status: %w", err)
	}
	if err := tmpFile.Close(); err != nil {
		_ = os.Remove(tmpPath)
		return fmt.Errorf("close temp status: %w", err)
	}
	if err := replaceStatusFile(tmpPath, paths.StatusPath); err != nil {
		_ = os.Remove(tmpPath)
		return err
	}
	return nil
}

func UnsupportedLegacyPayload(paths Paths) ErrorPayload {
	return ErrorPayload{
		Status:                "blocked",
		Readiness:             UnsupportedReadiness,
		ErrorCode:             ErrLegacyCode,
		RecommendedNextAction: "run_map_scan_build",
		Errors:                []string{"existing .specify/project-cognition state is not a compatible specify-runtime cognition store; remove or archive it and run sp-map-scan followed by sp-map-build"},
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
	if status.DirtyDebts == nil {
		status.DirtyDebts = []DebtRecord{}
		if status.Dirty && (len(status.DirtyScopePaths) > 0 || len(status.StalePaths) > 0 || len(status.DirtyReasons) > 0) {
			legacyPaths := append([]string{}, status.DirtyScopePaths...)
			legacyPaths = append(legacyPaths, status.StalePaths...)
			legacyPathSet := map[string]bool{}
			for _, path := range legacyPaths {
				path = filepath.ToSlash(strings.TrimSpace(path))
				if path != "" {
					legacyPathSet[path] = true
				}
			}
			legacyPaths = sortedStatusKeys(legacyPathSet)
			status.DirtyDebts = []DebtRecord{{
				ID:               legacyDebtID(legacyPaths, status.DirtyReasons),
				Kind:             "legacy_dirty",
				Paths:            legacyPaths,
				Reason:           strings.Join(status.DirtyReasons, "; "),
				OriginCommand:    status.DirtyOriginCommand,
				OriginFeatureDir: status.DirtyOriginFeatureDir,
				OriginLaneID:     status.DirtyOriginLaneID,
			}}
		}
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
	if status.LastUpdatePartialReasons == nil {
		status.LastUpdatePartialReasons = []string{}
	}
	ProjectDirtyDebts(status)
}

func ProjectDirtyDebts(status *Status) {
	if status == nil || len(status.DirtyDebts) == 0 {
		return
	}
	paths := map[string]bool{}
	reasons := map[string]bool{}
	for _, path := range append(append([]string{}, status.DirtyScopePaths...), status.StalePaths...) {
		path = filepath.ToSlash(strings.TrimSpace(path))
		if path != "" {
			paths[path] = true
		}
	}
	for _, reason := range append(append([]string{}, status.DirtyReasons...), status.StaleReasons...) {
		reason = strings.TrimSpace(reason)
		if reason != "" {
			reasons[reason] = true
		}
	}
	for _, debt := range status.DirtyDebts {
		for _, path := range debt.Paths {
			path = filepath.ToSlash(strings.TrimSpace(path))
			if path != "" {
				paths[path] = true
			}
		}
		reason := strings.TrimSpace(debt.Reason)
		if reason == "" {
			reason = strings.TrimSpace(debt.Kind)
		}
		if reason != "" {
			reasons[reason] = true
		}
	}
	status.DirtyScopePaths = sortedStatusKeys(paths)
	status.DirtyReasons = sortedStatusKeys(reasons)
	status.StalePaths = append([]string{}, status.DirtyScopePaths...)
	status.StaleReasons = append([]string{}, status.DirtyReasons...)
	status.Dirty = true
	if first := status.DirtyDebts[0]; len(status.DirtyDebts) == 1 {
		status.DirtyOriginCommand = first.OriginCommand
		status.DirtyOriginFeatureDir = first.OriginFeatureDir
		status.DirtyOriginLaneID = first.OriginLaneID
	} else {
		status.DirtyOriginCommand = ""
		status.DirtyOriginFeatureDir = ""
		status.DirtyOriginLaneID = ""
	}
	if status.Status == "ok" || status.Freshness == ReadyFreshness || status.Readiness == ReadyReadiness {
		status.Status = "stale"
		status.Freshness = StaleFreshness
		status.Readiness = BlockedReadiness
		status.RecommendedNextAction = "run_map_update"
	}
}

func sortedStatusKeys(values map[string]bool) []string {
	out := make([]string, 0, len(values))
	for value := range values {
		out = append(out, value)
	}
	sort.Strings(out)
	return out
}

func legacyDebtID(paths []string, reasons []string) string {
	values := append([]string{}, paths...)
	values = append(values, reasons...)
	sort.Strings(values)
	digest := sha256.Sum256([]byte(strings.Join(values, "\x00")))
	return fmt.Sprintf("debt-legacy-%x", digest[:8])
}

func normalizeDerivedStatus(status *Status) {
	if status.BaselineKind != BaselineKindGreenfieldEmpty || (len(status.StalePaths) == 0 && len(status.DirtyScopePaths) == 0) {
		return
	}
	status.Status = "stale"
	status.Freshness = StaleFreshness
	status.Readiness = NeedsRebuildReadiness
	status.RecommendedNextAction = "run_map_scan_build"
	status.Dirty = true
	status.DirtyReasons = appendStatusReason(status.DirtyReasons, GreenfieldBaselineHasProjectCodeReason)
	status.StaleReasons = appendStatusReason(status.StaleReasons, GreenfieldBaselineHasProjectCodeReason)
}

func appendStatusReason(values []string, reason string) []string {
	for _, value := range values {
		if value == reason {
			return values
		}
	}
	return append(values, reason)
}
