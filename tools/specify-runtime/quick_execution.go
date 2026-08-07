package main

import (
	"encoding/json"
	"fmt"
	"os"
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
			"task":             task,
			"work_item_id":     itemID,
			"confirmation":     doc,
			"packet":           packet,
			"packet_path":      quickPacketRelPath(workspace, itemID),
			"pulse":            renderQuickPulseView(doc),
			"ready_item_ids":   readyQuickItemIDs(doc),
			"blocked_item_ids": blockedQuickItemIDs(doc),
			"requires_worker":  true,
			"next_action":      "spawn subagent for write_scope, then result submit --lane-id " + itemID + ", then item-accept",
		}
		return env, nil
	case "allow-inline":
		if strings.TrimSpace(itemID) == "" {
			return Envelope{}, fmt.Errorf("allow-inline requires --item Qn")
		}
		reason := strings.TrimSpace(optionValue(args, "--reason", ""))
		if reason == "" {
			return Envelope{}, fmt.Errorf("allow-inline requires --reason (spawn_failed / tool_missing / subagent-blocked); docs-only is invalid")
		}
		doc, err := service.allowInlineWorkItem(workspacePath, workspace, itemID, reason)
		if err != nil {
			return Envelope{}, err
		}
		env := NewEnvelope("ok", "leader-inline approved for work item")
		env.Data = map[string]any{
			"task":             task,
			"work_item_id":     itemID,
			"confirmation":     doc,
			"pulse":            renderQuickPulseView(doc),
			"requires_worker":  false,
			"inline_reason":    reason,
			"ready_item_ids":   readyQuickItemIDs(doc),
			"blocked_item_ids": blockedQuickItemIDs(doc),
		}
		return env, nil
	case "item-accept":
		if strings.TrimSpace(itemID) == "" {
			return Envelope{}, fmt.Errorf("item-accept requires --item Qn")
		}
		evidence := optionValues(args, "--evidence")
		if len(evidence) == 0 {
			if extra := strings.TrimSpace(positionalArg(args, 3, "")); extra != "" {
				evidence = []string{extra}
			}
		}
		if len(evidence) == 0 {
			return Envelope{}, fmt.Errorf("item-accept requires at least one --evidence value")
		}
		doc, proof, err := service.acceptWorkItem(workspacePath, workspace, itemID, evidence, args)
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
			"worker_proof":     proof,
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
			"worker_gates":     quickWorkerGateSummary(doc),
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
		// Re-assert worker lock if still open.
		doc = ensureQuickExecutionRows(doc)
		setQuickItemWorkerLock(doc, itemID, true)
		packet, _, _, err := compileQuickWorkerPacket(doc, itemID)
		if err != nil {
			return nil, nil, err
		}
		_ = service.persistConfirmation(workspacePath, doc)
		_ = service.projectConfirmationIntoStatus(workspacePath, doc)
		return doc, packet, nil
	}
	unmet := unmetQuickDeps(item.DependsOn, statusByID)
	if len(unmet) > 0 {
		return nil, nil, fmt.Errorf("work item %s cannot start; waiting for accepted prerequisites: %s", itemID, strings.Join(unmet, ", "))
	}

	doc = ensureQuickExecutionRows(doc)
	setQuickItemStatus(doc, itemID, "in_progress", nil)
	setQuickItemWorkerLock(doc, itemID, true)
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

func (service quickService) allowInlineWorkItem(workspacePath, workspace, itemID, reason string) (*quickConfirmationDoc, error) {
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
	if forbidden, keyword := quickForbiddenInlineReason(reason); forbidden {
		return nil, fmt.Errorf("worker_result_required: leader-inline reason %q is not allowed (matched %q); only spawn/tool/subagent-blocked failures may use allow-inline", reason, keyword)
	}
	statusByID := quickStatusMap(doc)
	st := strings.ToLower(statusByID[itemID].Status)
	if st == "accepted" {
		return nil, fmt.Errorf("work item %s is already accepted", itemID)
	}
	if st != "in_progress" {
		return nil, fmt.Errorf("allow-inline requires item %s to be in_progress (run item-start first)", itemID)
	}

	doc = ensureQuickExecutionRows(doc)
	for i, row := range doc.Execution.WorkItemStatus {
		if row.WorkItemID != itemID {
			continue
		}
		doc.Execution.WorkItemStatus[i].RequiresWorker = false
		doc.Execution.WorkItemStatus[i].InlineApproved = true
		doc.Execution.WorkItemStatus[i].InlineReason = reason
		break
	}
	doc.Execution.BlockedDispatch = &quickBlockedDispatch{
		Status:         "recorded-fallback",
		Reason:         reason,
		AttemptedShape: "one-subagent",
		ChosenShape:    "leader-inline",
		ItemID:         itemID,
		ApprovedAt:     nowUTCString(),
	}
	doc.UpdatedAt = nowUTCString()
	if err := service.persistConfirmation(workspacePath, doc); err != nil {
		return nil, err
	}
	if err := service.projectConfirmationIntoStatus(workspacePath, doc); err != nil {
		return nil, err
	}
	return doc, nil
}

