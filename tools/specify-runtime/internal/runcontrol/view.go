package runcontrol

import (
	"context"
	"database/sql"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"sync"
)

// View provides a read-only handle over an existing run-control database.
// It never initializes schema, registers supervisor state, or writes shutdown
// metadata, so status/list commands can inspect existing state without
// materializing a control database.
type View struct {
	db        *sql.DB
	closeOnce sync.Once
	closeErr  error
}

func OpenView(ctx context.Context, databasePath string) (*View, error) {
	if strings.TrimSpace(databasePath) == "" {
		return nil, fmt.Errorf("%w: database path is required", ErrInvalidArgument)
	}
	absolutePath, err := filepath.Abs(databasePath)
	if err != nil {
		return nil, fmt.Errorf("resolve run control database path: %w", err)
	}
	absolutePath = filepath.Clean(absolutePath)
	if info, err := os.Stat(absolutePath); err != nil {
		if errors.Is(err, os.ErrNotExist) {
			return nil, fmt.Errorf("%w: run control database %q", ErrNotFound, absolutePath)
		}
		return nil, fmt.Errorf("inspect run control database: %w", err)
	} else if info.IsDir() {
		return nil, fmt.Errorf("%w: run control database %q is a directory", ErrInvalidArgument, absolutePath)
	}

	db, err := sql.Open("sqlite", absolutePath+"?mode=ro")
	if err != nil {
		return nil, fmt.Errorf("open run control database view: %w", err)
	}
	db.SetMaxOpenConns(1)
	db.SetMaxIdleConns(1)

	view := &View{db: db}
	if err := view.initialize(ctx); err != nil {
		_ = db.Close()
		return nil, err
	}
	return view, nil
}

func (view *View) initialize(ctx context.Context) error {
	if _, err := view.db.ExecContext(ctx, `PRAGMA query_only = ON`); err != nil {
		return fmt.Errorf("enable sqlite query_only mode: %w", err)
	}
	if _, err := view.db.ExecContext(ctx, fmt.Sprintf(`PRAGMA busy_timeout = %d`, sqliteBusyTimeoutMS)); err != nil {
		return fmt.Errorf("configure sqlite busy timeout: %w", err)
	}
	version, exists, err := existingSchemaVersion(ctx, view.db)
	if err != nil {
		return err
	}
	if !exists {
		return fmt.Errorf("%w: database has no run control metadata", ErrUnsupportedSchema)
	}
	if version != schemaVersion {
		return fmt.Errorf("%w: database has version %d, runtime requires %d", ErrUnsupportedSchema, version, schemaVersion)
	}
	return nil
}

func (view *View) Close() error {
	if view == nil || view.db == nil {
		return nil
	}
	view.closeOnce.Do(func() {
		if err := view.db.Close(); err != nil {
			view.closeErr = fmt.Errorf("close run control database view: %w", err)
		}
	})
	return view.closeErr
}

func (view *View) GetRun(ctx context.Context, runID string) (Run, error) {
	if strings.TrimSpace(runID) == "" {
		return Run{}, fmt.Errorf("%w: run id is required", ErrInvalidArgument)
	}
	return readRunTx(ctx, view.db, runID)
}

func (view *View) ListRunEvents(ctx context.Context, runID string) ([]Event, error) {
	if strings.TrimSpace(runID) == "" {
		return nil, fmt.Errorf("%w: run id is required", ErrInvalidArgument)
	}
	rows, err := view.db.QueryContext(ctx, `
		SELECT event_id, aggregate_type, aggregate_id, aggregate_revision,
		       event_type, reason, payload_json, created_at_ms
		FROM events
		WHERE aggregate_type = 'run' AND aggregate_id = ?
		ORDER BY aggregate_revision, event_id
	`, runID)
	if err != nil {
		return nil, fmt.Errorf("list run events: %w", err)
	}
	defer rows.Close()
	events := make([]Event, 0)
	for rows.Next() {
		var event Event
		if err := rows.Scan(
			&event.EventID,
			&event.AggregateType,
			&event.AggregateID,
			&event.AggregateRevision,
			&event.EventType,
			&event.Reason,
			&event.PayloadJSON,
			&event.CreatedAtMS,
		); err != nil {
			return nil, fmt.Errorf("scan run event: %w", err)
		}
		events = append(events, event)
	}
	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("iterate run events: %w", err)
	}
	return events, nil
}

