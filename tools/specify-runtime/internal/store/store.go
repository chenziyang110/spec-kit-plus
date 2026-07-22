package store

import (
	"context"
	"crypto/sha256"
	"database/sql"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"path"
	"path/filepath"
	"sort"
	"strconv"
	"strings"
	"time"
	"unicode"

	_ "modernc.org/sqlite"

	changemodel "github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/changes/model"
	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/claim"
	rt "github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/runtime"
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
	Aliases              []ConceptAliasRow
	EvidenceIDs          []string
	EvidencePaths        []string
	ObservationSummaries []string
}

type ConceptAliasRow struct {
	Alias           string
	NormalizedAlias string
	Source          string
	Confidence      string
	EvidenceID      string
}

// GraphClaimEvidence is the storage read model used by claim-aware navigation.
// RouteConfidence belongs to the owning graph node and must not be interpreted
// as confidence that the claim is current repository truth.
type GraphClaimEvidence struct {
	ID              string
	NodeID          string
	GraphClaimType  string
	Summary         string
	State           string
	Freshness       string
	StateReason     string
	RouteConfidence string
	Evidence        []GraphClaimEvidenceRef
}

type GraphClaimEvidenceRef struct {
	ID         string
	Role       string
	SourceKind string
	SourcePath string
	Span       string
	CommitSHA  string
}

// GraphClaimLifecycleSummary is a compact, evidence-free aggregate used for
// complete per-node ranking decisions without expanding claim detail payloads.
type GraphClaimLifecycleSummary struct {
	NodeID              string
	ClaimCount          int
	ContradictedCount   int
	StaleCount          int
	FreshVerifiedCount  int
	FreshSupportedCount int
}

type UpdateRecord struct {
	ID             string
	Trigger        string
	ChangedPaths   []string
	AffectedNodes  []string
	AffectedClaims []string
	AffectedSlices []string
	ResultState    string
	Attrs          map[string]any
}

type AffectedClosure struct {
	NodeIDs            []string
	ClaimIDs           []string
	SliceIDs           []string
	TraversedEdgeTypes []string
	Truncated          bool
	TruncationReason   string
}

type ClosureBudget struct {
	MaxNodes int
}

type TypedUpdate struct {
	Record           UpdateRecord
	PathChanges      []changemodel.PathChange
	Workflow         string
	BehaviorSurfaces []string
	Verification     []map[string]string
	Reason           string
}

type TypedUpdateResult struct {
	AdoptedPaths    []string
	RefreshedPaths  []string
	RenamedPaths    []string
	DeletedPaths    []string
	SkippedPaths    []string
	AffectedNodeIDs []string
	PathNodeIDs     map[string]string
}

type ClaimTransition struct {
	ClaimID   string
	FromState claim.State
	ToState   claim.State
	Reason    string
}

type PathCoverageRefresh struct {
	UpdateID   string
	Path       string
	NodeID     string
	Relation   string
	Confidence string
	Reason     string
}

type PathCoverageRefreshResult struct {
	EvidenceID  string
	PathIndexID string
}

type WorkflowPathAdoption struct {
	UpdateID         string
	Path             string
	Workflow         string
	BehaviorSurfaces []string
	Verification     []map[string]string
	Reason           string
}

