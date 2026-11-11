package main

import (
	"bytes"
	"context"
	"database/sql"
	"errors"
	"os"
	"path/filepath"
	"reflect"
	"strings"
	"testing"

	rt "github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/runtime"
	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/store"
)

func TestMutationCloseoutRecoveryInspectsIncompatibleGraphWithoutMutation(t *testing.T) {
	project, paths, scope := seedCloseoutApplyRuntime(t)
	absolute := filepath.Join(project, filepath.FromSlash(scope))
	intent, _, _, err := ensureCloseoutIntent(paths, "sp-quick", scope, "legacy-recovery", closeoutApplyPayloadJSON(t, true), "", "", []string{"src/app.go"})
	if err != nil {
		t.Fatal(err)
	}
	db, err := sql.Open("sqlite", paths.DatabasePath)
	if err != nil {
		t.Fatal(err)
	}
	if _, err := db.Exec("UPDATE metadata SET value_json = '2' WHERE key = 'schema_version'"); err != nil {
		db.Close()
		t.Fatal(err)
	}
	if err := db.Close(); err != nil {
		t.Fatal(err)
	}
	before, err := os.ReadFile(paths.DatabasePath)
	if err != nil {
		t.Fatal(err)
	}
	if argv := mutationCognitionRecoveryArgv(absolute, "sp-quick", []string{"src/app.go"}); !reflect.DeepEqual(argv, closeoutRecoveryArgv(paths, "inspect", intent.ID, "")) {
		t.Fatalf("incompatible graph bypassed its pending intent: %#v", argv)
	}
	if err := os.Remove(closeoutIntentPath(paths, intent.ID)); err != nil {
		t.Fatal(err)
	}
	argv := mutationCognitionRecoveryArgv(absolute, "sp-quick", []string{"src/app.go"})
	want := []string{"specify-runtime", "cognition", "archive-incompatible-store", "--inspect", "--format", "json"}
	if !reflect.DeepEqual(argv, want) {
		t.Fatalf("incompatible graph retries the blocked planner: %#v", argv)
	}
	if text := mutationCognitionRecoveryText(absolute, "sp-quick", nil); !strings.Contains(text, "--inspect") || strings.Contains(text, "consume exact inspect repair_argv") {
		t.Fatalf("wrong incompatible graph recovery: %s", text)
	}
	previousDir, err := os.Getwd()
	if err != nil {
		t.Fatal(err)
	}
	if err := os.Chdir(project); err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { _ = os.Chdir(previousDir) })
	var stdout, stderr bytes.Buffer
	if code := Run(argv[1:], &stdout, &stderr, "legacy-recovery"); code != 0 || !strings.Contains(stdout.String(), "\"status\":\"inspected\"") {
		t.Fatalf("returned recovery is not executable: code=%d stdout=%s stderr=%s", code, stdout.String(), stderr.String())
	}
	after, err := os.ReadFile(paths.DatabasePath)
	if err != nil || !bytes.Equal(before, after) {
		t.Fatalf("recovery lookup changed the incompatible database: %v", err)
	}
}

