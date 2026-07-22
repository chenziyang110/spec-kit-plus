package update

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
	"time"

	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/boundary"
	changemodel "github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/changes/model"
	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/config"
	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/delta"
	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/ignore"
	rt "github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/runtime"
	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/runtimegate"
	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/store"
)

type DirtyInput struct {
	Reason           string
	OriginCommand    string
	OriginFeatureDir string
	OriginLaneID     string
	ScopePaths       []string
	PacketFile       string
}

type VerificationEvidence struct {
	Command  string `json:"command"`
	Result   string `json:"result"`
	Artifact string `json:"artifact,omitempty"`
}

type VerificationEvidenceList []VerificationEvidence

func (values *VerificationEvidenceList) UnmarshalJSON(data []byte) error {
	var structured []VerificationEvidence
	if err := json.Unmarshal(data, &structured); err == nil {
		*values = normalizeVerificationEvidence(structured)
		return nil
	}
	var strings []string
	if err := json.Unmarshal(data, &strings); err == nil {
		out := make([]VerificationEvidence, 0, len(strings))
		for _, value := range strings {
			out = append(out, verificationEvidenceFromText(value))
		}
		*values = normalizeVerificationEvidence(out)
		return nil
	}
	return fmt.Errorf("verification evidence must be an array of objects or strings")
}

type UpdateBoundaryInput struct {
	CommitRange        string   `json:"commit_range,omitempty"`
	InitialDirtyPaths  []string `json:"initial_dirty_paths,omitempty"`
	WorkflowOwnedPaths []string `json:"workflow_owned_paths,omitempty"`
}

type PayloadFileInput struct {
	Workflow                string                                `json:"workflow"`
	Reason                  string                                `json:"reason"`
	ChangedPaths            []string                              `json:"changed_paths"`
	PathChanges             []changemodel.PathChange              `json:"path_changes"`
	UnknownPathDispositions []changemodel.PathDispositionDecision `json:"unknown_path_dispositions"`
	ScopePaths              []string                              `json:"scope_paths"`
	BehaviorSurfaces        []string                              `json:"behavior_surfaces"`
	GeneratedSurfaces       []string                              `json:"generated_surfaces"`
	GeneratedSurfaceNote    []string                              `json:"generated_surface_notes"`
	StateContracts          []string                              `json:"state_contracts"`
	Verification            VerificationEvidenceList              `json:"verification"`
	VerificationEvidence    VerificationEvidenceList              `json:"verification_evidence"`
	KnownUnknowns           []string                              `json:"known_unknowns"`
	ConfidenceNotes         []string                              `json:"confidence_notes"`
	UserDecisions           []string                              `json:"user_decisions"`
	Boundary                UpdateBoundaryInput                   `json:"boundary"`
}

type UpdateInput struct {
	ChangedPaths      []string
	PathChanges       []changemodel.PathChange
	ScopePaths        []string
	Reason            string
	DeltaSessionID    string
	CommitRange       string
	PayloadFile       string
	Workflow          string
	BehaviorSurfaces  []string
	GeneratedSurfaces []string
	StateContracts    []string
	Verification      []VerificationEvidence
	KnownUnknowns     []string
	ConfidenceNotes   []string
	UserDecisions     []string
	Boundary          UpdateBoundaryInput
}

type StatusUpdate struct {
	Status                string   `json:"status"`
	Freshness             string   `json:"freshness"`
	Readiness             string   `json:"readiness"`
	RecommendedNextAction string   `json:"recommended_next_action"`
	Dirty                 bool     `json:"dirty"`
	StalePaths            []string `json:"stale_paths"`
	StaleReasons          []string `json:"stale_reasons"`
	LastUpdateID          string   `json:"last_update_id"`
	LastUpdateOutcome     string   `json:"last_update_outcome"`
}

const (
	ResultReady          = "ready"
	ResultNoOp           = "no_op"
	ResultPartialRefresh = "partial_refresh"
	ResultNeedsRebuild   = "needs_rebuild"
	ResultBlocked        = "blocked"
	ResultRecorded       = "recorded"
	validateBuildReceipt = "validate-build-receipt.json"
)

var closureNodeBudget = 1000

var errNoUpdateRecord = errors.New("no project cognition update record")

type ValidateBuildReceipt struct {
	Version            int    `json:"version"`
	Gate               string `json:"gate"`
	Status             string `json:"status"`
	Readiness          string `json:"readiness"`
	ActiveGenerationID string `json:"active_generation_id"`
	UpdateID           string `json:"update_id"`
	UpdateOutcome      string `json:"update_outcome"`
	ValidatedAt        string `json:"validated_at"`
}

type updateRecordRef struct {
	ID           string
	ResultState  string
	GenerationID string
	ChangedPaths []string
}

type UpdatePayload struct {
	Readiness               string                   `json:"readiness"`
	RecommendedNextAction   string                   `json:"recommended_next_action"`
	UpdateID                string                   `json:"update_id"`
	UpdateOutcome           string                   `json:"update_outcome"`
	ResultState             string                   `json:"result_state"`
	StatusUpdate            StatusUpdate             `json:"status_update"`
	ChangedPaths            []string                 `json:"changed_paths"`
	PathChanges             []changemodel.PathChange `json:"path_changes"`
	IgnoredPaths            []string                 `json:"ignored_paths"`
	AffectedNodes           []map[string]any         `json:"affected_nodes"`
	AffectedGraphClaims     []string                 `json:"affected_graph_claims"`
	ClosureTruncated        bool                     `json:"closure_truncated"`
	ClosureTruncationReason string                   `json:"closure_truncation_reason,omitempty"`
	MissingCoverage         []string                 `json:"missing_coverage"`
	AdoptedPaths            []string                 `json:"adopted_paths"`
	ReviewPaths             []string                 `json:"review_paths"`
	UnadoptablePaths        []string                 `json:"unadoptable_paths"`
	PartialRefreshReasons   []string                 `json:"partial_refresh_reasons"`
	KnownUnknowns           []string                 `json:"known_unknowns"`
	MinimalLiveReads        []string                 `json:"minimal_live_reads"`
	PathAdoption            map[string]any           `json:"path_adoption"`
	LastRefreshChangedBasis []string                 `json:"last_refresh_changed_files_basis"`
	Boundary                *boundary.Result         `json:"boundary,omitempty"`
}

func MarkDirty(paths rt.Paths, input DirtyInput) (rt.Status, error) {
	releaseUpdateLock, err := rt.AcquireUpdateLock(paths)
	if err != nil {
		return rt.Status{}, err
	}
	defer releaseUpdateLock()

	if err := blockSplitBrainBaseline(paths); err != nil {
		return rt.Status{}, err
	}
	if input.Reason == "" {
		input.Reason = "manual"
	}
	status, err := rt.ReadStatus(paths)
	if err != nil {
		return rt.Status{}, err
	}
	scope := append([]string{}, input.ScopePaths...)
	if input.PacketFile != "" {
		derived, err := ScopeFromPacket(input.PacketFile)
		if err != nil {
			return rt.Status{}, err
		}
		scope = append(scope, derived...)
	}
	status.Dirty = true
	status.Status = "stale"
	status.Freshness = rt.StaleFreshness
	status.Readiness = rt.BlockedReadiness
	status.RecommendedNextAction = "run_map_update"
	status.DirtyReasons = appendUnique(status.DirtyReasons, input.Reason)
	status.DirtyOriginCommand = input.OriginCommand
	status.DirtyOriginFeatureDir = input.OriginFeatureDir
	status.DirtyOriginLaneID = input.OriginLaneID
	status.DirtyScopePaths = appendUnique(status.DirtyScopePaths, normalizePaths(scope)...)
	status.StalePaths = appendUnique(status.StalePaths, status.DirtyScopePaths...)
	status.StaleReasons = appendUnique(status.StaleReasons, input.Reason)
	if err := rt.WriteStatus(paths, status); err != nil {
		return rt.Status{}, err
	}
	return status, nil
}

func ClearDirty(paths rt.Paths) (rt.Status, error) {
	return CompleteRefresh(paths, "clear-dirty")
}

func RecordRefresh(paths rt.Paths, reason string) (rt.Status, error) {
	releaseUpdateLock, err := rt.AcquireUpdateLock(paths)
	if err != nil {
		return rt.Status{}, err
	}
	defer releaseUpdateLock()
	return recordRefreshLocked(paths, reason)
}

