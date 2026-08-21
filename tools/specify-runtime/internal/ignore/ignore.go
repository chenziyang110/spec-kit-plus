package ignore

import (
	"fmt"
	"os"
	"path/filepath"
	"regexp"
	"strings"
)

type Matcher struct {
	rules []rule
}

type rule struct {
	pattern   string
	negated   bool
	directory bool
	anchored  bool
}

var defaultIgnorePatterns = []string{
	".git/",
	".specify/",
	"node_modules/",
	".venv/",
	"venv/",
	".tox/",
	".pytest_cache/",
	".mypy_cache/",
	".ruff_cache/",
	".next/",
	".nuxt/",
	".turbo/",
	".cache/",
	"__pycache__/",
	"*.pyc",
	"*.pyo",
	"*.log",
	".DS_Store",
}

var starterOptionalDirectorySuggestions = []string{
	"vendor/",
	"generated/",
	"dist/",
	"build/",
	"coverage/",
	"fixtures/",
	"testdata/",
	"tests/",
	"docs/",
	"examples/",
	"samples/",
	"benchmarks/",
}

const reviewedKeepInScanPrefix = "# reviewed-keep-in-scan: "

func Load(root string) Matcher {
	rules := rulesFromPatterns(defaultIgnorePatterns)
	for _, ignorePath := range []string{
		filepath.Join(root, ".cognitionignore"),
		filepath.Join(root, ".specify", "project-cognition", ".cognitionignore"),
	} {
		rules = append(rules, readRules(ignorePath)...)
	}
	return Matcher{rules: rules}
}

func StarterIgnorePath(root string) string {
	return filepath.Join(root, ".specify", "project-cognition", ".cognitionignore")
}

func WriteStarterIgnoreFile(root string) (string, bool, error) {
	path := StarterIgnorePath(root)
	if _, err := os.Stat(path); err == nil {
		return path, false, nil
	} else if err != nil && !os.IsNotExist(err) {
		return path, false, err
	}
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		return path, false, err
	}
	if err := os.WriteFile(path, []byte(GenerateStarterIgnoreFile(root)), 0o644); err != nil {
		return path, false, err
	}
	return path, true, nil
}

func GenerateStarterIgnoreFile(root string) string {
	gitignoreSuggestions := gitignoreSuggestions(root)
	optionalSuggestions := optionalDirectorySuggestions(root, gitignoreSuggestions)

	var b strings.Builder
	b.WriteString("# Project Cognition ignore rules\n")
	b.WriteString("#\n")
	b.WriteString("# gitignore-compatible patterns for project cognition only.\n")
	b.WriteString("# These rules affect sp-map-scan, sp-map-build, and sp-map-update.\n")
	b.WriteString("# Uncomment suggestions only after confirming they are not useful project evidence.\n")
	b.WriteString("# The runtime marks reviewed but declined suggestions as reviewed-keep-in-scan.\n")
	b.WriteString("#\n")
	b.WriteString("# Built-in defaults are already ignored before this file is loaded: .git/,\n")
	b.WriteString("# .specify/, node_modules/, common virtualenv/cache directories, Python bytecode,\n")
	b.WriteString("# logs, and OS metadata.\n")

	if len(gitignoreSuggestions) > 0 {
		b.WriteString("\n# --- From .gitignore (uncomment to exclude from project cognition) ---\n")
		for _, suggestion := range gitignoreSuggestions {
			b.WriteString("# ")
			b.WriteString(suggestion)
			b.WriteString("\n")
		}
	}

	if len(optionalSuggestions) > 0 {
		b.WriteString("\n# --- Common low-signal directories found (review before uncommenting) ---\n")
		for _, suggestion := range optionalSuggestions {
			b.WriteString("# ")
			b.WriteString(suggestion)
			b.WriteString("\n")
		}
	}

	return strings.TrimRight(b.String(), "\n") + "\n"
}

// StarterIgnoreSuggestions returns only the decision-bearing patterns rendered
// into the starter file. The cognition CLI exposes this compact list so agents
// can present it for confirmation without opening runtime-owned storage.
func StarterIgnoreSuggestions(root string) []string {
	gitignorePatterns := gitignoreSuggestions(root)
	optionalPatterns := optionalDirectorySuggestions(root, gitignorePatterns)
	patterns := append([]string(nil), gitignorePatterns...)
	patterns = append(patterns, optionalPatterns...)
	return patterns
}

