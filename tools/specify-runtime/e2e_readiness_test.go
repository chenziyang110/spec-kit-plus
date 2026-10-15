package main

import (
	"fmt"
	"os"
	"path/filepath"
	"reflect"
	"sort"
	"strconv"
	"strings"
	"testing"
)

func e2eR2Plan(groups int) e2ePlanInput {
	plan := e2eViewsPlan(groups, "execution")
	for i := range plan.Tasks {
		task := &plan.Tasks[i]
		task.ID = strings.ToLower(task.ID)
		task.Outputs = []string{"tests/e2e/" + task.ID + ".md"}
		task.Inputs = []string{fmt.Sprintf("request-%03d.md", i/7)}
	}
	return plan
}
func e2eR2Init(t *testing.T, plan e2ePlanInput) string {
	t.Helper()
	root := t.TempDir()
	for i := range plan.Scope {
		e2eTestFile(t, root, fmt.Sprintf("request-%03d.md", i), "immutable initial requirement")
	}
	e2eTestData(t, root, "init", "--run-id", "run-1", "--leader-id", "leader", "--input-json", e2eTestJSON(t, plan), "--view", "compact")
	return root
}
func e2eR2Actions(data map[string]any) []string {
	result := []string{}
	for _, raw := range data["ready_actions"].([]any) {
		row := raw.(map[string]any)
		result = append(result, fmt.Sprint(row["task_id"], "/", row["action"], "/", row["diagnostic"]))
	}
	sort.Strings(result)
	return result
}
func e2eR2HasAction(data map[string]any, id, action string) bool {
	for _, raw := range data["ready_actions"].([]any) {
		row := raw.(map[string]any)
		if row["task_id"] == id && row["action"] == action {
			return true
		}
	}
	return false
}

func TestE2ER2ReadySetSharedGateAndFreshCAS(t *testing.T) {
	plan := e2eR2Plan(3)
	plan.Tasks[0].Resources = []string{"isolated-browser"}
	plan.Tasks[7].Resources = []string{"isolated-browser"}
	root := e2eR2Init(t, plan)
	initial := e2eTestData(t, root, "status", "--run-id", "run-1")
	if !e2eR2HasAction(initial, "t000-1", "task-start") || !e2eR2HasAction(initial, "t001-1", "task-start") || initial["readiness_counts"].(map[string]any)["candidate_conflict_pair_count"] != float64(1) {
		t.Fatal("individually ready mutually exclusive candidates were hidden")
	}
	for i, j := 0, len(plan.Tasks)-1; i < j; i, j = i+1, j-1 {
		plan.Tasks[i], plan.Tasks[j] = plan.Tasks[j], plan.Tasks[i]
	}
	reverse := e2eR2Init(t, plan)
	reversed := e2eTestData(t, reverse, "status", "--run-id", "run-1")
	if !reflect.DeepEqual(e2eR2Actions(initial), e2eR2Actions(reversed)) {
		t.Fatal("ready set depends on task order")
	}
	e2eTestMutation(t, root, "task-start", "--task-id", "t000-1", "--worker-id", "worker-a")
	current := e2eTestData(t, root, "status", "--run-id", "run-1")
	if !e2eR2HasAction(current, "t002-1", "task-start") || e2eR2HasAction(current, "t001-1", "task-start") {
		t.Fatal("active task starved independent lane or failed to block a conflict")
	}
	before := e2eViewsTree(t, root)
	code, _ := e2eTestCall(t, root, "task-start", "--run-id", "run-1", "--task-id", "t002-1", "--worker-id", "worker-c", "--expected-revision", "1")
	if code != 10 || !reflect.DeepEqual(before, e2eViewsTree(t, root)) {
		t.Fatal("old batch revision was accepted or wrote state")
	}
	code, _ = e2eTestCall(t, root, "task-start", "--run-id", "run-1", "--task-id", "t001-1", "--worker-id", "worker-b", "--expected-revision", e2eTestRevision(t, root))
	if code != 10 || !reflect.DeepEqual(before, e2eViewsTree(t, root)) {
		t.Fatal("query/mutation readiness disagreed about exclusive ownership")
	}
	e2eTestMutation(t, root, "task-start", "--task-id", "t002-1", "--worker-id", "worker-c")
	shown := e2eTestData(t, root, "task-show", "--run-id", "run-1", "--task-id", "t001-1", "--view", "compact")
	if !strings.Contains(e2eTestJSON(t, shown["waiting"]), "exclusive_resource") {
		t.Fatal("blocking resource reason was lost")
	}
	dependent := e2eTestData(t, root, "task-show", "--run-id", "run-1", "--task-id", "t000-2")
	if !strings.Contains(e2eTestJSON(t, dependent["waiting"]), `"required":"passed"`) {
		t.Fatal("implicit stage dependency missing")
	}
}

