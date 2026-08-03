package runcontrol

import (
	"context"
	"errors"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"testing"
	"time"
)

func TestForegroundSupervisorPublishesImmutableCandidateSnapshot(t *testing.T) {
	t.Setenv(foregroundHelperEnvironment, "1")
	mainRoot, _ := createLinkedRepository(t)
	repository, err := ResolveRepository(context.Background(), mainRoot)
	if err != nil {
		t.Fatal(err)
	}
	enqueueForegroundTestRun(t, repository, "candidate_snapshot")

	supervised, err := SuperviseRun(
		context.Background(),
		repository,
		foregroundTestParams("candidate_snapshot", "write", "candidate.txt", "published"),
	)
	if err != nil {
		t.Fatal(err)
	}
	candidate := supervised.Candidate
	if candidate.CandidateID == "" || candidate.Status != CandidateQueued {
		t.Fatalf("candidate = %#v, want queued immutable candidate", candidate)
	}
	if candidate.RunID != supervised.Run.RunID || candidate.AttemptID != supervised.Attempt.AttemptID ||
		candidate.WorkspaceID != supervised.Workspace.WorkspaceID ||
		candidate.WorkspaceGeneration != supervised.Workspace.Generation {
		t.Fatalf("candidate execution binding = %#v, want supervised execution", candidate)
	}
	if candidate.BaseCommit != supervised.Workspace.BaseCommit ||
		candidate.PrivateRef != supervised.Workspace.PrivateRef ||
		candidate.HeadCommit == "" || candidate.HeadCommit == candidate.BaseCommit {
		t.Fatalf("candidate Git binding = %#v, want committed change from workspace base", candidate)
	}
	if got := runGit(t, ensureGitAvailable(t), supervised.Workspace.RootPath, "rev-parse", "HEAD"); got != candidate.HeadCommit {
		t.Fatalf("workspace HEAD = %q, want candidate head %q", got, candidate.HeadCommit)
	}
	if got, statusErr := runGitStdout(context.Background(), supervised.Workspace.RootPath, "status", "--porcelain", "--untracked-files=all"); statusErr != nil || got != "" {
		t.Fatalf("published candidate workspace is not clean: %q", got)
	}
	if _, err := os.Stat(filepath.Join(mainRoot, "candidate.txt")); !errors.Is(err, os.ErrNotExist) {
		t.Fatalf("candidate publication modified primary worktree: %v", err)
	}

	observer := openTestStore(t, repository.DatabasePath, WithOwnerEpoch("candidate_snapshot_observer"))
	persisted, err := observer.GetCandidateForRun(context.Background(), supervised.Run.RunID)
	if err != nil {
		t.Fatal(err)
	}
	if persisted != candidate {
		t.Fatalf("persisted candidate = %#v, want %#v", persisted, candidate)
	}
}

func TestIntegrateNextSerializesParallelCandidatesOnTargetRef(t *testing.T) {
	t.Setenv(foregroundHelperEnvironment, "1")
	mainRoot, _ := createLinkedRepository(t)
	repository, err := ResolveRepository(context.Background(), mainRoot)
	if err != nil {
		t.Fatal(err)
	}
	gitPath := ensureGitAvailable(t)
	initialTarget := runGit(t, gitPath, mainRoot, "rev-parse", "HEAD")

	candidates := make([]Candidate, 0, 2)
	for _, suffix := range []string{"one", "two"} {
		runID := "parallel_integration_" + suffix
		enqueueForegroundTestRun(t, repository, runID)
		supervised, superviseErr := SuperviseRun(
			context.Background(),
			repository,
			foregroundTestParams(runID, "write", suffix+".txt", suffix),
		)
		if superviseErr != nil {
			t.Fatal(superviseErr)
		}
		candidates = append(candidates, supervised.Candidate)
	}
	if candidates[0].TargetRef != candidates[1].TargetRef {
		t.Fatalf("candidate targets differ: %#v", candidates)
	}

	type integrationCompletion struct {
		outcome IntegratedCandidate
		err     error
	}
	start := make(chan struct{})
	completed := make(chan integrationCompletion, 2)
	var workers sync.WaitGroup
	for index := 0; index < 2; index++ {
		index := index
		workers.Add(1)
		go func() {
			defer workers.Done()
			<-start
			outcome, integrateErr := IntegrateNext(context.Background(), repository, IntegrateNextParams{
				TargetRef:  candidates[0].TargetRef,
				OwnerEpoch: "parallel_integrator_" + candidates[index].RunID,
			})
			completed <- integrationCompletion{outcome: outcome, err: integrateErr}
		}()
	}
	close(start)
	workers.Wait()
	close(completed)

	links := map[string]string{}
	seenCandidates := map[string]bool{}
	for item := range completed {
		if item.err != nil {
			t.Fatal(item.err)
		}
		if item.outcome.Result.Status != ResultIntegrated || item.outcome.Candidate.Status != CandidateIntegrated {
			t.Fatalf("integration outcome = %#v, want integrated", item.outcome)
		}
		links[item.outcome.Result.TargetBefore] = item.outcome.Result.TargetAfter
		seenCandidates[item.outcome.Candidate.CandidateID] = true
	}
	if len(seenCandidates) != 2 {
		t.Fatalf("integrated candidates = %#v, want both candidates", seenCandidates)
	}
	second := links[initialTarget]
	finalTarget := links[second]
	if second == "" || finalTarget == "" || second == finalTarget {
		t.Fatalf("serialized target chain = %#v, want two ordered updates from %s", links, initialTarget)
	}
	if got := runGit(t, gitPath, mainRoot, "rev-parse", "HEAD"); got != finalTarget {
		t.Fatalf("target HEAD = %q, want final integrated commit %q", got, finalTarget)
	}
	for _, name := range []string{"one.txt", "two.txt"} {
		if _, err := os.Stat(filepath.Join(mainRoot, name)); err != nil {
			t.Fatalf("integrated file %s is unavailable: %v", name, err)
		}
	}
	if got, statusErr := runGitStdout(context.Background(), mainRoot, "status", "--porcelain", "--untracked-files=no"); statusErr != nil || got != "" {
		t.Fatalf("target worktree is dirty after serialized integration: %q", got)
	}
}

