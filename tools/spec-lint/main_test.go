package main

import (
	"bytes"
	"encoding/json"
	"errors"
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"
	"testing"
)

func TestCLIRejectsUnknownTier(t *testing.T) {
	binaryPath := buildSpecLintForTest(t)
	stdout, stderr, code := runSpecLintForTest(t, binaryPath,
		"-dir", filepath.Join("testdata", "good-spec"),
		"-tier", "standrad",
	)
	if code != 2 {
		t.Fatalf("exit code = %d, stdout=%q stderr=%q; want 2", code, stdout, stderr)
	}
	combined := stdout + stderr
	if !strings.Contains(combined, "invalid tier") || !strings.Contains(combined, "light, standard, deep") {
		t.Fatalf("output = %q, want invalid-tier guidance with allowed values", combined)
	}
	if strings.Contains(combined, "0 passed") {
		t.Fatalf("output = %q, unknown tier must not report an empty successful run", combined)
	}
}

func TestValidTierAcceptsOnlySupportedValues(t *testing.T) {
	tests := []struct {
		tier string
		want bool
	}{
		{tier: "light", want: true},
		{tier: "standard", want: true},
		{tier: "deep", want: true},
		{tier: "standrad", want: false},
		{tier: "", want: false},
	}

	for _, tt := range tests {
		t.Run(tt.tier, func(t *testing.T) {
			if got := validTier(tt.tier); got != tt.want {
				t.Fatalf("validTier(%q) = %t, want %t", tt.tier, got, tt.want)
			}
		})
	}
}

func TestValidFormatAcceptsOnlySupportedValues(t *testing.T) {
	tests := []struct {
		format string
		want   bool
	}{
		{format: "text", want: true},
		{format: "json", want: true},
		{format: "yaml", want: false},
		{format: "", want: false},
	}

	for _, tt := range tests {
		t.Run(tt.format, func(t *testing.T) {
			if got := validFormat(tt.format); got != tt.want {
				t.Fatalf("validFormat(%q) = %t, want %t", tt.format, got, tt.want)
			}
		})
	}
}

func TestPrintJSONReportClassifiesResultsAndControlsPassExpansion(t *testing.T) {
	results := []checkResult{
		{name: "passing-check", status: statusPass},
		{name: "failing-check", status: statusFail, message: "failed detail"},
		{name: "warning-check", status: statusWarn, message: "warning detail"},
	}

	for _, showPasses := range []bool{false, true} {
		t.Run(map[bool]string{false: "hidden", true: "shown"}[showPasses], func(t *testing.T) {
			var output bytes.Buffer
			if err := printJSONReport(&output, "deep", results, showPasses); err != nil {
				t.Fatalf("printJSONReport: %v", err)
			}
			payload := decodeJSONObjectForTest(t, output.String())
			if payload["status"] != "failed" || payload["tier"] != "deep" {
				t.Fatalf("payload=%#v, want failed deep report", payload)
			}
			requireSummaryForTest(t, payload, 1, 1, 1)
			requireJSONArrayLengthForTest(t, payload, "failures", 1)
			requireJSONArrayLengthForTest(t, payload, "warnings", 1)
			passes, present := payload["passes"]
			if present != showPasses {
				t.Fatalf("passes present=%t, want %t; payload=%#v", present, showPasses, payload)
			}
			if showPasses {
				items, ok := passes.([]any)
				if !ok || len(items) != 1 || items[0] != "passing-check" {
					t.Fatalf("passes=%#v, want passing check name", passes)
				}
			}
		})
	}
}

func TestPrintJSONReportReturnsEncodingError(t *testing.T) {
	err := printJSONReport(rejectingWriter{}, "standard", nil, false)
	if err == nil || !strings.Contains(err.Error(), "write rejected") {
		t.Fatalf("err=%v, want writer error", err)
	}
}

type rejectingWriter struct{}

func (rejectingWriter) Write([]byte) (int, error) {
	return 0, errors.New("write rejected")
}

func TestCLIJSONOutputContract(t *testing.T) {
	binaryPath := buildSpecLintForTest(t)

	t.Run("compact success omits passes by default", func(t *testing.T) {
		stdout, stderr, code := runSpecLintForTest(t, binaryPath,
			"-dir", filepath.Join("testdata", "good-spec"),
			"-tier", "standard",
			"-format", "json",
		)
		if code != 0 || stderr != "" {
			t.Fatalf("code=%d stderr=%q stdout=%q, want clean success", code, stderr, stdout)
		}
		if strings.Contains(strings.TrimSpace(stdout), "\n") {
			t.Fatalf("stdout=%q, want compact single-line JSON", stdout)
		}
		payload := decodeJSONObjectForTest(t, stdout)
		requireExactJSONKeys(t, payload, "status", "tier", "summary", "failures", "warnings")
		if payload["status"] != "ok" || payload["tier"] != "standard" {
			t.Fatalf("payload=%#v, want successful standard result", payload)
		}
		requireSummaryForTest(t, payload, 16, 0, 0)
		requireJSONArrayLengthForTest(t, payload, "failures", 0)
		requireJSONArrayLengthForTest(t, payload, "warnings", 0)
	})

	t.Run("show passes expands names only", func(t *testing.T) {
		stdout, stderr, code := runSpecLintForTest(t, binaryPath,
			"-dir", filepath.Join("testdata", "good-spec"),
			"-format", "json",
			"-show-passes",
		)
		if code != 0 || stderr != "" {
			t.Fatalf("code=%d stderr=%q stdout=%q, want clean success", code, stderr, stdout)
		}
		payload := decodeJSONObjectForTest(t, stdout)
		requireExactJSONKeys(t, payload, "status", "tier", "summary", "failures", "warnings", "passes")
		passes := requireJSONArrayLengthForTest(t, payload, "passes", 16)
		for _, pass := range passes {
			if _, ok := pass.(string); !ok {
				t.Fatalf("passes=%#v, want compact check-name strings", passes)
			}
		}
	})

	t.Run("failed checks keep exit one and structured diagnostics", func(t *testing.T) {
		stdout, stderr, code := runSpecLintForTest(t, binaryPath,
			"-dir", filepath.Join("testdata", "bad-spec"),
			"-tier", "standard",
			"-format", "json",
		)
		if code != 1 || stderr != "" {
			t.Fatalf("code=%d stderr=%q stdout=%q, want structured lint failure", code, stderr, stdout)
		}
		payload := decodeJSONObjectForTest(t, stdout)
		requireExactJSONKeys(t, payload, "status", "tier", "summary", "failures", "warnings")
		if payload["status"] != "failed" {
			t.Fatalf("status=%#v, want failed", payload["status"])
		}
		requireSummaryForTest(t, payload, 0, 9, 7)
		failures := requireJSONArrayLengthForTest(t, payload, "failures", 9)
		warnings := requireJSONArrayLengthForTest(t, payload, "warnings", 7)
		for _, item := range append(failures, warnings...) {
			diagnostic, ok := item.(map[string]any)
			if !ok {
				t.Fatalf("diagnostic=%#v, want object", item)
			}
			requireExactJSONKeys(t, diagnostic, "name", "message")
		}
	})
}

