package main

import (
	"bytes"
	"context"
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"

	changemodel "github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/changes/model"
	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/delta"
	rt "github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/runtime"
	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/store"
	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/update"
)

func TestCognitionCloseoutApplyRejectsMissingPassingEvidenceBeforeMutation(t *testing.T) {
	project, paths, scopeDir := seedCloseoutApplyRuntime(t)
	payloadJSON := closeoutApplyPayloadJSON(t, false)

	var stdout, stderr bytes.Buffer
	code := Run([]string{
		"cognition", "closeout", "apply",
		"--project-root", project,
		"--workflow", "sp-implement",
		"--scope-dir", scopeDir,
		"--payload-json", payloadJSON,
		"--format", "json",
	}, &stdout, &stderr, "test")
	if code != 10 {
		t.Fatalf("code = %d, want blocked exit 10; stderr=%s stdout=%s", code, stderr.String(), stdout.String())
	}
	envelope := decodeJSONObject(t, stdout.Bytes())
	data := requireObject(t, envelope, "data")
	if data["closeout_status"] != "needs_agent_input" {
		t.Fatalf("data = %#v, want needs_agent_input", data)
	}
	status, err := rt.ReadStatus(paths)
	if err != nil {
		t.Fatal(err)
	}
	if status.LastUpdateID != "" {
		t.Fatalf("LastUpdateID = %q, missing evidence must be rejected before update mutation", status.LastUpdateID)
	}
	if _, err := os.Stat(filepath.Join(project, filepath.FromSlash(scopeDir), mutationCognitionReceiptFileName)); !os.IsNotExist(err) {
		t.Fatalf("receipt exists after preflight rejection: %v", err)
	}
}

func TestCognitionCloseoutApplyFinalizesAndRecordsBoundReadyReceipt(t *testing.T) {
	project, paths, scopeDir := seedCloseoutApplyRuntime(t)
	payloadJSON := closeoutApplyPayloadJSON(t, true)

	var stdout, stderr bytes.Buffer
	code := Run([]string{
		"cognition", "closeout", "apply",
		"--project-root", project,
		"--workflow", "sp-implement",
		"--scope-dir", scopeDir,
		"--payload-json", payloadJSON,
		"--format", "json",
	}, &stdout, &stderr, "test")
	if code != 0 {
		t.Fatalf("code = %d; stderr=%s stdout=%s", code, stderr.String(), stdout.String())
	}
	envelope := decodeJSONObject(t, stdout.Bytes())
	data := requireObject(t, envelope, "data")
	if data["closeout_state"] != "ready" || data["allowed_close"] != true {
		t.Fatalf("data = %#v, want finalized ready closeout", data)
	}
	updateID, _ := data["update_id"].(string)
	if updateID == "" {
		t.Fatalf("data = %#v, want update_id", data)
	}
	status, err := rt.ReadStatus(paths)
	if err != nil {
		t.Fatal(err)
	}
	if status.LastFinalizedUpdateID != updateID || status.LastUpdateOutcome != update.ResultReady {
		t.Fatalf("status = %#v, want receipt-bound finalized update %s", status, updateID)
	}
	gate := mutationCognitionStatus(filepath.Join(project, filepath.FromSlash(scopeDir)))
	if gate["allowed_close"] != true || gate["result_state"] != "ready" {
		t.Fatalf("gate = %#v, want closeable ready receipt", gate)
	}
}

func TestCognitionCloseoutApplyAcceptsLargePayloadFromStdin(t *testing.T) {
	project, _, scopeDir := seedCloseoutApplyRuntime(t)
	payloadJSON := largeCloseoutApplyPayloadJSON(t)
	if len(payloadJSON) <= 32*1024 {
		t.Fatalf("payload is only %d bytes; test must exceed the Windows argv danger zone", len(payloadJSON))
	}
	args := []string{
		"--project-root", project,
		"--workflow", "sp-implement",
		"--scope-dir", scopeDir,
		"--payload-json", "-",
		"--format", "json",
	}
	if got := len(strings.Join(args, "")); got >= 4096 {
		t.Fatalf("argv is %d bytes; large payload leaked into argv", got)
	}

	var stdout bytes.Buffer
	code := runCognitionCloseoutApplyCLIWithInput(args, strings.NewReader(payloadJSON), &stdout)
	if code != 0 {
		t.Fatalf("code = %d; stdout=%s", code, stdout.String())
	}
	data := requireObject(t, decodeJSONObject(t, stdout.Bytes()), "data")
	if data["closeout_state"] != "ready" || data["allowed_close"] != true {
		t.Fatalf("data = %#v, want stdin payload to finalize closeout", data)
	}
}

