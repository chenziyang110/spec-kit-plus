package main

import (
	"encoding/json"
	"fmt"
	"regexp"
	"strings"
)

func allChecks() []check {
	return []check{
		{name: "required-artifacts", tiers: []string{"light", "standard", "deep"}, severity: statusFail, run: checkRequiredArtifacts},
		{name: "workflow-state-readiness", tiers: []string{"light", "standard", "deep"}, severity: statusFail, run: checkWorkflowStateReadiness},
		{name: "handoff-json-schema", tiers: []string{"light", "standard", "deep"}, severity: statusFail, run: checkHandoffJSONSchema},
		{name: "planning-gate-ready", tiers: []string{"light", "standard", "deep"}, severity: statusFail, run: checkPlanningGateReady},
		{name: "source-signal-disposition", tiers: []string{"light", "standard", "deep"}, severity: statusFail, run: checkSourceSignalDisposition},
		{name: "must-preserve-coverage", tiers: []string{"light", "standard", "deep"}, severity: statusFail, run: checkMustPreserveCoverage},
		{name: "review-state-approved", tiers: []string{"light", "standard", "deep"}, severity: statusWarn, run: checkReviewStateApproved},
		{name: "quality-gate-summary", tiers: []string{"light", "standard", "deep"}, severity: statusWarn, run: checkQualityGateSummary},
		{name: "scout-summary", tiers: []string{"light", "standard", "deep"}, severity: statusFail, run: checkScoutSummary},
		{name: "capability-triage", tiers: []string{"light", "standard", "deep"}, severity: statusFail, run: checkCapabilityTriage},
		{name: "execution-mode", tiers: []string{"light", "standard", "deep"}, severity: statusFail, run: checkExecutionMode},
		{name: "change-propagation", tiers: []string{"standard", "deep"}, severity: statusFail, run: checkChangePropagation},
		{name: "non-functional", tiers: []string{"standard", "deep"}, severity: statusWarn, run: checkNonFunctional},
		{name: "error-contract", tiers: []string{"standard", "deep"}, severity: statusWarn, run: checkErrorContract},
		{name: "config-effective-when", tiers: []string{"standard", "deep"}, severity: statusWarn, run: checkConfigEffectiveWhen},
		{name: "test-strategy", tiers: []string{"standard", "deep"}, severity: statusWarn, run: checkTestStrategy},
	}
}

// ---- artifact contract checks ----

func checkRequiredArtifacts(a artifactSet) checkResult {
	if strings.TrimSpace(a.specContract) != "" {
		missing := []string{}
		if strings.TrimSpace(a.spec) == "" {
			missing = append(missing, "spec.md")
		}
		if strings.TrimSpace(a.specContract) == "" {
			missing = append(missing, "spec-contract.json")
		}
		if len(missing) > 0 {
			return checkResult{status: statusFail, message: fmt.Sprintf("missing or empty required artifacts: %s", strings.Join(missing, ", "))}
		}
		return checkResult{status: statusPass, message: "canonical spec contract and project-facing spec present"}
	}

	missing := []string{}
	required := []struct {
		name    string
		content string
	}{
		{name: "spec.md", content: a.spec},
		{name: "alignment.md", content: a.alignment},
		{name: "context.md", content: a.context},
		{name: "workflow-state.md", content: a.workflowState},
		{name: "checklists/requirements.md", content: a.requirements},
		{name: "brainstorming/handoff-to-specify.json", content: a.handoff},
	}

	for _, artifact := range required {
		if strings.TrimSpace(artifact.content) == "" {
			missing = append(missing, artifact.name)
		}
	}

	if len(missing) > 0 {
		return checkResult{
			status:  statusFail,
			message: fmt.Sprintf("missing or empty required artifacts: %s", strings.Join(missing, ", ")),
		}
	}
	return checkResult{status: statusPass}
}

