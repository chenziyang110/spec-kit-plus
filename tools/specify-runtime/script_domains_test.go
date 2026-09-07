package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestQuickStateListCloseArchiveParity(t *testing.T) {
	root := t.TempDir()
	workspace := filepath.Join(root, ".planning", "quick", "260724-001-fix-login")
	mustMkdirAllScriptDomainTest(t, workspace)
	mustWriteScriptDomainTest(t, filepath.Join(workspace, "STATUS.md"), `---
id: "260724-001"
slug: "fix-login"
title: "Fix login"
status: "gathering"
trigger: "Login fails"
updated: "2026-07-24T00:00:00Z"
---
# Quick Task

## Current Focus

- Confirm failing auth path

## Next Action

- Reproduce the bug
`)

	env := runScriptDomainEnvelope(t, runQuick, []string{"--project-root", root, "list"})
	if env.Status != "ok" {
		t.Fatalf("list status = %s, blockers=%v", env.Status, env.Blockers)
	}
	tasks := env.Data["tasks"].([]any)
	if len(tasks) != 1 {
		t.Fatalf("tasks len = %d", len(tasks))
	}
	task := tasks[0].(map[string]any)
	if task["id"] != "260724-001" || task["current_focus"] != "Confirm failing auth path" || task["next_action"] != "Reproduce the bug" {
		t.Fatalf("unexpected task payload: %#v", task)
	}

	env = runScriptDomainEnvelope(t, runQuick, []string{"--project-root", root, "close", "260724-001", "blocked"})
	if env.Status != "ok" {
		t.Fatalf("close status = %s, blockers=%v", env.Status, env.Blockers)
	}
	task = env.Data["task"].(map[string]any)
	if task["status"] != "blocked" || task["closed_at"] == "" {
		t.Fatalf("close did not update task: %#v", task)
	}

	env = runScriptDomainEnvelope(t, runQuick, []string{"--project-root", root, "archive", "260724-001"})
	task = env.Data["task"].(map[string]any)
	if task["archived"] != true || task["archived_at"] == "" {
		t.Fatalf("archive did not update task: %#v", task)
	}
	if _, err := os.Stat(filepath.Join(root, ".planning", "quick", "archive", "260724-001-fix-login", "STATUS.md")); err != nil {
		t.Fatalf("archived status missing: %v", err)
	}
}

func TestPRDScanInitAndBuildStatusParity(t *testing.T) {
	root := t.TempDir()
	env := runScriptDomainEnvelope(t, runPRDScan, []string{"--project-root", root, "init-scan", "Legacy System"})
	if env.Status != "ok" {
		t.Fatalf("init status = %s, blockers=%v", env.Status, env.Blockers)
	}
	if env.Data["slug"] != "legacy-system" || env.Data["complete"] != true {
		t.Fatalf("unexpected init data: %#v", env.Data)
	}
	workspace := env.Data["workspace"].(string)
	for _, relative := range []string{
		"workflow-state.md",
		"prd-scan.md",
		"coverage-ledger.json",
		"entrypoint-ledger.json",
		"exports",
		"scan-packets",
	} {
		if _, err := os.Stat(filepath.Join(root, ".specify", "prd-runs", workspace, filepath.FromSlash(relative))); err != nil {
			t.Fatalf("expected PRD surface %s: %v", relative, err)
		}
	}

	env = runScriptDomainEnvelope(t, runPRDBuild, []string{"--project-root", root, "status-build", workspace})
	if env.Status != "ok" {
		t.Fatalf("build status = %s, blockers=%v", env.Status, env.Blockers)
	}
	if env.Data["complete"] != false {
		t.Fatalf("build status should be incomplete before exports are written: %#v", env.Data)
	}
	if env.Data["status"] != "blocked" || env.Data["readiness"] != "blocked" {
		t.Fatalf("build semantic status should be blocked before exports are written: %#v", env.Data)
	}
	surfaces := env.Data["surfaces"].(map[string]any)
	if surfaces["workspace"] != true || surfaces["prd_export"] != false {
		t.Fatalf("unexpected build surfaces: %#v", surfaces)
	}
}

func TestPRDScanStatusReportsPartialWorkspaceWithoutRequiringRecordFiles(t *testing.T) {
	root := t.TempDir()
	runID := "260502-partial-prd"
	runDir := filepath.Join(root, ".specify", "prd-runs", runID)
	mustMkdirAllScriptDomainTest(t, filepath.Join(runDir, "evidence"))
	mustWriteScriptDomainTest(t, filepath.Join(runDir, "workflow-state.md"), "# PRD Workflow State\n")

	env := runScriptDomainEnvelope(t, runPRDScan, []string{"--project-root", root, "status", runID})
	if env.Status != "ok" {
		t.Fatalf("partial status = %s, blockers=%v", env.Status, env.Blockers)
	}
	if env.Data["complete"] != false {
		t.Fatalf("partial workspace must remain incomplete: %#v", env.Data)
	}
	surfaces := env.Data["surfaces"].(map[string]any)
	if surfaces["workspace"] != true || surfaces["evidence"] != true || surfaces["coverage_ledger_json"] != false {
		t.Fatalf("unexpected partial surfaces: %#v", surfaces)
	}
	digests := env.Data["record_digests"].(map[string]any)
	if len(digests) != 0 {
		t.Fatalf("missing record surfaces must not emit digests: %#v", digests)
	}
}

func TestPRDScanFinalizeAndLiveFreshnessParity(t *testing.T) {
	requireGit(t)
	root := t.TempDir()
	gitRun(t, root, "init")
	gitRun(t, root, "config", "user.email", "tests@example.com")
	gitRun(t, root, "config", "user.name", "Spec Runtime Tests")
	mustWriteScriptDomainTest(t, filepath.Join(root, "README.md"), "seed\n")
	gitRun(t, root, "add", ".")
	gitRun(t, root, "commit", "-m", "seed")

	env := runScriptDomainEnvelope(t, runPRDScan, []string{"--project-root", root, "init-scan", "Legacy System"})
	workspace := env.Data["workspace"].(string)
	runDir := filepath.Join(root, ".specify", "prd-runs", workspace)
	writeValidPRDScanFixture(t, runDir, workspace, "legacy-system")

	env = runScriptDomainEnvelope(t, runPRDScan, []string{"--project-root", root, "finalize", workspace})
	if env.Status != "ok" {
		t.Fatalf("finalize status = %s, blockers=%v", env.Status, env.Blockers)
	}
	freshness := env.Data["freshness"].(map[string]any)
	if freshness["freshness"] != "fresh" || freshness["non_git_fallback"] != false {
		t.Fatalf("unexpected finalized freshness: %#v", freshness)
	}
	if freshness["current_commit"] == "" || freshness["current_branch"] == "" {
		t.Fatalf("git identity must be explicit: %#v", freshness)
	}

	env = runScriptDomainEnvelope(t, runPRDScan, []string{"--project-root", root, "status", workspace})
	if env.Data["freshness"].(map[string]any)["freshness"] != "fresh" {
		t.Fatalf("status freshness should remain fresh: %#v", env.Data)
	}

	mustWriteScriptDomainTest(t, filepath.Join(runDir, "evidence", "EVD-002.json"), "{\n  \"id\": \"EVD-002\"\n}\n")
	env = runScriptDomainEnvelope(t, runPRDScan, []string{"--project-root", root, "status", workspace})
	if env.Data["freshness"].(map[string]any)["freshness"] != "fresh" {
		t.Fatalf("CLI-owned PRD artifacts must not stale their own source snapshot: %#v", env.Data)
	}

	mustWriteScriptDomainTest(t, filepath.Join(root, "src", "app.go"), "package app\n")
	env = runScriptDomainEnvelope(t, runPRDScan, []string{"--project-root", root, "status", workspace})
	if env.Data["freshness"].(map[string]any)["freshness"] != "targeted-stale" {
		t.Fatalf("status freshness should become targeted-stale after source drift: %#v", env.Data)
	}

	mustWriteScriptDomainTest(t, filepath.Join(root, "package.json"), "{}\n")
	env = runScriptDomainEnvelope(t, runPRDScan, []string{"--project-root", root, "status", workspace})
	if env.Data["freshness"].(map[string]any)["freshness"] != "full-stale" {
		t.Fatalf("status freshness should become full-stale after contract drift: %#v", env.Data)
	}
}

func TestPRDScanFinalizeRejectsManualForcedStaleStatus(t *testing.T) {
	root := t.TempDir()
	env := runScriptDomainEnvelope(t, runPRDScan, []string{"--project-root", root, "init-scan", "Legacy System"})
	workspace := env.Data["workspace"].(string)
	runDir := filepath.Join(root, ".specify", "prd-runs", workspace)
	writeValidPRDScanFixture(t, runDir, workspace, "legacy-system")
	statusPath := filepath.Join(root, ".specify", "prd", "status.json")
	status, err := readJSONMap(statusPath)
	if err != nil {
		t.Fatalf("read status: %v", err)
	}
	status["manual_force_stale"] = true
	status["manual_force_stale_reasons"] = []any{"operator requested rescan"}
	raw, err := json.MarshalIndent(status, "", "  ")
	if err != nil {
		t.Fatal(err)
	}
	mustWriteScriptDomainTest(t, statusPath, string(raw)+"\n")

	env = runScriptDomainEnvelope(t, runPRDScan, []string{"--project-root", root, "finalize", workspace})
	if env.Status == "ok" || !strings.Contains(fmt.Sprint(env.Blockers), "manually forced stale") {
		t.Fatalf("finalize must reject manual stale status: status=%s blockers=%v", env.Status, env.Blockers)
	}
}

func TestClassifyPRDChangedPathMatchesSharedFreshnessContract(t *testing.T) {
	cases := map[string]string{
		"package.json":                          "full-stale",
		"templates/commands/prd-scan.md":        "full-stale",
		"src/specify_cli/integrations/x.py":     "full-stale",
		"src/app.go":                            "targeted-stale",
		"docs/operators/prd.md":                 "targeted-stale",
		"README.md":                             "targeted-stale",
		".specify/prd-runs/run/evidence/x.json": "ignore",
		"web/playwright-report/index.html":      "ignore",
	}
	for path, want := range cases {
		if got := classifyPRDChangedPath(path); got != want {
			t.Errorf("classifyPRDChangedPath(%q) = %q, want %q", path, got, want)
		}
	}
}

func TestPRDBuildStatusReturnsSemanticReadyWhenArtifactsValidate(t *testing.T) {
	requireGit(t)
	root := t.TempDir()
	gitRun(t, root, "init")
	gitRun(t, root, "config", "user.email", "tests@example.com")
	gitRun(t, root, "config", "user.name", "Spec Runtime Tests")
	mustWriteScriptDomainTest(t, filepath.Join(root, "README.md"), "seed\n")
	gitRun(t, root, "add", ".")
	gitRun(t, root, "commit", "-m", "seed")

	env := runScriptDomainEnvelope(t, runPRDScan, []string{"--project-root", root, "init-scan", "Legacy System"})
	workspace := env.Data["workspace"].(string)
	runDir := filepath.Join(root, ".specify", "prd-runs", workspace)
	writeValidPRDScanFixture(t, runDir, workspace, "legacy-system")
	env = runScriptDomainEnvelope(t, runPRDScan, []string{"--project-root", root, "finalize", workspace})
	if env.Status != "ok" {
		t.Fatalf("finalize status = %s, blockers=%v", env.Status, env.Blockers)
	}
	env = runScriptDomainEnvelope(t, runPRDBuild, []string{"--project-root", root, "status-build", workspace})
	if env.Status != "ok" || env.Data["complete"] != false || env.Data["status"] != "ready" || env.Data["readiness"] != "ready-to-build" || env.Data["recovery"] != nil {
		t.Fatalf("finalized scan should authorize PRD build: %#v", env.Data)
	}
	writeValidPRDBuildFixture(t, runDir, workspace, "legacy-system")

	env = runScriptDomainEnvelope(t, runPRDBuild, []string{"--project-root", root, "status-build", workspace})
	if env.Status != "ok" {
		t.Fatalf("build status envelope = %s, blockers=%v", env.Status, env.Blockers)
	}
	if env.Data["complete"] != true || env.Data["status"] != "ready" || env.Data["readiness"] != "complete" || env.Data["recovery"] != nil {
		t.Fatalf("build status should be semantically ready: %#v", env.Data)
	}
	if len(env.Data["errors"].([]any)) != 0 {
		t.Fatalf("build status should not report semantic errors: %#v", env.Data)
	}
}

func TestDiscussionHandoffLifecycleParity(t *testing.T) {
	root := t.TempDir()
	installScaffoldTemplate(t, root, "discussion-handoff-template.json")
	env := runScriptDomainEnvelope(t, runDiscussion, []string{"--project-root", root, "init", "Checkout Flow", "Checkout requirements"})
	if env.Status != "ok" {
		t.Fatalf("init status = %s, blockers=%v", env.Status, env.Blockers)
	}
	slug := env.Data["slug"].(string)
	handoff := discussionHandoffFixture()
	checkpointDiscussionForHandoffFixture(t, root, slug, handoff)
	raw, err := json.Marshal(handoff)
	if err != nil {
		t.Fatal(err)
	}

	env = runScriptDomainEnvelope(t, runDiscussion, []string{"--project-root", root, "write-handoff", slug, "--input-json", string(raw)})
	if env.Status != "ok" {
		t.Fatalf("write-handoff status = %s, blockers=%v", env.Status, env.Blockers)
	}
	digest := env.Data["review_digest"].(string)
	if digest == "" {
		t.Fatalf("missing review digest")
	}

	env = runScriptDomainEnvelope(t, runDiscussion, []string{"--project-root", root, "validate-handoff", slug, "draft"})
	if env.Data["valid"] != true {
		t.Fatalf("draft validation failed: %#v", env.Data)
	}
	env = runScriptDomainEnvelope(t, runDiscussion, []string{"--project-root", root, "confirm-handoff", slug, digest})
	if env.Status != "ok" {
		t.Fatalf("confirm status = %s, blockers=%v", env.Status, env.Blockers)
	}
	env = runScriptDomainEnvelope(t, runDiscussion, []string{"--project-root", root, "mark-ready", slug})
	if env.Status != "ok" {
		t.Fatalf("mark-ready status = %s, blockers=%v", env.Status, env.Blockers)
	}
	discussion := env.Data["discussion"].(map[string]any)
	if discussion["status"] != "handoff-ready" || discussion["next_command"] != "sp-quick" {
		t.Fatalf("discussion not ready: %#v", discussion)
	}
	stateSHA, err := discussionStateSHA256(filepath.Join(root, ".specify", "discussions", slug))
	if err != nil {
		t.Fatal(err)
	}

	consumer := filepath.Join(root, ".planning", "quick", "260724-001-checkout")
	mustMkdirAllScriptDomainTest(t, consumer)
	mustWriteJSONScriptDomainTest(t, filepath.Join(consumer, "handoff-to-specify.json"), map[string]any{
		"discussion_slug":      slug,
		"source_contract":      ".specify/discussions/" + slug + "/handoff-to-specify.json",
		"review_digest":        digest,
		"recommended_consumer": "sp-quick",
		"state_sha256":         stateSHA,
	})
	env = runScriptDomainEnvelope(t, runDiscussion, []string{"--project-root", root, "mark-consumed", slug, ".planning/quick/260724-001-checkout"})
	if env.Status != "ok" {
		t.Fatalf("consume status = %s, blockers=%v", env.Status, env.Blockers)
	}
	discussion = env.Data["discussion"].(map[string]any)
	if discussion["status"] != "completed" || discussion["lifecycle_phase"] != "consumed" {
		t.Fatalf("discussion not consumed: %#v", discussion)
	}
}

