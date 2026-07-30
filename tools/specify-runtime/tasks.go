package main

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"reflect"
	"regexp"
	"sort"
	"strings"
)

var taskControlIDRE = regexp.MustCompile(`^T\d+$`)

var taskControlTerminalStatuses = map[string]bool{"accepted": true, "deferred": true}

var taskControlAuthoringMutableStatuses = map[string]bool{
	"pending": true,
	"ready":   true,
	"blocked": true,
	"failed":  true,
}

var taskControlObsoleteFields = map[string]bool{
	"ui_contract_version":      true,
	"ui_fidelity_requirements": true,
	"ui_fidelity_evidence":     true,
}

var taskControlRuntimeFields = map[string]bool{
	"status":        true,
	"lifecycle_ref": true,
	"packet_ref":    true,
	"result_ref":    true,
}

var taskControlAuthoredFields = map[string]bool{
	"id": true, "task_id": true, "story_id": true, "phase": true,
	"objective": true, "description": true, "dependencies": true, "depends_on": true,
	"parallel": true, "batch": true, "batch_id": true, "join_point": true, "join_point_id": true,
	"owner": true, "execution_mode": true, "task_kind": true, "priority": true, "risk": true, "risk_level": true,
	"expected_write_scope": true, "write_scope": true, "read_scope": true,
	"required_refs": true, "authoritative_refs": true, "policy_refs": true,
	"forbidden_drift": true, "hard_rules": true, "acceptance": true, "acceptance_refs": true,
	"verification": true, "required_validation": true, "task_checks": true,
	"consumer_surfaces": true, "required_consumer_evidence": true, "required_evidence": true,
	"must_preserve_ids": true, "must_preserve_refs": true,
	"consequence_obligation_ids": true, "consequence_obligation_refs": true,
	"capability_operations": true, "capability_operation_refs": true, "fidelity_refs": true,
	"user_confirmed_deferral_refs": true, "implementation_target_ref": true,
	"stop_and_reopen_conditions": true, "recovery": true, "ui_contract": true,
	"no_new_test_rationale": true, "replacement_validation": true, "residual_risk": true,
	"skills": true, "notes": true,
}

func runTasks(args []string, stdout io.Writer) int {
	if len(args) == 0 {
		return writeImplementError(stdout, "usage-error", "missing tasks subcommand")
	}
	var payload map[string]any
	var err error
	var summary string
	switch args[0] {
	case "build":
		payload, err = runTasksBuild(args[1:])
		summary = "draft canonical task package created"
	case "upsert":
		payload, err = runTasksUpsert(args[1:])
		summary = "canonical task package updated"
	case "set-root":
		payload, err = runTasksSetRoot(args[1:])
		summary = "task package root fields updated"
	case "remove":
		payload, err = runTasksRemove(args[1:])
		summary = "task removed from canonical task package"
	case "finalize":
		payload, err = runTasksFinalize(args[1:])
		summary = "canonical task package finalized"
	case "handoff":
		payload, err = runTasksHandoff(args[1:])
		summary = "task handoff materialized"
	default:
		return writeImplementError(stdout, "usage-error", fmt.Sprintf("unknown tasks subcommand %q", args[0]))
	}
	return writeImplementPayload(stdout, payload, err, summary)
}

func runTasksBuild(args []string) (map[string]any, error) {
	root, feature, err := taskControlFeature(args)
	if err != nil {
		return nil, err
	}
	definition, err := taskControlInlineObject(args, "--definition-json", "task definition")
	if err != nil {
		return nil, err
	}
	if pathExists(filepath.Join(feature, "task-index.json")) || pathExists(filepath.Join(feature, "tasks.md")) {
		return nil, fmt.Errorf("task package already exists; use tasks upsert, set-root, or remove")
	}
	template, err := loadTaskControlTemplate(root)
	if err != nil {
		return nil, err
	}
	payload := cloneJSONMap(template)
	title := strings.TrimSpace(anyString(definition["title"]))
	if title == "" {
		title = "Feature implementation"
	}
	for key, value := range definition {
		if key == "title" {
			continue
		}
		if _, ok := template[key]; !ok {
			return nil, fmt.Errorf("task definition contains unsupported root field %q", key)
		}
		if key == "version" || key == "status" || key == "transition" {
			return nil, fmt.Errorf("%s is CLI-owned and cannot be authored", key)
		}
		payload[key] = cloneJSONValue(value)
	}
	tasks, err := normalizeTaskControlTasks(payload["tasks"], false)
	if err != nil {
		return nil, err
	}
	tasks, err = expandTaskControlUIContracts(root, tasks)
	if err != nil {
		return nil, err
	}
	payload["version"] = 2
	payload["status"] = "draft"
	payload["tasks"] = tasks
	payload["transition"] = map[string]any{
		"version":     1,
		"status":      "blocked",
		"source_ref":  "task-index.json",
		"blockers":    []any{"task package has not been finalized"},
		"next_action": "Run `specify-runtime tasks finalize` after task review.",
	}
	return commitTaskControlPackage(root, feature, payload, title, "tasks.build")
}