func TestR1RetainedCommittedIntentCannotHideNewPendingIntent(t *testing.T) {
	project, paths, scope := seedCloseoutApplyRuntime(t)
	absolute := filepath.Join(project, filepath.FromSlash(scope))
	closeoutApplyAfterScopeReceiptHook = func(string) error {
		return errors.New("interrupt after old committed receipt before pruning its intent")
	}
	t.Cleanup(func() {
		closeoutApplyAfterScopeReceiptHook = nil
		closeoutApplyAfterIntentPersistHook = nil
	})
	apply := func(reason string) int {
		var out, stderr bytes.Buffer
		code := Run([]string{"cognition", "closeout", "apply", "--project-root", project, "--workflow", "sp-implement", "--scope-dir", scope, "--reason", reason, "--payload-json", closeoutApplyPayloadJSON(t, true), "--format", "json"}, &out, &stderr, "r1-retained-intent")
		t.Logf("native apply reason=%s exit=%d stdout=%s stderr=%s", reason, code, out.String(), stderr.String())
		return code
	}
	if code := apply("r1-old-committed"); code != 10 {
		t.Fatalf("old receipt interruption exit=%d", code)
	}
	closeoutApplyAfterScopeReceiptHook = nil
	oldReceipt, err := loadMutationCognitionReceipt(absolute)
	if err != nil || oldReceipt == nil || oldReceipt.IntentID == "" || oldReceipt.UpdateID == "" {
		t.Fatalf("missing real committed receipt: %#v %v", oldReceipt, err)
	}
	closeoutApplyAfterIntentPersistHook = func(string) error {
		return errors.New("interrupt after same-scope new durable intent")
	}
	if code := apply("r1-new-pending"); code != 10 {
		t.Fatalf("new intent interruption exit=%d", code)
	}
	closeoutApplyAfterIntentPersistHook = nil
	gate := mutationCognitionStatus(absolute)
	t.Logf("retained committed receipt gate=%v", gate)
	if gate["allowed_close"] == true || gate["blocked_reason"] != "pending_closeout_intent_requires_replay" {
		t.Fatalf("old bound intent hid the new same-scope intent: %#v", gate)
	}
	intents, err := listCloseoutIntents(paths)
	if err != nil || len(intents) != 2 || countCloseoutApplyUpdates(t, paths) != 1 {
		t.Fatalf("real interruption state: intents=%#v err=%v", intents, err)
	}
	var newer closeoutIntent
	for _, intent := range intents {
		if intent.ID != oldReceipt.IntentID {
			newer = intent
		}
	}
	oldReceiptBytes, _ := os.ReadFile(mutationCognitionReceiptPath(absolute))
	newIntentBytes, _ := os.ReadFile(closeoutIntentPath(paths, newer.ID))
	var refusal, stderr bytes.Buffer
	if code := Run([]string{"cognition", "mutation-receipt", "--project-root", project, "--workflow", "sp-implement", "--scope-dir", scope, "--result-state", "mark-dirty", "--reason", "cannot hide newer pending intent", "--format", "json"}, &refusal, &stderr, "r1-retained-intent"); code != 10 {
		t.Fatalf("standalone refused exit=%d output=%s", code, refusal.String())
	}
	afterReceiptBytes, _ := os.ReadFile(mutationCognitionReceiptPath(absolute))
	afterIntentBytes, _ := os.ReadFile(closeoutIntentPath(paths, newer.ID))
	if !bytes.Equal(oldReceiptBytes, afterReceiptBytes) || !bytes.Equal(newIntentBytes, afterIntentBytes) {
		t.Fatal("standalone refusal changed receipt or new durable intent")
	}
	// Replay the retained committed owner first. It only prunes its completed
	// intent and must not release the scope while the new owner remains pending.
	for index, want := range []string{oldReceipt.IntentID, newer.ID} {
		argv := mutationCognitionRecoveryArgv(absolute, "sp-implement", nil)
		if !reflect.DeepEqual(argv, closeoutRecoveryArgv(paths, "inspect", want, "")) {
			t.Fatalf("recovery step %d selected incorrect owner: %#v", index, argv)
		}
		var out bytes.Buffer
		if code := Run(argv[1:], &out, &stderr, "r1-retained-inspect"); code != 0 {
			t.Fatalf("inspect step %d exit=%d output=%s", index, code, out.String())
		}
		data := requireObject(t, decodeJSONObject(t, out.Bytes()), "data")
		replay := anyStringSlice(data["replay_argv"])
		if len(replay) == 0 {
			t.Fatalf("inspect did not supply exact replay: %#v", data)
		}
		out.Reset()
		if code := Run(replay[1:], &out, &stderr, "r1-retained-replay"); code != 0 {
			t.Fatalf("replay step %d exit=%d output=%s", index, code, out.String())
		}
		data = requireObject(t, decodeJSONObject(t, out.Bytes()), "data")
		t.Logf("native exact replay step=%d output=%s", index, out.String())
		if index == 0 && (data["allowed_close"] == true || countCloseoutApplyUpdates(t, paths) != 1) {
			t.Fatalf("old committed cleanup released new owner or resubmitted update: %#v", data)
		}
	}
	if gate := mutationCognitionStatus(absolute); gate["allowed_close"] != true || countCloseoutApplyUpdates(t, paths) != 2 {
		t.Fatalf("exact recovery did not finish both owners once: %#v", gate)
	}
	intents, err = listCloseoutIntents(paths)
	if err != nil || len(intents) != 0 {
		t.Fatalf("recovery left pending owners: %#v %v", intents, err)
	}
}

func TestR1SameScopePendingIntentQueueStillRecovers(t *testing.T) {
	project, paths, scope := seedCloseoutApplyRuntime(t)
	absolute := filepath.Join(project, filepath.FromSlash(scope))
	closeoutApplyAfterIntentPersistHook = func(string) error {
		return errors.New("interrupt before first queued scope update")
	}
	t.Cleanup(func() { closeoutApplyAfterIntentPersistHook = nil })
	var out, stderr bytes.Buffer
	args := []string{"cognition", "closeout", "apply", "--project-root", project, "--workflow", "sp-implement", "--scope-dir", scope, "--reason", "r1-first-queued", "--payload-json", closeoutApplyPayloadJSON(t, true), "--format", "json"}
	if code := Run(args, &out, &stderr, "r1-same-scope-queue"); code != 10 {
		t.Fatalf("first pending exit=%d output=%s", code, out.String())
	}
	closeoutApplyAfterIntentPersistHook = nil
	for index := range args {
		if args[index] == "--reason" {
			args[index+1] = "r1-second-queued"
		}
	}
	out.Reset()
	code := Run(args, &out, &stderr, "r1-same-scope-queue")
	t.Logf("native same-scope drain exit=%d stdout=%s stderr=%s", code, out.String(), stderr.String())
	if code != 0 || mutationCognitionStatus(absolute)["allowed_close"] != true || countCloseoutApplyUpdates(t, paths) != 2 {
		t.Fatalf("same-scope recovery blocked after gate repair: exit=%d output=%s", code, out.String())
	}
	intents, err := listCloseoutIntents(paths)
	if err != nil || len(intents) != 0 {
		t.Fatalf("same-scope drain left pending owners: %#v %v", intents, err)
	}
}

