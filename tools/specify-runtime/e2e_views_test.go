package main

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"reflect"
	"strconv"
	"strings"
	"testing"
)

func e2eViewsPlan(groups int, mode string) e2ePlanInput {
	plan := e2ePlanInput{Mode: mode, Scope: []e2eScope{}, Tasks: []e2eTaskSpec{}}
	for group := 0; group < groups; group++ {
		scope := fmt.Sprintf("scope-%03d", group)
		plan.Scope = append(plan.Scope, e2eScope{ID: scope, Target: "web", Operation: "save"})
		for stage := 1; stage <= 7; stage++ {
			id := fmt.Sprintf("T%03d-%d", group, stage)
			plan.Tasks = append(plan.Tasks, e2eTaskSpec{ID: id, Stage: stage, ScopeIDs: []string{scope}, Inputs: []string{}, Outputs: []string{"tests/e2e/" + id + ".md"}, Acceptance: []e2eCriterion{{ID: "complete", Criterion: "Account for the complete declared operation"}}})
		}
	}
	return plan
}

func e2eViewsTree(t *testing.T, root string) map[string]string {
	t.Helper()
	entries := map[string]string{}
	err := filepath.Walk(root, func(path string, info os.FileInfo, err error) error {
		if err != nil {
			return err
		}
		rel, err := filepath.Rel(root, path)
		if err != nil {
			return err
		}
		if info.IsDir() {
			entries[rel] = "directory"
			return nil
		}
		raw, err := os.ReadFile(path)
		if err == nil {
			entries[rel] = fileContentSHA256(raw)
		}
		return err
	})
	if err != nil {
		t.Fatal(err)
	}
	return entries
}

func TestE2EViewsCompactBoundsAndCompletePagination(t *testing.T) {
	sizes := map[int]int{}
	for _, count := range []int{7, 70, 700} {
		t.Run(strconv.Itoa(count), func(t *testing.T) {
			root := t.TempDir()
			plan := e2eViewsPlan(count/7, "execution")
			e2eTestData(t, root, "init", "--run-id", "run-1", "--leader-id", "leader", "--input-json", e2eTestJSON(t, plan), "--view", "compact")
			_, defaultFull := e2eTestCall(t, root, "status", "--run-id", "run-1")
			_, explicitFull := e2eTestCall(t, root, "status", "--run-id", "run-1", "--view", "full")
			if !reflect.DeepEqual(defaultFull, explicitFull) {
				t.Fatal("explicit full changed the default response")
			}
			full := defaultFull["data"].(map[string]any)
			if len(full["tasks"].([]any)) != count || len(full["scope"].([]any)) != count/7 {
				t.Fatal("full view lost the original denominator")
			}
			before := e2eViewsTree(t, root)
			seen := map[string]bool{}
			for offset := 0; offset < count; offset += e2eDefaultPageLimit {
				_, response := e2eTestCall(t, root, "status", "--run-id", "run-1", "--view", "compact", "--offset", strconv.Itoa(offset))
				data := response["data"].(map[string]any)
				counts := data["counts"].(map[string]any)
				if counts["task_count"] != float64(count) || counts["requested_task_count"] != float64(count) || counts["acceptance_row_count"] != float64(count) || counts["unaccepted_task_count"] != float64(count) || counts["nonpassing_task_count"] != float64(count) {
					t.Fatalf("page substituted for the complete denominator: %v", counts)
				}
				if data["revision"] != float64(1) || data["scope_count"] != float64(count/7) || len(data["stage_counts"].(map[string]any)) != 7 {
					t.Fatal("page lost global stage/scope/revision bindings")
				}
				rows := data["tasks"].([]any)
				if len(rows) > e2eDefaultPageLimit || len(data["gaps"].([]any)) != len(rows) {
					t.Fatal("compact response is not bounded or hid unresolved work")
				}
				for _, raw := range rows {
					row := raw.(map[string]any)
					id := row["id"].(string)
					if seen[id] || !e2eContains(stringSliceFromAny(data["task_show_argv"]), "<task-id>") {
						t.Fatalf("duplicate/unexpandable task %s", id)
					}
					seen[id] = true
				}
				next := data["next_page_argv"].([]any)
				if (offset+len(rows) < count) != (len(next) > 0) {
					t.Fatal("pagination ends before or after the complete denominator")
				}
				if offset == 0 {
					raw, _ := json.Marshal(response)
					sizes[count] = len(raw)
					fullRaw, _ := json.Marshal(defaultFull)
					t.Logf("tasks=%d compact_bytes=%d full_bytes=%d", count, len(raw), len(fullRaw))
					if len(raw) >= len(fullRaw) || (count >= 70 && len(raw)*2 >= len(fullRaw)) {
						t.Fatal("compact page did not materially reduce the full response")
					}
					if count == 7 {
						show := stringSliceFromAny(data["task_show_argv"])
						id := rows[0].(map[string]any)["id"].(string)
						for i := range show {
							if show[i] == "<task-id>" {
								show[i] = id
							}
						}
						code, shown := e2ePublicCall(t, show[1:]...)
						if code != 0 || shown["data"].(map[string]any)["selected_task_id"] != id {
							t.Fatal("shared task-show template is not executable for the selected row")
						}
					}
				}
			}
			if len(seen) != count || !reflect.DeepEqual(before, e2eViewsTree(t, root)) {
				t.Fatal("pagination omitted tasks or wrote project state")
			}
		})
	}
	if sizes[700] > sizes[70]+2048 {
		t.Fatalf("page output grew with the full task denominator: %v", sizes)
	}
}

