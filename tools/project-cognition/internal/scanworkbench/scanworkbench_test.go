package scanworkbench

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"testing"
	"time"

	"github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/build"
	rt "github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/runtime"
	"github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/validation"
)

func TestPrepareDefaultsToLowTierPacketSize(t *testing.T) {
	files := make([]string, 26)
	for i := range files {
		files[i] = fmt.Sprintf("src/file-%02d.go", i+1)
	}
	paths := newScanPaths(t, files)

	payload, err := Prepare(paths, PrepareInput{})
	if err != nil {
		t.Fatalf("Prepare returned error: %v", err)
	}
	if payload.PacketCount != 2 {
		t.Fatalf("default packet count = %d, want 2 for 26 paths", payload.PacketCount)
	}
	queue := readJSONObject(t, filepath.Join(paths.RuntimeDir, "workbench", "scan-queue.json"))
	packets := objectRows(t, queue["packets"])
	if got := len(stringSlice(t, packets[0]["assigned_paths"])); got != 25 {
		t.Fatalf("default first packet size = %d, want 25", got)
	}
}

func TestPrepareCreatesBoundedConcretePacketSkeleton(t *testing.T) {
	paths := newScanPaths(t, []string{"src/z.go", "README.md", "src/a.go"})

	payload, err := Prepare(paths, PrepareInput{PacketSize: 2})
	if err != nil {
		t.Fatalf("Prepare returned error: %v", err)
	}
	if payload.Status != "prepared" || payload.PathCount != 3 || payload.PacketCount != 2 {
		t.Fatalf("unexpected prepare payload: %#v", payload)
	}

	queue := readJSONObject(t, filepath.Join(paths.RuntimeDir, "workbench", "scan-queue.json"))
	packets := objectRows(t, queue["packets"])
	if got := stringSlice(t, packets[0]["assigned_paths"]); !equalStrings(got, []string{"README.md", "src/a.go"}) {
		t.Fatalf("first packet assigned_paths = %v", got)
	}
	if got := stringSlice(t, packets[1]["assigned_paths"]); !equalStrings(got, []string{"src/z.go"}) {
		t.Fatalf("second packet assigned_paths = %v", got)
	}
	for _, row := range packets {
		if row["state"] != "pending" {
			t.Fatalf("packet state = %v, want pending", row["state"])
		}
	}

	universe := readJSONObject(t, filepath.Join(paths.RuntimeDir, "workbench", "repository-universe.json"))
	if universe["schema_version"] != float64(1) {
		t.Fatalf("repository-universe schema_version = %v", universe["schema_version"])
	}
	if got := stringSlice(t, universe["included_paths"]); !equalStrings(got, []string{"README.md", "src/a.go", "src/z.go"}) {
		t.Fatalf("included_paths = %v", got)
	}

	packetBody, err := os.ReadFile(filepath.Join(paths.RuntimeDir, "workbench", "scan-packets", "lane-001.md"))
	if err != nil {
		t.Fatal(err)
	}
	text := string(packetBody)
	for _, want := range []string{
		"mode: read_only",
		"README.md",
		"src/a.go",
		"worker-results/lane-001.json",
		`"ledger"`,
		`"coverage"`,
		`"evidence"`,
		`"assigned_paths"`,
	} {
		if !strings.Contains(text, want) {
			t.Fatalf("packet is missing %q:\n%s", want, text)
		}
	}
	if strings.Contains(text, "**") || strings.Contains(text, "src/*") {
		t.Fatalf("packet contains worker-discretion glob: %s", text)
	}
}

