package store

import (
	"context"
	"database/sql"
	"encoding/json"
	"errors"
	"fmt"
	"path/filepath"
	"sort"
	"strings"

	changemodel "github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/changes/model"
)

type typedPathIndexRow struct {
	ID         string
	NodeID     string
	Relation   string
	Confidence string
	EvidenceID string
}

func normalizeTypedPathChanges(values []changemodel.PathChange) ([]changemodel.PathChange, error) {
	out := make([]changemodel.PathChange, 0, len(values))
	affectedPaths := map[string]string{}
	for _, value := range values {
		change := value
		change.Path = normalizeTypedRepositoryPath(change.Path)
		change.OldPath = normalizeTypedRepositoryPath(change.OldPath)
		change.NodeID = strings.TrimSpace(change.NodeID)
		change.EvidenceRefs = uniqueSorted(change.EvidenceRefs)
		if err := change.Validate(); err != nil {
			return nil, err
		}
		if !validTypedRepositoryPath(change.Path) {
			return nil, fmt.Errorf("path change %q is not a concrete repository-relative path", change.Path)
		}
		if change.Operation == changemodel.OperationRename {
			if !validTypedRepositoryPath(change.OldPath) {
				return nil, fmt.Errorf("path change %q has invalid old_path %q", change.Path, change.OldPath)
			}
			if change.Path == change.OldPath {
				return nil, fmt.Errorf("path change %q rename must change the path", change.Path)
			}
		}
		for _, path := range []string{change.Path, change.OldPath} {
			if path == "" {
				continue
			}
			if owner, exists := affectedPaths[path]; exists {
				return nil, fmt.Errorf("path %q appears in multiple typed changes (%s and %s)", path, owner, change.Operation)
			}
			affectedPaths[path] = string(change.Operation)
		}
		out = append(out, change)
	}
	sort.Slice(out, func(i, j int) bool {
		if out[i].Path == out[j].Path {
			return out[i].OldPath < out[j].OldPath
		}
		return out[i].Path < out[j].Path
	})
	return out, nil
}

func normalizeTypedRepositoryPath(value string) string {
	value = filepath.ToSlash(strings.TrimSpace(value))
	for strings.HasPrefix(value, "./") {
		value = strings.TrimPrefix(value, "./")
	}
	return strings.TrimRight(value, "/")
}

func validTypedRepositoryPath(value string) bool {
	value = filepath.ToSlash(strings.TrimSpace(value))
	if value == "" || value == "." || filepath.IsAbs(value) || filepath.VolumeName(value) != "" || strings.Contains(value, ":") {
		return false
	}
	if value == ".specify" || strings.HasPrefix(value, ".specify/") {
		return false
	}
	for _, part := range strings.Split(value, "/") {
		if part == "" || part == "." || part == ".." {
			return false
		}
	}
	return true
}

func applyAddPathTx(ctx context.Context, tx *sql.Tx, generationID string, input TypedUpdate, change changemodel.PathChange, now string) ([]string, error) {
	rows, err := typedPathIndexRowsTx(ctx, tx, generationID, change.Path)
	if err != nil {
		return nil, err
	}
	if len(rows) > 0 {
		return nil, fmt.Errorf("add path %s already has active path coverage", change.Path)
	}
	nodeID := strings.TrimSpace(change.NodeID)
	createdNode := false
	if nodeID == "" {
		nodeID = "N-update-" + stableIDPart(generationID+"-"+change.Path)
		createdNode = true
	} else if err := requireActiveNodeTx(ctx, tx, generationID, nodeID); err != nil {
		return nil, err
	}
	reason := typedUpdateReason(input)
	evidenceID, err := upsertTypedUpdateEvidenceTx(ctx, tx, generationID, input.Record.ID, change, reason, now)
	if err != nil {
		return nil, err
	}
	if createdNode {
		attrs, err := attrsJSONOrEmpty(map[string]any{
			"source":            "specify-runtime cognition update",
			"update_id":         input.Record.ID,
			"workflow":          strings.TrimSpace(input.Workflow),
			"behavior_surfaces": uniqueSorted(input.BehaviorSurfaces),
			"verification":      input.Verification,
			"reason":            reason,
			"evidence_refs":     change.EvidenceRefs,
		})
		if err != nil {
			return nil, fmt.Errorf("encode adopted workflow node attrs: %w", err)
		}
		if _, err := tx.ExecContext(ctx, `INSERT INTO nodes(id, generation_id, type, title, confidence, attrs_json, created_at, updated_at) VALUES(?, ?, 'workflow_update', ?, 'partial', ?, ?, ?)`, nodeID, generationID, workflowPathTitle(change.Path), attrs, now, now); err != nil {
			return nil, fmt.Errorf("insert adopted workflow node for %s: %w", change.Path, err)
		}
	}
	pathIndexID := "P-update-" + stableIDPart(generationID+"-"+change.Path+"-"+nodeID)
	relation := "owns"
	if createdNode {
		relation = "provisional_path"
	}
	if _, err := tx.ExecContext(ctx, `INSERT INTO path_index(id, generation_id, path, node_id, relation, confidence, evidence_id, updated_at) VALUES(?, ?, ?, ?, ?, 'partial', ?, ?)`, pathIndexID, generationID, change.Path, nodeID, relation, evidenceID, now); err != nil {
		return nil, fmt.Errorf("insert path coverage for %s: %w", change.Path, err)
	}
	if _, err := tx.ExecContext(ctx, `INSERT OR IGNORE INTO node_evidence(node_id, evidence_id) VALUES(?, ?)`, nodeID, evidenceID); err != nil {
		return nil, fmt.Errorf("link adopted path evidence for %s: %w", change.Path, err)
	}
	title := ""
	if createdNode {
		title = workflowPathTitle(change.Path)
	}
	if err := upsertWorkflowPathAliasesTx(ctx, tx, generationID, nodeID, change.Path, title, input.Workflow, input.BehaviorSurfaces, evidenceID, "partial"); err != nil {
		return nil, err
	}
	return []string{nodeID}, nil
}