func (view *View) ListRunResults(ctx context.Context, runID string) ([]RunResult, error) {
	if strings.TrimSpace(runID) == "" {
		return nil, fmt.Errorf("%w: run id is required", ErrInvalidArgument)
	}
	rows, err := view.db.QueryContext(ctx, runResultSelectSQL+`
		WHERE run_id = ? ORDER BY result_revision, created_at_ms, result_id
	`, runID)
	if err != nil {
		return nil, fmt.Errorf("list Run Results for %q: %w", runID, err)
	}
	defer rows.Close()
	results := make([]RunResult, 0)
	for rows.Next() {
		result, err := scanRunResult(rows)
		if err != nil {
			return nil, err
		}
		results = append(results, result)
	}
	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("iterate Run Results for %q: %w", runID, err)
	}
	return results, nil
}

func (view *View) GetRunResult(ctx context.Context, resultID string) (RunResult, error) {
	if strings.TrimSpace(resultID) == "" {
		return RunResult{}, fmt.Errorf("%w: result id is required", ErrInvalidArgument)
	}
	return readRunResultTx(ctx, view.db, resultID)
}

func (view *View) ListRunResultPaths(ctx context.Context, resultID string) ([]string, error) {
	if strings.TrimSpace(resultID) == "" {
		return nil, fmt.Errorf("%w: result id is required", ErrInvalidArgument)
	}
	if _, err := readRunResultTx(ctx, view.db, resultID); err != nil {
		return nil, err
	}
	return listRunResultPaths(ctx, view.db, resultID)
}

func (view *View) GetResultSupersession(ctx context.Context, oldResultID string) (ResultSupersession, error) {
	if strings.TrimSpace(oldResultID) == "" {
		return ResultSupersession{}, fmt.Errorf("%w: old Result id is required", ErrInvalidArgument)
	}
	var edge ResultSupersession
	err := view.db.QueryRowContext(ctx, `
		SELECT old_result_id, new_result_id, run_id, reason, created_at_ms
		FROM result_supersessions WHERE old_result_id = ?
	`, oldResultID).Scan(&edge.OldResultID, &edge.NewResultID, &edge.RunID, &edge.Reason, &edge.CreatedAtMS)
	if errors.Is(err, sql.ErrNoRows) {
		return ResultSupersession{}, fmt.Errorf("%w: Result supersession for %q", ErrNotFound, oldResultID)
	}
	if err != nil {
		return ResultSupersession{}, fmt.Errorf("read Result supersession: %w", err)
	}
	return edge, nil
}

func (view *View) ListResultDependencies(ctx context.Context, resultID string) ([]ResultDependency, error) {
	if strings.TrimSpace(resultID) == "" {
		return nil, fmt.Errorf("%w: result id is required", ErrInvalidArgument)
	}
	if _, err := readRunResultTx(ctx, view.db, resultID); err != nil {
		return nil, err
	}
	rows, err := view.db.QueryContext(ctx, `
		SELECT dependency_id, result_id, depends_on_result_id, kind, reason, created_at_ms
		FROM result_dependencies WHERE result_id = ?
		ORDER BY kind, depends_on_result_id, dependency_id
	`, resultID)
	if err != nil {
		return nil, fmt.Errorf("list Result dependencies: %w", err)
	}
	defer rows.Close()
	edges := make([]ResultDependency, 0)
	for rows.Next() {
		var edge ResultDependency
		if err := rows.Scan(
			&edge.DependencyID, &edge.ResultID, &edge.DependsOnResultID,
			&edge.Kind, &edge.Reason, &edge.CreatedAtMS,
		); err != nil {
			return nil, err
		}
		edges = append(edges, edge)
	}
	return edges, rows.Err()
}

