package runcontrol

import (
	"bytes"
	"context"
	"database/sql"
	"errors"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"time"
)

const integrationBusyRetryInterval = 20 * time.Millisecond

// IntegrateNext claims the oldest queued Candidate for one target ref. A
// durable target-ref claim serializes merges on that target while unrelated
// targets remain independent.
func IntegrateNext(
	ctx context.Context,
	repository Repository,
	params IntegrateNextParams,
) (outcome IntegratedCandidate, returnErr error) {
	params = withIntegrationDefaults(params)
	if strings.TrimSpace(params.TargetRef) == "" {
		return IntegratedCandidate{}, fmt.Errorf("%w: target ref is required", ErrInvalidArgument)
	}
	canonical, err := canonicalAllocationRepository(ctx, repository)
	if err != nil {
		return IntegratedCandidate{}, err
	}
	targetRef, err := resolveMutableTargetRef(ctx, canonical.PrimaryRoot, params.TargetRef)
	if err != nil {
		return IntegratedCandidate{}, fmt.Errorf("resolve mutable target ref %q: %w", params.TargetRef, err)
	}
	params.TargetRef = targetRef
	options := []OpenOption{}
	if params.OwnerEpoch != "" {
		options = append(options, WithOwnerEpoch(params.OwnerEpoch))
	}
	store, err := Open(ctx, canonical.DatabasePath, options...)
	if err != nil {
		return IntegratedCandidate{}, err
	}
	defer func() {
		if closeErr := store.Close(); closeErr != nil {
			returnErr = errors.Join(returnErr, closeErr)
		}
	}()

	now := time.Now().UTC()
	if _, err := store.ReconcileStaleSupervisors(ctx, now, now.Add(-params.SupervisorStaleAfter)); err != nil {
		return IntegratedCandidate{}, fmt.Errorf("reconcile stale integration supervisors: %w", err)
	}
	if recovered, ok, err := store.recoverTargetIntegrations(ctx, canonical, params.TargetRef); err != nil {
		return IntegratedCandidate{}, err
	} else if ok {
		return recovered, nil
	}
	lifecycleCtx, cancelLifecycle := context.WithCancel(ctx)
	heartbeatErrors, heartbeatDone := superviseOwnerHeartbeat(
		lifecycleCtx,
		cancelLifecycle,
		store,
		params.HeartbeatInterval,
	)
	defer func() {
		cancelLifecycle()
		<-heartbeatDone
	}()

	var candidate Candidate
	var integration CandidateIntegration
	for {
		candidate, integration, err = store.claimNextCandidate(lifecycleCtx, params.TargetRef)
		if !errors.Is(err, ErrIntegrationBusy) {
			break
		}
		timer := time.NewTimer(integrationBusyRetryInterval)
		select {
		case <-lifecycleCtx.Done():
			timer.Stop()
			return IntegratedCandidate{}, supervisionCancellationError(ctx, heartbeatErrors)
		case <-timer.C:
		}
	}
	if err != nil {
		return IntegratedCandidate{}, supervisionOperationError(ctx, heartbeatErrors, "claim candidate integration", err)
	}
	outcome.Candidate = candidate
	outcome.Integration = integration

	failClaim := func(cause error, retryPrepared bool) (IntegratedCandidate, error) {
		cleanupCtx, cleanupCancel := context.WithTimeout(context.Background(), 5*time.Second)
		defer cleanupCancel()
		failErr := store.failClaimedIntegration(cleanupCtx, integration, candidate, cause, retryPrepared)
		return outcome, errors.Join(cause, failErr)
	}
	workspace, err := store.GetWorkspace(lifecycleCtx, candidate.WorkspaceID)
	if err != nil {
		return failClaim(err, false)
	}
	if err := validateCandidateGitBinding(lifecycleCtx, canonical, candidate, workspace); err != nil {
		return failClaim(err, false)
	}
	targetRoot, err := checkedOutTargetWorktree(lifecycleCtx, canonical, candidate.TargetRef)
	if err != nil {
		return failClaim(err, true)
	}
	targetBefore, err := validateTargetWorktreeReady(lifecycleCtx, targetRoot, candidate.TargetRef)
	if err != nil {
		return failClaim(err, true)
	}
	integration, err = store.startCandidateIntegration(lifecycleCtx, integration, targetBefore)
	if err != nil {
		return failClaim(supervisionOperationError(ctx, heartbeatErrors, "start candidate integration", err), true)
	}
	outcome.Integration = integration

	targetAfter, conflicted, mergeErr := mergeCandidateIntoTarget(
		lifecycleCtx,
		canonical,
		targetRoot,
		candidate,
		targetBefore,
	)
	if mergeErr != nil {
		return failClaim(mergeErr, false)
	}
	status := ResultIntegrated
	reason := "candidate integrated"
	if conflicted {
		status = ResultConflicted
		reason = "candidate conflicts with current target"
	}
	outcome, err = store.completeCandidateIntegration(
		lifecycleCtx,
		integration,
		candidate,
		targetBefore,
		targetAfter,
		status,
		reason,
	)
	if err != nil {
		return failClaim(supervisionOperationError(ctx, heartbeatErrors, "complete candidate integration", err), false)
	}
	return outcome, nil
}

