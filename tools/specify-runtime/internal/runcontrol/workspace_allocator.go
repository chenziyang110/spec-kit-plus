package runcontrol

import (
	"context"
	"crypto/sha256"
	"errors"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strconv"
	"strings"
	"time"
)

const (
	runWorktreeRootDirectory = "specify-runtime"
	runWorktreeNamespace     = "worktrees/runs"
)

type WorkspaceMaterializationStatus string

const (
	WorkspaceMaterializationCreated  WorkspaceMaterializationStatus = "created"
	WorkspaceMaterializationExisting WorkspaceMaterializationStatus = "existing"
)

type WorkspaceMaterialization struct {
	WorkspaceID string
	RootPath    string
	PrivateRef  string
	HeadCommit  string
	Status      WorkspaceMaterializationStatus
}

// PlanGitWorkspace freezes the repository, commit, path, and private branch
// identity for one Run workspace generation. The same Run ID and generation
// produce the same identity from every linked worktree in the repository.
func PlanGitWorkspace(ctx context.Context, repository Repository, run Run, generation int64) (CreateWorkspaceParams, error) {
	if strings.TrimSpace(run.RunID) == "" || strings.TrimSpace(run.TargetRef) == "" || generation <= 0 {
		return CreateWorkspaceParams{}, fmt.Errorf("%w: run id, target ref, and positive generation are required", ErrInvalidArgument)
	}
	canonical, err := canonicalAllocationRepository(ctx, repository)
	if err != nil {
		return CreateWorkspaceParams{}, err
	}
	baseRef, err := resolveMutableTargetRef(ctx, canonical.PrimaryRoot, run.TargetRef)
	if err != nil {
		return CreateWorkspaceParams{}, fmt.Errorf("resolve mutable target ref %q: %w", run.TargetRef, err)
	}
	baseCommit, err := resolveGitCommit(ctx, canonical.PrimaryRoot, baseRef)
	if err != nil {
		return CreateWorkspaceParams{}, fmt.Errorf("resolve target ref %q: %w", run.TargetRef, err)
	}
	identity := plannedWorkspaceIdentity(canonical, run.RunID, generation)
	if err := validateOwnedWorkspacePath(canonical.CommonDir, identity.rootPath); err != nil {
		return CreateWorkspaceParams{}, err
	}
	return CreateWorkspaceParams{
		WorkspaceID:   identity.workspaceID,
		RunID:         run.RunID,
		Generation:    generation,
		Kind:          "git_worktree",
		Mode:          WorkspaceModeIsolated,
		RootPath:      identity.rootPath,
		RepoCommonDir: canonical.CommonDir,
		BaseRef:       baseRef,
		BaseCommit:    baseCommit,
		PrivateRef:    identity.privateRef,
	}, nil
}

func PlanPrimaryWorkspace(ctx context.Context, repository Repository, run Run, generation int64) (CreateWorkspaceParams, error) {
	planned, err := planPrimaryWorkspaceBinding(ctx, repository, run, generation)
	if err != nil {
		return CreateWorkspaceParams{}, err
	}
	if err := requirePristinePrimaryWorkspace(ctx, planned.RootPath, planned.BaseRef); err != nil {
		return CreateWorkspaceParams{}, err
	}
	return planned, nil
}

