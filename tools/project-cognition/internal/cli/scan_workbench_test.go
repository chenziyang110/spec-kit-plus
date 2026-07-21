package cli

import (
	"bytes"
	"encoding/json"
	"fmt"
	"math"
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
	stdout.Reset()
	stderr.Reset()
	code = Run([]string{"scan-lease", "--packet-id", "lane-001", "--worker-id", "worker-a", "--format", "json"}, &stdout, &stderr, "test")
	if code != 0 {
		t.Fatalf("scan-lease code = %d stderr=%s stdout=%s", code, stderr.String(), stdout.String())
	}
	var lease map[string]any
	if err := json.Unmarshal(stdout.Bytes(), &lease); err != nil {
		t.Fatalf("decode scan-lease output: %v; output=%s", err, stdout.String())
	}
	attemptID, _ := lease["attempt_id"].(string)
	if attemptID == "" {
		t.Fatalf("scan-lease output has no attempt_id: %#v", lease)
	}

	resultPath := filepath.Join(root, ".specify", "project-cognition", "workbench", "pending-results", "lane-001.json")
	writeCLIJSON(t, resultPath, acceptedCLIWorkerResult("lane-001", attemptID, "src/app.go"))
	stdout.Reset()
	stderr.Reset()
	code = Run([]string{"scan-accept", "--packet-id", "lane-001", "--attempt-id", attemptID, "--format", "json"}, &stdout, &stderr, "test")
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

func TestScanStatusReportsCompactLeaseCounts(t *testing.T) {
	root := t.TempDir()
	for _, rel := range []string{".specify/project-cognition/tmp", "src"} {
		if err := os.MkdirAll(filepath.Join(root, filepath.FromSlash(rel)), 0o755); err != nil {
			t.Fatal(err)
		}
	}
	files := []string{"src/a.go", "src/b.go", "src/c.go"}
	for _, rel := range files {
		if err := os.WriteFile(filepath.Join(root, filepath.FromSlash(rel)), []byte("package fixture\n"), 0o644); err != nil {
			t.Fatal(err)
		}
	}
	writeCLIJSON(t, filepath.Join(root, ".specify", "project-cognition", "tmp", "scan-files.json"), map[string]any{
		"files": files,
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
	if code := Run([]string{"scan-prepare", "--packet-size", "2", "--format", "json"}, &stdout, &stderr, "test"); code != 0 {
		t.Fatalf("scan-prepare code=%d stderr=%s stdout=%s", code, stderr.String(), stdout.String())
	}
	stdout.Reset()
	stderr.Reset()
	if code := Run([]string{"scan-lease", "--worker-id", "worker-a", "--format", "json"}, &stdout, &stderr, "test"); code != 0 {
		t.Fatalf("scan-lease code=%d stderr=%s stdout=%s", code, stderr.String(), stdout.String())
	}
	var lease map[string]any
	if err := json.Unmarshal(stdout.Bytes(), &lease); err != nil {
		t.Fatalf("decode scan-lease output: %v; output=%s", err, stdout.String())
	}
	if lease["attempt_id"] == nil || lease["attempt_id"] == "" {
		t.Fatalf("scan-lease output has no attempt_id: %#v", lease)
	}

	stdout.Reset()
	stderr.Reset()
	if code := Run([]string{"scan-status", "--format", "json"}, &stdout, &stderr, "test"); code != 0 {
		t.Fatalf("scan-status code=%d stderr=%s stdout=%s", code, stderr.String(), stdout.String())
	}
	var status map[string]any
	if err := json.Unmarshal(stdout.Bytes(), &status); err != nil {
		t.Fatalf("decode scan-status output: %v; output=%s", err, stdout.String())
	}
	packetCounts, ok := status["packets"].(map[string]any)
	if !ok {
		t.Fatalf("scan-status packets = %#v, want compact count object", status["packets"])
	}
	if packetCounts["pending"] != float64(1) || packetCounts["leased"] != float64(1) || packetCounts["accepted"] != float64(0) {
		t.Fatalf("scan-status packet counts = %#v, want pending=1 leased=1 accepted=0", packetCounts)
	}
	if remaining, ok := status["estimated_remaining_tokens"].(float64); !ok || remaining <= 0 {
		t.Fatalf("estimated_remaining_tokens = %#v, want positive number", status["estimated_remaining_tokens"])
	}
	output := stdout.String()
	for _, forbidden := range append([]string{"assigned_paths"}, files...) {
		if strings.Contains(output, forbidden) {
			t.Fatalf("compact scan-status leaked %q: %s", forbidden, output)
		}
	}
}

func TestEffectiveScanWorkerBudgetAccountsForContextAndNeverRoundsToDefault(t *testing.T) {
	budget, err := effectiveScanWorkerBudget(0, 100_000, []int64{10_000, 5_000, 10_000, 5_000, 10_000}, 75)
	if err != nil {
		t.Fatal(err)
	}
	if budget != 45_000 {
		t.Fatalf("effective budget = %d, want 45000", budget)
	}
	if _, err := effectiveScanWorkerBudget(0, 1, nil, 75); err == nil || !strings.Contains(err.Error(), "too small") {
		t.Fatalf("round-to-zero budget error = %v", err)
	}
	if _, err := effectiveScanWorkerBudget(0, 10, []int64{math.MaxInt64, math.MaxInt64}, 75); err == nil || !strings.Contains(err.Error(), "exhaust") {
		t.Fatalf("overflowing reserve budget error = %v", err)
	}
	if _, err := effectiveScanWorkerBudget(1_000, 0, []int64{100}, 75); err == nil || !strings.Contains(err.Error(), "cannot combine") {
		t.Fatalf("direct budget plus reserve error = %v", err)
	}
	if _, err := effectiveScanWorkerBudget(0, 0, []int64{100}, 75); err == nil || !strings.Contains(err.Error(), "context-window-tokens") {
		t.Fatalf("reserve without context window error = %v", err)
	}
}

func TestScanCheckpointRejectsResultOutsideDesignatedWorkbenchPath(t *testing.T) {
	root := t.TempDir()
	for _, rel := range []string{".specify/project-cognition/tmp", "src"} {
		if err := os.MkdirAll(filepath.Join(root, filepath.FromSlash(rel)), 0o755); err != nil {
			t.Fatal(err)
		}
	}
	if err := os.WriteFile(filepath.Join(root, "src", "app.go"), []byte("package app\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	writeCLIJSON(t, filepath.Join(root, ".specify", "project-cognition", "tmp", "scan-files.json"), map[string]any{"files": []string{"src/app.go"}})
	old, err := os.Getwd()
	if err != nil {
		t.Fatal(err)
	}
	if err := os.Chdir(root); err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { _ = os.Chdir(old) })

	var stdout, stderr bytes.Buffer
	if code := Run([]string{"scan-prepare", "--format", "json"}, &stdout, &stderr, "test"); code != 0 {
		t.Fatalf("scan-prepare code=%d stderr=%s stdout=%s", code, stderr.String(), stdout.String())
	}
	stdout.Reset()
	stderr.Reset()
	if code := Run([]string{"scan-lease", "--worker-id", "worker-a", "--format", "json"}, &stdout, &stderr, "test"); code != 0 {
		t.Fatalf("scan-lease code=%d stderr=%s stdout=%s", code, stderr.String(), stdout.String())
	}
	var lease map[string]any
	if err := json.Unmarshal(stdout.Bytes(), &lease); err != nil {
		t.Fatal(err)
	}
	external := filepath.Join(t.TempDir(), "result.json")
	writeCLIJSON(t, external, map[string]any{})
	stdout.Reset()
	stderr.Reset()
	code := Run([]string{
		"scan-checkpoint", "--packet-id", "lane-001", "--attempt-id", lease["attempt_id"].(string),
		"--result", external, "--format", "json",
	}, &stdout, &stderr, "test")
	if code == 0 || !strings.Contains(stdout.String(), "CLI-designated") {
		t.Fatalf("outside checkpoint code=%d stderr=%s stdout=%s", code, stderr.String(), stdout.String())
	}
}

func TestScanCLIRequeuesCheckpointedRemainderEndToEnd(t *testing.T) {
	root := t.TempDir()
	for _, rel := range []string{".specify/project-cognition/tmp", "src"} {
		if err := os.MkdirAll(filepath.Join(root, filepath.FromSlash(rel)), 0o755); err != nil {
			t.Fatal(err)
		}
	}
	files := []string{"src/a.go", "src/b.go", "src/c.go"}
	for _, rel := range files {
		if err := os.WriteFile(filepath.Join(root, filepath.FromSlash(rel)), []byte("package fixture\n"), 0o644); err != nil {
			t.Fatal(err)
		}
	}
	writeCLIJSON(t, filepath.Join(root, ".specify", "project-cognition", "tmp", "scan-files.json"), map[string]any{"files": files})

	old, err := os.Getwd()
	if err != nil {
		t.Fatal(err)
	}
	if err := os.Chdir(root); err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { _ = os.Chdir(old) })

	runJSON := func(args ...string) map[string]any {
		t.Helper()
		var stdout, stderr bytes.Buffer
		if code := Run(args, &stdout, &stderr, "test"); code != 0 {
			t.Fatalf("%v code=%d stderr=%s stdout=%s", args, code, stderr.String(), stdout.String())
		}
		var payload map[string]any
		if err := json.Unmarshal(stdout.Bytes(), &payload); err != nil {
			t.Fatalf("decode %v output: %v; output=%s", args, err, stdout.String())
		}
		return payload
	}

	runJSON("scan-prepare", "--max-paths", "3", "--format", "json")
	firstLease := runJSON("scan-lease", "--packet-id", "lane-001", "--worker-id", "worker-a", "--format", "json")
	firstAttempt := firstLease["attempt_id"].(string)
	firstResult := filepath.Join(root, ".specify", "project-cognition", "workbench", "pending-results", "lane-001.json")
	writeCLIJSON(t, firstResult, checkpointCLIWorkerResult("lane-001", firstAttempt, 1, files, files[:2]))
	runJSON("scan-checkpoint", "--packet-id", "lane-001", "--attempt-id", firstAttempt, "--result", firstResult, "--format", "json")
	requeued := runJSON("scan-requeue", "--packet-id", "lane-001", "--attempt-id", firstAttempt, "--format", "json")
	if requeued["accepted_path_count"] != float64(2) || requeued["remaining_path_count"] != float64(1) {
		t.Fatalf("scan-requeue payload = %#v", requeued)
	}

	status := runJSON("scan-status", "--format", "json")
	counts := status["packets"].(map[string]any)
	if counts["accepted"] != float64(1) || counts["pending"] != float64(1) {
		t.Fatalf("post-requeue status = %#v", status)
	}
	secondLease := runJSON("scan-lease", "--worker-id", "worker-b", "--format", "json")
	secondPacket := secondLease["packet_id"].(string)
	secondAttempt := secondLease["attempt_id"].(string)
	secondResult := filepath.Join(root, ".specify", "project-cognition", "workbench", "pending-results", secondPacket+".json")
	writeCLIJSON(t, secondResult, acceptedCLIWorkerResult(secondPacket, secondAttempt, files[2]))
	runJSON("scan-accept", "--packet-id", secondPacket, "--attempt-id", secondAttempt, "--result", secondResult, "--format", "json")
	validated := runJSON("validate-scan", "--format", "json")
	if validated["status"] != "ok" || validated["readiness"] != "scan_ready" {
		t.Fatalf("validate-scan payload = %#v", validated)
	}
}

func checkpointCLIWorkerResult(packetID, attemptID string, sequence int, assigned, completed []string) map[string]any {
	done := map[string]bool{}
	for _, path := range completed {
		done[path] = true
	}
	todo := []string{}
	for _, path := range assigned {
		if !done[path] {
			todo = append(todo, path)
		}
	}
	coverage := []map[string]any{}
	evidence := []map[string]any{}
	nodes := []map[string]any{}
	for index, path := range completed {
		evidenceID := fmt.Sprintf("E-%s-%d", packetID, index+1)
		nodeID := fmt.Sprintf("N-%s-%d", packetID, index+1)
		coverage = append(coverage, map[string]any{"path": path, "outcome": "read", "evidence_ids": []string{evidenceID}})
		evidence = append(evidence, map[string]any{
			"id": evidenceID, "source_kind": "source", "source_path": path,
			"span": "1:1-1:15", "extractor": "scan-worker", "content_hash": "hash-" + evidenceID,
		})
		nodes = append(nodes, map[string]any{
			"id": nodeID, "type": "file", "title": filepath.Base(path), "confidence": "high",
			"paths": []string{path}, "evidence_ids": []string{evidenceID},
		})
	}
	return map[string]any{
		"protocol": "map_scan_result.v2", "packet_id": packetID, "attempt_id": attemptID, "sequence": sequence,
		"assigned_paths": assigned, "paths_read": completed,
		"ledger":   map[string]any{"todo": todo, "doing": []string{}, "done": completed, "blocked": []string{}, "overflow": []string{}},
		"coverage": coverage, "evidence": evidence, "nodes": nodes,
		"edges": []map[string]any{}, "observations": []map[string]any{}, "claims": []map[string]any{},
		"confidence": "high", "acceptance": "partial",
	}
}

func acceptedCLIWorkerResult(packetID string, attemptID string, path string) map[string]any {
	evidenceID := "E-" + packetID
	nodeID := "N-" + packetID
	return map[string]any{
		"protocol":       "map_scan_result.v2",
		"packet_id":      packetID,
		"attempt_id":     attemptID,
		"sequence":       1,
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
		"acceptance":   "partial",
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
