package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"sort"
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
	"alignment": {
		Kind:                  "alignment",
		TemplatePath:          "alignment-template.md",
		AllowedPaths:          [][]string{{"specs", "*", "alignment.md"}, {".specify", "features", "*", "alignment.md"}},
		AgentFillRequired:     []string{"current_understanding", "confirmed_facts", "readiness_decision"},
		EstimatedTokenSavings: 900,
	},
	"clarification-checkpoints": {
		Kind:                  "clarification-checkpoints",
		TemplatePath:          "artifacts/empty.ndjson",
		AllowedPaths:          [][]string{{"specs", "*", "clarification", "checkpoints.ndjson"}, {".specify", "features", "*", "clarification", "checkpoints.ndjson"}},
		EstimatedTokenSavings: 20,
	},
	"clarification-evidence-index": {
		Kind:                  "clarification-evidence-index",
		TemplatePath:          "artifacts/evidence-index.json",
		AllowedPaths:          [][]string{{"specs", "*", "clarification", "evidence-index.json"}, {".specify", "features", "*", "clarification", "evidence-index.json"}},
		AgentFillRequired:     []string{"lanes"},
		FillTargets:           map[string]map[string]string{"lanes": {"type": "json_pointer", "pointer": "/lanes"}},
		EstimatedTokenSavings: 80,
	},
	"constitution": {
		Kind:                  "constitution",
		TemplatePath:          "constitution-template.md",
		AllowedPaths:          [][]string{{".specify", "memory", "constitution.md"}},
		AgentFillRequired:     []string{"project_name", "governance_updates"},
		EstimatedTokenSavings: 1500,
	},
	"design-brief": {
		Kind:         "design-brief",
		TemplatePath: "design-brief-template.md",
		AllowedPaths: [][]string{{".specify", "design", "design-brief.md"}},
		// redesign_mode is conditional (live UI / refine|audit) and is not
		// unconditionally required by scaffold contracts.
		AgentFillRequired: []string{
			"subject",
			"audience",
			"single_job",
			"decisions",
			"design_read",
			"dials",
			"aesthetic_family",
			"foundation_strategy",
			"anti_slop_locks",
			"reference_board_intents",
		},
		EstimatedTokenSavings: 700,
	},
	"design-review": {
		Kind:                  "design-review",
		TemplatePath:          "artifacts/design-review.md",
		AllowedPaths:          [][]string{{".specify", "design", "review.md"}},
		AgentFillRequired:     []string{"mode", "inputs", "approved_direction", "immutable_references", "contract_ids", "platforms", "risks", "validation", "next_workflow"},
		EstimatedTokenSavings: 500,
	},
	"deep-research": {
		Kind:         "deep-research",
		TemplatePath: "artifacts/deep-research.md",
		AllowedPaths: [][]string{
			{"specs", "*", "deep-research.md"},
			{".specify", "features", "*", "deep-research.md"},
		},
		AgentFillRequired:     []string{"metadata", "feasibility_decision", "capability_matrix", "orchestration", "agent_findings", "evidence_quality", "implementation_chain", "spike_evidence", "contradiction_resolution", "synthesis_decisions", "planning_handoff", "traceability", "capability_cards", "research_exclusions", "sources", "readiness_checklist", "next_command"},
		EstimatedTokenSavings: 1400,
	},
	"deep-research-not-needed": {
		Kind:         "deep-research-not-needed",
		TemplatePath: "artifacts/deep-research-not-needed.md",
		AllowedPaths: [][]string{
			{"specs", "*", "deep-research.md"},
			{".specify", "features", "*", "deep-research.md"},
		},
		AgentFillRequired:     []string{"metadata", "feasibility_decision", "planning_handoff", "next_command"},
		EstimatedTokenSavings: 450,
	},
	"data-model": {
		Kind:                  "data-model",
		TemplatePath:          "artifacts/data-model.md",
		AllowedPaths:          [][]string{{"specs", "*", "data-model.md"}, {".specify", "features", "*", "data-model.md"}},
		AgentFillRequired:     []string{"scope_sources", "data_structures", "relationships_lifecycle", "invariants_migration", "integration_verification"},
		EstimatedTokenSavings: 280,
	},
	"debug-session": {
		Kind:                  "debug-session",
		TemplatePath:          "artifacts/debug-session.md",
		AllowedPaths:          [][]string{{".planning", "debug", "*.md"}},
		AgentFillRequired:     []string{"understanding_checkpoint"},
		EstimatedTokenSavings: 500,
	},
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
	"quick-plan": {
		Kind:                  "quick-plan",
		TemplatePath:          "artifacts/quick-plan.md",
		AllowedPaths:          [][]string{{".planning", "quick", "*", "PLAN.md"}},
		AgentFillRequired:     []string{"outcome_boundaries", "architecture_surfaces", "work_batches", "acceptance_verification"},
		EstimatedTokenSavings: 350,
	},
	"quick-summary": {
		Kind:                  "quick-summary",
		TemplatePath:          "artifacts/quick-summary.md",
		AllowedPaths:          [][]string{{".planning", "quick", "*", "SUMMARY.md"}},
		AgentFillRequired:     []string{"outcome", "changed_paths", "verification", "skipped_or_failed_checks", "residual_risk", "recovery_state"},
		EstimatedTokenSavings: 260,
	},
	"quickstart": {
		Kind:                  "quickstart",
		TemplatePath:          "artifacts/quickstart.md",
		AllowedPaths:          [][]string{{"specs", "*", "quickstart.md"}, {".specify", "features", "*", "quickstart.md"}},
		AgentFillRequired:     []string{"purpose", "preconditions", "scenario", "expected_results", "failure_recovery", "verification_evidence"},
		EstimatedTokenSavings: 230,
	},
	"planning-lane-manifest": {
		Kind:                  "planning-lane-manifest",
		TemplatePath:          "artifacts/lane-manifest.json",
		AllowedPaths:          [][]string{{"specs", "*", "planning", "lane-manifest.json"}, {".specify", "features", "*", "planning", "lane-manifest.json"}},
		AgentFillRequired:     []string{"lanes"},
		FillTargets:           map[string]map[string]string{"status": {"type": "json_pointer", "pointer": "/status"}, "lanes": {"type": "json_pointer", "pointer": "/lanes"}},
		EstimatedTokenSavings: 220,
	},
	"task-generation-lane-manifest": {
		Kind:                  "task-generation-lane-manifest",
		TemplatePath:          "artifacts/lane-manifest.json",
		AllowedPaths:          [][]string{{"specs", "*", "task-generation", "lane-manifest.json"}, {".specify", "features", "*", "task-generation", "lane-manifest.json"}},
		AgentFillRequired:     []string{"lanes"},
		FillTargets:           map[string]map[string]string{"status": {"type": "json_pointer", "pointer": "/status"}, "lanes": {"type": "json_pointer", "pointer": "/lanes"}},
		EstimatedTokenSavings: 220,
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
	"research": {
		Kind:         "research",
		TemplatePath: "research-template.md",
		AllowedPaths: [][]string{
			{"specs", "*", "research.md"},
			{".specify", "features", "*", "research.md"},
			{".planning", "debug", "*.research.md"},
		},
		AgentFillRequired:     []string{"summary", "decisions", "sources"},
		EstimatedTokenSavings: 350,
	},
	"references": {
		Kind:                  "references",
		TemplatePath:          "references-template.md",
		AllowedPaths:          [][]string{{"specs", "*", "references.md"}, {".specify", "features", "*", "references.md"}},
		AgentFillRequired:     []string{"source_files_read", "reference_entries"},
		EstimatedTokenSavings: 500,
	},
	"spec-contract": {
		Kind:         "spec-contract",
		TemplatePath: "spec-contract-template.json",
		AllowedPaths: [][]string{
			{"specs", "*", "spec-contract.json"},
			{".specify", "features", "*", "spec-contract.json"},
		},
		AgentFillRequired: []string{"target_need", "scope", "acceptance_criteria", "decisions"},
		FillTargets: map[string]map[string]string{
			"target_need":                 {"type": "json_pointer", "pointer": "/target_need"},
			"scope":                       {"type": "json_pointer", "pointer": "/scope"},
			"constraints":                 {"type": "json_pointer", "pointer": "/constraints"},
			"acceptance_criteria":         {"type": "json_pointer", "pointer": "/acceptance_criteria"},
			"decisions":                   {"type": "json_pointer", "pointer": "/decisions"},
			"capability_operations":       {"type": "json_pointer", "pointer": "/capability_operations"},
			"must_preserve_refs":          {"type": "json_pointer", "pointer": "/must_preserve_refs"},
			"consequence_obligation_refs": {"type": "json_pointer", "pointer": "/consequence_obligation_refs"},
			"design_contract":             {"type": "json_pointer", "pointer": "/design_contract"},
			"context_capsule":             {"type": "json_pointer", "pointer": "/context_capsule"},
			"open_items":                  {"type": "json_pointer", "pointer": "/open_items"},
		},
		EstimatedTokenSavings: 1800,
	},
	"specify-context": {
		Kind:                  "specify-context",
		TemplatePath:          "context-template.md",
		AllowedPaths:          [][]string{{"specs", "*", "context.md"}, {".specify", "features", "*", "context.md"}},
		AgentFillRequired:     []string{"planning_context", "repository_context", "integration_boundaries"},
		EstimatedTokenSavings: 650,
	},
	"specify-draft": {
		Kind:                  "specify-draft",
		TemplatePath:          "specify-draft-template.md",
		AllowedPaths:          [][]string{{"specs", "*", "specify-draft.md"}, {".specify", "features", "*", "specify-draft.md"}},
		AgentFillRequired:     []string{"intent_analysis", "domain_progress"},
		EstimatedTokenSavings: 1000,
	},
	"ui-reference-notes": {
		Kind:         "ui-reference-notes",
		TemplatePath: "ui-reference-notes-template.md",
		AllowedPaths: [][]string{
			{"specs", "*", "ui-reference-notes.md"},
			{".specify", "features", "*", "ui-reference-notes.md"},
		},
		AgentFillRequired:     []string{"reference_inputs", "fidelity_mode", "visual_facts"},
		EstimatedTokenSavings: 400,
	},
	"ui-brief": {
		Kind:         "ui-brief",
		TemplatePath: "ui-brief-template.md",
		AllowedPaths: [][]string{
			{"specs", "*", "ui-brief.md"},
			{".specify", "features", "*", "ui-brief.md"},
		},
		AgentFillRequired:     []string{"source_design_system", "experience_core", "approved_direction"},
		EstimatedTokenSavings: 900,
	},
	"workflow-state": {
		Kind:         "workflow-state",
		TemplatePath: "workflow-state-template.md",
		AllowedPaths: [][]string{
			{"specs", "*", "workflow-state.md"},
			{".specify", "features", "*", "workflow-state.md"},
		},
		AgentFillRequired:     []string{"current_command", "stage_state", "next_command"},
		EstimatedTokenSavings: 1200,
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
	names := make([]string, 0, len(artifactScaffoldKinds))
	for name := range artifactScaffoldKinds {
		names = append(names, name)
	}
	sort.Strings(names)
	for _, name := range names {
		kind := artifactScaffoldKinds[name]
		allowedPaths := make([]string, 0, len(kind.AllowedPaths))
		for _, pattern := range kind.AllowedPaths {
			allowedPaths = append(allowedPaths, strings.Join(pattern, "/"))
		}
		env.Items = append(env.Items, map[string]any{
			"agent_fill_required":     kind.AgentFillRequired,
			"allowed_paths":           allowedPaths,
			"estimated_token_savings": kind.EstimatedTokenSavings,
			"fill_targets":            kind.FillTargets,
			"kind":                    kind.Kind,
			"required_options":        []string{"--kind", "--path"},
			"usage":                   "specify-runtime artifact scaffold --kind " + kind.Kind + " --path <project-relative-path> --vars <json> --format json",
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
			if strings.HasPrefix(want, "*.") {
				if !safeSegment(parts[index]) || !strings.HasSuffix(parts[index], strings.TrimPrefix(want, "*")) {
					matches = false
					break
				}
				continue
			}
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
	case "spec-contract":
		return renderSpecContractScaffold(kind, template, variables)
	case "planning-lane-manifest", "task-generation-lane-manifest":
		return renderLaneManifestScaffold(kind, template, variables)
	case "clarification-evidence-index":
		return renderEvidenceIndexScaffold(kind, template, variables)
	case "alignment", "clarification-checkpoints", "constitution", "data-model", "debug-session", "deep-research", "deep-research-not-needed", "design-brief", "design-review", "quick-plan", "quick-summary", "quickstart", "references", "research", "specify-context", "specify-draft", "ui-brief", "ui-reference-notes", "workflow-state":
		return renderStaticArtifactScaffold(kind, template, variables)
	default:
		return nil, fmt.Errorf("unsupported artifact scaffold kind %q", kind.Kind)
	}
}

func renderEvidenceIndexScaffold(kind artifactScaffoldKind, template []byte, variables map[string]any) ([]byte, error) {
	if len(variables) != 0 {
		return nil, fmt.Errorf("%s does not accept scaffold variables; patch accepted lanes after creation", kind.Kind)
	}
	var payload map[string]any
	if err := json.Unmarshal(template, &payload); err != nil {
		return nil, fmt.Errorf("evidence-index template is invalid JSON: %w", err)
	}
	if intFromAny(payload["version"]) != 1 {
		return nil, fmt.Errorf("evidence-index template must use version 1")
	}
	lanes, ok := payload["lanes"].([]any)
	if !ok || len(lanes) != 0 {
		return nil, fmt.Errorf("evidence-index template lanes must default to an empty array")
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

func renderLaneManifestScaffold(kind artifactScaffoldKind, template []byte, variables map[string]any) ([]byte, error) {
	if len(variables) != 0 {
		return nil, fmt.Errorf("%s does not accept scaffold variables; patch semantic lane records after creation", kind.Kind)
	}
	var payload map[string]any
	if err := json.Unmarshal(template, &payload); err != nil {
		return nil, fmt.Errorf("lane-manifest template is invalid JSON: %w", err)
	}
	if intFromAny(payload["version"]) != 1 || payload["status"] != "draft" {
		return nil, fmt.Errorf("lane-manifest template must use version 1 and draft status")
	}
	lanes, ok := payload["lanes"].([]any)
	if !ok || len(lanes) != 0 {
		return nil, fmt.Errorf("lane-manifest template lanes must default to an empty array")
	}
	if kind.Kind == "planning-lane-manifest" {
		payload["command"] = "plan"
	} else {
		payload["command"] = "tasks"
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

func renderSpecContractScaffold(kind artifactScaffoldKind, template []byte, variables map[string]any) ([]byte, error) {
	var payload map[string]any
	if err := json.Unmarshal(template, &payload); err != nil {
		return nil, fmt.Errorf("spec-contract template is invalid JSON: %w", err)
	}
	if payload["status"] != "draft" {
		return nil, fmt.Errorf("spec-contract status must default to draft")
	}
	transition, ok := payload["transition"].(map[string]any)
	if !ok || transition["status"] != "blocked" {
		return nil, fmt.Errorf("spec-contract transition.status must default to blocked")
	}
	for target := range kind.FillTargets {
		if _, exists := payload[target]; !exists {
			return nil, fmt.Errorf("spec-contract template is missing fill target %q", target)
		}
	}
	for key, value := range variables {
		if _, allowed := kind.FillTargets[key]; !allowed {
			return nil, fmt.Errorf("variable %q is not registered for spec-contract", key)
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

func renderStaticArtifactScaffold(kind artifactScaffoldKind, template []byte, variables map[string]any) ([]byte, error) {
	if len(variables) != 0 {
		return nil, fmt.Errorf("%s does not accept scaffold variables; create it from the stable template, then use leased artifact patches", kind.Kind)
	}
	if len(template) == 0 || !utf8.Valid(template) {
		return nil, fmt.Errorf("%s template must be non-empty UTF-8", kind.Kind)
	}
	content := string(template)
	requiredMarkers := map[string][]string{
		"alignment":                 {"# Specification Alignment Report:", "## Current Understanding", "## Readiness Decision"},
		"clarification-checkpoints": {},
		"constitution":              {" Constitution", "## Core Principles", "## Governance"},
		"data-model":                {"# Data Model", "## Data Structures and Ownership", "## Integration and Verification"},
		"debug-session":             {"status: intake", "understanding_confirmed: false", "## Understanding Checkpoint"},
		"deep-research":             {"# Deep Research", "**Status**: Pending", "## Feasibility Decision", "## Contradiction Resolution Log", "## Planning Handoff", "## Capability Cards", "## Research Exclusions", "## Planning Handoff Readiness Checklist", "## Next Command"},
		"deep-research-not-needed":  {"# Deep Research", "**Status**: Pending", "## Feasibility Decision", "## Planning Handoff", "## Next Command"},
		"design-brief":              {"design_brief:", "status: draft", "# Design Brief", "## Taste Intake", "## UI Evidence And System Model", "## Confirmed Experience", "## Approval", "design_read:", "dials:", "aesthetic_family:", "foundation_strategy:", "redesign_mode:", "anti_slop_locks:", "reference_board_intents:"},
		"design-review":             {"# Design Review", "## Approved Direction", "## Immutable References", "## Recommended Next Workflow"},
		"quick-plan":                {"# Quick Task Plan", "## Outcome and Boundaries", "## Acceptance and Verification"},
		"quick-summary":             {"# Quick Task Summary", "## Outcome", "## Verification", "## Residual Risk"},
		"quickstart":                {"# Quickstart Validation", "## Preconditions", "## Expected Results", "## Verification Evidence"},
		"references":                {"# Reference Memory:", "## Source Files Read", "## Reference Entries"},
		"research":                  {"# Research:", "## Summary", "## Decisions", "## Sources"},
		"specify-context":           {"# Planning Context:", "## Planning Context", "## Relevant Repository Context"},
		"specify-draft":             {"# Specification Draft Ledger:", "## Intent Analysis Record", "## Domain Progress Ledger"},
		"ui-brief":                  {"# UI Brief", "## Source Design System", "## Approved Direction"},
		"ui-reference-notes":        {"# UI Reference Notes", "## Reference Inputs", "## Fidelity Mode", "## Risks And Gaps"},
		"workflow-state":            {"# Workflow State:", "## Current Command", "## Next Command"},
	}
	for _, marker := range requiredMarkers[kind.Kind] {
		if !strings.Contains(content, marker) {
			return nil, fmt.Errorf("%s template is missing %q", kind.Kind, marker)
		}
	}
	if map[string]bool{
		"deep-research":            true,
		"deep-research-not-needed": true,
		"data-model":               true,
		"design-review":            true,
		"quick-plan":               true,
		"quick-summary":            true,
		"quickstart":               true,
	}[kind.Kind] {
		for _, target := range kind.AgentFillRequired {
			anchor := "<!-- agent-fill:" + target + " -->"
			if !strings.Contains(content, anchor) {
				return nil, fmt.Errorf("%s template is missing %s", kind.Kind, anchor)
			}
		}
	}
	if kind.Kind == "debug-session" {
		if err := validateReadinessText(content); err != nil {
			return nil, err
		}
	}
	if kind.Kind == "design-brief" {
		if err := validateDesignBriefScaffoldTemplate(content); err != nil {
			return nil, err
		}
	}
	return append([]byte(nil), template...), nil
}

func validateDesignBriefScaffoldTemplate(content string) error {
	for _, marker := range []string{
		"  status: draft",
		"  design_read: null",
		"  dials:",
		"  aesthetic_family: null",
		"  foundation_strategy: null",
		"  redesign_mode: null",
		"  anti_slop_locks: []",
		"  reference_board_intents: []",
		"  approved_direction: null",
		"  approved_visual_ref: null",
		"  approved_preview_sha256: null",
		"  approved_manifest_sha256: null",
		"  approved_handoff_ref: null",
		"  approved_handoff_sha256: null",
		"  approved_handoff_contract_ids: []",
		"## Taste Intake",
		"- Status: unapproved",
	} {
		if !strings.Contains(content, marker) {
			return fmt.Errorf("design-brief template must preserve safe readiness default %q", strings.TrimSpace(marker))
		}
	}
	return nil
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
	case "intake", "not_requested", "unapproved":
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