func planPrimaryWorkspaceBinding(ctx context.Context, repository Repository, run Run, generation int64) (CreateWorkspaceParams, error) {
	if strings.TrimSpace(run.RunID) == "" || strings.TrimSpace(run.TargetRef) == "" || generation <= 0 {
		return CreateWorkspaceParams{}, fmt.Errorf("%w: run id, target ref, and positive generation are required", ErrInvalidArgument)
	}
	canonical, err := canonicalAllocationRepository(ctx, repository)
	if err != nil {
		return CreateWorkspaceParams{}, err
	}
	baseRef, err := resolveMutableTargetRef(ctx, canonical.Root, run.TargetRef)
	if err != nil {
		return CreateWorkspaceParams{}, fmt.Errorf("resolve mutable target ref %q: %w", run.TargetRef, err)
	}
	baseCommit, err := resolveGitCommit(ctx, canonical.Root, baseRef)
	if err != nil {
		return CreateWorkspaceParams{}, fmt.Errorf("resolve target ref %q: %w", run.TargetRef, err)
	}
	identity := plannedPrimaryWorkspaceIdentity(canonical, run.RunID, generation)
	return CreateWorkspaceParams{
		WorkspaceID:   identity.workspaceID,
		RunID:         run.RunID,
		Generation:    generation,
		Kind:          "git_worktree",
		Mode:          WorkspaceModePrimary,
		SourceRunID:   run.RunID,
		RootPath:      canonical.Root,
		RepoCommonDir: canonical.CommonDir,
		BaseRef:       baseRef,
		BaseCommit:    baseCommit,
		PrivateRef:    baseRef,
	}, nil
}

func requirePristinePrimaryWorkspace(ctx context.Context, rootPath, targetRef string) error {
	branch, err := runGitOutput(ctx, rootPath, "symbolic-ref", "--quiet", "HEAD")
	if err != nil || strings.TrimSpace(branch) != targetRef {
		return fmt.Errorf("%w: primary workspace does not check out target %q", ErrWorkspaceBinding, targetRef)
	}
	status, err := runGitStdout(ctx, rootPath, "status", "--porcelain", "--untracked-files=all")
	if err != nil {
		return err
	}
	if strings.TrimSpace(status) != "" {
		return fmt.Errorf("%w: primary workspace has local changes", ErrTargetWorktreeDirty)
	}
	return nil
}

func resolveMutableTargetRef(ctx context.Context, directory, revision string) (string, error) {
	if strings.TrimSpace(revision) == "HEAD" {
		value, err := runGitStdout(ctx, directory, "symbolic-ref", "--quiet", "HEAD")
		if err != nil {
			return "", fmt.Errorf("%w: target %q does not resolve to a local branch", ErrCandidateBinding, revision)
		}
		if strings.HasPrefix(value, "refs/heads/") && !strings.ContainsAny(value, "\r\n\x00") {
			return value, nil
		}
		return "", fmt.Errorf("%w: target %q does not resolve to a local branch", ErrCandidateBinding, revision)
	}
	value, err := runGitOutput(ctx, directory, "rev-parse", "--symbolic-full-name", "--verify", revision)
	if err != nil {
		return "", err
	}
	value = strings.TrimSpace(value)
	if !strings.HasPrefix(value, "refs/heads/") || strings.ContainsAny(value, "\r\n\x00") {
		return "", fmt.Errorf("%w: target %q does not resolve to a local branch", ErrCandidateBinding, revision)
	}
	return value, nil
}

