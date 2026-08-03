package runcontrol

import (
	"context"
	"errors"
	"path/filepath"
	"strings"
	"testing"
	"time"
)

func TestPrepareExecutionAtomicallyReadiesRunActivityAndWorkspace(t *testing.T) {
	ctx := context.Background()
	store := openTestStore(t, filepath.Join(t.TempDir(), "run-control.sqlite"))
	run, activity, workspace := createAllocatingExecution(t, store, "prepare_atomic", 1)

	_, err := store.PrepareExecution(ctx, PrepareExecutionParams{
		RunID:                     run.RunID,
		ActivityID:                activity.ActivityID,
		WorkspaceID:               workspace.WorkspaceID,
		ExpectedRunRevision:       run.Revision,
		ExpectedActivityRevision:  activity.Revision,
		ExpectedWorkspaceRevision: workspace.Revision + 1,
	})
	if !errors.Is(err, ErrRevisionConflict) {
		t.Fatalf("PrepareExecution() stale workspace error = %v, want ErrRevisionConflict", err)
	}
	assertExecutionStatuses(t, store, run.RunID, activity.ActivityID, workspace.WorkspaceID,
		RunAllocating, ActivityPlanned, WorkspaceAllocating)

	prepared, err := store.PrepareExecution(ctx, PrepareExecutionParams{
		RunID:                     run.RunID,
		ActivityID:                activity.ActivityID,
		WorkspaceID:               workspace.WorkspaceID,
		ExpectedRunRevision:       run.Revision,
		ExpectedActivityRevision:  activity.Revision,
		ExpectedWorkspaceRevision: workspace.Revision,
	})
	if err != nil {
		t.Fatal(err)
	}
	if prepared.Run.Status != RunReady || prepared.Activity.Status != ActivityReady || prepared.Workspace.Status != WorkspaceReady {
		t.Fatalf("prepared execution = %#v, want all three aggregates ready", prepared)
	}
	if prepared.Run.Revision != run.Revision+1 || prepared.Activity.Revision != activity.Revision+1 || prepared.Workspace.Revision != workspace.Revision+1 {
		t.Fatalf("prepared revisions = run %d activity %d workspace %d, want one increment each",
			prepared.Run.Revision, prepared.Activity.Revision, prepared.Workspace.Revision)
	}
}

func TestRunAllowsOnlyOneOpenActivityAndOneUsableWorkspace(t *testing.T) {
	ctx := context.Background()
	store := openTestStore(t, filepath.Join(t.TempDir(), "run-control.sqlite"))
	run, _, _ := createAllocatingExecution(t, store, "unique_execution", 1)

	_, err := store.CreateActivity(ctx, CreateActivityParams{
		ActivityID: "activity_unique_execution_second",
		RunID:      run.RunID,
		Kind:       "debug",
	})
	if !errors.Is(err, ErrOpenActivity) {
		t.Fatalf("second open activity error = %v, want ErrOpenActivity", err)
	}

	_, err = store.CreateWorkspace(ctx, CreateWorkspaceParams{
		WorkspaceID:   "workspace_unique_execution_second",
		RunID:         run.RunID,
		Generation:    2,
		Kind:          "git_worktree",
		RootPath:      filepath.Join(t.TempDir(), "workspace-2"),
		RepoCommonDir: filepath.Join(t.TempDir(), ".git"),
		BaseRef:       "refs/heads/main",
		BaseCommit:    strings.Repeat("b", 40),
		PrivateRef:    "refs/specify/runs/unique_execution/2",
	})
	if !errors.Is(err, ErrUsableWorkspace) {
		t.Fatalf("second usable workspace error = %v, want ErrUsableWorkspace", err)
	}
}

