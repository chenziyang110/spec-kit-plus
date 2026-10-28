package main

import (
	"fmt"
	"sort"
	"strconv"
)

type e2eWaitReason struct {
	Kind      string `json:"kind"`
	TaskID    string `json:"task_id,omitempty"`
	Path      string `json:"path,omitempty"`
	OtherPath string `json:"other_path,omitempty"`
	Resource  string `json:"resource,omitempty"`
	Required  string `json:"required,omitempty"`
	Observed  string `json:"observed,omitempty"`
	Reason    string `json:"reason"`
}

type e2eReadyAction struct {
	TaskID     string   `json:"task_id"`
	Action     string   `json:"action"`
	Diagnostic bool     `json:"diagnostic,omitempty"`
	Argv       []string `json:"argv,omitempty"`
}

type e2eWaitingTask struct {
	TaskID      string          `json:"task_id"`
	Reasons     []e2eWaitReason `json:"reasons,omitempty"`
	ReasonCount int             `json:"reason_count"`
	ReasonKinds map[string]int  `json:"reason_kinds,omitempty"`
}

type e2eCandidateConflict struct {
	TaskID       string          `json:"task_id"`
	OtherTaskID  string          `json:"other_task_id"`
	OtherStatus  string          `json:"other_status"`
	Relationship string          `json:"relationship"`
	Reasons      []e2eWaitReason `json:"reasons"`
}

func e2eTaskConflicts(a, b e2eTaskSpec) []e2eWaitReason {
	reasons := []e2eWaitReason{}
	for _, resource := range a.Resources {
		if e2eContains(b.Resources, resource) {
			reasons = append(reasons, e2eWaitReason{Kind: "exclusive_resource", TaskID: b.ID, Resource: resource, Reason: "exclusive resource is shared"})
		}
	}
	for _, pair := range []struct {
		left, right []string
		kind        string
	}{{a.Outputs, b.Outputs, "write_write"}, {a.Outputs, b.Inputs, "write_read"}, {a.Inputs, b.Outputs, "read_write"}} {
		for _, left := range pair.left {
			for _, right := range pair.right {
				if e2ePathsOverlap([]string{left}, []string{right}) {
					reasons = append(reasons, e2eWaitReason{Kind: pair.kind, TaskID: b.ID, Path: left, OtherPath: right, Reason: "overlapping paths under platform case rules"})
				}
			}
		}
	}
	sort.Slice(reasons, func(i, j int) bool { return fmt.Sprint(reasons[i]) < fmt.Sprint(reasons[j]) })
	return reasons
}

// Query and mutation share this predicate. A nil worker describes readiness for
// a fresh eligible identity; mutation always supplies the actual identity.
// The owner still revalidates immutable receipts, mutable bindings and CAS first.
func (service *e2eService) startReasons(state *e2eState, index int, diagnostic bool, worker *string) []e2eWaitReason {
	task := state.Tasks[index]
	reasons := []e2eWaitReason{}
	add := func(kind, reason string) { reasons = append(reasons, e2eWaitReason{Kind: kind, Reason: reason}) }
	if state.Status != "active" {
		add("closed_run", "closed run requires evidence-backed reopen")
	}
	if task.Status != "pending" {
		add("not_pending", "task-start requires a pending task; reopen other work explicitly")
		return reasons
	}
	if diagnostic && task.Contract.Stage < 6 {
		add("diagnostic_stage", "diagnostic start is limited to stages 6 and 7")
	}
	if worker != nil {
		if !e2eIdentity(*worker) || *worker == state.LeaderID {
			add("worker_identity", "task requires a separately recorded worker identity")
		}
		if task.Contract.Stage == 6 && e2eAncestorAuthorConflict(state, index, *worker) {
			add("audit_author_conflict", "stage 6 audit worker participated in producing an audited dependency")
		}
	}
	if !diagnostic {
		for _, dep := range e2eDependencies(state, task.Contract) {
			i, _ := e2eTaskIndex(state, dep.TaskID)
			producer := state.Tasks[i]
			if producer.Status != "accepted" || (dep.Require == "passed" && producer.Outcome != "pass") {
				reasons = append(reasons, e2eWaitReason{Kind: "dependency", TaskID: dep.TaskID, Required: dep.Require, Observed: producer.Status + "/" + producer.Outcome, Reason: "prerequisite is not accepted with the required outcome"})
			}
		}
	}
	for i, other := range state.Tasks {
		if i != index && e2eContains([]string{"running", "submitted", "reviewing", "verified"}, other.Status) {
			reasons = append(reasons, e2eTaskConflicts(task.Contract, other.Contract)...)
		}
	}
	for _, ref := range task.Contract.Inputs {
		if _, err := service.readFile(ref); err != nil {
			reasons = append(reasons, e2eWaitReason{Kind: "input_unavailable", Path: ref, Reason: err.Error()})
		}
	}
	sort.Slice(reasons, func(i, j int) bool { return fmt.Sprint(reasons[i]) < fmt.Sprint(reasons[j]) })
	return reasons
}

