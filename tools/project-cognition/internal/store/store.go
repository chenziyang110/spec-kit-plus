package store

import (
	"context"
	"database/sql"
	"fmt"
	"os"
	"time"

	_ "modernc.org/sqlite"

	rt "github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/runtime"
)

type Store struct {
	db *sql.DB
}

func Open(paths rt.Paths) (*Store, error) {
	if err := os.MkdirAll(paths.RuntimeDir, 0o755); err != nil {
		return nil, fmt.Errorf("create runtime dir: %w", err)
	}
	db, err := sql.Open("sqlite", paths.DatabasePath)
	if err != nil {
		return nil, fmt.Errorf("open sqlite: %w", err)
	}
	store := &Store{db: db}
	if err := store.Init(context.Background()); err != nil {
		_ = db.Close()
		return nil, err
	}
	return store, nil
}

func (s *Store) Close() error {
	return s.db.Close()
}

func (s *Store) Init(ctx context.Context) error {
	if _, err := s.db.ExecContext(ctx, schemaSQL); err != nil {
		return fmt.Errorf("initialize schema: %w", err)
	}
	now := time.Now().UTC().Format(time.RFC3339)
	pairs := map[string]string{
		"runtime_format":  rt.RuntimeFormat,
		"runtime_schema":  fmt.Sprint(rt.RuntimeSchema),
		"schema_version":  fmt.Sprint(SchemaVersion),
		"generation":      now,
		"published_at":    now,
		"active_baseline": now,
	}
	for key, value := range pairs {
		if _, err := s.db.ExecContext(ctx, `INSERT INTO metadata(key, value) VALUES(?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value`, key, value); err != nil {
			return fmt.Errorf("write metadata %s: %w", key, err)
		}
	}
	return nil
}

func (s *Store) Metadata(ctx context.Context) (map[string]string, error) {
	rows, err := s.db.QueryContext(ctx, `SELECT key, value FROM metadata ORDER BY key`)
	if err != nil {
		return nil, fmt.Errorf("read metadata: %w", err)
	}
	defer rows.Close()
	out := map[string]string{}
	for rows.Next() {
		var key, value string
		if err := rows.Scan(&key, &value); err != nil {
			return nil, fmt.Errorf("scan metadata: %w", err)
		}
		out[key] = value
	}
	return out, rows.Err()
}

func (s *Store) RecordUpdate(ctx context.Context, id, reason, changedPathsJSON string) error {
	_, err := s.db.ExecContext(ctx, `INSERT INTO updates(id, reason, changed_paths, created_at) VALUES(?, ?, ?, ?)`, id, reason, changedPathsJSON, time.Now().UTC().Format(time.RFC3339))
	if err != nil {
		return fmt.Errorf("record update: %w", err)
	}
	return nil
}

func (s *Store) NodesForPaths(ctx context.Context, paths []string) ([]map[string]any, error) {
	if len(paths) == 0 {
		rows, err := s.db.QueryContext(ctx, `SELECT id, type, title, path FROM nodes ORDER BY id LIMIT 25`)
		if err != nil {
			return nil, fmt.Errorf("query nodes: %w", err)
		}
		return scanNodeRows(rows)
	}
	out := make([]map[string]any, 0)
	for _, path := range paths {
		rows, err := s.db.QueryContext(ctx, `SELECT id, type, title, path FROM nodes WHERE path = ? OR path LIKE ? ORDER BY id LIMIT 25`, path, path+"%")
		if err != nil {
			return nil, fmt.Errorf("query nodes for %s: %w", path, err)
		}
		nodes, err := scanNodeRows(rows)
		if err != nil {
			return nil, err
		}
		out = append(out, nodes...)
	}
	return out, nil
}

func scanNodeRows(rows *sql.Rows) ([]map[string]any, error) {
	defer rows.Close()
	out := make([]map[string]any, 0)
	for rows.Next() {
		var id, typ, title string
		var path sql.NullString
		if err := rows.Scan(&id, &typ, &title, &path); err != nil {
			return nil, fmt.Errorf("scan node: %w", err)
		}
		item := map[string]any{"id": id, "type": typ, "title": title}
		if path.Valid {
			item["path"] = path.String
		}
		out = append(out, item)
	}
	return out, rows.Err()
}