func TestE2EViewsPlanningCountsAndPageOptions(t *testing.T) {
	root := t.TempDir()
	data := e2eTestData(t, root, "init", "--run-id", "run-1", "--leader-id", "leader", "--input-json", e2eTestJSON(t, e2eViewsPlan(1, "planning")), "--view", "compact", "--limit", "2")
	counts := data["counts"].(map[string]any)
	if counts["task_count"] != float64(7) || counts["requested_task_count"] != float64(4) || counts["acceptance_row_count"] != float64(7) || counts["requested_acceptance_row_count"] != float64(4) || data["product_pass"] != false {
		t.Fatalf("planning denominator or execution claim changed: %v", data)
	}
	last := e2eTestData(t, root, "status", "--run-id", "run-1", "--view", "compact", "--offset", "999", "--limit", "200")
	if len(last["tasks"].([]any)) != 0 || len(last["next_page_argv"].([]any)) != 0 || last["counts"].(map[string]any)["task_count"] != float64(7) {
		t.Fatal("out-of-range page hid the total or invented a next page")
	}
	for _, args := range [][]string{{"--view", "tiny"}, {"--offset", "1"}, {"--view", "full", "--limit", "1"}, {"--view", "compact", "--offset", "-1"}, {"--view", "compact", "--offset", "x"}, {"--view", "compact", "--limit", "0"}, {"--view", "compact", "--limit", "201"}, {"--view", "compact", "--limit", "1.5"}} {
		code, _ := e2eTestCall(t, root, append([]string{"status", "--run-id", "run-1"}, args...)...)
		if code != 2 {
			t.Fatalf("invalid view accepted: %v (exit %d)", args, code)
		}
	}
}

func e2eViewsFillSubmission(t *testing.T, root string, shown map[string]any) map[string]any {
	t.Helper()
	input := shown["submission_template"].(map[string]any)
	input["outcome"] = "pass"
	input["worker_result"] = map[string]any{"task_id": "S1", "packet_id": shown["packet_sha256"], "status": "success", "summary": "Synthetic protocol stage produced its declared report."}
	e2eTestFile(t, root, "tests/e2e/s1.md", "Synthetic stage report\n")
	e2eTestFile(t, root, "tests/e2e/view-evidence.txt", "Inspected synthetic stage report against declared contract\n")
	for _, raw := range input["checks"].([]any) {
		row := raw.(map[string]any)
		row["status"], row["actual"], row["reproduction"], row["preconditions"] = "passed", "The declared report exists and matches the fixture", "Read the fixture report against the immutable contract", "Synthetic protocol test in an isolated directory"
		row["evidence_refs"] = []any{"tests/e2e/view-evidence.txt"}
	}
	return input
}

