package store

import (
	"context"
	"database/sql"
	"encoding/json"
	"errors"
	"fmt"
	"strings"
	"time"

	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/scanartifacts"
)

type ScopedRegistrationInput struct {
	RegistrationID       string
	ExpectedGenerationID string
	PacketSHA256         string
	ParentUpdateID       string
	ParentIntentID       string
	ResultState          string
	Reason               string
	Package              scanartifacts.Package
	PathIndex            []PathIndexImport
	Aliases              []AliasImport
	Retirements          []ScopedRetirement
	ChangedPaths         []string
	NewClaimIDs          []string
	NegativeProbes       []ScopedNegativeProbe
	Attrs                map[string]any
	BeforeCommit         func() error
}

type ScopedRetirement struct {
	Kind   string
	ID     string
	Path   string
	Reason string
}

type ScopedNegativeProbe struct {
	Intent string
	Query  string
	Kind   string
}

type ScopedNegativeEvidence struct {
	Intent        string `json:"intent"`
	Query         string `json:"query"`
	Kind          string `json:"kind"`
	ObservedCount int    `json:"observed_count"`
	Status        string `json:"status"`
	Argv          string `json:"argv"`
}

type ScopedRegistrationResult struct {
	ActiveGenerationID string
	Registered         map[string][]string
	Retired            map[string][]string
	StaleClaims        []string
	NegativeQueries    []ScopedNegativeEvidence
}

func (s *Store) ApplyScopedRegistration(ctx context.Context, input ScopedRegistrationInput) (ScopedRegistrationResult, error) {
	result := ScopedRegistrationResult{
		Registered:      emptyScopedRegistered(),
		Retired:         map[string][]string{"aliases": []string{}, "paths": []string{}, "claims": []string{}},
		StaleClaims:     []string{},
		NegativeQueries: []ScopedNegativeEvidence{},
	}
	if strings.TrimSpace(input.RegistrationID) == "" {
		return result, fmt.Errorf("scoped registration id is required")
	}
	parentMode := strings.TrimSpace(input.ParentUpdateID) != "" || strings.TrimSpace(input.ParentIntentID) != ""
	if parentMode {
		if strings.TrimSpace(input.ParentUpdateID) == "" || strings.TrimSpace(input.ParentIntentID) == "" {
			return result, fmt.Errorf("parent update id and intent id are both required for parent scoped registration")
		}
		if strings.TrimSpace(input.RegistrationID) != strings.TrimSpace(input.ParentUpdateID) {
			return result, fmt.Errorf("parent scoped registration id %s must match parent update id %s", input.RegistrationID, input.ParentUpdateID)
		}
	}
	tx, err := s.db.BeginTx(ctx, nil)
	if err != nil {
		return result, fmt.Errorf("begin scoped registration: %w", err)
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
		return result, fmt.Errorf("project-cognition.db has no active generation")
	}
	if expected := strings.TrimSpace(input.ExpectedGenerationID); expected != "" && expected != generationID {
		return result, fmt.Errorf("active generation changed before scoped registration: got %s, want %s", generationID, expected)
	}
	if err := requireActiveGenerationStateTx(ctx, tx, generationID); err != nil {
		return result, err
	}
	result.ActiveGenerationID = generationID
	var parentAttrs map[string]any
	if parentMode {
		parentAttrs, err = validateParentScopedRegistrationTx(ctx, tx, generationID, input)
		if err != nil {
			return result, err
		}
	}
	if err := validateScopedActiveReferences(ctx, tx, generationID, input); err != nil {
		return result, err
	}
	now := time.Now().UTC().Format(time.RFC3339)
	if err := insertScopedPackageRowsTx(ctx, tx, generationID, input, now, result.Registered); err != nil {
		return result, err
	}
	retired, err := applyScopedRetirementsTx(ctx, tx, generationID, input.Retirements, now)
	if err != nil {
		return result, err
	}
	result.Retired = retired
	stale, err := markScopedAffectedClaimsStaleTx(ctx, tx, generationID, input.ChangedPaths, input.NewClaimIDs, input.Retirements, input.Reason, now)
	if err != nil {
		return result, err
	}
	result.StaleClaims = stale
	negative, err := runScopedNegativeProbesTx(ctx, tx, generationID, input.NegativeProbes)
	if err != nil {
		return result, err
	}
	result.NegativeQueries = negative
	if input.BeforeCommit != nil {
		if err := input.BeforeCommit(); err != nil {
			return result, fmt.Errorf("scoped registration before-commit guard: %w", err)
		}
	}
	attrs := scopedRegistrationAttrs(input.Attrs, result)
	if parentMode {
		merged := mergeParentScopedRegistrationAttrs(parentAttrs, attrs)
		storedAttrs, err := attrsJSONOrEmpty(merged)
		if err != nil {
			return result, fmt.Errorf("encode parent scoped registration attrs: %w", err)
		}
		updateResult, err := tx.ExecContext(ctx, `UPDATE updates SET attrs_json = ? WHERE generation_id = ? AND id = ?`, storedAttrs, generationID, strings.TrimSpace(input.ParentUpdateID))
		if err != nil {
			return result, fmt.Errorf("merge parent scoped registration %s: %w", input.ParentUpdateID, err)
		}
		if rows, _ := updateResult.RowsAffected(); rows != 1 {
			return result, fmt.Errorf("merge parent scoped registration %s affected %d rows", input.ParentUpdateID, rows)
		}
	} else if err := insertStructuredUpdateTx(ctx, tx, generationID, UpdateRecord{
		ID:             input.RegistrationID,
		Trigger:        "scoped-registration",
		ChangedPaths:   input.ChangedPaths,
		AffectedNodes:  registeredNodeIDs(result.Registered),
		AffectedClaims: result.StaleClaims,
		ResultState:    defaultScopedString(input.ResultState, "partial"),
		Attrs:          attrs,
	}, now); err != nil {
		return result, err
	}
	if err := tx.Commit(); err != nil {
		return result, fmt.Errorf("commit scoped registration: %w", err)
	}
	committed = true
	activeGenerationID, err := s.ActiveGenerationID(ctx)
	if err != nil {
		return result, err
	}
	if activeGenerationID != generationID {
		return result, fmt.Errorf("active generation changed after scoped registration: got %s, want %s", activeGenerationID, generationID)
	}
	return result, nil
}

