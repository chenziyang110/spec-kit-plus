package main

import (
	"bytes"
	"encoding/json"
	"os"
	"path/filepath"
	"testing"
)

func TestLearningStartAndListAreReadOnlyCompact(t *testing.T) {
	root := t.TempDir()
	mustMkdirLearningTest(t, filepath.Join(root, ".specify"))

	start := runLearningEnvelopeTest(t, []string{"start", "--project-root", root, "--command", "spx-plan", "--format", "json"})
	if start.Status != "ok" {
		t.Fatalf("start status = %s blockers=%v", start.Status, start.Blockers)
	}
	if start.Data["command"] != "sp-plan" || start.Data["read_only"] != true {
		t.Fatalf("unexpected start payload: %#v", start.Data)
	}
	if _, err := os.Stat(filepath.Join(root, ".specify", "memory", "learnings", "INDEX.md")); !os.IsNotExist(err) {
		t.Fatalf("read-only start created learning index or returned unexpected stat err: %v", err)
	}

	list := runLearningEnvelopeTest(t, []string{"list", "--project-root", root, "--command", "plan", "--format", "json"})
	if list.Status != "ok" {
		t.Fatalf("list status = %s blockers=%v", list.Status, list.Blockers)
	}
	if list.Data["items"].([]any) == nil || len(list.Data["warnings"].([]any)) == 0 {
		t.Fatalf("missing compact list warnings/items: %#v", list.Data)
	}
}

func TestLearningCaptureShowPromoteLifecycle(t *testing.T) {
	root := t.TempDir()
	mustMkdirLearningTest(t, filepath.Join(root, ".specify"))

	capture := runLearningEnvelopeTest(t, []string{
		"capture", "--project-root", root,
		"--command", "debug",
		"--type", "tooling_trap",
		"--summary", "Watcher loops can masquerade as process-manager failures",
		"--evidence", "Repeated process fixes failed; excluding the log directory stopped restarts.",
		"--recurrence-key", "debug.watcher-loop",
		"--false-start", "job object cleanup",
		"--rejected-path", "process manager root cause",
		"--decisive-signal", "watcher ignore stopped restarts",
		"--context", "operation_owner=Watcher",
		"--format", "json",
	})
	if capture.Status != "ok" || capture.Data["status"] != "candidate" {
		t.Fatalf("capture failed: %#v", capture)
	}
	entry := capture.Data["entry"].(map[string]any)
	if entry["recurrence_key"] != "debug.watcher-loop" || entry["status"] != "candidate" {
		t.Fatalf("unexpected captured entry: %#v", entry)
	}
	if _, err := os.Stat(capture.Data["detail_path"].(string)); err != nil {
		t.Fatalf("detail path missing: %v", err)
	}

	show := runLearningEnvelopeTest(t, []string{"show", "--project-root", root, "--ref", "debug.watcher-loop", "--format", "json"})
	if show.Data["ref"] != "debug.watcher-loop" || show.Data["status"] != "candidate" {
		t.Fatalf("unexpected show payload: %#v", show.Data)
	}
	guidance := show.Data["guidance"].(map[string]any)
	if guidance["action"] == "" {
		t.Fatalf("show did not expose guidance action: %#v", guidance)
	}

	promote := runLearningEnvelopeTest(t, []string{"promote", "--project-root", root, "--recurrence-key", "debug.watcher-loop", "--target", "learning", "--format", "json"})
	if promote.Status != "ok" || promote.Data["status"] != "confirmed" {
		t.Fatalf("promote failed: %#v", promote)
	}
	confirmed := readLearningEntriesIfPresent(filepath.Join(root, ".specify", "memory", "learnings", "confirmed.md"))
	candidates := readLearningEntriesIfPresent(filepath.Join(root, ".planning", "learnings", "candidates.md"))
	if len(confirmed) != 1 || len(candidates) != 0 {
		t.Fatalf("promotion storage mismatch: confirmed=%d candidates=%d", len(confirmed), len(candidates))
	}
}

func TestLearningCaptureAutoQuickDuplicateAndExplicitPromotion(t *testing.T) {
	root := t.TempDir()
	workspace := filepath.Join(root, ".planning", "quick", "260724-001-demo")
	mustMkdirLearningTest(t, workspace)
	mustWriteLearningTest(t, filepath.Join(workspace, "STATUS.md"), `---
id: "260724-001"
title: "Demo quick task"
status: "blocked"
---

## Current Focus
goal: keep the worker result contract aligned
next_action: wait for runtime recovery

## Execution
execution_fallback: native worker runtime unavailable
blocker_reason: runtime unavailable
recovery_action: retry after runtime comes back
retry_attempts: 1

## Validation
completed_checks: []
`)

	first := runLearningEnvelopeTest(t, []string{"capture-auto", "--project-root", root, "--command", "quick", "--workspace", ".planning/quick/260724-001-demo", "--format", "json"})
	if first.Status != "ok" || first.Data["status"] != "captured" {
		t.Fatalf("first capture-auto failed: %#v", first)
	}
	captured := first.Data["captured"].([]any)
	if len(captured) != 1 {
		t.Fatalf("captured len = %d", len(captured))
	}
	stored := captured[0].(map[string]any)["entry"].(map[string]any)
	if stored["recurrence_key"] != "quick.leader-inline-fallback-preserves-runtime-unavailability-reason" {
		t.Fatalf("unexpected auto-captured key: %#v", stored)
	}

	second := runLearningEnvelopeTest(t, []string{"capture-auto", "--project-root", root, "--command", "quick", "--workspace", ".planning/quick/260724-001-demo", "--format", "json"})
	if second.Data["status"] != "duplicate-snapshot" {
		t.Fatalf("duplicate snapshot was not detected: %#v", second.Data)
	}

	rule := runLearningEnvelopeTest(t, []string{"promote", "--project-root", root, "--recurrence-key", "quick.leader-inline-fallback-preserves-runtime-unavailability-reason", "--target", "rule", "--format", "json"})
	if rule.Data["status"] != "promoted-rule" {
		t.Fatalf("rule promotion failed: %#v", rule.Data)
	}
	rules := readLearningEntriesIfPresent(filepath.Join(root, ".specify", "memory", "project-rules.md"))
	if len(rules) != 1 || rules[0]["status"] != "promoted-rule" {
		t.Fatalf("rule storage mismatch: %#v", rules)
	}
}

func runLearningEnvelopeTest(t *testing.T, args []string) Envelope {
	t.Helper()
	var stdout bytes.Buffer
	code := runLearning(args, &stdout)
	var env Envelope
	if err := json.Unmarshal(stdout.Bytes(), &env); err != nil {
		t.Fatalf("decode learning envelope code=%d err=%v stdout=%s", code, err, stdout.String())
	}
	if code != ExitCodeForStatus(env.Status) {
		t.Fatalf("exit code %d does not match status %s", code, env.Status)
	}
	return env
}

func mustMkdirLearningTest(t *testing.T, path string) {
	t.Helper()
	if err := os.MkdirAll(path, 0o755); err != nil {
		t.Fatalf("mkdir %s: %v", path, err)
	}
}

func mustWriteLearningTest(t *testing.T, path, content string) {
	t.Helper()
	mustMkdirLearningTest(t, filepath.Dir(path))
	if err := os.WriteFile(path, []byte(content), 0o644); err != nil {
		t.Fatalf("write %s: %v", path, err)
	}
}