func TestDiscussionHandoffAcceptsInlineJSONWithoutDraftFile(t *testing.T) {
	root := t.TempDir()
	installScaffoldTemplate(t, root, "discussion-handoff-template.json")
	env := runScriptDomainEnvelope(t, runDiscussion, []string{"--project-root", root, "init", "Inline Handoff", "Inline requirements"})
	if env.Status != "ok" {
		t.Fatalf("init status = %s, blockers=%v", env.Status, env.Blockers)
	}
	slug := env.Data["slug"].(string)
	handoff := discussionHandoffFixture()
	checkpointDiscussionForHandoffFixture(t, root, slug, handoff)
	raw, err := json.Marshal(handoff)
	if err != nil {
		t.Fatal(err)
	}
	env = runScriptDomainEnvelope(t, runDiscussion, []string{"--project-root", root, "write-handoff", slug, "--input-json", string(raw)})
	if env.Status != "ok" || env.Data["review_digest"] == "" {
		t.Fatalf("inline write-handoff = %#v", env)
	}
	if _, err := os.Stat(filepath.Join(root, "handoff-input.json")); !os.IsNotExist(err) {
		t.Fatalf("inline handoff unexpectedly required a draft file: %v", err)
	}
	stored, err := readJSONMap(filepath.Join(root, ".specify", "discussions", slug, "handoff-to-specify.json"))
	if err != nil {
		t.Fatal(err)
	}
	if _, ok := stored["agent_requirement_contract"].(map[string]any); !ok {
		t.Fatalf("runtime did not expand the stable handoff template: %#v", stored)
	}
	quality, _ := stored["quality_gate"].(map[string]any)
	if quality["status"] != "self_reviewed" || quality["user_review_required"] != true {
		t.Fatalf("runtime did not preserve safe handoff gate defaults: %#v", quality)
	}
}

func TestDiscussionStateInitializesSemanticSnapshotContract(t *testing.T) {
	root := t.TempDir()
	env := runScriptDomainEnvelope(t, runDiscussion, []string{"--project-root", root, "init", "Semantic Snapshot", "Clarify checkout requirements"})
	if env.Status != "ok" {
		t.Fatalf("init status = %s, blockers=%v", env.Status, env.Blockers)
	}
	slug := env.Data["slug"].(string)
	discussion, err := readJSONMap(filepath.Join(root, ".specify", "discussions", slug, "discussion-state.json"))
	if err != nil {
		t.Fatal(err)
	}
	if intValue(discussion["version"]) != 3 {
		t.Fatalf("state version = %#v, want 3", discussion["version"])
	}
	packet := discussion["turn_packet"].(map[string]any)
	if intValue(packet["version"]) != 2 {
		t.Fatalf("turn_packet version = %#v, want 2", packet["version"])
	}
	for _, field := range []string{
		"requirements_snapshot",
		"implementation_target",
		"source_materials",
		"blocking_unknowns",
		"soft_unknowns",
		"conflicts",
		"evidence_checked",
		"advice_confidence",
		"discussion_compass_status",
		"next_discussion_paths",
		"artifact_refs",
		"design_context",
		"ui_discussion_status",
	} {
		if _, ok := packet[field]; !ok {
			t.Fatalf("turn_packet missing durable semantic field %q: %#v", field, packet)
		}
	}
}

func TestDiscussionHandoffValidationRejectsMissingCheckpointSemantics(t *testing.T) {
	root := t.TempDir()
	installScaffoldTemplate(t, root, "discussion-handoff-template.json")
	env := runScriptDomainEnvelope(t, runDiscussion, []string{"--project-root", root, "init", "Missing Materials", "Capture uploaded notes before handoff"})
	if env.Status != "ok" {
		t.Fatalf("init status = %s, blockers=%v", env.Status, env.Blockers)
	}
	slug := env.Data["slug"].(string)
	handoff := discussionHandoffFixture()
	raw, err := json.Marshal(handoff)
	if err != nil {
		t.Fatal(err)
	}
	env = runScriptDomainEnvelope(t, runDiscussion, []string{"--project-root", root, "write-handoff", slug, "--input-json", string(raw)})
	if env.Status == "ok" || !strings.Contains(fmt.Sprint(env.Blockers), "missing_semantic_checkpoint") {
		t.Fatalf("missing checkpoint semantics should block write-handoff: %#v", env)
	}
}

func TestDiscussionHandoffValidationDerivesUnknownAndConflictCounts(t *testing.T) {
	root := t.TempDir()
	installScaffoldTemplate(t, root, "discussion-handoff-template.json")
	env := runScriptDomainEnvelope(t, runDiscussion, []string{"--project-root", root, "init", "Derived Counts", "Do not trust authored counters"})
	if env.Status != "ok" {
		t.Fatalf("init status = %s, blockers=%v", env.Status, env.Blockers)
	}
	slug := env.Data["slug"].(string)
	handoff := discussionHandoffFixture()
	handoff["blocking_unknowns"] = []any{map[string]any{"id": "UNK-001", "question": "Which payment provider?", "owner": "user", "status": "open", "latest_resolve_phase": "prepare"}}
	handoff["conflicts"] = []any{map[string]any{"id": "CON-001", "claim": "Card-only vs wallet support", "status": "open"}}
	handoff["hard_unknown_count"] = float64(0)
	handoff["open_conflict_count"] = float64(0)
	checkpointDiscussionForHandoffFixture(t, root, slug, handoff)
	raw, err := json.Marshal(handoff)
	if err != nil {
		t.Fatal(err)
	}
	env = runScriptDomainEnvelope(t, runDiscussion, []string{"--project-root", root, "write-handoff", slug, "--input-json", string(raw)})
	if env.Status == "ok" || !strings.Contains(fmt.Sprint(env.Blockers), "blocking_unknowns and conflicts") {
		t.Fatalf("open unknowns/conflicts should block write-handoff even when counters claim zero: %#v", env)
	}
}

func TestDiscussionHandoffAllowsBothEligibleConsumersAndLocksSelectedConsumer(t *testing.T) {
	for _, selected := range []string{"sp-quick", "sp-specify"} {
		t.Run(selected, func(t *testing.T) {
			root := t.TempDir()
			installScaffoldTemplate(t, root, "discussion-handoff-template.json")
			env := runScriptDomainEnvelope(t, runDiscussion, []string{"--project-root", root, "init", "User Route Choice", "Choose the downstream route"})
			if env.Status != "ok" {
				t.Fatalf("init status = %s, blockers=%v", env.Status, env.Blockers)
			}
			slug := env.Data["slug"].(string)

			handoff := discussionHandoffFixture()
			handoff["consumer_eligibility"] = map[string]any{
				"sp-specify": map[string]any{"status": "ready"},
				"sp-quick":   map[string]any{"status": "ready"},
			}
			handoff["recommended_consumer"] = selected
			checkpointDiscussionForHandoffFixture(t, root, slug, handoff)
			raw, err := json.Marshal(handoff)
			if err != nil {
				t.Fatal(err)
			}

			env = runScriptDomainEnvelope(t, runDiscussion, []string{"--project-root", root, "write-handoff", slug, "--input-json", string(raw)})
			if env.Status != "ok" {
				t.Fatalf("write-handoff status = %s, blockers=%v", env.Status, env.Blockers)
			}
			digest := env.Data["review_digest"].(string)
			env = runScriptDomainEnvelope(t, runDiscussion, []string{"--project-root", root, "confirm-handoff", slug, "--digest", digest})
			if env.Status != "ok" {
				t.Fatalf("confirm status = %s, blockers=%v", env.Status, env.Blockers)
			}
			env = runScriptDomainEnvelope(t, runDiscussion, []string{"--project-root", root, "mark-ready", slug})
			if env.Status != "ok" {
				t.Fatalf("mark-ready status = %s, blockers=%v", env.Status, env.Blockers)
			}
			discussion := env.Data["discussion"].(map[string]any)
			if discussion["next_command"] != selected {
				t.Fatalf("selected consumer was not locked: %#v", discussion)
			}
		})
	}
}

func TestDiscussionResolveBlocksAmbiguousCandidatesAndBindsExplicitSlug(t *testing.T) {
	root := t.TempDir()
	firstSlug, firstDigest := createReadyDiscussionForConsumer(t, root, "Orders Import", "sp-specify")
	secondSlug, _ := createReadyDiscussionForConsumer(t, root, "Orders Export", "sp-specify")

	env := runScriptDomainEnvelope(t, runDiscussion, []string{
		"--project-root", root, "resolve", "--intent", "sp-specify",
	})
	if env.Status != "blocked" {
		t.Fatalf("ambiguous resolve status = %s, want blocked; env=%#v", env.Status, env)
	}
	candidates, ok := env.Data["candidates"].([]any)
	if !ok || len(candidates) != 2 {
		t.Fatalf("ambiguous resolve candidates = %#v, want both ready discussions", env.Data["candidates"])
	}

	env = runScriptDomainEnvelope(t, runDiscussion, []string{
		"--project-root", root, "resolve", "--intent", "sp-specify", "--slug", firstSlug,
	})
	if env.Status != "ok" {
		t.Fatalf("explicit resolve status = %s, blockers=%v", env.Status, env.Blockers)
	}
	binding := env.Data["binding"].(map[string]any)
	if binding["discussion_slug"] != firstSlug || strings.TrimSpace(fmt.Sprint(binding["state_sha256"])) == "" {
		t.Fatalf("explicit resolve binding missing discussion identity: %#v", binding)
	}
	consumer := binding["consumer"].(map[string]any)
	if consumer["source_contract"] != ".specify/discussions/"+firstSlug+"/handoff-to-specify.json" ||
		consumer["review_digest"] != firstDigest ||
		consumer["recommended_consumer"] != "sp-specify" {
		t.Fatalf("explicit resolve consumer binding = %#v", consumer)
	}
	if binding["selected_slug"] == secondSlug {
		t.Fatalf("explicit resolve selected the wrong discussion: %#v", binding)
	}
}

func TestDiscussionResolveRejectsReadyStatusWithNonReadyLifecycle(t *testing.T) {
	root := t.TempDir()
	slug, reviewDigest := createReadyDiscussionForConsumer(t, root, "Lifecycle Drift", "sp-specify")
	statePath := filepath.Join(root, ".specify", "discussions", slug, "discussion-state.json")
	state, err := readJSONMap(statePath)
	if err != nil {
		t.Fatal(err)
	}
	state["lifecycle_phase"] = "review"
	mustWriteJSONScriptDomainTest(t, statePath, state)

	env := runScriptDomainEnvelope(t, runDiscussion, []string{
		"--project-root", root, "resolve", "--intent", "sp-specify", "--slug", slug,
	})
	if env.Status != "blocked" || env.Data["resolution"] != "explicit_slug_not_eligible" {
		t.Fatalf("resolve accepted a handoff-ready status with non-ready lifecycle: %#v", env)
	}

	featureRel := ".specify/features/2026-08-23-lifecycle-drift"
	mustMkdirAllScriptDomainTest(t, filepath.Join(root, filepath.FromSlash(featureRel)))
	env = runScriptDomainEnvelope(t, runDiscussion, []string{
		"--project-root", root, "bind-consumer", slug,
		"--feature-dir", featureRel,
		"--review-digest", reviewDigest,
		"--input-json", `{"semantic_delta":[],"required_refs":[],"blockers":[],"recovery":null}`,
	})
	if env.Status != "blocked" {
		t.Fatalf("bind-consumer accepted a handoff-ready status with non-ready lifecycle: %#v", env)
	}
}

func TestDiscussionResolveRejectsReadyStateWithDraftSourceContract(t *testing.T) {
	root := t.TempDir()
	slug, reviewDigest := createReadyDiscussionForConsumer(t, root, "Draft Source Drift", "sp-specify")
	handoffPath := filepath.Join(root, ".specify", "discussions", slug, "handoff-to-specify.json")
	handoff, err := readJSONMap(handoffPath)
	if err != nil {
		t.Fatal(err)
	}
	handoff["status"] = "draft"
	mustWriteJSONScriptDomainTest(t, handoffPath, handoff)

	env := runScriptDomainEnvelope(t, runDiscussion, []string{
		"--project-root", root, "resolve", "--intent", "sp-specify", "--slug", slug,
	})
	if env.Status != "blocked" || env.Data["resolution"] != "explicit_slug_not_eligible" {
		t.Fatalf("resolve accepted a draft source contract behind ready state: %#v", env)
	}

	featureRel := ".specify/features/2026-08-23-draft-source-drift"
	mustMkdirAllScriptDomainTest(t, filepath.Join(root, filepath.FromSlash(featureRel)))
	env = runScriptDomainEnvelope(t, runDiscussion, []string{
		"--project-root", root, "bind-consumer", slug,
		"--feature-dir", featureRel,
		"--review-digest", reviewDigest,
		"--input-json", `{"semantic_delta":[],"required_refs":[],"blockers":[],"recovery":null}`,
	})
	if env.Status != "blocked" {
		t.Fatalf("bind-consumer accepted a draft source contract behind ready state: %#v", env)
	}
}

func TestDiscussionResolveRejectsStateContractReviewDigestDrift(t *testing.T) {
	root := t.TempDir()
	slug, _ := createReadyDiscussionForConsumer(t, root, "Digest Drift", "sp-specify")
	statePath := filepath.Join(root, ".specify", "discussions", slug, "discussion-state.json")
	state, err := readJSONMap(statePath)
	if err != nil {
		t.Fatal(err)
	}
	handoff := state["handoff"].(map[string]any)
	handoff["review_digest"] = strings.Repeat("0", 64)
	mustWriteJSONScriptDomainTest(t, statePath, state)

	env := runScriptDomainEnvelope(t, runDiscussion, []string{
		"--project-root", root, "resolve", "--intent", "sp-specify", "--slug", slug,
	})
	if env.Status != "blocked" || env.Data["resolution"] != "explicit_slug_not_eligible" {
		t.Fatalf("resolve accepted divergent state and source review digests: %#v", env)
	}
}

