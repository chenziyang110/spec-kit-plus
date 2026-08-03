package runcontrol

import (
	"context"
	"crypto/rand"
	"database/sql"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"sync"
	"time"

	_ "modernc.org/sqlite"
)

const sqliteBusyTimeoutMS = 5000

type Store struct {
	db         *sql.DB
	ownerEpoch string
	closeOnce  sync.Once
	closeErr   error
}

type openConfig struct {
	ownerEpoch string
}

type OpenOption func(*openConfig) error

func WithOwnerEpoch(ownerEpoch string) OpenOption {
	return func(config *openConfig) error {
		ownerEpoch = strings.TrimSpace(ownerEpoch)
		if ownerEpoch == "" {
			return fmt.Errorf("%w: owner epoch is required", ErrInvalidArgument)
		}
		config.ownerEpoch = ownerEpoch
		return nil
	}
}

func Open(ctx context.Context, databasePath string, options ...OpenOption) (*Store, error) {
	if strings.TrimSpace(databasePath) == "" {
		return nil, fmt.Errorf("%w: database path is required", ErrInvalidArgument)
	}
	config := openConfig{}
	for _, option := range options {
		if option == nil {
			continue
		}
		if err := option(&config); err != nil {
			return nil, err
		}
	}
	if config.ownerEpoch == "" {
		ownerEpoch, err := newOwnerEpoch()
		if err != nil {
			return nil, err
		}
		config.ownerEpoch = ownerEpoch
	}

	absolutePath, err := filepath.Abs(databasePath)
	if err != nil {
		return nil, fmt.Errorf("resolve run control database path: %w", err)
	}
	if err := os.MkdirAll(filepath.Dir(absolutePath), 0o755); err != nil {
		return nil, fmt.Errorf("create run control database directory: %w", err)
	}

	db, err := sql.Open("sqlite", absolutePath+"?_txlock=immediate")
	if err != nil {
		return nil, fmt.Errorf("open run control database: %w", err)
	}
	// SQLite PRAGMAs such as foreign_keys and busy_timeout are connection-local.
	// One pooled connection per Store keeps those invariants deterministic;
	// independent Store instances still exercise real cross-connection locking.
	db.SetMaxOpenConns(1)
	db.SetMaxIdleConns(1)

	store := &Store{db: db, ownerEpoch: config.ownerEpoch}
	if err := store.initialize(ctx); err != nil {
		_ = db.Close()
		return nil, err
	}
	return store, nil
}

