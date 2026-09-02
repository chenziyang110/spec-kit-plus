package runcontrol

import (
	"context"
	"errors"
	"os"
	"path/filepath"
	"reflect"
	"sort"
	"testing"
	"time"
)

func TestWorkspaceDeltaExcludesKnownRuntimeTransportAcrossGitStates(t *testing.T) {
	for _, state := range []string{"untracked", "staged", "committed"} {
		t.Run(state, func(t *testing.T) {
			ctx := context.Background()
			root, _ := createLinkedRepository(t)
			// The fixture deliberately stages nested transaction copies. Permit
			// those paths in this disposable repository even under a long Windows
			// test temp root; never change the operator's Git configuration.
			runGit(t, ensureGitAvailable(t), root, "config", "core.longpaths", "true")
			baseline := captureDeltaTestBaseline(t, root)
			transport := append(runtimeTransportTestPaths(), runControlRuntimeTestPaths()...)
			transport = append(transport, workflowRuntimeLockTestPaths()...)
			audited := []string{
				"README.md",
				".specify/features/feature/task-index.json",
				".specify/design/changes/UD-001/design-change.md",
				".specify/memory/project-rules.md",
				".planning/quick/Q001/STATUS.md",
				".specify/runtime/unknown-state.json",
				".specify/runtime/receipts-other/user.json",
				".specify/runtime/discussion/notes.md",
				".specify/runtime/test-design/report.md",
				".specify/runtime/workflow-mutations/receipt.json",
				"nested/.specify/runtime/receipts/user.json",
			}
			for _, path := range append(transport, audited...) {
				writeDeltaTestFile(t, root, path, "changed after baseline\n")
			}
			if state != "untracked" {
				runGit(t, ensureGitAvailable(t), root, "add", "-A")
			}
			if state == "committed" {
				runGit(t, ensureGitAvailable(t), root, "commit", "-m", "fixture changes")
			}
			delta, err := InspectWorkspaceDelta(ctx, root, baseline)
			if err != nil {
				t.Fatal(err)
			}
			sort.Strings(audited)
			if !reflect.DeepEqual(delta, audited) {
				t.Fatalf("%s delta = %#v, want only deliverable/unknown paths %#v", state, delta, audited)
			}
			if state != "committed" {
				dirty, err := InspectWorkspaceChanges(ctx, root)
				if err != nil {
					t.Fatal(err)
				}
				all := append(runtimeTransportTestPaths(), audited...)
				sort.Strings(all)
				if !reflect.DeepEqual(dirty, all) {
					t.Fatalf("recovery inspection filtered paths: %#v, want %#v", dirty, all)
				}
			}
		})
	}
}

func TestWorkspaceDeltaIgnoresExistingTransportModificationAndDeletion(t *testing.T) {
	root, _ := createLinkedRepository(t)
	modified := ".specify/runtime/transactions/old/journal.json"
	deleted := ".specify/runtime/receipts/old.json"
	canonical := ".specify/features/feature/workflow-state.md"
	for _, path := range []string{modified, deleted, canonical} {
		writeDeltaTestFile(t, root, path, "preexisting untracked state\n")
	}
	baseline := captureDeltaTestBaseline(t, root)
	writeDeltaTestFile(t, root, modified, "new transport state\n")
	writeDeltaTestFile(t, root, canonical, "new canonical state\n")
	if err := os.Remove(filepath.Join(root, filepath.FromSlash(deleted))); err != nil {
		t.Fatal(err)
	}
	delta, err := InspectWorkspaceDelta(context.Background(), root, baseline)
	if err != nil {
		t.Fatal(err)
	}
	if !reflect.DeepEqual(delta, []string{canonical}) {
		t.Fatalf("baseline delta = %#v, want canonical mutation only", delta)
	}
}

