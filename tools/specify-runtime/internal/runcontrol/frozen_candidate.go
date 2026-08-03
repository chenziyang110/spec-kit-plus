package runcontrol

import (
	"context"
	"database/sql"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"time"
)

var (
	ErrResultDependencyCycle  = errors.New("Result dependency graph contains a cycle")
	ErrResultConflict         = errors.New("Result set contains an explicit conflict")
	ErrCandidateStale         = errors.New("Candidate target changed during build")
	ErrCandidateBuildConflict = errors.New("Candidate build has a Git conflict")
)

type ResultDependencyKind string

const (
	ResultDependencyRequires      ResultDependencyKind = "requires"
	ResultDependencyAfter         ResultDependencyKind = "after"
	ResultDependencyConflictsWith ResultDependencyKind = "conflicts_with"
)

type ResultDependency struct {
	DependencyID      string
	ResultID          string
	DependsOnResultID string
	Kind              ResultDependencyKind
	Reason            string
	CreatedAtMS       int64
}

type AddResultDependencyParams struct {
	ResultID          string
	DependsOnResultID string
	Kind              ResultDependencyKind
	Reason            string
}

type CandidateBuildStatus string

const (
	CandidateBuildPrepared   CandidateBuildStatus = "prepared"
	CandidateBuildExecuting  CandidateBuildStatus = "executing"
	CandidateBuildSucceeded  CandidateBuildStatus = "succeeded"
	CandidateBuildConflicted CandidateBuildStatus = "conflicted"
	CandidateBuildStale      CandidateBuildStatus = "stale"
	CandidateBuildFailed     CandidateBuildStatus = "failed"
)

type FrozenCandidate struct {
	CandidateID       string
	BuildID           string
	TargetRef         string
	ExpectedTargetOID string
	TreeOID           string
	CommitOID         string
	HiddenRef         string
	ManifestSHA256    string
	MemberResultIDs   []string
	Status            CandidateBuildStatus
	CreatedAtMS       int64
}

type BuildFrozenCandidateParams struct {
	TargetRef string
	ResultIDs []string
}

const frozenCandidateSchemaSQL = `
CREATE TABLE IF NOT EXISTS result_dependencies (
    dependency_id TEXT PRIMARY KEY,
    result_id TEXT NOT NULL REFERENCES run_results(result_id) ON DELETE RESTRICT,
    depends_on_result_id TEXT NOT NULL REFERENCES run_results(result_id) ON DELETE RESTRICT,
    kind TEXT NOT NULL CHECK (kind IN ('requires', 'after', 'conflicts_with')),
    reason TEXT NOT NULL,
    created_at_ms INTEGER NOT NULL,
    UNIQUE (result_id, depends_on_result_id, kind),
    CHECK (result_id <> depends_on_result_id)
);

CREATE INDEX IF NOT EXISTS result_dependencies_result
    ON result_dependencies(result_id, kind, depends_on_result_id);

CREATE TABLE IF NOT EXISTS candidate_builds (
    build_id TEXT PRIMARY KEY,
    target_ref TEXT NOT NULL,
    expected_target_oid TEXT NOT NULL,
    requested_results_sha256 TEXT NOT NULL CHECK (
        length(requested_results_sha256) = 64 AND requested_results_sha256 NOT GLOB '*[^0-9a-f]*'
    ),
    workspace_root TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('prepared', 'executing', 'succeeded', 'conflicted', 'stale', 'failed')),
    reason TEXT NOT NULL DEFAULT '',
    created_at_ms INTEGER NOT NULL,
    updated_at_ms INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS frozen_candidates (
    candidate_id TEXT PRIMARY KEY,
    build_id TEXT NOT NULL UNIQUE REFERENCES candidate_builds(build_id) ON DELETE RESTRICT,
    target_ref TEXT NOT NULL,
    expected_target_oid TEXT NOT NULL,
    tree_oid TEXT NOT NULL,
    commit_oid TEXT NOT NULL,
    hidden_ref TEXT NOT NULL UNIQUE,
    manifest_sha256 TEXT NOT NULL CHECK (
        length(manifest_sha256) = 64 AND manifest_sha256 NOT GLOB '*[^0-9a-f]*'
    ),
    status TEXT NOT NULL CHECK (status IN ('succeeded', 'stale')),
    created_at_ms INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS frozen_candidate_members (
    candidate_id TEXT NOT NULL REFERENCES frozen_candidates(candidate_id) ON DELETE RESTRICT,
    ordinal INTEGER NOT NULL CHECK (ordinal > 0),
    result_id TEXT NOT NULL REFERENCES run_results(result_id) ON DELETE RESTRICT,
    result_manifest_sha256 TEXT NOT NULL,
    PRIMARY KEY (candidate_id, ordinal),
    UNIQUE (candidate_id, result_id)
);
`