func Open(paths rt.Paths) (*Store, error) {
	if err := os.MkdirAll(paths.RuntimeDir, 0o755); err != nil {
		return nil, fmt.Errorf("create runtime dir: %w", err)
	}
	if _, err := requireCurrentDatabase(paths); err != nil {
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

func ExistingDatabaseSchemaVersion(paths rt.Paths) (int, bool, error) {
	info, err := os.Stat(paths.DatabasePath)
	if errors.Is(err, os.ErrNotExist) {
		return 0, false, nil
	}
	if err != nil {
		return 0, false, fmt.Errorf("stat project-cognition.db: %w", err)
	}
	if info.Size() == 0 {
		return 0, false, nil
	}
	db, err := sql.Open("sqlite", paths.DatabasePath)
	if err != nil {
		return 0, true, fmt.Errorf("open sqlite for schema version check: %w", err)
	}
	defer db.Close()
	if err := db.PingContext(context.Background()); err != nil {
		return 0, true, fmt.Errorf("open sqlite for schema version check: %w", err)
	}
	version, err := databaseSchemaVersion(context.Background(), db)
	if err != nil {
		return 0, true, err
	}
	return version, true, nil
}

func requireCurrentDatabase(paths rt.Paths) (bool, error) {
	info, err := os.Stat(paths.DatabasePath)
	if errors.Is(err, os.ErrNotExist) {
		return false, nil
	}
	if err != nil {
		return false, fmt.Errorf("stat project-cognition.db: %w", err)
	}
	if info.Size() == 0 {
		return true, fmt.Errorf("project-cognition.db is empty; current runtime requires schema_version %d; remove the database and run sp-map-scan followed by sp-map-build", SchemaVersion)
	}
	version, _, err := ExistingDatabaseSchemaVersion(paths)
	if err != nil {
		return true, err
	}
	if version != SchemaVersion {
		return true, fmt.Errorf("project-cognition.db schema_version %d is unsupported; current runtime requires %d; remove the database and run sp-map-scan followed by sp-map-build", version, SchemaVersion)
	}
	db, err := sql.Open("sqlite", paths.DatabasePath)
	if err != nil {
		return true, fmt.Errorf("open sqlite for current schema check: %w", err)
	}
	defer db.Close()
	if err := db.PingContext(context.Background()); err != nil {
		return true, fmt.Errorf("open sqlite for current schema check: %w", err)
	}
	compatible, err := SchemaCompatible(context.Background(), db)
	if err != nil {
		return true, fmt.Errorf("check current sqlite schema: %w", err)
	}
	if !compatible {
		return true, fmt.Errorf("project-cognition.db schema_version %d is structurally incompatible; current runtime requires the complete schema; remove the database and run sp-map-scan followed by sp-map-build", SchemaVersion)
	}
	return true, nil
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
	exists, err := requireCurrentDatabase(paths)
	if err != nil {
		return nil, err
	}
	if !exists {
		return nil, fmt.Errorf("open sqlite: %w", os.ErrNotExist)
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
	if _, err := s.db.ExecContext(ctx, schemaV5ClaimSQL); err != nil {
		return fmt.Errorf("initialize claim schema: %w", err)
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
	}
	if err := rows.Err(); err != nil {
		return "", err
	}
	if hasValueJSON {
		return "value_json", nil
	}
	return "", fmt.Errorf("metadata table has no value_json column")
}

func databaseSchemaVersion(ctx context.Context, db *sql.DB) (int, error) {
	exists, err := tableExists(ctx, db, "metadata")
	if err != nil {
		return 0, err
	}
	if !exists {
		return 0, nil
	}
	valueColumn, err := metadataValueColumn(ctx, db)
	if err != nil {
		return 0, err
	}
	var value string
	err = db.QueryRowContext(ctx, `SELECT `+valueColumn+` FROM metadata WHERE key = 'schema_version'`).Scan(&value)
	if errors.Is(err, sql.ErrNoRows) {
		return 0, nil
	}
	if err != nil {
		return 0, fmt.Errorf("read metadata schema_version: %w", err)
	}
	var decoded int
	if err := json.Unmarshal([]byte(value), &decoded); err == nil {
		return decoded, nil
	}
	decoded, err = strconv.Atoi(strings.TrimSpace(value))
	if err != nil {
		return 0, nil
	}
	return decoded, nil
}

func decodeMetadataValue(value string) string {
	var decoded any
	if err := json.Unmarshal([]byte(value), &decoded); err != nil {
		return value
	}
	return fmt.Sprint(decoded)
}

func (s *Store) RecordUpdate(ctx context.Context, id, reason, changedPathsJSON string) error {
	var changed []string
	if strings.TrimSpace(changedPathsJSON) != "" {
		_ = json.Unmarshal([]byte(changedPathsJSON), &changed)
	}
	return s.RecordStructuredUpdate(ctx, UpdateRecord{
		ID:           id,
		Trigger:      reason,
		ChangedPaths: changed,
		ResultState:  "recorded",
		Attrs:        map[string]any{"legacy_record_update": true},
	})
}

func (s *Store) RecordStructuredUpdate(ctx context.Context, record UpdateRecord) error {
	_, err := s.ApplyTypedUpdate(ctx, TypedUpdate{Record: record})
	return err
}

func (s *Store) ApplyTypedUpdate(ctx context.Context, input TypedUpdate) (TypedUpdateResult, error) {
	result := TypedUpdateResult{
		AdoptedPaths:    []string{},
		RefreshedPaths:  []string{},
		RenamedPaths:    []string{},
		DeletedPaths:    []string{},
		SkippedPaths:    []string{},
		AffectedNodeIDs: []string{},
		PathNodeIDs:     map[string]string{},
	}
	pathChanges, err := normalizeTypedPathChanges(input.PathChanges)
	if err != nil {
		return result, err
	}
	if strings.TrimSpace(input.Record.ID) == "" {
		return result, fmt.Errorf("typed update record id is required")
	}
	tx, err := s.db.BeginTx(ctx, nil)
	if err != nil {
		return result, fmt.Errorf("begin typed update: %w", err)
	}
	committed := false
	defer func() {
		if !committed {
			_ = tx.Rollback()
		}
	}()
	generationID, err := activeGenerationIDTx(ctx, tx)
	if err != nil {
		return result, err
	}
	if generationID == "" {
		if len(pathChanges) > 0 {
			return result, fmt.Errorf("project-cognition.db has no active generation")
		}
		return result, nil
	}
	now := time.Now().UTC().Format(time.RFC3339)
	for _, change := range pathChanges {
		if !change.MutatesGraph() {
			result.SkippedPaths = append(result.SkippedPaths, change.Path)
			continue
		}
		switch change.Operation {
		case changemodel.OperationAdd:
			nodeIDs, err := applyAddPathTx(ctx, tx, generationID, input, change, now)
			if err != nil {
				return result, err
			}
			result.AdoptedPaths = append(result.AdoptedPaths, change.Path)
			result.AffectedNodeIDs = append(result.AffectedNodeIDs, nodeIDs...)
			if len(nodeIDs) > 0 {
				result.PathNodeIDs[change.Path] = nodeIDs[0]
			}
		case changemodel.OperationModify:
			nodeIDs, err := applyModifyPathTx(ctx, tx, generationID, input, change, now)
			if err != nil {
				return result, err
			}
			result.RefreshedPaths = append(result.RefreshedPaths, change.Path)
			result.AffectedNodeIDs = append(result.AffectedNodeIDs, nodeIDs...)
			if len(nodeIDs) > 0 {
				result.PathNodeIDs[change.Path] = nodeIDs[0]
			}
		case changemodel.OperationRename:
			nodeIDs, err := applyRenamePathTx(ctx, tx, generationID, input, change, now)
			if err != nil {
				return result, err
			}
			result.RenamedPaths = append(result.RenamedPaths, change.Path)
			result.AffectedNodeIDs = append(result.AffectedNodeIDs, nodeIDs...)
			if len(nodeIDs) > 0 {
				result.PathNodeIDs[change.Path] = nodeIDs[0]
			}
		case changemodel.OperationDelete:
			nodeIDs, err := applyDeletePathTx(ctx, tx, generationID, change)
			if err != nil {
				return result, err
			}
			result.DeletedPaths = append(result.DeletedPaths, change.Path)
			result.AffectedNodeIDs = append(result.AffectedNodeIDs, nodeIDs...)
		}
	}
	result.AdoptedPaths = uniqueSorted(result.AdoptedPaths)
	result.RefreshedPaths = uniqueSorted(result.RefreshedPaths)
	result.RenamedPaths = uniqueSorted(result.RenamedPaths)
	result.DeletedPaths = uniqueSorted(result.DeletedPaths)
	result.SkippedPaths = uniqueSorted(result.SkippedPaths)
	result.AffectedNodeIDs = uniqueSorted(result.AffectedNodeIDs)

	record := input.Record
	if strings.TrimSpace(record.ResultState) == "" {
		record.ResultState = "blocked"
	}
	if len(pathChanges) > 0 {
		// Typed dispositions are authoritative for graph-changing path scope.
		// Do not let a duplicated caller-authored ChangedPaths field smuggle an
		// ignored, review-only, or blocking path into the update record.
		record.ChangedPaths = []string{}
	}
	for _, change := range pathChanges {
		if change.MutatesGraph() {
			record.ChangedPaths = append(record.ChangedPaths, change.Path)
		}
	}
	record.ChangedPaths = uniqueSorted(record.ChangedPaths)
	record.AffectedNodes = uniqueSorted(append(record.AffectedNodes, result.AffectedNodeIDs...))
	automaticClaimIDs, err := claimIDsForNodeIDsTx(ctx, tx, generationID, result.AffectedNodeIDs)
	if err != nil {
		return result, err
	}
	record.AffectedClaims = uniqueSorted(append(record.AffectedClaims, automaticClaimIDs...))
	record.Attrs = cloneStringAnyMap(record.Attrs)
	record.Attrs["path_changes"] = pathChanges
	if workflow := strings.TrimSpace(input.Workflow); workflow != "" {
		record.Attrs["workflow"] = workflow
	}
	if len(input.BehaviorSurfaces) > 0 {
		record.Attrs["behavior_surfaces"] = uniqueSorted(input.BehaviorSurfaces)
	}
	if len(input.Verification) > 0 {
		record.Attrs["verification"] = input.Verification
	}
	if reason := strings.TrimSpace(input.Reason); reason != "" {
		record.Attrs["reason"] = reason
	}
	if _, err := markClaimsStaleTx(ctx, tx, generationID, record.AffectedClaims, changedPathReason(record.ChangedPaths), record.ID, now); err != nil {
		return result, err
	}
	if err := insertStructuredUpdateTx(ctx, tx, generationID, record, now); err != nil {
		return result, err
	}
	if err := tx.Commit(); err != nil {
		return result, fmt.Errorf("commit typed update: %w", err)
	}
	committed = true
	return result, nil
}

func (s *Store) AffectedClosureForPaths(ctx context.Context, paths []string) (AffectedClosure, error) {
	return s.AffectedClosureForPathsWithBudget(ctx, paths, ClosureBudget{})
}

func (s *Store) AffectedClosureForPathsWithBudget(ctx context.Context, paths []string, budget ClosureBudget) (AffectedClosure, error) {
	return s.AffectedClosureForPathsAndNodeIDsWithBudget(ctx, paths, nil, budget)
}

func (s *Store) AffectedClosureForPathsAndNodeIDsWithBudget(ctx context.Context, paths []string, startingNodeIDs []string, budget ClosureBudget) (AffectedClosure, error) {
	paths = uniqueSorted(paths)
	startingNodeIDs = uniqueSorted(startingNodeIDs)
	if len(paths) == 0 && len(startingNodeIDs) == 0 {
		return AffectedClosure{
			NodeIDs:            []string{},
			ClaimIDs:           []string{},
			SliceIDs:           []string{},
			TraversedEdgeTypes: []string{},
		}, nil
	}
	if len(paths) > 0 {
		nodes, err := s.NodesForPaths(ctx, paths)
		if err != nil {
			return AffectedClosure{}, err
		}
		startingNodeIDs = uniqueSorted(append(startingNodeIDs, nodeIDsFromMaps(nodes)...))
	}
	generationID, err := s.ActiveGenerationID(ctx)
	if err != nil {
		return AffectedClosure{}, err
	}
	nodeIDs, edgeTypes, truncated, err := s.expandTypedEdgeClosure(ctx, generationID, startingNodeIDs, budget)
	if err != nil {
		return AffectedClosure{}, err
	}
	claimIDs, err := s.claimIDsForNodesAndPaths(ctx, nodeIDs, paths)
	if err != nil {
		return AffectedClosure{}, err
	}
	return AffectedClosure{
		NodeIDs:            nodeIDs,
		ClaimIDs:           claimIDs,
		SliceIDs:           []string{},
		TraversedEdgeTypes: edgeTypes,
		Truncated:          truncated,
		TruncationReason: func() string {
			if truncated {
				return "node_budget_exhausted"
			}
			return ""
		}(),
	}, nil
}

func (s *Store) ClaimsForNodeIDs(ctx context.Context, nodeIDs []string) ([]map[string]any, error) {
	records, err := s.ClaimEvidenceForNodeIDs(ctx, nodeIDs)
	if err != nil {
		return nil, err
	}
	out := make([]map[string]any, 0, len(records))
	for _, record := range records {
		out = append(out, map[string]any{
			"id": record.ID, "node_id": record.NodeID, "graph_claim_type": record.GraphClaimType, "summary": record.Summary,
			"state": record.State, "freshness": record.Freshness, "state_reason": record.StateReason,
		})
	}
	return out, nil
}

func (s *Store) ClaimLifecycleSummariesForNodeIDs(ctx context.Context, nodeIDs []string) ([]GraphClaimLifecycleSummary, error) {
	generationID, err := s.ActiveGenerationID(ctx)
	if err != nil || generationID == "" || len(nodeIDs) == 0 {
		return []GraphClaimLifecycleSummary{}, err
	}
	nodeIDs = uniqueSorted(nodeIDs)
	placeholders := strings.TrimSuffix(strings.Repeat("?,", len(nodeIDs)), ",")
	args := make([]any, 0, len(nodeIDs)+1)
	args = append(args, generationID)
	for _, nodeID := range nodeIDs {
		args = append(args, nodeID)
	}
	rows, err := s.db.QueryContext(ctx, `SELECT node_id,
		COUNT(*),
		COALESCE(SUM(CASE WHEN LOWER(state) = 'contradicted' THEN 1 ELSE 0 END), 0),
		COALESCE(SUM(CASE WHEN LOWER(state) = 'stale' OR LOWER(freshness) = 'stale' THEN 1 ELSE 0 END), 0),
		COALESCE(SUM(CASE WHEN LOWER(state) = 'verified_in_graph_generation' AND LOWER(freshness) = 'fresh' THEN 1 ELSE 0 END), 0),
		COALESCE(SUM(CASE WHEN LOWER(state) = 'supported' AND LOWER(freshness) = 'fresh' THEN 1 ELSE 0 END), 0)
		FROM claims WHERE generation_id = ? AND node_id IN (`+placeholders+`)
		GROUP BY node_id ORDER BY node_id`, args...)
	if err != nil {
		return nil, fmt.Errorf("read graph claim lifecycle summaries: %w", err)
	}
	defer rows.Close()
	summaries := []GraphClaimLifecycleSummary{}
	for rows.Next() {
		var summary GraphClaimLifecycleSummary
		if err := rows.Scan(
			&summary.NodeID,
			&summary.ClaimCount,
			&summary.ContradictedCount,
			&summary.StaleCount,
			&summary.FreshVerifiedCount,
			&summary.FreshSupportedCount,
		); err != nil {
			return nil, fmt.Errorf("scan graph claim lifecycle summary: %w", err)
		}
		summaries = append(summaries, summary)
	}
	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("iterate graph claim lifecycle summaries: %w", err)
	}
	return summaries, nil
}

func (s *Store) ClaimEvidenceForNodeIDs(ctx context.Context, nodeIDs []string) ([]GraphClaimEvidence, error) {
	generationID, err := s.ActiveGenerationID(ctx)
	if err != nil || generationID == "" || len(nodeIDs) == 0 {
		return []GraphClaimEvidence{}, err
	}
	nodeIDs = uniqueSorted(nodeIDs)
	placeholders := strings.TrimSuffix(strings.Repeat("?,", len(nodeIDs)), ",")
	args := make([]any, 0, len(nodeIDs)+1)
	args = append(args, generationID)
	for _, nodeID := range nodeIDs {
		args = append(args, nodeID)
	}
	rows, err := s.db.QueryContext(ctx, `SELECT c.id, c.node_id, c.graph_claim_type, c.summary, c.state, c.freshness, c.state_reason, n.confidence FROM claims c JOIN nodes n ON n.id = c.node_id AND n.generation_id = c.generation_id WHERE c.generation_id = ? AND c.node_id IN (`+placeholders+`) ORDER BY c.id LIMIT 25`, args...)
	if err != nil {
		return nil, fmt.Errorf("read graph claim evidence heads: %w", err)
	}
	records := []GraphClaimEvidence{}
	for rows.Next() {
		var record GraphClaimEvidence
		if err := rows.Scan(&record.ID, &record.NodeID, &record.GraphClaimType, &record.Summary, &record.State, &record.Freshness, &record.StateReason, &record.RouteConfidence); err != nil {
			_ = rows.Close()
			return nil, fmt.Errorf("scan graph claim evidence head: %w", err)
		}
		record.Evidence = []GraphClaimEvidenceRef{}
		records = append(records, record)
	}
	if err := rows.Err(); err != nil {
		_ = rows.Close()
		return nil, fmt.Errorf("iterate graph claim evidence heads: %w", err)
	}
	if err := rows.Close(); err != nil {
		return nil, fmt.Errorf("close graph claim evidence heads: %w", err)
	}
	if len(records) == 0 {
		return records, nil
	}

	claimIDs := make([]string, 0, len(records))
	claimIndex := make(map[string]int, len(records))
	for index, record := range records {
		claimIDs = append(claimIDs, record.ID)
		claimIndex[record.ID] = index
	}
	claimPlaceholders := strings.TrimSuffix(strings.Repeat("?,", len(claimIDs)), ",")
	evidenceArgs := make([]any, 0, len(claimIDs)+1)
	evidenceArgs = append(evidenceArgs, generationID)
	for _, claimID := range claimIDs {
		evidenceArgs = append(evidenceArgs, claimID)
	}
	evidenceRows, err := s.db.QueryContext(ctx, `SELECT ce.claim_id, e.id, ce.role, e.source_kind, e.source_path, e.span, e.commit_sha FROM claim_evidence ce JOIN evidence e ON e.id = ce.evidence_id WHERE e.generation_id = ? AND ce.basis_state = 'current' AND ce.claim_id IN (`+claimPlaceholders+`) ORDER BY ce.claim_id, CASE ce.role WHEN 'contradicting' THEN 0 ELSE 1 END, e.id`, evidenceArgs...)
	if err != nil {
		return nil, fmt.Errorf("read graph claim evidence refs: %w", err)
	}
	defer evidenceRows.Close()
	for evidenceRows.Next() {
		var claimID string
		var ref GraphClaimEvidenceRef
		if err := evidenceRows.Scan(&claimID, &ref.ID, &ref.Role, &ref.SourceKind, &ref.SourcePath, &ref.Span, &ref.CommitSHA); err != nil {
			return nil, fmt.Errorf("scan graph claim evidence ref: %w", err)
		}
		if index, ok := claimIndex[claimID]; ok {
			records[index].Evidence = append(records[index].Evidence, ref)
		}
	}
	if err := evidenceRows.Err(); err != nil {
		return nil, fmt.Errorf("iterate graph claim evidence refs: %w", err)
	}
	return records, nil
}

func (s *Store) MarkClaimsStale(ctx context.Context, claimIDs []string, reason, transitionIDPrefix string) ([]ClaimTransition, error) {
	generationID, err := s.ActiveGenerationID(ctx)
	if err != nil || generationID == "" || len(claimIDs) == 0 {
		return []ClaimTransition{}, err
	}
	tx, err := s.db.BeginTx(ctx, nil)
	if err != nil {
		return nil, fmt.Errorf("begin claim invalidation: %w", err)
	}
	committed := false
	defer func() {
		if !committed {
			_ = tx.Rollback()
		}
	}()
	transitions, err := markClaimsStaleTx(ctx, tx, generationID, claimIDs, reason, transitionIDPrefix, time.Now().UTC().Format(time.RFC3339))
	if err != nil {
		return nil, err
	}
	if err := tx.Commit(); err != nil {
		return nil, fmt.Errorf("commit claim invalidation: %w", err)
	}
	committed = true
	return transitions, nil
}

func (s *Store) claimIDsForNodesAndPaths(ctx context.Context, nodeIDs, paths []string) ([]string, error) {
	generationID, err := s.ActiveGenerationID(ctx)
	if err != nil || generationID == "" {
		return []string{}, err
	}
	ids := map[string]bool{}
	if len(nodeIDs) > 0 {
		placeholders := strings.TrimSuffix(strings.Repeat("?,", len(nodeIDs)), ",")
		args := make([]any, 0, len(nodeIDs)+1)
		args = append(args, generationID)
		for _, nodeID := range nodeIDs {
			args = append(args, nodeID)
		}
		rows, err := s.db.QueryContext(ctx, `SELECT id FROM claims WHERE generation_id = ? AND node_id IN (`+placeholders+`)`, args...)
		if err != nil {
			return nil, fmt.Errorf("read claims for affected nodes: %w", err)
		}
		for rows.Next() {
			var id string
			if err := rows.Scan(&id); err != nil {
				_ = rows.Close()
				return nil, err
			}
			ids[id] = true
		}
		if err := rows.Close(); err != nil {
			return nil, err
		}
	}
	for _, candidate := range uniqueSorted(paths) {
		candidate = strings.Trim(strings.TrimSpace(candidate), "/")
		if candidate == "" {
			continue
		}
		rows, err := s.db.QueryContext(ctx, `SELECT DISTINCT c.id FROM claims c JOIN claim_evidence ce ON ce.claim_id = c.id AND ce.basis_state = 'current' JOIN evidence e ON e.id = ce.evidence_id AND e.generation_id = c.generation_id WHERE c.generation_id = ? AND (e.source_path = ? OR e.source_path LIKE ? OR ? LIKE e.source_path || '/%')`, generationID, candidate, candidate+"/%", candidate)
		if err != nil {
			return nil, fmt.Errorf("read claims for affected evidence paths: %w", err)
		}
		for rows.Next() {
			var id string
			if err := rows.Scan(&id); err != nil {
				_ = rows.Close()
				return nil, err
			}
			ids[id] = true
		}
		if err := rows.Close(); err != nil {
			return nil, err
		}
	}
	out := make([]string, 0, len(ids))
	for id := range ids {
		out = append(out, id)
	}
	sort.Strings(out)
	return out, nil
}

func markClaimsStaleTx(ctx context.Context, tx *sql.Tx, generationID string, claimIDs []string, reason, transitionIDPrefix, now string) ([]ClaimTransition, error) {
	reason = defaultString(reason, "affected_dependency_changed")
	transitionIDPrefix = defaultString(transitionIDPrefix, "manual")
	transitions := []ClaimTransition{}
	for _, claimID := range uniqueSorted(claimIDs) {
		var stateValue string
		err := tx.QueryRowContext(ctx, `SELECT state FROM claims WHERE generation_id = ? AND id = ?`, generationID, claimID).Scan(&stateValue)
		if errors.Is(err, sql.ErrNoRows) {
			continue
		}
		if err != nil {
			return nil, fmt.Errorf("read claim %s before invalidation: %w", claimID, err)
		}
		from := claim.State(stateValue)
		if from == claim.StateStale {
			continue
		}
		if !claim.CanTransition(from, claim.StateStale) {
			return nil, fmt.Errorf("claim %s cannot transition from %s to stale", claimID, from)
		}
		if _, err := tx.ExecContext(ctx, `UPDATE claims SET prior_state = state, state = ?, freshness = ?, state_reason = ?, revision = revision + 1, updated_at = ? WHERE generation_id = ? AND id = ?`, claim.StateStale, claim.FreshnessStale, reason, now, generationID, claimID); err != nil {
			return nil, fmt.Errorf("mark claim %s stale: %w", claimID, err)
		}
		transitionID := "claim-transition:" + stableIDPart(transitionIDPrefix) + ":" + stableIDPart(claimID)
		if _, err := tx.ExecContext(ctx, `INSERT INTO claim_transitions(id, claim_id, generation_id, from_state, to_state, reason, evidence_id, occurred_at, attrs_json) VALUES(?, ?, ?, ?, ?, ?, '', ?, '{}')`, transitionID, claimID, generationID, from, claim.StateStale, reason, now); err != nil {
			return nil, fmt.Errorf("record claim %s stale transition: %w", claimID, err)
		}
		transitions = append(transitions, ClaimTransition{ClaimID: claimID, FromState: from, ToState: claim.StateStale, Reason: reason})
	}
	return transitions, nil
}

func changedPathReason(paths []string) string {
	paths = uniqueSorted(paths)
	if len(paths) == 1 {
		return "changed_path:" + paths[0]
	}
	if len(paths) > 1 {
		return "changed_paths:" + strings.Join(paths, ",")
	}
	return "affected_dependency_changed"
}

func (s *Store) RefreshPathCoverage(ctx context.Context, refresh PathCoverageRefresh) (PathCoverageRefreshResult, error) {
	generationID, err := s.ActiveGenerationID(ctx)
	if err != nil {
		return PathCoverageRefreshResult{}, err
	}
	if generationID == "" {
		return PathCoverageRefreshResult{}, fmt.Errorf("project-cognition.db has no active generation")
	}
	path := strings.TrimSpace(refresh.Path)
	nodeID := strings.TrimSpace(refresh.NodeID)
	if path == "" {
		return PathCoverageRefreshResult{}, fmt.Errorf("path coverage refresh path is required")
	}
	if nodeID == "" {
		return PathCoverageRefreshResult{}, fmt.Errorf("path coverage refresh node id is required")
	}
	relation := defaultString(refresh.Relation, "owns")
	confidence := defaultString(refresh.Confidence, "partial")
	updateID := defaultString(refresh.UpdateID, "manual")
	now := time.Now().UTC().Format(time.RFC3339)
	evidenceID := "E-update-" + stableIDPart(updateID) + "-" + stableIDPart(path)
	pathIndexID, err := s.pathIndexIDForPath(ctx, generationID, path)
	if err != nil {
		return PathCoverageRefreshResult{}, err
	}
	if pathIndexID == "" {
		pathIndexID = "P-update-" + stableIDPart(path)
	}
	attrs, err := attrsJSONOrEmpty(map[string]any{"update_id": updateID, "reason": refresh.Reason})
	if err != nil {
		return PathCoverageRefreshResult{}, err
	}
	_, err = s.db.ExecContext(ctx, `INSERT INTO evidence(id, generation_id, source_kind, source_path, commit_sha, span, extractor, content_hash, captured_at, attrs_json) VALUES(?, ?, 'workflow_update', ?, '', '', 'specify-runtime cognition update', '', ?, ?) ON CONFLICT(id) DO UPDATE SET captured_at=excluded.captured_at, attrs_json=excluded.attrs_json`, evidenceID, generationID, path, now, attrs)
	if err != nil {
		return PathCoverageRefreshResult{}, fmt.Errorf("upsert update evidence: %w", err)
	}
	_, err = s.db.ExecContext(ctx, `INSERT INTO path_index(id, generation_id, path, node_id, relation, confidence, evidence_id, updated_at) VALUES(?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT(id) DO UPDATE SET path=excluded.path, node_id=excluded.node_id, relation=excluded.relation, confidence=excluded.confidence, evidence_id=excluded.evidence_id, updated_at=excluded.updated_at`, pathIndexID, generationID, path, nodeID, relation, confidence, evidenceID, now)
	if err != nil {
		return PathCoverageRefreshResult{}, fmt.Errorf("upsert path coverage: %w", err)
	}
	if err := s.upsertWorkflowPathAliases(ctx, generationID, nodeID, path, "", "", nil, evidenceID, confidence); err != nil {
		return PathCoverageRefreshResult{}, err
	}
	return PathCoverageRefreshResult{EvidenceID: evidenceID, PathIndexID: pathIndexID}, nil
}

func (s *Store) AdoptWorkflowPath(ctx context.Context, adoption WorkflowPathAdoption) (string, error) {
	generationID, err := s.ActiveGenerationID(ctx)
	if err != nil {
		return "", err
	}
	if generationID == "" {
		return "", fmt.Errorf("project-cognition.db has no active generation")
	}
	path := strings.TrimSpace(adoption.Path)
	if path == "" {
		return "", fmt.Errorf("workflow path adoption path is required")
	}
	updateID := defaultString(adoption.UpdateID, "manual")
	nodeID := "N-update-" + stableIDPart(path)
	title := workflowPathTitle(path)
	now := time.Now().UTC().Format(time.RFC3339)
	attrs, err := attrsJSONOrEmpty(map[string]any{
		"source":            "specify-runtime cognition update",
		"update_id":         updateID,
		"workflow":          adoption.Workflow,
		"behavior_surfaces": adoption.BehaviorSurfaces,
		"verification":      adoption.Verification,
		"reason":            adoption.Reason,
	})
	if err != nil {
		return "", fmt.Errorf("encode adopted workflow node attrs: %w", err)
	}
	_, err = s.db.ExecContext(ctx, `INSERT INTO nodes(id, generation_id, type, title, confidence, attrs_json, created_at, updated_at) VALUES(?, ?, 'workflow_update', ?, 'partial', ?, ?, ?) ON CONFLICT(id) DO UPDATE SET title=excluded.title, confidence=excluded.confidence, attrs_json=excluded.attrs_json, updated_at=excluded.updated_at`, nodeID, generationID, title, attrs, now, now)
	if err != nil {
		return "", fmt.Errorf("upsert adopted workflow node: %w", err)
	}
	coverage, err := s.RefreshPathCoverage(ctx, PathCoverageRefresh{
		UpdateID:   updateID,
		Path:       path,
		NodeID:     nodeID,
		Relation:   "provisional_path",
		Confidence: "partial",
		Reason:     adoption.Reason,
	})
	if err != nil {
		return "", err
	}
	if err := s.upsertWorkflowPathAliases(ctx, generationID, nodeID, path, title, adoption.Workflow, adoption.BehaviorSurfaces, coverage.EvidenceID, "partial"); err != nil {
		return "", err
	}
	return nodeID, nil
}

func workflowPathTitle(path string) string {
	trimmed := strings.TrimSpace(path)
	if trimmed == "" {
		return "Workflow-updated path"
	}
	base := filepath.Base(trimmed)
	if base == "." || base == string(filepath.Separator) || base == "" {
		return trimmed
	}
	return base
}

func (s *Store) upsertWorkflowPathAliases(ctx context.Context, generationID, nodeID, rawPath, title, workflow string, behaviorSurfaces []string, evidenceID, confidence string) error {
	seeds := []workflowAliasSeed{}
	if title = strings.TrimSpace(title); title != "" {
		seeds = append(seeds, workflowAliasSeed{alias: title, source: "workflow_update_title", confidence: confidence, evidenceID: evidenceID})
	}
	if workflow = strings.TrimSpace(workflow); workflow != "" {
		seeds = append(seeds, workflowAliasSeed{alias: workflow, source: "workflow_update_workflow", confidence: "medium", evidenceID: evidenceID})
	}
	if nodeID = strings.TrimSpace(nodeID); nodeID != "" {
		seeds = append(seeds, workflowAliasSeed{alias: nodeID, source: "workflow_update_node_id", confidence: "high"})
	}
	for _, alias := range workflowPathAliasValues(rawPath) {
		seeds = append(seeds, workflowAliasSeed{alias: alias, source: "workflow_update_path", confidence: confidence, evidenceID: evidenceID, language: "code"})
	}
	for _, surface := range behaviorSurfaces {
		seeds = append(seeds, workflowAliasSeed{alias: surface, source: "workflow_update_surface", confidence: "medium", evidenceID: evidenceID})
	}
	for _, seed := range compactWorkflowAliasSeeds(seeds) {
		if err := s.upsertWorkflowAliasSeed(ctx, generationID, nodeID, seed); err != nil {
			return err
		}
	}
	return nil
}

type workflowAliasSeed struct {
	alias      string
	source     string
	confidence string
	evidenceID string
	language   string
}

func (s *Store) upsertWorkflowAliasSeed(ctx context.Context, generationID, nodeID string, seed workflowAliasSeed) error {
	alias := strings.TrimSpace(seed.alias)
	normalized := normalizeWorkflowAlias(alias)
	if alias == "" || normalized == "" || workflowAliasPathExcluded(alias) {
		return nil
	}
	source := defaultString(seed.source, "workflow_update")
	confidence := defaultString(seed.confidence, "partial")
	language := defaultString(seed.language, "unknown")
	id := workflowAliasID(generationID, nodeID, normalized, source)
	_, err := s.db.ExecContext(ctx, `INSERT INTO alias_index(id, generation_id, alias, normalized_alias, target_type, target_id, language, source, confidence, evidence_id) VALUES(?, ?, ?, ?, 'node', ?, ?, ?, ?, ?) ON CONFLICT(id) DO UPDATE SET alias=excluded.alias, normalized_alias=excluded.normalized_alias, language=excluded.language, confidence=excluded.confidence, evidence_id=excluded.evidence_id`, id, generationID, alias, normalized, nodeID, language, source, confidence, seed.evidenceID)
	if err != nil {
		return fmt.Errorf("upsert workflow alias %s for %s: %w", alias, nodeID, err)
	}
	return nil
}

func workflowAliasID(generationID, nodeID, normalizedAlias, source string) string {
	sum := sha256.Sum256([]byte(strings.Join([]string{generationID, "node", nodeID, normalizedAlias, source}, "\x00")))
	return "ALIAS-update-" + stableIDPart(nodeID) + "-" + hex.EncodeToString(sum[:])[:16]
}

func workflowPathAliasValues(rawPath string) []string {
	normalizedPath := filepath.ToSlash(strings.TrimSpace(rawPath))
	normalizedPath = strings.TrimPrefix(normalizedPath, "./")
	if normalizedPath == "" || workflowAliasPathExcluded(normalizedPath) {
		return []string{}
	}
	values := []string{normalizedPath}
	withoutExt := strings.TrimSuffix(normalizedPath, path.Ext(normalizedPath))
	for _, part := range strings.FieldsFunc(withoutExt, func(r rune) bool {
		return r == '/' || r == '\\' || r == '-' || r == '_' || r == '.'
	}) {
		part = strings.TrimSpace(part)
		if len(part) >= 3 {
			values = append(values, part)
		}
	}
	if base := strings.TrimSuffix(path.Base(normalizedPath), path.Ext(normalizedPath)); len(base) >= 3 {
		values = append(values, base)
	}
	return uniqueWorkflowAliases(values)
}

func compactWorkflowAliasSeeds(seeds []workflowAliasSeed) []workflowAliasSeed {
	out := []workflowAliasSeed{}
	seen := map[string]bool{}
	for _, seed := range seeds {
		normalized := normalizeWorkflowAlias(seed.alias)
		if normalized == "" || workflowAliasPathExcluded(seed.alias) {
			continue
		}
		key := seed.source + "\x00" + normalized
		if seen[key] {
			continue
		}
		seen[key] = true
		out = append(out, seed)
	}
	return out
}

func uniqueWorkflowAliases(values []string) []string {
	out := []string{}
	seen := map[string]bool{}
	for _, value := range values {
		normalized := normalizeWorkflowAlias(value)
		if normalized == "" || seen[normalized] {
			continue
		}
		seen[normalized] = true
		out = append(out, strings.TrimSpace(value))
	}
	return out
}

func normalizeWorkflowAlias(value string) string {
	value = strings.ToLower(strings.TrimSpace(value))
	var b strings.Builder
	previousSplit := true
	for _, r := range value {
		if unicode.IsLetter(r) || unicode.IsDigit(r) || r == '_' || r == '-' || r == '/' || r == '.' {
			b.WriteRune(r)
			previousSplit = false
			continue
		}
		if !previousSplit {
			b.WriteByte(' ')
			previousSplit = true
		}
	}
	return strings.TrimSpace(b.String())
}

func workflowAliasPathExcluded(value string) bool {
	normalizedPath := filepath.ToSlash(strings.TrimSpace(value))
	normalizedPath = strings.TrimPrefix(normalizedPath, "./")
	return normalizedPath == ".specify" || strings.HasPrefix(normalizedPath, ".specify/")
}

func (s *Store) pathIndexIDForPath(ctx context.Context, generationID string, path string) (string, error) {
	var id string
	err := s.db.QueryRowContext(ctx, `SELECT id FROM path_index WHERE generation_id = ? AND path = ? ORDER BY id LIMIT 1`, generationID, path).Scan(&id)
	if errors.Is(err, sql.ErrNoRows) {
		return "", nil
	}
	if err != nil {
		return "", fmt.Errorf("query path index for %s: %w", path, err)
	}
	return id, nil
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
		rows, err := s.db.QueryContext(ctx, `SELECT n.id, n.type, n.title, COALESCE(p.path, '') FROM nodes n LEFT JOIN path_index p ON p.generation_id = n.generation_id AND p.node_id = n.id WHERE n.generation_id = ? ORDER BY n.id`, generationID)
		if err != nil {
			return nil, fmt.Errorf("query nodes: %w", err)
		}
		return scanNodeRows(rows)
	}
	out := make([]map[string]any, 0)
	for _, path := range paths {
		descendantPattern := strings.TrimRight(path, "/") + "/%"
		rows, err := s.db.QueryContext(ctx, `SELECT DISTINCT n.id, n.type, n.title, p.path FROM path_index p JOIN nodes n ON n.generation_id = p.generation_id AND n.id = p.node_id WHERE p.generation_id = ? AND (p.path = ? OR p.path LIKE ?) ORDER BY n.id`, generationID, path, descendantPattern)
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

func (s *Store) NodeIDsForExactPaths(ctx context.Context, paths []string) (map[string]string, error) {
	generationID, err := s.ActiveGenerationID(ctx)
	if err != nil {
		return nil, err
	}
	out := map[string]string{}
	if generationID == "" {
		return out, nil
	}
	for _, path := range paths {
		path = strings.TrimSpace(path)
		if path == "" {
			continue
		}
		var nodeID string
		err := s.db.QueryRowContext(ctx, `SELECT node_id FROM path_index WHERE generation_id = ? AND path = ? ORDER BY updated_at DESC, id DESC LIMIT 1`, generationID, path).Scan(&nodeID)
		if errors.Is(err, sql.ErrNoRows) {
			continue
		}
		if err != nil {
			return nil, fmt.Errorf("query node for path %s: %w", path, err)
		}
		if nodeID != "" {
			out[path] = nodeID
		}
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
		row.Aliases, err = s.nodeAliasRows(ctx, generationID, row.NodeID)
		if err != nil {
			return nil, fmt.Errorf("query active concept candidate aliases for %s: %w", row.NodeID, err)
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

func (s *Store) nodeAliasRows(ctx context.Context, generationID string, nodeID string) ([]ConceptAliasRow, error) {
	rows, err := s.db.QueryContext(ctx, `SELECT alias, normalized_alias, source, confidence, evidence_id FROM alias_index WHERE generation_id = ? AND target_type = 'node' AND target_id = ? ORDER BY source, normalized_alias, id`, generationID, nodeID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	out := []ConceptAliasRow{}
	seen := map[string]bool{}
	for rows.Next() {
		var row ConceptAliasRow
		if err := rows.Scan(&row.Alias, &row.NormalizedAlias, &row.Source, &row.Confidence, &row.EvidenceID); err != nil {
			return nil, err
		}
		key := row.Source + "\x00" + row.NormalizedAlias
		if strings.TrimSpace(row.Alias) == "" || seen[key] {
			continue
		}
		seen[key] = true
		out = append(out, row)
	}
	return out, rows.Err()
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

func nodeIDsFromMaps(rows []map[string]any) []string {
	ids := make([]string, 0, len(rows))
	for _, row := range rows {
		id, ok := row["id"].(string)
		if ok {
			ids = append(ids, id)
		}
	}
	return uniqueSorted(ids)
}

func uniqueSorted(values []string) []string {
	out := normalizeStoreStrings(values)
	sort.Strings(out)
	return out
}

func stableIDPart(value string) string {
	replacer := strings.NewReplacer("/", "-", "\\", "-", " ", "-", ".", "-", ":", "-")
	part := strings.Trim(replacer.Replace(strings.TrimSpace(value)), "-")
	if part == "" {
		return "unknown"
	}
	return part
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
