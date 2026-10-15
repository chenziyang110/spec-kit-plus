package main

import (
	"errors"
	"fmt"
	"sort"
	"strconv"
)

type e2eBindingError struct {
	Kind           string `json:"kind"`
	Path           string `json:"path"`
	ExpectedSHA256 string `json:"expected_sha256"`
	ObservedSHA256 string `json:"observed_sha256"`
	RootTaskID     string `json:"root_task_id"`
	Reason         string `json:"reason"`
	Immutable      bool   `json:"immutable"`
}

func (failure *e2eBindingError) Error() string { return failure.Reason }

func (service *e2eService) hasImmutableDiagnostic() bool {
	for _, diagnostic := range service.diagnostics {
		if diagnostic.Immutable {
			return true
		}
	}
	return false
}

type e2eDiagnostic struct {
	e2eBindingError
	AffectedTaskIDs   []string `json:"affected_task_ids"`
	AffectedTaskCount int      `json:"affected_task_count"`
	ResumeArgv        []string `json:"resume_argv"`
}

func e2eBindingContext(err error, kind, root string) error {
	var binding *e2eBindingError
	if errors.As(err, &binding) {
		copy := *binding
		if !copy.Immutable && kind != "" {
			copy.Kind = kind
		}
		if copy.RootTaskID == "" {
			copy.RootTaskID = root
		}
		return &copy
	}
	return &e2eBindingError{Kind: "binding_contract_corrupt", RootTaskID: root, Reason: err.Error(), Immutable: true}
}

func e2eAffectedTasks(state *e2eState, seeds map[string]bool) []string {
	affected := map[string]bool{}
	for id := range seeds {
		affected[id] = true
	}
	for changed := true; changed; {
		changed = false
		for _, task := range state.Tasks {
			if affected[task.Contract.ID] {
				continue
			}
			for _, dep := range e2eDependencies(state, task.Contract) {
				if affected[dep.TaskID] {
					affected[task.Contract.ID] = true
					changed = true
					break
				}
			}
		}
	}
	ids := []string{}
	for _, task := range state.Tasks {
		if affected[task.Contract.ID] && task.Status != "not_requested" {
			ids = append(ids, task.Contract.ID)
		}
	}
	sort.Strings(ids)
	return ids
}

func (service *e2eService) diagnoseState(state *e2eState) (map[string]bool, bool) {
	service.diagnostics = nil
	seeds := map[string]bool{}
	seen := map[string]bool{}
	corrupt := false
	broken := map[int]bool{}
	record := func(err error, task e2eTaskState) {
		var binding *e2eBindingError
		wrapped := e2eBindingContext(err, "", task.Contract.ID)
		errors.As(wrapped, &binding)
		if binding.Path == "" {
			binding.Path, binding.ExpectedSHA256, binding.ObservedSHA256 = task.Packet.Ref, task.Packet.SHA256, service.observed[task.Packet.Ref]
		}
		key := fmt.Sprint(*binding)
		if seen[key] {
			return
		}
		seen[key] = true
		if binding.Immutable {
			corrupt = true
		} else {
			seeds[binding.RootTaskID] = true
		}
		affected := e2eAffectedTasks(state, map[string]bool{binding.RootTaskID: true})
		service.diagnostics = append(service.diagnostics, e2eDiagnostic{e2eBindingError: *binding, AffectedTaskIDs: affected, AffectedTaskCount: len(affected)})
	}
	// Complete the current immutable preflight before inspecting any live
	// bindings. A changed input must never hide a later corrupt receipt and let
	// invalidation move it into history. readState separately verifies history.
	for index, task := range state.Tasks {
		for _, ref := range []e2eRef{task.Packet, task.Submission, task.ReviewPacket, task.Review, task.Acceptance} {
			if ref.Ref == "" {
				continue
			}
			var snapshot map[string]any
			if err := service.readSnapshot(ref, &snapshot); err != nil {
				broken[index] = true
				record(err, task)
			}
		}
	}
	for index, task := range state.Tasks {
		if task.Packet.Ref == "" || broken[index] {
			continue
		}
		if err := service.verifyTask(state, index); err != nil {
			record(err, task)
		}
	}
	sort.Slice(service.diagnostics, func(i, j int) bool {
		a, b := service.diagnostics[i], service.diagnostics[j]
		return a.RootTaskID+a.Kind+a.Path < b.RootTaskID+b.Kind+b.Path
	})
	service.readinessBlocked = len(service.diagnostics) > 0
	return seeds, corrupt
}

