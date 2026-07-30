package main

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"regexp"
	"strings"
)

var implementTaskTerminalStatuses = map[string]bool{"accepted": true, "deferred": true}

func runImplementTaskNext(args []string) (map[string]any, error) {
	root, feature, err := taskControlFeature(args)
	if err != nil {
		return nil, err
	}
	index, err := loadReadyImplementTaskIndex(root, feature)
	if err != nil {
		return nil, err
	}
	next := nextImplementTaskFromIndex(index)
	return map[string]any{"status": "ok", "task": next}, nil
}

func runImplementPacketCompile(args []string) (map[string]any, error) {
	root, feature, err := taskControlFeature(args)
	if err != nil {
		return nil, err
	}
	taskID, err := normalizeTaskControlID(optionValue(args, "--task-id", ""))
	if err != nil {
		return nil, err
	}
	index, err := loadReadyImplementTaskIndex(root, feature)
	if err != nil {
		return nil, err
	}
	position, task, err := findImplementTask(index, taskID)
	if err != nil {
		return nil, err
	}
	template, err := readImplementJSONMap(filepath.Join(root, ".specify", "templates", "task-packet-template.json"))
	if err != nil {
		return nil, fmt.Errorf("task-packet template is invalid or missing: %w", err)
	}
	packet := cloneJSONMap(template)
	packet["version"] = 2
	packet["task_id"] = taskID
	packet["source_task_ref"] = fmt.Sprintf("task-index.json#/tasks/%d", position)
	packet["source_revision"] = index["source_revision"]
	packet["objective"] = task["objective"]
	packet["policy_refs"] = mergeImplementTaskLists(index["policy_refs"], task["policy_refs"])
	packet["user_confirmed_deferral_refs"] = mergeImplementTaskLists(index["user_confirmed_deferral_refs"], task["user_confirmed_deferral_refs"])
	packet["implementation_target_ref"] = firstImplementTaskValue(task["implementation_target_ref"], index["implementation_target_ref"])
	packet["authoritative_refs"] = mergeImplementTaskLists(task["authoritative_refs"], task["required_refs"])
	readScope := anyStringSlice(task["read_scope"])
	if err := validateTaskControlProductScope(taskID, "read_scope", readScope); err != nil {
		return nil, err
	}
	writeScope := anyStringSlice(task["expected_write_scope"])
	if err := validateTaskControlProductScope(taskID, "expected_write_scope", writeScope); err != nil {
		return nil, err
	}
	packet["read_scope"] = stringsToAny(readScope)
	packet["write_scope"] = stringsToAny(writeScope)
	packet["forbidden_drift"] = stringsToAny(anyStringSlice(task["forbidden_drift"]))
	packetAcceptanceRefs := mergeImplementTaskLists(task["acceptance_refs"], task["required_refs"])
	if len(packetAcceptanceRefs) == 0 {
		packetAcceptanceRefs = mergeImplementTaskLists(index["acceptance_refs"])
	}
	packet["acceptance_refs"] = packetAcceptanceRefs
	packet["must_preserve_refs"] = mergeImplementTaskLists(task["must_preserve_refs"], task["must_preserve_ids"])
	packet["consequence_obligation_refs"] = mergeImplementTaskLists(task["consequence_obligation_refs"], task["consequence_obligation_ids"])
	packet["capability_operation_refs"] = mergeImplementTaskLists(task["capability_operation_refs"], task["capability_operations"])
	packet["fidelity_refs"] = mergeImplementTaskLists(task["fidelity_refs"])
	if ui, ok := task["ui_contract"].(map[string]any); ok {
		packet["ui_contract"] = cloneJSONValue(ui)
	}
	if policy, ok := index["validation_policy"].(map[string]any); ok {
		packet["validation_policy"] = cloneJSONValue(policy)
	}
	packet["task_checks"] = stringsToAny(anyStringSlice(task["task_checks"]))
	packet["required_validation"] = stringsToAny(anyStringSlice(task["verification"]))
	packet["required_consumer_evidence"] = stringsToAny(anyStringSlice(task["consumer_surfaces"]))
	packet["done_condition"] = stringsToAny(anyStringSlice(task["acceptance"]))
	packet["stop_and_reopen_conditions"] = stringsToAny(anyStringSlice(task["stop_and_reopen_conditions"]))
	packet["recovery"] = cloneJSONValue(task["recovery"])
	if strings.TrimSpace(anyString(packet["objective"])) == "" {
		return nil, fmt.Errorf("task %s has no objective", taskID)
	}
	packetBytes, err := marshalTaskControlJSON(packet)
	if err != nil {
		return nil, err
	}
	packetRef := filepath.ToSlash(filepath.Join("implementation-review", "packets", taskID+".json"))
	task["packet_ref"] = packetRef
	indexBytes, err := marshalTaskControlJSON(index)
	if err != nil {
		return nil, err
	}
	receipt, err := applyFileTransaction(root, "implement.packet.compile", []fileTransactionUpdate{
		{Path: filepath.Join(feature, filepath.FromSlash(packetRef)), Content: packetBytes, Perm: 0o644},
		{Path: filepath.Join(feature, "task-index.json"), Content: indexBytes, Perm: 0o644},
	})
	if err != nil {
		return nil, err
	}
	result := fileTransactionReceiptMap(receipt)
	result["status"] = "ok"
	result["task_id"] = taskID
	result["packet_ref"] = packetRef
	result["path"] = packetRef
	result["sha256"] = taskControlSHA256(packetBytes)
	return result, nil
}

