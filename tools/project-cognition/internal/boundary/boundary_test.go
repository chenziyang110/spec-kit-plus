package boundary

import (
	"os"
	"path/filepath"
	"testing"

	"github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/config"
	"github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/delta"
)

func TestWorkflowOwnedPathsExcludeInitialDirty(t *testing.T) {
	result := Resolve(ResolveInput{
		Config: config.Config{
			ProjectCognition: config.ProjectCognitionConfig{AutoCommit: true},
		},
		Bundle: delta.Bundle{
			Session: delta.Session{
				Git: delta.GitContext{InitialDirtyPaths: []string{"src/user.go"}},
			},
			Events: []delta.Event{
				{ChangedPaths: []string{"src/task.go", "src/user.go"}},
			},
		},
		GitDiffPaths:      []string{"src/task.go", "src/user.go"},
		ExplicitArtifacts: []string{"docs/task.md"},
	})

	if result.AutoCommitDecision != "commit_skipped" {
		t.Fatalf("AutoCommitDecision = %q, want commit_skipped", result.AutoCommitDecision)
	}
	if !contains(result.WorkflowOwnedPaths, "src/task.go") {
		t.Fatalf("WorkflowOwnedPaths = %v, want src/task.go", result.WorkflowOwnedPaths)
	}
	if contains(result.WorkflowOwnedPaths, "src/user.go") {
		t.Fatalf("WorkflowOwnedPaths = %v, did not want src/user.go", result.WorkflowOwnedPaths)
	}
	if !contains(result.AmbiguousPaths, "src/user.go") {
		t.Fatalf("AmbiguousPaths = %v, want src/user.go", result.AmbiguousPaths)
	}
}

func TestClaimedInitialDirtyPathCanBeOwned(t *testing.T) {
	result := Resolve(ResolveInput{
		Config: config.Config{
			ProjectCognition: config.ProjectCognitionConfig{AutoCommit: true},
		},
		Bundle: delta.Bundle{
			Session: delta.Session{
				Git: delta.GitContext{InitialDirtyPaths: []string{"src/user.go"}},
			},
			Events: []delta.Event{
				{
					ChangedPaths: []string{"src/user.go"},
					GraphSemantics: map[string]any{
						"claimed_initial_dirty_paths": []any{"src/user.go"},
					},
				},
			},
		},
		GitDiffPaths: []string{"src/user.go"},
	})

	if result.AutoCommitDecision != "commit_created" {
		t.Fatalf("AutoCommitDecision = %q, want commit_created", result.AutoCommitDecision)
	}
	if !contains(result.WorkflowOwnedPaths, "src/user.go") {
		t.Fatalf("WorkflowOwnedPaths = %v, want src/user.go", result.WorkflowOwnedPaths)
	}
}

func TestAutoCommitDisabledByConfig(t *testing.T) {
	result := Resolve(ResolveInput{
		Config: config.Config{
			ProjectCognition: config.ProjectCognitionConfig{AutoCommit: false},
		},
		Bundle: delta.Bundle{
			Events: []delta.Event{
				{ChangedPaths: []string{"src/a.go"}},
			},
		},
	})

	if result.AutoCommitDecision != "commit_skipped" {
		t.Fatalf("AutoCommitDecision = %q, want commit_skipped", result.AutoCommitDecision)
	}
	if result.Outcome != "boundary_resolved" {
		t.Fatalf("Outcome = %q, want boundary_resolved", result.Outcome)
	}
}

func TestResolveUsesDeltaPathsWhenGitDiffEmpty(t *testing.T) {
	result := Resolve(ResolveInput{
		Config: config.Config{
			ProjectCognition: config.ProjectCognitionConfig{AutoCommit: true},
		},
		Bundle: delta.Bundle{
			Events: []delta.Event{
				{ChangedPaths: []string{"src/a.go"}},
			},
		},
	})

	if !contains(result.ChangedPaths, "src/a.go") {
		t.Fatalf("ChangedPaths = %v, want src/a.go", result.ChangedPaths)
	}
}

func TestIgnoredPathsAreRemoved(t *testing.T) {
	root := t.TempDir()
	if err := os.WriteFile(filepath.Join(root, ".cognitionignore"), []byte("vendor/\n"), 0o644); err != nil {
		t.Fatalf("write .cognitionignore: %v", err)
	}

	result := Resolve(ResolveInput{
		Root: root,
		Config: config.Config{
			ProjectCognition: config.ProjectCognitionConfig{AutoCommit: true},
		},
		Bundle: delta.Bundle{
			Events: []delta.Event{
				{ChangedPaths: []string{"src/a.go", "vendor/a.go"}},
			},
		},
	})

	if contains(result.ChangedPaths, "vendor/a.go") {
		t.Fatalf("ChangedPaths = %v, did not want vendor/a.go", result.ChangedPaths)
	}
	if !contains(result.IgnoredPaths, "vendor/a.go") {
		t.Fatalf("IgnoredPaths = %v, want vendor/a.go", result.IgnoredPaths)
	}
}

func contains(values []string, want string) bool {
	for _, value := range values {
		if value == want {
			return true
		}
	}
	return false
}
