package main

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"testing"

	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/delta"
	rt "github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/runtime"
	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/store"
)

func TestCloseoutPreflightRejectsEveryInvalidEvidenceBeforeIntent(t *testing.T) {
	for _, field := range []string{"verification", "verification_evidence"} {
		for _, invalid := range []map[string]string{{"result": "passed"}, {"command": "check"}, {"command": "check", "result": "success"}, {"command": "check", "result": "failed"}, {}} {
			t.Run(field+fmt.Sprint(invalid), func(t *testing.T) {
				project, paths, scope := seedCloseoutApplyRuntime(t)
				good := closeoutApplyPayloadJSON(t, true)
				closeoutRecoveryRunOK(t, project, "apply", "--workflow", "sp-implement", "--scope-dir", scope, "--payload-json", good)
				receiptPath := filepath.Join(project, filepath.FromSlash(scope), mutationCognitionReceiptFileName)
				before, err := os.ReadFile(receiptPath)
				if err != nil {
					t.Fatal(err)
				}
				var payload map[string]any
				if err := json.Unmarshal([]byte(good), &payload); err != nil {
					t.Fatal(err)
				}
				delete(payload, "verification")
				payload[field] = []map[string]string{{"command": "go test ./...", "result": "passed"}, invalid}
				raw, _ := json.Marshal(payload)
				code, data := closeoutRecoveryRun(t, project, "apply", "--workflow", "sp-implement", "--scope-dir", scope, "--payload-json", string(raw))
				if code == 0 || data["mutation_performed"] != false {
					t.Fatalf("invalid input must be rejected before mutation: code=%d data=%v", code, data)
				}
				intents, err := listCloseoutIntents(paths)
				if err != nil || len(intents) != 0 {
					t.Fatalf("invalid evidence left pending intents: count=%d err=%v", len(intents), err)
				}
				after, err := os.ReadFile(receiptPath)
				if err != nil || !bytes.Equal(before, after) || countCloseoutApplyUpdates(t, paths) != 1 {
					t.Fatalf("invalid input changed prior receipt or graph: err=%v", err)
				}
			})
		}
	}
}

func TestCloseoutPreflightRejectsInvalidDeltaEvidenceBeforeIntent(t *testing.T) {
	project, paths, scope := seedCloseoutApplyRuntime(t)
	session := appendCloseoutApplyDelta(t, paths, "sp-implement")
	if _, err := delta.Append(delta.AppendInput{RuntimeDir: paths.RuntimeDir, SessionID: session, EventType: "workflow_closeout", ChangedPaths: []string{"src/app.go"}, Verification: []string{`{"result":"recorded"}`}}); err != nil {
		t.Fatal(err)
	}
	code, data := closeoutRecoveryRun(t, project, "apply", "--workflow", "sp-implement", "--scope-dir", scope, "--delta-session", session)
	if code == 0 || data["mutation_performed"] != false {
		t.Fatalf("invalid delta must fail before mutation: code=%d data=%v", code, data)
	}
	intents, err := listCloseoutIntents(paths)
	if err != nil || len(intents) != 0 || countCloseoutApplyUpdates(t, paths) != 0 {
		t.Fatalf("invalid delta changed runtime: intents=%d err=%v", len(intents), err)
	}
}

