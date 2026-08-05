package main

import (
	"fmt"
	"path/filepath"
	"sort"
	"strings"
)

const quickWorkerPacketSchema = "quick-worker-packet-v1"

func (service quickService) runExecution(mode, quickID string, args []string) (Envelope, error) {
	root, err := service.root()
	if err != nil {
		return Envelope{}, err
	}
	tasks, err := service.scan(root)
	if err != nil {
		return Envelope{}, err
	}
	task, err := matchQuickTask(tasks, quickID)
	if err != nil {
		return Envelope{}, err
	}
	workspacePath := stringValue(task["workspace_path"])
	workspace := stringValue(task["workspace"])
	itemID := firstNonEmpty(optionValue(args, "--item", ""), positionalArg(args, 2, ""))

	switch strings.ToLower(strings.TrimSpace(mode)) {
	case "item-start":
		if strings.TrimSpace(itemID) == "" {
			return Envelope{}, fmt.Errorf("item-start requires --item Qn")
		}
		doc, packet, err := service.startWorkItem(workspacePath, workspace, itemID)
		if err != nil {
			return Envelope{}, err
		}
		env := NewEnvelope("ok", "quick work item started")
		env.Data = map[string]any{
			"task":               task,
			"work_item_id":       itemID,
			"confirmation":       doc,
			"packet":             packet,
			"packet_path":        quickPacketRelPath(workspace, itemID),
			"pulse":              renderQuickPulseView(doc),
			"ready_item_ids":     readyQuickItemIDs(doc),
			"blocked_item_ids":   blockedQuickItemIDs(doc),
		}
		return env, nil
	case "item-accept":
		if strings.TrimSpace(itemID) == "" {
			return Envelope{}, fmt.Errorf("item-accept requires --item Qn")
		}
		evidence := optionValues(args, "--evidence")
		if len(evidence) == 0 {
			// allow a single positional evidence string after the item id
			if extra := strings.TrimSpace(positionalArg(args, 3, "")); extra != "" {
				evidence = []string{extra}
			}
		}
		if len(evidence) == 0 {
			return Envelope{}, fmt.Errorf("item-accept requires at least one --evidence value")
		}
		doc, err := service.acceptWorkItem(workspacePath, workspace, itemID, evidence)
		if err != nil {
			return Envelope{}, err
		}
		env := NewEnvelope("ok", "quick work item accepted")
		env.Data = map[string]any{
			"task":             task,
			"work_item_id":     itemID,
			"confirmation":     doc,
			"pulse":            renderQuickPulseView(doc),
			"ready_item_ids":   readyQuickItemIDs(doc),
			"blocked_item_ids": blockedQuickItemIDs(doc),
			"all_accepted":     allQuickItemsAccepted(doc),
		}
		return env, nil
	case "packet-compile":
		if strings.TrimSpace(itemID) == "" {
			return Envelope{}, fmt.Errorf("packet-compile requires --item Qn")
		}
		doc, err := service.loadConfirmation(workspacePath)
		if err != nil {
			return Envelope{}, err
		}
		if err := requireQuickCheckpointExecutable(doc); err != nil {
			return Envelope{}, err
		}
		packet, ready, blockers, err := compileQuickWorkerPacket(doc, itemID)
		if err != nil {
			return Envelope{}, err
		}
		if !ready && !hasFlag(args, "--allow-blocked") {
			return Envelope{}, fmt.Errorf("work item %s is not ready to dispatch: %s", itemID, strings.Join(blockers, "; "))
		}
		path := filepath.Join(workspacePath, "packets", itemID+".json")
		if err := writeScriptJSONFile(path, packet); err != nil {
			return Envelope{}, err
		}
		env := NewEnvelope("ok", "quick worker packet compiled")
		env.Data = map[string]any{
			"task":         task,
			"work_item_id": itemID,
			"ready":        ready,
			"blockers":     blockers,
			"packet":       packet,
			"packet_path":  quickPacketRelPath(workspace, itemID),
		}
		return env, nil
	case "item-status":
		doc, err := service.loadConfirmation(workspacePath)
		if err != nil {
			return Envelope{}, err
		}
		env := NewEnvelope("ok", "quick work item status")
		env.Data = map[string]any{
			"task":             task,
			"confirmation":     doc,
			"pulse":            renderQuickPulseView(doc),
			"ready_item_ids":   readyQuickItemIDs(doc),
			"blocked_item_ids": blockedQuickItemIDs(doc),
			"active_item_ids":  append([]string{}, doc.Execution.ActiveItemIDs...),
			"all_accepted":     allQuickItemsAccepted(doc),
		}
		return env, nil
	default:
		return Envelope{}, fmt.Errorf("unknown execution mode: %s", mode)
	}
}