func TestDiscussionCheckpointRequiresExpectedStateSHAWhenMultipleDiscussionsAreIncomplete(t *testing.T) {
	root := t.TempDir()
	env := runScriptDomainEnvelope(t, runDiscussion, []string{"--project-root", root, "init", "Primary", "Primary"})
	slug := env.Data["slug"].(string)
	runScriptDomainEnvelope(t, runDiscussion, []string{"--project-root", root, "init", "Secondary", "Secondary"})

	env = runScriptDomainEnvelope(t, runDiscussion, []string{
		"--project-root", root, "checkpoint", slug, "--input-json", `{"summary":"missing digest"}`,
	})
	if env.Status != "blocked" {
		t.Fatalf("checkpoint without expected state digest = %#v, want blocked", env)
	}

	env = runScriptDomainEnvelope(t, runDiscussion, []string{
		"--project-root", root, "checkpoint", slug, "--expected-state-sha256", "sha256:wrong",
		"--input-json", `{"summary":"wrong digest"}`,
	})
	if env.Status != "blocked" {
		t.Fatalf("checkpoint with stale state digest = %#v, want blocked", env)
	}

	stateDigest, err := fileSHA256(filepath.Join(root, ".specify", "discussions", slug, "discussion-state.json"))
	if err != nil {
		t.Fatal(err)
	}
	env = runScriptDomainEnvelope(t, runDiscussion, []string{
		"--project-root", root, "checkpoint", slug, "--expected-state-sha256", stateDigest,
		"--input-json", `{"summary":"matching digest","lifecycle_phase":"decide"}`,
	})
	if env.Status != "ok" {
		t.Fatalf("checkpoint with matching state digest = %#v, want ok", env)
	}
}

func TestDiscussionCheckpointInvalidInputReturnsSchemaRecovery(t *testing.T) {
	root := t.TempDir()
	env := runScriptDomainEnvelope(t, runDiscussion, []string{"--project-root", root, "init", "Input Recovery", "Input recovery"})
	slug := env.Data["slug"].(string)

	env = runScriptDomainEnvelope(t, runDiscussion, []string{
		"--project-root", root, "checkpoint", slug,
		"--input-json", `{"summary":`,
	})
	if env.Status != "invalid" {
		t.Fatalf("invalid checkpoint input = %#v, want invalid", env)
	}
	if saved, ok := env.Data["checkpoint_saved"].(bool); !ok || saved {
		t.Fatalf("invalid checkpoint saved marker = %#v, want false", env.Data)
	}
	if len(env.ShowArgv) < 6 || env.ShowArgv[1] != "api" || env.ShowArgv[2] != "schema" || env.ShowArgv[3] != "discussion-checkpoint-input" {
		t.Fatalf("invalid checkpoint show argv = %#v, want checkpoint schema recovery", env.ShowArgv)
	}
}

func TestDiscussionCheckpointStaleStateReturnsResolveRecovery(t *testing.T) {
	root := t.TempDir()
	env := runScriptDomainEnvelope(t, runDiscussion, []string{"--project-root", root, "init", "State Recovery", "State recovery"})
	slug := env.Data["slug"].(string)

	env = runScriptDomainEnvelope(t, runDiscussion, []string{
		"--project-root", root, "checkpoint", slug,
		"--expected-state-sha256", strings.Repeat("f", 64),
		"--input-json", `{"summary":"stale"}`,
	})
	if env.Status != "blocked" {
		t.Fatalf("stale checkpoint = %#v, want blocked", env)
	}
	if saved, ok := env.Data["checkpoint_saved"].(bool); !ok || saved {
		t.Fatalf("stale checkpoint saved marker = %#v, want false", env.Data)
	}
	if len(env.NextArgv) < 8 || env.NextArgv[1] != "discussion" || env.NextArgv[2] != "resolve" || optionValue(env.NextArgv, "--slug", "") != slug {
		t.Fatalf("stale checkpoint next argv = %#v, want slug-bound resolve recovery", env.NextArgv)
	}
}

func TestDiscussionCheckpointArchivedDiscussionDoesNotAdvertiseResolveRetry(t *testing.T) {
	root := t.TempDir()
	env := runScriptDomainEnvelope(t, runDiscussion, []string{"--project-root", root, "init", "Archived Recovery", "Archived recovery"})
	slug := env.Data["slug"].(string)

	env = runScriptDomainEnvelope(t, runDiscussion, []string{
		"--project-root", root, "close", slug, "--status", "completed",
	})
	if env.Status != "ok" {
		t.Fatalf("close discussion = %#v, want ok", env)
	}

	env = runScriptDomainEnvelope(t, runDiscussion, []string{
		"--project-root", root, "archive", slug,
	})
	if env.Status != "ok" {
		t.Fatalf("archive discussion = %#v, want ok", env)
	}

	env = runScriptDomainEnvelope(t, runDiscussion, []string{
		"--project-root", root, "checkpoint", slug,
		"--input-json", `{"summary":"should stay archived"}`,
	})
	if env.Status != "blocked" {
		t.Fatalf("archived checkpoint = %#v, want blocked", env)
	}
	if recovery, _ := env.Data["recovery_kind"].(string); recovery == "resolve-session-and-retry" {
		t.Fatalf("archived checkpoint recovery_kind = %q, want blocker-only recovery", recovery)
	}
	if len(env.NextArgv) != 0 {
		t.Fatalf("archived checkpoint next argv = %#v, want no automatic resolve retry", env.NextArgv)
	}
}

func TestDiscussionCheckpointRejectsStaleDigestAfterConcurrentWriterCommits(t *testing.T) {
	root := t.TempDir()
	env := runScriptDomainEnvelope(t, runDiscussion, []string{"--project-root", root, "init", "Serialized Checkpoint", "Serialized checkpoint"})
	slug := env.Data["slug"].(string)
	stateDigest, err := fileSHA256(filepath.Join(root, ".specify", "discussions", slug, "discussion-state.json"))
	if err != nil {
		t.Fatal(err)
	}

	entered, release, restore := installDiscussionMutationBarrierForTest(t, "checkpoint", slug)
	defer restore()

	firstDone := make(chan Envelope, 1)
	go func() {
		firstDone <- runScriptDomainEnvelope(t, runDiscussion, []string{
			"--project-root", root, "checkpoint", slug,
			"--expected-state-sha256", stateDigest,
			"--input-json", `{"summary":"first writer","lifecycle_phase":"decide"}`,
		})
	}()

	<-entered
	secondDone := make(chan Envelope, 1)
	go func() {
		secondDone <- runScriptDomainEnvelope(t, runDiscussion, []string{
			"--project-root", root, "checkpoint", slug,
			"--expected-state-sha256", stateDigest,
			"--input-json", `{"summary":"second writer","lifecycle_phase":"ground"}`,
		})
	}()

	close(release)
	first := <-firstDone
	second := <-secondDone
	if first.Status != "ok" {
		t.Fatalf("first checkpoint writer = %#v, want ok", first)
	}
	if second.Status != "blocked" {
		t.Fatalf("second checkpoint writer = %#v, want stale-digest rejection", second)
	}
	if !strings.Contains(strings.ToLower(fmt.Sprint(second.Blockers)), "stale") && !strings.Contains(strings.ToLower(fmt.Sprint(second.Blockers)), "state_sha256") {
		t.Fatalf("second checkpoint blockers = %#v, want stale digest evidence", second.Blockers)
	}
}

func TestDiscussionWriteHandoffRequiresExpectedStateSHAWhenMultipleDiscussionsAreIncomplete(t *testing.T) {
	root := t.TempDir()
	installScaffoldTemplate(t, root, "discussion-handoff-template.json")
	env := runScriptDomainEnvelope(t, runDiscussion, []string{"--project-root", root, "init", "Primary Handoff", "Primary"})
	slug := env.Data["slug"].(string)
	handoff := discussionHandoffFixture()
	stateDigest := checkpointDiscussionForHandoffFixture(t, root, slug, handoff)
	runScriptDomainEnvelope(t, runDiscussion, []string{"--project-root", root, "init", "Secondary Handoff", "Secondary"})
	raw, err := json.Marshal(handoff)
	if err != nil {
		t.Fatal(err)
	}

	env = runScriptDomainEnvelope(t, runDiscussion, []string{
		"--project-root", root, "write-handoff", slug, "--input-json", string(raw),
	})
	if env.Status != "blocked" {
		t.Fatalf("write-handoff without expected state digest = %#v, want blocked", env)
	}

	env = runScriptDomainEnvelope(t, runDiscussion, []string{
		"--project-root", root, "write-handoff", slug, "--expected-state-sha256", stateDigest,
		"--input-json", string(raw),
	})
	if env.Status != "ok" {
		t.Fatalf("write-handoff with matching state digest = %#v, want ok", env)
	}
}

func TestDiscussionWriteHandoffRejectsStaleDigestAfterConcurrentWriterCommits(t *testing.T) {
	root := t.TempDir()
	installScaffoldTemplate(t, root, "discussion-handoff-template.json")
	env := runScriptDomainEnvelope(t, runDiscussion, []string{"--project-root", root, "init", "Serialized Handoff", "Serialized handoff"})
	slug := env.Data["slug"].(string)
	handoff := discussionHandoffFixture()
	stateDigest := checkpointDiscussionForHandoffFixture(t, root, slug, handoff)
	raw, err := json.Marshal(handoff)
	if err != nil {
		t.Fatal(err)
	}

	entered, release, restore := installDiscussionMutationBarrierForTest(t, "write-handoff-json", slug)
	defer restore()

	firstDone := make(chan Envelope, 1)
	go func() {
		firstDone <- runScriptDomainEnvelope(t, runDiscussion, []string{
			"--project-root", root, "write-handoff", slug,
			"--expected-state-sha256", stateDigest,
			"--input-json", string(raw),
		})
	}()

	<-entered
	secondDone := make(chan Envelope, 1)
	go func() {
		secondDone <- runScriptDomainEnvelope(t, runDiscussion, []string{
			"--project-root", root, "write-handoff", slug,
			"--expected-state-sha256", stateDigest,
			"--input-json", string(raw),
		})
	}()

	close(release)
	first := <-firstDone
	second := <-secondDone
	if first.Status != "ok" {
		t.Fatalf("first write-handoff writer = %#v, want ok", first)
	}
	if second.Status != "blocked" {
		t.Fatalf("second write-handoff writer = %#v, want stale-digest rejection", second)
	}
	if !strings.Contains(strings.ToLower(fmt.Sprint(second.Blockers)), "stale") && !strings.Contains(strings.ToLower(fmt.Sprint(second.Blockers)), "state_sha256") {
		t.Fatalf("second write-handoff blockers = %#v, want stale digest evidence", second.Blockers)
	}
}

func TestDiscussionBindConsumerWritesDerivedFeaturePointerAndEnablesConsumption(t *testing.T) {
	root := t.TempDir()
	installScaffoldTemplate(t, root, "discussion-handoff-template.json")
	env := runScriptDomainEnvelope(t, runDiscussion, []string{"--project-root", root, "init", "Formal Checkout", "Checkout requirements"})
	slug := env.Data["slug"].(string)
	handoff := discussionHandoffFixture()
	handoff["consumer_eligibility"] = map[string]any{
		"sp-specify": map[string]any{"status": "ready"},
		"sp-quick":   map[string]any{"status": "blocked"},
	}
	handoff["recommended_consumer"] = "sp-specify"
	stateDigest := checkpointDiscussionForHandoffFixture(t, root, slug, handoff)
	raw, err := json.Marshal(handoff)
	if err != nil {
		t.Fatal(err)
	}
	env = runScriptDomainEnvelope(t, runDiscussion, []string{
		"--project-root", root, "write-handoff", slug,
		"--expected-state-sha256", stateDigest,
		"--input-json", string(raw),
	})
	digest := env.Data["review_digest"].(string)
	env = runScriptDomainEnvelope(t, runDiscussion, []string{"--project-root", root, "confirm-handoff", slug, "--digest", digest})
	if env.Status != "ok" {
		t.Fatalf("confirm handoff = %#v", env)
	}
	env = runScriptDomainEnvelope(t, runDiscussion, []string{"--project-root", root, "mark-ready", slug})
	if env.Status != "ok" {
		t.Fatalf("mark ready = %#v", env)
	}

	featureRel := ".specify/features/2026-07-29-checkout"
	feature := filepath.Join(root, filepath.FromSlash(featureRel))
	mustMkdirAllScriptDomainTest(t, feature)
	input := `{"semantic_delta":[],"required_refs":["MP-001"],"blockers":[],"recovery":null}`
	env = runScriptDomainEnvelope(t, runDiscussion, []string{
		"--project-root", root, "bind-consumer", slug,
		"--feature-dir", featureRel,
		"--input-json", input,
	})
	if env.Status != "blocked" {
		t.Fatalf("bind consumer without review digest = %#v, want blocked", env)
	}

	env = runScriptDomainEnvelope(t, runDiscussion, []string{
		"--project-root", root, "bind-consumer", slug,
		"--feature-dir", featureRel,
		"--review-digest", digest,
		"--input-json", input,
	})
	if env.Status != "ok" || env.Data["status"] != "ready" || env.Data["next_action"] != "/sp.plan" {
		t.Fatalf("bind consumer with review digest = %#v", env)
	}
	pointer := filepath.Join(feature, "brainstorming", "handoff-to-specify.json")
	payload, err := readJSONMap(pointer)
	if err != nil {
		t.Fatal(err)
	}
	if payload["discussion_slug"] != slug || payload["review_digest"] != digest || payload["entry_source"] != "sp-discussion" {
		t.Fatalf("consumer pointer = %#v", payload)
	}
	if payload["source_contract"] != ".specify/discussions/"+slug+"/handoff-to-specify.json" {
		t.Fatalf("consumer source contract = %#v", payload["source_contract"])
	}
	if payload["recommended_consumer"] != "sp-specify" {
		t.Fatalf("consumer recommended_consumer = %#v, want sp-specify", payload["recommended_consumer"])
	}
	if strings.TrimSpace(fmt.Sprint(payload["state_sha256"])) == "" {
		t.Fatalf("consumer pointer missing state_sha256: %#v", payload)
	}
	env = runScriptDomainEnvelope(t, runDiscussion, []string{
		"--project-root", root, "bind-consumer", slug,
		"--feature-dir", featureRel,
		"--review-digest", digest,
		"--input-json", input,
	})
	if env.Status != "ok" {
		t.Fatalf("idempotent bind consumer = %#v", env)
	}

	env = runScriptDomainEnvelope(t, runDiscussion, []string{"--project-root", root, "mark-consumed", slug, "--feature-dir", featureRel})
	if env.Status != "ok" {
		t.Fatalf("mark consumed from bound pointer = %#v", env)
	}
}