// MaterializeGitWorkspace creates or verifies the physical worktree described
// by an already durable Workspace allocation. Existing paths are never
// overwritten or removed: replay succeeds only when every Git binding matches.
func MaterializeGitWorkspace(ctx context.Context, repository Repository, workspace Workspace) (WorkspaceMaterialization, error) {
	canonical, err := canonicalAllocationRepository(ctx, repository)
	if err != nil {
		return WorkspaceMaterialization{}, err
	}
	if err := validateMaterializationBinding(ctx, canonical, workspace); err != nil {
		return WorkspaceMaterialization{}, err
	}
	if workspaceIsPrimary(workspace, canonical) {
		if err := verifyMaterializedWorkspace(ctx, canonical, workspace); err != nil {
			return WorkspaceMaterialization{}, err
		}
		return materializationResult(workspace, WorkspaceMaterializationExisting), nil
	}

	_, statErr := os.Lstat(workspace.RootPath)
	switch {
	case statErr == nil:
		if err := verifyMaterializedWorkspace(ctx, canonical, workspace); err != nil {
			return WorkspaceMaterialization{}, err
		}
		return materializationResult(workspace, WorkspaceMaterializationExisting), nil
	case !errors.Is(statErr, os.ErrNotExist):
		return WorkspaceMaterialization{}, fmt.Errorf("inspect workspace root %q: %w", workspace.RootPath, statErr)
	}

	if err := createOwnedWorkspaceParents(canonical.CommonDir, workspace.RootPath); err != nil {
		return WorkspaceMaterialization{}, fmt.Errorf("create workspace parent: %w", err)
	}
	if err := validateOwnedWorkspacePath(canonical.CommonDir, workspace.RootPath); err != nil {
		return WorkspaceMaterialization{}, err
	}

	privateCommit, privateExists, err := resolveOptionalGitCommit(ctx, canonical.Root, workspace.PrivateRef)
	if err != nil {
		return WorkspaceMaterialization{}, fmt.Errorf("inspect private ref %q: %w", workspace.PrivateRef, err)
	}
	branchName := strings.TrimPrefix(workspace.PrivateRef, "refs/heads/")
	if privateExists {
		if privateCommit != workspace.BaseCommit {
			return WorkspaceMaterialization{}, fmt.Errorf(
				"%w: private ref %q points to %s, expected %s",
				ErrWorkspaceConflict, workspace.PrivateRef, privateCommit, workspace.BaseCommit,
			)
		}
		err = runGitMutationWithRetry(ctx, canonical.Root, "worktree", "add", workspace.RootPath, branchName)
	} else {
		err = runGitMutationWithRetry(ctx, canonical.Root, "worktree", "add", "-b", branchName, workspace.RootPath, workspace.BaseCommit)
	}
	if err != nil {
		// Git can report an uncertain outcome after creating the worktree. Treat
		// an exact observable binding as success; every other path is preserved
		// for reconciliation and reported as a conflict/failure.
		if verifyErr := verifyMaterializedWorkspace(ctx, canonical, workspace); verifyErr != nil {
			return WorkspaceMaterialization{}, fmt.Errorf("create Git worktree: %w", err)
		}
	}
	if err := verifyMaterializedWorkspace(ctx, canonical, workspace); err != nil {
		return WorkspaceMaterialization{}, err
	}
	return materializationResult(workspace, WorkspaceMaterializationCreated), nil
}

type workspaceIdentity struct {
	workspaceID string
	rootPath    string
	privateRef  string
}

func plannedPrimaryWorkspaceIdentity(repository Repository, runID string, generation int64) workspaceIdentity {
	_, digest := safeRunToken(runID)
	return workspaceIdentity{
		workspaceID: "workspace-primary-" + digest[:20] + "-g" + strconv.FormatInt(generation, 10),
		rootPath:    filepath.Clean(repository.Root),
	}
}

func plannedWorkspaceIdentity(repository Repository, runID string, generation int64) workspaceIdentity {
	token, digest := safeRunToken(runID)
	generationName := "g" + strconv.FormatInt(generation, 10)
	return workspaceIdentity{
		workspaceID: "workspace-" + digest[:20] + "-" + generationName,
		rootPath: filepath.Clean(filepath.Join(
			repository.CommonDir,
			runWorktreeRootDirectory,
			runWorktreeNamespace,
			token,
			generationName,
		)),
		privateRef: "refs/heads/specify/runs/" + token + "/" + generationName,
	}
}

func safeRunToken(runID string) (string, string) {
	digestBytes := sha256.Sum256([]byte(runID))
	digest := fmt.Sprintf("%x", digestBytes[:])
	var slug strings.Builder
	separator := false
	for _, character := range strings.ToLower(runID) {
		valid := (character >= 'a' && character <= 'z') || (character >= '0' && character <= '9')
		if valid {
			if slug.Len() >= 32 {
				break
			}
			slug.WriteRune(character)
			separator = false
			continue
		}
		if slug.Len() > 0 && slug.Len() < 32 && !separator {
			slug.WriteByte('-')
			separator = true
		}
	}
	value := strings.Trim(slug.String(), "-")
	if value == "" {
		value = "run"
	}
	return value + "-" + digest[:12], digest
}

