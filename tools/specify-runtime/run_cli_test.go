package main

import (
	"bytes"
	"context"
	"database/sql"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"sync"
	"testing"
	"time"

	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/runcontrol"
)

func TestRunCLIControlsDurableRunLifecycle(t *testing.T) {
	root := initRunCLIRepository(t)
	runID := "run_cli_lifecycle"
	digest := strings.Repeat("a", 64)

	code, created := invokeRunCLI(t,
		"run", "create",
		"--project-root", root,
		"--run-id", runID,
		"--kind", "quick",
		"--subject-type", "feature",
		"--subject-id", "parallel-quick",
		"--target-ref", "refs/heads/main",
		"--intent-sha256", digest,
		"--format", "json",
	)
	if code != 0 || created["status"] != "ok" {
		t.Fatalf("run create = code %d envelope %#v, want ok", code, created)
	}
	createdRun := requireObject(t, requireObject(t, created, "data"), "run")
	if createdRun["run_id"] != runID || createdRun["status"] != "queued" || createdRun["revision"] != float64(1) {
		t.Fatalf("created run = %#v, want queued revision 1", createdRun)
	}

	code, shown := invokeRunCLI(t, "run", "show", runID, "--project-root", root, "--format", "json")
	if code != 0 || shown["status"] != "ok" {
		t.Fatalf("run show = code %d envelope %#v, want ok", code, shown)
	}
	shownRun := requireObject(t, requireObject(t, shown, "data"), "run")
	if shownRun["status"] != "queued" {
		t.Fatalf("run status after create process closed = %#v, want queued", shownRun["status"])
	}

	code, events := invokeRunCLI(t, "run", "events", runID, "--project-root", root, "--format", "json")
	if code != 0 || events["status"] != "ok" {
		t.Fatalf("run events = code %d envelope %#v, want ok", code, events)
	}
	items := events["items"].([]any)
	if len(items) != 1 || requireObjectValue(t, items[0])["event_type"] != "run.created" {
		t.Fatalf("created run events = %#v, want one run.created event", items)
	}

	code, cancelled := invokeRunCLI(t,
		"run", "cancel", runID,
		"--project-root", root,
		"--expected-revision", "1",
		"--reason", "user stopped the task",
		"--format", "json",
	)
	if code != 0 || cancelled["status"] != "ok" {
		t.Fatalf("run cancel = code %d envelope %#v, want ok", code, cancelled)
	}
	cancelledRun := requireObject(t, requireObject(t, cancelled, "data"), "run")
	if cancelledRun["status"] != "cancelled" || cancelledRun["revision"] != float64(2) || cancelledRun["current_fence"] != float64(1) {
		t.Fatalf("cancelled run = %#v, want cancelled revision 2 fence 1", cancelledRun)
	}

	_, events = invokeRunCLI(t, "run", "events", runID, "--project-root", root, "--format", "json")
	items = events["items"].([]any)
	if len(items) != 2 || requireObjectValue(t, items[1])["event_type"] != "run.cancelled" {
		t.Fatalf("cancelled run events = %#v, want terminal run.cancelled event", items)
	}
}

func TestRunCLICancelUsesRevisionCAS(t *testing.T) {
	root := initRunCLIRepository(t)
	createRunThroughCLI(t, root, "run_cli_stale")

	code, payload := invokeRunCLI(t,
		"run", "cancel", "run_cli_stale",
		"--project-root", root,
		"--expected-revision", "99",
		"--reason", "stale caller",
		"--format", "json",
	)
	if code != 10 || payload["status"] != "blocked" {
		t.Fatalf("stale run cancel = code %d envelope %#v, want blocked exit 10", code, payload)
	}

	code, shown := invokeRunCLI(t, "run", "show", "run_cli_stale", "--project-root", root, "--format", "json")
	if code != 0 || requireObject(t, requireObject(t, shown, "data"), "run")["status"] != "queued" {
		t.Fatalf("stale cancellation changed run: code %d envelope %#v", code, shown)
	}
}

