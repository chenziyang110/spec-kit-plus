package runcontrol

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"sort"
	"strconv"
	"strings"
	"time"
)

func SealRunResult(
	ctx context.Context,
	repository Repository,
	run Run,
	attempt Attempt,
	workspace Workspace,
	snapshot Snapshot,
	snapshotEntries []SnapshotEntry,
	attestation WorkspaceAttestation,
	resources RunResourceNamespace,
	resultRevision int64,
) (RunResultSnapshot, error) {
	canonical, err := canonicalAllocationRepository(ctx, repository)
	if err != nil {
		return RunResultSnapshot{}, err
	}
	if resultRevision <= 0 || attempt.RunID != run.RunID || workspace.RunID != run.RunID ||
		attempt.WorkspaceID != workspace.WorkspaceID || attempt.WorkspaceGeneration != workspace.Generation ||
		workspace.Status != WorkspaceInUse || snapshot.RunID != run.RunID ||
		snapshot.TargetRef != workspace.BaseRef || snapshot.BaseCommit != workspace.BaseCommit {
		return RunResultSnapshot{}, fmt.Errorf("%w: Result sealing bindings are inconsistent", ErrCandidateBinding)
	}
	if attestation.WorkspaceID != workspace.WorkspaceID ||
		attestation.RunID != run.RunID ||
		attestation.WorkspaceGeneration != workspace.Generation ||
		filepath.Clean(attestation.CanonicalRoot) != filepath.Clean(workspace.RootPath) ||
		filepath.Clean(attestation.RepoCommonDir) != filepath.Clean(workspace.RepoCommonDir) ||
		attestation.BaseRef != workspace.BaseRef ||
		attestation.BaseCommitOID != workspace.BaseCommit ||
		attestation.PrivateRef != workspace.PrivateRef ||
		attestation.SnapshotID != snapshot.SnapshotID ||
		attestation.OverlayManifestSHA256 != snapshot.OverlayManifestSHA256 ||
		!validSHA256(attestation.AttestationDigest) {
		return RunResultSnapshot{}, fmt.Errorf("%w: persisted workspace attestation does not match execution bindings", ErrWorkspaceBinding)
	}
	if err := validateSnapshotWorkspaceBinding(ctx, canonical, workspace); err != nil {
		return RunResultSnapshot{}, err
	}
	if err := verifyRunResourceNamespace(resources); err != nil {
		return RunResultSnapshot{}, fmt.Errorf("attest Run resources before sealing: %w", err)
	}

	indexRoot := filepath.Join(canonical.CommonDir, "specify-runtime", "result-indexes")
	if err := safeMkdirAllWithin(canonical.CommonDir, indexRoot); err != nil {
		return RunResultSnapshot{}, err
	}
	indexFile, err := os.CreateTemp(indexRoot, "index-*.tmp")
	if err != nil {
		return RunResultSnapshot{}, fmt.Errorf("allocate Result index: %w", err)
	}
	indexPath := indexFile.Name()
	if err := indexFile.Close(); err != nil {
		return RunResultSnapshot{}, err
	}
	if err := os.Remove(indexPath); err != nil {
		return RunResultSnapshot{}, err
	}
	defer func() { _ = os.Remove(indexPath) }()
	gitEnv := map[string]string{"GIT_INDEX_FILE": indexPath}
	if _, err := runGitWithEnvironment(ctx, workspace.RootPath, gitEnv, "read-tree", workspace.BaseCommit); err != nil {
		return RunResultSnapshot{}, fmt.Errorf("seed Result index: %w", err)
	}
	if _, err := runGitWithEnvironment(ctx, workspace.RootPath, gitEnv, "add", "-A", "--", "."); err != nil {
		return RunResultSnapshot{}, fmt.Errorf("capture Result workspace tree: %w", err)
	}

	finalAmbient := make(map[string]SnapshotEntry)
	for _, raw := range snapshotEntries {
		entry := hydrateSnapshotEntryCompatibility(raw)
		if previous, exists := finalAmbient[entry.RelativePath]; !exists || entry.Ordinal > previous.Ordinal {
			finalAmbient[entry.RelativePath] = entry
		}
	}
	overlayDependent := false
	ambientPaths := make([]string, 0, len(finalAmbient))
	for path := range finalAmbient {
		ambientPaths = append(ambientPaths, path)
	}
	sort.Strings(ambientPaths)
	for _, path := range ambientPaths {
		entry := finalAmbient[path]
		matches, err := workspaceMatchesSnapshotEntry(workspace.RootPath, entry)
		if err != nil {
			return RunResultSnapshot{}, err
		}
		if !matches {
			overlayDependent = true
			continue
		}
		if err := restoreResultIndexPathToBase(ctx, workspace.RootPath, gitEnv, workspace.BaseCommit, path); err != nil {
			return RunResultSnapshot{}, err
		}
	}

	treeOID, err := runGitWithEnvironment(ctx, workspace.RootPath, gitEnv, "write-tree")
	if err != nil {
		return RunResultSnapshot{}, fmt.Errorf("write Result tree: %w", err)
	}
	treeOID = strings.ToLower(strings.TrimSpace(treeOID))
	if !validGitObjectID(treeOID) {
		return RunResultSnapshot{}, fmt.Errorf("%w: Git returned invalid Result tree %q", ErrCandidateBinding, treeOID)
	}
	resultID := supervisedAggregateID("result", run.RunID, workspace.Generation)
	_, runDigest := safeRunToken(run.RunID)
	hiddenRef := "refs/specify/results/" + runDigest[:20] + "/r" + strconv.FormatInt(resultRevision, 10)
	commitEnv := map[string]string{
		"GIT_AUTHOR_NAME":     "Spec Kit Plus",
		"GIT_AUTHOR_EMAIL":    "spec-kit-plus@invalid",
		"GIT_COMMITTER_NAME":  "Spec Kit Plus",
		"GIT_COMMITTER_EMAIL": "spec-kit-plus@invalid",
	}
	commitOID, err := runGitWithEnvironment(
		ctx,
		workspace.RootPath,
		commitEnv,
		"commit-tree", treeOID, "-p", workspace.BaseCommit,
		"-m", "specify: seal Run Result "+resultID,
	)
	if err != nil {
		return RunResultSnapshot{}, fmt.Errorf("commit Result tree: %w", err)
	}
	commitOID = strings.ToLower(strings.TrimSpace(commitOID))
	if !validGitObjectID(commitOID) {
		return RunResultSnapshot{}, fmt.Errorf("%w: Git returned invalid Result commit %q", ErrCandidateBinding, commitOID)
	}
	if err := createImmutableGitRef(ctx, canonical.Root, hiddenRef, commitOID); err != nil {
		return RunResultSnapshot{}, err
	}
	changedPaths, err := changedPathsBetweenObjects(ctx, workspace.RootPath, workspace.BaseCommit, treeOID)
	if err != nil {
		return RunResultSnapshot{}, err
	}
	resourceAttestation, err := digestRunResourceClaims(resources.Claims)
	if err != nil {
		return RunResultSnapshot{}, err
	}
	eligibility := ResultEligibilityReady
	if overlayDependent {
		eligibility = ResultEligibilityOverlayDependent
	}
	manifestSHA256, err := digestCanonicalJSON(struct {
		ResultID                   string            `json:"result_id"`
		ResultRevision             int64             `json:"result_revision"`
		RunID                      string            `json:"run_id"`
		ActivityID                 string            `json:"activity_id"`
		AttemptID                  string            `json:"attempt_id"`
		Fence                      int64             `json:"fence"`
		SnapshotID                 string            `json:"snapshot_id"`
		BaseCommitOID              string            `json:"base_commit_oid"`
		ResultTreeOID              string            `json:"result_tree_oid"`
		ResultCommitOID            string            `json:"result_commit_oid"`
		HiddenRef                  string            `json:"hidden_ref"`
		ChangedPaths               []string          `json:"changed_paths"`
		Eligibility                ResultEligibility `json:"eligibility"`
		WorkspaceAttestationSHA256 string            `json:"workspace_attestation_sha256"`
		ResourceAttestationSHA256  string            `json:"resource_attestation_sha256"`
	}{
		ResultID: resultID, ResultRevision: resultRevision, RunID: run.RunID,
		ActivityID: attempt.ActivityID, AttemptID: attempt.AttemptID, Fence: attempt.Fence,
		SnapshotID: snapshot.SnapshotID, BaseCommitOID: workspace.BaseCommit,
		ResultTreeOID: treeOID, ResultCommitOID: commitOID, HiddenRef: hiddenRef,
		ChangedPaths: changedPaths, Eligibility: eligibility,
		WorkspaceAttestationSHA256: attestation.AttestationDigest,
		ResourceAttestationSHA256:  resourceAttestation,
	})
	if err != nil {
		return RunResultSnapshot{}, err
	}
	return RunResultSnapshot{
		ResultID: resultID, ResultRevision: resultRevision, SnapshotID: snapshot.SnapshotID,
		TargetRef: workspace.BaseRef, BaseCommitOID: workspace.BaseCommit,
		ResultTreeOID: treeOID, ResultCommitOID: commitOID, HiddenRef: hiddenRef,
		ManifestSHA256: manifestSHA256, WorkspaceAttestationSHA256: attestation.AttestationDigest,
		ResourceAttestationSHA256: resourceAttestation, Eligibility: eligibility,
		ChangedPaths: changedPaths, ValidationEvidenceJSON: "[]",
		WorkerResultDigestsJSON: "[]", ExternalEffectsJSON: "[]",
	}, nil
}

