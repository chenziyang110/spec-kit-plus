package runcontrol

import (
	"bytes"
	"context"
	"database/sql"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"sort"
	"strings"
	"time"
)

var (
	ErrAcceptanceRequired = errors.New("Candidate requires explicit human acceptance")
	ErrPublicationUnknown = errors.New("Candidate publication outcome is unknown and must be resumed")
	ErrReviewBinding      = errors.New("Candidate Review binding is stale or invalid")
	ErrSyncUnsafe         = errors.New("published Candidate cannot safely synchronize the user worktree")
)

type CandidateReviewStatus string

const (
	CandidateReviewPassed CandidateReviewStatus = "passed"
	CandidateReviewFailed CandidateReviewStatus = "failed"
)

type CandidateReview struct {
	ReviewID                string
	CandidateID             string
	CandidateManifestSHA256 string
	CandidateTreeOID        string
	CandidateCommitOID      string
	Reviewer                string
	Status                  CandidateReviewStatus
	EvidenceDigest          string
	ReviewDigest            string
	CreatedAtMS             int64
}

type ReviewFrozenCandidateParams struct {
	CandidateID string
	Reviewer    string
	Commands    [][]string
}

type CandidateAcceptanceDecision string

const (
	CandidateAccepted CandidateAcceptanceDecision = "accepted"
	CandidateRejected CandidateAcceptanceDecision = "rejected"
)

type CandidateAcceptance struct {
	AcceptanceID     string
	CandidateID      string
	ReviewID         string
	ReviewDigest     string
	EvidenceDigest   string
	Decision         CandidateAcceptanceDecision
	Actor            string
	AcceptanceDigest string
	CreatedAtMS      int64
}

type CandidateAcceptanceParams struct {
	CandidateID  string
	ReviewDigest string
	Decision     CandidateAcceptanceDecision
	Actor        string
}

type CandidatePublicationStatus string

const (
	CandidatePublicationPrepared  CandidatePublicationStatus = "prepared"
	CandidatePublicationExecuting CandidatePublicationStatus = "executing"
	CandidatePublicationSucceeded CandidatePublicationStatus = "succeeded"
	CandidatePublicationStale     CandidatePublicationStatus = "stale"
	CandidatePublicationUnknown   CandidatePublicationStatus = "outcome_unknown"
)

type CandidatePublication struct {
	PublicationID        string
	CandidateID          string
	AcceptanceID         string
	TargetRef            string
	TargetBefore         string
	TargetAfter          string
	ExpectedIndexTreeOID string
	Status               CandidatePublicationStatus
	PublicationDigest    string
	CreatedAtMS          int64
	UpdatedAtMS          int64
}

type PublishFrozenCandidateParams struct {
	CandidateID      string
	AcceptanceDigest string
}

type CandidateSync struct {
	SyncID        string
	CandidateID   string
	PublicationID string
	WorktreeRoot  string
	Status        string
	SyncDigest    string
	CreatedAtMS   int64
}

type SyncPublishedCandidateParams struct {
	CandidateID       string
	PublicationDigest string
	TargetRef         string
}

const candidateDeliverySchemaSQL = `
CREATE TABLE IF NOT EXISTS candidate_reviews (
    review_id TEXT PRIMARY KEY,
    candidate_id TEXT NOT NULL REFERENCES frozen_candidates(candidate_id) ON DELETE RESTRICT,
    candidate_manifest_sha256 TEXT NOT NULL,
    candidate_tree_oid TEXT NOT NULL,
    candidate_commit_oid TEXT NOT NULL,
    reviewer TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('passed', 'failed')),
    evidence_digest TEXT NOT NULL CHECK (
        length(evidence_digest) = 64 AND evidence_digest NOT GLOB '*[^0-9a-f]*'
    ),
    review_digest TEXT NOT NULL UNIQUE CHECK (
        length(review_digest) = 64 AND review_digest NOT GLOB '*[^0-9a-f]*'
    ),
    evidence_json TEXT NOT NULL,
    created_at_ms INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS candidate_reviews_latest
    ON candidate_reviews(candidate_id, created_at_ms, review_id);

CREATE TABLE IF NOT EXISTS candidate_acceptances (
    acceptance_id TEXT PRIMARY KEY,
    candidate_id TEXT NOT NULL REFERENCES frozen_candidates(candidate_id) ON DELETE RESTRICT,
    review_id TEXT NOT NULL REFERENCES candidate_reviews(review_id) ON DELETE RESTRICT,
    review_digest TEXT NOT NULL,
    evidence_digest TEXT NOT NULL,
    decision TEXT NOT NULL CHECK (decision IN ('accepted', 'rejected')),
    actor TEXT NOT NULL,
    acceptance_digest TEXT NOT NULL UNIQUE CHECK (
        length(acceptance_digest) = 64 AND acceptance_digest NOT GLOB '*[^0-9a-f]*'
    ),
    created_at_ms INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS candidate_acceptances_latest
    ON candidate_acceptances(candidate_id, created_at_ms, acceptance_id);

CREATE TABLE IF NOT EXISTS candidate_publications (
    publication_id TEXT PRIMARY KEY,
    candidate_id TEXT NOT NULL REFERENCES frozen_candidates(candidate_id) ON DELETE RESTRICT,
    acceptance_id TEXT NOT NULL REFERENCES candidate_acceptances(acceptance_id) ON DELETE RESTRICT,
    target_ref TEXT NOT NULL,
    target_before TEXT NOT NULL,
    target_after TEXT NOT NULL,
    expected_index_tree_oid TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('prepared', 'executing', 'succeeded', 'stale', 'outcome_unknown')),
    publication_digest TEXT NOT NULL UNIQUE CHECK (
        length(publication_digest) = 64 AND publication_digest NOT GLOB '*[^0-9a-f]*'
    ),
    reason TEXT NOT NULL DEFAULT '',
    created_at_ms INTEGER NOT NULL,
    updated_at_ms INTEGER NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS candidate_publications_one_success
    ON candidate_publications(candidate_id) WHERE status = 'succeeded';

CREATE TABLE IF NOT EXISTS candidate_syncs (
    sync_id TEXT PRIMARY KEY,
    candidate_id TEXT NOT NULL REFERENCES frozen_candidates(candidate_id) ON DELETE RESTRICT,
    publication_id TEXT NOT NULL REFERENCES candidate_publications(publication_id) ON DELETE RESTRICT,
    worktree_root TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('succeeded')),
    sync_digest TEXT NOT NULL UNIQUE,
    created_at_ms INTEGER NOT NULL,
    UNIQUE (publication_id, worktree_root)
);
`

