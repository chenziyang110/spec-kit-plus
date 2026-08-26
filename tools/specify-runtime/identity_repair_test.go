package main

import (
	"bytes"
	"context"
	"crypto/sha256"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"testing"

	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/store"
	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/validation"
)

func TestCognitionIdentityRepairPlanAndApplyFixBoundedMissingCoverage(t *testing.T) {
	project, paths, _ := seedCloseoutApplyRuntime(t)
	writeIdentityRepairScanPackage(t, paths.RuntimeDir)
	st, err := store.OpenExisting(paths)
	if err != nil {
		t.Fatal(err)
	}
	if _, err := st.AdoptWorkflowPath(context.Background(), store.WorkflowPathAdoption{
		UpdateID:     "upd-keep-path",
		Path:         "src/keep.go",
		Workflow:     "sp-map-update",
		Verification: []map[string]string{{"command": "go test ./...", "result": "passed"}},
		Reason:       "keep-nonzero-path-index",
	}); err != nil {
		_ = st.Close()
		t.Fatal(err)
	}
	if _, err := st.DB().ExecContext(context.Background(), `DELETE FROM path_index WHERE generation_id = 'GEN-closeout' AND path = 'src/app.go'`); err != nil {
		_ = st.Close()
		t.Fatal(err)
	}
	if err := st.Close(); err != nil {
		t.Fatal(err)
	}
	before := validation.ValidateBuild(paths)
	if before.Details["identity_repairability"] != "bounded_path_repair" {
		t.Fatalf("before = %#v, want bounded path repair", before)
	}

	var planOut, planErr bytes.Buffer
	planCode := Run([]string{
		"cognition", "identity-repair", "plan",
		"--project-root", project,
		"--format", "json",
	}, &planOut, &planErr, "test")
	if planCode != 0 {
		t.Fatalf("plan code = %d; stderr=%s stdout=%s", planCode, planErr.String(), planOut.String())
	}
	planData := requireObject(t, decodeJSONObject(t, planOut.Bytes()), "data")
	planRef, _ := planData["plan_ref"].(string)
	planSHA, _ := planData["plan_sha256"].(string)
	if planRef == "" || len(planSHA) != 64 || planData["repairability"] != "bounded_path_repair" {
		t.Fatalf("plan data = %#v", planData)
	}

	var applyOut, applyErr bytes.Buffer
	applyCode := Run([]string{
		"cognition", "identity-repair", "apply",
		"--project-root", project,
		"--plan-ref", planRef,
		"--plan-sha256", planSHA,
		"--format", "json",
	}, &applyOut, &applyErr, "test")
	if applyCode != 0 {
		t.Fatalf("apply code = %d; stderr=%s stdout=%s", applyCode, applyErr.String(), applyOut.String())
	}
	applyData := requireObject(t, decodeJSONObject(t, applyOut.Bytes()), "data")
	if applyData["status"] != "repaired" || applyData["readiness"] != "query_ready" {
		t.Fatalf("apply data = %#v, want repaired query-ready validation", applyData)
	}
}

func TestCognitionIdentityRepairApplyRejectsTamperedRepairRowsBeforeMutation(t *testing.T) {
	project, paths, _ := seedCloseoutApplyRuntime(t)
	writeIdentityRepairScanPackage(t, paths.RuntimeDir)
	st, err := store.OpenExisting(paths)
	if err != nil {
		t.Fatal(err)
	}
	if _, err := st.AdoptWorkflowPath(context.Background(), store.WorkflowPathAdoption{
		UpdateID: "upd-keep-path", Path: "src/keep.go", Workflow: "sp-map-update",
		Verification: []map[string]string{{"command": "go test ./...", "result": "passed"}}, Reason: "keep-nonzero-path-index",
	}); err != nil {
		_ = st.Close()
		t.Fatal(err)
	}
	if _, err := st.DB().ExecContext(context.Background(), `DELETE FROM path_index WHERE generation_id = 'GEN-closeout' AND path = 'src/app.go'`); err != nil {
		_ = st.Close()
		t.Fatal(err)
	}
	if err := st.Close(); err != nil {
		t.Fatal(err)
	}

	var planOut, planErr bytes.Buffer
	if code := Run([]string{"cognition", "identity-repair", "plan", "--project-root", project, "--format", "json"}, &planOut, &planErr, "test"); code != 0 {
		t.Fatalf("plan failed: %d stderr=%s stdout=%s", code, planErr.String(), planOut.String())
	}
	planData := requireObject(t, decodeJSONObject(t, planOut.Bytes()), "data")
	planRef := planData["plan_ref"].(string)
	planPath := filepath.Join(project, filepath.FromSlash(planRef))
	raw, err := os.ReadFile(planPath)
	if err != nil {
		t.Fatal(err)
	}
	var plan map[string]any
	if err := json.Unmarshal(raw, &plan); err != nil {
		t.Fatal(err)
	}
	repairs := plan["repairs"].([]any)
	repairs[0].(map[string]any)["path"] = "src/forged.go"
	tampered, err := json.MarshalIndent(plan, "", "  ")
	if err != nil {
		t.Fatal(err)
	}
	tampered = append(tampered, '\n')
	if err := os.WriteFile(planPath, tampered, 0o644); err != nil {
		t.Fatal(err)
	}
	tamperedSHA := sha256.Sum256(tampered)

	var applyOut, applyErr bytes.Buffer
	applyCode := Run([]string{
		"cognition", "identity-repair", "apply", "--project-root", project,
		"--plan-ref", planRef, "--plan-sha256", fmt.Sprintf("%x", tamperedSHA[:]), "--format", "json",
	}, &applyOut, &applyErr, "test")
	if applyCode == 0 {
		t.Fatalf("tampered apply unexpectedly succeeded: %s", applyOut.String())
	}
	st, err = store.OpenExisting(paths)
	if err != nil {
		t.Fatal(err)
	}
	defer st.Close()
	var forgedCount int
	if err := st.DB().QueryRowContext(context.Background(), `SELECT COUNT(*) FROM path_index WHERE path = 'src/forged.go'`).Scan(&forgedCount); err != nil {
		t.Fatal(err)
	}
	if forgedCount != 0 {
		t.Fatalf("tampered identity repair mutated %d forged rows before rejection", forgedCount)
	}
}

