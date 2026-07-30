package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"regexp"
	"strings"
	"unicode/utf8"

	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/filelock"
)

const maxChecklistInputBytes = 4 * 1024 * 1024

var (
	checklistIDPattern         = regexp.MustCompile(`(?m)^- \[[ xX]\] CHK([0-9]{3,})\b`)
	checklistSuppliedIDPattern = regexp.MustCompile(`(?i)^CHK[0-9]+\b`)
)

type ArtifactChecklistRequest struct {
	Path      string
	InputJSON []byte
}

type artifactChecklistInput struct {
	Title      string                      `json:"title"`
	Purpose    string                      `json:"purpose"`
	Feature    string                      `json:"feature"`
	Categories []artifactChecklistCategory `json:"categories"`
}

type artifactChecklistCategory struct {
	Heading string   `json:"heading"`
	Items   []string `json:"items"`
}

func (service *ArtifactService) UpsertChecklist(request ArtifactChecklistRequest) Envelope {
	canonicalPath, err := registeredArtifactPath(request.Path)
	if err != nil {
		return invalidChecklist("checklist path is invalid", err)
	}
	metadata, ok := LookupArtifactType(canonicalPath)
	if !ok || metadata.TypeID != "feature-checklist" || !artifactTypeAllows(metadata, "checklist") {
		return invalidChecklist("checklist path is not registered", fmt.Errorf("%s is not a feature checklist path", canonicalPath))
	}
	input, err := decodeArtifactChecklistInput(request.InputJSON)
	if err != nil {
		return invalidChecklist("checklist input is invalid", err)
	}
	target, err := secureProjectPath(service.projectRoot, canonicalPath)
	if err != nil {
		return blockedChecklist("checklist path safety check failed", err)
	}
	lockPath, err := service.artifactLockPath(canonicalPath)
	if err != nil {
		return blockedChecklist("checklist lock path is unavailable", err)
	}
	releaseLock, err := filelock.Acquire(lockPath)
	if err != nil {
		return blockedChecklist("checklist lock cannot be acquired", err)
	}
	defer releaseLock()

	target, err = secureProjectPath(service.projectRoot, canonicalPath)
	if err != nil {
		return blockedChecklist("checklist path safety check failed", err)
	}
	existing, readErr := os.ReadFile(target)
	created := os.IsNotExist(readErr)
	if readErr != nil && !created {
		return blockedChecklist("checklist cannot be read", readErr)
	}
	if created && (input.Title == "" || input.Purpose == "" || input.Feature == "") {
		return invalidChecklist("new checklist metadata is incomplete", fmt.Errorf("title, purpose, and feature are required when creating a checklist"))
	}

	nextID, err := nextChecklistID(existing)
	if err != nil {
		return invalidChecklist("existing checklist IDs are invalid", err)
	}
	categoryContent, itemCount := renderChecklistCategories(input.Categories, nextID)
	var content []byte
	if created {
		content, err = service.renderNewChecklist(input, categoryContent)
		if err != nil {
			return blockedChecklist("checklist template cannot be rendered", err)
		}
	} else {
		content = []byte(strings.TrimRight(string(existing), "\r\n") + "\n\n" + categoryContent + "\n")
	}
	if err := os.MkdirAll(filepath.Dir(target), 0o755); err != nil {
		return blockedChecklist("checklist parent cannot be created", err)
	}
	target, err = secureProjectPath(service.projectRoot, canonicalPath)
	if err != nil {
		return blockedChecklist("checklist path safety check failed", err)
	}
	if err := atomicWriteFile(target, content, 0o644); err != nil {
		return blockedChecklist("checklist cannot be written", err)
	}

	env := NewEnvelope("ok", "checklist rendered through the artifact control plane")
	env.Data["canonical_path"] = canonicalPath
	env.Data["created"] = created
	env.Data["first_item_id"] = fmt.Sprintf("CHK%03d", nextID)
	env.Data["last_item_id"] = fmt.Sprintf("CHK%03d", nextID+itemCount-1)
	env.Data["item_count"] = itemCount
	env.ShowArgv = []string{"specify-runtime", "artifact", "show", "--path", canonicalPath, "--view", "summary"}
	return env
}

