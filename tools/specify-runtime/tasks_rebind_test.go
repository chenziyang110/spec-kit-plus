package main

import (
	"bytes"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"reflect"
	"strings"
	"testing"
)

type taskRebindFixture struct {
	root, feature, featureRef string
	args                      []string
}

func newTaskRebindFixture(t *testing.T) taskRebindFixture {
	t.Helper()
	producer := setupValidatedTestDesignProjectionFixture(t, "feature", 2)
	requireTestDesignOK(t, producer.command("handoff", "--format", "json"))
	root, featureRef := producer.projectRoot, producer.featureRel
	feature := filepath.Join(root, filepath.FromSlash(featureRef))
	for _, name := range []string{"task-index-template.json", "task-packet-template.json", "task-lifecycle-template.json"} {
		path, err := locateTemplate(name)
		if err != nil {
			t.Fatal(err)
		}
		raw, err := os.ReadFile(path)
		if err != nil {
			t.Fatal(err)
		}
		if err := os.WriteFile(filepath.Join(root, ".specify", "templates", name), raw, 0o644); err != nil {
			t.Fatal(err)
		}
	}
	definition := map[string]any{
		"title": "Recover published test binding", "source_revision": 7,
		"tasks": []any{
			map[string]any{"id": "T001", "objective": "Already accepted", "test_case_refs": []any{"test-catalog.json#/cases/TC-001"}, "test_data_refs": []any{"test-data-manifest.json#/datasets/TD-001"}},
			map[string]any{"id": "T002", "objective": "User deferred", "user_confirmed_deferral_refs": []any{"discussion.md#confirmed-deferral"}},
			map[string]any{"id": "T003", "objective": "Remaining implementation", "dependencies": []any{"T001"}, "expected_write_scope": []any{"src/reversal.go"}, "test_case_refs": []any{"test-catalog.json#/cases/TC-002"}, "test_data_refs": []any{"test-data-manifest.json#/datasets/TD-002"}},
		},
	}
	assertTaskRuntimeCommandOK(t, []string{"tasks", "build", "--feature-dir", featureRef, "--definition-json", mustTestDesignJSON(t, definition), "--format", "json"})
	assertTaskRuntimeCommandOK(t, []string{"tasks", "finalize", "--feature-dir", featureRef, "--format", "json"})
	index := readImplementJSONFile(t, filepath.Join(feature, "task-index.json"))
	tasks := index["tasks"].([]any)
	for position, status := range []string{"accepted", "deferred"} {
		task := tasks[position].(map[string]any)
		id := anyString(task["id"])
		task["status"] = status
		task["result_ref"] = "worker-results/" + id + ".json"
		writeTaskRuntimeFixture(t, filepath.Join(feature, "implementation-review", "tasks", id+".json"), map[string]any{
			"version": 1, "revision": 9, "task_id": id, "status": status,
			"result_ref": task["result_ref"], "validation": []any{map[string]any{"command": "previous real verification", "status": "passed"}},
			"review": map[string]any{"status": "accepted"}, "reopen_history": []any{map[string]any{"reason": "prior preserved history"}},
		})
		writeTaskRuntimeFixture(t, filepath.Join(feature, "worker-results", id+".json"), map[string]any{
			"task_id": id, "status": "success", "summary": "Preserve this accepted history exactly.",
		})
	}
	writeTaskRuntimeFixture(t, filepath.Join(feature, "task-index.json"), index)
	assertTaskRuntimeCommandOK(t, []string{"tasks", "handoff", "--feature-dir", featureRef, "--target", "implement", "--format", "json"})
	assertTaskRuntimeCommandOK(t, []string{"tasks", "handoff", "--feature-dir", featureRef, "--target", "tasks", "--format", "json"})
	assertTaskRuntimeCommandOK(t, []string{"implement", "packet-compile", "--feature-dir", featureRef, "--task-id", "T003", "--format", "json"})
	writeTaskRuntimeFixture(t, filepath.Join(feature, "workflow.json"), map[string]any{
		"schema_version": 1, "feature_id": filepath.Base(feature), "revision": 7, "stage": "tasks", "status": "active",
		"summary": "Refresh Tasks", "blocker": nil, "last_resolution_evidence": []any{}, "last_reopen": nil,
		"last_blocker_resolution": nil, "acceptance_sha256": nil,
	})
	// Model a valid later producer publication over the same unchanged case/data
	// set. The production verifier validates the complete bundle and audit chain;
	// only the fixture's state publication revision and its bound digest change.
	statePath := filepath.Join(producer.artifactRoot, "test-state.json")
	state := readImplementJSONFile(t, statePath)
	state["revision"] = intFromAny(state["revision"]) + 1
	writeTaskRuntimeFixture(t, statePath, state)
	handoffPath := filepath.Join(producer.artifactRoot, "handoff-to-tasks.json")
	handoff := readImplementJSONFile(t, handoffPath)
	handoff["state_revision"] = state["revision"]
	handoff["artifact_digests"].(map[string]any)["state"] = taskControlSHA256(readTaskRebindFile(t, statePath))
	writeTaskRuntimeFixture(t, handoffPath, handoff)
	if _, err := (testDesignService{projectRoot: root}).verifyPublishedHandoff(producer.artifactRoot); err != nil {
		t.Fatalf("new producer fixture must be fully verified: %v", err)
	}
	fixture := taskRebindFixture{root: root, feature: feature, featureRef: featureRef}
	fixture.args = []string{
		"tasks", "rebind", "--feature-dir", featureRef,
		"--expected-task-index-sha256", taskControlSHA256(readTaskRebindFile(t, filepath.Join(feature, "task-index.json"))),
		"--expected-workflow-revision", "7",
		"--expected-test-design-handoff-sha256", taskControlSHA256(readTaskRebindFile(t, handoffPath)),
		"--reason", "Consume the verified refreshed producer without losing accepted work.", "--format", "json",
	}
	return fixture
}