func TestE2ER2ConflictPagesBoundCartesianOutput(t *testing.T) {
	plan := e2eViewsPlan(100, "execution")
	for i := range plan.Tasks {
		if plan.Tasks[i].Stage == 1 {
			plan.Tasks[i].Resources = []string{"one-browser"}
		}
	}
	root := e2eR2Init(t, plan)
	status := e2eTestData(t, root, "status", "--run-id", "run-1", "--view", "compact")
	if status["readiness_counts"].(map[string]any)["candidate_conflict_pair_count"] != float64(4950) || status["candidate_conflicts"] != nil {
		t.Fatal("compact expanded or hid Cartesian candidate conflicts")
	}
	allReady, allWaiting := map[string]bool{}, map[string]bool{}
	for offset := 0; offset < 700; offset += 25 {
		page := e2eTestData(t, root, "status", "--run-id", "run-1", "--view", "compact", "--offset", strconv.Itoa(offset))
		for _, raw := range page["ready_actions"].([]any) {
			id := raw.(map[string]any)["task_id"].(string)
			if allReady[id] {
				t.Fatal("duplicate ready action")
			}
			allReady[id] = true
		}
		for _, raw := range page["waiting"].([]any) {
			id := raw.(map[string]any)["task_id"].(string)
			if allWaiting[id] {
				t.Fatal("duplicate waiting task")
			}
			allWaiting[id] = true
		}
	}
	counts := status["readiness_counts"].(map[string]any)
	if float64(len(allReady)) != counts["ready_action_count"] || float64(len(allWaiting)) != counts["waiting_task_count"] || len(allReady) != 300 {
		t.Fatal("compact readiness pages lost part of executable/waiting denominator")
	}
	before := e2eViewsTree(t, root)
	seen := map[string]bool{}
	for offset := 0; offset < 99; offset += 7 {
		shown := e2eTestData(t, root, "task-show", "--run-id", "run-1", "--task-id", "T000-1", "--view", "compact", "--offset", strconv.Itoa(offset), "--limit", "7")
		rows := shown["conflicts"].([]any)
		if len(rows) > 7 || shown["conflict_page"].(map[string]any)["total"] != float64(99) {
			t.Fatal("task conflict page not bounded")
		}
		for _, raw := range rows {
			id := raw.(map[string]any)["other_task_id"].(string)
			if seen[id] {
				t.Fatal("duplicate conflict")
			}
			seen[id] = true
		}
		if (offset+len(rows) < 99) != (len(shown["next_conflict_page_argv"].([]any)) > 0) {
			t.Fatal("conflict pagination ended early")
		}
	}
	if len(seen) != 99 || !reflect.DeepEqual(before, e2eViewsTree(t, root)) {
		t.Fatal("conflict pages lost peers or wrote state")
	}
}

