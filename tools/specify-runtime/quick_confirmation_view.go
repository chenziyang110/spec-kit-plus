package main

import (
	"fmt"
	"strings"
)

func renderQuickConfirmationView(doc *quickConfirmationDoc, view string) (string, error) {
	switch strings.ToLower(strings.TrimSpace(view)) {
	case "decision":
		return renderQuickDecisionView(doc), nil
	case "delivery":
		return renderQuickDeliveryView(doc), nil
	case "pulse":
		return renderQuickPulseView(doc), nil
	default:
		return "", fmt.Errorf("unsupported view %q (use decision|delivery|pulse)", view)
	}
}

func renderQuickDecisionView(doc *quickConfirmationDoc) string {
	var b strings.Builder
	b.WriteString("## 请确认本次修改\n\n")
	sourceLabel := doc.Source.Kind
	if doc.Source.Kind == "discussion" && doc.Source.DiscussionSlug != "" {
		sourceLabel = "discussion/" + doc.Source.DiscussionSlug
	}
	switch doc.ConfirmationState {
	case "inherited":
		b.WriteString(fmt.Sprintf("确认状态：已继承确认（来源：%s），无需重复确认。\n\n", sourceLabel))
	case "confirmed":
		if doc.ConfirmationMode == "delta" {
			b.WriteString(fmt.Sprintf("确认状态：变更已确认（%s）。\n\n", firstNonEmpty(doc.Source.DeltaSummary, "局部变更")))
		} else {
			b.WriteString("确认状态：已确认。\n\n")
		}
	case "staged":
		if doc.ConfirmationMode == "delta" {
			b.WriteString(fmt.Sprintf("确认状态：待确认变更。本次只确认：%s。\n\n", firstNonEmpty(doc.Source.DeltaSummary, "已标记的变更项")))
		} else {
			b.WriteString("确认状态：待确认。\n\n")
		}
	default:
		b.WriteString("确认状态：待确认。\n\n")
	}
	if quickUsesDeltaFieldFilter(doc) {
		b.WriteString("未列出的决策保持不变。\n\n")
	}
	if quickDecisionFieldSelected(doc, "goal") {
		b.WriteString(doc.Decision.Goal)
		b.WriteString("\n\n")
	}
	if quickDecisionFieldSelected(doc, "current_state_evidence") && (len(doc.Decision.CurrentStateEvidence) > 0 || quickUsesDeltaFieldFilter(doc)) {
		writeQuickBulletSection(&b, "### 当前情况与依据", doc.Decision.CurrentStateEvidence)
	}
	if quickDecisionFieldSelected(doc, "user_visible_result") {
		writeQuickBulletSection(&b, "### 你会看到", []string{doc.Decision.UserVisibleResult})
	}
	if quickDecisionFieldSelected(doc, "scope.include") {
		writeQuickBulletSection(&b, "### 本次会做", doc.Decision.Scope.Include)
	}
	if quickDecisionFieldSelected(doc, "scope.exclude") {
		writeQuickBulletSection(&b, "### 本次不做", doc.Decision.Scope.Exclude)
	}
	if quickDecisionFieldSelected(doc, "scope.defer") && (len(doc.Decision.Scope.Defer) > 0 || quickUsesDeltaFieldFilter(doc)) {
		writeQuickBulletSection(&b, "### 后续处理", doc.Decision.Scope.Defer)
	}

	selectedItems := make([]quickConfirmationItem, 0, len(doc.Decision.Items))
	for _, item := range doc.Decision.Items {
		if quickDecisionFieldSelected(doc, "items."+item.ID) {
			selectedItems = append(selectedItems, item)
		}
	}
	if len(selectedItems) > 0 {
		b.WriteString("### 交付与验收\n\n")
	}
	for _, item := range selectedItems {
		b.WriteString(fmt.Sprintf("- **%s · %s**\n", item.ID, item.Deliverable))
		b.WriteString(fmt.Sprintf("  - 验收：%s\n", item.Acceptance))
		if len(item.DependsOn) > 0 {
			b.WriteString(fmt.Sprintf("  - 前置：%s\n", strings.Join(item.DependsOn, "、")))
		}
	}
	if len(selectedItems) > 0 {
		b.WriteString("\n")
	}

	if quickDecisionFieldSelected(doc, "ui_confirmation") {
		if quickBool(doc.Decision.UIConfirmation["applicable"]) {
			renderQuickUIDecision(&b, doc)
		} else if quickUsesDeltaFieldFilter(doc) {
			writeQuickBulletSection(&b, "### 界面方向", []string{"本次变更后不再需要界面确认。"})
		}
	}

	approachSelected := quickDecisionFieldSelected(doc, "recommended_approach")
	risksSelected := quickDecisionFieldSelected(doc, "assumptions_and_risks")
	evidenceSelected := quickDecisionFieldSelected(doc, "completion_evidence")
	showStandards := approachSelected && doc.Decision.RecommendedApproach != "" || risksSelected && len(doc.Decision.AssumptionsAndRisks) > 0 || evidenceSelected && len(doc.Decision.CompletionEvidence) > 0
	if quickUsesDeltaFieldFilter(doc) && (approachSelected || risksSelected || evidenceSelected) {
		showStandards = true
	}
	if showStandards {
		b.WriteString("### 方案与完成标准\n\n")
		if approachSelected {
			appendQuickLabeledBullet(&b, "推荐路径", firstNonEmpty(doc.Decision.RecommendedApproach, "无"))
		}
		if risksSelected {
			if len(doc.Decision.AssumptionsAndRisks) == 0 {
				appendQuickLabeledBullet(&b, "假设或风险", "无")
			}
			for _, risk := range doc.Decision.AssumptionsAndRisks {
				appendQuickLabeledBullet(&b, "假设或风险", risk)
			}
		}
		if evidenceSelected {
			if len(doc.Decision.CompletionEvidence) == 0 {
				appendQuickLabeledBullet(&b, "完成证据", "无")
			}
			for _, evidence := range doc.Decision.CompletionEvidence {
				appendQuickLabeledBullet(&b, "完成证据", evidence)
			}
		}
		b.WriteString("\n")
	}

	if quickDecisionFieldSelected(doc, "reconfirmation_trigger") {
		writeQuickBulletSection(&b, "### 需要重新确认的情况", []string{doc.Decision.ReconfirmationTrigger})
	}
	if doc.ConfirmationState == "staged" {
		b.WriteString("回复：**确认** / **修改范围** / **修改 Qn 验收** / **修改界面方向**\n")
	}
	return b.String()
}

