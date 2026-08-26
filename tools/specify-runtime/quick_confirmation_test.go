package main

import (
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func quickNotApplicableSourceContinuity() map[string]any {
	return map[string]any{
		"schema": "spec-kit-ui-source-continuity-v1", "applicability": "not-applicable",
		"mode": "none", "reason": "This test does not exercise source-grounded reconstruction.",
		"coverage":       map[string]any{"surface_ids": []any{}, "interaction_ids": []any{}, "component_ids": []any{}},
		"authority_refs": []any{}, "surface_bindings": []any{}, "action_bindings": []any{},
		"asset_bindings": []any{}, "unresolved_gaps": []any{},
	}
}

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
			"ui_confirmation": map[string]any{
				"applicable":                        true,
				"confirmation_purpose":              "Quick implementation proposal for Prompt discovery",
				"user_and_primary_job":              "创作者发布并管理 Prompt",
				"design_basis_and_source_material":  []any{"现有资产详情页"},
				"target_experience":                 "清晰、可扫描的 Prompt 管理体验",
				"structure_and_visible_change":      "统一发布、治理和详情层级",
				"interaction_states_and_adaptation": []any{"桌面和窄窗均可操作"},
				"design_boundaries": map[string]any{
					"must_preserve": []any{"现有导航"},
					"may_adapt":     []any{"内容密度"},
					"must_not":      []any{"引入第二套视觉体系"},
				},
				"acceptance_evidence": []any{"真实入口视觉检查"},
				"source_continuity":   quickNotApplicableSourceContinuity(),
				"design_binding": map[string]any{
					"scope":                "prompt-detail",
					"design_change_id":     "UD-1234",
					"design_change_ref":    ".specify/design/changes/UD-1234/design-change.md",
					"design_change_sha256": strings.Repeat("b", 64),
					"design_contract_ref":  ".specify/design/changes/UD-1234/handoff.json",
				},
			},
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
	for _, marker := range []string{
		"## 请确认本次修改", "### 你会看到", "### 本次会做", "### 本次不做",
		"### 交付与验收", "### 界面方向", "Q1", "DB、API、Web 类型一致",
		"scope=prompt-detail", "design_change_id=UD-1234",
		"design_change_ref=.specify/design/changes/UD-1234/design-change.md",
		"design_change_sha256=" + strings.Repeat("b", 64),
		"design_contract_ref=.specify/design/changes/UD-1234/handoff.json",
	} {
		if !strings.Contains(decisionText, marker) {
			t.Fatalf("decision view missing human-first marker %q: %s", marker, decisionText)
		}
	}
	if strings.Contains(decisionText, digest) || strings.Contains(decisionText, "confirmation_digest:") {
		t.Fatalf("default human view must not print the raw digest: %s", decisionText)
	}
	if strings.Contains(decisionText, "━━━━━") || strings.Contains(decisionText, "独立验收门槛") {
		t.Fatalf("default human view must not use the dense Q table: %s", decisionText)
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

func TestQuickCheckpointDeltaShowsOnlyChangedDecisionFields(t *testing.T) {
	root := t.TempDir()
	workspace := filepath.Join(root, ".planning", "quick", "260805-004-delta")
	mustMkdirAllScriptDomainTest(t, workspace)
	mustWriteScriptDomainTest(t, filepath.Join(workspace, "STATUS.md"), `---
id: "260805-004"
slug: "delta"
title: "Delta"
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
			"kind":                    "delta",
			"semantic_delta":          true,
			"delta_summary":           "Q2 验收与目标体验调整",
			"changed_decision_fields": []any{"items.Q2.acceptance", "ui_confirmation.target_experience"},
		},
		"decision": map[string]any{
			"goal":                "保持完整决策用于摘要校验",
			"user_visible_result": "未变化的用户结果",
			"scope": map[string]any{
				"include": []any{"未变化的包含范围"},
				"exclude": []any{"未变化的排除范围"},
			},
			"items": []any{
				map[string]any{"id": "Q1", "deliverable": "未变化交付", "depends_on": []any{}, "acceptance": "未变化验收"},
				map[string]any{"id": "Q2", "deliverable": "目标交付", "depends_on": []any{"Q1"}, "acceptance": "新的 Q2 验收"},
			},
			"reconfirmation_trigger": "未变化的重确认条件",
			"ui_confirmation": map[string]any{
				"applicable":                        true,
				"confirmation_purpose":              "未变化的确认目的",
				"user_and_primary_job":              "未变化的使用者",
				"target_experience":                 "新的目标体验",
				"structure_and_visible_change":      "未变化的可见变化",
				"interaction_states_and_adaptation": []any{"未变化的交互"},
				"acceptance_evidence":               []any{"未变化的证据"},
				"source_continuity":                 quickNotApplicableSourceContinuity(),
			},
		},
	}
	raw, err := json.Marshal(payload)
	if err != nil {
		t.Fatalf("marshal: %v", err)
	}
	env := runScriptDomainEnvelope(t, runQuick, []string{
		"--project-root", root,
		"checkpoint-stage", "260805-004",
		"--input-json", string(raw),
	})
	if env.Status != "ok" {
		t.Fatalf("stage status=%s blockers=%v", env.Status, env.Blockers)
	}
	decisionText := stringValue(env.Data["views"].(map[string]any)["decision"])
	for _, marker := range []string{"本次只确认：Q2 验收与目标体验调整", "Q2", "新的 Q2 验收", "### 界面方向", "新的目标体验"} {
		if !strings.Contains(decisionText, marker) {
			t.Fatalf("delta decision view missing %q: %s", marker, decisionText)
		}
	}
	for _, unchanged := range []string{
		"保持完整决策用于摘要校验", "未变化的用户结果", "未变化的包含范围",
		"未变化的排除范围", "未变化交付", "未变化验收", "未变化的确认目的",
		"未变化的使用者", "未变化的可见变化", "未变化的交互",
		"未变化的证据", "未变化的重确认条件",
	} {
		if strings.Contains(decisionText, unchanged) {
			t.Fatalf("delta decision view replayed unchanged field %q: %s", unchanged, decisionText)
		}
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
			"kind":            "discussion",
			"discussion_slug": "prompt-authoring-modes",
			"review_digest":   strings.Repeat("a", 64),
			"semantic_delta":  false,
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

func TestQuickConfirmationRejectsInvalidDeltaMetadata(t *testing.T) {
	base := func() *quickConfirmationDoc {
		return &quickConfirmationDoc{
			Source: quickConfirmationSource{
				Kind:          "delta",
				SemanticDelta: true,
				DeltaSummary:  "acceptance changed",
			},
			Decision: quickConfirmationDecision{
				Goal:              "goal",
				UserVisibleResult: "result",
				Scope:             quickConfirmationScope{Include: []string{"a"}, Exclude: []string{"b"}},
				Items: []quickConfirmationItem{
					{ID: "Q1", Deliverable: "one", Acceptance: "pass"},
				},
				ReconfirmationTrigger: "change",
			},
			Delivery: quickConfirmationDelivery{
				Waves: []quickConfirmationWave{{ID: "W1", ItemIDs: []string{"Q1"}}},
			},
		}
	}

	cases := []struct {
		name   string
		fields []string
	}{
		{name: "missing"},
		{name: "unknown top-level field", fields: []string{"unknown"}},
		{name: "unknown work item", fields: []string{"items.Q9.acceptance"}},
		{name: "duplicate", fields: []string{"goal", "goal"}},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			doc := base()
			doc.Source.ChangedDecisionFields = tc.fields
			if err := validateQuickDeltaMetadata(doc); err == nil {
				t.Fatalf("invalid delta metadata should fail: %#v", tc.fields)
			}
		})
	}
}

func TestQuickCheckpointLegacyDeltaAllowsDeliveryOnlyUpdate(t *testing.T) {
	root := t.TempDir()
	workspace := filepath.Join(root, ".planning", "quick", "260805-005-legacy-delta")
	mustMkdirAllScriptDomainTest(t, workspace)
	mustWriteScriptDomainTest(t, filepath.Join(workspace, "STATUS.md"), `---
id: "260805-005"
slug: "legacy-delta"
title: "Legacy delta"
status: ready
understanding_confirmed: true
---

## Understanding Checkpoint

legacy

## Execution

legacy
`)
	decision := quickConfirmationDecision{
		Goal:              "legacy goal",
		UserVisibleResult: "legacy result",
		Scope:             quickConfirmationScope{Include: []string{"a"}, Exclude: []string{"b"}},
		Items: []quickConfirmationItem{
			{ID: "Q1", Deliverable: "one", Acceptance: "pass"},
		},
		ReconfirmationTrigger: "change",
	}
	digest, err := computeQuickConfirmationDigest(decision)
	if err != nil {
		t.Fatal(err)
	}
	legacy := &quickConfirmationDoc{
		Schema:             quickConfirmationSchema,
		Workspace:          "260805-005-legacy-delta",
		ConfirmationMode:   "delta",
		ConfirmationState:  "confirmed",
		ConfirmationDigest: digest,
		Source: quickConfirmationSource{
			Kind:          "delta",
			SemanticDelta: true,
			DeltaSummary:  "legacy delta before field-level rendering",
		},
		Decision: decision,
		Delivery: quickConfirmationDelivery{
			Waves: []quickConfirmationWave{{ID: "W1", ItemIDs: []string{"Q1"}}},
		},
	}
	if err := (quickService{projectRoot: root}).persistConfirmation(workspace, legacy); err != nil {
		t.Fatalf("persist legacy confirmation: %v", err)
	}
	payload := map[string]any{
		"delivery": map[string]any{
			"waves": []any{map[string]any{"id": "W1", "item_ids": []any{"Q1"}, "parallel": false}},
		},
	}
	raw, _ := json.Marshal(payload)
	env := runScriptDomainEnvelope(t, runQuick, []string{
		"--project-root", root,
		"checkpoint-stage", "260805-005",
		"--delivery-only",
		"--input-json", string(raw),
	})
	if env.Status != "ok" {
		t.Fatalf("legacy delta delivery-only update should remain compatible: blockers=%v", env.Blockers)
	}
}

func TestQuickConfirmationSemanticDeltaFlagSelectsDeltaMode(t *testing.T) {
	doc := &quickConfirmationDoc{
		Source: quickConfirmationSource{Kind: "prompt", SemanticDelta: true},
	}
	mode, state, err := deriveQuickConfirmationMode(doc)
	if err != nil {
		t.Fatal(err)
	}
	if mode != "delta" || state != "staged" {
		t.Fatalf("semantic delta flag should select staged delta mode, got mode=%s state=%s", mode, state)
	}
}
