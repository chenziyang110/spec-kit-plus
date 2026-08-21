package main

import (
	"bytes"
	"context"
	"encoding/json"
	"io"
	"strings"
	"testing"
	"time"

	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/runcontrol"
)

type notifyingWriter struct {
	wrote chan struct{}
	bytes.Buffer
}

func (writer *notifyingWriter) Write(value []byte) (int, error) {
	select {
	case writer.wrote <- struct{}{}:
	default:
	}
	return writer.Buffer.Write(value)
}

func TestRuntimeCommandTimeoutUsesShortBudgetForQueries(t *testing.T) {
	t.Setenv(runtimeTimeoutEnv, "")

	tests := []struct {
		args []string
		want time.Duration
	}{
		{args: []string{"quick", "status", "Q-123"}, want: 30 * time.Second},
		{args: []string{"artifact", "show", "--path", "spec.md"}, want: 30 * time.Second},
		{args: []string{"validate", "spec"}, want: 5 * time.Minute},
		{args: []string{"run", "launch", "--", "codex", "exec"}, want: 6 * time.Hour},
		{args: []string{"run", "supervise", "run-123", "--", "codex", "exec"}, want: 6 * time.Hour},
	}
	for _, test := range tests {
		got, err := runtimeCommandTimeout(test.args)
		if err != nil {
			t.Fatalf("runtimeCommandTimeout(%v) error = %v", test.args, err)
		}
		if got != test.want {
			t.Fatalf("runtimeCommandTimeout(%v) = %s, want %s", test.args, got, test.want)
		}
	}
}

func TestRuntimeCommandTimeoutRejectsAnUnboundedOverride(t *testing.T) {
	t.Setenv(runtimeTimeoutEnv, "0")

	if _, err := runtimeCommandTimeout([]string{"api", "list"}); err == nil {
		t.Fatal("runtimeCommandTimeout accepted zero timeout")
	}
}

func TestRunWithWatchdogReturnsStructuredBlockInsteadOfHanging(t *testing.T) {
	runner := func(ctx context.Context, _ []string, _, _ io.Writer, _ string) int {
		<-ctx.Done()
		return 0
	}
	var stdout, stderr bytes.Buffer
	started := time.Now()

	code := runWithWatchdog(
		[]string{"quick", "status", "Q-123", "--format", "json"},
		&stdout,
		&stderr,
		"test",
		20*time.Millisecond,
		runner,
	)

	if elapsed := time.Since(started); elapsed > time.Second {
		t.Fatalf("watchdog returned after %s, want under 1s", elapsed)
	}
	if code != 10 {
		t.Fatalf("watchdog exit code = %d, want 10; stdout=%s", code, stdout.String())
	}
	if stderr.Len() != 0 {
		t.Fatalf("watchdog stderr = %q, want empty", stderr.String())
	}
	var payload map[string]any
	if err := json.Unmarshal(stdout.Bytes(), &payload); err != nil {
		t.Fatalf("watchdog stdout is not JSON: %v; stdout=%q", err, stdout.String())
	}
	if payload["status"] != "blocked" || payload["summary"] != "runtime command timed out" {
		t.Fatalf("watchdog payload = %#v", payload)
	}
	data, ok := payload["data"].(map[string]any)
	if !ok || data["operation"] != "quick.status" {
		t.Fatalf("watchdog data = %#v, want operation quick.status", payload["data"])
	}
}

func TestRuntimeHelpDocumentsBoundedCommandTimeouts(t *testing.T) {
	var stdout, stderr bytes.Buffer

	code := Run([]string{"--help"}, &stdout, &stderr, "test")

	if code != 0 {
		t.Fatalf("help exit code = %d, want 0", code)
	}
	for _, expected := range []string{
		runtimeTimeoutEnv,
		"queries: 30s",
		"commands: 5m0s",
		"run launch/supervise: 6h0m0s",
		"cannot disable the watchdog",
	} {
		if !strings.Contains(stdout.String(), expected) {
			t.Fatalf("help output missing %q:\n%s", expected, stdout.String())
		}
	}
}

func TestSupervisedRuntimeTimeoutStreamsAndCancelsContext(t *testing.T) {
	var stdout bytes.Buffer
	stderr := &notifyingWriter{wrote: make(chan struct{}, 1)}
	done := make(chan int, 1)
	runner := func(ctx context.Context, _ []string, stdout, stderr io.Writer, _ string) int {
		_, _ = stderr.Write([]byte("live child output\n"))
		<-ctx.Done()
		env := NewEnvelope("blocked", "runtime command timed out")
		return writeEnvelope(stdout, env)
	}

	go func() {
		done <- runSupervisedWithTimeout(
			[]string{"run", "launch"},
			&stdout,
			stderr,
			"test",
			500*time.Millisecond,
			runner,
		)
	}()

	select {
	case <-stderr.wrote:
		// Live output arrived before the command deadline.
	case <-time.After(250 * time.Millisecond):
		t.Fatal("supervised child output was buffered instead of streamed")
	}
	select {
	case code := <-done:
		if code != 10 {
			t.Fatalf("supervised timeout exit code = %d, want 10", code)
		}
	case <-time.After(time.Second):
		t.Fatal("supervised runtime did not return after its context deadline")
	}
}

func TestRunSupervisionDeadlineReturnsStructuredTimeoutBlock(t *testing.T) {
	ctx, cancel := context.WithTimeout(context.Background(), time.Nanosecond)
	defer cancel()
	<-ctx.Done()
	var stdout bytes.Buffer

	code := writeRunSupervisionEnvelope(
		&stdout,
		ctx,
		"run.launch",
		"run-timeout",
		".",
		runcontrol.SupervisedRun{},
		context.DeadlineExceeded,
	)

	if code != 10 {
		t.Fatalf("deadline exit code = %d, want 10; stdout=%s", code, stdout.String())
	}
	var payload map[string]any
	if err := json.Unmarshal(stdout.Bytes(), &payload); err != nil {
		t.Fatalf("deadline stdout is not JSON: %v", err)
	}
	if payload["status"] != "blocked" || payload["summary"] != "runtime command timed out" {
		t.Fatalf("deadline envelope = %#v", payload)
	}
	data, _ := payload["data"].(map[string]any)
	if data["operation"] != "run.launch" {
		t.Fatalf("deadline operation = %#v, want run.launch", data["operation"])
	}
}
