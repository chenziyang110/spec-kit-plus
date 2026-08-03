package runcontrol

import (
	"context"
	"database/sql"
	"errors"
	"fmt"
	"path/filepath"
	"strings"
	"time"
)

type WorkspacePolicy string

const (
	WorkspacePolicyAuto     WorkspacePolicy = "auto"
	WorkspacePolicyPrimary  WorkspacePolicy = "primary"
	WorkspacePolicyIsolated WorkspacePolicy = "isolated"
)

const primaryWorkspaceSchemaSQL = `
CREATE TABLE IF NOT EXISTS workspace_routes (
    workspace_id TEXT PRIMARY KEY REFERENCES workspaces(workspace_id) ON DELETE RESTRICT,
    mode TEXT NOT NULL CHECK (mode IN ('primary', 'isolated')),
    source_run_id TEXT REFERENCES runs(run_id) ON DELETE RESTRICT,
    created_at_ms INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS workspace_routes_source_run
    ON workspace_routes(source_run_id, mode, workspace_id);

CREATE TABLE IF NOT EXISTS primary_workspace_slots (
    slot_id INTEGER PRIMARY KEY CHECK (slot_id = 1),
    run_id TEXT NOT NULL UNIQUE REFERENCES runs(run_id) ON DELETE RESTRICT,
    owner_epoch TEXT NOT NULL REFERENCES supervisor_instances(owner_epoch) ON DELETE RESTRICT,
    root_path TEXT NOT NULL,
    acquired_at_ms INTEGER NOT NULL
);
`

func normalizeWorkspaceMode(mode WorkspaceMode) WorkspaceMode {
	if mode == "" {
		return WorkspaceModeIsolated
	}
	return mode
}

func normalizeWorkspacePolicy(policy WorkspacePolicy) WorkspacePolicy {
	if policy == "" {
		return WorkspacePolicyAuto
	}
	return policy
}

func planSupervisedWorkspace(
	ctx context.Context,
	store *Store,
	repository Repository,
	run Run,
	generation int64,
	policy WorkspacePolicy,
) (CreateWorkspaceParams, error) {
	policy = normalizeWorkspacePolicy(policy)
	if policy != WorkspacePolicyAuto && policy != WorkspacePolicyPrimary && policy != WorkspacePolicyIsolated {
		return CreateWorkspaceParams{}, fmt.Errorf("%w: unsupported workspace policy %q", ErrInvalidArgument, policy)
	}
	isolated, err := PlanGitWorkspace(ctx, repository, run, generation)
	if err != nil {
		return CreateWorkspaceParams{}, err
	}
	isolated.Mode = WorkspaceModeIsolated
	if policy == WorkspacePolicyIsolated {
		return isolated, nil
	}

	primary, primaryErr := planPrimaryWorkspaceBinding(ctx, repository, run, generation)
	if primaryErr != nil {
		if policy == WorkspacePolicyPrimary {
			return CreateWorkspaceParams{}, primaryErr
		}
		return isolated, nil
	}
	primary.Mode = WorkspaceModePrimary

	holderRunID, acquired, err := store.acquirePrimaryWorkspaceSlot(ctx, run, primary.RootPath)
	if err != nil {
		return CreateWorkspaceParams{}, err
	}
	if acquired {
		if pristineErr := requirePristinePrimaryWorkspace(ctx, primary.RootPath, primary.BaseRef); pristineErr != nil {
			if releaseErr := store.releasePrimaryWorkspaceSlot(ctx, run.RunID); releaseErr != nil {
				return CreateWorkspaceParams{}, errors.Join(pristineErr, releaseErr)
			}
			if policy == WorkspacePolicyPrimary {
				return CreateWorkspaceParams{}, pristineErr
			}
			return isolated, nil
		}
		primary.SourceRunID = run.RunID
		return primary, nil
	}
	if policy == WorkspacePolicyPrimary {
		return CreateWorkspaceParams{}, fmt.Errorf(
			"%w: primary workspace is owned by Run %q",
			ErrResourceConflict,
			holderRunID,
		)
	}
	isolated.SourceRunID = holderRunID
	return isolated, nil
}

