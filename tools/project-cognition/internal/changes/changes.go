package changes

import (
	"context"
	"errors"
	"fmt"
	"os/exec"
	"path/filepath"
	"sort"
	"strings"

	"github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/ignore"
	rt "github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/runtime"
	"github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/store"
)

const (
	nextNoOp            = "no_op"
	nextAffectedClosure = "affected_closure"
	nextPartialRefresh  = "partial_refresh"
	nextNeedsRebuild    = "needs_rebuild"
	nextBlocked         = "blocked"

	levelMappedChange = "mapped_change"
	levelNewPath      = "new_path"
	levelDeletedPath  = "deleted_path"
	levelRenamedPath  = "renamed_path"
	levelUnknownPath  = "unknown_path"
)

type Input struct {
	Since              string   `json:"since"`
	Head               string   `json:"head"`
	IncludeWorkingTree bool     `json:"include_working_tree"`
	IncludeUntracked   bool     `json:"include_untracked"`
	ExplicitPaths      []string `json:"explicit_paths"`
	Intent             string   `json:"intent"`
}

type Summary struct {
	Total    int `json:"total"`
	Included int `json:"included"`
	Ignored  int `json:"ignored"`
	Known    int `json:"known"`
	Unknown  int `json:"unknown"`
	Deleted  int `json:"deleted"`
	Renamed  int `json:"renamed"`
}

type Change struct {
	Path               string   `json:"path"`
	OldPath            string   `json:"old_path,omitempty"`
	GitStatus          string   `json:"git_status"`
	Sources            []string `json:"sources"`
	Tracked            bool     `json:"tracked"`
	WorkingTreeDirty   bool     `json:"working_tree_dirty"`
	IgnoredByCognition bool     `json:"ignored_by_cognition"`
	KnownToRuntime     bool     `json:"known_to_runtime"`
	NodeID             string   `json:"node_id,omitempty"`
	ChangeLevel        string   `json:"change_level"`
	RecommendedAction  string   `json:"recommended_action"`
	Reason             []string `json:"reason"`
}

type Payload struct {
	Status           string   `json:"status"`
	Readiness        string   `json:"readiness"`
	BaselineCommit   string   `json:"baseline_commit,omitempty"`
	HeadCommit       string   `json:"head_commit,omitempty"`
	WorkingTreeDirty bool     `json:"working_tree_dirty"`
	NextAction       string   `json:"next_action"`
	Summary          Summary  `json:"summary"`
	Changes          []Change `json:"changes"`
	IgnoredPaths     []string `json:"ignored_paths"`
	UnknownPaths     []string `json:"unknown_paths"`
	Warnings         []string `json:"warnings"`
	Errors           []string `json:"errors"`
}

type mergedChange struct {
	path    string
	oldPath string
	status  string
	sources map[string]bool
	tracked bool
}