func (view *View) GetFrozenCandidate(ctx context.Context, candidateID string) (FrozenCandidate, error) {
	if strings.TrimSpace(candidateID) == "" {
		return FrozenCandidate{}, fmt.Errorf("%w: Candidate id is required", ErrInvalidArgument)
	}
	var candidate FrozenCandidate
	err := view.db.QueryRowContext(ctx, `
		SELECT candidate_id, build_id, target_ref, expected_target_oid, tree_oid,
		       commit_oid, hidden_ref, manifest_sha256, status, created_at_ms
		FROM frozen_candidates WHERE candidate_id = ?
	`, candidateID).Scan(
		&candidate.CandidateID, &candidate.BuildID, &candidate.TargetRef,
		&candidate.ExpectedTargetOID, &candidate.TreeOID, &candidate.CommitOID,
		&candidate.HiddenRef, &candidate.ManifestSHA256, &candidate.Status, &candidate.CreatedAtMS,
	)
	if errors.Is(err, sql.ErrNoRows) {
		return FrozenCandidate{}, fmt.Errorf("%w: frozen Candidate %q", ErrCandidateNotFound, candidateID)
	}
	if err != nil {
		return FrozenCandidate{}, fmt.Errorf("read frozen Candidate: %w", err)
	}
	rows, err := view.db.QueryContext(ctx, `
		SELECT result_id FROM frozen_candidate_members WHERE candidate_id = ? ORDER BY ordinal
	`, candidateID)
	if err != nil {
		return FrozenCandidate{}, err
	}
	defer rows.Close()
	for rows.Next() {
		var resultID string
		if err := rows.Scan(&resultID); err != nil {
			return FrozenCandidate{}, err
		}
		candidate.MemberResultIDs = append(candidate.MemberResultIDs, resultID)
	}
	return candidate, rows.Err()
}

func (view *View) GetLatestCandidateReview(ctx context.Context, candidateID string) (CandidateReview, error) {
	var review CandidateReview
	err := view.db.QueryRowContext(ctx, `
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

func (view *View) GetLatestCandidateAcceptance(ctx context.Context, candidateID string) (CandidateAcceptance, error) {
	var acceptance CandidateAcceptance
	err := view.db.QueryRowContext(ctx, `
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

func (view *View) GetLatestCandidatePublication(ctx context.Context, candidateID string) (CandidatePublication, error) {
	var publication CandidatePublication
	err := view.db.QueryRowContext(ctx, `
		SELECT publication_id, candidate_id, acceptance_id, target_ref, target_before,
		       target_after, expected_index_tree_oid, status, publication_digest,
		       created_at_ms, updated_at_ms
		FROM candidate_publications WHERE candidate_id = ?
		ORDER BY created_at_ms DESC, publication_id DESC LIMIT 1
	`, candidateID).Scan(
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

func (view *View) GetLatestCandidateSync(ctx context.Context, candidateID string) (CandidateSync, error) {
	var syncReceipt CandidateSync
	err := view.db.QueryRowContext(ctx, `
		SELECT sync_id, candidate_id, publication_id, worktree_root, status, sync_digest, created_at_ms
		FROM candidate_syncs WHERE candidate_id = ?
		ORDER BY created_at_ms DESC, sync_id DESC LIMIT 1
	`, candidateID).Scan(
		&syncReceipt.SyncID, &syncReceipt.CandidateID, &syncReceipt.PublicationID,
		&syncReceipt.WorktreeRoot, &syncReceipt.Status, &syncReceipt.SyncDigest,
		&syncReceipt.CreatedAtMS,
	)
	if errors.Is(err, sql.ErrNoRows) {
		return CandidateSync{}, fmt.Errorf("%w: Candidate sync", ErrNotFound)
	}
	return syncReceipt, err
}
