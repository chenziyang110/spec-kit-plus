package store

import (
	"context"
	"fmt"
	"strings"
)

type ClaimEvidencePage struct {
	Records    []GraphClaimEvidence
	TotalCount int
	Offset     int
}

// ClaimEvidencePageForNodeIDs fairly interleaves the selected lanes, retaining
// their order and putting contradicted/stale claims first within each lane.
// Offset is over that complete deterministic sequence, not a truncated subset.
func (s *Store) ClaimEvidencePageForNodeIDs(ctx context.Context, nodeIDs []string, offset, limit int) (ClaimEvidencePage, error) {
	page := ClaimEvidencePage{Records: []GraphClaimEvidence{}, Offset: offset}
	if offset < 0 || limit < 1 || limit > 25 {
		return page, fmt.Errorf("claim evidence page requires offset >= 0 and limit between 1 and 25")
	}
	ordered := []string{}
	seen := map[string]bool{}
	for _, id := range nodeIDs {
		if id != "" && !seen[id] {
			seen[id] = true
			ordered = append(ordered, id)
		}
	}
	if len(ordered) == 0 {
		return page, nil
	}
	generation, err := s.ActiveGenerationID(ctx)
	if err != nil || generation == "" {
		return page, err
	}
	placeholders := strings.TrimSuffix(strings.Repeat("?,", len(ordered)), ",")
	countArgs := []any{generation}
	for _, id := range ordered {
		countArgs = append(countArgs, id)
	}
	if err := s.db.QueryRowContext(ctx, `SELECT COUNT(*) FROM claims c JOIN nodes n ON n.id=c.node_id AND n.generation_id=c.generation_id WHERE c.generation_id=? AND c.node_id IN (`+placeholders+`)`, countArgs...).Scan(&page.TotalCount); err != nil {
		return page, fmt.Errorf("count selected lane claims: %w", err)
	}
	args := []any{}
	for order, id := range ordered {
		args = append(args, id, order)
	}
	args = append(args, generation, limit, offset)
	values := strings.TrimSuffix(strings.Repeat("(?,?),", len(ordered)), ",")
	rows, err := s.db.QueryContext(ctx, `WITH selected(node_id, lane_order) AS (VALUES `+values+`), ranked AS (
		SELECT c.id,c.node_id,c.graph_claim_type,c.summary,c.state,c.freshness,c.state_reason,n.confidence,selected.lane_order,
		ROW_NUMBER() OVER (PARTITION BY c.node_id ORDER BY CASE WHEN c.state='contradicted' THEN 0 WHEN c.state='stale' OR c.freshness='stale' THEN 1 ELSE 2 END,c.id) AS quota_rank
		FROM claims c JOIN nodes n ON n.id=c.node_id AND n.generation_id=c.generation_id JOIN selected ON selected.node_id=c.node_id WHERE c.generation_id=?
	) SELECT id,node_id,graph_claim_type,summary,state,freshness,state_reason,confidence FROM ranked ORDER BY quota_rank,lane_order,id LIMIT ? OFFSET ?`, args...)
	if err != nil {
		return page, fmt.Errorf("read selected lane claim page: %w", err)
	}
	for rows.Next() {
		var record GraphClaimEvidence
		if err := rows.Scan(&record.ID, &record.NodeID, &record.GraphClaimType, &record.Summary, &record.State, &record.Freshness, &record.StateReason, &record.RouteConfidence); err != nil {
			_ = rows.Close()
			return page, err
		}
		record.Evidence = []GraphClaimEvidenceRef{}
		page.Records = append(page.Records, record)
	}
	if err := rows.Err(); err != nil {
		_ = rows.Close()
		return page, err
	}
	if err := rows.Close(); err != nil {
		return page, err
	}
	if len(page.Records) == 0 {
		return page, nil
	}
	indexByID := map[string]int{}
	evidenceArgs := []any{generation}
	for index, record := range page.Records {
		indexByID[record.ID] = index
		evidenceArgs = append(evidenceArgs, record.ID)
	}
	claimPlaceholders := strings.TrimSuffix(strings.Repeat("?,", len(page.Records)), ",")
	refs, err := s.db.QueryContext(ctx, `SELECT ce.claim_id,e.id,ce.role,e.source_kind,e.source_path,e.span,e.commit_sha FROM claim_evidence ce JOIN evidence e ON e.id=ce.evidence_id WHERE e.generation_id=? AND ce.basis_state='current' AND ce.claim_id IN (`+claimPlaceholders+`) ORDER BY ce.claim_id,CASE ce.role WHEN 'contradicting' THEN 0 ELSE 1 END,e.id`, evidenceArgs...)
	if err != nil {
		return page, fmt.Errorf("read selected lane claim evidence: %w", err)
	}
	defer refs.Close()
	for refs.Next() {
		var id string
		var ref GraphClaimEvidenceRef
		if err := refs.Scan(&id, &ref.ID, &ref.Role, &ref.SourceKind, &ref.SourcePath, &ref.Span, &ref.CommitSHA); err != nil {
			return page, err
		}
		index := indexByID[id]
		page.Records[index].Evidence = append(page.Records[index].Evidence, ref)
	}
	return page, refs.Err()
}
