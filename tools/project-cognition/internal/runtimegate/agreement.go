package runtimegate

import (
	"context"
	"database/sql"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"strings"

	rt "github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/runtime"
	"github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/store"
)

const (
	graphStorePath                   = ".specify/project-cognition/project-cognition.db"
	rebuildAction                    = "run_map_scan_build"
	RepairStatusAction               = "project_cognition.repair_status"
	ResolveStatusAccessAction        = "project_cognition.resolve_status_access"
	FinalizeUpdateAction             = "project_cognition.validate_and_complete_refresh"
	LatestUpdateMismatchRepairReason = "status_latest_update_mismatch_repaired"
)

type CauseCode string

const (
	CauseRuntimeStateUnreadable        CauseCode = "runtime_state_unreadable"
	CauseUnsupportedRuntime            CauseCode = "unsupported_runtime"
	CauseStatusUnreadable              CauseCode = "status_unreadable"
	CauseStatusAccessFailed            CauseCode = "status_access_failed"
	CauseStatusWriteFailed             CauseCode = "status_write_failed"
	CauseGraphStoreIncompatible        CauseCode = "graph_store_incompatible"
	CauseGraphStoreUnreadable          CauseCode = "graph_store_unreadable"
	CauseMissingActiveGeneration       CauseCode = "missing_active_generation"
	CauseStatusGraphStorePathMismatch  CauseCode = "status_graph_store_path_mismatch"
	CauseStatusGenerationMismatch      CauseCode = "status_generation_mismatch"
	CauseStatusLatestUpdateMismatch    CauseCode = "status_latest_update_mismatch"
	CauseUpdateFinalizationPending     CauseCode = "update_finalization_pending"
	CauseGraphStoreMetadataInvalid     CauseCode = "graph_store_metadata_invalid"
	CauseStatusBaselineKindMismatch    CauseCode = "status_baseline_kind_mismatch"
	CauseGraphStoreBaselineKindInvalid CauseCode = "graph_store_baseline_kind_invalid"
	CauseMissingStatus                 CauseCode = "missing_status"
	CauseMissingGraphStore             CauseCode = "missing_graph_store"
)

type CauseOwner string

const (
	CauseOwnerRuntimeState CauseOwner = "runtime_state"
	CauseOwnerStatus       CauseOwner = "status"
	CauseOwnerGraphStore   CauseOwner = "graph_store"
)

type Agreement struct {
	Status                  string     `json:"status"`
	Readiness               string     `json:"readiness"`
	CauseCode               CauseCode  `json:"cause_code,omitempty"`
	CauseOwner              CauseOwner `json:"cause_owner,omitempty"`
	Errors                  []string   `json:"errors"`
	Warnings                []string   `json:"warnings"`
	RecoveryAction          string     `json:"recovery_action,omitempty"`
	StatusPath              string     `json:"status_path"`
	GraphStorePath          string     `json:"graph_store_path"`
	StatusGenerationID      string     `json:"status_generation_id,omitempty"`
	DBActiveGenerationID    string     `json:"db_active_generation_id,omitempty"`
	StatusBaselineKind      string     `json:"status_baseline_kind,omitempty"`
	DBBaselineKind          string     `json:"db_baseline_kind,omitempty"`
	DBGenerationKind        string     `json:"db_generation_kind,omitempty"`
	StatusLatestUpdateID    string     `json:"status_latest_update_id,omitempty"`
	StatusLatestOutcome     string     `json:"status_latest_update_outcome,omitempty"`
	StatusFinalizedUpdateID string     `json:"status_finalized_update_id,omitempty"`
	DBLatestUpdateID        string     `json:"db_latest_update_id,omitempty"`
	DBLatestUpdateOutcome   string     `json:"db_latest_update_outcome,omitempty"`
	RecommendedNextAction   string     `json:"recommended_next_action"`
}

type latestUpdateState struct {
	ID           string
	Outcome      string
	ChangedPaths []string
}

type RepairError struct {
	CauseCode  CauseCode
	CauseOwner CauseOwner
	Err        error
}

func (e *RepairError) Error() string {
	if e == nil || e.Err == nil {
		return "project cognition status repair failed"
	}
	return e.Err.Error()
}

func (e *RepairError) Unwrap() error {
	if e == nil {
		return nil
	}
	return e.Err
}