func (s *Store) UpdateScopedRegistrationReceipt(ctx context.Context, generationID, registrationID, packetSHA string, attrs map[string]any) error {
	if strings.TrimSpace(generationID) == "" || strings.TrimSpace(registrationID) == "" {
		return fmt.Errorf("generation id and registration id are required")
	}
	var existingRaw string
	err := s.db.QueryRowContext(ctx, `SELECT attrs_json FROM updates WHERE generation_id = ? AND id = ?`, generationID, registrationID).Scan(&existingRaw)
	if errors.Is(err, sql.ErrNoRows) {
		return fmt.Errorf("update scoped registration receipt %s affected 0 rows", registrationID)
	}
	if err != nil {
		return fmt.Errorf("read scoped registration receipt %s: %w", registrationID, err)
	}
	existing, err := decodeAttrsObject(existingRaw)
	if err != nil {
		return fmt.Errorf("decode scoped registration receipt %s attrs: %w", registrationID, err)
	}
	storedAttrs := attrs
	if scoped, ok := existing["scoped_registration"].(map[string]any); ok {
		if strings.TrimSpace(stringValue(scoped["packet_sha256"])) != packetSHA {
			return fmt.Errorf("update scoped registration receipt %s packet mismatch", registrationID)
		}
		mergedScoped := cloneStringAnyMap(scoped)
		for key, value := range scopedRegistrationAttrs(attrs, nil) {
			mergedScoped[key] = value
		}
		storedMap := cloneStringAnyMap(existing)
		storedMap["scoped_registration"] = mergedScoped
		storedAttrs = storedMap
	} else if strings.TrimSpace(stringValue(existing["packet_sha256"])) != packetSHA {
		return fmt.Errorf("update scoped registration receipt %s packet mismatch", registrationID)
	}
	encoded, err := attrsJSONOrEmpty(storedAttrs)
	if err != nil {
		return err
	}
	result, err := s.db.ExecContext(ctx, `UPDATE updates SET attrs_json = ? WHERE generation_id = ? AND id = ?`, encoded, generationID, registrationID)
	if err != nil {
		return fmt.Errorf("update scoped registration receipt %s: %w", registrationID, err)
	}
	if rows, _ := result.RowsAffected(); rows != 1 {
		return fmt.Errorf("update scoped registration receipt %s affected %d rows", registrationID, rows)
	}
	return nil
}

func scopedRegistrationAttrs(attrs map[string]any, result any) map[string]any {
	out := cloneStringAnyMap(attrs)
	if result != nil {
		out["scoped_registration_result"] = result
	}
	return out
}

func scopedRowAttrs(attrs map[string]any, input ScopedRegistrationInput) map[string]any {
	out := cloneStringAnyMap(attrs)
	out["scoped_registration_registration_id"] = strings.TrimSpace(input.RegistrationID)
	out["scoped_registration_packet_sha256"] = strings.TrimSpace(input.PacketSHA256)
	out["scoped_registration_owned"] = true
	if owner := scopedRegistrationOwnerKey(input); owner != "" {
		out["scoped_registration_owner_key"] = owner
	}
	return out
}

func scopedRegistrationOwnerKey(input ScopedRegistrationInput) string {
	if strings.TrimSpace(input.ParentUpdateID) != "" || strings.TrimSpace(input.ParentIntentID) != "" {
		return "parent:" + strings.TrimSpace(input.ParentUpdateID) + ":" + strings.TrimSpace(input.ParentIntentID)
	}
	proof := map[string]any{}
	if rawProof, ok := input.Attrs["native_proof"]; ok && rawProof != nil {
		if mapped, ok := rawProof.(map[string]any); ok {
			proof = mapped
		} else if encoded, err := json.Marshal(rawProof); err == nil {
			decoder := json.NewDecoder(strings.NewReader(string(encoded)))
			decoder.UseNumber()
			_ = decoder.Decode(&proof)
		}
	}
	if len(proof) == 0 {
		return ""
	}
	parts := []string{
		stringValue(proof["kind"]),
		stringValue(proof["workflow"]),
		stringValue(proof["scope"]),
		stringValue(proof["do_ref"]),
		stringValue(proof["work_id"]),
		stringValue(proof["parent_update_id"]),
		stringValue(proof["parent_intent_id"]),
	}
	return strings.Join(uniqueSorted(trimEmptyStrings(parts)), "|")
}

func trimEmptyStrings(values []string) []string {
	out := []string{}
	for _, value := range values {
		if strings.TrimSpace(value) != "" {
			out = append(out, strings.TrimSpace(value))
		}
	}
	return out
}

func requireScopedRowReplacement(attrsRaw, id, kind string, input ScopedRegistrationInput) (map[string]any, error) {
	attrs, err := decodeAttrsObject(attrsRaw)
	if err != nil {
		return nil, fmt.Errorf("decode existing scoped %s %s attrs: %w", kind, id, err)
	}
	priorOwner := strings.TrimSpace(stringValue(attrs["scoped_registration_owner_key"]))
	currentOwner := scopedRegistrationOwnerKey(input)
	if strings.TrimSpace(stringValue(attrs["scoped_registration_registration_id"])) == "" || strings.TrimSpace(stringValue(attrs["scoped_registration_packet_sha256"])) == "" || priorOwner == "" {
		return nil, fmt.Errorf("scoped %s %s conflicts with unrelated active %s", kind, id, kind)
	}
	if currentOwner == "" || currentOwner != priorOwner {
		return nil, fmt.Errorf("scoped %s %s conflicts with a different scoped registration owner", kind, id)
	}
	return attrs, nil
}

func validateParentScopedRegistrationTx(ctx context.Context, tx *sql.Tx, generationID string, input ScopedRegistrationInput) (map[string]any, error) {
	var attrsRaw string
	err := tx.QueryRowContext(ctx, `SELECT attrs_json FROM updates WHERE generation_id = ? AND id = ?`, generationID, strings.TrimSpace(input.ParentUpdateID)).Scan(&attrsRaw)
	if errors.Is(err, sql.ErrNoRows) {
		return nil, fmt.Errorf("parent update %s is missing for scoped registration", input.ParentUpdateID)
	}
	if err != nil {
		return nil, fmt.Errorf("read parent update %s: %w", input.ParentUpdateID, err)
	}
	attrs, err := decodeAttrsObject(attrsRaw)
	if err != nil {
		return nil, fmt.Errorf("decode parent update %s attrs: %w", input.ParentUpdateID, err)
	}
	if got := strings.TrimSpace(stringValue(attrs["closeout_intent_id"])); got != strings.TrimSpace(input.ParentIntentID) {
		return nil, fmt.Errorf("parent update %s closeout_intent_id mismatch: got %q want %q", input.ParentUpdateID, got, strings.TrimSpace(input.ParentIntentID))
	}
	if scoped, ok := attrs["scoped_registration"].(map[string]any); ok {
		if got := strings.TrimSpace(stringValue(scoped["packet_sha256"])); got != "" && got != strings.TrimSpace(input.PacketSHA256) {
			return nil, fmt.Errorf("parent update %s already has a different scoped registration packet", input.ParentUpdateID)
		}
	}
	return attrs, nil
}

