package main

import (
	"bytes"
	"context"
	"errors"
	"os"
	"path/filepath"
	"strings"
	"testing"

	rt "github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/runtime"
	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/store"
	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/update"
	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/validation"
)

func TestCompletedCloseoutReplayRefusesInvalidPublishedProofBeforeUpdate(t *testing.T) {
	for _, mismatch := range []string{"generation", "reference", "digest", "completion-order"} {
		t.Run(mismatch, func(t *testing.T) {
			project, paths, scope, old := r1SeedSupersededScopeReceipt(t)
			receipt, err := loadMutationCognitionReceipt(scope)
			if err != nil || receipt == nil {
				t.Fatalf("current receipt: %#v %v", receipt, err)
			}
			switch mismatch {
			case "reference":
				receipt.IntentRef = ".specify/project-cognition/closeout-intents/foreign.json"
			case "digest":
				receipt.IntentDigest = strings.Repeat("0", 64)
			case "generation":
				st, err := store.OpenExisting(paths)
				if err != nil {
					t.Fatal(err)
				}
				_, err = st.ImportGeneration(context.Background(), store.ImportInput{GenerationID: "GEN-completed-replay-other", Kind: "full", SourceCommit: "other"})
				if err == nil {
					_, _, err = st.PublishRuntimeMetadata(context.Background(), "GEN-completed-replay-other", rt.BaselineKindBrownfieldFull)
				}
				st.Close()
				if err != nil {
					t.Fatal(err)
				}
			case "completion-order":
				completedReplayMoveOldCompletionIntoFuture(t, paths, old)
			}
			if _, err := writeMutationCognitionReceipt(scope, *receipt); err != nil {
				t.Fatal(err)
			}
			beforeIntent, _ := os.ReadFile(closeoutIntentPath(paths, old.ID))
			beforeReceipt, _ := os.ReadFile(mutationCognitionReceiptPath(scope))
			var out, stderr bytes.Buffer
			code := Run(closeoutRecoveryArgv(paths, "replay", old.ID, old.InputDigest)[1:], &out, &stderr, "completed-proof-refusal")
			t.Logf("exact replay mismatch=%s exit=%d stdout=%s stderr=%s", mismatch, code, out.String(), stderr.String())
			if code != 10 {
				t.Fatalf("invalid %s proof was replayed: exit=%d", mismatch, code)
			}
			completedReplayAssertUnchanged(t, paths, scope, old, beforeIntent, beforeReceipt)
			data := requireObject(t, decodeJSONObject(t, out.Bytes()), "data")
			if !strings.Contains(data["error"].(string), "cannot be pruned") || len(anyStringSlice(data["recovery_argv"])) == 0 {
				t.Fatalf("refusal lacks bounded inspect recovery: %#v (project=%s)", data, project)
			}
		})
	}
}

