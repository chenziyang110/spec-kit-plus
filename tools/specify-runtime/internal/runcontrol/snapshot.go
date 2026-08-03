package runcontrol

import (
	"context"
	"crypto/sha256"
	"database/sql"
	"encoding/hex"
	"errors"
	"fmt"
	"io/fs"
	"os"
	"os/exec"
	"path/filepath"
	"regexp"
	"sort"
	"strconv"
	"strings"
	"time"
)

var (
	ErrSnapshotDrift           = errors.New("snapshot ambient scan changed during capture")
	ErrSnapshotSecretCandidate = errors.New("snapshot ambient capture blocked by secret candidate")
	ErrSnapshotApplyConflict   = errors.New("snapshot ambient apply target is not safe")
)

type SnapshotDeliveryPolicy string
type SnapshotScope = SnapshotDeliveryPolicy

const (
	SnapshotContextOnly SnapshotDeliveryPolicy = "context_only"
	SnapshotRestorable  SnapshotDeliveryPolicy = "restorable"

	SnapshotScopeContextOnly = SnapshotContextOnly
	SnapshotScopeRestorable  = SnapshotRestorable
)

type SnapshotProvenance string
type SnapshotEntryOrigin = SnapshotProvenance

const (
	SnapshotProvenanceStaged    SnapshotProvenance = "staged"
	SnapshotProvenanceUnstaged  SnapshotProvenance = "unstaged"
	SnapshotProvenanceUntracked SnapshotProvenance = "untracked"

	SnapshotEntryStaged    = SnapshotProvenanceStaged
	SnapshotEntryUnstaged  = SnapshotProvenanceUnstaged
	SnapshotEntryUntracked = SnapshotProvenanceUntracked
)

type SnapshotEntryKind string

const (
	SnapshotEntryFile    SnapshotEntryKind = "file"
	SnapshotEntryDeleted SnapshotEntryKind = "deleted"
)

type Snapshot struct {
	SnapshotID            string
	RunID                 string
	AttemptID             string
	WorkspaceID           string
	WorkspaceGeneration   int64
	TargetRef             string
	SourceRoot            string
	WorkspaceRoot         string
	RepoCommonDir         string
	PrivateRef            string
	BaseCommit            string
	BaseTree              string
	OverlayManifestSHA256 string
	InputManifestSHA256   string
	Scope                 SnapshotScope
	ScanDigest            string
	EntryCount            int64
	CreatedAtMS           int64
	UpdatedAtMS           int64
}

type SnapshotEntry struct {
	EntryID        string
	SnapshotID     string
	RelativePath   string
	Provenance     SnapshotProvenance
	Origin         SnapshotEntryOrigin
	DeliveryPolicy SnapshotDeliveryPolicy
	Kind           SnapshotEntryKind
	FileMode       int64
	BlobSHA256     string
	ContentSHA256  string
	ObjectPath     string
	SizeBytes      int64
	ContextOnly    bool
	Ordinal        int64
	CreatedAtMS    int64
}

type CreateSnapshotParams struct {
	SnapshotID            string
	RunID                 string
	AttemptID             string
	WorkspaceID           string
	WorkspaceGeneration   int64
	TargetRef             string
	SourceRoot            string
	WorkspaceRoot         string
	RepoCommonDir         string
	PrivateRef            string
	BaseCommit            string
	BaseTree              string
	OverlayManifestSHA256 string
	InputManifestSHA256   string
	Scope                 SnapshotScope
	ScanDigest            string
	Entries               []SnapshotEntry
}

type CaptureSnapshotParams struct {
	SnapshotID string
	RunID      string
	AttemptID  string
	TargetRef  string
	SourceRoot string
	Scope      SnapshotScope
}

const snapshotSchemaSQL = `
CREATE TABLE IF NOT EXISTS snapshots (
    snapshot_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL UNIQUE,
    attempt_id TEXT NOT NULL,
    workspace_id TEXT NOT NULL,
    workspace_generation INTEGER NOT NULL CHECK (workspace_generation > 0),
    target_ref TEXT NOT NULL,
    source_root TEXT NOT NULL,
    workspace_root TEXT NOT NULL,
    repo_common_dir TEXT NOT NULL,
    private_ref TEXT NOT NULL,
    base_commit TEXT NOT NULL,
    base_tree TEXT NOT NULL,
    overlay_manifest_sha256 TEXT NOT NULL CHECK (
        length(overlay_manifest_sha256) = 64 AND overlay_manifest_sha256 NOT GLOB '*[^0-9a-f]*'
    ),
    input_manifest_sha256 TEXT NOT NULL CHECK (
        length(input_manifest_sha256) = 64 AND input_manifest_sha256 NOT GLOB '*[^0-9a-f]*'
    ),
    default_delivery_policy TEXT NOT NULL CHECK (default_delivery_policy IN ('context_only', 'restorable')),
    entry_count INTEGER NOT NULL CHECK (entry_count >= 0),
    created_at_ms INTEGER NOT NULL,
    updated_at_ms INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS snapshot_entries (
    entry_id TEXT PRIMARY KEY,
    snapshot_id TEXT NOT NULL REFERENCES snapshots(snapshot_id) ON DELETE CASCADE,
    ordinal INTEGER NOT NULL CHECK (ordinal > 0),
    relative_path TEXT NOT NULL,
    provenance TEXT NOT NULL CHECK (provenance IN ('staged', 'unstaged', 'untracked')),
    kind TEXT NOT NULL CHECK (kind IN ('file', 'deleted')),
    file_mode INTEGER NOT NULL CHECK (file_mode >= 0),
    blob_sha256 TEXT NOT NULL CHECK (
        blob_sha256 = '' OR (length(blob_sha256) = 64 AND blob_sha256 NOT GLOB '*[^0-9a-f]*')
    ),
    object_path TEXT NOT NULL,
    size_bytes INTEGER NOT NULL CHECK (size_bytes >= 0),
    delivery_policy TEXT NOT NULL CHECK (delivery_policy IN ('context_only', 'restorable')),
    created_at_ms INTEGER NOT NULL,
    UNIQUE (snapshot_id, ordinal),
    UNIQUE (snapshot_id, provenance, relative_path)
);

CREATE INDEX IF NOT EXISTS snapshot_entries_snapshot_order
    ON snapshot_entries(snapshot_id, ordinal);
`