func ReviewFrozenCandidate(
	ctx context.Context,
	repository Repository,
	params ReviewFrozenCandidateParams,
) (review CandidateReview, returnErr error) {
	if strings.TrimSpace(params.CandidateID) == "" || strings.TrimSpace(params.Reviewer) == "" {
		return CandidateReview{}, fmt.Errorf("%w: Candidate id and reviewer are required", ErrInvalidArgument)
	}
	canonical, err := canonicalAllocationRepository(ctx, repository)
	if err != nil {
		return CandidateReview{}, err
	}
	store, err := Open(ctx, canonical.DatabasePath)
	if err != nil {
		return CandidateReview{}, err
	}
	defer func() {
		if closeErr := store.Close(); closeErr != nil {
			returnErr = errors.Join(returnErr, closeErr)
		}
	}()
	candidate, err := store.GetFrozenCandidate(ctx, params.CandidateID)
	if err != nil {
		return CandidateReview{}, err
	}
	if err := verifyFrozenCandidateGitBinding(ctx, canonical, candidate); err != nil {
		return CandidateReview{}, err
	}
	commands := params.Commands
	if len(commands) == 0 {
		commands = [][]string{{"git", "diff", "--quiet"}}
	}
	commandDigest, err := digestCanonicalJSON(commands)
	if err != nil {
		return CandidateReview{}, err
	}
	workspaceRoot := filepath.Join(
		canonical.CommonDir,
		"specify-runtime", "worktrees", "reviews",
		candidate.CandidateID+"-"+commandDigest[:12],
	)
	if err := safeMkdirAllWithin(canonical.CommonDir, filepath.Dir(workspaceRoot)); err != nil {
		return CandidateReview{}, err
	}
	if _, err := os.Lstat(workspaceRoot); err == nil {
		return CandidateReview{}, fmt.Errorf("%w: Review workspace %q already exists", ErrWorkspaceConflict, workspaceRoot)
	} else if !errors.Is(err, os.ErrNotExist) {
		return CandidateReview{}, err
	}
	if err := runGitMutationWithRetry(ctx, canonical.Root, "worktree", "add", "--detach", workspaceRoot, candidate.CommitOID); err != nil {
		return CandidateReview{}, fmt.Errorf("materialize Candidate Review workspace: %w", err)
	}
	defer func() {
		_ = runGitMutationWithRetry(context.Background(), canonical.Root, "worktree", "remove", "--force", workspaceRoot)
	}()
	type commandEvidence struct {
		Ordinal      int      `json:"ordinal"`
		Argv         []string `json:"argv"`
		ExitCode     int      `json:"exit_code"`
		StdoutSHA256 string   `json:"stdout_sha256"`
		StderrSHA256 string   `json:"stderr_sha256"`
	}
	evidence := make([]commandEvidence, 0, len(commands))
	status := CandidateReviewPassed
	for index, argv := range commands {
		exitCode, stdoutDigest, stderrDigest, runErr := runCandidateReviewCommand(ctx, workspaceRoot, argv)
		if runErr != nil && !errors.Is(runErr, errReviewCommandFailed) {
			return CandidateReview{}, runErr
		}
		evidence = append(evidence, commandEvidence{
			Ordinal: index + 1, Argv: append([]string(nil), argv...), ExitCode: exitCode,
			StdoutSHA256: stdoutDigest, StderrSHA256: stderrDigest,
		})
		if exitCode != 0 {
			status = CandidateReviewFailed
			break
		}
	}
	evidenceJSON, err := canonicalJSON(evidence)
	if err != nil {
		return CandidateReview{}, err
	}
	evidenceDigest := sha256String(evidenceJSON)
	nowMS := time.Now().UTC().UnixMilli()
	reviewDigest, err := digestCanonicalJSON(struct {
		CandidateID             string                `json:"candidate_id"`
		CandidateManifestSHA256 string                `json:"candidate_manifest_sha256"`
		CandidateTreeOID        string                `json:"candidate_tree_oid"`
		CandidateCommitOID      string                `json:"candidate_commit_oid"`
		Reviewer                string                `json:"reviewer"`
		Status                  CandidateReviewStatus `json:"status"`
		EvidenceDigest          string                `json:"evidence_digest"`
		CreatedAtMS             int64                 `json:"created_at_ms"`
	}{
		CandidateID: candidate.CandidateID, CandidateManifestSHA256: candidate.ManifestSHA256,
		CandidateTreeOID: candidate.TreeOID, CandidateCommitOID: candidate.CommitOID,
		Reviewer: params.Reviewer, Status: status, EvidenceDigest: evidenceDigest, CreatedAtMS: nowMS,
	})
	if err != nil {
		return CandidateReview{}, err
	}
	review = CandidateReview{
		ReviewID: "review-" + reviewDigest[:24], CandidateID: candidate.CandidateID,
		CandidateManifestSHA256: candidate.ManifestSHA256, CandidateTreeOID: candidate.TreeOID,
		CandidateCommitOID: candidate.CommitOID, Reviewer: params.Reviewer, Status: status,
		EvidenceDigest: evidenceDigest, ReviewDigest: reviewDigest, CreatedAtMS: nowMS,
	}
	if _, err := store.db.ExecContext(ctx, `
		INSERT INTO candidate_reviews (
			review_id, candidate_id, candidate_manifest_sha256, candidate_tree_oid,
			candidate_commit_oid, reviewer, status, evidence_digest, review_digest,
			evidence_json, created_at_ms
		) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
	`, review.ReviewID, review.CandidateID, review.CandidateManifestSHA256,
		review.CandidateTreeOID, review.CandidateCommitOID, review.Reviewer, review.Status,
		review.EvidenceDigest, review.ReviewDigest, evidenceJSON, review.CreatedAtMS); err != nil {
		if !isUniqueConstraintError(err) {
			return CandidateReview{}, fmt.Errorf("record Candidate Review: %w", err)
		}
	}
	return review, nil
}