func runTasksUpsert(args []string) (map[string]any, error) {
	root, feature, err := taskControlFeature(args)
	if err != nil {
		return nil, err
	}
	rawTask, err := taskControlInlineObject(args, "--task-json", "task")
	if err != nil {
		return nil, err
	}
	payload, title, err := loadTaskControlPackage(root, feature)
	if err != nil {
		return nil, err
	}
	task, err := normalizeTaskControlTask(rawTask, false)
	if err != nil {
		return nil, err
	}
	expanded, err := expandTaskControlUIContracts(root, []any{task})
	if err != nil {
		return nil, err
	}
	task = expanded[0].(map[string]any)
	tasks := payload["tasks"].([]any)
	replaced := false
	for index, value := range tasks {
		existing := value.(map[string]any)
		if existing["id"] != task["id"] {
			continue
		}
		existingStatus := taskControlStatus(existing)
		if !taskControlAuthoringMutableStatuses[existingStatus] {
			return nil, fmt.Errorf("%s has runtime status %s and cannot be replaced through task authoring", task["id"], existingStatus)
		}
		tasks[index] = task
		replaced = true
		break
	}
	if !replaced {
		tasks = append(tasks, task)
	}
	payload["tasks"] = tasks
	markTaskControlDraft(payload, "task package changed after its last finalize")
	return commitTaskControlPackage(root, feature, payload, title, "tasks.upsert")
}

func runTasksSetRoot(args []string) (map[string]any, error) {
	root, feature, err := taskControlFeature(args)
	if err != nil {
		return nil, err
	}
	patch, err := taskControlInlineObject(args, "--patch-json", "task root patch")
	if err != nil {
		return nil, err
	}
	payload, title, err := loadTaskControlPackage(root, feature)
	if err != nil {
		return nil, err
	}
	template, err := loadTaskControlTemplate(root)
	if err != nil {
		return nil, err
	}
	for key, value := range patch {
		if _, ok := template[key]; !ok {
			return nil, fmt.Errorf("root patch contains unsupported field %q", key)
		}
		if key == "version" || key == "status" || key == "tasks" || key == "transition" {
			return nil, fmt.Errorf("root patch contains CLI-owned field %q", key)
		}
		payload[key] = cloneJSONValue(value)
	}
	markTaskControlDraft(payload, "task package changed after its last finalize")
	return commitTaskControlPackage(root, feature, payload, title, "tasks.set-root")
}

func runTasksRemove(args []string) (map[string]any, error) {
	root, feature, err := taskControlFeature(args)
	if err != nil {
		return nil, err
	}
	taskID, err := normalizeTaskControlID(optionValue(args, "--task-id", ""))
	if err != nil {
		return nil, err
	}
	payload, title, err := loadTaskControlPackage(root, feature)
	if err != nil {
		return nil, err
	}
	tasks := payload["tasks"].([]any)
	found := false
	for _, value := range tasks {
		task := value.(map[string]any)
		if task["id"] == taskID {
			found = true
			status := taskControlStatus(task)
			if !taskControlAuthoringMutableStatuses[status] {
				return nil, fmt.Errorf("%s has runtime status %s and cannot be removed through task authoring", taskID, status)
			}
		}
		for _, dependency := range anyStringSlice(task["dependencies"]) {
			if dependency == taskID && task["id"] != taskID {
				return nil, fmt.Errorf("%s is still required by %s; update that task first", taskID, task["id"])
			}
		}
	}
	if !found {
		return nil, fmt.Errorf("unknown task: %s", taskID)
	}
	kept := make([]any, 0, len(tasks)-1)
	for _, value := range tasks {
		if value.(map[string]any)["id"] != taskID {
			kept = append(kept, value)
		}
	}
	payload["tasks"] = kept
	markTaskControlDraft(payload, "task package changed after its last finalize")
	return commitTaskControlPackage(root, feature, payload, title, "tasks.remove")
}

