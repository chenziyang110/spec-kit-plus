package store

import (
	"context"
	"database/sql"
	"encoding/json"
	"errors"
	"fmt"
	"strings"
	"time"

	"github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/claim"
)

type ClaimReconciliationBatch struct {
	ID           string
	PacketHash   string
	GenerationID string
	Workflow     string
	ObservedAt   string
	CommitSHA    string
	Items        []ClaimReconciliationItem
}

type ClaimReconciliationItem struct {
	ClaimID       string
	ExpectedState claim.State
	Reason        string
	Evidence      []ClaimReconciliationEvidence
	Verification  *ClaimReconciliationVerification
}

type ClaimReconciliationEvidence struct {
	ID          string
	SourceKind  string
	SourcePath  string
	Span        string
	ContentHash string
	Role        string
}

type ClaimReconciliationVerification struct {
	ID      string
	Result  claim.VerificationResult
	Command string
}

type ClaimReconciliationResult struct {
	ID                 string                      `json:"reconciliation_id"`
	ActiveGenerationID string                      `json:"active_generation_id"`
	ResultState        string                      `json:"result_state"`
	Replayed           bool                        `json:"replayed"`
	Claims             []ClaimReconciliationRecord `json:"reconciled_claims"`
}

type ClaimReconciliationRecord struct {
	ClaimID        string      `json:"claim_id"`
	FromState      claim.State `json:"from_state"`
	ToState        claim.State `json:"to_state"`
	StateReason    string      `json:"state_reason"`
	EvidenceIDs    []string    `json:"evidence_refs"`
	VerificationID string      `json:"verification_ref,omitempty"`
	TransitionID   string      `json:"transition_ref,omitempty"`
}

type reconciliationPreflight struct {
	item          ClaimReconciliationItem
	from          claim.State
	freshness     claim.Freshness
	decision      claim.ReconciliationDecision
	basisAccepted bool
}

