package main

import (
	"encoding/json"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strings"
)

func runIntegrate(args []string, stdout io.Writer) int {
	projectRoot := optionValue(args, "--project-root", ".")
	records, err := readRuntimeLanes(projectRoot)
	if err != nil {
		return writeEnvelope(stdout, laneBlocked("integration lane state is invalid", err))
	}
	featureDir := filepath.ToSlash(strings.TrimSpace(optionValue(args, "--feature-dir", "")))
	closeLane := hasFlag(args, "--close")
	if featureDir == "" {
		env := NewEnvelope("ok", "integration candidates inspected")
		env.Data["mode"] = "discovery"
		env.Data["candidates"] = integrationCandidates(projectRoot, records)
		return writeEnvelope(stdout, env)
	}
	var selected *runtimeLaneRecord
	for index := range records {
		if filepath.ToSlash(records[index].FeatureDir) == featureDir {
			selected = &records[index]
			break
		}
	}
	if selected == nil {
		env := NewEnvelope("blocked", "feature directory has no registered integration lane")
		env.Data["mode"] = "targeted"
		env.Data["feature_dir"] = featureDir
		env.Blockers = append(env.Blockers, "register or select the lane before integration closeout")
		return writeEnvelope(stdout, env)
	}
	ready, checks := assessRuntimeIntegration(projectRoot, *selected)
	env := NewEnvelope("ok", "integration lane inspected")
	env.Data["mode"] = "targeted"
	env.Data["feature_dir"] = featureDir
	env.Data["lane_id"] = selected.LaneID
	env.Data["ready"] = ready
	env.Data["closed"] = false
	env.Data["checks"] = checks
	if closeLane && !ready {
		env.Status = "blocked"
		env.Summary = "integration closeout prechecks failed"
		env.Blockers = append(env.Blockers, map[string]any{
			"code":              "integration-precheck-failed",
			"owner":             "agent",
			"exact_next_action": "Repair every failed integration check and rerun integrate --close.",
		})
		return writeEnvelope(stdout, env)
	}
	if closeLane {
		selected.LifecycleState = "completed"
		selected.RecoveryState = "completed"
		selected.LastCommand = "integrate"
		if err := persistRuntimeLane(projectRoot, *selected); err != nil {
			return writeEnvelope(stdout, laneBlocked("integration closeout could not persist lane state", err))
		}
		env.Data["closed"] = true
	}
	return writeEnvelope(stdout, env)
}

func integrationCandidates(projectRoot string, records []runtimeLaneRecord) []any {
	items := []any{}
	for _, lane := range records {
		if lane.LastCommand != "implement" &&
			lane.LastCommand != "integrate" &&
			lane.LifecycleState != "implementing" &&
			lane.LifecycleState != "integrating" &&
			lane.LifecycleState != "completed" {
			continue
		}
		ready, checks := assessRuntimeIntegration(projectRoot, lane)
		items = append(items, map[string]any{
			"lane_id":             lane.LaneID,
			"feature_id":          lane.FeatureID,
			"feature_dir":         filepath.ToSlash(lane.FeatureDir),
			"branch_name":         lane.BranchName,
			"recovery_state":      lane.RecoveryState,
			"verification_status": lane.VerificationStatus,
			"ready":               ready,
			"recommended_action":  map[bool]string{true: "close", false: "fix-prechecks"}[ready],
			"checks":              checks,
		})
	}
	return items
}

func assessRuntimeIntegration(projectRoot string, lane runtimeLaneRecord) (bool, []any) {
	checks := []any{}
	appendCheck := func(name string, passed bool, detail string) {
		status := "fail"
		if passed {
			status = "pass"
		}
		checks = append(checks, map[string]any{"name": name, "status": status, "detail": detail})
	}
	appendCheck("branch-bound", strings.TrimSpace(lane.BranchName) != "", defaultString(lane.BranchName, "missing branch name"))

	featureRoot, err := secureProjectPath(projectRoot, filepath.ToSlash(lane.FeatureDir))
	featureInfo, statErr := os.Stat(featureRoot)
	featureExists := err == nil && statErr == nil && featureInfo.IsDir()
	appendCheck("feature-dir-exists", featureExists, filepath.ToSlash(lane.FeatureDir))

	implementationComplete := lane.RecoveryState == "completed"
	if featureExists && lane.LastCommand == "implement" {
		if raw, readErr := os.ReadFile(filepath.Join(featureRoot, "implement-tracker.md")); readErr == nil {
			implementationComplete = markdownStateValue(string(raw), "status") == "resolved"
		}
	}
	appendCheck("implementation-complete", implementationComplete, lane.RecoveryState)
	appendCheck("verification-passed", lane.VerificationStatus == "passed", defaultString(lane.VerificationStatus, "unknown"))

	uiReady, uiDetail := validateRuntimeIntegratedUI(featureRoot, featureExists)
	appendCheck("integrated-ui-evidence", uiReady, uiDetail)

	ready := true
	for _, raw := range checks {
		check := raw.(map[string]any)
		if check["status"] != "pass" {
			ready = false
		}
	}
	return ready, checks
}

