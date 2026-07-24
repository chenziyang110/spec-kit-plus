package main

import (
	"bytes"
	"encoding/json"
	"io"
	"os"
	"path/filepath"
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
	surfaces := env.Data["surfaces"].(map[string]any)
	if surfaces["workspace"] != true || surfaces["prd_export"] != false {
		t.Fatalf("unexpected build surfaces: %#v", surfaces)
	}
}

func TestDiscussionHandoffLifecycleParity(t *testing.T) {
	root := t.TempDir()
	env := runScriptDomainEnvelope(t, runDiscussion, []string{"--project-root", root, "init", "Checkout Flow", "Checkout requirements"})
	if env.Status != "ok" {
		t.Fatalf("init status = %s, blockers=%v", env.Status, env.Blockers)
	}
	slug := env.Data["slug"].(string)
	inputPath := filepath.Join(root, "handoff-input.json")
	mustWriteJSONScriptDomainTest(t, inputPath, discussionHandoffFixture())

	env = runScriptDomainEnvelope(t, runDiscussion, []string{"--project-root", root, "write-handoff", slug, "handoff-input.json"})
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
