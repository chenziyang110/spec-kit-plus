package scanworkbench

import (
	"os"
	"path/filepath"
	"strings"
	"testing"

	rt "github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/runtime"
	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/scanartifacts"
	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/scanreceipt"
)

func TestPrepareResumesCompatibleWorkbenchWithoutForce(t *testing.T) {
	paths := newScanPaths(t, []string{"src/app.go"})
	first, err := Prepare(paths, PrepareInput{})
	if err != nil {
		t.Fatal(err)
	}
	lease := mustLeasePacket(t, paths, "lane-001")
	resultPath := filepath.Join(t.TempDir(), "lane-001.json")
	writeJSON(t, resultPath, bindWorkerResultToLease(acceptedWorkerResult("lane-001", "src/app.go"), lease))
	if _, err := Accept(paths, AcceptInput{PacketID: lease.PacketID, AttemptID: lease.AttemptID, ResultPath: resultPath}); err != nil {
		t.Fatal(err)
	}

	second, err := Prepare(paths, PrepareInput{})
	if err != nil {
		t.Fatalf("compatible Prepare returned error: %v", err)
	}
	if second.Status != "resumed" || second.ReusedPathCount != 1 || second.PendingPathCount != 0 {
		t.Fatalf("resumed payload = %#v", second)
	}
	if second.PreparationDigest == "" || second.PreparationDigest != first.PreparationDigest {
		t.Fatalf("preparation digest first=%q second=%q", first.PreparationDigest, second.PreparationDigest)
	}
	queue := readJSONObject(t, filepath.Join(paths.RuntimeDir, "workbench", "scan-queue.json"))
	if state := objectRows(t, queue["packets"])[0]["state"]; state != "accepted" {
		t.Fatalf("resumed queue state = %v, want accepted", state)
	}
	if _, err := os.Stat(filepath.Join(paths.RuntimeDir, "workbench", "worker-results", "lane-001.json")); err != nil {
		t.Fatalf("resumed workbench lost accepted result: %v", err)
	}
}

