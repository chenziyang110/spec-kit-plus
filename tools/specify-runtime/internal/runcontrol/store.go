package runcontrol

import (
	"context"
	"database/sql"
	"errors"
	"fmt"
	"net/url"
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
	db        *sql.DB
	closeOnce sync.Once
	closeErr  error
}

// StoreAccessError identifies a local filesystem boundary that prevented the
// repository-shared coordination store from opening. Callers keep this typed
// so an agent can repair project-local runtime state without misclassifying the
// failure as a user decision or external-system blocker.
type StoreAccessError struct {
	Stage string
	Path  string
	Cause error
}

func (err *StoreAccessError) Error() string {
	if err == nil {
		return "run control store is unavailable"
	}
	return fmt.Sprintf("run control store is unavailable during %s for %q: %v", err.Stage, err.Path, err.Cause)
}

func (err *StoreAccessError) Unwrap() error {
	if err == nil {
		return nil
	}
	return err.Cause
}

type openConfig struct{}

type OpenOption func(*openConfig) error

// WithOwnerEpoch is retained for source compatibility with older board callers.
// Deprecated: shared work owns its own fence and lease; this option registers
// no supervisor and grants no authority.
func WithOwnerEpoch(ownerEpoch string) OpenOption {
	ownerEpoch = strings.TrimSpace(ownerEpoch)
	return func(_ *openConfig) error {
		if ownerEpoch == "" {
			return fmt.Errorf("%w: owner epoch is required", ErrInvalidArgument)
		}
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
	absolutePath, err := filepath.Abs(databasePath)
	if err != nil {
		return nil, fmt.Errorf("resolve run control database path: %w", err)
	}
	if err := os.MkdirAll(filepath.Dir(absolutePath), 0o755); err != nil {
		return nil, &StoreAccessError{Stage: "create-directory", Path: absolutePath, Cause: err}
	}

	db, err := sql.Open("sqlite", sqliteDataSource(absolutePath, "_txlock=immediate"))
	if err != nil {
		return nil, &StoreAccessError{Stage: "open-database", Path: absolutePath, Cause: err}
	}
	// SQLite PRAGMAs such as foreign_keys and busy_timeout are connection-local.
	// One pooled connection per Store keeps those invariants deterministic;
	// independent Store instances still exercise real cross-connection locking.
	db.SetMaxOpenConns(1)
	db.SetMaxIdleConns(1)

	store := &Store{db: db}
	if err := store.initialize(ctx); err != nil {
		_ = db.Close()
		if isStoreAccessFailure(err) {
			return nil, &StoreAccessError{Stage: storeAccessStage(err), Path: absolutePath, Cause: err}
		}
		return nil, err
	}
	return store, nil
}

func isStoreAccessFailure(err error) bool {
	if err == nil {
		return false
	}
	if errors.Is(err, os.ErrPermission) {
		return true
	}
	message := strings.ToLower(err.Error())
	for _, marker := range []string{
		"unable to open database file", "attempt to write a readonly database",
		"readonly database", "read-only database", "permission denied", "access is denied",
	} {
		if strings.Contains(message, marker) {
			return true
		}
	}
	return false
}

func storeAccessStage(err error) string {
	message := strings.ToLower(err.Error())
	if strings.Contains(message, "wal") {
		return "enable-wal"
	}
	if strings.Contains(message, "initialization") || strings.Contains(message, "schema") {
		return "initialize-schema"
	}
	return "initialize-database"
}

// SQLite honors mode=ro only for file: URIs. Encode paths as URI paths so
// spaces, percent signs, and fragment characters cannot change their meaning.
func sqliteDataSource(absolutePath, query string) string {
	path := filepath.ToSlash(absolutePath)
	if !strings.HasPrefix(path, "/") {
		path = "/" + path
	}
	return (&url.URL{Scheme: "file", Path: path, RawQuery: query}).String()
}

// initialize installs only shared coordination state. Historical lifecycle
// tables are intentionally neither created nor modified. Schema migration is
// additive, and reopening never reconciles leases or starts background work.
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
		return fmt.Errorf("begin shared board initialization: %w", err)
	}
	defer func() { _ = transaction.Rollback() }()

	version, exists, err := existingSchemaVersion(ctx, transaction)
	if err != nil {
		return err
	}
	if exists && (version < oldestSupportedSchemaVersion || version > schemaVersion) {
		return fmt.Errorf("%w: database has version %d, supported versions are %d..%d",
			ErrUnsupportedSchema, version, oldestSupportedSchemaVersion, schemaVersion)
	}
	if _, err := transaction.ExecContext(ctx, schemaSQL); err != nil {
		return fmt.Errorf("initialize shared board schema: %w", err)
	}
	if !exists || version != schemaVersion {
		if _, err := transaction.ExecContext(ctx, `
			INSERT INTO metadata (key, value) VALUES ('schema_version', ?)
			ON CONFLICT(key) DO UPDATE SET value = excluded.value
		`, fmt.Sprint(schemaVersion)); err != nil {
			return fmt.Errorf("record shared board schema version: %w", err)
		}
	}
	if err := transaction.Commit(); err != nil {
		return fmt.Errorf("commit shared board initialization: %w", err)
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

// Close releases only this database handle. Durable work and historical rows
// belong to their recorded owners, not the lifetime of a CLI invocation.
func (store *Store) Close() error {
	if store == nil || store.db == nil {
		return nil
	}
	store.closeOnce.Do(func() {
		if err := store.db.Close(); err != nil {
			store.closeErr = fmt.Errorf("close shared board database: %w", err)
		}
	})
	return store.closeErr
}

type rowQuerier interface {
	QueryRowContext(context.Context, string, ...any) *sql.Row
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

func isUniqueConstraintError(err error) bool {
	return err != nil && strings.Contains(strings.ToLower(err.Error()), "unique constraint failed")
}

func requireOneCASRow(result sql.Result, conflict error, action string) error {
	rows, err := result.RowsAffected()
	if err != nil {
		return fmt.Errorf("read %s result: %w", action, err)
	}
	if rows != 1 {
		return fmt.Errorf("%w: %s compare-and-swap affected %d rows", conflict, action, rows)
	}
	return nil
}

func isSQLiteContention(err error) bool {
	if err == nil {
		return false
	}
	message := strings.ToLower(err.Error())
	return strings.Contains(message, "database is locked") ||
		strings.Contains(message, "database table is locked") ||
		strings.Contains(message, "sqlite_busy")
}
