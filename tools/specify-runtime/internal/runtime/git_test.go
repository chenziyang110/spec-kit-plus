package runtime

import (
	"os"
	"os/exec"
	"path/filepath"
	"testing"
)

func initGitRepo(t *testing.T) string {
	t.Helper()

	root := t.TempDir()
	runGit(t, root, "init")
	runGit(t, root, "config", "user.email", "test@example.com")
	runGit(t, root, "config", "user.name", "Test User")

	readmePath := filepath.Join(root, "README.md")
	if err := os.WriteFile(readmePath, []byte("# Test\n"), 0o644); err != nil {
		t.Fatalf("write README.md: %v", err)
	}
	runGit(t, root, "add", "README.md")
	runGit(t, root, "commit", "-m", "initial commit")

	return root
}

func runGit(t *testing.T, root string, args ...string) string {
	t.Helper()

	cmd := exec.Command("git", args...)
	cmd.Dir = root
	output, err := cmd.CombinedOutput()
	if err != nil {
		t.Fatalf("git %v failed: %v\n%s", args, err, output)
	}
	return string(output)
}

func TestGitHeadAndBranch(t *testing.T) {
	root := initGitRepo(t)

	head, err := GitHead(root)
	if err != nil {
		t.Fatalf("GitHead returned error: %v", err)
	}
	if head == "" {
		t.Fatal("GitHead returned empty HEAD")
	}

	branch, err := GitBranch(root)
	if err != nil {
		t.Fatalf("GitBranch returned error: %v", err)
	}
	if branch == "" {
		t.Fatal("GitBranch returned empty branch")
	}
}

func TestGitStatusEntriesIncludeStatusCodes(t *testing.T) {
	root := initGitRepo(t)

	if err := os.WriteFile(filepath.Join(root, "src.go"), []byte("package main\n"), 0o644); err != nil {
		t.Fatalf("write src.go: %v", err)
	}
	if err := os.WriteFile(filepath.Join(root, "README.md"), []byte("# Test\n\nupdated\n"), 0o644); err != nil {
		t.Fatalf("modify README.md: %v", err)
	}

	entries, err := GitStatusEntries(root)
	if err != nil {
		t.Fatalf("GitStatusEntries returned error: %v", err)
	}

	codes := map[string]string{}
	for _, entry := range entries {
		codes[entry.Path] = entry.Code
	}

	if codes["src.go"] != "??" {
		t.Fatalf("src.go status code = %q, want ??; entries=%v", codes["src.go"], entries)
	}
	if codes["README.md"] != "M" {
		t.Fatalf("README.md status code = %q, want M; entries=%v", codes["README.md"], entries)
	}
}

func TestGitStatusEntriesUnquoteEscapedPaths(t *testing.T) {
	root := initGitRepo(t)
	runGit(t, root, "config", "core.quotePath", "true")

	path := "caf\u00e9.go"
	if err := os.WriteFile(filepath.Join(root, path), []byte("package main\n"), 0o644); err != nil {
		t.Fatalf("write %s: %v", path, err)
	}

	entries, err := GitStatusEntries(root)
	if err != nil {
		t.Fatalf("GitStatusEntries returned error: %v", err)
	}

	for _, entry := range entries {
		if entry.Path == path {
			if entry.Code != "??" {
				t.Fatalf("%s status code = %q, want ??; entries=%v", path, entry.Code, entries)
			}
			return
		}
	}
	t.Fatalf("missing unquoted path %q; entries=%v", path, entries)
}

func TestGitDiffNameStatus(t *testing.T) {
	root := initGitRepo(t)
	base, err := GitHead(root)
	if err != nil {
		t.Fatalf("GitHead(base) returned error: %v", err)
	}

	if err := os.WriteFile(filepath.Join(root, "feature.txt"), []byte("feature\n"), 0o644); err != nil {
		t.Fatalf("write feature.txt: %v", err)
	}
	runGit(t, root, "add", "feature.txt")
	runGit(t, root, "commit", "-m", "add feature")

	head, err := GitHead(root)
	if err != nil {
		t.Fatalf("GitHead(head) returned error: %v", err)
	}

	entries, err := GitDiffNameStatus(root, base, head)
	if err != nil {
		t.Fatalf("GitDiffNameStatus returned error: %v", err)
	}
	if len(entries) != 1 {
		t.Fatalf("len(entries) = %d, want 1; entries=%v", len(entries), entries)
	}
	if entries[0].Path != "feature.txt" || entries[0].Code != "A" {
		t.Fatalf("entry = %+v, want {Path:%q Code:%q}", entries[0], "feature.txt", "A")
	}
}

func TestGitDiffNameStatusUnquoteEscapedPaths(t *testing.T) {
	root := initGitRepo(t)
	runGit(t, root, "config", "core.quotePath", "true")
	base, err := GitHead(root)
	if err != nil {
		t.Fatalf("GitHead(base) returned error: %v", err)
	}

	path := "caf\u00e9.txt"
	if err := os.WriteFile(filepath.Join(root, path), []byte("feature\n"), 0o644); err != nil {
		t.Fatalf("write %s: %v", path, err)
	}
	runGit(t, root, "add", path)
	runGit(t, root, "commit", "-m", "add quoted path")

	head, err := GitHead(root)
	if err != nil {
		t.Fatalf("GitHead(head) returned error: %v", err)
	}

	entries, err := GitDiffNameStatus(root, base, head)
	if err != nil {
		t.Fatalf("GitDiffNameStatus returned error: %v", err)
	}
	if len(entries) != 1 {
		t.Fatalf("len(entries) = %d, want 1; entries=%v", len(entries), entries)
	}
	if entries[0].Path != path || entries[0].Code != "A" {
		t.Fatalf("entry = %+v, want {Path:%q Code:%q}", entries[0], path, "A")
	}
}
