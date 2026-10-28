package main

import (
	"fmt"
	"sort"
	"strings"
	"time"
)

const playbookObservedMinimumSamples = 3

type playbookMetricsGroup struct {
	Key, MethodID, FamilyID, TemplateDigest, InstanceDigest                string
	WorkloadDigest, ContextDigest, VerificationDigest, SourceBasisDigest   string
	ContextComplete                                                        bool
	Sessions, TerminalSessions, FirstPassEligible, FirstPass               int
	Dispositions, Attempts                                                 map[string]int
	Retries, Replans, BlockedEpisodes, Historical, MissingTiming, Retained int
	ExecutionMS, VerificationMS, RecoveryMS                                int64
	SuccessfulToolMS                                                       []int64
}

func aggregatePlaybookMetrics(sessions []DoSession, methodID string, context map[string]string) []*playbookMetricsGroup {
	groups := map[string]*playbookMetricsGroup{}
	for _, session := range sessions {
		o := projectDoMetrics(session)
		if o.MethodID != methodID || (context != nil && o.ContextDigest != doDigest(context)) {
			continue
		}
		key := doDigest([]string{o.MethodID, o.TemplateDigest, o.InstanceDigest, o.ContextDigest, o.VerificationDigest, o.SourceBasisDigest})
		group := groups[key]
		if group == nil {
			group = &playbookMetricsGroup{Key: key, MethodID: o.MethodID, FamilyID: o.FamilyID, TemplateDigest: o.TemplateDigest, InstanceDigest: o.InstanceDigest, WorkloadDigest: o.WorkloadDigest, ContextDigest: o.ContextDigest, VerificationDigest: o.VerificationDigest, SourceBasisDigest: o.SourceBasisDigest, ContextComplete: o.ContextComplete, Dispositions: map[string]int{"passed": 0, "failed": 0, "interrupted": 0, "blocked": 0, "pending": 0, "unknown": 0}, Attempts: map[string]int{"passed": 0, "failed": 0, "interrupted": 0, "running": 0, "unknown": 0}}
			groups[key] = group
		}
		group.Sessions++
		group.Dispositions[o.Disposition]++
		if o.Terminal {
			group.TerminalSessions++
		}
		if o.FirstPassEligible {
			group.FirstPassEligible++
			if o.FirstPass {
				group.FirstPass++
			}
		}
		for status, count := range o.AttemptCounts {
			group.Attempts[status] += count
		}
		group.Retries += o.Retries
		group.Replans += o.Replans
		group.BlockedEpisodes += o.BlockedEpisodes
		group.Historical += o.Historical
		group.Retained += o.Retained
		group.MissingTiming += o.MissingTiming
		group.ExecutionMS += o.ExecutionMS
		group.VerificationMS += o.VerificationMS
		group.RecoveryMS += o.RecoveryMS
		if o.Comparable && o.ExecutionPassed && o.TimingComplete && o.Attempts > 0 {
			group.SuccessfulToolMS = append(group.SuccessfulToolMS, o.ExecutionMS+o.VerificationMS)
		}
	}
	result := make([]*playbookMetricsGroup, 0, len(groups))
	for _, group := range groups {
		result = append(result, group)
	}
	sort.Slice(result, func(i, j int) bool { return result[i].Key < result[j].Key })
	return result
}

func playbookMetricsMedian(values []int64) any {
	if len(values) == 0 {
		return nil
	}
	ordered := append([]int64{}, values...)
	sort.Slice(ordered, func(i, j int) bool { return ordered[i] < ordered[j] })
	mid := len(ordered) / 2
	if len(ordered)%2 == 0 {
		return ordered[mid-1] + (ordered[mid]-ordered[mid-1])/2
	}
	return ordered[mid]
}