func TestCloseoutRepairRecoversPoisonedIntentWithOlderSuccessfulReceipt(t *testing.T) {
	for _, laterScope := range []string{"same", "different"} {
		t.Run(laterScope, func(t *testing.T) {
			project, paths, scope := seedCloseoutApplyRuntime(t)
			good := closeoutApplyPayloadJSON(t, true)
			closeoutRecoveryRunOK(t, project, "apply", "--workflow", "sp-implement", "--scope-dir", ".", "--reason", "prior-completed-closeout", "--payload-json", good)
			old := seedMalformedCloseoutRecoveryIntent(t, paths, ".", "")
			currentScope := "."
			if laterScope == "different" {
				currentScope = scope
			}
			code, blocked := closeoutRecoveryRun(t, project, "apply", "--workflow", "sp-implement", "--scope-dir", currentScope, "--payload-json", good)
			if code == 0 || blocked["blocked_intent_id"] != old.ID || len(fmt.Sprint(blocked["recovery_argv"])) == 0 {
				t.Fatalf("missing exact recovery route: code=%d data=%v", code, blocked)
			}
			inspected := closeoutRecoveryRunOK(t, project, "inspect", "--intent-id", old.ID)
			if inspected["input_digest"] != old.InputDigest || inspected["repair_argv"] == nil {
				t.Fatalf("inspect did not offer bounded repair: %v", inspected)
			}
			repaired := closeoutRecoveryRunOK(t, project, "repair", "--intent-id", old.ID, "--expected-digest", old.InputDigest, "--verification-json", `[{"command":"go test ./...","result":"passed"}]`)
			id, _ := repaired["replacement_intent_id"].(string)
			digest, _ := repaired["replacement_input_digest"].(string)
			if id == "" || id == old.ID || len(digest) != 64 {
				t.Fatalf("repair did not bind replacement: %v", repaired)
			}
			if countCloseoutApplyUpdates(t, paths) != 1 {
				t.Fatal("repair must not submit or finalize graph updates")
			}
			repeated := closeoutRecoveryRunOK(t, project, "repair", "--intent-id", old.ID, "--expected-digest", old.InputDigest, "--verification-json", `[{"command":"go test ./...","result":"passed"}]`)
			if repeated["replacement_intent_id"] != id {
				t.Fatalf("repair is not idempotent: %v", repeated)
			}
			closeoutRecoveryRunOK(t, project, "replay", "--intent-id", id, "--expected-digest", digest)
			closeoutRecoveryRunOK(t, project, "apply", "--workflow", "sp-implement", "--scope-dir", currentScope, "--payload-json", good)
			if intents, err := listCloseoutIntents(paths); err != nil || len(intents) != 0 {
				t.Fatalf("queue did not recover: count=%d err=%v", len(intents), err)
			}
		})
	}
}

func TestCloseoutRepairPreservesFrozenDeltaSession(t *testing.T) {
	project, paths, scope := seedCloseoutApplyRuntime(t)
	session := appendCloseoutApplyDelta(t, paths, "sp-implement")
	if _, err := delta.Append(delta.AppendInput{RuntimeDir: paths.RuntimeDir, SessionID: session, EventType: "workflow_closeout", ChangedPaths: []string{"src/app.go"}, Verification: []string{`{"result":"recorded"}`}}); err != nil {
		t.Fatal(err)
	}
	old := seedMalformedCloseoutRecoveryIntent(t, paths, scope, session)
	before, err := closeoutDeltaDigest(paths, session)
	if err != nil {
		t.Fatal(err)
	}
	repaired := closeoutRecoveryRunOK(t, project, "repair", "--intent-id", old.ID, "--expected-digest", old.InputDigest, "--verification-json", `[{"command":"go test ./...","result":"passed"}]`)
	id := fmt.Sprint(repaired["replacement_intent_id"])
	closeoutRecoveryRunOK(t, project, "replay", "--intent-id", id, "--expected-digest", fmt.Sprint(repaired["replacement_input_digest"]))
	after, err := closeoutDeltaDigest(paths, session)
	if err != nil || before != after || countCloseoutApplyUpdates(t, paths) != 1 {
		t.Fatalf("repair changed delta or duplicated update: err=%v", err)
	}
}