func decodeArtifactChecklistInput(raw []byte) (artifactChecklistInput, error) {
	if len(raw) == 0 {
		return artifactChecklistInput{}, fmt.Errorf("--input-json must not be empty")
	}
	if len(raw) > maxChecklistInputBytes {
		return artifactChecklistInput{}, fmt.Errorf("--input-json exceeds %d bytes", maxChecklistInputBytes)
	}
	decoder := json.NewDecoder(bytes.NewReader(raw))
	decoder.DisallowUnknownFields()
	var input artifactChecklistInput
	if err := decoder.Decode(&input); err != nil {
		return artifactChecklistInput{}, fmt.Errorf("--input-json must be one checklist object: %w", err)
	}
	if err := decoder.Decode(&struct{}{}); err != io.EOF {
		if err == nil {
			err = fmt.Errorf("multiple JSON values are not allowed")
		}
		return artifactChecklistInput{}, fmt.Errorf("--input-json must be one checklist object: %w", err)
	}
	for label, value := range map[string]string{"title": input.Title, "purpose": input.Purpose, "feature": input.Feature} {
		normalized, err := checklistSingleLine(value, label, 1000)
		if err != nil {
			return artifactChecklistInput{}, err
		}
		switch label {
		case "title":
			input.Title = normalized
		case "purpose":
			input.Purpose = normalized
		case "feature":
			input.Feature = normalized
		}
	}
	if len(input.Categories) == 0 || len(input.Categories) > 40 {
		return artifactChecklistInput{}, fmt.Errorf("categories must contain between 1 and 40 entries")
	}
	totalItems := 0
	seenHeadings := map[string]bool{}
	for categoryIndex := range input.Categories {
		category := &input.Categories[categoryIndex]
		heading, err := checklistSingleLine(category.Heading, "category heading", 200)
		if err != nil || heading == "" {
			if err == nil {
				err = fmt.Errorf("category heading must not be empty")
			}
			return artifactChecklistInput{}, err
		}
		if strings.HasPrefix(heading, "#") {
			return artifactChecklistInput{}, fmt.Errorf("category heading must not include Markdown heading markers")
		}
		key := strings.ToLower(heading)
		if seenHeadings[key] {
			return artifactChecklistInput{}, fmt.Errorf("category heading %q is duplicated", heading)
		}
		seenHeadings[key] = true
		category.Heading = heading
		if len(category.Items) == 0 {
			return artifactChecklistInput{}, fmt.Errorf("category %q must include at least one item", heading)
		}
		for itemIndex := range category.Items {
			item, err := checklistSingleLine(category.Items[itemIndex], "checklist item", 2000)
			if err != nil || item == "" {
				if err == nil {
					err = fmt.Errorf("checklist item must not be empty")
				}
				return artifactChecklistInput{}, err
			}
			if strings.HasPrefix(item, "- [") || checklistSuppliedIDPattern.MatchString(item) {
				return artifactChecklistInput{}, fmt.Errorf("checklist items must omit checkbox and CHK identifiers; the CLI assigns them")
			}
			category.Items[itemIndex] = item
			totalItems++
		}
	}
	if totalItems > 200 {
		return artifactChecklistInput{}, fmt.Errorf("checklist input may contain at most 200 items")
	}
	return input, nil
}

func checklistSingleLine(value, label string, maxBytes int) (string, error) {
	if !utf8.ValidString(value) {
		return "", fmt.Errorf("%s must be valid UTF-8", label)
	}
	value = strings.TrimSpace(value)
	if len(value) > maxBytes {
		return "", fmt.Errorf("%s exceeds %d bytes", label, maxBytes)
	}
	if strings.ContainsAny(value, "\r\n") {
		return "", fmt.Errorf("%s must be a single line", label)
	}
	for _, char := range value {
		if char < 32 || char == 127 {
			return "", fmt.Errorf("%s contains a control character", label)
		}
	}
	return value, nil
}

func nextChecklistID(content []byte) (int, error) {
	maxID := 0
	seen := map[string]bool{}
	for _, match := range checklistIDPattern.FindAllSubmatch(content, -1) {
		id := string(match[1])
		if seen[id] {
			return 0, fmt.Errorf("CHK%s appears more than once", id)
		}
		seen[id] = true
		var parsed int
		if _, err := fmt.Sscanf(id, "%d", &parsed); err != nil {
			return 0, fmt.Errorf("CHK%s is invalid", id)
		}
		if parsed > maxID {
			maxID = parsed
		}
	}
	return maxID + 1, nil
}

func renderChecklistCategories(categories []artifactChecklistCategory, firstID int) (string, int) {
	var output strings.Builder
	nextID := firstID
	for categoryIndex, category := range categories {
		if categoryIndex > 0 {
			output.WriteString("\n")
		}
		fmt.Fprintf(&output, "## %s\n\n", category.Heading)
		for _, item := range category.Items {
			fmt.Fprintf(&output, "- [ ] CHK%03d %s\n", nextID, item)
			nextID++
		}
	}
	return strings.TrimRight(output.String(), "\n"), nextID - firstID
}

func (service *ArtifactService) renderNewChecklist(input artifactChecklistInput, categories string) ([]byte, error) {
	templatePath, err := secureProjectPath(service.projectRoot, ".specify/templates/artifacts/checklist.md")
	if err != nil {
		return nil, err
	}
	template, err := os.ReadFile(templatePath)
	if err != nil {
		return nil, err
	}
	content := string(template)
	for _, marker := range []string{"{{title}}", "{{purpose}}", "{{created}}", "{{feature}}", "{{categories}}"} {
		if strings.Count(content, marker) != 1 {
			return nil, fmt.Errorf("checklist template must contain %s exactly once", marker)
		}
	}
	replacements := map[string]string{
		"{{title}}":      input.Title,
		"{{purpose}}":    input.Purpose,
		"{{created}}":    nowUTC().Format("2006-01-02"),
		"{{feature}}":    input.Feature,
		"{{categories}}": categories,
	}
	for marker, value := range replacements {
		content = strings.Replace(content, marker, value, 1)
	}
	return []byte(strings.TrimRight(content, "\r\n") + "\n"), nil
}

func invalidChecklist(summary string, err error) Envelope {
	env := NewEnvelope("invalid", summary)
	env.Blockers = append(env.Blockers, err.Error())
	return env
}

func blockedChecklist(summary string, err error) Envelope {
	env := NewEnvelope("blocked", summary)
	env.Blockers = append(env.Blockers, err.Error())
	return env
}
