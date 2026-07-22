package main

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"time"
)

type workflowLauncherConfig struct {
	SpecifyLauncher struct {
		Argv []string `json:"argv"`
	} `json:"specify_launcher"`
}

func (service *WorkflowService) validateStageArtifacts(feature workflowFeature, stage string) Envelope {
	if service.workflowArtifactGateRunner != nil {
		return service.workflowArtifactGateRunner(feature, stage)
	}
	configPath, err := secureProjectPath(service.projectRoot, ".specify/config.json")
	if err != nil {
		return workflowArtifactGateFailure(feature, stage, "artifact validation launcher config is unsafe", err, nil)
	}
	raw, err := os.ReadFile(configPath)
	if err != nil {
		return workflowArtifactGateFailure(feature, stage, "artifact validation launcher config is unavailable", err, nil)
	}
	var config workflowLauncherConfig
	if err := json.Unmarshal(raw, &config); err != nil {
		return workflowArtifactGateFailure(feature, stage, "artifact validation launcher config is invalid", err, nil)
	}
	launcher := make([]string, 0, len(config.SpecifyLauncher.Argv))
	for _, item := range config.SpecifyLauncher.Argv {
		item = strings.TrimSpace(item)
		if item == "" {
			return workflowArtifactGateFailure(feature, stage, "artifact validation launcher argv is invalid", fmt.Errorf("launcher argv contains an empty item"), nil)
		}
		launcher = append(launcher, item)
	}
	if len(launcher) == 0 {
		return workflowArtifactGateFailure(feature, stage, "artifact validation launcher is unavailable", fmt.Errorf("specify_launcher.argv is required"), nil)
	}
	gateArgs := []string{
		"hook", "validate-artifacts",
		"--command", stage,
		"--feature-dir", feature.Rel,
		"--format", "json",
	}
	commandArgs := append(append([]string{}, launcher[1:]...), gateArgs...)
	ctx, cancel := context.WithTimeout(context.Background(), 60*time.Second)
	defer cancel()
	command := exec.CommandContext(ctx, launcher[0], commandArgs...)
	projectRoot, rootErr := filepath.Abs(service.projectRoot)
	if rootErr != nil {
		return workflowArtifactGateFailure(feature, stage, "artifact validation project root is unavailable", rootErr, nil)
	}
	projectRoot, rootErr = filepath.EvalSymlinks(projectRoot)
	if rootErr != nil {
		return workflowArtifactGateFailure(feature, stage, "artifact validation project root is unavailable", rootErr, nil)
	}
	command.Dir = projectRoot
	command.Env = append(os.Environ(), "SPECIFY_RUNTIME_WORKFLOW_GATE=1")
	var stdout, stderr bytes.Buffer
	command.Stdout = &stdout
	command.Stderr = &stderr
	runErr := command.Run()
	if ctx.Err() != nil {
		return workflowArtifactGateFailure(feature, stage, "artifact validation timed out", ctx.Err(), nil)
	}
	trimmed := bytes.TrimSpace(stdout.Bytes())
	var payload map[string]any
	if len(trimmed) == 0 || json.Unmarshal(trimmed, &payload) != nil {
		details := runErr
		if details == nil {
			details = fmt.Errorf("launcher returned invalid JSON")
		}
		if text := strings.TrimSpace(stderr.String()); text != "" {
			details = fmt.Errorf("%w: %s", details, text)
		}
		return workflowArtifactGateFailure(feature, stage, "artifact validation did not return a typed result", details, nil)
	}
	status, _ := payload["status"].(string)
	if runErr == nil && (status == "ok" || status == "warn" || status == "repaired") {
		env := NewEnvelope(status, "workflow stage artifacts validated")
		if summary, ok := payload["summary"].(string); ok && strings.TrimSpace(summary) != "" {
			env.Summary = summary
		}
		env.Data["stage"] = stage
		env.Data["feature_id"] = feature.ID
		return env
	}
	blockers := workflowPayloadBlockers(payload)
	if runErr != nil && len(blockers) == 0 {
		blockers = append(blockers, runErr.Error())
	}
	if text := strings.TrimSpace(stderr.String()); text != "" && len(blockers) == 0 {
		blockers = append(blockers, text)
	}
	return workflowArtifactGateFailure(feature, stage, "workflow stage artifact validation failed", nil, blockers)
}

func workflowPayloadBlockers(payload map[string]any) []any {
	raw, ok := payload["blockers"].([]any)
	if !ok {
		return []any{}
	}
	return append([]any{}, raw...)
}

func workflowArtifactGateFailure(feature workflowFeature, stage, summary string, err error, blockers []any) Envelope {
	env := NewEnvelope("blocked", summary)
	env.Data["error_code"] = "artifact-validation-failed"
	env.Data["feature_id"] = feature.ID
	env.Data["stage"] = stage
	if blockers != nil {
		env.Blockers = append(env.Blockers, blockers...)
	}
	if err != nil {
		env.Blockers = append(env.Blockers, err.Error())
	}
	env.ShowArgv = workflowShowArgv(feature)
	return env
}
