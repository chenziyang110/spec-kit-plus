package main

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"regexp"
	"sort"
	"strings"
	"unicode/utf8"

	runtimeconfig "github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/config"
)

const (
	learningAssessmentVersion     = "v1"
	learningPolicyFallbackWarning = "project_learning_policy_invalid:using_builtin_policy"
)

type learningPolicy struct {
	detectors          runtimeconfig.LearningDetectorsConfig
	deferredReviewDays int
}

func learningPolicyFromConfig(configured runtimeconfig.ProjectLearningConfig) learningPolicy {
	if configured.DeferredReviewDays == 0 {
		configured.DeferredReviewDays = runtimeconfig.DefaultLearningDeferredReviewDays
	}
	configured.Detectors.SecretPrefixes = normalizedLearningPolicyLiterals(configured.Detectors.SecretPrefixes)
	configured.Detectors.SensitiveKeyNames = normalizedLearningPolicyLiterals(configured.Detectors.SensitiveKeyNames)
	configured.Detectors.BusinessIDPrefixes = normalizedLearningPolicyLiterals(configured.Detectors.BusinessIDPrefixes)
	configured.Detectors.SensitiveTerms = normalizedLearningPolicyLiterals(configured.Detectors.SensitiveTerms)
	return learningPolicy{detectors: configured.Detectors, deferredReviewDays: configured.DeferredReviewDays}
}

func builtinLearningPolicy() learningPolicy {
	return learningPolicyFromConfig(runtimeconfig.ProjectLearningConfig{})
}

func (service learningService) loadLearningPolicy(write bool) (learningPolicy, []string, error) {
	configured, err := runtimeconfig.LoadProjectLearning(service.projectRoot)
	if err == nil {
		return learningPolicyFromConfig(configured), nil, nil
	}
	if write {
		return learningPolicy{}, nil, fmt.Errorf("project_learning policy is invalid; repair .specify/config.json before Learning writes")
	}
	return builtinLearningPolicy(), []string{learningPolicyFallbackWarning}, nil
}

func (policy learningPolicy) digest() string {
	payload := map[string]any{
		"deferred_review_days": policy.deferredReviewDays,
		"detectors": map[string]any{
			"secret_prefixes":      policy.detectors.SecretPrefixes,
			"sensitive_key_names":  policy.detectors.SensitiveKeyNames,
			"business_id_prefixes": policy.detectors.BusinessIDPrefixes,
			"sensitive_terms":      policy.detectors.SensitiveTerms,
		},
	}
	raw, _ := json.Marshal(payload)
	sum := sha256.Sum256(raw)
	return hex.EncodeToString(sum[:])
}

func normalizedLearningPolicyLiterals(values []string) []string {
	seen := map[string]string{}
	for _, value := range values {
		trimmed := strings.TrimSpace(value)
		if trimmed != "" {
			seen[strings.ToLower(trimmed)] = trimmed
		}
	}
	keys := make([]string, 0, len(seen))
	for key := range seen {
		keys = append(keys, key)
	}
	sort.Slice(keys, func(i, j int) bool {
		leftLength := utf8.RuneCountInString(seen[keys[i]])
		rightLength := utf8.RuneCountInString(seen[keys[j]])
		if leftLength != rightLength {
			return leftLength > rightLength
		}
		return keys[i] < keys[j]
	})
	result := make([]string, 0, len(keys))
	for _, key := range keys {
		result = append(result, seen[key])
	}
	return result
}

