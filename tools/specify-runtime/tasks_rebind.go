package main

import (
	"encoding/json"
	"fmt"
	"net/url"
	"os"
	"path/filepath"
	"reflect"
	"sort"
	"strings"
)

// A rebind is a guarded forward migration of an existing package. It never
// rebuilds execution history or chooses a newer unadopted Design for a feature.
func runTasksRebind(args []string) (map[string]any, error) {
	parsed, err := parseCoordinationCommandArgs(args, 0, "--feature-dir", "--expected-task-index-sha256", "--expected-workflow-revision", "--expected-test-design-handoff-sha256", "--reason", "--task-updates-json", "--format")
	if err != nil {
		return nil, err
	}
	if err := parsed.validateJSONFormat(); err != nil {
		return nil, err
	}
	root, feature, err := taskControlFeature(args)
	if err != nil {
		return nil, err
	}
	expectedIndex := strings.TrimSpace(optionValue(args, "--expected-task-index-sha256", ""))
	expectedHandoff := strings.TrimSpace(optionValue(args, "--expected-test-design-handoff-sha256", ""))
	if !hexDigestRE.MatchString(expectedIndex) || !hexDigestRE.MatchString(expectedHandoff) {
		return nil, fmt.Errorf("tasks rebind requires SHA-256 --expected-task-index-sha256 and --expected-test-design-handoff-sha256")
	}
	expectedRevision, ok := intOption(args, "--expected-workflow-revision")
	if !ok || expectedRevision < 0 {
		return nil, fmt.Errorf("tasks rebind requires a non-negative --expected-workflow-revision (0 when workflow.json is absent)")
	}
	reason := strings.TrimSpace(optionValue(args, "--reason", ""))
	if reason == "" {
		return nil, fmt.Errorf("tasks rebind requires --reason")
	}
	updates := map[string]any{}
	if _, exists := parsed.options["--task-updates-json"]; exists {
		updates, err = taskControlInlineObject(args, "--task-updates-json", "task rebind updates")
		if err != nil {
			return nil, err
		}
	}
	snapshot := &taskRebindSnapshot{root: root, files: map[string][]byte{}}
	indexPath := filepath.Join(feature, "task-index.json")
	indexRaw, err := snapshot.read(indexPath, true)
	if err != nil {
		return nil, err
	}
	if taskControlSHA256(indexRaw) != expectedIndex {
		return nil, fmt.Errorf("task-index digest is stale; inspect the current package before rebinding")
	}
	var index map[string]any
	if err := json.Unmarshal(indexRaw, &index); err != nil || index == nil || intFromAny(index["version"]) != 2 {
		return nil, fmt.Errorf("tasks rebind requires an existing version-2 task-index.json")
	}
	// Validate canonical shape on a copy; terminal task objects remain exact.
	normalized, err := normalizeTaskControlTasks(index["tasks"], true)
	if err != nil || len(normalized) == 0 {
		return nil, fmt.Errorf("tasks rebind requires a valid non-empty task graph: %v", err)
	}
	tasks, _ := index["tasks"].([]any)
	if err := validateTaskControlGraph(normalized); err != nil {
		return nil, err
	}
	if _, err := snapshot.read(filepath.Join(feature, "workflow.json"), false); err != nil {
		return nil, err
	}
	workflow, err := loadImplementWorkflowSnapshot(root, feature)
	if err != nil {
		return nil, err
	}
	if workflow.Revision != expectedRevision {
		return nil, fmt.Errorf("workflow revision is stale: expected %d but current revision is %d", expectedRevision, workflow.Revision)
	}
	if workflow.Present && workflow.Stage != "tasks" && workflow.Stage != "implement" {
		return nil, fmt.Errorf("tasks rebind requires workflow stage tasks or implement; reopen the owning stage first")
	}
	tasksRaw, err := snapshot.read(filepath.Join(feature, "tasks.md"), true)
	if err != nil {
		return nil, err
	}
	title := filepath.Base(feature)
	if first, _, _ := strings.Cut(string(tasksRaw), "\n"); strings.HasPrefix(first, "# Tasks:") {
		title = strings.TrimSpace(strings.TrimPrefix(first, "# Tasks:"))
	}
	for _, name := range []string{"plan-contract.json", "plan/plan-contract.json", "spec-contract.json", "implementation-review/execution-state.json"} {
		if _, err := snapshot.read(filepath.Join(feature, filepath.FromSlash(name)), false); err != nil {
			return nil, err
		}
	}
	planPath := filepath.Join(feature, "plan-contract.json")
	if snapshot.files[planPath] == nil {
		planPath = filepath.Join(feature, "plan", "plan-contract.json")
	}
	var plan map[string]any
	if raw := snapshot.files[planPath]; raw != nil {
		if err := json.Unmarshal(raw, &plan); err != nil || plan == nil {
			return nil, fmt.Errorf("plan-contract.json is invalid")
		}
	}

	preserved := []string{}
	refreshedUI := []string{}
	seenUpdates := map[string]bool{}
	var projectedUI map[string]any
	unstartedUI := 0
	for _, value := range tasks {
		task := value.(map[string]any)
		if taskControlTerminalStatuses[taskControlStatus(task)] {
			continue
		}
		currentUI, _ := task["ui_contract"].(map[string]any)
		patch, _ := updates[anyString(task["id"])].(map[string]any)
		if _, explicit := patch["ui_contract"]; explicit || taskRebindUIApplicable(currentUI) {
			unstartedUI++
		}
	}
	for position, value := range tasks {
		task, ok := value.(map[string]any)
		if !ok {
			return nil, fmt.Errorf("task index must contain task objects")
		}
		id := anyString(task["id"])
		status := taskControlStatus(task)
		lifecyclePath := filepath.Join(feature, "implementation-review", "tasks", id+".json")
		lifecycleRaw, err := snapshot.read(lifecyclePath, false)
		if err != nil {
			return nil, err
		}
		if _, err := snapshot.read(filepath.Join(feature, "worker-results", id+".json"), false); err != nil {
			return nil, err
		}
		if lifecycleRaw != nil {
			var lifecycle map[string]any
			if json.Unmarshal(lifecycleRaw, &lifecycle) != nil || lifecycle == nil || anyString(lifecycle["task_id"]) != id || taskControlStatus(lifecycle) != status {
				return nil, fmt.Errorf("%s lifecycle identity/status disagrees with the task index", id)
			}
		}
		if taskControlTerminalStatuses[status] {
			if _, exists := updates[id]; exists {
				return nil, fmt.Errorf("%s is %s; rebind preserves terminal tasks and cannot alter their contracts", id, status)
			}
			preserved = append(preserved, id)
			continue
		}
		if status != "pending" && status != "ready" {
			return nil, fmt.Errorf("%s is %s; finish or recover started task execution before rebinding", id, status)
		}
		patch := map[string]any{}
		if raw, exists := updates[id]; exists {
			var ok bool
			patch, ok = raw.(map[string]any)
			if !ok || len(patch) == 0 {
				return nil, fmt.Errorf("%s rebind update must be a non-empty object", id)
			}
			seenUpdates[id] = true
			for field := range patch {
				if field != "test_case_refs" && field != "test_data_refs" && field != "ui_contract" {
					return nil, fmt.Errorf("tasks rebind cannot change %s.%s", id, field)
				}
			}
		}
		for _, field := range []string{"test_case_refs", "test_data_refs"} {
			if value, exists := patch[field]; exists {
				refs, err := taskRebindStrictRefs(value, id+" "+field)
				if err != nil {
					return nil, err
				}
				task[field] = stringsToAny(refs)
			}
		}
		currentUI, _ := task["ui_contract"].(map[string]any)
		_, updateUI := patch["ui_contract"]
		if updateUI || taskRebindUIApplicable(currentUI) {
			if projectedUI == nil {
				projectedUI, err = taskRebindPlanUI(root, feature, plan, snapshot)
				if err != nil {
					return nil, err
				}
			}
			selected, err := taskRebindSelectUI(currentUI, projectedUI, patch["ui_contract"], updateUI, unstartedUI > 1)
			if err != nil {
				return nil, fmt.Errorf("%s: %w", id, err)
			}
			task["ui_contract"] = selected
			refreshedUI = append(refreshedUI, id)
		}
		tasks[position] = task
	}
	for id := range updates {
		if !seenUpdates[id] {
			return nil, fmt.Errorf("task rebind update %q does not identify an unstarted task", id)
		}
	}
	if projectedUI != nil {
		for _, field := range []string{"design_decision_ids", "handoff_contract_ids"} {
			covered := map[string]bool{}
			for _, value := range tasks {
				taskUI, _ := value.(map[string]any)["ui_contract"].(map[string]any)
				if taskUI["design_change_sha256"] == projectedUI["design_change_sha256"] {
					for _, id := range anyStringSlice(taskUI[field]) {
						covered[id] = true
					}
				}
			}
			if !stringSetEqual(covered, stringSliceSet(anyStringSlice(projectedUI[field]))) {
				return nil, fmt.Errorf("rebound UI tasks must cover all and only adopted Plan %s", field)
			}
		}
	}
	// Freeze producer inputs before validating them, and compare every byte again
	// under the shared file transaction lock before publication.
	producer := filepath.Join(feature, "test-design")
	if err := snapshot.tree(producer); err != nil {
		return nil, err
	}
	verifySources, err := taskRebindSourceVerification(root, snapshot.files[filepath.Join(producer, "test-state.json")])
	if err != nil {
		return nil, err
	}
	if err := taskControlValidateTestDesignBinding(root, feature, index, true, true); err != nil {
		return nil, err
	}
	if anyString(index["test_design_handoff_sha256"]) != expectedHandoff {
		return nil, fmt.Errorf("Test Design handoff digest is stale or missing; verify the current producer handoff before rebinding")
	}
	if err := validateTaskControlAcceptance(feature, index); err != nil {
		return nil, err
	}
	if plan != nil && plan["source_revision"] != nil {
		index["source_revision"] = cloneJSONValue(plan["source_revision"])
	}
	index["status"] = "ready"
	index["transition"] = map[string]any{
		"version": 1, "status": "ready", "source_ref": "task-index.json",
		"required_refs": cloneJSONValue(index["acceptance_refs"]), "blockers": []any{},
		"next_action": "Run sp-implement or spx-implement.", "recovery": nil,
	}
	indexBytes, err := marshalTaskControlJSON(index)
	if err != nil {
		return nil, err
	}
	markdown, err := renderTaskControlMarkdown(index, title)
	if err != nil {
		return nil, err
	}
	publication := []fileTransactionUpdate{
		{Path: indexPath, Content: indexBytes, Perm: 0o644},
		{Path: filepath.Join(feature, "tasks.md"), Content: []byte(markdown), Perm: 0o644},
	}
	for _, target := range []string{"tasks", "implement"} {
		path := filepath.Join(feature, "handoff-to-"+target+".json")
		if _, err := snapshot.read(path, false); err != nil {
			return nil, err
		}
		raw, err := marshalTaskControlJSON(taskControlHandoff(index, indexBytes, target))
		if err != nil {
			return nil, err
		}
		publication = append(publication, fileTransactionUpdate{Path: path, Content: raw, Perm: 0o644})
	}
	// Previously compiled unstarted packets must not remain usable with an old
	// binding after a successful rebind. Keep completed packets as history.
	for position, value := range tasks {
		task := value.(map[string]any)
		if taskControlTerminalStatuses[taskControlStatus(task)] {
			continue
		}
		id := anyString(task["id"])
		packetPath := filepath.Join(feature, "implementation-review", "packets", id+".json")
		raw, err := snapshot.read(packetPath, false)
		if err != nil {
			return nil, err
		}
		if raw != nil {
			packet, err := buildImplementTaskPacket(root, feature, id, index, position, task)
			if err != nil {
				return nil, err
			}
			packetRaw, err := marshalTaskControlJSON(packet)
			if err != nil {
				return nil, err
			}
			publication = append(publication, fileTransactionUpdate{Path: packetPath, Content: packetRaw, Perm: 0o644})
		}
	}
	previous := map[string]any{}
	for _, update := range publication {
		ref := projectRelativeSlash(root, update.Path)
		if raw := snapshot.files[update.Path]; raw != nil {
			previous[ref] = map[string]any{"sha256": taskControlSHA256(raw), "content": string(raw)}
		} else {
			previous[ref] = nil
		}
	}
	history := map[string]any{
		"version": 1, "kind": "tasks.rebind", "reason": reason,
		"workflow_revision": workflow.Revision, "previous_task_index_sha256": expectedIndex,
		"task_index_sha256": taskControlSHA256(indexBytes), "test_design_handoff_sha256": expectedHandoff,
		"preserved_task_ids": preserved, "refreshed_ui_task_ids": refreshedUI, "previous_files": previous,
	}
	historyBytes, err := marshalTaskControlJSON(history)
	if err != nil {
		return nil, err
	}
	historySHA := taskControlSHA256(historyBytes)
	historyPath := filepath.Join(feature, "task-rebind-history", historySHA+".json")
	if prior, err := snapshot.read(historyPath, false); err != nil || prior != nil {
		return nil, fmt.Errorf("task rebind history already exists or is unsafe; inspect the previous transaction before retrying: %v", err)
	}
	publication = append(publication, fileTransactionUpdate{Path: historyPath, Content: historyBytes, Perm: 0o644})
	receipt, err := applyFileTransactionWithVerification(root, "tasks.rebind", publication, snapshot.preconditions(), verifySources)
	if err != nil {
		return nil, err
	}
	result := fileTransactionReceiptMap(receipt)
	result["status"] = "ok"
	result["task_count"] = len(tasks)
	result["task_index_sha256"] = taskControlSHA256(indexBytes)
	result["test_design_handoff_sha256"] = expectedHandoff
	result["workflow_revision"] = workflow.Revision
	result["history_ref"] = projectRelativeSlash(root, historyPath)
	result["history_sha256"] = historySHA
	result["preserved_task_ids"] = preserved
	result["refreshed_ui_task_ids"] = refreshedUI
	return result, nil
}