type quickWorkerAcceptProof struct {
	Mode         string   `json:"mode"` // worker | leader-inline
	LaneID       string   `json:"lane_id,omitempty"`
	ResultPath   string   `json:"result_path,omitempty"`
	ResultStatus string   `json:"result_status,omitempty"`
	ChangedFiles []string `json:"changed_files,omitempty"`
	InlineReason string   `json:"inline_reason,omitempty"`
}

func (service quickService) acceptWorkItem(workspacePath, workspace, itemID string, evidence []string, args []string) (*quickConfirmationDoc, *quickWorkerAcceptProof, error) {
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
	cleaned := []string{}
	for _, row := range evidence {
		row = strings.TrimSpace(row)
		if row != "" {
			cleaned = append(cleaned, row)
		}
	}
	if len(cleaned) == 0 {
		return nil, nil, fmt.Errorf("acceptance evidence is required for %s", itemID)
	}
	statusByID := quickStatusMap(doc)
	unmet := unmetQuickDeps(item.DependsOn, statusByID)
	if len(unmet) > 0 && strings.ToLower(statusByID[itemID].Status) != "accepted" {
		return nil, nil, fmt.Errorf("work item %s cannot be accepted; prerequisites not accepted: %s", itemID, strings.Join(unmet, ", "))
	}

	// Idempotent re-accept returns stored proof.
	if strings.ToLower(statusByID[itemID].Status) == "accepted" {
		row := statusByID[itemID]
		proof := &quickWorkerAcceptProof{
			Mode:         firstNonEmpty(row.ExecutionMode, "worker"),
			LaneID:       row.WorkerLaneID,
			ResultPath:   row.WorkerResultRef,
			InlineReason: row.InlineReason,
			ResultStatus: "success",
		}
		return doc, proof, nil
	}

	// One-shot --allow-inline on accept (also records approval if not already done).
	if hasFlag(args, "--allow-inline") {
		reason := strings.TrimSpace(optionValue(args, "--reason", ""))
		if reason == "" {
			reason = statusByID[itemID].InlineReason
		}
		if reason == "" {
			return nil, nil, fmt.Errorf("worker_result_required: item-accept --allow-inline requires --reason, or prior quick allow-inline")
		}
		if _, err := service.allowInlineWorkItem(workspacePath, workspace, itemID, reason); err != nil {
			return nil, nil, err
		}
		// Reload after allow-inline mutation.
		doc, err = service.loadConfirmation(workspacePath)
		if err != nil {
			return nil, nil, err
		}
		statusByID = quickStatusMap(doc)
	}

	proof, err := requireQuickWorkerAcceptProof(workspacePath, workspace, itemID, item, statusByID[itemID])
	if err != nil {
		return nil, nil, err
	}

	doc = ensureQuickExecutionRows(doc)
	setQuickItemStatus(doc, itemID, "accepted", cleaned)
	setQuickItemWorkerProof(doc, itemID, proof)
	active := []string{}
	for _, id := range doc.Execution.ActiveItemIDs {
		if id != itemID {
			active = append(active, id)
		}
	}
	doc.Execution.ActiveItemIDs = active
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
		return nil, nil, err
	}
	if err := service.projectConfirmationIntoStatus(workspacePath, doc); err != nil {
		return nil, nil, err
	}
	return doc, proof, nil
}

