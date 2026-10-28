package main

import (
	"encoding/json"
	"os"
	"os/exec"
	"path/filepath"
	"reflect"
	"runtime"
	"strings"
	"testing"
)

// E2E consumes method advice through the existing read APIs. Only fixture setup
// publishes a verified method; neither repeated native execution opens Do again.
func TestE2EMethodReuseNeedsFreshExecutionAndBindings(t *testing.T) {
	root, input := playbookFixture(t)
	session := playbookExecuteFixture(t, root, input)
	published := playbookPublishFixture(t, root, session, "")
	playbookFinishFixture(t, root, session.ID, published)
	context, _ := json.Marshal(map[string]string{"os": runtime.GOOS, "arch": runtime.GOARCH})
	before := playbookSnapshotFiles(t, root)
	found, err := findPlaybooks(root, []string{"--operation", "test", "--target", "fixture", "--context-json", string(context), "--rank", "relevance"})
	if err != nil {
		t.Fatal(err)
	}
	items := found["items"].([]map[string]any)
	if len(items) != 1 {
		t.Fatalf("matching methods: %#v", found)
	}
	id := items[0]["id"].(string)
	pinned, err := showPlaybook(root, id, "all", "1", "")
	if err != nil {
		t.Fatal(err)
	}
	evidence, err := showPlaybook(root, id, "evidence", "1", "")
	if err != nil {
		t.Fatal(err)
	}
	raw, err := json.Marshal(pinned["definition"])
	if err != nil {
		t.Fatal(err)
	}
	// One discovery and expansion, two fresh validations and real invocations.
	// No token or wall-clock agent improvement is inferred from these counts.
	for round := 0; round < 2; round++ {
		validated, err := validatePlaybookInput(root, []string{"--input-json", string(raw), "--context-json", string(context)})
		if err != nil || validated["applicable"] != true || validated["execution_verified"] != false || validated["claim_ready"] != false || validated["definition_digest"] != pinned["content_digest"] {
			t.Fatalf("round %d: %#v, %v", round, validated, err)
		}
		if !reflect.DeepEqual(validated["source_fingerprint"], evidence["source_fingerprint"]) {
			t.Fatal("historical method sources do not match live bytes")
		}
		output, err := exec.Command("git", "--version").CombinedOutput()
		if err != nil || !strings.HasPrefix(string(output), "git version ") {
			t.Fatalf("fresh native round %d: %q, %v", round, output, err)
		}
	}
	if !reflect.DeepEqual(before, playbookSnapshotFiles(t, root)) {
		t.Fatal("E2E read/reuse created a DoSession, changed Work or modified method storage")
	}
	other, err := findPlaybooks(root, []string{"--operation", "test", "--target", "another-build", "--rank", "relevance"})
	if err != nil || len(other["items"].([]map[string]any)) != 0 {
		t.Fatalf("target mismatch recalled the old method: %#v, %v", other, err)
	}
	if err := os.WriteFile(filepath.Join(root, "source.txt"), []byte("source v2\n"), 0o600); err != nil {
		t.Fatal(err)
	}
	changed, err := validatePlaybookInput(root, []string{"--input-json", string(raw), "--context-json", string(context)})
	if err != nil || changed["applicable"] != true {
		t.Fatalf("definition validation is not a historical freshness gate: %#v, %v", changed, err)
	}
	if reflect.DeepEqual(changed["source_fingerprint"], evidence["source_fingerprint"]) {
		t.Fatal("changed source was hidden by method history")
	}
	stale, err := showPlaybook(root, id, "all", "1", "")
	if err != nil || stale["source_status"] != "changed" {
		t.Fatalf("stale pinned method: %#v, %v", stale, err)
	}
	wrongContext, _ := json.Marshal(map[string]string{"os": "unavailable-platform", "arch": runtime.GOARCH})
	incompatible, err := validatePlaybookInput(root, []string{"--input-json", string(raw), "--context-json", string(wrongContext)})
	if err != nil || incompatible["applicable"] != false {
		t.Fatalf("context mismatch: %#v, %v", incompatible, err)
	}
}