func recordRefreshLocked(paths rt.Paths, reason string) (rt.Status, error) {
	if reason == "" {
		reason = "manual"
	}
	status, err := completeRefreshLocked(paths, "recorded")
	if err != nil {
		return rt.Status{}, err
	}
	status.LastRefreshReason = reason
	status.LastRefreshBasis = "recorded"
	if err := rt.WriteStatus(paths, status); err != nil {
		return rt.Status{}, err
	}
	return status, nil
}

func recordGitRefreshBaseline(paths rt.Paths, status *rt.Status) {
	if !rt.GitAvailable(paths.Root) {
		status.LastRefreshGitCommit = ""
		status.LastRefreshGitBranch = ""
		return
	}
	if commit, err := rt.GitHead(paths.Root); err == nil {
		status.LastRefreshGitCommit = commit
	}
	if branch, err := rt.GitBranch(paths.Root); err == nil {
		status.LastRefreshGitBranch = branch
	}
}

func CompleteRefresh(paths rt.Paths, basis string) (rt.Status, error) {
	releaseUpdateLock, err := rt.AcquireUpdateLock(paths)
	if err != nil {
		return rt.Status{}, err
	}
	defer releaseUpdateLock()
	return completeRefreshLocked(paths, basis)
}

func completeRefreshLocked(paths rt.Paths, basis string) (rt.Status, error) {
	agreement, ok := runtimegate.CheckExisting(paths)
	if !ok {
		return rt.Status{}, fmt.Errorf("project cognition agreement blocked: run_map_scan_build: status.json and project-cognition.db are missing")
	}
	if agreement.Status != "ok" && agreement.CauseCode != runtimegate.CauseUpdateFinalizationPending {
		return rt.Status{}, fmt.Errorf("project cognition agreement blocked: %s: %s", agreementAction(agreement), strings.Join(agreement.Errors, "; "))
	}
	status, err := rt.ReadStatus(paths)
	if err != nil {
		return rt.Status{}, err
	}
	if !refreshEligibleOutcome(status.LastUpdateOutcome) || strings.TrimSpace(status.LastUpdateID) == "" {
		return rt.Status{}, fmt.Errorf("complete refresh blocked: latest update outcome %q is not ready or no_op", status.LastUpdateOutcome)
	}
	latest, err := latestUpdateRecord(paths)
	if err != nil {
		return rt.Status{}, fmt.Errorf("complete refresh blocked: latest update record unavailable: %w", err)
	}
	if latest.ID != status.LastUpdateID || latest.ResultState != status.LastUpdateOutcome || latest.GenerationID != status.ActiveGenerationID {
		return rt.Status{}, fmt.Errorf("complete refresh blocked: status latest update %s/%s does not match database latest update %s/%s", status.LastUpdateID, status.LastUpdateOutcome, latest.ID, latest.ResultState)
	}
	if !finalizationEligibleStatus(status, latest) {
		return rt.Status{}, fmt.Errorf("complete refresh blocked: latest update %s left unresolved dirty or stale project cognition state", status.LastUpdateID)
	}
	receipt, err := readValidateBuildReceipt(paths)
	if err != nil {
		return rt.Status{}, fmt.Errorf("complete refresh blocked: run validate-build after the latest ready/no_op update: %w", err)
	}
	if receipt.Gate != "build_acceptance" || receipt.Status != "ok" || receipt.Readiness != rt.ReadyReadiness ||
		receipt.ActiveGenerationID != status.ActiveGenerationID || receipt.UpdateID != status.LastUpdateID || receipt.UpdateOutcome != status.LastUpdateOutcome {
		return rt.Status{}, fmt.Errorf("complete refresh blocked: validate-build receipt does not match latest update %s/%s", status.LastUpdateID, status.LastUpdateOutcome)
	}
	status.Status = "ok"
	status.Freshness = rt.ReadyFreshness
	status.Readiness = rt.ReadyReadiness
	status.RecommendedNextAction = "use_project_cognition"
	status.Dirty = false
	status.DirtyReasons = []string{}
	status.DirtyOriginCommand = ""
	status.DirtyOriginFeatureDir = ""
	status.DirtyOriginLaneID = ""
	status.DirtyScopePaths = []string{}
	status.StalePaths = []string{}
	status.StaleReasons = []string{}
	status.LastFinalizedUpdateID = status.LastUpdateID
	if basis == "" {
		basis = "validated-update"
	}
	status.LastRefreshBasis = basis
	recordGitRefreshBaseline(paths, &status)
	if err := rt.WriteStatus(paths, status); err != nil {
		return rt.Status{}, err
	}
	return status, nil
}

func RecordValidateBuildReceipt(paths rt.Paths, gateStatus string, gate string, readiness string) error {
	releaseUpdateLock, err := rt.AcquireUpdateLock(paths)
	if err != nil {
		return err
	}
	defer releaseUpdateLock()

	receiptPath := filepath.Join(paths.RuntimeDir, validateBuildReceipt)
	removeReceipt := func() error {
		if err := os.Remove(receiptPath); err != nil && !errors.Is(err, os.ErrNotExist) {
			return fmt.Errorf("remove stale validate-build receipt: %w", err)
		}
		return nil
	}
	if gateStatus != "ok" || gate != "build_acceptance" || readiness != rt.ReadyReadiness {
		return removeReceipt()
	}
	status, err := rt.ReadStatus(paths)
	if err != nil {
		return err
	}
	if !refreshEligibleOutcome(status.LastUpdateOutcome) || strings.TrimSpace(status.LastUpdateID) == "" {
		return removeReceipt()
	}
	latest, err := latestUpdateRecord(paths)
	if errors.Is(err, errNoUpdateRecord) || errors.Is(err, os.ErrNotExist) {
		return removeReceipt()
	}
	if err != nil {
		return err
	}
	if latest.ID != status.LastUpdateID || latest.ResultState != status.LastUpdateOutcome || latest.GenerationID != status.ActiveGenerationID || !finalizationEligibleStatus(status, latest) {
		return removeReceipt()
	}
	receipt := ValidateBuildReceipt{
		Version:            1,
		Gate:               gate,
		Status:             gateStatus,
		Readiness:          readiness,
		ActiveGenerationID: status.ActiveGenerationID,
		UpdateID:           status.LastUpdateID,
		UpdateOutcome:      status.LastUpdateOutcome,
		ValidatedAt:        time.Now().UTC().Format(time.RFC3339Nano),
	}
	data, err := json.MarshalIndent(receipt, "", "  ")
	if err != nil {
		return fmt.Errorf("encode validate-build receipt: %w", err)
	}
	if err := os.MkdirAll(paths.RuntimeDir, 0o755); err != nil {
		return fmt.Errorf("create runtime dir for validate-build receipt: %w", err)
	}
	if err := os.WriteFile(receiptPath, append(data, '\n'), 0o644); err != nil {
		return fmt.Errorf("write validate-build receipt: %w", err)
	}
	return nil
}

func readValidateBuildReceipt(paths rt.Paths) (ValidateBuildReceipt, error) {
	data, err := os.ReadFile(filepath.Join(paths.RuntimeDir, validateBuildReceipt))
	if err != nil {
		return ValidateBuildReceipt{}, err
	}
	var receipt ValidateBuildReceipt
	if err := json.Unmarshal(data, &receipt); err != nil {
		return ValidateBuildReceipt{}, fmt.Errorf("parse validate-build receipt: %w", err)
	}
	if receipt.Version != 1 {
		return ValidateBuildReceipt{}, fmt.Errorf("unsupported validate-build receipt version %d", receipt.Version)
	}
	return receipt, nil
}