func setQuickItemWorkerLock(doc *quickConfirmationDoc, itemID string, requiresWorker bool) {
	if doc == nil {
		return
	}
	for i, row := range doc.Execution.WorkItemStatus {
		if row.WorkItemID != itemID {
			continue
		}
		doc.Execution.WorkItemStatus[i].RequiresWorker = requiresWorker
		if requiresWorker {
			// Fresh lock clears prior result binding until submit/accept.
			if doc.Execution.WorkItemStatus[i].Status != "accepted" {
				doc.Execution.WorkItemStatus[i].WorkerResultID = ""
				// Keep InlineApproved if already granted for this in_progress cycle.
			}
		}
		return
	}
}

func setQuickItemWorkerProof(doc *quickConfirmationDoc, itemID string, proof *quickWorkerAcceptProof) {
	if doc == nil || proof == nil {
		return
	}
	for i, row := range doc.Execution.WorkItemStatus {
		if row.WorkItemID != itemID {
			continue
		}
		doc.Execution.WorkItemStatus[i].ExecutionMode = proof.Mode
		doc.Execution.WorkItemStatus[i].RequiresWorker = false
		doc.Execution.WorkItemStatus[i].WorkerResultRef = proof.ResultPath
		doc.Execution.WorkItemStatus[i].WorkerLaneID = proof.LaneID
		doc.Execution.WorkItemStatus[i].WorkerResultID = firstNonEmpty(proof.LaneID, proof.ResultPath)
		doc.Execution.WorkItemStatus[i].InlineReason = proof.InlineReason
		if proof.Mode == "leader-inline" {
			doc.Execution.WorkItemStatus[i].InlineApproved = true
		}
		return
	}
}

func requireQuickWorkerAcceptProof(workspacePath, workspace, itemID string, item quickConfirmationItem, row quickWorkItemStatus) (*quickWorkerAcceptProof, error) {
	// Audited leader-inline path.
	if row.InlineApproved && !row.RequiresWorker && strings.TrimSpace(row.InlineReason) != "" {
		if forbidden, keyword := quickForbiddenInlineReason(row.InlineReason); forbidden {
			return nil, fmt.Errorf("worker_result_required: leader-inline reason %q is not allowed (matched %q)", row.InlineReason, keyword)
		}
		return &quickWorkerAcceptProof{
			Mode:         "leader-inline",
			InlineReason: row.InlineReason,
		}, nil
	}

	result, absPath, laneID, err := findQuickWorkerResult(workspacePath, itemID)
	if err != nil {
		return nil, fmt.Errorf("worker_result_required: %w; submit with `specify-runtime result submit --command quick --workspace %s --lane-id %s --result-json '...'` (status success/DONE/DONE_WITH_CONCERNS), or run `quick allow-inline --item %s --reason \"spawn_failed: ...\"` first", err, filepath.ToSlash(filepath.Join(".planning", "quick", workspace)), itemID, itemID)
	}
	status := strings.ToLower(strings.TrimSpace(asString(result["status"])))
	if status != "success" {
		return nil, fmt.Errorf("worker_result_required: worker result for %s has status %q (need success, DONE, or DONE_WITH_CONCERNS)", itemID, firstNonEmpty(asString(result["reported_status"]), status))
	}
	changed := asStringList(result["changed_files"])
	if err := validateQuickChangedFilesInScope(changed, item.WriteScope); err != nil {
		return nil, fmt.Errorf("worker_result_required: %w", err)
	}
	rel := filepath.ToSlash(filepath.Join(".planning", "quick", workspace, "worker-results", laneID+".json"))
	if relFromWS, err := filepath.Rel(workspacePath, absPath); err == nil {
		rel = filepath.ToSlash(filepath.Join(".planning", "quick", workspace, relFromWS))
	}
	return &quickWorkerAcceptProof{
		Mode:         "worker",
		LaneID:       laneID,
		ResultPath:   rel,
		ResultStatus: status,
		ChangedFiles: changed,
	}, nil
}

func quickForbiddenInlineReason(reason string) (bool, string) {
	lower := strings.ToLower(strings.TrimSpace(reason))
	forbidden := []string{
		"docs-only", "docs only", "documentation only", "doc only",
		"small edit", "small change", "few files", "file few", "few file",
		"serial only", "serial dependency", "serial deps",
		"save time", "saves time", "faster", "quicker", "time-saving", "time saving",
		"trivial", "simple docs", "readme only", "skill only",
		"leader knows", "i already", "already edited", "already wrote",
	}
	for _, keyword := range forbidden {
		if strings.Contains(lower, keyword) {
			return true, keyword
		}
	}
	return false, ""
}

