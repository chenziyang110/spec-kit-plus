package runcontrol

import (
	"context"
	"crypto/sha256"
	"database/sql"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"os"
	"os/exec"
	"strconv"
	"strings"
	"time"
)

const (
	defaultSupervisorHeartbeatInterval = 5 * time.Second
	defaultAttemptLeaseDuration        = 30 * time.Second
	defaultSupervisorStaleAfter        = 30 * time.Second
	attemptLaunchDatabaseOperations    = 4
)

// initialAttemptLeaseDuration covers the serialized Issue, BeginLaunch,
// CompleteLaunch, and Activate database operations. Once activation succeeds,
// ActivateAttempt replaces this grace period with the active heartbeat lease.
func initialAttemptLeaseDuration(activeLease time.Duration) time.Duration {
	launchGrace := attemptLaunchDatabaseOperations * time.Duration(sqliteBusyTimeoutMS) * time.Millisecond
	return activeLease + launchGrace
}

// SuperviseRunParams describes one tokenized child process. Argv is passed
// directly to the operating system; it is never joined into shell text.
type SuperviseRunParams struct {
	RunID                string
	AdapterID            string
	Argv                 []string
	ChildStdin           io.Reader
	ChildStdout          io.Writer
	ChildStderr          io.Writer
	HeartbeatInterval    time.Duration
	LeaseDuration        time.Duration
	SupervisorStaleAfter time.Duration
	OwnerEpoch           string
}

// SupervisedRun is the durable terminal execution observed after the managed
// child exits. A nonzero ExitCode is a successfully recorded failed Run, not a
// supervisor infrastructure error.
type SupervisedRun struct {
	Run       Run
	Attempt   Attempt
	Activity  Activity
	Workspace Workspace
	Candidate Candidate
	ExitCode  int
}