func TestRunCLICreatesFiveIndependentRunsConcurrently(t *testing.T) {
	root := initRunCLIRepository(t)
	type result struct {
		runID   string
		code    int
		payload map[string]any
		err     error
	}
	start := make(chan struct{})
	results := make(chan result, 5)
	var workers sync.WaitGroup
	for index := 1; index <= 5; index++ {
		runID := "run_cli_parallel_" + strconv.Itoa(index)
		workers.Add(1)
		go func() {
			defer workers.Done()
			<-start
			var stdout, stderr bytes.Buffer
			code := Run([]string{
				"run", "create",
				"--project-root", root,
				"--run-id", runID,
				"--kind", "quick",
				"--subject-type", "feature",
				"--subject-id", runID,
				"--target-ref", "HEAD",
				"--intent-sha256", strings.Repeat("c", 64),
				"--format", "json",
			}, &stdout, &stderr, "test")
			var payload map[string]any
			decodeErr := json.Unmarshal(stdout.Bytes(), &payload)
			if decodeErr == nil && stderr.Len() != 0 {
				decodeErr = fmt.Errorf("stderr: %s", stderr.String())
			}
			results <- result{runID: runID, code: code, payload: payload, err: decodeErr}
		}()
	}
	close(start)
	workers.Wait()
	close(results)

	for created := range results {
		if created.err != nil || created.code != 0 || created.payload["status"] != "ok" {
			t.Fatalf("parallel create %s = code %d error %v envelope %#v", created.runID, created.code, created.err, created.payload)
		}
		code, shown := invokeRunCLI(t, "run", "show", created.runID, "--project-root", root, "--format", "json")
		if code != 0 || requireObject(t, requireObject(t, shown, "data"), "run")["status"] != "queued" {
			t.Fatalf("parallel run %s not independently visible: code %d envelope %#v", created.runID, code, shown)
		}
	}
}

func TestRunCLIQueuedRunSurvivesNewSupervisorReconciliation(t *testing.T) {
	root := initRunCLIRepository(t)
	createRunThroughCLI(t, root, "run_cli_queued_handoff")

	store, err := runcontrol.OpenForRepository(context.Background(), root, runcontrol.WithOwnerEpoch("supervisor_after_enqueue"))
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { _ = store.Close() })
	now := time.Now().UTC()
	interrupted, err := store.ReconcileStaleSupervisors(context.Background(), now, now.Add(-time.Minute))
	if err != nil {
		t.Fatal(err)
	}
	if len(interrupted) != 0 {
		t.Fatalf("queued run was reconciled as abandoned execution: %#v", interrupted)
	}
	queued, err := store.GetRun(context.Background(), "run_cli_queued_handoff")
	if err != nil {
		t.Fatal(err)
	}
	if queued.Status != runcontrol.RunStatus("queued") || queued.Revision != 1 || queued.CurrentFence != 0 {
		t.Fatalf("queued run after supervisor reconciliation = %#v", queued)
	}
}

func TestRunCLIShowAndEventsAreActuallyReadOnly(t *testing.T) {
	root := initRunCLIRepository(t)
	createRunThroughCLI(t, root, "run_cli_read_only")
	repository, err := runcontrol.ResolveRepository(context.Background(), root)
	if err != nil {
		t.Fatal(err)
	}
	database, err := sql.Open("sqlite", repository.DatabasePath)
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { _ = database.Close() })
	before := supervisorRowCount(t, database)

	if code, _ := invokeRunCLI(t, "run", "show", "run_cli_read_only", "--project-root", root, "--format", "json"); code != 0 {
		t.Fatalf("run show exit code = %d", code)
	}
	if code, _ := invokeRunCLI(t, "run", "events", "run_cli_read_only", "--project-root", root, "--format", "json"); code != 0 {
		t.Fatalf("run events exit code = %d", code)
	}
	if after := supervisorRowCount(t, database); after != before {
		t.Fatalf("read-only commands changed supervisor rows from %d to %d", before, after)
	}
}

