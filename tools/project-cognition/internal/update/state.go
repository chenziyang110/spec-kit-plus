package update

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"time"

	"github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/boundary"
	"github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/config"
	"github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/delta"
	"github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/ignore"
	rt "github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/runtime"
	"github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/runtimegate"
	"github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/store"
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

type UpdateBoundaryInput struct {
	CommitRange        string   `json:"commit_range,omitempty"`
	InitialDirtyPaths  []string `json:"initial_dirty_paths,omitempty"`
	WorkflowOwnedPaths []string `json:"workflow_owned_paths,omitempty"`
}

type PayloadFileInput struct {
	Workflow          string                 `json:"workflow"`
	Reason            string                 `json:"reason"`
	ChangedPaths      []string               `json:"changed_paths"`
	ScopePaths        []string               `json:"scope_paths"`
	BehaviorSurfaces  []string               `json:"behavior_surfaces"`
	GeneratedSurfaces []string               `json:"generated_surfaces"`
	StateContracts    []string               `json:"state_contracts"`
	Verification      []VerificationEvidence `json:"verification"`
	KnownUnknowns     []string               `json:"known_unknowns"`
	ConfidenceNotes   []string               `json:"confidence_notes"`
	UserDecisions     []string               `json:"user_decisions"`
	Boundary          UpdateBoundaryInput    `json:"boundary"`
}

type UpdateInput struct {
	ChangedPaths      []string
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
)

type UpdatePayload struct {
	Readiness               string           `json:"readiness"`
	RecommendedNextAction   string           `json:"recommended_next_action"`
	UpdateID                string           `json:"update_id"`
	UpdateOutcome           string           `json:"update_outcome"`
	ResultState             string           `json:"result_state"`
	StatusUpdate            StatusUpdate     `json:"status_update"`
	ChangedPaths            []string         `json:"changed_paths"`
	IgnoredPaths            []string         `json:"ignored_paths"`
	AffectedNodes           []map[string]any `json:"affected_nodes"`
	MissingCoverage         []string         `json:"missing_coverage"`
	AdoptedPaths            []string         `json:"adopted_paths"`
	ReviewPaths             []string         `json:"review_paths"`
	UnadoptablePaths        []string         `json:"unadoptable_paths"`
	KnownUnknowns           []string         `json:"known_unknowns"`
	MinimalLiveReads        []string         `json:"minimal_live_reads"`
	PathAdoption            map[string]any   `json:"path_adoption"`
	LastRefreshChangedBasis []string         `json:"last_refresh_changed_files_basis"`
	Boundary                *boundary.Result `json:"boundary,omitempty"`
}

func MarkDirty(paths rt.Paths, input DirtyInput) (rt.Status, error) {
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
	if err := blockSplitBrainBaseline(paths); err != nil {
		return rt.Status{}, err
	}
	status, err := rt.ReadStatus(paths)
	if err != nil {
		return rt.Status{}, err
	}
	status.Dirty = false
	status.DirtyReasons = []string{}
	status.DirtyOriginCommand = ""
	status.DirtyOriginFeatureDir = ""
	status.DirtyOriginLaneID = ""
	status.DirtyScopePaths = []string{}
	if status.Status == "stale" {
		status.Status = "ok"
	}
	if err := rt.WriteStatus(paths, status); err != nil {
		return rt.Status{}, err
	}
	return status, nil
}