func (group *playbookMetricsGroup) card() map[string]any {
	var firstPassRate any
	if group.FirstPassEligible > 0 {
		firstPassRate = float64(group.FirstPass) / float64(group.FirstPassEligible)
	}
	return map[string]any{
		"group_digest": group.Key, "method_id": group.MethodID, "task_family": group.FamilyID,
		"template_digest": group.TemplateDigest, "instance_digest": group.InstanceDigest, "workload_digest": group.WorkloadDigest,
		"context_digest": group.ContextDigest, "context_complete": group.ContextComplete, "verification_contract_digest": group.VerificationDigest,
		"source_basis_digest": group.SourceBasisDigest,
		"sessions":            group.Sessions, "terminal_sessions": group.TerminalSessions, "current_dispositions": group.Dispositions,
		"attempts": group.Attempts, "first_pass_invocations": group.FirstPass, "first_pass_denominator": group.FirstPassEligible, "first_pass_rate": firstPassRate,
		"first_pass_denominator_semantics": "comparable invocations with an observed failure/interruption or completed execution; external blocks and mixed definition epochs excluded",
		"retries":                          group.Retries, "replans": group.Replans, "blocked_episodes": group.BlockedEpisodes, "historical_definition_attempts": group.Historical,
		"retained_attempts": group.Retained, "retention_policy": doMetricsRetentionPolicy,
		"missing_timing_attempts": group.MissingTiming, "observed_execution_ms": group.ExecutionMS, "observed_verification_ms": group.VerificationMS,
		"observed_recovery_attempt_ms": group.RecoveryMS, "successful_timing_samples": len(group.SuccessfulToolMS), "median_successful_tool_ms": playbookMetricsMedian(group.SuccessfulToolMS),
	}
}

func playbookMetrics(root string, args []string) (map[string]any, error) {
	id := optionValue(args, "--id", "")
	document, err := loadPlaybookDocument(root, id)
	if err != nil {
		return nil, err
	}
	var context map[string]string
	if raw := optionValue(args, "--context-json", ""); raw != "" {
		context, err = playbookReadContext(raw)
		if err != nil {
			return nil, err
		}
	}
	sessions, warnings, err := readDoMetricsSessions(root)
	if err != nil {
		return nil, err
	}
	groups := aggregatePlaybookMetrics(sessions, id, context)
	if raw := optionValue(args, "--parameters-json", ""); raw != "" {
		parameters, parseErr := playbookMetricsParameters(raw)
		if parseErr != nil {
			return nil, parseErr
		}
		definition, _, resolveErr := resolvePlaybookDefinition(root, document.Definition, parameters)
		if resolveErr != nil {
			return nil, resolveErr
		}
		digest, digestErr := playbookDefinitionDigest(definition)
		if digestErr != nil {
			return nil, digestErr
		}
		selected := []*playbookMetricsGroup{}
		for _, group := range groups {
			if group.InstanceDigest == digest && group.TemplateDigest == document.ContentDigest {
				selected = append(selected, group)
			}
		}
		groups = selected
	}
	cards := []map[string]any{}
	for i, group := range groups {
		if i == 20 {
			break
		}
		cards = append(cards, group.card())
	}
	return map[string]any{"schema_version": 1, "read_only": true, "id": id, "current_template_digest": document.ContentDigest, "groups": cards, "total_groups": len(groups), "groups_truncated": len(groups) > len(cards), "session_catalog_complete": len(warnings) == 0, "excluded_session_entries": len(warnings), "warnings": uniqueSortedTrimmed(warnings), "provenance": "agent_tool_observation", "claim_ready": false, "live_verification_required": true, "metrics_semantics": "current session dispositions are resumable snapshots; attempts retain all observed outcomes; successful playbook usage is not the denominator", "scan_cost": map[string]any{"sessions_read": len(sessions), "strategy": "read_only_session_scan", "constant_time": false}}, nil
}

func playbookMetricsParameters(raw string) (map[string]string, error) {
	parameters := map[string]string{}
	if raw != "" {
		if err := decodePlaybookJSON([]byte(raw), &parameters); err != nil {
			return nil, err
		}
		if parameters == nil {
			return nil, fmt.Errorf("playbook_parameters_must_be_object")
		}
	}
	return parameters, nil
}