func writeIdentityRepairScanPackage(t *testing.T, runtimeDir string) {
	t.Helper()
	files := map[string]string{
		filepath.Join(runtimeDir, "evidence", "E-app.json"):                 `{"id":"E-app","source_kind":"file","source_path":"src/app.go","commit_sha":"abc123","span":"L1-L5","extractor":"test","content_hash":"hash-app","attrs":{"language":"go"}}`,
		filepath.Join(runtimeDir, "provisional", "nodes.json"):              `{"nodes":[{"id":"N-app","type":"capability","title":"App","confidence":"verified","paths":["src/app.go"],"evidence_ids":["E-app"],"attrs":{"owner":"app"}}]}`,
		filepath.Join(runtimeDir, "provisional", "edges.json"):              `{"edges":[]}`,
		filepath.Join(runtimeDir, "provisional", "observations.json"):       `{"observations":[]}`,
		filepath.Join(runtimeDir, "coverage.json"):                          `{"rows":[{"path":"src/app.go"}]}`,
		filepath.Join(runtimeDir, "workbench", "map-scan.md"):               `# Map Scan`,
		filepath.Join(runtimeDir, "workbench", "coverage-ledger.md"):        `# Coverage Ledger`,
		filepath.Join(runtimeDir, "workbench", "scan-packets", "lane-1.md"): `# Lane 1`,
		filepath.Join(runtimeDir, "workbench", "worker-results", "lane-1.json"): `{
            "packet_id":"lane-1",
            "family_id":"app",
            "assigned_paths":["src/app.go"],
            "paths_read":["src/app.go"],
            "ledger":{"todo":[],"doing":[],"done":["src/app.go"],"blocked":[],"overflow":[]},
            "coverage":[{"path":"src/app.go","outcome":"read","evidence_ids":["E-app"]}],
            "confidence":"high",
            "acceptance":"pass"
        }`,
		filepath.Join(runtimeDir, "workbench", "map-state.md"):             `# Map State`,
		filepath.Join(runtimeDir, "workbench", "repository-universe.json"): `{"rows":[{"path":"src/app.go"}]}`,
		filepath.Join(runtimeDir, "workbench", "scan-queue.json"): `{"packets":[{
            "packet_id":"lane-1",
            "state":"accepted",
            "assigned_paths":["src/app.go"],
            "result_handoff_path":".specify/project-cognition/workbench/worker-results/lane-1.json"
        }]}`,
		filepath.Join(runtimeDir, "workbench", "handoff-ledger.json"): `{"events":[
            {"event_id":"dispatch-1","packet_id":"lane-1","event_type":"dispatched","created_at":"2026-05-26T00:00:00Z"},
            {"event_id":"return-1","packet_id":"lane-1","event_type":"returned","worker_result_path":".specify/project-cognition/workbench/worker-results/lane-1.json","created_at":"2026-05-26T00:01:00Z"}
        ]}`,
	}
	for path, content := range files {
		if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
			t.Fatal(err)
		}
		if err := os.WriteFile(path, []byte(content+"\n"), 0o644); err != nil {
			t.Fatal(err)
		}
	}
}
