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

	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/build"
	rt "github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/runtime"
	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/scanreceipt"
	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/validation"
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
	for _, packet := range packets {
		estimated, ok := packet["estimated_tokens"].(float64)
		if !ok || estimated <= 0 || estimated > float64(defaultEffectiveWorkerTokens) {
			t.Fatalf("default estimated_tokens = %#v, want 1..%d", packet["estimated_tokens"], defaultEffectiveWorkerTokens)
		}
	}
}

func TestPrepareSplitsPacketsByEffectiveTokenBudget(t *testing.T) {
	files := []string{"src/a.go", "src/b.go", "src/c.go", "src/d.go"}
	paths := newScanPaths(t, files)
	for _, rel := range files {
		body := "package fixture\n/*\n" + strings.Repeat("token ", 700) + "*/\n"
		if err := os.WriteFile(filepath.Join(paths.Root, filepath.FromSlash(rel)), []byte(body), 0o644); err != nil {
			t.Fatal(err)
		}
	}

	payload, err := Prepare(paths, PrepareInput{
		WorkerBudgetTokens: 2500,
		MaxPaths:           100,
	})
	if err != nil {
		t.Fatalf("Prepare returned error: %v", err)
	}
	if payload.PacketCount < 2 {
		t.Fatalf("token-budgeted packet count = %d, want at least 2", payload.PacketCount)
	}

	queue := readJSONObject(t, filepath.Join(paths.RuntimeDir, "workbench", "scan-queue.json"))
	assigned := map[string]int{}
	for _, packet := range objectRows(t, queue["packets"]) {
		estimated, ok := packet["estimated_tokens"].(float64)
		if !ok || estimated <= 0 {
			t.Fatalf("packet estimated_tokens = %#v, want positive number", packet["estimated_tokens"])
		}
		if estimated > 2500 {
			t.Fatalf("packet estimated_tokens = %.0f, exceeds effective worker budget 2500", estimated)
		}
		for _, path := range stringSlice(t, packet["assigned_paths"]) {
			assigned[path]++
		}
	}
	for _, path := range files {
		if assigned[path] != 1 {
			t.Fatalf("path %s assigned %d times, want exactly once", path, assigned[path])
		}
	}
}

func TestLeaseRequiresExplicitCapacityForOversizedPacket(t *testing.T) {
	paths := newScanPaths(t, []string{"src/huge.go"})
	body := "package fixture\n/*" + strings.Repeat("large-input ", 4000) + "*/\n"
	if err := os.WriteFile(filepath.Join(paths.Root, "src", "huge.go"), []byte(body), 0o644); err != nil {
		t.Fatal(err)
	}
	if _, err := Prepare(paths, PrepareInput{WorkerBudgetTokens: 1000, MaxPaths: 10}); err != nil {
		t.Fatal(err)
	}

	if _, err := Lease(paths, LeaseInput{WorkerID: "worker-small"}); err == nil || !strings.Contains(err.Error(), "worker capacity") {
		t.Fatalf("Lease oversized packet without capacity error = %v", err)
	}
	queue := readJSONObject(t, filepath.Join(paths.RuntimeDir, "workbench", "scan-queue.json"))
	packet := objectRows(t, queue["packets"])[0]
	estimated := int64(packet["estimated_tokens"].(float64))
	lease, err := Lease(paths, LeaseInput{WorkerID: "worker-large", WorkerCapacityTokens: estimated})
	if err != nil {
		t.Fatalf("Lease oversized packet with sufficient capacity: %v", err)
	}
	if lease.EffectiveContextBudget != estimated {
		t.Fatalf("lease effective budget = %d, want explicit capacity %d", lease.EffectiveContextBudget, estimated)
	}
}

func TestLeaseCreatesUniqueAttemptsAndNeverDoubleAssignsPacket(t *testing.T) {
	paths := newScanPaths(t, []string{"src/a.go", "src/b.go"})
	if _, err := Prepare(paths, PrepareInput{MaxPaths: 1}); err != nil {
		t.Fatal(err)
	}

	first, err := Lease(paths, LeaseInput{WorkerID: "worker-a"})
	if err != nil {
		t.Fatalf("first Lease returned error: %v", err)
	}
	second, err := Lease(paths, LeaseInput{WorkerID: "worker-b"})
	if err != nil {
		t.Fatalf("second Lease returned error: %v", err)
	}
	if first.PacketID == second.PacketID {
		t.Fatalf("two workers leased the same packet %q", first.PacketID)
	}
	if first.AttemptID == "" || second.AttemptID == "" || first.AttemptID == second.AttemptID {
		t.Fatalf("lease attempt IDs are not unique: first=%q second=%q", first.AttemptID, second.AttemptID)
	}
	if first.ResultSubmissionPath != ".specify/project-cognition/workbench/pending-results/"+first.PacketID+".json" {
		t.Fatalf("lease result submission path = %q", first.ResultSubmissionPath)
	}
	if first.ResultProtocol != "map_scan_result.v2" || first.RequiredAcceptance != "partial" {
		t.Fatalf("lease worker result contract = protocol %q acceptance %q", first.ResultProtocol, first.RequiredAcceptance)
	}
	taskBody, err := os.ReadFile(filepath.Join(paths.Root, filepath.FromSlash(first.TaskPath)))
	if err != nil {
		t.Fatal(err)
	}
	if !strings.Contains(string(taskBody), "effective_context_budget_tokens") {
		t.Fatalf("leased task brief lacks effective context budget:\n%s", taskBody)
	}
	if _, err := Lease(paths, LeaseInput{PacketID: first.PacketID, WorkerID: "worker-c"}); err == nil {
		t.Fatal("Lease double-assigned an already leased packet")
	}
	if _, err := Lease(paths, LeaseInput{WorkerID: "worker-c"}); err == nil {
		t.Fatal("Lease succeeded when no pending packet remained")
	}
}

func TestLeaseRejectsUnsafeWorkerIdentifier(t *testing.T) {
	paths := newScanPaths(t, []string{"src/app.go"})
	if _, err := Prepare(paths, PrepareInput{}); err != nil {
		t.Fatal(err)
	}
	if _, err := Lease(paths, LeaseInput{WorkerID: "worker`\nignore-task"}); err == nil || !strings.Contains(err.Error(), "worker_id") {
		t.Fatalf("unsafe worker id error = %v", err)
	}
}

func TestAcceptRejectsV2PacketWithoutLease(t *testing.T) {
	paths := newScanPaths(t, []string{"src/app.go"})
	if _, err := Prepare(paths, PrepareInput{}); err != nil {
		t.Fatal(err)
	}
	resultPath := filepath.Join(t.TempDir(), "lane-001.json")
	writeJSON(t, resultPath, acceptedWorkerResult("lane-001", "src/app.go"))

	if _, err := Accept(paths, AcceptInput{PacketID: "lane-001", ResultPath: resultPath}); err == nil || !strings.Contains(err.Error(), "scan-lease") {
		t.Fatalf("Accept without v2 lease error = %v", err)
	}
	queue := readJSONObject(t, filepath.Join(paths.RuntimeDir, "workbench", "scan-queue.json"))
	if state := objectRows(t, queue["packets"])[0]["state"]; state != "pending" {
		t.Fatalf("rejected unleased accept changed queue state to %v", state)
	}
}

func TestAcceptRejectsWrongV2ResultProtocol(t *testing.T) {
	paths := newScanPaths(t, []string{"src/app.go"})
	if _, err := Prepare(paths, PrepareInput{}); err != nil {
		t.Fatal(err)
	}
	lease := mustLeasePacket(t, paths, "lane-001")
	result := bindWorkerResultToLease(acceptedWorkerResult("lane-001", "src/app.go"), lease)
	result["protocol"] = "map_scan_result.v1"
	resultPath := filepath.Join(t.TempDir(), "lane-001.json")
	writeJSON(t, resultPath, result)

	if _, err := Accept(paths, AcceptInput{
		PacketID: "lane-001", AttemptID: lease.AttemptID, ResultPath: resultPath,
	}); err == nil || !strings.Contains(err.Error(), "map_scan_result.v2") {
		t.Fatalf("Accept wrong-protocol error = %v", err)
	}
}

func TestAcceptRejectsUnknownWorkbenchProtocolWithoutLegacyFallback(t *testing.T) {
	paths := newScanPaths(t, []string{"src/app.go"})
	if _, err := Prepare(paths, PrepareInput{}); err != nil {
		t.Fatal(err)
	}
	queuePath := filepath.Join(paths.RuntimeDir, "workbench", "scan-queue.json")
	queue := readJSONObject(t, queuePath)
	queue["protocol"] = "map_scan_workbench.v3"
	writeJSON(t, queuePath, queue)
	resultPath := filepath.Join(t.TempDir(), "lane-001.json")
	writeJSON(t, resultPath, acceptedWorkerResult("lane-001", "src/app.go"))

	if _, err := Accept(paths, AcceptInput{PacketID: "lane-001", ResultPath: resultPath}); err == nil || !strings.Contains(err.Error(), "workbench protocol") {
		t.Fatalf("Accept unknown workbench protocol error = %v", err)
	}
}

