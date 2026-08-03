package runcontrol

import (
	"context"
	"fmt"
	"strings"
	"time"
)

type finishAttemptTargets struct {
	run       RunStatus
	attempt   AttemptStatus
	activity  ActivityStatus
	workspace WorkspaceStatus
}

// FinishAttempt atomically records the definite result of an owned execution.
// The Run fence advances in the same transaction as every terminal aggregate,
// so a late heartbeat or operation can never write through a completed Run.
func (store *Store) FinishAttempt(
	ctx context.Context,
	params FinishAttemptParams,
) (FinishedExecution, error) {
	targets, err := validateFinishAttemptParams(params)
	if err != nil {
		return FinishedExecution{}, err
	}

	transaction, err := store.db.BeginTx(ctx, nil)
	if err != nil {
		return FinishedExecution{}, fmt.Errorf("begin finish attempt transaction: %w", err)
	}
	defer func() { _ = transaction.Rollback() }()
	if err := requireActiveSupervisorTx(ctx, transaction, store.ownerEpoch); err != nil {
		return FinishedExecution{}, err
	}

	attempt, err := readAttemptTx(ctx, transaction, params.AttemptID)
	if err != nil {
		return FinishedExecution{}, err
	}
	if attempt.OwnerEpoch != store.ownerEpoch || attempt.Fence != params.Fence {
		return FinishedExecution{}, fmt.Errorf(
			"%w: attempt %q belongs to a different supervisor authority",
			ErrStaleFence,
			attempt.AttemptID,
		)
	}
	run, err := readRunTx(ctx, transaction, attempt.RunID)
	if err != nil {
		return FinishedExecution{}, err
	}
	activity, err := readActivityTx(ctx, transaction, attempt.ActivityID)
	if err != nil {
		return FinishedExecution{}, err
	}
	workspace, err := readWorkspaceTx(ctx, transaction, attempt.WorkspaceID)
	if err != nil {
		return FinishedExecution{}, err
	}

	finished := FinishedExecution{
		Run:       run,
		Attempt:   attempt,
		Activity:  activity,
		Workspace: workspace,
	}
	if finishAttemptMatchesReplay(finished, params, targets, store.ownerEpoch) {
		if err := transaction.Commit(); err != nil {
			return FinishedExecution{}, fmt.Errorf("commit finish attempt replay: %w", err)
		}
		return finished, nil
	}
	if isTerminalAttemptStatus(attempt.Status) {
		return FinishedExecution{}, fmt.Errorf(
			"%w: attempt %q already finished as %q",
			ErrInvalidTransition,
			attempt.AttemptID,
			attempt.Status,
		)
	}
	if err := validateAttemptAuthority(attempt, run, params.Fence, store.ownerEpoch); err != nil {
		return FinishedExecution{}, err
	}
	if attempt.Status != AttemptActive && attempt.Status != AttemptSealing {
		return FinishedExecution{}, fmt.Errorf(
			"%w: attempt %q is %q, expected active or sealing",
			ErrInvalidTransition,
			attempt.AttemptID,
			attempt.Status,
		)
	}
	if run.Status != RunActive || activity.Status != ActivityActive || workspace.Status != WorkspaceInUse {
		return FinishedExecution{}, fmt.Errorf(
			"%w: attempt %q execution aggregates are not active",
			ErrStaleFence,
			attempt.AttemptID,
		)
	}
	if activity.RunID != run.RunID || workspace.RunID != run.RunID ||
		attempt.RunID != run.RunID || attempt.ActivityID != activity.ActivityID ||
		attempt.WorkspaceID != workspace.WorkspaceID ||
		workspace.Generation != attempt.WorkspaceGeneration {
		return FinishedExecution{}, fmt.Errorf(
			"%w: attempt %q execution bindings are inconsistent",
			ErrStaleFence,
			attempt.AttemptID,
		)
	}
	nowMS := time.Now().UTC().UnixMilli()
	if attempt.LeaseUntilMS <= nowMS {
		return FinishedExecution{}, fmt.Errorf(
			"%w: attempt %q lease expired before completion",
			ErrStaleFence,
			attempt.AttemptID,
		)
	}

	result, err := transaction.ExecContext(ctx, `
		UPDATE runs
		SET status = ?, current_fence = current_fence + 1,
		    owner_epoch = ?, revision = revision + 1, updated_at_ms = ?
		WHERE run_id = ? AND revision = ? AND current_fence = ?
		  AND status = ? AND owner_epoch = ?
	`, targets.run, store.ownerEpoch, nowMS, run.RunID, run.Revision,
		run.CurrentFence, RunActive, store.ownerEpoch)
	if err != nil {
		return FinishedExecution{}, fmt.Errorf("finish attempt run: %w", err)
	}
	if err := requireOneCASRow(result, ErrStaleFence, "finish attempt run"); err != nil {
		return FinishedExecution{}, err
	}
	run.Status = targets.run
	run.CurrentFence++
	run.OwnerEpoch = store.ownerEpoch
	run.Revision++
	run.UpdatedAtMS = nowMS

	if err := updateAttemptTerminalTx(ctx, transaction, attempt, targets.attempt, nowMS); err != nil {
		return FinishedExecution{}, err
	}
	attempt.Status = targets.attempt
	attempt.Revision++
	attempt.UpdatedAtMS = nowMS
	if err := updateActivityStatusTx(ctx, transaction, &activity, targets.activity, nowMS, params.Reason); err != nil {
		return FinishedExecution{}, err
	}
	if err := updateWorkspaceStatusTx(ctx, transaction, &workspace, targets.workspace, nowMS, params.Reason); err != nil {
		return FinishedExecution{}, err
	}
	if err := appendRunEventTx(ctx, transaction, run, "run."+string(targets.run), params.Reason); err != nil {
		return FinishedExecution{}, err
	}
	if err := transaction.Commit(); err != nil {
		return FinishedExecution{}, fmt.Errorf("commit finish attempt: %w", err)
	}
	return FinishedExecution{
		Run:       run,
		Attempt:   attempt,
		Activity:  activity,
		Workspace: workspace,
	}, nil
}

