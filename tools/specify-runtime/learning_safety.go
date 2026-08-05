package main

import (
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"regexp"
	"sort"
	"strings"
)

type learningRedactionResult struct {
	text   string
	labels []string
}

func redactLearningText(value string) learningRedactionResult {
	text := value
	labels := map[string]bool{}
	for marker, label := range map[string]string{
		"[REDACTED_SECRET]":      "credential",
		"[REDACTED_EMAIL]":       "email",
		"[REDACTED_PRIVATE_KEY]": "private_key",
		"[REDACTED_PHONE]":       "personal_identifier",
		"[REDACTED_BUSINESS_ID]": "business_identifier",
		"[REDACTED_ORG_TERM]":    "organization_sensitive",
		"<USER_HOME>":            "machine_path",
	} {
		if strings.Contains(text, marker) {
			labels[label] = true
		}
	}
	apply := func(pattern, replacement, label string) {
		re := regexp.MustCompile(pattern)
		if re.MatchString(text) {
			labels[label] = true
			text = re.ReplaceAllString(text, replacement)
		}
	}
	apply(`(?is)-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----.*?-----END [A-Z0-9 ]*PRIVATE KEY-----`, `[REDACTED_PRIVATE_KEY]`, "private_key")
	apply(`(?i)(https?://)[^/\s:@]+:[^@\s/]+@`, `${1}[REDACTED_SECRET]@`, "credential")
	apply(`(?i)\bAuthorization\s*[:=]\s*Bearer\s+[A-Za-z0-9._~+/=-]+`, `Authorization: [REDACTED_SECRET]`, "credential")
	apply(`(?i)\bBearer\s+[A-Za-z0-9._~+/=-]+`, `[REDACTED_SECRET]`, "credential")
	apply(`(?i)(["']?\b(?:secret|password|token|api[_-]?key|authorization)\b["']?\s*[:=]\s*)["']?[^\["',;}\]\s]+["']?`, `${1}"[REDACTED_SECRET]"`, "credential")
	apply(`\bghp_[A-Za-z0-9_]{8,}\b`, `[REDACTED_SECRET]`, "credential")
	apply(`\bsk-[A-Za-z0-9_-]{16,}\b`, `[REDACTED_SECRET]`, "credential")
	apply(`\bAKIA[0-9A-Z]{12,}\b`, `[REDACTED_SECRET]`, "credential")
	apply(`\beyJ[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]{5,}\b`, `[REDACTED_SECRET]`, "credential")
	apply(`(?i)\b[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,}\b`, `[REDACTED_EMAIL]`, "email")
	text = redactLearningPhoneNumbers(text, labels)
	text = redactLearningMachinePaths(text, labels)
	// Entropy is deliberately the final fallback. Deterministic shapes such as
	// email addresses and home-directory paths must retain their more precise
	// safety label instead of being swallowed by a generic credential match.
	text = redactLearningHighEntropyTokens(text, labels)
	return learningRedactionResult{text: text, labels: sortedLearningLabels(labels)}
}

func redactLearningPhoneNumbers(text string, labels map[string]bool) string {
	phone := regexp.MustCompile(`\+?\d[\d() -]{6,}\d`)
	return phone.ReplaceAllStringFunc(text, func(match string) string {
		if regexp.MustCompile(`^\d{4}-\d{2}-\d{2}$`).MatchString(match) {
			return match
		}
		digits, hasSeparator := 0, false
		for _, character := range match {
			switch {
			case character >= '0' && character <= '9':
				digits++
			case strings.ContainsRune("+() -", character):
				hasSeparator = true
			}
		}
		if digits < 7 || digits > 15 || !hasSeparator {
			return match
		}
		if !strings.ContainsAny(match, "+() ") && !regexp.MustCompile(`^(?:\d{1,3}-)?\d{3}-\d{3}-\d{4}$`).MatchString(match) {
			return match
		}
		labels["personal_identifier"] = true
		return "[REDACTED_PHONE]"
	})
}