func quickPacketRelPath(workspace, itemID string) string {
	return filepath.ToSlash(filepath.Join(".planning", "quick", workspace, "packets", itemID+".json"))
}

func requireQuickCheckpointExecutable(doc *quickConfirmationDoc) error {
	if doc == nil {
		return fmt.Errorf("quick confirmation not found; run checkpoint-stage first")
	}
	state := strings.ToLower(strings.TrimSpace(doc.ConfirmationState))
	if state != "confirmed" && state != "inherited" {
		return fmt.Errorf("checkpoint is not confirmed (state=%s); confirm or inherit before execution", doc.ConfirmationState)
	}
	return nil
}

func (service quickService) startWorkItem(workspacePath, workspace, itemID string) (*quickConfirmationDoc, map[string]any, error) {
	doc, err := service.loadConfirmation(workspacePath)
	if err != nil {
		return nil, nil, err
	}
	if err := requireQuickCheckpointExecutable(doc); err != nil {
		return nil, nil, err
	}
	item, ok := findQuickItem(doc, itemID)
	if !ok {
		return nil, nil, fmt.Errorf("unknown work item %s", itemID)
	}
	statusByID := quickStatusMap(doc)
	current := strings.ToLower(statusByID[itemID].Status)
	if current == "accepted" {
		return nil, nil, fmt.Errorf("work item %s is already accepted", itemID)
	}
	if current == "in_progress" {
		packet, _, _, err := compileQuickWorkerPacket(doc, itemID)
		if err != nil {
			return nil, nil, err
		}
		return doc, packet, nil
	}
	unmet := unmetQuickDeps(item.DependsOn, statusByID)
	if len(unmet) > 0 {
		return nil, nil, fmt.Errorf("work item %s cannot start; waiting for accepted prerequisites: %s", itemID, strings.Join(unmet, ", "))
	}

	// Mark ready dependents blocked when another active item has write conflicts in the same wave? optional later.
	doc = ensureQuickExecutionRows(doc)
	setQuickItemStatus(doc, itemID, "in_progress", nil)
	if !quickContains(doc.Execution.ActiveItemIDs, itemID) {
		doc.Execution.ActiveItemIDs = append(doc.Execution.ActiveItemIDs, itemID)
		sort.Strings(doc.Execution.ActiveItemIDs)
	}
	doc.Execution.JoinPoint = deriveQuickJoinPoint(doc)
	doc.Execution.Blockers = nil
	doc.UpdatedAt = nowUTCString()

	packet, ready, blockers, err := compileQuickWorkerPacket(doc, itemID)
	if err != nil {
		return nil, nil, err
	}
	if !ready {
		return nil, nil, fmt.Errorf("work item %s is not ready: %s", itemID, strings.Join(blockers, "; "))
	}
	path := filepath.Join(workspacePath, "packets", itemID+".json")
	if err := writeScriptJSONFile(path, packet); err != nil {
		return nil, nil, err
	}
	if err := service.persistConfirmation(workspacePath, doc); err != nil {
		return nil, nil, err
	}
	if err := service.projectConfirmationIntoStatus(workspacePath, doc); err != nil {
		return nil, nil, err
	}
	return doc, packet, nil
}