func e2eViewsFillReview(t *testing.T, root string, shown map[string]any) map[string]any {
	t.Helper()
	input := shown["review_template"].(map[string]any)
	e2eTestFile(t, root, "tests/e2e/view-review-evidence.txt", "Independent protocol fixture inspection\n")
	for _, raw := range input["checks"].([]any) {
		row := raw.(map[string]any)
		row["status"], row["method"], row["actual"] = "passed", "inspected", "The complete assigned report matches its contract"
		row["reproduction"], row["preconditions"] = "Inspect the archived fixture report and original task contract", "Synthetic independent review fixture"
		row["evidence_refs"] = []any{"tests/e2e/view-review-evidence.txt"}
	}
	return input
}

func TestE2EViewsTaskShowRestoresExactTemplatesWithoutWrites(t *testing.T) {
	root := e2eTestInit(t, "execution")
	started := e2eTestMutation(t, root, "task-start", "--task-id", "S1", "--worker-id", "worker-S1", "--view", "compact")
	if _, duplicate := started["packet"]; duplicate || started["worker_task_packet"] == nil {
		t.Fatal("compact dispatch duplicated the enclosing packet or lost the standard packet")
	}
	lockPath := filepath.Join(root, ".specify", "runtime", "e2e", "locks", "run-1.lock")
	if err := os.Remove(lockPath); err != nil && !os.IsNotExist(err) {
		t.Fatal(err)
	}
	before := e2eViewsTree(t, root)
	for _, view := range []string{"full", "compact"} {
		shown := e2eTestData(t, root, "task-show", "--run-id", "run-1", "--task-id", "S1", "--view", view)
		if shown["packet_sha256"] != started["packet_sha256"] || shown["attempt_id"] != started["attempt_id"] || !reflect.DeepEqual(shown["submission_template"], started["submission_template"]) || !reflect.DeepEqual(shown["worker_task_packet_binding"], started["worker_task_packet_binding"]) || shown["resume_available"] != true {
			t.Fatal("task-show changed the frozen attempt or submission template")
		}
		if shown["submission_template"].(map[string]any)["worker_result"].(map[string]any)["status"] != "pending" {
			t.Fatal("reading a template invented a passing observation")
		}
		if !reflect.DeepEqual(before, e2eViewsTree(t, root)) {
			t.Fatal("task-show wrote files, a mutation lock, or state revision")
		}
	}
	input := e2eViewsFillSubmission(t, root, started)
	e2eTestMutation(t, root, "task-submit", "--task-id", "S1", "--worker-id", "worker-S1", "--result-json", e2eTestJSON(t, input), "--view", "compact")
	review := e2eTestMutation(t, root, "review-start", "--task-id", "S1", "--validator-id", "validator-S1", "--view", "compact")
	before = e2eViewsTree(t, root)
	for _, view := range []string{"full", "compact"} {
		shown := e2eTestData(t, root, "task-show", "--run-id", "run-1", "--task-id", "S1", "--view", view)
		if shown["review_packet_sha256"] != review["review_packet_sha256"] || !reflect.DeepEqual(shown["review_template"], review["review_template"]) || !reflect.DeepEqual(shown["worker_task_packet_binding"], review["worker_task_packet_binding"]) || shown["resume_available"] != true {
			t.Fatal("task-show changed the independent review binding")
		}
		if _, wrongTemplate := shown["submission_template"]; wrongTemplate || !reflect.DeepEqual(before, e2eViewsTree(t, root)) {
			t.Fatal("review resume exposed a worker submission or mutated the run")
		}
	}
}

