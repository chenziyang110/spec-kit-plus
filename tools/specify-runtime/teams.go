package main

import (
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"
)

func runTeams(args []string, stdout io.Writer) int {
	if len(args) == 0 {
		return teamsWriteError(stdout, "usage-error", "missing teams subcommand")
	}
	switch args[0] {
	case "status":
		return teamsStatus(args[1:], stdout)
	case "doctor":
		return teamsDoctor(args[1:], stdout)
	case "live-probe":
		return teamsLiveProbe(args[1:], stdout)
	case "auto-dispatch":
		return teamsAutoDispatch(args[1:], stdout)
	case "complete-batch":
		return teamsCompleteBatch(args[1:], stdout)
	case "submit-result":
		return teamsSubmitResult(args[1:], stdout)
	case "result-template":
		return teamsResultTemplate(args[1:], stdout)
	case "sync-back":
		return teamsSyncBack(args[1:], stdout)
	default:
		return teamsWriteError(stdout, "usage-error", fmt.Sprintf("unknown teams subcommand %q", args[0]))
	}
}

func teamsStatus(args []string, stdout io.Writer) int {
	root, env, ok := teamsProjectRoot()
	if !ok {
		return writeEnvelope(stdout, env)
	}
	sessionID := optionValue(args, "--session-id", "default")
	payload := teamsRuntimeStatus(root, sessionID)
	env = NewEnvelope("ok", "codex teams runtime status")
	env.Data = payload
	return writeEnvelope(stdout, env)
}

func teamsDoctor(args []string, stdout io.Writer) int {
	root, env, ok := teamsProjectRoot()
	if !ok {
		return writeEnvelope(stdout, env)
	}
	sessionID := optionValue(args, "--session-id", "default")
	payload := map[string]any{
		"status":            teamsRuntimeStatus(root, sessionID),
		"transcript":        teamsLatestTranscript(root),
		"failed_dispatches": teamsFailedDispatches(root),
		"recent_batches":    teamsRecentBatches(root),
	}
	env = NewEnvelope("ok", "codex teams doctor report")
	env.Data = payload
	return writeEnvelope(stdout, env)
}

func teamsLiveProbe(args []string, stdout io.Writer) int {
	_, env, ok := teamsProjectRoot()
	if !ok {
		return writeEnvelope(stdout, env)
	}
	sessionID := optionValue(args, "--session-id", "default")
	env = NewEnvelope("blocked", "live teams dispatch probe is unavailable in standalone specify-runtime")
	env.Data["session_id"] = sessionID
	env.Data["reason"] = "standalone Go runtime cannot safely launch Codex/agent-teams external dispatch"
	env.Blockers = append(env.Blockers, env.Data["reason"])
	return writeEnvelope(stdout, env)
}

func teamsAutoDispatch(args []string, stdout io.Writer) int {
	root, env, ok := teamsProjectRoot()
	if !ok {
		return writeEnvelope(stdout, env)
	}
	featureDir := optionValue(args, "--feature-dir", "")
	if strings.TrimSpace(featureDir) == "" {
		return teamsWriteError(stdout, "usage-error", "--feature-dir is required")
	}
	resolved, err := resolveProjectContainedPath(root, featureDir)
	if err != nil {
		return teamsWriteError(stdout, "usage-error", "feature_dir must stay inside project_root: "+err.Error())
	}
	env = NewEnvelope("blocked", "auto-dispatch is unavailable in standalone specify-runtime")
	env.Data["feature_dir"] = resolved
	env.Data["reason"] = "standalone Go runtime cannot safely spawn Codex workers or agent-teams runtime-cli"
	env.Blockers = append(env.Blockers, env.Data["reason"])
	return writeEnvelope(stdout, env)
}

