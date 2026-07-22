package scanreceipt

import (
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"

	rt "github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/runtime"
)

func TestCreateAndVerifyBindBoundaryArtifacts(t *testing.T) {
	paths := newReceiptPaths(t)

	receipt, required, err := Create(paths, "scan_ready")
	if err != nil || !required {
		t.Fatalf("Create receipt=%#v required=%v err=%v", receipt, required, err)
	}
	if receipt.Protocol != ReceiptProtocol || receipt.GenerationID != "GEN-test" {
		t.Fatalf("receipt identity = %#v", receipt)
	}
	if required, err := Verify(paths); err != nil || !required {
		t.Fatalf("Verify required=%v err=%v", required, err)
	}

	writeReceiptJSON(t, filepath.Join(paths.RuntimeDir, "workbench", "repository-universe.json"), map[string]any{
		"included_paths": []string{"src/app.go", "src/late.go"},
	})
	if required, err := Verify(paths); !required || err == nil || !strings.Contains(err.Error(), "stale") {
		t.Fatalf("Verify after boundary mutation required=%v err=%v", required, err)
	}
}

func TestVerifyRejectsSourceMutationAfterValidation(t *testing.T) {
	paths := newReceiptPaths(t)
	if _, required, err := Create(paths, "scan_ready"); err != nil || !required {
		t.Fatalf("Create required=%v err=%v", required, err)
	}
	if err := os.WriteFile(filepath.Join(paths.Root, "src", "app.go"), []byte("package app\n// changed after validation\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	if required, err := Verify(paths); !required || err == nil || !strings.Contains(err.Error(), "stale") {
		t.Fatalf("Verify after source mutation required=%v err=%v", required, err)
	}
}

func TestCreateExpectedRejectsValidateThenSealSnapshotChange(t *testing.T) {
	paths := newReceiptPaths(t)
	fingerprint, required, err := ComputeFingerprint(paths)
	if err != nil || !required {
		t.Fatalf("ComputeFingerprint required=%v err=%v", required, err)
	}
	if err := os.WriteFile(filepath.Join(paths.Root, "src", "app.go"), []byte("package app\n// changed during validation\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	if _, required, err := CreateExpected(paths, "scan_ready", &fingerprint); !required || err == nil || !strings.Contains(err.Error(), "changed") {
		t.Fatalf("CreateExpected changed snapshot required=%v err=%v", required, err)
	}
}

func TestCreateExpectedRejectsV2ToLegacyProtocolTransition(t *testing.T) {
	paths := newReceiptPaths(t)
	fingerprint, required, err := ComputeFingerprint(paths)
	if err != nil || !required {
		t.Fatalf("ComputeFingerprint required=%v err=%v", required, err)
	}
	writeReceiptJSON(t, filepath.Join(paths.RuntimeDir, "workbench", "scan-queue.json"), map[string]any{
		"packets": []map[string]any{},
	})

	if _, required, err := CreateExpected(paths, "scan_ready", &fingerprint); !required || err == nil || !strings.Contains(err.Error(), "changed") {
		t.Fatalf("CreateExpected protocol transition required=%v err=%v", required, err)
	}
}

func TestVerifyRejectsV2ProtocolDowngrade(t *testing.T) {
	paths := newReceiptPaths(t)
	if _, required, err := Create(paths, "scan_ready"); err != nil || !required {
		t.Fatalf("Create required=%v err=%v", required, err)
	}
	writeReceiptJSON(t, filepath.Join(paths.RuntimeDir, "workbench", "scan-queue.json"), map[string]any{
		"generation_id": "GEN-test", "scan_set_path": ".specify/project-cognition/tmp/scan-files.json",
		"packets": []map[string]any{},
	})
	if required, err := Verify(paths); !required || err == nil || !strings.Contains(err.Error(), "protocol") {
		t.Fatalf("Verify downgraded v2 queue required=%v err=%v", required, err)
	}
}

func TestVerifyRejectsSymlinkedCanonicalArtifactDirectory(t *testing.T) {
	paths := newReceiptPaths(t)
	if _, required, err := Create(paths, "scan_ready"); err != nil || !required {
		t.Fatalf("Create required=%v err=%v", required, err)
	}
	evidenceDir := filepath.Join(paths.RuntimeDir, "evidence")
	if err := os.Remove(evidenceDir); err != nil {
		t.Fatal(err)
	}
	if err := os.Symlink(t.TempDir(), evidenceDir); err != nil {
		t.Skipf("symbolic links are unavailable: %v", err)
	}
	if required, err := Verify(paths); !required || err == nil || !strings.Contains(err.Error(), "symbolic") {
		t.Fatalf("Verify symlinked artifacts required=%v err=%v", required, err)
	}
}

func TestCreateRejectsScanSetOutsideRepository(t *testing.T) {
	paths := newReceiptPaths(t)
	external := filepath.Join(t.TempDir(), "scan-files.json")
	writeReceiptJSON(t, external, map[string]any{"files": []string{"src/app.go"}})
	writeReceiptJSON(t, filepath.Join(paths.RuntimeDir, "workbench", "scan-queue.json"), map[string]any{
		"protocol": WorkbenchProtocol, "generation_id": "GEN-test", "scan_set_path": external,
		"packets": []map[string]any{},
	})

	if _, required, err := Create(paths, "scan_ready"); !required || err == nil || !strings.Contains(err.Error(), "outside") {
		t.Fatalf("Create outside scan set required=%v err=%v", required, err)
	}
}

func TestLegacyWorkbenchDoesNotRequireReceipt(t *testing.T) {
	paths := newReceiptPaths(t)
	writeReceiptJSON(t, filepath.Join(paths.RuntimeDir, "workbench", "scan-queue.json"), map[string]any{
		"packets": []map[string]any{},
	})

	if _, required, err := Create(paths, "scan_ready"); err != nil || required {
		t.Fatalf("legacy Create required=%v err=%v", required, err)
	}
	if required, err := Verify(paths); err != nil || required {
		t.Fatalf("legacy Verify required=%v err=%v", required, err)
	}
}

func TestV2IdentityCannotDowngradeByRemovingProtocol(t *testing.T) {
	paths := newReceiptPaths(t)
	writeReceiptJSON(t, filepath.Join(paths.RuntimeDir, "workbench", "scan-queue.json"), map[string]any{
		"generation_id": "GEN-test",
		"scan_set_path": ".specify/project-cognition/tmp/scan-files.json",
		"packets":       []map[string]any{},
	})

	if _, required, err := Create(paths, "scan_ready"); !required || err == nil || !strings.Contains(err.Error(), "protocol") {
		t.Fatalf("downgraded Create required=%v err=%v", required, err)
	}
	if required, err := Verify(paths); !required || err == nil || !strings.Contains(err.Error(), "protocol") {
		t.Fatalf("downgraded Verify required=%v err=%v", required, err)
	}
}

func TestVerifyRejectsRemovalOfV2QueueAfterReceipt(t *testing.T) {
	paths := newReceiptPaths(t)
	if _, required, err := Create(paths, "scan_ready"); err != nil || !required {
		t.Fatalf("Create required=%v err=%v", required, err)
	}
	if err := os.Remove(filepath.Join(paths.RuntimeDir, "workbench", "scan-queue.json")); err != nil {
		t.Fatal(err)
	}

	if required, err := Verify(paths); !required || err == nil || !strings.Contains(err.Error(), "scan-queue.json") {
		t.Fatalf("Verify after queue removal required=%v err=%v", required, err)
	}
}

func TestVerifyRejectsCompleteV2IdentityStrippingAfterReceipt(t *testing.T) {
	paths := newReceiptPaths(t)
	if _, required, err := Create(paths, "scan_ready"); err != nil || !required {
		t.Fatalf("Create required=%v err=%v", required, err)
	}
	writeReceiptJSON(t, filepath.Join(paths.RuntimeDir, "workbench", "scan-queue.json"), map[string]any{
		"packets": []map[string]any{},
	})

	if required, err := Verify(paths); !required || err == nil || !strings.Contains(err.Error(), "protocol") {
		t.Fatalf("Verify after identity stripping required=%v err=%v", required, err)
	}
}

func TestCreateRejectsUnreadableQueueShape(t *testing.T) {
	paths := newReceiptPaths(t)
	queuePath := filepath.Join(paths.RuntimeDir, "workbench", "scan-queue.json")
	if err := os.Remove(queuePath); err != nil {
		t.Fatal(err)
	}
	if err := os.Mkdir(queuePath, 0o755); err != nil {
		t.Fatal(err)
	}

	if _, required, err := Create(paths, "scan_ready"); !required || err == nil || !strings.Contains(err.Error(), "scan-queue.json") {
		t.Fatalf("Create with unreadable queue required=%v err=%v", required, err)
	}
}

func newReceiptPaths(t *testing.T) rt.Paths {
	t.Helper()
	root := t.TempDir()
	if err := os.MkdirAll(filepath.Join(root, ".specify"), 0o755); err != nil {
		t.Fatal(err)
	}
	paths, err := rt.ResolvePaths(root)
	if err != nil {
		t.Fatal(err)
	}
	for _, dir := range []string{
		filepath.Join(root, "src"),
		filepath.Join(paths.RuntimeDir, "tmp"),
		filepath.Join(paths.RuntimeDir, "workbench", "worker-results"),
		filepath.Join(paths.RuntimeDir, "evidence"),
		filepath.Join(paths.RuntimeDir, "provisional"),
	} {
		if err := os.MkdirAll(dir, 0o755); err != nil {
			t.Fatal(err)
		}
	}
	if err := os.WriteFile(filepath.Join(root, "src", "app.go"), []byte("package app\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	writeReceiptJSON(t, filepath.Join(paths.RuntimeDir, "tmp", "scan-files.json"), map[string]any{
		"files": []string{"src/app.go"},
	})
	writeReceiptJSON(t, filepath.Join(paths.RuntimeDir, "workbench", "scan-queue.json"), map[string]any{
		"protocol": WorkbenchProtocol, "generation_id": "GEN-test",
		"scan_set_path": ".specify/project-cognition/tmp/scan-files.json",
		"packets":       []map[string]any{},
	})
	for _, path := range []string{
		filepath.Join(paths.RuntimeDir, "coverage.json"),
		filepath.Join(paths.RuntimeDir, "workbench", "handoff-ledger.json"),
		filepath.Join(paths.RuntimeDir, "workbench", "coverage-ledger.json"),
		filepath.Join(paths.RuntimeDir, "workbench", "repository-universe.json"),
		filepath.Join(paths.RuntimeDir, "workbench", "scan-targets.json"),
		filepath.Join(paths.RuntimeDir, "workbench", "capability-ledger.json"),
		filepath.Join(paths.RuntimeDir, "workbench", "control-ledger.json"),
		filepath.Join(paths.RuntimeDir, "provisional", "nodes.json"),
		filepath.Join(paths.RuntimeDir, "provisional", "edges.json"),
		filepath.Join(paths.RuntimeDir, "provisional", "observations.json"),
		filepath.Join(paths.RuntimeDir, "provisional", "claims.json"),
	} {
		writeReceiptJSON(t, path, map[string]any{"rows": []map[string]any{}})
	}
	return paths
}

func writeReceiptJSON(t *testing.T, path string, value any) {
	t.Helper()
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		t.Fatal(err)
	}
	data, err := json.Marshal(value)
	if err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(path, append(data, '\n'), 0o644); err != nil {
		t.Fatal(err)
	}
}