func TestE2ER2PathConflictsUseOwnerCaseAndReadWriteRules(t *testing.T) {
	cases := []struct {
		a, b e2eTaskSpec
		kind string
	}{
		{e2eTaskSpec{ID: "a", Outputs: []string{"tests/e2e/shared"}}, e2eTaskSpec{ID: "b", Outputs: []string{"tests/e2e/shared/part.md"}}, "write_write"},
		{e2eTaskSpec{ID: "a", Outputs: []string{"tests/e2e/shared.md"}}, e2eTaskSpec{ID: "b", Inputs: []string{"tests/e2e/shared.md"}}, "write_read"},
		{e2eTaskSpec{ID: "a", Inputs: []string{"tests/e2e/shared.md"}}, e2eTaskSpec{ID: "b", Outputs: []string{"tests/e2e/shared.md"}}, "read_write"},
	}
	for _, tc := range cases {
		reasons := e2eTaskConflicts(tc.a, tc.b)
		if len(reasons) != 1 || reasons[0].Kind != tc.kind {
			t.Fatalf("incorrect conflict: %v", reasons)
		}
	}
	a, b := e2eTaskSpec{ID: "a", Outputs: []string{"tests/e2e/Report.md"}}, e2eTaskSpec{ID: "b", Outputs: []string{"tests/e2e/report.md"}}
	if (len(e2eTaskConflicts(a, b)) > 0) != (e2eFilePathKey(a.Outputs[0]) == e2eFilePathKey(b.Outputs[0])) {
		t.Fatal("platform case aliases disagree with owner")
	}
	if len(e2eTaskConflicts(e2eTaskSpec{Inputs: []string{"same.md"}}, e2eTaskSpec{Inputs: []string{"same.md"}})) != 0 {
		t.Fatal("independent readers conflict")
	}
}

func TestE2ER2TypedDriftPreservesIndependentAcceptance(t *testing.T) {
	for _, tc := range []struct{ kind, path string }{{"input_drift", "request-000.md"}, {"output_drift", "tests/e2e/t000-1.md"}, {"evidence_drift", "tests/e2e/evidence-t000-1.txt"}, {"review_evidence_drift", "tests/e2e/review-evidence-t000-1.txt"}} {
		t.Run(tc.kind, func(t *testing.T) {
			root := e2eR2Init(t, e2eR2Plan(2))
			e2eTestCompleteTask(t, root, "t000-1")
			e2eTestCompleteTask(t, root, "t001-1")
			e2eTestMutation(t, root, "task-start", "--task-id", "t000-2", "--worker-id", "worker-child")
			independent := e2eTestData(t, root, "task-show", "--run-id", "run-1", "--task-id", "t001-1")["task"].(map[string]any)["acceptance"]
			raw, err := os.ReadFile(filepath.Join(root, filepath.FromSlash(tc.path)))
			if err != nil {
				t.Fatal(err)
			}
			expected := fileContentSHA256(raw)
			e2eTestFile(t, root, tc.path, "changed live bytes")
			before := e2eViewsTree(t, root)
			code, response := e2eTestCall(t, root, "status", "--run-id", "run-1")
			if code != 10 || !reflect.DeepEqual(before, e2eViewsTree(t, root)) {
				t.Fatal("drift status was writable or passed")
			}
			data := response["data"].(map[string]any)
			diagnostics := data["diagnostics"].([]any)
			found := false
			for _, row := range diagnostics {
				d := row.(map[string]any)
				if d["root_task_id"] == "t000-1" && d["kind"] == tc.kind {
					found = true
					if d["path"] != tc.path || d["expected_sha256"] != expected || d["observed_sha256"] != fileContentSHA256([]byte("changed live bytes")) || d["immutable"] != false || len(d["affected_task_ids"].([]any)) != 7 {
						t.Fatalf("imprecise causal diagnostic: %v", d)
					}
				}
			}
			if !found || len(data["ready_actions"].([]any)) != 0 {
				t.Fatal("causal root lost or stale run advertised ordinary actions")
			}
			code, response = e2eTestCall(t, root, "task-start", "--run-id", "run-1", "--task-id", "t001-2", "--worker-id", "worker-next", "--expected-revision", strconv.Itoa(int(data["revision"].(float64))))
			if code != 10 {
				t.Fatal("drift mutation did not first refuse/invalidate")
			}
			invalidated := response["data"].(map[string]any)["invalidated_task_ids"].([]any)
			if len(invalidated) != 7 {
				t.Fatalf("wrong affected denominator: %v", invalidated)
			}
			for _, id := range invalidated {
				if !strings.HasPrefix(id.(string), "t000-") {
					t.Fatal("unrelated lane invalidated")
				}
			}
			shown := e2eTestData(t, root, "task-show", "--run-id", "run-1", "--task-id", "t001-1")
			if !reflect.DeepEqual(independent, shown["task"].(map[string]any)["acceptance"]) {
				t.Fatal("unrelated acceptance changed")
			}
			if shown["diagnostic_history_ref"] == nil || shown["diagnostic_history_count"] != float64(1) {
				t.Fatal("restart lost discoverable diagnostic history")
			}
			historyArgv := stringSliceFromAny(shown["diagnostic_history_show_argv"])
			historyCode, history := e2ePublicCall(t, historyArgv[1:]...)
			if historyCode != 0 || !strings.Contains(e2eTestJSON(t, history), expected) {
				t.Fatal("diagnostic history pointer cannot retrieve original causal hashes")
			}
			e2eTestMutation(t, root, "task-start", "--task-id", "t001-2", "--worker-id", "worker-next")
			stateRaw, err := os.ReadFile(filepath.Join(root, ".planning/e2e/run-1/state.json"))
			if err != nil {
				t.Fatal(err)
			}
			var state e2eState
			if err := e2eDecode(stateRaw, &state); err != nil {
				t.Fatal(err)
			}
			if len(state.Events) == 0 {
				t.Fatal("causal invalidation event not persisted")
			}
			event, err := os.ReadFile(filepath.Join(root, filepath.FromSlash(state.Events[len(state.Events)-1].Ref)))
			if err != nil || !strings.Contains(string(event), expected) || !strings.Contains(string(event), tc.kind) {
				t.Fatal("durable invalidation lost hashes/root cause")
			}
		})
	}
}