func withIntegrationDefaults(params IntegrateNextParams) IntegrateNextParams {
	if params.HeartbeatInterval <= 0 {
		params.HeartbeatInterval = defaultSupervisorHeartbeatInterval
	}
	if params.SupervisorStaleAfter <= 0 {
		params.SupervisorStaleAfter = defaultSupervisorStaleAfter
	}
	return params
}

func (store *Store) claimNextCandidate(
	ctx context.Context,
	targetRef string,
) (Candidate, CandidateIntegration, error) {
	transaction, err := store.db.BeginTx(ctx, nil)
	if err != nil {
		return Candidate{}, CandidateIntegration{}, fmt.Errorf("begin candidate integration claim: %w", err)
	}
	defer func() { _ = transaction.Rollback() }()
	if err := requireActiveSupervisorTx(ctx, transaction, store.ownerEpoch); err != nil {
		return Candidate{}, CandidateIntegration{}, err
	}
	var liveCount int
	if err := transaction.QueryRowContext(ctx, `
		SELECT COUNT(*) FROM candidate_integrations
		WHERE target_ref = ? AND status IN (?, ?, ?)
	`, targetRef, IntegrationPrepared, IntegrationExecuting, IntegrationOutcomeUnknown).Scan(&liveCount); err != nil {
		return Candidate{}, CandidateIntegration{}, fmt.Errorf("inspect target integration claim: %w", err)
	}
	if liveCount != 0 {
		return Candidate{}, CandidateIntegration{}, fmt.Errorf("%w: %s", ErrIntegrationBusy, targetRef)
	}
	row := transaction.QueryRowContext(ctx, candidateSelectSQL+`
		WHERE target_ref = ? AND status = ?
		ORDER BY created_at_ms, candidate_id
		LIMIT 1
	`, targetRef, CandidateQueued)
	candidate, err := scanCandidate(row)
	if errors.Is(err, sql.ErrNoRows) {
		return Candidate{}, CandidateIntegration{}, fmt.Errorf("%w: no queued candidate for %s", ErrNoCandidate, targetRef)
	}
	if err != nil {
		return Candidate{}, CandidateIntegration{}, fmt.Errorf("select queued candidate: %w", err)
	}
	nowMS := time.Now().UTC().UnixMilli()
	result, err := transaction.ExecContext(ctx, `
		UPDATE candidates
		SET status = ?, revision = revision + 1, updated_at_ms = ?
		WHERE candidate_id = ? AND revision = ? AND status = ?
	`, CandidateIntegrating, nowMS, candidate.CandidateID, candidate.Revision, CandidateQueued)
	if err != nil {
		return Candidate{}, CandidateIntegration{}, fmt.Errorf("claim candidate: %w", err)
	}
	if err := requireOneCASRow(result, ErrIntegrationBusy, "claim candidate"); err != nil {
		return Candidate{}, CandidateIntegration{}, err
	}
	candidate.Status = CandidateIntegrating
	candidate.Revision++
	candidate.UpdatedAtMS = nowMS
	integration := CandidateIntegration{
		IntegrationID: supervisedAggregateID("integration", candidate.CandidateID, candidate.Revision),
		CandidateID:   candidate.CandidateID,
		TargetRef:     candidate.TargetRef,
		OwnerEpoch:    store.ownerEpoch,
		Status:        IntegrationPrepared,
		Revision:      1,
		CreatedAtMS:   nowMS,
		UpdatedAtMS:   nowMS,
	}
	_, err = transaction.ExecContext(ctx, `
		INSERT INTO candidate_integrations (
			integration_id, candidate_id, target_ref, owner_epoch, status,
			target_before, target_after, reason, revision, created_at_ms, updated_at_ms
		) VALUES (?, ?, ?, ?, ?, '', '', '', ?, ?, ?)
	`, integration.IntegrationID, integration.CandidateID, integration.TargetRef,
		integration.OwnerEpoch, integration.Status, integration.Revision,
		integration.CreatedAtMS, integration.UpdatedAtMS)
	if err != nil {
		if isUniqueConstraintError(err) {
			return Candidate{}, CandidateIntegration{}, fmt.Errorf("%w: %s", ErrIntegrationBusy, targetRef)
		}
		return Candidate{}, CandidateIntegration{}, fmt.Errorf("insert candidate integration: %w", err)
	}
	if err := transaction.Commit(); err != nil {
		return Candidate{}, CandidateIntegration{}, fmt.Errorf("commit candidate integration claim: %w", err)
	}
	return candidate, integration, nil
}

