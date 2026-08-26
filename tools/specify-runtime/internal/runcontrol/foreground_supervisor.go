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
	"path/filepath"
	"runtime"
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
type SuperviseWorkParams struct {
	TaskRef      string
	Summary      string
	AgentID      string
	WriteIntents []WriteIntentSpec
}

type SuperviseRunParams struct {
	RunID                string
	AdapterID            string
	Work                 SuperviseWorkParams
	Argv                 []string
	ChildStdin           io.Reader
	ChildStdout          io.Writer
	ChildStderr          io.Writer
	HeartbeatInterval    time.Duration
	LeaseDuration        time.Duration
	SupervisorStaleAfter time.Duration
	OwnerEpoch           string
	WorkspacePolicy      WorkspacePolicy
}

// SupervisedRun is the durable terminal execution observed after the managed
// child exits. A nonzero ExitCode is a successfully recorded failed Run, not a
// supervisor infrastructure error.
type SupervisedRun struct {
	Run                 Run
	Attempt             Attempt
	Activity            Activity
	Workspace           Workspace
	Snapshot            Snapshot
	Attestation         WorkspaceAttestation
	Resources           RunResourceNamespace
	Result              RunResult
	Work                WorkItem
	FeatureBranchPolicy FeatureBranchPolicy
	ExitCode            int
}

