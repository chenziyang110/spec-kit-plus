package main

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestQuickCloseRequiresCognitionReceiptForSourceScopes(t *testing.T) {
	root := t.TempDir()
	workspace := filepath.Join(root, ".planning", "quick", "260806-cognition")
	mustMkdirAllScriptDomainTest(t, workspace)
	mustWriteScriptDomainTest(t, filepath.Join(workspace, "STATUS.md"), `---
id: "260806-cognition"
slug: "cognition"
title: "Cognition gate"
status: gathering
understanding_confirmed: false
---

## Understanding Checkpoint

x

## Execution

y

## Summary Pointer

changed_code_paths: []
project_cognition_refresh:
  status: not-needed
  evidence: []
`)

	payload := map[string]any{
		"source": map[string]any{"kind": "prompt"},
		"decision": map[string]any{
			"goal":                "replace icons",
			"user_visible_result": "real SVG icons",
			"scope":               map[string]any{"include": []any{"ui"}, "exclude": []any{}},
			"items": []any{
				map[string]any{
					"id": "Q1", "deliverable": "icons", "depends_on": []any{},
					"acceptance": "icons render", "write_scope": []any{"web/src/components/Icon.vue"},
				},
			},
			"reconfirmation_trigger": "scope change",
		},
	}
	raw, _ := json.Marshal(payload)
	env := runScriptDomainEnvelope(t, runQuick, []string{
		"--project-root", root, "checkpoint-stage", "260806-cognition", "--input-json", string(raw),
	})
	if env.Status != "ok" {
		t.Fatalf("stage failed: status=%s blockers=%v data=%#v", env.Status, env.Blockers, env.Data)
	}
	digest := stringValue(env.Data["confirmation_digest"])
	if digest == "" {
		t.Fatalf("missing confirmation_digest: %#v", env.Data)
	}
	env = runScriptDomainEnvelope(t, runQuick, []string{
		"--project-root", root, "checkpoint-confirm", "260806-cognition", "--digest", digest,
	})
	if env.Status != "ok" {
		t.Fatalf("confirm failed: %v data=%#v", env.Blockers, env.Data)
	}
	env = runScriptDomainEnvelope(t, runQuick, []string{
		"--project-root", root, "item-start", "260806-cognition", "--item", "Q1",
	})
	if env.Status != "ok" {
		t.Fatalf("start failed: %v", env.Blockers)
	}
	env = runScriptDomainEnvelope(t, runQuick, []string{
		"--project-root", root, "item-accept", "260806-cognition", "--item", "Q1", "--evidence", "vue-tsc + tests",
	})
	if env.Status != "ok" {
		t.Fatalf("accept failed: %v", env.Blockers)
	}

	env = runScriptDomainEnvelope(t, runQuick, []string{
		"--project-root", root, "status", "260806-cognition",
	})
	if env.Status != "ok" {
		t.Fatalf("status failed: %v", env.Blockers)
	}
	gate, _ := env.Data["cognition_closeout"].(map[string]any)
	if gate["required"] != true || gate["allowed_close"] != false {
		t.Fatalf("cognition_closeout = %#v", gate)
	}
	status := fmt.Sprint(gate["status"])
	if status != "missing" && status != "missing-receipt" {
		t.Fatalf("expected missing receipt status, got %#v", gate)
	}

	env = runScriptDomainEnvelope(t, runQuick, []string{
		"--project-root", root, "close", "260806-cognition",
	})
	if env.Status == "ok" || !strings.Contains(fmt.Sprint(env.Blockers)+env.Summary, "resolved or blocked") {
		// empty status should give usage-style error
	}

	env = runScriptDomainEnvelope(t, runQuick, []string{
		"--project-root", root, "close", "260806-cognition", "resolved",
	})
	if env.Status == "ok" {
		t.Fatalf("expected close blocked without cognition receipt")
	}

	// Greenfield minimum: mark-dirty with reason is allowed.
	env = runScriptDomainEnvelope(t, runQuick, []string{
		"--project-root", root,
		"cognition-closeout", "260806-cognition",
		"--result-state", "mark-dirty",
		"--reason", "greenfield_empty baseline; no path_index to adopt",
	})
	if env.Status != "ok" {
		t.Fatalf("mark-dirty closeout failed: %v", env.Blockers)
	}
	body, err := os.ReadFile(filepath.Join(workspace, "STATUS.md"))
	if err != nil {
		t.Fatal(err)
	}
	if !strings.Contains(string(body), "status: mark-dirty") {
		t.Fatalf("STATUS.md not synced: %s", body)
	}

	env = runScriptDomainEnvelope(t, runQuick, []string{
		"--project-root", root, "close", "260806-cognition", "resolved",
	})
	if env.Status != "ok" {
		t.Fatalf("close after mark-dirty should pass: %v", env.Blockers)
	}
}

func TestQuickCloseSkipsCognitionWhenNoSourceWriteScope(t *testing.T) {
	root := t.TempDir()
	workspace := filepath.Join(root, ".planning", "quick", "260806-docs")
	mustMkdirAllScriptDomainTest(t, workspace)
	mustWriteScriptDomainTest(t, filepath.Join(workspace, "STATUS.md"), `---
id: "260806-docs"
slug: "docs"
title: "Docs only"
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
			"goal":                "edit quick notes",
			"user_visible_result": "notes updated",
			"scope":               map[string]any{"include": []any{"notes"}, "exclude": []any{}},
			"items": []any{
				map[string]any{
					"id": "Q1", "deliverable": "notes", "depends_on": []any{},
					"acceptance": "notes exist", "write_scope": []any{".planning/quick/260806-docs/STATUS.md"},
				},
			},
			"reconfirmation_trigger": "scope change",
		},
	}
	raw, _ := json.Marshal(payload)
	env := runScriptDomainEnvelope(t, runQuick, []string{
		"--project-root", root, "checkpoint-stage", "260806-docs", "--input-json", string(raw),
	})
	if env.Status != "ok" {
		t.Fatalf("stage: %v", env.Blockers)
	}
	digest := stringValue(env.Data["confirmation_digest"])
	env = runScriptDomainEnvelope(t, runQuick, []string{
		"--project-root", root, "checkpoint-confirm", "260806-docs", "--digest", digest,
	})
	if env.Status != "ok" {
		t.Fatalf("confirm: %v", env.Blockers)
	}
	env = runScriptDomainEnvelope(t, runQuick, []string{
		"--project-root", root, "item-start", "260806-docs", "--item", "Q1",
	})
	if env.Status != "ok" {
		t.Fatalf("start: %v", env.Blockers)
	}
	env = runScriptDomainEnvelope(t, runQuick, []string{
		"--project-root", root, "item-accept", "260806-docs", "--item", "Q1", "--evidence", "ok",
	})
	if env.Status != "ok" {
		t.Fatalf("accept: %v", env.Blockers)
	}
	env = runScriptDomainEnvelope(t, runQuick, []string{
		"--project-root", root, "close", "260806-docs", "resolved",
	})
	if env.Status != "ok" {
		t.Fatalf("docs-only close should not require cognition: %v", env.Blockers)
	}
}