func latestUpdateRecord(paths rt.Paths) (updateRecordRef, error) {
	st, err := store.OpenExisting(paths)
	if err != nil {
		return updateRecordRef{}, err
	}
	defer st.Close()
	generationID, err := st.ActiveGenerationID(context.Background())
	if err != nil {
		return updateRecordRef{}, err
	}
	var record updateRecordRef
	var changedPathsJSON string
	err = st.DB().QueryRowContext(context.Background(), `SELECT id, result_state, changed_paths_json FROM updates WHERE generation_id = ? ORDER BY completed_at DESC, id DESC LIMIT 1`, generationID).Scan(&record.ID, &record.ResultState, &changedPathsJSON)
	if errors.Is(err, sql.ErrNoRows) {
		return updateRecordRef{}, errNoUpdateRecord
	}
	if err != nil {
		return updateRecordRef{}, fmt.Errorf("read latest project cognition update: %w", err)
	}
	if strings.TrimSpace(changedPathsJSON) != "" {
		if err := json.Unmarshal([]byte(changedPathsJSON), &record.ChangedPaths); err != nil {
			return updateRecordRef{}, fmt.Errorf("parse latest project cognition update changed paths: %w", err)
		}
	}
	record.ChangedPaths = normalizePaths(record.ChangedPaths)
	record.GenerationID = generationID
	return record, nil
}

func refreshEligibleOutcome(outcome string) bool {
	return outcome == ResultReady || outcome == ResultNoOp
}

func cleanRefreshStatus(status rt.Status) bool {
	return status.Status == "ok" && status.Freshness == rt.ReadyFreshness && status.Readiness == rt.ReadyReadiness && status.GraphReady &&
		!status.Dirty && len(status.DirtyReasons) == 0 && len(status.DirtyScopePaths) == 0 && len(status.StalePaths) == 0 && len(status.StaleReasons) == 0
}

func finalizationEligibleStatus(status rt.Status, latest updateRecordRef) bool {
	if cleanRefreshStatus(status) {
		return true
	}
	if status.Status != "stale" || status.Freshness != rt.StaleFreshness || status.Readiness != rt.ReviewReadiness ||
		status.RecommendedNextAction != "review_project_cognition_update" || !status.GraphReady || !status.Dirty ||
		status.DirtyOriginCommand != "specify-runtime cognition repair-status" || status.DirtyOriginFeatureDir != "" || status.DirtyOriginLaneID != "" {
		return false
	}
	dirtyReasons := compactStrings(status.DirtyReasons)
	staleReasons := compactStrings(status.StaleReasons)
	if len(dirtyReasons) != 1 || dirtyReasons[0] != runtimegate.LatestUpdateMismatchRepairReason ||
		len(staleReasons) != 1 || staleReasons[0] != runtimegate.LatestUpdateMismatchRepairReason {
		return false
	}
	return sameNormalizedPaths(status.DirtyScopePaths, latest.ChangedPaths) &&
		sameNormalizedPaths(status.StalePaths, latest.ChangedPaths) &&
		sameNormalizedPaths(status.LastRefreshChangedFilesBasis, latest.ChangedPaths)
}

func sameNormalizedPaths(left []string, right []string) bool {
	left = normalizePaths(left)
	right = normalizePaths(right)
	if len(left) != len(right) {
		return false
	}
	for index := range left {
		if left[index] != right[index] {
			return false
		}
	}
	return true
}

func RefreshTopics(paths rt.Paths, topics []string, reason string) (rt.Status, error) {
	releaseUpdateLock, err := rt.AcquireUpdateLock(paths)
	if err != nil {
		return rt.Status{}, err
	}
	defer releaseUpdateLock()

	if err := blockSplitBrainBaseline(paths); err != nil {
		return rt.Status{}, err
	}
	if reason == "" {
		reason = "topic-refresh"
	}
	status, err := recordRefreshLocked(paths, reason)
	if err != nil {
		return rt.Status{}, err
	}
	status.LastRefreshChangedFilesBasis = appendUnique(status.LastRefreshChangedFilesBasis, normalizePaths(topics)...)
	if err := rt.WriteStatus(paths, status); err != nil {
		return rt.Status{}, err
	}
	return status, nil
}

func RunUpdate(paths rt.Paths, input UpdateInput) (UpdatePayload, error) {
	releaseUpdateLock, err := rt.AcquireUpdateLock(paths)
	if err != nil {
		return UpdatePayload{}, err
	}
	defer releaseUpdateLock()

	if err := blockSplitBrainBaseline(paths); err != nil {
		return UpdatePayload{}, err
	}
	if input.PayloadFile != "" {
		payload, err := loadPayloadFile(input.PayloadFile)
		if err != nil {
			return UpdatePayload{}, err
		}
		input = applyPayloadFileInput(input, payload)
	}
	if input.DeltaSessionID != "" {
		return runDeltaSessionUpdate(paths, input)
	}
	pathChanges, err := normalizePathChanges(input.PathChanges)
	if err != nil {
		return UpdatePayload{}, err
	}
	input.PathChanges = pathChanges
	changed := append([]string{}, input.ChangedPaths...)
	changed = append(changed, input.ScopePaths...)
	for _, change := range pathChanges {
		changed = append(changed, change.Path)
	}
	if len(changed) == 0 {
		derived, err := rt.GitChangedPaths(paths.Root)
		if err != nil {
			return UpdatePayload{}, err
		}
		changed = derived
	}
	changed = normalizePaths(changed)
	matcher := ignore.Load(paths.Root)
	kept, ignored := matcher.Filter(changed)
	kept = normalizePaths(kept)
	ignored = normalizePaths(ignored)
	input.PathChanges, kept = convertIgnoredRenameTargetsToDeletes(input.PathChanges, kept, ignored)
	input.PathChanges = filterPathChanges(input.PathChanges, kept)
	if err := validateChangedPaths(kept); err != nil {
		return UpdatePayload{}, err
	}
	return runResolvedUpdate(paths, input, kept, ignored, nil)
}

func blockSplitBrainBaseline(paths rt.Paths) error {
	return runtimegate.BlockIfExisting(paths)
}

func agreementAction(agreement runtimegate.Agreement) string {
	if agreement.RecoveryAction != "" {
		return agreement.RecoveryAction
	}
	return agreement.RecommendedNextAction
}

