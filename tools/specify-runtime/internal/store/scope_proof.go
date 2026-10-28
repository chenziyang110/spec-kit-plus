package store

import (
	"context"
	"fmt"
	"strings"
)

// ScopeSourceOwner is the complete active path-index source/policy basis, not
// an agent-owned database representation or permission to change that source.
type ScopeSourceOwner struct {
	Path, NodeID, Relation, Confidence, EvidencePath, ContentHash string
}

type ScopeProofEvidence struct {
	OwnerKind, OwnerID, EvidenceID, SourcePath, ContentHash string
}

type ScopeProofMaterial struct {
	Evidence          []ScopeProofEvidence
	IncompleteReasons []string
}

func (s *Store) ScopeOwners(ctx context.Context) ([]ScopeSourceOwner, error) {
	generation, err := s.ActiveGenerationID(ctx)
	if err != nil {
		return nil, err
	}
	rows, err := s.db.QueryContext(ctx, `SELECT p.path,p.node_id,p.relation,p.confidence,COALESCE(e.source_path,''),COALESCE(e.content_hash,'') FROM path_index p LEFT JOIN evidence e ON e.generation_id=p.generation_id AND e.id=p.evidence_id WHERE p.generation_id=? ORDER BY p.path,p.node_id,p.id`, generation)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	owners := []ScopeSourceOwner{}
	for rows.Next() {
		var owner ScopeSourceOwner
		if err := rows.Scan(&owner.Path, &owner.NodeID, &owner.Relation, &owner.Confidence, &owner.EvidencePath, &owner.ContentHash); err != nil {
			return nil, err
		}
		owners = append(owners, owner)
	}
	return owners, rows.Err()
}