func TestR1SameScopePendingIntentsReplayBothOrders(t *testing.T) {
	for _, order := range []string{"older-first", "newer-first"} {
		t.Run(order, func(t *testing.T) {
			project, paths, scope := seedCloseoutApplyRuntime(t)
			absolute := filepath.Join(project, filepath.FromSlash(scope))
			closeoutApplyAfterIntentPersistHook = func(string) error {
				return errors.New("leave two same-scope intents before either commits")
			}
			t.Cleanup(func() { closeoutApplyAfterIntentPersistHook = nil })
			for _, reason := range []string{"r1-pending-A", "r1-pending-B"} {
				var out, stderr bytes.Buffer
				if code := Run([]string{"cognition", "closeout", "apply", "--project-root", project, "--workflow", "sp-implement", "--scope-dir", scope, "--reason", reason, "--payload-json", closeoutApplyPayloadJSON(t, true), "--format", "json"}, &out, &stderr, "r1-replay-order"); code != 10 {
					t.Fatalf("persist reason=%s exit=%d output=%s", reason, code, out.String())
				}
			}
			closeoutApplyAfterIntentPersistHook = nil
			intents, err := listCloseoutIntents(paths)
			if err != nil || len(intents) != 2 || countCloseoutApplyUpdates(t, paths) != 0 {
				t.Fatalf("pending inputs were not both uncommitted: %#v %v", intents, err)
			}
			if order == "older-first" {
				before, err := os.ReadFile(closeoutIntentPath(paths, intents[0].ID))
				if err != nil {
					t.Fatal(err)
				}
				wrongDigest := closeoutRecoveryArgv(paths, "replay", intents[0].ID, strings.Repeat("0", 64))
				foreignScope := append(closeoutRecoveryArgv(paths, "replay", intents[0].ID, intents[0].InputDigest), "--scope-dir", ".specify/features/foreign")
				for _, argv := range [][]string{wrongDigest, foreignScope} {
					var out, stderr bytes.Buffer
					code := Run(argv[1:], &out, &stderr, "r1-queue-refusal")
					t.Logf("native queue refusal exit=%d argv=%v stdout=%s", code, argv, out.String())
					if code != 10 || countCloseoutApplyUpdates(t, paths) != 0 {
						t.Fatalf("invalid binding mutated queue: exit=%d output=%s", code, out.String())
					}
					after, _ := os.ReadFile(closeoutIntentPath(paths, intents[0].ID))
					if !bytes.Equal(before, after) {
						t.Fatal("invalid binding changed pending owner")
					}
				}
			}
			if order == "newer-first" {
				intents[0], intents[1] = intents[1], intents[0]
			}
			for index, intent := range intents {
				var out, stderr bytes.Buffer
				if code := Run(closeoutRecoveryArgv(paths, "inspect", intent.ID, "")[1:], &out, &stderr, "r1-order-inspect"); code != 0 {
					t.Fatalf("inspect step=%d exit=%d output=%s", index, code, out.String())
				}
				data := requireObject(t, decodeJSONObject(t, out.Bytes()), "data")
				argv := anyStringSlice(data["replay_argv"])
				if len(argv) == 0 {
					t.Fatalf("inspect has no exact replay: %#v", data)
				}
				out.Reset()
				if code := Run(argv[1:], &out, &stderr, "r1-order-replay"); code != 0 {
					t.Fatalf("replay step=%d exit=%d output=%s", index, code, out.String())
				}
				data = requireObject(t, decodeJSONObject(t, out.Bytes()), "data")
				t.Logf("native exact replay order=%s step=%d output=%s", order, index, out.String())
				if index == 0 && (data["allowed_close"] == true || mutationCognitionStatus(absolute)["allowed_close"] == true) {
					t.Fatal("first replay released the scope before the other pending owner")
				}
				if count := countCloseoutApplyUpdates(t, paths); count != index+1 {
					t.Fatalf("step=%d update count=%d", index, count)
				}
			}
			if gate := mutationCognitionStatus(absolute); gate["allowed_close"] != true {
				t.Fatalf("both exact owners completed but scope remains blocked: %#v", gate)
			}
			if remaining, err := listCloseoutIntents(paths); err != nil || len(remaining) != 0 {
				t.Fatalf("exact queue left pending records: %#v %v", remaining, err)
			}
		})
	}
}

