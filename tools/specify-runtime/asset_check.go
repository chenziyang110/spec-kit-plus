package main

import (
	"bytes"
	"context"
	"errors"
	"fmt"
	"net/url"
	"os"
	"os/exec"
	"path"
	"path/filepath"
	"regexp"
	"runtime"
	"sort"
	"strings"
	"time"
	"unicode/utf8"
)

type AssetCheckRequest struct {
	Paths            []string
	DeletedPaths     []string
	Staged           bool
	Base             string
	Head             string
	PolicyPath       string
	IncludeUntracked bool
	PathOnly         bool
}

type assetGitEntry struct {
	mode, object string
	unmerged     bool
}

type assetReadView struct {
	service   *AssetService
	scope     string
	revision  string
	entries   map[string]assetGitEntry
	casePaths map[string][]string
	deleted   map[string]bool
	gitRoot   bool
}

func (service *AssetService) Check(request AssetCheckRequest) Envelope {
	if (request.Base == "") != (request.Head == "") {
		return assetFailure("invalid", "both Git references are required", fmt.Errorf("provide both from-ref and to-ref; a single baseline never falls back to the worktree"))
	}
	if request.Staged && request.Base != "" {
		return assetFailure("invalid", "incompatible asset check scopes", fmt.Errorf("staged and two-reference checks are mutually exclusive"))
	}
	if request.IncludeUntracked && (request.Staged || request.Base != "") {
		return assetFailure("invalid", "untracked files belong to the worktree scope", fmt.Errorf("include-untracked cannot be combined with staged or Git references"))
	}
	if request.PathOnly && (len(request.Paths) == 0 || len(request.DeletedPaths) > 0 || request.Staged || request.Base != "" || request.IncludeUntracked) {
		return assetFailure("invalid", "path-only checks require explicit live paths", fmt.Errorf("use path-only with one or more paths and no Git/deletion scope"))
	}
	view, paths, err := service.assetCheckView(request)
	if err != nil {
		return assetFailure("blocked", "asset check scope could not be read", err)
	}
	policy, err := view.loadPolicy(request.PolicyPath)
	if err != nil {
		return assetFailure("invalid", "asset policy could not be read in the selected scope", err)
	}
	if len(paths) > assetMaxCheckPaths || len(view.deleted) > assetMaxCheckPaths {
		return assetFailure("blocked", "asset check exceeds the bounded scope", fmt.Errorf("select at most %d paths per check", assetMaxCheckPaths))
	}
	issues := []AssetIssue{}
	checked := 0
	contentChecked := 0
	contentBytes := 0
	deferredOwners := []AssetClassification{}
	checkedDocuments := map[string]bool{}
	for _, relative := range paths {
		classification, err := view.classify(relative, policy)
		if err != nil {
			issues = append(issues, AssetIssue{Path: relative, Code: "unsafe-path", Message: err.Error()})
			continue
		}
		checked++
		issues = append(issues, classification.Issues...)
		if request.PathOnly {
			if classification.Protected && classification.Kind != "configuration" {
				issues = append(issues, AssetIssue{Path: relative, Code: "owner-required", Message: "direct writes require the existing owner contract: " + classification.Owner})
			}
			continue
		}
		if classification.Protected {
			deferredOwners = append(deferredOwners, classification)
		}
		if err := view.requireFile(relative); err != nil {
			issues = append(issues, AssetIssue{Path: relative, Code: "unreadable-path", Message: err.Error()})
			continue
		}
		if classification.Temporary || classification.Cache || classification.Kind == "source" {
			continue
		}
		if !assetIsMarkdown(relative) {
			continue
		}
		if classification.Protected && classification.Kind != "workflow-artifact" && !(classification.Kind == "configuration" && !strings.Contains(relative, "/")) {
			continue
		}
		raw, err := view.read(relative, assetMaxContentBytes)
		if err != nil {
			issues = append(issues, AssetIssue{Path: relative, Code: "unreadable-content", Message: err.Error()})
			continue
		}
		contentBytes += len(raw)
		if contentBytes > 16*assetMaxContentBytes {
			return assetFailure("blocked", "asset content check exceeds the bounded scope", fmt.Errorf("split the check into smaller explicit path groups"))
		}
		contentChecked++
		checkedDocuments[relative] = true
		issues = append(issues, view.markdownIssues(relative, raw, policy, nil)...)
	}
	// A removed asset can break an unchanged document. Inspect only persistent
	// Markdown in the selected Git snapshot, never source/templates/fixtures or
	// arbitrary untracked/ignored trees. A bound failure is not a passing check.
	inboundChecked := 0
	if len(view.deleted) > 0 && !request.PathOnly {
		deletions := map[string]bool{}
		for relative := range view.deleted {
			classification, err := view.classify(relative, policy)
			if err != nil {
				issues = append(issues, AssetIssue{Path: relative, Code: "unsafe-deletion-path", Message: err.Error()})
				continue
			}
			if exists, err := view.exists(relative); err != nil {
				issues = append(issues, AssetIssue{Path: relative, Code: "unreadable-deletion-path", Message: err.Error()})
			} else if exists {
				issues = append(issues, AssetIssue{Path: relative, Code: "deletion-still-exists", Message: "a declared deleted path still exists in the selected scope"})
			}
			if classification.Kind != "source" && classification.Kind != "configuration" && !classification.Cache {
				deletions[relative] = true
			}
		}
		if len(deletions) > 0 {
			candidates, err := view.markdownCandidates(request.IncludeUntracked, policy)
			if err != nil {
				return assetFailure("blocked", "deleted-asset references could not be checked", err)
			}
			if len(candidates) > assetMaxCheckPaths {
				return assetFailure("blocked", "deleted-asset reference scope exceeds the inspection limit", fmt.Errorf("at most %d persistent Markdown documents can be inspected in one check", assetMaxCheckPaths))
			}
			for _, relative := range candidates {
				if checkedDocuments[relative] {
					continue
				}
				raw, err := view.read(relative, assetMaxContentBytes)
				if err != nil {
					issues = append(issues, AssetIssue{Path: relative, Code: "unreadable-inbound-reference", Message: err.Error()})
					continue
				}
				contentBytes += len(raw)
				if contentBytes > 16*assetMaxContentBytes {
					return assetFailure("blocked", "deleted-asset reference content exceeds the inspection limit", fmt.Errorf("use a smaller explicit migration/validation scope"))
				}
				inboundChecked++
				issues = append(issues, view.markdownIssues(relative, raw, policy, deletions)...)
			}
		}
	}
	sort.Slice(issues, func(i, j int) bool {
		if issues[i].Path != issues[j].Path {
			return issues[i].Path < issues[j].Path
		}
		if issues[i].Code != issues[j].Code {
			return issues[i].Code < issues[j].Code
		}
		return issues[i].Dependency < issues[j].Dependency
	})
	env := NewEnvelope("ok", "asset policy check passed for the selected scope")
	if request.PathOnly {
		env.Summary = "asset paths checked; contents and dependencies were not inspected"
	}
	for _, issue := range issues {
		env.Items = append(env.Items, issue)
	}
	if len(issues) > 0 {
		env.Status = "blocked"
		env.Summary = "asset policy check found violations"
		env.Blockers = append(env.Blockers, fmt.Sprintf("resolve %d asset policy violation(s)", len(issues)))
	}
	env.Data["scope"] = view.scope
	env.Data["checked"] = checked
	env.Data["content_checked"] = contentChecked
	env.Data["inbound_documents_checked"] = inboundChecked
	env.Data["violation_count"] = len(issues)
	env.Data["path_only"] = request.PathOnly
	env.Data["policy_path"] = policy.PolicyPath
	env.Data["deleted_paths"] = assetSortedKeys(view.deleted)
	if len(deferredOwners) > 0 {
		env.Data["owner_contracts"] = deferredOwners
	}
	if view.revision != "" {
		env.Data["revision"] = view.revision
	}
	return env
}