func TestCognitionCloseoutApplyAcceptsPayloadFromAtPath(t *testing.T) {
	project, _, scopeDir := seedCloseoutApplyRuntime(t)
	payloadPath := filepath.Join(t.TempDir(), "closeout-payload.json")
	if err := os.WriteFile(payloadPath, []byte(largeCloseoutApplyPayloadJSON(t)), 0o600); err != nil {
		t.Fatal(err)
	}

	var stdout bytes.Buffer
	code := runCognitionCloseoutApplyCLIWithInput([]string{
		"--project-root", project,
		"--workflow", "sp-implement",
		"--scope-dir", scopeDir,
		"--payload-json", "@" + payloadPath,
		"--format", "json",
	}, strings.NewReader(""), &stdout)
	if code != 0 {
		t.Fatalf("code = %d; stdout=%s", code, stdout.String())
	}
	data := requireObject(t, decodeJSONObject(t, stdout.Bytes()), "data")
	if data["closeout_state"] != "ready" || data["allowed_close"] != true {
		t.Fatalf("data = %#v, want @path payload to finalize closeout", data)
	}
}

func TestCognitionCloseoutApplyRejectsOversizedInlinePayloadBeforeMutation(t *testing.T) {
	project, paths, scopeDir := seedCloseoutApplyRuntime(t)
	var payload map[string]any
	if err := json.Unmarshal([]byte(closeoutApplyPayloadJSON(t, true)), &payload); err != nil {
		t.Fatal(err)
	}
	payload["confidence_notes"] = []string{strings.Repeat("x", maxAgentJSONInputBytes)}
	raw, err := json.Marshal(payload)
	if err != nil {
		t.Fatal(err)
	}
	if len(raw) <= maxAgentJSONInputBytes {
		t.Fatalf("payload is only %d bytes; test must exceed %d", len(raw), maxAgentJSONInputBytes)
	}

	var stdout bytes.Buffer
	code := runCognitionCloseoutApplyCLIWithInput([]string{
		"--project-root", project,
		"--workflow", "sp-implement",
		"--scope-dir", scopeDir,
		"--payload-json", string(raw),
		"--format", "json",
	}, strings.NewReader(""), &stdout)
	if code == 0 {
		t.Fatalf("code = %d; oversized inline payload must be rejected; stdout=%s", code, stdout.String())
	}
	data := requireObject(t, decodeJSONObject(t, stdout.Bytes()), "data")
	if data["mutation_performed"] != false || data["closeout_status"] != "input_rejected" {
		t.Fatalf("data = %#v, want explicit pre-mutation input rejection", data)
	}
	status, err := rt.ReadStatus(paths)
	if err != nil {
		t.Fatal(err)
	}
	if status.LastUpdateID != "" {
		t.Fatalf("LastUpdateID = %q, oversized input must be rejected before mutation", status.LastUpdateID)
	}
}

func TestCognitionCloseoutApplyAcceptsVerificationEvidenceAlias(t *testing.T) {
	project, _, scopeDir := seedCloseoutApplyRuntime(t)
	payloadJSON := closeoutApplyPayloadJSONWithVerificationField(t, "verification_evidence", true)

	var stdout, stderr bytes.Buffer
	code := Run([]string{
		"cognition", "closeout", "apply",
		"--project-root", project,
		"--workflow", "sp-implement",
		"--scope-dir", scopeDir,
		"--payload-json", payloadJSON,
		"--format", "json",
	}, &stdout, &stderr, "test")
	if code != 0 {
		t.Fatalf("code = %d; stderr=%s stdout=%s", code, stderr.String(), stdout.String())
	}
	envelope := decodeJSONObject(t, stdout.Bytes())
	data := requireObject(t, envelope, "data")
	if data["closeout_state"] != "ready" || data["allowed_close"] != true {
		t.Fatalf("data = %#v, want verification_evidence alias to finalize closeout", data)
	}
}