func TestR1RetainedCommittedIntentNewerReplayFirstStillBlocks(t *testing.T) {
	project, paths, scope := seedCloseoutApplyRuntime(t)
	absolute := filepath.Join(project, filepath.FromSlash(scope))
	closeoutApplyAfterScopeReceiptHook = func(string) error { return errors.New("retain committed old owner") }
	t.Cleanup(func() {
		closeoutApplyAfterScopeReceiptHook = nil
		closeoutApplyAfterIntentPersistHook = nil
	})
	var out, stderr bytes.Buffer
	args := []string{"cognition", "closeout", "apply", "--project-root", project, "--workflow", "sp-implement", "--scope-dir", scope, "--reason", "r1-retained-old", "--payload-json", closeoutApplyPayloadJSON(t, true), "--format", "json"}
	if code := Run(args, &out, &stderr, "r1-newer-first"); code != 10 {
		t.Fatalf("old interruption exit=%d output=%s", code, out.String())
	}
	closeoutApplyAfterScopeReceiptHook = nil
	oldReceipt, err := loadMutationCognitionReceipt(absolute)
	if err != nil || oldReceipt == nil {
		t.Fatalf("old receipt: %#v %v", oldReceipt, err)
	}
	closeoutApplyAfterIntentPersistHook = func(string) error { return errors.New("retain new pending owner") }
	for index := range args {
		if args[index] == "--reason" {
			args[index+1] = "r1-retained-newer"
		}
	}
	out.Reset()
	if code := Run(args, &out, &stderr, "r1-newer-first"); code != 10 {
		t.Fatalf("new interruption exit=%d output=%s", code, out.String())
	}
	closeoutApplyAfterIntentPersistHook = nil
	intents, err := listCloseoutIntents(paths)
	if err != nil || len(intents) != 2 {
		t.Fatalf("two retained owners: %#v %v", intents, err)
	}
	var newer closeoutIntent
	for _, intent := range intents {
		if intent.ID != oldReceipt.IntentID {
			newer = intent
		}
	}
	var laterReceiptBytes []byte
	for index, id := range []string{newer.ID, oldReceipt.IntentID} {
		out.Reset()
		if code := Run(closeoutRecoveryArgv(paths, "inspect", id, "")[1:], &out, &stderr, "r1-newer-first-inspect"); code != 0 {
			t.Fatalf("inspect step=%d exit=%d output=%s", index, code, out.String())
		}
		data := requireObject(t, decodeJSONObject(t, out.Bytes()), "data")
		argv := anyStringSlice(data["replay_argv"])
		if len(argv) == 0 {
			t.Fatalf("missing exact replay: %#v", data)
		}
		out.Reset()
		if code := Run(argv[1:], &out, &stderr, "r1-newer-first-replay"); code != 0 {
			t.Fatalf("replay step=%d exit=%d output=%s", index, code, out.String())
		}
		data = requireObject(t, decodeJSONObject(t, out.Bytes()), "data")
		t.Logf("native retained newer-first step=%d output=%s", index, out.String())
		if index == 0 && (data["allowed_close"] == true || mutationCognitionStatus(absolute)["allowed_close"] == true) {
			t.Fatal("newer replay silently hid retained older recovery owner")
		}
		if countCloseoutApplyUpdates(t, paths) != 2 {
			t.Fatal("replaying an already committed old intent resubmitted its update")
		}
		if index == 0 {
			laterReceiptBytes, _ = os.ReadFile(mutationCognitionReceiptPath(absolute))
		} else if actual, _ := os.ReadFile(mutationCognitionReceiptPath(absolute)); !bytes.Equal(laterReceiptBytes, actual) {
			t.Fatal("pruning older completion replaced the current later receipt")
		}
	}
	if gate := mutationCognitionStatus(absolute); gate["allowed_close"] != true {
		t.Fatalf("retained queue was not recovered: %#v", gate)
	}
}

func r1SeedSupersededScopeReceipt(t *testing.T) (string, rt.Paths, string, closeoutIntent) {
	t.Helper()
	project, paths, scope := seedCloseoutApplyRuntime(t)
	absolute := filepath.Join(project, filepath.FromSlash(scope))
	closeoutApplyAfterScopeReceiptHook = func(string) error { return errors.New("retain completed intent for guarded prune") }
	t.Cleanup(func() { closeoutApplyAfterScopeReceiptHook = nil })
	var out, stderr bytes.Buffer
	args := []string{"cognition", "closeout", "apply", "--project-root", project, "--workflow", "sp-implement", "--scope-dir", scope, "--reason", "r1-prune-old", "--payload-json", closeoutApplyPayloadJSON(t, true), "--format", "json"}
	if code := Run(args, &out, &stderr, "r1-prune-seed"); code != 10 {
		t.Fatalf("old interruption exit=%d output=%s", code, out.String())
	}
	closeoutApplyAfterScopeReceiptHook = nil
	oldReceipt, err := loadMutationCognitionReceipt(absolute)
	if err != nil || oldReceipt == nil {
		t.Fatalf("old receipt: %#v %v", oldReceipt, err)
	}
	old, err := loadCloseoutIntent(paths, oldReceipt.IntentID)
	if err != nil {
		t.Fatal(err)
	}
	newer, _, _, err := ensureCloseoutIntent(paths, "sp-implement", scope, "r1-prune-new", closeoutApplyPayloadJSON(t, true), "", "", []string{"src/app.go"})
	if err != nil {
		t.Fatal(err)
	}
	out.Reset()
	if code := Run(closeoutRecoveryArgv(paths, "replay", newer.ID, newer.InputDigest)[1:], &out, &stderr, "r1-prune-seed"); code != 0 {
		t.Fatalf("new exact replay exit=%d output=%s", code, out.String())
	}
	if mutationCognitionStatus(absolute)["allowed_close"] == true || countCloseoutApplyUpdates(t, paths) != 2 {
		t.Fatal("seed did not retain older completion alongside later real receipt")
	}
	return project, paths, absolute, old
}

