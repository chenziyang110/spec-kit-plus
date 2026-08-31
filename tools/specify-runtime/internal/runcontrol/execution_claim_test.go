package runcontrol

import (
	"context"
	"errors"
	"path/filepath"
	"reflect"
	"strings"
	"testing"
	"time"
)

func TestVerifyExecutionWorkClaimUsesExistingGuardWithoutMutation(t *testing.T) {
	ctx := context.Background()
	store := openTestStore(t, filepath.Join(t.TempDir(), "run-control.sqlite"))
	registration := announceExecutionTestActivity(t, store, "verify", "implement:feature", "src/owned", ResourceFeature, "feature")
	guarded := guardTestExecution(t, store, registration)
	before := databaseContents(t, store.db)
	params := ClaimWorkIntentsParams{
		WorkID: guarded.Work.WorkID, ExpectedRevision: guarded.Work.Revision, Fence: guarded.Work.Fence,
		Specs: []WriteIntentSpec{{Path: `src\owned\first.go`}, {Path: "./src/owned/second.go"}},
	}
	if _, err := store.db.Exec(`PRAGMA query_only = ON`); err != nil {
		t.Fatal(err)
	}
	work, intents, err := store.VerifyExecutionWorkClaim(ctx, params)
	if err != nil {
		t.Fatal(err)
	}
	if !reflect.DeepEqual(work, guarded.Work) || len(intents) != 1 ||
		intents[0].IntentID != guarded.WriteIntents[0].IntentID || intents[0].Path != "src/owned" {
		t.Fatalf("guard receipt = %#v / %#v, want unchanged work and its covering intent", work, intents)
	}
	assertPreservedDatabaseContents(t, store.db, before)
	if _, err := store.db.Exec(`PRAGMA query_only = OFF`); err != nil {
		t.Fatal(err)
	}
	if _, _, err := store.ClaimWorkIntents(ctx, params); !errors.Is(err, ErrExecutionGuardRequired) {
		t.Fatalf("raw claim after guard = %v, want ErrExecutionGuardRequired", err)
	}
	assertPreservedDatabaseContents(t, store.db, before)
}

func TestVerifyExecutionWorkClaimRejectsMissingOrStaleAuthority(t *testing.T) {
	cases := []struct {
		name       string
		noGuard    bool
		path       string
		request    string
		fixtureSQL string
		staleFence bool
		staleRev   bool
		want       error
	}{
		{name: "announced_without_guard", noGuard: true, want: ErrExecutionGuardRequired},
		{name: "old_fence", staleFence: true, want: ErrStaleFence},
		{name: "old_revision", staleRev: true, want: ErrRevisionConflict},
		{name: "expired_lease", fixtureSQL: `UPDATE work_items SET lease_until_ms = 1`, want: ErrStaleFence},
		{name: "blocked_phase", fixtureSQL: `UPDATE execution_activities SET phase = 'blocked'`, want: ErrExecutionGuardRequired},
		{name: "validating_phase", fixtureSQL: `UPDATE execution_activities SET phase = 'validating'`, want: ErrExecutionGuardRequired},
		{name: "missing_guard_digest", fixtureSQL: `UPDATE execution_activities SET guarded_overview_sha256 = ''`, want: ErrExecutionGuardRequired},
		{name: "missing_guard_revision", fixtureSQL: `UPDATE execution_activities SET guarded_overview_revision = 0`, want: ErrExecutionGuardRequired},
		{name: "outside_scope", request: "src/outside.go", want: ErrExecutionGuardRequired},
		{name: "child_does_not_cover_parent", path: "src/owned/file.go", request: "src/owned", want: ErrExecutionGuardRequired},
		{name: "text_prefix_is_not_ancestor", request: "src/owned-other/file.go", want: ErrExecutionGuardRequired},
		{name: "candidate_is_not_ownership", fixtureSQL: `UPDATE write_intents SET confidence = 'candidate'`, want: ErrExecutionGuardRequired},
		{name: "released_intent", fixtureSQL: `UPDATE write_intents SET status = 'released'`, want: ErrExecutionGuardRequired},
		{name: "recovery_intent", fixtureSQL: `UPDATE write_intents SET status = 'recovery'`, want: ErrExecutionGuardRequired},
		{name: "escaping_path", request: "../outside.go", want: ErrInvalidArgument},
	}
	for _, test := range cases {
		t.Run(test.name, func(t *testing.T) {
			store := openTestStore(t, filepath.Join(t.TempDir(), "run-control.sqlite"))
			path := test.path
			if path == "" {
				path = "src/owned"
			}
			registration := announceExecutionTestActivity(t, store, "verify", "quick:verify", path, ResourceAPI, "/v1/verify")
			if !test.noGuard {
				registration = guardTestExecution(t, store, registration).ExecutionRegistration
			}
			if test.fixtureSQL != "" {
				if _, err := store.db.Exec(test.fixtureSQL); err != nil {
					t.Fatal(err)
				}
			}
			request := test.request
			if request == "" {
				request = path
			}
			params := ClaimWorkIntentsParams{
				WorkID: registration.Work.WorkID, ExpectedRevision: registration.Work.Revision, Fence: registration.Work.Fence,
				Specs: []WriteIntentSpec{{Path: request}},
			}
			if test.staleFence {
				params.Fence++
			}
			if test.staleRev {
				params.ExpectedRevision--
			}
			before := databaseContents(t, store.db)
			_, intents, err := store.VerifyExecutionWorkClaim(context.Background(), params)
			if !errors.Is(err, test.want) || len(intents) != 0 {
				t.Fatalf("verify = %#v, %v; want no receipt and %v", intents, err, test.want)
			}
			assertPreservedDatabaseContents(t, store.db, before)
		})
	}
}

