package main

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"time"
)

type ArtifactPruneRequest struct {
	Now   time.Time
	Limit int
}

func hasArtifactQuery(request ArtifactShowRequest) bool {
	return strings.TrimSpace(request.JSONPointer) != "" || strings.TrimSpace(request.Section) != "" || request.Limit > 0
}

func artifactQueryResult(canonicalPath string, raw []byte, request ArtifactShowRequest) (any, error) {
	switch {
	case strings.TrimSpace(request.JSONPointer) != "":
		return queryJSONPointer(raw, request.JSONPointer, request.Limit)
	case strings.TrimSpace(request.Section) != "":
		return queryMarkdownSection(raw, request.Section, request.Limit)
	case request.Limit > 0:
		return queryArtifactLimitOnly(canonicalPath, raw, request.Limit)
	default:
		return nil, fmt.Errorf("artifact query is empty")
	}
}

func queryJSONPointer(raw []byte, pointer string, limit int) (any, error) {
	var payload any
	if err := json.Unmarshal(raw, &payload); err != nil {
		return nil, fmt.Errorf("JSON artifact content is malformed")
	}
	value, err := resolveJSONPointer(payload, pointer)
	if err != nil {
		return nil, err
	}
	return limitQueryValue(value, limit), nil
}

func resolveJSONPointer(value any, pointer string) (any, error) {
	if pointer == "" {
		return value, nil
	}
	if pointer[0] != '/' {
		return nil, fmt.Errorf("json pointer %q must start with /", pointer)
	}
	current := value
	for _, segment := range strings.Split(pointer[1:], "/") {
		token := strings.ReplaceAll(strings.ReplaceAll(segment, "~1", "/"), "~0", "~")
		switch typed := current.(type) {
		case map[string]any:
			next, ok := typed[token]
			if !ok {
				return nil, fmt.Errorf("json pointer %q does not match the artifact", pointer)
			}
			current = next
		case []any:
			index, err := parsePointerIndex(token, len(typed))
			if err != nil {
				return nil, err
			}
			current = typed[index]
		default:
			return nil, fmt.Errorf("json pointer %q does not match the artifact", pointer)
		}
	}
	return current, nil
}

func parsePointerIndex(token string, length int) (int, error) {
	index := 0
	for _, char := range token {
		if char < '0' || char > '9' {
			return 0, fmt.Errorf("json pointer array index %q is invalid", token)
		}
		index = index*10 + int(char-'0')
	}
	if token == "" || index >= length {
		return 0, fmt.Errorf("json pointer array index %q is out of range", token)
	}
	return index, nil
}

func queryMarkdownSection(raw []byte, section string, limit int) (any, error) {
	lines := strings.Split(string(raw), "\n")
	target := strings.ToLower(strings.TrimSpace(section))
	start := -1
	level := 0
	for index, line := range lines {
		trimmed := strings.TrimSpace(line)
		if !strings.HasPrefix(trimmed, "#") {
			continue
		}
		hashes := len(trimmed) - len(strings.TrimLeft(trimmed, "#"))
		title := strings.ToLower(strings.TrimSpace(trimmed[hashes:]))
		if title == target {
			start = index
			level = hashes
			break
		}
	}
	if start < 0 {
		return nil, fmt.Errorf("markdown section %q was not found", section)
	}
	end := len(lines)
	for index := start + 1; index < len(lines); index++ {
		trimmed := strings.TrimSpace(lines[index])
		if !strings.HasPrefix(trimmed, "#") {
			continue
		}
		hashes := len(trimmed) - len(strings.TrimLeft(trimmed, "#"))
		if hashes <= level {
			end = index
			break
		}
	}
	sectionLines := append([]string(nil), lines[start:end]...)
	if limit > 0 {
		filtered := []string{}
		kept := 0
		for index, line := range sectionLines {
			if index == 0 {
				filtered = append(filtered, line)
				continue
			}
			if strings.TrimSpace(line) == "" {
				continue
			}
			if kept == limit {
				break
			}
			filtered = append(filtered, line)
			kept++
		}
		sectionLines = filtered
	}
	return strings.TrimSpace(strings.Join(sectionLines, "\n")), nil
}

