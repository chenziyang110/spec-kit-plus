package runcontrol

import (
	"context"
	"errors"
	"path/filepath"
	"testing"
	"time"
)

func TestResourceClaimsAllowSharedClaimsAndRejectExclusiveConflict(t *testing.T) {
	ctx := context.Background()
	store := openTestStore(t, filepath.Join(t.TempDir(), "run-control.sqlite"))
	now := time.Now().UTC()
	_, attemptA := createAuthorityActiveRun(t, store, "run_resource_shared_a", now)
	_, attemptB := createAuthorityActiveRun(t, store, "run_resource_shared_b", now)

	for index, attempt := range []Attempt{attemptA, attemptB} {
		if _, err := store.AcquireResourceClaim(ctx, AcquireResourceClaimParams{
			ClaimID:      []string{"claim_shared_a", "claim_shared_b"}[index],
			AttemptID:    attempt.AttemptID,
			Fence:        attempt.Fence,
			ResourceKind: ResourceTCPPort,
			ResourceKey:  "tcp:4100",
			Mode:         ResourceShared,
			BindingJSON:  `{"port":4100}`,
			LeaseUntil:   now.Add(time.Minute),
		}); err != nil {
			t.Fatalf("acquire shared resource claim %d: %v", index, err)
		}
	}

	if _, err := store.AcquireResourceClaim(ctx, AcquireResourceClaimParams{
		ClaimID:      "claim_exclusive_conflict",
		AttemptID:    attemptB.AttemptID,
		Fence:        attemptB.Fence,
		ResourceKind: ResourceTCPPort,
		ResourceKey:  "tcp:4100",
		Mode:         ResourceExclusive,
		BindingJSON:  `{"port":4100}`,
		LeaseUntil:   now.Add(time.Minute),
	}); !errors.Is(err, ErrResourceConflict) {
		t.Fatalf("exclusive resource conflict error = %v, want ErrResourceConflict", err)
	}

	claims, err := store.ListResourceClaimsForAttempt(ctx, attemptA.AttemptID)
	if err != nil {
		t.Fatal(err)
	}
	if len(claims) != 1 || claims[0].Mode != ResourceShared || claims[0].Status != ResourceClaimed {
		t.Fatalf("attempt A claims = %#v, want one active shared claim", claims)
	}
}

func TestFinishAttemptReleasesFenceScopedResourceClaims(t *testing.T) {
	ctx := context.Background()
	store := openTestStore(t, filepath.Join(t.TempDir(), "run-control.sqlite"))
	run, attempt := activeManagedExecutionForFinishTest(t, store, "resource_release")

	if _, err := store.AcquireResourceClaim(ctx, AcquireResourceClaimParams{
		ClaimID:      "claim_finish_release",
		AttemptID:    attempt.AttemptID,
		Fence:        attempt.Fence,
		ResourceKind: ResourceFilesystem,
		ResourceKey:  attempt.WorkspaceID + "/edit-root",
		Mode:         ResourceExclusive,
		BindingJSON:  `{"scope":"workspace"}`,
		LeaseUntil:   time.Now().UTC().Add(time.Minute),
	}); err != nil {
		t.Fatalf("acquire releasable resource claim: %v", err)
	}

	if _, err := store.FinishAttempt(ctx, FinishAttemptParams{
		AttemptID: attempt.AttemptID,
		Fence:     attempt.Fence,
		Outcome:   AttemptOutcomeSucceeded,
		Reason:    "resource release contract",
	}); err != nil {
		t.Fatal(err)
	}

	claims, err := store.ListResourceClaimsForAttempt(ctx, attempt.AttemptID)
	if err != nil {
		t.Fatal(err)
	}
	if len(claims) != 1 || claims[0].RunID != run.RunID ||
		claims[0].Fence != attempt.Fence || claims[0].Status != ResourceReleased {
		t.Fatalf("finished attempt claims = %#v, want one released fence-bound claim", claims)
	}
}
