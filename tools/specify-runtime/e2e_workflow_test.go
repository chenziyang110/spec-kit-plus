package main

import (
	"bytes"
	"encoding/json"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"testing"
)

func e2eTestFile(t *testing.T, root, name, body string) {
	t.Helper()
	path := filepath.Join(root, filepath.FromSlash(name))
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(path, []byte(body), 0o644); err != nil {
		t.Fatal(err)
	}
}

func e2eTestCall(t *testing.T, root string, args ...string) (int, map[string]any) {
	t.Helper()
	var out bytes.Buffer
	code := runE2E(append(args, "--project-root", root, "--format", "json"), &out)
	var result map[string]any
	if err := json.Unmarshal(out.Bytes(), &result); err != nil {
		t.Fatalf("%v: %v: %s", args, err, out.String())
	}
	return code, result
}

func e2eTestData(t *testing.T, root string, args ...string) map[string]any {
	t.Helper()
	code, result := e2eTestCall(t, root, args...)
	if code != 0 {
		t.Fatalf("%v: %v", args, result)
	}
	return result["data"].(map[string]any)
}

func e2eTestJSON(t *testing.T, value any) string {
	t.Helper()
	raw, err := json.Marshal(value)
	if err != nil {
		t.Fatal(err)
	}
	return string(raw)
}

func e2eTestPlan(mode string) map[string]any {
	tasks := []any{}
	for stage := 1; stage <= 7; stage++ {
		tasks = append(tasks, map[string]any{
			"id": "S" + strconv.Itoa(stage), "stage": stage,
			"scope_ids": []any{"web-save"}, "inputs": []any{"request.md"},
			"outputs":    []any{"tests/e2e/s" + strconv.Itoa(stage) + ".md"},
			"acceptance": []any{map[string]any{"id": "complete", "criterion": "Every requested save behavior is accounted for with reproducible evidence"}},
		})
	}
	return map[string]any{"mode": mode, "scope": []any{map[string]any{"id": "web-save", "target": "web", "operation": "save"}}, "tasks": tasks}
}

func e2eTestInit(t *testing.T, mode string) string {
	t.Helper()
	root := t.TempDir()
	e2eTestFile(t, root, "request.md", "Cover save on the web target, including the persisted readback.\n")
	e2eTestData(t, root, "init", "--run-id", "run-1", "--leader-id", "leader", "--input-json", e2eTestJSON(t, e2eTestPlan(mode)))
	return root
}

func e2eTestRevision(t *testing.T, root string) string {
	t.Helper()
	_, result := e2eTestCall(t, root, "status", "--run-id", "run-1")
	return strconv.Itoa(int(result["data"].(map[string]any)["revision"].(float64)))
}

func e2eTestMutation(t *testing.T, root, action string, args ...string) map[string]any {
	t.Helper()
	full := []string{action, "--run-id", "run-1", "--expected-revision", e2eTestRevision(t, root)}
	return e2eTestData(t, root, append(full, args...)...)
}

func e2eTestPrepareSubmission(t *testing.T, root, id, outcome string, extra ...string) map[string]any {
	t.Helper()
	started := e2eTestMutation(t, root, "task-start", append([]string{"--task-id", id, "--worker-id", "worker-" + id}, extra...)...)
	input := started["submission_template"].(map[string]any)
	input["outcome"] = outcome
	input["worker_result"] = map[string]any{"task_id": id, "packet_id": started["packet_sha256"], "status": "success", "summary": "The complete assigned report is ready for independent inspection."}
	evidence := "tests/e2e/evidence-" + id + ".txt"
	e2eTestFile(t, root, evidence, "Observed persisted value equals expected value; exact replay sequence recorded.\n")
	for _, raw := range input["checks"].([]any) {
		row := raw.(map[string]any)
		row["status"], row["expected"], row["actual"] = "passed", "Persisted readback equals the save input", "Persisted readback equals the save input"
		row["reproduction"], row["preconditions"], row["evidence_refs"] = "Open fixture, save, reopen, inspect readback", "Isolated test account and reset fixture", []any{evidence}
	}
	e2eTestFile(t, root, "tests/e2e/"+strings.ToLower(id)+".md", "Complete stage report for "+id+"\n")
	return input
}

func e2eTestStartAndSubmit(t *testing.T, root, id, outcome string) map[string]any {
	t.Helper()
	input := e2eTestPrepareSubmission(t, root, id, outcome)
	return e2eTestMutation(t, root, "task-submit", "--task-id", id, "--worker-id", "worker-"+id, "--result-json", e2eTestJSON(t, input))
}

func e2eTestPrepareReview(t *testing.T, root, id string) map[string]any {
	t.Helper()
	started := e2eTestMutation(t, root, "review-start", "--task-id", id, "--validator-id", "validator-"+id)
	input := started["review_template"].(map[string]any)
	evidence := "tests/e2e/review-evidence-" + id + ".txt"
	e2eTestFile(t, root, evidence, "Independent replay and complete assigned-row reconciliation.\n")
	for _, raw := range input["checks"].([]any) {
		row := raw.(map[string]any)
		row["status"], row["method"] = "passed", "replayed"
		row["expected"], row["actual"] = "Every assigned acceptance row has reproducible evidence", "Every assigned acceptance row has reproducible evidence"
		row["reproduction"], row["preconditions"], row["evidence_refs"] = "Replay recorded sequence and compare original files", "Same isolated fixture and recorded build", []any{evidence}
	}
	return input
}

