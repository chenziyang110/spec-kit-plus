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
	return workflowArtifactGateFailure(feature, stage, env.Summary, nil, env.Blockers)
}

func workflowArtifactGateFailure(feature workflowFeature, stage, summary string, err error, blockers []any) Envelope {
	env := NewEnvelope("blocked", summary)
	env.Data["error_code"] = "artifact-validation-failed"
	env.Data["feature_id"] = feature.ID
	env.Data["stage"] = stage
	env.Data["validated_path"] = filepath.ToSlash(filepath.Join(feature.Rel, "workflow-state.md"))
	if blockers != nil {
		env.Blockers = append(env.Blockers, blockers...)
	}
	if err != nil {
		env.Blockers = append(env.Blockers, err.Error())
	}
	env.ShowArgv = workflowShowArgv(feature)
	return env
}