func (store *Store) startCandidateIntegration(
	ctx context.Context,
	integration CandidateIntegration,
	targetBefore string,
) (CandidateIntegration, error) {
	if !validGitObjectID(targetBefore) {
		return CandidateIntegration{}, fmt.Errorf("%w: target_before is invalid", ErrCandidateBinding)
	}
	transaction, err := store.db.BeginTx(ctx, nil)
	if err != nil {
		return CandidateIntegration{}, fmt.Errorf("begin candidate integration execution: %w", err)
	}
	defer func() { _ = transaction.Rollback() }()
	if err := requireActiveSupervisorTx(ctx, transaction, store.ownerEpoch); err != nil {
		return CandidateIntegration{}, err
	}
	nowMS := time.Now().UTC().UnixMilli()
	result, err := transaction.ExecContext(ctx, `
		UPDATE candidate_integrations
		SET status = ?, target_before = ?, revision = revision + 1, updated_at_ms = ?
		WHERE integration_id = ? AND candidate_id = ? AND target_ref = ?
		  AND owner_epoch = ? AND revision = ? AND status = ?
	`, IntegrationExecuting, targetBefore, nowMS,
		integration.IntegrationID, integration.CandidateID, integration.TargetRef,
		store.ownerEpoch, integration.Revision, IntegrationPrepared)
	if err != nil {
		return CandidateIntegration{}, fmt.Errorf("start candidate integration: %w", err)
	}
	if err := requireOneCASRow(result, ErrStaleFence, "start candidate integration"); err != nil {
		return CandidateIntegration{}, err
	}
	integration.Status = IntegrationExecuting
	integration.TargetBefore = targetBefore
	integration.Revision++
	integration.UpdatedAtMS = nowMS
	if err := transaction.Commit(); err != nil {
		return CandidateIntegration{}, fmt.Errorf("commit candidate integration execution: %w", err)
	}
	return integration, nil
}

