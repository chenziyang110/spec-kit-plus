package main

import (
	"encoding/json"
	"fmt"
	"os"
)

var learningMetricTotals = []string{"assessed", "captured", "candidate_captured", "confirmed", "promoted", "deferred", "ignored"}
var learningMetricDecisions = []string{"capture-safe", "capture-sanitized", "defer", "ignore"}
var learningMetricValueTiers = []string{"high", "medium", "low"}
var learningMetricRiskTiers = []string{"none", "moderate", "high"}
var learningMetricReasonCodes = []string{"explicit_capture", "workflow_gap", "user_correction", "reusable_constraint", "near_miss", "repeated_occurrence", "tooling_trap", "recovery_path", "high_signal", "routine_outcome"}
var learningMetricLabels = []string{"credential", "email", "private_key", "machine_path", "personal_identifier", "business_identifier", "organization_sensitive"}

func emptyLearningMetricBucket() map[string]any {
	return map[string]any{
		"totals":           zeroLearningMetricMap(learningMetricTotals),
		"decisions":        zeroLearningMetricMap(learningMetricDecisions),
		"value_tiers":      zeroLearningMetricMap(learningMetricValueTiers),
		"risk_tiers":       zeroLearningMetricMap(learningMetricRiskTiers),
		"reason_codes":     zeroLearningMetricMap(learningMetricReasonCodes),
		"redaction_labels": zeroLearningMetricMap(learningMetricLabels),
	}
}

func zeroLearningMetricMap(keys []string) map[string]any {
	values := map[string]any{}
	for _, key := range keys {
		values[key] = 0
	}
	return values
}

func emptyLearningMetricsState() map[string]any {
	return map[string]any{"schema_version": 1, "global": emptyLearningMetricBucket(), "by_command": map[string]any{}}
}

func readLearningMetricsState(path string) (map[string]any, error) {
	raw, err := os.ReadFile(path)
	if os.IsNotExist(err) {
		return emptyLearningMetricsState(), nil
	}
	if err != nil {
		return nil, err
	}
	var payload map[string]any
	if err := json.Unmarshal(raw, &payload); err != nil {
		return nil, fmt.Errorf("Learning metrics state is malformed")
	}
	clean := emptyLearningMetricsState()
	clean["global"] = sanitizeLearningMetricBucket(mapStringAny(payload["global"]))
	byCommand := map[string]any{}
	for rawCommand, rawBucket := range mapStringAny(payload["by_command"]) {
		command, err := normalizeLearningCommand(rawCommand)
		if err == nil && knownLearningCommand(command) {
			byCommand[command] = sanitizeLearningMetricBucket(mapStringAny(rawBucket))
		}
	}
	clean["by_command"] = byCommand
	return clean, nil
}

func sanitizeLearningMetricBucket(raw map[string]any) map[string]any {
	clean := emptyLearningMetricBucket()
	groups := []struct {
		name string
		keys []string
	}{
		{"totals", learningMetricTotals}, {"decisions", learningMetricDecisions}, {"value_tiers", learningMetricValueTiers},
		{"risk_tiers", learningMetricRiskTiers}, {"reason_codes", learningMetricReasonCodes}, {"redaction_labels", learningMetricLabels},
	}
	for _, group := range groups {
		target := mapStringAny(clean[group.name])
		source := mapStringAny(raw[group.name])
		for _, key := range group.keys {
			if value := intFromAny(source[key]); value > 0 {
				target[key] = value
			}
		}
	}
	return clean
}