func teamsCompleteBatch(args []string, stdout io.Writer) int {
	root, env, ok := teamsProjectRoot()
	if !ok {
		return writeEnvelope(stdout, env)
	}
	batchID := strings.TrimSpace(optionValue(args, "--batch-id", ""))
	if batchID == "" {
		return teamsWriteError(stdout, "usage-error", "--batch-id is required")
	}
	path := teamsBatchRecordPath(root, batchID)
	batch, err := teamsReadJSONMap(path)
	if err != nil {
		return teamsWriteError(stdout, "blocked", "batch record not found: "+batchID)
	}
	requests := teamsStringList(batch["request_ids"])
	missing := []string{}
	failed := []string{}
	for _, requestID := range requests {
		result, err := teamsReadJSONMap(teamsResultRecordPath(root, requestID))
		if err != nil {
			missing = append(missing, requestID)
			continue
		}
		status := strings.ToLower(strings.TrimSpace(fmt.Sprint(result["status"])))
		if status != "success" && status != "passed" && status != "done" {
			failed = append(failed, requestID+":"+status)
		}
	}
	if len(missing) > 0 || len(failed) > 0 {
		env = NewEnvelope("blocked", "batch is not terminal")
		env.Data["batch_id"] = batchID
		env.Data["missing_results"] = stringSliceToAny(missing)
		env.Data["non_success_results"] = stringSliceToAny(failed)
		env.Blockers = append(env.Blockers, "all batch request_ids must have terminal successful result records")
		return writeEnvelope(stdout, env)
	}
	batch["status"] = "completed"
	batch["updated_at"] = utcNow()
	if err := writeJSONAtomic(path, batch); err != nil {
		return teamsWriteError(stdout, "error", "write batch record: "+err.Error())
	}
	env = NewEnvelope("ok", "batch completed")
	env.Data = batch
	return writeEnvelope(stdout, env)
}

func teamsSubmitResult(args []string, stdout io.Writer) int {
	root, env, ok := teamsProjectRoot()
	if !ok {
		return writeEnvelope(stdout, env)
	}
	if hasFlag(args, "--print-schema") {
		env = NewEnvelope("ok", "worker result schema")
		env.Data = teamsWorkerResultSchemaHint()
		return writeEnvelope(stdout, env)
	}
	requestID := strings.TrimSpace(optionValue(args, "--request-id", ""))
	resultFile := strings.TrimSpace(optionValue(args, "--result-file", ""))
	if requestID == "" {
		return teamsWriteError(stdout, "usage-error", "--request-id is required unless --print-schema is used")
	}
	if resultFile == "" {
		return teamsWriteError(stdout, "usage-error", "--result-file is required unless --print-schema is used")
	}
	resultPath, err := resolveProjectContainedPath(root, resultFile)
	if err != nil {
		return teamsWriteError(stdout, "usage-error", "result file path is invalid: "+err.Error())
	}
	raw, err := os.ReadFile(resultPath)
	if err != nil {
		return teamsWriteError(stdout, "blocked", "Result file not found: "+resultPath)
	}
	normalized, err := teamsNormalizeResultSubmission(root, requestID, raw)
	if err != nil {
		return teamsWriteError(stdout, "invalid", err.Error())
	}
	record := map[string]any{}
	for key, value := range normalized {
		record[key] = value
	}
	record["request_id"] = requestID
	record["session_id"] = optionValue(args, "--session-id", "default")
	record["submitted_at"] = utcNow()
	if err := writeJSONAtomic(teamsResultRecordPath(root, requestID), record); err != nil {
		return teamsWriteError(stdout, "error", "write result record: "+err.Error())
	}
	env = NewEnvelope("ok", "worker result submitted")
	env.Data = record
	return writeEnvelope(stdout, env)
}

func teamsResultTemplate(args []string, stdout io.Writer) int {
	root, env, ok := teamsProjectRoot()
	if !ok {
		return writeEnvelope(stdout, env)
	}
	requestID := strings.TrimSpace(optionValue(args, "--request-id", ""))
	if requestID == "" {
		return teamsWriteError(stdout, "usage-error", "--request-id is required")
	}
	template, err := teamsBuildRequestResultTemplate(root, requestID)
	if err != nil {
		return teamsWriteError(stdout, "blocked", err.Error())
	}
	if output := strings.TrimSpace(optionValue(args, "--output", "")); output != "" {
		outPath, err := resolveProjectContainedPath(root, output)
		if err != nil {
			return teamsWriteError(stdout, "usage-error", "output path is invalid: "+err.Error())
		}
		if err := writeJSONAtomic(outPath, template); err != nil {
			return teamsWriteError(stdout, "error", "write result template: "+err.Error())
		}
		env = NewEnvelope("ok", "result template written")
		env.Data["path"] = outPath
		env.Data["request_id"] = requestID
		return writeEnvelope(stdout, env)
	}
	env = NewEnvelope("ok", "result template rendered")
	env.Data = template
	return writeEnvelope(stdout, env)
}