func TestCloseoutRepairRejectsDigestMismatchAndCommittedIntent(t *testing.T) {
	project, paths, scope := seedCloseoutApplyRuntime(t)
	old := seedMalformedCloseoutRecoveryIntent(t, paths, scope, "")
	code, _ := closeoutRecoveryRun(t, project, "repair", "--intent-id", old.ID, "--expected-digest", strings.Repeat("0", 64), "--verification-json", `[{"command":"check","result":"passed"}]`)
	if code == 0 {
		t.Fatal("repair accepted a stale digest")
	}
	st, err := store.OpenExisting(paths)
	if err != nil {
		t.Fatal(err)
	}
	_, err = st.DB().ExecContext(context.Background(), `INSERT INTO updates (id,generation_id,trigger,changed_paths_json,affected_nodes_json,affected_claims_json,affected_slices_json,result_state,completed_at,attrs_json) VALUES (?,?,?,'[]','[]','[]','[]',?,?,?)`, "upd-already-committed", "GEN-closeout", "test", "ready", "2026-08-31T00:00:00Z", `{"closeout_intent_id":"`+old.ID+`"}`)
	if err != nil {
		st.Close()
		t.Fatal(err)
	}
	st.Close()
	code, _ = closeoutRecoveryRun(t, project, "repair", "--intent-id", old.ID, "--expected-digest", old.InputDigest, "--verification-json", `[{"command":"check","result":"passed"}]`)
	if code == 0 {
		t.Fatal("repair rewrote an intent whose update committed before intent state advanced")
	}
	intents, err := listCloseoutIntents(paths)
	if err != nil || len(intents) != 1 || intents[0].InputDigest != old.InputDigest {
		t.Fatalf("rejected repair mutated original: %v", err)
	}
}

func TestCloseoutDirectReplayDoesNotRequireBlockedReceipt(t *testing.T) {
	project, paths, scope := seedCloseoutApplyRuntime(t)
	intent, _, _, err := ensureCloseoutIntent(paths, "sp-implement", scope, "workflow-finalize", closeoutApplyPayloadJSON(t, true), "", "", []string{"src/app.go"})
	if err != nil {
		t.Fatal(err)
	}
	data := closeoutRecoveryRunOK(t, project, "replay", "--intent-id", intent.ID, "--expected-digest", intent.InputDigest)
	if data["allowed_close"] != true || countCloseoutApplyUpdates(t, paths) != 1 {
		t.Fatalf("exact replay did not finish bound intent: %v", data)
	}
}

func TestCloseoutDirectReplayIgnoresUnrelatedCorruptIntent(t *testing.T) {
	project, paths, scope := seedCloseoutApplyRuntime(t)
	intent, _, _, err := ensureCloseoutIntent(paths, "sp-implement", scope, "workflow-finalize", closeoutApplyPayloadJSON(t, true), "", "", []string{"src/app.go"})
	if err != nil {
		t.Fatal(err)
	}
	other := "intent-" + strings.Repeat("a", 24)
	if err := os.WriteFile(closeoutIntentPath(paths, other), []byte("{invalid"), 0o644); err != nil {
		t.Fatal(err)
	}
	data := closeoutRecoveryRunOK(t, project, "replay", "--intent-id", intent.ID, "--expected-digest", intent.InputDigest)
	if data["allowed_close"] != true {
		t.Fatalf("selected recovery was obstructed by unrelated input: %v", data)
	}
	if _, err := os.Stat(closeoutIntentPath(paths, other)); err != nil {
		t.Fatal("unrelated intent must remain untouched")
	}
	if countCloseoutApplyUpdates(t, paths) != 1 {
		t.Fatal("replay updated more than its selected input")
	}
}

