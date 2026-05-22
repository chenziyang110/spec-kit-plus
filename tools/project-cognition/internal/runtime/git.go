package runtime

import (
	"bytes"
	"os/exec"
	"path/filepath"
	"strings"
)

func GitChangedPaths(root string) ([]string, error) {
	args := []string{"status", "--short", "--untracked-files=all"}
	cmd := exec.Command("git", args...)
	cmd.Dir = root
	var out bytes.Buffer
	cmd.Stdout = &out
	if err := cmd.Run(); err != nil {
		diff := exec.Command("git", "diff", "--name-only")
		diff.Dir = root
		data, diffErr := diff.Output()
		if diffErr != nil {
			return []string{}, err
		}
		return normalizeGitLines(string(data)), nil
	}
	return parseGitStatusShort(out.String()), nil
}

func parseGitStatusShort(output string) []string {
	var paths []string
	for _, line := range strings.Split(output, "\n") {
		if len(line) < 4 {
			continue
		}
		path := strings.TrimSpace(line[3:])
		if strings.Contains(path, " -> ") {
			parts := strings.Split(path, " -> ")
			path = parts[len(parts)-1]
		}
		paths = append(paths, filepath.ToSlash(path))
	}
	return uniqueStrings(paths)
}

func normalizeGitLines(output string) []string {
	var paths []string
	for _, line := range strings.Split(output, "\n") {
		line = strings.TrimSpace(line)
		if line != "" {
			paths = append(paths, filepath.ToSlash(line))
		}
	}
	return uniqueStrings(paths)
}

func uniqueStrings(values []string) []string {
	seen := map[string]bool{}
	out := make([]string, 0, len(values))
	for _, value := range values {
		value = filepath.ToSlash(strings.TrimSpace(value))
		if value == "" || seen[value] {
			continue
		}
		seen[value] = true
		out = append(out, value)
	}
	return out
}
