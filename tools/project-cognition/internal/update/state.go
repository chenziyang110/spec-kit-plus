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

type UpdateInput struct {
	ChangedPaths   []string
	ScopePaths     []string
	Reason         string
	DeltaSessionID string
	CommitRange    string
}

type UpdatePayload struct {
	Readiness               string           `json:"readiness"`
	RecommendedNextAction   string           `json:"recommended_next_action"`
	UpdateID                string           `json:"update_id"`
	UpdateOutcome           string           `json:"update_outcome"`
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
	if st != nil {
		defer st.Close()
		nodes, err = st.NodesForPaths(context.Background(), kept)
		if err != nil {
			return UpdatePayload{}, err
		}
		changedJSON, _ := json.Marshal(kept)
		if err := st.RecordUpdate(context.Background(), updateID, input.Reason, string(changedJSON)); err != nil {
			return UpdatePayload{}, err
		}
	}

	status, err := rt.ReadStatus(paths)
	if err != nil {
		return UpdatePayload{}, err
	}
	status.LastUpdateID = updateID
	status.LastRefreshChangedFilesBasis = kept
	status.StalePaths = appendUnique(status.StalePaths, kept...)
	status.StaleReasons = appendUnique(status.StaleReasons, input.Reason)
	if len(kept) > 0 {
		status.Dirty = true
		status.Status = "stale"
		status.Freshness = rt.StaleFreshness
		status.Readiness = rt.BlockedReadiness
		status.RecommendedNextAction = "review_project_cognition_update"
	}
	if err := rt.WriteStatus(paths, status); err != nil {
		return UpdatePayload{}, err
	}

	pathAdoption := map[string]any{
		"adopted":      kept,
		"ignored":      ignored,
		"needs_review": kept,
	}
	return UpdatePayload{
		Readiness:               status.Readiness,
		RecommendedNextAction:   status.RecommendedNextAction,
		UpdateID:                updateID,
		ChangedPaths:            kept,
		IgnoredPaths:            ignored,
		AffectedNodes:           nodes,
		MissingCoverage:         []string{},
		AdoptedPaths:            kept,
		ReviewPaths:             kept,
		UnadoptablePaths:        []string{},
		KnownUnknowns:           []string{},
		MinimalLiveReads:        kept,
		PathAdoption:            pathAdoption,
		LastRefreshChangedBasis: kept,
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
		changedJSON, _ := json.Marshal(result.ChangedPaths)
		if err := st.RecordUpdate(context.Background(), updateID, input.Reason, string(changedJSON)); err != nil {
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
		},
		LastRefreshChangedBasis: result.ChangedPaths,
		Boundary:                &result,
	}, nil
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

func containsString(values []string, want string) bool {
	for _, value := range values {
		if value == want {
			return true
		}
	}
	return false
}
