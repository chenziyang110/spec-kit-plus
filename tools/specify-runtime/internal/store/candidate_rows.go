package store

import (
	"context"
	"database/sql"
	"fmt"
	"sort"
	"strings"
)

// ConceptCandidatePage counts the full active universe but materializes only
// the stable ID-ordered page, all from the same SQLite read transaction.
type ConceptCandidatePage struct {
	GenerationID string
	Rows         []ConceptCandidateRow
	Offset       int
	Total        int
}

func (s *Store) ActiveConceptCandidatePage(ctx context.Context, offset, limit int) (ConceptCandidatePage, error) {
	if limit <= 0 {
		limit = 10
	}
	return s.readConceptCandidateRows(ctx, offset, limit, true)
}

func (s *Store) activeConceptCandidateRows(ctx context.Context, limit int, limited bool) ([]ConceptCandidateRow, error) {
	if limited && limit <= 0 {
		limit = 200
	}
	if !limited {
		limit = -1
	}
	page, err := s.readConceptCandidateRows(ctx, 0, limit, false)
	return page.Rows, err
}

func (s *Store) readConceptCandidateRows(ctx context.Context, offset, limit int, counted bool) (ConceptCandidatePage, error) {
	page := ConceptCandidatePage{Rows: []ConceptCandidateRow{}}
	tx, err := s.db.BeginTx(ctx, &sql.TxOptions{ReadOnly: true})
	if err != nil {
		return page, err
	}
	defer tx.Rollback()
	page.GenerationID, err = activeGenerationIDTx(ctx, tx)
	if err != nil || page.GenerationID == "" {
		return page, err
	}
	if counted {
		if err := tx.QueryRowContext(ctx, `SELECT COUNT(*) FROM nodes WHERE generation_id = ?`, page.GenerationID).Scan(&page.Total); err != nil {
			return page, err
		}
		if offset > page.Total {
			offset = page.Total
		}
	}
	if offset < 0 {
		offset = 0
	}
	page.Offset = offset
	rows, err := tx.QueryContext(ctx, `SELECT id, type, title, confidence, attrs_json FROM nodes WHERE generation_id = ? ORDER BY id LIMIT ? OFFSET ?`, page.GenerationID, limit, offset)
	if err != nil {
		return page, fmt.Errorf("query active concept candidate nodes: %w", err)
	}
	for rows.Next() {
		row := ConceptCandidateRow{GenerationID: page.GenerationID, Paths: []string{}, Aliases: []ConceptAliasRow{}, EvidenceIDs: []string{}, EvidencePaths: []string{}, ObservationSummaries: []string{}}
		if err := rows.Scan(&row.NodeID, &row.NodeType, &row.Title, &row.Confidence, &row.AttrsJSON); err != nil {
			rows.Close()
			return page, err
		}
		page.Rows = append(page.Rows, row)
	}
	err = rows.Err()
	rows.Close()
	if err != nil {
		return page, err
	}
	if len(page.Rows) > 0 {
		if err := hydrateConceptCandidateRows(ctx, tx, page.GenerationID, page.Rows); err != nil {
			return page, err
		}
	}
	if !counted {
		page.Total = len(page.Rows)
	}
	if err := tx.Commit(); err != nil {
		return page, err
	}
	return page, nil
}

