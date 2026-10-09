package main

import (
	"bytes"
	"encoding/json"
	"errors"
	"strings"
	"testing"

	rt "github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/runtime"
)

func TestDoCognitionForeignAutomaticReplayRequiresExactDoOwner(t *testing.T) {
	// Preserve another workflow's pending intent in the initial source basis.
	// Its later identical retry must not acquire or bypass this Do's session
	// lock while automatically draining the shared cognition queue.
	otherPayload := closeoutApplyPayloadJSON(t, true)
	root, _, session := doSourceMutationFixtureWithSetup(t, func(root string) {
		paths := doSeedCognitionBaseline(t, root)
		if _, _, _, err := ensureCloseoutIntent(paths, "sp-implement", ".planning/other", "workflow-finalize", otherPayload, "", "", []string{"src/app.go"}); err != nil {
			t.Fatal(err)
		}
	})
	payload := doCognitionPlannerPayload(t, root, session)
	closeoutApplyAfterIntentPersistHook = func(string) error { return errors.New("interrupt Do before its graph write") }
	t.Cleanup(func() { closeoutApplyAfterIntentPersistHook = nil })
	if code, envelope := doApplyCognitionPayload(t, root, session, payload); code == 0 || envelope.Data["closeout_status"] != "closeout_intent_pending" {
		t.Fatalf("fixture did not preserve the pending Do intent: %d %+v", code, envelope)
	}
	closeoutApplyAfterIntentPersistHook = nil
	paths, _ := rt.ResolvePaths(root)
	intents, err := listCloseoutIntents(paths)
	if err != nil {
		t.Fatal(err)
	}
	var doIntent closeoutIntent
	for _, intent := range intents {
		if intent.Workflow == "sp-do" {
			doIntent = intent
		}
	}
	if doIntent.ID == "" {
		t.Fatal("pending Do intent is missing")
	}
	releaseDo, err := doSessionLock(root, session.ID)
	if err != nil {
		t.Fatal(err)
	}
	defer releaseDo()
	var out, stderr bytes.Buffer
	code := Run([]string{"cognition", "closeout", "apply", "--project-root", root, "--workflow", "sp-implement", "--scope-dir", ".planning/other", "--payload-json", otherPayload, "--format", "json"}, &out, &stderr, "test")
	status, err := rt.ReadStatus(paths)
	if err != nil {
		t.Fatal(err)
	}
	if status.LastUpdateID != "" {
		t.Fatalf("another workflow replayed the Do graph while its owner lock was held: code=%d status=%+v output=%s", code, status, out.String())
	}
	if code == 0 || !strings.Contains(out.String(), "exact Do owner") {
		t.Fatalf("foreign automatic replay did not identify its exact Do recovery gate: %d %s %s", code, out.String(), stderr.String())
	}
	if _, err := loadCloseoutIntent(paths, doIntent.ID); err != nil {
		t.Fatalf("ownership refusal removed the original pending Do intent: %v", err)
	}
	releaseDo()
	out.Reset()
	stderr.Reset()
	code = Run([]string{"cognition", "closeout", "replay", "--project-root", root, "--intent-id", doIntent.ID, "--expected-digest", doIntent.InputDigest, "--format", "json"}, &out, &stderr, "test")
	var envelope Envelope
	if err := json.Unmarshal(out.Bytes(), &envelope); err != nil || code != 0 || envelope.Data["allowed_close"] != true {
		t.Fatalf("exact owner recovery did not finish the original Do: %v %d %s %s", err, code, out.String(), stderr.String())
	}
}