func TestCognitionCloseoutApplyFinalizesStructuredDeltaSession(t *testing.T) {
	project, paths, scopeDir := seedCloseoutApplyRuntime(t)
	sessionID := appendCloseoutApplyDelta(t, paths, "sp-implement")

	var stdout, stderr bytes.Buffer
	code := Run([]string{
		"cognition", "closeout", "apply",
		"--project-root", project,
		"--workflow", "sp-implement",
		"--scope-dir", scopeDir,
		"--delta-session", sessionID,
		"--format", "json",
	}, &stdout, &stderr, "test")
	if code != 0 {
		t.Fatalf("code = %d; stderr=%s stdout=%s", code, stderr.String(), stdout.String())
	}
	envelope := decodeJSONObject(t, stdout.Bytes())
	data := requireObject(t, envelope, "data")
	if data["closeout_state"] != "ready" || data["allowed_close"] != true {
		t.Fatalf("data = %#v, want finalized ready delta closeout", data)
	}
}

func TestCognitionCloseoutApplyRejectsInvalidDeltaWorkflowBeforeMutation(t *testing.T) {
	project, paths, scopeDir := seedCloseoutApplyRuntime(t)
	sessionID := appendCloseoutApplyDelta(t, paths, "not-a-workflow")

	var stdout, stderr bytes.Buffer
	code := Run([]string{
		"cognition", "closeout", "apply",
		"--project-root", project,
		"--workflow", "sp-implement",
		"--scope-dir", scopeDir,
		"--delta-session", sessionID,
		"--format", "json",
	}, &stdout, &stderr, "test")
	if code == 0 {
		t.Fatalf("code = %d; invalid delta workflow must block; stdout=%s", code, stdout.String())
	}
	status, err := rt.ReadStatus(paths)
	if err != nil {
		t.Fatal(err)
	}
	if status.LastUpdateID != "" {
		t.Fatalf("LastUpdateID = %q, invalid delta workflow must be rejected before mutation", status.LastUpdateID)
	}
}

func TestCognitionCloseoutApplyRejectsRenameOldPathOutsideInlineBoundary(t *testing.T) {
	project, paths, scopeDir := seedCloseoutApplyRuntime(t)
	disposition := changemodel.DispositionAdoptable
	payload := map[string]any{
		"workflow":      "sp-implement",
		"reason":        "workflow-finalize",
		"changed_paths": []string{"src/renamed-app.go"},
		"path_changes": []changemodel.PathChange{{
			Path: "src/renamed-app.go", OldPath: "src/app.go", Operation: changemodel.OperationRename,
			NodeID: "N-app", Disposition: &disposition,
		}},
		"verification": []map[string]string{{"command": "go test ./...", "result": "passed"}},
		"boundary": map[string]any{
			"workflow_owned_paths": []string{"src/renamed-app.go"},
			"scope_mode":           "explicit",
		},
	}
	raw, err := json.Marshal(payload)
	if err != nil {
		t.Fatal(err)
	}

	assertCloseoutApplyBlockedBeforeMutation(t, project, paths, scopeDir, "--payload-json", string(raw))
}

func TestCognitionCloseoutApplyRejectsRenameOldPathOutsideDeltaBoundary(t *testing.T) {
	project, paths, scopeDir := seedCloseoutApplyRuntime(t)
	session, err := delta.Begin(delta.BeginInput{Root: paths.Root, RuntimeDir: paths.RuntimeDir, OriginCommand: "sp-implement"})
	if err != nil {
		t.Fatal(err)
	}
	disposition := changemodel.DispositionAdoptable
	if _, err := delta.Append(delta.AppendInput{
		RuntimeDir:   paths.RuntimeDir,
		SessionID:    session.SessionID,
		EventType:    "workflow_closeout",
		ChangedPaths: []string{"src/renamed-app.go"},
		PathChanges: []changemodel.PathChange{{
			Path: "src/renamed-app.go", OldPath: "src/app.go", Operation: changemodel.OperationRename,
			NodeID: "N-app", Disposition: &disposition,
		}},
		Verification: []string{`{"command":"go test ./...","result":"passed"}`},
	}); err != nil {
		t.Fatal(err)
	}

	assertCloseoutApplyBlockedBeforeMutation(t, project, paths, scopeDir, "--delta-session", session.SessionID)
}

