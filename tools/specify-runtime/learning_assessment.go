package main

import (
	"regexp"
	"strings"
	"unicode"
)

var learningValueReasonCodes = map[string]bool{
	"explicit_capture": true, "workflow_gap": true, "user_correction": true, "reusable_constraint": true,
	"near_miss": true, "repeated_occurrence": true, "tooling_trap": true, "recovery_path": true,
	"high_signal": true, "routine_outcome": true,
}

func applyLearningAssessment(entry map[string]any, source string) map[string]any {
	result := cloneLearningMap(entry)
	tier, reasons := learningValueAssessment(result, source)
	sensitivity := firstString(stringFromAny(result["sensitivity"]), "safe")
	labels := anyStringSlice(result["redaction_labels"])
	risk := learningRiskTier(labels)
	decision, decisionReason := "capture-safe", "safe_content"
	if tier == "low" {
		decision, decisionReason = "ignore", "routine_outcome"
	} else if sensitivity == "sanitized" || len(labels) > 0 {
		if hasReusableLearningSemantic(result) {
			decision, decisionReason = "capture-sanitized", "valuable_after_abstraction"
		} else {
			decision, decisionReason = "defer", "sensitive_without_reusable_abstraction"
		}
	}
	result["learning_value_tier"] = tier
	result["learning_value_reason_codes"] = stringsToAny(reasons)
	result["sensitivity_risk_tier"] = risk
	result["assessment_decision"] = decision
	result["assessment_reason"] = decisionReason
	return result
}

func learningValueAssessment(entry map[string]any, source string) (string, []string) {
	typ := stringFromAny(entry["learning_type"])
	signals := anyStringSlice(entry["trigger_signals"])
	if source == "" {
		if learningContainsString(anyStringSlice(entry["learning_value_reason_codes"]), "explicit_capture") {
			source = "manual"
		} else {
			source = "auto"
		}
	}
	reasons := []string{}
	highValue, mediumValue := false, false
	if source == "manual" {
		highValue = true
		reasons = append(reasons, "explicit_capture")
		if code := canonicalLearningTypeReason(typ); code != "" {
			reasons = append(reasons, code)
		}
	}
	if learningContainsFold(signals, "user_correction") {
		highValue = true
		reasons = append(reasons, "user_correction")
	}
	if typ == "near_miss" || learningContainsFold(signals, "near_miss") {
		highValue = true
		reasons = append(reasons, "near_miss")
	}
	if typ == "project_constraint" || learningContainsFold(signals, "reusable_constraint") {
		highValue = true
		reasons = append(reasons, "reusable_constraint")
	}
	if intFromAny(entry["occurrence_count"]) >= 2 {
		highValue = true
		reasons = append(reasons, "repeated_occurrence")
		if code := canonicalLearningTypeReason(typ); code != "" {
			reasons = append(reasons, code)
		}
	}
	if !highValue {
		switch typ {
		case "recovery_path":
			mediumValue = true
			reasons = append(reasons, "recovery_path")
		case "workflow_gap":
			mediumValue = true
			reasons = append(reasons, "workflow_gap")
		case "tooling_trap":
			mediumValue = true
			reasons = append(reasons, "tooling_trap")
		}
		if learningContainsFold(signals, "recovery_completed") {
			mediumValue = true
			reasons = append(reasons, "recovery_path")
		}
		if !mediumValue && stringFromAny(entry["signal_strength"]) != "low" {
			mediumValue = true
			reasons = append(reasons, "high_signal")
		}
	}
	tier := "low"
	if highValue {
		tier = "high"
	} else if mediumValue {
		tier = "medium"
	}
	if len(reasons) == 0 {
		reasons = []string{"routine_outcome"}
	}
	return tier, canonicalLearningReasonCodes(reasons)
}

func canonicalLearningTypeReason(learningType string) string {
	switch learningType {
	case "workflow_gap":
		return "workflow_gap"
	case "project_constraint":
		return "reusable_constraint"
	case "tooling_trap":
		return "tooling_trap"
	case "recovery_path":
		return "recovery_path"
	default:
		return ""
	}
}

func canonicalLearningReasonCodes(values []string) []string {
	result := []string{}
	for _, value := range uniqueSortedTrimmed(values) {
		if learningValueReasonCodes[value] {
			result = append(result, value)
		}
	}
	return result
}

func learningRiskTier(labels []string) string {
	risk := "none"
	for _, label := range labels {
		switch label {
		case "credential", "private_key", "organization_sensitive":
			return "high"
		case "email", "machine_path", "personal_identifier", "business_identifier":
			risk = "moderate"
		}
	}
	return risk
}

func hasReusableLearningSemantic(entry map[string]any) bool {
	if learningSemanticWordCount(stringFromAny(entry["recommended_action"]), 6) >= 3 {
		return true
	}
	combined := strings.Join([]string{
		stringFromAny(entry["summary"]), stringFromAny(entry["evidence"]), stringFromAny(entry["problem"]),
	}, " ")
	return learningSemanticWordCount(combined, 8) >= 4
}