func mergeParentScopedRegistrationAttrs(parentAttrs, scopedAttrs map[string]any) map[string]any {
	out := cloneStringAnyMap(parentAttrs)
	out["scoped_registration"] = cloneStringAnyMap(scopedAttrs)
	return out
}

func decodeAttrsObject(raw string) (map[string]any, error) {
	out := map[string]any{}
	if strings.TrimSpace(raw) == "" {
		return out, nil
	}
	decoder := json.NewDecoder(strings.NewReader(raw))
	decoder.UseNumber()
	if err := decoder.Decode(&out); err != nil {
		return nil, err
	}
	return out, nil
}

func stringValue(value any) string {
	switch v := value.(type) {
	case string:
		return v
	case json.Number:
		return v.String()
	case fmt.Stringer:
		return v.String()
	default:
		return ""
	}
}

func requireActiveGenerationStateTx(ctx context.Context, tx *sql.Tx, generationID string) error {
	var state string
	err := tx.QueryRowContext(ctx, `SELECT state FROM generations WHERE id = ?`, generationID).Scan(&state)
	if errors.Is(err, sql.ErrNoRows) {
		return fmt.Errorf("active generation %s is missing", generationID)
	}
	if err != nil {
		return fmt.Errorf("read active generation %s: %w", generationID, err)
	}
	if state != "active" {
		return fmt.Errorf("generation %s is %s, not active", generationID, state)
	}
	return nil
}

func validateScopedActiveReferences(ctx context.Context, tx *sql.Tx, generationID string, input ScopedRegistrationInput) error {
	evidenceIDs := map[string]bool{}
	nodeIDs := map[string]bool{}
	for _, row := range input.Package.Evidence {
		evidenceIDs[row.ID] = true
	}
	for _, row := range input.Package.Nodes {
		nodeIDs[row.ID] = true
	}
	activeEvidence, err := scopedActiveIDs(ctx, tx, generationID, "evidence")
	if err != nil {
		return err
	}
	for _, id := range activeEvidence {
		evidenceIDs[id] = true
	}
	activeNodes, err := scopedActiveIDs(ctx, tx, generationID, "nodes")
	if err != nil {
		return err
	}
	for _, id := range activeNodes {
		nodeIDs[id] = true
	}
	for _, row := range input.PathIndex {
		if !nodeIDs[row.NodeID] {
			return fmt.Errorf("path_index %s references missing node %s", row.ID, row.NodeID)
		}
		if row.EvidenceID != "" && !evidenceIDs[row.EvidenceID] {
			return fmt.Errorf("path_index %s references missing evidence %s", row.ID, row.EvidenceID)
		}
	}
	for _, row := range input.Aliases {
		if row.TargetType != "" && row.TargetType != "node" {
			return fmt.Errorf("alias %s target_type must be node", row.ID)
		}
		if !nodeIDs[row.TargetID] {
			return fmt.Errorf("alias %s references missing node %s", row.ID, row.TargetID)
		}
		if row.EvidenceID != "" && !evidenceIDs[row.EvidenceID] {
			return fmt.Errorf("alias %s references missing evidence %s", row.ID, row.EvidenceID)
		}
	}
	return nil
}

func scopedActiveIDs(ctx context.Context, tx *sql.Tx, generationID, table string) ([]string, error) {
	if table != "evidence" && table != "nodes" {
		return nil, fmt.Errorf("unsupported scoped active id table %q", table)
	}
	rows, err := tx.QueryContext(ctx, `SELECT id FROM `+table+` WHERE generation_id = ?`, generationID)
	if err != nil {
		return nil, fmt.Errorf("read active %s ids: %w", table, err)
	}
	defer rows.Close()
	out := []string{}
	for rows.Next() {
		var id string
		if err := rows.Scan(&id); err != nil {
			return nil, fmt.Errorf("scan active %s id: %w", table, err)
		}
		out = append(out, id)
	}
	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("iterate active %s ids: %w", table, err)
	}
	return out, nil
}