func teamsSyncBack(args []string, stdout io.Writer) int {
	root, env, ok := teamsProjectRoot()
	if !ok {
		return writeEnvelope(stdout, env)
	}
	sessionID := optionValue(args, "--session-id", "default")
	allowDirty := hasFlag(args, "--allow-dirty")
	plan := teamsPlanSyncBack(root, sessionID, allowDirty)
	if hasFlag(args, "--dry-run") {
		env = NewEnvelope("ok", "sync-back plan")
		env.Data = plan
		return writeEnvelope(stdout, env)
	}
	if plan["dirty_workspace"] == true && !allowDirty {
		env = NewEnvelope("blocked", "main workspace is dirty")
		env.Data = plan
		env.Blockers = append(env.Blockers, "Main workspace is dirty; rerun sync-back with --allow-dirty to override.")
		return writeEnvelope(stdout, env)
	}
	candidates, _ := plan["candidates"].([]any)
	copied := []any{}
	for _, raw := range candidates {
		candidate := raw.(map[string]any)
		source := fmt.Sprint(candidate["source_path"])
		target := fmt.Sprint(candidate["target_path"])
		data, err := os.ReadFile(source)
		if err != nil {
			return teamsWriteError(stdout, "error", "read sync-back source: "+err.Error())
		}
		if err := writeTextAtomic(target, string(data)); err != nil {
			return teamsWriteError(stdout, "error", "write sync-back target: "+err.Error())
		}
		copied = append(copied, candidate)
	}
	result := cloneImplementMap(plan)
	result["copied_count"] = len(copied)
	result["copied"] = copied
	env = NewEnvelope("ok", "sync-back completed")
	env.Data = result
	return writeEnvelope(stdout, env)
}

func teamsProjectRoot() (string, Envelope, bool) {
	root, err := os.Getwd()
	if err != nil {
		return "", NewEnvelope("error", "resolve project root: "+err.Error()), false
	}
	integration, err := teamsIntegrationKey(root)
	if err != nil {
		env := NewEnvelope("usage-error", err.Error())
		env.Blockers = append(env.Blockers, err.Error())
		return "", env, false
	}
	if integration != "codex" {
		env := NewEnvelope("usage-error", "Codex team runtime is only available for Codex integration projects.")
		env.Blockers = append(env.Blockers, "set .specify/integration.json integration to codex")
		return "", env, false
	}
	return root, Envelope{}, true
}

func teamsIntegrationKey(root string) (string, error) {
	payload, err := teamsReadJSONMap(filepath.Join(root, ".specify", "integration.json"))
	if err != nil {
		return "", errors.New(".specify/integration.json is missing the integration key")
	}
	key := strings.TrimSpace(fmt.Sprint(payload["integration"]))
	if key == "" || key == "<nil>" {
		return "", errors.New(".specify/integration.json is missing the integration key")
	}
	return key, nil
}

func teamsRuntimeStatus(root, sessionID string) map[string]any {
	backend := teamsDetectBackend()
	executor := teamsDetectExecutor(root)
	git := teamsGitReadiness(root)
	return map[string]any{
		"available":                        true,
		"runtime_backend_available":        backend["available"],
		"runtime_backend":                  backend["name"],
		"runtime_backend_binary":           backend["binary"],
		"runtime_backend_source":           backend["source"],
		"tmux_available":                   backend["name"] == "tmux",
		"native_windows":                   runtime.GOOS == "windows",
		"native_toolchain_ready":           true,
		"native_toolchain_required":        []any{},
		"native_toolchain_missing":         []any{},
		"native_build_shell":               map[string]any{"source": "native-runtime", "ready": true},
		"baseline_build":                   map[string]any{"status": "unknown", "reason": "standalone runtime fallback does not run baseline build probes"},
		"git_repo_detected":                git["git_repo_detected"],
		"git_head_available":               git["git_head_available"],
		"leader_workspace_clean":           git["leader_workspace_clean"],
		"worktree_ready":                   git["worktree_ready"],
		"executor_available":               executor["available"],
		"executor_mode":                    executor["mode"],
		"executor_reason":                  executor["reason"],
		"executor_bundled_runtime_binary":  executor["runtime_cli_path"],
		"executor_runtime_cli_path":        executor["runtime_cli_path"],
		"executor_packet_executor_command": executor["packet_executor_command"],
		"teams_ready":                      backend["available"] == true && git["worktree_ready"] == true && executor["available"] == true,
		"next_steps":                       teamsNextSteps(backend, executor, git),
		"state_root":                       teamsStateRoot(root),
		"runtime_state":                    teamsLoadRuntimeSession(root, sessionID),
		"runtime_state_source":             "live",
		"runtime_state_summary":            "Runtime state surfaces worker outcomes, join points, retry-pending work, and blockers.",
	}
}