func (store *Store) initialize(ctx context.Context) error {
	if _, err := store.db.ExecContext(ctx, `PRAGMA foreign_keys = ON`); err != nil {
		return fmt.Errorf("enable sqlite foreign keys: %w", err)
	}
	if _, err := store.db.ExecContext(ctx, fmt.Sprintf(`PRAGMA busy_timeout = %d`, sqliteBusyTimeoutMS)); err != nil {
		return fmt.Errorf("configure sqlite busy timeout: %w", err)
	}
	if err := store.execInitializationPragma(ctx, `PRAGMA journal_mode = WAL`); err != nil {
		return fmt.Errorf("enable sqlite WAL: %w", err)
	}
	if _, err := store.db.ExecContext(ctx, `PRAGMA synchronous = FULL`); err != nil {
		return fmt.Errorf("configure sqlite synchronous mode: %w", err)
	}
	transaction, err := store.beginInitializationTransaction(ctx)
	if err != nil {
		return fmt.Errorf("begin run control initialization: %w", err)
	}
	defer func() { _ = transaction.Rollback() }()

	version, exists, err := existingSchemaVersion(ctx, transaction)
	if err != nil {
		return err
	}
	if exists && version != schemaVersion {
		switch version {
		case 3:
			if _, err := transaction.ExecContext(ctx, workspaceAllocationSchemaSQL); err != nil {
				return fmt.Errorf("migrate run control schema from version 3: %w", err)
			}
			fallthrough
		case 4:
			if _, err := transaction.ExecContext(ctx, candidateIntegrationSchemaSQL); err != nil {
				return fmt.Errorf("migrate run control schema from version %d: %w", version, err)
			}
			if _, err := transaction.ExecContext(ctx, `
				UPDATE metadata SET value = ? WHERE key = 'schema_version' AND value = ?
			`, fmt.Sprint(schemaVersion), fmt.Sprint(version)); err != nil {
				return fmt.Errorf("record migrated run control schema version: %w", err)
			}
		default:
			return fmt.Errorf("%w: database has version %d, runtime requires %d", ErrUnsupportedSchema, version, schemaVersion)
		}
	}
	if _, err := transaction.ExecContext(ctx, schemaSQL); err != nil {
		return fmt.Errorf("initialize run control schema: %w", err)
	}
	now := time.Now().UTC().UnixMilli()
	if _, err := transaction.ExecContext(ctx, `
		INSERT INTO metadata (key, value) VALUES ('schema_version', ?)
		ON CONFLICT(key) DO NOTHING
	`, fmt.Sprint(schemaVersion)); err != nil {
		return fmt.Errorf("record run control schema version: %w", err)
	}
	if _, err := transaction.ExecContext(ctx, `
		INSERT INTO supervisor_instances (
			owner_epoch, status, started_at_ms, heartbeat_at_ms, stopped_at_ms
		) VALUES (?, 'active', ?, ?, NULL)
	`, store.ownerEpoch, now, now); err != nil {
		if isUniqueConstraintError(err) {
			return fmt.Errorf("%w: %q", ErrOwnerEpochConflict, store.ownerEpoch)
		}
		return fmt.Errorf("register supervisor epoch: %w", err)
	}
	if err := transaction.Commit(); err != nil {
		return fmt.Errorf("commit run control initialization: %w", err)
	}
	return nil
}

func (store *Store) execInitializationPragma(ctx context.Context, statement string) error {
	deadline := time.Now().Add(time.Duration(sqliteBusyTimeoutMS) * time.Millisecond)
	for {
		if _, err := store.db.ExecContext(ctx, statement); err != nil {
			if !isSQLiteContention(err) || !time.Now().Before(deadline) {
				return err
			}
			if err := waitForSQLiteRetry(ctx); err != nil {
				return err
			}
			continue
		}
		return nil
	}
}

func (store *Store) beginInitializationTransaction(ctx context.Context) (*sql.Tx, error) {
	deadline := time.Now().Add(time.Duration(sqliteBusyTimeoutMS) * time.Millisecond)
	for {
		transaction, err := store.db.BeginTx(ctx, nil)
		if err == nil {
			return transaction, nil
		}
		if !isSQLiteContention(err) || !time.Now().Before(deadline) {
			return nil, err
		}
		if err := waitForSQLiteRetry(ctx); err != nil {
			return nil, err
		}
	}
}

func waitForSQLiteRetry(ctx context.Context) error {
	timer := time.NewTimer(10 * time.Millisecond)
	defer timer.Stop()
	select {
	case <-ctx.Done():
		return ctx.Err()
	case <-timer.C:
		return nil
	}
}

func (store *Store) Close() error {
	if store == nil || store.db == nil {
		return nil
	}
	store.closeOnce.Do(func() {
		now := time.Now().UTC()
		shutdownErr := store.shutdownOwnedState(context.Background(), now)
		_, updateErr := store.db.Exec(`
			UPDATE supervisor_instances
			SET status = 'stopped', heartbeat_at_ms = ?, stopped_at_ms = ?
			WHERE owner_epoch = ?
		`, now.UnixMilli(), now.UnixMilli(), store.ownerEpoch)
		closeErr := store.db.Close()
		switch {
		case shutdownErr != nil:
			store.closeErr = fmt.Errorf("interrupt supervisor-owned state: %w", shutdownErr)
		case updateErr != nil:
			store.closeErr = fmt.Errorf("stop supervisor epoch: %w", updateErr)
		case closeErr != nil:
			store.closeErr = fmt.Errorf("close run control database: %w", closeErr)
		}
	})
	return store.closeErr
}