// SuperviseRun owns the complete foreground lifecycle: stale-owner recovery,
// Run claim, authoritative workspace routing, forced child cwd, heartbeats,
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
	if _, err := store.ensureManagedAdapterCapability(ctx, params.AdapterID); err != nil {
		return SupervisedRun{}, fmt.Errorf("enforce managed adapter capability: %w", err)
	}

	now := time.Now().UTC()
	if _, err := store.ReconcileStaleSupervisors(ctx, now, now.Add(-params.SupervisorStaleAfter)); err != nil {
		return SupervisedRun{}, fmt.Errorf("reconcile stale supervisors: %w", err)
	}
	if _, err := store.ReconcileRepositoryWork(ctx, now); err != nil {
		return SupervisedRun{}, fmt.Errorf("reconcile expired Work Board items: %w", err)
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
	writeIntents, err := supervisedRunWriteIntents(run, params.Work.WriteIntents)
	if err != nil {
		return SupervisedRun{}, supervisionOperationError(ctx, heartbeatErrors, "validate modifying run write scope", err)
	}
	params.Work.WriteIntents = writeIntents
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
	workspacePlan, err := planSupervisedWorkspace(
		lifecycleCtx,
		store,
		repository,
		claimed,
		generation,
		params.WorkspacePolicy,
	)
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
	snapshot, snapshotEntries, err := prepareWorkspaceSnapshot(
		lifecycleCtx,
		store,
		repository,
		claimed,
		workspace,
	)
	if err != nil {
		return SupervisedRun{}, supervisionOperationError(ctx, heartbeatErrors, "prepare ambient Snapshot", err)
	}
	if workspace.Mode == WorkspaceModeIsolated {
		if err := ApplySnapshotAmbientToWorkspace(lifecycleCtx, repository, workspace, snapshot, snapshotEntries); err != nil {
			return SupervisedRun{}, supervisionOperationError(ctx, heartbeatErrors, "apply ambient Snapshot", err)
		}
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
	attestation, err := store.CreateWorkspaceAttestation(
		lifecycleCtx,
		repository,
		prepared.Run,
		prepared.Workspace,
		snapshot,
		[]string{prepared.Workspace.RootPath},
	)
	if err != nil {
		return SupervisedRun{}, supervisionOperationError(ctx, heartbeatErrors, "create workspace attestation", err)
	}
	automaticWork, err := beginAutomaticRunWork(
		lifecycleCtx,
		store,
		prepared.Run,
		prepared.Workspace,
		params.AdapterID,
		params.Work,
		time.Now().UTC().Add(initialAttemptLeaseDuration(params.LeaseDuration)),
	)
	if err != nil {
		return SupervisedRun{}, supervisionOperationError(ctx, heartbeatErrors, "register automatic work board item", err)
	}
	automaticWorkFinalized := false
	defer func() {
		if automaticWork.WorkID == "" || automaticWorkFinalized || returnErr == nil {
			return
		}
		interruptedWork, interruptErr := interruptAutomaticRunWork(
			store,
			automaticWork,
			"supervised run interrupted before terminal closeout",
		)
		if interruptErr == nil {
			automaticWork = interruptedWork
			return
		}
		returnErr = errors.Join(returnErr, interruptErr)
	}()
	branchDecision, err := store.ResolveFeatureBranchPolicy(lifecycleCtx, automaticWork.WorkID, time.Now().UTC())
	if err != nil {
		return SupervisedRun{}, supervisionOperationError(ctx, heartbeatErrors, "resolve feature branch policy", err)
	}

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
		Run:                 prepared.Run,
		Attempt:             attempt,
		Activity:            prepared.Activity,
		Workspace:           prepared.Workspace,
		Snapshot:            snapshot,
		Attestation:         attestation,
		Work:                automaticWork,
		FeatureBranchPolicy: branchDecision.Policy,
		ExitCode:            -1,
	}
	resources, err := prepareRunResourceNamespace(
		lifecycleCtx,
		store,
		repository,
		prepared.Run,
		attempt,
		prepared.Workspace,
		time.Now().UTC().Add(initialAttemptLeaseDuration(params.LeaseDuration)),
	)
	if err != nil {
		return result, supervisionOperationError(ctx, heartbeatErrors, "claim Run resources", err)
	}
	if err := verifyRunResourceNamespace(resources); err != nil {
		return result, supervisionOperationError(ctx, heartbeatErrors, "attest Run resources", err)
	}
	result.Resources = resources

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
		automaticWork,
		branchDecision.Policy,
	)...)
	command.Env = append(command.Env, supervisedResourceEnvironment(resources)...)
	command.Stdin = params.ChildStdin
	command.Stdout = params.ChildStdout
	command.Stderr = params.ChildStderr
	processes := newProcessTree()
	if err := processes.configure(command); err != nil {
		return result, supervisionOperationError(ctx, heartbeatErrors, "configure supervised process tree", err)
	}
	if err := processes.start(command); err != nil {
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
		_ = processes.terminate()
		cancelChild()
		<-waited
		_ = processes.close()
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
			if automaticWork.WorkID != "" {
				automaticWork, err = store.RenewWorkLease(
					lifecycleCtx,
					RenewWorkLeaseParams{
						WorkID: automaticWork.WorkID, Fence: automaticWork.Fence,
						LeaseUntil: time.Now().UTC().Add(params.LeaseDuration),
					},
				)
				if err != nil {
					stopAndWait()
					return result, fmt.Errorf("renew automatic Work Board lease: %w", err)
				}
				result.Work = automaticWork
			}
		}
	}
	if closeErr := processes.close(); closeErr != nil {
		return result, supervisionOperationError(ctx, heartbeatErrors, "close supervised process tree", closeErr)
	}

	exitCode := managedProcessExitCode(command, waitErr)
	outcome := AttemptOutcomeSucceeded
	reason := "managed process exited successfully"
	var sealedResultSnapshot *RunResultSnapshot
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
		if automaticWork.WorkID != "" {
			automaticWork, err = store.RenewWorkLease(lifecycleCtx, RenewWorkLeaseParams{
				WorkID: automaticWork.WorkID, Fence: automaticWork.Fence,
				LeaseUntil: time.Now().UTC().Add(params.LeaseDuration),
			})
			if err != nil {
				return result, supervisionOperationError(ctx, heartbeatErrors, "renew candidate Work Board lease", err)
			}
			result.Work = automaticWork
		}
		postprocessCtx, cancelPostprocess := context.WithCancel(lifecycleCtx)
		postprocessErrors, postprocessDone := superviseAttemptHeartbeat(
			postprocessCtx,
			cancelLifecycle,
			store,
			attempt.AttemptID,
			attempt.Fence,
			automaticWork.WorkID,
			automaticWork.Fence,
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
		resultRevision, revisionErr := store.nextRunResultRevision(lifecycleCtx, result.Run.RunID)
		if revisionErr != nil {
			cancelPostprocess()
			<-postprocessDone
			return result, supervisionOperationError(ctx, heartbeatErrors, "derive Result revision", revisionErr)
		}
		sealed, sealErr := SealRunResult(
			lifecycleCtx,
			repository,
			result.Run,
			attempt,
			result.Workspace,
			snapshot,
			snapshotEntries,
			attestation,
			resources,
			resultRevision,
		)
		cancelPostprocess()
		<-postprocessDone
		if sealErr != nil {
			return result, supervisionOperationError(ctx, heartbeatErrors, "seal Run Result", sealErr)
		}
		select {
		case postprocessErr := <-postprocessErrors:
			return result, fmt.Errorf("heartbeat candidate snapshot: %w", postprocessErr)
		default:
		}
		sealedResultSnapshot = &sealed
	}
	finished, err := store.FinishAttempt(lifecycleCtx, FinishAttemptParams{
		AttemptID: attempt.AttemptID,
		Fence:     attempt.Fence,
		Outcome:   outcome,
		Reason:    reason,
		Result:    sealedResultSnapshot,
	})
	if err != nil {
		return result, supervisionOperationError(ctx, heartbeatErrors, "finish attempt", err)
	}
	if automaticWork.WorkID != "" {
		observedPaths, observedErr := automaticRunObservedPaths(
			lifecycleCtx,
			store,
			finished,
		)
		if observedErr != nil {
			return result, supervisionOperationError(ctx, heartbeatErrors, "capture automatic work board paths", observedErr)
		}
		if len(observedPaths) != 0 {
			latestWork, _, getErr := store.GetWork(lifecycleCtx, automaticWork.WorkID)
			if getErr != nil {
				return result, supervisionOperationError(ctx, heartbeatErrors, "load automatic Work Board item", getErr)
			}
			if latestWork.Fence != automaticWork.Fence {
				return result, supervisionOperationError(ctx, heartbeatErrors, "load automatic Work Board item",
					fmt.Errorf("%w: work %q holds fence %d, received %d", ErrStaleFence,
						latestWork.WorkID, latestWork.Fence, automaticWork.Fence))
			}
			automaticWork = latestWork
			automaticWork, err = checkpointAutomaticRunWork(
				lifecycleCtx,
				store,
				automaticWork,
				extendAutomaticWorkLease(automaticWork, params.LeaseDuration),
				"supervised run reached terminal state",
				observedPaths,
			)
			if err != nil {
				return result, supervisionOperationError(ctx, heartbeatErrors, "checkpoint automatic work board item", err)
			}
		}
		if outcome == AttemptOutcomeFailed {
			automaticWork, err = blockAutomaticRunWork(lifecycleCtx, store, automaticWork, reason)
			if err != nil {
				return result, supervisionOperationError(ctx, heartbeatErrors, "block automatic Work Board item", err)
			}
		} else {
			latestWork, _, getErr := store.GetWork(lifecycleCtx, automaticWork.WorkID)
			if getErr != nil {
				return result, supervisionOperationError(ctx, heartbeatErrors, "load automatic Work Board item", getErr)
			}
			automaticWork = latestWork
			automaticWork, err = store.TransitionWork(lifecycleCtx, TransitionWorkParams{
				WorkID:           automaticWork.WorkID,
				ExpectedRevision: automaticWork.Revision,
				Fence:            automaticWork.Fence,
				Target:           WorkCompleted,
				Reason:           reason,
				NextAction:       "supervised run reached terminal state",
			})
			if err != nil {
				return result, supervisionOperationError(ctx, heartbeatErrors, "finish automatic work board item", err)
			}
		}
		automaticWorkFinalized = true
		result.Work = automaticWork
	}
	return SupervisedRun{
		Run:                 finished.Run,
		Attempt:             finished.Attempt,
		Activity:            finished.Activity,
		Workspace:           finished.Workspace,
		Snapshot:            snapshot,
		Attestation:         attestation,
		Resources:           resources,
		Result:              finished.Result,
		Work:                automaticWork,
		FeatureBranchPolicy: branchDecision.Policy,
		ExitCode:            exitCode,
	}, nil
}

