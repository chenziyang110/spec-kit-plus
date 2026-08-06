package main

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestQuickItemStartBlockedByUnmetDepsAndPacketCompile(t *testing.T) {
	root := t.TempDir()
	workspace := filepath.Join(root, ".planning", "quick", "260805-010-exec")
	mustMkdirAllScriptDomainTest(t, workspace)
	mustWriteScriptDomainTest(t, filepath.Join(workspace, "STATUS.md"), `---
id: "260805-010"
slug: "exec"
title: "Exec"
status: gathering
understanding_confirmed: false
---

## Understanding Checkpoint

x

## Execution

y
`)

	payload := map[string]any{
		"source": map[string]any{"kind": "prompt"},
		"decision": map[string]any{
			"goal":                "ship multi-item delivery",
			"user_visible_result": "all Q items done",
			"scope": map[string]any{
				"include": []any{"a"},
				"exclude": []any{"b"},
			},
			"items": []any{
				map[string]any{"id": "Q1", "deliverable": "contract", "depends_on": []any{}, "acceptance": "types match", "write_scope": []any{"src/a.go"}},
				map[string]any{"id": "Q2", "deliverable": "api", "depends_on": []any{"Q1"}, "acceptance": "api passes", "write_scope": []any{"src/b.go"}},
			},
			"reconfirmation_trigger": "scope change",
		},
	}
	raw, _ := json.Marshal(payload)
	env := runScriptDomainEnvelope(t, runQuick, []string{
		"--project-root", root,
		"checkpoint-stage", "260805-010",
		"--input-json", string(raw),
	})
	digest := stringValue(env.Data["confirmation_digest"])
	env = runScriptDomainEnvelope(t, runQuick, []string{
		"--project-root", root,
		"checkpoint-confirm", "260805-010",
		"--digest", digest,
	})
	if env.Status != "ok" {
		t.Fatalf("confirm: %v", env.Blockers)
	}

	// Q2 cannot start before Q1 accepted
	env = runScriptDomainEnvelope(t, runQuick, []string{
		"--project-root", root,
		"item-start", "260805-010",
		"--item", "Q2",
	})
	if env.Status == "ok" {
		t.Fatalf("expected Q2 start to fail while Q1 pending")
	}

	env = runScriptDomainEnvelope(t, runQuick, []string{
		"--project-root", root,
		"packet-compile", "260805-010",
		"--item", "Q2",
	})
	if env.Status == "ok" {
		t.Fatalf("expected packet-compile for blocked Q2 to fail")
	}

	env = runScriptDomainEnvelope(t, runQuick, []string{
		"--project-root", root,
		"packet-compile", "260805-010",
		"--item", "Q2",
		"--allow-blocked",
	})
	if env.Status != "ok" {
		t.Fatalf("allow-blocked compile failed: %v", env.Blockers)
	}
	if env.Data["ready"] != false {
		t.Fatalf("blocked packet should not be ready")
	}

	env = runScriptDomainEnvelope(t, runQuick, []string{
		"--project-root", root,
		"item-start", "260805-010",
		"--item", "Q1",
	})
	if env.Status != "ok" {
		t.Fatalf("Q1 start failed: %v", env.Blockers)
	}
	packet := env.Data["packet"].(map[string]any)
	if packet["work_item_id"] != "Q1" || packet["ready"] != true {
		t.Fatalf("packet = %#v", packet)
	}
	if _, err := os.Stat(filepath.Join(workspace, "packets", "Q1.json")); err != nil {
		t.Fatalf("packet file missing: %v", err)
	}

	// close resolved must fail while Q items pending
	env = runScriptDomainEnvelope(t, runQuick, []string{
		"--project-root", root,
		"close", "260805-010", "resolved",
	})
	if env.Status == "ok" {
		t.Fatalf("close resolved should fail with pending items")
	}

	env = runScriptDomainEnvelope(t, runQuick, []string{
		"--project-root", root,
		"item-accept", "260805-010",
		"--item", "Q1",
		"--evidence", "types match in tests",
	})
	if env.Status != "ok" {
		t.Fatalf("accept Q1 failed: %v", env.Blockers)
	}
	ready := env.Data["ready_item_ids"].([]any)
	if len(ready) != 1 || ready[0] != "Q2" {
		t.Fatalf("ready after Q1 accept = %#v", ready)
	}

	env = runScriptDomainEnvelope(t, runQuick, []string{
		"--project-root", root,
		"item-start", "260805-010",
		"--item", "Q2",
	})
	if env.Status != "ok" {
		t.Fatalf("Q2 start after Q1 accept failed: %v", env.Blockers)
	}

	env = runScriptDomainEnvelope(t, runQuick, []string{
		"--project-root", root,
		"item-accept", "260805-010",
		"--item", "Q2",
		"--evidence", "api passes",
	})
	if env.Status != "ok" {
		t.Fatalf("accept Q2 failed: %v", env.Blockers)
	}
	if env.Data["all_accepted"] != true {
		t.Fatalf("expected all accepted")
	}

	// Source-changing write_scope requires cognition closeout receipt before resolved close.
	env = runScriptDomainEnvelope(t, runQuick, []string{
		"--project-root", root,
		"close", "260805-010", "resolved",
	})
	if env.Status == "ok" {
		t.Fatalf("close resolved should fail without cognition closeout")
	}
	if !strings.Contains(fmt.Sprint(env.Blockers), "cognition") {
		t.Fatalf("expected cognition gate error, got %v", env.Blockers)
	}

	env = runScriptDomainEnvelope(t, runQuick, []string{
		"--project-root", root,
		"cognition-closeout", "260805-010",
		"--result-state", "ready",
		"--reason", "inline update completed in test",
		"--evidence-json", `["go test ./..."]`,
	})
	if env.Status != "ok" {
		t.Fatalf("cognition-closeout failed: %v", env.Blockers)
	}
	if _, err := os.Stat(filepath.Join(workspace, "cognition-closeout.json")); err != nil {
		t.Fatalf("receipt missing: %v", err)
	}

	env = runScriptDomainEnvelope(t, runQuick, []string{
		"--project-root", root,
		"close", "260805-010", "resolved",
	})
	if env.Status != "ok" {
		t.Fatalf("close after cognition closeout failed: %v", env.Blockers)
	}

	// pulse should mention accepted work
	env = runScriptDomainEnvelope(t, runQuick, []string{
		"--project-root", root,
		"checkpoint-show", "260805-010",
		"--view", "pulse",
	})
	if !strings.Contains(stringValue(env.Data["text"]), "已验收") {
		t.Fatalf("pulse = %s", env.Data["text"])
	}
}