func TestE2EViewsTaskShowRefusesStaleAndCorruptTemplates(t *testing.T) {
	for _, kind := range []string{"source", "packet", "archive", "history"} {
		t.Run(kind, func(t *testing.T) {
			root := e2eTestInit(t, "execution")
			started := e2eTestMutation(t, root, "task-start", "--task-id", "S1", "--worker-id", "worker-S1")
			path := "request.md"
			if kind == "packet" || kind == "history" {
				path = started["packet_ref"].(string)
			}
			if kind == "archive" {
				path = started["packet"].(map[string]any)["inputs"].([]any)[0].(map[string]any)["archive_ref"].(string)
			}
			if kind == "history" {
				e2eTestMutation(t, root, "reopen", "--task-id", "S1", "--leader-id", "leader", "--reason", "Synthetic interruption requires a new attempt", "--evidence-ref", "request.md")
			}
			absolute := filepath.Join(root, filepath.FromSlash(path))
			if err := os.Chmod(absolute, 0o644); err != nil {
				t.Fatal(err)
			}
			e2eTestFile(t, root, path, "Changed bytes\n")
			before := e2eViewsTree(t, root)
			for _, view := range []string{"full", "compact"} {
				code, response := e2eTestCall(t, root, "task-show", "--run-id", "run-1", "--task-id", "S1", "--view", view)
				data := response["data"].(map[string]any)
				if code != 10 || data["submission_template"] != nil || data["review_template"] != nil || data["resume_available"] == true {
					t.Fatalf("%s exposed a usable stale template: %v", kind, response)
				}
				if !reflect.DeepEqual(before, e2eViewsTree(t, root)) {
					t.Fatal("failed read changed project state")
				}
			}
		})
	}
	root := t.TempDir()
	before := e2eViewsTree(t, root)
	code, _ := e2eTestCall(t, root, "task-show", "--run-id", "missing", "--task-id", "S1")
	if code != 10 || !reflect.DeepEqual(before, e2eViewsTree(t, root)) {
		t.Fatal("reading a missing run created runtime storage")
	}
}

