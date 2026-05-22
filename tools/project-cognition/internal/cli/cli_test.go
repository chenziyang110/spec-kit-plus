package cli

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"testing"
	"time"
)

func TestVersionPrintsBinaryName(t *testing.T) {
	var stdout, stderr bytes.Buffer
	code := Run([]string{"--version"}, &stdout, &stderr, "v1.2.3")
	if code != 0 {
		t.Fatalf("code = %d stderr=%s", code, stderr.String())
	}
	if strings.TrimSpace(stdout.String()) != "project-cognition v1.2.3" {
		t.Fatalf("stdout = %q", stdout.String())
	}
}

func TestStatusReturnsUnsupportedLegacyJSON(t *testing.T) {
	root := t.TempDir()
	dir := filepath.Join(root, ".specify", "project-cognition")
	if err := os.MkdirAll(dir, 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(dir, "status.json"), []byte(`{"freshness":"fresh"}`), 0o644); err != nil {
		t.Fatal(err)
	}
	old, _ := os.Getwd()
	if err := os.Chdir(root); err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { _ = os.Chdir(old) })

	var stdout, stderr bytes.Buffer
	code := Run([]string{"status", "--format", "json"}, &stdout, &stderr, "test")
	if code != 0 {
		t.Fatalf("code = %d stderr=%s", code, stderr.String())
	}
	var payload map[string]any
	if err := json.Unmarshal(stdout.Bytes(), &payload); err != nil {
		t.Fatal(err)
	}
	if payload["error_code"] != "unsupported_legacy_runtime" {
		t.Fatalf("payload = %#v", payload)
	}
}

func TestDeltaBeginCommandCreatesSession(t *testing.T) {
	root := t.TempDir()
	if err := os.Mkdir(filepath.Join(root, ".specify"), 0o755); err != nil {
		t.Fatal(err)
	}
	old, _ := os.Getwd()
	if err := os.Chdir(root); err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { _ = os.Chdir(old) })

	var stdout, stderr bytes.Buffer
	code := Run([]string{"delta", "begin", "--origin-command", "quick", "--format", "json"}, &stdout, &stderr, "test")
	if code != 0 {
		t.Fatalf("code = %d stderr=%s", code, stderr.String())
	}
	var payload map[string]any
	if err := json.Unmarshal(stdout.Bytes(), &payload); err != nil {
		t.Fatal(err)
	}
	if payload["session_id"] == "" {
		t.Fatalf("payload = %#v", payload)
	}
}

