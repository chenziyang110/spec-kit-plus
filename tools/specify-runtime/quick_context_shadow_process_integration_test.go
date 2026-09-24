package main

import (
	"bytes"
	"encoding/json"
	"io"
	"os"
	"reflect"
	"testing"
	"time"
)

// These tests connect the real watchdog, RunContext, Quick adapter, Git child,
// confirmation reader, owner packet builder, compiler and runtime JSON writer.
// A synthetic confirmed document is not human acceptance or live-code evidence.
func TestQuickShadowCLIProcessRoundTripReadOnly(t *testing.T) {
	service, doc := shadowTestRepo(t)
	doc.Decision.UIConfirmation["large_integer"] = json.Number("9007199254740993")
	doc.Decision.UIConfirmation["long_decimal"] = json.Number("0.12345678901234567890123456789")
	statePath := shadowTestWrite(t, service.projectRoot, doc)
	before := shadowTestFiles(t, service.projectRoot)
	args := []string{"quick", "context-shadow", "--workspace", doc.Workspace,
		"--item", "Q1", "--project-root", service.projectRoot, "--format", "json"}
	var stdout, stderr bytes.Buffer
	code := runWithWatchdog(args, &stdout, &stderr, "test", defaultRuntimeQueryTimeout, RunContext)
	if code != 0 || stderr.Len() != 0 || stdout.Len() > quickShadowCLIOutputLimit {
		t.Fatalf("process wrapper failed: code=%d stderr=%s", code, stderr.String())
	}
	var env Envelope
	decoder := json.NewDecoder(bytes.NewReader(stdout.Bytes()))
	decoder.UseNumber()
	if err := decoder.Decode(&env); err != nil {
		t.Fatal(err)
	}
	if err := decoder.Decode(new(any)); err != io.EOF {
		t.Fatal("expected exactly one complete response", err)
	}
	if env.Status != "ok" || env.Data["authorizes_execution"] != false ||
		env.Data["claim_ready"] != false || len(env.NextArgv) != 0 {
		t.Fatal("diagnostic acquired authority or automatic continuation", env)
	}
	report, ok := env.Data["report"].(map[string]any)
	if !ok || report["mode"] != "shadow-only" || report["authorizes_execution"] != false ||
		report["live_code_verified"] != false {
		t.Fatal("missing complete non-authorizing report", report)
	}
	raw, err := os.ReadFile(statePath)
	if err != nil {
		t.Fatal(err)
	}
	current, err := decodeQuickShadowConfirmation(raw)
	if err != nil {
		t.Fatal(err)
	}
	owner, ready, _, err := compileQuickWorkerPacket(&current, "Q1")
	if err != nil || !ready {
		t.Fatal("fixture owner was not readable", err)
	}
	want, err := json.Marshal(owner)
	if err != nil {
		t.Fatal(err)
	}
	got, err := json.Marshal(report["owner_packet"])
	if err != nil || !bytes.Equal(want, got) {
		t.Fatal("owner contract changed across process output", err)
	}
	for _, number := range []string{"9007199254740993", "0.12345678901234567890123456789"} {
		if !bytes.Contains(stdout.Bytes(), []byte(number)) {
			t.Fatal("exact number was lost at the process boundary", number)
		}
	}
	if !reflect.DeepEqual(before, shadowTestFiles(t, service.projectRoot)) {
		t.Fatal("read-only process path modified project or Git files")
	}
}

func TestQuickShadowCLIProcessClosedPipeIsFailure(t *testing.T) {
	service, doc := shadowTestRepo(t)
	before := shadowTestFiles(t, service.projectRoot)
	reader, writer, err := os.Pipe()
	if err != nil {
		t.Fatal(err)
	}
	defer writer.Close()
	if err := reader.Close(); err != nil {
		t.Fatal(err)
	}
	var stderr bytes.Buffer
	code := runWithWatchdog([]string{"quick", "context-shadow", "--workspace", doc.Workspace,
		"--item", "Q1", "--project-root", service.projectRoot}, writer, &stderr,
		"test", defaultRuntimeQueryTimeout, RunContext)
	if code != 1 {
		t.Fatalf("real command output to a closed pipe returned %d, want delivery failure", code)
	}
	if !reflect.DeepEqual(before, shadowTestFiles(t, service.projectRoot)) {
		t.Fatal("delivery failure changed the existing owner state")
	}
}

func TestQuickShadowCLIProcessTimeoutCancelsStartedGit(t *testing.T) {
	root, marker := shadowInstallGitHelper(t, "hang")
	before := shadowTestFiles(t, root)
	var stdout, stderr bytes.Buffer
	code := runWithWatchdog([]string{"quick", "context-shadow", "--workspace", "demo",
		"--item", "Q1", "--project-root", root}, &stdout, &stderr, "test", 2*time.Second, RunContext)
	if _, err := os.Stat(marker); err != nil {
		t.Fatal("test did not observe the real Git helper starting", err)
	}
	var env Envelope
	if err := json.Unmarshal(stdout.Bytes(), &env); err != nil {
		t.Fatal("timeout did not return exactly one JSON document", err)
	}
	if code != 10 || env.Status != "blocked" || env.Data["operation"] != "quick.context-shadow" ||
		env.Data["error_code"] != "runtime-command-timeout" ||
		env.Data["cancellation_requested"] != true || env.Data["command_returned"] != true ||
		env.Data["side_effects_unknown"] != true || len(env.NextArgv) != 0 {
		t.Fatal("timeout did not traverse the real cancellation path", code, env)
	}
	if _, ok := env.Data["report"]; ok {
		t.Fatal("late snapshot escaped the timed-out process wrapper")
	}
	if stderr.Len() != 0 || !reflect.DeepEqual(before, shadowTestFiles(t, root)) {
		t.Fatal("cancelled read wrote diagnostics or changed the selected project")
	}
}
