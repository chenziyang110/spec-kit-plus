package runcontrol

import (
	"context"
	"errors"
	"fmt"
	"path/filepath"
	"sync"
	"testing"
	"time"
)

func TestWorkBoardBeginPersistsTaskAndDeclaredWriteIntents(t *testing.T) {
	ctx := context.Background()
	databasePath := filepath.Join(t.TempDir(), "run-control.sqlite")
	store := openTestStore(t, databasePath)
	now := time.Now().UTC()

	created, intents, err := store.BeginWork(ctx, BeginWorkParams{
		WorkID:        "work-auth-refresh",
		Summary:       "Refresh authentication tokens safely",
		AgentID:       "codex-thread-a",
		AdapterID:     "codex",
		WorkspaceRoot: filepath.Join(t.TempDir(), "workspace"),
		BaseCommit:    "abc123",
		LeaseUntil:    now.Add(30 * time.Minute),
		WriteIntents: []WriteIntentSpec{
			{
				Path:       "src/auth/token.go",
				Operation:  WriteModify,
				Reason:     "add refresh-token rotation",
				Confidence: IntentConfirmed,
			},
		},
	})
	if err != nil {
		t.Fatal(err)
	}
	if created.Status != WorkActive || created.Fence != 1 || created.Revision != 1 {
		t.Fatalf("created work = %#v, want active revision 1 fence 1", created)
	}
	if len(intents) != 1 || intents[0].Path != "src/auth/token.go" || intents[0].Status != WriteIntentActive {
		t.Fatalf("created intents = %#v", intents)
	}
	if err := store.Close(); err != nil {
		t.Fatal(err)
	}

	reopened := openTestStore(t, databasePath)
	loaded, loadedIntents, err := reopened.GetWork(ctx, created.WorkID)
	if err != nil {
		t.Fatal(err)
	}
	if loaded.Summary != created.Summary || loaded.AgentID != created.AgentID || loaded.LeaseUntilMS != created.LeaseUntilMS {
		t.Fatalf("reopened work = %#v, want %#v", loaded, created)
	}
	if len(loadedIntents) != 1 || loadedIntents[0].Reason != "add refresh-token rotation" {
		t.Fatalf("reopened intents = %#v", loadedIntents)
	}
}

func TestWorkBoardIsSharedAcrossLinkedWorktrees(t *testing.T) {
	ctx := context.Background()
	mainRoot, linkedRoot := createLinkedRepository(t)
	mainStore, err := OpenForRepository(ctx, mainRoot)
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { _ = mainStore.Close() })
	created, _, err := mainStore.BeginWork(ctx, BeginWorkParams{
		WorkID: "work-main-tree", Summary: "shared task", AgentID: "agent-main", AdapterID: "codex",
		WorkspaceRoot: mainRoot, BaseCommit: "base", LeaseUntil: time.Now().UTC().Add(time.Hour),
		WriteIntents: []WriteIntentSpec{{
			Path: "src/shared.go", Operation: WriteModify, Reason: "shared edit", Confidence: IntentConfirmed,
		}},
	})
	if err != nil {
		t.Fatal(err)
	}

	linkedView, err := OpenViewForRepository(ctx, linkedRoot)
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { _ = linkedView.Close() })
	loaded, intents, err := linkedView.GetWork(ctx, created.WorkID)
	if err != nil {
		t.Fatal(err)
	}
	if loaded.WorkID != created.WorkID || len(intents) != 1 || intents[0].Path != "src/shared.go" {
		t.Fatalf("linked worktree board item = %#v intents=%#v", loaded, intents)
	}
}

