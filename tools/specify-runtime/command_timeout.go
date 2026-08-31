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

func runWithWatchdog(
	args []string,
	stdout, stderr io.Writer,
	cliVersion string,
	timeout time.Duration,
	runner contextualRuntimeCommandRunner,
) int {
	type commandResult struct {
		code   int
		stdout []byte
		stderr []byte
	}
	ctx, cancel := context.WithTimeout(context.Background(), timeout)
	defer cancel()
	resultChannel := make(chan commandResult, 1)
	go func() {
		var commandStdout, commandStderr bytes.Buffer
		code := runner(ctx, args, &commandStdout, &commandStderr, cliVersion)
		resultChannel <- commandResult{
			code:   code,
			stdout: append([]byte(nil), commandStdout.Bytes()...),
			stderr: append([]byte(nil), commandStderr.Bytes()...),
		}
	}()

	select {
	case result := <-resultChannel:
		_, _ = stdout.Write(result.stdout)
		_, _ = stderr.Write(result.stderr)
		return result.code
	case <-ctx.Done():
	}

	cleanupTimer := time.NewTimer(runtimeCleanupGrace)
	defer cleanupTimer.Stop()
	select {
	case <-resultChannel:
	case <-cleanupTimer.C:
	}
	env := NewEnvelope("blocked", "runtime command timed out")
	env.Data["operation"] = runtimeOperation(args)
	env.Data["timeout_seconds"] = timeout.Seconds()
	env.Data["timeout_env"] = runtimeTimeoutEnv
	env.Blockers = append(
		env.Blockers,
		fmt.Sprintf("operation exceeded its %s execution budget; child processes were cancelled and cleanup was bounded", timeout),
	)
	return writeEnvelope(stdout, env)
}