func e2eTestReviewAndAccept(t *testing.T, root, id string) {
	t.Helper()
	input := e2eTestPrepareReview(t, root, id)
	e2eTestMutation(t, root, "review-submit", "--task-id", id, "--validator-id", "validator-"+id, "--result-json", e2eTestJSON(t, input))
	e2eTestMutation(t, root, "task-accept", "--task-id", id, "--leader-id", "leader")
}

func e2eTestCompleteTask(t *testing.T, root, id string) {
	t.Helper()
	e2eTestStartAndSubmit(t, root, id, "pass")
	e2eTestReviewAndAccept(t, root, id)
}

func TestE2EUnacceptedProducerCannotStartConsumer(t *testing.T) {
	root := e2eTestInit(t, "execution")
	e2eTestStartAndSubmit(t, root, "S1", "pass")
	code, result := e2eTestCall(t, root, "task-start", "--run-id", "run-1", "--task-id", "S2", "--worker-id", "worker-S2", "--expected-revision", e2eTestRevision(t, root))
	if code == 0 || !strings.Contains(e2eTestJSON(t, result), "accepted") {
		t.Fatalf("unaccepted producer was consumed: %v", result)
	}
	e2eTestReviewAndAccept(t, root, "S1")
	e2eTestMutation(t, root, "task-start", "--task-id", "S2", "--worker-id", "worker-S2")
}

func TestE2EAuthorCannotActAsIndependentValidator(t *testing.T) {
	root := e2eTestInit(t, "execution")
	e2eTestStartAndSubmit(t, root, "S1", "pass")
	for _, identity := range []string{"worker-S1", "leader"} {
		code, result := e2eTestCall(t, root, "review-start", "--run-id", "run-1", "--task-id", "S1", "--validator-id", identity, "--expected-revision", e2eTestRevision(t, root))
		if code == 0 {
			t.Fatalf("non-independent reviewer %s accepted: %v", identity, result)
		}
	}
}

func TestE2EFullSevenStageClosureAndDriftInvalidation(t *testing.T) {
	root := e2eTestInit(t, "execution")
	for stage := 1; stage <= 7; stage++ {
		e2eTestCompleteTask(t, root, "S"+strconv.Itoa(stage))
	}
	closed := e2eTestMutation(t, root, "close", "--leader-id", "leader", "--outcome", "pass")
	if closed["status"] != "complete" || closed["product_pass"] != true {
		t.Fatalf("wrong closure: %v", closed)
	}
	e2eTestFile(t, root, "tests/e2e/s1.md", "Changed producer bytes; old consumers are no longer valid.\n")
	code, result := e2eTestCall(t, root, "close", "--run-id", "run-1", "--leader-id", "leader", "--outcome", "pass", "--expected-revision", e2eTestRevision(t, root))
	if code == 0 {
		t.Fatalf("changed producer retained a pass: %v", result)
	}
	data := result["data"].(map[string]any)
	if data["product_pass"] == true {
		t.Fatal("drift retained product_pass")
	}
	for _, raw := range data["tasks"].([]any) {
		if raw.(map[string]any)["status"] == "accepted" {
			t.Fatalf("descendant acceptance survived: %v", raw)
		}
	}
}

func TestE2EPlanningClosureNeverClaimsExecutionPass(t *testing.T) {
	root := e2eTestInit(t, "planning")
	for _, id := range []string{"S1", "S2", "S6", "S7"} {
		e2eTestCompleteTask(t, root, id)
	}
	closed := e2eTestMutation(t, root, "close", "--leader-id", "leader", "--outcome", "pass")
	if closed["status"] != "planning-complete" || closed["product_pass"] != false {
		t.Fatalf("planning misreported execution: %v", closed)
	}
}

func TestE2EInitRejectsMissingPlatformAndStageCoverage(t *testing.T) {
	root := t.TempDir()
	plan := e2eTestPlan("execution")
	plan["scope"] = append(plan["scope"].([]any), map[string]any{"id": "ios-save", "target": "ios", "operation": "save"})
	code, _ := e2eTestCall(t, root, "init", "--run-id", "run-1", "--leader-id", "leader", "--input-json", e2eTestJSON(t, plan))
	if code == 0 {
		t.Fatal("uncovered requested platform disappeared from the denominator")
	}
}