func TestDiscussionBindConsumerRequiresReviewDigestWhenMultipleReadySpecifyHandoffsExist(t *testing.T) {
	root := t.TempDir()
	firstSlug, firstDigest := createReadyDiscussionForConsumer(t, root, "Payment Auth", "sp-specify")
	createReadyDiscussionForConsumer(t, root, "Payment Capture", "sp-specify")
	featureRel := ".specify/features/2026-08-22-payment-auth"
	mustMkdirAllScriptDomainTest(t, filepath.Join(root, filepath.FromSlash(featureRel)))
	input := `{"semantic_delta":[],"required_refs":["MP-001"],"blockers":[],"recovery":null}`

	env := runScriptDomainEnvelope(t, runDiscussion, []string{
		"--project-root", root, "bind-consumer", firstSlug,
		"--feature-dir", featureRel,
		"--input-json", input,
	})
	if env.Status != "blocked" {
		t.Fatalf("bind-consumer without review digest = %#v, want blocked", env)
	}

	env = runScriptDomainEnvelope(t, runDiscussion, []string{
		"--project-root", root, "bind-consumer", firstSlug,
		"--feature-dir", featureRel,
		"--review-digest", firstDigest,
		"--input-json", input,
	})
	if env.Status != "ok" {
		t.Fatalf("bind-consumer with matching review digest = %#v, want ok", env)
	}
}

func TestDiscussionBindConsumerRequiresReviewDigestEvenForSingleReadySpecifyHandoff(t *testing.T) {
	root := t.TempDir()
	slug, digest := createReadyDiscussionForConsumer(t, root, "Single Ready", "sp-specify")
	featureRel := ".specify/features/2026-08-22-single-ready"
	mustMkdirAllScriptDomainTest(t, filepath.Join(root, filepath.FromSlash(featureRel)))
	input := `{"semantic_delta":[],"required_refs":["MP-001"],"blockers":[],"recovery":null}`

	env := runScriptDomainEnvelope(t, runDiscussion, []string{
		"--project-root", root, "bind-consumer", slug,
		"--feature-dir", featureRel,
		"--input-json", input,
	})
	if env.Status != "blocked" {
		t.Fatalf("bind-consumer without review digest on single ready handoff = %#v, want blocked", env)
	}

	env = runScriptDomainEnvelope(t, runDiscussion, []string{
		"--project-root", root, "bind-consumer", slug,
		"--feature-dir", featureRel,
		"--review-digest", digest,
		"--input-json", input,
	})
	if env.Status != "ok" {
		t.Fatalf("bind-consumer with review digest on single ready handoff = %#v, want ok", env)
	}
}

func TestDiscussionBindConsumerRejectsFeatureBoundToDifferentDiscussion(t *testing.T) {
	root := t.TempDir()
	installScaffoldTemplate(t, root, "discussion-handoff-template.json")
	env := runScriptDomainEnvelope(t, runDiscussion, []string{"--project-root", root, "init", "Current Prompt Modes", "Current requirements"})
	slug := env.Data["slug"].(string)
	handoff := discussionHandoffFixture()
	handoff["consumer_eligibility"] = map[string]any{
		"sp-specify": map[string]any{"status": "ready"},
		"sp-quick":   map[string]any{"status": "blocked"},
	}
	handoff["recommended_consumer"] = "sp-specify"
	checkpointDiscussionForHandoffFixture(t, root, slug, handoff)
	raw, err := json.Marshal(handoff)
	if err != nil {
		t.Fatal(err)
	}
	env = runScriptDomainEnvelope(t, runDiscussion, []string{"--project-root", root, "write-handoff", slug, "--input-json", string(raw)})
	digest := env.Data["review_digest"].(string)
	env = runScriptDomainEnvelope(t, runDiscussion, []string{"--project-root", root, "confirm-handoff", slug, "--digest", digest})
	if env.Status != "ok" {
		t.Fatalf("confirm handoff = %#v", env)
	}
	env = runScriptDomainEnvelope(t, runDiscussion, []string{"--project-root", root, "mark-ready", slug})
	if env.Status != "ok" {
		t.Fatalf("mark ready = %#v", env)
	}

	featureRel := ".specify/features/2026-08-03-prompt-hub"
	feature := filepath.Join(root, filepath.FromSlash(featureRel))
	pointer := filepath.Join(feature, "brainstorming", "handoff-to-specify.json")
	existing := map[string]any{
		"discussion_slug": "old-prompt-hub",
		"source_contract": ".specify/discussions/old-prompt-hub/handoff-to-specify.json",
		"review_digest":   "sha256:old-review",
	}
	mustWriteJSONScriptDomainTest(t, pointer, existing)

	env = runScriptDomainEnvelope(t, runDiscussion, []string{
		"--project-root", root, "bind-consumer", slug,
		"--feature-dir", featureRel,
		"--review-digest", digest,
		"--input-json", `{"semantic_delta":[],"required_refs":[],"blockers":[],"recovery":null}`,
	})
	if env.Status != "blocked" {
		t.Fatalf("cross-discussion bind = %#v, want blocked", env)
	}
	if !strings.Contains(fmt.Sprint(env.Blockers), "already bound to a different discussion contract") {
		t.Fatalf("cross-discussion blocker = %#v", env.Blockers)
	}
	stored, err := readJSONMap(pointer)
	if err != nil {
		t.Fatal(err)
	}
	if stored["discussion_slug"] != existing["discussion_slug"] || stored["review_digest"] != existing["review_digest"] {
		t.Fatalf("existing consumer binding was overwritten: %#v", stored)
	}
}

func TestDiscussionCheckpointPersistsTopicOwnership(t *testing.T) {
	root := t.TempDir()
	env := runScriptDomainEnvelope(t, runDiscussion, []string{"--project-root", root, "init", "Topic Owner", "Topic ownership"})
	slug := env.Data["slug"].(string)
	ownership := `{"anchor":"checkout","owned_scope":["checkout requirements"],"routed_topics":[{"topic":"billing export","route":"branch_new","target_slug":"billing-export"}]}`

	env = runScriptDomainEnvelope(t, runDiscussion, []string{
		"--project-root", root, "checkpoint", slug,
		"--input-json", `{"summary":"topic ownership","topic_ownership":` + ownership + `}`,
	})
	if env.Status != "ok" {
		t.Fatalf("checkpoint topic ownership = %#v, want ok", env)
	}
	packet := env.Data["turn_packet"].(map[string]any)
	if fmt.Sprint(packet["topic_ownership"]) == "" {
		t.Fatalf("turn_packet missing topic_ownership: %#v", packet)
	}
}

func TestDiscussionCheckpointRejectsMismatchedTopicOwner(t *testing.T) {
	root := t.TempDir()
	env := runScriptDomainEnvelope(t, runDiscussion, []string{"--project-root", root, "init", "Topic Owner Reject", "Topic owner reject"})
	slug := env.Data["slug"].(string)

	env = runScriptDomainEnvelope(t, runDiscussion, []string{
		"--project-root", root, "checkpoint", slug,
		"--input-json", `{"summary":"bad owner","topic_ownership":{"owner_slug":"other-discussion","anchor":"checkout","owned_scope":["checkout requirements"],"routed_topics":[]}}`,
	})
	if env.Status != "blocked" {
		t.Fatalf("checkpoint accepted mismatched topic owner = %#v, want blocked", env)
	}
}

func TestDiscussionHandoffCarriesTopicOwnershipFromCurrentState(t *testing.T) {
	root := t.TempDir()
	installScaffoldTemplate(t, root, "discussion-handoff-template.json")
	env := runScriptDomainEnvelope(t, runDiscussion, []string{"--project-root", root, "init", "Owned Handoff", "Owned handoff"})
	slug := env.Data["slug"].(string)
	statePath := filepath.Join(root, ".specify", "discussions", slug, "discussion-state.json")
	state, err := readJSONMap(statePath)
	if err != nil {
		t.Fatal(err)
	}
	packet := state["turn_packet"].(map[string]any)
	packet["topic_ownership"] = map[string]any{
		"anchor":        "checkout",
		"owned_scope":   []any{"checkout requirements"},
		"routed_topics": []any{map[string]any{"topic": "billing export", "route": "branch_new", "target_slug": "billing-export"}},
	}
	mustWriteJSONScriptDomainTest(t, statePath, state)
	handoff := discussionHandoffFixture()
	checkpointDiscussionForHandoffFixture(t, root, slug, handoff)
	raw, err := json.Marshal(handoff)
	if err != nil {
		t.Fatal(err)
	}

	env = runScriptDomainEnvelope(t, runDiscussion, []string{
		"--project-root", root, "write-handoff", slug, "--input-json", string(raw),
	})
	if env.Status != "ok" {
		t.Fatalf("write-handoff = %#v", env)
	}
	storedHandoff, err := readJSONMap(filepath.Join(root, ".specify", "discussions", slug, "handoff-to-specify.json"))
	if err != nil {
		t.Fatal(err)
	}
	ownership, ok := storedHandoff["topic_ownership"].(map[string]any)
	if !ok {
		t.Fatalf("handoff missing topic_ownership: %#v", storedHandoff)
	}
	if ownership["owner_slug"] != slug {
		t.Fatalf("handoff topic ownership = %#v, want owner_slug %q", ownership, slug)
	}
}

func TestDiscussionBindConsumerOverwritesUnboundCreateFeatureScaffold(t *testing.T) {
	root := t.TempDir()
	installScaffoldTemplate(t, root, "discussion-handoff-template.json")
	env := runScriptDomainEnvelope(t, runDiscussion, []string{"--project-root", root, "init", "Unbound Scaffold Bind", "Scaffold requirements"})
	slug := env.Data["slug"].(string)
	handoff := discussionHandoffFixture()
	handoff["consumer_eligibility"] = map[string]any{
		"sp-specify": map[string]any{"status": "ready"},
		"sp-quick":   map[string]any{"status": "blocked"},
	}
	handoff["recommended_consumer"] = "sp-specify"
	checkpointDiscussionForHandoffFixture(t, root, slug, handoff)
	raw, err := json.Marshal(handoff)
	if err != nil {
		t.Fatal(err)
	}
	env = runScriptDomainEnvelope(t, runDiscussion, []string{"--project-root", root, "write-handoff", slug, "--input-json", string(raw)})
	digest := env.Data["review_digest"].(string)
	env = runScriptDomainEnvelope(t, runDiscussion, []string{"--project-root", root, "confirm-handoff", slug, "--digest", digest})
	if env.Status != "ok" {
		t.Fatalf("confirm handoff = %#v", env)
	}
	env = runScriptDomainEnvelope(t, runDiscussion, []string{"--project-root", root, "mark-ready", slug})
	if env.Status != "ok" {
		t.Fatalf("mark ready = %#v", env)
	}

	featureRel := ".specify/features/2026-08-06-flowcore"
	feature := filepath.Join(root, filepath.FromSlash(featureRel))
	pointer := filepath.Join(feature, "brainstorming", "handoff-to-specify.json")
	// Matches templates/brainstorming-handoff-specify-template.json installed by create-feature.
	scaffold := map[string]any{
		"version":         3,
		"status":          "pending",
		"entry_source":    nil,
		"discussion_slug": nil,
		"source_contract": nil,
		"review_digest":   nil,
		"semantic_delta":  []any{},
		"required_refs":   []any{},
		"blockers":        []any{},
		"next_action":     nil,
		"recovery":        nil,
	}
	mustWriteJSONScriptDomainTest(t, pointer, scaffold)

	env = runScriptDomainEnvelope(t, runDiscussion, []string{
		"--project-root", root, "bind-consumer", slug,
		"--feature-dir", featureRel,
		"--review-digest", digest,
		"--input-json", `{"semantic_delta":[],"required_refs":["MP-001"],"blockers":[],"recovery":null}`,
	})
	if env.Status != "ok" {
		t.Fatalf("bind over unbound scaffold = %#v, want ok", env)
	}
	payload, err := readJSONMap(pointer)
	if err != nil {
		t.Fatal(err)
	}
	if payload["discussion_slug"] != slug {
		t.Fatalf("bound slug = %#v, want %q", payload["discussion_slug"], slug)
	}
	if payload["review_digest"] != digest {
		t.Fatalf("bound digest = %#v, want %q", payload["review_digest"], digest)
	}
	if payload["status"] != "ready" {
		t.Fatalf("bound status = %#v, want ready", payload["status"])
	}
}

func TestDiscussionMarkConsumedRejectsMismatchedFormalConsumerStateSHA(t *testing.T) {
	root := t.TempDir()
	slug, digest := createReadyDiscussionForConsumer(t, root, "Formal State SHA", "sp-specify")
	featureRel := ".specify/features/2026-08-22-formal-state-sha"
	feature := filepath.Join(root, filepath.FromSlash(featureRel))
	mustMkdirAllScriptDomainTest(t, feature)
	input := `{"semantic_delta":[],"required_refs":["MP-001"],"blockers":[],"recovery":null}`
	env := runScriptDomainEnvelope(t, runDiscussion, []string{
		"--project-root", root, "bind-consumer", slug,
		"--feature-dir", featureRel,
		"--review-digest", digest,
		"--input-json", input,
	})
	if env.Status != "ok" {
		t.Fatalf("bind formal consumer = %#v", env)
	}

	pointer := filepath.Join(feature, "brainstorming", "handoff-to-specify.json")
	payload, err := readJSONMap(pointer)
	if err != nil {
		t.Fatal(err)
	}
	payload["state_sha256"] = strings.Repeat("0", 64)
	mustWriteJSONScriptDomainTest(t, pointer, payload)

	env = runScriptDomainEnvelope(t, runDiscussion, []string{"--project-root", root, "mark-consumed", slug, "--feature-dir", featureRel})
	if env.Status != "blocked" {
		t.Fatalf("mark-consumed accepted mismatched state_sha256 = %#v, want blocked", env)
	}
}

func TestDiscussionMarkConsumedRejectsMismatchedFormalConsumerRecommendation(t *testing.T) {
	root := t.TempDir()
	slug, digest := createReadyDiscussionForConsumer(t, root, "Formal Recommendation", "sp-specify")
	featureRel := ".specify/features/2026-08-22-formal-recommendation"
	feature := filepath.Join(root, filepath.FromSlash(featureRel))
	mustMkdirAllScriptDomainTest(t, feature)
	input := `{"semantic_delta":[],"required_refs":["MP-001"],"blockers":[],"recovery":null}`
	env := runScriptDomainEnvelope(t, runDiscussion, []string{
		"--project-root", root, "bind-consumer", slug,
		"--feature-dir", featureRel,
		"--review-digest", digest,
		"--input-json", input,
	})
	if env.Status != "ok" {
		t.Fatalf("bind formal consumer = %#v", env)
	}

	pointer := filepath.Join(feature, "brainstorming", "handoff-to-specify.json")
	payload, err := readJSONMap(pointer)
	if err != nil {
		t.Fatal(err)
	}
	payload["recommended_consumer"] = "sp-quick"
	mustWriteJSONScriptDomainTest(t, pointer, payload)

	env = runScriptDomainEnvelope(t, runDiscussion, []string{"--project-root", root, "mark-consumed", slug, "--feature-dir", featureRel})
	if env.Status != "blocked" {
		t.Fatalf("mark-consumed accepted mismatched recommended_consumer = %#v, want blocked", env)
	}
}