func findQuickWorkerResult(workspacePath, itemID string) (map[string]any, string, string, error) {
	itemID = strings.TrimSpace(itemID)
	if itemID == "" {
		return nil, "", "", fmt.Errorf("work item id is required")
	}
	dir := filepath.Join(workspacePath, "worker-results")
	entries, err := os.ReadDir(dir)
	if err != nil {
		if os.IsNotExist(err) {
			return nil, "", "", fmt.Errorf("no worker-results directory for %s", itemID)
		}
		return nil, "", "", fmt.Errorf("read worker-results: %w", err)
	}

	type candidate struct {
		laneID string
		path   string
		rank   int
	}
	var candidates []candidate
	for _, entry := range entries {
		if entry.IsDir() || !strings.HasSuffix(strings.ToLower(entry.Name()), ".json") {
			continue
		}
		laneID := strings.TrimSuffix(entry.Name(), filepath.Ext(entry.Name()))
		rank := quickLaneMatchRank(laneID, itemID)
		if rank < 0 {
			rank = 100
		}
		candidates = append(candidates, candidate{
			laneID: laneID,
			path:   filepath.Join(dir, entry.Name()),
			rank:   rank,
		})
	}
	if len(candidates) == 0 {
		return nil, "", "", fmt.Errorf("no worker result files for %s", itemID)
	}
	sort.SliceStable(candidates, func(i, j int) bool {
		if candidates[i].rank != candidates[j].rank {
			return candidates[i].rank < candidates[j].rank
		}
		return candidates[i].laneID < candidates[j].laneID
	})

	var lastErr error
	for _, cand := range candidates {
		raw, err := os.ReadFile(cand.path)
		if err != nil {
			lastErr = err
			continue
		}
		normalized, err := normalizeWorkerTaskResult(raw)
		if err != nil {
			var payload map[string]any
			if jsonErr := json.Unmarshal(raw, &payload); jsonErr != nil {
				lastErr = err
				continue
			}
			normalized = payload
			if status := strings.ToLower(strings.TrimSpace(asString(pick(payload, "status", "reported_status")))); status != "" {
				if alias, ok := resultStatusAliases[status]; ok {
					normalized["status"] = alias
				} else {
					normalized["status"] = status
				}
			}
		}
		payloadItem := firstNonEmpty(
			asString(pick(normalized, "work_item_id", "workItemId")),
			asString(pick(normalized, "task_id", "taskId")),
		)
		laneMatch := quickLaneMatchRank(cand.laneID, itemID) >= 0
		payloadMatch := payloadItem == itemID || strings.EqualFold(payloadItem, itemID)
		if !laneMatch && !payloadMatch {
			continue
		}
		return normalized, cand.path, cand.laneID, nil
	}
	if lastErr != nil {
		return nil, "", "", fmt.Errorf("no usable worker result for %s: %v", itemID, lastErr)
	}
	return nil, "", "", fmt.Errorf("no worker result with lane-id/task_id matching %s", itemID)
}

func quickLaneMatchRank(laneID, itemID string) int {
	laneID = strings.TrimSpace(laneID)
	itemID = strings.TrimSpace(itemID)
	if laneID == "" || itemID == "" {
		return -1
	}
	if strings.EqualFold(laneID, itemID) {
		return 0
	}
	upperLane := strings.ToUpper(laneID)
	upperItem := strings.ToUpper(itemID)
	if strings.HasPrefix(upperLane, upperItem+"-") || strings.HasPrefix(upperLane, upperItem+"_") {
		return 1
	}
	return -1
}

func validateQuickChangedFilesInScope(changedFiles, writeScope []string) error {
	if len(writeScope) == 0 || len(changedFiles) == 0 {
		return nil
	}
	outOfScope := []string{}
	for _, file := range changedFiles {
		file = filepath.ToSlash(strings.TrimSpace(file))
		if file == "" {
			continue
		}
		if !quickPathInWriteScope(file, writeScope) {
			outOfScope = append(outOfScope, file)
		}
	}
	if len(outOfScope) > 0 {
		return fmt.Errorf("changed_files outside packet write_scope: %s", strings.Join(outOfScope, ", "))
	}
	return nil
}