func workspaceMatchesSnapshotEntry(workspaceRoot string, entry SnapshotEntry) (bool, error) {
	path, err := resolveSnapshotTargetPath(workspaceRoot, entry.RelativePath)
	if err != nil {
		return false, err
	}
	switch entry.Kind {
	case SnapshotEntryDeleted:
		_, err := os.Lstat(path)
		if errors.Is(err, os.ErrNotExist) {
			return true, nil
		}
		return false, err
	case SnapshotEntryFile:
		info, err := os.Lstat(path)
		if errors.Is(err, os.ErrNotExist) {
			return false, nil
		}
		if err != nil {
			return false, err
		}
		if !info.Mode().IsRegular() {
			return false, nil
		}
		contents, err := os.ReadFile(path)
		if err != nil {
			return false, err
		}
		digest := sha256.Sum256(contents)
		return hex.EncodeToString(digest[:]) == entry.BlobSHA256, nil
	default:
		return false, fmt.Errorf("%w: unsupported Snapshot entry kind %q", ErrInvalidArgument, entry.Kind)
	}
}

func restoreResultIndexPathToBase(
	ctx context.Context,
	directory string,
	environment map[string]string,
	baseCommit string,
	relativePath string,
) error {
	output, err := runGitWithEnvironmentBytes(ctx, directory, environment, "ls-tree", "-z", baseCommit, "--", relativePath)
	if err != nil {
		return fmt.Errorf("inspect base path %q: %w", relativePath, err)
	}
	if len(output) == 0 {
		if _, err := runGitWithEnvironment(ctx, directory, environment, "update-index", "--force-remove", "--", relativePath); err != nil {
			return fmt.Errorf("remove ambient-only path %q from Result index: %w", relativePath, err)
		}
		return nil
	}
	line := strings.TrimSuffix(string(output), "\x00")
	tab := strings.IndexByte(line, '\t')
	if tab <= 0 {
		return fmt.Errorf("%w: invalid Git ls-tree record for %q", ErrCandidateBinding, relativePath)
	}
	metadata := strings.Fields(line[:tab])
	if len(metadata) != 3 || metadata[1] != "blob" || !validGitObjectID(metadata[2]) {
		return fmt.Errorf("%w: unsupported base entry for %q", ErrCandidateBinding, relativePath)
	}
	cacheInfo := metadata[0] + "," + metadata[2] + "," + relativePath
	if _, err := runGitWithEnvironment(ctx, directory, environment, "update-index", "--add", "--cacheinfo", cacheInfo); err != nil {
		return fmt.Errorf("restore base path %q in Result index: %w", relativePath, err)
	}
	return nil
}