func TestCloseoutRepairPublicationSurvivesEveryCrashBoundary(t *testing.T) {
	for _, point := range []string{"journal", "replacement", "original-removal"} {
		t.Run(point, func(t *testing.T) {
			project, paths, scope := seedCloseoutApplyRuntime(t)
			old := seedMalformedCloseoutRecoveryIntent(t, paths, scope, "")
			fail := func() error { return errors.New("injected repair interruption") }
			switch point {
			case "journal":
				closeoutRepairAfterJournalHook = fail
			case "replacement":
				closeoutRepairAfterReplacementHook = fail
			case "original-removal":
				closeoutRepairAfterOriginalRemovalHook = fail
			}
			reset := func() {
				closeoutRepairAfterJournalHook = nil
				closeoutRepairAfterReplacementHook = nil
				closeoutRepairAfterOriginalRemovalHook = nil
			}
			t.Cleanup(reset)
			code, _ := closeoutRecoveryRun(t, project, "repair", "--intent-id", old.ID, "--expected-digest", old.InputDigest, "--verification-json", `[{"command":"go test ./...","result":"passed"}]`)
			if code == 0 {
				t.Fatal("injected interruption did not stop repair")
			}
			reset()
			data := closeoutRecoveryRunOK(t, project, "repair", "--intent-id", old.ID, "--expected-digest", old.InputDigest)
			closeoutRecoveryRunOK(t, project, "replay", "--intent-id", fmt.Sprint(data["replacement_intent_id"]), "--expected-digest", fmt.Sprint(data["replacement_input_digest"]))
			closeoutRecoveryRunOK(t, project, "repair", "--intent-id", old.ID, "--expected-digest", old.InputDigest)
			if intents, err := listCloseoutIntents(paths); err != nil || len(intents) != 0 || countCloseoutApplyUpdates(t, paths) != 1 {
				t.Fatalf("repair resurrected or duplicated an update: intents=%d err=%v", len(intents), err)
			}
		})
	}
}

func TestCloseoutApplyCompletesDurableRepairBeforeDrainingQueue(t *testing.T) {
	project, paths, scope := seedCloseoutApplyRuntime(t)
	old := seedMalformedCloseoutRecoveryIntent(t, paths, scope, "")
	closeoutRepairAfterReplacementHook = func() error { return errors.New("crash with both intents published") }
	t.Cleanup(func() { closeoutRepairAfterReplacementHook = nil })
	code, _ := closeoutRecoveryRun(t, project, "repair", "--intent-id", old.ID, "--expected-digest", old.InputDigest, "--verification-json", `[{"command":"go test ./...","result":"passed"}]`)
	if code == 0 {
		t.Fatal("repair should have been interrupted")
	}
	closeoutRepairAfterReplacementHook = nil
	closeoutRecoveryRunOK(t, project, "apply", "--workflow", "sp-implement", "--scope-dir", ".", "--payload-json", closeoutApplyPayloadJSON(t, true))
	if intents, err := listCloseoutIntents(paths); err != nil || len(intents) != 0 || countCloseoutApplyUpdates(t, paths) != 2 {
		t.Fatalf("ordinary apply did not finish repair publication: count=%d err=%v", len(intents), err)
	}
}

func TestCloseoutDeltaChangeAfterPreflightCannotPersistUncheckedIntent(t *testing.T) {
	project, paths, scope := seedCloseoutApplyRuntime(t)
	session := appendCloseoutApplyDelta(t, paths, "sp-implement")
	closeoutApplyAfterPreflightHook = func() error {
		_, err := delta.Append(delta.AppendInput{RuntimeDir: paths.RuntimeDir, SessionID: session, EventType: "workflow_closeout", ChangedPaths: []string{"src/app.go"}, Verification: []string{`{"result":"passed"}`}})
		return err
	}
	t.Cleanup(func() { closeoutApplyAfterPreflightHook = nil })
	code, data := closeoutRecoveryRun(t, project, "apply", "--workflow", "sp-implement", "--scope-dir", scope, "--delta-session", session)
	if code == 0 || data["mutation_performed"] != false {
		t.Fatalf("unchecked delta was admitted: %d %v", code, data)
	}
	if intents, err := listCloseoutIntents(paths); err != nil || len(intents) != 0 || countCloseoutApplyUpdates(t, paths) != 0 {
		t.Fatalf("raced delta left a durable intent: count=%d err=%v", len(intents), err)
	}
}