func TestR1SupersededCompletedIntentPruneRequiresEveryProof(t *testing.T) {
	for _, mismatch := range []string{"old-state", "old-journal", "new-journal", "workflow", "scope", "receipt-ref", "receipt-digest", "result", "active-generation", "completion-order"} {
		t.Run(mismatch, func(t *testing.T) {
			_, paths, absolute, old := r1SeedSupersededScopeReceipt(t)
			receipt, err := loadMutationCognitionReceipt(absolute)
			if err != nil || receipt == nil {
				t.Fatalf("current real receipt: %#v %v", receipt, err)
			}
			switch mismatch {
			case "old-state":
				old.State = "receipt_recorded"
			case "old-journal":
				old.UpdateID = receipt.UpdateID
			case "new-journal":
				receipt.UpdateID = old.UpdateID
			case "workflow":
				receipt.Workflow = "sp-review"
			case "scope":
				receipt.Scope = ".specify/features/foreign"
			case "receipt-ref":
				receipt.IntentRef = closeoutIntentRef(paths, closeoutIntentPath(paths, old.ID))
			case "receipt-digest":
				receipt.IntentDigest = strings.Repeat("0", 64)
			case "result":
				receipt.ResultState = "no_op"
			case "active-generation":
				st, err := store.OpenExisting(paths)
				if err != nil {
					t.Fatal(err)
				}
				_, err = st.ImportGeneration(context.Background(), store.ImportInput{GenerationID: "GEN-r1-new", Kind: "full", SourceCommit: "newcommit"})
				if err == nil {
					_, _, err = st.PublishRuntimeMetadata(context.Background(), "GEN-r1-new", rt.BaselineKindBrownfieldFull)
				}
				st.Close()
				if err != nil {
					t.Fatal(err)
				}
			case "completion-order":
				st, err := store.OpenExisting(paths)
				if err != nil {
					t.Fatal(err)
				}
				_, err = st.DB().ExecContext(context.Background(), `UPDATE updates SET completed_at = ? WHERE id = ?`, "9999-12-31T00:00:00Z", old.UpdateID)
				st.Close()
				if err != nil {
					t.Fatal(err)
				}
			}
			if _, err := writeMutationCognitionReceipt(absolute, *receipt); err != nil {
				t.Fatal(err)
			}
			beforeIntent, _ := os.ReadFile(closeoutIntentPath(paths, old.ID))
			beforeReceipt, _ := os.ReadFile(mutationCognitionReceiptPath(absolute))
			pruned, err := pruneCompletedCloseoutIntent(paths, old)
			if pruned {
				t.Fatalf("missing proof %s pruned the older intent (err=%v)", mismatch, err)
			}
			afterIntent, _ := os.ReadFile(closeoutIntentPath(paths, old.ID))
			afterReceipt, _ := os.ReadFile(mutationCognitionReceiptPath(absolute))
			if !bytes.Equal(beforeIntent, afterIntent) || !bytes.Equal(beforeReceipt, afterReceipt) || countCloseoutApplyUpdates(t, paths) != 2 {
				t.Fatal("rejected prune modified old owner, current receipt or update journal")
			}
		})
	}
}