func runImplementTaskStart(args []string) (map[string]any, error) {
	root, feature, err := taskControlFeature(args)
	if err != nil {
		return nil, err
	}
	taskID, err := normalizeTaskControlID(optionValue(args, "--task-id", ""))
	if err != nil {
		return nil, err
	}
	mode := strings.ToLower(strings.TrimSpace(optionValue(args, "--execution-mode", "leader-direct")))
	if mode != "leader-direct" && mode != "delegated" && mode != "managed-team" {
		return nil, fmt.Errorf("execution_mode must be leader-direct, delegated, or managed-team")
	}
	index, err := loadReadyImplementTaskIndex(root, feature)
	if err != nil {
		return nil, err
	}
	position, task, err := findImplementTask(index, taskID)
	if err != nil {
		return nil, err
	}
	status := taskControlStatus(task)
	if status != "pending" && status != "ready" && status != "blocked" && status != "failed" {
		return nil, fmt.Errorf("task %s cannot start from status %s", taskID, status)
	}
	if unmet := unmetImplementTaskDependencies(index, task); len(unmet) > 0 {
		return nil, fmt.Errorf("task %s has unmet dependencies: %s", taskID, strings.Join(unmet, ", "))
	}
	lifecycleRef := filepath.ToSlash(filepath.Join("implementation-review", "tasks", taskID+".json"))
	lifecyclePath := filepath.Join(feature, filepath.FromSlash(lifecycleRef))
	var lifecycle map[string]any
	if pathExists(lifecyclePath) {
		lifecycle, err = readImplementJSONMap(lifecyclePath)
		if err != nil {
			return nil, fmt.Errorf("task lifecycle is invalid: %w", err)
		}
	} else {
		lifecycle, err = newImplementTaskLifecycle(root, index, position, taskID)
		if err != nil {
			return nil, err
		}
	}
	revision := intFromAny(lifecycle["revision"]) + 1
	packetRef := strings.TrimSpace(optionValue(args, "--packet-ref", ""))
	if packetRef == "" {
		packetRef = strings.TrimSpace(anyString(task["packet_ref"]))
	}
	if mode != "leader-direct" && packetRef == "" {
		return nil, fmt.Errorf("%s execution requires a CLI-compiled packet_ref", mode)
	}
	if mode != "leader-direct" {
		packetRef, err = validateImplementTaskPacketRef(root, feature, packetRef, taskID)
		if err != nil {
			return nil, err
		}
	}
	lifecycle["revision"] = revision
	lifecycle["execution_mode"] = mode
	lifecycle["packet_ref"] = nullableImplementTaskString(packetRef)
	lifecycle["status"] = "in_progress"
	lifecycle["blockers"] = []any{}
	lifecycle["recovery"] = nil
	task["status"] = "in_progress"
	task["lifecycle_ref"] = lifecycleRef
	state, err := loadImplementExecutionState(feature, index)
	if err != nil {
		return nil, err
	}
	state["revision"] = intFromAny(state["revision"]) + 1
	state["status"] = "executing"
	state["current_task"] = taskID
	state["next_action"] = fmt.Sprintf("Complete %s and record its structured result.", taskID)
	payload, err := commitImplementTaskState(root, feature, "implement.task.start", index, state, map[string]map[string]any{lifecycleRef: lifecycle}, nil, nil)
	if err != nil {
		return nil, err
	}
	payload["task_id"] = taskID
	payload["task_status"] = "in_progress"
	payload["revision"] = revision
	return payload, nil
}