func (s *Store) ApplyClaimReconciliation(ctx context.Context, input ClaimReconciliationBatch) (ClaimReconciliationResult, error) {
	if err := validateReconciliationBatch(input); err != nil {
		return ClaimReconciliationResult{}, err
	}
	observedAt, _ := time.Parse(time.RFC3339, input.ObservedAt)

	tx, err := s.db.BeginTx(ctx, nil)
	if err != nil {
		return ClaimReconciliationResult{}, fmt.Errorf("begin claim reconciliation: %w", err)
	}
	committed := false
	defer func() {
		if !committed {
			_ = tx.Rollback()
		}
	}()

	if replayed, found, err := replayedClaimReconciliation(ctx, tx, input); err != nil {
		return ClaimReconciliationResult{}, err
	} else if found {
		return replayed, nil
	}

	var activeGenerationID string
	err = tx.QueryRowContext(ctx, `SELECT id FROM generations WHERE state = 'active' ORDER BY sequence DESC LIMIT 1`).Scan(&activeGenerationID)
	if errors.Is(err, sql.ErrNoRows) {
		return ClaimReconciliationResult{}, fmt.Errorf("project-cognition.db has no active generation")
	}
	if err != nil {
		return ClaimReconciliationResult{}, fmt.Errorf("read active generation for claim reconciliation: %w", err)
	}
	if input.GenerationID != activeGenerationID {
		return ClaimReconciliationResult{}, fmt.Errorf("claim reconciliation expected generation %q but active generation is %q", input.GenerationID, activeGenerationID)
	}

	preflight := make([]reconciliationPreflight, 0, len(input.Items))
	seenClaims := map[string]bool{}
	seenEvidence := map[string]bool{}
	seenVerifications := map[string]bool{}
	for _, item := range input.Items {
		if seenClaims[item.ClaimID] {
			return ClaimReconciliationResult{}, fmt.Errorf("claim reconciliation contains duplicate claim %q", item.ClaimID)
		}
		seenClaims[item.ClaimID] = true
		var stateValue, freshnessValue string
		err := tx.QueryRowContext(ctx, `SELECT state, freshness FROM claims WHERE generation_id = ? AND id = ?`, activeGenerationID, item.ClaimID).Scan(&stateValue, &freshnessValue)
		if errors.Is(err, sql.ErrNoRows) {
			return ClaimReconciliationResult{}, fmt.Errorf("claim %q does not exist in active generation %q", item.ClaimID, activeGenerationID)
		}
		if err != nil {
			return ClaimReconciliationResult{}, fmt.Errorf("read claim %q for reconciliation: %w", item.ClaimID, err)
		}
		from := claim.State(stateValue)
		if item.ExpectedState != from {
			return ClaimReconciliationResult{}, fmt.Errorf("claim %q expected state %q but current state is %q", item.ClaimID, item.ExpectedState, from)
		}
		if err := rejectOlderClaimObservation(ctx, tx, item.ClaimID, observedAt); err != nil {
			return ClaimReconciliationResult{}, err
		}

		signals := claim.ReconciliationSignals{}
		for _, evidence := range item.Evidence {
			if seenEvidence[evidence.ID] {
				return ClaimReconciliationResult{}, fmt.Errorf("claim reconciliation contains duplicate evidence id %q", evidence.ID)
			}
			seenEvidence[evidence.ID] = true
			switch evidence.Role {
			case "supporting":
				signals.SupportingEvidence = true
			case "contradicting":
				signals.ContradictingEvidence = true
			}
		}
		if item.Verification != nil {
			if seenVerifications[item.Verification.ID] {
				return ClaimReconciliationResult{}, fmt.Errorf("claim reconciliation contains duplicate verification id %q", item.Verification.ID)
			}
			seenVerifications[item.Verification.ID] = true
			signals.VerificationResult = item.Verification.Result
		}
		decision := claim.DeriveReconciliation(from, claim.Freshness(freshnessValue), signals)
		if !claim.CanReconcileTransition(from, decision.State) {
			return ClaimReconciliationResult{}, fmt.Errorf("claim %q cannot reconcile from %q to %q", item.ClaimID, from, decision.State)
		}
		preflight = append(preflight, reconciliationPreflight{
			item: item, from: from, freshness: claim.Freshness(freshnessValue), decision: decision,
			basisAccepted: reconciliationBasisAccepted(signals),
		})
	}

	result := ClaimReconciliationResult{
		ID: input.ID, ActiveGenerationID: activeGenerationID, ResultState: "ready", Replayed: false,
		Claims: make([]ClaimReconciliationRecord, 0, len(preflight)),
	}
	for _, planned := range preflight {
		record, err := applyClaimReconciliationItem(ctx, tx, input, planned)
		if err != nil {
			return ClaimReconciliationResult{}, err
		}
		if !planned.basisAccepted {
			result.ResultState = "partial"
		}
		result.Claims = append(result.Claims, record)
	}
	encodedResult, err := json.Marshal(result)
	if err != nil {
		return ClaimReconciliationResult{}, fmt.Errorf("encode claim reconciliation result: %w", err)
	}
	if _, err := tx.ExecContext(ctx, `INSERT INTO claim_reconciliations(id, generation_id, workflow, observed_at, packet_hash, result_state, attrs_json) VALUES(?, ?, ?, ?, ?, ?, ?)`, input.ID, activeGenerationID, input.Workflow, input.ObservedAt, input.PacketHash, result.ResultState, string(encodedResult)); err != nil {
		return ClaimReconciliationResult{}, fmt.Errorf("record claim reconciliation %q: %w", input.ID, err)
	}
	if err := tx.Commit(); err != nil {
		return ClaimReconciliationResult{}, fmt.Errorf("commit claim reconciliation: %w", err)
	}
	committed = true
	return result, nil
}

func validateReconciliationBatch(input ClaimReconciliationBatch) error {
	for name, value := range map[string]string{
		"id": input.ID, "packet hash": input.PacketHash, "generation id": input.GenerationID,
		"workflow": input.Workflow, "observed_at": input.ObservedAt, "commit sha": input.CommitSHA,
	} {
		if strings.TrimSpace(value) == "" {
			return fmt.Errorf("claim reconciliation %s is required", name)
		}
	}
	if _, err := time.Parse(time.RFC3339, input.ObservedAt); err != nil {
		return fmt.Errorf("claim reconciliation observed_at must be RFC3339: %w", err)
	}
	if len(input.Items) == 0 {
		return fmt.Errorf("claim reconciliation requires at least one item")
	}
	for _, item := range input.Items {
		if strings.TrimSpace(item.ClaimID) == "" || strings.TrimSpace(string(item.ExpectedState)) == "" || strings.TrimSpace(item.Reason) == "" {
			return fmt.Errorf("claim reconciliation item requires claim_id, expected_state, and reason")
		}
		if len(item.Evidence) == 0 && item.Verification == nil {
			return fmt.Errorf("claim %q reconciliation requires evidence or verification", item.ClaimID)
		}
		hasSupporting := false
		hasContradicting := false
		for _, evidence := range item.Evidence {
			if strings.TrimSpace(evidence.ID) == "" || strings.TrimSpace(evidence.SourceKind) == "" || strings.TrimSpace(evidence.SourcePath) == "" || strings.TrimSpace(evidence.Span) == "" || strings.TrimSpace(evidence.ContentHash) == "" {
				return fmt.Errorf("claim %q reconciliation evidence requires id, source_kind, source_path, span, and content_hash", item.ClaimID)
			}
			switch evidence.Role {
			case "supporting":
				hasSupporting = true
			case "contradicting":
				hasContradicting = true
			default:
				return fmt.Errorf("claim %q reconciliation evidence role %q is invalid", item.ClaimID, evidence.Role)
			}
		}
		if item.Verification != nil {
			if strings.TrimSpace(item.Verification.ID) == "" || strings.TrimSpace(item.Verification.Command) == "" {
				return fmt.Errorf("claim %q reconciliation verification requires id and command", item.ClaimID)
			}
			switch item.Verification.Result {
			case claim.VerificationPassed, claim.VerificationFailed, claim.VerificationBlocked, claim.VerificationInconclusive, claim.VerificationContradicted:
			default:
				return fmt.Errorf("claim %q reconciliation verification result %q is invalid", item.ClaimID, item.Verification.Result)
			}
			if item.Verification.Result == claim.VerificationPassed && !hasSupporting {
				return fmt.Errorf("claim %q passed verification requires supporting evidence", item.ClaimID)
			}
			if item.Verification.Result == claim.VerificationContradicted && !hasContradicting {
				return fmt.Errorf("claim %q contradicted verification requires contradicting evidence", item.ClaimID)
			}
		}
	}
	return nil
}