func TestAttemptRequiresAndPersistsExecutionBindings(t *testing.T) {
	ctx := context.Background()
	databasePath := filepath.Join(t.TempDir(), "run-control.sqlite")
	store := openTestStore(t, databasePath)
	prepared := createPreparedExecution(t, store, "attempt_binding", 1)
	now := time.Now().UTC()

	missing := IssueAttemptParams{
		AttemptID:                 "attempt_binding_missing",
		RunID:                     prepared.Run.RunID,
		ExpectedRunRevision:       prepared.Run.Revision,
		ExpectedActivityRevision:  prepared.Activity.Revision,
		ExpectedWorkspaceRevision: prepared.Workspace.Revision,
		AdapterID:                 "codex",
		ExecutionMode:             ExecutionManaged,
		LeaseUntil:                now.Add(time.Minute),
	}
	if _, err := store.IssueAttempt(ctx, missing); !errors.Is(err, ErrInvalidArgument) {
		t.Fatalf("IssueAttempt() without bindings error = %v, want ErrInvalidArgument", err)
	}

	issued, err := store.IssueAttempt(ctx, IssueAttemptParams{
		AttemptID:                 "attempt_binding_1",
		RunID:                     prepared.Run.RunID,
		ActivityID:                prepared.Activity.ActivityID,
		WorkspaceID:               prepared.Workspace.WorkspaceID,
		ExpectedRunRevision:       prepared.Run.Revision,
		ExpectedActivityRevision:  prepared.Activity.Revision,
		ExpectedWorkspaceRevision: prepared.Workspace.Revision,
		AdapterID:                 "codex",
		ExecutionMode:             ExecutionManaged,
		LeaseUntil:                now.Add(time.Minute),
	})
	if err != nil {
		t.Fatal(err)
	}
	if issued.ActivityID != prepared.Activity.ActivityID || issued.WorkspaceID != prepared.Workspace.WorkspaceID || issued.WorkspaceGeneration != 1 {
		t.Fatalf("issued attempt bindings = %#v, want activity %q workspace %q generation 1",
			issued, prepared.Activity.ActivityID, prepared.Workspace.WorkspaceID)
	}
	confirmManagedAttemptLaunchForTest(t, store, issued)
	if _, err := store.ActivateAttempt(ctx, issued.AttemptID, issued.Fence, now.Add(2*time.Minute)); err != nil {
		t.Fatal(err)
	}
	assertExecutionStatuses(t, store, prepared.Run.RunID, prepared.Activity.ActivityID, prepared.Workspace.WorkspaceID,
		RunActive, ActivityActive, WorkspaceInUse)

	loaded, err := store.GetAttempt(ctx, issued.AttemptID)
	if err != nil {
		t.Fatal(err)
	}
	if loaded.ActivityID != issued.ActivityID || loaded.WorkspaceID != issued.WorkspaceID || loaded.WorkspaceGeneration != issued.WorkspaceGeneration {
		t.Fatalf("persisted attempt bindings = %#v, want %#v", loaded, issued)
	}
}

func TestAttemptLossAndCancellationPropagateToExecutionAggregates(t *testing.T) {
	tests := []struct {
		name         string
		id           string
		end          func(*testing.T, context.Context, *Store, string, Run, Attempt, time.Time) error
		wantRun      RunStatus
		wantActivity ActivityStatus
	}{
		{
			name: "lease expiry",
			id:   "lease_expiry",
			end: func(_ *testing.T, ctx context.Context, store *Store, _ string, _ Run, _ Attempt, now time.Time) error {
				_, err := store.ExpireLeases(ctx, now.Add(2*time.Minute))
				return err
			},
			wantRun:      RunInterrupted,
			wantActivity: ActivityInterrupted,
		},
		{
			name: "owner takeover",
			id:   "owner_takeover",
			end: func(t *testing.T, ctx context.Context, _ *Store, databasePath string, _ Run, _ Attempt, now time.Time) error {
				takeover := openTestStore(t, databasePath, WithOwnerEpoch("takeover_new"))
				_, err := takeover.ReconcileOwnerEpoch(ctx, now)
				return err
			},
			wantRun:      RunInterrupted,
			wantActivity: ActivityInterrupted,
		},
		{
			name: "user cancellation",
			id:   "user_cancellation",
			end: func(_ *testing.T, ctx context.Context, store *Store, _ string, run Run, _ Attempt, _ time.Time) error {
				_, err := store.CancelRun(ctx, run.RunID, run.Revision, "user cancelled")
				return err
			},
			wantRun:      RunCancelled,
			wantActivity: ActivityCancelled,
		},
	}

	for _, test := range tests {
		t.Run(test.name, func(t *testing.T) {
			ctx := context.Background()
			databasePath := filepath.Join(t.TempDir(), "run-control.sqlite")
			owner := "lifecycle_owner"
			store := openTestStore(t, databasePath, WithOwnerEpoch(owner))
			prepared := createPreparedExecution(t, store, "lifecycle_"+test.id, 1)
			now := time.Now().UTC()
			attempt := issueAndActivateExecution(t, store, prepared, "attempt_lifecycle", now)
			active, err := store.GetRun(ctx, prepared.Run.RunID)
			if err != nil {
				t.Fatal(err)
			}
			if err := test.end(t, ctx, store, databasePath, active, attempt, now); err != nil {
				t.Fatal(err)
			}
			assertExecutionStatuses(t, store, prepared.Run.RunID, prepared.Activity.ActivityID, prepared.Workspace.WorkspaceID,
				test.wantRun, test.wantActivity, WorkspaceQuarantined)
		})
	}
}