func checkWorkflowStateReadiness(a artifactSet) checkResult {
	if strings.TrimSpace(a.specContract) != "" {
		contract, result := parseSpecContract(a)
		if result.status != statusPass {
			return result
		}
		if normalizeBareValue(valueString(contract["status"])) != "planning-ready" {
			return checkResult{status: statusFail, message: "spec-contract status must be planning-ready"}
		}
		transition, ok := objectValue(contract["transition"])
		if !ok {
			return checkResult{status: statusFail, message: "spec-contract transition must be an object"}
		}
		if normalizeCommandToken(valueString(transition["next_action"])) != "/sp.plan" {
			return checkResult{status: statusFail, message: "spec-contract transition.next_action must be /sp.plan"}
		}
		return checkResult{status: statusPass, message: "canonical contract is planning-ready"}
	}

	if strings.TrimSpace(a.workflowState) == "" {
		return fileMissing("workflow-state.md")
	}

	state := parseMarkdownKeyValues(a.workflowState)
	var failures []string

	if normalizeWorkflowToken(state["active_command"]) != "sp-specify" {
		failures = append(failures, "active_command must be sp-specify")
	}
	if !workflowStatusReady(state["status"]) {
		failures = append(failures, "status must be completed or planning-ready")
	}
	reviewState := normalizeBareValue(state["last_user_reviewed_artifact_state"])
	if reviewState != "requested" && reviewState != "approved" {
		failures = append(failures, "last_user_reviewed_artifact_state must be requested or approved")
	}
	dispositionState := normalizeBareValue(state["source_signal_disposition_status"])
	if dispositionState != "complete" && dispositionState != "not-applicable" {
		failures = append(failures, "source_signal_disposition_status must be complete or not-applicable")
	}
	finalDecision := normalizeCommandToken(state["final_handoff_decision"])
	nextCommand := normalizeCommandToken(state["next_command"])
	if finalDecision != "/sp.plan" && nextCommand != "/sp.plan" {
		failures = append(failures, "final_handoff_decision or next_command must be /sp.plan")
	}

	if len(failures) > 0 {
		return checkResult{status: statusFail, message: strings.Join(failures, "; ")}
	}
	return checkResult{status: statusPass}
}

func checkHandoffJSONSchema(a artifactSet) checkResult {
	if strings.TrimSpace(a.specContract) != "" {
		contract, result := parseSpecContract(a)
		if result.status != statusPass {
			return result
		}
		required := []string{"version", "status", "target_need", "scope", "constraints", "acceptance_criteria", "decisions", "semantic_delta", "capability_operations", "must_preserve_refs", "consequence_obligation_refs", "context_capsule", "open_items", "artifact_refs", "transition"}
		missing := []string{}
		for _, key := range required {
			if _, ok := contract[key]; !ok {
				missing = append(missing, key)
			}
		}
		if len(missing) > 0 {
			return checkResult{status: statusFail, message: fmt.Sprintf("missing required spec-contract fields: %s", strings.Join(missing, ", "))}
		}
		for _, key := range []string{"constraints", "acceptance_criteria", "decisions", "semantic_delta", "capability_operations", "must_preserve_refs", "consequence_obligation_refs", "open_items"} {
			if _, ok := arrayValue(contract[key]); !ok {
				return checkResult{status: statusFail, message: fmt.Sprintf("spec-contract %s must be an array", key)}
			}
		}
		for _, key := range []string{"scope", "context_capsule", "artifact_refs", "transition"} {
			if _, ok := objectValue(contract[key]); !ok {
				return checkResult{status: statusFail, message: fmt.Sprintf("spec-contract %s must be an object", key)}
			}
		}
		return checkResult{status: statusPass}
	}

	handoff, result := parseHandoff(a)
	if result.status != statusPass {
		return result
	}

	required := []string{
		"status",
		"entry_source",
		"source_files_read",
		"source_signal_disposition",
		"must_preserve",
		"coverage_status",
		"planning_gate_status",
		"hard_unknown_count",
		"open_conflict_count",
		"quality_gate",
	}
	missing := []string{}
	for _, key := range required {
		if _, ok := handoff[key]; !ok {
			missing = append(missing, key)
		}
	}
	if len(missing) > 0 {
		return checkResult{status: statusFail, message: fmt.Sprintf("missing required handoff fields: %s", strings.Join(missing, ", "))}
	}
	var malformed []string
	if !requiredStringField(handoff, "status") {
		malformed = append(malformed, "status must be a non-empty string")
	}
	if !requiredStringField(handoff, "entry_source") {
		malformed = append(malformed, "entry_source must be a non-empty string")
	}
	if _, ok := arrayValue(handoff["source_files_read"]); !ok {
		malformed = append(malformed, "source_files_read must be an array")
	}
	if _, ok := arrayValue(handoff["source_signal_disposition"]); !ok {
		malformed = append(malformed, "source_signal_disposition must be an array")
	}
	if _, ok := arrayValue(handoff["must_preserve"]); !ok {
		malformed = append(malformed, "must_preserve must be an array")
	}
	if !requiredStringField(handoff, "coverage_status") {
		malformed = append(malformed, "coverage_status must be a non-empty string")
	}
	if !requiredStringField(handoff, "planning_gate_status") {
		malformed = append(malformed, "planning_gate_status must be a non-empty string")
	}
	if _, ok := numericValue(handoff["hard_unknown_count"]); !ok {
		malformed = append(malformed, "hard_unknown_count must be numeric")
	}
	if _, ok := numericValue(handoff["open_conflict_count"]); !ok {
		malformed = append(malformed, "open_conflict_count must be numeric")
	}
	if _, ok := objectValue(handoff["quality_gate"]); !ok {
		malformed = append(malformed, "quality_gate must be an object")
	}
	if len(malformed) > 0 {
		return checkResult{status: statusFail, message: strings.Join(malformed, "; ")}
	}
	return checkResult{status: statusPass}
}