func (service *AssetService) assetCheckView(request AssetCheckRequest) (*assetReadView, []string, error) {
	view := &assetReadView{service: service, scope: "worktree", deleted: map[string]bool{}}
	if request.PathOnly {
		view.scope = "paths"
	}
	if request.Staged {
		view.scope = "index"
	}
	if request.Base != "" {
		view.scope = "tree"
	}
	needGit := request.Staged || request.Base != "" || (len(request.Paths) == 0 && len(request.DeletedPaths) == 0)
	if needGit {
		if err := view.verifyGitRoot(); err != nil {
			return nil, nil, err
		}
	}
	paths := map[string]bool{}
	for _, requested := range request.Paths {
		relative, err := assetNormalizePath(requested)
		if err != nil {
			return nil, nil, err
		}
		paths[relative] = true
	}
	for _, requested := range request.DeletedPaths {
		relative, err := assetNormalizePath(requested)
		if err != nil {
			return nil, nil, err
		}
		view.deleted[relative] = true
		if paths[relative] {
			return nil, nil, fmt.Errorf("%s cannot be both a current and deleted path", relative)
		}
	}
	base := ""
	if request.Base != "" {
		var err error
		base, err = view.resolveCommit(request.Base)
		if err != nil {
			return nil, nil, fmt.Errorf("invalid from-ref: %w", err)
		}
		view.revision, err = view.resolveCommit(request.Head)
		if err != nil {
			return nil, nil, fmt.Errorf("invalid to-ref: %w", err)
		}
	}
	if view.scope == "index" || view.scope == "tree" {
		if err := view.loadEntries(); err != nil {
			return nil, nil, err
		}
	}
	if len(request.Paths) == 0 && len(request.DeletedPaths) == 0 {
		args := []string{"diff", "--name-status", "-z", "--no-renames", "--no-ext-diff", "--no-textconv", "--ignore-submodules=all"}
		switch view.scope {
		case "tree":
			args = append(args, base, view.revision, "--")
		case "index":
			args = append(args, "--cached", "--")
		default:
			if err := service.assetCheckWorktreeFilterBoundary(); err != nil {
				return nil, nil, err
			}
			head, err := view.resolveCommit("HEAD")
			if err != nil {
				// Only a genuinely unborn branch may use an empty baseline. A bad
				// repository/reference never silently produces an empty change set.
				if _, branchErr := service.assetGit("symbolic-ref", "-q", "HEAD"); branchErr != nil {
					return nil, nil, err
				}
				if _, verifyErr := service.assetGit("rev-parse", "--verify", "HEAD"); verifyErr == nil {
					return nil, nil, err
				}
				staged, readErr := service.assetGit("ls-files", "--cached", "-z")
				if readErr != nil {
					return nil, nil, readErr
				}
				for _, relative := range assetNullFields(staged) {
					paths[relative] = true
				}
				args = append(args, "--")
			} else {
				args = append(args, head, "--")
			}
		}
		raw, err := service.assetGit(args...)
		if err != nil {
			return nil, nil, err
		}
		fields := assetNullFields(raw)
		if len(fields)%2 != 0 {
			return nil, nil, fmt.Errorf("Git returned an invalid change list")
		}
		for i := 0; i < len(fields); i += 2 {
			status, relative := fields[i], fields[i+1]
			if _, err := assetNormalizePath(relative); err != nil {
				return nil, nil, fmt.Errorf("unsafe changed path: %w", err)
			}
			if status == "D" {
				view.deleted[relative] = true
				delete(paths, relative)
			} else {
				paths[relative] = true
			}
			if status == "U" {
				return nil, nil, fmt.Errorf("resolve unmerged index path %s before checking assets", relative)
			}
		}
		if request.IncludeUntracked {
			raw, err := service.assetGit("ls-files", "--others", "--exclude-standard", "-z")
			if err != nil {
				return nil, nil, err
			}
			for _, relative := range assetNullFields(raw) {
				if _, err := assetNormalizePath(relative); err != nil {
					return nil, nil, err
				}
				paths[relative] = true
			}
		}
	}
	return view, assetSortedKeys(paths), nil
}