// Parse the frozen producer state rather than accepting a later state with a
// different source boundary. Recompute both file bytes and included-directory
// membership under the transaction lock immediately before publication.
func taskRebindSourceVerification(root string, frozenRaw []byte) (func() error, error) {
	var state testDesignState
	if err := json.Unmarshal(frozenRaw, &state); err != nil || state.SchemaVersion != testDesignStateSchema ||
		state.Revision < 1 || state.ArtifactRoot == "" || !hexDigestRE.MatchString(state.Source.Fingerprint) {
		return nil, fmt.Errorf("tasks rebind requires a canonical frozen Test Design state")
	}
	return func() error {
		if err := (testDesignService{projectRoot: root}).requireFreshSources(state); err != nil {
			return fmt.Errorf("Test Design sources changed before tasks rebind publication: %w", err)
		}
		return nil
	}, nil
}

func taskControlHandoff(index map[string]any, raw []byte, target string) map[string]any {
	handoff := map[string]any{
		"version": 1, "status": "ready", "target": target, "task_index_ref": "task-index.json",
		"tasks_ref": "tasks.md", "task_index_sha256": taskControlSHA256(raw),
		"source_revision": cloneJSONValue(index["source_revision"]), "task_count": len(index["tasks"].([]any)),
	}
	for field := range taskControlTestDesignRootFields {
		handoff[field] = cloneJSONValue(index[field])
	}
	return handoff
}