// PendingStarterIgnoreSuggestions returns current starter suggestions that are
// still present as undecided comments. Active rules and explicit
// reviewed-keep-in-scan markers are already resolved decisions.
func PendingStarterIgnoreSuggestions(root string) []string {
	suggestions := StarterIgnoreSuggestions(root)
	if len(suggestions) == 0 {
		return nil
	}
	data, err := os.ReadFile(StarterIgnorePath(root))
	if err != nil {
		return nil
	}
	available := map[string]bool{}
	for _, pattern := range suggestions {
		available[pattern] = true
	}
	active := map[string]bool{}
	pending := map[string]bool{}
	for _, line := range strings.Split(string(data), "\n") {
		trimmed := strings.TrimSpace(line)
		if trimmed == "" || strings.HasPrefix(trimmed, reviewedKeepInScanPrefix) {
			continue
		}
		if strings.HasPrefix(trimmed, "#") {
			commented := filepath.ToSlash(strings.TrimSpace(strings.TrimPrefix(trimmed, "#")))
			if available[commented] {
				pending[commented] = true
			}
			continue
		}
		candidate := filepath.ToSlash(trimmed)
		if available[candidate] {
			active[candidate] = true
		}
	}
	result := make([]string, 0, len(pending))
	for _, pattern := range suggestions {
		if pending[pattern] && !active[pattern] {
			result = append(result, pattern)
		}
	}
	return result
}

// ActivateStarterIgnoreSuggestions turns only user-confirmed starter comments
// into active cognition-ignore rules. Callers may select any subset of the
// current suggestions, but cannot use this surface to append arbitrary rules.
func ActivateStarterIgnoreSuggestions(root string, selected []string) ([]string, error) {
	if len(selected) == 0 {
		return nil, fmt.Errorf("at least one reviewed starter ignore pattern is required")
	}
	available := map[string]bool{}
	for _, pattern := range StarterIgnoreSuggestions(root) {
		available[pattern] = true
	}

	confirmed := make([]string, 0, len(selected))
	seen := map[string]bool{}
	for _, raw := range selected {
		pattern := filepath.ToSlash(strings.TrimSpace(raw))
		if pattern == "" {
			return nil, fmt.Errorf("confirmed starter ignore patterns must not be empty")
		}
		if !available[pattern] {
			return nil, fmt.Errorf("pattern %q was not present in the current starter review set", pattern)
		}
		if !seen[pattern] {
			seen[pattern] = true
			confirmed = append(confirmed, pattern)
		}
	}

	path := StarterIgnorePath(root)
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, fmt.Errorf("read starter cognition ignore: %w", err)
	}
	lines := strings.Split(string(data), "\n")
	found := map[string]bool{}
	for index, line := range lines {
		trimmed := strings.TrimSpace(line)
		if seen[trimmed] {
			found[trimmed] = true
			continue
		}
		if strings.HasPrefix(trimmed, reviewedKeepInScanPrefix) {
			reviewed := filepath.ToSlash(strings.TrimSpace(strings.TrimPrefix(trimmed, reviewedKeepInScanPrefix)))
			if seen[reviewed] {
				lines[index] = reviewed
				found[reviewed] = true
			}
			continue
		}
		if !strings.HasPrefix(trimmed, "#") {
			continue
		}
		commented := filepath.ToSlash(strings.TrimSpace(strings.TrimPrefix(trimmed, "#")))
		if !available[commented] {
			continue
		}
		if seen[commented] {
			lines[index] = commented
			found[commented] = true
		} else {
			lines[index] = reviewedKeepInScanPrefix + commented
		}
	}
	for _, pattern := range confirmed {
		if !found[pattern] {
			return nil, fmt.Errorf("reviewed pattern %q is not present in the starter cognition ignore file", pattern)
		}
	}
	if err := os.WriteFile(path, []byte(strings.Join(lines, "\n")), 0o644); err != nil {
		return nil, fmt.Errorf("activate starter cognition ignore patterns: %w", err)
	}
	return confirmed, nil
}

