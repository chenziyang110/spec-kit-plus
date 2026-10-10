package changes

import (
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"testing"

	changemodel "github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/changes/model"
	rt "github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/runtime"
)

// These exercise the real Run entrypoint and existing SQLite-backed fixture.
// Unlike the isolated helper tests, they require the complete runtime module.
func TestRunExplicitBatchPreservesMappedAndNewPathOperations(t *testing.T) {
	root, paths := initChangesFixture(t)
	writeFile(t, root, "src/new.go", "package app\n")
	payload, err := Run(paths, Input{ExplicitPaths: []string{"./src/app.go", "src/new.go", "src/app.go"}})
	if err != nil || payload.Status != "ok" {
		t.Fatalf("Run: payload=%#v err=%v", payload, err)
	}
	if len(payload.Changes) != 2 || payload.Summary.Included != 2 || payload.NextAction != nextPartialRefresh {
		t.Fatalf("duplicate or incomplete explicit-path intake: %#v", payload)
	}
	byPath := map[string]Change{}
	for _, change := range payload.Changes {
		byPath[change.Path] = change
		if len(change.Sources) != 1 || change.Sources[0] != "explicit" || change.WorkingTreeDirty {
			t.Fatalf("explicit-only scope widened: %#v", change)
		}
	}
	mapped := byPath["src/app.go"]
	if !mapped.Tracked || !mapped.KnownToRuntime || mapped.NodeID != "N-app" || mapped.Operation != changemodel.OperationModify {
		t.Fatalf("mapped path changed meaning: %#v", mapped)
	}
	added := byPath["src/new.go"]
	if added.Tracked || added.KnownToRuntime || added.Operation != changemodel.OperationAdd {
		t.Fatalf("untracked path changed meaning: %#v", added)
	}
}

func TestRunExplicitBatchGitFailureBlocksInsteadOfAdopting(t *testing.T) {
	_, paths := initChangesFixture(t)
	index := filepath.Join(t.TempDir(), "invalid-index")
	if err := os.WriteFile(index, []byte("not a Git index\n"), 0o600); err != nil {
		t.Fatal(err)
	}
	// rev-parse still works, but the exact ls-files intake must fail. Never
	// interpret an unreadable index as evidence that requested paths are new.
	t.Setenv("GIT_INDEX_FILE", index)
	payload, err := Run(paths, Input{ExplicitPaths: []string{"src/app.go", "src/new.go"}})
	if err != nil {
		t.Fatal(err)
	}
	if payload.Status != "blocked" || payload.Readiness != rt.BlockedReadiness || payload.NextAction != nextBlocked {
		t.Fatalf("Git failure did not block: %#v", payload)
	}
	if len(payload.Changes) != 0 || len(payload.UnknownPaths) != 0 || !strings.Contains(strings.Join(payload.Errors, " "), "query tracked explicit paths") {
		t.Fatalf("failed lookup leaked adoptable changes or lost diagnostic: %#v", payload)
	}
}

func TestRunExplicitBatchRejectsNULBeforeGit(t *testing.T) {
	_, paths := initChangesFixture(t)
	payload, err := Run(paths, Input{ExplicitPaths: []string{"src/app.go", "src/bad\x00.go"}})
	if err != nil || payload.Status != "blocked" || payload.NextAction != nextBlocked {
		t.Fatalf("invalid path accepted: %#v, %v", payload, err)
	}
	if len(payload.Changes) != 0 || !strings.Contains(strings.Join(payload.Errors, " "), "invalid explicit path") {
		t.Fatalf("NUL was not rejected at the intake boundary: %#v", payload)
	}
}

// This exercises the actual SQLite-backed intake, not only the pure status
// projection. It runs with the complete runtime module and its existing fixture.
func TestRunStagedThenDeletedMappedPathReportsDeletion(t *testing.T) {
	root, paths := initChangesFixture(t)
	writeFile(t, root, "src/app.go", "package app\n\nfunc App() string { return \"staged\" }\n")
	cmd := exec.Command("git", "add", "--", "src/app.go")
	cmd.Dir = root
	if out, err := cmd.CombinedOutput(); err != nil {
		t.Fatalf("git add: %v: %s", err, out)
	}
	if err := os.Remove(filepath.Join(root, "src/app.go")); err != nil {
		t.Fatal(err)
	}
	payload, err := Run(paths, Input{IncludeWorkingTree: true})
	if err != nil || payload.Status != "ok" {
		t.Fatalf("Run: %v, payload=%#v", err, payload)
	}
	if len(payload.Changes) != 1 {
		t.Fatalf("expected one deletion, got %#v", payload.Changes)
	}
	change := payload.Changes[0]
	if change.GitStatus != "MD" || change.Operation != changemodel.OperationDelete || change.ChangeLevel != levelDeletedPath || change.NodeID != "N-app" {
		t.Fatalf("staged-then-deleted mapped path lost its deletion/provenance/owner: %#v", change)
	}
}
