package runcontrol

import (
	"context"
	"os"
	"path/filepath"
	"slices"
	"testing"

	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/filelock"
)

func TestWorkspaceBaselineDoesNotReadHeldDoLockAndRetainsRecoveryVisibility(t *testing.T) {
	root, _ := createLinkedRepository(t)
	const relative = ".specify/runtime/receipts/do-locks/fixture.lock"
	lockPath := filepath.Join(root, filepath.FromSlash(relative))
	if err := os.MkdirAll(filepath.Dir(lockPath), 0o700); err != nil {
		t.Fatal(err)
	}
	release, err := filelock.Acquire(lockPath)
	if err != nil {
		t.Fatal(err)
	}
	defer release()
	const canonical = ".planning/quick/Q001/STATUS.md"
	writeDeltaTestFile(t, root, canonical, "canonical workflow state\n")
	baseline, err := CaptureWorkspaceBaseline(context.Background(), root)
	if err != nil {
		t.Fatalf("held private Do lock blocked baseline capture: %v", err)
	}
	if !slices.Contains(baseline.DirtyPaths, relative) || !slices.Contains(baseline.DirtyPaths, canonical) {
		t.Fatalf("baseline lost ownership paths: %#v", baseline.DirtyPaths)
	}
	if baseline.PathDigests[relative] == "" {
		t.Fatal("baseline lost the private lock's existence/type state")
	}
	if baseline.PathDigests[canonical] == "" {
		t.Fatal("canonical workflow state escaped baseline hashing")
	}
	dirty, err := InspectWorkspaceChanges(context.Background(), root)
	if err != nil || !slices.Contains(dirty, relative) {
		t.Fatalf("Do lock disappeared from ownership recovery: %v %#v", err, dirty)
	}
}

func TestWorkspaceBaselineAndDeltaRetainHeldKnowledgeLocksAndCanonicalState(t *testing.T) {
	for _, relative := range []string{".specify/project-cognition/.update.lock", ".planning/learnings/.learning.lock", ".specify/runtime/locks/playbooks.lock"} {
		t.Run(filepath.Base(relative), func(t *testing.T) {
			root, _ := createLinkedRepository(t)
			lockPath := filepath.Join(root, filepath.FromSlash(relative))
			if err := os.MkdirAll(filepath.Dir(lockPath), 0o700); err != nil {
				t.Fatal(err)
			}
			release, err := filelock.Acquire(lockPath)
			if err != nil {
				t.Fatal(err)
			}
			defer release()
			const canonical = ".planning/learnings/candidates.md"
			writeDeltaTestFile(t, root, canonical, "initial canonical state\n")
			baseline, err := CaptureWorkspaceBaseline(context.Background(), root)
			if err != nil || baseline.PathDigests[relative] == "" || baseline.PathDigests[canonical] == "" {
				t.Fatalf("held private knowledge lock prevented complete baseline: %v %#v", err, baseline)
			}
			encoded, err := EncodeWorkspaceBaseline(baseline)
			if err != nil {
				t.Fatal(err)
			}
			writeDeltaTestFile(t, root, canonical, "changed canonical state\n")
			delta, err := InspectWorkspaceDelta(context.Background(), root, encoded)
			if err != nil || !slices.Contains(delta, canonical) || slices.Contains(delta, relative) {
				t.Fatalf("held lock obscured the real canonical delta: %v %#v", err, delta)
			}
			dirty, err := InspectWorkspaceChanges(context.Background(), root)
			if err != nil || !slices.Contains(dirty, relative) {
				t.Fatalf("held lock was removed from recovery inspection: %v %#v", err, dirty)
			}
		})
	}
}

