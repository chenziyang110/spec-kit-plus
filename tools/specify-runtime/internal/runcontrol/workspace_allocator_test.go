package runcontrol

import (
	"context"
	"errors"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"testing"
)

func TestPlanGitWorkspaceIsStableAcrossLinkedWorktrees(t *testing.T) {
	mainRoot, linkedRoot := createLinkedRepository(t)
	ctx := context.Background()
	mainRepository, err := ResolveRepository(ctx, mainRoot)
	if err != nil {
		t.Fatal(err)
	}
	linkedRepository, err := ResolveRepository(ctx, linkedRoot)
	if err != nil {
		t.Fatal(err)
	}
	run := Run{RunID: "run/feature:payments A", TargetRef: "HEAD"}

	mainPlan, err := PlanGitWorkspace(ctx, mainRepository, run, 1)
	if err != nil {
		t.Fatal(err)
	}
	linkedPlan, err := PlanGitWorkspace(ctx, linkedRepository, run, 1)
	if err != nil {
		t.Fatal(err)
	}
	if mainPlan != linkedPlan {
		t.Fatalf("workspace plans differ across linked worktrees:\nmain:   %#v\nlinked: %#v", mainPlan, linkedPlan)
	}

	expectedRoot := filepath.Join(mainRepository.CommonDir, "specify-runtime", "worktrees", "runs")
	if !pathIsWithin(expectedRoot, mainPlan.RootPath) {
		t.Fatalf("workspace root %q is outside runtime-owned root %q", mainPlan.RootPath, expectedRoot)
	}
	if !strings.HasPrefix(mainPlan.PrivateRef, "refs/heads/specify/runs/") {
		t.Fatalf("private ref = %q, want refs/heads/specify/runs/...", mainPlan.PrivateRef)
	}
	if !strings.HasPrefix(mainPlan.BaseRef, "refs/heads/") {
		t.Fatalf("base ref = %q, want canonical local branch", mainPlan.BaseRef)
	}
	wantCommit := runGit(t, ensureGitAvailable(t), mainRoot, "rev-parse", "HEAD")
	if mainPlan.BaseCommit != wantCommit {
		t.Fatalf("base commit = %q, want %q", mainPlan.BaseCommit, wantCommit)
	}
	if mainPlan.RepoCommonDir != mainRepository.CommonDir {
		t.Fatalf("common dir = %q, want %q", mainPlan.RepoCommonDir, mainRepository.CommonDir)
	}
	if mainPlan.Generation != 1 || mainPlan.Kind != "git_worktree" || mainPlan.WorkspaceID == "" {
		t.Fatalf("incomplete workspace plan: %#v", mainPlan)
	}

	second, err := PlanGitWorkspace(ctx, mainRepository, run, 2)
	if err != nil {
		t.Fatal(err)
	}
	if second.RootPath == mainPlan.RootPath || second.PrivateRef == mainPlan.PrivateRef || second.WorkspaceID == mainPlan.WorkspaceID {
		t.Fatalf("workspace generation did not receive independent identities: first=%#v second=%#v", mainPlan, second)
	}
}

