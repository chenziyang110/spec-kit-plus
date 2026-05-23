package store

import (
	"context"
	"database/sql"
	"encoding/json"
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

func OpenExisting(paths rt.Paths) (*Store, error) {
	info, err := os.Stat(paths.DatabasePath)
	if err != nil {
		return nil, fmt.Errorf("open sqlite: %w", err)
	}
	if info.Size() == 0 {
		return nil, fmt.Errorf("open sqlite: %s must not be empty", paths.DatabasePath)
	}
	db, err := sql.Open("sqlite", paths.DatabasePath)
	if err != nil {
		return nil, fmt.Errorf("open sqlite: %w", err)
	}
	if err := db.PingContext(context.Background()); err != nil {
		_ = db.Close()
		return nil, fmt.Errorf("open sqlite: %w", err)
	}
	return &Store{db: db}, nil
}

func (s *Store) Close() error {
	return s.db.Close()
}

func (s *Store) DB() *sql.DB {
	return s.db
}

func (s *Store) Init(ctx context.Context) error {
	if _, err := s.db.ExecContext(ctx, schemaSQL); err != nil {
		return fmt.Errorf("initialize schema: %w", err)
	}
	now := time.Now().UTC().Format(time.RFC3339)
	pairs := map[string]any{
		"runtime_format":  rt.RuntimeFormat,
		"runtime_schema":  rt.RuntimeSchema,
		"schema_version":  SchemaVersion,
		"generation":      now,
		"published_at":    now,
		"active_baseline": now,
	}
	for key, value := range pairs {
		encoded, err := json.Marshal(value)
		if err != nil {
			return fmt.Errorf("encode metadata %s: %w", key, err)
		}
		if _, err := s.db.ExecContext(ctx, `INSERT INTO metadata(key, value_json, updated_at) VALUES(?, ?, ?) ON CONFLICT(key) DO UPDATE SET value_json=excluded.value_json, updated_at=excluded.updated_at`, key, string(encoded), now); err != nil {
			return fmt.Errorf("write metadata %s: %w", key, err)
		}
	}
	return nil
}

func (s *Store) Metadata(ctx context.Context) (map[string]string, error) {
	valueColumn, err := metadataValueColumn(ctx, s.db)
	if err != nil {
		return nil, err
	}
	rows, err := s.db.QueryContext(ctx, `SELECT key, `+valueColumn+` FROM metadata ORDER BY key`)
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
		out[key] = decodeMetadataValue(value)
	}
	return out, rows.Err()
}

func metadataValueColumn(ctx context.Context, db *sql.DB) (string, error) {
	rows, err := db.QueryContext(ctx, `PRAGMA table_info(metadata)`)
	if err != nil {
		return "", fmt.Errorf("inspect metadata schema: %w", err)
	}
	defer rows.Close()
	hasValueJSON := false
	hasValue := false
	for rows.Next() {
		var cid int
		var name, typ string
		var notNull int
		var defaultValue sql.NullString
		var pk int
		if err := rows.Scan(&cid, &name, &typ, &notNull, &defaultValue, &pk); err != nil {
			return "", fmt.Errorf("scan metadata schema: %w", err)
		}
		if name == "value_json" {
			hasValueJSON = true
		}
		if name == "value" {
			hasValue = true
		}
	}
	if err := rows.Err(); err != nil {
		return "", err
	}
	if hasValueJSON {
		return "value_json", nil
	}
	if hasValue {
		return "value", nil
	}
	return "", fmt.Errorf("metadata table has no value_json column")
}

func decodeMetadataValue(value string) string {
	var decoded any
	if err := json.Unmarshal([]byte(value), &decoded); err != nil {
		return value
	}
	return fmt.Sprint(decoded)
}

