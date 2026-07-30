package runcontrol

import (
	"context"
	"errors"
	"fmt"
	"os/exec"
	"path/filepath"
	"strings"
)

// ErrNotGitRepository identifies a working directory that Git cannot resolve
// to a worktree. Callers can use errors.Is to distinguish this expected
// boundary failure from an unavailable Git executable or a cancelled context.
var ErrNotGitRepository = errors.New("not a git repository")

// Repository describes the paths shared by every worktree belonging to one
// Git repository. Root is specific to the current worktree, while CommonDir
// and DatabasePath are shared by the main and linked worktrees.
type Repository struct {
	Root         string
	CommonDir    string
	DatabasePath string
}

// ResolveRepository discovers the current worktree root and the shared Git
// common directory. Git commands always run with an explicit working
// directory so callers do not depend on, or mutate, process-global state.
func ResolveRepository(ctx context.Context, cwd string) (Repository, error) {
	if strings.TrimSpace(cwd) == "" {
		return Repository{}, fmt.Errorf("%w: repository working directory is required", ErrInvalidArgument)
	}

	directory, err := filepath.Abs(cwd)
	if err != nil {
		return Repository{}, fmt.Errorf("resolve repository working directory: %w", err)
	}
	directory = filepath.Clean(directory)

	rootOutput, err := runGitRevParse(ctx, directory, "--show-toplevel")
	if err != nil {
		if isGitRepositoryBoundaryError(err) {
			return Repository{}, fmt.Errorf("%w: working directory is outside a Git worktree", ErrNotGitRepository)
		}
		return Repository{}, fmt.Errorf("resolve Git worktree root: %w", err)
	}
	root, err := resolveGitPath(directory, rootOutput)
	if err != nil {
		return Repository{}, fmt.Errorf("resolve Git worktree root: %w", err)
	}

	commonOutput, err := runGitRevParse(ctx, directory, "--git-common-dir")
	if err != nil {
		if isGitRepositoryBoundaryError(err) {
			return Repository{}, fmt.Errorf("%w: working directory is outside a Git worktree", ErrNotGitRepository)
		}
		return Repository{}, fmt.Errorf("resolve Git common directory: %w", err)
	}
	commonDir, err := resolveGitPath(directory, commonOutput)
	if err != nil {
		return Repository{}, fmt.Errorf("resolve Git common directory: %w", err)
	}

	return Repository{
		Root:         root,
		CommonDir:    commonDir,
		DatabasePath: filepath.Join(commonDir, "specify-runtime", "run-control.sqlite"),
	}, nil
}

// OpenForRepository opens the run-control store shared by all worktrees in the
// repository containing cwd.
func OpenForRepository(ctx context.Context, cwd string, options ...OpenOption) (*Store, error) {
	repository, err := ResolveRepository(ctx, cwd)
	if err != nil {
		return nil, err
	}
	store, err := Open(ctx, repository.DatabasePath, options...)
	if err != nil {
		return nil, fmt.Errorf("open repository run control store: %w", err)
	}
	return store, nil
}

func runGitRevParse(ctx context.Context, directory string, argument string) (string, error) {
	command := exec.CommandContext(ctx, "git", "rev-parse", argument)
	command.Dir = directory
	output, err := command.Output()
	if err != nil {
		if contextErr := ctx.Err(); contextErr != nil {
			return "", contextErr
		}
		return "", err
	}
	value := strings.TrimSpace(string(output))
	if value == "" || strings.ContainsAny(value, "\r\n\x00") {
		return "", errors.New("Git returned an invalid path")
	}
	return value, nil
}

func isGitRepositoryBoundaryError(err error) bool {
	var exitError *exec.ExitError
	return errors.As(err, &exitError)
}

func resolveGitPath(directory string, value string) (string, error) {
	path := filepath.FromSlash(strings.TrimSpace(value))
	if path == "" {
		return "", errors.New("Git returned an empty path")
	}
	if !filepath.IsAbs(path) {
		path = filepath.Join(directory, path)
	}
	absolute, err := filepath.Abs(path)
	if err != nil {
		return "", err
	}
	return filepath.Clean(absolute), nil
}
