package runtime

import (
	"bytes"
	"os/exec"
	"path/filepath"
	"strings"
)

type GitStatusEntry struct {
	Code    string
	Path    string
	OldPath string
}

func GitAvailable(root string) bool {
	cmd := exec.Command("git", "rev-parse", "--is-inside-work-tree")
	cmd.Dir = root
	data, err := cmd.Output()
	return err == nil && strings.TrimSpace(string(data)) == "true"
}

func GitHead(root string) (string, error) {
	cmd := exec.Command("git", "rev-parse", "HEAD")
	cmd.Dir = root
	data, err := cmd.Output()
	if err != nil {
		return "", err
	}
	return strings.TrimSpace(string(data)), nil
}

func GitBranch(root string) (string, error) {
	cmd := exec.Command("git", "branch", "--show-current")
	cmd.Dir = root
	data, err := cmd.Output()
	if err != nil {
		return "", err
	}
	return strings.TrimSpace(string(data)), nil
}

func GitStatusEntries(root string) ([]GitStatusEntry, error) {
	cmd := exec.Command("git", "status", "--porcelain=v1", "-z", "--untracked-files=all")
	cmd.Dir = root
	data, err := cmd.Output()
	if err != nil {
		return []GitStatusEntry{}, err
	}
	return parseStatusEntriesZ(string(data)), nil
}

func GitDiffNameStatus(root, base, head string) ([]GitStatusEntry, error) {
	cmd := exec.Command("git", "diff", "--name-status", "-z", base+".."+head)
	cmd.Dir = root
	data, err := cmd.Output()
	if err != nil {
		return []GitStatusEntry{}, err
	}
	return parseNameStatusEntriesZ(string(data)), nil
}

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