func redactLearningHighEntropyTokens(text string, labels map[string]bool) string {
	token := regexp.MustCompile(`[A-Za-z0-9!@#$%^&*_=+~.-]{20,}`)
	return token.ReplaceAllStringFunc(text, func(match string) string {
		if regexp.MustCompile(`^[a-fA-F0-9]+$`).MatchString(match) {
			return match
		}
		if regexp.MustCompile(`(?i)^(?:LRN-|learn-)[A-Za-z0-9._-]+$`).MatchString(match) {
			return match
		}
		upper, lower, digit, symbol := false, false, false, false
		distinct := map[rune]bool{}
		for _, character := range match {
			distinct[character] = true
			switch {
			case character >= 'A' && character <= 'Z':
				upper = true
			case character >= 'a' && character <= 'z':
				lower = true
			case character >= '0' && character <= '9':
				digit = true
			default:
				if !strings.ContainsRune("._-", character) {
					symbol = true
				}
			}
		}
		categories := 0
		for _, present := range []bool{upper, lower, digit, symbol} {
			if present {
				categories++
			}
		}
		if categories < 3 || len(distinct) < 10 {
			return match
		}
		labels["credential"] = true
		return "[REDACTED_SECRET]"
	})
}

func redactLearningMachinePaths(text string, labels map[string]bool) string {
	windows := regexp.MustCompile(`(?i)\b[A-Z]:[\\/]Users[\\/][^\\/\s"'<>|?*]+((?:[\\/][^\s"'<>|?*]+)*)`)
	text = windows.ReplaceAllStringFunc(text, func(match string) string {
		labels["machine_path"] = true
		parts := regexp.MustCompile(`(?i)^[A-Z]:[\\/]Users[\\/][^\\/]+`).ReplaceAllString(match, "")
		return "<USER_HOME>" + normalizeLearningPathSuffix(parts)
	})
	unix := regexp.MustCompile(`(?:^|[^\w])(/(?:(?:home|Users)/[^/\s"'<>]+|root/[^/\s"'<>]+)((?:/[^\s"'<>]+)*))`)
	text = unix.ReplaceAllStringFunc(text, func(match string) string {
		prefix := ""
		path := match
		if !strings.HasPrefix(match, "/") {
			prefix, path = match[:1], match[1:]
		}
		labels["machine_path"] = true
		parts := regexp.MustCompile(`^/(?:(?:home|Users)/[^/]+|root)`).ReplaceAllString(path, "")
		return prefix + "<USER_HOME>" + normalizeLearningPathSuffix(parts)
	})
	bareRoot := regexp.MustCompile(`(^|[^\w])(/root)([^A-Za-z0-9_/-]|$)`)
	if bareRoot.MatchString(text) {
		labels["machine_path"] = true
		text = bareRoot.ReplaceAllString(text, `${1}<USER_HOME>${3}`)
	}
	return text
}

func normalizeLearningPathSuffix(suffix string) string {
	if suffix == "" {
		return ""
	}
	suffix = strings.ReplaceAll(suffix, "\\", "/")
	if !strings.HasPrefix(suffix, "/") {
		suffix = "/" + suffix
	}
	return suffix
}

func sortedLearningLabels(labels map[string]bool) []string {
	values := []string{}
	for label := range labels {
		values = append(values, label)
	}
	sort.Strings(values)
	return values
}

func sanitizeLearningEntry(entry map[string]any) map[string]any {
	if entry == nil {
		return nil
	}
	labels := map[string]bool{}
	sanitized := sanitizeLearningAny(entry, labels).(map[string]any)
	if key := stringFromAny(entry["recurrence_key"]); key != "" {
		result := sanitizeLearningRecurrenceKey(key)
		sanitized["recurrence_key"] = result.text
		for _, label := range result.labels {
			labels[label] = true
		}
	}
	mergedLabels := map[string]bool{}
	for _, label := range anyStringSlice(entry["redaction_labels"]) {
		if validLearningRedactionLabel(label) {
			mergedLabels[label] = true
		}
	}
	for label := range labels {
		if validLearningRedactionLabel(label) {
			mergedLabels[label] = true
		}
	}
	finalLabels := sortedLearningLabels(mergedLabels)
	sanitized["redaction_labels"] = stringsToAny(finalLabels)
	if len(finalLabels) > 0 {
		sanitized["sensitivity"] = "sanitized"
	} else if stringFromAny(entry["sensitivity"]) == "sanitized" {
		sanitized["sensitivity"] = "sanitized"
	} else {
		sanitized["sensitivity"] = "safe"
	}
	return sanitized
}

func sanitizeLearningEntryForOutput(entry map[string]any) map[string]any {
	return sanitizeLearningEntry(entry)
}

