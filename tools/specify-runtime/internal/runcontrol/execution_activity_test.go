package runcontrol

import (
	"context"
	"encoding/json"
	"errors"
	"path/filepath"
	"strings"
	"testing"
	"time"
)

func TestExecutionGuardClaimsWriteAndSemanticResourcesAtomically(t *testing.T) {
	ctx := context.Background()
	store := openTestStore(t, filepath.Join(t.TempDir(), "run-control.sqlite"))
	first := announceExecutionTestActivity(t, store, "activity-first", "fast:first", "src/first.go", "api", "/v1/nodes")
	second := announceExecutionTestActivity(t, store, "activity-second", "debug:second", "src/second.go", "api", "/v1/nodes")

	revision, err := store.CoordinationRevision(ctx)
	if err != nil {
		t.Fatal(err)
	}
	guarded, err := store.GuardExecution(ctx, GuardExecutionParams{
		ActivityID:                   first.Activity.ActivityID,
		ExpectedWorkRevision:         first.Work.Revision,
		Fence:                        first.Work.Fence,
		ExpectedCoordinationRevision: revision,
		OverviewSHA256:               strings.Repeat("a", 64),
		WriteIntents: []WriteIntentSpec{{
			Path: "src/first.go", Operation: WriteModify, Confidence: IntentConfirmed,
		}},
		Resources: []ExecutionResourceIntentSpec{{
			ResourceType: ResourceAPI, ResourceKey: "/v1/nodes", Mode: ResourceClaimExclusive,
			Confidence: IntentConfirmed,
		}},
		Reason: "start first execution",
	})
	if err != nil {
		t.Fatal(err)
	}
	if guarded.Activity.Phase != ExecutionPhaseExecuting || guarded.Work.Status != WorkActive {
		t.Fatalf("guarded execution = %#v", guarded)
	}
	if len(guarded.WriteIntents) != 1 || guarded.WriteIntents[0].Confidence != IntentConfirmed {
		t.Fatalf("guarded writes = %#v", guarded.WriteIntents)
	}
	if len(guarded.Resources) != 1 || guarded.Resources[0].Confidence != IntentConfirmed {
		t.Fatalf("guarded resources = %#v", guarded.Resources)
	}

	_, err = store.GuardExecution(ctx, GuardExecutionParams{
		ActivityID:                   second.Activity.ActivityID,
		ExpectedWorkRevision:         second.Work.Revision,
		Fence:                        second.Work.Fence,
		ExpectedCoordinationRevision: guarded.CoordinationRevision,
		OverviewSHA256:               strings.Repeat("b", 64),
		WriteIntents: []WriteIntentSpec{{
			Path: "src/second.go", Operation: WriteModify, Confidence: IntentConfirmed,
		}},
		Resources: []ExecutionResourceIntentSpec{{
			ResourceType: ResourceAPI, ResourceKey: "/v1/nodes", Mode: ResourceClaimExclusive,
			Confidence: IntentConfirmed,
		}},
		Reason: "start second execution",
	})
	if !errors.Is(err, ErrExecutionResourceConflict) {
		t.Fatalf("second guard error = %v, want semantic resource conflict", err)
	}
	loaded, err := store.GetExecutionActivity(ctx, second.Activity.ActivityID)
	if err != nil {
		t.Fatal(err)
	}
	if loaded.Activity.Phase != ExecutionPhaseAnnounced || loaded.Work.Revision != second.Work.Revision {
		t.Fatalf("rejected execution mutated = %#v", loaded)
	}
	if loaded.WriteIntents[0].Confidence != IntentCandidate || loaded.Resources[0].Confidence != IntentCandidate {
		t.Fatalf("rejected guard partially promoted claims = %#v", loaded)
	}
}