func runResolvedUpdate(paths rt.Paths, input UpdateInput, changed []string, ignored []string, boundaryResult *boundary.Result) (UpdatePayload, error) {
	changed = normalizePaths(changed)
	ignored = normalizePaths(ignored)
	ignoredDispositionChanges := pathChangesWithDisposition(input.PathChanges, changemodel.DispositionIgnored)
	pathChanges, ignoredByDisposition := splitIgnoredPathChanges(input.PathChanges)
	input.PathChanges = pathChanges
	ignored = normalizePaths(append(ignored, ignoredByDisposition...))
	changed = subtractStrings(changed, ignoredByDisposition)
	if err := validateChangedPaths(changed); err != nil {
		return UpdatePayload{}, err
	}
	input.Verification = normalizeVerificationEvidence(input.Verification)
	if err := validateVerificationEvidence(input.Verification); err != nil {
		return UpdatePayload{}, err
	}
	baselineStatus, err := requireUpdateBaseline(paths)
	if err != nil {
		return UpdatePayload{}, err
	}
	updateID := "upd-" + time.Now().UTC().Format("20060102T150405.000000000Z")

	st, err := store.OpenExisting(paths)
	if err != nil {
		return UpdatePayload{}, err
	}
	defer st.Close()

	lookupPaths := pathChangeLookupPaths(changed, input.PathChanges)
	pathNodeIDs, err := st.NodeIDsForExactPaths(context.Background(), lookupPaths)
	if err != nil {
		return UpdatePayload{}, err
	}
	input.PathChanges = completePathChanges(changed, input.PathChanges, pathNodeIDs)
	auditPathChanges := append([]changemodel.PathChange{}, input.PathChanges...)
	auditPathChanges = append(auditPathChanges, ignoredDispositionChanges...)
	sort.Slice(auditPathChanges, func(i, j int) bool { return auditPathChanges[i].Path < auditPathChanges[j].Path })
	if err := validatePathChangesAgainstRuntime(input.PathChanges, pathNodeIDs); err != nil {
		return UpdatePayload{}, err
	}
	refreshScopePaths := pathChangeLookupPaths(changed, input.PathChanges)
	graphChanges := graphMutationPathChanges(input.PathChanges)
	closurePaths := pathChangeLookupPaths(graphMutationPaths(graphChanges), graphChanges)
	closure, err := st.AffectedClosureForPathsAndNodeIDsWithBudget(context.Background(), closurePaths, pathChangeNodeIDs(graphChanges), store.ClosureBudget{MaxNodes: closureNodeBudget})
	if err != nil {
		return UpdatePayload{}, err
	}
	nodes, err := st.NodesForIDs(context.Background(), closure.NodeIDs)
	if err != nil {
		return UpdatePayload{}, err
	}
	resultState := constrainResultStateByBaseline(typedUpdateResultState(changed, input, closure, pathNodeIDs), baselineStatus, refreshScopePaths, input.Reason)
	typedResult, err := st.ApplyTypedUpdate(context.Background(), store.TypedUpdate{
		Record: store.UpdateRecord{
			ID:             updateID,
			Trigger:        input.Reason,
			ChangedPaths:   graphMutationPaths(input.PathChanges),
			AffectedNodes:  closure.NodeIDs,
			AffectedClaims: closure.ClaimIDs,
			AffectedSlices: closure.SliceIDs,
			ResultState:    resultState,
			Attrs: map[string]any{
				"generated_surfaces": input.GeneratedSurfaces,
				"state_contracts":    input.StateContracts,
				"known_unknowns":     input.KnownUnknowns,
				"confidence_notes":   input.ConfidenceNotes,
				"boundary":           boundaryResult,
				"closure_truncated":  closure.Truncated,
			},
		},
		PathChanges:      auditPathChanges,
		Workflow:         input.Workflow,
		BehaviorSurfaces: input.BehaviorSurfaces,
		Verification:     verificationAttrs(input.Verification),
		Reason:           input.Reason,
	})
	if err != nil {
		return UpdatePayload{}, err
	}
	postClosure, err := st.AffectedClosureForPathsWithBudget(context.Background(), closurePaths, store.ClosureBudget{MaxNodes: closureNodeBudget})
	if err != nil {
		return UpdatePayload{}, err
	}
	closure = mergeAffectedClosures(closure, postClosure, typedResult.AffectedNodeIDs)
	nodes, err = st.NodesForIDs(context.Background(), closure.NodeIDs)
	if err != nil {
		return UpdatePayload{}, err
	}
	pathNodeIDs, err = st.NodeIDsForExactPaths(context.Background(), lookupPaths)
	if err != nil {
		return UpdatePayload{}, err
	}

	status, err := rt.ReadStatus(paths)
	if err != nil {
		return UpdatePayload{}, err
	}
	status = applyResultState(status, resultState, updateID, refreshScopePaths, input.Reason)
	if input.DeltaSessionID != "" {
		status.LastDeltaSessionID = input.DeltaSessionID
	}
	if boundaryResult != nil {
		status.LastUpdateBoundary = boundaryResult.BoundarySource
	}
	if err := rt.WriteStatus(paths, status); err != nil {
		return UpdatePayload{}, err
	}

	pathAccounting := updatePathAccounting(changed, ignored)
	if boundaryResult != nil {
		pathAccounting = boundaryResult.PathAccounting
	}
	reviewPaths := reviewOnlyPaths(input.PathChanges)
	if resultState != ResultReady && len(reviewPaths) == 0 {
		reviewPaths = append([]string{}, changed...)
	}
	if boundaryResult != nil && resultState != ResultReady {
		reviewPaths = appendUnique(reviewPaths, boundaryResult.AmbiguousPaths...)
	}
	partialRefreshReasons := updateResultReasons(resultState, changed, nodes, input, pathNodeIDs, true, baselineStatus, refreshScopePaths)
	partialRefreshReasons = appendUnique(partialRefreshReasons, pathChangePartialReasons(input.PathChanges, closure)...)
	knownUnknowns := compactStrings(input.KnownUnknowns)
	if boundaryResult != nil {
		knownUnknowns = compactStrings(append(knownUnknowns, boundaryResult.Warnings...))
	}
	pathAdoption := map[string]any{
		"adopted":         typedResult.AdoptedPaths,
		"refreshed":       typedResult.RefreshedPaths,
		"renamed":         typedResult.RenamedPaths,
		"deleted":         typedResult.DeletedPaths,
		"ignored":         ignored,
		"needs_review":    reviewPaths,
		"path_accounting": pathAccounting,
	}
	if len(partialRefreshReasons) > 0 {
		pathAdoption["partial_refresh_reasons"] = partialRefreshReasons
	}
	if boundaryResult != nil {
		pathAdoption["phase"] = "boundary_resolved"
		pathAdoption["auto_commit_decision"] = boundaryResult.AutoCommitDecision
	}
	return UpdatePayload{
		Readiness:               status.Readiness,
		RecommendedNextAction:   status.RecommendedNextAction,
		UpdateID:                updateID,
		UpdateOutcome:           boundaryOutcome(boundaryResult),
		ResultState:             resultState,
		StatusUpdate:            statusUpdateFromStatus(status),
		ChangedPaths:            append([]string{}, changed...),
		PathChanges:             append([]changemodel.PathChange{}, auditPathChanges...),
		IgnoredPaths:            ignored,
		AffectedNodes:           nodes,
		AffectedGraphClaims:     append([]string{}, closure.ClaimIDs...),
		ClosureTruncated:        closure.Truncated,
		ClosureTruncationReason: closure.TruncationReason,
		MissingCoverage:         []string{},
		AdoptedPaths:            append([]string{}, typedResult.AdoptedPaths...),
		ReviewPaths:             reviewPaths,
		UnadoptablePaths:        blockingDispositionPaths(input.PathChanges),
		PartialRefreshReasons:   partialRefreshReasons,
		KnownUnknowns:           knownUnknowns,
		MinimalLiveReads:        append([]string{}, reviewPaths...),
		PathAdoption:            pathAdoption,
		LastRefreshChangedBasis: append([]string{}, refreshScopePaths...),
		Boundary:                boundaryResult,
	}, nil
}

func requireUpdateBaseline(paths rt.Paths) (rt.Status, error) {
	agreement, ok := runtimegate.CheckExisting(paths)
	if !ok {
		return rt.Status{}, fmt.Errorf("project cognition update blocked: run_map_scan_build: status.json and project-cognition.db are missing")
	}
	if agreement.Status != "ok" {
		return rt.Status{}, fmt.Errorf("project cognition update blocked: %s: %s", agreementAction(agreement), strings.Join(agreement.Errors, "; "))
	}
	status, err := rt.ReadStatus(paths)
	if err != nil {
		return rt.Status{}, err
	}
	if status.Status == "missing" || status.Freshness == rt.MissingFreshness || status.Readiness == rt.NeedsRebuildReadiness || !status.GraphReady || status.ActiveGenerationID == "" {
		return rt.Status{}, fmt.Errorf("project cognition update blocked: run_map_scan_build: baseline is missing or needs_rebuild")
	}
	return status, nil
}

func statusUpdateFromStatus(status rt.Status) StatusUpdate {
	return StatusUpdate{
		Status:                status.Status,
		Freshness:             status.Freshness,
		Readiness:             status.Readiness,
		RecommendedNextAction: status.RecommendedNextAction,
		Dirty:                 status.Dirty,
		StalePaths:            append([]string{}, status.StalePaths...),
		StaleReasons:          append([]string{}, status.StaleReasons...),
		LastUpdateID:          status.LastUpdateID,
		LastUpdateOutcome:     status.LastUpdateOutcome,
	}
}

func typedUpdateResultState(changed []string, input UpdateInput, closure store.AffectedClosure, pathNodeIDs map[string]string) string {
	if len(changed) == 0 {
		return ResultNoOp
	}
	if closure.Truncated || !hasPassingVerification(input.Verification) || len(blockingKnownUnknowns(input.KnownUnknowns)) > 0 {
		return ResultPartialRefresh
	}
	for _, change := range input.PathChanges {
		if change.Disposition == nil || *change.Disposition != changemodel.DispositionAdoptable {
			return ResultPartialRefresh
		}
		switch change.Operation {
		case changemodel.OperationAdd:
			continue
		case changemodel.OperationRename:
			if change.NodeID == "" && pathNodeIDs[change.OldPath] == "" {
				return ResultPartialRefresh
			}
		case changemodel.OperationModify, changemodel.OperationDelete:
			if change.NodeID == "" && pathNodeIDs[change.Path] == "" {
				return ResultPartialRefresh
			}
		default:
			return ResultPartialRefresh
		}
	}
	return ResultReady
}