func (s *Store) RecordUpdate(ctx context.Context, id, reason, changedPathsJSON string) error {
	generationID, err := s.ActiveGenerationID(ctx)
	if err != nil {
		return err
	}
	if generationID == "" {
		return nil
	}
	now := time.Now().UTC().Format(time.RFC3339)
	_, err = s.db.ExecContext(ctx, `INSERT INTO updates(id, generation_id, trigger, changed_paths_json, affected_nodes_json, affected_claims_json, affected_slices_json, result_state, completed_at, attrs_json) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`, id, generationID, reason, changedPathsJSON, "[]", "[]", "[]", "recorded", now, "{}")
	if err != nil {
		return fmt.Errorf("record update: %w", err)
	}
	return nil
}

func (s *Store) PublishRuntimeMetadata(ctx context.Context) (map[string]string, string, error) {
	generationID, err := s.ActiveGenerationID(ctx)
	if err != nil {
		return nil, "", err
	}
	if generationID == "" {
		return nil, "", fmt.Errorf("project-cognition.db has no active generation")
	}
	now := time.Now().UTC().Format(time.RFC3339)
	pairs := map[string]any{
		"runtime_format":          rt.RuntimeFormat,
		"runtime_schema":          rt.RuntimeSchema,
		"schema_version":          SchemaVersion,
		"active_generation_id":    generationID,
		"graph_store_path":        ".specify/project-cognition/project-cognition.db",
		"graph_ready":             true,
		"baseline_state":          "fresh",
		"query_contract_version":  1,
		"update_contract_version": 1,
		"published_at":            now,
	}
	for key, value := range pairs {
		encoded, err := json.Marshal(value)
		if err != nil {
			return nil, "", fmt.Errorf("encode metadata %s: %w", key, err)
		}
		if _, err := s.db.ExecContext(ctx, `INSERT INTO metadata(key, value_json, updated_at) VALUES(?, ?, ?) ON CONFLICT(key) DO UPDATE SET value_json=excluded.value_json, updated_at=excluded.updated_at`, key, string(encoded), now); err != nil {
			return nil, "", fmt.Errorf("write metadata %s: %w", key, err)
		}
	}
	meta, err := s.Metadata(ctx)
	if err != nil {
		return nil, "", err
	}
	return meta, generationID, nil
}

func (s *Store) ActiveGenerationID(ctx context.Context) (string, error) {
	rows, err := s.db.QueryContext(ctx, `SELECT id FROM generations WHERE state = 'active' ORDER BY sequence DESC, id DESC LIMIT 1`)
	if err != nil {
		return "", fmt.Errorf("read active generation: %w", err)
	}
	defer rows.Close()
	if !rows.Next() {
		return "", nil
	}
	var id string
	if err := rows.Scan(&id); err != nil {
		return "", fmt.Errorf("scan active generation: %w", err)
	}
	return id, rows.Err()
}

func (s *Store) NodesForPaths(ctx context.Context, paths []string) ([]map[string]any, error) {
	generationID, err := s.ActiveGenerationID(ctx)
	if err != nil {
		return nil, err
	}
	if generationID == "" {
		return []map[string]any{}, nil
	}
	if len(paths) == 0 {
		rows, err := s.db.QueryContext(ctx, `SELECT n.id, n.type, n.title, COALESCE(p.path, '') FROM nodes n LEFT JOIN path_index p ON p.generation_id = n.generation_id AND p.node_id = n.id WHERE n.generation_id = ? ORDER BY n.id LIMIT 25`, generationID)
		if err != nil {
			return nil, fmt.Errorf("query nodes: %w", err)
		}
		return scanNodeRows(rows)
	}
	out := make([]map[string]any, 0)
	for _, path := range paths {
		rows, err := s.db.QueryContext(ctx, `SELECT DISTINCT n.id, n.type, n.title, p.path FROM path_index p JOIN nodes n ON n.generation_id = p.generation_id AND n.id = p.node_id WHERE p.generation_id = ? AND (p.path = ? OR p.path LIKE ?) ORDER BY n.id LIMIT 25`, generationID, path, path+"%")
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