func applyModifyPathTx(ctx context.Context, tx *sql.Tx, generationID string, input TypedUpdate, change changemodel.PathChange, now string) ([]string, error) {
	rows, err := typedPathIndexRowsTx(ctx, tx, generationID, change.Path)
	if err != nil {
		return nil, err
	}
	if len(rows) == 0 {
		return nil, fmt.Errorf("modify path %s has no active path coverage", change.Path)
	}
	if err := requireExpectedPathNode(change, rows); err != nil {
		return nil, err
	}
	evidenceID, err := upsertTypedUpdateEvidenceTx(ctx, tx, generationID, input.Record.ID, change, typedUpdateReason(input), now)
	if err != nil {
		return nil, err
	}
	nodeIDs := typedPathNodeIDs(rows)
	if _, err := tx.ExecContext(ctx, `UPDATE path_index SET evidence_id = ?, updated_at = ? WHERE generation_id = ? AND path = ?`, evidenceID, now, generationID, change.Path); err != nil {
		return nil, fmt.Errorf("refresh path coverage for %s: %w", change.Path, err)
	}
	for _, nodeID := range nodeIDs {
		if _, err := tx.ExecContext(ctx, `INSERT OR IGNORE INTO node_evidence(node_id, evidence_id) VALUES(?, ?)`, nodeID, evidenceID); err != nil {
			return nil, fmt.Errorf("link refreshed path evidence for %s: %w", change.Path, err)
		}
		if err := upsertWorkflowPathAliasesTx(ctx, tx, generationID, nodeID, change.Path, "", "", nil, evidenceID, "partial"); err != nil {
			return nil, err
		}
	}
	return nodeIDs, nil
}

func applyRenamePathTx(ctx context.Context, tx *sql.Tx, generationID string, input TypedUpdate, change changemodel.PathChange, now string) ([]string, error) {
	rows, err := typedPathIndexRowsTx(ctx, tx, generationID, change.OldPath)
	if err != nil {
		return nil, err
	}
	if len(rows) == 0 {
		return nil, fmt.Errorf("rename old_path %s has no active path coverage", change.OldPath)
	}
	if err := requireExpectedPathNode(change, rows); err != nil {
		return nil, err
	}
	targetRows, err := typedPathIndexRowsTx(ctx, tx, generationID, change.Path)
	if err != nil {
		return nil, err
	}
	if len(targetRows) > 0 {
		return nil, fmt.Errorf("rename target path %s already has active path coverage", change.Path)
	}
	evidenceID, err := upsertTypedUpdateEvidenceTx(ctx, tx, generationID, input.Record.ID, change, typedUpdateReason(input), now)
	if err != nil {
		return nil, err
	}
	if _, err := tx.ExecContext(ctx, `UPDATE path_index SET path = ?, evidence_id = ?, updated_at = ? WHERE generation_id = ? AND path = ?`, change.Path, evidenceID, now, generationID, change.OldPath); err != nil {
		return nil, fmt.Errorf("rename path coverage %s to %s: %w", change.OldPath, change.Path, err)
	}
	nodeIDs := typedPathNodeIDs(rows)
	for _, nodeID := range nodeIDs {
		if err := deleteUnbackedWorkflowPathAliasesTx(ctx, tx, generationID, nodeID, change.OldPath); err != nil {
			return nil, err
		}
		if _, err := tx.ExecContext(ctx, `INSERT OR IGNORE INTO node_evidence(node_id, evidence_id) VALUES(?, ?)`, nodeID, evidenceID); err != nil {
			return nil, fmt.Errorf("link renamed path evidence for %s: %w", change.Path, err)
		}
		if err := upsertWorkflowPathAliasesTx(ctx, tx, generationID, nodeID, change.Path, "", "", nil, evidenceID, "partial"); err != nil {
			return nil, err
		}
	}
	return nodeIDs, nil
}

