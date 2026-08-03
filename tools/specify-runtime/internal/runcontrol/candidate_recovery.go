package runcontrol

import (
	"context"
	"database/sql"
	"fmt"
	"time"
)

func markOwnedIntegrationsOutcomeUnknownTx(ctx context.Context, transaction *sql.Tx, ownerEpoch string, nowMS int64) error {
	_, err := transaction.ExecContext(ctx, `
		UPDATE candidate_integrations
		SET status = ?, reason = 'integration supervisor stopped before durable completion',
		    revision = revision + 1, updated_at_ms = ?
		WHERE owner_epoch = ? AND status IN (?, ?)
	`, IntegrationOutcomeUnknown, nowMS, ownerEpoch, IntegrationPrepared, IntegrationExecuting)
	if err != nil {
		return fmt.Errorf("mark owned candidate integrations outcome unknown: %w", err)
	}
	return nil
}

// recoverTargetIntegrations resolves uncertain work only from observable Git
// facts. Candidate ancestry proves success; an unchanged target permits a safe
// requeue. Ambiguous target movement remains fenced.
func (store *Store) recoverTargetIntegrations(ctx context.Context, repository Repository, targetRef string) (IntegratedCandidate, bool, error) {
	rows, err := store.db.QueryContext(ctx, `
		SELECT integration_id, candidate_id, target_ref, owner_epoch, status,
		       target_before, target_after, reason, revision, created_at_ms, updated_at_ms
		FROM candidate_integrations
		WHERE target_ref = ? AND status = ?
		ORDER BY created_at_ms, integration_id
	`, targetRef, IntegrationOutcomeUnknown)
	if err != nil {
		return IntegratedCandidate{}, false, fmt.Errorf("list uncertain candidate integrations: %w", err)
	}
	uncertain := []CandidateIntegration{}
	for rows.Next() {
		var integration CandidateIntegration
		if err := rows.Scan(
			&integration.IntegrationID, &integration.CandidateID, &integration.TargetRef,
			&integration.OwnerEpoch, &integration.Status, &integration.TargetBefore,
			&integration.TargetAfter, &integration.Reason, &integration.Revision,
			&integration.CreatedAtMS, &integration.UpdatedAtMS,
		); err != nil {
			_ = rows.Close()
			return IntegratedCandidate{}, false, err
		}
		uncertain = append(uncertain, integration)
	}
	if err := rows.Err(); err != nil {
		_ = rows.Close()
		return IntegratedCandidate{}, false, err
	}
	if err := rows.Close(); err != nil {
		return IntegratedCandidate{}, false, err
	}

	for _, integration := range uncertain {
		candidate, err := store.GetCandidate(ctx, integration.CandidateID)
		if err != nil {
			return IntegratedCandidate{}, false, err
		}
		current, err := resolveGitCommit(ctx, repository.Root, targetRef)
		if err != nil {
			return IntegratedCandidate{}, false, err
		}
		if requireGitAncestor(ctx, repository.Root, candidate.HeadCommit, current) == nil {
			outcome, err := store.recoverIntegratedCandidate(ctx, integration, candidate, current)
			return outcome, err == nil, err
		}
		if integration.TargetBefore == "" || integration.TargetBefore == current {
			if err := store.requeueUncertainCandidate(ctx, integration, candidate); err != nil {
				return IntegratedCandidate{}, false, err
			}
			continue
		}
		return IntegratedCandidate{}, false, fmt.Errorf(
			"%w: integration %q outcome is unknown after target moved from %s to %s",
			ErrIntegrationBusy, integration.IntegrationID, integration.TargetBefore, current,
		)
	}
	return IntegratedCandidate{}, false, nil
}