func TestDiscussionMarkConsumedRejectsNotReadySourceHandoffAfterBinding(t *testing.T) {
	root := t.TempDir()
	slug, digest := createReadyDiscussionForConsumer(t, root, "Formal Source Drift", "sp-specify")
	featureRel := ".specify/features/2026-08-22-formal-source-drift"
	feature := filepath.Join(root, filepath.FromSlash(featureRel))
	mustMkdirAllScriptDomainTest(t, feature)
	input := `{"semantic_delta":[],"required_refs":["MP-001"],"blockers":[],"recovery":null}`
	env := runScriptDomainEnvelope(t, runDiscussion, []string{
		"--project-root", root, "bind-consumer", slug,
		"--feature-dir", featureRel,
		"--review-digest", digest,
		"--input-json", input,
	})
	if env.Status != "ok" {
		t.Fatalf("bind formal consumer = %#v", env)
	}

	handoffPath := filepath.Join(root, ".specify", "discussions", slug, "handoff-to-specify.json")
	handoff, err := readJSONMap(handoffPath)
	if err != nil {
		t.Fatal(err)
	}
	handoff["status"] = "draft"
	mustWriteJSONScriptDomainTest(t, handoffPath, handoff)

	env = runScriptDomainEnvelope(t, runDiscussion, []string{"--project-root", root, "mark-consumed", slug, "--feature-dir", featureRel})
	if env.Status != "blocked" {
		t.Fatalf("mark-consumed accepted stale/not-ready source handoff = %#v, want blocked", env)
	}
}

func TestDiscussionMarkConsumedRejectsMismatchedStateHandoffContractPath(t *testing.T) {
	root := t.TempDir()
	slug, digest := createReadyDiscussionForConsumer(t, root, "Formal Contract Path", "sp-specify")
	featureRel := ".specify/features/2026-08-22-formal-contract-path"
	feature := filepath.Join(root, filepath.FromSlash(featureRel))
	mustMkdirAllScriptDomainTest(t, feature)
	input := `{"semantic_delta":[],"required_refs":["MP-001"],"blockers":[],"recovery":null}`
	env := runScriptDomainEnvelope(t, runDiscussion, []string{
		"--project-root", root, "bind-consumer", slug,
		"--feature-dir", featureRel,
		"--review-digest", digest,
		"--input-json", input,
	})
	if env.Status != "ok" {
		t.Fatalf("bind formal consumer = %#v", env)
	}

	statePath := filepath.Join(root, ".specify", "discussions", slug, "discussion-state.json")
	state, err := readJSONMap(statePath)
	if err != nil {
		t.Fatal(err)
	}
	handoff := mapValue(state["handoff"])
	handoff["contract_path"] = ".specify/discussions/other/handoff-to-specify.json"
	state["handoff"] = handoff
	mustWriteJSONScriptDomainTest(t, statePath, state)

	env = runScriptDomainEnvelope(t, runDiscussion, []string{"--project-root", root, "mark-consumed", slug, "--feature-dir", featureRel})
	if env.Status != "blocked" {
		t.Fatalf("mark-consumed accepted mismatched state handoff contract_path = %#v, want blocked", env)
	}
}

func TestIsUnboundConsumerHandoff(t *testing.T) {
	if !isUnboundConsumerHandoff(nil) {
		t.Fatal("nil map should be unbound")
	}
	if !isUnboundConsumerHandoff(map[string]any{
		"status":          "pending",
		"discussion_slug": nil,
		"source_contract": nil,
		"review_digest":   nil,
	}) {
		t.Fatal("create-feature scaffold should be unbound")
	}
	if !isUnboundConsumerHandoff(map[string]any{
		"status":          "pending",
		"discussion_slug": "",
		"source_contract": "",
		"review_digest":   "",
	}) {
		t.Fatal("empty binding fields should be unbound")
	}
	if isUnboundConsumerHandoff(map[string]any{
		"discussion_slug": "demo",
		"source_contract": "",
		"review_digest":   "",
	}) {
		t.Fatal("slug-only pointer must be treated as bound")
	}
}

func TestDiscussionBindConsumerRejectsFilesAndIntegrityFieldOverrides(t *testing.T) {
	root := t.TempDir()
	// Bare --input is an input-channel violation (invalid), not a state conflict.
	env := runScriptDomainEnvelope(t, runDiscussion, []string{
		"--project-root", root, "bind-consumer", "demo", "--feature-dir", "specs/demo",
		"--input", "payload.json", "--input-json", `{}`,
	})
	if env.Status != "invalid" || len(env.Blockers) == 0 {
		t.Fatalf("bind-consumer bare --input = %#v, want invalid", env)
	}
	// Agent-authored integrity fields are rejected after the input channel opens.
	env = runScriptDomainEnvelope(t, runDiscussion, []string{
		"--project-root", root, "bind-consumer", "demo", "--feature-dir", "specs/demo",
		"--input-json", `{"semantic_delta":[],"required_refs":[],"blockers":[],"recovery":null,"review_digest":"agent-value"}`,
	})
	if env.Status != "blocked" && env.Status != "invalid" {
		t.Fatalf("bind-consumer integrity override = %#v, want blocked/invalid", env)
	}
	if len(env.Blockers) == 0 {
		t.Fatalf("bind-consumer integrity override missing blockers: %#v", env)
	}
}

func TestDiscussionHandoffRequiresInlineInputChannel(t *testing.T) {
	root := t.TempDir()
	env := runScriptDomainEnvelope(t, runDiscussion, []string{"--project-root", root, "init", "Input Gate", "Input requirements"})
	slug := env.Data["slug"].(string)
	for _, args := range [][]string{
		{"--project-root", root, "write-handoff", slug},
		{"--project-root", root, "write-handoff", slug, "draft.json"},
		{"--project-root", root, "write-handoff", slug, "--input", "draft.json", "--input-json", "{}"},
	} {
		env = runScriptDomainEnvelope(t, runDiscussion, args)
		// Input-channel violations are usage/invalid, not state-blocked.
		if (env.Status != "invalid" && env.Status != "blocked") || len(env.Blockers) == 0 {
			t.Fatalf("write-handoff input gate for %v = %#v", args, env)
		}
	}
}

func TestDiscussionHandoffRequiresSafeInstalledTemplate(t *testing.T) {
	for _, test := range []struct {
		name   string
		tamper bool
	}{
		{name: "missing"},
		{name: "unsafe readiness", tamper: true},
	} {
		t.Run(test.name, func(t *testing.T) {
			root := t.TempDir()
			if test.tamper {
				installScaffoldTemplate(t, root, "discussion-handoff-template.json")
				path := filepath.Join(root, ".specify", "templates", "discussion-handoff-template.json")
				payload, err := readJSONMap(path)
				if err != nil {
					t.Fatal(err)
				}
				payload["planning_gate_status"] = "ready"
				mustWriteJSONScriptDomainTest(t, path, payload)
			}
			env := runScriptDomainEnvelope(t, runDiscussion, []string{"--project-root", root, "init", "Template Gate", "Template requirements"})
			slug := env.Data["slug"].(string)
			handoff := discussionHandoffFixture()
			checkpointDiscussionForHandoffFixture(t, root, slug, handoff)
			raw, err := json.Marshal(handoff)
			if err != nil {
				t.Fatal(err)
			}
			env = runScriptDomainEnvelope(t, runDiscussion, []string{"--project-root", root, "write-handoff", slug, "--input-json", string(raw)})
			if env.Status != "blocked" || !strings.Contains(strings.ToLower(fmt.Sprint(env.Blockers)), "template") {
				t.Fatalf("unsafe discussion template = %#v, want blocked", env)
			}
		})
	}
}

func TestDiscussionHandoffReadyRechecksSnapshotMaterialCoverageAndCounts(t *testing.T) {
	root := t.TempDir()
	installScaffoldTemplate(t, root, "discussion-handoff-template.json")
	env := runScriptDomainEnvelope(t, runDiscussion, []string{"--project-root", root, "init", "Readiness Semantics", "Readiness semantics"})
	if env.Status != "ok" {
		t.Fatalf("init status = %s, blockers=%v", env.Status, env.Blockers)
	}
	slug := env.Data["slug"].(string)

	handoff := discussionHandoffFixture()
	handoff["source_materials"] = []any{map[string]any{
		"id":                "MAT-001",
		"material_type":     "user_note",
		"locator":           "chat:turn-1",
		"inspection_status": "pending",
		"summary":           "User supplied a requirement note.",
		"claims":            []any{"The note must be considered."},
		"coverage_gaps":     []any{"not inspected"},
		"sensitivity":       "safe",
	}}
	checkpointDiscussionForHandoffFixture(t, root, slug, handoff)
	raw, err := json.Marshal(handoff)
	if err != nil {
		t.Fatal(err)
	}
	env = runScriptDomainEnvelope(t, runDiscussion, []string{"--project-root", root, "write-handoff", slug, "--input-json", string(raw)})
	if env.Status != "blocked" || !strings.Contains(fmt.Sprint(env.Blockers), "source_materials") {
		t.Fatalf("uninspected materials should block write-handoff: %#v", env)
	}

	handoff["source_materials"].([]any)[0].(map[string]any)["inspection_status"] = "inspected"
	handoff["source_materials"].([]any)[0].(map[string]any)["coverage_gaps"] = []any{}
	checkpointDiscussionForHandoffFixture(t, root, slug, handoff)
	raw, err = json.Marshal(handoff)
	if err != nil {
		t.Fatal(err)
	}
	env = runScriptDomainEnvelope(t, runDiscussion, []string{"--project-root", root, "write-handoff", slug, "--input-json", string(raw)})
	if env.Status != "ok" {
		t.Fatalf("write-handoff after inspected material = %#v", env)
	}
	digest := env.Data["review_digest"].(string)
	env = runScriptDomainEnvelope(t, runDiscussion, []string{"--project-root", root, "confirm-handoff", slug, "--digest", digest})
	if env.Status != "ok" {
		t.Fatalf("confirm after inspected material = %#v", env)
	}
	env = runScriptDomainEnvelope(t, runDiscussion, []string{"--project-root", root, "checkpoint", slug, "--input-json", `{"summary":"changed after handoff","soft_unknowns":["new softer unknown"]}`})
	if env.Status != "ok" {
		t.Fatalf("checkpoint after handoff = %#v", env)
	}
	env = runScriptDomainEnvelope(t, runDiscussion, []string{"--project-root", root, "mark-ready", slug})
	if env.Status != "blocked" || !strings.Contains(fmt.Sprint(env.Blockers), "discussion_snapshot_digest") {
		t.Fatalf("stale discussion snapshot should block ready: %#v", env)
	}
}

func TestDiscussionHandoffRejectsEmptyRequirementContractEvenWithReadyCounts(t *testing.T) {
	root := t.TempDir()
	installScaffoldTemplate(t, root, "discussion-handoff-template.json")
	env := runScriptDomainEnvelope(t, runDiscussion, []string{"--project-root", root, "init", "Thin Handoff", "Thin requirements"})
	if env.Status != "ok" {
		t.Fatalf("init = %#v", env)
	}
	slug := env.Data["slug"].(string)
	thin := discussionHandoffFixture()
	thin["agent_requirement_contract"] = map[string]any{
		"target_need":               "",
		"actors":                    []any{},
		"scenarios":                 []any{},
		"constraints":               []any{},
		"success_criteria":          []any{},
		"optimal_solution_approach": []any{},
		"scope":                     map[string]any{"in": []any{}},
	}
	checkpointDiscussionForHandoffFixture(t, root, slug, thin)
	raw, err := json.Marshal(thin)
	if err != nil {
		t.Fatal(err)
	}
	env = runScriptDomainEnvelope(t, runDiscussion, []string{
		"--project-root", root, "write-handoff", slug, "--input-json", string(raw),
	})
	if env.Status == "ok" {
		t.Fatalf("write-handoff accepted empty semantic requirement contract: %#v", env)
	}
}

