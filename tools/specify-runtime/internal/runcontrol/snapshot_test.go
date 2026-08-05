package runcontrol

import (
	"context"
	"errors"
	"os"
	"path/filepath"
	"testing"
	"time"
)

func TestForegroundSupervisorCapturesImmutableAmbientSnapshotWithoutChangingSource(t *testing.T) {
	t.Setenv(foregroundHelperEnvironment, "1")
	mainRoot, _ := createLinkedRepository(t)
	repository, err := ResolveRepository(context.Background(), mainRoot)
	if err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(mainRoot, "README.md"), []byte("ambient tracked\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(mainRoot, "ambient-note.txt"), []byte("ambient untracked\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	sourceStatus := runGit(t, ensureGitAvailable(t), mainRoot, "status", "--porcelain=v2", "--untracked-files=all")
	queued := enqueueForegroundTestRun(t, repository, "snapshot_prelaunch")
	readyPath := filepath.Join(t.TempDir(), "snapshot-ready")
	ctx, cancel := context.WithCancel(context.Background())
	t.Cleanup(cancel)

	type completion struct {
		result SupervisedRun
		err    error
	}
	done := make(chan completion, 1)
	go func() {
		result, runErr := SuperviseRun(ctx, repository, foregroundTestParams(
			queued.RunID,
			"block",
			readyPath,
		))
		done <- completion{result: result, err: runErr}
	}()
	waitForForegroundHelper(t, readyPath)

	observer := openTestStore(t, repository.DatabasePath, WithOwnerEpoch("snapshot_observer"))
	snapshot, err := observer.GetSnapshotForRun(context.Background(), queued.RunID)
	if err != nil {
		t.Fatal(err)
	}
	entries, err := observer.ListSnapshotEntries(context.Background(), snapshot.SnapshotID)
	if err != nil {
		t.Fatal(err)
	}
	if snapshot.RunID != queued.RunID || snapshot.SourceRoot != mainRoot ||
		snapshot.BaseCommit == "" || snapshot.BaseTree == "" ||
		snapshot.OverlayManifestSHA256 == "" || snapshot.InputManifestSHA256 == "" {
		t.Fatalf("snapshot = %#v, want immutable source/base/manifest binding", snapshot)
	}
	byPath := make(map[string]SnapshotEntry, len(entries))
	for _, entry := range entries {
		byPath[entry.RelativePath] = entry
	}
	if entry := byPath["README.md"]; entry.Provenance != SnapshotProvenanceUnstaged ||
		entry.DeliveryPolicy != SnapshotContextOnly || entry.BlobSHA256 == "" {
		t.Fatalf("tracked ambient entry = %#v", entry)
	}
	if entry := byPath["ambient-note.txt"]; entry.Provenance != SnapshotProvenanceUntracked ||
		entry.DeliveryPolicy != SnapshotContextOnly || entry.BlobSHA256 == "" {
		t.Fatalf("untracked ambient entry = %#v", entry)
	}
	if got := runGit(t, ensureGitAvailable(t), mainRoot, "status", "--porcelain=v2", "--untracked-files=all"); got != sourceStatus {
		t.Fatalf("snapshot capture changed source status:\n got: %q\nwant: %q", got, sourceStatus)
	}
	if got := runGit(t, ensureGitAvailable(t), mainRoot, "rev-parse", "HEAD"); got != snapshot.BaseCommit {
		t.Fatalf("snapshot capture changed source HEAD: got %q want %q", got, snapshot.BaseCommit)
	}
	if _, err := os.Stat(filepath.Join(mainRoot, "snapshot-prelaunch-marker.txt")); !errors.Is(err, os.ErrNotExist) {
		t.Fatalf("primary worktree received a runtime marker: %v", err)
	}

	loadedAgain, err := observer.GetSnapshotForRun(context.Background(), queued.RunID)
	if err != nil {
		t.Fatal(err)
	}
	if loadedAgain != snapshot {
		t.Fatalf("snapshot read changed immutable record: first=%#v second=%#v", snapshot, loadedAgain)
	}
	if _, err := observer.CreateSnapshot(context.Background(), CreateSnapshotParams{
		RunID:      queued.RunID,
		TargetRef:  snapshot.TargetRef,
		SourceRoot: snapshot.SourceRoot,
	}); !errors.Is(err, ErrAlreadyExists) {
		t.Fatalf("second snapshot creation error = %v, want ErrAlreadyExists", err)
	}

	cancel()
	select {
	case finished := <-done:
		if !errors.Is(finished.err, context.Canceled) {
			t.Fatalf("cancelled snapshot supervision error = %v, want context.Canceled", finished.err)
		}
	case <-time.After(10 * time.Second):
		t.Fatal("cancelled snapshot supervision did not stop")
	}
}