// Handoffs are required for Test Design consumers. Legacy unbound task packages
// still validate without a compatibility handoff, but an existing handoff must
// always match the canonical index.
func validateTaskControlFreshness(root, feature string, index map[string]any) error {
	transition, _ := index["transition"].(map[string]any)
	if taskControlStatus(index) != "ready" || anyString(transition["status"]) != "ready" {
		return fmt.Errorf("task package must be finalized before workflow completion")
	}
	tasks, _ := index["tasks"].([]any)
	if len(tasks) == 0 {
		return fmt.Errorf("task package must contain at least one task")
	}
	if err := validateTaskControlGraph(tasks); err != nil {
		return err
	}
	if err := taskControlValidateTestDesignBinding(root, feature, index, false, true); err != nil {
		return err
	}
	raw, err := secureProjectReadFile(root, projectRelativeSlash(root, filepath.Join(feature, "task-index.json")))
	if err != nil {
		return err
	}
	markdown, err := secureProjectReadFile(root, projectRelativeSlash(root, filepath.Join(feature, "tasks.md")))
	if err != nil {
		return err
	}
	title := filepath.Base(feature)
	if first, _, _ := strings.Cut(string(markdown), "\n"); strings.HasPrefix(first, "# Tasks:") {
		title = strings.TrimSpace(strings.TrimPrefix(first, "# Tasks:"))
	}
	expectedMarkdown, err := renderTaskControlMarkdown(index, title)
	if err != nil {
		return err
	}
	if string(markdown) != expectedMarkdown {
		return fmt.Errorf("tasks.md is stale relative to its canonical task index; finalize or rebind Tasks before completing the stage")
	}
	for _, target := range []string{"tasks", "implement"} {
		ref := projectRelativeSlash(root, filepath.Join(feature, "handoff-to-"+target+".json"))
		handoffRaw, err := secureProjectReadFile(root, ref)
		if os.IsNotExist(err) && (target == "tasks" || taskControlTestDesignBindingEmpty(index)) {
			continue
		}
		if err != nil {
			return fmt.Errorf("task handoff %s is missing or unsafe: %w", target, err)
		}
		var actual map[string]any
		if json.Unmarshal(handoffRaw, &actual) != nil || canonicalJSONSHA256(actual) != canonicalJSONSHA256(taskControlHandoff(index, raw, target)) {
			return fmt.Errorf("task handoff %s is stale; regenerate it with tasks handoff or guarded tasks rebind", target)
		}
	}
	return nil
}