func (store *Store) CreateRun(ctx context.Context, params CreateRunParams) (Run, error) {
	return store.createRun(ctx, params, RunAllocating)
}

// EnqueueRun records durable execution intent without claiming that a
// supervisor has started allocation. Queued Runs are neutral during owner
// reconciliation and must be claimed explicitly before workspace allocation.
func (store *Store) EnqueueRun(ctx context.Context, params CreateRunParams) (Run, error) {
	return store.createRun(ctx, params, RunQueued)
}

func (store *Store) createRun(ctx context.Context, params CreateRunParams, status RunStatus) (Run, error) {
	if err := validateCreateRunParams(params); err != nil {
		return Run{}, err
	}
	now := time.Now().UTC().UnixMilli()
	run := Run{
		RunID:        params.RunID,
		Kind:         params.Kind,
		SubjectType:  params.SubjectType,
		SubjectID:    params.SubjectID,
		TargetRef:    params.TargetRef,
		IntentSHA256: params.IntentSHA256,
		OwnerEpoch:   store.ownerEpoch,
		Status:       status,
		Revision:     1,
		CurrentFence: 0,
		CreatedAtMS:  now,
		UpdatedAtMS:  now,
	}
	transaction, err := store.db.BeginTx(ctx, nil)
	if err != nil {
		return Run{}, fmt.Errorf("begin create run: %w", err)
	}
	defer func() { _ = transaction.Rollback() }()
	if err := requireActiveSupervisorTx(ctx, transaction, store.ownerEpoch); err != nil {
		return Run{}, err
	}
	_, err = transaction.ExecContext(ctx, `
		INSERT INTO runs (
			run_id, kind, subject_type, subject_id, target_ref, intent_sha256,
			owner_epoch, status, revision, current_fence, created_at_ms, updated_at_ms
		) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
	`, run.RunID, run.Kind, run.SubjectType, run.SubjectID, run.TargetRef,
		run.IntentSHA256, run.OwnerEpoch, run.Status, run.Revision, run.CurrentFence,
		run.CreatedAtMS, run.UpdatedAtMS)
	if err != nil {
		if isUniqueConstraintError(err) {
			return Run{}, fmt.Errorf("%w: run %q", ErrAlreadyExists, run.RunID)
		}
		return Run{}, fmt.Errorf("insert run: %w", err)
	}
	if err := appendRunEventTx(ctx, transaction, run, RunEventCreated, "run created"); err != nil {
		return Run{}, err
	}
	if err := transaction.Commit(); err != nil {
		return Run{}, fmt.Errorf("commit create run: %w", err)
	}
	return run, nil
}

