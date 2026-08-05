package main

import (
	"encoding/json"
	"fmt"
	"os"
	"sort"
	"strings"
	"time"
)

var learningReviewDecisions = map[string]bool{
	"none": true, "captured": true, "auto-captured": true, "deferred": true, "manual-capture-needed": true,
}

func (service learningService) review(commandName, decision, rationale, recurrenceKey string) (map[string]any, error) {
	policy, _, err := service.loadLearningPolicy(true)
	if err != nil {
		return nil, err
	}
	command, err := normalizeLearningCommand(commandName)
	if err != nil {
		return nil, err
	}
	command = safeLearningCommandProjection(command, policy)
	decision = strings.ToLower(strings.TrimSpace(decision))
	if !learningReviewDecisions[decision] {
		return nil, fmt.Errorf("learning review decision is unsupported")
	}
	rationaleResult := redactLearningTextWithPolicy(strings.TrimSpace(rationale), policy)
	rationale = rationaleResult.text
	if (decision == "deferred" || decision == "manual-capture-needed") && rationale == "" {
		return nil, fmt.Errorf("learning review decision %q requires a rationale", decision)
	}
	key := ""
	if strings.TrimSpace(recurrenceKey) != "" {
		key = sanitizeLearningRecurrenceKeyWithPolicy(recurrenceKey, policy).text
	}
	return service.withLock(func(paths learningPaths) (map[string]any, error) {
		items, _, err := service.readLearningReviewItems(paths, policy)
		if err != nil {
			return nil, err
		}
		pending := matchingLearningReviewItems(items, command, key)
		switch decision {
		case "none":
			if len(pending) > 0 {
				return nil, fmt.Errorf("pending deferred Learning must be resolved by a matching durable capture before decision none")
			}
			return map[string]any{"status": "none", "command": safeLearningCommandProjection(command, policy), "decision": decision, "rationale": rationale}, nil
		case "deferred", "manual-capture-needed":
			entry := map[string]any{"source_command": command, "recurrence_key": key}
			if err := service.upsertDeferredLearningReview(paths, entry, decision, rationale, policy); err != nil {
				return nil, err
			}
			return map[string]any{"status": decision, "command": safeLearningCommandProjection(command, policy), "decision": decision, "recurrence_key": key, "rationale": rationale}, nil
		case "captured", "auto-captured":
			if len(pending) == 0 {
				if !service.hasMatchingPersistedLearning(paths, command, key, policy, "") {
					return nil, fmt.Errorf("learning review claimed capture without a matching durable candidate, confirmed Learning, or project rule")
				}
			} else {
				for _, item := range pending {
					createdAt := stringFromAny(item["created_at"])
					effectiveKey := key
					if effectiveKey == "" {
						effectiveKey = stringFromAny(item["recurrence_key"])
					}
					if createdAt == "" || !service.hasMatchingPersistedLearning(paths, command, effectiveKey, policy, createdAt) {
						return nil, fmt.Errorf("learning review claimed capture without a matching durable Learning recorded after the deferred review")
					}
				}
			}
			if err := service.clearMatchingLearningReviews(paths, command, key, policy); err != nil {
				return nil, err
			}
			return map[string]any{"status": decision, "command": safeLearningCommandProjection(command, policy), "decision": decision, "recurrence_key": key}, nil
		default:
			return nil, fmt.Errorf("learning review decision is unsupported")
		}
	})
}