func teamsDetectBackend() map[string]any {
	for _, name := range []string{"psmux", "tmux"} {
		if path, err := exec.LookPath(name); err == nil {
			return map[string]any{"available": true, "name": name, "binary": path, "source": "path"}
		}
	}
	return map[string]any{"available": false, "name": nil, "binary": nil, "source": "unavailable"}
}

func teamsDetectExecutor(root string) map[string]any {
	if raw := strings.TrimSpace(os.Getenv("SPECIFY_CODEX_TEAM_PACKET_EXECUTOR")); raw != "" {
		return map[string]any{"available": true, "mode": "packet-executor", "reason": "SPECIFY_CODEX_TEAM_PACKET_EXECUTOR is configured", "packet_executor_command": []any{raw}, "runtime_cli_path": ""}
	}
	runtimeCLI := filepath.Join(root, ".specify", "extensions", "agent-teams", "engine", "dist", "team", "runtime-cli.js")
	if _, err := os.Stat(runtimeCLI); err == nil {
		if node, nodeErr := exec.LookPath("node"); nodeErr == nil {
			return map[string]any{"available": true, "mode": "agent-teams-runtime", "reason": "Bundled agent-teams runtime-cli is available", "packet_executor_command": []any{node, runtimeCLI}, "runtime_cli_path": runtimeCLI}
		}
	}
	return map[string]any{"available": false, "mode": "unavailable", "reason": "No packet executor or agent-teams runtime-cli is configured", "packet_executor_command": []any{}, "runtime_cli_path": ""}
}

func teamsGitReadiness(root string) map[string]any {
	inside := teamsGitOutput(root, "rev-parse", "--is-inside-work-tree") == "true"
	head := teamsGitOutput(root, "rev-parse", "--verify", "HEAD") != ""
	clean := teamsGitOutput(root, "status", "--short") == ""
	return map[string]any{"git_repo_detected": inside, "git_head_available": head, "leader_workspace_clean": clean, "worktree_ready": inside && head && clean}
}

func teamsGitOutput(root string, args ...string) string {
	cmd := exec.Command("git", args...)
	cmd.Dir = root
	raw, err := cmd.Output()
	if err != nil {
		return ""
	}
	return strings.TrimSpace(string(raw))
}

func teamsNextSteps(backend, executor, git map[string]any) []any {
	steps := []any{}
	if backend["available"] != true {
		steps = append(steps, "Install tmux or psmux before teams execution.")
	}
	if executor["available"] != true {
		steps = append(steps, "Configure SPECIFY_CODEX_TEAM_PACKET_EXECUTOR or install bundled agent-teams runtime-cli.")
	}
	if git["worktree_ready"] != true {
		steps = append(steps, "Initialize git, create HEAD, and commit or stash leader workspace changes before teams execution.")
	}
	return steps
}

func teamsBuildRequestResultTemplate(root, requestID string) (map[string]any, error) {
	packet, _, err := teamsLoadRequestPacket(root, requestID)
	if err != nil {
		return nil, err
	}
	gates := teamsStringList(packet["validation_gates"])
	validation := []any{}
	for _, gate := range gates {
		validation = append(validation, map[string]any{"command": gate, "status": "skipped", "output": "NOT RUN - replace with actual command output after execution"})
	}
	scope, _ := packet["scope"].(map[string]any)
	template := map[string]any{
		"task_id":            packet["task_id"],
		"status":             "pending",
		"changed_files":      scope["write_scope"],
		"validation_results": validation,
		"summary":            packet["objective"],
		"rule_acknowledgement": map[string]any{
			"required_references_read":  false,
			"forbidden_drift_respected": false,
			"context_bundle_read":       false,
			"paths_read":                []any{},
			"critical_notes":            []any{"Replace the pending placeholder with the real validation evidence before returning success."},
		},
	}
	return template, nil
}