type playbookObservedProfile struct {
	Group                 *playbookMetricsGroup
	ComparisonKey, Reason string
}

func playbookObservationProfile(root string, document PlaybookDocument, sourceStatus string, context, parameters map[string]string, sessions []DoSession, catalogComplete bool) playbookObservedProfile {
	profile := playbookObservedProfile{Reason: "insufficient_evidence"}
	if !catalogComplete {
		profile.Reason = "incomplete_session_catalog"
		return profile
	}
	if document.Status != "verified" || sourceStatus != "matched_prior_validation" {
		profile.Reason = "current_source_revalidation_required"
		return profile
	}
	if !doMetricsContextComplete(document.Definition, context) {
		profile.Reason = "incomplete_execution_context"
		return profile
	}
	definition, _, err := resolvePlaybookDefinition(root, document.Definition, parameters)
	if err != nil {
		profile.Reason = "parameters_unresolved"
		return profile
	}
	instanceDigest, err := playbookDefinitionDigest(definition)
	if err != nil {
		profile.Reason = "parameters_unresolved"
		return profile
	}
	sources, err := playbookSourceFingerprint(root, definition)
	if err != nil {
		profile.Reason = "source_basis_unavailable"
		return profile
	}
	for _, group := range aggregatePlaybookMetrics(sessions, document.ID, context) {
		if group.TemplateDigest != document.ContentDigest || group.InstanceDigest != instanceDigest || group.SourceBasisDigest != doDigest(sources) {
			continue
		}
		if profile.Group != nil {
			profile.Group = nil
			profile.Reason = "ambiguous_instances"
			return profile
		}
		profile.Group = group
	}
	if profile.Group == nil {
		return profile
	}
	group := profile.Group
	if !group.ContextComplete || group.FirstPassEligible < playbookObservedMinimumSamples || group.MissingTiming > 0 || group.Attempts["unknown"] > 0 {
		return profile
	}
	profile.ComparisonKey = doDigest([]string{group.FamilyID, group.WorkloadDigest, group.ContextDigest, group.VerificationDigest, group.SourceBasisDigest, sourceStatus})
	profile.Reason = "comparable_observed_history"
	return profile
}

func playbookObservedBetter(a, b playbookObservedProfile) bool {
	if a.ComparisonKey == "" || a.ComparisonKey != b.ComparisonKey || a.Group == nil || b.Group == nil {
		return false
	}
	left, right := a.Group.FirstPass*b.Group.FirstPassEligible, b.Group.FirstPass*a.Group.FirstPassEligible
	return left > right
}

// The caller supplies one comparison group. Reliability is a stable first
// pass; within an equal-rate group, only sufficiently sampled timing slots are
// reordered. A partial timing comparison is not a valid sort comparator.
func playbookObservedOrder(profiles []playbookObservedProfile) []int {
	order := make([]int, len(profiles))
	for i := range profiles {
		order[i] = i
	}
	sort.SliceStable(order, func(i, j int) bool { return playbookObservedBetter(profiles[order[i]], profiles[order[j]]) })
	for start := 0; start < len(order); {
		end := start + 1
		for end < len(order) && !playbookObservedBetter(profiles[order[start]], profiles[order[end]]) {
			end++
		}
		positions, timed := []int{}, []int{}
		for i := start; i < end; i++ {
			if len(profiles[order[i]].Group.SuccessfulToolMS) >= playbookObservedMinimumSamples {
				positions = append(positions, i)
				timed = append(timed, order[i])
			}
		}
		sort.SliceStable(timed, func(i, j int) bool {
			return playbookMetricsMedian(profiles[timed[i]].Group.SuccessfulToolMS).(int64) < playbookMetricsMedian(profiles[timed[j]].Group.SuccessfulToolMS).(int64)
		})
		for i, position := range positions {
			order[position] = timed[i]
		}
		start = end
	}
	return order
}

