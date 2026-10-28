package main

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"testing"
)

// These fixtures isolate the real archived-byte verifier and history reader.
// They are not live application evidence or semantic workflow acceptance.
// All references are unique snapshots sharing one immutable payload, matching
// the duplication encountered when historical attempts reuse large evidence.
func e2eOptimizationArchiveFixture(b *testing.B, count, payloadBytes int) (*e2eService, []e2eRef) {
	b.Helper()
	root := b.TempDir()
	service := &e2eService{projectRoot: root, runID: "benchmark", rootRef: ".planning/e2e/benchmark", observed: map[string]string{}}
	payload := make([]byte, payloadBytes)
	for index := range payload {
		payload[index] = byte(index % 251)
	}
	digest := fileContentSHA256(payload)
	blob := service.rootRef + "/blobs/" + digest + ".bin"
	write := func(ref string, raw []byte) {
		p := filepath.Join(root, filepath.FromSlash(ref))
		if err := os.MkdirAll(filepath.Dir(p), 0o755); err != nil {
			b.Fatal(err)
		}
		if err := os.WriteFile(p, raw, 0o644); err != nil {
			b.Fatal(err)
		}
	}
	write(blob, payload)
	refs := make([]e2eRef, 0, count)
	for index := 0; index < count; index++ {
		submission := e2eSubmission{SchemaVersion: "e2e-worker-result-v1", WorkerID: fmt.Sprintf("attempt-%03d", index), Outcome: "failed",
			WorkerResult:      map[string]any{"status": "failed", "summary": "Synthetic benchmark history; not an application verdict"},
			WorkerResultInput: json.RawMessage(`{"status":"failed","summary":"Synthetic benchmark history"}`),
			Evidence:          []e2eBinding{{Path: "tests/e2e/shared.bin", SHA256: digest, ArchiveRef: blob}}}
		ref, raw, err := service.snapshot(submission)
		if err != nil {
			b.Fatal(err)
		}
		write(ref.Ref, raw)
		refs = append(refs, ref)
	}
	return service, refs
}

func BenchmarkE2EOptimizationSharedArchiveValidation(b *testing.B) {
	for _, payloadBytes := range []int{64 * 1024, 1024 * 1024} {
		for _, count := range []int{1, 8, 64} {
			b.Run(fmt.Sprintf("payload=%d/references=%d", payloadBytes, count), func(b *testing.B) {
				service, refs := e2eOptimizationArchiveFixture(b, count, payloadBytes)
				b.ReportAllocs()
				b.SetBytes(int64(payloadBytes * count))
				b.ResetTimer()
				for iteration := 0; iteration < b.N; iteration++ {
					service.resetReadRequest()
					for _, ref := range refs {
						var submission e2eSubmission
						if err := service.readSnapshot(ref, &submission); err != nil {
							b.Fatal(err)
						}
					}
				}
				b.ReportMetric(float64(service.immutable.reads), "immutable-reads/op")
				b.ReportMetric(float64(service.immutable.readBytes), "immutable-read-bytes/op")
				b.ReportMetric(float64(service.immutable.hits), "immutable-hits/op")
			})
		}
	}
}

func BenchmarkE2EOptimizationHistoryRead(b *testing.B) {
	for _, count := range []int{1, 16, 64} {
		b.Run(fmt.Sprintf("history=%d/shared_payload=1048576", count), func(b *testing.B) {
			service, refs := e2eOptimizationArchiveFixture(b, count, 1024*1024)
			state := e2eState{SchemaVersion: e2eWorkflowSchema, RunID: service.runID, Revision: 1, LeaderID: "leader", Mode: "execution", Status: "active",
				Scope: []e2eScope{{ID: "save", Target: "cli", Operation: "save"}}, Tasks: []e2eTaskState{}, Events: []e2eRef{}}
			for stage := 1; stage <= 7; stage++ {
				contract := e2eTaskSpec{ID: fmt.Sprintf("S%d", stage), Stage: stage, ScopeIDs: []string{"save"}, Inputs: []string{},
					Outputs: []string{fmt.Sprintf("tests/e2e/s%d.txt", stage)}, Acceptance: []e2eCriterion{{ID: "readback", Criterion: "Independent readback matches request"}}}
				state.Tasks = append(state.Tasks, e2eNewTask(contract, state.Mode))
			}
			state.Tasks[0].History = refs
			raw, err := json.Marshal(state)
			if err != nil {
				b.Fatal(err)
			}
			if err := os.WriteFile(filepath.Join(service.projectRoot, filepath.FromSlash(service.rootRef+"/state.json")), raw, 0o644); err != nil {
				b.Fatal(err)
			}
			if _, err := service.readState(); err != nil {
				b.Fatalf("benchmark precondition: %v", err)
			}
			b.ReportAllocs()
			b.SetBytes(int64(count * 1024 * 1024))
			b.ResetTimer()
			for iteration := 0; iteration < b.N; iteration++ {
				service.resetReadRequest()
				if _, err := service.readState(); err != nil {
					b.Fatal(err)
				}
			}
			b.ReportMetric(float64(service.immutable.reads), "immutable-reads/op")
			b.ReportMetric(float64(service.immutable.readBytes), "immutable-read-bytes/op")
			b.ReportMetric(float64(service.immutable.hits), "immutable-hits/op")
		})
	}
}
