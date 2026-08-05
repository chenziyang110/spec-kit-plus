package runcontrol

import (
	"context"
	"crypto/sha256"
	"encoding/binary"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strconv"
	"time"
)

// RunResourceNamespace contains only runtime-owned paths and names. Nothing in
// this namespace is placed below the Git worktree, so temporary output cannot
// accidentally become part of a sealed Result.
type RunResourceNamespace struct {
	Root           string
	TempDir        string
	CacheDir       string
	LogDir         string
	ServiceName    string
	DatabaseName   string
	ComposeProject string
	PortBase       int
	Claims         []ResourceClaim
}

func prepareRunResourceNamespace(
	ctx context.Context,
	store *Store,
	repository Repository,
	run Run,
	attempt Attempt,
	workspace Workspace,
	leaseUntil time.Time,
) (RunResourceNamespace, error) {
	_, digest := safeRunToken(run.RunID)
	token := digest[:20] + "-g" + strconv.FormatInt(workspace.Generation, 10) + "-f" + strconv.FormatInt(attempt.Fence, 10)
	root := filepath.Join(repository.CommonDir, "specify-runtime", "run-resources", token)
	namespace := RunResourceNamespace{
		Root:           root,
		TempDir:        filepath.Join(root, "tmp"),
		CacheDir:       filepath.Join(root, "cache"),
		LogDir:         filepath.Join(root, "logs"),
		ServiceName:    "specify-" + digest[:16],
		DatabaseName:   "specify_" + digest[:16],
		ComposeProject: "specify-" + digest[:16],
		PortBase:       deterministicRunPortBase(run.RunID),
	}
	for _, directory := range []string{namespace.TempDir, namespace.CacheDir, namespace.LogDir} {
		if err := safeMkdirAllWithin(repository.CommonDir, directory); err != nil {
			return RunResourceNamespace{}, fmt.Errorf("create Run resource namespace: %w", err)
		}
	}

	type claimSpec struct {
		kind    ResourceType
		key     string
		binding map[string]any
	}
	specs := []claimSpec{
		{kind: ResourceFilesystem, key: filepath.Clean(workspace.RootPath), binding: map[string]any{"role": "edit-root", "path": workspace.RootPath}},
		{kind: ResourceTemp, key: filepath.Clean(namespace.TempDir), binding: map[string]any{"path": namespace.TempDir}},
		{kind: ResourceCache, key: filepath.Clean(namespace.CacheDir), binding: map[string]any{"path": namespace.CacheDir}},
		{kind: ResourceFilesystem, key: filepath.Clean(namespace.LogDir), binding: map[string]any{"role": "log-root", "path": namespace.LogDir}},
		{kind: ResourceService, key: namespace.ServiceName, binding: map[string]any{"name": namespace.ServiceName}},
		{kind: ResourceDatabase, key: namespace.DatabaseName, binding: map[string]any{"name": namespace.DatabaseName}},
		{kind: ResourceComposeProject, key: namespace.ComposeProject, binding: map[string]any{"name": namespace.ComposeProject}},
		{kind: ResourceTCPPort, key: "tcp:" + strconv.Itoa(namespace.PortBase), binding: map[string]any{"port_base": namespace.PortBase}},
	}
	for index, spec := range specs {
		binding, err := json.Marshal(spec.binding)
		if err != nil {
			return RunResourceNamespace{}, fmt.Errorf("encode Run resource binding: %w", err)
		}
		claim, err := store.AcquireResourceClaim(ctx, AcquireResourceClaimParams{
			ClaimID:       supervisedAggregateID("resource", run.RunID+"/"+string(spec.kind), int64(index+1)+workspace.Generation*1000),
			AttemptID:     attempt.AttemptID,
			Fence:         attempt.Fence,
			ResourceKind:  spec.kind,
			ResourceKey:   spec.key,
			Mode:          ResourceExclusive,
			BindingJSON:   string(binding),
			LeaseUntil:    leaseUntil,
			ExpectedRunID: run.RunID,
		})
		if err != nil {
			return RunResourceNamespace{}, fmt.Errorf("claim %s resource %q: %w", spec.kind, spec.key, err)
		}
		namespace.Claims = append(namespace.Claims, claim)
	}
	return namespace, nil
}

func deterministicRunPortBase(runID string) int {
	digest := sha256.Sum256([]byte(runID))
	return 20000 + int(binary.BigEndian.Uint16(digest[:2])%20000)
}

func supervisedResourceEnvironment(namespace RunResourceNamespace) []string {
	return []string{
		"SPECIFY_RUN_RESOURCE_ROOT=" + namespace.Root,
		"SPECIFY_RUN_TEMP=" + namespace.TempDir,
		"SPECIFY_RUN_CACHE=" + namespace.CacheDir,
		"SPECIFY_RUN_LOGS=" + namespace.LogDir,
		"SPECIFY_RUN_SERVICE_NAMESPACE=" + namespace.ServiceName,
		"SPECIFY_RUN_DATABASE_NAMESPACE=" + namespace.DatabaseName,
		"SPECIFY_RUN_COMPOSE_PROJECT=" + namespace.ComposeProject,
		"SPECIFY_RUN_PORT_BASE=" + strconv.Itoa(namespace.PortBase),
		"TMPDIR=" + namespace.TempDir,
		"TMP=" + namespace.TempDir,
		"TEMP=" + namespace.TempDir,
		"XDG_CACHE_HOME=" + namespace.CacheDir,
	}
}

func verifyRunResourceNamespace(namespace RunResourceNamespace) error {
	for _, directory := range []string{namespace.Root, namespace.TempDir, namespace.CacheDir, namespace.LogDir} {
		info, err := os.Stat(directory)
		if err != nil {
			return err
		}
		if !info.IsDir() {
			return fmt.Errorf("%w: Run resource path %q is not a directory", ErrWorkspaceBinding, directory)
		}
	}
	return nil
}
