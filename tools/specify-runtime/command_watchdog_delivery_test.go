package main

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"io"
	"os"
	"path/filepath"
	"strings"
	"sync/atomic"
	"testing"
	"time"
)

type watchdogDeliveryWriter func([]byte) (int, error)

func (write watchdogDeliveryWriter) Write(data []byte) (int, error) { return write(data) }

func watchdogFixtureRunner(code int, output, diagnostic string) contextualRuntimeCommandRunner {
	return func(_ context.Context, _ []string, stdout, stderr io.Writer, _ string) int {
		_, _ = io.WriteString(stdout, output)
		_, _ = io.WriteString(stderr, diagnostic)
		return code
	}
}

func watchdogDecode(t *testing.T, data []byte) Envelope {
	t.Helper()
	var env Envelope
	if err := json.Unmarshal(data, &env); err != nil {
		t.Fatalf("expected one JSON envelope: %v; output=%q", err, data)
	}
	return env
}

func TestRuntimeWatchdogRejectsStdoutDeliveryFailure(t *testing.T) {
	for _, kind := range []string{"closed", "short", "partial-error", "full-with-error", "negative", "oversized"} {
		t.Run(kind, func(t *testing.T) {
			calls := 0
			writer := watchdogDeliveryWriter(func(data []byte) (int, error) {
				calls++
				switch kind {
				case "closed":
					return 0, io.ErrClosedPipe
				case "short":
					return len(data) - 1, nil
				case "partial-error":
					return 1, io.ErrShortWrite
				case "full-with-error":
					return len(data), errors.New("delivery unconfirmed")
				case "negative":
					return -1, nil
				default:
					return len(data) + 1, nil
				}
			})
			code := runWithWatchdog([]string{"api", "handshake"}, writer, io.Discard,
				"test", time.Second, watchdogFixtureRunner(0, "success\n", ""))
			if code != 1 || calls != 1 {
				t.Fatalf("output failure was ignored or retried: code=%d writes=%d", code, calls)
			}
		})
	}
}

func TestRuntimeWatchdogStderrFailureDoesNotPublishSuccess(t *testing.T) {
	for _, short := range []bool{false, true} {
		var stdout bytes.Buffer
		writer := watchdogDeliveryWriter(func(data []byte) (int, error) {
			if short {
				return len(data) - 1, nil
			}
			return 0, io.ErrClosedPipe
		})
		code := runWithWatchdog([]string{"quick", "status"}, &stdout, writer, "test", time.Second,
			watchdogFixtureRunner(0, `{"status":"ok"}`, "important diagnostic"))
		if code != 1 || stdout.Len() != 0 {
			t.Fatalf("success published after lost stderr: code=%d output=%q", code, stdout.String())
		}
	}
}

func TestRuntimeWatchdogDoesNotTouchEmptyStreams(t *testing.T) {
	for _, useStdout := range []bool{false, true} {
		calls := 0
		unused := watchdogDeliveryWriter(func([]byte) (int, error) {
			calls++
			return 0, io.ErrClosedPipe
		})
		var actual bytes.Buffer
		var stdout, stderr io.Writer = unused, &actual
		output, diagnostic := "", "diagnostic"
		if useStdout {
			stdout, stderr, output, diagnostic = &actual, unused, "output", ""
		}
		code := runWithWatchdog([]string{"version"}, stdout, stderr, "test", time.Second,
			watchdogFixtureRunner(0, output, diagnostic))
		if code != 0 || calls != 0 || actual.String() != output+diagnostic {
			t.Fatal("empty stream was unnecessarily written", code, calls)
		}
	}
}

func TestRuntimeWatchdogPreservesCompletedExitCodesAndBytes(t *testing.T) {
	for _, want := range []int{0, 1, 2, 10} {
		var stdout, stderr bytes.Buffer
		code := runWithWatchdog([]string{"test-command"}, &stdout, &stderr, "test", time.Second,
			watchdogFixtureRunner(want, "原始输出\r\n", "diagnostic\x00\n"))
		if code != want || stdout.String() != "原始输出\r\n" || stderr.String() != "diagnostic\x00\n" {
			t.Fatalf("completed command changed: got %d want %d", code, want)
		}
	}
}