func runImplementResultMerge(args []string) (map[string]any, error) {
	root, feature, err := taskControlFeature(args)
	if err != nil {
		return nil, err
	}
	taskID, err := normalizeTaskControlID(optionValue(args, "--task-id", ""))
	if err != nil {
		return nil, err
	}
	rawResult, err := readImplementTaskResult(args, root)
	if err != nil {
		return nil, err
	}
	result, workerStatus, err := normalizeImplementTaskResult(rawResult, taskID)
	if err != nil {
		return nil, err
	}
	index, err := loadReadyImplementTaskIndex(root, feature)
	if err != nil {
		return nil, err
	}
	_, task, err := findImplementTask(index, taskID)
	if err != nil {
		return nil, err
	}
	lifecycleRef := filepath.ToSlash(filepath.Join("implementation-review", "tasks", taskID+".json"))
	lifecycle, err := readImplementJSONMap(filepath.Join(feature, filepath.FromSlash(lifecycleRef)))
	if err != nil {
		return nil, fmt.Errorf("task lifecycle is missing or invalid: %w", err)
	}
	lifecycleStatus := strings.ToLower(strings.TrimSpace(anyString(lifecycle["status"])))
	if lifecycleStatus != "in_progress" && lifecycleStatus != "blocked" && lifecycleStatus != "failed" {
		return nil, fmt.Errorf("task %s cannot record a result from status %s", taskID, lifecycleStatus)
	}
	statusMap := map[string]string{"success": "implemented", "blocked": "blocked", "failed": "failed"}
	taskStatus := statusMap[workerStatus]
	resultRef := filepath.ToSlash(filepath.Join("worker-results", taskID+".json"))
	revision := intFromAny(lifecycle["revision"]) + 1
	lifecycle["revision"] = revision
	lifecycle["status"] = taskStatus
	lifecycle["result_ref"] = resultRef
	lifecycle["changed_paths"] = cloneJSONValue(result["changed_files"])
	lifecycle["validation"] = cloneJSONValue(result["validation_results"])
	lifecycle["blockers"] = cloneJSONValue(result["blockers"])
	recoveryActions := anyStringSlice(result["suggested_recovery_actions"])
	if len(recoveryActions) > 0 {
		lifecycle["recovery"] = map[string]any{"actions": stringsToAny(recoveryActions)}
	} else {
		lifecycle["recovery"] = nil
	}
	if ui, ok := result["ui_verification"].(map[string]any); ok {
		lifecycle["ui_verification"] = cloneJSONValue(ui)
	}
	if evidence, ok := result["obligation_evidence"].([]any); ok {
		lifecycle["obligation_evidence"] = cloneJSONValue(evidence)
	}
	task["status"] = taskStatus
	task["result_ref"] = resultRef
	state, err := loadImplementExecutionState(feature, index)
	if err != nil {
		return nil, err
	}
	state["revision"] = intFromAny(state["revision"]) + 1
	state["status"] = taskStatus
	if workerStatus == "success" {
		state["status"] = "validating"
	}
	state["current_task"] = taskID
	if workerStatus == "success" {
		state["next_action"] = fmt.Sprintf("Validate and accept %s.", taskID)
	} else {
		state["next_action"] = fmt.Sprintf("Recover %s before continuing.", taskID)
	}
	failed := anyStringSlice(state["failed_task_ids"])
	failed = removeImplementTaskString(failed, taskID)
	if workerStatus == "failed" {
		failed = append(failed, taskID)
	}
	state["failed_task_ids"] = stringsToAny(failed)
	resultBytes, err := marshalTaskControlJSON(result)
	if err != nil {
		return nil, err
	}
	payload, err := commitImplementTaskState(root, feature, "implement.result.merge", index, state, map[string]map[string]any{lifecycleRef: lifecycle}, map[string][]byte{resultRef: resultBytes}, nil)
	if err != nil {
		return nil, err
	}
	payload["task_id"] = taskID
	payload["task_status"] = taskStatus
	payload["worker_status"] = workerStatus
	payload["result_ref"] = resultRef
	payload["revision"] = revision
	return payload, nil
}