func insertScopedPackageRowsTx(ctx context.Context, tx *sql.Tx, generationID string, input ScopedRegistrationInput, now string, registered map[string][]string) error {
	pkg := input.Package
	paths := input.PathIndex
	aliases := input.Aliases
	for _, row := range pkg.Evidence {
		attrs, err := attrsJSONOrEmpty(scopedRowAttrs(row.Attrs, input))
		if err != nil {
			return err
		}
		if err := upsertScopedEvidenceTx(ctx, tx, generationID, input, row, attrs, now); err != nil {
			return err
		}
		registered["evidence"] = append(registered["evidence"], row.ID)
	}
	for _, row := range pkg.Nodes {
		attrs, err := attrsJSONOrEmpty(scopedRowAttrs(row.Attrs, input))
		if err != nil {
			return err
		}
		replaced, err := replaceParentScopedPlaceholderNodeTx(ctx, tx, generationID, strings.TrimSpace(input.ParentUpdateID), row, attrs, now)
		if err != nil {
			return err
		}
		if !replaced {
			if err := upsertScopedNodeTx(ctx, tx, generationID, input, row, attrs, now); err != nil {
				return err
			}
		}
		if err := deleteScopedLinksTx(ctx, tx, "node_evidence", "node_id", row.ID); err != nil {
			return err
		}
		for _, evidenceID := range row.EvidenceIDs {
			if _, err := tx.ExecContext(ctx, `INSERT INTO node_evidence(node_id, evidence_id) VALUES(?, ?)`, row.ID, evidenceID); err != nil {
				return fmt.Errorf("insert scoped node evidence %s/%s: %w", row.ID, evidenceID, err)
			}
		}
		registered["nodes"] = append(registered["nodes"], row.ID)
	}
	for _, row := range pkg.Edges {
		attrs, err := attrsJSONOrEmpty(scopedRowAttrs(row.Attrs, input))
		if err != nil {
			return err
		}
		if err := upsertScopedEdgeTx(ctx, tx, generationID, input, row, attrs, now); err != nil {
			return err
		}
		if err := deleteScopedLinksTx(ctx, tx, "edge_evidence", "edge_id", row.ID); err != nil {
			return err
		}
		for _, evidenceID := range row.EvidenceIDs {
			if _, err := tx.ExecContext(ctx, `INSERT INTO edge_evidence(edge_id, evidence_id) VALUES(?, ?)`, row.ID, evidenceID); err != nil {
				return fmt.Errorf("insert scoped edge evidence %s/%s: %w", row.ID, evidenceID, err)
			}
		}
		registered["edges"] = append(registered["edges"], row.ID)
	}
	for _, row := range pkg.Observations {
		attrs, err := attrsJSONOrEmpty(scopedRowAttrs(row.Attrs, input))
		if err != nil {
			return err
		}
		if err := upsertScopedObservationTx(ctx, tx, generationID, input, row, attrs, now); err != nil {
			return err
		}
		if err := deleteScopedLinksTx(ctx, tx, "observation_evidence", "observation_id", row.ID); err != nil {
			return err
		}
		for _, evidenceID := range row.EvidenceIDs {
			if _, err := tx.ExecContext(ctx, `INSERT INTO observation_evidence(observation_id, evidence_id) VALUES(?, ?)`, row.ID, evidenceID); err != nil {
				return fmt.Errorf("insert scoped observation evidence %s/%s: %w", row.ID, evidenceID, err)
			}
		}
		registered["observations"] = append(registered["observations"], row.ID)
	}
	for _, row := range pkg.Claims {
		attrs, err := attrsJSONOrEmpty(scopedRowAttrs(row.Attrs, input))
		if err != nil {
			return err
		}
		if err := upsertScopedClaimTx(ctx, tx, generationID, input, row, attrs, now); err != nil {
			return err
		}
		if err := deleteScopedLinksTx(ctx, tx, "claim_evidence", "claim_id", row.ID); err != nil {
			return err
		}
		if err := deleteScopedLinksTx(ctx, tx, "claim_verifications", "claim_id", row.ID); err != nil {
			return err
		}
		for _, evidenceID := range row.SupportingEvidenceIDs {
			if _, err := tx.ExecContext(ctx, `INSERT INTO claim_evidence(claim_id, evidence_id, role) VALUES(?, ?, 'supporting')`, row.ID, evidenceID); err != nil {
				return fmt.Errorf("insert scoped claim evidence %s/%s: %w", row.ID, evidenceID, err)
			}
		}
		for _, evidenceID := range row.ContradictingEvidenceIDs {
			if _, err := tx.ExecContext(ctx, `INSERT INTO claim_evidence(claim_id, evidence_id, role) VALUES(?, ?, 'contradicting')`, row.ID, evidenceID); err != nil {
				return fmt.Errorf("insert scoped claim contradicting evidence %s/%s: %w", row.ID, evidenceID, err)
			}
		}
		for _, verification := range row.Verifications {
			attrs, err := attrsJSONOrEmpty(verification.Attrs)
			if err != nil {
				return err
			}
			if _, err := tx.ExecContext(ctx, `INSERT INTO claim_verifications(id, claim_id, generation_id, result, command, evidence_id, observed_at, attrs_json) VALUES(?, ?, ?, ?, ?, ?, ?, ?)`, verification.ID, row.ID, generationID, verification.Result, verification.Command, verification.EvidenceID, verification.ObservedAt, attrs); err != nil {
				return fmt.Errorf("insert scoped claim verification %s: %w", verification.ID, err)
			}
		}
		transitionID := "claim-transition:scoped:" + stableScopedPart(input.RegistrationID+":"+row.ID)
		if _, err := tx.ExecContext(ctx, `INSERT INTO claim_transitions(id, claim_id, generation_id, from_state, to_state, reason, evidence_id, occurred_at, attrs_json) VALUES(?, ?, ?, '', ?, ?, '', ?, '{}')`, transitionID, row.ID, generationID, row.State, row.StateReason, now); err != nil {
			return fmt.Errorf("insert scoped claim transition %s: %w", transitionID, err)
		}
		registered["claims"] = append(registered["claims"], row.ID)
	}
	for _, row := range paths {
		if strings.TrimSpace(input.ParentUpdateID) != "" {
			if err := deleteParentScopedPlaceholderPathTx(ctx, tx, generationID, strings.TrimSpace(input.ParentUpdateID), row); err != nil {
				return err
			}
		}
		id := strings.TrimSpace(row.ID)
		if id == "" {
			id = "P-scoped-" + stableScopedPart(generationID+"-"+row.Path+"-"+row.NodeID)
		}
		if err := upsertScopedPathIndexTx(ctx, tx, generationID, input, id, row, now); err != nil {
			return err
		}
		registered["path_index"] = append(registered["path_index"], id)
	}
	for _, row := range aliases {
		id := strings.TrimSpace(row.ID)
		if id == "" {
			id = "A-scoped-" + stableScopedPart(generationID+"-"+row.TargetID+"-"+row.NormalizedAlias+"-"+row.Source)
		}
		normalized := strings.TrimSpace(row.NormalizedAlias)
		if normalized == "" {
			normalized = normalizeWorkflowAlias(row.Alias)
		}
		if err := upsertScopedAliasTx(ctx, tx, generationID, input, id, row, normalized); err != nil {
			return err
		}
		registered["aliases"] = append(registered["aliases"], id)
	}
	return nil
}

func upsertScopedEvidenceTx(ctx context.Context, tx *sql.Tx, generationID string, input ScopedRegistrationInput, row scanartifacts.EvidenceRow, attrs string, now string) error {
	var existingAttrs, existingSourcePath string
	err := tx.QueryRowContext(ctx, `SELECT attrs_json, source_path FROM evidence WHERE generation_id = ? AND id = ?`, generationID, row.ID).Scan(&existingAttrs, &existingSourcePath)
	if errors.Is(err, sql.ErrNoRows) {
		if _, err := tx.ExecContext(ctx, `INSERT INTO evidence(id, generation_id, source_kind, source_path, commit_sha, span, extractor, content_hash, captured_at, attrs_json) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`, row.ID, generationID, row.SourceKind, row.SourcePath, row.CommitSHA, row.Span, row.Extractor, row.ContentHash, now, attrs); err != nil {
			return fmt.Errorf("insert scoped evidence %s: %w", row.ID, err)
		}
		return nil
	}
	if err != nil {
		return fmt.Errorf("read scoped evidence %s: %w", row.ID, err)
	}
	if _, err := requireScopedRowReplacement(existingAttrs, row.ID, "evidence", input); err != nil {
		return err
	}
	if normalizeScopedPath(existingSourcePath) != normalizeScopedPath(row.SourcePath) {
		return fmt.Errorf("scoped evidence %s conflicts with a different source path", row.ID)
	}
	result, err := tx.ExecContext(ctx, `UPDATE evidence SET source_kind = ?, source_path = ?, commit_sha = ?, span = ?, extractor = ?, content_hash = ?, captured_at = ?, attrs_json = ? WHERE generation_id = ? AND id = ?`, row.SourceKind, row.SourcePath, row.CommitSHA, row.Span, row.Extractor, row.ContentHash, now, attrs, generationID, row.ID)
	if err != nil {
		return fmt.Errorf("replace scoped evidence %s: %w", row.ID, err)
	}
	if rows, _ := result.RowsAffected(); rows != 1 {
		return fmt.Errorf("replace scoped evidence %s affected %d rows", row.ID, rows)
	}
	return nil
}