type taskRebindSnapshot struct {
	root  string
	files map[string][]byte // nil records absence as a CAS precondition.
}

func (snapshot *taskRebindSnapshot) read(path string, required bool) ([]byte, error) {
	path = filepath.Clean(path)
	if raw, ok := snapshot.files[path]; ok {
		if required && raw == nil {
			return nil, fmt.Errorf("required rebind input %s is missing", path)
		}
		return raw, nil
	}
	raw, err := secureProjectReadFile(snapshot.root, projectRelativeSlash(snapshot.root, path))
	if os.IsNotExist(err) && !required {
		snapshot.files[path] = nil
		return nil, nil
	}
	if err != nil {
		return nil, fmt.Errorf("read rebind input %s: %w", path, err)
	}
	snapshot.files[path] = raw
	return raw, nil
}

func (snapshot *taskRebindSnapshot) tree(root string) error {
	return filepath.WalkDir(root, func(path string, entry os.DirEntry, err error) error {
		if err != nil {
			return err
		}
		if entry.IsDir() {
			// Old generations are immutable history, not current binding inputs.
			if path != root && (entry.Name() == "history" || entry.Name() == "archive") {
				return filepath.SkipDir
			}
			return nil
		}
		_, err = snapshot.read(path, true)
		return err
	})
}

func (snapshot *taskRebindSnapshot) preconditions() []fileTransactionPrecondition {
	paths := make([]string, 0, len(snapshot.files))
	for path := range snapshot.files {
		paths = append(paths, path)
	}
	sort.Strings(paths)
	result := make([]fileTransactionPrecondition, 0, len(paths))
	for _, path := range paths {
		condition := fileTransactionPrecondition{Path: path, MustNotExist: snapshot.files[path] == nil}
		if !condition.MustNotExist {
			condition.ExpectedSHA256 = taskControlSHA256(snapshot.files[path])
		}
		result = append(result, condition)
	}
	return result
}

func taskRebindUIApplicable(ui map[string]any) bool {
	return ui != nil && (anyString(ui["fidelity_level"]) != "" && anyString(ui["fidelity_level"]) != "none" ||
		anyString(ui["ui_work_type"]) != "" || anyString(ui["design_change_id"]) != "" ||
		len(anyStringSlice(ui["design_sources"])) > 0 || len(designAnyList(ui["surface_catalog"])) > 0)
}

func taskRebindStrictRefs(value any, label string) ([]string, error) {
	rows, ok := value.([]any)
	if !ok {
		return nil, fmt.Errorf("%s must be an array of unique canonical strings", label)
	}
	refs := make([]string, 0, len(rows))
	seen := map[string]bool{}
	for _, value := range rows {
		ref, ok := value.(string)
		if !ok || strings.TrimSpace(ref) == "" || ref != strings.TrimSpace(ref) || seen[ref] {
			return nil, fmt.Errorf("%s must contain unique non-empty canonical strings without surrounding whitespace", label)
		}
		seen[ref] = true
		refs = append(refs, ref)
	}
	return refs, nil
}

