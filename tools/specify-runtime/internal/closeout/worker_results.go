package closeout

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strings"

	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/workerdelta"
)

// CollectWorkerResults exposes the existing canonical result owner to the
// source-binding gate; callers cannot supply an alternative accepted-result list.
func CollectWorkerResults(root, workflow, scope string) (*workerdelta.Merge, error) {
	return collectWorkerResults(root, workflow, scope)
}

// collectWorkerResults reads only the registered workflow's canonical owners.
// It never accepts an agent-provided result list or reads cognition storage.
func collectWorkerResults(root, workflow, scope string) (*workerdelta.Merge, error) {
	if scope == "" {
		return nil, nil
	}
	if filepath.IsAbs(scope) {
		relative, err := filepath.Rel(root, scope)
		if err != nil {
			return nil, err
		}
		scope = filepath.ToSlash(relative)
	}
	// The scope is a directory; unlike result references, the project root is
	// valid for repository-scoped workflows such as Fast and Debug.
	if scope != "." {
		var err error
		scope, err = workerdelta.SafePath(scope)
		if err != nil {
			return nil, err
		}
	}
	reader := &workerResultReader{root: root, reads: map[string]string{}}
	var quickDirectory string
	var quickInventory []string
	events := []workerdelta.Event{}
	switch workflow {
	case "sp-implement":
		index, err := reader.optional(scope + "/task-index.json")
		if err != nil {
			return nil, err
		}
		if index == nil {
			return nil, nil
		}
		rows, valid := index["tasks"].([]any)
		if !valid {
			return nil, fmt.Errorf("stored Implement task index has no task array")
		}
		seen := map[string]bool{}
		for _, raw := range rows {
			task, _ := raw.(map[string]any)
			id, _ := task["task_id"].(string)
			if id == "" {
				id, _ = task["id"].(string)
			}
			if id == "" || seen[id] {
				return nil, fmt.Errorf("stored Implement task identity is missing or duplicated")
			}
			seen[id] = true
			if strings.ContainsAny(id, "/\\") {
				return nil, fmt.Errorf("invalid task result identity")
			}
			ref := scope + "/worker-results/" + id + ".json"
			stored, err := reader.optional(ref)
			if err != nil {
				return nil, err
			}
			lifecycleRef := scope + "/implementation-review/tasks/" + id + ".json"
			lifecycle, err := reader.optional(lifecycleRef)
			if err != nil {
				return nil, err
			}
			accepted := false
			if binding, ok := stored["cognition_result_binding"].(map[string]any); ok {
				revision, _ := workerdelta.Sequence(lifecycle["revision"])
				submissionRevision, _ := workerdelta.Sequence(binding["lifecycle_revision"])
				accepted = lifecycle["status"] == "accepted" && task["status"] == "accepted" && binding["acceptance_state"] == "accepted" && binding["acceptance_ref"] == lifecycleRef && fmt.Sprint(binding["acceptance_revision"]) == fmt.Sprint(revision) && submissionRevision == revision-1 && binding["result_ref"] == ref && stored["task_id"] == id && workerdelta.Same(stored["validation_results"], lifecycle["validation"]) && workerdelta.Same(stored["blockers"], lifecycle["blockers"]) && lifecycle["result_ref"] == "worker-results/"+id+".json"
			}
			if stored != nil {
				next, err := reader.history(ref, stored, id, accepted)
				if err != nil {
					return nil, err
				}
				events = append(events, next...)
			}
			history, _ := lifecycle["reopen_history"].([]any)
			for _, raw := range history {
				record, _ := raw.(map[string]any)
				historyRef, _ := record["history_ref"].(string)
				digest, _ := record["history_sha256"].(string)
				if historyRef == "" {
					continue
				}
				archived, err := reader.readBound(scope+"/"+historyRef, digest)
				if err != nil {
					return nil, err
				}
				previous, _ := archived["previous"].(map[string]any)
				if previous == nil {
					previous, _ = archived["previous_state"].(map[string]any)
				}
				worker, _ := previous["worker_result"].(map[string]any)
				if worker != nil {
					next, err := reader.history(scope+"/"+historyRef, worker, id, false)
					if err != nil {
						return nil, err
					}
					events = append(events, next...)
				}
			}
		}
	case "sp-quick":
		if !strings.HasPrefix(scope, ".planning/quick/") {
			return nil, fmt.Errorf("Quick result scope must be a canonical Quick workspace")
		}
		doc, err := reader.optional(scope + "/confirmation.json")
		if err != nil {
			return nil, err
		}
		if doc == nil {
			return nil, nil
		}
		execution, _ := doc["execution"].(map[string]any)
		rows, valid := execution["work_item_status"].([]any)
		if !valid {
			return nil, fmt.Errorf("stored Quick confirmation has no work-item status array")
		}
		accepted := map[string]map[string]any{}
		for _, raw := range rows {
			row, _ := raw.(map[string]any)
			if row["status"] == "accepted" {
				ref, _ := row["worker_result_ref"].(string)
				accepted[ref] = row
			}
		}
		quickDirectory = filepath.Join(root, filepath.FromSlash(scope+"/worker-results"))
		entries, err := os.ReadDir(quickDirectory)
		if os.IsNotExist(err) {
			break
		}
		if err != nil {
			return nil, err
		}
		for _, entry := range entries {
			if entry.IsDir() || !strings.HasSuffix(entry.Name(), ".json") {
				continue
			}
			quickInventory = append(quickInventory, entry.Name())
			ref := scope + "/worker-results/" + entry.Name()
			stored, err := reader.read(ref)
			if err != nil {
				return nil, err
			}
			binding, _ := stored["cognition_result_binding"].(map[string]any)
			row := accepted[ref]
			current := row != nil && binding["acceptance_state"] == "accepted" && binding["acceptance_ref"] == scope+"/confirmation.json" && binding["result_sha256"] == row["worker_result_sha256"] && binding["attempt_id"] == row["worker_attempt_id"] && fmt.Sprint(binding["sequence"]) == fmt.Sprint(row["worker_submission_sequence"])
			id, _ := stored["task_id"].(string)
			next, err := reader.history(ref, stored, id, current)
			if err != nil {
				return nil, err
			}
			events = append(events, next...)
		}
	case "sp-e2e":
		if !strings.HasPrefix(scope, ".planning/e2e/") {
			return nil, fmt.Errorf("E2E result scope must be a canonical E2E run")
		}
		state, err := reader.optional(scope + "/state.json")
		if err != nil {
			return nil, err
		}
		if state == nil {
			return nil, nil
		}
		tasks, valid := state["tasks"].([]any)
		if !valid {
			return nil, fmt.Errorf("stored E2E state has no task array")
		}
		seen := map[string]bool{}
		for _, raw := range tasks {
			task, _ := raw.(map[string]any)
			contract, _ := task["contract"].(map[string]any)
			id, _ := contract["id"].(string)
			if id == "" || seen[id] {
				return nil, fmt.Errorf("stored E2E task identity is missing or duplicated")
			}
			seen[id] = true
			current, _ := task["submission"].(map[string]any)
			refs := []any{}
			if current["ref"] != "" {
				refs = append(refs, current)
			}
			history, _ := task["history"].([]any)
			refs = append(refs, history...)
			for historyIndex, rawRef := range refs {
				reference, _ := rawRef.(map[string]any)
				ref, _ := reference["ref"].(string)
				digest, _ := reference["sha256"].(string)
				if ref == "" {
					continue
				}
				if ref != scope+"/snapshots/"+digest+".json" {
					return nil, fmt.Errorf("invalid E2E snapshot result reference")
				}
				snapshot, err := reader.readBound(ref, digest)
				if err != nil {
					return nil, err
				}
				schema := snapshot["schema_version"]
				if schema == "e2e-rejected-worker-result-v1" {
					text, _ := snapshot["worker_result_json"].(string)
					if snapshot["worker_result_sha256"] != workerdelta.Digest([]byte(text)) {
						return nil, fmt.Errorf("rejected E2E input digest changed")
					}
					if raw, present := snapshot["submission_input_json"]; present {
						exact, ok := raw.(string)
						if !ok || snapshot["submission_input_sha256"] != workerdelta.Digest([]byte(exact)) {
							return nil, fmt.Errorf("rejected E2E exact submission input digest changed")
						}
					}
					input, decodeErr := workerdelta.Decode([]byte(text))
					event := reader.event(ref, id, "rejected", text, false, fmt.Sprint(snapshot["attempt"]), fmt.Sprint(snapshot["rejection_reason"]), input, decodeErr)
					event.Sequence = historyIndex + 1
					events = append(events, event)
					continue
				}
				if schema != "e2e-worker-result-v1" {
					continue
				}
				result, _ := snapshot["worker_result"].(map[string]any)
				textBytes, _ := json.Marshal(result)
				binding, _ := snapshot["cognition_result_binding"].(map[string]any)
				accepted := false
				if historyIndex == 0 && ref == current["ref"] && task["status"] == "accepted" && task["outcome"] == "pass" && result["status"] == "success" && binding["result_sha256"] == workerdelta.Digest(textBytes) {
					acceptRef, _ := task["acceptance"].(map[string]any)
					acceptPath, _ := acceptRef["ref"].(string)
					acceptDigest, _ := acceptRef["sha256"].(string)
					if acceptPath != "" {
						acceptance, err := reader.readBound(acceptPath, acceptDigest)
						if err != nil {
							return nil, err
						}
						accepted, err = reader.e2eAccepted(scope, state, task, snapshot, acceptance, id, current, binding)
						if err != nil {
							return nil, err
						}
					}
				}
				event := reader.event(ref, id, fmt.Sprint(result["status"]), string(textBytes), accepted, fmt.Sprint(binding["attempt_id"]), "", result, nil)
				event.Sequence = historyIndex + 1
				events = append(events, event)
			}
		}
	default:
		return nil, nil
	}
	for ref, digest := range reader.reads {
		raw, err := reader.bytes(ref)
		if err != nil {
			return nil, err
		}
		if workerdelta.Digest(raw) != digest {
			return nil, fmt.Errorf("worker result owner changed during closeout planning: %s", ref)
		}
	}
	if quickDirectory != "" && quickInventory != nil {
		entries, err := os.ReadDir(quickDirectory)
		if err != nil {
			return nil, err
		}
		names := []string{}
		for _, entry := range entries {
			if !entry.IsDir() && strings.HasSuffix(entry.Name(), ".json") {
				names = append(names, entry.Name())
			}
		}
		if !workerdelta.Same(names, quickInventory) {
			return nil, fmt.Errorf("Quick worker-result directory changed during closeout planning")
		}
	}
	merged := workerdelta.MergeEvents(events)
	return &merged, nil
}