func (service learningService) upsertDeferredLearningReview(paths learningPaths, entry map[string]any, decision, rationale string, policy learningPolicy) error {
	items, _, err := service.readLearningReviewItems(paths, policy)
	if err != nil {
		return err
	}
	command := stringFromAny(entry["source_command"])
	key := stringFromAny(entry["recurrence_key"])
	if command == "" {
		return fmt.Errorf("deferred Learning review requires a command")
	}
	rationale = redactLearningTextWithPolicy(rationale, policy).text
	now := time.Now().UTC().Truncate(time.Second)
	updated := map[string]any{
		"command": command, "decision": decision, "rationale": rationale, "recurrence_key": key,
		"created_at": now.Format(time.RFC3339), "updated_at": now.Format(time.RFC3339),
		"review_after": now.AddDate(0, 0, policy.deferredReviewDays).Format(time.RFC3339),
	}
	found := false
	for index, item := range items {
		if stringFromAny(item["command"]) == command && stringFromAny(item["recurrence_key"]) == key {
			updated["created_at"] = firstString(stringFromAny(item["created_at"]), stringFromAny(updated["created_at"]))
			updated["review_after"] = firstString(stringFromAny(item["review_after"]), stringFromAny(updated["review_after"]))
			items[index] = updated
			found = true
			break
		}
	}
	if !found {
		canonicalItems, _, canonicalErr := readCanonicalLearningReviewState(paths.reviewState, policy)
		if canonicalErr != nil {
			return canonicalErr
		}
		canonicalCommand := false
		for _, item := range canonicalItems {
			if stringFromAny(item["command"]) == command {
				canonicalCommand = true
				break
			}
		}
		if !canonicalCommand {
			filtered := make([]map[string]any, 0, len(items))
			for _, item := range items {
				if stringFromAny(item["command"]) == command {
					updated["created_at"] = firstString(stringFromAny(item["created_at"]), stringFromAny(updated["created_at"]))
					updated["review_after"] = firstString(stringFromAny(item["review_after"]), stringFromAny(updated["review_after"]))
					continue
				}
				filtered = append(filtered, item)
			}
			items = filtered
		}
	}
	if !found {
		items = append(items, updated)
	}
	if err := writeLearningReviewState(paths.reviewState, items); err != nil {
		return err
	}
	return service.removeLegacyLearningReviewForCommand(paths, command, policy)
}

func (service learningService) removeLegacyLearningReviewForCommand(paths learningPaths, command string, policy learningPolicy) error {
	path := strings.TrimSuffix(paths.reviewState, "review-state.json") + "signal-state.json"
	raw, err := os.ReadFile(path)
	if os.IsNotExist(err) {
		return nil
	}
	if err != nil {
		return err
	}
	var payload map[string]any
	if json.Unmarshal(raw, &payload) != nil {
		return nil
	}
	changed := false
	for rawCommand, rawState := range payload {
		normalized, normalizeErr := normalizeLearningCommand(rawCommand)
		normalized = safeLearningCommandProjection(normalized, policy)
		if normalizeErr != nil || normalized != command {
			continue
		}
		state := mapStringAny(rawState)
		if _, exists := state["learning_review"]; !exists {
			continue
		}
		delete(state, "learning_review")
		payload[rawCommand] = state
		changed = true
	}
	if !changed {
		return nil
	}
	clean := sanitizeLegacySignalStateForWrite(payload, policy)
	serialized, _ := json.MarshalIndent(clean, "", "  ")
	return writeLearningText(path, string(serialized)+"\n")
}

func (service learningService) clearMatchingLearningReviews(paths learningPaths, command, recurrenceKey string, policy learningPolicy) error {
	items, _, err := service.readLearningReviewItems(paths, policy)
	if err != nil {
		return err
	}
	filtered := make([]map[string]any, 0, len(items))
	changed := false
	for _, item := range items {
		createdAt := stringFromAny(item["created_at"])
		effectiveKey := recurrenceKey
		if effectiveKey == "" {
			effectiveKey = stringFromAny(item["recurrence_key"])
		}
		if learningReviewMatches(item, command, recurrenceKey) && createdAt != "" && service.hasMatchingPersistedLearning(paths, command, effectiveKey, policy, createdAt) {
			changed = true
			continue
		}
		filtered = append(filtered, item)
	}
	legacyChanged, err := service.clearLegacyLearningReview(paths, command, recurrenceKey, policy)
	if err != nil {
		return err
	}
	if changed || legacyChanged {
		return writeLearningReviewState(paths.reviewState, filtered)
	}
	return nil
}

func (service learningService) readLearningReviewItems(paths learningPaths, policy learningPolicy) ([]map[string]any, bool, error) {
	items, exists, err := readCanonicalLearningReviewState(paths.reviewState, policy)
	if err != nil {
		return nil, exists, err
	}
	byKey := map[string]map[string]any{}
	canonicalCommands := map[string]bool{}
	for _, item := range items {
		byKey[learningReviewItemKey(item)] = item
		canonicalCommands[stringFromAny(item["command"])] = true
	}
	for _, item := range readLegacyLearningReviews(paths, policy) {
		if !canonicalCommands[stringFromAny(item["command"])] {
			byKey[learningReviewItemKey(item)] = item
		}
	}
	merged := make([]map[string]any, 0, len(byKey))
	for _, item := range byKey {
		merged = append(merged, item)
	}
	sortLearningReviewItems(merged)
	return merged, exists, nil
}

