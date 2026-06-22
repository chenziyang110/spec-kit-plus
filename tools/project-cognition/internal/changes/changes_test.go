package changes

import (
	"context"
	"os"
	"os/exec"
	"path/filepath"
	"reflect"
	"strconv"
	"strings"
	"testing"

	rt "github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/runtime"
	"github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/store"
	"github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/update"
)

func TestRunReportsWorkingTreeChangesWithRuntimePathKnowledge(t *testing.T) {
	root, paths := initChangesFixture(t)
	writeFile(t, root, "src/app.go", "package app\n\nfunc App() string { return \"v2\" }\n")

	payload, err := Run(paths, Input{IncludeWorkingTree: true})
	if err != nil {
		t.Fatalf("Run returned error: %v", err)
	}

	if payload.Status != "ok" {
		t.Fatalf("Status = %q, want ok; errors=%v", payload.Status, payload.Errors)
	}
	if payload.BaselineCommit == "" || payload.HeadCommit == "" {
		t.Fatalf("commit fields missing: baseline=%q head=%q", payload.BaselineCommit, payload.HeadCommit)
	}
	if payload.NextAction != "affected_closure" {
		t.Fatalf("NextAction = %q, want affected_closure", payload.NextAction)
	}
	if len(payload.Changes) != 1 {
		t.Fatalf("len(Changes) = %d, want 1; changes=%#v", len(payload.Changes), payload.Changes)
	}
	change := payload.Changes[0]
	if change.Path != "src/app.go" {
		t.Fatalf("Path = %q, want src/app.go", change.Path)
	}
	if !change.KnownToRuntime || change.NodeID != "N-app" {
		t.Fatalf("runtime knowledge = known %v node %q, want true/N-app", change.KnownToRuntime, change.NodeID)
	}
	if change.GitStatus != "M" {
		t.Fatalf("GitStatus = %q, want M", change.GitStatus)
	}
	if change.ChangeLevel != "mapped_change" {
		t.Fatalf("ChangeLevel = %q, want mapped_change", change.ChangeLevel)
	}
}

func TestRunUnsupportedLegacyStatusReturnsBlockedPayload(t *testing.T) {
	root := t.TempDir()
	if err := os.MkdirAll(filepath.Join(root, ".specify", "project-cognition"), 0o755); err != nil {
		t.Fatalf("create runtime dir: %v", err)
	}
	paths, err := rt.ResolvePaths(root)
	if err != nil {
		t.Fatalf("ResolvePaths: %v", err)
	}
	writeFile(t, root, ".specify/project-cognition/status.json", `{"status":"ok"}`)

	payload, err := Run(paths, Input{})
	if err != nil {
		t.Fatalf("Run returned error: %v", err)
	}

	if payload.Status != "blocked" {
		t.Fatalf("Status = %q, want blocked", payload.Status)
	}
	if payload.Readiness != rt.UnsupportedReadiness {
		t.Fatalf("Readiness = %q, want %q", payload.Readiness, rt.UnsupportedReadiness)
	}
	if payload.NextAction != "needs_rebuild" {
		t.Fatalf("NextAction = %q, want needs_rebuild", payload.NextAction)
	}
	if len(payload.Errors) == 0 {
		t.Fatal("Errors is empty, want legacy runtime error")
	}
}

func TestRunGitUnavailableReturnsBlockedPayload(t *testing.T) {
	root := t.TempDir()
	if err := os.MkdirAll(filepath.Join(root, ".specify"), 0o755); err != nil {
		t.Fatalf("create .specify: %v", err)
	}
	paths, err := rt.ResolvePaths(root)
	if err != nil {
		t.Fatalf("ResolvePaths: %v", err)
	}

	payload, err := Run(paths, Input{})
	if err != nil {
		t.Fatalf("Run returned error: %v", err)
	}

	if payload.Status != "blocked" {
		t.Fatalf("Status = %q, want blocked", payload.Status)
	}
	if payload.NextAction != "blocked" {
		t.Fatalf("NextAction = %q, want blocked", payload.NextAction)
	}
	if payload.Readiness != rt.BlockedReadiness {
		t.Fatalf("Readiness = %q, want %q", payload.Readiness, rt.BlockedReadiness)
	}
	if !containsString(payload.Errors, "git repository unavailable") {
		t.Fatalf("Errors = %#v, want git repository unavailable", payload.Errors)
	}
	if len(payload.Changes) != 0 {
		t.Fatalf("Changes = %#v, want none", payload.Changes)
	}
}