func (store *Store) CreateSnapshot(ctx context.Context, params CreateSnapshotParams) (Snapshot, error) {
	if err := store.ensureSnapshotSchema(ctx); err != nil {
		return Snapshot{}, err
	}
	if strings.TrimSpace(params.RunID) != "" {
		if _, err := store.GetSnapshotForRun(ctx, params.RunID); err == nil {
			return Snapshot{}, fmt.Errorf("%w: run %q already has a snapshot", ErrAlreadyExists, params.RunID)
		} else if !errors.Is(err, ErrNotFound) {
			return Snapshot{}, err
		}
	}
	if err := validateCreateSnapshotParams(params); err != nil {
		return Snapshot{}, err
	}

	transaction, err := store.db.BeginTx(ctx, nil)
	if err != nil {
		return Snapshot{}, fmt.Errorf("begin snapshot create transaction: %w", err)
	}
	defer func() { _ = transaction.Rollback() }()

	nowMS := time.Now().UTC().UnixMilli()
	snapshot := Snapshot{
		SnapshotID:            params.SnapshotID,
		RunID:                 params.RunID,
		AttemptID:             params.AttemptID,
		WorkspaceID:           params.WorkspaceID,
		WorkspaceGeneration:   params.WorkspaceGeneration,
		TargetRef:             strings.TrimSpace(params.TargetRef),
		SourceRoot:            filepath.Clean(params.SourceRoot),
		WorkspaceRoot:         filepath.Clean(params.WorkspaceRoot),
		RepoCommonDir:         filepath.Clean(params.RepoCommonDir),
		PrivateRef:            strings.TrimSpace(params.PrivateRef),
		BaseCommit:            strings.TrimSpace(params.BaseCommit),
		BaseTree:              strings.TrimSpace(params.BaseTree),
		OverlayManifestSHA256: params.OverlayManifestSHA256,
		InputManifestSHA256:   params.InputManifestSHA256,
		Scope:                 normalizeSnapshotDeliveryPolicy(params.Scope),
		ScanDigest:            firstNonEmpty(params.ScanDigest, params.OverlayManifestSHA256),
		EntryCount:            int64(len(params.Entries)),
		CreatedAtMS:           nowMS,
		UpdatedAtMS:           nowMS,
	}
	if _, err := transaction.ExecContext(ctx, `
		INSERT INTO snapshots (
			snapshot_id, run_id, attempt_id, workspace_id, workspace_generation,
			target_ref, source_root, workspace_root, repo_common_dir, private_ref,
			base_commit, base_tree, overlay_manifest_sha256, input_manifest_sha256,
			default_delivery_policy, entry_count, created_at_ms, updated_at_ms
		) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
	`,
		snapshot.SnapshotID, snapshot.RunID, snapshot.AttemptID, snapshot.WorkspaceID,
		snapshot.WorkspaceGeneration, snapshot.TargetRef, snapshot.SourceRoot,
		snapshot.WorkspaceRoot, snapshot.RepoCommonDir, snapshot.PrivateRef,
		snapshot.BaseCommit, snapshot.BaseTree, snapshot.OverlayManifestSHA256,
		snapshot.InputManifestSHA256, snapshot.Scope, snapshot.EntryCount,
		snapshot.CreatedAtMS, snapshot.UpdatedAtMS,
	); err != nil {
		if isUniqueConstraintError(err) {
			return Snapshot{}, fmt.Errorf("%w: snapshot %q", ErrAlreadyExists, params.RunID)
		}
		return Snapshot{}, fmt.Errorf("insert snapshot: %w", err)
	}

	for index, raw := range params.Entries {
		entry, err := normalizedSnapshotEntry(raw, snapshot.Scope)
		if err != nil {
			return Snapshot{}, fmt.Errorf("normalize snapshot entry %d: %w", index+1, err)
		}
		entry.SnapshotID = snapshot.SnapshotID
		entry.Ordinal = int64(index + 1)
		entry.CreatedAtMS = nowMS
		if _, err := transaction.ExecContext(ctx, `
			INSERT INTO snapshot_entries (
				entry_id, snapshot_id, ordinal, relative_path, provenance, kind,
				file_mode, blob_sha256, object_path, size_bytes, delivery_policy, created_at_ms
			) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
		`,
			entry.EntryID, entry.SnapshotID, entry.Ordinal, entry.RelativePath,
			entry.Provenance, entry.Kind, entry.FileMode, entry.BlobSHA256,
			entry.ObjectPath, entry.SizeBytes, entry.DeliveryPolicy, entry.CreatedAtMS,
		); err != nil {
			if isUniqueConstraintError(err) {
				return Snapshot{}, fmt.Errorf("%w: snapshot entry %q", ErrAlreadyExists, entry.EntryID)
			}
			return Snapshot{}, fmt.Errorf("insert snapshot entry %q: %w", entry.EntryID, err)
		}
	}

	if err := transaction.Commit(); err != nil {
		return Snapshot{}, fmt.Errorf("commit snapshot create: %w", err)
	}
	return snapshot, nil
}

func (store *Store) GetSnapshot(ctx context.Context, snapshotID string) (Snapshot, error) {
	if strings.TrimSpace(snapshotID) == "" {
		return Snapshot{}, fmt.Errorf("%w: snapshot id is required", ErrInvalidArgument)
	}
	if err := store.ensureSnapshotSchema(ctx); err != nil {
		return Snapshot{}, err
	}
	return readSnapshotByID(ctx, store.db, snapshotID)
}

func (store *Store) GetSnapshotForRun(ctx context.Context, runID string) (Snapshot, error) {
	if strings.TrimSpace(runID) == "" {
		return Snapshot{}, fmt.Errorf("%w: run id is required", ErrInvalidArgument)
	}
	if err := store.ensureSnapshotSchema(ctx); err != nil {
		return Snapshot{}, err
	}
	return readSnapshotByRunID(ctx, store.db, runID)
}

func (store *Store) ListSnapshots(ctx context.Context, runID string) ([]Snapshot, error) {
	snapshot, err := store.GetSnapshotForRun(ctx, runID)
	if err != nil {
		if errors.Is(err, ErrNotFound) {
			return []Snapshot{}, nil
		}
		return nil, err
	}
	return []Snapshot{snapshot}, nil
}

func (store *Store) ListSnapshotEntries(ctx context.Context, snapshotID string) ([]SnapshotEntry, error) {
	if strings.TrimSpace(snapshotID) == "" {
		return nil, fmt.Errorf("%w: snapshot id is required", ErrInvalidArgument)
	}
	if err := store.ensureSnapshotSchema(ctx); err != nil {
		return nil, err
	}
	rows, err := store.db.QueryContext(ctx, `
		SELECT entry_id, snapshot_id, ordinal, relative_path, provenance, kind,
		       file_mode, blob_sha256, object_path, size_bytes, delivery_policy, created_at_ms
		FROM snapshot_entries
		WHERE snapshot_id = ?
		ORDER BY ordinal
	`, snapshotID)
	if err != nil {
		return nil, fmt.Errorf("list snapshot entries for %q: %w", snapshotID, err)
	}
	defer rows.Close()
	entries := make([]SnapshotEntry, 0)
	for rows.Next() {
		var entry SnapshotEntry
		if err := rows.Scan(
			&entry.EntryID,
			&entry.SnapshotID,
			&entry.Ordinal,
			&entry.RelativePath,
			&entry.Provenance,
			&entry.Kind,
			&entry.FileMode,
			&entry.BlobSHA256,
			&entry.ObjectPath,
			&entry.SizeBytes,
			&entry.DeliveryPolicy,
			&entry.CreatedAtMS,
		); err != nil {
			return nil, fmt.Errorf("scan snapshot entry for %q: %w", snapshotID, err)
		}
		entry = hydrateSnapshotEntryCompatibility(entry)
		entries = append(entries, entry)
	}
	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("iterate snapshot entries for %q: %w", snapshotID, err)
	}
	if len(entries) == 0 {
		if _, err := store.GetSnapshot(ctx, snapshotID); err != nil {
			return nil, err
		}
	}
	return entries, nil
}