func TestR1CompletedIntentReplayPreservesDoSourceGuard(t *testing.T) {
	project, _, session := doSourceMutationFixtureWithSetup(t, func(root string) { doSeedCognitionBaseline(t, root) })
	payload := doCognitionPlannerPayload(t, project, session)
	closeoutApplyAfterScopeReceiptHook = func(string) error { return errors.New("retain completed Do intent before prune") }
	t.Cleanup(func() { closeoutApplyAfterScopeReceiptHook = nil })
	if code, env := doApplyCognitionPayload(t, project, session, payload); code != 10 {
		t.Fatalf("Do interruption exit=%d env=%#v", code, env)
	}
	closeoutApplyAfterScopeReceiptHook = nil
	paths, err := rt.ResolvePaths(project)
	if err != nil {
		t.Fatal(err)
	}
	absolute := filepath.Join(project, ".specify/do/sessions", session.ID)
	receipt, err := loadMutationCognitionReceipt(absolute)
	if err != nil || receipt == nil {
		t.Fatalf("completed Do receipt: %#v %v", receipt, err)
	}
	beforeIntent, _ := os.ReadFile(closeoutIntentPath(paths, receipt.IntentID))
	beforeReceipt, _ := os.ReadFile(mutationCognitionReceiptPath(absolute))
	writeTextFile(t, filepath.Join(project, "source.txt"), "unrecorded changed Do source after cognition completion\n")
	var out, stderr bytes.Buffer
	code := Run(closeoutRecoveryArgv(paths, "replay", receipt.IntentID, receipt.IntentDigest)[1:], &out, &stderr, "r1-source-refusal")
	t.Logf("native Do changed-source replay exit=%d stdout=%s stderr=%s", code, out.String(), stderr.String())
	if code != 10 {
		t.Fatalf("changed Do source pruned completed recovery owner: exit=%d output=%s", code, out.String())
	}
	afterIntent, _ := os.ReadFile(closeoutIntentPath(paths, receipt.IntentID))
	afterReceipt, _ := os.ReadFile(mutationCognitionReceiptPath(absolute))
	if !bytes.Equal(beforeIntent, afterIntent) || !bytes.Equal(beforeReceipt, afterReceipt) {
		t.Fatal("Do source refusal changed exact recovery state")
	}
}

func TestR1SupersededCompletedIntentPruneUsesWindowsScopeIdentity(t *testing.T) {
	if filepath.Separator != '\\' {
		t.Skip("Windows filesystem scope aliases")
	}
	project, paths, absolute, old := r1SeedSupersededScopeReceipt(t)
	receipt, err := loadMutationCognitionReceipt(absolute)
	if err != nil || receipt == nil {
		t.Fatalf("current receipt: %#v %v", receipt, err)
	}
	receipt.Scope = strings.ToUpper(receipt.Scope)
	if _, err := writeMutationCognitionReceipt(absolute, *receipt); err != nil {
		t.Fatal(err)
	}
	before, _ := os.ReadFile(mutationCognitionReceiptPath(absolute))
	var out, stderr bytes.Buffer
	code := Run(closeoutRecoveryArgv(paths, "replay", old.ID, old.InputDigest)[1:], &out, &stderr, "r1-windows-alias")
	t.Logf("native superseded alias project=%s exit=%d stdout=%s", project, code, out.String())
	if code != 0 || mutationCognitionStatus(absolute)["allowed_close"] != true || countCloseoutApplyUpdates(t, paths) != 2 {
		t.Fatalf("existing Windows scope identity was not preserved: exit=%d output=%s", code, out.String())
	}
	after, _ := os.ReadFile(mutationCognitionReceiptPath(absolute))
	if !bytes.Equal(before, after) {
		t.Fatal("alias prune replaced current later receipt")
	}
}

func TestR1StandaloneReceiptCannotReplacePendingIntent(t *testing.T) {
	for _, state := range []string{"mark-dirty", "partial", "ready", "no_op", "scope_ready"} {
		t.Run(state, func(t *testing.T) {
			project, paths, scope := seedCloseoutApplyRuntime(t)
			absolute := filepath.Join(project, filepath.FromSlash(scope))
			if _, err := recordMutationCognitionReceipt(absolute, "sp-implement", scope, "mark-dirty", "previous unclean receipt", "", nil); err != nil {
				t.Fatal(err)
			}
			beforeReceipt, err := os.ReadFile(mutationCognitionReceiptPath(absolute))
			if err != nil {
				t.Fatal(err)
			}
			intent, _, _, err := ensureCloseoutIntent(paths, "sp-implement", scope, "r1-pending", closeoutApplyPayloadJSON(t, true), "", "", []string{"src/app.go"})
			if err != nil {
				t.Fatal(err)
			}
			beforeIntent, err := os.ReadFile(closeoutIntentPath(paths, intent.ID))
			if err != nil {
				t.Fatal(err)
			}
			writeReadyProjectCognitionStatus(t, project, "U-previous")
			var out, stderr bytes.Buffer
			args := []string{"cognition", "mutation-receipt", "--project-root", project, "--workflow", "sp-implement", "--scope-dir", scope, "--result-state", state, "--reason", "fallback after durable intent", "--update-id", "U-previous", "--format", "json"}
			code := Run(args, &out, &stderr, "r1-after")
			afterReceipt, _ := os.ReadFile(mutationCognitionReceiptPath(absolute))
			afterIntent, _ := os.ReadFile(closeoutIntentPath(paths, intent.ID))
			gate := mutationCognitionStatus(absolute)
			t.Logf("native exit=%d state=%s gate=%v stdout=%s stderr=%s", code, state, gate, out.String(), stderr.String())
			if code != 10 || !strings.Contains(out.String(), intent.ID) || !strings.Contains(out.String(), "closeout inspect") || gate["allowed_close"] == true {
				t.Fatalf("standalone fallback crossed pending intent: exit=%d gate=%v output=%s", code, gate, out.String())
			}
			if !bytes.Equal(beforeReceipt, afterReceipt) || !bytes.Equal(beforeIntent, afterIntent) {
				t.Fatal("refusal changed receipt or pending intent")
			}
		})
	}
}