func runImplementTaskAccept(args []string) (map[string]any, error) {
	root, feature, err := taskControlFeature(args)
	if err != nil {
		return nil, err
	}
	taskID, err := normalizeTaskControlID(optionValue(args, "--task-id", ""))
	if err != nil {
		return nil, err
	}
	index, err := loadReadyImplementTaskIndex(root, feature)
	if err != nil {
		return nil, err
	}
	_, task, err := findImplementTask(index, taskID)
	if err != nil {
		return nil, err
	}
	lifecycleRef := filepath.ToSlash(filepath.Join("implementation-review", "tasks", taskID+".json"))
	lifecycle, err := readImplementJSONMap(filepath.Join(feature, filepath.FromSlash(lifecycleRef)))
	if err != nil {
		return nil, fmt.Errorf("task lifecycle is missing or invalid: %w", err)
	}
	if lifecycle["status"] != "implemented" {
		return nil, fmt.Errorf("task %s must be implemented before acceptance", taskID)
	}
	validation, ok := lifecycle["validation"].([]any)
	if !ok || len(validation) == 0 {
		return nil, fmt.Errorf("task acceptance requires validation evidence")
	}
	for _, value := range validation {
		item, ok := value.(map[string]any)
		if !ok || strings.ToLower(strings.TrimSpace(anyString(item["status"]))) != "passed" {
			return nil, fmt.Errorf("task acceptance requires passed validation evidence")
		}
	}
	if err := validateImplementTaskCheckCoverage(task, validation); err != nil {
		return nil, err
	}
	if blockers, ok := lifecycle["blockers"].([]any); ok && len(blockers) > 0 {
		return nil, fmt.Errorf("task acceptance is blocked by unresolved blockers")
	}
	revision := intFromAny(lifecycle["revision"]) + 1
	lifecycle["revision"] = revision
	lifecycle["status"] = "accepted"
	task["status"] = "accepted"
	tasksPath := filepath.Join(feature, "tasks.md")
	rawTasks, err := os.ReadFile(tasksPath)
	if err != nil {
		return nil, fmt.Errorf("tasks.md is missing: %w", err)
	}
	projected, err := projectImplementTaskCheckbox(string(rawTasks), taskID, true)
	if err != nil {
		return nil, err
	}
	state, err := loadImplementExecutionState(feature, index)
	if err != nil {
		return nil, err
	}
	state["revision"] = intFromAny(state["revision"]) + 1
	completed := removeImplementTaskString(anyStringSlice(state["completed_task_ids"]), taskID)
	completed = append(completed, taskID)
	state["completed_task_ids"] = stringsToAny(completed)
	state["current_task"] = nil
	next := nextImplementTaskFromIndex(index)
	if next == nil {
		state["status"] = "resolved"
		state["next_action"] = "Run implementation convergence and closeout."
	} else {
		state["status"] = "executing"
		state["next_action"] = fmt.Sprintf("Start %s.", next["task_id"])
	}
	payload, err := commitImplementTaskState(root, feature, "implement.task.accept", index, state, map[string]map[string]any{lifecycleRef: lifecycle}, nil, []byte(projected))
	if err != nil {
		return nil, err
	}
	payload["task_id"] = taskID
	payload["task_status"] = "accepted"
	payload["revision"] = revision
	if next == nil {
		payload["next_task_id"] = nil
	} else {
		payload["next_task_id"] = next["task_id"]
	}
	return payload, nil
}

func loadReadyImplementTaskIndex(root, feature string) (map[string]any, error) {
	index, _, err := loadTaskControlPackage(root, feature)
	if err != nil {
		return nil, err
	}
	if index["status"] != "ready" {
		return nil, fmt.Errorf("task-index.json must use version 2 with status ready")
	}
	return index, nil
}

