package store

import (
	"context"
	"database/sql"
	"encoding/json"
	"fmt"
	"strings"
	"time"

	"github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/claim"
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
	Claims       []ClaimImport
	PathIndex    []PathIndexImport
	Aliases      []AliasImport
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

type ClaimImport struct {
	ID                       string
	NodeID                   string
	GraphClaimType           string
	Summary                  string
	State                    claim.State
	PriorState               claim.State
	Freshness                claim.Freshness
	StateReason              string
	SupportingEvidenceIDs    []string
	ContradictingEvidenceIDs []string
	Verifications            []ClaimVerificationImport
	Attrs                    map[string]any
}

type ClaimVerificationImport struct {
	ID         string
	Result     claim.VerificationResult
	Command    string
	EvidenceID string
	ObservedAt string
	Attrs      map[string]any
}

type PathIndexImport struct {
	ID         string
	Path       string
	NodeID     string
	Relation   string
	Confidence string
	EvidenceID string
}

type AliasImport struct {
	ID              string
	Alias           string
	NormalizedAlias string
	TargetType      string
	TargetID        string
	Language        string
	Source          string
	Confidence      string
	EvidenceID      string
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
	Evidence                    map[string]bool `json:"evidence"`
	Nodes                       map[string]bool `json:"nodes"`
	Edges                       map[string]bool `json:"edges"`
	Observations                map[string]bool `json:"observations"`
	Claims                      map[string]bool `json:"claims"`
	CoveragePaths               map[string]bool `json:"coverage_paths"`
	WorkflowUpdateEvidence      map[string]bool `json:"workflow_update_evidence"`
	WorkflowUpdateNodes         map[string]bool `json:"workflow_update_nodes"`
	WorkflowUpdateCoveragePaths map[string]bool `json:"workflow_update_coverage_paths"`
	Rejections                  []RowDecision   `json:"rejections"`
	MergeRecords                []MergeRecord   `json:"merge_records"`
}

func (s *Store) ImportGeneration(ctx context.Context, input ImportInput) (string, error) {
	input.GenerationID = strings.TrimSpace(input.GenerationID)
	if input.GenerationID == "" {
		return "", fmt.Errorf("generation id is required")
	}
	if input.Kind == "" {
		input.Kind = "full"
	}
	if err := validateImportReferences(input); err != nil {
		return "", err
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
	if err := supersedeAndDeleteActiveGenerationData(ctx, tx, input.GenerationID, now); err != nil {
		return "", err
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

	for _, graphClaim := range input.Claims {
		attrs, err := attrsJSONOrEmpty(graphClaim.Attrs)
		if err != nil {
			return "", fmt.Errorf("encode claim %s attrs: %w", graphClaim.ID, err)
		}
		if _, err := tx.ExecContext(ctx, `INSERT INTO claims(id, generation_id, node_id, graph_claim_type, summary, state, prior_state, freshness, state_reason, attrs_json, created_at, updated_at) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`, graphClaim.ID, input.GenerationID, graphClaim.NodeID, graphClaim.GraphClaimType, graphClaim.Summary, graphClaim.State, graphClaim.PriorState, graphClaim.Freshness, graphClaim.StateReason, attrs, now, now); err != nil {
			return "", fmt.Errorf("insert claim %s: %w", graphClaim.ID, err)
		}
		for _, evidenceID := range graphClaim.SupportingEvidenceIDs {
			if _, err := tx.ExecContext(ctx, `INSERT INTO claim_evidence(claim_id, evidence_id, role, reconciliation_id, basis_state) VALUES(?, ?, 'supporting', ?, 'current')`, graphClaim.ID, evidenceID, "build:"+input.GenerationID); err != nil {
				return "", fmt.Errorf("insert supporting claim evidence %s/%s: %w", graphClaim.ID, evidenceID, err)
			}
		}
		for _, evidenceID := range graphClaim.ContradictingEvidenceIDs {
			if _, err := tx.ExecContext(ctx, `INSERT INTO claim_evidence(claim_id, evidence_id, role, reconciliation_id, basis_state) VALUES(?, ?, 'contradicting', ?, 'current')`, graphClaim.ID, evidenceID, "build:"+input.GenerationID); err != nil {
				return "", fmt.Errorf("insert contradicting claim evidence %s/%s: %w", graphClaim.ID, evidenceID, err)
			}
		}
		for _, verification := range graphClaim.Verifications {
			verificationAttrs, err := attrsJSONOrEmpty(verification.Attrs)
			if err != nil {
				return "", fmt.Errorf("encode claim verification %s attrs: %w", verification.ID, err)
			}
			if _, err := tx.ExecContext(ctx, `INSERT INTO claim_verifications(id, claim_id, generation_id, result, command, evidence_id, observed_at, attrs_json) VALUES(?, ?, ?, ?, ?, ?, ?, ?)`, verification.ID, graphClaim.ID, input.GenerationID, verification.Result, verification.Command, verification.EvidenceID, verification.ObservedAt, verificationAttrs); err != nil {
				return "", fmt.Errorf("insert claim verification %s: %w", verification.ID, err)
			}
		}
		transitionID := "claim-transition:initial:" + graphClaim.ID
		if _, err := tx.ExecContext(ctx, `INSERT INTO claim_transitions(id, claim_id, generation_id, from_state, to_state, reason, evidence_id, occurred_at, attrs_json) VALUES(?, ?, ?, '', ?, ?, '', ?, '{}')`, transitionID, graphClaim.ID, input.GenerationID, graphClaim.State, graphClaim.StateReason, now); err != nil {
			return "", fmt.Errorf("insert initial claim transition %s: %w", graphClaim.ID, err)
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

	for _, alias := range input.Aliases {
		language := defaultString(alias.Language, "unknown")
		source := defaultString(alias.Source, "scan_alias")
		confidence := defaultString(alias.Confidence, "medium")
		if _, err := tx.ExecContext(ctx, `INSERT INTO alias_index(id, generation_id, alias, normalized_alias, target_type, target_id, language, source, confidence, evidence_id) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`, alias.ID, input.GenerationID, alias.Alias, alias.NormalizedAlias, alias.TargetType, alias.TargetID, language, source, confidence, alias.EvidenceID); err != nil {
			return "", fmt.Errorf("insert alias index %s: %w", alias.ID, err)
		}
	}

	if _, err := tx.ExecContext(ctx, `UPDATE generations SET state = 'active', published_at = ? WHERE id = ?`, now, input.GenerationID); err != nil {
		return "", fmt.Errorf("publish generation %s: %w", input.GenerationID, err)
	}
	if err := writeImportMetadata(ctx, tx, input.GenerationID, input.Kind, now); err != nil {
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
		Evidence:                    map[string]bool{},
		Nodes:                       map[string]bool{},
		Edges:                       map[string]bool{},
		Observations:                map[string]bool{},
		Claims:                      map[string]bool{},
		CoveragePaths:               map[string]bool{},
		WorkflowUpdateEvidence:      map[string]bool{},
		WorkflowUpdateNodes:         map[string]bool{},
		WorkflowUpdateCoveragePaths: map[string]bool{},
		Rejections:                  []RowDecision{},
		MergeRecords:                []MergeRecord{},
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
	if err := scanSnapshotRows(ctx, s.db, `SELECT id FROM claims WHERE generation_id = ?`, generationID, func(values []string) {
		snapshot.Claims[values[0]] = true
	}); err != nil {
		return snapshot, fmt.Errorf("read claim identities: %w", err)
	}
	if err := scanSnapshotRows(ctx, s.db, `SELECT path FROM path_index WHERE generation_id = ?`, generationID, func(values []string) {
		snapshot.CoveragePaths[values[0]] = true
	}); err != nil {
		return snapshot, fmt.Errorf("read coverage identities: %w", err)
	}
	if err := scanSnapshotRows(ctx, s.db, `SELECT e.id, e.source_path, e.content_hash, n.id, p.path FROM path_index p JOIN nodes n ON n.generation_id = p.generation_id AND n.id = p.node_id JOIN evidence e ON e.generation_id = p.generation_id AND e.id = p.evidence_id WHERE p.generation_id = ? AND n.type = 'workflow_update' AND e.source_kind = 'workflow_update' AND p.relation = 'provisional_path' AND p.confidence IN ('weak', 'partial')`, generationID, func(values []string) {
		snapshot.WorkflowUpdateEvidence[values[0]+"|"+values[1]+"|"+values[2]] = true
		snapshot.WorkflowUpdateNodes[values[3]] = true
		snapshot.WorkflowUpdateCoveragePaths[values[4]] = true
	}); err != nil {
		return snapshot, fmt.Errorf("read workflow update identities: %w", err)
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

func validateImportReferences(input ImportInput) error {
	evidenceIDs := map[string]bool{}
	for _, evidence := range input.Evidence {
		evidenceIDs[evidence.ID] = true
	}
	nodeIDs := map[string]bool{}
	for _, node := range input.Nodes {
		nodeIDs[node.ID] = true
		for _, evidenceID := range node.EvidenceIDs {
			if err := validateImportedEvidenceID("node", node.ID, evidenceID, evidenceIDs); err != nil {
				return err
			}
		}
	}
	for _, edge := range input.Edges {
		for _, evidenceID := range edge.EvidenceIDs {
			if err := validateImportedEvidenceID("edge", edge.ID, evidenceID, evidenceIDs); err != nil {
				return err
			}
		}
	}
	for _, observation := range input.Observations {
		for _, evidenceID := range observation.EvidenceIDs {
			if err := validateImportedEvidenceID("observation", observation.ID, evidenceID, evidenceIDs); err != nil {
				return err
			}
		}
	}
	for _, graphClaim := range input.Claims {
		if !nodeIDs[graphClaim.NodeID] {
			return fmt.Errorf("claim %s references missing node %s", graphClaim.ID, graphClaim.NodeID)
		}
		if strings.TrimSpace(graphClaim.GraphClaimType) == "" {
			return fmt.Errorf("claim %s graph_claim_type is required", graphClaim.ID)
		}
		for _, evidenceID := range append(append([]string{}, graphClaim.SupportingEvidenceIDs...), graphClaim.ContradictingEvidenceIDs...) {
			if err := validateImportedEvidenceID("claim", graphClaim.ID, evidenceID, evidenceIDs); err != nil {
				return err
			}
		}
		for _, verification := range graphClaim.Verifications {
			if strings.TrimSpace(verification.ID) == "" {
				return fmt.Errorf("claim %s verification id is required", graphClaim.ID)
			}
			if verification.EvidenceID != "" {
				if err := validateImportedEvidenceID("claim verification", verification.ID, verification.EvidenceID, evidenceIDs); err != nil {
					return err
				}
			}
		}
	}
	for _, pathIndex := range input.PathIndex {
		if !nodeIDs[pathIndex.NodeID] {
			return fmt.Errorf("path_index %s references missing node %s", pathIndex.ID, pathIndex.NodeID)
		}
		if pathIndex.EvidenceID != "" {
			if err := validateImportedEvidenceID("path_index", pathIndex.ID, pathIndex.EvidenceID, evidenceIDs); err != nil {
				return err
			}
		}
	}
	for _, alias := range input.Aliases {
		if strings.TrimSpace(alias.Alias) == "" {
			return fmt.Errorf("alias_index %s alias is required", alias.ID)
		}
		if strings.TrimSpace(alias.NormalizedAlias) == "" {
			return fmt.Errorf("alias_index %s normalized_alias is required", alias.ID)
		}
		if alias.TargetType != "node" {
			return fmt.Errorf("alias_index %s target_type %q is not supported", alias.ID, alias.TargetType)
		}
		if !nodeIDs[alias.TargetID] {
			return fmt.Errorf("alias_index %s references missing node %s", alias.ID, alias.TargetID)
		}
		if alias.EvidenceID != "" {
			if err := validateImportedEvidenceID("alias_index", alias.ID, alias.EvidenceID, evidenceIDs); err != nil {
				return err
			}
		}
	}
	return nil
}

func validateImportedEvidenceID(rowType, rowID, evidenceID string, evidenceIDs map[string]bool) error {
	if !evidenceIDs[evidenceID] {
		return fmt.Errorf("%s %s references missing evidence %s", rowType, rowID, evidenceID)
	}
	return nil
}

func defaultString(value string, fallback string) string {
	value = strings.TrimSpace(value)
	if value == "" {
		return fallback
	}
	return value
}

func supersedeAndDeleteActiveGenerationData(ctx context.Context, tx *sql.Tx, newGenerationID, now string) error {
	rows, err := tx.QueryContext(ctx, `SELECT id FROM generations WHERE state = 'active' AND id <> ?`, newGenerationID)
	if err != nil {
		return fmt.Errorf("read active generations for replacement: %w", err)
	}
	defer rows.Close()
	activeGenerationIDs := []string{}
	for rows.Next() {
		var generationID string
		if err := rows.Scan(&generationID); err != nil {
			return fmt.Errorf("scan active generation for replacement: %w", err)
		}
		activeGenerationIDs = append(activeGenerationIDs, generationID)
	}
	if err := rows.Err(); err != nil {
		return err
	}
	for _, generationID := range activeGenerationIDs {
		if err := deleteGenerationData(ctx, tx, generationID); err != nil {
			return err
		}
	}
	if _, err := tx.ExecContext(ctx, `UPDATE generations SET state = 'superseded', superseded_at = ? WHERE state = 'active' AND id <> ?`, now, newGenerationID); err != nil {
		return fmt.Errorf("supersede active generations: %w", err)
	}
	return nil
}

func deleteGenerationData(ctx context.Context, tx *sql.Tx, generationID string) error {
	statements := []string{
		`DELETE FROM claim_transitions WHERE generation_id = ?`,
		`DELETE FROM claim_verifications WHERE generation_id = ?`,
		`DELETE FROM claim_evidence WHERE claim_id IN (SELECT id FROM claims WHERE generation_id = ?)`,
		`DELETE FROM claims WHERE generation_id = ?`,
		`DELETE FROM observation_evidence WHERE observation_id IN (SELECT id FROM observations WHERE generation_id = ?)`,
		`DELETE FROM node_evidence WHERE node_id IN (SELECT id FROM nodes WHERE generation_id = ?)`,
		`DELETE FROM edge_evidence WHERE edge_id IN (SELECT id FROM edges WHERE generation_id = ?)`,
		`DELETE FROM alias_index WHERE generation_id = ?`,
		`DELETE FROM path_index WHERE generation_id = ?`,
		`DELETE FROM edges WHERE generation_id = ?`,
		`DELETE FROM observations WHERE generation_id = ?`,
		`DELETE FROM nodes WHERE generation_id = ?`,
		`DELETE FROM evidence WHERE generation_id = ?`,
	}
	for _, statement := range statements {
		if _, err := tx.ExecContext(ctx, statement, generationID); err != nil {
			return fmt.Errorf("delete generation data %s: %w", generationID, err)
		}
	}
	return nil
}

func writeImportMetadata(ctx context.Context, tx *sql.Tx, generationID, generationKind, now string) error {
	pairs := map[string]any{
		"runtime_format":       rt.RuntimeFormat,
		"runtime_schema":       rt.RuntimeSchema,
		"schema_version":       SchemaVersion,
		"active_generation_id": generationID,
		"graph_store_path":     ".specify/project-cognition/project-cognition.db",
		"graph_ready":          false,
		"baseline_state":       "building",
		"baseline_kind":        normalizeBaselineKind(generationKind),
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