func TestRunGitDiffFailureReturnsBlockedReadiness(t *testing.T) {
	_, paths := initChangesFixture(t)

	payload, err := Run(paths, Input{Since: "not-a-commit", Head: "also-not-a-commit"})
	if err != nil {
		t.Fatalf("Run returned error: %v", err)
	}

	if payload.Status != "blocked" {
		t.Fatalf("Status = %q, want blocked", payload.Status)
	}
	if payload.Readiness != rt.BlockedReadiness {
		t.Fatalf("Readiness = %q, want %q", payload.Readiness, rt.BlockedReadiness)
	}
	if payload.NextAction != "blocked" {
		t.Fatalf("NextAction = %q, want blocked", payload.NextAction)
	}
	if len(payload.Errors) == 0 {
		t.Fatal("Errors is empty, want git diff error")
	}
}

func TestRunBlockedRuntimeStatusReturnsBlockedPayload(t *testing.T) {
	_, paths := initChangesFixture(t)
	status, err := rt.ReadStatus(paths)
	if err != nil {
		t.Fatalf("ReadStatus: %v", err)
	}
	status.Status = "blocked"
	status.Readiness = rt.BlockedReadiness
	status.StaleReasons = []string{"manual block"}
	if err := rt.WriteStatus(paths, status); err != nil {
		t.Fatalf("WriteStatus: %v", err)
	}

	payload, err := Run(paths, Input{})
	if err != nil {
		t.Fatalf("Run returned error: %v", err)
	}

	if payload.Status != "blocked" {
		t.Fatalf("Status = %q, want blocked", payload.Status)
	}
	if payload.Readiness != rt.BlockedReadiness {
		t.Fatalf("Readiness = %q, want %q", payload.Readiness, rt.BlockedReadiness)
	}
	if payload.NextAction != "blocked" {
		t.Fatalf("NextAction = %q, want blocked", payload.NextAction)
	}
	if len(payload.Errors) == 0 {
		t.Fatal("Errors is empty, want blocked runtime error")
	}
	if len(payload.Changes) != 0 || len(payload.UnknownPaths) != 0 {
		t.Fatalf("Changes/UnknownPaths = %#v/%#v, want none", payload.Changes, payload.UnknownPaths)
	}
}

func TestRunMissingBaselineEmitsWorkingTreeWarning(t *testing.T) {
	root, paths := initChangesFixture(t)
	status, err := rt.ReadStatus(paths)
	if err != nil {
		t.Fatalf("ReadStatus: %v", err)
	}
	status.Status = "missing"
	status.LastRefreshGitCommit = ""
	if err := rt.WriteStatus(paths, status); err != nil {
		t.Fatalf("WriteStatus: %v", err)
	}
	writeFile(t, root, "src/app.go", "package app\n\nfunc App() string { return \"no-baseline\" }\n")

	payload, err := Run(paths, Input{IncludeWorkingTree: true})
	if err != nil {
		t.Fatalf("Run returned error: %v", err)
	}

	if payload.Status != "ok" {
		t.Fatalf("Status = %q, want ok", payload.Status)
	}
	if !containsString(payload.Warnings, "no refresh git baseline recorded; using working tree status only") {
		t.Fatalf("Warnings = %#v, want missing baseline warning", payload.Warnings)
	}
}

func TestRunFiltersCognitionIgnoredPaths(t *testing.T) {
	root, paths := initChangesFixture(t)
	writeFile(t, root, ".cognitionignore", ".specify/\nscratch/\n")
	runGit(t, root, "add", ".cognitionignore")
	runGit(t, root, "commit", "-m", "ignore scratch")
	if _, err := update.CompleteRefresh(paths, "map-build"); err != nil {
		t.Fatalf("CompleteRefresh after ignore commit: %v", err)
	}
	writeFile(t, root, "scratch/out.log", "generated\n")

	payload, err := Run(paths, Input{IncludeWorkingTree: true, IncludeUntracked: true})
	if err != nil {
		t.Fatalf("Run returned error: %v", err)
	}

	if !containsString(payload.IgnoredPaths, "scratch/out.log") {
		t.Fatalf("IgnoredPaths = %#v, want scratch/out.log", payload.IgnoredPaths)
	}
	if len(payload.Changes) != 0 {
		t.Fatalf("Changes = %#v, want none", payload.Changes)
	}
	if payload.NextAction != "no_op" {
		t.Fatalf("NextAction = %q, want no_op", payload.NextAction)
	}
}

