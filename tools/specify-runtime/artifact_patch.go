package main

import (
	"encoding/json"
	"fmt"
	"os"
	"sort"
	"strings"

	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/filelock"
)

type ArtifactPatchRequest struct {
	LeaseID     string
	JSONPointer string
	Value       any
	Section     string
	Content     string
	Frontmatter map[string]any
	Heading     string
	NewHeading  string
	Preamble    *string
	AppendJSON  any
	Append      bool
}

func (service *ArtifactService) Patch(request ArtifactPatchRequest) Envelope {
	lease, claimPath, err := service.claimLease(request.LeaseID)
	if err != nil {
		env := NewEnvelope("blocked", "artifact lease is unavailable")
		env.Blockers = append(env.Blockers, err.Error())
		return env
	}
	metadata, ok := LookupArtifactType(lease.CanonicalPath)
	if !ok || !artifactTypeAllows(metadata, "patch") {
		env := NewEnvelope("invalid", "workflow artifact is not patchable through the generic CLI")
		if ok {
			env.Blockers = append(env.Blockers, fmt.Sprintf("%s may be changed only through %s", lease.CanonicalPath, metadata.Owner))
			env.Data["owner"] = metadata.Owner
		}
		return service.finishLease(lease, claimPath, env)
	}
	if err := validateArtifactPatchRequest(lease.CanonicalPath, request); err != nil {
		return service.finishLease(lease, claimPath, artifactPatchError("invalid", err))
	}
	target, err := secureProjectPath(service.projectRoot, lease.CanonicalPath)
	if err != nil {
		return service.finishLease(lease, claimPath, artifactPatchError("blocked", err))
	}
	lockPath, err := service.artifactLockPath(lease.CanonicalPath)
	if err != nil {
		return service.finishLease(lease, claimPath, artifactPatchError("blocked", err))
	}
	release, err := filelock.Acquire(lockPath)
	if err != nil {
		return service.finishLease(lease, claimPath, artifactPatchError("error", err))
	}
	defer release()
	currentExists, currentSHA256, err := snapshotArtifactTarget(target)
	if err != nil || currentExists != lease.TargetExists || currentSHA256 != lease.TargetSHA256 {
		if err == nil {
			err = fmt.Errorf("artifact target changed after lease preparation")
		}
		env := artifactPatchError("blocked", err)
		env.NextArgv = []string{"specify-runtime", "artifact", "prepare", "--path", lease.CanonicalPath}
		return service.finishLease(lease, claimPath, env)
	}
	if !currentExists {
		return service.finishLease(lease, claimPath, artifactPatchError("blocked", fmt.Errorf("patch requires an existing artifact; scaffold or submit it first")))
	}
	raw, err := os.ReadFile(target)
	if err != nil {
		return service.finishLease(lease, claimPath, artifactPatchError("error", err))
	}
	updated, err := patchArtifactContent(raw, request)
	if err != nil {
		return service.finishLease(lease, claimPath, artifactPatchError("invalid", err))
	}
	if err := validateArtifactContent(lease.CanonicalPath, updated); err != nil {
		return service.finishLease(lease, claimPath, artifactPatchError("invalid", err))
	}
	if err := atomicWriteFile(target, updated, 0o644); err != nil {
		return service.finishLease(lease, claimPath, artifactPatchError("error", err))
	}
	env := NewEnvelope("ok", "canonical artifact patched")
	env.Data["canonical_path"] = lease.CanonicalPath
	env.Data["bytes"] = len(updated)
	env.ShowArgv = []string{"specify-runtime", "artifact", "show", "--path", lease.CanonicalPath, "--view", "summary"}
	return service.finishLease(lease, claimPath, env)
}

func validateArtifactPatchRequest(canonicalPath string, request ArtifactPatchRequest) error {
	modes := 0
	if strings.TrimSpace(request.JSONPointer) != "" {
		modes++
	}
	if strings.TrimSpace(request.Section) != "" {
		modes++
	}
	if request.Frontmatter != nil {
		modes++
	}
	if strings.TrimSpace(request.Heading) != "" || strings.TrimSpace(request.NewHeading) != "" {
		modes++
		if strings.TrimSpace(request.Heading) == "" || strings.TrimSpace(request.NewHeading) == "" {
			return fmt.Errorf("heading rename requires both current and new heading text")
		}
	}
	if request.Preamble != nil {
		modes++
	}
	if request.Append {
		modes++
	}
	if modes != 1 {
		return fmt.Errorf("artifact patch requires exactly one patch operation")
	}
	if request.Append {
		lowerPath := strings.ToLower(canonicalPath)
		if !strings.HasSuffix(lowerPath, ".jsonl") && !strings.HasSuffix(lowerPath, ".ndjson") {
			return fmt.Errorf("JSON-line append requires a JSONL or NDJSON artifact")
		}
	}
	return nil
}