func TestReplacementAttemptRequiresNewReadyWorkspaceGeneration(t *testing.T) {
	ctx := context.Background()
	store := openTestStore(t, filepath.Join(t.TempDir(), "run-control.sqlite"))
	prepared := createPreparedExecution(t, store, "replacement", 1)
	now := time.Now().UTC()
	issueAndActivateExecution(t, store, prepared, "attempt_replacement_old", now)
	if _, err := store.ExpireLeases(ctx, now.Add(2*time.Minute)); err != nil {
		t.Fatal(err)
	}

	interruptedRun, _ := store.GetRun(ctx, prepared.Run.RunID)
	interruptedActivity, _ := store.GetActivity(ctx, prepared.Activity.ActivityID)
	oldWorkspace, _ := store.GetWorkspace(ctx, prepared.Workspace.WorkspaceID)
	if oldWorkspace.Status != WorkspaceQuarantined {
		t.Fatalf("old workspace status = %q, want quarantined", oldWorkspace.Status)
	}
	if _, err := store.CreateWorkspace(ctx, CreateWorkspaceParams{
		WorkspaceID:   "workspace_replacement_reused_generation",
		RunID:         prepared.Run.RunID,
		Generation:    1,
		Kind:          "git_worktree",
		RootPath:      filepath.Join(t.TempDir(), "reused"),
		RepoCommonDir: filepath.Join(t.TempDir(), ".git"),
		BaseRef:       "refs/heads/main",
		BaseCommit:    strings.Repeat("b", 40),
		PrivateRef:    "refs/specify/runs/replacement/reused",
	}); !errors.Is(err, ErrWorkspaceGeneration) {
		t.Fatalf("reused workspace generation error = %v, want ErrWorkspaceGeneration", err)
	}

	newWorkspace, err := store.CreateWorkspace(ctx, CreateWorkspaceParams{
		WorkspaceID:   "workspace_replacement_2",
		RunID:         prepared.Run.RunID,
		Generation:    2,
		Kind:          "git_worktree",
		RootPath:      filepath.Join(t.TempDir(), "generation-2"),
		RepoCommonDir: filepath.Join(t.TempDir(), ".git"),
		BaseRef:       "refs/heads/main",
		BaseCommit:    strings.Repeat("c", 40),
		PrivateRef:    "refs/specify/runs/replacement/2",
	})
	if err != nil {
		t.Fatal(err)
	}
	resumed, err := store.PrepareExecution(ctx, PrepareExecutionParams{
		RunID:                     interruptedRun.RunID,
		ActivityID:                interruptedActivity.ActivityID,
		WorkspaceID:               newWorkspace.WorkspaceID,
		ExpectedRunRevision:       interruptedRun.Revision,
		ExpectedActivityRevision:  interruptedActivity.Revision,
		ExpectedWorkspaceRevision: newWorkspace.Revision,
	})
	if err != nil {
		t.Fatal(err)
	}

	baseIssue := IssueAttemptParams{
		AttemptID:                 "attempt_replacement_new",
		RunID:                     resumed.Run.RunID,
		ActivityID:                resumed.Activity.ActivityID,
		ExpectedRunRevision:       resumed.Run.Revision,
		ExpectedActivityRevision:  resumed.Activity.Revision,
		ExpectedWorkspaceRevision: oldWorkspace.Revision,
		AdapterID:                 "codex",
		ExecutionMode:             ExecutionManaged,
		LeaseUntil:                now.Add(5 * time.Minute),
	}
	baseIssue.WorkspaceID = oldWorkspace.WorkspaceID
	if _, err := store.IssueAttempt(ctx, baseIssue); !errors.Is(err, ErrWorkspaceNotUsable) {
		t.Fatalf("replacement on quarantined workspace error = %v, want ErrWorkspaceNotUsable", err)
	}
	baseIssue.WorkspaceID = resumed.Workspace.WorkspaceID
	baseIssue.ExpectedWorkspaceRevision = resumed.Workspace.Revision
	issued, err := store.IssueAttempt(ctx, baseIssue)
	if err != nil {
		t.Fatal(err)
	}
	if issued.WorkspaceGeneration != 2 {
		t.Fatalf("replacement workspace generation = %d, want 2", issued.WorkspaceGeneration)
	}
}