func CaptureAmbientSnapshot(
	ctx context.Context,
	repository Repository,
	workspace Workspace,
	params CaptureSnapshotParams,
) (CreateSnapshotParams, error) {
	sourceRoot := strings.TrimSpace(params.SourceRoot)
	if sourceRoot == "" {
		sourceRoot = repository.Root
	}
	targetRef := strings.TrimSpace(params.TargetRef)
	if targetRef == "" {
		targetRef = workspace.PrivateRef
	}
	return captureAmbientSnapshotFromSource(ctx, repository, workspace, CaptureSnapshotParams{
		SnapshotID: params.SnapshotID,
		RunID:      params.RunID,
		AttemptID:  params.AttemptID,
		TargetRef:  targetRef,
		SourceRoot: sourceRoot,
		Scope:      params.Scope,
	})
}

func ApplySnapshotAmbientToWorkspace(
	ctx context.Context,
	repository Repository,
	workspace Workspace,
	snapshot Snapshot,
	entries []SnapshotEntry,
) error {
	canonical, err := canonicalAllocationRepository(ctx, repository)
	if err != nil {
		return err
	}
	if err := validateSnapshotWorkspaceBinding(ctx, canonical, workspace); err != nil {
		return err
	}
	if workspaceIsPrimary(workspace, canonical) {
		return fmt.Errorf("%w: snapshots cannot be applied onto primary workspace %q", ErrSnapshotApplyConflict, workspace.WorkspaceID)
	}
	if snapshot.RunID != workspace.RunID ||
		!sameFilesystemPath(snapshot.RepoCommonDir, canonical.CommonDir) ||
		snapshot.TargetRef != workspace.BaseRef ||
		snapshot.BaseCommit != workspace.BaseCommit {
		return fmt.Errorf("%w: snapshot %q does not match workspace %q generation %d", ErrSnapshotApplyConflict, snapshot.SnapshotID, workspace.WorkspaceID, workspace.Generation)
	}

	sortedEntries := append([]SnapshotEntry(nil), entries...)
	sort.Slice(sortedEntries, func(i, j int) bool { return sortedEntries[i].Ordinal < sortedEntries[j].Ordinal })
	for _, raw := range sortedEntries {
		entry := hydrateSnapshotEntryCompatibility(raw)
		targetPath, err := resolveSnapshotTargetPath(workspace.RootPath, entry.RelativePath)
		if err != nil {
			return err
		}
		switch entry.Kind {
		case SnapshotEntryDeleted:
			if err := removeSnapshotTarget(targetPath, workspace.RootPath); err != nil {
				return err
			}
		case SnapshotEntryFile:
			bytes, err := readSnapshotObjectBytes(canonical.CommonDir, entry)
			if err != nil {
				return err
			}
			if err := writeSnapshotTarget(targetPath, workspace.RootPath, bytes, fs.FileMode(entry.FileMode)); err != nil {
				return err
			}
		default:
			return fmt.Errorf("%w: unsupported snapshot entry kind %q", ErrInvalidArgument, entry.Kind)
		}
	}
	return nil
}

func validateCreateSnapshotParams(params CreateSnapshotParams) error {
	required := map[string]string{
		"snapshot_id":             params.SnapshotID,
		"run_id":                  params.RunID,
		"attempt_id":              params.AttemptID,
		"workspace_id":            params.WorkspaceID,
		"target_ref":              params.TargetRef,
		"source_root":             params.SourceRoot,
		"workspace_root":          params.WorkspaceRoot,
		"repo_common_dir":         params.RepoCommonDir,
		"private_ref":             params.PrivateRef,
		"base_commit":             params.BaseCommit,
		"base_tree":               params.BaseTree,
		"overlay_manifest_sha256": params.OverlayManifestSHA256,
		"input_manifest_sha256":   params.InputManifestSHA256,
	}
	for name, value := range required {
		if strings.TrimSpace(value) == "" {
			return fmt.Errorf("%w: %s is required", ErrInvalidArgument, name)
		}
	}
	if params.WorkspaceGeneration <= 0 {
		return fmt.Errorf("%w: workspace generation must be positive", ErrInvalidArgument)
	}
	if normalizeSnapshotDeliveryPolicy(params.Scope) == "" {
		return fmt.Errorf("%w: snapshot delivery policy is invalid", ErrInvalidArgument)
	}
	if !validSHA256(params.OverlayManifestSHA256) || !validSHA256(params.InputManifestSHA256) {
		return fmt.Errorf("%w: snapshot manifests must be lowercase sha256 digests", ErrInvalidArgument)
	}
	if !filepath.IsAbs(params.SourceRoot) || !filepath.IsAbs(params.WorkspaceRoot) || !filepath.IsAbs(params.RepoCommonDir) {
		return fmt.Errorf("%w: snapshot roots must be absolute", ErrInvalidArgument)
	}
	seenEntries := make(map[string]struct{}, len(params.Entries))
	for index, raw := range params.Entries {
		entry, err := normalizedSnapshotEntry(raw, params.Scope)
		if err != nil {
			return fmt.Errorf("entry %d: %w", index+1, err)
		}
		if _, exists := seenEntries[entry.EntryID]; exists {
			return fmt.Errorf("%w: snapshot entry %q is duplicated", ErrInvalidArgument, entry.EntryID)
		}
		seenEntries[entry.EntryID] = struct{}{}
	}
	return nil
}