func TestRunAccountsRuntimeBookkeepingPathsAsIgnored(t *testing.T) {
	root, paths := initChangesFixture(t)
	writeFile(t, root, "src/app.go", "package app\n\nfunc App() string { return \"v2\" }\n")

	payload, err := Run(paths, Input{IncludeWorkingTree: true})
	if err != nil {
		t.Fatalf("Run returned error: %v", err)
	}

	if !containsString(payload.IgnoredPaths, ".specify/project-cognition/status.json") {
		t.Fatalf("IgnoredPaths = %#v, want runtime status path accounted as ignored", payload.IgnoredPaths)
	}
	if containsChangePath(payload.Changes, ".specify/project-cognition/status.json") {
		t.Fatalf("Changes = %#v, want runtime status path excluded from changes by cognition ignore", payload.Changes)
	}
	if containsString(payload.UnknownPaths, ".specify/project-cognition/status.json") {
		t.Fatalf("UnknownPaths = %#v, want runtime status path excluded from unknown by cognition ignore", payload.UnknownPaths)
	}
	if payload.Summary.Ignored == 0 {
		t.Fatalf("Summary.Ignored = 0, want ignored runtime status path counted")
	}
}

func TestRunReportsCommitRangeChanges(t *testing.T) {
	root, paths := initChangesFixture(t)
	base := gitHead(t, root)
	writeFile(t, root, "src/app.go", "package app\n\nfunc App() string { return \"v2\" }\n")
	runGit(t, root, "add", "src/app.go")
	runGit(t, root, "commit", "-m", "modify app")
	head := gitHead(t, root)

	payload, err := Run(paths, Input{Since: base, Head: head})
	if err != nil {
		t.Fatalf("Run returned error: %v", err)
	}

	if payload.BaselineCommit != base || payload.HeadCommit != head {
		t.Fatalf("commit fields = %q/%q, want %q/%q", payload.BaselineCommit, payload.HeadCommit, base, head)
	}
	if len(payload.Changes) != 1 {
		t.Fatalf("len(Changes) = %d, want 1; changes=%#v", len(payload.Changes), payload.Changes)
	}
	change := payload.Changes[0]
	if !reflect.DeepEqual(change.Sources, []string{"committed"}) {
		t.Fatalf("Sources = %#v, want committed", change.Sources)
	}
	if change.GitStatus != "M" {
		t.Fatalf("GitStatus = %q, want M", change.GitStatus)
	}
}

func TestRunClassifiesWorkingTreeDeleteAndRenameChanges(t *testing.T) {
	root, paths := initChangesFixture(t)
	writeFile(t, root, "src/zzz.go", "package app\n")
	runGit(t, root, "add", "src/zzz.go")
	runGit(t, root, "commit", "-m", "add rename source")
	base := gitHead(t, root)
	runGit(t, root, "rm", "src/app.go")
	runGit(t, root, "mv", "src/zzz.go", "src/aaa.go")

	payload, err := Run(paths, Input{Since: base, Head: base, IncludeWorkingTree: true})
	if err != nil {
		t.Fatalf("Run returned error: %v", err)
	}

	if payload.Status != "ok" {
		t.Fatalf("Status = %q, want ok", payload.Status)
	}
	if len(payload.Changes) != 2 {
		t.Fatalf("len(Changes) = %d, want 2; changes=%#v", len(payload.Changes), payload.Changes)
	}
	if payload.Changes[0].Path != "src/aaa.go" || payload.Changes[1].Path != "src/app.go" {
		t.Fatalf("changes not sorted by path: %#v", payload.Changes)
	}
	renamed := payload.Changes[0]
	if renamed.OldPath != "src/zzz.go" {
		t.Fatalf("renamed OldPath = %q, want src/zzz.go", renamed.OldPath)
	}
	if renamed.ChangeLevel != "renamed_path" {
		t.Fatalf("renamed ChangeLevel = %q, want renamed_path", renamed.ChangeLevel)
	}
	if !reflect.DeepEqual(renamed.Reason, []string{"changed path lacks active runtime path_index coverage"}) {
		t.Fatalf("renamed Reason = %#v", renamed.Reason)
	}
	deleted := payload.Changes[1]
	if deleted.ChangeLevel != "deleted_path" {
		t.Fatalf("deleted ChangeLevel = %q, want deleted_path", deleted.ChangeLevel)
	}
	if !reflect.DeepEqual(deleted.Reason, []string{"path exists in active runtime path_index"}) {
		t.Fatalf("deleted Reason = %#v", deleted.Reason)
	}
	if payload.Summary.Deleted != 1 || payload.Summary.Renamed != 1 {
		t.Fatalf("summary deleted/renamed = %d/%d, want 1/1", payload.Summary.Deleted, payload.Summary.Renamed)
	}
}