func TestExecutionGuardRejectsAStaleOverviewRevision(t *testing.T) {
	ctx := context.Background()
	store := openTestStore(t, filepath.Join(t.TempDir(), "run-control.sqlite"))
	first := announceExecutionTestActivity(t, store, "activity-stale", "fast:stale", "src/stale.go", "feature", "stale")
	revision, err := store.CoordinationRevision(ctx)
	if err != nil {
		t.Fatal(err)
	}
	_ = announceExecutionTestActivity(t, store, "activity-racer", "debug:racer", "src/racer.go", "feature", "racer")

	_, err = store.GuardExecution(ctx, GuardExecutionParams{
		ActivityID:                   first.Activity.ActivityID,
		ExpectedWorkRevision:         first.Work.Revision,
		Fence:                        first.Work.Fence,
		ExpectedCoordinationRevision: revision,
		OverviewSHA256:               strings.Repeat("c", 64),
		WriteIntents: []WriteIntentSpec{{
			Path: "src/stale.go", Operation: WriteModify, Confidence: IntentConfirmed,
		}},
		Reason: "stale snapshot",
	})
	if !errors.Is(err, ErrExecutionSnapshotStale) {
		t.Fatalf("guard error = %v, want stale overview", err)
	}
}

func TestExecutionCompletionAuditsActualPathsAndClosesAllAuthority(t *testing.T) {
	ctx := context.Background()
	store := openTestStore(t, filepath.Join(t.TempDir(), "run-control.sqlite"))
	announced := announceExecutionTestActivity(t, store, "activity-complete", "fast:complete", "src/allowed", "feature", "complete")
	revision, err := store.CoordinationRevision(ctx)
	if err != nil {
		t.Fatal(err)
	}
	guarded, err := store.GuardExecution(ctx, GuardExecutionParams{
		ActivityID:                   announced.Activity.ActivityID,
		ExpectedWorkRevision:         announced.Work.Revision,
		Fence:                        announced.Work.Fence,
		ExpectedCoordinationRevision: revision,
		OverviewSHA256:               strings.Repeat("d", 64),
		WriteIntents: []WriteIntentSpec{{
			Path: "src/allowed", Operation: WriteModify, Confidence: IntentConfirmed,
		}},
		Resources: []ExecutionResourceIntentSpec{{
			ResourceType: ResourceFeature, ResourceKey: "complete", Mode: ResourceClaimExclusive,
			Confidence: IntentConfirmed,
		}},
		Reason: "execute guarded work",
	})
	if err != nil {
		t.Fatal(err)
	}

	_, err = store.CompleteExecution(ctx, CompleteExecutionParams{
		ActivityID:           guarded.Activity.ActivityID,
		ExpectedWorkRevision: guarded.Work.Revision,
		Fence:                guarded.Work.Fence,
		ChangedPaths:         []string{"src/outside.go"},
		ValidationJSON:       `[{"command":"go test ./...","result":"passed"}]`,
		Reason:               "attempt invalid completion",
	})
	var auditErr *ExecutionScopeAuditError
	if !errors.As(err, &auditErr) || strings.Join(auditErr.UnclaimedPaths, ",") != "src/outside.go" {
		t.Fatalf("completion error = %v, want out-of-scope audit", err)
	}
	unchanged, err := store.GetExecutionActivity(ctx, guarded.Activity.ActivityID)
	if err != nil {
		t.Fatal(err)
	}
	if unchanged.Activity.Phase != ExecutionPhaseExecuting || unchanged.Work.Status != WorkActive {
		t.Fatalf("failed completion mutated authority = %#v", unchanged)
	}

	completed, err := store.CompleteExecution(ctx, CompleteExecutionParams{
		ActivityID:           guarded.Activity.ActivityID,
		ExpectedWorkRevision: guarded.Work.Revision,
		Fence:                guarded.Work.Fence,
		ChangedPaths:         []string{"src/allowed/main.go"},
		ValidationJSON:       `[{"command":"go test ./...","result":"passed"}]`,
		Reason:               "execution verified",
	})
	if err != nil {
		t.Fatal(err)
	}
	if completed.Activity.Phase != ExecutionPhaseCompleted || completed.Work.Status != WorkCompleted {
		t.Fatalf("completed execution = %#v", completed)
	}
	if len(completed.Activity.CompletionSHA256) != 64 {
		t.Fatalf("completion digest = %q", completed.Activity.CompletionSHA256)
	}
	for _, intent := range completed.WriteIntents {
		if intent.Status != WriteIntentReleased {
			t.Fatalf("write intent remains live = %#v", intent)
		}
	}
	for _, resource := range completed.Resources {
		if resource.Status != WriteIntentReleased {
			t.Fatalf("resource intent remains live = %#v", resource)
		}
	}
}