func TestE2ESubmissionRejectsIncompleteAndUnreproducibleRows(t *testing.T) {
	cases := map[string]func(map[string]any){
		"missing row":      func(input map[string]any) { input["checks"] = []any{} },
		"duplicate row":    func(input map[string]any) { rows := input["checks"].([]any); input["checks"] = append(rows, rows[0]) },
		"wrong scope":      func(input map[string]any) { input["checks"].([]any)[0].(map[string]any)["scope_id"] = "untested-ios" },
		"missing expected": func(input map[string]any) { input["checks"].([]any)[0].(map[string]any)["expected"] = "" },
		"missing actual":   func(input map[string]any) { input["checks"].([]any)[0].(map[string]any)["actual"] = "" },
		"missing replay":   func(input map[string]any) { input["checks"].([]any)[0].(map[string]any)["reproduction"] = "" },
		"missing evidence": func(input map[string]any) { input["checks"].([]any)[0].(map[string]any)["evidence_refs"] = []any{} },
		"unavailable evidence": func(input map[string]any) {
			input["checks"].([]any)[0].(map[string]any)["evidence_refs"] = []any{"tests/e2e/missing.txt"}
		},
		"unsafe evidence": func(input map[string]any) {
			input["checks"].([]any)[0].(map[string]any)["evidence_refs"] = []any{"../outside.txt"}
		},
		"green aggregate hides skipped row": func(input map[string]any) { input["checks"].([]any)[0].(map[string]any)["status"] = "skipped" },
		"wrong packet":                      func(input map[string]any) { input["packet_sha256"] = strings.Repeat("0", 64) },
		"worker result from different task": func(input map[string]any) { input["worker_result"].(map[string]any)["task_id"] = "S2" },
		"pending worker result":             func(input map[string]any) { input["worker_result"].(map[string]any)["status"] = "pending" },
	}
	for name, mutate := range cases {
		t.Run(name, func(t *testing.T) {
			root := e2eTestInit(t, "execution")
			input := e2eTestPrepareSubmission(t, root, "S1", "pass")
			mutate(input)
			code, result := e2eTestCall(t, root, "task-submit", "--run-id", "run-1", "--task-id", "S1", "--worker-id", "worker-S1", "--expected-revision", e2eTestRevision(t, root), "--result-json", e2eTestJSON(t, input))
			if code == 0 {
				t.Fatalf("invalid result reached submitted: %v", result)
			}
		})
	}
}

func TestE2EConsumerPacketCarriesAcceptedProducerOutputs(t *testing.T) {
	root := e2eTestInit(t, "execution")
	e2eTestCompleteTask(t, root, "S1")
	started := e2eTestMutation(t, root, "task-start", "--task-id", "S2", "--worker-id", "worker-S2")
	packet := started["packet"].(map[string]any)
	deps := packet["dependencies"].([]any)
	if len(deps) != 1 {
		t.Fatalf("S2 does not consume S1: %v", packet)
	}
	outputs, ok := deps[0].(map[string]any)["outputs"].([]any)
	if !ok || len(outputs) != 1 || outputs[0].(map[string]any)["path"] != "tests/e2e/s1.md" {
		t.Fatalf("consumer lacks actual output binding: %v", deps)
	}
	if len(outputs[0].(map[string]any)["sha256"].(string)) != 64 {
		t.Fatal("consumer has no producer byte hash")
	}
}

func TestE2EIndependentTasksAndExclusiveResourceGates(t *testing.T) {
	for _, mode := range []string{"independent", "resource", "output", "revision"} {
		t.Run(mode, func(t *testing.T) {
			root := t.TempDir()
			e2eTestFile(t, root, "request.md", "Save request")
			plan := e2eTestPlan("execution")
			tasks := plan["tasks"].([]any)
			first := tasks[0].(map[string]any)
			second := map[string]any{"id": "S1b", "stage": 1, "scope_ids": first["scope_ids"], "inputs": first["inputs"], "outputs": []any{"tests/e2e/another-inventory.md"}, "acceptance": first["acceptance"]}
			if mode == "resource" {
				first["resources"], second["resources"] = []any{"device:simulator-one"}, []any{"device:simulator-one"}
			}
			if mode == "output" {
				second["outputs"] = first["outputs"]
			}
			plan["tasks"] = append(tasks, second)
			e2eTestData(t, root, "init", "--run-id", "run-1", "--leader-id", "leader", "--input-json", e2eTestJSON(t, plan))
			oldRevision := e2eTestRevision(t, root)
			e2eTestMutation(t, root, "task-start", "--task-id", "S1", "--worker-id", "worker-S1")
			revision := e2eTestRevision(t, root)
			if mode == "revision" {
				revision = oldRevision
			}
			code, result := e2eTestCall(t, root, "task-start", "--run-id", "run-1", "--task-id", "S1b", "--worker-id", "worker-S1b", "--expected-revision", revision)
			if mode == "independent" && code != 0 {
				t.Fatalf("independent lane was serialized: %v", result)
			}
			if mode != "independent" && code == 0 {
				t.Fatalf("conflicting lane was admitted: %v", result)
			}
			if mode == "revision" {
				e2eTestMutation(t, root, "task-start", "--task-id", "S1b", "--worker-id", "worker-S1b")
			}
		})
	}
}

func TestE2EFailureReportCannotUnlockExecutionOrFullPass(t *testing.T) {
	root := e2eTestInit(t, "execution")
	for _, id := range []string{"S1", "S2"} {
		e2eTestCompleteTask(t, root, id)
	}
	e2eTestStartAndSubmit(t, root, "S3", "blocked")
	e2eTestReviewAndAccept(t, root, "S3")
	code, _ := e2eTestCall(t, root, "task-start", "--run-id", "run-1", "--task-id", "S4", "--worker-id", "worker-S4", "--expected-revision", e2eTestRevision(t, root))
	if code == 0 {
		t.Fatal("accepted blocked readiness report unlocked execution")
	}
	for _, id := range []string{"S6", "S7"} {
		input := e2eTestPrepareSubmission(t, root, id, "blocked", "--diagnostic")
		if id == "S6" {
			input["outcome"] = "pass"
			code, _ := e2eTestCall(t, root, "task-submit", "--run-id", "run-1", "--task-id", id, "--worker-id", "worker-"+id, "--expected-revision", e2eTestRevision(t, root), "--result-json", e2eTestJSON(t, input))
			if code == 0 {
				t.Fatal("diagnostic audit claimed a pass")
			}
			input["outcome"] = "blocked"
		}
		e2eTestMutation(t, root, "task-submit", "--task-id", id, "--worker-id", "worker-"+id, "--result-json", e2eTestJSON(t, input))
		e2eTestReviewAndAccept(t, root, id)
	}
	code, _ = e2eTestCall(t, root, "close", "--run-id", "run-1", "--leader-id", "leader", "--outcome", "pass", "--expected-revision", e2eTestRevision(t, root))
	if code == 0 {
		t.Fatal("unexecuted mandatory stages closed as pass")
	}
	closed := e2eTestMutation(t, root, "close", "--leader-id", "leader", "--outcome", "blocked")
	if closed["status"] != "blocked" || closed["product_pass"] != false {
		t.Fatalf("blocked report concealed unresolved work: %v", closed)
	}
}