func TestDeltaBeginCommandCapturesGitMetadata(t *testing.T) {
	root := t.TempDir()
	runGit(t, root, "init")
	runGit(t, root, "checkout", "-b", "main")
	runGit(t, root, "config", "user.email", "test@example.com")
	runGit(t, root, "config", "user.name", "Test User")
	if err := os.Mkdir(filepath.Join(root, ".specify"), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(root, ".specify", ".keep"), []byte("keep\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	runGit(t, root, "add", ".specify/.keep")
	runGit(t, root, "commit", "-m", "initial")
	wantHead := strings.TrimSpace(runGit(t, root, "rev-parse", "HEAD"))

	old, _ := os.Getwd()
	if err := os.Chdir(root); err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { _ = os.Chdir(old) })

	var stdout, stderr bytes.Buffer
	code := Run([]string{"delta", "begin", "--origin-command", "quick", "--format", "json"}, &stdout, &stderr, "test")
	if code != 0 {
		t.Fatalf("code = %d stderr=%s", code, stderr.String())
	}
	var payload map[string]any
	if err := json.Unmarshal(stdout.Bytes(), &payload); err != nil {
		t.Fatal(err)
	}
	gitPayload, ok := payload["git"].(map[string]any)
	if !ok {
		t.Fatalf("payload = %#v", payload)
	}
	if gitPayload["base_commit"] != wantHead {
		t.Fatalf("base_commit = %#v, want %q", gitPayload["base_commit"], wantHead)
	}
	if gitPayload["branch"] != "main" {
		t.Fatalf("branch = %#v, want main", gitPayload["branch"])
	}
}

func TestDeltaGitMetadataSkipsDirtyPathsOnTimeout(t *testing.T) {
	root := t.TempDir()
	if err := os.Mkdir(filepath.Join(root, ".git"), 0o755); err != nil {
		t.Fatal(err)
	}
	calls := []string{}
	runner := func(ctx context.Context, root string, args ...string) (string, error) {
		command := strings.Join(args, " ")
		calls = append(calls, command)
		if len(args) >= 2 && args[0] == "rev-parse" && args[1] == "--is-inside-work-tree" {
			return "true\n", nil
		}
		if len(args) >= 2 && args[0] == "rev-parse" && args[1] == "HEAD" {
			return "abc123\n", nil
		}
		if len(args) >= 2 && args[0] == "branch" && args[1] == "--show-current" {
			return "main\n", nil
		}
		if command == "status --porcelain=v1 -z --untracked-files=all" {
			return "", context.DeadlineExceeded
		}
		return "", errors.New("unexpected git command: " + command)
	}

	metadata := collectDeltaGitMetadata(root, time.Millisecond, runner)

	if metadata.baseCommit != "abc123" {
		t.Fatalf("baseCommit = %q", metadata.baseCommit)
	}
	if metadata.branch != "main" {
		t.Fatalf("branch = %q", metadata.branch)
	}
	if len(metadata.initialDirty) != 0 {
		t.Fatalf("initialDirty = %#v", metadata.initialDirty)
	}
	if !hasCall(calls, "status --porcelain=v1 -z --untracked-files=all") {
		t.Fatalf("calls = %#v", calls)
	}
}

func TestDeltaGitMetadataCapturesDirtyPathsWithoutRootGitDirectory(t *testing.T) {
	root := t.TempDir()
	calls := []string{}
	runner := func(ctx context.Context, root string, args ...string) (string, error) {
		command := strings.Join(args, " ")
		calls = append(calls, command)
		switch command {
		case "rev-parse --is-inside-work-tree":
			return "true\n", nil
		case "rev-parse HEAD":
			return "abc123\n", nil
		case "branch --show-current":
			return "main\n", nil
		case "status --porcelain=v1 -z --untracked-files=all":
			return " M src/a.go\x00", nil
		default:
			return "", errors.New("unexpected git command: " + command)
		}
	}

	metadata := collectDeltaGitMetadata(root, time.Millisecond, runner)

	if !hasCall(calls, "status --porcelain=v1 -z --untracked-files=all") {
		t.Fatalf("calls = %#v", calls)
	}
	if got := metadata.initialDirty; len(got) != 1 || got[0] != "src/a.go" {
		t.Fatalf("initialDirty = %#v, want src/a.go", got)
	}
}

func TestDeltaGitMetadataParsesRawZStatusNonASCIIPath(t *testing.T) {
	root := t.TempDir()
	calls := []string{}
	runner := func(ctx context.Context, root string, args ...string) (string, error) {
		command := strings.Join(args, " ")
		calls = append(calls, command)
		switch command {
		case "rev-parse --is-inside-work-tree":
			return "true\n", nil
		case "rev-parse HEAD":
			return "abc123\n", nil
		case "branch --show-current":
			return "main\n", nil
		case "status --porcelain=v1 -z --untracked-files=all":
			return "?? café.go\x00", nil
		default:
			return "", errors.New("unexpected git command: " + command)
		}
	}

	metadata := collectDeltaGitMetadata(root, time.Millisecond, runner)

	if !hasCall(calls, "status --porcelain=v1 -z --untracked-files=all") {
		t.Fatalf("calls = %#v", calls)
	}
	if got := metadata.initialDirty; len(got) != 1 || got[0] != "café.go" {
		t.Fatalf("initialDirty = %#v, want café.go", got)
	}
}

func TestParseDeltaGitStatusZKeepsRenameTargetPath(t *testing.T) {
	paths := parseDeltaGitStatusZ("R  new.txt\x00old.txt\x00")

	if got := paths; len(got) != 1 || got[0] != "new.txt" {
		t.Fatalf("paths = %#v, want new.txt", got)
	}
	if hasString(paths, "old.txt") {
		t.Fatalf("paths = %#v, did not want old.txt", paths)
	}
}

func TestDeltaAppendCommandWritesEvent(t *testing.T) {
	root := t.TempDir()
	if err := os.Mkdir(filepath.Join(root, ".specify"), 0o755); err != nil {
		t.Fatal(err)
	}
	old, _ := os.Getwd()
	if err := os.Chdir(root); err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { _ = os.Chdir(old) })

	sessionID := beginDeltaSession(t)
	var stdout, stderr bytes.Buffer
	code := Run([]string{
		"delta", "append",
		"--session", sessionID,
		"--event-type", "worker_result",
		"--changed-path", "src/a.go",
		"--verification", "go test ./... PASS",
		"--format", "json",
	}, &stdout, &stderr, "test")
	if code != 0 {
		t.Fatalf("code = %d stderr=%s", code, stderr.String())
	}
	var payload map[string]any
	if err := json.Unmarshal(stdout.Bytes(), &payload); err != nil {
		t.Fatal(err)
	}
	if payload["event_id"] == "" {
		t.Fatalf("payload = %#v", payload)
	}
}

