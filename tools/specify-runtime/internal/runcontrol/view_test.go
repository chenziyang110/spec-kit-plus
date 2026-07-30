package runcontrol

import (
	"context"
	"path/filepath"
	"testing"
)

func TestViewEnforcesSQLiteQueryOnlyMode(t *testing.T) {
	ctx := context.Background()
	databasePath := filepath.Join(t.TempDir(), "run-control.sqlite")
	store, err := Open(ctx, databasePath, WithOwnerEpoch("view_writer"))
	if err != nil {
		t.Fatal(err)
	}
	queued, err := store.EnqueueRun(ctx, CreateRunParams{
		RunID:        "run_view_query_only",
		Kind:         "quick",
		SubjectType:  "feature",
		SubjectID:    "view-query-only",
		TargetRef:    "HEAD",
		IntentSHA256: digestForTest("view query only"),
	})
	if err != nil {
		t.Fatal(err)
	}
	if err := store.Close(); err != nil {
		t.Fatal(err)
	}

	view, err := OpenView(ctx, databasePath)
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { _ = view.Close() })
	if _, err := view.db.ExecContext(ctx, `UPDATE runs SET status = 'cancelled' WHERE run_id = ?`, queued.RunID); err == nil {
		t.Fatal("query-only View accepted a write")
	}
	loaded, err := view.GetRun(ctx, queued.RunID)
	if err != nil {
		t.Fatal(err)
	}
	if loaded.Status != RunQueued || loaded.Revision != queued.Revision {
		t.Fatalf("run changed through View: %#v", loaded)
	}
	if err := view.Close(); err != nil {
		t.Fatal(err)
	}
	if err := view.Close(); err != nil {
		t.Fatalf("second View.Close() error = %v", err)
	}
}