func RecordCandidateAcceptance(
	ctx context.Context,
	repository Repository,
	params CandidateAcceptanceParams,
) (acceptance CandidateAcceptance, returnErr error) {
	if strings.TrimSpace(params.CandidateID) == "" || strings.TrimSpace(params.ReviewDigest) == "" ||
		strings.TrimSpace(params.Actor) == "" {
		return CandidateAcceptance{}, fmt.Errorf("%w: Candidate, Review digest, decision, and actor are required", ErrInvalidArgument)
	}
	if params.Decision != CandidateAccepted && params.Decision != CandidateRejected {
		return CandidateAcceptance{}, fmt.Errorf("%w: unsupported acceptance decision %q", ErrInvalidArgument, params.Decision)
	}
	canonical, err := canonicalAllocationRepository(ctx, repository)
	if err != nil {
		return CandidateAcceptance{}, err
	}
	store, err := Open(ctx, canonical.DatabasePath)
	if err != nil {
		return CandidateAcceptance{}, err
	}
	defer func() {
		if closeErr := store.Close(); closeErr != nil {
			returnErr = errors.Join(returnErr, closeErr)
		}
	}()
	candidate, err := store.GetFrozenCandidate(ctx, params.CandidateID)
	if err != nil {
		return CandidateAcceptance{}, err
	}
	review, err := latestCandidateReview(ctx, store, candidate.CandidateID)
	if err != nil || review.ReviewDigest != params.ReviewDigest || review.Status != CandidateReviewPassed ||
		review.CandidateManifestSHA256 != candidate.ManifestSHA256 || review.CandidateTreeOID != candidate.TreeOID {
		return CandidateAcceptance{}, fmt.Errorf("%w: acceptance does not name the latest passing Review", ErrReviewBinding)
	}
	nowMS := time.Now().UTC().UnixMilli()
	digest, err := digestCanonicalJSON(struct {
		CandidateID    string                      `json:"candidate_id"`
		ReviewDigest   string                      `json:"review_digest"`
		EvidenceDigest string                      `json:"evidence_digest"`
		Decision       CandidateAcceptanceDecision `json:"decision"`
		Actor          string                      `json:"actor"`
		CreatedAtMS    int64                       `json:"created_at_ms"`
	}{candidate.CandidateID, review.ReviewDigest, review.EvidenceDigest, params.Decision, params.Actor, nowMS})
	if err != nil {
		return CandidateAcceptance{}, err
	}
	acceptance = CandidateAcceptance{
		AcceptanceID: "acceptance-" + digest[:24], CandidateID: candidate.CandidateID,
		ReviewID: review.ReviewID, ReviewDigest: review.ReviewDigest,
		EvidenceDigest: review.EvidenceDigest, Decision: params.Decision, Actor: params.Actor,
		AcceptanceDigest: digest, CreatedAtMS: nowMS,
	}
	if _, err := store.db.ExecContext(ctx, `
		INSERT INTO candidate_acceptances (
			acceptance_id, candidate_id, review_id, review_digest, evidence_digest,
			decision, actor, acceptance_digest, created_at_ms
		) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
	`, acceptance.AcceptanceID, acceptance.CandidateID, acceptance.ReviewID,
		acceptance.ReviewDigest, acceptance.EvidenceDigest, acceptance.Decision,
		acceptance.Actor, acceptance.AcceptanceDigest, acceptance.CreatedAtMS); err != nil {
		return CandidateAcceptance{}, fmt.Errorf("record Candidate acceptance: %w", err)
	}
	return acceptance, nil
}