func applyDeletePathTx(ctx context.Context, tx *sql.Tx, generationID string, change changemodel.PathChange) ([]string, error) {
	rows, err := typedPathIndexRowsTx(ctx, tx, generationID, change.Path)
	if err != nil {
		return nil, err
	}
	if len(rows) == 0 {
		return nil, fmt.Errorf("delete path %s has no active path coverage", change.Path)
	}
	if err := requireExpectedPathNode(change, rows); err != nil {
		return nil, err
	}
	if _, err := tx.ExecContext(ctx, `DELETE FROM path_index WHERE generation_id = ? AND path = ?`, generationID, change.Path); err != nil {
		return nil, fmt.Errorf("delete path coverage for %s: %w", change.Path, err)
	}
	nodeIDs := typedPathNodeIDs(rows)
	for _, nodeID := range nodeIDs {
		if err := deleteUnbackedWorkflowPathAliasesTx(ctx, tx, generationID, nodeID, change.Path); err != nil {
			return nil, err
		}
	}
	return nodeIDs, nil
}

func typedPathIndexRowsTx(ctx context.Context, tx *sql.Tx, generationID, path string) ([]typedPathIndexRow, error) {
	rows, err := tx.QueryContext(ctx, `SELECT id, node_id, relation, confidence, evidence_id FROM path_index WHERE generation_id = ? AND path = ? ORDER BY id`, generationID, path)
	if err != nil {
		return nil, fmt.Errorf("read path coverage for %s: %w", path, err)
	}
	defer rows.Close()
	out := []typedPathIndexRow{}
	for rows.Next() {
		var row typedPathIndexRow
		if err := rows.Scan(&row.ID, &row.NodeID, &row.Relation, &row.Confidence, &row.EvidenceID); err != nil {
			return nil, fmt.Errorf("scan path coverage for %s: %w", path, err)
		}
		out = append(out, row)
	}
	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("iterate path coverage for %s: %w", path, err)
	}
	return out, nil
}

func requireExpectedPathNode(change changemodel.PathChange, rows []typedPathIndexRow) error {
	if strings.TrimSpace(change.NodeID) == "" {
		return nil
	}
	for _, row := range rows {
		if row.NodeID == change.NodeID {
			return nil
		}
	}
	return fmt.Errorf("path change %s expected node %s but active coverage differs", change.Path, change.NodeID)
}

func typedPathNodeIDs(rows []typedPathIndexRow) []string {
	values := make([]string, 0, len(rows))
	for _, row := range rows {
		values = append(values, row.NodeID)
	}
	return uniqueSorted(values)
}

func requireActiveNodeTx(ctx context.Context, tx *sql.Tx, generationID, nodeID string) error {
	var found string
	err := tx.QueryRowContext(ctx, `SELECT id FROM nodes WHERE generation_id = ? AND id = ?`, generationID, nodeID).Scan(&found)
	if errors.Is(err, sql.ErrNoRows) {
		return fmt.Errorf("active generation has no node %s", nodeID)
	}
	if err != nil {
		return fmt.Errorf("read active node %s: %w", nodeID, err)
	}
	return nil
}

func upsertTypedUpdateEvidenceTx(ctx context.Context, tx *sql.Tx, generationID, updateID string, change changemodel.PathChange, reason, now string) (string, error) {
	evidenceID := "E-update-" + stableIDPart(updateID) + "-" + stableIDPart(generationID+"-"+change.Path)
	attrs, err := attrsJSONOrEmpty(map[string]any{
		"update_id":     updateID,
		"reason":        reason,
		"operation":     change.Operation,
		"old_path":      change.OldPath,
		"evidence_refs": change.EvidenceRefs,
	})
	if err != nil {
		return "", fmt.Errorf("encode typed update evidence attrs: %w", err)
	}
	if _, err := tx.ExecContext(ctx, `INSERT INTO evidence(id, generation_id, source_kind, source_path, commit_sha, span, extractor, content_hash, captured_at, attrs_json) VALUES(?, ?, 'workflow_update', ?, '', '', 'specify-runtime cognition update', '', ?, ?) ON CONFLICT(id) DO UPDATE SET source_path=excluded.source_path, captured_at=excluded.captured_at, attrs_json=excluded.attrs_json`, evidenceID, generationID, change.Path, now, attrs); err != nil {
		return "", fmt.Errorf("upsert typed update evidence for %s: %w", change.Path, err)
	}
	return evidenceID, nil
}

