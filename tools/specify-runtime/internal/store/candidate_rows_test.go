package store

import (
	"context"
	"fmt"
	"reflect"
	"testing"
)

func TestCandidateBatchMatchesLegacyMaterialAndExactPages(t *testing.T) {
	ctx := context.Background()
	st := openImportTestStore(t)
	defer st.Close()
	input := validImportInput("GEN-candidate-batch")
	input.Nodes = nil
	input.PathIndex = nil
	input.Edges = nil
	input.Evidence = []EvidenceImport{
		{ID: "E-shared", SourceKind: "source", SourcePath: " src/共享.go ", CommitSHA: "abc123", Extractor: "test", ContentHash: "shared"},
		{ID: "E-same-path", SourceKind: "source", SourcePath: "src/共享.go", CommitSHA: "abc123", Extractor: "test", ContentHash: "same-path"},
	}
	input.Observations = []ObservationImport{
		{ID: "O-one", ObservationType: "summary", Summary: " shared summary ", EvidenceIDs: []string{"E-shared", "E-same-path"}},
		{ID: "O-two", ObservationType: "summary", Summary: "shared summary", EvidenceIDs: []string{"E-shared"}},
	}
	input.Aliases = nil
	for index := 0; index < 37; index++ {
		id := fmt.Sprintf("N-%03d", index)
		input.Nodes = append(input.Nodes, NodeImport{ID: id, Type: "capability", Title: "共同 runtime owner", Confidence: "high", EvidenceIDs: []string{"E-shared", "E-same-path"}, Attrs: map[string]any{"owner": "runtime", "aliases": []string{"切换", "runtime override"}, "exclusions": []string{"history"}}})
		input.PathIndex = append(input.PathIndex,
			PathIndexImport{ID: "P-" + id, Path: fmt.Sprintf("src/%s.go", id), NodeID: id, Relation: "owns", Confidence: "high", EvidenceID: "E-shared"},
			PathIndexImport{ID: "P-duplicate-" + id, Path: fmt.Sprintf("src/%s.go", id), NodeID: id, Relation: "reads", Confidence: "high", EvidenceID: "E-same-path"})
	}
	if _, err := st.ImportGeneration(ctx, input); err != nil {
		t.Fatal(err)
	}
	// Malformed optional cards and whitespace are tolerated exactly as before;
	// malformed database schemas are still rejected by the existing Store gate.
	if _, err := st.db.ExecContext(ctx, `UPDATE nodes SET attrs_json = '{malformed' WHERE id = 'N-003'`); err != nil {
		t.Fatal(err)
	}
	if _, err := st.db.ExecContext(ctx, `UPDATE alias_index SET alias = '  ' WHERE target_id = 'N-004'`); err != nil {
		t.Fatal(err)
	}
	want, err := st.legacyConceptCandidateRows(ctx, 0, false)
	if err != nil {
		t.Fatal(err)
	}
	got, err := st.AllActiveConceptCandidateRows(ctx)
	if err != nil || !reflect.DeepEqual(got, want) {
		t.Fatalf("batch differs from unchanged original owner: got=%#v want=%#v err=%v", got, want, err)
	}
	for _, limit := range []int{0, 1, 8, 99} {
		got, err := st.ActiveConceptCandidateRows(ctx, limit)
		want, wantErr := st.legacyConceptCandidateRows(ctx, limit, true)
		if err != nil || wantErr != nil || !reflect.DeepEqual(got, want) {
			t.Fatalf("limited material differs at %d: %v %v", limit, err, wantErr)
		}
	}
	var traversed []ConceptCandidateRow
	for offset := 0; offset < len(want); offset += 8 {
		page, err := st.ActiveConceptCandidatePage(ctx, offset, 8)
		end := offset + 8
		if end > len(want) {
			end = len(want)
		}
		if err != nil || page.GenerationID != input.GenerationID || page.Total != len(want) || page.Offset != offset || !reflect.DeepEqual(page.Rows, want[offset:end]) {
			t.Fatalf("page differs at %d: %#v %v", offset, page, err)
		}
		traversed = append(traversed, page.Rows...)
	}
	if !reflect.DeepEqual(traversed, want) {
		t.Fatal("page traversal dropped or repeated material")
	}
	for _, offset := range []int{-1, 37, 100} {
		page, err := st.ActiveConceptCandidatePage(ctx, offset, 8)
		if err != nil || page.Total != 37 {
			t.Fatalf("boundary page failed: %#v %v", page, err)
		}
		if offset < 0 && (page.Offset != 0 || len(page.Rows) != 8) || offset >= 37 && (page.Offset != 37 || len(page.Rows) != 0) {
			t.Fatalf("boundary behavior changed: %#v", page)
		}
	}
}

// Frozen pre-optimization loader used as a differential oracle, not a product path.
func (s *Store) legacyConceptCandidateRows(ctx context.Context, limit int, limited bool) ([]ConceptCandidateRow, error) {
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
