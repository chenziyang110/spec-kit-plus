package runcontrol

import (
	"context"
	"database/sql"
	"encoding/json"
	"errors"
	"fmt"
	"path/filepath"
	"sort"
	"strings"
	"time"
)

type AdapterLaunchMode string

const (
	AdapterLaunchManaged    AdapterLaunchMode = "managed"
	AdapterLaunchAttach     AdapterLaunchMode = "manual_attach"
	AdapterLaunchPromptOnly AdapterLaunchMode = "prompt_only"
)

type AdapterCapability struct {
	AdapterID                string
	LaunchMode               AdapterLaunchMode
	EnforcesCWD              bool
	EnforcesWorkspaceRoot    bool
	EnforcesWritableRoots    bool
	ControlsProcessTree      bool
	SupportsHeartbeat        bool
	SupportsCancellation     bool
	SupportsStructuredResult bool
	CapabilityDigest         string
	CreatedAtMS              int64
}

type WorkspaceAttestation struct {
	AttestationID         string
	WorkspaceID           string
	RunID                 string
	WorkspaceGeneration   int64
	CanonicalRoot         string
	RepoCommonDir         string
	GitAdminDir           string
	BaseRef               string
	BaseCommitOID         string
	PrivateRef            string
	SnapshotID            string
	OverlayManifestSHA256 string
	WritableRootsJSON     string
	AttestationDigest     string
	CreatedAtMS           int64
}

const adapterAttestationSchemaSQL = `
CREATE TABLE IF NOT EXISTS adapter_capabilities (
    adapter_id TEXT PRIMARY KEY,
    launch_mode TEXT NOT NULL CHECK (launch_mode IN ('managed', 'manual_attach', 'prompt_only')),
    enforces_cwd INTEGER NOT NULL CHECK (enforces_cwd IN (0, 1)),
    enforces_workspace_root INTEGER NOT NULL CHECK (enforces_workspace_root IN (0, 1)),
    enforces_writable_roots INTEGER NOT NULL CHECK (enforces_writable_roots IN (0, 1)),
    controls_process_tree INTEGER NOT NULL CHECK (controls_process_tree IN (0, 1)),
    supports_heartbeat INTEGER NOT NULL CHECK (supports_heartbeat IN (0, 1)),
    supports_cancellation INTEGER NOT NULL CHECK (supports_cancellation IN (0, 1)),
    supports_structured_result INTEGER NOT NULL CHECK (supports_structured_result IN (0, 1)),
    capability_digest TEXT NOT NULL UNIQUE CHECK (
        length(capability_digest) = 64 AND capability_digest NOT GLOB '*[^0-9a-f]*'
    ),
    created_at_ms INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS workspace_attestations (
    attestation_id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL UNIQUE REFERENCES workspaces(workspace_id) ON DELETE RESTRICT,
    run_id TEXT NOT NULL REFERENCES runs(run_id) ON DELETE RESTRICT,
    workspace_generation INTEGER NOT NULL CHECK (workspace_generation > 0),
    canonical_root TEXT NOT NULL,
    repo_common_dir TEXT NOT NULL,
    git_admin_dir TEXT NOT NULL,
    base_ref TEXT NOT NULL,
    base_commit_oid TEXT NOT NULL,
    private_ref TEXT NOT NULL,
    snapshot_id TEXT NOT NULL REFERENCES snapshots(snapshot_id) ON DELETE RESTRICT,
    overlay_manifest_sha256 TEXT NOT NULL,
    writable_roots_json TEXT NOT NULL,
    attestation_digest TEXT NOT NULL UNIQUE CHECK (
        length(attestation_digest) = 64 AND attestation_digest NOT GLOB '*[^0-9a-f]*'
    ),
    created_at_ms INTEGER NOT NULL
);
`