func beginAutomaticRunWork(
	ctx context.Context,
	store *Store,
	run Run,
	workspace Workspace,
	adapterID string,
	requested SuperviseWorkParams,
	leaseUntil time.Time,
) (WorkItem, error) {
	taskRef := strings.TrimSpace(requested.TaskRef)
	if taskRef == "" {
		taskRef = strings.Trim(strings.TrimSpace(run.SubjectType)+":"+strings.TrimSpace(run.SubjectID), ":")
	}
	summary := strings.TrimSpace(requested.Summary)
	if summary == "" {
		summary = "managed run " + run.RunID + " (" + run.Kind + ")"
	}
	agentID := strings.TrimSpace(requested.AgentID)
	if agentID == "" {
		agentID = adapterID
	}
	writeIntents := append([]WriteIntentSpec(nil), requested.WriteIntents...)
	if len(writeIntents) == 0 {
		writeIntents = automaticRunWriteIntents(run)
	}
	params := BeginWorkParams{
		WorkID:        automaticRunWorkID(run.RunID, workspace.Generation),
		RunID:         run.RunID,
		TaskRef:       taskRef,
		Summary:       summary,
		AgentID:       agentID,
		AdapterID:     adapterID,
		WorkspaceRoot: workspace.RootPath,
		BaseCommit:    workspace.BaseCommit,
		NextAction:    "supervised child process running",
		LeaseUntil:    leaseUntil,
		WriteIntents:  writeIntents,
	}
	work, _, err := store.BeginWork(ctx, params)
	if err == nil {
		return work, nil
	}
	if !errors.Is(err, ErrAlreadyExists) {
		return WorkItem{}, err
	}
	existing, _, getErr := store.GetWork(ctx, params.WorkID)
	if getErr != nil {
		return WorkItem{}, getErr
	}
	if existing.Status != WorkInterrupted {
		return WorkItem{}, err
	}
	return store.ResumeWork(ctx, ResumeWorkParams{
		WorkID:           existing.WorkID,
		ExpectedRevision: existing.Revision,
		AgentID:          agentID,
		AdapterID:        adapterID,
		WorkspaceRoot:    workspace.RootPath,
		BaseCommit:       workspace.BaseCommit,
		NextAction:       "supervised child process resumed",
		LeaseUntil:       leaseUntil,
	})
}

