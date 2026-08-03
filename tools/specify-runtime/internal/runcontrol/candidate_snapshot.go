package runcontrol

import (
	"context"
	"errors"
	"fmt"
	"os/exec"
	"strings"
)

// SnapshotGitCandidate commits every tracked and untracked change in the
// runtime-owned worktree, then returns the immutable Git identity to publish
// with successful Attempt closeout. It never touches the target worktree.
func SnapshotGitCandidate(
	ctx context.Context,
	repository Repository,
	run Run,
	attempt Attempt,
	workspace Workspace,
) (CandidateSnapshot, error) {
	canonical, err := canonicalAllocationRepository(ctx, repository)
	if err != nil {
		return CandidateSnapshot{}, err
	}
	if run.RunID == "" || attempt.RunID != run.RunID || workspace.RunID != run.RunID ||
		attempt.WorkspaceID != workspace.WorkspaceID ||
		attempt.WorkspaceGeneration != workspace.Generation ||
		workspace.Status != WorkspaceInUse {
		return CandidateSnapshot{}, fmt.Errorf("%w: candidate execution bindings are inconsistent", ErrCandidateBinding)
	}
	if !sameFilesystemPath(workspace.RepoCommonDir, canonical.CommonDir) {
		return CandidateSnapshot{}, fmt.Errorf("%w: candidate repository common directory changed", ErrCandidateBinding)
	}
	if err := validateOwnedWorkspacePath(canonical.PrimaryRoot, workspace.RootPath); err != nil {
		return CandidateSnapshot{}, fmt.Errorf("%w: %v", ErrCandidateBinding, err)
	}
	actual, err := ResolveRepository(ctx, workspace.RootPath)
	if err != nil || !sameFilesystemPath(actual.Root, workspace.RootPath) ||
		!sameFilesystemPath(actual.CommonDir, workspace.RepoCommonDir) {
		return CandidateSnapshot{}, fmt.Errorf("%w: workspace path is no longer the recorded Git worktree", ErrCandidateBinding)
	}
	branch, err := runGitOutput(ctx, workspace.RootPath, "symbolic-ref", "HEAD")
	if err != nil || branch != workspace.PrivateRef {
		return CandidateSnapshot{}, fmt.Errorf("%w: workspace HEAD is not private ref %q", ErrCandidateBinding, workspace.PrivateRef)
	}
	if err := requireGitAncestor(ctx, workspace.RootPath, workspace.BaseCommit, "HEAD"); err != nil {
		return CandidateSnapshot{}, fmt.Errorf("%w: workspace history no longer descends from base: %v", ErrCandidateBinding, err)
	}

	if err := runGitMutationWithRetry(ctx, workspace.RootPath, "add", "-A", "--", "."); err != nil {
		return CandidateSnapshot{}, fmt.Errorf("stage candidate snapshot: %w", err)
	}
	hasStagedChanges, err := gitDiffHasStagedChanges(ctx, workspace.RootPath)
	if err != nil {
		return CandidateSnapshot{}, err
	}
	if hasStagedChanges {
		message := "specify: snapshot Run " + run.RunID
		if err := runGitMutationWithRetry(
			ctx,
			workspace.RootPath,
			"-c", "user.name=Spec Kit Plus",
			"-c", "user.email=spec-kit-plus@invalid",
			"-c", "commit.gpgsign=false",
			"commit", "--no-verify", "--no-gpg-sign", "-m", message,
		); err != nil {
			return CandidateSnapshot{}, fmt.Errorf("commit candidate snapshot: %w", err)
		}
	}
	status, err := runGitStdout(ctx, workspace.RootPath, "status", "--porcelain", "--untracked-files=all")
	if err != nil {
		return CandidateSnapshot{}, fmt.Errorf("inspect candidate workspace status: %w", err)
	}
	if strings.TrimSpace(status) != "" {
		return CandidateSnapshot{}, fmt.Errorf("%w: candidate workspace is not clean after snapshot: %s", ErrCandidateBinding, strings.TrimSpace(status))
	}
	headCommit, err := resolveGitCommit(ctx, workspace.RootPath, "HEAD")
	if err != nil {
		return CandidateSnapshot{}, fmt.Errorf("resolve candidate HEAD: %w", err)
	}
	privateCommit, exists, err := resolveOptionalGitCommit(ctx, canonical.Root, workspace.PrivateRef)
	if err != nil || !exists || privateCommit != headCommit {
		return CandidateSnapshot{}, fmt.Errorf("%w: private ref does not match candidate HEAD", ErrCandidateBinding)
	}
	if err := requireGitAncestor(ctx, workspace.RootPath, workspace.BaseCommit, headCommit); err != nil {
		return CandidateSnapshot{}, fmt.Errorf("%w: candidate head does not descend from base: %v", ErrCandidateBinding, err)
	}
	return CandidateSnapshot{
		CandidateID: supervisedAggregateID("candidate", run.RunID, workspace.Generation),
		TargetRef:   workspace.BaseRef,
		BaseCommit:  workspace.BaseCommit,
		PrivateRef:  workspace.PrivateRef,
		HeadCommit:  headCommit,
	}, nil
}

func gitDiffHasStagedChanges(ctx context.Context, directory string) (bool, error) {
	command := exec.CommandContext(ctx, "git", "diff", "--cached", "--quiet", "--exit-code")
	command.Dir = directory
	err := command.Run()
	if err == nil {
		return false, nil
	}
	if contextErr := ctx.Err(); contextErr != nil {
		return false, contextErr
	}
	var exitError *exec.ExitError
	if errors.As(err, &exitError) && exitError.ExitCode() == 1 {
		return true, nil
	}
	return false, fmt.Errorf("inspect staged candidate changes: %w", err)
}

func requireGitAncestor(ctx context.Context, directory, ancestor, descendant string) error {
	command := exec.CommandContext(ctx, "git", "merge-base", "--is-ancestor", ancestor, descendant)
	command.Dir = directory
	err := command.Run()
	if err == nil {
		return nil
	}
	if contextErr := ctx.Err(); contextErr != nil {
		return contextErr
	}
	var exitError *exec.ExitError
	if errors.As(err, &exitError) && exitError.ExitCode() == 1 {
		return fmt.Errorf("%s is not an ancestor of %s", ancestor, descendant)
	}
	return err
}
