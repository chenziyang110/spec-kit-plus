package runcontrol

import (
	"context"
	"errors"
	"os"
	"path/filepath"
	"testing"
)

func TestCandidateReviewRequiresExplicitAcceptanceBeforeCASPublishAndSafeSync(t *testing.T) {
	t.Setenv(foregroundHelperEnvironment, "1")
	ctx := context.Background()
	mainRoot, _ := createLinkedRepository(t)
	repository, err := ResolveRepository(ctx, mainRoot)
	if err != nil {
		t.Fatal(err)
	}
	result := superviseCandidateResult(t, repository, "candidate_delivery", "delivery.txt", "approved")
	candidate, err := BuildFrozenCandidate(ctx, repository, BuildFrozenCandidateParams{
		TargetRef: "refs/heads/main",
		ResultIDs: []string{result.ResultID},
	})
	if err != nil {
		t.Fatal(err)
	}
	review, err := ReviewFrozenCandidate(ctx, repository, ReviewFrozenCandidateParams{
		CandidateID: candidate.CandidateID,
		Reviewer:    "runtime-review",
		Commands:    [][]string{{ensureGitAvailable(t), "diff", "--quiet"}},
	})
	if err != nil {
		t.Fatal(err)
	}
	if review.Status != CandidateReviewPassed || review.CandidateManifestSHA256 != candidate.ManifestSHA256 ||
		review.CandidateTreeOID != candidate.TreeOID || review.ReviewDigest == "" || review.EvidenceDigest == "" {
		t.Fatalf("Candidate Review = %#v, want passed exact Candidate binding", review)
	}
	if _, err := PublishFrozenCandidate(ctx, repository, PublishFrozenCandidateParams{
		CandidateID: candidate.CandidateID,
	}); !errors.Is(err, ErrAcceptanceRequired) {
		t.Fatalf("publish before acceptance error = %v, want ErrAcceptanceRequired", err)
	}
	if _, err := RecordCandidateAcceptance(ctx, repository, CandidateAcceptanceParams{
		CandidateID: candidate.CandidateID,
		ReviewDigest: "wrong-review-digest",
		Decision:     CandidateAccepted,
		Actor:        "test-user",
	}); !errors.Is(err, ErrReviewBinding) {
		t.Fatalf("accept stale Review error = %v, want ErrReviewBinding", err)
	}
	acceptance, err := RecordCandidateAcceptance(ctx, repository, CandidateAcceptanceParams{
		CandidateID: candidate.CandidateID,
		ReviewDigest: review.ReviewDigest,
		Decision:     CandidateAccepted,
		Actor:        "test-user",
	})
	if err != nil {
		t.Fatal(err)
	}
	publication, err := PublishFrozenCandidate(ctx, repository, PublishFrozenCandidateParams{
		CandidateID:     candidate.CandidateID,
		AcceptanceDigest: acceptance.AcceptanceDigest,
	})
	if err != nil {
		t.Fatal(err)
	}
	if publication.TargetBefore != candidate.ExpectedTargetOID || publication.TargetAfter != candidate.CommitOID ||
		publication.PublicationDigest == "" {
		t.Fatalf("publication = %#v, want Candidate CAS receipt", publication)
	}
	if got := runGit(t, ensureGitAvailable(t), mainRoot, "rev-parse", "refs/heads/main"); got != candidate.CommitOID {
		t.Fatalf("published target = %q, want %q", got, candidate.CommitOID)
	}
	if _, err := SyncPublishedCandidate(ctx, repository, SyncPublishedCandidateParams{
		CandidateID:       candidate.CandidateID,
		PublicationDigest: publication.PublicationDigest,
	}); err != nil {
		t.Fatal(err)
	}
	if status := runGit(t, ensureGitAvailable(t), mainRoot, "status", "--porcelain"); status != "" {
		t.Fatalf("safe-synced primary worktree is dirty: %q", status)
	}
	if got := runGit(t, ensureGitAvailable(t), mainRoot, "show", "HEAD:delivery.txt"); got != "approved" {
		t.Fatalf("safe-synced delivery content = %q, want approved", got)
	}
}

func TestCandidatePublishRejectsTargetDriftWithoutOverwritingIt(t *testing.T) {
	t.Setenv(foregroundHelperEnvironment, "1")
	ctx := context.Background()
	mainRoot, _ := createLinkedRepository(t)
	repository, err := ResolveRepository(ctx, mainRoot)
	if err != nil {
		t.Fatal(err)
	}
	result := superviseCandidateResult(t, repository, "candidate_drift", "candidate.txt", "candidate")
	candidate, err := BuildFrozenCandidate(ctx, repository, BuildFrozenCandidateParams{
		TargetRef: "refs/heads/main",
		ResultIDs: []string{result.ResultID},
	})
	if err != nil {
		t.Fatal(err)
	}
	review, err := ReviewFrozenCandidate(ctx, repository, ReviewFrozenCandidateParams{
		CandidateID: candidate.CandidateID,
		Reviewer:    "runtime-review",
	})
	if err != nil {
		t.Fatal(err)
	}
	acceptance, err := RecordCandidateAcceptance(ctx, repository, CandidateAcceptanceParams{
		CandidateID: candidate.CandidateID,
		ReviewDigest: review.ReviewDigest,
		Decision:     CandidateAccepted,
		Actor:        "test-user",
	})
	if err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(mainRoot, "target-drift.txt"), []byte("drift"), 0o644); err != nil {
		t.Fatal(err)
	}
	runGit(t, ensureGitAvailable(t), mainRoot, "add", "target-drift.txt")
	runGit(t, ensureGitAvailable(t), mainRoot, "commit", "-m", "target drift")
	driftOID := runGit(t, ensureGitAvailable(t), mainRoot, "rev-parse", "HEAD")
	if _, err := PublishFrozenCandidate(ctx, repository, PublishFrozenCandidateParams{
		CandidateID: candidate.CandidateID, AcceptanceDigest: acceptance.AcceptanceDigest,
	}); !errors.Is(err, ErrCandidateStale) {
		t.Fatalf("drifted publish error = %v, want ErrCandidateStale", err)
	}
	if got := runGit(t, ensureGitAvailable(t), mainRoot, "rev-parse", "HEAD"); got != driftOID {
		t.Fatalf("drifted target was overwritten: got %q want %q", got, driftOID)
	}
}