func findImplementTask(index map[string]any, taskID string) (int, map[string]any, error) {
	tasks, ok := index["tasks"].([]any)
	if !ok {
		return 0, nil, fmt.Errorf("task-index.json tasks must be an array")
	}
	for position, value := range tasks {
		task, ok := value.(map[string]any)
		if ok && strings.ToUpper(anyString(firstImplementTaskValue(task["id"], task["task_id"]))) == taskID {
			return position, task, nil
		}
	}
	return 0, nil, fmt.Errorf("task %s is not present in task-index.json", taskID)
}

func nextImplementTaskFromIndex(index map[string]any) map[string]any {
	tasks, _ := index["tasks"].([]any)
	statuses := map[string]string{}
	for _, value := range tasks {
		task, ok := value.(map[string]any)
		if !ok {
			continue
		}
		statuses[strings.ToUpper(anyString(firstImplementTaskValue(task["id"], task["task_id"])))] = taskControlStatus(task)
	}
	for _, value := range tasks {
		task, ok := value.(map[string]any)
		if !ok {
			continue
		}
		id := strings.ToUpper(anyString(firstImplementTaskValue(task["id"], task["task_id"])))
		status := taskControlStatus(task)
		if !taskControlIDRE.MatchString(id) || (status != "pending" && status != "ready") {
			continue
		}
		dependencies := anyStringSlice(task["dependencies"])
		ready := true
		for _, dependency := range dependencies {
			if !implementTaskTerminalStatuses[statuses[strings.ToUpper(dependency)]] {
				ready = false
				break
			}
		}
		if ready {
			return map[string]any{
				"task_id":       id,
				"status":        status,
				"objective":     strings.TrimSpace(anyString(task["objective"])),
				"dependencies":  stringsToAny(dependencies),
				"lifecycle_ref": filepath.ToSlash(filepath.Join("implementation-review", "tasks", id+".json")),
			}
		}
	}
	return nil
}

func unmetImplementTaskDependencies(index map[string]any, task map[string]any) []string {
	tasks, _ := index["tasks"].([]any)
	statuses := map[string]string{}
	for _, value := range tasks {
		item, ok := value.(map[string]any)
		if ok {
			statuses[strings.ToUpper(anyString(item["id"]))] = taskControlStatus(item)
		}
	}
	unmet := []string{}
	for _, dependency := range anyStringSlice(task["dependencies"]) {
		dependency = strings.ToUpper(dependency)
		if !implementTaskTerminalStatuses[statuses[dependency]] {
			unmet = append(unmet, dependency)
		}
	}
	return unmet
}

func newImplementTaskLifecycle(root string, index map[string]any, position int, taskID string) (map[string]any, error) {
	path := filepath.Join(root, ".specify", "templates", "task-lifecycle-template.json")
	payload, err := readImplementJSONMap(path)
	if err != nil {
		return nil, fmt.Errorf("task-lifecycle template is invalid or missing: %w", err)
	}
	payload["version"] = 1
	payload["revision"] = 0
	payload["task_id"] = taskID
	payload["task_ref"] = fmt.Sprintf("task-index.json#/tasks/%d", position)
	payload["source_revision"] = index["source_revision"]
	payload["execution_mode"] = "leader-direct"
	payload["packet_ref"] = nil
	payload["result_ref"] = nil
	payload["status"] = "pending"
	return payload, nil
}

func loadImplementExecutionState(feature string, index map[string]any) (map[string]any, error) {
	path := filepath.Join(feature, "implementation-review", "execution-state.json")
	if pathExists(path) {
		payload, err := readImplementJSONMap(path)
		if err != nil {
			return nil, fmt.Errorf("execution-state.json is invalid: %w", err)
		}
		if intFromAny(payload["version"]) != 3 {
			return nil, fmt.Errorf("execution-state.json must use version 3")
		}
		return payload, nil
	}
	return map[string]any{
		"version": 3, "revision": 0, "status": "gathering",
		"source_contract": "task-index.json", "source_revision": index["source_revision"],
		"current_batch": nil, "current_task": nil,
		"next_action":        "Start the next dependency-ready task.",
		"completed_task_ids": []any{}, "failed_task_ids": []any{}, "retry_count": 0,
		"active_packet_refs": []any{}, "blockers": []any{}, "recovery": nil,
		"open_gaps": []any{}, "validation": []any{},
	}, nil
}