func canonicalAllocationRepository(ctx context.Context, repository Repository) (Repository, error) {
	if strings.TrimSpace(repository.Root) == "" {
		return Repository{}, fmt.Errorf("%w: repository root is required", ErrInvalidArgument)
	}
	actual, err := ResolveRepository(ctx, repository.Root)
	if err != nil {
		return Repository{}, err
	}
	checks := []struct {
		name     string
		supplied string
		actual   string
	}{
		{name: "repository root", supplied: repository.Root, actual: actual.Root},
		{name: "primary worktree root", supplied: repository.PrimaryRoot, actual: actual.PrimaryRoot},
		{name: "Git common directory", supplied: repository.CommonDir, actual: actual.CommonDir},
	}
	for _, check := range checks {
		if strings.TrimSpace(check.supplied) != "" && !sameFilesystemPath(check.supplied, check.actual) {
			return Repository{}, fmt.Errorf("%w: %s %q does not match %q", ErrWorkspaceBinding, check.name, check.supplied, check.actual)
		}
	}
	return actual, nil
}

func validateMaterializationBinding(ctx context.Context, repository Repository, workspace Workspace) error {
	if workspace.Status != WorkspaceAllocating {
		return fmt.Errorf("%w: workspace %q has status %q, expected allocating", ErrWorkspaceBinding, workspace.WorkspaceID, workspace.Status)
	}
	if workspace.Kind != "git_worktree" || strings.TrimSpace(workspace.RunID) == "" || workspace.Generation <= 0 {
		return fmt.Errorf("%w: workspace kind, run id, and generation are invalid", ErrWorkspaceBinding)
	}
	if strings.TrimSpace(workspace.BaseRef) == "" || !validGitObjectID(workspace.BaseCommit) {
		return fmt.Errorf("%w: workspace base ref or commit is invalid", ErrWorkspaceBinding)
	}
	commit, err := resolveGitCommit(ctx, repository.Root, workspace.BaseCommit)
	if err != nil || commit != workspace.BaseCommit {
		return fmt.Errorf("%w: workspace base commit %q is not available in the repository", ErrWorkspaceBinding, workspace.BaseCommit)
	}
	if workspaceIsPrimary(workspace, repository) {
		return validatePrimaryWorkspaceBinding(ctx, repository, workspace)
	}
	identity := plannedWorkspaceIdentity(repository, workspace.RunID, workspace.Generation)
	if workspace.WorkspaceID != identity.workspaceID ||
		!sameFilesystemPath(workspace.RootPath, identity.rootPath) ||
		!sameFilesystemPath(workspace.RepoCommonDir, repository.CommonDir) ||
		workspace.PrivateRef != identity.privateRef {
		return fmt.Errorf("%w: workspace %q does not match its deterministic run generation identity", ErrWorkspaceBinding, workspace.WorkspaceID)
	}
	return validateOwnedWorkspacePath(repository.CommonDir, workspace.RootPath)
}

func verifyMaterializedWorkspace(ctx context.Context, repository Repository, workspace Workspace) error {
	actual, err := ResolveRepository(ctx, workspace.RootPath)
	if err != nil {
		return fmt.Errorf("%w: path %q is not the recorded Git worktree: %v", ErrWorkspaceConflict, workspace.RootPath, err)
	}
	if !sameFilesystemPath(actual.Root, workspace.RootPath) ||
		!sameFilesystemPath(actual.PrimaryRoot, repository.PrimaryRoot) ||
		!sameFilesystemPath(actual.CommonDir, workspace.RepoCommonDir) {
		return fmt.Errorf("%w: Git repository metadata does not match workspace %q", ErrWorkspaceConflict, workspace.WorkspaceID)
	}
	branch, err := runGitOutput(ctx, workspace.RootPath, "symbolic-ref", "HEAD")
	if err != nil || branch != workspace.PrivateRef {
		return fmt.Errorf("%w: workspace HEAD is not private ref %q", ErrWorkspaceConflict, workspace.PrivateRef)
	}
	head, err := resolveGitCommit(ctx, workspace.RootPath, "HEAD")
	if err != nil || head != workspace.BaseCommit {
		return fmt.Errorf("%w: workspace HEAD does not match base commit %q", ErrWorkspaceConflict, workspace.BaseCommit)
	}
	if workspaceIsPrimary(workspace, repository) {
		currentBase, err := resolveGitCommit(ctx, repository.Root, workspace.BaseRef)
		if err != nil || currentBase != workspace.BaseCommit {
			return fmt.Errorf("%w: primary target ref %q no longer matches base commit %q", ErrWorkspaceConflict, workspace.BaseRef, workspace.BaseCommit)
		}
		if branch != workspace.BaseRef || workspace.PrivateRef != workspace.BaseRef {
			return fmt.Errorf("%w: primary workspace HEAD %q is not bound to base ref %q", ErrWorkspaceConflict, branch, workspace.BaseRef)
		}
		return nil
	}
	privateCommit, exists, err := resolveOptionalGitCommit(ctx, repository.Root, workspace.PrivateRef)
	if err != nil || !exists || privateCommit != head {
		return fmt.Errorf("%w: private ref %q does not match workspace HEAD", ErrWorkspaceConflict, workspace.PrivateRef)
	}
	return validateOwnedWorkspacePath(repository.CommonDir, workspace.RootPath)
}