func TestWorkBoardRejectsSameAndAncestorWriteIntentConflicts(t *testing.T) {
	ctx := context.Background()
	store := openTestStore(t, filepath.Join(t.TempDir(), "run-control.sqlite"))
	now := time.Now().UTC()
	workspace := filepath.Join(t.TempDir(), "workspace")

	_, _, err := store.BeginWork(ctx, BeginWorkParams{
		WorkID: "work-auth", Summary: "auth changes", AgentID: "agent-a", AdapterID: "codex",
		WorkspaceRoot: workspace, BaseCommit: "base", LeaseUntil: now.Add(time.Hour),
		WriteIntents: []WriteIntentSpec{{
			Path: "src/auth", Operation: WriteModify, Reason: "auth refactor", Confidence: IntentConfirmed,
		}},
	})
	if err != nil {
		t.Fatal(err)
	}

	_, _, err = store.BeginWork(ctx, BeginWorkParams{
		WorkID: "work-login", Summary: "login changes", AgentID: "agent-b", AdapterID: "codex",
		WorkspaceRoot: workspace, BaseCommit: "base", LeaseUntil: now.Add(time.Hour),
		WriteIntents: []WriteIntentSpec{{
			Path: "src/auth/login/view.tsx", Operation: WriteModify, Reason: "login UI", Confidence: IntentConfirmed,
		}},
	})
	var conflict *WorkIntentConflictError
	if !errors.As(err, &conflict) || !errors.Is(err, ErrWorkIntentConflict) {
		t.Fatalf("ancestor conflict error = %v, want typed work intent conflict", err)
	}
	if len(conflict.Conflicts) != 1 || conflict.Conflicts[0].OwnerWorkID != "work-auth" {
		t.Fatalf("ancestor conflicts = %#v", conflict.Conflicts)
	}

	_, _, err = store.BeginWork(ctx, BeginWorkParams{
		WorkID: "work-billing", Summary: "billing changes", AgentID: "agent-c", AdapterID: "codex",
		WorkspaceRoot: workspace, BaseCommit: "base", LeaseUntil: now.Add(time.Hour),
		WriteIntents: []WriteIntentSpec{{
			Path: "src/billing/invoice.ts", Operation: WriteModify, Reason: "invoice flow", Confidence: IntentConfirmed,
		}},
	})
	if err != nil {
		t.Fatalf("sibling scope should not conflict: %v", err)
	}
}

func TestWorkBoardConcurrentConfirmedClaimsHaveExactlyOneOwner(t *testing.T) {
	ctx := context.Background()
	databasePath := filepath.Join(t.TempDir(), "run-control.sqlite")
	firstStore := openTestStore(t, databasePath)
	secondStore := openTestStore(t, databasePath)
	workspace := filepath.Join(t.TempDir(), "workspace")
	leaseUntil := time.Now().UTC().Add(time.Hour)

	type beginResult struct {
		work WorkItem
		err  error
	}
	results := make(chan beginResult, 2)
	start := make(chan struct{})
	var wait sync.WaitGroup
	for index, store := range []*Store{firstStore, secondStore} {
		wait.Add(1)
		go func(index int, store *Store) {
			defer wait.Done()
			<-start
			work, _, err := store.BeginWork(ctx, BeginWorkParams{
				WorkID:        fmt.Sprintf("work-concurrent-%d", index),
				Summary:       "concurrent owner",
				AgentID:       fmt.Sprintf("agent-%d", index),
				AdapterID:     "codex",
				WorkspaceRoot: workspace,
				BaseCommit:    "base",
				LeaseUntil:    leaseUntil,
				WriteIntents: []WriteIntentSpec{{
					Path: "src/shared.go", Operation: WriteModify, Reason: "shared edit", Confidence: IntentConfirmed,
				}},
			})
			results <- beginResult{work: work, err: err}
		}(index, store)
	}
	close(start)
	wait.Wait()
	close(results)

	successes := 0
	conflicts := 0
	for result := range results {
		switch {
		case result.err == nil:
			successes++
			if result.work.WorkID == "" {
				t.Fatal("successful concurrent claim returned an empty work id")
			}
		case errors.Is(result.err, ErrWorkIntentConflict):
			conflicts++
		default:
			t.Fatalf("concurrent claim error = %v, want a typed conflict", result.err)
		}
	}
	if successes != 1 || conflicts != 1 {
		t.Fatalf("concurrent claims = %d successes and %d conflicts, want exactly one of each", successes, conflicts)
	}
}