func (service quickService) acceptWorkItem(workspacePath, workspace, itemID string, evidence []string) (*quickConfirmationDoc, error) {
	doc, err := service.loadConfirmation(workspacePath)
	if err != nil {
		return nil, err
	}
	if err := requireQuickCheckpointExecutable(doc); err != nil {
		return nil, err
	}
	if _, ok := findQuickItem(doc, itemID); !ok {
		return nil, fmt.Errorf("unknown work item %s", itemID)
	}
	cleaned := []string{}
	for _, row := range evidence {
		row = strings.TrimSpace(row)
		if row != "" {
			cleaned = append(cleaned, row)
		}
	}
	if len(cleaned) == 0 {
		return nil, fmt.Errorf("acceptance evidence is required for %s", itemID)
	}
	statusByID := quickStatusMap(doc)
	item, _ := findQuickItem(doc, itemID)
	unmet := unmetQuickDeps(item.DependsOn, statusByID)
	if len(unmet) > 0 && strings.ToLower(statusByID[itemID].Status) != "accepted" {
		return nil, fmt.Errorf("work item %s cannot be accepted; prerequisites not accepted: %s", itemID, strings.Join(unmet, ", "))
	}

	doc = ensureQuickExecutionRows(doc)
	setQuickItemStatus(doc, itemID, "accepted", cleaned)
	active := []string{}
	for _, id := range doc.Execution.ActiveItemIDs {
		if id != itemID {
			active = append(active, id)
		}
	}
	doc.Execution.ActiveItemIDs = active
	// Promote newly unblocked items to ready in the projection.
	statusByID = quickStatusMap(doc)
	for _, candidate := range doc.Decision.Items {
		st := strings.ToLower(statusByID[candidate.ID].Status)
		if st == "accepted" || st == "in_progress" || st == "blocked" {
			continue
		}
		if len(unmetQuickDeps(candidate.DependsOn, statusByID)) == 0 {
			setQuickItemStatus(doc, candidate.ID, "ready", statusByID[candidate.ID].AcceptanceEvidence)
		}
	}
	doc.Execution.JoinPoint = deriveQuickJoinPoint(doc)
	doc.UpdatedAt = nowUTCString()
	if err := service.persistConfirmation(workspacePath, doc); err != nil {
		return nil, err
	}
	if err := service.projectConfirmationIntoStatus(workspacePath, doc); err != nil {
		return nil, err
	}
	return doc, nil
}

func compileQuickWorkerPacket(doc *quickConfirmationDoc, itemID string) (map[string]any, bool, []string, error) {
	item, ok := findQuickItem(doc, itemID)
	if !ok {
		return nil, false, nil, fmt.Errorf("unknown work item %s", itemID)
	}
	statusByID := quickStatusMap(doc)
	blockers := []string{}
	if err := requireQuickCheckpointExecutable(doc); err != nil {
		blockers = append(blockers, err.Error())
	}
	unmet := unmetQuickDeps(item.DependsOn, statusByID)
	if len(unmet) > 0 {
		blockers = append(blockers, fmt.Sprintf("waiting for accepted prerequisites: %s", strings.Join(unmet, ", ")))
	}
	if strings.ToLower(statusByID[itemID].Status) == "accepted" {
		blockers = append(blockers, "work item already accepted")
	}

	prereq := []map[string]any{}
	for _, dep := range item.DependsOn {
		row := statusByID[dep]
		prereq = append(prereq, map[string]any{
			"work_item_id":         dep,
			"status":               firstNonEmpty(row.Status, "pending"),
			"acceptance_evidence":  append([]string{}, row.AcceptanceEvidence...),
			"accepted":             strings.ToLower(row.Status) == "accepted",
		})
	}

	packet := map[string]any{
		"schema":               quickWorkerPacketSchema,
		"work_item_id":         item.ID,
		"deliverable":          item.Deliverable,
		"depends_on":           append([]string{}, item.DependsOn...),
		"acceptance":           item.Acceptance,
		"write_scope":          append([]string{}, item.WriteScope...),
		"goal":                 doc.Decision.Goal,
		"user_visible_result":  doc.Decision.UserVisibleResult,
		"scope": map[string]any{
			"include": append([]string{}, doc.Decision.Scope.Include...),
			"exclude": append([]string{}, doc.Decision.Scope.Exclude...),
			"defer":   append([]string{}, doc.Decision.Scope.Defer...),
		},
		"confirmation_digest":     doc.ConfirmationDigest,
		"confirmation_state":      doc.ConfirmationState,
		"prerequisite_status":     prereq,
		"required_acceptance":     item.Acceptance,
		"completion_evidence":     append([]string{}, doc.Decision.CompletionEvidence...),
		"reconfirmation_trigger":  doc.Decision.ReconfirmationTrigger,
		"ui_confirmation":         doc.Decision.UIConfirmation,
		"ready":                   len(blockers) == 0,
		"blockers":                blockers,
		"worker_contract": map[string]any{
			"complete_one_work_item_only": true,
			"must_not_start_if_deps_open": true,
			"must_return_acceptance_evidence": true,
			"status_md_leader_owned":      true,
		},
	}
	return packet, len(blockers) == 0, blockers, nil
}

func findQuickItem(doc *quickConfirmationDoc, itemID string) (quickConfirmationItem, bool) {
	for _, item := range doc.Decision.Items {
		if item.ID == itemID {
			return item, true
		}
	}
	return quickConfirmationItem{}, false
}

func quickStatusMap(doc *quickConfirmationDoc) map[string]quickWorkItemStatus {
	out := map[string]quickWorkItemStatus{}
	for _, item := range doc.Decision.Items {
		out[item.ID] = quickWorkItemStatus{WorkItemID: item.ID, Status: "pending"}
	}
	for _, row := range doc.Execution.WorkItemStatus {
		out[row.WorkItemID] = row
	}
	return out
}

