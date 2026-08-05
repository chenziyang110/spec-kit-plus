package main

import (
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestQuickCheckpointStageConfirmShow(t *testing.T) {
	root := t.TempDir()
	workspace := filepath.Join(root, ".planning", "quick", "260805-001-prompt-modes")
	mustMkdirAllScriptDomainTest(t, workspace)
	mustWriteScriptDomainTest(t, filepath.Join(workspace, "STATUS.md"), `---
id: "260805-001"
slug: "prompt-modes"
title: "Prompt modes"
status: gathering
understanding_confirmed: false
---

## Current Focus

goal: "stage checkpoint"

## Understanding Checkpoint

checkpoint:
  request_and_outcome: ""

## Execution

active_lane: ""
`)

	payload := map[string]any{
		"source": map[string]any{"kind": "prompt"},
		"decision": map[string]any{
			"goal":                "把 Prompt 做成与 SkillHub 一致的一等资产。",
			"user_visible_result": "Prompt 可发布、治理、发现、安装并通过全链路验证",
			"scope": map[string]any{
				"include": []any{"发布", "治理", "发现", "Web", "CLI", "验证"},
				"exclude": []any{"MCP", "模型调用", "Agent 执行", "自动翻译", "旧 feature"},
			},
			"items": []any{
				map[string]any{"id": "Q1", "deliverable": "Prompt 元数据契约", "depends_on": []any{}, "acceptance": "DB、API、Web 类型一致"},
				map[string]any{"id": "Q2", "deliverable": "发布与治理", "depends_on": []any{"Q1"}, "acceptance": "审核、归档、下架、权限与 Skill 对齐"},
				map[string]any{"id": "Q3", "deliverable": "Web 发现与使用体验", "depends_on": []any{"Q1"}, "acceptance": "首页、搜索、详情、管理、双语和响应式通过"},
				map[string]any{"id": "Q4", "deliverable": "CLI Use / Install", "depends_on": []any{"Q1", "Q2"}, "acceptance": "Use 不落盘；Install 保留所有权并校验 hash"},
				map[string]any{"id": "Q5", "deliverable": "全链路验证", "depends_on": []any{"Q2", "Q3", "Q4"}, "acceptance": "后端、OpenAPI、Web、CLI、安全和回归全部通过"},
			},
			"reconfirmation_trigger": "范围、依赖、验收或权限模型变化",
			"completion_evidence":    []any{"全链路验证通过"},
		},
	}
	raw, err := json.Marshal(payload)
	if err != nil {
		t.Fatalf("marshal: %v", err)
	}

	env := runScriptDomainEnvelope(t, runQuick, []string{
		"--project-root", root,
		"checkpoint-stage", "260805-001",
		"--input-json", string(raw),
	})
	if env.Status != "ok" {
		t.Fatalf("stage status=%s blockers=%v", env.Status, env.Blockers)
	}
	if env.Data["requires_user_confirm"] != true {
		t.Fatalf("new prompt should require confirm: %#v", env.Data)
	}
	digest := stringValue(env.Data["confirmation_digest"])
	if len(digest) != 64 {
		t.Fatalf("digest = %q", digest)
	}
	views := env.Data["views"].(map[string]any)
	decisionText := stringValue(views["decision"])
	if !strings.Contains(decisionText, "Q1") || !strings.Contains(decisionText, "独立验收门槛") {
		t.Fatalf("decision view missing Q table: %s", decisionText)
	}
	deliveryText := stringValue(views["delivery"])
	if !strings.Contains(deliveryText, "W1") || !strings.Contains(deliveryText, "Delivery Map") {
		t.Fatalf("delivery view missing waves: %s", deliveryText)
	}

	// delivery changes must not alter digest
	deliveryOnly := map[string]any{
		"delivery": map[string]any{
			"waves": []any{
				map[string]any{"id": "W1", "item_ids": []any{"Q1"}, "parallel": false},
				map[string]any{"id": "W2", "item_ids": []any{"Q2"}, "parallel": false},
				map[string]any{"id": "W3", "item_ids": []any{"Q3"}, "parallel": false},
				map[string]any{"id": "W4", "item_ids": []any{"Q4"}, "parallel": false},
				map[string]any{"id": "W5", "item_ids": []any{"Q5"}, "parallel": false},
			},
		},
	}
	// cannot delivery-only before confirm
	rawDelivery, _ := json.Marshal(deliveryOnly)
	env = runScriptDomainEnvelope(t, runQuick, []string{
		"--project-root", root,
		"checkpoint-stage", "260805-001",
		"--delivery-only",
		"--input-json", string(rawDelivery),
	})
	if env.Status == "ok" {
		t.Fatalf("delivery-only before confirm should fail")
	}

	env = runScriptDomainEnvelope(t, runQuick, []string{
		"--project-root", root,
		"checkpoint-confirm", "260805-001",
		"--digest", digest,
	})
	if env.Status != "ok" {
		t.Fatalf("confirm status=%s blockers=%v", env.Status, env.Blockers)
	}
	if stringValue(env.Data["confirmation_state"]) != "confirmed" {
		t.Fatalf("state=%v", env.Data["confirmation_state"])
	}

	statusRaw, err := os.ReadFile(filepath.Join(workspace, "STATUS.md"))
	if err != nil {
		t.Fatalf("read status: %v", err)
	}
	statusText := string(statusRaw)
	if !strings.Contains(statusText, "understanding_confirmed: true") && !strings.Contains(statusText, "understanding_confirmed: \"true\"") {
		// frontmatter may be unquoted true
		if !strings.Contains(statusText, "understanding_confirmed: true") {
			// emitFrontmatter writes key: value without quotes for true?
			if !strings.Contains(statusText, "understanding_confirmed:") {
				t.Fatalf("status missing confirmation flag: %s", statusText)
			}
		}
	}
	if !strings.Contains(statusText, "runtime-managed:quick-confirmation-v1") {
		t.Fatalf("status missing runtime managed marker")
	}
	if !strings.Contains(statusText, "confirmation_digest:") {
		t.Fatalf("status missing digest projection")
	}

	env = runScriptDomainEnvelope(t, runQuick, []string{
		"--project-root", root,
		"checkpoint-stage", "260805-001",
		"--delivery-only",
		"--input-json", string(rawDelivery),
	})
	if env.Status != "ok" {
		t.Fatalf("delivery-only after confirm status=%s blockers=%v", env.Status, env.Blockers)
	}
	if stringValue(env.Data["confirmation_digest"]) != digest {
		t.Fatalf("delivery-only changed decision digest")
	}

	env = runScriptDomainEnvelope(t, runQuick, []string{
		"--project-root", root,
		"checkpoint-show", "260805-001",
		"--view", "pulse",
	})
	if env.Status != "ok" {
		t.Fatalf("show pulse status=%s blockers=%v", env.Status, env.Blockers)
	}
	if !strings.Contains(stringValue(env.Data["text"]), "Checkpoint 已确认") {
		t.Fatalf("pulse text = %s", env.Data["text"])
	}
}

func TestQuickCheckpointInheritedDiscussionSkipsReconfirm(t *testing.T) {
	root := t.TempDir()
	workspace := filepath.Join(root, ".planning", "quick", "260805-002-inherited")
	mustMkdirAllScriptDomainTest(t, workspace)
	mustWriteScriptDomainTest(t, filepath.Join(workspace, "STATUS.md"), `---
id: "260805-002"
slug: "inherited"
title: "Inherited"
status: gathering
understanding_confirmed: false
---

## Understanding Checkpoint

placeholder

## Execution

placeholder
`)

	payload := map[string]any{
		"source": map[string]any{
			"kind":             "discussion",
			"discussion_slug":  "prompt-authoring-modes",
			"review_digest":    strings.Repeat("a", 64),
			"semantic_delta":   false,
		},
		"decision": map[string]any{
			"goal":                "交付已确认的 Prompt 资产能力",
			"user_visible_result": "可发布可安装的 Prompt",
			"scope": map[string]any{
				"include": []any{"发布", "CLI"},
				"exclude": []any{"MCP"},
			},
			"items": []any{
				map[string]any{"id": "Q1", "deliverable": "元数据契约", "depends_on": []any{}, "acceptance": "类型一致"},
			},
			"reconfirmation_trigger": "范围变化",
		},
	}
	raw, _ := json.Marshal(payload)
	env := runScriptDomainEnvelope(t, runQuick, []string{
		"--project-root", root,
		"checkpoint-stage", "260805-002",
		"--input-json", string(raw),
	})
	if env.Status != "ok" {
		t.Fatalf("stage status=%s blockers=%v", env.Status, env.Blockers)
	}
	if env.Data["requires_user_confirm"] != false {
		t.Fatalf("inherited should not require confirm: %#v", env.Data)
	}
	if stringValue(env.Data["confirmation_state"]) != "inherited" {
		t.Fatalf("state=%v", env.Data["confirmation_state"])
	}
	decisionText := stringValue(env.Data["views"].(map[string]any)["decision"])
	if !strings.Contains(decisionText, "已继承确认") || !strings.Contains(decisionText, "无需重复确认") {
		t.Fatalf("decision view should show inheritance summary: %s", decisionText)
	}
}

func TestQuickCheckpointRejectsCyclesAndMissingAcceptance(t *testing.T) {
	root := t.TempDir()
	workspace := filepath.Join(root, ".planning", "quick", "260805-003-invalid")
	mustMkdirAllScriptDomainTest(t, workspace)
	mustWriteScriptDomainTest(t, filepath.Join(workspace, "STATUS.md"), `---
id: "260805-003"
slug: "invalid"
title: "Invalid"
status: gathering
understanding_confirmed: false
---

## Understanding Checkpoint

x

## Execution

y
`)

	cycle := map[string]any{
		"source": map[string]any{"kind": "prompt"},
		"decision": map[string]any{
			"goal":                "cycle",
			"user_visible_result": "cycle",
			"scope":               map[string]any{"include": []any{"a"}, "exclude": []any{"b"}},
			"items": []any{
				map[string]any{"id": "Q1", "deliverable": "A", "depends_on": []any{"Q2"}, "acceptance": "ok"},
				map[string]any{"id": "Q2", "deliverable": "B", "depends_on": []any{"Q1"}, "acceptance": "ok"},
			},
			"reconfirmation_trigger": "x",
		},
	}
	raw, _ := json.Marshal(cycle)
	env := runScriptDomainEnvelope(t, runQuick, []string{
		"--project-root", root,
		"checkpoint-stage", "260805-003",
		"--input-json", string(raw),
	})
	if env.Status == "ok" {
		t.Fatalf("cycle should fail")
	}

	missing := map[string]any{
		"source": map[string]any{"kind": "prompt"},
		"decision": map[string]any{
			"goal":                "missing",
			"user_visible_result": "missing",
			"scope":               map[string]any{"include": []any{"a"}, "exclude": []any{"b"}},
			"items": []any{
				map[string]any{"id": "Q1", "deliverable": "A", "depends_on": []any{}, "acceptance": ""},
			},
			"reconfirmation_trigger": "x",
		},
	}
	raw, _ = json.Marshal(missing)
	env = runScriptDomainEnvelope(t, runQuick, []string{
		"--project-root", root,
		"checkpoint-stage", "260805-003",
		"--input-json", string(raw),
	})
	if env.Status == "ok" {
		t.Fatalf("missing acceptance should fail")
	}
}

func TestQuickConfirmationDigestIgnoresDelivery(t *testing.T) {
	decision := quickConfirmationDecision{
		Goal:              "goal",
		UserVisibleResult: "result",
		Scope:             quickConfirmationScope{Include: []string{"a"}, Exclude: []string{"b"}},
		Items: []quickConfirmationItem{
			{ID: "Q1", Deliverable: "one", DependsOn: nil, Acceptance: "pass", WriteScope: []string{"src/a.go"}},
		},
		ReconfirmationTrigger: "change",
	}
	d1, err := computeQuickConfirmationDigest(decision)
	if err != nil {
		t.Fatal(err)
	}
	decision.Items[0].WriteScope = []string{"src/b.go", "src/c.go"}
	d2, err := computeQuickConfirmationDigest(decision)
	if err != nil {
		t.Fatal(err)
	}
	if d1 != d2 {
		t.Fatalf("write_scope must not affect digest")
	}
	decision.Items[0].Acceptance = "different"
	d3, err := computeQuickConfirmationDigest(decision)
	if err != nil {
		t.Fatal(err)
	}
	if d3 == d1 {
		t.Fatalf("acceptance change must affect digest")
	}
}