// ClaimRun transfers a queued request or an interrupted execution to the
// current supervisor. Interrupted Runs can be retried only after their old
// Attempt is fenced and every old workspace is non-usable; the next allocation
// therefore receives a strictly newer workspace generation.
func (store *Store) ClaimRun(ctx context.Context, runID string, expectedRevision int64) (Run, error) {
	if strings.TrimSpace(runID) == "" || expectedRevision <= 0 {
		return Run{}, fmt.Errorf("%w: run id and positive expected revision are required", ErrInvalidArgument)
	}
	transaction, err := store.db.BeginTx(ctx, nil)
	if err != nil {
		return Run{}, fmt.Errorf("begin claim run: %w", err)
	}
	defer func() { _ = transaction.Rollback() }()
	if err := requireActiveSupervisorTx(ctx, transaction, store.ownerEpoch); err != nil {
		return Run{}, err
	}

	run, err := readRunTx(ctx, transaction, runID)
	if err != nil {
		return Run{}, err
	}
	if run.Revision != expectedRevision {
		return Run{}, fmt.Errorf("%w: run %q is revision %d, expected %d", ErrRevisionConflict, run.RunID, run.Revision, expectedRevision)
	}
	if run.Status != RunQueued && run.Status != RunInterrupted {
		return Run{}, fmt.Errorf("%w: cannot claim run %q from %q", ErrInvalidTransition, run.RunID, run.Status)
	}
	if hasLiveAttempt, err := runHasLiveAttemptTx(ctx, transaction, run.RunID); err != nil {
		return Run{}, err
	} else if hasLiveAttempt {
		return Run{}, fmt.Errorf("%w: run %q still has a live attempt", ErrLiveAttempt, run.RunID)
	}
	var hasUsableWorkspace int
	if err := transaction.QueryRowContext(ctx, `
		SELECT EXISTS (
			SELECT 1 FROM workspaces
			WHERE run_id = ? AND status IN (?, ?, ?)
		)
	`, run.RunID, WorkspaceAllocating, WorkspaceReady, WorkspaceInUse).Scan(&hasUsableWorkspace); err != nil {
		return Run{}, fmt.Errorf("read usable workspace for run %q: %w", run.RunID, err)
	}
	if hasUsableWorkspace != 0 {
		return Run{}, fmt.Errorf("%w: run %q still has a usable workspace", ErrUsableWorkspace, run.RunID)
	}

	claimedFrom := run.Status
	nowMS := time.Now().UTC().UnixMilli()
	result, err := transaction.ExecContext(ctx, `
		UPDATE runs
		SET status = ?, owner_epoch = ?, revision = revision + 1, updated_at_ms = ?
		WHERE run_id = ? AND revision = ? AND current_fence = ? AND status = ?
	`, RunAllocating, store.ownerEpoch, nowMS, run.RunID, run.Revision, run.CurrentFence, run.Status)
	if err != nil {
		return Run{}, fmt.Errorf("claim run %q: %w", run.RunID, err)
	}
	if err := requireOneCASRow(result, ErrRevisionConflict, "claim run"); err != nil {
		return Run{}, err
	}
	run.Status = RunAllocating
	run.OwnerEpoch = store.ownerEpoch
	run.Revision++
	run.UpdatedAtMS = nowMS
	reason := "run claimed for allocation"
	if claimedFrom == RunInterrupted {
		reason = "interrupted run reclaimed for replacement allocation"
	}
	if err := appendRunEventTx(ctx, transaction, run, RunEventClaimed, reason); err != nil {
		return Run{}, err
	}
	if err := transaction.Commit(); err != nil {
		return Run{}, fmt.Errorf("commit claim run: %w", err)
	}
	return run, nil
}

func (store *Store) GetRun(ctx context.Context, runID string) (Run, error) {
	if strings.TrimSpace(runID) == "" {
		return Run{}, fmt.Errorf("%w: run id is required", ErrInvalidArgument)
	}
	return readRunTx(ctx, store.db, runID)
}

func (store *Store) TransitionRun(ctx context.Context, runID string, expectedRevision int64, target RunStatus, reason string) (Run, error) {
	if strings.TrimSpace(runID) == "" || expectedRevision < 1 {
		return Run{}, fmt.Errorf("%w: run id and positive expected revision are required", ErrInvalidArgument)
	}
	transaction, err := store.db.BeginTx(ctx, nil)
	if err != nil {
		return Run{}, fmt.Errorf("begin run transition: %w", err)
	}
	defer func() { _ = transaction.Rollback() }()
	if err := requireActiveSupervisorTx(ctx, transaction, store.ownerEpoch); err != nil {
		return Run{}, err
	}

	run, err := readRunTx(ctx, transaction, runID)
	if err != nil {
		return Run{}, err
	}
	if run.Revision != expectedRevision {
		return Run{}, fmt.Errorf("%w: run %q is revision %d, expected %d", ErrRevisionConflict, runID, run.Revision, expectedRevision)
	}
	if !canTransitionRun(run.Status, target) {
		return Run{}, fmt.Errorf("%w: %s -> %s", ErrInvalidTransition, run.Status, target)
	}
	run.Status = target
	run.OwnerEpoch = store.ownerEpoch
	run.Revision++
	run.UpdatedAtMS = time.Now().UTC().UnixMilli()
	result, err := transaction.ExecContext(ctx, `
		UPDATE runs
		SET status = ?, owner_epoch = ?, revision = ?, updated_at_ms = ?
		WHERE run_id = ? AND revision = ?
	`, run.Status, run.OwnerEpoch, run.Revision, run.UpdatedAtMS, run.RunID, expectedRevision)
	if err != nil {
		return Run{}, fmt.Errorf("update run transition: %w", err)
	}
	updated, err := result.RowsAffected()
	if err != nil {
		return Run{}, fmt.Errorf("count updated runs: %w", err)
	}
	if updated != 1 {
		return Run{}, fmt.Errorf("%w: run %q changed concurrently", ErrRevisionConflict, runID)
	}
	if err := appendRunEventTx(ctx, transaction, run, RunEventTransitioned, reason); err != nil {
		return Run{}, err
	}
	if err := transaction.Commit(); err != nil {
		return Run{}, fmt.Errorf("commit run transition: %w", err)
	}
	return run, nil
}