func redactLearningTextWithPolicy(value string, policy learningPolicy) learningRedactionResult {
	text := value
	labels := map[string]bool{}
	apply := func(pattern, replacement, label string) {
		re := regexp.MustCompile(pattern)
		if re.MatchString(text) {
			labels[label] = true
			text = re.ReplaceAllString(text, replacement)
		}
	}
	for _, term := range policy.detectors.SensitiveTerms {
		apply(`(?i)`+regexp.QuoteMeta(term), `[REDACTED_ORG_TERM]`, "organization_sensitive")
	}
	for _, key := range policy.detectors.SensitiveKeyNames {
		pattern := `(?i)(^|[^A-Za-z0-9_.-])(` + regexp.QuoteMeta(key) + `\s*[:=]\s*)(["']?)([^"'\s,;}]+)(["']?)`
		apply(pattern, `${1}${2}${3}[REDACTED_SECRET]${5}`, "credential")
	}
	for _, prefix := range policy.detectors.SecretPrefixes {
		apply(`(?i)(^|[^A-Za-z0-9_])`+regexp.QuoteMeta(prefix)+`[^\s"',;}\]]{3,}`, `${1}[REDACTED_SECRET]`, "credential")
	}
	for _, prefix := range policy.detectors.BusinessIDPrefixes {
		apply(`(?i)(^|[^A-Za-z0-9_])`+regexp.QuoteMeta(prefix)+`[A-Za-z0-9_-]{3,}($|[^A-Za-z0-9_])`, `${1}[REDACTED_BUSINESS_ID]${2}`, "business_identifier")
	}
	builtin := redactLearningText(text)
	text = builtin.text
	for _, label := range builtin.labels {
		labels[label] = true
	}
	return learningRedactionResult{text: text, labels: sortedLearningLabels(labels)}
}

func redactLearningReferenceTextWithPolicy(value string, policy learningPolicy) learningRedactionResult {
	text := value
	labels := map[string]bool{}
	for _, term := range policy.detectors.SensitiveTerms {
		slug := learningPolicyTermSlug(term)
		if slug == "" {
			continue
		}
		pattern := regexp.MustCompile(`(?i)(^|[^a-z0-9])(` + regexp.QuoteMeta(slug) + `)($|[^a-z0-9])`)
		if pattern.MatchString(text) {
			text = pattern.ReplaceAllString(text, `${1}[REDACTED_ORG_TERM]${3}`)
			labels["organization_sensitive"] = true
		}
	}
	redacted := redactLearningTextWithPolicy(text, policy)
	mergeLearningPolicyLabels(labels, redacted.labels)
	redacted.labels = sortedLearningLabels(labels)
	return redacted
}

func sanitizeLearningEntryWithPolicy(entry map[string]any, policy learningPolicy) map[string]any {
	// Apply project literals to raw human-authored fields first. Running the
	// built-in recursive sanitizer before this step can partially redact a
	// configured organization phrase (for example, its embedded email), which
	// prevents the configured literal from ever matching as a whole.
	prepared := cloneLearningMap(entry)
	labels := map[string]bool{}
	for _, label := range anyStringSlice(prepared["redaction_labels"]) {
		if validLearningRedactionLabel(label) {
			labels[label] = true
		}
	}
	if command, err := normalizeLearningCommand(stringFromAny(prepared["source_command"])); err == nil {
		commandResult := redactLearningTextWithPolicy(command, policy)
		mergeLearningPolicyLabels(labels, commandResult.labels)
		if commandResult.text != command {
			prepared["source_command"] = "sp-other"
		} else {
			prepared["source_command"] = command
		}
	}
	cleanApplies := []string{}
	for _, value := range anyStringSlice(prepared["applies_to"]) {
		command, err := normalizeLearningCommand(value)
		if err != nil {
			continue
		}
		commandResult := redactLearningTextWithPolicy(command, policy)
		mergeLearningPolicyLabels(labels, commandResult.labels)
		if commandResult.text != command {
			cleanApplies = append(cleanApplies, "sp-other")
		} else {
			cleanApplies = append(cleanApplies, command)
		}
	}
	prepared["applies_to"] = stringsToAny(uniqueSortedTrimmed(cleanApplies))
	for _, key := range []string{
		"summary", "evidence", "decisive_signal", "root_cause_family", "promotion_hint", "problem", "lesson", "recommended_action",
	} {
		if value, ok := prepared[key].(string); ok {
			redacted := redactLearningTextWithPolicy(value, policy)
			prepared[key] = redacted.text
			mergeLearningPolicyLabels(labels, redacted.labels)
		}
	}
	for _, key := range []string{"false_starts", "rejected_paths", "injection_targets", "avoid", "trigger_signals", "success_criteria", "exceptions"} {
		values := []string{}
		for _, value := range anyStringSlice(prepared[key]) {
			redacted := redactLearningTextWithPolicy(value, policy)
			values = append(values, redacted.text)
			mergeLearningPolicyLabels(labels, redacted.labels)
		}
		prepared[key] = stringsToAny(uniqueSortedTrimmed(values))
	}
	if facets := mapStringAny(prepared["facets"]); len(facets) > 0 {
		cleanFacets := map[string]any{}
		for key, rawValues := range facets {
			values := []string{}
			for _, value := range anyStringSlice(rawValues) {
				redacted := redactLearningTextWithPolicy(value, policy)
				values = append(values, redacted.text)
				mergeLearningPolicyLabels(labels, redacted.labels)
			}
			cleanFacets[key] = stringsToAny(uniqueSortedTrimmed(values))
		}
		prepared["facets"] = cleanFacets
	}
	if rawKey := stringFromAny(entry["recurrence_key"]); rawKey != "" {
		keyResult := sanitizeLearningRecurrenceKeyWithPolicy(rawKey, policy)
		prepared["recurrence_key"] = keyResult.text
		mergeLearningPolicyLabels(labels, keyResult.labels)
	}
	prepared["redaction_labels"] = stringsToAny(sortedLearningLabels(labels))
	if len(labels) > 0 {
		prepared["sensitivity"] = "sanitized"
	}
	sanitized := sanitizeLearningEntry(prepared)
	for _, label := range anyStringSlice(sanitized["redaction_labels"]) {
		if validLearningRedactionLabel(label) {
			labels[label] = true
		}
	}
	finalLabels := sortedLearningLabels(labels)
	sanitized["redaction_labels"] = stringsToAny(finalLabels)
	if len(finalLabels) > 0 {
		sanitized["sensitivity"] = "sanitized"
	} else {
		sanitized["sensitivity"] = "safe"
	}
	return sanitized
}