func (store *Store) releasePrimaryWorkspaceSlot(ctx context.Context, runID string) error {
	if strings.TrimSpace(runID) == "" {
		return fmt.Errorf("%w: Run id is required to release primary workspace", ErrInvalidArgument)
	}
	if _, err := store.db.ExecContext(ctx, `DELETE FROM primary_workspace_slots WHERE run_id = ?`, runID); err != nil {
		return fmt.Errorf("release primary workspace slot for Run %q: %w", runID, err)
	}
	return nil
}

func (store *Store) acquirePrimaryWorkspaceSlot(
	ctx context.Context,
	run Run,
	rootPath string,
) (holderRunID string, acquired bool, returnErr error) {
	if strings.TrimSpace(run.RunID) == "" || strings.TrimSpace(rootPath) == "" {
		return "", false, fmt.Errorf("%w: Run and primary root are required", ErrInvalidArgument)
	}
	tx, err := store.db.BeginTx(ctx, nil)
	if err != nil {
		return "", false, fmt.Errorf("begin primary workspace election: %w", err)
	}
	defer func() { _ = tx.Rollback() }()
	if err := requireActiveSupervisorTx(ctx, tx, store.ownerEpoch); err != nil {
		return "", false, err
	}
	if _, err := tx.ExecContext(ctx, `
		DELETE FROM primary_workspace_slots
		WHERE run_id IN (
			SELECT run_id FROM runs
			WHERE status IN ('sealed', 'cancelled', 'failed')
		) OR owner_epoch IN (
			SELECT owner_epoch FROM supervisor_instances WHERE status <> 'active'
		)
	`); err != nil {
		return "", false, fmt.Errorf("reap obsolete primary workspace slot: %w", err)
	}

	var holderRoot string
	err = tx.QueryRowContext(ctx, `
		SELECT run_id, root_path FROM primary_workspace_slots WHERE slot_id = 1
	`).Scan(&holderRunID, &holderRoot)
	if errors.Is(err, sql.ErrNoRows) {
		nowMS := time.Now().UTC().UnixMilli()
		if _, err := tx.ExecContext(ctx, `
			INSERT INTO primary_workspace_slots (
				slot_id, run_id, owner_epoch, root_path, acquired_at_ms
			) VALUES (1, ?, ?, ?, ?)
		`, run.RunID, store.ownerEpoch, filepath.Clean(rootPath), nowMS); err != nil {
			return "", false, fmt.Errorf("claim primary workspace slot: %w", err)
		}
		holderRunID = run.RunID
		holderRoot = filepath.Clean(rootPath)
		acquired = true
	} else if err != nil {
		return "", false, fmt.Errorf("read primary workspace slot: %w", err)
	} else {
		acquired = holderRunID == run.RunID && sameFilesystemPath(holderRoot, rootPath)
		if holderRunID == run.RunID && !acquired {
			return "", false, fmt.Errorf("%w: primary workspace root changed for Run %q", ErrWorkspaceBinding, run.RunID)
		}
	}
	if err := tx.Commit(); err != nil {
		return "", false, fmt.Errorf("commit primary workspace election: %w", err)
	}
	return holderRunID, acquired, nil
}

func releasePrimaryWorkspaceSlotTx(ctx context.Context, tx *sql.Tx, runID string) error {
	if strings.TrimSpace(runID) == "" {
		return fmt.Errorf("%w: Run id is required to release primary workspace", ErrInvalidArgument)
	}
	if _, err := tx.ExecContext(ctx, `
		DELETE FROM primary_workspace_slots WHERE run_id = ?
	`, runID); err != nil {
		return fmt.Errorf("release primary workspace slot for Run %q: %w", runID, err)
	}
	return nil
}

