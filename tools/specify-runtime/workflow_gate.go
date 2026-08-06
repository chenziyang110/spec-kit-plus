package main

import (
	"path/filepath"
	"strings"
)

func (service *WorkflowService) validateStageArtifacts(feature workflowFeature, stage string) Envelope {
	if service.workflowArtifactGateRunner != nil {
		return service.workflowArtifactGateRunner(feature, stage)
	}
	env := validateHookArtifacts([]string{
		"--command", stage,
		"--feature-dir", feature.Rel,
		"--project-root", service.projectRoot,
		"--format", "json",
	})
	if env.Status == "ok" || env.Status == "warn" || env.Status == "repaired" {
		env.Data["stage"] = stage
		env.Data["feature_id"] = feature.ID
		if strings.TrimSpace(env.Summary) == "" {
			env.Summary = "workflow stage artifacts validated"
		}
		return env
	}
	return workflowArtifactGateFailure(feature, stage, env)
}

func workflowArtifactGateFailure(feature workflowFeature, stage string, source Envelope) Envelope {
	summary := strings.TrimSpace(source.Summary)
	if summary == "" {
		summary = "workflow stage artifacts failed validation"
	}
	// Prefer the first concrete blocker as the summary when the envelope only
	// carries a generic semantic failure, so agents see resume-audit/handoff
	// text instead of "semantic validation failed".
	if len(source.Blockers) > 0 {
		if first, ok := source.Blockers[0].(string); ok && strings.TrimSpace(first) != "" {
			if summary == "workflow artifact semantic validation failed" || summary == "required workflow artifacts are missing or invalid" {
				summary = first
			}
		}
	}
	env := NewEnvelope("blocked", summary)
	env.Data["error_code"] = "artifact-validation-failed"
	env.Data["feature_id"] = feature.ID
	env.Data["stage"] = stage
	validatedPath := filepath.ToSlash(filepath.Join(feature.Rel, "workflow-state.md"))
	if path, ok := source.Data["validated_path"].(string); ok && strings.TrimSpace(path) != "" {
		validatedPath = path
	} else {
		switch stage {
		case "implement":
			validatedPath = filepath.ToSlash(filepath.Join(feature.Rel, "implementation-handoff.json"))
		case "review":
			validatedPath = filepath.ToSlash(filepath.Join(feature.Rel, "review-state.json"))
		case "accept":
			validatedPath = filepath.ToSlash(filepath.Join(feature.Rel, "human-acceptance.json"))
		case "tasks":
			validatedPath = filepath.ToSlash(filepath.Join(feature.Rel, "task-index.json"))
		}
	}
	env.Data["validated_path"] = validatedPath
	if errors, ok := source.Data["errors"].([]string); ok && len(errors) > 0 {
		env.Data["errors"] = errors
	} else if errors, ok := source.Data["errors"].([]any); ok {
		env.Data["errors"] = errors
	}
	if source.Blockers != nil {
		env.Blockers = append(env.Blockers, source.Blockers...)
	}
	env.ShowArgv = workflowShowArgv(feature)
	return env
}