func TestIntegrateNextIsolatesConflict(t *testing.T) {
	t.Setenv(foregroundHelperEnvironment, "1")
	mainRoot, _ := createLinkedRepository(t)
	repository, err := ResolveRepository(context.Background(), mainRoot)
	if err != nil {
		t.Fatal(err)
	}
	gitPath := ensureGitAvailable(t)

	candidates := make([]Candidate, 0, 2)
	for _, change := range []string{"first", "second"} {
		runID := "conflict_" + change
		enqueueForegroundTestRun(t, repository, runID)
		supervised, superviseErr := SuperviseRun(
			context.Background(),
			repository,
			foregroundTestParams(runID, "write", "README.md", change),
		)
		if superviseErr != nil {
			t.Fatal(superviseErr)
		}
		candidates = append(candidates, supervised.Candidate)
	}

	first, err := IntegrateNext(context.Background(), repository, IntegrateNextParams{
		TargetRef: candidates[0].TargetRef, OwnerEpoch: "conflict_integrator_first",
	})
	if err != nil || first.Result.Status != ResultIntegrated {
		t.Fatalf("first integration = %#v err=%v", first, err)
	}
	second, err := IntegrateNext(context.Background(), repository, IntegrateNextParams{
		TargetRef: candidates[0].TargetRef, OwnerEpoch: "conflict_integrator_second",
	})
	if err != nil {
		t.Fatal(err)
	}
	if second.Result.Status != ResultConflicted || second.Candidate.Status != CandidateConflicted {
		t.Fatalf("conflicting integration = %#v, want isolated conflict", second)
	}
	content, err := os.ReadFile(filepath.Join(mainRoot, "README.md"))
	if err != nil {
		t.Fatal(err)
	}
	if !strings.HasSuffix(string(content), "\nfirst") || strings.Contains(string(content), "\nsecond") {
		t.Fatalf("target content = %q, want first integrated candidate", content)
	}
	if got, statusErr := runGitStdout(context.Background(), mainRoot, "status", "--porcelain", "--untracked-files=no"); statusErr != nil || got != "" {
		t.Fatalf("target worktree retained conflict state: %q", got)
	}
	mergeHeadPath := runGit(t, gitPath, mainRoot, "rev-parse", "--git-path", "MERGE_HEAD")
	if !filepath.IsAbs(mergeHeadPath) {
		mergeHeadPath = filepath.Join(mainRoot, mergeHeadPath)
	}
	if _, statErr := os.Stat(mergeHeadPath); !errors.Is(statErr, os.ErrNotExist) {
		t.Fatalf("target worktree retained MERGE_HEAD: %v", statErr)
	}
}

