package main

import (
	"bytes"
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"

	rt "github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/runtime"
)

func TestDoCognitionReceiptRefusesForeignWorkflowOwner(t *testing.T) {
	root, session := doStartFixture(t)
	for _, scope := range []string{
		".specify/do/sessions/" + session.ID,
		".SPECIFY/DO/sessions/" + session.ID,
		".specify/do",
	} {
		t.Run(scope, func(t *testing.T) {
			var out, stderr bytes.Buffer
			code := Run([]string{"cognition", "mutation-receipt", "--project-root", root,
				"--workflow", "sp-implement", "--scope-dir", scope,
				"--result-state", "mark-dirty", "--reason", "foreign owner must not write Do state",
				"--format", "json"}, &out, &stderr, "test")
			if code == 0 || !strings.Contains(out.String(), "sp-do owner") {
				t.Fatalf("foreign workflow acquired the Do receipt scope: %d %s %s", code, out.String(), stderr.String())
			}
			if _, err := os.Stat(filepath.Join(root, filepath.FromSlash(scope), mutationCognitionReceiptFileName)); !os.IsNotExist(err) {
				t.Fatalf("foreign ownership refusal wrote a receipt: %v", err)
			}
		})
	}
}

func TestDoCognitionForeignScopeCloseoutRefusesBeforeGraphMutation(t *testing.T) {
	root, session := doStartFixture(t)
	paths := doSeedCognitionBaseline(t, root)
	payload := closeoutApplyPayloadJSON(t, true)
	for _, scope := range []string{".specify/do/sessions/" + session.ID, ".SPECIFY/DO/sessions/" + session.ID} {
		t.Run(scope, func(t *testing.T) {
			var out, stderr bytes.Buffer
			code := Run([]string{"cognition", "closeout", "apply", "--project-root", root,
				"--workflow", "sp-implement", "--scope-dir", scope, "--payload-json", payload,
				"--format", "json"}, &out, &stderr, "test")
			doAssertForeignCognitionScopeRefused(t, root, paths, scope, code, out.String(), stderr.String())
			intents, err := listCloseoutIntents(paths)
			if err != nil || len(intents) != 0 {
				t.Fatalf("foreign scope rejection persisted an intent: %+v %v", intents, err)
			}
		})
	}
}

func TestDoCognitionForeignLegacyScopeIntentRefusesBeforeGraphReplay(t *testing.T) {
	root, session := doStartFixture(t)
	paths := doSeedCognitionBaseline(t, root)
	payload := closeoutApplyPayloadJSON(t, true)
	for _, scope := range []string{".specify/do/sessions/" + session.ID, ".SPECIFY/DO/sessions/" + session.ID, filepath.Join(root, ".specify/do/sessions", session.ID)} {
		t.Run(scope, func(t *testing.T) {
			// Create the exact typed intent through its existing writer to simulate
			// a pending record retained from the former permissive runtime.
			intent, _, _, err := ensureCloseoutIntent(paths, "sp-implement", scope, "workflow-finalize", payload, "", "", []string{"src/app.go"})
			if err != nil {
				t.Fatal(err)
			}
			var out, stderr bytes.Buffer
			code := Run([]string{"cognition", "closeout", "replay", "--project-root", root,
				"--intent-id", intent.ID, "--expected-digest", intent.InputDigest, "--format", "json"}, &out, &stderr, "test")
			doAssertForeignCognitionScopeRefused(t, root, paths, scope, code, out.String(), stderr.String())
			if _, err := loadCloseoutIntent(paths, intent.ID); err != nil {
				t.Fatalf("foreign legacy intent was removed on refusal: %v", err)
			}
		})
	}
}

func doAssertForeignCognitionScopeRefused(t *testing.T, root string, paths rt.Paths, scope string, code int, output, stderr string) {
	t.Helper()
	if code == 0 || !strings.Contains(output, "sp-do owner") {
		t.Fatalf("foreign workflow acquired the Do scope: %d %s %s", code, output, stderr)
	}
	var envelope Envelope
	if err := json.Unmarshal([]byte(output), &envelope); err != nil || envelope.Data["allowed_close"] == true {
		t.Fatalf("ownership refusal claimed closeable state: %v %+v", err, envelope)
	}
	status, err := rt.ReadStatus(paths)
	if err != nil || status.LastUpdateID != "" || status.LastFinalizedUpdateID != "" {
		t.Fatalf("foreign Do scope mutated or finalized the graph: %+v %v", status, err)
	}
	absScope, _, err := resolveCloseoutApplyScope(root, scope)
	if err != nil {
		t.Fatal(err)
	}
	if _, err := os.Stat(filepath.Join(absScope, mutationCognitionReceiptFileName)); !os.IsNotExist(err) {
		t.Fatalf("foreign ownership refusal wrote a receipt: %v", err)
	}
}