func TestDiscussionCheckpointPersistsCompleteSemanticSnapshotAndResume(t *testing.T) {
	root := t.TempDir()
	env := runScriptDomainEnvelope(t, runDiscussion, []string{"--project-root", root, "init", "Semantic Recovery", "Recover details"})
	if env.Status != "ok" {
		t.Fatalf("init = %#v", env)
	}
	slug := env.Data["slug"].(string)
	payload := map[string]any{
		"summary": "Ready to hand off validated discussion state.",
		"phase":   "prepare",
		"requirements_snapshot": map[string]any{
			"target_need":               "Operators need a recoverable checkout discussion package.",
			"actors":                    []any{"shopper", "operator"},
			"scenarios":                 []any{"resume after compaction"},
			"constraints":               []any{"do not rely on chat memory"},
			"success_criteria":          []any{"resume shows preserved decisions"},
			"design_direction":          []any{"quiet operational UI"},
			"optimal_solution_approach": []any{"use runtime checkpoint and handoff contracts"},
			"non_goals":                 []any{"rewrite checkout implementation"},
			"scope":                     map[string]any{"in": []any{"discussion state"}, "out": []any{"payment gateway"}, "deferred": []any{"analytics"}},
		},
		"implementation_target": map[string]any{
			"actual_project":                  "checkout-service",
			"target_root":                     root,
			"target_paths":                    []any{"src/checkout"},
			"required_target_paths_to_verify": []any{"src/checkout"},
		},
		"source_evidence": []any{
			map[string]any{"source_type": "discussion", "evidence_status": "verified", "source": "chat", "claim": "checkout recovery is required", "material_id": "MAT-001"},
		},
		"source_materials": []any{
			map[string]any{"id": "MAT-001", "material_type": "chat", "locator": "user message", "summary": "User requested recoverable discussion state.", "inspection_status": "inspected", "claims": []any{"checkout recovery is required"}, "coverage_gaps": []any{}, "sensitivity": "safe"},
		},
		"blocking_unknowns":          []any{},
		"soft_unknowns":              []any{"deployment date"},
		"conflicts":                  []any{},
		"downstream_instructions":    map[string]any{"planning_constraints": []any{"preserve runtime checkpoint contract"}, "settled_decisions": []any{"use v3 discussion state"}, "preserved_assumptions": []any{}, "conflicts_requiring_return": []any{}, "capability_map": []any{}, "dependencies": []any{}, "deferred_scope": []any{"analytics"}, "reopen_conditions": []any{"new payment requirement"}},
		"discussion_decision_digest": map[string]any{"locked_direction": []any{"runtime-owned state"}, "must_not_dilute": []any{"material evidence"}},
		"must_preserve":              []any{map[string]any{"id": "MP-001", "type": "requirement", "claim": "State must resume without chat memory", "source": "MAT-001", "downstream_requirement": "Consumers must read handoff JSON", "blocking_level": "hard", "owner": "agent", "latest_resolve_phase": "discussion", "status": "active"}},
		"truth_pass_status":          "complete",
		"verified_project_facts":     []any{"runtime stores discussion-state.json"},
		"evidence_checked":           []any{"tools/specify-runtime/script_domains.go"},
		"advice_confidence":          "high",
		"discussion_compass_status":  "current",
		"next_discussion_paths":      []any{"handoff assessment"},
		"ui_discussion_status":       "offered",
		"design_context":             map[string]any{"ui_involved": true, "surface_type": "product-workspace"},
		"artifact_refs":              []any{".specify/discussions/" + slug + "/discussion-state.json"},
	}
	raw, err := json.Marshal(payload)
	if err != nil {
		t.Fatal(err)
	}
	env = runScriptDomainEnvelope(t, runDiscussion, []string{"--project-root", root, "checkpoint", slug, "--input-json", string(raw)})
	if env.Status != "ok" {
		t.Fatalf("checkpoint = %#v", env)
	}
	packet := env.Data["turn_packet"].(map[string]any)
	if packet["version"] != float64(2) {
		t.Fatalf("checkpoint did not migrate turn_packet version: %#v", packet)
	}
	if packet["truth_pass_status"] != "complete" || packet["discussion_compass_status"] != "current" {
		t.Fatalf("checkpoint lost truth/compass state: %#v", packet)
	}
	materials := packet["source_materials"].([]any)
	material := materials[0].(map[string]any)
	if stringValue(material["material_digest"]) == "" {
		t.Fatalf("checkpoint did not protect source material digest: %#v", material)
	}
	checkpoint := env.Data["discussion"].(map[string]any)["latest_checkpoint"].(map[string]any)
	if stringValue(checkpoint["snapshot_sha256"]) == "" || len(checkpoint["changed_fields"].([]any)) == 0 {
		t.Fatalf("latest checkpoint missing semantic snapshot metadata: %#v", checkpoint)
	}

	env = runScriptDomainEnvelope(t, runDiscussion, []string{"--project-root", root, "resume", slug})
	if env.Status != "ok" {
		t.Fatalf("resume = %#v", env)
	}
	resumePacket := env.Data["turn_packet"].(map[string]any)
	if resumePacket["truth_pass_status"] != "complete" || len(resumePacket["source_materials"].([]any)) != 1 {
		t.Fatalf("resume lost complete semantic packet: %#v", resumePacket)
	}
}

func TestDiscussionHandoffDerivesFromCheckpointAndRejectsSnapshotDrift(t *testing.T) {
	root := t.TempDir()
	installScaffoldTemplate(t, root, "discussion-handoff-template.json")
	env := runScriptDomainEnvelope(t, runDiscussion, []string{"--project-root", root, "init", "Derived Handoff", "Derived handoff"})
	slug := env.Data["slug"].(string)
	semantic := discussionCompleteSemanticCheckpoint(root)
	raw, err := json.Marshal(semantic)
	if err != nil {
		t.Fatal(err)
	}
	env = runScriptDomainEnvelope(t, runDiscussion, []string{"--project-root", root, "checkpoint", slug, "--input-json", string(raw)})
	if env.Status != "ok" {
		t.Fatalf("checkpoint = %#v", env)
	}
	stateDigest := env.Data["binding"].(map[string]any)["state_sha256"].(string)
	draft := map[string]any{
		"handoff_goal": "Implement checkout recovery",
		"quality_gate": map[string]any{"self_reviewed_at": "2026-07-24T00:00:00Z"},
		"consumer_eligibility": map[string]any{
			"sp-specify": map[string]any{"status": "blocked"},
			"sp-quick":   map[string]any{"status": "ready"},
		},
		"recommended_consumer": "sp-quick",
	}
	raw, err = json.Marshal(draft)
	if err != nil {
		t.Fatal(err)
	}
	env = runScriptDomainEnvelope(t, runDiscussion, []string{"--project-root", root, "write-handoff", slug, "--expected-state-sha256", stateDigest, "--input-json", string(raw)})
	if env.Status != "ok" {
		t.Fatalf("write-handoff = %#v", env)
	}
	handoffPath := filepath.Join(root, ".specify", "discussions", slug, "handoff-to-specify.json")
	handoff, err := readJSONMap(handoffPath)
	if err != nil {
		t.Fatal(err)
	}
	if stringValue(handoff["discussion_snapshot_digest"]) == "" {
		t.Fatalf("handoff did not bind discussion snapshot digest: %#v", handoff)
	}
	materials := handoff["source_materials"].([]any)
	if len(materials) != 1 || stringValue(materials[0].(map[string]any)["material_digest"]) == "" {
		t.Fatalf("handoff did not carry protected source materials: %#v", handoff["source_materials"])
	}
	if mapValue(handoff["agent_requirement_contract"])["target_need"] != "Operators need a recoverable checkout discussion package." {
		t.Fatalf("handoff did not derive requirements from checkpoint: %#v", handoff["agent_requirement_contract"])
	}

	reviewDigest := env.Data["review_digest"].(string)
	env = runScriptDomainEnvelope(t, runDiscussion, []string{"--project-root", root, "confirm-handoff", slug, "--digest", reviewDigest})
	if env.Status != "ok" {
		t.Fatalf("confirm = %#v", env)
	}
	statePath := filepath.Join(root, ".specify", "discussions", slug, "discussion-state.json")
	state, err := readJSONMap(statePath)
	if err != nil {
		t.Fatal(err)
	}
	packet := mapValue(state["turn_packet"])
	packet["current_recommendation"] = "Different recommendation after the handoff draft."
	mustWriteJSONScriptDomainTest(t, statePath, state)
	env = runScriptDomainEnvelope(t, runDiscussion, []string{"--project-root", root, "mark-ready", slug})
	if env.Status == "ok" {
		t.Fatalf("mark-ready accepted stale discussion snapshot: %#v", env)
	}
}

func TestDiscussionHandoffRejectsFakeZeroUnknownConflictCountsAndMaterialDigestTamper(t *testing.T) {
	root := t.TempDir()
	installScaffoldTemplate(t, root, "discussion-handoff-template.json")
	env := runScriptDomainEnvelope(t, runDiscussion, []string{"--project-root", root, "init", "Count Tamper", "Count tamper"})
	slug := env.Data["slug"].(string)
	semantic := discussionCompleteSemanticCheckpoint(root)
	semantic["blocking_unknowns"] = []any{map[string]any{"id": "UNK-001", "question": "Which gateway?", "owner": "user", "status": "open", "latest_resolve_phase": "prepare"}}
	semantic["conflicts"] = []any{map[string]any{"id": "CON-001", "claim": "Gateway conflict", "status": "open"}}
	raw, err := json.Marshal(semantic)
	if err != nil {
		t.Fatal(err)
	}
	env = runScriptDomainEnvelope(t, runDiscussion, []string{"--project-root", root, "checkpoint", slug, "--input-json", string(raw)})
	if env.Status != "ok" {
		t.Fatalf("checkpoint = %#v", env)
	}
	draft := discussionHandoffFixture()
	draft["hard_unknown_count"] = float64(0)
	draft["open_conflict_count"] = float64(0)
	raw, err = json.Marshal(draft)
	if err != nil {
		t.Fatal(err)
	}
	env = runScriptDomainEnvelope(t, runDiscussion, []string{"--project-root", root, "write-handoff", slug, "--input-json", string(raw)})
	if env.Status == "ok" {
		t.Fatalf("write-handoff accepted fake zero unknown/conflict counts: %#v", env)
	}

	semantic["blocking_unknowns"] = []any{}
	semantic["conflicts"] = []any{}
	raw, err = json.Marshal(semantic)
	if err != nil {
		t.Fatal(err)
	}
	env = runScriptDomainEnvelope(t, runDiscussion, []string{"--project-root", root, "checkpoint", slug, "--input-json", string(raw)})
	if env.Status != "ok" {
		t.Fatalf("checkpoint clean semantic = %#v", env)
	}
	stateDigest := env.Data["binding"].(map[string]any)["state_sha256"].(string)
	raw, err = json.Marshal(discussionHandoffFixture())
	if err != nil {
		t.Fatal(err)
	}
	env = runScriptDomainEnvelope(t, runDiscussion, []string{"--project-root", root, "write-handoff", slug, "--expected-state-sha256", stateDigest, "--input-json", string(raw)})
	if env.Status != "ok" {
		t.Fatalf("write-handoff clean = %#v", env)
	}
	handoffPath := filepath.Join(root, ".specify", "discussions", slug, "handoff-to-specify.json")
	handoff, err := readJSONMap(handoffPath)
	if err != nil {
		t.Fatal(err)
	}
	material := handoff["source_materials"].([]any)[0].(map[string]any)
	material["summary"] = "tampered summary"
	mustWriteJSONScriptDomainTest(t, handoffPath, handoff)
	env = runScriptDomainEnvelope(t, runDiscussion, []string{"--project-root", root, "validate-handoff", slug, "draft"})
	if env.Data["valid"] == true {
		t.Fatalf("validate-handoff accepted tampered source material digest: %#v", env)
	}
}

func TestDiscussionLegacyV2StateMigratesOnWrite(t *testing.T) {
	root := t.TempDir()
	env := runScriptDomainEnvelope(t, runDiscussion, []string{"--project-root", root, "init", "Legacy V2", "Legacy V2"})
	slug := env.Data["slug"].(string)
	statePath := filepath.Join(root, ".specify", "discussions", slug, "discussion-state.json")
	state, err := readJSONMap(statePath)
	if err != nil {
		t.Fatal(err)
	}
	state["version"] = float64(2)
	packet := mapValue(state["turn_packet"])
	packet["version"] = float64(1)
	mustWriteJSONScriptDomainTest(t, statePath, state)
	env = runScriptDomainEnvelope(t, runDiscussion, []string{
		"--project-root", root, "checkpoint", slug, "--input-json", `{"summary":"migrated","lifecycle_phase":"decide"}`,
	})
	if env.Status != "ok" {
		t.Fatalf("checkpoint legacy v2 = %#v", env)
	}
	updated, err := readJSONMap(statePath)
	if err != nil {
		t.Fatal(err)
	}
	if updated["version"] != float64(3) || mapValue(updated["turn_packet"])["version"] != float64(2) {
		t.Fatalf("legacy v2 state was not migrated on write: %#v", updated)
	}
}

func discussionCompleteSemanticCheckpoint(root string) map[string]any {
	return map[string]any{
		"summary": "Ready to hand off validated discussion state.",
		"phase":   "prepare",
		"requirements_snapshot": map[string]any{
			"target_need":               "Operators need a recoverable checkout discussion package.",
			"actors":                    []any{"shopper", "operator"},
			"scenarios":                 []any{"resume after compaction"},
			"constraints":               []any{"do not rely on chat memory"},
			"success_criteria":          []any{"resume shows preserved decisions"},
			"design_direction":          []any{"quiet operational UI"},
			"optimal_solution_approach": []any{"use runtime checkpoint and handoff contracts"},
			"non_goals":                 []any{"rewrite checkout implementation"},
			"scope":                     map[string]any{"in": []any{"discussion state"}, "out": []any{"payment gateway"}, "deferred": []any{"analytics"}},
		},
		"implementation_target": map[string]any{
			"actual_project":                  "checkout-service",
			"target_root":                     root,
			"target_paths":                    []any{"src/checkout"},
			"required_target_paths_to_verify": []any{"src/checkout"},
		},
		"context_boundary": map[string]any{
			"status": "locked",
			"current_project_roles": []any{
				map[string]any{"role": "implementation_target", "scope": "checkout", "evidence_source": "live repository", "notes": "same project"},
			},
			"target_project_root": root,
			"target_project_roles": []any{
				map[string]any{"role": "implementation_target", "scope": "checkout", "evidence_source": "live repository", "notes": "verified target"},
			},
		},
		"source_evidence":         []any{map[string]any{"source_type": "discussion", "evidence_status": "verified", "source": "MAT-001", "claim": "checkout recovery is required", "material_id": "MAT-001"}},
		"source_materials":        []any{map[string]any{"id": "MAT-001", "material_type": "chat", "locator": "user message", "summary": "User requested recoverable discussion state.", "inspection_status": "inspected", "claims": []any{"checkout recovery is required"}, "coverage_gaps": []any{}, "sensitivity": "safe"}},
		"blocking_unknowns":       []any{},
		"soft_unknowns":           []any{},
		"conflicts":               []any{},
		"downstream_instructions": map[string]any{"planning_constraints": []any{"preserve runtime checkpoint contract"}, "settled_decisions": []any{"use v3 discussion state"}, "preserved_assumptions": []any{}, "conflicts_requiring_return": []any{}, "capability_map": []any{}, "dependencies": []any{}, "deferred_scope": []any{"analytics"}, "reopen_conditions": []any{"new payment requirement"}},
		"discussion_decision_digest": map[string]any{
			"locked_direction":                []any{"runtime-owned state"},
			"rejected_alternatives":           []any{"chat-only memory"},
			"accepted_tradeoffs":              []any{"compact state over transcript"},
			"experience_commitments":          []any{},
			"design_system_requirements":      []any{},
			"review_criteria_carried_forward": []any{"preserve material evidence"},
			"must_not_dilute":                 []any{"material evidence"},
		},
		"must_preserve": []any{map[string]any{"id": "MP-001", "type": "requirement", "claim": "State must resume without chat memory", "source": "MAT-001", "downstream_requirement": "Consumers must read handoff JSON", "blocking_level": "hard", "owner": "agent", "latest_resolve_phase": "discussion", "status": "active"}},
	}
}