// Even a name-only diff can run attribute-selected clean/process filters while
// hashing worktree bytes. Do not execute arbitrary project commands or silently
// disable a required conversion. Explicit file reads and immutable index/tree
// comparisons remain available without worktree conversion.
func (service *AssetService) assetCheckWorktreeFilterBoundary() error {
	raw, err := service.assetGit("config", "--null", "--name-only", "--get-regexp", `^filter\..*\.(clean|process)$`)
	if err != nil {
		var exitError *exec.ExitError
		if errors.As(err, &exitError) && exitError.ExitCode() == 1 {
			return nil // git config returns 1 when no matching keys exist.
		}
		return fmt.Errorf("cannot establish a read-only Git worktree scope: %w", err)
	}
	drivers := map[string]bool{}
	if len(raw) > 0 && raw[len(raw)-1] != 0 {
		return fmt.Errorf("cannot establish a read-only Git worktree scope: invalid filter configuration output")
	}
	for _, key := range assetNullFields(raw) {
		separator := strings.LastIndexByte(key, '.')
		if !strings.HasPrefix(key, "filter.") || separator <= len("filter.") || (key[separator+1:] != "clean" && key[separator+1:] != "process") {
			return fmt.Errorf("cannot establish a read-only Git worktree scope: invalid filter configuration key")
		}
		drivers[key[len("filter."):separator]] = true
	}
	if len(drivers) == 0 {
		return nil
	}
	// A globally installed driver (for example Git LFS) does not imply that
	// this project uses it. Attribute inspection reads metadata without running
	// a conversion; do it before any worktree diff can hash filtered content.
	raw, err = service.assetGit("ls-files", "--cached", "--others", "--exclude-standard", "-z")
	if err != nil {
		return fmt.Errorf("cannot establish a read-only Git worktree scope: %w", err)
	}
	if len(raw) > 0 && raw[len(raw)-1] != 0 {
		return fmt.Errorf("cannot establish a read-only Git worktree scope: incomplete file inventory")
	}
	paths := assetNullFields(raw)
	if len(paths) > 100000 {
		return fmt.Errorf("cannot establish a read-only Git worktree scope: file inventory exceeds 100000 paths")
	}
	seen := map[string]bool{}
	unique := make([]string, 0, len(paths))
	var input bytes.Buffer
	for _, relative := range paths {
		if relative == "" {
			return fmt.Errorf("cannot establish a read-only Git worktree scope: empty inventory path")
		}
		if !seen[relative] {
			seen[relative] = true
			unique = append(unique, relative)
			input.WriteString(relative)
			input.WriteByte(0)
		}
	}
	if len(unique) == 0 {
		return nil
	}
	raw, err = service.assetGitWithInput(input.Bytes(), "check-attr", "-z", "--stdin", "filter")
	if err != nil {
		return fmt.Errorf("cannot establish a read-only Git worktree scope: %w", err)
	}
	attributes := assetNullFields(raw)
	if len(raw) == 0 || raw[len(raw)-1] != 0 || len(attributes) != len(unique)*3 {
		return fmt.Errorf("cannot establish a read-only Git worktree scope: incomplete filter attribute results")
	}
	for index, relative := range unique {
		if attributes[index*3] != relative || attributes[index*3+1] != "filter" {
			return fmt.Errorf("cannot establish a read-only Git worktree scope: filter attribute result does not match inventory")
		}
		if drivers[attributes[index*3+2]] {
			return fmt.Errorf("automatic worktree inspection is unavailable because a Git-visible file uses a configured clean/process filter; use explicit --path/--deleted-path inputs, --staged, or a paired --from-ref/--to-ref snapshot check; no filter was executed or disabled")
		}
	}
	return nil
}