func replayedClaimReconciliation(ctx context.Context, tx *sql.Tx, input ClaimReconciliationBatch) (ClaimReconciliationResult, bool, error) {
	var generationID, packetHash, attrsJSON string
	err := tx.QueryRowContext(ctx, `SELECT generation_id, packet_hash, attrs_json FROM claim_reconciliations WHERE id = ?`, input.ID).Scan(&generationID, &packetHash, &attrsJSON)
	if errors.Is(err, sql.ErrNoRows) {
		return ClaimReconciliationResult{}, false, nil
	}
	if err != nil {
		return ClaimReconciliationResult{}, false, fmt.Errorf("read claim reconciliation replay %q: %w", input.ID, err)
	}
	if generationID != input.GenerationID || packetHash != input.PacketHash {
		return ClaimReconciliationResult{}, false, fmt.Errorf("claim reconciliation id %q conflicts with an existing packet", input.ID)
	}
	var result ClaimReconciliationResult
	if err := json.Unmarshal([]byte(attrsJSON), &result); err != nil {
		return ClaimReconciliationResult{}, false, fmt.Errorf("decode claim reconciliation replay %q: %w", input.ID, err)
	}
	result.Replayed = true
	return result, true, nil
}

func rejectOlderClaimObservation(ctx context.Context, tx *sql.Tx, claimID string, observedAt time.Time) error {
	var latestRaw string
	err := tx.QueryRowContext(ctx, `SELECT observed_at FROM claim_verifications WHERE claim_id = ? AND observed_at <> '' ORDER BY observed_at DESC, id DESC LIMIT 1`, claimID).Scan(&latestRaw)
	if errors.Is(err, sql.ErrNoRows) {
		return nil
	}
	if err != nil {
		return fmt.Errorf("read latest verification for claim %q: %w", claimID, err)
	}
	latest, err := time.Parse(time.RFC3339, latestRaw)
	if err != nil {
		return fmt.Errorf("claim %q has invalid stored verification time %q", claimID, latestRaw)
	}
	if !observedAt.After(latest) {
		return fmt.Errorf("claim %q reconciliation observed_at %s is not newer than latest verification %s", claimID, observedAt.Format(time.RFC3339), latest.Format(time.RFC3339))
	}
	return nil
}

func reconciliationBasisAccepted(signals claim.ReconciliationSignals) bool {
	if signals.ContradictingEvidence || signals.VerificationResult == claim.VerificationContradicted {
		return true
	}
	if !signals.SupportingEvidence {
		return false
	}
	return signals.VerificationResult == "" || signals.VerificationResult == claim.VerificationPassed
}