func (store *Store) ListRunEvents(ctx context.Context, runID string) ([]Event, error) {
	if strings.TrimSpace(runID) == "" {
		return nil, fmt.Errorf("%w: run id is required", ErrInvalidArgument)
	}
	rows, err := store.db.QueryContext(ctx, `
		SELECT event_id, aggregate_type, aggregate_id, aggregate_revision,
		       event_type, reason, payload_json, created_at_ms
		FROM events
		WHERE aggregate_type = 'run' AND aggregate_id = ?
		ORDER BY aggregate_revision, event_id
	`, runID)
	if err != nil {
		return nil, fmt.Errorf("list run events: %w", err)
	}
	defer rows.Close()
	events := make([]Event, 0)
	for rows.Next() {
		var event Event
		if err := rows.Scan(
			&event.EventID,
			&event.AggregateType,
			&event.AggregateID,
			&event.AggregateRevision,
			&event.EventType,
			&event.Reason,
			&event.PayloadJSON,
			&event.CreatedAtMS,
		); err != nil {
			return nil, fmt.Errorf("scan run event: %w", err)
		}
		events = append(events, event)
	}
	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("iterate run events: %w", err)
	}
	return events, nil
}

type rowQuerier interface {
	QueryRowContext(context.Context, string, ...any) *sql.Row
}

func requireActiveSupervisorTx(ctx context.Context, querier rowQuerier, ownerEpoch string) error {
	var status string
	if err := querier.QueryRowContext(ctx, `
		SELECT status FROM supervisor_instances WHERE owner_epoch = ?
	`, ownerEpoch).Scan(&status); err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			return fmt.Errorf("%w: supervisor epoch %q is not registered", ErrStaleFence, ownerEpoch)
		}
		return fmt.Errorf("read supervisor authority: %w", err)
	}
	if status != "active" {
		return fmt.Errorf("%w: supervisor epoch %q is %q", ErrStaleFence, ownerEpoch, status)
	}
	return nil
}

func readRunTx(ctx context.Context, querier rowQuerier, runID string) (Run, error) {
	row := querier.QueryRowContext(ctx, `
		SELECT run_id, kind, subject_type, subject_id, target_ref, intent_sha256,
		       owner_epoch, status, revision, current_fence, created_at_ms, updated_at_ms
		FROM runs
		WHERE run_id = ?
	`, runID)
	var run Run
	if err := row.Scan(
		&run.RunID,
		&run.Kind,
		&run.SubjectType,
		&run.SubjectID,
		&run.TargetRef,
		&run.IntentSHA256,
		&run.OwnerEpoch,
		&run.Status,
		&run.Revision,
		&run.CurrentFence,
		&run.CreatedAtMS,
		&run.UpdatedAtMS,
	); err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			return Run{}, fmt.Errorf("%w: run %q", ErrRunNotFound, runID)
		}
		return Run{}, fmt.Errorf("read run %q: %w", runID, err)
	}
	return run, nil
}