func upsertScopedNodeTx(ctx context.Context, tx *sql.Tx, generationID string, input ScopedRegistrationInput, row scanartifacts.NodeRow, attrs string, now string) error {
	var existingAttrs string
	err := tx.QueryRowContext(ctx, `SELECT attrs_json FROM nodes WHERE generation_id = ? AND id = ?`, generationID, row.ID).Scan(&existingAttrs)
	if errors.Is(err, sql.ErrNoRows) {
		if _, err := tx.ExecContext(ctx, `INSERT INTO nodes(id, generation_id, type, title, confidence, attrs_json, created_at, updated_at) VALUES(?, ?, ?, ?, ?, ?, ?, ?)`, row.ID, generationID, row.Type, row.Title, row.Confidence, attrs, now, now); err != nil {
			return fmt.Errorf("insert scoped node %s: %w", row.ID, err)
		}
		return nil
	}
	if err != nil {
		return fmt.Errorf("read scoped node %s: %w", row.ID, err)
	}
	if _, err := requireScopedRowReplacement(existingAttrs, row.ID, "node", input); err != nil {
		return err
	}
	result, err := tx.ExecContext(ctx, `UPDATE nodes SET type = ?, title = ?, confidence = ?, attrs_json = ?, updated_at = ? WHERE generation_id = ? AND id = ?`, row.Type, row.Title, row.Confidence, attrs, now, generationID, row.ID)
	if err != nil {
		return fmt.Errorf("replace scoped node %s: %w", row.ID, err)
	}
	if rows, _ := result.RowsAffected(); rows != 1 {
		return fmt.Errorf("replace scoped node %s affected %d rows", row.ID, rows)
	}
	return nil
}

func upsertScopedEdgeTx(ctx context.Context, tx *sql.Tx, generationID string, input ScopedRegistrationInput, row scanartifacts.EdgeRow, attrs string, now string) error {
	var existingAttrs string
	err := tx.QueryRowContext(ctx, `SELECT attrs_json FROM edges WHERE generation_id = ? AND id = ?`, generationID, row.ID).Scan(&existingAttrs)
	if errors.Is(err, sql.ErrNoRows) {
		if _, err := tx.ExecContext(ctx, `INSERT INTO edges(id, generation_id, type, source_id, target_id, confidence, attrs_json, created_at, updated_at) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)`, row.ID, generationID, row.Type, row.SourceID, row.TargetID, row.Confidence, attrs, now, now); err != nil {
			return fmt.Errorf("insert scoped edge %s: %w", row.ID, err)
		}
		return nil
	}
	if err != nil {
		return fmt.Errorf("read scoped edge %s: %w", row.ID, err)
	}
	if _, err := requireScopedRowReplacement(existingAttrs, row.ID, "edge", input); err != nil {
		return err
	}
	result, err := tx.ExecContext(ctx, `UPDATE edges SET type = ?, source_id = ?, target_id = ?, confidence = ?, attrs_json = ?, updated_at = ? WHERE generation_id = ? AND id = ?`, row.Type, row.SourceID, row.TargetID, row.Confidence, attrs, now, generationID, row.ID)
	if err != nil {
		return fmt.Errorf("replace scoped edge %s: %w", row.ID, err)
	}
	if rows, _ := result.RowsAffected(); rows != 1 {
		return fmt.Errorf("replace scoped edge %s affected %d rows", row.ID, rows)
	}
	return nil
}

func upsertScopedObservationTx(ctx context.Context, tx *sql.Tx, generationID string, input ScopedRegistrationInput, row scanartifacts.ObservationRow, attrs string, now string) error {
	var existingAttrs string
	err := tx.QueryRowContext(ctx, `SELECT attrs_json FROM observations WHERE generation_id = ? AND id = ?`, generationID, row.ID).Scan(&existingAttrs)
	if errors.Is(err, sql.ErrNoRows) {
		if _, err := tx.ExecContext(ctx, `INSERT INTO observations(id, generation_id, observation_type, summary, attrs_json, created_at, updated_at) VALUES(?, ?, ?, ?, ?, ?, ?)`, row.ID, generationID, row.ObservationType, row.Summary, attrs, now, now); err != nil {
			return fmt.Errorf("insert scoped observation %s: %w", row.ID, err)
		}
		return nil
	}
	if err != nil {
		return fmt.Errorf("read scoped observation %s: %w", row.ID, err)
	}
	if _, err := requireScopedRowReplacement(existingAttrs, row.ID, "observation", input); err != nil {
		return err
	}
	result, err := tx.ExecContext(ctx, `UPDATE observations SET observation_type = ?, summary = ?, attrs_json = ?, updated_at = ? WHERE generation_id = ? AND id = ?`, row.ObservationType, row.Summary, attrs, now, generationID, row.ID)
	if err != nil {
		return fmt.Errorf("replace scoped observation %s: %w", row.ID, err)
	}
	if rows, _ := result.RowsAffected(); rows != 1 {
		return fmt.Errorf("replace scoped observation %s affected %d rows", row.ID, rows)
	}
	return nil
}