func prepareWorkspaceSnapshot(
	ctx context.Context,
	store *Store,
	repository Repository,
	run Run,
	workspace Workspace,
) (Snapshot, []SnapshotEntry, error) {
	if existing, err := store.GetSnapshotForRun(ctx, run.RunID); err == nil {
		entries, listErr := store.ListSnapshotEntries(ctx, existing.SnapshotID)
		return existing, entries, listErr
	} else if !errors.Is(err, ErrNotFound) {
		return Snapshot{}, nil, err
	}

	snapshotID := supervisedAggregateID("snapshot", run.RunID, 0)
	attemptID := supervisedAggregateID("attempt", run.RunID, workspace.Generation)
	var captured CreateSnapshotParams
	var err error
	if workspace.SourceRunID != "" && workspace.SourceRunID != run.RunID {
		source, sourceEntries, waitErr := waitForRunSnapshot(ctx, store, workspace.SourceRunID)
		if waitErr != nil {
			return Snapshot{}, nil, waitErr
		}
		if source.TargetRef == workspace.BaseRef && source.BaseCommit == workspace.BaseCommit {
			captured, err = cloneSnapshotForWorkspace(snapshotID, attemptID, run, workspace, source, sourceEntries)
		} else {
			captured, err = emptySnapshotForWorkspace(ctx, snapshotID, attemptID, repository, run, workspace)
		}
	} else {
		captured, err = CaptureAmbientSnapshot(ctx, repository, workspace, CaptureSnapshotParams{
			SnapshotID: snapshotID,
			RunID:      run.RunID,
			AttemptID:  attemptID,
			TargetRef:  workspace.BaseRef,
			SourceRoot: repository.Root,
			Scope:      SnapshotContextOnly,
		})
		if err != nil && workspace.Mode == WorkspaceModeIsolated && errors.Is(err, ErrWorkspaceBinding) {
			captured, err = emptySnapshotForWorkspace(ctx, snapshotID, attemptID, repository, run, workspace)
		}
	}
	if err != nil {
		return Snapshot{}, nil, err
	}
	snapshot, err := store.CreateSnapshot(ctx, captured)
	if err != nil {
		return Snapshot{}, nil, err
	}
	entries, err := store.ListSnapshotEntries(ctx, snapshot.SnapshotID)
	return snapshot, entries, err
}

func waitForRunSnapshot(ctx context.Context, store *Store, runID string) (Snapshot, []SnapshotEntry, error) {
	ticker := time.NewTicker(20 * time.Millisecond)
	defer ticker.Stop()
	for {
		snapshot, err := store.GetSnapshotForRun(ctx, runID)
		if err == nil {
			entries, listErr := store.ListSnapshotEntries(ctx, snapshot.SnapshotID)
			return snapshot, entries, listErr
		}
		if !errors.Is(err, ErrNotFound) {
			return Snapshot{}, nil, err
		}
		sourceRun, runErr := store.GetRun(ctx, runID)
		if runErr != nil {
			return Snapshot{}, nil, runErr
		}
		if sourceRun.Status == RunCancelled || sourceRun.Status == RunFailed || sourceRun.Status == RunInterrupted {
			return Snapshot{}, nil, fmt.Errorf("%w: source Run %q ended before its prelaunch Snapshot", ErrWorkspaceBinding, runID)
		}
		select {
		case <-ctx.Done():
			return Snapshot{}, nil, ctx.Err()
		case <-ticker.C:
		}
	}
}