func (store *Store) completeCandidateIntegration(
	ctx context.Context,
	integration CandidateIntegration,
	candidate Candidate,
	targetBefore string,
	targetAfter string,
	status ResultStatus,
	reason string,
) (IntegratedCandidate, error) {
	if status != ResultIntegrated && status != ResultConflicted {
		return IntegratedCandidate{}, fmt.Errorf("%w: unsupported result status %q", ErrInvalidArgument, status)
	}
	if !validGitObjectID(targetBefore) || !validGitObjectID(targetAfter) || strings.TrimSpace(reason) == "" {
		return IntegratedCandidate{}, fmt.Errorf("%w: completion Git identity and reason are required", ErrInvalidArgument)
	}
	transaction, err := store.db.BeginTx(ctx, nil)
	if err != nil {
		return IntegratedCandidate{}, fmt.Errorf("begin candidate integration completion: %w", err)
	}
	defer func() { _ = transaction.Rollback() }()
	if err := requireActiveSupervisorTx(ctx, transaction, store.ownerEpoch); err != nil {
		return IntegratedCandidate{}, err
	}
	nowMS := time.Now().UTC().UnixMilli()
	integrationStatus := IntegrationSucceeded
	candidateStatus := CandidateIntegrated
	if status == ResultConflicted {
		integrationStatus = IntegrationConflicted
		candidateStatus = CandidateConflicted
	}
	result, err := transaction.ExecContext(ctx, `
		UPDATE candidate_integrations
		SET status = ?, target_after = ?, reason = ?, revision = revision + 1, updated_at_ms = ?
		WHERE integration_id = ? AND candidate_id = ? AND target_ref = ?
		  AND owner_epoch = ? AND revision = ? AND status = ? AND target_before = ?
	`, integrationStatus, targetAfter, reason, nowMS,
		integration.IntegrationID, candidate.CandidateID, candidate.TargetRef,
		store.ownerEpoch, integration.Revision, IntegrationExecuting, targetBefore)
	if err != nil {
		return IntegratedCandidate{}, fmt.Errorf("complete candidate integration journal: %w", err)
	}
	if err := requireOneCASRow(result, ErrStaleFence, "complete candidate integration journal"); err != nil {
		return IntegratedCandidate{}, err
	}
	result, err = transaction.ExecContext(ctx, `
		UPDATE candidates
		SET status = ?, revision = revision + 1, updated_at_ms = ?
		WHERE candidate_id = ? AND revision = ? AND status = ?
	`, candidateStatus, nowMS, candidate.CandidateID, candidate.Revision, CandidateIntegrating)
	if err != nil {
		return IntegratedCandidate{}, fmt.Errorf("complete candidate: %w", err)
	}
	if err := requireOneCASRow(result, ErrRevisionConflict, "complete candidate"); err != nil {
		return IntegratedCandidate{}, err
	}
	candidate.Status = candidateStatus
	candidate.Revision++
	candidate.UpdatedAtMS = nowMS
	integration.Status = integrationStatus
	integration.TargetAfter = targetAfter
	integration.Reason = reason
	integration.Revision++
	integration.UpdatedAtMS = nowMS
	resultRecord := Result{
		ResultID:      supervisedAggregateID("result", candidate.CandidateID, 1),
		IntegrationID: integration.IntegrationID,
		CandidateID:   candidate.CandidateID,
		RunID:         candidate.RunID,
		TargetRef:     candidate.TargetRef,
		TargetBefore:  targetBefore,
		TargetAfter:   targetAfter,
		Status:        status,
		Reason:        reason,
		CreatedAtMS:   nowMS,
	}
	_, err = transaction.ExecContext(ctx, `
		INSERT INTO results (
			result_id, integration_id, candidate_id, run_id, target_ref,
			target_before, target_after, status, reason, created_at_ms
		) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
	`, resultRecord.ResultID, resultRecord.IntegrationID, resultRecord.CandidateID,
		resultRecord.RunID, resultRecord.TargetRef, resultRecord.TargetBefore,
		resultRecord.TargetAfter, resultRecord.Status, resultRecord.Reason,
		resultRecord.CreatedAtMS)
	if err != nil {
		return IntegratedCandidate{}, fmt.Errorf("insert immutable integration result: %w", err)
	}
	if err := transaction.Commit(); err != nil {
		return IntegratedCandidate{}, fmt.Errorf("commit candidate integration completion: %w", err)
	}
	return IntegratedCandidate{Candidate: candidate, Integration: integration, Result: resultRecord}, nil
}

func (store *Store) failClaimedIntegration(
	ctx context.Context,
	integration CandidateIntegration,
	candidate Candidate,
	cause error,
	retryPrepared bool,
) error {
	if integration.IntegrationID == "" || candidate.CandidateID == "" {
		return nil
	}
	transaction, err := store.db.BeginTx(ctx, nil)
	if err != nil {
		return fmt.Errorf("begin failed candidate integration closeout: %w", err)
	}
	defer func() { _ = transaction.Rollback() }()
	if err := requireActiveSupervisorTx(ctx, transaction, store.ownerEpoch); err != nil {
		return err
	}
	nowMS := time.Now().UTC().UnixMilli()
	integrationStatus := IntegrationFailed
	candidateStatus := CandidateConflicted
	if integration.Status == IntegrationExecuting {
		integrationStatus = IntegrationOutcomeUnknown
		candidateStatus = CandidateIntegrating
	} else if retryPrepared {
		candidateStatus = CandidateQueued
	}
	result, err := transaction.ExecContext(ctx, `
		UPDATE candidate_integrations
		SET status = ?, reason = ?, revision = revision + 1, updated_at_ms = ?
		WHERE integration_id = ? AND owner_epoch = ? AND revision = ?
		  AND status IN (?, ?)
	`, integrationStatus, strings.TrimSpace(cause.Error()), nowMS,
		integration.IntegrationID, store.ownerEpoch, integration.Revision,
		IntegrationPrepared, IntegrationExecuting)
	if err != nil {
		return fmt.Errorf("fail candidate integration journal: %w", err)
	}
	if err := requireOneCASRow(result, ErrStaleFence, "fail candidate integration journal"); err != nil {
		return err
	}
	result, err = transaction.ExecContext(ctx, `
		UPDATE candidates
		SET status = ?, revision = revision + 1, updated_at_ms = ?
		WHERE candidate_id = ? AND revision = ? AND status = ?
	`, candidateStatus, nowMS, candidate.CandidateID, candidate.Revision, CandidateIntegrating)
	if err != nil {
		return fmt.Errorf("close failed candidate integration: %w", err)
	}
	if err := requireOneCASRow(result, ErrRevisionConflict, "close failed candidate integration"); err != nil {
		return err
	}
	if err := transaction.Commit(); err != nil {
		return fmt.Errorf("commit failed candidate integration closeout: %w", err)
	}
	return nil
}

