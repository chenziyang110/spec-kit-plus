package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"unicode/utf8"
)

type ArtifactScaffoldRequest struct {
	Kind      string
	Path      string
	Variables map[string]any
}

type artifactScaffoldKind struct {
	Kind                  string
	TemplatePath          string
	AllowedPaths          [][]string
	AgentFillRequired     []string
	FillTargets           map[string]map[string]string
	EstimatedTokenSavings int
}

var artifactScaffoldKinds = map[string]artifactScaffoldKind{
	"quick-status": {
		Kind:         "quick-status",
		TemplatePath: "artifacts/quick-status.md",
		AllowedPaths: [][]string{{".planning", "quick", "*", "STATUS.md"}},
		AgentFillRequired: []string{
			"current_focus",
		},
		FillTargets: map[string]map[string]string{
			"discussion_handoff_source": {"type": "markdown_anchor", "anchor": "agent-fill:discussion_handoff_source"},
			"current_focus":             {"type": "markdown_anchor", "anchor": "agent-fill:current_focus"},
			"execution_intent":          {"type": "markdown_anchor", "anchor": "agent-fill:execution_intent"},
			"understanding_checkpoint":  {"type": "markdown_anchor", "anchor": "agent-fill:understanding_checkpoint"},
			"execution":                 {"type": "markdown_anchor", "anchor": "agent-fill:execution"},
			"validation":                {"type": "markdown_anchor", "anchor": "agent-fill:validation"},
			"summary_pointer":           {"type": "markdown_anchor", "anchor": "agent-fill:summary_pointer"},
			"senior_consequence_analysis": {
				"type": "markdown_anchor", "anchor": "agent-fill:senior_consequence_analysis",
			},
		},
		EstimatedTokenSavings: 400,
	},
	"plan-contract": {
		Kind:         "plan-contract",
		TemplatePath: "plan-contract-template.json",
		AllowedPaths: [][]string{
			{"specs", "*", "plan-contract.json"},
			{"specs", "*", "plan", "plan-contract.json"},
			{".specify", "features", "*", "plan-contract.json"},
			{".specify", "features", "*", "plan", "plan-contract.json"},
		},
		AgentFillRequired: []string{
			"intent", "complexity_level", "architecture_decisions", "interface_map", "acceptance_refs",
		},
		FillTargets: map[string]map[string]string{
			"intent":                      {"type": "json_pointer", "pointer": "/intent"},
			"complexity_level":            {"type": "json_pointer", "pointer": "/complexity_level"},
			"architecture_decisions":      {"type": "json_pointer", "pointer": "/architecture_decisions"},
			"interface_map":               {"type": "json_pointer", "pointer": "/interface_map"},
			"acceptance_refs":             {"type": "json_pointer", "pointer": "/acceptance_refs"},
			"capability_operations":       {"type": "json_pointer", "pointer": "/capability_operations"},
			"must_preserve_refs":          {"type": "json_pointer", "pointer": "/must_preserve_refs"},
			"consequence_obligation_refs": {"type": "json_pointer", "pointer": "/consequence_obligation_refs"},
			"review_risk_notes":           {"type": "json_pointer", "pointer": "/review_risk_notes"},
		},
		EstimatedTokenSavings: 362,
	},
}

func (service *ArtifactService) Scaffold(request ArtifactScaffoldRequest) Envelope {
	kind, exists := artifactScaffoldKinds[strings.TrimSpace(request.Kind)]
	if !exists {
		env := NewEnvelope("invalid", "artifact scaffold kind is invalid")
		env.Blockers = append(env.Blockers, fmt.Sprintf("unknown artifact scaffold kind %q", request.Kind))
		return env
	}
	canonicalPath, err := registeredArtifactPath(request.Path)
	if err != nil || !matchesScaffoldPath(canonicalPath, kind.AllowedPaths) {
		env := NewEnvelope("invalid", "artifact scaffold path is invalid")
		if err != nil {
			env.Blockers = append(env.Blockers, err.Error())
		} else {
			env.Blockers = append(env.Blockers, "output path is not registered for scaffold kind "+kind.Kind)
		}
		return env
	}
	if err := rejectUnsafeReadiness(request.Variables); err != nil {
		env := NewEnvelope("invalid", "artifact scaffold variables are invalid")
		env.Blockers = append(env.Blockers, err.Error())
		return env
	}

	templateRelative := filepath.ToSlash(filepath.Join(".specify", "templates", filepath.FromSlash(kind.TemplatePath)))
	templatePath, err := secureProjectPath(service.projectRoot, templateRelative)
	if err != nil {
		return blockedScaffold("artifact scaffold template path is unsafe", err)
	}
	template, err := os.ReadFile(templatePath)
	if err != nil {
		return blockedScaffold("artifact scaffold template is unavailable", err)
	}
	rendered, err := renderArtifactScaffold(kind, template, request.Variables)
	if err != nil {
		env := NewEnvelope("invalid", "artifact scaffold template is invalid")
		env.Blockers = append(env.Blockers, err.Error())
		return env
	}

	target, err := secureProjectPath(service.projectRoot, canonicalPath)
	if err != nil {
		return blockedScaffold("artifact scaffold path safety check failed", err)
	}
	if _, err := os.Lstat(target); err == nil {
		env := NewEnvelope("blocked", "artifact scaffold target already exists")
		env.Blockers = append(env.Blockers, canonicalPath+" already exists; scaffolds are create-only")
		return env
	} else if !os.IsNotExist(err) {
		return blockedScaffold("artifact scaffold target cannot be inspected", err)
	}
	if err := os.MkdirAll(filepath.Dir(target), 0o755); err != nil {
		return blockedScaffold("artifact scaffold parent cannot be created", err)
	}
	target, err = secureProjectPath(service.projectRoot, canonicalPath)
	if err != nil {
		return blockedScaffold("artifact scaffold path safety check failed", err)
	}
	if err := writeCreateOnly(target, rendered); err != nil {
		if os.IsExist(err) {
			env := NewEnvelope("blocked", "artifact scaffold target already exists")
			env.Blockers = append(env.Blockers, canonicalPath+" already exists; scaffolds are create-only")
			return env
		}
		return blockedScaffold("artifact scaffold cannot be written", err)
	}

	env := NewEnvelope("ok", "artifact scaffold created")
	env.Data["agent_fill_required"] = append([]string(nil), kind.AgentFillRequired...)
	env.Data["canonical_path"] = canonicalPath
	env.Data["estimated_token_savings"] = kind.EstimatedTokenSavings
	env.Data["fill_targets"] = kind.FillTargets
	env.Data["kind"] = kind.Kind
	env.ShowArgv = []string{"specify-runtime", "artifact", "show", "--path", canonicalPath, "--view", "summary"}
	return env
}