func runTasksFinalize(args []string) (map[string]any, error) {
	root, feature, err := taskControlFeature(args)
	if err != nil {
		return nil, err
	}
	payload, title, err := loadTaskControlPackage(root, feature)
	if err != nil {
		return nil, err
	}
	tasks := payload["tasks"].([]any)
	if len(tasks) == 0 {
		return nil, fmt.Errorf("task package must contain at least one task")
	}
	if err := validateTaskControlGraph(tasks); err != nil {
		return nil, err
	}
	if err := validateTaskControlAcceptance(feature, payload); err != nil {
		return nil, err
	}
	payload["status"] = "ready"
	payload["transition"] = map[string]any{
		"version":       1,
		"status":        "ready",
		"source_ref":    "task-index.json",
		"required_refs": cloneJSONValue(payload["acceptance_refs"]),
		"blockers":      []any{},
		"next_action":   "Run sp-implement or spx-implement.",
		"recovery":      nil,
	}
	return commitTaskControlPackage(root, feature, payload, title, "tasks.finalize")
}

func runTasksHandoff(args []string) (map[string]any, error) {
	root, feature, err := taskControlFeature(args)
	if err != nil {
		return nil, err
	}
	target := strings.ToLower(strings.TrimSpace(optionValue(args, "--target", "")))
	if target != "tasks" && target != "implement" {
		return nil, fmt.Errorf("--target must be tasks or implement")
	}
	payload, _, err := loadTaskControlPackage(root, feature)
	if err != nil {
		return nil, err
	}
	transition, _ := payload["transition"].(map[string]any)
	if taskControlStatus(payload) != "ready" || strings.ToLower(strings.TrimSpace(anyString(transition["status"]))) != "ready" {
		return nil, fmt.Errorf("task package must be finalized before creating a handoff")
	}
	indexPath := filepath.Join(feature, "task-index.json")
	indexRaw, err := os.ReadFile(indexPath)
	if err != nil {
		return nil, fmt.Errorf("read canonical task index: %w", err)
	}
	handoff := map[string]any{
		"version":           1,
		"status":            "ready",
		"target":            target,
		"task_index_ref":    "task-index.json",
		"tasks_ref":         "tasks.md",
		"task_index_sha256": taskControlSHA256(indexRaw),
		"source_revision":   cloneJSONValue(payload["source_revision"]),
		"task_count":        len(payload["tasks"].([]any)),
	}
	raw, err := marshalTaskControlJSON(handoff)
	if err != nil {
		return nil, err
	}
	name := "handoff-to-" + target + ".json"
	receipt, err := applyFileTransaction(root, "tasks.handoff", []fileTransactionUpdate{
		{Path: filepath.Join(feature, name), Content: raw, Perm: 0o644},
	})
	if err != nil {
		return nil, err
	}
	result := fileTransactionReceiptMap(receipt)
	result["status"] = "ok"
	result["target"] = target
	result["handoff_ref"] = filepath.ToSlash(filepath.Join(filepath.Base(feature), name))
	for _, path := range receipt.ChangedPaths {
		if strings.HasSuffix(path, "/"+name) || path == name {
			result["handoff_ref"] = path
			break
		}
	}
	result["handoff_sha256"] = taskControlSHA256(raw)
	result["task_count"] = len(payload["tasks"].([]any))
	return result, nil
}

func taskControlFeature(args []string) (string, string, error) {
	root, feature, env, ok := implementFeatureFromArgs(args)
	if !ok {
		message := env.Summary
		if message == "" {
			message = "invalid feature directory"
		}
		return "", "", fmt.Errorf("%s", message)
	}
	info, err := os.Stat(feature)
	if err != nil || !info.IsDir() {
		return "", "", fmt.Errorf("feature directory does not exist: %s", feature)
	}
	return root, feature, nil
}