func validateCandidateGitBinding(
	ctx context.Context,
	repository Repository,
	candidate Candidate,
	workspace Workspace,
) error {
	if candidate.Status != CandidateIntegrating || workspace.Status != WorkspaceSealed ||
		candidate.RunID != workspace.RunID || candidate.WorkspaceID != workspace.WorkspaceID ||
		candidate.WorkspaceGeneration != workspace.Generation || candidate.TargetRef != workspace.BaseRef ||
		candidate.BaseCommit != workspace.BaseCommit || candidate.PrivateRef != workspace.PrivateRef ||
		!sameFilesystemPath(workspace.RepoCommonDir, repository.CommonDir) {
		return fmt.Errorf("%w: candidate no longer matches its sealed workspace", ErrCandidateBinding)
	}
	if err := validateOwnedWorkspacePath(repository.PrimaryRoot, workspace.RootPath); err != nil {
		return fmt.Errorf("%w: %v", ErrCandidateBinding, err)
	}
	privateCommit, exists, err := resolveOptionalGitCommit(ctx, repository.Root, candidate.PrivateRef)
	if err != nil || !exists || privateCommit != candidate.HeadCommit {
		return fmt.Errorf("%w: private ref %q moved from %s", ErrCandidateBinding, candidate.PrivateRef, candidate.HeadCommit)
	}
	if err := requireGitAncestor(ctx, repository.Root, candidate.BaseCommit, candidate.HeadCommit); err != nil {
		return fmt.Errorf("%w: candidate head does not descend from base: %v", ErrCandidateBinding, err)
	}
	return nil
}

func checkedOutTargetWorktree(
	ctx context.Context,
	repository Repository,
	targetRef string,
) (string, error) {
	output, err := runGitBytes(ctx, repository.Root, "worktree", "list", "--porcelain", "-z")
	if err != nil {
		return "", err
	}
	var root string
	for _, field := range bytes.Split(output, []byte{0}) {
		value := string(field)
		switch {
		case strings.HasPrefix(value, "worktree "):
			root = strings.TrimPrefix(value, "worktree ")
		case strings.HasPrefix(value, "branch ") && strings.TrimPrefix(value, "branch ") == targetRef:
			if root == "" {
				return "", fmt.Errorf("%w: Git worktree record has no root", ErrCandidateBinding)
			}
			absolute, absoluteErr := filepath.Abs(filepath.FromSlash(root))
			if absoluteErr != nil {
				return "", absoluteErr
			}
			return filepath.Clean(absolute), nil
		case value == "":
			root = ""
		}
	}
	return "", fmt.Errorf("%w: target ref %q is not checked out in a worktree", ErrCandidateBinding, targetRef)
}

func validateTargetWorktreeReady(ctx context.Context, targetRoot, targetRef string) (string, error) {
	branch, err := runGitOutput(ctx, targetRoot, "symbolic-ref", "HEAD")
	if err != nil || branch != targetRef {
		return "", fmt.Errorf("%w: target worktree is not attached to %q", ErrCandidateBinding, targetRef)
	}
	mergeHead, exists, err := resolveOptionalGitCommit(ctx, targetRoot, "MERGE_HEAD")
	if err != nil {
		return "", fmt.Errorf("inspect target merge state: %w", err)
	}
	if exists {
		return "", fmt.Errorf("%w: target worktree has unfinished merge %s", ErrTargetWorktreeDirty, mergeHead)
	}
	status, err := runGitStdout(ctx, targetRoot, "status", "--porcelain", "--untracked-files=no")
	if err != nil {
		return "", err
	}
	if strings.TrimSpace(status) != "" {
		return "", fmt.Errorf("%w: %s", ErrTargetWorktreeDirty, targetRoot)
	}
	return resolveGitCommit(ctx, targetRoot, "HEAD")
}

