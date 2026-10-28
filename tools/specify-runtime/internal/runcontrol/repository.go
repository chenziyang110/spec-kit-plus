package runcontrol

import (
	"bytes"
	"context"
	"crypto/sha256"
	"database/sql"
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

	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/filelock"
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
	Root               string
	PrimaryRoot        string
	CommonDir          string
	DatabasePath       string
	LegacyDatabasePath string
}

type WorkspaceBaseline struct {
	HeadCommit           string                       `json:"head_commit"`
	DirtyPaths           []string                     `json:"dirty_paths"`
	PathDigests          map[string]string            `json:"path_digests"`
	WorkerPacket         *WorkerPacketBinding         `json:"worker_packet,omitempty"`
	WorkflowControlPlane *WorkflowControlPlaneBinding `json:"workflow_control_plane,omitempty"`
	ScopeAmendments      []ExecutionScopeAmendment    `json:"scope_amendments,omitempty"`
}

type WorkflowControlPlaneBinding struct {
	FeatureRef    string `json:"feature_ref"`
	WorkflowRef   string `json:"workflow_ref"`
	StateSHA256   string `json:"state_sha256,omitempty"`
	Revision      int    `json:"revision"`
	ReceiptRef    string `json:"receipt_ref,omitempty"`
	ReceiptSHA256 string `json:"receipt_sha256,omitempty"`
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
		Root:               root,
		PrimaryRoot:        primaryRoot,
		CommonDir:          commonDir,
		DatabasePath:       filepath.Join(primaryRoot, ".specify", "runtime", "run-control", "run-control.sqlite"),
		LegacyDatabasePath: filepath.Join(commonDir, "specify-runtime", "run-control.sqlite"),
	}, nil
}

// OpenRepository opens the canonical repository-shared run-control store for an
// already resolved repository and performs the one-time legacy snapshot
// migration when the canonical store does not exist yet.
func OpenRepository(ctx context.Context, repository Repository, options ...OpenOption) (*Store, error) {
	canonicalPath, err := resolveCanonicalRepositoryDatabasePath(repository)
	if err != nil {
		return nil, fmt.Errorf("resolve canonical repository run control path: %w", err)
	}
	exists, err := pathExistsForRunControl(canonicalPath)
	if err != nil {
		return nil, fmt.Errorf("inspect canonical repository run control path: %w", err)
	}
	if exists {
		store, err := Open(ctx, canonicalPath, options...)
		if err != nil {
			return nil, fmt.Errorf("open repository run control store: %w", err)
		}
		return store, nil
	}
	legacyPath := filepath.Clean(strings.TrimSpace(repository.LegacyDatabasePath))
	if legacyPath != "" {
		legacyExists, err := pathExistsForRunControl(legacyPath)
		if err != nil {
			return nil, fmt.Errorf("inspect legacy repository run control path: %w", err)
		}
		if legacyExists {
			if err := migrateLegacyRepositoryStore(ctx, repository, canonicalPath, legacyPath, options...); err != nil {
				if isStoreAccessFailure(err) {
					return nil, &StoreAccessError{Stage: "migrate-legacy", Path: canonicalPath, Cause: err}
				}
				return nil, fmt.Errorf("migrate legacy repository run control store: %w", err)
			}
		}
	}
	store, err := Open(ctx, canonicalPath, options...)
	if err != nil {
		return nil, fmt.Errorf("open repository run control store: %w", err)
	}
	return store, nil
}

// OpenForRepository opens the run-control store shared by all worktrees in the
// repository containing cwd.
func OpenForRepository(ctx context.Context, cwd string, options ...OpenOption) (*Store, error) {
	repository, err := ResolveRepository(ctx, cwd)
	if err != nil {
		return nil, err
	}
	return OpenRepository(ctx, repository, options...)
}