func TestE2ER2ImmutableCorruptionRequiresExactRestoration(t *testing.T) {
	for _, kind := range []string{"packet", "archive", "history"} {
		t.Run(kind, func(t *testing.T) {
			root := e2eR2Init(t, e2eR2Plan(1))
			started := e2eTestMutation(t, root, "task-start", "--task-id", "t000-1", "--worker-id", "worker")
			ref := started["packet_ref"].(string)
			if kind == "archive" {
				ref = started["packet"].(map[string]any)["inputs"].([]any)[0].(map[string]any)["archive_ref"].(string)
			}
			if kind == "history" {
				e2eTestMutation(t, root, "reopen", "--task-id", "t000-1", "--leader-id", "leader", "--reason", "new attempt", "--evidence-ref", "request-000.md")
			}
			revision := e2eTestRevision(t, root)
			path := filepath.Join(root, filepath.FromSlash(ref))
			original, err := os.ReadFile(path)
			if err != nil {
				t.Fatal(err)
			}
			if err := os.Chmod(path, 0o644); err != nil {
				t.Fatal(err)
			}
			e2eTestFile(t, root, ref, "corrupt immutable bytes")
			before := e2eViewsTree(t, root)
			for _, args := range [][]string{{"status"}, {"task-show", "--task-id", "t000-1"}, {"reopen", "--task-id", "t000-1", "--leader-id", "leader", "--reason", "must not erase corruption", "--evidence-ref", "request-000.md", "--expected-revision", revision}, {"task-start", "--task-id", "t000-1", "--worker-id", "next-worker", "--expected-revision", revision}} {
				code, response := e2eTestCall(t, root, append(args, "--run-id", "run-1")...)
				if code != 10 || !reflect.DeepEqual(before, e2eViewsTree(t, root)) {
					t.Fatal("immutable corruption was reset or mutated")
				}
				diagnostic := response["data"].(map[string]any)["diagnostics"].([]any)[0].(map[string]any)
				if diagnostic["immutable"] != true || diagnostic["path"] != ref || diagnostic["expected_sha256"] != fileContentSHA256(original) || diagnostic["observed_sha256"] != fileContentSHA256([]byte("corrupt immutable bytes")) {
					t.Fatalf("corruption lost exact immutable binding: %v", diagnostic)
				}
			}
			if err := os.WriteFile(path, original, 0o444); err != nil {
				t.Fatal(err)
			}
			shown := e2eTestData(t, root, "task-show", "--run-id", "run-1", "--task-id", "t000-1")
			if strconv.Itoa(int(shown["revision"].(float64))) != revision {
				t.Fatal("restoration changed the workflow revision")
			}
			if kind != "history" && !reflect.DeepEqual(shown["submission_template"], started["submission_template"]) {
				t.Fatal("exact restoration did not restore the original attempt")
			}
		})
	}
}