func (store *Store) AddResultDependency(ctx context.Context, params AddResultDependencyParams) (ResultDependency, error) {
	if strings.TrimSpace(params.ResultID) == "" || strings.TrimSpace(params.DependsOnResultID) == "" ||
		strings.TrimSpace(params.Reason) == "" || params.ResultID == params.DependsOnResultID {
		return ResultDependency{}, fmt.Errorf("%w: distinct Result ids and reason are required", ErrInvalidArgument)
	}
	switch params.Kind {
	case ResultDependencyRequires, ResultDependencyAfter, ResultDependencyConflictsWith:
	default:
		return ResultDependency{}, fmt.Errorf("%w: unsupported dependency kind %q", ErrInvalidArgument, params.Kind)
	}
	if _, err := store.GetRunResult(ctx, params.ResultID); err != nil {
		return ResultDependency{}, err
	}
	if _, err := store.GetRunResult(ctx, params.DependsOnResultID); err != nil {
		return ResultDependency{}, err
	}
	digest, err := digestCanonicalJSON([]string{params.ResultID, params.DependsOnResultID, string(params.Kind)})
	if err != nil {
		return ResultDependency{}, err
	}
	edge := ResultDependency{
		DependencyID: "dependency-" + digest[:20], ResultID: params.ResultID,
		DependsOnResultID: params.DependsOnResultID, Kind: params.Kind,
		Reason: params.Reason, CreatedAtMS: time.Now().UTC().UnixMilli(),
	}
	_, err = store.db.ExecContext(ctx, `
		INSERT INTO result_dependencies (
			dependency_id, result_id, depends_on_result_id, kind, reason, created_at_ms
		) VALUES (?, ?, ?, ?, ?, ?)
	`, edge.DependencyID, edge.ResultID, edge.DependsOnResultID, edge.Kind, edge.Reason, edge.CreatedAtMS)
	if err != nil {
		if isUniqueConstraintError(err) {
			return store.readResultDependency(ctx, edge.ResultID, edge.DependsOnResultID, edge.Kind)
		}
		return ResultDependency{}, fmt.Errorf("insert Result dependency: %w", err)
	}
	return edge, nil
}

func (store *Store) readResultDependency(ctx context.Context, resultID, dependsOnID string, kind ResultDependencyKind) (ResultDependency, error) {
	var edge ResultDependency
	err := store.db.QueryRowContext(ctx, `
		SELECT dependency_id, result_id, depends_on_result_id, kind, reason, created_at_ms
		FROM result_dependencies WHERE result_id = ? AND depends_on_result_id = ? AND kind = ?
	`, resultID, dependsOnID, kind).Scan(
		&edge.DependencyID, &edge.ResultID, &edge.DependsOnResultID, &edge.Kind, &edge.Reason, &edge.CreatedAtMS,
	)
	if err != nil {
		return ResultDependency{}, err
	}
	return edge, nil
}