func TestRunOrdersMergedSourcesByDomainOrder(t *testing.T) {
	root, paths := initChangesFixture(t)
	base := gitHead(t, root)
	writeFile(t, root, "src/app.go", "package app\n\nfunc App() string { return \"committed\" }\n")
	runGit(t, root, "add", "src/app.go")
	runGit(t, root, "commit", "-m", "commit app change")
	head := gitHead(t, root)
	writeFile(t, root, "src/app.go", "package app\n\nfunc App() string { return \"working\" }\n")

	payload, err := Run(paths, Input{
		Since:              base,
		Head:               head,
		IncludeWorkingTree: true,
		ExplicitPaths:      []string{"src/app.go"},
	})
	if err != nil {
		t.Fatalf("Run returned error: %v", err)
	}

	if len(payload.Changes) != 1 {
		t.Fatalf("len(Changes) = %d, want 1; changes=%#v", len(payload.Changes), payload.Changes)
	}
	want := []string{"committed", "working_tree", "explicit"}
	if !reflect.DeepEqual(payload.Changes[0].Sources, want) {
		t.Fatalf("Sources = %#v, want %#v", payload.Changes[0].Sources, want)
	}
}

func TestRunMarksUnknownNewPathAsPartialRefresh(t *testing.T) {
	root, paths := initChangesFixture(t)
	writeFile(t, root, "src/new.go", "package app\n")

	payload, err := Run(paths, Input{IncludeWorkingTree: true, IncludeUntracked: true})
	if err != nil {
		t.Fatalf("Run returned error: %v", err)
	}

	if payload.NextAction != "partial_refresh" {
		t.Fatalf("NextAction = %q, want partial_refresh", payload.NextAction)
	}
	if len(payload.Changes) != 1 {
		t.Fatalf("len(Changes) = %d, want 1; changes=%#v", len(payload.Changes), payload.Changes)
	}
	change := payload.Changes[0]
	if change.Path != "src/new.go" {
		t.Fatalf("Path = %q, want src/new.go", change.Path)
	}
	if change.KnownToRuntime {
		t.Fatal("KnownToRuntime = true, want false")
	}
	if change.ChangeLevel != "new_path" {
		t.Fatalf("ChangeLevel = %q, want new_path", change.ChangeLevel)
	}
}

func TestRunIncludeUntrackedOnlySkipsTrackedWorkingTreeChanges(t *testing.T) {
	root, paths := initChangesFixture(t)
	writeFile(t, root, "src/app.go", "package app\n\nfunc App() string { return \"modified\" }\n")
	writeFile(t, root, "src/untracked-only.go", "package app\n")

	payload, err := Run(paths, Input{IncludeUntracked: true})
	if err != nil {
		t.Fatalf("Run returned error: %v", err)
	}

	if !containsChangePath(payload.Changes, "src/untracked-only.go") {
		t.Fatalf("Changes = %#v, want untracked path", payload.Changes)
	}
	if containsChangePath(payload.Changes, "src/app.go") {
		t.Fatalf("Changes = %#v, want tracked modified path skipped", payload.Changes)
	}
}

func TestRunBlocksUnsupportedWorkingTreeStatus(t *testing.T) {
	root, paths := initChangesFixture(t)
	runGit(t, root, "checkout", "-b", "left")
	writeFile(t, root, "src/app.go", "package app\n\nfunc App() string { return \"left\" }\n")
	runGit(t, root, "add", "src/app.go")
	runGit(t, root, "commit", "-m", "left change")
	runGit(t, root, "checkout", "-")
	runGit(t, root, "checkout", "-b", "right")
	writeFile(t, root, "src/app.go", "package app\n\nfunc App() string { return \"right\" }\n")
	runGit(t, root, "add", "src/app.go")
	runGit(t, root, "commit", "-m", "right change")
	runGitAllowFailure(t, root, "merge", "left")

	payload, err := Run(paths, Input{IncludeWorkingTree: true})
	if err != nil {
		t.Fatalf("Run returned error: %v", err)
	}

	if payload.Status != "blocked" {
		t.Fatalf("Status = %q, want blocked", payload.Status)
	}
	if payload.Readiness != rt.BlockedReadiness {
		t.Fatalf("Readiness = %q, want %q", payload.Readiness, rt.BlockedReadiness)
	}
	if payload.NextAction != "blocked" {
		t.Fatalf("NextAction = %q, want blocked", payload.NextAction)
	}
	if len(payload.Errors) == 0 {
		t.Fatal("Errors is empty, want unsupported status error")
	}
	if !strings.Contains(payload.Errors[0], "src/app.go") || !strings.Contains(payload.Errors[0], "UU") {
		t.Fatalf("Errors = %#v, want path and UU status", payload.Errors)
	}
	if len(payload.Changes) != 0 {
		t.Fatalf("Changes = %#v, want none for blocked unsupported status", payload.Changes)
	}
}