func PublishFrozenCandidate(
	ctx context.Context,
	repository Repository,
	params PublishFrozenCandidateParams,
) (publication CandidatePublication, returnErr error) {
	if strings.TrimSpace(params.CandidateID) == "" {
		return CandidatePublication{}, fmt.Errorf("%w: Candidate id is required", ErrInvalidArgument)
	}
	canonical, err := canonicalAllocationRepository(ctx, repository)
	if err != nil {
		return CandidatePublication{}, err
	}
	store, err := Open(ctx, canonical.DatabasePath)
	if err != nil {
		return CandidatePublication{}, err
	}
	defer func() {
		if closeErr := store.Close(); closeErr != nil {
			returnErr = errors.Join(returnErr, closeErr)
		}
	}()
	candidate, err := store.GetFrozenCandidate(ctx, params.CandidateID)
	if err != nil {
		return CandidatePublication{}, err
	}
	review, err := latestCandidateReview(ctx, store, candidate.CandidateID)
	if err != nil || review.Status != CandidateReviewPassed ||
		review.CandidateManifestSHA256 != candidate.ManifestSHA256 || review.CandidateTreeOID != candidate.TreeOID {
		return CandidatePublication{}, fmt.Errorf("%w: Candidate lacks an exact passing Review", ErrReviewBinding)
	}
	acceptance, err := latestCandidateAcceptance(ctx, store, candidate.CandidateID)
	if err != nil || acceptance.Decision != CandidateAccepted ||
		acceptance.ReviewDigest != review.ReviewDigest ||
		params.AcceptanceDigest == "" || params.AcceptanceDigest != acceptance.AcceptanceDigest {
		return CandidatePublication{}, fmt.Errorf("%w: Candidate lacks exact current acceptance", ErrAcceptanceRequired)
	}
	if err := verifyFrozenCandidateGitBinding(ctx, canonical, candidate); err != nil {
		return CandidatePublication{}, err
	}
	if existing, existingErr := successfulCandidatePublication(ctx, store, candidate.CandidateID); existingErr == nil {
		if existing.AcceptanceID != acceptance.AcceptanceID ||
			existing.TargetRef != candidate.TargetRef ||
			existing.TargetBefore != candidate.ExpectedTargetOID ||
			existing.TargetAfter != candidate.CommitOID {
			return CandidatePublication{}, fmt.Errorf("%w: successful publication does not match current Candidate acceptance", ErrCandidateBinding)
		}
		return existing, nil
	} else if !errors.Is(existingErr, ErrNotFound) {
		return CandidatePublication{}, existingErr
	}
	currentTarget, err := resolveGitCommit(ctx, canonical.Root, candidate.TargetRef)
	if err != nil {
		return CandidatePublication{}, err
	}
	if currentTarget != candidate.ExpectedTargetOID && currentTarget != candidate.CommitOID {
		return CandidatePublication{}, fmt.Errorf(
			"%w: target moved from %s to %s",
			ErrCandidateStale,
			candidate.ExpectedTargetOID,
			currentTarget,
		)
	}
	expectedIndexTree, _, err := requirePublishableProtectedWorktree(ctx, store.db, canonical, candidate)
	if err != nil {
		return CandidatePublication{}, err
	}
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
		acceptance.AcceptanceDigest, candidate.TargetRef, candidate.ExpectedTargetOID, candidate.CommitOID,
	})
	if err != nil {
		return CandidatePublication{}, err
	}
	publication, err = prepareOrLoadCandidatePublication(
		ctx,
		store,
		CandidatePublication{
			PublicationID: "publication-" + publicationDigest[:24], CandidateID: candidate.CandidateID,
			AcceptanceID: acceptance.AcceptanceID, TargetRef: candidate.TargetRef,
			TargetBefore: candidate.ExpectedTargetOID, TargetAfter: candidate.CommitOID,
			ExpectedIndexTreeOID: expectedIndexTree, Status: CandidatePublicationPrepared,
			PublicationDigest: publicationDigest,
		})
	if err != nil {
		return CandidatePublication{}, err
	}
	if publication.AcceptanceID != acceptance.AcceptanceID ||
		publication.TargetRef != candidate.TargetRef ||
		publication.TargetBefore != candidate.ExpectedTargetOID ||
		publication.TargetAfter != candidate.CommitOID ||
		publication.ExpectedIndexTreeOID != expectedIndexTree ||
		publication.PublicationDigest != publicationDigest {
		return CandidatePublication{}, fmt.Errorf("%w: existing publication journal does not match current Candidate acceptance", ErrCandidateBinding)
	}
	if publication.Status == CandidatePublicationSucceeded {
		return publication, nil
	}
	return executeCandidatePublication(ctx, store, canonical, candidate, publication)
}

func prepareOrLoadCandidatePublication(
	ctx context.Context,
	store *Store,
	prepared CandidatePublication,
) (CandidatePublication, error) {
	tx, err := store.db.BeginTx(ctx, nil)
	if err != nil {
		return CandidatePublication{}, fmt.Errorf("begin Candidate publication preparation: %w", err)
	}
	defer func() { _ = tx.Rollback() }()
	existing, err := scanCandidatePublication(tx.QueryRowContext(ctx, `
		SELECT publication_id, candidate_id, acceptance_id, target_ref, target_before,
		       target_after, expected_index_tree_oid, status, publication_digest,
		       created_at_ms, updated_at_ms
		FROM candidate_publications
		WHERE publication_id = ?
	`, prepared.PublicationID))
	if err == nil {
		if err := tx.Commit(); err != nil {
			return CandidatePublication{}, fmt.Errorf("commit Candidate publication replay: %w", err)
		}
		return existing, nil
	}
	if !errors.Is(err, sql.ErrNoRows) {
		return CandidatePublication{}, fmt.Errorf("load Candidate publication journal: %w", err)
	}
	existing, err = scanCandidatePublication(tx.QueryRowContext(ctx, `
		SELECT publication_id, candidate_id, acceptance_id, target_ref, target_before,
		       target_after, expected_index_tree_oid, status, publication_digest,
		       created_at_ms, updated_at_ms
		FROM candidate_publications
		WHERE candidate_id = ? AND status = 'succeeded'
		ORDER BY updated_at_ms DESC, publication_id DESC LIMIT 1
	`, prepared.CandidateID))
	if err == nil {
		if err := tx.Commit(); err != nil {
			return CandidatePublication{}, fmt.Errorf("commit Candidate publication replay: %w", err)
		}
		return existing, nil
	}
	if !errors.Is(err, sql.ErrNoRows) {
		return CandidatePublication{}, fmt.Errorf("load successful Candidate publication: %w", err)
	}
	nowMS := time.Now().UTC().UnixMilli()
	prepared.CreatedAtMS = nowMS
	prepared.UpdatedAtMS = nowMS
	if _, err := tx.ExecContext(ctx, `
		INSERT INTO candidate_publications (
			publication_id, candidate_id, acceptance_id, target_ref, target_before,
			target_after, expected_index_tree_oid, status, publication_digest, reason,
			created_at_ms, updated_at_ms
		) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, '', ?, ?)
	`, prepared.PublicationID, prepared.CandidateID, prepared.AcceptanceID,
		prepared.TargetRef, prepared.TargetBefore, prepared.TargetAfter,
		prepared.ExpectedIndexTreeOID, prepared.Status, prepared.PublicationDigest,
		prepared.CreatedAtMS, prepared.UpdatedAtMS); err != nil {
		return CandidatePublication{}, fmt.Errorf("prepare Candidate publication: %w", err)
	}
	if err := tx.Commit(); err != nil {
		return CandidatePublication{}, fmt.Errorf("commit Candidate publication preparation: %w", err)
	}
	return prepared, nil
}