func applyClaimReconciliationItem(ctx context.Context, tx *sql.Tx, batch ClaimReconciliationBatch, planned reconciliationPreflight) (ClaimReconciliationRecord, error) {
	item := planned.item
	basisState := "historical"
	if planned.basisAccepted {
		basisState = "current"
		if _, err := tx.ExecContext(ctx, `UPDATE claim_evidence SET basis_state = 'superseded' WHERE claim_id = ? AND basis_state = 'current'`, item.ClaimID); err != nil {
			return ClaimReconciliationRecord{}, fmt.Errorf("supersede claim %q evidence basis: %w", item.ClaimID, err)
		}
	}
	evidenceIDs := make([]string, 0, len(item.Evidence))
	verificationEvidenceID := ""
	for _, evidence := range item.Evidence {
		attrs, err := attrsJSONOrEmpty(map[string]any{"reconciliation_id": batch.ID, "workflow": batch.Workflow})
		if err != nil {
			return ClaimReconciliationRecord{}, err
		}
		if _, err := tx.ExecContext(ctx, `INSERT INTO evidence(id, generation_id, source_kind, source_path, commit_sha, span, extractor, content_hash, captured_at, attrs_json) VALUES(?, ?, ?, ?, ?, ?, 'claim-reconcile', ?, ?, ?)`, evidence.ID, batch.GenerationID, evidence.SourceKind, evidence.SourcePath, batch.CommitSHA, evidence.Span, evidence.ContentHash, batch.ObservedAt, attrs); err != nil {
			return ClaimReconciliationRecord{}, fmt.Errorf("insert claim %q reconciliation evidence %q: %w", item.ClaimID, evidence.ID, err)
		}
		if _, err := tx.ExecContext(ctx, `INSERT INTO claim_evidence(claim_id, evidence_id, role, reconciliation_id, basis_state) VALUES(?, ?, ?, ?, ?)`, item.ClaimID, evidence.ID, evidence.Role, batch.ID, basisState); err != nil {
			return ClaimReconciliationRecord{}, fmt.Errorf("link claim %q reconciliation evidence %q: %w", item.ClaimID, evidence.ID, err)
		}
		evidenceIDs = append(evidenceIDs, evidence.ID)
		if verificationEvidenceID == "" || (item.Verification != nil && item.Verification.Result == claim.VerificationContradicted && evidence.Role == "contradicting") || (item.Verification != nil && item.Verification.Result == claim.VerificationPassed && evidence.Role == "supporting") {
			verificationEvidenceID = evidence.ID
		}
	}

	verificationID := ""
	if item.Verification != nil {
		verificationID = item.Verification.ID
		attrs, err := attrsJSONOrEmpty(map[string]any{"reconciliation_id": batch.ID, "reason": item.Reason, "workflow": batch.Workflow})
		if err != nil {
			return ClaimReconciliationRecord{}, err
		}
		if _, err := tx.ExecContext(ctx, `INSERT INTO claim_verifications(id, claim_id, generation_id, result, command, evidence_id, observed_at, attrs_json) VALUES(?, ?, ?, ?, ?, ?, ?, ?)`, verificationID, item.ClaimID, batch.GenerationID, item.Verification.Result, item.Verification.Command, verificationEvidenceID, batch.ObservedAt, attrs); err != nil {
			return ClaimReconciliationRecord{}, fmt.Errorf("insert claim %q reconciliation verification: %w", item.ClaimID, err)
		}
	}

	transitionID := ""
	if planned.basisAccepted {
		if planned.decision.State != planned.from {
			if _, err := tx.ExecContext(ctx, `UPDATE claims SET prior_state = state, state = ?, freshness = ?, state_reason = ?, updated_at = ? WHERE generation_id = ? AND id = ?`, planned.decision.State, planned.decision.Freshness, item.Reason, batch.ObservedAt, batch.GenerationID, item.ClaimID); err != nil {
				return ClaimReconciliationRecord{}, fmt.Errorf("update reconciled claim %q: %w", item.ClaimID, err)
			}
			transitionID = "claim-transition:reconcile:" + stableIDPart(batch.ID) + ":" + stableIDPart(item.ClaimID)
			attrs, err := attrsJSONOrEmpty(map[string]any{"reconciliation_id": batch.ID, "workflow": batch.Workflow})
			if err != nil {
				return ClaimReconciliationRecord{}, err
			}
			if _, err := tx.ExecContext(ctx, `INSERT INTO claim_transitions(id, claim_id, generation_id, from_state, to_state, reason, evidence_id, occurred_at, attrs_json) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)`, transitionID, item.ClaimID, batch.GenerationID, planned.from, planned.decision.State, item.Reason, verificationEvidenceID, batch.ObservedAt, attrs); err != nil {
				return ClaimReconciliationRecord{}, fmt.Errorf("insert claim %q reconciliation transition: %w", item.ClaimID, err)
			}
		} else {
			if _, err := tx.ExecContext(ctx, `UPDATE claims SET freshness = ?, state_reason = ?, updated_at = ? WHERE generation_id = ? AND id = ?`, planned.decision.Freshness, item.Reason, batch.ObservedAt, batch.GenerationID, item.ClaimID); err != nil {
				return ClaimReconciliationRecord{}, fmt.Errorf("refresh reconciled claim %q: %w", item.ClaimID, err)
			}
		}
	}
	return ClaimReconciliationRecord{
		ClaimID: item.ClaimID, FromState: planned.from, ToState: planned.decision.State, StateReason: item.Reason,
		EvidenceIDs: evidenceIDs, VerificationID: verificationID, TransitionID: transitionID,
	}, nil
}