func taskRebindSelectUI(current, projected map[string]any, patch any, explicit, multiple bool) (map[string]any, error) {
	selection := map[string]any{}
	if explicit {
		var ok bool
		selection, ok = patch.(map[string]any)
		if !ok || len(selection) == 0 {
			return nil, fmt.Errorf("ui_contract selection must be a non-empty object")
		}
	}
	bound := anyString(current["design_change_id"]) != "" || anyString(current["design_change_sha256"]) != ""
	sameBinding := bound && current["design_change_id"] == projected["design_change_id"] && current["design_change_sha256"] == projected["design_change_sha256"]
	if (bound && !sameBinding) || (!bound && multiple) {
		// A new adoption or several placeholder tasks cannot imply a safe division
		// of product work. The caller must supply the two stable-ID selectors.
		if selection["design_decision_ids"] == nil || selection["handoff_contract_ids"] == nil {
			return nil, fmt.Errorf("changed or ambiguous UI binding requires explicit task-local design_decision_ids and handoff_contract_ids in --task-updates-json")
		}
	}
	selected := cloneJSONMap(projected)
	if sameBinding {
		for field, baseline := range projected {
			selectionField := taskRebindSelectionField(field, baseline)
			protected := field == "required_evidence" || field == "must_preserve" || field == "must_not" ||
				field == "accepted_deviations" || field == "design_sources" || field == "style_authority" ||
				field == "comparison_tolerance" || field == "usability_validation"
			if !selectionField && !protected {
				continue
			}
			if _, overridden := selection[field]; overridden {
				continue
			}
			value, exists := current[field]
			if !exists || !taskRebindExactSelection(field, value, baseline) {
				return nil, fmt.Errorf("existing task-local ui_contract.%s is missing or differs from the exact adopted Plan; supply an explicit selector instead of widening its scope", field)
			}
			selected[field] = cloneJSONValue(value)
		}
		if notes, exists := current["reference_notes"]; exists {
			selected["reference_notes"] = cloneJSONValue(notes)
		}
	}
	for field, value := range selection {
		baseline, exists := projected[field]
		if !exists || !taskRebindExactSelection(field, value, baseline) {
			return nil, fmt.Errorf("ui_contract.%s must preserve the exact adopted Plan contract or immutable row subset", field)
		}
		selected[field] = cloneJSONValue(value)
	}
	if err := taskRebindValidateUISelection(selected); err != nil {
		return nil, err
	}
	if err := taskRebindValidateSelectedRows(selected, projected); err != nil {
		return nil, err
	}
	return selected, nil
}

func taskRebindSelectionField(field string, baseline any) bool {
	if field == "motion_contract" || field == "source_continuity" {
		return true
	}
	if field == "required_evidence" || field == "must_preserve" || field == "must_not" || field == "accepted_deviations" || field == "design_sources" {
		return false
	}
	_, array := baseline.([]any)
	return array
}

// Array selections copy whole immutable rows. Global safety, evidence, source
// continuity and style authority remain exact rather than accepting deep edits.
func taskRebindExactSelection(field string, selected, baseline any) bool {
	if reflect.DeepEqual(selected, baseline) {
		return true
	}
	if field == "required_evidence" || field == "must_preserve" || field == "must_not" || field == "accepted_deviations" || field == "design_sources" {
		return false
	}
	if field == "motion_contract" || field == "source_continuity" || field == "coverage" {
		chosen, chosenOK := selected.(map[string]any)
		approved, approvedOK := baseline.(map[string]any)
		if !chosenOK || !approvedOK || len(chosen) != len(approved) {
			return false
		}
		for key, value := range approved {
			candidate, exists := chosen[key]
			if !exists {
				return false
			}
			subset := field == "motion_contract" && key == "transitions" ||
				field == "source_continuity" && (key == "coverage" || key == "surface_bindings" || key == "action_bindings" || key == "asset_bindings") ||
				field == "coverage" && (key == "surface_ids" || key == "interaction_ids" || key == "component_ids")
			if subset {
				if !taskRebindExactSelection(key, candidate, value) {
					return false
				}
			} else if !reflect.DeepEqual(candidate, value) {
				return false
			}
		}
		return true
	}
	rows, rowsOK := selected.([]any)
	allowed, allowedOK := baseline.([]any)
	if !rowsOK || !allowedOK || len(rows) == 0 {
		return false
	}
	seen := map[string]bool{}
	for _, row := range rows {
		key := canonicalJSONSHA256(row)
		if seen[key] {
			return false
		}
		seen[key] = true
		found := false
		for _, candidate := range allowed {
			if reflect.DeepEqual(row, candidate) {
				found = true
				break
			}
		}
		if !found {
			return false
		}
	}
	return true
}