func queryArtifactLimitOnly(canonicalPath string, raw []byte, limit int) (any, error) {
	switch strings.ToLower(filepath.Ext(canonicalPath)) {
	case ".json":
		var payload map[string]any
		if err := json.Unmarshal(raw, &payload); err != nil {
			return nil, fmt.Errorf("JSON artifact content is malformed")
		}
		keys := make([]string, 0, len(payload))
		for key := range payload {
			keys = append(keys, key)
		}
		sort.Strings(keys)
		if limit < len(keys) {
			keys = keys[:limit]
		}
		return keys, nil
	case ".md":
		headings := []string{}
		for _, line := range strings.Split(string(raw), "\n") {
			trimmed := strings.TrimSpace(line)
			if strings.HasPrefix(trimmed, "#") {
				headings = append(headings, trimmed)
				if len(headings) == limit {
					break
				}
			}
		}
		return headings, nil
	default:
		lines := strings.Split(string(raw), "\n")
		if limit < len(lines) {
			lines = lines[:limit]
		}
		return strings.Join(lines, "\n"), nil
	}
}

func limitQueryValue(value any, limit int) any {
	if limit <= 0 {
		return value
	}
	switch typed := value.(type) {
	case []any:
		if len(typed) > limit {
			return typed[:limit]
		}
		return typed
	case map[string]any:
		keys := make([]string, 0, len(typed))
		for key := range typed {
			keys = append(keys, key)
		}
		sort.Strings(keys)
		if len(keys) > limit {
			keys = keys[:limit]
		}
		limited := map[string]any{}
		for _, key := range keys {
			limited[key] = typed[key]
		}
		return limited
	case string:
		lines := strings.Split(typed, "\n")
		if len(lines) > limit {
			lines = lines[:limit]
		}
		return strings.Join(lines, "\n")
	default:
		return value
	}
}

func (service *ArtifactService) PruneLeases(request ArtifactPruneRequest) Envelope {
	now := request.Now.UTC()
	if now.IsZero() {
		now = nowUTC()
	}
	limit := request.Limit
	if limit <= 0 {
		limit = 100
	}
	leaseDir, err := secureProjectPath(service.projectRoot, filepath.ToSlash(filepath.Join(".specify", "runtime", "leases")))
	if err != nil {
		env := NewEnvelope("blocked", "artifact lease directory is unavailable")
		env.Blockers = append(env.Blockers, err.Error())
		return env
	}
	entries, err := os.ReadDir(leaseDir)
	if os.IsNotExist(err) {
		env := NewEnvelope("ok", "artifact leases pruned")
		env.Data["pruned"] = 0
		env.Data["scanned"] = 0
		return env
	}
	if err != nil {
		env := NewEnvelope("blocked", "artifact leases cannot be listed")
		env.Blockers = append(env.Blockers, err.Error())
		return env
	}
	pruned := 0
	scanned := 0
	for _, entry := range entries {
		if pruned >= limit {
			break
		}
		if entry.IsDir() || !strings.HasSuffix(strings.ToLower(entry.Name()), ".json") {
			continue
		}
		scanned++
		path := filepath.Join(leaseDir, entry.Name())
		raw, err := os.ReadFile(path)
		if err != nil {
			continue
		}
		var lease artifactLease
		if err := json.Unmarshal(raw, &lease); err != nil {
			continue
		}
		if lease.ExpiresAt == "" {
			continue
		}
		expiresAt, err := time.Parse(time.RFC3339, lease.ExpiresAt)
		if err != nil || expiresAt.After(now) {
			continue
		}
		if err := os.Remove(path); err == nil || os.IsNotExist(err) {
			pruned++
		}
	}
	env := NewEnvelope("ok", "artifact leases pruned")
	env.Data["pruned"] = pruned
	env.Data["scanned"] = scanned
	env.Data["limit"] = limit
	return env
}
