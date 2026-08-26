package main

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"testing"
	"time"

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

func TestCognitionCloseoutApplyRecoversPendingPredecessorBeforeCurrentUpdate(t *testing.T) {
	project, paths, scopeDir := seedCloseoutApplyRuntime(t)
	pending, err := update.RunUpdate(paths, update.UpdateInput{
		ChangedPaths: []string{"src/app.go"},
		Reason:       "previous-workflow-finalize",
		Workflow:     "sp-fast",
		Verification: []update.VerificationEvidence{{Command: "go test ./...", Result: "passed"}},
	})
	if err != nil {
		t.Fatal(err)
	}
	if pending.ResultState != update.ResultReady {
		t.Fatalf("pending ResultState = %q, want ready", pending.ResultState)
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
	data := requireObject(t, decodeJSONObject(t, stdout.Bytes()), "data")
	recovery := requireObject(t, data, "predecessor_recovery")
	if recovery["attempted"] != true || recovery["outcome"] != "finalized" || recovery["update_id"] != pending.UpdateID {
		t.Fatalf("predecessor_recovery = %#v, want exact pending update finalized", recovery)
	}
	currentUpdateID, _ := data["update_id"].(string)
	if currentUpdateID == "" || currentUpdateID == pending.UpdateID {
		t.Fatalf("update_id = %q, want a new current update after recovering %s", currentUpdateID, pending.UpdateID)
	}
	status, err := rt.ReadStatus(paths)
	if err != nil {
		t.Fatal(err)
	}
	if status.LastFinalizedUpdateID != currentUpdateID || status.LastUpdateID != currentUpdateID {
		t.Fatalf("status = %#v, want current update finalized after predecessor recovery", status)
	}
}

func TestCognitionCloseoutApplyRecordsCurrentScopeWhenPredecessorRecoveryBlocks(t *testing.T) {
	project, paths, scopeDir := seedCloseoutApplyRuntime(t)
	pending, err := update.RunUpdate(paths, update.UpdateInput{
		ChangedPaths: []string{"src/app.go"},
		Reason:       "previous-workflow-finalize",
		Workflow:     "sp-fast",
		Verification: []update.VerificationEvidence{{Command: "go test ./...", Result: "passed"}},
	})
	if err != nil {
		t.Fatal(err)
	}
	if err := os.Remove(filepath.Join(paths.RuntimeDir, "workbench", "capability-ledger.json")); err != nil {
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
	if code != 10 {
		t.Fatalf("code = %d, want blocked exit 10; stderr=%s stdout=%s", code, stderr.String(), stdout.String())
	}
	data := requireObject(t, decodeJSONObject(t, stdout.Bytes()), "data")
	if data["closeout_status"] != "predecessor_recovery_blocked" || data["current_mutation_accounting"] != "recorded" || data["closeout_state"] != "predecessor_recovery_blocked" {
		t.Fatalf("data = %#v, want exact current mutation recorded without laundering recovery", data)
	}
	recovery := requireObject(t, data, "predecessor_recovery")
	if recovery["attempted"] != true || recovery["outcome"] != "blocked" || recovery["update_id"] != pending.UpdateID {
		t.Fatalf("predecessor_recovery = %#v, want blocked exact predecessor", recovery)
	}
	validation := requireObject(t, recovery, "validation")
	if _, leaked := validation["identity_diffs"]; leaked {
		t.Fatalf("predecessor validation leaked unbounded identity_diffs: %#v", validation)
	}
	receiptPath := filepath.Join(project, filepath.FromSlash(scopeDir), mutationCognitionReceiptFileName)
	raw, err := os.ReadFile(receiptPath)
	if err != nil {
		t.Fatal(err)
	}
	var receipt map[string]any
	if err := json.Unmarshal(raw, &receipt); err != nil {
		t.Fatal(err)
	}
	if receipt["result_state"] != "blocked" {
		t.Fatalf("receipt = %#v, want non-closeable predecessor recovery accounting", receipt)
	}
	changedPaths, ok := receipt["changed_paths"].([]any)
	if !ok || len(changedPaths) != 1 || changedPaths[0] != "src/app.go" {
		t.Fatalf("receipt changed_paths = %#v, want exact current scope", receipt["changed_paths"])
	}
	status, err := rt.ReadStatus(paths)
	if err != nil {
		t.Fatal(err)
	}
	if status.LastUpdateID != pending.UpdateID || status.LastFinalizedUpdateID != "" {
		t.Fatalf("status = %#v, blocked recovery must not commit or finalize the current update", status)
	}
	if err := requireMutationCognitionReceipt(filepath.Join(project, filepath.FromSlash(scopeDir)), "sp-implement"); err == nil || !strings.Contains(err.Error(), "not closeable") {
		t.Fatalf("requireMutationCognitionReceipt error = %v, want predecessor-blocked receipt to reject terminal close", err)
	}
	intentRef, _ := data["intent_ref"].(string)
	if intentRef == "" {
		t.Fatalf("data = %#v, want durable replay intent", data)
	}
}

func TestCognitionCloseoutApplySerializesConcurrentReadyCloseouts(t *testing.T) {
	project, _, scopeA := seedCloseoutApplyRuntime(t)
	scopeB := filepath.ToSlash(filepath.Join(".specify", "features", "002-closeout"))
	if err := os.MkdirAll(filepath.Join(project, filepath.FromSlash(scopeB)), 0o755); err != nil {
		t.Fatal(err)
	}

	firstReached := make(chan struct{})
	releaseFirst := make(chan struct{})
	var once sync.Once
	closeoutApplyAfterUpdateHook = func(updateID string) error {
		once.Do(func() {
			close(firstReached)
			<-releaseFirst
		})
		return nil
	}
	t.Cleanup(func() { closeoutApplyAfterUpdateHook = nil })

	type result struct {
		code int
		data map[string]any
	}
	run := func(scope string, out chan<- result) {
		var stdout, stderr bytes.Buffer
		code := Run([]string{
			"cognition", "closeout", "apply",
			"--project-root", project,
			"--workflow", "sp-implement",
			"--scope-dir", scope,
			"--payload-json", closeoutApplyPayloadJSON(t, true),
			"--format", "json",
		}, &stdout, &stderr, "test")
		if code != 0 {
			out <- result{code: code, data: map[string]any{"stderr": stderr.String(), "stdout": stdout.String()}}
			return
		}
		out <- result{code: code, data: requireObject(t, decodeJSONObject(t, stdout.Bytes()), "data")}
	}

	first := make(chan result, 1)
	second := make(chan result, 1)
	go run(scopeA, first)
	select {
	case <-firstReached:
	case <-time.After(5 * time.Second):
		t.Fatal("first closeout did not reach the post-update hook")
	}
	go run(scopeB, second)
	select {
	case early := <-second:
		close(releaseFirst)
		t.Fatalf("second closeout bypassed the end-to-end closeout lock: %#v", early)
	case <-time.After(250 * time.Millisecond):
	}
	close(releaseFirst)

	firstResult := <-first
	secondResult := <-second
	for label, got := range map[string]result{"first": firstResult, "second": secondResult} {
		if got.code != 0 || got.data["allowed_close"] != true {
			t.Fatalf("%s closeout = %#v, want closeable success", label, got)
		}
		receipt := requireObject(t, got.data, "receipt")
		if receipt["update_id"] != got.data["update_id"] {
			t.Fatalf("%s receipt/update mismatch: receipt=%#v data=%#v", label, receipt, got.data)
		}
	}
}

func TestCognitionCloseoutApplyResumesIntentAfterCrashBeforeCurrentUpdate(t *testing.T) {
	project, paths, scopeDir := seedCloseoutApplyRuntime(t)
	closeoutApplyAfterIntentPersistHook = func(intentID string) error {
		return errors.New("simulated crash after durable intent")
	}
	t.Cleanup(func() { closeoutApplyAfterIntentPersistHook = nil })

	var firstOut, firstErr bytes.Buffer
	firstCode := Run([]string{
		"cognition", "closeout", "apply",
		"--project-root", project,
		"--workflow", "sp-implement",
		"--scope-dir", scopeDir,
		"--payload-json", closeoutApplyPayloadJSON(t, true),
		"--format", "json",
	}, &firstOut, &firstErr, "test")
	if firstCode != 10 {
		t.Fatalf("first code = %d, want blocked simulated crash; stderr=%s stdout=%s", firstCode, firstErr.String(), firstOut.String())
	}
	firstData := requireObject(t, decodeJSONObject(t, firstOut.Bytes()), "data")
	if firstData["closeout_status"] != "closeout_intent_pending" {
		t.Fatalf("first data = %#v, want durable pending intent", firstData)
	}
	if got := countCloseoutApplyUpdates(t, paths); got != 0 {
		t.Fatalf("update count after pre-update crash = %d, want 0", got)
	}
	closeoutApplyAfterIntentPersistHook = nil

	var secondOut, secondErr bytes.Buffer
	secondCode := Run([]string{
		"cognition", "closeout", "apply",
		"--project-root", project,
		"--workflow", "sp-implement",
		"--scope-dir", scopeDir,
		"--payload-json", closeoutApplyPayloadJSON(t, true),
		"--format", "json",
	}, &secondOut, &secondErr, "test")
	if secondCode != 0 {
		t.Fatalf("second code = %d; stderr=%s stdout=%s", secondCode, secondErr.String(), secondOut.String())
	}
	secondData := requireObject(t, decodeJSONObject(t, secondOut.Bytes()), "data")
	if secondData["resumed_from_intent"] != true || secondData["allowed_close"] != true {
		t.Fatalf("second data = %#v, want replayed closeable intent", secondData)
	}
	if got := countCloseoutApplyUpdates(t, paths); got != 1 {
		t.Fatalf("update count after replay = %d, want exactly 1", got)
	}
}

func TestCognitionCloseoutApplyResumesIntentAfterCrashAfterCurrentUpdate(t *testing.T) {
	project, paths, scopeDir := seedCloseoutApplyRuntime(t)
	crashOnce := true
	closeoutApplyAfterUpdateHook = func(updateID string) error {
		if crashOnce {
			crashOnce = false
			return errors.New("simulated crash after current update")
		}
		return nil
	}
	t.Cleanup(func() { closeoutApplyAfterUpdateHook = nil })

	var firstOut, firstErr bytes.Buffer
	firstCode := Run([]string{
		"cognition", "closeout", "apply",
		"--project-root", project,
		"--workflow", "sp-implement",
		"--scope-dir", scopeDir,
		"--payload-json", closeoutApplyPayloadJSON(t, true),
		"--format", "json",
	}, &firstOut, &firstErr, "test")
	if firstCode != 10 || countCloseoutApplyUpdates(t, paths) != 1 {
		t.Fatalf("first closeout code/update-count = %d/%d; stderr=%s stdout=%s", firstCode, countCloseoutApplyUpdates(t, paths), firstErr.String(), firstOut.String())
	}
	intents, err := listCloseoutIntents(paths)
	if err != nil || len(intents) != 1 || intents[0].UpdateID == "" {
		t.Fatalf("intents = %#v err=%v, want one update-bound intent", intents, err)
	}
	wantUpdateID := intents[0].UpdateID
	closeoutApplyAfterUpdateHook = nil

	var secondOut, secondErr bytes.Buffer
	secondCode := Run([]string{
		"cognition", "closeout", "apply",
		"--project-root", project,
		"--workflow", "sp-implement",
		"--scope-dir", scopeDir,
		"--payload-json", closeoutApplyPayloadJSON(t, true),
		"--format", "json",
	}, &secondOut, &secondErr, "test")
	if secondCode != 0 {
		t.Fatalf("second code = %d; stderr=%s stdout=%s", secondCode, secondErr.String(), secondOut.String())
	}
	data := requireObject(t, decodeJSONObject(t, secondOut.Bytes()), "data")
	if data["update_id"] != wantUpdateID || data["resumed_from_intent"] != true || countCloseoutApplyUpdates(t, paths) != 1 {
		t.Fatalf("data=%#v update-count=%d, want same update %s resumed", data, countCloseoutApplyUpdates(t, paths), wantUpdateID)
	}
}

func TestCognitionCloseoutApplyDrainsOlderIntentBeforeDifferentCurrentScope(t *testing.T) {
	project, paths, scopeA := seedCloseoutApplyRuntime(t)
	scopeB := filepath.ToSlash(filepath.Join(".specify", "features", "002-closeout"))
	if err := os.MkdirAll(filepath.Join(project, filepath.FromSlash(scopeB)), 0o755); err != nil {
		t.Fatal(err)
	}
	closeoutApplyAfterIntentPersistHook = func(intentID string) error {
		return errors.New("leave first scope queued")
	}

	var firstOut, firstErr bytes.Buffer
	firstCode := Run([]string{
		"cognition", "closeout", "apply",
		"--project-root", project,
		"--workflow", "sp-implement",
		"--scope-dir", scopeA,
		"--payload-json", closeoutApplyPayloadJSON(t, true),
		"--format", "json",
	}, &firstOut, &firstErr, "test")
	if firstCode != 10 {
		t.Fatalf("first code = %d; stderr=%s stdout=%s", firstCode, firstErr.String(), firstOut.String())
	}
	closeoutApplyAfterIntentPersistHook = nil

	var secondOut, secondErr bytes.Buffer
	secondCode := Run([]string{
		"cognition", "closeout", "apply",
		"--project-root", project,
		"--workflow", "sp-implement",
		"--scope-dir", scopeB,
		"--payload-json", closeoutApplyPayloadJSON(t, true),
		"--format", "json",
	}, &secondOut, &secondErr, "test")
	if secondCode != 0 {
		t.Fatalf("second code = %d; stderr=%s stdout=%s", secondCode, secondErr.String(), secondOut.String())
	}
	data := requireObject(t, decodeJSONObject(t, secondOut.Bytes()), "data")
	replayed, ok := data["replayed_intents"].([]any)
	if !ok || len(replayed) != 1 || countCloseoutApplyUpdates(t, paths) != 2 {
		t.Fatalf("data=%#v update-count=%d, want one older intent drained then current update", data, countCloseoutApplyUpdates(t, paths))
	}
	if _, err := os.Stat(filepath.Join(project, filepath.FromSlash(scopeA), mutationCognitionReceiptFileName)); err != nil {
		t.Fatalf("older scope receipt missing after automatic drain: %v", err)
	}
	intents, err := listCloseoutIntents(paths)
	if err != nil || len(intents) != 0 {
		t.Fatalf("intents = %#v err=%v, want queue drained", intents, err)
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

func countCloseoutApplyUpdates(t *testing.T, paths rt.Paths) int {
	t.Helper()
	st, err := store.OpenExisting(paths)
	if err != nil {
		t.Fatal(err)
	}
	defer st.Close()
	var count int
	if err := st.DB().QueryRowContext(context.Background(), `SELECT COUNT(*) FROM updates WHERE generation_id = 'GEN-closeout'`).Scan(&count); err != nil {
		t.Fatal(err)
	}
	return count
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