func cloneSnapshotForWorkspace(
	snapshotID string,
	attemptID string,
	run Run,
	workspace Workspace,
	source Snapshot,
	sourceEntries []SnapshotEntry,
) (CreateSnapshotParams, error) {
	entries := make([]SnapshotEntry, len(sourceEntries))
	for index, sourceEntry := range sourceEntries {
		entry := hydrateSnapshotEntryCompatibility(sourceEntry)
		entry.EntryID = supervisedAggregateID(
			"snapshot-entry",
			snapshotID+"/"+string(entry.Provenance)+"/"+entry.RelativePath,
			int64(index+1),
		)
		entry.SnapshotID = snapshotID
		entry.Ordinal = int64(index + 1)
		entries[index] = entry
	}
	overlayDigest := digestAmbientEntries(entries)
	inputDigest, err := digestCanonicalJSON(struct {
		SourceInputSHA256 string `json:"source_input_sha256"`
		RunID             string `json:"run_id"`
		AttemptID         string `json:"attempt_id"`
		WorkspaceID       string `json:"workspace_id"`
		Generation        int64  `json:"generation"`
		WorkspaceRoot     string `json:"workspace_root"`
		OverlaySHA256     string `json:"overlay_sha256"`
	}{
		SourceInputSHA256: source.InputManifestSHA256,
		RunID:             run.RunID,
		AttemptID:         attemptID,
		WorkspaceID:       workspace.WorkspaceID,
		Generation:        workspace.Generation,
		WorkspaceRoot:     filepath.Clean(workspace.RootPath),
		OverlaySHA256:     overlayDigest,
	})
	if err != nil {
		return CreateSnapshotParams{}, err
	}
	return CreateSnapshotParams{
		SnapshotID: snapshotID, RunID: run.RunID, AttemptID: attemptID,
		WorkspaceID: workspace.WorkspaceID, WorkspaceGeneration: workspace.Generation,
		TargetRef: workspace.BaseRef, SourceRoot: source.SourceRoot,
		WorkspaceRoot: workspace.RootPath, RepoCommonDir: workspace.RepoCommonDir,
		PrivateRef: workspace.PrivateRef, BaseCommit: workspace.BaseCommit,
		BaseTree: source.BaseTree, OverlayManifestSHA256: overlayDigest,
		InputManifestSHA256: inputDigest, Scope: source.Scope,
		ScanDigest: overlayDigest, Entries: entries,
	}, nil
}

func emptySnapshotForWorkspace(
	ctx context.Context,
	snapshotID string,
	attemptID string,
	repository Repository,
	run Run,
	workspace Workspace,
) (CreateSnapshotParams, error) {
	baseTree, err := runGitOutput(ctx, repository.Root, "rev-parse", workspace.BaseCommit+"^{tree}")
	if err != nil {
		return CreateSnapshotParams{}, err
	}
	overlayDigest := digestAmbientEntries(nil)
	inputDigest, err := digestCanonicalJSON(struct {
		RunID         string `json:"run_id"`
		AttemptID     string `json:"attempt_id"`
		WorkspaceID   string `json:"workspace_id"`
		Generation    int64  `json:"generation"`
		BaseCommitOID string `json:"base_commit_oid"`
		BaseTreeOID   string `json:"base_tree_oid"`
	}{run.RunID, attemptID, workspace.WorkspaceID, workspace.Generation, workspace.BaseCommit, baseTree})
	if err != nil {
		return CreateSnapshotParams{}, err
	}
	return CreateSnapshotParams{
		SnapshotID: snapshotID, RunID: run.RunID, AttemptID: attemptID,
		WorkspaceID: workspace.WorkspaceID, WorkspaceGeneration: workspace.Generation,
		TargetRef: workspace.BaseRef, SourceRoot: repository.Root,
		WorkspaceRoot: workspace.RootPath, RepoCommonDir: workspace.RepoCommonDir,
		PrivateRef: workspace.PrivateRef, BaseCommit: workspace.BaseCommit,
		BaseTree: baseTree, OverlayManifestSHA256: overlayDigest,
		InputManifestSHA256: inputDigest, Scope: SnapshotContextOnly,
		ScanDigest: overlayDigest, Entries: []SnapshotEntry{},
	}, nil
}
