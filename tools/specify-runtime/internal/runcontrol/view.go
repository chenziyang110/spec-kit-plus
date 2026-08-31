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
// It never initializes or migrates schema, reconciles work, or writes shutdown
// metadata. Shared tables absent in an older store project as empty state.
type View struct {
	db                     *sql.DB
	hasWorkBoard           bool
	hasExecutionActivities bool
	closeOnce              sync.Once
	closeErr               error
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

	db, err := sql.Open("sqlite", sqliteDataSource(absolutePath, "mode=ro"))
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
	if version < oldestSupportedSchemaVersion || version > schemaVersion {
		return fmt.Errorf("%w: database has version %d, supported versions are %d..%d",
			ErrUnsupportedSchema, version, oldestSupportedSchemaVersion, schemaVersion)
	}
	var workTables, executionTables, eventTables int
	if err := view.db.QueryRowContext(ctx, `
		SELECT
			COUNT(CASE WHEN name IN ('work_items', 'write_intents') THEN 1 END),
			COUNT(CASE WHEN name IN ('execution_activities', 'execution_resource_intents') THEN 1 END),
			COUNT(CASE WHEN name = 'events' THEN 1 END)
		FROM sqlite_master WHERE type = 'table'
	`).Scan(&workTables, &executionTables, &eventTables); err != nil {
		return fmt.Errorf("inspect shared board tables: %w", err)
	}
	if eventTables != 1 || (workTables != 0 && workTables != 2) ||
		(executionTables != 0 && executionTables != 2) ||
		(executionTables != 0 && workTables != 2) ||
		(version >= 12 && workTables != 2) || (version >= 13 && executionTables != 2) {
		return fmt.Errorf("%w: incomplete shared coordination tables", ErrUnsupportedSchema)
	}
	view.hasWorkBoard = workTables == 2
	view.hasExecutionActivities = executionTables == 2
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
