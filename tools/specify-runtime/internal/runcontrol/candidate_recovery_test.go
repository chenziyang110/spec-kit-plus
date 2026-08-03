package runcontrol

import (
	"context"
	"testing"
	"time"
)

func TestIntegrateNextRecoversTargetUpdateAfterSupervisorStops(t *testing.T) {
	t.Setenv(foregroundHelperEnvironment, "1")
	mainRoot, _ := createLinkedRepository(t)
	repository, err := ResolveRepository(context.Background(), mainRoot)
	if err != nil {
		t.Fatal(err)
	}
	enqueueForegroundTestRun(t, repository, "recover_merge")
	supervised, err := SuperviseRun(
		context.Background(),
		repository,
		foregroundTestParams("recover_merge", "write", "recovered.txt", "recovered"),
	)
	if err != nil {
		t.Fatal(err)
	}

	owner, err := Open(
		context.Background(),
		repository.DatabasePath,
		WithOwnerEpoch("integration_that_stops"),
	)
	if err != nil {
		t.Fatal(err)
	}
	candidate, integration, err := owner.claimNextCandidate(context.Background(), supervised.Candidate.TargetRef)
	if err != nil {
		t.Fatal(err)
	}
	targetRoot, err := checkedOutTargetWorktree(context.Background(), repository, candidate.TargetRef)
	if err != nil {
		t.Fatal(err)
	}
	targetBefore, err := validateTargetWorktreeReady(context.Background(), targetRoot, candidate.TargetRef)
	if err != nil {
		t.Fatal(err)
	}
	integration, err = owner.startCandidateIntegration(context.Background(), integration, targetBefore)
	if err != nil {
		t.Fatal(err)
	}
	targetAfter, conflicted, err := mergeCandidateIntoTarget(
		context.Background(),
		repository,
		targetRoot,
		candidate,
		targetBefore,
	)
	if err != nil || conflicted || targetAfter == targetBefore {
		t.Fatalf("Git integration before stop = after %q conflicted=%v err=%v", targetAfter, conflicted, err)
	}
	if err := owner.Close(); err != nil {
		t.Fatal(err)
	}

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	recovered, err := IntegrateNext(ctx, repository, IntegrateNextParams{
		TargetRef:  candidate.TargetRef,
		OwnerEpoch: "integration_recovery",
	})
	if err != nil {
		t.Fatal(err)
	}
	if recovered.Candidate.CandidateID != candidate.CandidateID ||
		recovered.Result.Status != ResultIntegrated ||
		recovered.Result.TargetBefore != targetBefore ||
		recovered.Result.TargetAfter != targetAfter {
		t.Fatalf("recovered integration = %#v", recovered)
	}
}

func TestIntegrateNextRequeuesPreparedClaimAfterSupervisorStops(t *testing.T) {
	t.Setenv(foregroundHelperEnvironment, "1")
	mainRoot, _ := createLinkedRepository(t)
	repository, err := ResolveRepository(context.Background(), mainRoot)
	if err != nil {
		t.Fatal(err)
	}
	enqueueForegroundTestRun(t, repository, "recover_claim")
	supervised, err := SuperviseRun(
		context.Background(),
		repository,
		foregroundTestParams("recover_claim", "write", "claimed.txt", "claimed"),
	)
	if err != nil {
		t.Fatal(err)
	}

	owner, err := Open(
		context.Background(),
		repository.DatabasePath,
		WithOwnerEpoch("prepared_claim_that_stops"),
	)
	if err != nil {
		t.Fatal(err)
	}
	if _, _, err := owner.claimNextCandidate(context.Background(), supervised.Candidate.TargetRef); err != nil {
		t.Fatal(err)
	}
	if err := owner.Close(); err != nil {
		t.Fatal(err)
	}

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	recovered, err := IntegrateNext(ctx, repository, IntegrateNextParams{
		TargetRef:  supervised.Candidate.TargetRef,
		OwnerEpoch: "prepared_claim_recovery",
	})
	if err != nil {
		t.Fatal(err)
	}
	if recovered.Result.Status != ResultIntegrated || recovered.Candidate.CandidateID != supervised.Candidate.CandidateID {
		t.Fatalf("requeued prepared claim outcome = %#v", recovered)
	}
}