func mergeCandidateIntoTarget(
	ctx context.Context,
	repository Repository,
	targetRoot string,
	candidate Candidate,
	targetBefore string,
) (string, bool, error) {
	if requireGitAncestor(ctx, repository.Root, candidate.HeadCommit, targetBefore) == nil {
		return targetBefore, false, nil
	}
	hooksPath := filepath.Join(repository.CommonDir, "specify-runtime", "disabled-hooks")
	if err := os.MkdirAll(hooksPath, 0o700); err != nil {
		return "", false, fmt.Errorf("create disabled Git hooks directory: %w", err)
	}
	arguments := []string{
		"-c", "core.hooksPath=" + hooksPath,
		"-c", "user.name=Spec Kit Plus",
		"-c", "user.email=spec-kit-plus@invalid",
		"-c", "commit.gpgsign=false",
		"merge",
	}
	if requireGitAncestor(ctx, repository.Root, targetBefore, candidate.HeadCommit) == nil {
		arguments = append(arguments, "--ff-only", "--no-edit", candidate.HeadCommit)
	} else {
		arguments = append(
			arguments,
			"--no-ff", "--no-edit", "--no-verify",
			"-m", "Integrate SP Run "+candidate.RunID+" ("+candidate.CandidateID+")",
			candidate.HeadCommit,
		)
	}
	_, mergeErr := runGitBytes(ctx, targetRoot, arguments...)
	if mergeErr != nil {
		_, hasMergeHead, inspectErr := resolveOptionalGitCommit(context.Background(), targetRoot, "MERGE_HEAD")
		if inspectErr != nil {
			return "", false, errors.Join(mergeErr, inspectErr)
		}
		if hasMergeHead {
			abortErr := runGitMutationWithRetry(context.Background(), targetRoot, "merge", "--abort")
			if abortErr != nil {
				return "", false, errors.Join(mergeErr, fmt.Errorf("abort conflicted target merge: %w", abortErr))
			}
			current, currentErr := resolveGitCommit(context.Background(), targetRoot, "HEAD")
			if currentErr != nil || current != targetBefore {
				return "", false, errors.Join(mergeErr, fmt.Errorf("target did not return to pre-merge commit %s", targetBefore))
			}
			return targetBefore, true, nil
		}
		return "", false, mergeErr
	}
	targetAfter, err := resolveGitCommit(ctx, targetRoot, "HEAD")
	if err != nil {
		return "", false, err
	}
	if err := requireGitAncestor(ctx, targetRoot, candidate.HeadCommit, targetAfter); err != nil {
		return "", false, fmt.Errorf("%w: integrated target does not contain candidate head", ErrCandidateBinding)
	}
	return targetAfter, false, nil
}

func runGitBytes(ctx context.Context, directory string, arguments ...string) ([]byte, error) {
	command := exec.CommandContext(ctx, "git", arguments...)
	command.Dir = directory
	output, err := command.CombinedOutput()
	if err != nil {
		if contextErr := ctx.Err(); contextErr != nil {
			return output, contextErr
		}
		return output, fmt.Errorf("git %s failed: %w: %s", strings.Join(arguments, " "), err, strings.TrimSpace(string(output)))
	}
	return output, nil
}

func (store *Store) GetResultForCandidate(ctx context.Context, candidateID string) (Result, error) {
	row := store.db.QueryRowContext(ctx, `
		SELECT result_id, integration_id, candidate_id, run_id, target_ref,
		       target_before, target_after, status, reason, created_at_ms
		FROM results WHERE candidate_id = ?
	`, candidateID)
	var result Result
	err := row.Scan(
		&result.ResultID,
		&result.IntegrationID,
		&result.CandidateID,
		&result.RunID,
		&result.TargetRef,
		&result.TargetBefore,
		&result.TargetAfter,
		&result.Status,
		&result.Reason,
		&result.CreatedAtMS,
	)
	if errors.Is(err, sql.ErrNoRows) {
		return Result{}, fmt.Errorf("%w: result for candidate %q", ErrResultNotFound, candidateID)
	}
	return result, err
}