func TestE2EAllAcceptedFailureReportClosesAsReported(t *testing.T) {
	root := e2eTestInit(t, "execution")
	for stage := 1; stage <= 7; stage++ {
		id, outcome := "S"+strconv.Itoa(stage), "pass"
		if stage == 4 {
			outcome = "failed"
		}
		e2eTestStartAndSubmit(t, root, id, outcome)
		e2eTestReviewAndAccept(t, root, id)
	}
	code, _ := e2eTestCall(t, root, "close", "--run-id", "run-1", "--leader-id", "leader", "--outcome", "pass", "--expected-revision", e2eTestRevision(t, root))
	if code == 0 {
		t.Fatal("observed product failure became a pass")
	}
	closed := e2eTestMutation(t, root, "close", "--leader-id", "leader", "--outcome", "failed")
	if closed["status"] != "reported" || closed["product_pass"] != false {
		t.Fatalf("accepted failure report misclassified: %v", closed)
	}
}

func TestE2ERejectionAndRepairRequireFreshIndependentReview(t *testing.T) {
	root := e2eTestInit(t, "execution")
	e2eTestStartAndSubmit(t, root, "S1", "pass")
	oldReview := e2eTestPrepareReview(t, root, "S1")
	oldReview["checks"].([]any)[0].(map[string]any)["status"] = "failed"
	code, _ := e2eTestCall(t, root, "review-submit", "--run-id", "run-1", "--task-id", "S1", "--validator-id", "validator-S1", "--expected-revision", e2eTestRevision(t, root), "--result-json", e2eTestJSON(t, oldReview))
	if code == 0 {
		t.Fatal("rejected review reported verification success")
	}
	code, _ = e2eTestCall(t, root, "task-accept", "--run-id", "run-1", "--task-id", "S1", "--leader-id", "leader", "--expected-revision", e2eTestRevision(t, root))
	if code == 0 {
		t.Fatal("leader accepted a rejected result")
	}
	e2eTestMutation(t, root, "reopen", "--task-id", "S1", "--leader-id", "leader", "--reason", "Replay revealed an omitted persistence observation", "--evidence-ref", "tests/e2e/review-evidence-S1.txt")
	e2eTestStartAndSubmit(t, root, "S1", "pass")
	newReview := e2eTestPrepareReview(t, root, "S1")
	oldReview["checks"].([]any)[0].(map[string]any)["status"] = "passed"
	code, _ = e2eTestCall(t, root, "review-submit", "--run-id", "run-1", "--task-id", "S1", "--validator-id", "validator-S1", "--expected-revision", e2eTestRevision(t, root), "--result-json", e2eTestJSON(t, oldReview))
	if code == 0 {
		t.Fatal("old review was transplanted onto repaired output")
	}
	e2eTestMutation(t, root, "review-submit", "--task-id", "S1", "--validator-id", "validator-S1", "--result-json", e2eTestJSON(t, newReview))
	e2eTestMutation(t, root, "task-accept", "--task-id", "S1", "--leader-id", "leader")
}

func TestE2EScopeExpansionPreservesTargetsAndInvalidatesAffectedStages(t *testing.T) {
	root := e2eTestInit(t, "execution")
	for stage := 1; stage <= 7; stage++ {
		e2eTestCompleteTask(t, root, "S"+strconv.Itoa(stage))
	}
	extra := map[string]any{"scope": []any{}, "tasks": []any{map[string]any{"id": "S2-new-condition", "stage": 2, "scope_ids": []any{"web-save"}, "inputs": []any{"request.md"}, "outputs": []any{"tests/e2e/new-condition.md"}, "acceptance": []any{map[string]any{"id": "event-order", "criterion": "Account for a save while an external rename occurs"}}}}}
	data := e2eTestMutation(t, root, "scope-add", "--leader-id", "leader", "--reason", "Audit discovered an event-order omission", "--evidence-ref", "tests/e2e/review-evidence-S6.txt", "--input-json", e2eTestJSON(t, extra))
	if len(data["scope"].([]any)) != 1 {
		t.Fatal("scope expansion removed the original target")
	}
	for _, raw := range data["tasks"].([]any) {
		task := raw.(map[string]any)
		if task["id"] == "S1" {
			if task["status"] != "accepted" {
				t.Fatal("unaffected inventory lost acceptance")
			}
		} else if task["status"] == "accepted" {
			t.Fatalf("affected consumer acceptance survived: %v", task)
		}
	}
	bad := map[string]any{"scope": []any{map[string]any{"id": "web-save", "target": "ios", "operation": "save"}}, "tasks": []any{}}
	code, _ := e2eTestCall(t, root, "scope-add", "--run-id", "run-1", "--leader-id", "leader", "--expected-revision", e2eTestRevision(t, root), "--reason", "Replace the old target", "--evidence-ref", "request.md", "--input-json", e2eTestJSON(t, bad))
	if code == 0 {
		t.Fatal("scope-add replaced an existing requested target")
	}
}