func (view *assetReadView) verifyGitRoot() error {
	raw, err := view.service.assetGit("rev-parse", "--show-toplevel")
	if err != nil {
		return fmt.Errorf("Git scope unavailable; provide explicit paths for a non-Git project: %w", err)
	}
	actual, err := filepath.EvalSymlinks(strings.TrimSpace(string(raw)))
	if err != nil {
		return err
	}
	expected, err := filepath.Abs(view.service.projectRoot)
	if err != nil {
		return err
	}
	expected, err = filepath.EvalSymlinks(expected)
	if err != nil {
		return err
	}
	sameRoot := actual == expected
	if runtime.GOOS == "windows" {
		sameRoot = strings.EqualFold(actual, expected)
	}
	if !sameRoot {
		return fmt.Errorf("project root must be the Git worktree root for a Git-scoped asset check")
	}
	view.gitRoot = true
	return nil
}

var assetObjectID = regexp.MustCompile(`^[0-9a-f]{40}(?:[0-9a-f]{24})?$`)

func (view *assetReadView) resolveCommit(ref string) (string, error) {
	if ref == "" || strings.HasPrefix(ref, "-") || strings.ContainsAny(ref, "\x00\r\n") {
		return "", fmt.Errorf("invalid Git reference")
	}
	raw, err := view.service.assetGit("rev-parse", "--verify", "--end-of-options", ref+"^{commit}")
	if err != nil {
		return "", err
	}
	object := strings.TrimSpace(string(raw))
	if !assetObjectID.MatchString(object) {
		return "", fmt.Errorf("Git reference did not resolve to a commit object")
	}
	return object, nil
}