func splitIgnoredPathChanges(values []changemodel.PathChange) ([]changemodel.PathChange, []string) {
	kept := make([]changemodel.PathChange, 0, len(values))
	ignored := []string{}
	for _, value := range values {
		if value.Disposition != nil && *value.Disposition == changemodel.DispositionIgnored {
			ignored = append(ignored, value.Path)
			continue
		}
		kept = append(kept, value)
	}
	return kept, normalizePaths(ignored)
}

func pathChangesWithDisposition(values []changemodel.PathChange, disposition changemodel.Disposition) []changemodel.PathChange {
	out := []changemodel.PathChange{}
	for _, value := range values {
		if value.Disposition != nil && *value.Disposition == disposition {
			out = append(out, value)
		}
	}
	return out
}

func pathChangeLookupPaths(changed []string, values []changemodel.PathChange) []string {
	paths := append([]string{}, changed...)
	for _, value := range values {
		paths = append(paths, value.Path)
		if value.OldPath != "" {
			paths = append(paths, value.OldPath)
		}
	}
	return normalizePaths(paths)
}

func completePathChanges(changed []string, values []changemodel.PathChange, pathNodeIDs map[string]string) []changemodel.PathChange {
	out := make([]changemodel.PathChange, 0, len(changed)+len(values))
	seen := make(map[string]bool, len(changed)+len(values))
	for _, value := range values {
		if value.NodeID == "" {
			value.NodeID = pathNodeIDs[value.Path]
			if value.NodeID == "" && value.Operation == changemodel.OperationRename {
				value.NodeID = pathNodeIDs[value.OldPath]
			}
		}
		out = append(out, value)
		seen[value.Path] = true
	}
	for _, path := range changed {
		if seen[path] {
			continue
		}
		nodeID := pathNodeIDs[path]
		operation := changemodel.OperationModify
		disposition := changemodel.DispositionAdoptable
		if nodeID == "" {
			operation = changemodel.OperationAdd
			disposition = changemodel.DispositionReviewOnly
		}
		out = append(out, changemodel.PathChange{
			Path:        path,
			Operation:   operation,
			NodeID:      nodeID,
			Disposition: &disposition,
		})
	}
	sort.Slice(out, func(i, j int) bool { return out[i].Path < out[j].Path })
	return out
}

func validatePathChangesAgainstRuntime(values []changemodel.PathChange, pathNodeIDs map[string]string) error {
	for _, value := range values {
		if !value.MutatesGraph() {
			continue
		}
		switch value.Operation {
		case changemodel.OperationAdd:
			if pathNodeIDs[value.Path] != "" {
				return fmt.Errorf("path change %s cannot add: active path coverage already exists", value.Path)
			}
		case changemodel.OperationModify, changemodel.OperationDelete:
			if pathNodeIDs[value.Path] == "" {
				return fmt.Errorf("path change %s cannot %s: active path coverage is missing", value.Path, value.Operation)
			}
		case changemodel.OperationRename:
			if pathNodeIDs[value.OldPath] == "" {
				return fmt.Errorf("path change %s cannot rename: old_path %s lacks active path coverage", value.Path, value.OldPath)
			}
			if pathNodeIDs[value.Path] != "" {
				return fmt.Errorf("path change %s cannot rename: target already has active path coverage", value.Path)
			}
		}
	}
	return nil
}

func mergeAffectedClosures(left store.AffectedClosure, right store.AffectedClosure, nodeIDs []string) store.AffectedClosure {
	merged := store.AffectedClosure{
		NodeIDs:            appendUnique(append([]string{}, left.NodeIDs...), append(right.NodeIDs, nodeIDs...)...),
		ClaimIDs:           appendUnique(append([]string{}, left.ClaimIDs...), right.ClaimIDs...),
		SliceIDs:           appendUnique(append([]string{}, left.SliceIDs...), right.SliceIDs...),
		TraversedEdgeTypes: appendUnique(append([]string{}, left.TraversedEdgeTypes...), right.TraversedEdgeTypes...),
		Truncated:          left.Truncated || right.Truncated,
	}
	if left.TruncationReason != "" {
		merged.TruncationReason = left.TruncationReason
	} else {
		merged.TruncationReason = right.TruncationReason
	}
	return merged
}

func reviewOnlyPaths(values []changemodel.PathChange) []string {
	paths := []string{}
	for _, value := range values {
		if value.Disposition != nil && (*value.Disposition == changemodel.DispositionReviewOnly || *value.Disposition == changemodel.DispositionBlockingKnownUnknown) {
			paths = append(paths, value.Path)
		}
	}
	return normalizePaths(paths)
}

func graphMutationPaths(values []changemodel.PathChange) []string {
	paths := []string{}
	for _, value := range values {
		if value.MutatesGraph() {
			paths = append(paths, value.Path)
		}
	}
	return normalizePaths(paths)
}

func graphMutationPathChanges(values []changemodel.PathChange) []changemodel.PathChange {
	out := make([]changemodel.PathChange, 0, len(values))
	for _, value := range values {
		if value.MutatesGraph() {
			out = append(out, value)
		}
	}
	return out
}

func pathChangeNodeIDs(values []changemodel.PathChange) []string {
	nodeIDs := []string{}
	for _, value := range values {
		if value.NodeID != "" {
			nodeIDs = append(nodeIDs, value.NodeID)
		}
	}
	return compactStrings(nodeIDs)
}

func blockingDispositionPaths(values []changemodel.PathChange) []string {
	paths := []string{}
	for _, value := range values {
		if value.Disposition != nil && *value.Disposition == changemodel.DispositionBlockingKnownUnknown {
			paths = append(paths, value.Path)
		}
	}
	return normalizePaths(paths)
}

func pathChangePartialReasons(values []changemodel.PathChange, closure store.AffectedClosure) []string {
	reasons := []string{}
	for _, value := range values {
		if value.Disposition == nil {
			reasons = append(reasons, "path_disposition_missing")
			continue
		}
		switch *value.Disposition {
		case changemodel.DispositionReviewOnly:
			reasons = append(reasons, "review_only_paths_present")
		case changemodel.DispositionBlockingKnownUnknown:
			reasons = append(reasons, "blocking_path_dispositions_present")
		}
	}
	if closure.Truncated {
		reason := strings.TrimSpace(closure.TruncationReason)
		if reason == "" {
			reason = "truncated"
		}
		reasons = append(reasons, "affected_closure_"+reason)
	}
	return compactStrings(reasons)
}

func updateResultReasons(resultState string, kept []string, nodes []map[string]any, input UpdateInput, pathNodeIDs map[string]string, hasStore bool, baselineStatus rt.Status, refreshScopePaths []string) []string {
	if resultState != ResultPartialRefresh {
		return []string{}
	}
	reasons := []string{}
	if !hasStore {
		reasons = append(reasons, "missing_project_cognition_db")
	}
	if len(nodes) == 0 {
		reasons = append(reasons, "no_affected_nodes_for_changed_paths")
	}
	if len(kept) > 0 && !allPathsMapped(kept, pathNodeIDs) {
		reasons = append(reasons, "changed_paths_missing_active_path_index")
	}
	if !hasPassingVerification(input.Verification) {
		reasons = append(reasons, "missing_passing_verification_result")
	}
	if len(blockingKnownUnknowns(input.KnownUnknowns)) > 0 {
		reasons = append(reasons, "blocking_known_unknowns_present")
	}
	if baselineHasUnresolvedState(baselineStatus, refreshScopePaths, input.Reason) {
		reasons = append(reasons, "existing_project_cognition_stale_or_dirty")
	}
	return compactStrings(reasons)
}

func constrainResultStateByBaseline(resultState string, status rt.Status, changedPaths []string, reason string) string {
	if resultState != ResultReady && resultState != ResultNoOp {
		return resultState
	}
	if baselineHasUnresolvedState(status, changedPaths, reason) {
		return ResultPartialRefresh
	}
	return resultState
}

