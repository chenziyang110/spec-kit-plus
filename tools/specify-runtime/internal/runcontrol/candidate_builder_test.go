package runcontrol

import (
	"context"
	"testing"
)

func TestBuildCandidateFreezesMultipleReadyResultsWithoutChangingTarget(t *testing.T) {
	t.Setenv(foregroundHelperEnvironment, "1")
	ctx := context.Background()
	mainRoot, _ := createLinkedRepository(t)
	repository, err := ResolveRepository(ctx, mainRoot)
	if err != nil {
		t.Fatal(err)
	}
	targetBefore := runGit(t, ensureGitAvailable(t), mainRoot, "rev-parse", "HEAD")

	resultA := superviseCandidateResult(t, repository, "candidate_result_a", "feature-a.txt", "A")
	resultB := superviseCandidateResult(t, repository, "candidate_result_b", "feature-b.txt", "B")
	candidate, err := BuildFrozenCandidate(ctx, repository, BuildFrozenCandidateParams{
		TargetRef: "refs/heads/main",
		ResultIDs: []string{resultB.ResultID, resultA.ResultID},
	})
	if err != nil {
		t.Fatal(err)
	}
	if candidate.ManifestSHA256 == "" || candidate.TreeOID == "" || candidate.CommitOID == "" ||
		candidate.ExpectedTargetOID != targetBefore {
		t.Fatalf("candidate = %#v, want immutable target/tree/manifest binding", candidate)
	}
	wantOrder := []string{resultB.ResultID, resultA.ResultID}
	if !equalStrings(candidate.MemberResultIDs, wantOrder) {
		t.Fatalf("candidate member order = %#v, want %#v", candidate.MemberResultIDs, wantOrder)
	}
	if got := runGit(t, ensureGitAvailable(t), mainRoot, "rev-parse", "HEAD"); got != targetBefore {
		t.Fatalf("candidate build modified target ref: got %q want %q", got, targetBefore)
	}
	if got := runGit(t, ensureGitAvailable(t), mainRoot, "show", candidate.CommitOID+":feature-a.txt"); got != "A" {
		t.Fatalf("candidate feature A = %q, want A", got)
	}
	if got := runGit(t, ensureGitAvailable(t), mainRoot, "show", candidate.CommitOID+":feature-b.txt"); got != "B" {
		t.Fatalf("candidate feature B = %q, want B", got)
	}
}

func TestBuildCandidateExpandsPersistedDependencyClosureInRequestedOrder(t *testing.T) {
	t.Setenv(foregroundHelperEnvironment, "1")
	ctx := context.Background()
	mainRoot, _ := createLinkedRepository(t)
	repository, err := ResolveRepository(ctx, mainRoot)
	if err != nil {
		t.Fatal(err)
	}
	domain := superviseCandidateResult(t, repository, "candidate_domain", "domain.txt", "domain")
	ui := superviseCandidateResult(t, repository, "candidate_ui", "ui.txt", "ui")
	docs := superviseCandidateResult(t, repository, "candidate_docs", "docs.txt", "docs")

	store := openTestStore(t, repository.DatabasePath, WithOwnerEpoch("candidate_dependency_writer"))
	if _, err := store.AddResultDependency(ctx, AddResultDependencyParams{
		ResultID:          ui.ResultID,
		DependsOnResultID: domain.ResultID,
		Kind:              ResultDependencyRequires,
		Reason:            "UI consumes the domain contract",
	}); err != nil {
		t.Fatal(err)
	}

	candidate, err := BuildFrozenCandidate(ctx, repository, BuildFrozenCandidateParams{
		TargetRef: "refs/heads/main",
		ResultIDs: []string{ui.ResultID, docs.ResultID},
	})
	if err != nil {
		t.Fatal(err)
	}
	wantOrder := []string{domain.ResultID, ui.ResultID, docs.ResultID}
	if !equalStrings(candidate.MemberResultIDs, wantOrder) {
		t.Fatalf("candidate dependency closure = %#v, want %#v", candidate.MemberResultIDs, wantOrder)
	}
	loaded, err := store.GetFrozenCandidate(ctx, candidate.CandidateID)
	if err != nil {
		t.Fatal(err)
	}
	if loaded.ManifestSHA256 != candidate.ManifestSHA256 ||
		!equalStrings(loaded.MemberResultIDs, candidate.MemberResultIDs) {
		t.Fatalf("stored candidate mutated: built=%#v loaded=%#v", candidate, loaded)
	}
}

func superviseCandidateResult(
	t *testing.T,
	repository Repository,
	runID string,
	path string,
	content string,
) RunResult {
	t.Helper()
	enqueueForegroundTestRun(t, repository, runID)
	params := foregroundTestParams(runID, "write-exact", path, content)
	params.WorkspacePolicy = WorkspacePolicyIsolated
	supervised, err := SuperviseRun(
		context.Background(),
		repository,
		params,
	)
	if err != nil {
		t.Fatal(err)
	}
	if supervised.Result.Eligibility != ResultEligibilityReady {
		t.Fatalf("result %s eligibility = %q, want ready", supervised.Result.ResultID, supervised.Result.Eligibility)
	}
	return supervised.Result
}

func equalStrings(left, right []string) bool {
	if len(left) != len(right) {
		return false
	}
	for index := range left {
		if left[index] != right[index] {
			return false
		}
	}
	return true
}