func TestWorkBoardNormalizesEquivalentPathsForConflictChecks(t *testing.T) {
	pathValue, pathKey, err := normalizeWorkPath(`.\src\\Auth\..\Auth\Token.ts`, true)
	if err != nil {
		t.Fatal(err)
	}
	if pathValue != "src/Auth/Token.ts" || pathKey != "src/auth/token.ts" {
		t.Fatalf("normalized path/key = %q / %q", pathValue, pathKey)
	}
	if !workPathsOverlap("src/auth", "src/auth/token.ts") {
		t.Fatal("ancestor and child paths should overlap")
	}
	if workPathsOverlap("src/auth", "src/author.ts") {
		t.Fatal("path-prefix siblings must not overlap")
	}
	if _, _, err := normalizeWorkPath("../outside.go", false); !errors.Is(err, ErrInvalidArgument) {
		t.Fatalf("escaping path error = %v, want invalid argument", err)
	}
}

func TestWorkBoardScopeExpansionIsAtomicAndReportsOwner(t *testing.T) {
	ctx := context.Background()
	store := openTestStore(t, filepath.Join(t.TempDir(), "run-control.sqlite"))
	now := time.Now().UTC()
	workspace := filepath.Join(t.TempDir(), "workspace")

	owner, _, err := store.BeginWork(ctx, BeginWorkParams{
		WorkID: "work-owner", Summary: "owns shared config", AgentID: "agent-a", AdapterID: "codex",
		WorkspaceRoot: workspace, BaseCommit: "base", LeaseUntil: now.Add(time.Hour),
		WriteIntents: []WriteIntentSpec{{
			Path: "config/runtime.yaml", Operation: WriteModify, Reason: "runtime config", Confidence: IntentConfirmed,
		}},
	})
	if err != nil {
		t.Fatal(err)
	}
	requester, _, err := store.BeginWork(ctx, BeginWorkParams{
		WorkID: "work-requester", Summary: "owns app", AgentID: "agent-b", AdapterID: "codex",
		WorkspaceRoot: workspace, BaseCommit: "base", LeaseUntil: now.Add(time.Hour),
		WriteIntents: []WriteIntentSpec{{
			Path: "src/app.go", Operation: WriteModify, Reason: "app update", Confidence: IntentConfirmed,
		}},
	})
	if err != nil {
		t.Fatal(err)
	}

	_, _, err = store.AddWorkIntent(ctx, AddWorkIntentParams{
		WorkID:           requester.WorkID,
		ExpectedRevision: requester.Revision,
		Fence:            requester.Fence,
		Spec: WriteIntentSpec{
			Path: "config", Operation: WriteModify, Reason: "discovered config dependency", Confidence: IntentConfirmed,
		},
	})
	var conflict *WorkIntentConflictError
	if !errors.As(err, &conflict) || len(conflict.Conflicts) != 1 || conflict.Conflicts[0].OwnerWorkID != owner.WorkID {
		t.Fatalf("scope expansion error = %v conflicts %#v", err, conflict)
	}
	loaded, intents, loadErr := store.GetWork(ctx, requester.WorkID)
	if loadErr != nil {
		t.Fatal(loadErr)
	}
	if loaded.Revision != requester.Revision || len(intents) != 1 {
		t.Fatalf("failed expansion mutated requester: work %#v intents %#v", loaded, intents)
	}
}

