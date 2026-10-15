package main

import (
	"fmt"
	"os"
	"sort"
	"strings"
	"time"
)

const doMetricsRetentionPolicy = "same-source-local-output-direct-previous-epoch"

// Metrics are projections of the Do owner's existing observations. They never
// mutate a session, advance a workflow, or use successful playbook usage as the
// denominator of a success rate.
type doMetricsObservation struct {
	SessionID, MethodID, FamilyID, TemplateDigest, InstanceDigest        string
	WorkloadDigest, ContextDigest, VerificationDigest, SourceBasisDigest string
	Context                                                              map[string]string
	ContextComplete, Comparable, TimingComplete                          bool
	Disposition                                                          string
	Terminal, ExecutionPassed, FirstPassEligible, FirstPass              bool
	AttemptCounts                                                        map[string]int
	Attempts, Retries, Replans, BlockedEpisodes, Historical, Retained    int
	ExecutionMS, VerificationMS, RecoveryMS, ObservedSpanMS              int64
	TimedAttempts, MissingTiming                                         int
}

func doMetricsContextComplete(definition PlaybookDefinition, context map[string]string) bool {
	if context["os"] == "" || context["arch"] == "" || context["shell"] == "" {
		return false
	}
	toolchain := false
	for key, value := range context {
		if strings.HasPrefix(key, "toolchain.") && value != "" {
			toolchain = true
		}
	}
	return toolchain && len(playbookCompatibility(definition, context)) == 0
}

func doMetricsFamily(definition PlaybookDefinition) string {
	if definition.TaskFamily != "" {
		return definition.TaskFamily
	}
	return "legacy-method:" + playbookID(definition)
}

func doMetricsWorkload(definition PlaybookDefinition, parameters map[string]string) string {
	if parameters == nil {
		parameters = map[string]string{}
	}
	return doDigest(map[string]any{"family": doMetricsFamily(definition), "operation": definition.Operation, "target": definition.Target, "owner": definition.Owner, "goal": definition.Goal, "parameters": parameters, "source_files": uniqueSortedTrimmed(definition.SourceFiles)})
}

// Include actual required assertions and the dependency/expected-result
// contract. Implementation argv on steps can differ, but a faster candidate
// cannot win by dropping required work or weakening acceptance.
func doMetricsVerificationDigest(definition PlaybookDefinition) string {
	checks := []PlaybookCheck{}
	required := map[string]bool{}
	dependencies := map[string][]string{}
	for _, check := range definition.Checks {
		dependencies[check.ID] = check.DependsOn
		if check.Required {
			required[check.ID] = true
		}
	}
	for _, step := range definition.Steps {
		dependencies[step.ID] = step.DependsOn
		if step.Required {
			required[step.ID] = true
		}
	}
	queue := []string{}
	for id := range required {
		queue = append(queue, id)
	}
	for len(queue) > 0 {
		id := queue[0]
		queue = queue[1:]
		for _, dependency := range dependencies[id] {
			if !required[dependency] {
				required[dependency] = true
				queue = append(queue, dependency)
			}
		}
	}
	for _, check := range definition.Checks {
		if required[check.ID] {
			checks = append(checks, check)
		}
	}
	steps := []map[string]any{}
	for _, step := range definition.Steps {
		if required[step.ID] {
			steps = append(steps, map[string]any{"id": step.ID, "purpose": step.Purpose, "required": step.Required, "expected_result": step.ExpectedResult, "side_effect": step.SideEffect, "source_writes": uniqueSortedTrimmed(step.SourceWrites), "depends_on": uniqueSortedTrimmed(step.DependsOn)})
		}
	}
	return doDigest(map[string]any{"checks": checks, "steps": steps})
}