func learningSemanticWordCount(value string, unicodeThreshold int) int {
	markers := regexp.MustCompile(`(?i)\[REDACTED_[A-Z_]+\]|<USER_HOME>`)
	value = markers.ReplaceAllString(value, " ")
	words := regexp.MustCompile(`[\p{L}\p{N}_-]{2,}`).FindAllString(strings.ToLower(value), -1)
	ignored := map[string]bool{
		"secret": true, "password": true, "token": true, "authorization": true, "api_key": true,
		"apikey": true, "email": true, "phone": true, "business": true, "identifier": true,
		"organization": true, "term": true, "user_home": true, "only": true, "value": true,
	}
	seen := map[string]bool{}
	for _, word := range words {
		if !ignored[word] {
			seen[word] = true
		}
	}
	semanticRunes := 0
	for _, character := range value {
		if character > unicode.MaxASCII && (unicode.IsLetter(character) || unicode.IsNumber(character)) {
			semanticRunes++
		}
	}
	if semanticRunes >= unicodeThreshold && len(seen) < 4 {
		return 4
	}
	return len(seen)
}

func learningContainsFold(values []string, expected string) bool {
	for _, value := range values {
		if strings.EqualFold(strings.TrimSpace(value), expected) {
			return true
		}
	}
	return false
}

func learningAssessmentProjection(entry map[string]any) map[string]any {
	tier := stringFromAny(entry["learning_value_tier"])
	rawReasons := anyStringSlice(entry["learning_value_reason_codes"])
	reasons := canonicalLearningReasonCodes(rawReasons)
	sensitivity := firstString(stringFromAny(entry["sensitivity"]), "safe")
	rawLabels := anyStringSlice(entry["redaction_labels"])
	labels := canonicalLearningLabels(rawLabels)
	risk := stringFromAny(entry["sensitivity_risk_tier"])
	decision := stringFromAny(entry["assessment_decision"])
	decisionReason := stringFromAny(entry["assessment_reason"])
	if len(reasons) != len(rawReasons) || len(labels) != len(rawLabels) || !validLearningAssessment(tier, reasons, sensitivity, risk, labels, decision, decisionReason) {
		return nil
	}
	return map[string]any{
		"learning_value": map[string]any{
			"tier":         tier,
			"reason_codes": stringsToAny(reasons),
		},
		"content_safety": map[string]any{
			"sensitivity":      sensitivity,
			"risk_tier":        risk,
			"redaction_labels": stringsToAny(labels),
		},
		"decision":        decision,
		"decision_reason": decisionReason,
	}
}

func validLearningAssessment(tier string, reasons []string, sensitivity, risk string, labels []string, decision, decisionReason string) bool {
	if tier != "high" && tier != "medium" && tier != "low" {
		return false
	}
	if len(reasons) == 0 || len(canonicalLearningReasonCodes(reasons)) != len(reasons) {
		return false
	}
	if sensitivity != "safe" && sensitivity != "sanitized" {
		return false
	}
	if risk != learningRiskTier(labels) {
		return false
	}
	if sensitivity == "safe" && (risk != "none" || len(labels) != 0) {
		return false
	}
	expectedReasons := map[string]string{
		"capture-safe": "safe_content", "capture-sanitized": "valuable_after_abstraction",
		"defer": "sensitive_without_reusable_abstraction", "ignore": "routine_outcome",
	}
	if expectedReasons[decision] != decisionReason {
		return false
	}
	switch decision {
	case "capture-safe":
		return sensitivity == "safe" && risk == "none" && len(labels) == 0 && tier != "low"
	case "capture-sanitized":
		return sensitivity == "sanitized" && len(labels) > 0 && risk != "none" && tier != "low"
	case "defer":
		return sensitivity == "sanitized" && len(labels) > 0 && risk != "none" && tier != "low"
	case "ignore":
		return tier == "low"
	default:
		return false
	}
}

func canonicalLearningLabels(values []string) []string {
	labels := map[string]bool{}
	for _, value := range values {
		if validLearningRedactionLabel(value) {
			labels[value] = true
		}
	}
	return sortedLearningLabels(labels)
}

func learningAssessedCard(entry map[string]any) map[string]any {
	return map[string]any{
		"type": stringFromAny(entry["learning_type"]), "summary": stringFromAny(entry["summary"]),
		"action": stringFromAny(entry["recommended_action"]), "recurrence_key": stringFromAny(entry["recurrence_key"]),
		"assessment": learningAssessmentProjection(entry),
	}
}

func firstNonNilLearningEntry(entries ...map[string]any) map[string]any {
	for _, entry := range entries {
		if entry != nil {
			return entry
		}
	}
	return nil
}

func learningValueRank(tier string) int {
	switch tier {
	case "high":
		return 0
	case "medium":
		return 1
	default:
		return 2
	}
}