func TestAcceptRejectsCompleteV2IdentityStrippingWithoutLegacyFallback(t *testing.T) {
	paths := newScanPaths(t, []string{"src/app.go"})
	if _, err := Prepare(paths, PrepareInput{}); err != nil {
		t.Fatal(err)
	}
	writeLegacyQueue(t, paths)
	resultPath := filepath.Join(t.TempDir(), "lane-001.json")
	writeJSON(t, resultPath, acceptedWorkerResult("lane-001", "src/app.go"))

	if _, err := Accept(paths, AcceptInput{PacketID: "lane-001", ResultPath: resultPath}); err == nil || !strings.Contains(err.Error(), "v2 workbench identity") {
		t.Fatalf("Accept stripped v2 workbench identity error = %v", err)
	}
}

func TestAcceptDerivesV2AcceptanceInsteadOfTrustingWorkerPass(t *testing.T) {
	paths := newScanPaths(t, []string{"src/app.go"})
	if _, err := Prepare(paths, PrepareInput{}); err != nil {
		t.Fatal(err)
	}
	lease := mustLeasePacket(t, paths, "lane-001")
	result := bindWorkerResultToLease(acceptedWorkerResult("lane-001", "src/app.go"), lease)
	result["acceptance"] = "pass"
	resultPath := filepath.Join(t.TempDir(), "lane-001.json")
	writeJSON(t, resultPath, result)

	if _, err := Accept(paths, AcceptInput{PacketID: "lane-001", AttemptID: lease.AttemptID, ResultPath: resultPath}); err == nil || !strings.Contains(err.Error(), "worker-authored acceptance") {
		t.Fatalf("Accept worker-authored pass error = %v", err)
	}
	result["acceptance"] = "partial"
	writeJSON(t, resultPath, result)
	if _, err := Accept(paths, AcceptInput{PacketID: "lane-001", AttemptID: lease.AttemptID, ResultPath: resultPath}); err != nil {
		t.Fatalf("Accept runtime-derived result returned error: %v", err)
	}
	canonical := readJSONObject(t, filepath.Join(paths.RuntimeDir, "workbench", "worker-results", "lane-001.json"))
	if canonical["acceptance"] != "pass" {
		t.Fatalf("canonical acceptance = %v, want runtime-derived pass", canonical["acceptance"])
	}
}

func TestResumableCommandsRejectLegacyWorkbenchQueue(t *testing.T) {
	t.Run("lease", func(t *testing.T) {
		paths := newScanPaths(t, []string{"src/app.go"})
		if _, err := Prepare(paths, PrepareInput{}); err != nil {
			t.Fatal(err)
		}
		writeLegacyQueue(t, paths)

		if _, err := Lease(paths, LeaseInput{PacketID: "lane-001", WorkerID: "worker-a"}); err == nil || !strings.Contains(err.Error(), "v2 workbench") {
			t.Fatalf("Lease legacy queue error = %v", err)
		}
	})

	t.Run("status", func(t *testing.T) {
		paths := newScanPaths(t, []string{"src/app.go"})
		if _, err := Prepare(paths, PrepareInput{}); err != nil {
			t.Fatal(err)
		}
		writeLegacyQueue(t, paths)

		if _, err := Status(paths); err == nil || !strings.Contains(err.Error(), "v2 workbench") {
			t.Fatalf("Status legacy queue error = %v", err)
		}
	})
}

func writeLegacyQueue(t *testing.T, paths rt.Paths) {
	t.Helper()
	queuePath := filepath.Join(paths.RuntimeDir, "workbench", "scan-queue.json")
	queue := readJSONObject(t, queuePath)
	delete(queue, "protocol")
	delete(queue, "generation_id")
	delete(queue, "scan_set_path")
	writeJSON(t, queuePath, queue)
}

func TestCheckpointAcceptsCumulativeProgressWithoutDuplicateRows(t *testing.T) {
	assigned := []string{"src/a.go", "src/b.go", "src/c.go"}
	paths := newScanPaths(t, assigned)
	if _, err := Prepare(paths, PrepareInput{MaxPaths: len(assigned)}); err != nil {
		t.Fatal(err)
	}
	lease, err := Lease(paths, LeaseInput{PacketID: "lane-001", WorkerID: "worker-a"})
	if err != nil {
		t.Fatal(err)
	}

	checkpointDir := t.TempDir()
	firstPath := filepath.Join(checkpointDir, "checkpoint-0001.json")
	writeJSON(t, firstPath, checkpointWorkerResult("lane-001", lease.AttemptID, 1, assigned, assigned[:1]))
	if _, err := Checkpoint(paths, CheckpointInput{
		PacketID: "lane-001", AttemptID: lease.AttemptID, ResultPath: firstPath,
	}); err != nil {
		t.Fatalf("first Checkpoint returned error: %v", err)
	}

	secondPath := filepath.Join(checkpointDir, "checkpoint-0002.json")
	writeJSON(t, secondPath, checkpointWorkerResult("lane-001", lease.AttemptID, 2, assigned, assigned[:2]))
	if _, err := Checkpoint(paths, CheckpointInput{
		PacketID: "lane-001", AttemptID: lease.AttemptID, ResultPath: secondPath,
	}); err != nil {
		t.Fatalf("second cumulative Checkpoint returned error: %v", err)
	}

	coverage := objectRows(t, readJSONObject(t, filepath.Join(paths.RuntimeDir, "coverage.json"))["rows"])
	if len(coverage) != 2 {
		t.Fatalf("coverage rows after cumulative checkpoints = %d, want 2", len(coverage))
	}
	got := map[string]int{}
	for _, row := range coverage {
		got[row["path"].(string)]++
	}
	for _, path := range assigned[:2] {
		if got[path] != 1 {
			t.Fatalf("checkpointed path %s has %d canonical rows, want 1", path, got[path])
		}
	}
	mapState, err := os.ReadFile(filepath.Join(paths.RuntimeDir, "workbench", "map-state.md"))
	if err != nil {
		t.Fatal(err)
	}
	for _, want := range []string{"- packets: 1", "- accepted: 0", "- pending: 1"} {
		if !strings.Contains(string(mapState), want) {
			t.Fatalf("checkpoint corrupted human scan state; missing %q:\n%s", want, mapState)
		}
	}
}

func TestCheckpointCumulativeNodeMonotonicallyExtendsPathsAndEvidence(t *testing.T) {
	assigned := []string{"src/a.go", "src/b.go"}
	paths := newScanPaths(t, assigned)
	if _, err := Prepare(paths, PrepareInput{MaxPaths: len(assigned)}); err != nil {
		t.Fatal(err)
	}
	lease := mustLeasePacket(t, paths, "lane-001")
	checkpointDir := t.TempDir()

	firstPath := filepath.Join(checkpointDir, "checkpoint-0001.json")
	writeJSON(t, firstPath, sharedNodeCheckpointWorkerResult("lane-001", lease.AttemptID, 1, assigned, assigned[:1]))
	if _, err := Checkpoint(paths, CheckpointInput{
		PacketID: "lane-001", AttemptID: lease.AttemptID, ResultPath: firstPath,
	}); err != nil {
		t.Fatalf("first Checkpoint returned error: %v", err)
	}

	secondPath := filepath.Join(checkpointDir, "checkpoint-0002.json")
	writeJSON(t, secondPath, sharedNodeCheckpointWorkerResult("lane-001", lease.AttemptID, 2, assigned, assigned))
	if _, err := Checkpoint(paths, CheckpointInput{
		PacketID: "lane-001", AttemptID: lease.AttemptID, ResultPath: secondPath,
	}); err != nil {
		t.Fatalf("second cumulative Checkpoint returned error: %v", err)
	}

	nodes := objectRows(t, readJSONObject(t, filepath.Join(paths.RuntimeDir, "provisional", "nodes.json"))["nodes"])
	if len(nodes) != 1 {
		t.Fatalf("node count after cumulative checkpoints = %d, want 1", len(nodes))
	}
	if got := stringSlice(t, nodes[0]["paths"]); !sameStringSet(got, assigned) {
		t.Fatalf("shared node paths = %v, want %v", got, assigned)
	}
	wantEvidence := []string{"E-lane-001-1", "E-lane-001-2"}
	if got := stringSlice(t, nodes[0]["evidence_ids"]); !sameStringSet(got, wantEvidence) {
		t.Fatalf("shared node evidence_ids = %v, want %v", got, wantEvidence)
	}
}

