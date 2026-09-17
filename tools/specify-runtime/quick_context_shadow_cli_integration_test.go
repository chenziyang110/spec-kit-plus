package main

import (
	"bytes"
	"context"
	"encoding/json"
	"os"
	"path/filepath"
	"reflect"
	"testing"
	"time"
)

// These tests deliberately invoke the production Run entrypoint and existing
// shadowTestRepo fixture. They must be executed in a complete source checkout.
func runQuickShadowEntry(t *testing.T, args ...string) (int, Envelope) {
	t.Helper()
	var stdout, stderr bytes.Buffer
	code := Run(args, &stdout, &stderr, "test")
	var env Envelope
	if err := json.Unmarshal(stdout.Bytes(), &env); err != nil {
		t.Fatalf("invalid entrypoint JSON: %v; stdout=%s stderr=%s", err, stdout.String(), stderr.String())
	}
	if code != ExitCodeForStatus(env.Status) {
		t.Fatalf("status/code mismatch: %s %d", env.Status, code)
	}
	return code, env
}

func TestQuickShadowCLIEntrypointReadsRealOwnerWithoutWrites(t *testing.T) {
	service, doc := shadowTestRepo(t)
	before := shadowTestFiles(t, service.projectRoot)
	code, env := runQuickShadowEntry(t, "quick", "context-shadow",
		"--workspace", doc.Workspace, "--item", "Q1",
		"--project-root", service.projectRoot, "--format", "json")
	if code != 0 || env.Data["authorizes_execution"] != false ||
		env.Data["claim_ready"] != false || len(env.NextArgv) != 0 {
		t.Fatal(env)
	}
	report, ok := env.Data["report"].(map[string]any)
	if !ok || report["workspace"] != doc.Workspace || report["item_id"] != "Q1" ||
		report["authorizes_execution"] != false || report["live_code_verified"] != false {
		t.Fatal("report lost selection or boundary", report)
	}
	loaded, err := service.loadConfirmation(filepath.Join(service.projectRoot, ".planning", "quick", doc.Workspace))
	if err != nil {
		t.Fatal(err)
	}
	owner, ready, _, err := compileQuickWorkerPacket(loaded, "Q1")
	if err != nil || !ready {
		t.Fatal(err)
	}
	want, _ := json.Marshal(owner)
	got, _ := json.Marshal(report["owner_packet"])
	if !bytes.Equal(want, got) {
		t.Fatal("legacy owner contract was not preserved")
	}
	if !reflect.DeepEqual(before, shadowTestFiles(t, service.projectRoot)) {
		t.Fatal("read-only public command wrote project/Git files")
	}
}

func TestQuickShadowCLIEntrypointBlocksDependenciesWithoutRepair(t *testing.T) {
	service, doc := shadowTestRepo(t)
	before := shadowTestFiles(t, service.projectRoot)
	code, env := runQuickShadowEntry(t, "quick", "context-shadow",
		"--workspace", doc.Workspace, "--item", "Q2", "--project-root", service.projectRoot)
	if code != 10 || len(env.NextArgv) != 0 || env.Data["authorizes_execution"] != false {
		t.Fatal(env)
	}
	if _, present := env.Data["report"]; present {
		t.Fatal("blocked query returned partial report")
	}
	if !reflect.DeepEqual(before, shadowTestFiles(t, service.projectRoot)) {
		t.Fatal("blocked diagnostic repaired state")
	}
}

func TestQuickShadowCLIEntrypointHelpBeforeRepositoryAccess(t *testing.T) {
	missing := filepath.Join(t.TempDir(), "not-created")
	code, env := runQuickShadowEntry(t, "quick", "context-shadow", "--help", "--project-root", missing)
	if code != 0 || env.Data["usage"] != quickShadowCommandUsage {
		t.Fatal(env)
	}
	if _, err := os.Stat(missing); !os.IsNotExist(err) {
		t.Fatal("help created a project")
	}
	// Must hit the strict subcommand parser rather than the generic help scan.
	code, _ = runQuickShadowEntry(t, "quick", "context-shadow", "--help", "--force")
	if code != 2 {
		t.Fatal("unknown mutation flag was swallowed by generic help")
	}
}