func sanitizeLearningPayload(payload map[string]any) map[string]any {
	labels := map[string]bool{}
	sanitized := sanitizeLearningAny(payload, labels).(map[string]any)
	if len(labels) > 0 {
		existing := map[string]bool{}
		for _, label := range anyStringSlice(sanitized["redaction_labels"]) {
			if validLearningRedactionLabel(label) {
				existing[label] = true
			}
		}
		for label := range labels {
			if validLearningRedactionLabel(label) {
				existing[label] = true
			}
		}
		sanitized["redaction_labels"] = stringsToAny(sortedLearningLabels(existing))
		sanitized["sensitivity"] = "sanitized"
	}
	return sanitized
}

func sanitizeLearningProjection(payload map[string]any) map[string]any {
	labels := map[string]bool{}
	return sanitizeLearningAny(payload, labels).(map[string]any)
}

func mergeLearningContentSafety(values ...map[string]any) (string, []string) {
	labels := map[string]bool{}
	sanitized := false
	for _, value := range values {
		if value == nil {
			continue
		}
		if stringFromAny(value["sensitivity"]) == "sanitized" {
			sanitized = true
		}
		for _, label := range anyStringSlice(value["redaction_labels"]) {
			if validLearningRedactionLabel(label) {
				labels[label] = true
				sanitized = true
			}
		}
	}
	merged := sortedLearningLabels(labels)
	if sanitized || len(merged) > 0 {
		return "sanitized", merged
	}
	return "safe", merged
}

func sanitizeLearningAny(value any, labels map[string]bool) any {
	switch typed := value.(type) {
	case map[string]any:
		result := map[string]any{}
		for key, item := range typed {
			redactedKey := redactLearningText(key)
			for _, label := range redactedKey.labels {
				labels[label] = true
			}
			safeKey := redactedKey.text
			if strings.TrimSpace(safeKey) == "" {
				sum := sha256.Sum256([]byte(key))
				safeKey = "redacted-field-" + hex.EncodeToString(sum[:])[:12]
			}
			result[safeKey] = sanitizeLearningAny(item, labels)
		}
		return result
	case map[string][]string:
		result := map[string]any{}
		for key, items := range typed {
			result[key] = sanitizeLearningAny(items, labels)
		}
		return result
	case []any:
		result := make([]any, len(typed))
		for i, item := range typed {
			result[i] = sanitizeLearningAny(item, labels)
		}
		return result
	case []string:
		result := make([]any, len(typed))
		for i, item := range typed {
			result[i] = sanitizeLearningAny(item, labels)
		}
		return result
	case string:
		redacted := redactLearningText(typed)
		for _, label := range redacted.labels {
			labels[label] = true
		}
		return redacted.text
	default:
		return value
	}
}

func validLearningRedactionLabel(label string) bool {
	switch label {
	case "credential", "email", "private_key", "machine_path", "personal_identifier", "business_identifier", "organization_sensitive":
		return true
	default:
		return false
	}
}

func sanitizeLearningRecurrenceKey(key string) learningRedactionResult {
	redacted := redactLearningText(strings.ToLower(strings.TrimSpace(key)))
	safe := strings.ReplaceAll(redacted.text, "\\", "/")
	safe = strings.ReplaceAll(safe, "<USER_HOME>", "user-home")
	safe = strings.ReplaceAll(safe, "[REDACTED_SECRET]", "redacted-secret")
	safe = strings.ReplaceAll(safe, "[REDACTED_EMAIL]", "redacted-email")
	safe = strings.ReplaceAll(safe, "[REDACTED_PRIVATE_KEY]", "redacted-private-key")
	safe = strings.ReplaceAll(safe, "[REDACTED_PHONE]", "redacted-phone")
	safe = strings.ReplaceAll(safe, "[REDACTED_BUSINESS_ID]", "redacted-business-id")
	safe = strings.ReplaceAll(safe, "[REDACTED_ORG_TERM]", "redacted-org-term")
	safe = regexp.MustCompile(`[^a-z0-9._-]+`).ReplaceAllString(safe, "-")
	safe = strings.Trim(safe, ".-")
	if safe == "" {
		sum := sha256.Sum256([]byte(key))
		safe = "redacted." + hex.EncodeToString(sum[:])[:12]
	}
	redacted.text = safe
	return redacted
}

func safeSemanticLearningDigest(summary string) string {
	redacted := redactLearningText(summary).text
	sum := sha256.Sum256([]byte(redacted))
	return hex.EncodeToString(sum[:])[:16]
}

func redactLearningFormat(format string, args ...any) string {
	return redactLearningText(fmt.Sprintf(format, args...)).text
}