func taskControlInlineObject(args []string, flag, label string) (map[string]any, error) {
	raw := optionValue(args, flag, "")
	if strings.TrimSpace(raw) == "" {
		return nil, fmt.Errorf("%s is required", flag)
	}
	if len([]byte(raw)) > maxAgentJSONInputBytes {
		return nil, fmt.Errorf("%s exceeds %d bytes", label, maxAgentJSONInputBytes)
	}
	var payload map[string]any
	if err := json.Unmarshal([]byte(raw), &payload); err != nil {
		return nil, fmt.Errorf("%s must be a JSON object: %w", label, err)
	}
	if payload == nil {
		return nil, fmt.Errorf("%s must be a JSON object", label)
	}
	return payload, nil
}

func loadTaskControlTemplate(root string) (map[string]any, error) {
	path := filepath.Join(root, ".specify", "templates", "task-index-template.json")
	payload, err := readImplementJSONMap(path)
	if err != nil {
		return nil, fmt.Errorf("task-index template is invalid or missing: %w", err)
	}
	return payload, nil
}

func expandTaskControlUIContracts(root string, tasks []any) ([]any, error) {
	var defaults map[string]any
	for _, value := range tasks {
		task := value.(map[string]any)
		rawUI, exists := task["ui_contract"]
		if !exists || rawUI == nil {
			continue
		}
		ui, ok := rawUI.(map[string]any)
		if !ok {
			return nil, fmt.Errorf("%s ui_contract must be a JSON object", task["id"])
		}
		if len(ui) == 0 {
			continue
		}
		if defaults == nil {
			packetTemplate, err := readImplementJSONMap(filepath.Join(root, ".specify", "templates", "task-packet-template.json"))
			if err != nil {
				return nil, fmt.Errorf("task-packet template is invalid or missing: %w", err)
			}
			var defaultsOK bool
			defaults, defaultsOK = packetTemplate["ui_contract"].(map[string]any)
			if !defaultsOK || len(defaults) == 0 {
				return nil, fmt.Errorf("task-packet template ui_contract must be a non-empty JSON object")
			}
		}
		expanded := cloneJSONMap(defaults)
		for key, item := range ui {
			if _, supported := defaults[key]; !supported {
				return nil, fmt.Errorf("%s ui_contract contains unsupported field %q", task["id"], key)
			}
			expanded[key] = cloneJSONValue(item)
		}
		task["ui_contract"] = expanded
	}
	return tasks, nil
}

func loadTaskControlPackage(root, feature string) (map[string]any, string, error) {
	payload, err := readImplementJSONMap(filepath.Join(feature, "task-index.json"))
	if err != nil {
		return nil, "", fmt.Errorf("task-index.json is invalid or missing: %w", err)
	}
	if intFromAny(payload["version"]) != 2 {
		return nil, "", fmt.Errorf("task-index.json must use version 2")
	}
	tasks, err := normalizeTaskControlTasks(payload["tasks"], true)
	if err != nil {
		return nil, "", err
	}
	tasks, err = expandTaskControlUIContracts(root, tasks)
	if err != nil {
		return nil, "", err
	}
	payload["tasks"] = tasks
	title := filepath.Base(feature)
	if raw, readErr := os.ReadFile(filepath.Join(feature, "tasks.md")); readErr == nil {
		first, _, _ := strings.Cut(string(raw), "\n")
		if strings.HasPrefix(first, "# Tasks:") {
			if parsed := strings.TrimSpace(strings.TrimPrefix(first, "# Tasks:")); parsed != "" {
				title = parsed
			}
		}
	}
	return payload, title, nil
}

func normalizeTaskControlTasks(value any, allowRuntimeFields bool) ([]any, error) {
	raw, ok := value.([]any)
	if !ok {
		return nil, fmt.Errorf("tasks must be an array")
	}
	result := make([]any, 0, len(raw))
	seen := map[string]bool{}
	for _, item := range raw {
		task, err := normalizeTaskControlTask(item, allowRuntimeFields)
		if err != nil {
			return nil, err
		}
		id := task["id"].(string)
		if seen[id] {
			return nil, fmt.Errorf("duplicate task id: %s", id)
		}
		seen[id] = true
		result = append(result, task)
	}
	return result, nil
}

