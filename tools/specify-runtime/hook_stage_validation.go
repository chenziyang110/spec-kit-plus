package main

import (
	"bufio"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"regexp"
	"slices"
	"strings"
	"time"
)

var hookResearchEvidenceRefRE = regexp.MustCompile(`research-evidence/(EVD-\d+)\.json`)
var hookConstitutionMetadataRE = regexp.MustCompile(`\*\*Version\*\*:\s*([0-9]+\.[0-9]+\.[0-9]+)\s*\|\s*\*\*Ratified\*\*:\s*([0-9]{4}-[0-9]{2}-[0-9]{2})\s*\|\s*\*\*Last Amended\*\*:\s*([0-9]{4}-[0-9]{2}-[0-9]{2})`)
var hookISODateRE = regexp.MustCompile(`^[0-9]{4}-[0-9]{2}-[0-9]{2}$`)

func validateHookClarifyArtifacts(featurePath string) error {
	checkpointsPath := filepath.Join(featurePath, "clarification", "checkpoints.ndjson")
	file, err := os.Open(checkpointsPath)
	if err != nil {
		return fmt.Errorf("clarification/checkpoints.ndjson is unavailable: %w", err)
	}
	defer file.Close()

	scanner := bufio.NewScanner(file)
	lineNumber := 0
	for scanner.Scan() {
		lineNumber++
		line := strings.TrimSpace(scanner.Text())
		if line == "" {
			continue
		}
		var payload map[string]any
		if err := json.Unmarshal([]byte(line), &payload); err != nil || payload == nil {
			return fmt.Errorf("clarification/checkpoints.ndjson line %d must be a JSON object", lineNumber)
		}
	}
	if err := scanner.Err(); err != nil {
		return fmt.Errorf("clarification/checkpoints.ndjson is unavailable: %w", err)
	}

	indexPath := filepath.Join(featurePath, "clarification", "evidence-index.json")
	index, err := readJSONObject(indexPath)
	if err != nil {
		return fmt.Errorf("clarification/evidence-index.json is unavailable: %w", err)
	}
	var walk func(any) error
	walk = func(node any) error {
		switch value := node.(type) {
		case map[string]any:
			if hookClarifyLaneAccepted(value) {
				disposition := strings.ToLower(strings.TrimSpace(hookAnyStringField(value, "disposition")))
				if disposition == "" {
					return fmt.Errorf("clarification/evidence-index.json accepted lanes must record disposition integrated, deferred, or blocked")
				}
				if !slices.Contains([]string{"integrated", "deferred", "blocked"}, disposition) {
					return fmt.Errorf("clarification/evidence-index.json accepted lane disposition must be integrated, deferred, or blocked")
				}
			}
			for _, child := range value {
				if err := walk(child); err != nil {
					return err
				}
			}
		case []any:
			for _, child := range value {
				if err := walk(child); err != nil {
					return err
				}
			}
		}
		return nil
	}
	if err := walk(index); err != nil {
		return err
	}
	return nil
}

func hookClarifyLaneAccepted(payload map[string]any) bool {
	if accepted, ok := payload["accepted"].(bool); ok && accepted {
		return true
	}
	return strings.EqualFold(strings.TrimSpace(hookAnyStringField(payload, "status")), "accepted")
}

func validateHookDeepResearchArtifacts(featurePath string) error {
	content, err := os.ReadFile(filepath.Join(featurePath, "deep-research.md"))
	if err != nil {
		return fmt.Errorf("deep-research.md is unavailable: %w", err)
	}
	text := string(content)
	if !regexp.MustCompile(`(?m)^\*\*Status\*\*:\s+\S`).MatchString(text) {
		return fmt.Errorf("deep-research.md must declare an explicit **Status** marker")
	}
	for _, heading := range []string{"## Feasibility Decision", "## Planning Handoff", "## Next Command"} {
		if !strings.Contains(text, heading) {
			return fmt.Errorf("deep-research.md must include %s", heading)
		}
	}
	seen := map[string]bool{}
	for _, match := range hookResearchEvidenceRefRE.FindAllStringSubmatch(text, -1) {
		relative := filepath.ToSlash(filepath.Join("research-evidence", match[1]+".json"))
		if seen[relative] {
			continue
		}
		seen[relative] = true
		if err := hookValidateJSONObject(filepath.Join(featurePath, filepath.FromSlash(relative)), relative); err != nil {
			return err
		}
	}
	return nil
}