// SuperviseRun owns the complete foreground lifecycle: stale-owner recovery,
// Run claim, isolated Git worktree allocation, forced child cwd, heartbeats,
// and atomic terminal closeout. The Store remains open for the child's entire
// lifetime and its Close path fences any incomplete execution.
func SuperviseRun(
	ctx context.Context,
	repository Repository,
	params SuperviseRunParams,
) (result SupervisedRun, returnErr error) {
	params = withSupervisionDefaults(params)
	if err := validateSuperviseRunParams(repository, params); err != nil {
		return SupervisedRun{}, err
	}

	options := make([]OpenOption, 0, 1)
	if params.OwnerEpoch != "" {
		options = append(options, WithOwnerEpoch(params.OwnerEpoch))
	}
	store, err := Open(ctx, repository.DatabasePath, options...)
	if err != nil {
		return SupervisedRun{}, err
	}
	defer func() {
		if closeErr := store.Close(); closeErr != nil {
			returnErr = errors.Join(returnErr, closeErr)
		}
	}()

	now := time.Now().UTC()
	if _, err := store.ReconcileStaleSupervisors(ctx, now, now.Add(-params.SupervisorStaleAfter)); err != nil {
		return SupervisedRun{}, fmt.Errorf("reconcile stale supervisors: %w", err)
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

	run, err := store.GetRun(lifecycleCtx, params.RunID)
	if err != nil {
		return SupervisedRun{}, supervisionOperationError(ctx, heartbeatErrors, "load run", err)
	}
	claimed, err := store.ClaimRun(lifecycleCtx, run.RunID, run.Revision)
	if err != nil {
		return SupervisedRun{}, supervisionOperationError(ctx, heartbeatErrors, "claim run", err)
	}
	activity, err := prepareSupervisedActivity(lifecycleCtx, store, claimed)
	if err != nil {
		return SupervisedRun{}, supervisionOperationError(ctx, heartbeatErrors, "prepare activity", err)
	}
	generation, err := nextWorkspaceGeneration(lifecycleCtx, store, claimed.RunID)
	if err != nil {
		return SupervisedRun{}, supervisionOperationError(ctx, heartbeatErrors, "allocate workspace generation", err)
	}
	workspacePlan, err := PlanGitWorkspace(lifecycleCtx, repository, claimed, generation)
	if err != nil {
		return SupervisedRun{}, supervisionOperationError(ctx, heartbeatErrors, "plan Git workspace", err)
	}
	workspace, err := store.CreateWorkspace(lifecycleCtx, workspacePlan)
	if err != nil {
		return SupervisedRun{}, supervisionOperationError(ctx, heartbeatErrors, "record Git workspace", err)
	}

	allocationID := supervisedAggregateID("allocation", claimed.RunID, generation)
	allocationDigest, err := supervisedRequestDigest(struct {
		RunRevision       int64                 `json:"run_revision"`
		WorkspaceRevision int64                 `json:"workspace_revision"`
		Plan              CreateWorkspaceParams `json:"plan"`
	}{RunRevision: claimed.Revision, WorkspaceRevision: workspace.Revision, Plan: workspacePlan})
	if err != nil {
		return SupervisedRun{}, err
	}
	allocation, _, err := store.BeginWorkspaceAllocation(lifecycleCtx, BeginWorkspaceAllocationParams{
		AllocationID:              allocationID,
		RunID:                     claimed.RunID,
		WorkspaceID:               workspace.WorkspaceID,
		ExpectedRunRevision:       claimed.Revision,
		ExpectedWorkspaceRevision: workspace.Revision,
		IdempotencyKey:            "workspace-allocation/" + workspace.WorkspaceID,
		RequestSHA256:             allocationDigest,
	})
	if err != nil {
		return SupervisedRun{}, supervisionOperationError(ctx, heartbeatErrors, "journal workspace allocation", err)
	}
	allocation, err = store.StartWorkspaceAllocation(lifecycleCtx, allocation.AllocationID, allocation.Revision)
	if err != nil {
		return SupervisedRun{}, supervisionOperationError(ctx, heartbeatErrors, "start workspace allocation", err)
	}
	if _, err := MaterializeGitWorkspace(lifecycleCtx, repository, workspace); err != nil {
		return SupervisedRun{}, supervisionOperationError(ctx, heartbeatErrors, "materialize Git workspace", err)
	}
	allocation, prepared, err := store.CompleteWorkspaceAllocation(lifecycleCtx, CompleteWorkspaceAllocationParams{
		AllocationID:               allocation.AllocationID,
		ExpectedAllocationRevision: allocation.Revision,
		Execution: PrepareExecutionParams{
			RunID:                     claimed.RunID,
			ActivityID:                activity.ActivityID,
			WorkspaceID:               workspace.WorkspaceID,
			ExpectedRunRevision:       claimed.Revision,
			ExpectedActivityRevision:  activity.Revision,
			ExpectedWorkspaceRevision: workspace.Revision,
		},
	})
	if err != nil {
		return SupervisedRun{}, supervisionOperationError(ctx, heartbeatErrors, "complete workspace allocation", err)
	}
	_ = allocation

	attempt, err := store.IssueAttempt(lifecycleCtx, IssueAttemptParams{
		AttemptID:                 supervisedAggregateID("attempt", claimed.RunID, generation),
		RunID:                     prepared.Run.RunID,
		ActivityID:                prepared.Activity.ActivityID,
		WorkspaceID:               prepared.Workspace.WorkspaceID,
		ExpectedRunRevision:       prepared.Run.Revision,
		ExpectedActivityRevision:  prepared.Activity.Revision,
		ExpectedWorkspaceRevision: prepared.Workspace.Revision,
		AdapterID:                 params.AdapterID,
		ExecutionMode:             ExecutionManaged,
		LeaseUntil:                time.Now().UTC().Add(initialAttemptLeaseDuration(params.LeaseDuration)),
	})
	if err != nil {
		return SupervisedRun{}, supervisionOperationError(ctx, heartbeatErrors, "issue attempt", err)
	}
	result = SupervisedRun{
		Run:       prepared.Run,
		Attempt:   attempt,
		Activity:  prepared.Activity,
		Workspace: prepared.Workspace,
		ExitCode:  -1,
	}

	launchDigest, err := supervisedRequestDigest(struct {
		Argv []string `json:"argv"`
		Cwd  string   `json:"cwd"`
	}{Argv: params.Argv, Cwd: prepared.Workspace.RootPath})
	if err != nil {
		return result, err
	}
	launch, _, err := store.BeginAttemptLaunch(lifecycleCtx, BeginAttemptLaunchParams{
		OperationID:    supervisedAggregateID("launch", claimed.RunID, generation),
		AttemptID:      attempt.AttemptID,
		Fence:          attempt.Fence,
		IdempotencyKey: "attempt-launch/" + attempt.AttemptID,
		RequestSHA256:  launchDigest,
	})
	if err != nil {
		return result, supervisionOperationError(ctx, heartbeatErrors, "claim child launch", err)
	}

	childCtx, cancelChild := context.WithCancel(lifecycleCtx)
	defer cancelChild()
	command := exec.CommandContext(childCtx, params.Argv[0], params.Argv[1:]...)
	command.Dir = prepared.Workspace.RootPath
	command.Env = append(os.Environ(), supervisedRunEnvironment(
		prepared.Run,
		attempt,
		prepared.Workspace,
	)...)
	command.Stdin = params.ChildStdin
	command.Stdout = params.ChildStdout
	command.Stderr = params.ChildStderr
	if err := command.Start(); err != nil {
		cleanupCtx, cleanupCancel := context.WithTimeout(context.Background(), 5*time.Second)
		_, completionErr := store.CompleteAttemptLaunch(cleanupCtx, CompleteAttemptLaunchParams{
			OperationID:      launch.OperationID,
			Fence:            attempt.Fence,
			ExpectedRevision: launch.Revision,
			Succeeded:        false,
		})
		cleanupCancel()
		if completionErr != nil {
			return result, errors.Join(fmt.Errorf("start supervised child: %w", err), completionErr)
		}
		return result, supervisionOperationError(ctx, heartbeatErrors, "start supervised child", err)
	}
	waited := make(chan error, 1)
	go func() { waited <- command.Wait() }()
	stopAndWait := func() {
		cancelChild()
		<-waited
	}

	launch, err = store.CompleteAttemptLaunch(lifecycleCtx, CompleteAttemptLaunchParams{
		OperationID:      launch.OperationID,
		Fence:            attempt.Fence,
		ExpectedRevision: launch.Revision,
		Succeeded:        true,
	})
	if err != nil {
		stopAndWait()
		return result, supervisionOperationError(ctx, heartbeatErrors, "confirm child launch", err)
	}
	_ = launch
	attempt, err = store.ActivateAttempt(
		lifecycleCtx,
		attempt.AttemptID,
		attempt.Fence,
		time.Now().UTC().Add(params.LeaseDuration),
	)
	if err != nil {
		stopAndWait()
		return result, supervisionOperationError(ctx, heartbeatErrors, "activate attempt", err)
	}
	result.Attempt = attempt

	attemptTicker := time.NewTicker(params.HeartbeatInterval)
	defer attemptTicker.Stop()
	var waitErr error
	waitComplete := false
	for !waitComplete {
		select {
		case waitErr = <-waited:
			waitComplete = true
		case <-lifecycleCtx.Done():
			stopAndWait()
			return result, supervisionCancellationError(ctx, heartbeatErrors)
		case <-attemptTicker.C:
			attempt, err = store.Heartbeat(
				lifecycleCtx,
				attempt.AttemptID,
				attempt.Fence,
				time.Now().UTC().Add(params.LeaseDuration),
			)
			if err != nil {
				stopAndWait()
				return result, fmt.Errorf("heartbeat supervised attempt: %w", err)
			}
			result.Attempt = attempt
		}
	}

	exitCode := managedProcessExitCode(command, waitErr)
	outcome := AttemptOutcomeSucceeded
	reason := "managed process exited successfully"
	var candidateSnapshot *CandidateSnapshot
	if exitCode != 0 {
		outcome = AttemptOutcomeFailed
		reason = fmt.Sprintf("managed process exited with code %d", exitCode)
	} else {
		attempt, err = store.Heartbeat(
			lifecycleCtx,
			attempt.AttemptID,
			attempt.Fence,
			time.Now().UTC().Add(params.LeaseDuration),
		)
		if err != nil {
			return result, supervisionOperationError(ctx, heartbeatErrors, "renew candidate snapshot lease", err)
		}
		postprocessCtx, cancelPostprocess := context.WithCancel(lifecycleCtx)
		postprocessErrors, postprocessDone := superviseAttemptHeartbeat(
			postprocessCtx,
			cancelLifecycle,
			store,
			attempt.AttemptID,
			attempt.Fence,
			params.HeartbeatInterval,
			params.LeaseDuration,
		)
		activeWorkspace, workspaceErr := store.GetWorkspace(lifecycleCtx, attempt.WorkspaceID)
		if workspaceErr != nil {
			cancelPostprocess()
			<-postprocessDone
			return result, supervisionOperationError(ctx, heartbeatErrors, "load active candidate workspace", workspaceErr)
		}
		result.Workspace = activeWorkspace
		snapshot, snapshotErr := SnapshotGitCandidate(
			lifecycleCtx,
			repository,
			result.Run,
			attempt,
			result.Workspace,
		)
		cancelPostprocess()
		<-postprocessDone
		if snapshotErr != nil {
			return result, supervisionOperationError(ctx, heartbeatErrors, "snapshot candidate", snapshotErr)
		}
		select {
		case postprocessErr := <-postprocessErrors:
			return result, fmt.Errorf("heartbeat candidate snapshot: %w", postprocessErr)
		default:
		}
		candidateSnapshot = &snapshot
	}
	finished, err := store.FinishAttempt(lifecycleCtx, FinishAttemptParams{
		AttemptID: attempt.AttemptID,
		Fence:     attempt.Fence,
		Outcome:   outcome,
		Reason:    reason,
		Candidate: candidateSnapshot,
	})
	if err != nil {
		return result, supervisionOperationError(ctx, heartbeatErrors, "finish attempt", err)
	}
	return SupervisedRun{
		Run:       finished.Run,
		Attempt:   finished.Attempt,
		Activity:  finished.Activity,
		Workspace: finished.Workspace,
		Candidate: finished.Candidate,
		ExitCode:  exitCode,
	}, nil
}

func supervisedRunEnvironment(run Run, attempt Attempt, workspace Workspace) []string {
	environment := []string{
		"SPECIFY_RUN_MANAGED=1",
		"SPECIFY_RUN_ID=" + run.RunID,
		"SPECIFY_RUN_KIND=" + run.Kind,
		"SPECIFY_RUN_SUBJECT_TYPE=" + run.SubjectType,
		"SPECIFY_RUN_SUBJECT_ID=" + run.SubjectID,
		"SPECIFY_RUN_TARGET_REF=" + run.TargetRef,
		"SPECIFY_RUN_ATTEMPT_ID=" + attempt.AttemptID,
		"SPECIFY_RUN_FENCE=" + strconv.FormatInt(attempt.Fence, 10),
		"SPECIFY_RUN_WORKSPACE_ID=" + workspace.WorkspaceID,
		"SPECIFY_RUN_WORKSPACE_GENERATION=" + strconv.FormatInt(workspace.Generation, 10),
		"SPECIFY_RUN_WORKSPACE=" + workspace.RootPath,
		"SPECIFY_RUN_PRIVATE_REF=" + workspace.PrivateRef,
	}
	return append(environment, "WSLENV="+supervisedRunWSLEnv(os.Getenv("WSLENV")))
}

func supervisedRunWSLEnv(existing string) string {
	required := []string{
		"SPECIFY_RUN_MANAGED",
		"SPECIFY_RUN_ID",
		"SPECIFY_RUN_KIND",
		"SPECIFY_RUN_SUBJECT_TYPE",
		"SPECIFY_RUN_SUBJECT_ID",
		"SPECIFY_RUN_TARGET_REF",
		"SPECIFY_RUN_ATTEMPT_ID",
		"SPECIFY_RUN_FENCE",
		"SPECIFY_RUN_WORKSPACE_ID",
		"SPECIFY_RUN_WORKSPACE_GENERATION",
		"SPECIFY_RUN_WORKSPACE/p",
		"SPECIFY_RUN_PRIVATE_REF",
	}
	managed := make(map[string]struct{}, len(required))
	for _, entry := range required {
		managed[strings.SplitN(entry, "/", 2)[0]] = struct{}{}
	}
	entries := make([]string, 0, len(required)+4)
	for _, entry := range strings.Split(existing, ":") {
		entry = strings.TrimSpace(entry)
		if entry == "" {
			continue
		}
		name := strings.SplitN(entry, "/", 2)[0]
		if _, replaced := managed[name]; !replaced {
			entries = append(entries, entry)
		}
	}
	return strings.Join(append(entries, required...), ":")
}

func superviseAttemptHeartbeat(
	ctx context.Context,
	cancel context.CancelFunc,
	store *Store,
	attemptID string,
	fence int64,
	interval time.Duration,
	leaseDuration time.Duration,
) (<-chan error, <-chan struct{}) {
	errorsChannel := make(chan error, 1)
	done := make(chan struct{})
	go func() {
		defer close(done)
		ticker := time.NewTicker(interval)
		defer ticker.Stop()
		for {
			select {
			case <-ctx.Done():
				return
			case <-ticker.C:
				if _, err := store.Heartbeat(
					ctx,
					attemptID,
					fence,
					time.Now().UTC().Add(leaseDuration),
				); err != nil {
					if ctx.Err() != nil {
						return
					}
					errorsChannel <- err
					cancel()
					return
				}
			}
		}
	}()
	return errorsChannel, done
}

func withSupervisionDefaults(params SuperviseRunParams) SuperviseRunParams {
	if params.HeartbeatInterval <= 0 {
		params.HeartbeatInterval = defaultSupervisorHeartbeatInterval
	}
	if params.LeaseDuration <= 0 {
		params.LeaseDuration = defaultAttemptLeaseDuration
	}
	if params.SupervisorStaleAfter <= 0 {
		params.SupervisorStaleAfter = defaultSupervisorStaleAfter
	}
	if params.ChildStdout == nil {
		params.ChildStdout = io.Discard
	}
	if params.ChildStderr == nil {
		params.ChildStderr = io.Discard
	}
	return params
}

func validateSuperviseRunParams(repository Repository, params SuperviseRunParams) error {
	if strings.TrimSpace(repository.DatabasePath) == "" || strings.TrimSpace(repository.Root) == "" {
		return fmt.Errorf("%w: repository root and database path are required", ErrInvalidArgument)
	}
	if strings.TrimSpace(params.RunID) == "" || strings.TrimSpace(params.AdapterID) == "" {
		return fmt.Errorf("%w: run id and adapter id are required", ErrInvalidArgument)
	}
	if len(params.Argv) == 0 || strings.TrimSpace(params.Argv[0]) == "" {
		return fmt.Errorf("%w: a tokenized child argv is required", ErrInvalidArgument)
	}
	for _, argument := range params.Argv {
		if strings.ContainsRune(argument, '\x00') {
			return fmt.Errorf("%w: child argv cannot contain NUL", ErrInvalidArgument)
		}
	}
	if params.LeaseDuration <= 2*params.HeartbeatInterval {
		return fmt.Errorf("%w: lease duration must exceed two heartbeat intervals", ErrInvalidArgument)
	}
	contentionWindow := time.Duration(sqliteBusyTimeoutMS) * time.Millisecond
	if params.LeaseDuration <= contentionWindow {
		return fmt.Errorf("%w: lease duration must exceed the SQLite contention window", ErrInvalidArgument)
	}
	if params.SupervisorStaleAfter <= 2*params.HeartbeatInterval {
		return fmt.Errorf("%w: supervisor stale interval must exceed two heartbeat intervals", ErrInvalidArgument)
	}
	if params.SupervisorStaleAfter <= contentionWindow {
		return fmt.Errorf("%w: supervisor stale interval must exceed the SQLite contention window", ErrInvalidArgument)
	}
	return nil
}

func superviseOwnerHeartbeat(
	ctx context.Context,
	cancel context.CancelFunc,
	store *Store,
	interval time.Duration,
) (<-chan error, <-chan struct{}) {
	errorsChannel := make(chan error, 1)
	done := make(chan struct{})
	go func() {
		defer close(done)
		ticker := time.NewTicker(interval)
		defer ticker.Stop()
		for {
			select {
			case <-ctx.Done():
				return
			case <-ticker.C:
				if err := store.HeartbeatSupervisor(ctx, time.Now().UTC()); err != nil {
					if ctx.Err() != nil {
						return
					}
					errorsChannel <- err
					cancel()
					return
				}
			}
		}
	}()
	return errorsChannel, done
}

func supervisionOperationError(
	parent context.Context,
	heartbeatErrors <-chan error,
	stage string,
	operationErr error,
) error {
	if parent.Err() != nil {
		return parent.Err()
	}
	select {
	case heartbeatErr := <-heartbeatErrors:
		return fmt.Errorf("supervisor heartbeat failed during %s: %w", stage, heartbeatErr)
	default:
		return fmt.Errorf("%s: %w", stage, operationErr)
	}
}

func supervisionCancellationError(parent context.Context, heartbeatErrors <-chan error) error {
	if parent.Err() != nil {
		return parent.Err()
	}
	select {
	case heartbeatErr := <-heartbeatErrors:
		return fmt.Errorf("supervisor heartbeat failed: %w", heartbeatErr)
	default:
		return context.Canceled
	}
}

func prepareSupervisedActivity(ctx context.Context, store *Store, run Run) (Activity, error) {
	var activityID string
	err := store.db.QueryRowContext(ctx, `
		SELECT activity_id
		FROM activities
		WHERE run_id = ? AND status = ?
		ORDER BY ordinal DESC
		LIMIT 1
	`, run.RunID, ActivityInterrupted).Scan(&activityID)
	switch {
	case err == nil:
		return store.GetActivity(ctx, activityID)
	case !errors.Is(err, sql.ErrNoRows):
		return Activity{}, fmt.Errorf("read reusable activity for run %q: %w", run.RunID, err)
	default:
		return store.CreateActivity(ctx, CreateActivityParams{
			ActivityID:  supervisedAggregateID("activity", run.RunID, 0),
			RunID:       run.RunID,
			Kind:        run.Kind,
			InputSHA256: run.IntentSHA256,
		})
	}
}

func nextWorkspaceGeneration(ctx context.Context, store *Store, runID string) (int64, error) {
	var maximum int64
	if err := store.db.QueryRowContext(ctx, `
		SELECT COALESCE(MAX(generation), 0) FROM workspaces WHERE run_id = ?
	`, runID).Scan(&maximum); err != nil {
		return 0, fmt.Errorf("read workspace generation for run %q: %w", runID, err)
	}
	return maximum + 1, nil
}

func supervisedAggregateID(kind, runID string, generation int64) string {
	digest := sha256.Sum256([]byte(kind + "\x00" + runID + "\x00" + strconv.FormatInt(generation, 10)))
	suffix := hex.EncodeToString(digest[:10])
	if generation > 0 {
		return kind + "-" + suffix + "-g" + strconv.FormatInt(generation, 10)
	}
	return kind + "-" + suffix
}

func supervisedRequestDigest(value any) (string, error) {
	encoded, err := json.Marshal(value)
	if err != nil {
		return "", fmt.Errorf("encode supervised request digest: %w", err)
	}
	digest := sha256.Sum256(encoded)
	return hex.EncodeToString(digest[:]), nil
}

func managedProcessExitCode(command *exec.Cmd, waitErr error) int {
	if command.ProcessState != nil {
		return command.ProcessState.ExitCode()
	}
	var exitError *exec.ExitError
	if errors.As(waitErr, &exitError) {
		return exitError.ExitCode()
	}
	if waitErr == nil {
		return 0
	}
	return -1
}