func TestCheckpointCumulativeNodeRejectsNonMonotonicOverwrite(t *testing.T) {
	tests := []struct {
		name   string
		mutate func(*testing.T, map[string]any)
		want   string
	}{
		{
			name: "drops paths",
			mutate: func(t *testing.T, result map[string]any) {
				nodes := objectRows(t, result["nodes"])
				nodes[0]["paths"] = []string{"src/b.go"}
				nodes = append(nodes, map[string]any{
					"id": "N-lane-001-aux", "type": "file", "title": "a.go", "confidence": "high",
					"paths": []string{"src/a.go"}, "evidence_ids": []string{"E-lane-001-1"},
				})
				result["nodes"] = nodes
			},
			want: "dropped paths",
		},
		{
			name: "drops evidence ids",
			mutate: func(t *testing.T, result map[string]any) {
				objectRows(t, result["nodes"])[0]["evidence_ids"] = []string{"E-lane-001-2"}
			},
			want: "dropped evidence_ids",
		},
		{
			name: "changes immutable fields",
			mutate: func(t *testing.T, result map[string]any) {
				objectRows(t, result["nodes"])[0]["title"] = "rewritten component"
			},
			want: "changed immutable fields",
		},
	}

	for _, test := range tests {
		t.Run(test.name, func(t *testing.T) {
			assigned := []string{"src/a.go", "src/b.go"}
			paths := newScanPaths(t, assigned)
			if _, err := Prepare(paths, PrepareInput{MaxPaths: len(assigned)}); err != nil {
				t.Fatal(err)
			}
			lease := mustLeasePacket(t, paths, "lane-001")
			checkpointDir := t.TempDir()

			firstPath := filepath.Join(checkpointDir, "checkpoint-0001.json")
			writeJSON(t, firstPath, sharedNodeCheckpointWorkerResult("lane-001", lease.AttemptID, 1, assigned, assigned[:1]))
			if _, err := Checkpoint(paths, CheckpointInput{
				PacketID: "lane-001", AttemptID: lease.AttemptID, ResultPath: firstPath,
			}); err != nil {
				t.Fatalf("first Checkpoint returned error: %v", err)
			}

			second := sharedNodeCheckpointWorkerResult("lane-001", lease.AttemptID, 2, assigned, assigned)
			test.mutate(t, second)
			secondPath := filepath.Join(checkpointDir, "checkpoint-0002.json")
			writeJSON(t, secondPath, second)
			if _, err := Checkpoint(paths, CheckpointInput{
				PacketID: "lane-001", AttemptID: lease.AttemptID, ResultPath: secondPath,
			}); err == nil || !strings.Contains(err.Error(), test.want) {
				t.Fatalf("non-monotonic cumulative Checkpoint error = %v, want %q", err, test.want)
			}

			nodes := objectRows(t, readJSONObject(t, filepath.Join(paths.RuntimeDir, "provisional", "nodes.json"))["nodes"])
			if len(nodes) != 1 {
				t.Fatalf("rejected checkpoint node count = %d, want 1", len(nodes))
			}
			if got := stringSlice(t, nodes[0]["paths"]); !sameStringSet(got, assigned[:1]) {
				t.Fatalf("rejected checkpoint mutated shared node paths: %v", got)
			}
			if got := stringSlice(t, nodes[0]["evidence_ids"]); !sameStringSet(got, []string{"E-lane-001-1"}) {
				t.Fatalf("rejected checkpoint mutated shared node evidence_ids: %v", got)
			}
		})
	}
}

func TestCheckpointRetryIsIdempotentButConflictingPayloadIsRejected(t *testing.T) {
	assigned := []string{"src/a.go", "src/b.go"}
	paths := newScanPaths(t, assigned)
	if _, err := Prepare(paths, PrepareInput{MaxPaths: len(assigned)}); err != nil {
		t.Fatal(err)
	}
	lease := mustLeasePacket(t, paths, "lane-001")
	resultPath := filepath.Join(t.TempDir(), "checkpoint-0001.json")
	result := checkpointWorkerResult("lane-001", lease.AttemptID, 1, assigned, assigned[:1])
	writeJSON(t, resultPath, result)
	first, err := Checkpoint(paths, CheckpointInput{PacketID: "lane-001", AttemptID: lease.AttemptID, ResultPath: resultPath})
	if err != nil {
		t.Fatal(err)
	}
	second, err := Checkpoint(paths, CheckpointInput{PacketID: "lane-001", AttemptID: lease.AttemptID, ResultPath: resultPath})
	if err != nil {
		t.Fatalf("identical checkpoint retry returned error: %v", err)
	}
	if first != second {
		t.Fatalf("idempotent checkpoint payload changed: first=%#v second=%#v", first, second)
	}

	result["confidence"] = "low"
	writeJSON(t, resultPath, result)
	if _, err := Checkpoint(paths, CheckpointInput{PacketID: "lane-001", AttemptID: lease.AttemptID, ResultPath: resultPath}); err == nil || !strings.Contains(err.Error(), "conflict") {
		t.Fatalf("conflicting same-sequence checkpoint error = %v", err)
	}
}

func TestStatusSubtractsCheckpointedWorkAndExposesActiveLease(t *testing.T) {
	assigned := []string{"src/a.go", "src/b.go", "src/c.go"}
	paths := newScanPaths(t, assigned)
	for _, rel := range assigned {
		body := "package fixture\n/*" + strings.Repeat("content ", 500) + "*/\n"
		if err := os.WriteFile(filepath.Join(paths.Root, filepath.FromSlash(rel)), []byte(body), 0o644); err != nil {
			t.Fatal(err)
		}
	}
	if _, err := Prepare(paths, PrepareInput{MaxPaths: len(assigned), WorkerBudgetTokens: 10000}); err != nil {
		t.Fatal(err)
	}
	lease := mustLeasePacket(t, paths, "lane-001")
	before, err := Status(paths)
	if err != nil {
		t.Fatal(err)
	}
	resultPath := filepath.Join(t.TempDir(), "checkpoint-0001.json")
	writeJSON(t, resultPath, checkpointWorkerResult("lane-001", lease.AttemptID, 1, assigned, assigned[:2]))
	if _, err := Checkpoint(paths, CheckpointInput{PacketID: "lane-001", AttemptID: lease.AttemptID, ResultPath: resultPath}); err != nil {
		t.Fatal(err)
	}
	after, err := Status(paths)
	if err != nil {
		t.Fatal(err)
	}
	if after.EstimatedRemainingTokens >= before.EstimatedRemainingTokens {
		t.Fatalf("remaining tokens did not decrease after checkpoint: before=%d after=%d", before.EstimatedRemainingTokens, after.EstimatedRemainingTokens)
	}
	if len(after.ActiveLeases) != 1 || after.ActiveLeases[0].PacketID != lease.PacketID || after.ActiveLeases[0].AttemptID != lease.AttemptID || after.ActiveLeases[0].RemainingPathCount != 1 {
		t.Fatalf("active lease recovery summary = %#v", after.ActiveLeases)
	}
}

func TestYieldPreservesCompletedSubsetAndRequeuesExactRemainder(t *testing.T) {
	assigned := []string{"src/a.go", "src/b.go", "src/c.go"}
	paths := newScanPaths(t, assigned)
	if _, err := Prepare(paths, PrepareInput{MaxPaths: len(assigned)}); err != nil {
		t.Fatal(err)
	}
	lease, err := Lease(paths, LeaseInput{PacketID: "lane-001", WorkerID: "worker-a"})
	if err != nil {
		t.Fatal(err)
	}
	resultPath := filepath.Join(t.TempDir(), "checkpoint-0001.json")
	writeJSON(t, resultPath, checkpointWorkerResult("lane-001", lease.AttemptID, 1, assigned, assigned[:2]))
	if _, err := Checkpoint(paths, CheckpointInput{
		PacketID: "lane-001", AttemptID: lease.AttemptID, ResultPath: resultPath,
	}); err != nil {
		t.Fatal(err)
	}
	if _, err := Yield(paths, YieldInput{PacketID: "lane-001", AttemptID: lease.AttemptID}); err != nil {
		t.Fatalf("Yield returned error: %v", err)
	}

	queue := readJSONObject(t, filepath.Join(paths.RuntimeDir, "workbench", "scan-queue.json"))
	acceptedPaths := []string{}
	pendingPaths := []string{}
	for _, packet := range objectRows(t, queue["packets"]) {
		switch packet["state"] {
		case "accepted":
			acceptedPaths = append(acceptedPaths, stringSlice(t, packet["assigned_paths"])...)
		case "pending":
			pendingPaths = append(pendingPaths, stringSlice(t, packet["assigned_paths"])...)
		}
	}
	if !sameStringSet(acceptedPaths, assigned[:2]) {
		t.Fatalf("accepted paths after yield = %v, want %v", acceptedPaths, assigned[:2])
	}
	if !sameStringSet(pendingPaths, assigned[2:]) {
		t.Fatalf("pending paths after yield = %v, want %v", pendingPaths, assigned[2:])
	}
	coverage := objectRows(t, readJSONObject(t, filepath.Join(paths.RuntimeDir, "coverage.json"))["rows"])
	if len(coverage) != 2 {
		t.Fatalf("yield discarded checkpointed coverage: got %d rows, want 2", len(coverage))
	}

	next, err := Lease(paths, LeaseInput{WorkerID: "worker-b"})
	if err != nil {
		t.Fatalf("Lease of yielded remainder returned error: %v", err)
	}
	if next.AttemptID == lease.AttemptID {
		t.Fatalf("requeued remainder reused stale attempt %q", next.AttemptID)
	}
}