func rulesFromPatterns(patterns []string) []rule {
	rules := make([]rule, 0, len(patterns))
	for _, pattern := range patterns {
		if parsed, ok := parseRule(pattern); ok {
			rules = append(rules, parsed)
		}
	}
	return rules
}

func gitignoreSuggestions(root string) []string {
	data, err := os.ReadFile(filepath.Join(root, ".gitignore"))
	if err != nil {
		return nil
	}
	defaults := defaultPatternKeys()
	out := []string{}
	seen := map[string]bool{}
	for _, line := range strings.Split(string(data), "\n") {
		pattern, ok := suggestionPattern(line)
		if !ok {
			continue
		}
		key := patternKey(pattern)
		if key == "" || defaults[key] || seen[key] {
			continue
		}
		seen[key] = true
		out = append(out, pattern)
	}
	return out
}

func optionalDirectorySuggestions(root string, existing []string) []string {
	defaults := defaultPatternKeys()
	seen := map[string]bool{}
	for _, pattern := range existing {
		seen[patternKey(pattern)] = true
	}
	out := []string{}
	for _, pattern := range starterOptionalDirectorySuggestions {
		key := patternKey(pattern)
		if key == "" || defaults[key] || seen[key] {
			continue
		}
		info, err := os.Stat(filepath.Join(root, strings.TrimSuffix(pattern, "/")))
		if err != nil || !info.IsDir() {
			continue
		}
		seen[key] = true
		out = append(out, pattern)
	}
	return out
}

func defaultPatternKeys() map[string]bool {
	keys := map[string]bool{}
	for _, pattern := range defaultIgnorePatterns {
		if key := patternKey(pattern); key != "" {
			keys[key] = true
		}
	}
	return keys
}

func suggestionPattern(line string) (string, bool) {
	pattern := filepath.ToSlash(strings.TrimSpace(line))
	if pattern == "" || strings.HasPrefix(pattern, "#") || strings.HasPrefix(pattern, "!") {
		return "", false
	}
	return pattern, true
}

func patternKey(pattern string) string {
	pattern = filepath.ToSlash(strings.TrimSpace(pattern))
	pattern = strings.TrimPrefix(pattern, "!")
	pattern = strings.TrimSpace(pattern)
	for strings.HasPrefix(pattern, "./") {
		pattern = strings.TrimPrefix(pattern, "./")
	}
	pattern = strings.TrimPrefix(pattern, "/")
	return strings.Trim(pattern, "/")
}

func readRules(path string) []rule {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil
	}
	var rules []rule
	for _, line := range strings.Split(string(data), "\n") {
		parsed, ok := parseRule(line)
		if !ok {
			continue
		}
		rules = append(rules, parsed)
	}
	return rules
}

func parseRule(line string) (rule, bool) {
	pattern := filepath.ToSlash(strings.TrimSpace(line))
	if pattern == "" || strings.HasPrefix(pattern, "#") {
		return rule{}, false
	}

	negated := false
	if strings.HasPrefix(pattern, "!") {
		negated = true
		pattern = strings.TrimSpace(strings.TrimPrefix(pattern, "!"))
		if pattern == "" {
			return rule{}, false
		}
	}

	anchored := strings.HasPrefix(pattern, "/")
	pattern = strings.TrimPrefix(pattern, "/")
	for strings.HasPrefix(pattern, "./") {
		pattern = strings.TrimPrefix(pattern, "./")
	}
	directory := strings.HasSuffix(pattern, "/")
	pattern = strings.Trim(pattern, "/")
	if pattern == "" {
		return rule{}, false
	}

	return rule{
		pattern:   pattern,
		negated:   negated,
		directory: directory,
		anchored:  anchored,
	}, true
}

func (m Matcher) Filter(paths []string) (kept []string, ignored []string) {
	for _, path := range paths {
		if m.Ignored(path) {
			ignored = append(ignored, path)
			continue
		}
		kept = append(kept, path)
	}
	return kept, ignored
}

func (m Matcher) Ignored(path string) bool {
	path = normalizePath(path)
	if path == "" {
		return false
	}

	ignored := false
	for _, rule := range m.rules {
		if rule.matches(path) {
			ignored = !rule.negated
		}
	}
	return ignored
}