func TestE2ER2MissingLiveInputIsRerunnableDrift(t *testing.T) {
	root := e2eR2Init(t, e2eR2Plan(1))
	e2eTestMutation(t, root, "task-start", "--task-id", "t000-1", "--worker-id", "worker")
	if err := os.Remove(filepath.Join(root, "request-000.md")); err != nil {
		t.Fatal(err)
	}
	before := e2eViewsTree(t, root)
	code, response := e2eTestCall(t, root, "status", "--run-id", "run-1", "--view", "compact")
	if code != 10 || !reflect.DeepEqual(before, e2eViewsTree(t, root)) {
		t.Fatal("missing input status mutated state")
	}
	d := response["data"].(map[string]any)["diagnostics"].([]any)[0].(map[string]any)
	if d["kind"] != "input_drift" || d["immutable"] != false || d["observed_sha256"] != "" || d["expected_sha256"] == "" {
		t.Fatalf("missing input classified as immutable corruption: %v", d)
	}
}

func TestE2ER2MixedCorruptionBlocksAllRecoveryUntilRestored(t *testing.T) {
	for _, reverse := range []bool{false, true} {
		t.Run(strconv.FormatBool(reverse), func(t *testing.T) {
			plan := e2eR2Plan(2)
			if reverse {
				for i, j := 0, len(plan.Tasks)-1; i < j; i, j = i+1, j-1 {
					plan.Tasks[i], plan.Tasks[j] = plan.Tasks[j], plan.Tasks[i]
				}
			}
			root := e2eR2Init(t, plan)
			e2eTestMutation(t, root, "task-start", "--task-id", "t000-1", "--worker-id", "a")
			second := e2eTestMutation(t, root, "task-start", "--task-id", "t001-1", "--worker-id", "b")
			revision := strconv.Itoa(int(second["revision"].(float64)))
			ref := second["packet_ref"].(string)
			path := filepath.Join(root, filepath.FromSlash(ref))
			original, err := os.ReadFile(path)
			if err != nil {
				t.Fatal(err)
			}
			if err := os.Chmod(path, 0o644); err != nil {
				t.Fatal(err)
			}
			e2eTestFile(t, root, ref, "corrupt immutable packet")
			e2eTestFile(t, root, "request-000.md", "changed live source")
			before := e2eViewsTree(t, root)
			for _, view := range []string{"full", "compact"} {
				for _, args := range [][]string{{"status"}, {"task-show", "--task-id", "t000-1"}, {"task-show", "--task-id", "t001-1"}} {
					code, response := e2eTestCall(t, root, append(args, "--run-id", "run-1", "--view", view)...)
					data := response["data"].(map[string]any)
					if code != 10 || len(stringSliceFromAny(response["next_argv"])) != 0 || len(data["ready_actions"].([]any)) != 0 || data["recovery_blocked_by_immutable"] != true || data["submission_template"] != nil || data["review_template"] != nil {
						t.Fatalf("mixed failure advertised unusable recovery: %v", response)
					}
					if len(data["diagnostics"].([]any)) != 2 {
						t.Fatal("mixed failure hid a root")
					}
					for _, raw := range data["diagnostics"].([]any) {
						if len(stringSliceFromAny(raw.(map[string]any)["resume_argv"])) != 0 {
							t.Fatal("mutable root bypassed an immutable recovery prerequisite")
						}
					}
					if !reflect.DeepEqual(before, e2eViewsTree(t, root)) {
						t.Fatal("mixed-failure read changed state")
					}
				}
			}
			for _, args := range [][]string{{"reopen", "--task-id", "t000-1", "--leader-id", "leader", "--reason", "repair input", "--evidence-ref", "request-000.md"}, {"task-start", "--task-id", "t000-2", "--worker-id", "child"}} {
				code, response := e2eTestCall(t, root, append(args, "--run-id", "run-1", "--expected-revision", revision)...)
				if code != 10 || len(stringSliceFromAny(response["next_argv"])) != 0 || !reflect.DeepEqual(before, e2eViewsTree(t, root)) {
					t.Fatal("mixed-failure mutation changed state or advertised recovery")
				}
			}
			if err := os.WriteFile(path, original, 0o444); err != nil {
				t.Fatal(err)
			}
			code, response := e2eTestCall(t, root, "status", "--run-id", "run-1")
			if code != 10 || response["data"].(map[string]any)["recovery_blocked_by_immutable"] != false || !e2eContains(stringSliceFromAny(response["next_argv"]), "reopen") {
				t.Fatal("restored immutable bytes did not release the mutable repair gate")
			}
			e2eTestMutation(t, root, "reopen", "--task-id", "t000-1", "--leader-id", "leader", "--reason", "repair changed live source", "--evidence-ref", "request-000.md")
			fresh := e2eTestData(t, root, "task-show", "--run-id", "run-1", "--task-id", "t001-1")
			if !reflect.DeepEqual(fresh["submission_template"], second["submission_template"]) {
				t.Fatal("unrelated restored attempt was invalidated by mutable repair")
			}
		})
	}
}

