package main

import (
	"fmt"
	"strconv"
)

const e2eDefaultPageLimit = 25
const e2eMaxPageLimit = 200

type e2eViewOptions struct {
	Mode   string
	Offset int
	Limit  int
}

func e2eParseViewOptions(args []string) (e2eViewOptions, error) {
	view := e2eViewOptions{Mode: optionValue(args, "--view", "full"), Limit: e2eDefaultPageLimit}
	if view.Mode != "full" && view.Mode != "compact" {
		return view, fmt.Errorf("--view must be full or compact")
	}
	if view.Mode != "compact" && (hasFlag(args, "--offset") || hasFlag(args, "--limit")) {
		return view, fmt.Errorf("--offset and --limit require --view compact")
	}
	var err error
	view.Offset, err = strconv.Atoi(optionValue(args, "--offset", "0"))
	if err != nil || view.Offset < 0 {
		return view, fmt.Errorf("--offset must be a nonnegative integer")
	}
	view.Limit, err = strconv.Atoi(optionValue(args, "--limit", strconv.Itoa(e2eDefaultPageLimit)))
	if err != nil || view.Limit < 1 || view.Limit > e2eMaxPageLimit {
		return view, fmt.Errorf("--limit must be between 1 and %d", e2eMaxPageLimit)
	}
	return view, nil
}

type e2eViewCounts struct {
	TaskCount                   int            `json:"task_count"`
	RequestedTaskCount          int            `json:"requested_task_count"`
	AcceptanceRowCount          int            `json:"acceptance_row_count"`
	RequestedAcceptanceRowCount int            `json:"requested_acceptance_row_count"`
	AcceptedTaskCount           int            `json:"accepted_task_count"`
	PassingTaskCount            int            `json:"passing_task_count"`
	UnacceptedTaskCount         int            `json:"unaccepted_task_count"`
	NonpassingTaskCount         int            `json:"nonpassing_task_count"`
	StatusCounts                map[string]int `json:"status_counts"`
}

func (counts *e2eViewCounts) add(task e2eTaskState) {
	if counts.StatusCounts == nil {
		counts.StatusCounts = map[string]int{}
	}
	counts.TaskCount++
	counts.StatusCounts[task.Status]++
	rows := len(task.Contract.ScopeIDs) * len(task.Contract.Acceptance)
	counts.AcceptanceRowCount += rows
	if task.Status == "not_requested" {
		return
	}
	counts.RequestedTaskCount++
	counts.RequestedAcceptanceRowCount += rows
	if task.Status == "accepted" {
		counts.AcceptedTaskCount++
	} else {
		counts.UnacceptedTaskCount++
	}
	if task.Outcome == "pass" {
		counts.PassingTaskCount++
	} else {
		counts.NonpassingTaskCount++
	}
}

func (service *e2eService) readArgv(state *e2eState, action string, extra ...string) []string {
	args := []string{"specify-runtime", "e2e", action, "--run-id", state.RunID, "--project-root", service.projectRoot, "--format", "json"}
	return append(args, extra...)
}

func e2ePageBounds(total, offset, limit int) (int, int) {
	start := offset
	if start > total {
		start = total
	}
	end := start + limit
	if end > total {
		end = total
	}
	return start, end
}

// Only the response projection is paginated. The owner still validates the
// complete state and evidence chain before producing any view or mutation.
func (service *e2eService) compactEnvelope(env *Envelope, state *e2eState) {
	counts := e2eViewCounts{}
	stages := map[string]map[string]int{}
	for stage := 1; stage <= 7; stage++ {
		stages[strconv.Itoa(stage)] = map[string]int{}
	}
	for _, task := range state.Tasks {
		counts.add(task)
		stages[strconv.Itoa(task.Contract.Stage)][task.Status]++
	}
	env.Data["view"] = "compact"
	env.Data["scope_count"] = len(state.Scope)
	env.Data["counts"], env.Data["stage_counts"] = counts, stages
	env.Data["full_show_argv"] = service.readArgv(state, "status", "--view", "full")
	env.Data["task_show_argv"] = service.readArgv(state, "task-show", "--task-id", "<task-id>", "--view", "compact")
	env.ShowArgv = service.readArgv(state, "status", "--view", "compact", "--offset", strconv.Itoa(service.view.Offset), "--limit", strconv.Itoa(service.view.Limit))
	delete(env.Data, "scope")
	delete(env.Data, "tasks")
	// The canonical immutable packet remains accessible through packet_ref. The
	// dispatchable view already has its exact digest/pointer binding alongside it.
	delete(env.Data, "packet")
	delete(env.Data, "review_packet")
	if _, targeted := env.Data["selected_task_id"]; targeted {
		if task, ok := env.Data["task"].(e2eTaskState); ok {
			env.Data["task"] = map[string]any{
				"contract": task.Contract, "status": task.Status, "attempt": task.Attempt,
				"worker_id": task.WorkerID, "validator_id": task.ValidatorID, "outcome": task.Outcome,
				"packet": task.Packet, "submission": task.Submission, "review_packet": task.ReviewPacket,
				"review": task.Review, "acceptance": task.Acceptance, "history_count": len(task.History),
				"reopen_reason": task.ReopenReason,
			}
		}
		env.ShowArgv = service.readArgv(state, "task-show", "--task-id", env.Data["selected_task_id"].(string), "--view", "compact")
		return
	}
	start, end := e2ePageBounds(len(state.Tasks), service.view.Offset, service.view.Limit)
	tasks, gaps := []any{}, []any{}
	for _, task := range state.Tasks[start:end] {
		row := map[string]any{
			"id": task.Contract.ID, "stage": task.Contract.Stage, "status": task.Status,
			"outcome": task.Outcome, "attempt": task.Attempt, "scope_count": len(task.Contract.ScopeIDs),
			"acceptance_row_count": len(task.Contract.ScopeIDs) * len(task.Contract.Acceptance),
		}
		tasks = append(tasks, row)
		if task.Status != "not_requested" && (task.Status != "accepted" || task.Outcome != "pass") {
			gaps = append(gaps, map[string]any{"task_id": task.Contract.ID, "unaccepted": task.Status != "accepted", "nonpassing": task.Outcome != "pass"})
		}
	}
	next := []string{}
	if end < len(state.Tasks) {
		next = service.readArgv(state, "status", "--view", "compact", "--offset", strconv.Itoa(end), "--limit", strconv.Itoa(service.view.Limit))
	}
	env.Data["tasks"], env.Data["gaps"] = tasks, gaps
	env.Data["page"] = map[string]any{"offset": service.view.Offset, "limit": service.view.Limit, "returned": len(tasks), "total": len(state.Tasks), "revision": state.Revision}
	env.Data["next_page_argv"] = next
	// Invalidation can affect the complete denominator. Keep the total explicit
	// while exposing only the requested slice in a compact response.
	for _, name := range []string{"stale_task_ids", "invalidated_task_ids"} {
		if ids, ok := env.Data[name].([]string); ok {
			first, last := e2ePageBounds(len(ids), service.view.Offset, service.view.Limit)
			env.Data[name+"_count"] = len(ids)
			env.Data[name] = ids[first:last]
		}
	}
}

