package runcontrol

import (
	"bytes"
	"context"
	"errors"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"sort"
	"strings"

	runtimecmd "github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/runtime"
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
	PrimaryRoot  string
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
		if isPlainNonGitDirectory(directory, err) {
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
		return Repository{}, fmt.Errorf("resolve Git common directory: %w", err)
	}
	commonDir, err := resolveGitPath(directory, commonOutput)
	if err != nil {
		return Repository{}, fmt.Errorf("resolve Git common directory: %w", err)
	}
	primaryRoot, err := resolvePrimaryWorktreeRoot(ctx, directory)
	if err != nil {
		return Repository{}, fmt.Errorf("resolve primary Git worktree root: %w", err)
	}

	return Repository{
		Root:         root,
		PrimaryRoot:  primaryRoot,
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

// OpenViewForRepository opens a read-only run-control view shared by all
// worktrees in the repository containing cwd.
func OpenViewForRepository(ctx context.Context, cwd string) (*View, error) {
	repository, err := ResolveRepository(ctx, cwd)
	if err != nil {
		return nil, err
	}
	view, err := OpenView(ctx, repository.DatabasePath)
	if err != nil {
		return nil, fmt.Errorf("open repository run control view: %w", err)
	}
	return view, nil
}

// InspectWorkspaceChanges returns repository-relative paths changed in one
// worktree. Both sides of a rename or copy are included so recovery holds do
// not accidentally release either declared scope.
func InspectWorkspaceChanges(ctx context.Context, workspaceRoot string) ([]string, error) {
	workspaceRoot = strings.TrimSpace(workspaceRoot)
	if workspaceRoot == "" {
		return nil, fmt.Errorf("%w: workspace root is required", ErrInvalidArgument)
	}
	output, err := runtimecmd.CommandOutputContext(ctx, workspaceRoot, nil, "git", "status", "--porcelain=v1", "-z", "--untracked-files=all")
	if err != nil {
		if contextErr := ctx.Err(); contextErr != nil {
			return nil, contextErr
		}
		return nil, fmt.Errorf("inspect workspace changes for %q: %w", workspaceRoot, err)
	}
	fields := bytes.Split(output, []byte{0})
	paths := make([]string, 0, len(fields))
	seen := make(map[string]struct{}, len(fields))
	appendPath := func(raw []byte) error {
		value := filepath.ToSlash(string(raw))
		pathValue, pathKey, err := normalizeWorkPath(value, runtime.GOOS == "windows")
		if err != nil {
			return fmt.Errorf("parse Git status path %q: %w", value, err)
		}
		if _, exists := seen[pathKey]; !exists {
			seen[pathKey] = struct{}{}
			paths = append(paths, pathValue)
		}
		return nil
	}
	for index := 0; index < len(fields); index++ {
		field := fields[index]
		if len(field) == 0 {
			continue
		}
		if len(field) < 4 || field[2] != ' ' {
			return nil, fmt.Errorf("Git returned malformed porcelain status for %q", workspaceRoot)
		}
		if err := appendPath(field[3:]); err != nil {
			return nil, err
		}
		if (field[0] == 'R' || field[0] == 'C' || field[1] == 'R' || field[1] == 'C') && index+1 < len(fields) {
			index++
			if err := appendPath(fields[index]); err != nil {
				return nil, err
			}
		}
	}
	sort.Strings(paths)
	return paths, nil
}

func ReadHeadCommit(ctx context.Context, workspaceRoot string) (string, error) {
	return runGitRevParse(ctx, workspaceRoot, "HEAD")
}

func runGitRevParse(ctx context.Context, directory string, argument string) (string, error) {
	output, err := runtimecmd.CommandOutputContext(ctx, directory, nil, "git", "rev-parse", argument)
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

func resolvePrimaryWorktreeRoot(ctx context.Context, directory string) (string, error) {
	output, err := runtimecmd.CommandOutputContext(ctx, directory, nil, "git", "worktree", "list", "--porcelain", "-z")
	if err != nil {
		if contextErr := ctx.Err(); contextErr != nil {
			return "", contextErr
		}
		return "", err
	}
	for _, field := range bytes.Split(output, []byte{0}) {
		const prefix = "worktree "
		if bytes.HasPrefix(field, []byte(prefix)) {
			value := string(field[len(prefix):])
			return resolveGitPath(directory, value)
		}
	}
	return "", errors.New("Git returned no primary worktree")
}

func isPlainNonGitDirectory(directory string, err error) bool {
	var exitError *exec.ExitError
	if !errors.As(err, &exitError) {
		return false
	}
	// Explicit Git routing means a command failure is configuration or metadata
	// trouble, not proof that the directory is simply outside a worktree.
	if os.Getenv("GIT_DIR") != "" || os.Getenv("GIT_WORK_TREE") != "" {
		return false
	}

	ceilings := make(map[string]struct{})
	for _, value := range filepath.SplitList(os.Getenv("GIT_CEILING_DIRECTORIES")) {
		if absolute, absoluteErr := filepath.Abs(value); absoluteErr == nil {
			ceilings[filepath.Clean(absolute)] = struct{}{}
		}
	}

	current := filepath.Clean(directory)
	for {
		_, statErr := os.Lstat(filepath.Join(current, ".git"))
		switch {
		case statErr == nil:
			return false
		case !errors.Is(statErr, os.ErrNotExist):
			return false
		}

		parent := filepath.Dir(current)
		if parent == current {
			break
		}
		if _, stop := ceilings[parent]; stop {
			break
		}
		current = parent
	}
	return true
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