func (view *assetReadView) loadEntries() error {
	if view.entries != nil {
		return nil
	}
	args := []string{"ls-files", "--stage", "-z"}
	if view.scope == "tree" {
		args = []string{"ls-tree", "-r", "-z", "--full-tree", view.revision}
	}
	raw, err := view.service.assetGit(args...)
	if err != nil {
		return err
	}
	view.entries = map[string]assetGitEntry{}
	view.casePaths = map[string][]string{}
	for _, record := range assetNullFields(raw) {
		parts := strings.SplitN(record, "\t", 2)
		if len(parts) != 2 {
			return fmt.Errorf("invalid Git file inventory")
		}
		metadata := strings.Fields(parts[0])
		if len(metadata) != 3 {
			return fmt.Errorf("invalid Git file metadata")
		}
		entry := assetGitEntry{mode: metadata[0]}
		if view.scope == "tree" {
			entry.object = metadata[2]
		} else {
			entry.object = metadata[1]
			entry.unmerged = metadata[2] != "0"
		}
		if !assetObjectID.MatchString(entry.object) {
			return fmt.Errorf("invalid Git object id in asset inventory")
		}
		if old, exists := view.entries[parts[1]]; exists {
			entry.unmerged = entry.unmerged || old.unmerged
		}
		view.entries[parts[1]] = entry
		components := strings.Split(parts[1], "/")
		for i := 1; i <= len(components); i++ {
			prefix := strings.Join(components[:i], "/")
			folded := strings.ToLower(prefix)
			if !assetContains(view.casePaths[folded], prefix) {
				view.casePaths[folded] = append(view.casePaths[folded], prefix)
			}
		}
	}
	return nil
}

func (view *assetReadView) loadPolicy(requested string) (AssetPolicy, error) {
	if view.scope != "index" && view.scope != "tree" {
		return view.service.LoadPolicy(requested)
	}
	explicit := requested != ""
	if !explicit {
		requested = assetDefaultPolicyPath
	}
	relative, err := assetNormalizePath(requested)
	if err != nil {
		return AssetPolicy{}, err
	}
	if _, exists := view.entries[relative]; !exists && !explicit {
		return defaultAssetPolicy(), nil
	}
	raw, err := view.read(relative, assetMaxPolicyBytes)
	if err != nil {
		return AssetPolicy{}, err
	}
	return decodeAssetPolicy(raw, relative)
}

func (view *assetReadView) classify(relative string, policy AssetPolicy) (AssetClassification, error) {
	if normalized, err := assetNormalizePath(relative); err != nil || normalized != relative {
		return AssetClassification{}, fmt.Errorf("path is not normalized and project-relative")
	}
	if view.scope != "index" && view.scope != "tree" {
		return view.service.ClassifyPath(relative, policy)
	}
	classification := classifyAssetPath(relative, policy)
	components := strings.Split(relative, "/")
	for i := 1; i <= len(components); i++ {
		prefix := strings.Join(components[:i], "/")
		if entry, exists := view.entries[prefix]; exists && (entry.mode == "120000" || entry.mode == "160000") {
			return classification, fmt.Errorf("selected snapshot path crosses a symlink or submodule: %s", prefix)
		}
		for _, existing := range view.casePaths[strings.ToLower(prefix)] {
			if existing != prefix {
				classification.Issues = append(classification.Issues, AssetIssue{Path: relative, Code: "case-conflict", Message: "selected snapshot contains a case-conflicting path: " + existing})
				classification.Compliant = false
			}
		}
	}
	return classification, nil
}