func TestAcceptMergesPacketAndProducesBuildableScanPackage(t *testing.T) {
	paths := newScanPaths(t, []string{"src/app.go"})
	if _, err := Prepare(paths, PrepareInput{PacketSize: 25}); err != nil {
		t.Fatal(err)
	}
	resultPath := filepath.Join(t.TempDir(), "lane-001.json")
	writeJSON(t, resultPath, acceptedWorkerResult("lane-001", "src/app.go"))

	payload, err := Accept(paths, AcceptInput{PacketID: "lane-001", ResultPath: resultPath})
	if err != nil {
		t.Fatalf("Accept returned error: %v", err)
	}
	if payload.Status != "accepted" || payload.PacketID != "lane-001" || payload.AcceptedPathCount != 1 {
		t.Fatalf("unexpected accept payload: %#v", payload)
	}

	gate := validation.ValidateScan(paths)
	if gate.Status != "ok" || gate.Readiness != "scan_ready" {
		t.Fatalf("validate-scan = %#v", gate)
	}

	buildPayload, err := build.Run(paths)
	if err != nil {
		t.Fatalf("build-from-scan returned error: %v; payload=%#v", err, buildPayload)
	}
	if buildPayload.Status != "ok" || buildPayload.Readiness != rt.ReadyReadiness {
		t.Fatalf("build-from-scan payload = %#v", buildPayload)
	}
	buildGate := validation.ValidateBuild(paths)
	if buildGate.Status != "ok" || buildGate.Readiness != "query_ready" {
		t.Fatalf("validate-build = %#v", buildGate)
	}

	nodes := readJSONObject(t, filepath.Join(paths.RuntimeDir, "provisional", "nodes.json"))
	nodeRows := objectRows(t, nodes["nodes"])
	if got := stringSlice(t, nodeRows[0]["paths"]); !equalStrings(got, []string{"src/app.go"}) {
		t.Fatalf("nodes[].paths = %v; path_index source was lost", got)
	}
}

func TestAcceptRejectsCrossPacketPathsWithoutMerging(t *testing.T) {
	paths := newScanPaths(t, []string{"src/a.go", "src/b.go"})
	if _, err := Prepare(paths, PrepareInput{PacketSize: 1}); err != nil {
		t.Fatal(err)
	}
	result := acceptedWorkerResult("lane-001", "src/a.go")
	evidence := objectRows(t, result["evidence"])
	evidence[0]["source_path"] = "src/b.go"
	resultPath := filepath.Join(t.TempDir(), "lane-001.json")
	writeJSON(t, resultPath, result)

	if _, err := Accept(paths, AcceptInput{PacketID: "lane-001", ResultPath: resultPath}); err == nil {
		t.Fatal("Accept succeeded for evidence outside assigned_paths")
	}
	if _, err := os.Stat(filepath.Join(paths.RuntimeDir, "workbench", "worker-results", "lane-001.json")); !os.IsNotExist(err) {
		t.Fatalf("invalid result was persisted: %v", err)
	}
	nodes := readJSONObject(t, filepath.Join(paths.RuntimeDir, "provisional", "nodes.json"))
	if got := objectRows(t, nodes["nodes"]); len(got) != 0 {
		t.Fatalf("invalid result mutated provisional nodes: %#v", got)
	}
	queue := readJSONObject(t, filepath.Join(paths.RuntimeDir, "workbench", "scan-queue.json"))
	if state := objectRows(t, queue["packets"])[0]["state"]; state != "pending" {
		t.Fatalf("invalid result changed queue state to %v", state)
	}
}

func TestAcceptKeepsHandoffLedgerDeterministicAcrossCompletionOrder(t *testing.T) {
	paths := newScanPaths(t, []string{"src/a.go", "src/b.go"})
	if _, err := Prepare(paths, PrepareInput{PacketSize: 1}); err != nil {
		t.Fatal(err)
	}
	for _, item := range []struct {
		packetID string
		path     string
	}{{"lane-002", "src/b.go"}, {"lane-001", "src/a.go"}} {
		resultPath := filepath.Join(t.TempDir(), item.packetID+".json")
		writeJSON(t, resultPath, acceptedWorkerResult(item.packetID, item.path))
		if _, err := Accept(paths, AcceptInput{PacketID: item.packetID, ResultPath: resultPath}); err != nil {
			t.Fatal(err)
		}
	}

	handoffs := readJSONObject(t, filepath.Join(paths.RuntimeDir, "workbench", "handoff-ledger.json"))
	events := objectRows(t, handoffs["events"])
	got := make([]string, 0, len(events))
	for _, event := range events {
		got = append(got, event["event_id"].(string))
	}
	want := []string{"dispatch-lane-001", "dispatch-lane-002", "return-lane-001", "return-lane-002"}
	if !equalStrings(got, want) {
		t.Fatalf("handoff event order = %v, want %v", got, want)
	}
}

