package runcontrol

import (
	"context"
	"path/filepath"
	"testing"
	"time"
)

func TestQueuedRunSurvivesReconciliationUntilClaimed(t *testing.T) {
	ctx := context.Background()
	databasePath := filepath.Join(t.TempDir(), "run-control.sqlite")
	submitter, err := Open(ctx, databasePath, WithOwnerEpoch("queue_submitter"))
	if err != nil {
		t.Fatal(err)
	}
	queued, err := submitter.EnqueueRun(ctx, CreateRunParams{
		RunID:        "run_queued_claim",
		Kind:         "quick",
		SubjectType:  "feature",
		SubjectID:    "queued-claim",
		TargetRef:    "HEAD",
		IntentSHA256: digestForTest("queued claim"),
	})
	if err != nil {
		t.Fatal(err)
	}
	if err := submitter.Close(); err != nil {
		t.Fatal(err)
	}

	supervisor := openTestStore(t, databasePath, WithOwnerEpoch("queue_supervisor"))
	interrupted, err := supervisor.ReconcileOwnerEpoch(ctx, time.Now().UTC())
	if err != nil {
		t.Fatal(err)
	}
	if len(interrupted) != 0 {
		t.Fatalf("queued reconciliation interrupted = %#v, want none", interrupted)
	}
	claimed, err := supervisor.ClaimRun(ctx, queued.RunID, queued.Revision)
	if err != nil {
		t.Fatal(err)
	}
	if claimed.Status != RunAllocating || claimed.Revision != queued.Revision+1 || claimed.OwnerEpoch != "queue_supervisor" {
		t.Fatalf("claimed run = %#v, want allocating revision 2 owned by queue_supervisor", claimed)
	}
	events, err := supervisor.ListRunEvents(ctx, queued.RunID)
	if err != nil {
		t.Fatal(err)
	}
	if len(events) != 2 || events[0].EventType != RunEventCreated || events[1].EventType != RunEventClaimed {
		t.Fatalf("queued run events = %#v, want created then claimed", events)
	}
}