func TestExecutionModelSurvivesDatabaseReopen(t *testing.T) {
	ctx := context.Background()
	databasePath := filepath.Join(t.TempDir(), "run-control.sqlite")
	store := openTestStore(t, databasePath)
	prepared := createPreparedExecution(t, store, "execution_reopen", 1)
	if err := store.Close(); err != nil {
		t.Fatal(err)
	}

	reopened := openTestStore(t, databasePath)
	activity, err := reopened.GetActivity(ctx, prepared.Activity.ActivityID)
	if err != nil {
		t.Fatal(err)
	}
	workspace, err := reopened.GetWorkspace(ctx, prepared.Workspace.WorkspaceID)
	if err != nil {
		t.Fatal(err)
	}
	if activity.RunID != prepared.Run.RunID || workspace.RunID != prepared.Run.RunID || workspace.Generation != 1 {
		t.Fatalf("reopened execution = activity %#v workspace %#v, want durable run bindings and generation 1", activity, workspace)
	}
}

func createAllocatingExecution(t *testing.T, store *Store, suffix string, generation int64) (Run, Activity, Workspace) {
	t.Helper()
	ctx := context.Background()
	run, err := store.CreateRun(ctx, CreateRunParams{
		RunID:        "run_" + suffix,
		Kind:         "quick",
		SubjectType:  "feature",
		SubjectID:    suffix,
		TargetRef:    "refs/heads/main",
		IntentSHA256: digestForTest(suffix),
	})
	if err != nil {
		t.Fatal(err)
	}
	activity, err := store.CreateActivity(ctx, CreateActivityParams{
		ActivityID: "activity_" + suffix,
		RunID:      run.RunID,
		Kind:       "quick",
	})
	if err != nil {
		t.Fatal(err)
	}
	workspace, err := store.CreateWorkspace(ctx, CreateWorkspaceParams{
		WorkspaceID:   "workspace_" + suffix,
		RunID:         run.RunID,
		Generation:    generation,
		Kind:          "git_worktree",
		RootPath:      filepath.Join(t.TempDir(), "workspace"),
		RepoCommonDir: filepath.Join(t.TempDir(), ".git"),
		BaseRef:       "refs/heads/main",
		BaseCommit:    strings.Repeat("a", 40),
		PrivateRef:    "refs/specify/runs/" + suffix,
	})
	if err != nil {
		t.Fatal(err)
	}
	return run, activity, workspace
}

func createPreparedExecution(t *testing.T, store *Store, suffix string, generation int64) PreparedExecution {
	t.Helper()
	run, activity, workspace := createAllocatingExecution(t, store, suffix, generation)
	prepared, err := store.PrepareExecution(context.Background(), PrepareExecutionParams{
		RunID:                     run.RunID,
		ActivityID:                activity.ActivityID,
		WorkspaceID:               workspace.WorkspaceID,
		ExpectedRunRevision:       run.Revision,
		ExpectedActivityRevision:  activity.Revision,
		ExpectedWorkspaceRevision: workspace.Revision,
	})
	if err != nil {
		t.Fatal(err)
	}
	return prepared
}

func issueAndActivateExecution(t *testing.T, store *Store, prepared PreparedExecution, attemptID string, now time.Time) Attempt {
	t.Helper()
	attempt, err := store.IssueAttempt(context.Background(), IssueAttemptParams{
		AttemptID:                 attemptID,
		RunID:                     prepared.Run.RunID,
		ActivityID:                prepared.Activity.ActivityID,
		WorkspaceID:               prepared.Workspace.WorkspaceID,
		ExpectedRunRevision:       prepared.Run.Revision,
		ExpectedActivityRevision:  prepared.Activity.Revision,
		ExpectedWorkspaceRevision: prepared.Workspace.Revision,
		AdapterID:                 "codex",
		ExecutionMode:             ExecutionManaged,
		LeaseUntil:                now.Add(time.Minute),
	})
	if err != nil {
		t.Fatal(err)
	}
	confirmManagedAttemptLaunchForTest(t, store, attempt)
	attempt, err = store.ActivateAttempt(context.Background(), attempt.AttemptID, attempt.Fence, now.Add(time.Minute))
	if err != nil {
		t.Fatal(err)
	}
	return attempt
}

func assertExecutionStatuses(t *testing.T, store *Store, runID, activityID, workspaceID string, wantRun RunStatus, wantActivity ActivityStatus, wantWorkspace WorkspaceStatus) {
	t.Helper()
	ctx := context.Background()
	run, err := store.GetRun(ctx, runID)
	if err != nil {
		t.Fatal(err)
	}
	activity, err := store.GetActivity(ctx, activityID)
	if err != nil {
		t.Fatal(err)
	}
	workspace, err := store.GetWorkspace(ctx, workspaceID)
	if err != nil {
		t.Fatal(err)
	}
	if run.Status != wantRun || activity.Status != wantActivity || workspace.Status != wantWorkspace {
		t.Fatalf("execution statuses = run %q activity %q workspace %q, want %q %q %q",
			run.Status, activity.Status, workspace.Status, wantRun, wantActivity, wantWorkspace)
	}
}