func quickUsesDeltaFieldFilter(doc *quickConfirmationDoc) bool {
	return doc.ConfirmationMode == "delta" && len(doc.Source.ChangedDecisionFields) > 0
}

func quickDecisionFieldSelected(doc *quickConfirmationDoc, field string) bool {
	if !quickUsesDeltaFieldFilter(doc) {
		return true
	}
	wanted := strings.ToLower(strings.TrimSpace(field))
	for _, raw := range doc.Source.ChangedDecisionFields {
		selected := strings.ToLower(strings.TrimSpace(raw))
		if selected == wanted || strings.HasPrefix(selected, wanted+".") || strings.HasPrefix(wanted, selected+".") {
			return true
		}
	}
	return false
}

func writeQuickBulletSection(b *strings.Builder, heading string, values []string) {
	b.WriteString(heading)
	b.WriteString("\n\n")
	if len(values) == 0 {
		b.WriteString("- 无\n\n")
		return
	}
	for _, value := range values {
		if text := strings.TrimSpace(value); text != "" {
			b.WriteString("- ")
			b.WriteString(text)
			b.WriteString("\n")
		}
	}
	b.WriteString("\n")
}

func appendQuickLabeledBullet(b *strings.Builder, label, value string) {
	if text := strings.TrimSpace(value); text != "" {
		b.WriteString(fmt.Sprintf("- **%s**：%s\n", label, text))
	}
}