func normalizedSnapshotEntry(raw SnapshotEntry, defaultPolicy SnapshotDeliveryPolicy) (SnapshotEntry, error) {
	entry := hydrateSnapshotEntryCompatibility(raw)
	if strings.TrimSpace(entry.EntryID) == "" {
		return SnapshotEntry{}, fmt.Errorf("%w: snapshot entry id is required", ErrInvalidArgument)
	}
	if strings.TrimSpace(entry.RelativePath) == "" {
		return SnapshotEntry{}, fmt.Errorf("%w: snapshot entry relative path is required", ErrInvalidArgument)
	}
	if _, err := normalizeSnapshotRelativePath(entry.RelativePath); err != nil {
		return SnapshotEntry{}, err
	}
	if normalizeSnapshotProvenance(entry.Provenance) == "" {
		return SnapshotEntry{}, fmt.Errorf("%w: snapshot entry provenance %q is invalid", ErrInvalidArgument, entry.Provenance)
	}
	entry.Provenance = normalizeSnapshotProvenance(entry.Provenance)
	entry.Origin = entry.Provenance
	entry.DeliveryPolicy = normalizeSnapshotDeliveryPolicy(firstNonEmptyPolicy(entry.DeliveryPolicy, defaultPolicy, boolToPolicy(entry.ContextOnly)))
	if entry.DeliveryPolicy == "" {
		return SnapshotEntry{}, fmt.Errorf("%w: snapshot entry delivery policy is invalid", ErrInvalidArgument)
	}
	entry.ContextOnly = entry.DeliveryPolicy == SnapshotContextOnly
	if entry.Kind != SnapshotEntryFile && entry.Kind != SnapshotEntryDeleted {
		return SnapshotEntry{}, fmt.Errorf("%w: snapshot entry kind %q is invalid", ErrInvalidArgument, entry.Kind)
	}
	entry.RelativePath = filepath.ToSlash(filepath.Clean(filepath.FromSlash(entry.RelativePath)))
	entry.BlobSHA256 = firstNonEmpty(entry.BlobSHA256, entry.ContentSHA256)
	entry.ContentSHA256 = entry.BlobSHA256
	entry.ObjectPath = filepath.ToSlash(filepath.Clean(filepath.FromSlash(entry.ObjectPath)))
	if entry.Kind == SnapshotEntryDeleted {
		if entry.BlobSHA256 != "" || entry.ObjectPath != "" || entry.SizeBytes != 0 {
			return SnapshotEntry{}, fmt.Errorf("%w: deleted snapshot entry must not carry object content", ErrInvalidArgument)
		}
		return entry, nil
	}
	if !validSHA256(entry.BlobSHA256) {
		return SnapshotEntry{}, fmt.Errorf("%w: snapshot entry blob digest must be a lowercase sha256 digest", ErrInvalidArgument)
	}
	if strings.TrimSpace(entry.ObjectPath) == "" {
		return SnapshotEntry{}, fmt.Errorf("%w: snapshot entry object path is required", ErrInvalidArgument)
	}
	if entry.SizeBytes < 0 || entry.FileMode < 0 {
		return SnapshotEntry{}, fmt.Errorf("%w: snapshot entry mode and size must be non-negative", ErrInvalidArgument)
	}
	return entry, nil
}

func normalizeSnapshotDeliveryPolicy(policy SnapshotDeliveryPolicy) SnapshotDeliveryPolicy {
	switch policy {
	case "", SnapshotContextOnly:
		return SnapshotContextOnly
	case SnapshotRestorable:
		return SnapshotRestorable
	default:
		return ""
	}
}

func normalizeSnapshotProvenance(provenance SnapshotProvenance) SnapshotProvenance {
	switch provenance {
	case SnapshotProvenanceStaged:
		return SnapshotProvenanceStaged
	case SnapshotProvenanceUnstaged:
		return SnapshotProvenanceUnstaged
	case SnapshotProvenanceUntracked:
		return SnapshotProvenanceUntracked
	default:
		return ""
	}
}

func (store *Store) ensureSnapshotSchema(ctx context.Context) error {
	if _, err := store.db.ExecContext(ctx, snapshotSchemaSQL); err != nil {
		return fmt.Errorf("ensure snapshot schema: %w", err)
	}
	return nil
}

func readSnapshotByID(ctx context.Context, querier interface {
	QueryRowContext(context.Context, string, ...any) *sql.Row
}, snapshotID string) (Snapshot, error) {
	return readSnapshotRow(ctx, querier, `
		SELECT snapshot_id, run_id, attempt_id, workspace_id, workspace_generation,
		       target_ref, source_root, workspace_root, repo_common_dir, private_ref,
		       base_commit, base_tree, overlay_manifest_sha256, input_manifest_sha256,
		       default_delivery_policy, entry_count, created_at_ms, updated_at_ms
		FROM snapshots
		WHERE snapshot_id = ?
	`, snapshotID, fmt.Sprintf("snapshot %q", snapshotID))
}

func readSnapshotByRunID(ctx context.Context, querier interface {
	QueryRowContext(context.Context, string, ...any) *sql.Row
}, runID string) (Snapshot, error) {
	return readSnapshotRow(ctx, querier, `
		SELECT snapshot_id, run_id, attempt_id, workspace_id, workspace_generation,
		       target_ref, source_root, workspace_root, repo_common_dir, private_ref,
		       base_commit, base_tree, overlay_manifest_sha256, input_manifest_sha256,
		       default_delivery_policy, entry_count, created_at_ms, updated_at_ms
		FROM snapshots
		WHERE run_id = ?
	`, runID, fmt.Sprintf("run %q snapshot", runID))
}

func readSnapshotRow(ctx context.Context, querier interface {
	QueryRowContext(context.Context, string, ...any) *sql.Row
}, query string, arg any, subject string) (Snapshot, error) {
	row := querier.QueryRowContext(ctx, query, arg)
	var snapshot Snapshot
	if err := row.Scan(
		&snapshot.SnapshotID,
		&snapshot.RunID,
		&snapshot.AttemptID,
		&snapshot.WorkspaceID,
		&snapshot.WorkspaceGeneration,
		&snapshot.TargetRef,
		&snapshot.SourceRoot,
		&snapshot.WorkspaceRoot,
		&snapshot.RepoCommonDir,
		&snapshot.PrivateRef,
		&snapshot.BaseCommit,
		&snapshot.BaseTree,
		&snapshot.OverlayManifestSHA256,
		&snapshot.InputManifestSHA256,
		&snapshot.Scope,
		&snapshot.EntryCount,
		&snapshot.CreatedAtMS,
		&snapshot.UpdatedAtMS,
	); err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			return Snapshot{}, fmt.Errorf("%w: %s", ErrNotFound, subject)
		}
		return Snapshot{}, fmt.Errorf("read %s: %w", subject, err)
	}
	snapshot.ScanDigest = firstNonEmpty(snapshot.ScanDigest, snapshot.OverlayManifestSHA256)
	return snapshot, nil
}