func (store *Store) ensureManagedAdapterCapability(ctx context.Context, adapterID string) (AdapterCapability, error) {
	if strings.TrimSpace(adapterID) == "" {
		return AdapterCapability{}, fmt.Errorf("%w: adapter id is required", ErrInvalidArgument)
	}
	capability := AdapterCapability{
		AdapterID: adapterID, LaunchMode: AdapterLaunchManaged,
		EnforcesCWD: true, EnforcesWorkspaceRoot: true, EnforcesWritableRoots: true,
		ControlsProcessTree: true, SupportsHeartbeat: true, SupportsCancellation: true,
		SupportsStructuredResult: true, CreatedAtMS: time.Now().UTC().UnixMilli(),
	}
	digest, err := digestCanonicalJSON(struct {
		AdapterID                string            `json:"adapter_id"`
		LaunchMode               AdapterLaunchMode `json:"launch_mode"`
		EnforcesCWD              bool              `json:"enforces_cwd"`
		EnforcesWorkspaceRoot    bool              `json:"enforces_workspace_root"`
		EnforcesWritableRoots    bool              `json:"enforces_writable_roots"`
		ControlsProcessTree      bool              `json:"controls_process_tree"`
		SupportsHeartbeat        bool              `json:"supports_heartbeat"`
		SupportsCancellation     bool              `json:"supports_cancellation"`
		SupportsStructuredResult bool              `json:"supports_structured_result"`
	}{
		capability.AdapterID, capability.LaunchMode, capability.EnforcesCWD,
		capability.EnforcesWorkspaceRoot, capability.EnforcesWritableRoots,
		capability.ControlsProcessTree, capability.SupportsHeartbeat,
		capability.SupportsCancellation, capability.SupportsStructuredResult,
	})
	if err != nil {
		return AdapterCapability{}, err
	}
	capability.CapabilityDigest = digest
	if _, err := store.db.ExecContext(ctx, `
		INSERT INTO adapter_capabilities (
			adapter_id, launch_mode, enforces_cwd, enforces_workspace_root,
			enforces_writable_roots, controls_process_tree, supports_heartbeat,
			supports_cancellation, supports_structured_result, capability_digest, created_at_ms
		) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
		ON CONFLICT(adapter_id) DO NOTHING
	`, capability.AdapterID, capability.LaunchMode, boolToInt(capability.EnforcesCWD),
		boolToInt(capability.EnforcesWorkspaceRoot), boolToInt(capability.EnforcesWritableRoots),
		boolToInt(capability.ControlsProcessTree), boolToInt(capability.SupportsHeartbeat),
		boolToInt(capability.SupportsCancellation), boolToInt(capability.SupportsStructuredResult),
		capability.CapabilityDigest, capability.CreatedAtMS); err != nil {
		return AdapterCapability{}, fmt.Errorf("record Adapter capability: %w", err)
	}
	stored, err := store.GetAdapterCapability(ctx, adapterID)
	if err != nil {
		return AdapterCapability{}, err
	}
	if stored.CapabilityDigest != capability.CapabilityDigest || stored.LaunchMode != AdapterLaunchManaged ||
		!stored.EnforcesCWD || !stored.EnforcesWorkspaceRoot || !stored.EnforcesWritableRoots ||
		!stored.ControlsProcessTree || !stored.SupportsHeartbeat || !stored.SupportsCancellation ||
		!stored.SupportsStructuredResult {
		return AdapterCapability{}, fmt.Errorf("%w: Adapter %q lacks enforced modifying capability", ErrWorkspaceBinding, adapterID)
	}
	return stored, nil
}

