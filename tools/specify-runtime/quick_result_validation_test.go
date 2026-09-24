package main

import (
	"bytes"
	"encoding/json"
	"os"
	"path/filepath"
	"reflect"
	"strings"
	"testing"
)

func TestQuickResultRejectsLossyChecks(t *testing.T) {
	good := `{"command":"unit checks","status":"passed"}`
	for _, tc := range []struct{ name, check string }{
		{"failed without command", `{"status":"failed","output":"integration failed"}`},
		{"blank command", `{"command":" ","status":"failed"}`},
		{"null command", `{"command":null,"status":"failed"}`},
		{"numeric command", `{"command":123,"status":"passed"}`},
		{"missing status", `{"command":"integration"}`},
		{"null status", `{"command":"integration","status":null}`},
		{"non-string status", `{"command":"integration","status":true}`},
		{"scalar row", `"integration failed"`},
		{"null row", `null`},
		{"array row", `[]`},
		{"command alias conflict", `{"command":"unit","cmd":"integration","status":"passed"}`},
		{"status alias conflict", `{"command":"unit","status":"passed","result":"failed"}`},
		{"invalid hidden alias", `{"command":"unit","cmd":null,"status":"passed"}`},
	} {
		t.Run(tc.name, func(t *testing.T) {
			raw := []byte(`{"task_id":"Q1","status":"success","validation_results":[` + good + `,` + tc.check + `]}`)
			before := append([]byte(nil), raw...)
			if _, err := normalizeSubmittedTaskResult("quick", raw); err == nil {
				t.Fatal("accepted a check that could be dropped or coerced")
			}
			if !bytes.Equal(before, raw) {
				t.Fatal("input bytes changed")
			}
		})
	}
}

func TestQuickResultValidationListAliases(t *testing.T) {
	for _, raw := range []string{
		`{"validation_results":"passed"}`,
		`{"validation_results":{}}`,
		`{"validation_results":[],"validationResults":[{"command":"integration","status":"failed"}]}`,
		`{"validation_results":[{"command":"unit","status":"passed"}],"validationResults":null}`,
		`{"validation_results":[{"command":"unit","status":"passed"}],"validationResults":[null]}`,
		`{"validation_results":[{"command":"unit","status":"passed"}],"validationResults":[{"command":"unit","status":"failed"}]}`,
		`null`, `[]`, `{`,
	} {
		t.Run(raw, func(t *testing.T) {
			if _, err := normalizeSubmittedTaskResult("quick", []byte(raw)); err == nil {
				t.Fatal("invalid alias or list accepted")
			}
		})
	}
}

func TestQuickResultRoundTripPreservesCheckVerdicts(t *testing.T) {
	for _, status := range []string{"passed", "pass", "success", "failed", "fail", "error", "skipped", "skip", "unknown"} {
		t.Run(status, func(t *testing.T) {
			raw := []byte(`{"task_id":"Q1","status":"success","validationResults":[{"cmd":" unit ","result":"` + status + `"}],"blockers":[]}`)
			first, err := normalizeSubmittedTaskResult(" QUICK ", raw)
			if err != nil {
				t.Fatal(err)
			}
			persisted, err := json.Marshal(first)
			if err != nil {
				t.Fatal(err)
			}
			second, err := normalizeSubmittedTaskResult("quick", persisted)
			if err != nil {
				t.Fatal(err)
			}
			if !reflect.DeepEqual(first, second) {
				t.Fatal("normalization changed after persistence")
			}
			checks := second["validation_results"].([]map[string]string)
			want := resultValidationStatusAliases[status]
			if want == "" {
				want = "failed"
			}
			if len(checks) != 1 || checks[0]["status"] != want {
				t.Fatal(checks)
			}
			if got := validateQuickLeaderDirectResult(second); (got == nil) != (want == "passed") {
				t.Fatalf("direct gate for %s: %v", status, got)
			}
		})
	}
}