func TestCloseoutReplayCannotResubmitIntentCommittedInOlderGeneration(t *testing.T) {
	project, paths, scope := seedCloseoutApplyRuntime(t)
	intent, _, _, err := ensureCloseoutIntent(paths, "sp-implement", scope, "workflow-finalize", closeoutApplyPayloadJSON(t, true), "", "", []string{"src/app.go"})
	if err != nil {
		t.Fatal(err)
	}
	st, err := store.OpenExisting(paths)
	if err != nil {
		t.Fatal(err)
	}
	_, err = st.DB().ExecContext(context.Background(), `INSERT INTO updates (id,generation_id,trigger,changed_paths_json,affected_nodes_json,affected_claims_json,affected_slices_json,result_state,completed_at,attrs_json) VALUES (?,?,?,'[]','[]','[]','[]',?,?,?)`, "upd-old-generation", "GEN-closeout", "test", "ready", "2026-08-31T00:00:00Z", `{"closeout_intent_id":"`+intent.ID+`"}`)
	if err != nil {
		st.Close()
		t.Fatal(err)
	}
	_, err = st.ImportGeneration(context.Background(), store.ImportInput{
		GenerationID: "GEN-new", Kind: "full", SourceCommit: "newcommit",
		Evidence:  []store.EvidenceImport{{ID: "E-new", SourceKind: "file", SourcePath: "src/app.go", CommitSHA: "newcommit", Extractor: "test", ContentHash: "hash"}},
		Nodes:     []store.NodeImport{{ID: "N-new", Type: "capability", Title: "App", Confidence: "verified", EvidenceIDs: []string{"E-new"}}},
		PathIndex: []store.PathIndexImport{{ID: "P-new", Path: "src/app.go", NodeID: "N-new", Relation: "owns", Confidence: "verified", EvidenceID: "E-new"}},
		Aliases:   []store.AliasImport{{ID: "A-new", Alias: "App", NormalizedAlias: "app", TargetType: "node", TargetID: "N-new", Source: "node_title", Confidence: "verified", EvidenceID: "E-new"}},
	})
	if err != nil {
		st.Close()
		t.Fatal(err)
	}
	if _, _, err = st.PublishRuntimeMetadata(context.Background(), "GEN-new", rt.BaselineKindBrownfieldFull); err != nil {
		st.Close()
		t.Fatal(err)
	}
	st.Close()
	status := rt.DefaultStatus(paths)
	status.Status, status.Freshness, status.Readiness = "ok", rt.ReadyFreshness, rt.ReadyReadiness
	status.RecommendedNextAction, status.GraphReady, status.ActiveGenerationID, status.BaselineKind = "use_project_cognition", true, "GEN-new", rt.BaselineKindBrownfieldFull
	if err := rt.WriteStatus(paths, status); err != nil {
		t.Fatal(err)
	}
	inspected := closeoutRecoveryRunOK(t, project, "inspect", "--intent-id", intent.ID)
	if inspected["replay_argv"] != nil {
		t.Fatalf("inspect recommends replaying an older committed generation: %v", inspected)
	}
	code, data := closeoutRecoveryRun(t, project, "replay", "--intent-id", intent.ID, "--expected-digest", intent.InputDigest)
	if code == 0 || !strings.Contains(fmt.Sprint(data["error"]), "generation") {
		t.Fatalf("replay admitted an already committed older-generation intent: code=%d data=%v", code, data)
	}
	st, err = store.OpenExisting(paths)
	if err != nil {
		t.Fatal(err)
	}
	defer st.Close()
	var count int
	if err := st.DB().QueryRowContext(context.Background(), `SELECT COUNT(*) FROM updates WHERE generation_id='GEN-new'`).Scan(&count); err != nil {
		t.Fatal(err)
	}
	if count != 0 {
		t.Fatalf("old intent was submitted %d times into rebuilt graph", count)
	}
}

func TestCloseoutPreflightRejectsInvalidCommitRangeBeforeIntent(t *testing.T) {
	for _, commitRange := range []string{"not-a-range", "missing-ref-a..missing-ref-b"} {
		t.Run(commitRange, func(t *testing.T) {
			project, paths, scope := seedCloseoutApplyRuntime(t)
			session := appendCloseoutApplyDelta(t, paths, "sp-implement")
			code, data := closeoutRecoveryRun(t, project, "apply", "--workflow", "sp-implement", "--scope-dir", scope, "--delta-session", session, "--commit-range", commitRange)
			if code == 0 || data["mutation_performed"] != false {
				t.Fatalf("invalid commit range admitted: %d %v", code, data)
			}
			if intents, err := listCloseoutIntents(paths); err != nil || len(intents) != 0 || countCloseoutApplyUpdates(t, paths) != 0 {
				t.Fatalf("invalid range left a poisoned intent: %d %v", len(intents), err)
			}
		})
	}
}

