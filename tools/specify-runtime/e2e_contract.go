package main

import (
	"path"
	"runtime"
	"strings"
)

const e2eWorkflowSchema = "spec-kit-e2e-workflow-v1"

var e2eActions = []string{"init", "status", "task-show", "scope-add", "task-start", "task-submit", "review-start", "review-submit", "task-accept", "reopen", "close"}

func e2eReadOnlyAction(action string) bool {
	return action == "status" || action == "task-show"
}

func e2eRequiresActiveRun(action string) bool {
	switch action {
	case "task-start", "task-submit", "review-start", "review-submit", "task-accept":
		return true
	}
	return false
}

func e2eCapabilityIDs() []string {
	ids := make([]string, 0, len(e2eActions)+1)
	for _, action := range e2eActions {
		ids = append(ids, "e2e."+action)
	}
	return append(ids, "e2e.compact")
}

// The registry supplies canonical project-relative paths. E2E state and all
// immutable handoff snapshots have one mutation owner, including future files.
func e2eRuntimeOwnedPath(value string) bool {
	value = path.Clean(strings.ReplaceAll(strings.TrimSpace(value), "\\", "/"))
	value = e2eFilePathKey(value)
	return value == ".planning/e2e" || strings.HasPrefix(value, ".planning/e2e/")
}

// Windows and default macOS volumes identify case-only spellings as the same
// file. Compare conservatively on Darwin, including its optional case-sensitive
// volumes; retain case-distinct paths elsewhere and original binding spellings.
func e2eFilePathKey(value string) string {
	if runtime.GOOS == "windows" || runtime.GOOS == "darwin" {
		return strings.ToLower(value)
	}
	return value
}