func upsertScopedClaimTx(ctx context.Context, tx *sql.Tx, generationID string, input ScopedRegistrationInput, row scanartifacts.ClaimRow, attrs string, now string) error {
	var existingAttrs, existingState string
	err := tx.QueryRowContext(ctx, `SELECT attrs_json, state FROM claims WHERE generation_id = ? AND id = ?`, generationID, row.ID).Scan(&existingAttrs, &existingState)
	if errors.Is(err, sql.ErrNoRows) {
		if _, err := tx.ExecContext(ctx, `INSERT INTO claims(id, generation_id, node_id, graph_claim_type, summary, state, prior_state, freshness, state_reason, attrs_json, created_at, updated_at) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`, row.ID, generationID, row.NodeID, row.GraphClaimType, row.Summary, row.State, row.PriorState, row.Freshness, row.StateReason, attrs, now, now); err != nil {
			return fmt.Errorf("insert scoped claim %s: %w", row.ID, err)
		}
		return nil
	}
	if err != nil {
		return fmt.Errorf("read scoped claim %s: %w", row.ID, err)
	}
	existing, err := requireScopedRowReplacement(existingAttrs, row.ID, "claim", input)
	if err != nil {
		return err
	}
	priorRegistration := strings.TrimSpace(stringValue(existing["scoped_registration_registration_id"]))
	staleTransitionID := "claim-transition:scoped-replace:" + stableScopedPart(priorRegistration+":"+input.RegistrationID+":"+row.ID)
	if _, err := tx.ExecContext(ctx, `INSERT INTO claim_transitions(id, claim_id, generation_id, from_state, to_state, reason, evidence_id, occurred_at, attrs_json) VALUES(?, ?, ?, ?, 'stale', ?, '', ?, '{}')`, staleTransitionID, row.ID, generationID, existingState, "scoped registration successor "+input.RegistrationID, now); err != nil {
		return fmt.Errorf("record scoped claim %s predecessor stale transition: %w", row.ID, err)
	}
	result, err := tx.ExecContext(ctx, `UPDATE claims SET node_id = ?, graph_claim_type = ?, summary = ?, state = ?, prior_state = ?, freshness = ?, state_reason = ?, attrs_json = ?, revision = revision + 1, updated_at = ? WHERE generation_id = ? AND id = ?`, row.NodeID, row.GraphClaimType, row.Summary, row.State, row.PriorState, row.Freshness, row.StateReason, attrs, now, generationID, row.ID)
	if err != nil {
		return fmt.Errorf("replace scoped claim %s: %w", row.ID, err)
	}
	if rows, _ := result.RowsAffected(); rows != 1 {
		return fmt.Errorf("replace scoped claim %s affected %d rows", row.ID, rows)
	}
	return nil
}

func deleteScopedLinksTx(ctx context.Context, tx *sql.Tx, table, column, id string) error {
	switch table {
	case "node_evidence", "edge_evidence", "observation_evidence", "claim_evidence", "claim_verifications":
	default:
		return fmt.Errorf("unsupported scoped link table %s", table)
	}
	if column != "node_id" && column != "edge_id" && column != "observation_id" && column != "claim_id" {
		return fmt.Errorf("unsupported scoped link column %s", column)
	}
	if _, err := tx.ExecContext(ctx, `DELETE FROM `+table+` WHERE `+column+` = ?`, id); err != nil {
		return fmt.Errorf("delete scoped replacement links for %s %s: %w", table, id, err)
	}
	return nil
}

func upsertScopedPathIndexTx(ctx context.Context, tx *sql.Tx, generationID string, input ScopedRegistrationInput, id string, row PathIndexImport, now string) error {
	var existingEvidence string
	err := tx.QueryRowContext(ctx, `SELECT evidence_id FROM path_index WHERE generation_id = ? AND id = ?`, generationID, id).Scan(&existingEvidence)
	if errors.Is(err, sql.ErrNoRows) {
		if _, err := tx.ExecContext(ctx, `INSERT INTO path_index(id, generation_id, path, node_id, relation, confidence, evidence_id, updated_at) VALUES(?, ?, ?, ?, ?, ?, ?, ?)`, id, generationID, normalizeScopedPath(row.Path), row.NodeID, defaultScopedString(row.Relation, "owns"), defaultScopedString(row.Confidence, "partial"), row.EvidenceID, now); err != nil {
			return fmt.Errorf("insert scoped path index %s: %w", id, err)
		}
		return nil
	}
	if err != nil {
		return fmt.Errorf("read scoped path index %s: %w", id, err)
	}
	if err := requireScopedEvidenceProvenanceTx(ctx, tx, generationID, existingEvidence, "path_index", id, input); err != nil {
		return err
	}
	result, err := tx.ExecContext(ctx, `UPDATE path_index SET path = ?, node_id = ?, relation = ?, confidence = ?, evidence_id = ?, updated_at = ? WHERE generation_id = ? AND id = ?`, normalizeScopedPath(row.Path), row.NodeID, defaultScopedString(row.Relation, "owns"), defaultScopedString(row.Confidence, "partial"), row.EvidenceID, now, generationID, id)
	if err != nil {
		return fmt.Errorf("replace scoped path index %s: %w", id, err)
	}
	if rows, _ := result.RowsAffected(); rows != 1 {
		return fmt.Errorf("replace scoped path index %s affected %d rows", id, rows)
	}
	return nil
}

func upsertScopedAliasTx(ctx context.Context, tx *sql.Tx, generationID string, input ScopedRegistrationInput, id string, row AliasImport, normalized string) error {
	var existingEvidence string
	err := tx.QueryRowContext(ctx, `SELECT evidence_id FROM alias_index WHERE generation_id = ? AND id = ?`, generationID, id).Scan(&existingEvidence)
	if errors.Is(err, sql.ErrNoRows) {
		if _, err := tx.ExecContext(ctx, `INSERT INTO alias_index(id, generation_id, alias, normalized_alias, target_type, target_id, language, source, confidence, evidence_id) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`, id, generationID, row.Alias, normalized, defaultScopedString(row.TargetType, "node"), row.TargetID, defaultScopedString(row.Language, "unknown"), defaultScopedString(row.Source, "scoped_registration"), defaultScopedString(row.Confidence, "partial"), row.EvidenceID); err != nil {
			return fmt.Errorf("insert scoped alias %s: %w", id, err)
		}
		return nil
	}
	if err != nil {
		return fmt.Errorf("read scoped alias %s: %w", id, err)
	}
	if err := requireScopedEvidenceProvenanceTx(ctx, tx, generationID, existingEvidence, "alias", id, input); err != nil {
		return err
	}
	result, err := tx.ExecContext(ctx, `UPDATE alias_index SET alias = ?, normalized_alias = ?, target_type = ?, target_id = ?, language = ?, source = ?, confidence = ?, evidence_id = ? WHERE generation_id = ? AND id = ?`, row.Alias, normalized, defaultScopedString(row.TargetType, "node"), row.TargetID, defaultScopedString(row.Language, "unknown"), defaultScopedString(row.Source, "scoped_registration"), defaultScopedString(row.Confidence, "partial"), row.EvidenceID, generationID, id)
	if err != nil {
		return fmt.Errorf("replace scoped alias %s: %w", id, err)
	}
	if rows, _ := result.RowsAffected(); rows != 1 {
		return fmt.Errorf("replace scoped alias %s affected %d rows", id, rows)
	}
	return nil
}

