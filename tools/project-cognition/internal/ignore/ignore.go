package ignore

import (
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

func Load(root string) Matcher {
	var rules []rule
	for _, ignorePath := range []string{
		filepath.Join(root, ".cognitionignore"),
		filepath.Join(root, ".specify", "project-cognition", ".cognitionignore"),
	} {
		rules = append(rules, readRules(ignorePath)...)
	}
	return Matcher{rules: rules}
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