func appendRunEventTx(ctx context.Context, transaction *sql.Tx, run Run, eventType, reason string) error {
	payload, err := json.Marshal(struct {
		Status       RunStatus `json:"status"`
		CurrentFence int64     `json:"current_fence"`
		OwnerEpoch   string    `json:"owner_epoch"`
	}{Status: run.Status, CurrentFence: run.CurrentFence, OwnerEpoch: run.OwnerEpoch})
	if err != nil {
		return fmt.Errorf("encode run event: %w", err)
	}
	_, err = transaction.ExecContext(ctx, `
		INSERT INTO events (
			aggregate_type, aggregate_id, aggregate_revision,
			event_type, reason, payload_json, created_at_ms
		) VALUES ('run', ?, ?, ?, ?, ?, ?)
	`, run.RunID, run.Revision, eventType, reason, string(payload), run.UpdatedAtMS)
	if err != nil {
		return fmt.Errorf("append run event: %w", err)
	}
	return nil
}

func validateCreateRunParams(params CreateRunParams) error {
	required := map[string]string{
		"run_id":        params.RunID,
		"kind":          params.Kind,
		"subject_type":  params.SubjectType,
		"subject_id":    params.SubjectID,
		"target_ref":    params.TargetRef,
		"intent_sha256": params.IntentSHA256,
	}
	for name, value := range required {
		if strings.TrimSpace(value) == "" {
			return fmt.Errorf("%w: %s is required", ErrInvalidArgument, name)
		}
	}
	if !validSHA256(params.IntentSHA256) {
		return fmt.Errorf("%w: intent_sha256 must be a lowercase sha256 digest", ErrInvalidArgument)
	}
	return nil
}

func canTransitionRun(from, to RunStatus) bool {
	transitions := map[RunStatus]map[RunStatus]bool{
		RunQueued:      {},
		RunAllocating:  {RunReady: true},
		RunReady:       {RunParked: true},
		RunActive:      {},
		RunParked:      {RunReady: true},
		RunInterrupted: {RunReady: true},
		RunSealed:      {},
		RunCancelled:   {},
		RunFailed:      {},
	}
	allowed, knownFrom := transitions[from]
	if !knownFrom {
		return false
	}
	_, knownTo := transitions[to]
	return knownTo && allowed[to]
}

func existingSchemaVersion(ctx context.Context, db rowQuerier) (int, bool, error) {
	var tableCount int
	if err := db.QueryRowContext(ctx, `
		SELECT COUNT(*) FROM sqlite_master WHERE type = 'table' AND name = 'metadata'
	`).Scan(&tableCount); err != nil {
		return 0, false, fmt.Errorf("inspect run control metadata table: %w", err)
	}
	if tableCount == 0 {
		return 0, false, nil
	}
	var raw string
	if err := db.QueryRowContext(ctx, `SELECT value FROM metadata WHERE key = 'schema_version'`).Scan(&raw); err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			return 0, false, fmt.Errorf("%w: metadata has no schema_version", ErrUnsupportedSchema)
		}
		return 0, false, fmt.Errorf("read run control schema version: %w", err)
	}
	version, err := strconv.Atoi(strings.TrimSpace(raw))
	if err != nil {
		return 0, false, fmt.Errorf("%w: invalid schema_version %q", ErrUnsupportedSchema, raw)
	}
	return version, true, nil
}

func validSHA256(value string) bool {
	if len(value) != 64 {
		return false
	}
	for _, character := range value {
		if (character < '0' || character > '9') && (character < 'a' || character > 'f') {
			return false
		}
	}
	return true
}

func newOwnerEpoch() (string, error) {
	bytes := make([]byte, 16)
	if _, err := rand.Read(bytes); err != nil {
		return "", fmt.Errorf("generate supervisor epoch: %w", err)
	}
	return "supervisor_" + hex.EncodeToString(bytes), nil
}

func isUniqueConstraintError(err error) bool {
	return err != nil && strings.Contains(strings.ToLower(err.Error()), "unique constraint failed")
}