func (view *assetReadView) requireFile(relative string) error {
	if view.scope == "index" || view.scope == "tree" {
		entry, exists := view.entries[relative]
		if !exists {
			return fmt.Errorf("file is absent from the selected %s snapshot", view.scope)
		}
		if entry.unmerged {
			return fmt.Errorf("file has unmerged index stages")
		}
		if entry.mode != "100644" && entry.mode != "100755" {
			return fmt.Errorf("selected snapshot entry is not a regular file")
		}
		return nil
	}
	absolute, err := secureProjectPath(view.service.projectRoot, relative)
	if err != nil {
		return err
	}
	info, err := os.Stat(absolute)
	if err != nil {
		return err
	}
	if !info.Mode().IsRegular() {
		return fmt.Errorf("path must name a regular file")
	}
	return nil
}

func (view *assetReadView) read(relative string, limit int64) ([]byte, error) {
	if err := view.requireFile(relative); err != nil {
		return nil, err
	}
	if view.scope == "index" || view.scope == "tree" {
		raw, err := view.service.assetGit("cat-file", "blob", view.entries[relative].object)
		if err != nil {
			return nil, err
		}
		if int64(len(raw)) > limit {
			return nil, fmt.Errorf("snapshot file exceeds %d byte inspection limit", limit)
		}
		return raw, nil
	}
	absolute, err := secureProjectPath(view.service.projectRoot, relative)
	if err != nil {
		return nil, err
	}
	return assetReadLimitedFile(absolute, limit)
}

func (view *assetReadView) exists(relative string) (bool, error) {
	if relative == "." {
		return true, nil
	}
	if _, err := assetNormalizePath(relative); err != nil {
		return false, err
	}
	if view.scope == "index" || view.scope == "tree" {
		components := strings.Split(relative, "/")
		for i := 1; i <= len(components); i++ {
			prefix := strings.Join(components[:i], "/")
			if entry, found := view.entries[prefix]; found && (entry.mode == "120000" || entry.unmerged) {
				return false, fmt.Errorf("dependency crosses a symlink or unresolved index path")
			}
			for _, candidate := range view.casePaths[strings.ToLower(prefix)] {
				if candidate != prefix {
					return false, fmt.Errorf("dependency has a case-conflicting snapshot path: %s", candidate)
				}
			}
		}
		if _, found := view.entries[relative]; found {
			return true, nil
		}
		for file := range view.entries {
			if strings.HasPrefix(file, relative+"/") {
				return true, nil
			}
		}
		return false, nil
	}
	absolute, err := secureProjectPath(view.service.projectRoot, relative)
	if err != nil {
		return false, err
	}
	if err := assetCheckFilesystemCase(view.service.projectRoot, relative); err != nil {
		return false, err
	}
	_, err = os.Stat(absolute)
	if os.IsNotExist(err) {
		return false, nil
	}
	return err == nil, err
}

func (view *assetReadView) markdownCandidates(includeUntracked bool, policy AssetPolicy) ([]string, error) {
	all := map[string]bool{}
	if view.scope == "index" || view.scope == "tree" {
		for relative := range view.entries {
			all[relative] = true
		}
	} else {
		if !view.gitRoot {
			if err := view.verifyGitRoot(); err != nil {
				return nil, err
			}
		}
		raw, err := view.service.assetGit("ls-files", "--cached", "-z")
		if err != nil {
			return nil, err
		}
		for _, relative := range assetNullFields(raw) {
			all[relative] = true
		}
		if includeUntracked {
			raw, err = view.service.assetGit("ls-files", "--others", "--exclude-standard", "-z")
			if err != nil {
				return nil, err
			}
			for _, relative := range assetNullFields(raw) {
				all[relative] = true
			}
		}
	}
	candidates := []string{}
	for relative := range all {
		if view.deleted[relative] || !assetIsMarkdown(relative) {
			continue
		}
		classification := classifyAssetPath(relative, policy)
		if classification.Kind != "document" && classification.Kind != "workflow-artifact" && !(classification.Kind == "configuration" && !strings.Contains(relative, "/")) {
			continue
		}
		if classification.Temporary || classification.Cache {
			continue
		}
		candidates = append(candidates, relative)
	}
	sort.Strings(candidates)
	return candidates, nil
}