// OpenViewForRepository opens a read-only run-control view shared by all
// worktrees in the repository containing cwd.
func OpenViewForRepository(ctx context.Context, cwd string) (*View, error) {
	repository, err := ResolveRepository(ctx, cwd)
	if err != nil {
		return nil, err
	}
	canonicalPath, err := resolveCanonicalRepositoryDatabasePath(repository)
	if err != nil {
		return nil, fmt.Errorf("resolve canonical repository run control path: %w", err)
	}
	canonicalExists, err := pathExistsForRunControl(canonicalPath)
	if err != nil {
		return nil, fmt.Errorf("inspect canonical repository run control path: %w", err)
	}
	if canonicalExists {
		view, err := OpenView(ctx, canonicalPath)
		if err != nil {
			return nil, fmt.Errorf("open repository run control view: %w", err)
		}
		return view, nil
	}
	legacyPath := filepath.Clean(strings.TrimSpace(repository.LegacyDatabasePath))
	if legacyPath != "" {
		legacyExists, err := pathExistsForRunControl(legacyPath)
		if err != nil {
			return nil, fmt.Errorf("inspect legacy repository run control path: %w", err)
		}
		if legacyExists {
			view, err := OpenView(ctx, legacyPath)
			if err != nil {
				return nil, fmt.Errorf("open repository run control view: %w", err)
			}
			return view, nil
		}
	}
	view, err := OpenView(ctx, canonicalPath)
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
		if isRunControlRuntimePath(pathKey) || isWorkflowRuntimeLockPath(pathKey) || isWorkflowMutationReceiptPath(pathKey) {
			return nil
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

func isDoSessionRuntimeLockPath(pathKey string) bool {
	const prefix = ".specify/runtime/receipts/do-locks/"
	if !strings.HasPrefix(pathKey, prefix) || !strings.HasSuffix(pathKey, ".lock") {
		return false
	}
	id := strings.TrimSuffix(strings.TrimPrefix(pathKey, prefix), ".lock")
	if len(id) < 1 || len(id) > 96 {
		return false
	}
	for i, char := range id {
		alphanumeric := char >= 'a' && char <= 'z' || char >= 'A' && char <= 'Z' || char >= '0' && char <= '9'
		if !alphanumeric && (i == 0 || char != '-' && char != '_') {
			return false
		}
	}
	return true
}

func isPrivateRuntimeLockPath(pathKey string) bool {
	if isDoSessionRuntimeLockPath(pathKey) {
		return true
	}
	switch pathKey {
	case ".specify/project-cognition/.update.lock", ".planning/learnings/.learning.lock", ".specify/runtime/locks/playbooks.lock":
		return true
	default:
		return false
	}
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
		if isPrivateRuntimeDeltaPath(pathKey) {
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
		if isPrivateRuntimeDeltaPath(key) {
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
		if isPrivateRuntimeDeltaPath(key) {
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
	if isWorkflowRuntimeLockPath(pathKey) || isWorkflowMutationReceiptPath(pathKey) {
		return true
	}
	const root = ".specify/runtime/"
	if !strings.HasPrefix(pathKey, root) {
		return false
	}
	privatePath := strings.TrimPrefix(pathKey, root)
	for _, directory := range []string{
		"receipts/", "transactions/", "leases/", "locks/", "artifact-trash/",
		"deep-research/locks/", "test-design/locks/", "run-control/",
	} {
		if strings.HasPrefix(privatePath, directory) {
			return true
		}
	}
	return privatePath == "discussion/mutation.lock"
}

func isPrivateRuntimeDeltaPath(pathKey string) bool {
	return isPrivateRuntimeTransportPath(pathKey) || isPrivateRuntimeLockPath(pathKey)
}

func isRunControlRuntimePath(pathKey string) bool {
	const root = ".specify/runtime/run-control/"
	return strings.HasPrefix(pathKey, root)
}

func isWorkflowRuntimeLockPath(pathKey string) bool {
	parts := strings.Split(strings.Trim(pathKey, "/"), "/")
	if len(parts) == 4 && parts[0] == ".specify" && (parts[1] == "features" || parts[1] == "specs") {
		return parts[2] != "" && parts[3] == ".workflow.lock"
	}
	return len(parts) == 3 && parts[0] == "specs" && parts[1] != "" && parts[2] == ".workflow.lock"
}

func isWorkflowMutationReceiptPath(pathKey string) bool {
	const root = ".specify/runtime/workflow-mutations/"
	if !strings.HasPrefix(pathKey, root) {
		return false
	}
	name := strings.TrimPrefix(pathKey, root)
	if len(name) != 69 || !strings.HasSuffix(name, ".json") || strings.Contains(name, "/") {
		return false
	}
	for _, char := range strings.TrimSuffix(name, ".json") {
		if (char < '0' || char > '9') && (char < 'a' || char > 'f') {
			return false
		}
	}
	return true
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
	pathValue, pathKey, err := normalizeWorkPath(relativePath, runtime.GOOS == "windows")
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
	case info.Mode().IsRegular() && isPrivateRuntimeLockPath(pathKey):
		// Exact private lock bytes are operational state, not deliverables.
		// A Windows owner cannot read its own exclusively locked byte. Retain
		// path/existence/type accounting without filtering recovery inspection
		// or neighboring canonical cognition, Learning, or workflow artifacts.
		payload = []byte("private-runtime-lock")
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

func resolveCanonicalRepositoryDatabasePath(repository Repository) (string, error) {
	primaryRoot := strings.TrimSpace(repository.PrimaryRoot)
	if primaryRoot == "" {
		return "", fmt.Errorf("%w: repository primary worktree root is required", ErrInvalidArgument)
	}
	resolvedRoot, err := filepath.Abs(primaryRoot)
	if err != nil {
		return "", fmt.Errorf("resolve repository primary worktree root: %w", err)
	}
	resolvedRoot, err = filepath.EvalSymlinks(resolvedRoot)
	if err != nil {
		return "", fmt.Errorf("resolve repository primary worktree root: %w", err)
	}
	path, err := secureRepositoryProjectPath(resolvedRoot, filepath.ToSlash(filepath.Join(".specify", "runtime", "run-control", "run-control.sqlite")))
	if err != nil {
		return "", err
	}
	if configured := strings.TrimSpace(repository.DatabasePath); configured != "" {
		configuredPath, configErr := filepath.Abs(configured)
		if configErr != nil {
			return "", fmt.Errorf("resolve configured repository run control path: %w", configErr)
		}
		same := filepath.Clean(configuredPath) == filepath.Clean(path)
		if runtime.GOOS == "windows" {
			same = strings.EqualFold(filepath.Clean(configuredPath), filepath.Clean(path))
		}
		if !same {
			return "", fmt.Errorf("%w: configured repository run control path %q does not match canonical path %q", ErrInvalidArgument, configuredPath, path)
		}
	}
	return path, nil
}

func pathExistsForRunControl(path string) (bool, error) {
	info, err := os.Lstat(path)
	if errors.Is(err, os.ErrNotExist) {
		return false, nil
	}
	if err != nil {
		return false, err
	}
	if info.Mode()&os.ModeSymlink != 0 {
		return false, fmt.Errorf("%w: run control path %q must not be a symlink or junction", ErrInvalidArgument, path)
	}
	if !info.Mode().IsRegular() {
		return false, fmt.Errorf("%w: run control path %q must be a regular file", ErrInvalidArgument, path)
	}
	return true, nil
}

func migrateLegacyRepositoryStore(ctx context.Context, repository Repository, canonicalPath, legacyPath string, options ...OpenOption) error {
	if err := ensureSecureRunControlDirectory(repository.PrimaryRoot, filepath.Dir(canonicalPath)); err != nil {
		return fmt.Errorf("prepare canonical run control directory: %w", err)
	}
	lockCandidate := filepath.Join(filepath.Dir(canonicalPath), ".run-control.migrate.lock")
	lockRelative, err := filepath.Rel(repository.PrimaryRoot, lockCandidate)
	if err != nil {
		return fmt.Errorf("resolve run control migration lock: %w", err)
	}
	lockPath, err := secureRepositoryProjectPath(repository.PrimaryRoot, filepath.ToSlash(lockRelative))
	if err != nil {
		return fmt.Errorf("validate run control migration lock: %w", err)
	}
	if info, statErr := os.Lstat(lockPath); statErr == nil && !info.Mode().IsRegular() {
		return fmt.Errorf("%w: run control migration lock %q must be a regular file", ErrInvalidArgument, lockPath)
	} else if statErr != nil && !errors.Is(statErr, os.ErrNotExist) {
		return fmt.Errorf("inspect run control migration lock: %w", statErr)
	}
	release, err := filelock.Acquire(lockPath)
	if err != nil {
		return fmt.Errorf("acquire run control migration lock: %w", err)
	}
	defer release()
	if _, err := secureRepositoryProjectPath(repository.PrimaryRoot, filepath.ToSlash(lockRelative)); err != nil {
		return fmt.Errorf("revalidate run control migration lock: %w", err)
	}
	if info, err := os.Lstat(lockPath); err != nil || !info.Mode().IsRegular() {
		return fmt.Errorf("%w: run control migration lock %q changed during acquisition", ErrInvalidArgument, lockPath)
	}

	exists, err := pathExistsForRunControl(canonicalPath)
	if err != nil {
		return fmt.Errorf("inspect canonical run control store: %w", err)
	}
	if exists {
		return nil
	}
	legacyExists, err := pathExistsForRunControl(legacyPath)
	if err != nil {
		return fmt.Errorf("inspect legacy run control store: %w", err)
	}
	if !legacyExists {
		return nil
	}

	temporaryFile, err := os.CreateTemp(filepath.Dir(canonicalPath), ".run-control-migrate-*.sqlite")
	if err != nil {
		return fmt.Errorf("create migration snapshot path: %w", err)
	}
	temporaryPath := temporaryFile.Name()
	if closeErr := temporaryFile.Close(); closeErr != nil {
		_ = os.Remove(temporaryPath)
		return fmt.Errorf("close migration snapshot path: %w", closeErr)
	}
	if err := os.Remove(temporaryPath); err != nil && !errors.Is(err, os.ErrNotExist) {
		return fmt.Errorf("prepare migration snapshot path: %w", err)
	}
	defer cleanupRunControlSnapshot(temporaryPath)

	if err := copyLegacyRunControlSnapshot(ctx, legacyPath, temporaryPath); err != nil {
		return err
	}
	destination, err := Open(ctx, temporaryPath, options...)
	if err != nil {
		return fmt.Errorf("validate canonical migration store: %w", err)
	}
	if err := checkpointRunControlSnapshot(ctx, destination.db); err != nil {
		_ = destination.Close()
		return err
	}
	if err := destination.Close(); err != nil {
		return fmt.Errorf("close canonical migration store: %w", err)
	}

	exists, err = pathExistsForRunControl(canonicalPath)
	if err != nil {
		return fmt.Errorf("reinspect canonical run control store: %w", err)
	}
	if exists {
		return nil
	}
	if err := os.Rename(temporaryPath, canonicalPath); err != nil {
		return fmt.Errorf("publish canonical run control snapshot: %w", err)
	}
	return nil
}

func ensureSecureRunControlDirectory(primaryRoot, directory string) error {
	resolvedRoot, err := filepath.Abs(strings.TrimSpace(primaryRoot))
	if err != nil {
		return fmt.Errorf("resolve repository primary worktree root: %w", err)
	}
	resolvedRoot, err = filepath.EvalSymlinks(resolvedRoot)
	if err != nil {
		return fmt.Errorf("resolve repository primary worktree root: %w", err)
	}
	relative, err := filepath.Rel(resolvedRoot, directory)
	if err != nil || relative == ".." || strings.HasPrefix(relative, ".."+string(filepath.Separator)) || filepath.IsAbs(relative) {
		return fmt.Errorf("%w: canonical run control directory escapes the primary worktree root", ErrInvalidArgument)
	}
	secureDirectory, err := secureRepositoryProjectPath(resolvedRoot, filepath.ToSlash(relative))
	if err != nil {
		return err
	}
	if err := os.MkdirAll(secureDirectory, 0o755); err != nil {
		return err
	}
	_, err = secureRepositoryProjectPath(resolvedRoot, filepath.ToSlash(relative))
	return err
}

func secureRepositoryProjectPath(projectRoot, relative string) (string, error) {
	root, err := filepath.Abs(projectRoot)
	if err != nil {
		return "", err
	}
	root, err = filepath.EvalSymlinks(root)
	if err != nil {
		return "", err
	}
	candidate := filepath.Join(root, filepath.FromSlash(strings.TrimSpace(relative)))
	candidate, err = filepath.Abs(candidate)
	if err != nil {
		return "", err
	}
	relativeToRoot, err := filepath.Rel(root, candidate)
	if err != nil || relativeToRoot == ".." || strings.HasPrefix(relativeToRoot, ".."+string(filepath.Separator)) || filepath.IsAbs(relativeToRoot) {
		return "", fmt.Errorf("%w: path must stay inside the repository primary worktree", ErrInvalidArgument)
	}
	current := root
	for _, component := range strings.Split(relativeToRoot, string(filepath.Separator)) {
		if component == "" || component == "." {
			continue
		}
		current = filepath.Join(current, component)
		info, statErr := os.Lstat(current)
		if errors.Is(statErr, os.ErrNotExist) {
			break
		}
		if statErr != nil {
			return "", statErr
		}
		if info.Mode()&os.ModeSymlink != 0 {
			return "", fmt.Errorf("%w: project path crosses symlink or junction %q", ErrInvalidArgument, current)
		}
		resolved, resolveErr := filepath.EvalSymlinks(current)
		if resolveErr != nil {
			return "", resolveErr
		}
		resolved, resolveErr = filepath.Abs(resolved)
		if resolveErr != nil {
			return "", resolveErr
		}
		currentAbs, currentErr := filepath.Abs(current)
		if currentErr != nil {
			return "", currentErr
		}
		same := filepath.Clean(resolved) == filepath.Clean(currentAbs)
		if runtime.GOOS == "windows" {
			same = strings.EqualFold(filepath.Clean(resolved), filepath.Clean(currentAbs))
		}
		if !same {
			return "", fmt.Errorf("%w: project path crosses reparse point %q", ErrInvalidArgument, current)
		}
	}
	return candidate, nil
}

func copyLegacyRunControlSnapshot(ctx context.Context, legacyPath, destinationPath string) error {
	source, err := sql.Open("sqlite", sqliteDataSource(legacyPath, "mode=ro"))
	if err != nil {
		return fmt.Errorf("open legacy run control snapshot: %w", err)
	}
	source.SetMaxOpenConns(1)
	source.SetMaxIdleConns(1)
	defer source.Close()
	if _, err := source.ExecContext(ctx, fmt.Sprintf(`PRAGMA busy_timeout = %d`, sqliteBusyTimeoutMS)); err != nil {
		return fmt.Errorf("configure legacy run control snapshot timeout: %w", err)
	}
	// VACUUM INTO reads a transactionally consistent snapshot, preserves
	// retired/unknown history tables, and does not need write access to the
	// legacy Git-administration directory.
	if _, err := source.ExecContext(ctx, `VACUUM INTO ?`, destinationPath); err != nil {
		return fmt.Errorf("snapshot legacy run control store: %w", err)
	}
	return nil
}

func checkpointRunControlSnapshot(ctx context.Context, db *sql.DB) error {
	if _, err := db.ExecContext(ctx, `PRAGMA wal_checkpoint(TRUNCATE)`); err != nil {
		return fmt.Errorf("checkpoint canonical run control snapshot: %w", err)
	}
	return nil
}

func cleanupRunControlSnapshot(databasePath string) {
	for _, path := range []string{
		databasePath,
		databasePath + "-wal",
		databasePath + "-shm",
	} {
		_ = os.Remove(path)
	}
}