func TestR1StandaloneReceiptOtherScopeDoesNotConsumePendingIntent(t *testing.T) {
	project, paths, scope := seedCloseoutApplyRuntime(t)
	intent, _, _, err := ensureCloseoutIntent(paths, "sp-implement", scope, "r1-other-scope", closeoutApplyPayloadJSON(t, true), "", "", []string{"src/app.go"})
	if err != nil {
		t.Fatal(err)
	}
	other := filepath.Join(project, ".specify", "features", "other")
	result, err := recordMutationCognitionReceipt(other, "sp-implement", ".specify/features/other", "partial", "external evidence unavailable; debt retained", "", nil)
	if err != nil || result["allowed_close"] != true {
		t.Fatalf("independent legacy partial rejected: %v %#v", err, result)
	}
	if _, err := loadCloseoutIntent(paths, intent.ID); err != nil {
		t.Fatal("unrelated compatibility consumed the pending intent")
	}
}

func TestR1StandaloneReceiptCannotUseWindowsScopeCaseAlias(t *testing.T) {
	if filepath.Separator != '\\' {
		t.Skip("Windows filesystem case aliases")
	}
	project, paths, scope := seedCloseoutApplyRuntime(t)
	intent, _, _, err := ensureCloseoutIntent(paths, "sp-implement", scope, "r1-case-alias", closeoutApplyPayloadJSON(t, true), "", "", []string{"src/app.go"})
	if err != nil {
		t.Fatal(err)
	}
	alias := filepath.Join(project, filepath.FromSlash(strings.ToUpper(scope)))
	if _, err := recordMutationCognitionReceipt(alias, "sp-implement", strings.ToUpper(scope), "mark-dirty", "case alias fallback", "", nil); err == nil || !strings.Contains(err.Error(), intent.ID) {
		t.Fatalf("case alias crossed pending intent: %v", err)
	}
}

func TestR1PendingIntentRecoveryOwnsExactReplay(t *testing.T) {
	project, paths, scope := seedCloseoutApplyRuntime(t)
	absolute := filepath.Join(project, filepath.FromSlash(scope))
	intent, _, _, err := ensureCloseoutIntent(paths, "sp-implement", scope, "r1-replay", closeoutApplyPayloadJSON(t, true), "", "", []string{"src/app.go"})
	if err != nil {
		t.Fatal(err)
	}
	argv := mutationCognitionRecoveryArgv(absolute, "sp-implement", nil)
	if !reflect.DeepEqual(argv, closeoutRecoveryArgv(paths, "inspect", intent.ID, "")) {
		t.Fatalf("next argv not exact intent inspect: %#v", argv)
	}
	var out, stderr bytes.Buffer
	if code := Run(argv[1:], &out, &stderr, "r1-inspect"); code != 0 {
		t.Fatalf("inspect exit=%d %s %s", code, out.String(), stderr.String())
	}
	data := requireObject(t, decodeJSONObject(t, out.Bytes()), "data")
	replay := anyStringSlice(data["replay_argv"])
	expectedReplay := closeoutRecoveryArgv(paths, "replay", intent.ID, intent.InputDigest)
	if len(replay) == 0 || !filepath.IsAbs(replay[0]) || !reflect.DeepEqual(replay[1:], expectedReplay[1:]) {
		t.Fatalf("inspect returned incorrect replay binding: %#v", data)
	}
	out.Reset()
	if code := Run(replay[1:], &out, &stderr, "r1-replay"); code != 0 {
		t.Fatalf("replay exit=%d %s %s", code, out.String(), stderr.String())
	}
	firstReceipt, err := os.ReadFile(mutationCognitionReceiptPath(absolute))
	if err != nil {
		t.Fatal(err)
	}
	if gate := mutationCognitionStatus(absolute); gate["allowed_close"] != true {
		t.Fatalf("recovery did not produce allowed bound receipt: %#v", gate)
	}
	if count := countCloseoutApplyUpdates(t, paths); count != 1 {
		t.Fatalf("recovery updates=%d want one", count)
	}
	var secondOut bytes.Buffer
	// Identical apply recovers/uses the committed intent identity; no second update.
	code := Run([]string{"cognition", "closeout", "apply", "--project-root", project, "--workflow", "sp-implement", "--scope-dir", scope, "--reason", "r1-replay", "--payload-json", closeoutApplyPayloadJSON(t, true), "--format", "json"}, &secondOut, &stderr, "r1-repeat")
	if code != 0 || countCloseoutApplyUpdates(t, paths) != 1 {
		t.Fatalf("repeat created mutation: exit=%d %s", code, secondOut.String())
	}
	receipt, err := loadMutationCognitionReceipt(absolute)
	if err != nil || receipt == nil || receipt.IntentID != intent.ID || receipt.IntentDigest != intent.InputDigest {
		t.Fatalf("receipt lost exact intent binding: %#v %v (first=%s)", receipt, err, firstReceipt)
	}
}