func (view *assetReadView) markdownIssues(relative string, raw []byte, policy AssetPolicy, onlyDeleted map[string]bool) []AssetIssue {
	issues := []AssetIssue{}
	if !utf8.Valid(raw) {
		return []AssetIssue{{Path: relative, Code: "invalid-markdown-encoding", Message: "Markdown must be UTF-8 to validate its local dependencies"}}
	}
	seen := map[string]bool{}
	for _, destination := range assetMarkdownDestinations(string(raw)) {
		target, local, err := assetLocalDependency(relative, destination)
		if !local {
			continue
		}
		if onlyDeleted != nil && !onlyDeleted[target] {
			continue
		}
		if err != nil {
			issues = append(issues, AssetIssue{Path: relative, Code: "unsafe-dependency", Message: err.Error(), Dependency: destination})
			continue
		}
		if seen[target] {
			continue
		}
		seen[target] = true
		classification := classifyAssetPath(target, policy)
		if classification.Temporary || classification.Cache || assetUnder(target, ".specify/tmp") || assetUnder(target, ".specify/runtime") || assetUnder(target, ".agent_tmp") || assetUnder(target, ".agent-tmp") || assetUnder(target, ".tmp") || assetUnder(target, "tmp") {
			issues = append(issues, AssetIssue{Path: relative, Code: "ephemeral-dependency", Message: "persistent Markdown must not depend on temporary files or runtime/cache state", Dependency: target})
			continue
		}
		exists, err := view.exists(target)
		if err != nil {
			issues = append(issues, AssetIssue{Path: relative, Code: "unsafe-dependency", Message: err.Error(), Dependency: target})
		} else if !exists {
			issues = append(issues, AssetIssue{Path: relative, Code: "missing-dependency", Message: "local Markdown dependency is missing from the selected scope", Dependency: target})
		}
	}
	return issues
}

func assetIsMarkdown(relative string) bool {
	extension := strings.ToLower(path.Ext(relative))
	return extension == ".md" || extension == ".markdown" || extension == ".mdx"
}

var assetReferenceDefinition = regexp.MustCompile(`^\s{0,3}\[[^\]]+\]:\s*(?:<([^>]+)>|(\S+))`)
var assetHTMLDependency = regexp.MustCompile(`(?i)\b(?:src|href)\s*=\s*["']([^"']+)["']`)
var assetInlineCode = regexp.MustCompile("`+[^`]*`+")

func assetMarkdownDestinations(markdown string) []string {
	destinations := []string{}
	fence := byte(0)
	fenceLength := 0
	visible := []string{}
	for _, line := range strings.Split(markdown, "\n") {
		trimmed := strings.TrimSpace(line)
		if strings.HasPrefix(line, "    ") || strings.HasPrefix(line, "\t") {
			continue
		}
		markerLength := 0
		if len(trimmed) > 0 && (trimmed[0] == '`' || trimmed[0] == '~') {
			for markerLength < len(trimmed) && trimmed[markerLength] == trimmed[0] {
				markerLength++
			}
		}
		if markerLength >= 3 {
			if fence == 0 {
				fence, fenceLength = trimmed[0], markerLength
			} else if fence == trimmed[0] && markerLength >= fenceLength && strings.TrimSpace(trimmed[markerLength:]) == "" {
				fence, fenceLength = 0, 0
			}
			continue
		}
		if fence != 0 {
			continue
		}
		line = assetInlineCode.ReplaceAllString(line, "")
		visible = append(visible, line)
		if match := assetReferenceDefinition.FindStringSubmatch(line); len(match) > 0 {
			destination := match[1]
			if destination == "" {
				destination = match[2]
			}
			destinations = append(destinations, destination)
		}
		for _, match := range assetHTMLDependency.FindAllStringSubmatch(line, -1) {
			destinations = append(destinations, match[1])
		}
	}
	text := strings.Join(visible, "\n")
	for cursor := 0; cursor < len(text); {
		found := strings.Index(text[cursor:], "](")
		if found < 0 {
			break
		}
		cursor += found + 2
		for cursor < len(text) && (text[cursor] == ' ' || text[cursor] == '\t' || text[cursor] == '\n' || text[cursor] == '\r') {
			cursor++
		}
		if cursor >= len(text) {
			break
		}
		if text[cursor] == '<' {
			end := strings.IndexByte(text[cursor+1:], '>')
			if end < 0 {
				break
			}
			destinations = append(destinations, text[cursor+1:cursor+1+end])
			cursor += end + 2
			continue
		}
		start, depth := cursor, 0
		for cursor < len(text) {
			char := text[cursor]
			if char == '\\' && cursor+1 < len(text) {
				cursor += 2
				continue
			}
			if char == '(' {
				depth++
			}
			if char == ')' {
				if depth == 0 {
					break
				}
				depth--
			}
			if (char == ' ' || char == '\t' || char == '\n' || char == '\r') && depth == 0 {
				break
			}
			cursor++
		}
		if cursor > start {
			destinations = append(destinations, text[start:cursor])
		}
		if cursor < len(text) {
			cursor++
		}
	}
	return destinations
}