func executeCandidatePublication(
	ctx context.Context,
	store *Store,
	repository Repository,
	candidate FrozenCandidate,
	publication CandidatePublication,
) (CandidatePublication, error) {
	tx, err := store.db.BeginTx(ctx, nil)
	if err != nil {
		return CandidatePublication{}, fmt.Errorf("begin Candidate publication execution: %w", err)
	}
	defer func() { _ = tx.Rollback() }()
	currentTarget, err := resolveGitCommit(ctx, repository.Root, candidate.TargetRef)
	if err != nil {
		return CandidatePublication{}, err
	}
	if currentTarget == candidate.CommitOID {
		return finishCandidatePublicationTx(ctx, tx, publication, CandidatePublicationSucceeded, "")
	}
	if currentTarget != candidate.ExpectedTargetOID {
		reason := fmt.Sprintf("target moved from %s to %s", candidate.ExpectedTargetOID, currentTarget)
		if _, finishErr := finishCandidatePublicationTx(ctx, tx, publication, CandidatePublicationStale, reason); finishErr != nil {
			return CandidatePublication{}, finishErr
		}
		return CandidatePublication{}, fmt.Errorf("%w: %s", ErrCandidateStale, reason)
	}
	if holderRunID, err := primaryWorkspaceHolderTx(ctx, tx); err != nil {
		return CandidatePublication{}, err
	} else if holderRunID != "" {
		return CandidatePublication{}, fmt.Errorf("%w: primary workspace is owned by Run %q", ErrResourceConflict, holderRunID)
	}
	currentIndexTree, _, err := requirePublishableProtectedWorktree(ctx, tx, repository, candidate)
	if err != nil {
		return CandidatePublication{}, err
	}
	if currentIndexTree != publication.ExpectedIndexTreeOID {
		return CandidatePublication{}, fmt.Errorf("%w: protected target index changed after publication preparation", ErrTargetWorktreeDirty)
	}
	publication.Status = CandidatePublicationExecuting
	publication.UpdatedAtMS = time.Now().UTC().UnixMilli()
	if _, err := tx.ExecContext(ctx, `
		UPDATE candidate_publications SET status = ?, reason = '', updated_at_ms = ?
		WHERE publication_id = ? AND status IN ('prepared', 'executing', 'outcome_unknown', 'stale')
	`, publication.Status, publication.UpdatedAtMS, publication.PublicationID); err != nil {
		return CandidatePublication{}, fmt.Errorf("mark Candidate publication executing: %w", err)
	}
	casErr := runGitMutationWithRetry(
		ctx, repository.Root, "update-ref", candidate.TargetRef, candidate.CommitOID, candidate.ExpectedTargetOID,
	)
	if casErr == nil {
		return finishCandidatePublicationTx(ctx, tx, publication, CandidatePublicationSucceeded, "")
	}
	observedTarget, observeErr := resolveGitCommit(ctx, repository.Root, candidate.TargetRef)
	if observeErr != nil {
		return CandidatePublication{}, errors.Join(fmt.Errorf("publish target CAS: %w", casErr), observeErr)
	}
	if observedTarget == candidate.CommitOID {
		return finishCandidatePublicationTx(ctx, tx, publication, CandidatePublicationSucceeded, "")
	}
	if observedTarget != candidate.ExpectedTargetOID {
		reason := fmt.Sprintf("target moved from %s to %s during publish", candidate.ExpectedTargetOID, observedTarget)
		if _, finishErr := finishCandidatePublicationTx(ctx, tx, publication, CandidatePublicationStale, reason); finishErr != nil {
			return CandidatePublication{}, finishErr
		}
		return CandidatePublication{}, fmt.Errorf("%w: %s", ErrCandidateStale, reason)
	}
	reason := "target CAS returned without a provable ref update: " + casErr.Error()
	if _, finishErr := finishCandidatePublicationTx(ctx, tx, publication, CandidatePublicationUnknown, reason); finishErr != nil {
		return CandidatePublication{}, finishErr
	}
	return CandidatePublication{}, fmt.Errorf("%w: %s", ErrPublicationUnknown, reason)
}

func finishCandidatePublicationTx(
	ctx context.Context,
	tx *sql.Tx,
	publication CandidatePublication,
	status CandidatePublicationStatus,
	reason string,
) (CandidatePublication, error) {
	publication.Status = status
	publication.UpdatedAtMS = time.Now().UTC().UnixMilli()
	if _, err := tx.ExecContext(ctx, `
		UPDATE candidate_publications SET status = ?, reason = ?, updated_at_ms = ?
		WHERE publication_id = ?
	`, publication.Status, reason, publication.UpdatedAtMS, publication.PublicationID); err != nil {
		return CandidatePublication{}, fmt.Errorf("record Candidate publication outcome: %w", err)
	}
	if err := tx.Commit(); err != nil {
		return CandidatePublication{}, fmt.Errorf("commit Candidate publication outcome: %w", err)
	}
	return publication, nil
}

func primaryWorkspaceHolderTx(ctx context.Context, tx *sql.Tx) (string, error) {
	var runID string
	err := tx.QueryRowContext(ctx, `SELECT run_id FROM primary_workspace_slots WHERE slot_id = 1`).Scan(&runID)
	if errors.Is(err, sql.ErrNoRows) {
		return "", nil
	}
	if err != nil {
		return "", fmt.Errorf("read primary workspace owner: %w", err)
	}
	return runID, nil
}