func changedPathsBetweenObjects(ctx context.Context, directory, baseCommit, treeOID string) ([]string, error) {
	output, err := runGitWithEnvironmentBytes(ctx, directory, nil, "diff", "--name-only", "-z", baseCommit, treeOID)
	if err != nil {
		return nil, fmt.Errorf("derive Result changed paths: %w", err)
	}
	paths := make([]string, 0)
	for _, raw := range strings.Split(string(output), "\x00") {
		if raw == "" {
			continue
		}
		path, err := normalizeSnapshotRelativePath(raw)
		if err != nil {
			return nil, err
		}
		paths = append(paths, path)
	}
	sort.Strings(paths)
	return paths, nil
}

func createImmutableGitRef(ctx context.Context, directory, ref, commitOID string) error {
	existing, exists, err := resolveOptionalGitCommit(ctx, directory, ref)
	if err != nil {
		return err
	}
	if exists {
		if existing == commitOID {
			return nil
		}
		return fmt.Errorf("%w: immutable ref %q already points to %s", ErrAlreadyExists, ref, existing)
	}
	zeroOID := strings.Repeat("0", len(commitOID))
	if err := runGitMutationWithRetry(ctx, directory, "update-ref", ref, commitOID, zeroOID); err != nil {
		return fmt.Errorf("publish immutable Git ref %q: %w", ref, err)
	}
	return nil
}