func TestValidatedScanCacheReusesUnchangedScopesAndQueuesChangedScope(t *testing.T) {
	files := []string{"src/a.go", "src/b.go", "src/c.go"}
	paths := newScanPaths(t, files)
	if _, err := Prepare(paths, PrepareInput{MaxPaths: 3}); err != nil {
		t.Fatal(err)
	}
	acceptAllPreparedPackets(t, paths)
	sealCacheableScan(t, paths)
	cache, err := SnapshotValidatedScanCache(paths)
	if err != nil {
		t.Fatal(err)
	}
	if cache.BundleCount != 3 || cache.PathCount != 3 {
		t.Fatalf("cache snapshot = %#v", cache)
	}

	if err := os.WriteFile(filepath.Join(paths.Root, "src", "b.go"), []byte("package fixture\n// changed\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	payload, err := Prepare(paths, PrepareInput{MaxPaths: 3})
	if err != nil {
		t.Fatalf("incremental Prepare returned error: %v", err)
	}
	if payload.Status != "prepared" || payload.ReusedPathCount != 2 || payload.PendingPathCount != 1 {
		t.Fatalf("incremental payload = %#v", payload)
	}
	if payload.CacheHitBundleCount != 2 || payload.CacheMissReasons["source_digest_changed"] != 1 {
		t.Fatalf("cache accounting = %#v", payload)
	}

	queue := readJSONObject(t, filepath.Join(paths.RuntimeDir, "workbench", "scan-queue.json"))
	acceptedPaths := []string{}
	pendingPaths := []string{}
	for _, packet := range objectRows(t, queue["packets"]) {
		switch packet["state"] {
		case "accepted":
			acceptedPaths = append(acceptedPaths, stringSlice(t, packet["assigned_paths"])...)
			if !strings.HasPrefix(packet["packet_id"].(string), "reuse-") {
				t.Fatalf("cache packet id = %v, want reuse-*", packet["packet_id"])
			}
		case "pending":
			pendingPaths = append(pendingPaths, stringSlice(t, packet["assigned_paths"])...)
			if !strings.HasPrefix(packet["packet_id"].(string), "delta-") {
				t.Fatalf("incremental packet id = %v, want delta-*", packet["packet_id"])
			}
		}
	}
	if !sameStringSet(acceptedPaths, []string{"src/a.go", "src/c.go"}) || !sameStringSet(pendingPaths, []string{"src/b.go"}) {
		t.Fatalf("incremental partition accepted=%v pending=%v", acceptedPaths, pendingPaths)
	}

	currentGeneration, _ := queue["generation_id"].(string)
	for _, entry := range mustReadDir(t, filepath.Join(paths.RuntimeDir, "workbench", "acceptance-receipts")) {
		receipt := readJSONObject(t, filepath.Join(paths.RuntimeDir, "workbench", "acceptance-receipts", entry.Name()))
		if receipt["workbench_generation_id"] != currentGeneration {
			t.Fatalf("reused receipt generation = %v, want %s", receipt["workbench_generation_id"], currentGeneration)
		}
		if receipt["source_result_path"] != "external-result" {
			t.Fatalf("reused receipt source = %v, want external-result", receipt["source_result_path"])
		}
	}
}

func TestScanCacheInvalidatesWholeCrossPathDependencyScope(t *testing.T) {
	paths := newScanPaths(t, []string{"src/a.go", "src/b.go"})
	if _, err := Prepare(paths, PrepareInput{MaxPaths: 1}); err != nil {
		t.Fatal(err)
	}
	firstLease := mustLeasePacket(t, paths, "lane-001")
	first := bindWorkerResultToLease(acceptedWorkerResult("lane-001", "src/a.go"), firstLease)
	first["edges"] = []map[string]any{{
		"id": "EDGE-a-b", "type": "depends_on", "source_id": "N-lane-001", "target_id": "src/b.go",
		"confidence": "high", "evidence_ids": []string{"E-lane-001"},
	}}
	firstPath := filepath.Join(t.TempDir(), "lane-001.json")
	writeJSON(t, firstPath, first)
	if _, err := Accept(paths, AcceptInput{PacketID: firstLease.PacketID, AttemptID: firstLease.AttemptID, ResultPath: firstPath}); err != nil {
		t.Fatal(err)
	}
	secondLease := mustLeasePacket(t, paths, "lane-002")
	secondPath := filepath.Join(t.TempDir(), "lane-002.json")
	writeJSON(t, secondPath, bindWorkerResultToLease(acceptedWorkerResult("lane-002", "src/b.go"), secondLease))
	if _, err := Accept(paths, AcceptInput{PacketID: secondLease.PacketID, AttemptID: secondLease.AttemptID, ResultPath: secondPath}); err != nil {
		t.Fatal(err)
	}
	sealCacheableScan(t, paths)
	cache, err := SnapshotValidatedScanCache(paths)
	if err != nil {
		t.Fatal(err)
	}
	if cache.BundleCount != 1 || cache.PathCount != 2 {
		t.Fatalf("cross-path cache snapshot = %#v, want one two-path bundle", cache)
	}

	if err := os.WriteFile(filepath.Join(paths.Root, "src", "b.go"), []byte("package fixture\n// changed\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	payload, err := Prepare(paths, PrepareInput{MaxPaths: 1})
	if err != nil {
		t.Fatal(err)
	}
	if payload.ReusedPathCount != 0 || payload.PendingPathCount != 2 || payload.CacheMissReasons["source_digest_changed"] != 2 {
		t.Fatalf("cross-path invalidation payload = %#v", payload)
	}
}

func TestCachePathComponentsConnectsMultiPathClaimEvidence(t *testing.T) {
	rows := scanCacheRows{
		Coverage: []map[string]any{
			{"path": "src/a.go", "outcome": "read", "evidence_ids": []string{"E-a"}},
			{"path": "src/b.go", "outcome": "read", "evidence_ids": []string{"E-b"}},
		},
		Evidence: []map[string]any{
			{"id": "E-a", "source_path": "src/a.go"},
			{"id": "E-b", "source_path": "src/b.go"},
		},
		Nodes: []map[string]any{
			{"id": "N-a", "paths": []string{"src/a.go"}, "evidence_ids": []string{"E-a"}},
			{"id": "N-b", "paths": []string{"src/b.go"}, "evidence_ids": []string{"E-b"}},
		},
		Observations: []map[string]any{{
			"id": "O-shared", "evidence_ids": []string{"E-a", "E-b"},
		}},
		Claims: []map[string]any{{
			"id": "C-a", "node_id": "N-a", "supporting_evidence_ids": []string{"E-a"},
			"contradicting_evidence_ids": []string{"E-b"},
		}},
	}
	components, dependencies, err := cachePathComponents(normalizedSet([]string{"src/a.go", "src/b.go"}), rows)
	if err != nil {
		t.Fatal(err)
	}
	if len(components) != 1 || !sameStringSet(components[0], []string{"src/a.go", "src/b.go"}) {
		t.Fatalf("claim dependency components = %#v", components)
	}
	if !sameSet(dependencies.Claims["C-a"], normalizedSet([]string{"src/a.go", "src/b.go"})) {
		t.Fatalf("claim dependency scope = %#v", dependencies.Claims["C-a"])
	}
	filtered := filterCacheRowsForScope(rows, dependencies, normalizedSet(components[0]))
	if len(filtered.Claims) != 1 || len(filtered.Observations) != 1 || len(filtered.Evidence) != 2 || len(filtered.Nodes) != 2 {
		t.Fatalf("filtered claim bundle = %#v", filtered)
	}
}

func TestPrepareRecoversInterruptedCacheReplayOnExactResume(t *testing.T) {
	paths := newScanPaths(t, []string{"src/a.go", "src/b.go"})
	if _, err := Prepare(paths, PrepareInput{MaxPaths: 2}); err != nil {
		t.Fatal(err)
	}
	acceptAllPreparedPackets(t, paths)
	sealCacheableScan(t, paths)
	if _, err := SnapshotValidatedScanCache(paths); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(paths.Root, "src", "b.go"), []byte("package fixture\n// changed\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	if _, err := Prepare(paths, PrepareInput{MaxPaths: 2}); err != nil {
		t.Fatal(err)
	}

	queuePath := filepath.Join(paths.RuntimeDir, "workbench", "scan-queue.json")
	queue := readJSONObject(t, queuePath)
	cachePacketID := ""
	for _, packet := range objectRows(t, queue["packets"]) {
		if packet["cache_bundle_id"] == nil {
			continue
		}
		cachePacketID = packet["packet_id"].(string)
		packet["state"] = "leased"
		break
	}
	if cachePacketID == "" {
		t.Fatal("incremental preparation produced no cache replay packet")
	}
	writeJSON(t, queuePath, queue)
	for _, path := range []string{
		filepath.Join(paths.RuntimeDir, "workbench", "worker-results", cachePacketID+".json"),
		acceptanceReceiptPath(paths, cachePacketID),
		acceptanceSubmissionSnapshotPath(paths, cachePacketID),
	} {
		if err := os.Remove(path); err != nil {
			t.Fatal(err)
		}
	}

	payload, err := Prepare(paths, PrepareInput{MaxPaths: 2})
	if err != nil {
		t.Fatalf("exact resume did not recover cache replay: %v", err)
	}
	if payload.Status != "resumed" || payload.ReusedPathCount != 1 || payload.PendingPathCount != 1 {
		t.Fatalf("recovered resume payload = %#v", payload)
	}
	recovered := readJSONObject(t, queuePath)
	for _, packet := range objectRows(t, recovered["packets"]) {
		if packet["packet_id"] == cachePacketID && packet["state"] != "accepted" {
			t.Fatalf("recovered cache packet state = %v, want accepted", packet["state"])
		}
	}
	if _, err := os.Stat(acceptanceReceiptPath(paths, cachePacketID)); err != nil {
		t.Fatalf("recovered cache replay receipt: %v", err)
	}
}

func TestPrepareRejectsTamperedValidatedCacheBundle(t *testing.T) {
	paths := newScanPaths(t, []string{"src/a.go"})
	if _, err := Prepare(paths, PrepareInput{}); err != nil {
		t.Fatal(err)
	}
	acceptAllPreparedPackets(t, paths)
	sealCacheableScan(t, paths)
	if _, err := SnapshotValidatedScanCache(paths); err != nil {
		t.Fatal(err)
	}

	cachePath := scanCachePath(paths)
	cache := readJSONObject(t, cachePath)
	bundle := objectRows(t, cache["bundles"])[0]
	rows := bundle["rows"].(map[string]any)
	objectRows(t, rows["nodes"])[0]["title"] = "tampered"
	writeJSON(t, cachePath, cache)

	payload, err := Prepare(paths, PrepareInput{Force: true})
	if err != nil {
		t.Fatal(err)
	}
	if payload.ReusedPathCount != 0 || payload.PendingPathCount != 1 || payload.CacheMissReasons["cache_integrity_mismatch"] != 1 {
		t.Fatalf("tampered cache payload = %#v", payload)
	}
}

func TestPrepareDoesNotDiscardAcceptedResultsCoveredOnlyByOlderCache(t *testing.T) {
	paths := newScanPaths(t, []string{"src/a.go"})
	if _, err := Prepare(paths, PrepareInput{}); err != nil {
		t.Fatal(err)
	}
	acceptAllPreparedPackets(t, paths)
	sealCacheableScan(t, paths)
	if _, err := SnapshotValidatedScanCache(paths); err != nil {
		t.Fatal(err)
	}

	if err := os.WriteFile(filepath.Join(paths.Root, "src", "a.go"), []byte("package fixture\n// first change\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	if _, err := Prepare(paths, PrepareInput{}); err != nil {
		t.Fatal(err)
	}
	acceptAllPreparedPackets(t, paths)

	if err := os.WriteFile(filepath.Join(paths.Root, "src", "a.go"), []byte("package fixture\n// second change\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	if _, err := Prepare(paths, PrepareInput{}); err == nil || !strings.Contains(err.Error(), "not safely cached") {
		t.Fatalf("Prepare with only older cache error = %v", err)
	}
}

func TestFullRebuildExplicitlyBypassesValidatedScanCache(t *testing.T) {
	paths := newScanPaths(t, []string{"src/a.go", "src/b.go"})
	if _, err := Prepare(paths, PrepareInput{MaxPaths: 1}); err != nil {
		t.Fatal(err)
	}
	acceptAllPreparedPackets(t, paths)
	sealCacheableScan(t, paths)
	if _, err := SnapshotValidatedScanCache(paths); err != nil {
		t.Fatal(err)
	}

	payload, err := Prepare(paths, PrepareInput{MaxPaths: 1, FullRebuild: true})
	if err != nil {
		t.Fatal(err)
	}
	if payload.ReusedPathCount != 0 || payload.PendingPathCount != 2 || payload.CacheHitBundleCount != 0 || payload.CacheMissReasons["full_rebuild"] != 2 {
		t.Fatalf("full rebuild payload = %#v", payload)
	}
}

func acceptAllPreparedPackets(t *testing.T, paths rt.Paths) {
	t.Helper()
	queue := readJSONObject(t, filepath.Join(paths.RuntimeDir, "workbench", "scan-queue.json"))
	for _, packet := range objectRows(t, queue["packets"]) {
		packetID := packet["packet_id"].(string)
		assigned := stringSlice(t, packet["assigned_paths"])
		lease := mustLeasePacket(t, paths, packetID)
		resultPath := filepath.Join(t.TempDir(), packetID+".json")
		writeJSON(t, resultPath, checkpointWorkerResult(packetID, lease.AttemptID, 1, assigned, assigned))
		if _, err := Accept(paths, AcceptInput{PacketID: packetID, AttemptID: lease.AttemptID, ResultPath: resultPath}); err != nil {
			t.Fatalf("Accept %s returned error: %v", packetID, err)
		}
	}
}

func mustReadDir(t *testing.T, path string) []os.DirEntry {
	t.Helper()
	entries, err := os.ReadDir(path)
	if err != nil {
		t.Fatal(err)
	}
	return entries
}

func sealCacheableScan(t *testing.T, paths rt.Paths) {
	t.Helper()
	if result := scanartifacts.Validate(paths, scanartifacts.ValidateOptions{}); len(result.Errors) != 0 {
		t.Fatalf("scan validation errors = %#v", result.Errors)
	}
	if _, required, err := scanreceipt.Create(paths, "scan_ready"); err != nil || !required {
		t.Fatalf("create scan receipt required=%v err=%v", required, err)
	}
}
