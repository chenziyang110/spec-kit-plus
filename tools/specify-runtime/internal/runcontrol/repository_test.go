package runcontrol

import (
	"context"
	"errors"
	"os"
	"os/exec"
	"path/filepath"
	"reflect"
	"strings"
	"testing"
	"time"
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

func TestOpenForRepositorySharesWorkAcrossWorktrees(t *testing.T) {
	mainRoot, worktreeRoot := createLinkedRepository(t)
	ctx := context.Background()
	mainStore, err := OpenForRepository(ctx, mainRoot)
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { _ = mainStore.Close() })
	created, _, err := mainStore.BeginWork(ctx, BeginWorkParams{
		WorkID: "shared-work", Summary: "shared work", AgentID: "main-agent", AdapterID: "codex",
		WorkspaceRoot: mainRoot, LeaseUntil: time.Now().UTC().Add(time.Hour),
		WriteIntents: []WriteIntentSpec{{Path: "src/shared.go", Operation: WriteModify, Confidence: IntentConfirmed}},
	})
	if err != nil {
		t.Fatal(err)
	}
	linkedStore, err := OpenForRepository(ctx, worktreeRoot)
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { _ = linkedStore.Close() })
	loaded, intents, err := linkedStore.GetWork(ctx, created.WorkID)
	if err != nil {
		t.Fatal(err)
	}
	if !reflect.DeepEqual(loaded, created) || len(intents) != 1 || intents[0].Path != "src/shared.go" {
		t.Fatalf("linked work = %#v, intents = %#v", loaded, intents)
	}
}

func TestInspectWorkspaceChangesIncludesBothSidesOfRename(t *testing.T) {
	mainRoot, _ := createLinkedRepository(t)
	if err := os.Rename(filepath.Join(mainRoot, "README.md"), filepath.Join(mainRoot, "RENAMED.md")); err != nil {
		t.Fatal(err)
	}
	runGit(t, ensureGitAvailable(t), mainRoot, "add", "-A")

	paths, err := InspectWorkspaceChanges(context.Background(), mainRoot)
	if err != nil {
		t.Fatal(err)
	}
	if len(paths) != 2 || paths[0] != "README.md" || paths[1] != "RENAMED.md" {
		t.Fatalf("renamed workspace paths = %#v, want both original and destination", paths)
	}
}

func TestInspectWorkspaceDeltaDetectsDeletedPreexistingUntrackedPath(t *testing.T) {
	mainRoot, _ := createLinkedRepository(t)
	relativePath := "preexisting-untracked.txt"
	absolutePath := filepath.Join(mainRoot, relativePath)
	if err := os.WriteFile(absolutePath, []byte("user work before activity\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	baseline, err := CaptureWorkspaceBaseline(context.Background(), mainRoot)
	if err != nil {
		t.Fatal(err)
	}
	baselineJSON, err := EncodeWorkspaceBaseline(baseline)
	if err != nil {
		t.Fatal(err)
	}
	if err := os.Remove(absolutePath); err != nil {
		t.Fatal(err)
	}

	paths, err := InspectWorkspaceDelta(context.Background(), mainRoot, baselineJSON)
	if err != nil {
		t.Fatal(err)
	}
	if len(paths) != 1 || paths[0] != relativePath {
		t.Fatalf("workspace delta = %#v, want deleted preexisting path", paths)
	}
}

func TestWorkspaceBaselineToleratesUntrackedNestedWorktree(t *testing.T) {
	ctx := context.Background()
	mainRoot, _ := createLinkedRepository(t)
	nestedRoot := filepath.Join(mainRoot, "nested copies", "parallel work")
	runGit(t, ensureGitAvailable(t), mainRoot, "worktree", "add", "--detach", nestedRoot, "HEAD")
	baseline, err := CaptureWorkspaceBaseline(ctx, mainRoot)
	if err != nil {
		t.Fatalf("baseline with an untracked nested worktree: %v", err)
	}
	if !reflect.DeepEqual(baseline.DirtyPaths, []string{"nested copies/parallel work"}) {
		t.Fatalf("nested worktree baseline paths = %#v", baseline.DirtyPaths)
	}
	baselineJSON, err := EncodeWorkspaceBaseline(baseline)
	if err != nil {
		t.Fatal(err)
	}
	nestedContent := []byte("another owner's unfinished work\n")
	if err := os.WriteFile(filepath.Join(nestedRoot, "README.md"), nestedContent, 0o644); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(mainRoot, "README.md"), []byte("this workspace changed\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	delta, err := InspectWorkspaceDelta(ctx, mainRoot, baselineJSON)
	if err != nil {
		t.Fatal(err)
	}
	if !reflect.DeepEqual(delta, []string{"README.md"}) {
		t.Fatalf("parent workspace delta = %#v, want only its own changed file", delta)
	}
	if content, err := os.ReadFile(filepath.Join(nestedRoot, "README.md")); err != nil || string(content) != string(nestedContent) {
		t.Fatalf("baseline audit changed nested worktree content: %q, %v", content, err)
	}
	if _, err := os.Stat(filepath.Join(mainRoot, ".git", "specify-runtime")); !errors.Is(err, os.ErrNotExist) {
		t.Fatalf("baseline materialized retired runtime storage: %v", err)
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

	runGit(t, gitPath, mainRoot, "init", "-b", "main")
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

func TestResolveRepositoryDistinguishesPlainDirectoryFromBrokenGitMetadata(t *testing.T) {
	ensureGitAvailable(t)
	parent := t.TempDir()
	plainDirectory := filepath.Join(parent, "plain")
	if err := os.MkdirAll(plainDirectory, 0o755); err != nil {
		t.Fatalf("create plain directory: %v", err)
	}
	t.Setenv("GIT_CEILING_DIRECTORIES", parent)

	_, err := ResolveRepository(context.Background(), plainDirectory)
	if !errors.Is(err, ErrNotGitRepository) {
		t.Fatalf("ResolveRepository(plain) error = %v, want ErrNotGitRepository", err)
	}
}

func TestResolveRepositoryDoesNotClassifyBrokenGitMetadataAsPlainDirectory(t *testing.T) {
	ensureGitAvailable(t)
	parent := t.TempDir()
	brokenDirectory := filepath.Join(parent, "broken")
	if err := os.MkdirAll(brokenDirectory, 0o755); err != nil {
		t.Fatalf("create broken directory: %v", err)
	}
	t.Setenv("GIT_CEILING_DIRECTORIES", parent)
	if err := os.WriteFile(filepath.Join(brokenDirectory, ".git"), []byte("gitdir: missing\n"), 0o644); err != nil {
		t.Fatalf("write broken .git file: %v", err)
	}

	_, err := ResolveRepository(context.Background(), brokenDirectory)
	if err == nil {
		t.Fatal("ResolveRepository(broken) error = nil, want broken Git metadata error")
	}
	if errors.Is(err, ErrNotGitRepository) || strings.Contains(err.Error(), ErrNotGitRepository.Error()) {
		t.Fatalf("ResolveRepository(broken) error = %v, want non-ErrNotGitRepository broken metadata error", err)
	}
}