func e2eCapabilityDescriptor(id string) (map[string]any, bool) {
	if id == "e2e.compact" {
		return map[string]any{
			"id": id, "summary": "Explicit paginated E2E state views and exact task resume reads",
			"usage":          "specify-runtime e2e <action> --run-id <id> --view compact [--offset <n>] [--limit <1..200>] --format json",
			"side_effect":    "view-only-feature",
			"input_contract": "An output feature, not an executable action. The default full view remains compatible. Compact state responses retain full-scope counts, global status counts, per-stage status counts and a task page (default 25, maximum 200), exact revision, next_page_argv and full_show_argv. The shared task_show_argv template replaces only <task-id> with a current row's id; stable project/runtime paths are not duplicated per row. Read every page at the same revision; restart pagination if it changes. Counts and missing work are never inferred from only the current page. Underlying actions retain their own mutation and acceptance gates; compact does not authorize writes.",
		}, true
	}
	action := strings.TrimPrefix(id, "e2e.")
	if id == action || !e2eContains(e2eActions, action) {
		return nil, false
	}
	usage := "specify-runtime e2e " + action + " --run-id <id> [--project-root <path>] --format json"
	if action != "init" && !e2eReadOnlyAction(action) {
		usage += " --expected-revision <revision>"
	}
	usage += " [--view full|compact] [--offset <n>] [--limit <1..200>]"
	inputSchema := ""
	sideEffect := "writes-e2e-workflow"
	contract := "Runtime-owned, revision-checked E2E handoffs; native agent tools create workers. Recorded distinct identities are checked, not authenticated as separate agent processes."
	contract += " State responses expose fresh_revision, readiness_counts, ready_actions and waiting. Compact lists only the current task page; task-show expands an exact task's reasons/argv and bounded conflicts with next_conflict_page_argv/next_waiting_page_argv. Full status includes all ready actions, reasons and candidate_conflicts. Individually ready candidates may conflict with each other; candidate_conflict_pair_count is global and never authorizes a batch. Every mutation still requires fresh revision and live owner checks. Typed diagnostics retain root_task_id, kind, path, expected_sha256, observed_sha256, reason and transitive affected_task_ids; compact exposes counts/pages and full expansion. Empty observed_sha256 means unavailable bytes, not a matching digest. Mutable drift is invalidated with a durable causal event; corrupt immutable history blocks without resetting it."
	if e2eRequiresActiveRun(action) {
		contract += " Require an active run; after closeout, the leader must reopen the affected task with a recovery reason and evidence before ordinary task progression."
	}
	switch action {
	case "init":
		usage += " --leader-id <id> --input-json <object|@path|->"
		inputSchema = "e2e-plan-input"
		contract += " Freeze every requested target/operation and all seven stage task placeholders; future output files need not exist. Scope, task IDs and acceptance criteria cannot be silently removed."
	case "status":
		sideEffect = "read-only"
		contract += " Revalidate snapshot, source, output and evidence byte bindings; return the full denominator, unresolved tasks and stale descendants. Status does not mutate stale state. Fresh blocked/reported closeouts return an evidence-backed reopen action for the earliest unresolved or nonpassing stage; passing closeouts have no ordinary next action."
	case "task-show":
		sideEffect = "read-only"
		usage += " --task-id <id>"
		contract += " Read one current task without acquiring a mutation lock or writing files. Revalidate the run's immutable history and current bindings before returning the exact current worker/review packet and a same-attempt submission/review template. A stale or corrupt run returns no usable template. Closed runs do not expose ordinary submission/review resume actions. Template placeholders are not passing observations."
	case "scope-add":
		usage += " --leader-id <id> --reason <text> --evidence-ref <path> --input-json <object|@path|->"
		inputSchema = "e2e-scope-add-input"
		contract += " Add scope/tasks only, retain old contracts, and invalidate affected producers and consumers. Every new scope requires all seven stage placeholders."
	case "task-start":
		usage += " --task-id <id> --worker-id <id> [--diagnostic]"
		contract += " Compile an E2E envelope containing the standard worker_task_packet view with complete intent, a separately persisted immutable task contract for concrete context even when inputs are empty, exact accepted dependency outputs/receipts, and fresh input digests with archived original bytes. Reject unaccepted prerequisites or overlapping active read/write paths/resources. Plans must declare every output-to-input producer dependency. Diagnostic mode is restricted to stages 6/7 and cannot establish a passing outcome."
	case "task-submit":
		usage += " --task-id <id> --worker-id <id> --result-json <object|@path|->"
		inputSchema = "e2e-task-result"
		contract += " Embed normalized WorkerTaskResult and its pre-normalization input in an immutable runtime snapshot. Account for every assigned scope/acceptance pair with expected/actual outcomes and archived original evidence/output bytes. A passing outcome rejects any failed/skipped/malformed reported validation, conflicting aliases, or nonzero runner exit code. Submission is not acceptance."
	case "review-start":
		usage += " --task-id <id> --validator-id <id>"
		contract += " Bind an independently recorded reviewer to the exact submission, original task and complete acceptance rows; return a review packet and semantic result template."
	case "review-submit":
		usage += " --task-id <id> --validator-id <id> --result-json <object|@path|->"
		inputSchema = "e2e-review-result"
		contract += " Check every review row and current source/output/evidence digests. Preserve rejection evidence and require a fresh worker attempt before another review."
	case "task-accept":
		usage += " --task-id <id> --leader-id <id>"
		contract += " Accept only a current, completely verified submission. An accepted failure report remains a failed observation and cannot unlock a passed prerequisite."
	case "reopen":
		usage += " --task-id <id> --leader-id <id> --reason <text> --evidence-ref <path>"
		contract += " Preserve immutable history, reopen the earliest affected producer and transitively invalidate its consumers; no old review may be reused. Archive any terminal closeout receipt and restore an active run at a fresh revision before resuming task progression."
	case "close":
		usage += " --leader-id <id> --outcome <pass|failed|blocked>"
		contract += " Recheck the complete reachable evidence chain, original raw artifact archives including failure history, and every requested scope/stage. Planning completion never claims product execution. Failure reports are reported, not a passing completed run; unresolved mandatory work remains blocked. Closed runs reject ordinary task/review/accept actions until evidence-backed leader reopen; existing source-drift invalidation and additive scope recovery remain available."
	}
	out := map[string]any{"id": id, "summary": "Verified E2E dependency handoff: " + action, "usage": usage, "side_effect": sideEffect, "input_contract": contract}
	if inputSchema != "" {
		out["input_schema"] = inputSchema
	}
	return out, true
}

