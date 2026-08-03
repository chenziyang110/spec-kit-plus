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

	env = runScriptDomainEnvelope(t, runQuick, []string{"--project-root", root, "close", "260724-001", "resolved"})
	task = env.Data["task"].(map[string]any)
	if task["status"] != "resolved" || task["closed_at"] == "" {
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
	raw, err := json.Marshal(discussionHandoffFixture())
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

	consumer := filepath.Join(root, ".planning", "quick", "260724-001-checkout")
	mustMkdirAllScriptDomainTest(t, consumer)
	mustWriteJSONScriptDomainTest(t, filepath.Join(consumer, "handoff-to-specify.json"), map[string]any{
		"discussion_slug": slug,
		"source_contract": ".specify/discussions/" + slug + "/handoff-to-specify.json",
		"review_digest":   digest,
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
	raw, err := json.Marshal(discussionHandoffFixture())
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

	featureRel := ".specify/features/2026-07-29-checkout"
	feature := filepath.Join(root, filepath.FromSlash(featureRel))
	mustMkdirAllScriptDomainTest(t, feature)
	input := `{"semantic_delta":[],"required_refs":["MP-001"],"blockers":[],"recovery":null}`
	env = runScriptDomainEnvelope(t, runDiscussion, []string{
		"--project-root", root, "bind-consumer", slug,
		"--feature-dir", featureRel,
		"--input-json", input,
	})
	if env.Status != "ok" || env.Data["status"] != "ready" || env.Data["next_action"] != "/sp.plan" {
		t.Fatalf("bind consumer = %#v", env)
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

	env = runScriptDomainEnvelope(t, runDiscussion, []string{"--project-root", root, "mark-consumed", slug, "--feature-dir", featureRel})
	if env.Status != "ok" {
		t.Fatalf("mark consumed from bound pointer = %#v", env)
	}
}

func TestDiscussionBindConsumerRejectsFilesAndIntegrityFieldOverrides(t *testing.T) {
	root := t.TempDir()
	for _, args := range [][]string{
		{"--project-root", root, "bind-consumer", "demo", "--feature-dir", "specs/demo", "--input", "payload.json", "--input-json", `{}`},
		{"--project-root", root, "bind-consumer", "demo", "--feature-dir", "specs/demo", "--input-json", `{"semantic_delta":[],"required_refs":[],"blockers":[],"recovery":null,"review_digest":"agent-value"}`},
	} {
		env := runScriptDomainEnvelope(t, runDiscussion, args)
		if env.Status != "blocked" {
			t.Fatalf("bind-consumer %#v = %#v, want blocked", args, env)
		}
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
		if env.Status != "blocked" || len(env.Blockers) == 0 {
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
			raw, err := json.Marshal(discussionHandoffFixture())
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

func discussionHandoffFixture() map[string]any {
	role := map[string]any{"role": "source", "scope": "checkout", "evidence_source": "discussion", "notes": "confirmed"}
	return map[string]any{
		"handoff_goal": "Implement checkout flow",
		"context_boundary": map[string]any{
			"status":                "locked",
			"current_project_roles": []any{role},
		},
		"source_evidence": []any{map[string]any{"source_type": "discussion", "evidence_status": "verified", "source": "chat", "claim": "checkout is required"}},
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
		"downstream_instructions": map[string]any{
			"planning_constraints": []any{"Preserve payment collection."},
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