func teamsNormalizeResultSubmission(root, requestID string, raw []byte) (map[string]any, error) {
	if len(raw) >= 3 && raw[0] == 0xef && raw[1] == 0xbb && raw[2] == 0xbf {
		return nil, errors.New("Result file contains a UTF-8 BOM. Re-save it without BOM and retry.")
	}
	packet, _, err := teamsLoadRequestPacket(root, requestID)
	if err != nil {
		return nil, err
	}
	normalized, err := normalizeWorkerTaskResult(raw)
	if err != nil {
		return nil, err
	}
	if strings.TrimSpace(fmt.Sprint(normalized["task_id"])) == "" {
		return nil, errors.New("Result file is missing required fields: task_id")
	}
	if strings.TrimSpace(fmt.Sprint(normalized["status"])) == "" {
		return nil, errors.New("Result file is missing required fields: status")
	}
	if fmt.Sprint(normalized["task_id"]) != fmt.Sprint(packet["task_id"]) {
		return nil, fmt.Errorf("Result task_id %q does not match dispatched packet task_id %q.", normalized["task_id"], packet["task_id"])
	}
	if normalized["status"] == "pending" {
		return nil, errors.New("Pending result templates cannot be submitted.")
	}
	return normalized, nil
}

func teamsLoadRequestPacket(root, requestID string) (map[string]any, string, error) {
	dispatch, err := teamsReadJSONMap(teamsDispatchRecordPath(root, requestID))
	if err != nil {
		return nil, "", fmt.Errorf("Dispatch request %s was not found.", requestID)
	}
	packetPath := strings.TrimSpace(fmt.Sprint(dispatch["packet_path"]))
	if packetPath == "" {
		return nil, "", fmt.Errorf("Packet for request %s is unavailable.", requestID)
	}
	if !filepath.IsAbs(packetPath) {
		packetPath = filepath.Join(root, filepath.FromSlash(packetPath))
	}
	cleanPacket, err := resolveProjectContainedPath(root, packetPath)
	if err != nil {
		return nil, "", fmt.Errorf("Packet for request %s is unsafe.", requestID)
	}
	packet, err := teamsReadJSONMap(cleanPacket)
	if err != nil {
		return nil, "", fmt.Errorf("Packet for request %s is unavailable.", requestID)
	}
	return packet, cleanPacket, nil
}

func teamsWorkerResultSchemaHint() map[string]any {
	return map[string]any{
		"required_fields":        []any{"task_id", "status"},
		"recommended_fields":     []any{"changed_files", "validation_results", "summary", "rule_acknowledgement"},
		"accepted_status_values": []any{"pending", "success", "blocked", "failed"},
		"canonical_template_defaults": map[string]any{
			"status": "pending", "validation_results": "skipped until real execution occurs",
		},
		"submission_rules": []any{"Do not submit the canonical pending template unchanged.", "Replace pending/skipped placeholder values with the real success, blocked, or failed result before submit-result."},
	}
}

func teamsPlanSyncBack(root, sessionID string, allowDirty bool) map[string]any {
	candidates := teamsCollectSyncBackCandidates(root, sessionID)
	return map[string]any{"session_id": sessionID, "dirty_workspace": teamsWorkspaceDirty(root), "allow_dirty": allowDirty, "candidate_count": len(candidates), "candidates": candidates}
}