func TestRuntimeWatchdogTimeoutDiscardsLateSuccess(t *testing.T) {
	var stdout, stderr bytes.Buffer
	runner := func(ctx context.Context, _ []string, out, errOut io.Writer, _ string) int {
		_, _ = io.WriteString(out, "DO_NOT_PUBLISH_PARTIAL_SUCCESS")
		<-ctx.Done()
		_, _ = io.WriteString(errOut, "DO_NOT_PUBLISH_LATE_DIAGNOSTIC")
		return 0
	}
	code := runWithWatchdog([]string{"quick", "status"}, &stdout, &stderr, "test", 5*time.Millisecond, runner)
	env := watchdogDecode(t, stdout.Bytes())
	if code != 10 || env.Status != "blocked" || env.Data["operation"] != "quick.status" ||
		env.Data["cancellation_requested"] != true || env.Data["command_returned"] != true ||
		env.Data["side_effects_unknown"] != true || len(env.NextArgv) != 0 ||
		bytes.Contains(stdout.Bytes(), []byte("DO_NOT_PUBLISH")) || stderr.Len() != 0 {
		t.Fatal("timeout returned success, partial output or unsupported cleanup claim", code, env)
	}
}

func TestRuntimeWatchdogTimeoutShortWriteFails(t *testing.T) {
	calls := 0
	writer := watchdogDeliveryWriter(func(data []byte) (int, error) { calls++; return len(data) - 1, nil })
	runner := func(ctx context.Context, _ []string, _, _ io.Writer, _ string) int { <-ctx.Done(); return 0 }
	code := runWithWatchdog([]string{"quick", "status"}, writer, io.Discard, "test", time.Millisecond, runner)
	if code != 1 || calls != 1 {
		t.Fatal("truncated timeout envelope did not fail delivery", code, calls)
	}
}

func TestRuntimeWatchdogUsesRealClosedPipeError(t *testing.T) {
	reader, writer, err := os.Pipe()
	if err != nil {
		t.Fatal(err)
	}
	defer writer.Close()
	if err := reader.Close(); err != nil {
		t.Fatal(err)
	}
	code := runWithWatchdog([]string{"version"}, writer, io.Discard, "test", time.Second,
		watchdogFixtureRunner(0, "runtime-version\n", ""))
	if code != 1 {
		t.Fatalf("real pipe delivery failure returned %d", code)
	}
}

func TestRuntimeWatchdogDeadlineDuringDiagnosticDropsSuccess(t *testing.T) {
	var childContext context.Context
	var stdout bytes.Buffer
	writer := watchdogDeliveryWriter(func(data []byte) (int, error) {
		<-childContext.Done()
		return len(data), nil
	})
	runner := func(ctx context.Context, _ []string, out, errOut io.Writer, _ string) int {
		childContext = ctx
		_, _ = io.WriteString(out, "DO_NOT_PUBLISH_EXPIRED_SUCCESS")
		_, _ = io.WriteString(errOut, "diagnostic")
		return 0
	}
	code := runWithWatchdog([]string{"quick", "status"}, &stdout, writer, "test", 50*time.Millisecond, runner)
	env := watchdogDecode(t, stdout.Bytes())
	if code != 10 || env.Status != "blocked" || env.Data["command_returned"] != true ||
		bytes.Contains(stdout.Bytes(), []byte("DO_NOT_PUBLISH")) {
		t.Fatal("expired delivery returned success", code, env)
	}
}

func TestRuntimeWatchdogDeadlineDuringStdoutIsDeliveryFailure(t *testing.T) {
	var childContext context.Context
	calls := 0
	writer := watchdogDeliveryWriter(func(data []byte) (int, error) {
		calls++
		<-childContext.Done()
		return len(data), nil
	})
	runner := func(ctx context.Context, _ []string, out, _ io.Writer, _ string) int {
		childContext = ctx
		_, _ = io.WriteString(out, "success-written-too-late")
		return 0
	}
	code := runWithWatchdog([]string{"version"}, writer, io.Discard, "test", 50*time.Millisecond, runner)
	if code != 1 || calls != 1 {
		t.Fatal("late external write was a success or received appended JSON", code, calls)
	}
}