func commitImplementTaskState(root, feature, kind string, index, state map[string]any, lifecycles map[string]map[string]any, extra map[string][]byte, tasksProjection []byte) (map[string]any, error) {
	indexBytes, err := marshalTaskControlJSON(index)
	if err != nil {
		return nil, err
	}
	stateBytes, err := marshalTaskControlJSON(state)
	if err != nil {
		return nil, err
	}
	updates := []fileTransactionUpdate{
		{Path: filepath.Join(feature, "task-index.json"), Content: indexBytes, Perm: 0o644},
		{Path: filepath.Join(feature, "implementation-review", "execution-state.json"), Content: stateBytes, Perm: 0o644},
		{Path: filepath.Join(feature, "implement-tracker.md"), Content: renderImplementTaskTracker(feature, state), Perm: 0o644},
	}
	for ref, payload := range lifecycles {
		raw, marshalErr := marshalTaskControlJSON(payload)
		if marshalErr != nil {
			return nil, marshalErr
		}
		updates = append(updates, fileTransactionUpdate{Path: filepath.Join(feature, filepath.FromSlash(ref)), Content: raw, Perm: 0o644})
	}
	for ref, raw := range extra {
		updates = append(updates, fileTransactionUpdate{Path: filepath.Join(feature, filepath.FromSlash(ref)), Content: raw, Perm: 0o644})
	}
	if tasksProjection != nil {
		updates = append(updates, fileTransactionUpdate{Path: filepath.Join(feature, "tasks.md"), Content: tasksProjection, Perm: 0o644})
	}
	receipt, err := applyFileTransaction(root, kind, updates)
	if err != nil {
		return nil, err
	}
	result := fileTransactionReceiptMap(receipt)
	result["status"] = "ok"
	return result, nil
}

func renderImplementTaskTracker(feature string, state map[string]any) []byte {
	status := defaultString(strings.TrimSpace(anyString(state["status"])), "executing")
	resume := "continue"
	if status == "resolved" {
		resume = "resolved"
	} else if status == "blocked" {
		resume = "blocked"
	}
	current := defaultString(strings.TrimSpace(anyString(state["current_task"])), "none")
	lines := []string{
		"---", "status: " + status, "feature: " + filepath.Base(feature), "resume_decision: " + resume,
		"---", "", "## Current Focus", "current_batch: " + defaultString(anyString(state["current_batch"]), "canonical task graph"),
		"goal: execute " + current, "next_action: " + defaultString(anyString(state["next_action"]), "Resume the canonical task state."),
		"", "## Execution State", "completed_tasks:",
	}
	for _, id := range anyStringSlice(state["completed_task_ids"]) {
		lines = append(lines, "  - "+id)
	}
	lines = append(lines, "in_progress_tasks:")
	if current != "none" {
		lines = append(lines, "  - "+current)
	}
	lines = append(lines, "failed_tasks:")
	for _, id := range anyStringSlice(state["failed_task_ids"]) {
		lines = append(lines, "  - "+id)
	}
	lines = append(lines, fmt.Sprintf("retry_attempts: %d", intFromAny(state["retry_count"])), "", "## Open Gaps")
	for _, gap := range anyStringSlice(state["open_gaps"]) {
		lines = append(lines, "- "+gap)
	}
	return []byte(strings.Join(lines, "\n") + "\n")
}

func readImplementTaskResult(args []string, root string) (map[string]any, error) {
	hasInline := hasFlag(args, "--result-json")
	hasFile := hasFlag(args, "--result-file")
	if hasInline == hasFile {
		return nil, fmt.Errorf("provide exactly one of --result-json or --result-file")
	}
	var raw []byte
	if hasInline {
		raw = []byte(optionValue(args, "--result-json", ""))
		if len(raw) == 0 || len(raw) > maxAgentJSONInputBytes {
			return nil, fmt.Errorf("--result-json must contain at most %d bytes", maxAgentJSONInputBytes)
		}
	} else {
		path, err := resolveProjectContainedPath(root, optionValue(args, "--result-file", ""))
		if err != nil {
			return nil, fmt.Errorf("result file must stay inside the project: %w", err)
		}
		if !strings.EqualFold(filepath.Ext(path), ".json") {
			return nil, fmt.Errorf("result file must be JSON")
		}
		relative, err := filepath.Rel(root, path)
		if err != nil {
			return nil, fmt.Errorf("result file must stay inside the project: %w", err)
		}
		metadata, registered := LookupArtifactType(filepath.ToSlash(relative))
		if !registered || (metadata.Schema != "json/worker-result" && metadata.TypeID != "teams-runtime-state") {
			return nil, fmt.Errorf("--result-file may reference only a CLI-owned canonical worker-result artifact; pass new results inline with --result-json")
		}
		info, err := os.Stat(path)
		if err != nil || !info.Mode().IsRegular() || info.Size() > maxAgentJSONInputBytes {
			return nil, fmt.Errorf("result file is unavailable, non-regular, or too large")
		}
		raw, err = os.ReadFile(path)
		if err != nil {
			return nil, err
		}
	}
	var payload map[string]any
	if err := json.Unmarshal(raw, &payload); err != nil || payload == nil {
		return nil, fmt.Errorf("worker result must be a JSON object")
	}
	return payload, nil
}