func taskRebindValidateUISelection(ui map[string]any) error {
	decisionIDs, err := taskRebindStrictRefs(ui["design_decision_ids"], "ui_contract.design_decision_ids")
	if err != nil {
		return err
	}
	handoffIDs, err := taskRebindStrictRefs(ui["handoff_contract_ids"], "ui_contract.handoff_contract_ids")
	if err != nil {
		return err
	}
	decisions := stringSliceSet(decisionIDs)
	handoffs := stringSliceSet(handoffIDs)
	if len(decisions) == 0 || len(handoffs) == 0 {
		return fmt.Errorf("adopted task UI requires DS and DH contract IDs")
	}
	rowSets := map[string]map[string]bool{}
	for _, field := range []string{"surface_catalog", "scenario_matrix", "component_contracts", "interaction_matrix", "editing_matrix", "data_state_matrix", "accessibility_matrix", "navigation_matrix", "content_matrix", "responsive_matrix", "visual_acceptance_matrix", "accepted_deviations"} {
		rowSets[field] = map[string]bool{}
		if field != "accepted_deviations" && len(designAnyList(ui[field])) == 0 {
			return fmt.Errorf("adopted task UI requires non-empty %s", field)
		}
		for _, raw := range designAnyList(ui[field]) {
			row, ok := raw.(map[string]any)
			if !ok || !handoffs[anyString(row["id"])] || rowSets[field][anyString(row["id"])] || !stringSetContainsAll(decisions, anyStringSlice(row["decision_ids"])) {
				return fmt.Errorf("%s rows must preserve selected DS/DH bindings", field)
			}
			rowSets[field][anyString(row["id"])] = true
		}
	}
	motion, _ := ui["motion_contract"].(map[string]any)
	rowSets["motion_contract"] = map[string]bool{}
	if len(designAnyList(motion["transitions"])) == 0 {
		return fmt.Errorf("adopted task UI requires motion transitions")
	}
	for _, raw := range designAnyList(motion["transitions"]) {
		row, _ := raw.(map[string]any)
		id := anyString(row["id"])
		if !handoffs[id] || rowSets["motion_contract"][id] || !stringSetContainsAll(decisions, anyStringSlice(row["decision_ids"])) {
			return fmt.Errorf("motion transitions must preserve selected DS/DH bindings")
		}
		rowSets["motion_contract"][id] = true
	}
	scenarioFields := map[string]string{
		"interaction_ids": "interaction_matrix", "editing_ids": "editing_matrix", "data_state_ids": "data_state_matrix",
		"accessibility_ids": "accessibility_matrix", "navigation_ids": "navigation_matrix", "content_ids": "content_matrix",
		"responsive_ids": "responsive_matrix", "motion_transition_ids": "motion_contract",
	}
	covered := map[string]map[string]bool{}
	for _, field := range scenarioFields {
		covered[field] = map[string]bool{}
	}
	for _, raw := range designAnyList(ui["scenario_matrix"]) {
		row, _ := raw.(map[string]any)
		if !rowSets["surface_catalog"][anyString(row["surface_id"])] {
			return fmt.Errorf("selected scenario requires its exact surface row")
		}
		for refs, field := range scenarioFields {
			if !stringSetContainsAll(rowSets[field], anyStringSlice(row[refs])) {
				return fmt.Errorf("selected scenario requires complete %s rows", field)
			}
			for _, id := range anyStringSlice(row[refs]) {
				covered[field][id] = true
			}
		}
	}
	for field, ids := range covered {
		if !stringSetEqual(ids, rowSets[field]) {
			return fmt.Errorf("selected scenarios must cover all and only selected %s rows", field)
		}
	}
	components := map[string]bool{}
	requiredStates := map[string]bool{}
	for _, raw := range designAnyList(ui["component_contracts"]) {
		row, _ := raw.(map[string]any)
		components[anyString(row["id"])] = true
		for _, state := range anyStringSlice(row["required_states"]) {
			requiredStates[state] = true
		}
	}
	for _, raw := range designAnyList(ui["surface_catalog"]) {
		row, _ := raw.(map[string]any)
		if !stringSetContainsAll(components, anyStringSlice(row["component_ids"])) {
			return fmt.Errorf("selected surfaces require their complete component contracts")
		}
	}
	coveredTargets, coveredStates, coveredDecisions := map[string]bool{}, map[string]bool{}, map[string]bool{}
	for _, raw := range designAnyList(ui["visual_acceptance_matrix"]) {
		row, _ := raw.(map[string]any)
		coveredTargets[anyString(row["target_id"])] = true
		for _, state := range anyStringSlice(row["states"]) {
			coveredStates[state] = true
		}
		for _, id := range anyStringSlice(row["decision_ids"]) {
			coveredDecisions[id] = true
		}
	}
	if !stringSetEqual(coveredTargets, rowSets["responsive_matrix"]) {
		return fmt.Errorf("visual_acceptance_matrix must cover all and only selected responsive targets")
	}
	if !stringSetContainsAll(coveredStates, sortedBoolKeys(requiredStates)) {
		return fmt.Errorf("visual_acceptance_matrix must cover every selected component's required states")
	}
	if !stringSetContainsAll(coveredDecisions, decisionIDs) {
		return fmt.Errorf("visual_acceptance_matrix must cover every selected design decision")
	}
	continuity, _ := ui["source_continuity"].(map[string]any)
	if continuity != nil {
		if err := validateDesignSourceContinuity(continuity, "ui_contract.source_continuity", true); err != nil {
			return err
		}
	}
	if err := validateDesignHandoffSourceContinuityCoverage(ui, "ui_contract.source_continuity"); err != nil {
		return err
	}
	return nil
}

// Every selected DH identifier whose row is represented by task contracts must
// retain that row. Keeping the ID list while omitting an immutable row cannot
// make coverage look complete. Token-map IDs remain in the exported Design.
func taskRebindValidateSelectedRows(selected, approved map[string]any) error {
	ids := stringSliceSet(anyStringSlice(selected["handoff_contract_ids"]))
	for field, baseline := range approved {
		rows, ok := baseline.([]any)
		chosen, chosenOK := selected[field].([]any)
		if field == "motion_contract" {
			motion, _ := baseline.(map[string]any)
			current, _ := selected[field].(map[string]any)
			rows, ok = motion["transitions"].([]any)
			chosen, chosenOK = current["transitions"].([]any)
		}
		if !ok || !chosenOK {
			continue
		}
		retained := map[string]bool{}
		for _, value := range chosen {
			if row, ok := value.(map[string]any); ok {
				retained[anyString(row["id"])] = true
			}
		}
		for _, value := range rows {
			if row, ok := value.(map[string]any); ok && ids[anyString(row["id"])] && !retained[anyString(row["id"])] {
				return fmt.Errorf("selected DH IDs require the complete immutable %s row %s", field, anyString(row["id"]))
			}
		}
	}
	return nil
}

