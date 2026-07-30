package runcontrol

import (
	"context"
	"database/sql"
	"errors"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"
)

func TestOpenRejectsSchemaVersionOneAfterSchemaChanges(t *testing.T) {
	ctx := context.Background()
	databasePath := filepath.Join(t.TempDir(), "run-control.db")
	db, err := sql.Open("sqlite", databasePath)
	if err != nil {
		t.Fatalf("sql.Open() error = %v", err)
	}
	if _, err := db.Exec(`CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)`); err != nil {
		t.Fatalf("create metadata error = %v", err)
	}
	if _, err := db.Exec(`INSERT INTO metadata (key, value) VALUES ('schema_version', '1')`); err != nil {
		t.Fatalf("insert schema version error = %v", err)
	}
	if err := db.Close(); err != nil {
		t.Fatalf("close fixture database error = %v", err)
	}

	store, err := Open(ctx, databasePath, WithOwnerEpoch("supervisor_old_schema_v1"))
	if store != nil {
		_ = store.Close()
	}
	if !errors.Is(err, ErrUnsupportedSchema) {
		t.Fatalf("Open() error = %v, want ErrUnsupportedSchema for schema_version=1", err)
	}
}

func TestOpenRejectsSchemaVersionTwoAfterQueuedRunSchemaChange(t *testing.T) {
	ctx := context.Background()
	databasePath := filepath.Join(t.TempDir(), "run-control.db")
	db, err := sql.Open("sqlite", databasePath)
	if err != nil {
		t.Fatalf("sql.Open() error = %v", err)
	}
	if _, err := db.Exec(`CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)`); err != nil {
		t.Fatalf("create metadata error = %v", err)
	}
	if _, err := db.Exec(`INSERT INTO metadata (key, value) VALUES ('schema_version', '2')`); err != nil {
		t.Fatalf("insert schema version error = %v", err)
	}
	if err := db.Close(); err != nil {
		t.Fatalf("close fixture database error = %v", err)
	}

	store, err := Open(ctx, databasePath, WithOwnerEpoch("supervisor_old_schema_v2"))
	if store != nil {
		_ = store.Close()
	}
	if !errors.Is(err, ErrUnsupportedSchema) {
		t.Fatalf("Open() error = %v, want ErrUnsupportedSchema for schema_version=2", err)
	}
}

func TestOperationsSchemaRejectsCrossAttemptBinding(t *testing.T) {
	ctx := context.Background()
	store := openTestStore(t, filepath.Join(t.TempDir(), "run-control.db"))
	activeA, attemptA := createAuthorityActiveRun(t, store, "run_cross_attempt_a", time.Now().UTC())
	activeB, attemptB := createAuthorityActiveRun(t, store, "run_cross_attempt_b", time.Now().UTC())
	nowMS := time.Now().UTC().UnixMilli()

	_, err := store.db.ExecContext(ctx, `
		INSERT INTO operations (
			operation_id, kind, aggregate_type, aggregate_id,
			run_id, attempt_id, activity_id, workspace_id,
			owner_epoch, fence, run_revision,
			idempotency_key, request_sha256, status, revision,
			created_at_ms, updated_at_ms
		) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
	`, "op_cross_attempt_binding", "command.execute", "run", activeB.RunID,
		activeB.RunID, attemptA.AttemptID, attemptB.ActivityID, attemptB.WorkspaceID,
		store.ownerEpoch, attemptA.Fence, activeB.Revision,
		"command/cross-attempt-binding/1", digestForTest("cross-attempt-binding"),
		OperationPrepared, int64(1), nowMS, nowMS)
	if err == nil {
		t.Fatalf("insert operation with run %q and attempt %q from run %q succeeded; want FK rejection",
			activeB.RunID, attemptA.AttemptID, activeA.RunID)
	}
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