func TestWorkspaceDeltaPreservesCanonicalEndpointOfTransportRename(t *testing.T) {
	const canonical = ".specify/features/feature/spec.md"
	const transport = ".specify/runtime/artifact-trash/archive/payload.md"
	for _, restore := range []bool{false, true} {
		name := "archive"
		if restore {
			name = "restore"
		}
		t.Run(name, func(t *testing.T) {
			root, _ := createLinkedRepository(t)
			from, to := canonical, transport
			if restore {
				from, to = transport, canonical
			}
			writeDeltaTestFile(t, root, from, "canonical artifact bytes\n")
			git := ensureGitAvailable(t)
			runGit(t, git, root, "add", "-A")
			runGit(t, git, root, "commit", "-m", "fixture baseline")
			baseline := captureDeltaTestBaseline(t, root)
			if err := os.MkdirAll(filepath.Dir(filepath.Join(root, filepath.FromSlash(to))), 0o755); err != nil {
				t.Fatal(err)
			}
			if err := os.Rename(filepath.Join(root, filepath.FromSlash(from)), filepath.Join(root, filepath.FromSlash(to))); err != nil {
				t.Fatal(err)
			}
			runGit(t, git, root, "add", "-A")
			runGit(t, git, root, "commit", "-m", "fixture rename")
			delta, err := InspectWorkspaceDelta(context.Background(), root, baseline)
			if err != nil {
				t.Fatal(err)
			}
			if !reflect.DeepEqual(delta, []string{canonical}) {
				t.Fatalf("%s hid canonical rename endpoint: %#v", name, delta)
			}
		})
	}
}

func TestExecutionDeltaAuditStillBlocksUnclaimedCanonicalArtifacts(t *testing.T) {
	for _, outside := range []bool{false, true} {
		name := "private_transport_only"
		if outside {
			name = "unclaimed_canonical_artifacts"
		}
		t.Run(name, func(t *testing.T) {
			ctx := context.Background()
			root, _ := createLinkedRepository(t)
			store := openTestStore(t, filepath.Join(t.TempDir(), "run-control.sqlite"))
			registration, err := store.AnnounceExecution(ctx, AnnounceExecutionParams{
				ActivityID: "audit", WorkID: "audit", Workflow: ExecutionWorkflowFast, SubjectID: "audit",
				TaskRef: "fast:audit", Summary: "source audit", AgentID: "agent", AdapterID: "codex",
				WorkspaceRoot: root, LeaseUntil: time.Now().UTC().Add(time.Hour), BaselineJSON: captureDeltaTestBaseline(t, root),
				PlannedWriteIntents: []WriteIntentSpec{{Path: "README.md", Confidence: IntentCandidate}},
			})
			if err != nil {
				t.Fatal(err)
			}
			guarded := guardTestExecution(t, store, registration)
			for _, path := range append(runtimeTransportTestPaths(), "README.md") {
				writeDeltaTestFile(t, root, path, "new state\n")
			}
			canonical := []string{
				".specify/features/feature/implementation-review/task-index.json",
				".specify/design/changes/UD-001/design-change.md",
				".specify/memory/project-rules.md",
				".planning/quick/Q001/STATUS.md",
			}
			if outside {
				for _, path := range canonical {
					writeDeltaTestFile(t, root, path, "unclaimed canonical change\n")
				}
			}
			delta, err := InspectWorkspaceDelta(ctx, root, guarded.Activity.BaselineJSON)
			if err != nil {
				t.Fatal(err)
			}
			completed, err := store.CompleteExecution(ctx, CompleteExecutionParams{
				ActivityID: guarded.Activity.ActivityID, ExpectedWorkRevision: guarded.Work.Revision, Fence: guarded.Work.Fence,
				ChangedPaths: delta, ValidationJSON: `[{"command":"fixture validation","result":"passed"}]`, Reason: "audit actual delta",
			})
			if !outside {
				if err != nil || completed.Work.Status != WorkCompleted || !reflect.DeepEqual(delta, []string{"README.md"}) {
					t.Fatalf("private transport prevented scoped completion: delta=%#v, completed=%#v, err=%v", delta, completed, err)
				}
				return
			}
			var auditErr *ExecutionScopeAuditError
			sort.Strings(canonical)
			if !errors.As(err, &auditErr) || !reflect.DeepEqual(auditErr.UnclaimedPaths, canonical) {
				t.Fatalf("canonical scope audit weakened: %v, want unclaimed paths %#v", err, canonical)
			}
			current, err := store.GetExecutionActivity(ctx, guarded.Activity.ActivityID)
			if err != nil || !reflect.DeepEqual(current, guarded.ExecutionRegistration) {
				t.Fatalf("failed canonical audit mutated execution: %#v, %v", current, err)
			}
		})
	}
}