func renderQuickUIDecision(b *strings.Builder, doc *quickConfirmationDoc) {
	ui := doc.Decision.UIConfirmation
	b.WriteString("### 界面方向\n\n")
	if quickUsesDeltaFieldFilter(doc) && quickDecisionFieldSelected(doc, "ui_confirmation.applicable") {
		appendQuickLabeledBullet(b, "界面适用性", "适用")
	}
	if quickDecisionFieldSelected(doc, "ui_confirmation.confirmation_purpose") {
		appendQuickLabeledBullet(b, "确认目的", stringValue(ui["confirmation_purpose"]))
	}
	if quickDecisionFieldSelected(doc, "ui_confirmation.user_and_primary_job") {
		appendQuickLabeledBullet(b, "使用者与主要任务", stringValue(ui["user_and_primary_job"]))
	}
	if quickDecisionFieldSelected(doc, "ui_confirmation.target_experience") {
		appendQuickLabeledBullet(b, "目标体验", stringValue(ui["target_experience"]))
	}
	if quickDecisionFieldSelected(doc, "ui_confirmation.structure_and_visible_change") {
		appendQuickLabeledBullet(b, "可见变化", stringValue(ui["structure_and_visible_change"]))
	}

	boundaries := mapValue(ui["design_boundaries"])
	if quickDecisionFieldSelected(doc, "ui_confirmation.design_boundaries.must_preserve") {
		appendQuickLabeledBullet(b, "必须保留", joinOrDash(quickStringSlice(boundaries["must_preserve"])))
	}
	if quickDecisionFieldSelected(doc, "ui_confirmation.design_boundaries.may_adapt") {
		appendQuickLabeledBullet(b, "可以调整", joinOrDash(quickStringSlice(boundaries["may_adapt"])))
	}
	if quickDecisionFieldSelected(doc, "ui_confirmation.design_boundaries.must_not") {
		appendQuickLabeledBullet(b, "不得改变", joinOrDash(quickStringSlice(boundaries["must_not"])))
	}
	if quickDecisionFieldSelected(doc, "ui_confirmation.design_basis_and_source_material") {
		appendQuickLabeledBullet(b, "设计依据", joinOrDash(quickStringSlice(ui["design_basis_and_source_material"])))
	}
	if quickDecisionFieldSelected(doc, "ui_confirmation.interaction_states_and_adaptation") {
		appendQuickLabeledBullet(b, "交互与适配", joinOrDash(quickStringSlice(ui["interaction_states_and_adaptation"])))
	}
	if quickDecisionFieldSelected(doc, "ui_confirmation.acceptance_evidence") {
		appendQuickLabeledBullet(b, "验收方式", joinOrDash(quickStringSlice(ui["acceptance_evidence"])))
	}
	if quickDecisionFieldSelected(doc, "ui_confirmation.source_continuity") {
		if continuity := mapValue(ui["source_continuity"]); len(continuity) > 0 {
			renderQuickSourceContinuity(b, doc, continuity)
		} else if quickUsesDeltaFieldFilter(doc) {
			appendQuickLabeledBullet(b, "来源连续性", "无")
		}
	}

	if quickDecisionFieldSelected(doc, "ui_confirmation.design_binding") {
		if binding := mapValue(ui["design_binding"]); len(binding) > 0 {
			fields := []string{
				"scope=" + stringValue(binding["scope"]),
				"design_change_id=" + stringValue(binding["design_change_id"]),
				"design_change_ref=" + stringValue(binding["design_change_ref"]),
				"design_change_sha256=" + stringValue(binding["design_change_sha256"]),
				"design_contract_ref=" + stringValue(binding["design_contract_ref"]),
			}
			appendQuickLabeledBullet(b, "注册设计绑定", strings.Join(fields, "；"))
		} else if quickUsesDeltaFieldFilter(doc) {
			appendQuickLabeledBullet(b, "注册设计绑定", "无")
		}
	}
	b.WriteString("\n")
}