func (store *Store) GetAdapterCapability(ctx context.Context, adapterID string) (AdapterCapability, error) {
	if strings.TrimSpace(adapterID) == "" {
		return AdapterCapability{}, fmt.Errorf("%w: adapter id is required", ErrInvalidArgument)
	}
	var capability AdapterCapability
	var cwd, root, writable, processTree, heartbeat, cancellation, result int
	err := store.db.QueryRowContext(ctx, `
		SELECT adapter_id, launch_mode, enforces_cwd, enforces_workspace_root,
		       enforces_writable_roots, controls_process_tree, supports_heartbeat,
		       supports_cancellation, supports_structured_result, capability_digest, created_at_ms
		FROM adapter_capabilities WHERE adapter_id = ?
	`, adapterID).Scan(
		&capability.AdapterID, &capability.LaunchMode, &cwd, &root, &writable,
		&processTree, &heartbeat, &cancellation, &result,
		&capability.CapabilityDigest, &capability.CreatedAtMS,
	)
	if errors.Is(err, sql.ErrNoRows) {
		return AdapterCapability{}, fmt.Errorf("%w: Adapter capability %q", ErrNotFound, adapterID)
	}
	if err != nil {
		return AdapterCapability{}, err
	}
	capability.EnforcesCWD = cwd != 0
	capability.EnforcesWorkspaceRoot = root != 0
	capability.EnforcesWritableRoots = writable != 0
	capability.ControlsProcessTree = processTree != 0
	capability.SupportsHeartbeat = heartbeat != 0
	capability.SupportsCancellation = cancellation != 0
	capability.SupportsStructuredResult = result != 0
	return capability, nil
}

func (store *Store) CreateWorkspaceAttestation(
	ctx context.Context,
	repository Repository,
	run Run,
	workspace Workspace,
	snapshot Snapshot,
	writableRoots []string,
) (WorkspaceAttestation, error) {
	canonical, err := canonicalAllocationRepository(ctx, repository)
	if err != nil {
		return WorkspaceAttestation{}, err
	}
	if err := validateSnapshotWorkspaceBinding(ctx, canonical, workspace); err != nil {
		return WorkspaceAttestation{}, err
	}
	if snapshot.RunID != run.RunID || workspace.RunID != run.RunID ||
		snapshot.TargetRef != workspace.BaseRef || snapshot.BaseCommit != workspace.BaseCommit {
		return WorkspaceAttestation{}, fmt.Errorf("%w: Workspace Attestation bindings are inconsistent", ErrWorkspaceBinding)
	}
	adminOutput, err := runGitOutput(ctx, workspace.RootPath, "rev-parse", "--git-dir")
	if err != nil {
		return WorkspaceAttestation{}, err
	}
	gitAdminDir, err := resolveGitPath(workspace.RootPath, adminOutput)
	if err != nil {
		return WorkspaceAttestation{}, err
	}
	roots := make([]string, 0, len(writableRoots))
	for _, root := range writableRoots {
		absolute, err := filepath.Abs(root)
		if err != nil {
			return WorkspaceAttestation{}, err
		}
		roots = append(roots, filepath.Clean(absolute))
	}
	sort.Strings(roots)
	writableJSONBytes, err := json.Marshal(roots)
	if err != nil {
		return WorkspaceAttestation{}, err
	}
	digest, err := digestCanonicalJSON(struct {
		WorkspaceID           string   `json:"workspace_id"`
		RunID                 string   `json:"run_id"`
		WorkspaceGeneration   int64    `json:"workspace_generation"`
		CanonicalRoot         string   `json:"canonical_root"`
		RepoCommonDir         string   `json:"repo_common_dir"`
		GitAdminDir           string   `json:"git_admin_dir"`
		BaseRef               string   `json:"base_ref"`
		BaseCommitOID         string   `json:"base_commit_oid"`
		PrivateRef            string   `json:"private_ref"`
		SnapshotID            string   `json:"snapshot_id"`
		OverlayManifestSHA256 string   `json:"overlay_manifest_sha256"`
		WritableRoots         []string `json:"writable_roots"`
	}{
		workspace.WorkspaceID, run.RunID, workspace.Generation, filepath.Clean(workspace.RootPath),
		filepath.Clean(workspace.RepoCommonDir), filepath.Clean(gitAdminDir), workspace.BaseRef,
		workspace.BaseCommit, workspace.PrivateRef, snapshot.SnapshotID,
		snapshot.OverlayManifestSHA256, roots,
	})
	if err != nil {
		return WorkspaceAttestation{}, err
	}
	attestation := WorkspaceAttestation{
		AttestationID: "attestation-" + digest[:24], WorkspaceID: workspace.WorkspaceID,
		RunID: run.RunID, WorkspaceGeneration: workspace.Generation,
		CanonicalRoot: filepath.Clean(workspace.RootPath), RepoCommonDir: filepath.Clean(workspace.RepoCommonDir),
		GitAdminDir: filepath.Clean(gitAdminDir), BaseRef: workspace.BaseRef,
		BaseCommitOID: workspace.BaseCommit, PrivateRef: workspace.PrivateRef,
		SnapshotID: snapshot.SnapshotID, OverlayManifestSHA256: snapshot.OverlayManifestSHA256,
		WritableRootsJSON: string(writableJSONBytes), AttestationDigest: digest,
		CreatedAtMS: time.Now().UTC().UnixMilli(),
	}
	if _, err := store.db.ExecContext(ctx, `
		INSERT INTO workspace_attestations (
			attestation_id, workspace_id, run_id, workspace_generation, canonical_root,
			repo_common_dir, git_admin_dir, base_ref, base_commit_oid, private_ref,
			snapshot_id, overlay_manifest_sha256, writable_roots_json,
			attestation_digest, created_at_ms
		) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
		ON CONFLICT(workspace_id) DO NOTHING
	`, attestation.AttestationID, attestation.WorkspaceID, attestation.RunID,
		attestation.WorkspaceGeneration, attestation.CanonicalRoot, attestation.RepoCommonDir,
		attestation.GitAdminDir, attestation.BaseRef, attestation.BaseCommitOID,
		attestation.PrivateRef, attestation.SnapshotID, attestation.OverlayManifestSHA256,
		attestation.WritableRootsJSON, attestation.AttestationDigest, attestation.CreatedAtMS); err != nil {
		return WorkspaceAttestation{}, fmt.Errorf("record Workspace Attestation: %w", err)
	}
	stored, err := store.GetWorkspaceAttestation(ctx, workspace.WorkspaceID)
	if err != nil {
		return WorkspaceAttestation{}, err
	}
	if stored.AttestationDigest != attestation.AttestationDigest {
		return WorkspaceAttestation{}, fmt.Errorf("%w: Workspace Attestation replay differs", ErrWorkspaceBinding)
	}
	return stored, nil
}