func TestQuickShadowCLIEntrypointFreshStateOnEveryInvocation(t *testing.T) {
	service, doc := shadowTestRepo(t)
	args := []string{"quick", "context-shadow", "--workspace", doc.Workspace, "--item", "Q1", "--project-root", service.projectRoot}
	_, first := runQuickShadowEntry(t, args...)
	doc.UpdatedAt = "2026-09-17T10:00:00Z" // Not part of the decision-only digest.
	shadowTestWrite(t, service.projectRoot, doc)
	code, second := runQuickShadowEntry(t, args...)
	if code != 0 {
		t.Fatal(second)
	}
	a := first.Data["report"].(map[string]any)
	b := second.Data["report"].(map[string]any)
	if a["source_fingerprint"] == b["source_fingerprint"] {
		t.Fatal("old snapshot reused after state-only change")
	}
}

func TestQuickShadowCLIEntrypointDiscoveryAgrees(t *testing.T) {
	if !containsCapability(defaultCapabilities(), quickShadowCapability) ||
		capabilitySummary(quickShadowCapability) != quickShadowSummary {
		t.Fatal("capability missing from registry")
	}
	count := 0
	for _, id := range defaultCapabilities() {
		if id == quickShadowCapability {
			count++
		}
	}
	if count != 1 {
		t.Fatal("duplicate capability")
	}
	_, generalHelp := runQuickShadowEntry(t, "quick", "--help")
	if _, ok := generalHelp.Data["context_shadow"]; !ok {
		t.Fatal("general Quick help missing shadow descriptor")
	}
	_, help := runQuickShadowEntry(t, "quick", "context-shadow", "--help")
	code, show := runQuickShadowEntry(t, "api", "show", quickShadowCapability, "--format", "json")
	if code != 0 {
		t.Fatal(show)
	}
	code, pack := runQuickShadowEntry(t, "api", "pack", "--capabilities", quickShadowCapability, "--format", "json")
	if code != 0 || len(pack.Items) != 1 {
		t.Fatal(pack)
	}
	descriptor := show.Data["capability"].(map[string]any)
	packed := pack.Items[0].(map[string]any)
	if descriptor["side_effect"] != "read-only" || packed["side_effect"] != "read-only" ||
		!reflect.DeepEqual(descriptor["output_contract"], help.Data["output_contract"]) ||
		!reflect.DeepEqual(packed["output_contract"], help.Data["output_contract"]) {
		t.Fatal("pack/show/help lost shared non-authority contract")
	}
	code, ensure := runQuickShadowEntry(t, "api", "ensure", "--capabilities", quickShadowCapability, "--format", "json")
	if code != 0 {
		t.Fatal(ensure)
	}
	_, handshake := runQuickShadowEntry(t, "api", "handshake", "--format", "json")
	found := false
	for _, id := range handshake.Data["capability_ids"].([]any) {
		found = found || id == quickShadowCapability
	}
	if !found {
		t.Fatal("handshake failed to advertise capability")
	}
}

func TestQuickShadowCLIEntrypointUsesQueryTimeout(t *testing.T) {
	if !isShortRuntimeQuery([]string{"quick", "context-shadow", "--workspace", "demo", "--item", "Q1"}) {
		t.Fatal("read-only diagnostic does not use query timeout")
	}
	if isShortRuntimeQuery([]string{"quick", "item-start", "demo", "--item", "Q1"}) {
		t.Fatal("mutation timeout classification was changed")
	}
}

