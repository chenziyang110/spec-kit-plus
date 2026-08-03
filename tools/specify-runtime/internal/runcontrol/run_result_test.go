package runcontrol

import (
	"context"
	"testing"
)

func TestSuccessfulSupervisionSealsRuntimeDerivedRunResult(t *testing.T) {
	t.Setenv(foregroundHelperEnvironment, "1")
	mainRoot, _ := createLinkedRepository(t)
	repository, err := ResolveRepository(context.Background(), mainRoot)
	if err != nil {
		t.Fatal(err)
	}
	enqueueForegroundTestRun(t, repository, "sealed_result_success")

	supervised, err := SuperviseRun(
		context.Background(),
		repository,
		foregroundTestParams("sealed_result_success", "write", "sealed-result.txt", "ready"),
	)
	if err != nil {
		t.Fatal(err)
	}
	if supervised.Run.Status != RunSealed || supervised.Attempt.Status != AttemptFinished {
		t.Fatalf("supervised execution = %#v, want sealed run and finished attempt", supervised)
	}

	observer := openTestStore(t, repository.DatabasePath, WithOwnerEpoch("sealed_result_observer"))
	results, err := observer.ListRunResults(context.Background(), supervised.Run.RunID)
	if err != nil {
		t.Fatal(err)
	}
	if len(results) != 1 {
		t.Fatalf("sealed run results = %#v, want exactly one append-only result", results)
	}

	result := results[0]
	if result.ResultID != supervised.Result.ResultID ||
		result.RunID != supervised.Run.RunID ||
		result.AttemptID != supervised.Attempt.AttemptID ||
		result.WorkspaceID != supervised.Workspace.WorkspaceID ||
		result.SnapshotID != supervised.Snapshot.SnapshotID {
		t.Fatalf("sealed result binding = %#v, want supervised execution identities", result)
	}
	if result.BaseCommitOID != supervised.Workspace.BaseCommit ||
		result.ResultTreeOID == "" || result.ResultCommitOID == "" ||
		result.ManifestSHA256 == "" || result.WorkspaceAttestationSHA256 == "" {
		t.Fatalf("sealed result = %#v, want runtime-derived immutable Git and attestation binding", result)
	}
	if result.Eligibility != ResultEligibilityReady {
		t.Fatalf("sealed result eligibility = %q, want %q", result.Eligibility, ResultEligibilityReady)
	}
}

func TestRunReopenAppendsResultAndSupersedesWithoutMutation(t *testing.T) {
	t.Setenv(foregroundHelperEnvironment, "1")
	ctx := context.Background()
	mainRoot, _ := createLinkedRepository(t)
	repository, err := ResolveRepository(ctx, mainRoot)
	if err != nil {
		t.Fatal(err)
	}
	enqueueForegroundTestRun(t, repository, "sealed_result_retry")

	first, err := SuperviseRun(
		ctx,
		repository,
		foregroundTestParams("sealed_result_retry", "write", "first.txt", "first"),
	)
	if err != nil {
		t.Fatal(err)
	}

	reopener := openTestStore(t, repository.DatabasePath, WithOwnerEpoch("sealed_result_reopener"))
	reopened, err := reopener.ReopenRun(ctx, ReopenRunParams{
		RunID:            first.Run.RunID,
		BasisResultID:    first.Result.ResultID,
		ExpectedRevision: first.Run.Revision,
		Reason:           "repair after sealed result",
	})
	if err != nil {
		t.Fatal(err)
	}
	if reopened.Status != RunQueued {
		t.Fatalf("reopened run status = %q, want %q", reopened.Status, RunQueued)
	}

	second, err := SuperviseRun(
		ctx,
		repository,
		foregroundTestParams("sealed_result_retry", "write", "second.txt", "second"),
	)
	if err != nil {
		t.Fatal(err)
	}

	results, err := reopener.ListRunResults(ctx, first.Run.RunID)
	if err != nil {
		t.Fatal(err)
	}
	if len(results) != 2 {
		t.Fatalf("sealed run results = %#v, want append-only history", results)
	}
	if results[0].ResultID != first.Result.ResultID || results[1].ResultID != second.Result.ResultID ||
		results[0].ResultRevision != 1 || results[1].ResultRevision != 2 {
		t.Fatalf("sealed result ordering = %#v, want revisions 1 then 2", results)
	}
	supersession, err := reopener.GetResultSupersession(ctx, first.Result.ResultID)
	if err != nil {
		t.Fatal(err)
	}
	if supersession.NewResultID != second.Result.ResultID || supersession.Reason == "" {
		t.Fatalf("result supersession = %#v, want second result replacement", supersession)
	}
}