func captureAmbientSnapshotFromSource(
	ctx context.Context,
	repository Repository,
	workspace Workspace,
	params CaptureSnapshotParams,
) (CreateSnapshotParams, error) {
	scope := normalizeSnapshotDeliveryPolicy(params.Scope)
	if strings.TrimSpace(params.SnapshotID) == "" ||
		strings.TrimSpace(params.RunID) == "" ||
		strings.TrimSpace(params.AttemptID) == "" ||
		strings.TrimSpace(params.TargetRef) == "" {
		return CreateSnapshotParams{}, fmt.Errorf("%w: snapshot id, run id, attempt id, and target ref are required", ErrInvalidArgument)
	}
	canonical, err := canonicalAllocationRepository(ctx, repository)
	if err != nil {
		return CreateSnapshotParams{}, err
	}
	if err := validateSnapshotWorkspaceBinding(ctx, canonical, workspace); err != nil {
		return CreateSnapshotParams{}, err
	}
	sourceRoot, actualSource, err := validateSnapshotSourceBinding(ctx, canonical, params.SourceRoot)
	if err != nil {
		return CreateSnapshotParams{}, err
	}
	baseCommit, err := runGitOutput(ctx, sourceRoot, "rev-parse", "HEAD")
	if err != nil {
		return CreateSnapshotParams{}, fmt.Errorf("resolve source HEAD for snapshot: %w", err)
	}
	if baseCommit != workspace.BaseCommit {
		return CreateSnapshotParams{}, fmt.Errorf(
			"%w: source HEAD %s differs from target base %s",
			ErrSnapshotApplyConflict,
			baseCommit,
			workspace.BaseCommit,
		)
	}
	baseTree, err := runGitOutput(ctx, sourceRoot, "rev-parse", workspace.BaseCommit+"^{tree}")
	if err != nil {
		return CreateSnapshotParams{}, fmt.Errorf("resolve source tree for snapshot: %w", err)
	}

	firstManifest, err := ambientStatusManifest(ctx, sourceRoot)
	if err != nil {
		return CreateSnapshotParams{}, err
	}
	entries, err := captureAmbientEntries(ctx, canonical, params.SnapshotID, sourceRoot, scope)
	if err != nil {
		return CreateSnapshotParams{}, err
	}
	secondManifest, err := ambientStatusManifest(ctx, sourceRoot)
	if err != nil {
		return CreateSnapshotParams{}, err
	}
	if firstManifest != secondManifest {
		return CreateSnapshotParams{}, fmt.Errorf("%w: source ambient state changed during capture", ErrSnapshotDrift)
	}

	overlayDigest := digestAmbientEntries(entries)
	inputDigest := digestSnapshotInputManifest(
		params.RunID,
		params.AttemptID,
		params.TargetRef,
		sourceRoot,
		workspace,
		baseCommit,
		baseTree,
		overlayDigest,
		firstManifest,
	)
	return CreateSnapshotParams{
		SnapshotID:            params.SnapshotID,
		RunID:                 params.RunID,
		AttemptID:             params.AttemptID,
		WorkspaceID:           workspace.WorkspaceID,
		WorkspaceGeneration:   workspace.Generation,
		TargetRef:             params.TargetRef,
		SourceRoot:            sourceRoot,
		WorkspaceRoot:         workspace.RootPath,
		RepoCommonDir:         actualSource.CommonDir,
		PrivateRef:            workspace.PrivateRef,
		BaseCommit:            baseCommit,
		BaseTree:              baseTree,
		OverlayManifestSHA256: overlayDigest,
		InputManifestSHA256:   inputDigest,
		Scope:                 scope,
		ScanDigest:            overlayDigest,
		Entries:               entries,
	}, nil
}

func validateSnapshotWorkspaceBinding(ctx context.Context, repository Repository, workspace Workspace) error {
	if workspace.WorkspaceID == "" || workspace.RunID == "" || workspace.Generation <= 0 {
		return fmt.Errorf("%w: workspace binding is incomplete", ErrWorkspaceBinding)
	}
	if !sameFilesystemPath(workspace.RepoCommonDir, repository.CommonDir) {
		return fmt.Errorf("%w: workspace common directory changed", ErrWorkspaceBinding)
	}
	isPrimary := workspaceIsPrimary(workspace, repository)
	if !isPrimary {
		if err := validateOwnedWorkspacePath(repository.CommonDir, workspace.RootPath); err != nil {
			return fmt.Errorf("%w: %v", ErrWorkspaceBinding, err)
		}
	}
	actual, err := ResolveRepository(ctx, workspace.RootPath)
	if err != nil {
		return fmt.Errorf("%w: workspace root is not the recorded Git worktree", ErrWorkspaceBinding)
	}
	if !sameFilesystemPath(actual.Root, workspace.RootPath) ||
		!sameFilesystemPath(actual.CommonDir, workspace.RepoCommonDir) {
		return fmt.Errorf("%w: workspace repository metadata changed", ErrWorkspaceBinding)
	}
	branch, err := runGitOutput(ctx, workspace.RootPath, "symbolic-ref", "HEAD")
	if err != nil || branch != workspace.PrivateRef {
		return fmt.Errorf("%w: workspace HEAD is not private ref %q", ErrWorkspaceBinding, workspace.PrivateRef)
	}
	if isPrimary {
		if !sameFilesystemPath(workspace.RootPath, repository.Root) ||
			workspace.PrivateRef != workspace.BaseRef {
			return fmt.Errorf("%w: primary workspace binding does not match canonical root/base ref", ErrWorkspaceBinding)
		}
		currentBase, err := resolveGitCommit(ctx, repository.Root, workspace.BaseRef)
		if err != nil || currentBase != workspace.BaseCommit {
			return fmt.Errorf("%w: primary target ref %q no longer matches base commit %q", ErrWorkspaceBinding, workspace.BaseRef, workspace.BaseCommit)
		}
	}
	return nil
}

func validateSnapshotSourceBinding(ctx context.Context, repository Repository, sourceRoot string) (string, Repository, error) {
	if strings.TrimSpace(sourceRoot) == "" {
		return "", Repository{}, fmt.Errorf("%w: source root is required", ErrInvalidArgument)
	}
	actual, err := ResolveRepository(ctx, sourceRoot)
	if err != nil {
		return "", Repository{}, fmt.Errorf("%w: source root is not a Git worktree", ErrWorkspaceBinding)
	}
	if !sameFilesystemPath(actual.CommonDir, repository.CommonDir) {
		return "", Repository{}, fmt.Errorf("%w: source root is outside the recorded repository", ErrWorkspaceBinding)
	}
	return filepath.Clean(actual.Root), actual, nil
}

func ambientStatusManifest(ctx context.Context, directory string) (string, error) {
	stagedChanged, err := listGitPaths(ctx, directory, "diff", "--cached", "--name-only", "-z", "--diff-filter=ACMR")
	if err != nil {
		return "", err
	}
	stagedDeleted, err := listGitPaths(ctx, directory, "diff", "--cached", "--name-only", "-z", "--diff-filter=D")
	if err != nil {
		return "", err
	}
	unstagedChanged, err := listGitPaths(ctx, directory, "diff", "--name-only", "-z", "--diff-filter=ACMR")
	if err != nil {
		return "", err
	}
	unstagedDeleted, err := listGitPaths(ctx, directory, "diff", "--name-only", "-z", "--diff-filter=D")
	if err != nil {
		return "", err
	}
	untracked, err := listGitPaths(ctx, directory, "ls-files", "--others", "--exclude-standard", "-z")
	if err != nil {
		return "", err
	}
	lines := make([]string, 0, len(stagedChanged)+len(stagedDeleted)+len(unstagedChanged)+len(unstagedDeleted)+len(untracked))
	for _, path := range stagedChanged {
		lines = append(lines, "staged:file:"+path)
	}
	for _, path := range stagedDeleted {
		lines = append(lines, "staged:deleted:"+path)
	}
	for _, path := range unstagedChanged {
		lines = append(lines, "unstaged:file:"+path)
	}
	for _, path := range unstagedDeleted {
		lines = append(lines, "unstaged:deleted:"+path)
	}
	for _, path := range untracked {
		lines = append(lines, "untracked:file:"+path)
	}
	sort.Strings(lines)
	return strings.Join(lines, "\n"), nil
}