func (service *e2eService) taskShow(args []string) Envelope {
	state, err := service.readState()
	if err != nil {
		return service.unavailable("e2e state is unavailable; no resume template is safe", err)
	}
	index, err := e2eTaskIndex(&state, optionValue(args, "--task-id", ""))
	if err != nil {
		service.readinessBlocked = true
		return service.failureWithState("invalid", "unknown e2e task", &state, err)
	}
	stale, corrupt := service.diagnoseState(&state)
	if corrupt {
		env := service.failureWithState("blocked", "immutable E2E evidence is corrupt; no resume template is safe", &state, nil)
		env.NextArgv = []string{}
		return env
	}
	if len(stale) > 0 {
		ids := e2eInvalidate(&state, stale, "read-only task-show detected stale bindings")
		env := service.failureWithState("blocked", "E2E has stale artifacts; no resume template is safe", &state, nil)
		env.Data["stale_task_ids"], env.Data["state_mutated"] = ids, false
		env.NextArgv = []string{}
		return env
	}
	task := state.Tasks[index]
	env := service.envelope("ok", "E2E current task and exact handoff bindings; no state changed", &state)
	delete(env.Data, "tasks")
	env.Data["scope"] = e2eScopeForTask(&state, task.Contract)
	env.Data["selected_task_id"], env.Data["task"] = task.Contract.ID, task
	env.Data["state_mutated"], env.Data["resume_available"] = false, false
	env.Data["full_show_argv"] = service.readArgv(&state, "status", "--view", "full")
	env.ShowArgv = service.readArgv(&state, "task-show", "--task-id", task.Contract.ID)
	env.NextArgv = []string{}
	if task.Packet.Ref == "" {
		return env
	}
	var packet e2ePacket
	if err := service.readSnapshot(task.Packet, &packet); err != nil {
		return service.failureWithState("blocked", "current worker packet is unavailable; no resume template is safe", &state, err)
	}
	env.Data["packet"], env.Data["packet_ref"], env.Data["packet_sha256"], env.Data["attempt_id"] = packet, task.Packet.Ref, task.Packet.SHA256, packet.AttemptID
	env.Data["worker_task_packet"], env.Data["worker_task_packet_binding"] = packet.WorkerTaskPacket, e2ePacketViewBinding(task.Packet)
	if task.ReviewPacket.Ref != "" {
		var review e2eReviewPacket
		if err := service.readSnapshot(task.ReviewPacket, &review); err != nil {
			return service.failureWithState("blocked", "current review packet is unavailable; no resume template is safe", &state, err)
		}
		env.Data["review_packet"], env.Data["review_packet_ref"], env.Data["review_packet_sha256"] = review, task.ReviewPacket.Ref, task.ReviewPacket.SHA256
		env.Data["worker_task_packet"], env.Data["worker_task_packet_binding"] = review.WorkerTaskPacket, e2ePacketViewBinding(task.ReviewPacket)
	}
	if state.Status != "active" {
		return env
	}
	switch task.Status {
	case "running":
		env.Data["submission_template"] = e2eSubmissionTemplate(packet, task.Packet)
		env.Data["resume_available"] = true
		env.NextArgv = service.argv(&state, "task-submit", "--task-id", task.Contract.ID, "--worker-id", task.WorkerID, "--result-json", "<semantic-json|@path|->")
	case "reviewing":
		env.Data["review_template"] = map[string]any{"review_packet_sha256": task.ReviewPacket.SHA256, "submission_sha256": task.Submission.SHA256, "checks": e2eCheckTemplate(task.Contract, true)}
		env.Data["resume_available"] = true
		env.NextArgv = service.argv(&state, "review-submit", "--task-id", task.Contract.ID, "--validator-id", task.ValidatorID, "--result-json", "<semantic-json|@path|->")
	}
	return env
}

func e2ePacketViewBinding(ref e2eRef) map[string]any {
	return map[string]any{"artifact_ref": ref.Ref, "artifact_sha256": ref.SHA256, "json_pointer": "/worker_task_packet"}
}
