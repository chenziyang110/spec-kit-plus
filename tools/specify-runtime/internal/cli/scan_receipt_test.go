package cli

import (
	"bytes"
	"crypto/sha256"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"testing"

	rt "github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/runtime"
	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/validation"
)

func TestValidateScanCommandWritesV2ScanReceipt(t *testing.T) {
	root := writeMinimalCLIScanPackage(t)
	paths := markCLIFixtureAsV2Workbench(t, root)
	chdirForScanReceiptTest(t, root)

	var stdout, stderr bytes.Buffer
	code := Run([]string{"validate-scan", "--format", "json"}, &stdout, &stderr, "test")
	if code != 0 {
		t.Fatalf("validate-scan code=%d stderr=%s stdout=%s", code, stderr.String(), stdout.String())
	}
	var gate map[string]any
	if err := json.Unmarshal(stdout.Bytes(), &gate); err != nil {
		t.Fatalf("decode validate-scan output: %v; output=%s", err, stdout.String())
	}
	if gate["completion_allowed"] != true || gate["bypass_allowed"] != false || gate["error_classification"] != "none" {
		t.Fatalf("validate-scan completion contract = %#v", gate)
	}

	receiptPath := filepath.Join(paths.RuntimeDir, "scan-receipt.json")
	data, err := os.ReadFile(receiptPath)
	if err != nil {
		t.Fatalf("validate-scan did not write scan-receipt.json: %v", err)
	}
	var receipt map[string]any
	if err := json.Unmarshal(data, &receipt); err != nil {
		t.Fatalf("decode scan-receipt.json: %v", err)
	}
	if receipt["protocol"] != "map_scan_receipt.v2" || receipt["generation_id"] != "GEN-scan-v2" {
		t.Fatalf("scan receipt identity = %#v, want v2 protocol and source generation", receipt)
	}
	if receipt["readiness"] != "scan_ready" {
		t.Fatalf("scan receipt readiness = %#v, want scan_ready", receipt["readiness"])
	}
	for _, key := range []string{"scan_set_digest", "source_digest", "artifact_digest"} {
		value, ok := receipt[key].(string)
		if !ok || strings.TrimSpace(value) == "" {
			t.Fatalf("scan receipt %s = %#v, want non-empty digest", key, receipt[key])
		}
	}
}

func TestValidateScanCommandRejectsNonV2ToV2SwitchDuringValidation(t *testing.T) {
	for _, initialState := range []string{"legacy", "missing"} {
		t.Run(initialState, func(t *testing.T) {
			root := writeMinimalCLIScanPackage(t)
			paths, err := rt.ResolvePaths(root)
			if err != nil {
				t.Fatal(err)
			}
			if initialState == "missing" {
				if err := os.Remove(filepath.Join(paths.RuntimeDir, "workbench", "scan-queue.json")); err != nil {
					t.Fatal(err)
				}
			}
			chdirForScanReceiptTest(t, root)

			var stdout, stderr bytes.Buffer
			code := validateScanCommandWithValidator(
				[]string{"--format", "json"},
				&stdout,
				&stderr,
				paths,
				func(validatePaths rt.Paths) validation.GatePayload {
					// Simulate another workbench operation installing v2 after
					// validate-scan captured its initial snapshot.
					markCLIFixtureAsV2Workbench(t, root)
					return validation.ValidateScan(validatePaths)
				},
			)
			if code == 0 {
				t.Fatalf("validate-scan signed a v2 snapshot introduced during validation; stdout=%s stderr=%s", stdout.String(), stderr.String())
			}
			var payload map[string]any
			if err := json.Unmarshal(stdout.Bytes(), &payload); err != nil {
				t.Fatalf("decode blocked validate-scan payload: %v; output=%s", err, stdout.String())
			}
			if payload["status"] != "blocked" || payload["readiness"] != rt.BlockedReadiness {
				t.Fatalf("validate-scan payload = %#v, want blocked readiness", payload)
			}
			if errorsText := strings.Join(jsonStringValues(payload["errors"]), "\n"); !strings.Contains(errorsText, "changed while validate-scan was running") {
				t.Fatalf("validate-scan errors = %#v, want snapshot-change evidence", payload["errors"])
			}
			if _, err := os.Stat(filepath.Join(paths.RuntimeDir, "scan-receipt.json")); !errors.Is(err, os.ErrNotExist) {
				t.Fatalf("validate-scan wrote a receipt for an unvalidated v2 snapshot: %v", err)
			}
		})
	}
}