func BuildFrozenCandidate(
	ctx context.Context,
	repository Repository,
	params BuildFrozenCandidateParams,
) (candidate FrozenCandidate, returnErr error) {
	if strings.TrimSpace(params.TargetRef) == "" || len(params.ResultIDs) == 0 {
		return FrozenCandidate{}, fmt.Errorf("%w: target ref and at least one Result are required", ErrInvalidArgument)
	}
	canonical, err := canonicalAllocationRepository(ctx, repository)
	if err != nil {
		return FrozenCandidate{}, err
	}
	targetRef, err := resolveMutableTargetRef(ctx, canonical.PrimaryRoot, params.TargetRef)
	if err != nil {
		return FrozenCandidate{}, err
	}
	targetOID, err := resolveGitCommit(ctx, canonical.Root, targetRef)
	if err != nil {
		return FrozenCandidate{}, err
	}
	store, err := Open(ctx, canonical.DatabasePath)
	if err != nil {
		return FrozenCandidate{}, err
	}
	defer func() {
		if closeErr := store.Close(); closeErr != nil {
			returnErr = errors.Join(returnErr, closeErr)
		}
	}()
	orderedResults, err := store.resolveCandidateResultOrder(ctx, params.ResultIDs, targetRef)
	if err != nil {
		return FrozenCandidate{}, err
	}
	memberIDs := make([]string, len(orderedResults))
	memberBindings := make([][]string, len(orderedResults))
	for index, result := range orderedResults {
		memberIDs[index] = result.ResultID
		memberBindings[index] = []string{result.ResultID, result.ManifestSHA256, result.ResultCommitOID}
	}
	requestedDigest, err := digestCanonicalJSON(params.ResultIDs)
	if err != nil {
		return FrozenCandidate{}, err
	}
	identityDigest, err := digestCanonicalJSON(struct {
		TargetRef string     `json:"target_ref"`
		TargetOID string     `json:"target_oid"`
		Members   [][]string `json:"members"`
	}{TargetRef: targetRef, TargetOID: targetOID, Members: memberBindings})
	if err != nil {
		return FrozenCandidate{}, err
	}
	candidateID := "candidate-" + identityDigest[:24]
	buildID := "candidate-build-" + identityDigest[:24]
	workspaceRoot := filepath.Join(canonical.CommonDir, "specify-runtime", "worktrees", "candidates", candidateID)
	nowMS := time.Now().UTC().UnixMilli()
	if _, err := store.db.ExecContext(ctx, `
		INSERT INTO candidate_builds (
			build_id, target_ref, expected_target_oid, requested_results_sha256,
			workspace_root, status, reason, created_at_ms, updated_at_ms
		) VALUES (?, ?, ?, ?, ?, ?, '', ?, ?)
		ON CONFLICT(build_id) DO NOTHING
	`, buildID, targetRef, targetOID, requestedDigest, workspaceRoot,
		CandidateBuildPrepared, nowMS, nowMS); err != nil {
		return FrozenCandidate{}, fmt.Errorf("record Candidate Build: %w", err)
	}
	if existing, err := store.GetFrozenCandidate(ctx, candidateID); err == nil {
		return existing, nil
	} else if !errors.Is(err, ErrCandidateNotFound) {
		return FrozenCandidate{}, err
	}
	if err := safeMkdirAllWithin(canonical.CommonDir, filepath.Dir(workspaceRoot)); err != nil {
		return FrozenCandidate{}, err
	}
	if _, err := os.Lstat(workspaceRoot); err == nil {
		return FrozenCandidate{}, fmt.Errorf("%w: Candidate workspace %q already exists", ErrWorkspaceConflict, workspaceRoot)
	} else if !errors.Is(err, os.ErrNotExist) {
		return FrozenCandidate{}, err
	}
	if _, err := store.db.ExecContext(ctx, `
		UPDATE candidate_builds SET status = ?, updated_at_ms = ? WHERE build_id = ? AND status = ?
	`, CandidateBuildExecuting, time.Now().UTC().UnixMilli(), buildID, CandidateBuildPrepared); err != nil {
		return FrozenCandidate{}, err
	}
	if err := runGitMutationWithRetry(ctx, canonical.Root, "worktree", "add", "--detach", workspaceRoot, targetOID); err != nil {
		_ = markCandidateBuild(ctx, store, buildID, CandidateBuildFailed, err.Error())
		return FrozenCandidate{}, fmt.Errorf("materialize Candidate workspace: %w", err)
	}
	cleanupWorkspace := true
	defer func() {
		if cleanupWorkspace {
			_ = runGitMutationWithRetry(context.Background(), canonical.Root, "worktree", "remove", "--force", workspaceRoot)
		}
	}()
	for _, result := range orderedResults {
		current, exists, err := resolveOptionalGitCommit(ctx, canonical.Root, result.HiddenRef)
		if err != nil || !exists || current != result.ResultCommitOID {
			_ = markCandidateBuild(ctx, store, buildID, CandidateBuildFailed, "Result ref binding changed")
			return FrozenCandidate{}, fmt.Errorf("%w: Result %q hidden ref is not immutable", ErrCandidateBinding, result.ResultID)
		}
		if _, err := runGitWithEnvironment(
			ctx,
			workspaceRoot,
			map[string]string{
				"GIT_AUTHOR_NAME": "Spec Kit Plus", "GIT_AUTHOR_EMAIL": "spec-kit-plus@invalid",
				"GIT_COMMITTER_NAME": "Spec Kit Plus", "GIT_COMMITTER_EMAIL": "spec-kit-plus@invalid",
			},
			"cherry-pick", "--allow-empty", result.ResultCommitOID,
		); err != nil {
			_ = markCandidateBuild(ctx, store, buildID, CandidateBuildConflicted, err.Error())
			cleanupWorkspace = false
			return FrozenCandidate{}, fmt.Errorf("%w: applying Result %q: %v", ErrCandidateBuildConflict, result.ResultID, err)
		}
	}
	currentTarget, err := resolveGitCommit(ctx, canonical.Root, targetRef)
	if err != nil {
		return FrozenCandidate{}, err
	}
	if currentTarget != targetOID {
		_ = markCandidateBuild(ctx, store, buildID, CandidateBuildStale, "target ref changed during build")
		return FrozenCandidate{}, fmt.Errorf("%w: target moved from %s to %s", ErrCandidateStale, targetOID, currentTarget)
	}
	commitOID, err := resolveGitCommit(ctx, workspaceRoot, "HEAD")
	if err != nil {
		return FrozenCandidate{}, err
	}
	treeOID, err := runGitOutput(ctx, workspaceRoot, "rev-parse", "HEAD^{tree}")
	if err != nil {
		return FrozenCandidate{}, err
	}
	treeOID = strings.ToLower(strings.TrimSpace(treeOID))
	hiddenRef := "refs/specify/candidates/" + candidateID
	if err := createImmutableGitRef(ctx, canonical.Root, hiddenRef, commitOID); err != nil {
		return FrozenCandidate{}, err
	}
	manifestSHA256, err := digestCanonicalJSON(struct {
		CandidateID       string     `json:"candidate_id"`
		TargetRef         string     `json:"target_ref"`
		ExpectedTargetOID string     `json:"expected_target_oid"`
		TreeOID           string     `json:"tree_oid"`
		CommitOID         string     `json:"commit_oid"`
		HiddenRef         string     `json:"hidden_ref"`
		Members           [][]string `json:"members"`
	}{
		CandidateID: candidateID, TargetRef: targetRef, ExpectedTargetOID: targetOID,
		TreeOID: treeOID, CommitOID: commitOID, HiddenRef: hiddenRef, Members: memberBindings,
	})
	if err != nil {
		return FrozenCandidate{}, err
	}
	candidate = FrozenCandidate{
		CandidateID: candidateID, BuildID: buildID, TargetRef: targetRef,
		ExpectedTargetOID: targetOID, TreeOID: treeOID, CommitOID: commitOID,
		HiddenRef: hiddenRef, ManifestSHA256: manifestSHA256,
		MemberResultIDs: append([]string(nil), memberIDs...), Status: CandidateBuildSucceeded,
		CreatedAtMS: time.Now().UTC().UnixMilli(),
	}
	tx, err := store.db.BeginTx(ctx, nil)
	if err != nil {
		return FrozenCandidate{}, err
	}
	defer func() { _ = tx.Rollback() }()
	if _, err := tx.ExecContext(ctx, `
		INSERT INTO frozen_candidates (
			candidate_id, build_id, target_ref, expected_target_oid, tree_oid,
			commit_oid, hidden_ref, manifest_sha256, status, created_at_ms
		) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
	`, candidate.CandidateID, candidate.BuildID, candidate.TargetRef, candidate.ExpectedTargetOID,
		candidate.TreeOID, candidate.CommitOID, candidate.HiddenRef, candidate.ManifestSHA256,
		candidate.Status, candidate.CreatedAtMS); err != nil {
		return FrozenCandidate{}, fmt.Errorf("insert frozen Candidate: %w", err)
	}
	for index, result := range orderedResults {
		if _, err := tx.ExecContext(ctx, `
			INSERT INTO frozen_candidate_members (
				candidate_id, ordinal, result_id, result_manifest_sha256
			) VALUES (?, ?, ?, ?)
		`, candidate.CandidateID, index+1, result.ResultID, result.ManifestSHA256); err != nil {
			return FrozenCandidate{}, fmt.Errorf("insert Candidate member: %w", err)
		}
	}
	if _, err := tx.ExecContext(ctx, `
		UPDATE candidate_builds SET status = ?, reason = '', updated_at_ms = ? WHERE build_id = ?
	`, CandidateBuildSucceeded, candidate.CreatedAtMS, buildID); err != nil {
		return FrozenCandidate{}, err
	}
	if err := tx.Commit(); err != nil {
		return FrozenCandidate{}, fmt.Errorf("commit frozen Candidate: %w", err)
	}
	return candidate, nil
}