func (r *workerResultReader) e2eAccepted(scope string, state, task, submission, acceptance map[string]any, id string, current, binding map[string]any) (bool, error) {
	if binding["schema"] != workerdelta.BindingSchema || !workerdelta.VersionOne(binding["version"]) || acceptance["schema_version"] != "e2e-acceptance-v1" || acceptance["run_id"] != state["run_id"] || acceptance["leader_id"] != state["leader_id"] || acceptance["task_id"] != id || acceptance["outcome"] != "pass" || !workerdelta.Same(acceptance["submission"], current) || !workerdelta.Same(submission["packet"], task["packet"]) || submission["worker_id"] != task["worker_id"] || submission["outcome"] != "pass" {
		return false, nil
	}
	bound := map[string]map[string]any{}
	for _, field := range []string{"packet", "review_packet", "review"} {
		ref, _ := task[field].(map[string]any)
		name, _ := ref["ref"].(string)
		digest, _ := ref["sha256"].(string)
		if name != scope+"/snapshots/"+digest+".json" || !workerdelta.Same(acceptance[field], ref) {
			return false, nil
		}
		payload, err := r.readBound(name, digest)
		if err != nil {
			return false, err
		}
		bound[field] = payload
	}
	packet, reviewPacket, review := bound["packet"], bound["review_packet"], bound["review"]
	if packet["schema_version"] != "e2e-worker-packet-v1" || packet["run_id"] != state["run_id"] || packet["task_id"] != id || packet["worker_id"] != task["worker_id"] || packet["attempt_id"] != binding["attempt_id"] || binding["task_ref"] != "e2e:"+fmt.Sprint(state["run_id"])+"#"+id || !workerdelta.Same(packet["contract"], task["contract"]) || reviewPacket["schema_version"] != "e2e-review-packet-v1" || reviewPacket["task_id"] != id || !workerdelta.Same(reviewPacket["packet"], task["packet"]) || !workerdelta.Same(reviewPacket["submission"], current) || review["schema_version"] != "e2e-independent-review-v1" || !workerdelta.Same(review["request"], task["review_packet"]) || !workerdelta.Same(review["submission"], current) || review["validator_id"] != task["validator_id"] {
		return false, nil
	}
	attempt, err := workerdelta.Sequence(task["attempt"])
	if err != nil || packet["attempt_id"] != fmt.Sprintf("%s-%04d", id, attempt) {
		return false, nil
	}
	for _, owner := range []map[string]any{submission, review} {
		for _, field := range []string{"outputs", "evidence"} {
			rows, _ := owner[field].([]any)
			for _, raw := range rows {
				fact, _ := raw.(map[string]any)
				path, _ := fact["path"].(string)
				digest, _ := fact["sha256"].(string)
				if path == "" || digest == "" {
					return false, nil
				}
				current, err := r.bytes(path)
				if os.IsNotExist(err) {
					return false, nil
				}
				if err != nil {
					return false, err
				}
				actual := workerdelta.Digest(current)
				r.reads[path] = actual
				if actual != digest {
					return false, nil
				}
			}
		}
	}
	return true, nil
}