func (m Matcher) MayReincludeDescendant(path string) bool {
	path = normalizePath(path)
	if path == "" {
		return true
	}
	for _, rule := range m.rules {
		if rule.negated && ruleMayMatchDescendant(rule, path) {
			return true
		}
	}
	return false
}

func ruleMayMatchDescendant(r rule, path string) bool {
	pattern := normalizePath(r.pattern)
	if pattern == "" {
		return false
	}
	if r.anchored {
		return pattern == path || strings.HasPrefix(pattern, path+"/") || strings.HasPrefix(path, pattern+"/")
	}
	if !strings.Contains(pattern, "/") {
		return true
	}
	if strings.HasPrefix(pattern, "**/") {
		pattern = strings.TrimPrefix(pattern, "**/")
	}
	if pattern == path || strings.HasPrefix(pattern, path+"/") {
		return true
	}
	parts := strings.Split(path, "/")
	for i := range parts {
		suffix := strings.Join(parts[i:], "/")
		if pattern == suffix || strings.HasPrefix(pattern, suffix+"/") {
			return true
		}
	}
	return false
}

func (r rule) matches(path string) bool {
	if r.directory {
		return r.matchesDirectory(path)
	}
	return matchPattern(r.pattern, path, r.anchored)
}

func (r rule) matchesDirectory(path string) bool {
	parts := strings.Split(path, "/")
	if r.anchored {
		for i := range parts {
			prefix := strings.Join(parts[:i+1], "/")
			if globMatch(r.pattern, prefix) {
				return true
			}
		}
		return false
	}

	if !strings.Contains(r.pattern, "/") {
		for _, part := range parts {
			if globMatch(r.pattern, part) {
				return true
			}
		}
		return false
	}

	for i := range parts {
		prefix := strings.Join(parts[:i+1], "/")
		if matchPattern(r.pattern, prefix, r.anchored) {
			return true
		}
	}
	return false
}

func matchPattern(pattern string, path string, anchored bool) bool {
	if !strings.Contains(pattern, "/") {
		if anchored {
			return matchPathOrDescendant(pattern, path)
		}
		for _, part := range strings.Split(path, "/") {
			if globMatch(pattern, part) {
				return true
			}
		}
		return false
	}

	patterns := []string{pattern}
	if strings.HasPrefix(pattern, "**/") {
		patterns = append(patterns, strings.TrimPrefix(pattern, "**/"))
	}

	for _, candidate := range patterns {
		if matchPathOrDescendant(candidate, path) {
			return true
		}
		if anchored {
			continue
		}
		parts := strings.Split(path, "/")
		for i := 1; i < len(parts); i++ {
			if matchPathOrDescendant(candidate, strings.Join(parts[i:], "/")) {
				return true
			}
		}
	}
	return false
}

func matchPathOrDescendant(pattern string, path string) bool {
	if globMatch(pattern, path) {
		return true
	}
	parts := strings.Split(path, "/")
	for i := 0; i < len(parts)-1; i++ {
		prefix := strings.Join(parts[:i+1], "/")
		if globMatch(pattern, prefix) {
			return true
		}
	}
	return false
}

func globMatch(pattern string, value string) bool {
	ok, err := regexp.MatchString("^"+globRegex(pattern)+"$", value)
	return err == nil && ok
}

func globRegex(pattern string) string {
	var out strings.Builder
	for i := 0; i < len(pattern); {
		switch pattern[i] {
		case '*':
			if i+1 < len(pattern) && pattern[i+1] == '*' {
				if i+2 < len(pattern) && pattern[i+2] == '/' {
					out.WriteString("(?:.*/)?")
					i += 3
					continue
				}
				out.WriteString(".*")
				i += 2
				continue
			}
			out.WriteString("[^/]*")
		case '?':
			out.WriteString("[^/]")
		default:
			out.WriteString(regexp.QuoteMeta(string(pattern[i])))
		}
		i++
	}
	return out.String()
}

func normalizePath(path string) string {
	normalized := filepath.ToSlash(strings.TrimSpace(path))
	for strings.HasPrefix(normalized, "./") {
		normalized = strings.TrimPrefix(normalized, "./")
	}
	return strings.Trim(normalized, "/")
}