func TestWorkBoardClaimIntentsIsAllOrNothing(t *testing.T) {
	ctx := context.Background()
	store := openTestStore(t, filepath.Join(t.TempDir(), "run-control.sqlite"))
	now := time.Now().UTC()
	workspace := filepath.Join(t.TempDir(), "workspace")

	_, _, err := store.BeginWork(ctx, BeginWorkParams{
		WorkID: "work-owner", Summary: "owns shared config", AgentID: "agent-a", AdapterID: "codex",
		WorkspaceRoot: workspace, BaseCommit: "base", LeaseUntil: now.Add(time.Hour),
		WriteIntents: []WriteIntentSpec{{
			Path: "src/shared", Operation: WriteModify, Reason: "shared source", Confidence: IntentConfirmed,
		}},
	})
	if err != nil {
		t.Fatal(err)
	}
	requester, _, err := store.BeginWork(ctx, BeginWorkParams{
		WorkID: "work-requester", Summary: "claims one Quick item", AgentID: "agent-b", AdapterID: "codex",
		WorkspaceRoot: workspace, BaseCommit: "base", LeaseUntil: now.Add(time.Hour),
	})
	if err != nil {
		t.Fatal(err)
	}

	_, _, err = store.ClaimWorkIntents(ctx, ClaimWorkIntentsParams{
		WorkID: requester.WorkID, ExpectedRevision: requester.Revision, Fence: requester.Fence,
		Specs: []WriteIntentSpec{
			{Path: "src/free.go", Operation: WriteModify, Reason: "free path", Confidence: IntentConfirmed},
			{Path: "src/shared/conflict.go", Operation: WriteModify, Reason: "conflicting path", Confidence: IntentConfirmed},
		},
	})
	if !errors.Is(err, ErrWorkIntentConflict) {
		t.Fatalf("batch scope claim error = %v, want conflict", err)
	}
	loaded, intents, loadErr := store.GetWork(ctx, requester.WorkID)
	if loadErr != nil {
		t.Fatal(loadErr)
	}
	if loaded.Revision != requester.Revision || len(intents) != 0 {
		t.Fatalf("failed batch claim partially mutated requester: work %#v intents %#v", loaded, intents)
	}
}

func TestWorkBoardClaimIntentsCommitsOneRevisionForWholeBatch(t *testing.T) {
	ctx := context.Background()
	store := openTestStore(t, filepath.Join(t.TempDir(), "run-control.sqlite"))
	now := time.Now().UTC()
	workspace := filepath.Join(t.TempDir(), "workspace")
	requester, _, err := store.BeginWork(ctx, BeginWorkParams{
		WorkID: "work-requester", Summary: "claims one Quick item", AgentID: "agent-b", AdapterID: "codex",
		WorkspaceRoot: workspace, BaseCommit: "base", LeaseUntil: now.Add(time.Hour),
	})
	if err != nil {
		t.Fatal(err)
	}

	claimedWork, claimed, err := store.ClaimWorkIntents(ctx, ClaimWorkIntentsParams{
		WorkID: requester.WorkID, ExpectedRevision: requester.Revision, Fence: requester.Fence,
		Specs: []WriteIntentSpec{
			{Path: "src/a.go", Operation: WriteModify, Reason: "Q1", Confidence: IntentConfirmed},
			{Path: "src/b.go", Operation: WriteModify, Reason: "Q1", Confidence: IntentConfirmed},
		},
	})
	if err != nil {
		t.Fatal(err)
	}
	if claimedWork.Revision != requester.Revision+1 || len(claimed) != 2 {
		t.Fatalf("batch claim = work %#v intents %#v", claimedWork, claimed)
	}
}