func teamsCollectSyncBackCandidates(root, sessionID string) []any {
	sessionRoot := filepath.Join(root, ".specify", "teams", "worktrees", sessionID)
	entries, err := os.ReadDir(sessionRoot)
	if err != nil {
		return []any{}
	}
	candidates := []any{}
	for _, entry := range entries {
		if !entry.IsDir() {
			continue
		}
		workerID := entry.Name()
		workerRoot := filepath.Join(sessionRoot, workerID)
		_ = filepath.WalkDir(workerRoot, func(path string, d os.DirEntry, err error) error {
			if err != nil || d.IsDir() {
				return nil
			}
			rel, err := filepath.Rel(workerRoot, path)
			if err != nil {
				return nil
			}
			parts := strings.Split(filepath.ToSlash(rel), "/")
			for _, part := range parts {
				if part == ".git" || part == ".specify" {
					return nil
				}
			}
			candidates = append(candidates, map[string]any{"worker_id": workerID, "source_path": path, "target_path": filepath.Join(root, rel), "relative_path": filepath.ToSlash(rel)})
			return nil
		})
	}
	return candidates
}

func teamsWorkspaceDirty(root string) bool {
	if teamsGitOutput(root, "rev-parse", "--is-inside-work-tree") != "true" {
		return false
	}
	return teamsGitOutput(root, "status", "--short") != ""
}

func teamsLoadRuntimeSession(root, sessionID string) any {
	payload, err := teamsReadJSONMap(teamsRuntimeSessionPath(root, sessionID))
	if err != nil {
		return nil
	}
	return payload
}

func teamsLatestTranscript(root string) any {
	executors := filepath.Join(teamsStateRoot(root), "executors")
	var latest string
	_ = filepath.WalkDir(executors, func(path string, d os.DirEntry, err error) error {
		if err == nil && !d.IsDir() && strings.HasSuffix(strings.ToLower(path), ".json") {
			if path > latest {
				latest = path
			}
		}
		return nil
	})
	if latest == "" {
		return nil
	}
	payload, err := teamsReadJSONMap(latest)
	if err != nil {
		return map[string]any{"path": latest}
	}
	payload["path"] = latest
	return payload
}

func teamsFailedDispatches(root string) []any {
	dispatchDir := filepath.Join(teamsStateRoot(root), "dispatch")
	entries, _ := os.ReadDir(dispatchDir)
	items := []any{}
	for _, entry := range entries {
		if entry.IsDir() || !strings.HasSuffix(entry.Name(), ".json") {
			continue
		}
		payload, err := teamsReadJSONMap(filepath.Join(dispatchDir, entry.Name()))
		if err == nil && strings.ToLower(fmt.Sprint(payload["status"])) == "failed" {
			items = append(items, payload)
		}
	}
	return items
}

func teamsRecentBatches(root string) []any {
	batchDir := filepath.Join(teamsStateRoot(root), "batches")
	entries, _ := os.ReadDir(batchDir)
	items := []any{}
	for _, entry := range entries {
		if entry.IsDir() || !strings.HasSuffix(entry.Name(), ".json") {
			continue
		}
		payload, err := teamsReadJSONMap(filepath.Join(batchDir, entry.Name()))
		if err == nil {
			items = append(items, payload)
		}
	}
	return items
}

func teamsStateRoot(root string) string {
	return filepath.Join(root, ".specify", "teams", "state")
}

func teamsRuntimeSessionPath(root, sessionID string) string {
	return filepath.Join(teamsStateRoot(root), "session-"+sessionID+".json")
}

func teamsDispatchRecordPath(root, requestID string) string {
	return filepath.Join(teamsStateRoot(root), "dispatch", requestID+".json")
}

func teamsResultRecordPath(root, requestID string) string {
	return filepath.Join(teamsStateRoot(root), "results", requestID+".json")
}

func teamsBatchRecordPath(root, batchID string) string {
	return filepath.Join(teamsStateRoot(root), "batches", batchID+".json")
}

func teamsReadJSONMap(path string) (map[string]any, error) {
	raw, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	var payload map[string]any
	if err := json.Unmarshal(raw, &payload); err != nil {
		return nil, err
	}
	return payload, nil
}

func teamsStringList(value any) []string {
	list, ok := value.([]any)
	if !ok {
		return []string{}
	}
	result := make([]string, 0, len(list))
	for _, raw := range list {
		if text := strings.TrimSpace(fmt.Sprint(raw)); text != "" && text != "<nil>" {
			result = append(result, text)
		}
	}
	return result
}

func teamsWriteError(stdout io.Writer, status, message string) int {
	env := NewEnvelope(status, message)
	env.Blockers = append(env.Blockers, message)
	return writeEnvelope(stdout, env)
}
