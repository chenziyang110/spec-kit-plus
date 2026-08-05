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
	"reflect"
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

func TestRunCLICreatesIndependentWorkflowRunsConcurrently(t *testing.T) {
	root := initRunCLIRepository(t)
	type result struct {
		runID   string
		kind    string
		code    int
		payload map[string]any
		err     error
	}
	kinds := []string{"quick", "debug", "fast", "specify", "implement"}
	start := make(chan struct{})
	results := make(chan result, len(kinds))
	var workers sync.WaitGroup
	for index, kind := range kinds {
		runID := "run_cli_parallel_" + strconv.Itoa(index+1)
		workers.Add(1)
		go func(runID, kind string) {
			defer workers.Done()
			<-start
			var stdout, stderr bytes.Buffer
			code := Run([]string{
				"run", "create",
				"--project-root", root,
				"--run-id", runID,
				"--kind", kind,
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
			results <- result{runID: runID, kind: kind, code: code, payload: payload, err: decodeErr}
		}(runID, kind)
	}
	close(start)
	workers.Wait()
	close(results)

	for created := range results {
		if created.err != nil || created.code != 0 || created.payload["status"] != "ok" {
			t.Fatalf("parallel create %s = code %d error %v envelope %#v", created.runID, created.code, created.err, created.payload)
		}
		code, shown := invokeRunCLI(t, "run", "show", created.runID, "--project-root", root, "--format", "json")
		shownRun := requireObject(t, requireObject(t, shown, "data"), "run")
		if code != 0 || shownRun["status"] != "queued" || shownRun["kind"] != created.kind {
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
		{name: "launch missing argv separator", args: []string{"run", "launch", "--project-root", root, "--run-id", "missing", "--adapter-id", "test"}},
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

func TestRunCLILaunchCreatesAndSupervisesManagedRun(t *testing.T) {
	root := initRunCLIRepository(t)
	gitRun(t, root, "config", "user.name", "Run CLI Test")
	gitRun(t, root, "config", "user.email", "run-cli@example.invalid")
	gitRun(t, root, "config", "commit.gpgsign", "false")
	if err := os.WriteFile(filepath.Join(root, "README.md"), []byte("launch cli\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	gitRun(t, root, "add", "README.md")
	gitRun(t, root, "commit", "-m", "initial")
	t.Setenv("SPECIFY_RUNTIME_CLI_FOREGROUND_HELPER", "1")

	code, payload := invokeRunCLI(t,
		"run", "launch",
		"--project-root", root,
		"--run-id", "run_cli_launch",
		"--kind", "debug",
		"--subject-type", "feature",
		"--subject-id", "run_cli_launch",
		"--target-ref", "HEAD",
		"--intent-sha256", strings.Repeat("d", 64),
		"--adapter-id", "test-helper",
		"--workspace-policy", "isolated",
		"--format", "json",
		"--",
		os.Args[0], "-test.run=^TestRunCLIForegroundHelperProcess$", "--",
		"launch-marker.txt", "single-call&token",
	)
	if code != 0 || payload["status"] != "ok" {
		t.Fatalf("run launch = code %d envelope %#v", code, payload)
	}
	data := requireObject(t, payload, "data")
	run := requireObject(t, data, "run")
	execution := requireObject(t, data, "execution")
	workspaceRoot, _ := execution["workspace_root"].(string)
	if run["run_id"] != "run_cli_launch" || run["kind"] != "debug" || run["status"] != "sealed" {
		t.Fatalf("launched run = %#v", run)
	}
	marker, err := os.ReadFile(filepath.Join(workspaceRoot, "launch-marker.txt"))
	if err != nil {
		t.Fatal(err)
	}
	if string(marker) != workspaceRoot+"\nsingle-call&token" {
		t.Fatalf("launched child marker = %q", marker)
	}
	if _, err := os.Stat(filepath.Join(root, "launch-marker.txt")); !errors.Is(err, os.ErrNotExist) {
		t.Fatalf("launched child modified primary worktree: %v", err)
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
		"--workspace-policy", "isolated",
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

func TestRunCLISuperviseBindsManagedRunEnvironment(t *testing.T) {
	root := initRunCLIRepository(t)
	gitRun(t, root, "config", "user.name", "Run CLI Test")
	gitRun(t, root, "config", "user.email", "run-cli@example.invalid")
	gitRun(t, root, "config", "commit.gpgsign", "false")
	if err := os.WriteFile(filepath.Join(root, "README.md"), []byte("managed environment\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	gitRun(t, root, "add", "README.md")
	gitRun(t, root, "commit", "-m", "initial")
	createRunThroughCLI(t, root, "run_cli_environment")
	t.Setenv("SPECIFY_RUNTIME_CLI_FOREGROUND_HELPER", "1")
	t.Setenv("WSLENV", "EXISTING/u:SPECIFY_RUN_WORKSPACE")

	code, payload := invokeRunCLI(t,
		"run", "supervise", "run_cli_environment",
		"--project-root", root,
		"--adapter-id", "test-helper",
		"--workspace-policy", "isolated",
		"--format", "json",
		"--",
		os.Args[0], "-test.run=^TestRunCLIForegroundHelperProcess$", "--",
		"run-environment.txt", "__run_environment__",
	)
	if code != 0 || payload["status"] != "ok" {
		t.Fatalf("run supervise = code %d envelope %#v", code, payload)
	}
	execution := requireObject(t, requireObject(t, payload, "data"), "execution")
	workspaceRoot, _ := execution["workspace_root"].(string)
	attemptID, _ := execution["attempt_id"].(string)
	workspaceID, _ := execution["workspace_id"].(string)
	privateRef, _ := execution["private_ref"].(string)
	content, err := os.ReadFile(filepath.Join(workspaceRoot, "run-environment.txt"))
	if err != nil {
		t.Fatal(err)
	}
	lines := strings.Split(strings.TrimSpace(string(content)), "\n")
	want := []string{
		"1",
		"run_cli_environment",
		"quick",
		"feature",
		"run_cli_environment",
		"HEAD",
		attemptID,
		"1",
		workspaceID,
		"1",
		"isolated",
		workspaceRoot,
		privateRef,
	}
	if len(lines) != len(want)+1 || !reflect.DeepEqual(lines[:len(want)], want) {
		t.Fatalf("managed Run environment = %#v, want %#v", lines, want)
	}
	wslEnv := lines[len(want)]
	for _, entry := range []string{
		"EXISTING/u",
		"SPECIFY_RUN_MANAGED",
		"SPECIFY_RUN_SUBJECT_ID",
		"SPECIFY_RUN_WORKSPACE/p",
		"SPECIFY_RUN_PRIVATE_REF",
	} {
		if !strings.Contains(wslEnv, entry) {
			t.Fatalf("managed Run WSLENV = %q, missing %q", wslEnv, entry)
		}
	}
	if strings.Contains(wslEnv, "SPECIFY_RUN_WORKSPACE:") {
		t.Fatalf("managed Run WSLENV kept stale workspace entry: %q", wslEnv)
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
	content := cwd + "\n" + arguments[1]
	if arguments[1] == "__run_environment__" {
		content = strings.Join([]string{
			os.Getenv("SPECIFY_RUN_MANAGED"),
			os.Getenv("SPECIFY_RUN_ID"),
			os.Getenv("SPECIFY_RUN_KIND"),
			os.Getenv("SPECIFY_RUN_SUBJECT_TYPE"),
			os.Getenv("SPECIFY_RUN_SUBJECT_ID"),
			os.Getenv("SPECIFY_RUN_TARGET_REF"),
			os.Getenv("SPECIFY_RUN_ATTEMPT_ID"),
			os.Getenv("SPECIFY_RUN_FENCE"),
			os.Getenv("SPECIFY_RUN_WORKSPACE_ID"),
			os.Getenv("SPECIFY_RUN_WORKSPACE_GENERATION"),
			os.Getenv("SPECIFY_RUN_WORKSPACE_MODE"),
			os.Getenv("SPECIFY_RUN_WORKSPACE"),
			os.Getenv("SPECIFY_RUN_PRIVATE_REF"),
			os.Getenv("WSLENV"),
		}, "\n")
	}
	if err := os.WriteFile(
		filepath.Join(cwd, arguments[0]),
		[]byte(content),
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

func TestRunCapabilitiesPublishPublicRunControlFlowInsteadOfDirectIntegration(t *testing.T) {
	for _, capabilityID := range []string{
		"run.create",
		"run.show",
		"run.events",
		"run.cancel",
		"run.launch",
		"run.supervise",
		"result.list",
		"result.show",
		"result.reopen",
		"result.depend",
		"candidate.build",
		"candidate.show",
		"candidate.review",
		"accept.receipt",
		"cas.publish",
		"sync.safe",
	} {
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
	for _, forbidden := range []string{"run.integrate"} {
		if containsCapability(defaultCapabilities(), forbidden) {
			t.Fatalf("default capabilities still expose legacy direct integration %q", forbidden)
		}
		code, payload := invokeRunCLI(t, "api", "show", forbidden, "--format", "json")
		if code == 0 {
			t.Fatalf("api show %s = code %d envelope %#v, want missing capability", forbidden, code, payload)
		}
	}
	for _, privileged := range []string{"run.issue-attempt", "run.activate-attempt", "run.heartbeat", "run.reconcile"} {
		if containsCapability(defaultCapabilities(), privileged) {
			t.Fatalf("default capabilities expose privileged control %q", privileged)
		}
	}
}

func TestRunCLIFiveParallelWorkflowsConvergeThroughPublicDeliveryFlowWithoutWorkspaceDrift(t *testing.T) {
	root := initRunCLIRepository(t)
	gitRun(t, root, "config", "user.name", "Run CLI Test")
	gitRun(t, root, "config", "user.email", "run-cli@example.invalid")
	gitRun(t, root, "config", "commit.gpgsign", "false")
	if err := os.WriteFile(filepath.Join(root, "README.md"), []byte("public delivery flow\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	gitRun(t, root, "add", "README.md")
	gitRun(t, root, "commit", "-m", "initial")
	targetRef := strings.TrimSpace(gitRun(t, root, "symbolic-ref", "HEAD"))
	t.Setenv("SPECIFY_RUNTIME_CLI_FOREGROUND_HELPER", "1")

	filenames := []string{"feature-a.txt", "feature-b.txt", "feature-c.txt", "feature-d.txt", "feature-e.txt"}
	type launchCompletion struct {
		index  int
		code   int
		stdout []byte
		stderr string
	}
	start := make(chan struct{})
	completed := make(chan launchCompletion, len(filenames))
	var launches sync.WaitGroup
	for index, filename := range filenames {
		runID := fmt.Sprintf("run_cli_delivery_%d", index+1)
		args := []string{
			"run", "launch",
			"--project-root", root,
			"--run-id", runID,
			"--kind", "quick",
			"--subject-type", "feature",
			"--subject-id", runID,
			"--target-ref", targetRef,
			"--intent-sha256", strings.Repeat(strconv.Itoa(index+1), 64),
			"--adapter-id", "test-helper",
			"--format", "json",
			"--",
			os.Args[0], "-test.run=^TestRunCLIForegroundHelperProcess$", "--",
			filename, runID,
		}
		launches.Add(1)
		go func(index int, args []string) {
			defer launches.Done()
			<-start
			var stdout, stderr bytes.Buffer
			code := Run(args, &stdout, &stderr, "test")
			completed <- launchCompletion{
				index:  index,
				code:   code,
				stdout: append([]byte(nil), stdout.Bytes()...),
				stderr: stderr.String(),
			}
		}(index, args)
	}
	close(start)
	launches.Wait()
	close(completed)

	ordered := make([]launchCompletion, len(filenames))
	for completion := range completed {
		ordered[completion.index] = completion
	}
	resultIDs := make([]string, 0, len(filenames))
	workspaceModes := map[string]int{}
	for index, completion := range ordered {
		runID := fmt.Sprintf("run_cli_delivery_%d", index+1)
		if completion.stderr != "" {
			t.Fatalf("run launch %s stderr = %q", runID, completion.stderr)
		}
		payload := decodeJSONObject(t, completion.stdout)
		code := completion.code
		if code != 0 || payload["status"] != "ok" {
			t.Fatalf("run launch %s = code %d envelope %#v", runID, code, payload)
		}
		execution := requireObject(t, requireObject(t, payload, "data"), "execution")
		resultID, _ := execution["result_id"].(string)
		workspaceMode, _ := execution["workspace_mode"].(string)
		if resultID == "" || (workspaceMode != "primary" && workspaceMode != "isolated") || execution["result_eligibility"] != "ready" {
			t.Fatalf("sealed execution %s = %#v", runID, execution)
		}
		workspaceModes[workspaceMode]++
		resultIDs = append(resultIDs, resultID)
	}
	if workspaceModes["primary"] != 1 || workspaceModes["isolated"] != len(filenames)-1 {
		t.Fatalf("automatic workspace routes = %#v, want one primary and %d isolated", workspaceModes, len(filenames)-1)
	}

	code, listed := invokeRunCLI(t, "result", "list", "run_cli_delivery_1", "--project-root", root, "--format", "json")
	if code != 0 || listed["status"] != "ok" {
		t.Fatalf("result list = code %d envelope %#v", code, listed)
	}
	items, _ := listed["items"].([]any)
	if len(items) != 1 || requireObjectValue(t, items[0])["result_id"] != resultIDs[0] {
		t.Fatalf("result list items = %#v", items)
	}
	code, shownResult := invokeRunCLI(t, "result", "show", resultIDs[0], "--project-root", root, "--format", "json")
	if code != 0 || requireObject(t, requireObject(t, shownResult, "data"), "result")["manifest_sha256"] == "" {
		t.Fatalf("result show = code %d envelope %#v", code, shownResult)
	}
	code, dependency := invokeRunCLI(t,
		"result", "depend", resultIDs[1],
		"--project-root", root,
		"--on", resultIDs[0],
		"--kind", "after",
		"--reason", "feature-b follows feature-a",
		"--format", "json",
	)
	if code != 0 || dependency["status"] != "ok" {
		t.Fatalf("result depend = code %d envelope %#v", code, dependency)
	}
	code, shownDependent := invokeRunCLI(t, "result", "show", resultIDs[1], "--project-root", root, "--format", "json")
	dependencies, _ := requireObject(t, shownDependent, "data")["dependencies"].([]any)
	if code != 0 || len(dependencies) != 1 || requireObjectValue(t, dependencies[0])["depends_on_result_id"] != resultIDs[0] {
		t.Fatalf("dependent result show = code %d envelope %#v", code, shownDependent)
	}

	buildArgs := []string{"candidate", "build", "--project-root", root, "--target-ref", targetRef}
	for _, resultID := range resultIDs {
		buildArgs = append(buildArgs, "--result", resultID)
	}
	buildArgs = append(buildArgs, "--format", "json")
	code, built := invokeRunCLI(t, buildArgs...)
	if code != 0 || built["status"] != "ok" {
		t.Fatalf("candidate build = code %d envelope %#v", code, built)
	}
	candidate := requireObject(t, requireObject(t, built, "data"), "candidate")
	candidateID, _ := candidate["candidate_id"].(string)
	if candidateID == "" {
		t.Fatalf("candidate build = %#v", candidate)
	}

	repository, err := runcontrol.ResolveRepository(context.Background(), root)
	if err != nil {
		t.Fatal(err)
	}
	database, err := sql.Open("sqlite", repository.DatabasePath)
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { _ = database.Close() })
	beforeReadOnly := supervisorRowCount(t, database)
	code, shownCandidate := invokeRunCLI(t, "candidate", "show", candidateID, "--project-root", root, "--format", "json")
	if code != 0 || requireObject(t, requireObject(t, shownCandidate, "data"), "candidate")["manifest_sha256"] != candidate["manifest_sha256"] {
		t.Fatalf("candidate show = code %d envelope %#v", code, shownCandidate)
	}
	if afterReadOnly := supervisorRowCount(t, database); afterReadOnly != beforeReadOnly {
		t.Fatalf("read-only result/candidate queries registered supervisors: before=%d after=%d", beforeReadOnly, afterReadOnly)
	}

	code, reviewed := invokeRunCLI(t,
		"candidate", "review", candidateID,
		"--project-root", root,
		"--reviewer", "runtime-reviewer",
		"--format", "json",
		"--", "git", "diff", "--quiet",
	)
	if code != 0 || reviewed["status"] != "ok" {
		t.Fatalf("candidate review = code %d envelope %#v", code, reviewed)
	}
	review := requireObject(t, requireObject(t, reviewed, "data"), "review")
	reviewDigest, _ := review["review_digest"].(string)
	if review["status"] != "passed" || reviewDigest == "" {
		t.Fatalf("candidate review = %#v", review)
	}

	acceptanceInput, err := json.Marshal(map[string]any{
		"candidate_id":  candidateID,
		"review_digest": reviewDigest,
		"decision":      "accepted",
		"actor":         "human:test-user",
	})
	if err != nil {
		t.Fatal(err)
	}
	code, accepted := invokeRunCLI(t,
		"accept", "receipt",
		"--project-root", root,
		"--input-json", string(acceptanceInput),
		"--format", "json",
	)
	if code != 0 || accepted["status"] != "ok" {
		t.Fatalf("accept receipt = code %d envelope %#v", code, accepted)
	}
	acceptance := requireObject(t, requireObject(t, accepted, "data"), "acceptance")
	acceptanceDigest, _ := acceptance["acceptance_digest"].(string)
	if acceptance["decision"] != "accepted" || acceptanceDigest == "" {
		t.Fatalf("acceptance receipt = %#v", acceptance)
	}

	code, published := invokeRunCLI(t,
		"cas", "publish", candidateID,
		"--project-root", root,
		"--acceptance-digest", acceptanceDigest,
		"--format", "json",
	)
	if code != 0 || published["status"] != "ok" {
		t.Fatalf("cas publish = code %d envelope %#v", code, published)
	}
	publication := requireObject(t, requireObject(t, published, "data"), "publication")
	publicationDigest, _ := publication["publication_digest"].(string)
	if publication["status"] != "succeeded" || publicationDigest == "" {
		t.Fatalf("publication receipt = %#v", publication)
	}

	code, synced := invokeRunCLI(t,
		"sync", "safe", candidateID,
		"--project-root", root,
		"--publication-digest", publicationDigest,
		"--target-ref", targetRef,
		"--format", "json",
	)
	if code != 0 || synced["status"] != "ok" {
		t.Fatalf("sync safe = code %d envelope %#v", code, synced)
	}
	for _, filename := range filenames {
		if _, err := os.Stat(filepath.Join(root, filename)); err != nil {
			t.Fatalf("published file %s is missing after safe sync: %v", filename, err)
		}
	}
	if status := strings.TrimSpace(gitRun(t, root, "status", "--porcelain")); status != "" {
		t.Fatalf("primary worktree after safe sync is dirty: %q", status)
	}
	code, deliveryState := invokeRunCLI(t, "candidate", "show", candidateID, "--project-root", root, "--format", "json")
	if code != 0 {
		t.Fatalf("candidate delivery state = code %d envelope %#v", code, deliveryState)
	}
	deliveryData := requireObject(t, deliveryState, "data")
	for _, key := range []string{"review", "acceptance", "publication", "sync"} {
		if _, ok := deliveryData[key].(map[string]any); !ok {
			t.Fatalf("candidate delivery state missing %s: %#v", key, deliveryData)
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