func artifactPatchError(status string, err error) Envelope {
	env := NewEnvelope(status, "artifact patch failed")
	if err != nil {
		env.Blockers = append(env.Blockers, err.Error())
	}
	return env
}

func patchArtifactContent(raw []byte, request ArtifactPatchRequest) ([]byte, error) {
	switch {
	case strings.TrimSpace(request.JSONPointer) != "":
		var payload any
		if err := json.Unmarshal(raw, &payload); err != nil {
			return nil, fmt.Errorf("JSON artifact content is malformed")
		}
		if err := setJSONPointer(payload, request.JSONPointer, request.Value); err != nil {
			return nil, err
		}
		updated, err := json.MarshalIndent(payload, "", "  ")
		return append(updated, '\n'), err
	case strings.TrimSpace(request.Section) != "":
		return replaceMarkdownSection(raw, request.Section, request.Content)
	case request.Frontmatter != nil:
		return patchMarkdownFrontmatter(raw, request.Frontmatter)
	case strings.TrimSpace(request.Heading) != "":
		return renameMarkdownHeading(raw, request.Heading, request.NewHeading)
	case request.Preamble != nil:
		return replaceMarkdownPreamble(raw, *request.Preamble)
	case request.Append:
		line, err := json.Marshal(request.AppendJSON)
		if err != nil {
			return nil, err
		}
		updated := append([]byte(nil), raw...)
		if len(updated) > 0 && updated[len(updated)-1] != '\n' {
			updated = append(updated, '\n')
		}
		updated = append(updated, line...)
		return append(updated, '\n'), nil
	default:
		return nil, fmt.Errorf("artifact patch requires one patch operation")
	}
}

func renameMarkdownHeading(raw []byte, current, replacement string) ([]byte, error) {
	current = strings.TrimSpace(current)
	replacement = strings.TrimSpace(replacement)
	if current == "" || replacement == "" {
		return nil, fmt.Errorf("heading rename requires non-empty current and new heading text")
	}
	if strings.ContainsAny(current, "\r\n") || strings.ContainsAny(replacement, "\r\n") {
		return nil, fmt.Errorf("heading text must be one line")
	}
	if strings.HasPrefix(replacement, "#") {
		return nil, fmt.Errorf("new heading text must omit Markdown hash markers")
	}

	lines := strings.Split(strings.ReplaceAll(string(raw), "\r\n", "\n"), "\n")
	matched := -1
	for index, line := range lines {
		trimmed := strings.TrimSpace(line)
		if !strings.HasPrefix(trimmed, "#") {
			continue
		}
		hashes := len(trimmed) - len(strings.TrimLeft(trimmed, "#"))
		if hashes == 0 || hashes > 6 || len(trimmed) == hashes || trimmed[hashes] != ' ' {
			continue
		}
		label := strings.TrimSpace(trimmed[hashes:])
		if !strings.EqualFold(label, current) {
			continue
		}
		if matched >= 0 {
			return nil, fmt.Errorf("Markdown heading %q is ambiguous", current)
		}
		matched = index
		indent := line[:len(line)-len(strings.TrimLeft(line, " \t"))]
		lines[index] = indent + strings.Repeat("#", hashes) + " " + replacement
	}
	if matched < 0 {
		return nil, fmt.Errorf("Markdown heading %q was not found", current)
	}
	for len(lines) > 0 && lines[len(lines)-1] == "" {
		lines = lines[:len(lines)-1]
	}
	return []byte(strings.Join(lines, "\n") + "\n"), nil
}

func replaceMarkdownPreamble(raw []byte, preamble string) ([]byte, error) {
	text := strings.ReplaceAll(string(raw), "\r\n", "\n")
	lines := strings.Split(text, "\n")
	firstHeading := -1
	for index, line := range lines {
		trimmed := strings.TrimSpace(line)
		if strings.HasPrefix(trimmed, "# ") {
			firstHeading = index
			break
		}
	}
	if firstHeading < 0 {
		return nil, fmt.Errorf("Markdown document has no level-1 heading")
	}
	preamble = strings.TrimSpace(strings.ReplaceAll(preamble, "\r\n", "\n"))
	for _, line := range strings.Split(preamble, "\n") {
		if strings.HasPrefix(strings.TrimSpace(line), "#") {
			return nil, fmt.Errorf("Markdown preamble must not contain headings")
		}
	}
	body := strings.TrimLeft(strings.Join(lines[firstHeading:], "\n"), "\n")
	if preamble == "" {
		return []byte(strings.TrimRight(body, "\n") + "\n"), nil
	}
	return []byte(preamble + "\n\n" + strings.TrimRight(body, "\n") + "\n"), nil
}