func TestAcceptSerializesConcurrentPacketsWithoutLostUpdates(t *testing.T) {
	paths := newScanPaths(t, []string{"src/a.go", "src/b.go"})
	if _, err := Prepare(paths, PrepareInput{PacketSize: 1}); err != nil {
		t.Fatal(err)
	}
	resultDir := t.TempDir()
	for _, item := range []struct {
		packetID string
		path     string
	}{{"lane-001", "src/a.go"}, {"lane-002", "src/b.go"}} {
		writeJSON(t, filepath.Join(resultDir, item.packetID+".json"), acceptedWorkerResult(item.packetID, item.path))
	}

	var wg sync.WaitGroup
	errorsByPacket := make(chan error, 2)
	for _, packetID := range []string{"lane-001", "lane-002"} {
		packetID := packetID
		wg.Add(1)
		go func() {
			defer wg.Done()
			_, err := Accept(paths, AcceptInput{
				PacketID:   packetID,
				ResultPath: filepath.Join(resultDir, packetID+".json"),
			})
			errorsByPacket <- err
		}()
	}
	wg.Wait()
	close(errorsByPacket)
	for err := range errorsByPacket {
		if err != nil {
			t.Fatalf("concurrent Accept returned error: %v", err)
		}
	}

	queue := readJSONObject(t, filepath.Join(paths.RuntimeDir, "workbench", "scan-queue.json"))
	for _, packet := range objectRows(t, queue["packets"]) {
		if packet["state"] != "accepted" {
			t.Fatalf("concurrent accept lost queue update: %#v", packet)
		}
	}
	if got := len(objectRows(t, readJSONObject(t, filepath.Join(paths.RuntimeDir, "provisional", "nodes.json"))["nodes"])); got != 2 {
		t.Fatalf("node count after concurrent accept = %d, want 2", got)
	}
	if got := len(objectRows(t, readJSONObject(t, filepath.Join(paths.RuntimeDir, "coverage.json"))["rows"])); got != 2 {
		t.Fatalf("coverage count after concurrent accept = %d, want 2", got)
	}
}

func TestAcceptWaitsForExistingWorkbenchOperation(t *testing.T) {
	paths := newScanPaths(t, []string{"src/app.go"})
	if _, err := Prepare(paths, PrepareInput{}); err != nil {
		t.Fatal(err)
	}
	resultPath := filepath.Join(t.TempDir(), "lane-001.json")
	writeJSON(t, resultPath, acceptedWorkerResult("lane-001", "src/app.go"))

	release, err := acquireWorkbenchLock(paths)
	if err != nil {
		t.Fatal(err)
	}
	done := make(chan error, 1)
	go func() {
		_, err := Accept(paths, AcceptInput{PacketID: "lane-001", ResultPath: resultPath})
		done <- err
	}()
	select {
	case err := <-done:
		release()
		t.Fatalf("Accept bypassed existing lock: %v", err)
	case <-time.After(100 * time.Millisecond):
	}
	release()
	select {
	case err := <-done:
		if err != nil {
			t.Fatalf("Accept after lock release returned error: %v", err)
		}
	case <-time.After(2 * time.Second):
		t.Fatal("Accept did not resume after lock release")
	}
}

func TestAcceptPreservesCrossPacketEdgeByCanonicalPath(t *testing.T) {
	paths := newScanPaths(t, []string{"src/a.go", "src/b.go"})
	if _, err := Prepare(paths, PrepareInput{PacketSize: 1}); err != nil {
		t.Fatal(err)
	}
	first := acceptedWorkerResult("lane-001", "src/a.go")
	first["edges"] = []map[string]any{{
		"id": "EDGE-a-imports-b", "type": "imports",
		"source_id": "N-lane-001", "target_id": "src/b.go",
		"confidence": "high", "evidence_ids": []string{"E-lane-001"},
	}}
	resultDir := t.TempDir()
	writeJSON(t, filepath.Join(resultDir, "lane-001.json"), first)
	writeJSON(t, filepath.Join(resultDir, "lane-002.json"), acceptedWorkerResult("lane-002", "src/b.go"))
	for _, packetID := range []string{"lane-001", "lane-002"} {
		if _, err := Accept(paths, AcceptInput{PacketID: packetID, ResultPath: filepath.Join(resultDir, packetID+".json")}); err != nil {
			t.Fatalf("Accept %s returned error: %v", packetID, err)
		}
	}

	if gate := validation.ValidateScan(paths); gate.Status != "ok" {
		t.Fatalf("cross-packet validate-scan = %#v", gate)
	}
	payload, err := build.Run(paths)
	if err != nil || payload.Status != "ok" {
		t.Fatalf("cross-packet build = %#v, err=%v", payload, err)
	}
	if gate := validation.ValidateBuild(paths); gate.Status != "ok" {
		t.Fatalf("cross-packet validate-build = %#v", gate)
	}
}