func normalizeTaskControlTask(value any, allowRuntimeFields bool) (map[string]any, error) {
	raw, ok := value.(map[string]any)
	if !ok {
		return nil, fmt.Errorf("each task must be a JSON object")
	}
	task := cloneJSONMap(raw)
	for key := range task {
		if taskControlObsoleteFields[key] {
			return nil, fmt.Errorf("task contains obsolete field %s", key)
		}
		if !allowRuntimeFields && taskControlRuntimeFields[key] {
			return nil, fmt.Errorf("task field %s is CLI-owned and cannot be authored", key)
		}
		if !allowRuntimeFields && !taskControlAuthoredFields[key] {
			return nil, fmt.Errorf("task contains unsupported field %q", key)
		}
	}
	idValue := task["id"]
	if idValue == nil {
		idValue = task["task_id"]
	}
	id, err := normalizeTaskControlID(anyString(idValue))
	if err != nil {
		return nil, err
	}
	objective := strings.TrimSpace(anyString(task["objective"]))
	if objective == "" {
		return nil, fmt.Errorf("%s objective is required", id)
	}
	delete(task, "task_id")
	task["id"] = id
	task["objective"] = objective
	dependencies := task["dependencies"]
	if dependencies == nil {
		dependencies = task["depends_on"]
	}
	dependencyValues, err := taskControlStringList(dependencies, id+" dependencies")
	if err != nil {
		return nil, err
	}
	for index, dependency := range dependencyValues {
		dependencyValues[index], err = normalizeTaskControlID(dependency)
		if err != nil {
			return nil, err
		}
	}
	task["dependencies"] = stringsToAny(dependencyValues)
	delete(task, "depends_on")
	writeScope := task["expected_write_scope"]
	if writeScope == nil {
		writeScope = task["write_scope"]
	}
	writeValues, err := taskControlStringList(writeScope, id+" expected_write_scope")
	if err != nil {
		return nil, err
	}
	if err := validateTaskControlProductScope(id, "expected_write_scope", writeValues); err != nil {
		return nil, err
	}
	task["expected_write_scope"] = stringsToAny(writeValues)
	delete(task, "write_scope")
	for _, key := range []string{
		"read_scope", "required_refs", "authoritative_refs", "policy_refs", "forbidden_drift", "hard_rules",
		"acceptance", "verification", "required_validation", "task_checks", "consumer_surfaces", "required_consumer_evidence",
		"required_evidence", "must_preserve_ids", "must_preserve_refs",
		"consequence_obligation_ids", "consequence_obligation_refs",
		"capability_operations", "capability_operation_refs", "fidelity_refs",
		"acceptance_refs", "user_confirmed_deferral_refs", "stop_and_reopen_conditions", "skills",
	} {
		if _, exists := task[key]; !exists {
			continue
		}
		values, listErr := taskControlStringList(task[key], id+" "+key)
		if listErr != nil {
			return nil, listErr
		}
		if key == "read_scope" {
			if scopeErr := validateTaskControlProductScope(id, key, values); scopeErr != nil {
				return nil, scopeErr
			}
		}
		task[key] = stringsToAny(values)
	}
	status := strings.ToLower(strings.TrimSpace(anyString(task["status"])))
	if status == "" {
		status = "pending"
	}
	valid := map[string]bool{
		"pending": true, "ready": true, "in_progress": true, "implemented": true,
		"accepted": true, "blocked": true, "failed": true, "deferred": true,
	}
	if !valid[status] {
		return nil, fmt.Errorf("%s status is invalid: %s", id, status)
	}
	task["status"] = status
	return task, nil
}

