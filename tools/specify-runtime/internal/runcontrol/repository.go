package runcontrol

import (
	"bytes"
	"context"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
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

const emptyGitTreeOID = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"

// Repository describes the paths shared by every worktree belonging to one
// Git repository. Root is specific to the current worktree, while CommonDir
// and DatabasePath are shared by the main and linked worktrees.
type Repository struct {
	Root         string
	PrimaryRoot  string
	CommonDir    string
	DatabasePath string
}

type WorkspaceBaseline struct {
	HeadCommit   string               `json:"head_commit"`
	DirtyPaths   []string             `json:"dirty_paths"`
	PathDigests  map[string]string    `json:"path_digests"`
	WorkerPacket *WorkerPacketBinding `json:"worker_packet,omitempty"`
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

func CaptureWorkspaceBaseline(ctx context.Context, workspaceRoot string) (WorkspaceBaseline, error) {
	headCommit, err := ReadHeadCommit(ctx, workspaceRoot)
	if err != nil {
		// An initialized but unborn repository has no HEAD yet. The canonical
		// empty-tree object keeps later committed-path comparison deterministic.
		headCommit = emptyGitTreeOID
	}
	dirtyPaths, err := InspectWorkspaceChanges(ctx, workspaceRoot)
	if err != nil {
		return WorkspaceBaseline{}, fmt.Errorf("capture workspace baseline paths: %w", err)
	}
	digests := make(map[string]string, len(dirtyPaths))
	for _, path := range dirtyPaths {
		digest, digestErr := workspacePathDigest(workspaceRoot, path)
		if digestErr != nil {
			return WorkspaceBaseline{}, fmt.Errorf("capture baseline digest for %q: %w", path, digestErr)
		}
		digests[path] = digest
	}
	return WorkspaceBaseline{HeadCommit: headCommit, DirtyPaths: dirtyPaths, PathDigests: digests}, nil
}

func EncodeWorkspaceBaseline(baseline WorkspaceBaseline) (string, error) {
	if strings.TrimSpace(baseline.HeadCommit) == "" {
		return "", fmt.Errorf("%w: workspace baseline head commit is required", ErrInvalidArgument)
	}
	if baseline.DirtyPaths == nil {
		baseline.DirtyPaths = []string{}
	}
	if baseline.PathDigests == nil {
		baseline.PathDigests = map[string]string{}
	}
	raw, err := json.Marshal(baseline)
	if err != nil {
		return "", fmt.Errorf("encode workspace baseline: %w", err)
	}
	return string(raw), nil
}

// InspectWorkspaceDelta audits deliverable changes against an execution's
// baseline. Known private runtime transport paths are excluded only here;
// ownership recovery must continue to use the unfiltered InspectWorkspaceChanges.
func InspectWorkspaceDelta(ctx context.Context, workspaceRoot, baselineJSON string) ([]string, error) {
	var baseline WorkspaceBaseline
	if err := json.Unmarshal([]byte(strings.TrimSpace(baselineJSON)), &baseline); err != nil {
		return nil, fmt.Errorf("decode workspace baseline: %w", err)
	}
	if strings.TrimSpace(baseline.HeadCommit) == "" {
		return nil, fmt.Errorf("%w: workspace baseline has no head commit", ErrInvalidArgument)
	}
	committed, err := inspectCommittedWorkspacePaths(ctx, workspaceRoot, baseline.HeadCommit)
	if err != nil {
		return nil, err
	}
	dirty, err := InspectWorkspaceChanges(ctx, workspaceRoot)
	if err != nil {
		return nil, err
	}
	type baselinePathState struct {
		path   string
		digest string
	}
	baselineByKey := make(map[string]baselinePathState, len(baseline.PathDigests))
	for baselinePath, digest := range baseline.PathDigests {
		pathValue, pathKey, normalizeErr := normalizeWorkPath(baselinePath, runtime.GOOS == "windows")
		if normalizeErr != nil {
			return nil, fmt.Errorf("normalize workspace baseline path %q: %w", baselinePath, normalizeErr)
		}
		if isPrivateRuntimeTransportPath(pathKey) {
			continue
		}
		baselineByKey[pathKey] = baselinePathState{path: pathValue, digest: digest}
	}
	seen := make(map[string]string, len(committed)+len(dirty)+len(baselineByKey))
	for _, path := range committed {
		_, key, normalizeErr := normalizeWorkPath(path, runtime.GOOS == "windows")
		if normalizeErr != nil {
			return nil, normalizeErr
		}
		if isPrivateRuntimeTransportPath(key) {
			continue
		}
		seen[key] = path
	}
	currentDirtyKeys := make(map[string]struct{}, len(dirty))
	for _, path := range dirty {
		_, key, normalizeErr := normalizeWorkPath(path, runtime.GOOS == "windows")
		if normalizeErr != nil {
			return nil, normalizeErr
		}
		if isPrivateRuntimeTransportPath(key) {
			continue
		}
		digest, digestErr := workspacePathDigest(workspaceRoot, path)
		if digestErr != nil {
			return nil, fmt.Errorf("inspect current digest for %q: %w", path, digestErr)
		}
		currentDirtyKeys[key] = struct{}{}
		if baselineState, existed := baselineByKey[key]; existed && baselineState.digest == digest {
			continue
		}
		seen[key] = path
	}
	// A path that was already dirty at announcement may disappear from Git
	// status after deletion or restoration. Re-read those paths explicitly so
	// the execution audit cannot mistake absence from current status for no-op.
	for key, baselineState := range baselineByKey {
		if _, stillDirty := currentDirtyKeys[key]; stillDirty {
			continue
		}
		digest, digestErr := workspacePathDigest(workspaceRoot, baselineState.path)
		if digestErr != nil {
			return nil, fmt.Errorf("inspect current digest for baseline path %q: %w", baselineState.path, digestErr)
		}
		if digest != baselineState.digest {
			seen[key] = baselineState.path
		}
	}
	paths := make([]string, 0, len(seen))
	for _, path := range seen {
		paths = append(paths, path)
	}
	sort.Strings(paths)
	return paths, nil
}

// isPrivateRuntimeTransportPath accepts an already-normalized repository path
// key. These are operational journals/copies, receipts, leases, and locks owned
// by file_transaction.go, artifact*.go, and the workflow lock helpers. Their
// canonical source/destination artifacts remain audited, including both sides
// of renames. Do not extend this to all of .specify or .planning: even unknown
// .specify/runtime paths and the directory roots themselves stay audit-visible.
// This exception belongs only to execution delta auditing, never Work recovery.
func isPrivateRuntimeTransportPath(pathKey string) bool {
	const root = ".specify/runtime/"
	if !strings.HasPrefix(pathKey, root) {
		return false
	}
	privatePath := strings.TrimPrefix(pathKey, root)
	for _, directory := range []string{
		"receipts/", "transactions/", "leases/", "locks/", "artifact-trash/",
		"deep-research/locks/", "test-design/locks/",
	} {
		if strings.HasPrefix(privatePath, directory) {
			return true
		}
	}
	return privatePath == "discussion/mutation.lock"
}

func inspectCommittedWorkspacePaths(ctx context.Context, workspaceRoot, baseCommit string) ([]string, error) {
	if _, err := ReadHeadCommit(ctx, workspaceRoot); err != nil {
		return []string{}, nil
	}
	output, err := runtimecmd.CommandOutputContext(
		ctx,
		workspaceRoot,
		nil,
		"git", "diff", "--name-status", "-z", "--find-renames", baseCommit+"..HEAD",
	)
	if err != nil {
		if contextErr := ctx.Err(); contextErr != nil {
			return nil, contextErr
		}
		return nil, fmt.Errorf("inspect committed workspace delta: %w", err)
	}
	fields := bytes.Split(output, []byte{0})
	seen := make(map[string]string)
	for index := 0; index < len(fields); {
		status := string(fields[index])
		index++
		if status == "" {
			continue
		}
		pathCount := 1
		if strings.HasPrefix(status, "R") || strings.HasPrefix(status, "C") {
			pathCount = 2
		}
		if index+pathCount > len(fields) {
			return nil, fmt.Errorf("Git returned malformed committed path delta")
		}
		for count := 0; count < pathCount; count++ {
			value, key, normalizeErr := normalizeWorkPath(filepath.ToSlash(string(fields[index])), runtime.GOOS == "windows")
			index++
			if normalizeErr != nil {
				return nil, normalizeErr
			}
			seen[key] = value
		}
	}
	paths := make([]string, 0, len(seen))
	for _, path := range seen {
		paths = append(paths, path)
	}
	sort.Strings(paths)
	return paths, nil
}

func workspacePathDigest(workspaceRoot, relativePath string) (string, error) {
	pathValue, _, err := normalizeWorkPath(relativePath, runtime.GOOS == "windows")
	if err != nil {
		return "", err
	}
	absoluteRoot, err := filepath.Abs(workspaceRoot)
	if err != nil {
		return "", err
	}
	absolutePath, err := filepath.Abs(filepath.Join(absoluteRoot, filepath.FromSlash(pathValue)))
	if err != nil {
		return "", err
	}
	rootPrefix := filepath.Clean(absoluteRoot) + string(os.PathSeparator)
	if absolutePath != filepath.Clean(absoluteRoot) && !strings.HasPrefix(filepath.Clean(absolutePath), rootPrefix) {
		return "", fmt.Errorf("%w: workspace digest path escapes root", ErrInvalidArgument)
	}
	info, err := os.Lstat(absolutePath)
	if errors.Is(err, os.ErrNotExist) {
		return "missing", nil
	}
	if err != nil {
		return "", err
	}
	var payload []byte
	switch {
	case info.Mode()&os.ModeSymlink != 0:
		target, readErr := os.Readlink(absolutePath)
		if readErr != nil {
			return "", readErr
		}
		payload = []byte("symlink\x00" + target)
	case info.IsDir():
		payload = []byte("directory")
	default:
		payload, err = os.ReadFile(absolutePath)
		if err != nil {
			return "", err
		}
	}
	digest := sha256.Sum256(payload)
	return hex.EncodeToString(digest[:]), nil
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