func checkpointAutomaticRunWork(
	ctx context.Context,
	store *Store,
	work WorkItem,
	leaseUntil time.Time,
	nextAction string,
	observedPaths []string,
) (WorkItem, error) {
	return store.CheckpointWork(ctx, CheckpointWorkParams{
		WorkID:           work.WorkID,
		ExpectedRevision: work.Revision,
		Fence:            work.Fence,
		LeaseUntil:       leaseUntil,
		NextAction:       nextAction,
		ObservedPaths:    observedPaths,
	})
}

func interruptAutomaticRunWork(store *Store, work WorkItem, reason string) (WorkItem, error) {
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	latest, intents, err := store.GetWork(ctx, work.WorkID)
	if err != nil {
		return WorkItem{}, err
	}
	if latest.Fence != work.Fence {
		return WorkItem{}, fmt.Errorf("%w: work %q holds fence %d, received %d", ErrStaleFence,
			latest.WorkID, latest.Fence, work.Fence)
	}
	observedPaths, inspectErr := InspectWorkspaceChanges(ctx, latest.WorkspaceRoot)
	if inspectErr != nil {
		observedPaths = activeWorkIntentPaths(intents)
		reason = strings.TrimSpace(reason) + "; workspace unavailable, declared scopes preserved"
	}
	return store.InterruptWork(ctx, InterruptWorkParams{
		WorkID:           latest.WorkID,
		ExpectedRevision: latest.Revision,
		Fence:            latest.Fence,
		Reason:           reason,
		ObservedPaths:    observedPaths,
	})
}

func blockAutomaticRunWork(ctx context.Context, store *Store, work WorkItem, reason string) (WorkItem, error) {
	latest, _, err := store.GetWork(ctx, work.WorkID)
	if err != nil {
		return WorkItem{}, err
	}
	if latest.Fence != work.Fence {
		return WorkItem{}, fmt.Errorf("%w: work %q holds fence %d, received %d", ErrStaleFence,
			latest.WorkID, latest.Fence, work.Fence)
	}
	if latest.Status == WorkBlocked {
		return latest, nil
	}
	return store.TransitionWork(ctx, TransitionWorkParams{
		WorkID:           latest.WorkID,
		ExpectedRevision: latest.Revision,
		Fence:            latest.Fence,
		Target:           WorkBlocked,
		Reason:           reason,
		NextAction:       "inspect the failed managed run before resuming or abandoning its scope",
	})
}

func activeWorkIntentPaths(intents []WriteIntent) []string {
	paths := make([]string, 0, len(intents))
	for _, intent := range intents {
		if intent.Status == WriteIntentActive || intent.Status == WriteIntentRecovery {
			paths = append(paths, intent.Path)
		}
	}
	return paths
}