func scanCandidatePublication(scanner interface{ Scan(...any) error }) (CandidatePublication, error) {
	var publication CandidatePublication
	err := scanner.Scan(
		&publication.PublicationID, &publication.CandidateID, &publication.AcceptanceID,
		&publication.TargetRef, &publication.TargetBefore, &publication.TargetAfter,
		&publication.ExpectedIndexTreeOID, &publication.Status, &publication.PublicationDigest,
		&publication.CreatedAtMS, &publication.UpdatedAtMS,
	)
	return publication, err
}

func SyncPublishedCandidate(
	ctx context.Context,
	repository Repository,
	params SyncPublishedCandidateParams,
) (syncReceipt CandidateSync, returnErr error) {
	if strings.TrimSpace(params.CandidateID) == "" || strings.TrimSpace(params.PublicationDigest) == "" {
		return CandidateSync{}, fmt.Errorf("%w: Candidate id and publication digest are required", ErrInvalidArgument)
	}
	canonical, err := canonicalAllocationRepository(ctx, repository)
	if err != nil {
		return CandidateSync{}, err
	}
	store, err := Open(ctx, canonical.DatabasePath)
	if err != nil {
		return CandidateSync{}, err
	}
	defer func() {
		if closeErr := store.Close(); closeErr != nil {
			returnErr = errors.Join(returnErr, closeErr)
		}
	}()
	candidate, err := store.GetFrozenCandidate(ctx, params.CandidateID)
	if err != nil {
		return CandidateSync{}, err
	}
	if targetRef := strings.TrimSpace(params.TargetRef); targetRef != "" && targetRef != candidate.TargetRef {
		return CandidateSync{}, fmt.Errorf("%w: requested target %q does not match Candidate target %q", ErrSyncUnsafe, targetRef, candidate.TargetRef)
	}
	publication, err := successfulCandidatePublication(ctx, store, candidate.CandidateID)
	if err != nil || publication.PublicationDigest != params.PublicationDigest {
		return CandidateSync{}, fmt.Errorf("%w: publication receipt is missing or stale", ErrSyncUnsafe)
	}
	tx, err := store.db.BeginTx(ctx, nil)
	if err != nil {
		return CandidateSync{}, fmt.Errorf("begin guarded Candidate sync: %w", err)
	}
	defer func() { _ = tx.Rollback() }()
	if holderRunID, err := primaryWorkspaceHolderTx(ctx, tx); err != nil {
		return CandidateSync{}, err
	} else if holderRunID != "" {
		return CandidateSync{}, fmt.Errorf("%w: primary workspace is owned by Run %q", ErrSyncUnsafe, holderRunID)
	}
	branch, err := runGitOutput(ctx, canonical.PrimaryRoot, "symbolic-ref", "--quiet", "HEAD")
	if err != nil || strings.TrimSpace(branch) != candidate.TargetRef {
		return CandidateSync{}, fmt.Errorf("%w: primary worktree does not check out %q", ErrSyncUnsafe, candidate.TargetRef)
	}
	current, err := resolveGitCommit(ctx, canonical.Root, candidate.TargetRef)
	if err != nil || current != candidate.CommitOID {
		return CandidateSync{}, fmt.Errorf("%w: published target no longer names Candidate", ErrSyncUnsafe)
	}
	indexTree, err := runGitOutput(ctx, canonical.PrimaryRoot, "write-tree")
	if err != nil {
		return CandidateSync{}, fmt.Errorf("%w: primary index changed after publication", ErrSyncUnsafe)
	}
	indexTree = strings.TrimSpace(indexTree)
	if indexTree != publication.ExpectedIndexTreeOID && indexTree != candidate.TreeOID {
		return CandidateSync{}, fmt.Errorf("%w: primary index changed after publication", ErrSyncUnsafe)
	}
	worktreeTree, err := captureProtectedWorktreeTree(ctx, canonical, candidate.ExpectedTargetOID)
	if err != nil {
		return CandidateSync{}, err
	}
	allowedTrees, err := candidateProtectedWorktreeTrees(ctx, tx, canonical, candidate)
	if err != nil {
		return CandidateSync{}, err
	}
	allowedTrees[candidate.TreeOID] = struct{}{}
	if _, allowed := allowedTrees[worktreeTree]; !allowed {
		return CandidateSync{}, fmt.Errorf("%w: primary worktree changed after publication", ErrSyncUnsafe)
	}
	if indexTree != candidate.TreeOID || worktreeTree != candidate.TreeOID {
		if err := runGitMutationWithRetry(ctx, canonical.PrimaryRoot, "reset", "--hard", candidate.CommitOID); err != nil {
			return CandidateSync{}, fmt.Errorf("safe-sync accepted Candidate: %w", err)
		}
	}
	nowMS := time.Now().UTC().UnixMilli()
	digest, err := digestCanonicalJSON([]string{
		candidate.CandidateID, publication.PublicationDigest, canonical.PrimaryRoot, candidate.CommitOID,
	})
	if err != nil {
		return CandidateSync{}, err
	}
	syncReceipt = CandidateSync{
		SyncID: "sync-" + digest[:24], CandidateID: candidate.CandidateID,
		PublicationID: publication.PublicationID, WorktreeRoot: canonical.PrimaryRoot,
		Status: "succeeded", SyncDigest: digest, CreatedAtMS: nowMS,
	}
	if _, err := tx.ExecContext(ctx, `
		INSERT INTO candidate_syncs (
			sync_id, candidate_id, publication_id, worktree_root, status, sync_digest, created_at_ms
		) VALUES (?, ?, ?, ?, ?, ?, ?)
		ON CONFLICT(publication_id, worktree_root) DO NOTHING
	`, syncReceipt.SyncID, syncReceipt.CandidateID, syncReceipt.PublicationID,
		syncReceipt.WorktreeRoot, syncReceipt.Status, syncReceipt.SyncDigest,
		syncReceipt.CreatedAtMS); err != nil {
		return CandidateSync{}, fmt.Errorf("record Candidate sync: %w", err)
	}
	if err := tx.Commit(); err != nil {
		return CandidateSync{}, fmt.Errorf("commit Candidate sync: %w", err)
	}
	return syncReceipt, nil
}