func materializationResult(workspace Workspace, status WorkspaceMaterializationStatus) WorkspaceMaterialization {
	return WorkspaceMaterialization{
		WorkspaceID: workspace.WorkspaceID,
		RootPath:    workspace.RootPath,
		PrivateRef:  workspace.PrivateRef,
		HeadCommit:  workspace.BaseCommit,
		Status:      status,
	}
}

func validatePrimaryWorkspaceBinding(ctx context.Context, repository Repository, workspace Workspace) error {
	identity := plannedPrimaryWorkspaceIdentity(repository, workspace.RunID, workspace.Generation)
	if workspace.WorkspaceID != identity.workspaceID ||
		!sameFilesystemPath(workspace.RootPath, repository.Root) ||
		!sameFilesystemPath(workspace.RepoCommonDir, repository.CommonDir) {
		return fmt.Errorf("%w: primary workspace %q does not match canonical repository root/common dir", ErrWorkspaceBinding, workspace.WorkspaceID)
	}
	if workspace.PrivateRef != workspace.BaseRef || strings.TrimSpace(workspace.PrivateRef) == "" {
		return fmt.Errorf("%w: primary workspace must bind HEAD directly to base ref", ErrWorkspaceBinding)
	}
	branch, err := runGitOutput(ctx, repository.Root, "symbolic-ref", "HEAD")
	if err != nil || branch != workspace.BaseRef {
		return fmt.Errorf("%w: repository HEAD is not base ref %q", ErrWorkspaceBinding, workspace.BaseRef)
	}
	currentBase, err := resolveGitCommit(ctx, repository.Root, workspace.BaseRef)
	if err != nil || currentBase != workspace.BaseCommit {
		return fmt.Errorf("%w: target ref %q no longer matches base commit %q", ErrWorkspaceBinding, workspace.BaseRef, workspace.BaseCommit)
	}
	return nil
}

func workspaceIsPrimary(workspace Workspace, repository Repository) bool {
	if workspace.Mode != "" {
		return workspace.Mode == WorkspaceModePrimary
	}
	return sameFilesystemPath(workspace.RootPath, repository.Root) &&
		sameFilesystemPath(workspace.RepoCommonDir, repository.CommonDir) &&
		strings.TrimSpace(workspace.BaseRef) != "" &&
		workspace.PrivateRef == workspace.BaseRef
}