func TestCognitionCloseoutApplyClosesReadyScopeWithoutHidingGlobalDebt(t *testing.T) {
	project, paths, scopeDir := seedCloseoutApplyRuntime(t)
	if _, err := update.MarkDirty(paths, update.DirtyInput{
		Reason:     "older unrelated debt",
		ScopePaths: []string{"src/other.go"},
	}); err != nil {
		t.Fatal(err)
	}

	var stdout, stderr bytes.Buffer
	code := Run([]string{
		"cognition", "closeout", "apply",
		"--project-root", project,
		"--workflow", "sp-implement",
		"--scope-dir", scopeDir,
		"--payload-json", closeoutApplyPayloadJSON(t, true),
		"--format", "json",
	}, &stdout, &stderr, "test")
	if code != 0 {
		t.Fatalf("code = %d; stderr=%s stdout=%s", code, stderr.String(), stdout.String())
	}
	envelope := decodeJSONObject(t, stdout.Bytes())
	data := requireObject(t, envelope, "data")
	if data["closeout_state"] != "scope_ready" || data["allowed_close"] != true {
		t.Fatalf("data = %#v, want closeable scope_ready with global debt preserved", data)
	}
	if data["scope_result_state"] != update.ResultReady || data["result_state"] != update.ResultPartialRefresh {
		t.Fatalf("data = %#v, want ready scope and partial global result", data)
	}
	status, err := rt.ReadStatus(paths)
	if err != nil {
		t.Fatal(err)
	}
	if status.Freshness != rt.PartialRefreshFreshness || !status.Dirty || status.LastFinalizedUpdateID != "" {
		t.Fatalf("status = %#v, global debt must remain truthful and unfinalized", status)
	}
	gate := mutationCognitionStatus(filepath.Join(project, filepath.FromSlash(scopeDir)))
	if gate["allowed_close"] != true || gate["result_state"] != "scope_ready" {
		t.Fatalf("gate = %#v, want closeable scope_ready receipt", gate)
	}
}

func seedCloseoutApplyRuntime(t *testing.T) (string, rt.Paths, string) {
	t.Helper()
	project := t.TempDir()
	if err := os.MkdirAll(filepath.Join(project, ".specify"), 0o755); err != nil {
		t.Fatal(err)
	}
	paths, err := rt.ResolvePaths(project)
	if err != nil {
		t.Fatal(err)
	}
	st, err := store.Open(paths)
	if err != nil {
		t.Fatal(err)
	}
	_, err = st.ImportGeneration(context.Background(), store.ImportInput{
		GenerationID: "GEN-closeout",
		Kind:         "full",
		SourceCommit: "abc123",
		Evidence: []store.EvidenceImport{{
			ID: "E-app", SourceKind: "file", SourcePath: "src/app.go", CommitSHA: "abc123", Extractor: "test", ContentHash: "hash-app",
		}},
		Nodes: []store.NodeImport{{
			ID: "N-app", Type: "capability", Title: "App", Confidence: "verified", EvidenceIDs: []string{"E-app"},
		}},
		PathIndex: []store.PathIndexImport{{
			ID: "P-app", Path: "src/app.go", NodeID: "N-app", Relation: "owns", Confidence: "verified", EvidenceID: "E-app",
		}},
		Aliases: []store.AliasImport{{
			ID: "A-app", Alias: "App", NormalizedAlias: "app", TargetType: "node", TargetID: "N-app", Source: "node_title", Confidence: "verified", EvidenceID: "E-app",
		}},
	})
	if err != nil {
		_ = st.Close()
		t.Fatal(err)
	}
	if _, _, err := st.PublishRuntimeMetadata(context.Background(), "GEN-closeout", rt.BaselineKindBrownfieldFull); err != nil {
		_ = st.Close()
		t.Fatal(err)
	}
	if err := st.Close(); err != nil {
		t.Fatal(err)
	}
	status := rt.DefaultStatus(paths)
	status.Status = "ok"
	status.Freshness = rt.ReadyFreshness
	status.Readiness = rt.ReadyReadiness
	status.RecommendedNextAction = "use_project_cognition"
	status.GraphReady = true
	status.ActiveGenerationID = "GEN-closeout"
	status.BaselineKind = rt.BaselineKindBrownfieldFull
	if err := rt.WriteStatus(paths, status); err != nil {
		t.Fatal(err)
	}
	for name, body := range map[string]string{
		"capability-ledger.json": `{"rows":[]}`,
		"control-ledger.json":    `{"rows":[]}`,
		"coverage-ledger.json":   `{"rows":[{"path":"src/app.go","status":"covered"}],"open_gaps":[]}`,
	} {
		path := filepath.Join(paths.RuntimeDir, "workbench", name)
		if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
			t.Fatal(err)
		}
		if err := os.WriteFile(path, []byte(body+"\n"), 0o644); err != nil {
			t.Fatal(err)
		}
	}
	scopeDir := filepath.ToSlash(filepath.Join(".specify", "features", "001-closeout"))
	if err := os.MkdirAll(filepath.Join(project, filepath.FromSlash(scopeDir)), 0o755); err != nil {
		t.Fatal(err)
	}
	return project, paths, scopeDir
}