func RecordRefresh(paths rt.Paths, reason string) (rt.Status, error) {
	if err := blockSplitBrainBaseline(paths); err != nil {
		return rt.Status{}, err
	}
	if reason == "" {
		reason = "manual"
	}
	status, err := rt.ReadStatus(paths)
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

func CompleteRefresh(paths rt.Paths, basis string) (rt.Status, error) {
	agreement, ok := runtimegate.CheckExisting(paths)
	if !ok {
		return rt.Status{}, fmt.Errorf("project cognition agreement blocked: run_map_scan_build: status.json and project-cognition.db are missing")
	}
	if agreement.Status != "ok" {
		return rt.Status{}, fmt.Errorf("project cognition agreement blocked: %s: %s", agreementAction(agreement), strings.Join(agreement.Errors, "; "))
	}
	status, err := rt.ReadStatus(paths)
	if err != nil {
		return rt.Status{}, err
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
	if basis == "" {
		basis = "map-build"
	}
	status.LastRefreshBasis = basis
	if err := rt.WriteStatus(paths, status); err != nil {
		return rt.Status{}, err
	}
	return status, nil
}

func RefreshTopics(paths rt.Paths, topics []string, reason string) (rt.Status, error) {
	if err := blockSplitBrainBaseline(paths); err != nil {
		return rt.Status{}, err
	}
	if reason == "" {
		reason = "topic-refresh"
	}
	status, err := RecordRefresh(paths, reason)
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
	changed := append([]string{}, input.ChangedPaths...)
	changed = append(changed, input.ScopePaths...)
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
	pathAccounting := updatePathAccounting(kept, ignored)
	updateID := "upd-" + time.Now().UTC().Format("20060102T150405.000000000Z")

	st, err := store.OpenExisting(paths)
	if errors.Is(err, os.ErrNotExist) {
		st = nil
		err = nil
	}
	if err != nil {
		return UpdatePayload{}, err
	}
	nodes := []map[string]any{}
	closure := store.AffectedClosure{}
	resultState := updateResultState(kept, nodes, input)
	if st != nil {
		defer st.Close()
		closure, err = st.AffectedClosureForPaths(context.Background(), kept)
		if err != nil {
			return UpdatePayload{}, err
		}
		nodes, err = st.NodesForIDs(context.Background(), closure.NodeIDs)
		if err != nil {
			return UpdatePayload{}, err
		}
		resultState = updateResultState(kept, nodes, input)
		if resultState == ResultReady && len(closure.NodeIDs) > 0 {
			for _, path := range kept {
				if _, err := st.RefreshPathCoverage(context.Background(), store.PathCoverageRefresh{
					UpdateID:   updateID,
					Path:       path,
					NodeID:     closure.NodeIDs[0],
					Relation:   "owns",
					Confidence: "verified",
					Reason:     input.Reason,
				}); err != nil {
					return UpdatePayload{}, err
				}
			}
		}
		if err := st.RecordStructuredUpdate(context.Background(), store.UpdateRecord{
			ID:             updateID,
			Trigger:        input.Reason,
			ChangedPaths:   kept,
			AffectedNodes:  closure.NodeIDs,
			AffectedClaims: closure.ClaimIDs,
			AffectedSlices: closure.SliceIDs,
			ResultState:    resultState,
			Attrs: map[string]any{
				"workflow":           input.Workflow,
				"behavior_surfaces":  input.BehaviorSurfaces,
				"generated_surfaces": input.GeneratedSurfaces,
				"state_contracts":    input.StateContracts,
				"verification":       input.Verification,
				"known_unknowns":     input.KnownUnknowns,
				"confidence_notes":   input.ConfidenceNotes,
			},
		}); err != nil {
			return UpdatePayload{}, err
		}
	}

	status, err := rt.ReadStatus(paths)
	if err != nil {
		return UpdatePayload{}, err
	}
	status = applyResultState(status, resultState, updateID, kept, input.Reason)
	if err := rt.WriteStatus(paths, status); err != nil {
		return UpdatePayload{}, err
	}

	updatePaths := updatePathPayloads(resultState, kept)
	pathAdoption := map[string]any{
		"adopted":         updatePaths.adopted,
		"ignored":         ignored,
		"needs_review":    updatePaths.review,
		"path_accounting": pathAccounting,
	}
	return UpdatePayload{
		Readiness:               status.Readiness,
		RecommendedNextAction:   status.RecommendedNextAction,
		UpdateID:                updateID,
		ResultState:             resultState,
		StatusUpdate:            statusUpdateFromStatus(status),
		ChangedPaths:            updatePaths.changed,
		IgnoredPaths:            ignored,
		AffectedNodes:           nodes,
		MissingCoverage:         []string{},
		AdoptedPaths:            updatePaths.adopted,
		ReviewPaths:             updatePaths.review,
		UnadoptablePaths:        []string{},
		KnownUnknowns:           compactStrings(input.KnownUnknowns),
		MinimalLiveReads:        updatePaths.minimalLiveReads,
		PathAdoption:            pathAdoption,
		LastRefreshChangedBasis: updatePaths.changed,
	}, nil
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

func updateResultState(kept []string, nodes []map[string]any, input UpdateInput) string {
	if len(kept) == 0 {
		return ResultNoOp
	}
	if len(nodes) > 0 && len(input.Verification) > 0 && len(compactStrings(input.KnownUnknowns)) == 0 {
		return ResultReady
	}
	return ResultPartialRefresh
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

type updatePathPayload struct {
	changed          []string
	adopted          []string
	review           []string
	minimalLiveReads []string
}

func updatePathPayloads(resultState string, kept []string) updatePathPayload {
	switch resultState {
	case ResultReady:
		return updatePathPayload{
			changed: append([]string{}, kept...),
			adopted: append([]string{}, kept...),
		}
	case ResultNoOp:
		return updatePathPayload{
			changed:          []string{},
			adopted:          []string{},
			review:           []string{},
			minimalLiveReads: []string{},
		}
	default:
		return updatePathPayload{
			changed:          append([]string{}, kept...),
			adopted:          []string{},
			review:           append([]string{}, kept...),
			minimalLiveReads: append([]string{}, kept...),
		}
	}
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
	payload.ScopePaths = normalizePaths(payload.ScopePaths)
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

func nodeIDsFromRows(rows []map[string]any) []string {
	ids := make([]string, 0, len(rows))
	seen := map[string]bool{}
	for _, row := range rows {
		id, ok := row["id"].(string)
		if !ok || id == "" || seen[id] {
			continue
		}
		seen[id] = true
		ids = append(ids, id)
	}
	sort.Strings(ids)
	return ids
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

	updateID := "upd-" + time.Now().UTC().Format("20060102T150405.000000000Z")
	st, err := store.OpenExisting(paths)
	if errors.Is(err, os.ErrNotExist) {
		st = nil
		err = nil
	}
	if err != nil {
		return UpdatePayload{}, err
	}
	if st != nil {
		defer st.Close()
		if err := st.RecordStructuredUpdate(context.Background(), store.UpdateRecord{
			ID:           updateID,
			Trigger:      input.Reason,
			ChangedPaths: result.ChangedPaths,
			ResultState:  ResultPartialRefresh,
			Attrs: map[string]any{
				"workflow":           input.Workflow,
				"behavior_surfaces":  input.BehaviorSurfaces,
				"generated_surfaces": input.GeneratedSurfaces,
				"state_contracts":    input.StateContracts,
				"verification":       input.Verification,
				"known_unknowns":     input.KnownUnknowns,
				"confidence_notes":   input.ConfidenceNotes,
				"boundary":           result,
			},
		}); err != nil {
			return UpdatePayload{}, err
		}
	}

	status, err := rt.ReadStatus(paths)
	if err != nil {
		return UpdatePayload{}, err
	}
	status.LastUpdateID = updateID
	status.LastDeltaSessionID = input.DeltaSessionID
	status.LastUpdateOutcome = result.Outcome
	status.LastUpdateBoundary = result.BoundarySource
	status.LastRefreshChangedFilesBasis = result.ChangedPaths
	status.StalePaths = appendUnique(status.StalePaths, result.ChangedPaths...)
	status.StaleReasons = appendUnique(status.StaleReasons, input.Reason)
	status.Dirty = true
	status.Status = "stale"
	status.Freshness = rt.StaleFreshness
	status.Readiness = rt.BlockedReadiness
	status.RecommendedNextAction = "review_project_cognition_update"
	if err := rt.WriteStatus(paths, status); err != nil {
		return UpdatePayload{}, err
	}

	return UpdatePayload{
		Readiness:             status.Readiness,
		RecommendedNextAction: status.RecommendedNextAction,
		UpdateID:              updateID,
		UpdateOutcome:         result.Outcome,
		ResultState:           ResultPartialRefresh,
		StatusUpdate:          statusUpdateFromStatus(status),
		ChangedPaths:          result.ChangedPaths,
		IgnoredPaths:          result.IgnoredPaths,
		AffectedNodes:         []map[string]any{},
		MissingCoverage:       []string{},
		AdoptedPaths:          []string{},
		ReviewPaths:           result.AmbiguousPaths,
		UnadoptablePaths:      []string{},
		KnownUnknowns:         result.Warnings,
		MinimalLiveReads:      result.WorkflowOwnedPaths,
		PathAdoption: map[string]any{
			"phase":                "boundary_only",
			"auto_commit_decision": result.AutoCommitDecision,
			"path_accounting":      result.PathAccounting,
		},
		LastRefreshChangedBasis: result.ChangedPaths,
		Boundary:                &result,
	}, nil
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