func quickPathInWriteScope(path string, writeScope []string) bool {
	path = filepath.ToSlash(strings.TrimPrefix(path, "./"))
	for _, scope := range writeScope {
		scope = filepath.ToSlash(strings.TrimSpace(strings.TrimPrefix(scope, "./")))
		if scope == "" {
			continue
		}
		if path == scope {
			return true
		}
		if strings.HasSuffix(scope, "/") {
			if strings.HasPrefix(path, scope) {
				return true
			}
			continue
		}
		if strings.HasPrefix(path, scope+"/") {
			return true
		}
		if strings.HasSuffix(scope, "/**") || strings.HasSuffix(scope, "/*") {
			prefix := strings.TrimSuffix(strings.TrimSuffix(scope, "/**"), "/*")
			prefix = strings.TrimSuffix(prefix, "/")
			if path == prefix || strings.HasPrefix(path, prefix+"/") {
				return true
			}
		}
	}
	return false
}

func quickWorkerGateSummary(doc *quickConfirmationDoc) []map[string]any {
	if doc == nil {
		return nil
	}
	out := []map[string]any{}
	statusByID := quickStatusMap(doc)
	for _, item := range doc.Decision.Items {
		row := statusByID[item.ID]
		out = append(out, map[string]any{
			"work_item_id":     item.ID,
			"status":           firstNonEmpty(row.Status, "pending"),
			"requires_worker":  row.RequiresWorker,
			"inline_approved":  row.InlineApproved,
			"execution_mode":   row.ExecutionMode,
			"worker_result_id": row.WorkerResultID,
			"worker_lane_id":   row.WorkerLaneID,
		})
	}
	return out
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
			"work_item_id":        dep,
			"status":              firstNonEmpty(row.Status, "pending"),
			"acceptance_evidence": append([]string{}, row.AcceptanceEvidence...),
			"accepted":            strings.ToLower(row.Status) == "accepted",
		})
	}

	packet := map[string]any{
		"schema":              quickWorkerPacketSchema,
		"work_item_id":        item.ID,
		"deliverable":         item.Deliverable,
		"depends_on":          append([]string{}, item.DependsOn...),
		"acceptance":          item.Acceptance,
		"write_scope":         append([]string{}, item.WriteScope...),
		"goal":                doc.Decision.Goal,
		"user_visible_result": doc.Decision.UserVisibleResult,
		"scope": map[string]any{
			"include": append([]string{}, doc.Decision.Scope.Include...),
			"exclude": append([]string{}, doc.Decision.Scope.Exclude...),
			"defer":   append([]string{}, doc.Decision.Scope.Defer...),
		},
		"confirmation_digest":    doc.ConfirmationDigest,
		"confirmation_state":     doc.ConfirmationState,
		"prerequisite_status":    prereq,
		"required_acceptance":    item.Acceptance,
		"completion_evidence":    append([]string{}, doc.Decision.CompletionEvidence...),
		"reconfirmation_trigger": doc.Decision.ReconfirmationTrigger,
		"ui_confirmation":        doc.Decision.UIConfirmation,
		"ready":                  len(blockers) == 0,
		"blockers":               blockers,
		"requires_worker":        true,
		"worker_contract": map[string]any{
			"complete_one_work_item_only":     true,
			"must_not_start_if_deps_open":     true,
			"must_return_acceptance_evidence": true,
			"must_result_submit_before_accept": true,
			"status_md_leader_owned":          true,
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
	// Every accepted item must have an audited execution mode (worker result or allow-inline).
	statusByID := quickStatusMap(doc)
	missing := []string{}
	for _, item := range doc.Decision.Items {
		row := statusByID[item.ID]
		mode := strings.ToLower(strings.TrimSpace(row.ExecutionMode))
		switch mode {
		case "worker":
			if strings.TrimSpace(row.WorkerResultRef) == "" && strings.TrimSpace(row.WorkerLaneID) == "" {
				missing = append(missing, item.ID+"(worker_result_missing)")
			}
		case "leader-inline":
			if strings.TrimSpace(row.InlineReason) == "" {
				missing = append(missing, item.ID+"(inline_reason_missing)")
			}
		default:
			// Pre-gate legacy accepts may lack mode; refuse close to force re-accept under new gate.
			missing = append(missing, item.ID+"(execution_mode_missing)")
		}
	}
	if len(missing) > 0 {
		return fmt.Errorf("cannot close as resolved: work items lack worker/inline proof: %s; re-accept with result submit or allow-inline", strings.Join(missing, ", "))
	}
	return nil
}