func TestE2ESourceDriftBetweenValidationAndCommitRejectsAllWrites(t *testing.T) {
	root := e2eTestInit(t, "execution")
	statePath := filepath.Join(root, ".planning/e2e/run-1/state.json")
	before, err := os.ReadFile(statePath)
	if err != nil {
		t.Fatal(err)
	}
	service := &e2eService{projectRoot: root, runID: "run-1", rootRef: ".planning/e2e/run-1", observed: map[string]string{}, beforeCommit: func() error {
		return os.WriteFile(filepath.Join(root, "request.md"), []byte("Changed concurrently before publish"), 0o644)
	}}
	env := service.run("task-start", []string{"--task-id", "S1", "--worker-id", "worker-S1", "--expected-revision", "1"})
	if env.Status == "ok" {
		t.Fatal("source changed after packet construction but task-start committed")
	}
	after, err := os.ReadFile(statePath)
	if err != nil || !bytes.Equal(before, after) {
		t.Fatalf("failed CAS partially mutated canonical state: %v", err)
	}
}

func TestE2ERejectsDuplicateJSONKeysAndDependencyCycles(t *testing.T) {
	root := t.TempDir()
	plan := e2eTestJSON(t, e2eTestPlan("execution"))
	plan = strings.Replace(plan, `"mode":"execution"`, `"mode":"execution","mode":"planning"`, 1)
	code, _ := e2eTestCall(t, root, "init", "--run-id", "run-1", "--leader-id", "leader", "--input-json", plan)
	if code == 0 {
		t.Fatal("duplicate mode silently weakened execution scope")
	}
	value := e2eTestPlan("execution")
	value["tasks"].([]any)[0].(map[string]any)["depends_on"] = []any{map[string]any{"task_id": "S2", "require": "accepted"}}
	code, _ = e2eTestCall(t, root, "init", "--run-id", "run-1", "--leader-id", "leader", "--input-json", e2eTestJSON(t, value))
	if code == 0 {
		t.Fatal("implicit stage dependency cycle admitted")
	}
}

func TestE2EStatusLabelsCannotReplaceReceipts(t *testing.T) {
	root := e2eTestInit(t, "execution")
	statePath := filepath.Join(root, ".planning/e2e/run-1/state.json")
	raw, err := os.ReadFile(statePath)
	if err != nil {
		t.Fatal(err)
	}
	var state map[string]any
	if err := json.Unmarshal(raw, &state); err != nil {
		t.Fatal(err)
	}
	for _, row := range state["tasks"].([]any) {
		task := row.(map[string]any)
		task["status"], task["outcome"] = "accepted", "pass"
	}
	e2eTestFile(t, root, ".planning/e2e/run-1/state.json", e2eTestJSON(t, state))
	code, result := e2eTestCall(t, root, "close", "--run-id", "run-1", "--leader-id", "leader", "--outcome", "pass", "--expected-revision", "1")
	if code == 0 {
		t.Fatalf("labels without submission/review/acceptance receipts became a complete run: %v", result)
	}
}

func TestE2EUnavailableExecutionReturnsConcreteDiagnosticResume(t *testing.T) {
	root := e2eTestInit(t, "execution")
	for _, id := range []string{"S1", "S2"} {
		e2eTestCompleteTask(t, root, id)
	}
	e2eTestStartAndSubmit(t, root, "S3", "blocked")
	e2eTestReviewAndAccept(t, root, "S3")
	_, result := e2eTestCall(t, root, "status", "--run-id", "run-1")
	argv := result["next_argv"].([]any)
	encoded := e2eTestJSON(t, argv)
	if !strings.Contains(encoded, "task-start") || !strings.Contains(encoded, "--diagnostic") || !strings.Contains(encoded, "S6") {
		t.Fatalf("no actionable audit/report resume: %v", result)
	}
}