func readCanonicalLearningReviewState(path string, policy learningPolicy) ([]map[string]any, bool, error) {
	raw, err := os.ReadFile(path)
	if os.IsNotExist(err) {
		return []map[string]any{}, false, nil
	}
	if err != nil {
		return nil, true, err
	}
	var payload map[string]any
	if err := json.Unmarshal(raw, &payload); err != nil {
		return nil, true, fmt.Errorf("Learning review state is malformed")
	}
	items := []map[string]any{}
	for _, rawItem := range anyMapSlice(payload["items"]) {
		if item := sanitizeLearningReviewItem(rawItem, policy); item != nil {
			items = append(items, item)
		}
	}
	return items, true, nil
}

func readLegacyLearningReviews(paths learningPaths, policy learningPolicy) []map[string]any {
	path := strings.TrimSuffix(paths.reviewState, "review-state.json") + "signal-state.json"
	raw, err := os.ReadFile(path)
	if err != nil {
		return nil
	}
	var payload map[string]any
	if json.Unmarshal(raw, &payload) != nil {
		return nil
	}
	items := []map[string]any{}
	for rawCommand, rawState := range payload {
		command, err := normalizeLearningCommand(rawCommand)
		if err != nil {
			continue
		}
		command = safeLearningCommandProjection(command, policy)
		review := mapStringAny(mapStringAny(rawState)["learning_review"])
		decision := strings.ToLower(stringFromAny(review["decision"]))
		rationale := redactLearningTextWithPolicy(stringFromAny(review["rationale"]), policy).text
		if (decision != "deferred" && decision != "manual-capture-needed") || rationale == "" {
			continue
		}
		created := validLearningTimestamp(firstString(stringFromAny(review["deferred_at"]), stringFromAny(mapStringAny(rawState)["observed_at"])))
		reviewAfter := ""
		if parsed, err := time.Parse(time.RFC3339, created); err == nil {
			reviewAfter = parsed.AddDate(0, 0, policy.deferredReviewDays).Format(time.RFC3339)
		}
		items = append(items, map[string]any{
			"command": command, "decision": decision, "rationale": rationale, "recurrence_key": "",
			"created_at": created, "updated_at": created, "review_after": reviewAfter,
		})
	}
	return items
}

func sanitizeLearningReviewItem(raw map[string]any, policy learningPolicy) map[string]any {
	command, err := normalizeLearningCommand(stringFromAny(raw["command"]))
	if err != nil {
		return nil
	}
	command = safeLearningCommandProjection(command, policy)
	decision := strings.ToLower(stringFromAny(raw["decision"]))
	rationale := redactLearningTextWithPolicy(stringFromAny(raw["rationale"]), policy).text
	if (decision != "deferred" && decision != "manual-capture-needed") || rationale == "" {
		return nil
	}
	return map[string]any{
		"command": command, "decision": decision, "rationale": rationale,
		"recurrence_key": sanitizeOptionalLearningReviewKey(stringFromAny(raw["recurrence_key"]), policy),
		"created_at":     validLearningTimestamp(stringFromAny(raw["created_at"])),
		"updated_at":     validLearningTimestamp(stringFromAny(raw["updated_at"])),
		"review_after":   validLearningTimestamp(stringFromAny(raw["review_after"])),
	}
}

func (service learningService) clearLegacyLearningReview(paths learningPaths, command, recurrenceKey string, policy learningPolicy) (bool, error) {
	path := strings.TrimSuffix(paths.reviewState, "review-state.json") + "signal-state.json"
	raw, err := os.ReadFile(path)
	if os.IsNotExist(err) {
		return false, nil
	}
	if err != nil {
		return false, err
	}
	var payload map[string]any
	if json.Unmarshal(raw, &payload) != nil {
		return false, nil
	}
	changed := false
	for rawCommand, rawState := range payload {
		normalized, err := normalizeLearningCommand(rawCommand)
		normalized = safeLearningCommandProjection(normalized, policy)
		if err != nil || normalized != command {
			continue
		}
		state := mapStringAny(rawState)
		review := mapStringAny(state["learning_review"])
		if len(review) == 0 {
			continue
		}
		legacyKey := sanitizeOptionalLearningReviewKey(stringFromAny(review["recurrence_key"]), policy)
		if recurrenceKey != "" && legacyKey != "" && legacyKey != recurrenceKey {
			continue
		}
		deferredAt := validLearningTimestamp(firstString(stringFromAny(review["deferred_at"]), stringFromAny(state["observed_at"])))
		effectiveKey := recurrenceKey
		if effectiveKey == "" {
			effectiveKey = legacyKey
		}
		if deferredAt == "" || !service.hasMatchingPersistedLearning(paths, command, effectiveKey, policy, deferredAt) {
			continue
		}
		delete(state, "learning_review")
		payload[rawCommand] = state
		changed = true
	}
	if !changed {
		return false, nil
	}
	clean := sanitizeLegacySignalStateForWrite(payload, policy)
	serialized, _ := json.MarshalIndent(clean, "", "  ")
	return true, writeLearningText(path, string(serialized)+"\n")
}