func TestWorkRecoveryStillSeesPrivateTransportChanges(t *testing.T) {
	ctx := context.Background()
	root, _ := createLinkedRepository(t)
	store := openTestStore(t, filepath.Join(t.TempDir(), "run-control.sqlite"))
	now := time.Now().UTC()
	work, _, err := store.BeginWork(ctx, BeginWorkParams{
		WorkID: "transport-owner", Summary: "private transport maintenance", AgentID: "agent", AdapterID: "codex",
		WorkspaceRoot: root, LeaseUntil: now.Add(time.Minute), WriteIntents: []WriteIntentSpec{{Path: ".specify/runtime/receipts"}},
	})
	if err != nil {
		t.Fatal(err)
	}
	writeDeltaTestFile(t, root, ".specify/runtime/receipts/pending.json", "unfinished transport\n")
	if _, err := store.ReconcileRepositoryWork(ctx, now.Add(2*time.Minute)); err != nil {
		t.Fatal(err)
	}
	recovered, intents, err := store.GetWork(ctx, work.WorkID)
	if err != nil {
		t.Fatal(err)
	}
	if recovered.Status != WorkInterrupted || !recovered.RecoveryHold || len(intents) != 1 || intents[0].Status != WriteIntentRecovery {
		t.Fatalf("transport changes lost recovery ownership: %#v / %#v", recovered, intents)
	}
}

func runtimeTransportTestPaths() []string {
	return []string{
		".specify/runtime/receipts/random-transaction.json",
		".specify/runtime/transactions/random-transaction/journal.json",
		".specify/runtime/transactions/random-transaction/stage/.specify/features/feature/task-index.json",
		".specify/runtime/leases/random-lease.json",
		".specify/runtime/locks/file-transactions.lock",
		".specify/runtime/locks/artifacts/random-artifact.lock",
		".specify/runtime/locks/leases/random-lease.lock",
		".specify/runtime/artifact-trash/random-archive/payload.md",
		".specify/runtime/deep-research/locks/random-subject.lock",
		".specify/runtime/test-design/locks/random-subject.lock",
		".specify/runtime/discussion/mutation.lock",
	}
}

func runControlRuntimeTestPaths() []string {
	return []string{
		".specify/runtime/run-control/run-control.sqlite",
		".specify/runtime/run-control/run-control.sqlite-wal",
		".specify/runtime/run-control/run-control.sqlite-shm",
		".specify/runtime/run-control/migration.lock",
	}
}

func workflowRuntimeLockTestPaths() []string {
	return []string{
		".specify/features/feature/.workflow.lock",
		".specify/specs/legacy/.workflow.lock",
		"specs/compat/.workflow.lock",
		".specify/runtime/workflow-mutations/0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef.json",
	}
}

func captureDeltaTestBaseline(t *testing.T, root string) string {
	t.Helper()
	baseline, err := CaptureWorkspaceBaseline(context.Background(), root)
	if err != nil {
		t.Fatal(err)
	}
	encoded, err := EncodeWorkspaceBaseline(baseline)
	if err != nil {
		t.Fatal(err)
	}
	return encoded
}

func writeDeltaTestFile(t *testing.T, root, relative, content string) {
	t.Helper()
	target := filepath.Join(root, filepath.FromSlash(relative))
	if err := os.MkdirAll(filepath.Dir(target), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(target, []byte(content), 0o644); err != nil {
		t.Fatal(err)
	}
}