func TestE2ERepairRetainsOriginalRawFailureAndReviewBytes(t *testing.T) {
	root := e2eTestInit(t, "execution")
	input := e2eTestPrepareSubmission(t, root, "S1", "failed")
	oldEvidence := []byte("Original failing readback: expected saved value, observed missing value.\n")
	e2eTestFile(t, root, "tests/e2e/evidence-S1.txt", string(oldEvidence))
	input["checks"].([]any)[0].(map[string]any)["status"] = "failed"
	e2eTestMutation(t, root, "task-submit", "--task-id", "S1", "--worker-id", "worker-S1", "--result-json", e2eTestJSON(t, input))
	review := e2eTestPrepareReview(t, root, "S1")
	oldReview := []byte("Original independent rejection: required persistence observation missing.\n")
	e2eTestFile(t, root, "tests/e2e/review-evidence-S1.txt", string(oldReview))
	review["checks"].([]any)[0].(map[string]any)["status"] = "failed"
	code, _ := e2eTestCall(t, root, "review-submit", "--run-id", "run-1", "--task-id", "S1", "--validator-id", "validator-S1", "--expected-revision", e2eTestRevision(t, root), "--result-json", e2eTestJSON(t, review))
	if code == 0 {
		t.Fatal("fixture review did not reject")
	}
	stateRaw, err := os.ReadFile(filepath.Join(root, ".planning/e2e/run-1/state.json"))
	if err != nil {
		t.Fatal(err)
	}
	var state e2eState
	if err := json.Unmarshal(stateRaw, &state); err != nil {
		t.Fatal(err)
	}
	submittedRaw, err := os.ReadFile(filepath.Join(root, state.Tasks[0].Submission.Ref))
	if err != nil {
		t.Fatal(err)
	}
	var submission e2eSubmission
	if err := json.Unmarshal(submittedRaw, &submission); err != nil {
		t.Fatal(err)
	}
	if len(submission.Evidence) != 1 || submission.Evidence[0].ArchiveRef == "" {
		t.Fatal("raw failing observation was not archived")
	}
	oldOutput, err := os.ReadFile(filepath.Join(root, submission.Outputs[0].ArchiveRef))
	if err != nil {
		t.Fatal(err)
	}
	oldReviewRaw, err := os.ReadFile(filepath.Join(root, state.Tasks[0].Review.Ref))
	if err != nil {
		t.Fatal(err)
	}
	var recordedReview e2eReview
	if err := json.Unmarshal(oldReviewRaw, &recordedReview); err != nil {
		t.Fatal(err)
	}
	e2eTestMutation(t, root, "reopen", "--task-id", "S1", "--leader-id", "leader", "--reason", "Repair the omitted persistence observation", "--evidence-ref", "tests/e2e/review-evidence-S1.txt")
	for stage := 1; stage <= 7; stage++ {
		e2eTestCompleteTask(t, root, "S"+strconv.Itoa(stage))
	}
	closed := e2eTestMutation(t, root, "close", "--leader-id", "leader", "--outcome", "pass")
	if closed["product_pass"] != true {
		t.Fatal("fresh complete repair failed to close")
	}
	for _, check := range []struct {
		ref  string
		want []byte
	}{{submission.Evidence[0].ArchiveRef, oldEvidence}, {recordedReview.Evidence[0].ArchiveRef, oldReview}, {submission.Outputs[0].ArchiveRef, oldOutput}} {
		actual, err := os.ReadFile(filepath.Join(root, check.ref))
		if err != nil || !bytes.Equal(actual, check.want) {
			t.Fatalf("old raw failure/report bytes were lost when original paths were reused: %s %v", check.ref, err)
		}
	}
	if err := os.Remove(filepath.Join(root, submission.Evidence[0].ArchiveRef)); err != nil {
		t.Fatal(err)
	}
	code, _ = e2eTestCall(t, root, "close", "--run-id", "run-1", "--leader-id", "leader", "--outcome", "pass", "--expected-revision", strconv.Itoa(int(closed["revision"].(float64))))
	if code == 0 {
		t.Fatal("missing historical raw evidence was silently ignored at close")
	}
}

func TestE2EDeclaredProducerOutputCannotBeConsumedFromStaleLeftovers(t *testing.T) {
	root := t.TempDir()
	e2eTestFile(t, root, "request.md", "Requested save flow")
	e2eTestFile(t, root, "tests/e2e/s1.md", "STALE file from an earlier invocation")
	plan := e2eTestPlan("execution")
	tasks := plan["tasks"].([]any)
	consumer := map[string]any{"id": "S1-consumer", "stage": 1, "scope_ids": []any{"web-save"}, "inputs": []any{"tests/e2e/s1.md"}, "outputs": []any{"tests/e2e/consumer.md"}, "acceptance": []any{map[string]any{"id": "consumed", "criterion": "Consume the accepted producer result"}}}
	plan["tasks"] = append(tasks, consumer)
	code, result := e2eTestCall(t, root, "init", "--run-id", "run-1", "--leader-id", "leader", "--input-json", e2eTestJSON(t, plan))
	if code == 0 || !strings.Contains(e2eTestJSON(t, result), "producer dependency") {
		t.Fatalf("undeclared output/input dependency was admitted: %v", result)
	}
	consumer["depends_on"] = []any{map[string]any{"task_id": "S1", "require": "passed"}}
	e2eTestData(t, root, "init", "--run-id", "run-1", "--leader-id", "leader", "--input-json", e2eTestJSON(t, plan))
	code, _ = e2eTestCall(t, root, "task-start", "--run-id", "run-1", "--task-id", "S1-consumer", "--worker-id", "consumer", "--expected-revision", e2eTestRevision(t, root))
	if code == 0 {
		t.Fatal("pending producer's stale existing file was consumed")
	}
	e2eTestCompleteTask(t, root, "S1")
	started := e2eTestMutation(t, root, "task-start", "--task-id", "S1-consumer", "--worker-id", "consumer")
	inputs := started["packet"].(map[string]any)["inputs"].([]any)
	if inputs[0].(map[string]any)["sha256"] == fileContentSHA256([]byte("STALE file from an earlier invocation")) {
		t.Fatal("consumer bound the stale file instead of the accepted producer's output")
	}
}