func assetLocalDependency(source, destination string) (string, bool, error) {
	if destination == "" || strings.HasPrefix(destination, "#") || strings.HasPrefix(destination, "//") {
		return "", false, nil
	}
	destination = strings.ReplaceAll(strings.ReplaceAll(destination, `\(`, "("), `\)`, ")")
	parsed, err := url.Parse(destination)
	if err != nil {
		return "", true, fmt.Errorf("invalid local Markdown link: %w", err)
	}
	if parsed.Scheme != "" {
		if strings.EqualFold(parsed.Scheme, "file") || len(parsed.Scheme) == 1 {
			return "", true, fmt.Errorf("persistent Markdown cannot depend on a machine-local file URL")
		}
		return "", false, nil
	}
	if parsed.Path == "" {
		return "", false, nil
	}
	decoded := parsed.Path // net/url has already decoded percent escapes once.
	if strings.ContainsAny(decoded, "\\\x00") {
		return "", true, fmt.Errorf("local dependency path contains an unsafe separator")
	}
	target := ""
	if strings.HasPrefix(decoded, "/") {
		target = path.Clean(strings.TrimPrefix(decoded, "/"))
	} else {
		target = path.Join(path.Dir(source), decoded)
	}
	if target == "." {
		return target, true, nil
	}
	normalized, err := assetNormalizePath(target)
	if err != nil {
		return "", true, fmt.Errorf("local dependency escapes the project: %w", err)
	}
	return normalized, true, nil
}

type assetLimitedBuffer struct {
	bytes.Buffer
	limit int
}

func (buffer *assetLimitedBuffer) Write(raw []byte) (int, error) {
	if len(raw) > buffer.limit-buffer.Len() {
		return 0, fmt.Errorf("Git output exceeds the bounded asset inspection limit")
	}
	return buffer.Buffer.Write(raw)
}

func (service *AssetService) assetGit(args ...string) ([]byte, error) {
	return service.assetGitWithInput(nil, args...)
}

func (service *AssetService) assetGitWithInput(input []byte, args ...string) ([]byte, error) {
	ctx, cancel := context.WithTimeout(context.Background(), 15*time.Second)
	defer cancel()
	arguments := append([]string{"-C", service.projectRoot, "-c", "core.fsmonitor=false"}, args...)
	command := exec.CommandContext(ctx, "git", arguments...)
	if input != nil {
		command.Stdin = bytes.NewReader(input)
	}
	for _, setting := range os.Environ() {
		if !strings.HasPrefix(setting, "GIT_") {
			command.Env = append(command.Env, setting)
		}
	}
	command.Env = append(command.Env, "GIT_OPTIONAL_LOCKS=0", "GIT_NO_REPLACE_OBJECTS=1", "GIT_TERMINAL_PROMPT=0", "LC_ALL=C")
	stdout := &assetLimitedBuffer{limit: 16 * 1024 * 1024}
	stderr := &assetLimitedBuffer{limit: 16 * 1024}
	command.Stdout = stdout
	command.Stderr = stderr
	if err := command.Run(); err != nil {
		if ctx.Err() != nil {
			return nil, fmt.Errorf("Git asset inspection timed out")
		}
		return nil, fmt.Errorf("Git asset inspection failed: %s: %w", strings.TrimSpace(stderr.String()), err)
	}
	return append([]byte{}, stdout.Bytes()...), nil
}

func assetNullFields(raw []byte) []string {
	if len(raw) == 0 {
		return nil
	}
	return strings.Split(strings.TrimSuffix(string(raw), "\x00"), "\x00")
}

func assetSortedKeys(values map[string]bool) []string {
	keys := make([]string, 0, len(values))
	for key := range values {
		keys = append(keys, key)
	}
	sort.Strings(keys)
	return keys
}