func TestVerifyExecutionWorkClaimRejectsUnregisteredWork(t *testing.T) {
	store := openTestStore(t, filepath.Join(t.TempDir(), "run-control.sqlite"))
	work, _, err := store.BeginWork(context.Background(), BeginWorkParams{
		WorkID: "unregistered", Summary: "ordinary work", AgentID: "agent", AdapterID: "codex",
		WorkspaceRoot: t.TempDir(), LeaseUntil: time.Now().UTC().Add(time.Hour),
		WriteIntents: []WriteIntentSpec{{Path: "src/owned"}},
	})
	if err != nil {
		t.Fatal(err)
	}
	_, _, err = store.VerifyExecutionWorkClaim(context.Background(), ClaimWorkIntentsParams{
		WorkID: work.WorkID, ExpectedRevision: work.Revision, Fence: work.Fence,
		Specs: []WriteIntentSpec{{Path: "src/owned/file.go"}},
	})
	if !errors.Is(err, ErrExecutionGuardRequired) {
		t.Fatalf("unregistered work verification = %v, want execution guard required", err)
	}
}

func TestVerifyExecutionWorkClaimReadsOneCommittedStateDuringWriter(t *testing.T) {
	databasePath := filepath.Join(t.TempDir(), "run-control.sqlite")
	reader := openTestStore(t, databasePath)
	registration := announceExecutionTestActivity(t, reader, "verify", "implement:verify", "src/owned", ResourceAPI, "/v1/verify")
	guarded := guardTestExecution(t, reader, registration)
	writer := openTestStore(t, databasePath)
	tx, err := writer.db.BeginTx(context.Background(), nil)
	if err != nil {
		t.Fatal(err)
	}
	defer func() { _ = tx.Rollback() }()
	if _, err := tx.Exec(`UPDATE work_items SET revision = revision + 1, next_action = 'uncommitted' WHERE work_id = ?`, guarded.Work.WorkID); err != nil {
		t.Fatal(err)
	}
	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
	defer cancel()
	work, _, err := reader.VerifyExecutionWorkClaim(ctx, ClaimWorkIntentsParams{
		WorkID: guarded.Work.WorkID, ExpectedRevision: guarded.Work.Revision, Fence: guarded.Work.Fence,
		Specs: []WriteIntentSpec{{Path: "src/owned/file.go"}},
	})
	if err != nil {
		t.Fatalf("read-only verification took a writer lock: %v", err)
	}
	if !reflect.DeepEqual(work, guarded.Work) {
		t.Fatalf("verification read uncommitted state: %#v", work)
	}
}