func TestDeltaAppendCommandAcceptsPacketFile(t *testing.T) {
	root := t.TempDir()
	if err := os.Mkdir(filepath.Join(root, ".specify"), 0o755); err != nil {
		t.Fatal(err)
	}
	old, _ := os.Getwd()
	if err := os.Chdir(root); err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { _ = os.Chdir(old) })

	sessionID := beginDeltaSession(t)
	packet := filepath.Join(root, "packet.json")
	data := []byte(`{"event_type":"worker_result","changed_paths":["src/a.go"],"verification_evidence":["go test ./... PASS"]}`)
	if err := os.WriteFile(packet, data, 0o644); err != nil {
		t.Fatal(err)
	}

	var stdout, stderr bytes.Buffer
	code := Run([]string{
		"delta", "append",
		"--session", sessionID,
		"--packet-file", packet,
		"--format", "json",
	}, &stdout, &stderr, "test")
	if code != 0 {
		t.Fatalf("code = %d stderr=%s", code, stderr.String())
	}
	var payload map[string]any
	if err := json.Unmarshal(stdout.Bytes(), &payload); err != nil {
		t.Fatal(err)
	}
	if payload["event_type"] != "worker_result" {
		t.Fatalf("payload = %#v", payload)
	}
}

func TestUpdateCommandAcceptsDeltaSession(t *testing.T) {
	root := t.TempDir()
	if err := os.Mkdir(filepath.Join(root, ".specify"), 0o755); err != nil {
		t.Fatal(err)
	}
	old, _ := os.Getwd()
	if err := os.Chdir(root); err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { _ = os.Chdir(old) })

	sessionID := beginDeltaSession(t)
	var appendStdout, appendStderr bytes.Buffer
	appendCode := Run([]string{
		"delta", "append",
		"--session", sessionID,
		"--event-type", "worker_result",
		"--changed-path", "src/a.go",
		"--format", "json",
	}, &appendStdout, &appendStderr, "test")
	if appendCode != 0 {
		t.Fatalf("append code = %d stderr=%s", appendCode, appendStderr.String())
	}

	var stdout, stderr bytes.Buffer
	code := Run([]string{
		"update",
		"--delta-session", sessionID,
		"--reason", "workflow-finalize",
		"--format", "json",
	}, &stdout, &stderr, "test")
	if code != 0 {
		t.Fatalf("code = %d stderr=%s", code, stderr.String())
	}
	var payload map[string]any
	if err := json.Unmarshal(stdout.Bytes(), &payload); err != nil {
		t.Fatal(err)
	}
	if payload["update_outcome"] != "boundary_resolved" {
		t.Fatalf("payload = %#v", payload)
	}
	if payload["readiness"] == "query_ready" {
		t.Fatalf("payload = %#v", payload)
	}
}