func typedUpdateReason(input TypedUpdate) string {
	if reason := strings.TrimSpace(input.Reason); reason != "" {
		return reason
	}
	return defaultString(input.Record.Trigger, "workflow-finalize")
}

func upsertWorkflowPathAliasesTx(ctx context.Context, tx *sql.Tx, generationID, nodeID, rawPath, title, workflow string, behaviorSurfaces []string, evidenceID, confidence string) error {
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
		alias := strings.TrimSpace(seed.alias)
		normalized := normalizeWorkflowAlias(alias)
		if alias == "" || normalized == "" || workflowAliasPathExcluded(alias) {
			continue
		}
		source := defaultString(seed.source, "workflow_update")
		aliasID := workflowAliasID(generationID, nodeID, normalized, source)
		if _, err := tx.ExecContext(ctx, `INSERT INTO alias_index(id, generation_id, alias, normalized_alias, target_type, target_id, language, source, confidence, evidence_id) VALUES(?, ?, ?, ?, 'node', ?, ?, ?, ?, ?) ON CONFLICT(id) DO UPDATE SET alias=excluded.alias, normalized_alias=excluded.normalized_alias, language=excluded.language, confidence=excluded.confidence, evidence_id=excluded.evidence_id`, aliasID, generationID, alias, normalized, nodeID, defaultString(seed.language, "unknown"), source, defaultString(seed.confidence, "partial"), seed.evidenceID); err != nil {
			return fmt.Errorf("upsert workflow alias %s for %s: %w", alias, nodeID, err)
		}
	}
	return nil
}

func deleteUnbackedWorkflowPathAliasesTx(ctx context.Context, tx *sql.Tx, generationID, nodeID, removedPath string) error {
	rows, err := tx.QueryContext(ctx, `SELECT path FROM path_index WHERE generation_id = ? AND node_id = ? ORDER BY path`, generationID, nodeID)
	if err != nil {
		return fmt.Errorf("read remaining paths for node %s: %w", nodeID, err)
	}
	remainingAliases := map[string]bool{}
	for rows.Next() {
		var path string
		if err := rows.Scan(&path); err != nil {
			_ = rows.Close()
			return fmt.Errorf("scan remaining path for node %s: %w", nodeID, err)
		}
		for _, alias := range workflowPathAliasValues(path) {
			remainingAliases[normalizeWorkflowAlias(alias)] = true
		}
	}
	if err := rows.Close(); err != nil {
		return fmt.Errorf("close remaining paths for node %s: %w", nodeID, err)
	}
	for _, alias := range workflowPathAliasValues(removedPath) {
		normalized := normalizeWorkflowAlias(alias)
		if normalized == "" || remainingAliases[normalized] {
			continue
		}
		if _, err := tx.ExecContext(ctx, `DELETE FROM alias_index WHERE generation_id = ? AND target_type = 'node' AND target_id = ? AND source = 'workflow_update_path' AND normalized_alias = ?`, generationID, nodeID, normalized); err != nil {
			return fmt.Errorf("delete stale workflow path alias %s for %s: %w", alias, nodeID, err)
		}
	}
	return nil
}

func claimIDsForNodeIDsTx(ctx context.Context, tx *sql.Tx, generationID string, nodeIDs []string) ([]string, error) {
	nodeIDs = uniqueSorted(nodeIDs)
	if len(nodeIDs) == 0 {
		return []string{}, nil
	}
	placeholders := strings.TrimSuffix(strings.Repeat("?,", len(nodeIDs)), ",")
	args := make([]any, 0, len(nodeIDs)+1)
	args = append(args, generationID)
	for _, nodeID := range nodeIDs {
		args = append(args, nodeID)
	}
	rows, err := tx.QueryContext(ctx, `SELECT id FROM claims WHERE generation_id = ? AND node_id IN (`+placeholders+`) ORDER BY id`, args...)
	if err != nil {
		return nil, fmt.Errorf("read claims for typed update nodes: %w", err)
	}
	defer rows.Close()
	claimIDs := []string{}
	for rows.Next() {
		var claimID string
		if err := rows.Scan(&claimID); err != nil {
			return nil, fmt.Errorf("scan claim for typed update node: %w", err)
		}
		claimIDs = append(claimIDs, claimID)
	}
	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("iterate claims for typed update nodes: %w", err)
	}
	return uniqueSorted(claimIDs), nil
}