func (service *e2eService) readyArgv(state *e2eState, action e2eReadyAction) []string {
	i, _ := e2eTaskIndex(state, action.TaskID)
	task := state.Tasks[i]
	extra := []string{"--task-id", action.TaskID}
	switch action.Action {
	case "task-start":
		extra = append(extra, "--worker-id", "<native-worker-id>")
		if action.Diagnostic {
			extra = append(extra, "--diagnostic")
		}
	case "task-submit":
		extra = append(extra, "--worker-id", task.WorkerID, "--result-json", "<semantic-json|@path|->")
	case "review-start":
		extra = append(extra, "--validator-id", "<independent-agent-id>")
	case "review-submit":
		extra = append(extra, "--validator-id", task.ValidatorID, "--result-json", "<semantic-json|@path|->")
	case "task-accept":
		extra = append(extra, "--leader-id", state.LeaderID)
	case "reopen":
		extra = append(extra, "--leader-id", state.LeaderID, "--reason", "<causal-repair-reason>", "--evidence-ref", "<reproduction-evidence-path>")
	}
	return service.argv(state, action.Action, extra...)
}

func (service *e2eService) addReadiness(env *Envelope, state *e2eState) {
	ready, waiting := []e2eReadyAction{}, []e2eWaitingTask{}
	candidates := []e2eTaskSpec{}
	for index, task := range state.Tasks {
		if task.Status == "not_requested" {
			continue
		}
		reasons := []e2eWaitReason{}
		action := e2eReadyAction{TaskID: task.Contract.ID}
		if service.readinessBlocked {
			reasons = append(reasons, e2eWaitReason{Kind: "stale_bindings", Reason: "repair the reported binding before any ordinary action"})
		} else if state.Status != "active" {
			reasons = append(reasons, e2eWaitReason{Kind: "closed_run", Reason: "closed run has no ordinary task action"})
		} else {
			switch task.Status {
			case "pending":
				reasons = service.startReasons(state, index, false, nil)
				if len(reasons) == 0 {
					action.Action = "task-start"
				} else if task.Contract.Stage >= 6 && len(service.startReasons(state, index, true, nil)) == 0 {
					action.Action = "task-start"
					action.Diagnostic = true
				}
			case "running":
				action.Action = "task-submit"
			case "submitted":
				action.Action = "review-start"
			case "reviewing":
				action.Action = "review-submit"
			case "verified":
				action.Action = "task-accept"
			case "rejected":
				action.Action = "reopen"
			}
		}
		if action.Action != "" {
			ready = append(ready, action)
			if action.Action == "task-start" {
				candidates = append(candidates, task.Contract)
			}
		}
		if len(reasons) > 0 {
			waiting = append(waiting, e2eWaitingTask{TaskID: task.Contract.ID, Reasons: reasons, ReasonCount: len(reasons)})
		}
	}
	sort.Slice(ready, func(i, j int) bool { return ready[i].TaskID < ready[j].TaskID })
	sort.Slice(waiting, func(i, j int) bool { return waiting[i].TaskID < waiting[j].TaskID })
	sort.Slice(candidates, func(i, j int) bool { return candidates[i].ID < candidates[j].ID })
	full := service.view.Mode != "compact"
	selected, _ := env.Data["selected_task_id"].(string)
	pairs := []e2eCandidateConflict{}
	pairCount := 0
	for i, a := range candidates {
		for _, b := range candidates[i+1:] {
			reasons := e2eTaskConflicts(a, b)
			if len(reasons) > 0 {
				pairCount++
				if full {
					pairs = append(pairs, e2eCandidateConflict{TaskID: a.ID, OtherTaskID: b.ID, OtherStatus: "pending", Relationship: "candidate_mutual_exclusion", Reasons: reasons})
				}
			}
		}
	}
	env.Data["fresh_revision"] = state.Revision
	env.Data["readiness_counts"] = map[string]int{"ready_action_count": len(ready), "waiting_task_count": len(waiting), "candidate_conflict_pair_count": pairCount}
	include := map[string]bool{}
	if selected != "" {
		include[selected] = true
	} else if !full {
		first, last := e2ePageBounds(len(state.Tasks), service.view.Offset, service.view.Limit)
		for _, task := range state.Tasks[first:last] {
			include[task.Contract.ID] = true
		}
	}
	visibleReady := []e2eReadyAction{}
	visibleWaiting := []e2eWaitingTask{}
	for _, action := range ready {
		if (full && selected == "") || include[action.TaskID] {
			if full || selected != "" {
				action.Argv = service.readyArgv(state, action)
			}
			visibleReady = append(visibleReady, action)
		}
	}
	for _, item := range waiting {
		if (full && selected == "") || include[item.TaskID] {
			if !full && selected == "" {
				item.ReasonKinds = map[string]int{}
				for _, reason := range item.Reasons {
					item.ReasonKinds[reason.Kind]++
				}
				item.Reasons = nil
			}
			visibleWaiting = append(visibleWaiting, item)
		}
	}
	env.Data["ready_actions"], env.Data["waiting"] = visibleReady, visibleWaiting
	if full && selected == "" {
		env.Data["candidate_conflicts"] = pairs
	}
	if selected != "" {
		i, _ := e2eTaskIndex(state, selected)
		conflicts := []e2eCandidateConflict{}
		candidateIDs := map[string]bool{}
		for _, candidate := range candidates {
			candidateIDs[candidate.ID] = true
		}
		for _, other := range state.Tasks {
			if other.Contract.ID != selected {
				reasons := e2eTaskConflicts(state.Tasks[i].Contract, other.Contract)
				if len(reasons) > 0 {
					relationship := "potential_overlap"
					if e2eContains([]string{"running", "submitted", "reviewing", "verified"}, other.Status) {
						relationship = "active_blocker"
					} else if candidateIDs[selected] && candidateIDs[other.Contract.ID] {
						relationship = "candidate_mutual_exclusion"
					}
					conflicts = append(conflicts, e2eCandidateConflict{TaskID: selected, OtherTaskID: other.Contract.ID, OtherStatus: other.Status, Relationship: relationship, Reasons: reasons})
				}
			}
		}
		sort.Slice(conflicts, func(i, j int) bool { return conflicts[i].OtherTaskID < conflicts[j].OtherTaskID })
		total := len(conflicts)
		first, last := 0, total
		if !full {
			first, last = e2ePageBounds(total, service.view.Offset, service.view.Limit)
		}
		env.Data["conflicts"] = conflicts[first:last]
		env.Data["conflict_page"] = map[string]int{"offset": first, "returned": last - first, "total": total, "revision": state.Revision}
		next := []string{}
		if last < total {
			next = service.readArgv(state, "task-show", "--task-id", selected, "--view", "compact", "--offset", strconv.Itoa(last), "--limit", strconv.Itoa(service.view.Limit))
		}
		env.Data["next_conflict_page_argv"] = next
		if !full {
			reasonTotal := 0
			for j := range visibleWaiting {
				item := &visibleWaiting[j]
				reasonTotal += item.ReasonCount
				first, last := e2ePageBounds(len(item.Reasons), service.view.Offset, service.view.Limit)
				item.Reasons = item.Reasons[first:last]
			}
			nextReasons := []string{}
			_, end := e2ePageBounds(reasonTotal, service.view.Offset, service.view.Limit)
			if end < reasonTotal {
				nextReasons = service.readArgv(state, "task-show", "--task-id", selected, "--view", "compact", "--offset", strconv.Itoa(end), "--limit", strconv.Itoa(service.view.Limit))
			}
			env.Data["next_waiting_page_argv"] = nextReasons
		}
	}
	if service.readinessBlocked {
		env.NextArgv = service.readArgv(state, "status")
		if len(service.diagnostics) > 0 {
			env.NextArgv = []string{}
			for _, diagnostic := range service.diagnostics {
				if !diagnostic.Immutable && !service.hasImmutableDiagnostic() {
					env.NextArgv = service.argv(state, "reopen", "--task-id", diagnostic.RootTaskID, "--leader-id", state.LeaderID, "--reason", "<causal-repair-reason>", "--evidence-ref", "<reproduction-evidence-path>")
					break
				}
			}
		}
	}
}
