package boundary

import (
	"path/filepath"
	"sort"
	"strings"

	"github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/config"
	"github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/delta"
	"github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/ignore"
)

type ResolveInput struct {
	Root              string
	Config            config.Config
	Bundle            delta.Bundle
	GitDiffPaths      []string
	ExplicitArtifacts []string
}

type Result struct {
	Outcome            string   `json:"outcome"`
	AutoCommitDecision string   `json:"auto_commit_decision"`
	BoundarySource     string   `json:"boundary_source"`
	ChangedPaths       []string `json:"changed_paths"`
	WorkflowOwnedPaths []string `json:"workflow_owned_paths"`
	AmbiguousPaths     []string `json:"ambiguous_paths"`
	IgnoredPaths       []string `json:"ignored_paths"`
	Warnings           []string `json:"warnings"`
}

func Resolve(input ResolveInput) Result {
	candidates := normalizePaths(input.GitDiffPaths)
	boundarySource := "git_diff"
	if len(candidates) == 0 {
		boundarySource = "delta_journal"
		candidates = eventChangedPaths(input.Bundle.Events)
	}
	candidates = normalizePaths(append(candidates, input.ExplicitArtifacts...))

	kept, ignored := ignore.Load(input.Root).Filter(candidates)
	kept = normalizePaths(kept)
	ignored = normalizePaths(ignored)

	initialDirty := stringSet(normalizePaths(input.Bundle.Session.Git.InitialDirtyPaths))
	claimed := claimedInitialDirtyPaths(input.Bundle.Events)

	owned := make([]string, 0, len(kept))
	ambiguous := make([]string, 0)
	for _, path := range kept {
		if _, wasInitiallyDirty := initialDirty[path]; wasInitiallyDirty {
			if _, isClaimed := claimed[path]; !isClaimed {
				ambiguous = append(ambiguous, path)
				continue
			}
		}
		owned = append(owned, path)
	}

	owned = normalizePaths(owned)
	ambiguous = normalizePaths(ambiguous)

	decision := "commit_skipped"
	if input.Config.ProjectCognition.AutoCommit && len(owned) > 0 && len(ambiguous) == 0 {
		decision = "commit_created"
	}

	warnings := make([]string, 0, 2)
	if decision == "commit_skipped" {
		warnings = append(warnings, "auto-commit skipped; update can continue from boundary metadata")
	}
	if len(ambiguous) > 0 {
		warnings = append(warnings, "ambiguous initial dirty paths excluded from workflow-owned paths")
	}

	return Result{
		Outcome:            "boundary_resolved",
		AutoCommitDecision: decision,
		BoundarySource:     boundarySource,
		ChangedPaths:       kept,
		WorkflowOwnedPaths: owned,
		AmbiguousPaths:     ambiguous,
		IgnoredPaths:       ignored,
		Warnings:           warnings,
	}
}

func eventChangedPaths(events []delta.Event) []string {
	paths := make([]string, 0)
	for _, event := range events {
		paths = append(paths, event.ChangedPaths...)
	}
	return normalizePaths(paths)
}

func claimedInitialDirtyPaths(events []delta.Event) map[string]struct{} {
	claimed := make(map[string]struct{})
	for _, event := range events {
		if event.GraphSemantics == nil {
			continue
		}
		value, ok := event.GraphSemantics["claimed_initial_dirty_paths"]
		if !ok {
			continue
		}
		for _, path := range claimPaths(value) {
			claimed[path] = struct{}{}
		}
	}
	return claimed
}

func claimPaths(value any) []string {
	switch paths := value.(type) {
	case []string:
		return normalizePaths(paths)
	case []any:
		out := make([]string, 0, len(paths))
		for _, path := range paths {
			if text, ok := path.(string); ok {
				out = append(out, text)
			}
		}
		return normalizePaths(out)
	default:
		return nil
	}
}

func stringSet(values []string) map[string]struct{} {
	set := make(map[string]struct{}, len(values))
	for _, value := range values {
		set[value] = struct{}{}
	}
	return set
}

func normalizePaths(paths []string) []string {
	out := make([]string, 0, len(paths))
	seen := make(map[string]struct{}, len(paths))
	for _, path := range paths {
		normalized := filepath.ToSlash(strings.TrimSpace(path))
		for strings.HasPrefix(normalized, "./") {
			normalized = strings.TrimPrefix(normalized, "./")
		}
		normalized = strings.Trim(normalized, "/")
		if normalized == "" {
			continue
		}
		if _, ok := seen[normalized]; ok {
			continue
		}
		seen[normalized] = struct{}{}
		out = append(out, normalized)
	}
	sort.Strings(out)
	return out
}