func TestRunCLIShowDoesNotCreateMissingControlDatabase(t *testing.T) {
	root := initRunCLIRepository(t)
	repository, err := runcontrol.ResolveRepository(context.Background(), root)
	if err != nil {
		t.Fatal(err)
	}
	if _, err := os.Stat(repository.DatabasePath); !os.IsNotExist(err) {
		t.Fatalf("control database exists before read: %v", err)
	}
	code, payload := invokeRunCLI(t, "run", "show", "missing", "--project-root", root, "--format", "json")
	if code != 2 || payload["status"] != "invalid" {
		t.Fatalf("show without database = code %d envelope %#v, want invalid exit 2", code, payload)
	}
	if _, err := os.Stat(repository.DatabasePath); !os.IsNotExist(err) {
		t.Fatalf("read-only show created control database: %v", err)
	}
}

func TestRunCLIRejectsUnsafeOrIncompleteRequests(t *testing.T) {
	root := initRunCLIRepository(t)
	tests := []struct {
		name string
		args []string
	}{
		{name: "missing subcommand", args: []string{"run"}},
		{name: "missing create field", args: []string{"run", "create", "--project-root", root, "--run-id", "missing"}},
		{name: "unknown option", args: []string{"run", "show", "missing", "--project-root", root, "--surprise", "value"}},
		{name: "missing show id", args: []string{"run", "show", "--project-root", root}},
		{name: "invalid revision", args: []string{"run", "cancel", "missing", "--project-root", root, "--expected-revision", "zero", "--reason", "invalid"}},
		{name: "supervise missing argv separator", args: []string{"run", "supervise", "missing", "--project-root", root, "--adapter-id", "test"}},
		{name: "privileged subcommand", args: []string{"run", "heartbeat", "attempt", "--project-root", root}},
	}
	for _, test := range tests {
		t.Run(test.name, func(t *testing.T) {
			code, payload := invokeRunCLI(t, test.args...)
			if code != 2 || payload["status"] != "usage-error" {
				t.Fatalf("request %v = code %d envelope %#v, want usage-error exit 2", test.args, code, payload)
			}
		})
	}
}