func normalizeImplementTaskResult(raw map[string]any, taskID string) (map[string]any, string, error) {
	payload := cloneJSONMap(raw)
	resultTaskID := strings.ToUpper(strings.TrimSpace(anyString(firstImplementTaskValue(payload["task_id"], payload["taskId"]))))
	if resultTaskID == "" {
		resultTaskID = taskID
	}
	if resultTaskID != taskID {
		return nil, "", fmt.Errorf("worker result task_id %s does not match %s", resultTaskID, taskID)
	}
	status := strings.ToLower(strings.TrimSpace(anyString(payload["status"])))
	switch status {
	case "success", "succeeded", "completed", "complete", "passed", "pass":
		status = "success"
	case "blocked", "needs_context", "needs-context":
		status = "blocked"
	case "failed", "failure", "error":
		status = "failed"
	case "pending", "":
		return nil, "", fmt.Errorf("pending worker results cannot be merged")
	default:
		return nil, "", fmt.Errorf("worker result status is invalid: %s", status)
	}
	changed := firstImplementTaskValue(payload["changed_files"], payload["changedFiles"], payload["files_changed"])
	changedFiles, err := taskControlStringList(changed, "changed_files")
	if err != nil {
		return nil, "", err
	}
	validationRaw := firstImplementTaskValue(payload["validation_results"], payload["validationResults"])
	validation := []any{}
	if validationRaw != nil {
		items, ok := validationRaw.([]any)
		if !ok {
			return nil, "", fmt.Errorf("validation_results must be an array")
		}
		for _, value := range items {
			item, ok := value.(map[string]any)
			if !ok {
				return nil, "", fmt.Errorf("validation_results entries must be objects")
			}
			item = cloneJSONMap(item)
			itemStatus := strings.ToLower(strings.TrimSpace(anyString(item["status"])))
			switch itemStatus {
			case "pass", "passed", "success", "succeeded":
				itemStatus = "passed"
			case "fail", "failed", "failure", "error":
				itemStatus = "failed"
			case "skipped", "not_run", "not-run":
				itemStatus = "skipped"
			default:
				return nil, "", fmt.Errorf("validation result status is invalid: %s", itemStatus)
			}
			item["status"] = itemStatus
			validation = append(validation, item)
		}
	}
	blockers, err := taskControlStringList(firstImplementTaskValue(payload["blockers"], []any{}), "blockers")
	if err != nil {
		return nil, "", err
	}
	recovery, err := taskControlStringList(firstImplementTaskValue(payload["suggested_recovery_actions"], payload["suggestedRecoveryActions"], []any{}), "suggested_recovery_actions")
	if err != nil {
		return nil, "", err
	}
	if status == "blocked" && len(blockers) == 0 {
		return nil, "", fmt.Errorf("blocked worker results require at least one blocker")
	}
	if status == "blocked" && len(recovery) == 0 {
		recovery = []string{"inspect the blocker details and resubmit the delegated task"}
	}
	if status == "success" && len(blockers) > 0 {
		return nil, "", fmt.Errorf("successful worker results cannot contain blockers")
	}
	payload["version"] = intFromAny(payload["version"])
	if intFromAny(payload["version"]) == 0 {
		payload["version"] = 1
	}
	payload["task_id"] = taskID
	payload["status"] = status
	payload["changed_files"] = stringsToAny(changedFiles)
	payload["validation_results"] = validation
	payload["blockers"] = stringsToAny(blockers)
	payload["suggested_recovery_actions"] = stringsToAny(recovery)
	delete(payload, "taskId")
	delete(payload, "changedFiles")
	delete(payload, "files_changed")
	delete(payload, "validationResults")
	delete(payload, "suggestedRecoveryActions")
	return payload, status, nil
}

