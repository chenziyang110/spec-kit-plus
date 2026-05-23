package store

import (
	"context"
	"database/sql"
	"encoding/json"
	"fmt"
	"strings"
	"time"

	rt "github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/runtime"
)

type ImportInput struct {
	GenerationID string
	Kind         string
	SourceCommit string
	Evidence     []EvidenceImport
	Nodes        []NodeImport
	Edges        []EdgeImport
	Observations []ObservationImport
	PathIndex    []PathIndexImport
	Rejections   []RowDecision
	MergeRecords []MergeRecord
}

type EvidenceImport struct {
	ID          string
	SourceKind  string
	SourcePath  string
	CommitSHA   string
	Span        string
	Extractor   string
	ContentHash string
	Attrs       map[string]any
}

type NodeImport struct {
	ID          string
	Type        string
	Title       string
	Confidence  string
	EvidenceIDs []string
	Attrs       map[string]any
}

type EdgeImport struct {
	ID          string
	Type        string
	SourceID    string
	TargetID    string
	Confidence  string
	EvidenceIDs []string
	Attrs       map[string]any
}

type ObservationImport struct {
	ID              string
	ObservationType string
	Summary         string
	EvidenceIDs     []string
	Attrs           map[string]any
}

type PathIndexImport struct {
	ID         string
	Path       string
	NodeID     string
	Relation   string
	Confidence string
	EvidenceID string
}

type RowDecision struct {
	Category string `json:"category"`
	Identity string `json:"identity"`
	Reason   string `json:"reason"`
}

type MergeRecord struct {
	Category       string `json:"category"`
	SourceIdentity string `json:"source_identity"`
	TargetIdentity string `json:"target_identity"`
	Reason         string `json:"reason"`
}

type IdentitySnapshot struct {
	Evidence      map[string]bool `json:"evidence"`
	Nodes         map[string]bool `json:"nodes"`
	Edges         map[string]bool `json:"edges"`
	Observations  map[string]bool `json:"observations"`
	CoveragePaths map[string]bool `json:"coverage_paths"`
	Rejections    []RowDecision   `json:"rejections"`
	MergeRecords  []MergeRecord   `json:"merge_records"`
}