func captureAmbientEntries(ctx context.Context, repository Repository, snapshotID, sourceRoot string, scope SnapshotDeliveryPolicy) ([]SnapshotEntry, error) {
	stagedChanged, err := listGitPaths(ctx, sourceRoot, "diff", "--cached", "--name-only", "-z", "--diff-filter=ACMR")
	if err != nil {
		return nil, err
	}
	stagedDeleted, err := listGitPaths(ctx, sourceRoot, "diff", "--cached", "--name-only", "-z", "--diff-filter=D")
	if err != nil {
		return nil, err
	}
	unstagedChanged, err := listGitPaths(ctx, sourceRoot, "diff", "--name-only", "-z", "--diff-filter=ACMR")
	if err != nil {
		return nil, err
	}
	unstagedDeleted, err := listGitPaths(ctx, sourceRoot, "diff", "--name-only", "-z", "--diff-filter=D")
	if err != nil {
		return nil, err
	}
	untracked, err := listGitPaths(ctx, sourceRoot, "ls-files", "--others", "--exclude-standard", "-z")
	if err != nil {
		return nil, err
	}
	entries := make([]SnapshotEntry, 0, len(stagedChanged)+len(stagedDeleted)+len(unstagedChanged)+len(unstagedDeleted)+len(untracked))
	appendFileEntry := func(provenance SnapshotProvenance, relativePath string, bytes []byte, mode int64) error {
		if err := blockSecretCandidate(relativePath, bytes); err != nil {
			return err
		}
		digest := sha256.Sum256(bytes)
		objectRel, err := storeSnapshotObject(repository.CommonDir, digest[:], bytes)
		if err != nil {
			return err
		}
		entries = append(entries, hydrateSnapshotEntryCompatibility(SnapshotEntry{
			EntryID:        snapshotEntryID(snapshotID, provenance, relativePath),
			RelativePath:   relativePath,
			Provenance:     provenance,
			DeliveryPolicy: scope,
			Kind:           SnapshotEntryFile,
			FileMode:       mode,
			BlobSHA256:     hex.EncodeToString(digest[:]),
			ObjectPath:     objectRel,
			SizeBytes:      int64(len(bytes)),
		}))
		return nil
	}
	appendDeletedEntry := func(provenance SnapshotProvenance, relativePath string) {
		entries = append(entries, hydrateSnapshotEntryCompatibility(SnapshotEntry{
			EntryID:        snapshotEntryID(snapshotID, provenance, relativePath),
			RelativePath:   relativePath,
			Provenance:     provenance,
			DeliveryPolicy: scope,
			Kind:           SnapshotEntryDeleted,
		}))
	}

	for _, relativePath := range stagedChanged {
		bytes, mode, err := readStagedFileContent(ctx, sourceRoot, relativePath)
		if err != nil {
			return nil, err
		}
		if err := appendFileEntry(SnapshotProvenanceStaged, relativePath, bytes, mode); err != nil {
			return nil, err
		}
	}
	for _, relativePath := range stagedDeleted {
		appendDeletedEntry(SnapshotProvenanceStaged, relativePath)
	}
	for _, relativePath := range unstagedChanged {
		bytes, mode, err := readWorkspaceFileContent(sourceRoot, relativePath)
		if err != nil {
			return nil, err
		}
		if err := appendFileEntry(SnapshotProvenanceUnstaged, relativePath, bytes, mode); err != nil {
			return nil, err
		}
	}
	for _, relativePath := range unstagedDeleted {
		appendDeletedEntry(SnapshotProvenanceUnstaged, relativePath)
	}
	for _, relativePath := range untracked {
		bytes, mode, err := readWorkspaceFileContent(sourceRoot, relativePath)
		if err != nil {
			return nil, err
		}
		if err := appendFileEntry(SnapshotProvenanceUntracked, relativePath, bytes, mode); err != nil {
			return nil, err
		}
	}

	sort.Slice(entries, func(i, j int) bool {
		if entries[i].RelativePath == entries[j].RelativePath {
			return entries[i].Provenance < entries[j].Provenance
		}
		return entries[i].RelativePath < entries[j].RelativePath
	})
	for index := range entries {
		entries[index].Ordinal = int64(index + 1)
	}
	return entries, nil
}

func listGitPaths(ctx context.Context, directory string, arguments ...string) ([]string, error) {
	output, err := runGitStdoutBytes(ctx, directory, arguments...)
	if err != nil {
		return nil, err
	}
	if len(output) == 0 {
		return nil, nil
	}
	parts := strings.Split(string(output), "\x00")
	paths := make([]string, 0, len(parts))
	seen := make(map[string]struct{}, len(parts))
	for _, part := range parts {
		if strings.TrimSpace(part) == "" {
			continue
		}
		relativePath, err := normalizeSnapshotRelativePath(part)
		if err != nil {
			return nil, err
		}
		if isRuntimeOwnedAmbientPath(relativePath) {
			continue
		}
		if _, exists := seen[relativePath]; exists {
			continue
		}
		seen[relativePath] = struct{}{}
		paths = append(paths, relativePath)
	}
	sort.Strings(paths)
	return paths, nil
}

func isRuntimeOwnedAmbientPath(relativePath string) bool {
	path := strings.TrimPrefix(filepath.ToSlash(relativePath), "./")
	return strings.HasPrefix(path, ".worktrees/specify-runs/") ||
		strings.HasPrefix(path, ".worktrees/specify-candidates/") ||
		strings.HasPrefix(path, ".specify/runtime/")
}

func normalizeSnapshotRelativePath(value string) (string, error) {
	path := filepath.ToSlash(filepath.Clean(filepath.FromSlash(strings.TrimSpace(value))))
	if path == "." || path == "" || strings.HasPrefix(path, "../") || strings.Contains(path, "/../") || filepath.IsAbs(path) {
		return "", fmt.Errorf("%w: snapshot path %q escapes the workspace", ErrWorkspaceEscape, value)
	}
	return path, nil
}

func resolveSnapshotTargetPath(workspaceRoot, relativePath string) (string, error) {
	normalized, err := normalizeSnapshotRelativePath(relativePath)
	if err != nil {
		return "", err
	}
	target := filepath.Join(workspaceRoot, filepath.FromSlash(normalized))
	resolvedRoot, err := resolveThroughExistingAncestor(workspaceRoot)
	if err != nil {
		return "", err
	}
	resolvedTarget, err := resolveThroughExistingAncestor(target)
	if err != nil {
		return "", err
	}
	if !isContainedPath(resolvedRoot, resolvedTarget) && !sameFilesystemPath(resolvedRoot, resolvedTarget) {
		return "", fmt.Errorf("%w: snapshot target %q escapes workspace %q", ErrSnapshotApplyConflict, relativePath, workspaceRoot)
	}
	return target, nil
}