func validateRuntimeIntegratedUI(featureRoot string, featureExists bool) (bool, string) {
	if !featureExists {
		return false, "feature directory is unavailable"
	}
	taskIndexPath := filepath.Join(featureRoot, "task-index.json")
	raw, err := os.ReadFile(taskIndexPath)
	if os.IsNotExist(err) {
		return true, "no structured UI tasks declared"
	}
	if err != nil {
		return false, err.Error()
	}
	var payload map[string]any
	if err := json.Unmarshal(raw, &payload); err != nil {
		return false, "task-index.json is invalid: " + err.Error()
	}
	tasks, _ := payload["tasks"].([]any)
	uiTaskIDs := []string{}
	for _, item := range tasks {
		task, _ := item.(map[string]any)
		if task == nil {
			continue
		}
		uiContract, _ := task["ui_contract"].(map[string]any)
		applicability := strings.ToLower(fmt.Sprint(uiContract["applicability"]))
		if applicability == "applicable" || applicability == "required" {
			uiTaskIDs = append(uiTaskIDs, fmt.Sprint(task["id"]))
		}
	}
	for _, taskID := range uiTaskIDs {
		lifecyclePath := filepath.Join(featureRoot, "implementation-review", "tasks", taskID+".json")
		lifecycleRaw, readErr := os.ReadFile(lifecyclePath)
		if readErr != nil {
			return false, filepath.ToSlash(filepath.Join("implementation-review", "tasks", taskID+".json")) + " is required"
		}
		var lifecycle map[string]any
		if jsonErr := json.Unmarshal(lifecycleRaw, &lifecycle); jsonErr != nil {
			return false, taskID + " lifecycle is invalid"
		}
		if fmt.Sprint(lifecycle["status"]) != "accepted" {
			return false, taskID + " lifecycle must be accepted"
		}
		evidenceScope := strings.ToLower(fmt.Sprint(lifecycle["evidence_scope"]))
		if evidenceScope != "integrated" {
			return false, taskID + " evidence_scope must be integrated"
		}
	}
	if len(uiTaskIDs) == 0 {
		return true, "no UI-bearing tasks"
	}
	return true, strings.Join(uiTaskIDs, ", ")
}

func markdownStateValue(content, key string) string {
	prefix := strings.ToLower(key) + ":"
	for _, line := range strings.Split(content, "\n") {
		normalized := strings.TrimSpace(line)
		if strings.HasPrefix(strings.ToLower(normalized), prefix) {
			return strings.ToLower(strings.Trim(strings.TrimSpace(normalized[len(prefix):]), `"'`))
		}
	}
	return ""
}

func persistRuntimeLane(projectRoot string, lane runtimeLaneRecord) error {
	target, err := secureProjectPath(projectRoot, filepath.ToSlash(filepath.Join(".specify", "lanes", lane.LaneID, "lane.json")))
	if err != nil {
		return err
	}
	if err := writeScriptJSONFile(target, lane); err != nil {
		return err
	}
	records, err := readRuntimeLanes(projectRoot)
	if err != nil {
		return err
	}
	indexItems := make([]any, 0, len(records))
	for _, record := range records {
		indexItems = append(indexItems, map[string]any{
			"lane_id":        record.LaneID,
			"feature_id":     record.FeatureID,
			"feature_dir":    filepath.ToSlash(record.FeatureDir),
			"last_command":   record.LastCommand,
			"recovery_state": record.RecoveryState,
		})
	}
	indexPath, err := secureProjectPath(projectRoot, ".specify/lanes/index.json")
	if err != nil {
		return err
	}
	return writeScriptJSONFile(indexPath, map[string]any{"lanes": indexItems})
}