func TestIncludeCommittedStatusEntryLimitsCommitRangeStatuses(t *testing.T) {
	tests := []struct {
		code string
		want bool
	}{
		{code: "A", want: true},
		{code: "M", want: true},
		{code: "D", want: true},
		{code: "R", want: true},
		{code: "R100", want: true},
		{code: "R075", want: true},
		{code: "T", want: false},
		{code: "U", want: false},
		{code: "X", want: false},
		{code: "B", want: false},
		{code: "C", want: false},
		{code: "MM", want: false},
		{code: "Rxx", want: false},
		{code: "", want: false},
	}

	for _, tt := range tests {
		t.Run(tt.code, func(t *testing.T) {
			got := includeCommittedStatusEntry(tt.code)
			if got != tt.want {
				t.Fatalf("includeCommittedStatusEntry(%q) = %v, want %v", tt.code, got, tt.want)
			}
		})
	}
}

func TestIncludeStatusEntryLimitsPhaseStatuses(t *testing.T) {
	tests := []struct {
		name               string
		code               string
		includeWorkingTree bool
		includeUntracked   bool
		want               bool
	}{
		{name: "modified with working tree", code: "M", includeWorkingTree: true, want: true},
		{name: "added with working tree", code: "A", includeWorkingTree: true, want: true},
		{name: "deleted with working tree", code: "D", includeWorkingTree: true, want: true},
		{name: "renamed with working tree", code: "R", includeWorkingTree: true, want: true},
		{name: "index and worktree modified with working tree", code: "MM", includeWorkingTree: true, want: true},
		{name: "untracked with include untracked", code: "??", includeUntracked: true, want: true},
		{name: "modified without working tree", code: "M", includeUntracked: true, want: false},
		{name: "untracked without include untracked", code: "??", includeWorkingTree: true, want: false},
		{name: "copied rejected", code: "C", includeWorkingTree: true, includeUntracked: true, want: false},
		{name: "typechange rejected", code: "T", includeWorkingTree: true, includeUntracked: true, want: false},
		{name: "unmerged both deleted rejected", code: "DD", includeWorkingTree: true, includeUntracked: true, want: false},
		{name: "unmerged added by us rejected", code: "AU", includeWorkingTree: true, includeUntracked: true, want: false},
		{name: "unmerged deleted by them rejected", code: "UD", includeWorkingTree: true, includeUntracked: true, want: false},
		{name: "unmerged added by them rejected", code: "UA", includeWorkingTree: true, includeUntracked: true, want: false},
		{name: "unmerged deleted by us rejected", code: "DU", includeWorkingTree: true, includeUntracked: true, want: false},
		{name: "unmerged both added rejected", code: "AA", includeWorkingTree: true, includeUntracked: true, want: false},
		{name: "unmerged both modified rejected", code: "UU", includeWorkingTree: true, includeUntracked: true, want: false},
		{name: "unknown rejected", code: "X", includeWorkingTree: true, includeUntracked: true, want: false},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got := includeStatusEntry(tt.code, tt.includeWorkingTree, tt.includeUntracked)
			if got != tt.want {
				t.Fatalf("includeStatusEntry(%q, %v, %v) = %v, want %v", tt.code, tt.includeWorkingTree, tt.includeUntracked, got, tt.want)
			}
		})
	}
}

func TestIntakeStatusEntryBlocksUnsupportedStatuses(t *testing.T) {
	tests := []struct {
		name               string
		code               string
		includeWorkingTree bool
		includeUntracked   bool
		wantInclude        bool
		wantBlock          bool
	}{
		{name: "unrequested modified skipped", code: "M", includeUntracked: true, wantInclude: false, wantBlock: false},
		{name: "unrequested untracked skipped", code: "??", includeWorkingTree: true, wantInclude: false, wantBlock: false},
		{name: "unsupported copied blocks", code: "C", includeWorkingTree: true, wantInclude: false, wantBlock: true},
		{name: "unsupported typechange blocks", code: "T", includeWorkingTree: true, wantInclude: false, wantBlock: true},
		{name: "conflict blocks", code: "UU", includeWorkingTree: true, wantInclude: false, wantBlock: true},
		{name: "conflict blocks even when only untracked requested", code: "AA", includeUntracked: true, wantInclude: false, wantBlock: true},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			gotInclude, gotBlock := intakeStatusEntry(tt.code, tt.includeWorkingTree, tt.includeUntracked)
			if gotInclude != tt.wantInclude || gotBlock != tt.wantBlock {
				t.Fatalf("intakeStatusEntry(%q, %v, %v) = (%v, %v), want (%v, %v)", tt.code, tt.includeWorkingTree, tt.includeUntracked, gotInclude, gotBlock, tt.wantInclude, tt.wantBlock)
			}
		})
	}
}