func TestE2EViewsResumeRejectsOldAttempts(t *testing.T) {
	root := e2eTestInit(t, "execution")
	first := e2eTestMutation(t, root, "task-start", "--task-id", "S1", "--worker-id", "worker-S1")
	oldSubmission := e2eViewsFillSubmission(t, root, first)
	e2eTestMutation(t, root, "task-submit", "--task-id", "S1", "--worker-id", "worker-S1", "--result-json", e2eTestJSON(t, oldSubmission))
	e2eTestMutation(t, root, "review-start", "--task-id", "S1", "--validator-id", "validator-S1")
	oldReview := e2eViewsFillReview(t, root, e2eTestData(t, root, "task-show", "--run-id", "run-1", "--task-id", "S1"))
	e2eTestMutation(t, root, "reopen", "--task-id", "S1", "--leader-id", "leader", "--reason", "Synthetic interruption requires repair and fresh review", "--evidence-ref", "tests/e2e/view-review-evidence.txt")
	e2eTestMutation(t, root, "task-start", "--task-id", "S1", "--worker-id", "worker-S1")
	second := e2eTestData(t, root, "task-show", "--run-id", "run-1", "--task-id", "S1", "--view", "compact")
	if second["packet_sha256"] == first["packet_sha256"] || second["attempt_id"] == first["attempt_id"] {
		t.Fatal("new attempt reused an old binding")
	}
	before := e2eViewsTree(t, root)
	code, _ := e2eTestCall(t, root, "task-submit", "--run-id", "run-1", "--task-id", "S1", "--worker-id", "worker-S1", "--expected-revision", e2eTestRevision(t, root), "--result-json", e2eTestJSON(t, oldSubmission))
	if code != 2 {
		t.Fatal("old submission was accepted")
	}
	// Rejected submissions remain immutable audit input under the native owner;
	// they cannot replace the current packet or become accepted source evidence.
	audited := e2eTestData(t, root, "task-show", "--run-id", "run-1", "--task-id", "S1", "--view", "compact")
	if audited["packet_sha256"] != second["packet_sha256"] || audited["attempt_id"] != second["attempt_id"] || audited["task"].(map[string]any)["status"] != "running" {
		t.Fatal("rejected old submission replaced the active attempt")
	}
	newSubmission := e2eViewsFillSubmission(t, root, second)
	e2eTestMutation(t, root, "task-submit", "--task-id", "S1", "--worker-id", "worker-S1", "--result-json", e2eTestJSON(t, newSubmission))
	e2eTestMutation(t, root, "review-start", "--task-id", "S1", "--validator-id", "validator-S1")
	current := e2eTestData(t, root, "task-show", "--run-id", "run-1", "--task-id", "S1", "--view", "compact")
	before = e2eViewsTree(t, root)
	code, _ = e2eTestCall(t, root, "review-submit", "--run-id", "run-1", "--task-id", "S1", "--validator-id", "validator-S1", "--expected-revision", e2eTestRevision(t, root), "--result-json", e2eTestJSON(t, oldReview))
	if code != 2 || !reflect.DeepEqual(before, e2eViewsTree(t, root)) {
		t.Fatal("old review was accepted or mutated state")
	}
	newReview := e2eViewsFillReview(t, root, current)
	e2eTestMutation(t, root, "review-submit", "--task-id", "S1", "--validator-id", "validator-S1", "--result-json", e2eTestJSON(t, newReview), "--view", "compact")
}

func TestE2EViewsClosedRunDoesNotOfferSubmissionResume(t *testing.T) {
	root := e2eTestInit(t, "execution")
	e2eTestMutation(t, root, "task-start", "--task-id", "S1", "--worker-id", "worker-S1")
	for _, id := range []string{"S6", "S7"} {
		input := e2eTestPrepareSubmission(t, root, id, "blocked", "--diagnostic")
		e2eTestMutation(t, root, "task-submit", "--task-id", id, "--worker-id", "worker-"+id, "--result-json", e2eTestJSON(t, input))
		e2eTestReviewAndAccept(t, root, id)
	}
	e2eTestMutation(t, root, "close", "--leader-id", "leader", "--outcome", "blocked", "--view", "compact")
	before := e2eViewsTree(t, root)
	for _, view := range []string{"full", "compact"} {
		code, response := e2eTestCall(t, root, "task-show", "--run-id", "run-1", "--task-id", "S1", "--view", view)
		data := response["data"].(map[string]any)
		if code != 0 || data["resume_available"] != false || data["submission_template"] != nil || data["review_template"] != nil || len(response["next_argv"].([]any)) != 0 {
			t.Fatal("a closed run exposed ordinary task progression")
		}
		if !reflect.DeepEqual(before, e2eViewsTree(t, root)) {
			t.Fatal("reading a closed run wrote state")
		}
	}
}

func TestE2EViewsCapabilityContracts(t *testing.T) {
	for _, id := range []string{"e2e.compact", "e2e.task-show"} {
		descriptor, ok := e2eCapabilityDescriptor(id)
		if !ok || !e2eContains(e2eCapabilityIDs(), id) || descriptor["input_contract"] == "" {
			t.Fatalf("capability is not discoverable: %s", id)
		}
	}
	descriptor, _ := e2eCapabilityDescriptor("e2e.task-show")
	if descriptor["side_effect"] != "read-only" || strings.Contains(descriptor["usage"].(string), "--expected-revision") {
		t.Fatal("task-show advertises a mutation contract")
	}
	if e2eContains(e2eActions, "compact") {
		t.Fatal("compact is an output feature, not a command")
	}
}
