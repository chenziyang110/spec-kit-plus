package runcontrol

import (
	"context"
	"database/sql"
	"errors"
	"fmt"
	"strings"
	"time"
)

func (store *Store) GetCandidateForRun(ctx context.Context, runID string) (Candidate, error) {
	if strings.TrimSpace(runID) == "" {
		return Candidate{}, fmt.Errorf("%w: run id is required", ErrInvalidArgument)
	}
	return readCandidateForRunTx(ctx, store.db, runID)
}

func (store *Store) GetCandidate(ctx context.Context, candidateID string) (Candidate, error) {
	if strings.TrimSpace(candidateID) == "" {
		return Candidate{}, fmt.Errorf("%w: candidate id is required", ErrInvalidArgument)
	}
	return readCandidateTx(ctx, store.db, candidateID)
}

func insertCandidateTx(
	ctx context.Context,
	transaction *sql.Tx,
	run Run,
	attempt Attempt,
	activity Activity,
	workspace Workspace,
	snapshot CandidateSnapshot,
	nowMS int64,
) (Candidate, error) {
	if err := validateCandidateSnapshot(run, attempt, activity, workspace, snapshot); err != nil {
		return Candidate{}, err
	}
	candidate := Candidate{
		CandidateID:         snapshot.CandidateID,
		RunID:               run.RunID,
		AttemptID:           attempt.AttemptID,
		ActivityID:          activity.ActivityID,
		WorkspaceID:         workspace.WorkspaceID,
		WorkspaceGeneration: workspace.Generation,
		TargetRef:           snapshot.TargetRef,
		BaseCommit:          snapshot.BaseCommit,
		PrivateRef:          snapshot.PrivateRef,
		HeadCommit:          snapshot.HeadCommit,
		Status:              CandidateQueued,
		Revision:            1,
		CreatedAtMS:         nowMS,
		UpdatedAtMS:         nowMS,
	}
	result, err := transaction.ExecContext(ctx, `
		INSERT INTO candidates (
			candidate_id, run_id, attempt_id, activity_id, workspace_id,
			workspace_generation, target_ref, base_commit, private_ref,
			head_commit, status, revision, created_at_ms, updated_at_ms
		) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
		ON CONFLICT(run_id) DO NOTHING
	`, candidate.CandidateID, candidate.RunID, candidate.AttemptID, candidate.ActivityID,
		candidate.WorkspaceID, candidate.WorkspaceGeneration, candidate.TargetRef,
		candidate.BaseCommit, candidate.PrivateRef, candidate.HeadCommit,
		candidate.Status, candidate.Revision, candidate.CreatedAtMS, candidate.UpdatedAtMS)
	if err != nil {
		if isUniqueConstraintError(err) {
			return Candidate{}, fmt.Errorf("%w: candidate %q conflicts with an existing execution binding", ErrAlreadyExists, candidate.CandidateID)
		}
		return Candidate{}, fmt.Errorf("insert candidate: %w", err)
	}
	inserted, err := result.RowsAffected()
	if err != nil {
		return Candidate{}, fmt.Errorf("count inserted candidates: %w", err)
	}
	if inserted == 0 {
		existing, readErr := readCandidateForRunTx(ctx, transaction, run.RunID)
		if readErr != nil {
			return Candidate{}, readErr
		}
		if !candidateImmutableFieldsEqual(existing, candidate) {
			return Candidate{}, fmt.Errorf("%w: run %q already published a different candidate", ErrCandidateBinding, run.RunID)
		}
		return existing, nil
	}
	return candidate, nil
}