func TestRunNeedsRebuildWhenReadyRuntimeDatabaseIsMissingWithNoIncludedChanges(t *testing.T) {
	_, paths := initChangesFixture(t)
	if err := os.Remove(paths.DatabasePath); err != nil {
		t.Fatalf("remove database: %v", err)
	}

	payload, err := Run(paths, Input{})
	if err != nil {
		t.Fatalf("Run returned error: %v", err)
	}

	if payload.Status != "blocked" {
		t.Fatalf("Status = %q, want blocked", payload.Status)
	}
	if payload.Readiness != rt.NeedsRebuildReadiness {
		t.Fatalf("Readiness = %q, want %q", payload.Readiness, rt.NeedsRebuildReadiness)
	}
	if payload.NextAction != "needs_rebuild" {
		t.Fatalf("NextAction = %q, want needs_rebuild", payload.NextAction)
	}
	if len(payload.Errors) == 0 {
		t.Fatal("Errors is empty, want runtime lookup error")
	}
	if len(payload.Changes) != 0 {
		t.Fatalf("Changes = %#v, want none when runtime DB is missing", payload.Changes)
	}
}

func TestRunNeedsRebuildWhenReadyRuntimeDatabaseIsMissing(t *testing.T) {
	root, paths := initChangesFixture(t)
	if err := os.Remove(paths.DatabasePath); err != nil {
		t.Fatalf("remove database: %v", err)
	}
	writeFile(t, root, "src/app.go", "package app\n\nfunc App() string { return \"missing-db\" }\n")

	payload, err := Run(paths, Input{IncludeWorkingTree: true})
	if err != nil {
		t.Fatalf("Run returned error: %v", err)
	}

	if payload.NextAction != "needs_rebuild" {
		t.Fatalf("NextAction = %q, want needs_rebuild", payload.NextAction)
	}
	if payload.Status != "blocked" {
		t.Fatalf("Status = %q, want blocked", payload.Status)
	}
	if payload.Readiness != rt.NeedsRebuildReadiness {
		t.Fatalf("Readiness = %q, want %q", payload.Readiness, rt.NeedsRebuildReadiness)
	}
	if len(payload.Errors) == 0 {
		t.Fatal("Errors is empty, want runtime lookup error")
	}
	if len(payload.Changes) != 0 {
		t.Fatalf("Changes = %#v, want none when runtime DB is unusable", payload.Changes)
	}
}

func TestRunNeedsRebuildWhenStatusIsCorrupt(t *testing.T) {
	root, paths := initChangesFixture(t)
	writeFile(t, root, ".specify/project-cognition/status.json", "{not-json")

	payload, err := Run(paths, Input{IncludeWorkingTree: true})
	if err != nil {
		t.Fatalf("Run returned error: %v", err)
	}

	if payload.Status != "blocked" {
		t.Fatalf("Status = %q, want blocked", payload.Status)
	}
	if payload.Readiness != rt.NeedsRebuildReadiness {
		t.Fatalf("Readiness = %q, want %q", payload.Readiness, rt.NeedsRebuildReadiness)
	}
	if payload.NextAction != "needs_rebuild" {
		t.Fatalf("NextAction = %q, want needs_rebuild", payload.NextAction)
	}
	if len(payload.Errors) == 0 {
		t.Fatal("Errors is empty, want status parse error")
	}
	if len(payload.Warnings) != 0 || len(payload.Changes) != 0 || len(payload.IgnoredPaths) != 0 || len(payload.UnknownPaths) != 0 {
		t.Fatalf("payload slices = warnings %#v changes %#v ignored %#v unknown %#v, want all empty", payload.Warnings, payload.Changes, payload.IgnoredPaths, payload.UnknownPaths)
	}
}

func TestRunNeedsRebuildWhenReadyRuntimeDatabaseIsCorrupt(t *testing.T) {
	root, paths := initChangesFixture(t)
	writeFile(t, root, ".specify/project-cognition/project-cognition.db", "not a sqlite database")
	writeFile(t, root, "src/app.go", "package app\n\nfunc App() string { return \"corrupt-db\" }\n")

	payload, err := Run(paths, Input{IncludeWorkingTree: true})
	if err != nil {
		t.Fatalf("Run returned error: %v", err)
	}

	if payload.Status != "blocked" {
		t.Fatalf("Status = %q, want blocked", payload.Status)
	}
	if payload.Readiness != rt.NeedsRebuildReadiness {
		t.Fatalf("Readiness = %q, want %q", payload.Readiness, rt.NeedsRebuildReadiness)
	}
	if payload.NextAction != "needs_rebuild" {
		t.Fatalf("NextAction = %q, want needs_rebuild", payload.NextAction)
	}
	if len(payload.Errors) == 0 {
		t.Fatal("Errors is empty, want runtime lookup error")
	}
	if len(payload.Changes) != 0 {
		t.Fatalf("Changes = %#v, want none when runtime DB is corrupt", payload.Changes)
	}
}