func validateOwnedWorkspacePath(commonDir, candidate string) error {
	if !filepath.IsAbs(commonDir) || !filepath.IsAbs(candidate) {
		return fmt.Errorf("%w: workspace paths must be absolute", ErrWorkspaceEscape)
	}
	ownedRoot := filepath.Join(commonDir, runWorktreeRootDirectory, filepath.FromSlash(runWorktreeNamespace))
	resolvedCommon, err := resolveThroughExistingAncestor(commonDir)
	if err != nil {
		return fmt.Errorf("resolve Git common directory: %w", err)
	}
	resolvedOwnedRoot, err := resolveThroughExistingAncestor(ownedRoot)
	if err != nil {
		return fmt.Errorf("resolve runtime-owned workspace root: %w", err)
	}
	resolvedCandidate, err := resolveThroughExistingAncestor(candidate)
	if err != nil {
		return fmt.Errorf("resolve workspace path: %w", err)
	}
	if !isContainedPath(resolvedCommon, resolvedOwnedRoot) || !isContainedPath(resolvedOwnedRoot, resolvedCandidate) {
		return fmt.Errorf("%w: workspace path %q is outside %q", ErrWorkspaceEscape, candidate, ownedRoot)
	}
	return nil
}

func createOwnedWorkspaceParents(commonDir, candidate string) error {
	if err := validateOwnedWorkspacePath(commonDir, candidate); err != nil {
		return err
	}
	parent := filepath.Dir(filepath.Clean(candidate))
	relative, err := filepath.Rel(filepath.Clean(commonDir), parent)
	if err != nil || relative == "." || relative == ".." || strings.HasPrefix(relative, ".."+string(filepath.Separator)) {
		return fmt.Errorf("%w: workspace parent %q is outside Git common directory %q", ErrWorkspaceEscape, parent, commonDir)
	}
	current := filepath.Clean(commonDir)
	resolvedCommon, err := resolveThroughExistingAncestor(commonDir)
	if err != nil {
		return err
	}
	for _, segment := range strings.Split(relative, string(filepath.Separator)) {
		if segment == "" || segment == "." || segment == ".." {
			return fmt.Errorf("%w: workspace parent contains unsafe segment %q", ErrWorkspaceEscape, segment)
		}
		current = filepath.Join(current, segment)
		info, statErr := os.Lstat(current)
		if errors.Is(statErr, os.ErrNotExist) {
			if mkdirErr := os.Mkdir(current, 0o755); mkdirErr != nil && !errors.Is(mkdirErr, os.ErrExist) {
				return mkdirErr
			}
			info, statErr = os.Lstat(current)
		}
		if statErr != nil {
			return statErr
		}
		if info.Mode()&os.ModeSymlink != 0 || !info.IsDir() {
			return fmt.Errorf("%w: workspace parent component %q is not a real directory", ErrWorkspaceEscape, current)
		}
		resolvedCurrent, resolveErr := resolveThroughExistingAncestor(current)
		if resolveErr != nil {
			return resolveErr
		}
		if !isContainedPath(resolvedCommon, resolvedCurrent) {
			return fmt.Errorf("%w: workspace parent component %q escapes Git common directory", ErrWorkspaceEscape, current)
		}
	}
	return validateOwnedWorkspacePath(commonDir, candidate)
}

func resolveThroughExistingAncestor(path string) (string, error) {
	absolute, err := filepath.Abs(path)
	if err != nil {
		return "", err
	}
	current := filepath.Clean(absolute)
	var missing []string
	for {
		_, statErr := os.Lstat(current)
		if statErr == nil {
			resolved, resolveErr := filepath.EvalSymlinks(current)
			if resolveErr != nil {
				return "", resolveErr
			}
			for index := len(missing) - 1; index >= 0; index-- {
				resolved = filepath.Join(resolved, missing[index])
			}
			return filepath.Clean(resolved), nil
		}
		if !errors.Is(statErr, os.ErrNotExist) {
			return "", statErr
		}
		parent := filepath.Dir(current)
		if parent == current {
			return "", statErr
		}
		missing = append(missing, filepath.Base(current))
		current = parent
	}
}

func isContainedPath(root, candidate string) bool {
	relative, err := filepath.Rel(filepath.Clean(root), filepath.Clean(candidate))
	return err == nil && relative != "." && relative != ".." && !strings.HasPrefix(relative, ".."+string(filepath.Separator))
}

func sameFilesystemPath(left, right string) bool {
	left = filepath.Clean(left)
	right = filepath.Clean(right)
	if runtime.GOOS == "windows" {
		return strings.EqualFold(left, right)
	}
	return left == right
}