func ensureQuickExecutionRows(doc *quickConfirmationDoc) *quickConfirmationDoc {
	if doc.Execution.WorkItemStatus == nil {
		doc.Execution.WorkItemStatus = []quickWorkItemStatus{}
	}
	seen := map[string]bool{}
	for _, row := range doc.Execution.WorkItemStatus {
		seen[row.WorkItemID] = true
	}
	for _, item := range doc.Decision.Items {
		if !seen[item.ID] {
			doc.Execution.WorkItemStatus = append(doc.Execution.WorkItemStatus, quickWorkItemStatus{
				WorkItemID: item.ID,
				Status:     "pending",
			})
		}
	}
	return doc
}

func setQuickItemStatus(doc *quickConfirmationDoc, itemID, status string, evidence []string) {
	found := false
	for i, row := range doc.Execution.WorkItemStatus {
		if row.WorkItemID == itemID {
			doc.Execution.WorkItemStatus[i].Status = status
			if evidence != nil {
				doc.Execution.WorkItemStatus[i].AcceptanceEvidence = append([]string{}, evidence...)
			}
			found = true
			break
		}
	}
	if !found {
		doc.Execution.WorkItemStatus = append(doc.Execution.WorkItemStatus, quickWorkItemStatus{
			WorkItemID:         itemID,
			Status:             status,
			AcceptanceEvidence: append([]string{}, evidence...),
		})
	}
}

func readyQuickItemIDs(doc *quickConfirmationDoc) []string {
	statusByID := quickStatusMap(doc)
	ready := []string{}
	for _, item := range doc.Decision.Items {
		st := strings.ToLower(statusByID[item.ID].Status)
		if st == "accepted" || st == "in_progress" {
			continue
		}
		if len(unmetQuickDeps(item.DependsOn, statusByID)) == 0 {
			ready = append(ready, item.ID)
		}
	}
	return ready
}

func blockedQuickItemIDs(doc *quickConfirmationDoc) []string {
	statusByID := quickStatusMap(doc)
	blocked := []string{}
	for _, item := range doc.Decision.Items {
		st := strings.ToLower(statusByID[item.ID].Status)
		if st == "accepted" || st == "in_progress" {
			continue
		}
		if len(unmetQuickDeps(item.DependsOn, statusByID)) > 0 {
			blocked = append(blocked, item.ID)
		}
	}
	return blocked
}

func allQuickItemsAccepted(doc *quickConfirmationDoc) bool {
	if doc == nil || len(doc.Decision.Items) == 0 {
		return false
	}
	statusByID := quickStatusMap(doc)
	for _, item := range doc.Decision.Items {
		if strings.ToLower(statusByID[item.ID].Status) != "accepted" {
			return false
		}
	}
	return true
}

func deriveQuickJoinPoint(doc *quickConfirmationDoc) string {
	statusByID := quickStatusMap(doc)
	for _, join := range doc.Delivery.JoinPoints {
		ready := true
		for _, id := range join.After {
			if strings.ToLower(statusByID[id].Status) != "accepted" {
				ready = false
				break
			}
		}
		if !ready {
			return fmt.Sprintf("%s 验收通过后启动 %s", strings.Join(join.After, "、"), join.Starts)
		}
	}
	if allQuickItemsAccepted(doc) {
		return "全部 Q 项已验收；可进入整体完成证据与 close"
	}
	ready := readyQuickItemIDs(doc)
	if len(ready) > 0 {
		return fmt.Sprintf("可启动：%s", strings.Join(ready, "、"))
	}
	return ""
}

func (service quickService) validateCloseAgainstConfirmation(workspacePath, statusValue string) error {
	if statusValue != "resolved" {
		return nil
	}
	doc, err := service.loadConfirmation(workspacePath)
	if err != nil {
		// Legacy workspaces without confirmation.json may still close.
		if strings.Contains(err.Error(), "not found") {
			return nil
		}
		return err
	}
	if !allQuickItemsAccepted(doc) {
		pending := []string{}
		statusByID := quickStatusMap(doc)
		for _, item := range doc.Decision.Items {
			if strings.ToLower(statusByID[item.ID].Status) != "accepted" {
				pending = append(pending, item.ID)
			}
		}
		return fmt.Errorf("cannot close as resolved until all work items are accepted; pending: %s", strings.Join(pending, ", "))
	}
	return nil
}