func ArtifactScaffoldCatalog() Envelope {
	env := NewEnvelope("ok", "artifact scaffold catalog")
	for _, name := range []string{"plan-contract", "quick-status"} {
		kind := artifactScaffoldKinds[name]
		env.Items = append(env.Items, map[string]any{
			"agent_fill_required":     kind.AgentFillRequired,
			"estimated_token_savings": kind.EstimatedTokenSavings,
			"fill_targets":            kind.FillTargets,
			"kind":                    kind.Kind,
		})
	}
	return env
}

func blockedScaffold(summary string, err error) Envelope {
	env := NewEnvelope("blocked", summary)
	env.Blockers = append(env.Blockers, err.Error())
	return env
}

func matchesScaffoldPath(path string, patterns [][]string) bool {
	parts := strings.Split(filepath.ToSlash(path), "/")
	for _, pattern := range patterns {
		if len(parts) != len(pattern) {
			continue
		}
		matches := true
		for index, want := range pattern {
			if want != "*" && parts[index] != want {
				matches = false
				break
			}
			if want == "*" && !safeSegment(parts[index]) {
				matches = false
				break
			}
		}
		if matches {
			return true
		}
	}
	return false
}

func renderArtifactScaffold(kind artifactScaffoldKind, template []byte, variables map[string]any) ([]byte, error) {
	switch kind.Kind {
	case "quick-status":
		return renderQuickStatusScaffold(kind, template, variables)
	case "plan-contract":
		return renderPlanContractScaffold(kind, template, variables)
	default:
		return nil, fmt.Errorf("unsupported artifact scaffold kind %q", kind.Kind)
	}
}

func renderQuickStatusScaffold(kind artifactScaffoldKind, template []byte, variables map[string]any) ([]byte, error) {
	content := string(template)
	if !strings.HasPrefix(content, "---\n") && !strings.HasPrefix(content, "---\r\n") {
		return nil, fmt.Errorf("quick-status template must start with YAML frontmatter")
	}
	if !strings.Contains(content, "\nstatus: gathering\n") || !strings.Contains(content, "\nunderstanding_confirmed: false\n") {
		return nil, fmt.Errorf("quick-status template must default to gathering and unconfirmed")
	}
	for _, target := range kind.FillTargets {
		anchor := "<!-- " + target["anchor"] + " -->"
		if !strings.Contains(content, anchor) {
			return nil, fmt.Errorf("quick-status template is missing %s", anchor)
		}
	}
	allowed := map[string]bool{"id": true, "slug": true, "title": true, "trigger": true}
	for key := range variables {
		if !allowed[key] {
			return nil, fmt.Errorf("variable %q is not registered for quick-status", key)
		}
	}
	for _, key := range []string{"id", "slug", "title", "trigger"} {
		if key != "trigger" {
			if text, ok := variables[key].(string); ok && (strings.ContainsAny(text, "\r\n") || strings.Contains(text, "---") || strings.Contains(text, "...")) {
				return nil, fmt.Errorf("variable %q contains unsafe frontmatter content", key)
			}
		}
		value, err := yamlDoubleQuotedScalar(variables[key])
		if err != nil {
			return nil, fmt.Errorf("variable %q: %w", key, err)
		}
		content = strings.ReplaceAll(content, "{{"+key+"}}", value)
	}
	if err := validateReadinessText(content); err != nil {
		return nil, err
	}
	return []byte(content), nil
}

