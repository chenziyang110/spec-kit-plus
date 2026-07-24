package main

import (
	"encoding/json"
	"fmt"
	"io"
	"os"
	"os/exec"
	"path/filepath"
	"sort"
	"strings"
)

type runtimeLaneRecord struct {
	LaneID               string `json:"lane_id"`
	FeatureID            string `json:"feature_id"`
	FeatureDir           string `json:"feature_dir"`
	BranchName           string `json:"branch_name"`
	WorktreePath         string `json:"worktree_path"`
	LifecycleState       string `json:"lifecycle_state"`
	RecoveryState        string `json:"recovery_state"`
	LastCommand          string `json:"last_command"`
	LastStableCheckpoint string `json:"last_stable_checkpoint"`
	RecoveryReason       string `json:"recovery_reason"`
	VerificationStatus   string `json:"verification_status"`
}

func runLane(args []string, stdout io.Writer) int {
	if len(args) == 0 || args[0] != "resolve" {
		return writeEnvelope(stdout, NewEnvelope("usage-error", "lane resolve is the supported runtime operation"))
	}
	projectRoot := optionValue(args, "--project-root", ".")
	command := strings.ToLower(strings.TrimSpace(optionValue(args, "--command", "")))
	if command == "" {
		return writeEnvelope(stdout, NewEnvelope("usage-error", "--command is required"))
	}
	records, err := readRuntimeLanes(projectRoot)
	if err != nil {
		return writeEnvelope(stdout, laneBlocked("lane index is invalid", err))
	}
	featureDir := filepath.ToSlash(strings.TrimSpace(optionValue(args, "--feature-dir", "")))
	candidates := make([]runtimeLaneRecord, 0, len(records))
	for _, lane := range records {
		if featureDir != "" && filepath.ToSlash(lane.FeatureDir) != featureDir {
			continue
		}
		inferred := inferRuntimeLaneCommand(projectRoot, lane)
		if featureDir == "" && command != "auto" && inferred != command {
			continue
		}
		lane.LastCommand = inferred
		candidates = append(candidates, lane)
	}

	mode, selectedID, reason := resolveRuntimeLaneCandidates(candidates, featureDir != "")
	env := NewEnvelope("ok", "lane resolution completed")
	env.Data["mode"] = mode
	env.Data["selected_lane_id"] = selectedID
	env.Data["reason"] = reason
	env.Data["candidates"] = runtimeLaneCandidates(projectRoot, candidates)
	if mode == "blocked" || mode == "choose" {
		env.Status = "blocked"
		env.Blockers = append(env.Blockers, map[string]any{
			"code":              "lane-selection-required",
			"owner":             "agent",
			"cause":             reason,
			"exact_next_action": "Select one candidate feature directory explicitly and rerun lane resolve.",
		})
	}
	if hasFlag(args, "--ensure-worktree") && mode == "resume" {
		selected := findRuntimeLane(candidates, selectedID)
		if selected == nil {
			return writeEnvelope(stdout, laneBlocked("selected lane record disappeared", fmt.Errorf("%s", selectedID)))
		}
		worktree, worktreeErr := materializeRuntimeLaneWorktree(projectRoot, *selected)
		if worktreeErr != nil {
			return writeEnvelope(stdout, laneBlocked("lane worktree provisioning failed", worktreeErr))
		}
		env.Data["worktree"] = worktree
	}
	return writeEnvelope(stdout, env)
}

func readRuntimeLanes(projectRoot string) ([]runtimeLaneRecord, error) {
	root, err := secureProjectPath(projectRoot, ".specify/lanes")
	if err != nil {
		return nil, err
	}
	entries, err := os.ReadDir(root)
	if os.IsNotExist(err) {
		return []runtimeLaneRecord{}, nil
	}
	if err != nil {
		return nil, err
	}
	records := []runtimeLaneRecord{}
	for _, entry := range entries {
		if !entry.IsDir() {
			continue
		}
		raw, readErr := os.ReadFile(filepath.Join(root, entry.Name(), "lane.json"))
		if os.IsNotExist(readErr) {
			continue
		}
		if readErr != nil {
			return nil, readErr
		}
		var record runtimeLaneRecord
		if jsonErr := json.Unmarshal(raw, &record); jsonErr != nil {
			return nil, fmt.Errorf("%s: %w", entry.Name(), jsonErr)
		}
		if record.LaneID == "" || record.FeatureDir == "" {
			continue
		}
		records = append(records, record)
	}
	sort.Slice(records, func(i, j int) bool { return records[i].LaneID < records[j].LaneID })
	return records, nil
}