func Run(paths rt.Paths, input Input) (Payload, error) {
	payload := Payload{
		Changes:      []Change{},
		IgnoredPaths: []string{},
		UnknownPaths: []string{},
		Warnings:     []string{},
		Errors:       []string{},
	}

	status, err := rt.ReadStatus(paths)
	if errors.Is(err, rt.ErrUnsupportedLegacy) {
		payload.Status = "blocked"
		payload.Readiness = rt.UnsupportedReadiness
		payload.NextAction = nextNeedsRebuild
		payload.Errors = []string{rt.UnsupportedLegacyPayload(paths).Errors[0]}
		return payload, nil
	}
	if err != nil {
		payload.Status = "blocked"
		payload.Readiness = rt.NeedsRebuildReadiness
		payload.NextAction = nextNeedsRebuild
		payload.Errors = []string{err.Error()}
		return payload, nil
	}
	payload.Status = status.Status
	payload.Readiness = status.Readiness

	if !rt.GitAvailable(paths.Root) {
		payload.Status = "blocked"
		payload.NextAction = nextBlocked
		payload.Errors = []string{"git repository unavailable"}
		return payload, nil
	}

	head := strings.TrimSpace(input.Head)
	if head == "" {
		var headErr error
		head, headErr = rt.GitHead(paths.Root)
		if headErr != nil {
			payload.Status = "blocked"
			payload.NextAction = nextBlocked
			payload.Errors = []string{"git repository unavailable"}
			return payload, nil
		}
	}
	baseline := strings.TrimSpace(input.Since)
	if baseline == "" {
		baseline = strings.TrimSpace(status.LastRefreshGitCommit)
	}
	payload.HeadCommit = head
	payload.BaselineCommit = baseline
	if baseline == "" {
		payload.Warnings = append(payload.Warnings, "no refresh git baseline recorded; using working tree status only")
	}

	merged := map[string]*mergedChange{}
	if baseline != "" && head != "" {
		entries, err := rt.GitDiffNameStatus(paths.Root, baseline, head)
		if err != nil {
			payload.Status = "blocked"
			payload.NextAction = nextBlocked
			payload.Errors = []string{err.Error()}
			return payload, nil
		}
		for _, entry := range entries {
			addMerged(merged, entry, "committed", true)
		}
	}

	if input.IncludeWorkingTree || input.IncludeUntracked {
		entries, err := rt.GitStatusEntries(paths.Root)
		if err != nil {
			payload.Status = "blocked"
			payload.NextAction = nextBlocked
			payload.Errors = []string{"git repository unavailable"}
			return payload, nil
		}
		for _, entry := range entries {
			include, block := intakeStatusEntry(entry.Code, input.IncludeWorkingTree, input.IncludeUntracked)
			if block {
				payload.Status = "blocked"
				payload.Readiness = rt.BlockedReadiness
				payload.NextAction = nextBlocked
				payload.Changes = []Change{}
				payload.UnknownPaths = []string{}
				payload.Errors = []string{fmt.Sprintf("unsupported git status %q for %s", entry.Code, entry.Path)}
				return payload, nil
			}
			if !include {
				continue
			}
			addMerged(merged, entry, "working_tree", entry.Code != "??")
		}
	}

	for _, path := range input.ExplicitPaths {
		path = normalizePath(path)
		if path == "" {
			continue
		}
		addMerged(merged, rt.GitStatusEntry{Code: "explicit", Path: path}, "explicit", pathTrackedByGit(paths.Root, path))
	}

	matcher := ignore.Load(paths.Root)
	includedPaths := make([]string, 0, len(merged))
	for _, item := range merged {
		if matcher.Ignored(item.path) {
			payload.IgnoredPaths = append(payload.IgnoredPaths, item.path)
			continue
		}
		includedPaths = append(includedPaths, item.path)
	}
	sort.Strings(includedPaths)
	sort.Strings(payload.IgnoredPaths)

	pathNodeIDs, err := nodeIDsForPaths(paths, includedPaths, runtimeRequiresStore(status))
	if err != nil {
		payload.Status = "blocked"
		payload.Readiness = rt.NeedsRebuildReadiness
		payload.NextAction = nextNeedsRebuild
		payload.Changes = []Change{}
		payload.UnknownPaths = []string{}
		payload.Errors = []string{err.Error()}
		payload.Summary = Summary{
			Total:   len(includedPaths) + len(payload.IgnoredPaths),
			Ignored: len(payload.IgnoredPaths),
		}
		return payload, nil
	}
	for _, path := range includedPaths {
		item := merged[path]
		nodeID := pathNodeIDs[path]
		change := Change{
			Path:               item.path,
			OldPath:            item.oldPath,
			GitStatus:          item.status,
			Sources:            sortedSources(item.sources),
			Tracked:            item.tracked,
			WorkingTreeDirty:   item.sources["working_tree"],
			IgnoredByCognition: false,
			KnownToRuntime:     nodeID != "",
			NodeID:             nodeID,
		}
		change.ChangeLevel = classify(change.GitStatus, change.KnownToRuntime)
		change.RecommendedAction = recommendedAction(change.ChangeLevel)
		change.Reason = reason(change.KnownToRuntime, change.ChangeLevel)
		payload.Changes = append(payload.Changes, change)
		if change.WorkingTreeDirty {
			payload.WorkingTreeDirty = true
		}
	}

	sort.Slice(payload.Changes, func(i, j int) bool {
		return payload.Changes[i].Path < payload.Changes[j].Path
	})
	for _, change := range payload.Changes {
		payload.Summary.Included++
		if change.KnownToRuntime {
			payload.Summary.Known++
		} else {
			payload.Summary.Unknown++
			payload.UnknownPaths = append(payload.UnknownPaths, change.Path)
		}
		switch change.ChangeLevel {
		case levelDeletedPath:
			payload.Summary.Deleted++
		case levelRenamedPath:
			payload.Summary.Renamed++
		}
	}
	sort.Strings(payload.UnknownPaths)
	payload.Summary.Ignored = len(payload.IgnoredPaths)
	payload.Summary.Total = payload.Summary.Included + payload.Summary.Ignored

	payload.NextAction = nextAction(payload.Readiness, payload.Summary.Included, payload.UnknownPaths)
	return payload, nil
}