func checkpointDiscussionForHandoffFixture(t *testing.T, root, slug string, handoff map[string]any) string {
	t.Helper()
	requirements := handoff["agent_requirement_contract"]
	if _, ok := handoff["agent_requirement_contract"]; !ok {
		requirements = handoff["requirements_snapshot"]
	}
	payload := map[string]any{
		"summary":                 firstNonEmpty(stringValue(handoff["handoff_goal"]), "discussion handoff fixture"),
		"lifecycle_phase":         "prepare",
		"requirements_snapshot":   requirements,
		"implementation_target":   handoff["implementation_target"],
		"context_boundary":        handoff["context_boundary"],
		"source_evidence":         handoff["source_evidence"],
		"source_materials":        handoff["source_materials"],
		"blocking_unknowns":       firstAny(handoff["blocking_unknowns"], []any{}),
		"soft_unknowns":           firstAny(handoff["soft_unknowns"], []any{}),
		"conflicts":               firstAny(handoff["conflicts"], []any{}),
		"downstream_instructions": handoff["downstream_instructions"],
		"discussion_decision_digest": firstAny(handoff["discussion_decision_digest"], map[string]any{
			"locked_direction":                []any{"fixture direction"},
			"rejected_alternatives":           []any{},
			"accepted_tradeoffs":              []any{},
			"experience_commitments":          []any{},
			"design_system_requirements":      []any{},
			"review_criteria_carried_forward": []any{"preserve fixture direction"},
			"must_not_dilute":                 []any{},
		}),
		"must_preserve":             handoff["must_preserve"],
		"truth_pass_status":         "complete",
		"verified_project_facts":    []any{"fixture fact"},
		"evidence_checked":          firstAny(handoff["evidence_checked"], []any{"fixture evidence"}),
		"advice_confidence":         "high",
		"discussion_compass_status": "current",
		"next_discussion_paths":     []any{"handoff review"},
	}
	raw, err := json.Marshal(payload)
	if err != nil {
		t.Fatal(err)
	}
	stateDigest, err := fileSHA256(filepath.Join(root, ".specify", "discussions", slug, "discussion-state.json"))
	if err != nil {
		t.Fatal(err)
	}
	env := runScriptDomainEnvelope(t, runDiscussion, []string{
		"--project-root", root, "checkpoint", slug,
		"--expected-state-sha256", stateDigest,
		"--input-json", string(raw),
	})
	if env.Status != "ok" {
		t.Fatalf("checkpoint handoff fixture = %#v", env)
	}
	return env.Data["binding"].(map[string]any)["state_sha256"].(string)
}

func discussionHandoffFixture() map[string]any {
	role := map[string]any{"role": "source", "scope": "checkout", "evidence_source": "discussion", "notes": "confirmed"}
	return map[string]any{
		"handoff_goal": "Implement checkout flow",
		"agent_requirement_contract": map[string]any{
			"target_need":               "Checkout users need a payment collection flow.",
			"actors":                    []any{"shopper"},
			"scenarios":                 []any{"shopper submits payment during checkout"},
			"constraints":               []any{"preserve payment collection"},
			"success_criteria":          []any{"checkout can collect payment"},
			"design_direction":          []any{},
			"optimal_solution_approach": []any{"plan payment collection as a first-class requirement"},
			"non_goals":                 []any{},
			"scope":                     map[string]any{"in": []any{"payment collection"}, "out": []any{}, "deferred": []any{}},
		},
		"implementation_target": map[string]any{"target_kind": "feature", "actual_project": "spec-kit-plus", "target_root": "<current-project>", "target_project_root": "<current-project>", "target_paths": []any{"templates/commands/discussion.md"}, "required_target_paths_to_verify": []any{}},
		"context_boundary": map[string]any{
			"status":                "locked",
			"current_project_roles": []any{role},
		},
		"source_materials": []any{map[string]any{
			"id":                "MAT-001",
			"material_type":     "chat",
			"locator":           "chat",
			"summary":           "User confirmed checkout payment need.",
			"inspection_status": "inspected",
			"claims":            []any{"checkout is required"},
			"coverage_gaps":     []any{},
			"sensitivity":       "safe",
		}},
		"source_evidence":   []any{map[string]any{"source_type": "discussion", "evidence_status": "verified", "source": "chat", "claim": "checkout is required", "material_id": "MAT-001"}},
		"evidence_checked":  []any{"chat", "MAT-001"},
		"advice_confidence": map[string]any{"level": "high", "reason": "User confirmed the handoff goal and preserve rule."},
		"must_preserve": []any{map[string]any{
			"id":                     "MP-001",
			"type":                   "requirement",
			"claim":                  "Checkout must collect payment",
			"source":                 "chat",
			"downstream_requirement": "Planning must include payment collection",
			"blocking_level":         "hard",
			"owner":                  "agent",
			"latest_resolve_phase":   "plan",
			"status":                 "active",
		}},
		"coverage_status":      "complete",
		"planning_gate_status": "ready",
		"hard_unknown_count":   float64(0),
		"open_conflict_count":  float64(0),
		"blocking_unknowns":    []any{},
		"soft_unknowns":        []any{},
		"conflicts":            []any{},
		"downstream_instructions": map[string]any{
			"settled_decisions":          []any{"Checkout must collect payment."},
			"preserved_assumptions":      []any{},
			"conflicts_requiring_return": []any{},
			"capability_map":             []any{},
			"dependencies":               []any{},
			"planning_constraints":       []any{"Preserve payment collection."},
			"deferred_scope":             []any{},
			"reopen_conditions":          []any{},
		},
		"discussion_decision_digest": map[string]any{
			"locked_direction":                []any{"Treat payment collection as first-class checkout scope."},
			"rejected_alternatives":           []any{},
			"accepted_tradeoffs":              []any{"Keep discussion handoff consumer-neutral."},
			"experience_commitments":          []any{},
			"design_system_requirements":      []any{},
			"review_criteria_carried_forward": []any{"Payment collection cannot be dropped downstream."},
			"must_not_dilute":                 []any{"Must preserve checkout payment collection."},
		},
		"consumer_eligibility": map[string]any{
			"sp-specify": map[string]any{"status": "blocked"},
			"sp-quick":   map[string]any{"status": "ready"},
		},
		"recommended_consumer": "sp-quick",
		"quality_gate": map[string]any{
			"self_reviewed_at": "2026-07-24T00:00:00Z",
		},
	}
}

func TestDiscussionSourceMaterialDigestUsesCrossRuntimeCanonicalJSON(t *testing.T) {
	material := map[string]any{
		"id":                "MAT-001",
		"material_type":     "user_note",
		"locator":           "https://example.test/a?x=1&y=2",
		"summary":           "Use <safe> reference",
		"inspection_status": "inspected",
		"claims":            []any{"A & B"},
		"coverage_gaps":     []any{},
		"sensitivity":       "safe",
	}

	digest, err := discussionSourceMaterialDigest(material)
	if err != nil {
		t.Fatal(err)
	}
	if digest != "43dbbb0c92e0d1fc7f66430bf2d280417906aef09e12d43d670e36d910519aa2" {
		t.Fatalf("material digest = %s, want cross-runtime canonical digest", digest)
	}
}

func TestDiscussionCheckpointRejectsInvalidSemanticShapes(t *testing.T) {
	root := t.TempDir()
	env := runScriptDomainEnvelope(t, runDiscussion, []string{"--project-root", root, "init", "Invalid Semantic Shape", "Invalid semantic shape"})
	if env.Status != "ok" {
		t.Fatalf("init = %#v", env)
	}
	slug := env.Data["slug"].(string)

	for _, payload := range []string{
		`{"advice_confidence":"certain"}`,
		`{"source_evidence":"not-a-list"}`,
		`{"source_evidence":[{"source_type":"discussion","evidence_status":"verified","source":"","claim":"missing source"}]}`,
	} {
		env = runScriptDomainEnvelope(t, runDiscussion, []string{"--project-root", root, "checkpoint", slug, "--input-json", payload})
		if env.Status != "blocked" {
			t.Fatalf("invalid checkpoint payload %s = %#v, want blocked", payload, env)
		}
	}
}

func TestDiscussionSnapshotValidationRequiresCheckpoint(t *testing.T) {
	state := discussionService{}.state("missing-checkpoint", "Missing checkpoint")
	errors := []map[string]string{}
	validateDiscussionSnapshotDigest(map[string]any{"discussion_snapshot_digest": strings.Repeat("0", 64)}, state, &errors)
	if len(errors) == 0 || errors[0]["code"] != "missing_semantic_checkpoint" {
		t.Fatalf("snapshot validation errors = %#v, want missing_semantic_checkpoint", errors)
	}
}

func TestDiscussionObjectListRejectsBlankRequiredValues(t *testing.T) {
	errors := []map[string]string{}
	validateObjectList(
		[]any{map[string]any{"source_type": "discussion", "evidence_status": "verified", "source": "", "claim": "claim"}},
		[]string{"source_type", "evidence_status", "source", "claim"},
		"source_evidence",
		&errors,
	)
	if len(errors) == 0 {
		t.Fatal("blank required source_evidence value must be rejected")
	}
}

func TestDiscussionHandoffSemanticValidatorsRejectHollowContent(t *testing.T) {
	errors := []map[string]string{}
	validateDiscussionMustPreserve(
		[]any{map[string]any{
			"id": "decision-1", "type": "decision", "claim": "claim", "source": "chat",
			"downstream_requirement": "preserve", "blocking_level": "hard", "owner": "discussion",
			"latest_resolve_phase": "prepare", "status": "confirmed",
		}},
		&errors,
	)
	validateDiscussionDownstreamInstructions(
		map[string]any{
			"settled_decisions": []any{}, "preserved_assumptions": []any{}, "conflicts_requiring_return": []any{},
			"capability_map": []any{}, "dependencies": []any{}, "planning_constraints": []any{},
			"deferred_scope": []any{}, "reopen_conditions": []any{},
		},
		&errors,
	)
	validateDiscussionDecisionDigest(
		map[string]any{
			"locked_direction": []any{}, "rejected_alternatives": []any{}, "accepted_tradeoffs": []any{},
			"experience_commitments": []any{}, "design_system_requirements": []any{},
			"review_criteria_carried_forward": []any{}, "must_not_dilute": []any{},
		},
		&errors,
	)
	if len(errors) < 3 {
		t.Fatalf("semantic validation errors = %#v, want MP id, settled decision, and decision digest failures", errors)
	}
}

func createReadyDiscussionForConsumer(t *testing.T, root, title, consumer string) (string, string) {
	t.Helper()
	installScaffoldTemplate(t, root, "discussion-handoff-template.json")
	env := runScriptDomainEnvelope(t, runDiscussion, []string{"--project-root", root, "init", title, title})
	if env.Status != "ok" {
		t.Fatalf("init %q = %#v", title, env)
	}
	slug := env.Data["slug"].(string)
	handoff := discussionHandoffFixture()
	if consumer == "sp-specify" {
		handoff["consumer_eligibility"] = map[string]any{
			"sp-specify": map[string]any{"status": "ready"},
			"sp-quick":   map[string]any{"status": "blocked"},
		}
	} else {
		handoff["consumer_eligibility"] = map[string]any{
			"sp-specify": map[string]any{"status": "blocked"},
			"sp-quick":   map[string]any{"status": "ready"},
		}
	}
	handoff["recommended_consumer"] = consumer
	checkpointDiscussionForHandoffFixture(t, root, slug, handoff)
	raw, err := json.Marshal(handoff)
	if err != nil {
		t.Fatal(err)
	}
	stateDigest, err := fileSHA256(filepath.Join(root, ".specify", "discussions", slug, "discussion-state.json"))
	if err != nil {
		t.Fatal(err)
	}
	env = runScriptDomainEnvelope(t, runDiscussion, []string{
		"--project-root", root, "write-handoff", slug,
		"--expected-state-sha256", stateDigest,
		"--input-json", string(raw),
	})
	if env.Status != "ok" {
		t.Fatalf("write-handoff %q = %#v", title, env)
	}
	digest := env.Data["review_digest"].(string)
	env = runScriptDomainEnvelope(t, runDiscussion, []string{"--project-root", root, "confirm-handoff", slug, "--digest", digest})
	if env.Status != "ok" {
		t.Fatalf("confirm-handoff %q = %#v", title, env)
	}
	env = runScriptDomainEnvelope(t, runDiscussion, []string{"--project-root", root, "mark-ready", slug})
	if env.Status != "ok" {
		t.Fatalf("mark-ready %q = %#v", title, env)
	}
	return slug, digest
}

func TestDiscussionCheckpointPersistsSemanticFieldsAndInputJSON(t *testing.T) {
	root := t.TempDir()
	env := runScriptDomainEnvelope(t, runDiscussion, []string{"--project-root", root, "init", "Durable recovery", "Durable recovery"})
	if env.Status != "ok" {
		t.Fatalf("init status = %s, blockers=%v", env.Status, env.Blockers)
	}
	slug := env.Data["slug"].(string)

	payload := map[string]any{
		"summary":                "Persist semantic checkpoint fields.",
		"lifecycle_phase":        "decide",
		"user_goal":              "Recover discussion without chat memory.",
		"confirmed_decisions":    []any{"Checkpoint must update turn_packet."},
		"open_questions":         []any{"Which consumer?"},
		"current_recommendation": "Keep typed state durable.",
		"context_boundary":       map[string]any{"status": "in-progress"},
		"requirements_snapshot": map[string]any{
			"status":           "partial",
			"actors":           []any{"shopper"},
			"scenarios":        []any{"shopper compares payment options"},
			"scope":            map[string]any{"in": []any{"checkout payment choice"}},
			"success_criteria": []any{"payment choice is ready for planning"},
		},
		"implementation_target": map[string]any{"target_kind": "feature", "target_project_root": "<current-project>"},
		"source_materials": []any{map[string]any{
			"id":                "MAT-001",
			"material_type":     "uploaded_note",
			"locator":           "notes/checkout.md",
			"summary":           "User supplied checkout abandonment notes.",
			"inspection_status": "partial",
			"claims":            []any{"Users need wallet and card options compared."},
			"coverage_gaps":     []any{"No payment provider named yet."},
			"sensitivity":       "safe",
		}},
		"blocking_unknowns": []any{map[string]any{"id": "UNK-001", "question": "Which payment provider?", "owner": "user", "status": "open", "latest_resolve_phase": "prepare"}},
		"evidence_checked":  []any{"notes/checkout.md"},
		"advice_confidence": map[string]any{"level": "medium", "reason": "One user material reviewed; provider still unknown."},
	}
	raw, err := json.Marshal(payload)
	if err != nil {
		t.Fatal(err)
	}
	path := filepath.Join(root, "checkpoint.json")
	if err := os.WriteFile(path, raw, 0o644); err != nil {
		t.Fatal(err)
	}

	env = runScriptDomainEnvelope(t, runDiscussion, []string{
		"--project-root", root, "checkpoint", slug, "--input-json", "@checkpoint.json",
	})
	if env.Status != "ok" {
		t.Fatalf("checkpoint status = %s, blockers=%v", env.Status, env.Blockers)
	}
	packet := env.Data["turn_packet"].(map[string]any)
	if packet["user_goal"] != "Recover discussion without chat memory." {
		t.Fatalf("user_goal not persisted: %#v", packet)
	}
	if packet["current_recommendation"] != "Keep typed state durable." {
		t.Fatalf("current_recommendation not persisted: %#v", packet)
	}
	boundary := packet["context_boundary"].(map[string]any)
	if boundary["status"] != "in-progress" {
		t.Fatalf("context_boundary not persisted: %#v", packet)
	}
	materials := packet["source_materials"].([]any)
	if len(materials) != 1 || materials[0].(map[string]any)["id"] != "MAT-001" {
		t.Fatalf("source_materials not persisted: %#v", packet)
	}

	env = runScriptDomainEnvelope(t, runDiscussion, []string{"--project-root", root, "resume", slug})
	if env.Status != "ok" {
		t.Fatalf("resume status = %s, blockers=%v", env.Status, env.Blockers)
	}
	resumePacket := env.Data["turn_packet"].(map[string]any)
	if resumePacket["user_goal"] != "Recover discussion without chat memory." {
		t.Fatalf("resume lost user_goal: %#v", resumePacket)
	}

	env = runScriptDomainEnvelope(t, runDiscussion, []string{
		"--project-root", root, "checkpoint", slug, "--input-json", `{"summary":"bad","not_a_field":true}`,
	})
	if env.Status == "ok" {
		t.Fatalf("unknown checkpoint fields should fail: %#v", env)
	}
	if !strings.Contains(fmt.Sprint(env.Blockers), "unknown fields") {
		t.Fatalf("expected unknown fields error, got %#v", env.Blockers)
	}
}