func TestBuildFromScanRejectsStaleV2ReceiptAfterCanonicalArtifactChange(t *testing.T) {
	root := writeMinimalCLIScanPackage(t)
	paths := markCLIFixtureAsV2Workbench(t, root)
	chdirForScanReceiptTest(t, root)

	var validateStdout, validateStderr bytes.Buffer
	if code := Run([]string{"validate-scan", "--format", "json"}, &validateStdout, &validateStderr, "test"); code != 0 {
		t.Fatalf("validate-scan code=%d stderr=%s stdout=%s", code, validateStderr.String(), validateStdout.String())
	}

	writeTestJSON(t, filepath.Join(paths.RuntimeDir, "provisional", "nodes.json"), map[string]any{
		"nodes": []map[string]any{{
			"id": "N-app", "type": "capability", "title": "App changed after validation", "confidence": "verified",
			"paths": []string{"src/app.go"}, "evidence_ids": []string{"E-001"}, "attrs": map[string]any{"owner": "test"},
		}},
	})

	var stdout, stderr bytes.Buffer
	code := Run([]string{"build-from-scan", "--format", "json"}, &stdout, &stderr, "test")
	if code == 0 {
		t.Fatalf("build-from-scan accepted stale receipt; stdout=%s stderr=%s", stdout.String(), stderr.String())
	}
	var payload map[string]any
	if err := json.Unmarshal(stdout.Bytes(), &payload); err != nil {
		t.Fatalf("decode blocked build payload: %v; output=%s", err, stdout.String())
	}
	if payload["status"] != "blocked" {
		t.Fatalf("build payload = %#v, want blocked", payload)
	}
	joined := strings.Join(jsonStringValues(payload["errors"]), "\n")
	if !strings.Contains(joined, "scan-receipt.json") || (!strings.Contains(joined, "stale") && !strings.Contains(joined, "digest")) {
		t.Fatalf("build errors = %#v, want stale scan receipt digest", payload["errors"])
	}
	if _, err := os.Stat(paths.DatabasePath); !errors.Is(err, os.ErrNotExist) {
		t.Fatalf("stale receipt build created or touched graph store: %v", err)
	}
}

func TestBuildFromScanRejectsStaleV2ReceiptAfterSourceChange(t *testing.T) {
	root := writeMinimalCLIScanPackage(t)
	paths := markCLIFixtureAsV2Workbench(t, root)
	chdirForScanReceiptTest(t, root)

	var validateStdout, validateStderr bytes.Buffer
	if code := Run([]string{"validate-scan", "--format", "json"}, &validateStdout, &validateStderr, "test"); code != 0 {
		t.Fatalf("validate-scan code=%d stderr=%s stdout=%s", code, validateStderr.String(), validateStdout.String())
	}
	if err := os.WriteFile(filepath.Join(root, "src", "app.go"), []byte("package app\n// changed after scan validation\n"), 0o644); err != nil {
		t.Fatal(err)
	}

	var stdout, stderr bytes.Buffer
	code := Run([]string{"build-from-scan", "--format", "json"}, &stdout, &stderr, "test")
	if code == 0 {
		t.Fatalf("build-from-scan accepted stale source receipt; stdout=%s stderr=%s", stdout.String(), stderr.String())
	}
	if !strings.Contains(stdout.String(), "stale") {
		t.Fatalf("blocked build output lacks stale source evidence: %s", stdout.String())
	}
	if _, err := os.Stat(paths.DatabasePath); !errors.Is(err, os.ErrNotExist) {
		t.Fatalf("source-stale receipt build created or touched graph store: %v", err)
	}
}