func baselineHasUnresolvedState(status rt.Status, changedPaths []string, reason string) bool {
	remainingStalePaths := subtractStrings(status.StalePaths, changedPaths)
	remainingDirtyScope := subtractStrings(status.DirtyScopePaths, changedPaths)
	remainingStaleReasons := subtractStrings(status.StaleReasons, []string{reason})
	remainingDirtyReasons := subtractStrings(status.DirtyReasons, []string{reason})
	if len(remainingStalePaths) > 0 || len(remainingDirtyScope) > 0 || len(remainingStaleReasons) > 0 || len(remainingDirtyReasons) > 0 {
		return true
	}
	if status.Dirty && len(status.DirtyScopePaths) == 0 && len(status.DirtyReasons) == 0 {
		return true
	}
	return false
}

func allPathsMapped(paths []string, pathNodeIDs map[string]string) bool {
	if len(paths) == 0 {
		return false
	}
	for _, path := range paths {
		if pathNodeIDs[path] == "" {
			return false
		}
	}
	return true
}

func hasPassingVerification(values []VerificationEvidence) bool {
	for _, value := range values {
		if strings.TrimSpace(value.Command) != "" && verificationResultPassed(value.Result) {
			return true
		}
	}
	return false
}

func verificationResultPassed(value string) bool {
	return strings.TrimSpace(value) == "passed"
}

func validateVerificationEvidence(values []VerificationEvidence) error {
	for index, value := range values {
		if strings.TrimSpace(value.Command) == "" {
			return fmt.Errorf("invalid verification evidence %d: command is required", index+1)
		}
		switch strings.TrimSpace(value.Result) {
		case "passed", "failed", ResultRecorded:
		default:
			return fmt.Errorf("invalid verification evidence %d: result must be passed, failed, or recorded", index+1)
		}
	}
	return nil
}

func verificationAttrs(values []VerificationEvidence) []map[string]string {
	out := make([]map[string]string, 0, len(values))
	for _, value := range values {
		item := map[string]string{}
		if strings.TrimSpace(value.Command) != "" {
			item["command"] = strings.TrimSpace(value.Command)
		}
		if strings.TrimSpace(value.Result) != "" {
			item["result"] = strings.TrimSpace(value.Result)
		}
		if strings.TrimSpace(value.Artifact) != "" {
			item["artifact"] = strings.TrimSpace(value.Artifact)
		}
		if len(item) > 0 {
			out = append(out, item)
		}
	}
	return out
}

func applyResultState(status rt.Status, resultState string, updateID string, changedPaths []string, reason string) rt.Status {
	status.LastUpdateID = updateID
	status.LastUpdateOutcome = resultState
	status.LastRefreshChangedFilesBasis = append([]string{}, changedPaths...)
	switch resultState {
	case ResultReady:
		status.Status = "ok"
		status.Freshness = rt.ReadyFreshness
		status.Readiness = rt.ReadyReadiness
		status.RecommendedNextAction = "use_project_cognition"
		status.Dirty = false
		status.DirtyReasons = []string{}
		status.DirtyOriginCommand = ""
		status.DirtyOriginFeatureDir = ""
		status.DirtyOriginLaneID = ""
		status.DirtyScopePaths = []string{}
		status.StalePaths = subtractStrings(status.StalePaths, changedPaths)
		status.StaleReasons = subtractStrings(status.StaleReasons, []string{reason})
	case ResultNoOp:
		if status.Status == "" {
			status.Status = "ok"
		}
		if status.Freshness == "" || status.Freshness == rt.MissingFreshness {
			status.Freshness = rt.ReadyFreshness
		}
		if status.Readiness == "" {
			status.Readiness = rt.ReadyReadiness
		}
		if status.RecommendedNextAction == "" {
			status.RecommendedNextAction = "use_project_cognition"
		}
	case ResultPartialRefresh:
		status.Status = "stale"
		status.Freshness = rt.PartialRefreshFreshness
		status.Readiness = rt.ReviewReadiness
		status.RecommendedNextAction = "review_project_cognition_update"
		status.Dirty = true
		status.StalePaths = appendUnique(status.StalePaths, changedPaths...)
		status.StaleReasons = appendUnique(status.StaleReasons, reason)
	case ResultNeedsRebuild:
		status.Status = "stale"
		status.Freshness = rt.StaleFreshness
		status.Readiness = rt.NeedsRebuildReadiness
		status.RecommendedNextAction = "run_map_scan_build"
		status.Dirty = true
		status.StalePaths = appendUnique(status.StalePaths, changedPaths...)
		status.StaleReasons = appendUnique(status.StaleReasons, reason)
	default:
		status.Status = "stale"
		status.Freshness = rt.StaleFreshness
		status.Readiness = rt.BlockedReadiness
		status.RecommendedNextAction = "review_project_cognition_update"
		status.Dirty = true
		status.StalePaths = appendUnique(status.StalePaths, changedPaths...)
		status.StaleReasons = appendUnique(status.StaleReasons, reason)
	}
	return status
}

func boundaryOutcome(result *boundary.Result) string {
	if result == nil {
		return ""
	}
	return result.Outcome
}

func blockingKnownUnknowns(values []string) []string {
	out := make([]string, 0, len(values))
	for _, value := range compactStrings(values) {
		if isNonBlockingBoundaryWarning(value) {
			continue
		}
		out = append(out, value)
	}
	return out
}

func isNonBlockingBoundaryWarning(value string) bool {
	lower := strings.ToLower(value)
	return strings.Contains(lower, "auto-commit") || isNonBlockingCloseoutScopeNote(lower)
}

func isNonBlockingCloseoutScopeNote(lower string) bool {
	hasExplicitScope := strings.Contains(lower, "explicit path") ||
		strings.Contains(lower, "workflow-owned") ||
		strings.Contains(lower, "workflow owned") ||
		strings.Contains(lower, "explicitly scoped") ||
		strings.Contains(lower, "显式路径") ||
		strings.Contains(lower, "工作流拥有")
	hasUnrelatedDirtyWorkspace := (strings.Contains(lower, "unrelated") &&
		(strings.Contains(lower, "dirty") || strings.Contains(lower, "working tree") || strings.Contains(lower, "workspace"))) ||
		(strings.Contains(lower, "无关") && (strings.Contains(lower, "脏") || strings.Contains(lower, "工作区")))
	hasDisabledBroadScan := strings.Contains(lower, "include-working-tree=false") ||
		strings.Contains(lower, "include_working_tree=false") ||
		strings.Contains(lower, "include-untracked=false") ||
		strings.Contains(lower, "include_untracked=false")
	return hasExplicitScope && (hasUnrelatedDirtyWorkspace || hasDisabledBroadScan)
}

func loadPayloadFile(path string) (PayloadFileInput, error) {
	if strings.TrimSpace(path) == "" {
		return PayloadFileInput{}, nil
	}
	data, err := os.ReadFile(path)
	if err != nil {
		return PayloadFileInput{}, fmt.Errorf("read update payload file: %w", err)
	}
	var payload PayloadFileInput
	if err := json.Unmarshal(data, &payload); err != nil {
		return PayloadFileInput{}, fmt.Errorf("parse update payload file: %w", err)
	}
	payload.ChangedPaths = normalizePaths(payload.ChangedPaths)
	for index := range payload.PathChanges {
		payload.PathChanges[index].Path = normalizePathValue(payload.PathChanges[index].Path)
		payload.PathChanges[index].OldPath = normalizePathValue(payload.PathChanges[index].OldPath)
	}
	for index := range payload.UnknownPathDispositions {
		payload.UnknownPathDispositions[index].Path = normalizePathValue(payload.UnknownPathDispositions[index].Path)
		if payload.UnknownPathDispositions[index].AgentDisposition != nil {
			disposition := changemodel.Disposition(strings.TrimSpace(string(*payload.UnknownPathDispositions[index].AgentDisposition)))
			payload.UnknownPathDispositions[index].AgentDisposition = &disposition
		}
	}
	resolvedPathChanges, err := changemodel.ResolvePathDispositions(payload.PathChanges, payload.UnknownPathDispositions)
	if err != nil {
		return PayloadFileInput{}, err
	}
	pathChanges, err := normalizePathChanges(resolvedPathChanges)
	if err != nil {
		return PayloadFileInput{}, err
	}
	payload.PathChanges = pathChanges
	payload.ScopePaths = normalizePaths(payload.ScopePaths)
	payload.GeneratedSurfaces = normalizePaths(append(payload.GeneratedSurfaces, payload.GeneratedSurfaceNote...))
	payload.Verification = normalizeVerificationEvidence(append(payload.Verification, payload.VerificationEvidence...))
	payload.KnownUnknowns = compactStrings(payload.KnownUnknowns)
	payload.ConfidenceNotes = compactStrings(payload.ConfidenceNotes)
	return payload, nil
}