func TestCompletedCloseoutApplyAndQueueCannotRewriteInvalidPublishedProof(t *testing.T) {
	for _, current := range []bool{true, false} {
		name := "queued-predecessor"
		if current {
			name = "same-apply"
		}
		t.Run(name, func(t *testing.T) {
			project, paths, scope, old := r1SeedSupersededScopeReceipt(t)
			completedReplayMoveOldCompletionIntoFuture(t, paths, old)
			beforeIntent, _ := os.ReadFile(closeoutIntentPath(paths, old.ID))
			beforeReceipt, _ := os.ReadFile(mutationCognitionReceiptPath(scope))
			reason, relScope := old.Reason, old.Scope
			var queued closeoutIntent
			var beforeQueued []byte
			if !current {
				reason, relScope = "completed-replay-queued-current", ".specify/features/002-closeout"
				if err := os.MkdirAll(filepath.Join(project, filepath.FromSlash(relScope)), 0o755); err != nil {
					t.Fatal(err)
				}
				var err error
				queued, _, _, err = ensureCloseoutIntent(paths, old.Workflow, relScope, reason, old.PayloadJSON, "", "", old.ChangedPaths)
				if err != nil {
					t.Fatal(err)
				}
				beforeQueued, _ = os.ReadFile(closeoutIntentPath(paths, queued.ID))
			}
			var out, stderr bytes.Buffer
			code := Run([]string{"cognition", "closeout", "apply", "--project-root", project, "--workflow", old.Workflow, "--scope-dir", relScope, "--reason", reason, "--payload-json", old.PayloadJSON, "--format", "json"}, &out, &stderr, "completed-proof-apply-refusal")
			t.Logf("apply route=%s exit=%d stdout=%s stderr=%s", name, code, out.String(), stderr.String())
			if code != 10 {
				t.Fatalf("apply consumed invalid completed predecessor: exit=%d", code)
			}
			completedReplayAssertUnchanged(t, paths, scope, old, beforeIntent, beforeReceipt)
			data := requireObject(t, decodeJSONObject(t, out.Bytes()), "data")
			if data["blocked_intent_id"] != old.ID || len(anyStringSlice(data["recovery_argv"])) == 0 {
				t.Fatalf("apply refusal lost exact recovery owner: %#v", data)
			}
			if !current {
				afterQueued, _ := os.ReadFile(closeoutIntentPath(paths, queued.ID))
				if !bytes.Equal(beforeQueued, afterQueued) {
					t.Fatal("refused predecessor mutated current queued intent")
				}
			}
		})
	}
}

func TestCompletedCloseoutApplyReturnsExactReplayForPublicationInterruption(t *testing.T) {
	project, paths, scope := seedCloseoutApplyRuntime(t)
	closeoutApplyAfterScopeReceiptHook = func(string) error { return errors.New("interrupt after published receipt") }
	t.Cleanup(func() { closeoutApplyAfterScopeReceiptHook = nil })
	args := []string{"cognition", "closeout", "apply", "--project-root", project, "--workflow", "sp-implement", "--scope-dir", scope, "--payload-json", closeoutApplyPayloadJSON(t, true), "--format", "json"}
	var out, stderr bytes.Buffer
	if code := Run(args, &out, &stderr, "completed-proof-publication-interruption"); code != 10 {
		t.Fatalf("publication interruption exit=%d stdout=%s", code, out.String())
	}
	closeoutApplyAfterScopeReceiptHook = nil
	intents, err := listCloseoutIntents(paths)
	if err != nil || len(intents) != 1 || intents[0].State != "scope_receipt_recorded" {
		t.Fatalf("publication interruption owner: %#v %v", intents, err)
	}
	intent := intents[0]
	absScope := filepath.Join(project, filepath.FromSlash(scope))
	beforeReceipt, _ := os.ReadFile(mutationCognitionReceiptPath(absScope))
	out.Reset()
	if code := Run(args, &out, &stderr, "completed-proof-apply-recovery"); code != 10 {
		t.Fatalf("completed apply did not return exact recovery: exit=%d stdout=%s", code, out.String())
	}
	data := requireObject(t, decodeJSONObject(t, out.Bytes()), "data")
	inspect := anyStringSlice(data["recovery_argv"])
	if len(inspect) == 0 {
		t.Fatalf("completed apply omitted inspect: %#v", data)
	}
	out.Reset()
	if code := Run(inspect[1:], &out, &stderr, "completed-proof-inspect"); code != 0 {
		t.Fatalf("inspect exit=%d stdout=%s", code, out.String())
	}
	replay := anyStringSlice(requireObject(t, decodeJSONObject(t, out.Bytes()), "data")["replay_argv"])
	if len(replay) == 0 {
		t.Fatal("published interruption lacks exact replay")
	}
	out.Reset()
	if code := Run(replay[1:], &out, &stderr, "completed-proof-replay"); code != 0 {
		t.Fatalf("valid publication recovery exit=%d stdout=%s", code, out.String())
	}
	afterReceipt, _ := os.ReadFile(mutationCognitionReceiptPath(absScope))
	if !bytes.Equal(beforeReceipt, afterReceipt) || countCloseoutApplyUpdates(t, paths) != 1 {
		t.Fatal("valid completed replay rewrote the receipt or resubmitted the update")
	}
	if _, err := os.Stat(closeoutIntentPath(paths, intent.ID)); !os.IsNotExist(err) || mutationCognitionStatus(absScope)["allowed_close"] != true {
		t.Fatalf("valid completed replay did not prune owner: %v", err)
	}
}