func readTaskRebindFile(t *testing.T, path string) []byte {
	t.Helper()
	raw, err := os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}
	return raw
}

func snapshotTaskRebindOutputs(t *testing.T, fixture taskRebindFixture) map[string][]byte {
	t.Helper()
	result := map[string][]byte{}
	err := filepath.WalkDir(fixture.feature, func(path string, entry os.DirEntry, err error) error {
		if err != nil {
			return err
		}
		if entry.IsDir() {
			if path == filepath.Join(fixture.feature, "test-design") {
				return filepath.SkipDir
			}
			return nil
		}
		result[projectRelativeSlash(fixture.root, path)] = readTaskRebindFile(t, path)
		return nil
	})
	if err != nil {
		t.Fatal(err)
	}
	return result
}

func TestTasksRebindPreservesLifecycleAndPublishesAtomicHandoffs(t *testing.T) {
	fixture := newTaskRebindFixture(t)
	before := snapshotTaskRebindOutputs(t, fixture)
	indexPath := filepath.Join(fixture.feature, "task-index.json")
	previousIndex := readImplementJSONFile(t, indexPath)
	if env := validateHookArtifactSemantics(fixture.root, fixture.feature, fixture.featureRef, "tasks"); env.Status == "ok" {
		t.Fatal("Tasks stage accepted the old producer binding")
	}
	result := assertTaskRuntimeCommandOK(t, fixture.args)
	index := readImplementJSONFile(t, indexPath)
	for position := 0; position < 2; position++ {
		if !reflect.DeepEqual(previousIndex["tasks"].([]any)[position], index["tasks"].([]any)[position]) {
			t.Fatal("terminal task record was changed by rebind")
		}
	}
	for path, content := range before {
		if strings.Contains(path, "/implementation-review/tasks/") || strings.Contains(path, "/worker-results/") || strings.HasSuffix(path, "/workflow.json") {
			if !bytes.Equal(content, readTaskRebindFile(t, filepath.Join(fixture.root, filepath.FromSlash(path)))) {
				t.Fatalf("lifecycle/result/workflow history changed: %s", path)
			}
		}
	}
	if err := taskControlValidateTestDesignBinding(fixture.root, fixture.feature, index, false, true); err != nil {
		t.Fatalf("rebound binding is not current: %v", err)
	}
	if err := validateTaskControlFreshness(fixture.root, fixture.feature, index); err != nil {
		t.Fatalf("rebound handoffs are stale: %v", err)
	}
	if env := validateHookArtifactSemantics(fixture.root, fixture.feature, fixture.featureRef, "tasks"); env.Status != "ok" {
		t.Fatalf("current rebound Tasks stage rejected: %#v", env)
	}
	packet := readImplementJSONFile(t, filepath.Join(fixture.feature, "implementation-review", "packets", "T003.json"))
	if packet["test_design_handoff_sha256"] != index["test_design_handoff_sha256"] {
		t.Fatal("existing pending worker packet still has the previous binding")
	}
	historyPath := filepath.Join(fixture.root, filepath.FromSlash(anyString(result["history_ref"])))
	historyBytes := readTaskRebindFile(t, historyPath)
	if taskControlSHA256(historyBytes) != result["history_sha256"] {
		t.Fatal("history digest is not bound to the exact archived bytes")
	}
	history := readImplementJSONFile(t, historyPath)
	previousFiles := history["previous_files"].(map[string]any)
	indexRef := projectRelativeSlash(fixture.root, indexPath)
	if previousFiles[indexRef].(map[string]any)["content"] != string(before[indexRef]) {
		t.Fatal("audit did not preserve the exact original task index")
	}
	for _, target := range []string{"tasks", "implement"} {
		path := filepath.Join(fixture.feature, "handoff-to-"+target+".json")
		raw := readTaskRebindFile(t, path)
		if err := os.WriteFile(path, []byte(`{"status":"ready","task_index_sha256":"stale"}`), 0o644); err != nil {
			t.Fatal(err)
		}
		if env := validateHookArtifactSemantics(fixture.root, fixture.feature, fixture.featureRef, "tasks"); env.Status == "ok" {
			t.Fatalf("Tasks stage accepted stale %s handoff", target)
		}
		if err := os.WriteFile(path, raw, 0o644); err != nil {
			t.Fatal(err)
		}
	}
	markdownPath := filepath.Join(fixture.feature, "tasks.md")
	if err := os.WriteFile(markdownPath, []byte("# Tasks: Recover published test binding\n\n- [ ] T999 Contradictory stale projection\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	if env := validateHookArtifactSemantics(fixture.root, fixture.feature, fixture.featureRef, "tasks"); env.Status == "ok" || !strings.Contains(fmt.Sprint(env.Blockers), "tasks.md is stale") {
		t.Fatalf("Tasks stage accepted stale Markdown despite fresh index and handoffs: %#v", env)
	}
}

func TestTasksRebindRejectsUnsafeInputsWithoutChangingHistory(t *testing.T) {
	for _, test := range []struct {
		name, flag, value, want string
	}{
		{"stale_index", "--expected-task-index-sha256", strings.Repeat("a", 64), "digest is stale"},
		{"stale_workflow", "--expected-workflow-revision", "6", "revision is stale"},
		{"stale_producer", "--expected-test-design-handoff-sha256", strings.Repeat("b", 64), "handoff digest is stale"},
		{"terminal_update", "--task-updates-json", `{"T001":{"test_case_refs":[]}}`, "preserves terminal"},
		{"missing_case", "--task-updates-json", `{"T003":{"test_case_refs":[]}}`, "not consumed"},
		{"foreign_data", "--task-updates-json", `{"T003":{"test_data_refs":["test-data-manifest.json#/datasets/TD-999"]}}`, "not a member"},
		{"unknown_task", "--task-updates-json", `{"T999":{"test_case_refs":[]}}`, "does not identify"},
		{"runtime_field", "--task-updates-json", `{"T003":{"status":"accepted"}}`, "cannot change"},
		{"null_refs", "--task-updates-json", `{"T003":{"test_case_refs":null}}`, "array of unique canonical strings"},
		{"number_refs", "--task-updates-json", `{"T003":{"test_case_refs":[2]}}`, "unique non-empty canonical strings"},
		{"duplicate_refs", "--task-updates-json", `{"T003":{"test_case_refs":["test-catalog.json#/cases/TC-002","test-catalog.json#/cases/TC-002"]}}`, "unique non-empty canonical strings"},
	} {
		t.Run(test.name, func(t *testing.T) {
			fixture := newTaskRebindFixture(t)
			args := append([]string{}, fixture.args...)
			found := false
			for i := range args {
				if args[i] == test.flag {
					args[i+1] = test.value
					found = true
					break
				}
			}
			if !found {
				args = append(args, test.flag, test.value)
			}
			before := snapshotTaskRebindOutputs(t, fixture)
			exit, env := runTaskRuntimeCommand(t, args)
			if exit == 0 || !strings.Contains(env.Summary+fmt.Sprint(env.Blockers), test.want) {
				t.Fatalf("expected %q rejection: exit=%d env=%#v", test.want, exit, env)
			}
			if !reflect.DeepEqual(before, snapshotTaskRebindOutputs(t, fixture)) {
				t.Fatal("rejected rebind changed package, lifecycle or audit outputs")
			}
		})
	}
}

func TestTasksRebindRollsBackEveryOutputOnPublicationFailure(t *testing.T) {
	fixture := newTaskRebindFixture(t)
	before := snapshotTaskRebindOutputs(t, fixture)
	original := promoteTransactionFile
	t.Cleanup(func() { promoteTransactionFile = original })
	promoteTransactionFile = func(path string, data []byte, mode os.FileMode) error {
		if path == filepath.Join(fixture.feature, "tasks.md") {
			return errors.New("injected publication failure after other outputs")
		}
		return original(path, data, mode)
	}
	exit, env := runTaskRuntimeCommand(t, fixture.args)
	if exit == 0 || !strings.Contains(env.Summary+fmt.Sprint(env.Blockers), "injected publication failure") {
		t.Fatalf("expected publication failure: exit=%d env=%#v", exit, env)
	}
	if !reflect.DeepEqual(before, snapshotTaskRebindOutputs(t, fixture)) {
		t.Fatal("publication failure left mixed old/new task artifacts or audit")
	}
}

func newTaskRebindUIFixture(t *testing.T) (taskRebindFixture, map[string]any) {
	t.Helper()
	fixture := newTaskRebindFixture(t)
	designPath, digest := createRegisteredDesignChangeRuntime(t, "UD-0091", "web:settings")
	contractRef := writeDesignContractRuntime(t, designPath)
	_, _, doc, err := loadRegisteredDesignChange(fixture.root, "UD-0091")
	if err != nil {
		t.Fatal(err)
	}
	approval := doc.DesignSystem["approval"].(map[string]any)
	handoffPath := filepath.Join(filepath.Dir(designPath), filepath.FromSlash(anyString(approval["handoff_ref"])))
	handoff := readImplementJSONFile(t, handoffPath)
	reproduction := handoff["reproduction"].(map[string]any)
	templatePath, err := locateTemplate("plan-contract-template.json")
	if err != nil {
		t.Fatal(err)
	}
	plan := readImplementJSONFile(t, templatePath)
	ui := plan["ui_design_contract"].(map[string]any)
	for field := range ui {
		if value, exists := reproduction[field]; exists {
			ui[field] = cloneJSONValue(value)
		}
	}
	ui["ui_applicable"], ui["design_readiness"], ui["fidelity_mode"] = true, "approved", "high"
	ui["design_change_id"], ui["design_change_ref"], ui["design_change_sha256"], ui["design_contract_ref"] = "UD-0091", filepath.ToSlash(designPath), digest, contractRef
	ui["approved_preview_sha256"], ui["approved_manifest_sha256"], ui["approved_handoff_sha256"] = approval["preview_sha256"], approval["manifest_sha256"], approval["handoff_sha256"]
	ui["approved_handoff_ref"] = filepath.ToSlash(handoffPath)
	ui["approved_visual_ref"] = filepath.ToSlash(filepath.Join(filepath.Dir(designPath), "previews", "round-01.html")) + "#direction-main"
	ui["design_decision_ids"], ui["handoff_contract_ids"] = approval["decision_ids"], approval["handoff_contract_ids"]
	ui["style_authority"] = doc.DesignSystem["style_authority"]
	for _, section := range []string{"product_context", "direction_contract"} {
		for field, value := range doc.DesignSystem[section].(map[string]any) {
			if _, exists := ui[field]; exists {
				ui[field] = cloneJSONValue(value)
			}
		}
	}
	if constraints, ok := doc.DesignSystem["constraints"].(map[string]any); ok {
		for field, value := range constraints {
			if _, exists := ui[field]; exists {
				ui[field] = cloneJSONValue(value)
			}
		}
	}
	ui["ui_brief_ref"] = "ui-brief.md"
	if err := os.WriteFile(filepath.Join(fixture.feature, "ui-brief.md"), []byte("# UI Brief\n\nImplement the exact registered settings Design and its approved preview.\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	plan["source_revision"] = 8
	plan["source_requirement_coverage"] = nil
	delete(plan, "source_requirement_coverage")
	writeTaskRuntimeFixture(t, filepath.Join(fixture.feature, "plan-contract.json"), plan)
	specBinding := map[string]any{}
	for _, field := range []string{"design_change_id", "design_change_ref", "design_change_sha256", "design_contract_ref"} {
		specBinding[field] = ui[field]
	}
	writeTaskRuntimeFixture(t, filepath.Join(fixture.feature, "spec-contract.json"), map[string]any{"design_contract": specBinding})
	indexPath := filepath.Join(fixture.feature, "task-index.json")
	index := readImplementJSONFile(t, indexPath)
	index["tasks"].([]any)[2].(map[string]any)["ui_contract"] = map[string]any{
		"fidelity_level": "high", "design_sources": []any{}, "must_not": []any{"formal design required"},
	}
	writeTaskRuntimeFixture(t, indexPath, index)
	fixture.args[5] = taskControlSHA256(readTaskRebindFile(t, indexPath))
	return fixture, ui
}

func TestTasksRebindRefreshesOnlyPendingUIFromExactAdoptedDesign(t *testing.T) {
	fixture, ui := newTaskRebindUIFixture(t)
	indexPath := filepath.Join(fixture.feature, "task-index.json")
	result := assertTaskRuntimeCommandOK(t, fixture.args)
	if !reflect.DeepEqual(anyStringSlice(result["refreshed_ui_task_ids"]), []string{"T003"}) {
		t.Fatalf("unexpected refreshed UI task set: %#v", result)
	}
	updated := readImplementJSONFile(t, indexPath)
	actual := updated["tasks"].([]any)[2].(map[string]any)["ui_contract"].(map[string]any)
	for _, field := range []string{"design_change_id", "design_change_sha256", "style_authority", "scenario_matrix", "interaction_matrix", "source_continuity", "approved_handoff_sha256"} {
		if !reflect.DeepEqual(actual[field], ui[field]) {
			t.Fatalf("pending UI %s drifted from exact adopted Plan", field)
		}
	}
	if len(anyStringSlice(actual["design_sources"])) == 0 || strings.Contains(fmt.Sprint(actual["must_not"]), "formal design required") {
		t.Fatal("pending UI retained placeholder design contract")
	}
	packet := readImplementJSONFile(t, filepath.Join(fixture.feature, "implementation-review", "packets", "T003.json"))
	if !reflect.DeepEqual(packet["ui_contract"], actual) {
		t.Fatal("worker packet does not carry the refreshed task-local UI contract")
	}
	// An apparently valid task patch cannot substitute a fabricated design row.
	fixture.args[5] = taskControlSHA256(readTaskRebindFile(t, indexPath))
	fixture.args = append(fixture.args, "--task-updates-json", `{"T003":{"ui_contract":{"interaction_matrix":[{"id":"DH-FAKE","decision_ids":["DS-FAKE"]}]}}}`)
	before := snapshotTaskRebindOutputs(t, fixture)
	exit, env := runTaskRuntimeCommand(t, fixture.args)
	if exit == 0 || !strings.Contains(env.Summary+fmt.Sprint(env.Blockers), "exact adopted Plan") {
		t.Fatalf("fabricated design selection accepted: exit=%d env=%#v", exit, env)
	}
	if !reflect.DeepEqual(before, snapshotTaskRebindOutputs(t, fixture)) {
		t.Fatal("invalid UI selection changed existing state")
	}
}

func TestTasksRebindRejectsIncompleteOrUnapprovedUIProofWithoutWrites(t *testing.T) {
	for _, test := range []struct {
		name, field string
		value       any
		missing     bool
	}{
		{name: "missing_components", field: "component_contracts", missing: true},
		{name: "missing_scenarios", field: "scenario_matrix", missing: true},
		{name: "missing_visual_acceptance", field: "visual_acceptance_matrix", missing: true},
		{name: "missing_motion", field: "motion_contract", missing: true},
		{name: "fake_visual_ref", field: "approved_visual_ref", value: "unapproved-preview.html#fabricated"},
		{name: "fake_handoff_ref", field: "approved_handoff_ref", value: "unapproved-handoff.json"},
		{name: "wrong_ui_brief", field: "ui_brief_ref", value: "another-feature/ui-brief.md"},
		{name: "missing_ui_brief", field: "ui_brief_ref", missing: true},
		{name: "unsupported_fidelity", field: "fidelity_mode", value: "banana"},
	} {
		t.Run(test.name, func(t *testing.T) {
			fixture, _ := newTaskRebindUIFixture(t)
			path := filepath.Join(fixture.feature, "plan-contract.json")
			plan := readImplementJSONFile(t, path)
			ui := plan["ui_design_contract"].(map[string]any)
			if test.missing {
				delete(ui, test.field)
			} else {
				ui[test.field] = test.value
			}
			writeTaskRuntimeFixture(t, path, plan)
			before := snapshotTaskRebindOutputs(t, fixture)
			exit, env := runTaskRuntimeCommand(t, fixture.args)
			if exit == 0 || !strings.Contains(env.Summary+fmt.Sprint(env.Blockers), test.field) {
				t.Fatalf("unsafe UI proof was accepted or failed for an unrelated cause: exit=%d env=%#v", exit, env)
			}
			if !reflect.DeepEqual(before, snapshotTaskRebindOutputs(t, fixture)) {
				t.Fatal("invalid adopted UI proof changed task state or history")
			}
		})
	}
}

func TestTasksRebindPreservesExistingTaskLocalUISelection(t *testing.T) {
	fixture, _ := newTaskRebindUIFixture(t)
	assertTaskRuntimeCommandOK(t, fixture.args)
	indexPath := filepath.Join(fixture.feature, "task-index.json")
	index := readImplementJSONFile(t, indexPath)
	tasks := index["tasks"].([]any)
	full := tasks[2].(map[string]any)["ui_contract"].(map[string]any)
	selected := cloneJSONMap(full)
	scenarios := designAnyList(full["scenario_matrix"])
	if len(scenarios) < 2 {
		t.Fatal("real approved fixture needs multiple scenarios to prove preservation")
	}
	selected["scenario_matrix"] = []any{cloneJSONValue(scenarios[0])}
	keep := map[string]map[string]bool{}
	first := scenarios[0].(map[string]any)
	keep["surface_catalog"] = stringSliceSet([]string{anyString(first["surface_id"])})
	for refs, field := range map[string]string{
		"interaction_ids": "interaction_matrix", "editing_ids": "editing_matrix", "data_state_ids": "data_state_matrix",
		"accessibility_ids": "accessibility_matrix", "navigation_ids": "navigation_matrix", "content_ids": "content_matrix",
		"responsive_ids": "responsive_matrix", "motion_transition_ids": "motion_contract",
	} {
		keep[field] = stringSliceSet(anyStringSlice(first[refs]))
	}
	removed := map[string]bool{}
	for _, row := range scenarios[1:] {
		removed[anyString(row.(map[string]any)["id"])] = true
	}
	for field, ids := range keep {
		rows := designAnyList(full[field])
		if field == "motion_contract" {
			rows = designAnyList(full[field].(map[string]any)["transitions"])
		}
		chosen := []any{}
		for _, value := range rows {
			row := value.(map[string]any)
			if ids[anyString(row["id"])] {
				chosen = append(chosen, cloneJSONValue(row))
			} else {
				removed[anyString(row["id"])] = true
			}
		}
		if field == "motion_contract" {
			selected[field].(map[string]any)["transitions"] = chosen
		} else {
			selected[field] = chosen
		}
	}
	acceptance := []any{}
	for _, raw := range designAnyList(full["visual_acceptance_matrix"]) {
		row := raw.(map[string]any)
		if keep["responsive_matrix"][anyString(row["target_id"])] {
			acceptance = append(acceptance, cloneJSONValue(row))
		} else {
			removed[anyString(row["id"])] = true
		}
	}
	selected["visual_acceptance_matrix"] = acceptance
	selectedIDs := []any{}
	for _, id := range anyStringSlice(full["handoff_contract_ids"]) {
		if !removed[id] {
			selectedIDs = append(selectedIDs, id)
		}
	}
	selected["handoff_contract_ids"] = selectedIDs
	selected["reference_notes"] = "Keep the settings-entrypoint task boundary."
	if err := taskRebindValidateUISelection(selected); err != nil {
		t.Fatalf("real approved task-local scenario selection is invalid: %v", err)
	}
	tasks[2].(map[string]any)["ui_contract"] = selected
	// A sibling owns the other approved work. Its independent write scope must
	// never be silently copied into T003's UI contract during a producer refresh.
	sibling := cloneJSONMap(tasks[2].(map[string]any))
	sibling["id"], sibling["objective"], sibling["expected_write_scope"] = "T004", "Other UI work", []any{"src/other-ui.go"}
	sibling["test_case_refs"], sibling["test_data_refs"], sibling["ui_contract"] = []any{}, []any{}, cloneJSONMap(full)
	index["tasks"] = append(tasks, sibling)
	writeTaskRuntimeFixture(t, indexPath, index)
	fixture.args[5] = taskControlSHA256(readTaskRebindFile(t, indexPath))
	assertTaskRuntimeCommandOK(t, fixture.args)
	actual := readImplementJSONFile(t, indexPath)["tasks"].([]any)
	if !reflect.DeepEqual(actual[2].(map[string]any)["ui_contract"], selected) {
		t.Fatal("rebind expanded the existing task-local UI subset into the full Plan")
	}
	for i, before := range []map[string]any{tasks[2].(map[string]any), sibling} {
		if !reflect.DeepEqual(actual[i+2].(map[string]any)["expected_write_scope"], before["expected_write_scope"]) {
			t.Fatal("rebind changed the product write scope to accommodate expanded UI work")
		}
	}
}

func TestTasksRebindRejectsBoundUISafetyDrift(t *testing.T) {
	fixture, _ := newTaskRebindUIFixture(t)
	assertTaskRuntimeCommandOK(t, fixture.args)
	indexPath := filepath.Join(fixture.feature, "task-index.json")
	index := readImplementJSONFile(t, indexPath)
	ui := index["tasks"].([]any)[2].(map[string]any)["ui_contract"].(map[string]any)
	ui["required_evidence"] = append(designAnyList(ui["required_evidence"]), "task-specific keyboard verification")
	writeTaskRuntimeFixture(t, indexPath, index)
	fixture.args[5] = taskControlSHA256(readTaskRebindFile(t, indexPath))
	before := snapshotTaskRebindOutputs(t, fixture)
	exit, env := runTaskRuntimeCommand(t, fixture.args)
	if exit == 0 || !strings.Contains(env.Summary+fmt.Sprint(env.Blockers), "required_evidence") {
		t.Fatalf("bound task-local evidence was silently removed: exit=%d env=%#v", exit, env)
	}
	if !reflect.DeepEqual(before, snapshotTaskRebindOutputs(t, fixture)) {
		t.Fatal("bound UI safety drift changed task state or audit")
	}
}

func TestTasksRebindRejectsDroppedVisualTargetWithRemovedDHID(t *testing.T) {
	fixture, _ := newTaskRebindUIFixture(t)
	planPath := filepath.Join(fixture.feature, "plan-contract.json")
	plan := readImplementJSONFile(t, planPath)
	ui := plan["ui_design_contract"].(map[string]any)
	rows := designAnyList(ui["visual_acceptance_matrix"])
	if len(rows) < 2 {
		t.Fatal("approved fixture needs multiple visual targets")
	}
	removedID := anyString(rows[0].(map[string]any)["id"])
	ui["visual_acceptance_matrix"] = rows[1:]
	ids := []any{}
	for _, id := range anyStringSlice(ui["handoff_contract_ids"]) {
		if id != removedID {
			ids = append(ids, id)
		}
	}
	ui["handoff_contract_ids"] = ids
	writeTaskRuntimeFixture(t, planPath, plan)
	before := snapshotTaskRebindOutputs(t, fixture)
	exit, env := runTaskRuntimeCommand(t, fixture.args)
	if exit == 0 || !strings.Contains(env.Summary+fmt.Sprint(env.Blockers), "visual_acceptance_matrix must cover all and only selected responsive targets") {
		t.Fatalf("responsive target lost visual acceptance but still published: exit=%d env=%#v", exit, env)
	}
	if !reflect.DeepEqual(before, snapshotTaskRebindOutputs(t, fixture)) {
		t.Fatal("incomplete visual target coverage changed task state or audit")
	}
}

func TestTasksRebindSnapshotRejectsConcurrentLifecycleChange(t *testing.T) {
	fixture := newTaskRebindFixture(t)
	snapshot := &taskRebindSnapshot{root: fixture.root, files: map[string][]byte{}}
	path := filepath.Join(fixture.feature, "implementation-review", "tasks", "T001.json")
	if _, err := snapshot.read(path, true); err != nil {
		t.Fatal(err)
	}
	current := readImplementJSONFile(t, path)
	current["revision"] = 10
	writeTaskRuntimeFixture(t, path, current)
	indexPath := filepath.Join(fixture.feature, "task-index.json")
	before := readTaskRebindFile(t, indexPath)
	_, err := applyFileTransactionWithPreconditions(fixture.root, "tasks.rebind", []fileTransactionUpdate{{Path: indexPath, Content: []byte("replacement")}}, snapshot.preconditions())
	if err == nil || !strings.Contains(err.Error(), "precondition failed") {
		t.Fatalf("stale lifecycle snapshot accepted: %v", err)
	}
	if !bytes.Equal(before, readTaskRebindFile(t, indexPath)) {
		t.Fatal("stale lifecycle transaction overwrote the current task index")
	}
}