func (store *Store) GetWorkspaceAttestation(ctx context.Context, workspaceID string) (WorkspaceAttestation, error) {
	if strings.TrimSpace(workspaceID) == "" {
		return WorkspaceAttestation{}, fmt.Errorf("%w: workspace id is required", ErrInvalidArgument)
	}
	var attestation WorkspaceAttestation
	err := store.db.QueryRowContext(ctx, `
		SELECT attestation_id, workspace_id, run_id, workspace_generation,
		       canonical_root, repo_common_dir, git_admin_dir, base_ref,
		       base_commit_oid, private_ref, snapshot_id, overlay_manifest_sha256,
		       writable_roots_json, attestation_digest, created_at_ms
		FROM workspace_attestations WHERE workspace_id = ?
	`, workspaceID).Scan(
		&attestation.AttestationID, &attestation.WorkspaceID, &attestation.RunID,
		&attestation.WorkspaceGeneration, &attestation.CanonicalRoot,
		&attestation.RepoCommonDir, &attestation.GitAdminDir, &attestation.BaseRef,
		&attestation.BaseCommitOID, &attestation.PrivateRef, &attestation.SnapshotID,
		&attestation.OverlayManifestSHA256, &attestation.WritableRootsJSON,
		&attestation.AttestationDigest, &attestation.CreatedAtMS,
	)
	if errors.Is(err, sql.ErrNoRows) {
		return WorkspaceAttestation{}, fmt.Errorf("%w: Workspace Attestation for %q", ErrNotFound, workspaceID)
	}
	if err != nil {
		return WorkspaceAttestation{}, err
	}
	return attestation, nil
}