func TestE2EAuditWorkerCanRepairOwnRejectedAuditButCannotReviewIt(t *testing.T) {
	root := e2eTestInit(t, "execution")
	for stage := 1; stage <= 5; stage++ {
		e2eTestCompleteTask(t, root, "S"+strconv.Itoa(stage))
	}
	e2eTestStartAndSubmit(t, root, "S6", "pass")
	review := e2eTestPrepareReview(t, root, "S6")
	review["checks"].([]any)[0].(map[string]any)["status"] = "failed"
	code, _ := e2eTestCall(t, root, "review-submit", "--run-id", "run-1", "--task-id", "S6", "--validator-id", "validator-S6", "--expected-revision", e2eTestRevision(t, root), "--result-json", e2eTestJSON(t, review))
	if code == 0 {
		t.Fatal("audit review did not reject")
	}
	e2eTestMutation(t, root, "reopen", "--task-id", "S6", "--leader-id", "leader", "--reason", "Audit report omitted one inspection detail", "--evidence-ref", "tests/e2e/review-evidence-S6.txt")
	e2eTestStartAndSubmit(t, root, "S6", "pass")
	code, _ = e2eTestCall(t, root, "review-start", "--run-id", "run-1", "--task-id", "S6", "--validator-id", "worker-S6", "--expected-revision", e2eTestRevision(t, root))
	if code == 0 {
		t.Fatal("audit author validated its own repaired report")
	}
	e2eTestReviewAndAccept(t, root, "S6")
	e2eTestCompleteTask(t, root, "S7")
	e2eTestMutation(t, root, "close", "--leader-id", "leader", "--outcome", "pass")
}

func TestE2EOuterPassCannotHideFailedOrLostWorkerValidation(t *testing.T) {
	cases := map[string]map[string]any{
		"failed check":                       {"validation_results": []any{map[string]any{"command": "native-runner", "status": "failed", "exit_code": 1}}},
		"nonzero exit with passed label":     {"validation_results": []any{map[string]any{"command": "native-runner", "status": "passed", "exit_code": 1}}},
		"camel exit":                         {"validationResults": []any{map[string]any{"cmd": "native-runner", "result": "passed", "exitCode": 1}}},
		"signal exit":                        {"validation_results": []any{map[string]any{"command": "native-runner", "status": "passed", "returncode": -1}}},
		"invalid hidden row":                 {"validation_results": []any{map[string]any{"command": "native-runner", "status": "passed"}, nil}},
		"missing command would be discarded": {"validation_results": []any{map[string]any{"status": "failed"}}},
		"conflicting lists":                  {"validation_results": []any{}, "validationResults": []any{map[string]any{"command": "native-runner", "status": "failed"}}},
		"conflicting check status":           {"validation_results": []any{map[string]any{"command": "native-runner", "status": "passed", "result": "failed"}}},
		"malformed exit":                     {"validation_results": []any{map[string]any{"command": "native-runner", "status": "passed", "exit_code": "0"}}},
		"top-level failed exit":              {"exit_code": 1},
		"worker status conflict":             {"reported_status": "failed"},
	}
	for name, fields := range cases {
		t.Run(name, func(t *testing.T) {
			root := e2eTestInit(t, "execution")
			input := e2eTestPrepareSubmission(t, root, "S1", "pass")
			worker := input["worker_result"].(map[string]any)
			for key, value := range fields {
				worker[key] = value
			}
			code, result := e2eTestCall(t, root, "task-submit", "--run-id", "run-1", "--task-id", "S1", "--worker-id", "worker-S1", "--expected-revision", e2eTestRevision(t, root), "--result-json", e2eTestJSON(t, input))
			if code == 0 {
				t.Fatalf("failed validation hidden by outer pass: %v", result)
			}
		})
	}
}