func TestE2ELearningManualCaptureReusesOneFailureRepairPair(t *testing.T) {
	root := t.TempDir()
	mustMkdirLearningTest(t, filepath.Join(root, ".specify"))
	failure, err := exec.Command("git", "--spec-kit-invalid-readiness-option").CombinedOutput()
	if err == nil || len(failure) == 0 {
		t.Fatalf("negative native control did not fail: %q", failure)
	}
	repair, err := exec.Command("git", "--version").CombinedOutput()
	if err != nil || !strings.HasPrefix(string(repair), "git version ") {
		t.Fatalf("native recovery did not pass: %q, %v", repair, err)
	}
	for name, raw := range map[string][]byte{"failure.log": failure, "repair.log": repair} {
		if err := os.WriteFile(filepath.Join(root, name), raw, 0o600); err != nil {
			t.Fatal(err)
		}
	}
	key := "e2e.git-readiness-invalid-flag"
	evidence := "failure.log sha256=" + fileContentSHA256(failure) + "; repair.log sha256=" + fileContentSHA256(repair)
	capture := runLearningEnvelopeTest(t, []string{"capture", "--project-root", root, "--command", "sp-e2e", "--type", "tooling_trap", "--recurrence-key", key,
		"--summary", "A unsupported readiness flag fails before the native operation starts", "--problem", "The native tool rejected the invented readiness flag", "--action", "Use the documented version flag and independently inspect its fresh exit and output", "--trigger", "Checking the same native Git prerequisite", "--success", "Fresh exit zero and the actual Git version prefix", "--exception", "A different tool, build, target or fixture requires new applicability and effect checks", "--evidence", evidence, "--context", "operation_owner=GitReadiness", "--format", "json"})
	if capture.Status != "ok" || capture.Data["status"] != "candidate" {
		t.Fatalf("manual E2E capture: %#v", capture)
	}
	before := playbookSnapshotFiles(t, root)
	// Resuming the same pair uses start/list/show instead of capturing it again.
	for _, args := range [][]string{
		{"start", "--command", "spx-e2e", "--context", "operation_owner=GitReadiness"},
		{"list", "--command", "sp-e2e", "--query", "readiness", "--context", "operation_owner=GitReadiness"},
		{"show", "--ref", key},
	} {
		result := runLearningEnvelopeTest(t, append(args, "--project-root", root, "--format", "json"))
		if result.Status != "ok" {
			t.Fatalf("read-only reuse: %#v", result)
		}
	}
	if !reflect.DeepEqual(before, playbookSnapshotFiles(t, root)) {
		t.Fatal("same failure/repair pair was recaptured or automatically promoted")
	}
	unsupported := runLearningEnvelopeTest(t, []string{"capture-auto", "--project-root", root, "--command", "sp-e2e", "--format", "json"})
	if unsupported.Status == "ok" || !reflect.DeepEqual(before, playbookSnapshotFiles(t, root)) {
		t.Fatal("unsupported E2E auto capture silently succeeded or mutated knowledge")
	}
}

func TestE2ELearningAdviceCannotReplaceCurrentEffectEvidence(t *testing.T) {
	root := t.TempDir()
	mustMkdirLearningTest(t, filepath.Join(root, ".specify"))
	// A deliberately wrong candidate is test input, not verified history.
	key := "e2e.wrong-readiness-candidate"
	seed := runLearningEnvelopeTest(t, []string{"capture", "--project-root", root, "--command", "sp-e2e", "--type", "tooling_trap", "--recurrence-key", key,
		"--summary", "Legacy advice incorrectly assumes an unsupported native readiness option works", "--action", "Invoke the unsupported readiness option", "--evidence", "Deliberately wrong advisory fixture; current native observation must decide applicability", "--format", "json"})
	if seed.Status != "ok" || seed.Data["status"] != "candidate" {
		t.Fatalf("wrong candidate fixture: %#v", seed)
	}
	before := playbookSnapshotFiles(t, root)
	shown := runLearningEnvelopeTest(t, []string{"show", "--project-root", root, "--ref", key, "--format", "json"})
	if shown.Status != "ok" || shown.Data["status"] != "candidate" {
		t.Fatalf("advice disclosure: %#v", shown)
	}
	if output, err := exec.Command("git", "--spec-kit-invalid-readiness-option").CombinedOutput(); err == nil || len(output) == 0 {
		t.Fatal("current native counterevidence unexpectedly agrees with wrong advice")
	}
	if !reflect.DeepEqual(before, playbookSnapshotFiles(t, root)) {
		t.Fatal("rejecting applicability erased or promoted the historical candidate")
	}
}
