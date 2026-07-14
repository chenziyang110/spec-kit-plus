package cli

import (
	"bytes"
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestScanPrepareAndAcceptCommands(t *testing.T) {
	root := t.TempDir()
	for _, rel := range []string{".specify/project-cognition/tmp", "src"} {
		if err := os.MkdirAll(filepath.Join(root, filepath.FromSlash(rel)), 0o755); err != nil {
			t.Fatal(err)
		}
	}
	if err := os.WriteFile(filepath.Join(root, "src", "app.go"), []byte("package app\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	writeCLIJSON(t, filepath.Join(root, ".specify", "project-cognition", "tmp", "scan-files.json"), map[string]any{
		"files": []string{"src/app.go"},
	})

	old, err := os.Getwd()
	if err != nil {
		t.Fatal(err)
	}
	if err := os.Chdir(root); err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { _ = os.Chdir(old) })

	var stdout, stderr bytes.Buffer
	code := Run([]string{"scan-prepare", "--packet-size", "1", "--format", "json"}, &stdout, &stderr, "test")
	if code != 0 {
		t.Fatalf("scan-prepare code = %d stderr=%s stdout=%s", code, stderr.String(), stdout.String())
	}
	if got, want := strings.TrimSpace(stdout.String()), `{"status":"prepared","path_count":1,"packet_count":1,"packet_ids":["lane-001"],"scan_set_path":".specify/project-cognition/tmp/scan-files.json","workbench_path":".specify/project-cognition/workbench","next_action":"dispatch_scan_packets"}`; got != want {
		t.Fatalf("scan-prepare stdout = %q, want %q", got, want)
	}

	resultPath := filepath.Join(root, ".specify", "project-cognition", "workbench", "pending-results", "lane-001.json")
	writeCLIJSON(t, resultPath, acceptedCLIWorkerResult("lane-001", "src/app.go"))
	stdout.Reset()
	stderr.Reset()
	code = Run([]string{"scan-accept", "--packet-id", "lane-001", "--format", "json"}, &stdout, &stderr, "test")
	if code != 0 {
		t.Fatalf("scan-accept code = %d stderr=%s stdout=%s", code, stderr.String(), stdout.String())
	}
	if got, want := strings.TrimSpace(stdout.String()), `{"status":"accepted","packet_id":"lane-001","accepted_path_count":1,"pending_packets":0,"worker_result_path":".specify/project-cognition/workbench/worker-results/lane-001.json","next_action":"validate_scan"}`; got != want {
		t.Fatalf("scan-accept stdout = %q, want %q", got, want)
	}

	stdout.Reset()
	stderr.Reset()
	code = Run([]string{"scan-prepare", "--format", "json"}, &stdout, &stderr, "test")
	if code != 1 || !strings.Contains(stdout.String(), `"status":"blocked"`) || !strings.Contains(stdout.String(), "--force") {
		t.Fatalf("guarded scan-prepare code=%d stderr=%s stdout=%s", code, stderr.String(), stdout.String())
	}
	stdout.Reset()
	stderr.Reset()
	code = Run([]string{"scan-prepare", "--force", "--format", "json"}, &stdout, &stderr, "test")
	if code != 0 {
		t.Fatalf("forced scan-prepare code=%d stderr=%s stdout=%s", code, stderr.String(), stdout.String())
	}
}

func acceptedCLIWorkerResult(packetID string, path string) map[string]any {
	evidenceID := "E-" + packetID
	nodeID := "N-" + packetID
	return map[string]any{
		"packet_id":      packetID,
		"family_id":      packetID,
		"assigned_paths": []string{path},
		"paths_read":     []string{path},
		"ledger": map[string]any{
			"todo":     []string{},
			"doing":    []string{},
			"done":     []string{path},
			"blocked":  []string{},
			"overflow": []string{},
		},
		"coverage": []map[string]any{{
			"path":         path,
			"outcome":      "read",
			"evidence_ids": []string{evidenceID},
		}},
		"evidence": []map[string]any{{
			"id":           evidenceID,
			"source_kind":  "source",
			"source_path":  path,
			"span":         "1:1-1:12",
			"extractor":    "scan-worker",
			"content_hash": "hash-" + packetID,
		}},
		"nodes": []map[string]any{{
			"id":           nodeID,
			"type":         "file",
			"title":        filepath.Base(path),
			"confidence":   "high",
			"paths":        []string{path},
			"evidence_ids": []string{evidenceID},
		}},
		"edges":        []map[string]any{},
		"observations": []map[string]any{},
		"claims":       []map[string]any{},
		"confidence":   "high",
		"acceptance":   "pass",
	}
}

func writeCLIJSON(t *testing.T, path string, value any) {
	t.Helper()
	data, err := json.Marshal(value)
	if err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(path, append(data, '\n'), 0o644); err != nil {
		t.Fatal(err)
	}
}