func (service *e2eService) unavailable(summary string, err error) Envelope {
	var binding *e2eBindingError
	if !errors.As(err, &binding) {
		binding = &e2eBindingError{Kind: "state_unavailable", Path: service.rootRef + "/state.json", Reason: err.Error(), Immutable: true}
	}
	env := e2eFailure("blocked", summary, err)
	env.Data = map[string]any{"diagnostics": []e2eDiagnostic{{e2eBindingError: *binding, AffectedTaskIDs: []string{}, ResumeArgv: []string{}}}, "state_mutated": false, "resume_available": false}
	return env
}

func (service *e2eService) addDiagnostics(env *Envelope, state *e2eState) {
	if service.lastDiagnosticEvent.Ref != "" {
		env.Data["diagnostic_history_count"] = service.diagnosticEventCount
		env.Data["diagnostic_history_ref"], env.Data["diagnostic_history_sha256"] = service.lastDiagnosticEvent.Ref, service.lastDiagnosticEvent.SHA256
		env.Data["diagnostic_history_show_argv"] = []string{"specify-runtime", "artifact", "show", "--path", service.lastDiagnosticEvent.Ref, "--project-root", service.projectRoot, "--view", "full", "--format", "json"}
	}
	if len(service.diagnostics) == 0 {
		return
	}
	immutableBlocked := service.hasImmutableDiagnostic()
	env.Data["recovery_blocked_by_immutable"] = immutableBlocked
	full := service.view.Mode != "compact"
	first, last := 0, len(service.diagnostics)
	if !full {
		first, last = e2ePageBounds(last, service.view.Offset, service.view.Limit)
	}
	rows := []e2eDiagnostic{}
	for _, original := range service.diagnostics[first:last] {
		row := original
		row.AffectedTaskCount = len(row.AffectedTaskIDs)
		if !row.Immutable && !immutableBlocked {
			row.ResumeArgv = service.argv(state, "reopen", "--task-id", row.RootTaskID, "--leader-id", state.LeaderID, "--reason", "<causal-repair-reason>", "--evidence-ref", "<reproduction-evidence-path>")
		} else {
			row.ResumeArgv = []string{}
		}
		if !full {
			row.AffectedTaskIDs = nil
			row.ResumeArgv = nil
		}
		rows = append(rows, row)
	}
	env.Data["diagnostics"], env.Data["diagnostic_count"] = rows, len(service.diagnostics)
	env.Data["diagnostics_state"] = service.diagnosticsState
	// Per-task affected membership is on the ordinary task pages. This avoids a
	// roots x descendants expansion in compact responses without losing coverage.
	if tasks, ok := env.Data["tasks"].([]any); ok {
		for _, raw := range tasks {
			row, ok := raw.(map[string]any)
			if !ok {
				continue
			}
			id, _ := row["id"].(string)
			roots := 0
			for _, diagnostic := range service.diagnostics {
				if e2eContains(diagnostic.AffectedTaskIDs, id) {
					roots++
				}
			}
			if roots > 0 {
				row["drift_root_count"] = roots
			}
		}
	}
	next := []string{}
	if last < len(service.diagnostics) {
		next = service.readArgv(state, "status", "--view", "compact", "--offset", strconv.Itoa(last), "--limit", strconv.Itoa(service.view.Limit))
	}
	env.Data["next_diagnostic_page_argv"] = next
	if !full {
		env.Data["diagnostic_show_argv"] = service.readArgv(state, "status", "--view", "full")
	}
}