var taskControlWorkflowScopeOwners = map[string]string{
	"design.md":                   "specify-runtime design",
	"alignment.md":                "specify-runtime artifact",
	"context.md":                  "specify-runtime artifact",
	"data-model.md":               "specify-runtime artifact",
	"deep-research.md":            "specify-runtime artifact",
	"handoff-to-implement.json":   "specify-runtime tasks handoff",
	"handoff-to-tasks.json":       "specify-runtime tasks handoff",
	"human-acceptance.json":       "specify-runtime accept",
	"implementation-handoff.json": "specify-runtime implement closeout",
	"implementation-summary.md":   "specify-runtime implement closeout",
	"implement-tracker.md":        "specify-runtime implement",
	"plan-contract.json":          "specify-runtime artifact",
	"plan.md":                     "specify-runtime artifact",
	"quickstart.md":               "specify-runtime artifact",
	"references.md":               "specify-runtime artifact",
	"research.md":                 "specify-runtime artifact",
	"review-state.json":           "specify-runtime review",
	"semantic-audit-input.json":   "specify-runtime cognition semantic-audit",
	"semantic-audit-output.json":  "specify-runtime cognition semantic-audit",
	"spec-contract.json":          "specify-runtime artifact",
	"spec.md":                     "specify-runtime artifact",
	"specify-draft.md":            "specify-runtime artifact",
	"task-index.json":             "specify-runtime tasks",
	"tasks.md":                    "specify-runtime tasks",
	"ui-brief.md":                 "specify-runtime artifact",
	"ui-reference-notes.md":       "specify-runtime artifact",
	"ui-target.html":              "specify-runtime design ui-target",
	"workflow-state.md":           "specify-runtime artifact",
	"workflow.json":               "specify-runtime workflow",
}

func taskControlWorkflowScopeOwner(value string) (string, bool) {
	normalized := strings.Trim(strings.TrimSpace(value), "`'\"")
	if fragment := strings.Index(normalized, "#"); fragment >= 0 {
		normalized = normalized[:fragment]
	}
	normalized = strings.TrimPrefix(filepath.ToSlash(filepath.Clean(filepath.FromSlash(normalized))), "./")
	normalizedLower := strings.ToLower(normalized)
	if owner, ok := taskControlWorkflowScopeOwners[normalizedLower]; ok {
		return owner, true
	}
	if metadata, ok := LookupArtifactType(normalized); ok {
		return metadata.Owner, true
	}
	for _, prefix := range []string{
		".specify/",
		".planning/debug/",
		".planning/learnings/",
		".planning/quick/",
	} {
		if strings.HasPrefix(normalizedLower, prefix) {
			return "specify-runtime registered owner", true
		}
	}
	return "", false
}

func validateTaskControlProductScope(taskID, field string, values []string) error {
	for _, value := range values {
		if owner, owned := taskControlWorkflowScopeOwner(value); owned {
			return fmt.Errorf("%s %s contains CLI-owned workflow artifact %q; use %s instead", taskID, field, value, owner)
		}
	}
	return nil
}

func taskControlStringList(value any, label string) ([]string, error) {
	if value == nil {
		return []string{}, nil
	}
	raw, ok := value.([]any)
	if !ok {
		return nil, fmt.Errorf("%s must be an array", label)
	}
	result := []string{}
	seen := map[string]bool{}
	for _, item := range raw {
		text := strings.TrimSpace(anyString(item))
		if text == "" {
			return nil, fmt.Errorf("%s must contain non-empty strings", label)
		}
		if !seen[text] {
			result = append(result, text)
			seen[text] = true
		}
	}
	return result, nil
}

func normalizeTaskControlID(value string) (string, error) {
	normalized := strings.ToUpper(strings.TrimSpace(value))
	if !taskControlIDRE.MatchString(normalized) {
		return "", fmt.Errorf("task id must match T<digits>: %q", value)
	}
	return normalized, nil
}

func taskControlStatus(task map[string]any) string {
	status := strings.ToLower(strings.TrimSpace(anyString(task["status"])))
	if status == "" {
		return "pending"
	}
	return status
}

func markTaskControlDraft(payload map[string]any, blocker string) {
	payload["status"] = "draft"
	transition, ok := payload["transition"].(map[string]any)
	if !ok {
		transition = map[string]any{}
		payload["transition"] = transition
	}
	transition["status"] = "blocked"
	transition["blockers"] = []any{blocker}
	transition["next_action"] = "Run `specify-runtime tasks finalize`."
}