func TestUpdateCommandTreatsQuotedInitialDirtyUnicodePathAsAmbiguous(t *testing.T) {
	root := t.TempDir()
	runGit(t, root, "init")
	runGit(t, root, "checkout", "-b", "main")
	runGit(t, root, "config", "user.email", "test@example.com")
	runGit(t, root, "config", "user.name", "Test User")
	runGit(t, root, "config", "core.quotePath", "true")
	if err := os.Mkdir(filepath.Join(root, ".specify"), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(root, ".specify", ".keep"), []byte("keep\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	runGit(t, root, "add", ".specify/.keep")
	runGit(t, root, "commit", "-m", "initial")
	if err := os.WriteFile(filepath.Join(root, "café.go"), []byte("package demo\n"), 0o644); err != nil {
		t.Fatal(err)
	}

	old, _ := os.Getwd()
	if err := os.Chdir(root); err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { _ = os.Chdir(old) })

	sessionID := beginDeltaSession(t)
	var appendStdout, appendStderr bytes.Buffer
	appendCode := Run([]string{
		"delta", "append",
		"--session", sessionID,
		"--event-type", "worker_result",
		"--changed-path", "café.go",
		"--format", "json",
	}, &appendStdout, &appendStderr, "test")
	if appendCode != 0 {
		t.Fatalf("append code = %d stderr=%s", appendCode, appendStderr.String())
	}

	var stdout, stderr bytes.Buffer
	code := Run([]string{
		"update",
		"--delta-session", sessionID,
		"--reason", "workflow-finalize",
		"--format", "json",
	}, &stdout, &stderr, "test")
	if code != 0 {
		t.Fatalf("code = %d stderr=%s", code, stderr.String())
	}
	var payload map[string]any
	if err := json.Unmarshal(stdout.Bytes(), &payload); err != nil {
		t.Fatal(err)
	}
	boundary, ok := payload["boundary"].(map[string]any)
	if !ok {
		t.Fatalf("payload = %#v", payload)
	}
	if !jsonStringSliceContains(boundary["ambiguous_paths"], "café.go") {
		t.Fatalf("boundary ambiguous_paths = %#v, want café.go", boundary["ambiguous_paths"])
	}
	if jsonStringSliceContains(boundary["workflow_owned_paths"], "café.go") {
		t.Fatalf("boundary workflow_owned_paths = %#v, did not want café.go", boundary["workflow_owned_paths"])
	}
}

func TestUpdateCommandTreatsStagedRenameTargetAsAmbiguous(t *testing.T) {
	root := t.TempDir()
	runGit(t, root, "init")
	runGit(t, root, "checkout", "-b", "main")
	runGit(t, root, "config", "user.email", "test@example.com")
	runGit(t, root, "config", "user.name", "Test User")
	if err := os.Mkdir(filepath.Join(root, ".specify"), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(root, ".specify", ".keep"), []byte("keep\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(root, "old.txt"), []byte("old\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	runGit(t, root, "add", ".specify/.keep", "old.txt")
	runGit(t, root, "commit", "-m", "initial")
	runGit(t, root, "mv", "old.txt", "new.txt")

	old, _ := os.Getwd()
	if err := os.Chdir(root); err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { _ = os.Chdir(old) })

	sessionID := beginDeltaSession(t)
	var appendStdout, appendStderr bytes.Buffer
	appendCode := Run([]string{
		"delta", "append",
		"--session", sessionID,
		"--event-type", "worker_result",
		"--changed-path", "new.txt",
		"--format", "json",
	}, &appendStdout, &appendStderr, "test")
	if appendCode != 0 {
		t.Fatalf("append code = %d stderr=%s", appendCode, appendStderr.String())
	}

	var stdout, stderr bytes.Buffer
	code := Run([]string{
		"update",
		"--delta-session", sessionID,
		"--reason", "workflow-finalize",
		"--format", "json",
	}, &stdout, &stderr, "test")
	if code != 0 {
		t.Fatalf("code = %d stderr=%s", code, stderr.String())
	}
	var payload map[string]any
	if err := json.Unmarshal(stdout.Bytes(), &payload); err != nil {
		t.Fatal(err)
	}
	boundary, ok := payload["boundary"].(map[string]any)
	if !ok {
		t.Fatalf("payload = %#v", payload)
	}
	if !jsonStringSliceContains(boundary["ambiguous_paths"], "new.txt") {
		t.Fatalf("boundary ambiguous_paths = %#v, want new.txt", boundary["ambiguous_paths"])
	}
	if jsonStringSliceContains(boundary["workflow_owned_paths"], "new.txt") {
		t.Fatalf("boundary workflow_owned_paths = %#v, did not want new.txt", boundary["workflow_owned_paths"])
	}
}

func TestUpdateCommandRejectsBadDeltaCommitRange(t *testing.T) {
	root := t.TempDir()
	if err := os.Mkdir(filepath.Join(root, ".specify"), 0o755); err != nil {
		t.Fatal(err)
	}
	old, _ := os.Getwd()
	if err := os.Chdir(root); err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { _ = os.Chdir(old) })

	sessionID := beginDeltaSession(t)
	var stdout, stderr bytes.Buffer
	code := Run([]string{
		"update",
		"--delta-session", sessionID,
		"--commit-range", "bad-range",
		"--reason", "workflow-finalize",
		"--format", "json",
	}, &stdout, &stderr, "test")
	if code == 0 {
		t.Fatalf("code = %d stdout=%s stderr=%s, want non-zero", code, stdout.String(), stderr.String())
	}
}

func beginDeltaSession(t *testing.T) string {
	t.Helper()
	var stdout, stderr bytes.Buffer
	code := Run([]string{"delta", "begin", "--origin-command", "quick", "--format", "json"}, &stdout, &stderr, "test")
	if code != 0 {
		t.Fatalf("begin code = %d stderr=%s", code, stderr.String())
	}
	var payload map[string]any
	if err := json.Unmarshal(stdout.Bytes(), &payload); err != nil {
		t.Fatal(err)
	}
	sessionID, ok := payload["session_id"].(string)
	if !ok || sessionID == "" {
		t.Fatalf("payload = %#v", payload)
	}
	return sessionID
}

func runGit(t *testing.T, dir string, args ...string) string {
	t.Helper()
	cmd := exec.Command("git", args...)
	cmd.Dir = dir
	data, err := cmd.CombinedOutput()
	if err != nil {
		t.Fatalf("git %s failed: %v\n%s", strings.Join(args, " "), err, data)
	}
	return string(data)
}

func hasCall(calls []string, want string) bool {
	for _, call := range calls {
		if call == want {
			return true
		}
	}
	return false
}

func hasString(values []string, want string) bool {
	for _, value := range values {
		if value == want {
			return true
		}
	}
	return false
}

func jsonStringSliceContains(value any, want string) bool {
	values, ok := value.([]any)
	if !ok {
		return false
	}
	for _, value := range values {
		if text, ok := value.(string); ok && text == want {
			return true
		}
	}
	return false
}