func TestQuickResultLegacyAndEquivalentAliasesRemainCompatible(t *testing.T) {
	for _, raw := range []string{
		`{"status":"success"}`,
		`{"status":"success","validation_results":null}`,
		`{"status":"success","validation_results":[],"validationResults":null}`,
		`{"status":"success","validation_results":[{"command":"unit","cmd":" unit ","status":"pass","result":"passed"}],"validationResults":[{"cmd":"unit","result":"success"}]}`,
	} {
		t.Run(raw, func(t *testing.T) {
			got, err := normalizeSubmittedTaskResult("quick", []byte(raw))
			if err != nil {
				t.Fatal(err)
			}
			old, err := normalizeWorkerTaskResult([]byte(raw))
			if err != nil {
				t.Fatal(err)
			}
			if !reflect.DeepEqual(got, old) {
				t.Fatal("valid legacy output changed")
			}
			if len(got["validation_results"].([]map[string]string)) == 0 && validateQuickLeaderDirectResult(got) == nil {
				t.Fatal("empty checks passed direct gate")
			}
		})
	}
}

func TestQuickResultGuardDoesNotChangeOtherChannels(t *testing.T) {
	raw := []byte(`{"status":"success","validation_results":[{"command":"unit","status":"passed"},{"status":"failed"}]}`)
	for _, channel := range []string{"review", "plan", "tasks", "implement", "prd-scan", "debug", ""} {
		t.Run(channel, func(t *testing.T) {
			got, err := normalizeSubmittedTaskResult(channel, raw)
			if err != nil {
				t.Fatal(err)
			}
			want, err := normalizeWorkerTaskResult(raw)
			if err != nil {
				t.Fatal(err)
			}
			if !reflect.DeepEqual(got, want) {
				t.Fatal("other channel changed")
			}
		})
	}
}

func TestQuickResultReadRejectsInvalidPreferredLane(t *testing.T) {
	workspace := t.TempDir()
	dir := filepath.Join(workspace, "worker-results")
	if err := os.Mkdir(dir, 0o700); err != nil {
		t.Fatal(err)
	}
	good := []byte(`{"task_id":"Q1","status":"success","validation_results":[{"command":"unit","status":"passed"}]}`)
	if err := os.WriteFile(filepath.Join(dir, "Q1-older.json"), good, 0o600); err != nil {
		t.Fatal(err)
	}
	for _, bad := range []string{
		`{"task_id":"Q1","status":"success","validation_results":[{"command":"unit","status":"passed"},{"status":"failed"}]}`,
		`{"task_id":"Q1","status":"success","ui_verification":{"unsupported":true}}`,
		`{`,
	} {
		if err := os.WriteFile(filepath.Join(dir, "Q1.json"), []byte(bad), 0o600); err != nil {
			t.Fatal(err)
		}
		if _, _, _, err := findQuickWorkerResult(workspace, "Q1"); err == nil {
			t.Fatal("invalid preferred result bypassed through fallback")
		}
	}
	if err := os.WriteFile(filepath.Join(dir, "Q1.json"), good, 0o600); err != nil {
		t.Fatal(err)
	}
	if _, _, lane, err := findQuickWorkerResult(workspace, "Q1"); err != nil || lane != "Q1" {
		t.Fatalf("repaired lane: %s %v", lane, err)
	}
}

func TestQuickResultReadIgnoresUnrelatedLanes(t *testing.T) {
	workspace := t.TempDir()
	dir := filepath.Join(workspace, "worker-results")
	if err := os.Mkdir(dir, 0o700); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(dir, "Q2.json"), []byte(`{`), 0o600); err != nil {
		t.Fatal(err)
	}
	_, _, _, err := findQuickWorkerResult(workspace, "Q1")
	if err == nil || !strings.Contains(err.Error(), "no worker result files") {
		t.Fatalf("unrelated lane entered validation: %v", err)
	}
}

func TestQuickResultValidationErrorsDoNotEchoOutput(t *testing.T) {
	_, err := normalizeSubmittedTaskResult("quick", []byte(`{"validation_results":[{"status":"failed","output":"PRIVATE_TOOL_OUTPUT"}]}`))
	if err == nil || strings.Contains(err.Error(), "PRIVATE_TOOL_OUTPUT") {
		t.Fatal(err)
	}
}