func TestWorkspaceDeltaIgnoresPrivateLocksCreatedAfterBaseline(t *testing.T) {
	for _, relative := range []string{".specify/project-cognition/.update.lock", ".planning/learnings/.learning.lock", ".specify/runtime/locks/playbooks.lock"} {
		t.Run(filepath.Base(relative), func(t *testing.T) {
			root, _ := createLinkedRepository(t)
			baseline, err := CaptureWorkspaceBaseline(context.Background(), root)
			if err != nil {
				t.Fatal(err)
			}
			encoded, err := EncodeWorkspaceBaseline(baseline)
			if err != nil {
				t.Fatal(err)
			}
			lockPath := filepath.Join(root, filepath.FromSlash(relative))
			if err := os.MkdirAll(filepath.Dir(lockPath), 0o700); err != nil {
				t.Fatal(err)
			}
			release, err := filelock.Acquire(lockPath)
			if err != nil {
				t.Fatal(err)
			}
			defer release()
			delta, err := InspectWorkspaceDelta(context.Background(), root, encoded)
			if err != nil || slices.Contains(delta, relative) {
				t.Fatalf("new private lock entered execution delta: %v %#v", err, delta)
			}
			dirty, err := InspectWorkspaceChanges(context.Background(), root)
			if err != nil || !slices.Contains(dirty, relative) {
				t.Fatalf("new private lock disappeared from recovery inspection: %v %#v", err, dirty)
			}
		})
	}
}

func TestDoBaselineLockExclusionRequiresExactOwnerPath(t *testing.T) {
	for _, relative := range []string{
		".specify/runtime/receipts/do-locks/fixture.json",
		".specify/runtime/receipts/do-locks/nested/fixture.lock",
		".specify/runtime/receipts/do-locks/.lock",
		".specify/runtime/receipts/do-locks/.hidden.lock",
		".specify/runtime/receipts/do-locks/fixture.other.lock",
		".specify/runtime/receipts/do-locks-other/fixture.lock",
		"nested/.specify/runtime/receipts/do-locks/fixture.lock",
		".planning/e2e/fixture.lock",
	} {
		if isDoSessionRuntimeLockPath(relative) {
			t.Errorf("excluded a path outside the private Do lock owner: %s", relative)
		}
	}
}

func TestPrivateLockDigestStillReadsNeighborsAndDistinguishesMissingDirectoryAndSymlink(t *testing.T) {
	root, _ := createLinkedRepository(t)
	for _, relative := range []string{
		".specify/project-cognition/status.json", ".specify/project-cognition/.update.lock.notes",
		".planning/learnings/candidates.md", ".planning/learnings/.learning.lock.notes",
		".specify/runtime/locks/playbooks.lock.notes", ".specify/runtime/receipts/do-locks/.hidden.lock",
	} {
		writeDeltaTestFile(t, root, relative, "first bytes\n")
		before, err := workspacePathDigest(root, relative)
		if err != nil {
			t.Fatal(err)
		}
		writeDeltaTestFile(t, root, relative, "second bytes\n")
		after, err := workspacePathDigest(root, relative)
		if err != nil || before == after {
			t.Fatalf("neighboring state bytes became opaque: %s %v", relative, err)
		}
	}
	const regular = ".specify/runtime/receipts/do-locks/file.lock"
	writeDeltaTestFile(t, root, regular, "operational bytes\n")
	regularDigest, err := workspacePathDigest(root, regular)
	if err != nil {
		t.Fatal(err)
	}
	const directory = ".specify/runtime/receipts/do-locks/directory.lock"
	if err := os.Mkdir(filepath.Join(root, filepath.FromSlash(directory)), 0o700); err != nil {
		t.Fatal(err)
	}
	directoryDigest, err := workspacePathDigest(root, directory)
	if err != nil || directoryDigest == regularDigest {
		t.Fatalf("directory became a regular operational lock: %v", err)
	}
	missingDigest, err := workspacePathDigest(root, ".specify/runtime/receipts/do-locks/missing.lock")
	if err != nil || missingDigest == regularDigest {
		t.Fatalf("missing lock became existing operational state: %v", err)
	}
	t.Run("symlink", func(t *testing.T) {
		const linked = ".specify/runtime/receipts/do-locks/linked.lock"
		if err := os.Symlink(filepath.Join(root, filepath.FromSlash(regular)), filepath.Join(root, filepath.FromSlash(linked))); err != nil {
			t.Skipf("native symlink creation unavailable: %v", err)
		}
		linkedDigest, err := workspacePathDigest(root, linked)
		if err != nil || linkedDigest == regularDigest {
			t.Fatalf("symlink became a regular operational lock: %v", err)
		}
	})
}