func checkPlanningGateReady(a artifactSet) checkResult {
	if strings.TrimSpace(a.specContract) != "" {
		contract, result := parseSpecContract(a)
		if result.status != statusPass {
			return result
		}
		failures := []string{}
		if normalizeBareValue(valueString(contract["status"])) != "planning-ready" {
			failures = append(failures, "status must be planning-ready")
		}
		if strings.TrimSpace(valueString(contract["target_need"])) == "" {
			failures = append(failures, "target_need must be non-empty")
		}
		criteria, ok := arrayValue(contract["acceptance_criteria"])
		if !ok || len(criteria) == 0 {
			failures = append(failures, "acceptance_criteria must be non-empty")
		}
		transition, ok := objectValue(contract["transition"])
		if !ok {
			failures = append(failures, "transition must be an object")
		} else {
			if normalizeBareValue(valueString(transition["status"])) != "ready" {
				failures = append(failures, "transition.status must be ready")
			}
			blockers, blockersOK := arrayValue(transition["blockers"])
			if !blockersOK || len(blockers) > 0 {
				failures = append(failures, "transition.blockers must be an empty array")
			}
		}
		if len(failures) > 0 {
			return checkResult{status: statusFail, message: strings.Join(failures, "; ")}
		}
		return checkResult{status: statusPass}
	}

	handoff, result := parseHandoff(a)
	if result.status != statusPass {
		return result
	}

	var failures []string
	planningStatus := normalizeBareValue(valueString(handoff["planning_gate_status"]))
	if planningStatus != "ready" {
		failures = append(failures, fmt.Sprintf("planning_gate_status must be ready, got %q", planningStatus))
	}
	coverageStatus := normalizeBareValue(valueString(handoff["coverage_status"]))
	if coverageStatus == "" || containsAny(coverageStatus, []string{"incomplete", "blocked", "missing"}) {
		failures = append(failures, fmt.Sprintf("coverage_status is not planning-ready: %q", coverageStatus))
	}
	if count, ok := numericValue(handoff["hard_unknown_count"]); !ok {
		failures = append(failures, "hard_unknown_count must be numeric")
	} else if count > 0 {
		failures = append(failures, fmt.Sprintf("hard_unknown_count must be 0, got %g", count))
	}
	if count, ok := numericValue(handoff["open_conflict_count"]); !ok {
		failures = append(failures, "open_conflict_count must be numeric")
	} else if count > 0 {
		failures = append(failures, fmt.Sprintf("open_conflict_count must be 0, got %g", count))
	}

	if len(failures) > 0 {
		return checkResult{status: statusFail, message: strings.Join(failures, "; ")}
	}
	return checkResult{status: statusPass}
}

func checkSourceSignalDisposition(a artifactSet) checkResult {
	if strings.TrimSpace(a.specContract) != "" {
		contract, result := parseSpecContract(a)
		if result.status != statusPass {
			return result
		}
		operations, ok := arrayValue(contract["capability_operations"])
		if !ok {
			return checkResult{status: statusFail, message: "spec-contract capability_operations must be an array"}
		}
		return checkResult{status: statusPass, message: fmt.Sprintf("%d capability operations checked", len(operations))}
	}

	handoff, result := parseHandoff(a)
	if result.status != statusPass {
		return result
	}

	rows, ok := arrayValue(handoff["source_signal_disposition"])
	if !ok {
		return checkResult{status: statusFail, message: "source_signal_disposition must be an array"}
	}
	if len(rows) == 0 {
		return checkResult{status: statusPass, message: "no source signal dispositions recorded"}
	}

	allowed := map[string]bool{
		"preserved":             true,
		"in_scope":              true,
		"deferred":              true,
		"dropped":               true,
		"clarification_blocker": true,
	}
	for i, row := range rows {
		obj, ok := objectValue(row)
		if !ok {
			return checkResult{status: statusFail, message: fmt.Sprintf("source_signal_disposition[%d] must be an object", i)}
		}
		disposition := firstStringValue(obj, "disposition", "status", "state")
		disposition = normalizeBareValue(disposition)
		if disposition == "" {
			return checkResult{status: statusFail, message: fmt.Sprintf("source_signal_disposition[%d] has no disposition", i)}
		}
		if !allowed[disposition] {
			return checkResult{status: statusFail, message: fmt.Sprintf("source_signal_disposition[%d] has unknown disposition %q", i, disposition)}
		}
		if disposition == "clarification_blocker" {
			return checkResult{status: statusFail, message: fmt.Sprintf("source_signal_disposition[%d] is a clarification_blocker", i)}
		}
	}
	return checkResult{status: statusPass, message: fmt.Sprintf("%d source signal disposition rows checked", len(rows))}
}