func TestRunNeedsRebuildWhenReadyRuntimeDatabaseIsCorruptWithOnlyIgnoredChanges(t *testing.T) {
	root, paths := initChangesFixture(t)
	writeFile(t, root, ".cognitionignore", ".specify/\nscratch/\n")
	writeFile(t, root, ".specify/project-cognition/project-cognition.db", "not a sqlite database")
	writeFile(t, root, "scratch/out.log", "ignored\n")

	payload, err := Run(paths, Input{IncludeUntracked: true})
	if err != nil {
		t.Fatalf("Run returned error: %v", err)
	}

	if payload.Status != "blocked" {
		t.Fatalf("Status = %q, want blocked", payload.Status)
	}
	if payload.Readiness != rt.NeedsRebuildReadiness {
		t.Fatalf("Readiness = %q, want %q", payload.Readiness, rt.NeedsRebuildReadiness)
	}
	if payload.NextAction != "needs_rebuild" {
		t.Fatalf("NextAction = %q, want needs_rebuild", payload.NextAction)
	}
	if len(payload.Errors) == 0 {
		t.Fatal("Errors is empty, want runtime lookup error")
	}
	if len(payload.Changes) != 0 {
		t.Fatalf("Changes = %#v, want none when only ignored paths changed", payload.Changes)
	}
	if !containsString(payload.IgnoredPaths, "scratch/out.log") {
		t.Fatalf("IgnoredPaths = %#v, want ignored scratch path preserved", payload.IgnoredPaths)
	}
}

func TestRunMarksUntrackedExplicitPathAsUntracked(t *testing.T) {
	root, paths := initChangesFixture(t)
	writeFile(t, root, "src/new-explicit.go", "package app\n")

	payload, err := Run(paths, Input{ExplicitPaths: []string{"src/new-explicit.go"}})
	if err != nil {
		t.Fatalf("Run returned error: %v", err)
	}

	if len(payload.Changes) != 1 {
		t.Fatalf("len(Changes) = %d, want 1; changes=%#v", len(payload.Changes), payload.Changes)
	}
	change := payload.Changes[0]
	if change.Path != "src/new-explicit.go" {
		t.Fatalf("Path = %q, want src/new-explicit.go", change.Path)
	}
	if change.Tracked {
		t.Fatalf("Tracked = true, want false for untracked explicit path")
	}
	if change.GitStatus != "explicit" {
		t.Fatalf("GitStatus = %q, want explicit", change.GitStatus)
	}
	if !reflect.DeepEqual(change.Sources, []string{"explicit"}) {
		t.Fatalf("Sources = %#v, want explicit", change.Sources)
	}
}

func TestRunConvertsAbsoluteExplicitPathUnderRoot(t *testing.T) {
	root, paths := initChangesFixture(t)
	absolutePath := filepath.Join(root, "src", "app.go")

	payload, err := Run(paths, Input{ExplicitPaths: []string{absolutePath}})
	if err != nil {
		t.Fatalf("Run returned error: %v", err)
	}

	if payload.Status != "ok" {
		t.Fatalf("Status = %q, want ok; errors=%#v", payload.Status, payload.Errors)
	}
	if len(payload.Changes) != 1 {
		t.Fatalf("len(Changes) = %d, want 1; changes=%#v", len(payload.Changes), payload.Changes)
	}
	if payload.Changes[0].Path != "src/app.go" {
		t.Fatalf("Path = %q, want src/app.go", payload.Changes[0].Path)
	}
}

func TestRunBlocksInvalidExplicitPaths(t *testing.T) {
	_, paths := initChangesFixture(t)
	outsideRoot := t.TempDir()
	tests := []struct {
		name string
		path string
	}{
		{name: "absolute outside root", path: filepath.Join(outsideRoot, "outside.go")},
		{name: "parent traversal", path: "../outside.go"},
		{name: "glob", path: "src/*.go"},
		{name: "runtime path", path: ".specify/project-cognition/status.json"},
		{name: "dot", path: "."},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			payload, err := Run(paths, Input{ExplicitPaths: []string{tt.path}})
			if err != nil {
				t.Fatalf("Run returned error: %v", err)
			}

			if payload.Status != "blocked" {
				t.Fatalf("Status = %q, want blocked", payload.Status)
			}
			if payload.Readiness != rt.BlockedReadiness {
				t.Fatalf("Readiness = %q, want %q", payload.Readiness, rt.BlockedReadiness)
			}
			if payload.NextAction != "blocked" {
				t.Fatalf("NextAction = %q, want blocked", payload.NextAction)
			}
			if len(payload.Errors) == 0 || !strings.Contains(payload.Errors[0], strconv.Quote(tt.path)) {
				t.Fatalf("Errors = %#v, want invalid path %q", payload.Errors, tt.path)
			}
			if len(payload.Changes) != 0 {
				t.Fatalf("Changes = %#v, want none", payload.Changes)
			}
		})
	}
}