func TestRuntimeWatchdogCannotClaimUncooperativeCommandStopped(t *testing.T) {
	release := make(chan struct{})
	finished := make(chan struct{})
	started := make(chan struct{})
	var runnerExited atomic.Bool
	marker := filepath.Join(t.TempDir(), "already-written")
	runner := func(_ context.Context, _ []string, _, _ io.Writer, _ string) int {
		defer close(finished)
		_ = os.WriteFile(marker, []byte("existing side effect"), 0600)
		close(started)
		<-release // Deliberately does not cooperate with cancellation.
		runnerExited.Store(true)
		return 0
	}
	defer func() {
		close(release)
		select {
		case <-finished:
		case <-time.After(3 * time.Second):
			t.Error("test runner did not exit after its explicit release")
		}
	}()
	var stdout, stderr bytes.Buffer
	code := runWithWatchdog([]string{"workflow", "transition"}, &stdout, &stderr, "test", 50*time.Millisecond, runner)
	<-started
	env := watchdogDecode(t, stdout.Bytes())
	if code != 10 || runnerExited.Load() || env.Data["command_returned"] != false ||
		env.Data["cancellation_requested"] != true || env.Data["side_effects_unknown"] != true ||
		env.Data["cleanup_grace_seconds"] != runtimeCleanupGrace.Seconds() || len(env.NextArgv) != 0 {
		t.Fatal("unobserved cleanup claimed as complete", code, env)
	}
	if bytes.Contains(stdout.Bytes(), []byte("child processes were cancelled")) {
		t.Fatal("cancellation request was described as a verified cleanup")
	}
	data, err := os.ReadFile(marker)
	if err != nil || string(data) != "existing side effect" {
		t.Fatal("watchdog should not roll back or delete command side effects")
	}
}

func TestRuntimeWatchdogPreservesRuntimeBoundHelp(t *testing.T) {
	// Timeout responses never schedule another command; discovery is unchanged.
	var stdout, stderr bytes.Buffer
	code := runWithWatchdog([]string{"quick", "context-shadow"}, &stdout, &stderr, "test", time.Second,
		func(_ context.Context, _ []string, out, _ io.Writer, _ string) int {
			env := NewEnvelope("ok", "diagnostic help")
			env.ShowArgv = []string{"specify-runtime", "quick", "context-shadow", "--help"}
			return writeEnvelope(out, env)
		})
	env := watchdogDecode(t, stdout.Bytes())
	if code != 0 || len(env.ShowArgv) != 4 || env.ShowArgv[0] == "specify-runtime" ||
		!strings.HasSuffix(env.ShowArgv[3], "--help") || len(env.NextArgv) != 0 {
		t.Fatal("runtime argv binding lost at wrapper", code, env)
	}
}

func TestRuntimeWatchdogCancelledResultCannotWinDelivery(t *testing.T) {
	for _, point := range []string{"before", "stderr", "stdout"} {
		t.Run(point, func(t *testing.T) {
			ctx, cancel := context.WithCancel(context.Background())
			defer cancel()
			stdoutCalls, stderrCalls := 0, 0
			stdout := watchdogDeliveryWriter(func(data []byte) (int, error) {
				stdoutCalls++
				if point == "stdout" {
					cancel()
				}
				return len(data), nil
			})
			stderr := watchdogDeliveryWriter(func(data []byte) (int, error) {
				stderrCalls++
				if point == "stderr" {
					cancel()
				}
				return len(data), nil
			})
			if point == "before" {
				cancel()
			}
			code, expired := deliverWatchdogResult(ctx, stdout, stderr, watchdogCommandResult{
				code: 0, stdout: []byte("success"), stderr: []byte("diagnostic"),
			})
			if point == "stdout" {
				if code != 1 || expired || stdoutCalls != 1 || stderrCalls != 1 {
					t.Fatal("cancelled external write must fail without appending a second result", code, expired)
				}
			} else if code != 10 || !expired || stdoutCalls != 0 || (point == "before" && stderrCalls != 0) {
				t.Fatal("cancelled result won delivery", code, expired, stdoutCalls, stderrCalls)
			}
		})
	}
}

func TestRuntimeWatchdogInvalidInvocationDoesNotRun(t *testing.T) {
	for _, invalid := range []string{"stdout", "stderr", "runner", "zero", "negative", "unbounded"} {
		t.Run(invalid, func(t *testing.T) {
			var ran atomic.Bool
			var out, errOut bytes.Buffer
			var stdout, stderr io.Writer = &out, &errOut
			timeout := time.Second
			var runner contextualRuntimeCommandRunner = func(context.Context, []string, io.Writer, io.Writer, string) int {
				ran.Store(true)
				return 0
			}
			switch invalid {
			case "stdout":
				stdout = nil
			case "stderr":
				stderr = nil
			case "runner":
				runner = nil
			case "zero":
				timeout = 0
			case "negative":
				timeout = -time.Second
			case "unbounded":
				timeout = maxRuntimeCommandTimeout + time.Nanosecond
			}
			code := runWithWatchdog([]string{"version"}, stdout, stderr, "test", timeout, runner)
			if code != 1 || ran.Load() || out.Len() != 0 || errOut.Len() != 0 {
				t.Fatal("invalid wrapper invocation executed or emitted a partial response", code)
			}
		})
	}
}