type workerResultReader struct {
	root  string
	reads map[string]string
}

func (r *workerResultReader) bytes(ref string) ([]byte, error) {
	ref, err := workerdelta.SafePath(ref)
	if err != nil {
		return nil, err
	}
	target := filepath.Join(r.root, filepath.FromSlash(ref))
	resolved, err := filepath.EvalSymlinks(target)
	if err != nil {
		return nil, err
	}
	root, err := filepath.EvalSymlinks(r.root)
	if err != nil {
		return nil, err
	}
	relative, err := filepath.Rel(root, resolved)
	if err != nil || relative == ".." || strings.HasPrefix(relative, ".."+string(filepath.Separator)) {
		return nil, fmt.Errorf("worker result path escapes the project")
	}
	info, err := os.Stat(resolved)
	if err != nil {
		return nil, err
	}
	if !info.Mode().IsRegular() || info.Size() > 8*1024*1024 {
		return nil, fmt.Errorf("worker result must be a bounded regular file")
	}
	return os.ReadFile(resolved)
}
func (r *workerResultReader) read(ref string) (map[string]any, error) {
	raw, err := r.bytes(ref)
	if err != nil {
		return nil, err
	}
	r.reads[ref] = workerdelta.Digest(raw)
	return workerdelta.Decode(raw)
}
func (r *workerResultReader) optional(ref string) (map[string]any, error) {
	value, err := r.read(ref)
	if os.IsNotExist(err) {
		return nil, nil
	}
	return value, err
}
func (r *workerResultReader) readBound(ref, digest string) (map[string]any, error) {
	value, err := r.read(ref)
	if err != nil {
		return nil, err
	}
	if r.reads[ref] != digest {
		return nil, fmt.Errorf("worker result history digest changed: %s", ref)
	}
	return value, nil
}
func (r *workerResultReader) history(ref string, stored map[string]any, id string, accepted bool) ([]workerdelta.Event, error) {
	if err := workerdelta.ValidateStored(stored); err != nil {
		return nil, err
	}
	rows, _ := stored["submission_history"].([]any)
	binding, _ := stored["cognition_result_binding"].(map[string]any)
	sequence, _ := workerdelta.Sequence(binding["sequence"])
	events := []workerdelta.Event{}
	if len(rows) == 0 {
		raw, _ := json.Marshal(stored)
		events = append(events, r.event(ref, id, "legacy", string(raw), false, "legacy", "", stored, nil))
		return events, nil
	}
	for index, raw := range rows {
		row, _ := raw.(map[string]any)
		text, _ := row["result_json"].(string)
		input, decodeErr := workerdelta.Decode([]byte(text))
		current := accepted && sequence == index+1 && row["status"] == "success"
		event := r.event(ref, id, fmt.Sprint(row["status"]), text, current, fmt.Sprint(row["attempt_id"]), fmt.Sprint(row["rejection_reason"]), input, decodeErr)
		event.Sequence = index + 1
		events = append(events, event)
	}
	return events, nil
}
func (r *workerResultReader) event(ref, id, status, text string, accepted bool, attempt, reason string, input map[string]any, decodeErr error) workerdelta.Event {
	delta := map[string]any{}
	var candidateInput map[string]any
	if input != nil {
		normalized, _, err := workerdelta.Normalize(input)
		if err == nil {
			delta = normalized
		} else {
			accepted = false
			candidateInput = workerdelta.Clone(input)
			if reason == "" {
				reason = err.Error()
			}
		}
	}
	return workerdelta.Event{SourceRef: ref, SourceSHA256: r.reads[ref], TaskID: id, AttemptID: attempt, ResultSHA256: workerdelta.Digest([]byte(text)), Status: status, Accepted: accepted, Delta: delta, CandidateInput: candidateInput, RetainedPaths: workerdelta.Accounting(input), RejectionReason: reason, Unaccounted: decodeErr != nil}
}