var errReviewCommandFailed = errors.New("Candidate Review command failed")

func runCandidateReviewCommand(ctx context.Context, directory string, argv []string) (int, string, string, error) {
	if len(argv) == 0 || strings.TrimSpace(argv[0]) == "" {
		return -1, "", "", fmt.Errorf("%w: Review command argv is empty", ErrInvalidArgument)
	}
	command := exec.CommandContext(ctx, argv[0], argv[1:]...)
	command.Dir = directory
	var stdout, stderr bytes.Buffer
	command.Stdout = &stdout
	command.Stderr = &stderr
	processes := newProcessTree()
	if err := processes.configure(command); err != nil {
		return -1, "", "", err
	}
	if err := processes.start(command); err != nil {
		return -1, "", "", err
	}
	waitErr := command.Wait()
	_ = processes.close()
	exitCode := managedProcessExitCode(command, waitErr)
	stdoutDigest := sha256String(stdout.String())
	stderrDigest := sha256String(stderr.String())
	if waitErr != nil {
		if ctx.Err() != nil {
			_ = processes.terminate()
			return exitCode, stdoutDigest, stderrDigest, ctx.Err()
		}
		var exitError *exec.ExitError
		if errors.As(waitErr, &exitError) {
			return exitCode, stdoutDigest, stderrDigest, errReviewCommandFailed
		}
		return exitCode, stdoutDigest, stderrDigest, waitErr
	}
	return exitCode, stdoutDigest, stderrDigest, nil
}

func verifyFrozenCandidateGitBinding(ctx context.Context, repository Repository, candidate FrozenCandidate) error {
	commit, exists, err := resolveOptionalGitCommit(ctx, repository.Root, candidate.HiddenRef)
	if err != nil || !exists || commit != candidate.CommitOID {
		return fmt.Errorf("%w: Candidate hidden ref changed", ErrCandidateBinding)
	}
	tree, err := runGitOutput(ctx, repository.Root, "rev-parse", candidate.CommitOID+"^{tree}")
	if err != nil || strings.TrimSpace(tree) != candidate.TreeOID {
		return fmt.Errorf("%w: Candidate tree changed", ErrCandidateBinding)
	}
	return nil
}

func latestCandidateReview(ctx context.Context, store *Store, candidateID string) (CandidateReview, error) {
	var review CandidateReview
	err := store.db.QueryRowContext(ctx, `
		SELECT review_id, candidate_id, candidate_manifest_sha256, candidate_tree_oid,
		       candidate_commit_oid, reviewer, status, evidence_digest, review_digest, created_at_ms
		FROM candidate_reviews WHERE candidate_id = ?
		ORDER BY created_at_ms DESC, review_id DESC LIMIT 1
	`, candidateID).Scan(
		&review.ReviewID, &review.CandidateID, &review.CandidateManifestSHA256,
		&review.CandidateTreeOID, &review.CandidateCommitOID, &review.Reviewer,
		&review.Status, &review.EvidenceDigest, &review.ReviewDigest, &review.CreatedAtMS,
	)
	if errors.Is(err, sql.ErrNoRows) {
		return CandidateReview{}, fmt.Errorf("%w: Candidate Review", ErrNotFound)
	}
	return review, err
}

func latestCandidateAcceptance(ctx context.Context, store *Store, candidateID string) (CandidateAcceptance, error) {
	var acceptance CandidateAcceptance
	err := store.db.QueryRowContext(ctx, `
		SELECT acceptance_id, candidate_id, review_id, review_digest, evidence_digest,
		       decision, actor, acceptance_digest, created_at_ms
		FROM candidate_acceptances WHERE candidate_id = ?
		ORDER BY created_at_ms DESC, acceptance_id DESC LIMIT 1
	`, candidateID).Scan(
		&acceptance.AcceptanceID, &acceptance.CandidateID, &acceptance.ReviewID,
		&acceptance.ReviewDigest, &acceptance.EvidenceDigest, &acceptance.Decision,
		&acceptance.Actor, &acceptance.AcceptanceDigest, &acceptance.CreatedAtMS,
	)
	if errors.Is(err, sql.ErrNoRows) {
		return CandidateAcceptance{}, fmt.Errorf("%w: Candidate acceptance", ErrNotFound)
	}
	return acceptance, err
}

func successfulCandidatePublication(ctx context.Context, store *Store, candidateID string) (CandidatePublication, error) {
	var publication CandidatePublication
	err := store.db.QueryRowContext(ctx, `
		SELECT publication_id, candidate_id, acceptance_id, target_ref, target_before,
		       target_after, expected_index_tree_oid, status, publication_digest,
		       created_at_ms, updated_at_ms
		FROM candidate_publications WHERE candidate_id = ? AND status = ?
	`, candidateID, CandidatePublicationSucceeded).Scan(
		&publication.PublicationID, &publication.CandidateID, &publication.AcceptanceID,
		&publication.TargetRef, &publication.TargetBefore, &publication.TargetAfter,
		&publication.ExpectedIndexTreeOID, &publication.Status, &publication.PublicationDigest,
		&publication.CreatedAtMS, &publication.UpdatedAtMS,
	)
	if errors.Is(err, sql.ErrNoRows) {
		return CandidatePublication{}, fmt.Errorf("%w: Candidate publication", ErrNotFound)
	}
	return publication, err
}