func TestExecutionEventsPreserveEveryLifecycleBoundaryAtomically(t *testing.T) {
	ctx := context.Background()
	store := openTestStore(t, filepath.Join(t.TempDir(), "run-control.sqlite"))
	announced := announceExecutionTestActivity(
		t, store, "activity-lifecycle", "fast:lifecycle", "src/lifecycle", "feature", "lifecycle",
	)
	revision, err := store.CoordinationRevision(ctx)
	if err != nil {
		t.Fatal(err)
	}
	guarded, err := store.GuardExecution(ctx, GuardExecutionParams{
		ActivityID:                   announced.Activity.ActivityID,
		ExpectedWorkRevision:         announced.Work.Revision,
		Fence:                        announced.Work.Fence,
		ExpectedCoordinationRevision: revision,
		OverviewSHA256:               strings.Repeat("e", 64),
		WriteIntents: []WriteIntentSpec{{
			Path: "src/lifecycle", Operation: WriteModify, Confidence: IntentConfirmed,
		}},
		Reason: "guard lifecycle",
	})
	if err != nil {
		t.Fatal(err)
	}
	if _, err := store.CompleteExecution(ctx, CompleteExecutionParams{
		ActivityID:           guarded.Activity.ActivityID,
		ExpectedWorkRevision: guarded.Work.Revision,
		Fence:                guarded.Work.Fence,
		ChangedPaths:         []string{"src/lifecycle/main.go"},
		ValidationJSON:       `[{"command":"go test ./...","result":"passed"}]`,
		Reason:               "complete lifecycle",
	}); err != nil {
		t.Fatal(err)
	}
	changes, err := store.ListCoordinationChanges(ctx, 0, 100)
	if err != nil {
		t.Fatal(err)
	}
	phases := make([]string, 0)
	for _, change := range changes {
		if change.AggregateType != "execution_activity" || change.AggregateID != announced.Activity.ActivityID {
			continue
		}
		var payload map[string]any
		if err := json.Unmarshal([]byte(change.PayloadJSON), &payload); err != nil {
			t.Fatal(err)
		}
		phases = append(phases, strings.TrimSpace(payload["phase"].(string)))
	}
	if got := strings.Join(phases, ","); got != "announced,selected,claimed,executing,validating,completed" {
		t.Fatalf("lifecycle event phases = %q", got)
	}
}

func announceExecutionTestActivity(
	t *testing.T,
	store *Store,
	activityID string,
	taskRef string,
	writePath string,
	resourceType ResourceType,
	resourceKey string,
) ExecutionRegistration {
	t.Helper()
	workflow, subject, found := strings.Cut(taskRef, ":")
	if !found {
		t.Fatalf("invalid task ref %q", taskRef)
	}
	registration, err := store.AnnounceExecution(context.Background(), AnnounceExecutionParams{
		ActivityID:    activityID,
		WorkID:        activityID,
		TaskRef:       taskRef,
		Workflow:      ExecutionWorkflow(workflow),
		SubjectID:     subject,
		Summary:       taskRef,
		AgentID:       activityID + "-agent",
		AdapterID:     "codex",
		WorkspaceRoot: t.TempDir(),
		NextAction:    "await guard",
		LeaseUntil:    time.Now().UTC().Add(time.Hour),
		PlannedWriteIntents: []WriteIntentSpec{{
			Path: writePath, Operation: WriteModify, Confidence: IntentCandidate,
		}},
		Resources: []ExecutionResourceIntentSpec{{
			ResourceType: resourceType, ResourceKey: resourceKey, Mode: ResourceClaimExclusive,
			Confidence: IntentCandidate,
		}},
		BaselineJSON: `{"head_commit":"","dirty_paths":[],"path_digests":{}}`,
	})
	if err != nil {
		t.Fatal(err)
	}
	return registration
}