func e2ePayloadSchema(id string) (map[string]any, string, bool) {
	text := map[string]any{"type": "string", "minLength": 1}
	texts := func(minimum int) map[string]any {
		return map[string]any{"type": "array", "minItems": minimum, "uniqueItems": true, "items": text}
	}
	object := func(required []string, properties map[string]any) map[string]any {
		return map[string]any{"type": "object", "additionalProperties": false, "required": required, "properties": properties}
	}
	scope := object([]string{"id", "target", "operation"}, map[string]any{"id": text, "target": text, "operation": text})
	acceptance := object([]string{"id", "criterion"}, map[string]any{"id": text, "criterion": text})
	dependency := object([]string{"task_id", "require"}, map[string]any{"task_id": text, "require": map[string]any{"enum": []string{"accepted", "passed"}}})
	task := object([]string{"id", "stage", "scope_ids", "acceptance", "inputs", "outputs"}, map[string]any{
		"id": text, "stage": map[string]any{"type": "integer", "minimum": 1, "maximum": 7}, "scope_ids": texts(1),
		"depends_on": map[string]any{"type": "array", "items": dependency}, "acceptance": map[string]any{"type": "array", "minItems": 1, "items": acceptance},
		"inputs": texts(0), "outputs": texts(1), "resources": texts(0),
	})
	var schema map[string]any
	capability := ""
	switch id {
	case "e2e-plan-input", "e2e-scope-add-input":
		properties := map[string]any{"scope": map[string]any{"type": "array", "items": scope}, "tasks": map[string]any{"type": "array", "minItems": 1, "items": task}}
		required := []string{"scope", "tasks"}
		capability = "e2e.scope-add"
		if id == "e2e-plan-input" {
			properties["mode"] = map[string]any{"enum": []string{"execution", "planning"}}
			required = append(required, "mode")
			capability = "e2e.init"
		}
		schema = object(required, properties)
		if id == "e2e-plan-input" {
			tasks := []any{}
			for stage := 1; stage <= 7; stage++ {
				tasks = append(tasks, map[string]any{"id": "S" + string(rune('0'+stage)), "stage": stage, "scope_ids": []string{"target-operation"}, "acceptance": []any{map[string]any{"id": "complete", "criterion": "Replace with this stage's complete, source-backed acceptance requirement"}}, "inputs": []string{"request.md"}, "outputs": []string{"tests/e2e/stage-" + string(rune('0'+stage)) + ".md"}, "resources": []string{}})
			}
			schema["examples"] = []any{map[string]any{"mode": "execution", "scope": []any{map[string]any{"id": "target-operation", "target": "web", "operation": "Replace with a requested product operation"}}, "tasks": tasks}}
		}
	case "e2e-task-result", "e2e-review-result":
		properties := map[string]any{"scope_id": text, "acceptance_id": text, "status": map[string]any{"enum": []string{"passed", "failed", "blocked", "skipped", "not_run"}}, "expected": text, "actual": text, "reproduction": text, "preconditions": text, "evidence_refs": texts(1)}
		required := []string{"scope_id", "acceptance_id", "status", "expected", "actual", "reproduction", "preconditions", "evidence_refs"}
		if id == "e2e-review-result" {
			properties["method"] = map[string]any{"enum": []string{"inspected", "replayed"}}
			required = append(required, "method")
			properties["status"] = map[string]any{"enum": []string{"passed", "failed"}}
		}
		checks := map[string]any{"type": "array", "minItems": 1, "items": object(required, properties)}
		if id == "e2e-task-result" {
			schema = object([]string{"packet_sha256", "outcome", "worker_result", "checks"}, map[string]any{"packet_sha256": text, "outcome": map[string]any{"enum": []string{"pass", "failed", "blocked"}}, "worker_result": map[string]any{"type": "object", "description": "Existing normalized WorkerTaskResult; task_id and packet_id must match this exact packet; status cannot be pending."}, "checks": checks})
			capability = "e2e.task-submit"
		} else {
			schema = object([]string{"review_packet_sha256", "submission_sha256", "checks"}, map[string]any{"review_packet_sha256": text, "submission_sha256": text, "checks": checks})
			capability = "e2e.review-submit"
		}
	default:
		return nil, "", false
	}
	schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
	schema["$id"] = "specify://schemas/" + id + "/v1"
	return schema, capability, true
}