func (s *Store) ImportGeneration(ctx context.Context, input ImportInput) (string, error) {
	input.GenerationID = strings.TrimSpace(input.GenerationID)
	if input.GenerationID == "" {
		return "", fmt.Errorf("generation id is required")
	}
	if input.Kind == "" {
		input.Kind = "full"
	}
	now := time.Now().UTC().Format(time.RFC3339)

	tx, err := s.db.BeginTx(ctx, nil)
	if err != nil {
		return "", fmt.Errorf("begin import transaction: %w", err)
	}
	committed := false
	defer func() {
		if !committed {
			_ = tx.Rollback()
		}
	}()

	sequence, err := nextGenerationSequence(ctx, tx)
	if err != nil {
		return "", err
	}
	attrsJSON, err := generationAttrsJSON(input.Rejections, input.MergeRecords)
	if err != nil {
		return "", err
	}
	if _, err := tx.ExecContext(ctx, `INSERT INTO generations(id, sequence, kind, state, source_commit, started_at, published_at, superseded_at, attrs_json) VALUES(?, ?, ?, 'building', ?, ?, '', '', ?)`, input.GenerationID, sequence, input.Kind, input.SourceCommit, now, attrsJSON); err != nil {
		return "", fmt.Errorf("insert generation %s: %w", input.GenerationID, err)
	}

	for _, evidence := range input.Evidence {
		attrs, err := attrsJSONOrEmpty(evidence.Attrs)
		if err != nil {
			return "", fmt.Errorf("encode evidence %s attrs: %w", evidence.ID, err)
		}
		if _, err := tx.ExecContext(ctx, `INSERT INTO evidence(id, generation_id, source_kind, source_path, commit_sha, span, extractor, content_hash, captured_at, attrs_json) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`, evidence.ID, input.GenerationID, evidence.SourceKind, evidence.SourcePath, evidence.CommitSHA, evidence.Span, evidence.Extractor, evidence.ContentHash, now, attrs); err != nil {
			return "", fmt.Errorf("insert evidence %s: %w", evidence.ID, err)
		}
	}

	for _, node := range input.Nodes {
		attrs, err := attrsJSONOrEmpty(node.Attrs)
		if err != nil {
			return "", fmt.Errorf("encode node %s attrs: %w", node.ID, err)
		}
		if _, err := tx.ExecContext(ctx, `INSERT INTO nodes(id, generation_id, type, title, confidence, attrs_json, created_at, updated_at) VALUES(?, ?, ?, ?, ?, ?, ?, ?)`, node.ID, input.GenerationID, node.Type, node.Title, node.Confidence, attrs, now, now); err != nil {
			return "", fmt.Errorf("insert node %s: %w", node.ID, err)
		}
		for _, evidenceID := range node.EvidenceIDs {
			if _, err := tx.ExecContext(ctx, `INSERT INTO node_evidence(node_id, evidence_id) VALUES(?, ?)`, node.ID, evidenceID); err != nil {
				return "", fmt.Errorf("insert node evidence %s/%s: %w", node.ID, evidenceID, err)
			}
		}
	}

	for _, edge := range input.Edges {
		if err := validateEdgeNodes(ctx, tx, input.GenerationID, edge); err != nil {
			return "", err
		}
		attrs, err := attrsJSONOrEmpty(edge.Attrs)
		if err != nil {
			return "", fmt.Errorf("encode edge %s attrs: %w", edge.ID, err)
		}
		if _, err := tx.ExecContext(ctx, `INSERT INTO edges(id, generation_id, type, source_id, target_id, confidence, attrs_json, created_at, updated_at) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)`, edge.ID, input.GenerationID, edge.Type, edge.SourceID, edge.TargetID, edge.Confidence, attrs, now, now); err != nil {
			return "", fmt.Errorf("insert edge %s: %w", edge.ID, err)
		}
		for _, evidenceID := range edge.EvidenceIDs {
			if _, err := tx.ExecContext(ctx, `INSERT INTO edge_evidence(edge_id, evidence_id) VALUES(?, ?)`, edge.ID, evidenceID); err != nil {
				return "", fmt.Errorf("insert edge evidence %s/%s: %w", edge.ID, evidenceID, err)
			}
		}
	}

	for _, observation := range input.Observations {
		attrs, err := attrsJSONOrEmpty(observation.Attrs)
		if err != nil {
			return "", fmt.Errorf("encode observation %s attrs: %w", observation.ID, err)
		}
		if _, err := tx.ExecContext(ctx, `INSERT INTO observations(id, generation_id, observation_type, summary, attrs_json, created_at, updated_at) VALUES(?, ?, ?, ?, ?, ?, ?)`, observation.ID, input.GenerationID, observation.ObservationType, observation.Summary, attrs, now, now); err != nil {
			return "", fmt.Errorf("insert observation %s: %w", observation.ID, err)
		}
		for _, evidenceID := range observation.EvidenceIDs {
			if _, err := tx.ExecContext(ctx, `INSERT INTO observation_evidence(observation_id, evidence_id) VALUES(?, ?)`, observation.ID, evidenceID); err != nil {
				return "", fmt.Errorf("insert observation evidence %s/%s: %w", observation.ID, evidenceID, err)
			}
		}
	}

	for _, pathIndex := range input.PathIndex {
		if _, err := tx.ExecContext(ctx, `INSERT INTO path_index(id, generation_id, path, node_id, relation, confidence, evidence_id, updated_at) VALUES(?, ?, ?, ?, ?, ?, ?, ?)`, pathIndex.ID, input.GenerationID, pathIndex.Path, pathIndex.NodeID, pathIndex.Relation, pathIndex.Confidence, pathIndex.EvidenceID, now); err != nil {
			return "", fmt.Errorf("insert path index %s: %w", pathIndex.ID, err)
		}
	}

	if _, err := tx.ExecContext(ctx, `UPDATE generations SET state = 'superseded', superseded_at = ? WHERE state = 'active' AND id <> ?`, now, input.GenerationID); err != nil {
		return "", fmt.Errorf("supersede active generations: %w", err)
	}
	if _, err := tx.ExecContext(ctx, `UPDATE generations SET state = 'active', published_at = ? WHERE id = ?`, now, input.GenerationID); err != nil {
		return "", fmt.Errorf("publish generation %s: %w", input.GenerationID, err)
	}
	if err := writeImportMetadata(ctx, tx, input.GenerationID, now); err != nil {
		return "", err
	}
	if err := tx.Commit(); err != nil {
		return "", fmt.Errorf("commit import generation %s: %w", input.GenerationID, err)
	}
	committed = true
	return input.GenerationID, nil
}