func projectDoMetrics(session DoSession) doMetricsObservation {
	method := doMethodDefinition(session)
	observation := doMetricsObservation{SessionID: session.ID, MethodID: playbookID(method), FamilyID: doMetricsFamily(method), TemplateDigest: doMethodDigest(session), InstanceDigest: session.DefinitionDigest, WorkloadDigest: doMetricsWorkload(session.Definition, session.Parameters), ContextDigest: doDigest(session.Context), Context: session.Context, VerificationDigest: doMetricsVerificationDigest(session.Definition), ContextComplete: doMetricsContextComplete(method, session.Context), Comparable: true, TimingComplete: true, Disposition: session.ExecutionOutcome, AttemptCounts: map[string]int{"passed": 0, "failed": 0, "interrupted": 0, "running": 0, "unknown": 0}, Replans: len(session.ReplanReceipts), BlockedEpisodes: len(session.BlockerHistory)}
	for _, epoch := range session.DefinitionHistory {
		if epoch.Epoch == doCurrentDefinitionEpoch(session) {
			observation.Retained = len(epoch.RetainedAttempts)
		}
	}
	sources := session.InitialSources
	for _, attempt := range session.Attempts {
		if doAttemptInCurrentDefinition(session, attempt) && len(attempt.AfterSources) > 0 {
			sources = attempt.AfterSources
		}
	}
	basis := map[string]string{}
	for _, source := range session.Definition.SourceFiles {
		basis[source] = sources[source]
	}
	for _, step := range session.Definition.Steps {
		if step.ScriptRef != "" {
			basis[step.ScriptRef] = sources[step.ScriptRef]
		}
	}
	for _, check := range session.Definition.Checks {
		if check.ScriptRef != "" {
			basis[check.ScriptRef] = sources[check.ScriptRef]
		}
	}
	observation.SourceBasisDigest = doDigest(basis)
	if session.Blocker != nil {
		observation.Disposition = "blocked"
		observation.BlockedEpisodes++
	}
	switch observation.Disposition {
	case "pending", "passed", "failed", "interrupted", "blocked":
	default:
		observation.Disposition = "unknown"
		observation.Comparable = false
	}
	observation.ExecutionPassed = session.ExecutionOutcome == "passed" && session.Blocker == nil
	if observation.ExecutionPassed && (session.Validation == nil || session.Validation.Status != "passed" || session.Validation.DefinitionDigest != session.DefinitionDigest) {
		observation.Comparable = false
	}
	observation.Terminal = observation.ExecutionPassed && (session.KnowledgeStatus == "saved" || session.KnowledgeStatus == "not_applicable")
	seen := map[string]bool{}
	firstFailure := false
	var first, last, firstFailureAt time.Time
	timed := []struct {
		started time.Time
		elapsed int64
	}{}
	for _, attempt := range session.Attempts {
		observation.Attempts++
		status := attempt.Status
		if _, ok := observation.AttemptCounts[status]; !ok {
			status = "unknown"
		}
		observation.AttemptCounts[status]++
		key := fmt.Sprintf("%d:%s:%s", attempt.DefinitionEpoch, attempt.Kind, attempt.TargetID)
		if seen[key] {
			observation.Retries++
		}
		seen[key] = true
		if !doAttemptInCurrentDefinition(session, attempt) {
			observation.Historical++
			observation.Comparable = false
		}
		if status == "running" || status == "unknown" {
			observation.Comparable = false
			continue
		}
		started, startErr := time.Parse(time.RFC3339Nano, attempt.StartedAt)
		finished, finishErr := time.Parse(time.RFC3339Nano, attempt.FinishedAt)
		if startErr != nil || finishErr != nil || finished.Before(started) || attempt.ElapsedMS != finished.Sub(started).Milliseconds() {
			observation.MissingTiming++
			observation.TimingComplete = false
		} else {
			observation.TimedAttempts++
			if first.IsZero() || started.Before(first) {
				first = started
			}
			if last.IsZero() || finished.After(last) {
				last = finished
			}
			if attempt.Kind == "check" {
				observation.VerificationMS += attempt.ElapsedMS
			} else {
				observation.ExecutionMS += attempt.ElapsedMS
			}
			timed = append(timed, struct {
				started time.Time
				elapsed int64
			}{started, attempt.ElapsedMS})
			if (status == "failed" || status == "interrupted") && (firstFailureAt.IsZero() || finished.Before(firstFailureAt)) {
				firstFailureAt = finished
			}
		}
		if status == "failed" || status == "interrupted" {
			firstFailure = true
		}
	}
	if !first.IsZero() && !last.IsZero() {
		observation.ObservedSpanMS = last.Sub(first).Milliseconds()
	}
	if !firstFailureAt.IsZero() {
		for _, attempt := range timed {
			if !attempt.started.Before(firstFailureAt) {
				observation.RecoveryMS += attempt.elapsed
			}
		}
	}
	// A failure is already evidence that the invocation was not first-pass,
	// even if it remains resumable. External blocks are disclosed separately.
	observation.FirstPassEligible = observation.Comparable && observation.Disposition != "blocked" && observation.Attempts > 0 && (observation.ExecutionPassed || firstFailure)
	observation.FirstPass = observation.FirstPassEligible && observation.ExecutionPassed && !firstFailure && observation.Retries == 0 && observation.Replans == 0
	return observation
}