func insertStructuredUpdateTx(ctx context.Context, tx *sql.Tx, generationID string, record UpdateRecord, now string) error {
	record.ChangedPaths = uniqueSorted(record.ChangedPaths)
	record.AffectedNodes = uniqueSorted(record.AffectedNodes)
	record.AffectedClaims = uniqueSorted(record.AffectedClaims)
	record.AffectedSlices = uniqueSorted(record.AffectedSlices)
	changedJSON, err := json.Marshal(record.ChangedPaths)
	if err != nil {
		return fmt.Errorf("encode update changed paths: %w", err)
	}
	nodesJSON, err := json.Marshal(record.AffectedNodes)
	if err != nil {
		return fmt.Errorf("encode update affected nodes: %w", err)
	}
	claimsJSON, err := json.Marshal(record.AffectedClaims)
	if err != nil {
		return fmt.Errorf("encode update affected claims: %w", err)
	}
	slicesJSON, err := json.Marshal(record.AffectedSlices)
	if err != nil {
		return fmt.Errorf("encode update affected slices: %w", err)
	}
	attrs, err := attrsJSONOrEmpty(record.Attrs)
	if err != nil {
		return fmt.Errorf("encode update attrs: %w", err)
	}
	if _, err := tx.ExecContext(ctx, `INSERT INTO updates(id, generation_id, trigger, changed_paths_json, affected_nodes_json, affected_claims_json, affected_slices_json, result_state, completed_at, attrs_json) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`, record.ID, generationID, record.Trigger, string(changedJSON), string(nodesJSON), string(claimsJSON), string(slicesJSON), record.ResultState, now, attrs); err != nil {
		return fmt.Errorf("record structured update: %w", err)
	}
	return nil
}

func cloneStringAnyMap(input map[string]any) map[string]any {
	out := make(map[string]any, len(input)+1)
	for key, value := range input {
		out[key] = value
	}
	return out
}

func (s *Store) expandTypedEdgeClosure(ctx context.Context, generationID string, startingNodeIDs []string, budget ClosureBudget) ([]string, []string, bool, error) {
	startingNodeIDs = uniqueSorted(startingNodeIDs)
	if generationID == "" || len(startingNodeIDs) == 0 {
		return []string{}, []string{}, false, nil
	}
	visited := map[string]bool{}
	edgeTypes := map[string]bool{}
	queue := []string{}
	truncated := false
	addNode := func(nodeID string) {
		nodeID = strings.TrimSpace(nodeID)
		if nodeID == "" || visited[nodeID] {
			return
		}
		if budget.MaxNodes > 0 && len(visited) >= budget.MaxNodes {
			truncated = true
			return
		}
		visited[nodeID] = true
		queue = append(queue, nodeID)
	}
	for _, nodeID := range startingNodeIDs {
		addNode(nodeID)
	}
	for len(queue) > 0 {
		nodeID := queue[0]
		queue = queue[1:]
		rows, err := s.db.QueryContext(ctx, `SELECT type, source_id, target_id FROM edges WHERE generation_id = ? AND TRIM(type) <> '' AND (source_id = ? OR target_id = ?) ORDER BY type, source_id, target_id`, generationID, nodeID, nodeID)
		if err != nil {
			return nil, nil, false, fmt.Errorf("read typed edges for %s: %w", nodeID, err)
		}
		for rows.Next() {
			var edgeType, sourceID, targetID string
			if err := rows.Scan(&edgeType, &sourceID, &targetID); err != nil {
				_ = rows.Close()
				return nil, nil, false, fmt.Errorf("scan typed edge for %s: %w", nodeID, err)
			}
			edgeType = strings.TrimSpace(edgeType)
			if edgeType != "" {
				edgeTypes[edgeType] = true
			}
			if sourceID != nodeID {
				addNode(sourceID)
			}
			if targetID != nodeID {
				addNode(targetID)
			}
		}
		if err := rows.Close(); err != nil {
			return nil, nil, false, fmt.Errorf("close typed edges for %s: %w", nodeID, err)
		}
	}
	nodeIDs := make([]string, 0, len(visited))
	for nodeID := range visited {
		nodeIDs = append(nodeIDs, nodeID)
	}
	types := make([]string, 0, len(edgeTypes))
	for edgeType := range edgeTypes {
		types = append(types, edgeType)
	}
	sort.Strings(nodeIDs)
	sort.Strings(types)
	return nodeIDs, types, truncated, nil
}