func renderQuickSourceContinuity(b *strings.Builder, doc *quickConfirmationDoc, continuity map[string]any) {
	b.WriteString("\n#### 来源连续性\n\n")
	if quickDecisionFieldSelected(doc, "ui_confirmation.source_continuity.mode") || quickDecisionFieldSelected(doc, "ui_confirmation.source_continuity.reason") {
		mode := strings.TrimSpace(stringValue(continuity["mode"]))
		reason := strings.TrimSpace(stringValue(continuity["reason"]))
		appendQuickLabeledBullet(b, "来源模式", strings.Trim(strings.Join([]string{mode, reason}, "；"), "；"))
	}
	if quickDecisionFieldSelected(doc, "ui_confirmation.source_continuity.authority_refs") {
		appendQuickLabeledBullet(b, "权威依据", joinOrDash(quickStringSlice(continuity["authority_refs"])))
	}
	if quickDecisionFieldSelected(doc, "ui_confirmation.source_continuity.coverage") {
		coverage := mapValue(continuity["coverage"])
		appendQuickLabeledBullet(
			b,
			"覆盖范围",
			"surface="+joinOrDash(quickStringSlice(coverage["surface_ids"]))+
				"；interaction="+joinOrDash(quickStringSlice(coverage["interaction_ids"]))+
				"；component="+joinOrDash(quickStringSlice(coverage["component_ids"])),
		)
	}
	if quickDecisionFieldSelected(doc, "ui_confirmation.source_continuity.surface_bindings") {
		for _, surface := range listValue(continuity["surface_bindings"]) {
			row := mapValue(surface)
			rowPath := "ui_confirmation.source_continuity.surface_bindings." + stringValue(row["id"])
			if !quickDecisionFieldSelected(doc, rowPath) {
				continue
			}
			value := fmt.Sprintf("%s（%s；%s）", stringValue(row["surface_id"]), stringValue(row["discovery"]), stringValue(row["disposition"]))
			appendQuickLabeledBullet(b, "界面表面", value)
		}
	}
	if quickDecisionFieldSelected(doc, "ui_confirmation.source_continuity.action_bindings") {
		for _, action := range listValue(continuity["action_bindings"]) {
			row := mapValue(action)
			rowPath := "ui_confirmation.source_continuity.action_bindings." + stringValue(row["id"])
			if !quickDecisionFieldSelected(doc, rowPath) {
				continue
			}
			value := fmt.Sprintf("%s；业务结果：%s", stringValue(row["user_promise"]), stringValue(row["business_outcome"]))
			appendQuickLabeledBullet(b, "业务动作", value)
		}
	}
	if quickDecisionFieldSelected(doc, "ui_confirmation.source_continuity.asset_bindings") {
		for _, asset := range listValue(continuity["asset_bindings"]) {
			row := mapValue(asset)
			rowPath := "ui_confirmation.source_continuity.asset_bindings." + stringValue(row["id"])
			if !quickDecisionFieldSelected(doc, rowPath) {
				continue
			}
			value := fmt.Sprintf("%s → %s（%s；%s）", stringValue(row["semantic_role"]), stringValue(row["target_ref"]), stringValue(row["target_strategy"]), stringValue(row["placeholder_policy"]))
			appendQuickLabeledBullet(b, "资产", value)
		}
	}
	if quickDecisionFieldSelected(doc, "ui_confirmation.source_continuity.unresolved_gaps") {
		gaps := quickStringSlice(continuity["unresolved_gaps"])
		if len(gaps) == 0 {
			b.WriteString("- 未解决缺口：无\n")
		} else {
			b.WriteString("- 未解决缺口：")
			b.WriteString(strings.Join(gaps, "；"))
			b.WriteString("\n")
		}
	}
}