func TestPrepareRejectsUnsafeScanSetPath(t *testing.T) {
	paths := newScanPaths(t, []string{"src/app.go"})
	writeJSON(t, filepath.Join(paths.RuntimeDir, "tmp", "scan-files.json"), map[string]any{
		"files": []string{"../outside.go"},
	})

	if _, err := Prepare(paths, PrepareInput{}); err == nil {
		t.Fatal("Prepare accepted a path outside the repository")
	}
}

func TestPrepareRejectsSymlinkedRuntimeControlDirectory(t *testing.T) {
	root := t.TempDir()
	if err := os.MkdirAll(filepath.Join(root, ".specify"), 0o755); err != nil {
		t.Fatal(err)
	}
	paths, err := rt.ResolvePaths(root)
	if err != nil {
		t.Fatal(err)
	}
	external := t.TempDir()
	sentinel := filepath.Join(external, "sentinel.txt")
	if err := os.WriteFile(sentinel, []byte("keep"), 0o644); err != nil {
		t.Fatal(err)
	}
	if err := os.Symlink(external, paths.RuntimeDir); err != nil {
		t.Skipf("symbolic links are unavailable: %v", err)
	}

	if _, err := Prepare(paths, PrepareInput{Force: true}); err == nil || !strings.Contains(err.Error(), "symbolic links") {
		t.Fatalf("Prepare with symlinked RuntimeDir error = %v", err)
	}
	if data, err := os.ReadFile(sentinel); err != nil || string(data) != "keep" {
		t.Fatalf("external sentinel was changed: data=%q err=%v", data, err)
	}
}

func TestPrepareRequiresForceBeforeReplacingAcceptedWorkbench(t *testing.T) {
	paths := newScanPaths(t, []string{"src/app.go"})
	if _, err := Prepare(paths, PrepareInput{}); err != nil {
		t.Fatal(err)
	}
	resultPath := filepath.Join(t.TempDir(), "lane-001.json")
	writeJSON(t, resultPath, acceptedWorkerResult("lane-001", "src/app.go"))
	if _, err := Accept(paths, AcceptInput{PacketID: "lane-001", ResultPath: resultPath}); err != nil {
		t.Fatal(err)
	}

	if _, err := Prepare(paths, PrepareInput{}); err == nil || !strings.Contains(err.Error(), "--force") {
		t.Fatalf("Prepare without force error = %v, want explicit --force requirement", err)
	}
	queue := readJSONObject(t, filepath.Join(paths.RuntimeDir, "workbench", "scan-queue.json"))
	if state := objectRows(t, queue["packets"])[0]["state"]; state != "accepted" {
		t.Fatalf("rejected prepare changed existing queue state to %v", state)
	}
	if _, err := os.Stat(filepath.Join(paths.RuntimeDir, "workbench", "worker-results", "lane-001.json")); err != nil {
		t.Fatalf("rejected prepare removed accepted result: %v", err)
	}

	if _, err := Prepare(paths, PrepareInput{Force: true}); err != nil {
		t.Fatalf("forced Prepare returned error: %v", err)
	}
	queue = readJSONObject(t, filepath.Join(paths.RuntimeDir, "workbench", "scan-queue.json"))
	if state := objectRows(t, queue["packets"])[0]["state"]; state != "pending" {
		t.Fatalf("forced prepare queue state = %v, want pending", state)
	}
	if _, err := os.Stat(filepath.Join(paths.RuntimeDir, "workbench", "worker-results", "lane-001.json")); !os.IsNotExist(err) {
		t.Fatalf("forced prepare retained old accepted result: %v", err)
	}
}