func checkMustPreserveCoverage(a artifactSet) checkResult {
	if strings.TrimSpace(a.specContract) != "" {
		contract, result := parseSpecContract(a)
		if result.status != statusPass {
			return result
		}
		refs, ok := arrayValue(contract["must_preserve_refs"])
		if !ok {
			return checkResult{status: statusFail, message: "spec-contract must_preserve_refs must be an array"}
		}
		for i, ref := range refs {
			if strings.TrimSpace(valueString(ref)) == "" {
				return checkResult{status: statusFail, message: fmt.Sprintf("must_preserve_refs[%d] must be a non-empty stable ref", i)}
			}
		}
		return checkResult{status: statusPass, message: fmt.Sprintf("%d must-preserve refs checked", len(refs))}
	}

	handoff, result := parseHandoff(a)
	if result.status != statusPass {
		return result
	}

	rows, ok := arrayValue(handoff["must_preserve"])
	if !ok {
		return checkResult{status: statusFail, message: "must_preserve must be an array"}
	}
	if len(rows) == 0 {
		return checkResult{status: statusPass, message: "no must_preserve rows recorded"}
	}

	for i, row := range rows {
		obj, ok := objectValue(row)
		if !ok {
			return checkResult{status: statusFail, message: fmt.Sprintf("must_preserve[%d] must be an object", i)}
		}
		trace := firstStringValue(obj, "id", "summary", "signal", "description")
		if strings.TrimSpace(trace) == "" {
			return checkResult{status: statusFail, message: fmt.Sprintf("must_preserve[%d] has no stable id, summary, signal, or description", i)}
		}
		state := normalizeBareValue(firstStringValue(obj, "status", "disposition", "coverage_status", "state"))
		if containsAny(state, []string{"unmapped", "unresolved", "missing", "incomplete"}) {
			return checkResult{status: statusFail, message: fmt.Sprintf("must_preserve[%d] is not mapped: %q", i, state)}
		}
	}
	return checkResult{status: statusPass, message: fmt.Sprintf("%d must_preserve rows checked", len(rows))}
}

func checkReviewStateApproved(a artifactSet) checkResult {
	if strings.TrimSpace(a.specContract) != "" {
		contract, result := parseSpecContract(a)
		if result.status != statusPass {
			return result
		}
		delta, _ := arrayValue(contract["semantic_delta"])
		if len(delta) == 0 {
			return checkResult{status: statusPass, message: "no semantic delta requires repeated user review"}
		}
		state := parseMarkdownKeyValues(a.workflowState)
		reviewState := normalizeBareValue(state["last_user_reviewed_artifact_state"])
		if reviewState == "approved" {
			return checkResult{status: statusPass}
		}
		return checkResult{status: statusWarn, message: "semantic delta is non-empty without approved user review state"}
	}

	if strings.TrimSpace(a.workflowState) == "" {
		return fileMissing("workflow-state.md")
	}
	state := parseMarkdownKeyValues(a.workflowState)
	reviewState := normalizeBareValue(state["last_user_reviewed_artifact_state"])
	if reviewState == "approved" {
		return checkResult{status: statusPass}
	}
	if reviewState == "requested" {
		return checkResult{status: statusWarn, message: "user review was requested but explicit approval is not recorded"}
	}
	return checkResult{status: statusFail, message: "last_user_reviewed_artifact_state must be requested or approved"}
}