func validateFinishAttemptParams(params FinishAttemptParams) (finishAttemptTargets, error) {
	if strings.TrimSpace(params.AttemptID) == "" {
		return finishAttemptTargets{}, fmt.Errorf("%w: attempt_id is required", ErrInvalidArgument)
	}
	if params.Fence <= 0 {
		return finishAttemptTargets{}, fmt.Errorf("%w: fence must be positive", ErrInvalidArgument)
	}
	if strings.TrimSpace(params.Reason) == "" {
		return finishAttemptTargets{}, fmt.Errorf("%w: reason is required", ErrInvalidArgument)
	}
	switch params.Outcome {
	case AttemptOutcomeSucceeded:
		return finishAttemptTargets{
			run:       RunSealed,
			attempt:   AttemptFinished,
			activity:  ActivitySucceeded,
			workspace: WorkspaceSealed,
		}, nil
	case AttemptOutcomeFailed:
		return finishAttemptTargets{
			run:       RunFailed,
			attempt:   AttemptFailed,
			activity:  ActivityFailed,
			workspace: WorkspaceQuarantined,
		}, nil
	default:
		return finishAttemptTargets{}, fmt.Errorf(
			"%w: unsupported attempt outcome %q",
			ErrInvalidArgument,
			params.Outcome,
		)
	}
}

func finishAttemptMatchesReplay(
	finished FinishedExecution,
	params FinishAttemptParams,
	targets finishAttemptTargets,
	ownerEpoch string,
) bool {
	return finished.Run.OwnerEpoch == ownerEpoch &&
		finished.Run.Status == targets.run &&
		finished.Run.CurrentFence == params.Fence+1 &&
		finished.Attempt.OwnerEpoch == ownerEpoch &&
		finished.Attempt.Fence == params.Fence &&
		finished.Attempt.Status == targets.attempt &&
		finished.Activity.Status == targets.activity &&
		finished.Workspace.Status == targets.workspace &&
		finished.Attempt.RunID == finished.Run.RunID &&
		finished.Activity.RunID == finished.Run.RunID &&
		finished.Workspace.RunID == finished.Run.RunID &&
		finished.Attempt.ActivityID == finished.Activity.ActivityID &&
		finished.Attempt.WorkspaceID == finished.Workspace.WorkspaceID &&
		finished.Attempt.WorkspaceGeneration == finished.Workspace.Generation
}

func isTerminalAttemptStatus(status AttemptStatus) bool {
	switch status {
	case AttemptFinished, AttemptRevoked, AttemptLost, AttemptFailed:
		return true
	default:
		return false
	}
}
