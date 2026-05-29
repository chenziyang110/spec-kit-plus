package store

import (
	"context"
	"database/sql"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"time"

	_ "modernc.org/sqlite"

	rt "github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/runtime"
)

type Store struct {
	db *sql.DB
}

type ConceptCandidateRow struct {
	GenerationID         string
	NodeID               string
	NodeType             string
	Title                string
	Confidence           string
	AttrsJSON            string
	Paths                []string
	EvidenceIDs          []string
	EvidencePaths        []string
	ObservationSummaries []string
}

func Open(paths rt.Paths) (*Store, error) {
	if err := os.MkdirAll(paths.RuntimeDir, 0o755); err != nil {
		return nil, fmt.Errorf("create runtime dir: %w", err)
	}
	if _, err := ReplaceIncompatibleDatabase(paths); err != nil {
		return nil, err
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

func ReplaceIncompatibleDatabase(paths rt.Paths) (bool, error) {
	compatible, err := ExistingDatabaseCompatible(paths)
	if err != nil {
		return false, err
	}
	if compatible {
		return false, nil
	}
	archivePath, err := archiveDatabasePath(paths.DatabasePath)
	if err != nil {
		return false, err
	}
	if err := os.Rename(paths.DatabasePath, archivePath); err != nil {
		return false, fmt.Errorf("archive incompatible project-cognition.db: %w", err)
	}
	return true, nil
}

func ExistingDatabaseCompatible(paths rt.Paths) (bool, error) {
	info, err := os.Stat(paths.DatabasePath)
	if errors.Is(err, os.ErrNotExist) {
		return true, nil
	}
	if err != nil {
		return false, fmt.Errorf("stat project-cognition.db: %w", err)
	}
	if info.Size() == 0 {
		return false, nil
	}
	db, err := sql.Open("sqlite", paths.DatabasePath)
	if err != nil {
		return false, fmt.Errorf("open sqlite for schema compatibility check: %w", err)
	}
	defer db.Close()
	if err := db.PingContext(context.Background()); err != nil {
		return false, fmt.Errorf("open sqlite for schema compatibility check: %w", err)
	}
	return SchemaCompatible(context.Background(), db)
}

func SchemaCompatible(ctx context.Context, db *sql.DB) (bool, error) {
	for _, table := range RequiredTables() {
		exists, err := tableExists(ctx, db, table)
		if err != nil {
			return false, err
		}
		if !exists {
			return false, nil
		}
	}
	for table, requiredColumns := range RequiredTableColumns() {
		columns, err := tableColumns(ctx, db, table)
		if err != nil {
			return false, err
		}
		for _, column := range requiredColumns {
			if !columns[column] {
				return false, nil
			}
		}
	}
	return true, nil
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
	compatible, err := SchemaCompatible(context.Background(), db)
	if err != nil {
		_ = db.Close()
		return nil, fmt.Errorf("check sqlite schema compatibility: %w", err)
	}
	if !compatible {
		_ = db.Close()
		return nil, fmt.Errorf("project-cognition.db schema is incompatible; run sp-map-scan followed by sp-map-build")
	}
	return &Store{db: db}, nil
}

func tableExists(ctx context.Context, db *sql.DB, table string) (bool, error) {
	var name string
	err := db.QueryRowContext(ctx, `SELECT name FROM sqlite_master WHERE type IN ('table', 'view') AND name = ?`, table).Scan(&name)
	if errors.Is(err, sql.ErrNoRows) {
		return false, nil
	}
	if err != nil {
		return false, fmt.Errorf("inspect table %s: %w", table, err)
	}
	return true, nil
}

func tableColumns(ctx context.Context, db *sql.DB, table string) (map[string]bool, error) {
	rows, err := db.QueryContext(ctx, `PRAGMA table_info(`+quoteSQLiteIdentifier(table)+`)`)
	if err != nil {
		return nil, fmt.Errorf("inspect %s schema: %w", table, err)
	}
	defer rows.Close()
	columns := map[string]bool{}
	for rows.Next() {
		var cid int
		var name, typ string
		var notNull int
		var defaultValue sql.NullString
		var pk int
		if err := rows.Scan(&cid, &name, &typ, &notNull, &defaultValue, &pk); err != nil {
			return nil, fmt.Errorf("scan %s schema: %w", table, err)
		}
		columns[name] = true
	}
	return columns, rows.Err()
}

func archiveDatabasePath(databasePath string) (string, error) {
	base := databasePath + ".legacy"
	if _, err := os.Stat(base); errors.Is(err, os.ErrNotExist) {
		return base, nil
	} else if err != nil {
		return "", fmt.Errorf("stat legacy database archive: %w", err)
	}
	now := time.Now().UTC().Format("20060102T150405.000000000Z")
	for i := 0; i < 100; i++ {
		candidate := filepath.Join(filepath.Dir(databasePath), filepath.Base(databasePath)+".legacy."+now)
		if i > 0 {
			candidate = fmt.Sprintf("%s.%02d", candidate, i)
		}
		if _, err := os.Stat(candidate); errors.Is(err, os.ErrNotExist) {
			return candidate, nil
		} else if err != nil {
			return "", fmt.Errorf("stat legacy database archive: %w", err)
		}
	}
	return "", fmt.Errorf("could not choose legacy database archive path for %s", databasePath)
}

func quoteSQLiteIdentifier(identifier string) string {
	return `"` + strings.ReplaceAll(identifier, `"`, `""`) + `"`
}

func (s *Store) Close() error {
	return s.db.Close()
}

func (s *Store) DB() *sql.DB {
	return s.db
}

func GreenfieldEmptyEligible(root string) bool {
	eligible := true
	err := filepath.WalkDir(root, func(path string, d os.DirEntry, err error) error {
		if err != nil {
			eligible = false
			return filepath.SkipAll
		}
		rel, relErr := filepath.Rel(root, path)
		if relErr != nil {
			eligible = false
			return filepath.SkipAll
		}
		rel = filepath.ToSlash(rel)
		if rel == "." {
			return nil
		}
		if d.IsDir() && greenfieldSkipDir(rel) {
			return filepath.SkipDir
		}
		if d.IsDir() {
			return nil
		}
		if !greenfieldScaffoldFile(rel) {
			eligible = false
			return filepath.SkipAll
		}
		return nil
	})
	return err == nil && eligible
}

func greenfieldSkipDir(rel string) bool {
	return rel == ".git" ||
		rel == ".specify" ||
		rel == ".claude" ||
		rel == ".cursor" ||
		rel == ".gemini" ||
		rel == ".github" ||
		rel == ".qwen" ||
		rel == ".opencode" ||
		rel == ".codex" ||
		rel == ".windsurf" ||
		rel == ".kilocode" ||
		rel == ".junie" ||
		rel == ".augment" ||
		rel == ".roo" ||
		rel == ".codebuddy" ||
		rel == ".qoder" ||
		rel == ".kiro" ||
		rel == ".agents" ||
		rel == ".shai" ||
		rel == ".tabnine" ||
		rel == ".kimi" ||
		rel == ".pi" ||
		rel == ".iflow" ||
		rel == ".forge" ||
		rel == ".bob" ||
		rel == ".trae" ||
		rel == ".vibe"
}

func greenfieldScaffoldFile(rel string) bool {
	switch rel {
	case "AGENTS.md", "README.md", ".gitignore", ".cognitionignore":
		return true
	default:
		return false
	}
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

func (s *Store) PublishRuntimeMetadata(ctx context.Context, expectedGenerationID string, baselineKind string, afterCommit ...func() error) (map[string]string, string, error) {
	baselineKind = normalizeBaselineKind(baselineKind)
	expectedGenerationID = strings.TrimSpace(expectedGenerationID)
	if expectedGenerationID == "" {
		return nil, "", fmt.Errorf("expected generation id is required")
	}
	now := time.Now().UTC().Format(time.RFC3339)
	tx, err := s.db.BeginTx(ctx, nil)
	if err != nil {
		return nil, "", fmt.Errorf("begin ready metadata transaction: %w", err)
	}
	defer tx.Rollback()

	generationID, err := activeGenerationIDTx(ctx, tx)
	if err != nil {
		return nil, "", err
	}
	if generationID == "" {
		return nil, "", fmt.Errorf("project-cognition.db has no active generation")
	}
	if generationID != expectedGenerationID {
		return nil, "", fmt.Errorf("active generation changed before ready metadata publication: got %s, want %s", generationID, expectedGenerationID)
	}

	pairs := map[string]any{
		"runtime_format":          rt.RuntimeFormat,
		"runtime_schema":          rt.RuntimeSchema,
		"schema_version":          SchemaVersion,
		"active_generation_id":    generationID,
		"graph_store_path":        ".specify/project-cognition/project-cognition.db",
		"graph_ready":             true,
		"baseline_state":          "fresh",
		"baseline_kind":           baselineKind,
		"query_contract_version":  1,
		"update_contract_version": 1,
		"published_at":            now,
	}
	for key, value := range pairs {
		encoded, err := json.Marshal(value)
		if err != nil {
			return nil, "", fmt.Errorf("encode metadata %s: %w", key, err)
		}
		if _, err := tx.ExecContext(ctx, `INSERT INTO metadata(key, value_json, updated_at) VALUES(?, ?, ?) ON CONFLICT(key) DO UPDATE SET value_json=excluded.value_json, updated_at=excluded.updated_at`, key, string(encoded), now); err != nil {
			return nil, "", fmt.Errorf("write metadata %s: %w", key, err)
		}
	}
	if err := tx.Commit(); err != nil {
		return nil, "", fmt.Errorf("commit ready metadata transaction: %w", err)
	}
	activeGenerationID, err := s.ActiveGenerationID(ctx)
	if err != nil {
		return nil, "", err
	}
	if activeGenerationID != generationID {
		return nil, "", fmt.Errorf("active generation changed after ready metadata publication: got %s, want %s", activeGenerationID, generationID)
	}
	for _, fn := range afterCommit {
		if fn == nil {
			continue
		}
		if err := fn(); err != nil {
			return nil, "", err
		}
	}
	meta, err := s.Metadata(ctx)
	if err != nil {
		return nil, "", err
	}
	return meta, generationID, nil
}

func (s *Store) InitializeGreenfieldEmpty(ctx context.Context) (string, error) {
	generationID := "GEN-greenfield-" + time.Now().UTC().Format("20060102T150405.000000000Z")
	input := ImportInput{
		GenerationID: generationID,
		Kind:         rt.BaselineKindGreenfieldEmpty,
		SourceCommit: "",
		Evidence:     []EvidenceImport{},
		Nodes:        []NodeImport{},
		Edges:        []EdgeImport{},
		Observations: []ObservationImport{},
		PathIndex:    []PathIndexImport{},
		Rejections:   []RowDecision{},
		MergeRecords: []MergeRecord{},
	}
	importedGenerationID, err := s.ImportGeneration(ctx, input)
	if err != nil {
		return "", err
	}
	meta, readyGenerationID, err := s.PublishRuntimeMetadata(ctx, importedGenerationID, rt.BaselineKindGreenfieldEmpty)
	if err != nil {
		return "", err
	}
	if readyGenerationID != importedGenerationID {
		return "", fmt.Errorf("greenfield metadata active generation mismatch: got %s, want %s", readyGenerationID, importedGenerationID)
	}
	if meta["baseline_kind"] != rt.BaselineKindGreenfieldEmpty {
		return "", fmt.Errorf("greenfield metadata baseline_kind = %q, want %q", meta["baseline_kind"], rt.BaselineKindGreenfieldEmpty)
	}
	return importedGenerationID, nil
}

func activeGenerationIDTx(ctx context.Context, tx *sql.Tx) (string, error) {
	var id string
	err := tx.QueryRowContext(ctx, `SELECT id FROM generations WHERE state = 'active' ORDER BY sequence DESC, id DESC LIMIT 1`).Scan(&id)
	if errors.Is(err, sql.ErrNoRows) {
		return "", nil
	}
	if err != nil {
		return "", fmt.Errorf("read active generation: %w", err)
	}
	return id, nil
}

func (s *Store) MarkRuntimeMetadataBlocked(ctx context.Context, generationID string, afterCommit ...func() error) error {
	generationID = strings.TrimSpace(generationID)
	if generationID == "" {
		return fmt.Errorf("expected generation id is required")
	}
	now := time.Now().UTC().Format(time.RFC3339)
	tx, err := s.db.BeginTx(ctx, nil)
	if err != nil {
		return fmt.Errorf("begin blocked metadata transaction: %w", err)
	}
	defer tx.Rollback()

	activeGenerationID, err := activeGenerationIDTx(ctx, tx)
	if err != nil {
		return err
	}
	if activeGenerationID == "" {
		return fmt.Errorf("project-cognition.db has no active generation")
	}
	if activeGenerationID != generationID {
		return fmt.Errorf("active generation changed before blocked metadata publication: got %s, want %s", activeGenerationID, generationID)
	}
	baselineKind, err := activeGenerationKindTx(ctx, tx)
	if err != nil {
		return err
	}

	pairs := map[string]any{
		"runtime_format":       rt.RuntimeFormat,
		"runtime_schema":       rt.RuntimeSchema,
		"schema_version":       SchemaVersion,
		"active_generation_id": activeGenerationID,
		"graph_store_path":     ".specify/project-cognition/project-cognition.db",
		"graph_ready":          false,
		"baseline_state":       "blocked",
		"baseline_kind":        normalizeBaselineKind(baselineKind),
		"published_at":         now,
	}
	for key, value := range pairs {
		encoded, err := json.Marshal(value)
		if err != nil {
			return fmt.Errorf("encode metadata %s: %w", key, err)
		}
		if _, err := tx.ExecContext(ctx, `INSERT INTO metadata(key, value_json, updated_at) VALUES(?, ?, ?) ON CONFLICT(key) DO UPDATE SET value_json=excluded.value_json, updated_at=excluded.updated_at`, key, string(encoded), now); err != nil {
			return fmt.Errorf("write metadata %s: %w", key, err)
		}
	}
	if _, err := tx.ExecContext(ctx, `DELETE FROM metadata WHERE key IN (?, ?)`, "query_contract_version", "update_contract_version"); err != nil {
		return fmt.Errorf("clear ready contract metadata: %w", err)
	}
	if err := tx.Commit(); err != nil {
		return fmt.Errorf("commit blocked metadata transaction: %w", err)
	}
	activeGenerationID, err = s.ActiveGenerationID(ctx)
	if err != nil {
		return err
	}
	if activeGenerationID != generationID {
		return fmt.Errorf("active generation changed after blocked metadata publication: got %s, want %s", activeGenerationID, generationID)
	}
	for _, fn := range afterCommit {
		if fn == nil {
			continue
		}
		if err := fn(); err != nil {
			return err
		}
	}
	return nil
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

func (s *Store) ActiveGenerationKind(ctx context.Context) (string, error) {
	rows, err := s.db.QueryContext(ctx, `SELECT kind FROM generations WHERE state = 'active' ORDER BY sequence DESC, id DESC LIMIT 1`)
	if err != nil {
		return "", fmt.Errorf("read active generation kind: %w", err)
	}
	defer rows.Close()
	if !rows.Next() {
		return "", nil
	}
	var kind string
	if err := rows.Scan(&kind); err != nil {
		return "", fmt.Errorf("scan active generation kind: %w", err)
	}
	return kind, rows.Err()
}

func activeGenerationKindTx(ctx context.Context, tx *sql.Tx) (string, error) {
	var kind string
	err := tx.QueryRowContext(ctx, `SELECT kind FROM generations WHERE state = 'active' ORDER BY sequence DESC, id DESC LIMIT 1`).Scan(&kind)
	if errors.Is(err, sql.ErrNoRows) {
		return "", nil
	}
	if err != nil {
		return "", fmt.Errorf("read active generation kind: %w", err)
	}
	return kind, nil
}

func normalizeBaselineKind(kind string) string {
	switch strings.TrimSpace(kind) {
	case "", "full":
		return rt.BaselineKindBrownfieldFull
	default:
		return strings.TrimSpace(kind)
	}
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

func (s *Store) ActiveConceptCandidateRows(ctx context.Context, limit int) ([]ConceptCandidateRow, error) {
	return s.activeConceptCandidateRows(ctx, limit, true)
}

func (s *Store) AllActiveConceptCandidateRows(ctx context.Context) ([]ConceptCandidateRow, error) {
	return s.activeConceptCandidateRows(ctx, 0, false)
}

func (s *Store) activeConceptCandidateRows(ctx context.Context, limit int, limited bool) ([]ConceptCandidateRow, error) {
	generationID, err := s.ActiveGenerationID(ctx)
	if err != nil {
		return nil, err
	}
	if generationID == "" {
		return []ConceptCandidateRow{}, nil
	}

	query := `SELECT id, type, title, confidence, attrs_json FROM nodes WHERE generation_id = ? ORDER BY id`
	args := []any{generationID}
	if limited {
		if limit <= 0 {
			limit = 200
		}
		query += ` LIMIT ?`
		args = append(args, limit)
	}

	rows, err := s.db.QueryContext(ctx, query, args...)
	if err != nil {
		return nil, fmt.Errorf("query active concept candidate nodes: %w", err)
	}
	defer rows.Close()

	out := make([]ConceptCandidateRow, 0)
	for rows.Next() {
		row := ConceptCandidateRow{GenerationID: generationID}
		if err := rows.Scan(&row.NodeID, &row.NodeType, &row.Title, &row.Confidence, &row.AttrsJSON); err != nil {
			return nil, fmt.Errorf("scan active concept candidate node: %w", err)
		}
		row.Paths, err = s.nodeStringValues(ctx, `SELECT path FROM path_index WHERE generation_id = ? AND node_id = ? ORDER BY path`, generationID, row.NodeID)
		if err != nil {
			return nil, fmt.Errorf("query active concept candidate paths for %s: %w", row.NodeID, err)
		}
		row.EvidenceIDs, err = s.nodeStringValues(ctx, `
WITH candidate_evidence AS (
	SELECT ne.evidence_id
	FROM node_evidence ne
	JOIN nodes n ON n.id = ne.node_id AND n.generation_id = ?
	WHERE ne.node_id = ?
	UNION
	SELECT p.evidence_id
	FROM path_index p
	WHERE p.generation_id = ? AND p.node_id = ?
)
SELECT e.id
FROM candidate_evidence ce
JOIN evidence e ON e.id = ce.evidence_id AND e.generation_id = ?
ORDER BY e.id`, generationID, row.NodeID, generationID, row.NodeID, generationID)
		if err != nil {
			return nil, fmt.Errorf("query active concept candidate evidence for %s: %w", row.NodeID, err)
		}
		row.EvidencePaths, err = s.nodeStringValues(ctx, `
WITH candidate_evidence AS (
	SELECT ne.evidence_id
	FROM node_evidence ne
	JOIN nodes n ON n.id = ne.node_id AND n.generation_id = ?
	WHERE ne.node_id = ?
	UNION
	SELECT p.evidence_id
	FROM path_index p
	WHERE p.generation_id = ? AND p.node_id = ?
)
SELECT e.source_path
FROM candidate_evidence ce
JOIN evidence e ON e.id = ce.evidence_id AND e.generation_id = ?
ORDER BY e.source_path`, generationID, row.NodeID, generationID, row.NodeID, generationID)
		if err != nil {
			return nil, fmt.Errorf("query active concept candidate evidence paths for %s: %w", row.NodeID, err)
		}
		row.ObservationSummaries, err = s.nodeStringValues(ctx, `
WITH candidate_evidence AS (
	SELECT ne.evidence_id
	FROM node_evidence ne
	JOIN nodes n ON n.id = ne.node_id AND n.generation_id = ?
	WHERE ne.node_id = ?
	UNION
	SELECT p.evidence_id
	FROM path_index p
	WHERE p.generation_id = ? AND p.node_id = ?
)
SELECT o.summary
FROM candidate_evidence ce
JOIN observation_evidence oe ON oe.evidence_id = ce.evidence_id
JOIN observations o ON o.id = oe.observation_id AND o.generation_id = ?
ORDER BY o.summary`, generationID, row.NodeID, generationID, row.NodeID, generationID)
		if err != nil {
			return nil, fmt.Errorf("query active concept candidate observations for %s: %w", row.NodeID, err)
		}
		out = append(out, row)
	}
	if err := rows.Err(); err != nil {
		return nil, err
	}
	return out, nil
}

func (s *Store) NodesForIDs(ctx context.Context, nodeIDs []string) ([]map[string]any, error) {
	generationID, err := s.ActiveGenerationID(ctx)
	if err != nil {
		return nil, err
	}
	if generationID == "" {
		return []map[string]any{}, nil
	}
	nodeIDs = normalizeStoreStrings(nodeIDs)
	if len(nodeIDs) == 0 {
		return []map[string]any{}, nil
	}

	out := make([]map[string]any, 0, len(nodeIDs))
	for _, nodeID := range nodeIDs {
		rows, err := s.db.QueryContext(ctx, `
SELECT n.id, n.type, n.title, MIN(p.path)
FROM nodes n
LEFT JOIN path_index p ON p.generation_id = n.generation_id AND p.node_id = n.id
WHERE n.generation_id = ? AND n.id = ?
GROUP BY n.id, n.type, n.title
ORDER BY n.id`, generationID, nodeID)
		if err != nil {
			return nil, fmt.Errorf("query node for id %s: %w", nodeID, err)
		}
		nodes, err := scanNodeRows(rows)
		if err != nil {
			return nil, err
		}
		out = append(out, nodes...)
	}
	return out, nil
}

func (s *Store) nodeStringValues(ctx context.Context, query string, args ...any) ([]string, error) {
	rows, err := s.db.QueryContext(ctx, query, args...)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	values := []string{}
	for rows.Next() {
		var value string
		if err := rows.Scan(&value); err != nil {
			return nil, err
		}
		values = append(values, value)
	}
	if err := rows.Err(); err != nil {
		return nil, err
	}
	return normalizeStoreStrings(values), nil
}

func normalizeStoreStrings(values []string) []string {
	out := make([]string, 0, len(values))
	seen := map[string]bool{}
	for _, value := range values {
		value = strings.TrimSpace(value)
		if value == "" || seen[value] {
			continue
		}
		seen[value] = true
		out = append(out, value)
	}
	return out
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