func TestAcceptRecoversMatchingPartiallyMergedRowsWithoutDuplicates(t *testing.T) {
	paths := newScanPaths(t, []string{"src/app.go"})
	if _, err := Prepare(paths, PrepareInput{}); err != nil {
		t.Fatal(err)
	}
	result := acceptedWorkerResult("lane-001", "src/app.go")
	writeJSON(t, filepath.Join(paths.RuntimeDir, "evidence", "lane-001.json"), map[string]any{"rows": result["evidence"]})
	writeJSON(t, filepath.Join(paths.RuntimeDir, "provisional", "nodes.json"), map[string]any{"nodes": result["nodes"]})
	writeJSON(t, filepath.Join(paths.RuntimeDir, "coverage.json"), map[string]any{"rows": result["coverage"]})
	resultPath := filepath.Join(t.TempDir(), "lane-001.json")
	writeJSON(t, resultPath, result)

	if _, err := Accept(paths, AcceptInput{PacketID: "lane-001", ResultPath: resultPath}); err != nil {
		t.Fatalf("Accept could not recover matching partial state: %v", err)
	}
	if got := len(objectRows(t, readJSONObject(t, filepath.Join(paths.RuntimeDir, "provisional", "nodes.json"))["nodes"])); got != 1 {
		t.Fatalf("node count after recovery = %d, want 1", got)
	}
	if got := len(objectRows(t, readJSONObject(t, filepath.Join(paths.RuntimeDir, "coverage.json"))["rows"])); got != 1 {
		t.Fatalf("coverage count after recovery = %d, want 1", got)
	}
}

func TestAcceptRejectsConflictingPartiallyMergedRow(t *testing.T) {
	paths := newScanPaths(t, []string{"src/app.go"})
	if _, err := Prepare(paths, PrepareInput{}); err != nil {
		t.Fatal(err)
	}
	result := acceptedWorkerResult("lane-001", "src/app.go")
	conflict := cloneTestObject(objectRows(t, result["nodes"])[0])
	conflict["title"] = "different content"
	writeJSON(t, filepath.Join(paths.RuntimeDir, "provisional", "nodes.json"), map[string]any{"nodes": []map[string]any{conflict}})
	resultPath := filepath.Join(t.TempDir(), "lane-001.json")
	writeJSON(t, resultPath, result)

	if _, err := Accept(paths, AcceptInput{PacketID: "lane-001", ResultPath: resultPath}); err == nil || !strings.Contains(err.Error(), "conflict") {
		t.Fatalf("Accept conflict error = %v", err)
	}
	queue := readJSONObject(t, filepath.Join(paths.RuntimeDir, "workbench", "scan-queue.json"))
	if state := objectRows(t, queue["packets"])[0]["state"]; state != "pending" {
		t.Fatalf("conflicting retry changed queue state to %v", state)
	}
}

func TestAcceptSameResultIsIdempotentAfterAccepted(t *testing.T) {
	paths := newScanPaths(t, []string{"src/app.go"})
	if _, err := Prepare(paths, PrepareInput{}); err != nil {
		t.Fatal(err)
	}
	resultPath := filepath.Join(t.TempDir(), "lane-001.json")
	writeJSON(t, resultPath, acceptedWorkerResult("lane-001", "src/app.go"))
	if _, err := Accept(paths, AcceptInput{PacketID: "lane-001", ResultPath: resultPath}); err != nil {
		t.Fatal(err)
	}
	payload, err := Accept(paths, AcceptInput{PacketID: "lane-001", ResultPath: resultPath})
	if err != nil {
		t.Fatalf("accepted packet retry returned error: %v", err)
	}
	if payload.Status != "accepted" || payload.PendingPackets != 0 {
		t.Fatalf("accepted retry payload = %#v", payload)
	}
	if got := len(objectRows(t, readJSONObject(t, filepath.Join(paths.RuntimeDir, "provisional", "nodes.json"))["nodes"])); got != 1 {
		t.Fatalf("node count after accepted retry = %d, want 1", got)
	}

	changed := acceptedWorkerResult("lane-001", "src/app.go")
	objectRows(t, changed["nodes"])[0]["title"] = "changed"
	writeJSON(t, resultPath, changed)
	if _, err := Accept(paths, AcceptInput{PacketID: "lane-001", ResultPath: resultPath}); err == nil {
		t.Fatal("accepted packet retry allowed a different result")
	}
}