func renderQuickDeliveryView(doc *quickConfirmationDoc) string {
	var b strings.Builder
	b.WriteString("## Delivery Map\n\n")
	itemLabel := map[string]string{}
	for _, item := range doc.Decision.Items {
		itemLabel[item.ID] = item.Deliverable
	}
	for _, wave := range doc.Delivery.Waves {
		b.WriteString(fmt.Sprintf("%s\n", wave.ID))
		if len(wave.ItemIDs) == 1 {
			id := wave.ItemIDs[0]
			b.WriteString(fmt.Sprintf("└─ %s %s\n\n", id, itemLabel[id]))
			continue
		}
		for i, id := range wave.ItemIDs {
			branch := "├─"
			suffix := ""
			if i+1 == len(wave.ItemIDs) {
				branch = "└─"
				if wave.Parallel {
					suffix = "  ┘ 并行"
				}
			} else if wave.Parallel && i == 0 {
				suffix = "  ┐"
			} else if wave.Parallel {
				suffix = "  │"
			}
			b.WriteString(fmt.Sprintf("%s %s %s%s\n", branch, id, itemLabel[id], suffix))
		}
		b.WriteString("\n")
	}
	if len(doc.Delivery.JoinPoints) > 0 {
		b.WriteString("Join points:\n")
		for _, join := range doc.Delivery.JoinPoints {
			gate := join.Gate
			if gate == "" {
				gate = "prerequisite acceptance"
			}
			b.WriteString(fmt.Sprintf("- after %s → start %s (%s)\n", strings.Join(join.After, ", "), join.Starts, gate))
		}
		b.WriteString("\n")
	}
	if doc.Delivery.IntegrationGate != "" {
		b.WriteString(fmt.Sprintf("最终集成门槛：%s\n", doc.Delivery.IntegrationGate))
	}
	b.WriteString("\n（Delivery Map 为 Agent 执行投影，不要求用户确认；仅调整 wave/batch/subagent 不触发重新确认。）\n")
	return b.String()
}

func renderQuickPulseView(doc *quickConfirmationDoc) string {
	var b strings.Builder
	b.WriteString("## Delivery Pulse\n\n")
	switch doc.ConfirmationState {
	case "inherited":
		b.WriteString("✓ Checkpoint 已继承\n")
	case "confirmed":
		b.WriteString("✓ Checkpoint 已确认\n")
	default:
		b.WriteString("• Checkpoint 待确认\n")
	}

	statusByID := map[string]quickWorkItemStatus{}
	for _, row := range doc.Execution.WorkItemStatus {
		statusByID[row.WorkItemID] = row
	}
	for _, item := range doc.Decision.Items {
		row, ok := statusByID[item.ID]
		if !ok {
			row = quickWorkItemStatus{WorkItemID: item.ID, Status: "pending"}
		}
		label := item.Deliverable
		switch strings.ToLower(row.Status) {
		case "in_progress", "active":
			b.WriteString(fmt.Sprintf("→ %s %s 正在执行\n", item.ID, label))
		case "accepted", "done", "completed":
			b.WriteString(fmt.Sprintf("✓ %s %s 已验收\n", item.ID, label))
		case "blocked":
			b.WriteString(fmt.Sprintf("✕ %s %s 阻塞\n", item.ID, label))
		default:
			waiting := unmetQuickDeps(item.DependsOn, statusByID)
			if len(waiting) > 0 {
				b.WriteString(fmt.Sprintf("⏸ %s %s 等待 %s\n", item.ID, label, strings.Join(waiting, "、")))
			} else if quickContains(doc.Execution.ActiveItemIDs, item.ID) {
				b.WriteString(fmt.Sprintf("→ %s %s 正在执行\n", item.ID, label))
			} else {
				b.WriteString(fmt.Sprintf("· %s %s 就绪\n", item.ID, label))
			}
		}
	}
	if doc.Execution.JoinPoint != "" {
		b.WriteString(fmt.Sprintf("\nJoin point：%s\n", doc.Execution.JoinPoint))
	} else if len(doc.Delivery.JoinPoints) > 0 {
		// derive next join from first incomplete wave
		for _, join := range doc.Delivery.JoinPoints {
			ready := true
			for _, id := range join.After {
				if strings.ToLower(statusByID[id].Status) != "accepted" {
					ready = false
					break
				}
			}
			if !ready {
				b.WriteString(fmt.Sprintf("\nJoin point：%s 验收通过后启动 %s\n", strings.Join(join.After, "、"), join.Starts))
				break
			}
		}
	}
	if len(doc.Execution.Blockers) > 0 {
		b.WriteString(fmt.Sprintf("\nBlockers：%s\n", strings.Join(doc.Execution.Blockers, "；")))
	}
	return b.String()
}

func unmetQuickDeps(deps []string, statusByID map[string]quickWorkItemStatus) []string {
	out := []string{}
	for _, dep := range deps {
		if strings.ToLower(statusByID[dep].Status) != "accepted" {
			out = append(out, dep)
		}
	}
	return out
}