func TestWorkBoardScopeAddPromotesOwnCandidateAfterConflictCheck(t *testing.T) {
	ctx := context.Background()
	store := openTestStore(t, filepath.Join(t.TempDir(), "run-control.sqlite"))
	now := time.Now().UTC()
	workspace := filepath.Join(t.TempDir(), "workspace")
	candidateWork, candidateIntents, err := store.BeginWork(ctx, BeginWorkParams{
		WorkID: "work-candidate", Summary: "candidate scope", AgentID: "agent-a", AdapterID: "codex",
		WorkspaceRoot: workspace, BaseCommit: "base", LeaseUntil: now.Add(time.Hour),
		WriteIntents: []WriteIntentSpec{{
			Path: "src/shared.go", Operation: WriteModify, Reason: "likely edit", Confidence: IntentCandidate,
		}},
	})
	if err != nil {
		t.Fatal(err)
	}
	owner, _, err := store.BeginWork(ctx, BeginWorkParams{
		WorkID: "work-confirmed", Summary: "confirmed scope", AgentID: "agent-b", AdapterID: "codex",
		WorkspaceRoot: workspace, BaseCommit: "base", LeaseUntil: now.Add(time.Hour),
		WriteIntents: []WriteIntentSpec{{
			Path: "src/shared.go", Operation: WriteModify, Reason: "active edit", Confidence: IntentConfirmed,
		}},
	})
	if err != nil {
		t.Fatal(err)
	}

	_, _, err = store.AddWorkIntent(ctx, AddWorkIntentParams{
		WorkID: candidateWork.WorkID, ExpectedRevision: candidateWork.Revision, Fence: candidateWork.Fence,
		Spec: WriteIntentSpec{
			Path: "src/shared.go", Operation: WriteModify, Reason: "now required", Confidence: IntentConfirmed,
		},
	})
	if !errors.Is(err, ErrWorkIntentConflict) {
		t.Fatalf("candidate promotion error = %v, want conflict while another task owns the path", err)
	}
	unchanged, intents, err := store.GetWork(ctx, candidateWork.WorkID)
	if err != nil {
		t.Fatal(err)
	}
	if unchanged.Revision != candidateWork.Revision || len(intents) != 1 || intents[0].Confidence != IntentCandidate {
		t.Fatalf("failed promotion mutated candidate work=%#v intents=%#v", unchanged, intents)
	}
	if _, err := store.TransitionWork(ctx, TransitionWorkParams{
		WorkID: owner.WorkID, ExpectedRevision: owner.Revision, Fence: owner.Fence,
		Target: WorkCompleted, Reason: "owner finished",
	}); err != nil {
		t.Fatal(err)
	}

	promotedWork, promoted, err := store.AddWorkIntent(ctx, AddWorkIntentParams{
		WorkID: candidateWork.WorkID, ExpectedRevision: candidateWork.Revision, Fence: candidateWork.Fence,
		Spec: WriteIntentSpec{
			Path: "src/shared.go", Operation: WriteModify, Reason: "now required", Confidence: IntentConfirmed,
		},
	})
	if err != nil {
		t.Fatal(err)
	}
	if promotedWork.Revision != candidateWork.Revision+1 || promoted.IntentID != candidateIntents[0].IntentID || promoted.Confidence != IntentConfirmed {
		t.Fatalf("promoted work=%#v intent=%#v", promotedWork, promoted)
	}
	_, intents, err = store.GetWork(ctx, candidateWork.WorkID)
	if err != nil {
		t.Fatal(err)
	}
	if len(intents) != 1 || intents[0].Confidence != IntentConfirmed || intents[0].Reason != "now required" {
		t.Fatalf("promoted intent history = %#v, want one confirmed intent", intents)
	}
}

func TestWorkBoardCompleteReleasesWriteIntentAndKeepsHistory(t *testing.T) {
	ctx := context.Background()
	store := openTestStore(t, filepath.Join(t.TempDir(), "run-control.sqlite"))
	now := time.Now().UTC()
	workspace := filepath.Join(t.TempDir(), "workspace")
	first, _, err := store.BeginWork(ctx, BeginWorkParams{
		WorkID: "work-first", Summary: "first", AgentID: "agent-a", AdapterID: "codex",
		WorkspaceRoot: workspace, BaseCommit: "base", LeaseUntil: now.Add(time.Hour),
		WriteIntents: []WriteIntentSpec{{
			Path: "src/shared.go", Operation: WriteModify, Reason: "first edit", Confidence: IntentConfirmed,
		}},
	})
	if err != nil {
		t.Fatal(err)
	}
	completed, err := store.TransitionWork(ctx, TransitionWorkParams{
		WorkID: first.WorkID, ExpectedRevision: first.Revision, Fence: first.Fence,
		Target: WorkCompleted, Reason: "verified and complete",
	})
	if err != nil {
		t.Fatal(err)
	}
	if completed.Status != WorkCompleted {
		t.Fatalf("completed work = %#v", completed)
	}

	_, _, err = store.BeginWork(ctx, BeginWorkParams{
		WorkID: "work-second", Summary: "second", AgentID: "agent-b", AdapterID: "codex",
		WorkspaceRoot: workspace, BaseCommit: "base", LeaseUntil: now.Add(time.Hour),
		WriteIntents: []WriteIntentSpec{{
			Path: "src/shared.go", Operation: WriteModify, Reason: "second edit", Confidence: IntentConfirmed,
		}},
	})
	if err != nil {
		t.Fatalf("released path should be claimable: %v", err)
	}
	_, history, err := store.GetWork(ctx, first.WorkID)
	if err != nil {
		t.Fatal(err)
	}
	if len(history) != 1 || history[0].Status != WriteIntentReleased {
		t.Fatalf("completed intent history = %#v", history)
	}
}