func validateHookAnalyzeArtifacts(featurePath string) error {
	content, err := os.ReadFile(filepath.Join(featurePath, "workflow-state.md"))
	if err != nil {
		return fmt.Errorf("workflow-state.md is unavailable: %w", err)
	}
	checkpoint := hookWorkflowCheckpoint(string(content))
	if hookAnyStringField(checkpoint, "active_command") != "sp-analyze" {
		return fmt.Errorf("workflow-state.md active_command must be sp-analyze")
	}
	if hookAnyStringField(checkpoint, "phase_mode") != "analysis-only" {
		return fmt.Errorf("workflow-state.md phase_mode must be analysis-only")
	}
	analyzeGate := hookMarkdownBulletSection(string(content), "Analyze Gate")
	gateStatus := strings.ToLower(strings.TrimSpace(analyzeGate["gate_status"]))
	if gateStatus != "cleared" && gateStatus != "blocked" {
		return fmt.Errorf("workflow-state.md Analyze Gate gate_status must be cleared or blocked")
	}
	return nil
}

func validateHookConstitutionArtifacts(projectRoot string) error {
	content, err := os.ReadFile(filepath.Join(projectRoot, ".specify", "memory", "constitution.md"))
	if err != nil {
		return fmt.Errorf(".specify/memory/constitution.md is unavailable: %w", err)
	}
	text := string(content)
	matches := hookConstitutionMetadataRE.FindStringSubmatch(text)
	if matches == nil {
		return fmt.Errorf(".specify/memory/constitution.md must record Version, Ratified, and Last Amended metadata")
	}
	for _, date := range matches[2:] {
		if !hookISODateRE.MatchString(date) {
			return fmt.Errorf(".specify/memory/constitution.md metadata dates must use YYYY-MM-DD")
		}
		if _, err := time.Parse("2006-01-02", date); err != nil {
			return fmt.Errorf(".specify/memory/constitution.md metadata date %s is invalid", date)
		}
	}
	principleCount := 0
	for _, line := range strings.Split(text, "\n") {
		if strings.HasPrefix(strings.TrimSpace(line), "### ") {
			principleCount++
		}
	}
	if principleCount == 0 {
		return fmt.Errorf(".specify/memory/constitution.md must contain at least one principle heading")
	}
	return nil
}

func validateHookImplementArtifacts(projectRoot, featurePath string) error {
	handoffPath := filepath.Join(featurePath, "implementation-handoff.json")
	handoff, err := readJSONObject(handoffPath)
	if err != nil {
		return fmt.Errorf("implementation-handoff.json is unavailable: %w", err)
	}
	if err := validateCanonicalImplementationHandoff(projectRoot, featurePath, handoff); err != nil {
		return fmt.Errorf("implementation-handoff.json is invalid: %w", err)
	}
	// Closeout already required a passing resume-audit. Once handoff is
	// ready_for_review and validates, it is the implement completion authority
	// for complete-stage. Re-running live resume-audit here races fingerprint
	// drift from post-closeout state-file patches (workflow-state.md, etc.).
	if strings.TrimSpace(fmt.Sprint(handoff["status"])) == "ready_for_review" {
		return nil
	}
	audit := auditImplementResume(projectRoot, featurePath)
	if strings.TrimSpace(fmt.Sprint(audit["status"])) != "pass" {
		gaps := audit["open_gaps"]
		return fmt.Errorf("implement resume audit must pass before implement artifacts are complete (status=%v open_gaps=%v); run specify-runtime implement resume-audit --feature-dir <feature> --format json", audit["status"], gaps)
	}
	if audit["trusted_terminal_state"] != true {
		return fmt.Errorf("implement resume audit must trust the terminal state before implement artifacts are complete; open_gaps=%v", audit["open_gaps"])
	}
	return nil
}

func hookMarkdownBulletSection(content, section string) map[string]string {
	lines := strings.Split(content, "\n")
	target := "## " + strings.TrimSpace(section)
	inside := false
	values := map[string]string{}
	for _, raw := range lines {
		line := strings.TrimSpace(raw)
		if strings.HasPrefix(line, "## ") {
			if line == target {
				inside = true
				continue
			}
			if inside {
				break
			}
		}
		if !inside || !strings.HasPrefix(line, "- ") || !strings.Contains(line, ":") {
			continue
		}
		parts := strings.SplitN(strings.TrimPrefix(line, "- "), ":", 2)
		values[strings.ToLower(strings.TrimSpace(parts[0]))] = strings.TrimSpace(parts[1])
	}
	return values
}