func requirePublishableProtectedWorktree(
	ctx context.Context,
	querier candidateDeliveryQuerier,
	repository Repository,
	candidate FrozenCandidate,
) (string, string, error) {
	baseTree, err := runGitOutput(ctx, repository.Root, "rev-parse", candidate.ExpectedTargetOID+"^{tree}")
	if err != nil {
		return "", "", err
	}
	baseTree = strings.TrimSpace(baseTree)
	branch, err := runGitOutput(ctx, repository.PrimaryRoot, "symbolic-ref", "--quiet", "HEAD")
	if err != nil || strings.TrimSpace(branch) != candidate.TargetRef {
		return baseTree, baseTree, nil
	}
	indexTree, err := runGitOutput(ctx, repository.PrimaryRoot, "write-tree")
	if err != nil {
		return "", "", fmt.Errorf("inspect protected target index: %w", err)
	}
	indexTree = strings.TrimSpace(indexTree)
	worktreeTree, err := captureProtectedWorktreeTree(ctx, repository, candidate.ExpectedTargetOID)
	if err != nil {
		return "", "", err
	}
	allowedTrees, err := candidateProtectedWorktreeTrees(ctx, querier, repository, candidate)
	if err != nil {
		return "", "", err
	}
	if _, allowed := allowedTrees[indexTree]; !allowed {
		return "", "", fmt.Errorf("%w: protected target index is not sealed in the Candidate", ErrTargetWorktreeDirty)
	}
	if _, allowed := allowedTrees[worktreeTree]; !allowed {
		return "", "", fmt.Errorf("%w: protected target worktree has unsealed local changes", ErrTargetWorktreeDirty)
	}
	return indexTree, worktreeTree, nil
}

type candidateDeliveryQuerier interface {
	QueryContext(context.Context, string, ...any) (*sql.Rows, error)
}

func candidateProtectedWorktreeTrees(
	ctx context.Context,
	querier candidateDeliveryQuerier,
	repository Repository,
	candidate FrozenCandidate,
) (map[string]struct{}, error) {
	baseTree, err := runGitOutput(ctx, repository.Root, "rev-parse", candidate.ExpectedTargetOID+"^{tree}")
	if err != nil {
		return nil, err
	}
	allowed := map[string]struct{}{strings.TrimSpace(baseTree): {}}
	rows, err := querier.QueryContext(ctx, `
		SELECT rr.result_id, rr.base_commit_oid, rr.result_tree_oid
		FROM frozen_candidate_members AS member
		JOIN run_results AS rr ON rr.result_id = member.result_id
		JOIN workspace_routes AS route ON route.workspace_id = rr.workspace_id
		WHERE member.candidate_id = ? AND route.mode = 'primary'
		ORDER BY member.ordinal
	`, candidate.CandidateID)
	if err != nil {
		return nil, fmt.Errorf("read Candidate primary Result state: %w", err)
	}
	defer rows.Close()
	primaryCount := 0
	for rows.Next() {
		var resultID, baseCommit, resultTree string
		if err := rows.Scan(&resultID, &baseCommit, &resultTree); err != nil {
			return nil, err
		}
		primaryCount++
		if primaryCount > 1 || baseCommit != candidate.ExpectedTargetOID || !validGitObjectID(resultTree) {
			return nil, fmt.Errorf("%w: Candidate primary Result bindings are ambiguous", ErrCandidateBinding)
		}
		allowed[resultTree] = struct{}{}
	}
	if err := rows.Err(); err != nil {
		return nil, err
	}
	return allowed, nil
}

func captureProtectedWorktreeTree(ctx context.Context, repository Repository, baseCommit string) (string, error) {
	indexRoot := filepath.Join(repository.CommonDir, "specify-runtime", "result-indexes")
	if err := safeMkdirAllWithin(repository.CommonDir, indexRoot); err != nil {
		return "", err
	}
	indexFile, err := os.CreateTemp(indexRoot, "protected-index-*.tmp")
	if err != nil {
		return "", fmt.Errorf("allocate protected worktree index: %w", err)
	}
	indexPath := indexFile.Name()
	if err := indexFile.Close(); err != nil {
		return "", err
	}
	if err := os.Remove(indexPath); err != nil {
		return "", err
	}
	defer func() { _ = os.Remove(indexPath) }()
	gitEnv := map[string]string{"GIT_INDEX_FILE": indexPath}
	if _, err := runGitWithEnvironment(ctx, repository.PrimaryRoot, gitEnv, "read-tree", baseCommit); err != nil {
		return "", fmt.Errorf("seed protected worktree index: %w", err)
	}
	if _, err := runGitWithEnvironment(ctx, repository.PrimaryRoot, gitEnv, "add", "-A", "--", "."); err != nil {
		return "", fmt.Errorf("capture protected worktree tree: %w", err)
	}
	tree, err := runGitWithEnvironment(ctx, repository.PrimaryRoot, gitEnv, "write-tree")
	if err != nil {
		return "", fmt.Errorf("write protected worktree tree: %w", err)
	}
	tree = strings.TrimSpace(tree)
	if !validGitObjectID(tree) {
		return "", fmt.Errorf("%w: protected worktree produced invalid tree %q", ErrCandidateBinding, tree)
	}
	return tree, nil
}

func canonicalJSON(value any) (string, error) {
	encoded, err := jsonMarshal(value)
	if err != nil {
		return "", fmt.Errorf("encode canonical JSON: %w", err)
	}
	return string(encoded), nil
}

func sha256String(value string) string {
	digest, _ := digestCanonicalJSON(value)
	return digest
}

var jsonMarshal = func(value any) ([]byte, error) {
	return json.Marshal(value)
}

func sortedReviewDigests(values []string) []string {
	result := append([]string(nil), values...)
	sort.Strings(result)
	return result
}