func sanitizeLegacySignalStateForWrite(payload map[string]any, policy learningPolicy) map[string]any {
	clean := map[string]any{}
	for rawCommand, rawState := range payload {
		command, err := normalizeLearningCommand(rawCommand)
		if err != nil {
			continue
		}
		command = safeLearningCommandProjection(command, policy)
		labels := map[string]bool{}
		state := map[string]any{"command": command}
		for _, field := range []string{"pain_score"} {
			state[field] = intFromAny(mapStringAny(rawState)[field])
		}
		factorKeys := []string{
			"retry_attempts", "hypothesis_changes", "validation_failures", "artifact_rewrites", "command_failures",
			"user_corrections", "route_changes", "scope_changes", "false_starts", "hidden_dependencies", "trigger_signals",
		}
		factors := map[string]any{}
		for _, key := range factorKeys {
			if _, exists := mapStringAny(mapStringAny(rawState)["factors"])[key]; exists {
				factors[key] = intFromAny(mapStringAny(mapStringAny(rawState)["factors"])[key])
			}
		}
		state["factors"] = factors
		for _, field := range []string{"observed_at", "last_observed_at"} {
			state[field] = validLearningTimestamp(stringFromAny(mapStringAny(rawState)[field]))
		}
		for _, field := range []string{"false_starts", "hidden_dependencies", "trigger_signals"} {
			values := []string{}
			for _, value := range anyStringSlice(mapStringAny(rawState)[field]) {
				redacted := redactLearningTextWithPolicy(value, policy)
				values = append(values, redacted.text)
				mergeLearningPolicyLabels(labels, redacted.labels)
			}
			state[field] = stringsToAny(uniqueSortedTrimmed(values))
		}
		state["content_safety"] = map[string]any{"sensitivity": learningSensitivityForLabels(labels), "redaction_labels": stringsToAny(sortedLearningLabels(labels))}
		clean[strings.TrimPrefix(command, "sp-")] = state
	}
	return clean
}

func (service learningService) hasMatchingPersistedLearning(paths learningPaths, command, recurrenceKey string, policy learningPolicy, notBefore string) bool {
	threshold, thresholdErr := time.Parse(time.RFC3339, notBefore)
	if notBefore != "" && thresholdErr != nil {
		return false
	}
	for _, path := range []string{paths.candidates, paths.confirmedLearnings, paths.projectRules} {
		for _, entry := range sanitizeLearningEntriesWithPolicy(readLearningEntriesIfPresent(path), policy) {
			if recurrenceKey != "" && stringFromAny(entry["recurrence_key"]) != recurrenceKey {
				continue
			}
			if stringFromAny(entry["source_command"]) == command || learningContainsString(anyStringSlice(entry["applies_to"]), command) {
				if thresholdErr == nil {
					seen, err := time.Parse(time.RFC3339, stringFromAny(entry["last_seen"]))
					if err != nil || seen.Before(threshold) {
						continue
					}
				}
				return true
			}
		}
	}
	return false
}