func readStagedFileContent(ctx context.Context, directory, relativePath string) ([]byte, int64, error) {
	mode, err := readStagedIndexMode(ctx, directory, relativePath)
	if err != nil {
		return nil, 0, err
	}
	output, err := runGitShowBytes(ctx, directory, ":"+relativePath)
	if err != nil {
		return nil, 0, err
	}
	return output, mode, nil
}

func readStagedIndexMode(ctx context.Context, directory, relativePath string) (int64, error) {
	output, err := runGitOutput(ctx, directory, "ls-files", "-s", "--", relativePath)
	if err != nil {
		return 0, err
	}
	if output == "" {
		return 0, fmt.Errorf("%w: staged path %q is missing from the index", ErrWorkspaceBinding, relativePath)
	}
	fields := strings.Fields(output)
	if len(fields) < 4 {
		return 0, fmt.Errorf("%w: staged metadata for %q is invalid", ErrWorkspaceBinding, relativePath)
	}
	mode, err := strconv.ParseInt(fields[0], 8, 64)
	if err != nil {
		return 0, fmt.Errorf("parse staged mode for %q: %w", relativePath, err)
	}
	return mode, nil
}

func runGitShowBytes(ctx context.Context, directory, revision string) ([]byte, error) {
	command := execCommandContext(ctx, "git", "show", "--no-textconv", revision)
	command.Dir = directory
	output, err := command.Output()
	if err != nil {
		if contextErr := ctx.Err(); contextErr != nil {
			return nil, contextErr
		}
		return nil, fmt.Errorf("git show %s failed: %w", revision, err)
	}
	return output, nil
}

func runGitStdoutBytes(ctx context.Context, directory string, arguments ...string) ([]byte, error) {
	command := execCommandContext(ctx, "git", arguments...)
	command.Dir = directory
	output, err := command.Output()
	if err != nil {
		if contextErr := ctx.Err(); contextErr != nil {
			return nil, contextErr
		}
		return nil, fmt.Errorf("git %s failed: %w", strings.Join(arguments, " "), err)
	}
	return output, nil
}

func readWorkspaceFileContent(workspaceRoot, relativePath string) ([]byte, int64, error) {
	targetPath, err := resolveSnapshotTargetPath(workspaceRoot, relativePath)
	if err != nil {
		return nil, 0, err
	}
	info, err := os.Lstat(targetPath)
	if err != nil {
		return nil, 0, err
	}
	if info.Mode()&os.ModeSymlink != 0 {
		return nil, 0, fmt.Errorf("%w: snapshot capture blocks symlink path %q", ErrWorkspaceEscape, relativePath)
	}
	if !info.Mode().IsRegular() {
		return nil, 0, fmt.Errorf("%w: snapshot capture requires regular files, got %q", ErrInvalidArgument, relativePath)
	}
	bytes, err := os.ReadFile(targetPath)
	if err != nil {
		return nil, 0, err
	}
	return bytes, int64(info.Mode().Perm()), nil
}

func storeSnapshotObject(commonDir string, digest []byte, bytes []byte) (string, error) {
	encoded := hex.EncodeToString(digest)
	objectRelative := filepath.ToSlash(filepath.Join("specify-runtime", "snapshot-objects", "sha256", encoded[:2], encoded[2:]))
	objectPath := filepath.Join(commonDir, filepath.FromSlash(objectRelative))
	if err := safeMkdirAllWithin(commonDir, filepath.Dir(objectPath)); err != nil {
		return "", err
	}
	if existing, err := os.ReadFile(objectPath); err == nil {
		if sha256.Sum256(existing) == sha256.Sum256(bytes) {
			return objectRelative, nil
		}
		return "", fmt.Errorf("%w: object path %q already exists with different bytes", ErrAlreadyExists, objectRelative)
	} else if !errors.Is(err, os.ErrNotExist) {
		return "", err
	}
	tempFile, err := os.CreateTemp(filepath.Dir(objectPath), "object-*.tmp")
	if err != nil {
		return "", err
	}
	tempPath := tempFile.Name()
	defer func() { _ = os.Remove(tempPath) }()
	if _, err := tempFile.Write(bytes); err != nil {
		_ = tempFile.Close()
		return "", err
	}
	if err := tempFile.Close(); err != nil {
		return "", err
	}
	if err := os.Rename(tempPath, objectPath); err != nil && !errors.Is(err, os.ErrExist) {
		if existing, readErr := os.ReadFile(objectPath); readErr == nil && sha256.Sum256(existing) == sha256.Sum256(bytes) {
			return objectRelative, nil
		}
		return "", err
	}
	return objectRelative, nil
}

func readSnapshotObjectBytes(commonDir string, entry SnapshotEntry) ([]byte, error) {
	objectPath := filepath.Join(commonDir, filepath.FromSlash(filepath.Clean(filepath.FromSlash(entry.ObjectPath))))
	resolvedCommon, err := resolveThroughExistingAncestor(commonDir)
	if err != nil {
		return nil, err
	}
	resolvedObject, err := resolveThroughExistingAncestor(objectPath)
	if err != nil {
		return nil, err
	}
	if !isContainedPath(resolvedCommon, resolvedObject) && !sameFilesystemPath(resolvedCommon, resolvedObject) {
		return nil, fmt.Errorf("%w: snapshot object %q escapes common dir", ErrSnapshotApplyConflict, entry.ObjectPath)
	}
	bytes, err := os.ReadFile(objectPath)
	if err != nil {
		return nil, err
	}
	if digest := sha256.Sum256(bytes); hex.EncodeToString(digest[:]) != entry.BlobSHA256 {
		return nil, fmt.Errorf("%w: snapshot object %q digest mismatch", ErrWorkspaceBinding, entry.ObjectPath)
	}
	return bytes, nil
}

func writeSnapshotTarget(targetPath, workspaceRoot string, bytes []byte, mode fs.FileMode) error {
	if err := safeMkdirAllWithin(workspaceRoot, filepath.Dir(targetPath)); err != nil {
		return err
	}
	if existing, err := os.ReadFile(targetPath); err == nil {
		if sha256.Sum256(existing) == sha256.Sum256(bytes) {
			return os.Chmod(targetPath, mode.Perm())
		}
	} else if !errors.Is(err, os.ErrNotExist) {
		return err
	}
	tempFile, err := os.CreateTemp(filepath.Dir(targetPath), "snapshot-apply-*.tmp")
	if err != nil {
		return err
	}
	tempPath := tempFile.Name()
	defer func() { _ = os.Remove(tempPath) }()
	if _, err := tempFile.Write(bytes); err != nil {
		_ = tempFile.Close()
		return err
	}
	if err := tempFile.Chmod(mode.Perm()); err != nil {
		_ = tempFile.Close()
		return err
	}
	if err := tempFile.Close(); err != nil {
		return err
	}
	return os.Rename(tempPath, targetPath)
}

