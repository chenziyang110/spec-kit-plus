package main

import (
	"bytes"
	"context"
	"fmt"
	"io"
	"math"
	"os"
	"strconv"
	"strings"
	"time"
)

const (
	runtimeTimeoutEnv            = "SPECIFY_RUNTIME_TIMEOUT_SECONDS"
	defaultRuntimeQueryTimeout   = 30 * time.Second
	defaultRuntimeCommandTimeout = 5 * time.Minute
	maxRuntimeCommandTimeout     = 24 * time.Hour
	runtimeCleanupGrace          = 4 * time.Second
)

type contextualRuntimeCommandRunner func(context.Context, []string, io.Writer, io.Writer, string) int

func runtimeCommandTimeout(args []string) (time.Duration, error) {
	if raw := strings.TrimSpace(os.Getenv(runtimeTimeoutEnv)); raw != "" {
		seconds, err := strconv.ParseFloat(raw, 64)
		if err != nil || math.IsNaN(seconds) || math.IsInf(seconds, 0) || seconds <= 0 {
			return 0, fmt.Errorf("%s must be a positive number of seconds", runtimeTimeoutEnv)
		}
		timeout := time.Duration(seconds * float64(time.Second))
		if timeout <= 0 || timeout > maxRuntimeCommandTimeout {
			return 0, fmt.Errorf("%s must not exceed %s", runtimeTimeoutEnv, maxRuntimeCommandTimeout)
		}
		return timeout, nil
	}
	if isShortRuntimeQuery(args) {
		return defaultRuntimeQueryTimeout, nil
	}
	return defaultRuntimeCommandTimeout, nil
}

func isShortRuntimeQuery(args []string) bool {
	if len(args) == 0 {
		return true
	}
	topLevel := strings.ToLower(strings.TrimSpace(args[0]))
	if topLevel == "version" || topLevel == "help" || topLevel == "--help" || topLevel == "-h" || topLevel == "api" {
		return true
	}
	if len(args) < 2 {
		return false
	}
	if topLevel == "quick" && args[1] == "context-shadow" {
		return true
	}
	switch strings.ToLower(strings.TrimSpace(args[1])) {
	case "catalog", "checkpoint-show", "handshake", "item-status", "list", "registry", "resume", "schema", "show", "show-many", "status":
		return true
	default:
		return false
	}
}

func runtimeOperation(args []string) string {
	if len(args) == 0 {
		return "command"
	}
	operation := strings.TrimSpace(args[0])
	if len(args) > 1 && !strings.HasPrefix(args[1], "-") {
		operation += "." + strings.TrimSpace(args[1])
	}
	return operation
}

// Result buffers are private to the runner until it returns. The buffered
// channel also lets a late runner finish without blocking after cleanup expires.
type watchdogCommandResult struct {
	code   int
	stdout []byte
	stderr []byte
}

func watchdogContextExpired(ctx context.Context) bool {
	if ctx.Err() != nil {
		return true
	}
	// Timer delivery may lag behind the deadline while the scheduler is busy.
	deadline, bounded := ctx.Deadline()
	return bounded && !time.Now().Before(deadline)
}

func writeWatchdogOutput(writer io.Writer, data []byte) error {
	if len(data) == 0 {
		return nil
	}
	n, err := writer.Write(data)
	if err != nil {
		return err
	}
	if n != len(data) {
		return io.ErrShortWrite
	}
	return nil
}

// The boolean requests a timeout envelope only while command stdout is still
// untouched. Once stdout delivery starts, failures return 1 without appending
// a second JSON document, retrying a partial write, or rerunning the command.
func deliverWatchdogResult(ctx context.Context, stdout, stderr io.Writer, result watchdogCommandResult) (int, bool) {
	if watchdogContextExpired(ctx) {
		return 10, true
	}
	// Preserve diagnostics before publishing a successful machine-readable result.
	if err := writeWatchdogOutput(stderr, result.stderr); err != nil {
		return 1, false
	}
	if watchdogContextExpired(ctx) {
		return 10, true
	}
	if err := writeWatchdogOutput(stdout, result.stdout); err != nil {
		return 1, false
	}
	if watchdogContextExpired(ctx) {
		return 1, false
	}
	return result.code, false
}

func runWithWatchdog(
	args []string,
	stdout, stderr io.Writer,
	cliVersion string,
	timeout time.Duration,
	runner contextualRuntimeCommandRunner,
) int {
	if stdout == nil || stderr == nil || runner == nil || timeout <= 0 || timeout > maxRuntimeCommandTimeout {
		return 1
	}
	ctx, cancel := context.WithTimeout(context.Background(), timeout)
	defer cancel()
	resultChannel := make(chan watchdogCommandResult, 1)
	go func() {
		var commandStdout, commandStderr bytes.Buffer
		code := runner(ctx, args, &commandStdout, &commandStderr, cliVersion)
		resultChannel <- watchdogCommandResult{
			code:   code,
			stdout: append([]byte(nil), commandStdout.Bytes()...),
			stderr: append([]byte(nil), commandStderr.Bytes()...),
		}
	}()

	commandReturned := false
	select {
	case result := <-resultChannel:
		commandReturned = true
		if code, expired := deliverWatchdogResult(ctx, stdout, stderr, result); !expired {
			return code
		}
	case <-ctx.Done():
	}
	cancel()

	// Receiving a late result confirms only that the command function returned,
	// not that its descendants stopped or its earlier side effects were undone.
	if !commandReturned {
		cleanupTimer := time.NewTimer(runtimeCleanupGrace)
		defer cleanupTimer.Stop()
		select {
		case <-resultChannel:
			commandReturned = true
		case <-cleanupTimer.C:
		}
	}
	env := NewEnvelope("blocked", "runtime command timed out")
	env.Data["operation"] = runtimeOperation(args)
	env.Data["timeout_seconds"] = timeout.Seconds()
	env.Data["timeout_env"] = runtimeTimeoutEnv
	env.Data["error_code"] = "runtime-command-timeout"
	env.Data["cancellation_requested"] = true
	env.Data["command_returned"] = commandReturned
	env.Data["cleanup_grace_seconds"] = runtimeCleanupGrace.Seconds()
	env.Data["command_stdout_discarded"] = true
	env.Data["side_effects_unknown"] = true
	env.Data["recovery"] = "Inspect current runtime-owned state before any retry; cancellation does not roll back completed writes or establish descendant-process cleanup."
	env.Blockers = append(env.Blockers,
		fmt.Sprintf("operation exceeded its %s execution budget; cancellation requested, command_returned=%t after bounded cleanup", timeout, commandReturned),
	)
	var encoded bytes.Buffer
	if code := writeEnvelope(&encoded, env); code != 10 {
		return 1
	}
	if err := writeWatchdogOutput(stdout, encoded.Bytes()); err != nil {
		return 1
	}
	return 10
}
