package main

import "sort"

func sortLearningCards(cards []map[string]any) {
	sort.SliceStable(cards, func(i, j int) bool {
		left, right := cards[i], cards[j]
		leftContext, rightContext := mapStringAny(left["context_match"]), mapStringAny(right["context_match"])
		leftExact, _ := leftContext["exact_operation_owner"].(bool)
		rightExact, _ := rightContext["exact_operation_owner"].(bool)
		if leftExact != rightExact {
			return leftExact
		}
		if intFromAny(leftContext["matched_dimensions"]) != intFromAny(rightContext["matched_dimensions"]) {
			return intFromAny(leftContext["matched_dimensions"]) > intFromAny(rightContext["matched_dimensions"])
		}
		if intFromAny(leftContext["matched_values"]) != intFromAny(rightContext["matched_values"]) {
			return intFromAny(leftContext["matched_values"]) > intFromAny(rightContext["matched_values"])
		}
		if learningCardStable(left) != learningCardStable(right) {
			return learningCardStable(left)
		}
		if learningValueRank(stringFromAny(left["_learning_value_tier"])) != learningValueRank(stringFromAny(right["_learning_value_tier"])) {
			return learningValueRank(stringFromAny(left["_learning_value_tier"])) < learningValueRank(stringFromAny(right["_learning_value_tier"]))
		}
		leftSignalOccurrence := signalRank(stringFromAny(left["signal"])) - intFromAny(left["occurrences"])
		rightSignalOccurrence := signalRank(stringFromAny(right["signal"])) - intFromAny(right["occurrences"])
		if leftSignalOccurrence != rightSignalOccurrence {
			return leftSignalOccurrence < rightSignalOccurrence
		}
		return stringFromAny(left["ref"]) < stringFromAny(right["ref"])
	})
}

func learningStartQuotaCards(cards []map[string]any, stableQuota, candidateQuota int) []map[string]any {
	if len(cards) <= stableQuota+candidateQuota {
		return cards
	}
	stable := []map[string]any{}
	candidates := []map[string]any{}
	for _, card := range cards {
		if learningCardStable(card) {
			stable = append(stable, card)
		} else {
			candidates = append(candidates, card)
		}
	}
	selected := []map[string]any{}
	selected = append(selected, takeLearningCards(stable, stableQuota)...)
	selected = append(selected, diverseLearningCards(candidates, candidateQuota)...)
	if len(selected) < stableQuota+candidateQuota {
		used := map[string]bool{}
		for _, card := range selected {
			used[stringFromAny(card["ref"])] = true
		}
		for _, card := range cards {
			if len(selected) >= stableQuota+candidateQuota {
				break
			}
			ref := stringFromAny(card["ref"])
			if !used[ref] {
				selected = append(selected, card)
				used[ref] = true
			}
		}
	}
	sortLearningCards(selected)
	return selected
}

func diverseLearningCards(cards []map[string]any, limit int) []map[string]any {
	if len(cards) <= limit {
		return append([]map[string]any{}, cards...)
	}
	typeCounts := map[string]int{}
	sourceCounts := map[string]int{}
	familyCounts := map[string]int{}
	selected := []map[string]any{}
	used := map[string]bool{}
	trySelect := func(enforceSource, enforceFamily bool) {
		for _, card := range cards {
			if len(selected) >= limit {
				return
			}
			ref := stringFromAny(card["ref"])
			if used[ref] {
				continue
			}
			learningType := stringFromAny(card["type"])
			source := stringFromAny(card["_source_command"])
			family := stringFromAny(card["_recurrence_family"])
			if typeCounts[learningType] >= 2 || (enforceSource && sourceCounts[source] >= 2) || (enforceFamily && familyCounts[family] >= 2) {
				continue
			}
			selected = append(selected, card)
			used[ref] = true
			typeCounts[learningType]++
			sourceCounts[source]++
			familyCounts[family]++
		}
	}
	trySelect(true, true)
	trySelect(false, true)
	for _, card := range cards {
		if len(selected) >= limit {
			break
		}
		if !used[stringFromAny(card["ref"])] {
			selected = append(selected, card)
		}
	}
	return selected
}

func takeLearningCards(cards []map[string]any, limit int) []map[string]any {
	if len(cards) < limit {
		limit = len(cards)
	}
	return append([]map[string]any{}, cards[:limit]...)
}

func learningCardStable(card map[string]any) bool {
	if sourceLayer := stringFromAny(card["source_layer"]); sourceLayer != "" {
		return sourceLayer != "candidate"
	}
	status := stringFromAny(card["status"])
	return status == "confirmed" || status == "promoted-rule" || status == "indexed"
}