func closeoutApplyPayloadJSON(t *testing.T, passing bool) string {
	return closeoutApplyPayloadJSONWithVerificationField(t, "verification", passing)
}

func appendCloseoutApplyDelta(t *testing.T, paths rt.Paths, originCommand string) string {
	t.Helper()
	session, err := delta.Begin(delta.BeginInput{
		Root:          paths.Root,
		RuntimeDir:    paths.RuntimeDir,
		OriginCommand: originCommand,
	})
	if err != nil {
		t.Fatal(err)
	}
	if _, err := delta.Append(delta.AppendInput{
		RuntimeDir:       paths.RuntimeDir,
		SessionID:        session.SessionID,
		EventType:        "workflow_closeout",
		ChangedPaths:     []string{"src/app.go"},
		BehaviorSurfaces: []string{"application entrypoint"},
		Verification:     []string{`{"command":"go test ./...","result":"passed"}`},
	}); err != nil {
		t.Fatal(err)
	}
	return session.SessionID
}

func assertCloseoutApplyBlockedBeforeMutation(t *testing.T, project string, paths rt.Paths, scopeDir string, inputFlag string, inputValue string) {
	t.Helper()
	var stdout, stderr bytes.Buffer
	code := Run([]string{
		"cognition", "closeout", "apply",
		"--project-root", project,
		"--workflow", "sp-implement",
		"--scope-dir", scopeDir,
		inputFlag, inputValue,
		"--format", "json",
	}, &stdout, &stderr, "test")
	if code == 0 {
		t.Fatalf("code = %d; rename scope escape must block; stdout=%s", code, stdout.String())
	}
	status, err := rt.ReadStatus(paths)
	if err != nil {
		t.Fatal(err)
	}
	if status.LastUpdateID != "" {
		t.Fatalf("LastUpdateID = %q, rename scope escape must be rejected before mutation", status.LastUpdateID)
	}
}

func closeoutApplyPayloadJSONWithVerificationField(t *testing.T, field string, passing bool) string {
	t.Helper()
	verification := []map[string]string{}
	if passing {
		verification = append(verification, map[string]string{"command": "go test ./...", "result": "passed"})
	}
	payload := map[string]any{
		"workflow":      "sp-implement",
		"reason":        "workflow-finalize",
		"changed_paths": []string{"src/app.go"},
		"scope_paths":   []string{"src/app.go"},
		"boundary": map[string]any{
			"workflow_owned_paths": []string{"src/app.go"},
			"scope_mode":           "explicit",
		},
	}
	payload[field] = verification
	raw, err := json.Marshal(payload)
	if err != nil {
		t.Fatal(err)
	}
	return string(raw)
}

func largeCloseoutApplyPayloadJSON(t *testing.T) string {
	t.Helper()
	var payload map[string]any
	if err := json.Unmarshal([]byte(closeoutApplyPayloadJSON(t, true)), &payload); err != nil {
		t.Fatal(err)
	}
	payload["implementation_notes"] = []string{strings.Repeat("large-closeout-evidence-", 4096)}
	raw, err := json.Marshal(payload)
	if err != nil {
		t.Fatal(err)
	}
	return string(raw)
}