func TestResumedExecutionRequiresANewGuardForItsNewFence(t *testing.T) {
	ctx := context.Background()
	store := openTestStore(t, filepath.Join(t.TempDir(), "run-control.sqlite"))
	registration := announceExecutionTestActivity(t, store, "resume", "quick:resume", "src/owned", ResourceAPI, "/v1/resume")
	guarded := guardTestExecution(t, store, registration)
	interrupted, err := store.InterruptWork(ctx, InterruptWorkParams{
		WorkID: guarded.Work.WorkID, ExpectedRevision: guarded.Work.Revision, Fence: guarded.Work.Fence,
		Reason: "old session ended", ObservedPaths: []string{"src/owned/file.go"},
	})
	if err != nil {
		t.Fatal(err)
	}
	resumed, err := store.ResumeWork(ctx, ResumeWorkParams{
		WorkID: interrupted.WorkID, ExpectedRevision: interrupted.Revision, AgentID: "replacement", AdapterID: "codex",
		NextAction: "recheck before editing", LeaseUntil: time.Now().UTC().Add(2 * time.Hour),
	})
	if err != nil {
		t.Fatal(err)
	}
	current, err := store.GetExecutionActivity(ctx, guarded.Activity.ActivityID)
	if err != nil {
		t.Fatal(err)
	}
	if current.Activity.GuardedOverviewRevision != 0 || current.Activity.GuardedOverviewSHA256 != "" {
		t.Fatalf("resume retained a guard from an old fence: %#v", current.Activity)
	}
	params := ClaimWorkIntentsParams{
		WorkID: resumed.WorkID, ExpectedRevision: resumed.Revision, Fence: resumed.Fence,
		Specs: []WriteIntentSpec{{Path: "src/owned/file.go"}},
	}
	if _, _, err := store.VerifyExecutionWorkClaim(ctx, params); !errors.Is(err, ErrExecutionGuardRequired) {
		t.Fatalf("resume reused previous guard: %v", err)
	}
	if _, err := store.CheckpointExecution(ctx, CheckpointExecutionParams{
		ActivityID: current.Activity.ActivityID, ExpectedWorkRevision: resumed.Revision, Fence: resumed.Fence,
		TargetPhase: ExecutionPhaseExecuting, NextAction: "try bypassing guard", LeaseUntil: time.Now().UTC().Add(3 * time.Hour),
	}); !errors.Is(err, ErrExecutionGuardRequired) {
		t.Fatalf("checkpoint manufactured execution authority: %v", err)
	}
	reguarded := guardTestExecution(t, store, current)
	params.ExpectedRevision = reguarded.Work.Revision
	if _, _, err := store.VerifyExecutionWorkClaim(ctx, params); err != nil {
		t.Fatalf("new-fence guard rejected: %v", err)
	}
}

func guardTestExecution(t *testing.T, store *Store, registration ExecutionRegistration) GuardedExecution {
	t.Helper()
	revision, err := store.CoordinationRevision(context.Background())
	if err != nil {
		t.Fatal(err)
	}
	params := GuardExecutionParams{
		ActivityID: registration.Activity.ActivityID, ExpectedWorkRevision: registration.Work.Revision,
		Fence: registration.Work.Fence, ExpectedCoordinationRevision: revision,
		OverviewSHA256: strings.Repeat("a", 64), Reason: "execute within confirmed scope",
	}
	for _, intent := range registration.WriteIntents {
		params.WriteIntents = append(params.WriteIntents, WriteIntentSpec{
			Path: intent.Path, Operation: intent.Operation, Confidence: IntentConfirmed,
		})
	}
	for _, resource := range registration.Resources {
		params.Resources = append(params.Resources, ExecutionResourceIntentSpec{
			ResourceType: resource.ResourceType, ResourceKey: resource.ResourceKey,
			Mode: resource.Mode, Confidence: IntentConfirmed,
		})
	}
	guarded, err := store.GuardExecution(context.Background(), params)
	if err != nil {
		t.Fatal(err)
	}
	return guarded
}
