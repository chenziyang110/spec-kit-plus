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
	"strings"
	"time"

	_ "modernc.org/sqlite"
)

const sqliteBusyTimeoutMS = 5000

type Store struct {
	db         *sql.DB
	ownerEpoch string
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

	db, err := sql.Open("sqlite", absolutePath)
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
	if _, err := store.db.ExecContext(ctx, `PRAGMA journal_mode = WAL`); err != nil {
		return fmt.Errorf("enable sqlite WAL: %w", err)
	}
	if _, err := store.db.ExecContext(ctx, schemaSQL); err != nil {
		return fmt.Errorf("initialize run control schema: %w", err)
	}
	now := time.Now().UTC().UnixMilli()
	transaction, err := store.db.BeginTx(ctx, nil)
	if err != nil {
		return fmt.Errorf("begin run control initialization: %w", err)
	}
	defer func() { _ = transaction.Rollback() }()
	if _, err := transaction.ExecContext(ctx, `
		INSERT INTO metadata (key, value) VALUES ('schema_version', ?)
		ON CONFLICT(key) DO UPDATE SET value = excluded.value
	`, fmt.Sprint(schemaVersion)); err != nil {
		return fmt.Errorf("record run control schema version: %w", err)
	}
	if _, err := transaction.ExecContext(ctx, `
		INSERT INTO supervisor_instances (
			owner_epoch, status, started_at_ms, heartbeat_at_ms, stopped_at_ms
		) VALUES (?, 'active', ?, ?, NULL)
		ON CONFLICT(owner_epoch) DO UPDATE SET
			status = 'active', heartbeat_at_ms = excluded.heartbeat_at_ms,
			stopped_at_ms = NULL
	`, store.ownerEpoch, now, now); err != nil {
		return fmt.Errorf("register supervisor epoch: %w", err)
	}
	if err := transaction.Commit(); err != nil {
		return fmt.Errorf("commit run control initialization: %w", err)
	}
	return nil
}

func (store *Store) Close() error {
	if store == nil || store.db == nil {
		return nil
	}
	now := time.Now().UTC().UnixMilli()
	_, updateErr := store.db.Exec(`
		UPDATE supervisor_instances
		SET status = 'stopped', heartbeat_at_ms = ?, stopped_at_ms = ?
		WHERE owner_epoch = ?
	`, now, now, store.ownerEpoch)
	closeErr := store.db.Close()
	if updateErr != nil {
		return fmt.Errorf("stop supervisor epoch: %w", updateErr)
	}
	if closeErr != nil {
		return fmt.Errorf("close run control database: %w", closeErr)
	}
	return nil
}

func (store *Store) CreateRun(ctx context.Context, params CreateRunParams) (Run, error) {
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
		Status:       RunAllocating,
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
	_, err = transaction.ExecContext(ctx, `
		INSERT INTO runs (
			run_id, kind, subject_type, subject_id, target_ref, intent_sha256,
			status, revision, current_fence, created_at_ms, updated_at_ms
		) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
	`, run.RunID, run.Kind, run.SubjectType, run.SubjectID, run.TargetRef,
		run.IntentSHA256, run.Status, run.Revision, run.CurrentFence,
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
	run.Revision++
	run.UpdatedAtMS = time.Now().UTC().UnixMilli()
	result, err := transaction.ExecContext(ctx, `
		UPDATE runs
		SET status = ?, revision = ?, updated_at_ms = ?
		WHERE run_id = ? AND revision = ?
	`, run.Status, run.Revision, run.UpdatedAtMS, run.RunID, expectedRevision)
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

func readRunTx(ctx context.Context, querier rowQuerier, runID string) (Run, error) {
	row := querier.QueryRowContext(ctx, `
		SELECT run_id, kind, subject_type, subject_id, target_ref, intent_sha256,
		       status, revision, current_fence, created_at_ms, updated_at_ms
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
	}{Status: run.Status, CurrentFence: run.CurrentFence})
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
		RunAllocating:  {RunReady: true, RunInterrupted: true, RunCancelled: true, RunFailed: true},
		RunReady:       {RunActive: true, RunInterrupted: true, RunCancelled: true, RunFailed: true},
		RunActive:      {RunSealing: true, RunInterrupted: true, RunCancelled: true, RunFailed: true},
		RunInterrupted: {RunReady: true, RunCancelled: true, RunFailed: true},
		RunSealing:     {RunSealed: true, RunInterrupted: true, RunCancelled: true, RunFailed: true},
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