func renderPlanContractScaffold(kind artifactScaffoldKind, template []byte, variables map[string]any) ([]byte, error) {
	var payload map[string]any
	if err := json.Unmarshal(template, &payload); err != nil {
		return nil, fmt.Errorf("plan-contract template is invalid JSON: %w", err)
	}
	if payload["status"] != "draft" {
		return nil, fmt.Errorf("plan-contract status must default to draft")
	}
	transition, ok := payload["transition"].(map[string]any)
	if !ok || transition["status"] != "blocked" {
		return nil, fmt.Errorf("plan-contract transition.status must default to blocked")
	}
	for target := range kind.FillTargets {
		if _, exists := payload[target]; !exists {
			return nil, fmt.Errorf("plan-contract template is missing fill target %q", target)
		}
	}
	for key, value := range variables {
		if _, allowed := kind.FillTargets[key]; !allowed {
			return nil, fmt.Errorf("variable %q is not registered for plan-contract", key)
		}
		payload[key] = value
	}
	if err := rejectUnsafeReadiness(payload); err != nil {
		return nil, err
	}
	var output bytes.Buffer
	encoder := json.NewEncoder(&output)
	encoder.SetEscapeHTML(false)
	encoder.SetIndent("", "  ")
	if err := encoder.Encode(payload); err != nil {
		return nil, err
	}
	return output.Bytes(), nil
}

func yamlDoubleQuotedScalar(value any) (string, error) {
	if value == nil {
		return "", nil
	}
	text, ok := value.(string)
	if !ok {
		return "", fmt.Errorf("must be a string")
	}
	if !utf8.ValidString(text) {
		return "", fmt.Errorf("must be valid UTF-8")
	}
	var output strings.Builder
	for _, char := range text {
		switch char {
		case '\\':
			output.WriteString(`\\`)
		case '"':
			output.WriteString(`\"`)
		case '\r':
			output.WriteString(`\r`)
		case '\n':
			output.WriteString(`\n`)
		case '\t':
			output.WriteString(`\t`)
		default:
			if char < 32 || char == 127 {
				return "", fmt.Errorf("contains a control character")
			}
			output.WriteRune(char)
		}
	}
	return output.String(), nil
}

func validateReadinessText(content string) error {
	for _, line := range strings.Split(content, "\n") {
		trimmed := strings.TrimSpace(line)
		if trimmed == "" || strings.HasPrefix(trimmed, "#") || !strings.Contains(trimmed, ":") {
			continue
		}
		parts := strings.SplitN(trimmed, ":", 2)
		key := strings.TrimSpace(parts[0])
		value := strings.Trim(strings.TrimSpace(strings.SplitN(parts[1], "#", 2)[0]), `"'`)
		if isReadinessSensitive(key) && !safeReadinessScalar(value) {
			return fmt.Errorf("template field %q cannot assert readiness", key)
		}
	}
	return nil
}

func rejectUnsafeReadiness(value any) error {
	return walkReadinessValue("", value)
}

func walkReadinessValue(key string, value any) error {
	if isReadinessSensitive(key) && !safeReadinessValue(value) {
		return fmt.Errorf("field %q cannot assert readiness in a scaffold", key)
	}
	switch typed := value.(type) {
	case map[string]any:
		for nestedKey, nestedValue := range typed {
			if err := walkReadinessValue(nestedKey, nestedValue); err != nil {
				return err
			}
		}
	case []any:
		for _, item := range typed {
			if err := walkReadinessValue(key, item); err != nil {
				return err
			}
		}
	}
	return nil
}

func isReadinessSensitive(key string) bool {
	normalized := strings.ReplaceAll(strings.ToLower(key), "-", "_")
	return normalized == "status" || strings.Contains(normalized, "ready") || strings.Contains(normalized, "approved") || strings.Contains(normalized, "confirmed") || strings.HasSuffix(normalized, "_status")
}

func safeReadinessValue(value any) bool {
	if value == nil || value == false {
		return true
	}
	if text, ok := value.(string); ok {
		return safeReadinessScalar(text)
	}
	_, object := value.(map[string]any)
	_, list := value.([]any)
	return object || list
}

func safeReadinessScalar(value string) bool {
	switch strings.ToLower(strings.TrimSpace(value)) {
	case "", "false", "blocked", "draft", "gathering", "none", "not applicable", "not-applicable", "not-needed", "not-triggered", "not_applicable", "not_needed", "null", "pending", "unknown":
		return true
	default:
		return false
	}
}

func writeCreateOnly(path string, content []byte) error {
	file, err := os.OpenFile(path, os.O_WRONLY|os.O_CREATE|os.O_EXCL, 0o644)
	if err != nil {
		return err
	}
	if _, err := file.Write(content); err != nil {
		_ = file.Close()
		_ = os.Remove(path)
		return err
	}
	if err := file.Sync(); err != nil {
		_ = file.Close()
		_ = os.Remove(path)
		return err
	}
	return file.Close()
}
