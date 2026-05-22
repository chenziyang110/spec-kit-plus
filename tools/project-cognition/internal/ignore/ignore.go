package ignore

import (
	"os"
	"path/filepath"
	"strings"
)

type Matcher struct {
	patterns []string
}

func Load(root string) Matcher {
	var patterns []string
	for _, ignorePath := range []string{
		filepath.Join(root, ".cognitionignore"),
		filepath.Join(root, ".specify", "project-cognition", ".cognitionignore"),
	} {
		patterns = append(patterns, readPatterns(ignorePath)...)
	}
	return Matcher{patterns: patterns}
}

func readPatterns(path string) []string {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil
	}
	var patterns []string
	for _, line := range strings.Split(string(data), "\n") {
		line = strings.TrimSpace(line)
		if line == "" || strings.HasPrefix(line, "#") {
			continue
		}
		patterns = append(patterns, filepath.ToSlash(line))
	}
	return patterns
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
	path = filepath.ToSlash(strings.TrimPrefix(path, "./"))
	for _, pattern := range m.patterns {
		if pattern == path || strings.HasPrefix(path, strings.TrimSuffix(pattern, "/")+"/") {
			return true
		}
		if ok, _ := filepath.Match(pattern, path); ok {
			return true
		}
	}
	return false
}