func requireScopedEvidenceProvenanceTx(ctx context.Context, tx *sql.Tx, generationID, evidenceID, kind, id string, input ScopedRegistrationInput) error {
	var attrsRaw string
	err := tx.QueryRowContext(ctx, `SELECT attrs_json FROM evidence WHERE generation_id = ? AND id = ?`, generationID, evidenceID).Scan(&attrsRaw)
	if err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			return fmt.Errorf("scoped %s %s conflicts with missing predecessor evidence %s", kind, id, evidenceID)
		}
		return fmt.Errorf("read scoped %s %s predecessor evidence %s: %w", kind, id, evidenceID, err)
	}
	_, err = requireScopedRowReplacement(attrsRaw, id, kind, input)
	return err
}

func replaceParentScopedPlaceholderNodeTx(ctx context.Context, tx *sql.Tx, generationID, parentUpdateID string, row scanartifacts.NodeRow, attrs string, now string) (bool, error) {
	if parentUpdateID == "" {
		return false, nil
	}
	var existingType, existingAttrs string
	err := tx.QueryRowContext(ctx, `SELECT type, attrs_json FROM nodes WHERE generation_id = ? AND id = ?`, generationID, row.ID).Scan(&existingType, &existingAttrs)
	if errors.Is(err, sql.ErrNoRows) {
		return false, nil
	}
	if err != nil {
		return false, fmt.Errorf("read parent scoped placeholder node %s: %w", row.ID, err)
	}
	decoded, err := decodeAttrsObject(existingAttrs)
	if err != nil {
		return false, fmt.Errorf("decode parent scoped placeholder node %s attrs: %w", row.ID, err)
	}
	if existingType != "workflow_update" || strings.TrimSpace(stringValue(decoded["update_id"])) != parentUpdateID {
		return false, fmt.Errorf("scoped node %s conflicts with unrelated active node", row.ID)
	}
	result, err := tx.ExecContext(ctx, `UPDATE nodes SET type = ?, title = ?, confidence = ?, attrs_json = ?, updated_at = ? WHERE generation_id = ? AND id = ? AND type = 'workflow_update'`, row.Type, row.Title, row.Confidence, attrs, now, generationID, row.ID)
	if err != nil {
		return false, fmt.Errorf("replace parent scoped placeholder node %s: %w", row.ID, err)
	}
	if rows, _ := result.RowsAffected(); rows != 1 {
		return false, fmt.Errorf("replace parent scoped placeholder node %s affected %d rows", row.ID, rows)
	}
	return true, nil
}

func deleteParentScopedPlaceholderPathTx(ctx context.Context, tx *sql.Tx, generationID, parentUpdateID string, row PathIndexImport) error {
	pathValue := normalizeScopedPath(row.Path)
	if pathValue == "" {
		return nil
	}
	rows, err := tx.QueryContext(ctx, `SELECT p.id, e.attrs_json FROM path_index p JOIN evidence e ON e.id = p.evidence_id AND e.generation_id = p.generation_id WHERE p.generation_id = ? AND p.path = ?`, generationID, pathValue)
	if err != nil {
		return fmt.Errorf("read parent scoped placeholder path %s: %w", pathValue, err)
	}
	defer rows.Close()
	ids := []string{}
	for rows.Next() {
		var id, attrsRaw string
		if err := rows.Scan(&id, &attrsRaw); err != nil {
			return fmt.Errorf("scan parent scoped placeholder path %s: %w", pathValue, err)
		}
		attrs, err := decodeAttrsObject(attrsRaw)
		if err != nil {
			return fmt.Errorf("decode parent scoped placeholder path %s attrs: %w", pathValue, err)
		}
		if strings.TrimSpace(stringValue(attrs["update_id"])) == parentUpdateID {
			ids = append(ids, id)
		}
	}
	if err := rows.Err(); err != nil {
		return fmt.Errorf("iterate parent scoped placeholder path %s: %w", pathValue, err)
	}
	for _, id := range ids {
		if _, err := tx.ExecContext(ctx, `DELETE FROM path_index WHERE generation_id = ? AND id = ?`, generationID, id); err != nil {
			return fmt.Errorf("delete parent scoped placeholder path %s: %w", id, err)
		}
	}
	return nil
}