func TestYieldFullyCheckpointedPacketCreatesValidAcceptanceReceipt(t *testing.T) {
	assigned := []string{"src/app.go"}
	paths := newScanPaths(t, assigned)
	if _, err := Prepare(paths, PrepareInput{}); err != nil {
		t.Fatal(err)
	}
	lease := mustLeasePacket(t, paths, "lane-001")
	resultPath := filepath.Join(t.TempDir(), "checkpoint-0001.json")
	writeJSON(t, resultPath, checkpointWorkerResult(
		"lane-001",
		lease.AttemptID,
		1,
		assigned,
		assigned,
	))
	if _, err := Checkpoint(paths, CheckpointInput{
		PacketID: "lane-001", AttemptID: lease.AttemptID, ResultPath: resultPath,
	}); err != nil {
		t.Fatal(err)
	}
	if _, err := Yield(paths, YieldInput{
		PacketID: "lane-001", AttemptID: lease.AttemptID,
	}); err != nil {
		t.Fatal(err)
	}

	receipt := readJSONObject(t, acceptanceReceiptPath(paths, "lane-001"))
	if receipt["protocol"] != acceptanceReceiptProtocolV1 ||
		receipt["attempt_id"] != lease.AttemptID ||
		receipt["submission_path"] != canonicalAcceptedSubmissionPath("lane-001") {
		t.Fatalf("yield acceptance receipt = %#v", receipt)
	}
	if gate := validation.ValidateScan(paths); gate.Status != "ok" {
		t.Fatalf("validate-scan after fully checkpointed yield = %#v", gate)
	}
}

func TestYieldKeepsExactRemainderFromCustomByteBudget(t *testing.T) {
	assigned := []string{"src/a.go", "src/b.go", "src/c.go"}
	paths := newScanPaths(t, assigned)
	content := []byte(strings.Repeat("x", int(defaultPacketBytes/2)+128))
	for _, rel := range assigned {
		if err := os.WriteFile(filepath.Join(paths.Root, filepath.FromSlash(rel)), content, 0o644); err != nil {
			t.Fatal(err)
		}
	}
	if _, err := Prepare(paths, PrepareInput{
		MaxPaths:           len(assigned),
		MaxBytes:           defaultPacketBytes * 2,
		WorkerBudgetTokens: 2_000_000,
	}); err != nil {
		t.Fatal(err)
	}
	lease := mustLeasePacket(t, paths, "lane-001")
	resultPath := filepath.Join(t.TempDir(), "checkpoint-0001.json")
	writeJSON(t, resultPath, checkpointWorkerResult("lane-001", lease.AttemptID, 1, assigned, assigned[:1]))
	if _, err := Checkpoint(paths, CheckpointInput{
		PacketID: "lane-001", AttemptID: lease.AttemptID, ResultPath: resultPath,
	}); err != nil {
		t.Fatal(err)
	}

	payload, err := Yield(paths, YieldInput{PacketID: "lane-001", AttemptID: lease.AttemptID})
	if err != nil {
		t.Fatalf("Yield with custom byte budget returned error: %v", err)
	}
	queue := readJSONObject(t, filepath.Join(paths.RuntimeDir, "workbench", "scan-queue.json"))
	var remainder []string
	for _, packet := range objectRows(t, queue["packets"]) {
		if packet["packet_id"] == payload.RemainderPacketID {
			remainder = stringSlice(t, packet["assigned_paths"])
		}
	}
	if !sameStringSet(remainder, assigned[1:]) {
		t.Fatalf("yielded remainder = %v, want exact remainder %v", remainder, assigned[1:])
	}
}

func TestYieldRetryAfterHandoffFailureKeepsExactPartition(t *testing.T) {
	assigned := []string{"src/a.go", "src/b.go", "src/c.go"}
	paths := newScanPaths(t, assigned)
	if _, err := Prepare(paths, PrepareInput{MaxPaths: len(assigned)}); err != nil {
		t.Fatal(err)
	}
	lease := mustLeasePacket(t, paths, "lane-001")
	resultPath := filepath.Join(t.TempDir(), "checkpoint-0001.json")
	writeJSON(t, resultPath, checkpointWorkerResult("lane-001", lease.AttemptID, 1, assigned, assigned[:2]))
	if _, err := Checkpoint(paths, CheckpointInput{PacketID: "lane-001", AttemptID: lease.AttemptID, ResultPath: resultPath}); err != nil {
		t.Fatal(err)
	}

	handoffPath := filepath.Join(paths.RuntimeDir, "workbench", "handoff-ledger.json")
	backupPath := filepath.Join(paths.RuntimeDir, "workbench", "handoff-ledger.backup")
	if err := os.Rename(handoffPath, backupPath); err != nil {
		t.Fatal(err)
	}
	if err := os.Mkdir(handoffPath, 0o755); err != nil {
		t.Fatal(err)
	}
	if _, err := Yield(paths, YieldInput{PacketID: "lane-001", AttemptID: lease.AttemptID}); err == nil {
		t.Fatal("Yield unexpectedly succeeded with unwritable handoff ledger")
	}
	if err := os.Remove(handoffPath); err != nil {
		t.Fatal(err)
	}
	if err := os.Rename(backupPath, handoffPath); err != nil {
		t.Fatal(err)
	}
	if _, err := Yield(paths, YieldInput{PacketID: "lane-001", AttemptID: lease.AttemptID}); err != nil {
		t.Fatalf("retry Yield returned error: %v", err)
	}

	queue := readJSONObject(t, filepath.Join(paths.RuntimeDir, "workbench", "scan-queue.json"))
	accepted, pending := []string{}, []string{}
	for _, packet := range objectRows(t, queue["packets"]) {
		switch packet["state"] {
		case "accepted":
			accepted = append(accepted, stringSlice(t, packet["assigned_paths"])...)
		case "pending":
			pending = append(pending, stringSlice(t, packet["assigned_paths"])...)
		}
	}
	if !sameStringSet(accepted, assigned[:2]) || !sameStringSet(pending, assigned[2:]) {
		t.Fatalf("yield retry partition accepted=%v pending=%v, want %v / %v", accepted, pending, assigned[:2], assigned[2:])
	}
}

func TestForcePrepareCreatesNewAttemptGenerationAndRejectsLateResult(t *testing.T) {
	paths := newScanPaths(t, []string{"src/app.go"})
	if _, err := Prepare(paths, PrepareInput{}); err != nil {
		t.Fatal(err)
	}
	first := mustLeasePacket(t, paths, "lane-001")
	lateResultPath := filepath.Join(t.TempDir(), "late-result.json")
	writeJSON(t, lateResultPath, bindWorkerResultToLease(acceptedWorkerResult("lane-001", "src/app.go"), first))

	if _, err := Prepare(paths, PrepareInput{Force: true}); err != nil {
		t.Fatal(err)
	}
	second := mustLeasePacket(t, paths, "lane-001")
	if second.AttemptID == first.AttemptID {
		t.Fatalf("force prepare reused attempt id %q", first.AttemptID)
	}
	if _, err := Accept(paths, AcceptInput{PacketID: second.PacketID, AttemptID: second.AttemptID, ResultPath: lateResultPath}); err == nil || !strings.Contains(err.Error(), "attempt_id") {
		t.Fatalf("late prior-generation result error = %v", err)
	}
}