func markCLIFixtureAsV2Workbench(t *testing.T, root string) rt.Paths {
	t.Helper()
	paths, err := rt.ResolvePaths(root)
	if err != nil {
		t.Fatal(err)
	}
	const generationID = "GEN-scan-v2"
	if err := os.MkdirAll(filepath.Join(paths.RuntimeDir, "tmp"), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.MkdirAll(filepath.Join(root, "src"), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(root, "src", "app.go"), []byte("package app\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	writeTestJSON(t, filepath.Join(paths.RuntimeDir, "tmp", "scan-files.json"), map[string]any{
		"protocol": "map_scan_set.v2", "generation_id": generationID, "files": []string{"src/app.go"},
	})
	writeTestJSON(t, filepath.Join(paths.RuntimeDir, "workbench", "scan-queue.json"), map[string]any{
		"protocol":      "map_scan_workbench.v2",
		"generation_id": generationID,
		"scan_set_path": ".specify/project-cognition/tmp/scan-files.json",
		"packets": []map[string]any{{
			"packet_id": "lane-1", "state": "accepted", "attempt_id": "attempt-lane-1-1",
			"assigned_paths":      []string{"src/app.go"},
			"result_handoff_path": ".specify/project-cognition/workbench/worker-results/lane-1.json",
		}},
	})
	writeCLIV2AcceptanceFixture(t, paths, generationID, "attempt-lane-1-1")
	status := rt.DefaultStatus(paths)
	if err := rt.WriteStatus(paths, status); err != nil {
		t.Fatal(err)
	}
	return paths
}

func writeCLIV2AcceptanceFixture(t *testing.T, paths rt.Paths, generationID string, attemptID string) {
	t.Helper()
	resultPath := filepath.Join(paths.RuntimeDir, "workbench", "worker-results", "lane-1.json")
	data, err := os.ReadFile(resultPath)
	if err != nil {
		t.Fatal(err)
	}
	var canonical map[string]any
	if err := json.Unmarshal(data, &canonical); err != nil {
		t.Fatal(err)
	}
	canonical["protocol"] = "map_scan_result.v2"
	canonical["attempt_id"] = attemptID
	canonical["sequence"] = 1
	writeTestJSON(t, resultPath, canonical)

	submitted := cloneJSONMap(t, canonical)
	submitted["acceptance"] = "partial"
	writeTestJSON(t, filepath.Join(paths.RuntimeDir, "workbench", "pending-results", "lane-1.json"), submitted)
	writeTestJSON(t, filepath.Join(paths.RuntimeDir, "workbench", "accepted-submissions", "lane-1.json"), submitted)
	writeTestJSON(t, filepath.Join(paths.RuntimeDir, "workbench", "acceptance-receipts", "lane-1.json"), map[string]any{
		"protocol":                "map_scan_acceptance.v1",
		"workbench_generation_id": generationID,
		"packet_id":               "lane-1",
		"attempt_id":              attemptID,
		"sequence":                1,
		"source_result_path":      ".specify/project-cognition/workbench/pending-results/lane-1.json",
		"submission_path":         ".specify/project-cognition/workbench/accepted-submissions/lane-1.json",
		"submission_sha256":       normalizedJSONTestDigest(t, submitted),
		"canonical_result_path":   ".specify/project-cognition/workbench/worker-results/lane-1.json",
		"canonical_result_sha256": normalizedJSONTestDigest(t, canonical),
		"accepted_path_count":     1,
	})
}

func cloneJSONMap(t *testing.T, value map[string]any) map[string]any {
	t.Helper()
	data, err := json.Marshal(value)
	if err != nil {
		t.Fatal(err)
	}
	var clone map[string]any
	if err := json.Unmarshal(data, &clone); err != nil {
		t.Fatal(err)
	}
	return clone
}

func normalizedJSONTestDigest(t *testing.T, value any) string {
	t.Helper()
	data, err := json.Marshal(value)
	if err != nil {
		t.Fatal(err)
	}
	sum := sha256.Sum256(data)
	return fmt.Sprintf("%x", sum[:])
}

func chdirForScanReceiptTest(t *testing.T, root string) {
	t.Helper()
	old, err := os.Getwd()
	if err != nil {
		t.Fatal(err)
	}
	if err := os.Chdir(root); err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { _ = os.Chdir(old) })
}

func jsonStringValues(value any) []string {
	raw, _ := value.([]any)
	values := make([]string, 0, len(raw))
	for _, item := range raw {
		if text, ok := item.(string); ok {
			values = append(values, text)
		}
	}
	return values
}