func TestMaterializeGitWorkspaceCreatesAndReusesVerifiedWorktree(t *testing.T) {
	mainRoot, _ := createLinkedRepository(t)
	ctx := context.Background()
	repository, err := ResolveRepository(ctx, mainRoot)
	if err != nil {
		t.Fatal(err)
	}
	run := Run{RunID: "run_materialize", TargetRef: "HEAD"}
	plan, err := PlanGitWorkspace(ctx, repository, run, 1)
	if err != nil {
		t.Fatal(err)
	}
	workspace := workspaceFromPlan(plan)

	// Allocation must not require, clean, or modify the primary worktree.
	if err := os.WriteFile(filepath.Join(mainRoot, "README.md"), []byte("dirty primary worktree\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	created, err := MaterializeGitWorkspace(ctx, repository, workspace)
	if err != nil {
		t.Fatal(err)
	}
	if created.Status != WorkspaceMaterializationCreated {
		t.Fatalf("first materialization status = %q, want %q", created.Status, WorkspaceMaterializationCreated)
	}

	materializedRepository, err := ResolveRepository(ctx, workspace.RootPath)
	if err != nil {
		t.Fatalf("resolve materialized worktree: %v", err)
	}
	if materializedRepository.Root != workspace.RootPath || materializedRepository.CommonDir != repository.CommonDir {
		t.Fatalf("materialized repository = %#v, want root %q common dir %q", materializedRepository, workspace.RootPath, repository.CommonDir)
	}
	gitPath := ensureGitAvailable(t)
	if branch := runGit(t, gitPath, workspace.RootPath, "symbolic-ref", "HEAD"); branch != workspace.PrivateRef {
		t.Fatalf("materialized branch = %q, want %q", branch, workspace.PrivateRef)
	}
	if head := runGit(t, gitPath, workspace.RootPath, "rev-parse", "HEAD"); head != workspace.BaseCommit {
		t.Fatalf("materialized HEAD = %q, want %q", head, workspace.BaseCommit)
	}
	if status := runGit(t, gitPath, mainRoot, "status", "--short"); !strings.Contains(status, "README.md") {
		t.Fatalf("primary worktree dirty state was lost: %q", status)
	}

	reused, err := MaterializeGitWorkspace(ctx, repository, workspace)
	if err != nil {
		t.Fatal(err)
	}
	if reused.Status != WorkspaceMaterializationExisting {
		t.Fatalf("replayed materialization status = %q, want %q", reused.Status, WorkspaceMaterializationExisting)
	}
}

func TestMaterializeGitWorkspaceRecoversFromPrivateRefOnly(t *testing.T) {
	mainRoot, _ := createLinkedRepository(t)
	ctx := context.Background()
	repository, err := ResolveRepository(ctx, mainRoot)
	if err != nil {
		t.Fatal(err)
	}
	plan, err := PlanGitWorkspace(ctx, repository, Run{RunID: "run_ref_recovery", TargetRef: "HEAD"}, 1)
	if err != nil {
		t.Fatal(err)
	}
	runGit(t, ensureGitAvailable(t), mainRoot, "update-ref", plan.PrivateRef, plan.BaseCommit)

	result, err := MaterializeGitWorkspace(ctx, repository, workspaceFromPlan(plan))
	if err != nil {
		t.Fatal(err)
	}
	if result.Status != WorkspaceMaterializationCreated {
		t.Fatalf("recovered materialization status = %q, want %q", result.Status, WorkspaceMaterializationCreated)
	}
	if branch := runGit(t, ensureGitAvailable(t), plan.RootPath, "symbolic-ref", "HEAD"); branch != plan.PrivateRef {
		t.Fatalf("recovered branch = %q, want %q", branch, plan.PrivateRef)
	}
}

func TestMaterializeGitWorkspaceRejectsTamperedBindingAndExistingDirectory(t *testing.T) {
	mainRoot, _ := createLinkedRepository(t)
	ctx := context.Background()
	repository, err := ResolveRepository(ctx, mainRoot)
	if err != nil {
		t.Fatal(err)
	}
	plan, err := PlanGitWorkspace(ctx, repository, Run{RunID: "run_binding", TargetRef: "HEAD"}, 1)
	if err != nil {
		t.Fatal(err)
	}

	tampered := workspaceFromPlan(plan)
	tampered.PrivateRef = "refs/heads/not-authoritative"
	if _, err := MaterializeGitWorkspace(ctx, repository, tampered); !errors.Is(err, ErrWorkspaceBinding) {
		t.Fatalf("tampered private ref error = %v, want ErrWorkspaceBinding", err)
	}

	if err := os.MkdirAll(plan.RootPath, 0o755); err != nil {
		t.Fatal(err)
	}
	marker := filepath.Join(plan.RootPath, "do-not-delete.txt")
	if err := os.WriteFile(marker, []byte("preserve"), 0o644); err != nil {
		t.Fatal(err)
	}
	if _, err := MaterializeGitWorkspace(ctx, repository, workspaceFromPlan(plan)); !errors.Is(err, ErrWorkspaceConflict) {
		t.Fatalf("conflicting directory error = %v, want ErrWorkspaceConflict", err)
	}
	if content, err := os.ReadFile(marker); err != nil || string(content) != "preserve" {
		t.Fatalf("conflicting directory was modified: content=%q err=%v", content, err)
	}
}

func TestMaterializeGitWorkspaceRejectsSymlinkedOwnedRootBeforeWriting(t *testing.T) {
	mainRoot, _ := createLinkedRepository(t)
	ctx := context.Background()
	repository, err := ResolveRepository(ctx, mainRoot)
	if err != nil {
		t.Fatal(err)
	}
	plan, err := PlanGitWorkspace(ctx, repository, Run{RunID: "run_symlink_escape", TargetRef: "HEAD"}, 1)
	if err != nil {
		t.Fatal(err)
	}

	outside := t.TempDir()
	link := filepath.Join(repository.CommonDir, "specify-runtime")
	if err := os.Symlink(outside, link); err != nil {
		t.Skipf("create directory symlink: %v", err)
	}
	if _, err := MaterializeGitWorkspace(ctx, repository, workspaceFromPlan(plan)); !errors.Is(err, ErrWorkspaceEscape) {
		t.Fatalf("symlinked workspace root error = %v, want ErrWorkspaceEscape", err)
	}
	if _, err := os.Stat(filepath.Join(outside, "worktrees", "runs")); !errors.Is(err, os.ErrNotExist) {
		t.Fatalf("allocator wrote through symlink before rejecting it: %v", err)
	}
}

func TestMaterializeGitWorkspaceSupportsFiveParallelRuns(t *testing.T) {
	mainRoot, _ := createLinkedRepository(t)
	ctx := context.Background()
	repository, err := ResolveRepository(ctx, mainRoot)
	if err != nil {
		t.Fatal(err)
	}

	const count = 5
	plans := make([]CreateWorkspaceParams, count)
	for index := range plans {
		plans[index], err = PlanGitWorkspace(ctx, repository, Run{
			RunID:     "parallel_run_" + string(rune('a'+index)),
			TargetRef: "HEAD",
		}, 1)
		if err != nil {
			t.Fatal(err)
		}
	}

	var wait sync.WaitGroup
	errorsByIndex := make([]error, count)
	for index := range plans {
		wait.Add(1)
		go func(index int) {
			defer wait.Done()
			_, errorsByIndex[index] = MaterializeGitWorkspace(ctx, repository, workspaceFromPlan(plans[index]))
		}(index)
	}
	wait.Wait()
	for index, materializeErr := range errorsByIndex {
		if materializeErr != nil {
			t.Fatalf("parallel materialization %d failed: %v", index, materializeErr)
		}
		if branch := runGit(t, ensureGitAvailable(t), plans[index].RootPath, "symbolic-ref", "HEAD"); branch != plans[index].PrivateRef {
			t.Fatalf("parallel workspace %d branch = %q, want %q", index, branch, plans[index].PrivateRef)
		}
	}
}

func workspaceFromPlan(plan CreateWorkspaceParams) Workspace {
	return Workspace{
		WorkspaceID:   plan.WorkspaceID,
		RunID:         plan.RunID,
		Generation:    plan.Generation,
		Kind:          plan.Kind,
		RootPath:      plan.RootPath,
		RepoCommonDir: plan.RepoCommonDir,
		BaseRef:       plan.BaseRef,
		BaseCommit:    plan.BaseCommit,
		PrivateRef:    plan.PrivateRef,
		Status:        WorkspaceAllocating,
		Revision:      1,
	}
}

func pathIsWithin(root, candidate string) bool {
	relative, err := filepath.Rel(filepath.Clean(root), filepath.Clean(candidate))
	return err == nil && relative != "." && relative != ".." && !strings.HasPrefix(relative, ".."+string(filepath.Separator))
}