func (profile playbookObservedProfile) card() map[string]any {
	result := map[string]any{"reason": profile.Reason, "comparison_group": profile.ComparisonKey, "minimum_samples": playbookObservedMinimumSamples, "claim": "advisory_observations_not_optimality_or_new_execution_success"}
	if profile.Group != nil {
		result["first_pass_invocations"] = profile.Group.FirstPass
		result["first_pass_denominator"] = profile.Group.FirstPassEligible
		result["successful_timing_samples"] = len(profile.Group.SuccessfulToolMS)
		result["median_successful_tool_ms"] = playbookMetricsMedian(profile.Group.SuccessfulToolMS)
		result["metrics_argv"] = []string{"specify-runtime", "playbook", "metrics", "--id", profile.Group.MethodID, "--format", "json"}
	}
	return result
}

// Recovery hints bind observed differences, not an inferred causal diagnosis.
// A passed diagnostic is only a candidate preflight: moving it before a step
// or publishing prevention guidance still needs normal definition validation.
func doVerifiedRecoveryHints(session DoSession, validation DoValidation) []map[string]any {
	hints := []map[string]any{}
	if validation.Status != "passed" {
		return hints
	}
	latest, failed := map[string]DoAttempt{}, map[string]DoAttempt{}
	order := []string{}
	for _, attempt := range session.Attempts {
		key := attempt.Kind + ":" + attempt.TargetID
		if _, ok := latest[key]; !ok {
			order = append(order, key)
		}
		latest[key] = attempt
		if attempt.Status == "failed" || attempt.Status == "interrupted" || attempt.TimedOut || attempt.Cancelled || attempt.Recovery != nil {
			failed[key] = attempt
		}
	}
	for _, key := range order {
		before, ok := failed[key]
		after := latest[key]
		if !ok || before.ID == after.ID || after.Status != "passed" || after.EvidenceOrigin != "agent_tool_observation" || after.ToolCallID == "" || !doAttemptInCurrentDefinition(session, after) {
			continue
		}
		signal := strings.Join(strings.Fields(before.Summary), " ")
		if len(signal) > 512 {
			signal = string([]rune(signal)[:min(len([]rune(signal)), 160)])
		}
		discriminator := map[string]any{"target_id": before.TargetID, "kind": before.Kind, "status": before.Status, "exit_code": before.ExitCode, "timed_out": before.TimedOut, "cancelled": before.Cancelled, "action_digest": doDigest(map[string]any{"argv": before.Argv, "cwd": before.Cwd, "native_action": before.NativeAction}), "context_digest": doDigest(session.Context), "observed_signal_digest": doDigest(signal), "native_observation_sha256": before.NativeObservationSHA256}
		preflights := []map[string]any{}
		dependencies := doRecoveryDependencyIDs(session.Definition, after.Kind, after.TargetID)
		for _, step := range session.Definition.Steps {
			probe := latest["step:"+step.ID]
			finished, fe := time.Parse(time.RFC3339Nano, probe.FinishedAt)
			started, se := time.Parse(time.RFC3339Nano, after.StartedAt)
			if !dependencies[step.ID] || step.ID == after.TargetID || step.SideEffect != "read" || probe.Status != "passed" || probe.EvidenceOrigin != "agent_tool_observation" || probe.ToolCallID == "" || !doAttemptInCurrentDefinition(session, probe) || fe != nil || se != nil || finished.After(started) {
				continue
			}
			preflights = append(preflights, map[string]any{"action_id": step.ID, "attempt_id": probe.ID, "argv": step.Argv, "cwd": step.Cwd, "native_action": step.NativeAction, "native_observation_ref": probe.NativeObservationRef, "native_observation_sha256": probe.NativeObservationSHA256, "expected_result": step.ExpectedResult, "status": "observed_diagnostic_candidate", "prevention_verified": false})
			if len(preflights) == 3 {
				break
			}
		}
		hint := map[string]any{"failure_signature": doDigest(discriminator), "failure_discriminator": discriminator, "observed_signal": signal, "session_id": session.ID, "template_digest": doMethodDigest(session), "instance_digest": session.DefinitionDigest, "failed_attempt": before.ID, "verified_attempt": after.ID, "verified_definition_epoch": doCurrentDefinitionEpoch(session), "verification_digest": validation.EvidenceDigest, "observed_delta": map[string]any{"argv_changed": doDigest(before.Argv) != doDigest(after.Argv), "native_action_changed": doDigest(before.NativeAction) != doDigest(after.NativeAction), "cwd_changed": before.Cwd != after.Cwd, "definition_changed": before.DefinitionDigest != after.DefinitionDigest, "source_changed": before.SourceFingerprint != after.SourceFingerprint, "failed_action": map[string]any{"argv": before.Argv, "cwd": before.Cwd, "native_action": before.NativeAction, "native_observation_ref": before.NativeObservationRef, "native_observation_sha256": before.NativeObservationSHA256}, "verified_action": map[string]any{"argv": after.Argv, "cwd": after.Cwd, "native_action": after.NativeAction, "native_observation_ref": after.NativeObservationRef, "native_observation_sha256": after.NativeObservationSHA256}}, "preflight_candidates": preflights, "prevention_status": "candidate_requires_current_execution", "root_cause_proven": false, "provenance": "agent_tool_observation", "claim_ready": false}
		if before.Recovery != nil {
			hint["recovery_reason_claim"] = before.Recovery.Reason
			hint["recovery_evidence"] = before.Recovery.EvidenceRef
		}
		hints = append(hints, hint)
		if len(hints) == 6 {
			break
		}
	}
	return hints
}