func automaticRunObservedPaths(
	ctx context.Context,
	store *Store,
	finished FinishedExecution,
) ([]string, error) {
	if finished.Result.ResultID != "" {
		return store.ListRunResultPaths(ctx, finished.Result.ResultID)
	}
	return InspectWorkspaceChanges(ctx, finished.Workspace.RootPath)
}

func extendAutomaticWorkLease(work WorkItem, leaseDuration time.Duration) time.Time {
	leaseUntil := time.Now().UTC().Add(leaseDuration)
	currentLease := time.UnixMilli(work.LeaseUntilMS).UTC().Add(time.Millisecond)
	if currentLease.After(leaseUntil) {
		return currentLease
	}
	return leaseUntil
}

func automaticRunWorkID(runID string, generation int64) string {
	return supervisedAggregateID("work", runID, generation)
}

func automaticRunWriteIntents(run Run) []WriteIntentSpec {
	subjectID := strings.TrimSpace(run.SubjectID)
	if subjectID == "" {
		return nil
	}
	subjectType := strings.ToLower(strings.TrimSpace(run.SubjectType))
	if subjectType == "feature" {
		if subjectID == "." || subjectID == ".." || strings.TrimSpace(run.SubjectID) != run.SubjectID ||
			strings.ContainsAny(subjectID, `/\\`) || strings.ContainsRune(subjectID, '\x00') {
			return nil
		}
		featurePath := filepath.ToSlash(filepath.Join(".specify", "features", subjectID))
		if _, _, err := normalizeWorkPath(featurePath, runtime.GOOS == "windows"); err != nil {
			return nil
		}
		return []WriteIntentSpec{{
			Path:       featurePath,
			Operation:  WriteCreate,
			Reason:     "automatic feature bootstrap scope from managed Run subject",
			Confidence: IntentConfirmed,
		}}
	}
	if subjectType == "quick" {
		if subjectID == "." || subjectID == ".." || strings.TrimSpace(run.SubjectID) != run.SubjectID ||
			strings.ContainsAny(subjectID, `/\`) || strings.ContainsRune(subjectID, '\x00') {
			return nil
		}
		quickPath := filepath.ToSlash(filepath.Join(".planning", "quick", subjectID))
		if _, _, err := normalizeWorkPath(quickPath, runtime.GOOS == "windows"); err != nil {
			return nil
		}
		return []WriteIntentSpec{{
			Path:       quickPath,
			Operation:  WriteModify,
			Reason:     "automatic Quick workspace scope from managed Run subject",
			Confidence: IntentConfirmed,
		}}
	}
	pathLikeSubject := subjectType == "file" || subjectType == "path" ||
		strings.ContainsAny(subjectID, `/\`)
	if !pathLikeSubject {
		return nil
	}
	if _, _, err := normalizeWorkPath(subjectID, runtime.GOOS == "windows"); err != nil {
		return nil
	}
	return []WriteIntentSpec{{
		Path:       subjectID,
		Operation:  WriteModify,
		Reason:     "automatic write scope from managed Run subject",
		Confidence: IntentConfirmed,
	}}
}

func supervisedRunWriteIntents(run Run, requested []WriteIntentSpec) ([]WriteIntentSpec, error) {
	writeIntents := append([]WriteIntentSpec(nil), requested...)
	if len(writeIntents) == 0 {
		writeIntents = automaticRunWriteIntents(run)
	}
	if !modifyingExecutionRunKind(run.Kind) {
		return writeIntents, nil
	}
	confirmed := 0
	for _, intent := range writeIntents {
		if intent.Confidence == IntentConfirmed {
			confirmed++
		}
	}
	if confirmed == 0 {
		return nil, fmt.Errorf("%w: modifying run kind %q has zero confirmed write scope; pass the complete scope before child launch", ErrInvalidArgument, run.Kind)
	}
	if confirmed != len(writeIntents) {
		return nil, fmt.Errorf("%w: modifying run kind %q requires every launch write scope to be confirmed before child launch", ErrInvalidArgument, run.Kind)
	}
	return writeIntents, nil
}

func modifyingExecutionRunKind(kind string) bool {
	kind = strings.ToLower(strings.TrimSpace(kind))
	kind = strings.TrimPrefix(kind, "spx-")
	kind = strings.TrimPrefix(kind, "sp-")
	switch kind {
	case "fast", "debug", "implement", "quick":
		return true
	default:
		return false
	}
}

func supervisedRunEnvironment(
	run Run,
	attempt Attempt,
	workspace Workspace,
	work WorkItem,
	featureBranchPolicy FeatureBranchPolicy,
) []string {
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
		"SPECIFY_RUN_WORKSPACE_MODE=" + string(normalizeWorkspaceMode(workspace.Mode)),
		"SPECIFY_RUN_WORKSPACE=" + workspace.RootPath,
		"SPECIFY_RUN_PRIVATE_REF=" + workspace.PrivateRef,
		"SPECIFY_WORK_ID=" + work.WorkID,
		"SPECIFY_WORK_FENCE=" + strconv.FormatInt(work.Fence, 10),
		"SPECIFY_FEATURE_BRANCH_POLICY=" + string(featureBranchPolicy),
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
		"SPECIFY_RUN_WORKSPACE_MODE",
		"SPECIFY_RUN_WORKSPACE/p",
		"SPECIFY_RUN_PRIVATE_REF",
		"SPECIFY_WORK_ID",
		"SPECIFY_WORK_FENCE",
		"SPECIFY_FEATURE_BRANCH_POLICY",
		"SPECIFY_RUN_RESOURCE_ROOT/p",
		"SPECIFY_RUN_TEMP/p",
		"SPECIFY_RUN_CACHE/p",
		"SPECIFY_RUN_LOGS/p",
		"SPECIFY_RUN_SERVICE_NAMESPACE",
		"SPECIFY_RUN_DATABASE_NAMESPACE",
		"SPECIFY_RUN_COMPOSE_PROJECT",
		"SPECIFY_RUN_PORT_BASE",
		"TMPDIR/p",
		"TMP/p",
		"TEMP/p",
		"XDG_CACHE_HOME/p",
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
	workID string,
	workFence int64,
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
				if workID != "" {
					if _, err := store.RenewWorkLease(ctx, RenewWorkLeaseParams{
						WorkID: workID, Fence: workFence,
						LeaseUntil: time.Now().UTC().Add(leaseDuration),
					}); err != nil {
						if ctx.Err() != nil {
							return
						}
						errorsChannel <- err
						cancel()
						return
					}
				}
			}
		}
	}()
	return errorsChannel, done
}

func withSupervisionDefaults(params SuperviseRunParams) SuperviseRunParams {
	params.WorkspacePolicy = normalizeWorkspacePolicy(params.WorkspacePolicy)
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
	if policy := normalizeWorkspacePolicy(params.WorkspacePolicy); policy != WorkspacePolicyAuto &&
		policy != WorkspacePolicyPrimary && policy != WorkspacePolicyIsolated {
		return fmt.Errorf("%w: unsupported workspace policy %q", ErrInvalidArgument, params.WorkspacePolicy)
	}
	for _, argument := range params.Argv {
		if strings.ContainsRune(argument, '\x00') {
			return fmt.Errorf("%w: child argv cannot contain NUL", ErrInvalidArgument)
		}
	}
	for name, value := range map[string]string{
		"work agent id": params.Work.AgentID,
		"work task ref": params.Work.TaskRef,
		"work summary":  params.Work.Summary,
	} {
		if strings.ContainsRune(value, '\x00') {
			return fmt.Errorf("%w: %s cannot contain NUL", ErrInvalidArgument, name)
		}
	}
	seenWorkPaths := make(map[string]struct{}, len(params.Work.WriteIntents))
	for _, raw := range params.Work.WriteIntents {
		spec, err := normalizeWriteIntentSpec(raw)
		if err != nil {
			return err
		}
		if _, duplicate := seenWorkPaths[spec.pathKey]; duplicate {
			return fmt.Errorf("%w: duplicate managed write intent path %q", ErrInvalidArgument, spec.Path)
		}
		seenWorkPaths[spec.pathKey] = struct{}{}
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
		var maximumOrdinal int64
		if err := store.db.QueryRowContext(ctx, `
			SELECT COALESCE(MAX(ordinal), 0) FROM activities WHERE run_id = ?
		`, run.RunID).Scan(&maximumOrdinal); err != nil {
			return Activity{}, fmt.Errorf("read next activity ordinal for run %q: %w", run.RunID, err)
		}
		return store.CreateActivity(ctx, CreateActivityParams{
			ActivityID:  supervisedAggregateID("activity", run.RunID, maximumOrdinal+1),
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