func validGitObjectID(value string) bool {
	if len(value) != 40 && len(value) != 64 {
		return false
	}
	for _, character := range value {
		if (character < '0' || character > '9') && (character < 'a' || character > 'f') {
			return false
		}
	}
	return true
}

func resolveGitCommit(ctx context.Context, directory, revision string) (string, error) {
	value, err := runGitOutput(ctx, directory, "rev-parse", "--verify", "--end-of-options", revision+"^{commit}")
	if err != nil {
		return "", err
	}
	value = strings.ToLower(strings.TrimSpace(value))
	if !validGitObjectID(value) {
		return "", fmt.Errorf("Git returned invalid commit %q", value)
	}
	return value, nil
}

func resolveOptionalGitCommit(ctx context.Context, directory, revision string) (string, bool, error) {
	command := exec.CommandContext(ctx, "git", "rev-parse", "--verify", "--quiet", "--end-of-options", revision+"^{commit}")
	command.Dir = directory
	output, err := command.CombinedOutput()
	if err != nil {
		if contextErr := ctx.Err(); contextErr != nil {
			return "", false, contextErr
		}
		var exitError *exec.ExitError
		if errors.As(err, &exitError) && exitError.ExitCode() == 1 {
			return "", false, nil
		}
		return "", false, fmt.Errorf("git rev-parse failed: %w: %s", err, strings.TrimSpace(string(output)))
	}
	value := strings.ToLower(strings.TrimSpace(string(output)))
	if !validGitObjectID(value) {
		return "", false, fmt.Errorf("Git returned invalid commit %q", value)
	}
	return value, true, nil
}

func runGitOutput(ctx context.Context, directory string, arguments ...string) (string, error) {
	command := exec.CommandContext(ctx, "git", arguments...)
	command.Dir = directory
	output, err := command.CombinedOutput()
	if err != nil {
		if contextErr := ctx.Err(); contextErr != nil {
			return "", contextErr
		}
		return "", fmt.Errorf("git %s failed: %w: %s", strings.Join(arguments, " "), err, strings.TrimSpace(string(output)))
	}
	value := strings.TrimSpace(string(output))
	if strings.ContainsRune(value, 0) {
		return "", errors.New("Git returned NUL output")
	}
	return value, nil
}

// runGitStdout is used when stdout is itself the protocol. Git may emit
// non-fatal configuration warnings on stderr; combining streams would turn
// those warnings into false status/path data.
func runGitStdout(ctx context.Context, directory string, arguments ...string) (string, error) {
	command := exec.CommandContext(ctx, "git", arguments...)
	command.Dir = directory
	output, err := command.Output()
	if err != nil {
		if contextErr := ctx.Err(); contextErr != nil {
			return "", contextErr
		}
		return "", fmt.Errorf("git %s failed: %w", strings.Join(arguments, " "), err)
	}
	value := strings.TrimSpace(string(output))
	if strings.ContainsRune(value, 0) {
		return "", errors.New("Git returned NUL output")
	}
	return value, nil
}

func runGitMutationWithRetry(ctx context.Context, directory string, arguments ...string) error {
	var lastErr error
	for attempt := 0; attempt < 20; attempt++ {
		_, err := runGitOutput(ctx, directory, arguments...)
		if err == nil {
			return nil
		}
		lastErr = err
		if !isTransientGitLockError(err) {
			return err
		}
		delay := time.Duration(attempt+1) * 25 * time.Millisecond
		if delay > 250*time.Millisecond {
			delay = 250 * time.Millisecond
		}
		timer := time.NewTimer(delay)
		select {
		case <-ctx.Done():
			timer.Stop()
			return ctx.Err()
		case <-timer.C:
		}
	}
	return lastErr
}

func isTransientGitLockError(err error) bool {
	message := strings.ToLower(err.Error())
	for _, marker := range []string{
		"another git process",
		"could not lock",
		"unable to create", // Git reports lock-file creation races this way.
		"index.lock",
		"config.lock",
		"packed-refs.lock",
	} {
		if strings.Contains(message, marker) {
			return true
		}
	}
	return false
}