func doSessionMetrics(session DoSession) map[string]any {
	o := projectDoMetrics(session)
	return map[string]any{
		"schema_version": 1, "read_only": true, "session_id": o.SessionID, "session_revision": session.Revision,
		"method_id": o.MethodID, "task_family": o.FamilyID, "template_digest": o.TemplateDigest, "instance_digest": o.InstanceDigest,
		"workload_digest": o.WorkloadDigest, "context_digest": o.ContextDigest, "verification_contract_digest": o.VerificationDigest,
		"source_basis_digest": o.SourceBasisDigest,
		"context_complete":    o.ContextComplete, "current_disposition": o.Disposition, "terminal": o.Terminal,
		"execution_passed": o.ExecutionPassed, "knowledge_status": session.KnowledgeStatus, "attempts": o.AttemptCounts,
		"attempt_count": o.Attempts, "retry_count": o.Retries, "replan_count": o.Replans, "blocked_episode_count": o.BlockedEpisodes,
		"historical_definition_attempts": o.Historical, "first_pass_eligible": o.FirstPassEligible, "first_pass": o.FirstPass,
		"retained_attempts": o.Retained, "retention_policy": doMetricsRetentionPolicy,
		"timing_complete": o.TimingComplete, "missing_timing_attempts": o.MissingTiming,
		"observed_execution_ms": o.ExecutionMS, "observed_verification_ms": o.VerificationMS,
		"observed_recovery_attempt_ms": o.RecoveryMS, "observed_tool_total_ms": o.ExecutionMS + o.VerificationMS,
		"observed_span_ms": o.ObservedSpanMS, "timing_semantics": "agent-observed tool durations; sums may overlap; span excludes unobserved exploration and knowledge persistence",
		"provenance": "agent_tool_observation", "claim_ready": false,
	}
}

func readDoMetricsSessions(root string) ([]DoSession, []string, error) {
	directory, err := secureProjectPath(root, ".specify/do/sessions")
	if err != nil {
		return nil, nil, err
	}
	entries, err := os.ReadDir(directory)
	if os.IsNotExist(err) {
		return []DoSession{}, []string{}, nil
	}
	if err != nil {
		return nil, nil, err
	}
	if len(entries) > 10000 {
		return nil, nil, fmt.Errorf("do_metrics_session_capacity_exceeded")
	}
	sessions, warnings := []DoSession{}, []string{}
	for _, entry := range entries {
		if !entry.IsDir() || !doIDPattern.MatchString(entry.Name()) {
			warnings = append(warnings, "do_metrics_unreadable_session_entry")
			continue
		}
		session, _, err := loadDoSession(root, entry.Name())
		if err != nil {
			warnings = append(warnings, "do_metrics_invalid_session_excluded")
			continue
		}
		// Metrics needs the verified session, not the potentially large audit
		// baseline. Avoid retaining every hydrated workspace in the collection.
		session.BaselineJSON = ""
		sessions = append(sessions, session)
	}
	sort.Slice(sessions, func(i, j int) bool { return sessions[i].ID < sessions[j].ID })
	return sessions, warnings, nil
}

func groupDoMetricsSessions(sessions []DoSession) map[string][]DoSession {
	groups := map[string][]DoSession{}
	for _, session := range sessions {
		id := playbookID(doMethodDefinition(session))
		groups[id] = append(groups[id], session)
	}
	return groups
}