func TestWorkBoardReconcileExpiredLeaseReleasesCleanScope(t *testing.T) {
	ctx := context.Background()
	store := openTestStore(t, filepath.Join(t.TempDir(), "run-control.sqlite"))
	now := time.Now().UTC()
	workspace := filepath.Join(t.TempDir(), "workspace")
	work, _, err := store.BeginWork(ctx, BeginWorkParams{
		WorkID: "work-expired-clean", Summary: "clean interrupted work", AgentID: "agent-a", AdapterID: "codex",
		WorkspaceRoot: workspace, BaseCommit: "base", LeaseUntil: now.Add(time.Second),
		WriteIntents: []WriteIntentSpec{{
			Path: "src/clean.go", Operation: WriteModify, Reason: "clean edit", Confidence: IntentConfirmed,
		}},
	})
	if err != nil {
		t.Fatal(err)
	}
	interrupted, err := store.ReconcileExpiredWork(ctx, ReconcileWorkParams{
		Now: now.Add(2 * time.Second), DirtyPathsByWorkspace: map[string][]string{},
	})
	if err != nil {
		t.Fatal(err)
	}
	if len(interrupted) != 1 || interrupted[0].Status != WorkInterrupted || interrupted[0].RecoveryHold {
		t.Fatalf("reconciled clean work = %#v", interrupted)
	}
	if interrupted[0].Fence <= work.Fence {
		t.Fatalf("reconciled fence = %d, want greater than %d", interrupted[0].Fence, work.Fence)
	}
	_, intents, err := store.GetWork(ctx, work.WorkID)
	if err != nil {
		t.Fatal(err)
	}
	if len(intents) != 1 || intents[0].Status != WriteIntentReleased {
		t.Fatalf("clean interrupted intents = %#v", intents)
	}
}