func TestIntegrateNextRejectsCandidateWhosePrivateRefMoved(t *testing.T) {
	t.Setenv(foregroundHelperEnvironment, "1")
	mainRoot, _ := createLinkedRepository(t)
	repository, err := ResolveRepository(context.Background(), mainRoot)
	if err != nil {
		t.Fatal(err)
	}
	enqueueForegroundTestRun(t, repository, "candidate_binding")
	supervised, err := SuperviseRun(
		context.Background(),
		repository,
		foregroundTestParams("candidate_binding", "write", "bound.txt", "bound"),
	)
	if err != nil {
		t.Fatal(err)
	}
	candidate := supervised.Candidate
	enqueueForegroundTestRun(t, repository, "candidate_binding_followup")
	followup, err := SuperviseRun(
		context.Background(),
		repository,
		foregroundTestParams("candidate_binding_followup", "write", "followup.txt", "followup"),
	)
	if err != nil {
		t.Fatal(err)
	}
	runGit(
		t,
		ensureGitAvailable(t),
		mainRoot,
		"update-ref",
		candidate.PrivateRef,
		candidate.BaseCommit,
		candidate.HeadCommit,
	)

	_, err = IntegrateNext(context.Background(), repository, IntegrateNextParams{
		TargetRef: candidate.TargetRef, OwnerEpoch: "binding_integrator",
	})
	if !errors.Is(err, ErrCandidateBinding) {
		t.Fatalf("tampered candidate integration error = %v, want ErrCandidateBinding", err)
	}
	if _, statErr := os.Stat(filepath.Join(mainRoot, "bound.txt")); !errors.Is(statErr, os.ErrNotExist) {
		t.Fatalf("tampered candidate modified target worktree: %v", statErr)
	}
	observer := openTestStore(t, repository.DatabasePath, WithOwnerEpoch("binding_observer"))
	rejected, err := observer.GetCandidate(context.Background(), candidate.CandidateID)
	if err != nil {
		t.Fatal(err)
	}
	if rejected.Status != CandidateConflicted {
		t.Fatalf("tampered candidate status = %q, want terminal conflicted", rejected.Status)
	}
	integrated, err := IntegrateNext(context.Background(), repository, IntegrateNextParams{
		TargetRef: candidate.TargetRef, OwnerEpoch: "binding_followup_integrator",
	})
	if err != nil {
		t.Fatal(err)
	}
	if integrated.Candidate.CandidateID != followup.Candidate.CandidateID || integrated.Result.Status != ResultIntegrated {
		t.Fatalf("follow-up integration = %#v, want candidate %s", integrated, followup.Candidate.CandidateID)
	}
}

func TestReconcileStaleExecutingIntegrationReleasesTargetQueue(t *testing.T) {
	t.Setenv(foregroundHelperEnvironment, "1")
	mainRoot, _ := createLinkedRepository(t)
	repository, err := ResolveRepository(context.Background(), mainRoot)
	if err != nil {
		t.Fatal(err)
	}
	candidates := make([]Candidate, 0, 2)
	for _, suffix := range []string{"stale", "next"} {
		runID := "stale_integration_" + suffix
		enqueueForegroundTestRun(t, repository, runID)
		supervised, superviseErr := SuperviseRun(
			context.Background(), repository,
			foregroundTestParams(runID, "write", suffix+".txt", suffix),
		)
		if superviseErr != nil {
			t.Fatal(superviseErr)
		}
		candidates = append(candidates, supervised.Candidate)
	}

	staleOwner := openTestStore(t, repository.DatabasePath, WithOwnerEpoch("stale_integration_owner"))
	claimed, integration, err := staleOwner.claimNextCandidate(context.Background(), candidates[0].TargetRef)
	if err != nil {
		t.Fatal(err)
	}
	targetBefore := runGit(t, ensureGitAvailable(t), mainRoot, "rev-parse", "HEAD")
	integration, err = staleOwner.startCandidateIntegration(context.Background(), integration, targetBefore)
	if err != nil {
		t.Fatal(err)
	}

	recovery := openTestStore(t, repository.DatabasePath, WithOwnerEpoch("stale_integration_recovery"))
	future := time.Now().UTC().Add(2 * time.Hour)
	if _, err := recovery.ReconcileStaleSupervisors(context.Background(), future, future.Add(-time.Hour)); err != nil {
		t.Fatal(err)
	}
	var integrationStatus IntegrationStatus
	if err := recovery.db.QueryRowContext(
		context.Background(),
		"SELECT status FROM candidate_integrations WHERE integration_id = ?",
		integration.IntegrationID,
	).Scan(&integrationStatus); err != nil {
		t.Fatal(err)
	}
	if integrationStatus != IntegrationOutcomeUnknown {
		t.Fatalf("stale integration status = %q, want outcome_unknown", integrationStatus)
	}
	uncertain, err := recovery.GetCandidate(context.Background(), claimed.CandidateID)
	if err != nil {
		t.Fatal(err)
	}
	if uncertain.Status != CandidateIntegrating {
		t.Fatalf("stale candidate status = %q, want integrating until Git recovery", uncertain.Status)
	}

	integrated, err := IntegrateNext(context.Background(), repository, IntegrateNextParams{
		TargetRef: candidates[0].TargetRef, OwnerEpoch: "stale_integration_next_owner",
	})
	if err != nil {
		t.Fatal(err)
	}
	if integrated.Candidate.CandidateID != claimed.CandidateID || integrated.Result.Status != ResultIntegrated {
		t.Fatalf("post-recovery integration = %#v, want safely requeued candidate %s", integrated, claimed.CandidateID)
	}
}