func TestQuickPacketCompileRequiresConfirmedCheckpoint(t *testing.T) {
	root := t.TempDir()
	workspace := filepath.Join(root, ".planning", "quick", "260805-011-unconfirmed")
	mustMkdirAllScriptDomainTest(t, workspace)
	mustWriteScriptDomainTest(t, filepath.Join(workspace, "STATUS.md"), `---
id: "260805-011"
slug: "unconfirmed"
title: "Unconfirmed"
status: gathering
understanding_confirmed: false
---

## Understanding Checkpoint

x

## Execution

y
`)
	payload := map[string]any{
		"source": map[string]any{"kind": "prompt"},
		"decision": map[string]any{
			"goal":                "g",
			"user_visible_result": "r",
			"scope":               map[string]any{"include": []any{"a"}, "exclude": []any{"b"}},
			"items": []any{
				map[string]any{"id": "Q1", "deliverable": "one", "depends_on": []any{}, "acceptance": "ok"},
			},
			"reconfirmation_trigger": "x",
		},
	}
	raw, _ := json.Marshal(payload)
	env := runScriptDomainEnvelope(t, runQuick, []string{
		"--project-root", root,
		"checkpoint-stage", "260805-011",
		"--input-json", string(raw),
	})
	if env.Status != "ok" {
		t.Fatalf("stage: %v", env.Blockers)
	}
	env = runScriptDomainEnvelope(t, runQuick, []string{
		"--project-root", root,
		"item-start", "260805-011",
		"--item", "Q1",
	})
	if env.Status == "ok" {
		t.Fatalf("start should require confirmed checkpoint")
	}
}