func checkQualityGateSummary(a artifactSet) checkResult {
	if strings.TrimSpace(a.specContract) != "" {
		contract, result := parseSpecContract(a)
		if result.status != statusPass {
			return result
		}
		if normalizeBareValue(valueString(contract["status"])) == "planning-ready" {
			return checkResult{status: statusPass, message: "planning-ready contract records deterministic gate result"}
		}
		return checkResult{status: statusWarn, message: "spec-contract is not planning-ready"}
	}

	handoff, result := parseHandoff(a)
	if result.status != statusPass {
		return result
	}
	qualityGate, ok := objectValue(handoff["quality_gate"])
	if !ok {
		return checkResult{status: statusFail, message: "quality_gate must be an object"}
	}
	status := firstStringValue(qualityGate, "status", "state")
	summary := firstStringValue(qualityGate, "summary", "decision", "result")
	if strings.TrimSpace(status) == "" && strings.TrimSpace(summary) == "" {
		return checkResult{status: statusWarn, message: "quality_gate has no readable status or summary"}
	}
	return checkResult{status: statusPass}
}

func parseHandoff(a artifactSet) (map[string]any, checkResult) {
	if strings.TrimSpace(a.handoff) == "" {
		return nil, fileMissing("brainstorming/handoff-to-specify.json")
	}
	var handoff map[string]any
	if err := json.Unmarshal([]byte(a.handoff), &handoff); err != nil {
		return nil, checkResult{status: statusFail, message: fmt.Sprintf("invalid brainstorming/handoff-to-specify.json: %v", err)}
	}
	return handoff, checkResult{status: statusPass}
}

func parseSpecContract(a artifactSet) (map[string]any, checkResult) {
	if strings.TrimSpace(a.specContract) == "" {
		return nil, fileMissing("spec-contract.json")
	}
	var contract map[string]any
	if err := json.Unmarshal([]byte(a.specContract), &contract); err != nil {
		return nil, checkResult{status: statusFail, message: fmt.Sprintf("invalid spec-contract.json: %v", err)}
	}
	return contract, checkResult{status: statusPass}
}

func parseMarkdownKeyValues(content string) map[string]string {
	values := map[string]string{}
	re := regexp.MustCompile(`^\s*[-*]?\s*([A-Za-z0-9_-]+)\s*:\s*(.+?)\s*$`)
	for _, line := range strings.Split(content, "\n") {
		match := re.FindStringSubmatch(line)
		if match == nil {
			continue
		}
		values[strings.ToLower(match[1])] = strings.TrimSpace(match[2])
	}
	return values
}

func workflowStatusReady(value string) bool {
	normalized := normalizeBareValue(value)
	return normalized == "completed" || normalized == "planning-ready" || normalized == "ready"
}

func normalizeCommandToken(value string) string {
	normalized := normalizeBareValue(value)
	normalized = strings.ReplaceAll(normalized, "`", "")
	normalized = strings.TrimSpace(normalized)
	if normalized == "/sp-plan" {
		return "/sp.plan"
	}
	return normalized
}

func normalizeWorkflowToken(value string) string {
	normalized := normalizeBareValue(value)
	normalized = strings.TrimPrefix(normalized, "/")
	return strings.ReplaceAll(normalized, ".", "-")
}

func normalizeBareValue(value string) string {
	value = strings.TrimSpace(strings.ToLower(value))
	value = strings.Trim(value, "`\"'[]")
	value = strings.TrimRight(value, ",;")
	return value
}

func valueString(value any) string {
	switch typed := value.(type) {
	case string:
		return typed
	case fmt.Stringer:
		return typed.String()
	default:
		return fmt.Sprintf("%v", value)
	}
}

func numericValue(value any) (float64, bool) {
	switch typed := value.(type) {
	case float64:
		return typed, true
	case int:
		return float64(typed), true
	case json.Number:
		n, err := typed.Float64()
		return n, err == nil
	default:
		return 0, false
	}
}

func arrayValue(value any) ([]any, bool) {
	rows, ok := value.([]any)
	return rows, ok
}

func objectValue(value any) (map[string]any, bool) {
	obj, ok := value.(map[string]any)
	return obj, ok
}

func firstStringValue(obj map[string]any, keys ...string) string {
	for _, key := range keys {
		if value, ok := obj[key]; ok {
			str := valueString(value)
			if strings.TrimSpace(str) != "" {
				return str
			}
		}
	}
	return ""
}

func requiredStringField(obj map[string]any, key string) bool {
	value, ok := obj[key].(string)
	return ok && strings.TrimSpace(value) != ""
}

func containsAny(value string, needles []string) bool {
	for _, needle := range needles {
		if strings.Contains(value, needle) {
			return true
		}
	}
	return false
}

// ---- check 1: scout-summary ----
// context.md must cover at least 3 of 6 scout topics.

