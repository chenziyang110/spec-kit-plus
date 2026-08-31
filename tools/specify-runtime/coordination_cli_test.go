package main

import (
	"bytes"
	"testing"
)

// The CLI fixture is shared by Work Board and execution lifecycle tests.
func initCoordinationCLIRepository(t *testing.T) string {
	t.Helper()
	requireGit(t)
	root := t.TempDir()
	gitRun(t, root, "init")
	return root
}

func invokeCoordinationCLI(t *testing.T, args ...string) (int, map[string]any) {
	t.Helper()
	var stdout, stderr bytes.Buffer
	code := Run(args, &stdout, &stderr, "test")
	if stderr.Len() != 0 {
		t.Fatalf("Run(%v) stderr = %q, want empty", args, stderr.String())
	}
	return code, decodeJSONObject(t, stdout.Bytes())
}