func validateImplementTaskCheckCoverage(task map[string]any, validation []any) error {
	required := anyStringSlice(task["task_checks"])
	if len(required) == 0 {
		return nil
	}
	passed := map[string]bool{}
	for _, value := range validation {
		item, ok := value.(map[string]any)
		if !ok || strings.ToLower(strings.TrimSpace(anyString(item["status"]))) != "passed" {
			continue
		}
		command := strings.TrimSpace(anyString(firstImplementTaskValue(item["command"], item["check"])))
		if command != "" {
			passed[command] = true
		}
	}
	missing := []string{}
	for _, check := range required {
		if !passed[check] {
			missing = append(missing, check)
		}
	}
	if len(missing) > 0 {
		return fmt.Errorf("task acceptance is missing passed task_checks: %s", strings.Join(missing, ", "))
	}
	return nil
}

func projectImplementTaskCheckbox(content, taskID string, checked bool) (string, error) {
	pattern := regexp.MustCompile(`(?m)^(\s*-\s*\[)[ xX](\]\s+` + regexp.QuoteMeta(taskID) + `\b)`)
	replacement := "${1} ${2}"
	if checked {
		replacement = "${1}x${2}"
	}
	matches := pattern.FindAllStringIndex(content, -1)
	if len(matches) != 1 {
		return "", fmt.Errorf("tasks.md has no unique checkbox for %s", taskID)
	}
	return pattern.ReplaceAllString(content, replacement), nil
}

func mergeImplementTaskLists(values ...any) []any {
	result := []string{}
	seen := map[string]bool{}
	for _, value := range values {
		for _, item := range anyStringSlice(value) {
			if !seen[item] {
				result = append(result, item)
				seen[item] = true
			}
		}
	}
	return stringsToAny(result)
}

func firstImplementTaskValue(values ...any) any {
	for _, value := range values {
		if value == nil {
			continue
		}
		if text, ok := value.(string); ok && strings.TrimSpace(text) == "" {
			continue
		}
		return value
	}
	return nil
}

func nullableImplementTaskString(value string) any {
	if strings.TrimSpace(value) == "" {
		return nil
	}
	return value
}

func validateImplementTaskPacketRef(root, feature, packetRef, taskID string) (string, error) {
	packetRef = filepath.ToSlash(strings.TrimSpace(packetRef))
	if packetRef == "" || filepath.IsAbs(filepath.FromSlash(packetRef)) || strings.HasPrefix(packetRef, "../") {
		return "", fmt.Errorf("packet_ref must be a feature-relative CLI-owned path")
	}
	featureRelative, err := filepath.Rel(root, feature)
	if err != nil {
		return "", err
	}
	projectRef := filepath.ToSlash(filepath.Join(featureRelative, filepath.FromSlash(packetRef)))
	packetPath, err := resolveProjectContainedPath(root, projectRef)
	if err != nil {
		return "", fmt.Errorf("packet_ref is invalid: %w", err)
	}
	expectedRoot := filepath.Join(feature, "implementation-review", "packets")
	rel, err := filepath.Rel(expectedRoot, packetPath)
	if err != nil || rel == ".." || strings.HasPrefix(rel, ".."+string(filepath.Separator)) {
		return "", fmt.Errorf("packet_ref must name a CLI-owned implementation packet")
	}
	packet, err := readImplementJSONMap(packetPath)
	if err != nil {
		return "", fmt.Errorf("packet_ref is missing or invalid: %w", err)
	}
	if strings.ToUpper(strings.TrimSpace(anyString(packet["task_id"]))) != taskID {
		return "", fmt.Errorf("packet_ref is not bound to task %s", taskID)
	}
	return packetRef, nil
}

func removeImplementTaskString(values []string, target string) []string {
	result := make([]string, 0, len(values))
	for _, value := range values {
		if value != target {
			result = append(result, value)
		}
	}
	return result
}