func (service learningService) recordLearningAssessment(paths learningPaths, entry map[string]any, captured, confirmed bool) error {
	state, err := readLearningMetricsState(paths.metrics)
	if err != nil {
		return err
	}
	update := func(bucket map[string]any) {
		incrementLearningMetric(bucket, "totals", "assessed")
		decision := stringFromAny(entry["assessment_decision"])
		incrementLearningMetric(bucket, "decisions", decision)
		incrementLearningMetric(bucket, "value_tiers", stringFromAny(entry["learning_value_tier"]))
		incrementLearningMetric(bucket, "risk_tiers", stringFromAny(entry["sensitivity_risk_tier"]))
		for _, reason := range canonicalLearningReasonCodes(anyStringSlice(entry["learning_value_reason_codes"])) {
			incrementLearningMetric(bucket, "reason_codes", reason)
		}
		for _, label := range canonicalLearningLabels(anyStringSlice(entry["redaction_labels"])) {
			incrementLearningMetric(bucket, "redaction_labels", label)
		}
		switch decision {
		case "defer":
			incrementLearningMetric(bucket, "totals", "deferred")
		case "ignore":
			incrementLearningMetric(bucket, "totals", "ignored")
		}
		if captured {
			incrementLearningMetric(bucket, "totals", "captured")
			if confirmed {
				incrementLearningMetric(bucket, "totals", "confirmed")
			} else {
				incrementLearningMetric(bucket, "totals", "candidate_captured")
			}
		}
	}
	update(mapStringAny(state["global"]))
	if command := stringFromAny(entry["source_command"]); knownLearningCommand(command) {
		byCommand := mapStringAny(state["by_command"])
		bucket := sanitizeLearningMetricBucket(mapStringAny(byCommand[command]))
		update(bucket)
		byCommand[command] = bucket
	}
	return writeLearningMetricsState(paths.metrics, state)
}

func (service learningService) recordLearningPromotion(paths learningPaths, entry map[string]any, event string) error {
	state, err := readLearningMetricsState(paths.metrics)
	if err != nil {
		return err
	}
	update := func(bucket map[string]any) {
		incrementLearningMetric(bucket, "totals", event)
	}
	update(mapStringAny(state["global"]))
	if command := stringFromAny(entry["source_command"]); knownLearningCommand(command) {
		byCommand := mapStringAny(state["by_command"])
		bucket := sanitizeLearningMetricBucket(mapStringAny(byCommand[command]))
		update(bucket)
		byCommand[command] = bucket
	}
	return writeLearningMetricsState(paths.metrics, state)
}

func incrementLearningMetric(bucket map[string]any, group, key string) {
	values := mapStringAny(bucket[group])
	if _, exists := values[key]; exists {
		values[key] = intFromAny(values[key]) + 1
	}
}

func writeLearningMetricsState(path string, state map[string]any) error {
	raw, _ := json.MarshalIndent(state, "", "  ")
	return writeLearningText(path, string(raw)+"\n")
}

func (service learningService) learningMetrics(commandName string) (map[string]any, error) {
	policy, warnings, _ := service.loadLearningPolicy(false)
	paths, err := service.paths()
	if err != nil {
		return nil, err
	}
	state, err := readLearningMetricsState(paths.metrics)
	if err != nil {
		return nil, err
	}
	var command any
	filter := ""
	bucket := mapStringAny(state["global"])
	if commandName != "" {
		normalized, normalizeErr := normalizeLearningCommand(commandName)
		if normalizeErr != nil {
			return nil, normalizeErr
		}
		normalized = safeLearningCommandProjection(normalized, policy)
		command = safeLearningCommandProjection(normalized, policy)
		filter = normalized
		if knownLearningCommand(normalized) {
			bucket = sanitizeLearningMetricBucket(mapStringAny(mapStringAny(state["by_command"])[normalized]))
		} else {
			bucket = emptyLearningMetricBucket()
		}
	}
	items, _, err := service.readLearningReviewItems(paths, policy)
	if err != nil {
		return nil, err
	}
	ageBuckets := learningReviewAgeBuckets(items, filter)
	confirmed := intFromAny(mapStringAny(bucket["totals"])["confirmed"])
	captured := intFromAny(mapStringAny(bucket["totals"])["captured"])
	rate := float64(0)
	if captured > 0 {
		rate = float64(confirmed) / float64(captured)
		if rate > 1 {
			rate = 1
		}
	}
	return map[string]any{
		"schema_version": 1, "read_only": true, "command": command, "metrics": bucket,
		"age_buckets": ageBuckets, "derived": map[string]any{"confirmation_rate": rate}, "warnings": stringsToAny(warnings),
	}, nil
}

func knownLearningCommand(command string) bool {
	for _, known := range knownLearningCommands {
		if command == known {
			return true
		}
	}
	return false
}

func safeLearningCommandProjection(command string, policy learningPolicy) string {
	redacted := redactLearningTextWithPolicy(command, policy).text
	if redacted != command {
		return "sp-other"
	}
	return command
}