func removeSnapshotTarget(targetPath, workspaceRoot string) error {
	resolvedRoot, err := resolveThroughExistingAncestor(workspaceRoot)
	if err != nil {
		return err
	}
	resolvedTarget, err := resolveThroughExistingAncestor(targetPath)
	if err != nil {
		if errors.Is(err, os.ErrNotExist) {
			return nil
		}
		return err
	}
	if !isContainedPath(resolvedRoot, resolvedTarget) && !sameFilesystemPath(resolvedRoot, resolvedTarget) {
		return fmt.Errorf("%w: snapshot delete target %q escapes workspace", ErrSnapshotApplyConflict, targetPath)
	}
	if err := os.Remove(targetPath); err != nil && !errors.Is(err, os.ErrNotExist) {
		return err
	}
	return nil
}

func safeMkdirAllWithin(root, target string) error {
	if !filepath.IsAbs(root) || !filepath.IsAbs(target) {
		return fmt.Errorf("%w: mkdir root and target must be absolute", ErrSnapshotApplyConflict)
	}
	resolvedRoot, err := resolveThroughExistingAncestor(root)
	if err != nil {
		return err
	}
	current := filepath.Clean(root)
	relative, err := filepath.Rel(current, filepath.Clean(target))
	if err != nil {
		return err
	}
	if relative == "." {
		return nil
	}
	for _, segment := range strings.Split(relative, string(filepath.Separator)) {
		if segment == "" || segment == "." || segment == ".." {
			return fmt.Errorf("%w: unsafe parent segment %q", ErrSnapshotApplyConflict, segment)
		}
		current = filepath.Join(current, segment)
		info, statErr := os.Lstat(current)
		if errors.Is(statErr, os.ErrNotExist) {
			if err := os.Mkdir(current, 0o755); err != nil && !errors.Is(err, os.ErrExist) {
				return err
			}
			info, statErr = os.Lstat(current)
		}
		if statErr != nil {
			return statErr
		}
		if info.Mode()&os.ModeSymlink != 0 || !info.IsDir() {
			return fmt.Errorf("%w: target parent %q is not a real directory", ErrSnapshotApplyConflict, current)
		}
		resolvedCurrent, err := resolveThroughExistingAncestor(current)
		if err != nil {
			return err
		}
		if !isContainedPath(resolvedRoot, resolvedCurrent) && !sameFilesystemPath(resolvedRoot, resolvedCurrent) {
			return fmt.Errorf("%w: target parent %q escapes root %q", ErrSnapshotApplyConflict, current, root)
		}
	}
	return nil
}

func digestAmbientEntries(entries []SnapshotEntry) string {
	lines := make([]string, 0, len(entries))
	for _, raw := range entries {
		entry := hydrateSnapshotEntryCompatibility(raw)
		lines = append(lines, strings.Join([]string{
			string(entry.Provenance),
			string(entry.Kind),
			entry.RelativePath,
			strconv.FormatInt(entry.FileMode, 10),
			entry.BlobSHA256,
			strconv.FormatInt(entry.SizeBytes, 10),
			string(entry.DeliveryPolicy),
		}, "\x00"))
	}
	sort.Strings(lines)
	digest := sha256.Sum256([]byte(strings.Join(lines, "\n")))
	return hex.EncodeToString(digest[:])
}

func digestSnapshotInputManifest(
	runID string,
	attemptID string,
	targetRef string,
	sourceRoot string,
	workspace Workspace,
	baseCommit string,
	baseTree string,
	overlayDigest string,
	statusManifest string,
) string {
	lines := []string{
		"run_id=" + strings.TrimSpace(runID),
		"attempt_id=" + strings.TrimSpace(attemptID),
		"target_ref=" + strings.TrimSpace(targetRef),
		"source_root=" + filepath.Clean(sourceRoot),
		"workspace_id=" + strings.TrimSpace(workspace.WorkspaceID),
		"workspace_generation=" + strconv.FormatInt(workspace.Generation, 10),
		"workspace_root=" + filepath.Clean(workspace.RootPath),
		"repo_common_dir=" + filepath.Clean(workspace.RepoCommonDir),
		"private_ref=" + strings.TrimSpace(workspace.PrivateRef),
		"base_commit=" + strings.TrimSpace(baseCommit),
		"base_tree=" + strings.TrimSpace(baseTree),
		"overlay_manifest_sha256=" + strings.TrimSpace(overlayDigest),
		"source_status_manifest=" + statusManifest,
	}
	digest := sha256.Sum256([]byte(strings.Join(lines, "\n")))
	return hex.EncodeToString(digest[:])
}

func snapshotEntryID(snapshotID string, provenance SnapshotProvenance, relativePath string) string {
	digest := sha256.Sum256([]byte(snapshotID + "\x00" + string(provenance) + "\x00" + relativePath))
	return "snapshot-entry-" + hex.EncodeToString(digest[:10])
}

var secretPathPattern = regexp.MustCompile(`(?i)(^|/)(\.env(\.|$)?|id_(rsa|dsa|ecdsa|ed25519)|.*\.(pem|p12|pfx|key)|.*(secret|token|credential|passwd).*)`)

var secretContentPattern = regexp.MustCompile(`(?m)(-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----|AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{20,}|xox[baprs]-[A-Za-z0-9-]{10,}|sk-[A-Za-z0-9]{16,})`)

func blockSecretCandidate(relativePath string, bytes []byte) error {
	if secretPathPattern.MatchString(filepath.ToSlash(relativePath)) || secretContentPattern.Match(bytes) {
		return fmt.Errorf("%w: %s", ErrSnapshotSecretCandidate, relativePath)
	}
	return nil
}

func hydrateSnapshotEntryCompatibility(entry SnapshotEntry) SnapshotEntry {
	if entry.Provenance == "" {
		entry.Provenance = entry.Origin
	}
	entry.Origin = entry.Provenance
	if entry.DeliveryPolicy == "" {
		entry.DeliveryPolicy = boolToPolicy(entry.ContextOnly)
	}
	entry.DeliveryPolicy = normalizeSnapshotDeliveryPolicy(entry.DeliveryPolicy)
	entry.ContextOnly = entry.DeliveryPolicy == SnapshotContextOnly
	if entry.BlobSHA256 == "" {
		entry.BlobSHA256 = entry.ContentSHA256
	}
	entry.ContentSHA256 = entry.BlobSHA256
	return entry
}

func firstNonEmpty(values ...string) string {
	for _, value := range values {
		if strings.TrimSpace(value) != "" {
			return value
		}
	}
	return ""
}

func firstNonEmptyPolicy(values ...SnapshotDeliveryPolicy) SnapshotDeliveryPolicy {
	for _, value := range values {
		if value != "" {
			return value
		}
	}
	return ""
}

func boolToInt(value bool) int {
	if value {
		return 1
	}
	return 0
}

func boolToPolicy(value bool) SnapshotDeliveryPolicy {
	if value {
		return SnapshotContextOnly
	}
	return SnapshotRestorable
}

var execCommandContext = func(ctx context.Context, name string, args ...string) *exec.Cmd {
	return exec.CommandContext(ctx, name, args...)
}
