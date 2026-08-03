package runcontrol

import (
	"context"
	"errors"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"
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
		CandidateID:  candidate.CandidateID,
		ReviewDigest: "wrong-review-digest",
		Decision:     CandidateAccepted,
		Actor:        "test-user",
	}); !errors.Is(err, ErrReviewBinding) {
		t.Fatalf("accept stale Review error = %v, want ErrReviewBinding", err)
	}
	acceptance, err := RecordCandidateAcceptance(ctx, repository, CandidateAcceptanceParams{
		CandidateID:  candidate.CandidateID,
		ReviewDigest: review.ReviewDigest,
		Decision:     CandidateAccepted,
		Actor:        "test-user",
	})
	if err != nil {
		t.Fatal(err)
	}
	guardStore := openTestStore(t, repository.DatabasePath)
	guardRun, err := guardStore.EnqueueRun(ctx, CreateRunParams{
		RunID: "candidate_delivery_primary_guard", Kind: "quick",
		SubjectType: "feature", SubjectID: "delivery-guard", TargetRef: "refs/heads/main",
		IntentSHA256: strings.Repeat("d", 64),
	})
	if err != nil {
		t.Fatal(err)
	}
	setPrimaryGuard := func() {
		t.Helper()
		if _, err := guardStore.db.ExecContext(ctx, `
			INSERT INTO primary_workspace_slots (slot_id, run_id, owner_epoch, root_path, acquired_at_ms)
			VALUES (1, ?, ?, ?, ?)
		`, guardRun.RunID, guardStore.ownerEpoch, repository.PrimaryRoot, time.Now().UTC().UnixMilli()); err != nil {
			t.Fatal(err)
		}
	}
	clearPrimaryGuard := func() {
		t.Helper()
		if _, err := guardStore.db.ExecContext(ctx, `DELETE FROM primary_workspace_slots WHERE slot_id = 1`); err != nil {
			t.Fatal(err)
		}
	}
	setPrimaryGuard()
	if _, err := PublishFrozenCandidate(ctx, repository, PublishFrozenCandidateParams{
		CandidateID: candidate.CandidateID, AcceptanceDigest: acceptance.AcceptanceDigest,
	}); !errors.Is(err, ErrResourceConflict) {
		t.Fatalf("publish while primary workspace is active error = %v, want ErrResourceConflict", err)
	}
	if got := runGit(t, ensureGitAvailable(t), mainRoot, "rev-parse", "refs/heads/main"); got != candidate.ExpectedTargetOID {
		t.Fatalf("guarded publish changed target to %q, want %q", got, candidate.ExpectedTargetOID)
	}
	clearPrimaryGuard()
	publication, err := PublishFrozenCandidate(ctx, repository, PublishFrozenCandidateParams{
		CandidateID:      candidate.CandidateID,
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
	if _, err := PublishFrozenCandidate(ctx, repository, PublishFrozenCandidateParams{
		CandidateID: candidate.CandidateID, AcceptanceDigest: strings.Repeat("0", 64),
	}); !errors.Is(err, ErrAcceptanceRequired) {
		t.Fatalf("published Candidate replay with wrong acceptance error = %v, want ErrAcceptanceRequired", err)
	}
	setPrimaryGuard()
	if _, err := SyncPublishedCandidate(ctx, repository, SyncPublishedCandidateParams{
		CandidateID: candidate.CandidateID, PublicationDigest: publication.PublicationDigest,
	}); !errors.Is(err, ErrSyncUnsafe) {
		t.Fatalf("sync while primary workspace is active error = %v, want ErrSyncUnsafe", err)
	}
	if _, err := os.Stat(filepath.Join(mainRoot, "delivery.txt")); !errors.Is(err, os.ErrNotExist) {
		t.Fatalf("guarded sync changed primary worktree: %v", err)
	}
	clearPrimaryGuard()
	// Simulate a process interruption after reset but before the durable Sync
	// receipt. The retry must recognize the already-synchronized clean tree.
	runGit(t, ensureGitAvailable(t), mainRoot, "reset", "--hard", candidate.CommitOID)
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

func TestCandidatePublishAndSyncPreserveOnlyTheSealedPrimaryRunState(t *testing.T) {
	t.Setenv(foregroundHelperEnvironment, "1")
	ctx := context.Background()
	mainRoot, _ := createLinkedRepository(t)
	repository, err := ResolveRepository(ctx, mainRoot)
	if err != nil {
		t.Fatal(err)
	}
	enqueueForegroundTestRun(t, repository, "candidate_primary_delivery")
	params := foregroundTestParams(
		"candidate_primary_delivery",
		"write-exact",
		"primary-delivery.txt",
		"sealed primary content",
	)
	params.WorkspacePolicy = WorkspacePolicyPrimary
	supervised, err := SuperviseRun(ctx, repository, params)
	if err != nil {
		t.Fatal(err)
	}
	if supervised.Workspace.Mode != WorkspaceModePrimary || supervised.Result.Eligibility != ResultEligibilityReady {
		t.Fatalf("primary execution = %#v", supervised)
	}
	candidate, err := BuildFrozenCandidate(ctx, repository, BuildFrozenCandidateParams{
		TargetRef: "refs/heads/main", ResultIDs: []string{supervised.Result.ResultID},
	})
	if err != nil {
		t.Fatal(err)
	}
	review, err := ReviewFrozenCandidate(ctx, repository, ReviewFrozenCandidateParams{
		CandidateID: candidate.CandidateID, Reviewer: "runtime-review",
	})
	if err != nil {
		t.Fatal(err)
	}
	acceptance, err := RecordCandidateAcceptance(ctx, repository, CandidateAcceptanceParams{
		CandidateID: candidate.CandidateID, ReviewDigest: review.ReviewDigest,
		Decision: CandidateAccepted, Actor: "test-user",
	})
	if err != nil {
		t.Fatal(err)
	}

	unexpectedPath := filepath.Join(mainRoot, "unsealed-user-change.txt")
	if err := os.WriteFile(unexpectedPath, []byte("must survive"), 0o644); err != nil {
		t.Fatal(err)
	}
	if _, err := PublishFrozenCandidate(ctx, repository, PublishFrozenCandidateParams{
		CandidateID: candidate.CandidateID, AcceptanceDigest: acceptance.AcceptanceDigest,
	}); !errors.Is(err, ErrTargetWorktreeDirty) {
		t.Fatalf("publish with unsealed primary drift error = %v, want ErrTargetWorktreeDirty", err)
	}
	if _, err := os.Stat(unexpectedPath); err != nil {
		t.Fatalf("blocked publication changed unsealed user file: %v", err)
	}
	if err := os.Remove(unexpectedPath); err != nil {
		t.Fatal(err)
	}

	publication, err := PublishFrozenCandidate(ctx, repository, PublishFrozenCandidateParams{
		CandidateID: candidate.CandidateID, AcceptanceDigest: acceptance.AcceptanceDigest,
	})
	if err != nil {
		t.Fatal(err)
	}
	if _, err := SyncPublishedCandidate(ctx, repository, SyncPublishedCandidateParams{
		CandidateID: candidate.CandidateID, PublicationDigest: publication.PublicationDigest,
	}); err != nil {
		t.Fatal(err)
	}
	if status := runGit(t, ensureGitAvailable(t), mainRoot, "status", "--porcelain"); status != "" {
		t.Fatalf("primary worktree after accounted sync is dirty: %q", status)
	}
	if got := runGit(t, ensureGitAvailable(t), mainRoot, "show", "HEAD:primary-delivery.txt"); got != "sealed primary content" {
		t.Fatalf("published primary Result content = %q", got)
	}
}

func TestCandidatePublishRecoversExecutingJournalAfterTargetCAS(t *testing.T) {
	t.Setenv(foregroundHelperEnvironment, "1")
	ctx := context.Background()
	mainRoot, _ := createLinkedRepository(t)
	repository, err := ResolveRepository(ctx, mainRoot)
	if err != nil {
		t.Fatal(err)
	}
	result := superviseCandidateResult(t, repository, "candidate_publish_recovery", "recovered.txt", "recovered")
	candidate, err := BuildFrozenCandidate(ctx, repository, BuildFrozenCandidateParams{
		TargetRef: "refs/heads/main", ResultIDs: []string{result.ResultID},
	})
	if err != nil {
		t.Fatal(err)
	}
	review, err := ReviewFrozenCandidate(ctx, repository, ReviewFrozenCandidateParams{
		CandidateID: candidate.CandidateID, Reviewer: "runtime-review",
	})
	if err != nil {
		t.Fatal(err)
	}
	acceptance, err := RecordCandidateAcceptance(ctx, repository, CandidateAcceptanceParams{
		CandidateID: candidate.CandidateID, ReviewDigest: review.ReviewDigest,
		Decision: CandidateAccepted, Actor: "test-user",
	})
	if err != nil {
		t.Fatal(err)
	}
	expectedTree := runGit(t, ensureGitAvailable(t), mainRoot, "rev-parse", candidate.ExpectedTargetOID+"^{tree}")
	nowMS := time.Now().UTC().UnixMilli()
	publicationDigest, err := digestCanonicalJSON(struct {
		CandidateID       string `json:"candidate_id"`
		CandidateManifest string `json:"candidate_manifest"`
		ReviewDigest      string `json:"review_digest"`
		AcceptanceDigest  string `json:"acceptance_digest"`
		TargetRef         string `json:"target_ref"`
		TargetBefore      string `json:"target_before"`
		TargetAfter       string `json:"target_after"`
	}{
		candidate.CandidateID, candidate.ManifestSHA256, review.ReviewDigest,
		acceptance.AcceptanceDigest, candidate.TargetRef,
		candidate.ExpectedTargetOID, candidate.CommitOID,
	})
	if err != nil {
		t.Fatal(err)
	}
	publicationID := "publication-" + publicationDigest[:24]
	store := openTestStore(t, repository.DatabasePath)
	if _, err := store.db.ExecContext(ctx, `
		INSERT INTO candidate_publications (
			publication_id, candidate_id, acceptance_id, target_ref, target_before,
			target_after, expected_index_tree_oid, status, publication_digest, reason,
			created_at_ms, updated_at_ms
		) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, '', ?, ?)
	`, publicationID, candidate.CandidateID, acceptance.AcceptanceID, candidate.TargetRef,
		candidate.ExpectedTargetOID, candidate.CommitOID, expectedTree,
		CandidatePublicationExecuting, publicationDigest, nowMS, nowMS); err != nil {
		t.Fatal(err)
	}
	runGit(t, ensureGitAvailable(t), mainRoot, "update-ref", candidate.TargetRef, candidate.CommitOID, candidate.ExpectedTargetOID)

	recovered, err := PublishFrozenCandidate(ctx, repository, PublishFrozenCandidateParams{
		CandidateID: candidate.CandidateID, AcceptanceDigest: acceptance.AcceptanceDigest,
	})
	if err != nil {
		t.Fatal(err)
	}
	if recovered.PublicationID != publicationID || recovered.Status != CandidatePublicationSucceeded ||
		recovered.PublicationDigest != publicationDigest {
		t.Fatalf("recovered publication = %#v", recovered)
	}
	var status CandidatePublicationStatus
	if err := store.db.QueryRowContext(ctx, `
		SELECT status FROM candidate_publications WHERE publication_id = ?
	`, publicationID).Scan(&status); err != nil {
		t.Fatal(err)
	}
	if status != CandidatePublicationSucceeded {
		t.Fatalf("persisted recovered publication status = %q, want succeeded", status)
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
		CandidateID:  candidate.CandidateID,
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