func TestE2EEmptyInputTaskHasImmutableContractAndCompleteDispatchIntent(t *testing.T) {
	root := t.TempDir()
	plan := e2eTestPlan("execution")
	for _, task := range plan["tasks"].([]any) {
		task.(map[string]any)["inputs"] = []any{}
	}
	e2eTestData(t, root, "init", "--run-id", "run-1", "--leader-id", "leader", "--input-json", e2eTestJSON(t, plan))
	input := e2eTestPrepareSubmission(t, root, "S1", "pass")
	packetRaw, err := os.ReadFile(filepath.Join(root, ".planning/e2e/run-1/snapshots/"+input["packet_sha256"].(string)+".json"))
	if err != nil {
		t.Fatal(err)
	}
	var packet map[string]any
	if err := json.Unmarshal(packetRaw, &packet); err != nil {
		t.Fatal(err)
	}
	checkIntent := func(view map[string]any) {
		t.Helper()
		intent, ok := view["intent"].(map[string]any)
		if !ok || intent["outcome"] != view["objective"] || !e2eSameJSON(intent["constraints"], view["hard_rules"]) || !e2eSameJSON(intent["success_signals"], view["done_criteria"]) {
			t.Fatalf("standard worker intent omitted its actual objective/rules/acceptance: %v", view)
		}
	}
	view := packet["worker_task_packet"].(map[string]any)
	checkIntent(view)
	contractRef, ok := packet["contract_ref"].(map[string]any)
	if !ok {
		t.Fatal("zero-input worker has no independently persisted contract reference")
	}
	contractPath, digest := contractRef["ref"].(string), contractRef["sha256"].(string)
	contractRaw, err := os.ReadFile(filepath.Join(root, contractPath))
	if err != nil || fileContentSHA256(contractRaw) != digest || contractPath != ".planning/e2e/run-1/snapshots/"+digest+".json" {
		t.Fatalf("contract reference does not resolve to immutable original bytes: %v", err)
	}
	var contract map[string]any
	if err := json.Unmarshal(contractRaw, &contract); err != nil {
		t.Fatal(err)
	}
	if !e2eSameJSON(contract["contract"], packet["contract"]) || !e2eSameJSON(contract["scope"], packet["scope"]) || contract["run_id"] != "run-1" || contract["contract_sha256"] != packet["contract_sha256"] {
		t.Fatalf("task contract reference does not preserve the exact task and original scope: %v", contract)
	}
	reads := view["scope"].(map[string]any)["read_scope"].([]any)
	if len(reads) != 1 || reads[0] != contractPath || len(view["context_bundle"].([]any)) != 1 || view["required_references"].([]any)[0].(map[string]any)["path"] != contractPath {
		t.Fatalf("zero-input dispatch lacks a concrete contract context: %v", view)
	}
	e2eTestMutation(t, root, "task-submit", "--task-id", "S1", "--worker-id", "worker-S1", "--result-json", e2eTestJSON(t, input))
	review := e2eTestPrepareReview(t, root, "S1")
	requestRaw, err := os.ReadFile(filepath.Join(root, ".planning/e2e/run-1/snapshots/"+review["review_packet_sha256"].(string)+".json"))
	if err != nil {
		t.Fatal(err)
	}
	var request map[string]any
	if err := json.Unmarshal(requestRaw, &request); err != nil {
		t.Fatal(err)
	}
	checkIntent(request["worker_task_packet"].(map[string]any))
	reviewView := request["worker_task_packet"].(map[string]any)
	if len(reviewView["scope"].(map[string]any)["write_scope"].([]any)) != 0 || len(reviewView["interfaces"].(map[string]any)["produces"].([]any)) != 0 {
		t.Fatal("independent review acquired write permissions")
	}
	e2eTestMutation(t, root, "review-submit", "--task-id", "S1", "--validator-id", "validator-S1", "--result-json", e2eTestJSON(t, review))
	e2eTestMutation(t, root, "task-accept", "--task-id", "S1", "--leader-id", "leader")
	for stage := 2; stage <= 7; stage++ {
		e2eTestCompleteTask(t, root, "S"+strconv.Itoa(stage))
	}
	closed := e2eTestMutation(t, root, "close", "--leader-id", "leader", "--outcome", "pass")
	if closed["product_pass"] != true {
		t.Fatal("zero-input plan failed complete closure")
	}
	after, err := os.ReadFile(filepath.Join(root, contractPath))
	if err != nil || !bytes.Equal(contractRaw, after) {
		t.Fatalf("state revisions changed the immutable task contract: %v", err)
	}
	if err := os.Remove(filepath.Join(root, contractPath)); err != nil {
		t.Fatal(err)
	}
	if code, _ := e2eTestCall(t, root, "status", "--run-id", "run-1"); code == 0 {
		t.Fatal("missing original task contract left acceptance valid")
	}
}

func TestE2EWorkerMetadataArchiveKeysRemainOpaqueThroughRepairAndClose(t *testing.T) {
	metadata := map[string]any{"archive_ref": "tests/e2e/external-native-archive.txt", "sha256": strings.Repeat("0", 64), "summary": "native runner metadata"}
	for name, observations := range map[string]any{"raw-object": metadata, "normalized-object-list": []any{metadata}} {
		t.Run(name, func(t *testing.T) {
			root := e2eTestInit(t, "execution")
			input := e2eTestPrepareSubmission(t, root, "S1", "pass")
			input["worker_result"].(map[string]any)["observations"] = observations
			submitted := e2eTestMutation(t, root, "task-submit", "--task-id", "S1", "--worker-id", "worker-S1", "--result-json", e2eTestJSON(t, input))
			raw, err := os.ReadFile(filepath.Join(root, submitted["submission_ref"].(string)))
			if err != nil {
				t.Fatal(err)
			}
			var snapshot map[string]any
			if err := json.Unmarshal(raw, &snapshot); err != nil {
				t.Fatal(err)
			}
			if !e2eSameJSON(snapshot["worker_result_input"].(map[string]any)["observations"], observations) {
				t.Fatal("raw worker metadata was rewritten")
			}
			if name == "normalized-object-list" && !e2eSameJSON(snapshot["worker_result"].(map[string]any)["observations"], observations) {
				t.Fatal("normalized worker metadata was rewritten")
			}
			e2eTestData(t, root, "status", "--run-id", "run-1")
			review := e2eTestPrepareReview(t, root, "S1")
			review["checks"].([]any)[0].(map[string]any)["status"] = "failed"
			code, result := e2eTestCall(t, root, "review-submit", "--run-id", "run-1", "--task-id", "S1", "--validator-id", "validator-S1", "--expected-revision", e2eTestRevision(t, root), "--result-json", e2eTestJSON(t, review))
			if code == 0 || !strings.Contains(e2eTestJSON(t, result), "rejected") {
				t.Fatalf("independent rejection was not recorded: %v", result)
			}
			e2eTestMutation(t, root, "reopen", "--task-id", "S1", "--leader-id", "leader", "--reason", "Repair the independently rejected result", "--evidence-ref", "tests/e2e/review-evidence-S1.txt")
			for stage := 1; stage <= 7; stage++ {
				e2eTestCompleteTask(t, root, "S"+strconv.Itoa(stage))
			}
			closed := e2eTestMutation(t, root, "close", "--leader-id", "leader", "--outcome", "pass")
			if closed["product_pass"] != true {
				t.Fatal("raw metadata keys poisoned a repaired run's history")
			}
			e2eTestData(t, root, "status", "--run-id", "run-1")
		})
	}
}