func repairError(code CauseCode, owner CauseOwner, err error) error {
	return &RepairError{CauseCode: code, CauseOwner: owner, Err: err}
}

func Check(paths rt.Paths) Agreement {
	agreement := baseAgreement(paths)
	status, err := rt.ReadStatus(paths)
	if errors.Is(err, rt.ErrUnsupportedLegacy) {
		payload := rt.UnsupportedLegacyPayload(paths)
		agreement.Readiness = rt.UnsupportedReadiness
		agreement.CauseCode = CauseUnsupportedRuntime
		agreement.CauseOwner = CauseOwnerRuntimeState
		agreement.RecoveryAction = rebuildAction
		agreement.RecommendedNextAction = rebuildAction
		agreement.Errors = append(agreement.Errors, payload.ErrorCode+": "+payload.Errors[0])
		return agreement
	}
	if err != nil {
		agreement.CauseCode = CauseStatusUnreadable
		agreement.CauseOwner = CauseOwnerStatus
		agreement.RecoveryAction = RepairStatusAction
		agreement.RecommendedNextAction = RepairStatusAction
		agreement.Errors = append(agreement.Errors, fmt.Sprintf("read status: %v", err))
		return agreement
	}
	agreement.Readiness = status.Readiness
	agreement.GraphStorePath = normalizeGraphStorePath(status.GraphStorePath)
	agreement.StatusGenerationID = status.ActiveGenerationID
	agreement.StatusBaselineKind = status.BaselineKind
	agreement.StatusLatestUpdateID = strings.TrimSpace(status.LastUpdateID)
	agreement.StatusLatestOutcome = strings.TrimSpace(status.LastUpdateOutcome)
	agreement.StatusFinalizedUpdateID = strings.TrimSpace(status.LastFinalizedUpdateID)

	st, err := store.OpenExisting(paths)
	if err != nil {
		agreement.Readiness = rt.BlockedReadiness
		agreement.CauseCode = CauseGraphStoreIncompatible
		agreement.CauseOwner = CauseOwnerGraphStore
		agreement.RecoveryAction = rebuildAction
		agreement.RecommendedNextAction = rebuildAction
		agreement.Errors = append(agreement.Errors, fmt.Sprintf("open graph store: %v", err))
		return agreement
	}
	defer st.Close()

	activeGenerationID, err := st.ActiveGenerationID(context.Background())
	if err != nil {
		agreement.Readiness = rt.BlockedReadiness
		agreement.CauseCode = CauseGraphStoreUnreadable
		agreement.CauseOwner = CauseOwnerGraphStore
		agreement.RecoveryAction = rebuildAction
		agreement.RecommendedNextAction = rebuildAction
		agreement.Errors = append(agreement.Errors, fmt.Sprintf("read DB active generation: %v", err))
		return agreement
	}
	agreement.DBActiveGenerationID = activeGenerationID
	if activeGenerationID == "" {
		agreement.Readiness = rt.BlockedReadiness
		agreement.CauseCode = CauseMissingActiveGeneration
		agreement.CauseOwner = CauseOwnerGraphStore
		agreement.RecoveryAction = rebuildAction
		agreement.RecommendedNextAction = rebuildAction
		agreement.Errors = append(agreement.Errors, "project-cognition.db has no active generation")
		return agreement
	}
	if err := verifyDBMetadata(context.Background(), st, activeGenerationID, graphStorePath); err != nil {
		agreement.Readiness = rt.BlockedReadiness
		agreement.CauseCode = CauseGraphStoreMetadataInvalid
		agreement.CauseOwner = CauseOwnerGraphStore
		agreement.RecoveryAction = rebuildAction
		agreement.RecommendedNextAction = rebuildAction
		agreement.Errors = append(agreement.Errors, err.Error())
		return agreement
	}
	dbBaselineKind, dbGenerationKind, err := baselineKindAgreement(context.Background(), st, rt.Status{})
	agreement.DBBaselineKind = dbBaselineKind
	agreement.DBGenerationKind = dbGenerationKind
	if err != nil || dbBaselineKind == "" || dbGenerationKind == "" || dbBaselineKind != dbGenerationKind {
		agreement.Readiness = rt.BlockedReadiness
		agreement.CauseCode = CauseGraphStoreBaselineKindInvalid
		agreement.CauseOwner = CauseOwnerGraphStore
		agreement.RecoveryAction = rebuildAction
		agreement.RecommendedNextAction = rebuildAction
		if err != nil {
			agreement.Errors = append(agreement.Errors, err.Error())
		} else {
			agreement.Errors = append(agreement.Errors, fmt.Sprintf("baseline_kind mismatch: DB metadata has %q, active generation has %q", dbBaselineKind, dbGenerationKind))
		}
		return agreement
	}
	if agreement.GraphStorePath != graphStorePath {
		agreement.Readiness = rt.BlockedReadiness
		agreement.CauseCode = CauseStatusGraphStorePathMismatch
		agreement.CauseOwner = CauseOwnerStatus
		agreement.RecoveryAction = RepairStatusAction
		agreement.RecommendedNextAction = RepairStatusAction
		agreement.Errors = append(agreement.Errors, fmt.Sprintf("graph_store_path mismatch: status.json has %q, expected %q", agreement.GraphStorePath, graphStorePath))
		return agreement
	}
	if status.ActiveGenerationID != activeGenerationID {
		agreement.Readiness = rt.BlockedReadiness
		agreement.CauseCode = CauseStatusGenerationMismatch
		agreement.CauseOwner = CauseOwnerStatus
		agreement.RecoveryAction = RepairStatusAction
		agreement.RecommendedNextAction = RepairStatusAction
		agreement.Errors = append(agreement.Errors, fmt.Sprintf("active_generation_id mismatch: status.json has %q, DB has %q", status.ActiveGenerationID, activeGenerationID))
		return agreement
	}
	if normalizeBaselineKind(status.BaselineKind) != "" && normalizeBaselineKind(status.BaselineKind) != dbBaselineKind {
		agreement.Readiness = rt.BlockedReadiness
		agreement.CauseCode = CauseStatusBaselineKindMismatch
		agreement.CauseOwner = CauseOwnerStatus
		agreement.RecoveryAction = RepairStatusAction
		agreement.RecommendedNextAction = RepairStatusAction
		agreement.Errors = append(agreement.Errors, fmt.Sprintf("baseline_kind mismatch: status.json has %q, DB metadata has %q", normalizeBaselineKind(status.BaselineKind), dbBaselineKind))
		return agreement
	}
	latestUpdate, err := readLatestUpdate(context.Background(), st, activeGenerationID)
	if err != nil {
		agreement.Readiness = rt.BlockedReadiness
		agreement.CauseCode = CauseGraphStoreUnreadable
		agreement.CauseOwner = CauseOwnerGraphStore
		agreement.RecoveryAction = rebuildAction
		agreement.RecommendedNextAction = rebuildAction
		agreement.Errors = append(agreement.Errors, fmt.Sprintf("read DB latest update: %v", err))
		return agreement
	}
	agreement.DBLatestUpdateID = latestUpdate.ID
	agreement.DBLatestUpdateOutcome = latestUpdate.Outcome
	if agreement.StatusLatestUpdateID != latestUpdate.ID || agreement.StatusLatestOutcome != latestUpdate.Outcome {
		agreement.Readiness = rt.BlockedReadiness
		agreement.CauseCode = CauseStatusLatestUpdateMismatch
		agreement.CauseOwner = CauseOwnerStatus
		agreement.RecoveryAction = RepairStatusAction
		agreement.RecommendedNextAction = RepairStatusAction
		agreement.Errors = append(agreement.Errors, fmt.Sprintf(
			"latest update mismatch: status.json has %q/%q, DB has %q/%q",
			agreement.StatusLatestUpdateID,
			agreement.StatusLatestOutcome,
			latestUpdate.ID,
			latestUpdate.Outcome,
		))
		return agreement
	}
	if updateOutcomeRequiresFinalization(latestUpdate.Outcome) && agreement.StatusFinalizedUpdateID != latestUpdate.ID {
		agreement.Readiness = rt.BlockedReadiness
		agreement.CauseCode = CauseUpdateFinalizationPending
		agreement.CauseOwner = CauseOwnerStatus
		agreement.RecoveryAction = FinalizeUpdateAction
		agreement.RecommendedNextAction = FinalizeUpdateAction
		agreement.Errors = append(agreement.Errors, fmt.Sprintf("latest update %s/%s is not receipt-bound finalized", latestUpdate.ID, latestUpdate.Outcome))
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
		agreement.CauseCode = CauseRuntimeStateUnreadable
		agreement.CauseOwner = CauseOwnerRuntimeState
		agreement.RecoveryAction = rebuildAction
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
		if statusExists {
			agreement.CauseCode = CauseMissingGraphStore
			agreement.CauseOwner = CauseOwnerGraphStore
			agreement.RecoveryAction = rebuildAction
			agreement.Errors = append(agreement.Errors, "status.json exists but project-cognition.db is missing")
		} else {
			agreement.CauseCode = CauseMissingStatus
			agreement.CauseOwner = CauseOwnerStatus
			agreement.RecoveryAction = RepairStatusAction
			agreement.RecommendedNextAction = RepairStatusAction
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
		"status":                     agreement.Status,
		"readiness":                  agreement.Readiness,
		"cause_code":                 agreement.CauseCode,
		"cause_owner":                agreement.CauseOwner,
		"errors":                     agreement.Errors,
		"warnings":                   agreement.Warnings,
		"recovery_action":            agreement.RecoveryAction,
		"recommended_next_action":    agreement.RecommendedNextAction,
		"status_path":                agreement.StatusPath,
		"graph_store_path":           agreement.GraphStorePath,
		"status_generation_id":       agreement.StatusGenerationID,
		"db_active_generation_id":    agreement.DBActiveGenerationID,
		"status_baseline_kind":       agreement.StatusBaselineKind,
		"db_baseline_kind":           agreement.DBBaselineKind,
		"db_generation_kind":         agreement.DBGenerationKind,
		"status_latest_update_id":    agreement.StatusLatestUpdateID,
		"status_latest_outcome":      agreement.StatusLatestOutcome,
		"status_finalized_update_id": agreement.StatusFinalizedUpdateID,
		"db_latest_update_id":        agreement.DBLatestUpdateID,
		"db_latest_outcome":          agreement.DBLatestUpdateOutcome,
	}
}

// RepairStatusFromDB reconstructs status-owned runtime fields only after the
// graph store proves its own schema, metadata, and active-generation agreement.
func RepairStatusFromDB(paths rt.Paths) (rt.Status, error) {
	releaseUpdateLock, err := rt.AcquireUpdateLock(paths)
	if err != nil {
		return rt.Status{}, repairError(CauseRuntimeStateUnreadable, CauseOwnerRuntimeState, err)
	}
	defer releaseUpdateLock()

	st, err := store.OpenExisting(paths)
	if err != nil {
		return rt.Status{}, repairError(CauseGraphStoreIncompatible, CauseOwnerGraphStore, fmt.Errorf("open graph store for status repair: %w", err))
	}
	defer st.Close()

	ctx := context.Background()
	activeGenerationID, err := st.ActiveGenerationID(ctx)
	if err != nil {
		return rt.Status{}, repairError(CauseGraphStoreUnreadable, CauseOwnerGraphStore, fmt.Errorf("read DB active generation for status repair: %w", err))
	}
	if activeGenerationID == "" {
		return rt.Status{}, repairError(CauseMissingActiveGeneration, CauseOwnerGraphStore, fmt.Errorf("project-cognition.db has no active generation"))
	}
	baselineState, dbBaselineKind, err := inspectDBMetadataForStatusRepair(ctx, st, activeGenerationID)
	if err != nil {
		return rt.Status{}, repairError(CauseGraphStoreMetadataInvalid, CauseOwnerGraphStore, fmt.Errorf("validate graph store for status repair: %w", err))
	}
	dbBaselineKind, dbGenerationKind, err := baselineKindAgreement(ctx, st, rt.Status{})
	if err != nil {
		return rt.Status{}, repairError(CauseGraphStoreBaselineKindInvalid, CauseOwnerGraphStore, fmt.Errorf("validate graph baseline for status repair: %w", err))
	}
	if dbBaselineKind == "" || dbGenerationKind == "" || dbBaselineKind != dbGenerationKind {
		return rt.Status{}, repairError(CauseGraphStoreBaselineKindInvalid, CauseOwnerGraphStore, fmt.Errorf(
			"graph baseline cannot repair status: metadata=%q active_generation=%q",
			dbBaselineKind,
			dbGenerationKind,
		))
	}
	latestUpdate, err := readLatestUpdate(ctx, st, activeGenerationID)
	if err != nil {
		return rt.Status{}, repairError(CauseGraphStoreUnreadable, CauseOwnerGraphStore, fmt.Errorf("read DB latest update for status repair: %w", err))
	}

	statusExists, statusErr := pathExists(paths.StatusPath)
	if statusErr != nil {
		return rt.Status{}, repairError(CauseStatusAccessFailed, CauseOwnerStatus, fmt.Errorf("inspect status before repair: %w", statusErr))
	}
	status, readErr := rt.ReadStatus(paths)
	reconstructed := !statusExists || readErr != nil || status.Status == "" || status.Status == "missing"
	if readErr != nil {
		status = rt.DefaultStatus(paths)
	}
	latestUpdateMismatch := strings.TrimSpace(status.LastUpdateID) != latestUpdate.ID || strings.TrimSpace(status.LastUpdateOutcome) != latestUpdate.Outcome
	if baselineState == "blocked" {
		status.Status = "blocked"
		status.Freshness = rt.StaleFreshness
		status.Readiness = rt.BlockedReadiness
		status.RecommendedNextAction = rebuildAction
		status.Dirty = true
		status.DirtyReasons = appendUnique(status.DirtyReasons, "graph_store_baseline_blocked")
		status.StaleReasons = appendUnique(status.StaleReasons, "graph_store_baseline_blocked")
		status.DirtyOriginCommand = "project-cognition repair-status"
	} else if reconstructed {
		status.Status = "stale"
		status.Freshness = rt.StaleFreshness
		status.Readiness = rt.ReviewReadiness
		status.RecommendedNextAction = "review_project_cognition_update"
		status.Dirty = true
		status.DirtyReasons = appendUnique(status.DirtyReasons, "status_reconstructed_from_db_metadata")
		status.StaleReasons = appendUnique(status.StaleReasons, "status_reconstructed_from_db_metadata")
		status.DirtyOriginCommand = "project-cognition repair-status"
	}
	if latestUpdateMismatch && baselineState == "fresh" {
		status.Status = "stale"
		status.Freshness = rt.StaleFreshness
		status.Readiness = rt.ReviewReadiness
		status.RecommendedNextAction = "review_project_cognition_update"
		status.Dirty = true
		status.DirtyReasons = appendUnique(status.DirtyReasons, LatestUpdateMismatchRepairReason)
		status.StaleReasons = appendUnique(status.StaleReasons, LatestUpdateMismatchRepairReason)
		status.DirtyOriginCommand = "project-cognition repair-status"
		for _, path := range latestUpdate.ChangedPaths {
			status.DirtyScopePaths = appendUnique(status.DirtyScopePaths, path)
			status.StalePaths = appendUnique(status.StalePaths, path)
		}
	}
	status.LastUpdateID = latestUpdate.ID
	status.LastUpdateOutcome = latestUpdate.Outcome
	status.LastRefreshChangedFilesBasis = append([]string{}, latestUpdate.ChangedPaths...)
	status.GraphStorePath = graphStorePath
	status.GraphReady = baselineState == "fresh"
	status.ActiveGenerationID = activeGenerationID
	status.BaselineKind = dbBaselineKind
	status.QueryContractVersion = 1
	status.UpdateContractVersion = 1
	if err := rt.WriteStatus(paths, status); err != nil {
		return rt.Status{}, repairError(CauseStatusWriteFailed, CauseOwnerStatus, fmt.Errorf("write repaired status: %w", err))
	}

	agreement := Check(paths)
	if baselineState == "fresh" && agreement.Status != "ok" && agreement.CauseCode != CauseUpdateFinalizationPending {
		return rt.Status{}, repairError(agreement.CauseCode, agreement.CauseOwner, fmt.Errorf(
			"repaired status did not restore runtime agreement: %s",
			strings.Join(agreement.Errors, "; "),
		))
	}
	return status, nil
}

func updateOutcomeRequiresFinalization(outcome string) bool {
	switch strings.TrimSpace(outcome) {
	case "ready", "no_op":
		return true
	default:
		return false
	}
}

func readLatestUpdate(ctx context.Context, st *store.Store, activeGenerationID string) (latestUpdateState, error) {
	var state latestUpdateState
	var changedPathsJSON string
	err := st.DB().QueryRowContext(ctx, `SELECT id, result_state, changed_paths_json FROM updates WHERE generation_id = ? ORDER BY completed_at DESC, id DESC LIMIT 1`, activeGenerationID).Scan(&state.ID, &state.Outcome, &changedPathsJSON)
	if errors.Is(err, sql.ErrNoRows) {
		return latestUpdateState{}, nil
	}
	if err != nil {
		return latestUpdateState{}, err
	}
	if strings.TrimSpace(changedPathsJSON) == "" {
		state.ChangedPaths = []string{}
		return state, nil
	}
	if err := json.Unmarshal([]byte(changedPathsJSON), &state.ChangedPaths); err != nil {
		return latestUpdateState{}, fmt.Errorf("decode changed_paths_json for update %s: %w", state.ID, err)
	}
	return state, nil
}

func inspectDBMetadataForStatusRepair(ctx context.Context, st *store.Store, activeGenerationID string) (string, string, error) {
	meta, err := st.Metadata(ctx)
	if err != nil {
		return "", "", fmt.Errorf("read DB metadata: %w", err)
	}
	required := []struct {
		key  string
		want string
	}{
		{key: "runtime_format", want: rt.RuntimeFormat},
		{key: "runtime_schema", want: fmt.Sprint(rt.RuntimeSchema)},
		{key: "schema_version", want: fmt.Sprint(store.SchemaVersion)},
		{key: "active_generation_id", want: activeGenerationID},
		{key: "graph_store_path", want: graphStorePath},
	}
	for _, item := range required {
		got, ok := meta[item.key]
		if !ok {
			return "", "", fmt.Errorf("project-cognition.db metadata missing %s", item.key)
		}
		if item.key == "graph_store_path" {
			got = normalizeGraphStorePath(got)
		}
		if got != item.want {
			return "", "", fmt.Errorf("project-cognition.db metadata %s has %q, expected %q", item.key, got, item.want)
		}
	}

	baselineKind := normalizeBaselineKind(meta["baseline_kind"])
	if baselineKind != rt.BaselineKindBrownfieldFull && baselineKind != rt.BaselineKindGreenfieldEmpty {
		return "", "", fmt.Errorf("project-cognition.db metadata baseline_kind has %q", meta["baseline_kind"])
	}
	baselineState := strings.TrimSpace(meta["baseline_state"])
	switch baselineState {
	case "fresh":
		for _, item := range []struct {
			key  string
			want string
		}{
			{key: "graph_ready", want: "true"},
			{key: "query_contract_version", want: "1"},
			{key: "update_contract_version", want: "1"},
		} {
			if meta[item.key] != item.want {
				return "", "", fmt.Errorf("project-cognition.db metadata %s has %q, expected %q", item.key, meta[item.key], item.want)
			}
		}
	case "blocked":
		if meta["graph_ready"] != "false" {
			return "", "", fmt.Errorf("project-cognition.db metadata graph_ready has %q, expected %q", meta["graph_ready"], "false")
		}
	default:
		return "", "", fmt.Errorf("project-cognition.db metadata baseline_state has %q, expected fresh or blocked", baselineState)
	}
	return baselineState, baselineKind, nil
}

func appendUnique(values []string, value string) []string {
	for _, existing := range values {
		if existing == value {
			return values
		}
	}
	return append(values, value)
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
	statusKind := normalizeBaselineKind(status.BaselineKind)
	dbKind = normalizeBaselineKind(meta["baseline_kind"])
	generationKind, err = st.ActiveGenerationKind(ctx)
	if err != nil {
		return "", "", err
	}
	generationKind = normalizeBaselineKind(generationKind)
	if statusKind != "" && dbKind != statusKind {
		return dbKind, generationKind, fmt.Errorf("baseline_kind mismatch: status.json has %q, DB metadata has %q", statusKind, dbKind)
	}
	if dbKind != "" && generationKind != "" && dbKind != generationKind {
		return dbKind, generationKind, fmt.Errorf("baseline_kind mismatch: DB metadata has %q, active generation has %q", dbKind, generationKind)
	}
	return dbKind, generationKind, nil
}

func normalizeBaselineKind(kind string) string {
	switch strings.TrimSpace(kind) {
	case "":
		return ""
	case "full":
		return rt.BaselineKindBrownfieldFull
	default:
		return strings.TrimSpace(kind)
	}
}