func TestWorkBoardReconcileDirtyScopeCreatesRecoveryHoldAndResumeFencesOldOwner(t *testing.T) {
	ctx := context.Background()
	store := openTestStore(t, filepath.Join(t.TempDir(), "run-control.sqlite"))
	now := time.Now().UTC()
	workspace := filepath.Join(t.TempDir(), "workspace")
	work, _, err := store.BeginWork(ctx, BeginWorkParams{
		WorkID: "work-expired-dirty", Summary: "dirty interrupted work", AgentID: "agent-a", AdapterID: "codex",
		WorkspaceRoot: workspace, BaseCommit: "base", LeaseUntil: now.Add(time.Second),
		WriteIntents: []WriteIntentSpec{{
			Path: "src/dirty.go", Operation: WriteModify, Reason: "dirty edit", Confidence: IntentConfirmed,
		}},
	})
	if err != nil {
		t.Fatal(err)
	}
	interrupted, err := store.ReconcileExpiredWork(ctx, ReconcileWorkParams{
		Now:                   now.Add(2 * time.Second),
		DirtyPathsByWorkspace: map[string][]string{workspace: {"src/dirty.go"}},
	})
	if err != nil {
		t.Fatal(err)
	}
	if len(interrupted) != 1 || !interrupted[0].RecoveryHold {
		t.Fatalf("reconciled dirty work = %#v", interrupted)
	}
	branchDecision, err := store.ResolveFeatureBranchPolicy(ctx, "work-current-feature", now.Add(2*time.Second))
	if err != nil {
		t.Fatal(err)
	}
	if branchDecision.Policy != FeatureBranchPolicyKeepCurrent || len(branchDecision.ConcurrentWork) != 1 {
		t.Fatalf("recovery branch policy = %#v, want keep-current with one retained owner", branchDecision)
	}
	_, intents, err := store.GetWork(ctx, work.WorkID)
	if err != nil {
		t.Fatal(err)
	}
	if len(intents) != 1 || intents[0].Status != WriteIntentRecovery {
		t.Fatalf("dirty interrupted intents = %#v", intents)
	}
	if _, err := store.CheckpointWork(ctx, CheckpointWorkParams{
		WorkID: work.WorkID, ExpectedRevision: work.Revision, Fence: work.Fence,
		LeaseUntil: now.Add(time.Hour), NextAction: "old owner writes late",
	}); !errors.Is(err, ErrStaleFence) && !errors.Is(err, ErrRevisionConflict) {
		t.Fatalf("old owner checkpoint error = %v, want stale fence/revision", err)
	}

	resumed, err := store.ResumeWork(ctx, ResumeWorkParams{
		WorkID: interrupted[0].WorkID, ExpectedRevision: interrupted[0].Revision,
		AgentID: "agent-resumer", AdapterID: "codex", LeaseUntil: now.Add(time.Hour),
		WorkspaceRoot: workspace, BaseCommit: "base",
	})
	if err != nil {
		t.Fatal(err)
	}
	if resumed.Status != WorkActive || resumed.Fence <= interrupted[0].Fence || resumed.RecoveryHold {
		t.Fatalf("resumed work = %#v", resumed)
	}
	_, resumedIntents, err := store.GetWork(ctx, work.WorkID)
	if err != nil {
		t.Fatal(err)
	}
	if len(resumedIntents) != 1 || resumedIntents[0].Status != WriteIntentActive {
		t.Fatalf("resumed intents = %#v", resumedIntents)
	}
}

func TestWorkBoardAbandonInterruptedRecoveryHoldReleasesScope(t *testing.T) {
	ctx := context.Background()
	store := openTestStore(t, filepath.Join(t.TempDir(), "run-control.sqlite"))
	now := time.Now().UTC()
	workspace := filepath.Join(t.TempDir(), "workspace")
	work, _, err := store.BeginWork(ctx, BeginWorkParams{
		WorkID: "work-abandon-recovery", Summary: "abandon preserved work", AgentID: "agent-a", AdapterID: "codex",
		WorkspaceRoot: workspace, BaseCommit: "base", LeaseUntil: now.Add(time.Second),
		WriteIntents: []WriteIntentSpec{{
			Path: "src/preserved.go", Operation: WriteModify, Reason: "preserved edit", Confidence: IntentConfirmed,
		}},
	})
	if err != nil {
		t.Fatal(err)
	}
	interrupted, err := store.ReconcileExpiredWork(ctx, ReconcileWorkParams{
		Now: now.Add(2 * time.Second),
		DirtyPathsByWorkspace: map[string][]string{
			workspace: {"src/preserved.go"},
		},
	})
	if err != nil {
		t.Fatal(err)
	}
	if _, err := store.db.ExecContext(ctx, `UPDATE work_items SET lease_until_ms = 1 WHERE work_id = ?`, work.WorkID); err != nil {
		t.Fatal(err)
	}
	abandoned, err := store.TransitionWork(ctx, TransitionWorkParams{
		WorkID: work.WorkID, ExpectedRevision: interrupted[0].Revision, Fence: interrupted[0].Fence,
		Target: WorkAbandoned, Reason: "operator inspected and discarded the interrupted task",
	})
	if err != nil {
		t.Fatal(err)
	}
	if abandoned.Status != WorkAbandoned {
		t.Fatalf("abandoned work = %#v", abandoned)
	}
	_, intents, err := store.GetWork(ctx, work.WorkID)
	if err != nil {
		t.Fatal(err)
	}
	if len(intents) != 1 || intents[0].Status != WriteIntentReleased {
		t.Fatalf("abandoned recovery intents = %#v", intents)
	}
}