func TestCloseoutAutomaticReplayRequiresRepairLineage(t *testing.T) {
	project, paths, scope := seedCloseoutApplyRuntime(t)
	old := seedMalformedCloseoutRecoveryIntent(t, paths, scope, "")
	repaired := closeoutRecoveryRunOK(t, project, "repair", "--intent-id", old.ID, "--expected-digest", old.InputDigest, "--verification-json", `[{"command":"check","result":"passed"}]`)
	if err := os.Remove(closeoutRepairPath(paths, old.ID)); err != nil {
		t.Fatal(err)
	}
	_, inspected := closeoutRecoveryRun(t, project, "inspect", "--intent-id", fmt.Sprint(repaired["replacement_intent_id"]))
	if inspected["replay_argv"] != nil {
		t.Fatal("inspect recommends an impossible replay when repair lineage is missing")
	}
	code, _ := closeoutRecoveryRun(t, project, "apply", "--workflow", "sp-implement", "--scope-dir", ".", "--payload-json", closeoutApplyPayloadJSON(t, true))
	if code == 0 || countCloseoutApplyUpdates(t, paths) != 0 {
		t.Fatal("automatic replay bypassed repaired-intent lineage checks")
	}
}

func TestCloseoutAutomaticReplayRejectsFailedEvidenceBeforeSubmission(t *testing.T) {
	project, paths, scope := seedCloseoutApplyRuntime(t)
	var payload map[string]any
	json.Unmarshal([]byte(closeoutApplyPayloadJSON(t, true)), &payload)
	payload["verification"] = []map[string]string{{"command": "ok-check", "result": "passed"}, {"command": "bad-check", "result": "failed"}}
	raw, _ := json.Marshal(payload)
	old, _, _, err := ensureCloseoutIntent(paths, "sp-implement", scope, "workflow-finalize", string(raw), "", "", []string{"src/app.go"})
	if err != nil {
		t.Fatal(err)
	}
	code, _ := closeoutRecoveryRun(t, project, "apply", "--workflow", "sp-implement", "--scope-dir", ".", "--payload-json", closeoutApplyPayloadJSON(t, true))
	if code == 0 || countCloseoutApplyUpdates(t, paths) != 0 {
		t.Fatal("automatic replay submitted failed evidence before validating it")
	}
	closeoutRecoveryRunOK(t, project, "repair", "--intent-id", old.ID, "--expected-digest", old.InputDigest, "--verification-json", `[{"command":"fixed-check","result":"passed"}]`)
}

func TestCloseoutReplayFailureDoesNotClaimNoMutationAfterCommit(t *testing.T) {
	project, paths, scope := seedCloseoutApplyRuntime(t)
	intent, _, _, err := ensureCloseoutIntent(paths, "sp-implement", scope, "workflow-finalize", closeoutApplyPayloadJSON(t, true), "", "", []string{"src/app.go"})
	if err != nil {
		t.Fatal(err)
	}
	closeoutApplyAfterReplayedScopeReceiptHook = func(string) error { return errors.New("injected failure after durable scope receipt") }
	t.Cleanup(func() { closeoutApplyAfterReplayedScopeReceiptHook = nil })
	code, data := closeoutRecoveryRun(t, project, "replay", "--intent-id", intent.ID, "--expected-digest", intent.InputDigest)
	if code == 0 || countCloseoutApplyUpdates(t, paths) != 1 {
		t.Fatalf("expected failure after commit: %d %v", code, data)
	}
	if data["graph_mutation_performed"] == false {
		t.Fatal("post-commit replay failure falsely denied recorded graph mutation")
	}
}