func inferRuntimeLaneCommand(projectRoot string, lane runtimeLaneRecord) string {
	featureRoot, err := secureProjectPath(projectRoot, filepath.ToSlash(lane.FeatureDir))
	if err == nil {
		tracker, readErr := os.ReadFile(filepath.Join(featureRoot, "implement-tracker.md"))
		if readErr == nil {
			lowered := strings.ToLower(string(tracker))
			for _, status := range []string{"gathering", "executing", "recovering", "replanning", "validating", "blocked", "resolved"} {
				if strings.Contains(lowered, "status: "+status) {
					return "implement"
				}
			}
		}
		workflow, readErr := os.ReadFile(filepath.Join(featureRoot, "workflow-state.md"))
		if readErr == nil {
			for _, line := range strings.Split(string(workflow), "\n") {
				normalized := strings.TrimSpace(line)
				if strings.HasPrefix(normalized, "next_command:") {
					next := strings.TrimSpace(strings.TrimPrefix(normalized, "next_command:"))
					next = strings.Trim(next, `"'`)
					next = strings.TrimPrefix(next, "spx-")
					next = strings.TrimPrefix(next, "sp-")
					if next != "" {
						return strings.Fields(next)[0]
					}
				}
			}
		}
	}
	if command := strings.ToLower(strings.TrimSpace(lane.LastCommand)); command != "" {
		return strings.TrimPrefix(strings.TrimPrefix(command, "spx-"), "sp-")
	}
	return "specify"
}

func resolveRuntimeLaneCandidates(candidates []runtimeLaneRecord, explicit bool) (string, string, string) {
	if explicit {
		if len(candidates) == 1 {
			return "resume", candidates[0].LaneID, "explicit-feature-dir"
		}
		return "blocked", "", "feature-dir-has-no-registered-lane"
	}
	resumable := []runtimeLaneRecord{}
	uncertain := false
	for _, candidate := range candidates {
		switch candidate.RecoveryState {
		case "resumable":
			resumable = append(resumable, candidate)
		case "uncertain":
			uncertain = true
		}
	}
	if len(resumable) == 1 && !uncertain {
		return "resume", resumable[0].LaneID, "unique-safe-candidate"
	}
	if len(resumable) > 0 || uncertain {
		return "choose", "", "ambiguous-or-uncertain"
	}
	return "start", "", "no-resumable-candidate"
}

func runtimeLaneCandidates(projectRoot string, lanes []runtimeLaneRecord) []any {
	items := make([]any, 0, len(lanes))
	for _, lane := range lanes {
		worktree, _ := secureProjectPath(projectRoot, filepath.ToSlash(lane.WorktreePath))
		_, statErr := os.Stat(worktree)
		items = append(items, map[string]any{
			"lane_id":                lane.LaneID,
			"feature_id":             lane.FeatureID,
			"feature_dir":            filepath.ToSlash(lane.FeatureDir),
			"last_command":           lane.LastCommand,
			"recovery_state":         lane.RecoveryState,
			"last_stable_checkpoint": lane.LastStableCheckpoint,
			"recovery_reason":        lane.RecoveryReason,
			"verification_status":    defaultString(lane.VerificationStatus, "unknown"),
			"worktree_path":          filepath.ToSlash(lane.WorktreePath),
			"worktree_exists":        statErr == nil,
		})
	}
	return items
}

func materializeRuntimeLaneWorktree(projectRoot string, lane runtimeLaneRecord) (map[string]any, error) {
	if lane.WorktreePath == "" || lane.BranchName == "" {
		return nil, fmt.Errorf("lane is missing worktree_path or branch_name")
	}
	target, err := secureProjectPath(projectRoot, filepath.ToSlash(lane.WorktreePath))
	if err != nil {
		return nil, err
	}
	status := "existing"
	if info, statErr := os.Stat(target); statErr != nil || !info.IsDir() {
		command := exec.Command("git", "worktree", "add", target, lane.BranchName)
		command.Dir = projectRoot
		if output, commandErr := command.CombinedOutput(); commandErr != nil {
			return nil, fmt.Errorf("git worktree add: %w: %s", commandErr, strings.TrimSpace(string(output)))
		}
		status = "created"
	}
	if err := copyRuntimeBindingToWorktree(projectRoot, target); err != nil {
		return nil, err
	}
	return map[string]any{
		"status":        status,
		"checkout_mode": "branch",
		"path":          filepath.ToSlash(lane.WorktreePath),
		"reason":        "project runtime binding provisioned",
	}, nil
}

