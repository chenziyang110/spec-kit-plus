package runtime

import (
	"path/filepath"
	"strings"
)

type GitStatusEntry struct {
	Code    string
	Path    string
	OldPath string
}

func GitAvailable(root string) bool {
	data, err := CommandOutput(root, nil, "git", "rev-parse", "--is-inside-work-tree")
	return err == nil && strings.TrimSpace(string(data)) == "true"
}

func GitHead(root string) (string, error) {
	data, err := CommandOutput(root, nil, "git", "rev-parse", "HEAD")
	if err != nil {
		return "", err
	}
	return strings.TrimSpace(string(data)), nil
}

func GitBranch(root string) (string, error) {
	data, err := CommandOutput(root, nil, "git", "branch", "--show-current")
	if err != nil {
		return "", err
	}
	return strings.TrimSpace(string(data)), nil
}

func GitStatusEntries(root string) ([]GitStatusEntry, error) {
	data, err := CommandOutput(root, nil, "git", "status", "--porcelain=v1", "-z", "--untracked-files=all")
	if err != nil {
		return []GitStatusEntry{}, err
	}
	return parseStatusEntriesZ(string(data)), nil
}

func GitDiffNameStatus(root, base, head string) ([]GitStatusEntry, error) {
	data, err := CommandOutput(root, nil, "git", "diff", "--name-status", "-z", base+".."+head)
	if err != nil {
		return []GitStatusEntry{}, err
	}
	return parseNameStatusEntriesZ(string(data)), nil
}

func GitChangedPaths(root string) ([]string, error) {
	args := []string{"status", "--short", "--untracked-files=all"}
	out, err := CommandOutput(root, nil, "git", args...)
	if err != nil {
		data, diffErr := CommandOutput(root, nil, "git", "diff", "--name-only")
		if diffErr != nil {
			return []string{}, err
		}
		return normalizeGitLines(string(data)), nil
	}
	return parseGitStatusShort(string(out)), nil
}

func parseStatusEntries(output string) []GitStatusEntry {
	var entries []GitStatusEntry
	for _, line := range strings.Split(output, "\n") {
		if len(line) < 4 {
			continue
		}
		code := strings.TrimSpace(line[:2])
		if code == "" {
			continue
		}
		path := strings.TrimSpace(line[3:])
		entry := GitStatusEntry{Code: code}
		if strings.Contains(path, " -> ") {
			parts := strings.Split(path, " -> ")
			entry.OldPath = filepath.ToSlash(strings.TrimSpace(parts[0]))
			entry.Path = filepath.ToSlash(strings.TrimSpace(parts[len(parts)-1]))
		} else {
			entry.Path = filepath.ToSlash(path)
		}
		if entry.Path != "" {
			entries = append(entries, entry)
		}
	}
	return entries
}

func parseStatusEntriesZ(output string) []GitStatusEntry {
	var entries []GitStatusEntry
	fields := splitNUL(output)
	for i := 0; i < len(fields); i++ {
		field := fields[i]
		if len(field) < 4 {
			continue
		}
		code := strings.TrimSpace(field[:2])
		if code == "" {
			continue
		}
		entry := GitStatusEntry{
			Code: code,
			Path: filepath.ToSlash(field[3:]),
		}
		if (strings.HasPrefix(code, "R") || strings.HasPrefix(code, "C")) && i+1 < len(fields) {
			entry.OldPath = filepath.ToSlash(fields[i+1])
			i++
		}
		if entry.Path != "" {
			entries = append(entries, entry)
		}
	}
	return entries
}

func parseNameStatusEntries(output string) []GitStatusEntry {
	var entries []GitStatusEntry
	for _, line := range strings.Split(output, "\n") {
		line = strings.TrimSpace(line)
		if line == "" {
			continue
		}
		parts := strings.Split(line, "\t")
		if len(parts) < 2 {
			continue
		}
		entry := GitStatusEntry{
			Code: strings.TrimSpace(parts[0]),
			Path: filepath.ToSlash(strings.TrimSpace(parts[len(parts)-1])),
		}
		if len(parts) > 2 {
			entry.OldPath = filepath.ToSlash(strings.TrimSpace(parts[1]))
		}
		if entry.Code != "" && entry.Path != "" {
			entries = append(entries, entry)
		}
	}
	return entries
}

func parseNameStatusEntriesZ(output string) []GitStatusEntry {
	var entries []GitStatusEntry
	fields := splitNUL(output)
	for i := 0; i < len(fields); {
		code := strings.TrimSpace(fields[i])
		i++
		if code == "" || i >= len(fields) {
			continue
		}
		entry := GitStatusEntry{Code: code}
		if (strings.HasPrefix(code, "R") || strings.HasPrefix(code, "C")) && i+1 < len(fields) {
			entry.OldPath = filepath.ToSlash(fields[i])
			entry.Path = filepath.ToSlash(fields[i+1])
			i += 2
		} else {
			entry.Path = filepath.ToSlash(fields[i])
			i++
		}
		if entry.Path != "" {
			entries = append(entries, entry)
		}
	}
	return entries
}

func splitNUL(output string) []string {
	raw := strings.Split(output, "\x00")
	fields := make([]string, 0, len(raw))
	for _, field := range raw {
		if field != "" {
			fields = append(fields, field)
		}
	}
	return fields
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