func (store *Store) recoverIntegratedCandidate(ctx context.Context, integration CandidateIntegration, candidate Candidate, targetAfter string) (IntegratedCandidate, error) {
	transaction, err := store.db.BeginTx(ctx, nil)
	if err != nil {
		return IntegratedCandidate{}, fmt.Errorf("begin integrated candidate recovery: %w", err)
	}
	defer func() { _ = transaction.Rollback() }()
	if err := requireActiveSupervisorTx(ctx, transaction, store.ownerEpoch); err != nil {
		return IntegratedCandidate{}, err
	}
	nowMS := time.Now().UTC().UnixMilli()
	targetBefore := integration.TargetBefore
	if targetBefore == "" {
		targetBefore = candidate.BaseCommit
	}
	result, err := transaction.ExecContext(ctx, `
		UPDATE candidate_integrations
		SET owner_epoch = ?, status = ?, target_after = ?,
		    reason = 'reconciled observable integrated target',
		    revision = revision + 1, updated_at_ms = ?
		WHERE integration_id = ? AND revision = ? AND status = ?
	`, store.ownerEpoch, IntegrationSucceeded, targetAfter, nowMS,
		integration.IntegrationID, integration.Revision, IntegrationOutcomeUnknown)
	if err != nil {
		return IntegratedCandidate{}, fmt.Errorf("recover integrated candidate journal: %w", err)
	}
	if err := requireOneCASRow(result, ErrStaleFence, "recover integrated candidate journal"); err != nil {
		return IntegratedCandidate{}, err
	}
	result, err = transaction.ExecContext(ctx, `
		UPDATE candidates SET status = ?, revision = revision + 1, updated_at_ms = ?
		WHERE candidate_id = ? AND revision = ? AND status = ?
	`, CandidateIntegrated, nowMS, candidate.CandidateID, candidate.Revision, CandidateIntegrating)
	if err != nil {
		return IntegratedCandidate{}, fmt.Errorf("recover integrated candidate: %w", err)
	}
	if err := requireOneCASRow(result, ErrRevisionConflict, "recover integrated candidate"); err != nil {
		return IntegratedCandidate{}, err
	}
	candidate.Status = CandidateIntegrated
	candidate.Revision++
	candidate.UpdatedAtMS = nowMS
	integration.OwnerEpoch = store.ownerEpoch
	integration.Status = IntegrationSucceeded
	integration.TargetAfter = targetAfter
	integration.Reason = "reconciled observable integrated target"
	integration.Revision++
	integration.UpdatedAtMS = nowMS
	resultRecord := Result{
		ResultID: supervisedAggregateID("result", candidate.CandidateID, 1), IntegrationID: integration.IntegrationID,
		CandidateID: candidate.CandidateID, RunID: candidate.RunID, TargetRef: candidate.TargetRef,
		TargetBefore: targetBefore, TargetAfter: targetAfter, Status: ResultIntegrated,
		Reason: integration.Reason, CreatedAtMS: nowMS,
	}
	_, err = transaction.ExecContext(ctx, `
		INSERT INTO results (
			result_id, integration_id, candidate_id, run_id, target_ref,
			target_before, target_after, status, reason, created_at_ms
		) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
	`, resultRecord.ResultID, resultRecord.IntegrationID, resultRecord.CandidateID,
		resultRecord.RunID, resultRecord.TargetRef, resultRecord.TargetBefore,
		resultRecord.TargetAfter, resultRecord.Status, resultRecord.Reason, resultRecord.CreatedAtMS)
	if err != nil {
		return IntegratedCandidate{}, fmt.Errorf("insert recovered immutable result: %w", err)
	}
	if err := transaction.Commit(); err != nil {
		return IntegratedCandidate{}, fmt.Errorf("commit integrated candidate recovery: %w", err)
	}
	return IntegratedCandidate{Candidate: candidate, Integration: integration, Result: resultRecord}, nil
}

func (store *Store) requeueUncertainCandidate(ctx context.Context, integration CandidateIntegration, candidate Candidate) error {
	transaction, err := store.db.BeginTx(ctx, nil)
	if err != nil {
		return fmt.Errorf("begin uncertain candidate requeue: %w", err)
	}
	defer func() { _ = transaction.Rollback() }()
	if err := requireActiveSupervisorTx(ctx, transaction, store.ownerEpoch); err != nil {
		return err
	}
	nowMS := time.Now().UTC().UnixMilli()
	result, err := transaction.ExecContext(ctx, `
		UPDATE candidate_integrations
		SET owner_epoch = ?, status = ?, reason = 'requeued after unchanged target recovery',
		    revision = revision + 1, updated_at_ms = ?
		WHERE integration_id = ? AND revision = ? AND status = ?
	`, store.ownerEpoch, IntegrationFailed, nowMS,
		integration.IntegrationID, integration.Revision, IntegrationOutcomeUnknown)
	if err != nil {
		return fmt.Errorf("close uncertain integration journal: %w", err)
	}
	if err := requireOneCASRow(result, ErrStaleFence, "close uncertain integration journal"); err != nil {
		return err
	}
	result, err = transaction.ExecContext(ctx, `
		UPDATE candidates SET status = ?, revision = revision + 1, updated_at_ms = ?
		WHERE candidate_id = ? AND revision = ? AND status = ?
	`, CandidateQueued, nowMS, candidate.CandidateID, candidate.Revision, CandidateIntegrating)
	if err != nil {
		return fmt.Errorf("requeue uncertain candidate: %w", err)
	}
	if err := requireOneCASRow(result, ErrRevisionConflict, "requeue uncertain candidate"); err != nil {
		return err
	}
	if err := transaction.Commit(); err != nil {
		return fmt.Errorf("commit uncertain candidate requeue: %w", err)
	}
	return nil
}