func initChangesFixture(t *testing.T) (string, rt.Paths) {
	t.Helper()
	root := t.TempDir()
	if err := os.MkdirAll(filepath.Join(root, ".specify"), 0o755); err != nil {
		t.Fatalf("create .specify: %v", err)
	}
	writeFile(t, root, ".cognitionignore", ".specify/\n")
	writeFile(t, root, "src/app.go", "package app\n\nfunc App() string { return \"v1\" }\n")
	paths, err := rt.ResolvePaths(root)
	if err != nil {
		t.Fatalf("ResolvePaths: %v", err)
	}
	seedRuntimePathIndex(t, paths)
	status := rt.DefaultStatus(paths)
	status.Status = "ok"
	status.Freshness = rt.ReadyFreshness
	status.Readiness = rt.ReadyReadiness
	status.GraphReady = true
	status.ActiveGenerationID = "GEN-changes"
	status.BaselineKind = rt.BaselineKindBrownfieldFull
	if err := rt.WriteStatus(paths, status); err != nil {
		t.Fatalf("WriteStatus: %v", err)
	}
	runGit(t, root, "init")
	runGit(t, root, "config", "user.email", "test@example.com")
	runGit(t, root, "config", "user.name", "Test User")
	runGit(t, root, "add", ".")
	runGit(t, root, "commit", "-m", "baseline")
	if _, err := update.CompleteRefresh(paths, "map-build"); err != nil {
		t.Fatalf("CompleteRefresh: %v", err)
	}
	return root, paths
}

func seedRuntimePathIndex(t *testing.T, paths rt.Paths) {
	t.Helper()
	st, err := store.Open(paths)
	if err != nil {
		t.Fatalf("store.Open: %v", err)
	}
	defer st.Close()
	if _, err := st.ImportGeneration(context.Background(), store.ImportInput{
		GenerationID: "GEN-changes",
		Kind:         "full",
		SourceCommit: "abc123",
		Evidence: []store.EvidenceImport{{
			ID:          "E-app",
			SourceKind:  "file",
			SourcePath:  "src/app.go",
			CommitSHA:   "abc123",
			Extractor:   "test",
			ContentHash: "hash-app",
		}},
		Nodes: []store.NodeImport{{
			ID:          "N-app",
			Type:        "capability",
			Title:       "App",
			Confidence:  "verified",
			EvidenceIDs: []string{"E-app"},
		}},
		PathIndex: []store.PathIndexImport{{
			ID:         "P-app",
			Path:       "src/app.go",
			NodeID:     "N-app",
			Relation:   "owns",
			Confidence: "verified",
			EvidenceID: "E-app",
		}},
		Aliases: []store.AliasImport{{
			ID:              "ALIAS-app",
			Alias:           "App",
			NormalizedAlias: "app",
			TargetType:      "node",
			TargetID:        "N-app",
			Language:        "go",
			Source:          "node_title",
			Confidence:      "verified",
			EvidenceID:      "E-app",
		}},
	}); err != nil {
		t.Fatalf("ImportGeneration: %v", err)
	}
	if _, _, err := st.PublishRuntimeMetadata(context.Background(), "GEN-changes", rt.BaselineKindBrownfieldFull); err != nil {
		t.Fatalf("PublishRuntimeMetadata: %v", err)
	}
}

func writeFile(t *testing.T, root string, rel string, content string) {
	t.Helper()
	path := filepath.Join(root, filepath.FromSlash(rel))
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		t.Fatalf("create parent for %s: %v", rel, err)
	}
	if err := os.WriteFile(path, []byte(content), 0o644); err != nil {
		t.Fatalf("write %s: %v", rel, err)
	}
}

func runGit(t *testing.T, root string, args ...string) string {
	t.Helper()
	cmd := exec.Command("git", args...)
	cmd.Dir = root
	output, err := cmd.CombinedOutput()
	if err != nil {
		t.Fatalf("git %v failed: %v\n%s", args, err, output)
	}
	return string(output)
}

func runGitAllowFailure(t *testing.T, root string, args ...string) string {
	t.Helper()
	cmd := exec.Command("git", args...)
	cmd.Dir = root
	output, _ := cmd.CombinedOutput()
	return string(output)
}

func gitHead(t *testing.T, root string) string {
	t.Helper()
	head, err := rt.GitHead(root)
	if err != nil {
		t.Fatalf("GitHead: %v", err)
	}
	return head
}

func containsString(values []string, want string) bool {
	for _, value := range values {
		if value == want {
			return true
		}
	}
	return false
}

func containsChangePath(changes []Change, want string) bool {
	for _, change := range changes {
		if change.Path == want {
			return true
		}
	}
	return false
}