func TestAcceptHumanStateFailureCommitsCanonicalQueueAndRemainsRetryable(t *testing.T) {
	paths := newScanPaths(t, []string{"src/app.go"})
	if _, err := Prepare(paths, PrepareInput{}); err != nil {
		t.Fatal(err)
	}
	mapStatePath := filepath.Join(paths.RuntimeDir, "workbench", "map-state.md")
	if err := os.Remove(mapStatePath); err != nil {
		t.Fatal(err)
	}
	if err := os.Mkdir(mapStatePath, 0o755); err != nil {
		t.Fatal(err)
	}
	resultPath := filepath.Join(t.TempDir(), "lane-001.json")
	writeJSON(t, resultPath, acceptedWorkerResult("lane-001", "src/app.go"))
	if _, err := Accept(paths, AcceptInput{PacketID: "lane-001", ResultPath: resultPath}); err == nil {
		t.Fatal("Accept succeeded despite human-state render fault")
	}
	queue := readJSONObject(t, filepath.Join(paths.RuntimeDir, "workbench", "scan-queue.json"))
	if state := objectRows(t, queue["packets"])[0]["state"]; state != "accepted" {
		t.Fatalf("render fault left canonical queue state %v, want accepted", state)
	}
	if err := os.Remove(mapStatePath); err != nil {
		t.Fatal(err)
	}
	if _, err := Accept(paths, AcceptInput{PacketID: "lane-001", ResultPath: resultPath}); err != nil {
		t.Fatalf("retry after human-state fault failed: %v", err)
	}
}

func acceptedWorkerResult(packetID string, path string) map[string]any {
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
			"span":         "1:1-3:1",
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

func newScanPaths(t *testing.T, files []string) rt.Paths {
	t.Helper()
	root := t.TempDir()
	if err := os.MkdirAll(filepath.Join(root, ".specify"), 0o755); err != nil {
		t.Fatal(err)
	}
	paths, err := rt.ResolvePaths(root)
	if err != nil {
		t.Fatal(err)
	}
	for _, rel := range files {
		full := filepath.Join(root, filepath.FromSlash(rel))
		if err := os.MkdirAll(filepath.Dir(full), 0o755); err != nil {
			t.Fatal(err)
		}
		if err := os.WriteFile(full, []byte("package fixture\n"), 0o644); err != nil {
			t.Fatal(err)
		}
	}
	if err := os.MkdirAll(filepath.Join(paths.RuntimeDir, "tmp"), 0o755); err != nil {
		t.Fatal(err)
	}
	writeJSON(t, filepath.Join(paths.RuntimeDir, "tmp", "scan-files.json"), map[string]any{"files": files})
	return paths
}

func writeJSON(t *testing.T, path string, value any) {
	t.Helper()
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		t.Fatal(err)
	}
	data, err := json.MarshalIndent(value, "", "  ")
	if err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(path, append(data, '\n'), 0o644); err != nil {
		t.Fatal(err)
	}
}

func readJSONObject(t *testing.T, path string) map[string]any {
	t.Helper()
	data, err := os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}
	var value map[string]any
	if err := json.Unmarshal(data, &value); err != nil {
		t.Fatal(err)
	}
	return value
}

func objectRows(t *testing.T, value any) []map[string]any {
	t.Helper()
	raw, ok := value.([]any)
	if !ok {
		if typed, ok := value.([]map[string]any); ok {
			return typed
		}
		t.Fatalf("value is not an object array: %#v", value)
	}
	rows := make([]map[string]any, 0, len(raw))
	for _, item := range raw {
		row, ok := item.(map[string]any)
		if !ok {
			t.Fatalf("array item is not an object: %#v", item)
		}
		rows = append(rows, row)
	}
	return rows
}

func stringSlice(t *testing.T, value any) []string {
	t.Helper()
	if typed, ok := value.([]string); ok {
		return typed
	}
	raw, ok := value.([]any)
	if !ok {
		t.Fatalf("value is not a string array: %#v", value)
	}
	values := make([]string, 0, len(raw))
	for _, item := range raw {
		text, ok := item.(string)
		if !ok {
			t.Fatalf("array item is not a string: %#v", item)
		}
		values = append(values, text)
	}
	return values
}

func equalStrings(left []string, right []string) bool {
	if len(left) != len(right) {
		return false
	}
	for i := range left {
		if left[i] != right[i] {
			return false
		}
	}
	return true
}

func cloneTestObject(value map[string]any) map[string]any {
	clone := make(map[string]any, len(value))
	for key, item := range value {
		clone[key] = item
	}
	return clone
}