func (store *Store) GetFrozenCandidate(ctx context.Context, candidateID string) (FrozenCandidate, error) {
	if strings.TrimSpace(candidateID) == "" {
		return FrozenCandidate{}, fmt.Errorf("%w: Candidate id is required", ErrInvalidArgument)
	}
	var candidate FrozenCandidate
	err := store.db.QueryRowContext(ctx, `
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
	rows, err := store.db.QueryContext(ctx, `
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

func (store *Store) resolveCandidateResultOrder(ctx context.Context, requested []string, targetRef string) ([]RunResult, error) {
	requestedSeen := make(map[string]struct{}, len(requested))
	for _, resultID := range requested {
		if strings.TrimSpace(resultID) == "" {
			return nil, fmt.Errorf("%w: empty Result id", ErrInvalidArgument)
		}
		if _, exists := requestedSeen[resultID]; exists {
			return nil, fmt.Errorf("%w: duplicate Result %q", ErrInvalidArgument, resultID)
		}
		requestedSeen[resultID] = struct{}{}
	}
	state := make(map[string]uint8)
	ordered := make([]RunResult, 0, len(requested))
	loaded := make(map[string]RunResult)
	var visit func(string) error
	visit = func(resultID string) error {
		switch state[resultID] {
		case 1:
			return fmt.Errorf("%w at Result %q", ErrResultDependencyCycle, resultID)
		case 2:
			return nil
		}
		state[resultID] = 1
		result, ok := loaded[resultID]
		if !ok {
			var err error
			result, err = store.GetRunResult(ctx, resultID)
			if err != nil {
				return err
			}
			loaded[resultID] = result
		}
		if result.TargetRef != targetRef || result.Eligibility != ResultEligibilityReady {
			return fmt.Errorf("%w: Result %q is not ready for target %q", ErrCandidateBinding, resultID, targetRef)
		}
		dependencies, err := store.listDependenciesForResult(ctx, resultID)
		if err != nil {
			return err
		}
		for _, dependency := range dependencies {
			if dependency.Kind == ResultDependencyConflictsWith {
				if _, selected := requestedSeen[dependency.DependsOnResultID]; selected || state[dependency.DependsOnResultID] != 0 {
					return fmt.Errorf("%w: %s conflicts with %s", ErrResultConflict, resultID, dependency.DependsOnResultID)
				}
				continue
			}
			if dependency.Kind == ResultDependencyRequires {
				if err := visit(dependency.DependsOnResultID); err != nil {
					return err
				}
			}
		}
		state[resultID] = 2
		ordered = append(ordered, result)
		return nil
	}
	for _, resultID := range requested {
		if err := visit(resultID); err != nil {
			return nil, err
		}
	}
	return ordered, nil
}

func (store *Store) listDependenciesForResult(ctx context.Context, resultID string) ([]ResultDependency, error) {
	rows, err := store.db.QueryContext(ctx, `
		SELECT dependency_id, result_id, depends_on_result_id, kind, reason, created_at_ms
		FROM result_dependencies WHERE result_id = ?
		ORDER BY CASE kind WHEN 'requires' THEN 0 WHEN 'after' THEN 1 ELSE 2 END,
		         created_at_ms, dependency_id
	`, resultID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	edges := make([]ResultDependency, 0)
	for rows.Next() {
		var edge ResultDependency
		if err := rows.Scan(&edge.DependencyID, &edge.ResultID, &edge.DependsOnResultID, &edge.Kind, &edge.Reason, &edge.CreatedAtMS); err != nil {
			return nil, err
		}
		edges = append(edges, edge)
	}
	return edges, rows.Err()
}

func markCandidateBuild(ctx context.Context, store *Store, buildID string, status CandidateBuildStatus, reason string) error {
	_, err := store.db.ExecContext(ctx, `
		UPDATE candidate_builds SET status = ?, reason = ?, updated_at_ms = ? WHERE build_id = ?
	`, status, reason, time.Now().UTC().UnixMilli(), buildID)
	return err
}

func sortedUniqueStrings(values []string) []string {
	seen := make(map[string]struct{}, len(values))
	result := make([]string, 0, len(values))
	for _, value := range values {
		if _, exists := seen[value]; exists {
			continue
		}
		seen[value] = struct{}{}
		result = append(result, value)
	}
	sort.Strings(result)
	return result
}