// ScopeProofMaterialForNodeIDs reads ALL current bases rather than the bounded
// navigation disclosure pages. Callers retain the Store navigation read guard,
// validate these hashes against live bytes, expand dependencies to a fixed
// point, and revalidate both Store and bytes before claiming scoped readiness.
func (s *Store) ScopeProofMaterialForNodeIDs(ctx context.Context, nodeIDs []string) (ScopeProofMaterial, error) {
	material := ScopeProofMaterial{Evidence: []ScopeProofEvidence{}, IncompleteReasons: []string{}}
	nodeIDs = uniqueSorted(nodeIDs)
	if len(nodeIDs) == 0 {
		return material, nil
	}
	generation, err := s.ActiveGenerationID(ctx)
	if err != nil {
		return material, err
	}
	marks := strings.TrimSuffix(strings.Repeat("?,", len(nodeIDs)), ",")
	args := []any{generation}
	for _, id := range nodeIDs {
		args = append(args, id)
	}
	nodeRows, err := s.db.QueryContext(ctx, `SELECT n.id,n.confidence,COALESCE(e.id,''),COALESCE(e.source_path,''),COALESCE(e.content_hash,'') FROM nodes n LEFT JOIN node_evidence ne ON ne.node_id=n.id LEFT JOIN evidence e ON e.id=ne.evidence_id AND e.generation_id=n.generation_id WHERE n.generation_id=? AND n.id IN (`+marks+`) ORDER BY n.id,e.id`, args...)
	if err != nil {
		return material, err
	}
	seen := map[string]bool{}
	for nodeRows.Next() {
		var row ScopeProofEvidence
		var confidence string
		row.OwnerKind = "node"
		if err := nodeRows.Scan(&row.OwnerID, &confidence, &row.EvidenceID, &row.SourcePath, &row.ContentHash); err != nil {
			nodeRows.Close()
			return material, err
		}
		seen[row.OwnerID] = true
		material.Evidence = append(material.Evidence, row)
		if !scopeProofConfidence(confidence) {
			material.IncompleteReasons = append(material.IncompleteReasons, "node_support_weak:"+row.OwnerID)
		}
	}
	if err := nodeRows.Err(); err != nil {
		nodeRows.Close()
		return material, err
	}
	if err := nodeRows.Close(); err != nil {
		return material, err
	}
	for _, id := range nodeIDs {
		if !seen[id] {
			material.IncompleteReasons = append(material.IncompleteReasons, "node_missing:"+id)
		}
	}
	edgeArgs := append([]any{}, args...)
	for _, id := range nodeIDs {
		edgeArgs = append(edgeArgs, id)
	}
	edgeRows, err := s.db.QueryContext(ctx, `SELECT x.id,x.confidence,COALESCE(e.id,''),COALESCE(e.source_path,''),COALESCE(e.content_hash,'') FROM edges x LEFT JOIN edge_evidence xe ON xe.edge_id=x.id LEFT JOIN evidence e ON e.id=xe.evidence_id AND e.generation_id=x.generation_id WHERE x.generation_id=? AND TRIM(x.type)<>'' AND (x.source_id IN (`+marks+`) OR x.target_id IN (`+marks+`)) ORDER BY x.id,e.id`, edgeArgs...)
	if err != nil {
		return material, err
	}
	for edgeRows.Next() {
		var row ScopeProofEvidence
		var confidence string
		row.OwnerKind = "edge"
		if err := edgeRows.Scan(&row.OwnerID, &confidence, &row.EvidenceID, &row.SourcePath, &row.ContentHash); err != nil {
			edgeRows.Close()
			return material, err
		}
		material.Evidence = append(material.Evidence, row)
		if !scopeProofConfidence(confidence) {
			material.IncompleteReasons = append(material.IncompleteReasons, "edge_support_weak:"+row.OwnerID)
		}
	}
	if err := edgeRows.Err(); err != nil {
		edgeRows.Close()
		return material, err
	}
	if err := edgeRows.Close(); err != nil {
		return material, err
	}
	claimRows, err := s.db.QueryContext(ctx, `SELECT c.id,COALESCE(ce.role,''),COALESCE(e.id,''),COALESCE(e.source_path,''),COALESCE(e.content_hash,'') FROM claims c LEFT JOIN claim_evidence ce ON ce.claim_id=c.id AND ce.basis_state='current' LEFT JOIN evidence e ON e.id=ce.evidence_id AND e.generation_id=c.generation_id WHERE c.generation_id=? AND c.node_id IN (`+marks+`) ORDER BY c.id,ce.role,e.id`, args...)
	if err != nil {
		return material, err
	}
	for claimRows.Next() {
		var row ScopeProofEvidence
		var role string
		row.OwnerKind = "claim"
		if err := claimRows.Scan(&row.OwnerID, &role, &row.EvidenceID, &row.SourcePath, &row.ContentHash); err != nil {
			claimRows.Close()
			return material, err
		}
		material.Evidence = append(material.Evidence, row)
		if role != "supporting" {
			material.IncompleteReasons = append(material.IncompleteReasons, "claim_support_uncertain:"+row.OwnerID)
		}
	}
	if err := claimRows.Err(); err != nil {
		claimRows.Close()
		return material, err
	}
	if err := claimRows.Close(); err != nil {
		return material, err
	}
	for _, row := range material.Evidence {
		if row.EvidenceID == "" || row.SourcePath == "" || row.ContentHash == "" {
			material.IncompleteReasons = append(material.IncompleteReasons, fmt.Sprintf("%s_evidence_incomplete:%s", row.OwnerKind, row.OwnerID))
		}
	}
	summaries, err := s.ClaimLifecycleSummariesForNodeIDs(ctx, nodeIDs)
	if err != nil {
		return material, err
	}
	for _, summary := range summaries {
		if summary.ClaimCount != summary.FreshSupportedCount+summary.FreshVerifiedCount {
			material.IncompleteReasons = append(material.IncompleteReasons, "claim_lifecycle_requires_live_verification:"+summary.NodeID)
		}
	}
	material.IncompleteReasons = uniqueSorted(material.IncompleteReasons)
	return material, nil
}

func scopeProofConfidence(value string) bool { return value == "high" || value == "verified" }