func hydrateConceptCandidateRows(ctx context.Context, tx *sql.Tx, generationID string, candidates []ConceptCandidateRow) error {
	// The selected IDs are contiguous in this transaction's ID ordering. A
	// bounded range avoids per-node statements and SQLite parameter-count limits.
	selected := `WITH selected AS (SELECT id FROM nodes WHERE generation_id = ? AND id >= ? AND id <= ?)`
	args := []any{generationID, candidates[0].NodeID, candidates[len(candidates)-1].NodeID, generationID}
	byID := make(map[string]*ConceptCandidateRow, len(candidates))
	for index := range candidates {
		byID[candidates[index].NodeID] = &candidates[index]
	}
	read := func(statement string, visit func(*sql.Rows) error) error {
		rows, err := tx.QueryContext(ctx, statement, args...)
		if err != nil {
			return err
		}
		defer rows.Close()
		for rows.Next() {
			if err := visit(rows); err != nil {
				return err
			}
		}
		return rows.Err()
	}
	if err := read(selected+` SELECT p.node_id, p.path FROM selected s JOIN path_index p ON p.node_id = s.id WHERE p.generation_id = ? ORDER BY p.node_id, p.path`, func(rows *sql.Rows) error {
		var id, value string
		if err := rows.Scan(&id, &value); err != nil {
			return err
		}
		byID[id].Paths = append(byID[id].Paths, value)
		return nil
	}); err != nil {
		return fmt.Errorf("query candidate paths: %w", err)
	}
	seenAliases := map[string]map[string]bool{}
	if err := read(selected+` SELECT a.target_id, a.alias, a.normalized_alias, a.source, a.confidence, a.evidence_id FROM selected s JOIN alias_index a ON a.target_id = s.id WHERE a.generation_id = ? AND a.target_type = 'node' ORDER BY a.target_id, a.source, a.normalized_alias, a.id`, func(rows *sql.Rows) error {
		var id string
		var alias ConceptAliasRow
		if err := rows.Scan(&id, &alias.Alias, &alias.NormalizedAlias, &alias.Source, &alias.Confidence, &alias.EvidenceID); err != nil {
			return err
		}
		if seenAliases[id] == nil {
			seenAliases[id] = map[string]bool{}
		}
		key := alias.Source + "\x00" + alias.NormalizedAlias
		if strings.TrimSpace(alias.Alias) != "" && !seenAliases[id][key] {
			seenAliases[id][key] = true
			byID[id].Aliases = append(byID[id].Aliases, alias)
		}
		return nil
	}); err != nil {
		return fmt.Errorf("query candidate aliases: %w", err)
	}
	// Union by node AND evidence preserves shared/duplicate evidence semantics.
	evidence := selected + `, candidate_evidence AS (
	SELECT ne.node_id, ne.evidence_id FROM selected s JOIN node_evidence ne ON ne.node_id = s.id
	UNION SELECT p.node_id, p.evidence_id FROM selected s JOIN path_index p ON p.node_id = s.id WHERE p.generation_id = ?
)`
	args = append(args, generationID)
	if err := read(evidence+` SELECT ce.node_id, e.id, e.source_path FROM candidate_evidence ce JOIN evidence e ON e.id = ce.evidence_id WHERE e.generation_id = ? ORDER BY ce.node_id, e.id`, func(rows *sql.Rows) error {
		var id, evidenceID, path string
		if err := rows.Scan(&id, &evidenceID, &path); err != nil {
			return err
		}
		byID[id].EvidenceIDs = append(byID[id].EvidenceIDs, evidenceID)
		byID[id].EvidencePaths = append(byID[id].EvidencePaths, path)
		return nil
	}); err != nil {
		return fmt.Errorf("query candidate evidence: %w", err)
	}
	if err := read(evidence+` SELECT ce.node_id, o.summary FROM candidate_evidence ce JOIN observation_evidence oe ON oe.evidence_id = ce.evidence_id JOIN observations o ON o.id = oe.observation_id WHERE o.generation_id = ? ORDER BY ce.node_id, o.summary`, func(rows *sql.Rows) error {
		var id, summary string
		if err := rows.Scan(&id, &summary); err != nil {
			return err
		}
		byID[id].ObservationSummaries = append(byID[id].ObservationSummaries, summary)
		return nil
	}); err != nil {
		return fmt.Errorf("query candidate observations: %w", err)
	}
	for index := range candidates {
		row := &candidates[index]
		row.Paths = normalizeStoreStrings(row.Paths)
		row.EvidenceIDs = normalizeStoreStrings(row.EvidenceIDs)
		sort.Strings(row.EvidencePaths)
		row.EvidencePaths = normalizeStoreStrings(row.EvidencePaths)
		row.ObservationSummaries = normalizeStoreStrings(row.ObservationSummaries)
	}
	return nil
}