func TestCheckpointAndAcceptRejectUntrustedCompletionClaims(t *testing.T) {
	t.Run("path outside assignment", func(t *testing.T) {
		assigned := []string{"src/a.go", "src/b.go"}
		paths := newScanPaths(t, assigned)
		if _, err := Prepare(paths, PrepareInput{MaxPaths: len(assigned)}); err != nil {
			t.Fatal(err)
		}
		lease, err := Lease(paths, LeaseInput{WorkerID: "worker-a"})
		if err != nil {
			t.Fatal(err)
		}
		resultPath := filepath.Join(t.TempDir(), "outside.json")
		writeJSON(t, resultPath, checkpointWorkerResult(lease.PacketID, lease.AttemptID, 1, assigned, []string{"src/outside.go"}))
		if _, err := Checkpoint(paths, CheckpointInput{
			PacketID: lease.PacketID, AttemptID: lease.AttemptID, ResultPath: resultPath,
		}); err == nil {
			t.Fatal("Checkpoint accepted a path outside the leased assignment")
		}
		if got := len(objectRows(t, readJSONObject(t, filepath.Join(paths.RuntimeDir, "coverage.json"))["rows"])); got != 0 {
			t.Fatalf("rejected checkpoint mutated canonical coverage: %d rows", got)
		}
	})

	t.Run("omitted paths cannot finalize packet", func(t *testing.T) {
		assigned := []string{"src/a.go", "src/b.go"}
		paths := newScanPaths(t, assigned)
		if _, err := Prepare(paths, PrepareInput{MaxPaths: len(assigned)}); err != nil {
			t.Fatal(err)
		}
		lease, err := Lease(paths, LeaseInput{WorkerID: "worker-a"})
		if err != nil {
			t.Fatal(err)
		}
		resultPath := filepath.Join(t.TempDir(), "partial.json")
		writeJSON(t, resultPath, checkpointWorkerResult(lease.PacketID, lease.AttemptID, 1, assigned, assigned[:1]))
		if _, err := Checkpoint(paths, CheckpointInput{
			PacketID: lease.PacketID, AttemptID: lease.AttemptID, ResultPath: resultPath,
		}); err != nil {
			t.Fatal(err)
		}
		if _, err := Accept(paths, AcceptInput{PacketID: lease.PacketID, AttemptID: lease.AttemptID}); err == nil {
			t.Fatal("Accept finalized a packet with an omitted assigned path")
		}
	})

	t.Run("stale attempt", func(t *testing.T) {
		paths := newScanPaths(t, []string{"src/a.go"})
		if _, err := Prepare(paths, PrepareInput{MaxPaths: 1}); err != nil {
			t.Fatal(err)
		}
		first, err := Lease(paths, LeaseInput{WorkerID: "worker-a"})
		if err != nil {
			t.Fatal(err)
		}
		if _, err := Yield(paths, YieldInput{PacketID: first.PacketID, AttemptID: first.AttemptID}); err != nil {
			t.Fatal(err)
		}
		second, err := Lease(paths, LeaseInput{WorkerID: "worker-b"})
		if err != nil {
			t.Fatal(err)
		}
		resultPath := filepath.Join(t.TempDir(), "stale.json")
		writeJSON(t, resultPath, checkpointWorkerResult(second.PacketID, first.AttemptID, 1, []string{"src/a.go"}, []string{"src/a.go"}))
		if _, err := Checkpoint(paths, CheckpointInput{
			PacketID: second.PacketID, AttemptID: first.AttemptID, ResultPath: resultPath,
		}); err == nil {
			t.Fatal("Checkpoint accepted a stale attempt")
		}
	})

	t.Run("wrong protocol", func(t *testing.T) {
		paths := newScanPaths(t, []string{"src/a.go"})
		if _, err := Prepare(paths, PrepareInput{MaxPaths: 1}); err != nil {
			t.Fatal(err)
		}
		lease, err := Lease(paths, LeaseInput{WorkerID: "worker-a"})
		if err != nil {
			t.Fatal(err)
		}
		result := checkpointWorkerResult(lease.PacketID, lease.AttemptID, 1, []string{"src/a.go"}, []string{"src/a.go"})
		result["protocol"] = "map_scan_result.v1"
		resultPath := filepath.Join(t.TempDir(), "wrong-protocol.json")
		writeJSON(t, resultPath, result)
		if _, err := Checkpoint(paths, CheckpointInput{
			PacketID: lease.PacketID, AttemptID: lease.AttemptID, ResultPath: resultPath,
		}); err == nil || !strings.Contains(err.Error(), "map_scan_result.v2") {
			t.Fatalf("Checkpoint wrong-protocol error = %v", err)
		}
	})
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
	if universe["schema_version"] != float64(2) {
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
	pending := readJSONObject(t, filepath.Join(paths.RuntimeDir, "workbench", "pending-results", "lane-001.json"))
	if pending["protocol"] != "map_scan_result.v2" || pending["acceptance"] != "partial" {
		t.Fatalf("generated result skeleton = %#v", pending)
	}
	if got := stringSlice(t, pending["assigned_paths"]); !equalStrings(got, []string{"README.md", "src/a.go"}) {
		t.Fatalf("generated result skeleton assigned_paths = %v", got)
	}
}

func TestPrepareClassifiesRepresentativePathsByValueAndDisposition(t *testing.T) {
	files := []string{
		"cmd/server/main.go",
		"internal/auth/service.go",
		"internal/build/build.go",
		"go.mod",
		"tests/math/service_test.go",
		"tests/auth/policy_integration_test.go",
		"docs/usage.md",
		"dist/app.bundle.js",
	}
	paths := newScanPaths(t, files)

	if _, err := Prepare(paths, PrepareInput{PacketSize: len(files)}); err != nil {
		t.Fatalf("Prepare returned error: %v", err)
	}

	universe := readJSONObject(t, filepath.Join(paths.RuntimeDir, "workbench", "repository-universe.json"))
	rowsByPath := rowsByPath(t, universe["candidate_universe"])

	tests := []struct {
		path         string
		valueTier    string
		disposition  string
		scanDecision string
	}{
		{"cmd/server/main.go", "P0", "deep_read", "scan"},
		{"internal/auth/service.go", "P0", "deep_read", "scan"},
		{"internal/build/build.go", "P1", "deep_read", "scan"},
		{"go.mod", "P1", "deep_read", "scan"},
		{"tests/math/service_test.go", "P2", "sampled", "sample"},
		{"tests/auth/policy_integration_test.go", "P1", "deep_read", "scan"},
		{"docs/usage.md", "P2", "sampled", "sample"},
		{"dist/app.bundle.js", "P3", "inventory_only", "inventory_only"},
	}

	for _, tt := range tests {
		t.Run(tt.path, func(t *testing.T) {
			row, ok := rowsByPath[tt.path]
			if !ok {
				t.Fatalf("candidate_universe lacks path %q", tt.path)
			}
			if row["value_tier"] != tt.valueTier {
				t.Fatalf("%s value_tier = %v, want %s", tt.path, row["value_tier"], tt.valueTier)
			}
			if row["disposition"] != tt.disposition {
				t.Fatalf("%s disposition = %v, want %s", tt.path, row["disposition"], tt.disposition)
			}
			if row["scan_decision"] != tt.scanDecision {
				t.Fatalf("%s scan_decision = %v, want %s", tt.path, row["scan_decision"], tt.scanDecision)
			}
		})
	}
}

func TestPrepareDoesNotResetWorkbenchWhenClassificationHasNoDispatchTargets(t *testing.T) {
	paths := newScanPaths(t, []string{"dist/app.bundle.js"})
	sentinelPath := filepath.Join(paths.RuntimeDir, "workbench", "sentinel.txt")
	if err := os.MkdirAll(filepath.Dir(sentinelPath), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(sentinelPath, []byte("preserve"), 0o644); err != nil {
		t.Fatal(err)
	}

	_, err := Prepare(paths, PrepareInput{PacketSize: 25, Force: true})
	if err == nil || !strings.Contains(err.Error(), "no scan-eligible files") {
		t.Fatalf("Prepare error = %v, want no scan-eligible files", err)
	}
	if got, readErr := os.ReadFile(sentinelPath); readErr != nil || string(got) != "preserve" {
		t.Fatalf("classification failure reset existing workbench: content=%q err=%v", got, readErr)
	}
}

func TestPrepareWritesConsistentRepositoryUniverseAndScanTargetsMaps(t *testing.T) {
	files := []string{
		"cmd/server/main.go",
		"go.mod",
		"tests/math/service_test.go",
		"dist/app.bundle.js",
	}
	paths := newScanPaths(t, files)

	if _, err := Prepare(paths, PrepareInput{PacketSize: len(files)}); err != nil {
		t.Fatalf("Prepare returned error: %v", err)
	}

	universe := readJSONObject(t, filepath.Join(paths.RuntimeDir, "workbench", "repository-universe.json"))
	targets := readJSONObject(t, filepath.Join(paths.RuntimeDir, "workbench", "scan-targets.json"))
	for _, key := range []string{"schema_version", "selection_policy"} {
		if _, ok := targets[key]; !ok {
			t.Fatalf("scan-targets.json lacks %s", key)
		}
	}
	if targets["selection_policy"] != "value_weighted" {
		t.Fatalf("scan-targets selection_policy = %v, want value_weighted", targets["selection_policy"])
	}

	universeRows := rowsByPath(t, universe["candidate_universe"])
	targetValueTiers := stringMap(t, targets["value_tier"])
	targetDecisions := stringMap(t, targets["scan_decision"])
	targetDispositions := stringMap(t, targets["disposition"])
	targetCriticality := stringMap(t, targets["criticality"])
	targetReasons := stringMap(t, targets["classification_reasons"])
	selectedPaths := stringSlice(t, targets["selected_paths"])
	queue := readJSONObject(t, filepath.Join(paths.RuntimeDir, "workbench", "scan-queue.json"))
	queuePaths := []string{}
	for _, packet := range objectRows(t, queue["packets"]) {
		queuePaths = append(queuePaths, stringSlice(t, packet["assigned_paths"])...)
	}
	if !sameStringSet(selectedPaths, queuePaths) {
		t.Fatalf("scan queue paths = %v, want selected_paths %v", queuePaths, selectedPaths)
	}
	if containsString(selectedPaths, "dist/app.bundle.js") {
		t.Fatal("P3 inventory-only path must not be dispatched in selected_paths")
	}

	for _, path := range stringSlice(t, universe["included_paths"]) {
		row, ok := universeRows[path]
		if !ok {
			t.Fatalf("included path %s lacks candidate_universe row", path)
		}
		for _, key := range []string{"extension", "size_bytes", "directory_family", "decision_source"} {
			if _, ok := row[key]; !ok {
				t.Fatalf("candidate_universe row %s lacks documented metadata %s", path, key)
			}
		}
		if targetValueTiers[path] != row["value_tier"] {
			t.Fatalf("scan-targets value_tier[%s] = %q, want %v", path, targetValueTiers[path], row["value_tier"])
		}
		if targetDecisions[path] != row["scan_decision"] {
			t.Fatalf("scan-targets scan_decision[%s] = %q, want %v", path, targetDecisions[path], row["scan_decision"])
		}
		if targetDispositions[path] != row["disposition"] {
			t.Fatalf("scan-targets disposition[%s] = %q, want %v", path, targetDispositions[path], row["disposition"])
		}
		if targetCriticality[path] != row["criticality"] {
			t.Fatalf("scan-targets criticality[%s] = %q, want %v", path, targetCriticality[path], row["criticality"])
		}
		if targetReasons[path] == "" {
			t.Fatalf("scan-targets classification_reasons[%s] is empty", path)
		}
	}
}

func containsString(values []string, want string) bool {
	for _, value := range values {
		if value == want {
			return true
		}
	}
	return false
}

func TestAcceptMergesPacketAndProducesBuildableScanPackage(t *testing.T) {
	paths := newScanPaths(t, []string{"src/app.go", "dist/app.bundle.js"})
	if _, err := Prepare(paths, PrepareInput{PacketSize: 25}); err != nil {
		t.Fatal(err)
	}
	lease := mustLeasePacket(t, paths, "lane-001")
	resultPath := filepath.Join(t.TempDir(), "lane-001.json")
	writeJSON(t, resultPath, bindWorkerResultToLease(acceptedWorkerResult("lane-001", "src/app.go"), lease))

	payload, err := Accept(paths, AcceptInput{PacketID: "lane-001", AttemptID: lease.AttemptID, ResultPath: resultPath})
	if err != nil {
		t.Fatalf("Accept returned error: %v", err)
	}
	if payload.Status != "accepted" || payload.PacketID != "lane-001" || payload.AcceptedPathCount != 1 {
		t.Fatalf("unexpected accept payload: %#v", payload)
	}
	if payload.CompletionAllowed || payload.CompletionGate != "validate_scan" {
		t.Fatalf("accept completion gate = allowed %t gate %q", payload.CompletionAllowed, payload.CompletionGate)
	}
	status, err := Status(paths)
	if err != nil {
		t.Fatalf("Status returned error: %v", err)
	}
	if status.StageState != "validation_required" || status.CompletionAllowed || status.CompletionGate != "validate_scan" {
		t.Fatalf("scan status completion gate = %#v", status)
	}
	receipt := readJSONObject(t, filepath.Join(paths.RuntimeDir, "workbench", "acceptance-receipts", "lane-001.json"))
	if receipt["protocol"] != acceptanceReceiptProtocolV1 ||
		receipt["workbench_generation_id"] == "" ||
		receipt["attempt_id"] != lease.AttemptID ||
		receipt["submission_path"] != canonicalAcceptedSubmissionPath("lane-001") ||
		receipt["canonical_result_path"] != canonicalWorkerResultPath("lane-001") {
		t.Fatalf("runtime acceptance receipt = %#v", receipt)
	}

	gate := validation.ValidateScan(paths)
	if gate.Status != "ok" || gate.Readiness != "scan_ready" {
		t.Fatalf("validate-scan = %#v", gate)
	}
	if _, _, err := scanreceipt.Create(paths, gate.Readiness); err != nil {
		t.Fatalf("create scan receipt: %v", err)
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
	coverage := readJSONObject(t, filepath.Join(paths.RuntimeDir, "coverage.json"))
	if got := objectRows(t, coverage["rows"]); len(got) != 1 || got[0]["path"] != "src/app.go" {
		t.Fatalf("inventory-only path leaked into worker coverage: %#v", got)
	}
}

func TestValidateScanRejectsTamperedAcceptedSubmissionSnapshot(t *testing.T) {
	paths := newScanPaths(t, []string{"src/app.go"})
	if _, err := Prepare(paths, PrepareInput{}); err != nil {
		t.Fatal(err)
	}
	lease := mustLeasePacket(t, paths, "lane-001")
	resultPath := filepath.Join(t.TempDir(), "lane-001.json")
	writeJSON(t, resultPath, bindWorkerResultToLease(
		acceptedWorkerResult("lane-001", "src/app.go"),
		lease,
	))
	if _, err := Accept(paths, AcceptInput{
		PacketID: "lane-001", AttemptID: lease.AttemptID, ResultPath: resultPath,
	}); err != nil {
		t.Fatal(err)
	}
	snapshotPath := acceptanceSubmissionSnapshotPath(paths, "lane-001")
	snapshot := readJSONObject(t, snapshotPath)
	snapshot["tampered"] = true
	writeJSON(t, snapshotPath, snapshot)

	gate := validation.ValidateScan(paths)

	if gate.Status != "blocked" || gate.CompletionAllowed || gate.BypassAllowed {
		t.Fatalf("tampered acceptance snapshot gate = %#v, want blocked", gate)
	}
	if !containsError(
		gate.Errors,
		"acceptance receipt for packet lane-001 submission digest does not match .specify/project-cognition/workbench/accepted-submissions/lane-001.json",
	) {
		t.Fatalf("validate-scan errors = %#v, want submission digest mismatch", gate.Errors)
	}
}

func TestValidateScanRejectsTamperedScanTargetProjection(t *testing.T) {
	paths := newScanPaths(t, []string{"src/app.go"})
	if _, err := Prepare(paths, PrepareInput{PacketSize: 25}); err != nil {
		t.Fatal(err)
	}
	lease := mustLeasePacket(t, paths, "lane-001")
	resultPath := filepath.Join(t.TempDir(), "lane-001.json")
	writeJSON(t, resultPath, bindWorkerResultToLease(acceptedWorkerResult("lane-001", "src/app.go"), lease))
	if _, err := Accept(paths, AcceptInput{PacketID: "lane-001", AttemptID: lease.AttemptID, ResultPath: resultPath}); err != nil {
		t.Fatal(err)
	}

	targetPath := filepath.Join(paths.RuntimeDir, "workbench", "scan-targets.json")
	targets := readJSONObject(t, targetPath)
	decisions := targets["scan_decision"].(map[string]any)
	decisions["src/app.go"] = "inventory_only"
	writeJSON(t, targetPath, targets)

	gate := validation.ValidateScan(paths)
	if gate.Status != "blocked" || !containsError(gate.Errors, "scan-targets path src/app.go scan_decision conflicts with repository-universe") {
		t.Fatalf("tampered scan-target projection was not rejected: %#v", gate)
	}
}

func TestValidateScanRejectsMismatchedScanTargetSchema(t *testing.T) {
	paths := newScanPaths(t, []string{"src/app.go"})
	if _, err := Prepare(paths, PrepareInput{PacketSize: 25}); err != nil {
		t.Fatal(err)
	}

	targetPath := filepath.Join(paths.RuntimeDir, "workbench", "scan-targets.json")
	targets := readJSONObject(t, targetPath)
	targets["schema_version"] = 1
	writeJSON(t, targetPath, targets)

	gate := validation.ValidateScan(paths)
	if gate.Status != "blocked" || !containsError(gate.Errors, "scan-targets schema_version 1 must match repository-universe schema_version 2") {
		t.Fatalf("mismatched scan-target schema was not rejected: %#v", gate)
	}
}

func TestAcceptRejectsCrossPacketPathsWithoutMerging(t *testing.T) {
	paths := newScanPaths(t, []string{"src/a.go", "src/b.go"})
	if _, err := Prepare(paths, PrepareInput{PacketSize: 1}); err != nil {
		t.Fatal(err)
	}
	lease := mustLeasePacket(t, paths, "lane-001")
	result := bindWorkerResultToLease(acceptedWorkerResult("lane-001", "src/a.go"), lease)
	evidence := objectRows(t, result["evidence"])
	evidence[0]["source_path"] = "src/b.go"
	resultPath := filepath.Join(t.TempDir(), "lane-001.json")
	writeJSON(t, resultPath, result)

	if _, err := Accept(paths, AcceptInput{PacketID: "lane-001", AttemptID: lease.AttemptID, ResultPath: resultPath}); err == nil {
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
	if state := objectRows(t, queue["packets"])[0]["state"]; state != "leased" {
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
		lease := mustLeasePacket(t, paths, item.packetID)
		resultPath := filepath.Join(t.TempDir(), item.packetID+".json")
		writeJSON(t, resultPath, bindWorkerResultToLease(acceptedWorkerResult(item.packetID, item.path), lease))
		if _, err := Accept(paths, AcceptInput{PacketID: item.packetID, AttemptID: lease.AttemptID, ResultPath: resultPath}); err != nil {
			t.Fatal(err)
		}
	}

	handoffs := readJSONObject(t, filepath.Join(paths.RuntimeDir, "workbench", "handoff-ledger.json"))
	events := objectRows(t, handoffs["events"])
	got := make([]string, 0, len(events))
	for _, event := range events {
		got = append(got, event["event_id"].(string))
	}
	queue := readJSONObject(t, filepath.Join(paths.RuntimeDir, "workbench", "scan-queue.json"))
	generationID := queue["generation_id"].(string)
	want := []string{
		"dispatch-lane-001", "dispatch-lane-002",
		"lease-" + generationID + "-lane-001-attempt-001", "lease-" + generationID + "-lane-002-attempt-001",
		"return-lane-001", "return-lane-002",
	}
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
	attempts := map[string]string{}
	for _, item := range []struct {
		packetID string
		path     string
	}{{"lane-001", "src/a.go"}, {"lane-002", "src/b.go"}} {
		lease := mustLeasePacket(t, paths, item.packetID)
		attempts[item.packetID] = lease.AttemptID
		writeJSON(t, filepath.Join(resultDir, item.packetID+".json"), bindWorkerResultToLease(acceptedWorkerResult(item.packetID, item.path), lease))
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
				AttemptID:  attempts[packetID],
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
	lease := mustLeasePacket(t, paths, "lane-001")
	resultPath := filepath.Join(t.TempDir(), "lane-001.json")
	writeJSON(t, resultPath, bindWorkerResultToLease(acceptedWorkerResult("lane-001", "src/app.go"), lease))

	release, err := acquireWorkbenchLock(paths)
	if err != nil {
		t.Fatal(err)
	}
	done := make(chan error, 1)
	go func() {
		_, err := Accept(paths, AcceptInput{PacketID: "lane-001", AttemptID: lease.AttemptID, ResultPath: resultPath})
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
	firstLease := mustLeasePacket(t, paths, "lane-001")
	secondLease := mustLeasePacket(t, paths, "lane-002")
	first := bindWorkerResultToLease(acceptedWorkerResult("lane-001", "src/a.go"), firstLease)
	first["edges"] = []map[string]any{{
		"id": "EDGE-a-imports-b", "type": "imports",
		"source_id": "N-lane-001", "target_id": "src/b.go",
		"confidence": "high", "evidence_ids": []string{"E-lane-001"},
	}}
	resultDir := t.TempDir()
	writeJSON(t, filepath.Join(resultDir, "lane-001.json"), first)
	writeJSON(t, filepath.Join(resultDir, "lane-002.json"), bindWorkerResultToLease(acceptedWorkerResult("lane-002", "src/b.go"), secondLease))
	for _, lease := range []LeasePayload{firstLease, secondLease} {
		if _, err := Accept(paths, AcceptInput{PacketID: lease.PacketID, AttemptID: lease.AttemptID, ResultPath: filepath.Join(resultDir, lease.PacketID+".json")}); err != nil {
			t.Fatalf("Accept %s returned error: %v", lease.PacketID, err)
		}
	}

	if gate := validation.ValidateScan(paths); gate.Status != "ok" {
		t.Fatalf("cross-packet validate-scan = %#v", gate)
	} else if _, _, err := scanreceipt.Create(paths, gate.Readiness); err != nil {
		t.Fatalf("create cross-packet scan receipt: %v", err)
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

func TestPrepareRejectsAliasesForTheSameRepositoryFile(t *testing.T) {
	paths := newScanPaths(t, []string{"src/app.go"})
	writeJSON(t, filepath.Join(paths.RuntimeDir, "tmp", "scan-files.json"), map[string]any{
		"files": []string{"src/app.go", "./src/app.go"},
	})
	if _, err := Prepare(paths, PrepareInput{}); err == nil || !strings.Contains(err.Error(), "canonical") {
		t.Fatalf("Prepare alias-path error = %v", err)
	}
}

func TestPrepareRejectsTaskBriefMarkdownControlCharacters(t *testing.T) {
	paths := newScanPaths(t, []string{"src/bad`task.go"})
	if _, err := Prepare(paths, PrepareInput{}); err == nil || !strings.Contains(err.Error(), "task brief") {
		t.Fatalf("Prepare markdown-control path error = %v", err)
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

func TestLeaseRejectsSymlinkedNestedControlDirectory(t *testing.T) {
	paths := newScanPaths(t, []string{"src/app.go"})
	if _, err := Prepare(paths, PrepareInput{}); err != nil {
		t.Fatal(err)
	}
	pendingResults := filepath.Join(paths.RuntimeDir, "workbench", "pending-results")
	if err := os.Remove(filepath.Join(pendingResults, "lane-001.json")); err != nil {
		t.Fatal(err)
	}
	if err := os.Remove(pendingResults); err != nil {
		t.Fatal(err)
	}
	external := t.TempDir()
	if err := os.Symlink(external, pendingResults); err != nil {
		t.Skipf("symbolic links are unavailable: %v", err)
	}

	if _, err := Lease(paths, LeaseInput{WorkerID: "worker-a"}); err == nil || !strings.Contains(err.Error(), "symbolic links") {
		t.Fatalf("Lease with nested control symlink error = %v", err)
	}
	entries, err := os.ReadDir(external)
	if err != nil {
		t.Fatal(err)
	}
	if len(entries) != 0 {
		t.Fatalf("Lease wrote outside repository through nested symlink: %v", entries)
	}
}

func TestPrepareRequiresForceBeforeReplacingAcceptedWorkbench(t *testing.T) {
	paths := newScanPaths(t, []string{"src/app.go"})
	if _, err := Prepare(paths, PrepareInput{}); err != nil {
		t.Fatal(err)
	}
	lease := mustLeasePacket(t, paths, "lane-001")
	resultPath := filepath.Join(t.TempDir(), "lane-001.json")
	writeJSON(t, resultPath, bindWorkerResultToLease(acceptedWorkerResult("lane-001", "src/app.go"), lease))
	if _, err := Accept(paths, AcceptInput{PacketID: "lane-001", AttemptID: lease.AttemptID, ResultPath: resultPath}); err != nil {
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
	lease := mustLeasePacket(t, paths, "lane-001")
	result := bindWorkerResultToLease(acceptedWorkerResult("lane-001", "src/app.go"), lease)
	writeJSON(t, filepath.Join(paths.RuntimeDir, "evidence", "lane-001.json"), map[string]any{"rows": result["evidence"]})
	writeJSON(t, filepath.Join(paths.RuntimeDir, "provisional", "nodes.json"), map[string]any{"nodes": result["nodes"]})
	writeJSON(t, filepath.Join(paths.RuntimeDir, "coverage.json"), map[string]any{"rows": result["coverage"]})
	resultPath := filepath.Join(t.TempDir(), "lane-001.json")
	writeJSON(t, resultPath, result)

	if _, err := Accept(paths, AcceptInput{PacketID: "lane-001", AttemptID: lease.AttemptID, ResultPath: resultPath}); err != nil {
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
	lease := mustLeasePacket(t, paths, "lane-001")
	result := bindWorkerResultToLease(acceptedWorkerResult("lane-001", "src/app.go"), lease)
	conflict := cloneTestObject(objectRows(t, result["nodes"])[0])
	conflict["title"] = "different content"
	writeJSON(t, filepath.Join(paths.RuntimeDir, "provisional", "nodes.json"), map[string]any{"nodes": []map[string]any{conflict}})
	resultPath := filepath.Join(t.TempDir(), "lane-001.json")
	writeJSON(t, resultPath, result)

	if _, err := Accept(paths, AcceptInput{PacketID: "lane-001", AttemptID: lease.AttemptID, ResultPath: resultPath}); err == nil || !strings.Contains(err.Error(), "conflict") {
		t.Fatalf("Accept conflict error = %v", err)
	}
	queue := readJSONObject(t, filepath.Join(paths.RuntimeDir, "workbench", "scan-queue.json"))
	if state := objectRows(t, queue["packets"])[0]["state"]; state != "leased" {
		t.Fatalf("conflicting retry changed queue state to %v", state)
	}
}

func TestAcceptSameResultIsIdempotentAfterAccepted(t *testing.T) {
	paths := newScanPaths(t, []string{"src/app.go"})
	if _, err := Prepare(paths, PrepareInput{}); err != nil {
		t.Fatal(err)
	}
	lease := mustLeasePacket(t, paths, "lane-001")
	resultPath := filepath.Join(t.TempDir(), "lane-001.json")
	writeJSON(t, resultPath, bindWorkerResultToLease(acceptedWorkerResult("lane-001", "src/app.go"), lease))
	if _, err := Accept(paths, AcceptInput{PacketID: "lane-001", AttemptID: lease.AttemptID, ResultPath: resultPath}); err != nil {
		t.Fatal(err)
	}
	payload, err := Accept(paths, AcceptInput{PacketID: "lane-001", AttemptID: lease.AttemptID, ResultPath: resultPath})
	if err != nil {
		t.Fatalf("accepted packet retry returned error: %v", err)
	}
	if payload.Status != "accepted" || payload.PendingPackets != 0 {
		t.Fatalf("accepted retry payload = %#v", payload)
	}
	if got := len(objectRows(t, readJSONObject(t, filepath.Join(paths.RuntimeDir, "provisional", "nodes.json"))["nodes"])); got != 1 {
		t.Fatalf("node count after accepted retry = %d, want 1", got)
	}

	changed := bindWorkerResultToLease(acceptedWorkerResult("lane-001", "src/app.go"), lease)
	objectRows(t, changed["nodes"])[0]["title"] = "changed"
	writeJSON(t, resultPath, changed)
	if _, err := Accept(paths, AcceptInput{PacketID: "lane-001", AttemptID: lease.AttemptID, ResultPath: resultPath}); err == nil {
		t.Fatal("accepted packet retry allowed a different result")
	}
}

func TestAcceptHumanStateFailureCommitsCanonicalQueueAndRemainsRetryable(t *testing.T) {
	paths := newScanPaths(t, []string{"src/app.go"})
	if _, err := Prepare(paths, PrepareInput{}); err != nil {
		t.Fatal(err)
	}
	lease := mustLeasePacket(t, paths, "lane-001")
	mapStatePath := filepath.Join(paths.RuntimeDir, "workbench", "map-state.md")
	if err := os.Remove(mapStatePath); err != nil {
		t.Fatal(err)
	}
	if err := os.Mkdir(mapStatePath, 0o755); err != nil {
		t.Fatal(err)
	}
	resultPath := filepath.Join(t.TempDir(), "lane-001.json")
	writeJSON(t, resultPath, bindWorkerResultToLease(acceptedWorkerResult("lane-001", "src/app.go"), lease))
	if _, err := Accept(paths, AcceptInput{PacketID: "lane-001", AttemptID: lease.AttemptID, ResultPath: resultPath}); err == nil {
		t.Fatal("Accept succeeded despite human-state render fault")
	}
	queue := readJSONObject(t, filepath.Join(paths.RuntimeDir, "workbench", "scan-queue.json"))
	if state := objectRows(t, queue["packets"])[0]["state"]; state != "accepted" {
		t.Fatalf("render fault left canonical queue state %v, want accepted", state)
	}
	if err := os.Remove(mapStatePath); err != nil {
		t.Fatal(err)
	}
	if _, err := Accept(paths, AcceptInput{PacketID: "lane-001", AttemptID: lease.AttemptID, ResultPath: resultPath}); err != nil {
		t.Fatalf("retry after human-state fault failed: %v", err)
	}
}

func checkpointWorkerResult(packetID string, attemptID string, sequence int, assigned []string, completed []string) map[string]any {
	completedSet := map[string]bool{}
	for _, path := range completed {
		completedSet[path] = true
	}
	todo := make([]string, 0, len(assigned)-len(completed))
	for _, path := range assigned {
		if !completedSet[path] {
			todo = append(todo, path)
		}
	}
	coverage := make([]map[string]any, 0, len(completed))
	evidence := make([]map[string]any, 0, len(completed))
	nodes := make([]map[string]any, 0, len(completed))
	for index, path := range completed {
		evidenceID := fmt.Sprintf("E-%s-%d", packetID, index+1)
		nodeID := fmt.Sprintf("N-%s-%d", packetID, index+1)
		coverage = append(coverage, map[string]any{
			"path": path, "outcome": "read", "evidence_ids": []string{evidenceID},
		})
		evidence = append(evidence, map[string]any{
			"id": evidenceID, "source_kind": "source", "source_path": path,
			"span": "1:1-3:1", "extractor": "scan-worker", "content_hash": "hash-" + path,
		})
		nodes = append(nodes, map[string]any{
			"id": nodeID, "type": "file", "title": filepath.Base(path), "confidence": "high",
			"paths": []string{path}, "evidence_ids": []string{evidenceID},
		})
	}
	return map[string]any{
		"protocol":       "map_scan_result.v2",
		"packet_id":      packetID,
		"attempt_id":     attemptID,
		"sequence":       sequence,
		"assigned_paths": append([]string{}, assigned...),
		"paths_read":     append([]string{}, completed...),
		"ledger": map[string]any{
			"todo": todo, "doing": []string{}, "done": append([]string{}, completed...),
			"blocked": []string{}, "overflow": []string{},
		},
		"coverage": coverage, "evidence": evidence, "nodes": nodes,
		"edges": []map[string]any{}, "observations": []map[string]any{}, "claims": []map[string]any{},
		"confidence": "high", "acceptance": "partial",
	}
}

func sharedNodeCheckpointWorkerResult(packetID string, attemptID string, sequence int, assigned []string, completed []string) map[string]any {
	result := checkpointWorkerResult(packetID, attemptID, sequence, assigned, completed)
	evidenceIDs := make([]string, 0, len(completed))
	for index := range completed {
		evidenceIDs = append(evidenceIDs, fmt.Sprintf("E-%s-%d", packetID, index+1))
	}
	result["nodes"] = []map[string]any{{
		"id": "N-" + packetID + "-shared", "type": "component", "title": "shared component", "confidence": "high",
		"paths": append([]string{}, completed...), "evidence_ids": evidenceIDs,
	}}
	return result
}

func sameStringSet(left []string, right []string) bool {
	if len(left) != len(right) {
		return false
	}
	counts := map[string]int{}
	for _, item := range left {
		counts[item]++
	}
	for _, item := range right {
		counts[item]--
	}
	for _, count := range counts {
		if count != 0 {
			return false
		}
	}
	return true
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

func mustLeasePacket(t *testing.T, paths rt.Paths, packetID string) LeasePayload {
	t.Helper()
	lease, err := Lease(paths, LeaseInput{PacketID: packetID, WorkerID: "test-worker-" + packetID})
	if err != nil {
		t.Fatalf("Lease %s returned error: %v", packetID, err)
	}
	return lease
}

func bindWorkerResultToLease(result map[string]any, lease LeasePayload) map[string]any {
	result["protocol"] = "map_scan_result.v2"
	result["attempt_id"] = lease.AttemptID
	result["sequence"] = 1
	result["acceptance"] = "partial"
	return result
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

func rowsByPath(t *testing.T, value any) map[string]map[string]any {
	t.Helper()
	rows := objectRows(t, value)
	byPath := make(map[string]map[string]any, len(rows))
	for _, row := range rows {
		path, ok := row["path"].(string)
		if !ok || path == "" {
			t.Fatalf("row lacks path: %#v", row)
		}
		if _, exists := byPath[path]; exists {
			t.Fatalf("duplicate candidate_universe path %q", path)
		}
		byPath[path] = row
	}
	return byPath
}

func stringMap(t *testing.T, value any) map[string]string {
	t.Helper()
	raw, ok := value.(map[string]any)
	if !ok {
		t.Fatalf("value is not a string map: %#v", value)
	}
	result := make(map[string]string, len(raw))
	for key, item := range raw {
		text, ok := item.(string)
		if !ok {
			t.Fatalf("map value for %s is not a string: %#v", key, item)
		}
		result[key] = text
	}
	return result
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

func containsError(errors []string, want string) bool {
	for _, item := range errors {
		if item == want {
			return true
		}
	}
	return false
}

func cloneTestObject(value map[string]any) map[string]any {
	clone := make(map[string]any, len(value))
	for key, item := range value {
		clone[key] = item
	}
	return clone
}