func (s *Store) ActiveIdentitySnapshot(ctx context.Context) (IdentitySnapshot, error) {
	snapshot := IdentitySnapshot{
		Evidence:      map[string]bool{},
		Nodes:         map[string]bool{},
		Edges:         map[string]bool{},
		Observations:  map[string]bool{},
		CoveragePaths: map[string]bool{},
		Rejections:    []RowDecision{},
		MergeRecords:  []MergeRecord{},
	}
	generationID, err := s.ActiveGenerationID(ctx)
	if err != nil {
		return snapshot, err
	}
	if generationID == "" {
		return snapshot, nil
	}
	if err := scanSnapshotRows(ctx, s.db, `SELECT id, source_path, content_hash FROM evidence WHERE generation_id = ?`, generationID, func(values []string) {
		snapshot.Evidence[values[0]+"|"+values[1]+"|"+values[2]] = true
	}); err != nil {
		return snapshot, fmt.Errorf("read evidence identities: %w", err)
	}
	if err := scanSnapshotRows(ctx, s.db, `SELECT id FROM nodes WHERE generation_id = ?`, generationID, func(values []string) {
		snapshot.Nodes[values[0]] = true
	}); err != nil {
		return snapshot, fmt.Errorf("read node identities: %w", err)
	}
	if err := scanSnapshotRows(ctx, s.db, `SELECT id, source_id, target_id, type FROM edges WHERE generation_id = ?`, generationID, func(values []string) {
		snapshot.Edges[values[0]+"|"+values[1]+"|"+values[2]+"|"+values[3]] = true
	}); err != nil {
		return snapshot, fmt.Errorf("read edge identities: %w", err)
	}
	if err := scanSnapshotRows(ctx, s.db, `SELECT id FROM observations WHERE generation_id = ?`, generationID, func(values []string) {
		snapshot.Observations[values[0]] = true
	}); err != nil {
		return snapshot, fmt.Errorf("read observation identities: %w", err)
	}
	if err := scanSnapshotRows(ctx, s.db, `SELECT path FROM path_index WHERE generation_id = ?`, generationID, func(values []string) {
		snapshot.CoveragePaths[values[0]] = true
	}); err != nil {
		return snapshot, fmt.Errorf("read coverage identities: %w", err)
	}

	attrsJSON := "{}"
	if err := s.db.QueryRowContext(ctx, `SELECT attrs_json FROM generations WHERE id = ?`, generationID).Scan(&attrsJSON); err != nil {
		return snapshot, fmt.Errorf("read generation attrs: %w", err)
	}
	var attrs struct {
		Rejections   []RowDecision `json:"rejections"`
		MergeRecords []MergeRecord `json:"merge_records"`
	}
	if err := json.Unmarshal([]byte(attrsJSON), &attrs); err != nil {
		return snapshot, fmt.Errorf("decode generation attrs: %w", err)
	}
	if attrs.Rejections != nil {
		snapshot.Rejections = attrs.Rejections
	}
	if attrs.MergeRecords != nil {
		snapshot.MergeRecords = attrs.MergeRecords
	}
	return snapshot, nil
}

func nextGenerationSequence(ctx context.Context, tx *sql.Tx) (int, error) {
	var current sql.NullInt64
	if err := tx.QueryRowContext(ctx, `SELECT MAX(sequence) FROM generations`).Scan(&current); err != nil {
		return 0, fmt.Errorf("read next generation sequence: %w", err)
	}
	if !current.Valid {
		return 1, nil
	}
	return int(current.Int64) + 1, nil
}

func generationAttrsJSON(rejections []RowDecision, mergeRecords []MergeRecord) (string, error) {
	if rejections == nil {
		rejections = []RowDecision{}
	}
	if mergeRecords == nil {
		mergeRecords = []MergeRecord{}
	}
	encoded, err := json.Marshal(map[string]any{
		"rejections":    rejections,
		"merge_records": mergeRecords,
	})
	if err != nil {
		return "", fmt.Errorf("encode generation attrs: %w", err)
	}
	return string(encoded), nil
}

func attrsJSONOrEmpty(attrs map[string]any) (string, error) {
	if attrs == nil {
		return "{}", nil
	}
	encoded, err := json.Marshal(attrs)
	if err != nil {
		return "", err
	}
	return string(encoded), nil
}

func validateEdgeNodes(ctx context.Context, tx *sql.Tx, generationID string, edge EdgeImport) error {
	for _, nodeID := range []string{edge.SourceID, edge.TargetID} {
		var count int
		if err := tx.QueryRowContext(ctx, `SELECT COUNT(*) FROM nodes WHERE generation_id = ? AND id = ?`, generationID, nodeID).Scan(&count); err != nil {
			return fmt.Errorf("validate edge %s node %s: %w", edge.ID, nodeID, err)
		}
		if count == 0 {
			return fmt.Errorf("edge %s references missing node %s", edge.ID, nodeID)
		}
	}
	return nil
}

func writeImportMetadata(ctx context.Context, tx *sql.Tx, generationID, now string) error {
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
			return fmt.Errorf("encode metadata %s: %w", key, err)
		}
		if _, err := tx.ExecContext(ctx, `INSERT INTO metadata(key, value_json, updated_at) VALUES(?, ?, ?) ON CONFLICT(key) DO UPDATE SET value_json=excluded.value_json, updated_at=excluded.updated_at`, key, string(encoded), now); err != nil {
			return fmt.Errorf("write metadata %s: %w", key, err)
		}
	}
	return nil
}

func scanSnapshotRows(ctx context.Context, db *sql.DB, query string, generationID string, collect func([]string)) error {
	rows, err := db.QueryContext(ctx, query, generationID)
	if err != nil {
		return err
	}
	defer rows.Close()
	columns, err := rows.Columns()
	if err != nil {
		return err
	}
	for rows.Next() {
		values := make([]string, len(columns))
		scanValues := make([]any, len(columns))
		for i := range values {
			scanValues[i] = &values[i]
		}
		if err := rows.Scan(scanValues...); err != nil {
			return err
		}
		collect(values)
	}
	return rows.Err()
}
