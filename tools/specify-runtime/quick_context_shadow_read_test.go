package main

import (
	"bytes"
	"context"
	"errors"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

// These tests exercise the actual bounded reader and project-path owner.
// They do not create confirmation approvals or substitute workflow acceptance.
func TestQuickShadowReadPreservesExactBytesAndFiles(t *testing.T) {
	root := t.TempDir()
	relative := ".planning/quick/example/confirmation.json"
	name := filepath.Join(root, filepath.FromSlash(relative))
	if err := os.MkdirAll(filepath.Dir(name), 0700); err != nil {
		t.Fatal(err)
	}
	data := []byte("{\"goal\":\"修复登录😀\"}\r\n")
	if err := os.WriteFile(name, data, 0600); err != nil {
		t.Fatal(err)
	}
	before, err := os.Stat(name)
	if err != nil {
		t.Fatal(err)
	}
	for _, read := range []func() ([]byte, error){
		func() ([]byte, error) { return readQuickShadowState(root, relative) },
		func() ([]byte, error) { return readQuickShadowStateWithContext(context.Background(), root, relative) },
	} {
		got, err := read()
		if err != nil || !bytes.Equal(data, got) {
			t.Fatalf("bytes changed: %q %v", got, err)
		}
	}
	after, err := os.Stat(name)
	if err != nil {
		t.Fatal(err)
	}
	got, err := os.ReadFile(name)
	if err != nil || !bytes.Equal(got, data) || !os.SameFile(before, after) ||
		before.Mode() != after.Mode() || !before.ModTime().Equal(after.ModTime()) {
		t.Fatal("reader modified the source")
	}
}

func TestQuickShadowReadBudgetBoundaries(t *testing.T) {
	for _, size := range []int{0, quickShadowReadLimit, quickShadowReadLimit + 1} {
		root := t.TempDir()
		data := []byte(strings.Repeat("x", size))
		if err := os.WriteFile(filepath.Join(root, "state.json"), data, 0600); err != nil {
			t.Fatal(err)
		}
		got, err := readQuickShadowStateWithContext(context.Background(), root, "state.json")
		if size > quickShadowReadLimit {
			if err == nil || got != nil {
				t.Fatal("oversized source returned data")
			}
		} else if err != nil || !bytes.Equal(data, got) {
			t.Fatalf("valid byte budget rejected: size %d, %v", size, err)
		}
	}
	// Empty bytes are allowed by the byte reader; the owning JSON decoder must
	// reject them. A successful read alone is never valid-state evidence.
}

func TestQuickShadowReadCancellationBeforeFilesystemAccess(t *testing.T) {
	root := filepath.Join(t.TempDir(), "not-created")
	ctx, cancel := context.WithCancel(context.Background())
	cancel()
	got, err := readQuickShadowStateWithContext(ctx, root, "state.json")
	if !errors.Is(err, context.Canceled) || got != nil {
		t.Fatal(got, err)
	}
	if _, err := os.Stat(root); !os.IsNotExist(err) {
		t.Fatal("cancelled read touched absent root")
	}
	got, err = readQuickShadowStateWithContext(nil, root, "state.json")
	if err == nil || got != nil {
		t.Fatal("nil context returned state")
	}
}

func TestQuickShadowReadRejectsMissingDirectoryAndEscape(t *testing.T) {
	root := t.TempDir()
	if err := os.Mkdir(filepath.Join(root, "directory"), 0700); err != nil {
		t.Fatal(err)
	}
	for _, relative := range []string{"missing.json", "directory", "../outside.json"} {
		got, err := readQuickShadowStateWithContext(context.Background(), root, relative)
		if err == nil || got != nil {
			t.Fatalf("non-file or escape returned data: %q", relative)
		}
	}
}

func TestQuickShadowReadRejectsSymlinkAndAncestorAlias(t *testing.T) {
	root, outside := t.TempDir(), t.TempDir()
	if err := os.WriteFile(filepath.Join(outside, "state.json"), []byte("SECRET_TEST_FIXTURE"), 0600); err != nil {
		t.Fatal(err)
	}
	if err := os.Symlink(filepath.Join(outside, "state.json"), filepath.Join(root, "link.json")); err != nil {
		t.Skipf("symlink creation not available: %v", err)
	}
	if err := os.Symlink(outside, filepath.Join(root, "alias")); err != nil {
		t.Fatal(err)
	}
	for _, relative := range []string{"link.json", "alias/state.json"} {
		got, err := readQuickShadowStateWithContext(context.Background(), root, relative)
		if err == nil || got != nil || strings.Contains(err.Error(), "SECRET_TEST_FIXTURE") {
			t.Fatal("alias leaked source bytes", relative, err)
		}
	}
}