func TestCloseoutInspectIsReadOnlyAndRepairCannotFork(t *testing.T) {
	project, paths, scope := seedCloseoutApplyRuntime(t)
	old := seedMalformedCloseoutRecoveryIntent(t, paths, scope, "")
	snapshot := func() map[string]string {
		files := map[string]string{}
		err := filepath.WalkDir(paths.RuntimeDir, func(path string, entry os.DirEntry, err error) error {
			if err != nil {
				return err
			}
			if !entry.IsDir() {
				raw, err := os.ReadFile(path)
				if err != nil {
					return err
				}
				files[path] = string(raw)
			}
			return nil
		})
		if err != nil {
			t.Fatal(err)
		}
		return files
	}
	before, _ := json.Marshal(snapshot())
	closeoutRecoveryRunOK(t, project, "inspect")
	closeoutRecoveryRunOK(t, project, "inspect", "--intent-id", old.ID)
	after, _ := json.Marshal(snapshot())
	if !bytes.Equal(before, after) {
		t.Fatal("inspect changed runtime files")
	}
	type outcome struct {
		code int
		data map[string]any
	}
	outcomes := make(chan outcome, 2)
	var workers sync.WaitGroup
	for _, command := range []string{"first-actual-check", "second-actual-check"} {
		workers.Add(1)
		go func(command string) {
			defer workers.Done()
			raw, _ := json.Marshal([]map[string]string{{"command": command, "result": "passed"}})
			code, data := closeoutRecoveryRun(t, project, "repair", "--intent-id", old.ID, "--expected-digest", old.InputDigest, "--verification-json", string(raw))
			outcomes <- outcome{code: code, data: data}
		}(command)
	}
	workers.Wait()
	close(outcomes)
	passed, blocked := 0, 0
	for outcome := range outcomes {
		if outcome.code == 0 {
			passed++
		} else {
			blocked++
		}
	}
	if passed != 1 || blocked != 1 {
		t.Fatalf("concurrent repair forked or lost its winner: passed=%d blocked=%d", passed, blocked)
	}
	intents, err := listCloseoutIntents(paths)
	if err != nil || len(intents) != 1 || intents[0].RepairsIntentID != old.ID {
		t.Fatalf("unexpected repair successors: %d %v", len(intents), err)
	}
}

func seedMalformedCloseoutRecoveryIntent(t *testing.T, paths rt.Paths, scope, session string) closeoutIntent {
	t.Helper()
	payload := ""
	if session == "" {
		var value map[string]any
		if err := json.Unmarshal([]byte(closeoutApplyPayloadJSON(t, true)), &value); err != nil {
			t.Fatal(err)
		}
		value["verification"] = []map[string]string{{"command": "go test ./...", "result": "passed"}, {"result": "recorded"}}
		value["semantic_extension"] = map[string]string{"preserve": "unknown fields must survive repair"}
		raw, _ := json.Marshal(value)
		payload = string(raw)
	}
	intent, _, _, err := ensureCloseoutIntent(paths, "sp-implement", scope, "workflow-finalize", payload, session, "", []string{"src/app.go"})
	if err != nil {
		t.Fatal(err)
	}
	return intent
}

func closeoutRecoveryRun(t *testing.T, project string, args ...string) (int, map[string]any) {
	t.Helper()
	var stdout, stderr bytes.Buffer
	argv := append([]string{"cognition", "closeout"}, args...)
	argv = append(argv, "--project-root", project, "--format", "json")
	code := Run(argv, &stdout, &stderr, "test")
	var envelope map[string]any
	if err := json.Unmarshal(stdout.Bytes(), &envelope); err != nil {
		t.Fatalf("expected structured result: code=%d stdout=%s stderr=%s", code, stdout.String(), stderr.String())
	}
	data, _ := envelope["data"].(map[string]any)
	if data == nil {
		data = map[string]any{}
	}
	return code, data
}

func closeoutRecoveryRunOK(t *testing.T, project string, args ...string) map[string]any {
	t.Helper()
	code, data := closeoutRecoveryRun(t, project, args...)
	if code != 0 {
		t.Fatalf("closeout %v failed: code=%d data=%v", args, code, data)
	}
	return data
}