func applyPayloadFileInput(input UpdateInput, payload PayloadFileInput) UpdateInput {
	if payload.Workflow != "" {
		input.Workflow = payload.Workflow
	}
	if payload.Reason != "" && input.Reason == "" {
		input.Reason = payload.Reason
	}
	input.ChangedPaths = append(input.ChangedPaths, payload.ChangedPaths...)
	input.PathChanges = append(input.PathChanges, payload.PathChanges...)
	input.ScopePaths = append(input.ScopePaths, payload.ScopePaths...)
	input.BehaviorSurfaces = append(input.BehaviorSurfaces, payload.BehaviorSurfaces...)
	input.GeneratedSurfaces = append(input.GeneratedSurfaces, payload.GeneratedSurfaces...)
	input.StateContracts = append(input.StateContracts, payload.StateContracts...)
	input.Verification = append(input.Verification, payload.Verification...)
	input.KnownUnknowns = append(input.KnownUnknowns, payload.KnownUnknowns...)
	input.ConfidenceNotes = append(input.ConfidenceNotes, payload.ConfidenceNotes...)
	input.UserDecisions = append(input.UserDecisions, payload.UserDecisions...)
	if payload.Boundary.CommitRange != "" {
		input.Boundary = payload.Boundary
	}
	return input
}

func applyDeltaBundleInput(input UpdateInput, bundle delta.Bundle) UpdateInput {
	if input.Workflow == "" {
		input.Workflow = bundle.Session.OriginCommand
	}
	input.Boundary.InitialDirtyPaths = append(input.Boundary.InitialDirtyPaths, bundle.Session.Git.InitialDirtyPaths...)
	for _, event := range bundle.Events {
		input.PathChanges = append(input.PathChanges, event.PathChanges...)
		input.BehaviorSurfaces = append(input.BehaviorSurfaces, event.BehaviorSurfaces...)
		input.GeneratedSurfaces = append(input.GeneratedSurfaces, event.GeneratedSurfaces...)
		input.KnownUnknowns = append(input.KnownUnknowns, event.KnownUnknowns...)
		input.ConfidenceNotes = append(input.ConfidenceNotes, event.OwnerConsumers...)
		if event.Confidence != "" {
			input.ConfidenceNotes = append(input.ConfidenceNotes, event.Confidence)
		}
		for _, evidence := range event.Verification {
			input.Verification = append(input.Verification, verificationEvidenceFromDelta(evidence))
		}
	}
	input.BehaviorSurfaces = compactStrings(input.BehaviorSurfaces)
	input.GeneratedSurfaces = compactStrings(input.GeneratedSurfaces)
	input.KnownUnknowns = compactStrings(input.KnownUnknowns)
	input.ConfidenceNotes = compactStrings(input.ConfidenceNotes)
	return input
}

func updateInputFromBoundary(input UpdateInput, result boundary.Result) UpdateInput {
	input.ChangedPaths = append(input.ChangedPaths, result.ChangedPaths...)
	input.KnownUnknowns = append(input.KnownUnknowns, blockingBoundaryWarnings(result.Warnings)...)
	input.Boundary.WorkflowOwnedPaths = append(input.Boundary.WorkflowOwnedPaths, result.WorkflowOwnedPaths...)
	if input.CommitRange != "" {
		input.Boundary.CommitRange = input.CommitRange
	}
	input.ChangedPaths = normalizePaths(input.ChangedPaths)
	input.KnownUnknowns = compactStrings(input.KnownUnknowns)
	input.Boundary.WorkflowOwnedPaths = normalizePaths(input.Boundary.WorkflowOwnedPaths)
	return input
}

func verificationEvidenceFromDelta(value string) VerificationEvidence {
	trimmed := strings.TrimSpace(value)
	if strings.HasPrefix(trimmed, "{") {
		var evidence VerificationEvidence
		if err := json.Unmarshal([]byte(trimmed), &evidence); err == nil {
			return evidence
		}
	}
	return verificationEvidenceFromText(value)
}

func verificationEvidenceFromText(value string) VerificationEvidence {
	return VerificationEvidence{Command: strings.TrimSpace(value), Result: ResultRecorded}
}

func normalizeVerificationEvidence(values []VerificationEvidence) []VerificationEvidence {
	out := make([]VerificationEvidence, 0, len(values))
	seen := map[string]struct{}{}
	for _, value := range values {
		normalized := VerificationEvidence{
			Command:  strings.TrimSpace(value.Command),
			Result:   strings.TrimSpace(value.Result),
			Artifact: strings.TrimSpace(value.Artifact),
		}
		if normalized.Command == "" && normalized.Result == "" && normalized.Artifact == "" {
			continue
		}
		key := normalized.Command + "\x00" + normalized.Result + "\x00" + normalized.Artifact
		if _, ok := seen[key]; ok {
			continue
		}
		seen[key] = struct{}{}
		out = append(out, normalized)
	}
	return out
}

func blockingBoundaryWarnings(values []string) []string {
	out := []string{}
	for _, value := range compactStrings(values) {
		if isNonBlockingBoundaryWarning(value) {
			continue
		}
		out = append(out, value)
	}
	return out
}

func runDeltaSessionUpdate(paths rt.Paths, input UpdateInput) (UpdatePayload, error) {
	cfg, err := config.Load(paths.Root)
	if err != nil {
		return UpdatePayload{}, err
	}
	bundle, err := delta.Load(paths.RuntimeDir, input.DeltaSessionID)
	if err != nil {
		return UpdatePayload{}, err
	}
	input = applyDeltaBundleInput(input, bundle)
	input.PathChanges, err = normalizePathChanges(input.PathChanges)
	if err != nil {
		return UpdatePayload{}, err
	}

	gitDiff, err := gitDiffPathsFromCommitRange(paths.Root, input.CommitRange)
	if err != nil {
		return UpdatePayload{}, err
	}
	result := boundary.Resolve(boundary.ResolveInput{
		Root:         paths.Root,
		Config:       cfg,
		Bundle:       bundle,
		GitDiffPaths: gitDiff,
	})
	forceBoundaryOnlyAutoCommitDecision(&result)

	resolvedInput := updateInputFromBoundary(input, result)
	kept, extraIgnored := ignore.Load(paths.Root).Filter(result.ChangedPaths)
	resolvedInput.PathChanges = filterPathChanges(resolvedInput.PathChanges, normalizePaths(kept))
	ignored := normalizePaths(append(result.IgnoredPaths, extraIgnored...))
	payload, err := runResolvedUpdate(paths, resolvedInput, normalizePaths(kept), ignored, &result)
	if err != nil {
		return UpdatePayload{}, err
	}
	payload.UpdateOutcome = result.Outcome
	payload.Boundary = &result
	return payload, nil
}

func updatePathAccounting(kept []string, ignored []string) map[string]boundary.PathAccounting {
	accounting := make(map[string]boundary.PathAccounting, len(kept)+len(ignored))
	for _, path := range kept {
		accounting[path] = boundary.PathAccounting{
			Path:           path,
			Disposition:    "updated",
			DecisionSource: "changed_paths",
			Reason:         "kept for project cognition update",
		}
	}
	for _, path := range ignored {
		accounting[path] = boundary.PathAccounting{
			Path:           path,
			Disposition:    "ignored",
			DecisionSource: ".cognitionignore",
			Reason:         "matched cognition ignore rule",
		}
	}
	return accounting
}

func forceBoundaryOnlyAutoCommitDecision(result *boundary.Result) {
	const warning = "auto-commit not attempted by boundary-only update layer"
	result.AutoCommitDecision = "commit_skipped"
	if !containsString(result.Warnings, warning) {
		result.Warnings = append(result.Warnings, warning)
		sort.Strings(result.Warnings)
	}
}