func TestCLIRejectsUnknownFormat(t *testing.T) {
	binaryPath := buildSpecLintForTest(t)
	stdout, stderr, code := runSpecLintForTest(t, binaryPath,
		"-dir", filepath.Join("testdata", "good-spec"),
		"-format", "yaml",
	)
	if code != 2 {
		t.Fatalf("code=%d stderr=%q stdout=%q, want usage exit 2", code, stderr, stdout)
	}
	if stdout != "" || !strings.Contains(stderr, "invalid format") || !strings.Contains(stderr, "text, json") {
		t.Fatalf("stdout=%q stderr=%q, want strict format guidance", stdout, stderr)
	}
}

func TestCLIDefaultTextOutputRemainsHumanReadable(t *testing.T) {
	binaryPath := buildSpecLintForTest(t)
	stdout, stderr, code := runSpecLintForTest(t, binaryPath,
		"-dir", filepath.Join("testdata", "good-spec"),
		"-tier", "standard",
	)
	if code != 0 || stderr != "" {
		t.Fatalf("code=%d stderr=%q stdout=%q, want clean text success", code, stderr, stdout)
	}
	for _, want := range []string{"spec-lint dev", "[PASS] required-artifacts", "16 passed, 0 failed, 0 warnings"} {
		if !strings.Contains(stdout, want) {
			t.Fatalf("stdout=%q, want %q", stdout, want)
		}
	}
}

func buildSpecLintForTest(t *testing.T) string {
	t.Helper()
	binaryName := "spec-lint"
	if runtime.GOOS == "windows" {
		binaryName += ".exe"
	}
	binaryPath := filepath.Join(t.TempDir(), binaryName)
	build := exec.Command("go", "build", "-o", binaryPath, ".")
	if output, err := build.CombinedOutput(); err != nil {
		t.Fatalf("build spec-lint: %v\n%s", err, output)
	}
	return binaryPath
}

func runSpecLintForTest(t *testing.T, binaryPath string, args ...string) (stdout string, stderr string, code int) {
	t.Helper()
	var stdoutBuffer, stderrBuffer bytes.Buffer
	cmd := exec.Command(binaryPath, args...)
	cmd.Stdout = &stdoutBuffer
	cmd.Stderr = &stderrBuffer
	err := cmd.Run()
	if err == nil {
		return stdoutBuffer.String(), stderrBuffer.String(), 0
	}
	exitErr, ok := err.(*exec.ExitError)
	if !ok {
		t.Fatalf("run spec-lint: %v", err)
	}
	return stdoutBuffer.String(), stderrBuffer.String(), exitErr.ExitCode()
}

func decodeJSONObjectForTest(t *testing.T, output string) map[string]any {
	t.Helper()
	var payload map[string]any
	if err := json.Unmarshal([]byte(output), &payload); err != nil {
		t.Fatalf("decode JSON output %q: %v", output, err)
	}
	return payload
}

func requireExactJSONKeys(t *testing.T, object map[string]any, keys ...string) {
	t.Helper()
	if len(object) != len(keys) {
		t.Fatalf("keys=%v, want exactly %v", object, keys)
	}
	for _, key := range keys {
		if _, ok := object[key]; !ok {
			t.Fatalf("object=%#v, missing key %q", object, key)
		}
	}
}

func requireSummaryForTest(t *testing.T, payload map[string]any, passed, failed, warnings int) {
	t.Helper()
	summary, ok := payload["summary"].(map[string]any)
	if !ok {
		t.Fatalf("summary=%#v, want object", payload["summary"])
	}
	requireExactJSONKeys(t, summary, "passed", "failed", "warnings")
	if summary["passed"] != float64(passed) || summary["failed"] != float64(failed) || summary["warnings"] != float64(warnings) {
		t.Fatalf("summary=%#v, want passed=%d failed=%d warnings=%d", summary, passed, failed, warnings)
	}
}

func requireJSONArrayLengthForTest(t *testing.T, payload map[string]any, key string, length int) []any {
	t.Helper()
	items, ok := payload[key].([]any)
	if !ok {
		t.Fatalf("%s=%#v, want array", key, payload[key])
	}
	if len(items) != length {
		t.Fatalf("%s length=%d, want %d; items=%#v", key, len(items), length, items)
	}
	return items
}
