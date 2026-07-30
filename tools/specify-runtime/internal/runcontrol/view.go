package runcontrol

import (
	"context"
	"database/sql"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"sync"
)

// View provides a read-only handle over an existing run-control database.
// It never initializes schema, registers supervisor state, or writes shutdown
// metadata, so status/list commands can inspect existing state without
// materializing a control database.
type View struct {
	db        *sql.DB
	closeOnce sync.Once
	closeErr  error
}

func OpenView(ctx context.Context, databasePath string) (*View, error) {
	if strings.TrimSpace(databasePath) == "" {
		return nil, fmt.Errorf("%w: database path is required", ErrInvalidArgument)
	}
	absolutePath, err := filepath.Abs(databasePath)
	if err != nil {
		return nil, fmt.Errorf("resolve run control database path: %w", err)
	}
	absolutePath = filepath.Clean(absolutePath)
	if info, err := os.Stat(absolutePath); err != nil {
		if errors.Is(err, os.ErrNotExist) {
			return nil, fmt.Errorf("%w: run control database %q", ErrNotFound, absolutePath)
		}
		return nil, fmt.Errorf("inspect run control database: %w", err)
	} else if info.IsDir() {
		return nil, fmt.Errorf("%w: run control database %q is a directory", ErrInvalidArgument, absolutePath)
	}

	db, err := sql.Open("sqlite", absolutePath+"?mode=ro")
	if err != nil {
		return nil, fmt.Errorf("open run control database view: %w", err)
	}
	db.SetMaxOpenConns(1)
	db.SetMaxIdleConns(1)

	view := &View{db: db}
	if err := view.initialize(ctx); err != nil {
		_ = db.Close()
		return nil, err
	}
	return view, nil
}

func (view *View) initialize(ctx context.Context) error {
	if _, err := view.db.ExecContext(ctx, `PRAGMA query_only = ON`); err != nil {
		return fmt.Errorf("enable sqlite query_only mode: %w", err)
	}
	if _, err := view.db.ExecContext(ctx, fmt.Sprintf(`PRAGMA busy_timeout = %d`, sqliteBusyTimeoutMS)); err != nil {
		return fmt.Errorf("configure sqlite busy timeout: %w", err)
	}
	version, exists, err := existingSchemaVersion(ctx, view.db)
	if err != nil {
		return err
	}
	if !exists {
		return fmt.Errorf("%w: database has no run control metadata", ErrUnsupportedSchema)
	}
	if version != schemaVersion {
		return fmt.Errorf("%w: database has version %d, runtime requires %d", ErrUnsupportedSchema, version, schemaVersion)
	}
	return nil
}

func (view *View) Close() error {
	if view == nil || view.db == nil {
		return nil
	}
	view.closeOnce.Do(func() {
		if err := view.db.Close(); err != nil {
			view.closeErr = fmt.Errorf("close run control database view: %w", err)
		}
	})
	return view.closeErr
}

func (view *View) GetRun(ctx context.Context, runID string) (Run, error) {
	if strings.TrimSpace(runID) == "" {
		return Run{}, fmt.Errorf("%w: run id is required", ErrInvalidArgument)
	}
	return readRunTx(ctx, view.db, runID)
}

func (view *View) ListRunEvents(ctx context.Context, runID string) ([]Event, error) {
	if strings.TrimSpace(runID) == "" {
		return nil, fmt.Errorf("%w: run id is required", ErrInvalidArgument)
	}
	rows, err := view.db.QueryContext(ctx, `
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
