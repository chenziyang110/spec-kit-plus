package runcontrol

import (
	"context"
	"errors"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"testing"
)

func TestResolveRepositoryUsesSharedGitCommonDirectory(t *testing.T) {
	mainRoot, worktreeRoot := createLinkedRepository(t)
	nested := filepath.Join(mainRoot, "nested", "deeper")
	if err := os.MkdirAll(nested, 0o755); err != nil {
		t.Fatalf("create nested repository directory: %v", err)
	}

	ctx := context.Background()
	mainRepository, err := ResolveRepository(ctx, mainRoot)
	if err != nil {
		t.Fatalf("resolve main worktree: %v", err)
	}
	nestedRepository, err := ResolveRepository(ctx, nested)
	if err != nil {
		t.Fatalf("resolve nested repository directory: %v", err)
	}
	linkedRepository, err := ResolveRepository(ctx, worktreeRoot)
	if err != nil {
		t.Fatalf("resolve linked worktree: %v", err)
	}

	mainRoot = absoluteCleanPath(t, mainRoot)
	worktreeRoot = absoluteCleanPath(t, worktreeRoot)
	expectedCommonDir := filepath.Join(mainRoot, ".git")
	expectedDatabasePath := filepath.Join(expectedCommonDir, "specify-runtime", "run-control.sqlite")

	if mainRepository.Root != mainRoot {
		t.Fatalf("main repository root = %q, want %q", mainRepository.Root, mainRoot)
	}
	if nestedRepository.Root != mainRoot {
		t.Fatalf("nested repository root = %q, want %q", nestedRepository.Root, mainRoot)
	}
	if linkedRepository.Root != worktreeRoot {
		t.Fatalf("linked repository root = %q, want %q", linkedRepository.Root, worktreeRoot)
	}
	if mainRepository.Root == linkedRepository.Root {
		t.Fatalf("main and linked worktrees unexpectedly share root %q", mainRepository.Root)
	}

	for name, repository := range map[string]Repository{
		"main":   mainRepository,
		"nested": nestedRepository,
		"linked": linkedRepository,
	} {
		if !filepath.IsAbs(repository.CommonDir) {
			t.Errorf("%s common directory is not absolute: %q", name, repository.CommonDir)
		}
		if repository.CommonDir != expectedCommonDir {
			t.Errorf("%s common directory = %q, want %q", name, repository.CommonDir, expectedCommonDir)
		}
		if repository.DatabasePath != expectedDatabasePath {
			t.Errorf("%s database path = %q, want %q", name, repository.DatabasePath, expectedDatabasePath)
		}
	}
}

func TestResolveRepositoryRejectsNonGitDirectory(t *testing.T) {
	ensureGitAvailable(t)
	parent := t.TempDir()
	directory := filepath.Join(parent, "not-a-repository")
	if err := os.MkdirAll(directory, 0o755); err != nil {
		t.Fatal(err)
	}
	// Stop discovery above the fixture without manufacturing broken Git
	// metadata, which is a different and actionable failure class.
	t.Setenv("GIT_CEILING_DIRECTORIES", parent)

	_, err := ResolveRepository(context.Background(), directory)
	if !errors.Is(err, ErrNotGitRepository) {
		t.Fatalf("ResolveRepository error = %v, want %v", err, ErrNotGitRepository)
	}
}

func TestOpenForRepositorySharesRunDataAcrossWorktrees(t *testing.T) {
	mainRoot, worktreeRoot := createLinkedRepository(t)
	ctx := context.Background()

	mainStore, err := OpenForRepository(ctx, mainRoot, WithOwnerEpoch("main-view"))
	if err != nil {
		t.Fatalf("open store from main worktree: %v", err)
	}
	t.Cleanup(func() {
		if err := mainStore.Close(); err != nil {
			t.Errorf("close main store: %v", err)
		}
	})

	created, err := mainStore.CreateRun(ctx, CreateRunParams{
		RunID:        "run-shared-across-worktrees",
		Kind:         "sp-quick",
		SubjectType:  "feature",
		SubjectID:    "shared-database",
		TargetRef:    "HEAD",
		IntentSHA256: strings.Repeat("a", 64),
	})
	if err != nil {
		t.Fatalf("create run from main worktree: %v", err)
	}

	linkedStore, err := OpenForRepository(ctx, worktreeRoot, WithOwnerEpoch("linked-view"))
	if err != nil {
		t.Fatalf("open store from linked worktree: %v", err)
	}
	t.Cleanup(func() {
		if err := linkedStore.Close(); err != nil {
			t.Errorf("close linked store: %v", err)
		}
	})

	loaded, err := linkedStore.GetRun(ctx, created.RunID)
	if err != nil {
		t.Fatalf("load main-worktree run from linked worktree: %v", err)
	}
	if loaded.RunID != created.RunID || loaded.IntentSHA256 != created.IntentSHA256 {
		t.Fatalf("loaded run = %#v, want persisted run %#v", loaded, created)
	}
}

func createLinkedRepository(t *testing.T) (string, string) {
	t.Helper()
	gitPath := ensureGitAvailable(t)
	parent := t.TempDir()
	mainRoot := filepath.Join(parent, "main repository")
	worktreeRoot := filepath.Join(parent, "linked worktree")
	if err := os.MkdirAll(mainRoot, 0o755); err != nil {
		t.Fatalf("create main repository directory: %v", err)
	}

	runGit(t, gitPath, mainRoot, "init")
	runGit(t, gitPath, mainRoot, "config", "user.name", "Run Control Test")
	runGit(t, gitPath, mainRoot, "config", "user.email", "run-control@example.invalid")
	runGit(t, gitPath, mainRoot, "config", "commit.gpgsign", "false")
	if err := os.WriteFile(filepath.Join(mainRoot, "README.md"), []byte("run control repository test\n"), 0o644); err != nil {
		t.Fatalf("write initial repository file: %v", err)
	}
	runGit(t, gitPath, mainRoot, "add", "README.md")
	runGit(t, gitPath, mainRoot, "commit", "-m", "initial commit")
	runGit(t, gitPath, mainRoot, "worktree", "add", "--detach", worktreeRoot, "HEAD")

	return absoluteCleanPath(t, mainRoot), absoluteCleanPath(t, worktreeRoot)
}

func ensureGitAvailable(t *testing.T) string {
	t.Helper()
	gitPath, err := exec.LookPath("git")
	if err != nil {
		t.Skip("git executable is unavailable")
	}
	return gitPath
}

func runGit(t *testing.T, gitPath, directory string, arguments ...string) string {
	t.Helper()
	command := exec.Command(gitPath, arguments...)
	command.Dir = directory
	output, err := command.CombinedOutput()
	if err != nil {
		t.Fatalf("git %s failed in %q: %v\n%s", strings.Join(arguments, " "), directory, err, output)
	}
	return strings.TrimSpace(string(output))
}

func absoluteCleanPath(t *testing.T, path string) string {
	t.Helper()
	absolute, err := filepath.Abs(path)
	if err != nil {
		t.Fatalf("resolve absolute path %q: %v", path, err)
	}
	return filepath.Clean(absolute)
}