func taskRebindPlanUI(root, feature string, plan map[string]any, snapshot *taskRebindSnapshot) (map[string]any, error) {
	ui, _ := plan["ui_design_contract"].(map[string]any)
	if ui == nil || ui["ui_applicable"] != true || anyString(ui["design_readiness"]) != "approved" {
		return nil, fmt.Errorf("pending UI tasks require an approved adopted plan ui_design_contract before rebinding")
	}
	changeID := anyString(ui["design_change_id"])
	if !designChangeIDRE.MatchString(changeID) {
		return nil, fmt.Errorf("plan UI requires an exact registered UD-* design_change_id")
	}
	if _, err := snapshot.read(filepath.Join(root, ".specify", "design", "index.json"), true); err != nil {
		return nil, err
	}
	expectedDesignPath := filepath.Join(root, ".specify", "design", "changes", changeID, "design-change.md")
	if anyString(ui["design_change_ref"]) != projectRelativeSlash(root, expectedDesignPath) {
		return nil, fmt.Errorf("plan UI must reference its exact registered change-local design-change.md")
	}
	// Ready export checks preview, manifest, handoff, approval and image prompt
	// sidecars. Freeze the change-local proof before any of those live reads.
	if err := snapshot.tree(filepath.Dir(expectedDesignPath)); err != nil {
		return nil, err
	}
	designPath, digest, doc, err := loadRegisteredDesignChange(root, changeID)
	if err != nil {
		return nil, err
	}
	if anyString(ui["design_change_ref"]) != projectRelativeSlash(root, designPath) || anyString(ui["design_change_sha256"]) != digest {
		return nil, fmt.Errorf("plan UI binding does not match its exact registered design change")
	}
	if digest != taskControlSHA256(snapshot.files[expectedDesignPath]) {
		return nil, fmt.Errorf("registered Design changed while freezing the rebind proof")
	}
	contractRef := projectRelativeSlash(root, filepath.Join(filepath.Dir(designPath), "design-contract.json"))
	if anyString(ui["design_contract_ref"]) != contractRef {
		return nil, fmt.Errorf("plan UI contract must reference the registered change-local export")
	}
	contractRaw, err := snapshot.read(filepath.Join(root, filepath.FromSlash(contractRef)), true)
	if err != nil {
		return nil, err
	}
	exported, err := exportDesignSystem(designPath, "json", true)
	if err != nil {
		return nil, err
	}
	var contract, expected map[string]any
	if json.Unmarshal(contractRaw, &contract) != nil || json.Unmarshal([]byte(exported), &expected) != nil || !reflect.DeepEqual(contract, expected) {
		return nil, fmt.Errorf("registered design export is stale or modified")
	}
	// Formal post-Specify adoption uses its verified receipt. Design-first uses
	// the exact existing Spec binding. Neither route resolves a latest design.
	if binding, ok := ui["design_adoption_binding"].(map[string]any); ok && anyString(binding["mode"]) == "formal-post-specify" {
		bindingPath, err := secureProjectPath(root, anyString(binding["source_spec_ref"]))
		if err != nil {
			return nil, err
		}
		bindingRaw, err := snapshot.read(bindingPath, true)
		if err != nil || taskControlSHA256(bindingRaw) != anyString(binding["source_spec_sha256"]) {
			return nil, fmt.Errorf("formal-post-specify source Spec differs from its frozen adoption digest: %v", err)
		}
		verified, err := resolveDesignAdoption(root, designAdoptionRequest{
			ConsumerRef: "feature:" + filepath.Base(feature), Scope: anyString(binding["scope"]),
			BindingRef: anyString(binding["source_spec_ref"]), BindingSHA256: anyString(binding["source_spec_sha256"]), ExpectedChange: changeID,
		})
		if err != nil || intFromAny(verified["revision"]) != intFromAny(binding["revision"]) || anyString(verified["impact_sha256"]) != anyString(binding["impact_sha256"]) {
			return nil, fmt.Errorf("plan UI adoption receipt is stale or invalid: %v", err)
		}
	} else {
		var spec map[string]any
		if json.Unmarshal(snapshot.files[filepath.Join(feature, "spec-contract.json")], &spec) != nil {
			return nil, fmt.Errorf("registered UI requires a source Spec binding or verified formal-post-specify adoption")
		}
		binding, _ := spec["design_contract"].(map[string]any)
		for _, field := range []string{"design_change_id", "design_change_ref", "design_change_sha256", "design_contract_ref"} {
			if !reflect.DeepEqual(binding[field], ui[field]) {
				return nil, fmt.Errorf("plan UI %s differs from the adopted source Spec", field)
			}
		}
	}
	approval, _ := doc.DesignSystem["approval"].(map[string]any)
	for planField, sourceField := range map[string]string{"approved_preview_sha256": "preview_sha256", "approved_manifest_sha256": "manifest_sha256", "approved_handoff_sha256": "handoff_sha256"} {
		if ui[planField] != approval[sourceField] {
			return nil, fmt.Errorf("plan UI %s differs from approved Design", planField)
		}
	}
	if !stringSetContainsAll(stringSliceSet(anyStringSlice(approval["decision_ids"])), anyStringSlice(ui["design_decision_ids"])) ||
		!stringSetContainsAll(stringSliceSet(anyStringSlice(approval["handoff_contract_ids"])), anyStringSlice(ui["handoff_contract_ids"])) {
		return nil, fmt.Errorf("plan UI DS/DH IDs are not approved Design members")
	}
	handoffPath := filepath.Join(filepath.Dir(designPath), filepath.FromSlash(anyString(approval["handoff_ref"])))
	if strings.HasPrefix(anyString(approval["handoff_ref"]), ".specify/") {
		handoffPath = filepath.Join(root, filepath.FromSlash(anyString(approval["handoff_ref"])))
	}
	handoffRaw, err := snapshot.read(handoffPath, true)
	if err != nil || taskControlSHA256(handoffRaw) != anyString(ui["approved_handoff_sha256"]) {
		return nil, fmt.Errorf("approved Design handoff is stale or unreadable: %v", err)
	}
	if anyString(ui["approved_handoff_ref"]) != projectRelativeSlash(root, handoffPath) {
		return nil, fmt.Errorf("plan UI approved_handoff_ref must identify the exact approved Design handoff")
	}
	visualRef := anyString(ui["approved_visual_ref"])
	visualMatches := false
	for _, approvedRef := range anyStringSlice(approval["visual_refs"]) {
		parsed, err := url.Parse(approvedRef)
		if err != nil || parsed.IsAbs() || parsed.Host != "" {
			return nil, fmt.Errorf("approved Design visual reference must be project-contained")
		}
		visualPath := filepath.Join(filepath.Dir(designPath), filepath.FromSlash(parsed.Path))
		if strings.HasPrefix(parsed.Path, ".specify/") {
			visualPath = filepath.Join(root, filepath.FromSlash(parsed.Path))
		}
		parsed.Path = projectRelativeSlash(root, visualPath)
		if parsed.String() != visualRef {
			continue
		}
		visualRaw, err := snapshot.read(visualPath, true)
		if err != nil || taskControlSHA256(visualRaw) != anyString(ui["approved_preview_sha256"]) {
			return nil, fmt.Errorf("approved Design visual bytes are stale or unreadable: %v", err)
		}
		visualMatches = true
	}
	if !visualMatches {
		return nil, fmt.Errorf("plan UI approved_visual_ref must identify an exact approved Design visual reference")
	}
	var handoff map[string]any
	if json.Unmarshal(handoffRaw, &handoff) != nil {
		return nil, fmt.Errorf("approved Design handoff is malformed")
	}
	reproduction, _ := handoff["reproduction"].(map[string]any)
	for section, fields := range map[string][]string{
		"product_context":    {"subject", "audience", "single_job"},
		"direction_contract": {"visual_thesis", "content_thesis", "interaction_thesis", "signature_element"},
	} {
		values, _ := doc.DesignSystem[section].(map[string]any)
		for _, field := range fields {
			if !reflect.DeepEqual(values[field], ui[field]) {
				return nil, fmt.Errorf("plan UI %s differs from approved Design", field)
			}
		}
	}
	if !reflect.DeepEqual(doc.DesignSystem["style_authority"], ui["style_authority"]) {
		return nil, fmt.Errorf("plan UI style_authority differs from approved Design")
	}
	constraints, _ := doc.DesignSystem["constraints"].(map[string]any)
	for _, field := range []string{"must_preserve", "may_adapt", "must_not"} {
		if baseline, exists := constraints[field]; exists && !taskRebindExactSelection(field, ui[field], baseline) {
			return nil, fmt.Errorf("plan UI %s differs from approved Design constraints", field)
		}
	}
	briefPath := filepath.Join(feature, "ui-brief.md")
	briefRef := anyString(ui["ui_brief_ref"])
	if briefRef != "ui-brief.md" && briefRef != projectRelativeSlash(root, briefPath) {
		return nil, fmt.Errorf("plan UI ui_brief_ref must identify this feature's ui-brief.md")
	}
	briefRaw, err := snapshot.read(briefPath, true)
	if err != nil || strings.TrimSpace(string(briefRaw)) == "" {
		return nil, fmt.Errorf("adopted UI requires its non-empty feature UI brief: %v", err)
	}
	templatePath := filepath.Join(root, ".specify", "templates", "task-packet-template.json")
	packetRaw, err := snapshot.read(templatePath, true)
	if err != nil {
		return nil, err
	}
	var packet map[string]any
	if json.Unmarshal(packetRaw, &packet) != nil {
		return nil, fmt.Errorf("task packet template is invalid")
	}
	defaults, ok := packet["ui_contract"].(map[string]any)
	if !ok {
		return nil, fmt.Errorf("task packet template must contain ui_contract")
	}
	for field := range defaults {
		if baseline, exists := reproduction[field]; exists {
			value, supplied := ui[field]
			if !supplied || !taskRebindExactSelection(field, value, baseline) {
				return nil, fmt.Errorf("plan UI %s must preserve approved Design rows; missing fields cannot become empty defaults", field)
			}
		}
	}
	projected := cloneJSONMap(defaults)
	for field := range defaults {
		if value, exists := ui[field]; exists {
			projected[field] = cloneJSONValue(value)
		}
	}
	projected["fidelity_level"] = cloneJSONValue(ui["fidelity_mode"])
	if !stringInSlice(anyString(projected["fidelity_level"]), []string{"approximate", "high", "inspiration"}) {
		return nil, fmt.Errorf("adopted Design requires plan fidelity_mode approximate, high, or inspiration")
	}
	sources := anyStringSlice(ui["source_refs"])
	for _, ref := range []string{anyString(ui["design_change_ref"]), contractRef, anyString(ui["approved_visual_ref"]), anyString(ui["approved_handoff_ref"]), anyString(ui["ui_brief_ref"])} {
		if ref != "" && !stringInSlice(ref, sources) {
			sources = append(sources, ref)
		}
	}
	projected["design_sources"] = stringsToAny(sources)
	projected["visual_target"] = cloneJSONValue(ui["approved_visual_ref"])
	if err := taskRebindValidateUISelection(projected); err != nil {
		return nil, fmt.Errorf("adopted Plan UI: %w", err)
	}
	if err := taskRebindValidateSelectedRows(projected, reproduction); err != nil {
		return nil, fmt.Errorf("adopted Plan UI: %w", err)
	}
	return projected, nil
}