func applyScopedRetirementsTx(ctx context.Context, tx *sql.Tx, generationID string, retirements []ScopedRetirement, now string) (map[string][]string, error) {
	retired := map[string][]string{"aliases": []string{}, "paths": []string{}, "claims": []string{}}
	for _, retirement := range retirements {
		reason := strings.TrimSpace(retirement.Reason)
		if reason == "" {
			return retired, fmt.Errorf("retirement reason is required")
		}
		switch strings.TrimSpace(retirement.Kind) {
		case "alias":
			id := strings.TrimSpace(retirement.ID)
			if id == "" {
				return retired, fmt.Errorf("alias retirement id is required")
			}
			var targetType, targetID, alias string
			if err := tx.QueryRowContext(ctx, `SELECT target_type, target_id, alias FROM alias_index WHERE generation_id = ? AND id = ?`, generationID, id).Scan(&targetType, &targetID, &alias); err != nil {
				if errors.Is(err, sql.ErrNoRows) {
					return retired, fmt.Errorf("retire alias %s affected 0 rows", id)
				}
				return retired, fmt.Errorf("read alias %s before retirement: %w", id, err)
			}
			result, err := tx.ExecContext(ctx, `DELETE FROM alias_index WHERE generation_id = ? AND id = ?`, generationID, id)
			if err != nil {
				return retired, fmt.Errorf("retire alias %s: %w", id, err)
			}
			if rows, _ := result.RowsAffected(); rows != 1 {
				return retired, fmt.Errorf("retire alias %s affected %d rows", id, rows)
			}
			if defaultScopedString(targetType, "node") == "node" && strings.TrimSpace(targetID) != "" {
				var remaining int
				if err := tx.QueryRowContext(ctx, `SELECT COUNT(*) FROM alias_index WHERE generation_id = ? AND target_type = 'node' AND target_id = ?`, generationID, targetID).Scan(&remaining); err != nil {
					return retired, fmt.Errorf("count remaining aliases for %s: %w", targetID, err)
				}
				if remaining == 0 {
					fallbackAlias := strings.TrimSpace(targetID)
					fallbackID := "A-scoped-retained-" + stableScopedPart(generationID+"-"+targetID+"-"+id)
					if _, err := tx.ExecContext(ctx, `INSERT INTO alias_index(id, generation_id, alias, normalized_alias, target_type, target_id, language, source, confidence, evidence_id) VALUES(?, ?, ?, ?, 'node', ?, 'unknown', 'scoped_registration_retirement_retained_node_id', 'partial', '')`, fallbackID, generationID, fallbackAlias, normalizeWorkflowAlias(fallbackAlias), targetID); err != nil {
						return retired, fmt.Errorf("retain node identity alias after retiring %s (%s): %w", id, alias, err)
					}
				}
			}
			retired["aliases"] = append(retired["aliases"], id)
		case "path":
			path := normalizeScopedPath(retirement.Path)
			if path == "" {
				return retired, fmt.Errorf("path retirement path is required")
			}
			result, err := tx.ExecContext(ctx, `DELETE FROM path_index WHERE generation_id = ? AND path = ?`, generationID, path)
			if err != nil {
				return retired, fmt.Errorf("retire path %s: %w", path, err)
			}
			if rows, _ := result.RowsAffected(); rows != 1 {
				return retired, fmt.Errorf("retire path %s affected %d rows", path, rows)
			}
			retired["paths"] = append(retired["paths"], path)
		case "claim":
			id := strings.TrimSpace(retirement.ID)
			if id == "" {
				return retired, fmt.Errorf("claim retirement id is required")
			}
			result, err := tx.ExecContext(ctx, `UPDATE claims SET prior_state = state, state = 'stale', freshness = 'stale', state_reason = ?, revision = revision + 1, updated_at = ? WHERE generation_id = ? AND id = ?`, reason, now, generationID, id)
			if err != nil {
				return retired, fmt.Errorf("retire claim %s: %w", id, err)
			}
			if rows, _ := result.RowsAffected(); rows != 1 {
				return retired, fmt.Errorf("retire claim %s affected %d rows", id, rows)
			}
			retired["claims"] = append(retired["claims"], id)
		default:
			return retired, fmt.Errorf("unsupported retirement kind %q", retirement.Kind)
		}
	}
	return retired, nil
}

func markScopedAffectedClaimsStaleTx(ctx context.Context, tx *sql.Tx, generationID string, changedPaths []string, newClaimIDs []string, retirements []ScopedRetirement, reason, now string) ([]string, error) {
	newClaims := map[string]bool{}
	for _, id := range newClaimIDs {
		newClaims[strings.TrimSpace(id)] = true
	}
	claimIDs := []string{}
	for _, retirement := range retirements {
		if retirement.Kind == "claim" {
			claimIDs = append(claimIDs, retirement.ID)
		}
	}
	for _, path := range changedPaths {
		rows, err := tx.QueryContext(ctx, `SELECT DISTINCT c.id FROM path_index p JOIN claims c ON c.generation_id = p.generation_id AND c.node_id = p.node_id WHERE p.generation_id = ? AND p.path = ?`, generationID, path)
		if err != nil {
			return nil, err
		}
		for rows.Next() {
			var id string
			if rows.Scan(&id) == nil && !newClaims[id] {
				claimIDs = append(claimIDs, id)
			}
		}
		if err := rows.Close(); err != nil {
			return nil, err
		}
	}
	claimIDs = uniqueSorted(claimIDs)
	for _, id := range claimIDs {
		if _, err := tx.ExecContext(ctx, `UPDATE claims SET freshness = 'stale', state_reason = ?, revision = revision + 1, updated_at = ? WHERE generation_id = ? AND id = ? AND freshness <> 'stale'`, reason, now, generationID, id); err != nil {
			return nil, fmt.Errorf("mark claim %s stale: %w", id, err)
		}
	}
	return claimIDs, nil
}

func runScopedNegativeProbesTx(ctx context.Context, tx *sql.Tx, generationID string, probes []ScopedNegativeProbe) ([]ScopedNegativeEvidence, error) {
	out := []ScopedNegativeEvidence{}
	for _, probe := range probes {
		query := strings.TrimSpace(probe.Query)
		if query == "" {
			continue
		}
		kind := defaultScopedString(probe.Kind, "alias")
		count := 0
		switch kind {
		case "path":
			if err := tx.QueryRowContext(ctx, `SELECT COUNT(*) FROM path_index WHERE generation_id = ? AND path = ?`, generationID, normalizeScopedPath(query)).Scan(&count); err != nil {
				return nil, fmt.Errorf("run negative path query %s: %w", query, err)
			}
		case "alias":
			if err := tx.QueryRowContext(ctx, `SELECT COUNT(*) FROM alias_index WHERE generation_id = ? AND normalized_alias = ?`, generationID, normalizeWorkflowAlias(query)).Scan(&count); err != nil {
				return nil, fmt.Errorf("run negative alias query %s: %w", query, err)
			}
		default:
			return nil, fmt.Errorf("unsupported negative probe kind %q", kind)
		}
		status := "absent_current"
		if count != 0 {
			status = "still_current"
		}
		out = append(out, ScopedNegativeEvidence{Intent: defaultScopedString(probe.Intent, "negative-alias"), Query: query, Kind: kind, ObservedCount: count, Status: status, Argv: "specify-runtime cognition query --intent negative-alias --query " + query + " --format json"})
	}
	return out, nil
}

func emptyScopedRegistered() map[string][]string {
	return map[string][]string{"evidence": []string{}, "nodes": []string{}, "edges": []string{}, "observations": []string{}, "claims": []string{}, "aliases": []string{}, "path_index": []string{}}
}

func registeredNodeIDs(values map[string][]string) []string { return uniqueSorted(values["nodes"]) }
func normalizeScopedPath(value string) string {
	value = strings.TrimSpace(strings.ReplaceAll(value, "\\", "/"))
	for strings.HasPrefix(value, "./") {
		value = strings.TrimPrefix(value, "./")
	}
	return strings.TrimRight(value, "/")
}
func defaultScopedString(value, fallback string) string {
	if strings.TrimSpace(value) == "" {
		return fallback
	}
	return strings.TrimSpace(value)
}
func stableScopedPart(value string) string {
	return strings.TrimPrefix(workflowAliasID("scoped", "scoped", value, "scoped"), "alias-")
}