func sanitizeLearningRecurrenceKeyWithPolicy(key string, policy learningPolicy) learningRedactionResult {
	raw := strings.ToLower(strings.TrimSpace(key))
	redacted := redactLearningReferenceTextWithPolicy(raw, policy)
	safe := strings.ReplaceAll(redacted.text, "\\", "/")
	for marker, replacement := range map[string]string{
		"<USER_HOME>": "user-home", "[REDACTED_SECRET]": "redacted-secret", "[REDACTED_EMAIL]": "redacted-email",
		"[REDACTED_PRIVATE_KEY]": "redacted-private-key", "[REDACTED_PHONE]": "redacted-phone",
		"[REDACTED_BUSINESS_ID]": "redacted-business-id", "[REDACTED_ORG_TERM]": "redacted-org-term",
	} {
		safe = strings.ReplaceAll(safe, marker, replacement)
	}
	safe = regexp.MustCompile(`[^a-z0-9._-]+`).ReplaceAllString(safe, "-")
	safe = strings.Trim(safe, ".-")
	if safe == "" {
		sum := sha256.Sum256([]byte(key))
		safe = "redacted." + hex.EncodeToString(sum[:])[:12]
	}
	redacted.text = safe
	return redacted
}

func learningPolicyTermSlug(value string) string {
	slug := strings.ToLower(strings.TrimSpace(value))
	slug = regexp.MustCompile(`[^a-z0-9]+`).ReplaceAllString(slug, "-")
	return strings.Trim(slug, "-")
}

func mergeLearningPolicyLabels(target map[string]bool, labels []string) {
	for _, label := range labels {
		if validLearningRedactionLabel(label) {
			target[label] = true
		}
	}
}

func sanitizeLearningContextsWithPolicy(context map[string][]string, policy learningPolicy) map[string][]string {
	clean := map[string][]string{}
	for key, values := range context {
		for _, value := range values {
			clean[key] = append(clean[key], redactLearningTextWithPolicy(value, policy).text)
		}
		clean[key] = uniqueSortedTrimmed(clean[key])
	}
	return clean
}