func TestE2ER2CurrentCorruptionCannotHideBehindLiveDrift(t *testing.T) {
	for _, kind := range []string{"packet", "submission", "submission_archive", "review_packet", "review", "review_archive", "acceptance"} {
		t.Run(kind, func(t *testing.T) {
			root := e2eTestInit(t, "execution")
			ordinary := []string{"task-submit", "--task-id", "S1", "--worker-id", "worker-S1", "--result-json", "{}"}
			if kind == "packet" {
				e2eTestPrepareSubmission(t, root, "S1", "pass")
			} else {
				e2eTestStartAndSubmit(t, root, "S1", "pass")
				ordinary = []string{"review-start", "--task-id", "S1", "--validator-id", "validator-S1"}
			}
			if strings.HasPrefix(kind, "review") || kind == "acceptance" {
				review := e2eTestPrepareReview(t, root, "S1")
				ordinary = []string{"review-submit", "--task-id", "S1", "--validator-id", "validator-S1", "--result-json", e2eTestJSON(t, review)}
				if kind != "review_packet" {
					e2eTestMutation(t, root, ordinary[0], ordinary[1:]...)
					ordinary = []string{"task-accept", "--task-id", "S1", "--leader-id", "leader"}
				}
				if kind == "acceptance" {
					e2eTestMutation(t, root, ordinary[0], ordinary[1:]...)
					ordinary = []string{"task-start", "--task-id", "S2", "--worker-id", "worker-S2"}
				}
			}
			shown := e2eTestData(t, root, "task-show", "--run-id", "run-1", "--task-id", "S1")
			revision := strconv.Itoa(int(shown["revision"].(float64)))
			slot := strings.TrimSuffix(kind, "_archive")
			ref := shown["task"].(map[string]any)[slot].(map[string]any)["ref"].(string)
			if strings.HasSuffix(kind, "_archive") {
				raw, err := os.ReadFile(filepath.Join(root, filepath.FromSlash(ref)))
				if err != nil {
					t.Fatal(err)
				}
				var snapshot map[string]any
				if err := e2eDecode(raw, &snapshot); err != nil {
					t.Fatal(err)
				}
				ref = snapshot["evidence"].([]any)[0].(map[string]any)["archive_ref"].(string)
			}
			path := filepath.Join(root, filepath.FromSlash(ref))
			original, err := os.ReadFile(path)
			if err != nil {
				t.Fatal(err)
			}
			if err := os.Chmod(path, 0o644); err != nil {
				t.Fatal(err)
			}
			e2eTestFile(t, root, ref, "corrupt current immutable bytes")
			e2eTestFile(t, root, "request.md", "changed live input at the same time")
			before := e2eViewsTree(t, root)
			actions := [][]string{}
			for _, view := range []string{"full", "compact"} {
				actions = append(actions, []string{"status", "--view", view}, []string{"task-show", "--task-id", "S1", "--view", view})
			}
			actions = append(actions, append(append([]string{}, ordinary...), "--expected-revision", revision), []string{"reopen", "--task-id", "S1", "--leader-id", "leader", "--reason", "repair live source", "--evidence-ref", "request.md", "--expected-revision", revision})
			for _, args := range actions {
				code, response := e2eTestCall(t, root, append(args, "--run-id", "run-1")...)
				data := response["data"].(map[string]any)
				if code != 10 || len(stringSliceFromAny(response["next_argv"])) != 0 || data["submission_template"] != nil || data["review_template"] != nil || !reflect.DeepEqual(before, e2eViewsTree(t, root)) {
					t.Fatalf("live drift hid current corruption or allowed a reset: %v", response)
				}
				matched := false
				for _, raw := range data["diagnostics"].([]any) {
					d := raw.(map[string]any)
					if d["immutable"] == true && d["path"] == ref && d["root_task_id"] == "S1" && d["expected_sha256"] == fileContentSHA256(original) && d["observed_sha256"] == fileContentSHA256([]byte("corrupt current immutable bytes")) {
						matched = true
					}
					if len(stringSliceFromAny(d["resume_argv"])) != 0 {
						t.Fatal("corrupt current history advertised a recovery action")
					}
				}
				if !matched {
					t.Fatalf("missing exact current corruption diagnosis: %v", data)
				}
			}
			if err := os.WriteFile(path, original, 0o444); err != nil {
				t.Fatal(err)
			}
			restored := e2eViewsTree(t, root)
			code, response := e2eTestCall(t, root, "status", "--run-id", "run-1")
			data := response["data"].(map[string]any)
			if code != 10 || data["recovery_blocked_by_immutable"] != false || !e2eContains(stringSliceFromAny(response["next_argv"]), "reopen") || !reflect.DeepEqual(restored, e2eViewsTree(t, root)) {
				t.Fatal("exact restoration did not release only the mutable recovery gate")
			}
			code, response = e2eTestCall(t, root, append(append([]string{}, ordinary...), "--run-id", "run-1", "--expected-revision", revision)...)
			data = response["data"].(map[string]any)
			if code != 10 || data["revision"].(float64) != shown["revision"].(float64)+1 || len(data["invalidated_task_ids"].([]any)) != 7 {
				t.Fatalf("restored receipt did not allow precise mutable invalidation: %v", response)
			}
			if raw, err := os.ReadFile(path); err != nil || string(raw) != string(original) {
				t.Fatal("invalidation changed the restored immutable history")
			}
		})
	}
}