func gitDiffPathsFromCommitRange(root string, commitRange string) ([]string, error) {
	commitRange = strings.TrimSpace(commitRange)
	if commitRange == "" {
		return []string{}, nil
	}
	parts := strings.Split(commitRange, "..")
	if len(parts) != 2 || strings.TrimSpace(parts[0]) == "" || strings.TrimSpace(parts[1]) == "" {
		return nil, fmt.Errorf("invalid commit range %q: expected base..head", commitRange)
	}
	base := strings.TrimSpace(parts[0])
	head := strings.TrimSpace(parts[1])
	if strings.HasPrefix(base, "-") {
		return nil, fmt.Errorf("invalid commit range endpoint %q: endpoints must not start with '-'", base)
	}
	if strings.HasPrefix(head, "-") {
		return nil, fmt.Errorf("invalid commit range endpoint %q: endpoints must not start with '-'", head)
	}
	entries, err := rt.GitDiffNameStatus(root, base, head)
	if err != nil {
		return nil, fmt.Errorf("git diff commit range %q: %w", commitRange, err)
	}
	paths := make([]string, 0, len(entries))
	for _, entry := range entries {
		paths = append(paths, entry.Path)
	}
	return normalizePaths(paths), nil
}

func ScopeFromPacket(packetFile string) ([]string, error) {
	data, err := os.ReadFile(packetFile)
	if err != nil {
		return nil, fmt.Errorf("read packet file: %w", err)
	}
	var raw any
	if err := json.Unmarshal(data, &raw); err != nil {
		return nil, fmt.Errorf("parse packet file: %w", err)
	}
	var paths []string
	collectPaths(raw, false, &paths)
	return normalizePaths(paths), nil
}

func collectPaths(value any, allowString bool, out *[]string) {
	switch typed := value.(type) {
	case map[string]any:
		for key, item := range typed {
			lower := strings.ToLower(key)
			pathKey := lower == "path" || lower == "paths" || lower == "changed_paths" || lower == "scope_paths" || lower == "files" || lower == "file"
			collectPaths(item, pathKey, out)
		}
	case []any:
		for _, item := range typed {
			collectPaths(item, allowString, out)
		}
	case string:
		if allowString && looksLikePath(typed) {
			*out = append(*out, typed)
		}
	}
}

func looksLikePath(value string) bool {
	value = strings.TrimSpace(value)
	return value != "" && (strings.Contains(value, "/") || strings.Contains(value, "\\") || strings.Contains(value, "."))
}

func normalizePaths(paths []string) []string {
	out := make([]string, 0, len(paths))
	seen := map[string]bool{}
	for _, path := range paths {
		path = filepath.ToSlash(strings.TrimSpace(strings.TrimPrefix(path, "./")))
		if path == "" || seen[path] {
			continue
		}
		seen[path] = true
		out = append(out, path)
	}
	sort.Strings(out)
	return out
}

func normalizePathChanges(values []changemodel.PathChange) ([]changemodel.PathChange, error) {
	out := make([]changemodel.PathChange, 0, len(values))
	seenPaths := make(map[string]int, len(values))
	for _, value := range values {
		value.Path = normalizePathValue(value.Path)
		value.OldPath = normalizePathValue(value.OldPath)
		value.NodeID = strings.TrimSpace(value.NodeID)
		value.EvidenceRefs = compactStrings(value.EvidenceRefs)
		if value.Disposition != nil {
			disposition := changemodel.Disposition(strings.TrimSpace(string(*value.Disposition)))
			value.Disposition = &disposition
		}
		if !validChangedPath(value.Path) || (value.OldPath != "" && !validChangedPath(value.OldPath)) {
			return nil, fmt.Errorf("invalid path change %q: expected a concrete repository-relative path", value.Path)
		}
		if err := value.Validate(); err != nil {
			return nil, err
		}
		if priorIndex, ok := seenPaths[value.Path]; ok {
			prior := out[priorIndex]
			if prior.OldPath != value.OldPath || prior.Operation != value.Operation || prior.NodeID != value.NodeID || !sameDisposition(prior.Disposition, value.Disposition) {
				return nil, fmt.Errorf("conflicting path changes for %q", value.Path)
			}
			out[priorIndex].EvidenceRefs = compactStrings(append(prior.EvidenceRefs, value.EvidenceRefs...))
			continue
		}
		seenPaths[value.Path] = len(out)
		out = append(out, value)
	}
	sort.Slice(out, func(i, j int) bool { return out[i].Path < out[j].Path })
	return out, nil
}

func normalizePathValue(path string) string {
	path = filepath.ToSlash(strings.TrimSpace(path))
	for strings.HasPrefix(path, "./") {
		path = strings.TrimPrefix(path, "./")
	}
	return strings.TrimRight(path, "/")
}

func sameDisposition(left *changemodel.Disposition, right *changemodel.Disposition) bool {
	if left == nil || right == nil {
		return left == nil && right == nil
	}
	return *left == *right
}

func filterPathChanges(values []changemodel.PathChange, keptPaths []string) []changemodel.PathChange {
	kept := make(map[string]struct{}, len(keptPaths))
	for _, path := range keptPaths {
		kept[path] = struct{}{}
	}
	out := make([]changemodel.PathChange, 0, len(values))
	for _, value := range values {
		if _, ok := kept[value.Path]; ok {
			out = append(out, value)
		}
	}
	return out
}

func convertIgnoredRenameTargetsToDeletes(values []changemodel.PathChange, keptPaths []string, ignoredPaths []string) ([]changemodel.PathChange, []string) {
	ignored := make(map[string]struct{}, len(ignoredPaths))
	for _, path := range ignoredPaths {
		ignored[path] = struct{}{}
	}
	out := make([]changemodel.PathChange, 0, len(values))
	for _, value := range values {
		if value.Operation == changemodel.OperationRename && value.OldPath != "" {
			if _, targetIgnored := ignored[value.Path]; targetIgnored {
				value.Path = value.OldPath
				value.OldPath = ""
				value.Operation = changemodel.OperationDelete
				keptPaths = append(keptPaths, value.Path)
			}
		}
		out = append(out, value)
	}
	return out, normalizePaths(keptPaths)
}

func validateChangedPaths(paths []string) error {
	for _, path := range paths {
		if !validChangedPath(path) {
			return fmt.Errorf("invalid changed path %q: expected a concrete repository-relative path", path)
		}
	}
	return nil
}

func validChangedPath(path string) bool {
	path = filepath.ToSlash(strings.TrimSpace(path))
	path = strings.TrimPrefix(path, "./")
	if path == "" || path == "." || filepath.IsAbs(path) || strings.HasPrefix(path, "/") || strings.Contains(path, ":") {
		return false
	}
	if path == ".specify" || strings.HasPrefix(path, ".specify/") {
		return false
	}
	if strings.ContainsAny(path, "*?[]{}") {
		return false
	}
	parts := strings.Split(path, "/")
	for _, part := range parts {
		if part == "" || part == "." || part == ".." {
			return false
		}
	}
	return true
}

func appendUnique(existing []string, values ...string) []string {
	seen := map[string]bool{}
	for _, value := range existing {
		seen[value] = true
	}
	out := append([]string{}, existing...)
	for _, value := range values {
		value = strings.TrimSpace(value)
		if value == "" || seen[value] {
			continue
		}
		seen[value] = true
		out = append(out, value)
	}
	sort.Strings(out)
	return out
}

func subtractStrings(values []string, remove []string) []string {
	removeSet := map[string]bool{}
	for _, value := range remove {
		trimmed := strings.TrimSpace(value)
		if trimmed != "" {
			removeSet[trimmed] = true
		}
	}
	out := make([]string, 0, len(values))
	seen := map[string]bool{}
	for _, value := range values {
		trimmed := strings.TrimSpace(value)
		if trimmed == "" || removeSet[trimmed] || seen[trimmed] {
			continue
		}
		seen[trimmed] = true
		out = append(out, trimmed)
	}
	sort.Strings(out)
	return out
}

func compactStrings(values []string) []string {
	out := make([]string, 0, len(values))
	seen := map[string]bool{}
	for _, value := range values {
		trimmed := strings.TrimSpace(value)
		if trimmed == "" || seen[trimmed] {
			continue
		}
		seen[trimmed] = true
		out = append(out, trimmed)
	}
	sort.Strings(out)
	return out
}

func containsString(values []string, want string) bool {
	for _, value := range values {
		if value == want {
			return true
		}
	}
	return false
}