func TestQuickShadowCLIEntrypointCancelledBeforeProjectAccess(t *testing.T) {
	ctx, cancel := context.WithCancel(context.Background())
	cancel()
	root := filepath.Join(t.TempDir(), "must-not-create")
	var stdout, stderr bytes.Buffer
	code := RunContext(ctx, []string{"quick", "context-shadow", "--workspace", "demo", "--item", "Q1", "--project-root", root}, &stdout, &stderr, "test")
	var env Envelope
	if err := json.Unmarshal(stdout.Bytes(), &env); err != nil {
		t.Fatal(err)
	}
	if code != 10 || env.Data["error_code"] != "quick-shadow-cancelled" || len(env.NextArgv) != 0 {
		t.Fatal(code, env)
	}
	if _, err := os.Stat(root); !os.IsNotExist(err) {
		t.Fatal("cancelled command touched missing project")
	}
}

func TestQuickShadowCLIEntrypointCancellationReachesGit(t *testing.T) {
	root, marker := shadowInstallGitHelper(t, "hang")
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	var stdout, stderr bytes.Buffer
	done := make(chan int, 1)
	go func() {
		done <- RunContext(ctx, []string{"quick", "context-shadow", "--workspace", "demo", "--item", "Q1", "--project-root", root}, &stdout, &stderr, "test")
	}()
	deadline := time.After(3 * time.Second)
	for {
		if _, err := os.Stat(marker); err == nil {
			break
		}
		select {
		case code := <-done:
			t.Fatalf("entrypoint returned before starting child: %d", code)
		case <-deadline:
			t.Fatal("entrypoint did not reach the Git reader")
		case <-time.After(5 * time.Millisecond):
		}
	}
	cancel()
	select {
	case code := <-done:
		var env Envelope
		if err := json.Unmarshal(stdout.Bytes(), &env); err != nil {
			t.Fatal(err)
		}
		if code != 10 || env.Data["error_code"] != "quick-shadow-cancelled" {
			t.Fatal(code, env)
		}
		if _, ok := env.Data["report"]; ok {
			t.Fatal("cancelled entrypoint emitted snapshot")
		}
	case <-time.After(2 * time.Second):
		t.Fatal("RunContext cancellation was not propagated")
	}
}

func TestQuickShadowCLIEntrypointPreservesLegacyDescriptors(t *testing.T) {
	for _, id := range []string{"api.ensure", "quick.item-start", "quick.item-accept", "artifact.show"} {
		var old bytes.Buffer
		want := runAPIShow([]string{id, "--format", "json"}, &old)
		var got, stderr bytes.Buffer
		code := Run([]string{"api", "show", id, "--format", "json"}, &got, &stderr, "test")
		if code != want || !bytes.Equal(old.Bytes(), got.Bytes()) {
			t.Fatalf("legacy descriptor changed for %s", id)
		}
	}
}

func TestQuickShadowCLIEntrypointShowSelectorsAndMixedPack(t *testing.T) {
	code, byID := runQuickShadowEntry(t, "api", "show", "--id", quickShadowCapability, "--format", "json")
	if code != 0 || byID.Data["capability"].(map[string]any)["side_effect"] != "read-only" {
		t.Fatal(byID)
	}
	code, mixed := runQuickShadowEntry(t, "api", "pack", "--capabilities", "quick.item-start,"+quickShadowCapability, "--format", "json")
	if code != 0 || len(mixed.Items) != 2 {
		t.Fatal(mixed)
	}
	old := mixed.Items[0].(map[string]any)
	shadow := mixed.Items[1].(map[string]any)
	if old["side_effect"] == "read-only" || shadow["side_effect"] != "read-only" ||
		shadow["output_contract"].(map[string]any)["authorizes_execution"] != false {
		t.Fatal("mixed pack confused read and write contracts")
	}
	code, missing := runQuickShadowEntry(t, "api", "show", "quick.context-shadow-unknown", "--format", "json")
	if code != 2 || missing.Status != "usage-error" {
		t.Fatal("unknown capability was accepted", missing)
	}
}