var scoutTopicGroups = [][]string{
	// ownership / module attribution
	{"owning module", "owned by", "module ownership", "归属", "所属模块", "所属"},
	// reusable assets
	{"reusable", "reuse", "existing component", "existing service", "复用", "可复用"},
	// change-propagation hotspots
	{"change-propagation", "change propagation", "consumer surface", "affected module", "传播", "冲击", "受影响"},
	// integration boundaries
	{"integration boundary", "integration point", "interface boundary", "集成边界", "集成点", "边界"},
	// verification entry points
	{"verification entry", "test entry", "验证入口", "测试入口", "回归"},
	// known unknowns
	{"known unknown", "stale evidence", "gap", "隐忧", "未知", "风险"},
}

func checkScoutSummary(a artifactSet) checkResult {
	if strings.TrimSpace(a.specContract) != "" {
		contract, result := parseSpecContract(a)
		if result.status != statusPass {
			return result
		}
		capsule, ok := objectValue(contract["context_capsule"])
		if !ok {
			return checkResult{status: statusFail, message: "spec-contract context_capsule must be an object"}
		}
		for _, key := range []string{"evidence_refs", "selected_capabilities", "minimal_live_reads", "validation_routes", "stale_if"} {
			if _, ok := arrayValue(capsule[key]); !ok {
				return checkResult{status: statusFail, message: fmt.Sprintf("context_capsule.%s must be an array", key)}
			}
		}
		return checkResult{status: statusPass, message: "compact context capsule is structurally valid"}
	}

	if a.context == "" {
		return fileMissing("context.md")
	}

	covered := countKeywordGroups(a.context, scoutTopicGroups)

	if covered >= 4 {
		return checkResult{status: statusPass}
	}
	if covered >= 3 {
		return checkResult{
			status:  statusPass,
			message: fmt.Sprintf("covers %d/6 scout topics (minimum 3)", covered),
		}
	}
	return checkResult{
		status:  statusFail,
		message: fmt.Sprintf("only %d/6 scout topics covered in context.md (need >= 3): ownership, reusable, change-propagation, integration, verification, known-unknowns", covered),
	}
}

// ---- check 2: capability-triage ----
// Each capability in spec.md must have a state label: confirmed/已证明, inferred/可推断, or unresolved/未验证.

var capabilityStateLabels = []string{
	"confirmed", "已证明",
	"inferred", "可推断",
	"unresolved", "未验证",
}

func checkCapabilityTriage(a artifactSet) checkResult {
	if strings.TrimSpace(a.specContract) != "" {
		contract, result := parseSpecContract(a)
		if result.status != statusPass {
			return result
		}
		operations, ok := arrayValue(contract["capability_operations"])
		if !ok {
			return checkResult{status: statusFail, message: "spec-contract capability_operations must be an array"}
		}
		return checkResult{status: statusPass, message: fmt.Sprintf("%d canonical capability operations recorded", len(operations))}
	}

	if a.spec == "" {
		return fileMissing("spec.md")
	}

	// find capability-definition sections (exclude test-strategy / configuration sections)
	excludeInHeading := []string{"test", "测试", "config", "配置"}
	var capSections []section
	for _, s := range findSectionsWithHeadings(a.spec, "capability") {
		if hasKeyword(s.heading, excludeInHeading) {
			continue
		}
		capSections = append(capSections, s)
	}
	for _, s := range findSectionsWithHeadings(a.spec, "能力") {
		if hasKeyword(s.heading, excludeInHeading) {
			continue
		}
		capSections = append(capSections, s)
	}

	if len(capSections) == 0 {
		return checkResult{
			status:  statusWarn,
			message: "no capability sections found; cannot verify triage labels",
		}
	}

	// extract capability entries: both table rows and list items (deduplicate)
	seen := map[string]bool{}
	var capabilities []string
	capListRe := regexp.MustCompile(`(?mi)^[\s]*[-*]\s*\*?\*?(CAP|Cap|cap|\d+\.)`)
	capTablePrefixRe := regexp.MustCompile(`(?mi)^\s*\|\s*(CAP|Cap|cap|\d+)`)

	for _, sec := range capSections {
		lines := strings.Split(sec.body, "\n")
		for _, line := range lines {
			trimmed := strings.TrimSpace(line)
			if seen[trimmed] {
				continue
			}
			if capListRe.MatchString(line) || capTablePrefixRe.MatchString(line) {
				seen[trimmed] = true
				capabilities = append(capabilities, line)
			}
		}
	}

	if len(capabilities) == 0 {
		return checkResult{
			status:  statusWarn,
			message: "no capability list detected; cannot verify triage labels",
		}
	}

	// filter out table header rows (contain header words but no state label)
	headerWords := []string{"purpose", "description", "capability", "能力", "描述", "purpose"}
	var filtered []string
	for _, cap := range capabilities {
		trimmed := strings.TrimSpace(cap)
		if strings.HasPrefix(trimmed, "|") && hasKeyword(cap, headerWords) && !hasKeyword(cap, capabilityStateLabels) {
			continue
		}
		filtered = append(filtered, cap)
	}

	if len(filtered) == 0 {
		return checkResult{
			status:  statusWarn,
			message: "no capability data rows detected (only headers found)",
		}
	}

	labeled := 0
	for _, cap := range filtered {
		if hasKeyword(cap, capabilityStateLabels) {
			labeled++
		}
	}

	ratio := float64(labeled) / float64(len(filtered))
	if ratio >= 0.8 {
		return checkResult{
			status:  statusPass,
			message: fmt.Sprintf("%d/%d capabilities labeled", labeled, len(filtered)),
		}
	}
	return checkResult{
		status:  statusFail,
		message: fmt.Sprintf("%d/%d capabilities have state labels (need >= 80%%): confirmed/已证明, inferred/可推断, unresolved/未验证", labeled, len(filtered)),
	}
}