func validateTaskControlGraph(tasks []any) error {
	byID := map[string]map[string]any{}
	for _, value := range tasks {
		task := value.(map[string]any)
		byID[task["id"].(string)] = task
	}
	for id, task := range byID {
		for _, dependency := range anyStringSlice(task["dependencies"]) {
			if dependency == id {
				return fmt.Errorf("%s cannot depend on itself", id)
			}
			if byID[dependency] == nil {
				return fmt.Errorf("%s references unknown dependency %s", id, dependency)
			}
		}
	}
	visiting := map[string]bool{}
	visited := map[string]bool{}
	var visit func(string) error
	visit = func(id string) error {
		if visited[id] {
			return nil
		}
		if visiting[id] {
			return fmt.Errorf("task dependency cycle contains %s", id)
		}
		visiting[id] = true
		for _, dependency := range anyStringSlice(byID[id]["dependencies"]) {
			if err := visit(dependency); err != nil {
				return err
			}
		}
		delete(visiting, id)
		visited[id] = true
		return nil
	}
	ids := make([]string, 0, len(byID))
	for id := range byID {
		ids = append(ids, id)
	}
	sort.Strings(ids)
	for _, id := range ids {
		if err := visit(id); err != nil {
			return err
		}
	}
	return nil
}

func validateTaskControlAcceptance(feature string, payload map[string]any) error {
	planPath := filepath.Join(feature, "plan-contract.json")
	if !pathExists(planPath) {
		planPath = filepath.Join(feature, "plan", "plan-contract.json")
	}
	if !pathExists(planPath) {
		return nil
	}
	plan, err := readImplementJSONMap(planPath)
	if err != nil {
		return fmt.Errorf("plan-contract.json is invalid: %w", err)
	}
	expected, ok := plan["acceptance_refs"].([]any)
	if !ok {
		return fmt.Errorf("plan-contract acceptance_refs must be an array")
	}
	actual, ok := payload["acceptance_refs"].([]any)
	if !ok || !reflect.DeepEqual(actual, expected) {
		return fmt.Errorf("task-index acceptance_refs must exactly preserve plan-contract order")
	}
	if len(expected) == 0 {
		return nil
	}
	for _, field := range []string{
		"official_entrypoints", "system_review_scenarios", "review_obligations",
		"human_acceptance_obligations", "human_acceptance_scenarios",
	} {
		values, ok := payload[field].([]any)
		if !ok || len(values) == 0 {
			return fmt.Errorf("task-index %s is required when acceptance_refs are present", field)
		}
	}
	return nil
}

func commitTaskControlPackage(root, feature string, payload map[string]any, title, kind string) (map[string]any, error) {
	indexBytes, err := marshalTaskControlJSON(payload)
	if err != nil {
		return nil, err
	}
	markdown, err := renderTaskControlMarkdown(payload, title)
	if err != nil {
		return nil, err
	}
	receipt, err := applyFileTransaction(root, kind, []fileTransactionUpdate{
		{Path: filepath.Join(feature, "task-index.json"), Content: indexBytes, Perm: 0o644},
		{Path: filepath.Join(feature, "tasks.md"), Content: []byte(markdown), Perm: 0o644},
	})
	if err != nil {
		return nil, err
	}
	result := fileTransactionReceiptMap(receipt)
	result["status"] = "ok"
	result["package_status"] = payload["status"]
	result["task_count"] = len(payload["tasks"].([]any))
	for _, path := range receipt.ChangedPaths {
		if strings.HasSuffix(path, "/task-index.json") || path == "task-index.json" {
			result["task_index_ref"] = path
		}
		if strings.HasSuffix(path, "/tasks.md") || path == "tasks.md" {
			result["tasks_ref"] = path
		}
	}
	result["task_index_sha256"] = taskControlSHA256(indexBytes)
	result["tasks_sha256"] = taskControlSHA256([]byte(markdown))
	return result, nil
}