func TestDiscussionCheckpointPersistsFullSemanticSnapshot(t *testing.T) {
	root := t.TempDir()
	env := runScriptDomainEnvelope(t, runDiscussion, []string{"--project-root", root, "init", "Semantic Snapshot", "Clarify semantic handoff"})
	if env.Status != "ok" {
		t.Fatalf("init status = %s, blockers=%v", env.Status, env.Blockers)
	}
	slug := env.Data["slug"].(string)

	payload := map[string]any{
		"summary":               "Semantic material and target are durable.",
		"lifecycle_phase":       "ground",
		"requirements_snapshot": map[string]any{"target_need": "Preserve user material", "success_criteria": []any{"handoff is complete"}},
		"implementation_target": map[string]any{"actual_project": "spec-kit-plus", "target_root": root, "target_paths": []any{"templates/commands/discussion.md"}},
		"source_materials": []any{map[string]any{
			"id":                "MAT-001",
			"material_type":     "user_note",
			"locator":           "chat:turn-1",
			"inspection_status": "inspected",
			"summary":           "User asked whether discussion clarifies intent and records materials.",
			"claims":            []any{"Discussion must record user-provided material."},
			"coverage_gaps":     []any{},
			"sensitivity":       "safe",
		}},
		"blocking_unknowns":          []any{},
		"soft_unknowns":              []any{"Exact wording can stay compact."},
		"conflicts":                  []any{},
		"downstream_instructions":    map[string]any{"planning_constraints": []any{"Carry MAT-001 forward."}},
		"discussion_decision_digest": map[string]any{"locked_direction": []any{"Use source material ledger."}},
		"must_preserve":              []any{map[string]any{"id": "MP-001", "type": "requirement", "claim": "Preserve material ledger", "source": "chat", "downstream_requirement": "Plan sees material provenance", "blocking_level": "hard", "owner": "sp-discussion", "latest_resolve_phase": "ground", "status": "active"}},
		"verified_project_facts":     []any{"discussion runtime writes checkpoint state"},
		"evidence_checked":           []any{"tools/specify-runtime/script_domains.go"},
		"advice_confidence":          "high",
	}
	raw, err := json.Marshal(payload)
	if err != nil {
		t.Fatal(err)
	}
	env = runScriptDomainEnvelope(t, runDiscussion, []string{"--project-root", root, "checkpoint", slug, "--input-json", string(raw)})
	if env.Status != "ok" {
		t.Fatalf("checkpoint status = %s, blockers=%v", env.Status, env.Blockers)
	}
	event := env.Data["event"].(map[string]any)
	checkpoint := env.Data["discussion"].(map[string]any)["latest_checkpoint"].(map[string]any)
	packet := env.Data["turn_packet"].(map[string]any)
	if packet["version"] != float64(2) || event["version"] != float64(2) {
		t.Fatalf("semantic checkpoint versions not upgraded: packet=%#v event=%#v", packet["version"], event["version"])
	}
	if strings.TrimSpace(fmt.Sprint(event["snapshot_sha256"])) == "" || event["snapshot_sha256"] != checkpoint["snapshot_sha256"] {
		t.Fatalf("checkpoint snapshot digest missing or not recorded: event=%#v checkpoint=%#v", event, checkpoint)
	}
	if len(event["changed_fields"].([]any)) == 0 {
		t.Fatalf("checkpoint did not record changed fields: %#v", event)
	}
	materials := packet["source_materials"].([]any)
	if materials[0].(map[string]any)["id"] != "MAT-001" {
		t.Fatalf("source materials not included in turn packet: %#v", packet)
	}
}

func TestDiscussionWriteHandoffAcceptsAtPathInputJSON(t *testing.T) {
	root := t.TempDir()
	installScaffoldTemplate(t, root, "discussion-handoff-template.json")
	env := runScriptDomainEnvelope(t, runDiscussion, []string{"--project-root", root, "init", "Path input", "Path input"})
	if env.Status != "ok" {
		t.Fatalf("init status = %s", env.Status)
	}
	slug := env.Data["slug"].(string)
	handoff := discussionHandoffFixture()
	checkpointDiscussionForHandoffFixture(t, root, slug, handoff)
	raw, err := json.Marshal(handoff)
	if err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(root, "handoff-draft.json"), raw, 0o644); err != nil {
		t.Fatal(err)
	}
	env = runScriptDomainEnvelope(t, runDiscussion, []string{
		"--project-root", root, "write-handoff", slug, "--input-json", "@handoff-draft.json",
	})
	if env.Status != "ok" {
		t.Fatalf("write-handoff @path status = %s, blockers=%v", env.Status, env.Blockers)
	}
	if env.Data["review_digest"] == "" {
		t.Fatalf("missing review digest: %#v", env.Data)
	}
}

func TestDiscussionWriteHandoffQuotingFailureHint(t *testing.T) {
	root := t.TempDir()
	installScaffoldTemplate(t, root, "discussion-handoff-template.json")
	env := runScriptDomainEnvelope(t, runDiscussion, []string{"--project-root", root, "init", "Quote fail", "Quote fail"})
	slug := env.Data["slug"].(string)
	// Simulates PowerShell-stripped quotes: keys without double quotes.
	env = runScriptDomainEnvelope(t, runDiscussion, []string{
		"--project-root", root, "write-handoff", slug, "--input-json", `{handoff_goal:test}`,
	})
	if env.Status == "ok" {
		t.Fatalf("malformed JSON should fail")
	}
	joined := fmt.Sprint(env.Blockers)
	if !strings.Contains(joined, "JSON object") || !strings.Contains(joined, "PowerShell") {
		t.Fatalf("expected PowerShell quoting hint, got %#v", env.Blockers)
	}
}

type scriptDomainRunner func([]string, io.Writer) int

func runScriptDomainEnvelope(t *testing.T, runner scriptDomainRunner, args []string) Envelope {
	t.Helper()
	var stdout bytes.Buffer
	code := runner(args, &stdout)
	var env Envelope
	if err := json.Unmarshal(stdout.Bytes(), &env); err != nil {
		t.Fatalf("decode envelope (code %d): %v\n%s", code, err, stdout.String())
	}
	if code != ExitCodeForStatus(env.Status) {
		t.Fatalf("exit code %d does not match status %s", code, env.Status)
	}
	return env
}

func hasString(values []string, want string) bool {
	for _, value := range values {
		if value == want {
			return true
		}
	}
	return false
}

func mustMkdirAllScriptDomainTest(t *testing.T, path string) {
	t.Helper()
	if err := os.MkdirAll(path, 0o755); err != nil {
		t.Fatalf("mkdir %s: %v", path, err)
	}
}

func mustWriteScriptDomainTest(t *testing.T, path, content string) {
	t.Helper()
	mustMkdirAllScriptDomainTest(t, filepath.Dir(path))
	if err := os.WriteFile(path, []byte(content), 0o644); err != nil {
		t.Fatalf("write %s: %v", path, err)
	}
}

func mustWriteJSONScriptDomainTest(t *testing.T, path string, payload map[string]any) {
	t.Helper()
	raw, err := json.MarshalIndent(payload, "", "  ")
	if err != nil {
		t.Fatalf("marshal json: %v", err)
	}
	mustWriteScriptDomainTest(t, path, string(raw)+"\n")
}

func writeValidPRDScanFixture(t *testing.T, runDir, workspace, slug string) {
	t.Helper()
	mustWriteScriptDomainTest(t, filepath.Join(runDir, "workflow-state.md"), strings.Join([]string{
		"---",
		"id: \"" + workspace + "\"",
		"slug: \"" + slug + "\"",
		"status: \"ready-for-build\"",
		"---",
		"# PRD Workflow State",
		"",
		"## Current Command",
		"",
		"- active_command: `sp-prd-scan`",
		"- status: `ready-for-build`",
		"",
		"## Phase Mode",
		"",
		"- phase_mode: `analysis-only`",
		"- classification: `mixed`",
		"- scan_status: `complete`",
		"- build_status: `pending`",
		"- failed_readiness_checks: `none`",
		"",
		"## Allowed Artifact Writes",
		"",
		"- `.specify/prd-runs/" + workspace + "/workflow-state.md`",
		"",
		"## Forbidden Actions",
		"",
		"- edit source code",
		"",
		"## Next Command",
		"",
		"- `/sp.prd-build`",
		"",
		"## Authoritative Files",
		"",
		"- `.specify/prd-runs/" + workspace + "/workflow-state.md`",
		"",
	}, "\n"))
	mustWriteScriptDomainTest(t, filepath.Join(runDir, "prd-scan.md"), "# PRD Scan\n\n## Reconstruction Summary\n\n- Status: complete\n")
	mustWriteScriptDomainTest(t, filepath.Join(runDir, "coverage-ledger.md"), "# Coverage Ledger\n\n- Complete\n")
	mustWriteJSONScriptDomainTest(t, filepath.Join(runDir, "evidence", "EVD-001.json"), map[string]any{"id": "EVD-001"})
	mustWriteScriptDomainTest(t, filepath.Join(runDir, "scan-packets", "packet-001.md"), "# Packet\n")
	mustWriteJSONScriptDomainTest(t, filepath.Join(runDir, "worker-results", "worker-001.json"), map[string]any{
		"lane_id":                      "LN-001",
		"reported_status":              "done",
		"confidence":                   "high",
		"result_handoff_path":          "scan-packets/packet-001.md",
		"paths_read":                   []any{"README.md"},
		"key_facts":                    []any{"Repository context captured."},
		"evidence_refs":                []any{"evidence/EVD-001.json"},
		"recommended_contract_updates": []any{},
		"unknowns":                     []any{},
		"minimum_verification":         []any{"Review packet evidence."},
	})
	mustWriteJSONScriptDomainTest(t, filepath.Join(runDir, "coverage-ledger.json"), map[string]any{
		"version": 1,
		"rows": []any{map[string]any{
			"id":       "COV-001",
			"surface":  "repo-overview",
			"status":   "covered",
			"evidence": []any{"evidence/EVD-001.json"},
		}},
	})
	mustWriteJSONScriptDomainTest(t, filepath.Join(runDir, "capability-ledger.json"), map[string]any{
		"capabilities": []any{map[string]any{
			"id":     "CAP-001",
			"tier":   "critical",
			"status": "reconstruction-ready",
		}},
	})
	mustWriteJSONScriptDomainTest(t, filepath.Join(runDir, "artifact-contracts.json"), map[string]any{
		"artifacts": []any{map[string]any{"id": "ART-001", "status": "ready"}},
	})
	mustWriteJSONScriptDomainTest(t, filepath.Join(runDir, "reconstruction-checklist.json"), map[string]any{
		"checks": []any{map[string]any{"id": "CHK-001", "status": "done"}},
	})
}

func writeValidPRDBuildFixture(t *testing.T, runDir, workspace, slug string) {
	t.Helper()
	writeValidPRDScanFixture(t, runDir, workspace, slug)
	mustWriteScriptDomainTest(t, filepath.Join(runDir, "workflow-state.md"), strings.Join([]string{
		"---",
		"id: \"" + workspace + "\"",
		"slug: \"" + slug + "\"",
		"status: \"complete\"",
		"---",
		"# PRD Workflow State",
		"",
		"## Current Command",
		"",
		"- active_command: `sp-prd-build`",
		"- status: `complete`",
		"",
		"## Phase Mode",
		"",
		"- phase_mode: `analysis-only`",
		"- classification: `mixed`",
		"- scan_status: `complete`",
		"- build_status: `complete`",
		"- failed_readiness_checks: `none`",
		"- failed_reverse_coverage_checks: `none`",
		"",
		"## Allowed Artifact Writes",
		"",
		"- `.specify/prd-runs/" + workspace + "/exports/prd.md`",
		"",
		"## Forbidden Actions",
		"",
		"- edit source code",
		"",
		"## Next Command",
		"",
		"- `none`",
		"",
		"## Authoritative Files",
		"",
		"- `.specify/prd-runs/" + workspace + "/workflow-state.md`",
		"",
	}, "\n"))
	for relative, content := range map[string]string{
		"master/master-pack.md":              "# Master Pack\n\nSubstantive summary.\n",
		"exports/README.md":                  "# README\n\nExport bundle.\n",
		"exports/prd.md":                     "# PRD\n\n## Capability Overview\n\n- CAP-001\n\n## Critical Capability Notes\n\n- Ready\n\n## Unknowns and Evidence Confidence\n\n- Confidence: high\n",
		"exports/reconstruction-appendix.md": "# Appendix\n\nSupporting appendix.\n",
		"exports/data-model.md":              "# Data Model\n\nEntity summary.\n",
		"exports/integration-contracts.md":   "# Integration Contracts\n\nContract summary.\n",
		"exports/runtime-behaviors.md":       "# Runtime Behaviors\n\nBehavior summary.\n",
		"exports/config-contracts.md":        "# Config Contracts\n\nConfiguration summary.\n",
		"exports/protocol-contracts.md":      "# Protocol Contracts\n\nProtocol summary.\n",
		"exports/state-machines.md":          "# State Machines\n\nState summary.\n",
		"exports/error-semantics.md":         "# Error Semantics\n\nError summary.\n",
		"exports/verification-surface.md":    "# Verification Surface\n\nVerification summary.\n",
		"exports/reconstruction-risks.md":    "# Reconstruction Risks\n\nRisk summary.\n",
	} {
		mustWriteScriptDomainTest(t, filepath.Join(runDir, filepath.FromSlash(relative)), content)
	}
}