// ---- check 3: execution-mode ----
// workflow-state.md or alignment.md must record execution_model.

func checkExecutionMode(a artifactSet) checkResult {
	if strings.TrimSpace(a.specContract) != "" {
		return checkResult{status: statusPass, message: "specification quality is independent of agent dispatch mode"}
	}

	combined := a.workflowState + "\n" + a.alignment
	if combined == "\n" {
		return checkResult{
			status:  statusFail,
			message: "workflow-state.md and alignment.md both missing — cannot verify execution model",
		}
	}

	execRe := regexp.MustCompile(`(?i)execution[ _-]m(?:ode|odel)\s*[:\-=]\s*(\S+)`)
	match := execRe.FindStringSubmatch(combined)
	if match != nil {
		mode := match[1]
		return checkResult{
			status:  statusPass,
			message: fmt.Sprintf("execution_model: %s", strings.TrimRight(mode, ",;")),
		}
	}
	return checkResult{
		status:  statusFail,
		message: "execution_model not recorded in workflow-state.md or alignment.md",
	}
}

// ---- check 4: change-propagation ----
// context.md must have a change-propagation matrix (table).

var changePropHeadings = []string{
	"change-propagation", "change propagation", "impact", "变更传播", "冲击", "影响面", "影响矩阵",
}

func checkChangePropagation(a artifactSet) checkResult {
	if strings.TrimSpace(a.specContract) != "" && strings.TrimSpace(a.context) == "" {
		return checkResult{status: statusPass, message: "conditional context view omitted; propagation evidence remains reference-backed in spec-contract"}
	}

	if a.context == "" {
		return fileMissing("context.md")
	}

	// find relevant sections
	var sections []string
	for _, h := range changePropHeadings {
		sections = append(sections, findSections(a.context, h)...)
	}

	if len(sections) == 0 {
		return checkResult{
			status:  statusFail,
			message: "no change-propagation / impact section found in context.md",
		}
	}

	// check for a table within those sections
	for _, sec := range sections {
		rows := countTableDataRows(sec)
		if rows >= 1 {
			return checkResult{
				status:  statusPass,
				message: fmt.Sprintf("change-propagation matrix found (%d data rows)", rows),
			}
		}
	}

	return checkResult{
		status:  statusFail,
		message: "change-propagation section found but no data table present",
	}
}

// ---- check 5: non-functional ----
// spec.md should cover NFR dimensions: performance, security, reliability, observability.

var nfrGroups = [][]string{
	{"performance", "latency", "throughput", "startup", "性能", "延迟", "吞吐", "启动时间"},
	{"security", "auth", "permission", "injection", "安全", "权限", "认证"},
	{"reliability", "availability", "fault", "recovery", "可靠性", "可用性", "容错"},
	{"observability", "logging", "metrics", "tracing", "monitoring", "可观测", "日志", "指标", "监控"},
}

func checkNonFunctional(a artifactSet) checkResult {
	if a.spec == "" {
		return fileMissing("spec.md")
	}

	covered := 0
	missing := []string{}
	for _, g := range nfrGroups {
		if hasKeyword(a.spec, g) {
			covered++
		} else {
			missing = append(missing, g[0])
		}
	}

	if covered >= 3 {
		return checkResult{status: statusPass}
	}
	if covered >= 2 {
		return checkResult{
			status:  statusWarn,
			message: fmt.Sprintf("only %d/4 NFR dimensions covered; consider adding: %s", covered, strings.Join(missing, ", ")),
		}
	}
	return checkResult{
		status:  statusFail,
		message: fmt.Sprintf("only %d/4 NFR dimensions covered (need >= 2): performance, security, reliability, observability", covered),
	}
}

