package changes

import (
	"context"
	"os"
	"os/exec"
	"path/filepath"
	"reflect"
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
		{name: "unmerged rejected", code: "UU", includeWorkingTree: true, includeUntracked: true, want: false},
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