func doRecoveryDependencyIDs(definition PlaybookDefinition, kind, target string) map[string]bool {
	dependencies := map[string][]string{}
	for _, step := range definition.Steps {
		dependencies[step.ID] = step.DependsOn
	}
	for _, check := range definition.Checks {
		dependencies[check.ID] = check.DependsOn
	}
	result := map[string]bool{}
	queue := append([]string{}, dependencies[target]...)
	for len(queue) > 0 {
		id := queue[0]
		queue = queue[1:]
		if result[id] {
			continue
		}
		result[id] = true
		queue = append(queue, dependencies[id]...)
	}
	return result
}

func playbookRecoveryHints(root string, document PlaybookDocument) (map[string]any, error) {
	sessions, warnings, err := readDoMetricsSessions(root)
	if err != nil {
		return nil, err
	}
	policy, policyWarnings, _ := (learningService{projectRoot: root}).loadLearningPolicy(false)
	warnings = append(warnings, policyWarnings...)
	hints := []map[string]any{}
	seen := map[string]bool{}
	sort.SliceStable(sessions, func(i, j int) bool { return sessions[i].CreatedAt > sessions[j].CreatedAt })
	matching, invalidated := 0, 0
	for _, session := range sessions {
		if playbookID(doMethodDefinition(session)) != document.ID || doMethodDigest(session) != document.ContentDigest {
			continue
		}
		matching++
		validation := doValidate(root, session, true)
		if validation.Status != "passed" {
			invalidated++
			continue
		}
		for _, hint := range doVerifiedRecoveryHints(session, validation) {
			// Learning uses the same policy at capture; direct recovery disclosure
			// also sanitizes human-written observation and recovery text.
			hint["observed_signal"] = redactLearningTextWithPolicy(fmt.Sprint(hint["observed_signal"]), policy).text
			if reason, ok := hint["recovery_reason_claim"].(string); ok {
				hint["recovery_reason_claim"] = redactLearningTextWithPolicy(reason, policy).text
			}
			key := fmt.Sprint(hint["failure_signature"]) + doDigest(hint["observed_delta"])
			if !seen[key] {
				hints = append(hints, hint)
				seen[key] = true
			}
		}
	}
	total := len(hints)
	if len(hints) > 6 {
		hints = hints[:6]
	}
	return map[string]any{"items": hints, "total": total, "truncated": total > len(hints), "matching_sessions": matching, "invalidated_sessions": invalidated, "session_catalog_complete": len(warnings) == 0, "warnings": uniqueSortedTrimmed(warnings), "prevention_verified": false, "claim_ready": false}, nil
}