func digestRunResourceClaims(claims []ResourceClaim) (string, error) {
	type binding struct {
		ClaimID      string            `json:"claim_id"`
		ResourceType ResourceType      `json:"resource_type"`
		ResourceKey  string            `json:"resource_key"`
		Mode         ResourceClaimMode `json:"mode"`
		Fence        int64             `json:"fence"`
		BindingJSON  string            `json:"binding_json"`
	}
	bindings := make([]binding, 0, len(claims))
	for _, claim := range claims {
		bindings = append(bindings, binding{
			ClaimID: claim.ClaimID, ResourceType: claim.ResourceType, ResourceKey: claim.ResourceKey,
			Mode: claim.Mode, Fence: claim.Fence, BindingJSON: claim.BindingJSON,
		})
	}
	sort.Slice(bindings, func(i, j int) bool { return bindings[i].ClaimID < bindings[j].ClaimID })
	return digestCanonicalJSON(bindings)
}

func digestCanonicalJSON(value any) (string, error) {
	encoded, err := json.Marshal(value)
	if err != nil {
		return "", fmt.Errorf("encode canonical manifest: %w", err)
	}
	digest := sha256.Sum256(encoded)
	return hex.EncodeToString(digest[:]), nil
}

func runGitWithEnvironment(
	ctx context.Context,
	directory string,
	environment map[string]string,
	arguments ...string,
) (string, error) {
	output, err := runGitWithEnvironmentBytes(ctx, directory, environment, arguments...)
	return strings.TrimSpace(string(output)), err
}

func runGitWithEnvironmentBytes(
	ctx context.Context,
	directory string,
	environment map[string]string,
	arguments ...string,
) ([]byte, error) {
	command := exec.CommandContext(ctx, "git", arguments...)
	command.Dir = directory
	command.Env = mergeEnvironment(os.Environ(), environment)
	output, err := command.CombinedOutput()
	if err != nil {
		if ctx.Err() != nil {
			return nil, ctx.Err()
		}
		return nil, fmt.Errorf("git %s failed: %w: %s", strings.Join(arguments, " "), err, strings.TrimSpace(string(output)))
	}
	return output, nil
}

func mergeEnvironment(base []string, overrides map[string]string) []string {
	if len(overrides) == 0 {
		return base
	}
	keys := make(map[string]struct{}, len(overrides))
	for key := range overrides {
		keys[strings.ToUpper(key)] = struct{}{}
	}
	merged := make([]string, 0, len(base)+len(overrides))
	for _, entry := range base {
		name := entry
		if separator := strings.IndexByte(entry, '='); separator >= 0 {
			name = entry[:separator]
		}
		if _, replaced := keys[strings.ToUpper(name)]; !replaced {
			merged = append(merged, entry)
		}
	}
	ordered := make([]string, 0, len(overrides))
	for key := range overrides {
		ordered = append(ordered, key)
	}
	sort.Strings(ordered)
	for _, key := range ordered {
		merged = append(merged, key+"="+overrides[key])
	}
	return merged
}

func resultSealNow() time.Time { return time.Now().UTC() }