func TestCloseoutReceiptRecordedInterruptionStillPublishesScopeReceipt(t *testing.T) {
	project, paths, scope := seedCloseoutApplyRuntime(t)
	closeoutApplyAfterUpdateHook = func(string) error { return errors.New("interrupt after committed update") }
	t.Cleanup(func() { closeoutApplyAfterUpdateHook = nil })
	var out, stderr bytes.Buffer
	if code := Run([]string{"cognition", "closeout", "apply", "--project-root", project, "--workflow", "sp-implement", "--scope-dir", scope, "--payload-json", closeoutApplyPayloadJSON(t, true), "--format", "json"}, &out, &stderr, "receipt-recorded-interruption"); code != 10 {
		t.Fatalf("committed interruption exit=%d stdout=%s", code, out.String())
	}
	closeoutApplyAfterUpdateHook = nil
	intents, err := listCloseoutIntents(paths)
	if err != nil || len(intents) != 1 {
		t.Fatalf("committed interruption owner: %#v %v", intents, err)
	}
	intent := intents[0]
	// Execute the real validation/publication prefix, then stop at the durable
	// receipt_recorded boundary before CompleteRefresh and scope publication.
	gate := validation.ValidateBuild(paths)
	if gate.Status != "ok" || !gate.CompletionAllowed {
		t.Fatalf("validation prefix: %#v", gate)
	}
	if err := update.RecordValidateBuildReceipt(paths, gate.Status, gate.Gate, gate.Readiness); err != nil {
		t.Fatal(err)
	}
	intent.State = "receipt_recorded"
	if err := updateCloseoutIntent(paths, intent); err != nil {
		t.Fatal(err)
	}
	out.Reset()
	if code := Run(closeoutRecoveryArgv(paths, "replay", intent.ID, intent.InputDigest)[1:], &out, &stderr, "receipt-recorded-replay"); code != 0 {
		t.Fatalf("pre-publication replay exit=%d stdout=%s stderr=%s", code, out.String(), stderr.String())
	}
	data := requireObject(t, decodeJSONObject(t, out.Bytes()), "data")
	if data["update_id"] != intent.UpdateID || data["allowed_close"] != true || countCloseoutApplyUpdates(t, paths) != 1 {
		t.Fatalf("pre-publication replay failed or duplicated update: %#v", data)
	}
}

func completedReplayMoveOldCompletionIntoFuture(t *testing.T, paths rt.Paths, intent closeoutIntent) {
	t.Helper()
	st, err := store.OpenExisting(paths)
	if err != nil {
		t.Fatal(err)
	}
	_, err = st.DB().ExecContext(context.Background(), `UPDATE updates SET completed_at = ? WHERE id = ?`, "9999-12-31T00:00:00Z", intent.UpdateID)
	st.Close()
	if err != nil {
		t.Fatal(err)
	}
}

func completedReplayAssertUnchanged(t *testing.T, paths rt.Paths, scope string, intent closeoutIntent, beforeIntent, beforeReceipt []byte) {
	t.Helper()
	afterIntent, _ := os.ReadFile(closeoutIntentPath(paths, intent.ID))
	afterReceipt, _ := os.ReadFile(mutationCognitionReceiptPath(scope))
	if !bytes.Equal(beforeIntent, afterIntent) || !bytes.Equal(beforeReceipt, afterReceipt) || countCloseoutApplyUpdates(t, paths) != 2 {
		t.Fatal("refusal mutated completed owner, current receipt or update journal")
	}
}