func validateCandidateSnapshot(
	run Run,
	attempt Attempt,
	activity Activity,
	workspace Workspace,
	snapshot CandidateSnapshot,
) error {
	required := map[string]string{
		"candidate_id": snapshot.CandidateID,
		"target_ref":   snapshot.TargetRef,
		"base_commit":  snapshot.BaseCommit,
		"private_ref":  snapshot.PrivateRef,
		"head_commit":  snapshot.HeadCommit,
	}
	for name, value := range required {
		if strings.TrimSpace(value) == "" {
			return fmt.Errorf("%w: %s is required", ErrInvalidArgument, name)
		}
	}
	if !strings.HasPrefix(snapshot.TargetRef, "refs/heads/") ||
		!strings.HasPrefix(snapshot.PrivateRef, "refs/heads/specify/runs/") ||
		!validGitObjectID(snapshot.BaseCommit) || !validGitObjectID(snapshot.HeadCommit) {
		return fmt.Errorf("%w: candidate Git identity is invalid", ErrCandidateBinding)
	}
	if attempt.RunID != run.RunID || activity.RunID != run.RunID || workspace.RunID != run.RunID ||
		attempt.ActivityID != activity.ActivityID || attempt.WorkspaceID != workspace.WorkspaceID ||
		attempt.WorkspaceGeneration != workspace.Generation || snapshot.TargetRef != workspace.BaseRef ||
		snapshot.BaseCommit != workspace.BaseCommit || snapshot.PrivateRef != workspace.PrivateRef {
		return fmt.Errorf("%w: candidate does not match its execution workspace", ErrCandidateBinding)
	}
	return nil
}

func candidateImmutableFieldsEqual(left, right Candidate) bool {
	return left.CandidateID == right.CandidateID && left.RunID == right.RunID &&
		left.AttemptID == right.AttemptID && left.ActivityID == right.ActivityID &&
		left.WorkspaceID == right.WorkspaceID && left.WorkspaceGeneration == right.WorkspaceGeneration &&
		left.TargetRef == right.TargetRef && left.BaseCommit == right.BaseCommit &&
		left.PrivateRef == right.PrivateRef && left.HeadCommit == right.HeadCommit
}

func readCandidateForRunTx(ctx context.Context, querier rowQuerier, runID string) (Candidate, error) {
	row := querier.QueryRowContext(ctx, candidateSelectSQL+` WHERE run_id = ?`, runID)
	candidate, err := scanCandidate(row)
	if errors.Is(err, sql.ErrNoRows) {
		return Candidate{}, fmt.Errorf("%w: candidate for run %q", ErrCandidateNotFound, runID)
	}
	return candidate, err
}

func readCandidateTx(ctx context.Context, querier rowQuerier, candidateID string) (Candidate, error) {
	row := querier.QueryRowContext(ctx, candidateSelectSQL+` WHERE candidate_id = ?`, candidateID)
	candidate, err := scanCandidate(row)
	if errors.Is(err, sql.ErrNoRows) {
		return Candidate{}, fmt.Errorf("%w: candidate %q", ErrCandidateNotFound, candidateID)
	}
	return candidate, err
}

const candidateSelectSQL = `
	SELECT candidate_id, run_id, attempt_id, activity_id, workspace_id,
	       workspace_generation, target_ref, base_commit, private_ref,
	       head_commit, status, revision, created_at_ms, updated_at_ms
	FROM candidates`

type candidateScanner interface{ Scan(...any) error }

func scanCandidate(scanner candidateScanner) (Candidate, error) {
	var candidate Candidate
	err := scanner.Scan(
		&candidate.CandidateID,
		&candidate.RunID,
		&candidate.AttemptID,
		&candidate.ActivityID,
		&candidate.WorkspaceID,
		&candidate.WorkspaceGeneration,
		&candidate.TargetRef,
		&candidate.BaseCommit,
		&candidate.PrivateRef,
		&candidate.HeadCommit,
		&candidate.Status,
		&candidate.Revision,
		&candidate.CreatedAtMS,
		&candidate.UpdatedAtMS,
	)
	if err != nil {
		return Candidate{}, err
	}
	return candidate, nil
}

func candidateNowMS() int64 { return time.Now().UTC().UnixMilli() }