func renderTaskControlMarkdown(payload map[string]any, title string) (string, error) {
	tasks, ok := payload["tasks"].([]any)
	if !ok {
		return "", fmt.Errorf("task-index tasks must be an array")
	}
	lines := []string{
		"# Tasks: " + title,
		"",
		"> Generated by `specify-runtime tasks`; `task-index.json` is canonical.",
		"",
		"## Task List",
		"",
	}
	for _, value := range tasks {
		task := value.(map[string]any)
		checked := " "
		if taskControlTerminalStatuses[taskControlStatus(task)] {
			checked = "x"
		}
		markers := []string{}
		if parallel, _ := task["parallel"].(bool); parallel {
			markers = append(markers, "[P]")
		}
		if story := strings.TrimSpace(anyString(task["story_id"])); story != "" {
			markers = append(markers, "["+story+"]")
		}
		marker := ""
		if len(markers) > 0 {
			marker = " " + strings.Join(markers, " ")
		}
		lines = append(lines, fmt.Sprintf("- [%s] %s%s %s", checked, task["id"], marker, task["objective"]))
	}
	lines = append(lines, "", "## Consequence Obligation Mapping", "", "| Obligation ID | Task IDs |", "| --- | --- |")
	obligations := map[string][]string{}
	for _, value := range tasks {
		task := value.(map[string]any)
		ids := anyStringSlice(task["consequence_obligation_ids"])
		if len(ids) == 0 {
			ids = anyStringSlice(task["consequence_obligation_refs"])
		}
		for _, id := range ids {
			obligations[id] = append(obligations[id], task["id"].(string))
		}
	}
	if len(obligations) == 0 {
		lines = append(lines, "| None | None |")
	} else {
		ids := make([]string, 0, len(obligations))
		for id := range obligations {
			ids = append(ids, id)
		}
		sort.Strings(ids)
		for _, id := range ids {
			lines = append(lines, fmt.Sprintf("| %s | %s |", id, strings.Join(obligations[id], ", ")))
		}
	}
	for _, value := range tasks {
		task := value.(map[string]any)
		id := task["id"].(string)
		lines = append(lines,
			"", "## "+id+" — "+task["objective"].(string), "", "### Scope Boundaries", "",
			"| Field | Value |", "| --- | --- |",
			"| read_scope | "+taskControlRenderList(task["read_scope"])+" |",
			"| write_scope | "+taskControlRenderList(task["expected_write_scope"])+" |",
			"| required_refs | "+taskControlRenderList(task["required_refs"])+" |",
			"| dependencies | "+taskControlRenderList(task["dependencies"])+" |",
			"", "### Acceptance and Verification", "",
			"- Acceptance: "+taskControlRenderList(task["acceptance"]),
			"- Verification: "+taskControlRenderList(task["verification"]),
		)
		if ui, ok := task["ui_contract"].(map[string]any); ok && len(ui) > 0 {
			lines = append(lines,
				"", "### UI Implementation Contract", "", "| Field | Value |", "| --- | --- |",
				"| ui_contract_ref | task-index.json#/tasks/"+id+"/ui_contract |",
				"| fidelity_level | "+defaultString(anyString(ui["fidelity_level"]), "none")+" |",
				"| required_states | "+taskControlRenderList(ui["required_states"])+" |",
				"| required_evidence | "+taskControlRenderList(ui["required_evidence"])+" |",
			)
		}
	}
	return strings.TrimRight(strings.Join(lines, "\n"), "\n") + "\n", nil
}

func taskControlRenderList(value any) string {
	values := anyStringSlice(value)
	if len(values) == 0 {
		return "none"
	}
	quoted := make([]string, len(values))
	for index, value := range values {
		quoted[index] = "`" + value + "`"
	}
	return strings.Join(quoted, ", ")
}

func marshalTaskControlJSON(payload any) ([]byte, error) {
	raw, err := json.MarshalIndent(payload, "", "  ")
	if err != nil {
		return nil, err
	}
	return append(raw, '\n'), nil
}

func anyString(value any) string {
	if value == nil {
		return ""
	}
	if text, ok := value.(string); ok {
		return text
	}
	return fmt.Sprint(value)
}

func taskControlSHA256(raw []byte) string {
	sum := sha256.Sum256(raw)
	return hex.EncodeToString(sum[:])
}

func fileTransactionReceiptMap(receipt fileTransactionReceipt) map[string]any {
	return map[string]any{
		"transaction_id": receipt.TransactionID,
		"kind":           receipt.Kind,
		"changed_paths":  receipt.ChangedPaths,
		"receipt_ref":    receipt.ReceiptRef,
	}
}

func pathExists(path string) bool {
	_, err := os.Stat(path)
	return err == nil
}