func TestRunCLISuperviseExecutesTokenizedChildInSandbox(t *testing.T) {
	root := initRunCLIRepository(t)
	gitRun(t, root, "config", "user.name", "Run CLI Test")
	gitRun(t, root, "config", "user.email", "run-cli@example.invalid")
	gitRun(t, root, "config", "commit.gpgsign", "false")
	if err := os.WriteFile(filepath.Join(root, "README.md"), []byte("foreground cli\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	gitRun(t, root, "add", "README.md")
	gitRun(t, root, "commit", "-m", "initial")
	createRunThroughCLI(t, root, "run_cli_supervise")
	t.Setenv("SPECIFY_RUNTIME_CLI_FOREGROUND_HELPER", "1")

	code, payload := invokeRunCLI(t,
		"run", "supervise", "run_cli_supervise",
		"--project-root", root,
		"--adapter-id", "test-helper",
		"--format", "json",
		"--",
		os.Args[0], "-test.run=^TestRunCLIForegroundHelperProcess$", "--",
		"cli-marker.txt", "literal&token",
	)
	if code != 0 || payload["status"] != "ok" {
		t.Fatalf("run supervise = code %d envelope %#v", code, payload)
	}
	execution := requireObject(t, requireObject(t, payload, "data"), "execution")
	workspaceRoot, _ := execution["workspace_root"].(string)
	if workspaceRoot == "" || execution["workspace_generation"] != float64(1) {
		t.Fatalf("supervised execution = %#v", execution)
	}
	marker, err := os.ReadFile(filepath.Join(workspaceRoot, "cli-marker.txt"))
	if err != nil {
		t.Fatal(err)
	}
	if string(marker) != workspaceRoot+"\nliteral&token" {
		t.Fatalf("CLI child marker = %q", marker)
	}
	if _, err := os.Stat(filepath.Join(root, "cli-marker.txt")); !errors.Is(err, os.ErrNotExist) {
		t.Fatalf("CLI child modified primary worktree: %v", err)
	}
}

func TestRunCLIForegroundHelperProcess(t *testing.T) {
	if os.Getenv("SPECIFY_RUNTIME_CLI_FOREGROUND_HELPER") != "1" {
		return
	}
	arguments := helperArgumentsAfterDoubleDash(os.Args)
	if len(arguments) != 2 {
		os.Exit(81)
	}
	cwd, err := os.Getwd()
	if err != nil {
		os.Exit(82)
	}
	if err := os.WriteFile(
		filepath.Join(cwd, arguments[0]),
		[]byte(cwd+"\n"+arguments[1]),
		0o644,
	); err != nil {
		os.Exit(83)
	}
	os.Exit(0)
}

func TestRunCLIUsesSharedDatabaseFromLinkedWorktree(t *testing.T) {
	root := initRunCLIRepository(t)
	if err := os.WriteFile(filepath.Join(root, "README.md"), []byte("run cli\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	gitRun(t, root, "config", "user.name", "Run CLI Test")
	gitRun(t, root, "config", "user.email", "run-cli@example.invalid")
	gitRun(t, root, "config", "commit.gpgsign", "false")
	gitRun(t, root, "add", "README.md")
	gitRun(t, root, "commit", "-m", "initial")
	linked := filepath.Join(filepath.Dir(root), filepath.Base(root)+"-linked")
	gitRun(t, root, "worktree", "add", "--detach", linked, "HEAD")
	t.Cleanup(func() { _ = os.RemoveAll(linked) })

	createRunThroughCLI(t, root, "run_cli_shared")
	code, payload := invokeRunCLI(t, "run", "show", "run_cli_shared", "--project-root", linked, "--format", "json")
	if code != 0 || requireObject(t, requireObject(t, payload, "data"), "run")["run_id"] != "run_cli_shared" {
		t.Fatalf("linked worktree show = code %d envelope %#v, want shared run", code, payload)
	}
}

func TestRunCapabilitiesAreDiscoverableAndBounded(t *testing.T) {
	for _, capabilityID := range []string{"run.create", "run.show", "run.events", "run.cancel", "run.supervise"} {
		if !containsCapability(defaultCapabilities(), capabilityID) {
			t.Fatalf("default capabilities missing %q", capabilityID)
		}
		code, payload := invokeRunCLI(t, "api", "show", capabilityID, "--format", "json")
		if code != 0 {
			t.Fatalf("api show %s = code %d envelope %#v", capabilityID, code, payload)
		}
		capability := requireObject(t, requireObject(t, payload, "data"), "capability")
		if capability["usage"] == nil || capability["side_effect"] == nil {
			t.Fatalf("capability %s = %#v, want usage and side_effect", capabilityID, capability)
		}
	}
	for _, privileged := range []string{"run.issue-attempt", "run.activate-attempt", "run.heartbeat", "run.reconcile"} {
		if containsCapability(defaultCapabilities(), privileged) {
			t.Fatalf("default capabilities expose privileged control %q", privileged)
		}
	}
}

func helperArgumentsAfterDoubleDash(arguments []string) []string {
	for index, argument := range arguments {
		if argument == "--" {
			return arguments[index+1:]
		}
	}
	return nil
}

func initRunCLIRepository(t *testing.T) string {
	t.Helper()
	requireGit(t)
	root := t.TempDir()
	gitRun(t, root, "init")
	return root
}

func createRunThroughCLI(t *testing.T, root, runID string) map[string]any {
	t.Helper()
	code, payload := invokeRunCLI(t,
		"run", "create",
		"--project-root", root,
		"--run-id", runID,
		"--kind", "quick",
		"--subject-type", "feature",
		"--subject-id", runID,
		"--target-ref", "HEAD",
		"--intent-sha256", strings.Repeat("b", 64),
		"--format", "json",
	)
	if code != 0 {
		t.Fatalf("create run %q = code %d envelope %#v", runID, code, payload)
	}
	return payload
}

func invokeRunCLI(t *testing.T, args ...string) (int, map[string]any) {
	t.Helper()
	var stdout, stderr bytes.Buffer
	code := Run(args, &stdout, &stderr, "test")
	if stderr.Len() != 0 {
		t.Fatalf("Run(%v) stderr = %q, want empty", args, stderr.String())
	}
	return code, decodeJSONObject(t, stdout.Bytes())
}

func supervisorRowCount(t *testing.T, database *sql.DB) int {
	t.Helper()
	var count int
	if err := database.QueryRow(`SELECT COUNT(*) FROM supervisor_instances`).Scan(&count); err != nil {
		t.Fatal(err)
	}
	return count
}