func addMerged(merged map[string]*mergedChange, entry rt.GitStatusEntry, source string, tracked bool) {
	path := normalizePath(entry.Path)
	if path == "" {
		return
	}
	item := merged[path]
	if item == nil {
		item = &mergedChange{
			path:    path,
			sources: map[string]bool{},
		}
		merged[path] = item
	}
	if oldPath := normalizePath(entry.OldPath); oldPath != "" {
		item.oldPath = oldPath
	}
	status := strings.TrimSpace(entry.Code)
	if status != "" && shouldReplaceStatus(item.status, status, source) {
		item.status = status
	}
	item.sources[source] = true
	item.tracked = item.tracked || tracked
}

func shouldReplaceStatus(current string, next string, source string) bool {
	if current == "" {
		return true
	}
	if source == "working_tree" {
		return true
	}
	if source == "committed" && current == "explicit" {
		return true
	}
	return false
}

func includeStatusEntry(code string, includeWorkingTree bool, includeUntracked bool) bool {
	include, _ := intakeStatusEntry(code, includeWorkingTree, includeUntracked)
	return include
}

func intakeStatusEntry(code string, includeWorkingTree bool, includeUntracked bool) (bool, bool) {
	code = strings.TrimSpace(code)
	if code == "??" {
		return includeUntracked, false
	}
	switch code {
	case "DD", "AU", "UD", "UA", "DU", "AA", "UU":
		return false, true
	}
	for _, r := range code {
		switch r {
		case 'M', 'A', 'D', 'R':
			continue
		default:
			return false, true
		}
	}
	if code == "" {
		return false, false
	}
	return includeWorkingTree, false
}

func sortedSources(sources map[string]bool) []string {
	out := make([]string, 0, len(sources))
	for _, source := range []string{"committed", "working_tree", "explicit"} {
		if sources[source] {
			out = append(out, source)
		}
	}
	var unknown []string
	for source := range sources {
		switch source {
		case "committed", "working_tree", "explicit":
			continue
		default:
			unknown = append(unknown, source)
		}
	}
	sort.Strings(unknown)
	out = append(out, unknown...)
	return out
}

func nodeIDsForPaths(paths rt.Paths, changedPaths []string, requireStore bool) (map[string]string, error) {
	if len(changedPaths) == 0 && !requireStore {
		return map[string]string{}, nil
	}
	st, err := store.OpenExisting(paths)
	if err != nil {
		return nil, fmt.Errorf("runtime graph store unavailable: %w", err)
	}
	defer st.Close()
	if len(changedPaths) == 0 {
		return map[string]string{}, nil
	}
	pathNodeIDs, err := st.NodeIDsForExactPaths(context.Background(), changedPaths)
	if err != nil {
		return nil, fmt.Errorf("runtime path index lookup failed: %w", err)
	}
	return pathNodeIDs, nil
}

func runtimeRequiresStore(status rt.Status) bool {
	return status.Readiness == rt.ReadyReadiness || status.GraphReady
}

func classify(status string, known bool) string {
	switch {
	case strings.HasPrefix(status, "D"):
		return levelDeletedPath
	case strings.HasPrefix(status, "R"):
		return levelRenamedPath
	case status == "??" || strings.HasPrefix(status, "A"):
		return levelNewPath
	case known:
		return levelMappedChange
	default:
		return levelUnknownPath
	}
}

func recommendedAction(level string) string {
	switch level {
	case levelMappedChange, levelDeletedPath, levelRenamedPath:
		return nextAffectedClosure
	default:
		return nextPartialRefresh
	}
}

func reason(known bool, level string) []string {
	if known {
		return []string{"path exists in active runtime path_index"}
	}
	if level == levelNewPath {
		return []string{"path is not in active runtime path_index"}
	}
	return []string{"changed path lacks active runtime path_index coverage"}
}

func nextAction(readiness string, included int, unknownPaths []string) string {
	if readiness == rt.NeedsRebuildReadiness || readiness == rt.UnsupportedReadiness {
		return nextNeedsRebuild
	}
	if included == 0 {
		return nextNoOp
	}
	if len(unknownPaths) > 0 {
		return nextPartialRefresh
	}
	return nextAffectedClosure
}

func normalizePath(path string) string {
	normalized := filepath.ToSlash(strings.TrimSpace(path))
	for strings.HasPrefix(normalized, "./") {
		normalized = strings.TrimPrefix(normalized, "./")
	}
	return strings.Trim(normalized, "/")
}

func pathTrackedByGit(root string, path string) bool {
	if path == "" {
		return false
	}
	cmd := exec.Command("git", "ls-files", "--error-unmatch", "--", path)
	cmd.Dir = root
	return cmd.Run() == nil
}