func (service learningService) learningStatus(commandName string) (map[string]any, error) {
	policy, warnings, _ := service.loadLearningPolicy(false)
	paths, err := service.paths()
	if err != nil {
		return nil, err
	}
	filter := ""
	var command any
	if strings.TrimSpace(commandName) != "" {
		filter, err = normalizeLearningCommand(commandName)
		if err != nil {
			return nil, err
		}
		filter = safeLearningCommandProjection(filter, policy)
		command = safeLearningCommandProjection(filter, policy)
	}
	items, _, err := service.readLearningReviewItems(paths, policy)
	if err != nil {
		return nil, err
	}
	pending := 0
	overdue := 0
	for _, item := range items {
		if filter != "" && stringFromAny(item["command"]) != filter {
			continue
		}
		due, ageDays := learningReviewDue(item, time.Now().UTC())
		_ = ageDays
		pending++
		if due {
			overdue++
		}
	}
	return map[string]any{
		"schema_version": 1, "read_only": true, "command": command, "pending": pending, "overdue": overdue,
		"age_buckets": learningReviewAgeBuckets(items, filter), "warnings": stringsToAny(warnings),
	}, nil
}

func learningReviewAgeBuckets(items []map[string]any, command string) map[string]any {
	buckets := map[string]any{"not_due": 0, "due_0_7_days": 0, "due_8_30_days": 0, "due_over_30_days": 0}
	now := time.Now().UTC()
	for _, item := range items {
		if command != "" && stringFromAny(item["command"]) != command {
			continue
		}
		due, _ := learningReviewDue(item, now)
		if !due {
			buckets["not_due"] = intFromAny(buckets["not_due"]) + 1
			continue
		}
		reviewAfter, _ := time.Parse(time.RFC3339, stringFromAny(item["review_after"]))
		days := int(now.Sub(reviewAfter).Hours() / 24)
		switch {
		case days <= 7:
			buckets["due_0_7_days"] = intFromAny(buckets["due_0_7_days"]) + 1
		case days <= 30:
			buckets["due_8_30_days"] = intFromAny(buckets["due_8_30_days"]) + 1
		default:
			buckets["due_over_30_days"] = intFromAny(buckets["due_over_30_days"]) + 1
		}
	}
	return buckets
}

func learningReviewDue(item map[string]any, now time.Time) (bool, int) {
	created, createdErr := time.Parse(time.RFC3339, stringFromAny(item["created_at"]))
	reviewAfter, reviewErr := time.Parse(time.RFC3339, stringFromAny(item["review_after"]))
	ageDays := 0
	if createdErr == nil && now.After(created) {
		ageDays = int(now.Sub(created).Hours() / 24)
	}
	return reviewErr == nil && !now.Before(reviewAfter), ageDays
}

func writeLearningReviewState(path string, items []map[string]any) error {
	sortLearningReviewItems(items)
	raw, _ := json.MarshalIndent(map[string]any{"schema_version": 1, "items": mapsToAnyLearning(items)}, "", "  ")
	return writeLearningText(path, string(raw)+"\n")
}

func sortLearningReviewItems(items []map[string]any) {
	sort.Slice(items, func(i, j int) bool { return learningReviewItemKey(items[i]) < learningReviewItemKey(items[j]) })
}

func learningReviewItemKey(item map[string]any) string {
	return stringFromAny(item["command"]) + "\x00" + stringFromAny(item["recurrence_key"])
}

func matchingLearningReviewItems(items []map[string]any, command, recurrenceKey string) []map[string]any {
	matched := []map[string]any{}
	for _, item := range items {
		if learningReviewMatches(item, command, recurrenceKey) {
			matched = append(matched, item)
		}
	}
	return matched
}

func learningReviewMatches(item map[string]any, command, recurrenceKey string) bool {
	if stringFromAny(item["command"]) != command {
		return false
	}
	itemKey := stringFromAny(item["recurrence_key"])
	return recurrenceKey == "" || itemKey == "" || itemKey == recurrenceKey
}

func sanitizeOptionalLearningReviewKey(value string, policy learningPolicy) string {
	if strings.TrimSpace(value) == "" {
		return ""
	}
	return sanitizeLearningRecurrenceKeyWithPolicy(value, policy).text
}

func validLearningTimestamp(value string) string {
	parsed, err := time.Parse(time.RFC3339, strings.TrimSpace(value))
	if err != nil {
		return ""
	}
	return parsed.UTC().Truncate(time.Second).Format(time.RFC3339)
}

func anyMapSlice(value any) []map[string]any {
	result := []map[string]any{}
	items, ok := value.([]any)
	if !ok {
		return result
	}
	for _, item := range items {
		if mapped := mapStringAny(item); len(mapped) > 0 {
			result = append(result, mapped)
		}
	}
	return result
}

func learningSensitivityForLabels(labels map[string]bool) string {
	if len(labels) > 0 {
		return "sanitized"
	}
	return "safe"
}