func copyRuntimeBindingToWorktree(projectRoot, target string) error {
	relativeEntrypoint := strings.TrimPrefix(projectRuntimeRelativeEntrypoint(), "./")
	relativeEntrypoint = strings.TrimPrefix(relativeEntrypoint, `.\`)
	sourceName := filepath.Base(filepath.FromSlash(relativeEntrypoint))
	source, err := secureProjectPath(projectRoot, filepath.ToSlash(filepath.Join(".specify", "bin", sourceName)))
	if err != nil {
		return err
	}
	destination, err := secureProjectPath(target, filepath.ToSlash(filepath.Join(".specify", "bin", sourceName)))
	if err != nil {
		return err
	}
	raw, err := os.ReadFile(source)
	if err != nil {
		return err
	}
	sourceConfigPath, err := secureProjectPath(projectRoot, ".specify/config.json")
	if err != nil {
		return err
	}
	sourceConfigRaw, err := os.ReadFile(sourceConfigPath)
	if err != nil {
		return err
	}
	var sourceConfig map[string]any
	if err := json.Unmarshal(sourceConfigRaw, &sourceConfig); err != nil {
		return err
	}
	if err := validateRuntimeBindingForCopy(sourceConfig, raw); err != nil {
		return err
	}
	if err := os.MkdirAll(filepath.Dir(destination), 0o755); err != nil {
		return err
	}
	destination, err = secureProjectPath(target, filepath.ToSlash(filepath.Join(".specify", "bin", sourceName)))
	if err != nil {
		return err
	}
	if err := writeLaneAtomicFile(destination, raw, 0o755); err != nil {
		return err
	}
	targetConfigPath, err := secureProjectPath(target, ".specify/config.json")
	if err != nil {
		return err
	}
	targetConfig := map[string]any{}
	if targetRaw, readErr := os.ReadFile(targetConfigPath); readErr == nil {
		if err := json.Unmarshal(targetRaw, &targetConfig); err != nil {
			return err
		}
	} else if !os.IsNotExist(readErr) {
		return readErr
	}
	for _, key := range []string{"runtime_launcher", "runtime_launcher_binding"} {
		if value, ok := sourceConfig[key]; ok {
			targetConfig[key] = value
		}
	}
	encoded, err := json.MarshalIndent(targetConfig, "", "  ")
	if err != nil {
		return err
	}
	if err := os.MkdirAll(filepath.Dir(targetConfigPath), 0o755); err != nil {
		return err
	}
	targetConfigPath, err = secureProjectPath(target, ".specify/config.json")
	if err != nil {
		return err
	}
	return writeLaneAtomicFile(targetConfigPath, append(encoded, '\n'), 0o644)
}

func validateRuntimeBindingForCopy(config map[string]any, runtimeRaw []byte) error {
	launcher, ok := config["runtime_launcher"].(map[string]any)
	if !ok {
		return fmt.Errorf("runtime_launcher is not configured")
	}
	argv, ok := launcher["argv"].([]any)
	if !ok || len(argv) != 1 {
		return fmt.Errorf("runtime_launcher.argv must contain one project-local entrypoint")
	}
	entrypoint, ok := argv[0].(string)
	if !ok || normalizeRuntimePath(entrypoint) != normalizedRuntimeEntrypoint() {
		return fmt.Errorf("runtime_launcher must use the project-local .specify/bin entrypoint")
	}
	binding, ok := config["runtime_launcher_binding"].(map[string]any)
	if !ok {
		return fmt.Errorf("runtime_launcher_binding is not configured")
	}
	boundEntrypoint, _ := binding["runtime_entrypoint"].(string)
	if normalizeRuntimePath(boundEntrypoint) != normalizedRuntimeEntrypoint() {
		return fmt.Errorf("runtime_launcher_binding entrypoint does not match the project runtime")
	}
	expectedDigest, _ := binding["runtime_binary_sha256"].(string)
	actualDigest := sha256String(string(runtimeRaw))
	if expectedDigest == "" || !strings.EqualFold(expectedDigest, actualDigest) {
		return fmt.Errorf("project runtime digest does not match runtime_launcher_binding")
	}
	return nil
}

func writeLaneAtomicFile(path string, raw []byte, mode os.FileMode) error {
	temporary, err := os.CreateTemp(filepath.Dir(path), "."+filepath.Base(path)+".*.tmp")
	if err != nil {
		return err
	}
	temporaryName := temporary.Name()
	defer os.Remove(temporaryName)
	if _, err := temporary.Write(raw); err != nil {
		temporary.Close()
		return err
	}
	if err := temporary.Chmod(mode); err != nil {
		temporary.Close()
		return err
	}
	if err := temporary.Sync(); err != nil {
		temporary.Close()
		return err
	}
	if err := temporary.Close(); err != nil {
		return err
	}
	return replaceFile(temporaryName, path)
}

func findRuntimeLane(records []runtimeLaneRecord, laneID string) *runtimeLaneRecord {
	for index := range records {
		if records[index].LaneID == laneID {
			return &records[index]
		}
	}
	return nil
}

func laneBlocked(summary string, err error) Envelope {
	env := NewEnvelope("blocked", summary)
	env.Blockers = append(env.Blockers, err.Error())
	return env
}