// ---- check 6: error-contract ----
// Error/failure paths should describe user-visible behavior.

var errorKeywords = []string{
	"error", "failure", "exception", "timeout", "错误", "失败", "异常", "超时", "断线", "断开",
}

var userVisibleKeywords = []string{
	"user visible", "user-visible", "display", "show", "notification", "toast",
	"用户可见", "显示", "通知", "横幅", "提示", "reconnecting", "重连",
}

func checkErrorContract(a artifactSet) checkResult {
	if a.spec == "" {
		return fileMissing("spec.md")
	}

	// find sections about errors/failures
	var errorSections []string
	for _, kw := range []string{"error", "failure", "exception", "edge case", "错误", "失败", "异常", "边界"} {
		errorSections = append(errorSections, findSections(a.spec, kw)...)
	}

	if len(errorSections) == 0 {
		// no explicit error sections; try to find error mentions in the body
		if !hasKeyword(a.spec, errorKeywords) {
			return checkResult{
				status:  statusWarn,
				message: "no error/failure paths detected in spec",
			}
		}
		errorSections = []string{a.spec}
	}

	// for each error section, check if user-visible behavior is described
	described := 0
	total := 0
	for _, sec := range errorSections {
		if hasKeyword(sec, errorKeywords) {
			total++
			if hasKeyword(sec, userVisibleKeywords) {
				described++
			}
		}
	}

	if total == 0 {
		return checkResult{status: statusWarn, message: "no error paths detected"}
	}
	if described >= total || total <= 2 {
		return checkResult{status: statusPass}
	}

	return checkResult{
		status:  statusWarn,
		message: fmt.Sprintf("%d/%d error paths mention user-visible behavior; consider adding 'user visible' / '用户可见' descriptions", described, total),
	}
}

// ---- check 7: config-effective-when ----
// Config items should declare when changes take effect.

var configKeywords = []string{
	"config", "configuration", "setting", "option", "配置", "设置",
}

var effectiveWhenKeywords = []string{
	"effective when", "effective immediately", "生效时机", "即时生效", "下次", "next session",
	"after restart", "动态", "runtime",
}

func checkConfigEffectiveWhen(a artifactSet) checkResult {
	combined := a.spec + "\n" + a.context
	if strings.TrimSpace(combined) == "" {
		return checkResult{status: statusWarn, message: "no spec or context to check config declarations"}
	}

	if !hasKeyword(combined, configKeywords) {
		return checkResult{status: statusWarn, message: "no configuration items detected in spec/context"}
	}

	// check the full combined content for effective-when language (not just section bodies)
	if hasKeyword(combined, effectiveWhenKeywords) {
		return checkResult{status: statusPass}
	}

	return checkResult{
		status:  statusWarn,
		message: "config items found but no effective-when / 生效时机 declarations",
	}
}

// ---- check 8: test-strategy ----
// Capabilities should have test strategy notes.

var testStrategyKeywords = []string{
	"test strategy", "test note", "测试策略", "测试注记", "platform test",
	"integration test", "unit test", "e2e test", "平台测试",
}

func checkTestStrategy(a artifactSet) checkResult {
	if a.spec == "" {
		return fileMissing("spec.md")
	}

	// find capability sections
	capSections := findSections(a.spec, "capability")
	capSections = append(capSections, findSections(a.spec, "能力")...)

	if len(capSections) == 0 {
		return checkResult{
			status:  statusWarn,
			message: "no capability sections found; cannot verify test strategy notes",
		}
	}

	// check if any capability section mentions test strategy
	mentioned := 0
	for _, sec := range capSections {
		if hasKeyword(sec, testStrategyKeywords) {
			mentioned++
		}
	}

	if mentioned > 0 {
		return checkResult{
			status:  statusPass,
			message: fmt.Sprintf("test strategy mentioned in %d/%d capability sections", mentioned, len(capSections)),
		}
	}

	// also check globally in spec for test strategy
	if hasKeyword(a.spec, testStrategyKeywords) {
		return checkResult{status: statusPass, message: "test strategy mentioned in spec"}
	}

	return checkResult{
		status:  statusWarn,
		message: "capabilities defined but no test strategy notes found per capability",
	}
}