func patchMarkdownFrontmatter(raw []byte, values map[string]any) ([]byte, error) {
	text := strings.ReplaceAll(string(raw), "\r\n", "\n")
	lines := strings.Split(text, "\n")
	if len(lines) < 3 || strings.TrimSpace(lines[0]) != "---" {
		return nil, fmt.Errorf("markdown artifact has no frontmatter")
	}
	end := -1
	for index := 1; index < len(lines); index++ {
		if strings.TrimSpace(lines[index]) == "---" {
			end = index
			break
		}
	}
	if end < 0 {
		return nil, fmt.Errorf("markdown frontmatter is not terminated")
	}
	keys := make([]string, 0, len(values))
	for key := range values {
		if key == "" || key != strings.TrimSpace(key) || strings.ContainsAny(key, ":\r\n") {
			return nil, fmt.Errorf("frontmatter key %q is invalid", key)
		}
		keys = append(keys, key)
	}
	sort.Strings(keys)
	for _, key := range keys {
		value, err := frontmatterScalar(values[key])
		if err != nil {
			return nil, fmt.Errorf("frontmatter %s: %w", key, err)
		}
		replaced := false
		prefix := key + ":"
		for index := 1; index < end; index++ {
			if strings.HasPrefix(lines[index], " ") || strings.HasPrefix(lines[index], "\t") {
				continue
			}
			if strings.HasPrefix(lines[index], prefix) {
				lines[index] = prefix + " " + value
				replaced = true
				break
			}
		}
		if !replaced {
			lines = append(lines[:end], append([]string{prefix + " " + value}, lines[end:]...)...)
			end++
		}
	}
	for len(lines) > 0 && lines[len(lines)-1] == "" {
		lines = lines[:len(lines)-1]
	}
	return []byte(strings.Join(lines, "\n") + "\n"), nil
}

func frontmatterScalar(value any) (string, error) {
	switch value.(type) {
	case string, bool, float64, nil:
		raw, err := json.Marshal(value)
		return string(raw), err
	default:
		return "", fmt.Errorf("value must be a scalar string, boolean, number, or null")
	}
}

func setJSONPointer(payload any, pointer string, value any) error {
	if pointer == "" || !strings.HasPrefix(pointer, "/") {
		return fmt.Errorf("json pointer must identify a non-root object field")
	}
	tokens := strings.Split(pointer[1:], "/")
	current := payload
	for index, segment := range tokens {
		token := strings.ReplaceAll(strings.ReplaceAll(segment, "~1", "/"), "~0", "~")
		object, ok := current.(map[string]any)
		if !ok {
			return fmt.Errorf("json pointer %q crosses a non-object value", pointer)
		}
		if index == len(tokens)-1 {
			object[token] = value
			return nil
		}
		next, exists := object[token]
		if !exists {
			next = map[string]any{}
			object[token] = next
		}
		current = next
	}
	return nil
}

func replaceMarkdownSection(raw []byte, section, content string) ([]byte, error) {
	lines := strings.Split(strings.ReplaceAll(string(raw), "\r\n", "\n"), "\n")
	target := strings.ToLower(strings.TrimSpace(section))
	start, end, level := -1, len(lines), 0
	for index, line := range lines {
		trimmed := strings.TrimSpace(line)
		if !strings.HasPrefix(trimmed, "#") {
			continue
		}
		hashes := len(trimmed) - len(strings.TrimLeft(trimmed, "#"))
		if start < 0 && strings.ToLower(strings.TrimSpace(trimmed[hashes:])) == target {
			start, level = index, hashes
			continue
		}
		if start >= 0 && hashes <= level {
			end = index
			break
		}
	}
	if start < 0 {
		return nil, fmt.Errorf("markdown section %q was not found", section)
	}
	body := strings.TrimSpace(content)
	replacement := []string{lines[start], ""}
	if body != "" {
		replacement = append(replacement, strings.Split(body, "\n")...)
	}
	replacement = append(replacement, "")
	updated := append([]string{}, lines[:start]...)
	updated = append(updated, replacement...)
	updated = append(updated, lines[end:]...)
	for len(updated) > 0 && updated[len(updated)-1] == "" {
		updated = updated[:len(updated)-1]
	}
	return []byte(strings.Join(updated, "\n") + "\n"), nil
}