func TestR1QuickMissingReceiptUsesPlannerAndDurableIntentUsesInspect(t *testing.T) {
	project, paths, _ := seedCloseoutApplyRuntime(t)
	scope := ".planning/quick/r1-quick"
	absolute := filepath.Join(project, filepath.FromSlash(scope))
	writeTextFile(t, filepath.Join(absolute, "STATUS.md"), "---\nid: r1-quick\nstatus: in-progress\n---\n\nchanged_code_paths: [src/app.go]\nproject_cognition_refresh:\n  status: ready\n")
	service := quickService{projectRoot: project}
	gate := service.cognitionCloseoutStatus(absolute)
	argv := gate["next_argv"].([]string)
	if gate["allowed_close"] == true || len(argv) < 3 || argv[2] != "closeout-plan" || !strings.Contains(strings.Join(argv, " "), "--changed-path src/app.go") {
		t.Fatalf("status prose bypass or planner omission: %#v", gate)
	}
	intent, _, _, err := ensureCloseoutIntent(paths, "sp-quick", scope, "r1-quick-recovery", closeoutApplyPayloadJSON(t, true), "", "", []string{"src/app.go"})
	if err != nil {
		t.Fatal(err)
	}
	gate = service.cognitionCloseoutStatus(absolute)
	if !reflect.DeepEqual(gate["next_argv"], closeoutRecoveryArgv(paths, "inspect", intent.ID, "")) {
		t.Fatalf("Quick status ignored durable intent: %#v", gate)
	}
	if err := service.validateCognitionCloseoutForClose(absolute, "resolved"); err == nil || !strings.Contains(err.Error(), intent.ID) || strings.Contains(err.Error(), "--result-state ready") {
		t.Fatalf("Quick terminal recovery: %v", err)
	}
	var out bytes.Buffer
	code := runQuick([]string{"--project-root", project, "cognition-closeout", "r1-quick", "--result-state", "mark-dirty", "--reason", "incorrect fallback"}, &out)
	if code == 0 || !strings.Contains(out.String(), intent.ID) {
		t.Fatalf("Quick standalone bypass: exit=%d output=%s", code, out.String())
	}
}

func TestR1ImplementTerminalMissingReceiptReturnsPlanner(t *testing.T) {
	project, feature, rel := newImplementFeatureProject(t)
	withImplementCwd(t, project)
	writeImplementJSONFile(t, filepath.Join(feature, "worker-results", "T001.json"), map[string]any{
		"task_id": "T001", "status": "success", "validation_results": []any{map[string]any{"command": "pytest -q", "status": "passed"}}, "summary": "Implemented task",
	})
	writeImplementJSONFile(t, filepath.Join(feature, "implementation-review", "tasks", "T001.json"), map[string]any{
		"version": 1, "task_id": "T001", "status": "accepted", "blockers": []any{}, "changed_paths": []any{"src/product.txt"},
	})
	convergence, err := reserveImplementValidationEpoch(project, feature, "implement", "convergence", implementSnapshotSHA256(project, feature), []string{"pytest -q"}, []string{"T001"})
	if err != nil {
		t.Fatal(err)
	}
	if _, err := completeImplementValidationEpoch(project, feature, implementValidationFinishRequest{RunID: convergence["run_id"].(string), Status: "passed", EvidenceRefs: []string{"implementation-review/validation-evidence/V1.txt"}, Summary: "Convergence passed."}); err != nil {
		t.Fatal(err)
	}
	if err := os.Remove(mutationCognitionReceiptPath(feature)); err != nil {
		t.Fatal(err)
	}
	var out bytes.Buffer
	if code := runImplement([]string{"closeout", "--feature-dir", rel}, &out); code != 10 {
		t.Fatalf("terminal before cognition exit=%d %s", code, out.String())
	}
	env := decodeImplementEnvelope(t, out.Bytes())
	if len(env.NextArgv) < 3 || env.NextArgv[2] != "closeout-plan" || strings.Contains(strings.Join(env.NextArgv, " "), "mutation-receipt") {
		t.Fatalf("wrong missing receipt recovery: %#v", env)
	}
	for _, name := range []string{"implementation-summary.md", "implementation-handoff.json"} {
		if _, err := os.Stat(filepath.Join(feature, name)); !os.IsNotExist(err) {
			t.Fatalf("terminal artifact before cognition: %s %v", name, err)
		}
	}
}
